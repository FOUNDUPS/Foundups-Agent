"""Offline actual-save-owner controls; no browser, providers or credentials."""
from copy import deepcopy
from types import SimpleNamespace
import time

import pytest

from modules.communication.livechat.src import operator_command_queue as queue
from modules.platform_integration.youtube_shorts_scheduler.src import video_policy as policy
from modules.platform_integration.youtube_shorts_scheduler.src.dom_automation import YouTubeStudioDOM

CHANNEL = "UC" + "a" * 22
VIDEO = "a" * 11


@pytest.fixture
def editor(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    state = {"channel_id": CHANNEL, "url": f"https://studio.youtube.com/video/{VIDEO}/edit",
             "title": " Original title \n", "description": " Original body \n"}
    active, observations, clicks = {}, [], []

    def get_policy(channel_id, video_id=None, *, surface="metadata"):
        assert channel_id == CHANNEL and video_id == VIDEO
        return {"available": True, "blocked": False, "matched_command_ids": ["command"],
                "fingerprint": "f" * 64, **active.get(surface, {})}

    monkeypatch.setattr(queue, "get_video_policy", get_policy)
    monkeypatch.setattr(queue, "record_video_policy_observation", lambda ids, **kw: observations.append(kw))
    monkeypatch.setattr(queue, "claim_video_policy_save", lambda *_a, **_k: {"claimed": True})
    monkeypatch.setattr(queue, "verify_video_policy_save", lambda *_a, **_k: {"verified": False})
    dom = object.__new__(YouTubeStudioDOM)
    dom.driver = SimpleNamespace(execute_script=lambda *args: deepcopy(state), find_elements=lambda *_: [])
    dom._last_shorts_channel_id = CHANNEL
    dom._edit_title_unchecked = lambda value: state.update(title=value)
    dom._edit_description_unchecked = lambda value: state.update(description=value)
    dom.begin_policy_cycle()
    dom.begin_policy_edit(CHANNEL, VIDEO)
    return dom, state, active, observations, clicks


def test_preserve_arriving_after_draft_restores_exact_original_and_allows_schedule(editor):
    dom, state, active, observations, clicks = editor
    dom.edit_title("Analyzer draft")
    dom.edit_description("Analyzer body")
    active["metadata"] = {"title_mode": "preserve"}
    dom._policy_scheduling = True
    dom._submit_policy_save(lambda: clicks.append(dict(state)))
    assert clicks[0]["title"] == " Original title \n"
    assert clicks[0]["description"] == "Analyzer body"
    assert dom._policy_cycle_attempts == 1
    assert observations[-1]["outcome"] == "unknown"
    assert not any(row["outcome"] == "applied" for row in observations)


@pytest.mark.parametrize("field", ["title", "description"])
def test_foreign_manual_change_is_never_clobbered_or_saved(editor, field):
    dom, state, active, observations, clicks = editor
    dom.edit_title("Our draft")
    state[field] = "Foreign manual edit"
    active["metadata"] = {field + "_mode": "preserve"}
    before = dict(state)
    with pytest.raises(policy.VideoPolicyBlocked, match="foreign"):
        dom._submit_policy_save(lambda: clicks.append(True))
    assert state == before and not clicks


@pytest.mark.parametrize("surface,fields", [
    ("metadata", {"available": False, "blocked": True}),
    ("scheduling", {"scheduling_enabled": False}),
    ("scheduling", {"max_per_cycle": 1}),
])
def test_pre_save_block_retains_draft_without_click(editor, surface, fields):
    dom, state, active, observations, clicks = editor
    dom._policy_scheduling = True
    dom._policy_cycle_attempts = 1
    active[surface] = fields
    with pytest.raises(policy.VideoPolicyBlocked):
        dom._submit_policy_save(lambda: clicks.append(True))
    assert not clicks


def test_pause_arriving_during_set_time_blocks_actual_save_owner(editor):
    dom, state, active, observations, clicks = editor
    dom.open_visibility_dialog = lambda: None
    dom.select_schedule_option = lambda: None
    dom.set_schedule_date = lambda date: None
    dom.set_schedule_time = lambda time: active.update(scheduling={"scheduling_enabled": False})
    dom.click_done = lambda: None
    dom.wait_for_clickable = lambda *_a, **_k: SimpleNamespace(click=lambda: clicks.append(True))
    assert dom.schedule_video("Nov 2, 2026", "1:00 PM") is False
    assert not clicks


@pytest.mark.parametrize("change", ["preserve", "foreign", "pause"])
def test_actual_save_button_rechecks_after_candidate_wait(editor, change):
    dom, state, active, observations, clicks = editor
    dom.edit_title("Our auto title")
    dom._policy_scheduling = True
    def candidate(*_args, **_kwargs):
        if change == "foreign": state["title"] = "Manual edit"
        if change in ("preserve", "foreign"): active["metadata"] = {"title_mode": "preserve"}
        if change == "pause": active["scheduling"] = {"scheduling_enabled": False}
        return SimpleNamespace(click=lambda: clicks.append(dict(state)))
    dom.wait_for_clickable = candidate
    if change == "preserve":
        dom.click_save()
        assert clicks[0]["title"] == " Original title \n"
    else:
        with pytest.raises(policy.VideoPolicyBlocked):
            dom.click_save()
        assert not clicks
        if change == "foreign": assert state["title"] == "Manual edit"


def test_expired_or_cleared_replacement_does_not_persist_stale_policy_text(editor):
    dom, state, active, observations, clicks = editor
    active["metadata"] = {"title_mode": "replace", "title_text": "Exact approved title"}
    dom.edit_title("Our evidence draft")
    assert state["title"] == "Exact approved title"
    active["metadata"] = {}
    dom._submit_policy_save(lambda: clicks.append(dict(state)))
    assert clicks[0]["title"] == "Our evidence draft"


def test_replacement_has_no_private_context_or_promo_append(editor):
    dom, state, active, observations, clicks = editor
    active["metadata"] = {"description_mode": "replace", "description_text": "Exact approved body",
                          "context": "PRIVATE RESEARCH", "sources": ["PRIVATE SOURCE"]}
    dom._submit_policy_save(lambda: clicks.append(dict(state)))
    assert clicks[0]["description"] == "Exact approved body"
    assert "PRIVATE" not in repr(observations)


@pytest.mark.parametrize("changed", ["channel", "video", "host", "fields"])
def test_identity_and_unknown_fields_block(editor, changed):
    dom, state, active, observations, clicks = editor
    if changed == "channel": state["channel_id"] = "UC" + "b" * 22
    if changed == "video": state["url"] = state["url"].replace(VIDEO, "b" * 11)
    if changed == "host": state["url"] = state["url"].replace("studio.youtube.com", "studio.youtube.com.evil")
    if changed == "fields": state["description"] = None
    with pytest.raises(policy.VideoPolicyBlocked):
        dom._submit_policy_save(lambda: clicks.append(True))
    assert not clicks


def test_uncertain_started_save_is_not_retried(editor):
    dom, state, active, observations, clicks = editor
    def uncertain():
        clicks.append(True)
        raise RuntimeError("synthetic response lost")
    with pytest.raises(policy.VideoPolicyBlocked, match="outcome_unknown"):
        dom._submit_policy_save(uncertain)
    with pytest.raises(policy.VideoPolicyBlocked, match="submission_outcome_unknown"):
        dom._submit_policy_save(lambda: clicks.append(True))
    assert len(clicks) == 1


def test_original_comes_from_detail_not_stale_list_row(editor):
    dom, state, active, observations, clicks = editor
    assert dom._policy_edit().original["title"] == state["title"]
    assert dom._policy_edit().original["title"] != "Stale list-row title"


def test_cycle_attempt_count_is_not_reset_by_policy_reads(editor):
    dom, state, active, observations, clicks = editor
    active["scheduling"] = {"max_per_cycle": 1}
    dom._policy_scheduling = True
    dom._submit_policy_save(lambda: clicks.append(True))
    dom.begin_policy_edit(CHANNEL, VIDEO)
    with pytest.raises(policy.VideoPolicyBlocked, match="cycle_cap"):
        dom._submit_policy_save(lambda: clicks.append(True))
    assert len(clicks) == 1 and dom._policy_cycle_attempts == 1
