"""Receipt construction, cleanup, and finalization proof for acceptance."""

from __future__ import annotations

import hashlib
import os
from typing import Any

from holo_index.freshness_receipt import freshness_receipt_path

from .reddog_holoindex_acceptance_guards import ACCEPTANCE_SCHEMA_VERSION
from .reddog_holoindex_candidate_acceptance_types import (
    CandidateAcceptanceConfig,
    CandidateAcceptanceResult,
    CandidateAcceptanceState as _RunState,
)
from .reddog_holoindex_candidate_query_validation import _raise


SSD_PATH_ENV = "HOLOINDEX_SSD_PATH"


def _restore_environment(state: _RunState) -> None:
    if not state.environment_changed:
        return
    if state.environment_present:
        os.environ[SSD_PATH_ENV] = state.environment_value
    else:
        os.environ.pop(SSD_PATH_ENV, None)
    state.environment_changed = False


def _handoff_digest(handoff: tuple[str, str] | None) -> str:
    if handoff is None:
        return ""
    payload = (handoff[0] + "\0" + handoff[1]).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _receipt_payload(
    config: CandidateAcceptanceConfig, state: _RunState
) -> dict[str, Any]:
    verdict = "FAIL" if state.error else "PASS"
    return {
        "schema_version": ACCEPTANCE_SCHEMA_VERSION,
        "verdict": verdict,
        "error": state.error,
        "expected_repo_head_sha": config.expected_sha.lower(),
        "candidate_root_digest": state.candidate_digest,
        "authority_root_digest": state.authority_digest,
        "owner_runtime_root_digest": state.runtime_digest,
        "model_artifact_digest": state.model_digest,
        "model_file_count": state.model_files,
        "model_total_bytes": state.model_bytes,
        "generation_id": state.generation_id,
        "freshness_receipt_digest": state.receipt_digest,
        "owner_session_digest": state.owner_session_digest,
        "direct_query_count": state.query_count,
        "activation_query_count": state.activation_query_count,
        "activation_query_receipt_digest": (
            state.activation_query_receipt_digest
        ),
        "semantic_store_proof_unchanged": (
            state.semantic_store_proof_unchanged
        ),
        "canonical_receipt_unchanged": state.canonical_unchanged,
    }


def _cleanup_owned(
    dependencies: CandidateAcceptanceDependencies, state: _RunState
) -> BaseException | None:
    if state.owned_handoff is None:
        return None
    try:
        cleaned = dependencies.cleanup_owner(
            restore_environment=True,
            expected_handoff=state.owned_handoff,
        )
    except BaseException as exc:
        state.error = "OWNER_CLEANUP_FAILED"
        return exc if not isinstance(exc, Exception) else None
    if cleaned is False:
        state.error = "OWNER_HANDOFF_OWNERSHIP_CHANGED"
        state.owned_handoff = None
    else:
        state.owned_handoff = None
    return None


def _cleanup_private_owner(
    dependencies: CandidateAcceptanceDependencies, state: _RunState
) -> None:
    pending = _cleanup_owned(dependencies, state)
    if pending is not None:
        raise pending
    if state.error:
        _raise(state.error)
    try:
        leaked = dependencies.resolve_handoff()
    except Exception:
        _raise("OWNER_HANDOFF_RECHECK_FAILED")
    if leaked is not None:
        _raise("OWNER_HANDOFF_LEAKED")


def _require_no_activation_handoff(
    dependencies: CandidateAcceptanceDependencies,
) -> None:
    try:
        leaked = dependencies.resolve_handoff()
    except Exception:
        _raise("ACTIVATION_HANDOFF_RECHECK_FAILED")
    if leaked is not None:
        _raise("ACTIVATION_OWNER_HANDOFF_LEAKED")


def _check_canonical_receipt(
    config: CandidateAcceptanceConfig,
    dependencies: CandidateAcceptanceDependencies,
    state: _RunState,
) -> None:
    if state.canonical_before is None:
        return
    try:
        after = dependencies.read_digest(
            freshness_receipt_path(config.canonical_store),
            allowed_root=config.canonical_store,
            max_bytes=config.max_receipt_bytes,
        )
    except Exception:
        state.error = "CANONICAL_RECEIPT_RECHECK_FAILED"
        return
    state.canonical_unchanged = after == state.canonical_before
    if not state.canonical_unchanged:
        state.error = "CANONICAL_RECEIPT_CHANGED"


def _finalize(
    config: CandidateAcceptanceConfig, dependencies: CandidateAcceptanceDependencies, state: _RunState,
) -> tuple[CandidateAcceptanceResult, BaseException | None]:
    pending: BaseException | None = _cleanup_owned(dependencies, state)
    if not state.error and not state.owner_session_digest:
        state.error = "OWNER_SESSION_PROOF_MISSING"
    try:
        _restore_environment(state)
    except BaseException as exc:
        state.error = "ENVIRONMENT_RESTORE_FAILED"
        if pending is None and not isinstance(exc, Exception):
            pending = exc
    try:
        _check_canonical_receipt(config, dependencies, state)
    except BaseException as exc:
        state.canonical_unchanged = False
        state.error = "CANONICAL_RECEIPT_RECHECK_FAILED"
        if pending is None and not isinstance(exc, Exception):
            pending = exc
    payload = _receipt_payload(config, state)
    try:
        dependencies.publish_receipt(
            config.receipt_path,
            payload,
            allowed_root=config.receipt_path.parent,
            canonical_store=config.canonical_store,
            repo_roots=(config.candidate_root, config.authority_root, config.owner_runtime_root),
            max_bytes=config.max_receipt_bytes,
        )
    except BaseException as exc:
        if pending is None and not isinstance(exc, Exception):
            pending = exc
        return (
            CandidateAcceptanceResult(
                "FAIL", "COMPLETED", "RECEIPT_PUBLICATION_FAILED", False
            ),
            pending,
        )
    verdict = "FAIL" if state.error else "PASS"
    return (
        CandidateAcceptanceResult(
            verdict,
            "COMPLETED",
            state.error,
            True,
            state.generation_id,
            state.receipt_digest,
        ),
        pending,
    )
