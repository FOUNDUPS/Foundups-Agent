"""Test helpers for RedDog model runtime binding receipts."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, replace
from typing import Any, Mapping

from modules.ai_intelligence.ai_gateway.src.model_intelligence_catalog import (
    ModelCapabilityCard,
    PromotionState,
    build_model_catalog_snapshot,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    ModelOutcomeMetrics,
    build_model_benchmark_evidence_receipt,
    build_model_promotion_evidence_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import (
    ModelTaskRequirements,
    SelectionDecision,
    SelectionMode,
    SelectionPurpose,
    select_models_for_task,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding import (
    ModelRuntimeBindingDecision,
    ModelRuntimeBindingPolicy,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_evidence_verifier import (
    verify_model_runtime_binding_artifact,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_panel_rehydration import (
    PANEL_EVIDENCE_BUNDLE_SCHEMA_VERSION,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_use_time_verifier import (
    ModelRuntimeBindingUseTimeVerifier,
)
from modules.ai_intelligence.ai_gateway.src.model_panel_signed_evidence import (
    PanelEvidenceSignerRole,
)
from modules.ai_intelligence.ai_gateway.src.model_selection_artifact_supply import (
    EVIDENCE_BUNDLE_SCHEMA_VERSION,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    discard_verified_runtime_binding_capability,
    verified_runtime_binding_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    ModelEvidenceSignerRole,
    StaticModelEvidenceKeyResolver,
    VerifiedModelProductionEvidence,
)
from modules.ai_intelligence.ai_gateway.tests.model_signed_evidence_test_helpers import (
    BENCHMARK_FINGERPRINT,
    BENCHMARK_PUBLIC_KEY,
    DeterministicSignatureVerifier,
    KEY_EPOCH,
    PROMOTION_FINGERPRINT,
    PROMOTION_PUBLIC_KEY,
    make_verified_production_evidence,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_panel_test_helpers import (
    verified_panel_evidence,
)

_USE_TIME_VERIFIERS: dict[str, ModelRuntimeBindingUseTimeVerifier] = {}


@dataclass(frozen=True)
class _FixtureSeed:
    task_set_digest: str
    held_out_digest: str
    verifier_digest: str
    model_ids: tuple[str, ...]
    snapshot: Any
    benchmarks: tuple[Any, ...]
    promotions: tuple[Any, ...]


def model_selection_and_runtime_binding_receipts(
    *,
    runtime_surface: str,
    model_id: str = "openai/gpt-5.6-code",
    task_family: str = "reddog_runtime_model_call",
    panel_model_ids: tuple[str, ...] = (),
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build matching model-selection and runtime-binding receipts for tests."""

    seed = _fixture_seed(model_id, panel_model_ids, task_family)
    requirements = _selection_requirements(
        task_family, seed.model_ids, bool(panel_model_ids)
    )
    first_selection = _select_fixture(seed, requirements)
    if panel_model_ids:
        seed = _with_panel_topology(seed, task_family, first_selection)
    evidence = _verified_evidence(seed, first_selection)
    selection = select_models_for_task(
        seed.snapshot,
        first_selection.requirements,
        production_evidence=evidence,
    )
    policy = _runtime_policy(seed, selection, runtime_surface, task_family)
    runtime_evidence = (
        verified_panel_evidence(
            snapshot=seed.snapshot,
            selection=selection,
            benchmarks=seed.benchmarks,
            promotions=seed.promotions,
            policy=policy,
        )
        if panel_model_ids
        else evidence
    )
    return _build_receipt_pair(seed, selection, policy, runtime_evidence)


def _fixture_seed(
    model_id: str,
    panel_model_ids: tuple[str, ...],
    task_family: str,
) -> _FixtureSeed:
    model_ids = (model_id, *panel_model_ids)
    snapshot = build_model_catalog_snapshot(
        _model_cards(model_ids, task_family),
        generated_at="2026-07-16T00:00:00+00:00",
    )
    task_set_digest = _sha256("task-set")
    held_out_digest = _sha256("held-out")
    verifier_digest = _sha256("verifier")
    benchmarks = _benchmark_receipts(
        model_ids, task_family, task_set_digest, held_out_digest, verifier_digest
    )
    return _FixtureSeed(
        task_set_digest=task_set_digest,
        held_out_digest=held_out_digest,
        verifier_digest=verifier_digest,
        model_ids=model_ids,
        snapshot=snapshot,
        benchmarks=benchmarks,
        promotions=_promotion_receipts(benchmarks),
    )


def _model_cards(
    model_ids: tuple[str, ...],
    task_family: str,
) -> tuple[ModelCapabilityCard, ...]:
    return tuple(
        ModelCapabilityCard(
            provider=candidate.split("/", 1)[0],
            model_id=candidate,
            canonical_model_id=candidate,
            source="test",
            promotion_state=PromotionState.CHAMPION,
            task_families=(task_family,),
            supports_structured_output=True,
            supports_reasoning=True,
            benchmark_scores={task_family: 0.99 - index * 0.01},
            verifier_pass_rate=0.99 - index * 0.01,
        ).normalized()
        for index, candidate in enumerate(model_ids)
    )


def _benchmark_receipts(
    model_ids: tuple[str, ...],
    task_family: str,
    task_set_digest: str,
    held_out_digest: str,
    verifier_digest: str,
    topology_digest: str = "sha256:topology",
) -> tuple[Any, ...]:
    return tuple(
        build_model_benchmark_evidence_receipt(
            model_id=candidate,
            task_family=task_family,
            task_set_digest=task_set_digest,
            held_out_split_digest=held_out_digest,
            prompt_topology_digest=topology_digest,
            verifier_digest=verifier_digest,
            verifier_receipt_id=f"sha256:verifier-receipt-{index}",
            sample_count=20,
            accepted_count=20,
            metrics=ModelOutcomeMetrics(
                latency_ms=100 + index,
                input_tokens=10,
                output_tokens=20,
            ),
        )
        for index, candidate in enumerate(model_ids)
    )


def _promotion_receipts(benchmarks: tuple[Any, ...]) -> tuple[Any, ...]:
    return tuple(
        build_model_promotion_evidence_receipt(
            benchmark_receipt=benchmark,
            promotion_state=PromotionState.CHAMPION,
            promotion_authority_receipt_id="sha256:promotion-authority",
            signed_promotion_receipt_id=f"signature:promotion-{index}",
            min_verifier_pass_rate=0.9,
        )
        for index, benchmark in enumerate(benchmarks)
    )


def _selection_requirements(
    task_family: str,
    model_ids: tuple[str, ...],
    panel: bool,
) -> ModelTaskRequirements:
    return ModelTaskRequirements(
        task_family=task_family,
        selection_mode=SelectionMode.PANEL if panel else SelectionMode.SINGLE,
        purpose=SelectionPurpose.PRODUCTION,
        min_verifier_pass_rate=0.9,
        require_structured_output=True,
        require_reasoning=True,
        max_candidates=len(model_ids),
        panel_roles=(
            "principal",
            *(f"critic_{index}" for index in range(1, len(model_ids))),
        ),
    )


def _select_fixture(
    seed: _FixtureSeed,
    requirements: ModelTaskRequirements,
) -> Any:
    return select_models_for_task(
        seed.snapshot,
        requirements,
        production_evidence=_verified_evidence(seed, None),
    )


def _verified_evidence(
    seed: _FixtureSeed,
    selection: Any | None,
) -> VerifiedModelProductionEvidence:
    return VerifiedModelProductionEvidence(
        entries=tuple(
            entry
            for benchmark, promotion in zip(seed.benchmarks, seed.promotions)
            for entry in _signed_model_evidence(
                seed, selection, benchmark, promotion
            ).entries
        )
    )


def _signed_model_evidence(
    seed: _FixtureSeed,
    selection: Any | None,
    benchmark: Any,
    promotion: Any,
) -> Any:
    values = {
        "catalog_snapshot_id": seed.snapshot.snapshot_id,
    }
    if selection is not None:
        values["selection_receipt_id"] = selection.receipt_id
    return make_verified_production_evidence(
        benchmark,
        promotion,
        **values,
    )


def _with_panel_topology(
    seed: _FixtureSeed,
    task_family: str,
    selection: Any,
) -> _FixtureSeed:
    benchmarks = _benchmark_receipts(
        seed.model_ids,
        task_family,
        seed.task_set_digest,
        seed.held_out_digest,
        seed.verifier_digest,
        selection.panel_topology_digest,
    )
    return replace(
        seed,
        benchmarks=benchmarks,
        promotions=_promotion_receipts(benchmarks),
    )


def _runtime_policy(
    seed: _FixtureSeed,
    selection: Any,
    runtime_surface: str,
    task_family: str,
) -> ModelRuntimeBindingPolicy:
    return ModelRuntimeBindingPolicy(
        task_family=task_family,
        runtime_surface=runtime_surface,
        min_verifier_pass_rate=0.9,
        required_task_set_digest=seed.task_set_digest,
        required_held_out_split_digest=seed.held_out_digest,
        required_verifier_digest=seed.verifier_digest,
        required_panel_topology_digest=(
            selection.panel_topology_digest
            if selection.requirements.selection_mode == SelectionMode.PANEL
            else None
        ),
        authority_receipt_id="runtime-authority:test",
    )


def _build_receipt_pair(
    seed: _FixtureSeed,
    selection: Any,
    policy: ModelRuntimeBindingPolicy,
    runtime_evidence: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    verifier_inputs = _runtime_verifier_inputs(
        seed=seed,
        selection=selection,
        policy=policy,
        runtime_evidence=runtime_evidence,
    )
    verified = verify_model_runtime_binding_artifact(
        model_selection_receipt=_json_normalized(selection.to_dict()),
        **verifier_inputs,
        now=1_800_000_000,
    )
    receipt = verified.binding
    verification = verified.verification
    discard_verified_runtime_binding_capability(verified.capability)
    assert selection.decision == SelectionDecision.SELECTED
    assert receipt.decision == ModelRuntimeBindingDecision.BOUND
    runtime_dict = _json_normalized(
        {
            **receipt.to_dict(),
            "verification_receipt": verification.to_dict(),
        }
    )
    _USE_TIME_VERIFIERS[verification.receipt_id] = ModelRuntimeBindingUseTimeVerifier(
        **verifier_inputs,
        trusted_now_epoch=lambda: 1_800_000_000,
    )
    return _json_normalized(selection.to_dict()), runtime_dict


def _runtime_verifier_inputs(
    *,
    seed: _FixtureSeed,
    selection: Any,
    policy: ModelRuntimeBindingPolicy,
    runtime_evidence: Any,
) -> dict[str, Any]:
    trusted_keys = {
        (
            ModelEvidenceSignerRole.BENCHMARK_VERIFIER.value,
            BENCHMARK_FINGERPRINT,
            KEY_EPOCH,
        ): BENCHMARK_PUBLIC_KEY,
        (
            ModelEvidenceSignerRole.PROMOTION_AUTHORITY.value,
            PROMOTION_FINGERPRINT,
            KEY_EPOCH,
        ): PROMOTION_PUBLIC_KEY,
    }
    runtime_policy = policy.to_dict()
    if selection.requirements.selection_mode == SelectionMode.PANEL:
        aggregate = runtime_evidence.aggregate_receipt
        bundle = _panel_verifier_bundle(seed, selection, runtime_evidence)
        runtime_policy["panel_context_receipt_ids"] = {
            "task_receipt_id": aggregate.task_receipt_id,
            "topology_receipt_id": aggregate.topology_receipt_id,
            "policy_receipt_id": aggregate.policy_receipt_id,
            "runtime_surface_receipt_id": aggregate.runtime_surface_receipt_id,
        }
        trusted_keys[
            (
                PanelEvidenceSignerRole.PANEL_AUTHORITY.value,
                aggregate.signer_key_fingerprint,
                aggregate.key_epoch,
            )
        ] = aggregate.signer_public_key
    else:
        bundle = _single_verifier_bundle(seed, selection, runtime_evidence)
    trusted_keys_payload = _trusted_keys_payload(trusted_keys)
    resolver = StaticModelEvidenceKeyResolver(trusted_keys)
    verifier = DeterministicSignatureVerifier()
    return {
        "catalog_snapshot": _json_normalized(seed.snapshot.to_dict()),
        "benchmark_evidence_receipts": tuple(
            _json_normalized(item.to_dict()) for item in seed.benchmarks
        ),
        "promotion_evidence_receipts": tuple(
            _json_normalized(item.to_dict()) for item in seed.promotions
        ),
        "verified_evidence_bundle": _json_normalized(bundle),
        "runtime_policy": _json_normalized(runtime_policy),
        "trusted_keys_payload": _json_normalized(trusted_keys_payload),
        "key_resolver": resolver,
        "signature_verifier": verifier,
    }


def _trusted_keys_payload(trusted_keys: Mapping[Any, str]) -> dict[str, Any]:
    return {
        "trusted_public_keys": [
            {
                "signer_role": role,
                "signer_key_fingerprint": fingerprint,
                "key_epoch": epoch,
                "public_key": public_key,
            }
            for (role, fingerprint, epoch), public_key in trusted_keys.items()
        ]
    }


def _single_verifier_bundle(seed, selection, runtime_evidence):
    entry = runtime_evidence.entries[0]
    return {
        "schema_version": EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "catalog_snapshot_id": seed.snapshot.snapshot_id,
        "selection_receipt_id": selection.receipt_id,
        "benchmark_run_receipt_id": (
            entry.benchmark_signature_receipt.benchmark_run_receipt_id
        ),
        "entries": [_entry_records(entry)],
    }


def _panel_verifier_bundle(seed, selection, runtime_evidence):
    aggregate = runtime_evidence.aggregate_receipt
    return {
        "schema_version": PANEL_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "catalog_snapshot_id": seed.snapshot.snapshot_id,
        "selection_receipt_id": selection.receipt_id,
        "benchmark_run_receipt_id": aggregate.benchmark_run_receipt_id,
        "aggregate_receipt": aggregate.to_dict(),
        "entries": [
            {
                "role": member.role,
                "model_id": member.model_id,
                "provider": member.provider,
                **_entry_records(entry),
            }
            for member, entry in zip(
                aggregate.members, runtime_evidence.member_entries
            )
        ],
    }


def _entry_records(entry: Any) -> dict[str, Any]:
    return {
        "benchmark_receipt": entry.benchmark_receipt.to_dict(),
        "promotion_receipt": entry.promotion_receipt.to_dict(),
        "benchmark_signature_receipt": (
            entry.benchmark_signature_receipt.to_dict()
        ),
        "promotion_signature_receipt": (
            entry.promotion_signature_receipt.to_dict()
        ),
    }


def model_runtime_binding_receipt(
    *,
    runtime_surface: str,
    model_id: str = "openai/gpt-5.6-code",
    task_family: str = "reddog_runtime_model_call",
    panel_model_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Build a valid single-model runtime binding receipt for runtime tests."""

    _, receipt = model_selection_and_runtime_binding_receipts(
        runtime_surface=runtime_surface,
        model_id=model_id,
        task_family=task_family,
        panel_model_ids=panel_model_ids,
    )
    return receipt


def model_runtime_binding_test_capability(
    selection: dict[str, Any],
    binding: dict[str, Any],
) -> Any:
    """Issue a test-only invocation proof for an already built fixture."""

    verification = verified_runtime_binding_receipt(binding)
    if verification is None:
        return None
    verifier = _USE_TIME_VERIFIERS.get(verification.receipt_id)
    if verifier is None:
        return None
    try:
        return verifier.verify(
            binding=binding,
            selection=selection,
        )
    except (TypeError, ValueError):
        return None


def model_runtime_binding_test_verifier(
    binding: dict[str, Any],
) -> ModelRuntimeBindingUseTimeVerifier | None:
    verification = verified_runtime_binding_receipt(binding)
    return (
        _USE_TIME_VERIFIERS.get(verification.receipt_id)
        if verification is not None
        else None
    )


def _json_normalized(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _content_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
