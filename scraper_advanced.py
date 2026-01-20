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
            
if __name__ == "__main__":
    scraper = AdvancedWebsiteScraper()
    scraper.run()

