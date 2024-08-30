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
search_results = []

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

        # Scrape and print the titles of the search results
        results = driver.find_elements(By.CSS_SELECTOR, 'h3')
        print(f"Search results for '{search_query}':")
        for index, result in enumerate(results[:5], start=1):  # Limiting to top 5 results
            print(f"{index}. {result.text}")

        # Store the results
        with lock:
            search_results.extend([result.text for result in results[:5]])

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

def extract_euro_elements_and_links(driver):
    try:
        # Find all elements with class 'ChPIuf'
        euro_elements = driver.find_elements(By.CLASS_NAME, 'ChPIuf')
        
        results = []
        
        # Loop through the found elements
        for element in euro_elements:
            # Check if the text contains the Euro sign (€)
            if '€' in element.text:
                # Get the text of the element
                price_text = element.text
                
                # Locate the corresponding <a> tag with the specific jsname attribute
                link_element = element.find_element(By.XPATH, "./ancestor::a[@jsname='UWckNb']")
                link_url = link_element.get_attribute('href')
                
                # Store the result
                results.append((price_text, link_url))
        
        # Print the results
        for price_text, link_url in results:
            print(f"Price: {price_text}, Link: {link_url}")
            
        return results

    except Exception as e:
        print(f"Error extracting Euro elements and links: {e}")
        return []

def main():
    search_query = input("Enter the search query: ")

    threads = []
    for i in range(THREADS_NUM):  # Only one thread needed for this example
        thread = threading.Thread(target=google_search_thread, args=(i+1, search_query))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # After search is complete, extract Euro elements and links
    driver = init_driver(1)
    results = extract_euro_elements_and_links(driver)

    # Print the combined results
    print("\nFinal Extracted Prices and Links:")
    for price_text, link_url in results:
        print(f"Price: {price_text}, Link: {link_url}")

if __name__ == "__main__":
    main()

