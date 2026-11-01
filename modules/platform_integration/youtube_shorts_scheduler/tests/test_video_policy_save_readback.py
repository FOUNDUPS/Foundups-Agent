"""Real private queue claims and guarded reload with synthetic DOM only."""
from copy import deepcopy
from types import SimpleNamespace
import time

import pytest
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

from modules.communication.livechat.src import operator_command_queue as queue
from modules.platform_integration.youtube_shorts_scheduler.src import video_policy as policy
from modules.platform_integration.youtube_shorts_scheduler.src.dom_automation import YouTubeStudioDOM

CHANNEL = "UC" + "a" * 22
VIDEO = "a" * 11


@pytest.fixture
def owned_editor(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    owner = queue.OperatorCommandQueue(None, tmp_path / "inbox.json", tmp_path / "ack.json", tmp_path / "state.json")
    for name in ("get_video_policy", "record_video_policy_observation", "claim_video_policy_save", "verify_video_policy_save"):
        monkeypatch.setattr(queue, name, getattr(owner, name))
    state = {"channel_id": CHANNEL, "url": f"https://studio.youtube.com/video/{VIDEO}/edit",
             "title": " Exact original \n", "description": " Exact body \n",
             "save_disabled": False, "prompt_open": False}
    calls = {"clicks": 0, "refreshes": 0}
    document = {"stale": False}
    def enabled():
        if document["stale"]: raise StaleElementReferenceException()
        return True
    def refresh():
        calls["refreshes"] += 1
        document["stale"] = True
    driver = SimpleNamespace(current_window_handle="same-tab", execute_script=lambda *_: deepcopy(state),
                             refresh=refresh, find_elements=lambda *_: [],
                             find_element=lambda *_: SimpleNamespace(is_enabled=enabled))
    dom = object.__new__(YouTubeStudioDOM)
    dom.driver = driver
    dom._last_shorts_channel_id = CHANNEL
    dom._edit_title_unchecked = lambda value: state.update(title=value)
    dom._edit_description_unchecked = lambda value: state.update(description=value)
    dom.begin_policy_cycle()
    dom.begin_policy_edit(CHANNEL, VIDEO)
    def click():
        calls["clicks"] += 1
        state["save_disabled"] = True
    dom.wait_for_clickable = lambda *_a, **_k: SimpleNamespace(click=click)
    return dom, state, calls, owner


def test_actual_save_reload_exact_metadata_settles_real_private_claim(owned_editor):
    dom, state, calls, owner = owned_editor
    dom.edit_title("Verified title")
    dom.edit_description("Verified body")
    dom.click_save()
    saved = owner._read_json(owner.state_path, {})
    assert calls == {"clicks": 1, "refreshes": 1}
    assert saved["video_effect_claims"][-1]["outcome"] == "applied"
    assert any(row["outcome"] == "applied" for row in saved["video_policy_observations"])


def test_noop_refresh_cannot_verify_old_document_draft(owned_editor, monkeypatch):
    dom, state, calls, owner = owned_editor
    class OneCheckWait:
        def __init__(self, driver, _timeout): self.driver = driver
        def until(self, condition):
            result = condition(self.driver)
            if not result: raise TimeoutException("synthetic bounded wait")
            return result
    monkeypatch.setattr("modules.platform_integration.youtube_shorts_scheduler.src.dom_automation.WebDriverWait", OneCheckWait)
    dom.driver.refresh = lambda: calls.update(refreshes=1)
    dom.edit_title("Unsaved old-document draft")
    dom.click_save()
    assert calls == {"clicks": 1, "refreshes": 1}
    assert owner._read_json(owner.state_path, {})["video_effect_claims"][-1]["outcome"] == "unknown"


@pytest.mark.parametrize("reason", ["foreign", "prompt", "window", "identity", "save_enabled"])
def test_unowned_or_unclean_current_page_never_refreshes_or_applies(owned_editor, reason):
    dom, state, calls, owner = owned_editor
    dom._submit_policy_save(lambda: calls.update(clicks=1))
    state["save_disabled"] = True
    if reason == "foreign": state["title"] = "Manual draft"
    if reason == "prompt": state["prompt_open"] = True
    if reason == "window": dom.driver.current_window_handle = "different-tab"
    if reason == "identity": state["channel_id"] = "UC" + "b" * 22
    if reason == "save_enabled": state["save_disabled"] = False
    assert dom._readback_policy_save() is False
    assert calls["refreshes"] == 0
    assert owner._read_json(owner.state_path, {})["video_effect_claims"][-1]["outcome"] == "unknown"


def test_metadata_readback_cannot_settle_schedule_operation(owned_editor, monkeypatch):
    dom, state, calls, owner = owned_editor
    def forbidden_verify(*_args, **_kwargs):
        raise AssertionError("metadata readback must not settle scheduling claim")
    monkeypatch.setattr(queue, "verify_video_policy_save", forbidden_verify)
    dom._policy_scheduling = True
    dom._policy_edit().requested_schedule = {"date": "Nov 2, 2026", "time": "1:00 PM", "timezone": "Asia/Tokyo", "visibility": "scheduled"}
    dom.click_save()
    assert calls["refreshes"] == 1
    assert owner._read_json(owner.state_path, {})["video_effect_claims"][-1]["outcome"] == "unknown"


def schedule_with_fake_picker(dom, during_time=None):
    dom.open_visibility_dialog = lambda: None
    dom.select_schedule_option = lambda: None
    dom.set_schedule_date = lambda _date: None
    dom.set_schedule_time = lambda _time: during_time() if during_time else None
    dom.click_done = lambda: None
    dom._policy_timezone = "Asia/Tokyo"
    return dom.schedule_video("Nov 2, 2026", "1:00 PM")


def enqueue_title_policy(owner, mode):
    fields = {"channel_ids": [CHANNEL], "video_ids": [VIDEO], "title_mode": mode}
    if mode == "replace": fields["title_text"] = "Exact approved replacement"
    queue.enqueue_operator_command({"id": "metadata-" + mode, "action": "set_video_policy", "payload": fields},
        command_path=owner.command_path, acknowledgement_path=owner.acknowledgement_path)


@pytest.mark.parametrize("mode", ["preserve", "replace"])
def test_schedule_metadata_fact_applied_after_fresh_reload_without_releasing_save_claim(owned_editor, monkeypatch, mode):
    dom, state, calls, owner = owned_editor
    dom.edit_title("Earlier automatic title draft")
    def forbidden_verify(*_args, **_kwargs):
        raise AssertionError("metadata fact must not settle scheduling claim")
    monkeypatch.setattr(queue, "verify_video_policy_save", forbidden_verify)
    assert schedule_with_fake_picker(dom, lambda: enqueue_title_policy(owner, mode)) is True
    expected = " Exact original \n" if mode == "preserve" else "Exact approved replacement"
    assert state["title"] == expected and calls == {"clicks": 1, "refreshes": 1}
    saved = owner._read_json(owner.state_path, {})
    claim = saved["video_effect_claims"][-1]
    assert claim["outcome"] == "unknown" and "scheduling" in claim["fingerprints"]
    applied = [row for row in saved["video_policy_observations"] if row["outcome"] == "applied"]
    assert len(applied) == 1 and applied[0]["surface"] == "metadata"
    assert applied[0]["channel_id"] == CHANNEL and applied[0]["video_id"] == VIDEO
    detail = applied[0]["detail"]
    assert detail == {"persisted_readback": True, "policy_fingerprint": claim["fingerprints"]["metadata"],
                      "readback_sha256": policy.save_digest(CHANNEL, VIDEO, {"title": expected, "description": state["description"]})}
    dom.begin_policy_cycle()
    dom.begin_policy_edit(CHANNEL, VIDEO)
    with pytest.raises(policy.VideoPolicyBlocked, match="already_claimed"):
        dom._submit_policy_save(lambda: calls.update(clicks=2))
    assert calls["clicks"] == 1


@pytest.mark.parametrize("problem", ["wrong_identity", "noop_refresh"])
def test_schedule_metadata_fact_requires_exact_fresh_document(owned_editor, monkeypatch, problem):
    dom, state, calls, owner = owned_editor
    class OneCheckWait:
        def __init__(self, driver, _timeout): self.driver = driver
        def until(self, condition):
            result = condition(self.driver)
            if not result: raise TimeoutException("synthetic bounded wait")
            return result
    monkeypatch.setattr("modules.platform_integration.youtube_shorts_scheduler.src.dom_automation.WebDriverWait", OneCheckWait)
    original_refresh = dom.driver.refresh
    def refresh():
        if problem == "wrong_identity":
            original_refresh()
            state["channel_id"] = "UC" + "b" * 22
        else: calls["refreshes"] += 1
    dom.driver.refresh = refresh
    assert schedule_with_fake_picker(dom, lambda: enqueue_title_policy(owner, "preserve")) is True
    saved = owner._read_json(owner.state_path, {})
    assert calls == {"clicks": 1, "refreshes": 1}
    assert saved["video_effect_claims"][-1]["outcome"] == "unknown"
    assert not any(row["outcome"] == "applied" for row in saved["video_policy_observations"])


def test_schedule_metadata_policy_cleared_after_submit_remains_unknown(owned_editor):
    dom, state, calls, owner = owned_editor
    original_refresh = dom.driver.refresh
    def refresh():
        original_refresh()
        queue.enqueue_operator_command({"id": "clear", "action": "clear_video_policy", "payload": {"channel_ids": [CHANNEL], "video_ids": [VIDEO]}},
            command_path=owner.command_path, acknowledgement_path=owner.acknowledgement_path)
    dom.driver.refresh = refresh
    assert schedule_with_fake_picker(dom, lambda: enqueue_title_policy(owner, "preserve")) is True
    saved = owner._read_json(owner.state_path, {})
    assert saved["video_effect_claims"][-1]["outcome"] == "unknown"
    assert not any(row["outcome"] == "applied" for row in saved["video_policy_observations"])


def test_unknown_save_blocks_after_new_navigation_cycle_and_queue_instance(owned_editor, monkeypatch):
    dom, state, calls, owner = owned_editor
    def uncertain():
        calls["clicks"] += 1
        raise RuntimeError("synthetic lost response")
    with pytest.raises(policy.VideoPolicyBlocked): dom._submit_policy_save(uncertain)
    restarted = queue.OperatorCommandQueue(None, owner.command_path, owner.acknowledgement_path, owner.state_path)
    monkeypatch.setattr(queue, "claim_video_policy_save", restarted.claim_video_policy_save)
    dom.begin_policy_cycle()
    dom.begin_policy_edit(CHANNEL, VIDEO)
    dom.edit_title("Different draft cannot bypass unknown claim")
    with pytest.raises(policy.VideoPolicyBlocked, match="already_claimed"):
        dom._submit_policy_save(lambda: calls.update(clicks=2))
    assert calls["clicks"] == 1


@pytest.mark.parametrize("gate", ["stop", "disabled"])
def test_stop_arriving_during_save_candidate_wait_blocks_claim_and_click(owned_editor, tmp_path, monkeypatch, gate):
    dom, state, calls, owner = owned_editor
    def candidate(*_args, **_kwargs):
        if gate == "stop":
            stop = tmp_path / "STOP"
            stop.write_text("stop", encoding="utf-8")
            monkeypatch.setenv("YT_AUTOMATION_STOP_FILE", str(stop))
        else: monkeypatch.setenv("YT_AUTOMATION_ENABLED", "false")
        return SimpleNamespace(click=lambda: calls.update(clicks=1))
    dom.wait_for_clickable = candidate
    with pytest.raises(policy.VideoPolicyBlocked, match="public_automation"):
        dom.click_save()
    assert calls == {"clicks": 0, "refreshes": 0}
    assert not owner._read_json(owner.state_path, {}).get("video_effect_claims")
