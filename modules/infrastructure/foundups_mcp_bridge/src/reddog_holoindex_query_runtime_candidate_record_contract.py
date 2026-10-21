"""Exact contract for RECORD rows excluded from a query candidate payload."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping

from .reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    digest_bytes,
    is_digest,
)


_KEYS = frozenset({"path", "size", "sha256", "distribution", "reason"})
_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_RESERVED = frozenset({
    "con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
})


class CandidateRecordContractError(RuntimeError):
    """Stable fail-closed excluded RECORD contract error."""


def _fail(code: str) -> None:
    raise CandidateRecordContractError(code)


def validate_excluded_record_entries(
    value: object, distributions: list[Mapping[str, Any]], *,
    max_files: int, max_path_bytes: int, max_file_bytes: int,
) -> list[dict[str, Any]]:
    """Validate canonical prefix-local exclusions and exact distribution owners."""

    if type(value) is not list or len(value) > max_files:
        _fail("QUERY_RUNTIME_CANDIDATE_EXCLUDED_RECORD_INVALID")
    rows = [
        _entry(row, max_path_bytes=max_path_bytes, max_file_bytes=max_file_bytes)
        for row in value
    ]
    keys = [f"{row['path']}:{row['distribution']}" for row in rows]
    normalized = [unicodedata.normalize("NFC", key).casefold() for key in keys]
    if normalized != sorted(normalized) or len(normalized) != len(set(normalized)):
        _fail("QUERY_RUNTIME_CANDIDATE_EXCLUDED_RECORD_ORDER_INVALID")
    owners = {str(row["name"]) for row in distributions}
    if any(row["distribution"] not in owners for row in rows):
        _fail("QUERY_RUNTIME_CANDIDATE_EXCLUDED_RECORD_INVALID")
    return rows


def bind_excluded_record_entries(
    distributions: list[Mapping[str, Any]], rows: list[Mapping[str, Any]],
) -> None:
    """Bind each distribution's exact excluded rows to its count and digest."""

    for distribution in distributions:
        selected = [
            row for row in rows if row["distribution"] == distribution["name"]
        ]
        if (
            distribution["excluded_record_entry_count"] != len(selected)
            or distribution["excluded_record_entries_digest"]
            != digest_bytes(canonical_json_bytes(selected))
        ):
            _fail("QUERY_RUNTIME_CANDIDATE_EXCLUDED_RECORD_BINDING_INVALID")


def _entry(
    value: object, *, max_path_bytes: int, max_file_bytes: int,
) -> dict[str, Any]:
    if type(value) is not dict or frozenset(value) != _KEYS:
        _fail("QUERY_RUNTIME_CANDIDATE_EXCLUDED_RECORD_INVALID")
    row = dict(value)
    path, owner = row.get("path"), row.get("distribution")
    parts = path.split("/") if type(path) is str else []
    blank_identity = row.get("sha256") == "" and row.get("size") is None
    if (
        type(path) is not str or len(parts) < 3 or parts[0] != "@prefix"
        or path.casefold().startswith("@prefix/lib/site-packages/")
        or "\\" in path or ":" in path
        or unicodedata.normalize("NFC", path) != path
        or _unsafe_parts(parts[1:]) or len(path.encode("utf-8")) > max_path_bytes
        or _invalid_identity(row, blank_identity, max_file_bytes)
        or (blank_identity and not path.casefold().endswith(".pyc"))
        or type(owner) is not str or _NAME.fullmatch(owner) is None
        or row.get("reason") != "external_distribution_payload_excluded"
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_EXCLUDED_RECORD_INVALID")
    return row


def _unsafe_parts(parts: list[str]) -> bool:
    return any(
        part in {"", ".", ".."} or part[-1:] in {" ", "."}
        or part.split(".", 1)[0].casefold() in _RESERVED
        or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in part)
        for part in parts
    )


def _invalid_identity(
    row: Mapping[str, Any], blank_identity: bool, maximum: int,
) -> bool:
    return bool(
        not blank_identity and (
            type(row.get("size")) is not int or row["size"] < 0
            or row["size"] > maximum or not is_digest(row.get("sha256"))
        )
    )


__all__ = [
    "CandidateRecordContractError", "bind_excluded_record_entries",
    "validate_excluded_record_entries",
]
