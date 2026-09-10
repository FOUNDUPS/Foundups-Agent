"""Synthetic-only projection/renderer contracts, with no remote effects."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from modules.communication.moltbot_bridge.src.mosh_pit_projection import (
    AuthorizedActivitySnapshot, MoshPitRejected, MoshPitRequest, project_mosh_pit,
)
from modules.communication.moltbot_bridge.src.mosh_pit_render import render_mosh_pit_html
from modules.communication.moltbot_bridge.src.openclaw_memory_queries import query_mosh_pit


NOW = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
REQUEST = MoshPitRequest("synthetic-owner", "synthetic-project", "stakeholder", "snapshot-1")


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
    return {"id": 1, "data": {"mosh_pit": event, "raw_email": "PRIVATE_SECRET_BEARER"}}


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
    return project_mosh_pit(
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
    html = render_mosh_pit_html(result)
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
    with pytest.raises(MoshPitRejected):
        project_mosh_pit(REQUEST, source=source, capability="fixture-authorized", now=NOW)


@pytest.mark.parametrize("capability", [None, "revoked", "expired", "forged", "wrong-member"])
def test_missing_or_denied_authority_stops_projection(capability):
    source = SyntheticAuthorizedSource([crumb()])
    with pytest.raises(MoshPitRejected) as error:
        project_mosh_pit(REQUEST, source=source, capability=capability, now=NOW)
    assert "private failure" not in str(error.value)
    if capability is None:
        assert source.calls == 0


def test_query_entrypoint_has_no_legacy_or_ungated_fallback():
    with pytest.raises(MoshPitRejected, match="authorization_required"):
        query_mosh_pit(REQUEST)


@pytest.mark.parametrize("changes", [
    {"principal_id": "foreign"}, {"foundup_id": "foreign"},
    {"event_time": "yesterday"}, {"event_time": "2026-09-09T09:00:00"},
    {"event_time": "9999-12-31T23:59:59Z"}, {"kind": []}, {"truth": {}},
])
def test_foreign_event_or_invented_time_rejects(changes):
    with pytest.raises(MoshPitRejected):
        project([crumb(**changes)])


def test_missing_stakeholder_view_never_falls_back_to_private():
    assert project([crumb(views={"principal_private": {"summary": "SECRET"}})])["days"] == []


@pytest.mark.parametrize("disclosure", ["stakeholder", "public"])
def test_nonprivate_views_do_not_expose_private_fields_in_json_or_html(disclosure):
    rows = [crumb()]
    views = rows[0]["data"]["mosh_pit"]["views"]
    views["public"] = {"actor": "0102", "summary": "資料を更新", "details": []}
    source = SyntheticAuthorizedSource(rows)
    source.batch = replace(source.batch, disclosure_class=disclosure)
    result = project_mosh_pit(
        replace(REQUEST, disclosure_class=disclosure), source=source,
        capability="fixture-authorized", now=NOW,
    )
    assert "PRIVATE" not in str(result) + render_mosh_pit_html(result)
    assert result["days"][0]["entries"][0]["summary"] == views[disclosure]["summary"]


def test_conflicting_identity_requires_reconciliation():
    with pytest.raises(MoshPitRejected, match="conflicting_event_identity"):
        project([crumb(), crumb(event_time="2026-09-08")])


def test_limit_bounds_and_truncation_are_explicit():
    source = SyntheticAuthorizedSource([crumb("a"), crumb("b")])
    result = project_mosh_pit(replace(REQUEST, limit=1), source=source, capability="fixture-authorized", now=NOW)
    assert result["has_more"] and len(result["days"][0]["entries"]) == 1
    for limit in (0, -1, 101, True):
        with pytest.raises(MoshPitRejected, match="invalid_limit"):
            project_mosh_pit(replace(REQUEST, limit=limit), source=source, capability="fixture-authorized", now=NOW)
    with pytest.raises(MoshPitRejected, match="snapshot_bounds_exceeded"):
        project([crumb()] * 501)


def test_html_escapes_untrusted_content_and_preserves_reported_truth():
    result = project([crumb(truth="REPORTED_BY_012", views={"stakeholder": {
        "actor": "0102", "summary": "<script>alert(1)</script>", "details": ['<img src=x onerror="alert(1)">'],
    }})])
    html = render_mosh_pit_html(result)
    assert "<script>" not in html and "<img" not in html
    assert "&lt;script&gt;" in html and "012からの報告" in html


def test_malformed_disclosure_fails_with_bounded_error():
    with pytest.raises(MoshPitRejected, match="invalid_disclosure"):
        project_mosh_pit(replace(REQUEST, disclosure_class=[]), source=None)


def test_wardrobe_loader_discovers_the_registered_prototype():
    from pathlib import Path
    from modules.infrastructure.wre_core.skillz.wre_skills_loader import WRESkillsLoader
    root = Path(__file__).resolve().parents[4]
    loader = WRESkillsLoader(repo_root=root)
    assert "reddog_mosh_pit" in loader.list_skills(promotion_state="prototype")
    assert loader.resolve_skill_file("reddog_mosh_pit").name == "SKILLz.md"
    selected = [s for s in loader.discover_skills(logical_role="researcher") if s.name == "reddog_mosh_pit"]
    assert len(selected) == 1 and selected[0].has_evals
