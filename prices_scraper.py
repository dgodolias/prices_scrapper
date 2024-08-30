import random
import time
import os
import re
import tempfile
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import threading

# Thread number
NUM_THREADS = 2

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
    {"country_code": "ES", "domain": "google.es", "lang": "es", "currency": "EUR"},
    # Add more countries as needed...
]

# Supported currencies symbols for conversion
CURRENCY_SYMBOLS = {
    "€": "EUR",
    "$": "USD",
    "£": "GBP",
    "¥": "JPY",
    "SEK": "SEK",
    "DKK": "DKK",
    "PLN": "PLN",
    "CZK": "CZK",
    "HUF": "HUF",
    "RON": "RON",
    "BGN": "BGN",
}

def init_driver(thread_id):
    chrome_options = Options()
    
    user_data_dir = os.path.join(tempfile.gettempdir(), f"chrome_profile_{thread_id}")
    chrome_options.add_argument(f"user-data-dir={user_data_dir}")

    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("start-maximized")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("window-size=1280x720")  # Use lower resolution to reduce memory usage

    # Set a realistic user agent
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    if proxy:
        chrome_options.add_argument(f'--proxy-server={proxy}')


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
        print("Sleeping for 60 seconds before retrying...")
        time.sleep(60)

def perform_google_search(driver, search_query, page_number, country):
    try:
        time.sleep(random.uniform(1, 3))
        
        start = (page_number - 1) * 10
        url = f"https://{country['domain']}/search?q={search_query}&start={start}&hl={country['lang']}&gl={country['country_code']}&cr=country{country['country_code']}"
        driver.get(url)
        
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

def convert_currencies_to_euro(results):
    global exchange_rates
    for i in range(len(results)):
        price, currency_symbol, link, country_code, country_currency = results[i]
        if currency_symbol != "€":
            currency_code = CURRENCY_SYMBOLS.get(currency_symbol)
            if currency_code and currency_code in exchange_rates:
                euro_price = price / exchange_rates[currency_code]
                results[i] = (round(euro_price, 2), "€", link, country_code, country_currency)

def run_search(product, country):
    global results, current_page
    results = []  # Clear the results for each search
    current_page = 0  # Reset the current page counter
    
    threads = []
    for i in range(NUM_THREADS):
        thread = threading.Thread(target=google_search_thread, args=(i+1, product, country))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    return results
