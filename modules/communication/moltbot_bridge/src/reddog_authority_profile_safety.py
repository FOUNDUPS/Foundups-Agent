"""Secret-field rejection shared by authority-profile publication paths."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

_FORBIDDEN_FIELD_PARTS = (
    "access_token",
    "api_key",
    "authorization",
    "bearer",
    "cookie",
    "credential",
    "password",
    "private_key",
    "refresh_token",
    "secret",
)
_PUBLIC_REFERENCE_FIELDS = frozenset(
    {
        "proposal_policy_authorization_id",
    }
)
_SEED_FIELDS = frozenset(
    {
        "allowed_paths",
        "base_ref",
        "bounded_worker_plan",
        "consensus_receipt_digest",
        "denied_paths",
        "foundup_id",
        "holoindex_evidence",
        "identity_expires_at",
        "identity_nonce",
        "issued_at",
        "key_epoch",
        "memex_snapshot_receipt_id",
        "memex_supply_receipt_id",
        "model_catalog_snapshot_id",
        "model_selection_receipt_id",
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
        "permission_snapshot_digest",
        "principal_id",
        "principal_provider",
        "reddog_id",
        "reddog_public_key",
        "repo_full_name",
        "requested_operation",
        "required_policy_gates",
        "required_tests",
        "schema_version",
        "seed_supply_receipt_id",
        "source_determination_receipt_id",
        "sovereign_authorization_digest",
        "valve_state_required",
        "work_authority_expires_at",
        "work_authority_nonce",
        "queue_candidate_id",
        "wsp15_allocation_digest",
        "wsp15_allocation_receipt_id",
    }
)
_SOURCE_FIELDS = _SEED_FIELDS | frozenset(
    {
        "authority_profile_source_receipt_id",
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
        "owner_dae",
        "principal_public_key",
        "principal_wallet",
        "reward_account",
        "schema_version",
        "source_authority_basis",
    }
)
_RUNTIME_FIELDS = _SOURCE_FIELDS | frozenset(
    {
        "authorized_base_sha",
        "context_view_id",
        "determination_id",
        "evidence_bundle_id",
        "identity_ttl_seconds",
        "memex_supply_digest",
        "model_runtime_binding_digest",
        "model_runtime_binding_panel_models",
        "model_runtime_binding_principal_model",
        "model_runtime_binding_receipt",
        "model_runtime_binding_receipt_id",
        "model_runtime_binding_role_bindings",
        "model_runtime_binding_runtime_surface",
        "model_runtime_binding_verification_digest",
        "model_runtime_binding_verification_receipt",
        "model_runtime_binding_verification_receipt_id",
        "model_selection_digest",
        "model_selection_receipt",
        "operational_context_binding",
        "promotion_publication_id",
        "proposal_admission",
        "proposal_admission_digest",
        "proposal_admission_receipt_id",
        "proposal_authenticity_attestation_digest",
        "proposal_authenticity_attestation_id",
        "proposal_policy_authorization_digest",
        "proposal_policy_authorization_id",
        "proposal_signer_runtime_context_digest",
        "readonly_audit_decision_id",
        "snapshot_receipt_id",
        "task_summary",
        "work_authority_ttl_seconds",
        "work_order_id",
        "wsp15_allocation_receipt",
    }
)
_HOLOINDEX_FIELDS = frozenset(
    {
        "applicable_wsps",
        "evidence_refs",
        "holoindex_query",
        "holoindex_freshness_receipt_digest",
        "holoindex_status",
        "index_gap_detected",
        "memex_supply_receipt_id",
        "model_selection_receipt_id",
        "retrieval_quality",
    }
)
_SOURCE_AUTHORITY_BASIS_FIELDS = frozenset(
    {
        "permission_snapshot_can_admin",
        "permission_snapshot_can_write",
        "permission_snapshot_digest",
        "permission_snapshot_expires_at",
        "principal_foundup_scope",
        "principal_repo_scope",
        "principal_verified_subject_digest",
    }
)
_BOUNDED_WORKER_PLAN_FIELDS = frozenset(
    {
        "domain_id",
        "domain_profile",
        "env_policy",
        "operation",
        "planned_artifacts",
        "requested_allowed_paths",
        "selection_receipt",
        "shell_argv",
        "shell_profile",
        "signed_receipt_chain",
        "stdin_policy",
    }
)
_DOMAIN_PROFILE_FIELDS = frozenset(
    {
        "allowed_path_patterns",
        "artifact_contract_type",
        "branch_prefix",
        "canonical_root_template",
        "consensus_required",
        "denied_path_patterns",
        "domain_id_pattern",
        "draft_pr_only",
        "operation",
        "profile_id",
        "required_tests",
    }
)
_SHELL_PROFILE_FIELDS = frozenset(
    {
        "allowed_arg_patterns",
        "argv_prefix",
        "command_kind",
        "consensus_required",
        "denied_arg_patterns",
        "draft_pr_only",
        "max_stderr_bytes",
        "max_stdout_bytes",
        "output_redaction_policy",
        "profile_id",
        "repo_sensitive",
        "requires_cwd_guard",
        "requires_worktree",
        "timeout_seconds",
    }
)
_PLAN_SELECTION_FIELDS = frozenset(
    {
        "decision",
        "execution_plane",
        "no_execution_performed",
        "selected_wardrobe",
    }
)
_PLAN_RECEIPT_CHAIN_FIELDS = frozenset(
    {
        "accepted",
        "decision",
        "no_execution_performed",
        "no_reward_settlement_performed",
        "terminal_receipt_hash",
    }
)
_MODEL_SELECTION_FIELDS = frozenset(
    {
        "catalog_snapshot_id",
        "decision",
        "panel_topology_digest",
        "rankings",
        "receipt_id",
        "rejection_reasons",
        "requirements",
        "role_assignments",
        "schema_version",
        "selected_model_ids",
    }
)
_MODEL_TASK_REQUIREMENTS_FIELDS = frozenset(
    {
        "allowed_providers",
        "denied_providers",
        "max_candidates",
        "max_input_cost_per_million",
        "max_output_cost_per_million",
        "min_context_window",
        "min_verifier_pass_rate",
        "panel_roles",
        "panel_topology_digest",
        "purpose",
        "require_reasoning",
        "require_structured_output",
        "require_tools",
        "required_modalities",
        "selection_mode",
        "task_family",
    }
)
_MODEL_CANDIDATE_RANKING_FIELDS = frozenset(
    {"canonical_model_id", "provider", "reasons", "score"}
)
_MODEL_PANEL_ROLE_ASSIGNMENT_FIELDS = frozenset(
    {"canonical_model_id", "provider", "role"}
)
_MODEL_RUNTIME_ROLE_BINDING_FIELDS = frozenset(
    {"model_id", "provider", "role"}
)
_MODEL_RUNTIME_BINDING_POLICY_FIELDS = frozenset(
    {
        "authority_receipt_id",
        "max_panel_models",
        "min_verifier_pass_rate",
        "required_held_out_split_digest",
        "required_panel_topology_digest",
        "required_task_set_digest",
        "required_verifier_digest",
        "runtime_surface",
        "schema_version",
        "task_family",
    }
)
_MODEL_RUNTIME_BINDING_FIELDS = frozenset(
    {
        "benchmark_evidence_receipt_ids",
        "catalog_snapshot_id",
        "decision",
        "panel_models",
        "policy",
        "principal_model",
        "promotion_evidence_receipt_ids",
        "receipt_id",
        "rejection_reasons",
        "role_bindings",
        "runtime_surface",
        "schema_version",
        "selection_receipt_id",
        "signed_promotion_receipt_ids",
        "task_family",
        "verification_receipt",
    }
)
_MODEL_RUNTIME_BINDING_VERIFICATION_FIELDS = frozenset(
    {
        "benchmark_evidence_receipt_ids",
        "catalog_snapshot_digest",
        "evidence_bundle_digest",
        "evidence_projection_digest",
        "model_ids",
        "panel_aggregate_receipt_digest",
        "panel_aggregate_receipt_id",
        "promotion_evidence_receipt_ids",
        "receipt_id",
        "runtime_binding_digest",
        "runtime_binding_receipt_id",
        "runtime_policy_digest",
        "schema_version",
        "selection_mode",
        "selection_receipt_digest",
        "selection_receipt_id",
        "signed_promotion_receipt_ids",
        "trusted_keys_digest",
        "valid_until",
        "verified_at",
    }
)
_WSP15_ALLOCATION_FIELDS = frozenset(
    {
        "allowed_read_targets",
        "architect_model_runtime_binding_digest",
        "architect_model_runtime_binding_receipt_id",
        "changed_paths",
        "complexity",
        "deferability",
        "impact",
        "importance",
        "input_digest",
        "model_runtime_binding_digest",
        "model_runtime_binding_receipt_id",
        "mps_total",
        "no_holoindex_reindex_performed",
        "no_model_call_performed",
        "no_queue_mutation_performed",
        "no_repo_mutation_performed",
        "no_worker_spawn_performed",
        "priority",
        "prompt_digest",
        "reasoning_tier",
        "receipt_id",
        "requested_operation",
        "schema_version",
        "scoring_method",
        "scoring_rationale",
        "worker_plan",
        "wsp97_label",
        "wsp_refs",
    }
)
_WSP15_WORKER_PLAN_FIELDS = frozenset(
    {
        "coding_worker_count",
        "critic_count",
        "fusion_required",
        "hermes_execution_allowed",
        "independent_verifier_required",
        "mode_selection_source",
        "openclaw_candidate",
        "queue_mutation_allowed",
        "reasoning_tier",
        "schema_version",
    }
)
_WSP15_SCORING_RATIONALE_FIELDS = frozenset(
    {"complexity", "deferability", "impact", "importance"}
)


def _field_set(value: str) -> frozenset[str]:
    return frozenset(value.split())


_PROPOSAL_ADMISSION_FIELDS = _field_set(
    """
    accepted action admissible_to_authoritative_queue allowed_paths
    authorized_foundup_id conversation_binding_digest conversation_binding_present
    conversation_grounding_receipt_id conversation_id conversation_revision
    conversation_revision_receipt_id conversation_scope_record_digest decision_reasons
    denied_paths direct_read_grounded execution_readiness expected_evidence
    holoindex_freshness_receipt_digest holoindex_generation_id
    holoindex_maintenance_exception_applied index_gap_detected missing_preconditions
    no_execution_performed no_holoindex_reindex_performed no_queue_mutation_performed
    no_repo_mutation_performed policy_digest produced_capabilities proposal_validity
    receipt_id rejection_reasons repo_head_sha report_bundle_id requested_operation
    required_capabilities required_policy_gates required_tests resident_intent_digest
    resident_intent_id reuse_decision schema_version slice_id snapshot_content_digest
    snapshot_receipt_id stop_conditions supporting_direct_read_paths
    supporting_finding_ids target_effect_plane target_runtime task_summary_digest
    work_state_revision wsp15_allocation_digest wsp15_allocation_receipt_id
    """
)
_OPERATIONAL_CONTEXT_BINDING_FIELDS = _field_set(
    """
    architect_determination_receipt_id authorized_base_sha claim_id context_view_id
    determination_id evidence_bundle_id holoindex_evidence memex_supply_digest
    memex_supply_receipt_id model_catalog_snapshot_id model_runtime_binding_digest
    model_runtime_binding_panel_models model_runtime_binding_principal_model
    model_runtime_binding_receipt model_runtime_binding_receipt_id
    model_runtime_binding_role_bindings model_runtime_binding_runtime_surface
    model_runtime_binding_verification_digest
    model_runtime_binding_verification_receipt
    model_runtime_binding_verification_receipt_id model_selection_digest
    model_selection_receipt model_selection_receipt_id proposal_admission
    proposal_admission_digest proposal_admission_receipt_id
    proposal_authenticity_attestation_digest proposal_authenticity_attestation_id
    proposal_policy_authorization_digest proposal_policy_authorization_id
    proposal_signer_runtime_context_digest queue_item_id readonly_audit_decision_id
    snapshot_receipt_id work_order_id wsp15_allocation_receipt
    """
)
_NESTED_FIELD_SCHEMAS = (
    ("holoindex_evidence", _HOLOINDEX_FIELDS),
    ("source_authority_basis", _SOURCE_AUTHORITY_BASIS_FIELDS),
    ("bounded_worker_plan", _BOUNDED_WORKER_PLAN_FIELDS),
    ("bounded_worker_plan.domain_profile", _DOMAIN_PROFILE_FIELDS),
    ("bounded_worker_plan.shell_profile", _SHELL_PROFILE_FIELDS),
    ("bounded_worker_plan.selection_receipt", _PLAN_SELECTION_FIELDS),
    ("bounded_worker_plan.signed_receipt_chain", _PLAN_RECEIPT_CHAIN_FIELDS),
    ("bounded_worker_plan.env_policy", frozenset({"scrubbed"})),
    ("model_selection_receipt", _MODEL_SELECTION_FIELDS),
    ("model_selection_receipt.requirements", _MODEL_TASK_REQUIREMENTS_FIELDS),
    ("model_runtime_binding_receipt", _MODEL_RUNTIME_BINDING_FIELDS),
    ("model_runtime_binding_receipt.policy", _MODEL_RUNTIME_BINDING_POLICY_FIELDS),
    (
        "model_runtime_binding_receipt.verification_receipt",
        _MODEL_RUNTIME_BINDING_VERIFICATION_FIELDS,
    ),
    (
        "model_runtime_binding_verification_receipt",
        _MODEL_RUNTIME_BINDING_VERIFICATION_FIELDS,
    ),
    ("wsp15_allocation_receipt", _WSP15_ALLOCATION_FIELDS),
    ("wsp15_allocation_receipt.worker_plan", _WSP15_WORKER_PLAN_FIELDS),
    (
        "wsp15_allocation_receipt.scoring_rationale",
        _WSP15_SCORING_RATIONALE_FIELDS,
    ),
    ("proposal_admission", _PROPOSAL_ADMISSION_FIELDS),
    ("operational_context_binding", _OPERATIONAL_CONTEXT_BINDING_FIELDS),
    (
        "operational_context_binding.holoindex_evidence",
        _HOLOINDEX_FIELDS,
    ),
    (
        "operational_context_binding.model_selection_receipt",
        _MODEL_SELECTION_FIELDS,
    ),
    (
        "operational_context_binding.model_selection_receipt.requirements",
        _MODEL_TASK_REQUIREMENTS_FIELDS,
    ),
    (
        "operational_context_binding.model_runtime_binding_receipt",
        _MODEL_RUNTIME_BINDING_FIELDS,
    ),
    (
        "operational_context_binding.model_runtime_binding_receipt.policy",
        _MODEL_RUNTIME_BINDING_POLICY_FIELDS,
    ),
    (
        "operational_context_binding.model_runtime_binding_receipt.verification_receipt",
        _MODEL_RUNTIME_BINDING_VERIFICATION_FIELDS,
    ),
    (
        "operational_context_binding.model_runtime_binding_verification_receipt",
        _MODEL_RUNTIME_BINDING_VERIFICATION_FIELDS,
    ),
    (
        "operational_context_binding.wsp15_allocation_receipt",
        _WSP15_ALLOCATION_FIELDS,
    ),
    (
        "operational_context_binding.wsp15_allocation_receipt.worker_plan",
        _WSP15_WORKER_PLAN_FIELDS,
    ),
    (
        "operational_context_binding.wsp15_allocation_receipt.scoring_rationale",
        _WSP15_SCORING_RATIONALE_FIELDS,
    ),
    (
        "operational_context_binding.proposal_admission",
        _PROPOSAL_ADMISSION_FIELDS,
    ),
)
_SEQUENCE_MAPPING_SCHEMAS = (
    ("model_selection_receipt.rankings", _MODEL_CANDIDATE_RANKING_FIELDS),
    (
        "model_selection_receipt.role_assignments",
        _MODEL_PANEL_ROLE_ASSIGNMENT_FIELDS,
    ),
    (
        "model_runtime_binding_receipt.role_bindings",
        _MODEL_RUNTIME_ROLE_BINDING_FIELDS,
    ),
    ("model_runtime_binding_role_bindings", _MODEL_RUNTIME_ROLE_BINDING_FIELDS),
    (
        "operational_context_binding.model_selection_receipt.rankings",
        _MODEL_CANDIDATE_RANKING_FIELDS,
    ),
    (
        "operational_context_binding.model_selection_receipt.role_assignments",
        _MODEL_PANEL_ROLE_ASSIGNMENT_FIELDS,
    ),
    (
        "operational_context_binding.model_runtime_binding_receipt.role_bindings",
        _MODEL_RUNTIME_ROLE_BINDING_FIELDS,
    ),
    (
        "operational_context_binding.model_runtime_binding_role_bindings",
        _MODEL_RUNTIME_ROLE_BINDING_FIELDS,
    ),
)
_MISSING = object()


def authority_profile_secret_field_paths(value: Any) -> tuple[str, ...]:
    """Return secret-shaped field paths without reading secret values."""

    found: list[str] = []

    def visit(item: Any, path: str) -> None:
        if isinstance(item, Mapping):
            for raw_key, child in item.items():
                key = str(raw_key)
                clean = key.strip().lower().replace("-", "_")
                child_path = f"{path}.{key}" if path else key
                if (
                    clean not in {"principal_public_key", "reddog_public_key"}
                    and clean not in _PUBLIC_REFERENCE_FIELDS
                    and not clean.endswith("_digest")
                    and any(part in clean for part in _FORBIDDEN_FIELD_PARTS)
                ):
                    found.append(child_path)
                visit(child, child_path)
        elif isinstance(item, Sequence) and not isinstance(
            item, (str, bytes, bytearray)
        ):
            for index, child in enumerate(item):
                visit(child, f"{path}[{index}]")

    visit(value, "")
    return tuple(dict.fromkeys(found))


def authority_profile_unknown_field_paths(
    value: Any,
    *,
    seed: bool,
) -> tuple[str, ...]:
    """Return fields outside the frozen seed/source authority schemas."""

    if not isinstance(value, Mapping):
        return ("$",)
    allowed = _SEED_FIELDS if seed else _SOURCE_FIELDS
    return _unknown_field_paths(value, allowed)


def _unknown_field_paths(
    value: Mapping[str, Any],
    allowed: frozenset[str],
) -> tuple[str, ...]:
    found = [str(key) for key in value if str(key) not in allowed]
    for field, nested_allowed in _NESTED_FIELD_SCHEMAS:
        child = _mapping_at_path(value, field)
        if child is _MISSING:
            continue
        if not isinstance(child, Mapping):
            found.append(field)
            continue
        found.extend(
            f"{field}.{key}"
            for key in child
            if str(key) not in nested_allowed
        )
    for field, nested_allowed in _SEQUENCE_MAPPING_SCHEMAS:
        children = _mapping_at_path(value, field)
        if children is _MISSING:
            continue
        if not isinstance(children, Sequence) or isinstance(
            children, (str, bytes, bytearray)
        ):
            found.append(field)
            continue
        for index, child in enumerate(children):
            item_path = f"{field}[{index}]"
            if not isinstance(child, Mapping):
                found.append(item_path)
                continue
            found.extend(
                f"{item_path}.{key}"
                for key in child
                if str(key) not in nested_allowed
            )
    return tuple(dict.fromkeys(found))


def authority_profile_runtime_unknown_field_paths(
    value: Any,
) -> tuple[str, ...]:
    """Return fields outside the exact public runtime profile schema."""

    if not isinstance(value, Mapping):
        return ("$",)
    return _unknown_field_paths(value, _RUNTIME_FIELDS)


def _mapping_at_path(value: Mapping[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return _MISSING
        current = current[part]
    return current


def authority_profile_malformed_digest_paths(value: Any) -> tuple[str, ...]:
    """Require every admitted digest field to carry canonical SHA-256."""

    found: list[str] = []

    def visit(item: Any, path: str) -> None:
        if isinstance(item, Mapping):
            for raw_key, child in item.items():
                key = str(raw_key)
                child_path = f"{path}.{key}" if path else key
                if key.lower().replace("-", "_").endswith("_digest"):
                    text = str(child or "")
                    if text and (
                        len(text) != 71
                        or not text.startswith("sha256:")
                        or any(char not in "0123456789abcdef" for char in text[7:])
                    ):
                        found.append(child_path)
                visit(child, child_path)
        elif isinstance(item, Sequence) and not isinstance(
            item, (str, bytes, bytearray)
        ):
            for index, child in enumerate(item):
                visit(child, f"{path}[{index}]")

    visit(value, "")
    return tuple(dict.fromkeys(found))


__all__ = [
    "authority_profile_malformed_digest_paths",
    "authority_profile_runtime_unknown_field_paths",
    "authority_profile_secret_field_paths",
    "authority_profile_unknown_field_paths",
]
