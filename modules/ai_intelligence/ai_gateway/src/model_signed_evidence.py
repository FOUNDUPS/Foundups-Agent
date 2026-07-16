"""Signed production-evidence verification for model intelligence.

This module is the admission gate between benchmark/promotion receipts and
production model selection. It rehydrates receipt mappings, recomputes their
deterministic IDs, verifies role-specific signatures using the existing RedDog
signature backend contract, and returns a typed object that production
selection/runtime binding may consume.

It does not sign, generate keys, call models, run benchmarks, execute commands,
write PatternMemory, re-index HoloIndex, or promote a model by itself.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    NonceStore,
    SignatureVerifier,
    canonical_signing_input,
    constant_time_compare,
)

from .model_intelligence_catalog import (
    Availability,
    ModelCapabilityCard,
    ModelCatalogRejectedRecord,
    ModelCatalogSnapshot,
    PromotionState,
    build_model_catalog_snapshot,
)
from .model_intelligence_outcomes import (
    ModelBenchmarkEvidenceReceipt,
    ModelOutcomeMetrics,
    ModelPromotionEvidenceReceipt,
    build_model_benchmark_evidence_receipt,
    build_model_promotion_evidence_receipt,
    production_evidence_for_selection,
)
from .model_intelligence_selection import (
    ModelCandidateRanking,
    ModelPanelRoleAssignment,
    ModelSelectionReceipt,
    ModelTaskRequirements,
    SelectionDecision,
    SelectionMode,
    SelectionPurpose,
)
from .model_runtime_binding import (
    ModelRuntimeBindingDecision,
    ModelRuntimeBindingPolicy,
    RedDogModelRuntimeBindingReceipt,
    RuntimeModelRoleBinding,
)


SIGNED_EVIDENCE_SCHEMA_VERSION = "model_signed_evidence_receipt.v1"
VERIFIED_PRODUCTION_EVIDENCE_SCHEMA_VERSION = "verified_model_production_evidence.v1"
PREFIX_MODEL_SIGNED_EVIDENCE = "reddog-model-evidence.v1"


class ModelEvidenceSignerRole(str, Enum):
    """Signer roles accepted by the model-evidence admission gate."""

    BENCHMARK_VERIFIER = "benchmark_verifier"
    PROMOTION_AUTHORITY = "promotion_authority"


class ModelEvidenceSubjectType(str, Enum):
    """Current signed evidence subject types."""

    MODEL = "model"
    PANEL = "panel"


@dataclass(frozen=True)
class ModelSignedEvidenceReceipt:
    """Role-specific signed evidence over model benchmark/promotion receipts."""

    receipt_id: str
    signer_role: ModelEvidenceSignerRole
    signer_public_key: str
    signer_key_fingerprint: str
    key_epoch: str
    subject_type: ModelEvidenceSubjectType
    model_or_panel_subject: str
    catalog_snapshot_id: str
    selection_receipt_id: str
    benchmark_run_receipt_id: str
    benchmark_evidence_receipt_id: str
    task_family: str
    task_set_digest: str
    held_out_split_digest: str
    verifier_digest: str
    prompt_topology_digest: str
    promotion_evidence_receipt_id: str | None
    promotion_policy_digest: str | None
    issued_at: int
    expires_at: int
    nonce: str
    signature: str
    schema_version: str = SIGNED_EVIDENCE_SCHEMA_VERSION

    def to_signed_record(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "signer_role": self.signer_role.value,
            "signer_public_key": self.signer_public_key,
            "signer_key_fingerprint": self.signer_key_fingerprint,
            "key_epoch": self.key_epoch,
            "subject_type": self.subject_type.value,
            "model_or_panel_subject": self.model_or_panel_subject,
            "catalog_snapshot_id": self.catalog_snapshot_id,
            "selection_receipt_id": self.selection_receipt_id,
            "benchmark_run_receipt_id": self.benchmark_run_receipt_id,
            "benchmark_evidence_receipt_id": self.benchmark_evidence_receipt_id,
            "task_family": self.task_family,
            "task_set_digest": self.task_set_digest,
            "held_out_split_digest": self.held_out_split_digest,
            "verifier_digest": self.verifier_digest,
            "prompt_topology_digest": self.prompt_topology_digest,
            "promotion_evidence_receipt_id": self.promotion_evidence_receipt_id,
            "promotion_policy_digest": self.promotion_policy_digest,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "signature": self.signature,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"receipt_id": self.receipt_id, **self.to_signed_record()}


@dataclass(frozen=True)
class VerifiedModelEvidenceEntry:
    """Authenticated production evidence for one model subject."""

    model_id: str
    benchmark_receipt: ModelBenchmarkEvidenceReceipt
    promotion_receipt: ModelPromotionEvidenceReceipt
    benchmark_signature_receipt: ModelSignedEvidenceReceipt
    promotion_signature_receipt: ModelSignedEvidenceReceipt

    def to_selection_mapping(self) -> dict[str, Any]:
        mapping = production_evidence_for_selection(self.benchmark_receipt, self.promotion_receipt)[self.model_id]
        mapping.update(
            {
                "benchmark_signed_evidence_receipt_id": self.benchmark_signature_receipt.receipt_id,
                "promotion_signed_evidence_receipt_id": self.promotion_signature_receipt.receipt_id,
            }
        )
        return mapping


@dataclass(frozen=True)
class VerifiedModelProductionEvidence:
    """Typed evidence object accepted by production model selection."""

    entries: tuple[VerifiedModelEvidenceEntry, ...]
    schema_version: str = VERIFIED_PRODUCTION_EVIDENCE_SCHEMA_VERSION
    signed_evidence_verified: bool = True

    def to_selection_mapping(self) -> dict[str, dict[str, Any]]:
        return {entry.model_id: entry.to_selection_mapping() for entry in self.entries}

    def selection_receipt_ids(self) -> tuple[str, ...]:
        ids: set[str] = set()
        for entry in self.entries:
            ids.add(entry.benchmark_signature_receipt.selection_receipt_id)
            ids.add(entry.promotion_signature_receipt.selection_receipt_id)
        return tuple(sorted(ids))

    def model_ids(self) -> tuple[str, ...]:
        return tuple(sorted(entry.model_id for entry in self.entries))


@dataclass(frozen=True)
class SignedEvidenceVerificationResult:
    """Verification result for one signed model-evidence receipt."""

    accepted: bool
    reason_codes: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return self.accepted


@runtime_checkable
class ModelEvidenceKeyResolver(Protocol):
    """Trust anchor for role-specific public keys."""

    def resolve(self, signer_role: str, signer_key_fingerprint: str, key_epoch: str) -> str | None: ...


class StaticModelEvidenceKeyResolver:
    """Deterministic test/runtime adapter for trusted public model-evidence keys."""

    def __init__(self, trusted_public_keys: Mapping[tuple[str, str, str], str] | Mapping[str, str]):
        self._trusted_public_keys = dict(trusted_public_keys)

    def resolve(self, signer_role: str, signer_key_fingerprint: str, key_epoch: str) -> str | None:
        exact = self._trusted_public_keys.get((signer_role, signer_key_fingerprint, key_epoch))
        if exact:
            return exact
        return self._trusted_public_keys.get(signer_role)


class InMemoryEvidenceNonceStore:
    """Small test/store adapter with the same consume-once shape as RedDog nonce stores."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def consume(self, nonce: str) -> bool:
        if not isinstance(nonce, str) or not nonce or nonce in self._seen:
            return False
        self._seen.add(nonce)
        return True


def build_model_signed_evidence_receipt(
    *,
    signer_role: ModelEvidenceSignerRole | str,
    signer_public_key: str,
    signer_key_fingerprint: str,
    key_epoch: str,
    subject_type: ModelEvidenceSubjectType | str,
    model_or_panel_subject: str,
    catalog_snapshot_id: str,
    selection_receipt_id: str,
    benchmark_run_receipt_id: str,
    benchmark_evidence_receipt_id: str,
    task_family: str,
    task_set_digest: str,
    held_out_split_digest: str,
    verifier_digest: str,
    prompt_topology_digest: str,
    promotion_evidence_receipt_id: str | None = None,
    promotion_policy_digest: str | None = None,
    issued_at: int,
    expires_at: int,
    nonce: str,
    signature: str,
) -> ModelSignedEvidenceReceipt:
    """Build a deterministic signed-evidence receipt from already-issued signature text."""

    role = _coerce_role(signer_role)
    subject_kind = _coerce_subject_type(subject_type)
    body = {
        "schema_version": SIGNED_EVIDENCE_SCHEMA_VERSION,
        "signer_role": role.value,
        "signer_public_key": _required("signer_public_key", signer_public_key),
        "signer_key_fingerprint": _required("signer_key_fingerprint", signer_key_fingerprint),
        "key_epoch": _required("key_epoch", key_epoch),
        "subject_type": subject_kind.value,
        "model_or_panel_subject": _required("model_or_panel_subject", model_or_panel_subject),
        "catalog_snapshot_id": _required("catalog_snapshot_id", catalog_snapshot_id),
        "selection_receipt_id": _required("selection_receipt_id", selection_receipt_id),
        "benchmark_run_receipt_id": _required("benchmark_run_receipt_id", benchmark_run_receipt_id),
        "benchmark_evidence_receipt_id": _required(
            "benchmark_evidence_receipt_id",
            benchmark_evidence_receipt_id,
        ),
        "task_family": _clean_token(_required("task_family", task_family)),
        "task_set_digest": _required("task_set_digest", task_set_digest),
        "held_out_split_digest": _required("held_out_split_digest", held_out_split_digest),
        "verifier_digest": _required("verifier_digest", verifier_digest),
        "prompt_topology_digest": _required("prompt_topology_digest", prompt_topology_digest),
        "promotion_evidence_receipt_id": _optional(promotion_evidence_receipt_id),
        "promotion_policy_digest": _optional(promotion_policy_digest),
        "issued_at": _int_value(issued_at, "issued_at"),
        "expires_at": _int_value(expires_at, "expires_at"),
        "nonce": _required("nonce", nonce),
        "signature": _required("signature", signature),
    }
    if body["expires_at"] <= body["issued_at"]:
        raise ValueError("invalid_evidence_ttl")
    return ModelSignedEvidenceReceipt(
        receipt_id=_digest_prefixed("model_signed_evidence", body),
        signer_role=role,
        signer_public_key=body["signer_public_key"],
        signer_key_fingerprint=body["signer_key_fingerprint"],
        key_epoch=body["key_epoch"],
        subject_type=subject_kind,
        model_or_panel_subject=body["model_or_panel_subject"],
        catalog_snapshot_id=body["catalog_snapshot_id"],
        selection_receipt_id=body["selection_receipt_id"],
        benchmark_run_receipt_id=body["benchmark_run_receipt_id"],
        benchmark_evidence_receipt_id=body["benchmark_evidence_receipt_id"],
        task_family=body["task_family"],
        task_set_digest=body["task_set_digest"],
        held_out_split_digest=body["held_out_split_digest"],
        verifier_digest=body["verifier_digest"],
        prompt_topology_digest=body["prompt_topology_digest"],
        promotion_evidence_receipt_id=body["promotion_evidence_receipt_id"],
        promotion_policy_digest=body["promotion_policy_digest"],
        issued_at=body["issued_at"],
        expires_at=body["expires_at"],
        nonce=body["nonce"],
        signature=body["signature"],
    )


def model_signed_evidence_signing_input(receipt_or_record: ModelSignedEvidenceReceipt | Mapping[str, Any]) -> str:
    """Return the domain-separated canonical signing input for model evidence."""

    record = receipt_or_record.to_signed_record() if isinstance(receipt_or_record, ModelSignedEvidenceReceipt) else dict(receipt_or_record)
    return canonical_signing_input(record, PREFIX_MODEL_SIGNED_EVIDENCE)


def rehydrate_model_catalog_snapshot(data: Mapping[str, Any]) -> ModelCatalogSnapshot:
    """Rehydrate a catalog snapshot and recompute its snapshot ID."""

    if data.get("schema_version") != "model_catalog_snapshot.v1":
        raise ValueError("invalid_catalog_schema")
    cards = tuple(_rehydrate_card(item) for item in _list_value(data.get("cards"), "cards"))
    rejected = tuple(_rehydrate_rejected_record(item) for item in _list_value(data.get("rejected_records", []), "rejected_records"))
    snapshot = build_model_catalog_snapshot(
        cards,
        source_receipts=tuple(str(value) for value in _list_value(data.get("source_receipts", []), "source_receipts")),
        rejected_records=rejected,
        generated_at=_required("generated_at", data.get("generated_at")),
    )
    if not constant_time_compare(snapshot.snapshot_id, _required("snapshot_id", data.get("snapshot_id"))):
        raise ValueError("catalog_snapshot_id_mismatch")
    return snapshot


def rehydrate_model_benchmark_evidence_receipt(data: Mapping[str, Any]) -> ModelBenchmarkEvidenceReceipt:
    """Rehydrate benchmark evidence and recompute its receipt ID."""

    if data.get("schema_version") != "model_benchmark_evidence_receipt.v1":
        raise ValueError("invalid_benchmark_schema")
    metrics_data = _mapping_value(data.get("metrics"), "metrics")
    receipt = build_model_benchmark_evidence_receipt(
        model_id=_required("model_id", data.get("model_id")),
        task_family=_required("task_family", data.get("task_family")),
        task_set_digest=_required("task_set_digest", data.get("task_set_digest")),
        held_out_split_digest=_required("held_out_split_digest", data.get("held_out_split_digest")),
        prompt_topology_digest=_required("prompt_topology_digest", data.get("prompt_topology_digest")),
        verifier_digest=_required("verifier_digest", data.get("verifier_digest")),
        verifier_receipt_id=_required("verifier_receipt_id", data.get("verifier_receipt_id")),
        sample_count=_int_value(data.get("sample_count"), "sample_count"),
        accepted_count=_int_value(data.get("accepted_count"), "accepted_count"),
        metrics=ModelOutcomeMetrics(
            latency_ms=metrics_data.get("latency_ms"),
            input_tokens=metrics_data.get("input_tokens"),
            output_tokens=metrics_data.get("output_tokens"),
            cost_estimate_usd=metrics_data.get("cost_estimate_usd"),
        ),
    )
    if not constant_time_compare(receipt.receipt_id, _required("receipt_id", data.get("receipt_id"))):
        raise ValueError("benchmark_receipt_id_mismatch")
    if float(data.get("verifier_pass_rate")) != receipt.verifier_pass_rate:
        raise ValueError("benchmark_pass_rate_mismatch")
    return receipt


def rehydrate_model_promotion_evidence_receipt(
    data: Mapping[str, Any],
    *,
    benchmark_receipt: ModelBenchmarkEvidenceReceipt,
) -> ModelPromotionEvidenceReceipt:
    """Rehydrate promotion evidence and recompute its receipt ID."""

    if data.get("schema_version") != "model_promotion_evidence_receipt.v1":
        raise ValueError("invalid_promotion_schema")
    receipt = build_model_promotion_evidence_receipt(
        benchmark_receipt=benchmark_receipt,
        promotion_state=PromotionState(_required("promotion_state", data.get("promotion_state"))),
        promotion_authority_receipt_id=_required(
            "promotion_authority_receipt_id",
            data.get("promotion_authority_receipt_id"),
        ),
        signed_promotion_receipt_id=_required("signed_promotion_receipt_id", data.get("signed_promotion_receipt_id")),
        min_verifier_pass_rate=float(data.get("min_verifier_pass_rate")),
    )
    if not constant_time_compare(receipt.receipt_id, _required("receipt_id", data.get("receipt_id"))):
        raise ValueError("promotion_receipt_id_mismatch")
    return receipt


def rehydrate_model_selection_receipt(data: Mapping[str, Any]) -> ModelSelectionReceipt:
    """Rehydrate a selection receipt and verify its deterministic digest."""

    if data.get("schema_version") != "model_selection_receipt.v1":
        raise ValueError("invalid_selection_schema")
    requirements = _rehydrate_requirements(_mapping_value(data.get("requirements"), "requirements"))
    decision = SelectionDecision(_required("decision", data.get("decision")))
    rankings = tuple(_rehydrate_ranking(item) for item in _list_value(data.get("rankings"), "rankings"))
    assignments = tuple(_rehydrate_assignment(item) for item in _list_value(data.get("role_assignments", []), "role_assignments"))
    receipt = ModelSelectionReceipt(
        receipt_id=_required("receipt_id", data.get("receipt_id")),
        catalog_snapshot_id=_required("catalog_snapshot_id", data.get("catalog_snapshot_id")),
        requirements=requirements,
        decision=decision,
        selected_model_ids=tuple(str(value) for value in _list_value(data.get("selected_model_ids"), "selected_model_ids")),
        rankings=rankings,
        role_assignments=assignments,
        panel_topology_digest=_optional(data.get("panel_topology_digest")),
        rejection_reasons=tuple(str(value) for value in _list_value(data.get("rejection_reasons", []), "rejection_reasons")),
    )
    body = {
        "schema_version": receipt.schema_version,
        "catalog_snapshot_id": receipt.catalog_snapshot_id,
        "requirements": _requirements_to_json(receipt.requirements),
        "decision": receipt.decision.value,
        "selected_model_ids": list(receipt.selected_model_ids),
        "rankings": [asdict(item) for item in receipt.rankings],
        "role_assignments": [asdict(item) for item in receipt.role_assignments],
        "panel_topology_digest": receipt.panel_topology_digest,
        "rejection_reasons": list(receipt.rejection_reasons),
    }
    if not constant_time_compare(_digest_prefixed("model_selection_receipt", body), receipt.receipt_id):
        raise ValueError("selection_receipt_id_mismatch")
    return receipt


def rehydrate_model_runtime_binding_receipt(data: Mapping[str, Any]) -> RedDogModelRuntimeBindingReceipt:
    """Rehydrate a runtime binding receipt and verify its deterministic digest."""

    if data.get("schema_version") != "reddog_model_runtime_binding_receipt.v1":
        raise ValueError("invalid_runtime_binding_schema")
    policy = _rehydrate_runtime_policy(_mapping_value(data.get("policy"), "policy"))
    receipt = RedDogModelRuntimeBindingReceipt(
        receipt_id=_required("receipt_id", data.get("receipt_id")),
        decision=ModelRuntimeBindingDecision(_required("decision", data.get("decision"))),
        runtime_surface=_required("runtime_surface", data.get("runtime_surface")),
        catalog_snapshot_id=_required("catalog_snapshot_id", data.get("catalog_snapshot_id")),
        selection_receipt_id=_required("selection_receipt_id", data.get("selection_receipt_id")),
        task_family=_required("task_family", data.get("task_family")),
        principal_model=_optional(data.get("principal_model")),
        panel_models=tuple(str(value) for value in _list_value(data.get("panel_models", []), "panel_models")),
        role_bindings=tuple(_rehydrate_runtime_role(item) for item in _list_value(data.get("role_bindings", []), "role_bindings")),
        benchmark_evidence_receipt_ids=tuple(str(value) for value in _list_value(data.get("benchmark_evidence_receipt_ids", []), "benchmark_evidence_receipt_ids")),
        promotion_evidence_receipt_ids=tuple(str(value) for value in _list_value(data.get("promotion_evidence_receipt_ids", []), "promotion_evidence_receipt_ids")),
        signed_promotion_receipt_ids=tuple(str(value) for value in _list_value(data.get("signed_promotion_receipt_ids", []), "signed_promotion_receipt_ids")),
        policy=policy,
        rejection_reasons=tuple(str(value) for value in _list_value(data.get("rejection_reasons", []), "rejection_reasons")),
    )
    body = {
        "schema_version": receipt.schema_version,
        "decision": receipt.decision.value,
        "runtime_surface": receipt.runtime_surface,
        "catalog_snapshot_id": receipt.catalog_snapshot_id,
        "selection_receipt_id": receipt.selection_receipt_id,
        "task_family": receipt.task_family,
        "principal_model": receipt.principal_model,
        "panel_models": list(receipt.panel_models),
        "role_bindings": [binding.to_dict() for binding in receipt.role_bindings],
        "benchmark_evidence_receipt_ids": list(receipt.benchmark_evidence_receipt_ids),
        "promotion_evidence_receipt_ids": list(receipt.promotion_evidence_receipt_ids),
        "signed_promotion_receipt_ids": list(receipt.signed_promotion_receipt_ids),
        "policy": policy.to_dict(),
        "rejection_reasons": list(receipt.rejection_reasons),
    }
    if not constant_time_compare(_digest_prefixed("reddog_model_runtime_binding", body), receipt.receipt_id):
        raise ValueError("runtime_binding_receipt_id_mismatch")
    return receipt


def rehydrate_model_signed_evidence_receipt(data: Mapping[str, Any]) -> ModelSignedEvidenceReceipt:
    """Rehydrate signed evidence and recompute its receipt ID."""

    if data.get("schema_version") != SIGNED_EVIDENCE_SCHEMA_VERSION:
        raise ValueError("invalid_signed_evidence_schema")
    receipt = build_model_signed_evidence_receipt(
        signer_role=_required("signer_role", data.get("signer_role")),
        signer_public_key=_required("signer_public_key", data.get("signer_public_key")),
        signer_key_fingerprint=_required("signer_key_fingerprint", data.get("signer_key_fingerprint")),
        key_epoch=_required("key_epoch", data.get("key_epoch")),
        subject_type=_required("subject_type", data.get("subject_type")),
        model_or_panel_subject=_required("model_or_panel_subject", data.get("model_or_panel_subject")),
        catalog_snapshot_id=_required("catalog_snapshot_id", data.get("catalog_snapshot_id")),
        selection_receipt_id=_required("selection_receipt_id", data.get("selection_receipt_id")),
        benchmark_run_receipt_id=_required("benchmark_run_receipt_id", data.get("benchmark_run_receipt_id")),
        benchmark_evidence_receipt_id=_required(
            "benchmark_evidence_receipt_id",
            data.get("benchmark_evidence_receipt_id"),
        ),
        task_family=_required("task_family", data.get("task_family")),
        task_set_digest=_required("task_set_digest", data.get("task_set_digest")),
        held_out_split_digest=_required("held_out_split_digest", data.get("held_out_split_digest")),
        verifier_digest=_required("verifier_digest", data.get("verifier_digest")),
        prompt_topology_digest=_required("prompt_topology_digest", data.get("prompt_topology_digest")),
        promotion_evidence_receipt_id=_optional(data.get("promotion_evidence_receipt_id")),
        promotion_policy_digest=_optional(data.get("promotion_policy_digest")),
        issued_at=_int_value(data.get("issued_at"), "issued_at"),
        expires_at=_int_value(data.get("expires_at"), "expires_at"),
        nonce=_required("nonce", data.get("nonce")),
        signature=_required("signature", data.get("signature")),
    )
    if not constant_time_compare(receipt.receipt_id, _required("receipt_id", data.get("receipt_id"))):
        raise ValueError("signed_evidence_receipt_id_mismatch")
    return receipt


def verify_model_signed_evidence_receipt(
    receipt: ModelSignedEvidenceReceipt,
    *,
    expected_role: ModelEvidenceSignerRole | str,
    key_resolver: ModelEvidenceKeyResolver,
    signature_verifier: SignatureVerifier,
    now: int,
    nonce_store: NonceStore | None = None,
    consume_nonce: bool = False,
    revoked_key_epochs: Sequence[str] = (),
    leeway_s: int = 60,
) -> SignedEvidenceVerificationResult:
    """Verify role, trust anchor, TTL, revocation, signature and optional nonce."""

    reasons: list[str] = []
    role = _coerce_role(expected_role)
    if receipt.signer_role != role:
        reasons.append("signer_role_mismatch")
    if receipt.key_epoch in {str(value) for value in revoked_key_epochs}:
        reasons.append("key_epoch_revoked")
    trusted_key = None
    try:
        trusted_key = key_resolver.resolve(
            receipt.signer_role.value,
            receipt.signer_key_fingerprint,
            receipt.key_epoch,
        )
    except Exception:
        trusted_key = None
    if not trusted_key or not constant_time_compare(str(trusted_key), receipt.signer_public_key):
        reasons.append("signer_key_untrusted")
    if now + leeway_s < receipt.issued_at:
        reasons.append("issued_in_future")
    if now > receipt.expires_at + leeway_s:
        reasons.append("signed_evidence_expired")
    try:
        signature_ok = signature_verifier.verify(
            receipt.signer_public_key,
            model_signed_evidence_signing_input(receipt),
            receipt.signature,
        ) is True
    except Exception:
        signature_ok = False
    if not signature_ok:
        reasons.append("signature_invalid")
    if reasons:
        return SignedEvidenceVerificationResult(False, tuple(sorted(set(reasons))))
    if consume_nonce:
        if nonce_store is None:
            return SignedEvidenceVerificationResult(False, ("nonce_store_missing",))
        try:
            if not nonce_store.consume(receipt.nonce):
                return SignedEvidenceVerificationResult(False, ("nonce_replay",))
        except Exception:
            return SignedEvidenceVerificationResult(False, ("nonce_replay",))
    return SignedEvidenceVerificationResult(True, ())


def build_verified_model_production_evidence(
    *,
    catalog_snapshot_id: str,
    selection_receipt_id: str,
    benchmark_run_receipt_id: str,
    benchmark_receipt: ModelBenchmarkEvidenceReceipt | Mapping[str, Any],
    promotion_receipt: ModelPromotionEvidenceReceipt | Mapping[str, Any],
    benchmark_signature_receipt: ModelSignedEvidenceReceipt | Mapping[str, Any],
    promotion_signature_receipt: ModelSignedEvidenceReceipt | Mapping[str, Any],
    key_resolver: ModelEvidenceKeyResolver,
    signature_verifier: SignatureVerifier,
    now: int,
    nonce_store: NonceStore | None = None,
    consume_nonces: bool = False,
    revoked_key_epochs: Sequence[str] = (),
    leeway_s: int = 60,
) -> VerifiedModelProductionEvidence:
    """Verify one single-model production evidence chain and return typed evidence."""

    benchmark = (
        benchmark_receipt
        if isinstance(benchmark_receipt, ModelBenchmarkEvidenceReceipt)
        else rehydrate_model_benchmark_evidence_receipt(benchmark_receipt)
    )
    promotion = (
        promotion_receipt
        if isinstance(promotion_receipt, ModelPromotionEvidenceReceipt)
        else rehydrate_model_promotion_evidence_receipt(promotion_receipt, benchmark_receipt=benchmark)
    )
    benchmark_sig = (
        benchmark_signature_receipt
        if isinstance(benchmark_signature_receipt, ModelSignedEvidenceReceipt)
        else rehydrate_model_signed_evidence_receipt(benchmark_signature_receipt)
    )
    promotion_sig = (
        promotion_signature_receipt
        if isinstance(promotion_signature_receipt, ModelSignedEvidenceReceipt)
        else rehydrate_model_signed_evidence_receipt(promotion_signature_receipt)
    )
    _assert_single_model_chain(
        catalog_snapshot_id=catalog_snapshot_id,
        selection_receipt_id=selection_receipt_id,
        benchmark_run_receipt_id=benchmark_run_receipt_id,
        benchmark=benchmark,
        promotion=promotion,
        benchmark_sig=benchmark_sig,
        promotion_sig=promotion_sig,
    )
    benchmark_result = verify_model_signed_evidence_receipt(
        benchmark_sig,
        expected_role=ModelEvidenceSignerRole.BENCHMARK_VERIFIER,
        key_resolver=key_resolver,
        signature_verifier=signature_verifier,
        now=now,
        nonce_store=nonce_store,
        consume_nonce=consume_nonces,
        revoked_key_epochs=revoked_key_epochs,
        leeway_s=leeway_s,
    )
    if not benchmark_result.accepted:
        raise ValueError("benchmark_signed_evidence_rejected:" + ",".join(benchmark_result.reason_codes))
    promotion_result = verify_model_signed_evidence_receipt(
        promotion_sig,
        expected_role=ModelEvidenceSignerRole.PROMOTION_AUTHORITY,
        key_resolver=key_resolver,
        signature_verifier=signature_verifier,
        now=now,
        nonce_store=nonce_store,
        consume_nonce=consume_nonces,
        revoked_key_epochs=revoked_key_epochs,
        leeway_s=leeway_s,
    )
    if not promotion_result.accepted:
        raise ValueError("promotion_signed_evidence_rejected:" + ",".join(promotion_result.reason_codes))
    return VerifiedModelProductionEvidence(
        entries=(
            VerifiedModelEvidenceEntry(
                model_id=benchmark.model_id,
                benchmark_receipt=benchmark,
                promotion_receipt=promotion,
                benchmark_signature_receipt=benchmark_sig,
                promotion_signature_receipt=promotion_sig,
            ),
        )
    )


def _assert_single_model_chain(
    *,
    catalog_snapshot_id: str,
    selection_receipt_id: str,
    benchmark_run_receipt_id: str,
    benchmark: ModelBenchmarkEvidenceReceipt,
    promotion: ModelPromotionEvidenceReceipt,
    benchmark_sig: ModelSignedEvidenceReceipt,
    promotion_sig: ModelSignedEvidenceReceipt,
) -> None:
    if benchmark.model_id != promotion.model_id:
        raise ValueError("promotion_model_mismatch")
    if benchmark.task_family != promotion.task_family:
        raise ValueError("promotion_task_mismatch")
    if promotion.benchmark_evidence_receipt_id != benchmark.receipt_id:
        raise ValueError("promotion_benchmark_mismatch")
    if benchmark_sig.subject_type != ModelEvidenceSubjectType.MODEL or promotion_sig.subject_type != ModelEvidenceSubjectType.MODEL:
        raise ValueError("panel_signed_evidence_deferred")
    for receipt in (benchmark_sig, promotion_sig):
        if receipt.model_or_panel_subject != benchmark.model_id:
            raise ValueError("signed_evidence_subject_mismatch")
        if receipt.catalog_snapshot_id != catalog_snapshot_id:
            raise ValueError("signed_evidence_catalog_mismatch")
        if receipt.selection_receipt_id != selection_receipt_id:
            raise ValueError("signed_evidence_selection_mismatch")
        if receipt.benchmark_run_receipt_id != benchmark_run_receipt_id:
            raise ValueError("signed_evidence_benchmark_run_mismatch")
        if receipt.benchmark_evidence_receipt_id != benchmark.receipt_id:
            raise ValueError("signed_evidence_benchmark_mismatch")
        if receipt.task_family != benchmark.task_family:
            raise ValueError("signed_evidence_task_mismatch")
        if receipt.task_set_digest != benchmark.task_set_digest:
            raise ValueError("signed_evidence_task_set_mismatch")
        if receipt.held_out_split_digest != benchmark.held_out_split_digest:
            raise ValueError("signed_evidence_held_out_mismatch")
        if receipt.verifier_digest != benchmark.verifier_digest:
            raise ValueError("signed_evidence_verifier_mismatch")
        if receipt.prompt_topology_digest != benchmark.prompt_topology_digest:
            raise ValueError("signed_evidence_topology_mismatch")
    if promotion_sig.promotion_evidence_receipt_id != promotion.receipt_id:
        raise ValueError("signed_evidence_promotion_mismatch")
    if not promotion_sig.promotion_policy_digest:
        raise ValueError("missing_promotion_policy_digest")


def _rehydrate_card(data: Mapping[str, Any]) -> ModelCapabilityCard:
    if data.get("schema_version") != "model_capability_card.v1":
        raise ValueError("invalid_card_schema")
    return ModelCapabilityCard(
        provider=_required("provider", data.get("provider")),
        model_id=_required("model_id", data.get("model_id")),
        canonical_model_id=_required("canonical_model_id", data.get("canonical_model_id")),
        source=_required("source", data.get("source")),
        availability=Availability(_required("availability", data.get("availability"))),
        freshness=_required("freshness", data.get("freshness")),
        promotion_state=PromotionState(_required("promotion_state", data.get("promotion_state"))),
        task_families=tuple(str(value) for value in _list_value(data.get("task_families", []), "task_families")),
        context_window=data.get("context_window"),
        input_cost_per_million=data.get("input_cost_per_million"),
        output_cost_per_million=data.get("output_cost_per_million"),
        supports_tools=bool(data.get("supports_tools")),
        supports_structured_output=bool(data.get("supports_structured_output")),
        supports_reasoning=bool(data.get("supports_reasoning")),
        modalities=tuple(str(value) for value in _list_value(data.get("modalities", []), "modalities")),
        supported_parameters=tuple(str(value) for value in _list_value(data.get("supported_parameters", []), "supported_parameters")),
        privacy_policy=_required("privacy_policy", data.get("privacy_policy")),
        verifier_pass_rate=data.get("verifier_pass_rate"),
        benchmark_scores=_mapping_value(data.get("benchmark_scores", {}), "benchmark_scores"),
    ).normalized()


def _rehydrate_rejected_record(data: Mapping[str, Any]) -> ModelCatalogRejectedRecord:
    return ModelCatalogRejectedRecord(
        source=_required("source", data.get("source")),
        reason=_required("reason", data.get("reason")),
        record_digest=_required("record_digest", data.get("record_digest")),
    )


def _rehydrate_requirements(data: Mapping[str, Any]) -> ModelTaskRequirements:
    return ModelTaskRequirements(
        task_family=_required("task_family", data.get("task_family")),
        selection_mode=SelectionMode(_required("selection_mode", data.get("selection_mode"))),
        purpose=SelectionPurpose(_required("purpose", data.get("purpose"))),
        required_modalities=tuple(str(value) for value in _list_value(data.get("required_modalities", []), "required_modalities")),
        min_context_window=data.get("min_context_window"),
        require_tools=bool(data.get("require_tools")),
        require_structured_output=bool(data.get("require_structured_output")),
        require_reasoning=bool(data.get("require_reasoning")),
        max_input_cost_per_million=data.get("max_input_cost_per_million"),
        max_output_cost_per_million=data.get("max_output_cost_per_million"),
        allowed_providers=tuple(str(value) for value in _list_value(data.get("allowed_providers", []), "allowed_providers")),
        denied_providers=tuple(str(value) for value in _list_value(data.get("denied_providers", []), "denied_providers")),
        max_candidates=_int_value(data.get("max_candidates"), "max_candidates"),
        min_verifier_pass_rate=data.get("min_verifier_pass_rate"),
        panel_roles=tuple(str(value) for value in _list_value(data.get("panel_roles", []), "panel_roles")),
        panel_topology_digest=_optional(data.get("panel_topology_digest")),
    ).normalized()


def _rehydrate_ranking(data: Mapping[str, Any]) -> ModelCandidateRanking:
    return ModelCandidateRanking(
        canonical_model_id=_required("canonical_model_id", data.get("canonical_model_id")),
        provider=_required("provider", data.get("provider")),
        score=float(data.get("score")),
        reasons=tuple(str(value) for value in _list_value(data.get("reasons", []), "reasons")),
    )


def _rehydrate_assignment(data: Mapping[str, Any]) -> ModelPanelRoleAssignment:
    return ModelPanelRoleAssignment(
        role=_required("role", data.get("role")),
        canonical_model_id=_required("canonical_model_id", data.get("canonical_model_id")),
        provider=_required("provider", data.get("provider")),
    )


def _rehydrate_runtime_policy(data: Mapping[str, Any]) -> ModelRuntimeBindingPolicy:
    return ModelRuntimeBindingPolicy(
        task_family=_required("task_family", data.get("task_family")),
        runtime_surface=_required("runtime_surface", data.get("runtime_surface")),
        min_verifier_pass_rate=float(data.get("min_verifier_pass_rate")),
        required_task_set_digest=_required("required_task_set_digest", data.get("required_task_set_digest")),
        required_held_out_split_digest=_required(
            "required_held_out_split_digest",
            data.get("required_held_out_split_digest"),
        ),
        required_verifier_digest=_required("required_verifier_digest", data.get("required_verifier_digest")),
        max_panel_models=_int_value(data.get("max_panel_models"), "max_panel_models"),
        required_panel_topology_digest=_optional(data.get("required_panel_topology_digest")),
        authority_receipt_id=_optional(data.get("authority_receipt_id")),
    ).normalized()


def _rehydrate_runtime_role(data: Mapping[str, Any]) -> RuntimeModelRoleBinding:
    return RuntimeModelRoleBinding(
        role=_required("role", data.get("role")),
        model_id=_required("model_id", data.get("model_id")),
        provider=_required("provider", data.get("provider")),
    )


def _requirements_to_json(requirements: ModelTaskRequirements) -> dict[str, Any]:
    normalized = requirements.normalized()
    return {
        "task_family": normalized.task_family,
        "selection_mode": normalized.selection_mode.value,
        "purpose": normalized.purpose.value,
        "required_modalities": list(normalized.required_modalities),
        "min_context_window": normalized.min_context_window,
        "require_tools": normalized.require_tools,
        "require_structured_output": normalized.require_structured_output,
        "require_reasoning": normalized.require_reasoning,
        "max_input_cost_per_million": normalized.max_input_cost_per_million,
        "max_output_cost_per_million": normalized.max_output_cost_per_million,
        "allowed_providers": list(normalized.allowed_providers),
        "denied_providers": list(normalized.denied_providers),
        "max_candidates": normalized.max_candidates,
        "min_verifier_pass_rate": normalized.min_verifier_pass_rate,
        "panel_roles": list(normalized.panel_roles),
        "panel_topology_digest": normalized.panel_topology_digest,
    }


def _coerce_role(value: ModelEvidenceSignerRole | str) -> ModelEvidenceSignerRole:
    if isinstance(value, ModelEvidenceSignerRole):
        return value
    return ModelEvidenceSignerRole(str(value).strip())


def _coerce_subject_type(value: ModelEvidenceSubjectType | str) -> ModelEvidenceSubjectType:
    if isinstance(value, ModelEvidenceSubjectType):
        return value
    return ModelEvidenceSubjectType(str(value).strip())


def _mapping_value(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"invalid_{name}")
    return value


def _list_value(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"invalid_{name}")
    return value


def _required(name: str, value: Any) -> str:
    cleaned = str(value).strip() if value is not None else ""
    if not cleaned:
        raise ValueError(f"missing_{name}")
    return cleaned


def _optional(value: Any) -> str | None:
    cleaned = str(value).strip() if value is not None else ""
    return cleaned or None


def _int_value(value: Any, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid_{name}") from exc


def _clean_token(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _digest_prefixed(prefix: str, value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


__all__ = [
    "InMemoryEvidenceNonceStore",
    "ModelEvidenceKeyResolver",
    "ModelEvidenceSignerRole",
    "ModelEvidenceSubjectType",
    "ModelSignedEvidenceReceipt",
    "PREFIX_MODEL_SIGNED_EVIDENCE",
    "SignedEvidenceVerificationResult",
    "StaticModelEvidenceKeyResolver",
    "VerifiedModelEvidenceEntry",
    "VerifiedModelProductionEvidence",
    "build_model_signed_evidence_receipt",
    "build_verified_model_production_evidence",
    "model_signed_evidence_signing_input",
    "rehydrate_model_benchmark_evidence_receipt",
    "rehydrate_model_catalog_snapshot",
    "rehydrate_model_promotion_evidence_receipt",
    "rehydrate_model_runtime_binding_receipt",
    "rehydrate_model_selection_receipt",
    "rehydrate_model_signed_evidence_receipt",
    "verify_model_signed_evidence_receipt",
]
