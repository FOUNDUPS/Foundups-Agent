"""Tests for the extension's one-shot generation-bound HoloIndex bridge."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scripts.reddog_holoindex_owner_query_once import (
    MAX_QUERY_CHARS,
    query_once,
)


def _success() -> dict:
    return {
        "ok": True,
        "source": "holoindex_owner_service",
        "query": "audit pfmall",
        "freshness": "CURRENT",
        "raw_result": {"code_hits": [{"path": "modules/foundups/pfmall/api.py"}]},
        "error": "",
        "index_gap_detected": False,
        "stale_reasons": [],
        "freshness_generation_id": "sha256:" + "a" * 64,
        "freshness_receipt_digest": "sha256:" + "b" * 64,
        "repo_head_sha": "c" * 40,
        "retrieval_mode": "semantic",
        "no_holoindex_reindex_performed": True,
    }


def test_started_owner_uses_private_handoff_and_cleans_up(tmp_path: Path) -> None:
    calls: dict = {}

    def query_owner(**kwargs):
        calls.update(kwargs)
        return _success()

    def cleanup_owner():
        calls["cleaned"] = True

    result = query_once(
        {"query": "audit pfmall", "limit": 5},
        repo_root=tmp_path,
        ensure_owner=lambda **_kwargs: SimpleNamespace(
            ready=True, status="STARTED", error=""
        ),
        resolve_handoff=lambda: ("http://127.0.0.1:8127/holoindex/v1/query", "x" * 48),
        query_owner=query_owner,
        cleanup_owner=cleanup_owner,
    )

    assert result["ok"] is True
    assert result["query_receipt"]["schema_version"] == "holoindex_query_receipt.v1"
    assert result["query_receipt"]["freshness_generation_id"] == "sha256:" + "a" * 64
    assert result["query_receipt"]["index_gap_detected"] is False
    assert calls["repo_root"] == tmp_path
    assert calls["service_url"].startswith("http://127.0.0.1:")
    assert calls["service_token"] == "x" * 48
    assert calls["timeout_seconds"] == 60.0
    assert calls["cleaned"] is True


def test_configured_owner_uses_environment_contract_without_cleanup(tmp_path: Path) -> None:
    calls: dict = {}

    def query_owner(**kwargs):
        calls.update(kwargs)
        return _success()

    result = query_once(
        {"query": "audit pfmall"},
        repo_root=tmp_path,
        ensure_owner=lambda **_kwargs: SimpleNamespace(
            ready=True, status="CONFIGURED", error=""
        ),
        resolve_handoff=lambda: (_ for _ in ()).throw(
            AssertionError("configured owner must use environment")
        ),
        query_owner=query_owner,
        cleanup_owner=lambda: (_ for _ in ()).throw(
            AssertionError("configured owner is not process-owned")
        ),
    )

    assert result["ok"] is True
    assert calls["service_url"] is None
    assert calls["service_token"] is None


def test_bootstrap_failure_fails_closed_before_query(tmp_path: Path) -> None:
    result = query_once(
        {"query": "audit pfmall"},
        repo_root=tmp_path,
        ensure_owner=lambda **_kwargs: SimpleNamespace(
            ready=False, status="FAILED", error="STALE_INDEX"
        ),
        query_owner=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("query must not run after bootstrap failure")
        ),
    )

    assert result["ok"] is False
    assert result["error"] == "STALE_INDEX"
    assert result["index_gap_detected"] is True
    assert result["no_holoindex_reindex_performed"] is True


def test_missing_started_handoff_fails_closed_and_cleans_up(tmp_path: Path) -> None:
    calls: list[str] = []
    result = query_once(
        {"query": "audit pfmall"},
        repo_root=tmp_path,
        ensure_owner=lambda **_kwargs: SimpleNamespace(
            ready=True, status="STARTED", error=""
        ),
        resolve_handoff=lambda: None,
        query_owner=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("query must not run without handoff")
        ),
        cleanup_owner=lambda: calls.append("cleaned"),
    )

    assert result["ok"] is False
    assert result["error"] == "owner_handoff_missing"
    assert calls == ["cleaned"]


def test_request_validation_is_bounded_and_has_no_side_effects(tmp_path: Path) -> None:
    def unexpected(**_kwargs):
        raise AssertionError("invalid request must fail before owner bootstrap")

    cases = (
        ({}, "query_required"),
        ({"query": " "}, "query_required"),
        ({"query": "x" * (MAX_QUERY_CHARS + 1)}, "query_too_large"),
        ({"query": "audit", "limit": 0}, "limit_invalid"),
        ({"query": "audit", "limit": 21}, "limit_invalid"),
        ({"query": "audit", "limit": True}, "limit_invalid"),
    )
    for payload, expected in cases:
        result = query_once(payload, repo_root=tmp_path, ensure_owner=unexpected)
        assert result["ok"] is False
        assert result["error"] == expected


def test_query_exception_is_secret_free_and_cleanup_runs(tmp_path: Path) -> None:
    cleaned: list[bool] = []

    class SecretFailure(RuntimeError):
        pass

    result = query_once(
        {"query": "audit"},
        repo_root=tmp_path,
        ensure_owner=lambda **_kwargs: SimpleNamespace(
            ready=True, status="STARTED", error=""
        ),
        resolve_handoff=lambda: ("http://127.0.0.1:8127", "secret-token-value"),
        query_owner=lambda **_kwargs: (_ for _ in ()).throw(
            SecretFailure("secret-token-value")
        ),
        cleanup_owner=lambda: cleaned.append(True),
    )

    assert result["ok"] is False
    assert result["error"] == "SecretFailure"
    assert "secret-token-value" not in str(result)
    assert cleaned == [True]
