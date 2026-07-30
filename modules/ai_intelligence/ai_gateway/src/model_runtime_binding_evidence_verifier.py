"""Canonical restart-safe verification for RedDog model runtime bindings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)

from .model_intelligence_outcomes import (
    ModelBenchmarkEvidenceReceipt,
    ModelPromotionEvidenceReceipt,
)
from .model_runtime_binding import (
    ModelRuntimeBindingDecision,
    ModelRuntimeBindingPolicy,
    RedDogModelRuntimeBindingReceipt,
    bind_reddog_runtime_models,
)
from .model_runtime_binding_capability import (
    VerifiedRuntimeBindingCapability,
    build_verified_runtime_binding_capability_api,
)
from .model_runtime_binding_digest import canonical_digest
from .model_runtime_binding_input_rehydration import (
    rehydrate_benchmark_evidence,
    rehydrate_promotion_evidence,
    rehydrate_runtime_policy,
)
from .model_runtime_binding_evidence_dispatch import (
    rehydrate_verified_runtime_evidence,
)
from .model_runtime_binding_verification_builder import (
    build_runtime_binding_verification_receipt,
)
from .model_runtime_binding_verification_receipt import (
    ModelRuntimeBindingVerificationReceipt,
)
from .model_signed_evidence import (
    ModelEvidenceKeyResolver,
    rehydrate_model_catalog_snapshot,
    rehydrate_model_runtime_binding_receipt,
    rehydrate_model_selection_receipt,
)


@dataclass(frozen=True)
class VerifiedRuntimeBindingArtifact:
    binding: RedDogModelRuntimeBindingReceipt
    verification: ModelRuntimeBindingVerificationReceipt
    capability: VerifiedRuntimeBindingCapability

    def to_artifact(self) -> dict[str, Any]:
        return {
            **self.binding.to_dict(),
            "verification_receipt": self.verification.to_dict(),
        }


def _verified_artifact_inputs(
    *,
    catalog_snapshot: Mapping[str, Any],
    model_selection_receipt: Mapping[str, Any],
    benchmark_evidence_receipts: Sequence[Mapping[str, Any]],
    promotion_evidence_receipts: Sequence[Mapping[str, Any]],
    verified_evidence_bundle: Mapping[str, Any],
    runtime_policy: Mapping[str, Any],
    trusted_keys_payload: Mapping[str, Any],
    key_resolver: ModelEvidenceKeyResolver,
    signature_verifier: SignatureVerifier,
    now: int,
    receipt_verified_at: int | None = None,
) -> tuple[Mapping[str, Any], Mapping[str, Any], ModelRuntimeBindingVerificationReceipt]:
    snapshot = rehydrate_model_catalog_snapshot(catalog_snapshot)
    selection = rehydrate_model_selection_receipt(model_selection_receipt)
    benchmarks = rehydrate_benchmark_evidence(benchmark_evidence_receipts)
    promotions = rehydrate_promotion_evidence(
        promotion_evidence_receipts, benchmarks
    )
    policy = rehydrate_runtime_policy(runtime_policy)
    evidence = rehydrate_verified_runtime_evidence(
        verified_evidence_bundle=verified_evidence_bundle,
        snapshot=snapshot,
        selection=selection,
        policy=policy,
        runtime_policy_payload=runtime_policy,
        trusted_keys_payload=trusted_keys_payload,
        key_resolver=key_resolver,
        signature_verifier=signature_verifier,
        now=now,
    )
    binding = _bind_runtime(snapshot, selection, benchmarks, promotions, policy, evidence)
    verification = _verification_receipt(
        binding=binding,
        selection=selection,
        evidence=evidence,
        catalog_snapshot=catalog_snapshot,
        runtime_policy=runtime_policy,
        verified_evidence_bundle=verified_evidence_bundle,
        trusted_keys_payload=trusted_keys_payload,
        verified_at=int(receipt_verified_at or now),
    )
    artifact = {**binding.to_dict(), "verification_receipt": verification.to_dict()}
    return artifact, selection.to_dict(), verification


def _bind_runtime(
    snapshot: Any,
    selection: Any,
    benchmarks: Sequence[ModelBenchmarkEvidenceReceipt],
    promotions: Sequence[ModelPromotionEvidenceReceipt],
    policy: ModelRuntimeBindingPolicy,
    evidence: Any,
) -> RedDogModelRuntimeBindingReceipt:
    binding = bind_reddog_runtime_models(
        catalog_snapshot=snapshot,
        selection_receipt=selection,
        benchmark_evidence_receipts=benchmarks,
        promotion_evidence_receipts=promotions,
        policy=policy,
        verified_production_evidence=evidence,
    )
    if binding.decision != ModelRuntimeBindingDecision.BOUND:
        raise ValueError(
            "model_runtime_binding_rejected:" + ",".join(binding.rejection_reasons)
        )
    return binding


def _verification_receipt(
    *,
    binding: RedDogModelRuntimeBindingReceipt,
    selection: Any,
    evidence: Any,
    catalog_snapshot: Mapping[str, Any],
    runtime_policy: Mapping[str, Any],
    verified_evidence_bundle: Mapping[str, Any],
    trusted_keys_payload: Mapping[str, Any],
    verified_at: int,
) -> ModelRuntimeBindingVerificationReceipt:
    return build_runtime_binding_verification_receipt(
        binding=binding,
        selection=selection,
        evidence=evidence,
        catalog_snapshot_digest=canonical_digest(catalog_snapshot),
        runtime_policy_digest=canonical_digest(runtime_policy),
        evidence_bundle_digest=canonical_digest(verified_evidence_bundle),
        trusted_keys_digest=canonical_digest(trusted_keys_payload),
        verified_at=verified_at,
    )


def _build_public_verifier_api(
) -> tuple[Callable[..., Any], Callable[..., Any], Callable[[Any], None]]:
    issue, consume, discard = build_verified_runtime_binding_capability_api(
        _verified_artifact_inputs
    )

    def verify_model_runtime_binding_artifact(
        **inputs: Any,
    ) -> VerifiedRuntimeBindingArtifact:
        artifact, _selection, receipt, capability = issue(**inputs)
        binding = rehydrate_model_runtime_binding_receipt(artifact)
        return VerifiedRuntimeBindingArtifact(binding, receipt, capability)

    return verify_model_runtime_binding_artifact, consume, discard

(
    verify_model_runtime_binding_artifact,
    consume_verified_runtime_binding_capability,
    discard_verified_runtime_binding_capability,
) = _build_public_verifier_api()
del _build_public_verifier_api


__all__ = [
    "VerifiedRuntimeBindingArtifact",
    "VerifiedRuntimeBindingCapability",
    "consume_verified_runtime_binding_capability",
    "discard_verified_runtime_binding_capability",
    "verify_model_runtime_binding_artifact",
]
