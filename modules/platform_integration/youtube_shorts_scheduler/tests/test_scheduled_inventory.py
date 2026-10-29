"""Qualified schedule reads and absence-based consumers; no live browser effects."""

import asyncio
import copy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from modules.platform_integration.youtube_shorts_scheduler.src import schedule_inventory as inv
from modules.platform_integration.youtube_shorts_scheduler.src.content_page_scheduler import ContentPageScheduler
from modules.platform_integration.youtube_shorts_scheduler.src.dom_automation import YouTubeStudioDOM
from modules.platform_integration.youtube_shorts_scheduler.src.schedule_auditor import ScheduleAuditor
from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import ScheduleTracker
from modules.platform_integration.youtube_shorts_scheduler.src.scheduler import YouTubeShortsScheduler

CHANNEL = "UCSNTUXjAgpd4sgWYP0xoJgw"
FIRST, SECOND = "abcdefghijk", "lmnopqrstuv"


def row(video_id=FIRST, schedule="Scheduled\nOct 30, 2026\n9:15 AM", **changes):
    return dict(video_id=video_id, title="Existing title", schedule_text=schedule,
                date_text="Jan 1, 2020\nPublished", **changes)


def page(rows=None, **changes):
    values = dict(channel_id=CHANNEL, url=f"https://studio.youtube.com/channel/{CHANNEL}/videos/short",
                  chip_texts=["Visibility: Has schedule"], search_text="", loading=False,
                  empty=False, next_page=False, previous_page=False,
                  rows=[row()] if rows is None else rows)
    values.update(changes)
    return values


class Pages:
    def __init__(self, *pages, click_error=False):
        self.pages, self.cursor, self.reads, self.clicks = pages, 0, 0, 0
        self.click_error = click_error
        self.driver = self

    def execute_script(self, script):
        assert script == inv.SCHEDULED_PAGE_SCRIPT
        self.reads += 1
        value = self.pages[min(self.cursor, len(self.pages) - 1)]
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)

    def click_next_page(self):
        self.clicks += 1
        if self.click_error:
            raise RuntimeError("synthetic pagination failure")
        self.cursor += 1


def receipt(*pages, **options):
    return inv.collect_scheduled_inventory(Pages(*(pages or [page()])), CHANNEL, **options)


def test_complete_multi_page_read_preserves_actual_slots_and_identity():
    dom = Pages(page(next_page=True), page([row(SECOND, "Scheduled October 31, 2026, 11:30 PM")], previous_page=True))
    result = inv.collect_scheduled_inventory(dom, CHANNEL)
    assert inv.qualified_inventory(result, CHANNEL)
    assert result["total_scheduled"] == 2 and result["pages_read"] == 2
    assert [(v["video_id"], v["date"], v["time"]) for v in result["videos"]] == [
        (FIRST, "Oct 30, 2026", "9:15 AM"), (SECOND, "Oct 31, 2026", "11:30 PM")]
    assert dom.clicks == 1


def test_dom_public_receipt_delegates_to_qualified_owner():
    dom = object.__new__(YouTubeStudioDOM)
    dom.driver = Pages(page())
    assert inv.qualified_inventory(dom.read_scheduled_inventory(CHANNEL), CHANNEL)


def test_filter_verifier_uses_same_shadow_aware_chip_owner():
    dom = object.__new__(YouTubeStudioDOM)
    dom.driver = SimpleNamespace(execute_script=Mock(return_value={"chipTexts": ["Has schedule"], "url": page()["url"]}))
    assert dom.read_visibility_filter_state()["detected"] == "SCHEDULED"
    assert dom.driver.execute_script.call_args.args == (inv.FILTER_STATE_SCRIPT,)


@pytest.mark.parametrize("chips,detected", [
    (["Title contains Unlisted"], None),
    (["Title contains Scheduled"], None),
    (["Title contains Scheduled", "Visibility: Unlisted"], "UNLISTED"),
])
def test_legacy_visibility_reader_does_not_promote_title_chips(chips, detected):
    dom = object.__new__(YouTubeStudioDOM)
    dom.driver = SimpleNamespace(execute_script=Mock(return_value={"chipTexts": chips, "url": page()["url"]}))
    assert dom.read_visibility_filter_state()["detected"] == detected


@pytest.mark.parametrize("changes", [
    {"chip_texts": []}, {"chip_texts": ["Visibility: Unlisted"]},
    {"chip_texts": ["Has schedule", "Title contains demo"]},
    {"chip_texts": ["Visibility: Scheduled, Unlisted"]},
    {"search_text": "demo"}, {"chip_texts": ["Visibility: Unknown"]},
])
def test_failed_or_extra_filter_never_becomes_zero(changes):
    result = receipt(page(**changes))
    assert result["status"] == "failed" and result["total_scheduled"] is None
    assert result["videos"] == [] and not inv.qualified_inventory(result, CHANNEL)


@pytest.mark.parametrize("changes", [
    {"channel_id": "UCother"}, {"channel_id": None},
    {"url": "https://studio.youtube.com/channel/UCother/videos/short"},
    {"url": f"https://example.com/channel/{CHANNEL}/videos/short"},
    {"url": f"https://studio.youtube.com/channel/{CHANNEL}/comments/inbox"},
    {"url": f"https://studio.youtube.com/channel/{CHANNEL}/videos/short/extra"},
])
def test_native_and_url_receiving_account_must_agree(changes):
    result = receipt(page(**changes))
    assert result["status"] == "failed" and result["total_scheduled"] is None
    assert "receiving_channel_unverified" in result["issues"]


@pytest.mark.parametrize("bad_row", [
    row(schedule="Scheduled"), row(schedule="Unlisted Oct 30, 2026, 9:15 AM"),
    row(schedule="Scheduled Feb 30, 2026, 9:15 AM"),
    row(schedule="Scheduled Oct 30, 2026, 29:15 AM"),
    row(schedule="Scheduled Oct 30, 2026, 9:15 AM; Oct 31, 2026"),
    row(video_id=""), {"title": "A row without identity"},
])
def test_parse_failures_retain_raw_observations_and_never_use_upload_date(bad_row):
    result = receipt(page([bad_row]))
    assert result["status"] == "partial" and result["total_scheduled"] is None
    assert result["rows_seen"] == 1 and result["rows_parsed"] == 0
    assert len(result["unparsed_rows"]) == 1
    if bad_row.get("date_text"):
        assert result["unparsed_rows"][0]["date_text"] == bad_row["date_text"]


def test_mixed_good_and_unparsed_rows_keep_useful_positive_evidence():
    result = receipt(page([row(), row(SECOND, "Scheduled")]))
    assert result["status"] == "partial" and result["total_scheduled"] is None
    assert [video["video_id"] for video in result["videos"]] == [FIRST]
    assert result["rows_seen"] == 2 and result["rows_parsed"] == 1


@pytest.mark.parametrize("date_text,date_label", [
    ("Scheduled Oct 31, 2026, 10:30 AM", ""),
    ("Oct 31, 2026, 10:30 AM", "Scheduled"),
    ("Oct 31, 2026", "Scheduled for Oct 31, 2026, 10:30 AM"),
])
def test_explicit_schedule_labeled_modern_date_cell_is_useful_positive(date_text, date_label):
    source = row(schedule="Scheduled")
    source.update(date_text=date_text, date_label=date_label)
    result = receipt(page([source]))
    assert inv.qualified_inventory(result, CHANNEL)
    assert result["videos"][0]["schedule_source"] == "schedule_labeled_date_cell"
    assert (result["videos"][0]["date"], result["videos"][0]["time"]) == ("Oct 31, 2026", "10:30 AM")


@pytest.mark.parametrize("date_text,date_label", [
    ("Oct 31, 2026, 10:30 AM", ""),
    ("Uploaded Oct 31, 2026, 10:30 AM", "Scheduled"),
    ("Oct 31, 2026, 10:30 AM", "Published"),
    ("Scheduled Oct 31, 2026, 10:30 AM", "Published"),
])
def test_generic_uploaded_or_published_date_cell_cannot_become_schedule(date_text, date_label):
    source = row(schedule="Scheduled")
    source.update(date_text=date_text, date_label=date_label)
    result = receipt(page([source]))
    assert result["status"] == "partial" and result["total_scheduled"] is None


def test_conflicting_explicit_schedule_cells_are_unknown():
    source = row()
    source["date_text"] = "Scheduled Oct 31, 2026, 10:30 AM"
    assert receipt(page([source]))["total_scheduled"] is None


def test_numeric_video_identity_is_rejected_at_collector_and_sink():
    assert receipt(page([row(video_id=12345678901)]))["total_scheduled"] is None
    result = receipt()
    result["videos"][0]["video_id"] = 12345678901
    assert not inv.qualified_inventory(result, CHANNEL)


@pytest.mark.parametrize("channel", ["", None, 123])
def test_malformed_expected_channel_cannot_qualify_even_an_empty_receipt(channel):
    result = receipt(page([], empty=True))
    result["channel_id"] = channel
    assert not inv.qualified_inventory(result, channel)


def test_qualified_empty_is_complete_and_known_zero():
    result = receipt(page([], empty=True))
    assert inv.qualified_inventory(result, CHANNEL)
    assert result["total_scheduled"] == 0 and result["videos"] == []


@pytest.mark.parametrize("changes,issue", [
    ({"empty": False}, "empty_state_unverified"),
    ({"empty": True, "next_page": None}, "pagination_unknown"),
    ({"empty": True, "previous_page": None}, "pagination_start_unverified"),
    ({"empty": True, "previous_page": True}, "pagination_start_unverified"),
    ({"empty": True, "loading": True}, "page_rows_unqualified"),
])
def test_empty_loading_or_middle_page_is_unknown(changes, issue):
    result = receipt(page([], **changes))
    assert result["total_scheduled"] is None and issue in result["issues"]


@pytest.mark.parametrize("bad_rows", [False, True])
def test_repeated_page_stops_bounded_even_when_every_slot_unparsed(bad_rows):
    source = page([row(schedule="Scheduled")] if bad_rows else [row()], next_page=True)
    dom = Pages(source, {**source, "previous_page": True})
    result = inv.collect_scheduled_inventory(dom, CHANNEL)
    assert result["status"] == "partial" and result["total_scheduled"] is None
    assert "repeated_video_or_page" in result["issues"]
    assert dom.reads == 2 and dom.clicks == 1 and result["rows_seen"] == 1


@pytest.mark.parametrize("previous", [False, None])
def test_different_rows_after_no_progress_cannot_prove_pagination(previous):
    result = receipt(page(next_page=True), page([row(SECOND)], previous_page=previous))
    assert result["status"] == "partial" and result["total_scheduled"] is None
    assert "pagination_progress_unverified" in result["issues"]
    assert [video["video_id"] for video in result["videos"]] == [FIRST]


@pytest.mark.parametrize("later,issue", [
    (page([row(SECOND)], channel_id="UCother", previous_page=True), "receiving_channel_unverified"),
    (page([row(SECOND)], chip_texts=[], previous_page=True), "scheduled_filter_unverified"),
    (RuntimeError("synthetic read failure"), "page_read_failed"),
])
def test_later_failure_keeps_earlier_bound_rows_without_absence_claim(later, issue):
    result = receipt(page(next_page=True), later)
    assert result["status"] == "partial" and result["total_scheduled"] is None
    assert [video["video_id"] for video in result["videos"]] == [FIRST]
    assert issue in result["issues"]


def test_unknown_pagination_page_limit_and_click_failure_are_partial():
    for dom, options, issue in [
        (Pages(page(next_page=None)), {}, "pagination_unknown"),
        (Pages(page(next_page=True)), {"max_pages": 1}, "page_limit"),
        (Pages(page(next_page=True), click_error=True), {}, "pagination_failed"),
    ]:
        result = inv.collect_scheduled_inventory(dom, CHANNEL, **options)
        assert result["total_scheduled"] is None and issue in result["issues"]
        assert result["observed_scheduled_count"] == 1


@pytest.mark.parametrize("limit", [True, 0, 101, "1"])
def test_invalid_page_budget_is_rejected_before_read(limit):
    dom = Pages(page())
    assert inv.collect_scheduled_inventory(dom, CHANNEL, max_pages=limit)["status"] == "failed"
    assert dom.reads == 0


def auditor(result):
    owner = object.__new__(ScheduleAuditor)
    owner.channel_id, owner.channel_name = CHANNEL, "FoundUps"
    owner.tracker = Mock()
    owner.tracker.get_all_scheduled_video_ids.return_value = [FIRST]
    owner._read_scheduled_inventory = lambda: result
    return owner


def test_complete_audit_has_useful_positive_health_and_collision_results():
    healthy = auditor(receipt()).run_audit(auto_heal=True)
    assert healthy["status"] == "complete" and healthy["healthy"] is True
    collision = auditor(receipt(page([row(), row(SECOND)]))).run_audit()
    assert collision["healthy"] is False and len(collision["time_collisions"]) == 1


def test_partial_audit_never_purges_tracker_or_certifies_absence():
    owner = auditor(receipt(page([row(), row(SECOND, "Scheduled")])))
    owner.tracker.get_all_scheduled_video_ids.return_value = [FIRST, SECOND]
    result = owner.run_audit(auto_heal=True)
    assert result["healthy"] is None and result["total_scheduled"] is None
    assert result["false_positives"] == [] and len(result["youtube_scheduled"]) == 1
    assert owner.tracker.remove_video.call_count == 0


def test_complete_empty_can_establish_absence_for_explicit_autoheal():
    owner = auditor(receipt(page([], empty=True)))
    result = owner.run_audit(auto_heal=True)
    assert result["total_scheduled"] == 0 and result["healthy"] is False
    assert owner.tracker.remove_video.call_args.args == (FIRST,)


@pytest.mark.parametrize("navigation", [True, False])
def test_actual_auditor_navigation_and_dom_receipt_integration(monkeypatch, tmp_path, navigation):
    monkeypatch.setattr(ContentPageScheduler, "navigate_to_scheduled", lambda *_: navigation)
    owner = ScheduleAuditor("foundups", Pages(page()), storage_dir=tmp_path)
    result = owner._read_scheduled_inventory()
    assert result["status"] == ("complete" if navigation else "failed")
    assert result["total_scheduled"] == (1 if navigation else None)


def test_malformed_complete_receipt_cannot_be_reported_as_complete_or_heal():
    result = receipt()
    result["filter_verified"] = False
    owner = auditor(result)
    report = owner.run_audit(auto_heal=True)
    assert report["status"] == "failed" and report["total_scheduled"] is None
    assert owner.tracker.remove_video.call_count == 0


@pytest.mark.parametrize("kind", ["missing", "partial", "wrong_channel", "mismatched_list", "invalid_slot", "none_list", "tuple_list"])
def test_tracker_reset_requires_matching_complete_receipt(tmp_path, kind):
    owner = ScheduleTracker(CHANNEL, storage_dir=tmp_path)
    owner.schedule, owner.video_ids = {"Oct 29, 2026": 1}, {"Oct 29, 2026": [SECOND]}
    owner.save()
    before = owner.tracker_file.read_bytes()
    before_state = (copy.deepcopy(owner.schedule), copy.deepcopy(owner.video_ids))
    result, videos = receipt(), None
    videos = result["videos"]
    if kind == "missing": result = None
    elif kind == "partial": result["status"] = "partial"
    elif kind == "wrong_channel": result["channel_id"] = "UCother"
    elif kind == "mismatched_list": videos = []
    elif kind == "none_list": videos = None
    elif kind == "tuple_list": videos = tuple(videos)
    else: result["videos"][0]["date"] = "Jan 1, 1900"
    assert owner.sync_from_youtube(videos, inventory=result) is False
    assert owner.tracker_file.read_bytes() == before
    assert (owner.schedule, owner.video_ids) == before_state


def test_tracker_sync_accepts_positive_and_qualified_empty(tmp_path):
    owner = ScheduleTracker(CHANNEL, storage_dir=tmp_path)
    result = receipt()
    assert owner.sync_from_youtube(result["videos"], inventory=result)
    assert owner.video_ids == {"Oct 30, 2026": [FIRST]}
    empty = receipt(page([], empty=True))
    assert owner.sync_from_youtube([], inventory=empty)
    assert owner.schedule == {} and owner.video_ids == {}


@pytest.mark.parametrize("complete", [True, False])
def test_cps_calendar_reports_clean_only_from_complete_inventory(complete):
    result = receipt() if complete else receipt(page([row(), row(SECOND, "Scheduled")]))
    owner = ContentPageScheduler(None, SimpleNamespace(read_scheduled_inventory=lambda *_: result))
    owner.navigate_to_scheduled = lambda *_: True
    audit = owner.audit_calendar("foundups")
    assert audit["status"] == result["status"]
    assert audit["total_scheduled"] == (1 if complete else None)
    assert any("looks clean" in item for item in audit["recommendations"]) is complete
    assert len(audit["videos"]) == 1


def test_cps_failed_navigation_never_yields_clean_zero():
    owner = ContentPageScheduler(None, SimpleNamespace())
    owner.navigate_to_scheduled = lambda *_: False
    result = owner.audit_calendar("foundups")
    assert result["status"] == "failed" and result["total_scheduled"] is None
    assert not any("looks clean" in item for item in result["recommendations"])


def repair_owner(monkeypatch):
    from modules.platform_integration.youtube_shorts_scheduler.src import content_page_scheduler as cps

    monkeypatch.setattr(cps.time_module, "sleep", lambda *_: None)
    result = receipt(page([row(), row(SECOND)]))
    dom = Mock()
    dom.read_scheduled_inventory.return_value = result
    dom.human_delay.return_value = 0
    dom.schedule_video.return_value = True
    owner = ContentPageScheduler(SimpleNamespace(find_elements=lambda *_: []), dom)
    owner.navigate_to_scheduled = lambda *_: True
    audit = owner.audit_calendar("foundups", max_per_day=1)
    tracker = Mock(channel_id=CHANNEL)
    tracker.get_next_available_slot.return_value = ("Nov 1, 2026", "10:00 AM")
    return owner, dom, tracker, audit


@pytest.mark.parametrize("kind", ["missing", "partial", "wrong_channel", "mismatched_videos"])
def test_thinning_refuses_forged_complete_without_matching_inventory(monkeypatch, kind):
    owner, dom, tracker, audit = repair_owner(monkeypatch)
    if kind == "missing": audit.pop("inventory")
    elif kind == "partial": audit["inventory"]["status"] = "partial"
    elif kind == "wrong_channel": tracker.channel_id = "UCother"
    else: audit["videos"] = []
    result = asyncio.run(owner.thin_schedule(audit, tracker, ["10:00 AM"], max_per_day=1))
    assert result["error"] == "calendar_inventory_incomplete"
    assert dom.navigate_to_video.call_count == dom.schedule_video.call_count == 0
    assert tracker.get_next_available_slot.call_count == 0


def test_qualified_heavy_day_remains_a_useful_repair_input(monkeypatch):
    owner, dom, tracker, audit = repair_owner(monkeypatch)
    result = asyncio.run(owner.thin_schedule(audit, tracker, ["10:00 AM"], max_per_day=1))
    assert result["rescheduled"] == 1
    assert dom.navigate_to_video.call_args.args == (SECOND,)
    assert dom.schedule_video.call_args.args == ("Nov 1, 2026", "10:00 AM")


@pytest.mark.parametrize("kind", ["missing", "partial", "unbound_member", "unbound_slot"])
def test_conflict_writer_requires_bound_complete_receipt(monkeypatch, kind):
    owner, dom, tracker, audit = repair_owner(monkeypatch)
    inventory = audit["inventory"]
    if kind == "missing": inventory = None
    elif kind == "partial": inventory["status"] = "partial"
    elif kind == "unbound_member": audit["conflicts"][0]["videos"][1]["video_id"] = "XXXXXXXXXXX"
    else: audit["conflicts"][0]["slot"] = "Jan 1, 1900 1:00 AM"
    result = asyncio.run(owner.resolve_conflicts(audit["conflicts"], tracker, ["10:00 AM"], inventory=inventory))
    assert "error" in result
    assert dom.navigate_to_video.call_count == dom.schedule_video.call_count == 0
    assert tracker.get_next_available_slot.call_count == 0


def test_qualified_conflict_remains_a_useful_repair_input(monkeypatch):
    owner, dom, tracker, audit = repair_owner(monkeypatch)
    result = asyncio.run(owner.resolve_conflicts(audit["conflicts"], tracker, ["10:00 AM"], inventory=audit["inventory"]))
    assert result["rescheduled"] == 1
    assert dom.navigate_to_video.call_args.args == (SECOND,)


@pytest.mark.parametrize("complete", [True, False])
def test_scheduler_sync_routes_only_qualified_inventory(monkeypatch, complete):
    monkeypatch.setenv("YT_SCHEDULER_DO_SYNC", "true")
    monkeypatch.setattr(ContentPageScheduler, "navigate_to_scheduled", lambda *_: True)
    owner = object.__new__(YouTubeShortsScheduler)
    owner.channel_id, owner.channel_key, owner.driver = CHANNEL, "foundups", None
    result = receipt() if complete else receipt(page(next_page=None))
    owner.dom = SimpleNamespace(read_scheduled_inventory=lambda *_: result)
    owner.tracker = Mock()
    asyncio.run(owner._sync_scheduled_videos())
    assert owner.tracker.sync_from_youtube.call_count == int(complete)
    if complete:
        assert owner.tracker.sync_from_youtube.call_args.kwargs["inventory"] == result


def test_cps_filter_failure_does_not_continue_unfiltered(monkeypatch):
    from modules.platform_integration.youtube_shorts_scheduler.src import content_page_scheduler as cps

    owner = ContentPageScheduler(SimpleNamespace(current_url=f"https://studio.youtube.com/channel/{CHANNEL}/videos/short"), SimpleNamespace())
    owner._switch_content_tab = lambda *_: True
    owner._apply_visibility_filter_via_ui = lambda *_: False
    monkeypatch.setattr(cps, "WebDriverWait", lambda *_: SimpleNamespace(until=lambda *_: True))
    assert owner.navigate_to_content("foundups", visibility="SCHEDULED") is False
