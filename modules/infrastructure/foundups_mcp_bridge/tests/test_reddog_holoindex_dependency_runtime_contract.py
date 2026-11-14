"""Fail-closed parser and limit tests for inert dependency runtimes."""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeContractError,
    DependencyRuntimeLimits,
    canonical_json_bytes,
    validate_inventory,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_copy import (
    copy_dependency_runtime_snapshot,
    plan_dependency_runtime_snapshot,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_descriptor import (
    DependencyRuntimeDescriptorError,
    _parse_canonical,
    verify_dependency_runtime_generation,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_materializer import (
    materialize_dependency_runtime,
)
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_dependency_runtime_materializer as runtime_materializer,
)


def _inventory(paths: tuple[str, ...] = ("a.py", "b.py")) -> dict[str, object]:
    return {
        "schema_version": "holoindex_dependency_payload_inventory.v1",
        "directories": [],
        "files": [
            {
                "path": path,
                "size": 1,
                "sha256": "sha256:" + (str(index) * 64),
                "role": "dependency_payload",
            }
            for index, path in enumerate(paths, start=1)
        ],
    }


def test_duplicate_json_key_is_rejected() -> None:
    raw = '{"schema_version":"x","schema_version":"x"}\n'
    with pytest.raises(
        DependencyRuntimeDescriptorError,
        match="DEPENDENCY_RUNTIME_JSON_DUPLICATE_KEY",
    ):
        _parse_canonical(raw, code="DEPENDENCY_RUNTIME_INVENTORY_INVALID")


@pytest.mark.parametrize(
    "raw",
    (
        '{"b":2,"a":1}\n',
        '{"a":1}',
        '{"a":',
    ),
)
def test_noncanonical_or_truncated_json_is_rejected(raw: str) -> None:
    with pytest.raises(DependencyRuntimeDescriptorError):
        _parse_canonical(raw, code="DEPENDENCY_RUNTIME_INVENTORY_INVALID")


def test_inventory_unknown_key_and_reordered_rows_are_rejected() -> None:
    unknown = _inventory()
    unknown["unexpected"] = True
    with pytest.raises(DependencyRuntimeContractError):
        validate_inventory(unknown)

    with pytest.raises(
        DependencyRuntimeContractError,
        match="DEPENDENCY_RUNTIME_INVENTORY_ORDER_INVALID",
    ):
        validate_inventory(_inventory(("b.py", "a.py")))


def test_direct_planner_validates_limits_before_touching_source(tmp_path: Path) -> None:
    invalid = DependencyRuntimeLimits(max_files=0)
    with pytest.raises(
        DependencyRuntimeContractError,
        match="DEPENDENCY_RUNTIME_LIMIT_INVALID",
    ):
        plan_dependency_runtime_snapshot(tmp_path / "missing", limits=invalid)


def test_direct_copier_validates_limits_before_store_proof(tmp_path: Path) -> None:
    invalid = DependencyRuntimeLimits(max_directories=0)
    with pytest.raises(
        DependencyRuntimeContractError,
        match="DEPENDENCY_RUNTIME_LIMIT_INVALID",
    ):
        copy_dependency_runtime_snapshot(
            tmp_path / "missing-source",
            tmp_path / "missing-destination",
            store_proof=None,  # type: ignore[arg-type]
            canonical_store=tmp_path / "missing-canonical",
            repo_roots=(tmp_path / "missing-repo",),
            limits=invalid,
        )


def test_public_invalid_limits_have_no_store_side_effect(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    with pytest.raises(
        runtime_materializer.DependencyRuntimeMaterializationError,
        match="DEPENDENCY_RUNTIME_LIMIT_INVALID",
    ):
        materialize_dependency_runtime(
            source_site_packages=tmp_path / "missing-source",
            runtime_store_root=runtime,
            canonical_store=tmp_path / "canonical",
            repo_roots=(tmp_path / "repo",),
            limits=DependencyRuntimeLimits(max_files=0),
        )
    assert not runtime.exists()


def _assert_public_serialization(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, runtime_roots,
) -> None:
    entered, release = threading.Event(), threading.Event()
    state = {"active": 0, "calls": 0, "peak": 0}
    state_lock = threading.Lock()
    failures: list[BaseException] = []

    def fake_materialize(**_kwargs):
        with state_lock:
            state["active"] += 1
            state["calls"] += 1
            state["peak"] = max(state["peak"], state["active"])
            entered.set()
        release.wait(timeout=5)
        with state_lock:
            state["active"] -= 1
        return object()

    monkeypatch.setattr(
        runtime_materializer, "_materialize_dependency_runtime_for_test",
        fake_materialize,
    )
    common = {
        "source_site_packages": tmp_path / "source",
        "canonical_store": tmp_path / "canonical",
        "repo_roots": (tmp_path / "repo",),
    }

    def invoke(runtime_root: Path | str) -> None:
        try:
            materialize_dependency_runtime(
                runtime_store_root=runtime_root, **common
            )
        except BaseException as exc:
            failures.append(exc)

    first = threading.Thread(target=invoke, args=(runtime_roots[0],))
    second = threading.Thread(target=invoke, args=(runtime_roots[1],))
    first.start()
    assert entered.wait(timeout=2)
    second.start()
    time.sleep(0.1)
    assert state == {"active": 1, "calls": 1, "peak": 1}
    release.set()
    first.join(timeout=2)
    second.join(timeout=2)
    assert not first.is_alive() and not second.is_alive()
    assert not failures
    assert state == {"active": 0, "calls": 2, "peak": 1}


def test_public_materialization_serializes_concurrent_builders(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime"
    _assert_public_serialization(monkeypatch, tmp_path, (runtime, runtime))


@pytest.mark.skipif(os.name != "nt", reason="Windows path alias contract")
def test_public_lock_converges_windows_extended_path_alias(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime"
    extended = "\\\\?\\" + str(runtime)
    _assert_public_serialization(monkeypatch, tmp_path, (runtime, extended))


def test_inventory_substitution_fails_full_generation_verification(
    tmp_path: Path,
) -> None:
    repo, canonical = tmp_path / "repo", tmp_path / "canonical"
    source, runtime = repo / "site-packages", tmp_path / "runtime"
    (repo / ".git").mkdir(parents=True)
    canonical.mkdir()
    source.mkdir()
    (source / "payload.py").write_text("VALUE = 1\n", encoding="ascii")
    result = materialize_dependency_runtime(
        source_site_packages=source,
        runtime_store_root=runtime,
        canonical_store=canonical,
        repo_roots=(repo,),
    )
    inventory_path = result.binding.generation_root / (
        "holoindex_dependency_payload_inventory.json"
    )
    import json

    inventory = json.loads(inventory_path.read_text("ascii"))
    inventory["files"][0]["sha256"] = "sha256:" + ("f" * 64)
    inventory_path.write_bytes(canonical_json_bytes(inventory))

    with pytest.raises(
        DependencyRuntimeDescriptorError,
        match="DEPENDENCY_RUNTIME_DESCRIPTOR_BINDING_INVALID",
    ):
        verify_dependency_runtime_generation(
            runtime_store_root=runtime,
            generation_root=result.binding.generation_root,
            expected_generation_id=result.binding.generation_id,
            canonical_store=canonical,
            repo_roots=(repo,),
        )
