"""
Browser Manager
Manages singleton browser instances to avoid opening multiple windows
Reuses existing browser sessions for posting and streams telemetry for WSP oversight.

CROSS-PROCESS BROWSER REUSE:
- Browsers start with --remote-debugging-port to enable reconnection
- Port info saved to .browser_session files
- On get_browser(), tries to connect to existing browser before creating new

Migrated from social_media_orchestrator to foundups_selenium (Sprint V4)
WSP References: WSP 3 (Architecture), WSP 77 (AI Overseer telemetry)
"""

import os
import json
import logging
import threading
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

# LinkedIn account registry - centralized company ID management
from modules.infrastructure.shared_utilities.linkedin_account_registry import (
    get_company_id,
)

# Directory to store browser session info for cross-process reconnection
BROWSER_SESSION_DIR = Path("O:/Foundups-Agent/modules/infrastructure/foundups_selenium/data/sessions")

# Port range for debugging (each profile gets unique port)
BASE_DEBUG_PORT = 9222

try:
    from modules.infrastructure.foundups_selenium.src.foundups_driver import (
        FoundUpsDriver,
    )
except Exception:  # pragma: no cover - allow fallback when driver unavailable
    FoundUpsDriver = None  # type: ignore


class BrowserManager:
    """Singleton browser manager to reuse browser instances"""

    _instance = None
    _lock = threading.Lock()
    _browsers = {}  # Store browser instances by key

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.logger = logging.getLogger(__name__)
                    cls._instance._browsers = {}
                    cls._instance._browser_locks = {}
                    cls._instance._allocations = {}  # browser_key -> dae_name
                    cls._instance._allocations_lock = threading.Lock()
                    cls._instance._observers = {}
                    cls._instance._telemetry_lock = threading.Lock()
                    telemetry_dir = os.path.join("logs")
                    os.makedirs(telemetry_dir, exist_ok=True)
                    cls._instance._telemetry_path = os.path.join(
                        telemetry_dir, "foundups_browser_events.log"
                    )
        return cls._instance

    def _get_session_file(self, browser_key: str) -> Path:
        """Get path to session file for browser."""
        return BROWSER_SESSION_DIR / f"{browser_key}.json"

    def _save_session(self, browser_key: str, port: int, profile_dir: str) -> None:
        """Save browser session info for cross-process reconnection."""
        session_file = self._get_session_file(browser_key)
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_data = {
            "port": port,
            "profile_dir": profile_dir,
            "created": datetime.utcnow().isoformat() + "Z",
            "pid": os.getpid()
        }
        with open(session_file, "w") as f:
            json.dump(session_data, f)
        self.logger.info(f"・Session saved: {browser_key} on port {port}")

    def _load_session(self, browser_key: str) -> Optional[Dict[str, Any]]:
        """Load browser session info if exists."""
        session_file = self._get_session_file(browser_key)
        if session_file.exists():
            try:
                with open(session_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _is_browser_running(self, port: int) -> bool:
        """Check if browser is running on the given debug port."""
        try:
            resp = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def _connect_to_existing(self, browser_key: str, port: int) -> Optional[Any]:
        """Try to connect to an existing browser via CDP."""
        try:
            chrome_options = ChromeOptions()
            chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            driver = webdriver.Chrome(options=chrome_options)
            # Verify connection
            _ = driver.current_url
            self.logger.info(f"・Connected to existing browser on port {port}")
            return driver
        except Exception as e:
            self.logger.debug(f"・Could not connect to existing browser: {e}")
            return None

    def _get_debug_port(self, profile_name: str) -> int:
        """Get unique debug port for profile (deterministic hash)."""
        # Simple hash to get port in range 9222-9322
        port_offset = hash(profile_name) % 100
        return BASE_DEBUG_PORT + port_offset

    def get_browser(self, browser_type: str, profile_name: str, options: Dict[str, Any] = None, dae_name: Optional[str] = None) -> Any:
        """
        Get or create a browser instance.

        CROSS-PROCESS REUSE: If a browser is already running (from previous process),
        connects to it via CDP instead of creating a new instance.

        When `dae_name` is provided, BrowserManager tracks allocations to prevent
        multiple DAEs from hijacking the same browser/profile session.

        Args:
            browser_type: 'chrome' or 'edge'
            profile_name: Unique profile identifier (e.g., 'linkedin', 'x_foundups', 'youtube_move2japan')
            options: Additional browser options
            dae_name: Optional DAE owner name for cross-DAE coordination

        Returns:
            Browser driver instance
        """
        browser_key = f"{browser_type}_{profile_name}"

        if dae_name:
            with self._allocations_lock:
                current_owner = self._allocations.get(browser_key)
                if current_owner and current_owner != dae_name:
                    raise RuntimeError(
                        f"Browser {browser_key} is allocated to {current_owner}; cannot use for {dae_name}"
                    )

        # Check if browser exists in THIS process and is still valid
        if browser_key in self._browsers:
            browser = self._browsers[browser_key]
            try:
                # Check if browser is still responsive
                _ = browser.current_url
                self.logger.info(f"・Reusing existing {browser_type} browser for {profile_name}")
                self._ensure_observer(browser_key, browser)
                if dae_name:
                    with self._allocations_lock:
                        self._allocations[browser_key] = dae_name
                return browser
            except Exception as e:
                self.logger.warning(f"・・Existing browser unresponsive: {e}")
                # Browser is dead, remove it
                del self._browsers[browser_key]
                with self._allocations_lock:
                    self._allocations.pop(browser_key, None)

        # CROSS-PROCESS REUSE: Check if browser is running from previous process
        session = self._load_session(browser_key)
        if session and browser_type.lower() == 'chrome':
            port = session.get("port")
            if port and self._is_browser_running(port):
                self.logger.info(f"・Found existing browser on port {port}, connecting...")
                browser = self._connect_to_existing(browser_key, port)
                if browser:
                    self._browsers[browser_key] = browser
                    self._ensure_observer(browser_key, browser)
                    if dae_name:
                        with self._allocations_lock:
                            self._allocations[browser_key] = dae_name
                    return browser

        # Create new browser instance
        self.logger.info(f"・Creating new {browser_type} browser for {profile_name}")

        if browser_type.lower() == 'chrome':
            browser = self._create_chrome_browser(browser_key, profile_name, options)
        elif browser_type.lower() == 'edge':
            browser = self._create_edge_browser(profile_name, options)
        else:
            raise ValueError(f"Unsupported browser type: {browser_type}")

        # Store browser instance
        self._ensure_observer(browser_key, browser)
        self._browsers[browser_key] = browser
        if dae_name:
            with self._allocations_lock:
                self._allocations[browser_key] = dae_name
        self.logger.info(f"・Browser created and stored: {browser_key}")

        return browser

    def _create_chrome_browser(self, browser_key: str, profile_name: str, custom_options: Dict[str, Any] = None):
        """Create Chrome browser with anti-detection settings and CDP support for cross-process reuse."""
        chrome_options = ChromeOptions()

        # Anti-detection flags
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # CROSS-PROCESS REUSE: Enable remote debugging for reconnection
        debug_port = self._get_debug_port(profile_name)
        chrome_options.add_argument(f'--remote-debugging-port={debug_port}')
        self.logger.info(f"・Enabling CDP on port {debug_port} for cross-process reuse")

        # Standard settings
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        # User agent
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # Use existing profile to maintain session and reuse browser
        # Map profile names to actual Chrome profile directories (must match actual implementations)
        # Build profile mapping dynamically using central registry
        move2japan_id = get_company_id("move2japan")
        foundups_id = get_company_id("foundups")
        undaodu_id = get_company_id("undaodu")

        profile_mapping = {
            # LinkedIn profiles (using central registry IDs)
            f'linkedin_{move2japan_id}': 'O:/Foundups-Agent/modules/platform_integration/linkedin_agent/data/chrome_profile',  # GeoZai
            f'linkedin_{foundups_id}': 'O:/Foundups-Agent/modules/platform_integration/linkedin_agent/data/chrome_profile',     # FoundUps
            f'linkedin_{undaodu_id}': 'O:/Foundups-Agent/modules/platform_integration/linkedin_agent/data/chrome_profile',   # UnDaoDu

            # X/Twitter profiles
            'x_move2japan': 'O:/Foundups-Agent/modules/platform_integration/x_twitter/data/chrome_profile_geozai',
            'x_foundups': 'O:/Foundups-Agent/modules/platform_integration/x_twitter/data/chrome_profile_foundups',  # Now using Chrome instead of Edge

            # YouTube profiles (Sprint V4 addition)
            'youtube_move2japan': 'O:/Foundups-Agent/modules/platform_integration/youtube_auth/data/chrome_profile_move2japan',
            'youtube_foundups': 'O:/Foundups-Agent/modules/platform_integration/youtube_auth/data/chrome_profile_foundups',
            'youtube_geozai': 'O:/Foundups-Agent/modules/platform_integration/youtube_auth/data/chrome_profile_geozai',
            'youtube_undaodu': 'O:/Foundups-Agent/modules/platform_integration/youtube_auth/data/chrome_profile_undaodu',
        }

        profile_dir = profile_mapping.get(profile_name)
        if not profile_dir:
            # Fallback to default profile
            profile_dir = f"O:/Foundups-Agent/modules/platform_integration/browser_profiles/{profile_name}/chrome"

        os.makedirs(profile_dir, exist_ok=True)
        chrome_options.add_argument(f'--user-data-dir={profile_dir}')
        chrome_options.add_argument('--profile-directory=Default')

        # Apply custom options if provided
        if custom_options:
            for key, value in custom_options.items():
                if key == 'headless' and value:
                    chrome_options.add_argument('--headless')

        driver = self._instantiate_chrome_driver(browser_key, chrome_options, profile_dir)

        if not hasattr(driver, 'register_observer'):
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Save session for cross-process reconnection
        self._save_session(browser_key, debug_port, profile_dir)

        return driver

    def _instantiate_chrome_driver(self, browser_key: str, chrome_options: ChromeOptions, profile_dir: str):
        """Instantiate Chrome driver, preferring FoundUpsDriver for telemetry."""
        observer = self._get_observer(browser_key)
        if FoundUpsDriver is not None:
            try:
                return FoundUpsDriver(
                    profile_dir=profile_dir,
                    options=chrome_options,
                    observers=[observer] if observer else None,
                )
            except Exception as exc:  # pragma: no cover - log and fallback
                self.logger.warning("・・Failed to create FoundUpsDriver, falling back to raw Selenium: %s", exc)

        driver = webdriver.Chrome(options=chrome_options)
        if observer and FoundUpsDriver is None:
            self.logger.debug("・Telemetry observer registered in fallback mode (limited events)")
        return driver

    def _ensure_observer(self, browser_key: str, browser: Any) -> None:
        """Attach telemetry observer to a browser if supported."""
        observer = self._get_observer(browser_key)
        if hasattr(browser, "register_observer"):
            try:
                browser.register_observer(observer)
            except Exception as exc:  # pragma: no cover - best effort
                self.logger.warning("・・Failed to register browser observer: %s", exc)

    def _get_observer(self, browser_key: str) -> Callable[[str, Dict[str, Any]], None]:
        """Return (or create) a telemetry observer function for the browser key."""
        if browser_key in self._observers:
            return self._observers[browser_key]

        def observer(event: str, payload: Dict[str, Any]) -> None:
            record = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "browser_key": browser_key,
                "event": event,
                "payload": payload,
            }
            self.logger.debug(" Browser telemetry %s", record)
            try:
                with self._telemetry_lock:
                    with open(self._telemetry_path, "a", encoding="utf-8") as handle:
                        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            except Exception as exc:  # pragma: no cover - telemetry best effort
                self.logger.warning("・・Failed to persist browser telemetry: %s", exc)

        self._observers[browser_key] = observer
        return observer

    def _create_edge_browser(self, profile_name: str, custom_options: Dict[str, Any] = None):
        """Create Edge browser with anti-detection settings"""
        edge_options = EdgeOptions()

        # Anti-detection flags
        edge_options.add_argument('--disable-blink-features=AutomationControlled')
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        edge_options.add_experimental_option('useAutomationExtension', False)

        # Standard settings
        edge_options.add_argument('--window-size=1920,1080')
        edge_options.add_argument('--start-maximized')
        edge_options.add_argument('--disable-gpu')
        edge_options.add_argument('--no-sandbox')
        edge_options.add_argument('--disable-dev-shm-usage')

        # User agent
        edge_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0')

        # Map profile names to actual Edge profile directories (must match x_anti_detection_poster.py)
        profile_mapping = {
            'x_foundups': 'O:/Foundups-Agent/modules/platform_integration/x_twitter/data/edge_profile_foundups',
        }

        profile_dir = profile_mapping.get(profile_name)
        if not profile_dir:
            # Fallback to default location
            profile_dir = f"O:/Foundups-Agent/modules/platform_integration/browser_profiles/{profile_name}/edge"

        os.makedirs(profile_dir, exist_ok=True)
        edge_options.add_argument(f'--user-data-dir={profile_dir}')
        edge_options.add_argument('--profile-directory=Default')

        # Apply custom options if provided
        if custom_options:
            for key, value in custom_options.items():
                if key == 'headless' and value:
                    edge_options.add_argument('--headless')

        driver = webdriver.Edge(options=edge_options)

        # Override navigator.webdriver flag
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        return driver

    def close_browser(self, browser_type: str, profile_name: str):
        """Close a specific browser instance"""
        browser_key = f"{browser_type}_{profile_name}"

        if browser_key in self._browsers:
            try:
                browser = self._browsers[browser_key]
                browser.quit()
                self.logger.info(f" Closed browser: {browser_key}")
            except Exception as e:
                self.logger.warning(f"・・Error closing browser: {e}")
            finally:
                del self._browsers[browser_key]
                with self._allocations_lock:
                    self._allocations.pop(browser_key, None)

    def close_all_browsers(self):
        """Close all browser instances"""
        for browser_key in list(self._browsers.keys()):
            browser_type, profile_name = browser_key.split('_', 1)
            self.close_browser(browser_type, profile_name)

        self.logger.info(" All browsers closed")

    def release_browser(self, browser_type: str, profile_name: str, dae_name: Optional[str] = None) -> None:
        """
        Release an allocation without closing the browser.

        If `dae_name` is provided, only releases if the allocation matches.
        """
        browser_key = f"{browser_type}_{profile_name}"
        with self._allocations_lock:
            current_owner = self._allocations.get(browser_key)
            if current_owner is None:
                return
            if dae_name and current_owner != dae_name:
                return
            self._allocations.pop(browser_key, None)

    def get_allocations(self) -> Dict[str, str]:
        """Return a snapshot of current browser allocations."""
        with self._allocations_lock:
            return dict(self._allocations)

    def get_active_browsers(self) -> Dict[str, bool]:
        """Get status of all browser instances"""
        status = {}
        for browser_key, browser in self._browsers.items():
            try:
                _ = browser.current_url
                status[browser_key] = True
            except:
                status[browser_key] = False
        return status


# Singleton instance
_browser_manager = None


def get_browser_manager() -> BrowserManager:
    """Get singleton browser manager instance"""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager
