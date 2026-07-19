"""Concurrency tests for governed RedDog runtime-artifact reads."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Event

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_execution_valve_use_time_authority as use_time,
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


@pytest.mark.parametrize(("attribute", "filename"), _USE_TIME_ARTIFACTS)
def test_use_time_reload_waits_for_each_exact_artifact_operation_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attribute: str,
    filename: str,
) -> None:
    repo, runtime = _roots(tmp_path)
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
    repo, runtime = _roots(tmp_path)
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
        replacement = profile_path.with_suffix(".replacement.json")
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
        payload["work_order_id"] = "attacker-mixed-generation"
        replacement.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        with runtime_operation_lock(str(profile_path) + ".operation"):
            os.replace(replacement, profile_path)
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
