"""Read-only Moshpit candidate over authorized AgentDB breadcrumb snapshots.

The injected source is a TRUSTED HOST interface, never a client-supplied object.
It must authenticate, authorize project membership/disclosure, check revocation,
and bind the snapshot before returning data. No production source is wired yet.
This module does not mint capabilities, open AgentDB, persist or publish data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Mapping, Protocol, Sequence
from zoneinfo import ZoneInfo


ACTIVITY_KINDS = frozenset({
    "meeting", "action", "decision", "research", "artifact", "response", "milestone",
})
DISCLOSURES = frozenset({"principal_private", "team_pc", "stakeholder", "public"})
TRUTHS = frozenset({"OBSERVED", "REPORTED_BY_012", "INFERRED", "PROPOSED"})
MAX_RECORDS = 500


class MoshpitRejected(ValueError):
    """A bounded, payload-free failure suitable for the host to handle."""


@dataclass(frozen=True)
class MoshpitRequest:
    principal_id: str
    foundup_id: str
    disclosure_class: str
    snapshot_id: str
    timezone: str = "Asia/Tokyo"
    limit: int = 50


@dataclass(frozen=True)
class AuthorizedActivitySnapshot:
    """Host response; constructing this dataclass is NOT authentication."""

    principal_id: str
    foundup_id: str
    disclosure_class: str
    snapshot_id: str
    expires_at: datetime
    breadcrumbs: Sequence[Mapping[str, Any]]


class AuthorizedActivitySource(Protocol):
    def read_authorized_activity(
        self, request: MoshpitRequest, capability: object,
    ) -> AuthorizedActivitySnapshot:
        """Verify session, membership, revocation, disclosure and snapshot.

        Deny before reading source data. Curate each disclosure view independently;
        private summary/details are never fallback text for another audience.
        Return at most MAX_RECORDS rows. A production host must supply this method.
        """
        ...


def _text(value: Any, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise MoshpitRejected("invalid_activity_text")
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise MoshpitRejected("invalid_activity_text")
    return value.strip()


def _event_time(value: Any, tz: ZoneInfo) -> tuple[str, str]:
    # Unknown and date-only evidence must not acquire invented clock precision.
    if value is None:
        return "", ""
    if not isinstance(value, str):
        raise MoshpitRejected("invalid_event_time")
    try:
        if len(value) == 10:
            day = date.fromisoformat(value).isoformat()
            return day, ""
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError("timezone required")
        return stamp.astimezone(tz).date().isoformat(), stamp.astimezone(timezone.utc).isoformat()
    except (ValueError, OverflowError):
        raise MoshpitRejected("invalid_event_time") from None


def _aware_datetime(value: Any, error: str) -> datetime:
    try:
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("aware datetime required")
    except (TypeError, ValueError, OverflowError):
        raise MoshpitRejected(error) from None
    return value


def _clock(now: datetime | None) -> datetime:
    return _aware_datetime(now if now is not None else datetime.now(timezone.utc), "invalid_clock")


def _request_timezone(request: MoshpitRequest, now: datetime | None) -> ZoneInfo:
    if type(request) is not MoshpitRequest:
        raise MoshpitRejected("invalid_request")
    for value in (request.principal_id, request.foundup_id, request.snapshot_id):
        _text(value, 200)
    if not isinstance(request.disclosure_class, str) or request.disclosure_class not in DISCLOSURES:
        raise MoshpitRejected("invalid_disclosure")
    if type(request.limit) is not int or not 1 <= request.limit <= 100:
        raise MoshpitRejected("invalid_limit")
    try:
        tz = ZoneInfo(request.timezone)
    except (ValueError, KeyError, TypeError):
        raise MoshpitRejected("invalid_timezone") from None
    if now is not None:
        _clock(now)
    return tz


def _assert_fresh(batch: AuthorizedActivitySnapshot, now: datetime | None) -> None:
    expiry = _aware_datetime(batch.expires_at, "snapshot_expired")
    if expiry <= _clock(now):
        raise MoshpitRejected("snapshot_expired")


def _read_snapshot(request, source, capability, now) -> AuthorizedActivitySnapshot:
    if source is None or capability is None:
        raise MoshpitRejected("authorization_required")
    try:
        batch = source.read_authorized_activity(request, capability)
    except Exception:
        raise MoshpitRejected("authorization_or_source_unavailable") from None
    if type(batch) is not AuthorizedActivitySnapshot:
        raise MoshpitRejected("invalid_authorized_snapshot")
    for field in ("principal_id", "foundup_id", "disclosure_class", "snapshot_id"):
        if getattr(batch, field) != getattr(request, field):
            raise MoshpitRejected("snapshot_scope_mismatch")
    _assert_fresh(batch, now)
    if not isinstance(batch.breadcrumbs, (list, tuple)) or len(batch.breadcrumbs) > MAX_RECORDS:
        raise MoshpitRejected("snapshot_bounds_exceeded")
    return batch


def _visible_event(row: Mapping[str, Any], request: MoshpitRequest):
    if not isinstance(row, Mapping):
        raise MoshpitRejected("invalid_breadcrumb")
    data = row.get("data")
    if not isinstance(data, Mapping) or "moshpit" not in data:
        return None
    event = data["moshpit"]
    if not isinstance(event, Mapping):
        raise MoshpitRejected("invalid_activity")
    if (event.get("principal_id"), event.get("foundup_id")) != (
        request.principal_id, request.foundup_id,
    ):
        raise MoshpitRejected("event_scope_mismatch")
    kind, truth = event.get("kind"), event.get("truth")
    if not isinstance(kind, str) or not isinstance(truth, str):
        raise MoshpitRejected("invalid_classification")
    if kind not in ACTIVITY_KINDS | {"discussion"} or truth not in TRUTHS:
        return None
    if kind != "discussion" and truth not in {"OBSERVED", "REPORTED_BY_012"}:
        return None
    views = event.get("views")
    view = views.get(request.disclosure_class) if isinstance(views, Mapping) else None
    return (event, view) if isinstance(view, Mapping) else None


def _record(event: Mapping[str, Any], view: Mapping[str, Any], tz: ZoneInfo):
    # Only curated fields for the selected audience survive. Host curation must
    # exclude private contact information from these strings for every audience.
    details = view.get("details", [])
    if not isinstance(details, (list, tuple)) or len(details) > 12:
        raise MoshpitRejected("invalid_details")
    day, sort_time = _event_time(event.get("event_time"), tz)
    parent = event.get("parent_event_id")
    return {
        "event_id": _text(event.get("event_id"), 200),
        "day": day,
        "sort_time": sort_time,
        "kind": event["kind"],
        "truth": event["truth"],
        "parent_event_id": _text(parent, 200) if parent is not None else None,
        "actor": _text(view.get("actor"), 120),
        "summary": _text(view.get("summary"), 240),
        "details": [_text(item, 2000) for item in details],
    }


def _records(rows, request: MoshpitRequest, tz: ZoneInfo):
    records: dict[str, dict[str, Any]] = {}
    for row in rows:
        visible = _visible_event(row, request)
        if visible is None:
            continue
        record = _record(*visible, tz)
        event_id = record["event_id"]
        if event_id in records and records[event_id] != record:
            raise MoshpitRejected("conflicting_event_identity")
        records[event_id] = record
    return records


def _clean(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: record[key] for key in ("event_id", "actor", "summary", "details", "truth")}


def _days(records: Mapping[str, Any], limit: int):
    roots = [r for r in records.values() if r["kind"] in ACTIVITY_KINDS and r["parent_event_id"] is None]
    # Unknown dates last. Same-day date-only events have stable ID ordering,
    # without pretending their within-day timing is known.
    roots.sort(key=lambda r: (r["day"], r["sort_time"], r["event_id"]), reverse=True)
    days: dict[str, list[dict[str, Any]]] = {}
    for root in roots[:limit]:
        replies = [r for r in records.values() if r["kind"] == "discussion" and r["parent_event_id"] == root["event_id"]]
        replies.sort(key=lambda r: (not bool(r["day"]), r["day"], r["sort_time"], r["event_id"]))
        entry = _clean(root)
        entry["replies"] = [_clean(r) for r in replies[:50]]
        entry["more_replies"] = len(replies) > 50
        days.setdefault(root["day"], []).append(entry)
    return [{"date": day or None, "entries": entries} for day, entries in days.items()], len(roots) > limit


def project_moshpit(
    request: MoshpitRequest,
    *,
    source: AuthorizedActivitySource | None,
    capability: object = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Project host-authorized data.moshpit; no live source or routing is wired.

    Legacy unclassified rows are omitted. ``now`` is a fixed trusted test clock;
    normal calls sample current time after source read and again before return.
    This pure projection neither authenticates the source nor grants authority.
    """
    tz = _request_timezone(request, now)
    batch = _read_snapshot(request, source, capability, now)
    records = _records(batch.breadcrumbs, request, tz)
    days, has_more = _days(records, request.limit)
    _assert_fresh(batch, now)
    return {
        "schema_version": "moshpit_projection.v1",
        "foundup_id": request.foundup_id,
        "disclosure_class": request.disclosure_class,
        "snapshot_id": request.snapshot_id,
        "timezone": request.timezone,
        "days": days,
        "has_more": has_more,
        "read_only": True,
    }
