"""Exact-HEAD pre-owner incident admission and containment tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from holo_index.authority_worktree import HoloIndexAuthoritySelection
from holo_index.query_receipt import build_query_receipt, canonical_semantic_evidence
from modules.communication.moltbot_bridge.src import (
    reddog_holoindex_owner_result_verification as owner_verification,
)
from modules.communication.moltbot_bridge.src.reddog_holoindex_incident_repair_runtime import (
    coordinate_holoindex_incident_repair,
)


HEAD = "a" * 40
ROOT_DIGEST = "sha256:" + ("b" * 64)
GENERATION = "sha256:" + ("c" * 64)
FRESHNESS = "sha256:" + ("d" * 64)
STALE_HEAD = "e" * 40
QUERY = "repair HoloIndex owner"
TASK_ID = "holoindex_postmerge_refresh:" + HEAD


def _selection(root: Path) -> HoloIndexAuthoritySelection:
    return HoloIndexAuthoritySelection(
        True, root, HEAD, HEAD, ROOT_DIGEST, True, "authority_worktree"
    )


def _preowner_failure(**changes):
    value = {
        "ok": False,
        "source": "holoindex_owner_service",
        "query": QUERY,
        "freshness": "STALE",
        "error": "REPO_HEAD_MISMATCH",
        "index_gap_detected": True,
        "raw_result": {},
        "no_holoindex_reindex_performed": True,
        "no_reindex": True,
        "owner_attempts": 0,
        "owner_retry_performed": False,
        "owner_retry_reason": "",
        "owner_acquisition_cycle": 0,
        "repo_head_sha": STALE_HEAD,
        "repo_root_digest": ROOT_DIGEST,
        "freshness_generation_id": GENERATION,
        "freshness_receipt_digest": FRESHNESS,
        "workspace_repo_head_sha": HEAD,
        "authority_repo_head_sha": HEAD,
        "authority_repo_root_digest": ROOT_DIGEST,
        "workspace_overlay_present": False,
        "semantic_evidence_authority": "committed_head_only",
        "no_authority_worktree_mutation_performed": True,
        "stale_reasons": ["stale_repo_head_sha"],
    }
    value.update(changes)
    return value


def _receipt_bound_failure(error: str = "SEMANTIC_BACKEND_UNAVAILABLE"):
    result = {
        "ok": False,
        "source": "holoindex_owner_service",
        "query": QUERY,
        "freshness": "UNKNOWN",
        "error": error,
        "index_gap_detected": True,
        "raw_result": {},
        "no_holoindex_reindex_performed": True,
        "owner_attempts": 2,
        "repo_head_sha": HEAD,
        "repo_root_digest": ROOT_DIGEST,
        "freshness_generation_id": "",
        "freshness_receipt_digest": "",
        "workspace_repo_head_sha": HEAD,
        "authority_repo_head_sha": HEAD,
        "authority_repo_root_digest": ROOT_DIGEST,
        "workspace_overlay_present": False,
        "semantic_evidence_authority": "committed_head_only",
        "no_authority_worktree_mutation_performed": True,
    }
    serialized, _, _ = canonical_semantic_evidence(result["raw_result"])
    result["semantic_evidence_json"] = serialized
    result["query_receipt"] = build_query_receipt(
        source="holoindex_owner_service",
        source_class="holoindex",
        query=QUERY,
        result=result,
        require_generation=True,
    )
    return result


def _coordinated(*, task_id: str = TASK_ID):
    return SimpleNamespace(
        accepted=True,
        status="QUEUED",
        task_id=task_id,
        target_repo_head_sha=HEAD,
        authority_root_digest=ROOT_DIGEST,
        rejection_reasons=(),
    )


def _run(tmp_path: Path, *, initial=None, independent=None, coordinated=None):
    calls = []

    def coordinator(**kwargs):
        calls.append(kwargs)
        return coordinated or _coordinated()

    result = coordinate_holoindex_incident_repair(
        repo_root=tmp_path,
        query=QUERY,
        owner_failure=initial or _preowner_failure(),
        select_authority=lambda _root: _selection(tmp_path),
        coordinator=coordinator,
        query_runner=lambda *_args, **_kwargs: independent or _preowner_failure(),
    )
    return result, calls


def test_preowner_repo_head_mismatch_enqueues_exact_postmerge_task(
    tmp_path: Path,
) -> None:
    result, calls = _run(tmp_path)
    assert result.accepted is True and result.status == "QUEUED"
    assert result.task_id == TASK_ID and result.target_repo_head_sha == HEAD
    assert calls[0]["incident_binding"]["incident_kind"] == "REPO_HEAD_MISMATCH"


def test_shared_owner_classification_rejects_unreceipted_preowner_result(
    tmp_path: Path,
) -> None:
    result = _preowner_failure()
    selection = _selection(tmp_path)
    status, returned = owner_verification.query_and_classify_owner_result(
        query=QUERY,
        selection=selection,
        workspace_repo_root=tmp_path,
        query_runner=lambda *_args, **_kwargs: result,
    )
    assert status == owner_verification.INVALID and returned is result
    assert owner_verification.classify_verified_owner_result(
        result, query=QUERY, selection=selection
    ) == owner_verification.INVALID
    assert owner_verification.is_verified_transient_owner_result(
        result, query=QUERY, selection=selection
    ) is False


@pytest.mark.parametrize(
    "independent",
    [
        _receipt_bound_failure(),
        _receipt_bound_failure("REPO_HEAD_MISMATCH"),
    ],
)
def test_preowner_recheck_rejects_receipt_bound_result(
    tmp_path: Path, independent: dict,
) -> None:
    result, calls = _run(tmp_path, independent=independent)
    assert result.rejection_reasons == (
        "holoindex_incident_independent_recheck_failed",
    )
    assert calls == []


@pytest.mark.parametrize(
    "changes",
    [
        {"repo_head_sha": "f" * 40},
        {"freshness_generation_id": "sha256:" + ("f" * 64)},
        {"freshness_receipt_digest": "sha256:" + ("f" * 64)},
        {"stale_reasons": ["stale_repo_head_sha", "different_reason"]},
    ],
)
def test_preowner_recheck_requires_same_stale_generation_binding(
    tmp_path: Path, changes: dict,
) -> None:
    result, calls = _run(tmp_path, independent=_preowner_failure(**changes))
    assert result.rejection_reasons == (
        "holoindex_incident_independent_recheck_failed",
    )
    assert calls == []


@pytest.mark.parametrize(
    "changes",
    [
        {"owner_attempts": 1},
        {"repo_head_sha": HEAD},
        {"stale_reasons": []},
        {"query_receipt": {"receipt_id": "attacker-selected"}},
        {"query_receipt": None},
    ],
)
def test_untrusted_preowner_failure_never_enqueues(
    tmp_path: Path, changes: dict,
) -> None:
    result, calls = _run(tmp_path, initial=_preowner_failure(**changes))
    assert result.accepted is False and result.status == "REJECTED"
    assert calls == []


def test_preowner_coordinator_wrong_exact_task_never_admits_receipt(
    tmp_path: Path,
) -> None:
    result, calls = _run(tmp_path, coordinated=_coordinated(task_id="attacker-task"))
    assert len(calls) == 1
    assert result.accepted is False and result.status == "ESCALATE"
    assert result.rejection_reasons == ("maintenance_authority_binding_mismatch",)
