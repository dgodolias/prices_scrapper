import time
import os
import tempfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading

# Global lock for shared resource
lock = threading.Lock()
results = []

THREADS_NUM = 1  # Only one thread needed for a single Google search

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

def perform_google_search(driver, search_query):
    try:
        # Open Google
        driver.get("https://www.google.com")

        # Wait for the textarea search box to be present and clickable
        search_box = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'APjFqb'))  # Locate the textarea by ID
        )
        search_box.click()  # Click to focus on the textarea
        search_box.clear()
        search_box.send_keys(search_query)  # Enter the search query
        search_box.send_keys(Keys.RETURN)  # Submit the search

        # Wait for the results to load
        time.sleep(2)

        # Extract elements with the class 'ChPIuf' containing the euro sign (€)
        elements = driver.find_elements(By.CSS_SELECTOR, ".ChPIuf")
        for element in elements:
            if "€" in element.text:
                # Find the parent <a> tag with jsname="UWckNb" within the same result block
                try:
                    parent_a = element.find_element(By.XPATH, './ancestor::div[contains(@class, "tF2Cxc")]//a[@jsname="UWckNb"]')
                    link_href = parent_a.get_attribute('href')
                    # Store the price and link
                    results.append(f"{element.text} <{link_href}>")
                except Exception as e:
                    print(f"Error finding the link for element: {e}")

    except Exception as e:
        print(f"Error during Google search: {e}")

def google_search_thread(thread_id, search_query):
    print(f"Thread {thread_id} started.")
    driver = init_driver(thread_id)
    
    perform_google_search(driver, search_query)

    print(f"Thread {thread_id} - Search completed, quitting driver...")
    try:
        driver.quit()
    except Exception as e:
        print(f"Thread {thread_id} - Error quitting driver: {e}")

def main():
    search_query = input("Enter the search query: ")

    threads = []
    for i in range(THREADS_NUM):  # Only one thread needed for this example
        thread = threading.Thread(target=google_search_thread, args=(i+1, search_query))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # Print the combined results once the thread is done
    print("\nPrices with Euro Sign (€):")
    for index, result in enumerate(results, start=1):
        print(f"{index}. {result}")

if __name__ == "__main__":
    main()
