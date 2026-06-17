# -*- coding: utf-8 -*-
"""
YouTube Studio Ask Indexer - Browser Automation for Video Indexing

Uses YouTube's built-in Gemini "Ask" feature to index video content.
Runs after comment engagement completes each cycle.

WSP Compliance:
    WSP 27: DAE Architecture (Signal → Knowledge → Protocol → Agentic)
    WSP 72: Module Independence
    WSP 91: DAE Observability

Usage:
    indexer = StudioAskIndexer(driver)
    await indexer.index_channel_videos(channel_id="UCfHM9Fw9HD-NwiS0seD_oIA")
"""

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from modules.infrastructure.shared_utilities.youtube_channel_registry import get_channel_by_id
from modules.ai_intelligence.video_indexer.src.video_index_store import (
    VideoIndexStore,
    IndexData,
)

# WSP 84 REUSE: the proven "012 input behavior" already used by YT comment replies
# (tars_like_heart_reply/src/reply_executor.py). We reuse get_human_behavior ->
# HumanBehavior.human_type / human_delay rather than reinventing typing cadence.
try:
    from modules.infrastructure.foundups_selenium.src.human_behavior import (
        get_human_behavior,
    )
    HUMAN_BEHAVIOR_AVAILABLE = True
except ImportError:  # pragma: no cover - import guard mirrors reply_executor
    get_human_behavior = None
    HUMAN_BEHAVIOR_AVAILABLE = False

logger = logging.getLogger(__name__)

INDEX_ROOT = Path("memory") / "video_index"
STOP_FILE = Path("memory") / "STOP_VIDEO_INDEXER"
REINDEX_FILE = Path("memory") / "REINDEX_VIDEO_INDEXER"


def _env_truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _stop_active() -> bool:
    return STOP_FILE.exists()


def _consume_reindex_signal() -> bool:
    if _env_truthy("VIDEO_INDEXER_FORCE_REINDEX"):
        return True
    if REINDEX_FILE.exists():
        try:
            REINDEX_FILE.unlink()
        except Exception:
            logger.warning("[VIDEO-INDEX] Failed to clear REINDEX signal file")
        return True
    return False


def _count_indexed_by_channel(index_root: Path) -> Dict[str, int]:
    if not index_root.exists():
        return {}
    counts: Dict[str, int] = {}
    for child in index_root.iterdir():
        if not child.is_dir():
            continue
        counts[child.name] = len(list(child.glob("*.json")))
    return counts

# VideoContentIndex causes segfault on Windows (ChromaDB native library issue)
# Disable for now - indexing works without it, storage goes to JSON files
# TODO: Fix ChromaDB segfault in holo_index/core/video_search.py
VIDEO_INDEX_AVAILABLE = False
VideoContentIndex = None  # Placeholder
logger.debug("[STUDIO-ASK] VideoContentIndex disabled (ChromaDB segfault workaround)")


@dataclass
class AskResult:
    """Result from YouTube's Ask Gemini feature."""
    video_id: str
    title: str
    response_text: str
    topics: List[str]
    timestamps: List[Dict[str, str]]
    success: bool
    # Content category detected from browser Gemini (no API needed)
    content_category: str = "other"  # ffcpln_music, personal_vlog, ice_remix, educational, other
    error: Optional[str] = None


class StudioAskIndexer:
    """
    Index videos using YouTube Studio's built-in Gemini "Ask" feature.
    
    This mirrors 012's behavior of using the Ask button in Studio to
    query video content, then stores results in VideoContentIndex.
    """
    
    # =========================================================================
    # PRIMARY (Phase 1): YouTube Studio "Ask Studio" header UI
    # ---------------------------------------------------------------------
    # The current Studio video-edit page exposes an "Ask Studio" entry in the
    # page header (ytcp-icon-button). Clicking it opens a creator chat dialog
    # with a contenteditable prompt box and a streaming response panel.
    # This is the CANONICAL path for Phase 1. The legacy watch-page Ask button
    # and the old Studio popup menu are DEMOTED to fallback (see SELECTORS).
    # =========================================================================
    ASK_STUDIO_SELECTORS = {
        # Header entry button that opens the Ask Studio dialog.
        "header_button": [
            'ytcp-icon-button[aria-label="Ask Studio"]',
            'ytcp-icon-button[aria-label*="Ask Studio"]',
            'button[aria-label="Ask Studio"]',
            'button[aria-label*="Ask Studio"]',
        ],
        # Dialog container shown after clicking the header button.
        "dialog": [
            'ytcp-dialog#dialog',
            'ytcp-dialog',
        ],
        # Contenteditable prompt box inside the dialog.
        "prompt_box": [
            'div[contenteditable][aria-label="Ask something"]',
            'div.ytcpCreatorChatEntityAttachmentInlineFlowPromptBox[contenteditable="true"]',
            'div[contenteditable="true"][aria-label*="Ask"]',
        ],
        # Send / submit button inside the dialog. PREFERRED submission path
        # (mirror reply_executor's button-click submit, NEVER Enter-spam).
        "send_button": [
            'ytcp-icon-button[aria-label="Send"]',
            'ytcp-icon-button[aria-label*="Send"]',
            'button[aria-label="Send"]',
            'button[aria-label*="Send"]',
            'button[aria-label*="Submit"]',
        ],
        # Streaming / response container candidates (DOM text, NOT clipboard).
        "response_stream": [
            '#PAcreator_chat_streaming',
            'div.ytcpCreatorChatEntityResponse',
            'ytcp-creator-chat-response',
            '[class*="CreatorChat"][class*="Response"]',
        ],
    }

    # Refusal / no-answer markers. If the STABILIZED Ask Studio response contains
    # any of these, we fail closed (success=False) and persist NOTHING - a refusal
    # must never be stored as transcript_summary. (Data-integrity guard.)
    REFUSAL_MARKERS = (
        "query unsuccessful",
        "i didn't quite understand",
        "i'm not quite sure what you're asking",
        "transcript is unavailable",
        "i cannot analyze",
        "you canceled this response",
    )

    # Response is considered COMPLETE once its text stops growing for this many
    # consecutive polls (stabilization), guarding against partial/streaming reads.
    RESPONSE_STABLE_POLLS = 3

    # Legacy/fallback selectors (Watch Page AND Studio popup menu).
    # FALLBACK ONLY (Phase 1): retained for resilience, never the primary path.
    SELECTORS = {
        "content_tab": "a[href*='/channel/'][href*='/videos']",
        "video_row": "ytcp-video-row",
        "video_title": "a#video-title",

        # FALLBACK WATCH PAGE: Ask button is in #actions > ytd-menu-renderer > #flexible-item-buttons
        "watch_ask_button": "#flexible-item-buttons button, yt-button-view-model button",
        "watch_actions": "#actions ytd-menu-renderer",

        # FALLBACK STUDIO POPUP: Menu trigger to open popup where old Ask lived
        "studio_menu_trigger": "ytd-menu-renderer button, button[aria-label='More actions'], #button-shape button",
        # Ask button is inside popup menu as tp-yt-paper-item
        "studio_ask_popup_item": "tp-yt-paper-item.style-scope.ytd-menu-service-item-renderer",
        "popup_menu": "ytd-menu-popup-renderer, tp-yt-iron-dropdown",

        # Gemini chat interface (legacy fallback input/response)
        "ask_input": "textarea[placeholder*='Ask'], input[placeholder*='Ask'], .gemini-input textarea",
        "ask_response": ".gemini-response, .ask-response-content, .gemini-chat-response",
        "video_details_link": "a[href*='/video/'][href*='/edit']",
    }

    # Phase 1: PRIMARY path is the Studio "Ask Studio" header (NOT watch page).
    # Watch-page Ask is demoted to a labelled fallback only.
    USE_WATCH_PAGE = False

    # Max seconds to wait for the Ask Studio response stream to produce text
    # before failing closed (no partial/garbage indexing).
    RESPONSE_TIMEOUT_SECONDS = 30.0

    # ---------------------------------------------------------------------
    # STUDIO_ASK_CHANNEL_CONTEXT_PHASE1: right TARGET -> right CHANNEL -> verify
    # ---------------------------------------------------------------------
    # STEP 0 (target selection): 012 live-observed Selenium attach to a Chrome
    # SIDE-PANEL target first (chrome://glic / the gemini.google.com glic side
    # panel / accounts.google.com RotateCookiesPage), NOT the Studio tab. A
    # URL whose scheme/host matches any of these is NEVER a valid Ask target.
    NON_STUDIO_TARGET_URL_MARKERS = (
        "chrome://glic",
        "chrome-untrusted://glic",
        "gemini.google.com/glic",
        "/glic",
        "rotatecookiespage",
        "accounts.google.com/rotatecookies",
    )

    # A usable Ask target is a YouTube Studio tab or (acceptably) a normal
    # https web tab we can drive to Studio. about:blank / new-tab pages are
    # acceptable normal targets the driver can navigate.
    ACCEPTABLE_TARGET_URL_PREFIXES = (
        "https://studio.youtube.com",
        "https://www.youtube.com",
        "https://youtube.com",
    )
    ACCEPTABLE_NORMAL_URL_PREFIXES = (
        "https://",
        "http://",
        "about:blank",
        "chrome://newtab",
    )

    # STEP 2 (observable verification): markers that the channel-scoped Studio
    # context did NOT load as the owning channel (permission / not-found /
    # sign-in / account-switch / generic Oops). Detected in page title/body.
    WRONG_CONTEXT_MARKERS = (
        "oops",
        "not found",
        "no access",
        "don't have access",
        "permission",
        "unavailable",
        "switch account",
        "choose an account",
        "sign in",
        "this page isn",
        "something went wrong",
    )

    # Standard prompt for video analysis with content category detection
    ASK_PROMPT = """Analyze this video and respond in JSON format:
{
  "content_category": "ffcpln_music|personal_vlog|ice_remix|educational|other",
  "topics": ["topic1", "topic2"],
  "segments": [
    {"time": "0:00", "topic": "Introduction", "summary": "..."},
    {"time": "1:30", "topic": "Main point", "summary": "..."}
  ]
}

CONTENT CATEGORY (pick ONE):
- ffcpln_music: Music video, no speech, instrumental/electronic, visualizers
- personal_vlog: Person talking, daily life, conversational, personal stories
- ice_remix: Political content, ICE/immigration, news clips, activist
- educational: Tutorial, how-to, teaching, informational
- other: None of the above"""

    # Channel-specific Ask Studio prompts.
    # Keyed by the channel registry `description_template` value
    # (youtube_channel_registry: undaodu->undaodu, foundups->foundups,
    #  move2japan/antifafm->ffcpln). Music/ffcpln channels get a LIGHTER prompt
    # that does NOT demand a full transcript (no speech to transcribe).
    CHANNEL_PROMPTS = {
        "undaodu": """Analyze this UnDaoDu video and respond in JSON format:
{
  "content_category": "personal_vlog|educational|ice_remix|other",
  "topics": ["topic1", "topic2"],
  "segments": [
    {"time": "0:00", "topic": "Introduction", "summary": "..."},
    {"time": "1:30", "topic": "Main point", "summary": "..."}
  ]
}
Focus on the spoken ideas: identity, consciousness, pAVS/FoundUps themes.
Include timestamped segments for the key points discussed.""",
        "foundups": """Analyze this FoundUps video and respond in JSON format:
{
  "content_category": "educational|personal_vlog|other",
  "topics": ["topic1", "topic2"],
  "segments": [
    {"time": "0:00", "topic": "Introduction", "summary": "..."},
    {"time": "1:30", "topic": "Main point", "summary": "..."}
  ]
}
Focus on startup / autonomous-venture themes and the key points discussed.
Include timestamped segments.""",
        # Lighter prompt for FFCPLN / music channels (Move2Japan, antifaFM):
        # mostly instrumental, no full transcript expected.
        "ffcpln": """Analyze this music/short video and respond in JSON format:
{
  "content_category": "ffcpln_music|other",
  "topics": ["mood", "genre"],
  "segments": []
}
This is a music or short visual piece. Do NOT produce a full transcript.
Give a brief category and a few mood/genre topics only.""",
    }

    @classmethod
    def _prompt_for_channel(cls, channel_entry: Optional[Dict[str, Any]]) -> str:
        """
        Select the Ask Studio prompt for a channel.

        Resolution order:
          1. channel registry `shorts.description_template` -> CHANNEL_PROMPTS
          2. unknown / missing -> generic ASK_PROMPT (safe default)

        Does NOT invent a new registry; reads existing description_template.
        """
        template = ""
        if channel_entry:
            template = str(
                (channel_entry.get("shorts") or {}).get("description_template", "")
            ).strip().lower()
        return cls.CHANNEL_PROMPTS.get(template, cls.ASK_PROMPT)

    def __init__(
        self,
        driver=None,
        human=None,
        max_videos_per_cycle: int = 5,
    ):
        """
        Initialize Studio Ask Indexer.
        
        Args:
            driver: Selenium WebDriver (Chrome or Edge)
            human: HumanBehaviorSimulator for anti-detection
            max_videos_per_cycle: Max videos to index per cycle
        """
        self.driver = driver
        self.human = human
        self.max_videos_per_cycle = max_videos_per_cycle
        
        # Initialize video index if available
        self.video_index = None
        if VIDEO_INDEX_AVAILABLE:
            try:
                self.video_index = VideoContentIndex()
                logger.info("[STUDIO-ASK] VideoContentIndex connected")
            except Exception as e:
                logger.warning(f"[STUDIO-ASK] VideoContentIndex init failed: {e}")
    
    async def _human_delay(self, base: float = 1.0, variance: float = 0.3) -> None:
        """Human-like delay for anti-detection."""
        import asyncio
        import random
        
        if self.human:
            delay = self.human.human_delay(base, variance)
        else:
            delay = base * (1 + random.uniform(-variance, variance))
        
        await asyncio.sleep(delay)
    
    def _extract_video_id_from_url(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        match = re.search(r'/video/([^/?]+)', url)
        if match:
            return match.group(1)
        match = re.search(r'[?&]v=([^&]+)', url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _index_exists(index_root: Path, channel_key: str, video_id: str) -> bool:
        if not channel_key or not video_id:
            return False
        path = index_root / channel_key / f"{video_id}.json"
        return path.exists()

    @staticmethod
    def _parse_timestamp(ts: str) -> Optional[float]:
        """Convert 'M:SS' or 'H:MM:SS' to seconds."""
        if not ts:
            return None
        try:
            parts = ts.split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except (ValueError, IndexError):
            return None
        return None

    @staticmethod
    def _ask_result_to_index_data(
        ask_result: AskResult,
        channel_key: str,
    ) -> IndexData:
        """Build IndexData from Ask Gemini response."""
        segments = []
        for seg in ask_result.timestamps or []:
            start = StudioAskIndexer._parse_timestamp(seg.get("time", ""))
            summary = seg.get("summary") or seg.get("topic") or ""
            if not summary:
                continue
            segments.append(
                {
                    "start": start if start is not None else 0,
                    "end": None,
                    "text": summary,
                    "speaker": "",
                }
            )

        audio = {
            "segments": segments,
            "transcript_summary": ask_result.response_text or "",
        }

        return IndexData(
            video_id=ask_result.video_id,
            channel=channel_key,
            title=ask_result.title or "",
            duration=0,
            indexed_at=datetime.now().isoformat(),
            audio=audio,
            visual={"description": "", "keyframes": []},
            moments=[],
            clips=[],
            metadata={
                "topics": ask_result.topics or [],
                "key_points": [],
                "summary": ask_result.response_text or "",
                "content_category": ask_result.content_category or "other",
            },
            gemini_summary={
                "ask_response": ask_result.response_text or "",
                "ask_topics": ask_result.topics or [],
                "ask_segments": ask_result.timestamps or [],
            },
            transcript_source="gemini",
        )
    
    def _parse_ask_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from Ask Gemini response."""
        try:
            # Try to extract JSON from response (allow nested braces for segments)
            json_match = re.search(r'\{[\s\S]*?"topics"[\s\S]*?\}(?=\s*$|\s*```)', response_text)
            if json_match:
                parsed = json.loads(json_match.group())
                # Validate content_category
                valid_categories = {"ffcpln_music", "personal_vlog", "ice_remix", "educational", "other"}
                if parsed.get("content_category") not in valid_categories:
                    parsed["content_category"] = "other"
                return parsed

            # Fallback: extract topics manually + detect category from keywords
            topics = re.findall(r'"([^"]+)"', response_text)
            category = "other"
            text_lower = response_text.lower()
            if any(kw in text_lower for kw in ["music", "instrumental", "beat", "melody"]):
                category = "ffcpln_music"
            elif any(kw in text_lower for kw in ["vlog", "talking", "personal", "daily"]):
                category = "personal_vlog"
            elif any(kw in text_lower for kw in ["ice", "immigration", "deport", "resist"]):
                category = "ice_remix"
            elif any(kw in text_lower for kw in ["tutorial", "how to", "learn", "explain"]):
                category = "educational"
            return {"topics": topics[:10], "segments": [], "content_category": category}
        except Exception as e:
            logger.warning(f"[STUDIO-ASK] JSON parse failed: {e}")
            return {"topics": [], "segments": [], "content_category": "other", "raw": response_text}
    
    def _first_element(self, selectors: List[str]):
        """Return the first element matching any selector in the list, else None."""
        for selector in selectors:
            try:
                el = self.driver.find_element("css selector", selector)
                if el:
                    return el
            except Exception:
                continue
        return None

    def _open_ask_studio(self) -> bool:
        """
        PRIMARY (Phase 1): open the Studio "Ask Studio" dialog from the header.

        Returns True if the header button was found and clicked AND the dialog
        + prompt box subsequently appear, False otherwise (so callers can fall
        back to the legacy watch-page / popup paths).
        """
        header_btn = self._first_element(self.ASK_STUDIO_SELECTORS["header_button"])
        if not header_btn:
            logger.info("[STUDIO-ASK] Ask Studio header button not found")
            return False
        try:
            header_btn.click()
        except Exception as e:
            logger.info(f"[STUDIO-ASK] Ask Studio header click failed: {e}")
            return False
        logger.info("[STUDIO-ASK] Clicked Ask Studio header button (PRIMARY)")
        return True

    @staticmethod
    def _is_refusal(text: str) -> bool:
        """True if the response text is an Ask Studio refusal / no-answer."""
        if not text:
            return False
        lowered = text.lower()
        return any(marker in lowered for marker in StudioAskIndexer.REFUSAL_MARKERS)

    async def _scrape_ask_response(self) -> str:
        """
        Scrape the Ask Studio response text, waiting for it to STABILIZE.

        The response streams in token-by-token. Grabbing the first non-empty
        text can capture a partial/streaming/canceled fragment. Instead we poll
        the response container and only return once the text STOPS GROWING for
        RESPONSE_STABLE_POLLS consecutive polls (completion signal) or
        RESPONSE_TIMEOUT_SECONDS elapses. NO clipboard - DOM text only.
        Returns the stabilized text ("" if the response never materialized).
        """
        import time as _time

        deadline = _time.monotonic() + self.RESPONSE_TIMEOUT_SECONDS
        response_text = ""
        stable_count = 0
        while _time.monotonic() < deadline:
            el = self._first_element(self.ASK_STUDIO_SELECTORS["response_stream"])
            text = ""
            if el is not None:
                try:
                    text = (el.text or "").strip()
                except Exception:
                    text = ""

            if text:
                if text == response_text:
                    # Text unchanged since last poll -> it may have completed.
                    stable_count += 1
                    if stable_count >= self.RESPONSE_STABLE_POLLS:
                        # Stabilized: stopped growing for N consecutive polls.
                        break
                else:
                    # Still streaming (grew/changed) -> reset the stability run.
                    response_text = text
                    stable_count = 0

            await self._human_delay(1.0, 0.2)
        return response_text

    def _type_prompt_human(self, prompt_box, prompt: str) -> None:
        """
        Enter the prompt into the contenteditable box mimicking 012's input
        behavior (REUSE human_behavior), NEWLINE-SAFE: no bare "\\n" ever reaches
        the box (a bare "\\n" == ENTER == a submit in this contenteditable).

        Internal "\\n" are converted to Shift+Enter SOFT newlines (ActionChains:
        SHIFT down -> ENTER -> SHIFT up) so multi-line structure is preserved
        WITHOUT submitting. Typing cadence reuses HumanBehavior (human_type /
        human_delay); falls back to per-char send_keys if human infra is absent.
        """
        # Focus the box (preserves test assertion prompt_box.clicked is True).
        try:
            prompt_box.click()
        except Exception:
            pass

        lines = (prompt or "").split("\n")
        for idx, line in enumerate(lines):
            if idx > 0:
                # SOFT newline between logical lines (NEVER a bare ENTER submit).
                self._soft_newline(prompt_box)
            if not line:
                continue
            if self.human is not None:
                # REUSE the proven 012 typing cadence (human_type), same infra
                # comment replies use. clear() only on the first line so soft
                # newlines aren't wiped.
                try:
                    if idx == 0:
                        self.human.human_type(prompt_box, line)
                    else:
                        for ch in line:
                            prompt_box.send_keys(ch)
                    continue
                except Exception:
                    # Fall through to plain per-char send_keys on any human-infra
                    # hiccup (keeps the single-submit guarantee intact).
                    pass
            for ch in line:
                prompt_box.send_keys(ch)

    def _soft_newline(self, element) -> None:
        """
        Emit a Shift+Enter SOFT newline (keeps multi-line structure WITHOUT
        submitting). Prefer ActionChains SHIFT-down/ENTER/SHIFT-up; fall back to
        element.send_keys((SHIFT, ENTER)) when ActionChains is unavailable.
        NEVER sends a bare ENTER here.
        """
        from selenium.webdriver.common.keys import Keys

        try:
            from selenium.webdriver.common.action_chains import ActionChains

            (
                ActionChains(self.driver)
                .key_down(Keys.SHIFT)
                .send_keys(Keys.ENTER)
                .key_up(Keys.SHIFT)
                .perform()
            )
        except Exception:
            try:
                element.send_keys(Keys.SHIFT, Keys.ENTER)
            except Exception:
                pass

    def _submit_ask_prompt(self, prompt_box) -> str:
        """
        Submit the typed prompt EXACTLY ONCE.

        PREFERRED: locate + click an Ask Studio send/submit button (mirror
        reply_executor's button-click submit). If no button is present, send
        EXACTLY ONE Keys.ENTER after the full prompt. Returns the method used
        ("button" or "enter") for observability/tests.
        """
        from selenium.webdriver.common.keys import Keys

        send_btn = self._first_element(self.ASK_STUDIO_SELECTORS["send_button"])
        if send_btn is not None:
            try:
                send_btn.click()
                return "button"
            except Exception as e:
                logger.info(f"[STUDIO-ASK] Send button click failed, using Enter: {e}")
        # Exactly ONE Enter after the full prompt is typed.
        prompt_box.send_keys(Keys.ENTER)
        return "enter"

    # =====================================================================
    # STEP 0 - BROWSER TARGET SELECTION (STUDIO_ASK_CHANNEL_CONTEXT_PHASE1)
    # =====================================================================
    @classmethod
    def _is_non_studio_target(cls, url: str) -> bool:
        """
        True if a window/tab URL is a Chrome side-panel / glic / Gemini panel /
        RotateCookiesPage target that must NEVER be used to Ask. (012 live-
        observed Selenium attach to chrome://glic first.)
        """
        if not url:
            return False
        low = url.strip().lower()
        return any(marker in low for marker in cls.NON_STUDIO_TARGET_URL_MARKERS)

    @classmethod
    def _is_acceptable_target(cls, url: str) -> bool:
        """
        True if a window/tab URL is a usable Ask target: a YouTube/Studio tab,
        or a NORMAL web tab the existing driver can navigate to Studio. Side-
        panel / glic / Gemini / RotateCookies targets are rejected.
        """
        if not url:
            return False
        if cls._is_non_studio_target(url):
            return False
        low = url.strip().lower()
        if any(low.startswith(p) for p in cls.ACCEPTABLE_TARGET_URL_PREFIXES):
            return True
        return any(low.startswith(p) for p in cls.ACCEPTABLE_NORMAL_URL_PREFIXES)

    @staticmethod
    def _is_studio_youtube_url(url: str) -> bool:
        """
        True ONLY if the URL host is EXACTLY studio.youtube.com. A prefix check
        like startswith("https://studio.youtube.com") is bypassable by a host
        such as https://studio.youtube.com.evil.com (CodeQL
        py/incomplete-url-substring-sanitization); parse + compare the host.
        """
        if not url:
            return False
        try:
            host = (urlparse(url.strip()).hostname or "").lower()
        except Exception:
            return False
        return host == "studio.youtube.com"

    def _select_studio_target(self) -> bool:
        """
        STEP 0: select/verify a browser window/tab that is YouTube Studio or a
        normal web target (NOT chrome://glic / a Gemini side panel /
        RotateCookiesPage / iframe-webview) BEFORE any channel-context
        navigation. Switches the driver to the first acceptable handle using
        the EXISTING Selenium window-handle idiom (mirrors
        foundups_selenium/devtools_mcp_adapter.list_pages :570-581); creates a
        normal tab via the existing driver only if every open handle is a
        side-panel target. Returns True if an acceptable target is active,
        False (-> studio_target_unavailable) otherwise. Never opens a NEW
        browser.
        """
        driver = self.driver
        # Single-target drivers (no multi-window API) -> verify the one URL.
        handles = getattr(driver, "window_handles", None)
        if not handles:
            try:
                current = driver.current_url
            except Exception:
                current = ""
            if self._is_acceptable_target(current):
                return True
            logger.warning(
                f"[STUDIO-ASK] STEP0 target reject (single target, url={current!r})"
            )
            return False

        # Prefer a handle already on Studio, then any acceptable normal target.
        studio_handle = None
        normal_handle = None
        for handle in handles:
            try:
                driver.switch_to.window(handle)
                url = driver.current_url or ""
            except Exception:
                continue
            if self._is_non_studio_target(url):
                # Explicit glic / Gemini panel / RotateCookies -> never use.
                continue
            if self._is_studio_youtube_url(url):
                studio_handle = handle
                break
            if normal_handle is None and self._is_acceptable_target(url):
                normal_handle = handle

        target = studio_handle or normal_handle
        if target is not None:
            try:
                driver.switch_to.window(target)
                logger.info(
                    f"[STUDIO-ASK] STEP0 selected Studio/normal target "
                    f"(studio={studio_handle is not None})"
                )
                return True
            except Exception as e:
                logger.warning(f"[STUDIO-ASK] STEP0 switch to target failed: {e}")
                return False

        # Every open handle is a side-panel target. Try to open a NORMAL tab via
        # the EXISTING driver (no new browser); fail closed if unsupported.
        try:
            driver.execute_script("window.open('about:blank');")
            new_handles = getattr(driver, "window_handles", []) or []
            for handle in new_handles:
                if handle in handles:
                    continue
                driver.switch_to.window(handle)
                if self._is_acceptable_target(driver.current_url or "about:blank"):
                    logger.info("[STUDIO-ASK] STEP0 opened normal tab via existing driver")
                    return True
        except Exception as e:
            logger.warning(f"[STUDIO-ASK] STEP0 could not open normal tab: {e}")
        logger.warning("[STUDIO-ASK] STEP0 no usable Studio/normal target (fail closed)")
        return False

    # =====================================================================
    # STEP 1/2 - CHANNEL CONTEXT + OBSERVABLE VERIFICATION
    # =====================================================================
    def _set_channel_context(self, channel_id: str) -> None:
        """
        STEP 1: set the OWNING channel as the active Studio context by
        navigating to the CHANNEL-SCOPED Studio URL (mirrors the batch path
        index_channel_videos :962 studio.youtube.com/channel/{id}/videos/upload)
        BEFORE the channel-agnostic /video/{id}/edit page. Reuses the same
        channel_id resolved from the registry; invents no second map.
        """
        context_url = f"https://studio.youtube.com/channel/{channel_id}/videos/upload"
        logger.info(f"[STUDIO-ASK] STEP1 setting channel context: {context_url}")
        self.driver.get(context_url)

    def _detect_wrong_context(self) -> bool:
        """
        True if the current page shows a permission / not-found / sign-in /
        account-switch / Oops signal (NOT the owning channel). Reads page title
        + a bounded body sample. URL-only proof is NOT trusted (STEP 2).
        """
        driver = self.driver
        try:
            title = (driver.title or "").lower()
        except Exception:
            title = ""
        if any(marker in title for marker in self.WRONG_CONTEXT_MARKERS):
            return True
        # Bounded body text sample (avoid scraping the whole DOM).
        body_text = ""
        try:
            body_el = driver.find_element("css selector", "body")
            body_text = (body_el.text or "")[:2000].lower()
        except Exception:
            body_text = ""
        return any(marker in body_text for marker in self.WRONG_CONTEXT_MARKERS)

    def _edit_surface_present(self) -> bool:
        """
        True if an owner/edit-surface element (the title field) is present on
        the Studio video-edit page. Reuses the SAME title selector the edit
        flow already relies on (ask_about_video title read).
        """
        try:
            el = self.driver.find_element(
                "css selector", "input#title-field, h1.title"
            )
            return el is not None
        except Exception:
            return False

    async def _verify_channel_context(self, video_id: str) -> bool:
        """
        STEP 2: OBSERVABLE owner-context verification AFTER navigating
        channel-scoped context -> /video/{id}/edit. NOT URL-only. Requires:
          - NO permission/not-found/sign-in/account-switch/Oops signal, AND
          - the edit surface (title field) present within the timeout.
        Returns True if the owning-channel edit surface is observably present;
        False (-> wrong_channel_context) otherwise.
        """
        import time as _time

        if self._detect_wrong_context():
            logger.warning(
                f"[STUDIO-ASK] STEP2 wrong-context page detected for {video_id}"
            )
            return False

        deadline = _time.monotonic() + self.RESPONSE_TIMEOUT_SECONDS
        while _time.monotonic() < deadline:
            if self._detect_wrong_context():
                logger.warning(
                    f"[STUDIO-ASK] STEP2 wrong-context appeared for {video_id}"
                )
                return False
            if self._edit_surface_present():
                return True
            await self._human_delay(1.0, 0.2)
        logger.warning(
            f"[STUDIO-ASK] STEP2 edit surface absent after timeout for {video_id}"
        )
        return False

    async def ask_about_video(
        self,
        video_id: str,
        prompt: Optional[str] = None,
        channel_entry: Optional[Dict[str, Any]] = None,
        channel_id: Optional[str] = None,
    ) -> AskResult:
        """
        Use the YouTube Studio "Ask Studio" feature to index a specific video.

        Phase 1 PRIMARY path (STUDIO_ASK_CHANNEL_CONTEXT_PHASE1 ordering):
          select Studio TARGET (STEP 0) -> set OWNING-channel context via the
          channel-scoped URL (STEP 1) -> /video/{id}/edit -> OBSERVABLE
          verify (STEP 2) -> Ask Studio header button -> dialog/chat stream ->
          contenteditable prompt -> single submit -> DOM-scraped response.

        Legacy watch-page Ask / Studio popup menu are kept ONLY as fallback.

        Args:
            video_id: YouTube video ID
            prompt: Optional channel-specific prompt (defaults to ASK_PROMPT or
                    the prompt resolved from channel_entry).
            channel_entry: Optional channel registry entry; used to pick the
                    channel-specific prompt via description_template AND (when
                    channel_id is not passed) to resolve the OWNING channel_id.
            channel_id: REQUIRED owning channel ID for single-video Ask. Resolved
                    from channel_entry["id"] when omitted. If neither yields a
                    registry-known channel -> fail closed "channel_unresolved".
                    (Backward-compatible optional kwarg; NOT a new public action
                    arg + NO #819 action-id/output-schema change.)

        Returns:
            AskResult. success=False (fail-closed, NOTHING persisted) on:
            channel_unresolved, studio_target_unavailable, wrong_channel_context,
            response timeout, or a refusal.
        """
        import asyncio

        if not self.driver:
            return AskResult(
                video_id=video_id,
                title="",
                response_text="",
                topics=[],
                timestamps=[],
                success=False,
                error="No browser driver available"
            )

        # STEP 3 - channel_id REQUIRED (NO guessing from body/path/video URL).
        # Resolve the OWNING channel_id from the explicit kwarg, else the passed
        # registry entry's id. Then CONFIRM it is a registry-known channel
        # (get_channel_by_id). Missing / blank / unknown -> fail closed
        # "channel_unresolved". An EXPLICITLY-passed channel_entry is preserved
        # for PROMPT selection (ownership comes from channel_id; prompt comes
        # from the caller's entry when supplied).
        resolved_channel_id = (channel_id or "").strip()
        if not resolved_channel_id and channel_entry:
            resolved_channel_id = str(channel_entry.get("id") or "").strip()
        owning_entry = (
            get_channel_by_id(resolved_channel_id) if resolved_channel_id else None
        )
        if not resolved_channel_id or owning_entry is None:
            logger.warning(
                f"[STUDIO-ASK] {video_id}: channel_id unresolved (fail closed)"
            )
            return AskResult(
                video_id=video_id,
                title="",
                response_text="",
                topics=[],
                timestamps=[],
                success=False,
                error="channel_unresolved",
            )
        # Prompt selection uses the caller's explicit entry if given, else the
        # registry entry resolved from the owning channel_id.
        if channel_entry is None:
            channel_entry = owning_entry

        # Resolve the prompt: explicit > channel-specific > generic default.
        ask_prompt = prompt or self._prompt_for_channel(channel_entry)

        # WSP 84 REUSE: lazily attach the proven 012 input behavior (same infra
        # the YT comment replies use: comment_engagement_dae -> get_human_behavior).
        if self.human is None and HUMAN_BEHAVIOR_AVAILABLE and get_human_behavior is not None:
            try:
                self.human = get_human_behavior(self.driver)
            except Exception as e:  # pragma: no cover - defensive
                logger.info(f"[STUDIO-ASK] human behavior init skipped: {e}")

        try:
            from selenium.webdriver.common.keys import Keys

            # STEP 0 - BROWSER TARGET SELECTION (before ANY channel nav). Reject
            # chrome://glic / Gemini side panel / RotateCookiesPage. Fail closed.
            if not self._select_studio_target():
                logger.warning(
                    f"[STUDIO-ASK] {video_id}: no Studio target (fail closed)"
                )
                return AskResult(
                    video_id=video_id,
                    title="",
                    response_text="",
                    topics=[],
                    timestamps=[],
                    success=False,
                    error="studio_target_unavailable",
                )

            # STEP 1 - SET OWNING-CHANNEL CONTEXT via the channel-scoped URL
            # (mirror the batch path) BEFORE the channel-agnostic edit page.
            self._set_channel_context(resolved_channel_id)
            await self._human_delay(3.0, 0.4)

            # PRIMARY: navigate to the Studio video-edit page (Ask Studio lives here).
            studio_url = f"https://studio.youtube.com/video/{video_id}/edit"
            logger.info(f"[STUDIO-ASK] Navigating to {studio_url}")
            self.driver.get(studio_url)
            await self._human_delay(3.0, 0.4)

            # STEP 2 - OBSERVABLE channel verification (NOT URL-only). Fail
            # closed "wrong_channel_context" on permission/not-found/sign-in/
            # account-switch/Oops or an absent edit surface.
            if not await self._verify_channel_context(video_id):
                return AskResult(
                    video_id=video_id,
                    title="",
                    response_text="",
                    topics=[],
                    timestamps=[],
                    success=False,
                    error="wrong_channel_context",
                )

            # Studio title is in the title input field.
            title = ""
            try:
                title_el = self.driver.find_element("css selector", "input#title-field, h1.title")
                title = title_el.get_attribute("value") or title_el.text
            except Exception:
                pass

            used_ask_studio = False
            ask_clicked = False

            # ---- PRIMARY PATH: Ask Studio header button + dialog ----
            if self._open_ask_studio():
                await self._human_delay(2.0, 0.3)
                # Confirm the dialog appeared, then find the contenteditable prompt box.
                dialog = self._first_element(self.ASK_STUDIO_SELECTORS["dialog"])
                prompt_box = self._first_element(self.ASK_STUDIO_SELECTORS["prompt_box"])
                if dialog is not None and prompt_box is not None:
                    try:
                        # NEWLINE-SAFE human-cadence typing (no bare "\n" -> no
                        # implicit ENTER per line), then submit EXACTLY ONCE.
                        self._type_prompt_human(prompt_box, ask_prompt)
                        await self._human_delay(1.0, 0.2)
                        submit_via = self._submit_ask_prompt(prompt_box)
                        logger.info(
                            f"[STUDIO-ASK] Submitted prompt via Ask Studio dialog (submit={submit_via})"
                        )
                        ask_clicked = True
                        used_ask_studio = True
                    except Exception as e:
                        logger.warning(f"[STUDIO-ASK] Ask Studio prompt entry failed: {e}")
                else:
                    logger.info("[STUDIO-ASK] Ask Studio dialog/prompt box not found - falling back")

            # ---- FALLBACK PATH: legacy watch-page Ask + Studio popup menu ----
            if not used_ask_studio:
                logger.info("[STUDIO-ASK] FALLBACK: legacy watch-page / popup Ask path")
                # Navigate to watch page for the legacy direct Ask button.
                watch_url = f"https://www.youtube.com/watch?v={video_id}"
                self.driver.get(watch_url)
                await self._human_delay(3.0, 0.4)
                if not title:
                    try:
                        title_el = self.driver.find_element(
                            "css selector",
                            "h1.ytd-watch-metadata, yt-formatted-string.ytd-watch-metadata",
                        )
                        title = title_el.text
                    except Exception:
                        pass

                # FALLBACK A: watch-page Ask button via JS.
                ask_button = self.driver.execute_script("""
                    const flexItems = document.querySelector('#flexible-item-buttons');
                    if (flexItems) {
                        const viewModels = flexItems.querySelectorAll('yt-button-view-model');
                        for (let vm of viewModels) {
                            const text = (vm.textContent || vm.innerText || '').toLowerCase().trim();
                            if (text === 'ask') {
                                const btn = vm.querySelector('button-view-model button.yt-spec-button-shape-next')
                                         || vm.querySelector('button.yt-spec-button-shape-next')
                                         || vm.querySelector('button');
                                if (btn) return btn;
                            }
                        }
                    }
                    const askByLabel = document.querySelector('button[aria-label*="Ask"]');
                    if (askByLabel) return askByLabel;
                    return null;
                """)
                if ask_button:
                    try:
                        ask_button.click()
                        ask_clicked = True
                        logger.info("[STUDIO-ASK] FALLBACK: clicked watch-page Ask button")
                        await self._human_delay(2.0, 0.3)
                    except Exception:
                        ask_clicked = False

                # FALLBACK B: Studio popup menu Ask item.
                if not ask_clicked:
                    menu_selectors = [
                        "ytd-menu-renderer button",
                        "button[aria-label='More actions']",
                        "#button-shape button",
                        "yt-icon-button#button",
                    ]
                    menu_clicked = False
                    for selector in menu_selectors:
                        try:
                            menu_btn = self.driver.find_element("css selector", selector)
                            menu_btn.click()
                            menu_clicked = True
                            break
                        except Exception:
                            continue
                    if menu_clicked:
                        await self._human_delay(1.5, 0.3)
                        ask_item = self.driver.execute_script("""
                            const items = document.querySelectorAll('tp-yt-paper-item');
                            for (let item of items) {
                                if (item.textContent.trim().toLowerCase() === 'ask') {
                                    return item;
                                }
                            }
                            return null;
                        """)
                        if ask_item:
                            try:
                                ask_item.click()
                                ask_clicked = True
                                logger.info("[STUDIO-ASK] FALLBACK: clicked Studio popup Ask item")
                                await self._human_delay(2.0, 0.3)
                            except Exception:
                                ask_clicked = False

                # Legacy fallback: type into textarea/input and submit.
                if ask_clicked:
                    try:
                        ask_input = self.driver.find_element(
                            "css selector", "textarea, input[placeholder*='Ask']"
                        )
                        try:
                            ask_input.clear()
                        except Exception:
                            pass
                        # SAME single-submit/human-type fix as the primary path:
                        # newline-safe typing (no bare "\n" -> no implicit ENTER),
                        # then submit EXACTLY ONCE (button if present, else 1 Enter).
                        self._type_prompt_human(ask_input, ask_prompt)
                        await self._human_delay(1.0, 0.2)
                        submit_via = self._submit_ask_prompt(ask_input)
                        logger.info(
                            f"[STUDIO-ASK] FALLBACK submitted prompt (submit={submit_via})"
                        )
                    except Exception as e:
                        logger.warning(f"[STUDIO-ASK] FALLBACK input entry failed: {e}")
                        ask_clicked = False

            if not ask_clicked:
                return AskResult(
                    video_id=video_id,
                    title=title,
                    response_text="",
                    topics=[],
                    timestamps=[],
                    success=False,
                    error="Could not open Ask Studio or any fallback Ask path",
                )

            # ---- Scrape the response from DOM (NO clipboard). Fails closed. ----
            if used_ask_studio:
                response_text = await self._scrape_ask_response()
            else:
                # Legacy fallback: wait then scrape legacy response containers.
                await self._human_delay(5.0, 0.5)
                response_text = ""
                try:
                    response_el = self.driver.find_element(
                        "css selector", ".gemini-response, .response-content"
                    )
                    response_text = (response_el.text or "").strip()
                except Exception:
                    response_text = ""
                if not response_text:
                    # As a last resort scrape the Ask Studio stream selectors too.
                    response_text = await self._scrape_ask_response()

            if not response_text:
                # Response never materialized within the timeout -> FAIL CLOSED.
                logger.warning(f"[STUDIO-ASK] {video_id}: no response within timeout (fail closed)")
                return AskResult(
                    video_id=video_id,
                    title=title,
                    response_text="",
                    topics=[],
                    timestamps=[],
                    success=False,
                    error="Ask Studio response timeout (no DOM text)",
                )

            # FAIL CLOSED on a refusal / no-answer: never persist a refusal as
            # index content (transcript_summary). success=False, store nothing.
            if self._is_refusal(response_text):
                logger.warning(
                    f"[STUDIO-ASK] {video_id}: Ask Studio refusal/no-answer (fail closed)"
                )
                return AskResult(
                    video_id=video_id,
                    title=title,
                    response_text="",
                    topics=[],
                    timestamps=[],
                    success=False,
                    error="ask_studio_no_answer",
                )

            # Parse response
            parsed = self._parse_ask_response(response_text)
            content_category = parsed.get("content_category", "other")
            logger.info(f"[STUDIO-ASK] Content category detected: {content_category}")

            return AskResult(
                video_id=video_id,
                title=title,
                response_text=response_text,
                topics=parsed.get("topics", []),
                timestamps=parsed.get("segments", []),
                success=True,
                content_category=content_category,
            )

        except Exception as e:
            logger.error(f"[STUDIO-ASK] Error for {video_id}: {e}")
            return AskResult(
                video_id=video_id,
                title="",
                response_text="",
                topics=[],
                timestamps=[],
                success=False,
                error=str(e)
            )

    async def index_channel_videos(
        self,
        channel_id: str,
        max_videos: Optional[int] = None,
        force_reindex: bool = False,
    ) -> Dict[str, Any]:
        """
        Index videos for a channel using Ask Gemini.
        
        Args:
            channel_id: YouTube channel ID
            max_videos: Override max videos to index
            
        Returns:
            Summary of indexing results
        """
        import asyncio
        
        max_videos = max_videos or self.max_videos_per_cycle
        results = []
        skipped = 0
        
        channel_entry = get_channel_by_id(channel_id)
        channel_key = (channel_entry or {}).get("key") or channel_id or "unknown"
        channel_name = (channel_entry or {}).get("name", channel_key)

        logger.info(f"[STUDIO-ASK] Starting video indexing for channel {channel_id} ({channel_name})")
        logger.info(f"[STUDIO-ASK] Max videos: {max_videos}")
        
        if not self.driver:
            return {"error": "No browser driver", "indexed": 0}
        
        try:
            # Navigate to channel content page
            content_url = f"https://studio.youtube.com/channel/{channel_id}/videos/upload"
            logger.info(f"[STUDIO-ASK] Navigating to: {content_url}")
            self.driver.get(content_url)
            await self._human_delay(3.0, 0.4)

            # OLDEST FIRST: Click sort dropdown and select "Date (oldest)"
            # This ensures we process oldest videos first (building knowledge base chronologically)
            logger.info("[STUDIO-ASK] Sorting by oldest first...")
            try:
                # Use JavaScript to find and click sort dropdown, then select oldest
                sorted_ok = self.driver.execute_script("""
                    // Find sort button/dropdown
                    const sortButtons = document.querySelectorAll(
                        'ytcp-dropdown-trigger, button[aria-label*="Sort"], #sort-menu-button, ' +
                        '[icon="icons:filter-list"], ytcp-icon-button[icon="icons:filter-list"]'
                    );

                    for (const btn of sortButtons) {
                        if (btn.textContent.toLowerCase().includes('date') ||
                            btn.getAttribute('aria-label')?.toLowerCase().includes('sort')) {
                            btn.click();
                            return 'clicked_sort';
                        }
                    }
                    return 'no_sort_button';
                """)

                if sorted_ok == 'clicked_sort':
                    await self._human_delay(1.0, 0.2)

                    # Find and click "oldest" option
                    oldest_clicked = self.driver.execute_script("""
                        const items = document.querySelectorAll(
                            'tp-yt-paper-item, ytcp-text-menu-item, ytcp-ve, paper-item'
                        );
                        for (const item of items) {
                            const text = item.textContent.toLowerCase();
                            if (text.includes('oldest') || text.includes('date (oldest)')) {
                                item.click();
                                return true;
                            }
                        }
                        return false;
                    """)

                    if oldest_clicked:
                        await self._human_delay(2.0, 0.3)
                        logger.info("[STUDIO-ASK] ✓ Sorted by oldest")
                    else:
                        logger.warning("[STUDIO-ASK] Could not find 'oldest' option")
                else:
                    logger.warning("[STUDIO-ASK] Could not find sort button")

            except Exception as e:
                logger.warning(f"[STUDIO-ASK] Sort failed (using default order): {e}")
                # Continue with default order - better than failing

            # Get list of video IDs (PRIORITIZE: LIVE > Regular, skip Shorts)
            # 2026-03-18: Added LIVE prioritization and Shorts filtering
            video_ids = []
            live_videos = []
            regular_videos = []
            try:
                video_rows = self.driver.find_elements("css selector", "ytcp-video-row, tr.style-scope")
                for row in video_rows:
                    try:
                        link = row.find_element("css selector", "a[href*='/video/']")
                        href = link.get_attribute("href")
                        vid_id = self._extract_video_id_from_url(href)
                        if not vid_id:
                            continue

                        # Get row text to detect LIVE/Shorts
                        row_text = row.text.lower()

                        # Skip Shorts (they have limited content value for indexing)
                        if "short" in row_text or "#short" in row_text:
                            continue

                        # Detect LIVE/Premiered videos (higher priority)
                        is_live = any(kw in row_text for kw in ["live", "streamed", "premiered", "stream"])

                        if is_live:
                            live_videos.append(vid_id)
                        else:
                            regular_videos.append(vid_id)
                    except Exception:
                        continue

                # PRIORITY ORDER: LIVE first, then regular videos
                video_ids = live_videos + regular_videos
                video_ids = video_ids[:max_videos]  # Apply limit after prioritization

                if live_videos:
                    logger.info(f"[STUDIO-ASK] Found {len(live_videos)} LIVE videos (prioritized)")

            except Exception as e:
                logger.warning(f"[STUDIO-ASK] Failed to get video list: {e}")
            
            if not video_ids:
                return {"error": "No videos found", "indexed": 0}
            
            logger.info(f"[STUDIO-ASK] Found {len(video_ids)} videos to index")
            
            # Index each video
            index_root = INDEX_ROOT
            store = VideoIndexStore(base_path=str(index_root / channel_key))
            for vid_id in video_ids:
                if not force_reindex and self._index_exists(index_root, channel_key, vid_id):
                    skipped += 1
                    logger.info(f"[STUDIO-ASK] ⏭️ {vid_id}: already indexed")
                    continue
                result = await self.ask_about_video(
                    vid_id, channel_entry=channel_entry, channel_id=channel_id
                )
                results.append(result)
                
                if result.success:
                    logger.info(f"[STUDIO-ASK] ✅ {vid_id}: {len(result.topics)} topics")
                    
                    # Persist Ask results as JSON artifacts for indexing continuity
                    index_data = self._ask_result_to_index_data(result, channel_key=channel_key)
                    store.save_index(vid_id, index_data)
                else:
                    logger.warning(f"[STUDIO-ASK] ❌ {vid_id}: {result.error}")
                
                await self._human_delay(2.0, 0.3)
            
            # Summary
            indexed = sum(1 for r in results if r.success)
            return {
                "channel_id": channel_id,
                "indexed": indexed,
                "skipped": skipped,
                "failed": len(results) - indexed,
                "videos": [r.video_id for r in results if r.success],
            }
            
        except Exception as e:
            logger.error(f"[STUDIO-ASK] Channel indexing failed: {e}")
            return {"error": str(e), "indexed": 0}


async def run_video_indexing_cycle(
    driver=None,
    channels: Optional[List[str]] = None,
    max_videos_per_channel: int = 3,
    browser: str = "chrome",
) -> Dict[str, Any]:
    """
    Run one cycle of video indexing across all channels.

    Called by auto_moderator_dae after comment engagement completes.

    Args:
        driver: Selenium WebDriver (if None, will connect based on browser param)
        channels: List of channel IDs (defaults to env vars)
        max_videos_per_channel: Max videos to index per channel (9999 = all)
        browser: "chrome" (port 9222) or "edge" (port 9223)

    Returns:
        Summary of indexing cycle
    """
    if not os.getenv("YT_VIDEO_INDEXING_ENABLED", "true").lower() in ("1", "true", "yes"):
        logger.info("[VIDEO-INDEX] Video indexing disabled (YT_VIDEO_INDEXING_ENABLED)")
        return {"skipped": True}
    if _stop_active():
        logger.warning("[VIDEO-INDEX] STOP file active (memory/STOP_VIDEO_INDEXER)")
        return {"skipped": True, "reason": "STOP file active"}

    # 2026-03-10: CRITICAL FIX - Filter channels by browser to prevent OOPS
    # Chrome (9222): Move2Japan, UnDaoDu (Set 1)
    # Edge (9223): FoundUps, antifaFM (Set 10)
    # Trying to index an Edge channel on Chrome causes OOPS (wrong account)
    if not channels:
        try:
            from modules.infrastructure.shared_utilities.youtube_channel_registry import (
                group_channels_by_browser,
            )
            grouped = group_channels_by_browser(role="indexing")
            browser_channels = grouped.get(browser.lower(), [])
            channels = [ch.get("id") for ch in browser_channels if ch.get("id")]
            logger.info(f"[VIDEO-INDEX] Filtered to {browser.upper()} channels: {[ch.get('key') for ch in browser_channels]}")
        except ImportError:
            # Fallback to hardcoded if registry unavailable
            if browser.lower() == "chrome":
                channels = [
                    os.getenv("MOVE2JAPAN_CHANNEL_ID", "UC-LSSlOZwpGIRIYihaz8zCw"),
                    os.getenv("UNDAODU_CHANNEL_ID", "UCfHM9Fw9HD-NwiS0seD_oIA"),
                ]
            else:
                channels = [
                    os.getenv("FOUNDUPS_CHANNEL_ID", "UCSNTUXjAgpd4sgWYP0xoJgw"),
                    os.getenv("ANTIFAFM_CHANNEL_ID", "UCVSmg5aOhP4tnQ9KFUg97qA"),
                ]
        channels = [c for c in channels if c]

    logger.info("=" * 60)
    logger.info(f"[VIDEO-INDEX] Starting video indexing cycle ({browser.upper()})")
    logger.info(f"[VIDEO-INDEX] Channels: {len(channels)}")
    logger.info(f"[VIDEO-INDEX] Max videos per channel: {max_videos_per_channel}")
    logger.info("=" * 60)

    # Connect to browser if no driver provided
    # HARDENED: Use retry helpers with DevTools verification (2026-02-22)
    if driver is None:
        try:
            from modules.infrastructure.dependency_launcher.src.dae_dependencies import (
                connect_chrome_with_retry,
                connect_edge_with_retry,
            )

            if browser.lower() == "edge":
                logger.info("[VIDEO-INDEX] Connecting to Edge with retry...")
                driver = connect_edge_with_retry(max_retries=3, retry_delay=2.0)
                if driver is None:
                    logger.error("[VIDEO-INDEX] Edge connection failed after retries")
                    return {"error": "Edge connection failed", "total_indexed": 0}
                logger.info("[VIDEO-INDEX] Connected to Edge (with retry)")
            else:
                logger.info("[VIDEO-INDEX] Connecting to Chrome with retry...")
                driver = connect_chrome_with_retry(max_retries=3, retry_delay=2.0)
                if driver is None:
                    logger.error("[VIDEO-INDEX] Chrome connection failed after retries")
                    return {"error": "Chrome connection failed", "total_indexed": 0}
                logger.info("[VIDEO-INDEX] Connected to Chrome (with retry)")
        except Exception as e:
            logger.error(f"[VIDEO-INDEX] Failed to connect to {browser}: {e}")
            return {"error": str(e), "total_indexed": 0}

    indexer = StudioAskIndexer(
        driver=driver,
        max_videos_per_cycle=max_videos_per_channel
    )

    counts_before = _count_indexed_by_channel(INDEX_ROOT)
    force_reindex = _consume_reindex_signal()

    results = {}
    for channel_id in channels:
        result = await indexer.index_channel_videos(
            channel_id,
            force_reindex=force_reindex,
        )
        results[channel_id] = result
        logger.info(f"[VIDEO-INDEX] {channel_id}: {result.get('indexed', 0)} videos indexed")

    total_indexed = sum(r.get("indexed", 0) for r in results.values())
    total_skipped = sum(r.get("skipped", 0) for r in results.values())
    counts_after = _count_indexed_by_channel(INDEX_ROOT)
    indexed_delta = {k: counts_after.get(k, 0) - counts_before.get(k, 0) for k in counts_after}
    logger.info(f"[VIDEO-INDEX] Cycle complete: {total_indexed} videos indexed")
    logger.info(f"[VIDEO-INDEX] Skip count: {total_skipped}")

    # 2026-02-05: GEMINI ANALYSIS PASS — analyze newly indexed videos via Gemini 2.5 Flash.
    # Extracts topics, segments, transcript → generates hashtag suggestions.
    # Gated: only runs if Gemini API key is configured and videos were indexed.
    gemini_results = {}
    if total_indexed > 0 and os.getenv("GEMINI_API_KEY"):
        try:
            from modules.ai_intelligence.video_indexer.src.gemini_video_analyzer import (
                GeminiVideoAnalyzer,
                save_analysis_result,
                suggest_hashtags,
            )
            analyzer = GeminiVideoAnalyzer()
            logger.info(f"[VIDEO-INDEX] Running Gemini analysis on {total_indexed} newly indexed videos...")

            for channel_id, ch_result in results.items():
                video_ids = ch_result.get("videos", [])
                for vid in video_ids[:max_videos_per_channel]:
                    try:
                        analysis = analyzer.analyze_video(vid)
                        if analysis.success:
                            # Save to HoloIndex
                            save_analysis_result(analysis, index_to_holoindex=True)

                            # Generate hashtag suggestions
                            tags = suggest_hashtags(analysis)
                            logger.info(f"[VIDEO-INDEX] {vid}: {len(analysis.segments)} segments, "
                                        f"{len(analysis.topics)} topics, {len(tags)} hashtags suggested")
                            gemini_results[vid] = {
                                "topics": analysis.topics,
                                "hashtags": tags,
                                "segments": len(analysis.segments),
                                "success": True,
                            }
                        else:
                            logger.warning(f"[VIDEO-INDEX] Gemini analysis failed for {vid}: {analysis.error}")
                            gemini_results[vid] = {"success": False, "error": analysis.error}
                    except Exception as gemini_err:
                        logger.warning(f"[VIDEO-INDEX] Gemini error for {vid}: {gemini_err}")
                        gemini_results[vid] = {"success": False, "error": str(gemini_err)}
        except ImportError as ie:
            logger.info(f"[VIDEO-INDEX] Gemini analyzer not available: {ie}")
        except Exception as e:
            logger.warning(f"[VIDEO-INDEX] Gemini analysis pass failed: {e}")

    return {
        "total_indexed": total_indexed,
        "total_skipped": total_skipped,
        "channels": results,
        "gemini_analysis": gemini_results,
        "index_counts_before": counts_before,
        "index_counts_after": counts_after,
        "index_counts_delta": indexed_delta,
        "force_reindex": force_reindex,
        "timestamp": datetime.now().isoformat(),
    }


async def run_indexing_daemon(
    channels: Optional[List[str]] = None,
    max_videos_per_channel: int = 3,
    browser: str = "chrome",
    interval_minutes: int = 60,
    max_cycles: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run continuous indexing cycles with STOP/reindex signals.
    """
    cycles = 0
    last_result: Dict[str, Any] = {}
    logger.info("[VIDEO-INDEX] Daemon started")

    while True:
        if _stop_active():
            logger.warning("[VIDEO-INDEX] Daemon stopped (STOP file active)")
            break

        last_result = await run_video_indexing_cycle(
            channels=channels,
            max_videos_per_channel=max_videos_per_channel,
            browser=browser,
        )
        cycles += 1

        if max_cycles and cycles >= max_cycles:
            logger.info("[VIDEO-INDEX] Daemon reached max cycles")
            break

        sleep_seconds = max(60, int(interval_minutes * 60))
        logger.info(f"[VIDEO-INDEX] Daemon sleeping for {sleep_seconds}s")
        for _ in range(0, sleep_seconds, 10):
            if _stop_active():
                break
            await asyncio.sleep(10)
        if _stop_active():
            logger.warning("[VIDEO-INDEX] Daemon stopped during sleep")
            break

    return {
        "cycles": cycles,
        "last_result": last_result,
        "timestamp": datetime.now().isoformat(),
    }
