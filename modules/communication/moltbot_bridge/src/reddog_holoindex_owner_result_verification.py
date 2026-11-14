"""Verify independently queried HoloIndex owner results before repair effects."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Mapping

from holo_index.authority_worktree import HoloIndexAuthoritySelection
from holo_index.query_receipt import (
    SCHEMA_VERSION as QUERY_RECEIPT_SCHEMA,
    canonical_semantic_evidence,
    digest_json,
)

from modules.communication.moltbot_bridge.src.reddog_holoindex_incident_repair_contract import (
    REPAIRABLE_ERRORS,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_acquisition import (
    MAX_OWNER_ATTEMPTS,
    TRANSIENT_OWNER_ERRORS,
    owner_acquisition_cycle_valid,
)
from modules.infrastructure.idle_automation.src.holoindex_postmerge_contract import (
    REPO_HEAD_MISMATCH,
)


CURRENT = "CURRENT"
INVALID = "INVALID"
REPAIRABLE = "REPAIRABLE"
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")


def _receipt_integrity(receipt: Mapping[str, Any]) -> bool:
    payload = {key: value for key, value in receipt.items() if key != "receipt_id"}
    try:
        expected = digest_json(payload)
    except (TypeError, ValueError, RecursionError):
        return False
    return bool(receipt.get("schema_version") == QUERY_RECEIPT_SCHEMA
                and receipt.get("receipt_id") == expected)


def _binding_checks(
    result: Mapping[str, Any],
    receipt: Mapping[str, Any],
    query: str,
    selection: HoloIndexAuthoritySelection,
) -> tuple[bool, ...]:
    return (
        result.get("source") == "holoindex_owner_service",
        result.get("query") == query,
        receipt.get("source") == "holoindex_owner_service",
        receipt.get("source_class") == "holoindex",
        receipt.get("query") == query,
        result.get("repo_head_sha") == selection.authority_head_sha,
        receipt.get("repo_head_sha") == selection.authority_head_sha,
        result.get("repo_root_digest") == selection.authority_root_digest,
        receipt.get("repo_root_digest") == selection.authority_root_digest,
        result.get("workspace_repo_head_sha") == selection.workspace_head_sha,
        receipt.get("workspace_repo_head_sha") == selection.workspace_head_sha,
        result.get("authority_repo_head_sha") == selection.authority_head_sha,
        receipt.get("authority_repo_head_sha") == selection.authority_head_sha,
        result.get("authority_repo_root_digest") == selection.authority_root_digest,
        receipt.get("authority_repo_root_digest") == selection.authority_root_digest,
        result.get("no_authority_worktree_mutation_performed") is True,
        receipt.get("no_authority_worktree_mutation_performed") is True,
        result.get("no_holoindex_reindex_performed") is True,
        receipt.get("no_holoindex_reindex_performed") is True,
    )


def _semantic_evidence_valid(
    result: Mapping[str, Any], receipt: Mapping[str, Any]
) -> bool:
    try:
        serialized, digest, count = canonical_semantic_evidence(
            result.get("raw_result")
        )
    except ValueError:
        return False
    return bool(
        result.get("semantic_evidence_json") == serialized
        and receipt.get("semantic_evidence_digest") == digest
        and receipt.get("semantic_evidence_count") == count
    )


def _owner_attempts(result: Mapping[str, Any]) -> int:
    value = result.get("owner_attempts")
    return value if type(value) is int else 0


def _owner_telemetry_is_bound(
    result: Mapping[str, Any], receipt: Mapping[str, Any]
) -> bool:
    validators = {
        "owner_attempts": lambda value: type(value) is int and value >= 0,
        "owner_retry_performed": lambda value: type(value) is bool,
        "owner_retry_reason": lambda value: type(value) is str,
        "owner_acquisition_cycle": owner_acquisition_cycle_valid,
    }
    for field, valid in validators.items():
        if field not in result and field not in receipt:
            continue
        result_value = result.get(field)
        receipt_value = receipt.get(field)
        if not valid(result_value) or not valid(receipt_value):
            return False
        if type(result_value) is not type(receipt_value) or result_value != receipt_value:
            return False
    return True


def _digest(value: Any) -> bool:
    return type(value) is str and DIGEST_RE.fullmatch(value) is not None


def is_bound_preowner_repo_head_mismatch(
    result: Mapping[str, Any], *, query: str,
    selection: HoloIndexAuthoritySelection,
) -> bool:
    """Verify a fail-closed exact-HEAD rejection before owner acquisition."""
    stale_reasons = result.get("stale_reasons")
    return bool(
        result.get("ok") is False
        and result.get("source") == "holoindex_owner_service"
        and result.get("query") == query
        and result.get("freshness") == "STALE"
        and result.get("error") == REPO_HEAD_MISMATCH
        and result.get("index_gap_detected") is True
        and type(result.get("owner_attempts")) is int
        and result.get("owner_attempts") == 0
        and result.get("owner_retry_performed") is False
        and result.get("owner_retry_reason") == ""
        and type(result.get("owner_acquisition_cycle")) is int
        and result.get("owner_acquisition_cycle") == 0
        and type(result.get("repo_head_sha")) is str
        and SHA_RE.fullmatch(result["repo_head_sha"]) is not None
        and result.get("repo_head_sha") != selection.authority_head_sha
        and result.get("repo_root_digest") == selection.authority_root_digest
        and result.get("workspace_repo_head_sha") == selection.workspace_head_sha
        and result.get("authority_repo_head_sha") == selection.authority_head_sha
        and result.get("authority_repo_root_digest") == selection.authority_root_digest
        and result.get("no_authority_worktree_mutation_performed") is True
        and result.get("no_holoindex_reindex_performed") is True
        and result.get("no_reindex") is True
        and result.get("workspace_overlay_present") is False
        and result.get("semantic_evidence_authority") == "committed_head_only"
        and result.get("raw_result") == {}
        and "query_receipt" not in result
        and isinstance(stale_reasons, list)
        and 0 < len(stale_reasons) <= 16
        and all(type(reason) is str and len(reason) <= 128 for reason in stale_reasons)
        and "stale_repo_head_sha" in stale_reasons
        and _digest(result.get("freshness_generation_id"))
        and _digest(result.get("freshness_receipt_digest"))
    )


def _verified_receipt(
    result: Mapping[str, Any],
    *,
    query: str,
    selection: HoloIndexAuthoritySelection,
) -> Mapping[str, Any] | None:
    receipt = result.get("query_receipt")
    if not isinstance(receipt, Mapping):
        return None
    if type(result.get("error")) is not str or type(receipt.get("error")) is not str:
        return None
    if not all((
        _receipt_integrity(receipt),
        *_binding_checks(result, receipt, query, selection),
        _semantic_evidence_valid(result, receipt),
        receipt.get("ok") is (result.get("ok") is True),
        receipt.get("freshness") == result.get("freshness"),
        receipt.get("error") == result.get("error"),
        receipt.get("index_gap_detected") is (result.get("index_gap_detected") is True),
        _owner_telemetry_is_bound(result, receipt),
    )):
        return None
    return receipt


def classify_verified_owner_result(
    result: Mapping[str, Any],
    *,
    query: str,
    selection: HoloIndexAuthoritySelection,
) -> str:
    """Classify one independently produced, receipt-bound owner result."""

    receipt = _verified_receipt(
        result, query=query, selection=selection
    )
    if receipt is None:
        return INVALID
    if (
        result.get("ok") is True
        and result.get("freshness") == CURRENT
        and result.get("index_gap_detected") is False
        and _digest(result.get("freshness_generation_id"))
        and _digest(result.get("freshness_receipt_digest"))
        and result.get("freshness_generation_id")
        == receipt.get("freshness_generation_id")
        and result.get("freshness_receipt_digest")
        == receipt.get("freshness_receipt_digest")
    ):
        return CURRENT
    if (
        result.get("ok") is False
        and result.get("error") in REPAIRABLE_ERRORS
        and result.get("index_gap_detected") is True
        and _owner_attempts(result) >= 2
    ):
        return REPAIRABLE
    return INVALID


def is_verified_transient_owner_result(
    result: Mapping[str, Any],
    *,
    query: str,
    selection: HoloIndexAuthoritySelection,
) -> bool:
    """Admit one controller retry only for an exhausted authenticated transient."""

    receipt = _verified_receipt(
        result, query=query, selection=selection
    )
    error = result.get("error")
    retry_reason = result.get("owner_retry_reason")
    return bool(
        receipt is not None
        and result.get("ok") is False
        and type(error) is str
        and error in TRANSIENT_OWNER_ERRORS
        and result.get("index_gap_detected") is True
        and _owner_attempts(result) == MAX_OWNER_ATTEMPTS
        and result.get("owner_retry_performed") is True
        and type(retry_reason) is str
        and retry_reason in TRANSIENT_OWNER_ERRORS
    )


def query_and_classify_owner_result(
    *,
    query: str,
    selection: HoloIndexAuthoritySelection,
    workspace_repo_root: Path | str,
    query_runner: Callable[..., Mapping[str, Any]],
    operation_timeout_seconds: float | None = None,
) -> tuple[str, Mapping[str, Any]]:
    try:
        kwargs: dict[str, Any] = {
            "repo_root": Path(workspace_repo_root).resolve(strict=False)
        }
        if operation_timeout_seconds is not None:
            kwargs["operation_timeout_seconds"] = operation_timeout_seconds
        result = query_runner({"query": query, "limit": 5}, **kwargs)
    except Exception:
        return INVALID, {}
    if not isinstance(result, Mapping):
        return INVALID, {}
    status = classify_verified_owner_result(
        result, query=query, selection=selection
    )
    return status, result


__all__ = [
    "CURRENT",
    "INVALID",
    "REPAIRABLE",
    "classify_verified_owner_result",
    "is_bound_preowner_repo_head_mismatch",
    "is_verified_transient_owner_result",
    "query_and_classify_owner_result",
]
