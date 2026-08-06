"""Typed, fail-closed rehydration for public RedDog authority profiles."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

from modules.communication.moltbot_bridge.src.reddog_authority_profile_safety import (
    authority_profile_malformed_digest_paths,
    authority_profile_runtime_unknown_field_paths,
    authority_profile_secret_field_paths,
    authority_profile_unknown_field_paths,
)


_MAPPING_FIELDS = frozenset(
    {
        "bounded_worker_plan",
        "domain_profile",
        "env_policy",
        "holoindex_evidence",
        "model_runtime_binding_receipt",
        "model_runtime_binding_verification_receipt",
        "model_selection_receipt",
        "operational_context_binding",
        "policy",
        "proposal_admission",
        "repo_permission_snapshot",
        "requirements",
        "scoring_rationale",
        "selection_receipt",
        "shell_profile",
        "signed_receipt_chain",
        "source_authority_basis",
        "verification_receipt",
        "worker_plan",
        "wsp15_allocation_receipt",
    }
)
_MAPPING_LIST_FIELDS = frozenset(
    {
        "model_runtime_binding_role_bindings",
        "rankings",
        "role_assignments",
        "role_bindings",
    }
)
_STRING_LIST_FIELDS = frozenset(
    {
        "allowed_arg_patterns",
        "allowed_path_patterns",
        "allowed_paths",
        "allowed_providers",
        "allowed_read_targets",
        "applicable_wsps",
        "argv_prefix",
        "benchmark_evidence_receipt_ids",
        "changed_paths",
        "code_hits",
        "decision_reasons",
        "denied_arg_patterns",
        "denied_path_patterns",
        "denied_paths",
        "denied_providers",
        "evidence_refs",
        "holoindex_evidence_refs",
        "expected_evidence",
        "missing_preconditions",
        "model_ids",
        "model_runtime_binding_panel_models",
        "panel_models",
        "panel_roles",
        "planned_artifacts",
        "principal_foundup_scope",
        "principal_repo_scope",
        "produced_capabilities",
        "promotion_evidence_receipt_ids",
        "reasons",
        "rejection_reasons",
        "requested_allowed_paths",
        "required_capabilities",
        "required_modalities",
        "required_policy_gates",
        "required_reviewers",
        "required_tests",
        "sentinel_checks",
        "skillz_candidates",
        "skillz_hits",
        "shell_argv",
        "signed_promotion_receipt_ids",
        "stop_conditions",
        "supporting_direct_read_paths",
        "supporting_finding_ids",
        "wsp_applicability",
        "wsp_hits",
        "selected_model_ids",
        "secret_env_refs",
        "wsp_refs",
    }
)
_BOOL_FIELDS = frozenset(
    {
        "accepted",
        "admissible_to_authoritative_queue",
        "consensus_required",
        "conversation_binding_present",
        "direct_read_grounded",
        "direct_read_fallback_used",
        "draft_pr_only",
        "fusion_required",
        "hermes_execution_allowed",
        "holoindex_maintenance_exception_applied",
        "index_gap_detected",
        "independent_verifier_required",
        "permission_snapshot_can_admin",
        "permission_snapshot_can_write",
        "openclaw_candidate",
        "queue_mutation_allowed",
        "repo_sensitive",
        "require_reasoning",
        "require_structured_output",
        "require_tools",
        "requires_cwd_guard",
        "requires_worktree",
        "scrubbed",
        "skillz_gap_detected",
    }
)
_INT_FIELDS = frozenset(
    {
        "coding_worker_count",
        "complexity",
        "conversation_revision",
        "critic_count",
        "deferability",
        "identity_expires_at",
        "identity_ttl_seconds",
        "impact",
        "importance",
        "issued_at",
        "max_candidates",
        "max_panel_models",
        "max_stderr_bytes",
        "max_stdout_bytes",
        "min_context_window",
        "mps_total",
        "permission_snapshot_expires_at",
        "timeout_seconds",
        "valid_until",
        "verified_at",
        "work_authority_expires_at",
        "work_authority_ttl_seconds",
    }
)
_NUMBER_FIELDS = frozenset(
    {
        "max_input_cost_per_million",
        "max_output_cost_per_million",
        "min_verifier_pass_rate",
        "score",
    }
)
_NO_EFFECT_FIELDS = frozenset(
    {
        "no_hermes_dispatch_performed",
        "no_holoindex_reindex_performed",
        "no_openclaw_enqueue_performed",
        "no_pattern_memory_write_performed",
        "no_repo_mutation_performed",
        "no_shell_command_executed",
        "no_signature_verification_performed",
        "no_signer_state_mutation_performed",
        "no_signing_performed",
        "no_work_state_mutation_performed",
        "no_worker_spawn_performed",
        "no_worktree_created",
    }
)
_NULLABLE_RUNTIME_SUFFIXES = (
    "model_selection_receipt.panel_topology_digest",
    "model_selection_receipt.requirements.max_input_cost_per_million",
    "model_selection_receipt.requirements.max_output_cost_per_million",
    "model_selection_receipt.requirements.min_context_window",
    "model_selection_receipt.requirements.panel_topology_digest",
    "model_runtime_binding_receipt.policy.required_panel_topology_digest",
    "model_runtime_binding_receipt.verification_receipt.panel_aggregate_receipt_digest",
    "model_runtime_binding_receipt.verification_receipt.panel_aggregate_receipt_id",
)


def rehydrate_authority_profile_seed(value: Any) -> dict[str, Any]:
    """Return one canonical seed profile or reject without coercion."""

    return _rehydrate(value, mode="seed")


def rehydrate_authority_profile_source(value: Any) -> dict[str, Any]:
    """Return one canonical source profile or reject without coercion."""

    return _rehydrate(value, mode="source")


def rehydrate_authority_profile_runtime(value: Any) -> dict[str, Any]:
    """Return one canonical runtime profile or reject without coercion."""

    return _rehydrate(value, mode="runtime")


def rehydrate_authority_profile_effect_scope(value: Any) -> dict[str, Any]:
    """Type-check effect-bearing fields on legacy materializer profiles."""

    if type(value) is not dict:
        raise ValueError("authority_profile_not_plain_mapping")
    unsafe = tuple(_invalid_type_paths(value)) + tuple(
        field
        for field in _NO_EFFECT_FIELDS
        if field in value and value[field] is not True
    )
    if unsafe:
        raise ValueError(f"authority_profile_invalid:{unsafe[0]}")
    try:
        return json.loads(
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("authority_profile_not_canonical_json") from exc


def _rehydrate(value: Any, *, mode: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("authority_profile_not_plain_mapping")
    if mode == "runtime":
        unknown = authority_profile_runtime_unknown_field_paths(value)
    else:
        unknown = authority_profile_unknown_field_paths(
            value, seed=mode == "seed"
        )
    unsafe = (
        tuple(unknown)
        + tuple(authority_profile_secret_field_paths(value))
        + tuple(authority_profile_malformed_digest_paths(value))
        + tuple(_invalid_type_paths(value))
        + tuple(
            field
            for field in _NO_EFFECT_FIELDS
            if field in value and value[field] is not True
        )
    )
    if unsafe:
        raise ValueError(f"authority_profile_invalid:{unsafe[0]}")
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        canonical = json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise ValueError("authority_profile_not_canonical_json") from exc
    return canonical


def _invalid_type_paths(value: Any) -> tuple[str, ...]:
    found: list[str] = []
    for key, child in value.items():
        _visit_type_paths(child, str(key), str(key), found)
    return tuple(dict.fromkeys(found))


def _visit_type_paths(item: Any, path: str, field: str, found: list[str]) -> None:
    if item is None:
        if not any(path.endswith(suffix) for suffix in _NULLABLE_RUNTIME_SUFFIXES):
            found.append(path)
        return
    if field != "scoring_rationale" and ".scoring_rationale." in f".{path}.":
        if type(item) is not str:
            found.append(path)
        return
    if field in _MAPPING_FIELDS:
        if type(item) is not dict:
            found.append(path)
            return
    elif field in _MAPPING_LIST_FIELDS:
        if not _is_mapping_list(item):
            found.append(path)
            return
        for index, child in enumerate(item):
            for key, nested in child.items():
                _visit_type_paths(nested, f"{path}[{index}].{key}", str(key), found)
        return
    elif field in _STRING_LIST_FIELDS:
        if type(item) not in (list, tuple) or any(
            type(child) is not str for child in item
        ):
            found.append(path)
        return
    elif field.startswith("no_"):
        if item is not True:
            found.append(path)
        return
    elif field in _BOOL_FIELDS:
        if type(item) is not bool:
            found.append(path)
        return
    elif field in _INT_FIELDS:
        if type(item) is not int:
            found.append(path)
        return
    elif field in _NUMBER_FIELDS:
        if type(item) not in (int, float) or not math.isfinite(float(item)):
            found.append(path)
        return
    elif type(item) is not str:
        found.append(path)
        return
    if isinstance(item, Mapping):
        for key, child in item.items():
            if type(key) is not str:
                found.append(f"{path}.$key")
                continue
            _visit_type_paths(child, f"{path}.{key}" if path else key, key, found)
    elif isinstance(item, Sequence) and not isinstance(
        item, (str, bytes, bytearray)
    ):
        for index, child in enumerate(item):
            _visit_type_paths(child, f"{path}[{index}]", "", found)


def _is_mapping_list(value: Any) -> bool:
    return type(value) in (list, tuple) and all(
        type(item) is dict for item in value
    )


__all__ = [
    "rehydrate_authority_profile_effect_scope",
    "rehydrate_authority_profile_runtime",
    "rehydrate_authority_profile_seed",
    "rehydrate_authority_profile_source",
]
