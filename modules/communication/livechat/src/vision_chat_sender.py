"""
Vision Chat Sender - UI-TARS based chat posting
================================================

WSP Compliance: WSP 77, WSP 27 (DAE Phases)

Posts messages to YouTube Live Chat via UI-TARS browser automation.
ZERO API quota usage - bypasses YouTube API limits.

NAVIGATION:
-> Called by: chat_sender.py as fallback when quota is low
-> Uses: Selenium for DOM interaction
-> Related: party_reactor.py (same browser connection pattern)
"""

import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _env_truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")


class VisionChatSender:
    """Posts messages to YouTube Live Chat via browser automation."""
    
    def __init__(self):
        self.driver = None
        self.in_iframe = False
        self._last_post_time = 0
        self._min_post_interval = 2.0  # Minimum seconds between posts
        
    def _connect_to_chrome(self) -> bool:
        """Connect to Chrome instance with remote debugging."""
        if self.driver:
            try:
                # Check if connection is still alive
                _ = self.driver.current_url
                return True
            except Exception:
                self.driver = None
                self.in_iframe = False
        
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            port = int(os.getenv("FOUNDUPS_CHROME_PORT", "9222"))
            opts = Options()
            opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            self.driver = webdriver.Chrome(options=opts)
            from modules.infrastructure.foundups_selenium.src.youtube_verification import install_youtube_verification_guard
            install_youtube_verification_guard(self.driver, port)
            logger.info(f"[VISION-CHAT] Connected to Chrome: {self.driver.current_url[:40]}...")
            return True
        except Exception as e:
            logger.warning(f"[VISION-CHAT] Chrome connection failed: {e}")
            return False
    
    def _switch_to_chat_iframe(self) -> bool:
        """Switch to the YouTube live chat iframe."""
        try:
            from selenium.webdriver.common.by import By
            
            self.driver.switch_to.default_content()
            iframe = self.driver.find_element(By.CSS_SELECTOR, 'iframe#chatframe')
            self.driver.switch_to.frame(iframe)
            self.in_iframe = True
            return True
        except Exception as e:
            logger.warning(f"[VISION-CHAT] No chat iframe: {e}")
            self.in_iframe = False
            return False
    
    def _type_and_send(self, message: str) -> bool:
        """Type message into chat input and click send."""
        js = """
        var input = document.querySelector('div#input[contenteditable], yt-live-chat-text-input-field-renderer div[contenteditable]');
        if (input) {
            input.focus();
            input.textContent = arguments[0];
            input.dispatchEvent(new Event('input', {bubbles: true}));
            return 'typed';
        }
        return 'no_input';
        """
        
        try:
            result = self.driver.execute_script(js, message)
            
            if result != 'typed':
                logger.warning(f"[VISION-CHAT] Failed to type: {result}")
                return False
            
            time.sleep(0.3)  # Brief pause before clicking send
            
            # Click send button
            js_send = """
            var btn = document.querySelector('#send-button button, button#send-button, yt-button-renderer#send-button button');
            if (btn) {
                btn.click();
                return 'sent';
            }
            return 'no_button';
            """
            
            result = self.driver.execute_script(js_send)
            
            if result == 'sent':
                logger.info(f"[VISION-CHAT] ✅ Message posted: '{message[:50]}...'")
                return True
            else:
                logger.warning(f"[VISION-CHAT] Send button not found: {result}")
                return False
                
        except Exception as e:
            logger.error(f"[VISION-CHAT] Error posting message: {e}")
            return False
    
    async def post_message(self, message: str) -> bool:
        """
        Post a message to YouTube Live Chat via vision/browser.
        
        Args:
            message: The message text to post
            
        Returns:
            True if message was posted successfully
        """
        if not _env_truthy("YT_AUTOMATION_ENABLED", "true"):
            logger.warning("[VISION-CHAT] Disabled (YT_AUTOMATION_ENABLED=false)")
            return False
        if not _env_truthy("YT_LIVECHAT_UI_ACTIONS_ENABLED", "true"):
            logger.warning("[VISION-CHAT] Disabled (YT_LIVECHAT_UI_ACTIONS_ENABLED=false)")
            return False

        # Rate limiting
        now = time.time()
        if now - self._last_post_time < self._min_post_interval:
            wait_time = self._min_post_interval - (now - self._last_post_time)
            logger.debug(f"[VISION-CHAT] Rate limit: waiting {wait_time:.1f}s")
            time.sleep(wait_time)
        
        # Connect to Chrome
        if not self._connect_to_chrome():
            return False
        
        # Switch to chat iframe
        if not self._switch_to_chat_iframe():
            return False
        
        # Post the message
        success = self._type_and_send(message)
        
        if success:
            self._last_post_time = time.time()
        
        return success
    
    def post_message_sync(self, message: str) -> bool:
        """Synchronous version of post_message."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, run in executor
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(self._sync_post, message)
                    return future.result(timeout=10)
            else:
                return loop.run_until_complete(self.post_message(message))
        except Exception as e:
            logger.error(f"[VISION-CHAT] Sync post error: {e}")
            return self._sync_post(message)
    
    def _sync_post(self, message: str) -> bool:
        """Internal sync post implementation."""
        now = time.time()
        if now - self._last_post_time < self._min_post_interval:
            time.sleep(self._min_post_interval - (now - self._last_post_time))
        
        if not self._connect_to_chrome():
            return False
        if not self._switch_to_chat_iframe():
            return False
        
        success = self._type_and_send(message)
        if success:
            self._last_post_time = time.time()
        return success


# Global instance
_vision_sender = None


def get_vision_chat_sender() -> VisionChatSender:
    """Get or create global VisionChatSender instance."""
    global _vision_sender
    if _vision_sender is None:
        _vision_sender = VisionChatSender()
    return _vision_sender








