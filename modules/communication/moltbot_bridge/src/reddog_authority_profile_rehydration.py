"""Typed, fail-closed rehydration for public RedDog authority profiles."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from fnmatch import fnmatchcase
from typing import Any

from prompt.swarm.m2m_compiler import decode_m2m_envelope, encode_m2m_envelope

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
        "progressive_policy_stage_receipt",
        "repo_permission_snapshot",
        "requirements",
        "scoring_rationale",
        "selection_receipt",
        "shell_profile",
        "signed_receipt_chain",
        "slice_verifier_plan",
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
        "required_checks",
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
        "argv",
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
        "expected_changed_paths",
        "forbidden_path_patterns",
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
        "progressive_policy_would_block_reasons",
        "reasons",
        "rejection_reasons",
        "risk_classes",
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
        "would_block_reasons",
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
        "no_effect_authority",
        "permission_snapshot_can_admin",
        "permission_snapshot_can_write",
        "openclaw_candidate",
        "queue_mutation_allowed",
        "production_authority_granted",
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
        "timeout_s",
        "valid_until",
        "verified_at",
        "work_authority_expires_at",
        "work_authority_ttl_seconds",
        "wsp15_complexity",
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
_ENV_REFERENCE = re.compile(r"^[A-Z][A-Z0-9_]{1,127}$")
_WORKER_PLAN_PARENTS = ((), ("proposal_admission",),
                        ("operational_context_binding", "proposal_admission"))
_M2M_PATHS = frozenset(".".join((*parent, "bounded_worker_plan", "m2m_envelope"))
                       for parent in _WORKER_PLAN_PARENTS)
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
    "model_runtime_binding_verification_receipt.panel_aggregate_receipt_digest",
    "model_runtime_binding_verification_receipt.panel_aggregate_receipt_id",
)


def rehydrate_authority_profile_seed(value: Any) -> dict[str, Any]:
    """Return one canonical seed profile or reject without coercion."""

    return _rehydrate(value, mode="seed")


def snapshot_seed_worker_plan(value: Any) -> dict[str, Any] | None:
    """Detach optional plan data under the existing typed and ASCII policies."""
    if value is None:
        return None
    if type(value) is not dict:
        raise ValueError("bounded_worker_plan_not_plain_mapping")
    try:
        plan = rehydrate_authority_profile_seed({"bounded_worker_plan": value})["bounded_worker_plan"]
    except (TypeError, RecursionError, OverflowError) as exc:
        raise ValueError("bounded_worker_plan_invalid") from exc
    if not json.dumps(plan, ensure_ascii=False, allow_nan=False).isascii():
        raise ValueError("bounded_worker_plan_non_ascii")
    return plan


def worker_plan_matches_execution_scope(
    plan: Mapping[str, Any], data: Mapping[str, Any],
) -> bool:
    """Compare a typed, snapshotted plan with declared execution constraints.

    This proves data consistency, not current scope or execution authority.
    Only explicit packet mirrors are compared; S/A/T prose is not interpreted.
    """
    for owner, mirrors in (
        (plan, {"operation": "requested_operation"}),
        (plan.get("domain_profile", {}),
         {"operation": "requested_operation", "required_tests": "required_tests"}),
    ):
        if any(key in owner and json.dumps(owner[key], sort_keys=True) != json.dumps(data[target], sort_keys=True)
               for key, target in mirrors.items()):
            return False
    allowed, denied = data["allowed_paths"], data["denied_paths"]
    if any(type(rules) not in (list, tuple) or any(type(rule) is not str for rule in rules)
           for rules in (allowed, denied)):
        return False
    for path in plan.get("requested_allowed_paths", ()):
        if not _plan_path_allowed(path, allowed, denied, pattern=True):
            return False
    for path in plan.get("planned_artifacts", ()):
        if not _plan_path_allowed(path, allowed, denied, pattern=False):
            return False
    invariants = plan.get("m2m_envelope", {}).get("I", {})
    fields = ("requested_operation", "allowed_paths", "denied_paths",
              "required_tests", "required_policy_gates")
    return all(json.dumps(invariants[key], sort_keys=True) == json.dumps(data[key], sort_keys=True)
               for key in fields if key in invariants)



def _plan_path_allowed(path: str, allowed: Any, denied: Any, *, pattern: bool) -> bool:
    if (not path or path.startswith("/") or "\\" in path or any(ord(char) < 32 for char in path)
            or ":" in path or any(part in {"", ".", ".."} or part.rstrip(" .") != part
                                   for part in path.split("/"))):
        return False
    if not pattern and any(char in path for char in "*?["):
        return False
    if pattern and any(char in path for char in "*?["):
        # Literal prefixes can prove disjointness, not general glob inclusion.
        # Reject uncertain deny overlap; materialization still checks each file.
        prefix = path[:min(path.find(char) for char in "*?[" if char in path)].casefold()
        for rule in denied:
            boundary = min((rule.find(char) for char in "*?[" if char in rule), default=len(rule))
            denied_prefix = rule[:boundary].casefold()
            if prefix.startswith(denied_prefix) or denied_prefix.startswith(prefix):
                return False
    # Denials cover case aliases on supported Windows hosts as well.
    return not any(fnmatchcase(path.casefold(), rule.casefold()) for rule in denied) and any(
        (path == rule or (rule.endswith("/**") and path.startswith(rule[:-3] + "/")))
        if pattern else fnmatchcase(path, rule) for rule in allowed
    )



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
    value = snapshot_authority_profile_m2m(value)
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
    value = snapshot_authority_profile_m2m(value)
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
        if type(key) is not str:
            found.append("$key")
            continue
        _visit_type_paths(child, key, key, found)
    return tuple(dict.fromkeys(found))


def _visit_type_paths(item: Any, path: str, field: str, found: list[str]) -> None:
    if field == "m2m_envelope" and path in _M2M_PATHS:
        return  # Complete JSON and nested policies checked before generic traversal.
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
        _visit_mapping_list_paths(item, path, found)
        return
    elif field in _STRING_LIST_FIELDS:
        if type(item) not in (list, tuple) or any(
            type(child) is not str for child in item
        ):
            found.append(path)
        elif field == "secret_env_refs" and any(
            _ENV_REFERENCE.fullmatch(child) is None for child in item
        ):
            found.append(path)
        return
    elif field in _BOOL_FIELDS:
        if type(item) is not bool:
            found.append(path)
        return
    elif field.startswith("no_"):
        if item is not True:
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


def _visit_mapping_list_paths(
    items: Sequence[Mapping[str, Any]],
    path: str,
    found: list[str],
) -> None:
    for index, child in enumerate(items):
        for key, nested in child.items():
            _visit_type_paths(nested, f"{path}[{index}].{key}", str(key), found)


def _is_mapping_list(value: Any) -> bool:
    return type(value) in (list, tuple) and all(
        type(item) is dict for item in value
    )


def snapshot_authority_profile_m2m(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """Bound normalized packets at the three declared plan locations.

    This is profile data validation, not prompt or execution admission. An absent
    field retains legacy behavior; a present packet is detached without coercion.
    Callers must still apply their complete profile, ASCII and authority gates.
    """
    for parent_path in _WORKER_PLAN_PARENTS:
        parent, ancestors = value, []
        for index, field in enumerate(parent_path):
            if not isinstance(parent, Mapping):
                break
            if type(parent) is not dict:
                path = ".".join(parent_path[:index]) or "$"
                raise ValueError(f"authority_profile_invalid:{path}")
            ancestors.append((parent, field))
            parent = parent.get(field)
        else:
            if isinstance(parent, Mapping):
                if type(parent) is not dict:
                    path = ".".join(parent_path) or "$"
                    raise ValueError(f"authority_profile_invalid:{path}")
                updated = _snapshot_profile_plan(parent, parent_path)
                if updated is parent:
                    continue
                for ancestor, field in reversed(ancestors):
                    updated = {**ancestor, field: updated}
                value = updated
    return value


def _snapshot_profile_plan(
    value: Mapping[str, Any], parent_path: tuple[str, ...],
) -> Mapping[str, Any]:
    plan = value.get("bounded_worker_plan")
    if not isinstance(plan, Mapping) or "m2m_envelope" not in plan:
        return value
    path = ".".join((*parent_path, "bounded_worker_plan", "m2m_envelope"))
    try:
        if type(plan) is not dict:
            raise ValueError("plan_not_plain_mapping")
        packet = decode_m2m_envelope(encode_m2m_envelope(plan["m2m_envelope"]))
    except ValueError:
        raise ValueError(f"authority_profile_invalid:{path}") from None
    unsafe = list(authority_profile_secret_field_paths(packet))
    unsafe.extend(authority_profile_malformed_digest_paths(packet))
    _m2m_policy_paths(packet, "", unsafe)
    if unsafe:
        raise ValueError(f"authority_profile_invalid:{path}.{unsafe[0]}")
    return {**value, "bounded_worker_plan": {**plan, "m2m_envelope": packet}}


def _m2m_policy_paths(item: Any, path: str, found: list[str]) -> None:
    if type(item) is dict:
        for key, child in item.items():
            child_path = f"{path}.{key}" if path else key
            if key.startswith("no_") or key == "secret_env_refs":
                policy_errors: list[str] = []
                _visit_type_paths(child, "", key, policy_errors)
                if policy_errors:
                    found.append(child_path)
            else:
                _m2m_policy_paths(child, child_path, found)
    elif type(item) is list:
        for index, child in enumerate(item):
            _m2m_policy_paths(child, f"{path}[{index}]", found)


__all__ = [
    "rehydrate_authority_profile_effect_scope",
    "rehydrate_authority_profile_runtime",
    "rehydrate_authority_profile_seed",
    "rehydrate_authority_profile_source",
    "snapshot_authority_profile_m2m",
    "snapshot_seed_worker_plan",
    "worker_plan_matches_execution_scope",
]
