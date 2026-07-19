"""Concurrency tests for governed RedDog runtime-artifact reads."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Event
from types import ModuleType

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_authoritative_work_state_refresh_runtime as work_state_supply,
)
from modules.communication.moltbot_bridge.src import (
    reddog_authority_profile_source_artifact_supply as profile_source_supply,
)
from modules.communication.moltbot_bridge.src import (
    reddog_authority_runtime_resolver_artifact_supply as resolver_artifact_supply,
)
from modules.communication.moltbot_bridge.src import (
    reddog_execution_valve_environment_supply as valve_environment_supply,
)
from modules.communication.moltbot_bridge.src import (
    reddog_execution_valve_use_time_authority as use_time,
)
from modules.communication.moltbot_bridge.src import (
    reddog_github_principal_permission_snapshot_supply as github_artifact_supply,
)
from modules.communication.moltbot_bridge.src import (
    reddog_main_architect_fix_promotion_bootstrap as promoted_profile_supply,
)
from modules.communication.moltbot_bridge.src import (
    reddog_main_resident_queue_runtime_dependency_bundle as dependency_bundle,
)
from modules.communication.moltbot_bridge.src.reddog_execution_valve_use_time_authority import (
    GovernedValveUseTimeAuthorityResolver,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_live_canary_test_support import (
    _roots,
)
from modules.communication.moltbot_bridge.tests.test_reddog_main_resident_queue_runtime_dependency_bundle import (
    NOW,
    _principals,
    _repo,
    _snapshots,
    _write_json,
)


_USE_TIME_ARTIFACTS = (
    ("work_state_path", "authoritative_work_state.json"),
    ("authority_profile_path", "authority_profile.json"),
    ("permission_snapshots_path", "permission_snapshots.json"),
    ("principal_authority_records_path", "principal_authority_records.json"),
    ("valve_environment_path", "execution_valve_env.json"),
)

_PRODUCTION_WRITERS = (
    ("work_state_store", work_state_supply, "authoritative_work_state.json", "store"),
    ("profile_source", profile_source_supply, "authority_profile.json", "helper"),
    ("profile_promoted", promoted_profile_supply, "authority_profile.json", "helper"),
    ("github_permissions", github_artifact_supply, "permission_snapshots.json", "helper"),
    ("github_principals", github_artifact_supply, "principal_authority_records.json", "helper"),
    ("resolver_permissions", resolver_artifact_supply, "permission_snapshots.json", "helper"),
    ("resolver_principals", resolver_artifact_supply, "principal_authority_records.json", "helper"),
    ("valve_environment", valve_environment_supply, "execution_valve_env.json", "helper"),
)


def _resolver(repo: Path, runtime: Path) -> GovernedValveUseTimeAuthorityResolver:
    return GovernedValveUseTimeAuthorityResolver(
        repo_root=repo,
        work_state_path=runtime / "authoritative_work_state.json",
        authority_profile_path=runtime / "authority_profile.json",
        permission_snapshots_path=runtime / "permission_snapshots.json",
        principal_authority_records_path=runtime / "principal_authority_records.json",
        valve_environment_path=runtime / "execution_valve_env.json",
        runtime_allowed_root=runtime,
        signature_verifier=object(),
        principal_key_resolver=object(),
        nonce_store=object(),
        snapshot_resolver=object(),
        revocation_oracle=object(),
        now_epoch=1_784_006_400,
        required_valve_state="VALVE_OPEN_WORKTREE_CREATE",
        trusted_now_epoch=lambda: 1_784_006_400,
    )


def _invoke_production_writer(
    module: ModuleType,
    writer_kind: str,
    target: Path,
    payload: dict[str, str],
) -> None:
    if writer_kind == "store":
        module.AtomicJsonAuthoritativeWorkStateStore(target).commit(
            payload,
            expected_revision=None,
        )
        return
    module._write_json_atomic(target, payload)


@pytest.mark.parametrize(
    ("case", "module", "filename", "writer_kind"),
    _PRODUCTION_WRITERS,
    ids=[case[0] for case in _PRODUCTION_WRITERS],
)
def test_production_writer_cannot_replace_during_reader_operation_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    module: ModuleType,
    filename: str,
    writer_kind: str,
) -> None:
    target = tmp_path / case / filename
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps({"generation": "before", "revision": None}),
        encoding="utf-8",
    )
    attempted = Event()
    lock_identity = str(target) + ".operation"

    @contextmanager
    def observed_lock(identity: Path | str):
        if str(identity) == lock_identity:
            attempted.set()
        with runtime_operation_lock(identity):
            yield

    monkeypatch.setattr(module, "runtime_operation_lock", observed_lock)
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        with runtime_operation_lock(lock_identity):
            future = executor.submit(
                _invoke_production_writer,
                module,
                writer_kind,
                target,
                {"generation": "after"},
            )
            assert attempted.wait(timeout=2), case
            assert future.done() is False
            assert json.loads(target.read_text(encoding="utf-8"))["generation"] == "before"
        future.result(timeout=5)
    finally:
        executor.shutdown(wait=True)

    assert json.loads(target.read_text(encoding="utf-8"))["generation"] == "after"


@pytest.mark.parametrize(("attribute", "filename"), _USE_TIME_ARTIFACTS)
def test_use_time_reload_waits_for_each_exact_artifact_operation_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attribute: str,
    filename: str,
) -> None:
    repo, runtime = _roots(tmp_path, canonical_artifacts=True)
    resolver = _resolver(repo, runtime)
    target = Path(getattr(resolver, attribute))
    attempted = Event()
    lock_identity = str(target) + ".operation"

    @contextmanager
    def observed_lock(identity: Path | str):
        if str(identity) == lock_identity:
            attempted.set()
        with runtime_operation_lock(identity):
            yield

    monkeypatch.setattr(use_time, "runtime_operation_lock", observed_lock)
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        with runtime_operation_lock(lock_identity):
            future = executor.submit(use_time._read_runtime_artifacts, resolver)
            assert attempted.wait(timeout=2), filename
            assert future.done() is False
        payloads, reasons = future.result(timeout=5)
    finally:
        executor.shutdown(wait=True)

    assert reasons == []
    assert set(payloads) == {name.removesuffix("_path") for name, _ in _USE_TIME_ARTIFACTS}


def test_use_time_reload_replacement_fails_closed_without_mixed_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, runtime = _roots(tmp_path, canonical_artifacts=True)
    resolver = _resolver(repo, runtime)
    profile_path = Path(resolver.authority_profile_path)
    first_read = Event()
    replacement_done = Event()
    original_read = use_time._read_json_no_follow
    observed_profile_reads = 0

    def observed_read(repo_root: Path, path: Path, allowed_root: Path):
        nonlocal observed_profile_reads
        payload, reason = original_read(repo_root, path, allowed_root)
        if path == profile_path and observed_profile_reads == 0:
            observed_profile_reads += 1
            first_read.set()
            assert replacement_done.wait(timeout=5)
        return payload, reason

    def replace_profile() -> None:
        assert first_read.wait(timeout=5)
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
        payload["work_order_id"] = "attacker-mixed-generation"
        profile_source_supply._write_json_atomic(profile_path, payload)
        replacement_done.set()

    monkeypatch.setattr(use_time, "_read_json_no_follow", observed_read)
    with ThreadPoolExecutor(max_workers=1) as executor:
        writer = executor.submit(replace_profile)
        payloads, reasons = use_time._read_runtime_artifacts(resolver)
        writer.result(timeout=5)

    assert payloads == {}
    assert reasons == [
        "canonical_use_time_artifact_snapshot_changed:authority_profile"
    ]


@pytest.mark.parametrize("filename", ("snapshots.json", "principals.json"))
def test_dependency_bundle_descriptor_read_waits_for_exact_operation_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    snapshot_path = _write_json(tmp_path, "snapshots.json", _snapshots())
    principal_path = _write_json(tmp_path, "principals.json", _principals())
    target = runtime / filename
    lock_identity = str(target) + ".operation"
    attempted = Event()

    @contextmanager
    def observed_lock(identity: Path | str):
        if str(identity) == lock_identity:
            attempted.set()
        with runtime_operation_lock(identity):
            yield

    monkeypatch.setattr(dependency_bundle, "runtime_operation_lock", observed_lock)
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        with runtime_operation_lock(lock_identity):
            future = executor.submit(
                dependency_bundle.load_reddog_main_resident_queue_runtime_dependency_bundle,
                repo_root=repo,
                runtime_allowed_root=runtime,
                authority_state_path=runtime / "authority-state.json",
                permission_snapshots_path=snapshot_path,
                principal_authority_records_path=principal_path,
                now_epoch=NOW,
            )
            assert attempted.wait(timeout=2), filename
            assert future.done() is False
        result = future.result(timeout=5)
    finally:
        executor.shutdown(wait=True)

    assert result.accepted is True, result.rejection_reasons
