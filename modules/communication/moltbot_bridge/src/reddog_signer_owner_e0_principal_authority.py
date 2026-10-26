"""Current-generation principal authority for signer E0 admission."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityRecord,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    MAX_ARTIFACT_BYTES,
    raw_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_principal_records import (
    parse_principal_artifact,
    principal_record_key,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    constant_time_compare,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_bytes,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


class CurrentGenerationPrincipalKeyResolver:
    """Resolve keys only from a manifest-bound principal artifact."""

    def __init__(self, records: Mapping[str, PrincipalAuthorityRecord]) -> None:
        self._records = dict(records)

    def resolve(self, principal_id: str, principal_provider: str) -> str | None:
        record = self._records.get(
            principal_record_key(principal_id, principal_provider)
        )
        return record.principal_public_key if record is not None else None


class CurrentGenerationPrincipalAuthorityResolver:
    """Resolve full principal records from one manifest-bound generation."""

    def __init__(self, records: Mapping[str, PrincipalAuthorityRecord]) -> None:
        self._records = dict(records)

    def resolve(
        self, principal_id: str, principal_provider: str
    ) -> PrincipalAuthorityRecord | None:
        return self._records.get(
            principal_record_key(principal_id, principal_provider)
        )

    def resolve_unique(self, principal_id: str) -> PrincipalAuthorityRecord | None:
        matches = tuple(
            record
            for record in self._records.values()
            if record.principal_id == principal_id
        )
        return matches[0] if len(matches) == 1 else None


def load_current_generation_principal_key_resolver(
    *, repo_root: Path, selection: Mapping[str, Any]
) -> CurrentGenerationPrincipalKeyResolver:
    """Read and verify the principal artifact selected by the signed manifest."""

    return CurrentGenerationPrincipalKeyResolver(
        _load_current_generation_records(repo_root, selection)
    )


def load_current_generation_principal_authority_resolver(
    *, repo_root: Path, selection: Mapping[str, Any]
) -> CurrentGenerationPrincipalAuthorityResolver:
    """Load full principal authority from the same signed generation seam."""

    return CurrentGenerationPrincipalAuthorityResolver(
        _load_current_generation_records(repo_root, selection)
    )


def _load_current_generation_records(
    repo_root: Path, selection: Mapping[str, Any]
) -> Mapping[str, PrincipalAuthorityRecord]:
    records, _ = load_current_generation_principal_artifact(
        repo_root=repo_root, selection=selection,
    )
    return records


def load_current_generation_principal_artifact(
    *, repo_root: Path, selection: Mapping[str, Any]
) -> tuple[Mapping[str, PrincipalAuthorityRecord], tuple[dict[str, Any], ...]]:
    """Read digest-bound identity/designation data inside the caller's generation lease."""
    runtime = validate_runtime_root_path(selection["runtime_root"], repo_root=repo_root)
    target = validate_runtime_artifact_path(
        selection["principal_authority_records_path"],
        repo_root=repo_root,
        allowed_root=runtime,
    )
    if target != runtime / "principal_authority_records.json":
        raise ValueError("e0_principal_authority_path_invalid")
    raw, _ = secure_read_confined_bytes(
        target, allowed_root=runtime, max_bytes=MAX_ARTIFACT_BYTES
    )
    if not constant_time_compare(
        raw_digest(raw),
        str(selection["principal_authority_records_digest"]),
    ):
        raise ValueError("e0_principal_authority_digest_mismatch")
    return parse_principal_artifact(raw)


def verify_current_generation_principal_identity(
    *, repo_root: Path, selection: Mapping[str, Any],
    identity: Mapping[str, Any], work_authority: Mapping[str, Any],
) -> None:
    """Check principal/key/scope inside the caller's authenticated generation lease.

    This relies on the root-selected subject attestation, not a fresh login.
    It grants no permission and does not authenticate caller-built selections.
    """
    if not isinstance(identity, Mapping) or not isinstance(work_authority, Mapping):
        raise ValueError("current_principal_binding_missing")
    principal, provider, key = (identity.get(name) for name in
        ("principal_id", "principal_provider", "principal_public_key"))
    repo, foundup = (work_authority.get(name) for name in ("repo_full_name", "foundup_id"))
    if any(not isinstance(value, str) or not value for value in
           (principal, provider, key, repo, foundup)):
        raise ValueError("current_principal_binding_invalid")
    record = load_current_generation_principal_authority_resolver(
        repo_root=repo_root, selection=selection).resolve(principal, provider)
    if (record is None or not constant_time_compare(record.principal_public_key, key)
            or work_authority.get("principal_id") != principal
            or repo not in record.repo_scope or foundup not in record.foundup_scope):
        raise ValueError("current_principal_binding_mismatch")


__all__ = [
    "verify_current_generation_principal_identity",
    "CurrentGenerationPrincipalAuthorityResolver",
    "CurrentGenerationPrincipalKeyResolver",
    "load_current_generation_principal_authority_resolver",
    "load_current_generation_principal_key_resolver",
    "load_current_generation_principal_artifact",
]
