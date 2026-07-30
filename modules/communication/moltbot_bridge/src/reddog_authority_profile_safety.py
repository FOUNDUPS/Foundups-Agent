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
_NESTED_FIELD_SCHEMAS = (
    ("holoindex_evidence", _HOLOINDEX_FIELDS),
    ("source_authority_basis", _SOURCE_AUTHORITY_BASIS_FIELDS),
    ("bounded_worker_plan", _BOUNDED_WORKER_PLAN_FIELDS),
    ("bounded_worker_plan.domain_profile", _DOMAIN_PROFILE_FIELDS),
    ("bounded_worker_plan.shell_profile", _SHELL_PROFILE_FIELDS),
    ("bounded_worker_plan.selection_receipt", _PLAN_SELECTION_FIELDS),
    ("bounded_worker_plan.signed_receipt_chain", _PLAN_RECEIPT_CHAIN_FIELDS),
    ("bounded_worker_plan.env_policy", frozenset({"scrubbed"})),
)


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
    found = [str(key) for key in value if str(key) not in allowed]
    for field, nested_allowed in _NESTED_FIELD_SCHEMAS:
        child = _mapping_at_path(value, field)
        if child is None:
            continue
        if not isinstance(child, Mapping):
            found.append(field)
            continue
        found.extend(
            f"{field}.{key}"
            for key in child
            if str(key) not in nested_allowed
        )
    return tuple(dict.fromkeys(found))


def _mapping_at_path(value: Mapping[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
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
                    if (
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
    "authority_profile_secret_field_paths",
    "authority_profile_unknown_field_paths",
]
