"""Tests for the trusted RedDog/HoloIndex maintenance handshake."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from holo_index.freshness_receipt import (
    BASELINE_QUERY_COLLECTIONS,
    CollectionFreshness,
    HoloIndexFreshnessReceipt,
    freshness_receipt_path,
    write_freshness_receipt,
)
from holo_index.repository_state import RepositoryState
from holo_index.source_scope import canonical_source_scope_id
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_maintenance_handshake as handshake,
)
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_main_preflight as main_preflight,
)


HEAD = "a" * 40


def _state(*, head: str = HEAD, clean: bool = True) -> RepositoryState:
    return RepositoryState(
        head_sha=head,
        clean=clean,
        state_digest="sha256:state",
        error="" if clean else "dirty",
    )


def _receipt(
    repo_root: Path,
    ssd_path: Path,
    *,
    embedding_fingerprint: str = "sha256:" + ("1" * 64),
) -> HoloIndexFreshnessReceipt:
    entries = [
        CollectionFreshness(
            name=name,
            source_scope_id=canonical_source_scope_id(name),
            count=1,
            status="indexed",
            source="cli",
            repo_head_sha=HEAD,
            last_indexed_at="2026-07-18T00:00:00+00:00",
            source_manifest_digest="sha256:" + ("b" * 64),
            indexed_paths_digest="sha256:" + ("c" * 64),
            removed_paths_digest="sha256:" + ("d" * 64),
            embedding_backend="sentence_transformers",
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_space_fingerprint=embedding_fingerprint,
            verification="PASS",
            proof_kind="complete_source_manifest",
        )
        for name in sorted(BASELINE_QUERY_COLLECTIONS)
    ]
    return HoloIndexFreshnessReceipt(
        schema_version="holoindex_freshness_receipt.v1",
        generated_at="2026-07-18T00:00:00+00:00",
        repo_root=str(repo_root),
        repo_head_sha=HEAD,
        ssd_path=str(ssd_path),
        source="cli",
        generation_id="sha256:generation",
        collections=entries,
    )


def _publish(repo_root: Path, ssd_path: Path) -> None:
    write_freshness_receipt(
        _receipt(repo_root, ssd_path),
        freshness_receipt_path(ssd_path),
    )


def _ready_owner(**_kwargs):
    return SimpleNamespace(ready=True, status="STARTED", error="")


_SCOPE_OVERRIDE_NAMES = frozenset(
    {
        "HOLO_FAST_SEARCH",
        "HOLO_INDEX_SYMBOLS",
        "HOLO_INDEX_WEB",
        "HOLO_SKIP_MODEL",
        "HOLO_SYMBOL_AUTO",
        "HOLO_SYMBOL_ROOTS",
        "HOLO_SYMBOL_MAX_FILES",
        "HOLO_WEB_INDEX_ROOTS",
        "HOLO_WEB_INDEX_MAX_FILES",
        "HOLO_WSP_PATHS",
        "HOLOINDEX_WSP_ROOTS",
        "WSP_PATHS",
    }
)

_PARTIAL_REFRESH_ENV = {
    "HOLOINDEX_QUERY_READONLY": "1",
    "HOLO_OFFLINE": "1",
    "HOLO_SKIP_MODEL": "1",
    "HOLO_FAST_SEARCH": "1",
    "HOLO_INDEX_SYMBOLS": "0",
    "HOLO_INDEX_WEB": "0",
    "HOLO_SYMBOL_AUTO": "0",
    "HOLO_SYMBOL_ROOTS": "modules/one",
    "HOLO_SYMBOL_MAX_FILES": "1",
    "HOLO_WEB_INDEX_ROOTS": "public/one",
    "HOLO_WEB_INDEX_MAX_FILES": "1",
    "HOLO_WSP_PATHS": "WSP_framework/src/WSP_00_Zen_State.md",
    "HOLOINDEX_WSP_ROOTS": "WSP_framework/src",
    "WSP_PATHS": "WSP_framework/src",
}


def _publishing_refresh_runner(repo_root: Path, ssd_path: Path):
    def runner(command, **kwargs):
        assert command[1:3] == ["-B", str(repo_root / "holo_index.py")]
        assert command[-3:] == ["--index-all", "--ssd", str(ssd_path)]
        assert kwargs["shell"] is False
        assert "HOLOINDEX_QUERY_SERVICE_TOKEN" not in kwargs["env"]
        assert "HOLOINDEX_QUERY_READONLY" not in kwargs["env"]
        assert kwargs["env"]["HOLO_OFFLINE"] == "1"
        assert kwargs["env"]["HOLO_USE_TURBOQUANT"] == "0"
        assert _SCOPE_OVERRIDE_NAMES.isdisjoint(kwargs["env"])
        assert kwargs["stdout"] is subprocess.DEVNULL
        _publish(repo_root, ssd_path)
        return SimpleNamespace(returncode=0)

    return runner


def test_fresh_exact_head_receipt_starts_owner_without_refresh(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root, ssd_path = tmp_path / "repo", tmp_path / "ssd"
    repo_root.mkdir()
    _publish(repo_root, ssd_path)
    monkeypatch.setattr(handshake, "read_repository_state", lambda _root: _state())
    monkeypatch.setattr(
        handshake.owner_bootstrap, "ensure_reddog_holoindex_owner", _ready_owner
    )

    result = handshake.ensure_reddog_holoindex_operational(
        repo_root=repo_root,
        requested=True,
        environ={"HOLOINDEX_SSD_PATH": str(ssd_path)},
        runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError()),
    )

    assert result.ready is True
    assert result.status == handshake.OPERATIONAL_READY
    assert result.refreshed is False
    assert result.generation_id == "sha256:generation"


def test_missing_receipt_runs_bounded_secret_free_refresh_and_restarts_owner(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root, ssd_path = tmp_path / "repo", tmp_path / "ssd"
    repo_root.mkdir()
    cleanup_calls: list[bool] = []
    monkeypatch.setattr(handshake, "read_repository_state", lambda _root: _state())
    monkeypatch.setattr(
        handshake.owner_bootstrap,
        "cleanup_reddog_holoindex_owner",
        lambda: cleanup_calls.append(True),
    )
    monkeypatch.setattr(
        handshake.owner_bootstrap, "ensure_reddog_holoindex_owner", _ready_owner
    )

    result = handshake.ensure_reddog_holoindex_operational(
        repo_root=repo_root,
        requested=True,
        environ={
            "HOLOINDEX_SSD_PATH": str(ssd_path),
            **_PARTIAL_REFRESH_ENV,
        },
        runner=_publishing_refresh_runner(repo_root, ssd_path),
    )

    assert result.ready is True
    assert result.status == handshake.OPERATIONAL_REFRESHED
    assert cleanup_calls == [True]


def test_refresh_environment_strips_secrets_and_casefolded_scope_overrides(
    tmp_path: Path,
) -> None:
    ssd_path = tmp_path / "ssd"
    child = handshake._refresh_environment(
        environ={
            "HOLOINDEX_QUERY_SERVICE_URL": "http://127.0.0.1:8127",
            "HOLOINDEX_QUERY_SERVICE_TOKEN": "x" * 32,
            "holo_symbol_max_files": "1",
            "holo_web_index_roots": "public/partial",
            "holoindex_wsp_roots": "WSP_framework/src/partial",
            "HOLO_OFFLINE": "1",
        },
        ssd_path=ssd_path,
    )
    assert "HOLOINDEX_QUERY_SERVICE_URL" not in child
    assert "HOLOINDEX_QUERY_SERVICE_TOKEN" not in child
    assert "holo_symbol_max_files" not in child
    assert "holo_web_index_roots" not in child
    assert "holoindex_wsp_roots" not in child
    assert child["HOLO_OFFLINE"] == "1"
    assert child["HOLOINDEX_SSD_PATH"] == str(ssd_path)
    assert child["HOLO_USE_TURBOQUANT"] == "0"


def test_legacy_receipt_without_embedding_space_triggers_refresh(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root, ssd_path = tmp_path / "repo", tmp_path / "ssd"
    repo_root.mkdir()
    write_freshness_receipt(
        _receipt(repo_root, ssd_path, embedding_fingerprint=""),
        freshness_receipt_path(ssd_path),
    )
    refresh_calls: list[bool] = []
    monkeypatch.setattr(handshake, "read_repository_state", lambda _root: _state())
    monkeypatch.setattr(
        handshake.owner_bootstrap, "cleanup_reddog_holoindex_owner", lambda: None
    )
    monkeypatch.setattr(
        handshake.owner_bootstrap, "ensure_reddog_holoindex_owner", _ready_owner
    )

    def runner(*_args, **_kwargs):
        refresh_calls.append(True)
        _publish(repo_root, ssd_path)
        return SimpleNamespace(returncode=0)

    result = handshake.ensure_reddog_holoindex_operational(
        repo_root=repo_root,
        requested=True,
        environ={"HOLOINDEX_SSD_PATH": str(ssd_path)},
        runner=runner,
    )
    assert result.ready is True
    assert result.status == handshake.OPERATIONAL_REFRESHED
    assert refresh_calls == [True]


def test_dirty_repository_fails_before_owner_or_refresh(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        handshake, "read_repository_state", lambda _root: _state(clean=False)
    )
    result = handshake.ensure_reddog_holoindex_operational(
        repo_root=tmp_path,
        requested=True,
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
    )
    assert result.ready is False
    assert result.error == handshake.DIRTY_ERROR


def test_stale_external_owner_is_never_stopped_or_reindexed(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(handshake, "read_repository_state", lambda _root: _state())
    result = handshake.ensure_reddog_holoindex_operational(
        repo_root=tmp_path,
        requested=True,
        environ={
            "HOLOINDEX_SSD_PATH": str(tmp_path / "ssd"),
            "HOLOINDEX_QUERY_SERVICE_URL": "http://127.0.0.1:8127",
            "HOLOINDEX_QUERY_SERVICE_TOKEN": "x" * 32,
        },
    )
    assert result.ready is False
    assert result.error == handshake.EXTERNAL_OWNER_ERROR


def test_disabled_maintenance_reports_required(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(handshake, "read_repository_state", lambda _root: _state())
    result = handshake.ensure_reddog_holoindex_operational(
        repo_root=tmp_path,
        requested=True,
        auto_maintenance=False,
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
    )
    assert result.ready is False
    assert result.error == handshake.MAINTENANCE_REQUIRED_ERROR
    assert "missing_freshness_receipt" in result.freshness_reasons


def test_nonzero_refresh_fails_without_starting_owner(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(handshake, "read_repository_state", lambda _root: _state())
    monkeypatch.setattr(
        handshake.owner_bootstrap, "cleanup_reddog_holoindex_owner", lambda: None
    )
    result = handshake.ensure_reddog_holoindex_operational(
        repo_root=tmp_path,
        requested=True,
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        runner=lambda *_args, **_kwargs: SimpleNamespace(returncode=7),
    )
    assert result.ready is False
    assert result.error == handshake.REFRESH_FAILED_ERROR


def test_repository_head_change_after_refresh_fails_closed(
    tmp_path: Path, monkeypatch
) -> None:
    states = iter((_state(), _state(head="e" * 40)))
    monkeypatch.setattr(handshake, "read_repository_state", lambda _root: next(states))
    monkeypatch.setattr(
        handshake.owner_bootstrap, "cleanup_reddog_holoindex_owner", lambda: None
    )
    result = handshake.ensure_reddog_holoindex_operational(
        repo_root=tmp_path,
        requested=True,
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        runner=lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )
    assert result.ready is False
    assert result.error == handshake.REPOSITORY_CHANGED_ERROR


def test_not_requested_is_side_effect_free(tmp_path: Path) -> None:
    result = handshake.ensure_reddog_holoindex_operational(
        repo_root=tmp_path,
        requested=False,
    )
    assert result.ready is False
    assert result.status == handshake.OPERATIONAL_NOT_REQUESTED


def test_headless_aborts_before_supervisor_when_holo_preflight_fails(
    monkeypatch,
) -> None:
    import main

    monkeypatch.setattr(
        main,
        "run_connect_wre",
        lambda _root: {
            "readiness": "READY",
            "alert_counts": {"critical": 0, "warning": 0},
        },
    )
    monkeypatch.setattr(
        main,
        "run_reddog_holoindex_headless_preflight",
        lambda _root: False,
    )
    assert main.run_headless() == 1


def test_headless_owner_preflight_calls_operational_handshake(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(
        main_preflight,
        "ensure_reddog_holoindex_operational",
        lambda **kwargs: calls.append(kwargs)
        or SimpleNamespace(
            ready=True,
            status="READY",
            refreshed=False,
            error="",
        ),
    )
    environ = {
        "OPENCLAW_AUTO_TASKS_ENABLED": "1",
        "HOLOINDEX_SSD_PATH": str(tmp_path / "ssd"),
    }
    assert main_preflight.run_headless_owner_preflight(
        tmp_path,
        environ=environ,
    ) is True
    assert calls == [
        {
            "repo_root": tmp_path,
            "requested": True,
            "environ": environ,
        }
    ]


def test_interactive_auto_tasks_default_to_required_maintenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import main

    calls: list[dict] = []
    monkeypatch.setattr(
        main_preflight,
        "run_interactive_owner_preflight",
        lambda **kwargs: calls.append(kwargs) or False,
    )
    with patch.dict(
        "os.environ",
        {"OPENCLAW_AUTO_TASKS_ENABLED": "1"},
        clear=True,
    ):
        assert main.run_reddog_readonly_operational_bootstrap_preflight(tmp_path) is False
    assert calls == [
        {
            "repo_root": tmp_path,
            "maintenance_requested": True,
            "enforced": False,
        }
    ]
