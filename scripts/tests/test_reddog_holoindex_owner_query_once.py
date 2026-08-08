"""Tests for the extension's one-shot generation-bound HoloIndex bridge."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from holo_index.authority_worktree import HoloIndexAuthoritySelection
from holo_index.repository_state import repository_root_digest
from scripts.reddog_holoindex_owner_query_once import (
    MAX_QUERY_CHARS,
    query_once,
)


def _selection(root: Path) -> HoloIndexAuthoritySelection:
    return HoloIndexAuthoritySelection(
        accepted=True,
        selected_root=root,
        workspace_head_sha="c" * 40,
        authority_head_sha="c" * 40,
        authority_root_digest=repository_root_digest(root),
        workspace_overlay_present=False,
        source="workspace",
    )


def _success(root: Path) -> dict:
    return {
        "ok": True,
        "source": "holoindex_owner_service",
        "query": "audit pfmall",
        "freshness": "CURRENT",
        "hits": [{"path": "modules/foundups/pfmall/api.py", "score": 0.9}],
        "raw_result": {"code_hits": [{"path": "modules/foundups/pfmall/api.py"}]},
        "error": "",
        "index_gap_detected": False,
        "stale_reasons": [],
        "freshness_generation_id": "sha256:" + "a" * 64,
        "freshness_receipt_digest": "sha256:" + "b" * 64,
        "repo_head_sha": "c" * 40,
        "repo_root_digest": repository_root_digest(root),
        "retrieval_mode": "semantic",
        "no_holoindex_reindex_performed": True,
    }


def test_started_owner_uses_private_handoff_and_cleans_up(tmp_path: Path) -> None:
    calls: dict = {}

    def query_owner(**kwargs):
        calls.update(kwargs)
        return _success(tmp_path)

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
        select_authority=_selection,
    )

    assert result["ok"] is True
    assert result["query_receipt"]["schema_version"] == "holoindex_query_receipt.v1"
    assert result["query_receipt"]["freshness_generation_id"] == "sha256:" + "a" * 64
    assert result["query_receipt"]["index_gap_detected"] is False
    assert result["query_receipt"]["authority_repo_root_digest"] == repository_root_digest(
        tmp_path
    )
    assert result["query_receipt"]["no_authority_worktree_mutation_performed"] is True
    assert result["query_receipt"]["semantic_evidence_count"] == 1
    assert result["query_receipt"]["semantic_evidence_digest"].startswith("sha256:")
    assert result["query_receipt"]["hits"][0]["path"] == "modules/foundups/pfmall/api.py"
    assert result["query_receipt"]["hits"][0]["score"] == "0.9"
    assert "modules/foundups/pfmall/api.py" in result["semantic_evidence_json"]
    assert calls["repo_root"] == tmp_path
    assert calls["service_url"].startswith("http://127.0.0.1:")
    assert calls["service_token"] == "x" * 48
    assert calls["timeout_seconds"] == 60.0
    assert calls["cleaned"] is True


def test_configured_owner_uses_environment_contract_without_cleanup(tmp_path: Path) -> None:
    calls: dict = {}

    def query_owner(**kwargs):
        calls.update(kwargs)
        return _success(tmp_path)

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
        select_authority=_selection,
    )

    assert result["ok"] is True
    assert calls["service_url"] is None
    assert calls["service_token"] is None


def test_query_runs_against_selected_authority_root(tmp_path: Path) -> None:
    authority = tmp_path / "authority"
    authority.mkdir()
    selection = HoloIndexAuthoritySelection(
        accepted=True,
        selected_root=authority,
        workspace_head_sha="c" * 40,
        authority_head_sha="c" * 40,
        authority_root_digest=repository_root_digest(authority),
        workspace_overlay_present=True,
        source="configured",
    )
    calls: dict = {}
    bootstrap_calls: dict = {}

    def query_owner(**kwargs):
        calls.update(kwargs)
        return _success(authority)

    def ensure_owner(**kwargs):
        bootstrap_calls.update(kwargs)
        return SimpleNamespace(
            ready=kwargs["repo_root"] == authority,
            status="CONFIGURED",
            error="",
        )

    result = query_once(
        {"query": "audit pfmall"},
        repo_root=tmp_path,
        ensure_owner=ensure_owner,
        query_owner=query_owner,
        select_authority=lambda _root: selection,
    )

    assert result["ok"] is True
    assert bootstrap_calls["repo_root"] == authority
    assert bootstrap_calls["runtime_root"] == tmp_path
    assert calls["repo_root"] == authority
    assert result["workspace_overlay_present"] is True
    assert result["semantic_evidence_authority"] == "committed_head_only"


def test_linked_workspace_uses_resolved_primary_runtime_root(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    authority = tmp_path / "authority"
    primary = tmp_path / "primary"
    for path in (workspace, authority, primary):
        path.mkdir()
    selection = HoloIndexAuthoritySelection(
        accepted=True,
        selected_root=authority,
        workspace_head_sha="c" * 40,
        authority_head_sha="c" * 40,
        authority_root_digest=repository_root_digest(authority),
        workspace_overlay_present=False,
        source="configured",
    )
    bootstrap_calls: dict = {}

    def ensure_owner(**kwargs):
        bootstrap_calls.update(kwargs)
        return SimpleNamespace(ready=True, status="CONFIGURED", error="")

    result = query_once(
        {"query": "audit pfmall"},
        repo_root=workspace,
        ensure_owner=ensure_owner,
        query_owner=lambda **_kwargs: _success(authority),
        select_authority=lambda _root: selection,
        select_runtime_root=lambda _root: primary,
    )

    assert result["ok"] is True
    assert bootstrap_calls["repo_root"] == authority
    assert bootstrap_calls["runtime_root"] == primary


def test_clean_workspace_is_its_own_trusted_runtime_root(tmp_path: Path) -> None:
    bootstrap_calls: dict = {}

    def ensure_owner(**kwargs):
        bootstrap_calls.update(kwargs)
        return SimpleNamespace(ready=True, status="CONFIGURED", error="")

    result = query_once(
        {"query": "audit pfmall"},
        repo_root=tmp_path,
        ensure_owner=ensure_owner,
        query_owner=lambda **_kwargs: _success(tmp_path),
        select_authority=_selection,
    )

    assert result["ok"] is True
    assert bootstrap_calls["repo_root"] == tmp_path
    assert bootstrap_calls["runtime_root"] == tmp_path


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
        select_authority=_selection,
    )

    assert result["ok"] is False
    assert result["error"] == "STALE_INDEX"
    assert result["owner_attempts"] == 1
    assert result["owner_retry_performed"] is False
    assert result["index_gap_detected"] is True
    assert result["no_holoindex_reindex_performed"] is True


def test_transient_bootstrap_exit_retries_once_then_succeeds(
    tmp_path: Path,
) -> None:
    bootstraps = iter(
        (
            SimpleNamespace(
                ready=False,
                status="FAILED",
                error="HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP",
            ),
            SimpleNamespace(ready=True, status="STARTED", error=""),
        )
    )
    cleanup_calls: list[str] = []

    result = query_once(
        {"query": "audit pfmall"},
        repo_root=tmp_path,
        ensure_owner=lambda **_kwargs: next(bootstraps),
        resolve_handoff=lambda: (
            "http://127.0.0.1:8127/holoindex/v1/query",
            "x" * 48,
        ),
        query_owner=lambda **_kwargs: _success(tmp_path),
        cleanup_owner=lambda: cleanup_calls.append("cleaned"),
        select_authority=_selection,
    )

    assert result["ok"] is True
    assert result["owner_attempts"] == 2
    assert result["owner_retry_performed"] is True
    assert (
        result["owner_retry_reason"]
        == "HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP"
    )
    assert result["no_holoindex_reindex_performed"] is True
    assert cleanup_calls == ["cleaned", "cleaned"]


def test_transient_bootstrap_exhaustion_returns_bound_receipt(
    tmp_path: Path,
) -> None:
    result = query_once(
        {"query": "audit pfmall"},
        repo_root=tmp_path,
        ensure_owner=lambda **_kwargs: SimpleNamespace(
            ready=False,
            status="FAILED",
            error="HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP",
        ),
        cleanup_owner=lambda: None,
        select_authority=_selection,
    )

    assert result["ok"] is False
    assert result["owner_attempts"] == 2
    assert result["workspace_repo_head_sha"] == "c" * 40
    assert result["authority_repo_head_sha"] == "c" * 40
    assert result["query_receipt"]["receipt_id"].startswith("sha256:")
    assert result["query_receipt"]["query"] == "audit pfmall"
    assert result["no_authority_worktree_mutation_performed"] is True


def test_process_owned_semantic_failure_retries_once_then_succeeds(
    tmp_path: Path,
) -> None:
    results = iter(
        (
            {
                "ok": False,
                "error": "SEMANTIC_BACKEND_UNAVAILABLE",
                "raw_result": {},
                "no_holoindex_reindex_performed": True,
            },
            _success(tmp_path),
        )
    )
    cleanup_calls: list[str] = []

    result = query_once(
        {"query": "audit pfmall"},
        repo_root=tmp_path,
        ensure_owner=lambda **_kwargs: SimpleNamespace(
            ready=True, status="STARTED", error=""
        ),
        resolve_handoff=lambda: (
            "http://127.0.0.1:8127/holoindex/v1/query",
            "x" * 48,
        ),
        query_owner=lambda **_kwargs: next(results),
        cleanup_owner=lambda: cleanup_calls.append("cleaned"),
        select_authority=_selection,
    )

    assert result["ok"] is True
    assert result["owner_attempts"] == 2
    assert result["owner_retry_performed"] is True
    assert result["owner_retry_reason"] == "SEMANTIC_BACKEND_UNAVAILABLE"
    assert cleanup_calls == ["cleaned", "cleaned"]


def test_poisoned_process_owned_query_retries_once_then_succeeds(
    tmp_path: Path,
) -> None:
    results = iter(
        (
            {
                "ok": False,
                "error": "QUERY_OWNER_POISONED",
                "raw_result": {},
                "no_holoindex_reindex_performed": True,
            },
            _success(tmp_path),
        )
    )

    result = query_once(
        {"query": "audit pfmall"},
        repo_root=tmp_path,
        ensure_owner=lambda **_kwargs: SimpleNamespace(
            ready=True, status="STARTED", error=""
        ),
        resolve_handoff=lambda: (
            "http://127.0.0.1:8127/holoindex/v1/query",
            "x" * 48,
        ),
        query_owner=lambda **_kwargs: next(results),
        cleanup_owner=lambda: None,
        select_authority=_selection,
    )

    assert result["ok"] is True
    assert result["owner_attempts"] == 2
    assert result["owner_retry_reason"] == "QUERY_OWNER_POISONED"


def test_reused_process_owned_query_is_cleaned_before_retry(
    tmp_path: Path,
) -> None:
    statuses = iter(("REUSED", "STARTED"))
    results = iter(
        (
            {
                "ok": False,
                "error": "SEMANTIC_BACKEND_UNAVAILABLE",
                "raw_result": {},
                "no_holoindex_reindex_performed": True,
            },
            _success(tmp_path),
        )
    )
    cleanup_calls: list[str] = []

    result = query_once(
        {"query": "audit pfmall"},
        repo_root=tmp_path,
        ensure_owner=lambda **_kwargs: SimpleNamespace(
            ready=True, status=next(statuses), error=""
        ),
        resolve_handoff=lambda: (
            "http://127.0.0.1:8127/holoindex/v1/query",
            "x" * 48,
        ),
        query_owner=lambda **_kwargs: next(results),
        cleanup_owner=lambda: cleanup_calls.append("cleaned"),
        select_authority=_selection,
    )

    assert result["ok"] is True
    assert result["owner_attempts"] == 2
    assert cleanup_calls == ["cleaned", "cleaned"]


def test_two_transient_query_failures_stop_at_retry_ceiling(
    tmp_path: Path,
) -> None:
    query_calls: list[str] = []
    cleanup_calls: list[str] = []

    def unavailable(**_kwargs):
        query_calls.append("query")
        return {
            "ok": False,
            "source": "holoindex_owner_service",
            "query": "audit pfmall",
            "freshness": "STALE",
            "raw_result": {},
            "error": "SEMANTIC_BACKEND_UNAVAILABLE",
            "index_gap_detected": True,
            "stale_reasons": ["semantic_backend_unavailable"],
            "no_holoindex_reindex_performed": True,
        }

    result = query_once(
        {"query": "audit pfmall"},
        repo_root=tmp_path,
        ensure_owner=lambda **_kwargs: SimpleNamespace(
            ready=True, status="STARTED", error=""
        ),
        resolve_handoff=lambda: (
            "http://127.0.0.1:8127/holoindex/v1/query",
            "x" * 48,
        ),
        query_owner=unavailable,
        cleanup_owner=lambda: cleanup_calls.append("cleaned"),
        select_authority=_selection,
    )

    assert result["ok"] is False
    assert result["error"] == "SEMANTIC_BACKEND_UNAVAILABLE"
    assert result["owner_attempts"] == 2
    assert result["owner_retry_performed"] is True
    assert len(query_calls) == 2
    assert cleanup_calls == ["cleaned", "cleaned"]


def test_configured_owner_semantic_failure_is_not_restarted(
    tmp_path: Path,
) -> None:
    query_calls: list[str] = []

    result = query_once(
        {"query": "audit pfmall"},
        repo_root=tmp_path,
        ensure_owner=lambda **_kwargs: SimpleNamespace(
            ready=True, status="CONFIGURED", error=""
        ),
        query_owner=lambda **_kwargs: (
            query_calls.append("query")
            or {
                "ok": False,
                "source": "holoindex_owner_service",
                "query": "audit pfmall",
                "freshness": "STALE",
                "raw_result": {},
                "error": "SEMANTIC_BACKEND_UNAVAILABLE",
                "index_gap_detected": True,
                "stale_reasons": ["semantic_backend_unavailable"],
                "no_holoindex_reindex_performed": True,
            }
        ),
        cleanup_owner=lambda: (_ for _ in ()).throw(
            AssertionError("configured owner must not be stopped")
        ),
        select_authority=_selection,
    )

    assert result["ok"] is False
    assert result["error"] == "SEMANTIC_BACKEND_UNAVAILABLE"
    assert result["owner_attempts"] == 1
    assert result["owner_retry_performed"] is False
    assert query_calls == ["query"]


def test_two_transient_bootstrap_failures_stop_at_retry_ceiling(
    tmp_path: Path,
) -> None:
    ensure_calls: list[str] = []
    cleanup_calls: list[str] = []

    def ensure(**_kwargs):
        ensure_calls.append("ensure")
        return SimpleNamespace(
            ready=False,
            status="FAILED",
            error="HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP",
        )

    result = query_once(
        {"query": "audit pfmall"},
        repo_root=tmp_path,
        ensure_owner=ensure,
        cleanup_owner=lambda: cleanup_calls.append("cleaned"),
        query_owner=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("query must not run after bootstrap failure")
        ),
        select_authority=_selection,
    )

    assert result["ok"] is False
    assert result["owner_attempts"] == 2
    assert result["owner_retry_performed"] is True
    assert result["no_holoindex_reindex_performed"] is True
    assert ensure_calls == ["ensure", "ensure"]
    assert cleanup_calls == ["cleaned"]


def test_authority_selection_failure_precedes_owner_bootstrap(
    tmp_path: Path,
) -> None:
    selection = HoloIndexAuthoritySelection(
        accepted=False,
        selected_root=tmp_path,
        workspace_head_sha="c" * 40,
        authority_head_sha="",
        authority_root_digest="",
        workspace_overlay_present=True,
        source="configured",
        rejection_reasons=("HOLOINDEX_AUTHORITY_ROOT_DIRTY",),
    )
    result = query_once(
        {"query": "audit pfmall"},
        repo_root=tmp_path,
        ensure_owner=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("owner must not start after authority rejection")
        ),
        select_authority=lambda _root: selection,
    )

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_AUTHORITY_ROOT_DIRTY"
    assert result["workspace_overlay_present"] is True
    assert result["no_authority_worktree_mutation_performed"] is True


def test_head_mismatch_failure_preserves_verified_authority_binding(
    tmp_path: Path,
) -> None:
    workspace_head = "c" * 40
    authority_head = "d" * 40
    authority_digest = "sha256:" + "e" * 64
    selection = HoloIndexAuthoritySelection(
        accepted=False,
        selected_root=tmp_path,
        workspace_head_sha=workspace_head,
        authority_head_sha=authority_head,
        authority_root_digest=authority_digest,
        workspace_overlay_present=False,
        source="deterministic_sibling",
        rejection_reasons=("HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH",),
    )
    result = query_once(
        {"query": "audit pfmall"},
        repo_root=tmp_path,
        ensure_owner=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("owner must not start against stale authority")
        ),
        select_authority=lambda _root: selection,
    )

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH"
    assert result["owner_attempts"] == 0
    assert result["workspace_repo_head_sha"] == workspace_head
    assert result["authority_repo_head_sha"] == authority_head
    assert result["authority_repo_root_digest"] == authority_digest
    assert result["no_authority_worktree_mutation_performed"] is True


def test_authority_change_after_query_discards_result(tmp_path: Path) -> None:
    accepted = _selection(tmp_path)
    changed = HoloIndexAuthoritySelection(
        **{
            **accepted.__dict__,
            "workspace_head_sha": "d" * 40,
            "authority_head_sha": "d" * 40,
        }
    )
    selections = iter((accepted, changed))
    result = query_once(
        {"query": "audit pfmall"},
        repo_root=tmp_path,
        ensure_owner=lambda **_kwargs: SimpleNamespace(
            ready=True, status="CONFIGURED", error=""
        ),
        query_owner=lambda **_kwargs: _success(tmp_path),
        select_authority=lambda _root: next(selections),
    )

    assert result["ok"] is False
    assert result["error"] == "REPOSITORY_STATE_CHANGED_DURING_QUERY"
    assert "query_receipt" not in result


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
        select_authority=_selection,
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
        select_authority=_selection,
    )

    assert result["ok"] is False
    assert result["error"] == "SecretFailure"
    assert "secret-token-value" not in str(result)
    assert cleaned == [True]
