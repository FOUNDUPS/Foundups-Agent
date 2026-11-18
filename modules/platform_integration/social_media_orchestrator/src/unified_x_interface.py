#!/usr/bin/env python3
"""
Unified X/Twitter Interface - WSP 3 Compliant Centralized X Posting
All X/Twitter posting through single MCP-based interface

WSP Compliance:
- WSP 3: Functional distribution through orchestrator
- WSP 17: Reusable pattern for platform posting
- WSP 84: Consolidates existing X/Twitter functionality
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
import json
import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

def _env_truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")

class XContentType(Enum):
    """Types of content that can be posted to X/Twitter"""
    STREAM_NOTIFICATION = "stream_notification"
    GIT_COMMIT = "git_commit"
    DEVELOPMENT_UPDATE = "development_update"
    GENERAL_POST = "general_post"

class XAccount(Enum):
    """Supported X/Twitter accounts"""
    FOUNDUPS = "foundups"
    MOVE2JAPAN = "move2japan"
    ANTIFAFM = "antifafm"

@dataclass
class XPostRequest:
    """Unified request structure for X/Twitter posting"""
    content: str
    content_type: XContentType
    account: XAccount = XAccount.FOUNDUPS
    duplicate_check_key: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class XPostResult:
    """Result from X/Twitter posting attempt"""
    success: bool
    message: str
    timestamp: datetime
    content_type: XContentType
    account: XAccount
    duplicate_prevented: bool = False

class UnifiedXInterface:
    """
    Centralized X/Twitter posting interface via MCP.

    All X/Twitter posting in the system must go through this interface
    to ensure proper coordination, duplicate prevention, and training data collection.
    """

    def __init__(self):
        self.posted_content = {}
        self.history_file = "memory/unified_x_history.json"
        self._history_loaded = False
        logger.info("[UNIFIED X] Interface initialized - All X posting via MCP")

    def _load_history(self):
        """Load posting history for duplicate prevention"""
        self._history_loaded = True
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding="utf-8") as f:
                    self.posted_content = json.load(f)
            else:
                self.posted_content = {}
        except Exception as e:
            logger.warning(f"[UNIFIED X] Could not load history: {e}")
            self.posted_content = {}

    def _save_history(self):
        """Save posting history"""
        try:
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, 'w', encoding="utf-8") as f:
                json.dump(self.posted_content, f, indent=2)
        except Exception as e:
            logger.error(f"[UNIFIED X] Could not save history: {e}")

    def _post_direct_via_selenium(self, request: XPostRequest) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Fallback posting without MCP (direct Selenium)."""
        if request.account not in (XAccount.FOUNDUPS, XAccount.MOVE2JAPAN):
            return False, None, "Account requires the verified API route"
        try:
            from modules.platform_integration.x_twitter.src.x_anti_detection_poster import AntiDetectionX
            from modules.platform_integration.social_media_orchestrator.src.gemini_vision_analyzer import GeminiVisionAnalyzer

            poster = AntiDetectionX(use_foundups=(request.account == XAccount.FOUNDUPS))
            poster.setup_driver(use_existing_session=True)

            gemini_analysis = None
            if _env_truthy("FOUNDUPS_CAPTURE_SCREENSHOT", "true"):
                screenshot = poster.driver.get_screenshot_as_png()
                gemini = GeminiVisionAnalyzer(api_key=os.getenv('GOOGLE_AISTUDIO_API_KEY'))
                gemini_analysis = gemini.analyze_posting_ui(screenshot)

            success = poster.post_to_x(content=request.content)
            return success, gemini_analysis, None
        except Exception as e:
            return False, None, str(e)

    def check_duplicate(self, request: XPostRequest) -> bool:
        """Check if content would be a duplicate post"""
        if not request.duplicate_check_key:
            return False
        if not self._history_loaded:
            self._load_history()

        duplicate_key = f"{request.content_type.value}_{request.duplicate_check_key}"

        if duplicate_key in self.posted_content:
            logger.info(f"[UNIFIED X] Duplicate detected: {duplicate_key}")
            return True

        return False

    def mark_as_posted(self, request: XPostRequest, success: bool = True):
        """Mark content as posted to prevent future duplicates"""
        if request.duplicate_check_key:
            if not self._history_loaded:
                self._load_history()
            duplicate_key = f"{request.content_type.value}_{request.duplicate_check_key}"
            self.posted_content[duplicate_key] = {
                'timestamp': datetime.now().isoformat(),
                'content_type': request.content_type.value,
                'account': request.account.value,
                'success': success,
                'content_length': len(request.content)
            }
            self._save_history()
            logger.info(f"[UNIFIED X] Marked as posted: {duplicate_key}")

    async def post_to_x(self, request: XPostRequest) -> XPostResult:
        """
        Post content to X/Twitter via MCP with unified coordination.

        Args:
            request: X/Twitter post request

        Returns:
            Result of posting attempt
        """

        if request.account not in (XAccount.FOUNDUPS, XAccount.MOVE2JAPAN):
            return XPostResult(
                success=False, message="Account requires the verified API route",
                timestamp=datetime.now(), content_type=request.content_type,
                account=request.account,
            )

        # Step 1: Duplicate check
        if self.check_duplicate(request):
            logger.info(f"[UNIFIED X] Skipping duplicate post")
            return XPostResult(
                success=False,
                message="Content already posted (duplicate prevented)",
                timestamp=datetime.now(),
                content_type=request.content_type,
                account=request.account,
                duplicate_prevented=True
            )

        # Step 2: Validate content length (280 char limit)
        if len(request.content) > 280:
            return XPostResult(
                success=False,
                message=f"Content too long ({len(request.content)} chars, max 280)",
                timestamp=datetime.now(),
                content_type=request.content_type,
                account=request.account
            )

        # Step 3: Post via MCP FastMCP HoloIndex Server
        logger.info("="*60)
        logger.info(f"[UNIFIED X] POSTING {request.content_type.value.upper()}")
        logger.info(f"[UNIFIED X] Account: @{request.account.value}")
        logger.info(f"[UNIFIED X] Content: {len(request.content)} chars")
        logger.info("="*60)

        success = False
        error_message = None

        # Post via MCP - handles Selenium + Gemini Vision + Training Data
        try:
            import random
            from holo_index.mcp_client.holo_mcp_client import HoloIndexMCPClient

            logger.info("[UNIFIED X] Using MCP FastMCP HoloIndex Server for posting")

            # ANTI-DETECTION: Random delay before posting (2-5 seconds)
            # Mimics human reading/reviewing tweet before posting
            pre_post_delay = random.uniform(2.0, 5.0)
            logger.info(f"[ANTI-DETECTION] Waiting {pre_post_delay:.1f}s before posting (human-like behavior)")
            await asyncio.sleep(pre_post_delay)

            mcp_client = HoloIndexMCPClient()

            # Call MCP tool: post_to_x_via_selenium
            # This automatically:
            # 1. Uses Selenium browser automation (no $100/month API)
            # 2. Captures screenshot and analyzes with Gemini Vision
            # 3. Saves training pattern to holo_index/training/selenium_patterns.json
            result = await mcp_client.call_tool(
                "post_to_x_via_selenium",
                content=request.content,
                account=request.account.value,
                capture_screenshot=True  # Enable Gemini Vision analysis
            )

            # ANTI-DETECTION: Random delay after posting (1-3 seconds)
            # Mimics human verifying tweet posted successfully
            post_post_delay = random.uniform(1.0, 3.0)
            logger.info(f"[ANTI-DETECTION] Waiting {post_post_delay:.1f}s after posting (human-like verification)")
            await asyncio.sleep(post_post_delay)

            success = result.get("success", False)
            error_message = result.get("error", None) if not success else None

            if success:
                logger.info(f"[UNIFIED X] [OK] MCP post successful to @{request.account.value}")
                logger.info(f"[UNIFIED X] Training pattern saved: {result.get('training_pattern_id')}")

                # Log Gemini Vision analysis if available
                gemini_analysis = result.get("gemini_analysis")
                if gemini_analysis:
                    logger.info(f"[UNIFIED X] Gemini Vision UI analysis: {gemini_analysis.get('ui_state', 'N/A')}")
            else:
                error_message = error_message or "MCP posting failed"
                logger.warning(f"[UNIFIED X] [FAIL] MCP post failed: {error_message}")

        except Exception as e:
            error_message = str(e)
            logger.error(f"[UNIFIED X] Exception during MCP posting: {e}")

        if not success and _env_truthy("FOUNDUPS_SOCIAL_POST_FALLBACK", "true"):
            logger.warning("[UNIFIED X] MCP failed - attempting direct Selenium fallback")
            direct_success, gemini_analysis, direct_error = self._post_direct_via_selenium(request)
            if direct_success:
                success = True
                error_message = None
                logger.info(f"[UNIFIED X] [OK] Direct Selenium post successful to @{request.account.value}")
                if gemini_analysis:
                    logger.info(f"[UNIFIED X] Gemini Vision UI analysis: {gemini_analysis.get('ui_state', 'N/A')}")
            else:
                error_message = direct_error or error_message or "Direct Selenium posting failed"
                logger.warning(f"[UNIFIED X] [FAIL] Direct Selenium fallback failed: {error_message}")

        # Step 4: Update tracking and return result
        if success:
            self.mark_as_posted(request, success=True)

        return XPostResult(
            success=success,
            message=error_message or "Posted successfully",
            timestamp=datetime.now(),
            content_type=request.content_type,
            account=request.account
        )

    async def post_verified_x(self, content: str, account: XAccount,
                              campaign_id: str, job_id: str, *, client,
                              expected_user_id: str, db_path,
                              dry_run: bool = True) -> Dict[str, Any]:
        """Publish through the API with a bound account and durable readback.

        Dry-run validates inputs only: no client calls, imports of publishers,
        history access, or database writes. Legacy transport is never a fallback.
        """
        result = dict(success=False, status="rejected", dry_run=dry_run is True,
                      account=account.value if isinstance(account, XAccount) else None,
                      provider_user_id=None, post_id=None, post_url=None, error=None)
        if not isinstance(account, XAccount):
            result["error"] = "invalid_account"
        elif type(dry_run) is not bool:
            result["error"] = "invalid_dry_run"
        elif not isinstance(expected_user_id, str) or not re.fullmatch(r"[1-9][0-9]{0,19}", expected_user_id):
            result["error"] = "invalid_expected_user_id"
        elif not isinstance(content, str) or not content.strip() or len(content) > 280 or "\x00" in content:
            result["error"] = "invalid_content"
        elif any(not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", v)
                 for v in (campaign_id, job_id)):
            result["error"] = "invalid_job_identity"
        elif dry_run:
            result.update(success=True, status="dry_run")
        elif client is None:
            result["error"] = "live_client_required"
        else:
            try:
                from modules.platform_integration.x_twitter.src.verified_x_publisher import publish_verified_x
            except Exception:
                result["error"] = "publisher_unavailable"
                return result
            return await publish_verified_x(
                content, account.value, campaign_id, job_id, client=client,
                expected_user_id=expected_user_id, db_path=db_path,
            )
        return result

    def get_posting_statistics(self) -> Dict[str, Any]:
        """Get statistics about X/Twitter posting activity"""
        if not self._history_loaded:
            self._load_history()
        stats = {
            'total_posts': len(self.posted_content),
            'by_content_type': {},
            'by_account': {},
            'recent_posts': []
        }

        for key, data in self.posted_content.items():
            content_type = data.get('content_type', 'unknown')
            account = data.get('account', 'unknown')

            stats['by_content_type'][content_type] = stats['by_content_type'].get(content_type, 0) + 1
            stats['by_account'][account] = stats['by_account'].get(account, 0) + 1

            if len(stats['recent_posts']) < 10:
                stats['recent_posts'].append({
                    'key': key,
                    'timestamp': data.get('timestamp'),
                    'content_type': content_type
                })

        return stats

# Singleton instance
unified_x = UnifiedXInterface()

# Convenience functions
async def post_verified_x(content: str, account: XAccount, campaign_id: str,
                          job_id: str, *, client, expected_user_id: str,
                          db_path, dry_run: bool = True) -> Dict[str, Any]:
    """Use the canonical interface for a verified API publication."""
    return await unified_x.post_verified_x(
        content, account, campaign_id, job_id, client=client,
        expected_user_id=expected_user_id, db_path=db_path, dry_run=dry_run,
    )


async def post_stream_notification_x(stream_title: str, stream_url: str, video_id: str,
                                    account: XAccount = XAccount.FOUNDUPS) -> XPostResult:
    """Post stream notification to X/Twitter (280 char limit)"""
    # Ultra-condensed for Twitter
    content = f"[U+1F534] LIVE: {stream_title[:50]}\n\n{stream_url}\n\n#LiveStream"

    # Enforce 280 char limit
    if len(content) > 280:
        content = f"[U+1F534] LIVE\n\n{stream_url}\n\n#LiveStream"

    request = XPostRequest(
        content=content,
        content_type=XContentType.STREAM_NOTIFICATION,
        account=account,
        duplicate_check_key=video_id
    )

    return await unified_x.post_to_x(request)

async def post_git_commits_x(commit_msg: str, commit_hash: str, file_count: int) -> XPostResult:
    """Post git commit to X/Twitter (ultra-condensed)"""
    short_msg = commit_msg[:60] + "..." if len(commit_msg) > 60 else commit_msg
    content = f"0102: {short_msg}\n\n{file_count} files updated\n\nhttps://github.com/FOUNDUPS/Foundups-Agent\n\n#0102"

    # Enforce 280 char limit
    if len(content) > 280:
        content = f"0102: {file_count} files\n\n{commit_msg[:50]}\n\nhttps://github.com/FOUNDUPS/Foundups-Agent\n\n#0102"

    request = XPostRequest(
        content=content,
        content_type=XContentType.GIT_COMMIT,
        account=XAccount.FOUNDUPS,
        duplicate_check_key=commit_hash
    )

    return await unified_x.post_to_x(request)

async def post_general_x(content: str, account: XAccount = XAccount.FOUNDUPS,
                        duplicate_key: Optional[str] = None) -> XPostResult:
    """Post general content to X/Twitter"""
    request = XPostRequest(
        content=content,
        content_type=XContentType.GENERAL_POST,
        account=account,
        duplicate_check_key=duplicate_key
    )

    return await unified_x.post_to_x(request)

if __name__ == "__main__":
    async def test_unified_x():
        """Test the unified X interface"""
        print("="*80)
        print("TESTING UNIFIED X INTERFACE")
        print("="*80)

        # Test posting
        result = await post_stream_notification_x(
            "Test Stream",
            "https://www.youtube.com/watch?v=TEST123",
            "TEST123"
        )
        print(f"Post result: {result.success} - {result.message}")

        # Test duplicate
        result2 = await post_stream_notification_x(
            "Test Stream",
            "https://www.youtube.com/watch?v=TEST123",
            "TEST123"
        )
        print(f"Duplicate result: {result2.success} - {result2.duplicate_prevented}")

        # Show stats
        stats = unified_x.get_posting_statistics()
        print(f"\nStats: {stats}")

    asyncio.run(test_unified_x())
