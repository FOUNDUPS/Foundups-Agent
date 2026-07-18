"""Signed aggregate evidence for production model panels.

The aggregate is intentionally separate from single-model signed evidence.  A
panel is admitted only after every member's existing benchmark/promotion chain
has been independently verified.  The aggregate then binds the exact ordered
role/model/provider topology and its runtime context before its own signature
and optional single-use nonce are checked.

This module does not sign, choose models, call providers, execute commands,
mutate catalogs, persist runtime defaults, or wire a Fusion consumer.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    NonceStore,
    SignatureVerifier,
    canonical_signing_input,
    constant_time_compare,
)

from .model_intelligence_catalog import ModelCatalogSnapshot
from .model_intelligence_outcomes import ModelBenchmarkEvidenceReceipt, ModelPromotionEvidenceReceipt
from .model_intelligence_selection import ModelSelectionReceipt, SelectionDecision, SelectionMode, SelectionPurpose
from .model_runtime_binding import ModelRuntimeBindingPolicy
from .model_signed_evidence import (
    ModelEvidenceKeyResolver,
    ModelSignedEvidenceReceipt,
    VerifiedModelEvidenceEntry,
    VerifiedModelProductionEvidence,
    build_verified_model_production_evidence,
)


PANEL_EVIDENCE_SCHEMA_VERSION = "model_panel_signed_evidence_receipt.v1"
VERIFIED_PANEL_EVIDENCE_SCHEMA_VERSION = "verified_model_panel_evidence.v1"
PANEL_SIGNING_PREFIX = "reddog-model-panel-evidence.v1"
PANEL_SUBJECT_TYPE = "panel"
_VERIFIED_MARKER = object()
_PANEL_STRING_FIELDS = (
    "synthesizer_model_id",
    "synthesizer_role",
    "catalog_snapshot_id",
    "catalog_snapshot_digest",
    "selection_receipt_id",
    "selection_receipt_digest",
    "task_receipt_id",
    "task_receipt_digest",
    "topology_receipt_id",
    "topology_receipt_digest",
    "policy_receipt_id",
    "policy_receipt_digest",
    "runtime_surface_receipt_id",
    "runtime_surface_receipt_digest",
    "benchmark_run_receipt_id",
    "signer_public_key",
    "signer_key_fingerprint",
    "key_epoch",
    "nonce",
    "signature",
)


class PanelEvidenceSignerRole(str, Enum):
    """Signer role authorized to attest a complete panel topology."""

    PANEL_AUTHORITY = "panel_authority"


@dataclass(frozen=True)
class PanelMemberEvidenceInput:
    """Independent signed single-model chain assigned to one panel role."""

    role: str
    model_id: str
    provider: str
    benchmark_receipt: ModelBenchmarkEvidenceReceipt | Mapping[str, Any]
    promotion_receipt: ModelPromotionEvidenceReceipt | Mapping[str, Any]
    benchmark_signature_receipt: ModelSignedEvidenceReceipt | Mapping[str, Any]
    promotion_signature_receipt: ModelSignedEvidenceReceipt | Mapping[str, Any]


@dataclass(frozen=True)
class PanelMemberEvidenceBinding:
    """Digest-bound projection of one independently verified member chain."""

    ordinal: int
    role: str
    model_id: str
    provider: str
    member_evidence_id: str
    member_evidence_digest: str
    benchmark_evidence_receipt_id: str
    benchmark_evidence_digest: str
    promotion_evidence_receipt_id: str
    promotion_evidence_digest: str
    benchmark_signed_evidence_receipt_id: str
    benchmark_signed_evidence_digest: str
    promotion_signed_evidence_receipt_id: str
    promotion_signed_evidence_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "role": self.role,
            "model_id": self.model_id,
            "provider": self.provider,
            "member_evidence_id": self.member_evidence_id,
            "member_evidence_digest": self.member_evidence_digest,
            "benchmark_evidence_receipt_id": self.benchmark_evidence_receipt_id,
            "benchmark_evidence_digest": self.benchmark_evidence_digest,
            "promotion_evidence_receipt_id": self.promotion_evidence_receipt_id,
            "promotion_evidence_digest": self.promotion_evidence_digest,
            "benchmark_signed_evidence_receipt_id": self.benchmark_signed_evidence_receipt_id,
            "benchmark_signed_evidence_digest": self.benchmark_signed_evidence_digest,
            "promotion_signed_evidence_receipt_id": self.promotion_signed_evidence_receipt_id,
            "promotion_signed_evidence_digest": self.promotion_signed_evidence_digest,
        }


@dataclass(frozen=True)
class ModelPanelSignedEvidenceReceipt:
    """Signed envelope over an exact ordered production panel and context."""

    receipt_id: str
    panel_subject_id: str
    members: tuple[PanelMemberEvidenceBinding, ...]
    required_roles: tuple[str, ...]
    synthesizer_model_id: str
    synthesizer_role: str
    catalog_snapshot_id: str
    catalog_snapshot_digest: str
    selection_receipt_id: str
    selection_receipt_digest: str
    task_receipt_id: str
    task_receipt_digest: str
    topology_receipt_id: str
    topology_receipt_digest: str
    policy_receipt_id: str
    policy_receipt_digest: str
    runtime_surface_receipt_id: str
    runtime_surface_receipt_digest: str
    benchmark_run_receipt_id: str
    signer_role: PanelEvidenceSignerRole
    signer_public_key: str
    signer_key_fingerprint: str
    key_epoch: str
    issued_at: int
    expires_at: int
    nonce: str
    signature: str
    subject_type: str = PANEL_SUBJECT_TYPE
    schema_version: str = PANEL_EVIDENCE_SCHEMA_VERSION

    def to_signed_record(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "subject_type": self.subject_type,
            "panel_subject_id": self.panel_subject_id,
            "members": [member.to_dict() for member in self.members],
            "required_roles": list(self.required_roles),
            "synthesizer_model_id": self.synthesizer_model_id,
            "synthesizer_role": self.synthesizer_role,
            "catalog_snapshot_id": self.catalog_snapshot_id,
            "catalog_snapshot_digest": self.catalog_snapshot_digest,
            "selection_receipt_id": self.selection_receipt_id,
            "selection_receipt_digest": self.selection_receipt_digest,
            "task_receipt_id": self.task_receipt_id,
            "task_receipt_digest": self.task_receipt_digest,
            "topology_receipt_id": self.topology_receipt_id,
            "topology_receipt_digest": self.topology_receipt_digest,
            "policy_receipt_id": self.policy_receipt_id,
            "policy_receipt_digest": self.policy_receipt_digest,
            "runtime_surface_receipt_id": self.runtime_surface_receipt_id,
            "runtime_surface_receipt_digest": self.runtime_surface_receipt_digest,
            "benchmark_run_receipt_id": self.benchmark_run_receipt_id,
            "signer_role": self.signer_role.value,
            "signer_public_key": self.signer_public_key,
            "signer_key_fingerprint": self.signer_key_fingerprint,
            "key_epoch": self.key_epoch,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "signature": self.signature,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"receipt_id": self.receipt_id, **self.to_signed_record()}


@dataclass(frozen=True)
class VerifiedModelPanelEvidence:
    """Opaque factory result accepted by PANEL runtime binding."""

    aggregate_receipt: ModelPanelSignedEvidenceReceipt
    member_entries: tuple[VerifiedModelEvidenceEntry, ...]
    _marker: object
    schema_version: str = VERIFIED_PANEL_EVIDENCE_SCHEMA_VERSION

    @property
    def signed_evidence_verified(self) -> bool:
        return self._marker is _VERIFIED_MARKER

    @property
    def panel_signed_evidence_verified(self) -> bool:
        return self._marker is _VERIFIED_MARKER

    def model_ids(self) -> tuple[str, ...]:
        return tuple(member.model_id for member in self.aggregate_receipt.members)

    def selection_receipt_ids(self) -> tuple[str, ...]:
        return (self.aggregate_receipt.selection_receipt_id,)


def build_panel_member_evidence_binding(
    *,
    ordinal: int,
    role: str,
    model_id: str,
    provider: str,
    verified_evidence: VerifiedModelProductionEvidence,
) -> PanelMemberEvidenceBinding:
    """Project one already-verified single-model chain for panel signing."""

    if not isinstance(verified_evidence, VerifiedModelProductionEvidence) or not verified_evidence.signed_evidence_verified:
        raise ValueError("member_evidence_not_verified")
    if len(verified_evidence.entries) != 1:
        raise ValueError("member_evidence_entry_count_invalid")
    entry = verified_evidence.entries[0]
    source = PanelMemberEvidenceInput(
        role=role,
        model_id=model_id,
        provider=provider,
        benchmark_receipt=entry.benchmark_receipt,
        promotion_receipt=entry.promotion_receipt,
        benchmark_signature_receipt=entry.benchmark_signature_receipt,
        promotion_signature_receipt=entry.promotion_signature_receipt,
    )
    return _binding_from_entry(int(ordinal), source, entry)


def build_model_panel_signed_evidence_receipt(
    *,
    members: Sequence[PanelMemberEvidenceBinding | Mapping[str, Any]],
    required_roles: Sequence[str], synthesizer_model_id: str, synthesizer_role: str,
    catalog_snapshot_id: str, catalog_snapshot_digest: str,
    selection_receipt_id: str, selection_receipt_digest: str,
    task_receipt_id: str, task_receipt_digest: str,
    topology_receipt_id: str, topology_receipt_digest: str,
    policy_receipt_id: str, policy_receipt_digest: str,
    runtime_surface_receipt_id: str, runtime_surface_receipt_digest: str,
    benchmark_run_receipt_id: str, signer_role: PanelEvidenceSignerRole | str,
    signer_public_key: str, signer_key_fingerprint: str, key_epoch: str,
    issued_at: int, expires_at: int, nonce: str, signature: str,
) -> ModelPanelSignedEvidenceReceipt:
    """Build a deterministic aggregate receipt from an already-issued signature."""

    raw = locals()
    bindings = tuple(_member_binding(value) for value in members)
    role = PanelEvidenceSignerRole(str(getattr(signer_role, "value", signer_role)))
    body = {
        "schema_version": PANEL_EVIDENCE_SCHEMA_VERSION,
        "subject_type": PANEL_SUBJECT_TYPE,
        "panel_subject_id": _panel_subject_id(bindings),
        "members": [member.to_dict() for member in bindings],
        "required_roles": [_required("required_role", value) for value in required_roles],
        "signer_role": role.value,
        "issued_at": int(issued_at),
        "expires_at": int(expires_at),
    }
    body.update({name: _required(name, raw[name]) for name in _PANEL_STRING_FIELDS})
    if body["expires_at"] <= body["issued_at"]:
        raise ValueError("invalid_panel_evidence_ttl")
    body["receipt_id"] = _digest_id("model_panel_signed_evidence", body)
    body["members"] = bindings
    body["required_roles"] = tuple(body["required_roles"])
    body["signer_role"] = role
    return ModelPanelSignedEvidenceReceipt(**body)


def model_panel_signed_evidence_signing_input(
    receipt_or_record: ModelPanelSignedEvidenceReceipt | Mapping[str, Any],
) -> str:
    record = receipt_or_record.to_signed_record() if isinstance(receipt_or_record, ModelPanelSignedEvidenceReceipt) else dict(receipt_or_record)
    return canonical_signing_input(record, PANEL_SIGNING_PREFIX)


def rehydrate_model_panel_signed_evidence_receipt(data: Mapping[str, Any]) -> ModelPanelSignedEvidenceReceipt:
    """Rehydrate an aggregate receipt and recompute its deterministic ID."""

    if data.get("schema_version") != PANEL_EVIDENCE_SCHEMA_VERSION or data.get("subject_type") != PANEL_SUBJECT_TYPE:
        raise ValueError("invalid_panel_evidence_schema")
    receipt = build_model_panel_signed_evidence_receipt(
        members=_list(data, "members"),
        required_roles=_list(data, "required_roles"),
        synthesizer_model_id=data.get("synthesizer_model_id"),
        synthesizer_role=data.get("synthesizer_role"),
        catalog_snapshot_id=data.get("catalog_snapshot_id"),
        catalog_snapshot_digest=data.get("catalog_snapshot_digest"),
        selection_receipt_id=data.get("selection_receipt_id"),
        selection_receipt_digest=data.get("selection_receipt_digest"),
        task_receipt_id=data.get("task_receipt_id"),
        task_receipt_digest=data.get("task_receipt_digest"),
        topology_receipt_id=data.get("topology_receipt_id"),
        topology_receipt_digest=data.get("topology_receipt_digest"),
        policy_receipt_id=data.get("policy_receipt_id"),
        policy_receipt_digest=data.get("policy_receipt_digest"),
        runtime_surface_receipt_id=data.get("runtime_surface_receipt_id"),
        runtime_surface_receipt_digest=data.get("runtime_surface_receipt_digest"),
        benchmark_run_receipt_id=data.get("benchmark_run_receipt_id"),
        signer_role=data.get("signer_role"),
        signer_public_key=data.get("signer_public_key"),
        signer_key_fingerprint=data.get("signer_key_fingerprint"),
        key_epoch=data.get("key_epoch"),
        issued_at=data.get("issued_at"),
        expires_at=data.get("expires_at"),
        nonce=data.get("nonce"),
        signature=data.get("signature"),
    )
    if receipt.panel_subject_id != data.get("panel_subject_id"):
        raise ValueError("panel_subject_id_mismatch")
    if not constant_time_compare(receipt.receipt_id, _required("receipt_id", data.get("receipt_id"))):
        raise ValueError("panel_evidence_receipt_id_mismatch")
    return receipt


def build_verified_model_panel_evidence(
    *,
    catalog_snapshot: ModelCatalogSnapshot, selection_receipt: ModelSelectionReceipt,
    member_inputs: Sequence[PanelMemberEvidenceInput],
    aggregate_receipt: ModelPanelSignedEvidenceReceipt | Mapping[str, Any],
    runtime_policy: ModelRuntimeBindingPolicy, task_receipt_id: str,
    topology_receipt_id: str, policy_receipt_id: str,
    runtime_surface_receipt_id: str, member_key_resolver: ModelEvidenceKeyResolver,
    member_signature_verifier: SignatureVerifier, panel_key_resolver: ModelEvidenceKeyResolver,
    panel_signature_verifier: SignatureVerifier, now: int,
    nonce_store: NonceStore | None = None, consume_nonce: bool = False,
    revoked_member_key_epochs: Sequence[str] = (), revoked_panel_key_epochs: Sequence[str] = (),
    leeway_s: int = 60,
) -> VerifiedModelPanelEvidence:
    """Verify member chains first, then the aggregate envelope and nonce last."""

    receipt = aggregate_receipt if isinstance(aggregate_receipt, ModelPanelSignedEvidenceReceipt) else rehydrate_model_panel_signed_evidence_receipt(aggregate_receipt)
    entries, bindings = _verify_member_inputs(
        catalog_snapshot_id=catalog_snapshot.snapshot_id,
        selection_receipt_id=selection_receipt.receipt_id,
        benchmark_run_receipt_id=receipt.benchmark_run_receipt_id,
        member_inputs=member_inputs,
        key_resolver=member_key_resolver,
        signature_verifier=member_signature_verifier,
        now=now,
        revoked_key_epochs=revoked_member_key_epochs,
        leeway_s=leeway_s,
    )
    _assert_panel_context(
        catalog_snapshot=catalog_snapshot,
        selection_receipt=selection_receipt,
        bindings=bindings,
        entries=entries,
        receipt=receipt,
        runtime_policy=runtime_policy,
        task_receipt_id=task_receipt_id,
        topology_receipt_id=topology_receipt_id,
        policy_receipt_id=policy_receipt_id,
        runtime_surface_receipt_id=runtime_surface_receipt_id,
    )
    _verify_panel_signature(
        receipt,
        key_resolver=panel_key_resolver,
        signature_verifier=panel_signature_verifier,
        now=now,
        revoked_key_epochs=revoked_panel_key_epochs,
        leeway_s=leeway_s,
    )
    _consume_panel_nonce(receipt, nonce_store=nonce_store, consume_nonce=consume_nonce)
    return VerifiedModelPanelEvidence(receipt, entries, _VERIFIED_MARKER)


def _consume_panel_nonce(
    receipt: ModelPanelSignedEvidenceReceipt, *, nonce_store: NonceStore | None, consume_nonce: bool,
) -> None:
    if not consume_nonce:
        return
    if nonce_store is None:
        raise ValueError("panel_nonce_store_missing")
    try:
        consumed = nonce_store.consume(receipt.nonce)
    except Exception:
        consumed = False
    if not consumed:
        raise ValueError("panel_nonce_replay")


def _verify_member_inputs(
    *, catalog_snapshot_id: str, selection_receipt_id: str,
    benchmark_run_receipt_id: str, member_inputs: Sequence[PanelMemberEvidenceInput],
    key_resolver: ModelEvidenceKeyResolver, signature_verifier: SignatureVerifier,
    now: int, revoked_key_epochs: Sequence[str], leeway_s: int,
) -> tuple[tuple[VerifiedModelEvidenceEntry, ...], tuple[PanelMemberEvidenceBinding, ...]]:
    entries: list[VerifiedModelEvidenceEntry] = []
    bindings: list[PanelMemberEvidenceBinding] = []
    for ordinal, source in enumerate(member_inputs):
        verified = build_verified_model_production_evidence(
            catalog_snapshot_id=catalog_snapshot_id,
            selection_receipt_id=selection_receipt_id,
            benchmark_run_receipt_id=benchmark_run_receipt_id,
            benchmark_receipt=source.benchmark_receipt,
            promotion_receipt=source.promotion_receipt,
            benchmark_signature_receipt=source.benchmark_signature_receipt,
            promotion_signature_receipt=source.promotion_signature_receipt,
            key_resolver=key_resolver,
            signature_verifier=signature_verifier,
            now=now,
            consume_nonces=False,
            revoked_key_epochs=revoked_key_epochs,
            leeway_s=leeway_s,
        )
        entry = verified.entries[0]
        entries.append(entry)
        bindings.append(_binding_from_entry(ordinal, source, entry))
    return tuple(entries), tuple(bindings)


def panel_runtime_context_rejections(
    evidence: Any,
    *,
    catalog_snapshot: ModelCatalogSnapshot,
    selection_receipt: ModelSelectionReceipt,
    runtime_policy: ModelRuntimeBindingPolicy,
) -> tuple[str, ...]:
    """Recheck immutable aggregate context at the runtime-binding boundary."""

    if not isinstance(evidence, VerifiedModelPanelEvidence) or not evidence.panel_signed_evidence_verified:
        return ("missing_verified_panel_evidence",)
    receipt = evidence.aggregate_receipt
    reasons: list[str] = []
    try:
        if rehydrate_model_panel_signed_evidence_receipt(receipt.to_dict()) != receipt:
            reasons.append("panel_signed_evidence_receipt_invalid")
    except Exception:
        reasons.append("panel_signed_evidence_receipt_invalid")
    expected_assignments = tuple((a.role, a.canonical_model_id, a.provider) for a in selection_receipt.role_assignments)
    actual_assignments = tuple((m.role, m.model_id, m.provider) for m in receipt.members)
    if expected_assignments != actual_assignments:
        reasons.append("panel_signed_evidence_member_order_mismatch")
    if receipt.required_roles != tuple(selection_receipt.requirements.panel_roles):
        reasons.append("panel_signed_evidence_required_roles_mismatch")
    if not _runtime_member_bindings_match(receipt, evidence.member_entries):
        reasons.append("panel_signed_evidence_member_projection_mismatch")
    expected_context = _context_values(catalog_snapshot, selection_receipt, runtime_policy)
    actual_context = (
        receipt.catalog_snapshot_id,
        receipt.catalog_snapshot_digest,
        receipt.selection_receipt_id,
        receipt.selection_receipt_digest,
        receipt.topology_receipt_digest,
        receipt.policy_receipt_digest,
        receipt.runtime_surface_receipt_digest,
    )
    if expected_context != actual_context:
        reasons.append("panel_signed_evidence_context_mismatch")
    if receipt.task_receipt_digest != _common_task_digest(evidence.member_entries):
        reasons.append("panel_signed_evidence_task_mismatch")
    return tuple(sorted(set(reasons)))


def _runtime_member_bindings_match(
    receipt: ModelPanelSignedEvidenceReceipt,
    entries: tuple[VerifiedModelEvidenceEntry, ...],
) -> bool:
    if len(receipt.members) != len(entries):
        return False
    for member, entry in zip(receipt.members, entries):
        try:
            source = PanelMemberEvidenceInput(
                member.role, member.model_id, member.provider,
                entry.benchmark_receipt, entry.promotion_receipt,
                entry.benchmark_signature_receipt, entry.promotion_signature_receipt,
            )
            matches = _binding_from_entry(member.ordinal, source, entry) == member
        except Exception:
            matches = False
        if not matches:
            return False
    return True


def _assert_panel_context(
    *,
    catalog_snapshot: ModelCatalogSnapshot, selection_receipt: ModelSelectionReceipt,
    bindings: tuple[PanelMemberEvidenceBinding, ...], entries: tuple[VerifiedModelEvidenceEntry, ...],
    receipt: ModelPanelSignedEvidenceReceipt, runtime_policy: ModelRuntimeBindingPolicy,
    task_receipt_id: str, topology_receipt_id: str,
    policy_receipt_id: str, runtime_surface_receipt_id: str,
) -> None:
    _assert_panel_members(selection_receipt, bindings, receipt)
    _assert_member_context(selection_receipt, entries)
    if selection_receipt.catalog_snapshot_id != catalog_snapshot.snapshot_id:
        raise ValueError("panel_selection_catalog_mismatch")
    expected_context = _context_values(catalog_snapshot, selection_receipt, runtime_policy)
    actual_context = _receipt_context_values(receipt)
    if expected_context != actual_context:
        raise ValueError("panel_context_splice")
    exact_ids = (receipt.task_receipt_id, receipt.topology_receipt_id, receipt.policy_receipt_id, receipt.runtime_surface_receipt_id)
    names = ("task_receipt_id", "topology_receipt_id", "policy_receipt_id", "runtime_surface_receipt_id")
    supplied_ids = tuple(map(_required, names, (task_receipt_id, topology_receipt_id, policy_receipt_id, runtime_surface_receipt_id)))
    if exact_ids != supplied_ids:
        raise ValueError("panel_context_id_splice")
    if receipt.task_receipt_digest != _common_task_digest(entries):
        raise ValueError("panel_task_digest_splice")


def _assert_panel_members(
    selection_receipt: ModelSelectionReceipt,
    bindings: tuple[PanelMemberEvidenceBinding, ...],
    receipt: ModelPanelSignedEvidenceReceipt,
) -> None:
    if selection_receipt.decision != SelectionDecision.SELECTED or selection_receipt.requirements.purpose != SelectionPurpose.PRODUCTION:
        raise ValueError("panel_selection_not_production_selected")
    if selection_receipt.requirements.selection_mode != SelectionMode.PANEL:
        raise ValueError("panel_selection_mode_required")
    if not bindings or len(bindings) != len(selection_receipt.selected_model_ids):
        raise ValueError("panel_member_count_mismatch")
    roles = tuple(binding.role for binding in bindings)
    models = tuple(binding.model_id for binding in bindings)
    if len(set(roles)) != len(roles):
        raise ValueError("duplicate_panel_roles")
    if len(set(models)) != len(models):
        raise ValueError("duplicate_panel_members")
    if roles != tuple(selection_receipt.requirements.panel_roles):
        raise ValueError("missing_or_reordered_required_panel_roles")
    assignments = tuple((a.role, a.canonical_model_id, a.provider) for a in selection_receipt.role_assignments)
    if tuple((m.role, m.model_id, m.provider) for m in bindings) != assignments:
        raise ValueError("panel_role_model_provider_order_mismatch")
    if tuple(receipt.members) != bindings:
        raise ValueError("panel_member_evidence_substitution")
    if receipt.required_roles != roles:
        raise ValueError("panel_required_roles_mismatch")
    synth = tuple(m for m in bindings if m.role == receipt.synthesizer_role)
    if len(synth) != 1 or synth[0].model_id != receipt.synthesizer_model_id:
        raise ValueError("panel_synthesizer_substitution")


def _assert_member_context(
    selection_receipt: ModelSelectionReceipt,
    entries: tuple[VerifiedModelEvidenceEntry, ...],
) -> None:
    for entry in entries:
        benchmark = entry.benchmark_receipt
        if benchmark.task_family != selection_receipt.requirements.task_family:
            raise ValueError("panel_member_task_mismatch")
        if benchmark.prompt_topology_digest != selection_receipt.panel_topology_digest:
            raise ValueError("panel_member_topology_mismatch")


def _receipt_context_values(receipt: ModelPanelSignedEvidenceReceipt) -> tuple[str, ...]:
    return (
        receipt.catalog_snapshot_id,
        receipt.catalog_snapshot_digest,
        receipt.selection_receipt_id,
        receipt.selection_receipt_digest,
        receipt.topology_receipt_digest,
        receipt.policy_receipt_digest,
        receipt.runtime_surface_receipt_digest,
    )


def _verify_panel_signature(
    receipt: ModelPanelSignedEvidenceReceipt,
    *,
    key_resolver: ModelEvidenceKeyResolver,
    signature_verifier: SignatureVerifier,
    now: int,
    revoked_key_epochs: Sequence[str],
    leeway_s: int,
) -> None:
    reasons: list[str] = []
    if receipt.signer_role != PanelEvidenceSignerRole.PANEL_AUTHORITY:
        reasons.append("panel_signer_role_mismatch")
    if receipt.key_epoch in {str(value) for value in revoked_key_epochs}:
        reasons.append("panel_key_epoch_revoked")
    try:
        trusted_key = key_resolver.resolve(receipt.signer_role.value, receipt.signer_key_fingerprint, receipt.key_epoch)
    except Exception:
        trusted_key = None
    if not trusted_key or not constant_time_compare(str(trusted_key), receipt.signer_public_key):
        reasons.append("panel_signer_key_untrusted")
    if now + leeway_s < receipt.issued_at:
        reasons.append("panel_evidence_issued_in_future")
    if now > receipt.expires_at + leeway_s:
        reasons.append("panel_evidence_expired")
    try:
        valid = signature_verifier.verify(
            receipt.signer_public_key,
            model_panel_signed_evidence_signing_input(receipt),
            receipt.signature,
        ) is True
    except Exception:
        valid = False
    if not valid:
        reasons.append("panel_signature_invalid")
    if reasons:
        raise ValueError("panel_signed_evidence_rejected:" + ",".join(sorted(set(reasons))))


def _binding_from_entry(
    ordinal: int,
    source: PanelMemberEvidenceInput,
    entry: VerifiedModelEvidenceEntry,
) -> PanelMemberEvidenceBinding:
    if _required("member_model_id", source.model_id) != entry.model_id:
        raise ValueError("panel_member_evidence_model_mismatch")
    benchmark = entry.benchmark_receipt.to_dict()
    promotion = entry.promotion_receipt.to_dict()
    benchmark_sig = entry.benchmark_signature_receipt.to_dict()
    promotion_sig = entry.promotion_signature_receipt.to_dict()
    member_body = {
        "model_id": entry.model_id,
        "benchmark": benchmark,
        "promotion": promotion,
        "benchmark_signature": benchmark_sig,
        "promotion_signature": promotion_sig,
    }
    return PanelMemberEvidenceBinding(
        ordinal=ordinal,
        role=_required("member_role", source.role),
        model_id=_required("member_model_id", source.model_id),
        provider=_required("member_provider", source.provider),
        member_evidence_id=_digest_id("model_panel_member_evidence", member_body),
        member_evidence_digest=_content_digest(member_body),
        benchmark_evidence_receipt_id=entry.benchmark_receipt.receipt_id,
        benchmark_evidence_digest=_content_digest(benchmark),
        promotion_evidence_receipt_id=entry.promotion_receipt.receipt_id,
        promotion_evidence_digest=_content_digest(promotion),
        benchmark_signed_evidence_receipt_id=entry.benchmark_signature_receipt.receipt_id,
        benchmark_signed_evidence_digest=_content_digest(benchmark_sig),
        promotion_signed_evidence_receipt_id=entry.promotion_signature_receipt.receipt_id,
        promotion_signed_evidence_digest=_content_digest(promotion_sig),
    )


def _member_binding(value: PanelMemberEvidenceBinding | Mapping[str, Any]) -> PanelMemberEvidenceBinding:
    if isinstance(value, PanelMemberEvidenceBinding):
        return value
    fields = PanelMemberEvidenceBinding.__dataclass_fields__
    return PanelMemberEvidenceBinding(**{name: int(value[name]) if name == "ordinal" else _required(name, value.get(name)) for name in fields})


def _context_values(
    catalog: ModelCatalogSnapshot,
    selection: ModelSelectionReceipt,
    policy: ModelRuntimeBindingPolicy,
) -> tuple[str, ...]:
    normalized_policy = policy.normalized()
    return (
        catalog.snapshot_id,
        _content_digest(catalog.to_dict()),
        selection.receipt_id,
        _content_digest(selection.to_dict()),
        _required("panel_topology_digest", selection.panel_topology_digest),
        _content_digest(normalized_policy.to_dict()),
        _content_digest({"runtime_surface": normalized_policy.runtime_surface}),
    )


def _common_task_digest(entries: Sequence[VerifiedModelEvidenceEntry]) -> str:
    digests = {entry.benchmark_receipt.task_set_digest for entry in entries}
    return next(iter(digests)) if len(digests) == 1 else ""


def _panel_subject_id(members: Sequence[PanelMemberEvidenceBinding]) -> str:
    return _digest_id("model_panel_subject", {"members": [member.to_dict() for member in members]})


def _list(data: Mapping[str, Any], name: str) -> list[Any]:
    value = data.get(name)
    if not isinstance(value, list):
        raise ValueError(f"invalid_{name}")
    return value


def _required(name: str, value: Any) -> str:
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"missing_{name}")
    return cleaned


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")


def _content_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _digest_id(prefix: str, value: Any) -> str:
    return prefix + ":" + hashlib.sha256(_canonical(value)).hexdigest()


__all__ = [
    "ModelPanelSignedEvidenceReceipt",
    "PanelEvidenceSignerRole",
    "PanelMemberEvidenceBinding",
    "PanelMemberEvidenceInput",
    "VerifiedModelPanelEvidence",
    "build_model_panel_signed_evidence_receipt",
    "build_panel_member_evidence_binding",
    "build_verified_model_panel_evidence",
    "model_panel_signed_evidence_signing_input",
    "panel_runtime_context_rejections",
    "rehydrate_model_panel_signed_evidence_receipt",
]
