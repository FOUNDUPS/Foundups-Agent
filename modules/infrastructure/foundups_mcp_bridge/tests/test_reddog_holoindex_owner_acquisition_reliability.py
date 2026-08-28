"""Route continuity and bounded multi-process owner-port regressions."""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from holo_index.authority_worktree import AUTHORITY_REPO_ROOT_ENV
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_owner_bootstrap as bootstrap,
)
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_owner_acquisition as owner_acquisition,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service_supervisor import (
    PORT_IN_USE_ERROR,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_replica_route import (
    QUERY_REPLICA_ROOT_ENV,
    QUERY_REPLICA_ROUTE_FILE_ENV,
)
from modules.infrastructure.foundups_mcp_bridge.tests.reddog_holoindex_owner_bootstrap_support import (
    _FakeSupervisor,
    _clean_owner_state,
    _full_route,
)
from scripts import reddog_holoindex_owner_query_once as owner_query


def _fake_windows_registry(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    registry = SimpleNamespace(
        HKEY_CURRENT_USER=object(),
        KEY_QUERY_VALUE=1,
        REG_SZ=1,
        REG_BINARY=3,
        OpenKey=lambda *_args: nullcontext(object()),
        QueryValueEx=lambda *_args: (_ for _ in ()).throw(OSError("missing")),
    )
    monkeypatch.setattr(owner_acquisition.os, "name", "nt")
    monkeypatch.setitem(sys.modules, "winreg", registry)
    return registry


def test_current_user_route_replaces_stale_route_without_copying_secrets() -> None:
    process = {
        QUERY_REPLICA_ROOT_ENV: "O:/legacy-replica",
        "HOLOINDEX_QUERY_SERVICE_TOKEN": "process-private-token",
        "UNRELATED": "preserved",
    }
    user = {
        AUTHORITY_REPO_ROOT_ENV: "E:/authority",
        QUERY_REPLICA_ROUTE_FILE_ENV: "E:/HQR/runtime/route.json",
    }

    resolved = owner_acquisition.build_owner_query_environment(
        process_environment=process, user_environment=user,
    )

    assert resolved[AUTHORITY_REPO_ROOT_ENV] == "E:/authority"
    assert resolved[QUERY_REPLICA_ROUTE_FILE_ENV].endswith("route.json")
    assert QUERY_REPLICA_ROOT_ENV not in resolved
    assert "HOLOINDEX_QUERY_SERVICE_TOKEN" not in resolved
    assert "UNRELATED" not in resolved
    assert process[QUERY_REPLICA_ROOT_ENV] == "O:/legacy-replica"


def test_one_shot_reuses_the_shared_owner_acquisition_policy() -> None:
    assert owner_query.MAX_OWNER_ATTEMPTS == owner_acquisition.MAX_OWNER_ATTEMPTS
    assert (
        owner_query.MAX_OPERATION_TIMEOUT_SECONDS
        == owner_acquisition.OWNER_OPERATION_TIMEOUT_SECONDS
    )
    assert owner_query.TRANSIENT_OWNER_ERRORS is owner_acquisition.TRANSIENT_OWNER_ERRORS


def test_blank_user_route_preserves_explicit_process_migration_root() -> None:
    process = {QUERY_REPLICA_ROOT_ENV: "O:/legacy-replica"}
    resolved = owner_acquisition.build_owner_query_environment(
        process_environment=process,
        user_environment={QUERY_REPLICA_ROUTE_FILE_ENV: "   "},
    )
    assert resolved == process


def test_route_environment_rejects_non_string_values() -> None:
    with pytest.raises(ValueError, match="holoindex_query_environment_invalid"):
        owner_acquisition.build_owner_query_environment(
            process_environment={QUERY_REPLICA_ROOT_ENV: object()},  # type: ignore[dict-item]
            user_environment={},
        )


def test_windows_user_route_reader_accepts_only_nonempty_string_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    winreg = _fake_windows_registry(monkeypatch)

    def query_value(_key: object, name: str) -> tuple[object, int]:
        if name == AUTHORITY_REPO_ROOT_ENV:
            return "E:/authority", winreg.REG_SZ
        return b"not-a-string", winreg.REG_BINARY

    monkeypatch.setattr(winreg, "QueryValueEx", query_value)

    assert owner_acquisition._windows_user_route_environment() == {
        AUTHORITY_REPO_ROOT_ENV: "E:/authority",
    }


def test_windows_user_route_reader_ignores_missing_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    winreg = _fake_windows_registry(monkeypatch)
    monkeypatch.setattr(
        winreg,
        "QueryValueEx",
        lambda *_args: (_ for _ in ()).throw(OSError("missing")),
    )

    assert owner_acquisition._windows_user_route_environment() == {}


def test_windows_user_route_reader_fails_closed_when_hkcu_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    winreg = _fake_windows_registry(monkeypatch)
    monkeypatch.setattr(
        winreg,
        "OpenKey",
        lambda *_args: (_ for _ in ()).throw(OSError("unavailable")),
    )

    assert owner_acquisition._windows_user_route_environment() == {}


def test_non_windows_user_route_reader_is_empty_without_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(owner_acquisition.os, "name", "posix")
    monkeypatch.delitem(sys.modules, "winreg", raising=False)

    assert owner_acquisition._windows_user_route_environment() == {}


@pytest.mark.parametrize("port", [True, 0, 65_536, "8127"])
def test_bootstrap_rejects_non_exact_owner_port(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, port: object,
) -> None:
    constructor_calls: list[object] = []
    monkeypatch.setattr(
        bootstrap,
        "HoloQueryServiceSupervisor",
        lambda **kwargs: constructor_calls.append(kwargs),
    )

    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path, requested=True,
        query_replica_route=_full_route(tmp_path), owner_port=port,  # type: ignore[arg-type]
    )

    assert result.ready is False
    assert result.error == bootstrap.BOOTSTRAP_FAILED_ERROR
    assert constructor_calls == []


def test_bootstrap_propagates_exact_owner_port(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeSupervisor.instances.clear()
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    try:
        result = bootstrap.ensure_reddog_holoindex_owner(
            repo_root=tmp_path, requested=True,
            query_replica_route=_full_route(tmp_path), owner_port=8190,
        )
        assert result.ready is True
        assert _FakeSupervisor.instances[-1].port == 8190
    finally:
        bootstrap.cleanup_reddog_holoindex_owner()


def test_port_contention_retries_once_on_a_distinct_process_shard(
    tmp_path: Path,
) -> None:
    state = owner_query._OwnerQueryState()
    ports: list[int] = []
    cleanups: list[bool] = []

    def ensure_owner(**kwargs):
        ports.append(kwargs["owner_port"])
        if len(ports) == 1:
            return SimpleNamespace(ready=False, status="FAILED", error=PORT_IN_USE_ERROR)
        return SimpleNamespace(ready=True, status="CONFIGURED", error="")

    result, bindable = owner_query._query_with_retry(
        query="audit", limit=1, authority_root=tmp_path,
        runtime_root=tmp_path, ssd_path=tmp_path / "ssd",
        ensure_owner=ensure_owner, resolve_handoff=lambda: None,
        query_owner=lambda **_kwargs: {"ok": False, "error": "terminal"},
        cleanup_owner=lambda: cleanups.append(True), state=state,
        resolve_replica_route=lambda **_kwargs: SimpleNamespace(
            expected_replica_binding=("d", "g", "r", "p")
        ),
        operation_deadline=None, route_environment={"ROUTE": "safe"},
    )

    assert result["error"] == "terminal"
    assert bindable is True
    assert state.attempts == 2
    assert state.retry_reason == PORT_IN_USE_ERROR
    assert ports == [
        owner_query._owner_port_for_attempt(1),
        owner_query._owner_port_for_attempt(2),
    ]
    assert ports[0] != ports[1]
    assert cleanups == [True]


def test_same_initial_shard_uses_pid_diversified_retry_shard() -> None:
    first_pid = 100
    second_pid = first_pid + owner_query.OWNER_PORT_SHARD_COUNT

    assert owner_query._owner_port_for_attempt(
        1, process_id=first_pid,
    ) == owner_query._owner_port_for_attempt(1, process_id=second_pid)
    assert owner_query._owner_port_for_attempt(
        2, process_id=first_pid,
    ) != owner_query._owner_port_for_attempt(2, process_id=second_pid)


@pytest.mark.parametrize("attempt", [True, 0, 3])
def test_owner_port_policy_rejects_invalid_attempt(attempt: object) -> None:
    with pytest.raises(ValueError, match="owner_attempt_invalid"):
        owner_acquisition.owner_port_for_attempt(attempt)  # type: ignore[arg-type]


@pytest.mark.parametrize("process_id", [True, 0, -1, "100"])
def test_owner_port_policy_rejects_invalid_process_id(process_id: object) -> None:
    with pytest.raises(ValueError, match="owner_process_invalid"):
        owner_acquisition.owner_port_for_attempt(
            1, process_id=process_id,  # type: ignore[arg-type]
        )
