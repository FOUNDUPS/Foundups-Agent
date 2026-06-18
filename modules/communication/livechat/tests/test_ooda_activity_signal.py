"""
Unit tests for the channel-scoped OODA activity signal (RC3 observability).

PURE tests -- no live browser, no driver, no router. They pin two things:
  1. the rollup `current_activity` precedence is UNCHANGED (so should_pivot is
     byte-for-byte identical to the pre-fix Chrome-only logic), and
  2. the NEW channel-scoped truth: a stale Chrome comments tab during a live
     stream is flagged, and Edge-bound channels (FoundUps/antifaFM) are never
     mislabelled as "processing comments" just because Chrome is on a comments
     page.
"""
import pytest

from modules.communication.livechat.src.ooda_activity_signal import (
    ActivitySignal,
    derive_activity_signal,
)
from modules.infrastructure.activity_control.src.activity_control import ActivityType


def _ps(chrome=None, edge=None):
    """Build a page_state dict like the heartbeat probe produces."""
    return {
        "chrome": {"page_type": chrome} if chrome is not None else None,
        "edge": {"page_type": edge} if edge is not None else None,
    }


# ---------------------------------------------------------------------------
# Rollup precedence preserved (proves should_pivot is unchanged)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "chrome,edge,live,expected",
    [
        # Chrome on comments wins regardless of live (FIX 2026-02-21 precedence).
        ("youtube_studio_comments", "other", False, ActivityType.COMMENT_ENGAGEMENT),
        ("youtube_studio_comments", "other", True, ActivityType.COMMENT_ENGAGEMENT),
        # Chrome NOT on comments + live -> LIVE_CHAT.
        ("youtube_live", "other", True, ActivityType.LIVE_CHAT),
        ("other", None, True, ActivityType.LIVE_CHAT),
        # Chrome NOT on comments + not live -> default COMMENT_ENGAGEMENT.
        ("youtube_studio", "other", False, ActivityType.COMMENT_ENGAGEMENT),
        (None, None, False, ActivityType.COMMENT_ENGAGEMENT),
    ],
)
def test_rollup_precedence_unchanged(chrome, edge, live, expected):
    sig = derive_activity_signal(_ps(chrome, edge), live)
    assert sig.current_activity == expected


# ---------------------------------------------------------------------------
# RC3 CORE: stale Chrome comments tab during live is flagged, Edge not mislabelled
# ---------------------------------------------------------------------------

def test_rc3_stale_chrome_comments_during_live_is_flagged():
    # Live stream active, but a Chrome comments tab is open (the incident shape:
    # executor cancelled, tab is stale). Edge is NOT on a comments page.
    sig = derive_activity_signal(_ps("youtube_studio_comments", "youtube_studio"), live_chat_active=True)
    # Rollup unchanged (still COMMENT_ENGAGEMENT) ...
    assert sig.current_activity == ActivityType.COMMENT_ENGAGEMENT
    # ... but now explicitly flagged as a stale tab during live.
    assert sig.chrome_stale_during_live is True
    assert sig.is_misleading_comment_signal is True
    # Edge-bound channels (FoundUps/antifaFM) are NOT reported as processing comments.
    assert sig.edge_on_comments is False
    assert sig.edge_activity != ActivityType.COMMENT_ENGAGEMENT
    # The human-readable summary names the staleness so an observer is not misled.
    assert "STALE-TAB-DURING-LIVE" in sig.log_summary()


def test_chrome_comments_offline_is_not_flagged_stale():
    sig = derive_activity_signal(_ps("youtube_studio_comments", "other"), live_chat_active=False)
    assert sig.current_activity == ActivityType.COMMENT_ENGAGEMENT
    assert sig.chrome_stale_during_live is False
    assert sig.is_misleading_comment_signal is False
    assert "STALE-TAB-DURING-LIVE" not in sig.log_summary()


# ---------------------------------------------------------------------------
# Channel-scoping is real (non-vacuity): per-browser activities differ
# ---------------------------------------------------------------------------

def test_edge_comments_scoped_to_edge_not_chrome():
    # Only EDGE is on comments (FoundUps/antifaFM working); Chrome is idle.
    sig = derive_activity_signal(_ps("youtube_studio", "youtube_studio_comments"), live_chat_active=False)
    assert sig.edge_activity == ActivityType.COMMENT_ENGAGEMENT
    assert sig.chrome_activity != ActivityType.COMMENT_ENGAGEMENT  # Chrome group NOT doing comments
    assert sig.edge_on_comments is True
    assert sig.chrome_on_comments is False


def test_per_browser_split_is_independent():
    # Non-vacuity: when only one browser is on comments, the two activities differ
    # (proves we report per-browser truth, not a single value copied to both).
    sig = derive_activity_signal(_ps("youtube_studio_comments", "youtube_live"), live_chat_active=False)
    assert sig.chrome_activity == ActivityType.COMMENT_ENGAGEMENT
    assert sig.edge_activity == ActivityType.LIVE_CHAT
    assert sig.chrome_activity != sig.edge_activity


def test_live_chat_page_not_mislabelled_as_comments():
    sig = derive_activity_signal(_ps("youtube_live", "other"), live_chat_active=True)
    assert sig.current_activity == ActivityType.LIVE_CHAT
    assert sig.chrome_activity == ActivityType.LIVE_CHAT
    assert sig.is_misleading_comment_signal is False


# ---------------------------------------------------------------------------
# Robustness: missing / malformed page_state never raises
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ps", [None, {}, {"chrome": None, "edge": None}, {"chrome": "bad", "edge": 5}])
def test_missing_or_malformed_page_state_is_safe(ps):
    sig = derive_activity_signal(ps, live_chat_active=False)
    assert isinstance(sig, ActivitySignal)
    assert sig.current_activity == ActivityType.COMMENT_ENGAGEMENT  # else branch
    assert sig.chrome_on_comments is False
    assert sig.edge_on_comments is False
    assert sig.chrome_stale_during_live is False
