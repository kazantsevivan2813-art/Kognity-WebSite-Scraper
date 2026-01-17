"""
Selector configuration for Kognity scraper.
Contains all CSS selectors, XPath expressions, and timing configurations.
"""

from selenium.webdriver.common.by import By

# ============================================================================
# TIMING CONFIGURATIONS
# ============================================================================

WAIT_TIMES = {
    'element_load': 10,      # Wait time for elements to load (seconds)
    'page_load': 3,          # Wait time after page navigation (seconds)
    'after_login': 5,        # Wait time after login (seconds)
    'after_click': 2,        # Wait time after clicking elements (seconds)
}


# ============================================================================
# LOGIN SELECTORS
# ============================================================================

LOGIN_SELECTORS = {
    'email_field': [
        (By.CSS_SELECTOR, 'input[type="email"]'),
        (By.CSS_SELECTOR, 'input[name="email"]'),
        (By.CSS_SELECTOR, 'input[placeholder*="email" i]'),
        (By.XPATH, '//input[@type="email"]'),
    ],
    
    'password_field': [
        (By.CSS_SELECTOR, 'input[type="password"]'),
        (By.CSS_SELECTOR, 'input[name="password"]'),
        (By.XPATH, '//input[@type="password"]'),
    ],
    
    'login_button': [
        (By.CSS_SELECTOR, 'button[type="submit"]'),
        (By.XPATH, '//button[contains(text(), "Sign in")]'),
        (By.XPATH, '//button[contains(text(), "Log in")]'),
        (By.XPATH, '//button[contains(text(), "Continue")]'),
        (By.XPATH, '//input[@type="submit"]'),
    ],
}


# ============================================================================
# DASHBOARD SELECTORS
# ============================================================================

DASHBOARD_SELECTORS = {
    'logged_in_indicator': [
        (By.CSS_SELECTOR, '[class*="UserMenu"]'),
        (By.CSS_SELECTOR, '[class*="user-menu"]'),
        (By.XPATH, '//div[contains(@class, "user")]'),
    ],
    
    'class_items': [
        # Kognity-specific class card selectors
        (By.CSS_SELECTOR, '[class*="ClassCard"]'),
        (By.CSS_SELECTOR, 'a[class*="ClassCard"]'),
        (By.CSS_SELECTOR, '.ClassCard-className'),
        (By.XPATH, '//a[contains(@class, "ClassCard")]'),
        
        # Generic class/course selectors
        (By.CSS_SELECTOR, '[class*="class-card"]'),
        (By.CSS_SELECTOR, '[class*="course-card"]'),
        (By.XPATH, '//div[contains(@class, "class")]//a'),
        (By.XPATH, '//div[contains(@class, "course")]//a'),
    ],
}


# ============================================================================
# TAB SELECTORS
# ============================================================================

TAB_SELECTORS = {
    'overview': [
        (By.XPATH, '//a[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "overview")]'),
        (By.CSS_SELECTOR, 'a[href*="overview"]'),
        (By.XPATH, '//nav//a[contains(text(), "Overview")]'),
    ],
    
    'book': [
        (By.XPATH, '//a[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "book")]'),
        (By.CSS_SELECTOR, 'a[href*="book"]'),
        (By.XPATH, '//nav//a[contains(text(), "Book")]'),
    ],
    
    'practice': [
        (By.XPATH, '//a[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "practice")]'),
        (By.CSS_SELECTOR, 'a[href*="practice"]'),
        (By.XPATH, '//nav//a[contains(text(), "Practice")]'),
    ],
    
    'assignments': [
        (By.XPATH, '//a[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "assignment")]'),
        (By.CSS_SELECTOR, 'a[href*="assignment"]'),
        (By.XPATH, '//nav//a[contains(text(), "Assignment")]'),
    ],
    
    'insights': [
        (By.XPATH, '//a[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "insight")]'),
        (By.CSS_SELECTOR, 'a[href*="insight"]'),
        (By.XPATH, '//nav//a[contains(text(), "Insight")]'),
    ],
}


# ============================================================================
# CONTENT SELECTORS (Kognity-specific)
# ============================================================================

CONTENT_SELECTORS = {
    # Table of Contents
    'toc_topics': [
        (By.CSS_SELECTOR, '[class*="TableOfContentsTopics-listItem"]'),
        (By.CSS_SELECTOR, '.TableOfContentsTopics-listItem'),
    ],
    
    # Main topic buttons
    'main_topic_button': [
        (By.CSS_SELECTOR, 'button[class*="KogButtonLegacy"]'),
        (By.XPATH, '//button[contains(@class, "KogButtonLegacy")]'),
    ],
    
    # Subtopic containers
    'subtopic_container': [
        (By.CSS_SELECTOR, '[class*="SubjectOverviewSubtopic"]'),
    ],
    
    # Subtopic header
    'subtopic_header': [
        (By.CSS_SELECTOR, '[class*="SubjectOverviewSubtopic-headerContent"]'),
    ],
    
    # Sections list (within subtopic)
    'sections_list': [
        (By.CSS_SELECTOR, '[lang="en"].list-style-none'),
        (By.CSS_SELECTOR, '[lang="en"][class*="list-style-none"]'),
        (By.CSS_SELECTOR, 'ul.list-style-none'),
        (By.CSS_SELECTOR, 'ol.list-style-none'),
    ],
    
    # Navigation menu items
    'nav_menu_items': [
        (By.CSS_SELECTOR, '[class*="NavbarCenterMenu-menuItem"]'),
    ],
    
    # Close button for sidebar/panel
    'close_button': [
        (By.CSS_SELECTOR, '[class*="BookRailToc-topicHeadlineCloseButton"]'),
    ],
}


# ============================================================================
# ADDITIONAL CONFIGURATIONS
# ============================================================================

# Cookie expiry in days
COOKIE_EXPIRY_DAYS = 7

# Download settings
DOWNLOAD_SETTINGS = {
    'default_format': 'mhtml',  # Format for saving pages
    'create_screenshots': True,  # Whether to save screenshots
}

# Logging settings
LOGGING = {
    'console': True,
    'file': True,
    'level': 'INFO',  # INFO, WARN, ERROR
}
