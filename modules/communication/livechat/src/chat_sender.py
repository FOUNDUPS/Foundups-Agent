"""
Chat Sender

Sends messages to YouTube Live Chat with rate limiting and duplication checks.

NAVIGATION: Outputs responses to chat with throttle safeguards.
-> Called by: livechat_core.py::send_chat_message / MessageProcessor pipeline
-> Delegates to: YouTube liveChatMessages.insert API, IntelligentThrottleManager
-> Related: NAVIGATION.py -> PROBLEMS["Chat messages not sending"]
-> Quick ref: NAVIGATION.py -> NEED_TO["send throttled chat reply"]
"""

import logging
import os
import re
import asyncio
import random
import time
from typing import Optional
import googleapiclient.errors

from modules.communication.livechat.src.automation_gates import stop_active, stop_file_path

logger = logging.getLogger(__name__)

_UNICODE_TAG_RE = re.compile(r"\[U\+([0-9A-Fa-f]{4,6})\]")

def _convert_unicode_tags_to_emoji(text: str) -> str:
    """Convert [U+XXXX] tags to actual emoji characters."""
    if not text:
        return text
    def _replace(match: re.Match) -> str:
        try:
            return chr(int(match.group(1), 16))
        except Exception:
            return match.group(0)
    return _UNICODE_TAG_RE.sub(_replace, text)

def _env_truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")

class ChatSender:
    """Handles sending messages to YouTube Live Chat with human-like random delays."""
    
    def __init__(self, youtube_service, live_chat_id=None):
        self.youtube = youtube_service
        self.live_chat_id = live_chat_id
        self.bot_channel_id = None
        self._send_lock = asyncio.Lock()  # Prevent concurrent sends (anti-spam + consistent throttling)
        self.send_delay = 2.0  # Base delay between sends to avoid rate limiting
        
        # WSP Enhancement: Random delay configuration for human-like behavior
        self.random_delay_enabled = True
        self.min_random_delay = 0.5  # Minimum random delay (seconds)
        self.max_random_delay = 3.0  # Maximum random delay (seconds)

        # NOTE: Throttling is handled centrally by livechat_core.py's IntelligentThrottleManager
        # This class should NOT do its own throttling to avoid duplicate logic
        
    async def send_message(self, message_text: str, response_type: str = 'general', skip_delay: bool = False) -> bool:
        """
        Send a message to the live chat with adaptive throttling.

        Args:
            message_text: The message to send
            response_type: Type of response (consciousness, factcheck, maga, general)
            skip_delay: If True, skip the adaptive delay (for greetings/broadcasts)

        Returns:
            True if message was sent successfully, False otherwise
        """
        reviewed_text = getattr(message_text, 'reviewed_text', None)
        theme_snapshot = getattr(message_text, 'theme_snapshot', None)
        if stop_active():
            run_id = os.getenv("YT_AUTOMATION_RUN_ID", "").strip()
            logger.warning(
                f"[AUTOMATION-AUDIT] run_id={run_id or 'unset'} livechat_send=disabled (stop_file={stop_file_path()})"
            )
            return False

        if not _env_truthy("YT_AUTOMATION_ENABLED", "true"):
            run_id = os.getenv("YT_AUTOMATION_RUN_ID", "").strip()
            logger.warning(f"[AUTOMATION-AUDIT] run_id={run_id or 'unset'} livechat_send=disabled (YT_AUTOMATION_ENABLED=false)")
            return False

        if not _env_truthy("YT_LIVECHAT_SEND_ENABLED", "true"):
            run_id = os.getenv("YT_AUTOMATION_RUN_ID", "").strip()
            logger.warning(f"[AUTOMATION-AUDIT] run_id={run_id or 'unset'} livechat_send=disabled (YT_LIVECHAT_SEND_ENABLED=false)")
            return False

        if _env_truthy("YT_LIVECHAT_DRY_RUN", "false"):
            run_id = os.getenv("YT_AUTOMATION_RUN_ID", "").strip()
            logger.info(f"[AUTOMATION-AUDIT] run_id={run_id or 'unset'} livechat_send=dry_run type={response_type} chars={len(message_text or '')}")
            logger.info(f"[DRY-RUN] Would send: {message_text}")
            return True

        if not message_text or not message_text.strip():
            logger.warning("[WARN] Cannot send empty message")
            return False

        # Serialize all sends to avoid bursty multi-task behavior (multiple modules calling send at once).
        async with self._send_lock:
            # CRITICAL FIX: YouTube Live Chat has 200 character limit
            # Truncate messages that exceed limit to prevent INVALID_REQUEST_METADATA error
            MAX_MESSAGE_LENGTH = 200
            if len(message_text) > MAX_MESSAGE_LENGTH:
                original_length = len(message_text)

                # Smart truncation: Preserve @mentions at start
                if message_text.startswith('@'):
                    import re
                    mention_match = re.match(r'(@[A-Za-z0-9_-]+[\s:,!]*)', message_text)
                    if mention_match:
                        mention = mention_match.group(1)
                        remaining_space = MAX_MESSAGE_LENGTH - len(mention) - 3
                        rest = message_text[len(mention):remaining_space + len(mention)]
                        message_text = mention + rest + "..."
                        logger.info(f"[TRUNCATE] Smart truncate: Preserved @mention, {original_length}->{len(message_text)} chars")
                    else:
                        message_text = message_text[:MAX_MESSAGE_LENGTH - 3] + "..."
                        logger.warning(f"[WARN] Message truncated from {original_length} to {MAX_MESSAGE_LENGTH} chars (YouTube limit)")
                else:
                    message_text = message_text[:MAX_MESSAGE_LENGTH - 3] + "..."
                    logger.warning(f"[WARN] Message truncated from {original_length} to {MAX_MESSAGE_LENGTH} chars (YouTube limit)")

            # CRITICAL: Validate all @mentions in the message before sending
            # If we can't @mention properly, don't send the message at all
            if '@' in message_text:
                import re
                mentions = re.findall(r'@([A-Za-z0-9_-]+)', message_text)
                for username in mentions:
                    if not self._is_valid_mention(username):
                        logger.warning(f"[FORBIDDEN] BLOCKING message - cannot @mention '{username}': {message_text[:100]}...")
                        return False
                logger.debug("[OK] All @mentions validated in message")

            # GLOBAL THROTTLING: Apply minimum delays to ALL messages to prevent spam
            # Even "priority" messages get throttled to avoid quota exhaustion
            await self._apply_global_throttling(response_type, skip_delay)

            try:
                # Ensure we have bot channel ID
                if not self.bot_channel_id:
                    await self._get_bot_channel_id()

                # Apply additional random delays for human-like behavior (except highest priority)
                if skip_delay and response_type == 'timeout_announcement':
                    logger.info("[LIGHTNING][GAME] ULTIMATE PRIORITY: Minimal throttling for timeout announcement")
                elif skip_delay:
                    logger.info("[LIGHTNING] Reduced throttling for priority message")
                    if self.random_delay_enabled:
                        min_delay = min(0.5, self.min_random_delay)
                        random_delay = random.uniform(min_delay, min_delay + 1.0)
                        logger.debug(f"[TIMER] Priority message delay: {random_delay:.2f}s")
                        await asyncio.sleep(random_delay)

                # WSP Enhancement: Add random pre-send delay for human-like behavior
                # Skip for timeout announcements (highest priority)
                if self.random_delay_enabled and response_type != 'timeout_announcement':
                    random_delay = random.uniform(self.min_random_delay, self.max_random_delay)
                    logger.debug(f"[TIMER] Additional random delay: {random_delay:.2f}s")
                    await asyncio.sleep(random_delay)

                run_id = os.getenv("YT_AUTOMATION_RUN_ID", "").strip() or "unset"
                logger.info(f"📤 Sending message (type={response_type} run_id={run_id}): {message_text}")

                # CRITICAL FIX: Convert Unicode tags to emoji before YouTube send
                # YouTube API doesn't render [U+XXXX] tags - need actual emoji characters
                message_text = _convert_unicode_tags_to_emoji(message_text)
                logger.debug(
                    f"[EMOJI] After conversion: {message_text.encode('ascii', 'backslashreplace').decode('ascii')}"
                )

                # Recheck after every await/delay and before the network effect.
                if reviewed_text is not None:
                    from modules.communication.livechat.src.operator_command_queue import load_active_theme
                    if str(message_text) != reviewed_text or load_active_theme('livechat') != theme_snapshot:
                        return False

                # Prepare message data
                message_data = {
                    "snippet": {
                        "liveChatId": self.live_chat_id,
                        "type": "textMessageEvent",
                        "textMessageDetails": {
                            "messageText": message_text
                        }
                    }
                }

                # Send the message
                response = self.youtube.liveChatMessages().insert(
                    part="snippet",
                    body=message_data
                ).execute()

                message_id = response.get("id", "unknown")
                logger.info(f"[OK] Message sent successfully (ID: {message_id})")

                # NOTE: Response recording is handled by livechat_core.py's IntelligentThrottleManager
                await asyncio.sleep(self.send_delay)
                return True

            except googleapiclient.errors.HttpError as e:
                error_details = str(e)

                if "quotaExceeded" in error_details or "quota" in error_details.lower():
                    logger.error(f"[DATA] Quota exceeded while sending message: {e}")
                elif "forbidden" in error_details.lower():
                    logger.error(f"[FORBIDDEN] Forbidden error sending message (check permissions): {e}")
                elif "unauthorized" in error_details.lower():
                    logger.error(f"[U+1F510] Unauthorized error sending message: {e}")
                    raise
                else:
                    logger.error(f"[FAIL] HTTP error sending message: {e}")

                return False

            except Exception as e:
                logger.error(f"[FAIL] Unexpected error sending message: {e}")
                return False
    
    def configure_random_delays(self, enabled: bool = True, min_delay: float = 0.5, max_delay: float = 3.0):
        """
        Configure random delay settings for human-like behavior.
        
        Args:
            enabled: Whether to enable random delays
            min_delay: Minimum random delay in seconds
            max_delay: Maximum random delay in seconds
        """
        self.random_delay_enabled = enabled
        self.min_random_delay = max(0.1, min_delay)  # Ensure minimum of 0.1s
        self.max_random_delay = max(self.min_random_delay + 0.1, max_delay)  # Ensure max > min
        
        logger.info(f"[U+1F3B2] Random delays configured: enabled={enabled}, range={self.min_random_delay:.1f}s-{self.max_random_delay:.1f}s")
    
    async def send_greeting(self, greeting_message: str) -> bool:
        """
        Send a greeting message to the chat.
        
        Args:
            greeting_message: The greeting message to send
            
        Returns:
            True if greeting was sent successfully, False otherwise
        """
        logger.info("[U+1F44B] Sending greeting message to chat")
        
        if not greeting_message:
            greeting_message = "FoundUps online. Share your goal and we will map the path."
        
        success = await self.send_message(greeting_message)
        
        if success:
            logger.info("[OK] Greeting message sent successfully")
        else:
            logger.warning("[WARN] Failed to send greeting message")
        
        return success
    
    async def _get_bot_channel_id(self) -> Optional[str]:
        """Get the bot's channel ID for message sending."""
        try:
            logger.debug("[SEARCH] Fetching bot channel ID")
            
            response = self.youtube.channels().list(
                part="id",
                mine=True
            ).execute()
            
            items = response.get("items", [])
            if items:
                self.bot_channel_id = items[0]["id"]
                logger.info(f"[BOT] Bot channel ID: {self.bot_channel_id}")
                return self.bot_channel_id
            else:
                logger.error("[FAIL] No channel found for authenticated user")
                return None
                
        except Exception as e:
            logger.error(f"[FAIL] Error getting bot channel ID: {e}")
            return None
    
    def update_youtube_service(self, new_service):
        """
        Update the YouTube service (useful after token rotation).
        
        Args:
            new_service: New authenticated YouTube service
        """
        self.youtube = new_service
        self.bot_channel_id = None  # Reset channel ID to refetch with new service
        logger.info("[REFRESH] YouTube service updated")
    
    def _is_valid_mention(self, username: str) -> bool:
        """
        Check if username can be properly @mentioned on YouTube.
        YouTube needs usernames to be at least 2 chars and not contain certain characters.
        """
        if not username:
            return False
        
        # Username too short - single character usernames don't work
        # But 2-letter usernames like "JS" ARE valid on YouTube
        if len(username) < 2:
            logger.debug(f"Username '{username}' too short for @mention")
            return False
            
        # Contains spaces or special chars that break mentions
        invalid_chars = [' ', '\n', '\t', '@', '#', '$', '%', '^', '&', '*', '(', ')', '[', ']', '{', '}', ':', ';', '"', "'", ',', '.', '!', '?']
        if any(char in username for char in invalid_chars):
            logger.debug(f"Username '{username}' contains invalid chars for @mention")
            return False
            
        # Check if it looks like it might be part of the message text, not a real username
        # For example: "@mentioned" at the end of "You've been @mentioned" 
        if username.lower() in ['mentioned', 'everyone', 'here', 'all']:
            logger.debug(f"Username '{username}' appears to be a common word, not a real username")
            return False
            
        return True
    
    def get_sender_stats(self) -> dict:
        """Get sender statistics and status."""
        return {
            "live_chat_id": self.live_chat_id,
            "bot_channel_id": self.bot_channel_id,
            "send_delay": self.send_delay,
            "random_delay_enabled": self.random_delay_enabled,
            "random_delay_range": f"{self.min_random_delay:.1f}s-{self.max_random_delay:.1f}s",
            "has_service": self.youtube is not None
        }

    async def _apply_global_throttling(self, response_type: str, skip_delay: bool) -> None:
        """
        Apply global throttling to ALL messages to prevent spam and quota exhaustion.

        This enforces minimum delays between messages regardless of priority.
        """
        current_time = time.time()

        # Initialize global throttling tracking if needed
        if not hasattr(self, '_last_message_time'):
            self._last_message_time = 0
            self._message_count = 0

        # Global minimum delays to prevent spam (in seconds)
        global_delays = {
            'default': 2.0,  # Minimum 2 seconds between any messages
            'greeting': 5.0,  # Greetings need more spacing
            'update': 10.0,   # Update broadcasts need significant spacing
            'timeout_announcement': 0.5,  # Allow faster timeout announcements
            'consciousness': 3.0,  # Consciousness responses
            'maga': 15.0,     # MAGA responses (additional throttling)
        }

        # Determine appropriate delay based on message type
        if 'greeting' in response_type.lower() or 'greeting' in str(self).lower():
            min_delay = global_delays['greeting']
        elif 'update' in response_type.lower() or 'broadcast' in str(self).lower():
            min_delay = global_delays['update']
        elif response_type in global_delays:
            min_delay = global_delays[response_type]
        else:
            min_delay = global_delays['default']

        # Calculate time since last message
        time_since_last = current_time - self._last_message_time

        if time_since_last < min_delay:
            # Need to wait
            wait_time = min_delay - time_since_last
            logger.info(f"[THROTTLE] GLOBAL THROTTLE: Waiting {wait_time:.1f}s before sending {response_type} message")
            await asyncio.sleep(wait_time)
        else:
            logger.debug(f"[OK] GLOBAL THROTTLE: OK to send {response_type} message (gap: {time_since_last:.1f}s)")

        # Update tracking
        self._last_message_time = time.time()
        self._message_count += 1

        # Log spam prevention stats periodically
        if self._message_count % 10 == 0:
            logger.info(f"[DATA] GLOBAL THROTTLE: Sent {self._message_count} messages, enforcing anti-spam delays") 
