"""
OODA activity-signal derivation (RC3 observability).

Channel-scopes the heartbeat's OODA "current activity" signal across BOTH
browser groups instead of deriving it from the Chrome page-type alone.

Browser <-> channel-group binding (fixed): Chrome 9222 = Move2Japan + UnDaoDu;
Edge 9223 = FoundUps + antifaFM. A Chrome page-type therefore says NOTHING about
whether the Edge-bound channels are being processed. Deriving COMMENT_ENGAGEMENT
from the Chrome page alone made the OODA log REPORT comments-for-FoundUps while
only a (possibly stale) Chrome tab sat on the Studio comments page -- the RC3
mislabel that made a live-stream window look like a comment-processing outage,
when in reality the executor was cancelled and nothing was being processed.

This module is PURE (no driver, no router, no I/O) so it is unit-testable
without a live browser. It does NOT change the rollup `current_activity`
precedence (so the downstream `should_pivot` comparison is byte-for-byte
unchanged); it only adds the channel-scoped truth the OODA log/breadcrumb emit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from modules.infrastructure.activity_control.src.activity_control import ActivityType

# page_type values produced by the heartbeat's page-state probe
# (auto_moderator_dae.py ~2318-2361).
COMMENTS_PAGE = "youtube_studio_comments"
LIVE_PAGE = "youtube_live"


def _page_type(page_state: Optional[dict], browser: str) -> Optional[str]:
    """Safely read page_state[browser]['page_type'] without raising."""
    if not page_state:
        return None
    entry = page_state.get(browser) or {}
    if not isinstance(entry, dict):
        return None
    return entry.get("page_type")


def _activity_for_page(page_type: Optional[str]) -> Optional[ActivityType]:
    """Map a single browser's page_type to the activity it implies, or None."""
    if page_type == COMMENTS_PAGE:
        return ActivityType.COMMENT_ENGAGEMENT
    if page_type == LIVE_PAGE:
        return ActivityType.LIVE_CHAT
    return None  # not a tracked-activity page


@dataclass(frozen=True)
class ActivitySignal:
    """Channel-scoped OODA activity signal across both browser groups."""

    current_activity: ActivityType            # rollup (precedence UNCHANGED; drives should_pivot)
    chrome_activity: Optional[ActivityType]   # Chrome 9222 = Move2Japan / UnDaoDu
    edge_activity: Optional[ActivityType]     # Edge 9223 = FoundUps / antifaFM
    chrome_page_type: Optional[str]
    edge_page_type: Optional[str]
    chrome_on_comments: bool
    edge_on_comments: bool
    chrome_stale_during_live: bool            # live AND Chrome still on a comments page (likely stale tab)
    edge_stale_during_live: bool

    @property
    def is_misleading_comment_signal(self) -> bool:
        """True when the rollup says COMMENT_ENGAGEMENT but it is only a
        (likely stale) browser tab during a live stream -- the RC3 condition an
        observer must NOT read as 'comments are being processed'."""
        return self.current_activity == ActivityType.COMMENT_ENGAGEMENT and (
            self.chrome_stale_during_live or self.edge_stale_during_live
        )

    def log_summary(self) -> str:
        """Human-readable, channel-scoped one-liner for the OODA log."""
        def fmt(a: Optional[ActivityType]) -> str:
            return a.name if a is not None else "none"

        summary = (
            f"chrome(9222 M2J/UnDaoDu)={fmt(self.chrome_activity)}, "
            f"edge(9223 FoundUps/antifaFM)={fmt(self.edge_activity)}"
        )
        if self.chrome_stale_during_live or self.edge_stale_during_live:
            summary += " [STALE-TAB-DURING-LIVE: a comments page is open but NOT active processing]"
        return summary


def derive_activity_signal(page_state: Optional[dict], live_chat_active: bool) -> ActivitySignal:
    """
    Derive the channel-scoped OODA activity signal from BOTH browsers' page state.

    The rollup `current_activity` preserves the historical precedence EXACTLY
    (Chrome-comments wins -> else live -> else COMMENT_ENGAGEMENT) so the
    downstream should_pivot comparison is unchanged. The per-browser activities
    and the stale-during-live flags are the new, honest, channel-scoped signal.
    """
    chrome_pt = _page_type(page_state, "chrome")
    edge_pt = _page_type(page_state, "edge")
    chrome_on_comments = chrome_pt == COMMENTS_PAGE
    edge_on_comments = edge_pt == COMMENTS_PAGE

    # Rollup precedence preserved byte-for-byte (auto_moderator_dae.py:2388-2404).
    if chrome_on_comments:
        current = ActivityType.COMMENT_ENGAGEMENT
    elif live_chat_active:
        current = ActivityType.LIVE_CHAT
    else:
        current = ActivityType.COMMENT_ENGAGEMENT

    return ActivitySignal(
        current_activity=current,
        chrome_activity=_activity_for_page(chrome_pt),
        edge_activity=_activity_for_page(edge_pt),
        chrome_page_type=chrome_pt,
        edge_page_type=edge_pt,
        chrome_on_comments=chrome_on_comments,
        edge_on_comments=edge_on_comments,
        chrome_stale_during_live=bool(live_chat_active and chrome_on_comments),
        edge_stale_during_live=bool(live_chat_active and edge_on_comments),
    )
