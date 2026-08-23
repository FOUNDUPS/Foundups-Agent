"""Focused tests for the HoloIndex storage-authority contract."""

from __future__ import annotations

import builtins
import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
os.environ.setdefault("HOLO_SKIP_MODEL", "1")

from holo_index import _cli_main
from holo_index.core.holo_index import HoloIndex
from holo_index.storage_contract import (
    COLLECTION_UNAVAILABLE_CODE,
    STORAGE_NOT_WRITABLE_CODE,
    STORAGE_PATH_MISMATCH_CODE,
    STORAGE_UNAVAILABLE_CODE,
    HoloIndexStorageError,
    classify_storage_exception,
    resolve_holoindex_ssd_path,
    storage_path_identity,
)


class _Collection:
    pass


class _MaintenanceClient:
    def __init__(self) -> None:
        self.names: list[str] = []
        self.configurations: list[dict] = []

    def get_or_create_collection(self, name: str, *, configuration):
        self.names.append(name)
        self.configurations.append(configuration)
        return _Collection()


class _MissingReadonlyCollectionClient:
    def __init__(self) -> None:
        self.create_called = False
        self.generation_id = "sha256:" + "a" * 64

    def get_collection(self, name: str):
        raise RuntimeError(f"collection missing: {name}")

    def create_collection(self, name: str):
        self.create_called = True
        raise AssertionError("read-only initialization must not create a collection")


@pytest.fixture(autouse=True)
def _reset_holoindex_shared_state(monkeypatch):
    old_initialized = HoloIndex._initialized
    old_shared_state = HoloIndex._shared_state
    HoloIndex._initialized = False
    HoloIndex._shared_state = {}
    monkeypatch.setenv("HOLO_SKIP_MODEL", "1")
    monkeypatch.setenv("ANONYMIZED_TELEMETRY", "false")
    yield
    HoloIndex._initialized = old_initialized
    HoloIndex._shared_state = old_shared_state


def _readonly_layout(root: Path) -> None:
    (root / "vectors" / "query_snapshots").mkdir(parents=True)


def _silence_holo_logging(monkeypatch) -> None:
    monkeypatch.setattr(HoloIndex, "_log_agent_action", lambda *args, **kwargs: None)


def test_resolver_precedence_and_absolute_identity(tmp_path: Path) -> None:
    explicit = tmp_path / "explicit"
    canonical = tmp_path / "canonical"
    legacy = tmp_path / "legacy"
    env = {
        "HOLOINDEX_SSD_PATH": str(canonical),
        "HOLO_SSD_PATH": str(legacy),
    }

    assert resolve_holoindex_ssd_path(explicit, environ=env) == explicit.resolve()
    assert resolve_holoindex_ssd_path(None, environ=env) == canonical.resolve()
    assert resolve_holoindex_ssd_path("", environ={"HOLO_SSD_PATH": str(legacy)}) == legacy.resolve()
    assert storage_path_identity(explicit) == os.path.normcase(str(explicit.resolve()))


def test_platform_default_is_absolute_and_not_repo_relative(monkeypatch) -> None:
    monkeypatch.delenv("HOLOINDEX_SSD_PATH", raising=False)
    monkeypatch.delenv("HOLO_SSD_PATH", raising=False)

    resolved = resolve_holoindex_ssd_path()

    assert resolved.is_absolute()
    if os.name != "nt":
        assert resolved != (Path.cwd() / "E:/HoloIndex").resolve()


def test_readonly_missing_store_creates_nothing(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "missing"
    monkeypatch.setenv("HOLOINDEX_QUERY_READONLY", "1")
    _silence_holo_logging(monkeypatch)
    client_called = False

    def unexpected_client(*args, **kwargs):
        nonlocal client_called
        client_called = True
        raise AssertionError("Chroma must not open when the read-only layout is missing")

    monkeypatch.setattr("holo_index.core.holo_index._require_chromadb", unexpected_client)

    with pytest.raises(HoloIndexStorageError) as raised:
        HoloIndex(ssd_path=root, quiet=True)

    assert raised.value.code == STORAGE_UNAVAILABLE_CODE
    assert not root.exists()
    assert client_called is False


def test_readonly_collection_open_never_creates(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "store"
    _readonly_layout(root)
    monkeypatch.setenv("HOLOINDEX_QUERY_READONLY", "1")
    _silence_holo_logging(monkeypatch)
    client = _MissingReadonlyCollectionClient()
    session = type("Session", (), {"client": client, "close": lambda self: None})()
    monkeypatch.setattr(
        "modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_store.open_query_snapshot_client",
        lambda _path: session.client,
    )

    with pytest.raises(HoloIndexStorageError) as raised:
        HoloIndex(ssd_path=root, quiet=True)

    assert raised.value.code == COLLECTION_UNAVAILABLE_CODE
    assert client.create_called is False
    assert not (root / "cache").exists()
    assert not (root / "models").exists()
    assert not (root / "indexes").exists()


def test_readonly_query_uses_immutable_snapshot_client_without_chroma(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "store"
    _readonly_layout(root)
    assert not (root / "vectors" / "chroma.sqlite3").exists()
    monkeypatch.setenv("HOLOINDEX_QUERY_READONLY", "1")
    _silence_holo_logging(monkeypatch)
    captured = {}

    class ReadonlyClient:
        def get_collection(self, _name: str):
            return _Collection()

    client = ReadonlyClient()
    client.generation_id = "sha256:" + "a" * 64
    client.close = lambda: captured.update(closed=True)

    def open_client(vector_path):
        captured["vector_path"] = vector_path
        return client

    monkeypatch.setattr(
        "modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_store.open_query_snapshot_client",
        open_client,
    )

    index = HoloIndex(ssd_path=root, quiet=True)
    index.close()

    assert captured == {"vector_path": root / "vectors", "closed": True}
    assert index.query_snapshot_generation_id == "sha256:" + "a" * 64
    assert index.work_ledger_collection is None
    assert not (root / "vectors" / "chroma.sqlite3").exists()


def test_readonly_snapshot_open_write_denial_has_stable_code(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "store"
    _readonly_layout(root)
    monkeypatch.setenv("HOLOINDEX_QUERY_READONLY", "1")
    _silence_holo_logging(monkeypatch)

    def denied_client(*args, **kwargs):
        raise RuntimeError("error returned from database: (code: 8) attempt to write a readonly database")

    monkeypatch.setattr(
        "modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_store.open_query_snapshot_client",
        denied_client,
    )

    with pytest.raises(HoloIndexStorageError) as raised:
        HoloIndex(ssd_path=root, quiet=True)

    assert raised.value.code == STORAGE_NOT_WRITABLE_CODE
    assert raised.value.operation == "open_query_snapshot"


def test_permission_denial_classifier_is_stable(tmp_path: Path) -> None:
    error = classify_storage_exception(
        PermissionError("Access is denied"),
        path=tmp_path,
        operation="create_storage_layout",
    )

    assert error.code == STORAGE_NOT_WRITABLE_CODE
    assert error.to_dict()["error"] == STORAGE_NOT_WRITABLE_CODE


def test_maintenance_creates_layout_and_gets_or_creates_collections(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "maintenance"
    monkeypatch.delenv("HOLOINDEX_QUERY_READONLY", raising=False)
    _silence_holo_logging(monkeypatch)
    client = _MaintenanceClient()
    monkeypatch.setattr(
        "holo_index.core.holo_index._require_chromadb",
        lambda: type("Chroma", (), {"PersistentClient": staticmethod(lambda **_kwargs: client)}),
    )

    index = HoloIndex(ssd_path=root, quiet=True)

    assert index.ssd_path == root.resolve()
    assert (root / "vectors").is_dir()
    assert (root / "cache").is_dir()
    assert (root / "models").is_dir()
    assert (root / "indexes").is_dir()
    assert client.names == [
        "navigation_code",
        "navigation_wsp",
        "navigation_tests",
        "navigation_skills",
        "navigation_symbols",
        "navigation_docs",
        "navigation_knowledge",
        "navigation_work_ledger",
    ]
    assert all(
        value == {"hnsw": {"batch_size": 2, "sync_threshold": 3}}
        for value in client.configurations
    )


def test_initialized_store_rejects_different_path(tmp_path: Path, monkeypatch) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    monkeypatch.delenv("HOLOINDEX_QUERY_READONLY", raising=False)
    _silence_holo_logging(monkeypatch)
    client = _MaintenanceClient()
    monkeypatch.setattr(
        "holo_index.core.holo_index._require_chromadb",
        lambda: type("Chroma", (), {"PersistentClient": staticmethod(lambda **_kwargs: client)}),
    )
    HoloIndex(ssd_path=first, quiet=True)

    with pytest.raises(HoloIndexStorageError) as raised:
        HoloIndex(ssd_path=second, quiet=True)

    assert raised.value.code == STORAGE_PATH_MISMATCH_CODE
    assert not second.exists()


def test_readonly_activity_log_does_not_open_file(monkeypatch) -> None:
    monkeypatch.setenv("HOLOINDEX_QUERY_READONLY", "1")
    instance = object.__new__(HoloIndex)
    instance.quiet = True

    def unexpected_open(*args, **kwargs):
        raise AssertionError("read-only query attempted to write the activity log")

    monkeypatch.setattr(builtins, "open", unexpected_open)
    instance._log_agent_action("query startup", "TEST")


def test_cli_storage_error_is_structured_and_nonzero(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    error = HoloIndexStorageError(
        STORAGE_UNAVAILABLE_CODE,
        path=tmp_path,
        operation="open_readonly_store",
        detail="missing_required_path=vectors/query_snapshots",
    )

    monkeypatch.setattr(_cli_main, "_MAINTENANCE_RESULT_STREAM", sys.stdout)
    with pytest.raises(SystemExit) as raised:
        _cli_main._exit_storage_error(error)

    payload = json.loads(capsys.readouterr().out.strip())
    assert raised.value.code == _cli_main.STORAGE_ERROR_EXIT_CODE
    assert payload["ok"] is False
    assert payload["error"] == STORAGE_UNAVAILABLE_CODE
