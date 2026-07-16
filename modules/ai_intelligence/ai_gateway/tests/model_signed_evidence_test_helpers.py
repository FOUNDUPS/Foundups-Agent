"""Test helpers for signed model evidence."""

from __future__ import annotations

import hashlib

from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    ModelBenchmarkEvidenceReceipt,
    ModelPromotionEvidenceReceipt,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    InMemoryEvidenceNonceStore,
    ModelEvidenceSignerRole,
    ModelEvidenceSubjectType,
    ModelSignedEvidenceReceipt,
    StaticModelEvidenceKeyResolver,
    VerifiedModelProductionEvidence,
    build_model_signed_evidence_receipt,
    build_verified_model_production_evidence,
    model_signed_evidence_signing_input,
)


BENCHMARK_PUBLIC_KEY = "ed25519-pub-v1:benchmark"
PROMOTION_PUBLIC_KEY = "ed25519-pub-v1:promotion"
BENCHMARK_FINGERPRINT = "fingerprint:benchmark"
PROMOTION_FINGERPRINT = "fingerprint:promotion"
KEY_EPOCH = "epoch-1"
NOW = 1_800_000_000


class DeterministicSignatureVerifier:
    def verify(self, public_key: str, signing_input: str, signature: str) -> bool:
        return signature == deterministic_signature(public_key, signing_input)


def deterministic_signature(public_key: str, signing_input: str) -> str:
    digest = hashlib.sha256(f"{public_key}\0{signing_input}".encode("utf-8")).hexdigest()
    return f"test-sig:{digest}"


def make_signed_evidence_receipt(
    *,
    signer_role: ModelEvidenceSignerRole,
    public_key: str,
    fingerprint: str,
    model_id: str,
    catalog_snapshot_id: str,
    selection_receipt_id: str,
    benchmark_run_receipt_id: str,
    benchmark_receipt: ModelBenchmarkEvidenceReceipt,
    promotion_receipt: ModelPromotionEvidenceReceipt | None = None,
    promotion_policy_digest: str | None = None,
    nonce: str,
    subject_type: ModelEvidenceSubjectType = ModelEvidenceSubjectType.MODEL,
    signature_override: str | None = None,
) -> ModelSignedEvidenceReceipt:
    placeholder = build_model_signed_evidence_receipt(
        signer_role=signer_role,
        signer_public_key=public_key,
        signer_key_fingerprint=fingerprint,
        key_epoch=KEY_EPOCH,
        subject_type=subject_type,
        model_or_panel_subject=model_id,
        catalog_snapshot_id=catalog_snapshot_id,
        selection_receipt_id=selection_receipt_id,
        benchmark_run_receipt_id=benchmark_run_receipt_id,
        benchmark_evidence_receipt_id=benchmark_receipt.receipt_id,
        task_family=benchmark_receipt.task_family,
        task_set_digest=benchmark_receipt.task_set_digest,
        held_out_split_digest=benchmark_receipt.held_out_split_digest,
        verifier_digest=benchmark_receipt.verifier_digest,
        prompt_topology_digest=benchmark_receipt.prompt_topology_digest,
        promotion_evidence_receipt_id=promotion_receipt.receipt_id if promotion_receipt else None,
        promotion_policy_digest=promotion_policy_digest,
        issued_at=NOW - 10,
        expires_at=NOW + 3600,
        nonce=nonce,
        signature="placeholder",
    )
    signature = signature_override or deterministic_signature(public_key, model_signed_evidence_signing_input(placeholder))
    return build_model_signed_evidence_receipt(
        signer_role=signer_role,
        signer_public_key=public_key,
        signer_key_fingerprint=fingerprint,
        key_epoch=KEY_EPOCH,
        subject_type=subject_type,
        model_or_panel_subject=model_id,
        catalog_snapshot_id=catalog_snapshot_id,
        selection_receipt_id=selection_receipt_id,
        benchmark_run_receipt_id=benchmark_run_receipt_id,
        benchmark_evidence_receipt_id=benchmark_receipt.receipt_id,
        task_family=benchmark_receipt.task_family,
        task_set_digest=benchmark_receipt.task_set_digest,
        held_out_split_digest=benchmark_receipt.held_out_split_digest,
        verifier_digest=benchmark_receipt.verifier_digest,
        prompt_topology_digest=benchmark_receipt.prompt_topology_digest,
        promotion_evidence_receipt_id=promotion_receipt.receipt_id if promotion_receipt else None,
        promotion_policy_digest=promotion_policy_digest,
        issued_at=NOW - 10,
        expires_at=NOW + 3600,
        nonce=nonce,
        signature=signature,
    )


def make_verified_production_evidence(
    benchmark: ModelBenchmarkEvidenceReceipt,
    promotion: ModelPromotionEvidenceReceipt,
    *,
    catalog_snapshot_id: str,
    selection_receipt_id: str = "model_selection_receipt:pending",
    benchmark_run_receipt_id: str = "model_combination_benchmark_run:test",
    promotion_policy_digest: str = "sha256:promotion-policy",
    consume_nonces: bool = False,
) -> VerifiedModelProductionEvidence:
    benchmark_signature = make_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.BENCHMARK_VERIFIER,
        public_key=BENCHMARK_PUBLIC_KEY,
        fingerprint=BENCHMARK_FINGERPRINT,
        model_id=benchmark.model_id,
        catalog_snapshot_id=catalog_snapshot_id,
        selection_receipt_id=selection_receipt_id,
        benchmark_run_receipt_id=benchmark_run_receipt_id,
        benchmark_receipt=benchmark,
        nonce=f"nonce:benchmark:{benchmark.receipt_id}:{selection_receipt_id}",
    )
    promotion_signature = make_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.PROMOTION_AUTHORITY,
        public_key=PROMOTION_PUBLIC_KEY,
        fingerprint=PROMOTION_FINGERPRINT,
        model_id=benchmark.model_id,
        catalog_snapshot_id=catalog_snapshot_id,
        selection_receipt_id=selection_receipt_id,
        benchmark_run_receipt_id=benchmark_run_receipt_id,
        benchmark_receipt=benchmark,
        promotion_receipt=promotion,
        promotion_policy_digest=promotion_policy_digest,
        nonce=f"nonce:promotion:{promotion.receipt_id}:{selection_receipt_id}",
    )
    return build_verified_model_production_evidence(
        catalog_snapshot_id=catalog_snapshot_id,
        selection_receipt_id=selection_receipt_id,
        benchmark_run_receipt_id=benchmark_run_receipt_id,
        benchmark_receipt=benchmark,
        promotion_receipt=promotion,
        benchmark_signature_receipt=benchmark_signature,
        promotion_signature_receipt=promotion_signature,
        key_resolver=StaticModelEvidenceKeyResolver(
            {
                ModelEvidenceSignerRole.BENCHMARK_VERIFIER.value: BENCHMARK_PUBLIC_KEY,
                ModelEvidenceSignerRole.PROMOTION_AUTHORITY.value: PROMOTION_PUBLIC_KEY,
            }
        ),
        signature_verifier=DeterministicSignatureVerifier(),
        now=NOW,
        nonce_store=InMemoryEvidenceNonceStore(),
        consume_nonces=consume_nonces,
    )
