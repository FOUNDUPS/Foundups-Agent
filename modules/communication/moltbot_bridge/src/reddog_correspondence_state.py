"""Red Dog correspondence continuity state.

This module persists compact machine-readable correspondence state without
turning provider mailboxes or Google projections into the memory substrate.

Truth boundaries:
- Provider systems remain authoritative for whether a message actually exists,
  was sent, or was received.
- Correspondence state is a rebuildable continuity projection and never grants
  send authority.
- Raw message bodies, recipient address dumps, credentials, and hidden model
  reasoning are intentionally outside this store.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Iterable, Mapping, Sequence

from modules.infrastructure.database.src.module_db import ModuleDB


SCHEMA_VERSION = "reddog_correspondence_state.v1"
_SCOPE_PART_RE = re.compile(r"[^A-Z0-9._-]+")


class AskStatus(str, Enum):
    NOT_YET_ASKED = "NOT_YET_ASKED"
    OPEN = "OPEN"
    WAITING_PROVIDER = "WAITING_PROVIDER"
    FORMAL_ROUTE_REQUIRED = "FORMAL_ROUTE_REQUIRED"
    ANSWERED = "ANSWERED"
    SUPERSEDED = "SUPERSEDED"
    CLOSED = "CLOSED"


class SentCoverageState(str, Enum):
    SAME_MESSAGE_SENT = "SAME_MESSAGE_SENT"
    EARLIER_SENT_NEW_DRAFT = "EARLIER_SENT_NEW_DRAFT"
    PARTIAL_RECIPIENT_COVERAGE = "PARTIAL_RECIPIENT_COVERAGE"
    NO_SENT_MATCH_IN_CHECKED_SCOPE = "NO_SENT_MATCH_IN_CHECKED_SCOPE"
    UNKNOWN = "UNKNOWN"


class FollowUpGate(str, Enum):
    CLEAR = "CLEAR"
    WAIT = "WAIT"
    ESCALATE = "ESCALATE"
    BLOCK_DUPLICATE = "BLOCK_DUPLICATE"
    BLOCK_THIRD_FOLLOWUP = "BLOCK_THIRD_FOLLOWUP"
    UNKNOWN = "UNKNOWN"


class Freshness(str, Enum):
    VALID = "VALID"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class AskRecord:
    ask_id: str
    status: AskStatus
    summary_code: str = ""


@dataclass(frozen=True)
class CorrespondenceEvent:
    provider: str
    account_key: str
    message_id: str
    thread_id: str
    scope_key: str
    direction: str
    occurred_at: str
    event_type: str
    subject_digest: str = ""
    content_digest: str = ""
    reply_to_message_id: str = ""
    provider_status: str = ""

    @property
    def event_key(self) -> str:
        material = f"{self.provider}\x1f{self.account_key}\x1f{self.message_id}"
        return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CorrespondenceState:
    scope_key: str
    procedure_lane: str = ""
    active_thread_ids: tuple[str, ...] = ()
    latest_inbound_mid: str = ""
    latest_inbound_at: str = ""
    latest_outbound_mid: str = ""
    latest_outbound_at: str = ""
    outbound_since_latest_inbound: int = 0
    asks: tuple[AskRecord, ...] = ()
    new_delta_ask_ids: tuple[str, ...] = ()
    sent_coverage_state: SentCoverageState = SentCoverageState.UNKNOWN
    routing_state: str = ""
    follow_up_gate: FollowUpGate = FollowUpGate.UNKNOWN
    procedure_state: str = ""
    deadline_clock: str = ""
    next_expected_event: str = ""
    next_allowed_action: str = "HOLD / RECONCILE"
    provider_watermark: str = ""
    reconciled_at: str = ""
    freshness: Freshness = Freshness.UNKNOWN
    schema_version: str = SCHEMA_VERSION

    def ask_ids(self, *statuses: AskStatus) -> tuple[str, ...]:
        allowed = set(statuses)
        return tuple(ask.ask_id for ask in self.asks if ask.status in allowed)


def build_scope_key(*parts: str) -> str:
    """Return a deterministic privacy-bounded scope key."""
    normalized: list[str] = []
    for part in parts:
        token = _SCOPE_PART_RE.sub("_", str(part).strip().upper()).strip("_")
        if not token:
            raise ValueError("scope key parts must be non-empty")
        normalized.append(token)
    if not normalized:
        raise ValueError("at least one scope key part is required")
    return "::".join(normalized)


def _canonical_json(value: Mapping[str, object]) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def state_payload(state: CorrespondenceState) -> dict:
    payload = asdict(state)
    payload["asks"] = [
        {
            "ask_id": ask.ask_id,
            "status": ask.status.value,
            "summary_code": ask.summary_code,
        }
        for ask in state.asks
    ]
    payload["sent_coverage_state"] = state.sent_coverage_state.value
    payload["follow_up_gate"] = state.follow_up_gate.value
    payload["freshness"] = state.freshness.value
    return payload


def state_digest(state: CorrespondenceState) -> str:
    return "sha256:" + hashlib.sha256(
        _canonical_json(state_payload(state)).encode("utf-8")
    ).hexdigest()


def _state_from_payload(payload: Mapping[str, object]) -> CorrespondenceState:
    asks = tuple(
        AskRecord(
            ask_id=str(item["ask_id"]),
            status=AskStatus(str(item["status"])),
            summary_code=str(item.get("summary_code", "")),
        )
        for item in payload.get("asks", [])
    )
    return CorrespondenceState(
        scope_key=str(payload["scope_key"]),
        procedure_lane=str(payload.get("procedure_lane", "")),
        active_thread_ids=tuple(str(v) for v in payload.get("active_thread_ids", [])),
        latest_inbound_mid=str(payload.get("latest_inbound_mid", "")),
        latest_inbound_at=str(payload.get("latest_inbound_at", "")),
        latest_outbound_mid=str(payload.get("latest_outbound_mid", "")),
        latest_outbound_at=str(payload.get("latest_outbound_at", "")),
        outbound_since_latest_inbound=int(payload.get("outbound_since_latest_inbound", 0)),
        asks=asks,
        new_delta_ask_ids=tuple(str(v) for v in payload.get("new_delta_ask_ids", [])),
        sent_coverage_state=SentCoverageState(
            str(payload.get("sent_coverage_state", SentCoverageState.UNKNOWN.value))
        ),
        routing_state=str(payload.get("routing_state", "")),
        follow_up_gate=FollowUpGate(
            str(payload.get("follow_up_gate", FollowUpGate.UNKNOWN.value))
        ),
        procedure_state=str(payload.get("procedure_state", "")),
        deadline_clock=str(payload.get("deadline_clock", "")),
        next_expected_event=str(payload.get("next_expected_event", "")),
        next_allowed_action=str(payload.get("next_allowed_action", "HOLD / RECONCILE")),
        provider_watermark=str(payload.get("provider_watermark", "")),
        reconciled_at=str(payload.get("reconciled_at", "")),
        freshness=Freshness(str(payload.get("freshness", Freshness.UNKNOWN.value))),
        schema_version=str(payload.get("schema_version", SCHEMA_VERSION)),
    )


def _validate_state(state: CorrespondenceState) -> None:
    if not state.scope_key:
        raise ValueError("scope_key is required")
    if state.schema_version != SCHEMA_VERSION:
        raise ValueError("unsupported correspondence state schema")
    if state.outbound_since_latest_inbound < 0:
        raise ValueError("outbound_since_latest_inbound must be >= 0")
    ask_ids = [ask.ask_id for ask in state.asks]
    if len(ask_ids) != len(set(ask_ids)):
        raise ValueError("ask_id values must be unique within a scope")
    if not set(state.new_delta_ask_ids).issubset(set(ask_ids)):
        raise ValueError("new_delta_ask_ids must refer to declared asks")


def _validate_event(event: CorrespondenceEvent) -> None:
    required = (
        event.provider,
        event.account_key,
        event.message_id,
        event.thread_id,
        event.scope_key,
        event.direction,
        event.occurred_at,
        event.event_type,
    )
    if not all(str(value).strip() for value in required):
        raise ValueError("correspondence event required fields must be non-empty")


class RedDogCorrespondenceStateStore(ModuleDB):
    """Module-owned durable correspondence continuity projection."""

    def __init__(self) -> None:
        super().__init__("reddog_correspondence")

    def _init_tables(self) -> None:
        self.create_table(
            "events",
            """
            event_key TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            account_key TEXT NOT NULL,
            message_id TEXT NOT NULL,
            thread_id TEXT NOT NULL,
            scope_key TEXT NOT NULL,
            direction TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            event_type TEXT NOT NULL,
            subject_digest TEXT,
            content_digest TEXT,
            reply_to_message_id TEXT,
            provider_status TEXT
            """,
        )
        self.create_table(
            "state",
            """
            scope_key TEXT PRIMARY KEY,
            state_json TEXT NOT NULL,
            state_digest TEXT NOT NULL,
            provider_watermark TEXT,
            reconciled_at TEXT,
            freshness TEXT NOT NULL,
            schema_version TEXT NOT NULL
            """,
        )

    def record_event(self, event: CorrespondenceEvent) -> bool:
        """Persist one normalized provider event idempotently."""
        _validate_event(event)
        existing = self.select("events", "event_key = ?", (event.event_key,), limit=1)
        if existing:
            return False
        self.insert(
            "events",
            {
                "event_key": event.event_key,
                "provider": event.provider,
                "account_key": event.account_key,
                "message_id": event.message_id,
                "thread_id": event.thread_id,
                "scope_key": event.scope_key,
                "direction": event.direction,
                "occurred_at": event.occurred_at,
                "event_type": event.event_type,
                "subject_digest": event.subject_digest,
                "content_digest": event.content_digest,
                "reply_to_message_id": event.reply_to_message_id,
                "provider_status": event.provider_status,
            },
        )
        return True

    def list_events(self, scope_key: str, limit: int = 100) -> list[dict]:
        return self.select(
            "events",
            "scope_key = ?",
            (scope_key,),
            order_by="occurred_at ASC",
            limit=limit,
        )

    def upsert_state(self, state: CorrespondenceState) -> str:
        """Persist a materialized scope state and return its digest."""
        _validate_state(state)
        digest = state_digest(state)
        payload = _canonical_json(state_payload(state))
        record = {
            "scope_key": state.scope_key,
            "state_json": payload,
            "state_digest": digest,
            "provider_watermark": state.provider_watermark,
            "reconciled_at": state.reconciled_at,
            "freshness": state.freshness.value,
            "schema_version": state.schema_version,
        }
        existing = self.select("state", "scope_key = ?", (state.scope_key,), limit=1)
        if existing:
            self.update(
                "state",
                {k: v for k, v in record.items() if k != "scope_key"},
                "scope_key = ?",
                (state.scope_key,),
            )
        else:
            self.insert("state", record)
        return digest

    def load_state(self, scope_key: str) -> CorrespondenceState | None:
        rows = self.select("state", "scope_key = ?", (scope_key,), limit=1)
        if not rows:
            return None
        row = rows[0]
        payload = json.loads(row["state_json"])
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported correspondence state schema")
        state = _state_from_payload(payload)
        _validate_state(state)
        if state.scope_key != scope_key:
            raise ValueError("correspondence state scope mismatch")
        if state_digest(state) != row["state_digest"]:
            raise ValueError("correspondence state digest mismatch")
        return state

    def provider_refresh_required(self, scope_key: str, observed_watermark: str) -> bool:
        """Require VALID state and exact, nonempty string watermark evidence."""
        state = self.load_state(scope_key)
        if state is None:
            return True
        if state.freshness is not Freshness.VALID:
            return True
        if not isinstance(observed_watermark, str) or not observed_watermark:
            return True
        if not state.provider_watermark:
            return True
        return state.provider_watermark != observed_watermark


def summarize_ask_state(
    asks: Iterable[AskRecord],
) -> dict[str, tuple[str, ...]]:
    records = tuple(asks)
    return {
        "open": tuple(
            ask.ask_id
            for ask in records
            if ask.status
            in {
                AskStatus.NOT_YET_ASKED,
                AskStatus.OPEN,
                AskStatus.WAITING_PROVIDER,
                AskStatus.FORMAL_ROUTE_REQUIRED,
            }
        ),
        "answered": tuple(
            ask.ask_id for ask in records if ask.status is AskStatus.ANSWERED
        ),
        "closed": tuple(
            ask.ask_id
            for ask in records
            if ask.status in {AskStatus.CLOSED, AskStatus.SUPERSEDED}
        ),
    }
