"""WSP-focused tests for RedDog's host-owned HoloIndex bootstrap."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_owner_bootstrap as bootstrap,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service_supervisor import (
    SERVICE_TOKEN_ENV,
    SERVICE_URL_ENV,
    HoloQueryServiceSupervisorError,
)


SAFE_TOKEN = "s" * 64
SAFE_URL = "http://127.0.0.1:8127"
REAL_CONFIGURED_HEALTH = bootstrap._configured_owner_health_ready


class _FakeSupervisor:
    instances: list["_FakeSupervisor"] = []

    def __init__(self, *, repo_root: Path | str, ssd_path: Path | str) -> None:
        self.repo_root = Path(repo_root)
        self.ssd_path = Path(ssd_path)
        self.started = False
        self.stopped = False
        self.__class__.instances.append(self)

    @property
    def is_ready(self) -> bool:
        return self.started and not self.stopped

    def start(self) -> "_FakeSupervisor":
        self.started = True
        return self

    def environment_for_child(
        self,
        _base_environment: dict[str, str],
    ) -> dict[str, str]:
        if not self.is_ready:
            raise HoloQueryServiceSupervisorError(
                "HOLOINDEX_QUERY_SERVICE_NOT_READY"
            )
        return {
            SERVICE_URL_ENV: SAFE_URL,
            SERVICE_TOKEN_ENV: SAFE_TOKEN,
        }

    def stop(self) -> None:
        self.stopped = True


@pytest.fixture(autouse=True)
def _clean_owner_state(monkeypatch: pytest.MonkeyPatch):
    bootstrap.cleanup_reddog_holoindex_owner(restore_environment=True)
    _FakeSupervisor.instances.clear()
    monkeypatch.setattr(
        bootstrap,
        "_configured_owner_health_ready",
        lambda **_kwargs: True,
    )
    for name in (
        bootstrap.AUTO_START_ENV,
        SERVICE_TOKEN_ENV,
        SERVICE_URL_ENV,
    ):
        monkeypatch.delenv(name, raising=False)
    yield
    bootstrap.cleanup_reddog_holoindex_owner(restore_environment=True)
    os.environ.pop(SERVICE_URL_ENV, None)
    os.environ.pop(SERVICE_TOKEN_ENV, None)


def test_not_requested_has_no_process_or_environment_side_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bootstrap,
        "HoloQueryServiceSupervisor",
        Mock(side_effect=AssertionError("must not start")),
    )

    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=False,
    )

    assert result.status == bootstrap.OWNER_NOT_REQUESTED
    assert result.ready is False
    assert SERVICE_URL_ENV not in os.environ
    assert SERVICE_TOKEN_ENV not in os.environ


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8127",
        "http://127.0.0.1",
        "http://127.0.0.1:8127/holoindex/v1/query",
        "http://127.0.0.1:8127/holoindex/v1/query/",
    ],
)
def test_explicit_loopback_service_bypasses_auto_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    url: str,
) -> None:
    monkeypatch.setenv(SERVICE_URL_ENV, url)
    monkeypatch.setenv(SERVICE_TOKEN_ENV, SAFE_TOKEN)
    constructor = Mock(side_effect=AssertionError("configured service must win"))
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", constructor)

    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
    )

    assert result.ready is True
    assert result.status == bootstrap.OWNER_CONFIGURED
    assert bootstrap.resolve_reddog_holoindex_owner_handoff() is None
    constructor.assert_not_called()


def test_configured_health_wrapper_uses_authenticated_loopback_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = Mock(return_value=True)
    monkeypatch.setattr(bootstrap, "_authenticated_health_probe", probe)

    assert REAL_CONFIGURED_HEALTH(
        service_url="http://127.0.0.1:9127/holoindex/v1/query",
        token=SAFE_TOKEN,
    )

    probe.assert_called_once_with(
        host="127.0.0.1",
        port=9127,
        token=SAFE_TOKEN,
        timeout_seconds=bootstrap.CONFIGURED_HEALTH_TIMEOUT_SECONDS,
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
        expected_generation_id="",
        expected_receipt_digest="",
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
    store = tmp_path / "canonical-holo-store"
    resolver = Mock(return_value=store)
    monkeypatch.setattr(bootstrap, "resolve_holoindex_ssd_path", resolver)
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    monkeypatch.setenv("UNRELATED_VALUE", "preserved")

    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
    )

    assert result.ready is True
    assert result.status == bootstrap.OWNER_STARTED
    assert len(_FakeSupervisor.instances) == 1
    assert _FakeSupervisor.instances[0].ssd_path == store
    resolver.assert_called_once_with(environ=os.environ)
    assert SERVICE_URL_ENV not in os.environ
    assert SERVICE_TOKEN_ENV not in os.environ
    assert bootstrap.resolve_reddog_holoindex_owner_handoff() == (
        SAFE_URL,
        SAFE_TOKEN,
    )
    assert os.environ["UNRELATED_VALUE"] == "preserved"
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
    assert health.call_count == 1


def test_explicit_private_restart_replaces_failed_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    started = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
    )
    first = _FakeSupervisor.instances[0]
    failed_handoff = bootstrap.resolve_reddog_holoindex_owner_handoff()

    restarted = bootstrap.restart_reddog_holoindex_owner(
        failed_handoff=failed_handoff,
    )

    assert started.ready is True
    assert first.stopped is True
    assert len(_FakeSupervisor.instances) == 2
    assert restarted == (SAFE_URL, SAFE_TOKEN)


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


def test_supervisor_failure_returns_only_stable_error_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingSupervisor(_FakeSupervisor):
        def start(self) -> "_FakeSupervisor":
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
        bootstrap,
        "resolve_holoindex_ssd_path",
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
