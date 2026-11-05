"""Offline completion evidence through the complete engagement owner definition."""
import asyncio
import importlib.util
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest


FILTERED_EMPTY = "No comments found. Try searching for something else or removing filters."


class Clock:
    def __init__(self):
        self.now = 0.0

    def time(self):
        return self.now

    async def sleep(self, seconds):
        self.now += seconds


class InboxDriver:
    """Synthetic rendered DOM answers; no browser/session is constructed."""
    current_url = "https://studio.youtube.com/channel/creator/comments/inbox"

    def __init__(self, counts, empty=False, filtered=False, fail=False):
        self.counts, self.index = counts, 0
        self.empty, self.filtered, self.fail = empty, filtered, fail
        self.scripts, self.refreshes = [], 0

    def execute_script(self, script):
        self.scripts.append(script)
        if "querySelectorAll" in script:
            value = self.counts[min(self.index, len(self.counts) - 1)]
            self.index += 1
            return value
        if self.fail:
            raise RuntimeError("synthetic DOM read unavailable")
        if self.filtered:
            # A generic empty-state node is present in this filtered view.
            # This collaborator is not a JavaScript engine; the independent
            # actual-JS probe separately qualifies rendered whitespace semantics.
            text = self.filtered if isinstance(self.filtered, str) else FILTERED_EMPTY
            if r".replace(/\s+/g, ' ').trim()" in script:
                text = " ".join(text.split())
            veto = script.find(FILTERED_EMPTY)
            selectors = script.find("for (const sel")
            return not (FILTERED_EMPTY in text and 0 <= veto < selectors
                        and "return false" in script[veto:selectors])
        return self.empty

    def refresh(self):
        self.refreshes += 1


@pytest.fixture
def owner(tmp_path):
    path = Path(__file__).with_name("test_chat_manifest_inspection.py")
    spec = importlib.util.spec_from_file_location("_inbox_definition_helpers", path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    module = helper.definitions("_inbox_completion_owner",
        "modules/communication/video_comments/skillz/tars_like_heart_reply/comment_engagement_dae.py")
    module.TELEMETRY_DIR = tmp_path
    clock = Clock()
    module.time = SimpleNamespace(time=clock.time)
    module.asyncio = SimpleNamespace(sleep=clock.sleep)
    item = object.__new__(module.CommentEngagementDAE)
    item.session_id, item.channel_id, item.parent_pid = "inbox-fixture", "creator", None
    item.human, item.use_vision = None, False
    item._sessions_since_long_break = 0
    item.stats = dict(comments_processed=0, likes=0, hearts=0, replies=0)
    item._should_take_break = lambda *_: False
    item._save_break_state = lambda: None
    item.driver = InboxDriver([0])
    breadcrumbs, notices, processed = [], [], []
    async def notify(**_kwargs): notices.append(True)
    item.livechat_sender = SimpleNamespace(store_breadcrumb=lambda **data: breadcrumbs.append(data),
                                          send_chat_message=notify)
    async def engage(*_args, **_kwargs):
        processed.append(True)
        item.stats["comments_processed"] += 1
        item.stats["likes"] += 1
        return dict(reply=False, like=True, heart=False)
    async def nested(**_kwargs): return []
    item.comment_processor = SimpleNamespace(engage_comment=engage, delay_multiplier=0)
    item.reply_executor = SimpleNamespace(process_nested_replies=nested)
    return item, breadcrumbs, notices, processed, clock


def run_session(item, maximum=1):
    return asyncio.run(item.engage_all_comments(max_comments=maximum, do_reply=False,
                                               refresh_between=False))


@pytest.mark.parametrize("state", ["timeout", "filtered", "filtered_newline", "filtered_spaces", "error"])
def test_zero_threads_without_positive_empty_evidence_stays_unknown(owner, caplog, state):
    item, breadcrumbs, notices, processed, clock = owner
    filtered = {"filtered": FILTERED_EMPTY,
                "filtered_newline": FILTERED_EMPTY.replace(". Try", ".\nTry"),
                "filtered_spaces": FILTERED_EMPTY.replace("Try searching", "Try  searching")}.get(state, False)
    item.driver = InboxDriver([0], empty=bool(filtered), filtered=filtered,
                              fail=state == "error")
    caplog.set_level(logging.INFO)
    summary = run_session(item)
    assert summary["stats"]["all_processed"] is False
    assert summary["total_processed"] == 0 and processed == []
    assert notices == []
    assert not any("cleared" in row.get("message", "").lower() for row in breadcrumbs)
    assert "Inbox is clear!" not in caplog.text
    assert "ALL COMMENTS PROCESSED" not in caplog.text
    assert clock.now >= 15


def test_existing_positive_empty_indicator_allows_empty_view_completion(owner):
    item, breadcrumbs, notices, processed, clock = owner
    item.driver = InboxDriver([0], empty=True)
    summary = run_session(item)
    assert summary["stats"]["all_processed"] is True
    assert summary["total_processed"] == 0 and processed == []
    assert clock.now == 0 and notices == []


@pytest.mark.parametrize("empty", [True, False])
def test_real_processed_comment_requires_positive_end_empty_evidence(owner, empty):
    item, breadcrumbs, notices, processed, clock = owner
    item.driver = InboxDriver([1, 0], empty=empty)
    summary = run_session(item)
    assert processed == [True] and summary["total_processed"] == 1
    assert summary["stats"]["comments_processed"] == 1
    assert summary["stats"]["all_processed"] is empty


def test_remaining_thread_still_prevents_completion(owner):
    item, breadcrumbs, notices, processed, clock = owner
    item.driver = InboxDriver([1], empty=True)
    summary = run_session(item)
    assert processed == [True] and summary["stats"]["all_processed"] is False


@pytest.mark.parametrize("empty", [True, False])
def test_later_zero_observation_controls_clear_feedback(owner, empty, caplog):
    item, breadcrumbs, notices, processed, clock = owner
    item.driver = InboxDriver([1, 0], empty=empty)
    caplog.set_level(logging.INFO)
    summary = run_session(item, maximum=2)
    assert processed == [True] and summary["total_processed"] == 1
    assert summary["stats"]["all_processed"] is empty
    assert notices == ([True] if empty else [])
    assert any("cleared" in row.get("message", "").lower() for row in breadcrumbs) is empty
    assert ("ALL COMMENTS PROCESSED" in caplog.text) is empty


def test_positive_indicator_lost_before_final_check_cannot_complete(owner):
    item, breadcrumbs, notices, processed, clock = owner
    class TransientEmpty(InboxDriver):
        def execute_script(self, script):
            result = super().execute_script(script)
            if "querySelectorAll" not in script:
                self.empty = False
            return result
    item.driver = TransientEmpty([0], empty=True)
    assert run_session(item)["stats"]["all_processed"] is False


def test_missing_thread_during_processing_does_not_claim_clear(owner, caplog):
    item, breadcrumbs, notices, processed, clock = owner
    item.driver = InboxDriver([1, 0])
    async def gone(*_args, **_kwargs): return {"no_comment_exists": True}
    item.comment_processor.engage_comment = gone
    caplog.set_level(logging.INFO)
    summary = run_session(item)
    assert summary["stats"]["all_processed"] is False
    assert summary["total_processed"] == 0
    assert not any("cleared" in row.get("message", "").lower() for row in breadcrumbs)
    assert "Inbox cleared" not in caplog.text
