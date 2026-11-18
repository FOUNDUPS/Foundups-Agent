"""Owner lifecycle tests for RedDog's host-owned HoloIndex bootstrap."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from .reddog_holoindex_owner_bootstrap_support import (
    REPLICA_BINDING,
    SAFE_TOKEN,
    SAFE_URL,
    REAL_ENSURE_OWNER,
    REAL_VERIFY_OWNER,
    _FakeReplicaRoute,
    _FakeSupervisor,
    _clean_owner_state,
    _full_route,
    bootstrap,
    configured,
    HoloQueryServiceSupervisorError,
    SERVICE_TOKEN_ENV,
    SERVICE_URL_ENV,
)


@pytest.mark.parametrize(
    ("url", "token"),
    [
        ("http://127.0.0.1:not-a-port", SAFE_TOKEN),
        ("http://127.0.0.1:8127/not-an-owner-route", SAFE_TOKEN),
        ("http://127.0.0.1:8127", "weak"),
        ("http://localhost:8127", SAFE_TOKEN),
        ("http://[::1]:8127", SAFE_TOKEN),
        ("https://127.0.0.1:8127", SAFE_TOKEN),
    ],
)
def test_invalid_explicit_configuration_fails_without_overwrite_or_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    url: str,
    token: str,
) -> None:
    monkeypatch.setenv(SERVICE_URL_ENV, url)
    monkeypatch.setenv(SERVICE_TOKEN_ENV, token)
    constructor = Mock(side_effect=AssertionError("must not overwrite explicit config"))
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", constructor)

    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
    )

    assert result.status == bootstrap.OWNER_FAILED
    assert result.error == bootstrap.CONFIGURED_INVALID_ERROR
    assert os.environ[SERVICE_URL_ENV] == url
    assert os.environ[SERVICE_TOKEN_ENV] == token
    constructor.assert_not_called()


def test_owner_start_uses_caller_lifecycle_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(SERVICE_URL_ENV, raising=False)
    monkeypatch.delenv(SERVICE_TOKEN_ENV, raising=False)
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)

    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
        query_replica_route=_full_route(tmp_path),
        startup_timeout_seconds=7.0,
    )

    assert result.ready is True
    owner = _FakeSupervisor.instances[-1]
    assert owner.startup_timeout_seconds == 7.0
    assert owner.probe_timeout_seconds == 7.0
    assert owner.shutdown_timeout_seconds == 3.0


def test_configured_service_requires_authenticated_semantic_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(SERVICE_URL_ENV, SAFE_URL)
    monkeypatch.setenv(SERVICE_TOKEN_ENV, SAFE_TOKEN)
    health = Mock(return_value=False)
    monkeypatch.setattr(bootstrap, "_configured_owner_health_ready", health)
    constructor = Mock(side_effect=AssertionError("must preserve configured service"))
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", constructor)

    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
    )

    assert result.ready is False
    assert result.status == bootstrap.OWNER_FAILED
    assert result.error == bootstrap.CONFIGURED_UNREADY_ERROR
    assert os.environ[SERVICE_URL_ENV] == SAFE_URL
    assert os.environ[SERVICE_TOKEN_ENV] == SAFE_TOKEN
    health.assert_called_once_with(
        service_url=SAFE_URL,
        token=SAFE_TOKEN,
        expected_repo_head_sha="",
        expected_repo_root_digest=bootstrap.repository_root_digest(tmp_path),
        expected_generation_id="",
        expected_receipt_digest="",
        expected_replica_binding=REPLICA_BINDING,
    )
    constructor.assert_not_called()


def test_auto_start_opt_out_is_secret_free_and_side_effect_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(bootstrap.AUTO_START_ENV, "0")
    constructor = Mock(side_effect=AssertionError("opt-out must prevent start"))
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", constructor)

    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
    )

    assert result.status == bootstrap.OWNER_AUTO_START_DISABLED
    assert result.error == bootstrap.AUTO_START_DISABLED_ERROR
    assert SAFE_TOKEN not in repr(result)
    constructor.assert_not_called()


def test_auto_start_uses_canonical_store_and_keeps_handoff_process_private(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    route = _full_route(tmp_path)
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    monkeypatch.setenv("UNRELATED_VALUE", "preserved")

    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
        query_replica_route=route,
    )

    assert result.ready is True
    assert result.status == bootstrap.OWNER_STARTED
    assert len(_FakeSupervisor.instances) == 1
    assert _FakeSupervisor.instances[0].ssd_path == route.canonical_ssd_path
    assert not hasattr(bootstrap, "resolve_holoindex_ssd_path")
    assert SERVICE_URL_ENV not in os.environ
    assert SERVICE_TOKEN_ENV not in os.environ
    assert bootstrap.resolve_reddog_holoindex_owner_handoff() == (
        SAFE_URL,
        SAFE_TOKEN,
    )
    assert os.environ["UNRELATED_VALUE"] == "preserved"


def test_auto_start_forwards_explicit_trusted_runtime_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority = tmp_path / "authority"
    runtime_root = tmp_path / "workspace"
    authority.mkdir()
    runtime_root.mkdir()
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)

    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=authority,
        runtime_root=runtime_root,
        requested=True,
    )

    assert result.ready is True
    assert _FakeSupervisor.instances[0].repo_root == authority
    assert _FakeSupervisor.instances[0].runtime_root == runtime_root
    assert SAFE_TOKEN not in repr(result)


def test_owner_starts_once_and_reuses_process_lifetime_instance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    first = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
    )
    second = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
    )

    assert first.status == bootstrap.OWNER_STARTED
    assert second.status == bootstrap.OWNER_REUSED
    assert len(_FakeSupervisor.instances) == 1
    assert bootstrap.resolve_reddog_holoindex_owner_handoff() == (
        SAFE_URL,
        SAFE_TOKEN,
    )


def test_exact_replica_binding_reuses_owned_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    binding = ("descriptor", "generation", "replica", "path")
    first_route = _FakeReplicaRoute(tmp_path, binding)
    equivalent_route = _FakeReplicaRoute(tmp_path, binding)

    first = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path, requested=True, query_replica_route=first_route
    )
    reused = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path, requested=True, query_replica_route=equivalent_route
    )

    assert first.status == bootstrap.OWNER_STARTED
    assert reused.status == bootstrap.OWNER_REUSED
    assert len(_FakeSupervisor.instances) == 1
    assert _FakeSupervisor.instances[0].verified_replica_binding == binding
    assert equivalent_route.revalidations > 0
    assert _FakeSupervisor.instances[0].lifecycle_events == ["process", "health"]


@pytest.mark.parametrize("changed_index", (0, 1, 2, 3))
def test_replica_descriptor_or_generation_drift_forces_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed_index: int,
) -> None:
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    original = ["descriptor", "generation", "replica", "path"]
    changed = list(original)
    changed[changed_index] += "-changed"
    first_route = _FakeReplicaRoute(tmp_path, tuple(original))
    changed_route = _FakeReplicaRoute(tmp_path, tuple(changed))

    first = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path, requested=True, query_replica_route=first_route
    )
    first_owner = _FakeSupervisor.instances[0]
    replacement = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path, requested=True, query_replica_route=changed_route
    )

    assert first.status == bootstrap.OWNER_STARTED
    assert replacement.status == bootstrap.OWNER_STARTED
    assert first_owner.stopped is True
    assert len(_FakeSupervisor.instances) == 2
    assert _FakeSupervisor.instances[1].verified_replica_binding == tuple(changed)


def test_active_replica_swap_during_start_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    route = _FakeReplicaRoute(
        tmp_path,
        ("descriptor", "generation", "replica", "path"),
        fail_on_revalidation=3,
    )

    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path, requested=True, query_replica_route=route
    )

    assert result.ready is False
    assert result.status == bootstrap.OWNER_FAILED
    assert result.error == bootstrap.BOOTSTRAP_FAILED_ERROR
    assert _FakeSupervisor.instances[0].lifecycle_events == []
    assert _FakeSupervisor.instances[0].stopped is True
    assert bootstrap.resolve_reddog_holoindex_owner_handoff() is None


def test_changed_exact_binding_replaces_owned_process_instead_of_reusing_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    first_binding = (
        "a" * 40,
        bootstrap.repository_root_digest(tmp_path),
        "sha256:" + ("b" * 64),
        "sha256:" + ("c" * 64),
    )
    second_binding = (
        "d" * 40,
        bootstrap.repository_root_digest(tmp_path),
        "sha256:" + ("e" * 64),
        "sha256:" + ("f" * 64),
    )
    first = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
        expected_repo_head_sha=first_binding[0],
        expected_generation_id=first_binding[2],
        expected_receipt_digest=first_binding[3],
    )
    first_owner = _FakeSupervisor.instances[0]

    second = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
        expected_repo_head_sha=second_binding[0],
        expected_generation_id=second_binding[2],
        expected_receipt_digest=second_binding[3],
    )

    assert first.status == bootstrap.OWNER_STARTED
    assert second.status == bootstrap.OWNER_STARTED
    assert first_owner.stopped is True
    assert len(_FakeSupervisor.instances) == 2
    assert _FakeSupervisor.instances[-1].verified_binding == second_binding


def test_changed_runtime_root_replaces_owned_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority = tmp_path / "authority"
    runtime_a = tmp_path / "runtime-a"
    runtime_b = tmp_path / "runtime-b"
    for path in (authority, runtime_a, runtime_b):
        path.mkdir()
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)

    first = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=authority,
        runtime_root=runtime_a,
        requested=True,
    )
    first_owner = _FakeSupervisor.instances[0]
    second = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=authority,
        runtime_root=runtime_b,
        requested=True,
    )

    assert first.status == bootstrap.OWNER_STARTED
    assert second.status == bootstrap.OWNER_STARTED
    assert first_owner.stopped is True
    assert len(_FakeSupervisor.instances) == 2
    assert _FakeSupervisor.instances[1].runtime_root == runtime_b


def test_auto_owner_secret_is_not_inherited_by_unrelated_subprocess(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
    )

    child = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import os; "
                "print(int('HOLOINDEX_QUERY_SERVICE_URL' in os.environ), "
                "int('HOLOINDEX_QUERY_SERVICE_TOKEN' in os.environ))"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )

    assert result.ready is True
    assert child.stdout.strip() == "0 0"
    assert SAFE_TOKEN not in child.stdout


def test_dead_or_invalid_handoff_owner_is_replaced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    bootstrap.ensure_reddog_holoindex_owner(repo_root=tmp_path, requested=True)
    first = _FakeSupervisor.instances[0]
    first.environment_for_child = Mock(side_effect=RuntimeError("invalid handoff"))

    replaced = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
    )

    assert replaced.status == bootstrap.OWNER_STARTED
    assert first.stopped is True
    assert len(_FakeSupervisor.instances) == 2
    _FakeSupervisor.instances[-1].stopped = True

    restarted = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
    )

    assert restarted.status == bootstrap.OWNER_STARTED
    assert len(_FakeSupervisor.instances) == 3


def test_private_resolver_does_not_health_probe_a_live_busy_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    health = Mock(return_value=True)
    monkeypatch.setattr(
        bootstrap,
        "_configured_owner_health_ready",
        health,
    )
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    started = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
    )
    first = _FakeSupervisor.instances[0]

    handoff = bootstrap.resolve_reddog_holoindex_owner_handoff()

    assert started.ready is True
    assert first.stopped is False
    assert len(_FakeSupervisor.instances) == 1
    assert handoff == (SAFE_URL, SAFE_TOKEN)
    health.assert_not_called()


def test_explicit_private_restart_replaces_failed_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    route = _full_route(tmp_path)
    started = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
        query_replica_route=route,
        owner_port=8188,
    )
    first = _FakeSupervisor.instances[0]
    failed_handoff = bootstrap.resolve_reddog_holoindex_owner_handoff()

    restarted = bootstrap.restart_reddog_holoindex_owner(
        failed_handoff=failed_handoff,
    )

    assert started.ready is True
    assert first.stopped is True
    assert len(_FakeSupervisor.instances) == 2
    assert first.port == 8188
    assert _FakeSupervisor.instances[1].port == 8188
    assert _FakeSupervisor.instances[1].verified_replica_binding == REPLICA_BINDING
    assert route.revalidations > 0
    assert restarted == (SAFE_URL, SAFE_TOKEN)


def test_restart_with_missing_saved_replica_route_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    route = _full_route(tmp_path)
    started = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path, requested=True, query_replica_route=route
    )
    handoff = bootstrap.resolve_reddog_holoindex_owner_handoff()
    assert started.ready is True and handoff is not None
    first = _FakeSupervisor.instances[0]
    bootstrap._OWNER_REPLICA_ROUTE = None

    assert bootstrap.restart_reddog_holoindex_owner(
        failed_handoff=handoff
    ) is None
    assert first.stopped is True
    assert len(_FakeSupervisor.instances) == 1
    assert bootstrap.resolve_reddog_holoindex_owner_handoff() is None


def test_explicit_cleanup_stops_owner_and_clears_private_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
    )
    owner = _FakeSupervisor.instances[0]
    assert result.status == bootstrap.OWNER_STARTED
    assert bootstrap.resolve_reddog_holoindex_owner_handoff() is not None

    bootstrap.cleanup_reddog_holoindex_owner(restore_environment=True)

    assert owner.stopped is True
    assert bootstrap.resolve_reddog_holoindex_owner_handoff() is None
    assert SERVICE_URL_ENV not in os.environ
    assert SERVICE_TOKEN_ENV not in os.environ


def test_cleanup_expected_handoff_never_stops_replaced_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    bootstrap.ensure_reddog_holoindex_owner(repo_root=tmp_path, requested=True)
    owner = _FakeSupervisor.instances[0]
    handoff = bootstrap.resolve_reddog_holoindex_owner_handoff()
    assert handoff is not None

    rejected = bootstrap.cleanup_reddog_holoindex_owner(
        expected_handoff=(handoff[0], "different-private-token")
    )

    assert rejected is False
    assert owner.stopped is False
    assert bootstrap.resolve_reddog_holoindex_owner_handoff() == handoff
    assert bootstrap.cleanup_reddog_holoindex_owner(expected_handoff=handoff) is True
    assert owner.stopped is True


def test_supervisor_failure_returns_only_stable_error_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingSupervisor(_FakeSupervisor):
        def start(self, **_kwargs) -> "_FakeSupervisor":
            raise HoloQueryServiceSupervisorError(
                "HOLOINDEX_QUERY_SERVICE_STARTUP_TIMEOUT"
            )

    monkeypatch.setattr(
        bootstrap,
        "HoloQueryServiceSupervisor",
        FailingSupervisor,
    )
    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
    )

    assert result.ready is False
    assert result.status == bootstrap.OWNER_FAILED
    assert result.error == "HOLOINDEX_QUERY_SERVICE_STARTUP_TIMEOUT"
    assert SAFE_TOKEN not in repr(result)
    assert FailingSupervisor.instances[-1].stopped is True


def test_unexpected_bootstrap_failure_is_collapsed_to_stable_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bootstrap, "HoloQueryServiceSupervisor",
        Mock(side_effect=RuntimeError(f"do not expose {SAFE_TOKEN}")),
    )

    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
    )

    assert result.status == bootstrap.OWNER_FAILED
    assert result.error == bootstrap.BOOTSTRAP_FAILED_ERROR
    assert SAFE_TOKEN not in repr(result)


def test_cleanup_always_clears_private_handoff_for_compatibility_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    bootstrap.ensure_reddog_holoindex_owner(repo_root=tmp_path, requested=True)

    bootstrap.cleanup_reddog_holoindex_owner(restore_environment=False)

    assert bootstrap.resolve_reddog_holoindex_owner_handoff() is None
    assert SERVICE_URL_ENV not in os.environ
    assert SERVICE_TOKEN_ENV not in os.environ
