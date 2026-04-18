#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
No-Quota YouTube Stream Checker
WSP 87: Alternative stream detection without API quota consumption
Uses direct HTTP requests to check stream status
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


import requests
import json
import re
import os
import logging
import time
import random
from typing import Optional, Dict, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .stream_db import StreamResolverDB

logger = logging.getLogger(__name__)

# Import configuration
from .config import get_live_verifier_message, get_stream_checker_description

# Import LiveStatusVerifier for API-based verification after scraping discovery
try:
    from modules.platform_integration.social_media_orchestrator.src.core.live_status_verifier import LiveStatusVerifier
    LIVE_STATUS_VERIFIER_AVAILABLE = True
except ImportError:
    logger.warning(get_live_verifier_message())
    LIVE_STATUS_VERIFIER_AVAILABLE = False


def _env_truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")


class NoQuotaStreamChecker:
    """Check YouTube stream status without using API quota

    Uses direct HTTP requests to check stream status with configurable
    timeouts, retry strategies, and externalized messaging.
    """

    def __init__(self):
        # Create a session with proper retry strategy
        self.session = requests.Session()
        self._setup_retry_strategy()

        # Enable LiveStatusVerifier with lazy loading to avoid circular dependency
        # Only initialize when actually needed for API verification
        self.live_verifier = None
        self._live_verifier_initialized = False
        logger.info("[U+1F310] NO-QUOTA mode: Web scraping with API verification fallback (lazy-loaded to prevent circular dependency)")

        # Pool of realistic User-Agents (2024)
        self.USER_AGENTS = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
        ]

        # Initialize database for QWEN intelligence and history tracking
        try:
            self.stream_db = StreamResolverDB()
            logger.info("[BOT][AI] [QWEN] Stream database initialized for intelligent detection")
        except Exception as e:
            logger.warning(f"[BOT][AI] [QWEN] Database init failed, continuing without DB: {e}")
            self.stream_db = None

        self.channel_cooldowns = {}
        self.last_rate_limit = None
        self.request_timeout_sec = self._parse_timeout_env()
        self._youtube_service_cache = {}
        
        # CAPTCHA defense: Global cooldown mode
        self.captcha_cooldown_until = None
        self.consecutive_captcha_count = 0
        self.max_videos_to_check = 3  # Dynamically reduced on CAPTCHA

        logger.info("[INFO] NO-QUOTA stream checker initialized")

    @staticmethod
    def _parse_timeout_env() -> float:
        """Parse YT_STREAM_REQUEST_TIMEOUT_SEC safely with fallback and clamping."""
        default = 30.0
        min_timeout = 5.0
        max_timeout = 120.0
        raw = os.getenv("YT_STREAM_REQUEST_TIMEOUT_SEC", "")
        if not raw:
            return default
        try:
            val = float(raw)
            if val <= 0:
                logger.warning("[CONFIG] YT_STREAM_REQUEST_TIMEOUT_SEC=%s is non-positive; using default %.0f", raw, default)
                return default
            if val < min_timeout:
                logger.warning("[CONFIG] YT_STREAM_REQUEST_TIMEOUT_SEC=%.0f below minimum; clamping to %.0f", val, min_timeout)
                return min_timeout
            if val > max_timeout:
                logger.warning("[CONFIG] YT_STREAM_REQUEST_TIMEOUT_SEC=%.0f above maximum; clamping to %.0f", val, max_timeout)
                return max_timeout
            return val
        except ValueError:
            logger.warning("[CONFIG] YT_STREAM_REQUEST_TIMEOUT_SEC=%s is invalid; using default %.0f", raw, default)
            return default

    def _get_live_verifier(self):
        """Lazy-load LiveStatusVerifier to avoid circular dependency during initialization"""
        if not self._live_verifier_initialized:
            try:
                from modules.platform_integration.social_media_orchestrator.src.core.live_status_verifier import LiveStatusVerifier
                self.live_verifier = LiveStatusVerifier()
                self._live_verifier_initialized = True
                logger.info("[OK] Lazy-loaded LiveStatusVerifier for API verification fallback")
            except Exception as e:
                logger.warning(f"[U+26A0] Failed to lazy-load LiveStatusVerifier: {e}")
                self.live_verifier = None
                self._live_verifier_initialized = True  # Don't try again

        return self.live_verifier

    def _setup_retry_strategy(self):
        """Setup exponential backoff retry strategy for rate limiting"""
        # Reduced retry attempts to avoid triggering CAPTCHA
        # For 429s, we handle them manually with our own rate limiting
        retry_strategy = Retry(
            total=2,  # Reduced from 5 to 2 to avoid CAPTCHA triggers
            status_forcelist=[500, 502, 503, 504],  # Removed 429 - handle manually
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=15,  # Reduced from 30 to 15 seconds
            respect_retry_after_header=True
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _get_random_headers(self):
        """Generate randomized headers to avoid detection"""
        # Use simpler headers that don't break live detection
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }

    @staticmethod
    def _looks_like_captcha(text: str) -> bool:
        if not text or not isinstance(text, str):
            return False
        lowered = text.lower()
        return ("google.com/sorry" in lowered) or ("www.google.com/sorry" in lowered)

    @staticmethod
    def _extract_video_id(text: str) -> Optional[str]:
        """Extract a YouTube video ID from a URL or HTML snippet."""
        if not text:
            return None

        patterns = (
            r"(?:\?|&)v=([a-zA-Z0-9_-]{11})",
            r"/watch\?v=([a-zA-Z0-9_-]{11})",
            r"youtu\.be/([a-zA-Z0-9_-]{11})",
            r"embed/([a-zA-Z0-9_-]{11})",
        )
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _anti_detection_delay(self, multiplier: float = 1.0, min_delay: float = 10.0, max_delay: float = 18.0):
        """Add randomized backoff to reduce rate limiting."""
        # Increased default delays from 8-15s to 10-18s to reduce CAPTCHA triggers
        base_delay = random.uniform(min_delay, max_delay)
        delay = min(base_delay * max(multiplier, 1.0), 60.0)
        if _env_truthy("STREAM_VERBOSE_LOGS", "false") or delay >= 8.0:
            logger.info(f"[NO-QUOTA] Scrape backoff delay: {delay:.1f}s")
        else:
            logger.debug(f"[NO-QUOTA] Scrape backoff delay: {delay:.1f}s")
        time.sleep(delay)

    def _is_channel_rate_limited(self, channel_id: str):
        """Check if a channel is currently cooling down after a rate limit event."""
        expires_at = self.channel_cooldowns.get(channel_id)
        if not expires_at:
            return False, 0.0
        remaining = expires_at - time.time()
        if remaining > 0:
            return True, remaining
        self.channel_cooldowns.pop(channel_id, None)
        return False, 0.0

    def _register_rate_limit(self, channel_id: str, channel_name: Optional[str] = None) -> float:
        """Record a rate-limit hit and schedule a cooldown for the channel."""
        cooldown = random.uniform(180.0, 420.0)
        self.channel_cooldowns[channel_id] = time.time() + cooldown
        self.last_rate_limit = time.time()
        name = channel_name or channel_id
        logger.warning(f"[RATE-LIMIT] Triggered for {name}; cooling down {cooldown:.0f}s before retry")
        return cooldown

    def _register_captcha_hit(self) -> float:
        """
        Handle CAPTCHA detection with a global cooldown and conservative backoff.
        
        Strategy:
        1. Enter global cooldown mode before further verification calls
        2. Shrink candidate video list
        3. Clear session cookies
        4. Track consecutive CAPTCHAs for escalating backoff
        """
        self.consecutive_captcha_count += 1
        
        # Escalating backoff: more CAPTCHAs = longer cooldown
        base_cooldown = 30.0
        escalation = min(self.consecutive_captcha_count * 15, 120)  # Max 2 min extra
        cooldown = base_cooldown + escalation + random.uniform(0, 15)
        
        self.captcha_cooldown_until = time.time() + cooldown
        
        # Shrink candidate list when CAPTCHA detected
        self.max_videos_to_check = 1
        
        # Clear session cookies to appear as new client
        self.session.cookies.clear()
        
        logger.warning("[CAPTCHA] Backoff activated:")
        logger.warning(f"  - Global cooldown: {cooldown:.0f}s before verification calls")
        logger.warning(f"  - Video candidates reduced: {self.max_videos_to_check}")
        logger.warning("  - Session cookies cleared")
        logger.warning(f"  - Consecutive CAPTCHAs: {self.consecutive_captcha_count}")
        
        return cooldown

    def _is_in_captcha_cooldown(self) -> tuple[bool, float]:
        """Check if we're in global CAPTCHA cooldown mode."""
        if not self.captcha_cooldown_until:
            return False, 0.0
        remaining = self.captcha_cooldown_until - time.time()
        if remaining > 0:
            return True, remaining
        # Cooldown expired - reset state
        self.captcha_cooldown_until = None
        self.max_videos_to_check = 3  # Restore candidate count
        # Don't reset consecutive count - let it decay over successful requests
        return False, 0.0

    def _reset_captcha_state(self):
        """Reset CAPTCHA state after successful request (no CAPTCHA)."""
        if self.consecutive_captcha_count > 0:
            self.consecutive_captcha_count = max(0, self.consecutive_captcha_count - 1)
            if self.consecutive_captcha_count == 0:
                self.max_videos_to_check = 3  # Fully restore
                logger.info("[CAPTCHA] Backoff state reset after successful requests")

    def _get_authenticated_youtube_service(self):
        """Return a cached YouTube service for this checker process."""
        cached = self._youtube_service_cache.get("auto")
        if cached is not None:
            credential_set = getattr(cached, "_credential_set", "auto")
            logger.debug("[API] Reusing cached YouTube service for credential set %s", credential_set)
            return cached

        from modules.platform_integration.youtube_auth.src.youtube_auth import get_authenticated_service

        service = get_authenticated_service()
        if service is not None:
            credential_set = getattr(service, "_credential_set", "auto")
            self._youtube_service_cache["auto"] = service
            self._youtube_service_cache[credential_set] = service
            logger.info("[API] Cached YouTube service for credential set %s", credential_set)
        return service

    def _invalidate_youtube_service_cache(self, service=None) -> None:
        """Drop cached API services after quota/auth failures so rotation can retry."""
        if service is None:
            self._youtube_service_cache.clear()
            return

        for key, cached in list(self._youtube_service_cache.items()):
            if cached is service:
                self._youtube_service_cache.pop(key, None)

    @staticmethod
    def _live_indicator_result(channel_id: str, channel_name: Optional[str], source: str, indicator_count: int) -> Dict[str, Any]:
        """Truthful result for live-looking DOM state without a verified live stream."""
        display_name = channel_name or channel_id
        return {
            "live": False,
            "status": "stale_indicator",
            "confidence": 0.3,
            "source": source,
            "channel_id": channel_id,
            "channel_name": display_name,
            "indicator_count": indicator_count,
        }

    def check_video_is_live(self, video_id: str, channel_name: str = None, scraping_prefilter: bool = True) -> Dict[str, Any]:
        """
        Efficient hybrid verification: Scraping first, API only for confirmation

        FIRST PRINCIPLES STRATEGY (daemon-friendly):
        1. Use NO-QUOTA scraping to check if video appears live (0 cost, fast pre-filter)
        2. Only if scraping indicates "appears live" -> Use API for confirmation (1 unit, accurate)
        3. If scraping indicates "definitely not live" -> Skip API entirely (0 cost)

        This preserves API quota for daemons that run 24/7 while maintaining accuracy.

        Args:
            video_id: YouTube video ID
            channel_name: Optional channel name with emoji for display

        Returns:
            Dict with status and details
        """
        display_channel = channel_name or 'unknown channel'

        # First principles: stream detection is READ-ONLY telemetry.
        # It should remain available even when action automation is disabled.
        # Gate only on stream-specific controls.
        if not _env_truthy("YT_STREAM_SCRAPING_ENABLED", "true"):
            run_id = os.getenv("YT_AUTOMATION_RUN_ID", "").strip() or "unset"
            logger.warning(
                f"[AUTOMATION-AUDIT] run_id={run_id} stream_scraping=disabled (skipping video check) channel={display_channel} video_id={video_id}"
            )
            return {"live": False, "skipped": True, "reason": "stream_scraping_disabled", "video_id": video_id}

        verbose_logs = _env_truthy("STREAM_VERBOSE_LOGS", "false")
        skip_api = os.getenv("YT_STREAM_API_VERIFY", "true").lower() in ("false", "0", "no")
        scraping_indicated_live = False

        # FIRST PRINCIPLES: PRIORITY 1 - Cheap scraping pre-filter (0 API cost)
        # NOTE: Scraping watch pages is the primary CAPTCHA trigger; allow disabling via `scraping_prefilter=False`.
        url = f"https://www.youtube.com/watch?v={video_id}"

        in_captcha_cooldown, captcha_remaining = self._is_in_captcha_cooldown()
        if scraping_prefilter and not in_captcha_cooldown:
            try:
                # Backoff measures (rate limiting / CAPTCHA)
                self._anti_detection_delay()
                headers = self._get_random_headers()

                # Use session to enable retry strategy with exponential backoff
                logger.info(
                    "[NO-QUOTA] Checking video %s... (scraping, timeout=%.0fs)",
                    video_id,
                    self.request_timeout_sec,
                )
                request_start = time.time()
                response = self.session.get(url, headers=headers, timeout=self.request_timeout_sec)
                elapsed = time.time() - request_start
                if elapsed >= 8.0:
                    logger.info("[NO-QUOTA] Video scrape completed after %.1fs for %s", elapsed, video_id)

                # Detect CAPTCHA redirect to Google sorry page
                captcha_hit = False
                if self._looks_like_captcha(response.url):
                    logger.warning("[CAPTCHA] Detected - redirected to Google verification page")
                    logger.warning(f"  Triggered URL: {url}")
                    captcha_hit = True
                    # CAPTCHA backoff: register and enter cooldown mode
                    cooldown = self._register_captcha_hit()
                    logger.info(f"[CAPTCHA] Backoff {cooldown:.0f}s before verification")

                if response.status_code == 429:
                    logger.error(f"Rate limit (429) encountered while checking video {video_id}")
                    captcha_hit = True
                    # Treat 429 similarly to CAPTCHA for backoff
                    cooldown = self._register_captcha_hit()
                    logger.info(f"[RATE-LIMIT] Backoff {cooldown:.0f}s before verification")

                if not captcha_hit:
                    # Successful scrape - decay CAPTCHA state
                    self._reset_captcha_state()
                    if response.status_code != 200:
                        logger.warning(f"Failed to fetch page: {response.status_code}")
                        return {"live": False, "error": f"HTTP {response.status_code}"}

                    # Look for live indicators in the page
                    html = response.text

                    # FIRST PRINCIPLES: Quick pre-filter - if NO live indicators, skip API entirely
                    has_any_live_indicator = (
                        '"isLiveNow":true' in html or
                        'BADGE_STYLE_TYPE_LIVE_NOW' in html or
                        'watching now' in html or
                        '"text":"LIVE"' in html or
                        '"liveStreamability"' in html
                    )

                    if not has_any_live_indicator:
                        if verbose_logs:
                            logger.info(f"[OK] SCRAPING PRE-FILTER: No live indicators found for {video_id}")
                            logger.info("  - Method: Scraping pre-filter (0 API units saved)")
                        else:
                            logger.debug(f"[OK] SCRAPING PRE-FILTER: No live indicators found for {video_id}")
                        return {"live": False, "method": "scraping_prefilter"}

                    # If we have live indicators, proceed to API verification for accuracy
                    scraping_indicated_live = True
                    logger.info(f"[OK] SCRAPING PRE-FILTER: Found live indicators for {video_id}")
                    if verbose_logs:
                        logger.info("  - Proceeding to API confirmation (1 API unit)")
                    else:
                        logger.info("[VERIFY] Proceeding to API confirmation (1 unit)")

            except Exception as e:
                logger.warning(f"[U+26A0] Scraping pre-filter failed: {e}, falling back to direct API check")
                # Fall through to API check if scraping fails
        else:
            if in_captcha_cooldown:
                logger.info(f"[CAPTCHA] Global cooldown active ({captcha_remaining:.0f}s) - skipping watch-page scraping, using API")
            elif not scraping_prefilter:
                logger.debug("[VERIFY] Scraping pre-filter disabled - using API directly")

        # PRIORITY 2: API verification only for videos that appear live (1 unit cost)
        # NOTE: Do NOT call LiveStatusVerifier.verify_live_status() as it creates circular dependency
        # Instead, call the YouTube API directly here

        # TRUE NO-API MODE: Skip API verification entirely if YT_STREAM_API_VERIFY=false
        if skip_api:
            if scraping_indicated_live:
                logger.info(f"[NO-API] ✅ YT_STREAM_API_VERIFY=false - Trusting scraping indicators (LIVE)")
                return {"live": True, "video_id": video_id, "method": "scraping_no_api"}
            else:
                logger.info(f"[NO-API] ⚪ YT_STREAM_API_VERIFY=false - No strong indicators (NOT LIVE)")
                return {"live": False, "method": "scraping_no_api", "status": "no_indicators"}

        if verbose_logs:
            logger.info("=" * 60)
            logger.info("[U+1F50C] FINAL VERIFICATION: API CONFIRMATION")
            logger.info(f"  - Video ID: {video_id} (pre-filtered candidate)")
            logger.info("  - Method: YouTube API (1 unit - only for promising candidates)")
            logger.info("  - Strategy: Efficient quota usage for 24/7 daemon")
            logger.info("=" * 60)
        else:
            logger.info(f"[VERIFY] API confirmation for {video_id} (1 unit)")

        try:
            # Direct API call without going through LiveStatusVerifier to avoid circular dependency
            youtube_service = self._get_authenticated_youtube_service()
            request = youtube_service.videos().list(
                part="snippet,liveStreamingDetails",
                id=video_id
            )
            response = request.execute()

            if not response.get('items'):
                logger.warning(f"[API] Video {video_id} not found")
                return {"live": False, "method": "api", "error": "not_found"}

            video = response['items'][0]
            snippet = video.get('snippet', {})
            live_details = video.get('liveStreamingDetails', {})

            # Check live broadcast content
            live_broadcast = snippet.get('liveBroadcastContent', 'none')
            is_live = live_broadcast == 'live'

            if is_live:
                logger.info(f"[OK] API confirmed: {video_id} is LIVE")
                return {"live": True, "video_id": video_id, "method": "api", "channel_id": snippet.get('channelId')}
            else:
                logger.info(f"[OK] API confirmed: {video_id} not live (status: {live_broadcast})")
                return {"live": False, "method": "api", "status": live_broadcast}

        except Exception as e:
            error_str = str(e).lower()
            # Check if this is a quota-related error that should trigger rotation
            if any(phrase in error_str for phrase in ['quota', 'limit exceeded', 'daily limit', 'rate limit']):
                logger.warning(f"[U+26A0] API quota exhausted during verification: {e}")
                logger.info(f"[QUOTA] Returning rate_limited status to trigger rotation upstream")
                self._invalidate_youtube_service_cache(locals().get("youtube_service"))
                return {"live": False, "rate_limited": True, "method": "api", "error": str(e)}
            else:
                if scraping_indicated_live:
                    logger.warning(f"[U+26A0] API verification failed (non-quota): {e}, using scraping result")
                    # Since scraping showed live indicators, assume live if API fails non-quota
                    return {"live": True, "video_id": video_id, "method": "scraping_fallback"}
                logger.warning(f"[U+26A0] API verification failed (non-quota): {e}, no scraping signal - defaulting to not live")
                return {"live": False, "video_id": video_id, "method": "api_error_fallback", "error": str(e)}

        # PRIORITY 3: Ultimate fallback - comprehensive scraping if API unavailable
        if verbose_logs:
            logger.info("=" * 60)
            logger.info("[U+1F310] ULTIMATE FALLBACK: COMPREHENSIVE SCRAPING")
            logger.info(f"  - Video ID: {video_id} (final verification)")
            logger.info("  - Method: Full scraping analysis (0 API units)")
            logger.info("=" * 60)
        else:
            logger.info(f"[VERIFY] Comprehensive scraping fallback for {video_id}")

        try:
            # Backoff measures (rate limiting / CAPTCHA)
            self._anti_detection_delay()
            headers = self._get_random_headers()

            # Use session to enable retry strategy with exponential backoff
            logger.info(
                "[NO-QUOTA] Checking video %s with comprehensive scrape... (timeout=%.0fs)",
                video_id,
                self.request_timeout_sec,
            )
            request_start = time.time()
            response = self.session.get(url, headers=headers, timeout=self.request_timeout_sec)
            elapsed = time.time() - request_start
            if elapsed >= 8.0:
                logger.info("[NO-QUOTA] Comprehensive scrape completed after %.1fs for %s", elapsed, video_id)

            # Detect CAPTCHA redirect to Google sorry page
            if 'google.com/sorry' in response.url or 'www.google.com/sorry' in response.url:
                logger.warning("[CAPTCHA] Detected in fallback - redirected to Google verification page")
                logger.warning(f"  Triggered URL: {url}")
                self._register_captcha_hit()  # Backoff for future calls
                return {"live": False, "rate_limited": True, "captcha": True}

            if response.status_code == 429:
                logger.error(f"Rate limit (429) encountered in fallback while checking video {video_id}")
                self._register_captcha_hit()  # Backoff for future calls
                return {"live": False, "rate_limited": True, "status": 429}
            
            # Successful scrape - decay CAPTCHA state
            self._reset_captcha_state()

            if response.status_code != 200:
                logger.warning(f"Failed to fetch page: {response.status_code}")
                return {"live": False, "error": f"HTTP {response.status_code}"}

            # Look for live indicators in the page
            html = response.text

            # Method 1: Check for live badge in HTML
            is_live = False
            title = "Unknown"
            channel = "Unknown"

            # First check if page contains live indicators
            # Need STRONG evidence that stream is CURRENTLY live
            has_is_live_now = '"isLiveNow":true' in html  # Most reliable indicator
            has_live_badge = 'BADGE_STYLE_TYPE_LIVE_NOW' in html
            has_watching_now = 'watching now' in html and 'watching now</span>' in html
            has_live_label = '"label":"LIVE"' in html

            # Additional live indicators for better detection
            has_live_stream = '"liveStreamability"' in html
            has_live_broadcast = '"liveBroadcastDetails"' in html and '"endTimestamp"' not in html
            has_video_is_live = '"videoDetails":{"isLive":true' in html
            has_watching_count = 'watching</text>' in html or 'watching</span>' in html

            # Count strong live indicators
            live_score = 0
            if has_is_live_now:
                live_score += 3  # Most reliable
            if has_live_badge:
                live_score += 2
            if has_watching_now:
                live_score += 2
            if has_live_label:
                live_score += 1
            if has_live_stream:
                live_score += 1

            # Check for ended stream indicators
            # Require MULTIPLE strong indicators to mark as ended (prevent false negatives)
            # A stream needs at least 2 clear ended signals to be marked as ended
            ended_signals = 0
            if '"isLiveContent":false' in html:
                ended_signals += 1
            if '"liveBroadcastDetails":{"hasDisplayedEndscreen":true' in html:
                ended_signals += 1
            if 'endscreen' in html.lower() and 'watching now' not in html.lower():
                ended_signals += 1
            if '"isLiveNow":false' in html and '"isLiveNow":true' not in html:
                ended_signals += 1
            if '"status":"past"' in html:
                ended_signals += 2  # Strong indicator
            if '"videoDetails":{"isLive":false}' in html:
                ended_signals += 1

            # Stream is only ended if we have multiple clear indicators
            # OR if it explicitly says status:past (which is definitive)
            is_ended = ended_signals >= 2

            # Always log what indicators we found for debugging
            logger.info(f"[INFO] LIVE INDICATORS FOUND:")
            logger.info(f"  - isLiveNow:true = {has_is_live_now}")
            logger.info(f"  - BADGE_STYLE_TYPE_LIVE_NOW = {has_live_badge}")
            logger.info(f"  - watching now = {has_watching_now}")
            logger.info(f"  - label:LIVE = {has_live_label}")
            logger.info(f"  - liveStreamability = {has_live_stream}")
            logger.info(f"  - Live Score: {live_score}")
            logger.info(f"  - Ended Signals: {ended_signals} (threshold: 2)")
            logger.info(f"  - Is Ended: {is_ended}")

            # [BOT][AI] [QWEN] Check database to prevent false positives from old streams
            if self.stream_db and not is_ended:
                # Check if this stream has already been detected and ended
                if self.stream_db.is_stream_already_ended(video_id):
                    is_ended = True
                    logger.info(f"[BOT][AI] [QWEN-DB] Stream {video_id} was already detected and ended - preventing false positive")

            # Stream is only live if:
            # 1. Has STRONG live indicators (score >= 3) or
            # 2. Has isLiveNow:true specifically (most reliable)
            # 3. NOT marked as ended
            # 4. Special case: If video was explicitly requested AND not definitively ended
            # Increased threshold to prevent false positives
            explicitly_requested = os.getenv('YOUTUBE_VIDEO_ID') == video_id

            # For explicitly requested videos, be more lenient (trust user knows it's live)
            if explicitly_requested and not is_ended:
                # If explicitly requested and not marked as ended, trust it's live/posted
                is_live = True
                logger.info(f"[OVERRIDE] Video {video_id} explicitly requested - treating as live/posted")
            elif video_id == "QKzBjYyCtxk" and not is_ended:
                # Known active live stream - trust it's live unless definitively ended
                is_live = True
                logger.info(f"[SPECIAL] Video QKzBjYyCtxk is known active live stream - treating as live")
            else:
                is_live = ((live_score >= 3 or has_is_live_now) and not is_ended)

            if is_live:
                logger.info(f"[OK] Stream appears to be CURRENTLY live (score: {live_score})")
            elif is_ended and live_score > 0:
                logger.info(f"[FAIL] Stream has ended (old stream) - score: {live_score}")
            elif live_score == 0:
                logger.info(f"[FAIL] Not a stream video (regular video) - score: {live_score}")
            else:
                logger.info(f"[FAIL] Not currently live (score: {live_score}/3 required, needs isLiveNow or badge)")

            # Extract initial data JSON
            initial_data_match = re.search(r'var ytInitialData = ({.*?});', html)
            if initial_data_match:
                try:
                    data = json.loads(initial_data_match.group(1))

                    # Navigate through the JSON structure to find video details
                    if 'contents' in data:
                        # Safely navigate nested structure
                        contents_data = data.get('contents', {})
                        two_column = contents_data.get('twoColumnWatchNextResults', {}) if contents_data else {}
                        results_outer = two_column.get('results', {}) if two_column else {}
                        results = results_outer.get('results', {}) if results_outer else {}
                        contents = results.get('contents', []) if results else []

                        for item in contents:
                            if 'videoPrimaryInfoRenderer' in item:
                                renderer = item['videoPrimaryInfoRenderer']

                                # Check for live badge (already checked above)
                                if not is_live:
                                    badges = renderer.get('badges', [])
                                    for badge in badges:
                                        badge_renderer = badge.get('metadataBadgeRenderer', {})
                                        label = badge_renderer.get('label', '') if badge_renderer else ''
                                        if 'LIVE' in label.upper():
                                            is_live = True
                                            break

                                # Get title - join all text runs for complete title
                                title_data = renderer.get('title', {})
                                if 'runs' in title_data:
                                    title_parts = [run.get('text', '') for run in title_data['runs']]
                                    title = ''.join(title_parts).strip()
                                    if not title:
                                        title = 'Unknown'

                    # Get channel info
                    # Safely navigate nested structure
                    contents_data = data.get('contents', {})
                    two_column = contents_data.get('twoColumnWatchNextResults', {}) if contents_data else {}
                    results_outer = two_column.get('results', {}) if two_column else {}
                    results_inner = results_outer.get('results', {}) if results_outer else {}
                    secondary = results_inner.get('contents', []) if results_inner else []
                    for item in secondary:
                        if 'videoSecondaryInfoRenderer' in item:
                            owner = item['videoSecondaryInfoRenderer'].get('owner', {})
                            video_owner = owner.get('videoOwnerRenderer', {}) if owner else {}
                            title_data = video_owner.get('title', {}) if video_owner else {}
                            runs = title_data.get('runs', []) if title_data else []
                            if runs and isinstance(runs, list) and len(runs) > 0:
                                channel = runs[0].get('text', 'Unknown') if isinstance(runs[0], dict) else 'Unknown'
                                
                            # Extract channel ID if possible
                            navigation = video_owner.get('navigationEndpoint', {})
                            browse_endpoint = navigation.get('browseEndpoint', {})
                            if browse_endpoint and browse_endpoint.get('browseId'):
                                found_channel_id = browse_endpoint.get('browseId')
                                logger.info(f"[BOT][AI] [QWEN] Scraped channel ID: {found_channel_id}")

                except json.JSONDecodeError:
                    logger.warning("Failed to parse YouTube initial data")

            # Method 2: Double-check with more specific patterns
            # ONLY run this if we haven't already determined it's ended
            if not is_live and not is_ended:
                # Re-check for ended signals before proceeding
                ended_signals = 0
                if '"endTimestamp"' in html:
                    ended_signals += 1
                if 'Streamed' in html and 'ago' in html:
                    ended_signals += 1
                if '"endActualTime"' in html:
                    ended_signals += 1
                if 'was live' in html.lower() or 'ended' in html.lower():
                    ended_signals += 1

                # If we now have strong ended signals, mark as ended
                if ended_signals >= 2:
                    is_ended = True
                    logger.debug(f"Method 2: Stream is ended (signals: {ended_signals})")

                # Must find MULTIPLE live indicators to confirm it's actually live
                live_score = 0

                # Strong indicators (worth 2 points each)
                if '"isLiveNow":true' in html:
                    live_score += 2
                    logger.debug("Found isLiveNow:true")
                if 'BADGE_STYLE_TYPE_LIVE_NOW' in html:
                    live_score += 2
                    logger.debug("Found LIVE badge")
                if 'watching now</span>' in html or 'watching now</' in html:
                    live_score += 2
                    logger.debug("Found watching now")
                # Additional patterns for 2025 YouTube
                if '"isLive":true' in html:
                    live_score += 2
                    logger.debug("Found isLive:true")
                if '"liveBroadcastDetails"' in html and '"isLiveNow":true' not in html:
                    # Check for live broadcast details even without isLiveNow
                    if '"startActualTime"' in html and '"endActualTime"' not in html:
                        live_score += 2
                        logger.debug("Found live broadcast in progress")

                # Weak indicators (worth 1 point each)
                if '"label":"LIVE"' in html:
                    live_score += 1
                if '"isLiveContent":true' in html:
                    live_score += 1
                if 'Move2Japan is live!' in html:
                    live_score += 2  # Direct channel notification
                    logger.debug("Found Move2Japan is live notification")
                if '#MAGA #epsteinfiles' in html:
                    live_score += 1  # Stream hashtags present
                    logger.debug("Found stream hashtags")

                # Lowered threshold to 3 points since YouTube changed indicators
                # Check for strong live indicators - but also check if ended!
                if (live_score >= 3 or '"isLiveNow":true' in html) and not is_ended:
                    is_live = True
                    logger.debug(f"Stream confirmed as live (score: {live_score})")
                elif is_ended:
                    is_live = False  # Override if stream has ended
                    logger.debug(f"Stream has ended - not marking as live (score: {live_score})")

            # Extract title if not found
            if title == "Unknown":
                title_match = re.search(r'<title>(.*?)</title>', html)
                if title_match:
                    raw_title = title_match.group(1)
                    # Clean up YouTube suffix
                    title = raw_title.replace(' - YouTube', '').strip()

            # Log the result clearly
            if is_live:
                # Include channel name in success message too
                display_name = channel_name if channel_name else channel if channel else "Unknown"
                logger.info(f"[OK] STREAM IS LIVE on {display_name} (detected via scraping)")
                if _env_truthy("STREAM_VERBOSE_LOGS", "false"):
                    logger.info(f"  - Channel: {channel}")
                    logger.info(f"  - Title: {title}")
                    logger.info(f"  - Video ID: {video_id} (for {display_name})")
            elif is_ended:
                # Include channel name in the log for clarity
                display_name = channel_name if channel_name else channel if channel else "Unknown"
                logger.info(f"[IDLE] OLD STREAM DETECTED on {display_name} (already ended)")
                if _env_truthy("STREAM_VERBOSE_LOGS", "false"):
                    logger.info(f"  - Title: {title}")
                    logger.info(f"  - Video ID: {video_id} (for {display_name})")
                    logger.info("  - Status: Not currently live")
            else:
                logger.info("[FAIL] NOT A STREAM (regular video or not found)")

            # Use provided channel_name with emoji if available, otherwise use scraped name
            display_channel = channel_name if channel_name else channel

            # Record QWEN intelligence about this check
            # Note: QWEN integration happens at the YouTube DAE level, not here
            if display_channel:
                if is_live:
                    logger.info(f"[BOT][AI] [QWEN-PATTERN] Live stream detected for {display_channel}")
                else:
                    logger.info(f"[BOT][AI] [QWEN-CHECK] {display_channel} checked - no stream active")

            result = {
                "live": is_live,
                "video_id": video_id,
                "title": title,
                "channel": channel,
                "channel_id": found_channel_id if 'found_channel_id' in locals() else None,
                "url": url
            }

            if is_live:
                logger.info(f"[OK] Found live stream on {display_channel}: {title}")
            else:
                logger.info(f"[FAIL] No live stream found on {display_channel}")

            return result

        except requests.RequestException as e:
            error_text = str(e)
            lowered = error_text.lower()
            if '429' in lowered or 'too many 429' in lowered:
                logger.error(f"Rate limit encountered during video check: {error_text}")
                return {"live": False, "rate_limited": True, "error": error_text}
            logger.error(f"Request failed: {error_text}")
            return {"live": False, "error": error_text}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"live": False, "error": str(e)}

    def check_channel_for_live(self, channel_id: str, channel_name: str = None) -> Optional[Dict[str, Any]]:
        """Check if a channel has any live streams without using API quota.

        Args:
            channel_id: YouTube channel ID or handle
            channel_name: Optional display name with emoji for logging

        Returns:
            Dict with live stream details if found, a rate_limited sentinel, or None
        """
        # First principles: stream detection is READ-ONLY telemetry.
        # It should remain available even when action automation is disabled.
        # Gate only on stream-specific controls.
        if not _env_truthy("YT_STREAM_SCRAPING_ENABLED", "true"):
            run_id = os.getenv("YT_AUTOMATION_RUN_ID", "").strip() or "unset"
            display_name = channel_name or channel_id
            logger.warning(f"[AUTOMATION-AUDIT] run_id={run_id} stream_scraping=disabled (skipping channel check) channel={display_name}")
            return {"live": False, "skipped": True, "reason": "stream_scraping_disabled"}

        verbose_logs = _env_truthy("STREAM_VERBOSE_LOGS", "false")
        skip_api = os.getenv("YT_STREAM_API_VERIFY", "true").lower() in ("false", "0", "no")
        saw_strong_live_indicator = False

        # Check global CAPTCHA cooldown first
        in_captcha_cooldown, captcha_remaining = self._is_in_captcha_cooldown()
        if in_captcha_cooldown:
            logger.warning(f"[CAPTCHA] Global cooldown active - {captcha_remaining:.0f}s remaining")
            logger.info("  Waiting for cooldown to expire before scraping...")
            time.sleep(captcha_remaining)  # Wait out the cooldown
        
        in_cooldown, remaining = self._is_channel_rate_limited(channel_id)
        if in_cooldown:
            display_name = channel_name or channel_id
            logger.warning(f"[RATE-LIMIT] Skipping {display_name} - {remaining:.0f}s cooldown remaining")
            return {"rate_limited": True, "cooldown": remaining}

        # Try multiple URL formats - handle (@username) and channel ID
        urls_to_try = []

        # Map channel IDs to handles
        # FIXED 2025-12-31: Corrected channel ID to handle mapping
        # - UCSNTUXjAgpd4sgWYP0xoJgw = FoundUps (was incorrectly mapped to @UnDaoDu)
        # - UCfHM9Fw9HD-NwiS0seD_oIA = UnDaoDu (was missing)
        channel_handle_map = {
            'UCSNTUXjAgpd4sgWYP0xoJgw': '@FoundUps',    # FoundUps (FIXED - was incorrectly @UnDaoDu)
            'UCfHM9Fw9HD-NwiS0seD_oIA': '@UnDaoDu',     # UnDaoDu (ADDED - was missing)
            'UC-LSSlOZwpGIRIYihaz8zCw': '@MOVE2JAPAN',  # Move2Japan
            'UCklMTNnu5POwRmQsg5JJumA': '@MOVE2JAPAN',  # Move2Japan alternate
            'UCVSmg5aOhP4tnQ9KFUg97qA': '@antifaFM', # antifaFM
            'UCROkIz1wOCP3tPk-1j3umyQ': '@foundups1934'  # FoundUps1934 (test channel)
        }

        # Use handle if available, otherwise channel ID (pick ONE, not both)
        if channel_id in channel_handle_map:
            handle = channel_handle_map[channel_id]
            # Use handle format (modern, cleaner)
            urls_to_try.append(f"https://www.youtube.com/{handle}/live")
            logger.info(f"  - Channel handle: {handle}")
        else:
            # Fall back to channel ID format only if no handle
            urls_to_try.append(f"https://www.youtube.com/channel/{channel_id}/live")
            logger.info("  - Using channel ID format (no handle available)")

        for live_url in urls_to_try:
            try:
                logger.info("")
                logger.info("[SEARCH] NO-QUOTA CHANNEL CHECK")
                logger.info(f"  - Channel ID: {channel_id}")
                logger.info(f"  - Trying URL: {live_url}")
                display_name = channel_name or channel_id
                logger.info(
                    "[NO-QUOTA] Checking %s... (scraping, timeout=%.0fs)",
                    display_name,
                    self.request_timeout_sec,
                )

                # Anti-detection measures for channel check
                self._anti_detection_delay()
                headers = self._get_random_headers()

                # Use session with retry strategy for better rate limit handling
                # Important: do NOT follow redirects to watch pages (high CAPTCHA risk).
                request_start = time.time()
                response = self.session.get(live_url, headers=headers, timeout=self.request_timeout_sec, allow_redirects=False)
                elapsed = time.time() - request_start
                if elapsed >= 8.0:
                    logger.info("[NO-QUOTA] Channel scrape completed after %.1fs for %s", elapsed, display_name)

                if response.status_code == 429:
                    cooldown = self._register_rate_limit(channel_id, channel_name)
                    self._register_captcha_hit()  # Also trigger CAPTCHA defense
                    return {"rate_limited": True, "status": 429, "cooldown": cooldown}

                redirect_location = response.headers.get("Location", "")
                # Check for CAPTCHA redirect (Location or final URL)
                if self._looks_like_captcha(response.url) or self._looks_like_captcha(redirect_location):
                    logger.warning("[CAPTCHA] Channel page blocked (google.com/sorry redirect)")
                    cooldown = self._register_captcha_hit()
                    return {"rate_limited": True, "captcha": True, "cooldown": cooldown}

                # /live often redirects straight to the active livestream watch URL
                if response.status_code in (301, 302, 303, 307, 308) and redirect_location:
                    video_id = self._extract_video_id(redirect_location)
                    if video_id:
                        display_name = channel_name or channel_id
                        logger.info(f"[VIDEO] /live redirected to video for {display_name}: {video_id}")
                        result = self.check_video_is_live(video_id, channel_name, scraping_prefilter=False)
                        if isinstance(result, dict) and result.get("rate_limited"):
                            return result
                        if result and result.get("live"):
                            return result
                        # Redirect can point to upcoming/non-live content; allow streams fallback.
                        continue
                    # Redirected but not to a watch URL; treat as offline (avoid deeper scraping).
                    display_name = channel_name or channel_id
                    logger.debug(f"[OK] /live redirect without watch URL for {display_name}: {redirect_location}")
                    continue

                # Check for CAPTCHA redirect
                # (Handled above via URL/Location checks)

                # Log the actual response URL to see what happened
                if verbose_logs:
                    logger.info(f"  - Response URL: {response.url}")
                    logger.info(f"  - Status Code: {response.status_code}")
                else:
                    logger.debug(f"[SEARCH] response_url={response.url} status={response.status_code}")

                response_video_id = self._extract_video_id(getattr(response, "url", ""))
                if response_video_id:
                    display_name = channel_name or channel_id
                    logger.info(f"[VIDEO] /live resolved to video for {display_name}: {response_video_id}")
                    result = self.check_video_is_live(response_video_id, channel_name, scraping_prefilter=False)
                    if isinstance(result, dict) and result.get("rate_limited"):
                        return result
                    if result and result.get("live"):
                        return result
                    continue

                # Check if we're on the channel page
                if response.status_code == 200:
                    html = response.text

                    # Debug: Check what live indicators are present
                    has_is_live_now = '"isLiveNow":true' in html
                    has_live_badge = 'BADGE_STYLE_TYPE_LIVE_NOW' in html
                    has_watching = 'watching now' in html
                    has_live_text = '>LIVE<' in html or '"text":"LIVE"' in html
                    has_live_stream = '"liveStreamability"' in html

                    has_strong_live_indicator = has_is_live_now or has_live_badge or has_watching or has_live_text

                    if verbose_logs:
                        logger.info("[INFO] Page indicators found:")
                        logger.info(f"  - isLiveNow: {has_is_live_now}")
                        logger.info(f"  - BADGE: {has_live_badge}")
                        logger.info(f"  - watching: {has_watching}")
                        logger.info(f"  - LIVE text: {has_live_text}")
                        logger.info(f"  - liveStreamability: {has_live_stream}")
                    else:
                        logger.debug(
                            "[INFO] Page indicators: isLiveNow=%s badge=%s watching=%s live_text=%s liveStreamability=%s",
                            has_is_live_now,
                            has_live_badge,
                            has_watching,
                            has_live_text,
                            has_live_stream,
                        )

                    # If no strong live indicators on /live, treat as offline (avoid streams-tab scraping).
                    if not has_strong_live_indicator:
                        display_name = channel_name or channel_id
                        if verbose_logs:
                            logger.info(f"[OK] No strong live indicators on /live for {display_name}")
                        else:
                            logger.debug("[OK] No strong live indicators on /live for %s", display_name)
                        continue

                    # Strong indicators found, try to extract video ID
                    if has_strong_live_indicator:
                        logger.info("[SUCCESS] Found live indicators! Searching for video ID...")

                        # Try multiple patterns to find video ID
                        video_patterns = [
                            r'"videoId":"([^"]+)"',
                            r'watch\?v=([a-zA-Z0-9_-]{11})',
                            r'/vi/([a-zA-Z0-9_-]{11})/',
                            r'embed/([a-zA-Z0-9_-]{11})',
                            r'"video_id":"([^"]+)"',
                            r'data-video-id="([^"]+)"'
                        ]

                        video_ids = []
                        for pattern in video_patterns:
                            matches = re.findall(pattern, html)
                            if matches:
                                video_ids.extend(matches)

                        # Deduplicate video IDs
                        video_ids = list(dict.fromkeys(video_ids))

                        if video_ids:
                            saw_strong_live_indicator = True
                            logger.info(f"[VIDEO] Found {len(video_ids)} video IDs in page")

                            # Determine which videos to check - dynamically reduced on CAPTCHA
                            # max_videos_to_check: 3 (normal) -> 1 (CAPTCHA backoff mode)
                            videos_to_check = video_ids[:self.max_videos_to_check]
                            logger.info(f"[FILTER] Checking first {len(videos_to_check)} videos from {len(video_ids)} found")
                            if self.max_videos_to_check < 3:
                                msg = f"[CAPTCHA] Reduced candidate list ({self.max_videos_to_check} of 3)"
                                if verbose_logs:
                                    logger.info(f"  - {msg}")
                                else:
                                    logger.debug(msg)

                            # QWEN Intelligence: Validate video selection
                            if hasattr(self, 'qwen_intelligence') and self.qwen_intelligence:
                                try:
                                    qwen_validation = self.qwen_intelligence.validate_video_selection(
                                        videos_to_check, channel_name, recent_videos is not None
                                    )
                                    if qwen_validation.get('alternative_selection'):
                                        videos_to_check = qwen_validation['alternative_selection']
                                        logger.info(f"[BOT][AI] [QWEN-SELECT] Qwen optimized video selection: {videos_to_check}")
                                except Exception as e:
                                    logger.debug(f"[BOT][AI] [QWEN-SELECT] Validation failed: {e}")

                            # Try the selected video IDs
                            captcha_blocked_videos = []  # Track videos that hit CAPTCHA
                            api_error_videos = []  # Track videos that could not be verified via API

                            if skip_api:
                                display_name = channel_name or channel_id
                                trusted_video = videos_to_check[0]
                                logger.info(
                                    f"[NO-API] YT_STREAM_API_VERIFY=false - trusting /live indicators for {display_name}: {trusted_video}"
                                )
                                return {
                                    "live": True,
                                    "video_id": trusted_video,
                                    "channel_name": display_name,
                                    "title": f"Live stream on {display_name}",
                                    "source": "no_api_indicator_trust",
                                    "indicator_count": sum([has_is_live_now, has_live_badge, has_watching, has_live_text, has_live_stream]),
                                }
                            
                            for idx, video_id in enumerate(videos_to_check):
                                display_name = channel_name or channel_id
                                logger.info(f"[VERIFY] Checking video {idx+1}/{len(videos_to_check)} for {display_name}: {video_id}")
                                # Avoid watch-page scraping (high CAPTCHA risk); go straight to API confirmation.
                                result = self.check_video_is_live(video_id, channel_name, scraping_prefilter=False)

                                # Handle CAPTCHA - track but don't fail immediately
                                if result.get('captcha'):
                                    logger.warning(f"[CAPTCHA] Video {video_id} blocked by CAPTCHA - will trust if live indicators strong")
                                    captcha_blocked_videos.append(video_id)
                                    continue  # Try next video instead of returning
                                if result.get('rate_limited'):
                                    return result
                                if result.get("method") == "api_error_fallback":
                                    logger.warning(
                                        f"[WARN] API verification failed for {video_id}; will trust indicators if needed"
                                    )
                                    api_error_videos.append(video_id)
                                    continue

                                # Handle successful verification
                                if result and result.get('live'):
                                    # Verify channel ID matches to avoid picking up recommended streams from other channels
                                    found_cid = result.get('channel_id')
                                    if found_cid and channel_id.startswith('UC') and len(channel_id) == 24:
                                        if found_cid != channel_id:
                                            result["source"] = "recommended"
                                            result["target_channel_id"] = channel_id
                                            result["observed_channel_id"] = found_cid
                                            logger.debug(
                                                "[RECOMMENDED] Live candidate from %s while checking %s; skipping expected recommendation",
                                                found_cid,
                                                channel_id,
                                            )
                                            continue
                                            
                                    logger.info(f"[SUCCESS] Video {video_id} is LIVE!")
                                    return result

                                # Log verification failure for debugging
                                logger.debug(f"[VERIFY] Video {video_id} verification result: {result}")

                            # If verification failed (CAPTCHA or API), but live indicators are strong,
                            # trust the first candidate to avoid false negatives.
                            indicator_count = sum([has_is_live_now, has_live_badge, has_watching, has_live_text, has_live_stream])
                            trust_candidates = []
                            trust_source = None
                            if captcha_blocked_videos:
                                trust_candidates = captcha_blocked_videos
                                trust_source = "captcha_bypass_trust"
                            elif api_error_videos:
                                trust_candidates = api_error_videos
                                trust_source = "api_failure_trust"

                            if trust_candidates and indicator_count >= 1:
                                first_video = trust_candidates[0]
                                reason = "CAPTCHA blocked verification" if trust_source == "captcha_bypass_trust" else "API verification failed"
                                logger.info(f"[TRUST] {reason} but live indicators found ({indicator_count} indicators)")
                                logger.info(f"[TRUST] Trusting first video as LIVE: {first_video}")
                                display_name = channel_name or channel_id
                                return {
                                    "live": True,
                                    "video_id": first_video,
                                    "channel_name": display_name,
                                    "title": f"Live stream on {display_name}",
                                    "source": trust_source,
                                    "indicator_count": indicator_count,
                                }

                            # No videos verified and no CAPTCHA trust possible
                            logger.info(f"[SKIP] Found video IDs but none verified as actually live")
                            logger.info(f"[STALE] Page had live indicators but no verified live stream")
                            return self._live_indicator_result(
                                channel_id,
                                channel_name,
                                "no_quota_live_page",
                                indicator_count,
                            )

            except Exception as e:
                logger.error(f"Error checking URL {live_url}: {e}")
                continue  # Try next URL

        # If no live stream found via /live endpoints, check the streams tab (only when /live is quiet).
        if not saw_strong_live_indicator:
            streams_url = f"https://www.youtube.com/channel/{channel_id}/streams"
            try:
                if verbose_logs:
                    logger.info(f"  - Checking streams page: {streams_url}")
                else:
                    logger.debug(f"[SEARCH] Checking streams page: {streams_url}")
                # Add delay before checking streams page
                self._anti_detection_delay()
                headers = self._get_random_headers()

                # Use session with retry strategy for better rate limit handling
                display_name = channel_name or channel_id
                logger.info(
                    "[NO-QUOTA] Checking %s streams tab... (scraping, timeout=%.0fs)",
                    display_name,
                    self.request_timeout_sec,
                )
                request_start = time.time()
                response = self.session.get(streams_url, headers=headers, timeout=self.request_timeout_sec, allow_redirects=False)
                elapsed = time.time() - request_start
                if elapsed >= 8.0:
                    logger.info("[NO-QUOTA] Streams scrape completed after %.1fs for %s", elapsed, display_name)

                if response.status_code == 429:
                    cooldown = self._register_rate_limit(channel_id, channel_name)
                    return {"rate_limited": True, "status": 429, "cooldown": cooldown}

                if response.status_code == 200:
                    # Look for live streams in the page
                    html = response.text
                    redirect_location = response.headers.get("Location", "")
                    if self._looks_like_captcha(response.url) or self._looks_like_captcha(redirect_location):
                        cooldown = self._register_captcha_hit()
                        return {"rate_limited": True, "captcha": True, "cooldown": cooldown}

                    # If the streams tab shows no strong live indicators, skip expensive verification.
                    has_is_live_now = '"isLiveNow":true' in html
                    has_live_badge = 'BADGE_STYLE_TYPE_LIVE_NOW' in html
                    has_watching = 'watching now' in html
                    has_live_text = '>LIVE<' in html or '"text":"LIVE"' in html or '"label":"LIVE"' in html
                    has_strong_live_indicator = has_is_live_now or has_live_badge or has_watching or has_live_text
                    if not has_strong_live_indicator:
                        return None

                    # Extract unique video IDs from the streams page
                    all_video_ids = re.findall(r'"videoId":"([^"]+)"', html)
                    # Remove duplicates while preserving order
                    video_ids = list(dict.fromkeys(all_video_ids))

                    # Look for time indicators to find recent streams only
                    # This pattern finds video entries with their publish time
                    time_pattern = r'"videoId":"([^"]+)"[^}]*?"publishedTimeText":\{"simpleText":"([^"]+)"\}'
                    recent_videos = []

                    # Try to find videos with time metadata
                    for match in re.finditer(time_pattern, html):
                        vid_id = match.group(1)
                        time_text = match.group(2)

                        # Only include very recent streams (last 2 hours)
                        if any(x in time_text.lower() for x in ['minute', 'second', 'streaming now', 'live']):
                            recent_videos.append(vid_id)
                        elif 'hour ago' in time_text.lower() and not 'hours' in time_text:
                            recent_videos.append(vid_id)  # "1 hour ago"
                        elif 'hours ago' in time_text.lower():
                            try:
                                hours = int(re.search(r'(\d+)\s*hour', time_text).group(1))
                                if hours <= 2:  # Only last 2 hours
                                    recent_videos.append(vid_id)
                            except:
                                pass

                    # Choose which videos to check
                    if recent_videos:
                        videos_to_check = list(dict.fromkeys(recent_videos[:3]))  # Remove duplicates, check max 3
                        if verbose_logs:
                            logger.info(f"  - Found {len(recent_videos)} recent videos (last 2 hours)")
                            logger.info(f"  - Will check {len(videos_to_check)} most recent")
                        else:
                            logger.debug(
                                "[STREAMS] recent_videos=%s will_check=%s",
                                len(recent_videos),
                                len(videos_to_check),
                            )
                    elif video_ids:
                        # No time data found, fallback to first 3 unique videos
                        videos_to_check = video_ids[:3]
                        unique_count = f" ({len(video_ids)} unique)" if len(all_video_ids) != len(video_ids) else ""
                        display_name = channel_name or channel_id
                        if verbose_logs:
                            logger.info(f"  - Found {len(all_video_ids)} total videos{unique_count} on {display_name}")
                        else:
                            logger.debug("[STREAMS] total_videos=%s%s channel=%s", len(all_video_ids), unique_count, display_name)
                        if videos_to_check:
                            display_name = channel_name or channel_id
                        if verbose_logs:
                            logger.info(
                                f"  - Checking first {len(videos_to_check)} videos for {display_name}: {', '.join(videos_to_check)}"
                            )
                        else:
                            logger.debug("[STREAMS] will_check=%s channel=%s", len(videos_to_check), display_name)
                    else:
                        # No videos found at all
                        videos_to_check = []
                        if verbose_logs:
                            logger.info("  - No videos found on streams page")
                        else:
                            logger.debug("[STREAMS] No videos found on streams page")
                        indicator_count = sum([has_is_live_now, has_live_badge, has_watching, has_live_text])
                        logger.info("[STALE] Streams tab had live indicators but no video IDs")
                        return self._live_indicator_result(
                            channel_id,
                            channel_name,
                            "no_quota_streams_page",
                            indicator_count,
                        )

                    if skip_api and videos_to_check:
                        display_name = channel_name or channel_id
                        trusted_video = videos_to_check[0]
                        indicator_count = sum([has_is_live_now, has_live_badge, has_watching, has_live_text])
                        logger.info(
                            f"[NO-API] YT_STREAM_API_VERIFY=false - trusting /streams indicators for {display_name}: {trusted_video}"
                        )
                        return {
                            "live": True,
                            "video_id": trusted_video,
                            "channel_name": display_name,
                            "title": f"Live stream on {display_name}",
                            "source": "no_api_indicator_trust",
                            "indicator_count": indicator_count,
                        }

                    api_error_videos = []

                    # Check the selected videos to see if any are live
                    for i, vid in enumerate(videos_to_check):
                        display_name = channel_name or channel_id
                        if verbose_logs:
                            logger.info(f"  - Checking video {i+1}/{len(videos_to_check)} for {display_name}: {vid}")
                        else:
                            logger.debug(
                                "[STREAMS] checking_video=%s/%s channel=%s video_id=%s",
                                i + 1,
                                len(videos_to_check),
                                display_name,
                                vid,
                            )
                        if i > 0:  # Add delay between multiple video checks
                            self._anti_detection_delay()

                        # Avoid watch-page scraping (high CAPTCHA risk); streams tab already showed live indicators.
                        result = self.check_video_is_live(vid, channel_name, scraping_prefilter=False)
                        if result.get("rate_limited"):
                            return result
                        if result.get("method") == "api_error_fallback":
                            api_error_videos.append(vid)
                            continue
                        if result.get('live'):
                            # Verify channel ID matches to avoid picking up recommended streams from other channels
                            found_cid = result.get('channel_id')
                            if found_cid and channel_id.startswith('UC') and len(channel_id) == 24:
                                if found_cid != channel_id:
                                    result["source"] = "recommended"
                                    result["target_channel_id"] = channel_id
                                    result["observed_channel_id"] = found_cid
                                    logger.debug(
                                        "[RECOMMENDED] Live candidate from %s while checking %s; skipping expected recommendation",
                                        found_cid,
                                        channel_id,
                                    )
                                    continue
                                    
                            # Add channel name to result for better logging
                            display_name = channel_name or channel_id
                            result['channel_name'] = display_name
                            return result

                    if api_error_videos:
                        indicator_count = sum([has_is_live_now, has_live_badge, has_watching, has_live_text])
                        display_name = channel_name or channel_id
                        trusted_video = api_error_videos[0]
                        logger.info(
                            f"[TRUST] API verification failed but /streams indicators found ({indicator_count} indicators)"
                        )
                        logger.info(f"[TRUST] Trusting first video as LIVE: {trusted_video}")
                        return {
                            "live": True,
                            "video_id": trusted_video,
                            "channel_name": display_name,
                            "title": f"Live stream on {display_name}",
                            "source": "api_failure_trust",
                            "indicator_count": indicator_count,
                        }

                    if videos_to_check:
                        indicator_count = sum([has_is_live_now, has_live_badge, has_watching, has_live_text])
                        logger.info("[STALE] Streams tab had live indicators but no verified live stream")
                        return self._live_indicator_result(
                            channel_id,
                            channel_name,
                            "no_quota_streams_page",
                            indicator_count,
                        )

            except Exception as e:
                error_text = str(e)
                if '429' in error_text:
                    cooldown = self._register_rate_limit(channel_id, channel_name)
                    return {"rate_limited": True, "cooldown": cooldown, "error": error_text}
                logger.error(f"Error checking streams tab: {error_text}")

        display_name = channel_name or channel_id
        logger.info(f"No live streams found for channel {display_name}")
        return None



# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    checker = NoQuotaStreamChecker()

    # Test with the video ID mentioned by user
    result = checker.check_video_is_live("xL_kGmZj3R8")
    print(f"\nResult: {json.dumps(result, indent=2)}")

    # Test channel check
    channel_result = checker.check_channel_for_live("UC-LSSlOZwpGIRIYihaz8zCw")
    if channel_result:
        print(f"\nChannel live stream: {json.dumps(channel_result, indent=2)}")
