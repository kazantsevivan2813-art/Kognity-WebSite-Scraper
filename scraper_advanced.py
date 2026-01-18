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
        
    


if __name__ == "__main__":
    scraper = AdvancedWebsiteScraper()
    scraper.run()

