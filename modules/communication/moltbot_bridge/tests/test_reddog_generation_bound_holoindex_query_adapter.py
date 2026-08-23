"""Tests for the resident generation-bound HoloIndex query adapter."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Event, Thread
import time

import pytest

from holo_index.query_receipt import build_query_receipt
import modules.communication.moltbot_bridge.src.reddog_generation_bound_holoindex_query_adapter as adapter_module
from modules.communication.moltbot_bridge.src.reddog_generation_bound_holoindex_query_adapter import (
    GenerationBoundHoloIndexQueryAdapter,
)


def _seal_owner_result(result):
    value = dict(result)
    value["query_receipt"] = build_query_receipt(
        source="holoindex_owner_service",
        source_class="holoindex",
        query=value["query"],
        result=value,
        require_generation=True,
    )
    return value


def _bound_owner_result(query: str, digest: str, head: str, raw_result=None):
    return _seal_owner_result({
        "ok": True,
        "source": "holoindex_owner_service",
        "query": query,
        "freshness": "CURRENT",
        "freshness_generation_id": digest,
        "freshness_receipt_digest": digest,
        "repo_head_sha": head,
        "repo_root_digest": digest,
        "workspace_repo_head_sha": head,
        "authority_repo_head_sha": head,
        "authority_repo_root_digest": digest,
        "workspace_overlay_present": False,
        "semantic_evidence_authority": "clean_workspace_head",
        "retrieval_mode": "semantic",
        "query_replica_descriptor_digest": digest,
        "query_replica_generation_id": digest,
        "query_replica_id": digest,
        "query_replica_path_identity_digest": digest,
        "raw_result": raw_result or {},
        "index_gap_detected": False,
        "stale_reasons": [],
        "no_authority_worktree_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_reindex": True,
    })


def test_adapter_reuses_governed_one_shot_and_scopes_hits(tmp_path: Path) -> None:
    calls = []
    digest = "sha256:" + "a" * 64
    head = "b" * 40

    def query_once(
        payload, *, repo_root, operation_timeout_seconds, process_timeout_seconds,
    ):
        calls.append((
            dict(payload), repo_root,
            operation_timeout_seconds, process_timeout_seconds,
        ))
        result = _bound_owner_result(payload["query"], digest, head, {
            "code_hits": [
                {"path": "modules/private.py", "score": 0.9, "text": "DENIED_RAW"},
                {"path": "modules/allowed.py", "score": 0.8},
            ]
        })
        result.update({
            "semantic_evidence_json": "DENIED_SEMANTIC_CONTENT",
            "private_service_token": "DENIED_TOKEN",
        })
        return result

    result = GenerationBoundHoloIndexQueryAdapter(
        tmp_path, query_once_runner=query_once,
    ).query(query="resident evidence", allowed_paths=("modules/allowed.py",), limit=8)

    assert calls[0][:2] == ({
        "query": "resident evidence",
        "limit": 8,
        "retrieval_mode": "semantic",
        "include_bundle": False,
    }, tmp_path)
    assert 0 < calls[0][2] <= 27
    assert calls[0][2] < calls[0][3] <= 30
    assert result["ok"] is True
    assert result["freshness"] == "CURRENT"
    assert result["freshness_generation_id"] == digest
    assert [hit["path"] for hit in result["hits"]] == ["modules/allowed.py"]
    assert result["no_holoindex_reindex_performed"] is True
    serialized = json.dumps(result, sort_keys=True)
    assert "DENIED" not in serialized
    assert "raw_result" not in result
    assert "semantic_evidence_json" not in result
    assert "query_receipt" not in result


def test_adapter_preserves_route_failure_without_service_fallback(tmp_path: Path) -> None:
    expected = {
        "ok": False,
        "source": "holoindex_owner_service",
        "query": "resident evidence",
        "freshness": "UNKNOWN",
        "raw_result": {},
        "error": "HOLOINDEX_QUERY_REPLICA_REQUIRED",
        "index_gap_detected": True,
        "stale_reasons": ["holoindex_owner_query_failed"],
        "no_holoindex_reindex_performed": True,
        "no_reindex": True,
        "owner_attempts": 1,
    }

    result = GenerationBoundHoloIndexQueryAdapter(
        tmp_path, query_once_runner=lambda *_args, **_kwargs: expected,
    ).query(query="resident evidence", allowed_paths=("modules/**",), limit=8)

    assert result["error"] == "HOLOINDEX_QUERY_REPLICA_REQUIRED"
    assert result["hits"] == []
    assert result["owner_attempts"] == 1
    assert result["no_holoindex_reindex_performed"] is True
    assert "raw_result" not in result


def test_adapter_fails_closed_when_one_shot_raises(tmp_path: Path) -> None:
    def failed_query(*_args, **_kwargs):
        raise RuntimeError("sensitive detail")

    result = GenerationBoundHoloIndexQueryAdapter(
        tmp_path, query_once_runner=failed_query,
    ).query(query="resident evidence", allowed_paths=("modules/**",), limit=8)

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_OWNER_QUERY_ONCE_FAILED"
    assert result["hits"] == []
    assert result["no_holoindex_reindex_performed"] is True
    assert "sensitive detail" not in str(result)


@pytest.mark.parametrize("timeout", [None, "invalid", True, 0, 61])
def test_adapter_fails_closed_for_invalid_operation_timeout(
    tmp_path: Path, timeout,
) -> None:
    result = GenerationBoundHoloIndexQueryAdapter(
        tmp_path, operation_timeout_seconds=timeout,
    ).query(query="resident evidence", allowed_paths=("modules/**",), limit=8)

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_OWNER_QUERY_TIMEOUT_INVALID"


def test_adapter_serializes_complete_one_shot_lifecycle(tmp_path: Path) -> None:
    first_entered = Event()
    release_first = Event()
    active = 0
    max_active = 0
    calls = 0
    digest = "sha256:" + "c" * 64
    head = "d" * 40

    def query_once(
        payload, *, repo_root, operation_timeout_seconds, process_timeout_seconds,
    ):
        nonlocal active, max_active, calls
        calls += 1
        active += 1
        max_active = max(max_active, active)
        if calls == 1:
            first_entered.set()
            assert release_first.wait(2)
        active -= 1
        return _bound_owner_result(payload["query"], digest, head)

    adapter = GenerationBoundHoloIndexQueryAdapter(tmp_path, query_once)
    results = []
    first = Thread(target=lambda: results.append(adapter.query(
        query="first", allowed_paths=("modules/**",), limit=8,
    )))
    second = Thread(target=lambda: results.append(adapter.query(
        query="second", allowed_paths=("modules/**",), limit=8,
    )))
    first.start()
    assert first_entered.wait(2)
    second.start()
    assert calls == 1
    release_first.set()
    first.join(2)
    second.join(2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert max_active == 1
    assert calls == 2
    assert len(results) == 2
    assert all(result["ok"] is True for result in results)


def test_adapter_passes_hostile_request_to_shared_validator(tmp_path: Path) -> None:
    calls = []

    def rejecting_query_once(
        payload, *, repo_root, operation_timeout_seconds, process_timeout_seconds,
    ):
        calls.append(dict(payload))
        return {
            "ok": False,
            "source": "holoindex_owner_service",
            "query": "",
            "freshness": "UNKNOWN",
            "raw_result": {},
            "error": "limit_invalid",
            "index_gap_detected": True,
            "stale_reasons": ["holoindex_owner_query_failed"],
            "no_holoindex_reindex_performed": True,
            "no_reindex": True,
            "owner_attempts": 0,
        }

    result = GenerationBoundHoloIndexQueryAdapter(
        tmp_path, rejecting_query_once,
    ).query(query="evidence", allowed_paths=("modules/**",), limit=True)

    assert calls[0]["limit"] is True
    assert result["ok"] is False
    assert result["error"] == "limit_invalid"


def test_adapter_bounds_owner_lock_wait(tmp_path: Path) -> None:
    entered = Event()
    release = Event()
    digest = "sha256:" + "a" * 64

    def blocking_query(payload, **_kwargs):
        entered.set()
        assert release.wait(2)
        return _bound_owner_result(payload["query"], digest, "b" * 40)

    first_adapter = GenerationBoundHoloIndexQueryAdapter(
        tmp_path, blocking_query, operation_timeout_seconds=5,
    )
    first = Thread(target=lambda: first_adapter.query(
        query="first", allowed_paths=("modules/**",), limit=8,
    ))
    first.start()
    assert entered.wait(2)

    started = time.monotonic()
    result = GenerationBoundHoloIndexQueryAdapter(
        tmp_path, blocking_query, operation_timeout_seconds=0.05,
    ).query(query="second", allowed_paths=("modules/**",), limit=8)
    elapsed = time.monotonic() - started
    release.set()
    first.join(2)

    assert result["error"] == "HOLOINDEX_OWNER_QUERY_BUSY_TIMEOUT"
    assert elapsed < 1.0
    assert not first.is_alive()


def test_production_process_boundary_enforces_hard_timeout(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "reddog_holoindex_owner_query_once.py").write_text(
        "import time\ntime.sleep(1)\n", encoding="utf-8",
    )

    started = time.monotonic()
    result = adapter_module._run_owner_query_once(
        {"query": "evidence"}, repo_root=tmp_path,
        operation_timeout_seconds=0.02,
        process_timeout_seconds=0.05,
    )
    elapsed = time.monotonic() - started

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_OWNER_QUERY_PROCESS_TIMEOUT"
    assert elapsed < 0.5


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("authority_repo_root_digest", "sha256:" + "e" * 64),
        ("workspace_repo_head_sha", "f" * 40),
        ("query_replica_generation_id", "sha256:" + "e" * 64),
        ("query_replica_id", ""),
        ("index_gap_detected", True),
        ("stale_reasons", ["STALE_INDEX"]),
        ("no_authority_worktree_mutation_performed", False),
        ("retrieval_mode", "lexical"),
        ("semantic_evidence_authority", "committed_head_only"),
    ],
)
def test_adapter_rejects_split_or_incomplete_owner_binding(
    tmp_path: Path, field: str, value,
) -> None:
    digest = "sha256:" + "a" * 64
    result = _bound_owner_result("evidence", digest, "b" * 40)
    result[field] = value
    result = _seal_owner_result(result)

    observed = GenerationBoundHoloIndexQueryAdapter(
        tmp_path, lambda *_args, **_kwargs: result,
    ).query(query="evidence", allowed_paths=("modules/**",), limit=8)

    assert observed["ok"] is False
    assert observed["error"] == "HOLOINDEX_OWNER_QUERY_RESPONSE_INVALID"
