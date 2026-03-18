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

from modules.infrastructure.shared_utilities.youtube_channel_registry import get_channel_by_id
from modules.ai_intelligence.video_indexer.src.video_index_store import (
    VideoIndexStore,
    IndexData,
)

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
    
    # Selectors for YouTube (Watch Page AND Studio)
    SELECTORS = {
        "content_tab": "a[href*='/channel/'][href*='/videos']",
        "video_row": "ytcp-video-row",
        "video_title": "a#video-title",

        # WATCH PAGE: Ask button is in #actions > ytd-menu-renderer > #flexible-item-buttons
        "watch_ask_button": "#flexible-item-buttons button, yt-button-view-model button",
        "watch_actions": "#actions ytd-menu-renderer",

        # STUDIO PAGE: Menu trigger to open popup where Ask lives
        "studio_menu_trigger": "ytd-menu-renderer button, button[aria-label='More actions'], #button-shape button",
        # Ask button is inside popup menu as tp-yt-paper-item
        "studio_ask_popup_item": "tp-yt-paper-item.style-scope.ytd-menu-service-item-renderer",
        "popup_menu": "ytd-menu-popup-renderer, tp-yt-iron-dropdown",

        # Gemini chat interface (after clicking Ask)
        "ask_input": "textarea[placeholder*='Ask'], input[placeholder*='Ask'], .gemini-input textarea",
        "ask_response": ".gemini-response, .ask-response-content, .gemini-chat-response",
        "video_details_link": "a[href*='/video/'][href*='/edit']",
    }

    # Watch page is simpler (direct button), prefer it over Studio
    USE_WATCH_PAGE = True
    
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
    
    async def ask_about_video(self, video_id: str) -> AskResult:
        """
        Use Ask Gemini feature for a specific video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            AskResult with parsed response
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
        
        try:
            # Navigate to video page (watch page preferred for simpler Ask button)
            if self.USE_WATCH_PAGE:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
            else:
                video_url = f"https://studio.youtube.com/video/{video_id}/edit"
            logger.info(f"[STUDIO-ASK] Navigating to {video_url}")
            self.driver.get(video_url)
            await self._human_delay(3.0, 0.4)
            
            # Determine which page we're on and get title
            title = ""
            is_watch_page = "youtube.com/watch" in self.driver.current_url

            if is_watch_page:
                # WATCH PAGE: Title is in different location
                try:
                    title_el = self.driver.find_element("css selector", "h1.ytd-watch-metadata, yt-formatted-string.ytd-watch-metadata")
                    title = title_el.text
                except Exception:
                    pass
            else:
                # STUDIO PAGE: Title is in input field
                try:
                    title_el = self.driver.find_element("css selector", "input#title-field, h1.title")
                    title = title_el.get_attribute("value") or title_el.text
                except Exception:
                    pass

            ask_clicked = False

            if is_watch_page or self.USE_WATCH_PAGE:
                # WATCH PAGE APPROACH: Direct button in #flexible-item-buttons
                # Per 012 DOM: #actions > ytd-menu-renderer > #flexible-item-buttons > yt-button-view-model > button
                logger.info("[STUDIO-ASK] Trying watch page Ask button approach")

                # Find Ask button by JavaScript (most reliable for dynamic YT elements)
                # Full watch page DOM: #flexible-item-buttons > yt-button-view-model > button-view-model > button.yt-spec-button-shape-next
                ask_button = self.driver.execute_script("""
                    // Method 1: Precise path from 012's DOM inspection
                    const flexItems = document.querySelector('#flexible-item-buttons');
                    if (flexItems) {
                        const viewModels = flexItems.querySelectorAll('yt-button-view-model');
                        for (let vm of viewModels) {
                            const text = (vm.textContent || vm.innerText || '').toLowerCase().trim();
                            if (text === 'ask') {
                                // Get the button inside: button-view-model > button.yt-spec-button-shape-next
                                const btn = vm.querySelector('button-view-model button.yt-spec-button-shape-next')
                                         || vm.querySelector('button.yt-spec-button-shape-next')
                                         || vm.querySelector('button');
                                if (btn) return btn;
                            }
                        }
                    }
                    // Method 2: Find by aria-label
                    const askByLabel = document.querySelector('button[aria-label*="Ask"]');
                    if (askByLabel) return askByLabel;
                    // Method 3: Broader search - any button with Ask text in actions area
                    const actionsArea = document.querySelector('#actions-inner, #menu');
                    if (actionsArea) {
                        const buttons = actionsArea.querySelectorAll('button.yt-spec-button-shape-next');
                        for (let btn of buttons) {
                            const parent = btn.closest('yt-button-view-model');
                            if (parent && parent.textContent.toLowerCase().includes('ask')) {
                                return btn;
                            }
                        }
                    }
                    return null;
                """)

                if ask_button:
                    ask_button.click()
                    ask_clicked = True
                    logger.info("[STUDIO-ASK] Clicked Ask button on watch page")
                    await self._human_delay(2.0, 0.3)

            if not ask_clicked:
                # STUDIO PAGE FALLBACK: Open menu popup, find Ask item
                logger.info("[STUDIO-ASK] Falling back to Studio popup menu approach")

                # Step 1: Open the menu popup
                menu_clicked = False
                menu_selectors = [
                    "ytd-menu-renderer button",
                    "button[aria-label='More actions']",
                    "#button-shape button",
                    "yt-icon-button#button",
                ]
                for selector in menu_selectors:
                    try:
                        menu_btn = self.driver.find_element("css selector", selector)
                        menu_btn.click()
                        menu_clicked = True
                        logger.info(f"[STUDIO-ASK] Clicked menu via: {selector}")
                        break
                    except Exception:
                        continue

                if not menu_clicked:
                    return AskResult(
                        video_id=video_id,
                        title=title,
                        response_text="",
                        topics=[],
                        timestamps=[],
                        success=False,
                        error="Menu trigger not found"
                    )

                await self._human_delay(1.5, 0.3)  # Wait for popup

                # Step 2: Find "Ask" item inside popup menu by text content
                ask_item = self.driver.execute_script("""
                    const items = document.querySelectorAll('tp-yt-paper-item');
                    for (let item of items) {
                        if (item.textContent.trim().toLowerCase() === 'ask') {
                            return item;
                        }
                    }
                    return null;
                """)

                if not ask_item:
                    return AskResult(
                        video_id=video_id,
                        title=title,
                        response_text="",
                        topics=[],
                        timestamps=[],
                        success=False,
                        error="Ask menu item not found in popup"
                    )

                # Step 3: Click Ask item
                ask_item.click()
                ask_clicked = True
                logger.info("[STUDIO-ASK] Clicked 'Ask' menu item in popup")
                await self._human_delay(2.0, 0.3)

            if not ask_clicked:
                return AskResult(
                    video_id=video_id,
                    title=title,
                    response_text="",
                    topics=[],
                    timestamps=[],
                    success=False,
                    error="Could not click Ask button via any method"
                )
            
            # Find input field and type prompt
            ask_input = self.driver.find_element("css selector", "textarea, input[placeholder*='Ask']")
            ask_input.clear()
            ask_input.send_keys(self.ASK_PROMPT)
            await self._human_delay(1.0, 0.2)
            
            # Submit (Enter key or submit button)
            from selenium.webdriver.common.keys import Keys
            ask_input.send_keys(Keys.ENTER)
            await self._human_delay(5.0, 0.5)  # Wait for Gemini response
            
            # Get response text
            response_text = ""
            try:
                response_el = self.driver.find_element("css selector", ".gemini-response, .response-content")
                response_text = response_el.text
            except Exception:
                # Try to get any new text on page
                response_text = self.driver.find_element("css selector", "body").text[-2000:]
            
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
                result = await self.ask_about_video(vid_id)
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
