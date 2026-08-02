"""Digest-bound runtime freshness and compatibility advisory receipts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence


EVIDENCE_SCHEMA = "reddog_runtime_compatibility_evidence.v1"
RECEIPT_SCHEMA = "reddog_runtime_compatibility_receipt.v1"
REQUIRED_COMPONENTS = (
    "openclaw",
    "hermes",
    "qwen_general",
    "qwen_code",
    "inference_backend",
)
EXPECTED_EVIDENCE_KIND = {
    "openclaw": "UPSTREAM_RELEASE",
    "hermes": "UPSTREAM_RELEASE",
    "qwen_general": "PROMOTED_RUNTIME_BINDING",
    "qwen_code": "PROMOTED_RUNTIME_BINDING",
    "inference_backend": "PROMOTED_RUNTIME_BINDING",
}
MAX_EVIDENCE_TTL_SECONDS = 8 * 24 * 60 * 60
MAX_FUTURE_SKEW_SECONDS = 5 * 60
MAX_REFERENCE_LENGTH = 512


class CompatibilityState(str, Enum):
    CURRENT = "CURRENT"
    DRIFT = "DRIFT"
    NOT_READY = "NOT_READY"


@dataclass(frozen=True)
class ComponentCompatibility:
    component_id: str
    state: str
    installed_ref: str
    expected_ref: str
    evidence_kind: str
    evidence_receipt_id: str
    reason: str


@dataclass(frozen=True)
class RuntimeCompatibilityReceipt:
    schema_version: str
    observed_at_utc: str
    overall_state: str
    source_evidence_digest: str
    components: tuple[ComponentCompatibility, ...]
    reasons: tuple[str, ...]
    no_network_call: bool = True
    no_runtime_mutation: bool = True
    no_model_load: bool = True
    no_route_change: bool = True
    receipt_id: str = field(default="")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_digest(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def build_runtime_compatibility_receipt(
    evidence: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> RuntimeCompatibilityReceipt:
    """Validate cached evidence and produce a non-authoritative advisory receipt."""
    instant = _utc(now or datetime.now(timezone.utc))
    reasons = _validate_envelope(evidence, instant)
    components, component_reasons = _evaluate_components(evidence.get("components"))
    reasons.extend(component_reasons)
    reasons.extend(
        f"component_not_ready:{item.component_id}:{item.reason}"
        for item in components
        if item.state == CompatibilityState.NOT_READY.value
    )
    source_digest = canonical_digest(dict(evidence))
    return _compose_receipt(instant, source_digest, components, reasons)


def build_not_ready_receipt(
    reasons: Sequence[str],
    *,
    now: datetime | None = None,
) -> RuntimeCompatibilityReceipt:
    """Return a receipt for unavailable evidence without inventing component state."""
    instant = _utc(now or datetime.now(timezone.utc))
    normalized = tuple(sorted({str(reason).strip() for reason in reasons if str(reason).strip()}))
    return _compose_receipt(instant, canonical_digest({"unavailable": normalized}), (), list(normalized))


def _validate_envelope(evidence: Mapping[str, Any], now: datetime) -> list[str]:
    reasons: list[str] = []
    if evidence.get("schema_version") != EVIDENCE_SCHEMA:
        reasons.append("evidence_schema_invalid")
    if evidence.get("verification") != "PASS":
        reasons.append("evidence_verification_not_pass")
    receipt_id = evidence.get("evidence_receipt_id")
    if not _is_digest(receipt_id):
        reasons.append("evidence_receipt_id_invalid")
    else:
        unsigned = {key: value for key, value in evidence.items() if key != "evidence_receipt_id"}
        if receipt_id != canonical_digest(unsigned):
            reasons.append("evidence_receipt_id_mismatch")
    expires = _parse_timestamp(evidence.get("expires_at_utc"))
    generated = _parse_timestamp(evidence.get("generated_at_utc"))
    if generated is None or expires is None:
        reasons.append("evidence_freshness_invalid")
    else:
        lifetime = (expires - generated).total_seconds()
        future_skew = (generated - now).total_seconds()
        if expires <= generated or now > expires:
            reasons.append("evidence_expired")
        if lifetime > MAX_EVIDENCE_TTL_SECONDS:
            reasons.append("evidence_ttl_exceeds_policy")
        if future_skew > MAX_FUTURE_SKEW_SECONDS:
            reasons.append("evidence_generated_in_future")
    return reasons


def _evaluate_components(raw_components: Any) -> tuple[tuple[ComponentCompatibility, ...], list[str]]:
    if not isinstance(raw_components, list):
        return (), ["components_invalid"]
    by_id: dict[str, Mapping[str, Any]] = {}
    reasons: list[str] = []
    for raw in raw_components:
        if not isinstance(raw, Mapping):
            reasons.append("component_invalid")
            continue
        component_id = str(raw.get("component_id", "")).strip()
        if component_id in by_id:
            reasons.append(f"component_duplicate:{component_id}")
            continue
        by_id[component_id] = raw
    results = tuple(_evaluate_component(component_id, by_id.get(component_id)) for component_id in REQUIRED_COMPONENTS)
    if set(by_id) - set(REQUIRED_COMPONENTS):
        reasons.append("component_set_not_allowlisted")
    return results, reasons


def _evaluate_component(component_id: str, raw: Mapping[str, Any] | None) -> ComponentCompatibility:
    if raw is None:
        return ComponentCompatibility(component_id, CompatibilityState.NOT_READY.value, "", "", "", "", "component_missing")
    installed = str(raw.get("installed_ref", "")).strip()
    expected = str(raw.get("expected_ref", "")).strip()
    kind = str(raw.get("evidence_kind", "")).strip()
    receipt_id = str(raw.get("evidence_receipt_id", "")).strip()
    verified = raw.get("verification") == "PASS"
    references_valid = _is_reference(installed) and _is_reference(expected)
    kind_valid = kind == EXPECTED_EVIDENCE_KIND[component_id]
    if not references_valid or not kind_valid or not _is_digest(receipt_id) or not verified:
        state, reason = CompatibilityState.NOT_READY.value, "component_evidence_invalid"
    elif installed == expected:
        state, reason = CompatibilityState.CURRENT.value, "installed_matches_expected"
    else:
        state, reason = CompatibilityState.DRIFT.value, "installed_differs_from_expected"
    return ComponentCompatibility(component_id, state, installed, expected, kind, receipt_id, reason)


def _compose_receipt(
    instant: datetime,
    source_digest: str,
    components: tuple[ComponentCompatibility, ...],
    reasons: list[str],
) -> RuntimeCompatibilityReceipt:
    component_states = {item.state for item in components}
    if reasons or CompatibilityState.NOT_READY.value in component_states or not components:
        overall = CompatibilityState.NOT_READY.value
    elif CompatibilityState.DRIFT.value in component_states:
        overall = CompatibilityState.DRIFT.value
    else:
        overall = CompatibilityState.CURRENT.value
    normalized = tuple(sorted(set(reasons)))
    payload = {
        "schema_version": RECEIPT_SCHEMA,
        "observed_at_utc": instant.isoformat(),
        "overall_state": overall,
        "source_evidence_digest": source_digest,
        "components": [asdict(item) for item in components],
        "reasons": normalized,
        "no_network_call": True,
        "no_runtime_mutation": True,
        "no_model_load": True,
        "no_route_change": True,
    }
    return RuntimeCompatibilityReceipt(
        schema_version=RECEIPT_SCHEMA,
        observed_at_utc=instant.isoformat(),
        overall_state=overall,
        source_evidence_digest=source_digest,
        components=components,
        reasons=normalized,
        receipt_id=canonical_digest(payload),
    )


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return _utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return None


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_digest(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(char in "0123456789abcdef" for char in text[7:])


def _is_reference(value: str) -> bool:
    return bool(value) and len(value) <= MAX_REFERENCE_LENGTH and value.isascii() and value.isprintable()


__all__ = [
    "CompatibilityState",
    "ComponentCompatibility",
    "EVIDENCE_SCHEMA",
    "EXPECTED_EVIDENCE_KIND",
    "MAX_EVIDENCE_TTL_SECONDS",
    "MAX_FUTURE_SKEW_SECONDS",
    "MAX_REFERENCE_LENGTH",
    "RECEIPT_SCHEMA",
    "REQUIRED_COMPONENTS",
    "RuntimeCompatibilityReceipt",
    "build_not_ready_receipt",
    "build_runtime_compatibility_receipt",
    "canonical_digest",
]
