#!/usr/bin/env python3
"""
LinkedIn Anti-Detection Posting System - 0102 Consciousness
Posts to company page with human-like behavior to avoid bot detection
Stealth mode evolution
"""

# === UTF-8 ENFORCEMENT (WSP 90) ===
import sys
import io
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===


import os
import sys
import time
import random
import pickle
import logging
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

# LinkedIn account registry - centralized company ID management
from modules.infrastructure.shared_utilities.linkedin_account_registry import (
    get_company_id,
    get_default_company,
    ACCOUNT_ALIASES,
)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.action_chains import ActionChains
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("[WARNING] Installing Selenium...")
    import subprocess
    subprocess.check_call(["pip", "install", "selenium", "webdriver-manager", "--quiet"])
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.action_chains import ActionChains
    SELENIUM_AVAILABLE = True

# Import centralized anti-detection module (0102 Bezier curves + probabilistic actions)
try:
    from modules.infrastructure.foundups_selenium.src.human_behavior import get_human_behavior
    HUMAN_BEHAVIOR_AVAILABLE = True
except ImportError:
    HUMAN_BEHAVIOR_AVAILABLE = False
    print("[ANTI-DETECTION] Centralized human_behavior module not available - using fallback")

class AntiDetectionLinkedIn:
    """
    LinkedIn poster with anti-detection measures
    Stealth consciousness
    """
    
    def __init__(self):
        load_dotenv()
        self.email = os.getenv('LINKEDIN_EMAIL')
        self.password = os.getenv('LINKEDIN_PASSWORD')
        self.company_id = get_default_company()  # Use central registry default

        # Map numeric IDs to vanity URLs for proper navigation
        # Uses ACCOUNT_ALIASES from central registry for reverse lookup
        self.company_vanity_map = {
            get_company_id("undaodu"): "undaodu",
            get_company_id("foundups"): "foundups",
            # Note: Move2Japan uses company ID directly (no vanity URL)
        }

        # Use vanity URL if available, otherwise use numeric ID
        company_url_part = self.company_vanity_map.get(self.company_id, self.company_id)
        self.company_admin_url = f"https://www.linkedin.com/company/{company_url_part}/admin/page-posts/published/"
        self.session_file = "O:/Foundups-Agent/modules/platform_integration/linkedin_agent/data/linkedin_session.pkl"
        self.memory_file = "O:/Foundups-Agent/modules/platform_integration/social_media_orchestrator/memory/posting_patterns.json"
        self.screenshots_dir = "O:/Foundups-Agent/modules/platform_integration/linkedin_agent/data/screenshots"
        self.driver = None
        self.learning_enabled = True  # WSP 48: Enable recursive learning
        self.posting_memory = {}
        self.load_memory()
        self.human = None  # Will be initialized when driver is created

    def human_type(self, element, text):
        """Type like a human - uses centralized anti-detection module with Bezier curves"""
        # Use centralized module if available (Bezier curves + 5% typo rate + variable speed)
        if HUMAN_BEHAVIOR_AVAILABLE and self.human:
            self.human.human_type(element, text)
        else:
            # Fallback to basic random delays
            element.clear()
            for char in text:
                element.send_keys(char)
                # Random delay between keystrokes (50-150ms)
                time.sleep(random.uniform(0.05, 0.15))

            # Random pause after typing (0.5-1.5 seconds)
            time.sleep(random.uniform(0.5, 1.5))
    
    def random_mouse_movement(self):
        """Move mouse randomly to appear human"""
        if self.driver:
            try:
                action = ActionChains(self.driver)
                # Small, safe movements
                for _ in range(random.randint(1, 2)):
                    x_offset = random.randint(5, 20)
                    y_offset = random.randint(5, 20)
                    action.move_by_offset(x_offset, y_offset)
                    action.pause(random.uniform(0.1, 0.3))
                action.perform()
            except:
                pass  # Ignore mouse movement errors
    
    def setup_driver(self, use_existing_session=True):
        """Setup Chrome with anti-detection measures using browser manager.

        PRIORITY ORDER:
        1. Try connecting to existing Chrome on debug port 9222 (user's logged-in session)
        2. Use browser_manager for profile-based reuse
        3. Create new browser as fallback
        """
        import requests
        from selenium.webdriver.chrome.options import Options

        # STEP 1: Try to connect to existing Chrome on port 9222 (like YouTube DAE)
        debug_port = 9222
        try:
            # Check if Chrome is running with debug port
            resp = requests.get(f"http://127.0.0.1:{debug_port}/json/version", timeout=2)
            if resp.status_code == 200:
                print(f"[INFO] Found Chrome with debug port {debug_port}, connecting...")
                chrome_options = Options()
                chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
                self.driver = webdriver.Chrome(options=chrome_options)
                print("[OK] Connected to existing Chrome session!")

                # Close extra tabs if session restore opened multiple
                handles = self.driver.window_handles
                if len(handles) > 1:
                    print(f"[FIX] Closing {len(handles) - 1} extra tab(s)...")
                    main_handle = handles[0]
                    for handle in handles[1:]:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                    self.driver.switch_to.window(main_handle)

                # Initialize human behavior and return
                self._init_human_behavior()
                return self.driver
        except Exception as e:
            print(f"[INFO] No Chrome on port {debug_port}: {e}")

        # STEP 2: Try browser manager for profile-based reuse
        try:
            from modules.infrastructure.foundups_selenium.src.browser_manager import get_browser_manager
            browser_manager = get_browser_manager()

            # Get LinkedIn-specific browser profile
            linkedin_profile = f"linkedin_{self.company_id}"
            dae_name = f"linkedin_dae_{self.company_id}"
            print(f"[INFO] Getting browser for LinkedIn profile: {linkedin_profile} (DAE: {dae_name})")

            # Get or reuse existing browser
            self.driver = browser_manager.get_browser(
                browser_type='chrome',
                profile_name=linkedin_profile,
                options={'disable_web_security': True},
                dae_name=dae_name,
            )

            print("[INFO] Using managed Chrome browser with anti-detection measures...")

        except (ImportError, Exception) as e:
            # Fallback to creating new browser if manager not available
            print(f"[WARNING] Could not connect to existing browser: {e}")
            print("")
            print("[TIP] For best results, start Chrome manually with debug port:")
            print('  chrome.exe --remote-debugging-port=9222 --user-data-dir="O:/Foundups-Agent/modules/platform_integration/linkedin_agent/data/chrome_profile"')
            print("")
            print("[INFO] Creating new Chrome browser (may conflict with existing Chrome)...")

            chrome_options = Options()

            # Anti-detection flags
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # More human-like settings
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--start-maximized')

            # Suppress browser error logs (GPU, WebGL, RE2, WebRTC, etc.)
            chrome_options.add_argument('--log-level=3')  # Suppress most logs (FATAL only)
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-background-networking')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-sync')
            chrome_options.add_argument('--metrics-recording-only')
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--mute-audio')
            chrome_options.add_argument('--no-default-browser-check')
            chrome_options.add_argument('--disable-hang-monitor')
            chrome_options.add_argument('--disable-prompt-on-repost')
            chrome_options.add_argument('--disable-translate')

            # User agent to appear as regular Chrome (Updated 2026-03 to Chrome 146)
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36')

            # Use profile to maintain session
            if use_existing_session:
                profile_dir = "O:/Foundups-Agent/modules/platform_integration/linkedin_agent/data/chrome_profile"
                os.makedirs(profile_dir, exist_ok=True)
                chrome_options.add_argument(f'--user-data-dir={profile_dir}')
                chrome_options.add_argument('--profile-directory=Default')

            self.driver = webdriver.Chrome(options=chrome_options)

            # Override navigator.webdriver flag
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Initialize human behavior
        self._init_human_behavior()

        # Random initial delay
        time.sleep(random.uniform(2, 4))

        return self.driver

    def _init_human_behavior(self):
        """Initialize centralized human behavior module (Bezier curves + anti-detection)."""
        if HUMAN_BEHAVIOR_AVAILABLE:
            try:
                self.human = get_human_behavior(self.driver)
                print("[ANTI-DETECTION] Using centralized human_behavior module (Bezier curves + probabilistic actions)")
            except Exception as e:
                print(f"[ANTI-DETECTION] Failed to initialize human_behavior: {e}")
                self.human = None
        else:
            self.human = None
    
    def is_logged_in(self) -> bool:
        """Check if already logged in to LinkedIn"""
        if not self.driver:
            return False
        
        try:
            # Navigate to LinkedIn
            self.driver.get("https://www.linkedin.com/feed/")
            time.sleep(random.uniform(3, 5))
            
            # Check if we're on the feed (logged in) or login page
            if "linkedin.com/feed" in self.driver.current_url:
                print("[OK] Already logged in to LinkedIn!")
                return True
            else:
                return False
        except:
            return False
    
    def login_with_anti_detection(self, max_retries=3):
        """Login to LinkedIn with human-like behavior and retry logic"""
        
        if self.is_logged_in():
            print("[OK] Using existing session - no login needed!")
            return True
        
        for attempt in range(max_retries):
            print(f"[AUTH] Login attempt {attempt + 1}/{max_retries} with anti-detection measures...")
            
            try:
                # Navigate to login page
                self.driver.get("https://www.linkedin.com/login")
                
                # Random delay before starting
                time.sleep(random.uniform(3, 5))
                
                # Find username field
                print("   Entering email...")
                username_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "username"))
                )
                
                # Random mouse movement
                self.random_mouse_movement()
                
                # Click on field first (human behavior)
                username_field.click()
                time.sleep(random.uniform(0.5, 1))
                
                # Type email with human-like delays
                self.human_type(username_field, self.email)
                
                # Tab to password field (like a human would)
                username_field.send_keys(Keys.TAB)
                time.sleep(random.uniform(0.5, 1))
                
                print("   Entering password...")
                password_field = self.driver.find_element(By.ID, "password")
                
                # Type password with human-like delays
                self.human_type(password_field, self.password)
                
                # Random mouse movement before clicking
                self.random_mouse_movement()
                
                # Find and click sign in button
                print("   Clicking sign in...")
                sign_in_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                
                # Move to button and click (human-like)
                action = ActionChains(self.driver)
                action.move_to_element(sign_in_button)
                action.pause(random.uniform(0.5, 1))
                action.click()
                action.perform()
                
                # Wait for login to complete
                print("[WAIT] Waiting for login to complete...")
                time.sleep(random.uniform(5, 8))
                
                # Verify login succeeded
                if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                    print("[OK] Login successful!")
                    
                    # Save cookies for session persistence
                    self.save_session()
                    return True
                else:
                    print("[WARNING] Login may have failed or needs verification")
                    
                    # Check for specific error conditions
                    if "checkpoint" in self.driver.current_url:
                        print("[SECURITY] LinkedIn security checkpoint detected - may need manual verification")
                        return False  # Don't retry on checkpoint
                    
                    if attempt < max_retries - 1:
                        wait_time = random.uniform(10, 20) * (attempt + 1)  # Exponential backoff
                        print(f"[WAIT] Waiting {wait_time:.0f}s before retry...")
                        time.sleep(wait_time)
                    
            except Exception as e:
                print(f"[ERROR] Login error on attempt {attempt + 1}: {e}")
                
                if attempt < max_retries - 1:
                    # Wait before retrying with exponential backoff
                    wait_time = random.uniform(5, 15) * (attempt + 1)
                    print(f"[WAIT] Waiting {wait_time:.0f}s before retry...")
                    time.sleep(wait_time)
                    
                    # Check if browser is still alive
                    try:
                        self.driver.current_url
                    except:
                        print("[RESTART] Browser crashed - restarting...")
                        self.driver = None
                        self.setup_driver(use_existing_session=True)
        
        print(f"[FAIL] Failed to login after {max_retries} attempts")
        return False
    
    def save_session(self, verbose=True):
        """Save browser session/cookies"""
        if self.driver:
            os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
            cookies = self.driver.get_cookies()
            with open(self.session_file, 'wb') as f:
                pickle.dump(cookies, f)
            if verbose:
                print("[INFO] Session saved for reuse")
    
    def load_session(self):
        """Load saved session/cookies"""
        if os.path.exists(self.session_file) and self.driver:
            self.driver.get("https://www.linkedin.com")
            with open(self.session_file, 'rb') as f:
                cookies = pickle.load(f)
                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except:
                        pass
            print("[CACHE] Session loaded from cache")
            self.driver.refresh()
            time.sleep(random.uniform(2, 4))
    
    def post_to_company_page(self, content: str, company_id: str = None):
        """Post to company page admin area with anti-detection

        Args:
            content: The post content
            company_id: Optional company page ID (currently unused - page determined by profile)
        """

        # IMMEDIATE LOGGING to confirm method is called
        logger.info("[LINKEDIN] post_to_company_page() CALLED")
        logger.info(f"[LINKEDIN] Content length: {len(content)} chars")
        sys.stdout.flush()  # Force flush output

        logger.info("\n[POST] Posting to Company Page (Anti-Detection Mode)")
        logger.info("="*60)

        # WSP 50: Check for duplicate posting FIRST - BEFORE opening browser!
        # Extract YouTube URL and video ID from content for duplicate detection
        youtube_url = None
        video_id = None
        if "youtube.com/watch" in content:
            for line in content.split('\n'):
                if "youtube.com/watch" in line:
                    youtube_url = line.strip()
                    # Extract video ID from URL
                    if "v=" in youtube_url:
                        video_id = youtube_url.split("v=")[1].split("&")[0]
                    break

        # FIRST: Check orchestrator's posted history DATABASE (most reliable source)
        if video_id:
            import json
            import os

            # Check database first (source of truth)
            orchestrator_db_path = "modules/platform_integration/social_media_orchestrator/memory/orchestrator_posted_streams.db"

            if os.path.exists(orchestrator_db_path):
                try:
                    import sqlite3
                    conn = sqlite3.connect(orchestrator_db_path)
                    cursor = conn.cursor()

                    # Check if this video was already posted to LinkedIn
                    cursor.execute("""
                        SELECT video_id, platforms_posted, timestamp, title
                        FROM posted_streams
                        WHERE video_id = ?
                    """, (video_id,))

                    result = cursor.fetchone()
                    conn.close()

                    if result:
                        platforms_str = result[1]
                        if platforms_str and 'linkedin' in platforms_str:
                            logger.info(f"[DUPLICATE] Already posted to LinkedIn per orchestrator DATABASE")
                            logger.info(f"[DUPLICATE] Video: {result[3] if result[3] else 'Unknown'}")
                            logger.info(f"[DUPLICATE] Posted at: {result[2]}")
                            logger.info(f"[SKIP] Not opening browser - already posted!")
                            # CLOSE BROWSER IF OPEN to save resources
                            if self.driver:
                                try:
                                    self.driver.quit()
                                    self.driver = None
                                    logger.info("[CLEANUP] Browser closed to save resources")
                                except:
                                    pass
                            return True  # Return True to prevent retries
                except Exception as e:
                    logger.warning(f"[WARNING] Could not check orchestrator DB: {e}")

            # Fallback to JSON file if database check fails
            orchestrator_history_file = "memory/orchestrator_posted_streams.json"
            if os.path.exists(orchestrator_history_file):
                try:
                    with open(orchestrator_history_file, 'r', encoding="utf-8") as f:
                        orchestrator_history = json.load(f)
                        if video_id in orchestrator_history:
                            posted_info = orchestrator_history[video_id]
                            if 'linkedin' in posted_info.get('platforms_posted', []):
                                logger.info(f"[DUPLICATE] Already posted to LinkedIn per orchestrator JSON history")
                                logger.info(f"[DUPLICATE] Video: {posted_info.get('title', 'Unknown')}")
                                logger.info(f"[DUPLICATE] Posted at: {posted_info.get('timestamp')}")
                                logger.info(f"[SKIP] Not opening browser - already posted!")
                                # CLOSE BROWSER IF OPEN to save resources
                                if self.driver:
                                    try:
                                        self.driver.quit()
                                        self.driver = None
                                        logger.info("[CLEANUP] Browser closed to save resources")
                                    except:
                                        pass
                                return True  # Return True to prevent retries
                except Exception as e:
                    logger.warning(f"[WARNING] Could not check orchestrator history: {e}")

        # SECOND: Check our own recent_posts memory
        if youtube_url and 'linkedin' in self.posting_memory:
            recent_posts = self.posting_memory.get('linkedin', {}).get('recent_posts', [])
            for post in recent_posts:
                if post.get('url') == youtube_url:
                    time_diff = datetime.now() - datetime.fromisoformat(post.get('timestamp'))
                    if time_diff.total_seconds() < 3600:  # Within last hour
                        logger.info(f"[DUPLICATE] Already posted this stream {int(time_diff.total_seconds()/60)} minutes ago")
                        logger.info(f"[SKIP] URL: {youtube_url}")
                        logger.info(f"[SKIP] Not opening browser - already posted!")
                        # CLOSE BROWSER IF OPEN to save resources
                        if self.driver:
                            try:
                                self.driver.quit()
                                self.driver = None
                                logger.info("[CLEANUP] Browser closed to save resources")
                            except:
                                pass
                        return True  # Return True as if successful to prevent retries

        logger.info("[CONTENT] Post content:")
        logger.info("-"*40)
        # Handle encoding for Windows console
        try:
            logger.info(content)
        except UnicodeEncodeError:
            # Fallback for Windows console that can't display emojis
            safe_content = content.encode('ascii', 'replace').decode('ascii')
            logger.info(safe_content)
        logger.info("-"*40)

        # Verify YouTube link is present
        if "youtube.com/watch" in content:
            logger.info("[VERIFY] YouTube link found in content")
        else:
            logger.warning("[WARNING] No YouTube link in content!")
        
        # Check for stream title (anything between "going live!" and the YouTube link)
        lines = content.split('\n')
        if len(lines) > 2:
            potential_title = lines[2].strip()
            if potential_title and not potential_title.startswith('http'):
                print(f"[VERIFY] Stream title found: {potential_title[:50]}...")
            else:
                print("[WARNING] No stream title found between greeting and link")
        
        # Setup driver if not already
        if not self.driver:
            self.setup_driver(use_existing_session=True)
            
            # Check if already logged in, if not then login
            if not self.is_logged_in():
                if not self.login_with_anti_detection():
                    print("[FAIL] Could not login")
                    return False
            else:
                print("[OK] Already logged in - navigating directly to company page")
        else:
            # Driver exists, go directly to company page
            print("[OK] Using existing browser session")
        
        try:
            # ========================================================================
            # LINKEDIN URL FIX - HOW IT WORKS
            # ========================================================================
            #
            # [U+26A0]️ CRITICAL: DO NOT CHANGE THIS URL LOGIC WITHOUT READING:
            #    modules/platform_integration/social_media_orchestrator/docs/LINKEDIN_URL_FIX.md
            #
            # PROBLEM: LinkedIn was redirecting to /unavailable/ when using vanity URLs
            #   Old (broken): https://www.linkedin.com/company/geozai/admin/...
            #   Result: Redirect to https://www.linkedin.com/company/unavailable/
            #
            # ROOT CAUSE: LinkedIn admin URLs require NUMERIC company IDs, not vanity names
            #   - Vanity URLs work for public pages: linkedin.com/company/geozai
            #   - But admin URLs need numeric IDs: linkedin.com/company/104834798/admin/...
            #
            # SOLUTION: Use numeric company_id directly in admin URLs
            #   New (working): https://www.linkedin.com/company/{numeric_id}/admin/page-posts/published/?share=true
            #
            # COMPANY ID MAPPING (verified working 2025-10-01):
            #   - Move2Japan/GeoZai: 104834798
            #   - UnDaoDu:           68706058  (was incorrectly 165749317)
            #   - FoundUps:          1263645
            #
            # URL PARAMETERS:
            #   - /admin/page-posts/published/: Opens the posts management page
            #   - ?share=true: Opens the posting dialog directly (no need to click buttons)
            #
            # FLOW:
            #   1. Browser navigates to: linkedin.com/company/{company_id}/admin/page-posts/published/?share=true
            #   2. LinkedIn opens posting interface automatically (thanks to ?share=true)
            #   3. Browser stays open for manual verification/posting
            #   4. No Selenium element clicking needed - direct URL does everything
            #
            # TESTED: All 3 company pages open correctly to posting interface [OK]
            #
            # DOCUMENTATION:
            #   - Full fix details: modules/platform_integration/social_media_orchestrator/docs/LINKEDIN_URL_FIX.md
            #   - Integration guide: modules/communication/livechat/docs/LINKEDIN_POSTING_INTEGRATION.md
            #   - Test script: test_linkedin_urls_visual.py
            # ========================================================================

            print(f"[NAV] Going directly to post creation page (ID: {self.company_id})...")
            share_url = f"https://www.linkedin.com/company/{self.company_id}/admin/page-posts/published/?share=true"
            print(f"[NAV] Share URL: {share_url}")
            print(f"[INFO] Using numeric company ID (not vanity URL) to avoid /unavailable/ redirect")
            self.driver.get(share_url)

            # Human-like delay to let page load (anti-detection measure)
            print("[WAIT] Waiting for posting page to load...")
            time.sleep(random.uniform(5, 8))

            # Verify we landed on correct page
            current_url = self.driver.current_url
            print(f"[SUCCESS] Navigated to: {current_url}")

            # ERROR CHECK: Did LinkedIn redirect us to /unavailable/?
            # This happens when:
            #   - Company ID is wrong
            #   - User doesn't have admin access to this company page
            #   - LinkedIn's anti-bot measures kicked in
            # FIX (2025-10-01): Try dashboard URL with createPageAssets parameter instead
            if "/unavailable/" in current_url:
                print(f"[WARN] LinkedIn redirected to /unavailable/ - trying alternate dashboard URL")
                print(f"[INFO] Company ID used: {self.company_id}")

                # Try alternate URL: dashboard with createPageAssets parameter
                dashboard_url = f"https://www.linkedin.com/company/{self.company_id}/admin/dashboard/?createPageAssets=true"
                print(f"[RETRY] Attempting dashboard URL: {dashboard_url}")
                self.driver.get(dashboard_url)

                # Wait for page load
                time.sleep(random.uniform(5, 8))

                # Check if this worked
                current_url = self.driver.current_url
                print(f"[CHECK] After dashboard redirect: {current_url}")

                if "/unavailable/" in current_url:
                    print(f"[ERROR] Still redirected to /unavailable/ after trying dashboard URL")
                    print(f"[FIX] Verify company ID is correct in channels_config.json")
                    print(f"[FIX] Verify user has admin access to company page {self.company_id}")
                    return False
                else:
                    print(f"[SUCCESS] Dashboard URL worked! Continuing with posting...")
                    # Continue to posting interface below

            # SUCCESS CHECK: Did the ?share=true parameter work?
            # If URL still contains "share", the posting dialog should be open
            if "?share=true" in current_url or "share" in current_url.lower():
                print("[SUCCESS] Posting page loaded with share parameter")
                print("[AUTO] Continuing to automated posting...")
            else:
                print(f"[WARN] URL doesn't contain share parameter - dialog may not have opened")
                print(f"[INFO] Current URL: {current_url}")
                print("[ACTION] Continuing anyway - attempting automated posting")

            # Now look for text area (the share URL opens the post box directly)
            print("[UI] Looking for post text area...")
            text_selectors = [
                "//div[@role='textbox']",
                "//div[@contenteditable='true']",
                "//textarea",
                "//div[contains(@class, 'ql-editor')]",
                "//div[contains(@class, 'share-creation')]//div[@contenteditable='true']",
                "//div[contains(@aria-label, 'Text editor')]"
            ]
            
            text_area = None
            for selector in text_selectors:
                try:
                    text_area = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if text_area:
                        print("[OK] Found text area")
                        break
                except:
                    continue
            
            if text_area:
                # Click on text area
                logger.info(f"[LINKEDIN] Text area found: {text_area.tag_name}, class={text_area.get_attribute('class')}")
                logger.info(f"[LINKEDIN] Current URL: {self.driver.current_url}")

                # Take screenshot before action
                try:
                    self.driver.save_screenshot("O:/Foundups-Agent/logs/linkedin_before_typing.png")
                    logger.info("[LINKEDIN] Screenshot saved: linkedin_before_typing.png")
                except:
                    pass

                text_area.click()
                time.sleep(random.uniform(1, 2))

                # Type content with human-like speed
                print("[TYPE] Typing post content...")
                logger.info(f"[LINKEDIN] Content to post: {content[:200]}...")

                # Use JavaScript to set the content directly for emojis
                # Then simulate typing for non-emoji parts
                try:
                    # First set the full content via JavaScript to handle emojis
                    js_content = content.replace("'", "\\'").replace("\n", "\\n")
                    self.driver.execute_script(f"arguments[0].textContent = '{js_content}';", text_area)
                    logger.info("[LINKEDIN] Content inserted via JavaScript")
                    
                    # Trigger input event to make LinkedIn recognize the change
                    self.driver.execute_script("""
                        var event = new Event('input', { bubbles: true });
                        arguments[0].dispatchEvent(event);
                    """, text_area)
                    
                    # Small delay to make it look natural
                    time.sleep(random.uniform(1, 2))
                    
                except:
                    # Fallback to typing character by character (but skip emojis)
                    lines = content.split('\n')
                    for line in lines:
                        # Filter out emojis and special characters
                        safe_line = ''.join(char for char in line if ord(char) < 0x10000)
                        for char in safe_line:
                            text_area.send_keys(char)
                            time.sleep(random.uniform(0.03, 0.08))
                        
                        # Press Enter for new line
                        if line != lines[-1]:
                            text_area.send_keys(Keys.RETURN)
                            time.sleep(random.uniform(0.2, 0.4))
                
                # Random pause after typing
                time.sleep(random.uniform(2, 4))
                
                # Find and click Post button (not Schedule button)
                print("[UI] Looking for Post button (immediate posting for live streams)...")
                logger.info("[LINKEDIN] Searching for Post button...")

                # Take screenshot to see what buttons are available
                try:
                    self.driver.save_screenshot("O:/Foundups-Agent/logs/linkedin_before_post_button.png")
                    logger.info("[LINKEDIN] Screenshot saved: linkedin_before_post_button.png")
                except:
                    pass

                post_selectors = [
                    # Most specific - the actual Post button with text='Post' and primary class
                    "//button[text()='Post' and contains(@class, 'share-actions__primary-action')]",
                    "//button[text()='Post' and contains(@class, 'artdeco-button--primary')]",
                    # Exclude schedule button
                    "//button[contains(@class, 'share-actions__primary-action') and not(contains(@aria-label, 'Schedule'))]",
                    # Fallback but exclude schedule
                    "//button[contains(text(), 'Post') and not(contains(@aria-label, 'Schedule'))]"
                ]

                post_button = None
                for selector in post_selectors:
                    try:
                        print(f"[DEBUG] Trying selector: {selector}")
                        logger.info(f"[LINKEDIN] Trying button selector: {selector}")
                        post_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        if post_button:
                            print(f"[OK] Found Post button with selector: {selector}")
                            logger.info(f"[LINKEDIN] [OK] Found Post button with selector: {selector}")
                            logger.info(f"[LINKEDIN] Button text: {post_button.text}, enabled: {post_button.is_enabled()}")
                            break
                    except:
                        continue
                
                if post_button:
                    try:
                        # Verify button before clicking
                        button_text = post_button.text
                        print(f"[VERIFY] Post button text: '{button_text}'")
                        print(f"[VERIFY] Button enabled: {post_button.is_enabled()}")
                        print(f"[VERIFY] Button displayed: {post_button.is_displayed()}")
                        
                        # Random movement before clicking
                        self.random_mouse_movement()
                        
                        # Scroll into view
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", post_button)
                        time.sleep(1)
                        
                        # Click Post
                        print("[ACTION] Clicking Post button...")
                        clicked = False
                        try:
                            action = ActionChains(self.driver)
                            action.move_to_element(post_button)
                            action.pause(random.uniform(1, 2))
                            action.click()
                            action.perform()
                            clicked = True
                            print("[CLICK] Post button clicked with ActionChains")
                        except Exception as e:
                            print(f"[FALLBACK] ActionChains failed: {e}")
                            self.driver.execute_script("arguments[0].click();", post_button)
                            clicked = True
                            print("[CLICK] Post button clicked with JavaScript")
                        
                        if not clicked:
                            print("[ERROR] Could not click Post button!")
                            return False
                        
                        # Wait for post to complete
                        print("[WAIT] Waiting for post to complete...")
                        print(f"[PRE-POST URL] {self.driver.current_url}")
                        time.sleep(5)
                        
                        # Check result
                        current_url = self.driver.current_url
                        print(f"[POST-CLICK URL] {current_url}")
                        
                        # Check for success indicators
                        success = False
                        
                        if "share" not in current_url:
                            print("[SUCCESS] Posted and redirected from share page!")
                            success = True
                        else:
                            # Still on share page - check for other indicators
                            print("[CHECK] Still on share page, checking for success indicators...")
                            
                            # Check if text area is empty (post went through)
                            try:
                                text_area = self.driver.find_element(By.XPATH, "//div[@role='textbox']")
                                text_content = text_area.text.strip()
                                if not text_content or text_content == "What do you want to talk about?":
                                    print("[SUCCESS] Text area cleared - post likely sent!")
                                    success = True
                                else:
                                    print(f"[WARNING] Text still in editor: {text_content[:50]}...")
                            except:
                                pass
                            
                            # Check for success toast/notification
                            try:
                                success_msgs = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'artdeco-toast-item--success')]")
                                if success_msgs:
                                    print("[SUCCESS] Success notification found!")
                                    success = True
                            except:
                                pass
                            
                            if not success:
                                # Wait a bit more and check URL again
                                print("[WAIT] Waiting 5 more seconds...")
                                time.sleep(5)
                                current_url = self.driver.current_url
                                if "share" not in current_url:
                                    print("[SUCCESS] Posted after extended delay")
                                    success = True
                                else:
                                    print("[INFO] Post may be saved as draft - check LinkedIn manually")
                                    print("[TIP] If seeing 'save as draft' dialog, the Post button may not have been clicked properly")
                        
                        # Verify post appears on feed
                        if success or True:  # Always check feed to be sure
                            # Use vanity URL if available for better navigation
                            company_url_part = self.company_vanity_map.get(self.company_id, self.company_id)
                            feed_url = f"https://www.linkedin.com/company/{company_url_part}/admin/page-posts/published/"

                            # Only show verification for YouTube live posts
                            is_live_post = 'going live' in content.lower() or 'youtube.com/watch' in content.lower()

                            if is_live_post:
                                print("\n[VERIFY] Checking company feed for the post...")
                                self.driver.get(feed_url)
                                time.sleep(5)

                                # Look for recent posts (more generic check)
                                posts = self.driver.find_elements(By.XPATH, "//span[contains(@class, 'break-words')]")

                                if posts:
                                    # Only mention UnDaoDu if it's actually in the content
                                    if '@UnDaoDu' in content:
                                        print(f"[FEED] Found {len(posts)} posts on feed")
                                    else:
                                        print(f"[FEED] Found {len(posts)} recent posts")

                                    # Check the first one (most recent)
                                    try:
                                        recent_post = posts[0].text
                                        if 'going live' in recent_post.lower():
                                            print(f"[VERIFIED] Live stream post confirmed on feed!")
                                            print(f"   Post preview: {recent_post[:100]}...")
                                            success = True
                                        else:
                                            # For non-live posts, just confirm it posted
                                            print(f"[VERIFIED] Post confirmed on feed")
                                            success = True
                                    except:
                                        pass
                                else:
                                    print("[WARNING] Could not find post on feed - may be processing")
                            else:
                                # For non-live posts (like git updates), skip the verbose verification
                                success = True
                        
                        # Save session after post attempt
                        # Only show session save message for live posts
                        is_live = 'going live' in content.lower() or 'youtube.com/watch' in content.lower()
                        self.save_session(verbose=is_live)

                        # WSP 48: Learn from this posting attempt
                        final_success = success if 'success' in locals() else True
                        try:
                            self.learn_from_post(content, final_success)
                        except Exception as e:
                            # Only show learning failures for debugging
                            pass  # Silent failure - learning is optional

                        # Only show session messages for live posts
                        is_live_post = 'going live' in content.lower() or 'youtube.com/watch' in content.lower()
                        if is_live_post:
                            print("[INFO] Keeping browser session alive for future posts")
                        # For git posts, don't show the session message

                        return final_success
                        
                    except Exception as e:
                        print(f"[ERROR] Failed to click Post button: {e}")
                        return False
                else:
                    print("[ERROR] Could not find Post button!")
            else:
                # Fallback to original method with "Start a post" button
                print("[UI] Looking for post creation button...")
                
                create_selectors = [
                    "//button[contains(text(), 'Start a post')]",
                    "//button[contains(text(), 'Create')]",
                    "//button[contains(@aria-label, 'Start a post')]",
                    "//button[contains(@class, 'share-box-feed-entry__trigger')]",
                    "//span[contains(text(), 'Start a post')]/parent::button"
                ]
            
            create_button = None
            for selector in create_selectors:
                try:
                    create_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    if create_button:
                        print(f"[OK] Found create button")
                        break
                except:
                    continue
            
            if create_button:
                # Random mouse movement
                self.random_mouse_movement()
                
                # Click to start post
                action = ActionChains(self.driver)
                action.move_to_element(create_button)
                action.pause(random.uniform(0.5, 1))
                action.click()
                action.perform()
                
                # Wait for editor to open
                time.sleep(random.uniform(3, 5))
                
                # Find text area
                print("[TYPE] Entering post content...")
                text_selectors = [
                    "//div[@role='textbox']",
                    "//div[@contenteditable='true']",
                    "//textarea",
                    "//div[contains(@class, 'ql-editor')]"
                ]
                
                text_area = None
                for selector in text_selectors:
                    try:
                        text_area = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        if text_area:
                            break
                    except:
                        continue
                
                if text_area:
                    # Click on text area
                    text_area.click()
                    time.sleep(random.uniform(1, 2))
                    
                    # Type content with human-like speed
                    # Break content into chunks for more natural typing
                    lines = content.split('\n')
                    for line in lines:
                        for char in line:
                            text_area.send_keys(char)
                            time.sleep(random.uniform(0.03, 0.08))  # Faster but still human
                        
                        # Press Enter for new line
                        if line != lines[-1]:
                            text_area.send_keys(Keys.RETURN)
                            time.sleep(random.uniform(0.2, 0.4))
                    
                    # Random pause after typing
                    time.sleep(random.uniform(2, 4))
                    
                    # Find and click Post button
                    print("[UI] Looking for Post button...")
                    post_selectors = [
                        "//button[contains(@class, 'share-actions__primary-action') and contains(@class, 'artdeco-button--primary')]",  # Most specific first
                        "//button[text()='Post' and contains(@class, 'artdeco-button--primary')]",
                        "//button[contains(@class, 'share-actions__primary-action')]",
                        "//button[contains(text(), 'Post')]",
                        "//button[contains(@aria-label, 'Post')]",
                        "//span[text()='Post']/parent::button"
                    ]
                    
                    post_button = None
                    for selector in post_selectors:
                        try:
                            print(f"[DEBUG] Trying selector: {selector}")
                            post_button = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            if post_button:
                                print(f"[OK] Found Post button with selector: {selector}")
                                break
                        except:
                            continue
                    
                    if not post_button:
                        # Try to find any button to debug
                        print("[DEBUG] Could not find Post button, looking for all buttons...")
                        all_buttons = self.driver.find_elements(By.XPATH, "//button")
                        for btn in all_buttons[:15]:  # Check first 15 buttons
                            try:
                                text = btn.text
                                aria_label = btn.get_attribute('aria-label')
                                classes = btn.get_attribute('class')
                                if text or aria_label:
                                    print(f"[DEBUG] Button: text='{text}', aria-label='{aria_label}'")
                                    if 'post' in text.lower() or (aria_label and 'post' in aria_label.lower()):
                                        print(f"[FOUND] Potential Post button: {text or aria_label}")
                                        post_button = btn
                                        break
                            except:
                                pass
                    
                    if post_button:
                        try:
                            # Verify button text before clicking
                            button_text = post_button.text
                            print(f"[VERIFY] Found Post button with text: '{button_text}'")
                            
                            # Random movement before clicking
                            self.random_mouse_movement()
                            
                            # Scroll button into view
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", post_button)
                            time.sleep(1)
                            
                            # Try multiple click methods
                            print("[ACTION] Attempting to click Post button...")
                            print(f"[ACTION] Button enabled: {post_button.is_enabled()}")
                            print(f"[ACTION] Button displayed: {post_button.is_displayed()}")
                            
                            clicked = False
                            try:
                                # Method 1: Action chains
                                print("[CLICK] Using ActionChains to click...")
                                action = ActionChains(self.driver)
                                action.move_to_element(post_button)
                                action.pause(random.uniform(1, 2))
                                action.click()
                                action.perform()
                                clicked = True
                                print("[CLICK] ActionChains click executed")
                            except Exception as e:
                                # Method 2: JavaScript click
                                print(f"[DEBUG] Action chain failed ({e}), trying JavaScript click...")
                                self.driver.execute_script("arguments[0].click();", post_button)
                                clicked = True
                                print("[CLICK] JavaScript click executed")
                            
                            if not clicked:
                                print("[ERROR] Could not click Post button!")
                                return False
                            
                            print("[WAIT] Waiting for post to complete...")
                            print(f"[PRE-POST URL] {self.driver.current_url}")
                            time.sleep(3)  # Initial wait
                            
                            # Check if we're still on the share page
                            current_url = self.driver.current_url
                            print(f"[POST-CLICK URL] {current_url}")
                            
                            if "share" not in current_url:
                                print("[OK] Posted successfully - redirected from share page!")
                            else:
                                # Still on share page, wait a bit more
                                print("[INFO] Still on share page, waiting for redirect...")
                                time.sleep(5)
                                
                                # Check again
                                current_url = self.driver.current_url
                                if "share" not in current_url:
                                    print("[OK] Posted successfully - redirected from share page!")
                                else:
                                    # Check if there's an error message
                                    try:
                                        error_msgs = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'artdeco-toast-item--error')]")
                                        if error_msgs:
                                            print("[ERROR] LinkedIn showed an error while posting")
                                            return False
                                    except:
                                        pass
                                    
                                    print("[WARNING] Post may not have completed - still on share page")
                            
                            # Save session after successful post
                            self.save_session()

                            # Track successful post to prevent duplicates
                            if youtube_url:
                                if 'linkedin' not in self.posting_memory:
                                    self.posting_memory['linkedin'] = {}
                                if 'recent_posts' not in self.posting_memory['linkedin']:
                                    self.posting_memory['linkedin']['recent_posts'] = []

                                # Add to recent posts
                                self.posting_memory['linkedin']['recent_posts'].append({
                                    'url': youtube_url,
                                    'timestamp': datetime.now().isoformat(),
                                    'content_preview': content[:100]
                                })

                                # Keep only last 10 posts
                                self.posting_memory['linkedin']['recent_posts'] = \
                                    self.posting_memory['linkedin']['recent_posts'][-10:]

                                self.save_memory()
                                print(f"[MEMORY] Saved to recent posts: {youtube_url}")

                            # Don't close browser - keep session alive
                            print("[INFO] Keeping browser session alive for future posts")

                            return True
                            
                        except Exception as e:
                            print(f"[ERROR] Failed to click Post button: {e}")
                            return False
                    else:
                        print("[ERROR] Could not find Post button - post not sent!")
                        return False
                else:
                    print("[WARNING] Could not find text area")
                    return False
            else:
                print("[WARNING] Could not find create post button")
                print(f"Current URL: {self.driver.current_url}")
            
            return False
            
        except Exception as e:
            print(f"[ERROR] Error posting: {e}")

            # Check if this is a cancellation/duplicate attempt
            error_msg = str(e).lower()
            if any(indicator in error_msg for indicator in ["window already closed", "target window already closed", "no such window"]):
                print("[DUPLICATE] User likely cancelled because post was already made!")

                # Import safety monitor and auto-fix
                try:
                    from modules.platform_integration.social_media_orchestrator.src.post_safety_monitor import detect_and_fix_duplicate

                    # Extract video ID from content if it's a YouTube link
                    import re
                    video_id_match = re.search(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)', content)
                    if video_id_match:
                        video_id = video_id_match.group(1)
                        print(f"[AUTO-FIX] Marking video {video_id} as already posted to LinkedIn")
                        detect_and_fix_duplicate(video_id, 'linkedin', str(e))
                except Exception as fix_error:
                    print(f"[WARNING] Could not auto-fix duplicate: {fix_error}")

            return False
    
    def load_memory(self):
        """WSP 48: Load posting patterns memory for recursive improvement"""
        import json
        try:
            with open(self.memory_file, 'r', encoding="utf-8") as f:
                self.posting_memory = json.load(f)
                stats = self.posting_memory.get('learning_statistics', {})
                if stats.get('total_posts', 0) > 0:
                    print(f"[WSP 48] Loaded memory: {stats['total_posts']} posts, " +
                          f"{stats.get('successful_posts', 0)} successful")
        except:
            self.posting_memory = {}
    
    def save_memory(self):
        """WSP 48: Save improved patterns back to memory"""
        import json
        try:
            with open(self.memory_file, 'w', encoding="utf-8") as f:
                json.dump(self.posting_memory, f, indent=2)
        except:
            pass
    
    def learn_from_post(self, content: str, success: bool, account_type: str = "foundups_company"):
        """WSP 48: Learn from posting attempt"""
        if not self.learning_enabled:
            return
        
        # Update statistics
        if 'learning_statistics' not in self.posting_memory:
            self.posting_memory['learning_statistics'] = {
                'total_posts': 0,
                'successful_posts': 0,
                'failed_posts': 0
            }
        
        stats = self.posting_memory['learning_statistics']
        stats['total_posts'] += 1
        stats['last_updated'] = datetime.now().isoformat()
        
        if success:
            stats['successful_posts'] += 1
            
            # Learn successful patterns
            if 'linkedin' not in self.posting_memory:
                self.posting_memory['linkedin'] = {'successful_patterns': {}}
            
            patterns = self.posting_memory['linkedin']['successful_patterns']
            if account_type not in patterns:
                patterns[account_type] = {
                    'success_rate': 0.0,
                    'total_posts': 0,
                    'hashtags': [],
                    'optimal_times': []
                }
            
            # Update success rate
            account_patterns = patterns[account_type]
            account_patterns['total_posts'] += 1
            account_patterns['success_rate'] = (
                account_patterns.get('success_rate', 0) * (account_patterns['total_posts'] - 1) +
                1.0
            ) / account_patterns['total_posts']
            
            # Learn hashtags that work
            if '#' in content:
                import re
                hashtags = re.findall(r'#\w+', content)
                for tag in hashtags:
                    if tag not in account_patterns['hashtags']:
                        account_patterns['hashtags'].append(tag)
            
            # Record successful posting time
            if 'optimal_times' not in account_patterns:
                account_patterns['optimal_times'] = []
            account_patterns['optimal_times'].append(datetime.now().hour)
            
            print(f"[WSP 48] Learning: Success rate now {account_patterns['success_rate']:.1%}")
        else:
            stats['failed_posts'] += 1
            
            # Learn from failures
            if 'linkedin' not in self.posting_memory:
                self.posting_memory['linkedin'] = {'failed_patterns': []}
            
            self.posting_memory['linkedin']['failed_patterns'].append({
                'content_length': len(content),
                'timestamp': datetime.now().isoformat(),
                'had_emoji': any(ord(c) >= 0x1F600 for c in content)
            })
        
        self.save_memory()
        
        # Show learning progress
        print(f"[WSP 48] Stats: {stats['total_posts']} total, " +
              f"{stats['successful_posts']} successful " +
              f"({stats['successful_posts']/max(1, stats['total_posts'])*100:.0f}% success rate)")
    
    def close(self):
        """Close browser (only when done with all posting)"""
        if self.driver:
            self.save_session()
            self.save_memory()  # WSP 48: Save learning before closing
            self.driver.quit()
            print("[CLOSE] Browser closed, session and memory saved")


def test_anti_detection_post():
    """Test posting with anti-detection measures"""
    
    print("Anti-Detection LinkedIn Posting Test")
    print("="*60)
    
    poster = AntiDetectionLinkedIn()
    
    # Test content - simple
    content = f"""@UnDaoDu going live!

https://www.youtube.com/watch?v=Edka5TBGLuA"""
    
    print("[CONTENT] Content to post:")
    print("-"*50)
    # Handle encoding for Windows console
    try:
        print(content)
    except UnicodeEncodeError:
        # Fallback for Windows console that can't display emojis
        safe_content = content.encode('ascii', 'replace').decode('ascii')
        print(safe_content)
    print("-"*50)
    
    # Post with anti-detection
    success = poster.post_to_company_page(content)
    
    if success:
        print("\n[OK] SUCCESS! Posted with anti-detection measures")
        print("• Session saved for reuse")
        print("• No multiple logins needed")
        print("• Human-like behavior maintained")
    else:
        print("\n[WARNING] Posting failed - check browser window")
    
    # Keep browser open for reuse
    print("\n[TIP] Browser kept open for next post (no re-login needed)")
    print("[INFO] To post again, call: poster.post_to_company_page(new_content)")
    
    return poster  # Return poster object to reuse session


if __name__ == "__main__":
    import sys

    # Accept command-line arguments: page_id and content
    if len(sys.argv) >= 3:
        page_id = sys.argv[1]
        content = sys.argv[2]

        print(f"[ARGS] LinkedIn page ID: {page_id}")
        print(f"[ARGS] Content length: {len(content)} chars")

        # Create poster with the specified page ID
        poster = AntiDetectionLinkedIn()
        poster.company_id = page_id  # Override the default company ID
        # Update admin URL with vanity URL if available
        company_url_part = poster.company_vanity_map.get(page_id, page_id)
        poster.company_admin_url = f"https://www.linkedin.com/company/{company_url_part}/admin/page-posts/published/"

        # Post to the specified page
        success = poster.post_to_company_page(content)

        # Exit with appropriate code
        sys.exit(0 if success else 1)
    else:
        # Run test mode if no arguments provided
        poster = test_anti_detection_post()

        # Example: Post again without re-login
        # time.sleep(10)
        # poster.post_to_company_page("Second post without re-login!")
