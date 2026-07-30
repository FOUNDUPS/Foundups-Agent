"""Use-time re-verification for persisted RedDog model runtime bindings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)

from .model_runtime_binding_digest import canonical_digest
from .model_runtime_binding_evidence_verifier import (
    verify_model_runtime_binding_artifact,
)
from .model_runtime_binding_verified_admission import (
    VerifiedRuntimeBindingCapability,
    discard_verified_runtime_binding_capability,
    verified_runtime_binding_receipt,
)
from .model_signed_evidence import ModelEvidenceKeyResolver


@dataclass(frozen=True)
class ModelRuntimeBindingUseTimeVerifier:
    """Reverify immutable signed inputs against current time and key state."""

    catalog_snapshot: Mapping[str, Any]
    benchmark_evidence_receipts: Sequence[Mapping[str, Any]]
    promotion_evidence_receipts: Sequence[Mapping[str, Any]]
    verified_evidence_bundle: Mapping[str, Any]
    runtime_policy: Mapping[str, Any]
    trusted_keys_payload: Mapping[str, Any]
    key_resolver: ModelEvidenceKeyResolver
    signature_verifier: SignatureVerifier
    trusted_now_epoch: Callable[[], int]

    def verify(
        self,
        *,
        binding: Mapping[str, Any],
        selection: Mapping[str, Any],
    ) -> VerifiedRuntimeBindingCapability:
        """Return a one-shot proof only when the durable artifact still verifies."""

        persisted = verified_runtime_binding_receipt(binding)
        if persisted is None:
            raise ValueError("model_runtime_binding_verification_receipt_missing")
        verified = verify_model_runtime_binding_artifact(
            catalog_snapshot=self.catalog_snapshot,
            model_selection_receipt=selection,
            benchmark_evidence_receipts=self.benchmark_evidence_receipts,
            promotion_evidence_receipts=self.promotion_evidence_receipts,
            verified_evidence_bundle=self.verified_evidence_bundle,
            runtime_policy=self.runtime_policy,
            trusted_keys_payload=self.trusted_keys_payload,
            key_resolver=self.key_resolver,
            signature_verifier=self.signature_verifier,
            now=int(self.trusted_now_epoch()),
            receipt_verified_at=persisted.verified_at,
        )
        if canonical_digest(verified.to_artifact()) != canonical_digest(binding):
            discard_verified_runtime_binding_capability(verified.capability)
            raise ValueError("model_runtime_binding_verification_artifact_mismatch")
        return verified.capability


__all__ = ["ModelRuntimeBindingUseTimeVerifier"]
