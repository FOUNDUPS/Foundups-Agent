"""
Enhanced Stream Resolver Module for Windsurf Project

Integrates improvements from test coverage analysis:
- Enhanced error handling and validation
- Better retry logic with exponential backoff
- Improved fallback mechanisms
- More robust API client management
- Better logging and monitoring

Following WSP 3: Enterprise Domain Architecture
"""



import os
import logging
from typing import Optional, Tuple, Dict, Any, List
import googleapiclient.errors
from googleapiclient.errors import HttpError
from googleapiclient.discovery import Resource
from utils.oauth_manager import get_authenticated_service_with_fallback, get_authenticated_service
from utils.env_loader import get_env_variable
from modules.infrastructure.shared_utilities.youtube_channel_registry import get_channel_ids
import time
import random
from datetime import datetime, timedelta
import json
import asyncio

# Import intelligent quota testing
try:
    from modules.platform_integration.youtube_auth.src.quota_tester import QuotaTester, get_best_credential_set
except ImportError:
    QuotaTester = None
    get_best_credential_set = None

# Import database for pattern learning (WSP 78)
try:
    from .stream_db import StreamResolverDB
except ImportError:
    StreamResolverDB = None
    # Logger defined below, so use print for now
    print("WARNING: Stream database not available - using legacy JSON storage")

# Import existing superior implementations (HoloIndex analysis confirmed these are better)
from modules.platform_integration.social_media_orchestrator.src.core.platform_posting_service import PlatformPostingService
from modules.platform_integration.social_media_orchestrator.src.channel_routing import SocialMediaRouter
from modules.platform_integration.youtube_api_operations.src.youtube_api_operations import YouTubeAPIOperations
# Lazy import to avoid circular dependency: get_qwen_youtube imported when needed
from modules.infrastructure.database.src.agent_db import AgentDB

# Import existing config (simpler but functional)
from .config import config as stream_config

# Import infrastructure utilities (superior implementations)
try:
    from modules.infrastructure.shared_utilities.session_utils import SessionUtils
    session_utils_available = True
except ImportError:
    SessionUtils = None
    session_utils_available = False
    logger.warning("SessionUtils not available, session caching disabled")

try:
    from modules.infrastructure.shared_utilities.validation_utils import ValidationUtils
    validation_utils_available = True
except ImportError:
    ValidationUtils = None
    validation_utils_available = False
    logger.warning("ValidationUtils not available, using fallback validation")

try:
    from modules.infrastructure.shared_utilities.delay_utils import DelayUtils
    delay_utils_available = True
except ImportError:
    DelayUtils = None
    delay_utils_available = False
    logger.warning("DelayUtils not available, using fallback delays")

# Get a logger instance specific to this module
logger = logging.getLogger(__name__)

# WSP 3 Phase 4: Global constants (previously removed but needed for backward compatibility)
CHANNEL_ID = os.getenv('CHANNEL_ID', 'UC-LSSlOZwpGIRIYihaz8zCw')  # UnDaoDu default

# Define custom exceptions for better error handling
class QuotaExceededError(Exception):
    """Custom exception for when API quota is exceeded after retries."""
    pass

class StreamResolverError(Exception):
    """Base exception for stream resolver errors."""
    pass

class APIClientError(Exception):
    """Exception for API client creation/validation errors."""
    pass

# Circuit breaker and configuration now imported from separate modules

# calculate_enhanced_delay moved to infrastructure/shared_utilities/delay_utils.py
# mask_sensitive_id and validate_api_client moved to infrastructure/shared_utilities/validation_utils.py

# Fallback functions for backward compatibility
def mask_sensitive_id(id_str: str, id_type: str = "default") -> str:
    """Fallback function that uses infrastructure utilities when available."""
    try:
        from modules.infrastructure.shared_utilities.validation_utils import ValidationUtils
        return ValidationUtils.mask_sensitive_id(id_str, id_type)
    except ImportError:
        # Basic fallback implementation
        if not id_str or not isinstance(id_str, str):
            return "None"
        return f"{id_str[:3]}...{id_str[-2:]}" if len(id_str) > 8 else "***ID***"

def validate_api_client(youtube_client) -> bool:
    """Fallback function that uses infrastructure utilities when available."""
    try:
        from modules.infrastructure.shared_utilities.validation_utils import ValidationUtils
        return ValidationUtils.validate_api_client(youtube_client)
    except ImportError:
        # Basic fallback implementation
        return youtube_client is not None

# ============================================================================
# YouTube API Operations Extraction (WSP 3 Phase 4)
# ============================================================================
# The following 415 lines of standalone YouTube API functions have been
# extracted to modules/platform_integration/youtube_api_operations/
#
# CRITICAL BUGS FIXED:
# - Line 185: self.circuit_breaker.call() in module-level function (no self!)
# - Line 306: self.circuit_breaker.call() in module-level function (no self!)
# - Line 298: self.config.CHANNEL_ID in module-level function (no self!)
#
# These functions are now properly implemented as instance methods in the
# YouTubeAPIOperations class with correct self references and dependency injection.
#
# Usage: self.youtube_api_ops.get_active_livestream_video_id_enhanced(youtube, channel_id)
# ============================================================================

class StreamResolver:
    def __init__(self,
                 youtube_service,
                 circuit_breaker=None,  # from circuit_breaker module
                 config=None,           # from stream_config module
                 database=None,         # from stream_db module
                 social_poster=None,    # from social_media_orchestrator
                 qwen_integration=None, # from qwen_youtube_integration
                 cache_manager=None,    # from session_cache module
                 no_quota_checker=None, # from no_quota_stream_checker module
                 use_intelligent_sorting=True):
        """
        StreamResolver with full dependency injection.

        Args:
            youtube_service: YouTube API service instance
            circuit_breaker: Circuit breaker instance (optional, uses global if None)
            config: Configuration instance (optional, uses global if None)
            database: Database instance (optional, creates if None)
            social_poster: Social media posting service (optional)
            qwen_integration: QWEN intelligence instance (optional)
            cache_manager: Cache manager instance (optional, uses global if None)
            no_quota_checker: NO-QUOTA checker instance (optional, creates if None and needed)
            use_intelligent_sorting: Whether to use intelligent sorting
        """
        self.youtube = youtube_service
        self.logger = logging.getLogger(__name__)

        # Store circuit_breaker reference (used by youtube_api_ops)
        self.circuit_breaker = circuit_breaker  # May be None, that's okay

        # Store config reference (used by resolve_stream for channel fallback)
        self.config = config  # May be None, that's okay

        # Use superior existing implementations (HoloIndex confirmed)
        self.use_intelligent_sorting = use_intelligent_sorting

        # Initialize existing superior services
        self._quota_tester = QuotaTester() if QuotaTester and use_intelligent_sorting else None
        self._tested_credentials = set()
        self._cache = {}
        self._api_service_cache = {}
        self._last_stream_check = {}

        # QWEN Intelligence - Use existing superior implementation (lazy import to avoid circular dependency)
        if qwen_integration is not None:
            self.qwen = qwen_integration
        else:
            try:
                from modules.communication.livechat.src.qwen_youtube_integration import get_qwen_youtube
                self.qwen = get_qwen_youtube()
                self.logger.info("[QWEN] [QWEN-RESOLVER] QWEN intelligence connected to StreamResolver")
            except Exception as e:
                self.logger.debug(f"QWEN not available for StreamResolver: {e}")
                self.qwen = None

        # Database - Use existing superior AgentDB from infrastructure
        if database is not None:
            self.db = database
        else:
            try:
                self.db = AgentDB()  # Use superior infrastructure database
            except Exception as e:
                self.logger.warning(f"AgentDB not available, falling back to StreamResolverDB: {e}")
        self.db = StreamResolverDB() if StreamResolverDB else None

        # Social media poster - Use existing superior implementation
        if social_poster is not None:
            self.social_poster = social_poster
        else:
            try:
                self.social_poster = PlatformPostingService()
                self.logger.info("[SOCIAL] Social media posting service connected")
            except Exception as e:
                self.logger.warning(f"PlatformPostingService not available: {e}")
                self.social_poster = None

        # YouTube API Operations - Use extracted superior implementation
        self.youtube_api_ops = YouTubeAPIOperations(
            circuit_breaker=circuit_breaker,
            logger=self.logger
        )

        # Infrastructure utilities - Use superior implementations
        if cache_manager is not None:
            self.session_utils = cache_manager
        elif session_utils_available:
            self.session_utils = SessionUtils()
            self.logger.info("[SESSION] Session utilities connected from infrastructure")
        else:
            self.session_utils = None
            self.logger.warning("[SESSION] No session utilities available")

        # Validation utilities
        if validation_utils_available:
            self.validation_utils = ValidationUtils()
            self.logger.info("[VALIDATION] Validation utilities connected from infrastructure")
        else:
            self.validation_utils = None
            self.logger.warning("[VALIDATION] No validation utilities available")

        # Delay utilities
        if delay_utils_available:
            self.delay_utils = DelayUtils()
            self.logger.info("[DELAY] Delay utilities connected from infrastructure")
        else:
            self.delay_utils = None
            self.logger.warning("[DELAY] No delay utilities available")

        # NO-QUOTA checker - Use existing implementation
        if no_quota_checker is not None:
            self.no_quota_checker = no_quota_checker
        elif not self.youtube:
            try:
                from .no_quota_stream_checker import NoQuotaStreamChecker
                self.no_quota_checker = NoQuotaStreamChecker()
                self.logger.info("[NO-QUOTA] NO-QUOTA mode initialized - using web scraping")
            except ImportError:
                self.logger.warning("NoQuotaStreamChecker not available")
                self.no_quota_checker = None
        else:
            self.no_quota_checker = None

    def reset_circuit_breaker(self):
        """Reset the circuit breaker to recover from stuck OPEN state."""
        if self.circuit_breaker:
            self.circuit_breaker.reset()
            self.logger.info("[RESET] Circuit breaker reset requested from StreamResolver")
    
    def _ensure_memory_dir(self):
        """Ensure memory directory exists for session caching."""
        os.makedirs("memory", exist_ok=True)

    def _get_channel_display_name(self, channel_id: str) -> str:
        """Get human-readable channel name for logging with visual indicators"""
        return SocialMediaRouter.get_display_name(channel_id)


    def _get_linkedin_page_for_channel(self, channel_id: str) -> str:
        """Determine which LinkedIn page to post to based on YouTube channel.

        Uses centralized SocialMediaRouter for single source of truth.
        Replaced complex config file + fallback logic with simple routing call.
        """
        return SocialMediaRouter.get_linkedin_page(channel_id)
    
    def clear_cache(self):
        """Clear all cached stream data for fresh lookup."""
        import os
        # Clear in-memory cache
        self._cache = {}
        self._last_stream_check = {}
        
        # Clear session cache file using SessionUtils
        if self.session_utils:
            cache_file = getattr(self.session_utils, 'DEFAULT_CACHE_FILE', 'memory/session_cache.json')
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                    self.logger.info("[CLEAR] Cleared session cache file for fresh search")
                except Exception as e:
                    self.logger.warning(f"Could not clear session cache: {e}")
        else:
            self.logger.warning("[CLEAR] No session utilities available for cache clearing")
        
        self.logger.info("[CLEAN] All caches cleared - will perform fresh stream search")
    
    def get_best_available_service(self):
        """
        Get the best available YouTube service with quota.
        Uses intelligent testing to find credentials with remaining quota.
        
        Returns:
            tuple: (service, credential_set) or (None, None) if all exhausted
        """
        if not self.use_intelligent_sorting or not self._quota_tester:
            # Fall back to normal rotation
            return self.youtube, getattr(self.youtube, '_credential_set', 0)
        
        self.logger.info("[TEST] Testing credentials for available quota...")
        
        # Get recommended order from quota tester
        recommended = self._quota_tester.get_recommended_order()
        
        if not recommended:
            self.logger.error("[ERROR] No credentials with available quota!")
            return None, None
        
        # Try credentials in recommended order
        for cred_set in recommended:
            if cred_set in self._tested_credentials:
                continue  # Skip already tested in this session
                
            try:
                cached_service = self._api_service_cache.get(cred_set)
                if cached_service is not None:
                    self.logger.debug("[API] Reusing cached YouTube service for credential set %s", cred_set)
                    self._tested_credentials.add(cred_set)
                    return cached_service, cred_set

                self.logger.info(f"Testing credential set {cred_set}...")
                service, actual_set = self._get_cached_authenticated_service(cred_set)
                
                if service:
                    self.logger.info(f"[SUCCESS] Using credential set {cred_set} with available quota")
                    self._tested_credentials.add(cred_set)
                    return service, cred_set
                    
            except Exception as e:
                self.logger.warning(f"Failed to use credential set {cred_set}: {e}")
                self._tested_credentials.add(cred_set)
                continue
        
        self.logger.error("[ERROR] All recommended credentials failed")
        return None, None

    def _normalize_authenticated_service_result(self, auth_result, requested_set=None):
        """Normalize auth helpers that return either service or tuple variants."""
        if isinstance(auth_result, tuple):
            service = auth_result[0] if auth_result else None
            actual_set = auth_result[1] if len(auth_result) > 1 else requested_set
        else:
            service = auth_result
            actual_set = getattr(service, "_credential_set", requested_set) if service is not None else requested_set
        return service, actual_set

    def _get_cached_authenticated_service(self, credential_set=None):
        """Return a cached authenticated service by credential set or auto-rotation."""
        cache_key = credential_set if credential_set is not None else "auto"
        cached = self._api_service_cache.get(cache_key)
        if cached is not None:
            actual_set = getattr(cached, "_credential_set", credential_set)
            self.logger.debug("[API] Reusing cached YouTube service for credential set %s", actual_set or cache_key)
            return cached, actual_set

        from modules.platform_integration.youtube_auth.src.youtube_auth import get_authenticated_service

        if credential_set is None:
            auth_result = get_authenticated_service()
        else:
            auth_result = get_authenticated_service(token_index=credential_set)
        service, actual_set = self._normalize_authenticated_service_result(auth_result, credential_set)

        if service is not None:
            actual_key = actual_set if actual_set is not None else getattr(service, "_credential_set", cache_key)
            try:
                service._credential_set = actual_key
            except Exception:
                pass
            self._api_service_cache[cache_key] = service
            self._api_service_cache[actual_key] = service
            self.logger.info("[API] Cached YouTube service for credential set %s", actual_key)
        return service, actual_set

    def _invalidate_cached_authenticated_service(self, service=None) -> None:
        """Drop cached API services after quota/auth failures so rotation can retry."""
        if service is None:
            self._api_service_cache.clear()
            return
        for key, cached in list(self._api_service_cache.items()):
            if cached is service:
                self._api_service_cache.pop(key, None)
    
    def _load_session_cache(self):
        """Load cached session data using SessionUtils from infrastructure."""
        if self.session_utils:
            return self.session_utils.load_cache()
        return None
    
    def _save_session_cache(self, video_id, chat_id, channel_id=None, title=None):
        """Save successful connection data using SessionUtils from infrastructure."""
        if self.session_utils:
            stream_title = title or self._get_stream_title(video_id)
            return self.session_utils.save_cache(
                video_id,
                chat_id,
                channel_id=channel_id,
                title=stream_title,
            )
        return False

    def _get_allowed_channel_ids(self, preferred_channel_id=None):
        """Build channel allowlist for cache validation."""
        channels_override = os.getenv("YT_CHANNELS_TO_CHECK", "").strip()
        if channels_override:
            allowed = [ch.strip() for ch in channels_override.split(",") if ch.strip()]
        else:
            allowed = get_channel_ids(role="live_check")
        if preferred_channel_id and preferred_channel_id not in allowed:
            allowed.insert(0, preferred_channel_id)
        return [ch for ch in allowed if ch]

    def _fetch_chat_id_with_rotation(self, video_id: str) -> Optional[str]:
        """
        Fetch liveChatId for a confirmed live video using credential rotation.
        
        This is called when vision/NO-QUOTA detection finds a live stream but
        doesn't have the chat_id. Uses fresh credentials to avoid quota issues.
        
        Args:
            video_id: Video ID of confirmed live stream
            
        Returns:
            activeLiveChatId if found, None otherwise
        """
        self.logger.info("="*60)
        self.logger.info("[CHAT-ID] FETCHING LIVE CHAT ID WITH CREDENTIAL ROTATION")
        self.logger.info(f"  - Video ID: {video_id}")
        self.logger.info("="*60)
        
        # Try up to 3 credential sets (auto-rotation built into get_authenticated_service)
        for attempt in range(3):
            youtube_service = None
            try:
                # Get fresh credentials via rotation (auto-rotates through available sets)
                if attempt > 0:
                    self.logger.info(f"[CHAT-ID] Attempt {attempt + 1}: Retrying with credential rotation...")

                youtube_service, _ = self._get_cached_authenticated_service()
                if not youtube_service:
                    self.logger.warning(f"[CHAT-ID] Attempt {attempt + 1}: No credentials available")
                    continue

                # Get credential set for logging (attached by youtube_auth)
                credential_set = getattr(youtube_service, '_credential_set', 'Unknown')
                self.logger.info(f"[CHAT-ID] Using credential set: {credential_set}")

                # Fetch liveStreamingDetails
                request = youtube_service.videos().list(
                    part="liveStreamingDetails",
                    id=video_id
                )
                response = request.execute()
                
                if not response.get('items'):
                    self.logger.warning(f"[CHAT-ID] Video {video_id} not found in API response")
                    continue
                
                video = response['items'][0]
                live_details = video.get('liveStreamingDetails', {})
                chat_id = live_details.get('activeLiveChatId')
                
                if chat_id:
                    self.logger.info(f"[CHAT-ID] SUCCESS: Found chat ID: {chat_id[:20]}...")
                    return chat_id
                else:
                    self.logger.warning(f"[CHAT-ID] No activeLiveChatId in response (stream may be ending)")
                    # Don't retry - if it's not there, it's not there
                    return None
                    
            except Exception as e:
                error_str = str(e).lower()
                if 'quota' in error_str or '403' in error_str or 'exceeded' in error_str:
                    self.logger.warning(f"[CHAT-ID] Quota exhausted on attempt {attempt + 1}, rotating...")
                    self._invalidate_cached_authenticated_service(youtube_service)
                    continue
                else:
                    self.logger.error(f"[CHAT-ID] Error fetching chat ID: {e}")
                    if attempt < 2:
                        self.logger.info("[CHAT-ID] Will retry with different credentials...")
                        continue
                    return None
        
        self.logger.error("[CHAT-ID] FAILED: Could not fetch chat ID after 3 attempts")
        return None
    
    def _try_cached_stream(self, cache, allowed_channel_ids=None, require_channel_id=False):
        """Try to connect to cached stream using SessionUtils from infrastructure."""
        if self.session_utils:
            return self.session_utils.try_cached_stream(
                cache,
                allowed_channel_ids=allowed_channel_ids,
                require_channel_id=require_channel_id,
            )
        return None, None
    
    def resolve_stream(self, channel_id=None):
        """
        Main method to resolve active livestream with intelligent cache-first approach.

        Args:
            channel_id: Optional channel ID to search (uses config default if not provided)

        Returns:
            Tuple of (video_id, chat_id) if found, None otherwise
        """
        # Safety switchboard: allow disabling *all* stream detection/scraping while debugging automation warnings.
        if os.getenv("YT_AUTOMATION_ENABLED", "true").strip().lower() not in ("1", "true", "yes", "y", "on"):
            self.logger.info("[AUTOMATION-AUDIT] stream_detection=disabled reason=YT_AUTOMATION_ENABLED=false")
            return None
        if os.getenv("YT_STREAM_SCRAPING_ENABLED", "true").strip().lower() not in ("1", "true", "yes", "y", "on"):
            self.logger.info("[AUTOMATION-AUDIT] stream_detection=disabled reason=YT_STREAM_SCRAPING_ENABLED=false")
            return None

        # Record check attempt start (WSP 78)
        check_start_time = datetime.now()
        # Prefer explicit channel_id, else env defaults, else hard-coded fallback
        search_channel_id = channel_id or os.getenv('CHANNEL_ID') or CHANNEL_ID
        
        # PRIORITY 1: Try cached stream first for instant reconnection
        cache = self._load_session_cache()
        if cache:
            # When a specific channel is requested, only accept cache hits for that channel.
            # This prevents a cached stream from masking other live channels during rotation.
            allowed_channel_ids = (
                [search_channel_id] if channel_id else self._get_allowed_channel_ids(search_channel_id)
            )
            self.logger.info("[RESET] Attempting cached stream reconnection...")
            video_id, chat_id = self._try_cached_stream(
                cache,
                allowed_channel_ids=allowed_channel_ids,
                require_channel_id=True,
            )
            if video_id and chat_id:
                self.logger.info(f"[ROCKET] INSTANT reconnection successful using cached stream!")
                return video_id, chat_id
            else:
                self.logger.debug("Cached stream no longer active, proceeding to fresh search")
        
        # PRIORITY 2: Check circuit breaker before making API calls
        if self.circuit_breaker and hasattr(self.circuit_breaker, 'state') and self.circuit_breaker.state == "OPEN":
            self.logger.warning(f"[FORBIDDEN] Circuit breaker OPEN - API calls blocked for {self.circuit_breaker.timeout/60:.1f} minutes")
            # Try to reset if timeout expired
            if hasattr(self.circuit_breaker, '_should_attempt_reset') and self.circuit_breaker._should_attempt_reset():
                self.logger.info("[RESET] Circuit breaker timeout expired, attempting reset...")
                self.circuit_breaker.state = "HALF_OPEN"
            else:
                self.logger.error("[ERROR] Circuit breaker still OPEN, cannot search for new streams")
                return None
        
        # PRIORITY 3: Use provided channel_id or fall back to env/constant (never None)
        search_channel_id = channel_id or os.getenv('CHANNEL_ID') or CHANNEL_ID
        if not search_channel_id:
            self.logger.error("[ERROR] No channel ID provided and none configured")
            return None

        # =====================================================================
        # STREAM DISCOVERY (2026-02-06 Architecture)
        # =====================================================================
        # Vision is NOT used for discovery - it navigates browsers which
        # disrupts comment engagement. Discovery uses HTTP scraping only.
        #
        # Vision is available for VERIFICATION only (verify_video_is_live)
        # when live chat needs to check if a known stream is still active.
        # =====================================================================

        # PRIORITY 4: NO-QUOTA mode - HTTP scraping (no browser navigation)
        # This is the PRIMARY stream discovery method (vision removed from discovery)
        if self.no_quota_checker:
            logger.info("="*60)
            logger.info("[NO-QUOTA] NO-QUOTA STREAM SEARCH (MULTI-CHANNEL ROTATION)")
            logger.info(f"   Using web scraping (0 API units)")

            # Get all channels to rotate through in idle mode
            channels_override = os.getenv("YT_CHANNELS_TO_CHECK", "").strip()
            if channels_override:
                channels_to_rotate = [ch.strip() for ch in channels_override.split(",") if ch.strip()]
                logger.info(f"[CONFIG] Using YT_CHANNELS_TO_CHECK override for stream rotation ({len(channels_to_rotate)} channels)")
            else:
                channels_to_rotate = get_channel_ids(role="live_check")
                test_channel = os.getenv("TEST_CHANNEL_ID", "").strip()
                if test_channel and test_channel not in channels_to_rotate:
                    channels_to_rotate.append(test_channel)
            channels_to_rotate = [ch for ch in channels_to_rotate if ch]  # Filter None values

            if channel_id:
                # Specific channel requested - just check that one
                logger.info(f"   Channel: {search_channel_id} ({self._get_channel_display_name(search_channel_id)})")
                logger.info(f"   Mode: Single channel search")
                channels_to_check = [search_channel_id]
            else:
                # No specific channel - rotate through all channels
                logger.info(f"   Rotating through {len(channels_to_rotate)} channels:")
                for i, ch in enumerate(channels_to_rotate, 1):
                    logger.info(f"     {i}. {self._get_channel_display_name(ch)} ({ch[:12]}...)")
                logger.info(f"   Mode: Multi-channel rotation until stream found")
                channels_to_check = channels_to_rotate

            logger.info("="*60)

            # NO-QUOTA mode: Intelligent pattern-based checking
            total_channels = len(channels_to_check) or 1
            channels_queue = list(channels_to_check)
            attempt = 0

            # Get pattern-based predictions for all channels
            channel_predictions = {}
            for cid in channels_to_check:
                if self.db:
                    predictions = self.db.predict_next_stream_time(cid)
                    if predictions:
                        channel_predictions[cid] = predictions

            while channels_queue:
                attempt += 1

                # Simple round-robin selection (QWEN provides intelligent prioritization via should_check_now)
                current_channel_id = channels_queue.pop(0)

                channel_name = self._get_channel_display_name(current_channel_id)
                pattern_info = ""
                if current_channel_id in channel_predictions:
                    pred = channel_predictions[current_channel_id]
                    pattern_info = f" (predicted: {pred.get('confidence', 0):.2f} confidence)"

                if channel_id:
                    logger.info(f"[TEST] NO-QUOTA check for {channel_name}{pattern_info}")
                else:
                    logger.info(f"[QWEN] [RESET] NO-QUOTA rotation [{attempt}/{total_channels}] - QWEN checking {channel_name}{pattern_info}")

                if self.qwen:
                    try:
                        profile = self.qwen.get_channel_profile(current_channel_id, channel_name)
                        should_check, reason = profile.should_check_now()
                        if not should_check:
                            logger.info(f"[SKIP] Skipping {channel_name}: {reason}")
                            continue
                    except Exception as q_err:
                        logger.debug(f"QWEN profile lookup failed for {channel_name}: {q_err}")

                env_video_id = get_env_variable("YOUTUBE_VIDEO_ID", default=None)
                if env_video_id:
                    logger.info(f"[📺] Checking specific video from env: {env_video_id}")
                    # Phase 2R: Direct call (resolve_stream is sync, not async)
                    env_result = self.no_quota_checker.check_video_is_live(env_video_id, channel_name)
                    if env_result.get('rate_limited'):
                        cooldown = env_result.get('cooldown')
                        if cooldown:
                            logger.warning(f"[WARN] Rate limit hit while checking env video {env_video_id} on {channel_name} - pausing {cooldown:.0f}s")
                        else:
                            logger.warning(f"[WARN] Rate limit hit while checking env video {env_video_id} on {channel_name}")
                        if self.qwen:
                            try:
                                profile = self.qwen.get_channel_profile(current_channel_id, channel_name)
                                profile.record_429_error()
                                self.qwen.global_heat_level = min(self.qwen.global_heat_level + 1, 10)
                            except Exception as q_err:
                                logger.debug(f"QWEN rate-limit record failed: {q_err}")
                        continue
                    if env_result.get('live'):
                        logger.info("[SUCCESS] STREAM IS LIVE (via NO-QUOTA video check)")
                        
                        # HEARTBEAT SIGNAL: Write live stream signal
                        try:
                            from .live_stream_signal import write_live_signal
                            write_live_signal(
                                channel_id=current_channel_id,
                                channel_name=channel_name or current_channel_id,
                                video_id=env_video_id,
                                source="env_video_checker"
                            )
                        except Exception as sig_err:
                            logger.debug(f"[SIGNAL] Failed to write live signal: {sig_err}")

                        if self.db:
                            try:
                                self.db.record_stream_start(current_channel_id, env_video_id, env_result.get('title', 'Live Stream'))
                                self.db.analyze_and_update_patterns(current_channel_id)
                            except Exception as db_err:
                                logger.warning(f"Database error (non-critical): {db_err}")
                        # Fetch chat_id with credential rotation
                        chat_id = self._fetch_chat_id_with_rotation(env_video_id)
                        if chat_id:
                            self._save_session_cache(
                                env_video_id,
                                chat_id,
                                channel_id=current_channel_id,
                                title=env_result.get('title'),
                            )
                        return env_video_id, chat_id
                    logger.info("[OK] Specified video not live")

                logger.info(f"[TEST] Searching {channel_name} ({current_channel_id[:12]}...) for live streams...")
                check_start = time.time()
                # Phase 2R: Direct call (resolve_stream is sync, not async)
                result = self.no_quota_checker.check_channel_for_live(current_channel_id, channel_name)
                check_duration = int((time.time() - check_start) * 1000)

                if self.db:
                    found = bool(result and result.get('live'))
                    self.db.record_check(current_channel_id, found, check_duration)

                if isinstance(result, dict) and result.get('rate_limited'):
                    cooldown = result.get('cooldown')
                    if cooldown:
                        logger.warning(f"[WARN] Rate limit encountered while scraping {channel_name} - cooling down for {cooldown:.0f}s")
                    else:
                        logger.warning(f"[WARN] Rate limit encountered while scraping {channel_name}")
                    if current_channel_id in channel_predictions:
                        channel_predictions[current_channel_id]['confidence'] = 0.0
                    if self.qwen:
                        try:
                            profile = self.qwen.get_channel_profile(current_channel_id, channel_name)
                            profile.record_429_error()
                            self.qwen.global_heat_level = min(self.qwen.global_heat_level + 1, 10)
                        except Exception as q_err:
                            logger.debug(f"QWEN rate-limit record failed: {q_err}")
                    continue

                if result and result.get('live'):
                    video_id = result.get('video_id')
                    if video_id:
                        logger.info(f"[SUCCESS] Found live stream on {channel_name}: {video_id} [CELEBRATE]")

                        # HEARTBEAT SIGNAL: Write live stream signal for comment DAE
                        # This allows comment rotation to pause when live stream detected
                        try:
                            from .live_stream_signal import write_live_signal
                            write_live_signal(
                                channel_id=current_channel_id,
                                channel_name=channel_name or current_channel_id,
                                video_id=video_id,
                                source="stream_resolver"
                            )
                        except Exception as sig_err:
                            logger.debug(f"[SIGNAL] Failed to write live signal: {sig_err}")

                        if self.db:
                            try:
                                self.db.record_stream_start(current_channel_id, video_id, result.get('title', 'Live Stream'))
                                self.db.analyze_and_update_patterns(current_channel_id)
                            except Exception as db_err:
                                logger.warning(f"Database error (non-critical): {db_err}")
                        # Fetch chat_id with credential rotation (NO-QUOTA doesn't provide it)
                        chat_id = self._fetch_chat_id_with_rotation(video_id)
                        if chat_id:
                            self._save_session_cache(
                                video_id,
                                chat_id,
                                channel_id=current_channel_id,
                                title=result.get('title'),
                            )
                        return video_id, chat_id

                if channels_queue:
                    delay = 2.0
                    next_channel = self._get_channel_display_name(channels_queue[0]) if channels_queue else channel_name
                    logger.info(f"[IDLE] No stream on {channel_name}, checking {next_channel} in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    logger.info(f"[OFFLINE] No live stream on {channel_name} (last channel checked)")

            if channel_id:
                logger.info(f"[OFFLINE] No live stream found on {self._get_channel_display_name(channel_id)}")
            else:
                logger.info(f"[OFFLINE] No live streams found on any of the {total_channels} channels")

            # HEARTBEAT SIGNAL: Clear live stream signal (no active stream)
            # This allows comment rotation to resume
            try:
                from .live_stream_signal import clear_live_signal
                clear_live_signal()
            except Exception as sig_err:
                logger.debug(f"[SIGNAL] Failed to clear signal: {sig_err}")

            return None
        else:
            # NO-QUOTA mode not available but could be initialized
            logger.info("[WARN] NO-QUOTA mode not available, attempting to initialize...")
            try:
                from .no_quota_stream_checker import NoQuotaStreamChecker
                self.no_quota_checker = NoQuotaStreamChecker()
                logger.info("[SUCCESS] NO-QUOTA mode initialized successfully, retrying...")
                # Recurse to retry with NO-QUOTA mode
                return self.resolve_stream(channel_id)
            except Exception as e:
                logger.warning(f"[ERROR] Failed to initialize NO-QUOTA mode: {e}")
                logger.info("[WARN] Falling back to API mode")

        # PRIORITY 5: Fallback to API mode if NO-QUOTA is not available
        # Check if API client is available before attempting
        if self.youtube is None:
            logger.error("[ERROR] API client is None")
            logger.info("[RESET] Attempting to initialize NO-QUOTA mode as emergency fallback...")
            try:
                from .no_quota_stream_checker import NoQuotaStreamChecker
                self.no_quota_checker = NoQuotaStreamChecker()
                logger.info("[SUCCESS] NO-QUOTA mode initialized as emergency fallback")
                return self.resolve_stream(channel_id)  # Retry with NO-QUOTA
            except Exception as e:
                logger.error(f"[ERROR] Failed to initialize emergency NO-QUOTA mode: {e}")
                # WSP 3 Phase 4: circuit_breaker now handled by youtube_api_ops
                raise StreamResolverError("No API client available and NO-QUOTA mode failed")

        logger.info("="*60)
        logger.info("[TEST] FALLBACK: API STREAM SEARCH STARTING")
        logger.info(f"   Target Channel: {search_channel_id} ({self._get_channel_display_name(search_channel_id)})")
        logger.info(f"   Using Service: {getattr(self.youtube, '_credential_set', 'Unknown') if self.youtube else 'None'}")
        logger.info("="*60)

        try:

            # Try with current service first
            try:
                # Use YouTubeAPIOperations for enhanced API call
                result = self.youtube_api_ops.get_active_livestream_video_id_enhanced(
                    self.youtube, search_channel_id
                )

                if result:
                    video_id, chat_id = result
                    # Record stream start in database (WSP 78)
                    stream_title = self._get_stream_title(video_id)
                    if self.db:
                        self.db.record_stream_start(search_channel_id, video_id, stream_title)
                    # Note: Social media posting handled by auto_moderator_dae
                    # self._trigger_social_media_post(video_id, stream_title)
                    # Save successful connection to cache for future instant access
                    self._save_session_cache(
                        video_id,
                        chat_id,
                        channel_id=search_channel_id,
                        title=stream_title,
                    )
                    self.logger.info(f"[SUCCESS] Found and cached new livestream for future instant access")
                    return video_id, chat_id
                else:
                    self.logger.info("No active livestream found")
                    return None
                    
            except QuotaExceededError:
                self.logger.warning("[RESET] Quota exceeded during stream search, trying credential rotation...")
                # Try with credential rotation
                fallback_result = get_authenticated_service_with_fallback()
                if fallback_result:
                    fallback_service, fallback_creds, credential_set = fallback_result
                    self.logger.info(f"[SUCCESS] Rotated to credential {credential_set} for stream search")
                    
                    # Update our service instance
                    self.youtube = fallback_service

                    # WSP 3 Phase 4: circuit_breaker now managed by youtube_api_ops
                    self.logger.info("[RESET] Credential rotation successful - youtube_api_ops will handle circuit breaker")
                    
                    # Retry with new credentials using YouTubeAPIOperations
                    result = self.youtube_api_ops.get_active_livestream_video_id_enhanced(
                        self.youtube, search_channel_id
                    )
                    
                    if result:
                        video_id, chat_id = result
                        # Save successful connection to cache for future instant access
                        self._save_session_cache(
                            video_id,
                            chat_id,
                            channel_id=search_channel_id,
                        )
                        self.logger.info(f"[SUCCESS] Found and cached new livestream with rotated credentials")
                        return video_id, chat_id
                    else:
                        self.logger.info("No active livestream found with rotated credentials")
                        return None
                else:
                    self.logger.error("[ERROR] Credential rotation failed for stream search")
                    return None
                
        except StreamResolverError as e:
            if "Circuit breaker is OPEN" in str(e):
                self.logger.error("[FORBIDDEN] Circuit breaker prevented API call - too many recent failures")
            else:
                self.logger.error(f"[ERROR] Stream resolution failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"[ERROR] Unexpected error during stream resolution: {e}")
            return None

    def _get_stream_title(self, video_id: str) -> Optional[str]:
        """
        Get the title of a YouTube stream from its video ID.

        Args:
            video_id: The YouTube video ID

        Returns:
            Stream title if available, None otherwise
        """
        try:
            if self.youtube:
                response = self.youtube.videos().list(
                    part="snippet",
                    id=video_id
                ).execute()

                if response.get("items"):
                    return response["items"][0]["snippet"].get("title")
            return None
        except Exception as e:
            self.logger.debug(f"Could not get stream title: {e}")
            return None


# ---------------------------------------------------------------------------
# Backward-compatible module-level helpers (tests + legacy integrations)
# ---------------------------------------------------------------------------

def search_livestreams_enhanced(youtube, event_type: str = "live", channel_id: Optional[str] = None, max_results: int = 10):
    """
    Legacy wrapper for enhanced livestream search.
    Keeps older tests working after refactor to YouTubeAPIOperations.
    """
    target_channel_id = channel_id or get_env_variable("CHANNEL_ID", CHANNEL_ID)
    logger.info(f"[API] Searching livestreams for channel {target_channel_id} (event_type={event_type})")
    ops = YouTubeAPIOperations(logger=logger)
    return ops.search_livestreams_enhanced(youtube, target_channel_id, max_results=max_results)


def find_active_stream(youtube, channel_id: Optional[str] = None):
    """
    Legacy wrapper for active stream detection.
    Returns (video_id, chat_id) or None.
    """
    target_channel_id = channel_id or get_env_variable("CHANNEL_ID", CHANNEL_ID)
    ops = YouTubeAPIOperations(logger=logger)
    return ops.get_active_livestream_video_id_enhanced(youtube, target_channel_id)


def get_active_livestream_video_id(youtube, channel_id: Optional[str] = None):
    """
    Legacy wrapper used by direct execution block.
    """
    return find_active_stream(youtube, channel_id=channel_id)

# Example usage block with enhanced error handling
if __name__ == '__main__':
    print("Running enhanced stream_resolver module directly...")
    
    try:
        import sys
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        
        from utils.logging_config import setup_logging
        from dotenv import load_dotenv
        
        load_dotenv()
        setup_logging()
        
        test_channel_id = os.getenv("TEST_CHANNEL_ID", CHANNEL_ID)
        if not test_channel_id:
            print("Please set TEST_CHANNEL_ID or CHANNEL_ID in your .env file")
            sys.exit(1)
        
        print(f"Testing with channel: {mask_sensitive_id(test_channel_id, 'channel')}")
        
        service = get_authenticated_service_with_fallback()
        if service:
            result = get_active_livestream_video_id(service, test_channel_id)
            if result:
                video_id, chat_id = result
                print(f"Success! Found livestream: {mask_sensitive_id(video_id, 'video')}")
                print(f"Chat ID: {mask_sensitive_id(chat_id, 'chat')}")
            else:
                print("No active livestream found")
        else:
            print("Authentication failed")
            
    except Exception as e:
        logger.exception(f"Error during direct execution: {e}")
        print(f"Error: {e}")
        sys.exit(1) 
        sys.exit(1) 
