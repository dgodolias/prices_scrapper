import random
import threading
import time
import os
import re
import tempfile
import requests
from config import *
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.proxy import Proxy, ProxyType
from webdriver_manager.chrome import ChromeDriverManager
from python3_capsolver.recaptcha import ReCaptcha

# Load proxies from file
def load_proxies(file_path):
    proxies = []
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line:
                ip, port, username, password = line.split(':')
                proxies.append((ip, port, username, password))
    return proxies

# Path to your proxies file
proxies_file_path = "100proxies.txt"
all_proxies = load_proxies(proxies_file_path)

# Thread number
NUM_THREADS = 1

# Global variables for shared lock and page number
lock = threading.Lock()
current_page = 0
max_pages = 10  # Initial assumption; will adjust dynamically
results = []

# To store exchange rates
exchange_rates = {}

# EU countries with their respective Google domain, language, currency, and region parameters
EU_COUNTRIES = [
    {"country_code": "GR", "domain": "google.gr", "lang": "el", "currency": "EUR"},
]

# Supported currencies symbols for conversion
CURRENCY_SYMBOLS = {
    "€": "EUR",
    "$": "USD",
    "£": "GBP",
    "¥": "JPY",
    # Add the rest of the currencies as in your original list...
}


def init_driver(thread_id):
    chrome_options = Options()
    
    # Create a unique profile for each thread
    user_data_dir = os.path.join(tempfile.gettempdir(), f"chrome_profile_{thread_id}")
    chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    
    # Proxy configuration: Only if proxies list is not empty
    if all_proxies:
        ip, port, username, password = random.choice(all_proxies)
        proxy = f"{ip}:{port}"
        print(f"Thread {thread_id} using proxy: {proxy} with credentials {username}/{password}")
        
        proxy_options = Proxy()
        proxy_options.proxy_type = ProxyType.MANUAL
        proxy_options.http_proxy = f"{username}:{password}@{proxy}"
        proxy_options.ssl_proxy = f"{username}:{password}@{proxy}"
        
        chrome_options.proxy = proxy_options
    else:
        print(f"Thread {thread_id} is running without a proxy")

    # Chrome options
    #chrome_options.add_argument("--headless=new")  # Uncomment if you want to run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("start-maximized")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-notifications")

    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def update_max_pages(driver):
    global max_pages
    try:
        page_elements = driver.find_elements(By.XPATH, '//td/a[@aria-label and contains(@aria-label, "Page")]')
        if page_elements:
            last_page_element = page_elements[-1]
            page_text = last_page_element.text.strip()
            if page_text.isdigit():
                max_pages = int(page_text)
                print(f"Updated max pages to: {max_pages}")
            else:
                print(f"Skipping non-numeric page text: '{page_text}'")
        else:
            max_pages = 1
            print("No page elements found, setting max pages to 1.")
    except Exception as e:
        print(f"Error updating max pages: {e}")

def perform_google_search(driver, search_query, page_number, country):
    try:
        time.sleep(random.uniform(1, 3))
        
        start = (page_number - 1) * 10
        url = f"https://{country['domain']}/search?q={search_query}&start={start}&hl={country['lang']}&gl={country['country_code']}&cr=country{country['country_code']}"
        driver.get(url)

        # Check for CAPTCHA presence
        if "captcha" in driver.page_source.lower():
            print("CAPTCHA detected! Attempting to solve...")
            
            # Attempt to find site key
            try:
                site_key_element = driver.find_element(By.CSS_SELECTOR, "div.g-recaptcha")
                site_key = site_key_element.get_attribute("data-sitekey")
                print(f"Site key found: {site_key}")
                
                # Solve the CAPTCHA using CapSolver
                api_key = capsolver_api_key  # Your CapSolver API key
                token = capsolver(api_key, site_key, url)
                
                if token:
                    # Inject the token into the page and submit
                    driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{token}";')
                    driver.execute_script("document.forms[0].submit();")
                    time.sleep(5)  # Wait for the page to reload

                    print("CAPTCHA solved and form submitted.")
                else:
                    print("Failed to solve CAPTCHA.")
                    return

            except Exception as e:
                print(f"Error while handling CAPTCHA: {e}")
                return

        update_max_pages(driver)

        time.sleep(2)

        elements = driver.find_elements(By.CSS_SELECTOR, ".ChPIuf")
        for element in elements:
            price_text = element.text.strip()
            match = re.search(r'(\d+[.,]\d{2})\s*([€$£¥])', price_text)
            if match and "Μη διαθέσιμο" not in price_text and "Unavailable" not in price_text:
                clean_price = match.group(1)
                currency_symbol = match.group(2)
                price_value = float(clean_price.replace(',', '.'))
                try:
                    parent_a = element.find_element(By.XPATH, './ancestor::div[contains(@class, "tF2Cxc")]//a[@jsname="UWckNb"]')
                    link_href = parent_a.get_attribute('href')
                    results.append((price_value, currency_symbol, link_href, country['country_code'], country['currency']))
                except Exception as e:
                    print(f"Error finding the link for element: {e}")

    except Exception as e:
        print(f"Error during Google search on page {page_number}: {e}")



def capsolver(api_key, site_key, site_url):
    payload = {
        "clientKey": api_key,
        "task": {
            "type": 'ReCaptchaV2TaskProxyLess',
            "websiteKey": site_key,
            "websiteURL": site_url
        }
    }
    res = requests.post("https://api.capsolver.com/createTask", json=payload)
    resp = res.json()
    task_id = resp.get("taskId")
    if not task_id:
        print("Failed to create task:", res.text)
        return None
    print(f"Got taskId: {task_id} / Getting result...")

    while True:
        time.sleep(3)  # delay
        payload = {"clientKey": api_key, "taskId": task_id}
        res = requests.post("https://api.capsolver.com/getTaskResult", json=payload)
        resp = res.json()
        status = resp.get("status")
        if status == "ready":
            return resp.get("solution", {}).get('gRecaptchaResponse')
        if status == "failed" or resp.get("errorId"):
            print("Solve failed! response:", res.text)
            return None




def google_search_thread(thread_id, search_query, country):
    global current_page
    driver = init_driver(thread_id)
    
    while True:
        with lock:
            if current_page >= max_pages:
                break
            current_page += 1
            page_number = current_page
        
        print(f"Thread {thread_id} processing page {page_number} for country {country['country_code']}")
        perform_google_search(driver, search_query, page_number, country)
    
    print(f"Thread {thread_id} completed its pages, quitting driver...")
    driver.quit()

def fetch_exchange_rates():
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/EUR")
        rates = response.json().get("rates", {})
        for symbol in CURRENCY_SYMBOLS.values():
            if symbol in rates:
                exchange_rates[symbol] = rates[symbol]
        print("Exchange rates fetched successfully:", exchange_rates)
    except Exception as e:
        print(f"Failed to fetch exchange rates: {e}")

def convert_currencies_to_euro():
    global results
    for i in range(len(results)):
        price, currency_symbol, link, country_code, country_currency = results[i]
        if currency_symbol != "€":
            currency_code = CURRENCY_SYMBOLS.get(currency_symbol)
            if currency_code and currency_code in exchange_rates:
                euro_price = price / exchange_rates[currency_code]
                results[i] = (round(euro_price, 2), "€", link, country_code, country_currency)

def currency_conversion_thread():
    print("Starting currency conversion thread...")
    fetch_exchange_rates()
    convert_currencies_to_euro()
    print("Currency conversion completed.")

def main():
    search_query = input("Enter the search query: ")

    for country in EU_COUNTRIES:
        global current_page
        current_page = 0
        threads = []
        for i in range(NUM_THREADS):
            thread = threading.Thread(target=google_search_thread, args=(i+1, search_query, country))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    # Start a thread for currency conversion
    conversion_thread = threading.Thread(target=currency_conversion_thread)
    conversion_thread.start()
    conversion_thread.join()

    # Sort the results by price (low to high)
    sorted_results = sorted(results, key=lambda x: x[0])

    # Print the sorted and converted results
    print("\nPrices with Currency Sign (converted to Euro):")
    for index, (price, _, link, country_code, _) in enumerate(sorted_results, start=1):
        print(f"{index}. {price} € [{country_code}] <{link}>")

if __name__ == "__main__":
    main()
