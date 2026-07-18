"""Integration tests for the seven-collection CLI maintenance transaction."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from holo_index import _cli_main as cli
from holo_index.core.indexing_engine import IndexResult
from holo_index.maintenance_session import MaintenanceSessionError
from holo_index.source_scope import canonical_source_scope_id


BASELINE = set(cli.BASELINE_INDEX_COLLECTIONS)


class _Collection:
    metadata = {"embedding_backend": "test"}

    def count(self) -> int:
        return 1

    def get(self, include=None):
        return {"ids": ["one"], "metadatas": [{"path": "source.py"}]}


class _FakeHolo:
    failed_collection = ""
    retrieval_mode_value = "semantic"
    calls: list[str] = []
    symbol_roots_calls: list[object] = []

    def __init__(self, *, ssd_path: str, quiet: bool) -> None:
        del ssd_path, quiet
        self.project_root = Path(__file__).resolve().parents[2]
        self.retrieval_mode = self.__class__.retrieval_mode_value
        for attribute in (
            "code_collection",
            "symbol_collection",
            "wsp_collection",
            "test_collection",
            "skill_collection",
            "docs_collection",
            "knowledge_collection",
            "work_ledger_collection",
            "vocabulary_collection",
        ):
            setattr(self, attribute, _Collection())

    @classmethod
    def _result(cls, name: str) -> IndexResult:
        cls.calls.append(name)
        complete = name != cls.failed_collection
        return IndexResult(
            discovered_count=1,
            indexed_count=1,
            collection_name=name,
            warning=None if complete else "injected incomplete source",
            processed_count=1 if complete else 0,
            source_manifest_digest="sha256:" + ("a" * 64),
            source_scope_id=canonical_source_scope_id(name),
        )

    def index_code_entries(self):
        return self._result("navigation_code")

    def index_symbol_entries(self, roots=None):
        self.__class__.symbol_roots_calls.append(roots)
        return self._result("navigation_symbols")

    def index_wsp_entries(self, paths=None):
        del paths
        return self._result("navigation_wsp")

    def index_test_registry(self):
        return self._result("navigation_tests")

    def index_skillz_entries(self):
        return self._result("navigation_skills")

    def index_docs_entries(self):
        return self._result("navigation_docs")

    def index_knowledge_entries(self):
        return self._result("navigation_knowledge")

    def get_code_entry_count(self) -> int:
        return 1

    def get_wsp_entry_count(self) -> int:
        return 1


class _FakeSession:
    instances: list["_FakeSession"] = []

    def __init__(self, *, planned: set[str], ssd_path: Path) -> None:
        self.planned = planned
        self.receipt_path = ssd_path / "indexes" / "receipt.json"
        self.complete_kwargs = None
        self.closed = False
        self.__class__.instances.append(self)

    @classmethod
    def begin(cls, *, ssd_path, planned_collections, **_kwargs):
        return cls(planned=set(planned_collections), ssd_path=Path(ssd_path))

    def complete(self, _holo, **kwargs):
        self.complete_kwargs = kwargs
        refreshed = set(kwargs["refreshed_collections"])
        proofs = set(kwargs["refresh_proofs"])
        if refreshed != self.planned or proofs != self.planned:
            raise MaintenanceSessionError("HOLOINDEX_MAINTENANCE_INCOMPLETE")
        return SimpleNamespace()

    def close(self) -> None:
        self.closed = True


def _run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _FakeHolo.calls.clear()
    _FakeHolo.symbol_roots_calls.clear()
    _FakeSession.instances.clear()
    monkeypatch.setattr(cli, "HoloIndex", _FakeHolo)
    monkeypatch.setattr(cli, "MaintenanceSession", _FakeSession)
    monkeypatch.setattr(cli, "ADVISOR_AVAILABLE", False)
    monkeypatch.setattr(cli, "AgenticOutputThrottler", None)
    monkeypatch.setattr(
        "modules.infrastructure.database.src.agent_db.AgentDB",
        lambda: SimpleNamespace(
            record_index_refresh=lambda *_args, **_kwargs: None,
            should_refresh_index=lambda *_args, **_kwargs: False,
        ),
    )
    monkeypatch.setenv("HOLO_SYMBOL_AUTO", "1")
    monkeypatch.delenv("HOLOINDEX_QUERY_READONLY", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        ["holo_index.py", "--index-all", "--ssd", str(tmp_path / "ssd")],
    )
    cli.main()


def test_index_all_runs_exact_baseline_and_publishes_matching_proofs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeHolo.failed_collection = ""
    _run(monkeypatch, tmp_path)

    session = _FakeSession.instances[0]
    assert set(_FakeHolo.calls) == BASELINE
    assert _FakeHolo.symbol_roots_calls == [None]
    assert session.planned == BASELINE
    assert set(session.complete_kwargs["refresh_proofs"]) == BASELINE
    assert session.closed is True


def test_incomplete_indexer_exits_four_and_releases_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeHolo.failed_collection = "navigation_tests"
    with pytest.raises(SystemExit) as raised:
        _run(monkeypatch, tmp_path)

    session = _FakeSession.instances[0]
    assert raised.value.code == 4
    assert "navigation_tests" not in session.complete_kwargs["refresh_proofs"]
    assert session.closed is True


def test_lexical_backend_aborts_before_any_collection_indexer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeHolo.retrieval_mode_value = "lexical"
    try:
        with pytest.raises(SystemExit) as raised:
            _run(monkeypatch, tmp_path)
    finally:
        _FakeHolo.retrieval_mode_value = "semantic"

    session = _FakeSession.instances[0]
    assert raised.value.code == 4
    assert _FakeHolo.calls == []
    assert session.complete_kwargs is None
    assert session.closed is True


def test_index_all_rejects_web_source_cap_before_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOLO_WEB_INDEX_MAX_FILES", "1")

    with pytest.raises(SystemExit) as raised:
        _run(monkeypatch, tmp_path)

    assert raised.value.code == 4
    assert _FakeSession.instances == []
    assert _FakeHolo.calls == []
