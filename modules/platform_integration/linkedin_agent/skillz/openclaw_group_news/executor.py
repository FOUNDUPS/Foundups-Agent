#!/usr/bin/env python3
"""
OpenClaw Group News Poster - Executor

Posts OpenClaw news to LinkedIn Group 6729915.
Runs BEFORE comment engagement in the LinkedIn automation flow.

WSP References:
- WSP 78: Database logging to agents_social_posts
- WSP 42: LinkedIn platform integration
- WSP 96: WRE Skills protocol
"""

import os
import sys
import time
import random
import sqlite3
import hashlib
import logging
import re
import uuid
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

logger = logging.getLogger(__name__)

# UI-TARS agentic visual confirmation (optional - falls back to timing if unavailable)
UI_TARS_AVAILABLE = False
try:
    from modules.infrastructure.foundups_vision.src.ui_tars_bridge import UITarsBridge
    UI_TARS_AVAILABLE = True
except ImportError:
    pass

# Qwen3 AI-powered profile evaluation (replaces hardcoded rules)
QWEN3_AVAILABLE = False
try:
    from modules.platform_integration.linkedin_agent.src.qwen_profile_evaluator import (
        evaluate_profile_with_qwen,
        ProfileDecision,
        ProfileEvaluation,
    )
    QWEN3_AVAILABLE = True
    logger.info("[QWEN3] Profile evaluator available")
except ImportError:
    logger.info("[QWEN3] Profile evaluator not available - using fallback rules")

# Constants
LINKEDIN_GROUP_ID = "6729915"
LINKEDIN_GROUP_URL = f"https://www.linkedin.com/groups/{LINKEDIN_GROUP_ID}/"
LINKEDIN_GROUP_MEMBERSHIP_URL = (
    f"https://www.linkedin.com/groups/{LINKEDIN_GROUP_ID}/manage/membership/requested/"
)
MAX_POSTS_PER_DAY = 3
MIN_POST_INTERVAL_HOURS = 4
RELEVANCE_THRESHOLD = 0.6
POLICY_RELEVANCE_THRESHOLD = 0.55
DUPLICATE_CHECK_DAYS = 7
SEARCH_PROVIDER = "duckduckgo"

OPENCLAW_ECOSYSTEM_TERMS: Tuple[str, ...] = (
    "openclaw",
    "ironclaw",
    "lobster.cash",
    "lobster cash",
    "crossmint",
    "peeka",
)
MAJOR_AI_NEWS_TERMS: Tuple[str, ...] = (
    "openai",
    "anthropic",
    "claude",
    "google deepmind",
    "google ai",
    "gemini",
    "meta ai",
    "llama",
    "mistral",
    "xai",
    "grok",
)
UPDATE_SIGNAL_TERMS: Tuple[str, ...] = (
    "security",
    "vulnerability",
    "cve",
    "patch",
    "fix",
    "fixed",
    "release notes",
    "changelog",
    "update",
    "updated",
    "upgrade",
    "breaking change",
    "deprecation",
    "deprecated",
    "incident",
    "outage",
    "api change",
    "rollout",
    "announced",
    "launch",
    "released",
)


@dataclass
class NewsItem:
    """News item from search results."""
    title: str
    url: str
    source: str
    published_date: Optional[datetime] = None
    summary: Optional[str] = None

    def content_hash(self) -> str:
        """Generate hash for duplicate detection."""
        return hashlib.sha256(self.url.encode()).hexdigest()[:16]


class NewsRelevanceRater:
    """
    Simple 4-dimension news relevance scoring.
    Lighter than WSP 15 MPS - focused on news posting.
    """

    # Source authority tiers
    AUTHORITY_TIERS = {
        "high": ["techcrunch", "wired", "theverge", "arstechnica", "venturebeat",
                 "reuters", "bloomberg", "wsj", "nytimes", "forbes",
                 "arxiv", "acm.org", "ieee.org", "scholar.google", "nature.com", "science.org"],
        "medium": ["medium", "dev.to", "hackernews", "reddit", "substack", "github",
                   "researchgate", "semanticscholar", "paperswithcode"],
        "low": []  # Default for unknown sources
    }

    @staticmethod
    def rate(item: NewsItem) -> float:
        """
        Rate news relevance (0.0-1.0).

        Dimensions (weights):
        - Recency (0.3): How recent is the article?
        - Authority (0.2): Source credibility
        - Relevance (0.4): OpenClaw mention strength
        - Engagement (0.1): Breaking news potential
        """
        recency = NewsRelevanceRater._score_recency(item.published_date)
        authority = NewsRelevanceRater._score_authority(item.source)
        relevance = NewsRelevanceRater._score_relevance(item.title, item.summary)
        engagement = NewsRelevanceRater._score_engagement(item.title)

        score = (recency * 0.3) + (authority * 0.2) + (relevance * 0.4) + (engagement * 0.1)

        logger.debug(f"[NEWS_RATE] {item.title[:50]}... "
                    f"recency={recency:.2f} auth={authority:.2f} "
                    f"rel={relevance:.2f} eng={engagement:.2f} -> {score:.2f}")

        return round(score, 3)

    @staticmethod
    def _score_recency(pub_date: Optional[datetime]) -> float:
        """Score based on publication date."""
        if not pub_date:
            return 0.3  # Unknown date - assume moderately old

        age = datetime.now() - pub_date
        if age < timedelta(hours=24):
            return 1.0
        elif age < timedelta(days=3):
            return 0.7
        elif age < timedelta(days=7):
            return 0.5
        else:
            return 0.2

    @staticmethod
    def _score_authority(source: str) -> float:
        """Score based on source credibility."""
        source_lower = source.lower()

        for tier, sources in NewsRelevanceRater.AUTHORITY_TIERS.items():
            for s in sources:
                if s in source_lower:
                    if tier == "high":
                        return 1.0
                    elif tier == "medium":
                        return 0.6

        return 0.3  # Unknown source

    @staticmethod
    def _score_relevance(title: str, summary: Optional[str]) -> float:
        """Score based on OpenClaw mention strength."""
        text = f"{title} {summary or ''}".lower()
        has_update_signal = any(term in text for term in UPDATE_SIGNAL_TERMS)

        # Direct ecosystem mention with update/security context
        if any(term in text for term in OPENCLAW_ECOSYSTEM_TERMS) and has_update_signal:
            return 1.0

        # OpenClaw ecosystem terms (high relevance)
        if any(term in text for term in OPENCLAW_ECOSYSTEM_TERMS):
            return 0.85

        # Major AI ecosystem updates that impact agent workflows
        if any(term in text for term in MAJOR_AI_NEWS_TERMS) and has_update_signal:
            return 0.75

        # AI agent framework terms (medium-high relevance)
        agent_terms = ["ai agent framework", "autonomous agent", "llm agent",
                      "agent orchestration", "ai orchestration", "multi-agent"]
        if any(term in text for term in agent_terms):
            return 0.8

        # General related terms
        related_terms = ["open source ai", "ai agents", "agent framework",
                        "autonomous agents", "llm agents", "ai assistant framework"]
        matches = sum(1 for term in related_terms if term in text)

        if matches >= 2:
            return 0.7
        elif matches == 1:
            return 0.5

        return 0.2

    @staticmethod
    def _score_engagement(title: str) -> float:
        """Score based on engagement potential."""
        title_lower = title.lower()
        if any(word in title_lower for word in ("security", "patch", "fix", "cve", "deprecation")):
            return 1.0

        # Breaking news indicators
        if any(word in title_lower for word in ["launch", "release", "announce", "join", "partner"]):
            return 1.0

        # Update indicators
        if any(word in title_lower for word in ["update", "new", "add", "improve"]):
            return 0.6

        return 0.3


class OpenClawGroupPoster:
    """
    Posts news to LinkedIn OpenClaw Group.
    Uses anti-detection patterns from foundups_selenium.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize poster with database connection.

        Args:
            db_path: Path to unified database (WSP 78).
                     Default: modules/infrastructure/database/data/foundups.db
        """
        self.db_path = db_path or self._get_default_db_path()
        self._init_db()
        self.driver = None

    def _get_default_db_path(self) -> str:
        """Get default database path per WSP 78."""
        base = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
        return os.path.join(base, "modules", "infrastructure", "database", "data", "foundups.db")

    def _init_db(self) -> None:
        """Initialize agents_social_posts table."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents_social_posts (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                group_id TEXT,
                content TEXT NOT NULL,
                source_url TEXT,
                content_hash TEXT,
                relevance_score REAL,
                posted_at TIMESTAMP,
                post_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_posts_platform ON agents_social_posts(platform)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_posts_hash ON agents_social_posts(content_hash)")

        conn.commit()
        conn.close()
        logger.info(f"[DB] agents_social_posts table initialized: {self.db_path}")

    def can_post_today(self) -> Tuple[bool, str]:
        """
        Check if posting is allowed based on rate limits.

        Returns:
            Tuple of (allowed, reason)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check daily limit
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT COUNT(*) FROM agents_social_posts
            WHERE platform = 'linkedin'
            AND group_id = ?
            AND date(posted_at) = ?
            AND post_status = 'posted'
        """, (LINKEDIN_GROUP_ID, today))

        daily_count = cursor.fetchone()[0]
        if daily_count >= MAX_POSTS_PER_DAY:
            conn.close()
            return False, f"Daily limit reached ({daily_count}/{MAX_POSTS_PER_DAY})"

        # Check minimum interval
        cursor.execute("""
            SELECT posted_at FROM agents_social_posts
            WHERE platform = 'linkedin'
            AND group_id = ?
            AND post_status = 'posted'
            ORDER BY posted_at DESC LIMIT 1
        """, (LINKEDIN_GROUP_ID,))

        last_post = cursor.fetchone()
        conn.close()

        if last_post:
            last_time = datetime.fromisoformat(last_post[0])
            hours_since = (datetime.now() - last_time).total_seconds() / 3600
            if hours_since < MIN_POST_INTERVAL_HOURS:
                return False, f"Too soon since last post ({hours_since:.1f}h < {MIN_POST_INTERVAL_HOURS}h)"

        return True, f"OK ({daily_count}/{MAX_POSTS_PER_DAY} today)"

    def is_duplicate(self, item: NewsItem) -> bool:
        """Check if URL was posted recently (only counts actual posts, not dry runs)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(days=DUPLICATE_CHECK_DAYS)).isoformat()
        cursor.execute("""
            SELECT id FROM agents_social_posts
            WHERE content_hash = ?
            AND created_at > ?
            AND post_status = 'posted'
        """, (item.content_hash(), cutoff))

        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def format_post(self, item: NewsItem, extra_comment: str = "") -> str:
        """Format news item as LinkedIn post."""
        parts = [item.title]

        if item.summary:
            # Truncate summary if too long
            summary = item.summary[:500] + "..." if len(item.summary) > 500 else item.summary
            parts.append(f"\n\n{summary}")

        comment = (extra_comment or "").strip()
        if comment:
            parts.append(f"\n\n{comment}")

        parts.append(f"\n\nSource: {item.url}")
        parts.append("\n\n#OpenClaw #AI #Agents")

        return "".join(parts)

    def post_to_group(
        self,
        item: NewsItem,
        dry_run: bool = False,
        extra_comment: str = "",
    ) -> bool:
        """
        Post news item to LinkedIn group.

        Args:
            item: NewsItem to post
            dry_run: If True, log but don't actually post
            extra_comment: Optional custom line(s) to add to the post body

        Returns:
            True if successful (or dry_run), False otherwise
        """
        # Hard safety gate: never post video links to the group.
        if _looks_like_video_candidate(item.url, item.title, item.summary or ""):
            logger.warning(f"[POLICY] Rejecting video candidate for posting: {item.url}")
            return False

        # Check rate limits
        can_post, reason = self.can_post_today()
        if not can_post:
            logger.warning(f"[RATE_LIMIT] Cannot post: {reason}")
            return False

        # Check duplicate
        if self.is_duplicate(item):
            logger.info(f"[DUPLICATE] Already posted: {item.url}")
            return False

        # Generate post content
        content = self.format_post(item, extra_comment=extra_comment)
        score = NewsRelevanceRater.rate(item)

        # Generate post ID
        post_id = f"ln_grp_{LINKEDIN_GROUP_ID}_{item.content_hash()}_{int(time.time())}"

        if dry_run:
            logger.info(f"[DRY_RUN] Would post to group {LINKEDIN_GROUP_ID}:")
            logger.info(f"  Title: {item.title}")
            logger.info(f"  Score: {score:.2f}")
            logger.info(f"  Content:\n{content[:200]}...")

            # Still log to DB as 'dry_run' status
            self._log_post(post_id, content, item, score, status="dry_run")
            return True

        # Actual posting via Selenium
        try:
            success = self._selenium_post_to_group(content)
            status = "posted" if success else "failed"
            self._log_post(post_id, content, item, score, status=status)
            return success
        except Exception as e:
            logger.error(f"[POST_ERROR] {e}")
            self._log_post(post_id, content, item, score, status="error")
            return False

    def _log_post(self, post_id: str, content: str, item: NewsItem,
                  score: float, status: str) -> None:
        """Log post to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO agents_social_posts
            (id, platform, group_id, content, source_url, content_hash,
             relevance_score, posted_at, post_status)
            VALUES (?, 'linkedin', ?, ?, ?, ?, ?, datetime('now'), ?)
        """, (post_id, LINKEDIN_GROUP_ID, content, item.url,
              item.content_hash(), score, status))

        conn.commit()
        conn.close()
        logger.info(f"[DB] Logged post {post_id} with status={status}")

    async def _agentic_wait_for_element(
        self,
        driver: Any,
        element_description: str,
        max_attempts: int = 5,
        wait_between: float = 2.0
    ) -> bool:
        """
        Agentic visual confirmation that an element is visible using UI-TARS.

        Instead of fixed timing, the agent "sees" the browser and confirms readiness.
        Falls back to timing-based wait if UI-TARS is unavailable.

        Args:
            driver: Selenium WebDriver instance
            element_description: Human-readable description of element to find
            max_attempts: Maximum verification attempts
            wait_between: Seconds between attempts

        Returns:
            True if element visually confirmed, False otherwise
        """
        if not UI_TARS_AVAILABLE:
            logger.info(f"[AGENTIC] UI-TARS not available, using timing fallback for: {element_description}")
            time.sleep(wait_between * 2)  # Double wait as fallback
            return True

        try:
            bridge = UITarsBridge()
            await bridge.connect()

            for attempt in range(max_attempts):
                logger.info(f"[AGENTIC] Visual check {attempt + 1}/{max_attempts}: {element_description}")

                result = await bridge.execute_action(
                    action="verify",
                    description=element_description,
                    driver=driver,
                    timeout=30
                )

                if result.success:
                    logger.info(f"[AGENTIC] Element confirmed visible: {element_description} (confidence: {result.confidence:.2f})")
                    return True

                logger.info(f"[AGENTIC] Element not yet visible, waiting {wait_between}s...")
                await asyncio.sleep(wait_between)

            logger.warning(f"[AGENTIC] Element not found after {max_attempts} attempts: {element_description}")
            return False

        except Exception as e:
            logger.warning(f"[AGENTIC] Visual check failed, using timing fallback: {e}")
            time.sleep(wait_between * 2)
            return True

    def _selenium_post_to_group(self, content: str) -> bool:
        """
        Post to LinkedIn group using Selenium.
        Uses anti-detection patterns from foundups_selenium.
        AGENTIC: Uses UI-TARS visual confirmation instead of fixed timers.
        """
        try:
            from modules.platform_integration.linkedin_agent.src.anti_detection_poster import AntiDetectionLinkedIn

            poster = AntiDetectionLinkedIn()

            # Navigate to group (setup_driver per AntiDetectionLinkedIn API)
            if not poster.driver:
                poster.setup_driver(use_existing_session=True)

            # Maximize/focus window when reusing browser (fix for "move target out of bounds")
            try:
                poster.driver.maximize_window()
                poster.driver.switch_to.window(poster.driver.current_window_handle)
                logger.info("[BROWSER] Window maximized and focused")
            except Exception as e:
                logger.debug(f"[BROWSER] Window focus skipped: {e}")

            poster.driver.get(LINKEDIN_GROUP_URL)
            logger.info(f"[BROWSER] Navigating to {LINKEDIN_GROUP_URL}")

            # AGENTIC: Visual confirmation that page is ready
            # Instead of fixed delays, UI-TARS confirms the "Start a post" button is visible
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException

            def _safe_click(element: Any, label: str) -> None:
                """
                Resilient click helper for flaky viewport/layout conditions.

                Order:
                1) Human click (if available)
                2) Native Selenium click
                3) JavaScript click fallback
                """
                # Always attempt to center element first
                try:
                    poster.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                        element,
                    )
                    time.sleep(random.uniform(0.2, 0.5))
                except Exception:
                    pass

                # Prefer humanized click path first when available
                if hasattr(poster, "human") and poster.human:
                    try:
                        poster.human.human_click(element)
                        return
                    except Exception as exc:
                        logger.warning("[BROWSER] Human click failed for %s: %s", label, exc)

                try:
                    element.click()
                    return
                except Exception as exc:
                    logger.warning("[BROWSER] Native click failed for %s: %s", label, exc)

                try:
                    poster.driver.execute_script("arguments[0].click();", element)
                    return
                except Exception as exc:
                    raise RuntimeError(f"Could not click {label}: {exc}") from exc

            def _log_element_probe(element: Any, label: str) -> None:
                """Emit selector diagnostics so CLI logs prove what was clicked."""
                try:
                    rect = poster.driver.execute_script(
                        "const r = arguments[0].getBoundingClientRect();"
                        "return {top:r.top,left:r.left,width:r.width,height:r.height};",
                        element,
                    ) or {}
                except Exception:
                    rect = {}

                try:
                    text = (element.text or "").strip()
                except Exception:
                    text = ""
                try:
                    element_id = element.get_attribute("id") or ""
                except Exception:
                    element_id = ""
                try:
                    class_name = element.get_attribute("class") or ""
                except Exception:
                    class_name = ""

                logger.info(
                    "[BROWSER] %s matched | id=%s text=%s rect=%s class=%s",
                    label,
                    element_id,
                    text[:120],
                    rect,
                    class_name[:160],
                )

            def _find_start_post_button() -> Any:
                """
                Find the LinkedIn group post trigger with strict-first selector ordering.

                Priority:
                1) exact button text
                2) group-rail hare-box top-bar button
                3) legacy share-box selectors
                """
                selector_chain = [
                    (
                        "xpath_exact_text",
                        By.XPATH,
                        "//button[normalize-space()='Start a post in this group']",
                    ),
                    (
                        "css_hare_top_bar",
                        By.CSS_SELECTOR,
                        "div.hare-box-feed-entry__top-bar button.artdeco-button",
                    ),
                    (
                        "css_hare_container_button",
                        By.CSS_SELECTOR,
                        "div.hare-box-feed-entry button.artdeco-button",
                    ),
                    (
                        "css_legacy_share_box",
                        By.CSS_SELECTOR,
                        "button.share-box-feed-entry__trigger, button[class*='hare-box-feed-entry'], button[class*='share-box']",
                    ),
                ]

                last_err: Optional[Exception] = None
                for selector_name, by, locator in selector_chain:
                    try:
                        element = WebDriverWait(poster.driver, 8).until(
                            EC.element_to_be_clickable((by, locator))
                        )
                        _log_element_probe(element, f"Start post selector={selector_name}")
                        return element
                    except Exception as exc:
                        last_err = exc
                        logger.debug(
                            "[BROWSER] Start post selector miss: %s (%s)",
                            selector_name,
                            exc,
                        )

                raise TimeoutException(
                    f"Could not find clickable Start post button with any known selector: {last_err}"
                )

            # Phase 1: Wait for document.readyState
            WebDriverWait(poster.driver, 30).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            logger.info("[BROWSER] Document ready state complete")

            # Phase 2: AGENTIC visual confirmation
            if UI_TARS_AVAILABLE:
                logger.info("[AGENTIC] Using UI-TARS visual confirmation for page readiness")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    ready = loop.run_until_complete(
                        self._agentic_wait_for_element(
                            driver=poster.driver,
                            element_description="Start a post button or Share box on LinkedIn group page",
                            max_attempts=5,
                            wait_between=3.0
                        )
                    )
                    if not ready:
                        logger.warning("[AGENTIC] Could not confirm page readiness visually")
                finally:
                    loop.close()
            else:
                # Fallback: timing-based wait
                logger.info("[BROWSER] Using timing fallback (UI-TARS not available)")
                time.sleep(random.uniform(5, 8))

            # Click "Start a post in this group" (strict selector ordering + diagnostics)
            start_btn = _find_start_post_button()
            logger.info("[BROWSER] Start post button found")
            _safe_click(start_btn, "Start post")

            logger.info("[BROWSER] Clicked Start post button")
            time.sleep(random.uniform(1.5, 2.5))

            # Type content - wait for editor to be ready
            logger.info("[BROWSER] Waiting for post editor...")
            editor = WebDriverWait(poster.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    "div.ql-editor, div[contenteditable='true']"))
            )
            logger.info("[BROWSER] Editor found, typing content...")

            if hasattr(poster, 'human') and hasattr(poster.human, 'human_type'):
                poster.human.human_type(editor, content)
            elif hasattr(poster, 'human_type'):
                poster.human_type(editor, content)
            else:
                editor.send_keys(content)

            logger.info(f"[BROWSER] Content typed ({len(content)} chars)")
            time.sleep(random.uniform(2, 3))

            # Click Post - wait for button to be enabled
            logger.info("[BROWSER] Waiting for Post button...")
            post_btn = WebDriverWait(poster.driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,
                    "button.share-actions__primary-action, button[class*='primary-action']"))
            )

            logger.info("[BROWSER] Post button found, clicking...")
            _safe_click(post_btn, "Post button")

            logger.info("[BROWSER] Post button clicked, waiting for confirmation...")
            time.sleep(random.uniform(5, 8))  # Wait for post to complete

            logger.info(f"[POST] Successfully posted to group {LINKEDIN_GROUP_ID}")
            return True

        except Exception as e:
            logger.error(f"[SELENIUM] Post failed: {e}")
            import traceback
            logger.debug(f"[SELENIUM] Traceback: {traceback.format_exc()}")
            return False


@dataclass
class GroupMemberRequest:
    """Pending LinkedIn group membership request."""

    name: str
    headline: str = ""
    profile_url: str = ""
    image_url: str = ""
    language: str = "en"
    is_likely_human: bool = True
    classification_reason: str = "human_default"


class GroupLanguageDetector:
    """Best-effort language detection from member name/headline script."""

    _HANGUL = re.compile(r"[\uac00-\ud7af]")
    _HIRAGANA_KATAKANA = re.compile(r"[\u3040-\u30ff]")
    _CJK = re.compile(r"[\u4e00-\u9fff]")
    _CYRILLIC = re.compile(r"[\u0400-\u04ff]")
    _ARABIC = re.compile(r"[\u0600-\u06ff]")

    @classmethod
    def detect(cls, text: str) -> str:
        probe = (text or "").strip()
        if not probe:
            return "en"
        if cls._HANGUL.search(probe):
            return "ko"
        if cls._HIRAGANA_KATAKANA.search(probe):
            return "ja"
        if cls._CJK.search(probe):
            return "zh"
        if cls._CYRILLIC.search(probe):
            return "sr"
        if cls._ARABIC.search(probe):
            return "ar"
        return "en"


class WelcomeMessageComposer:
    """Localized welcome-message composer with optional IronClaw(Qwen) drafting."""

    DEFAULT_TEMPLATES: Dict[str, str] = {
        "en": (
            "welcome {name} - glad you joined.\n"
            "foundups is building on openclaw-like agents that do real work.\n"
            "quick context: foundups.com (litepaper)\n"
            "we are replacing roi with roc (return on compute)."
        ),
        "ko": (
            "{name}님, 그룹에 오신 것을 환영합니다.\n"
            "foundups는 실제 작업을 수행하는 openclaw 계열 에이전트 위에서 구축되고 있습니다.\n"
            "간단한 소개: foundups.com (litepaper)\n"
            "roi에서 roc(return on compute)로 전환합니다."
        ),
        "ja": (
            "{name}さん、グループへようこそ。\n"
            "foundupsは、実作業を行うopenclaw系エージェント上で構築されています。\n"
            "概要はこちら: foundups.com (litepaper)\n"
            "roiからroc(return on compute)へ移行します。"
        ),
        "zh": (
            "{name}，欢迎加入本群组。\n"
            "foundups 正在基于 openclaw 类代理构建，这些代理会执行真实工作。\n"
            "快速了解: foundups.com (litepaper)\n"
            "我们正在从 roi 转向 roc(return on compute)。"
        ),
        "sr": (
            "zdravo {name}, dobrodosli u grupu.\n"
            "foundups gradimo na openclaw-like agentima koji rade stvaran posao.\n"
            "kratko objasnjenje: foundups.com (litepaper)\n"
            "prelazimo sa roi na roc (return on compute)."
        ),
        "ar": (
            "مرحبا {name}، أهلا بك في المجموعة.\n"
            "نحن نبني foundups على وكلاء شبيهين بـ openclaw يقومون بعمل حقيقي.\n"
            "ملخص سريع: foundups.com (litepaper)\n"
            "ننتقل من roi إلى roc (return on compute)."
        ),
    }

    def __init__(
        self,
        prefer_ironclaw: Optional[bool] = None,
        ironclaw_model: Optional[str] = None,
    ):
        if prefer_ironclaw is None:
            prefer_ironclaw = os.getenv(
                "LINKEDIN_GROUP_WELCOME_USE_IRONCLAW", "1"
            ).strip().lower() in {"1", "true", "yes", "y", "on"}
        self.prefer_ironclaw = prefer_ironclaw
        self.ironclaw_model = (
            (ironclaw_model or "").strip()
            or os.getenv("LINKEDIN_GROUP_WELCOME_MODEL", "").strip()
            or "local/qwen3-4b"
        )

    def compose(self, member: GroupMemberRequest) -> str:
        lang = member.language if member.language in self.DEFAULT_TEMPLATES else "en"
        fallback = self.DEFAULT_TEMPLATES[lang].format(name=member.name or "there")

        if not self.prefer_ironclaw:
            return fallback

        generated = self._compose_with_ironclaw(member, fallback)
        if generated:
            return generated
        return fallback

    def _compose_with_ironclaw(
        self,
        member: GroupMemberRequest,
        fallback: str,
    ) -> Optional[str]:
        try:
            from modules.communication.moltbot_bridge.src.ironclaw_gateway_client import (
                IronClawGatewayClient,
            )
        except Exception:
            return None

        try:
            client = IronClawGatewayClient()
            system_prompt = (
                "You draft short LinkedIn group welcome messages.\n"
                "Rules:\n"
                "- keep to 3-5 lines\n"
                "- keep lowercase style\n"
                "- include foundups.com exactly once\n"
                "- mention roi -> roc in one short clause\n"
                "- no hashtags\n"
                "- no emojis"
            )
            user_prompt = (
                f"name={member.name}\n"
                f"headline={member.headline}\n"
                f"language={member.language}\n"
                f"fallback:\n{fallback}"
            )
            drafted = client.chat_completion(
                user_message=user_prompt,
                system_prompt=system_prompt,
                max_tokens=180,
                temperature=0.4,
                model=self.ironclaw_model,
            )
            if drafted:
                drafted = drafted.strip()
                if "foundups.com" not in drafted.lower():
                    return None
                return drafted
            return None
        except Exception:
            return None


class OpenClawGroupMembershipDAE:
    """Process LinkedIn group membership requests: message + approve."""

    NON_HUMAN_NAME_KEYWORDS: Tuple[str, ...] = (
        "official",
        "media",
        "news",
        "channel",
        "support",
        "team",
        "company",
        "page",
        "group",
        "studio",
        "topvn",
    )
    NON_HUMAN_HEADLINE_KEYWORDS: Tuple[str, ...] = (
        "official account",
        "company page",
        "brand page",
        "business page",
        "media page",
        "news page",
        "customer support",
        "channel manager",
    )

    MESSAGE_MENU_KEYWORDS: Tuple[str, ...] = (
        "message",
        "메시지",
        "mensaje",
        "mensagem",
        "nachricht",
        "messaggio",
        "メッセージ",
        "сообщение",
        "رسالة",
    )

    def __init__(
        self,
        db_path: Optional[str] = None,
        group_id: str = LINKEDIN_GROUP_ID,
    ):
        self.group_id = group_id
        self.group_membership_url = (
            f"https://www.linkedin.com/groups/{self.group_id}/manage/membership/requested/"
        )
        self.db_path = db_path or self._get_default_db_path()
        self.message_composer = WelcomeMessageComposer()
        self.deny_non_human = os.getenv(
            "LINKEDIN_GROUP_DENY_NON_HUMAN", "1"
        ).strip().lower() in {"1", "true", "yes", "y", "on"}
        self.non_human_message = (
            os.getenv(
                "LINKEDIN_GROUP_NON_HUMAN_MESSAGE",
                "sorry only for human accounts.",
            ).strip()
            or "sorry only for human accounts."
        )
        self._init_db()

    def _get_default_db_path(self) -> str:
        base = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
        return os.path.join(base, "modules", "infrastructure", "database", "data", "foundups.db")

    def _init_db(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agents_social_group_actions (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                group_id TEXT NOT NULL,
                member_name TEXT,
                member_profile_url TEXT,
                detected_language TEXT,
                action_type TEXT NOT NULL,
                action_status TEXT NOT NULL,
                message_preview TEXT,
                screenshot_path TEXT,
                error_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_group_actions_group_time "
            "ON agents_social_group_actions(group_id, created_at)"
        )
        conn.commit()
        conn.close()

    def _log_action(
        self,
        member: Optional[GroupMemberRequest],
        action_type: str,
        action_status: str,
        message_preview: Optional[str] = None,
        screenshot_path: Optional[str] = None,
        error_text: Optional[str] = None,
    ) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO agents_social_group_actions (
                id, platform, group_id, member_name, member_profile_url,
                detected_language, action_type, action_status,
                message_preview, screenshot_path, error_text
            ) VALUES (?, 'linkedin', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"ln_grp_act_{uuid.uuid4().hex[:18]}",
                self.group_id,
                member.name if member else "",
                member.profile_url if member else "",
                member.language if member else "",
                action_type,
                action_status,
                message_preview,
                screenshot_path,
                error_text,
            ),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def parse_member_name_from_approve_label(label: str) -> str:
        text = (label or "").strip()
        if not text:
            return ""
        # Examples:
        # - "Approve request for Dejan Djokic"
        # - "Approve 박동환"
        patterns = (
            r"for\s+(.+)$",
            r"approve\s+(.+)$",
        )
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return text

    def _capture_screenshot(self, driver: Any, screenshot_dir: Optional[str], prefix: str) -> Optional[str]:
        if not screenshot_dir:
            return None
        try:
            out_dir = Path(screenshot_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"{prefix}_{int(time.time() * 1000)}.png"
            driver.save_screenshot(str(path))
            return str(path)
        except Exception:
            return None

    def _find_request_rows(self, driver: Any) -> List[Any]:
        from selenium.webdriver.common.by import By

        selectors = [
            "//li[contains(@class,'artdeco-list__item')][.//button[contains(@class,'groups-manage-group-admin-actions__primary-action')]]",
            "//li[contains(@class,'artdeco-list__item')][.//button[contains(@aria-label,'Approve')]]",
            "//li[contains(@class,'artdeco-list__item')][.//button[normalize-space()='Approve']]",
        ]
        for selector in selectors:
            rows = driver.find_elements(By.XPATH, selector)
            if rows:
                return rows
        return []

    def _extract_member_request(self, row: Any) -> GroupMemberRequest:
        from selenium.webdriver.common.by import By

        def _first_text(xpaths: List[str]) -> str:
            for xp in xpaths:
                try:
                    el = row.find_element(By.XPATH, xp)
                    text = (el.text or "").strip()
                    if text:
                        return text
                except Exception:
                    continue
            return ""

        name = _first_text(
            [
                ".//*[contains(@class,'entity-action-title')]",
                ".//*[contains(@class,'artdeco-entity-lockup__title')]",
            ]
        )
        headline = _first_text(
            [
                ".//*[contains(@class,'artdeco-entity-lockup__subtitle')]",
                ".//*[contains(@class,'t-14') and not(contains(@class,'entity-action-title'))]",
            ]
        )

        profile_url = ""
        image_url = ""
        try:
            profile = row.find_element(By.XPATH, ".//a[contains(@href, '/in/') or contains(@href, 'linkedin.com')]")
            profile_url = (profile.get_attribute("href") or "").strip()
        except Exception:
            pass

        try:
            image = row.find_element(By.XPATH, ".//img[contains(@class,'presence-entity__image')]")
            image_url = (image.get_attribute("src") or "").strip()
        except Exception:
            pass

        if not name:
            try:
                approve_btn = row.find_element(
                    By.XPATH,
                    ".//button[contains(@class,'groups-manage-group-admin-actions__primary-action') or contains(@aria-label,'Approve')]",
                )
                label = approve_btn.get_attribute("aria-label") or ""
                name = self.parse_member_name_from_approve_label(label)
            except Exception:
                name = "unknown member"

        language = GroupLanguageDetector.detect(f"{name} {headline}")
        member = GroupMemberRequest(
            name=name,
            headline=headline,
            profile_url=profile_url,
            image_url=image_url,
            language=language,
        )
        is_human, reason = self._classify_member_account(member)
        member.is_likely_human = is_human
        member.classification_reason = reason
        return member

    @classmethod
    def _classify_member_account(cls, member: GroupMemberRequest) -> Tuple[bool, str]:
        """
        Heuristic classification for person vs non-human/brand membership requests.
        """
        name = (member.name or "").strip().lower()
        headline = (member.headline or "").strip().lower()
        profile_url = (member.profile_url or "").strip().lower()
        image_url = (member.image_url or "").strip().lower()

        signals: List[str] = []

        # Policy rule: no image/default placeholder => deny
        if not image_url:
            return False, "no_image"
        if image_url.startswith("data:image"):
            return False, "no_image"
        if any(token in image_url for token in ("ghost-person", "profile-ghost", "avatar-ghost", "default-avatar")):
            return False, "no_image"

        if any(path in profile_url for path in ("/company/", "/school/", "/groups/")):
            return False, "profile_org_url"

        if "administrator at" in headline or headline.startswith("admin at "):
            signals.append("headline_admin_role")

        if any(keyword in name for keyword in cls.NON_HUMAN_NAME_KEYWORDS):
            signals.append("name_brand_keyword")

        if any(keyword in headline for keyword in cls.NON_HUMAN_HEADLINE_KEYWORDS):
            signals.append("headline_brand_keyword")

        if len(signals) >= 2:
            return False, ",".join(sorted(set(signals)))

        if "headline_admin_role" in signals:
            return False, "headline_admin_role"

        return True, "human_likely"

    def _compose_non_human_message(self, member: GroupMemberRequest) -> str:
        """Compose a short rejection message for non-human account requests."""
        if member.classification_reason == "no_image":
            return "no image"
        template = self.non_human_message
        if "{name}" in template:
            return template.format(name=(member.name or "there"))
        return template

    def _select_message_menu_item(self, driver: Any) -> bool:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        try:
            WebDriverWait(driver, 6).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class,'artdeco-dropdown__content') or @role='menu']")
                )
            )
        except Exception:
            return False

        # 1) Text-match keyword route
        items = driver.find_elements(
            By.XPATH,
            "//div[contains(@class,'artdeco-dropdown__content') or @role='menu']//*[self::button or self::span or @role='menuitem']",
        )
        for item in items:
            txt = (item.text or "").strip().lower()
            if not txt:
                continue
            if any(keyword in txt for keyword in self.MESSAGE_MENU_KEYWORDS):
                try:
                    item.click()
                    return True
                except Exception:
                    continue

        # 2) Fallback: second menu item (first is usually connect)
        fallback_items = driver.find_elements(
            By.XPATH,
            "//div[contains(@class,'artdeco-dropdown__content') or @role='menu']//li|//div[@role='menu']//div[@role='menuitem']",
        )
        if len(fallback_items) >= 2:
            try:
                fallback_items[1].click()
                return True
            except Exception:
                return False

        return False

    def _send_welcome_message(self, driver: Any, message: str) -> bool:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        try:
            # Find all editors - prefer the modal one (usually the last/visible one)
            editors = driver.find_elements(By.CSS_SELECTOR, "div.msg-form__contenteditable[contenteditable='true']")
            editor = None
            for e in reversed(editors):  # Check from last (modal) to first
                if e.is_displayed():
                    editor = e
                    break
            if not editor and editors:
                editor = editors[-1]

            if not editor:
                logger.warning("[LN-GROUP-MEMBER] No message editor found")
                return False

            editor.click()
            time.sleep(0.3)
            editor.send_keys(Keys.CONTROL, "a")
            editor.send_keys(Keys.BACKSPACE)
            time.sleep(0.2)

            # Type message using clipboard (supports all Unicode including emojis)
            # Copy to clipboard using pyperclip or JS
            try:
                import pyperclip
                pyperclip.copy(message)
                editor.send_keys(Keys.CONTROL, "v")
            except ImportError:
                # Fallback: Use JS clipboard API
                driver.execute_script(
                    """
                    const text = arguments[1];
                    const el = arguments[0];
                    el.focus();
                    navigator.clipboard.writeText(text).then(() => {
                        document.execCommand('paste');
                    }).catch(() => {
                        // Fallback: set innerHTML with events
                        el.innerHTML = text.replace(/\\n/g, '<br>');
                        el.dispatchEvent(new InputEvent('input', {bubbles: true, data: text, inputType: 'insertText'}));
                    });
                    """,
                    editor,
                    message,
                )
            time.sleep(0.5)

            # Wait for send button to become enabled
            send_btn = None
            send_btns = driver.find_elements(By.CSS_SELECTOR, "button.msg-form__send-button")
            for btn in reversed(send_btns):
                if btn.is_displayed():
                    send_btn = btn
                    break
            if not send_btn and send_btns:
                send_btn = send_btns[-1]

            if not send_btn:
                logger.warning("[LN-GROUP-MEMBER] No send button found")
                return False

            # Wait up to 3s for button to be enabled
            for _ in range(6):
                if send_btn.is_enabled():
                    break
                time.sleep(0.5)

            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", send_btn)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", send_btn)
            time.sleep(random.uniform(0.7, 1.5))
            return True
        except Exception as exc:
            logger.warning("[LN-GROUP-MEMBER] Failed to send message: %s", exc)
            return False

    def _message_member_from_row(self, row: Any, driver: Any, message: str) -> bool:
        from selenium.webdriver.common.by import By

        try:
            overflow_btn = row.find_element(
                By.XPATH,
                ".//button[starts-with(@id,'overflowDropdownTriggerId') or contains(@class,'artdeco-dropdown__trigger')]",
            )
            overflow_btn.click()
            time.sleep(random.uniform(0.4, 1.0))
            if not self._select_message_menu_item(driver):
                return False
            time.sleep(random.uniform(0.8, 1.4))
            return self._send_welcome_message(driver, message)
        except Exception as exc:
            logger.warning("[LN-GROUP-MEMBER] Failed to open message flow: %s", exc)
            return False

    def _approve_member_from_row(self, row: Any, driver: Any = None) -> bool:
        from selenium.webdriver.common.by import By

        selectors = [
            ".//button[contains(@class,'groups-manage-group-admin-actions__primary-action')]",
            ".//button[contains(@aria-label,'Approve request for')]",
            ".//button[normalize-space()='Approve']",
        ]
        for selector in selectors:
            try:
                approve_btn = row.find_element(By.XPATH, selector)
                # Scroll into view before clicking (fix for "move target out of bounds")
                if driver:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", approve_btn)
                    time.sleep(random.uniform(0.2, 0.4))
                approve_btn.click()
                time.sleep(random.uniform(0.5, 1.2))
                return True
            except Exception:
                continue
        return False

    def _deny_member_from_row(self, row: Any, driver: Any = None) -> bool:
        from selenium.webdriver.common.by import By

        selectors = [
            ".//button[contains(@class,'groups-manage-group-admin-actions__secondary-action')]",
            ".//button[contains(@aria-label,'Deny request for')]",
            ".//button[normalize-space()='Deny']",
            ".//button[normalize-space()='Reject']",
        ]
        for selector in selectors:
            try:
                deny_btn = row.find_element(By.XPATH, selector)
                if driver:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", deny_btn)
                    time.sleep(random.uniform(0.2, 0.4))
                deny_btn.click()
                time.sleep(random.uniform(0.5, 1.2))
                return True
            except Exception:
                continue
        return False

    def process_membership_requests(
        self,
        dry_run: bool = True,
        max_requests: Optional[int] = None,
        send_welcome: bool = True,
        approve: bool = True,
        screenshot_dir: Optional[str] = None,
        post_news_after: bool = False,
        post_news_dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Process pending LinkedIn group membership requests.

        Args:
            dry_run: Read and draft only (no clicks that change state).
            max_requests: Optional limit for this run.
            send_welcome: Send DM welcome before approval.
            approve: Approve request after optional DM.
            screenshot_dir: Optional path for step screenshots.
            post_news_after: Run OpenClaw news posting once queue is processed.
            post_news_dry_run: Dry-run flag for post_news_after.
        """
        summary: Dict[str, Any] = {
            "status": "started",
            "dry_run": dry_run,
            "group_id": self.group_id,
            "processed": 0,
            "messaged": 0,
            "approved": 0,
            "denied": 0,
            "failed": 0,
            "drafts": [],
            "post_news_result": None,
        }

        try:
            from modules.platform_integration.linkedin_agent.src.anti_detection_poster import (
                AntiDetectionLinkedIn,
            )
            from selenium.webdriver.common.by import By

            poster = AntiDetectionLinkedIn()
            if not poster.driver:
                poster.setup_driver(use_existing_session=True)
            driver = poster.driver
            driver.get(self.group_membership_url)
            time.sleep(random.uniform(2.0, 3.5))

            if dry_run:
                rows = self._find_request_rows(driver)
                if max_requests:
                    rows = rows[: max_requests]
                for idx, row in enumerate(rows, 1):
                    member = self._extract_member_request(row)
                    should_deny = self.deny_non_human and not member.is_likely_human
                    decision = "deny" if should_deny else "approve"
                    message = (
                        self._compose_non_human_message(member)
                        if should_deny
                        else self.message_composer.compose(member)
                    )
                    summary["processed"] += 1
                    summary["drafts"].append(
                        {
                            "index": idx,
                            "name": member.name,
                            "headline": member.headline,
                            "language": member.language,
                            "is_likely_human": member.is_likely_human,
                            "classification_reason": member.classification_reason,
                            "decision": decision,
                            "message": message,
                            "profile_url": member.profile_url,
                            "image_url": member.image_url,
                        }
                    )
                    screenshot_path = self._capture_screenshot(
                        driver, screenshot_dir, f"dryrun_{idx:03d}"
                    )
                    self._log_action(
                        member=member,
                        action_type="dry_run_preview",
                        action_status="ok",
                        message_preview=message,
                        screenshot_path=screenshot_path,
                    )
                summary["status"] = "dry_run_complete"
                return summary

            # Live mode: process first row repeatedly to avoid stale-element issues
            processed_limit = max_requests or 10_000
            while summary["processed"] < processed_limit:
                rows = self._find_request_rows(driver)
                if not rows:
                    break
                row = rows[0]
                member = self._extract_member_request(row)
                should_deny = self.deny_non_human and not member.is_likely_human
                message = (
                    self._compose_non_human_message(member)
                    if should_deny
                    else self.message_composer.compose(member)
                )
                screenshot_path = self._capture_screenshot(
                    driver, screenshot_dir, f"member_{summary['processed'] + 1:03d}_before"
                )

                summary["processed"] += 1
                action_ok = True

                if send_welcome:
                    msg_ok = self._message_member_from_row(row, driver, message)
                    if msg_ok:
                        summary["messaged"] += 1
                        self._log_action(
                            member=member,
                            action_type="deny_notice_message" if should_deny else "welcome_message",
                            action_status="ok",
                            message_preview=message,
                            screenshot_path=screenshot_path,
                        )
                    else:
                        action_ok = False
                        self._log_action(
                            member=member,
                            action_type="deny_notice_message" if should_deny else "welcome_message",
                            action_status="failed",
                            message_preview=message,
                            screenshot_path=screenshot_path,
                            error_text="message_failed",
                        )

                # Reload row reference after overlay actions
                if approve:
                    try:
                        driver.get(self.group_membership_url)
                        time.sleep(random.uniform(1.8, 3.0))
                        rows = self._find_request_rows(driver)
                        if not rows:
                            break
                        row = rows[0]
                    except Exception:
                        pass

                    if should_deny:
                        deny_ok = self._deny_member_from_row(row, driver=driver)
                        if deny_ok:
                            summary["denied"] += 1
                            self._log_action(
                                member=member,
                                action_type="deny_request",
                                action_status="ok",
                                message_preview=message if send_welcome else None,
                            )
                        else:
                            action_ok = False
                            self._log_action(
                                member=member,
                                action_type="deny_request",
                                action_status="failed",
                                error_text="deny_failed",
                            )
                    else:
                        approve_ok = self._approve_member_from_row(row, driver=driver)
                        if approve_ok:
                            summary["approved"] += 1
                            self._log_action(
                                member=member,
                                action_type="approve_request",
                                action_status="ok",
                                message_preview=message if send_welcome else None,
                            )
                        else:
                            action_ok = False
                            self._log_action(
                                member=member,
                                action_type="approve_request",
                                action_status="failed",
                                error_text="approve_failed",
                            )

                if not action_ok:
                    summary["failed"] += 1

                driver.get(self.group_membership_url)
                time.sleep(random.uniform(1.8, 3.0))

            if post_news_after:
                summary["post_news_result"] = run_openclaw_news_flow(
                    dry_run=post_news_dry_run
                )

            summary["status"] = "live_complete"
            return summary

        except Exception as exc:
            summary["status"] = "error"
            summary["error"] = str(exc)
            return summary


def run_group_membership_cycle(
    dry_run: bool = True,
    max_requests: Optional[int] = None,
    send_welcome: bool = True,
    approve: bool = True,
    screenshot_dir: Optional[str] = None,
    post_news_after: bool = False,
    post_news_dry_run: bool = True,
) -> Dict[str, Any]:
    """Convenience wrapper for CLI/tests."""
    dae = OpenClawGroupMembershipDAE()
    return dae.process_membership_requests(
        dry_run=dry_run,
        max_requests=max_requests,
        send_welcome=send_welcome,
        approve=approve,
        screenshot_dir=screenshot_dir,
        post_news_after=post_news_after,
        post_news_dry_run=post_news_dry_run,
    )


def run_message_existing_members(
    dry_run: bool = True,
    max_members: int = 10,
    screenshot_dir: Optional[str] = None,
    skip_already_messaged: bool = True,
) -> Dict[str, Any]:
    """
    Message existing (already approved) group members.

    Goes to /manage/membership/members/ and sends intro messages.
    Tracks who has been messaged in SQLite to avoid duplicates.

    Args:
        dry_run: Preview without sending
        max_members: Max members to message per run
        screenshot_dir: Optional screenshot directory
        skip_already_messaged: Skip members already in DB

    Returns:
        Summary dict with counts
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    dae = OpenClawGroupMembershipDAE()
    summary = {
        "action": "message_existing_members",
        "dry_run": dry_run,
        "processed": 0,
        "messaged": 0,
        "skipped": 0,
        "failed": 0,
        "status": "started",
    }

    # URL for existing members (not pending requests)
    members_url = f"https://www.linkedin.com/groups/{dae.group_id}/manage/membership/members/"

    try:
        # Connect to existing Chrome debug session (already logged into LinkedIn)
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        driver = None

        # Primary: Connect to existing Chrome debug session (port 9222)
        try:
            options = Options()
            options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            driver = webdriver.Chrome(options=options)
            logger.info("[LN-GROUP-MEMBERS] Connected to Chrome debug port 9222")
        except Exception as e:
            logger.warning(f"[LN-GROUP-MEMBERS] Chrome 9222 connection failed: {e}")

        # Fallback: BrowserManager - use same session key as linkedin_company_poster
        # This reuses the existing logged-in session (linkedin_1263645)
        if not driver:
            try:
                from modules.infrastructure.foundups_selenium.src.browser_manager import get_browser_manager
            except ImportError:
                # Handle direct script execution (modules not in path)
                import sys
                from pathlib import Path
                repo_root = Path(__file__).parents[5]  # 5 levels up to repo root
                if str(repo_root) not in sys.path:
                    sys.path.insert(0, str(repo_root))
                from modules.infrastructure.foundups_selenium.src.browser_manager import get_browser_manager
            manager = get_browser_manager()
            # CRITICAL: Use linkedin_1263645 to reuse existing logged-in session
            # NOT linkedin_group_6729915 which would create a new blank session
            driver = manager.get_browser("chrome", "linkedin_1263645")
            logger.info("[LN-GROUP-MEMBERS] Using BrowserManager (session: linkedin_1263645)")

        logger.info(f"[LN-GROUP-MEMBERS] Navigating to {members_url}")
        driver.get(members_url)
        time.sleep(random.uniform(4.0, 6.0))  # Longer wait for page to fully load

        # Wait for member list to appear
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul[class*='artdeco'], div[class*='groups-manage']"))
            )
        except Exception:
            logger.warning("[LN-GROUP-MEMBERS] Timeout waiting for member list")

        # Screenshot directory
        if screenshot_dir:
            os.makedirs(screenshot_dir, exist_ok=True)

        # Find member rows - based on 012's DOM inspection
        # DOM: ul.artdeco-li.t > li.artdeco-li.t__item
        row_selectors = [
            "li.artdeco-list__item",
            "li[class*='artdeco-list__item']",
            "li[class*='groups-manage']",
            "ul[class*='artdeco'] > li",
            "div[class*='groups-manage'] li",
        ]

        member_rows = []
        for selector in row_selectors:
            try:
                member_rows = driver.find_elements(By.CSS_SELECTOR, selector)
                if member_rows:
                    logger.info(f"[LN-GROUP-MEMBERS] Found {len(member_rows)} rows via: {selector}")
                    break
            except Exception:
                continue

        if not member_rows:
            summary["status"] = "no_members_found"
            return summary

        # Get already-messaged members from DB
        messaged_profiles = set()
        if skip_already_messaged:
            try:
                conn = sqlite3.connect(dae.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT member_profile_url FROM agents_social_group_actions "
                    "WHERE action_type = 'intro_message' AND action_status = 'ok'"
                )
                messaged_profiles = {row[0] for row in cursor.fetchall()}
                conn.close()
                logger.info(f"[LN-GROUP-MEMBERS] {len(messaged_profiles)} already messaged (will skip)")
            except Exception as e:
                logger.warning(f"[LN-GROUP-MEMBERS] DB check failed: {e}")

        processed_count = 0
        for idx, row in enumerate(member_rows[:max_members]):
            if processed_count >= max_members:
                break

            try:
                # Extract member info from row
                # LinkedIn uses div, not span for these elements (as of 2026-03)
                name_elem = None
                for selector in ["div.artdeco-entity-lockup__title", "span.artdeco-entity-lockup__title"]:
                    try:
                        name_elem = row.find_element(By.CSS_SELECTOR, selector)
                        if name_elem:
                            break
                    except Exception:
                        continue
                name = name_elem.text.strip() if name_elem else f"Member_{idx}"

                headline_elem = None
                for selector in ["div.artdeco-entity-lockup__subtitle", "span.artdeco-entity-lockup__subtitle"]:
                    try:
                        headline_elem = row.find_element(By.CSS_SELECTOR, selector)
                        if headline_elem:
                            break
                    except Exception:
                        continue
                headline = headline_elem.text.strip() if headline_elem else ""

                profile_url = ""
                try:
                    link_elem = row.find_element(By.CSS_SELECTOR, "a[href*='/in/']")
                    profile_url = link_elem.get_attribute("href") or ""
                except Exception:
                    pass

                # Skip if already messaged
                if profile_url and profile_url in messaged_profiles:
                    logger.debug(f"[LN-GROUP-MEMBERS] Skipping {name} (already messaged)")
                    summary["skipped"] += 1
                    continue

                member = GroupMemberRequest(
                    name=name,
                    headline=headline,
                    image_url="",  # Not needed for messaging
                )

                # Use enhanced personalized message builder (012's template)
                try:
                    from modules.platform_integration.linkedin_agent.skillz.linkedin_group_moderation.executor import (
                        build_enhanced_welcome_message,
                    )
                    message = build_enhanced_welcome_message(member)
                except ImportError:
                    # Fallback to generic composer
                    message = dae.message_composer.compose(member)

                logger.info(f"[LN-GROUP-MEMBERS] [{idx+1}] {name} | {headline[:40]}...")

                if dry_run:
                    logger.info(f"[DRY-RUN] Would message: {name}")
                    logger.debug(f"[DRY-RUN] Message preview:\n{message[:200]}...")
                    summary["processed"] += 1
                    processed_count += 1
                    continue

                # Live mode: Click Message button directly (NOT in dropdown - it's a separate button)
                # As of 2026-03, LinkedIn shows Message as a pill button to the right of each row
                try:
                    # Message button is a separate button on the row, NOT in the overflow dropdown
                    message_btn = None
                    message_selectors = [
                        ".//button[normalize-space()='Message']",
                        ".//button[contains(@aria-label,'Message')]",
                        ".//button[contains(text(),'Message')]",
                        ".//span[normalize-space()='Message']/ancestor::button",
                    ]
                    for sel in message_selectors:
                        try:
                            message_btn = row.find_element(By.XPATH, sel)
                            if message_btn:
                                break
                        except Exception:
                            continue

                    if not message_btn:
                        logger.warning(f"[LN-GROUP-MEMBERS] Could not find Message button for {name}")
                        summary["failed"] += 1
                        continue

                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", message_btn)
                    time.sleep(random.uniform(0.3, 0.6))
                    message_btn.click()
                    time.sleep(random.uniform(0.8, 1.4))

                    # Send the message
                    if dae._send_welcome_message(driver, message):
                        summary["messaged"] += 1
                        dae._log_action(
                            member=member,
                            action_type="intro_message",
                            action_status="ok",
                            message_preview=message,
                        )
                        logger.info(f"[LN-GROUP-MEMBERS] Messaged: {name}")
                    else:
                        summary["failed"] += 1
                        dae._log_action(
                            member=member,
                            action_type="intro_message",
                            action_status="failed",
                            error_text="send_failed",
                        )

                    summary["processed"] += 1
                    processed_count += 1

                    # Anti-detection delay between messages
                    delay = random.uniform(30, 90)
                    logger.info(f"[LN-GROUP-MEMBERS] Waiting {delay:.0f}s before next message...")
                    time.sleep(delay)

                    # Refresh page to get fresh DOM
                    driver.get(members_url)
                    time.sleep(random.uniform(2.0, 3.5))

                    # Re-find rows after refresh
                    for selector in row_selectors:
                        try:
                            member_rows = driver.find_elements(By.CSS_SELECTOR, selector)
                            if member_rows:
                                break
                        except Exception:
                            continue

                except Exception as e:
                    logger.warning(f"[LN-GROUP-MEMBERS] Failed to message {name}: {e}")
                    summary["failed"] += 1

            except Exception as e:
                logger.warning(f"[LN-GROUP-MEMBERS] Row {idx} extraction failed: {e}")
                summary["failed"] += 1

        summary["status"] = "dry_run_complete" if dry_run else "live_complete"
        return summary

    except Exception as exc:
        summary["status"] = "error"
        summary["error"] = str(exc)
        logger.error(f"[LN-GROUP-MEMBERS] Error: {exc}")
        return summary


def read_linkedin_message_history(conversation_url: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    """
    Read message history from LinkedIn messaging page.

    This function scrapes the current LinkedIn messaging conversation
    to allow a second agent to understand the conversation context.

    Args:
        conversation_url: Optional URL to a specific conversation.
                         If None, reads the currently open conversation.
        limit: Maximum number of messages to extract.

    Returns:
        Dict with conversation info and messages list.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By

    result = {
        "status": "started",
        "conversation_url": "",
        "participant": "",
        "messages": [],
        "error": None,
    }

    try:
        options = Options()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        driver = webdriver.Chrome(options=options)
        logger.info("[LN-MSG-READER] Connected to Chrome debug port 9222")

        # Navigate to conversation if URL provided
        if conversation_url:
            driver.get(conversation_url)
            time.sleep(3)

        result["conversation_url"] = driver.current_url

        # Extract participant name from conversation header
        try:
            participant_elem = driver.find_element(
                By.CSS_SELECTOR,
                "h2.msg-entity-lockup__entity-title, span.msg-entity-lockup__entity-title"
            )
            result["participant"] = participant_elem.text.strip()
        except Exception:
            result["participant"] = "Unknown"

        # Extract messages from conversation
        message_bubbles = driver.find_elements(
            By.CSS_SELECTOR,
            "div.msg-s-event-listitem__body, li.msg-s-message-list__event"
        )

        messages = []
        for bubble in message_bubbles[-limit:]:  # Last N messages
            try:
                # Get message text
                text_elem = bubble.find_element(By.CSS_SELECTOR, "p.msg-s-event-listitem__body")
                text = text_elem.text.strip()

                # Determine if sent or received
                is_sent = "msg-s-message-list__self-message" in bubble.get_attribute("class") or ""

                # Get timestamp if available
                timestamp = ""
                try:
                    time_elem = bubble.find_element(By.CSS_SELECTOR, "time, span.msg-s-message-list__time-heading")
                    timestamp = time_elem.text.strip()
                except Exception:
                    pass

                messages.append({
                    "text": text,
                    "direction": "sent" if is_sent else "received",
                    "timestamp": timestamp,
                })
            except Exception:
                continue

        result["messages"] = messages
        result["status"] = "success"
        logger.info(f"[LN-MSG-READER] Extracted {len(messages)} messages from conversation with {result['participant']}")

    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)
        logger.error(f"[LN-MSG-READER] Error: {exc}")

    return result


def run_message_pending_requests(
    dry_run: bool = True,
    max_requests: int = 10,
    screenshot_dir: Optional[str] = None,
    skip_already_messaged: bool = True,
) -> Dict[str, Any]:
    """
    Message pending group membership requests (NOT yet approved members).

    Goes to /manage/membership/requested/ and sends intro messages via 3-dot dropdown.
    Tracks who has been messaged in SQLite to avoid duplicates.

    Args:
        dry_run: Preview without sending
        max_requests: Max requests to message per run
        screenshot_dir: Optional screenshot directory
        skip_already_messaged: Skip profiles already in DB

    Returns:
        Summary dict with counts
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    dae = OpenClawGroupMembershipDAE()
    summary = {
        "action": "message_pending_requests",
        "dry_run": dry_run,
        "processed": 0,
        "messaged": 0,
        "approved": 0,
        "denied": 0,
        "skipped": 0,
        "failed": 0,
        "status": "started",
    }

    # URL for PENDING REQUESTS (not approved members)
    requests_url = f"https://www.linkedin.com/groups/{dae.group_id}/manage/membership/requested/"

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        driver = None

        # Connect to existing Chrome debug session (port 9222)
        try:
            options = Options()
            options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            driver = webdriver.Chrome(options=options)
            logger.info("[LN-GROUP-REQUESTS] Connected to Chrome debug port 9222")
        except Exception as e:
            logger.warning(f"[LN-GROUP-REQUESTS] Chrome 9222 connection failed: {e}")

        if not driver:
            summary["status"] = "error"
            summary["error"] = "Failed to connect to Chrome"
            return summary

        logger.info(f"[LN-GROUP-REQUESTS] Navigating to {requests_url}")
        driver.get(requests_url)
        time.sleep(random.uniform(4.0, 6.0))

        # Wait for request list
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul[class*='artdeco'], div[class*='groups-manage']"))
            )
        except Exception:
            logger.warning("[LN-GROUP-REQUESTS] Timeout waiting for request list")

        # Get already messaged profiles
        messaged_profiles = set()
        if skip_already_messaged:
            try:
                conn = sqlite3.connect(dae.sqlite_db)
                cursor = conn.execute(
                    "SELECT profile_url FROM group_membership_logs WHERE action_type = 'intro_message'"
                )
                messaged_profiles = {row[0] for row in cursor.fetchall() if row[0]}
                conn.close()
                logger.info(f"[LN-GROUP-REQUESTS] {len(messaged_profiles)} already messaged (will skip)")
            except Exception:
                pass

        # Find request rows
        row_selectors = [
            "li.artdeco-list__item",
            "li[class*='artdeco-list__item']",
            "ul[class*='artdeco'] > li",
        ]

        request_rows = []
        for selector in row_selectors:
            try:
                request_rows = driver.find_elements(By.CSS_SELECTOR, selector)
                if request_rows:
                    logger.info(f"[LN-GROUP-REQUESTS] Found {len(request_rows)} rows via: {selector}")
                    break
            except Exception:
                continue

        if not request_rows:
            logger.warning("[LN-GROUP-REQUESTS] No request rows found")
            summary["status"] = "no_requests"
            return summary

        processed_count = 0
        for idx, row in enumerate(request_rows):
            if processed_count >= max_requests:
                break

            try:
                # Extract name
                name_elem = None
                for selector in ["div.artdeco-entity-lockup__title", "span.artdeco-entity-lockup__title"]:
                    try:
                        name_elem = row.find_element(By.CSS_SELECTOR, selector)
                        if name_elem:
                            break
                    except Exception:
                        continue
                name = name_elem.text.strip() if name_elem else f"Member_{idx}"

                # Extract headline
                headline_elem = None
                for selector in ["div.artdeco-entity-lockup__subtitle", "span.artdeco-entity-lockup__subtitle"]:
                    try:
                        headline_elem = row.find_element(By.CSS_SELECTOR, selector)
                        if headline_elem:
                            break
                    except Exception:
                        continue
                headline = headline_elem.text.strip() if headline_elem else ""

                # Get profile URL
                profile_url = ""
                try:
                    link_elem = row.find_element(By.CSS_SELECTOR, "a[href*='/in/']")
                    profile_url = link_elem.get_attribute("href") or ""
                except Exception:
                    pass

                # Skip if already messaged
                if profile_url and profile_url in messaged_profiles:
                    logger.debug(f"[LN-GROUP-REQUESTS] Skipping {name} (already messaged)")
                    summary["skipped"] += 1
                    continue

                # Check for profile image
                has_image = False
                image_url = ""
                try:
                    img_elem = row.find_element(By.CSS_SELECTOR, "img")
                    img_src = img_elem.get_attribute("src") or ""
                    has_image = img_src and "ghost" not in img_src.lower() and "data:image" not in img_src
                    image_url = img_src if has_image else ""
                except Exception:
                    pass

                member = GroupMemberRequest(name=name, headline=headline, image_url=image_url)

                # === QWEN3 AI EVALUATION ===
                qwen_evaluation = None
                if QWEN3_AVAILABLE:
                    try:
                        qwen_evaluation = evaluate_profile_with_qwen(
                            name=name,
                            headline=headline,
                            has_image=has_image,
                            profile_url=profile_url
                        )
                        logger.info(f"[QWEN3] Evaluated {name}: {qwen_evaluation.decision.value} "
                                   f"(confidence: {qwen_evaluation.confidence:.2f})")
                    except Exception as qwen_err:
                        logger.warning(f"[QWEN3] Evaluation failed for {name}: {qwen_err}")

                # Use enhanced personalized message
                try:
                    from modules.platform_integration.linkedin_agent.skillz.linkedin_group_moderation.executor import (
                        build_enhanced_welcome_message,
                    )
                    is_cxo = qwen_evaluation and qwen_evaluation.decision == ProfileDecision.APPROVE_CONNECT
                    message = build_enhanced_welcome_message(member, is_cxo=is_cxo)
                except ImportError:
                    message = dae.message_composer.compose(member)

                logger.info(f"[LN-GROUP-REQUESTS] [{idx+1}] {name} | {headline[:40]}...")

                if dry_run:
                    logger.info(f"[DRY-RUN] Would message: {name}")
                    summary["processed"] += 1
                    processed_count += 1
                    continue

                # LIVE MODE: Click 3-dot dropdown -> "Message"
                try:
                    # Find 3-dot dropdown trigger button
                    dropdown_trigger = row.find_element(By.CSS_SELECTOR, "button[class*='artdeco-dropdown__trigger']")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdown_trigger)
                    time.sleep(random.uniform(0.3, 0.6))
                    dropdown_trigger.click()
                    time.sleep(random.uniform(0.6, 1.0))

                    # Find "Message" option in the dropdown
                    dropdown = driver.find_element(By.CSS_SELECTOR, "div.artdeco-dropdown__content--is-open")
                    message_btn = None
                    items = dropdown.find_elements(By.CSS_SELECTOR, "div.artdeco-dropdown__item")
                    for item in items:
                        if item.text.strip().lower() == "message":
                            message_btn = item
                            break

                    if not message_btn:
                        logger.warning(f"[LN-GROUP-REQUESTS] No 'Message' option in dropdown for {name}")
                        summary["failed"] += 1
                        # Click elsewhere to close dropdown
                        driver.find_element(By.TAG_NAME, "body").click()
                        time.sleep(0.3)
                        continue

                    message_btn.click()
                    # Wait for message modal to fully load
                    time.sleep(random.uniform(2.5, 3.5))

                    # === WSP 97: CoT - RETRIEVE before STATING ===
                    # Check if conversation already has messages (prevent duplicate send)
                    existing_messages = driver.find_elements(
                        By.CSS_SELECTOR,
                        "p.msg-s-event-listitem__body, div.msg-s-event-listitem__body"
                    )

                    if existing_messages:
                        # Get the last sent message text
                        last_msg_text = ""
                        for msg_elem in reversed(existing_messages):
                            try:
                                last_msg_text = msg_elem.text.strip()
                                if last_msg_text:
                                    break
                            except Exception:
                                continue

                        # Compare with message we're about to send
                        # Check if first 100 chars match (signature line may differ)
                        if last_msg_text and message[:100].lower() in last_msg_text[:150].lower():
                            logger.info(f"[LN-GROUP-REQUESTS] WSP 97: Duplicate detected for {name} - already messaged")
                            summary["skipped"] += 1
                            # Close modal and continue
                            from selenium.webdriver.common.keys import Keys
                            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                            time.sleep(0.5)
                            continue
                        else:
                            logger.info(f"[LN-GROUP-REQUESTS] WSP 97: Existing message found but different - showing for 012 review")
                            print(f"\n{'='*60}")
                            print(f"EXISTING MESSAGE FOUND:")
                            print(f"{last_msg_text[:300]}...")
                            print(f"{'='*60}")
                    # === END WSP 97 ===

                    # Type message into editor and wait for 012 approval
                    logger.info(f"[LN-GROUP-REQUESTS] === COMPOSING MESSAGE ===")
                    logger.info(f"[LN-GROUP-REQUESTS] To: {name}")
                    logger.info(f"[LN-GROUP-REQUESTS] Headline: {headline}")

                    from selenium.webdriver.common.keys import Keys
                    editors = driver.find_elements(By.CSS_SELECTOR, "div.msg-form__contenteditable[contenteditable='true']")
                    editor = None
                    for e in reversed(editors):
                        if e.is_displayed():
                            editor = e
                            break

                    if not editor:
                        logger.warning(f"[LN-GROUP-REQUESTS] No editor found for {name}")
                        summary["failed"] += 1
                        continue

                    # Type the message
                    editor.click()
                    time.sleep(0.3)
                    try:
                        import pyperclip
                        pyperclip.copy(message)
                        editor.send_keys(Keys.CONTROL, "v")
                    except ImportError:
                        for line in message.split("\n"):
                            editor.send_keys(line)
                            editor.send_keys(Keys.SHIFT, Keys.ENTER)
                    time.sleep(0.5)

                    # PAUSE FOR 012 APPROVAL - message is visible in browser
                    print(f"\n{'='*60}")
                    print(f"MESSAGE READY FOR: {name}")
                    print(f"Headline: {headline}")
                    print(f"Has Image: {'Yes' if has_image else 'NO'}")

                    # Show Qwen3 AI evaluation
                    if qwen_evaluation:
                        print(f"{'='*60}")
                        print(f"[QWEN3 EVALUATION]")
                        print(f"  Decision: {qwen_evaluation.decision.value.upper()}")
                        print(f"  Confidence: {qwen_evaluation.confidence:.0%}")
                        print(f"  Threat Level: {qwen_evaluation.threat_level}")
                        print(f"  Engagement: {qwen_evaluation.engagement_potential}")
                        print(f"  Reasoning: {qwen_evaluation.reasoning}")

                    print(f"{'='*60}")
                    print(f"\n{message}\n")
                    print(f"{'='*60}")
                    print(">>> 012 APPROVAL REQUIRED <<<")
                    print("Press ENTER to SEND, or type 'skip' to skip this person")
                    print(f"{'='*60}")

                    try:
                        approval = input().strip().lower()
                        if approval == "skip":
                            logger.info(f"[LN-GROUP-REQUESTS] 012 skipped: {name}")
                            summary["skipped"] += 1
                            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                            time.sleep(0.5)
                            continue
                    except (EOFError, KeyboardInterrupt):
                        logger.info(f"[LN-GROUP-REQUESTS] Interrupted")
                        break

                    # 012 approved - click send button
                    send_btns = driver.find_elements(By.CSS_SELECTOR, "button.msg-form__send-button")
                    send_btn = None
                    for btn in reversed(send_btns):
                        if btn.is_displayed():
                            send_btn = btn
                            break

                    if send_btn and send_btn.is_enabled():
                        driver.execute_script("arguments[0].click();", send_btn)
                        time.sleep(1.0)
                        summary["messaged"] += 1
                        dae._log_action(member=member, action_type="intro_message", action_status="ok", message_preview=message)
                        logger.info(f"[LN-GROUP-REQUESTS] SENT: {name}")

                        # Close message modal
                        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        time.sleep(1.0)

                        # Navigate back to requests page
                        driver.get(requests_url)
                        time.sleep(2.0)

                        # === QWEN3 AI-POWERED APPROVE/DENY DECISION ===
                        # Use Qwen evaluation instead of hardcoded image check
                        try:
                            new_rows = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item")
                            for new_row in new_rows:
                                try:
                                    row_name = new_row.find_element(By.CSS_SELECTOR, "div.artdeco-entity-lockup__title").text.strip()
                                    if name in row_name or row_name in name:
                                        # Determine action based on Qwen evaluation
                                        should_approve = True  # Default approve if no Qwen
                                        should_deny_incomplete = False

                                        if qwen_evaluation:
                                            if qwen_evaluation.decision in [ProfileDecision.APPROVE, ProfileDecision.APPROVE_CONNECT]:
                                                should_approve = True
                                                logger.info(f"[QWEN3] Decision: APPROVE ({qwen_evaluation.reasoning})")
                                            elif qwen_evaluation.decision == ProfileDecision.DENY_INCOMPLETE:
                                                should_approve = False
                                                should_deny_incomplete = True
                                                logger.info(f"[QWEN3] Decision: DENY_INCOMPLETE ({qwen_evaluation.reasoning})")
                                            elif qwen_evaluation.decision == ProfileDecision.DENY:
                                                should_approve = False
                                                logger.info(f"[QWEN3] Decision: DENY ({qwen_evaluation.reasoning})")
                                            else:
                                                # NEEDS_REVIEW - skip for manual handling
                                                logger.info(f"[QWEN3] Decision: NEEDS_REVIEW - skipping")
                                                continue
                                        else:
                                            # Fallback: check image if Qwen unavailable
                                            has_pic = False
                                            try:
                                                img_elem = new_row.find_element(By.CSS_SELECTOR, "img")
                                                img_src = img_elem.get_attribute("src") or ""
                                                has_pic = img_src and "ghost" not in img_src.lower() and "data:image" not in img_src
                                            except Exception:
                                                pass
                                            should_approve = has_pic
                                            should_deny_incomplete = not has_pic

                                        if should_approve:
                                            # APPROVE - Qwen says this is a good member
                                            try:
                                                approve_btn = new_row.find_element(By.CSS_SELECTOR, "button[class*='primary-action'], button[aria-label*='Approve']")
                                                driver.execute_script("arguments[0].click();", approve_btn)
                                                time.sleep(0.5)
                                                reason = f"[QWEN3: {qwen_evaluation.decision.value}]" if qwen_evaluation else "(fallback)"
                                                logger.info(f"[LN-GROUP-REQUESTS] APPROVED: {name} {reason}")
                                                summary["approved"] += 1
                                            except Exception as approve_err:
                                                logger.warning(f"[LN-GROUP-REQUESTS] Could not approve {name}: {approve_err}")

                                        elif should_deny_incomplete:
                                            # DENY_INCOMPLETE - Message requesting profile completion, then deny
                                            logger.info(f"[LN-GROUP-REQUESTS] DENY_INCOMPLETE: {name} - sending follow-up + deny")

                                            # Open message again via 3-dot
                                            trigger = new_row.find_element(By.CSS_SELECTOR, "button[class*='artdeco-dropdown__trigger']")
                                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", trigger)
                                            time.sleep(0.3)
                                            trigger.click()
                                            time.sleep(0.5)

                                            dd = driver.find_element(By.CSS_SELECTOR, "div.artdeco-dropdown__content--is-open")
                                            for item in dd.find_elements(By.CSS_SELECTOR, "div.artdeco-dropdown__item"):
                                                if item.text.strip().lower() == "message":
                                                    item.click()
                                                    break
                                            time.sleep(2.0)

                                            # Type "complete your profile" message
                                            no_pic_msg = "Complete your profile (add a photo) to join. --0102"
                                            editors = driver.find_elements(By.CSS_SELECTOR, "div.msg-form__contenteditable[contenteditable='true']")
                                            for ed in reversed(editors):
                                                if ed.is_displayed():
                                                    ed.click()
                                                    time.sleep(0.2)
                                                    try:
                                                        import pyperclip
                                                        pyperclip.copy(no_pic_msg)
                                                        ed.send_keys(Keys.CONTROL, "v")
                                                    except ImportError:
                                                        ed.send_keys(no_pic_msg)
                                                    time.sleep(0.3)
                                                    break

                                            # Send the no-pic message
                                            for sb in reversed(driver.find_elements(By.CSS_SELECTOR, "button.msg-form__send-button")):
                                                if sb.is_displayed() and sb.is_enabled():
                                                    driver.execute_script("arguments[0].click();", sb)
                                                    time.sleep(0.5)
                                                    break

                                            # Close modal
                                            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                                            time.sleep(0.5)

                                            # Navigate back and DENY
                                            driver.get(requests_url)
                                            time.sleep(1.5)
                                            for r2 in driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item"):
                                                try:
                                                    r2_name = r2.find_element(By.CSS_SELECTOR, "div.artdeco-entity-lockup__title").text.strip()
                                                    if name in r2_name or r2_name in name:
                                                        t2 = r2.find_element(By.CSS_SELECTOR, "button[class*='artdeco-dropdown__trigger']")
                                                        t2.click()
                                                        time.sleep(0.5)
                                                        dd2 = driver.find_element(By.CSS_SELECTOR, "div.artdeco-dropdown__content--is-open")
                                                        for di in dd2.find_elements(By.CSS_SELECTOR, "div.artdeco-dropdown__item"):
                                                            if "block" in di.text.lower() or "deny" in di.text.lower():
                                                                di.click()
                                                                time.sleep(0.5)
                                                                reason = f"[QWEN3: {qwen_evaluation.decision.value}]" if qwen_evaluation else "(incomplete profile)"
                                                                logger.info(f"[LN-GROUP-REQUESTS] DENIED: {name} {reason}")
                                                                summary["denied"] += 1
                                                                break
                                                        break
                                                except Exception:
                                                    continue

                                        else:
                                            # Plain DENY - spam/bot detected by Qwen
                                            logger.info(f"[LN-GROUP-REQUESTS] DENY: {name} - spam/bot detected")
                                            try:
                                                trigger = new_row.find_element(By.CSS_SELECTOR, "button[class*='artdeco-dropdown__trigger']")
                                                trigger.click()
                                                time.sleep(0.5)
                                                dd = driver.find_element(By.CSS_SELECTOR, "div.artdeco-dropdown__content--is-open")
                                                for di in dd.find_elements(By.CSS_SELECTOR, "div.artdeco-dropdown__item"):
                                                    if "block" in di.text.lower() or "deny" in di.text.lower():
                                                        di.click()
                                                        time.sleep(0.5)
                                                        reason = f"[QWEN3: {qwen_evaluation.reasoning[:50]}]" if qwen_evaluation else "(spam)"
                                                        logger.info(f"[LN-GROUP-REQUESTS] DENIED: {name} {reason}")
                                                        summary["denied"] += 1
                                                        break
                                            except Exception as deny_err:
                                                logger.warning(f"[LN-GROUP-REQUESTS] Could not deny {name}: {deny_err}")

                                        break
                                except Exception:
                                    continue
                        except Exception as action_err:
                            logger.warning(f"[LN-GROUP-REQUESTS] Could not approve/deny {name}: {action_err}")

                    else:
                        logger.warning(f"[LN-GROUP-REQUESTS] Send button not enabled for {name}")
                        summary["failed"] += 1

                    summary["processed"] += 1
                    processed_count += 1

                    # Anti-detection delay
                    delay = random.uniform(30, 90)
                    logger.info(f"[LN-GROUP-REQUESTS] Waiting {delay:.0f}s before next...")
                    time.sleep(delay)

                    # Refresh page
                    driver.get(requests_url)
                    time.sleep(random.uniform(2.0, 3.5))

                    # Re-find rows
                    for selector in row_selectors:
                        try:
                            request_rows = driver.find_elements(By.CSS_SELECTOR, selector)
                            if request_rows:
                                break
                        except Exception:
                            continue

                except Exception as e:
                    logger.warning(f"[LN-GROUP-REQUESTS] Failed to message {name}: {e}")
                    summary["failed"] += 1
                    # Close any open modal and refresh to reset state
                    try:
                        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        time.sleep(0.5)
                        driver.get(requests_url)
                        time.sleep(2.0)
                        for selector in row_selectors:
                            try:
                                request_rows = driver.find_elements(By.CSS_SELECTOR, selector)
                                if request_rows:
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass

            except Exception as e:
                logger.warning(f"[LN-GROUP-REQUESTS] Row {idx} extraction failed: {e}")
                summary["failed"] += 1

        summary["status"] = "dry_run_complete" if dry_run else "live_complete"
        return summary

    except Exception as exc:
        summary["status"] = "error"
        summary["error"] = str(exc)
        logger.error(f"[LN-GROUP-REQUESTS] Error: {exc}")
        return summary


def _normalize_candidate_url(url: str) -> str:
    """Normalize search result URL and unwrap DuckDuckGo redirect links."""
    raw = (url or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
        host = parsed.netloc.lower()
        if "duckduckgo.com" in host and parsed.path.startswith("/l/"):
            q = parse_qs(parsed.query)
            wrapped = q.get("uddg", [""])[0]
            if wrapped:
                return unquote(wrapped).strip()
    except Exception:
        return raw
    return raw


def _looks_like_video_candidate(url: str, title: str = "", summary: str = "") -> bool:
    """
    Return True when a candidate appears to be a video link/content.

    Policy: group news posts should not open or link to video pages.
    """
    normalized = _normalize_candidate_url(url)
    probe_url = normalized.lower()
    probe_text = f"{title or ''} {summary or ''}".strip().lower()

    if not probe_url:
        return True

    video_domains = (
        "youtube.com",
        "youtu.be",
        "tiktok.com",
        "vimeo.com",
        "dailymotion.com",
        "twitch.tv",
        "rumble.com",
        "bilibili.com",
        "loom.com",
        "wistia.com",
        "brightcove.com",
    )
    if any(domain in probe_url for domain in video_domains):
        return True

    video_path_tokens = (
        "/watch",
        "/shorts",
        "/reel",
        "/reels",
        "/video",
        "/videos",
        "/live",
        "/clip",
        "/clips",
        "/embed/",
    )
    if any(token in probe_url for token in video_path_tokens):
        return True

    if probe_url.endswith((".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v")):
        return True

    # Content hints (kept conservative to limit false positives)
    if any(
        term in probe_text
        for term in (
            " official video ",
            " watch video ",
            " video: ",
            " trailer ",
            " livestream ",
            " full episode ",
        )
    ):
        return True

    return False


def _is_allowed_news_candidate(url: str, title: str = "", summary: str = "") -> bool:
    """True when URL is web-safe and not a video candidate."""
    normalized = _normalize_candidate_url(url)
    if not normalized:
        return False
    parsed = urlparse(normalized)
    if parsed.scheme.lower() not in ("http", "https"):
        return False
    if not parsed.netloc:
        return False
    return not _looks_like_video_candidate(normalized, title, summary)


def _compose_news_probe_text(title: str, summary: str = "", source: str = "") -> str:
    """Lowercased probe text for policy keyword checks."""
    return f"{title or ''} {summary or ''} {source or ''}".strip().lower()


def _classify_news_priority(title: str, summary: str = "", source: str = "") -> str:
    """
    Classify a candidate for posting policy:
    - openclaw_update: OpenClaw/IronClaw ecosystem + actionable update/security signal
    - major_ai_update: Top AI ecosystem + actionable update/security signal
    - openclaw_general: OpenClaw ecosystem but no explicit update signal
    - generic: everything else
    """
    text = _compose_news_probe_text(title, summary, source)
    has_openclaw = any(term in text for term in OPENCLAW_ECOSYSTEM_TERMS)
    has_major_ai = any(term in text for term in MAJOR_AI_NEWS_TERMS)
    has_update = any(term in text for term in UPDATE_SIGNAL_TERMS)

    if has_openclaw and has_update:
        return "openclaw_update"
    if has_major_ai and has_update:
        return "major_ai_update"
    if has_openclaw:
        return "openclaw_general"
    return "generic"


def _is_policy_news_candidate(item: NewsItem) -> bool:
    """Posting policy gate for LN group news."""
    bucket = _classify_news_priority(item.title, item.summary or "", item.source)
    return bucket in {"openclaw_update", "major_ai_update"}


def search_openclaw_news(max_results: int = 10) -> List[NewsItem]:
    """
    Search for OpenClaw news using DuckDuckGo.

    Searches for:
    - OpenClaw updates, features, security
    - Related projects (lobster.cash, Crossmint)
    - New agents (Peeka, etc.)

    Args:
        max_results: Maximum number of results to return

    Returns:
        List of NewsItem objects
    """
    logger.info(f"[SEARCH] Searching for OpenClaw news via {SEARCH_PROVIDER} (max={max_results})")

    # Search queries targeting actionable OpenClaw/IronClaw + major AI updates
    search_queries = [
        "OpenClaw security patch update CVE -site:youtube.com -site:tiktok.com -site:vimeo.com",
        "OpenClaw release notes changelog update -site:youtube.com -site:tiktok.com -site:vimeo.com",
        "IronClaw update security fix -site:youtube.com -site:tiktok.com -site:vimeo.com",
        "lobster.cash Crossmint update release -site:youtube.com -site:tiktok.com -site:vimeo.com",
        "OpenAI API deprecation security update -site:youtube.com -site:tiktok.com -site:vimeo.com",
        "Anthropic Claude update security release notes -site:youtube.com -site:tiktok.com -site:vimeo.com",
    ]

    # Research paper queries (separate to avoid rate limiting the news queries)
    research_queries = [
        "OpenClaw agent architecture paper arxiv -site:youtube.com",
        "agent security framework paper arxiv -site:youtube.com",
    ]

    all_items: List[NewsItem] = []
    seen_urls: set = set()

    try:
        ddg_library = "ddgs"
        try:
            from ddgs import DDGS
        except ImportError:
            # Backward-compatibility fallback for older environments.
            from duckduckgo_search import DDGS
            ddg_library = "duckduckgo_search"

        ddg = DDGS()
        logger.info(f"[SEARCH] DDG client loaded: {ddg_library}")

        for i, query in enumerate(search_queries):
            # Rate limit avoidance: delay between queries (2-4 seconds)
            if i > 0:
                delay = random.uniform(2.0, 4.0)
                logger.debug(f"[SEARCH] Rate limit delay: {delay:.1f}s")
                time.sleep(delay)

            try:
                # Search news specifically
                results = list(ddg.news(query, max_results=5, timelimit="m"))  # Last month

                for r in results:
                    url = _normalize_candidate_url(r.get("url", ""))
                    title = r.get("title", "")
                    body = r.get("body", "")
                    if url in seen_urls or not url:
                        continue
                    if not _is_allowed_news_candidate(url, title, body):
                        logger.info(f"[SEARCH] Skipping video result: {url}")
                        continue
                    seen_urls.add(url)

                    # Parse date
                    pub_date = None
                    date_str = r.get("date", "")
                    if date_str:
                        try:
                            # DDG returns ISO format dates
                            pub_date = datetime.fromisoformat(date_str.replace("Z", "+00:00").split("+")[0])
                        except (ValueError, TypeError):
                            pass

                    item = NewsItem(
                        title=title,
                        url=url,
                        source=r.get("source", "unknown"),
                        published_date=pub_date,
                        summary=body,
                    )
                    all_items.append(item)
                    logger.debug(f"[SEARCH] Found: {item.title[:50]}... from {item.source}")

                    if len(all_items) >= max_results:
                        break

            except Exception as e:
                logger.warning(f"[SEARCH] Query '{query}' failed: {e}")
                continue

            if len(all_items) >= max_results:
                break

        # Search for research papers (via web search for arxiv/scholar links)
        if len(all_items) < max_results:
            for i, query in enumerate(research_queries):
                if len(all_items) >= max_results:
                    break
                # Rate limit delay
                time.sleep(random.uniform(2.0, 4.0))
                try:
                    results = list(ddg.text(query, max_results=3))
                    for r in results:
                        url = _normalize_candidate_url(r.get("href", r.get("link", "")))
                        title = r.get("title", "")
                        body = r.get("body", "")
                        if url in seen_urls or not url:
                            continue
                        if not _is_allowed_news_candidate(url, title, body):
                            logger.info(f"[SEARCH] Skipping video result: {url}")
                            continue
                        # Prioritize arxiv, scholar, research domains
                        if any(domain in url.lower() for domain in ["arxiv.org", "scholar.google", "research", "paper", "acm.org", "ieee.org"]):
                            seen_urls.add(url)
                            item = NewsItem(
                                title=title,
                                url=url,
                                source=_extract_source(url),
                                summary=body,
                            )
                            all_items.append(item)
                            logger.info(f"[RESEARCH] Found paper: {item.title[:50]}...")
                except Exception as e:
                    logger.debug(f"[RESEARCH] Query '{query}' failed: {e}")
                    continue

        # Also try general web search if news didn't find enough
        if len(all_items) < max_results // 2:
            time.sleep(random.uniform(2.0, 4.0))  # Rate limit delay
            try:
                # Try multiple web search queries
                web_queries = [
                    "OpenClaw security update -site:youtube.com -site:tiktok.com -site:vimeo.com",
                    "OpenClaw release notes -site:youtube.com -site:tiktok.com -site:vimeo.com",
                    "AI model API deprecation update -site:youtube.com -site:tiktok.com -site:vimeo.com",
                ]
                for wq in web_queries:
                    if len(all_items) >= max_results:
                        break
                    try:
                        results = list(ddg.text(wq, max_results=5))
                        for r in results:
                            url = _normalize_candidate_url(r.get("href", r.get("link", "")))
                            title = r.get("title", "")
                            body = r.get("body", "")
                            if url in seen_urls or not url:
                                continue
                            if not _is_allowed_news_candidate(url, title, body):
                                logger.info(f"[SEARCH] Skipping video result: {url}")
                                continue
                            seen_urls.add(url)

                            item = NewsItem(
                                title=title,
                                url=url,
                                source=_extract_source(url),
                                summary=body,
                            )
                            all_items.append(item)
                        time.sleep(random.uniform(1.0, 2.0))  # Delay between web queries
                    except Exception as e:
                        logger.debug(f"[SEARCH] Web query '{wq}' failed: {e}")
                        continue

            except Exception as e:
                logger.warning(f"[SEARCH] Web search fallback failed: {e}")

    except ImportError:
        logger.error("[SEARCH] DDG client not installed. Run: pip install ddgs")
        return []

    except Exception as e:
        logger.error(f"[SEARCH] Search failed: {e}")
        return []

    logger.info(f"[SEARCH] Found {len(all_items)} news items")
    return all_items[:max_results]


def _extract_source(url: str) -> str:
    """Extract source name from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        # Get main domain name
        parts = domain.split(".")
        if len(parts) >= 2:
            return parts[-2]  # e.g., "techcrunch" from "techcrunch.com"
        return domain
    except Exception:
        return "unknown"


def run_openclaw_news_flow(dry_run: bool = True, extra_comment: str = "") -> Dict:
    """
    Main execution flow for OpenClaw news posting.

    Args:
        dry_run: If True, don't actually post
        extra_comment: Optional custom line(s) inserted into post body

    Returns:
        Dict with execution results
    """
    logger.info("[FLOW] Starting OpenClaw news flow")

    # 1. Search for news
    news_items = search_openclaw_news(max_results=10)

    if not news_items:
        logger.info("[FLOW] No news items found")
        return {
            "status": "no_news",
            "search_provider": SEARCH_PROVIDER,
            "video_policy": "blocked",
            "selection_policy": "openclaw_or_major_ai_actionable_updates",
            "policy_threshold": POLICY_RELEVANCE_THRESHOLD,
            "items_found": 0,
            "posted": False,
        }

    # 2. Rate and filter
    rater = NewsRelevanceRater()
    non_video_items = [
        item for item in news_items
        if not _looks_like_video_candidate(item.url, item.title, item.summary or "")
    ]
    video_filtered = len(news_items) - len(non_video_items)
    if video_filtered:
        logger.info(f"[FLOW] Excluded {video_filtered} video candidates before rating")

    policy_items = [item for item in non_video_items if _is_policy_news_candidate(item)]
    policy_filtered_out = len(non_video_items) - len(policy_items)
    if policy_filtered_out:
        logger.info(
            "[FLOW] Excluded %s items by policy (must be OpenClaw/major-AI actionable updates)",
            policy_filtered_out,
        )

    rated_items = [(item, rater.rate(item)) for item in policy_items]
    filtered = [
        (item, score) for item, score in rated_items
        if score >= POLICY_RELEVANCE_THRESHOLD
    ]

    logger.info(
        "[FLOW] %s policy-aligned non-video items evaluated, %s passed threshold (>= %.2f)",
        len(policy_items),
        len(filtered),
        POLICY_RELEVANCE_THRESHOLD,
    )

    if not filtered:
        return {
            "status": "below_threshold",
            "search_provider": SEARCH_PROVIDER,
            "video_policy": "blocked",
            "selection_policy": "openclaw_or_major_ai_actionable_updates",
            "items_found": len(news_items),
            "items_non_video": len(non_video_items),
            "items_policy_aligned": len(policy_items),
            "items_policy_filtered": policy_filtered_out,
            "policy_threshold": POLICY_RELEVANCE_THRESHOLD,
            "video_filtered": video_filtered,
            "posted": False,
        }

    # 3. Post top item
    poster = OpenClawGroupPoster()
    top_item, score = max(filtered, key=lambda x: x[1])

    success = poster.post_to_group(
        top_item,
        dry_run=dry_run,
        extra_comment=extra_comment,
    )

    return {
        "status": "posted" if success else "failed",
        "search_provider": SEARCH_PROVIDER,
        "video_policy": "blocked",
        "selection_policy": "openclaw_or_major_ai_actionable_updates",
        "items_found": len(news_items),
        "items_non_video": len(non_video_items),
        "items_policy_aligned": len(policy_items),
        "items_policy_filtered": policy_filtered_out,
        "policy_threshold": POLICY_RELEVANCE_THRESHOLD,
        "video_filtered": video_filtered,
        "items_filtered": len(filtered),
        "top_item": top_item.title,
        "top_score": score,
        "top_item_bucket": _classify_news_priority(
            top_item.title, top_item.summary or "", top_item.source
        ),
        "top_item_url": top_item.url,
        "comment_applied": bool((extra_comment or "").strip()),
        "posted": success,
        "dry_run": dry_run
    }


def main():
    """
    CLI entry point for OpenClaw Group News Poster.

    Agent-callable CLI for IronClaw/OpenClaw execution.

    Usage:
        python -m modules.platform_integration.linkedin_agent.skillz.openclaw_group_news.executor \
            --action approve_members --dry-run
        python -m modules.platform_integration.linkedin_agent.skillz.openclaw_group_news.executor \
            --action post_news --dry-run
        python -m modules.platform_integration.linkedin_agent.skillz.openclaw_group_news.executor \
            --action full_cycle --max-requests 5

    WSP Compliance:
        WSP 72: Module Independence (standalone CLI)
        WSP 11: Interface Documentation
    """
    import argparse

    parser = argparse.ArgumentParser(
        description='OpenClaw Group News - Agent CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Actions:
  approve_members  Check and approve pending group membership requests
  post_news        Search for OpenClaw news, rate, and post to group
  full_cycle       Run both: approve members first, then post news
  message_members  Message existing (already approved) group members

Examples:
  # Dry run - preview what would happen
  python -m modules.platform_integration.linkedin_agent.skillz.openclaw_group_news.executor \\
      --action approve_members --dry-run

  # Approve up to 10 members with welcome messages
  python -m modules.platform_integration.linkedin_agent.skillz.openclaw_group_news.executor \\
      --action approve_members --max-requests 10

  # Search and post news (dry run)
  python -m modules.platform_integration.linkedin_agent.skillz.openclaw_group_news.executor \\
      --action post_news --dry-run

  # Full cycle: approve members then post news
  python -m modules.platform_integration.linkedin_agent.skillz.openclaw_group_news.executor \\
      --action full_cycle

  # Message existing group members (dry run first!)
  python -m modules.platform_integration.linkedin_agent.skillz.openclaw_group_news.executor \\
      --action message_members --dry-run --max-requests 5

  # Message existing members (live - with 30-90s delays between)
  python -m modules.platform_integration.linkedin_agent.skillz.openclaw_group_news.executor \\
      --action message_members --max-requests 10
        """
    )

    parser.add_argument('--action', '-a', type=str, required=True,
                        choices=['approve_members', 'post_news', 'full_cycle', 'message_members'],
                        help='Action to perform')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview actions without executing')
    parser.add_argument('--max-requests', '-m', type=int, default=10,
                        help='Max membership requests to process (default: 10)')
    parser.add_argument('--send-welcome', action='store_true', default=True,
                        help='Send welcome DM before approving (default: True)')
    parser.add_argument('--no-welcome', action='store_true',
                        help='Skip welcome DM, just approve')
    parser.add_argument('--screenshot-dir', type=str, default=None,
                        help='Directory to save screenshots (optional)')
    parser.add_argument('--comment', type=str, default="",
                        help='Optional custom comment text appended to news post body')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(message)s")

    send_welcome = args.send_welcome and not args.no_welcome

    result = {"action": args.action, "dry_run": args.dry_run}

    if args.action == 'approve_members':
        logger.info(f"[CLI] Action: approve_members | dry_run={args.dry_run} | max={args.max_requests}")
        result.update(run_group_membership_cycle(
            dry_run=args.dry_run,
            max_requests=args.max_requests,
            send_welcome=send_welcome,
            approve=True,
            screenshot_dir=args.screenshot_dir,
            post_news_after=False
        ))

    elif args.action == 'post_news':
        logger.info(f"[CLI] Action: post_news | dry_run={args.dry_run}")
        result.update(
            run_openclaw_news_flow(
                dry_run=args.dry_run,
                extra_comment=args.comment,
            )
        )

    elif args.action == 'message_members':
        logger.info(f"[CLI] Action: message_members | dry_run={args.dry_run} | max={args.max_requests}")
        result.update(run_message_existing_members(
            dry_run=args.dry_run,
            max_members=args.max_requests,
            screenshot_dir=args.screenshot_dir,
            skip_already_messaged=True,
        ))

    elif args.action == 'full_cycle':
        logger.info(f"[CLI] Action: full_cycle | dry_run={args.dry_run}")
        # Run membership first, then news
        membership_result = run_group_membership_cycle(
            dry_run=args.dry_run,
            max_requests=args.max_requests,
            send_welcome=send_welcome,
            approve=True,
            screenshot_dir=args.screenshot_dir,
            post_news_after=False  # We call news separately for better logging
        )
        news_result = run_openclaw_news_flow(
            dry_run=args.dry_run,
            extra_comment=args.comment,
        )

        result["membership"] = membership_result
        result["news"] = news_result

    # Output JSON for agent parsing
    import json
    print(json.dumps(result, indent=2, default=str))

    # Return exit code based on success
    # Valid outcomes (exit 0): posted, dry_run, no_news (search worked), below_threshold
    # Error outcomes (exit 1): error, failed
    valid_statuses = ["posted", "live_complete", "dry_run_complete", "ok", "no_news", "below_threshold"]
    status = result.get("status", "")
    success = status in valid_statuses

    if args.action == "full_cycle":
        membership_status = result.get("membership", {}).get("status", "")
        success = membership_status in valid_statuses

    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
