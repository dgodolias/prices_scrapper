import random
import time
import os
import re
import tempfile
import requests  # To fetch conversion rates
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import threading

# Thread number
NUM_THREADS = 10

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
    {"country_code": "FR", "domain": "google.fr", "lang": "fr", "currency": "EUR"},
    {"country_code": "DE", "domain": "google.de", "lang": "de", "currency": "EUR"},
    {"country_code": "IT", "domain": "google.it", "lang": "it", "currency": "EUR"},
    {"country_code": "PT", "domain": "google.pt", "lang": "pt", "currency": "EUR"},
    {"country_code": "NL", "domain": "google.nl", "lang": "nl", "currency": "EUR"},
    {"country_code": "BE", "domain": "google.be", "lang": "nl", "currency": "EUR"},
    {"country_code": "IE", "domain": "google.ie", "lang": "en", "currency": "EUR"},
    {"country_code": "AT", "domain": "google.at", "lang": "de", "currency": "EUR"},
    {"country_code": "SE", "domain": "google.se", "lang": "sv", "currency": "SEK"},
    {"country_code": "FI", "domain": "google.fi", "lang": "fi", "currency": "EUR"},
    {"country_code": "DK", "domain": "google.dk", "lang": "da", "currency": "DKK"},
    {"country_code": "PL", "domain": "google.pl", "lang": "pl", "currency": "PLN"},
    {"country_code": "CZ", "domain": "google.cz", "lang": "cs", "currency": "CZK"},
    {"country_code": "HU", "domain": "google.hu", "lang": "hu", "currency": "HUF"},
    {"country_code": "RO", "domain": "google.ro", "lang": "ro", "currency": "RON"},
    {"country_code": "BG", "domain": "google.bg", "lang": "bg", "currency": "BGN"},
    {"country_code": "HR", "domain": "google.hr", "lang": "hr", "currency": "EUR"},
    {"country_code": "SI", "domain": "google.si", "lang": "sl", "currency": "EUR"},
    {"country_code": "SK", "domain": "google.sk", "lang": "sk", "currency": "EUR"},
    {"country_code": "LT", "domain": "google.lt", "lang": "lt", "currency": "EUR"},
    {"country_code": "LV", "domain": "google.lv", "lang": "lv", "currency": "EUR"},
    {"country_code": "EE", "domain": "google.ee", "lang": "et", "currency": "EUR"},
    {"country_code": "LU", "domain": "google.lu", "lang": "fr", "currency": "EUR"},
    {"country_code": "CY", "domain": "google.com.cy", "lang": "el", "currency": "EUR"},
    {"country_code": "MT", "domain": "google.com.mt", "lang": "en", "currency": "EUR"},
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
    
    chrome_options.add_argument("--headless=new")
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

    return webdriver.Chrome(options=chrome_options)

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
        # Use the domain and region parameters for the specific country
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


def currency_conversion_thread():
    print("Starting currency conversion thread...")
    fetch_exchange_rates()
    convert_currencies_to_euro()
    print("Currency conversion completed.")

def run_search(product, country):
    global results
    results = []  # Clear the results for each search

    # Reset the current page counter
    global current_page
    current_page = 0
    
    # Create threads to perform the search
    threads = []
    for i in range(NUM_THREADS):
        thread = threading.Thread(target=google_search_thread, args=(i+1, product, country))
        threads.append(thread)
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    # Return the results for this search
    return results


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
