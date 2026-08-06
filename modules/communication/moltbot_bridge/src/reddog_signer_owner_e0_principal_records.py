"""Strict parser for manifest-bound signer principal authority records."""

from __future__ import annotations

import json
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityRecord,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    ascii_deep,
    is_sha256,
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


def parse_principal_records(raw: bytes) -> Mapping[str, PrincipalAuthorityRecord]:
    try:
        payload = json.loads(raw.decode("ascii"), object_pairs_hook=_unique_object)
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
            canonical_key = principal_record_key(
                record.principal_id, record.principal_provider
            )
            if str(claimed_key) != canonical_key:
                raise ValueError("e0_principal_authority_key_invalid")
            if canonical_key in records:
                raise ValueError("e0_principal_authority_duplicate")
            records[canonical_key] = record
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("e0_principal_authority_record_invalid") from exc
    return records


def principal_record_key(principal_id: str, principal_provider: str) -> str:
    return f"{principal_provider}|{principal_id}"


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
        repo_scope=tuple(str(item) for item in repo_scope),
        foundup_scope=tuple(str(item) for item in foundup_scope),
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


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("e0_principal_authority_duplicate_json_key")
        value[key] = item
    return value


__all__ = ["parse_principal_records", "principal_record_key"]
