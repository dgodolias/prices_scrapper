import threading
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.proxy import Proxy, ProxyType
from webdriver_manager.chrome import ChromeDriverManager
import time
from config import username, password


# List of proxies from your image (excluding the one that is not working)
proxies = [
    "38.154.227.167:5868",
    "45.127.248.127:5128",
    "64.64.118.149:6732",
    "167.160.180.203:6754",
    "166.88.58.10:5735",
    "173.0.9.70:5653",
    "45.151.162.198:6600",
    "204.44.69.89:6342",
    "173.0.9.209:5792",
    "206.41.172.74:6634"
]

# Global variables for threading
NUM_THREADS = 2
results = []
lock = threading.Lock()

# Function to create a webdriver instance with proxy
def get_webdriver(proxy):
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    proxy_options = Proxy()
    proxy_options.proxy_type = ProxyType.MANUAL
    proxy_options.http_proxy = f"{username}:{password}@{proxy}"
    proxy_options.ssl_proxy = f"{username}:{password}@{proxy}"
    
    chrome_options.proxy = proxy_options
    
    # Initialize the Chrome driver with options
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

# Function to perform a Google search and handle the results
def perform_google_search(search_query):
    proxy = random.choice(proxies)
    print(f"Using proxy: {proxy}")
    driver = get_webdriver(proxy)
    try:
        driver.get("https://www.google.com")
        
        search_box = driver.find_element(By.NAME, "q")
        search_box.send_keys(search_query)
        search_box.submit()
        time.sleep(3)  # wait for results to load
        
        # Lock the shared results list while appending
        with lock:
            first_result = driver.find_element(By.ID, "voiceSearchButton")
            results.append(f"First result title with proxy {proxy}: {first_result.text}")
        
    except Exception as e:
        with lock:
            results.append(f"Error with proxy {proxy}: {e}")
    finally:
        driver.quit()

# Function to handle threads
def google_search_thread(search_query):
    perform_google_search(search_query)

# Main function to start threads
def main(search_query):
    threads = []
    
    for _ in range(NUM_THREADS):
        thread = threading.Thread(target=google_search_thread, args=(search_query,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # Print results
    for result in results:
        print(result)

if __name__ == "__main__":
    query = "Selenium rotating proxy search"
    main(query)