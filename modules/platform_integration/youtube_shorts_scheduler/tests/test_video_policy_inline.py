"""Offline inline button scope/gate checks with actual CPS methods."""
from copy import deepcopy
from types import SimpleNamespace
import time

import pytest

from modules.communication.livechat.src import operator_command_queue as queue
from modules.platform_integration.youtube_shorts_scheduler.src import video_policy as policy
from modules.platform_integration.youtube_shorts_scheduler.src.content_page_scheduler import ContentPageScheduler

CHANNEL = "UC" + "a" * 22
VIDEO = "a" * 11


@pytest.fixture
def popup(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    snapshot = {"channel_id": CHANNEL, "url": f"https://studio.youtube.com/channel/{CHANNEL}/videos/short",
                "video_id": VIDEO, "popup_bound": True}
    active, calls = {}, {"clicks": 0, "claims": 0}
    def fresh(channel_id, video_id=None, *, surface="metadata"):
        assert channel_id == CHANNEL and video_id == VIDEO
        return {"available": True, "blocked": False, "matched_command_ids": [],
                "fingerprint": "f" * 64, **active.get(surface, {})}
    def claim(*_args, **_kwargs):
        calls["claims"] += 1
        return {"claimed": True}
    monkeypatch.setattr(queue, "get_video_policy", fresh)
    monkeypatch.setattr(queue, "claim_video_policy_save", claim)
    monkeypatch.setattr(queue, "record_video_policy_observation", lambda *_a, **_k: None)
    def click(): calls["clicks"] += 1
    button = SimpleNamespace(click=click, is_displayed=lambda: True, is_enabled=lambda: True)
    owner = object.__new__(ContentPageScheduler)
    owner.driver = SimpleNamespace(execute_script=lambda *_: deepcopy(snapshot), find_element=lambda *_: button)
    owner.dom = SimpleNamespace(_policy_cycle_attempts=0)
    owner.sel = SimpleNamespace(POPUP_SAVE_BUTTON_CSS="button", POPUP_SAVE_BUTTON_XPATH="button")
    owner._policy_row = object()
    owner._policy_channel_id = CHANNEL
    owner._policy_video_id = VIDEO
    owner._policy_requested_schedule = {"date": "Nov 2, 2026", "time": "1:00 PM", "timezone": "Asia/Tokyo", "visibility": "scheduled"}
    return owner, snapshot, active, calls


def test_popup_without_description_and_audience_refuses_claim_and_click(popup):
    owner, snapshot, active, calls = popup
    with pytest.raises(policy.PreSaveAuditBlocked, match="detail_editor_required"):
        owner._click_popup_schedule_button()
    assert calls == {"clicks": 0, "claims": 0}
    assert owner.dom._policy_cycle_attempts == 0


@pytest.mark.parametrize("problem", ["popup_other_video", "channel", "row_video", "url", "pause", "cap", "unavailable"])
def test_wrong_popup_or_fresh_policy_blocks_before_claim_and_button(popup, problem):
    owner, snapshot, active, calls = popup
    if problem == "popup_other_video": snapshot["popup_bound"] = False
    if problem == "channel": snapshot["channel_id"] = "UC" + "b" * 22
    if problem == "row_video": snapshot["video_id"] = "b" * 11
    if problem == "url": snapshot["url"] = snapshot["url"].replace("studio.youtube.com", "evil.invalid")
    if problem == "pause": active["scheduling"] = {"scheduling_enabled": False}
    if problem == "cap":
        active["scheduling"] = {"max_per_cycle": 1}
        owner.dom._policy_cycle_attempts = 1
    if problem == "unavailable": active["scheduling"] = {"available": False, "blocked": True}
    with pytest.raises(policy.VideoPolicyBlocked): owner._click_popup_schedule_button()
    assert calls == {"clicks": 0, "claims": 0}


def test_unknown_popup_callback_is_not_retried_through_xpath_or_js(popup):
    owner, snapshot, active, calls = popup
    def uncertain():
        calls["clicks"] += 1
        raise RuntimeError("synthetic lost response")
    owner.driver.find_element = lambda *_: SimpleNamespace(click=uncertain, is_displayed=lambda: True, is_enabled=lambda: True)
    with pytest.raises(policy.VideoPolicyBlocked, match="detail_editor_required"):
        owner._click_popup_schedule_button()
    assert calls == {"clicks": 0, "claims": 0}
