"""Bind resident queue evidence to verified Memex outcome authority."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_publisher import (
    SignedVerifiedOutcomeEvidencePublisher,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_runtime_authority import (
    CommittedAuthorityProfileOutcomeKeyResolver,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_runtime_store import (
    AuthorityRuntimeVerifiedOutcomeStore,
)


def derive_verified_outcome_admission(
    chain_state: Mapping[str, Any],
    work_state_snapshot: Mapping[str, Any],
    now_iso: str,
) -> Mapping[str, Any] | None:
    stages = _mapping(chain_state, "stage_results")
    held_out_stage = _mapping(stages, "held_out_regression_gate")
    gate_result = _mapping(held_out_stage, "gate_result")
    gate_receipt = _mapping(gate_result, "receipt")
    if not _gate_allows_admission(gate_result, gate_receipt):
        return None
    verifier_stage = _mapping(stages, "slice_verifier")
    verifier_result = _mapping(verifier_stage, "verifier_result")
    verifier_receipt = _mapping(verifier_result, "receipt")
    queue_item = _queue_item(
        work_state_snapshot, str(chain_state.get("queue_item_id") or "")
    )
    work_order_id = str(gate_receipt.get("work_order_id") or "")
    if not work_order_id:
        return None
    if not _has_runtime_binding(queue_item):
        return _legacy_admission(gate_receipt, work_order_id)
    if not verifier_receipt or not now_iso:
        return None
    binding = _outcome_binding(queue_item, gate_receipt, verifier_receipt, work_order_id)
    if any(not value for value in binding.values()):
        return None
    return {
        "work_order_id": work_order_id,
        "admission_metadata": {
            "schema_version": "foundup_memex_verified_outcome_binding.v2",
            **binding,
            "verification_receipt_digest": _digest(verifier_receipt),
            "held_out_receipt_digest": _digest(gate_receipt),
            "verified_at": now_iso,
        },
    }


def _has_runtime_binding(queue_item: Mapping[str, Any]) -> bool:
    fields = ("foundup_id", "snapshot_id", "snapshot_content_digest")
    present = tuple(bool(str(queue_item.get(key) or "")) for key in fields)
    if any(present) and not all(present):
        raise ValueError("verified_outcome_queue_binding_partial")
    return all(present)


def _legacy_admission(
    gate: Mapping[str, Any], work_order_id: str
) -> Mapping[str, Any]:
    return {
        "work_order_id": work_order_id,
        "admission_metadata": {
            "source": "resident_queue_derived_pattern_memory_admission",
            "gate_id": str(gate.get("gate_id") or ""),
            "ratchet_id": str(gate.get("ratchet_id") or ""),
            "verifier_receipt_id": str(gate.get("verifier_receipt_id") or ""),
            "held_out_suite_id": str(gate.get("held_out_suite_id") or ""),
            "held_out_suite_digest": str(gate.get("held_out_suite_digest") or ""),
            "candidate_head_sha": str(gate.get("candidate_head_sha") or ""),
        },
    }


def resolve_verified_outcome_publisher(
    dependency_bundle: Any,
    authority_profile: Mapping[str, Any],
    work_state_snapshot: Mapping[str, Any],
    trusted_now_epoch: Callable[[], int],
) -> Any:
    if not getattr(dependency_bundle, "requested", False):
        return None
    inputs = _publisher_inputs(authority_profile)
    try:
        resolver = CommittedAuthorityProfileOutcomeKeyResolver(
            work_state_snapshot=work_state_snapshot,
            authority_profile=authority_profile,
        )
        public_key = resolver.resolve(inputs["reddog_id"], inputs["key_epoch"])
    except ValueError:
        return None
    dependencies = (
        dependency_bundle.authority_store,
        dependency_bundle.signer,
        dependency_bundle.signature_verifier,
        public_key,
        *inputs.values(),
    )
    if any(not value for value in dependencies):
        return None
    try:
        return SignedVerifiedOutcomeEvidencePublisher(
            store=AuthorityRuntimeVerifiedOutcomeStore(dependency_bundle.authority_store),
            signer=dependency_bundle.signer,
            signature_verifier=dependency_bundle.signature_verifier,
            issuer_principal_id=inputs["principal_id"],
            issuer_principal_provider=inputs["principal_provider"],
            reddog_id=inputs["reddog_id"],
            signer_public_key=str(public_key),
            key_epoch=inputs["key_epoch"],
            authority_tier=inputs["authority_tier"],
            consensus_receipt_digest=inputs["consensus_receipt_digest"],
            trusted_now_epoch=trusted_now_epoch,
        )
    except ValueError:
        return None


def _gate_allows_admission(
    gate_result: Mapping[str, Any], gate_receipt: Mapping[str, Any]
) -> bool:
    return bool(
        gate_result
        and gate_receipt
        and gate_result.get("accepted") is True
        and gate_receipt.get("pattern_memory_admission_allowed") is True
    )


def _outcome_binding(
    queue_item: Mapping[str, Any],
    gate: Mapping[str, Any],
    verifier: Mapping[str, Any],
    work_order_id: str,
) -> Mapping[str, str]:
    return {
        "foundup_id": str(queue_item.get("foundup_id") or ""),
        "snapshot_id": str(queue_item.get("snapshot_id") or ""),
        "snapshot_content_digest": str(queue_item.get("snapshot_content_digest") or ""),
        "work_order_id": work_order_id,
        "slice_id": str(gate.get("slice_name") or ""),
        "job_id": str(gate.get("improvement_job_id") or ""),
        "worker_id": str(verifier.get("worker_id") or ""),
        "verifier_id": str(verifier.get("verifier_id") or ""),
        "head_sha": str(gate.get("candidate_head_sha") or ""),
        "runtime_binding_receipt_id": str(
            gate.get("model_runtime_binding_receipt_id") or ""
        ),
        "runtime_binding_digest": str(gate.get("model_runtime_binding_digest") or ""),
    }


def _publisher_inputs(profile: Mapping[str, Any]) -> Mapping[str, str]:
    return {
        "principal_id": str(profile.get("principal_id") or "").strip(),
        "principal_provider": str(profile.get("principal_provider") or "").strip(),
        "reddog_id": str(profile.get("reddog_id") or "").strip(),
        "key_epoch": str(profile.get("key_epoch") or "").strip(),
        "authority_tier": "HIGH",
        "consensus_receipt_digest": str(
            profile.get("consensus_receipt_digest") or ""
        ).strip(),
    }


def _queue_item(snapshot: Mapping[str, Any], queue_item_id: str) -> Mapping[str, Any]:
    items = snapshot.get("wre_queue_items")
    if not isinstance(items, list):
        return {}
    return next(
        (
            item
            for item in items
            if isinstance(item, Mapping)
            and str(item.get("queue_item_id") or "") == queue_item_id
        ),
        {},
    )


def _mapping(source: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = source.get(key)
    return value if isinstance(value, Mapping) else {}


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "derive_verified_outcome_admission",
    "resolve_verified_outcome_publisher",
]
