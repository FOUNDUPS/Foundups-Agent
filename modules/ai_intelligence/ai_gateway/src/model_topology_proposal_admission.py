"""Fail-closed admission for model-authored RedDog topology proposals.

The proposer (initially Nemotron in shadow mode) may rank only candidates that
AI Gateway already found eligible. This module performs no provider call,
promotion, runtime binding, repository mutation, or execution. Accepted
topologies are benchmark candidates for the existing AutoResearch combination
harness; they are never production selections.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .model_combination_benchmark_harness import (
    ModelBenchmarkCandidate,
    ModelBenchmarkRoleAssignment,
    build_model_benchmark_candidate,
)
from .model_intelligence_catalog import ModelCatalogSnapshot
from .model_intelligence_selection import (
    ModelTaskRequirements,
    SelectionMode,
    SelectionPurpose,
    select_models_for_task,
)


PROPOSAL_SCHEMA_VERSION = "model_topology_proposal.v1"
ADMISSION_SCHEMA_VERSION = "model_topology_proposal_admission.v1"
MAX_PROPOSAL_BYTES = 65_536
MAX_PROPOSAL_CANDIDATES = 5
MAX_TOPOLOGY_MEMBERS = 6
MAX_TOKEN_LENGTH = 256


class ModelTopologyProposalReason:
    INVALID_SCHEMA = "invalid_model_topology_proposal_schema"
    PAYLOAD_TOO_LARGE = "model_topology_proposal_payload_too_large"
    CATALOG_MISMATCH = "model_topology_proposal_catalog_mismatch"
    REQUIREMENTS_MISMATCH = "model_topology_proposal_requirements_mismatch"
    PRODUCTION_NOT_ALLOWED = "model_topology_proposal_production_not_allowed"
    CANDIDATE_COUNT_INVALID = "model_topology_proposal_candidate_count_invalid"
    ROLE_ASSIGNMENTS_INVALID = "model_topology_proposal_role_assignments_invalid"
    ROLE_TOPOLOGY_MISMATCH = "model_topology_proposal_role_topology_mismatch"
    MODEL_NOT_ELIGIBLE = "model_topology_proposal_model_not_eligible"
    PROVIDER_MISMATCH = "model_topology_proposal_provider_mismatch"
    DUPLICATE_CANDIDATE = "model_topology_proposal_duplicate_candidate"
    DETERMINISTIC_BASELINE_UNAVAILABLE = "model_topology_deterministic_baseline_unavailable"


@dataclass(frozen=True)
class ModelTopologyProposalAdmissionReceipt:
    """Digest-bound shadow admission for AutoResearch candidate topologies."""

    receipt_id: str
    catalog_snapshot_id: str
    requirements_digest: str
    proposer_model_id: str
    proposer_call_receipt_id: str | None
    proposer_output_digest: str | None
    deterministic_selection_receipt_id: str
    deterministic_selected_model_ids: tuple[str, ...]
    accepted_candidates: tuple[ModelBenchmarkCandidate, ...]
    accepted: bool
    rejection_reasons: tuple[str, ...]
    shadow_only: bool = True
    schema_version: str = ADMISSION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "catalog_snapshot_id": self.catalog_snapshot_id,
            "requirements_digest": self.requirements_digest,
            "proposer_model_id": self.proposer_model_id,
            "proposer_call_receipt_id": self.proposer_call_receipt_id,
            "proposer_output_digest": self.proposer_output_digest,
            "deterministic_selection_receipt_id": self.deterministic_selection_receipt_id,
            "deterministic_selected_model_ids": list(self.deterministic_selected_model_ids),
            "accepted_candidates": [candidate.to_dict() for candidate in self.accepted_candidates],
            "accepted": self.accepted,
            "rejection_reasons": list(self.rejection_reasons),
            "shadow_only": True,
        }


def admit_model_topology_proposal(
    *,
    catalog_snapshot: ModelCatalogSnapshot,
    requirements: ModelTaskRequirements,
    proposer_model_id: str,
    proposal: Mapping[str, Any],
    proposer_call_receipt_id: str | None = None,
    proposer_output_digest: str | None = None,
) -> ModelTopologyProposalAdmissionReceipt:
    """Validate a bounded model-authored proposal against AI Gateway policy."""

    normalized = requirements.normalized()
    requirements_digest = model_task_requirements_digest(normalized)
    baseline = select_models_for_task(catalog_snapshot, normalized)
    reasons, raw_candidates = _proposal_rejections(
        proposal, catalog_snapshot.snapshot_id, requirements_digest, normalized
    )
    eligible = {ranking.canonical_model_id: ranking.provider for ranking in baseline.rankings}
    proposed, candidate_reasons = _admit_candidates(raw_candidates, normalized, eligible)
    reasons.extend(candidate_reasons)
    candidate_ids = [candidate.candidate_id for candidate in proposed]
    if len(candidate_ids) != len(set(candidate_ids)):
        reasons.append(ModelTopologyProposalReason.DUPLICATE_CANDIDATE)
    incumbent = _deterministic_baseline_candidate(baseline.role_assignments)
    if incumbent is None:
        reasons.append(ModelTopologyProposalReason.DETERMINISTIC_BASELINE_UNAVAILABLE)
    deduped = tuple(dict.fromkeys(reasons))
    candidates = _with_incumbent(incumbent, proposed) if not deduped else ()
    values = dict(
        catalog_snapshot_id=catalog_snapshot.snapshot_id,
        requirements_digest=requirements_digest,
        proposer_model_id=_token(proposer_model_id),
        proposer_call_receipt_id=_optional_token(proposer_call_receipt_id),
        proposer_output_digest=_optional_token(proposer_output_digest),
        deterministic_selection_receipt_id=baseline.receipt_id,
        deterministic_selected_model_ids=baseline.selected_model_ids,
        accepted_candidates=candidates,
        accepted=not deduped,
        rejection_reasons=deduped,
    )
    body = _receipt_body(**values)
    return ModelTopologyProposalAdmissionReceipt(
        receipt_id=_digest("model_topology_proposal_admission", body),
        **values,
    )


def _proposal_rejections(
    proposal: Mapping[str, Any],
    catalog_snapshot_id: str,
    requirements_digest: str,
    requirements: ModelTaskRequirements,
) -> tuple[list[str], list[Any]]:
    reasons: list[str] = []
    if _bounded_json(proposal) is None:
        reasons.append(ModelTopologyProposalReason.PAYLOAD_TOO_LARGE)
    if proposal.get("schema_version") != PROPOSAL_SCHEMA_VERSION:
        reasons.append(ModelTopologyProposalReason.INVALID_SCHEMA)
    if proposal.get("catalog_snapshot_id") != catalog_snapshot_id:
        reasons.append(ModelTopologyProposalReason.CATALOG_MISMATCH)
    if proposal.get("requirements_digest") != requirements_digest:
        reasons.append(ModelTopologyProposalReason.REQUIREMENTS_MISMATCH)
    if requirements.purpose != SelectionPurpose.EVALUATION:
        reasons.append(ModelTopologyProposalReason.PRODUCTION_NOT_ALLOWED)
    candidates = proposal.get("candidates")
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= MAX_PROPOSAL_CANDIDATES:
        reasons.append(ModelTopologyProposalReason.CANDIDATE_COUNT_INVALID)
        return reasons, []
    return reasons, candidates


def _admit_candidates(
    values: Sequence[Any],
    requirements: ModelTaskRequirements,
    eligible: Mapping[str, str],
) -> tuple[list[ModelBenchmarkCandidate], list[str]]:
    candidates: list[ModelBenchmarkCandidate] = []
    reasons: list[str] = []
    for value in values:
        candidate, candidate_reasons = _candidate(
            value, requirements=requirements, eligible=eligible
        )
        reasons.extend(candidate_reasons)
        if candidate is not None:
            candidates.append(candidate)
    return candidates, reasons


def _deterministic_baseline_candidate(
    values: Sequence[Any],
) -> ModelBenchmarkCandidate | None:
    if not values:
        return None
    roles = [
        ModelBenchmarkRoleAssignment(
            role=value.role,
            model_id=value.canonical_model_id,
            provider=value.provider,
        )
        for value in values
    ]
    try:
        return build_model_benchmark_candidate(roles)
    except ValueError:
        return None


def _with_incumbent(
    incumbent: ModelBenchmarkCandidate | None,
    proposed: Sequence[ModelBenchmarkCandidate],
) -> tuple[ModelBenchmarkCandidate, ...]:
    if incumbent is None:
        return ()
    return (incumbent,) + tuple(
        candidate for candidate in proposed if candidate.candidate_id != incumbent.candidate_id
    )


def rehydrate_model_topology_proposal_admission_receipt(
    payload: Mapping[str, Any],
) -> ModelTopologyProposalAdmissionReceipt:
    """Rehydrate a serialized receipt and verify its deterministic digest."""

    if payload.get("schema_version") != ADMISSION_SCHEMA_VERSION:
        raise ValueError("invalid_model_topology_proposal_admission_schema")
    candidates = tuple(_rehydrate_candidate(item) for item in _list(payload, "accepted_candidates"))
    accepted = payload.get("accepted")
    shadow_only = payload.get("shadow_only")
    if not isinstance(accepted, bool) or shadow_only is not True:
        raise ValueError("invalid_model_topology_proposal_admission_flags")
    rejection_reasons = tuple(_token(item) for item in _list(payload, "rejection_reasons"))
    if accepted == bool(rejection_reasons) or (not accepted and candidates):
        raise ValueError("invalid_model_topology_proposal_admission_outcome")
    values = {
        "catalog_snapshot_id": _token(payload.get("catalog_snapshot_id")),
        "requirements_digest": _token(payload.get("requirements_digest")),
        "proposer_model_id": _token(payload.get("proposer_model_id")),
        "proposer_call_receipt_id": _optional_token(payload.get("proposer_call_receipt_id")),
        "proposer_output_digest": _optional_token(payload.get("proposer_output_digest")),
        "deterministic_selection_receipt_id": _token(
            payload.get("deterministic_selection_receipt_id")
        ),
        "deterministic_selected_model_ids": tuple(
            _token(item) for item in _list(payload, "deterministic_selected_model_ids")
        ),
    }
    body = _receipt_body(
        **values,
        accepted_candidates=candidates,
        accepted=accepted,
        rejection_reasons=rejection_reasons,
    )
    receipt_id = _token(payload.get("receipt_id"))
    expected = _digest("model_topology_proposal_admission", body)
    if not hmac.compare_digest(receipt_id, expected):
        raise ValueError("model_topology_proposal_admission_receipt_id_mismatch")
    return ModelTopologyProposalAdmissionReceipt(
        receipt_id=receipt_id,
        accepted_candidates=candidates,
        accepted=accepted,
        rejection_reasons=rejection_reasons,
        **values,
    )


def model_task_requirements_digest(requirements: ModelTaskRequirements) -> str:
    normalized = requirements.normalized()
    return _digest(
        "model_task_requirements",
        {
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
        },
    )


def _candidate(
    value: Any,
    *,
    requirements: ModelTaskRequirements,
    eligible: Mapping[str, str],
) -> tuple[ModelBenchmarkCandidate | None, tuple[str, ...]]:
    if not isinstance(value, Mapping):
        return None, (ModelTopologyProposalReason.ROLE_ASSIGNMENTS_INVALID,)
    raw_roles = value.get("role_assignments")
    if not isinstance(raw_roles, list) or not 1 <= len(raw_roles) <= MAX_TOPOLOGY_MEMBERS:
        return None, (ModelTopologyProposalReason.ROLE_ASSIGNMENTS_INVALID,)
    expected_roles = (
        ("principal",)
        if requirements.selection_mode == SelectionMode.SINGLE
        else requirements.panel_roles[: requirements.max_candidates]
    )
    roles: list[ModelBenchmarkRoleAssignment] = []
    reasons: list[str] = []
    for item in raw_roles:
        if not isinstance(item, Mapping):
            reasons.append(ModelTopologyProposalReason.ROLE_ASSIGNMENTS_INVALID)
            continue
        role = _token(item.get("role"))
        model_id = _token(item.get("model_id"))
        provider = _token(item.get("provider"))
        if not role or not model_id or not provider:
            reasons.append(ModelTopologyProposalReason.ROLE_ASSIGNMENTS_INVALID)
            continue
        eligible_provider = eligible.get(model_id)
        if eligible_provider is None:
            reasons.append(ModelTopologyProposalReason.MODEL_NOT_ELIGIBLE)
        elif provider != eligible_provider:
            reasons.append(ModelTopologyProposalReason.PROVIDER_MISMATCH)
        roles.append(ModelBenchmarkRoleAssignment(role=role, model_id=model_id, provider=provider))
    if tuple(item.role for item in roles) != expected_roles:
        reasons.append(ModelTopologyProposalReason.ROLE_TOPOLOGY_MISMATCH)
    if len({item.model_id for item in roles}) != len(roles):
        reasons.append(ModelTopologyProposalReason.ROLE_ASSIGNMENTS_INVALID)
    if reasons:
        return None, tuple(dict.fromkeys(reasons))
    try:
        return build_model_benchmark_candidate(roles), ()
    except ValueError:
        return None, (ModelTopologyProposalReason.ROLE_ASSIGNMENTS_INVALID,)


def _rehydrate_candidate(value: Any) -> ModelBenchmarkCandidate:
    if not isinstance(value, Mapping) or value.get("schema_version") != "model_benchmark_candidate.v1":
        raise ValueError("invalid_model_topology_proposal_candidate")
    roles = [
        ModelBenchmarkRoleAssignment(
            role=_token(item.get("role")),
            model_id=_token(item.get("model_id")),
            provider=_token(item.get("provider")),
        )
        for item in _list(value, "role_assignments")
        if isinstance(item, Mapping)
    ]
    candidate = build_model_benchmark_candidate(roles)
    if candidate.candidate_id != _token(value.get("candidate_id")):
        raise ValueError("model_topology_proposal_candidate_id_mismatch")
    if candidate.topology_digest != _token(value.get("topology_digest")):
        raise ValueError("model_topology_proposal_topology_digest_mismatch")
    return candidate


def _receipt_body(**values: Any) -> dict[str, Any]:
    candidates: Sequence[ModelBenchmarkCandidate] = values.pop("accepted_candidates")
    return {
        "schema_version": ADMISSION_SCHEMA_VERSION,
        **values,
        "deterministic_selected_model_ids": list(values["deterministic_selected_model_ids"]),
        "accepted_candidates": [candidate.to_dict() for candidate in candidates],
        "rejection_reasons": list(values["rejection_reasons"]),
        "shadow_only": True,
    }


def _bounded_json(value: Any) -> bytes | None:
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError):
        return None
    return encoded if len(encoded) <= MAX_PROPOSAL_BYTES else None


def _list(value: Mapping[str, Any], name: str) -> list[Any]:
    result = value.get(name)
    if not isinstance(result, list):
        raise ValueError(f"invalid_{name}")
    return result


def _token(value: Any) -> str:
    token = str(value or "").strip()
    if len(token.encode("utf-8")) > MAX_TOKEN_LENGTH:
        raise ValueError("model_topology_proposal_token_too_long")
    return token


def _optional_token(value: Any) -> str | None:
    token = _token(value) if value is not None else ""
    return token or None


def _digest(prefix: str, value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


__all__ = [
    "ADMISSION_SCHEMA_VERSION",
    "PROPOSAL_SCHEMA_VERSION",
    "ModelTopologyProposalAdmissionReceipt",
    "ModelTopologyProposalReason",
    "admit_model_topology_proposal",
    "model_task_requirements_digest",
    "rehydrate_model_topology_proposal_admission_receipt",
]
