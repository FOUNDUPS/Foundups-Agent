"""Canonical contract for architect proposal validity and readiness receipts."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_execution_valve_use_time_authority import (
    INCOMPLETE_TRUST_ANCHOR_REASONS,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    OperationalContextSnapshot,
)


PROPOSAL_ADMISSION_SCHEMA_VERSION = (
    "reddog_architect_proposal_executability_admission.v2"
)
CONVERSATION_WORK_BINDING_SCHEMA = "reddog_conversation_work_binding.v1"

VALIDITY_VALID = "VALID"
VALIDITY_NEEDS_RESEARCH = "NEEDS_RESEARCH"
VALIDITY_INVALID = "INVALID"
PROPOSAL_VALIDITIES = frozenset(
    {VALIDITY_VALID, VALIDITY_NEEDS_RESEARCH, VALIDITY_INVALID}
)

READINESS_READY = "READY"
READINESS_CONFIGURATION_BLOCKED = "CONFIGURATION_BLOCKED"
READINESS_IMPLEMENTATION_BLOCKED = "IMPLEMENTATION_BLOCKED"
READINESS_PLATFORM_BLOCKED = "PLATFORM_BLOCKED"
READINESS_POLICY_BLOCKED = "POLICY_BLOCKED"
READINESS_EVIDENCE_BLOCKED = "EVIDENCE_BLOCKED"
EXECUTION_READINESS_STATES = frozenset(
    {
        READINESS_READY,
        READINESS_CONFIGURATION_BLOCKED,
        READINESS_IMPLEMENTATION_BLOCKED,
        READINESS_PLATFORM_BLOCKED,
        READINESS_POLICY_BLOCKED,
        READINESS_EVIDENCE_BLOCKED,
    }
)

REUSE_EXISTING = "REUSE_EXISTING"
EXTEND_EXISTING = "EXTEND_EXISTING"
CREATE_NEW = "CREATE_NEW"
REUSE_DECISIONS = frozenset({REUSE_EXISTING, EXTEND_EXISTING, CREATE_NEW})

EFFECT_NONE = "NONE"
EFFECT_READ_ONLY_AUDIT = "READ_ONLY_AUDIT"
EFFECT_CONFIGURATION_ONLY = "CONFIGURATION_ONLY"
EFFECT_REPOSITORY_CODE_CHANGE = "REPOSITORY_CODE_CHANGE"
EFFECT_LIVE_WORKTREE_CANARY = "LIVE_WORKTREE_CANARY"
EFFECT_DRAFT_PR_PUBLISH = "DRAFT_PR_PUBLISH"
EFFECT_MERGE = "MERGE"
EFFECT_EXTERNAL = "EXTERNAL_EFFECT"
TARGET_EFFECT_PLANES = frozenset(
    {
        EFFECT_NONE,
        EFFECT_READ_ONLY_AUDIT,
        EFFECT_CONFIGURATION_ONLY,
        EFFECT_REPOSITORY_CODE_CHANGE,
        EFFECT_LIVE_WORKTREE_CANARY,
        EFFECT_DRAFT_PR_PUBLISH,
        EFFECT_MERGE,
        EFFECT_EXTERNAL,
    }
)

CAP_MANIFEST_AUTHENTICATED_SELECTION = "runtime_artifact_manifest_authenticated_selection"
CAP_MANIFEST_DURABLE_REPLAY = "runtime_artifact_manifest_durable_replay"
CAP_MANIFEST_CURRENT_GENERATION = "runtime_artifact_manifest_current_generation"
CAP_CONSENSUS_RECEIPT = "verified_consensus_receipt"
CAP_SOVEREIGN_AUTHORIZATION = "verified_sovereign_authorization"
CAP_PRINCIPAL_KEY_ATTESTATION = "principal_subject_key_attestation"
CAP_MODEL_EVIDENCE = "model_signed_evidence_trust"
CAP_MODEL_SELECTION_EVIDENCE = "model_selection_signed_evidence"
CAP_MEMEX_EVIDENCE = "memex_supply_signed_evidence"
CAP_SIGNER_HANDSHAKE = "fresh_signer_peer_handshake"
CAP_PROPOSAL_AUTHENTICITY = "architect_proposal_admission_authenticity"
CAP_MERGE_AUTHORITY = "independent_merge_authority"
CAP_EXTERNAL_EFFECT_AUTHORITY = "external_effect_authority"
PROPOSAL_AUTHENTICITY_VERIFIER_MISSING = (
    "architect_proposal_admission_authenticity_verifier_missing"
)

_TRUST_REASON_CAPABILITY = {
    "canonical_signed_runtime_artifact_manifest_selection_verifier_missing": (
        CAP_MANIFEST_AUTHENTICATED_SELECTION
    ),
    "canonical_runtime_artifact_manifest_replay_high_water_missing": (
        CAP_MANIFEST_DURABLE_REPLAY
    ),
    "canonical_runtime_artifact_manifest_current_generation_verifier_missing": (
        CAP_MANIFEST_CURRENT_GENERATION
    ),
    "canonical_consensus_receipt_verifier_missing": CAP_CONSENSUS_RECEIPT,
    "canonical_sovereign_authorization_verifier_missing": (
        CAP_SOVEREIGN_AUTHORIZATION
    ),
    "canonical_principal_subject_key_attestation_missing": (
        CAP_PRINCIPAL_KEY_ATTESTATION
    ),
    "canonical_model_signed_evidence_trust_anchor_incomplete": CAP_MODEL_EVIDENCE,
    "canonical_model_selection_signed_evidence_verifier_missing": (
        CAP_MODEL_SELECTION_EVIDENCE
    ),
    "canonical_memex_supply_signed_evidence_verifier_missing": CAP_MEMEX_EVIDENCE,
    "canonical_signer_client_peer_handshake_verifier_missing": (
        CAP_SIGNER_HANDSHAKE
    ),
    PROPOSAL_AUTHENTICITY_VERIFIER_MISSING: CAP_PROPOSAL_AUTHENTICITY,
}
LIVE_EXECUTION_CAPABILITIES = tuple(sorted(_TRUST_REASON_CAPABILITY.values()))


@dataclass(frozen=True)
class ArchitectProposalAdmissionPolicy:
    platform: str
    available_capabilities: tuple[str, ...]
    missing_capability_reasons: Mapping[str, str]
    merge_authority_available: bool = False
    external_effect_authority_available: bool = False
    live_canary_platforms: tuple[str, ...] = ("linux",)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArchitectProposalExecutabilityReceipt:
    schema_version: str
    receipt_id: str
    accepted: bool
    proposal_validity: str
    execution_readiness: str
    admissible_to_authoritative_queue: bool
    action: str
    slice_id: str | None
    task_summary_digest: str
    reuse_decision: str
    requested_operation: str
    target_runtime: str
    target_effect_plane: str
    allowed_paths: tuple[str, ...]
    denied_paths: tuple[str, ...]
    required_tests: tuple[str, ...]
    required_policy_gates: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    produced_capabilities: tuple[str, ...]
    expected_evidence: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    missing_preconditions: tuple[str, ...]
    decision_reasons: tuple[str, ...]
    supporting_finding_ids: tuple[str, ...]
    supporting_direct_read_paths: tuple[str, ...]
    snapshot_receipt_id: str
    snapshot_content_digest: str
    repo_head_sha: str
    work_state_revision: str
    holoindex_generation_id: str
    holoindex_freshness_receipt_digest: str
    index_gap_detected: bool
    direct_read_grounded: bool
    holoindex_maintenance_exception_applied: bool
    report_bundle_id: str
    wsp15_allocation_receipt_id: str
    wsp15_allocation_digest: str
    policy_digest: str
    conversation_binding_present: bool
    conversation_binding_digest: str
    conversation_id: str
    conversation_revision: int
    conversation_revision_receipt_id: str
    conversation_scope_record_digest: str
    authorized_foundup_id: str
    resident_intent_id: str
    resident_intent_digest: str
    conversation_grounding_receipt_id: str
    rejection_reasons: tuple[str, ...]
    no_queue_mutation_performed: bool = True
    no_execution_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def current_architect_proposal_admission_policy(
    *, platform_name: str | None = None
) -> ArchitectProposalAdmissionPolicy:
    missing = {
        _TRUST_REASON_CAPABILITY[reason]: reason
        for reason in INCOMPLETE_TRUST_ANCHOR_REASONS
        if reason in _TRUST_REASON_CAPABILITY
    }
    # Proposal receipts are SHA-bound integrity records, not authenticated
    # authority. Keep production admission blocked until a verifier proves the
    # receipt came from the trusted architect determination runtime.
    missing[CAP_PROPOSAL_AUTHENTICITY] = (
        PROPOSAL_AUTHENTICITY_VERIFIER_MISSING
    )
    return ArchitectProposalAdmissionPolicy(
        platform=_normalize_platform(platform_name or sys.platform),
        available_capabilities=tuple(
            sorted(set(LIVE_EXECUTION_CAPABILITIES).difference(missing))
        ),
        missing_capability_reasons=missing,
    )


def proposal_admission_prompt_policy(
    *,
    snapshot: OperationalContextSnapshot,
    policy: ArchitectProposalAdmissionPolicy,
) -> Mapping[str, Any]:
    return {
        "schema_version": PROPOSAL_ADMISSION_SCHEMA_VERSION,
        "current_platform": policy.platform,
        "repo_head_sha": str(snapshot.repo_state.get("head_sha") or ""),
        "work_state_revision": str(snapshot.work_state.get("revision") or ""),
        "holoindex_freshness_ok": snapshot.holoindex_state.get("freshness_ok")
        is True,
        "holoindex_generation_id": str(
            snapshot.holoindex_state.get("generation_id") or ""
        ),
        "available_capabilities": list(policy.available_capabilities),
        "missing_capability_reasons": dict(policy.missing_capability_reasons),
        "live_canary_platforms": list(policy.live_canary_platforms),
        "merge_authority_available": policy.merge_authority_available,
        "external_effect_authority_available": (
            policy.external_effect_authority_available
        ),
        "reuse_decisions": sorted(REUSE_DECISIONS),
        "target_effect_planes": sorted(TARGET_EFFECT_PLANES),
        "rule": (
            "Proposal validity and resident execution readiness are separate. "
            "Never claim missing output capability as already implemented."
        ),
    }


def validate_architect_proposal_executability_receipt(
    value: Mapping[str, Any],
) -> ArchitectProposalExecutabilityReceipt:
    if not isinstance(value, Mapping):
        raise ValueError("proposal_admission_receipt_missing")
    expected = set(ArchitectProposalExecutabilityReceipt.__dataclass_fields__)
    if set(value) != expected:
        raise ValueError("proposal_admission_field_set_invalid")
    data = dict(value)
    receipt_id = _text(data.pop("receipt_id"))
    if not _valid_receipt_body(data, receipt_id):
        raise ValueError("proposal_admission_receipt_invalid")
    for field in _TUPLE_FIELDS:
        data[field] = tuple(str(item) for item in data.get(field) or ())
    return ArchitectProposalExecutabilityReceipt(receipt_id=receipt_id, **data)


def reevaluate_architect_proposal_execution_readiness(
    receipt: ArchitectProposalExecutabilityReceipt,
    *,
    policy: ArchitectProposalAdmissionPolicy | None = None,
) -> tuple[str, ...]:
    current = policy or current_architect_proposal_admission_policy()
    effect_capabilities = required_capabilities_for_effect(
        receipt.target_effect_plane
    )
    declared = set(receipt.required_capabilities)
    unavailable = effect_capabilities.union(declared).difference(
        current.available_capabilities
    )
    reasons: list[str] = [
        current.missing_capability_reasons.get(
            capability, f"required_capability_unavailable:{capability}"
        )
        for capability in sorted(unavailable)
    ]
    if not effect_capabilities.issubset(declared):
        reasons.append("effect_capability_requirements_underdeclared")
    if receipt.policy_digest != _digest(current.to_dict()):
        reasons.append("proposal_admission_policy_binding_stale")
    if (
        receipt.index_gap_detected
        and not receipt.holoindex_maintenance_exception_applied
    ):
        reasons.append("proposal_was_grounded_against_index_gap")
    if _unsupported_live_canary(receipt, current):
        reasons.append(f"live_canary_platform_unsupported:{current.platform}")
    if receipt.target_effect_plane == EFFECT_MERGE and not current.merge_authority_available:
        reasons.append("merge_authority_unavailable")
    if (
        receipt.target_effect_plane == EFFECT_EXTERNAL
        and not current.external_effect_authority_available
    ):
        reasons.append("external_effect_authority_unavailable")
    return tuple(dict.fromkeys(reasons))


def reevaluate_architect_proposal_promotion_preconditions(
    receipt: ArchitectProposalExecutabilityReceipt,
    *,
    policy: ArchitectProposalAdmissionPolicy | None = None,
) -> tuple[str, ...]:
    """Recheck proposal truth before its authority can be signed.

    Missing execution capabilities remain recorded on the receipt, but they
    cannot be required before the proposal-authenticity signature exists.
    The execution valve independently re-verifies every capability at use time.
    """

    current = policy or current_architect_proposal_admission_policy()
    required = required_capabilities_for_effect(
        receipt.target_effect_plane
    )
    reasons: list[str] = []
    if (
        receipt.accepted is not True
        or receipt.proposal_validity != VALIDITY_VALID
    ):
        reasons.append("proposal_not_valid_for_promotion")
    if not required.issubset(set(receipt.required_capabilities)):
        reasons.append("effect_capability_requirements_underdeclared")
    if receipt.policy_digest != _digest(current.to_dict()):
        reasons.append("proposal_admission_policy_binding_stale")
    if (
        receipt.index_gap_detected
        and not receipt.holoindex_maintenance_exception_applied
    ):
        reasons.append("proposal_was_grounded_against_index_gap")
    if _unsupported_live_canary(receipt, current):
        reasons.append(
            f"live_canary_platform_unsupported:{current.platform}"
        )
    if (
        receipt.target_effect_plane == EFFECT_MERGE
        and not current.merge_authority_available
    ):
        reasons.append("merge_authority_unavailable")
    if (
        receipt.target_effect_plane == EFFECT_EXTERNAL
        and not current.external_effect_authority_available
    ):
        reasons.append("external_effect_authority_unavailable")
    return tuple(dict.fromkeys(reasons))


_TUPLE_FIELDS = (
    "allowed_paths",
    "denied_paths",
    "required_tests",
    "required_policy_gates",
    "required_capabilities",
    "produced_capabilities",
    "expected_evidence",
    "stop_conditions",
    "missing_preconditions",
    "decision_reasons",
    "supporting_finding_ids",
    "supporting_direct_read_paths",
    "rejection_reasons",
)


def _valid_receipt_body(data: Mapping[str, Any], receipt_id: str) -> bool:
    expected_admission = (
        data.get("action") == "FIX"
        and data.get("proposal_validity") == VALIDITY_VALID
        and data.get("execution_readiness") == READINESS_READY
    )
    attestations = (
        "no_queue_mutation_performed",
        "no_execution_performed",
        "no_repo_mutation_performed",
        "no_holoindex_reindex_performed",
    )
    missing = tuple(data.get("missing_preconditions") or ())
    rejected = tuple(data.get("rejection_reasons") or ())
    return (
        data.get("schema_version") == PROPOSAL_ADMISSION_SCHEMA_VERSION
        and receipt_id == _digest(data)
        and data.get("proposal_validity") in PROPOSAL_VALIDITIES
        and data.get("execution_readiness") in EXECUTION_READINESS_STATES
        and data.get("reuse_decision") in REUSE_DECISIONS
        and data.get("target_effect_plane") in TARGET_EFFECT_PLANES
        and isinstance(data.get("direct_read_grounded"), bool)
        and isinstance(data.get("holoindex_maintenance_exception_applied"), bool)
        and _valid_conversation_binding(data)
        and _valid_holoindex_maintenance_exception(data)
        and data.get("accepted")
        is (data.get("proposal_validity") == VALIDITY_VALID)
        and data.get("admissible_to_authoritative_queue") is expected_admission
        and (
            (data.get("execution_readiness") == READINESS_READY and not missing)
            or (data.get("execution_readiness") != READINESS_READY and bool(missing))
        )
        and (
            (data.get("proposal_validity") == VALIDITY_VALID and not rejected)
            or (data.get("proposal_validity") != VALIDITY_VALID and bool(rejected))
        )
        and all(data.get(field) is True for field in attestations)
    )


def _valid_conversation_binding(data: Mapping[str, Any]) -> bool:
    present = data.get("conversation_binding_present")
    revision = data.get("conversation_revision")
    fields = (
        "conversation_binding_digest",
        "conversation_id",
        "conversation_revision_receipt_id",
        "conversation_scope_record_digest",
        "authorized_foundup_id",
        "resident_intent_id",
        "resident_intent_digest",
        "conversation_grounding_receipt_id",
    )
    if present is False:
        return revision == -1 and all(
            data.get(field) == "" for field in fields
        )
    if (
        present is not True
        or isinstance(revision, bool)
        or not isinstance(revision, int)
        or revision < 0
    ):
        return False
    digest_fields = fields[:4] + (fields[5],) + fields[6:]
    if any(not _sha256(data.get(field)) for field in digest_fields):
        return False
    binding = {
        "schema_version": CONVERSATION_WORK_BINDING_SCHEMA,
        "conversation_id": data["conversation_id"],
        "conversation_revision": data["conversation_revision"],
        "conversation_revision_receipt_id": data[
            "conversation_revision_receipt_id"
        ],
        "conversation_scope_record_digest": data[
            "conversation_scope_record_digest"
        ],
        "authorized_foundup_id": data["authorized_foundup_id"],
        "resident_intent_id": data["resident_intent_id"],
        "resident_intent_digest": data["resident_intent_digest"],
        "conversation_grounding_receipt_id": data[
            "conversation_grounding_receipt_id"
        ],
        "snapshot_receipt_id": data["snapshot_receipt_id"],
        "snapshot_content_digest": data["snapshot_content_digest"],
        "repo_head_sha": data["repo_head_sha"],
        "holoindex_generation_id": data["holoindex_generation_id"],
        "holoindex_freshness_receipt_digest": data[
            "holoindex_freshness_receipt_digest"
        ],
    }
    source_digests = (
        "snapshot_receipt_id",
        "snapshot_content_digest",
        "holoindex_generation_id",
        "holoindex_freshness_receipt_digest",
    )
    return bool(
        data.get("authorized_foundup_id")
        and all(_sha256(data.get(field)) for field in source_digests)
        and _git_sha(data.get("repo_head_sha"))
        and data.get("conversation_binding_digest") == _digest(binding)
    )


def _sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


def _git_sha(value: Any) -> bool:
    text = str(value or "")
    return 7 <= len(text) <= 64 and all(
        char in "0123456789abcdef" for char in text
    )


def _valid_holoindex_maintenance_exception(data: Mapping[str, Any]) -> bool:
    if data.get("holoindex_maintenance_exception_applied") is not True:
        return True
    allowed_paths = tuple(str(path) for path in data.get("allowed_paths") or ())
    evidence_paths = tuple(
        str(path) for path in data.get("supporting_direct_read_paths") or ()
    )
    return (
        data.get("index_gap_detected") is True
        and data.get("direct_read_grounded") is True
        and "HOLOINDEX" in _text(data.get("slice_id")).upper()
        and data.get("requested_operation")
        in {"holoindex_maintenance", "index_maintenance"}
        and bool(allowed_paths)
        and all(path.startswith("holo_index/") for path in allowed_paths)
        and all(not any(token in path for token in ("*", "?", "[")) for path in allowed_paths)
        and set(allowed_paths) == set(evidence_paths)
    )


def required_capabilities_for_effect(effect_plane: str) -> frozenset[str]:
    if effect_plane not in {
        EFFECT_REPOSITORY_CODE_CHANGE,
        EFFECT_LIVE_WORKTREE_CANARY,
        EFFECT_DRAFT_PR_PUBLISH,
        EFFECT_MERGE,
        EFFECT_EXTERNAL,
    }:
        return frozenset()
    values = set(LIVE_EXECUTION_CAPABILITIES)
    if effect_plane == EFFECT_MERGE:
        values.add(CAP_MERGE_AUTHORITY)
    if effect_plane == EFFECT_EXTERNAL:
        values.add(CAP_EXTERNAL_EFFECT_AUTHORITY)
    return frozenset(values)


def _unsupported_live_canary(
    receipt: ArchitectProposalExecutabilityReceipt,
    policy: ArchitectProposalAdmissionPolicy,
) -> bool:
    return (
        receipt.target_effect_plane == EFFECT_LIVE_WORKTREE_CANARY
        and policy.platform not in policy.live_canary_platforms
    )


def _normalize_platform(value: str) -> str:
    text = _text(value).lower()
    if text.startswith("linux"):
        return "linux"
    if text.startswith("win"):
        return "windows"
    if text.startswith(("darwin", "mac")):
        return "macos"
    return text or "unknown"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "ArchitectProposalAdmissionPolicy",
    "ArchitectProposalExecutabilityReceipt",
    "CONVERSATION_WORK_BINDING_SCHEMA",
    "CREATE_NEW",
    "EFFECT_CONFIGURATION_ONLY",
    "EFFECT_DRAFT_PR_PUBLISH",
    "EFFECT_EXTERNAL",
    "EFFECT_LIVE_WORKTREE_CANARY",
    "EFFECT_MERGE",
    "EFFECT_NONE",
    "EFFECT_READ_ONLY_AUDIT",
    "EFFECT_REPOSITORY_CODE_CHANGE",
    "EXECUTION_READINESS_STATES",
    "EXTEND_EXISTING",
    "LIVE_EXECUTION_CAPABILITIES",
    "PROPOSAL_ADMISSION_SCHEMA_VERSION",
    "PROPOSAL_VALIDITIES",
    "READINESS_CONFIGURATION_BLOCKED",
    "READINESS_EVIDENCE_BLOCKED",
    "READINESS_IMPLEMENTATION_BLOCKED",
    "READINESS_PLATFORM_BLOCKED",
    "READINESS_POLICY_BLOCKED",
    "READINESS_READY",
    "REUSE_DECISIONS",
    "REUSE_EXISTING",
    "TARGET_EFFECT_PLANES",
    "VALIDITY_INVALID",
    "VALIDITY_NEEDS_RESEARCH",
    "VALIDITY_VALID",
    "current_architect_proposal_admission_policy",
    "proposal_admission_prompt_policy",
    "required_capabilities_for_effect",
    "reevaluate_architect_proposal_execution_readiness",
    "reevaluate_architect_proposal_promotion_preconditions",
    "validate_architect_proposal_executability_receipt",
]
