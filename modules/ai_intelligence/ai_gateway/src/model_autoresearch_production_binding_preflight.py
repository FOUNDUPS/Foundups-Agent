"""Deterministic policy and trust preflight for production binding."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Mapping, cast

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
    constant_time_compare,
)

from .model_autoresearch_configured_gateway_evidence import digest_payload
from .model_runtime_binding import ModelRuntimeBindingPolicy
from .model_runtime_binding_input_rehydration import rehydrate_runtime_policy
from .model_signed_evidence import (
    ModelEvidenceKeyResolver,
    ModelEvidenceSignerRole,
    ModelSignedEvidenceReceipt,
    VerifiedModelEvidenceEntry,
    VerifiedModelProductionEvidence,
)


def preflight_preview_evidence(gate: Any, benchmark: Any, promotion: Any) -> Any:
    marker = SimpleNamespace(receipt_id="selection-preview-only:" + gate.receipt_id)
    return VerifiedModelProductionEvidence(
        entries=(
            VerifiedModelEvidenceEntry(
                model_id=gate.candidate_id,
                benchmark_receipt=benchmark,
                promotion_receipt=promotion,
                benchmark_signature_receipt=cast(ModelSignedEvidenceReceipt, marker),
                promotion_signature_receipt=cast(ModelSignedEvidenceReceipt, marker),
            ),
        ),
        signed_evidence_verified=False,
    )


def preflight_promotion_policy_digest(authenticated_promotion: Any, gate: Any) -> str:
    policy_digest = digest_payload([gate.policy.to_dict()])
    if (
        policy_digest
        != authenticated_promotion.authority.request.promotion_policy_digest
    ):
        raise ValueError("single_model_production_policy_authority_mismatch")
    return policy_digest


def preflight_verification_dependencies(
    *,
    evidence_key_resolver: ModelEvidenceKeyResolver,
    evidence_signature_verifier: SignatureVerifier,
) -> None:
    if not callable(getattr(evidence_key_resolver, "resolve", None)):
        raise ValueError("single_model_production_evidence_key_resolver_invalid")
    if not callable(getattr(evidence_signature_verifier, "verify", None)):
        raise ValueError("single_model_production_signature_verifier_invalid")


def preflight_runtime_policy(
    value: Mapping[str, Any] | ModelRuntimeBindingPolicy,
    *,
    gate: Any,
    authority_receipt_id: str,
) -> dict[str, Any]:
    policy = _runtime_policy(value)
    checks = (
        policy.task_family == gate.task_family,
        policy.min_verifier_pass_rate == gate.policy.min_verifier_pass_rate,
        policy.required_task_set_digest == gate.policy.required_task_set_digest,
        policy.required_held_out_split_digest
        == gate.policy.required_held_out_split_digest,
        policy.required_verifier_digest == gate.policy.required_verifier_digest,
        policy.required_panel_topology_digest is None,
        policy.authority_receipt_id == authority_receipt_id,
    )
    if not all(checks):
        raise ValueError("single_model_production_runtime_policy_mismatch")
    return policy.to_dict()


def preflight_trusted_keys(
    value: Mapping[str, Any],
    *,
    key_resolver: ModelEvidenceKeyResolver,
) -> dict[str, Any]:
    keys, revoked = _trusted_key_inputs(value)
    records: list[dict[str, str]] = []
    identities: set[tuple[str, str, str]] = set()
    for item in keys:
        record, identity = _trusted_key_record(item, key_resolver, revoked)
        if identity in identities:
            raise ValueError("single_model_production_trusted_keys_invalid")
        identities.add(identity)
        records.append(record)
    required = {
        ModelEvidenceSignerRole.BENCHMARK_VERIFIER.value,
        ModelEvidenceSignerRole.PROMOTION_AUTHORITY.value,
    }
    if {item[0] for item in identities} != required:
        raise ValueError("single_model_production_trusted_keys_invalid")
    records.sort(key=_record_sort_key)
    return {
        "trusted_public_keys": records,
        "revoked_key_epochs": list(sorted(revoked)),
    }


def _runtime_policy(
    value: Mapping[str, Any] | ModelRuntimeBindingPolicy,
) -> ModelRuntimeBindingPolicy:
    try:
        if type(value) is ModelRuntimeBindingPolicy:
            return value.normalized()
        if isinstance(value, Mapping):
            return rehydrate_runtime_policy(value)
    except Exception:
        pass
    raise ValueError("single_model_production_runtime_policy_invalid")


def _trusted_key_inputs(
    value: Mapping[str, Any],
) -> tuple[tuple[Mapping[str, Any], ...], tuple[str, ...]]:
    if not isinstance(value, Mapping) or set(value) - {
        "trusted_public_keys",
        "revoked_key_epochs",
    }:
        raise ValueError("single_model_production_trusted_keys_invalid")
    keys = value.get("trusted_public_keys")
    revoked_raw = value.get("revoked_key_epochs", ())
    if not isinstance(keys, (list, tuple)) or not keys:
        raise ValueError("single_model_production_trusted_keys_invalid")
    if not isinstance(revoked_raw, (list, tuple)):
        raise ValueError("single_model_production_trusted_keys_invalid")
    revoked = tuple(str(item).strip() for item in revoked_raw)
    if any(not item for item in revoked) or len(revoked) != len(set(revoked)):
        raise ValueError("single_model_production_trusted_keys_invalid")
    if any(not isinstance(item, Mapping) for item in keys):
        raise ValueError("single_model_production_trusted_keys_invalid")
    return tuple(keys), revoked


def _trusted_key_record(
    item: Mapping[str, Any],
    resolver: ModelEvidenceKeyResolver,
    revoked: tuple[str, ...],
) -> tuple[dict[str, str], tuple[str, str, str]]:
    names = {
        "signer_role",
        "signer_key_fingerprint",
        "key_epoch",
        "public_key",
    }
    if set(item) != names:
        raise ValueError("single_model_production_trusted_keys_invalid")
    record = {name: _required(item.get(name)) for name in names}
    identity = (
        record["signer_role"],
        record["signer_key_fingerprint"],
        record["key_epoch"],
    )
    if record["key_epoch"] in set(revoked):
        raise ValueError("single_model_production_trusted_keys_invalid")
    try:
        resolved = resolver.resolve(*identity)
    except Exception:
        resolved = None
    if not resolved or not constant_time_compare(str(resolved), record["public_key"]):
        raise ValueError("single_model_production_trusted_keys_invalid")
    return record, identity


def _record_sort_key(item: Mapping[str, str]) -> tuple[str, str, str]:
    return (
        item["signer_role"],
        item["signer_key_fingerprint"],
        item["key_epoch"],
    )


def _required(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("single_model_production_trusted_keys_invalid")
    return text


__all__ = [
    "preflight_preview_evidence",
    "preflight_promotion_policy_digest",
    "preflight_runtime_policy",
    "preflight_trusted_keys",
    "preflight_verification_dependencies",
]
