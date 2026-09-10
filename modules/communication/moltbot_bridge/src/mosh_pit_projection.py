"""Read-only Mosh Pit candidate over authorized AgentDB breadcrumb snapshots.

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


class MoshPitRejected(ValueError):
    """A bounded, payload-free failure suitable for the host to handle."""


@dataclass(frozen=True)
class MoshPitRequest:
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
        self, request: MoshPitRequest, capability: object,
    ) -> AuthorizedActivitySnapshot:
        """Verify session, membership, revocation, disclosure and snapshot.

        Deny before reading source data. Curate each disclosure view independently;
        private summary/details are never fallback text for another audience.
        Return at most MAX_RECORDS rows. A production host must supply this method.
        """
        ...


def _text(value: Any, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise MoshPitRejected("invalid_activity_text")
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise MoshPitRejected("invalid_activity_text")
    return value.strip()


def _event_time(value: Any, tz: ZoneInfo) -> tuple[str, str]:
    # Unknown and date-only evidence must not acquire invented clock precision.
    if value is None:
        return "", ""
    if not isinstance(value, str):
        raise MoshPitRejected("invalid_event_time")
    try:
        if len(value) == 10:
            day = date.fromisoformat(value).isoformat()
            return day, ""
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError("timezone required")
        return stamp.astimezone(tz).date().isoformat(), stamp.astimezone(timezone.utc).isoformat()
    except (ValueError, OverflowError):
        raise MoshPitRejected("invalid_event_time") from None


def project_mosh_pit(
    request: MoshPitRequest,
    *,
    source: AuthorizedActivitySource | None,
    capability: object = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return newest-first activity days, each with expandable details/replies.

    Existing breadcrumbs carry the optional normalized contract in
    data.mosh_pit. Legacy unclassified breadcrumbs are omitted, not guessed.
    No routes or unrestricted legacy query functions call this candidate.
    """
    if type(request) is not MoshPitRequest:
        raise MoshPitRejected("invalid_request")
    for value in (request.principal_id, request.foundup_id, request.snapshot_id):
        _text(value, 200)
    if not isinstance(request.disclosure_class, str) or request.disclosure_class not in DISCLOSURES:
        raise MoshPitRejected("invalid_disclosure")
    if type(request.limit) is not int or not 1 <= request.limit <= 100:
        raise MoshPitRejected("invalid_limit")
    try:
        tz = ZoneInfo(request.timezone)
    except (ValueError, KeyError, TypeError):
        raise MoshPitRejected("invalid_timezone") from None
    clock = now if now is not None else datetime.now(timezone.utc)
    if not isinstance(clock, datetime) or clock.tzinfo is None:
        raise MoshPitRejected("invalid_clock")
    if source is None or capability is None:
        raise MoshPitRejected("authorization_required")
    try:
        batch = source.read_authorized_activity(request, capability)
    except Exception:
        raise MoshPitRejected("authorization_or_source_unavailable") from None
    if type(batch) is not AuthorizedActivitySnapshot:
        raise MoshPitRejected("invalid_authorized_snapshot")
    for field in ("principal_id", "foundup_id", "disclosure_class", "snapshot_id"):
        if getattr(batch, field) != getattr(request, field):
            raise MoshPitRejected("snapshot_scope_mismatch")
    if (
        not isinstance(batch.expires_at, datetime)
        or batch.expires_at.tzinfo is None
        or batch.expires_at <= clock
    ):
        raise MoshPitRejected("snapshot_expired")
    if not isinstance(batch.breadcrumbs, (list, tuple)) or len(batch.breadcrumbs) > MAX_RECORDS:
        raise MoshPitRejected("snapshot_bounds_exceeded")

    records: dict[str, dict[str, Any]] = {}
    for row in batch.breadcrumbs:
        if not isinstance(row, Mapping):
            raise MoshPitRejected("invalid_breadcrumb")
        data = row.get("data")
        event = data.get("mosh_pit") if isinstance(data, Mapping) else None
        if not isinstance(event, Mapping):
            continue
        if (event.get("principal_id"), event.get("foundup_id")) != (
            request.principal_id, request.foundup_id,
        ):
            raise MoshPitRejected("event_scope_mismatch")
        kind, truth = event.get("kind"), event.get("truth")
        if not isinstance(kind, str) or not isinstance(truth, str):
            raise MoshPitRejected("invalid_classification")
        if kind not in ACTIVITY_KINDS | {"discussion"} or truth not in TRUTHS:
            continue
        if kind != "discussion" and truth not in {"OBSERVED", "REPORTED_BY_012"}:
            continue
        views = event.get("views")
        view = views.get(request.disclosure_class) if isinstance(views, Mapping) else None
        if not isinstance(view, Mapping):
            continue
        # Only this explicit audience's fields survive. Never copy raw row/data,
        # source transcripts, email bodies, contacts or other audience views.
        event_id = _text(event.get("event_id"), 200)
        details = view.get("details", [])
        if not isinstance(details, (list, tuple)) or len(details) > 12:
            raise MoshPitRejected("invalid_details")
        day, sort_time = _event_time(event.get("event_time"), tz)
        parent = event.get("parent_event_id")
        if parent is not None:
            parent = _text(parent, 200)
        record = {
            "event_id": event_id,
            "day": day,
            "sort_time": sort_time,
            "kind": kind,
            "truth": truth,
            "parent_event_id": parent,
            "actor": _text(view.get("actor"), 120),
            "summary": _text(view.get("summary"), 240),
            "details": [_text(item, 2000) for item in details],
        }
        if event_id in records and records[event_id] != record:
            raise MoshPitRejected("conflicting_event_identity")
        records[event_id] = record

    roots = [r for r in records.values() if r["kind"] in ACTIVITY_KINDS and r["parent_event_id"] is None]
    # Unknown dates last. Same-day date-only events have stable ID ordering,
    # without pretending their within-day timing is known.
    roots.sort(key=lambda r: (r["day"], r["sort_time"], r["event_id"]), reverse=True)
    days: dict[str, list[dict[str, Any]]] = {}
    for root in roots[:request.limit]:
        replies = [r for r in records.values() if r["kind"] == "discussion" and r["parent_event_id"] == root["event_id"]]
        replies.sort(key=lambda r: (not bool(r["day"]), r["day"], r["sort_time"], r["event_id"]))
        clean = lambda r: {k: r[k] for k in ("event_id", "actor", "summary", "details", "truth")}
        entry = clean(root)
        entry["replies"] = [clean(r) for r in replies[:50]]
        entry["more_replies"] = len(replies) > 50
        days.setdefault(root["day"], []).append(entry)
    return {
        "schema_version": "mosh_pit_projection.v1",
        "foundup_id": request.foundup_id,
        "disclosure_class": request.disclosure_class,
        "snapshot_id": request.snapshot_id,
        "timezone": request.timezone,
        "days": [{"date": day or None, "entries": entries} for day, entries in days.items()],
        "has_more": len(roots) > request.limit,
        "read_only": True,
    }
