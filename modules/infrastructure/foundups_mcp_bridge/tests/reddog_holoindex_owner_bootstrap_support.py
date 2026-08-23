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
    reddog_holoindex_owner_configured as configured,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service_supervisor import (
    SERVICE_TOKEN_ENV,
    SERVICE_URL_ENV,
    HoloQueryServiceSupervisorError,
)


SAFE_TOKEN = "s" * 64
SAFE_URL = "http://127.0.0.1:8127"
REPLICA_BINDING = ("descriptor", "generation", "replica", "path")
REAL_CONFIGURED_HEALTH = bootstrap._configured_owner_health_ready
REAL_ENSURE_OWNER = bootstrap.ensure_reddog_holoindex_owner
REAL_VERIFY_OWNER = bootstrap.verify_reddog_holoindex_owner_binding


class _FakeReplicaRoute:
    def __init__(
        self,
        root: Path,
        binding: tuple[str, str, str, str],
        *,
        fail_on_revalidation: int = 0,
    ) -> None:
        self.canonical_ssd_path = root / "canonical"
        self.replica_root_proof = SimpleNamespace(path=root / "replica")
        self.expected_replica_binding = binding
        self.fail_on_revalidation = fail_on_revalidation
        self.revalidations = 0

    def revalidate(self) -> object:
        self.revalidations += 1
        if self.revalidations == self.fail_on_revalidation:
            raise ValueError("QUERY_REPLICA_BINDING_CHANGED")
        return object()

    def __eq__(self, other: object) -> bool:
        return bool(
            isinstance(other, _FakeReplicaRoute)
            and self.canonical_ssd_path == other.canonical_ssd_path
            and self.replica_root_proof.path == other.replica_root_proof.path
            and self.expected_replica_binding == other.expected_replica_binding
        )


def _full_route(root: Path) -> _FakeReplicaRoute:
    return _FakeReplicaRoute(root, REPLICA_BINDING)


class _FakeSupervisor:
    instances: list["_FakeSupervisor"] = []

    def __init__(
        self,
        *,
        repo_root: Path | str,
        ssd_path: Path | str,
        runtime_root: Path | str | None = None,
        canonical_ssd_path: Path | str | None = None,
        query_replica_root: Path | str | None = None,
        replica_capability_verifier=None,
        startup_timeout_seconds: float = 300.0,
        probe_timeout_seconds: float = 30.0,
        shutdown_timeout_seconds: float = 3.0,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.runtime_root = Path(runtime_root or repo_root)
        self.ssd_path = Path(ssd_path)
        self.canonical_ssd_path = Path(canonical_ssd_path or ssd_path)
        self.query_replica_root = (
            Path(query_replica_root) if query_replica_root is not None else None
        )
        self.replica_capability_verifier = replica_capability_verifier
        self.startup_timeout_seconds = startup_timeout_seconds
        self.probe_timeout_seconds = probe_timeout_seconds
        self.shutdown_timeout_seconds = shutdown_timeout_seconds
        self.lifecycle_events: list[str] = []
        self.started = False
        self.stopped = False
        self.verified_binding = ("", "", "", "")
        self.verified_replica_binding = ("", "", "", "")
        self.__class__.instances.append(self)

    @property
    def is_ready(self) -> bool:
        return self.started and not self.stopped

    def start(
        self,
        *,
        expected_repo_head_sha: str = "",
        expected_repo_root_digest: str = "",
        expected_generation_id: str = "",
        expected_receipt_digest: str = "",
        expected_replica_binding: tuple[str, str, str, str] = ("", "", "", ""),
    ) -> "_FakeSupervisor":
        if self.replica_capability_verifier is not None:
            self.replica_capability_verifier()
        self.lifecycle_events.append("process")
        if self.replica_capability_verifier is not None:
            self.replica_capability_verifier()
        self.lifecycle_events.append("health")
        self.started = True
        self.stopped = False
        self.verified_binding = (
            expected_repo_head_sha or ("a" * 40),
            expected_repo_root_digest or ("sha256:" + ("d" * 64)),
            expected_generation_id or ("sha256:" + ("b" * 64)),
            expected_receipt_digest or ("sha256:" + ("c" * 64)),
        )
        self.verified_replica_binding = expected_replica_binding
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
        self.verified_binding = ("", "", "", "")
        self.verified_replica_binding = ("", "", "", "")


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
    def routed_ensure(**kwargs):
        if kwargs.get("requested") is True:
            kwargs.setdefault(
                "query_replica_route", _full_route(Path(kwargs["repo_root"]))
            )
        return REAL_ENSURE_OWNER(**kwargs)

    def routed_verify(**kwargs):
        kwargs.setdefault(
            "query_replica_route", _full_route(Path(kwargs["repo_root"]))
        )
        return REAL_VERIFY_OWNER(**kwargs)

    monkeypatch.setattr(bootstrap, "ensure_reddog_holoindex_owner", routed_ensure)
    monkeypatch.setattr(bootstrap, "verify_reddog_holoindex_owner_binding", routed_verify)
    yield
    bootstrap.cleanup_reddog_holoindex_owner(restore_environment=True)
    os.environ.pop(SERVICE_URL_ENV, None)
    os.environ.pop(SERVICE_TOKEN_ENV, None)
