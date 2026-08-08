"""Security tests for generic HoloIndex incident repair coordination."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from holo_index.authority_worktree import HoloIndexAuthoritySelection
from holo_index.query_receipt import build_query_receipt, canonical_semantic_evidence
from modules.communication.moltbot_bridge.src.reddog_holoindex_incident_repair_runtime import (
    coordinate_holoindex_incident_repair,
)


HEAD = "a" * 40
DIGEST = "sha256:" + ("b" * 64)
GENERATION = "sha256:" + ("c" * 64)
FRESHNESS = "sha256:" + ("d" * 64)
TASK_ID = "holoindex_postmerge_refresh:" + HEAD
STALE_HEAD = "e" * 40


def _selection(root: Path) -> HoloIndexAuthoritySelection:
    return HoloIndexAuthoritySelection(
        True, root, HEAD, HEAD, DIGEST, True, "authority_worktree"
    )


def _stale_selection(root: Path) -> HoloIndexAuthoritySelection:
    return HoloIndexAuthoritySelection(
        False,
        root,
        HEAD,
        STALE_HEAD,
        DIGEST,
        True,
        "authority_worktree",
        ("HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH",),
    )


def _failure(**changes):
    value = {
        "ok": False,
        "error": "SEMANTIC_BACKEND_UNAVAILABLE",
        "index_gap_detected": True,
        "no_holoindex_reindex_performed": True,
        "owner_attempts": 2,
        "workspace_repo_head_sha": HEAD,
        "authority_repo_head_sha": HEAD,
        "authority_repo_root_digest": DIGEST,
        "no_authority_worktree_mutation_performed": True,
    }
    value.update(changes)
    return value


def _stale_failure(**changes):
    value = _failure()
    value.update(
        error="HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH",
        owner_attempts=0,
        authority_repo_head_sha=STALE_HEAD,
    )
    value.update(changes)
    return value


def _verified_owner_result(*, current: bool = False, **changes):
    result = {
        "ok": current,
        "source": "holoindex_owner_service",
        "query": "repair HoloIndex owner",
        "freshness": "CURRENT" if current else "UNKNOWN",
        "error": "" if current else "SEMANTIC_BACKEND_UNAVAILABLE",
        "index_gap_detected": not current,
        "raw_result": {},
        "no_holoindex_reindex_performed": True,
        "owner_attempts": 1 if current else 2,
        "repo_head_sha": HEAD,
        "repo_root_digest": DIGEST,
        "freshness_generation_id": GENERATION if current else "",
        "freshness_receipt_digest": FRESHNESS if current else "",
        "workspace_repo_head_sha": HEAD,
        "authority_repo_head_sha": HEAD,
        "authority_repo_root_digest": DIGEST,
        "workspace_overlay_present": False,
        "semantic_evidence_authority": "committed_head_only",
        "no_authority_worktree_mutation_performed": True,
    }
    result.update(changes)
    serialized, _, _ = canonical_semantic_evidence(result["raw_result"])
    result["semantic_evidence_json"] = serialized
    receipt = build_query_receipt(
        source="holoindex_owner_service",
        source_class="holoindex",
        query=result["query"],
        result=result,
        require_generation=True,
    )
    result["query_receipt"] = receipt
    return result


def _coordinate(
    status="QUEUED", accepted=True, reasons=(), target_head=HEAD, authority_digest=DIGEST
):
    return SimpleNamespace(
        accepted=accepted,
        status=status,
        task_id=TASK_ID,
        target_repo_head_sha=target_head,
        authority_root_digest=authority_digest,
        rejection_reasons=reasons,
    )


def _run(tmp_path: Path, **changes):
    called = []
    coordinated = changes.pop("coordinated", _coordinate())

    def coordinator(**kwargs):
        called.append(kwargs)
        return coordinated

    query_runner = changes.pop(
        "query_runner", lambda *_args, **_kwargs: _verified_owner_result()
    )
    result = coordinate_holoindex_incident_repair(
        repo_root=tmp_path,
        query=changes.pop("query", "repair HoloIndex owner"),
        owner_failure=changes.pop("owner_failure", _failure()),
        db=object(),
        environment={"SAFE": "1"},
        select_authority=lambda _root: _selection(tmp_path),
        coordinator=coordinator,
        query_runner=query_runner,
        **changes,
    )
    return result, called


def test_valid_incident_enqueues_existing_postmerge_task(tmp_path: Path) -> None:
    result, called = _run(tmp_path)
    assert result.accepted is True
    assert result.status == "QUEUED"
    assert result.task_id == TASK_ID
    assert result.maintenance_enqueued is True
    assert result.coding_candidate_required is False
    assert result.receipt_id.startswith("sha256:")
    assert len(called) == 1
    assert called[0]["repo_root"] == tmp_path.resolve()


def test_stale_authority_enqueues_existing_postmerge_task(
    tmp_path: Path,
) -> None:
    called = []

    def coordinator(**kwargs):
        called.append(kwargs)
        return _coordinate()

    result = coordinate_holoindex_incident_repair(
        repo_root=tmp_path,
        query="repair HoloIndex authority",
        owner_failure=_stale_failure(),
        db=object(),
        environment={"SAFE": "1"},
        select_authority=lambda _root: _stale_selection(tmp_path),
        coordinator=coordinator,
        query_runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("stale authority must route to postmerge first")
        ),
    )

    assert result.accepted is True
    assert result.status == "QUEUED"
    assert result.target_repo_head_sha == HEAD
    assert result.authority_root_digest == DIGEST
    assert result.maintenance_enqueued is True
    assert len(called) == 1


@pytest.mark.parametrize(
    "failure",
    [
        _stale_failure(owner_attempts=False),
        _stale_failure(owner_attempts="0"),
        _stale_failure(owner_attempts=1),
        _stale_failure(authority_repo_head_sha="f" * 40),
        _stale_failure(authority_repo_root_digest="sha256:" + "f" * 64),
        _stale_failure(authority_repo_head_sha=HEAD),
    ],
)
def test_forged_stale_authority_failure_never_coordinates(
    tmp_path: Path, failure: dict
) -> None:
    called = []
    result = coordinate_holoindex_incident_repair(
        repo_root=tmp_path,
        query="repair HoloIndex authority",
        owner_failure=failure,
        select_authority=lambda _root: _stale_selection(tmp_path),
        coordinator=lambda **kwargs: called.append(kwargs),
        query_runner=lambda *_args, **_kwargs: _verified_owner_result(),
    )

    assert result.accepted is False
    assert called == []


def test_stale_authority_current_requires_fresh_selection_and_owner_receipt(
    tmp_path: Path,
) -> None:
    selections = iter((_stale_selection(tmp_path), _selection(tmp_path)))
    result = coordinate_holoindex_incident_repair(
        repo_root=tmp_path,
        query="repair HoloIndex owner",
        owner_failure=_stale_failure(),
        select_authority=lambda _root: next(selections),
        coordinator=lambda **_kwargs: _coordinate("CURRENT"),
        query_runner=lambda *_args, **_kwargs: _verified_owner_result(current=True),
    )

    assert result.accepted is True
    assert result.status == "OWNER_READY"
    assert result.target_repo_head_sha == HEAD
    assert result.owner_requery_performed is True


def test_stale_authority_current_rejects_still_stale_selection(
    tmp_path: Path,
) -> None:
    result = coordinate_holoindex_incident_repair(
        repo_root=tmp_path,
        query="repair HoloIndex owner",
        owner_failure=_stale_failure(),
        select_authority=lambda _root: _stale_selection(tmp_path),
        coordinator=lambda **_kwargs: _coordinate("CURRENT"),
        query_runner=lambda *_args, **_kwargs: _verified_owner_result(current=True),
    )

    assert result.accepted is False
    assert result.status == "ESCALATE"
    assert result.rejection_reasons == (
        "holoindex_authority_still_stale_after_current_proof",
    )


@pytest.mark.parametrize("status", ["ASSIGNED", "EXECUTING"])
def test_active_maintenance_task_defers_without_coding_candidate(
    tmp_path: Path, status: str
) -> None:
    result, called = _run(tmp_path, coordinated=_coordinate(status))
    assert len(called) == 1
    assert result.accepted is True
    assert result.status == status
    assert result.maintenance_enqueued is True
    assert result.coding_candidate_required is False


@pytest.mark.parametrize(
    "failure",
    [
        _failure(ok=True),
        _failure(error="attacker_selected"),
        _failure(index_gap_detected=False),
        _failure(no_holoindex_reindex_performed=False),
        _failure(owner_attempts=1),
        _failure(owner_attempts="2"),
        _failure(owner_attempts="not-a-number"),
        _failure(no_authority_worktree_mutation_performed=False),
        _failure(authority_repo_root_digest="sha256:forged"),
        _failure(authority_repo_head_sha="f" * 40),
    ],
)
def test_untrusted_or_unexhausted_failure_never_enqueues(
    tmp_path: Path, failure
) -> None:
    result, called = _run(tmp_path, owner_failure=failure)
    assert result.accepted is False
    assert result.status == "REJECTED"
    assert called == []


@pytest.mark.parametrize(
    "coordinated",
    [
        _coordinate(target_head="f" * 40),
        _coordinate(authority_digest="sha256:wrong-root"),
    ],
)
def test_coordinator_authority_binding_mismatch_escalates(
    tmp_path: Path, coordinated
) -> None:
    result, called = _run(tmp_path, coordinated=coordinated)
    assert len(called) == 1
    assert result.accepted is False
    assert result.status == "ESCALATE"
    assert result.coding_candidate_required is True
    assert result.rejection_reasons == ("maintenance_authority_binding_mismatch",)


def test_current_generation_requires_successful_owner_requery(tmp_path: Path) -> None:
    query_calls = []

    def query_runner(payload, *, repo_root):
        query_calls.append((payload, repo_root))
        return _verified_owner_result(current=True)

    result, _ = _run(
        tmp_path, coordinated=_coordinate("CURRENT"), query_runner=query_runner
    )
    assert result.accepted is True
    assert result.status == "OWNER_READY"
    assert result.generation_id == GENERATION
    assert result.freshness_receipt_digest == FRESHNESS
    assert result.owner_requery_performed is True
    assert query_calls == [
        ({"query": "repair HoloIndex owner", "limit": 5}, tmp_path)
    ]


def test_current_generation_with_broken_owner_escalates(tmp_path: Path) -> None:
    result, _ = _run(
        tmp_path,
        coordinated=_coordinate("CURRENT"),
        query_runner=lambda *_args, **_kwargs: _verified_owner_result(),
    )
    assert result.accepted is False
    assert result.status == "ESCALATE"
    assert result.coding_candidate_required is True
    assert result.maintenance_enqueued is False


@pytest.mark.parametrize(
    "changes",
    [
        {"freshness_generation_id": [GENERATION]},
        {"freshness_receipt_digest": "not-a-digest"},
    ],
)
def test_current_generation_requires_primitive_digest_identifiers(
    tmp_path: Path, changes: dict
) -> None:
    result, called = _run(
        tmp_path,
        query_runner=lambda *_args, **_kwargs: _verified_owner_result(
            current=True, **changes
        ),
    )
    assert result.accepted is False
    assert called == []


@pytest.mark.parametrize(
    "query_runner",
    [
        lambda *_args, **_kwargs: _failure(),
        lambda *_args, **_kwargs: _verified_owner_result(
            repo_root_digest="sha256:wrong-root"
        ),
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    ],
)
def test_independent_owner_recheck_failure_never_coordinates(
    tmp_path: Path, query_runner
) -> None:
    result, called = _run(tmp_path, query_runner=query_runner)
    assert result.accepted is False
    assert result.rejection_reasons == (
        "holoindex_incident_independent_recheck_failed",
    )
    assert called == []


def test_tampered_independent_owner_receipt_never_coordinates(tmp_path: Path) -> None:
    owner_result = _verified_owner_result()
    owner_result["query_receipt"]["error"] = "attacker-selected"
    result, called = _run(
        tmp_path, query_runner=lambda *_args, **_kwargs: owner_result
    )
    assert result.accepted is False
    assert called == []


def test_cyclic_independent_owner_receipt_never_coordinates(tmp_path: Path) -> None:
    owner_result = _verified_owner_result()
    owner_result["query_receipt"]["cycle"] = owner_result["query_receipt"]
    result, called = _run(
        tmp_path, query_runner=lambda *_args, **_kwargs: owner_result
    )
    assert result.accepted is False
    assert called == []


def test_retry_exhaustion_emits_candidate_without_model_binding(tmp_path: Path) -> None:
    result, _ = _run(
        tmp_path,
        coordinated=_coordinate(
            "RETRY_EXHAUSTED", False, ("maintenance_retry_exhausted",)
        ),
    )
    assert result.status == "ESCALATE"
    assert result.coding_candidate_required is True
    assert result.rejection_reasons == ("maintenance_retry_exhausted",)


def test_query_is_bounded_before_any_coordination(tmp_path: Path) -> None:
    result, called = _run(tmp_path, query="x" * 16_001)
    assert result.rejection_reasons == ("holoindex_incident_query_invalid",)
    assert called == []


def test_non_string_query_is_rejected_before_coordination(tmp_path: Path) -> None:
    result, called = _run(tmp_path, query={"query": "repair HoloIndex owner"})
    assert result.rejection_reasons == ("holoindex_incident_query_invalid",)
    assert called == []


def test_non_string_coordinator_fields_are_rejected(tmp_path: Path) -> None:
    coordinated = _coordinate()
    coordinated.status = ["QUEUED"]
    result, called = _run(tmp_path, coordinated=coordinated)
    assert len(called) == 1
    assert result.rejection_reasons == (
        "holoindex_incident_coordinator_result_invalid",
    )


def test_runtime_contains_no_direct_shell_model_or_index_call() -> None:
    source_path = Path(__file__).parents[1] / "src" / (
        "reddog_holoindex_incident_repair_runtime.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = {
        node.names[0].name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom)) and node.names
    }
    source = source_path.read_text(encoding="utf-8").lower()
    assert "subprocess" not in imports
    assert "qwen" not in source
    assert "--index" not in source
    assert "execute_holoindex_postmerge_task" not in source
