"""Concurrency, timeout, health, and maintenance safety tests for the query owner."""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from holo_index.maintenance_lock import (
    acquire_maintenance_lease,
    maintenance_lock_path,
)
from holo_index.core.search_engine import _search_collection
from modules.infrastructure.foundups_mcp_bridge.src import holo_query_service as service_module
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service import (
    HEALTH_PATH,
    QUERY_PATH,
    create_holo_query_app,
)
from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_service import (
    SHA,
    TOKEN,
    _Backend,
    _query,
    _raw_result,
    _receipt,
    _service,
)


_SAFETY_ENV_NAMES = (
    "HOLOINDEX_QUERY_READONLY",
    "HOLO_OFFLINE",
    "HOLO_DISABLE_PIP_INSTALL",
    "ANONYMIZED_TELEMETRY",
    "HF_HUB_OFFLINE",
    "TRANSFORMERS_OFFLINE",
    "HF_DATASETS_OFFLINE",
    "HOLO_USE_TURBOQUANT",
    "HOLOINDEX_QUERY_SERVICE_TOKEN",
)


class _SerializedBackend(_Backend):
    def __init__(self) -> None:
        super().__init__()
        self.active = 0
        self.max_active = 0
        self.guard = threading.Lock()

    def search(
        self,
        query: str,
        *,
        limit: int,
        doc_type_filter: str,
    ) -> Mapping[str, Any]:
        with self.guard:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(0.04)
        with self.guard:
            self.active -= 1
        self.search_calls += 1
        return self.result


class _Vector(list):
    def tolist(self) -> list[float]:
        return list(self)


class _SlowModel:
    def __init__(self, release: threading.Event) -> None:
        self._release = release

    def encode(self, *_args: Any, **_kwargs: Any) -> _Vector:
        self._release.wait(timeout=1)
        return _Vector([0.1])


class _OneDocumentCollection:
    name = "navigation_code"

    def count(self) -> int:
        return 1

    def query(self, **_kwargs: Any) -> Mapping[str, Any]:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}


class _SlowEncodeBackend(_Backend):
    def __init__(self, release: threading.Event) -> None:
        super().__init__()
        self.model = _SlowModel(release)
        self.embedders = {"sentence_transformers": self.model}
        self.routing_active = False

    def search(
        self,
        query: str,
        *,
        limit: int,
        doc_type_filter: str,
    ) -> Mapping[str, Any]:
        _search_collection(
            self,
            _OneDocumentCollection(),
            query,
            limit,
            kind="code",
        )
        raise AssertionError("blocked encode unexpectedly completed")

    def _log_agent_action(self, *_args: Any) -> None:
        return None


def test_backend_is_singleton_serialized_and_safety_env_precedes_init(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = _SerializedBackend()
    factory_calls = 0
    init_env: dict[str, str | None] = {}

    def factory(_path: Path) -> _SerializedBackend:
        nonlocal factory_calls
        factory_calls += 1
        for name in _SAFETY_ENV_NAMES:
            init_env[name] = os.environ.get(name)
        return backend

    owner = _service(tmp_path, monkeypatch, backend_factory=factory)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(_query, owner) for _ in range(2)]
            results = [future.result(timeout=2) for future in futures]
        assert all(result["ok"] is True for result in results)
        assert factory_calls == 1
        assert backend.search_calls == 2
        assert backend.max_active == 1
        assert init_env == {
            "HOLOINDEX_QUERY_READONLY": "1",
            "HOLO_OFFLINE": "1",
            "HOLO_DISABLE_PIP_INSTALL": "1",
            "ANONYMIZED_TELEMETRY": "false",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "HOLO_USE_TURBOQUANT": "0",
            "HOLOINDEX_QUERY_SERVICE_TOKEN": None,
        }
    finally:
        owner.close()


def test_timeout_is_bounded_and_does_not_trigger_indexing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = threading.Event()

    class SlowBackend(_Backend):
        def search(self, query: str, *, limit: int, doc_type_filter: str) -> Mapping[str, Any]:
            release.wait(timeout=1)
            self.search_calls += 1
            return self.result

    backend = SlowBackend()
    owner = _service(
        tmp_path,
        monkeypatch,
        backend=backend,
        query_timeout_seconds=0.02,
    )
    try:
        started = time.monotonic()
        result = _query(owner)
        elapsed = time.monotonic() - started
        assert result["error"] == "QUERY_TIMEOUT"
        assert result["freshness"] == "STALE"
        assert result["index_gap_detected"] is True
        assert result["stale_reasons"] == ["backend_timeout_owner_poisoned"]
        assert elapsed < 0.5
        assert backend.index_calls == 0
        owner._repository_state_reader = (
            lambda _root: (_ for _ in ()).throw(
                AssertionError("poisoned health must not inspect repository state")
            )
        )
        poison_started = time.monotonic()
        subsequent_query = _query(owner)
        subsequent_health = owner.handle_health(authorization=f"Bearer {TOKEN}")
        poison_elapsed = time.monotonic() - poison_started
        assert subsequent_query["error"] == "QUERY_OWNER_POISONED"
        assert subsequent_query["stale_reasons"] == [
            "backend_timeout_owner_poisoned"
        ]
        assert subsequent_health["error"] == "QUERY_OWNER_POISONED"
        assert subsequent_health["status"] == "unavailable"
        assert poison_elapsed < 0.25
    finally:
        release.set()
        owner.close()


def test_strict_owner_count_failure_never_claims_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class BrokenCollection:
        name = "navigation_code"

        def count(self) -> int:
            raise OSError("injected count failure")

    class BrokenBackend(_Backend):
        model = object()

        def search(
            self, query: str, *, limit: int, doc_type_filter: str
        ) -> Mapping[str, Any]:
            _search_collection(
                self, BrokenCollection(), query, limit, kind="code"
            )
            raise AssertionError("strict count failure was swallowed")

        def _log_agent_action(self, *_args: Any) -> None:
            return None

    owner = _service(tmp_path, monkeypatch, backend=BrokenBackend())
    try:
        result = _query(owner)
        assert result["ok"] is False
        assert result["freshness"] == "STALE"
        assert result["error"] == "SEMANTIC_BACKEND_UNAVAILABLE"
    finally:
        owner.close()


def test_strict_owner_encode_hang_uses_outer_poisoning_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = threading.Event()

    owner = _service(
        tmp_path,
        monkeypatch,
        backend=_SlowEncodeBackend(release),
        query_timeout_seconds=0.02,
    )
    try:
        result = _query(owner)
        assert result["ok"] is False
        assert result["error"] == "QUERY_TIMEOUT"
        assert result["stale_reasons"] == ["backend_timeout_owner_poisoned"]
        assert owner.handle_health(
            authorization=f"Bearer {TOKEN}"
        )["error"] == "QUERY_OWNER_POISONED"
    finally:
        release.set()
        owner.close()


def test_repository_proof_timeout_is_bounded_and_poisoned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def slow_repository(_root: Path) -> Any:
        time.sleep(0.2)
        return SimpleNamespace(proven_clean=True, head_sha=SHA, error="")

    owner = _service(
        tmp_path,
        monkeypatch,
        repository_state_reader=slow_repository,
        query_timeout_seconds=0.03,
    )
    try:
        started = time.monotonic()
        result = _query(owner)
        assert time.monotonic() - started < 0.15
        assert result["error"] == "QUERY_TIMEOUT"
        assert result["stale_reasons"] == ["proof_timeout_owner_poisoned"]
        assert owner.handle_health(
            authorization=f"Bearer {TOKEN}"
        )["error"] == "QUERY_OWNER_POISONED"
    finally:
        owner.close()


def test_waiting_query_uses_one_absolute_deadline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SlowBackend(_Backend):
        def search(self, *_args: Any, **_kwargs: Any) -> Mapping[str, Any]:
            time.sleep(0.06)
            return self.result

    owner = _service(
        tmp_path,
        monkeypatch,
        backend=SlowBackend(),
        query_timeout_seconds=0.09,
    )
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(_query, owner)
            time.sleep(0.01)
            started = time.monotonic()
            second = executor.submit(_query, owner)
            first_result = first.result(timeout=1)
            second_result = second.result(timeout=1)
        assert first_result["ok"] is True
        assert second_result["error"] == "QUERY_TIMEOUT"
        assert time.monotonic() - started < 0.2
    finally:
        owner.close()


def test_health_returns_busy_without_waiting_for_query_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _service(tmp_path, monkeypatch)
    owner._request_lock.acquire()
    try:
        started = time.monotonic()
        result = owner.handle_health(authorization=f"Bearer {TOKEN}")
        assert time.monotonic() - started < 0.05
        assert result["error"] == "OWNER_BUSY"
        assert result["freshness"] == "UNKNOWN"
        assert result["index_gap_detected"] is True
    finally:
        owner._request_lock.release()
        owner.close()


def test_health_runs_authenticated_generation_proven_semantic_canary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = _Backend()
    owner = _service(tmp_path, monkeypatch, backend=backend)
    try:
        assert owner.handle_health(authorization=None)["error"] == "UNAUTHORIZED"
        result = owner.handle_health(authorization=f"Bearer {TOKEN}")
        assert result["ok"] is True
        assert result["status"] == "ready"
        assert result["loopback_only"] is True
        assert result["freshness"] == "CURRENT"
        assert result["retrieval_mode"] == "semantic"
        assert result["query"] == ""
        assert result["raw_result"] == {}
        assert backend.search_calls == 1
    finally:
        owner.close()


def test_cold_health_uses_one_warmup_budget_without_extending_queries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered = threading.Event()
    release = threading.Event()
    backend = _Backend()
    factory_calls = 0

    def slow_factory(_path: Path) -> _Backend:
        nonlocal factory_calls
        factory_calls += 1
        entered.set()
        release.wait(timeout=0.2)
        return backend

    owner = _service(
        tmp_path,
        monkeypatch,
        backend_factory=slow_factory,
        query_timeout_seconds=0.02,
        startup_warmup_timeout_seconds=0.3,
    )
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            first = executor.submit(
                owner.handle_health,
                authorization=f"Bearer {TOKEN}",
            )
            assert entered.wait(timeout=0.1)
            busy = owner.handle_health(authorization=f"Bearer {TOKEN}")
            assert busy["error"] == "OWNER_BUSY"
            assert factory_calls == 1
            release.set()
            ready = first.result(timeout=0.5)
        assert ready["ok"] is True
        assert owner._warmed.is_set()
        assert _query(owner)["ok"] is True
        assert owner.query_timeout_seconds == 0.02
    finally:
        release.set()
        owner.close()


def test_health_rejects_backend_attribute_without_semantic_result_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = dict(_raw_result())
    raw["metadata"] = {"retrieval_mode": "semantic"}
    backend = _Backend(raw, mode="semantic")
    owner = _service(tmp_path, monkeypatch, backend=backend)
    try:
        result = owner.handle_health(authorization=f"Bearer {TOKEN}")
        assert result["ok"] is False
        assert result["status"] == "unavailable"
        assert result["error"] == "SEMANTIC_BACKEND_UNAVAILABLE"
        assert backend.search_calls == 1
    finally:
        owner.close()


def test_dirty_repository_fails_before_freshness_or_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = _Backend()
    owner = _service(
        tmp_path,
        monkeypatch,
        backend=backend,
        repository_state_reader=lambda _root: SimpleNamespace(
            proven_clean=False,
            head_sha=SHA,
            error="HOLOINDEX_REPOSITORY_DIRTY",
        ),
    )
    try:
        result = _query(owner)
        assert result["error"] == "HOLOINDEX_REPOSITORY_DIRTY"
        assert backend.search_calls == 0
    finally:
        owner.close()


def test_active_maintenance_lease_blocks_query_and_health_before_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = _Backend()
    owner = _service(tmp_path, monkeypatch, backend=backend)
    lock_path = maintenance_lock_path(tmp_path / "holo-store")
    try:
        with acquire_maintenance_lease(lock_path):
            query = _query(owner)
            health = owner.handle_health(authorization=f"Bearer {TOKEN}")
        assert query["error"] == "HOLOINDEX_MAINTENANCE_ACTIVE"
        assert health["error"] == "HOLOINDEX_MAINTENANCE_ACTIVE"
        assert query["stale_reasons"] == ["holoindex_maintenance_active"]
        assert health["status"] == "unavailable"
        assert backend.search_calls == 0
        assert _query(owner)["ok"] is True
    finally:
        owner.close()


def test_unproven_maintenance_lock_fails_before_repository_or_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = _Backend()
    owner = _service(
        tmp_path,
        monkeypatch,
        backend=backend,
        maintenance_probe=lambda _path: SimpleNamespace(
            clear=False, held=False, status="error"
        ),
        repository_state_reader=lambda _root: (_ for _ in ()).throw(
            AssertionError("unproven maintenance state must gate repository reads")
        ),
    )
    try:
        result = _query(owner)
        assert result["error"] == "HOLOINDEX_MAINTENANCE_LOCK_UNPROVEN"
        assert result["stale_reasons"] == [
            "holoindex_maintenance_lock_unproven"
        ]
        assert backend.search_calls == 0
    finally:
        owner.close()


def test_maintenance_starting_during_freshness_evaluation_blocks_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clear = SimpleNamespace(clear=True, held=False, status="idle")
    held = SimpleNamespace(clear=False, held=True, status="held")
    probes = iter([clear, clear, clear, held])
    backend = _Backend()
    receipt_reads = 0

    def load_receipt(_path: Path) -> Mapping[str, Any]:
        nonlocal receipt_reads
        receipt_reads += 1
        return _receipt()

    owner = _service(
        tmp_path,
        monkeypatch,
        backend=backend,
        receipt_loader=load_receipt,
        maintenance_probe=lambda _path: next(probes),
    )
    try:
        result = _query(owner)
        assert result["error"] == "HOLOINDEX_MAINTENANCE_ACTIVE"
        assert result["freshness"] == "UNKNOWN"
        assert receipt_reads == 1
        assert backend.search_calls == 0
    finally:
        owner.close()


def test_maintenance_starting_after_backend_rejects_query_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clear = SimpleNamespace(clear=True, held=False, status="idle")
    held = SimpleNamespace(clear=False, held=True, status="held")
    probes = iter([clear, clear, clear, clear, held])
    backend = _Backend()
    owner = _service(
        tmp_path,
        monkeypatch,
        backend=backend,
        maintenance_probe=lambda _path: next(probes),
    )
    try:
        result = _query(owner)
        assert result["ok"] is False
        assert result["error"] == "HOLOINDEX_MAINTENANCE_ACTIVE"
        assert result["stale_reasons"] == ["holoindex_maintenance_active"]
        assert result["raw_result"] == {}
        assert result["hits"] == []
        assert backend.search_calls == 1
    finally:
        owner.close()


def test_fastapi_surface_is_optional_and_has_only_two_application_routes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = _service(tmp_path, monkeypatch)
    try:
        if service_module.FastAPI is None:
            with pytest.raises(RuntimeError, match="FASTAPI_DEPENDENCY_UNAVAILABLE"):
                create_holo_query_app(owner)
            return
        app = create_holo_query_app(owner)
        assert {route.path for route in app.routes} == {QUERY_PATH, HEALTH_PATH}
    finally:
        owner.close()
