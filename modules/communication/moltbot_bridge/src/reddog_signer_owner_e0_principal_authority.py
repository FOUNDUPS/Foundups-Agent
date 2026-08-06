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
    parse_principal_records,
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
    return parse_principal_records(raw)


__all__ = [
    "CurrentGenerationPrincipalAuthorityResolver",
    "CurrentGenerationPrincipalKeyResolver",
    "load_current_generation_principal_authority_resolver",
    "load_current_generation_principal_key_resolver",
]
