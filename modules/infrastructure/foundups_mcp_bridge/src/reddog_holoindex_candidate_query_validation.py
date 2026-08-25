"""Pure query and activation-proof validation for candidate acceptance."""

from __future__ import annotations

from typing import Any, Mapping

from holo_index.query_receipt import digest_json

from . import reddog_holoindex_maintenance_handshake as maintenance_handshake


K1_ACCEPTANCE_QUERY = (
    "trusted-host isolated Holo candidate acceptance linked worktree dedicated "
    "store receipt model digest port ownership maintenance session"
)
K12_INCIDENT_QUERY = (
    "HoloDAE PQN training system UTF8 hygiene MCP testing unicode tools pfmall "
    "Tier0 contracts"
)
class CandidateAcceptanceError(RuntimeError):
    """Stable, secret-free candidate-acceptance failure."""


def _raise(code: str) -> None:
    raise CandidateAcceptanceError(code)


def _stable_operational_error(value: object) -> bool:
    public_errors = {
        maintenance_handshake.DIRTY_ERROR,
        maintenance_handshake.EXTERNAL_OWNER_ERROR,
        maintenance_handshake.MAINTENANCE_REQUIRED_ERROR,
        maintenance_handshake.RECEIPT_INVALID_ERROR,
        maintenance_handshake.REFRESH_FAILED_ERROR,
        maintenance_handshake.REFRESH_TIMEOUT_ERROR,
        maintenance_handshake.REPOSITORY_CHANGED_ERROR,
        maintenance_handshake.TIMEOUT_INVALID_ERROR,
    }
    return isinstance(value, str) and (
        value in public_errors
        or value in maintenance_handshake._STABLE_MAINTENANCE_ERRORS
    )


def _validate_operational(result: Any, expected_sha: str) -> None:
    if not (
        result.ready is True
        and result.refreshed is True
        and result.status == "REFRESHED"
        and str(result.repo_head_sha).lower() == expected_sha.lower()
        and str(result.generation_id).startswith("sha256:")
        and str(result.freshness_receipt_digest).startswith("sha256:")
    ):
        _raise("OPERATIONAL_REFRESH_PROOF_INVALID")


def _validate_query(
    result: Mapping[str, Any],
    *,
    expected_sha: str,
    generation_id: str,
    receipt_digest: str,
) -> None:
    if not (
        result.get("ok") is True
        and result.get("freshness") == "CURRENT"
        and result.get("index_gap_detected") is False
        and str(result.get("repo_head_sha", "")).lower() == expected_sha.lower()
        and result.get("freshness_generation_id") == generation_id
        and result.get("freshness_receipt_digest") == receipt_digest
        and result.get("no_holoindex_reindex_performed") is True
    ):
        _raise("DIRECT_QUERY_PROOF_INVALID")


def _validate_rehydration(
    admission: Any,
    *,
    expected_sha: str,
    generation_id: str,
    receipt_digest: str,
) -> None:
    binding = admission.binding if isinstance(admission.binding, Mapping) else {}
    if not (
        admission.allowed is True
        and admission.freshness == "CURRENT"
        and str(binding.get("repo_head_sha", "")).lower() == expected_sha.lower()
        and binding.get("freshness_generation_id") == generation_id
        and binding.get("freshness_receipt_digest") == receipt_digest
    ):
        _raise("FINAL_REHYDRATION_PROOF_INVALID")


def _replica_binding_valid(
    result: Mapping[str, Any],
    expected_replica_binding: Mapping[str, str] | None,
) -> bool:
    if expected_replica_binding is None:
        return True
    return all(
        result.get(key) == expected_replica_binding.get(key)
        for key in (
            "query_replica_descriptor_digest",
            "query_replica_generation_id",
            "query_replica_id",
            "query_replica_path_identity_digest",
        )
    )


def _activation_binding_valid(
    result: Mapping[str, Any],
    *,
    expected_query: str,
    expected_sha: str,
    expected_root_digest: str,
    generation_id: str,
    receipt_digest: str,
    expected_replica_binding: Mapping[str, str] | None = None,
) -> bool:
    return bool(
        result.get("ok") is True
        and result.get("query") == expected_query
        and result.get("freshness") == "CURRENT"
        and result.get("index_gap_detected") is False
        and result.get("no_holoindex_reindex_performed") is True
        and result.get("no_reindex") is True
        and str(result.get("repo_head_sha", "")).lower()
        == expected_sha.lower()
        and result.get("freshness_generation_id") == generation_id
        and result.get("freshness_receipt_digest") == receipt_digest
        and result.get("repo_root_digest") == expected_root_digest
        and str(result.get("workspace_repo_head_sha", "")).lower()
        == expected_sha.lower()
        and str(result.get("authority_repo_head_sha", "")).lower()
        == expected_sha.lower()
        and result.get("authority_repo_root_digest") == expected_root_digest
        and result.get("workspace_overlay_present") is False
        and result.get("semantic_evidence_authority")
        == "clean_workspace_head"
        and _replica_binding_valid(result, expected_replica_binding)
    )


def _activation_receipt_valid(
    query_receipt: Mapping[str, Any],
    *,
    expected_query: str,
    expected_sha: str,
    expected_root_digest: str,
    generation_id: str,
    receipt_digest: str,
    require_semantic_evidence: bool,
) -> str:
    receipt_payload = dict(query_receipt)
    claimed_id = receipt_payload.pop("receipt_id", "")
    if not (
        isinstance(claimed_id, str)
        and claimed_id.startswith("sha256:")
        and digest_json(receipt_payload) == claimed_id
        and query_receipt.get("ok") is True
        and query_receipt.get("query") == expected_query
        and query_receipt.get("freshness") == "CURRENT"
        and query_receipt.get("index_gap_detected") is False
        and query_receipt.get("no_holoindex_reindex_performed") is True
        and str(query_receipt.get("repo_head_sha", "")).lower()
        == expected_sha.lower()
        and query_receipt.get("freshness_generation_id") == generation_id
        and query_receipt.get("freshness_receipt_digest") == receipt_digest
        and query_receipt.get("repo_root_digest") == expected_root_digest
        and query_receipt.get("authority_repo_root_digest")
        == expected_root_digest
        and (
            not require_semantic_evidence
            or (
                type(query_receipt.get("semantic_evidence_count")) is int
                and query_receipt.get("semantic_evidence_count") >= 1
            )
        )
    ):
        _raise("ACTIVATION_QUERY_RECEIPT_INVALID")
    return claimed_id


def validate_activation_query(
    result: Mapping[str, Any],
    *,
    expected_query: str,
    expected_sha: str,
    expected_root_digest: str,
    generation_id: str,
    receipt_digest: str,
    expected_replica_binding: Mapping[str, str] | None = None,
) -> str:
    if not _activation_binding_valid(
        result,
        expected_query=expected_query,
        expected_sha=expected_sha,
        expected_root_digest=expected_root_digest,
        generation_id=generation_id,
        receipt_digest=receipt_digest,
        expected_replica_binding=expected_replica_binding,
    ) or result.get("no_authority_worktree_mutation_performed") is not True:
        _raise("ACTIVATION_QUERY_PROOF_INVALID")
    if expected_replica_binding is not None and not result.get("hits"):
        _raise("ACTIVATION_QUERY_PROOF_INVALID")
    query_receipt = result.get("query_receipt")
    if not isinstance(query_receipt, Mapping):
        _raise("ACTIVATION_QUERY_RECEIPT_INVALID")
    return _activation_receipt_valid(
        query_receipt,
        expected_query=expected_query,
        expected_sha=expected_sha,
        expected_root_digest=expected_root_digest,
        generation_id=generation_id,
        receipt_digest=receipt_digest,
        require_semantic_evidence=expected_replica_binding is not None,
    )


def _validate_activation_query(
    result: Mapping[str, Any],
    *,
    expected_sha: str,
    expected_root_digest: str,
    generation_id: str,
    receipt_digest: str,
) -> str:
    return validate_activation_query(
        result,
        expected_query=K1_ACCEPTANCE_QUERY,
        expected_sha=expected_sha,
        expected_root_digest=expected_root_digest,
        generation_id=generation_id,
        receipt_digest=receipt_digest,
    )
