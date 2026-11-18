"""Integrity-bound lease contract for one HoloIndex post-merge claim."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping


CLAIM_BINDING_SCHEMA = "holoindex_postmerge_claim_binding.v2"
MAX_POSTMERGE_CLAIM_LEASE_SECONDS = 7500
_CLAIM_RE = re.compile(r"^hpmc_[0-9a-f]{32}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def begin_holoindex_postmerge_write_fence(
    database: Any, connection: Any,
) -> str:
    """Acquire the backend write fence before evaluating a claim clock."""

    info = database.backend_info()
    engine = info.get("engine") if isinstance(info, Mapping) else None
    if engine == "sqlite":
        connection.execute("BEGIN IMMEDIATE")
        return ""
    if engine == "postgres":
        return " FOR UPDATE"
    raise RuntimeError("holoindex_postmerge_claim_backend_unsupported")


def _canonical_utc(value: Any) -> tuple[str, datetime] | None:
    raw = str(value or "")
    try:
        parsed = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    normalized = parsed.astimezone(timezone.utc)
    canonical = normalized.isoformat()
    return (canonical, normalized) if raw == canonical else None


def holoindex_postmerge_claim_binding_digest(
    *, task_id: str, agent_id: str, context: Mapping[str, Any],
) -> str:
    """Bind the exact claim identity, time window, and task context."""

    bound_context = {
        str(key): value
        for key, value in context.items()
        if key != "claim_binding_digest"
    }
    payload = {
        "schema_version": CLAIM_BINDING_SCHEMA,
        "task_id": task_id,
        "agent_id": agent_id,
        "context": bound_context,
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def build_holoindex_postmerge_claim_context(
    *, task_id: str, agent_id: str, base_context: Mapping[str, Any],
    claim_id: str, issued_at: datetime, lease_seconds: int,
) -> dict[str, Any] | None:
    """Create one canonical v2 claim context before the assignment CAS."""

    if (
        type(lease_seconds) is not int
        or not 1 <= lease_seconds <= MAX_POSTMERGE_CLAIM_LEASE_SECONDS
        or _CLAIM_RE.fullmatch(claim_id) is None
        or issued_at.tzinfo is None
    ):
        return None
    issued = issued_at.astimezone(timezone.utc)
    context = dict(base_context)
    context.update(
        {
            "claim_binding_schema": CLAIM_BINDING_SCHEMA,
            "claim_id": claim_id,
            "claim_issued_at": issued.isoformat(),
            "claim_expires_at": (
                issued + timedelta(seconds=lease_seconds)
            ).isoformat(),
        }
    )
    try:
        context["claim_binding_digest"] = (
            holoindex_postmerge_claim_binding_digest(
                task_id=task_id, agent_id=agent_id, context=context,
            )
        )
    except (TypeError, ValueError):
        return None
    return context


def holoindex_postmerge_claim_binding_valid(
    *, task_id: str, agent_id: str, assigned_at: Any,
    context: Mapping[str, Any], expected_claim_id: str = "",
    expected_digest: str = "", now: datetime | None = None,
    require_active: bool = False, require_expired: bool = False,
) -> bool:
    """Validate one exact v2 claim and optionally its current lease state."""

    if require_active and require_expired:
        return False
    claim_id = str(context.get("claim_id") or "")
    digest = str(context.get("claim_binding_digest") or "")
    issued = _canonical_utc(context.get("claim_issued_at"))
    expires = _canonical_utc(context.get("claim_expires_at"))
    if (
        context.get("claim_binding_schema") != CLAIM_BINDING_SCHEMA
        or _CLAIM_RE.fullmatch(claim_id) is None
        or _DIGEST_RE.fullmatch(digest) is None
        or issued is None
        or expires is None
        or str(assigned_at or "") != issued[0]
        or (expected_claim_id and claim_id != expected_claim_id)
        or (expected_digest and digest != expected_digest)
    ):
        return False
    duration = (expires[1] - issued[1]).total_seconds()
    if not 1 <= duration <= MAX_POSTMERGE_CLAIM_LEASE_SECONDS:
        return False
    try:
        recomputed = holoindex_postmerge_claim_binding_digest(
            task_id=task_id, agent_id=agent_id, context=context,
        )
    except (TypeError, ValueError):
        return False
    if not hmac.compare_digest(recomputed, digest):
        return False
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if require_active:
        return current < expires[1]
    if require_expired:
        return current >= expires[1]
    return True


def holoindex_postmerge_claim_completed_in_lease(
    context: Mapping[str, Any], completed_at: Any,
) -> bool:
    """Prove an already committed terminal transition preceded expiry."""

    completed = _canonical_utc(completed_at)
    expires = _canonical_utc(context.get("claim_expires_at"))
    return bool(completed and expires and completed[1] < expires[1])


def holoindex_postmerge_completed_replay_valid(
    *, task_id: str, agent_id: str, task: Mapping[str, Any],
    context: Mapping[str, Any], request: Mapping[str, Any] | None,
    existing_payload_raw: Any, completion_payload: Mapping[str, Any],
    claim_id: str, claim_binding_digest: str,
) -> bool:
    """Validate an exact already-committed replay, including lease timing."""

    try:
        existing_payload = json.loads(str(existing_payload_raw or ""))
    except (TypeError, ValueError):
        return False
    return bool(
        task.get("status") == "completed"
        and task.get("assigned_to") == agent_id
        and holoindex_postmerge_claim_binding_valid(
            task_id=task_id,
            agent_id=agent_id,
            assigned_at=task.get("assigned_at"),
            context=context,
            expected_claim_id=claim_id,
            expected_digest=claim_binding_digest,
        )
        and holoindex_postmerge_claim_completed_in_lease(
            context, task.get("completed_at")
        )
        and isinstance(request, Mapping)
        and request.get("resolution_status") == "completed"
        and existing_payload == completion_payload
    )


__all__ = [
    "CLAIM_BINDING_SCHEMA",
    "MAX_POSTMERGE_CLAIM_LEASE_SECONDS",
    "begin_holoindex_postmerge_write_fence",
    "build_holoindex_postmerge_claim_context",
    "holoindex_postmerge_claim_binding_digest",
    "holoindex_postmerge_claim_binding_valid",
    "holoindex_postmerge_claim_completed_in_lease",
    "holoindex_postmerge_completed_replay_valid",
]
