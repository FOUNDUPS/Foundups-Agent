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

# WSP 84 REUSE: shadow-DOM deep finder (returns REAL WebElements). YouTube Studio
# is shadow-rooted, so flat find_element silently fails on the live page even
# when the element exists (#817 fixed selector NAMES but not the TRAVERSAL model).
# first_deep tries shadow-piercing CSS chains FIRST, then a flat fallback - so the
# PRIMARY path is shadow traversal while light-DOM pages still resolve.
try:
    from modules.infrastructure.foundups_selenium.src.shadow_dom_finder import (
        find_deep,
        first_deep,
    )
    SHADOW_FINDER_AVAILABLE = True
except ImportError:  # pragma: no cover - import guard
    find_deep = None
    first_deep = None
    SHADOW_FINDER_AVAILABLE = False

# WSP 84 REUSE: the proven anti-detection stealth JS already used to harden the
# undetected browser. We REUSE _inject_stealth_js (which registers a CDP
# Page.addScriptToEvaluateOnNewDocument hook hiding navigator.webdriver +
# spoofing plugins/chrome runtime). The cdc_/$cdc property strip is added on top
# in _register_stealth (the undetected_browser JS does not strip cdc_). This
# reduces the Ask Studio "Gemini chat loads blank under automation" rate; the
# load-bearing fix remains the NEW-TAB retry below.
try:
    from modules.infrastructure.foundups_selenium.src.undetected_browser import (
        UndetectedBrowserManager,
    )
    UNDETECTED_BROWSER_AVAILABLE = True
except ImportError:  # pragma: no cover - import guard
    UndetectedBrowserManager = None
    UNDETECTED_BROWSER_AVAILABLE = False

logger = logging.getLogger(__name__)

INDEX_ROOT = Path("memory") / "video_index"
STOP_FILE = Path("memory") / "STOP_VIDEO_INDEXER"
REINDEX_FILE = Path("memory") / "REINDEX_VIDEO_INDEXER"

# WRE "no hang actions": a single guaranteed-terminating OUTER guard over the
# whole ask_about_video flow. The per-loop timeouts (readiness gate,
# answer-capture) already bound each stage, but a guaranteed-terminating action
# needs ONE hard ceiling measured from the start of the ask. If the total
# monotonic runtime of ask_about_video exceeds this, the flow ABORTS and returns
# success=False, error="ask_studio_timeout", and persists NOTHING. Measured with
# time.monotonic() (NOT wall-clock that a test could mock away). Tests may inject
# a tiny budget (e.g. 0.0) to force the timeout with a never-arriving answer.
ASK_TOTAL_RUNTIME_BUDGET_SECONDS = 180.0

# Heartbeat cadence for the long readiness-wait / answer-capture loops. The loops
# emit a periodic "[STUDIO-ASK] heartbeat: waiting for <phase> t+Ns/<budget>s" log
# every ~this many seconds so a watching operator/WRE sees the action is alive and
# NOT hung (WRE "no hang actions"). Heartbeat cadence is independent of the
# per-poll delay; we only emit once this many seconds elapse since the last beat.
ASK_HEARTBEAT_INTERVAL_SECONDS = 8.0


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


# =============================================================================
# OBSERVE-MODE acoustic music/talk label (SHORTS_MUSIC_LABEL_OBSERVE_PHASE1)
# Worker-Lane: MUSIC-OBSERVE
# =============================================================================
# Flag-gated (YT_AUDIO_LABEL_OBSERVE, default OFF) because it adds an audio
# DOWNLOAD to PHASE 2. When OFF this is a pure no-op: zero audio work, zero
# change to the artifact. When ON, for each indexed video we compute an ACOUSTIC
# audio_label (music|talk) and store it as a SIBLING to the existing LLM-derived
# content_category so 012 can OBSERVE acoustic-vs-LLM accuracy. This NEVER gates
# scheduling and NEVER mutates content_category. Any failure (download/classify)
# logs and continues with NO audio_label -- indexing is never broken.
#
# WSP 84 REUSE (cited file:line, re-confirmed on origin/main):
#   - audio fetch: VideoArchiveExtractor.extract_audio
#       modules/platform_integration/youtube_live_audio/src/youtube_live_audio.py:405
#     (returns a normalized float32 mono array; unlisted-cookie support via
#      YT_DLP_COOKIES_BROWSER at :451)
#   - acoustic decision: audio_content_classifier.classify_content(path) ->
#       ClassificationResult(label='music'|'talk', confidence, ...)
#       modules/ai_intelligence/audio_content_classifier/src/audio_content_classifier.py:294
#     (fail-safe: returns label='talk', confidence=0.0, method='unavailable';
#      never raises into the caller). The float32 array is persisted to a temp
#      WAV (stdlib `wave`, no soundfile dep) so classify_content can librosa.load it.
AUDIO_LABEL_OBSERVE_FLAG = "YT_AUDIO_LABEL_OBSERVE"


def _audio_label_observe_enabled() -> bool:
    """True iff the observe flag is explicitly enabled. Default OFF."""
    return _env_truthy(AUDIO_LABEL_OBSERVE_FLAG, "0")


def _array_to_temp_wav(audio, sample_rate: int = 16000) -> Optional[str]:
    """Persist a normalized float32 mono array to a temp 16-bit PCM WAV.

    Uses the stdlib `wave` module (NO soundfile dep) so the observe path adds no
    new hard dependency. Returns a temp .wav path, or None on any failure.
    """
    import tempfile
    import wave

    try:
        import numpy as np
    except ImportError:
        return None
    try:
        arr = np.asarray(audio, dtype=np.float32)
        if arr.ndim > 1:
            arr = np.mean(arr, axis=0).astype(np.float32)
        # float32 [-1,1] -> int16 PCM
        clipped = np.clip(arr, -1.0, 1.0)
        pcm16 = (clipped * 32767.0).astype("<i2")
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = tmp.name
        tmp.close()
        with wave.open(tmp_path, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)  # int16
            wav.setframerate(int(sample_rate))
            wav.writeframes(pcm16.tobytes())
        return tmp_path
    except Exception:
        return None


def _observe_audio_label(video_id: str) -> Optional[Dict[str, Any]]:
    """OBSERVE-only: acoustically label a video's audio as music|talk.

    Flag-gated (YT_AUDIO_LABEL_OBSERVE); returns None when the flag is OFF so the
    caller does ZERO audio work and writes NO field. When ON, downloads audio
    (VideoArchiveExtractor) and runs the acoustic classifier, returning
    {"audio_label": "music"|"talk", "audio_label_confidence": float} or None.

    HARD CONTRACT: never raises, never hangs into the indexing loop. On ANY
    failure (flag off, missing dep, download failure, classify unavailable) it
    returns None and the caller simply skips the field -- indexing continues.
    """
    if not _audio_label_observe_enabled():
        return None
    if not video_id:
        return None

    tmp_wav: Optional[str] = None
    try:
        # Lazy imports: keep the indexer hermetic when the observe flag is OFF and
        # when these optional deps (yt-dlp/ffmpeg/librosa) are not installed.
        from modules.platform_integration.youtube_live_audio.src.youtube_live_audio import (
            VideoArchiveExtractor,
        )
        from modules.ai_intelligence.audio_content_classifier.src.audio_content_classifier import (
            classify_content as acoustic_classify_content,
        )

        extractor = VideoArchiveExtractor()
        audio = extractor.extract_audio(video_id)
        if audio is None:
            logger.warning(
                "[MUSIC-OBSERVE] %s: audio unavailable (extract_audio returned None) -- skipping label",
                video_id,
            )
            return None

        tmp_wav = _array_to_temp_wav(audio, sample_rate=16000)
        if not tmp_wav:
            logger.warning("[MUSIC-OBSERVE] %s: could not persist temp wav -- skipping label", video_id)
            return None

        result = acoustic_classify_content(tmp_wav)
        # method == 'unavailable' (confidence 0.0) means the classifier could not
        # decide (missing librosa, corrupt audio). Treat as no observation.
        if getattr(result, "method", "unavailable") == "unavailable":
            logger.warning(
                "[MUSIC-OBSERVE] %s: classifier unavailable (%s) -- skipping label",
                video_id,
                getattr(result, "method", "unavailable"),
            )
            return None

        return {
            "audio_label": result.label,
            "audio_label_confidence": round(float(result.confidence), 4),
        }
    except Exception as exc:  # never break indexing
        logger.warning("[MUSIC-OBSERVE] %s: observe failed (%s) -- skipping label", video_id, exc)
        return None
    finally:
        if tmp_wav:
            try:
                Path(tmp_wav).unlink(missing_ok=True)
            except Exception:
                pass


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
    # RAW Gemini content_category string BEFORE enum normalization. Gemini often
    # returns a richer label ("Educational Philosophy & Future Trends") than the
    # 5-value enum. _parse_ask_response MAPS the raw label to the closest enum for
    # content_category, but PRESERVES the original here (+ in the saved index) so
    # the rich label is never lost. Equals content_category for an exact enum hit.
    content_category_raw: Optional[str] = None
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
    # =========================================================================
    # LIVE-GROUNDED SELECTORS (STUDIO_ASK_SHADOW_DOM_SELECTORS_PHASE1)
    # ---------------------------------------------------------------------
    # 012 captured these from the REAL shadow-rooted Studio DOM, so they are the
    # source-of-truth PRIMARY targets (resolved via the shadow-DOM deep finder).
    # The old aria-label="Ask Studio" flat selector does NOT exist on the live
    # page -- the real entry is the creator-chat "spark" trigger. Each entry is
    # either a CSS string (single deep step) or a list (a CROSS-SHADOW chain for
    # shadow_query). The legacy flat selectors are kept ONLY as documented
    # fallbacks (so light-DOM pages + the existing mock drivers still resolve).
    # =========================================================================

    # Edit-surface / title field (contains div#textbox[contenteditable]).
    TITLE_TEXTAREA_SELECTOR = "ytcp-social-suggestions-textbox#title-textarea"

    ASK_STUDIO_SELECTORS = {
        # Header entry button that opens the Ask Studio dialog.
        # PRIMARY (live-grounded): the "spark" creator-chat trigger chain
        # ytcp-creator-chat-trigger -> ytcp-icon-button (NOT aria-label="Ask Studio").
        "header_button": [
            ["ytcp-creator-chat-trigger", "ytcp-icon-button"],
            ["ytcp-creator-chat-trigger", "ytcp-creator-chat-spark", "ytcp-icon-button"],
            "ytcp-creator-chat-trigger",
            # Legacy flat fallbacks (resilience only; not present on live page).
            'ytcp-icon-button[aria-label="Ask Studio"]',
            'ytcp-icon-button[aria-label*="Ask Studio"]',
            'button[aria-label="Ask Studio"]',
            'button[aria-label*="Ask Studio"]',
        ],
        # Dialog container shown after clicking the header button. Live-observed:
        # the dialog HOST computes visible:false while its CHILDREN are visible,
        # so callers confirm "opened" via the PROMPT BOX / STREAM, not the dialog.
        "dialog": [
            "tp-yt-paper-dialog#dialog",
            "ytcp-dialog",
            # Legacy flat fallback.
            'ytcp-dialog#dialog',
        ],
        # Contenteditable prompt box inside the dialog (live-grounded class).
        "prompt_box": [
            'div.ytcpCreatorChatEntityAttachmentInlineFlowPromptBox[contenteditable="true"][aria-label="Ask something"]',
            'div.ytcpCreatorChatEntityAttachmentInlineFlowPromptBox[contenteditable="true"]',
            # Legacy flat fallbacks.
            'div[contenteditable][aria-label="Ask something"]',
            'div[contenteditable="true"][aria-label*="Ask"]',
        ],
        # Send / submit button inside the dialog. PREFERRED submission path
        # (mirror reply_executor's button-click submit, NEVER Enter-spam).
        "send_button": [
            # 012 live-grounded: the Ask Studio prompt-box send/action button
            # (ytcp-ask-studio-input-view-model -> ...ActionButton -> ytcp-icon-button#action-button).
            # Tried FIRST; the aria-label variants + the Enter fallback (_submit_prompt) remain.
            "ytcp-icon-button#action-button",
            'ytcp-icon-button[aria-label="Send"]',
            'ytcp-icon-button[aria-label*="Send"]',
            'button[aria-label="Send"]',
            'button[aria-label*="Send"]',
            'button[aria-label*="Submit"]',
        ],
        # Streaming / response container (live-grounded). DOM text, NOT clipboard.
        "response_stream": [
            "ytcp-engagement-panel-section-list-renderer#PAcreator_chat_streaming",
            "#PAcreator_chat_streaming",
            # Legacy flat fallbacks.
            'div.ytcpCreatorChatEntityResponse',
            'ytcp-creator-chat-response',
            '[class*="CreatorChat"][class*="Response"]',
        ],
    }

    # Zero-state suggestion view ("How can Ask Studio help me? Summarize comments
    # ...") rendered in the stream BEFORE any real answer. Live caveat: this must
    # NOT be scraped as the answer -- the real answer renders after submit.
    ZERO_STATE_SELECTOR = "ytcp-ask-studio-zero-state-view-model"

    # Markers proving a scraped stream block is the ZERO-STATE suggestion list,
    # not a real answer. If the stabilized text is ONLY zero-state, fail closed.
    #
    # LIVE-PROVEN false-success (STUDIO_ASK_GEMINI_READINESS_RETRY_PHASE1): after
    # submit the capture stabilized at +6s on the ZERO-STATE *suggestion* variant
    # and saved 106 chars: "A/B Testing Guide / Hello, UnDaoDu / Suggest new video
    # ideas / Summarize my channel performance / More suggestions" (topics=[],
    # category=other). The old marker set ("how can ask studio help" / "summarize
    # comments") did NOT contain these phrases, so the suggestion list survived
    # _strip_boilerplate and was scraped as the answer. We extend the marker set
    # to ALSO catch the suggestion-chip variant + the channel greeting so a stream
    # of ONLY these (no JSON block, no substantial prose) is recognized as the
    # zero-state and NEVER persisted as the answer.
    ZERO_STATE_MARKERS = (
        "how can ask studio help",
        "how can i help you",
        "summarize comments",
        "summarize the comments",
        # Suggestion-chip variant (live-captured 106-char false success).
        "suggest new video ideas",
        "summarize my channel performance",
        "more suggestions",
        "a/b testing",
        # Channel greeting line ("Hello, <ChannelName>") that heads the zero-state.
        "hello,",
    )

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

    # Minimum chars of boilerplate-stripped PROSE (no JSON block) to count as a
    # REAL answer. LIVE-PROVEN guard: the zero-state suggestion variant stripped
    # down to ~100 chars of chips ("Suggest new video ideas / Summarize my channel
    # performance / More suggestions"). Below this length (and with no JSON index
    # block) the stream is NOT an answer -> fail closed "ask_studio_no_answer".
    # A genuine Gemini prose answer is well above this; the JSON-index happy path
    # is unaffected (JSON block is extracted BEFORE this threshold applies).
    MIN_SUBSTANTIAL_PROSE_CHARS = 400

    # =====================================================================
    # STUDIO_ASK_GEMINI_READINESS_RETRY_PHASE1 (live-proven loop constants)
    # ---------------------------------------------------------------------
    # GEMINI-READY marker: the zero-state greeting Gemini renders in the stream
    # ONCE its chat has initialized ("how can i help"). Live-proven: when the
    # dialog opens BLANK (no greeting, only the disclaimer placeholder), Gemini
    # never initialized and typing scrapes the disclaimer as a false success.
    # The greeting (case-insensitive substring) is the PRIMARY, proven readiness
    # signal -- NOT a coordinate/vision check (that is Phase 2, out of scope).
    # =====================================================================
    GEMINI_READY_MARKER = "how can i help"

    # Max seconds to poll the stream for the readiness greeting after opening Ask
    # Studio, before declaring the panel BLANK (-> new-tab retry).
    GEMINI_READY_TIMEOUT_SECONDS = 16.0

    # Max NEW-TAB retries when Gemini loads blank (the load-bearing live fix:
    # attempt1=BLANK, attempt2(new tab)=LOADED). After N exhausted attempts with
    # no greeting -> fail closed "gemini_did_not_load".
    GEMINI_MAX_LOAD_ATTEMPTS = 5

    # DISCLAIMER footer rendered under every Ask Studio answer (NEVER the answer).
    # Live-grounded: "AI can make mistakes. You are responsible for the content
    # you publish. Learn more". Matched case-insensitively and stripped.
    DISCLAIMER_MARKERS = (
        "ai can make mistakes",
        "you are responsible for the content you publish",
    )

    # Transient PROCESSING lines that stream BEFORE the real answer (never the
    # answer). Live-grounded; stripped from the captured answer block.
    PROCESSING_MARKERS = (
        "reviewing your request",
        "looking through your content",
    )

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
    # before failing closed (no partial/garbage indexing). LIVE-PROVEN: the real
    # JSON index streams ~30s AFTER submit (the zero-state is immediately stable
    # at +6s), so the wait must outlast the zero-state and STABILIZE ON THE
    # EXTRACTED ANSWER, not the immediately-stable zero-state. Bumped 30s -> 60s.
    RESPONSE_TIMEOUT_SECONDS = 60.0

    # WRE "no hang actions" (class-attribute mirrors of the module constants so a
    # test can monkeypatch a tiny budget). ASK_TOTAL_RUNTIME_BUDGET_SECONDS is the
    # guaranteed-terminating OUTER ceiling on the whole ask_about_video flow
    # (monotonic-measured); past it the flow aborts "ask_studio_timeout" and
    # persists nothing. ASK_HEARTBEAT_INTERVAL_SECONDS paces the liveness beat.
    ASK_TOTAL_RUNTIME_BUDGET_SECONDS = ASK_TOTAL_RUNTIME_BUDGET_SECONDS
    ASK_HEARTBEAT_INTERVAL_SECONDS = ASK_HEARTBEAT_INTERVAL_SECONDS

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

    @staticmethod
    def _build_video_prompt(title: str, video_id: str) -> str:
        """
        Build a SINGLE-LINE prompt that NAMES the exact video (title + video id +
        studio URL) and requests a CLEAN JSON index.

        LIVE-PROVEN correctness requirement (STUDIO_ASK_GEMINI_READINESS_RETRY):
        Ask Studio is a CHANNEL assistant. A query WITHOUT the specific video id
        made Gemini analyze a DIFFERENT video even though the right one was loaded
        (a data-integrity disaster). Naming title+id+url pins it to THIS video.
        The JSON-requesting form is live-proven to return a clean JSON index
        (content_category + topics[] + segments[{time,topic,summary}]). Single
        line (no embedded "\\n") so the contenteditable never sees a stray ENTER.
        """
        safe_title = (title or "").replace('"', "'").strip()
        return (
            f'Analyze the video titled "{safe_title}" (video id {video_id}, '
            f"studio.youtube.com/video/{video_id}). Respond ONLY with a JSON "
            'index: {"content_category":"...","topics":["..."],'
            '"segments":[{"time":"0:00","topic":"...","summary":"..."}]}'
        )

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
        # Tabs THIS flow opens during the new-tab retry (step 3). Tracked so the
        # end-of-flow cleanup (step 7) closes ONLY flow-created tabs, never the
        # operator's pre-existing tabs.
        self._created_handles: List[str] = []
        
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

    def _maybe_heartbeat(
        self,
        phase: str,
        start_monotonic: float,
        last_beat: float,
    ) -> float:
        """
        Emit a periodic "[STUDIO-ASK] heartbeat: waiting for <phase> t+Ns/<budget>s"
        log if at least ASK_HEARTBEAT_INTERVAL_SECONDS have elapsed since the last
        beat (WRE "no hang actions" liveness signal). Returns the (possibly
        updated) last-beat monotonic timestamp so the caller can carry it forward.

        Uses time.monotonic() for elapsed/last-beat math (NOT wall-clock that a
        test could mock away); ``start_monotonic`` is the monotonic clock at the
        start of the ask flow so t+N is measured against the SAME guaranteed total
        runtime budget enforced by the outer no-hang guard.
        """
        now = time.monotonic()
        if (now - last_beat) < self.ASK_HEARTBEAT_INTERVAL_SECONDS:
            return last_beat
        elapsed = now - start_monotonic
        logger.info(
            f"[STUDIO-ASK] heartbeat: waiting for {phase} "
            f"t+{elapsed:.0f}s/{self.ASK_TOTAL_RUNTIME_BUDGET_SECONDS:.0f}s"
        )
        return now
    
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
                # PRESERVE Gemini's raw (pre-normalization) category in the saved
                # index so the rich label is never lost. None if Gemini returned no
                # category string (parse failure / prose fallback edge).
                "content_category_raw": ask_result.content_category_raw,
            },
            gemini_summary={
                "ask_response": ask_result.response_text or "",
                "ask_topics": ask_result.topics or [],
                "ask_segments": ask_result.timestamps or [],
            },
            transcript_source="gemini",
        )
    
    # Canonical content_category enum (the 5 values the index/classifier expect).
    CONTENT_CATEGORY_ENUM = ("educational", "personal_vlog", "ice_remix", "ffcpln_music", "other")

    @classmethod
    def _normalize_content_category(cls, raw: Any) -> str:
        """
        Map an arbitrary Gemini content_category string to the closest enum value.

        Gemini frequently returns a RICHER label than the 5-value enum (e.g.
        "Educational Philosophy & Future Trends"). An EXACT enum value passes
        through unchanged. Otherwise we keyword-map (case-insensitive substring):
          contains "educat"                              -> educational
          "vlog"/"personal"/"daily"/"diary"             -> personal_vlog
          "ice"/"immigration"/"politic"/"activist"/"news"-> ice_remix
          "music"/"instrumental"/"visualizer"           -> ffcpln_music
          else                                          -> other
        The RAW string is preserved separately (content_category_raw) by callers
        so the rich label is never lost; this method only resolves the enum slot.
        """
        if not isinstance(raw, str):
            return "other"
        low = raw.strip().lower()
        if low in cls.CONTENT_CATEGORY_ENUM:
            return low
        if "educat" in low:
            return "educational"
        if any(kw in low for kw in ("vlog", "personal", "daily", "diary")):
            return "personal_vlog"
        if any(kw in low for kw in ("ice", "immigration", "politic", "activist", "news")):
            return "ice_remix"
        if any(kw in low for kw in ("music", "instrumental", "visualizer")):
            return "ffcpln_music"
        return "other"

    def _parse_ask_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the Ask Studio answer: the JSON index block FIRST (Gemini returns a
        clean JSON index for the JSON-requesting prompt - live-proven:
        content_category + topics[] + segments[{time,topic,summary}]), then a
        prose/keyword fallback if no JSON block parses. Strict JSON is NOT
        required (prose tolerance is the documented fallback).

        CONTENT_CATEGORY NORMALIZE + PRESERVE: a content_category NOT in the enum
        (e.g. "Educational Philosophy & Future Trends") is MAPPED to the closest
        enum value (_normalize_content_category) for content_category, while the
        ORIGINAL Gemini string is preserved in content_category_raw (never lost).
        An exact enum value passes through unchanged with raw == that same value.
        """
        try:
            # JSON BLOCK FIRST: the last balanced {...} with topics /
            # content_category (the proven Gemini JSON index). Tolerant: try the
            # extracted block, falling back to the legacy non-greedy match.
            json_block = self._extract_json_block(response_text)
            if json_block:
                try:
                    parsed = json.loads(json_block)
                    return self._apply_category_normalization(parsed)
                except Exception:
                    pass  # malformed JSON block -> try legacy match, then prose
            json_match = re.search(r'\{[\s\S]*?"topics"[\s\S]*?\}(?=\s*$|\s*```)', response_text)
            if json_match:
                parsed = json.loads(json_match.group())
                return self._apply_category_normalization(parsed)

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
            return {
                "topics": topics[:10],
                "segments": [],
                "content_category": category,
                "content_category_raw": category,
            }
        except Exception as e:
            logger.warning(f"[STUDIO-ASK] JSON parse failed: {e}")
            return {
                "topics": [],
                "segments": [],
                "content_category": "other",
                "content_category_raw": None,
                "raw": response_text,
            }

    def _apply_category_normalization(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize ``parsed["content_category"]`` to the enum + preserve the RAW
        Gemini string in ``parsed["content_category_raw"]``. A non-string / missing
        category yields content_category="other" with raw=None; an exact enum value
        passes through with raw == that same value; a rich label is mapped to the
        closest enum while raw keeps the original. Mutates and returns ``parsed``.
        """
        raw = parsed.get("content_category")
        parsed["content_category"] = self._normalize_content_category(raw)
        parsed["content_category_raw"] = raw if isinstance(raw, str) else None
        return parsed
    
    def _first_element(self, selectors: List[Any]):
        """
        Return the first element resolving from the selector list, else None.

        PRIMARY: shadow-DOM deep traversal (first_deep) - each entry is a CSS
        string (single deep step) OR a list (a cross-shadow chain). This pierces
        YouTube Studio's shadow roots and returns a REAL WebElement (so #825's
        human_type + #827's .click() keep working). FALLBACK: a flat
        find_element per string selector (cheap, documented) so light-DOM pages
        and the existing mock drivers still resolve. The PRIMARY mechanism is
        shadow traversal, not the flat fallback.
        """
        # PRIMARY: shadow-piercing deep find (handles css strings + chains).
        if SHADOW_FINDER_AVAILABLE and first_deep is not None:
            try:
                el = first_deep(self.driver, selectors)
                if el is not None:
                    return el
            except Exception:
                pass
        # FALLBACK: flat light-DOM find for plain string selectors only.
        for selector in selectors:
            if not isinstance(selector, str):
                continue
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

    # =====================================================================
    # STEALTH (STUDIO_ASK_GEMINI_READINESS_RETRY_PHASE1 step 1)
    # =====================================================================
    # CDP pre-load script: strip cdc_/$cdc webdriver fingerprints + set
    # navigator.webdriver=undefined. Re-registered on every NEW tab (the CDP
    # hook is per-page). REUSES undetected_browser._inject_stealth_js when
    # importable (hides webdriver, spoofs plugins/chrome runtime); the cdc_ strip
    # is layered on top because that JS does not strip cdc_.
    _STEALTH_CDC_STRIP_JS = (
        "(function(){try{for(const k of Object.keys(window)){"
        "if(/cdc_|[$]cdc/.test(k)){try{delete window[k];}catch(e){}}}"
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        "}catch(e){}})();"
    )

    def _register_stealth(self) -> bool:
        """
        Register the anti-detection CDP pre-load script on the CURRENT driver/tab.

        Page.addScriptToEvaluateOnNewDocument runs the script on EVERY document
        the tab loads, so it must be (re-)registered per new tab. REUSES the
        proven undetected_browser stealth JS (navigator.webdriver hide + plugin /
        chrome-runtime spoof) when importable, then layers the cdc_/$cdc strip on
        top. Best-effort: a driver without execute_cdp_cmd (e.g. mock) is a no-op
        returning False, never raising (stealth is a softener, the new-tab retry
        is the load-bearing fix). Returns True if any stealth hook registered.
        """
        driver = self.driver
        # The stealth hooks REQUIRE execute_cdp_cmd (both the reused
        # undetected_browser JS and the cdc_ strip register a CDP pre-load
        # script). A driver without it (e.g. a mock) is a no-op returning False.
        cdp = getattr(driver, "execute_cdp_cmd", None)
        if not callable(cdp):
            return False
        registered = False
        # REUSE: undetected_browser stealth JS (per-new-document CDP hook).
        if UNDETECTED_BROWSER_AVAILABLE and UndetectedBrowserManager is not None:
            try:
                UndetectedBrowserManager._inject_stealth_js(driver)
                registered = True
            except Exception as e:  # pragma: no cover - defensive
                logger.debug(f"[STUDIO-ASK] reused stealth JS skipped: {e}")
        # LAYER: cdc_/$cdc strip + webdriver=undefined (undetected JS omits cdc_).
        try:
            cdp(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": self._STEALTH_CDC_STRIP_JS},
            )
            registered = True
        except Exception as e:  # pragma: no cover - defensive
            logger.debug(f"[STUDIO-ASK] cdc_ strip CDP hook skipped: {e}")
        if registered:
            logger.info("[STUDIO-ASK] Stealth CDP pre-load registered for tab")
        return registered

    # =====================================================================
    # GEMINI-READINESS GATE (step 2)
    # =====================================================================
    @classmethod
    def _is_gemini_ready(cls, text: str) -> bool:
        """
        True if the stream text shows Gemini has INITIALIZED: the proven
        zero-state greeting ("how can i help") OR the Ask Studio zero-state
        suggestion view ("How can Ask Studio help me? / Summarize comments ...").
        Either greeting proves the chat loaded (not the BLANK disclaimer-only
        placeholder). A blank/disclaimer-only stream is NOT ready (-> retry).
        """
        if not text:
            return False
        low = text.lower()
        if cls.GEMINI_READY_MARKER in low:
            return True
        return any(m in low for m in cls.ZERO_STATE_MARKERS)

    async def _wait_for_gemini_ready(self, start_monotonic: Optional[float] = None) -> bool:
        """
        POLL the Ask Studio stream for the Gemini-ready greeting ("how can i
        help") up to GEMINI_READY_TIMEOUT_SECONDS. Returns True once the greeting
        appears (Gemini initialized), False if the panel stays BLANK (no
        greeting) within the timeout -> caller triggers the NEW-TAB retry. Do NOT
        type into a blank panel.

        Emits a periodic "waiting for readiness" heartbeat (WRE "no hang actions").
        ``start_monotonic`` is the ask-flow start time used for the t+N heartbeat
        readout; defaults to "now" when called outside the flow.
        """
        import time as _time

        if start_monotonic is None:
            start_monotonic = _time.monotonic()
        last_beat = _time.monotonic()
        deadline = _time.monotonic() + self.GEMINI_READY_TIMEOUT_SECONDS
        while _time.monotonic() < deadline:
            el = self._first_element(self.ASK_STUDIO_SELECTORS["response_stream"])
            text = ""
            if el is not None:
                try:
                    text = (el.text or "").strip()
                except Exception:
                    text = ""
            # Gemini is READY when it has initialized: either the zero-state
            # greeting ("how can i help") is present, OR a real answer block is
            # already extractable (a non-empty stream past the blank placeholder).
            # The DISCLAIMER-only / empty placeholder is the BLANK case.
            if self._is_gemini_ready(text) or self._extract_answer(text):
                logger.info("[STUDIO-ASK] Gemini ready (greeting or answer present)")
                return True
            last_beat = self._maybe_heartbeat("readiness", start_monotonic, last_beat)
            await self._human_delay(1.0, 0.2)
        logger.info("[STUDIO-ASK] Gemini readiness greeting NOT seen (blank panel)")
        return False

    # =====================================================================
    # REAL-ANSWER CAPTURE (step 5) - strip boilerplate, never zero on greeting
    # =====================================================================
    @classmethod
    def _strip_boilerplate(cls, text: str) -> str:
        """
        Remove Ask Studio boilerplate from a stream block: the persistent
        zero-state greeting + suggestion list, the transient PROCESSING lines
        ("Reviewing your request", "Looking through your content"), and the
        DISCLAIMER footer ("AI can make mistakes..."). Returns the remaining body
        text. NOTE: this is used to decide whether a REAL answer is present -- it
        does NOT zero the stream merely because the persistent greeting is there
        (the proven scraper bug). Pure string helper (no DOM).
        """
        if not text:
            return ""
        kept: List[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            low = line.lower()
            if any(m in low for m in cls.ZERO_STATE_MARKERS):
                continue
            if any(m in low for m in cls.PROCESSING_MARKERS):
                continue
            if any(m in low for m in cls.DISCLAIMER_MARKERS):
                continue
            if low == "learn more":
                continue
            kept.append(line)
        return "\n".join(kept).strip()

    @staticmethod
    def _extract_json_block(text: str) -> Optional[str]:
        """
        Return the LAST balanced ``{...}`` block in ``text`` that contains a
        ``topics`` or ``content_category`` key (the JSON index Gemini returns for
        the JSON prompt), else None. Scans balanced brace runs so prompt-echo
        JSON examples ABOVE the answer don't shadow the real (last) answer block.
        """
        if not text or "{" not in text:
            return None
        best: Optional[str] = None
        depth = 0
        start = -1
        for i, ch in enumerate(text):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                if depth > 0:
                    depth -= 1
                    if depth == 0 and start >= 0:
                        block = text[start : i + 1]
                        low = block.lower()
                        if '"topics"' in low or '"content_category"' in low:
                            best = block  # keep LAST qualifying block
                        start = -1
        return best

    def _extract_answer(self, stream_text: str, prompt: str = "") -> str:
        """
        Extract the REAL answer from the Ask Studio stream, fixing BOTH the
        false-success scrape AND the greeting-zeroing bug.

        The stream PERSISTS the greeting + suggestions + prompt echo ABOVE the
        answer, so we must NOT reject the whole stream just because the greeting
        ("how can i help") is present. Instead:
          1. Prefer the JSON index block (last balanced {...} with topics /
             content_category) -- returned verbatim for tolerant JSON parsing.
          2. Else strip boilerplate (greeting/suggestions/processing/disclaimer)
             and the prompt echo, returning the remaining prose body.
        Returns "" only when nothing but boilerplate/greeting/disclaimer remains
        (caller fails closed "ask_studio_no_answer").
        """
        if not stream_text:
            return ""
        # 1) JSON index block (proven happy path for the JSON-requesting prompt).
        json_block = self._extract_json_block(stream_text)
        if json_block:
            return json_block
        # 2) Prose fallback: drop boilerplate, then drop the echoed prompt lines.
        body = self._strip_boilerplate(stream_text)
        if not body:
            return ""
        if prompt:
            prompt_lines = {ln.strip() for ln in prompt.splitlines() if ln.strip()}
            body = "\n".join(
                ln for ln in body.splitlines() if ln.strip() not in prompt_lines
            ).strip()
        return body

    @classmethod
    def _is_real_answer(cls, extracted: str) -> bool:
        """
        True if an EXTRACTED block is a REAL answer worth stabilizing/persisting:
          - a JSON INDEX block (balanced {...} with topics/content_category), OR
          - SUBSTANTIAL non-boilerplate prose (>= MIN_SUBSTANTIAL_PROSE_CHARS).

        LIVE-PROVEN guard: the zero-state suggestion variant, after boilerplate
        stripping, is only a short run of suggestion chips (~100 chars) -- NOT a
        JSON index and below the prose threshold -> NOT a real answer. This is the
        capture/persist gate; the pure _extract_answer helper stays a faithful
        "non-boilerplate body" extractor (so #836's prose-extraction proofs hold).
        """
        if not extracted:
            return False
        if cls._extract_json_block(extracted) is not None:
            return True
        return len(extracted) >= cls.MIN_SUBSTANTIAL_PROSE_CHARS

    # =====================================================================
    # NEW-TAB RETRY ON BLANK (step 3) - the LOAD-BEARING live fix
    # =====================================================================
    async def _open_ask_studio_ready(
        self,
        video_id: str,
        start_monotonic: Optional[float] = None,
        total_deadline: Optional[float] = None,
    ) -> str:
        """
        Open Ask Studio and ensure Gemini is READY, retrying on a BLANK panel by
        opening a FRESH tab (the live-proven fix: attempt1=BLANK,
        attempt2(new tab)=LOADED).

        Loop, up to GEMINI_MAX_LOAD_ATTEMPTS:
          - register stealth on the current tab
          - open Ask Studio header dialog
          - run the readiness gate (poll for "how can i help")
          - if ready -> return "ready" (prompt box is safe to type into)
          - if blank -> open a NEW tab, re-register stealth, re-navigate to the
            video edit page, CLOSE the OLD blank tab (do not accumulate dead
            tabs), and retry.

        Returns one of:
          "ready"    - Gemini greeted / answered; safe to type.
          "blank"    - the Ask Studio header WAS found but Gemini stayed blank
                       across all retries (-> caller fails closed
                       "gemini_did_not_load", no ask, no persist).
          "no_header" - the Ask Studio header was never found (legacy-only DOM)
                       so the loop never engaged (-> caller may try the legacy
                       watch-page / popup fallback).
        Tabs THIS flow creates are tracked in self._created_handles for
        end-of-flow cleanup; the operator's pre-existing tab is never closed.
        """
        import time as _time

        driver = self.driver
        header_ever_found = False
        for attempt in range(1, self.GEMINI_MAX_LOAD_ATTEMPTS + 1):
            # OUTER no-hang guard: never start a new retry attempt past the total
            # runtime budget (the readiness gate itself is also budget-bounded).
            if total_deadline is not None and _time.monotonic() >= total_deadline:
                logger.warning(
                    f"[STUDIO-ASK] {video_id}: total runtime budget exceeded "
                    f"during readiness (attempt {attempt}) -> abort"
                )
                return "blank" if header_ever_found else "no_header"

            # STEALTH: (re)register the CDP pre-load hook on THIS tab.
            self._register_stealth()

            # Open the Ask Studio dialog (header spark trigger).
            if self._open_ask_studio():
                header_ever_found = True
                await self._human_delay(2.0, 0.3)
                # READINESS GATE: do NOT type into a blank panel.
                if await self._wait_for_gemini_ready(start_monotonic):
                    logger.info(
                        f"[STUDIO-ASK] {video_id}: Gemini ready on attempt {attempt}"
                    )
                    return "ready"

            logger.info(
                f"[STUDIO-ASK] {video_id}: blank panel on attempt {attempt}/"
                f"{self.GEMINI_MAX_LOAD_ATTEMPTS}"
            )
            if attempt >= self.GEMINI_MAX_LOAD_ATTEMPTS:
                break

            # NEW-TAB RETRY: open a fresh tab, re-stealth, re-navigate, then CLOSE
            # the OLD blank tab. Requires multi-window support; if the driver
            # cannot open a new window, we cannot retry -> stop.
            old_handle = None
            try:
                old_handle = driver.current_window_handle
            except Exception:
                old_handle = None
            try:
                driver.switch_to.new_window("tab")
            except Exception as e:
                logger.warning(
                    f"[STUDIO-ASK] {video_id}: cannot open new tab for retry: {e}"
                )
                break
            # Track the tab THIS flow created (for end-of-flow cleanup).
            try:
                new_handle = driver.current_window_handle
                self._created_handles.append(new_handle)
            except Exception:
                new_handle = None
            # Re-register stealth on the fresh tab + re-navigate to the edit page.
            self._register_stealth()
            studio_url = f"https://studio.youtube.com/video/{video_id}/edit"
            try:
                driver.get(studio_url)
            except Exception as e:
                logger.warning(f"[STUDIO-ASK] {video_id}: retry nav failed: {e}")
            await self._human_delay(3.0, 0.4)
            # CLOSE the OLD blank tab (012: do not accumulate non-working tabs).
            if old_handle is not None and new_handle is not None and old_handle != new_handle:
                self._close_handle(old_handle, restore_to=new_handle)
        if not header_ever_found:
            # The Studio header was never present (legacy-only DOM): the readiness
            # loop never engaged, so let the caller try the legacy fallback.
            logger.info(
                f"[STUDIO-ASK] {video_id}: Ask Studio header never found -> fallback"
            )
            return "no_header"
        logger.warning(
            f"[STUDIO-ASK] {video_id}: Gemini never loaded after "
            f"{self.GEMINI_MAX_LOAD_ATTEMPTS} attempts (fail closed)"
        )
        return "blank"

    def _close_handle(self, handle, restore_to=None) -> None:
        """
        Close a SINGLE window handle this flow opened, then switch back to
        ``restore_to`` (or the first remaining handle). Only ever called with a
        handle THIS flow created/owns (the old blank retry tab); never closes the
        operator's pre-existing tab. Best-effort; never raises.
        """
        driver = self.driver
        try:
            driver.switch_to.window(handle)
            driver.close()
        except Exception as e:  # pragma: no cover - defensive
            logger.debug(f"[STUDIO-ASK] close handle skipped: {e}")
        finally:
            if handle in self._created_handles:
                try:
                    self._created_handles.remove(handle)
                except ValueError:
                    pass
        target = restore_to
        try:
            handles = getattr(driver, "window_handles", None) or []
            if target is None or target not in handles:
                target = handles[0] if handles else None
            if target is not None:
                driver.switch_to.window(target)
        except Exception as e:  # pragma: no cover - defensive
            logger.debug(f"[STUDIO-ASK] restore handle skipped: {e}")

    def _cleanup_created_tabs(self) -> None:
        """
        TAB CLEANUP (step 7): close EXTRA tabs THIS flow opened (the retry tabs
        tracked in self._created_handles), leaving the operator session clean.

        Crucially this NEVER closes:
          - the operator's pre-existing tabs (only flow-created handles are in
            the list), NOR
          - the CURRENTLY-ACTIVE tab. When the new-tab retry succeeded, the
            answer lives in a flow-created tab that became the active working
            tab; that survivor must be KEPT (it replaced the original blank tab,
            which the retry already closed). We only close flow-created tabs that
            are NOT the current active tab.
        Best-effort; never raises.
        """
        driver = self.driver
        created = list(getattr(self, "_created_handles", []) or [])
        if not created:
            return
        # The active tab (answer/working tab) is the survivor and is never closed.
        try:
            survivor = driver.current_window_handle
        except Exception:
            survivor = None
        for handle in created:
            if handle == survivor:
                # Keep the active working tab; just drop it from bookkeeping.
                if handle in self._created_handles:
                    try:
                        self._created_handles.remove(handle)
                    except ValueError:
                        pass
                continue
            self._close_handle(handle, restore_to=survivor)

    @staticmethod
    def _is_refusal(text: str) -> bool:
        """True if the response text is an Ask Studio refusal / no-answer."""
        if not text:
            return False
        lowered = text.lower()
        return any(marker in lowered for marker in StudioAskIndexer.REFUSAL_MARKERS)

    @staticmethod
    def _is_zero_state(text: str) -> bool:
        """
        True if the stream text is the Ask Studio ZERO-STATE suggestion list
        ("How can Ask Studio help me? / Summarize comments ...") and NOT a real
        answer. Live caveat: the stream renders this zero-state BEFORE any
        submit, so it must never be scraped/persisted as the answer.
        """
        if not text:
            return False
        lowered = text.lower()
        return any(marker in lowered for marker in StudioAskIndexer.ZERO_STATE_MARKERS)

    async def _scrape_ask_response(
        self,
        prompt: str = "",
        start_monotonic: Optional[float] = None,
        total_deadline: Optional[float] = None,
    ) -> str:
        """
        Scrape the Ask Studio response, EXTRACTING the real answer and waiting
        for it to STABILIZE.

        Fixes BOTH the false-success scrape AND the greeting-zeroing bug: the
        stream PERSISTS the greeting + suggestions + prompt echo ABOVE the answer,
        so we do NOT reject the whole stream just because "how can i help" is
        present. Each poll we EXTRACT the answer block (_extract_answer: the last
        balanced {...} with topics/content_category, else the boilerplate-stripped
        prose body) and stabilize on the EXTRACTED answer.

        LIVE-PROVEN: the real JSON index streams ~30s AFTER submit, while the
        zero-state suggestion variant is IMMEDIATELY stable at +6s and (with the
        extended ZERO_STATE_MARKERS) strips to a short chip run. We therefore only
        treat an extracted block as the answer once it is a REAL answer
        (_is_real_answer: a JSON index block OR substantial non-boilerplate prose)
        -- a short zero-state remainder NEVER stabilizes, so the loop keeps
        WAITING for the real answer that streams later. We return once the REAL
        answer STOPS GROWING for RESPONSE_STABLE_POLLS consecutive polls, or
        RESPONSE_TIMEOUT_SECONDS elapses. NO clipboard - DOM text only.

        Returns the stabilized REAL answer ("" if no real answer block ever
        materialized -> caller fails closed "ask_studio_no_answer").

        Emits a periodic "waiting for answer" heartbeat (WRE "no hang actions")
        and respects the OUTER total-runtime budget: ``total_deadline`` (a
        monotonic timestamp) caps this loop so it can never outlast the guaranteed
        ask_about_video ceiling, even when RESPONSE_TIMEOUT_SECONDS is larger.
        """
        import time as _time

        if start_monotonic is None:
            start_monotonic = _time.monotonic()
        last_beat = _time.monotonic()
        deadline = _time.monotonic() + self.RESPONSE_TIMEOUT_SECONDS
        # Honor the OUTER total-runtime budget: never poll past it.
        if total_deadline is not None:
            deadline = min(deadline, total_deadline)
        answer_text = ""
        stable_count = 0
        while _time.monotonic() < deadline:
            el = self._first_element(self.ASK_STUDIO_SELECTORS["response_stream"])
            raw = ""
            if el is not None:
                try:
                    raw = (el.text or "").strip()
                except Exception:
                    raw = ""

            # EXTRACT the real answer (DO NOT zero just because the persistent
            # greeting is present). "" while only greeting/disclaimer/processing.
            extracted = self._extract_answer(raw, prompt)

            # REAL-ANSWER GATE: a short zero-state remainder (suggestion chips that
            # slipped past the marker set) is NOT an answer -> never stabilizes;
            # keep polling for the JSON index / substantial prose that streams
            # ~30s later. Only stabilize on a JSON block or substantial prose.
            if extracted and self._is_real_answer(extracted):
                if extracted == answer_text:
                    # Real answer unchanged since last poll -> may be done.
                    stable_count += 1
                    if stable_count >= self.RESPONSE_STABLE_POLLS:
                        # Stabilized: stopped growing for N consecutive polls.
                        break
                else:
                    # Still streaming (answer grew/changed) -> reset stability.
                    answer_text = extracted
                    stable_count = 0

            last_beat = self._maybe_heartbeat("answer", start_monotonic, last_beat)
            await self._human_delay(1.0, 0.2)
        return answer_text

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
        the Studio video-edit page.

        PRIMARY (live-grounded): the shadow-rooted title textarea
        ytcp-social-suggestions-textbox#title-textarea via the deep finder (the
        flat input#title-field silently fails on the live shadow DOM). FALLBACK:
        the legacy flat input#title-field / h1.title so light-DOM pages and the
        existing mock drivers still resolve.
        """
        el = self._first_element(
            [
                self.TITLE_TEXTAREA_SELECTOR,
                "input#title-field, h1.title",
                "input#title-field",
                "h1.title",
            ]
        )
        return el is not None

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
            response timeout, or a refusal. ALSO success=False with
            error="ask_studio_timeout" (nothing persisted) if the TOTAL monotonic
            runtime exceeds ASK_TOTAL_RUNTIME_BUDGET_SECONDS (the guaranteed-
            terminating outer no-hang guard; per-loop timeouts still apply).
        """
        import asyncio

        # WRE "no hang actions": a single guaranteed-terminating OUTER guard.
        # Measured with time.monotonic() (NOT wall-clock that a test could mock
        # away) from the START of the ask flow. The per-loop timeouts still bound
        # each stage; this is the hard total-runtime ceiling beyond which we ABORT
        # and persist nothing. Tests may inject a tiny budget to force the timeout.
        ask_start_monotonic = time.monotonic()
        total_deadline = ask_start_monotonic + self.ASK_TOTAL_RUNTIME_BUDGET_SECONDS

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

        # Resolve the channel/default prompt (explicit > channel-specific >
        # generic). The PRIMARY path REBUILDS this into a single-line, video-NAMING
        # JSON prompt (_build_video_prompt) once the title is read, so Gemini (a
        # channel assistant) analyzes THIS exact video. The fallback paths still
        # use this multi-line channel prompt.
        ask_prompt = prompt or self._prompt_for_channel(channel_entry)
        # Reset per-call retry-tab tracking (no leakage across calls).
        self._created_handles = []

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

            # Studio title is in the (shadow-rooted) title textarea. Use the
            # deep finder PRIMARY (ytcp-social-suggestions-textbox#title-textarea),
            # flat input#title-field / h1.title as documented fallback.
            title = ""
            title_el = self._first_element(
                [
                    self.TITLE_TEXTAREA_SELECTOR,
                    "input#title-field, h1.title",
                    "input#title-field",
                    "h1.title",
                ]
            )
            if title_el is not None:
                try:
                    title = title_el.get_attribute("value") or title_el.text
                except Exception:
                    title = ""

            used_ask_studio = False
            ask_clicked = False
            # PRIMARY prompt: NAME the exact video (title+id+url) + request JSON.
            # Falls back to ask_prompt only if no title resolved (still id-pinned).
            primary_prompt = self._build_video_prompt(title, video_id)

            # ---- PRIMARY PATH: Ask Studio header + READINESS GATE + NEW-TAB
            # RETRY ON BLANK (the live-proven loop). Never type into a blank
            # panel; fail closed "gemini_did_not_load" if Gemini never loads. ----
            ready_state = await self._open_ask_studio_ready(
                video_id,
                start_monotonic=ask_start_monotonic,
                total_deadline=total_deadline,
            )

            # OUTER no-hang guard: if the readiness phase already blew the total
            # runtime budget, ABORT here (success=False, "ask_studio_timeout",
            # persist NOTHING) rather than proceeding to type/scrape.
            if time.monotonic() >= total_deadline:
                logger.warning(
                    f"[STUDIO-ASK] {video_id}: total runtime budget exceeded "
                    f"after readiness -> ask_studio_timeout (no persist)"
                )
                self._cleanup_created_tabs()
                return AskResult(
                    video_id=video_id,
                    title=title,
                    response_text="",
                    topics=[],
                    timestamps=[],
                    success=False,
                    error="ask_studio_timeout",
                )

            if ready_state == "blank":
                # The Studio header WAS found but Gemini stayed blank across all
                # retries -> fail closed, no ask, no persist. Clean up retry tabs.
                self._cleanup_created_tabs()
                return AskResult(
                    video_id=video_id,
                    title=title,
                    response_text="",
                    topics=[],
                    timestamps=[],
                    success=False,
                    error="gemini_did_not_load",
                )

            if ready_state == "ready":
                # READY: confirm the prompt box + stream resolved (open verified
                # via CHILDREN, not the dialog host's visibility), then type +
                # submit ONCE.
                prompt_box = self._first_element(self.ASK_STUDIO_SELECTORS["prompt_box"])
                stream = self._first_element(self.ASK_STUDIO_SELECTORS["response_stream"])
                if prompt_box is not None and stream is not None:
                    try:
                        # NEWLINE-SAFE human-cadence typing (no bare "\n" -> no
                        # implicit ENTER per line), then submit EXACTLY ONCE (#825).
                        self._type_prompt_human(prompt_box, primary_prompt)
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
            else:
                # "no_header": legacy-only DOM -> proceed to the watch-page /
                # popup fallback below (preserves the legacy fallback path).
                logger.info("[STUDIO-ASK] Ask Studio header absent - legacy fallback")

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
                self._cleanup_created_tabs()
                return AskResult(
                    video_id=video_id,
                    title=title,
                    response_text="",
                    topics=[],
                    timestamps=[],
                    success=False,
                    error="Could not open Ask Studio or any fallback Ask path",
                )

            # ---- Scrape + EXTRACT the real answer from DOM (NO clipboard).
            # _scrape_ask_response strips the persistent greeting/suggestions +
            # processing + disclaimer and returns ONLY the answer block. Fails
            # closed. ----
            if used_ask_studio:
                response_text = await self._scrape_ask_response(
                    primary_prompt,
                    start_monotonic=ask_start_monotonic,
                    total_deadline=total_deadline,
                )
            else:
                # Legacy fallback: wait then scrape legacy response containers.
                await self._human_delay(5.0, 0.5)
                response_text = ""
                try:
                    response_el = self.driver.find_element(
                        "css selector", ".gemini-response, .response-content"
                    )
                    response_text = self._extract_answer(
                        (response_el.text or "").strip(), ask_prompt
                    )
                except Exception:
                    response_text = ""
                if not response_text:
                    # As a last resort scrape the Ask Studio stream selectors too.
                    response_text = await self._scrape_ask_response(
                        ask_prompt,
                        start_monotonic=ask_start_monotonic,
                        total_deadline=total_deadline,
                    )

            # OUTER no-hang guard: if the answer-capture phase consumed the total
            # runtime budget without a real answer, report "ask_studio_timeout"
            # (the guaranteed-terminating ceiling) rather than the generic
            # "ask_studio_no_answer". Either way NOTHING is persisted.
            if not response_text and time.monotonic() >= total_deadline:
                logger.warning(
                    f"[STUDIO-ASK] {video_id}: total runtime budget exceeded "
                    f"during answer capture -> ask_studio_timeout (no persist)"
                )
                self._cleanup_created_tabs()
                return AskResult(
                    video_id=video_id,
                    title=title,
                    response_text="",
                    topics=[],
                    timestamps=[],
                    success=False,
                    error="ask_studio_timeout",
                )

            if not response_text:
                # No ANSWER block materialized within the timeout (stream was only
                # greeting/disclaimer/processing) -> FAIL CLOSED, persist nothing.
                logger.warning(
                    f"[STUDIO-ASK] {video_id}: no answer block within timeout (fail closed)"
                )
                self._cleanup_created_tabs()
                return AskResult(
                    video_id=video_id,
                    title=title,
                    response_text="",
                    topics=[],
                    timestamps=[],
                    success=False,
                    error="ask_studio_no_answer",
                )

            # FAIL CLOSED on a refusal / no-answer: never persist a refusal as
            # index content (transcript_summary). success=False, store nothing.
            if self._is_refusal(response_text):
                logger.warning(
                    f"[STUDIO-ASK] {video_id}: Ask Studio refusal/no-answer (fail closed)"
                )
                self._cleanup_created_tabs()
                return AskResult(
                    video_id=video_id,
                    title=title,
                    response_text="",
                    topics=[],
                    timestamps=[],
                    success=False,
                    error="ask_studio_no_answer",
                )

            # Parse response (JSON block FIRST, prose fallback). content_category
            # is enum-normalized; content_category_raw keeps Gemini's rich label.
            parsed = self._parse_ask_response(response_text)
            content_category = parsed.get("content_category", "other")
            content_category_raw = parsed.get("content_category_raw")
            logger.info(
                f"[STUDIO-ASK] Content category detected: {content_category}"
                f" (raw={content_category_raw!r})"
            )

            # TAB CLEANUP (step 7): close any retry tabs THIS flow opened, leaving
            # the operator session clean (success path).
            self._cleanup_created_tabs()

            return AskResult(
                video_id=video_id,
                title=title,
                response_text=response_text,
                topics=parsed.get("topics", []),
                timestamps=parsed.get("segments", []),
                success=True,
                content_category=content_category,
                content_category_raw=content_category_raw,
            )

        except Exception as e:
            logger.error(f"[STUDIO-ASK] Error for {video_id}: {e}")
            # Best-effort: never leak retry tabs THIS flow opened on an error.
            try:
                self._cleanup_created_tabs()
            except Exception:  # pragma: no cover - defensive
                pass
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

                    # OBSERVE-MODE acoustic music/talk label (flag-gated, default OFF;
                    # SHORTS_MUSIC_LABEL_OBSERVE_PHASE1). When YT_AUDIO_LABEL_OBSERVE=1
                    # we download audio + acoustically classify it, storing audio_label
                    # as a SIBLING to content_category (NEVER mutating content_category)
                    # and emitting a compare-breadcrumb so 012 can observe acoustic-vs-
                    # LLM accuracy. This NEVER gates scheduling and NEVER breaks indexing
                    # on failure (the helper returns None instead of raising).
                    observed = _observe_audio_label(vid_id)
                    if observed:
                        index_data.metadata["audio_label"] = observed["audio_label"]
                        index_data.metadata["audio_label_confidence"] = observed["audio_label_confidence"]
                        # Compare-breadcrumb: acoustic audio_label vs LLM content_category.
                        logger.info(
                            "[MUSIC-OBSERVE] %s audio_label=%s confidence=%s content_category=%s",
                            vid_id,
                            observed["audio_label"],
                            observed["audio_label_confidence"],
                            index_data.metadata.get("content_category"),
                        )

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
