"""Exact private route-record and recovery-journal contracts for RedDog Holo."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


ROUTE_SCHEMA_VERSION = "reddog_holoindex_query_route.v1"
JOURNAL_SCHEMA_VERSION = "reddog_holoindex_query_route_journal.v1"
ROUTE_MAX_BYTES = 16 * 1024
JOURNAL_MAX_BYTES = 64 * 1024
MAX_REVISION = (1 << 63) - 1
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_HEAD = re.compile(r"[0-9a-f]{40}\Z")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z")
_CANONICAL_KEYS = frozenset(
    {"repo_head_sha", "repo_root_digest", "generation_id", "receipt_digest"}
)
_REPLICA_KEYS = frozenset(
    {
        "query_replica_descriptor_digest",
        "query_replica_generation_id",
        "query_replica_id",
        "query_replica_path_identity_digest",
    }
)
_ROUTE_KEYS = frozenset(
    {
        "schema_version", "status", "revision", "activation_id",
        "previous_route_digest", "activated_at", "authority_repo_root",
        "replica_root", "canonical", "replica",
    }
)
_JOURNAL_KEYS = frozenset(
    {
        "schema_version", "status", "transition_id", "previous_route_digest",
        "candidate_route_digest", "previous_record", "candidate_record",
    }
)


class QueryRouteContractError(RuntimeError):
    """Stable fail-closed route-contract error."""


def _fail(code: str) -> None:
    raise QueryRouteContractError(code)


@dataclass(frozen=True)
class QueryRouteRecord:
    schema_version: str
    status: str
    revision: int
    activation_id: str
    previous_route_digest: str
    activated_at: str
    authority_repo_root: str
    replica_root: str
    canonical: Mapping[str, str]
    replica: Mapping[str, str]


@dataclass(frozen=True)
class QueryRouteStateProof:
    record: QueryRouteRecord
    digest: str
    encoded: bytes


@dataclass(frozen=True)
class QueryRouteJournal:
    schema_version: str
    status: str
    transition_id: str
    previous_route_digest: str
    candidate_route_digest: str
    previous_record: QueryRouteRecord
    candidate_record: QueryRouteRecord


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if type(key) is not str or key in result:
            _fail("QUERY_ROUTE_JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    _fail("QUERY_ROUTE_JSON_CONSTANT_INVALID")


def _parse_mapping(payload: bytes, *, max_bytes: int, code: str) -> dict[str, Any]:
    if type(payload) is not bytes or not payload or len(payload) > max_bytes:
        _fail(code)
    try:
        value = json.loads(
            payload.decode("ascii"), object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except QueryRouteContractError:
        raise
    except Exception:
        _fail(code)
    if type(value) is not dict:
        _fail(code)
    return value


def _exact_dict(value: object, keys: frozenset[str], code: str) -> dict[str, Any]:
    if type(value) is not dict or frozenset(value) != keys:
        _fail(code)
    return value


def _exact_text(value: object, *, allow_empty: bool = False) -> str:
    if type(value) is not str or value != value.strip():
        _fail("QUERY_ROUTE_TEXT_INVALID")
    if not value and allow_empty:
        return value
    if not value or unicodedata.normalize("NFC", value) != value:
        _fail("QUERY_ROUTE_TEXT_INVALID")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        _fail("QUERY_ROUTE_TEXT_INVALID")
    return value


def _digest(value: object, *, allow_empty: bool = False) -> str:
    text = _exact_text(value, allow_empty=allow_empty)
    if text or not allow_empty:
        if _DIGEST.fullmatch(text) is None:
            _fail("QUERY_ROUTE_DIGEST_INVALID")
    return text


def _absolute_path(value: object, *, allow_empty: bool = False) -> str:
    text = _exact_text(value, allow_empty=allow_empty)
    if text and not Path(text).is_absolute():
        _fail("QUERY_ROUTE_PATH_INVALID")
    return text


def _exact_string_map(
    value: object, keys: frozenset[str], *, allow_empty: bool,
) -> Mapping[str, str]:
    source = _exact_dict(value, keys, "QUERY_ROUTE_BINDING_SHAPE_INVALID")
    result = {key: _exact_text(source[key], allow_empty=allow_empty) for key in keys}
    return MappingProxyType(dict(sorted(result.items())))


def _copy_exact_proxy_map(
    value: object, keys: frozenset[str], *, allow_empty: bool,
) -> Mapping[str, str]:
    if type(value) is not MappingProxyType:
        _fail("QUERY_ROUTE_BINDING_SHAPE_INVALID")
    try:
        snapshot = dict(value)
    except Exception:
        _fail("QUERY_ROUTE_BINDING_SHAPE_INVALID")
    return _exact_string_map(snapshot, keys, allow_empty=allow_empty)


def _validate_current_bindings(record: QueryRouteRecord) -> None:
    if _HEAD.fullmatch(record.canonical["repo_head_sha"]) is None:
        _fail("QUERY_ROUTE_HEAD_INVALID")
    for key in _CANONICAL_KEYS - {"repo_head_sha"}:
        _digest(record.canonical[key])
    for key in _REPLICA_KEYS:
        _digest(record.replica[key])
    if record.replica["query_replica_generation_id"] != record.canonical["generation_id"]:
        _fail("QUERY_ROUTE_GENERATION_MISMATCH")


def _validate_timestamp(value: str) -> None:
    if _UTC.fullmatch(value) is None:
        _fail("QUERY_ROUTE_TIMESTAMP_INVALID")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        _fail("QUERY_ROUTE_TIMESTAMP_INVALID")
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        _fail("QUERY_ROUTE_TIMESTAMP_INVALID")


def validate_route_record(record: QueryRouteRecord) -> QueryRouteRecord:
    if type(record) is not QueryRouteRecord:
        _fail("QUERY_ROUTE_SCHEMA_INVALID")
    schema_version = _exact_text(record.schema_version)
    if schema_version != ROUTE_SCHEMA_VERSION:
        _fail("QUERY_ROUTE_SCHEMA_INVALID")
    status = _exact_text(record.status)
    if type(record.revision) is not int or not 0 <= record.revision <= MAX_REVISION:
        _fail("QUERY_ROUTE_REVISION_INVALID")
    allow_empty = status == "EMPTY"
    canonical = _copy_exact_proxy_map(
        record.canonical, _CANONICAL_KEYS, allow_empty=allow_empty,
    )
    replica = _copy_exact_proxy_map(
        record.replica, _REPLICA_KEYS, allow_empty=allow_empty,
    )
    normalized = QueryRouteRecord(
        schema_version=schema_version,
        status=status,
        revision=record.revision,
        activation_id=_digest(record.activation_id, allow_empty=allow_empty),
        previous_route_digest=_digest(
            record.previous_route_digest, allow_empty=allow_empty,
        ),
        activated_at=_exact_text(record.activated_at, allow_empty=allow_empty),
        authority_repo_root=_absolute_path(
            record.authority_repo_root, allow_empty=allow_empty,
        ),
        replica_root=_absolute_path(record.replica_root, allow_empty=allow_empty),
        canonical=canonical,
        replica=replica,
    )
    if status == "EMPTY":
        values = (
            normalized.activation_id, normalized.previous_route_digest,
            normalized.activated_at, normalized.authority_repo_root,
            normalized.replica_root, *canonical.values(), *replica.values(),
        )
        if normalized.revision != 0 or any(values):
            _fail("QUERY_ROUTE_EMPTY_INVALID")
        return normalized
    if status != "CURRENT" or normalized.revision < 1:
        _fail("QUERY_ROUTE_STATUS_INVALID")
    _validate_timestamp(normalized.activated_at)
    _validate_current_bindings(normalized)
    return normalized


def route_record_from_mapping(value: object) -> QueryRouteRecord:
    source = _exact_dict(value, _ROUTE_KEYS, "QUERY_ROUTE_SHAPE_INVALID")
    status = _exact_text(source["status"])
    allow_empty = status == "EMPTY"
    canonical = _exact_string_map(source["canonical"], _CANONICAL_KEYS, allow_empty=allow_empty)
    replica = _exact_string_map(source["replica"], _REPLICA_KEYS, allow_empty=allow_empty)
    record = QueryRouteRecord(
        schema_version=_exact_text(source["schema_version"]),
        status=status, revision=source["revision"],
        activation_id=_digest(source["activation_id"], allow_empty=allow_empty),
        previous_route_digest=_digest(source["previous_route_digest"], allow_empty=allow_empty),
        activated_at=_exact_text(source["activated_at"], allow_empty=allow_empty),
        authority_repo_root=_absolute_path(source["authority_repo_root"], allow_empty=allow_empty),
        replica_root=_absolute_path(source["replica_root"], allow_empty=allow_empty),
        canonical=canonical, replica=replica,
    )
    return validate_route_record(record)


def route_record_mapping(record: QueryRouteRecord) -> dict[str, Any]:
    valid = validate_route_record(record)
    return {
        "schema_version": valid.schema_version, "status": valid.status,
        "revision": valid.revision, "activation_id": valid.activation_id,
        "previous_route_digest": valid.previous_route_digest,
        "activated_at": valid.activated_at,
        "authority_repo_root": valid.authority_repo_root,
        "replica_root": valid.replica_root,
        "canonical": dict(valid.canonical), "replica": dict(valid.replica),
    }


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def prove_route_record(record: QueryRouteRecord) -> QueryRouteStateProof:
    valid = validate_route_record(record)
    encoded = _canonical_bytes(route_record_mapping(valid))
    if len(encoded) > ROUTE_MAX_BYTES:
        _fail("QUERY_ROUTE_SIZE_INVALID")
    digest = "sha256:" + hashlib.sha256(encoded).hexdigest()
    return QueryRouteStateProof(record=valid, digest=digest, encoded=encoded)


def parse_route_record_bytes(payload: bytes) -> QueryRouteStateProof:
    mapping = _parse_mapping(payload, max_bytes=ROUTE_MAX_BYTES, code="QUERY_ROUTE_JSON_INVALID")
    proof = prove_route_record(route_record_from_mapping(mapping))
    if proof.encoded != payload:
        _fail("QUERY_ROUTE_JSON_NOT_CANONICAL")
    return proof


def empty_route_record() -> QueryRouteRecord:
    empty_canonical = MappingProxyType({key: "" for key in sorted(_CANONICAL_KEYS)})
    empty_replica = MappingProxyType({key: "" for key in sorted(_REPLICA_KEYS)})
    return QueryRouteRecord(
        ROUTE_SCHEMA_VERSION, "EMPTY", 0, "", "", "", "", "",
        empty_canonical, empty_replica,
    )


def route_journal_mapping(journal: QueryRouteJournal) -> dict[str, Any]:
    valid = validate_route_journal(journal)
    return {
        "schema_version": valid.schema_version, "status": valid.status,
        "transition_id": valid.transition_id,
        "previous_route_digest": valid.previous_route_digest,
        "candidate_route_digest": valid.candidate_route_digest,
        "previous_record": route_record_mapping(valid.previous_record),
        "candidate_record": route_record_mapping(valid.candidate_record),
    }


def validate_route_journal(journal: QueryRouteJournal) -> QueryRouteJournal:
    if type(journal) is not QueryRouteJournal:
        _fail("QUERY_ROUTE_JOURNAL_SCHEMA_INVALID")
    schema_version = _exact_text(journal.schema_version)
    if schema_version != JOURNAL_SCHEMA_VERSION:
        _fail("QUERY_ROUTE_JOURNAL_SCHEMA_INVALID")
    status = _exact_text(journal.status)
    if status not in {"PREPARED", "COMMITTED", "ROLLED_BACK"}:
        _fail("QUERY_ROUTE_JOURNAL_STATUS_INVALID")
    transition_id = _digest(journal.transition_id)
    previous_route_digest = _digest(journal.previous_route_digest)
    candidate_route_digest = _digest(journal.candidate_route_digest)
    previous = prove_route_record(journal.previous_record)
    candidate = prove_route_record(journal.candidate_record)
    if previous_route_digest != previous.digest or candidate_route_digest != candidate.digest:
        _fail("QUERY_ROUTE_JOURNAL_BINDING_INVALID")
    if (
        transition_id != candidate.record.activation_id
        or candidate.record.status != "CURRENT"
        or candidate.record.revision != previous.record.revision + 1
        or candidate.record.previous_route_digest != previous.digest
    ):
        _fail("QUERY_ROUTE_JOURNAL_BINDING_INVALID")
    return QueryRouteJournal(
        schema_version=schema_version,
        status=status,
        transition_id=transition_id,
        previous_route_digest=previous_route_digest,
        candidate_route_digest=candidate_route_digest,
        previous_record=previous.record,
        candidate_record=candidate.record,
    )


def encode_route_journal(journal: QueryRouteJournal) -> bytes:
    encoded = _canonical_bytes(route_journal_mapping(journal))
    if len(encoded) > JOURNAL_MAX_BYTES:
        _fail("QUERY_ROUTE_JOURNAL_SIZE_INVALID")
    return encoded


def parse_route_journal_bytes(payload: bytes) -> QueryRouteJournal:
    mapping = _parse_mapping(payload, max_bytes=JOURNAL_MAX_BYTES, code="QUERY_ROUTE_JOURNAL_JSON_INVALID")
    source = _exact_dict(mapping, _JOURNAL_KEYS, "QUERY_ROUTE_JOURNAL_SHAPE_INVALID")
    journal = QueryRouteJournal(
        schema_version=_exact_text(source["schema_version"]),
        status=_exact_text(source["status"]),
        transition_id=_digest(source["transition_id"]),
        previous_route_digest=_digest(source["previous_route_digest"]),
        candidate_route_digest=_digest(source["candidate_route_digest"]),
        previous_record=route_record_from_mapping(source["previous_record"]),
        candidate_record=route_record_from_mapping(source["candidate_record"]),
    )
    journal = validate_route_journal(journal)
    if encode_route_journal(journal) != payload:
        _fail("QUERY_ROUTE_JOURNAL_JSON_NOT_CANONICAL")
    return journal


__all__ = [
    "JOURNAL_MAX_BYTES", "JOURNAL_SCHEMA_VERSION", "QueryRouteContractError",
    "QueryRouteJournal", "QueryRouteRecord", "QueryRouteStateProof",
    "ROUTE_MAX_BYTES", "ROUTE_SCHEMA_VERSION", "empty_route_record",
    "encode_route_journal", "parse_route_journal_bytes",
    "parse_route_record_bytes", "prove_route_record", "route_journal_mapping",
    "route_record_from_mapping", "route_record_mapping",
    "validate_route_journal", "validate_route_record",
]
