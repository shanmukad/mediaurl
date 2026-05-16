import json
import time
from playwright.sync_api import sync_playwright

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

def test_login():
    # Set headless=False so you can see the browser
    with sync_playwright() as p:
        print("Starting browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Navigating to: {config['login_url']}")
        page.goto(config['login_url'])

        # Wait for fields to appear to ensure the page loaded
        page.wait_for_selector("#email")
        
        print("Filling fields...")
        page.fill("#email", config['username'])
        page.fill("#password", config['password'])
        
        print("Clicking submit...")
        page.click("button[type='submit']")
        
        # Give it a few seconds to load
        page.wait_for_load_state("networkidle")
        
        print(f"Current URL: {page.url}")
        
        # Keep browser open for 10 seconds so you can see the result
        time.sleep(10)
        browser.close()

if __name__ == "__main__":
    try:
        test_login()
    except Exception as e:
        print(f"An error occurred: {e}")