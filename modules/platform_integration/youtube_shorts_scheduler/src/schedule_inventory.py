"""Qualified, bounded reads of the existing Studio scheduled-content list.

An upload-date column is never schedule evidence. A visibility slot or an
explicitly schedule-labeled date cell supplies one. Failed reads do not claim zero.
"""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlsplit

MAX_PAGES = 100
_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")
_DATE = re.compile(r"\b([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\b")
_TIME = re.compile(r"\b(\d{1,2}:\d{2}\s*[AP]M)\b", re.I)

# One read binds rows, applied chips, native receiving channel and URL together.
# These selectors are grounded in the existing DOM/CPS/Skillz owners. Offline
# fixtures qualify the contract; installed browser selectors still need live QA.
_SHADOW_QUERY_SCRIPT = r"""
const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
// Same open-shadow traversal as the existing shadow_dom_finder/Skillz owner;
// keep one synchronous snapshot so a later account/filter read cannot bless
// earlier rows from another receiving page.
function all(root, selector) {
    if (!root) return [];
    const out = Array.from(root.querySelectorAll(selector));
    if (root.shadowRoot) out.push(...all(root.shadowRoot, selector));
    for (const node of root.querySelectorAll('*')) {
        if (node.shadowRoot) out.push(...all(node.shadowRoot, selector));
    }
    return Array.from(new Set(out));
}
const first = (root, selector) => all(root, selector).find(visible) || null;
"""

FILTER_STATE_SCRIPT = _SHADOW_QUERY_SCRIPT + r"""
const filter = first(document, 'ytcp-video-filter');
return {chipTexts: all(filter, 'ytcp-chip').filter(visible).map(el => (el.innerText || el.textContent || '').trim()), url: window.location.href};
"""

SCHEDULED_PAGE_SCRIPT = _SHADOW_QUERY_SCRIPT + r"""
const list = first(document, 'ytcp-video-section-content#video-list, ytcp-video-section-content');
const rows = all(list, 'ytcp-video-row').filter(visible);
const filter = first(document, 'ytcp-video-filter');
const chips = all(filter, 'ytcp-chip').filter(visible);
const footer = first(document, 'ytcp-table-footer') || document;
const next = first(footer, "button[aria-label='Navigate to the next page'], #navigate-after");
const previous = first(footer, "button[aria-label='Navigate to the previous page'], #navigate-before");
const nativeLocations = [
    window.ytcfg && typeof window.ytcfg.get === 'function' ? window.ytcfg.get('CHANNEL_ID') : null,
    window.yt && window.yt.config_ ? window.yt.config_.CHANNEL_ID : null
];
const nativeIds = Array.from(new Set(nativeLocations.filter(value => typeof value === 'string' && value.length > 0)));
const text = list ? (list.innerText || '') : '';
const loading = all(list, '[aria-busy="true"], tp-yt-paper-spinner[active]').some(visible);
return {
    channel_id: nativeIds.length === 1 ? nativeIds[0] : null,
    url: window.location.href,
    chip_texts: chips.map(el => (el.innerText || el.textContent || '').trim()),
    search_text: (first(filter, 'input#text-input') || {}).value || '',
    loading: loading,
    empty: rows.length === 0 && !!list && /(^|\n)\s*(No videos found|No matching videos|No videos)\s*(\n|$)/i.test(text),
    next_page: next && visible(next) ? !(next.disabled || next.hasAttribute('disabled') || next.getAttribute('aria-disabled') === 'true') : null,
    previous_page: previous && visible(previous) ? !(previous.disabled || previous.hasAttribute('disabled') || previous.getAttribute('aria-disabled') === 'true') : null,
    rows: rows.map(row => {
        const link = first(row, 'a#video-title, a[href*="/video/"]');
        const href = link ? link.getAttribute('href') || '' : '';
        const match = href.match(/\/video\/([^/?]+)/);
        const visibility = first(row, '.cell-body.tablecell-visibility, .tablecell-visibility');
        const date = first(row, 'div.tablecell-date');
        return {video_id: match ? match[1] : '', title: link ? (link.textContent || '').trim() : '',
            schedule_text: visibility ? (visibility.innerText || visibility.textContent || '').trim() : '',
            date_text: date ? (date.innerText || date.textContent || '').trim() : '',
            date_label: date ? [date.getAttribute('aria-label'), date.getAttribute('title')].filter(Boolean).join('\n') : ''};
    })
};
"""


def failed_inventory(channel_id: str, reason: str) -> dict:
    """Create an unknown result, including for navigation failures."""
    return {"status": "failed", "channel_id": channel_id, "channel_verified": False,
            "filter_verified": False, "start_verified": False, "pagination_complete": False,
            "pages_read": 0, "rows_seen": 0, "rows_parsed": 0,
            "observed_scheduled_count": 0, "total_scheduled": None,
            "videos": [], "unparsed_rows": [], "issues": [reason]}


def _channel_matches(page: dict, channel_id: str) -> bool:
    try:
        url = urlsplit(page.get("url", ""))
        parts = url.path.strip("/").split("/")
        return (url.scheme == "https" and url.netloc == "studio.youtube.com"
                and parts[:3] == ["channel", channel_id, "videos"]
                and len(parts) == 4 and parts[3] in {"short", "upload"}
                and page.get("channel_id") == channel_id)
    except (TypeError, ValueError):
        return False


def _filter_matches(page: dict) -> bool:
    chips = page.get("chip_texts")
    if not isinstance(chips, list) or len(chips) != 1 or page.get("search_text"):
        return False
    # No URL-only proof, mixed visibility, extra title/search filter or unchecked
    # click acknowledgement can certify a whole-channel scheduled inventory.
    chip = " ".join(str(chips[0]).casefold().split())
    return chip in {"has schedule", "scheduled", "visibility: has schedule",
                    "visibility: scheduled", "visibility has schedule", "visibility scheduled"}


def _date_value(text: str) -> str | None:
    for pattern in ("%b %d, %Y", "%B %d, %Y"):
        try:
            date = datetime.strptime(" ".join(text.split()), pattern)
            return f"{date:%b} {date.day}, {date.year}"
        except ValueError:
            pass
    return None


def _time_value(text: str) -> str | None:
    try:
        time = datetime.strptime(re.sub(r"\s*([AP]M)$", r" \1", text.upper()), "%I:%M %p")
        return f"{time.hour % 12 or 12}:{time.minute:02d} {'AM' if time.hour < 12 else 'PM'}"
    except ValueError:
        return None


def _slot(text: str) -> tuple[str, str] | None:
    dates, times = _DATE.findall(text), _TIME.findall(text)
    if len(dates) != 1 or len(times) != 1:
        return None
    date, time = _date_value(dates[0]), _time_value(times[0])
    return (date, time) if date and time else None


def parse_scheduled_row(row: dict) -> dict | None:
    """Validate exact identity and an explicitly scheduled slot, never upload date."""
    if (not isinstance(row, dict) or not isinstance(row.get("video_id"), str)
            or not _VIDEO_ID.fullmatch(row["video_id"])):
        return None
    values = [row.get(key, "") for key in ("schedule_text", "date_text", "date_label")]
    if any(not isinstance(value, str) or len(value) > 4096 for value in values):
        return None
    visibility, date_text, date_label = [value.replace("\u202f", " ").replace("\u00a0", " ") for value in values]
    if not re.match(r"\s*Scheduled\b", visibility, re.I):
        return None
    candidates = [(visibility, "visibility_cell")]
    # Modern Date cells may supply a schedule only when their OWN text/tooltip
    # explicitly says Scheduled. A generic date next to Scheduled is insufficient.
    if not re.search(r"\b(uploaded|published)\b", date_text + " " + date_label, re.I):
        if re.match(r"\s*Scheduled\b", date_text, re.I):
            candidates.append((date_text, "schedule_labeled_date_cell"))
        if re.match(r"\s*Scheduled\b", date_label, re.I):
            candidates.append((date_label if _slot(date_label) else date_label + "\n" + date_text,
                               "schedule_labeled_date_cell"))
    parsed = [(slot, source) for text, source in candidates if (slot := _slot(text)) is not None]
    if not parsed or len({slot for slot, _ in parsed}) != 1:
        return None
    (date, time), source = parsed[0]
    if (any(_date_value(text) != date for text in _DATE.findall(visibility))
            or any(_time_value(text) != time for text in _TIME.findall(visibility))):
        return None
    return {"video_id": row["video_id"], "title": str(row.get("title", ""))[:256],
            "date": date, "time": time, "date_text": date_text, "date_label": date_label,
            "visibility_text": visibility, "schedule_source": source}


def _qualified_page(dom, channel_id: str, page_number: int, result: dict) -> dict | None:
    try:
        page = dom.driver.execute_script(SCHEDULED_PAGE_SCRIPT)
    except Exception:
        result["issues"].append("page_read_failed")
        return None
    if not isinstance(page, dict) or not _channel_matches(page, channel_id):
        result["channel_verified"] = False
        result["issues"].append("receiving_channel_unverified")
        return None
    if not _filter_matches(page):
        result["filter_verified"] = False
        result["issues"].append("scheduled_filter_unverified")
        return None
    rows = page.get("rows")
    if page.get("loading") is not False or not isinstance(rows, list) or len(rows) > 1000:
        result["issues"].append("page_rows_unqualified")
        return None
    result.update(channel_verified=True, filter_verified=True, pages_read=page_number)
    if page_number == 1:
        if page.get("previous_page") is not False:
            result["issues"].append("pagination_start_unverified")
            return None
        result["start_verified"] = True
    elif page.get("previous_page") is not True:
        result["issues"].append("pagination_progress_unverified")
        return None
    return page


def _append_page_rows(page: dict, result: dict, seen: set, seen_pages: set) -> bool:
    rows = page["rows"]
    fingerprint = tuple((str(row.get("video_id", ""))[:512], str(row.get("schedule_text", ""))[:4097])
                        if isinstance(row, dict) else ("invalid_row", "") for row in rows)
    if fingerprint in seen_pages:
        result["issues"].append("repeated_video_or_page")
        return False
    seen_pages.add(fingerprint)
    result["rows_seen"] += len(rows)
    if not rows and page.get("empty") is not True:
        result["issues"].append("empty_state_unverified")
        return False
    repeated = False
    for row_index, row in enumerate(rows):
        parsed = parse_scheduled_row(row)
        if parsed is None:
            result["unparsed_rows"].append({"reason": "scheduled_slot_unparsed", "row_index": result["rows_seen"] - len(rows) + row_index,
                **({key: str(row.get(key, ""))[:4096] for key in ("video_id", "schedule_text", "date_text", "date_label")} if isinstance(row, dict) else {})})
            continue
        if parsed["video_id"] in seen:
            repeated = True
            continue
        seen.add(parsed["video_id"])
        result["videos"].append(parsed)
    if repeated:
        result["issues"].append("repeated_video_or_page")
    return not repeated


def collect_scheduled_inventory(dom, channel_id: str, *, max_pages: int = MAX_PAGES) -> dict:
    """Read current filtered list; never navigate an account or alter content."""
    result = failed_inventory(channel_id, "not_read")
    result["issues"] = []
    if not isinstance(channel_id, str) or not channel_id or type(max_pages) is not int or not 1 <= max_pages <= MAX_PAGES:
        result["issues"] = ["inventory_request_invalid"]
        return result
    seen, seen_pages = set(), set()
    for page_number in range(1, max_pages + 1):
        page = _qualified_page(dom, channel_id, page_number, result)
        if page is None or not _append_page_rows(page, result, seen, seen_pages):
            break
        next_page = page.get("next_page")
        if type(next_page) is not bool:
            result["issues"].append("pagination_unknown")
            break
        if not next_page:
            result["pagination_complete"] = True
            break
        if not page["rows"]:
            result["issues"].append("empty_page_has_successor")
            break
        if page_number == max_pages:
            result["issues"].append("page_limit")
            break
        try:
            dom.click_next_page()
        except Exception:
            result["issues"].append("pagination_failed")
            break
    result["rows_parsed"] = len(result["videos"])
    result["observed_scheduled_count"] = len(result["videos"])
    if result["unparsed_rows"]:
        result["issues"].append("unparsed_scheduled_rows")
    complete = result["pagination_complete"] and not result["issues"]
    result["status"] = "complete" if complete else ("partial" if result["pages_read"] else "failed")
    result["total_scheduled"] = len(result["videos"]) if complete else None
    return result


def qualified_inventory(inventory: object, channel_id: str, videos: list | None = None) -> bool:
    """Guard destructive absence-based consumers against incomplete/mismatched reads."""
    if not isinstance(channel_id, str) or not channel_id or not isinstance(inventory, dict):
        return False
    rows = inventory.get("videos")
    if not isinstance(rows, list):
        return False
    ids = []
    for row in rows:
        if not isinstance(row, dict) or row.get("schedule_source") not in {"visibility_cell", "schedule_labeled_date_cell"}:
            return False
        parsed = parse_scheduled_row({**row, "schedule_text": row.get("visibility_text", "")})
        if parsed is None or any(row.get(key) != parsed[key] for key in ("video_id", "date", "time", "schedule_source")):
            return False
        ids.append(row["video_id"])
    return (len(set(ids)) == len(ids) and inventory.get("status") == "complete" and inventory.get("channel_id") == channel_id
            and inventory.get("channel_verified") is True and inventory.get("filter_verified") is True
            and inventory.get("start_verified") is True and inventory.get("pagination_complete") is True and inventory.get("issues") == []
            and inventory.get("unparsed_rows") == [] and isinstance(rows, list)
            and type(inventory.get("pages_read")) is int and 1 <= inventory["pages_read"] <= MAX_PAGES
            and type(inventory.get("rows_seen")) is int and inventory["rows_seen"] == len(rows)
            and type(inventory.get("rows_parsed")) is int and inventory["rows_parsed"] == len(rows)
            and type(inventory.get("total_scheduled")) is int and inventory["total_scheduled"] == len(rows)
            and (videos is None or videos == rows))
