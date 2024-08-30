import random
import time
import os
import re
import tempfile
import requests  # To fetch conversion rates
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

# Supported currencies
CURRENCY_SYMBOLS = {
    "€": "EUR",
    "$": "USD",
    "£": "GBP",
    "¥": "JPY",
}

def init_driver(thread_id):
    chrome_options = Options()
    
    user_data_dir = os.path.join(tempfile.gettempdir(), f"chrome_profile_{thread_id}")
    chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    
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
            max_pages = int(last_page_element.text)
            print(f"Updated max pages to: {max_pages}")
        else:
            max_pages = 1
    except Exception as e:
        print(f"Error updating max pages: {e}")

def perform_google_search(driver, search_query, page_number):
    try:
        time.sleep(random.uniform(1, 3))
        
        start = (page_number - 1) * 10
        url = f"https://www.google.com/search?q={search_query}&start={start}"
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
                    results.append((price_value, currency_symbol, link_href))
                except Exception as e:
                    print(f"Error finding the link for element: {e}")

    except Exception as e:
        print(f"Error during Google search on page {page_number}: {e}")

def google_search_thread(thread_id, search_query):
    global current_page
    driver = init_driver(thread_id)
    
    while True:
        with lock:
            if current_page >= max_pages:
                break
            current_page += 1
            page_number = current_page
        
        print(f"Thread {thread_id} processing page {page_number}")
        perform_google_search(driver, search_query, page_number)
    
    print(f"Thread {thread_id} completed its pages, quitting driver...")
    driver.quit()

def fetch_exchange_rates():
    try:
        # Fetch current exchange rates from a reliable API
        response = requests.get("https://api.exchangerate-api.com/v4/latest/EUR")
        rates = response.json().get("rates", {})
        
        # Store the relevant exchange rates
        for symbol in CURRENCY_SYMBOLS.values():
            if symbol in rates:
                exchange_rates[symbol] = rates[symbol]
        print("Exchange rates fetched successfully:", exchange_rates)
    except Exception as e:
        print(f"Failed to fetch exchange rates: {e}")

def convert_currencies_to_euro():
    global results
    for i in range(len(results)):
        price, currency_symbol, link = results[i]
        if currency_symbol != "€":
            currency_code = CURRENCY_SYMBOLS.get(currency_symbol)
            if currency_code and currency_code in exchange_rates:
                euro_price = price / exchange_rates[currency_code]
                results[i] = (round(euro_price, 2), "€", link)

def currency_conversion_thread():
    print("Starting currency conversion thread...")
    fetch_exchange_rates()
    convert_currencies_to_euro()
    print("Currency conversion completed.")

def main():
    search_query = input("Enter the search query: ")

    threads = []
    for i in range(NUM_THREADS):  
        thread = threading.Thread(target=google_search_thread, args=(i+1, search_query))
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
    for index, (price, _, link) in enumerate(sorted_results, start=1):
        print(f"{index}. {price} € <{link}>")

if __name__ == "__main__":
    main()
