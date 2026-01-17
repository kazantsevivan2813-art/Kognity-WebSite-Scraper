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
            self.log("No cookie file found")
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
    
    def get_classes(self):
        """Get list of all classes from dashboard"""
        self.log("Fetching classes...")
        self.log(f"Current URL: {self.driver.current_url}")
        self.log(f"Page title: {self.driver.title}")
        
        try:
            # Ensure we're on the right page
            self.navigate_to_classes_page()
            
            # Wait for page to fully load
            time.sleep(3)
            
            # Scroll down to make sure all classes are loaded (for lazy loading)
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
            except:
                pass
            
            # Find class cards directly using ClassCard selector
            # Each class card is a clickable link with class containing "ClassCard"
            self.log("Finding class cards...")
            classes = []
            
            try:
                classes = self.driver.find_elements(By.CSS_SELECTOR, 'a[class*="ClassCard"]')
                if classes:
                    self.log(f"✓ Found {len(classes)} class cards")
            except Exception as e:
                self.log(f"⚠ CSS selector failed: {e}", 'WARN')
            
            # If not found, try XPath
            if not classes:
                self.log("Trying XPath selector...")
                try:
                    classes = self.driver.find_elements(By.XPATH, '//a[contains(@class, "ClassCard")]')
                    if classes:
                        self.log(f"✓ Found {len(classes)} class cards with XPath")
                except:
                    pass
            
            if not classes:
                self.log("✗ No class cards found", 'WARN')
                self.log("Saving page source for debugging...")
                debug_file = self.base_download_path / 'debug_no_classes.html'
                try:
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    self.log(f"Saved to: {debug_file.name}")
                except:
                    pass
                return []
            
            self.log(f"✓ Found {len(classes)} classes")
            # Log first 5 class names
            for i, cls in enumerate(classes[:5]):
                try:
                    # Try to get class name from ClassCard-className element
                    class_name_elem = cls.find_element(By.CSS_SELECTOR, '.ClassCard-className')
                    class_name = class_name_elem.text.strip()
                    self.log(f"   {i+1}. {class_name}")
                except:
                    # Fallback to full text
                    self.log(f"   {i+1}. {cls.text.strip()[:60]}")
            
            if len(classes) > 5:
                self.log(f"   ... and {len(classes) - 5} more")
                
            return classes
            
        except Exception as e:
            self.log(f"✗ Error fetching classes: {e}", 'ERROR')
            import traceback
            self.log(traceback.format_exc(), 'ERROR')
            return []
            
    def detect_navigation_structure(self):
        """Detect and analyze the navigation/tab structure on current page"""
        try:
            self.log("Analyzing page navigation structure...")
            
            # Try to find navigation items dynamically
            nav_items = []
            
            # Look for common Kognity patterns
            patterns = [
                (By.XPATH, '//nav//a | //nav//button'),
                (By.XPATH, '//header//a | //header//button'),
                (By.XPATH, '//*[@role="tab"]'),
                (By.XPATH, '//*[@role="navigation"]//a | //*[@role="navigation"]//button'),
                (By.CSS_SELECTOR, '[class*="tab"]'),
                (By.CSS_SELECTOR, '[class*="nav"]'),
            ]
            
            for by_type, selector in patterns:
                try:
                    elements = self.driver.find_elements(by_type, selector)
                    for elem in elements:
                        try:
                            text = elem.text.strip().lower()
                            if text and any(keyword in text for keyword in ['overview', 'book', 'practice', 'assignment', 'insight', 'study']):
                                nav_items.append({
                                    'element': elem,
                                    'text': text,
                                    'class': elem.get_attribute('class'),
                                    'tag': elem.tag_name
                                })
                        except:
                            continue
                except:
                    continue
            
            if nav_items:
                self.log(f"✓ Detected {len(nav_items)} navigation items:")
                for item in nav_items[:10]:
                    self.log(f"   • {item['text']} ({item['tag']}, class='{item['class']}')")
                return nav_items
            else:
                self.log("⚠ No navigation items detected", 'WARN')
                return []
                
        except Exception as e:
            self.log(f"✗ Error detecting navigation: {e}", 'ERROR')
            return []
    
    def find_tab_by_text(self, tab_name):
        """Try to find a tab by searching for its text content"""
        try:
            # Try exact match first
            selectors = [
                (By.XPATH, f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{tab_name.lower()}')]"),
                (By.XPATH, f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{tab_name.lower()}')]"),
                (By.XPATH, f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{tab_name.lower()}') and (self::a or self::button or self::div[@role='tab'])]"),
            ]
            
            for by_type, selector in selectors:
                try:
                    elements = self.driver.find_elements(by_type, selector)
                    for elem in elements:
                        # Make sure it's relatively small (not a large container)
                        if len(elem.text.strip()) < 50:
                            return elem
                except:
                    continue
                    
            return None
        except:
            return None
    
    def switch_to_tab(self, tab_name):
        """Switch to a specific tab with improved detection"""
        try:
            self.log(f"Switching to tab: {tab_name}")
            
            # First, try the specific Kognity class "NavbarCenterMenu-menuItem"
            tab = None
            try:
                # Find all elements with class NavbarCenterMenu-menuItem
                tab_elements = self.driver.find_elements(By.CSS_SELECTOR, '[class*="NavbarCenterMenu-menuItem"]')
                self.log(f"Found {len(tab_elements)} NavbarCenterMenu-menuItem elements")
                
                for elem in tab_elements:
                    try:
                        elem_text = elem.text.strip().lower()
                        if tab_name.lower() in elem_text:
                            tab = elem
                            self.log(f"✓ Found tab using NavbarCenterMenu-menuItem: {elem.text.strip()}")
                            break
                    except:
                        continue
            except Exception as e:
                self.log(f"Error searching NavbarCenterMenu-menuItem: {e}")
            
            # If not found, try configured selectors
            if not tab and tab_name in TAB_SELECTORS:
                for by_type, selector in TAB_SELECTORS[tab_name]:
                    try:
                        tab = self.wait.until(
                            EC.element_to_be_clickable((by_type, selector))
                        )
                        self.log(f"✓ Found tab using configured selector")
                        break
                    except:
                        continue
            
            # If not found, try finding by text
            if not tab:
                self.log(f"Trying text search...")
                tab = self.find_tab_by_text(tab_name)
                
            # If still not found, detect structure and try again
            if not tab:
                self.log(f"Analyzing page structure...")
                nav_items = self.detect_navigation_structure()
                
                # Try to find in detected items
                for item in nav_items:
                    if tab_name.lower() in item['text']:
                        tab = item['element']
                        self.log(f"✓ Found tab in detected navigation items")
                        break
            
            if not tab:
                self.log(f"✗ Could not find tab: {tab_name}", 'WARN')
                # Save page source for debugging
                debug_file = self.base_download_path / f'debug_missing_tab_{tab_name}.html'
                try:
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    self.log(f"Saved page source to: {debug_file.name}")
                except:
                    pass
                return False
            
            # Check if tab is already active
            try:
                class_attr = tab.get_attribute('class') or ''
                aria_selected = tab.get_attribute('aria-selected') or ''
                if 'active' in class_attr.lower() or 'selected' in class_attr.lower() or 'selected' in aria_selected.lower():
                    self.log(f"✓ Tab {tab_name} already active")
                    return True
            except:
                pass
            
            # Click the tab
            if self.safe_click(tab, f"tab '{tab_name}'"):
                time.sleep(WAIT_TIMES['after_click'])
                self.log(f"✓ Switched to {tab_name}")
                return True
            else:
                self.log(f"✗ Failed to click tab {tab_name}", 'ERROR')
                return False
            
        except Exception as e:
            self.log(f"✗ Error switching to tab {tab_name}: {e}", 'ERROR')
            return False
            
    def get_main_topics(self):
        """Get main topics using exact class 'TableOfContentsTopics-listItem containContent'"""
        try:
            self.log("Fetching main topics from Kognity TOC...")
            
            main_topics = []
            
            # First try: Use the EXACT class name provided by user
            try:
                # Find elements with both classes
                list_items = self.driver.find_elements(By.CSS_SELECTOR, '[class*="TableOfContentsTopics-listItem"][class*="containContent"]')
                self.log(f"Found {len(list_items)} elements with TableOfContentsTopics-listItem class")
                
                for elem in list_items:
                    try:
                        text = elem.text.strip()
                        self.log(f"  Topic text: {text[:80]}")
                        
                        # Filter: must have meaningful text and no dot in first word
                        if text and len(text) > 5:
                            words = text.split()
                            if words:
                                first_word = words[0]
                                # Main topics have no dot (unlike A1.1, 0.1)
                                if '.' not in first_word:
                                    # Find THE ACTUAL button with specific class
                                    clickable = None
                                    topic_name = None
                                    
                                    # Try 1: Find button with class "KogButtonLegacy--noStyle"
                                    try:
                                        buttons = elem.find_elements(By.XPATH, './/button[contains(@class, "KogButtonLegacy--noStyle")]')
                                        self.log(f"  Found {len(buttons)} KogButtonLegacy button(s)")
                                        
                                        if buttons:
                                            for idx, btn in enumerate(buttons):
                                                try:
                                                    aria_label = btn.get_attribute('aria-label') or ''
                                                    btn_classes = btn.get_attribute('class') or ''
                                                    
                                                    self.log(f"    Button {idx+1}: aria-label='{aria_label[:50]}'")
                                                    
                                                    if btn.is_displayed() and btn.is_enabled():
                                                        clickable = btn
                                                        # Extract topic name from aria-label (remove "Open " prefix)
                                                        if aria_label.startswith('Open '):
                                                            topic_name = aria_label[5:]  # Remove "Open "
                                                        else:
                                                            topic_name = aria_label or text
                                                        
                                                        self.log(f"  ✓ Selected KogButtonLegacy: {topic_name[:60]}")
                                                        break
                                                    else:
                                                        self.log(f"    ✗ Button not displayed/enabled")
                                                except Exception as be:
                                                    self.log(f"    ✗ Error checking button: {str(be)[:40]}")
                                                    continue
                                    except Exception as e:
                                        self.log(f"  ✗ Error finding KogButtonLegacy: {str(e)[:60]}")
                                    
                                    # Try 2: Find ANY button element (fallback)
                                    if not clickable:
                                        try:
                                            buttons = elem.find_elements(By.TAG_NAME, 'button')
                                            if buttons:
                                                for btn in buttons:
                                                    try:
                                                        if btn.is_displayed() and btn.is_enabled():
                                                            clickable = btn
                                                            aria_label = btn.get_attribute('aria-label') or ''
                                                            if aria_label.startswith('Open '):
                                                                topic_name = aria_label[5:]
                                                            else:
                                                                topic_name = text
                                                            self.log(f"  ✓ Found fallback button")
                                                            break
                                                    except:
                                                        continue
                                        except:
                                            pass
                                    
                                    # Try 3: Find any link element
                                    if not clickable:
                                        try:
                                            links = elem.find_elements(By.TAG_NAME, 'a')
                                            if links:
                                                for link in links:
                                                    try:
                                                        if link.is_displayed() and link.is_enabled():
                                                            clickable = link
                                                            topic_name = text
                                                            self.log(f"  ✓ Found link element")
                                                            break
                                                    except:
                                                        continue
                                        except:
                                            pass
                                    
                                    # If we found a clickable element, add it
                                    if clickable:
                                        try:
                                            if not topic_name:
                                                topic_name = text
                                            
                                            main_topics.append({
                                                'element': clickable,
                                                'text': topic_name
                                            })
                                            self.log(f"  ✓ Added main topic: {topic_name[:60]}")
                                        except Exception as e:
                                            self.log(f"  ✗ Error adding topic: {e}")
                                    else:
                                        self.log(f"  ✗ No clickable element found for: {text[:60]}")
                    except Exception as e:
                        self.log(f"  Error processing topic: {e}")
                        continue
                
                if main_topics:
                    self.log(f"✓ Found main topics using TableOfContentsTopics-listItem class")
                    
            except Exception as e:
                self.log(f"Error with TableOfContentsTopics-listItem selector: {e}")
            
            # Fallback: Try other patterns if specific class doesn't work
            if not main_topics:
                self.log("Trying fallback selectors...")
                fallback_patterns = [
                    (By.XPATH, '//aside//button[not(contains(text(), "."))]'),
                    (By.XPATH, '//nav//button[not(contains(text(), "."))]'),
                ]
                
                for by_type, selector in fallback_patterns:
                    try:
                        elements = self.driver.find_elements(by_type, selector)
                        self.log(f"  Fallback found {len(elements)} elements")
                        
                        for elem in elements:
                            try:
                                if elem.is_displayed():
                                    text = elem.text.strip()
                                    if text and len(text) > 5 and '.' not in text.split()[0]:
                                        main_topics.append({
                                            'element': elem,
                                            'text': text
                                        })
                                        self.log(f"  ✓ Added: {text[:60]}")
                            except:
                                continue
                        
                        if main_topics:
                            break
                    except:
                        continue
            
            # Remove duplicates
            seen = set()
            unique_topics = []
            for topic in main_topics:
                if topic['text'] not in seen:
                    seen.add(topic['text'])
                    unique_topics.append(topic)
            
            if unique_topics:
                self.log(f"✓ Found {len(unique_topics)} unique main topics:")
                for i, topic in enumerate(unique_topics[:10]):
                    self.log(f"   {i+1}. {topic['text'][:60]}")
            
            return unique_topics
            
        except Exception as e:
            self.log(f"✗ Error fetching main topics: {e}", 'ERROR')
            import traceback
            self.log(traceback.format_exc(), 'ERROR')
            return []
             
    def get_sections_for_subtopic(self, subtopic_element):
        """Get sections list within SubjectOverviewSubtopic element"""
        try:
            self.log("      Looking for sections list within SubjectOverviewSubtopic...")
            
            section_items = []
            
            # Find sections list with lang="en" and class="list-style-none" within this SubjectOverviewSubtopic element
            try:
                # Try to find list within the subtopic element using both lang="en" AND class="list-style-none"
                lists = subtopic_element.find_elements(By.CSS_SELECTOR, '[lang="en"].list-style-none, [lang="en"][class*="list-style-none"]')
                
                for lst in lists:
                    try:
                        # Find clickable items (li, button, a)
                        items = lst.find_elements(By.XPATH, './/li | .//button | .//a')
                        
                        for item in items:
                            try:
                                text = item.text.strip()
                                # Filter for items that look like sections (have some content)
                                if text and len(text) > 3:
                                    # Find clickable element within
                                    clickable = None
                                    try:
                                        clickable = item.find_element(By.XPATH, './/button | .//a')
                                        if not clickable.is_displayed():
                                            clickable = None
                                    except:
                                        pass
                                    
                                    # If no clickable child, use item itself if it's clickable
                                    if not clickable:
                                        if item.tag_name in ['button', 'a', 'li'] and item.is_displayed():
                                            clickable = item
                                    
                                    if clickable:
                                        section_items.append({
                                            'element': clickable,
                                            'text': text
                                        })
                            except:
                                continue
                        
                        # If we found sections in this list, stop searching
                        if section_items:
                            break
                    except:
                        continue
                
                if section_items:
                    self.log(f"      ✓ Found {len(section_items)} sections within SubjectOverviewSubtopic")
                else:
                    self.log("      ⚠ No sections list found within SubjectOverviewSubtopic")
                    
            except Exception as e:
                self.log(f"      Error searching for sections: {e}")
            
            if section_items:
                self.log(f"      ✓ Found {len(section_items)} sections (will use FIRST only):")
                for i, item in enumerate(section_items[:3]):
                    self.log(f"         {i+1}. {item['text'][:60]}")
            
            return section_items
            
        except Exception as e:
            self.log(f"      ✗ Error finding sections for subtopic: {e}")
            return []
          
    def sanitize_folder_name(self, name):
        """Sanitize folder name by removing invalid characters"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        # Remove extra whitespace
        name = ' '.join(name.split())
        # Limit length
        if len(name) > 100:
            name = name[:100]
        return name.strip()
    
    def expand_all_collapsible_sections(self):
        """Click all collapsible toggle buttons and show solution buttons to expand hidden content before saving"""
        try:
            total_clicked = 0
            
            # Type 1: Collapsible toggle buttons
            collapsible_buttons = self.driver.find_elements(
                By.CSS_SELECTOR, 
                'button.KogButton.inline-block.KogButton--basic.KogButton--medium.collapsible-toggle'
            )
            
            # Type 2: Show solution buttons
            solution_buttons = self.driver.find_elements(
                By.CSS_SELECTOR,
                'button.KogButton.inline-block.KogButton--default-fill.KogButton--medium.js-showsolution-toggle'
            )
            
            # Combine all buttons
            all_buttons = collapsible_buttons + solution_buttons
            
            if all_buttons:
                self.log(f"  Found {len(collapsible_buttons)} collapsible toggles and {len(solution_buttons)} solution buttons")
                
                for idx, button in enumerate(all_buttons):
                    try:
                        # Scroll button into view
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(0.2)
                        
                        # Check if button is displayed and clickable
                        if button.is_displayed() and button.is_enabled():
                            # Click using JavaScript to avoid interception issues
                            self.driver.execute_script("arguments[0].click();", button)
                            total_clicked += 1
                            time.sleep(0.1)  # Small delay between clicks
                    except Exception as e:
                        # Continue even if one button fails
                        pass
                
                if total_clicked > 0:
                    self.log(f"  ✓ Expanded {total_clicked} sections (collapsibles + solutions)")
                    time.sleep(0.5)  # Wait for content to expand
                else:
                    self.log(f"  No sections needed expanding")
            else:
                self.log(f"  No expandable sections found on page")
                
        except Exception as e:
            self.log(f"  ⚠ Error expanding sections: {e}", 'WARN')
        
    def save_page_as_mhtml(self, folder_path, filename):
        """Save current page as MHTML using browser's native save functionality"""
        folder_path = Path(folder_path)
        folder_path.mkdir(parents=True, exist_ok=True)
        
        # Sanitize filename
        filename = self.sanitize_folder_name(filename)
        if not filename.endswith('.mhtml'):
            filename += '.mhtml'
            
        filepath = folder_path / filename
        
        try:
            self.log(f"Saving MHTML: {filename}")
            self.log(f"  URL: {self.driver.current_url}")
            self.log(f"  Path: {filepath}")
            
            # Wait a moment for page to fully load
            time.sleep(1)
            
            # Expand all collapsible sections before saving
            self.expand_all_collapsible_sections()
            
            # Method 1: Use Chrome's native save-as functionality via keyboard
            try:
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.common.action_chains import ActionChains
                import pyautogui
                import shutil
                
                # Get the body element to send keys to
                body = self.driver.find_element(By.TAG_NAME, 'body')
                
                # Set up Chrome's default download directory for this save
                # We'll move the file after it's saved
                temp_download_path = Path.home() / 'Downloads'
                
                self.log("Triggering browser's Save As dialog...")
                
                # Send Ctrl+S to open Save As dialog
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('s').key_up(Keys.CONTROL).perform()
                time.sleep(2)  # Wait for dialog to open
                
                # The dialog should now be open
                # Type the filename
                pyautogui.write(str(filepath.absolute()), interval=0.05)
                time.sleep(0.5)
                
                # Press Tab to move to format dropdown (if needed)
                # Then press Enter to save
                pyautogui.press('enter')
                time.sleep(2)  # Wait for save to complete
                
                # Check if file was created
                if filepath.exists() and filepath.stat().st_size > 0:
                    file_size = filepath.stat().st_size / 1024  # KB
                    self.log(f"✓ Saved: {filepath.name} ({file_size:.1f} KB)")
                    return True
                else:
                    self.log(f"✗ File not found after save attempt", 'WARN')
                    
            except ImportError:
                self.log("pyautogui not installed, trying alternative method...", 'WARN')
            except Exception as dialog_error:
                self.log(f"✗ Dialog method failed: {dialog_error}", 'WARN')
            
            # Method 2: Use Chrome DevTools Protocol - Produces valid MHTML for offline viewing
            try:
                self.log("Using Chrome DevTools Protocol to capture MHTML...")
                
                # Wait for page to fully render
                time.sleep(1)
                
                # Execute CDP command to capture page as MHTML
                result = self.driver.execute_cdp_cmd('Page.captureSnapshot', {'format': 'mhtml'})
                
                if result and 'data' in result:
                    mhtml_data = result['data']
                    
                    # Verify MHTML header is present (should start with MIME-Version)
                    if not mhtml_data.startswith('MIME-Version:'):
                        self.log("⚠ Warning: MHTML data doesn't have proper header", 'WARN')
                    
                    # Write MHTML file with UTF-8 encoding
                    with open(filepath, 'w', encoding='utf-8', newline='') as f:
                        f.write(mhtml_data)
                    
                    # Verify file was created and has valid content
                    if filepath.exists() and filepath.stat().st_size > 0:
                        file_size = filepath.stat().st_size / 1024  # KB
                        
                        # Additional validation: check if MHTML is well-formed
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                first_line = f.readline()
                                if 'MIME-Version:' in first_line:
                                    self.log(f"✓ Saved valid MHTML: {filepath.name} ({file_size:.1f} KB)")
                                    self.log(f"  Can be opened offline in Chrome/Edge")
                                    return True
                                else:
                                    self.log(f"⚠ MHTML saved but format may be invalid", 'WARN')
                                    return True  # Still return True as file was saved
                        except:
                            # If validation fails, still return True as file exists
                            self.log(f"✓ Saved MHTML: {filepath.name} ({file_size:.1f} KB)")
                            return True
                    else:
                        self.log(f"✗ File was created but is empty", 'WARN')
                else:
                    self.log(f"✗ CDP command returned no data", 'WARN')
                    
            except Exception as cdp_error:
                self.log(f"✗ CDP method failed: {cdp_error}", 'WARN')
            
            # Method 3: Fallback to saving as HTML
            self.log(f"Falling back to HTML save...")
            html_filepath = filepath.with_suffix('.html')
            
            try:
                page_source = self.driver.page_source
                with open(html_filepath, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                
                if html_filepath.exists() and html_filepath.stat().st_size > 0:
                    file_size = html_filepath.stat().st_size / 1024  # KB
                    self.log(f"✓ Saved as HTML: {html_filepath.name} ({file_size:.1f} KB)")
                    return True
                    
            except Exception as html_error:
                self.log(f"✗ HTML fallback also failed: {html_error}", 'ERROR')
            
            return False
            
        except Exception as e:
            self.log(f"✗ Error saving page: {e}", 'ERROR')
            import traceback
            self.log(traceback.format_exc(), 'ERROR')
            return False
            
    def process_all_subtopics(self, main_folder, main_topic_text=None):
        """
        All-in-one function to process SubjectOverviewSubtopic items.
        
        Flow:
        1. Find all SubjectOverviewSubtopic items on right side
        2. For each item:
           - Get subtopic name from header
           - Find sections list within the item
           - Click FIRST section item
           - Save new page to main topic folder with subtopic name
        
        Args:
            main_folder: Folder to save content to
            main_topic_text: Text of the main topic to re-find button if needed (optional)
        """
        try:
            self.log("  Processing SubjectOverviewSubtopic items...")
            time.sleep(1)
            
            # STEP 1: Find all SubjectOverviewSubtopic elements
            subtopic_elements = self.driver.find_elements(By.CSS_SELECTOR, '[class*="SubjectOverviewSubtopic"]')
            self.log(f"  Found {len(subtopic_elements)} SubjectOverviewSubtopic elements\n")
            
            if not subtopic_elements:
                self.log("  ⚠ No SubjectOverviewSubtopic items found")
                return
            
            # STEP 2: Process ALL SubjectOverviewSubtopic items in this main topic
            total_count = len(subtopic_elements)
            self.log(f"  Starting to process {total_count} SubjectOverviewSubtopic items (idx 0 to {total_count-1})\n")
            
            for idx in range(total_count):
                try:
                    self.log(f"  ─────────────────────────────────────")
                    self.log(f"  Processing index {idx} (item {idx+1}/{total_count})")
                    
                    # Re-fetch SubjectOverviewSubtopic elements to avoid stale element issues
                    # This is important after returning from new tabs
                    subtopic_elements_fresh = self.driver.find_elements(By.CSS_SELECTOR, '[class*="SubjectOverviewSubtopic"]')
                    self.log(f"  Re-fetched {len(subtopic_elements_fresh)} SubjectOverviewSubtopic elements")
                    
                    # If subtopics disappeared after going back, try to re-click the main topic button
                    if len(subtopic_elements_fresh) == 0 and main_topic_text is not None and idx > 0:
                        self.log(f"  ⚠ Subtopics disappeared after navigation, attempting to re-click main topic...")
                        self.log(f"  ℹ Looking for button with text: '{main_topic_text}'")
                        try:
                            # Re-find the main topic button using its text (to avoid stale element)
                            # Try multiple approaches to find the button
                            main_topic_button = None
                            
                            # Approach 1: Find by exact aria-label match
                            try:
                                # Escape quotes in the text for XPath
                                escaped_text = main_topic_text.replace("'", "\\'")
                                buttons = self.driver.find_elements(By.XPATH, 
                                    f"//button[contains(@class, 'KogButtonLegacy') and @aria-label='{escaped_text}']")
                                if buttons:
                                    main_topic_button = buttons[0]
                                    self.log(f"  ✓ Found using exact aria-label match")
                            except:
                                pass
                            
                            # Approach 2: Find by aria-label containing text (handles "Open " prefix)
                            if not main_topic_button:
                                try:
                                    buttons = self.driver.find_elements(By.XPATH, 
                                        f"//button[contains(@class, 'KogButtonLegacy') and contains(@aria-label, '{main_topic_text[:20]}')]")
                                    if buttons:
                                        main_topic_button = buttons[0]
                                        self.log(f"  ✓ Found using partial aria-label match")
                                except:
                                    pass
                            
                            # Approach 3: Find all KogButtonLegacy buttons and match by visible text
                            if not main_topic_button:
                                try:
                                    all_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button[class*="KogButtonLegacy"]')
                                    for btn in all_buttons:
                                        if main_topic_text[:15] in btn.text or main_topic_text[:15] in btn.get_attribute('aria-label'):
                                            main_topic_button = btn
                                            self.log(f"  ✓ Found by searching all buttons")
                                            break
                                except:
                                    pass
                            
                            if main_topic_button:
                                self.log(f"  ✓ Re-found main topic button")
                                
                                # Scroll to main topic button
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", main_topic_button)
                                time.sleep(0.5)
                                
                                # Re-click main topic button
                                if self.safe_click(main_topic_button, "main topic (re-click)"):
                                    self.log(f"  ✓ Re-clicked main topic button")
                                    time.sleep(WAIT_TIMES['after_click'] + 1)
                                    
                                    # Re-fetch again
                                    subtopic_elements_fresh = self.driver.find_elements(By.CSS_SELECTOR, '[class*="SubjectOverviewSubtopic"]')
                                    self.log(f"  Re-fetched {len(subtopic_elements_fresh)} SubjectOverviewSubtopic elements after re-click")
                                else:
                                    self.log(f"  ✗ Failed to re-click main topic button")
                            else:
                                self.log(f"  ✗ Could not re-find main topic button with any method")
                        except Exception as e:
                            self.log(f"  ✗ Error re-clicking main topic: {str(e)[:60]}")
                    
                    if idx >= len(subtopic_elements_fresh):
                        self.log(f"  ⚠ Item {idx+1} not found after re-fetch (idx={idx}, fresh count={len(subtopic_elements_fresh)})")
                        continue
                    
                    subtopic_elem = subtopic_elements_fresh[idx]
                    
                    # Scroll element into view to ensure it's visible
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", subtopic_elem)
                        time.sleep(0.3)
                    except:
                        pass
                    
                    # Get subtopic name from header
                    try:
                        header = subtopic_elem.find_element(By.CSS_SELECTOR, '[class*="SubjectOverviewSubtopic-headerContent"]')
                        subtopic_text = header.text.strip()
                    except:
                        # Fallback: use first line of element text
                        subtopic_text = subtopic_elem.text.strip().split('\n')[0]
                    
                    if not subtopic_text or len(subtopic_text) < 3:
                        self.log(f"  ⚠ Skipping item {idx+1}: no valid subtopic text")
                        continue
                    
                    self.log(f"  [{idx+1}/{total_count}] Subtopic: {subtopic_text}")
                    self.log(f"  ✓ Got subtopic name for item at index {idx}")
                    
                    # Find sections list with lang="en" and class="list-style-none" within this SubjectOverviewSubtopic element
                    section_items = []
                    try:
                        # Look for elements with both lang="en" AND class="list-style-none"
                        sections_lists = subtopic_elem.find_elements(By.CSS_SELECTOR, '[lang="en"].list-style-none, [lang="en"][class*="list-style-none"]')
                        self.log(f"    Found {len(sections_lists)} sections lists (lang='en' + list-style-none)")
                        
                        for lst in sections_lists:
                            # Get all list items
                            items = lst.find_elements(By.XPATH, './/li | .//button | .//a')
                            self.log(f"    Found {len(items)} items in sections list")
                            
                            for item in items:
                                try:
                                    text = item.text.strip()
                                    if text and len(text) > 3:
                                        # Find clickable element (button or link)
                                        clickable = None
                                        try:
                                            clickable = item.find_element(By.XPATH, './/button | .//a')
                                            if not clickable.is_displayed():
                                                clickable = None
                                        except:
                                            pass
                                        
                                        # If no clickable child, use item itself if it's clickable
                                        if not clickable:
                                            if item.tag_name in ['button', 'a', 'li'] and item.is_displayed():
                                                clickable = item
                                        
                                        if clickable:
                                            section_items.append({
                                                'element': clickable,
                                                'text': text
                                            })
                                except:
                                    continue
                            
                            # If we found sections in this list, stop searching
                            if section_items:
                                break
                    except Exception as e:
                        self.log(f"    Error finding list-style-none: {e}")
                    
                    if not section_items:
                        self.log(f"    ⚠ No sections list found")
                        continue
                    
                    self.log(f"    Found {len(section_items)} sections, clicking FIRST item")
                    
                    # Click FIRST section item (opens in new tab)
                    first_section = section_items[0]
                    section_text = first_section['text']
                    self.log(f"    → About to click first section for index {idx}: {section_text[:60]}")
                    
                    # Remember original window handle (BEFORE clicking)
                    original_window = self.driver.current_window_handle
                    original_windows = self.driver.window_handles
                    original_count = len(original_windows)
                    self.log(f"    Current tabs before click: {original_count}")
                    
                    # Scroll element into view
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_section['element'])
                        time.sleep(0.5)
                    except:
                        pass
                    
                    # Force opening in new tab using Ctrl+Click (or Command+Click on Mac)
                    try:
                        from selenium.webdriver.common.action_chains import ActionChains
                        from selenium.webdriver.common.keys import Keys
                        
                        # Try Ctrl+Click (Windows/Linux) or Command+Click (Mac)
                        action = ActionChains(self.driver)
                        action.key_down(Keys.CONTROL).click(first_section['element']).key_up(Keys.CONTROL).perform()
                        self.log(f"    ✓ Ctrl+Clicked section to open in new tab")
                    except Exception as e:
                        self.log(f"    ⚠ Ctrl+Click failed, trying JavaScript: {str(e)[:50]}")
                        # Fallback: Use JavaScript to modify link and click
                        try:
                            self.driver.execute_script("""
                                var element = arguments[0];
                                // If it's a link, set target to _blank
                                if (element.tagName === 'A' || element.closest('a')) {
                                    var link = element.tagName === 'A' ? element : element.closest('a');
                                    link.setAttribute('target', '_blank');
                                }
                                element.click();
                            """, first_section['element'])
                            self.log(f"    ✓ JavaScript click with target=_blank")
                        except Exception as e2:
                            self.log(f"    ✗ Could not click section: {e2}")
                            continue
                    
                    # Wait for new tab/window to open (check multiple times)
                    self.log(f"    ✓ Clicked, checking for new tab...")
                    new_tab_opened = False
                    for attempt in range(5):  # Check 5 times over 5 seconds
                        time.sleep(1)
                        new_windows = self.driver.window_handles
                        new_count = len(new_windows)
                        if new_count > original_count:
                            new_tab_opened = True
                            self.log(f"    ✓ New tab detected! Tabs: {original_count} → {new_count}")
                            break
                    
                    if not new_tab_opened:
                        self.log(f"    ⚠ No new tab opened after 5 seconds")
                    
                    # Process based on whether new tab opened
                    new_windows = self.driver.window_handles
                    if len(new_windows) > len(original_windows):
                        # New tab opened - switch to itBased on the change to copy role and studio the in transit status is another step that doesn’t exist
                        new_window = [w for w in new_windows if w not in original_windows][0]
                        self.driver.switch_to.window(new_window)
                        self.log(f"    ✓ Switched to new tab")
                        
                        # Wait for page to load
                        time.sleep(WAIT_TIMES['page_load'] + 2)
                        
                        # Click close button to hide sidebar/panel before saving
                        try:
                            close_button = self.driver.find_element(By.CSS_SELECTOR, '[class*="BookRailToc-topicHeadlineCloseButton"]')
                            if close_button.is_displayed():
                                close_button.click()
                                self.log(f"    ✓ Clicked BookRailToc-topicHeadlineCloseButton")
                                time.sleep(0.5)
                        except Exception as e:
                            self.log(f"    ⚠ Close button not found or not clickable: {str(e)[:50]}")
                        
                        # Save page with subtopic name
                        # Clean and deduplicate the subtopic text
                        # Example: "SUBTOPIC 1.1\n1.1, Tool 1: Experimental techniques\nTool 1: Experimental techniques"
                        # Should become: "1.1, Tool 1: Experimental techniques"
                        lines = [line.replace('SUBTOPIC ', '').replace('subtopic ', '').strip() 
                                for line in subtopic_text.split('\n') if line.strip()]
                        # Remove duplicates: keep only the most complete/longest line
                        if lines:
                            # Find the longest line (most descriptive)
                            filename = max(lines, key=len)
                        else:
                            filename = subtopic_text.strip()
                        filename = self.sanitize_folder_name(filename).replace(' ', '_')
                        
                        self.log(f"    Saving as: {filename}.mhtml")
                        success = self.save_page_as_mhtml(main_folder, filename)
                        
                        if success:
                            self.log(f"    ✓ Saved successfully")
                        else:
                            self.log(f"    ✗ Failed to save")
                        
                        # Close new tab
                        self.log(f"    Closing new tab...")
                        self.driver.close()
                        
                        # Switch back to original tab
                        self.driver.switch_to.window(original_window)
                        self.log(f"    ✓ Returned to original tab\n")
                        time.sleep(1)
                    else:
                        # No new tab - same tab navigation
                        self.log(f"    ⚠ No new tab opened, page loaded in same tab")
                        time.sleep(WAIT_TIMES['page_load'] + 2)
                        
                        # Save page
                        # Clean and deduplicate the subtopic text
                        lines = [line.replace('SUBTOPIC ', '').replace('subtopic ', '').strip() 
                                for line in subtopic_text.split('\n') if line.strip()]
                        # Remove duplicates: keep only the most complete/longest line
                        if lines:
                            # Find the longest line (most descriptive)
                            filename = max(lines, key=len)
                        else:
                            filename = subtopic_text.strip()
                        filename = self.sanitize_folder_name(filename).replace(' ', '_')
                        
                        self.log(f"    Saving as: {filename}.mhtml")
                        success = self.save_page_as_mhtml(main_folder, filename)
                        
                        if success:
                            self.log(f"    ✓ Saved successfully")
                        else:
                            self.log(f"    ✗ Failed to save")
                        
                        # Go back to original page
                        self.log(f"    Going back...")
                        self.driver.back()
                        time.sleep(WAIT_TIMES['after_click'] + 2)
                        
                        # Wait for page to stabilize and check if we're back
                        try:
                            # Wait for the table of contents to be visible again
                            time.sleep(1)
                            self.driver.execute_script("window.scrollTo(0, 0);")  # Scroll to top
                        except:
                            pass
                        
                        self.log(f"    ✓ Returned to original page\n")
                        
                except Exception as e:
                    self.log(f"    ✗ Error with subtopic: {e}")
                    import traceback
                    self.log(traceback.format_exc(), 'ERROR')
                    # Try to return to original window if something went wrong
                    try:
                        current_windows = self.driver.window_handles
                        if len(current_windows) > 1:
                            # Close extra windows
                            for window in current_windows[1:]:
                                try:
                                    self.driver.switch_to.window(window)
                                    self.driver.close()
                                except:
                                    pass
                            # Switch back to first window
                            self.driver.switch_to.window(current_windows[0])
                    except:
                        pass
                    continue
            
            self.log(f"  ✓ Completed processing SubjectOverviewSubtopic items")
            
        except Exception as e:
            self.log(f"  ✗ Error in process_all_subtopics: {e}", 'ERROR')
            import traceback
            self.log(traceback.format_exc(), 'ERROR')
    
    def process_subtopic_box(self, subtopic_item, main_folder):
        """
        Process a single SubjectOverviewSubtopic item.
        Each item contains: subtopic header + sections list
        
        Flow:
        1. Get subtopic name from the item
        2. Find sections list within the item
        3. Click FIRST section item
        4. Save new page to main topic folder with subtopic name
        
        Structure: MainTopic/subtopic_name.mhtml
        Example: A1 Unity and diversity Molecules/0.1,_Water.mhtml
        """
        try:
            subtopic_text = subtopic_item['text']
            self.log(f"\n    → SubjectOverviewSubtopic: {subtopic_text}")
            
            # DON'T create subtopic folder - save directly in main topic folder
            # DON'T click the subtopic header - it's not clickable!
            
            # Find the sections list within this SubjectOverviewSubtopic element
            section_items = self.get_sections_for_subtopic(subtopic_item['element'])
            
            if not section_items:
                self.log("      ⚠ No section items found for this subtopic")
                return
            
            self.log(f"      Found {len(section_items)} section items")
            
            # Click FIRST section item only
            first_section = section_items[0]
            section_text = first_section['text']
            self.log(f"      → Clicking first section: {section_text}")
            
            try:
                # Get current URL before clicking
                url_before = self.driver.current_url
                
                # Scroll into view
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_section['element'])
                    time.sleep(0.5)
                except:
                    pass
                
                # Click first section - this should navigate to a NEW PAGE
                clicked = self.safe_click(first_section['element'], f"section '{section_text}'")
                
                if not clicked:
                    self.log(f"      ✗ Could not click section")
                    return
                
                # Wait for navigation to complete
                self.log(f"      ✓ Clicked, waiting for NEW PAGE to load...")
                time.sleep(WAIT_TIMES['page_load'])  # Longer wait for page navigation
                
                # Verify URL changed (navigation occurred)
                url_after = self.driver.current_url
                if url_after != url_before:
                    self.log(f"      ✓ Navigation detected:")
                    self.log(f"         Before: {url_before}")
                    self.log(f"         After:  {url_after}")
                else:
                    self.log(f"      ⚠ URL unchanged, but proceeding...")
                
                # Additional wait to ensure page is fully loaded
                time.sleep(2)
                
                # NOW save the NEW PAGE with subtopic name directly in main topic folder
                # Clean up the subtopic text for filename (remove "SUBTOPIC X.X" prefix if present)
                filename = subtopic_text.replace('SUBTOPIC ', '').replace('subtopic ', '').strip()
                filename = self.sanitize_folder_name(filename).replace(' ', '_')
                
                self.log(f"      Saving NEW PAGE as {filename}.mhtml in main topic folder...")
                success = self.save_page_as_mhtml(main_folder, filename)
                
                if success:
                    self.log(f"      ✓ Saved {filename}.mhtml successfully\n")
                else:
                    self.log(f"      ✗ Failed to save\n")
                    
            except Exception as e:
                self.log(f"      ✗ Error: {e}", 'ERROR')
                
        except Exception as e:
            self.log(f"    ✗ Error processing subtopic: {e}", 'ERROR')
            import traceback
            self.log(traceback.format_exc(), 'ERROR')
    
    def process_main_topic(self, main_topic, tab_folder):
        """
        Process a main topic (e.g., "A1 Unity and diversity: Molecules").
        Flow: Click button FIRST → Create folder → Find subtopics → Process each
        """
        try:
            topic_text = main_topic['text']
            self.log(f"\n  ══ Main Topic: {topic_text}")
            
            # FIRST: Click the main topic button to load content on right side
            button_element = main_topic['element']
            
            # Scroll into view and click
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button_element)
                time.sleep(0.5)
            except:
                pass
            
            if not self.safe_click(button_element, f"main topic '{topic_text}'"):
                self.log(f"  ✗ Could not click main topic button")
                return
            
            self.log(f"  ✓ Clicked main topic button")
            time.sleep(WAIT_TIMES['after_click'] + 2)  # Wait for right side to load
            
            # SECOND: Create folder for main topic (after clicking)
            topic_folder = tab_folder / self.sanitize_folder_name(topic_text)
            topic_folder.mkdir(exist_ok=True)
            self.log(f"  ✓ Created folder: {topic_folder.name}")
            
            # THIRD: Process all SubjectOverviewSubtopic items (all in one function)
            # Pass the topic text so button can be re-found and re-clicked if subtopics disappear
            self.process_all_subtopics(topic_folder, topic_text)
                    
        except Exception as e:
            self.log(f"✗ Error processing main topic: {e}", 'ERROR')
            import traceback
            self.log(traceback.format_exc(), 'ERROR')
            
    def process_tab(self, tab_name, class_folder):
        """Process a single tab with two-level hierarchy (Main Topics → Sub-items)"""
        self.log(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        self.log(f"   Processing tab: {tab_name.upper()}")
        self.log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        
        try:
            # Switch to the tab
            if not self.switch_to_tab(tab_name):
                self.log(f"✗ Could not switch to tab {tab_name}, skipping")
                return
            
            time.sleep(WAIT_TIMES['after_click'])
            
            # Create folder for the tab
            tab_folder = class_folder / tab_name
            tab_folder.mkdir(exist_ok=True)
            self.log(f"✓ Tab folder: {tab_folder.name}\n")
            
            # Get main topics (0, 1, A1, A2, etc.) - get count first
            main_topics_initial = self.get_main_topics()
            
            if not main_topics_initial:
                self.log(f"⚠ No main topics found in {tab_name} tab", 'WARN')
                self.save_page_as_mhtml(tab_folder, f"{tab_name}_content")
                return
            
            total_topics = len(main_topics_initial)
            self.log(f"Total: {total_topics} main topics to process\n")
            
            # Process each main topic BY INDEX (to avoid stale elements)
            for idx in range(total_topics):
                try:
                    self.log(f"[{idx+1}/{total_topics}]")
                    
                    # Re-fetch main topics to avoid stale element references
                    self.log(f"  Re-fetching main topics to avoid stale elements...")
                    main_topics_fresh = self.get_main_topics()
                    
                    if not main_topics_fresh or idx >= len(main_topics_fresh):
                        self.log(f"  ⚠ Main topic {idx+1} not found after re-fetch (idx={idx}, count={len(main_topics_fresh)})")
                        continue
                    
                    main_topic = main_topics_fresh[idx]
                    self.log(f"  ✓ Got fresh element for topic: {main_topic['text']}")
                    
                    self.process_main_topic(main_topic, tab_folder)
                    
                except Exception as e:
                    self.log(f"✗ Error processing main topic: {e}", 'ERROR')
                    import traceback
                    self.log(traceback.format_exc(), 'ERROR')
                    continue
            
            self.log(f"\n✓ Completed tab: {tab_name.upper()}\n")
                    
        except Exception as e:
            self.log(f"✗ Error processing tab {tab_name}: {e}", 'ERROR')
            import traceback
            self.log(traceback.format_exc(), 'ERROR')
            
    def process_class(self, class_element, class_index):
        """Process a single class"""
        try:
            # Get initial class name for logging (temporary, will be updated after clicking)
            initial_class_name = None
            try:
                # Try to find the specific element with ClassCard-className
                class_name_elem = class_element.find_element(By.CSS_SELECTOR, '.ClassCard-className')
                initial_class_name = class_name_elem.text.strip()
            except:
                pass
            
            # Fallback to full text if specific element not found
            if not initial_class_name:
                initial_class_name = class_element.text.strip().split('\n')[0].strip()
            
            if not initial_class_name:
                initial_class_name = f"Class_{class_index + 1}"
                
            # Filter: Only process specific subjects
            allowed_subjects = ['Mathematics', 'Physics', 'Chemistry', 'Biology', 'Theory of knowledge']
            should_process = any(subject.lower() in initial_class_name.lower() for subject in allowed_subjects)
            
            if not should_process:
                self.log(f"\n{'='*60}")
                self.log(f"Skipping Class {class_index + 1}/25: {initial_class_name}")
                self.log(f"[FILTERED] Not a target subject (Mathematics/Physics/Chemistry/Biology/Theory of knowledge)")
                self.log(f"{'='*60}")
                self.filtered_classes.append(initial_class_name)
                return
            
            self.log(f"\n{'='*60}")
            self.log(f"Processing Class {class_index + 1}/25: {initial_class_name}")
            self.log(f"✓ Matches filter - Processing this class")
            self.log(f"{'='*60}")
            
            # Click on class using safe click
            if not self.safe_click(class_element, f"class '{initial_class_name}'"):
                self.log(f"✗ Could not click on class, skipping")
                return
            
            # Wait for URL to change from dashboard to class page
            # Dashboard URL: https://app.kognity.com/study/app/dashboard
            # Class URL: https://app.kognity.com/study/app/class-ib-dp-biology-slhl-fe2025/sid-422-cid-706250/overview/
            self.log("Waiting for page to navigate to class...")
            
            # Initial delay to allow click to register
            time.sleep(2)
            
            try:
                from selenium.webdriver.support import expected_conditions as EC
                # Wait up to 15 seconds for URL to contain 'sid-' (indicating class page)
                wait_long = WebDriverWait(self.driver, 15)
                wait_long.until(lambda driver: 'sid-' in driver.current_url)
                self.log("✓ URL changed to class page")
            except Exception as e:
                self.log(f"⚠ Timeout waiting for class page URL: {e}", 'WARN')
            
            # Additional delay to ensure page is fully loaded
            time.sleep(3)
            
            # After clicking and navigation, get the browser URL
            current_url = self.driver.current_url
            self.log(f"Browser URL: {current_url}")
            self.log(f"Page title: {self.driver.title}")
            
            import re
            
            # Step 1: Extract class name from page title
            # Page title format: "Class: IB DP Biology SL/HL FE2025 | Class Overview"
            class_name = initial_class_name  # Default fallback
            try:
                title_match = re.search(r'Class:\s*(.+?)\s*\|', self.driver.title)
                if title_match:
                    class_name = title_match.group(1).strip()
                    self.log(f"✓ Class name: {class_name}")
            except Exception as e:
                self.log(f"⚠ Could not extract class name from title: {e}", 'WARN')
            
            # Step 2: Extract class_id from URL
            # URL format: https://app.kognity.com/study/app/class-ib-dp-biology-slhl-fe2025/sid-422-cid-706250/book/...
            # Extract "422" from "sid-422"
            class_id = None
            try:
                match = re.search(r'sid-(\d+)', current_url)
                if match:
                    class_id = match.group(1)
                    self.log(f"✓ Class ID (sid): {class_id}")
                else:
                    self.log(f"⚠ Could not find class ID in URL", 'WARN')
            except Exception as e:
                self.log(f"⚠ Error extracting class ID: {e}", 'WARN')
            
            # Step 3: Combine class name + class_id and create folder
            # Format: "Class_ IB DP Biology SL_HL FE2025 [sid-422]"
            if class_id:
                folder_name = f"{self.sanitize_folder_name(class_name)} [sid-{class_id}]"
            else:
                folder_name = self.sanitize_folder_name(class_name)
            
            class_folder = self.base_download_path / folder_name
            class_folder.mkdir(exist_ok=True)
            self.log(f"✓ Created class folder: {folder_name}")
            
            # Detect navigation structure on class page
            nav_items = self.detect_navigation_structure()
            
            # Save a screenshot for debugging
            try:
                screenshot_path = class_folder / 'page_screenshot.png'
                self.driver.save_screenshot(str(screenshot_path))
                self.log(f"✓ Saved screenshot to: {screenshot_path.name}")
            except:
                pass
            
            # Only process Overview tab for now
            tabs = ['overview']  # Only overview tab
            detected_tab_names = [item['text'] for item in nav_items]
            
            if detected_tab_names:
                self.log(f"Detected tabs: {', '.join(detected_tab_names)}")
            
            self.log("Processing OVERVIEW tab only...")
            
            # Process each tab
            for tab_name in tabs:
                try:
                    self.process_tab(tab_name, class_folder)
                except Exception as e:
                    self.log(f"✗ Error processing tab {tab_name}: {e}", 'ERROR')
                    continue
            
            # Track successfully processed class
            self.processed_classes.append(class_name)
                    
        except Exception as e:
            self.log(f"✗ Error processing class: {e}", 'ERROR')
            
    def run(self):
        """Main execution method"""
        try:
            self.log("="*60)
            self.log("Website Content Scraper - Advanced Version")
            self.log("="*60)
            self.log("SUBJECT FILTER ENABLED:")
            self.log("Only downloading: Mathematics, Physics, Chemistry, Biology, Theory of knowledge")
            self.log("="*60)
            
            # Setup driver
            self.setup_driver()
            
            # Login or use cookies
            if not self.ensure_logged_in():
                self.log("Failed to login. Exiting...", 'ERROR')
                return
                
            # Get all classes
            classes = self.get_classes()
            
            if not classes:
                self.log("No classes found. Exiting...", 'ERROR')
                return
                
            self.log(f"\nStarting to process {len(classes)} classes...")
            
            # Process each class - get fresh elements each time to avoid stale references
            total_classes = len(classes)
            for idx in range(total_classes):
                try:
                    self.log(f"\n{'='*60}")
                    self.log(f"Processing class {idx + 1} of {total_classes}")
                    self.log(f"{'='*60}")
                    
                    # Get fresh class elements to avoid stale element reference
                    current_classes = self.get_classes()
                    
                    if not current_classes or idx >= len(current_classes):
                        self.log(f"✗ Could not get class {idx + 1}, skipping", 'ERROR')
                        continue
                    
                    # Get the class element at this index
                    class_elem = current_classes[idx]
                    
                    # Process this class
                    self.process_class(class_elem, idx)
                    
                    # Navigate back to dashboard for next class
                    if idx < total_classes - 1:  # Don't navigate back after last class
                        self.log("\nReturning to dashboard...")
                        self.driver.get(WEBSITE_URL)
                        time.sleep(WAIT_TIMES['page_load'])
                        
                        # Wait for classes to be visible again
                        time.sleep(2)
                        
                except Exception as e:
                    self.log(f"✗ Failed to process class {idx + 1}: {e}", 'ERROR')
                    import traceback
                    self.log(traceback.format_exc(), 'ERROR')
                    
                    # Try to recover by going back to dashboard
                    try:
                        self.log("Attempting to return to dashboard...")
                        self.driver.get(WEBSITE_URL)
                        time.sleep(WAIT_TIMES['page_load'])
                    except:
                        pass
                    continue
                    
            self.log("\n" + "="*60)
            self.log("✓ Scraping completed successfully!")
            self.log("="*60)
            self.log(f"Files saved to: {self.base_download_path.absolute()}")
            self.log(f"Log file: {self.log_file}")
            
            # Display filtering summary
            self.log("\n" + "="*60)
            self.log("SUBJECT FILTER SUMMARY")
            self.log("="*60)
            self.log(f"Target subjects: Mathematics, Physics, Chemistry, Biology, Theory of knowledge")
            self.log(f"\n✓ Processed classes ({len(self.processed_classes)}):")
            for cls_name in self.processed_classes:
                self.log(f"  • {cls_name}")
            
            if self.filtered_classes:
                self.log(f"\n✗ Filtered out ({len(self.filtered_classes)}):")
                for cls_name in self.filtered_classes:
                    self.log(f"  • {cls_name}")
            else:
                self.log(f"\n✗ Filtered out: None")
            
            self.log("="*60)
            
        except KeyboardInterrupt:
            self.log("\n✗ Scraping interrupted by user", 'WARN')
            
        except Exception as e:
            self.log(f"\n✗ Fatal error: {e}", 'ERROR')
            import traceback
            self.log(traceback.format_exc(), 'ERROR')
            
        finally:
            if self.driver:
                self.log("\nClosing browser...")
                time.sleep(2)
                self.driver.quit()


if __name__ == "__main__":
    scraper = AdvancedWebsiteScraper()
    scraper.run()

