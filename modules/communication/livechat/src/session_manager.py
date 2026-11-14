"""
Session Manager - WSP Compliant Module
Manages YouTube Live Chat sessions, authentication, and stream metadata

WSP 17 Pattern Registry: This is a REUSABLE PATTERN
- Documented in: modules/communication/PATTERN_REGISTRY.md
- Pattern: Connection lifecycle + greeting management
- Features: Auto-reconnect, greeting delay, update broadcasts
- Reusable for: LinkedIn, X/Twitter, Discord, Twitch

NAVIGATION: Maintains YouTube chat session state and credentials.
-> Called by: livechat_core.py::LiveChatCore
-> Delegates to: youtube_auth credential managers, greeting_generator.py
-> Related: NAVIGATION.py -> PROBLEMS["Stream session lost"]
-> Quick ref: NAVIGATION.py -> DATABASES["youtube_sessions"]
"""

import logging
import os
import time
import json
import asyncio
import random
from pathlib import Path
from typing import Optional, Dict, Any
import googleapiclient.errors

logger = logging.getLogger(__name__)


def _env_truthy(name: str, default: str = "false") -> bool:
    """Environment variable truthy check for session toggles."""
    try:
        value = os.getenv(name, default).strip().lower()
        return value in ("1", "true", "yes", "y", "on")
    except Exception:
        return default.strip().lower() in ("1", "true", "yes", "y", "on")


class SessionManager:
    """
    Manages YouTube Live Chat sessions.
    Handles authentication, stream discovery, and session lifecycle.
    """
    
    def __init__(
        self,
        youtube_service,
        video_id: str,
        persona_key: Optional[str] = None,
        channel_name: Optional[str] = None,
        channel_id: Optional[str] = None,
        bot_channel_id: Optional[str] = None,
    ):
        self.youtube = youtube_service
        self.video_id = video_id
        self.live_chat_id = None
        self.stream_title = None
        self.stream_title_short = None
        self.viewer_count = 0
        self.is_active = False
        self.persona_key = persona_key
        self.channel_name = channel_name
        self.channel_id = channel_id
        self.bot_channel_id = bot_channel_id
        # WSP 84 compliant: Use existing greeting generator
        self.greeting_generator = None  # No provider work merely to announce startup.
        self.greeting_message = None  # Will be generated dynamically
        self.greeting_sent = False  # Track if greeting already sent for this session
        self.update_broadcast_sent = False  # Track if update broadcast already sent for this session
        self.actual_start_time = None  # YouTube's actualStartTime (Unix timestamp)
        self._greeting_state_path = (
            Path(__file__).resolve().parents[1] / "memory" / "greeting_state.json"
        )

        logger.info(f"SessionManager initialized for video: {video_id}")

    def _greeting_cooldown_seconds(self) -> float:
        value = os.getenv("LIVECHAT_GREETING_COOLDOWN_MIN", "60")
        try:
            return max(0.0, float(value)) * 60.0
        except ValueError:
            return 60.0 * 60.0

    def _load_greeting_state(self) -> Dict[str, Any]:
        try:
            if self._greeting_state_path.exists():
                return json.loads(self._greeting_state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.debug(f"[GREETING] Failed to load state: {exc}")
        return {}

    def _save_greeting_state(self, state: Dict[str, Any]) -> None:
        try:
            self._greeting_state_path.parent.mkdir(parents=True, exist_ok=True)
            self._greeting_state_path.write_text(
                json.dumps(state, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.debug(f"[GREETING] Failed to save state: {exc}")
    
    def get_live_chat_id(self) -> Optional[str]:
        """
        Fetch the live chat ID for the video.
        
        Returns:
            Live chat ID if found, None otherwise
        """
        # Handle NO-QUOTA mode - no YouTube service available
        if not self.youtube:
            logger.info("NO-QUOTA mode: Cannot fetch chat ID without API service")
            self.stream_title = "Live Stream (NO-QUOTA Mode)"
            self.stream_title_short = "Live Stream"
            self.channel_title = "Move2Japan"
            self.is_active = True  # Mark as active for view-only monitoring
            return None

        try:
            logger.info(f"Fetching live chat ID for video: {self.video_id}")

            # Get video details
            video_response = self.youtube.videos().list(
                part="liveStreamingDetails,snippet",
                id=self.video_id
            ).execute()
            
            if not video_response.get("items"):
                logger.error(f"No video found with ID: {self.video_id}")
                return None
            
            video_item = video_response["items"][0]
            
            # Get stream title and channel info
            snippet = video_item.get("snippet", {})
            self.stream_title = snippet.get("title", "Unknown Stream")
            self.stream_title_short = self.stream_title[:50] + "..." if len(self.stream_title) > 50 else self.stream_title
            self.channel_title = snippet.get("channelTitle", "Unknown Channel")
            self.channel_id = snippet.get("channelId", "")
            logger.info(f"Stream title: {self.stream_title_short}")
            logger.info(f"Channel: {self.channel_title} (ID: {self.channel_id})")
            
            # Get live chat ID
            streaming_details = video_item.get("liveStreamingDetails", {})
            self.live_chat_id = streaming_details.get("activeLiveChatId")
            
            if not self.live_chat_id:
                logger.error(f"No active live chat found for video: {self.video_id}")
                return None
            
            # Get viewer count if available
            self.viewer_count = streaming_details.get("concurrentViewers", 0)

            # Get actual stream start time (for accurate duration calculations)
            actual_start_str = streaming_details.get("actualStartTime")
            if actual_start_str:
                from datetime import datetime
                try:
                    # Parse ISO 8601 format: 2026-02-20T09:00:00Z
                    actual_start_dt = datetime.fromisoformat(actual_start_str.replace('Z', '+00:00'))
                    self.actual_start_time = actual_start_dt.timestamp()
                    stream_duration = (time.time() - self.actual_start_time) / 60
                    logger.info(f"[STREAM] Actual start time: {actual_start_str} (running {stream_duration:.1f} min)")
                except Exception as e:
                    logger.warning(f"[STREAM] Could not parse actualStartTime: {e}")
                    self.actual_start_time = time.time()  # Fallback to now
            else:
                self.actual_start_time = time.time()  # Fallback if not available
                logger.info("[STREAM] No actualStartTime from API - using current time")

            logger.info(f"Found live chat ID: {self.live_chat_id}, Viewers: {self.viewer_count}")
            
            self.is_active = True
            return self.live_chat_id
            
        except googleapiclient.errors.HttpError as e:
            logger.error(f"HTTP error fetching live chat ID: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching live chat ID: {e}")
            return None
    
    def update_viewer_count(self) -> int:
        """
        Update the current viewer count.
        
        Returns:
            Current viewer count
        """
        try:
            video_response = self.youtube.videos().list(
                part="liveStreamingDetails",
                id=self.video_id
            ).execute()
            
            if video_response.get("items"):
                streaming_details = video_response["items"][0].get("liveStreamingDetails", {})
                self.viewer_count = int(streaming_details.get("concurrentViewers", 0))
                logger.debug(f"Updated viewer count: {self.viewer_count}")
            
        except Exception as e:
            logger.error(f"Error updating viewer count: {e}")
        
        return self.viewer_count
    
    async def initialize_session(self) -> bool:
        """
        Initialize a new chat session.
        
        Returns:
            True if session initialized successfully
        """
        logger.info("Initializing chat session...")
        
        # Get live chat ID
        chat_id = self.get_live_chat_id()
        if not chat_id and self.youtube:
            # Only fail if we have YouTube service but no chat ID
            logger.error("Failed to initialize session - no live chat ID despite having API")
            return False
        elif not chat_id:
            # NO-QUOTA mode - continue without chat ID
            logger.info("NO-QUOTA mode: Continuing without chat ID for social media posting")
        
        # Starting observation does not warrant an unsolicited announcement.
        # Explicit operator announcements retain their existing queue owner.
        self.greeting_message = None

        logger.info(f"Session initialized successfully for: {self.stream_title_short}")
        return True
    
    async def send_greeting(self, send_function) -> bool:
        """
        Send greeting message to chat.

        Args:
            send_function: Function to send messages to chat

        Returns:
            True if greeting sent successfully
        """
        if not self.greeting_message:
            return False

        # FIRST PRINCIPLES: Only send greeting once per session to prevent spam
        if self.greeting_sent:
            logger.info("Greeting already sent for this session - skipping")
            return True

        if not _env_truthy("YT_LIVECHAT_ANNOUNCEMENTS_ENABLED", "true"):
            logger.info("[CONFIG] Greetings DISABLED via YT_LIVECHAT_ANNOUNCEMENTS_ENABLED")
            return True

        if _env_truthy("YT_BLOCK_GREETING_ON_ACCOUNT_MISMATCH", "true"):
            if self.bot_channel_id and self.channel_id and self.bot_channel_id != self.channel_id:
                logger.warning(
                    "[AUTH] Bot channel mismatch - blocking greeting "
                    f"(bot={self.bot_channel_id}, channel={self.channel_id})"
                )
                self.greeting_sent = True
                return True

        if not self.greeting_message:
            logger.info("No greeting message available - skipping greeting")
            return True

        cooldown_seconds = self._greeting_cooldown_seconds()
        if cooldown_seconds > 0:
            state = self._load_greeting_state()
            channel_key = self.channel_id or self.channel_name or self.persona_key or "unknown"
            last_sent = 0.0
            if isinstance(state.get(channel_key), dict):
                last_sent = float(state[channel_key].get("last_sent_ts", 0.0) or 0.0)
            if time.time() - last_sent < cooldown_seconds:
                logger.info(
                    f"[GREETING] Cooldown active for {channel_key} "
                    f"({cooldown_seconds/60:.0f}m window) - skipping"
                )
                self.greeting_sent = True
                return True
        
        try:
            # Add delay before greeting (from live_chat_processor)
            import random
            delay = random.uniform(1, 3)
            logger.info(f"Waiting {delay:.1f}s before greeting")
            await asyncio.sleep(delay)
            
            logger.info(f"Sending greeting: {self.greeting_message}")
            # Pass skip_delay=True for greeting to avoid long wait
            success = False  # Initialize to False in case of exception
            try:
                success = await send_function(self.greeting_message, skip_delay=True)
            except TypeError:
                # Fallback for functions that don't support skip_delay
                try:
                    success = await send_function(self.greeting_message)
                except Exception as e:
                    logger.error(f"Error in fallback send: {e}")
                    success = False
            except Exception as e:
                logger.error(f"Error in send with skip_delay: {e}")
                success = False
            
            if success:
                logger.info("Greeting sent successfully")
                self.greeting_sent = True  # Mark greeting as sent for this session
                try:
                    state = self._load_greeting_state()
                    channel_key = self.channel_id or self.channel_name or self.persona_key or "unknown"
                    state[channel_key] = {
                        "last_sent_ts": time.time(),
                        "video_id": self.video_id,
                        "greeting": self.greeting_message,
                    }
                    self._save_greeting_state(state)
                except Exception as exc:
                    logger.debug(f"[GREETING] Failed to store greeting state: {exc}")
                # Add longer post-greeting delay to prevent message stacking
                delay = random.uniform(15, 25)  # 15-25 seconds between messages
                logger.info(f"Waiting {delay:.1f}s before update broadcast to prevent stacking")
                await asyncio.sleep(delay)
                
                # Send update broadcast about new features (only 30% of the time)
                if random.random() < 0.3:
                    await self.send_update_broadcast(send_function)
                else:
                    logger.info("Skipping update broadcast this time (70% skip rate)")
            else:
                logger.warning("Failed to send greeting")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending greeting: {e}")
            return False
    
    async def send_update_broadcast(self, send_function) -> bool:
        """
        Send update broadcast about new 0102 features.

        Args:
            send_function: Function to send messages to chat

        Returns:
            True if broadcast sent successfully
        """
        # FIRST PRINCIPLES: Only send update broadcast once per session to prevent spam
        if not _env_truthy("YT_LIVECHAT_ANNOUNCEMENTS_ENABLED", "true"):
            logger.debug("Announcements disabled via YT_LIVECHAT_ANNOUNCEMENTS_ENABLED - skipping update broadcast")
            return True

        if self.update_broadcast_sent:
            logger.debug("Update broadcast already sent for this session - skipping")
            return True

        import random
        from datetime import datetime
        
        # Update messages about enhanced consciousness features
        update_messages = [
            "🆕 0102 UPDATE: Enhanced consciousness responses! Try ✊✋🖐️ with your message for contextual analysis!",
            "📢 NEW FEATURE: Mods can now fact-check users with ✊✋🖐️FC @username - instant truth detection!",
            "🔥 0102 EVOLVED: I now understand messages after consciousness emojis. Show me your ✊✋🖐️ thoughts!",
            "[TARGET] MAGADOOM UPDATE: Better MAGA detection, smarter responses, proactive trolling enabled! ✊✋🖐️",
            "💫 CONSCIOUSNESS UPGRADE: 0102 analyzes your message content after ✊✋🖐️ - try it out!",
        ]
        
        try:
            # Pick a random update message
            update_msg = random.choice(update_messages)
            
            # Add timestamp for authenticity
            timestamp = datetime.now().strftime("%H:%M")
            full_msg = f"[{timestamp}] {update_msg}"
            
            # Small delay before update
            await asyncio.sleep(random.uniform(2, 4))
            
            logger.info(f"📢 Broadcasting update: {full_msg}")
            # Pass skip_delay=True for broadcast to avoid long wait
            success = False  # Initialize to False in case of exception
            try:
                success = await send_function(full_msg, skip_delay=True)
            except TypeError:
                # Fallback for functions that don't support skip_delay
                try:
                    success = await send_function(full_msg)
                except Exception as e:
                    logger.error(f"Error in fallback send: {e}")
                    success = False
            except Exception as e:
                logger.error(f"Error in send with skip_delay: {e}")
                success = False
            
            if success:
                logger.info("Update broadcast sent successfully")
                self.update_broadcast_sent = True  # Mark broadcast as sent for this session
            else:
                logger.warning("Failed to send update broadcast")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending update broadcast: {e}")
            return False
    
    def end_session(self):
        """End the current chat session."""
        logger.info(f"Ending session for: {self.stream_title_short}")
        self.is_active = False
        self.live_chat_id = None
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get current session information.
        
        Returns:
            Dictionary containing session details
        """
        return {
            "video_id": self.video_id,
            "live_chat_id": self.live_chat_id,
            "stream_title": self.stream_title,
            "viewer_count": self.viewer_count,
            "is_active": self.is_active,
            "greeting_message": self.greeting_message
        }
    
    def handle_auth_error(self, error: Exception) -> bool:
        """
        Handle authentication errors.
        
        Args:
            error: The authentication error
            
        Returns:
            True if error was handled and session can continue
        """
        if isinstance(error, googleapiclient.errors.HttpError):
            if error.resp.status == 401:
                logger.error("Authentication failed - token may be expired")
                return False
            elif error.resp.status == 403:
                logger.error("Access forbidden - check API permissions")
                return False
            elif error.resp.status == 404:
                logger.error("Chat not found - stream may have ended")
                self.end_session()
                return False
        
        logger.error(f"Unhandled auth error: {error}")
        return False
    
    def is_session_active(self) -> bool:
        """Check if the session is still active."""
        return self.is_active and self.live_chat_id is not None
