"""Access-policy receipts for governed Memex projection.

The receipt binds who may project which FoundUp memory scope into HoloIndex
shadow records. It is deterministic, read-only, and carries no private data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from holo_index.query_receipt import digest_json


SCHEMA_VERSION = "holoindex_memex_access_policy_receipt.v1"
POLICY_READY = "MEMEX_ACCESS_POLICY_READY"
POLICY_REJECTED = "MEMEX_ACCESS_POLICY_REJECTED"
VERIFICATION_PASS = "PASS"

ALLOWED_SENSITIVITY_CLASSES = frozenset(
    {
        "public",
        "internal",
        "foundup_private",
        "operator_private",
    }
)
DEFAULT_ALLOWED_SECTIONS = (
    "identity",
    "current_state",
    "roadmap_state",
    "verified_outcome",
)


@dataclass(frozen=True)
class MemexAccessPolicyReceipt:
    schema_version: str
    principal_id: str
    work_order_id: str
    foundup_scope: tuple[str, ...]
    source_scope: str
    sensitivity_classes: tuple[str, ...]
    allowed_record_sections: tuple[str, ...]
    denied_record_sections: tuple[str, ...]
    max_records: int
    issued_at: str
    expires_at: str
    policy_generation_id: str
    verification: str
    revoked: bool = False
    no_memex_write_performed: bool = True
    no_holoindex_write_performed: bool = True
    no_brain_write_performed: bool = True
    no_breadcrumb_write_performed: bool = True
    receipt_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MemexAccessPolicyValidationResult:
    accepted: bool
    status: str
    receipt: MemexAccessPolicyReceipt | None
    rejection_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "receipt": self.receipt.to_dict() if self.receipt else None,
            "rejection_reasons": list(self.rejection_reasons),
        }


def build_memex_access_policy_receipt(
    *,
    principal_id: str,
    work_order_id: str,
    foundup_scope: Sequence[str],
    source_scope: str,
    sensitivity_classes: Sequence[str],
    allowed_record_sections: Sequence[str] = DEFAULT_ALLOWED_SECTIONS,
    denied_record_sections: Sequence[str] = (),
    max_records: int = 32,
    issued_at: str,
    expires_at: str,
    policy_generation_id: str,
) -> MemexAccessPolicyValidationResult:
    """Build and validate a deterministic access-policy receipt."""

    payload = {
        "schema_version": SCHEMA_VERSION,
        "principal_id": _clean(principal_id),
        "work_order_id": _clean(work_order_id),
        "foundup_scope": tuple(_unique_clean(foundup_scope)),
        "source_scope": _clean(source_scope),
        "sensitivity_classes": tuple(_unique_clean(sensitivity_classes)),
        "allowed_record_sections": tuple(_unique_clean(allowed_record_sections)),
        "denied_record_sections": tuple(_unique_clean(denied_record_sections)),
        "max_records": int(max_records or 0),
        "issued_at": _clean(issued_at),
        "expires_at": _clean(expires_at),
        "policy_generation_id": _clean(policy_generation_id),
        "verification": VERIFICATION_PASS,
        "revoked": False,
        "no_memex_write_performed": True,
        "no_holoindex_write_performed": True,
        "no_brain_write_performed": True,
        "no_breadcrumb_write_performed": True,
    }
    receipt = MemexAccessPolicyReceipt(**payload, receipt_id=digest_json(payload))
    return validate_memex_access_policy_receipt(receipt, now_iso=issued_at)


def validate_memex_access_policy_receipt(
    receipt: MemexAccessPolicyReceipt | Mapping[str, Any],
    *,
    expected_foundup_id: str | None = None,
    expected_source_scope: str | None = None,
    expected_principal_id: str | None = None,
    expected_work_order_id: str | None = None,
    now_iso: str | None = None,
    seen_receipt_ids: Sequence[str] = (),
    revoked_receipt_ids: Sequence[str] = (),
) -> MemexAccessPolicyValidationResult:
    typed, reasons = _receipt_from_any(receipt)
    if typed is None:
        return _reject(*reasons, "access_policy_receipt_malformed")

    if typed.schema_version != SCHEMA_VERSION:
        reasons.append("schema_version_mismatch")
    if typed.verification != VERIFICATION_PASS:
        reasons.append("verification_not_pass")
    if typed.revoked:
        reasons.append("access_policy_revoked")
    if typed.receipt_id in {_clean(item) for item in seen_receipt_ids if _clean(item)}:
        reasons.append("access_policy_replayed")
    if typed.receipt_id in {_clean(item) for item in revoked_receipt_ids if _clean(item)}:
        reasons.append("access_policy_revoked")
    if not typed.foundup_scope:
        reasons.append("missing_foundup_scope")
    if not typed.source_scope:
        reasons.append("missing_source_scope")
    if not typed.policy_generation_id:
        reasons.append("missing_policy_generation_id")
    if typed.max_records <= 0:
        reasons.append("invalid_max_records")
    if set(typed.sensitivity_classes) - ALLOWED_SENSITIVITY_CLASSES:
        reasons.append("unsupported_sensitivity_class")
    if not typed.allowed_record_sections:
        reasons.append("missing_allowed_record_sections")
    if not (
        typed.no_memex_write_performed
        and typed.no_holoindex_write_performed
        and typed.no_brain_write_performed
        and typed.no_breadcrumb_write_performed
    ):
        reasons.append("side_effect_attestation_missing")
    time_reason = _time_reason(issued_at=typed.issued_at, expires_at=typed.expires_at, now_iso=now_iso)
    if time_reason:
        reasons.append(time_reason)
    if expected_foundup_id and _clean(expected_foundup_id) not in typed.foundup_scope:
        reasons.append("expected_foundup_not_in_scope")
    if expected_source_scope and typed.source_scope != _clean(expected_source_scope):
        reasons.append("expected_source_scope_mismatch")
    if expected_principal_id and typed.principal_id != _clean(expected_principal_id):
        reasons.append("expected_principal_mismatch")
    if expected_work_order_id and typed.work_order_id != _clean(expected_work_order_id):
        reasons.append("expected_work_order_mismatch")

    payload = _receipt_payload(typed)
    if digest_json(payload) != typed.receipt_id:
        reasons.append("access_policy_receipt_id_mismatch")

    if reasons:
        return _reject(*reasons)
    return MemexAccessPolicyValidationResult(
        accepted=True,
        status=POLICY_READY,
        receipt=typed,
        rejection_reasons=(),
    )


def section_allowed_by_policy(section: str, receipt: MemexAccessPolicyReceipt) -> bool:
    """Return whether a projected record section is allowed by the receipt."""

    normalized = _section_base(section)
    allowed = {_section_base(item) for item in receipt.allowed_record_sections}
    denied = {_section_base(item) for item in receipt.denied_record_sections}
    return normalized in allowed and normalized not in denied


def _receipt_payload(receipt: MemexAccessPolicyReceipt) -> dict[str, Any]:
    return {
        "schema_version": receipt.schema_version,
        "principal_id": receipt.principal_id,
        "work_order_id": receipt.work_order_id,
        "foundup_scope": tuple(receipt.foundup_scope),
        "source_scope": receipt.source_scope,
        "sensitivity_classes": tuple(receipt.sensitivity_classes),
        "allowed_record_sections": tuple(receipt.allowed_record_sections),
        "denied_record_sections": tuple(receipt.denied_record_sections),
        "max_records": receipt.max_records,
        "issued_at": receipt.issued_at,
        "expires_at": receipt.expires_at,
        "policy_generation_id": receipt.policy_generation_id,
        "verification": receipt.verification,
        "revoked": receipt.revoked,
        "no_memex_write_performed": receipt.no_memex_write_performed,
        "no_holoindex_write_performed": receipt.no_holoindex_write_performed,
        "no_brain_write_performed": receipt.no_brain_write_performed,
        "no_breadcrumb_write_performed": receipt.no_breadcrumb_write_performed,
    }


def _receipt_from_any(value: MemexAccessPolicyReceipt | Mapping[str, Any]) -> tuple[
    MemexAccessPolicyReceipt | None,
    list[str],
]:
    if isinstance(value, MemexAccessPolicyReceipt):
        return value, []
    if not isinstance(value, Mapping):
        return None, ["access_policy_not_mapping"]
    try:
        receipt = MemexAccessPolicyReceipt(
            schema_version=_clean(value.get("schema_version")),
            principal_id=_clean(value.get("principal_id")),
            work_order_id=_clean(value.get("work_order_id")),
            foundup_scope=tuple(_unique_clean(value.get("foundup_scope") or ())),
            source_scope=_clean(value.get("source_scope")),
            sensitivity_classes=tuple(_unique_clean(value.get("sensitivity_classes") or ())),
            allowed_record_sections=tuple(_unique_clean(value.get("allowed_record_sections") or ())),
            denied_record_sections=tuple(_unique_clean(value.get("denied_record_sections") or ())),
            max_records=int(value.get("max_records") or 0),
            issued_at=_clean(value.get("issued_at")),
            expires_at=_clean(value.get("expires_at")),
            policy_generation_id=_clean(value.get("policy_generation_id")),
            verification=_clean(value.get("verification")),
            revoked=bool(value.get("revoked")),
            no_memex_write_performed=bool(value.get("no_memex_write_performed")),
            no_holoindex_write_performed=bool(value.get("no_holoindex_write_performed")),
            no_brain_write_performed=bool(value.get("no_brain_write_performed")),
            no_breadcrumb_write_performed=bool(value.get("no_breadcrumb_write_performed")),
            receipt_id=_clean(value.get("receipt_id")),
        )
    except Exception:
        return None, ["access_policy_receipt_parse_failed"]
    missing = []
    for key in (
        "schema_version",
        "principal_id",
        "work_order_id",
        "source_scope",
        "issued_at",
        "expires_at",
        "policy_generation_id",
        "verification",
        "receipt_id",
    ):
        if not _clean(getattr(receipt, key)):
            missing.append(f"missing_{key}")
    return receipt, missing


def _time_reason(*, issued_at: str, expires_at: str, now_iso: str | None) -> str:
    try:
        issued = _parse_time(issued_at)
        expires = _parse_time(expires_at)
        now = _parse_time(now_iso) if now_iso else datetime.now(timezone.utc)
    except Exception:
        return "access_policy_time_malformed"
    if expires <= issued:
        return "access_policy_expiry_not_after_issue"
    if now < issued:
        return "access_policy_not_yet_valid"
    if now > expires:
        return "access_policy_expired"
    return ""


def _parse_time(value: str | None) -> datetime:
    text = _clean(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _section_base(value: str) -> str:
    text = _clean(value)
    if text.startswith("verified_outcome"):
        return "verified_outcome"
    return text


def _unique_clean(values: Sequence[Any]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        return (_clean(values),) if _clean(values) else ()
    return tuple(dict.fromkeys(_clean(item) for item in values if _clean(item)))


def _reject(*reasons: str) -> MemexAccessPolicyValidationResult:
    return MemexAccessPolicyValidationResult(
        accepted=False,
        status=POLICY_REJECTED,
        receipt=None,
        rejection_reasons=tuple(dict.fromkeys(reason for reason in reasons if reason)),
    )


def _clean(value: Any) -> str:
    return str(value or "").strip()


__all__ = [
    "DEFAULT_ALLOWED_SECTIONS",
    "MemexAccessPolicyReceipt",
    "MemexAccessPolicyValidationResult",
    "POLICY_READY",
    "POLICY_REJECTED",
    "SCHEMA_VERSION",
    "build_memex_access_policy_receipt",
    "section_allowed_by_policy",
    "validate_memex_access_policy_receipt",
]
