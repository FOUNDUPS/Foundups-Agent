"""Canonical signed-worker assurance-completion request contract."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping


ASSURANCE_COMPLETION_SCHEMA_VERSION = (
    "reddog_signed_worker_assurance_completion.v1"
)
ASSURANCE_COMPLETION_KEYS = {
    "schema_version",
    "reservation_id",
    "admission_reservation_digest",
    "verifier_task_id",
    "verifier_principal_id",
    "terminal_receipt_id",
    "terminal_receipt_digest",
    "terminal_status",
    "completed_at",
}
ASSURANCE_TERMINAL_STATUSES = {
    "ACCEPT",
    "REJECT",
    "VERIFIED",
    "FAILED",
    "CANCELLED",
}


def build_assurance_completion_request(
    *,
    reservation: Mapping[str, Any],
    terminal_receipt: Mapping[str, Any],
    terminal_status: str,
    completed_at: str,
) -> dict[str, str]:
    """Build the exact request later revalidated against durable authority."""

    return {
        "schema_version": ASSURANCE_COMPLETION_SCHEMA_VERSION,
        "reservation_id": str(reservation.get("reservation_id") or ""),
        "admission_reservation_digest": str(
            reservation.get("admission_reservation_digest")
            or reservation.get("reservation_digest")
            or ""
        ),
        "verifier_task_id": str(reservation.get("verifier_task_id") or ""),
        "verifier_principal_id": str(
            reservation.get("verifier_principal_id") or ""
        ),
        "terminal_receipt_id": str(terminal_receipt.get("receipt_id") or ""),
        "terminal_receipt_digest": str(
            terminal_receipt.get("receipt_digest") or ""
        ),
        "terminal_status": str(terminal_status or "").upper(),
        "completed_at": str(completed_at or ""),
    }


def validated_assurance_completion_request(
    request: Mapping[str, Any],
    *,
    task_id: str | None = None,
    assigned_to: str | None = None,
) -> dict[str, str] | None:
    """Return one exact canonical request or fail closed."""

    if not isinstance(request, Mapping) or set(request) != ASSURANCE_COMPLETION_KEYS:
        return None
    normalized = {
        key: str(request.get(key) or "") for key in ASSURANCE_COMPLETION_KEYS
    }
    if (
        normalized["schema_version"] != ASSURANCE_COMPLETION_SCHEMA_VERSION
        or normalized["terminal_status"] not in ASSURANCE_TERMINAL_STATUSES
        or not normalized["reservation_id"]
        or not normalized["verifier_task_id"]
        or not normalized["verifier_principal_id"]
        or not normalized["terminal_receipt_id"]
        or not is_digest(normalized["admission_reservation_digest"])
        or not is_digest(normalized["terminal_receipt_digest"])
        or parse_utc(normalized["completed_at"]) is None
        or (task_id is not None and normalized["verifier_task_id"] != task_id)
        or (
            assigned_to is not None
            and normalized["verifier_principal_id"] != assigned_to
        )
    ):
        return None
    return normalized


def canonical_request_json(request: Mapping[str, str]) -> str:
    return json.dumps(
        dict(request),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def canonical_request_digest(request: Mapping[str, str]) -> str:
    raw = canonical_request_json(request).encode("ascii")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def parse_utc(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def is_digest(value: Any) -> bool:
    text = str(value or "").removeprefix("sha256:")
    return len(text) == 64 and all(char in "0123456789abcdef" for char in text)


__all__ = [
    "ASSURANCE_COMPLETION_SCHEMA_VERSION",
    "build_assurance_completion_request",
    "canonical_request_digest",
    "canonical_request_json",
    "parse_utc",
    "validated_assurance_completion_request",
]
