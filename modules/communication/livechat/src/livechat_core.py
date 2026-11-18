"""
LiveChat Core - WSP Compliant Module (<500 lines)
Core YouTube Live Chat listener using modular components

NAVIGATION: This is the central coordinator for YouTube chat
-> Called by: auto_moderator_dae.py (line 252)
-> Delegates to: message_processor.py, chat_poller.py, chat_sender.py
-> For social media: See stream_resolver -> simple_posting_orchestrator
-> For consciousness: See message_processor -> consciousness_handler
-> For throttling: See intelligent_throttle_manager.py
-> Quick ref: NAVIGATION.py -> MODULE_GRAPH['core_flows']['message_processing_flow']
"""

import logging
import os
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
import googleapiclient.errors

# Import WSP-compliant modules
from modules.communication.livechat.src.moderation_stats import ModerationStats
from modules.communication.livechat.src.session_manager import SessionManager
from modules.communication.livechat.src.message_processor import MessageProcessor
from modules.communication.livechat.src.chat_sender import ChatSender
from modules.communication.livechat.src.chat_poller import ChatPoller
from modules.infrastructure.system_health_monitor.src.system_health_analyzer import SystemHealthAnalyzer
from modules.communication.livechat.src.chat_memory_manager import get_chat_memory_manager
from modules.communication.livechat.src.stream_session_logger import get_session_logger
from modules.communication.livechat.src.breadcrumb_telemetry import get_breadcrumb_telemetry
from modules.communication.livechat.src.persona_registry import (
    get_persona_config,
    resolve_persona_key,
    resolve_channel_credential_set,
)
try:
    from modules.communication.livechat.src.quota_aware_poller import QuotaAwarePoller
except ImportError:
    QuotaAwarePoller = None
try:
    from modules.communication.livechat.src.intelligent_throttle_manager import IntelligentThrottleManager
except ImportError:
    IntelligentThrottleManager = None
try:
    from modules.platform_integration.youtube_auth.src.quota_intelligence import QuotaIntelligence
    from modules.platform_integration.youtube_auth.src.quota_monitor import QuotaMonitor
except ImportError:
    QuotaIntelligence = None
    QuotaMonitor = None

# WRE Integration for recursive learning
try:
    from modules.infrastructure.wre_core.recursive_improvement.src.wre_integration import (
        record_error, record_success
    )
except ImportError:
    record_error = None
    record_success = None

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
MAX_MESSAGES_PER_CALL = 200

def _get_forced_credential_set() -> Optional[int]:
    raw = os.getenv("YT_FORCE_CREDENTIAL_SET", "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None

class LiveChatCore:
    """
    Core YouTube Live Chat listener - WSP compliant version.
    Uses modular components for functionality.
    """
    
    def __init__(self, youtube_service, video_id: str, live_chat_id: Optional[str] = None,
                 channel_name: str = None, channel_id: str = None,
                 message_router = None):
        """
        Initialize LiveChatCore with modular components.

        Args:
            youtube_service: Authenticated YouTube service
            video_id: YouTube video/stream ID
            live_chat_id: Optional pre-fetched chat ID
            channel_name: Name of the channel owner
            channel_id: Channel ID of the owner
            message_router: Optional orchestrator message router for centralized processing
        """
        self.youtube = youtube_service
        self.video_id = video_id
        self.live_chat_id = live_chat_id
        self.channel_name = channel_name or "StreamOwner"
        self.channel_id = channel_id or "owner"
        self.stream_title = None
        self.next_page_token = None
        self.is_running = False
        self.memory_dir = "memory"
        self.processed_message_ids = set()
        self.recent_command_cache = {}  # Cache to prevent duplicate command responses
        self.message_timestamps = []  # Track message times for activity monitoring

        # Stream health monitoring (intelligent stream switching)
        self._last_message_time = time.time()  # Track chat activity
        self._inactivity_threshold_seconds = int(os.getenv("STREAM_INACTIVITY_THRESHOLD", "600"))  # 10 minutes default
        self._min_viewers_threshold = int(os.getenv("STREAM_MIN_VIEWERS", "5"))  # Minimum viable viewers
        self._health_check_enabled = os.getenv("STREAM_HEALTH_CHECK_ENABLED", "true").lower() in ("1", "true", "yes")
        logger.info(f"[STREAM-HEALTH] Monitoring enabled: {self._health_check_enabled}")
        if self._health_check_enabled:
            logger.info(f"[STREAM-HEALTH]   Inactivity threshold: {self._inactivity_threshold_seconds}s")
            logger.info(f"[STREAM-HEALTH]   Min viewers: {self._min_viewers_threshold}")

        # Orchestrator integration (surgical migration)
        self.message_router = message_router
        self.router_mode = message_router is not None

        # WSP-compliant hybrid memory manager (singleton for shared access)
        self.memory_manager = get_chat_memory_manager(self.memory_dir)
        
        # Initialize modular components
        self.chat_sender = ChatSender(youtube_service, live_chat_id)

        # Get bot channel ID to prevent self-responses
        bot_channel_id = None
        try:
            # Try to get bot channel ID synchronously if possible
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If event loop is running, we need to handle this differently
                logger.debug("Event loop running, skipping bot channel ID check")
            else:
                bot_channel_id = loop.run_until_complete(self.chat_sender._get_bot_channel_id())
        except Exception as e:
            logger.debug(f"Could not get bot channel ID: {e}")

        self.bot_channel_id = bot_channel_id
        self._refresh_persona_context()
        self.session_manager = SessionManager(
            youtube_service,
            video_id,
            persona_key=self.persona_key,
            channel_name=self.channel_name,
            channel_id=self.channel_id,
            bot_channel_id=self.bot_channel_id,
        )
        self.mod_stats = ModerationStats(self.memory_dir)
        self.message_processor = MessageProcessor(
            youtube_service,
            self.memory_manager,
            self.chat_sender,
            persona_key=self.persona_key,
            channel_name=self.channel_name,
            channel_id=self.channel_id,
            bot_channel_id=self.bot_channel_id,
            stream_title=self.stream_title,
        )
        self.chat_poller = ChatPoller(youtube_service, live_chat_id, self.channel_name, self.channel_id)
        
        # Health monitoring for duplicate detection and error tracking
        self.health_analyzer = SystemHealthAnalyzer()
        self.recent_messages_sent = []  # Track sent messages
        
        # NEW: Quota-aware polling with HOLOINDEX integration gap fix
        try:
            # Get credential set number from service
            cred_set = getattr(
                youtube_service,
                'credential_set',
                getattr(youtube_service, '_credential_set', 1)
            )
            # HOLOINDEX IMPROVEMENT: Pass oauth_manager for automatic token rotation
            oauth_manager = youtube_service if hasattr(youtube_service, 'rotate_credentials') else None
            self.quota_poller = QuotaAwarePoller(cred_set, oauth_manager) if QuotaAwarePoller else None
        except Exception as e:
            logger.warning(f"HOLOINDEX FIX: Failed to initialize quota poller with OAuth integration: {e}")
            self.quota_poller = None
        
        # AUTOMATIC: Intelligent throttle manager for API quota
        self.intelligent_throttle = None
        if IntelligentThrottleManager:
            try:
                from pathlib import Path
                memory_path = Path(self.memory_dir)
                self.intelligent_throttle = IntelligentThrottleManager(
                    min_delay=1.0,
                    max_delay=60.0,
                    throttle_window=60,
                    memory_path=memory_path
                )
                # Enable all intelligent features by default
                self.intelligent_throttle.enable_learning(True)
                self.intelligent_throttle.set_agentic_mode(True)
                logger.info("[AUTO] Intelligent throttle manager initialized - automatic API management enabled")
            except Exception as e:
                logger.warning(f"[AUTO] Could not initialize intelligent throttle: {e}")
                self.intelligent_throttle = None

        # REVOLUTIONARY: Intelligent credential rotation orchestration
        self.quota_intelligence = None
        logger.info(f"[REFRESH] [INIT] QuotaIntelligence available: {QuotaIntelligence is not None}")
        logger.info(f"[REFRESH] [INIT] QuotaMonitor available: {QuotaMonitor is not None}")

        if QuotaIntelligence and QuotaMonitor:
            try:
                quota_monitor = QuotaMonitor()
                self.quota_intelligence = QuotaIntelligence(quota_monitor)
                logger.info("[REFRESH] Intelligent credential rotation system initialized")
            except Exception as e:
                logger.warning(f"[REFRESH] Could not initialize quota intelligence: {e}", exc_info=True)
                self.quota_intelligence = None
        else:
            logger.critical("[REFRESH][FAIL] ROTATION SYSTEM DISABLED - QuotaIntelligence/QuotaMonitor not imported")

        # Log final status
        if self.quota_intelligence:
            logger.info("[REFRESH][OK] Rotation intelligence ACTIVE - will check every poll cycle")
        else:
            logger.critical("[REFRESH][FAIL] Rotation intelligence INACTIVE - manual rotation required")
        
        # Ensure memory directory exists
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # AUTOMATIC: Initialize WRE monitor for continuous improvement
        enable_wre_monitor = os.getenv("FOUNDUPS_ENABLE_WRE_MONITOR", "true").strip().lower() in ("1", "true", "yes", "y", "on")
        enable_wre = os.getenv("FOUNDUPS_ENABLE_WRE", "true").strip().lower() in ("1", "true", "yes", "y", "on")
        if enable_wre and enable_wre_monitor:
            try:
                from modules.infrastructure.wre_core.wre_monitor import get_monitor
                self.wre_monitor = get_monitor()
                logger.info("[0102] WRE Monitor attached - Continuous improvement active")
            except Exception as e:
                logger.debug(f"WRE Monitor not available: {e}")
                self.wre_monitor = None
        else:
            self.wre_monitor = None
            if not enable_wre:
                logger.info("[0102] WRE Monitor disabled (FOUNDUPS_ENABLE_WRE=0)")
            else:
                logger.info("[0102] WRE Monitor disabled (FOUNDUPS_ENABLE_WRE_MONITOR=0)")

        # BREADCRUMB TELEMETRY: Centralized breadcrumb hub for all DAEs
        # Persistent storage enables: WRE learning, AI Overseer pattern detection, 0102 troubleshooting
        try:
            self.breadcrumb_telemetry = get_breadcrumb_telemetry()
            logger.info("[BREADCRUMB-HUB] Telemetry initialized - all DAEs can send breadcrumbs")
        except Exception as e:
            logger.warning(f"[BREADCRUMB-HUB] Failed to initialize telemetry: {e}")
            self.breadcrumb_telemetry = None
        self._force_credential_logged = False
        self._force_credential_mismatch_logged = False

        logger.info(f"LiveChatCore initialized for video: {video_id}")

    def _refresh_persona_context(self) -> None:
        """Resolve persona and auth routing from the latest stream/channel metadata."""
        self.persona_key = resolve_persona_key(
            channel_name=self.channel_name,
            channel_id=self.channel_id,
            bot_channel_id=self.bot_channel_id,
            stream_title=self.stream_title,
        )
        self.persona_config = get_persona_config(
            persona_key=self.persona_key,
            channel_name=self.channel_name,
            channel_id=self.channel_id,
            bot_channel_id=self.bot_channel_id,
            stream_title=self.stream_title,
        )
        self.pinned_credential_set = resolve_channel_credential_set(
            channel_name=self.channel_name,
            channel_id=self.channel_id,
            bot_channel_id=self.bot_channel_id,
        )

        if hasattr(self, "session_manager"):
            self.session_manager.persona_key = self.persona_key
            self.session_manager.channel_name = self.channel_name
            self.session_manager.channel_id = self.channel_id
            self.session_manager.bot_channel_id = self.bot_channel_id

        if hasattr(self, "message_processor"):
            self.message_processor.update_persona_context(
                persona_key=self.persona_key,
                channel_name=self.channel_name,
                channel_id=self.channel_id,
                bot_channel_id=self.bot_channel_id,
                stream_title=self.stream_title,
            )
    
    async def initialize(self) -> bool:
        """
        Initialize the chat session.

        Returns:
            True if initialization successful
        """
        # Initialize session - in NO-QUOTA mode this might return False but we continue
        session_initialized = await self.session_manager.initialize_session()
        if not session_initialized and self.youtube:
            # Only fail if we have API service but still can't initialize
            logger.error("Failed to initialize session despite having API service")
            return False
        elif not session_initialized:
            # NO-QUOTA mode - continue for social media posting
            logger.info("NO-QUOTA mode: Continuing for social media announcements only")
        
        # Get chat ID and channel info from session manager
        self.live_chat_id = self.session_manager.live_chat_id
        self.channel_name = getattr(self.session_manager, 'channel_title', self.channel_name)
        self.channel_id = getattr(self.session_manager, 'channel_id', self.channel_id)
        self.stream_title = getattr(self.session_manager, 'stream_title', self.stream_title)

        # Session initialization is the first point where we know the real stream metadata.
        self._refresh_persona_context()

        # Update components with new info
        self.chat_sender.live_chat_id = self.live_chat_id
        self.chat_poller.live_chat_id = self.live_chat_id
        self.chat_poller.channel_name = self.channel_name
        self.chat_poller.channel_id = self.channel_id

        # Start memory manager session for automatic logging
        stream_title = getattr(self.session_manager, 'stream_title', None)
        self.memory_manager.start_session(self.video_id, stream_title)
        logger.info(f"📹 Started automatic session logging for video {self.video_id}")

        # Update message processor with actual YouTube stream start time (for accurate duration calculations)
        actual_start_time = getattr(self.session_manager, 'actual_start_time', None)
        if actual_start_time:
            self.message_processor.set_actual_start_time(actual_start_time)

        # Send greeting
        await self.session_manager.send_greeting(self.send_chat_message)

        # NOTE: Social media posting moved to stream_resolver for better architecture
        # Posting happens when stream is DETECTED, not when chat is initialized

        logger.info("LiveChatCore initialized successfully")
        # Record successful initialization
        if record_success:
            record_success('livechat_initialization', {'video_id': self.video_id}, tokens_used=50)
        return True
    
    async def send_chat_message(self, message_text: str, skip_delay: bool = False, response_type: str = 'general') -> bool:
        """
        Send a message to the live chat with duplicate detection and intelligent throttling.
        
        Args:
            message_text: Message to send
            skip_delay: Whether to skip delay (overridden by intelligent throttle)
            response_type: Type of response for priority handling
            
        Returns:
            True if message sent successfully
        """
        if not self.live_chat_id:
            logger.error("Cannot send message - no live chat ID")
            self.health_analyzer.analyze_message("ERROR: Cannot send message - no live chat ID")
            return False

        if os.getenv("YT_BLOCK_MESSAGES_ON_ACCOUNT_MISMATCH", "true").lower() in ("1", "true", "yes"):
            if self.bot_channel_id and self.channel_id and self.bot_channel_id != self.channel_id:
                logger.warning(
                    "[AUTH] Bot channel mismatch - blocking message send "
                    f"(bot={self.bot_channel_id}, channel={self.channel_id})"
                )
                return False
        
        # AUTOMATIC: Intelligent throttling before sending
        if self.intelligent_throttle and not skip_delay:
            # Track API call
            self.intelligent_throttle.track_api_call(quota_cost=5)  # Chat messages cost more quota
            
            # WRE Monitor: Track API call
            if self.wre_monitor:
                self.wre_monitor.track_api_call('liveChatMessages.insert', 5, True)
            
            # Check if we should send based on intelligent throttling
            if not self.intelligent_throttle.should_respond(response_type):
                delay = self.intelligent_throttle.calculate_adaptive_delay(response_type)
                if response_type in {"whack", "consciousness"}:
                    logger.info(f"[AUTO-THROTTLE] Delaying {response_type} by {delay:.1f}s to conserve quota")
                    await asyncio.sleep(delay)
                    if not self.intelligent_throttle.should_respond(response_type):
                        logger.info(f"[AUTO-THROTTLE] Suppressing {response_type} after delay to protect quota")
                        return False
                else:
                    logger.info(f"[AUTO-THROTTLE] Suppressing {response_type} to conserve quota (delay {delay:.1f}s)")
                    return False
        
        # Check for duplicate messages
        issues = self.health_analyzer.analyze_message(f"SENDING: {message_text}")
        if issues:
            for issue in issues:
                if issue.issue_type == 'duplicate' and issue.severity in ['high', 'critical']:
                    logger.warning(f"⚠️ Duplicate message detected, skipping: {message_text[:50]}...")
                    # Integrate with self-improvement
                    if hasattr(self.message_processor, 'self_improvement'):
                        self.message_processor.self_improvement.observe_system_issue(
                            issue.issue_type, issue.severity, issue.context
                        )
                    return False
        
        # Track message for duplicate detection
        self.recent_messages_sent.append({
            'message': message_text,
            'timestamp': time.time()
        })
        
        # Send message FIRST (before recording success)
        start_time = time.time()
        success = await self.chat_sender.send_message(message_text, skip_delay=skip_delay, response_type=response_type)
        duration_ms = (time.time() - start_time) * 1000

        # Track operation performance
        self.health_analyzer.track_operation('send_message', duration_ms)

        # AUTOMATIC: Record response for intelligent learning (AFTER we have success value)
        if self.intelligent_throttle:
            self.intelligent_throttle.record_response(response_type, success=success)

            # WRE Monitor: Track successful response
            if self.wre_monitor and success:
                self.wre_monitor.messages_processed += 1

        # Limit recent messages cache
        if len(self.recent_messages_sent) > 100:
            self.recent_messages_sent = self.recent_messages_sent[-100:]

        return success

    def store_breadcrumb(
        self,
        source_dae: str,
        event_type: str,
        message: str,
        phase: Optional[str] = None,
        metadata: Optional[Dict] = None,
        session_id: Optional[str] = None
    ):
        """
        Store breadcrumb from any DAE (comment_engagement, party_reactor, etc.).

        This is the central breadcrumb hub - all DAEs send breadcrumbs here for:
        - Persistent storage (survives DAE restarts)
        - WRE learning (breadcrumbs = training data)
        - AI Overseer pattern detection
        - 0102 troubleshooting

        Args:
            source_dae: DAE name (e.g., 'comment_engagement', 'party_reactor')
            event_type: Event classification (e.g., 'no_comments', 'navigation', 'wsp_violation')
            message: Human-readable message
            phase: Optional phase identifier (e.g., 'PHASE-1', 'DAE-NAV')
            metadata: Optional JSON-serializable context
            session_id: Optional session identifier for grouping

        Example:
            >>> # From comment_engagement_dae.py:
            >>> self.livechat_sender.store_breadcrumb(
            ...     source_dae='comment_engagement',
            ...     phase='PHASE-2',
            ...     event_type='no_comments_detected',
            ...     message='Inbox cleared via Occam detection',
            ...     metadata={'comment_count': 0, 'detection_method': 'DOM'}
            ... )
        """
        if self.breadcrumb_telemetry:
            try:
                self.breadcrumb_telemetry.store_breadcrumb(
                    source_dae=source_dae,
                    event_type=event_type,
                    message=message,
                    phase=phase,
                    metadata=metadata,
                    session_id=session_id
                )
            except Exception as e:
                logger.debug(f"[BREADCRUMB-HUB] Failed to store breadcrumb: {e}")

    async def poll_messages(self) -> tuple:
        """
        Poll for new chat messages.
        
        Returns:
            Tuple of (messages list, poll interval in ms)
        """
        try:
            messages = await self.chat_poller.poll_messages(
                viewer_count=self.session_manager.viewer_count
            )
            
            # ChatPoller returns messages directly
            if messages:
                poll_interval = self.chat_poller.poll_interval_ms
                return messages, poll_interval
            
            return [], 5000
            
        except Exception as e:
            logger.error(f"Error polling messages: {e}")
            return [], 5000
    
    async def process_message(self, message: Dict[str, Any]) -> None:
        """
        Process a single chat message.
        
        Args:
            message: Message data from YouTube API or ban_event
        """
        try:
            # Check if this is a ban/timeout event from chat_poller
            if message.get("type") == "ban_event":
                await self.process_ban_event(message)
                return
            elif message.get("type") == "timeout_event":
                # Timeout events are also ban events for processing
                await self.process_ban_event(message)
                return
                
            # Extract message details for regular messages
            message_id = message.get("id", "")
            
            # Skip if already processed
            if message_id in self.processed_message_ids:
                return
            
            self.processed_message_ids.add(message_id)
            
            # Get message content
            snippet = message.get("snippet", {})
            author_details = message.get("authorDetails", {})
            
            display_message = snippet.get("displayMessage", "")
            author_name = author_details.get("displayName", "Unknown")
            author_id = author_details.get("channelId", "")
            is_moderator = author_details.get("isChatModerator", False)
            is_owner = author_details.get("isChatOwner", False)

            # Capture received text before filters, commands or model failures
            # can return early. Response eligibility must not decide history.
            if message_id not in getattr(self, '_batch_captured_ids', set()):
                self._log_to_user_file(message)
            if message.get("_capture_only") is True:
                return
            
            # Log the message
            logger.debug(f"[{author_name}]: {display_message}")

            # Schema commands for antifaFM (mods/owner only)
            if (is_moderator or is_owner) and display_message:
                schema_cmd = display_message.strip().lower()
                schema_map = {
                    '!karaoke': 'KARAOKE', '/karaoke': 'KARAOKE',
                    '!lyrics': 'KARAOKE', '/lyrics': 'KARAOKE',
                    '!video': 'VIDEO_GRID', '/video': 'VIDEO_GRID',
                    '!grid': 'VIDEO_GRID', '/grid': 'VIDEO_GRID',
                    '!news': 'NEWS', '/news': 'NEWS',
                    '!full': 'VIDEO_FULL', '/full': 'VIDEO_FULL',
                }
                if schema_cmd in schema_map:
                    try:
                        from pathlib import Path
                        schema_file = Path(__file__).parent.parent.parent.parent / "platform_integration" / "antifafm_broadcaster" / "data" / "current_schema.txt"
                        schema_file.write_text(schema_map[schema_cmd])
                        logger.info(f"[SCHEMA] {author_name} switched to {schema_map[schema_cmd]}")
                    except Exception as e:
                        logger.warning(f"[SCHEMA] Failed to switch: {e}")

            # Track message timestamp for activity monitoring
            self.message_timestamps.append(time.time())
            # Clean old timestamps (keep last hour)
            cutoff = time.time() - 3600
            self.message_timestamps = [ts for ts in self.message_timestamps if ts > cutoff]
            
            # Update stats
            self.mod_stats.record_message()
            
            # WRE Monitor: Track message processing
            if self.wre_monitor:
                self.wre_monitor.messages_processed += 1
            
            # Process message through orchestrator router or legacy processor
            if self.router_mode and self.message_router:
                try:
                    # Use orchestrator's centralized message router
                    router_response = self.message_router.route_message(message)
                    if router_response:
                        # Convert router response to legacy format for compatibility
                        processed = {
                            "response": router_response.get("response"),
                            "response_type": router_response.get("response_type", "general"),
                            "has_consciousness": False,  # Router handles this internally
                            "has_whack_command": True if router_response.get("response") else False
                        }
                        logger.debug(f"[REFRESH] Router processed message from {author_name}")
                    else:
                        # Router returned no response, use empty processed
                        processed = {}
                except Exception as e:
                    # Router failed, fallback to legacy processing
                    logger.warning(f"[REFRESH] Router failed for {author_name}, falling back: {e}")
                    processed = self.message_processor.process_message(message)
            else:
                # Legacy processing mode
                processed = self.message_processor.process_message(message)
            
            # Check if message processor returned None (bot's own message filtered out)
            if processed is None:
                logger.debug(f"[MESSAGE-FILTER] ⏭️ Message from {author_name} was filtered out (likely bot's own message)")
                return

            # Log ALL messages and their processing result
            logger.info(f"📨 [{author_name}] ({author_id}): {display_message[:100]}")
            if processed.get("has_consciousness"):
                logger.info(f"✨ CONSCIOUSNESS DETECTED from {author_name}!")
            if processed.get("has_whack_command"):
                logger.info(f"[GAME] WHACK COMMAND DETECTED from {author_name}!")
                logger.info(f"[SEARCH] DEBUG: Whack command message text: '{display_message}'")

            # Debug log for slash commands
            if display_message and display_message.startswith('/'):
                logger.info(f"[SEARCH] SLASH COMMAND DETECTED: '{display_message}' from {author_name}")
                
                # Check for duplicate command within 5 seconds
                cache_key = f"{author_id}:{display_message}"
                current_time = time.time()
                
                if cache_key in self.recent_command_cache:
                    last_time = self.recent_command_cache[cache_key]
                    if current_time - last_time < 5:  # 5 second window
                        logger.info(f"⏭️ Skipping duplicate command from {author_name}")
                        return
                
                self.recent_command_cache[cache_key] = current_time
                
                # Clean old cache entries
                self.recent_command_cache = {
                    k: v for k, v in self.recent_command_cache.items() 
                    if current_time - v < 10
                }
            
            # Check if it's a timeout/ban announcement - HIGH PRIORITY, NO DELAYS
            if processed.get("type") in ["timeout_announcement", "ban_announcement"]:
                # Send announcements immediately with skip_delay=True
                if processed.get("announcement"):
                    # Use centralized send_chat_message for ALL chat
                    success = await self.send_chat_message(
                        processed["announcement"],
                        skip_delay=True,  # Priority message
                        response_type="timeout_announcement"  # Mark as priority
                    )
                    logger.info(f"[LIGHTNING][GAME] Sent timeout announcement: {processed['announcement'][:50]}...")
                if processed.get("level_up"):
                    await asyncio.sleep(0.5)  # Minimal delay between messages
                    # Use centralized send_chat_message for ALL chat
                    success = await self.send_chat_message(
                        processed["level_up"],
                        skip_delay=True,  # Priority message
                        response_type="timeout_announcement"  # Mark as priority
                    )
                    logger.info(f"[LIGHTNING]🏆 Sent level up: {processed['level_up']}")
                return  # Skip normal processing for events
            
            # Skip if marked to skip
            if processed.get("skip"):
                return
            
            # Generate response if needed
            sender = getattr(self, 'chat_sender', None)
            conversation_destination = (getattr(sender, 'live_chat_id', None), getattr(sender, 'bot_channel_id', None))
            response = await self.message_processor.generate_response(processed)
            if response and processed.get('response_type') == 'conversation':
                if not conversation_destination[0] or not hasattr(response, 'reviewed_text'):
                    return
                response.destination_snapshot = conversation_destination
            
            if response:
                # Handle list responses (e.g., /help sends multiple messages)
                responses = response if isinstance(response, list) else [response]

                for i, single_response in enumerate(responses):
                    if i > 0:
                        await asyncio.sleep(1.5)  # Small delay between multi-messages

                    logger.info(f"📤 Generated response for {author_name}: {single_response[:100]}")
                    # Check if this is a consciousness response or slash command
                    response_type = processed.get("response_type", "general")

                    # SLASH COMMANDS go through intelligent throttling
                    if processed.get("has_whack_command") or display_message.startswith('/'):
                        logger.info(f"[GAME] Sending slash command response (throttled)")
                        # Commands use intelligent throttle with 'whack' priority
                        success = await self.send_chat_message(single_response, response_type="whack")
                    elif response_type == "consciousness":
                        logger.info(f"[AI] Sending consciousness response (throttled)")
                        # Consciousness responses use intelligent throttle
                        success = await self.send_chat_message(single_response, response_type="consciousness")
                    else:
                        # All other responses go through throttle with proper type
                        actual_type = response_type if response_type != "general" else "maga" if "maga" in single_response.lower() else "general"
                        success = await self.send_chat_message(single_response, response_type=actual_type)
                    if success:
                        logger.info(f"💬 Sent response to {author_name}")
            else:
                # Debug: log why no response
                if display_message.startswith('/'):
                    logger.warning(f"⚠️ NO RESPONSE for command: '{display_message}' from {author_name}")
                    logger.warning(f"⚠️ Processed flags: has_whack={processed.get('has_whack_command')}, has_trigger={processed.get('has_trigger')}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def process_ban_event(self, ban_event: Dict[str, Any]) -> None:
        """
        Process a ban/timeout event and send announcement.
        
        Args:
            ban_event: Ban event data from chat_poller
        """
        try:
            logger.info(f"[TARGET] Processing ban/timeout event: {ban_event.get('type')} - {ban_event.get('target_name')}")
            
            # Process through message processor to get announcement
            processed = self.message_processor.process_message(ban_event)
            
            # Check if this was queued for batching
            if processed.get("queued"):
                logger.info(f"[BOX] Event queued for batching (pending: {self.message_processor.event_handler.get_pending_count()})")
                return
            
            # Check if we should skip (already part of a batch)
            if processed.get("skip") and not processed.get("announcement"):
                logger.info("⏭️ Skipping - part of batch")
                return
            
            logger.info(f"[NOTE] Processed result: announcement={bool(processed.get('announcement'))}, is_batched={processed.get('is_batched', False)}")
            
            # Send announcements
            if processed.get("announcement"):
                if processed.get("is_batched"):
                    logger.info(f"[TARGET] Sending BATCHED announcement: {processed['announcement'][:50]}...")
                else:
                    logger.info(f"[GAME] Sending timeout announcement: {processed['announcement'][:50]}...")
                await self.send_chat_message(processed["announcement"], response_type="timeout_announcement")
            else:
                logger.warning("⚠️ No announcement generated for timeout event")
            
            if processed.get("level_up"):
                await asyncio.sleep(1)  # Small delay between messages
                logger.info(f"🏆 Sending level up: {processed['level_up']}")
                await self.send_chat_message(processed["level_up"])
                
        except Exception as e:
            logger.error(f"Error processing ban event: {e}")
    
    def _log_to_user_file(self, message: Dict[str, Any]) -> None:
        """
        Log message using hybrid memory manager.
        
        Args:
            message: Message data
        """
        try:
            author_details = message.get("authorDetails", {})
            snippet = message.get("snippet", {})

            author_name = author_details.get("displayName", "Unknown")
            author_id = author_details.get("channelId", "")
            display_message = snippet.get("displayMessage", "")
            is_moderator = author_details.get("isChatModerator", False)
            is_owner = author_details.get("isChatOwner", False)

            # Determine role
            role = 'OWNER' if is_owner else 'MOD' if is_moderator else 'USER'

            # Use hybrid memory manager with YouTube metadata for session logging
            self.memory_manager.store_message(
                author_name=author_name,
                message_text=display_message,
                role=role,
                author_id=author_id,
                youtube_name=author_name  # YouTube display name
            )
            
        except Exception as e:
            logger.error(f"Error logging message: {e}")
    
    async def process_message_batch(self, messages: List[Dict[str, Any]]) -> None:
        """Capture the received batch first, then preserve conversation order.

        Authorized platform commands retain priority; ordinary conversation has
        no badge queue. Polling remains serialized with bounded generation.
        """
        self._batch_captured_ids = set()
        try:
            for message in messages:
                identity = message.get('id', '')
                if (message.get('type') not in ('ban_event', 'timeout_event')
                        and identity not in self.processed_message_ids
                        and identity not in self._batch_captured_ids):
                    self._log_to_user_file(message)
                    self._batch_captured_ids.add(identity)
            def command_priority(message):
                author = message.get('authorDetails') or {}
                text = message.get('snippet', {}).get('displayMessage', '').lstrip()
                processor = getattr(self, 'message_processor', None)
                recognized = any(callable(check := getattr(processor, name, None)) and check(text)
                    for name in ('_check_whack_command', '_check_shorts_command', '_check_m2j_command', '_check_pqn_command'))
                return (message.get('_capture_only') is not True and text.startswith(('/', '!'))
                        and recognized and (author.get('isChatOwner') or author.get('isChatModerator')))
            ordered = [msg for msg in messages if command_priority(msg)]
            ordered += [msg for msg in messages if not command_priority(msg)]
            for message in ordered:
                await self.process_message(message)
        finally:
            self._batch_captured_ids.clear()
    
    async def run_polling_loop(self) -> None:
        """Run the polling loop with health monitoring and quiet conversation selection."""
        poll_interval_ms = 5000
        
        # Check quota status at start
        if self.quota_poller:
            status = self.quota_poller.get_quota_status()
            logger.warning(f"[DATA] QUOTA STATUS: {status['status']} - {status['units_used']}/{10000} units used ({status['percentage_used']:.1%})")
            logger.info(f"[IDEA] Recommendation: {status['recommendation']}")
        last_health_check = time.time()
        last_stream_check = time.time()  # Track last stream validation
        last_activity = time.time()  # Track last meaningful chat activity
        health_check_interval = 60  # Check health every minute
        stream_check_interval = 120  # Check if stream is still live every 2 minutes (more responsive)
        inactivity_timeout = 180  # Consider stream inactive after 3 minutes of no messages
        consecutive_poll_errors = 0  # Track consecutive polling errors
        consecutive_empty_polls = 0  # Track polls with no messages
        
        while self.is_running:
            try:
                # Periodic health check
                if time.time() - last_health_check > health_check_interval:
                    health_report = self.health_analyzer.get_health_report()
                    if health_report['health_score'] < 80:
                        logger.warning(f"⚠️ System health degraded: {health_report['health_score']:.1f}/100")
                        for recommendation in health_report['recommendations']:
                            logger.info(f"[IDEA] Health recommendation: {recommendation}")
                    last_health_check = time.time()
                
                # Observation cadence is not a reason to speak. Conversation
                # replies are selected from received messages by MessageProcessor.

                # Periodic stream health check - detect if stream ended
                if time.time() - last_stream_check > stream_check_interval:
                    logger.info("[SEARCH] Checking if stream is still live...")
                    try:
                        if self.youtube:
                            # API mode - check with API
                            response = self.youtube.videos().list(
                                part="liveStreamingDetails,snippet",
                                id=self.video_id
                            ).execute()

                            items = response.get('items', [])
                            if not items:
                                logger.warning("⚠️ Stream not found - may have ended")
                                consecutive_poll_errors = 5  # Trigger exit
                            else:
                                live_details = items[0].get('liveStreamingDetails', {})
                                actual_end_time = live_details.get('actualEndTime')
                                if actual_end_time:
                                    logger.warning(f"⚠️ Stream has ended at {actual_end_time}")
                                    logger.info("🔚 Exiting polling loop - stream ended")
                                    self.is_running = False
                                    break
                                else:
                                    logger.info("[OK] Stream is still live")
                                    consecutive_poll_errors = 0  # Reset error counter
                        else:
                            # NO-QUOTA mode - use web scraping to check
                            logger.info("🌐 NO-QUOTA mode: Checking stream via web scraping...")
                            from modules.platform_integration.stream_resolver.src.no_quota_stream_checker import NoQuotaStreamChecker

                            checker = NoQuotaStreamChecker()
                            is_live_result = checker.check_video_is_live(self.video_id)
                            is_live = is_live_result.get('is_live', False)

                            if not is_live:
                                logger.warning("⚠️ Stream appears to have ended (NO-QUOTA check)")
                                logger.info("🔚 Exiting polling loop - stream ended")
                                self.is_running = False
                                break
                            else:
                                logger.info("[OK] Stream is still live (NO-QUOTA check)")
                                consecutive_poll_errors = 0  # Reset error counter
                    except Exception as e:
                        logger.warning(f"⚠️ Error checking stream status: {e}")
                    
                    last_stream_check = time.time()
                
                # AUTOMATIC: Check quota before polling
                if self.intelligent_throttle:
                    # Get intelligent delay based on current activity
                    messages_per_minute = len([ts for ts in self.message_timestamps if time.time() - ts < 60])
                    intelligent_delay = self.intelligent_throttle.calculate_adaptive_delay('poll')

                    # Use intelligent delay if it's longer than current interval (handle None case)
                    if intelligent_delay is not None and intelligent_delay * 1000 > poll_interval_ms:
                        poll_interval_ms = int(intelligent_delay * 1000)
                        logger.info(f"[AUTO-THROTTLE] Adjusted poll interval to {intelligent_delay:.1f}s based on activity")
                    
                    # Check quota state
                    status = self.intelligent_throttle.get_status()
                    for set_id, quota_info in status.get('quota_states', {}).items():
                        if quota_info['percentage'] < 10:
                            logger.warning(f"[AUTO-QUOTA] Low quota on set {set_id}: {quota_info['percentage']:.1f}%")

                # Original quota poller as fallback
                elif self.quota_poller:
                    should_poll, wait_time = self.quota_poller.should_poll()
                    if not should_poll:
                        logger.critical("[ALERT] QUOTA EXHAUSTED - Stopping polling")
                        self.is_running = False
                        break

                    # Override poll interval with quota-aware interval
                    if wait_time:
                        poll_interval_ms = int(wait_time * 1000)
                        logger.info(f"⏱️ Quota-aware interval: {wait_time:.1f}s")

                # REVOLUTIONARY: Intelligent credential rotation check
                if self.quota_intelligence:
                    try:
                        # Get current credential set (default to 1 if not available)
                        current_set = getattr(
                            self.youtube,
                            'credential_set',
                            getattr(self.youtube, '_credential_set', 1)
                        )
                        logger.debug(f"[REFRESH] [ROTATION-CHECK] Checking rotation for Set {current_set}")

                        forced_set = _get_forced_credential_set()
                        pinned_set = self.pinned_credential_set
                        if forced_set:
                            if not self._force_credential_logged:
                                logger.info(f"[REFRESH] Credential rotation disabled (YT_FORCE_CREDENTIAL_SET={forced_set})")
                                self._force_credential_logged = True
                            if current_set != forced_set and not self._force_credential_mismatch_logged:
                                logger.warning(
                                    f"[REFRESH] Active credential set {current_set} does not match forced {forced_set}"
                                )
                                self._force_credential_mismatch_logged = True
                            # Skip rotation when a forced set is configured
                            rotation_decision = {"should_rotate": False}
                        elif pinned_set:
                            if not self._force_credential_logged:
                                logger.info(f"[REFRESH] Credential rotation disabled (channel pinned to Set {pinned_set})")
                                self._force_credential_logged = True
                            if current_set != pinned_set and not self._force_credential_mismatch_logged:
                                logger.warning(
                                    f"[REFRESH] Active credential set {current_set} does not match pinned {pinned_set}"
                                )
                                self._force_credential_mismatch_logged = True
                            rotation_decision = {"should_rotate": False}
                        else:
                            # Check if rotation is needed
                            rotation_decision = self.quota_intelligence.should_rotate_credentials(current_set)
                            logger.debug(
                                "[REFRESH] [ROTATION-CHECK] Decision: should_rotate=%s, urgency=%s",
                                rotation_decision['should_rotate'],
                                rotation_decision.get('urgency', 'N/A')
                            )

                        if rotation_decision['should_rotate']:
                            urgency = rotation_decision['urgency']
                            target_set = rotation_decision['target_set']
                            reason = rotation_decision['reason']

                            # Log rotation decision with appropriate severity
                            if urgency == 'critical':
                                logger.critical(f"[REFRESH][ALERT] CREDENTIAL ROTATION TRIGGERED: {reason}")
                            elif urgency == 'high':
                                logger.warning(f"[REFRESH]⚠️ CREDENTIAL ROTATION TRIGGERED: {reason}")
                            else:
                                logger.info(f"[REFRESH] CREDENTIAL ROTATION TRIGGERED: {reason}")

                            logger.critical(f"[TARGET] Rotating from Set {current_set} to Set {target_set}")
                            logger.info(f"[DATA] Current available: {rotation_decision['current_available']} units")
                            logger.info(f"[DATA] Target available: {rotation_decision['target_available']} units")
                            logger.info(f"[IDEA] Recommendation: {rotation_decision['recommendation']}")

                            # Execute graceful credential rotation
                            logger.info(f"[REFRESH] EXECUTING ROTATION from Set {current_set} to Set {target_set}")

                            try:
                                # Import youtube_auth module for service reinitialization
                                from modules.platform_integration.youtube_auth.src.youtube_auth import get_authenticated_service
                                from modules.platform_integration.youtube_auth.src.monitored_youtube_service import (
                                    create_monitored_service
                                )

                                # Get new YouTube service with target credential set
                                logger.info(f"[REFRESH] Reinitializing YouTube service with Set {target_set} credentials...")
                                new_youtube_service = get_authenticated_service(token_index=target_set)

                                if new_youtube_service:
                                    try:
                                        new_youtube = create_monitored_service(
                                            new_youtube_service,
                                            credential_set=target_set
                                        )
                                    except Exception as wrap_error:
                                        logger.warning(
                                            f"[WARN] Failed to wrap YouTube service for monitoring: {wrap_error}"
                                        )
                                        new_youtube = new_youtube_service

                                    # Update service reference
                                    old_service = self.youtube
                                    self.youtube = new_youtube
                                    self.session_manager.youtube = new_youtube
                                    self.chat_poller.youtube = new_youtube
                                    self.chat_sender.update_youtube_service(new_youtube)
                                    self.message_processor.youtube_service = new_youtube
                                    if self.intelligent_throttle:
                                        self.intelligent_throttle.current_credential_set = target_set

                                    # Reinitialize quota poller with new service
                                    if QuotaAwarePoller:
                                        oauth_manager = new_youtube if hasattr(new_youtube, 'rotate_credentials') else None
                                        self.quota_poller = QuotaAwarePoller(target_set, oauth_manager)
                                        logger.info(f"[REFRESH] QuotaAwarePoller reinitialized with Set {target_set}")

                                    logger.critical(f"[OK] ROTATION SUCCESSFUL: Now using Set {target_set} credentials")
                                    logger.info(f"[DATA] Available quota on Set {target_set}: {rotation_decision['target_available']} units")

                                    # Continue polling with new credentials
                                    # No need to stop - next poll will use new service
                                else:
                                    logger.error(f"[FAIL] ROTATION FAILED: Could not get service for Set {target_set}")
                                    logger.warning(f"⚠️ Continuing with Set {current_set} credentials")

                            except Exception as rotation_error:
                                logger.error(f"[FAIL] ROTATION FAILED: {rotation_error}", exc_info=True)
                                logger.warning(f"⚠️ Continuing with Set {current_set} credentials")

                    except Exception as e:
                        logger.error(f"[REFRESH][FAIL] Rotation check failed: {e}", exc_info=True)

                # Poll for messages
                logger.info(f"[REFRESH] Polling for messages...")
                try:
                    messages, original_interval = await self.poll_messages()
                    
                    # Let quota poller know about activity
                    if self.quota_poller:
                        optimal_interval = self.quota_poller.calculate_optimal_interval(
                            messages_received=len(messages),
                            stream_active=self.is_running
                        )

                        # CRITICAL: Handle quota exhaustion (None return)
                        if optimal_interval is None:
                            logger.critical("[ALERT] QUOTA EXHAUSTED - calculate_optimal_interval returned None")
                            logger.critical("[STOP] EMERGENCY SHUTDOWN - Stopping all polling to preserve quota")
                            self.is_running = False
                            break

                        poll_interval_ms = int(optimal_interval * 1000)
                    # Only reset error counter if we actually got a successful API response
                    # Empty messages list is OK (quiet chat), but API errors are not
                    consecutive_poll_errors = 0
                    
                    # Track activity for agentic stream switching
                    if messages:
                        last_activity = time.time()
                        consecutive_empty_polls = 0
                        logger.debug(f"📬 Got {len(messages)} messages - chat is active")
                    else:
                        consecutive_empty_polls += 1
                        time_since_activity = time.time() - last_activity
                        
                        # Agentic detection: Stream might be inactive/ended
                        if time_since_activity > inactivity_timeout:
                            logger.warning(f"⚠️ No chat activity for {time_since_activity:.0f}s - checking stream status")

                            # Quick stream validation
                            try:
                                if self.youtube:
                                    # API mode - check with API
                                    response = self.youtube.videos().list(
                                        part="liveStreamingDetails,snippet",
                                        id=self.video_id
                                    ).execute()

                                    items = response.get('items', [])
                                    if not items:
                                        logger.warning("🔚 Stream disappeared - likely ended")
                                        self.is_running = False
                                        break

                                    live_details = items[0].get('liveStreamingDetails', {})
                                    actual_end_time = live_details.get('actualEndTime')
                                    if actual_end_time:
                                        logger.info(f"🔚 Stream confirmed ended at {actual_end_time}")
                                        self.is_running = False
                                        break
                                else:
                                    # NO-QUOTA mode - use web scraping
                                    logger.info("🌐 NO-QUOTA mode: Checking if stream ended...")
                                    from modules.platform_integration.stream_resolver.src.no_quota_stream_checker import NoQuotaStreamChecker

                                    checker = NoQuotaStreamChecker()
                                    is_live_result = checker.check_video_is_live(self.video_id)
                                    is_live = is_live_result.get('is_live', False)

                                    if not is_live:
                                        logger.warning("🔚 Stream ended (NO-QUOTA check)")
                                        self.is_running = False
                                        break

                                # Stream exists but no chat activity
                                if consecutive_empty_polls > 20:  # ~100 seconds of no activity
                                    logger.warning("[U+1F4A4] Stream appears inactive - may be dead or viewers left")
                                    # Signal to auto_moderator to check for new streams
                                    self.is_running = False
                                    break

                            except Exception as e:
                                logger.warning(f"⚠️ Could not verify stream: {e}")
                                if consecutive_empty_polls > 30:  # Give up after ~150 seconds
                                    logger.info("[REFRESH] Assuming stream ended due to prolonged inactivity")
                                    self.is_running = False
                                    break
                except googleapiclient.errors.HttpError as e:
                    error_details = str(e)
                    consecutive_poll_errors += 1
                    
                    # AUTOMATIC: Handle quota errors intelligently
                    if "quotaExceeded" in error_details or "403" in error_details:
                        logger.warning(f"[AUTO-QUOTA] Quota exceeded error detected")
                        if self.intelligent_throttle:
                            # Check if all credential sets are exhausted before switching
                            status = self.intelligent_throttle.get_status()
                            all_exhausted = all(
                                quota_info.get('exhausted', False) or quota_info.get('percentage', 0) >= 98
                                for quota_info in status.get('quota_states', {}).values()
                            )

                            if all_exhausted:
                                logger.critical("[ALERT] ALL CREDENTIAL SETS EXHAUSTED - EMERGENCY SHUTDOWN")
                                logger.critical("[STOP] Stopping all operations to prevent quota death spiral")
                                self.is_running = False
                                break

                            # Automatically switch credential sets
                            new_set = self.intelligent_throttle.handle_quota_error()
                            logger.info(f"[AUTO-QUOTA] Switching to credential set {new_set}")
                            # Increase delay to conserve quota
                            poll_interval_ms = 30000  # 30 seconds minimum
                        else:
                            logger.error("[AUTO-QUOTA] No intelligent throttle available, stopping")
                            self.is_running = False
                            break
                    # Check if it's a "live chat ended" error
                    elif "liveChatEnded" in error_details or "forbidden" in error_details.lower():
                        logger.warning(f"🔚 Live chat has ended: {e}")
                        self.is_running = False
                        break
                    elif "notFound" in error_details:
                        logger.warning(f"🔚 Live chat not found - stream may have ended: {e}")
                        self.is_running = False
                        break
                    else:
                        logger.error(f"[FAIL] Polling error #{consecutive_poll_errors}: {e}")
                        # Only exit after many consecutive API errors (not just quiet chat)
                        if consecutive_poll_errors >= 10:
                            logger.warning("🔚 Too many API errors - checking if stream ended")
                            # Do one final check before giving up
                            try:
                                response = self.youtube.videos().list(
                                    part="liveStreamingDetails",
                                    id=self.video_id
                                ).execute()
                                items = response.get('items', [])
                                if not items or items[0].get('liveStreamingDetails', {}).get('actualEndTime'):
                                    logger.warning("🔚 Confirmed: Stream has ended")
                                    self.is_running = False
                                    break
                            except:
                                pass
                    
                    messages = []
                    poll_interval_ms = 5000
                except Exception as e:
                    # Other non-API errors
                    logger.error(f"[FAIL] Unexpected error polling: {e}")
                    messages = []
                    poll_interval_ms = 5000
                
                # Process messages
                if messages:
                    logger.info(f"Processing {len(messages)} messages")
                    await self.process_message_batch(messages)
                    # Update last message timestamp for stream health monitoring
                    self._last_message_time = time.time()

                # Check for pending batched announcements
                if hasattr(self.message_processor, 'event_handler'):
                    pending_count = self.message_processor.event_handler.get_pending_count()
                    if pending_count > 0:
                        logger.info(f"[BOX] Checking {pending_count} pending announcements...")
                        # Force flush if we have old pending announcements
                        flushed = self.message_processor.event_handler.force_flush()
                        if flushed:
                            logger.info(f"[U+1F4A5] Flushing batched announcement: {flushed[:50]}...")
                            await self.send_chat_message(flushed, response_type="timeout_announcement")
                
                # Update viewer count periodically
                if time.time() % 60 < 1:  # Every minute
                    self.session_manager.update_viewer_count()

                # Check stream health (intelligent switching to better streams)
                if self._health_check_enabled:
                    current_time = time.time()
                    time_since_message = current_time - self._last_message_time
                    viewers = self.session_manager.viewer_count

                    # Stream is unhealthy if: no messages for X minutes AND low viewer count
                    if time_since_message > self._inactivity_threshold_seconds and viewers < self._min_viewers_threshold:
                        logger.warning(f"[STREAM-HEALTH] ⚠️ UNHEALTHY STREAM DETECTED")
                        logger.warning(f"[STREAM-HEALTH]   Last message: {int(time_since_message)}s ago (threshold: {self._inactivity_threshold_seconds}s)")
                        logger.warning(f"[STREAM-HEALTH]   Viewers: {viewers} (threshold: {self._min_viewers_threshold})")
                        logger.warning(f"[STREAM-HEALTH]   Video: {self.video_id}")
                        logger.info(f"[STREAM-HEALTH] 🔄 Triggering intelligent stream switch...")
                        self.is_running = False
                        break

                # Wait before next poll
                sleep_time = max(poll_interval_ms / 1000.0, 1.0)
                await asyncio.sleep(sleep_time)
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt - stopping")
                self.is_running = False
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(5)
    
    async def start_listening(self) -> None:
        """Start listening to chat messages."""
        if self.is_running:
            logger.warning("Already listening")
            return
        
        logger.info("Starting LiveChatCore...")
        
        # Initialize session
        if not await self.initialize():
            logger.error("Failed to initialize - cannot start")
            return
        
        # Start polling
        self.is_running = True
        
        try:
            await self.run_polling_loop()
        finally:
            self.stop_listening()
    
    def stop_listening(self) -> None:
        """Stop listening to chat messages."""
        if not self.is_running:
            return

        logger.info("Stopping LiveChatCore...")
        self.is_running = False

        # End memory manager session (saves all logs automatically)
        self.memory_manager.end_session()
        logger.info("[DATA] Session logs saved to conversation folder")

        # End session manager session
        self.session_manager.end_session()

        # Save stats
        logger.info("Final stats:")
        logger.info(self.mod_stats.get_moderation_stats())
    
    # Convenience methods for compatibility
    
    def get_moderation_stats(self) -> Dict[str, Any]:
        """Get moderation statistics."""
        return self.mod_stats.get_moderation_stats()
    
    def get_user_violations(self, user_id: str) -> Dict[str, Any]:
        """Get violations for a specific user."""
        return self.mod_stats.get_user_violations(user_id)
    
    def get_top_violators(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top violators."""
        return self.mod_stats.get_top_violators(limit)
    
    def clear_user_violations(self, user_id: str) -> bool:
        """Clear violations for a user."""
        return self.mod_stats.clear_user_violations(user_id)
    
    def add_banned_phrase(self, phrase: str) -> bool:
        """Add a banned phrase."""
        return self.mod_stats.add_banned_phrase(phrase)
    
    def remove_banned_phrase(self, phrase: str) -> bool:
        """Remove a banned phrase."""
        return self.mod_stats.remove_banned_phrase(phrase)
    
    def get_banned_phrases(self) -> List[str]:
        """Get list of banned phrases."""
        return self.mod_stats.get_banned_phrases()
    
    def configure_emoji_triggers(self, **kwargs) -> Dict[str, Any]:
        """Configure emoji trigger settings."""
        # Now handled by message_processor's consciousness handler
        return {"status": "configured", "settings": kwargs}
    
    async def _post_stream_to_linkedin_deprecated(self) -> None:
        """
        DEPRECATED: Moved to stream_resolver for better architecture.
        Social media posting should happen when stream is DETECTED,
        not when chat module is initialized.
        """
        # This method is kept for reference but not called
        logger.warning("[DEPRECATED] Social media posting moved to stream_resolver")
        return

    # Social media posting has been moved to stream_resolver module per WSP architecture
