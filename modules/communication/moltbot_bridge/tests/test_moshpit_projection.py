"""Synthetic-only projection/renderer contracts, with no remote effects."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone, tzinfo

import pytest

from modules.communication.moltbot_bridge.src.moshpit_projection import (
    AuthorizedActivitySnapshot, MoshpitRejected, MoshpitRequest, project_moshpit,
)
from modules.communication.moltbot_bridge.src.moshpit_render import render_moshpit_html
from modules.communication.moltbot_bridge.src.openclaw_memory_queries import query_moshpit


NOW = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
REQUEST = MoshpitRequest("synthetic-owner", "synthetic-project", "stakeholder", "snapshot-1")


def crumb(event_id="event-1", **changes):
    event = dict(
        principal_id=REQUEST.principal_id, foundup_id=REQUEST.foundup_id,
        event_id=event_id, event_time="2026-09-09T08:00:00+09:00",
        kind="meeting", truth="OBSERVED", parent_event_id=None,
        views={
            "stakeholder": {"actor": "012", "summary": "地域の会合を実施", "details": ["次の協議事項を確認。"]},
            "principal_private": {"actor": "PRIVATE_COUNTERPARTY", "summary": "PRIVATE_COUNTERPARTY", "details": ["PRIVATE_EVIDENCE"]},
        },
    )
    event.update(changes)
    return {"id": 1, "data": {"moshpit": event, "raw_email": "PRIVATE_SECRET_BEARER"}}


class SyntheticAuthorizedSource:
    """Fixture, not a reusable authentication implementation."""
    def __init__(self, rows):
        self.batch = AuthorizedActivitySnapshot(
            REQUEST.principal_id, REQUEST.foundup_id, REQUEST.disclosure_class,
            REQUEST.snapshot_id, NOW + timedelta(minutes=5), rows,
        )
        self.calls = 0

    def read_authorized_activity(self, request, capability):
        self.calls += 1
        if capability != "fixture-authorized":
            raise PermissionError("synthetic private failure detail")
        return self.batch


def project(rows, **kwargs):
    return project_moshpit(
        REQUEST, source=SyntheticAuthorizedSource(rows), capability="fixture-authorized", now=NOW, **kwargs,
    )


def test_activity_only_disclosure_and_source_preservation():
    rows = [crumb(), crumb("notice", kind="system_notice"), crumb("plan", truth="PROPOSED"),
            crumb("inference", truth="INFERRED"), {"action": "unclassified sync"}]
    before = deepcopy(rows)
    result = project(rows)
    assert len(result["days"][0]["entries"]) == 1
    assert "PRIVATE" not in str(result)
    assert result["days"][0]["entries"][0]["actor"] == "012"
    assert rows == before


def test_timezone_reverse_order_date_only_unknown_and_dedup():
    rows = [crumb("old", event_time="2026-09-08"), crumb("unknown", event_time=None),
            crumb("new", event_time="2026-09-09T16:30:00Z"), crumb("old", event_time="2026-09-08")]
    result = project(rows)
    assert [d["date"] for d in result["days"]] == ["2026-09-10", "2026-09-08", None]
    assert len(result["days"][1]["entries"]) == 1


def test_folded_replies_do_not_become_top_level_activities_or_leak_orphans():
    rows = [crumb(), crumb("reply", kind="discussion", truth="PROPOSED", parent_event_id="event-1"),
            crumb("orphan", kind="discussion", parent_event_id="hidden")]
    result = project(rows)
    entries = result["days"][0]["entries"]
    assert len(entries) == 1
    assert entries[0]["replies"][0]["truth"] == "PROPOSED"
    assert "orphan" not in str(result)
    html = render_moshpit_html(result)
    assert "<details><summary>" in html and "<details open" not in html
    assert "提案" in html


@pytest.mark.parametrize("field,value", [
    ("principal_id", "other-owner"), ("foundup_id", "other-project"),
    ("disclosure_class", "principal_private"), ("snapshot_id", "old-snapshot"),
    ("expires_at", NOW), ("expires_at", NOW.replace(tzinfo=None)),
])
def test_mismatched_or_expired_host_response_rejects(field, value):
    source = SyntheticAuthorizedSource([crumb()])
    source.batch = replace(source.batch, **{field: value})
    with pytest.raises(MoshpitRejected):
        project_moshpit(REQUEST, source=source, capability="fixture-authorized", now=NOW)


@pytest.mark.parametrize("capability", [None, "revoked", "expired", "forged", "wrong-member"])
def test_missing_or_denied_authority_stops_projection(capability):
    source = SyntheticAuthorizedSource([crumb()])
    with pytest.raises(MoshpitRejected) as error:
        project_moshpit(REQUEST, source=source, capability=capability, now=NOW)
    assert "private failure" not in str(error.value)
    if capability is None:
        assert source.calls == 0


def test_query_entrypoint_has_no_legacy_or_ungated_fallback():
    with pytest.raises(MoshpitRejected, match="authorization_required"):
        query_moshpit(REQUEST)


@pytest.mark.parametrize("changes", [
    {"principal_id": "foreign"}, {"foundup_id": "foreign"},
    {"event_time": "yesterday"}, {"event_time": "2026-09-09T09:00:00"},
    {"event_time": "9999-12-31T23:59:59Z"}, {"kind": []}, {"truth": {}},
])
def test_foreign_event_or_invented_time_rejects(changes):
    with pytest.raises(MoshpitRejected):
        project([crumb(**changes)])


def test_missing_stakeholder_view_never_falls_back_to_private():
    assert project([crumb(views={"principal_private": {"summary": "SECRET"}})])["days"] == []


@pytest.mark.parametrize("disclosure", ["stakeholder", "public"])
def test_nonprivate_views_do_not_expose_private_fields_in_json_or_html(disclosure):
    rows = [crumb()]
    views = rows[0]["data"]["moshpit"]["views"]
    views["public"] = {"actor": "0102", "summary": "資料を更新", "details": []}
    source = SyntheticAuthorizedSource(rows)
    source.batch = replace(source.batch, disclosure_class=disclosure)
    result = project_moshpit(
        replace(REQUEST, disclosure_class=disclosure), source=source,
        capability="fixture-authorized", now=NOW,
    )
    assert "PRIVATE" not in str(result) + render_moshpit_html(result)
    assert result["days"][0]["entries"][0]["summary"] == views[disclosure]["summary"]


def test_conflicting_identity_requires_reconciliation():
    with pytest.raises(MoshpitRejected, match="conflicting_event_identity"):
        project([crumb(), crumb(event_time="2026-09-08")])


def test_limit_bounds_and_truncation_are_explicit():
    source = SyntheticAuthorizedSource([crumb("a"), crumb("b")])
    result = project_moshpit(replace(REQUEST, limit=1), source=source, capability="fixture-authorized", now=NOW)
    assert result["has_more"] and len(result["days"][0]["entries"]) == 1
    for limit in (0, -1, 101, True):
        with pytest.raises(MoshpitRejected, match="invalid_limit"):
            project_moshpit(replace(REQUEST, limit=limit), source=source, capability="fixture-authorized", now=NOW)
    with pytest.raises(MoshpitRejected, match="snapshot_bounds_exceeded"):
        project([crumb()] * 501)


def test_html_escapes_untrusted_content_and_preserves_reported_truth():
    result = project([crumb(truth="REPORTED_BY_012", views={"stakeholder": {
        "actor": "0102", "summary": "<script>alert(1)</script>", "details": ['<img src=x onerror="alert(1)">'],
    }})])
    html = render_moshpit_html(result)
    assert "<script>" not in html and "<img" not in html
    assert "&lt;script&gt;" in html and "012からの報告" in html


def test_malformed_disclosure_fails_with_bounded_error():
    with pytest.raises(MoshpitRejected, match="invalid_disclosure"):
        project_moshpit(replace(REQUEST, disclosure_class=[]), source=None)


def test_snapshot_expiring_during_source_read_rejects(monkeypatch):
    from modules.communication.moltbot_bridge.src import moshpit_projection as module

    class ControlledDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock[0].astimezone(tz)

    clock = [ControlledDateTime(2026, 9, 9, 12, tzinfo=timezone.utc)]
    source = SyntheticAuthorizedSource([crumb()])
    source.batch = replace(source.batch, expires_at=clock[0] + timedelta(seconds=1))
    read = source.read_authorized_activity

    def delayed_read(request, capability):
        clock[0] += timedelta(seconds=2)
        return read(request, capability)

    monkeypatch.setattr(source, "read_authorized_activity", delayed_read)
    monkeypatch.setattr(module, "datetime", ControlledDateTime)
    with pytest.raises(MoshpitRejected, match="snapshot_expired"):
        project_moshpit(REQUEST, source=source, capability="fixture-authorized")
    assert source.calls == 1


def test_snapshot_expiring_during_projection_rejects(monkeypatch):
    from modules.communication.moltbot_bridge.src import moshpit_projection as module

    class ControlledDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock[0].astimezone(tz)

    clock = [ControlledDateTime(2026, 9, 9, 12, tzinfo=timezone.utc)]
    source = SyntheticAuthorizedSource([crumb()])
    source.batch = replace(source.batch, expires_at=clock[0] + timedelta(seconds=1))
    days = module._days

    def delayed_projection(records, limit):
        result = days(records, limit)
        clock[0] += timedelta(seconds=2)
        return result

    monkeypatch.setattr(module, "datetime", ControlledDateTime)
    monkeypatch.setattr(module, "_days", delayed_projection)
    with pytest.raises(MoshpitRejected, match="snapshot_expired"):
        project_moshpit(REQUEST, source=source, capability="fixture-authorized")
    assert source.calls == 1


class NoOffset(tzinfo):
    def utcoffset(self, value):
        return None


@pytest.mark.parametrize("bad", [True, 0, "now", [], NOW.replace(tzinfo=None), NOW.replace(tzinfo=NoOffset())])
def test_invalid_clock_rejects_before_source_read(bad):
    source = SyntheticAuthorizedSource([crumb()])
    with pytest.raises(MoshpitRejected, match="invalid_clock"):
        project_moshpit(REQUEST, source=source, capability="fixture-authorized", now=bad)
    assert source.calls == 0


@pytest.mark.parametrize("bad", [None, True, 1, "future", {}, NOW.replace(tzinfo=NoOffset())])
def test_malformed_expiry_is_a_bounded_rejection(bad):
    source = SyntheticAuthorizedSource([crumb()])
    source.batch = replace(source.batch, expires_at=bad)
    with pytest.raises(MoshpitRejected, match="snapshot_expired"):
        project_moshpit(REQUEST, source=source, capability="fixture-authorized", now=NOW)


@pytest.mark.parametrize("field,value,error", [
    ("principal_id", None, "invalid_activity_text"),
    ("foundup_id", [], "invalid_activity_text"),
    ("snapshot_id", "\x00", "invalid_activity_text"),
    ("snapshot_id", "x" * 201, "invalid_activity_text"),
    ("disclosure_class", True, "invalid_disclosure"),
    ("timezone", None, "invalid_timezone"),
    ("timezone", "missing/timezone", "invalid_timezone"),
    ("limit", 1.0, "invalid_limit"),
    ("limit", float("nan"), "invalid_limit"),
    ("limit", float("inf"), "invalid_limit"),
])
def test_bad_request_rejects_before_source_read(field, value, error):
    source = SyntheticAuthorizedSource([crumb()])
    with pytest.raises(MoshpitRejected, match=error):
        project_moshpit(replace(REQUEST, **{field: value}), source=source,
                        capability="fixture-authorized", now=NOW)
    assert source.calls == 0


@pytest.mark.parametrize("bad", [None, {}, [], True])
def test_nonrequest_value_does_not_reach_source(bad):
    source = SyntheticAuthorizedSource([])
    with pytest.raises(MoshpitRejected, match="invalid_request"):
        project_moshpit(bad, source=source, capability="fixture-authorized", now=NOW)
    assert source.calls == 0


@pytest.mark.parametrize("bad", [None, {}, [], True])
def test_only_explicit_snapshot_shape_is_accepted(bad):
    source = SyntheticAuthorizedSource([])
    source.batch = bad
    with pytest.raises(MoshpitRejected, match="invalid_authorized_snapshot"):
        project_moshpit(REQUEST, source=source, capability="fixture-authorized", now=NOW)


@pytest.mark.parametrize("rows", [None, {}, "rows", True])
def test_nonsequence_snapshot_payload_rejects(rows):
    with pytest.raises(MoshpitRejected, match="snapshot_bounds_exceeded"):
        project(rows)


@pytest.mark.parametrize("row,error", [
    (None, "invalid_breadcrumb"), ([], "invalid_breadcrumb"),
    ({"data": {"moshpit": []}}, "invalid_activity"),
    ({"data": {"moshpit": None}}, "invalid_activity"),
])
def test_malformed_explicit_activity_never_becomes_legacy_fallback(row, error):
    with pytest.raises(MoshpitRejected, match=error):
        project([row])


@pytest.mark.parametrize("field,value,error", [
    ("actor", "a" * 121, "invalid_activity_text"),
    ("actor", None, "invalid_activity_text"),
    ("summary", "s" * 241, "invalid_activity_text"),
    ("summary", {}, "invalid_activity_text"),
    ("details", ["d"] * 13, "invalid_details"),
    ("details", "text", "invalid_details"),
    ("details", [{}], "invalid_activity_text"),
    ("details", ["d" * 2001], "invalid_activity_text"),
    ("details", ["\x00"], "invalid_activity_text"),
])
def test_text_and_detail_bounds_reject(field, value, error):
    view = {"actor": "actor", "summary": "summary", "details": []}
    view[field] = value
    with pytest.raises(MoshpitRejected, match=error):
        project([crumb(views={"stakeholder": view})])


def test_exact_text_and_snapshot_limits_remain_usable():
    view = {"actor": "a" * 120, "summary": "s" * 240, "details": ["d" * 2000] * 12}
    assert project([crumb(views={"stakeholder": view})])["days"][0]["entries"][0]["details"] == view["details"]
    rows = [crumb(str(index)) for index in range(500)]
    result = project_moshpit(replace(REQUEST, limit=100), source=SyntheticAuthorizedSource(rows),
                             capability="fixture-authorized", now=NOW)
    assert sum(len(day["entries"]) for day in result["days"]) == 100
    assert result["has_more"] is True
    with pytest.raises(MoshpitRejected, match="snapshot_bounds_exceeded"):
        project(rows + [crumb("overflow")])
    assert project([])["days"] == []


@pytest.mark.parametrize("count,more", [(50, False), (51, True)])
def test_reply_limit_reports_omission_without_promoting_discussion(count, more):
    rows = [crumb()] + [crumb(f"reply-{index:03}", kind="discussion", parent_event_id="event-1")
                        for index in range(count)]
    result = project(rows)
    entries = result["days"][0]["entries"]
    assert len(entries) == 1 and len(entries[0]["replies"]) == 50
    assert entries[0]["more_replies"] is more
    assert entries[0]["replies"][0]["event_id"] == "reply-000"


@pytest.mark.parametrize("disclosure", ["principal_private", "team_pc", "stakeholder", "public"])
def test_all_projection_audiences_exclude_raw_contact_fields(disclosure):
    forbidden = {key: "PRIVATE_FIELD_SENTINEL" for key in (
        "contact_id", "contact_card_index", "bcc", "coordinates", "identity_resolution", "body",
    )}
    view = {"actor": "curated actor", "summary": "curated event", "details": ["curated detail"], **forbidden}
    row = crumb(views={disclosure: view}, **forbidden)
    row.update(forbidden)
    source = SyntheticAuthorizedSource([row])
    source.batch = replace(source.batch, disclosure_class=disclosure)
    result = project_moshpit(replace(REQUEST, disclosure_class=disclosure), source=source,
                             capability="fixture-authorized", now=NOW)
    assert "PRIVATE_FIELD_SENTINEL" not in str(result) + render_moshpit_html(result)
    entry = result["days"][0]["entries"][0]
    assert set(entry) == {"event_id", "actor", "summary", "details", "truth", "replies", "more_replies"}


def test_renderer_escapes_actor_summary_and_reply_without_script_markup():
    hostile = '\"><svg onload="alert(1)">&'
    view = {"actor": hostile, "summary": hostile, "details": [hostile]}
    rows = [crumb(views={"stakeholder": view}),
            crumb("reply", kind="discussion", parent_event_id="event-1", views={"stakeholder": view})]
    html = render_moshpit_html(project(rows))
    assert "<svg" not in html and 'onload="alert(1)"' not in html
    assert html.count("&lt;svg") == 6 and "&quot;" in html and "&amp;" in html


def test_query_seam_uses_only_explicit_source_without_database_fallback(monkeypatch):
    from modules.communication.moltbot_bridge.src import openclaw_memory_queries as module
    source = SyntheticAuthorizedSource([crumb()])
    source.batch = replace(source.batch, expires_at=datetime.now(timezone.utc) + timedelta(minutes=1))

    def forbidden(*args, **kwargs):
        raise AssertionError("legacy query must not run")

    for name in ("search_breadcrumbs", "query_past_work", "query_cross_surface_activity"):
        monkeypatch.setattr(module, name, forbidden)
    result = query_moshpit(REQUEST, source=source, capability="fixture-authorized")
    assert source.calls == 1 and result["schema_version"] == "moshpit_projection.v1"
    with pytest.raises(MoshpitRejected, match="authorization_required"):
        query_moshpit(REQUEST, source=source)
    assert source.calls == 1
