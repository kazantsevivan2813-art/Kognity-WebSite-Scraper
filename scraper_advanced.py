"""
Advanced web scraper with improved selector handling and error recovery.
This version tries multiple selectors and provides better logging.
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
from selector_config import *

# Load environment variables
load_dotenv('config.env')

WEBSITE_URL = os.getenv('WEBSITE_URL')
EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD')
COOKIE_FILE = 'cookies.json'
COOKIE_EXPIRY_DAYS = 7


class AdvancedWebsiteScraper:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.base_download_path = Path('downloads')
        self.base_download_path.mkdir(exist_ok=True)
        self.log_file = self.base_download_path / 'scraper_log.txt'
        self.processed_classes = []
        self.filtered_classes = []
        
    def log(self, message, level='INFO'):
        """Log message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] [{level}] {message}"
        
        # Print to console with error handling for encoding issues
        try:
            print(log_msg)
        except UnicodeEncodeError:
            # Fallback for Windows console encoding issues
            print(log_msg.encode('ascii', 'replace').decode('ascii'))
        
        # Always write to file with UTF-8
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
        
    def setup_driver(self):
        """Initialize Chrome driver with options"""
        self.log("Setting up Chrome driver...")
        chrome_options = Options()
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Enable CDP for MHTML capture
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # Setup download preferences
        prefs = {
            'download.default_directory': str(self.base_download_path.absolute()),
            'download.prompt_for_download': False,
            'safebrowsing.enabled': True
        }
        chrome_options.add_experimental_option('prefs', prefs)
        
        driver_path = ChromeDriverManager().install()
        # Fix path if webdriver_manager returns wrong file
        if not driver_path.endswith('chromedriver.exe'):
            import os
            driver_dir = os.path.dirname(driver_path)
            actual_exe = os.path.join(driver_dir, 'chromedriver.exe')
            if os.path.exists(actual_exe):
                driver_path = actual_exe

        service = Service(driver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, WAIT_TIMES['element_load'])
        self.log("✓ Chrome driver ready")

    def find_element_with_fallbacks(self, selectors_list):
        """Try multiple selectors until one works"""
        for by_type, selector in selectors_list:
            try:
                element = self.wait.until(
                    EC.presence_of_element_located((by_type, selector))
                )
                return element
            except:
                continue
        return None
        
    def find_elements_with_fallbacks(self, selectors_list):
        """Try multiple selectors to find elements"""
        for by_type, selector in selectors_list:
            try:
                elements = self.driver.find_elements(by_type, selector)
                if elements:
                    return elements
            except:
                continue
        return []

    def safe_click(self, element, description="element"):
        """Safely click an element with multiple fallback strategies"""
        try:
            # Log element details
            try:
                tag = element.tag_name
                classes = element.get_attribute('class') or ''
                aria_label = element.get_attribute('aria-label') or ''
                self.log(f"  Attempting to click: <{tag}> class='{classes[:50]}' aria-label='{aria_label[:50]}'")
            except:
                pass
            
            # Check if element is displayed and enabled
            try:
                if not element.is_displayed():
                    self.log(f"  ⚠ Element not displayed", 'WARN')
                if not element.is_enabled():
                    self.log(f"  ⚠ Element not enabled", 'WARN')
            except:
                pass
            
            # Strategy 1: Scroll into view and wait, then normal click
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.5)
                element.click()
                self.log(f"  ✓ Clicked using normal click")
                return True
            except Exception as e1:
                self.log(f"  Strategy 1 failed: {str(e1)[:50]}")
            
            # Strategy 2: JavaScript click
            try:
                self.driver.execute_script("arguments[0].click();", element)
                self.log(f"  ✓ Clicked using JavaScript")
                return True
            except Exception as e2:
                self.log(f"  Strategy 2 failed: {str(e2)[:50]}")
            
            # Strategy 3: Remove aria-expanded and try click
            try:
                self.driver.execute_script("""
                    arguments[0].removeAttribute('aria-expanded');
                    arguments[0].removeAttribute('tabindex');
                    arguments[0].click();
                """, element)
                self.log(f"  ✓ Clicked after removing attributes")
                return True
            except Exception as e3:
                self.log(f"  Strategy 3 failed: {str(e3)[:50]}")
            
            # Strategy 4: Action chains
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(self.driver).move_to_element(element).click().perform()
                self.log(f"  ✓ Clicked using ActionChains")
                return True
            except Exception as e4:
                self.log(f"  Strategy 4 failed: {str(e4)[:50]}")
            
            # Strategy 5: Force click with JavaScript event
            try:
                self.driver.execute_script("""
                    var element = arguments[0];
                    var event = new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: true
                    });
                    element.dispatchEvent(event);
                """, element)
                self.log(f"  ✓ Clicked using MouseEvent dispatch")
                return True
            except Exception as e5:
                self.log(f"  Strategy 5 failed: {str(e5)[:50]}")
                
            self.log(f"✗ Could not click {description}", 'WARN')
            return False
            
        except Exception as e:
            self.log(f"✗ Error clicking {description}: {e}", 'WARN')
            return False
    
    def save_cookies(self):
        """Save cookies to file with timestamp"""
        cookies = self.driver.get_cookies()
        cookie_data = {
            'cookies': cookies,
            'timestamp': datetime.now().isoformat()
        }
        with open(COOKIE_FILE, 'w') as f:
            json.dump(cookie_data, f, indent=2)
        self.log("✓ Cookies saved")
        
    def load_cookies(self):
        """Load cookies from file if they exist and are not expired"""
        if not os.path.exists(COOKIE_FILE):
            return False
            
        try:
            with open(COOKIE_FILE, 'r') as f:
                cookie_data = json.load(f)
                
            # Check if cookies are expired
            saved_time = datetime.fromisoformat(cookie_data['timestamp'])
            age = datetime.now() - saved_time
            
            if age > timedelta(days=COOKIE_EXPIRY_DAYS):
                self.log(f"✗ Cookies expired ({age.days} days old)")
                return False
                
            # Load cookies
            self.driver.get(WEBSITE_URL)
            time.sleep(WAIT_TIMES['page_load'])
            
            for cookie in cookie_data['cookies']:
                if 'expiry' in cookie:
                    cookie['expiry'] = int(cookie['expiry'])
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    self.log(f"Warning: Could not add cookie: {e}", 'WARN')
                    
            self.log(f"✓ Cookies loaded ({age.days} days old)")
            return True
        except Exception as e:
            self.log(f"✗ Error loading cookies: {e}", 'ERROR')
            return False

    def login(self):
        """Login to the website (supports multi-step login)"""
        self.log("Attempting to login...")
        self.driver.get(WEBSITE_URL)
        time.sleep(WAIT_TIMES['page_load'])
        
        try:
            # Step 1: Find and fill email field
            email_field = self.find_element_with_fallbacks(LOGIN_SELECTORS['email_field'])
            if not email_field:
                self.log("✗ Could not find email field", 'ERROR')
                return False
                
            email_field.clear()
            email_field.send_keys(EMAIL)
            self.log("✓ Email entered")
            
            # Check if password field is on the same page
            password_field = None
            try:
                password_field = self.driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
                self.log("✓ Password field found on same page")
            except:
                # Multi-step login - need to click Continue/Next first
                self.log("Password field not on same page, looking for Continue button...")
                
                continue_button = self.find_element_with_fallbacks(LOGIN_SELECTORS['login_button'])
                if continue_button:
                    self.safe_click(continue_button, "Continue button")
                    time.sleep(WAIT_TIMES['page_load'])
                    self.log("✓ Moved to password page")
                else:
                    # Try pressing Enter
                    from selenium.webdriver.common.keys import Keys
                    email_field.send_keys(Keys.RETURN)
                    time.sleep(WAIT_TIMES['page_load'])
                    self.log("✓ Pressed Enter on email field")
            
            # Step 2: Find and fill password field (may be on new page)
            if not password_field:
                password_field = self.find_element_with_fallbacks(LOGIN_SELECTORS['password_field'])
                
            if not password_field:
                self.log("✗ Could not find password field", 'ERROR')
                return False
                
            password_field.clear()
            password_field.send_keys(PASSWORD)
            self.log("✓ Password entered")
            
            # Step 3: Find and click login button
            login_button = self.find_element_with_fallbacks(LOGIN_SELECTORS['login_button'])
            if login_button:
                self.safe_click(login_button, "Login button")
                self.log("✓ Login button clicked")
            else:
                # Try pressing Enter on password field
                from selenium.webdriver.common.keys import Keys
                password_field.send_keys(Keys.RETURN)
                self.log("✓ Pressed Enter on password field")
            
            # Wait for dashboard to load
            self.log("Waiting for dashboard to load...")
            time.sleep(WAIT_TIMES['after_login'])
            
            # Verify we're logged in
            current_url = self.driver.current_url
            if 'login' not in current_url.lower():
                self.log(f"✓ Login successful! Current URL: {current_url}")
                self.save_cookies()
                return True
            else:
                self.log(f"⚠ Still on login page: {current_url}", 'WARN')
                time.sleep(3)  # Extra wait in case of slow loading
                self.save_cookies()
                return True  # Try to continue anyway
            
        except Exception as e:
            self.log(f"✗ Login failed: {e}", 'ERROR')
            import traceback
            self.log(traceback.format_exc(), 'ERROR')
            return False
    def is_logged_in(self):
        """Check if user is currently logged in"""
        try:
            indicator = self.find_element_with_fallbacks(DASHBOARD_SELECTORS['logged_in_indicator'])
            return indicator is not None
        except:
            return False
    
    def ensure_logged_in(self):
        """Ensure user is logged in, using cookies if available"""
        # Try loading cookies first
        if self.load_cookies():
            self.driver.refresh()
            time.sleep(WAIT_TIMES['page_load'])
            
            # Log current page
            self.log(f"After cookie load, current URL: {self.driver.current_url}")
            
            # Check if we're logged in
            current_url = self.driver.current_url.lower()
            if 'login' not in current_url:
                self.log("✓ Using existing session (not on login page)")
                
                # Make sure we're on a page where we can find classes
                # For Kognity, ensure we're on the main app page
                if '/study/' in current_url or '/app/' in current_url:
                    self.log("✓ Already on study/app page")
                else:
                    # Navigate to the main page to see classes
                    self.log("Navigating to ensure classes are visible...")
                    # Try to find a home/dashboard link or just reload
                    self.driver.get(WEBSITE_URL)
                    time.sleep(WAIT_TIMES['page_load'])
                    self.log(f"Now at: {self.driver.current_url}")
                
                return True
            else:
                self.log("✗ Cookies invalid, still on login page")
                
        return self.login()
        
    def navigate_to_classes_page(self):
        """Ensure we're on a page where classes are visible"""
        try:
            current_url = self.driver.current_url.lower()
            
            # Check if we're already on a page with classes
            if 'class' in current_url or 'course' in current_url or 'dashboard' in current_url:
                self.log("✓ Already on a page with classes")
                return True
            
            # Try to find and click on a link to classes/courses/dashboard
            self.log("Looking for link to classes page...")
            possible_links = [
                (By.XPATH, '//a[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "class")]'),
                (By.XPATH, '//a[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "course")]'),
                (By.XPATH, '//a[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "dashboard")]'),
                (By.XPATH, '//a[contains(@href, "/classes")]'),
                (By.XPATH, '//a[contains(@href, "/courses")]'),
            ]
            
            for by_type, selector in possible_links:
                try:
                    link = self.driver.find_element(by_type, selector)
                    if link:
                        self.log(f"✓ Found link: {link.text}")
                        self.safe_click(link, "classes page link")
                        time.sleep(WAIT_TIMES['page_load'])
                        self.log(f"Navigated to: {self.driver.current_url}")
                        return True
                except:
                    continue
            
            # If no specific link found, just ensure we're at base URL
            if self.driver.current_url != WEBSITE_URL:
                self.log("Navigating to base URL...")
                self.driver.get(WEBSITE_URL)
                time.sleep(WAIT_TIMES['page_load'])
            
            return True
            
        except Exception as e:
            self.log(f"Error navigating to classes page: {e}", 'WARN')
            return False
if __name__ == "__main__":
    scraper = AdvancedWebsiteScraper()
    scraper.run()

