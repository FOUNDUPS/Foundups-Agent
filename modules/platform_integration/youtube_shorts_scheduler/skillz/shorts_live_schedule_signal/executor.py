#!/usr/bin/env python3
"""
shorts_live_schedule_signal - SKILLz Executor

Two READ-ONLY live signals scraped from the YouTube Studio shorts list:

  1. ACCURATE scheduled count via the Filter chip-bar "Has schedule" checkbox.
     This fixes the [CPS-AUDIT] false-0 bug: today
     `content_page_scheduler.audit_calendar()` applies the OLD sidebar
     `#filter-icon -> "Visibility" -> "Has schedule"` flow
     (`_apply_visibility_filter_via_ui`, content_page_scheduler.py:313-412) which
     TIMES OUT on the Edge channels (foundups/antifaFM); the filter never lands,
     `get_scheduled_videos_detailed()` then scrapes ZERO rows and the audit
     reports "Total scheduled: 0" (content_page_scheduler.py:992) even though the
     tracker holds 131 / 55. 012's reliable path is the chip-bar input ->
     "Has schedule" checkbox in the filter dialog. We click THAT path with the
     shadow-piercing finder (Studio is shadow-rooted; flat selectors silently
     fail) and -- critically -- when the filter cannot be applied we return
     scheduled_count = None (UNKNOWN), NEVER a false 0.

  2. Per-video VIEW count parsed from each row's views column -> a low-viewed
     signal (012: "re-schedule low viewed shorts"). Views are parsed from the
     row's views cell text / aria-label into an int (e.g. "1.2K views" -> 1200).

WSP Compliance:
    WSP 95: SKILLz Wardrobe Protocol (micro chain-of-thought + pattern fidelity)
    WSP 77: Agent Coordination (Qwen/daemon consumes the signal)
    WSP 91: DAEmon Observability (breadcrumb on every run)
    WSP 60/48: Pattern Memory outcome on every run (WRE self-improvement testbed)
    WSP 84: Code Reuse -- pierces the Studio shadow DOM with the EXISTING
            foundups_selenium.shadow_dom_finder (first_deep/find_deep), the same
            helper proven by the Studio-Ask work (#825/#827).
    WSP 27: Phase 0 KNOWLEDGE (read/verify before any act).

Read-only:
    - Reads the live shorts list (DOM). Ticks a filter checkbox to FILTER the
      view -- this is a view-state read aid, NOT a content mutation.
    - Never schedules, never edits metadata, never opens a publish path.

Malleable seams (intentional):
    - PARSING is behind pure functions (`parse_view_count`, `parse_row_signal`,
      `summarize_rows`) -- swap the parser without touching scrape/orchestration.
    - The DOM SCRAPE is injected via `scrape_fn` (default: `scrape_live_rows`,
      which uses shadow_dom_finder). Tests inject a mock-DOM scrape; live runs
      use the real one. The orchestration math is identical either way.

Usage (agent / daemon):
    from .executor import read_live_schedule_signal
    signal = read_live_schedule_signal(driver, channel_id="UC...")
    if signal["scheduled_count"] is None:
        ...  # filter could not be applied -> UNKNOWN (do NOT treat as 0)

Usage (--agent-command surface):
    youtube action live_schedule_signal channel=foundups
    (the adapter spawns run_skill.py --channel foundups --json)
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

SOURCE_DAE = "youtube_shorts_scheduler"
SKILL_NAME = "shorts_live_schedule_signal"

# 012: shorts under this view count are "low viewed" candidates for re-scheduling.
DEFAULT_LOW_VIEW_THRESHOLD = 100

# Sentinel: a row whose views cell could not be parsed. Distinct from 0 views.
VIEWS_UNKNOWN = None


# ---------------------------------------------------------------------------
# Grounded Studio DOM (012-confirmed; re-confirm live before graduation).
# These mirror the structure 012 gave and the existing content_page_scheduler
# selectors. They are consumed by the shadow-piercing finder, NOT flat CSS.
# ---------------------------------------------------------------------------

# Filter chip-bar text input (placeholder "Filter").
FILTER_INPUT_CHAIN = ["ytcp-video-filter#video-filter ytcp-chip-bar#chip-bar input#text-input"]
# Fallback chain: walk into the chip-bar first, then the input (shadow steps).
FILTER_INPUT_CHAIN_FALLBACK = [
    "ytcp-video-filter#video-filter",
    "ytcp-chip-bar#chip-bar",
    "input#text-input",
]
# The filter dialog that opens after focusing the chip-bar input.
FILTER_DIALOG_SELECTORS = ["ytcp-filter-dialog tp-yt-paper-dialog#dialog"]
# Video rows live under the list section.
VIDEO_ROW_SELECTOR = "ytcp-video-row"
VIDEO_LIST_SELECTOR = "ytcp-video-section-content#video-list"


@dataclass
class RowSignal:
    """One scraped+parsed shorts-list row."""

    video_id: str
    scheduled: bool
    scheduled_date: Optional[str]
    views: Optional[int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_id": self.video_id,
            "scheduled": self.scheduled,
            "scheduled_date": self.scheduled_date,
            "views": self.views,
        }


# === Malleable seam 1: pure parsing ========================================

def parse_view_count(text: Optional[str]) -> Optional[int]:
    """Parse a Studio views cell into an int (or None if unparseable).

    Handles the formats Studio renders in the views column:
        "1,234 views" -> 1234
        "1.2K views"  -> 1200
        "3.4M"        -> 3400000
        "0"           -> 0
        "-" / "" / None / "No views" -> None (UNKNOWN, distinct from 0)

    Pure + deterministic. The orchestration treats None as UNKNOWN (it is NOT
    counted as a low-viewed video).
    """
    if text is None:
        return None
    s = str(text).strip().lower()
    if not s:
        return None
    # Strip the trailing word "views" / "view".
    s = re.sub(r"\bviews?\b", "", s).strip()
    if not s or s in ("-", "--", "no", "no views", "none"):
        return None

    m = re.search(r"([0-9][0-9.,]*)\s*([kmb])?", s)
    if not m:
        return None
    num_raw, suffix = m.group(1), m.group(2)

    # "1,234" -> 1234 ; "1.2" (with K) -> 1.2 ; "1.234" plain thousands -> 1234.
    if suffix:
        # Suffix present: the dot is a decimal point (1.2K).
        try:
            value = float(num_raw.replace(",", ""))
        except ValueError:
            return None
        mult = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}[suffix]
        return int(round(value * mult))

    # No suffix: commas and dots are thousands separators -> strip both.
    digits = num_raw.replace(",", "").replace(".", "")
    if not digits.isdigit():
        return None
    return int(digits)


def parse_row_signal(raw: Dict[str, Any]) -> RowSignal:
    """Turn a raw scraped row dict into a typed RowSignal (pure).

    Expected raw keys (whatever the scrape produced):
        video_id: str
        visibility_text: str  (e.g. "Scheduled", "Unlisted")
        scheduled_date: str | None
        views_text: str | None

    The "scheduled" boolean is derived from the visibility label-span text
    (span.label-span -> "Scheduled"), matching the live row structure.
    """
    visibility_text = (raw.get("visibility_text") or "").strip().lower()
    scheduled = "scheduled" in visibility_text
    scheduled_date = raw.get("scheduled_date") or None
    if not scheduled:
        scheduled_date = None  # only carry a date for genuinely-scheduled rows
    return RowSignal(
        video_id=str(raw.get("video_id") or "").strip(),
        scheduled=scheduled,
        scheduled_date=scheduled_date,
        views=parse_view_count(raw.get("views_text")),
    )


def summarize_rows(
    rows: List[RowSignal],
    *,
    low_view_threshold: int = DEFAULT_LOW_VIEW_THRESHOLD,
) -> Dict[str, Any]:
    """Aggregate parsed rows into the read-only signal summary (pure).

    Returns scheduled_count, the scheduled videos, and the low-viewed shorts
    (views known AND strictly below the threshold). Rows with UNKNOWN views are
    NEVER counted as low-viewed.
    """
    scheduled = [r for r in rows if r.scheduled]
    low_viewed = [
        r for r in rows
        if r.views is not None and r.views < low_view_threshold
    ]
    return {
        "row_count": len(rows),
        "scheduled_count": len(scheduled),
        "scheduled_videos": [r.to_dict() for r in scheduled],
        "low_view_threshold": low_view_threshold,
        "low_viewed_count": len(low_viewed),
        "low_viewed_videos": [r.to_dict() for r in low_viewed],
        "videos": [r.to_dict() for r in rows],
    }


# === Malleable seam 2: the live DOM scrape (shadow-pierced) =================

def _apply_has_schedule_filter(driver) -> bool:
    """Click the Filter chip-bar input, then tick "Has schedule" in the dialog.

    Uses the EXISTING shadow-piercing finder (WSP 84) because Studio is
    shadow-rooted and flat selectors silently miss the chip-bar / dialog.

    Returns True only if the "Has schedule" checkbox was found AND ticked.
    Any failure -> False (caller maps that to UNKNOWN, never false-0).
    """
    try:
        from modules.infrastructure.foundups_selenium.src.shadow_dom_finder import (
            first_deep,
        )
    except Exception as exc:  # pragma: no cover - import guard
        logger.warning(f"[{SKILL_NAME}] shadow_dom_finder unavailable: {exc}")
        return False

    # Step 1: focus the chip-bar filter input to open the filter dialog.
    chip_input = first_deep(driver, [FILTER_INPUT_CHAIN[0], FILTER_INPUT_CHAIN_FALLBACK])
    if chip_input is None:
        logger.warning(f"[{SKILL_NAME}] filter chip-bar input not found (deep)")
        return False
    try:
        chip_input.click()
    except Exception as exc:
        logger.warning(f"[{SKILL_NAME}] filter chip-bar input click failed: {exc}")
        return False

    # Step 2: wait briefly for the filter dialog, then find the "Has schedule"
    # checkbox label inside it. We search labels deep and match the text.
    dialog = None
    for _ in range(10):
        dialog = first_deep(driver, FILTER_DIALOG_SELECTORS)
        if dialog is not None:
            break
        time.sleep(0.2)
    if dialog is None:
        logger.warning(f"[{SKILL_NAME}] filter dialog did not open")
        return False

    # Find a clickable "Has schedule" label/checkbox within the dialog subtree.
    checkbox = _find_has_schedule_option(driver, dialog)
    if checkbox is None:
        logger.warning(f"[{SKILL_NAME}] 'Has schedule' option not found in dialog")
        return False
    try:
        checkbox.click()
    except Exception as exc:
        logger.warning(f"[{SKILL_NAME}] 'Has schedule' click failed: {exc}")
        return False

    # Give the list a moment to re-filter.
    time.sleep(0.5)
    return True


def _find_has_schedule_option(driver, dialog):
    """Locate the "Has schedule" label/checkbox in the filter dialog subtree.

    Tries label elements first (the dialog renders a `label` with the text
    "Has schedule"), then a couple of paper-checkbox fallbacks. Text match is
    case-insensitive and tolerant of surrounding whitespace.
    """
    from modules.infrastructure.foundups_selenium.src.shadow_dom_finder import (
        find_deep,
    )

    # Walk the dialog subtree for candidate option elements.
    for sel in ("label", "tp-yt-paper-checkbox", "ytcp-checkbox-lit", "div.label"):
        candidate = find_deep(dialog, sel)
        # find_deep returns only the FIRST match; we need to scan text, so use a
        # JS scan over the dialog subtree for any element whose trimmed text is
        # exactly/contains "has schedule".
        # (candidate is just a cheap existence probe.)
        if candidate is None:
            continue
        match = _scan_text_for_has_schedule(driver, dialog, sel)
        if match is not None:
            return match
    # Last resort: scan all labels in the dialog.
    return _scan_text_for_has_schedule(driver, dialog, "*")


_SCAN_HAS_SCHEDULE_JS = r"""
const root = arguments[0];
const sel = arguments[1];
function* walk(node) {
    if (!node) return;
    let nodes;
    try { nodes = node.querySelectorAll(sel); } catch (e) { nodes = []; }
    for (const n of nodes) yield n;
    let all;
    try { all = node.querySelectorAll('*'); } catch (e) { return; }
    for (const child of all) {
        if (child.shadowRoot) { yield* walk(child.shadowRoot); }
    }
}
for (const el of walk(root)) {
    const t = (el.textContent || '').trim().toLowerCase();
    if (t === 'has schedule' || (t.includes('has schedule') && t.length < 40)) {
        return el;
    }
}
return null;
"""


def _scan_text_for_has_schedule(driver, dialog, sel):
    """JS-scan the dialog subtree (incl. shadow roots) for a 'Has schedule' element."""
    try:
        return driver.execute_script(_SCAN_HAS_SCHEDULE_JS, dialog, sel)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug(f"[{SKILL_NAME}] has-schedule scan failed for {sel!r}: {exc}")
        return None


_SCRAPE_ROWS_JS = r"""
// Scrape shorts-list rows across shadow roots. Returns raw dicts only; all
// parsing happens in Python (pure seam). No mutation.
function findInShadowAll(root, sel, out) {
    if (!root) return;
    let direct;
    try { direct = root.querySelectorAll(sel); } catch (e) { direct = []; }
    for (const d of direct) out.push(d);
    let all;
    try { all = root.querySelectorAll('*'); } catch (e) { return; }
    for (const child of all) {
        if (child.shadowRoot) findInShadowAll(child.shadowRoot, sel, out);
    }
}
function deepText(el, sel) {
    if (!el) return '';
    let hit = null;
    try { hit = el.querySelector(sel); } catch (e) {}
    if (hit) return (hit.textContent || '').trim();
    let all;
    try { all = el.querySelectorAll('*'); } catch (e) { return ''; }
    for (const c of all) {
        if (c.shadowRoot) {
            const t = deepText(c.shadowRoot.host || c, sel);
            if (t) return t;
        }
    }
    return '';
}
const rows = [];
findInShadowAll(document, 'ytcp-video-row', rows);
const out = [];
for (const row of rows) {
    // video id from the title link href.
    let video_id = '';
    let link = null;
    try { link = row.querySelector("a#video-title, a[href*='/video/']"); } catch (e) {}
    if (link) {
        const href = link.getAttribute('href') || '';
        const m = href.match(/\/video\/([^/?]+)/);
        if (m) video_id = m[1];
    }
    // visibility label-span text (e.g. "Scheduled").
    let visibility_text = '';
    try {
        const vs = row.querySelector('span.label-span');
        if (vs) visibility_text = (vs.textContent || '').trim();
    } catch (e) {}
    // scheduled date cell.
    let scheduled_date = '';
    try {
        const dc = row.querySelector('div.tablecell-date, .tablecell-date');
        if (dc) scheduled_date = (dc.textContent || '').trim().split('\n')[0];
    } catch (e) {}
    // views cell: prefer an explicit views column, else any cell containing 'view'.
    let views_text = '';
    try {
        const vc = row.querySelector(
            "#views, .tablecell-views, [class*='views'], span.cell-views"
        );
        if (vc) views_text = (vc.getAttribute('aria-label') || vc.textContent || '').trim();
    } catch (e) {}
    if (!views_text) {
        try {
            const cells = row.querySelectorAll('*');
            for (const c of cells) {
                const t = (c.textContent || '').trim();
                if (/\bviews?\b/i.test(t) && t.length < 30) { views_text = t; break; }
            }
        } catch (e) {}
    }
    out.push({
        video_id: video_id,
        visibility_text: visibility_text,
        scheduled_date: scheduled_date,
        views_text: views_text,
    });
}
return out;
"""


def scrape_live_rows(driver) -> List[Dict[str, Any]]:
    """Scrape the shorts-list rows (raw dicts) across shadow roots. No mutation.

    Returns a list of raw row dicts (video_id, visibility_text, scheduled_date,
    views_text). Parsing into typed signals happens in the pure seam.
    """
    try:
        rows = driver.execute_script(_SCRAPE_ROWS_JS)
        return list(rows or [])
    except Exception as exc:
        logger.warning(f"[{SKILL_NAME}] row scrape failed: {exc}")
        return []


# === Orchestration =========================================================

def read_live_schedule_signal(
    driver,
    *,
    channel_id: str,
    low_view_threshold: int = DEFAULT_LOW_VIEW_THRESHOLD,
    apply_filter_fn: Callable[[Any], bool] = _apply_has_schedule_filter,
    scrape_fn: Callable[[Any], List[Dict[str, Any]]] = scrape_live_rows,
) -> Dict[str, Any]:
    """Read the two live read-only signals from the shorts list (no mutation).

    Flow:
      1. Apply the "Has schedule" filter via the chip-bar input + dialog
         (shadow-pierced). If it cannot be applied -> filter_applied=False and
         scheduled_count = None (UNKNOWN). We do NOT scrape an unfiltered list
         and call its scheduled rows "the count" -- and we NEVER return 0 here.
      2. Scrape rows -> parse -> summarize: accurate scheduled_count + per-video
         views + low-viewed signal.

    Args:
        driver: Selenium WebDriver already on the channel's shorts list.
        channel_id: YouTube channel ID (from the registry; never hardcoded).
        low_view_threshold: views strictly below this => low-viewed candidate.
        apply_filter_fn: swappable "Has schedule" applier (default: real DOM).
        scrape_fn: swappable row scrape (default: real shadow-pierced scrape).

    Returns a structured signal dict. KEY CONTRACT:
        - scheduled_count is an int ONLY when filter_applied is True.
        - scheduled_count is None (UNKNOWN) when the filter could not be applied
          -- this is the false-0 fix.
    """
    patterns = {
        "has_schedule_filter_attempted": False,
        "has_schedule_filter_applied": False,
        "rows_scraped": False,
        "rows_parsed": False,
        "views_parsed": False,
    }

    patterns["has_schedule_filter_attempted"] = True
    filter_applied = bool(apply_filter_fn(driver))
    patterns["has_schedule_filter_applied"] = filter_applied

    if not filter_applied:
        # FAIL-SAFE: unknown, NOT a false 0 (the whole point of this slice).
        return {
            "success": False,
            "skill": SKILL_NAME,
            "channel_id": channel_id,
            "filter_applied": False,
            "scheduled_count": None,  # UNKNOWN
            "scheduled_count_status": "unknown_filter_not_applied",
            "low_view_threshold": low_view_threshold,
            "low_viewed_count": None,
            "low_viewed_videos": [],
            "scheduled_videos": [],
            "videos": [],
            "row_count": 0,
            "patterns": patterns,
        }

    raw_rows = scrape_fn(driver)
    patterns["rows_scraped"] = True

    parsed = [parse_row_signal(r) for r in raw_rows]
    patterns["rows_parsed"] = True
    patterns["views_parsed"] = any(r.views is not None for r in parsed)

    summary = summarize_rows(parsed, low_view_threshold=low_view_threshold)

    return {
        "success": True,
        "skill": SKILL_NAME,
        "channel_id": channel_id,
        "filter_applied": True,
        "scheduled_count": summary["scheduled_count"],  # accurate int
        "scheduled_count_status": "ok",
        "low_view_threshold": summary["low_view_threshold"],
        "low_viewed_count": summary["low_viewed_count"],
        "low_viewed_videos": summary["low_viewed_videos"],
        "scheduled_videos": summary["scheduled_videos"],
        "videos": summary["videos"],
        "row_count": summary["row_count"],
        "patterns": patterns,
    }


# === Signal emission (WSP 91 breadcrumb + WSP 60/48 PatternMemory) ==========

def _emit_breadcrumb(signal: Dict[str, Any]) -> bool:
    """Emit a live_schedule_signal breadcrumb so the WRE/overseer can learn."""
    try:
        from modules.communication.livechat.src.breadcrumb_telemetry import (
            get_breadcrumb_telemetry,
        )

        sc = signal.get("scheduled_count")
        get_breadcrumb_telemetry().store_breadcrumb(
            source_dae=SOURCE_DAE,
            event_type="live_schedule_signal",
            message=(
                f"live schedule signal ch={signal.get('channel_id')} "
                f"filter_applied={signal.get('filter_applied')} "
                f"scheduled_count={'UNKNOWN' if sc is None else sc} "
                f"low_viewed={signal.get('low_viewed_count')}"
            ),
            phase="SHORTS_LIVE_SCHEDULE_AND_VIEW_SIGNAL",
            metadata={
                "skill": SKILL_NAME,
                "channel_id": signal.get("channel_id"),
                "filter_applied": signal.get("filter_applied"),
                "scheduled_count": sc,
                "scheduled_count_status": signal.get("scheduled_count_status"),
                "low_view_threshold": signal.get("low_view_threshold"),
                "low_viewed_count": signal.get("low_viewed_count"),
                "row_count": signal.get("row_count"),
            },
        )
        return True
    except Exception as exc:  # pragma: no cover - telemetry is best-effort
        logger.warning(f"[{SKILL_NAME}] breadcrumb emit failed: {exc}")
        return False


def _store_outcome(signal: Dict[str, Any]) -> bool:
    """Store a SkillOutcome so the WRE remembers each live-signal read."""
    try:
        import json

        from modules.infrastructure.wre_core.src.pattern_memory import (
            PatternMemory,
            SkillOutcome,
        )

        success = bool(signal.get("success"))
        outcome = SkillOutcome(
            execution_id=f"{SKILL_NAME}-{uuid.uuid4().hex[:12]}",
            skill_name=SKILL_NAME,
            agent="gemma",
            timestamp=datetime.now().isoformat(),
            input_context=json.dumps(
                {
                    "channel_id": signal.get("channel_id"),
                    "low_view_threshold": signal.get("low_view_threshold"),
                },
                separators=(",", ":"),
            ),
            output_result=json.dumps(
                {
                    "filter_applied": signal.get("filter_applied"),
                    "scheduled_count": signal.get("scheduled_count"),
                    "scheduled_count_status": signal.get("scheduled_count_status"),
                    "low_viewed_count": signal.get("low_viewed_count"),
                    "row_count": signal.get("row_count"),
                },
                separators=(",", ":"),
            )[:10000],
            success=success,
            pattern_fidelity=_pattern_fidelity(signal.get("patterns") or {}),
            outcome_quality=1.0 if success else 0.0,
            execution_time_ms=0,
            step_count=len(signal.get("patterns") or {}),
            failed_at_step=None if success else 1,
            notes=f"source={SKILL_NAME} read_only=true filter_applied={signal.get('filter_applied')}",
        )
        PatternMemory().store_outcome(outcome)
        return True
    except Exception as exc:  # pragma: no cover - memory is best-effort
        logger.warning(f"[{SKILL_NAME}] pattern memory store failed: {exc}")
        return False


def _pattern_fidelity(patterns: Dict[str, bool]) -> float:
    if not patterns:
        return 0.0
    return round(sum(1 for v in patterns.values() if v) / len(patterns), 3)


def run_skill(
    *,
    channel: str,
    low_view_threshold: int = DEFAULT_LOW_VIEW_THRESHOLD,
    driver=None,
    apply_filter_fn: Callable[[Any], bool] = _apply_has_schedule_filter,
    scrape_fn: Callable[[Any], List[Dict[str, Any]]] = scrape_live_rows,
    emit_signals: bool = True,
) -> Dict[str, Any]:
    """SKILLz entry point: read the live signal for one channel and emit WRE signals.

    Resolves the channel_id from the registry (never hardcoded), reads the live
    read-only signal, and emits breadcrumb + PatternMemory. Returns a structured
    result for the daemon/Qwen to consume.

    If `driver` is None, no live browser is available -> returns a clear
    unavailable result (scheduled_count None / UNKNOWN), still NEVER a false 0.
    """
    channel_id = _resolve_channel_id(channel)

    if driver is None:
        signal = {
            "success": False,
            "skill": SKILL_NAME,
            "channel": channel,
            "channel_id": channel_id,
            "filter_applied": False,
            "scheduled_count": None,
            "scheduled_count_status": "unknown_no_driver",
            "low_view_threshold": low_view_threshold,
            "low_viewed_count": None,
            "low_viewed_videos": [],
            "scheduled_videos": [],
            "videos": [],
            "row_count": 0,
            "patterns": {},
        }
    else:
        signal = read_live_schedule_signal(
            driver,
            channel_id=channel_id or channel,
            low_view_threshold=low_view_threshold,
            apply_filter_fn=apply_filter_fn,
            scrape_fn=scrape_fn,
        )
        signal["channel"] = channel

    breadcrumb_emitted = False
    outcome_stored = False
    if emit_signals:
        breadcrumb_emitted = _emit_breadcrumb(signal)
        outcome_stored = _store_outcome(signal)

    signal["breadcrumb_emitted"] = breadcrumb_emitted
    signal["outcome_stored"] = outcome_stored
    return signal


def _resolve_channel_id(channel: str) -> Optional[str]:
    """Resolve a channel KEY (e.g. 'foundups') to its channel ID via the registry.

    Never hardcodes IDs. If `channel` is already an ID (UC...) it is returned as
    is. Returns None if it cannot be resolved (caller still degrades safely).
    """
    if channel and channel.startswith("UC"):
        return channel
    try:
        from modules.platform_integration.youtube_shorts_scheduler.src.channel_config import (
            get_channel_config,
        )

        config = get_channel_config(channel)
        if config:
            return config.get("id")
    except Exception as exc:  # pragma: no cover - registry best-effort
        logger.debug(f"[{SKILL_NAME}] channel resolve failed for {channel!r}: {exc}")
    return None


if __name__ == "__main__":  # pragma: no cover - manual smoke
    logging.basicConfig(level=logging.INFO)
    print(f"{SKILL_NAME} SKILLz - run via run_skill.py or the --agent-command surface")
