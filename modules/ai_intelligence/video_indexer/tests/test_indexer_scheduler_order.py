"""
Guard test: the auto_moderator scheduler order is comments -> index -> schedule.

Phase 1 does NOT change the scheduler. This static assertion documents and
locks the existing PHASE 1 (comments) -> PHASE 2 (video indexing) ->
PHASE 3 (shorts scheduling) ordering so a future regression (index AFTER
schedule) is caught. Re-ordering is deferred to INDEX_BEFORE_SHORTS_SCHEDULE_PHASE3.

This reads source text only - no live YouTube, no browser, no network.
"""

from pathlib import Path


def _dae_source() -> str:
    # Resolve relative to this test file so it works in any worktree.
    repo_root = Path(__file__).resolve().parents[4]
    dae = (
        repo_root
        / "modules"
        / "communication"
        / "livechat"
        / "src"
        / "auto_moderator_dae.py"
    )
    return dae.read_text(encoding="utf-8", errors="ignore")


def test_comments_then_index_then_schedule_order():
    src = _dae_source()

    comments_marker = "PHASE 1: COMMENT ENGAGEMENT"
    index_marker = "PHASE 2: VIDEO INDEXING"
    schedule_marker = "PHASE 3: SHORTS SCHEDULING"

    i_comments = src.find(comments_marker)
    i_index = src.find(index_marker)
    i_schedule = src.find(schedule_marker)

    assert i_comments != -1, "comment-engagement phase marker missing"
    assert i_index != -1, "video-indexing phase marker missing"
    assert i_schedule != -1, "shorts-scheduling phase marker missing"

    # comments -> index -> schedule  (NOT comments -> schedule -> index)
    assert i_comments < i_index < i_schedule


def test_indexing_invoked_before_scheduler_call():
    """The run_video_indexing_cycle call precedes the shorts scheduler launch."""
    src = _dae_source()
    i_index_call = src.find("run_video_indexing_cycle(browser=browser_name)")
    i_sched_call = src.find("run_multi_channel_scheduler")
    assert i_index_call != -1
    assert i_sched_call != -1
    assert i_index_call < i_sched_call
