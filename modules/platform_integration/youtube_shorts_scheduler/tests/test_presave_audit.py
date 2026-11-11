"""Actual save/preparation owners against synthetic drafts; no browser/model calls."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from modules.platform_integration.youtube_shorts_scheduler.src import video_policy as policy
from modules.platform_integration.youtube_shorts_scheduler.src import channel_config, index_weave
from modules.platform_integration.youtube_shorts_scheduler.src.dom_automation import YouTubeStudioDOM
from modules.platform_integration.youtube_shorts_scheduler.src.content_page_scheduler import ContentPageScheduler

CHANNEL = "UC" + "x" * 22
VIDEO = "x" * 11


@pytest.fixture(autouse=True)
def isolated_audience_environment(monkeypatch):
    monkeypatch.delenv("YT_MADE_FOR_KIDS_CHANNEL_IDS", raising=False)
    monkeypatch.delenv("YT_NOT_MADE_FOR_KIDS_CHANNEL_IDS", raising=False)


@pytest.mark.parametrize("target", [True, False])
def test_environment_audience_uses_native_identity_without_enabling_channel(monkeypatch, target):
    monkeypatch.setattr(channel_config, "CHANNELS", {})
    setting = "YT_MADE_FOR_KIDS_CHANNEL_IDS" if target else "YT_NOT_MADE_FOR_KIDS_CHANNEL_IDS"
    monkeypatch.setenv(setting, CHANNEL)
    assert policy.audience_target(CHANNEL) is target
    assert channel_config.CHANNELS == {}
    with pytest.raises(policy.PreSaveAuditBlocked, match="unconfigured"):
        policy.audience_target("UC" + "y" * 22)


@pytest.mark.parametrize("problem", ["handle", "duplicate", "overlap", "trailing_comma", "conflict", "registry_string", "duplicate_registry"])
def test_invalid_audience_configuration_cannot_select_or_claim(draft, monkeypatch, problem):
    dom, state, calls = draft
    if problem == "handle": monkeypatch.setenv("YT_MADE_FOR_KIDS_CHANNEL_IDS", "@Kids")
    if problem == "duplicate": monkeypatch.setenv("YT_MADE_FOR_KIDS_CHANNEL_IDS", CHANNEL + "," + CHANNEL)
    if problem == "overlap":
        monkeypatch.setenv("YT_MADE_FOR_KIDS_CHANNEL_IDS", CHANNEL)
        monkeypatch.setenv("YT_NOT_MADE_FOR_KIDS_CHANNEL_IDS", CHANNEL)
    if problem == "trailing_comma": monkeypatch.setenv("YT_NOT_MADE_FOR_KIDS_CHANNEL_IDS", CHANNEL + ",")
    if problem == "conflict": monkeypatch.setenv("YT_MADE_FOR_KIDS_CHANNEL_IDS", CHANNEL)
    if problem == "registry_string": monkeypatch.setitem(channel_config.CHANNELS["audit"], "made_for_kids", "false")
    if problem == "duplicate_registry": monkeypatch.setitem(channel_config.CHANNELS, "duplicate", {"id": CHANNEL, "made_for_kids": False})
    with pytest.raises(policy.PreSaveAuditBlocked, match="invalid_or_conflicting"):
        dom.prepare_schedule_audit()
    assert calls["audience"] == calls["claim"] == calls["save"] == 0


@pytest.mark.parametrize("audience", [True, False, None, "false"])
def test_registry_round_trip_preserves_audience_without_name_defaults(tmp_path, monkeypatch, audience):
    from modules.infrastructure.shared_utilities import youtube_channel_registry as registry
    monkeypatch.setattr(registry, "_REGISTRY_PATH", tmp_path / "channels.json")
    monkeypatch.setattr(registry, "_default_channels", lambda: [])
    registry.save_registry({"channels": [{"key": "antifafm", "id": CHANNEL, "shorts": {"made_for_kids": audience}}]})
    monkeypatch.setattr(channel_config, "get_channels", registry.get_channels)
    channels = channel_config._build_channel_config()
    assert channels["antifafm"]["made_for_kids"] == audience
    monkeypatch.setattr(channel_config, "CHANNELS", channels)
    if type(audience) is bool:
        assert policy.audience_target(CHANNEL) is audience
    else:
        with pytest.raises(policy.PreSaveAuditBlocked): policy.audience_target(CHANNEL)


@pytest.fixture
def draft(monkeypatch):
    monkeypatch.setitem(channel_config.CHANNELS, "audit", {"id": CHANNEL, "made_for_kids": False})
    monkeypatch.setattr(policy, "require_public_gate", lambda: None)
    monkeypatch.setattr(policy, "read_policy", lambda *_a, **_k: {
        "available": True, "blocked": False, "fingerprint": "f" * 64, "matched_command_ids": []})
    state = {"channel_id": CHANNEL, "url": f"https://studio.youtube.com/video/{VIDEO}/edit",
             "title": "A quiet walk through the forest", "description": "Walking beside a forest stream.",
             "made_for_kids": None, "audience_ready": True}
    calls = {"audience": 0, "save": 0, "claim": 0, "navigation": 0}
    choice = SimpleNamespace(is_displayed=lambda: True, is_enabled=lambda: True)
    dom = object.__new__(YouTubeStudioDOM)
    dom.driver = SimpleNamespace(execute_script=lambda *_: deepcopy(state),
                                find_elements=lambda *_: [choice])
    dom._edit_title_unchecked = lambda value: state.update(title=value)
    dom._edit_description_unchecked = lambda value: state.update(description=value)
    def click(_):
        calls["audience"] += 1
        state["made_for_kids"] = False
    dom.safe_click = click
    dom.begin_policy_edit(CHANNEL, VIDEO)
    dom._policy_edit().requested_schedule = {
        "date": "Nov 2, 2099", "time": "1:00 PM", "timezone": "Asia/Tokyo", "visibility": "scheduled"}
    dom._policy_timezone = "Asia/Tokyo"
    dom._policy_scheduling = True
    monkeypatch.setattr(policy, "claim_save", lambda *_: calls.update(claim=calls["claim"] + 1))
    return dom, state, calls


@pytest.mark.parametrize("title", ["", "August", "August #music", "August 9, 2026", "2026-08-09", "2026年8月9日",
                                  "Highlight Overview", "Untitled 2", "Video 123"])
def test_placeholder_title_is_incomplete(title):
    assert "title_missing_or_placeholder" in policy.metadata_audit_issues(title, "Real description.")


@pytest.mark.parametrize("description", ["", "  ", "TBD", "M2M_CONTEXT\n{}", "Below is a copy-ready bilingual YouTube description."])
def test_description_must_have_human_facing_content(description):
    assert any(i.startswith("description_") for i in policy.metadata_audit_issues("Forest stream", description))


def test_meaningful_title_is_not_rejected_for_containing_a_month_or_number():
    assert policy.metadata_audit_issues("August rain: three minutes beside a stream", "Rain falls on the trees.") == []


def test_prepare_selects_no_and_save_rechecks_observed_selection(draft):
    dom, state, calls = draft
    dom.prepare_schedule_audit()
    dom._submit_policy_save(lambda: calls.update(save=1))
    assert calls["audience"] == calls["save"] == calls["claim"] == 1
    assert dom._policy_edit().requested_schedule["made_for_kids"] is False


@pytest.mark.parametrize("change", ["audience", "unknown_audience", "missing_title", "empty_description", "identity", "timezone", "past", "missing_schedule"])
def test_late_bad_draft_cannot_claim_or_save(draft, change):
    dom, state, calls = draft
    dom.prepare_schedule_audit()
    if change == "audience": state["made_for_kids"] = True
    if change == "unknown_audience": state["audience_ready"] = False
    if change == "missing_title": state["title"] = "August"
    if change == "empty_description": state["description"] = ""
    if change == "identity": state["channel_id"] = "UC" + "y" * 22
    if change == "timezone": dom._policy_edit().requested_schedule["timezone"] = None
    if change == "past": dom._policy_edit().requested_schedule["date"] = "Nov 2, 2000"
    if change == "missing_schedule": dom._policy_edit().requested_schedule = None
    with pytest.raises(policy.VideoPolicyBlocked):
        dom._submit_policy_save(lambda: calls.update(save=1))
    assert calls["claim"] == calls["save"] == 0


@pytest.mark.parametrize("problem", ["missing", "ambiguous", "changed", "wrong_identity", "click_not_stuck"])
def test_audience_selection_refuses_unknown_controls_and_manual_changes(draft, problem):
    dom, state, calls = draft
    if problem == "missing": state["audience_ready"] = False
    if problem == "ambiguous": dom.driver.find_elements = lambda *_: [object(), object()]
    if problem == "changed": state["made_for_kids"] = True
    if problem == "wrong_identity": state["channel_id"] = "other"
    if problem == "click_not_stuck": dom.safe_click = lambda *_: None
    with pytest.raises(policy.VideoPolicyBlocked): dom.prepare_schedule_audit()
    assert calls["save"] == calls["claim"] == 0


def test_explicit_kids_policy_preserves_yes_unknown_channel_never_defaults_to_no(draft, monkeypatch):
    dom, state, calls = draft
    monkeypatch.setitem(channel_config.CHANNELS, "audit", {"id": CHANNEL, "made_for_kids": True})
    state["made_for_kids"] = True
    dom.begin_policy_edit(CHANNEL, VIDEO)
    dom.prepare_schedule_audit()
    assert calls["audience"] == 0
    monkeypatch.setitem(channel_config.CHANNELS, "audit", {"id": CHANNEL})
    with pytest.raises(policy.PreSaveAuditBlocked, match="policy_unconfigured"): dom.prepare_schedule_audit()
    assert calls["audience"] == 0


def test_missing_analysis_blocks_without_model_or_audience_write(draft, monkeypatch):
    dom, state, calls = draft
    state.update(title="August", description="")
    dom.begin_policy_edit(CHANNEL, VIDEO)
    monkeypatch.setattr(index_weave, "load_index_json", lambda **_: None)
    with pytest.raises(policy.PreSaveAuditBlocked, match="title_missing_or_placeholder"):
        dom.prepare_schedule_audit()
    assert state["title"] == "August" and state["description"] == "" and calls["audience"] == 0


def test_matched_existing_evidence_repairs_incomplete_metadata(draft, monkeypatch):
    dom, state, calls = draft
    state.update(title="August", description="")
    dom.begin_policy_edit(CHANNEL, VIDEO)
    artifact = {"video_id": VIDEO, "indexed_at": "2026-11-10T00:00:00Z", "transcript_source": "youtube_transcript",
                "metadata": {"retrieval_eligible": True},
                "audio": {"segments": [{"start": 0, "end": 4, "text": "A walk beside a forest stream."}]}}
    monkeypatch.setattr(index_weave, "load_index_json", lambda **_: artifact)
    dom.prepare_schedule_audit()
    assert "forest stream" in state["title"] and "forest stream" in state["description"]
    assert calls["audience"] == 1 and calls["save"] == 0


def test_content_row_routes_through_detail_owner_before_scheduling(monkeypatch):
    # This handoff uses synchronous DOM calls and does not await I/O. Drive the
    # coroutine directly so the sealed runner need not create event-loop sockets.
    def complete(coroutine):
        with pytest.raises(StopIteration) as result:
            coroutine.send(None)
        return result.value.value
    calls = []
    monkeypatch.setattr(policy, "inline_identity", lambda *_a, **_k: (CHANNEL, VIDEO))
    owner = object.__new__(ContentPageScheduler)
    owner.driver = SimpleNamespace(find_elements=lambda *_: [])
    owner._policy_channel_id = CHANNEL
    owner._policy_timezone = "Asia/Tokyo"
    owner.dom = SimpleNamespace(navigate_to_video=lambda v: calls.append(("navigate", v)),
        begin_policy_edit=lambda c, v: calls.append(("capture", c, v)),
        read_edit_page_visibility=lambda: "unlisted",
        schedule_video=lambda d, t: calls.append(("audit_and_schedule", d, t)) or True)
    assert complete(owner.schedule_video_from_row(object(), "Nov 2, 2099", "1:00 PM", VIDEO))
    assert [item[0] for item in calls] == ["navigate", "capture", "audit_and_schedule"]
    calls.clear()
    owner._policy_submission_started = True
    assert not complete(owner.schedule_video_from_row(object(), "Nov 2, 2099", "1:00 PM", VIDEO))
    assert calls == []


@pytest.mark.parametrize("date,time", [("Mar 10, 2030", "2:30 AM"), ("Nov 3, 2030", "1:30 AM")])
def test_dst_gaps_and_ambiguous_slots_refuse_save(draft, date, time):
    dom, state, calls = draft
    dom.prepare_schedule_audit()
    dom._policy_edit().requested_schedule.update(date=date, time=time, timezone="America/New_York")
    with pytest.raises(policy.PreSaveAuditBlocked, match="schedule_invalid"):
        dom._submit_policy_save(lambda: calls.update(save=1))
    assert calls["claim"] == calls["save"] == 0
