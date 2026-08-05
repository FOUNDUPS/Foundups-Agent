"""Current-generation principal authority for signer E0 admission."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityRecord,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    MAX_ARTIFACT_BYTES,
    ascii_deep,
    is_sha256,
    raw_digest,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    constant_time_compare,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_bytes,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


SCHEMA_VERSION = "reddog_authority_runtime_resolver_supply.v1"
TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "principals",
        "principal_count",
        "resolver_supply_receipt_id",
        "no_holoindex_reindex_performed",
    }
)
RECORD_FIELDS = frozenset(
    {
        "principal_id",
        "principal_provider",
        "principal_public_key",
        "repo_scope",
        "foundup_scope",
        "verified_subject_digest",
        "reward_account",
        "owner_dae",
        "principal_wallet",
    }
)


class CurrentGenerationPrincipalKeyResolver:
    """Resolve keys only from a manifest-bound principal artifact."""

    def __init__(self, records: Mapping[str, PrincipalAuthorityRecord]) -> None:
        self._records = dict(records)

    def resolve(self, principal_id: str, principal_provider: str) -> str | None:
        record = self._records.get(_key(principal_id, principal_provider))
        return record.principal_public_key if record is not None else None


class CurrentGenerationPrincipalAuthorityResolver:
    """Resolve full principal records from one manifest-bound generation."""

    def __init__(self, records: Mapping[str, PrincipalAuthorityRecord]) -> None:
        self._records = dict(records)

    def resolve(
        self, principal_id: str, principal_provider: str
    ) -> PrincipalAuthorityRecord | None:
        return self._records.get(_key(principal_id, principal_provider))

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
    return _parse_records(raw)


def _parse_records(raw: bytes) -> Mapping[str, PrincipalAuthorityRecord]:
    try:
        payload = json.loads(
            raw.decode("ascii"), object_pairs_hook=_unique_object
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("e0_principal_authority_malformed") from exc
    values = payload.get("principals") if isinstance(payload, Mapping) else None
    if (
        set(payload) != TOP_LEVEL_FIELDS
        or payload.get("schema_version") != SCHEMA_VERSION
        or not isinstance(values, Mapping)
        or type(payload.get("principal_count")) is not int
        or payload.get("principal_count") != len(values)
        or not is_sha256(payload.get("resolver_supply_receipt_id"))
        or payload.get("no_holoindex_reindex_performed") is not True
    ):
        raise ValueError("e0_principal_authority_shape_invalid")
    records: dict[str, PrincipalAuthorityRecord] = {}
    try:
        for claimed_key, value in values.items():
            if not isinstance(value, Mapping):
                raise ValueError("e0_principal_authority_shape_invalid")
            if set(value) != RECORD_FIELDS or not ascii_deep(value):
                raise ValueError("e0_principal_authority_shape_invalid")
            record = _record(value)
            canonical_key = _key(record.principal_id, record.principal_provider)
            if str(claimed_key) != canonical_key:
                raise ValueError("e0_principal_authority_key_invalid")
            if canonical_key in records:
                raise ValueError("e0_principal_authority_duplicate")
            records[canonical_key] = record
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("e0_principal_authority_record_invalid") from exc
    return records


def _record(value: Mapping[str, Any]) -> PrincipalAuthorityRecord:
    text = (
        value["principal_id"],
        value["principal_provider"],
        value["principal_public_key"],
    )
    repo_scope = tuple(value.get("repo_scope") or ())
    foundup_scope = tuple(value.get("foundup_scope") or ())
    if (
        any(not _text(item) for item in text)
        or not repo_scope
        or not foundup_scope
        or any(not _text(item) for item in (*repo_scope, *foundup_scope))
        or not is_sha256(value.get("verified_subject_digest"))
    ):
        raise ValueError("e0_principal_authority_value_invalid")
    return PrincipalAuthorityRecord(
        principal_id=str(value["principal_id"]),
        principal_provider=str(value["principal_provider"]),
        principal_public_key=str(value["principal_public_key"]),
        repo_scope=tuple(str(item) for item in value.get("repo_scope") or ()),
        foundup_scope=tuple(
            str(item) for item in value.get("foundup_scope") or ()
        ),
        verified_subject_digest=str(value["verified_subject_digest"]),
        reward_account=_optional(value.get("reward_account")),
        owner_dae=_optional(value.get("owner_dae")),
        principal_wallet=_optional(value.get("principal_wallet")),
    )


def _optional(value: Any) -> str | None:
    if value is None:
        return None
    if not _text(value):
        raise ValueError("e0_principal_authority_value_invalid")
    return str(value)


def _text(value: Any) -> bool:
    return bool(
        isinstance(value, str)
        and value.strip()
        and value.isascii()
        and len(value) <= 1024
    )


def _key(principal_id: str, principal_provider: str) -> str:
    return f"{principal_provider}|{principal_id}"


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("e0_principal_authority_duplicate_json_key")
        value[key] = item
    return value


__all__ = [
    "CurrentGenerationPrincipalAuthorityResolver",
    "CurrentGenerationPrincipalKeyResolver",
    "load_current_generation_principal_authority_resolver",
    "load_current_generation_principal_key_resolver",
]
