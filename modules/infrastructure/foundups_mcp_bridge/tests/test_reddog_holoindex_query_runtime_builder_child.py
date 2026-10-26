"""Falsifiers for one held-executable RedDog builder child."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

import pytest

from holo_index.repository_state import repository_root_digest
from modules.infrastructure.foundups_mcp_bridge.src.reddog_bounded_child_process import (
    BoundedChildResult,
    CHILD_STDOUT_MAX_BYTES,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_process_image import (
    ProcessExecutableCapability,
    ProcessExecutableProof,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_child import (
    BuilderProcessChildDependencies,
    QueryRuntimeBuilderChildError,
    _run_builder_process_once_for_test,
    run_builder_process_once,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_child_contract import (
    BuilderProcessChildEvidence,
    CHILD_OUTPUT_SCHEMA_VERSION,
    EVIDENCE_SCHEMA_VERSION,
    _FALSE_EVIDENCE_FIELDS,
    child_process_output_bytes,
    parse_child_process_output,
    validate_builder_process_child_evidence,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_dependency_composition_contract import (
    BuilderDependencyCompositionBinding,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging_source_contract import (
    BuilderPackagingSourceBinding,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging_wheel import (
    PACKAGING_26_WHEEL_FILENAME,
    PACKAGING_26_WHEEL_SHA256,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_runtime_composition import (
    compose_pinned_builder_runtime,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_runtime_composition_contract import (
    BuilderRuntimeCompositionBinding,
    build_builder_runtime_composition_binding,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_runtime_composition_materializer import (
    materialize_runtime_composition,
)
from modules.infrastructure.foundups_mcp_bridge.tests.reddog_holoindex_runtime_composition_test_support import (
    BASE_LIMITS,
    DEPENDENCY_LIMITS,
    materialized_runtime_components,
)


def _digest(character: str) -> str:
    return "sha256:" + character * 64


@pytest.fixture
def o_root():
    parent = Path("O:/tmp").resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reddog-builder-child-", dir=parent) as raw:
        yield Path(raw).resolve()


def _builder_runtime(root: Path) -> BuilderRuntimeCompositionBinding:
    fixture = materialized_runtime_components(root)
    runtime = materialize_runtime_composition(
        composition_store_root=fixture.composition_store,
        base_runtime_store_root=fixture.base_store,
        base_generation_root=fixture.base.binding.generation_root,
        dependency_runtime_store_root=fixture.dependency_store,
        dependency_generation_root=fixture.dependency.binding.generation_root,
        canonical_store=fixture.canonical,
        repo_roots=(fixture.repo,),
        base_limits=BASE_LIMITS,
        dependency_limits=DEPENDENCY_LIMITS,
    ).binding
    source_root = root / "builder-source" / "source-generation"
    source = BuilderPackagingSourceBinding(
        generation_root=source_root,
        site_packages_root=source_root / "site-packages",
        wheel_path=source_root / "packaging.whl",
        descriptor_path=source_root / "descriptor.json",
        descriptor_digest=_digest("1"),
        generation_id=_digest("2"),
        inventory_digest=_digest("3"),
        wheel_sha256=_digest("4"),
        member_set_digest=_digest("5"),
        dependency_tree_digest=runtime.dependency_runtime.generation_id,
        member_count=runtime.dependency_runtime.file_count,
        directory_count=runtime.dependency_runtime.directory_count,
        expanded_bytes=runtime.dependency_runtime.total_bytes,
        reviewed_pin_match=True,
        source_lease_held_through_publication=False,
        source_lease_held_through_current_verification=True,
    )
    builder = BuilderDependencyCompositionBinding(
        source=source, dependency=runtime.dependency_runtime,
    )
    return build_builder_runtime_composition_binding(
        builder_dependency=builder, runtime_composition=runtime,
    )


def _process_authority(binding: BuilderRuntimeCompositionBinding) -> dict[str, object]:
    runtime = binding.runtime_composition
    return {
        "runtime_composition_generation_id": runtime.generation_id,
        "runtime_composition_descriptor_digest": runtime.descriptor_digest,
        "builder_source_root_digest": repository_root_digest(
            runtime.base_runtime.generation_root.parents[1] / "repo"
        ),
        "dependency_runtime_inventory_digest": (
            runtime.dependency_runtime.inventory_digest
        ),
        "process_image_content_digest": runtime.interpreter_content_digest,
        "process_image_size": runtime.interpreter_size,
        "launch_state_digest": _digest("6"),
        "sys_path_digest": _digest("7"),
        "actual_process_image_verified": True,
        "isolation_verified": True,
        "native_loaded_image_closure_verified": False,
    }


def _repo_root(binding: BuilderRuntimeCompositionBinding) -> Path:
    return binding.runtime_composition.base_runtime.generation_root.parents[1] / "repo"


@dataclass
class _Recorder:
    commands: list[tuple[tuple[str, ...], dict[str, object]]]


def _dependencies(
    binding: BuilderRuntimeCompositionBinding,
    recorder: _Recorder,
    *, output: bytes | None = None,
    result: BoundedChildResult | None = None,
) -> BuilderProcessChildDependencies:
    runtime = binding.runtime_composition
    proof = ProcessExecutableProof(
        runtime.interpreter_path,
        (1, 2, runtime.interpreter_size, 4, 5, 1),
    )

    @contextmanager
    def holder(_proof):
        yield ProcessExecutableCapability(7, runtime.interpreter_path, ())

    authority = _process_authority(binding)
    payload = output if output is not None else child_process_output_bytes(authority)

    def runner(command, **kwargs):
        recorder.commands.append((tuple(str(value) for value in command), kwargs))
        return result if result is not None else BoundedChildResult(0, payload)

    return BuilderProcessChildDependencies(
        composition_verifier=lambda **_kwargs: runtime,
        executable_prover=lambda _path: proof,
        executable_holder=holder,
        child_runner=runner,
    )


def _run_unit(
    root: Path, *, output: bytes | None = None,
    result: BoundedChildResult | None = None,
):
    binding = _builder_runtime(root)
    repo = _repo_root(binding)
    temp_root = root / "child-temp"
    temp_root.mkdir()
    recorder = _Recorder([])
    evidence = _run_builder_process_once_for_test(
        builder_runtime=binding,
        repo_root=repo,
        canonical_store=root / "canonical",
        temp_root=temp_root,
        timeout_seconds=10,
        dependencies=_dependencies(
            binding, recorder, output=output, result=result,
        ),
    )
    return binding, recorder, evidence


def test_child_output_is_one_canonical_path_free_line(o_root: Path) -> None:
    binding = _builder_runtime(o_root)
    raw = child_process_output_bytes(_process_authority(binding))
    value = parse_child_process_output(raw)

    assert raw.endswith(b"\n") and raw.count(b"\n") == 1
    assert value["schema_version"] == CHILD_OUTPUT_SCHEMA_VERSION
    assert value["status"] == "OBSERVED_PROCESS_AUTHORITY"
    assert "O:" not in raw.decode("ascii")


def test_parent_runs_one_held_isolated_child_with_closed_environment(o_root: Path) -> None:
    binding, recorder, evidence = _run_unit(o_root)
    command, kwargs = recorder.commands[0]
    public = evidence.public_binding

    assert command[0] == str(binding.runtime_composition.interpreter_path)
    assert command[1:7] == ("-I", "-S", "-B", "-E", "-s", "-c")
    assert len(recorder.commands) == 1
    assert kwargs["env"] == {
        "TEMP": str(o_root / "child-temp"),
        "TMP": str(o_root / "child-temp"),
    }
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["stdout"] is subprocess.PIPE
    assert kwargs["stderr"] is subprocess.DEVNULL
    assert kwargs["shell"] is False
    assert public["schema_version"] == EVIDENCE_SCHEMA_VERSION
    assert public["held_executable_launch_verified"] is True
    assert public["runtime_composition_stable_around_child_verified"] is True
    assert all(public[name] is False for name in _FALSE_EVIDENCE_FIELDS)
    assert validate_builder_process_child_evidence(public) == public


def test_evidence_wrapper_rejects_direct_accidental_construction() -> None:
    with pytest.raises(Exception):
        BuilderProcessChildEvidence({})


@pytest.mark.parametrize(
    "raw",
    (
        b"{}\n",
        b'{"schema_version":"wrong"}\n',
        b'{"a":1,"a":1}\n',
        b"{}\n{}\n",
        b"\xef\xbb\xbf{}\n",
    ),
)
def test_child_output_parser_rejects_noncanonical_or_ambiguous_bytes(
    raw: bytes,
) -> None:
    with pytest.raises(Exception):
        parse_child_process_output(raw)


def test_child_output_parser_rejects_direct_oversized_input() -> None:
    with pytest.raises(Exception):
        parse_child_process_output(b"x" * CHILD_STDOUT_MAX_BYTES + b"\n")


def test_parent_rejects_wrong_child_composition_identity(o_root: Path) -> None:
    binding = _builder_runtime(o_root)
    authority = _process_authority(binding)
    authority["runtime_composition_generation_id"] = _digest("f")
    raw = child_process_output_bytes(authority)
    with pytest.raises(
        QueryRuntimeBuilderChildError,
        match="QUERY_BUILDER_CHILD_PROCESS_IDENTITY_MISMATCH",
    ):
        _run_unit(o_root / "second", output=raw)


@pytest.mark.parametrize(
    "result",
    (
        BoundedChildResult(0, b"{}\n", output_oversized=True),
        BoundedChildResult(0, b"{}\n", output_read_failed=True),
    ),
)
def test_parent_rejects_untrustworthy_bounded_output(
    o_root: Path, result: BoundedChildResult,
) -> None:
    with pytest.raises(
        QueryRuntimeBuilderChildError,
        match="QUERY_BUILDER_CHILD_EXECUTION_FAILED",
    ):
        _run_unit(o_root, result=result)


def test_parent_maps_child_timeout_to_stable_error(o_root: Path) -> None:
    binding = _builder_runtime(o_root)
    temp_root = o_root / "external-temp"
    temp_root.mkdir()

    def timeout_runner(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("child", 1)

    dependencies = replace(
        _dependencies(binding, _Recorder([])),
        child_runner=timeout_runner,
    )
    with pytest.raises(
        QueryRuntimeBuilderChildError, match="QUERY_BUILDER_CHILD_TIMEOUT",
    ):
        _run_builder_process_once_for_test(
            builder_runtime=binding, repo_root=_repo_root(binding),
            canonical_store=o_root / "canonical", temp_root=temp_root,
            timeout_seconds=10, dependencies=dependencies,
        )


def test_parent_rejects_forged_builder_runtime_binding(o_root: Path) -> None:
    binding = _builder_runtime(o_root)
    forged_runtime = replace(
        binding.runtime_composition,
        site_packages_root=o_root / "ambient-site-packages",
    )
    forged = replace(binding, runtime_composition=forged_runtime)
    temp_root = o_root / "child-temp"
    temp_root.mkdir()
    with pytest.raises(
        QueryRuntimeBuilderChildError,
        match="QUERY_BUILDER_CHILD_RUNTIME_INVALID",
    ):
        _run_builder_process_once_for_test(
            builder_runtime=forged,
            repo_root=_repo_root(binding),
            canonical_store=o_root / "canonical",
            temp_root=temp_root,
            timeout_seconds=10,
            dependencies=_dependencies(binding, _Recorder([])),
        )


@pytest.mark.parametrize(
    "protected_name",
    (
        "canonical", "composition_store", "composition", "base_store",
        "base", "dependency_store", "dependency", "repository",
    ),
)
def test_parent_rejects_temp_root_overlapping_protected_roots(
    o_root: Path, protected_name: str,
) -> None:
    binding = _builder_runtime(o_root)
    runtime = binding.runtime_composition
    protected = {
        "canonical": o_root / "canonical",
        "composition_store": runtime.generation_root.parent,
        "composition": runtime.generation_root,
        "base_store": runtime.base_runtime.generation_root.parent,
        "base": runtime.base_runtime.generation_root,
        "dependency_store": runtime.dependency_runtime.generation_root.parent,
        "dependency": runtime.dependency_runtime.generation_root,
        "repository": _repo_root(binding),
    }[protected_name]
    with pytest.raises(
        QueryRuntimeBuilderChildError,
        match="QUERY_BUILDER_CHILD_RUNTIME_PATH_INVALID",
    ):
        _run_builder_process_once_for_test(
            builder_runtime=binding,
            repo_root=_repo_root(binding),
            canonical_store=o_root / "canonical",
            temp_root=protected,
            timeout_seconds=10,
            dependencies=_dependencies(binding, _Recorder([])),
        )


def test_parent_rejects_composition_mutation_after_child(o_root: Path) -> None:
    binding = _builder_runtime(o_root)
    runtime = binding.runtime_composition
    calls = 0
    temp_root = o_root / "external-temp"
    temp_root.mkdir()

    def verifier(**_kwargs):
        nonlocal calls
        calls += 1
        return runtime if calls == 1 else replace(
            runtime, descriptor_digest=_digest("f"),
        )

    dependencies = replace(
        _dependencies(binding, _Recorder([])), composition_verifier=verifier,
    )
    with pytest.raises(
        QueryRuntimeBuilderChildError,
        match="QUERY_BUILDER_CHILD_COMPOSITION_MUTATED",
    ):
        _run_builder_process_once_for_test(
            builder_runtime=binding, repo_root=_repo_root(binding),
            canonical_store=o_root / "canonical", temp_root=temp_root,
            timeout_seconds=10, dependencies=dependencies,
        )


@pytest.mark.integration
@pytest.mark.skipif(os.name != "nt", reason="qualified Windows O: runtime")
def test_public_child_executes_the_qualified_o_runtime(o_root: Path) -> None:
    repo = Path("O:/Foundups-Agent").resolve()
    wheel_dir = (
        Path("O:/RedDog-Builder-Artifacts/packaging/26.0")
        / PACKAGING_26_WHEEL_SHA256
    )
    wheel = wheel_dir / PACKAGING_26_WHEEL_FILENAME
    base_store = Path("O:/RedDog-Runtime/base-runtimes")
    base_generation = base_store / (
        "8b9c41d5d9bf13b9588813333bc5383b19eb1120a078f3dd71a91cc6e69a52e8"
    )
    if not wheel.is_file() or not base_generation.is_dir():
        pytest.skip("qualified reviewed O: artifacts are not provisioned")
    canonical = o_root / "canonical"
    canonical.mkdir()
    temp_root = o_root / "child-temp"
    temp_root.mkdir()
    result = compose_pinned_builder_runtime(
        wheel_path=wheel,
        wheel_store_root=wheel_dir,
        source_store_root=o_root / "builder-source",
        dependency_runtime_store_root=o_root / "builder-dependency",
        base_runtime_store_root=base_store,
        base_generation_root=base_generation,
        composition_store_root=o_root / "builder-composition",
        canonical_store=canonical,
        repo_roots=(repo,),
    )
    descriptor = result.binding.runtime_composition.descriptor_path
    before = hashlib.sha256(descriptor.read_bytes()).hexdigest()

    evidence = run_builder_process_once(
        builder_runtime=result.binding,
        repo_root=repo,
        canonical_store=canonical,
        temp_root=temp_root,
        timeout_seconds=120,
    )

    assert evidence.public_binding["held_executable_launch_verified"] is True
    assert evidence.public_binding["process_authority"][
        "actual_process_image_verified"
    ] is True
    assert hashlib.sha256(descriptor.read_bytes()).hexdigest() == before
