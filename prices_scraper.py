import time
import os
import re
import tempfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading

# Number of threads to use for parallel scraping
NUM_THREADS = 10

# Global variables for shared lock and page number
lock = threading.Lock()
current_page = 0
max_pages = 10  # Initial assumption; will adjust dynamically
results = []

def init_driver(thread_id):
    chrome_options = Options()
    
    # Use a pre-configured user data directory if available, or create a new one.
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
        # Check the last available page number
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
        # Open Google with the specified search query and page number
        start = (page_number - 1) * 10
        url = f"https://www.google.com/search?q={search_query}&start={start}"
        driver.get(url)

        # Update the max pages after loading the page
        update_max_pages(driver)

        # Wait for the page to load
        time.sleep(0.5)

        # Extract elements with the class 'ChPIuf' containing the euro sign (€)
        elements = driver.find_elements(By.CSS_SELECTOR, ".ChPIuf")
        for element in elements:
            price_text = element.text.strip()
            # Only extract the price without any additional text like reviews or votes
            match = re.search(r'(\d+,\d+)\s*€', price_text)
            if match and "Μη διαθέσιμο" not in price_text and "Unavailable" not in price_text:
                # Clean up to only include the price
                clean_price = match.group(1)
                price_value = float(clean_price.replace(',', '.'))
                # Find the parent <a> tag with jsname="UWckNb" within the same result block
                try:
                    parent_a = element.find_element(By.XPATH, './ancestor::div[contains(@class, "tF2Cxc")]//a[@jsname="UWckNb"]')
                    link_href = parent_a.get_attribute('href')
                    # Store the price and link
                    results.append((price_value, f"{clean_price} € <{link_href}>"))
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

def main():
    search_query = input("Enter the search query: ")

    threads = []
    for i in range(NUM_THREADS):  # Create 2 threads
        thread = threading.Thread(target=google_search_thread, args=(i+1, search_query))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # Sort the results by price (low to high)
    sorted_results = sorted(results, key=lambda x: x[0])

    # Print the sorted and filtered results
    print("\nPrices with Euro Sign (€):")
    for index, (_, result) in enumerate(sorted_results, start=1):
        print(f"{index}. {result}")

if __name__ == "__main__":
    main()
