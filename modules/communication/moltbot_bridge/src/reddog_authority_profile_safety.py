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
    nested = (
        ("holoindex_evidence", _HOLOINDEX_FIELDS),
        ("source_authority_basis", _SOURCE_AUTHORITY_BASIS_FIELDS),
    )
    for field, nested_allowed in nested:
        child = value.get(field)
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
