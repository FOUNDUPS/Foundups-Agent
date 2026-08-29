"""Falsification tests for sequential builder/dependency composition."""

from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeBinding,
    DependencyRuntimeLimits,
    DependencyRuntimeMaterializationResult,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_copy import (
    plan_dependency_runtime_snapshot,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_materializer import (
    materialize_dependency_runtime,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_dependency_composition import (
    _CompositionDependencies,
    _compose_builder_dependency_runtime_for_test,
    compose_pinned_builder_dependency_runtime,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_dependency_composition_contract import (
    BuilderDependencyCompositionError,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging_source_contract import (
    BuilderPackagingSourceBinding,
    BuilderPackagingSourceMaterializationResult,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging_wheel import (
    PACKAGING_26_WHEEL_FILENAME,
    PACKAGING_26_WHEEL_SHA256,
)


def _digest(character: str) -> str:
    return "sha256:" + character * 64


@pytest.fixture
def o_root():
    parent = Path("O:/tmp").resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reddog-composition-", dir=parent) as raw:
        root = Path(raw).resolve()
        assert root.parent == parent and root.drive.upper() == "O:"
        yield root


def _source_binding(
    root: Path, *, tree: str | None = None, generation: str | None = None,
    published: bool = False, current: bool = True,
) -> BuilderPackagingSourceBinding:
    tree = tree or _digest("a")
    generation = generation or _digest("b")
    generation_root = root / "source" / generation.removeprefix("sha256:")
    site_packages = generation_root / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    return BuilderPackagingSourceBinding(
        generation_root=generation_root, site_packages_root=site_packages,
        wheel_path=generation_root / "wheel" / "packaging.whl",
        descriptor_path=generation_root / "builder-packaging-source.json",
        descriptor_digest=_digest("1"), generation_id=generation,
        inventory_digest=_digest("2"), wheel_sha256=_digest("3"),
        member_set_digest=_digest("4"), dependency_tree_digest=tree,
        member_count=2, directory_count=2, expanded_bytes=20,
        reviewed_pin_match=True,
        source_lease_held_through_publication=published,
        source_lease_held_through_current_verification=current,
    )


def _dependency_binding(
    root: Path, *, tree: str = "a",
) -> DependencyRuntimeBinding:
    generation = root / "runtime" / tree.removeprefix("sha256:")
    return DependencyRuntimeBinding(
        generation_root=generation,
        site_packages_root=generation / "site-packages",
        descriptor_path=generation / "dependency-runtime.json",
        descriptor_digest=_digest("5"), generation_id=tree,
        inventory_digest=_digest("6"), dependency_tree_digest=tree,
        file_count=2, directory_count=2, total_bytes=20,
        artifact_bytes_verified_at_publication=True,
        write_denial_verified=False, activation_eligible=False,
    )


def _source_result(
    binding: BuilderPackagingSourceBinding, reused: bool,
) -> BuilderPackagingSourceMaterializationResult:
    return BuilderPackagingSourceMaterializationResult(binding, reused)


def _dependency_result(
    binding: DependencyRuntimeBinding, reused: bool = False,
) -> DependencyRuntimeMaterializationResult:
    return DependencyRuntimeMaterializationResult(binding, reused)


def _arguments(root: Path, dependencies: _CompositionDependencies):
    return _compose_builder_dependency_runtime_for_test(
        wheel_path=root / "wheel" / "packaging.whl",
        wheel_store_root=root / "wheel", source_store_root=root / "source",
        runtime_store_root=root / "runtime", canonical_store=root / "canonical",
        repo_roots=(root / "repo",), dependencies=dependencies,
    )


def _sequenced_dependencies(
    sources: list[BuilderPackagingSourceMaterializationResult],
    dependency: DependencyRuntimeMaterializationResult,
    events: list[str] | None = None,
) -> _CompositionDependencies:
    trace = events if events is not None else []
    expected_site_packages = sources[0].binding.site_packages_root

    def source_materializer(**_kwargs):
        trace.append("source")
        return sources.pop(0)

    def dependency_materializer(**kwargs):
        trace.append("dependency")
        assert kwargs["source_site_packages"] == expected_site_packages
        return dependency

    return _CompositionDependencies(source_materializer, dependency_materializer)


def test_sequence_reproves_source_and_ignores_call_local_publication_truth(
    o_root: Path,
) -> None:
    tree, generation = _digest("a"), _digest("b")
    initial = _source_result(
        _source_binding(o_root, tree=tree, generation=generation, published=True), False,
    )
    final = _source_result(replace(initial.binding,
        source_lease_held_through_publication=False), True)
    events: list[str] = []
    result = _arguments(o_root, _sequenced_dependencies(
        [initial, final], _dependency_result(_dependency_binding(o_root, tree=tree)), events,
    ))
    assert events == ["source", "dependency", "source"]
    assert result.source_initial_reused_existing_generation is False
    assert result.source_final_reused_existing_generation is True
    assert result.binding.source.source_lease_held_through_publication is False
    assert result.binding.public_binding[
        "builder_dependency_composition_dependency_tree_digest_match"
    ] is True


def test_real_dependency_materializer_composes_the_reproved_source(
    o_root: Path,
) -> None:
    repo, canonical = o_root / "repo", o_root / "canonical"
    (repo / ".git").mkdir(parents=True)
    canonical.mkdir()
    source_root = o_root / "source-generation" / "site-packages"
    (source_root / "packaging").mkdir(parents=True)
    (source_root / "packaging" / "__init__.py").write_bytes(b"x = 1\n")
    limits = DependencyRuntimeLimits()
    plan = plan_dependency_runtime_snapshot(source_root, limits=limits)
    source = _source_binding(o_root, tree=plan.generation_id)
    source = replace(source, site_packages_root=source_root)
    values = [_source_result(source, False), _source_result(source, True)]
    deps = _CompositionDependencies(lambda **_kwargs: values.pop(0), materialize_dependency_runtime)
    result = _compose_builder_dependency_runtime_for_test(
        wheel_path=o_root / "wheel.whl", wheel_store_root=o_root / "wheel",
        source_store_root=o_root / "source", runtime_store_root=o_root / "runtime",
        canonical_store=canonical, repo_roots=(repo,), dependency_limits=limits,
        dependencies=deps,
    )
    assert result.binding.dependency.generation_id == plan.generation_id
    assert result.binding.dependency.site_packages_root.joinpath(
        "packaging", "__init__.py"
    ).read_bytes() == b"x = 1\n"


@pytest.mark.integration
def test_public_coordinator_composes_and_reuses_reviewed_physical_wheel(
    o_root: Path,
) -> None:
    wheel = Path(
        "O:/RedDog-Builder-Artifacts/packaging/26.0"
    ) / PACKAGING_26_WHEEL_SHA256 / PACKAGING_26_WHEEL_FILENAME
    if not wheel.is_file():
        pytest.skip("reviewed O:/E: packaging wheel is not provisioned")
    before = hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert before == PACKAGING_26_WHEEL_SHA256
    canonical = o_root / "canonical"
    canonical.mkdir()
    arguments = {
        "wheel_path": wheel,
        "wheel_store_root": wheel.parent,
        "source_store_root": o_root / "source-store",
        "runtime_store_root": o_root / "runtime-store",
        "canonical_store": canonical,
        "repo_roots": (Path("O:/Foundups-Agent").resolve(),),
    }
    first = compose_pinned_builder_dependency_runtime(**arguments)
    second = compose_pinned_builder_dependency_runtime(**arguments)
    assert (
        first.source_initial_reused_existing_generation,
        first.dependency_reused_existing_generation,
        first.source_final_reused_existing_generation,
    ) == (False, False, True)
    assert all((
        second.source_initial_reused_existing_generation,
        second.dependency_reused_existing_generation,
        second.source_final_reused_existing_generation,
    ))
    assert first.binding == second.binding
    assert first.binding.source.dependency_tree_digest == (
        first.binding.dependency.generation_id
    )
    assert all(not isinstance(value, Path)
               for value in first.binding.public_binding.values())
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == before


def test_source_identity_change_after_dependency_fails_closed(o_root: Path) -> None:
    tree = _digest("a")
    initial = _source_result(_source_binding(o_root, tree=tree), False)
    final = _source_result(_source_binding(o_root, tree=tree, generation=_digest("c")), False)
    dependencies = _sequenced_dependencies(
        [initial, final], _dependency_result(_dependency_binding(o_root, tree=tree)),
    )
    with pytest.raises(BuilderDependencyCompositionError) as failure:
        _arguments(o_root, dependencies)
    assert str(failure.value) == "BUILDER_DEPENDENCY_COMPOSITION_SOURCE_CHANGED"


def test_dependency_tree_mismatch_fails_after_final_source_reproof(o_root: Path) -> None:
    tree = _digest("a")
    source = _source_result(_source_binding(o_root, tree=tree), True)
    events: list[str] = []
    dependencies = _sequenced_dependencies(
        [source, source], _dependency_result(_dependency_binding(o_root, tree=_digest("c"))),
        events,
    )
    with pytest.raises(BuilderDependencyCompositionError) as failure:
        _arguments(o_root, dependencies)
    assert events == ["source", "dependency", "source"]
    assert str(failure.value) == "BUILDER_DEPENDENCY_COMPOSITION_TREE_DIGEST_MISMATCH"


def test_call_local_publication_truth_must_be_boolean(o_root: Path) -> None:
    tree = _digest("a")
    valid = _source_result(_source_binding(o_root, tree=tree), True)
    invalid = _source_result(replace(valid.binding,
        source_lease_held_through_publication=o_root / "private"), True)
    dependencies = _sequenced_dependencies(
        [invalid], _dependency_result(_dependency_binding(o_root, tree=tree)),
    )
    with pytest.raises(BuilderDependencyCompositionError) as failure:
        _arguments(o_root, dependencies)
    assert str(failure.value) == "BUILDER_DEPENDENCY_COMPOSITION_SOURCE_BINDING_INVALID"


@pytest.mark.parametrize(
    ("stage", "expected"),
    [
        ("source_initial", "BUILDER_DEPENDENCY_COMPOSITION_SOURCE_INITIAL_FAILED"),
        ("dependency", "BUILDER_DEPENDENCY_COMPOSITION_DEPENDENCY_FAILED"),
        ("source_final", "BUILDER_DEPENDENCY_COMPOSITION_SOURCE_FINAL_FAILED"),
    ],
)
def test_reuse_observations_must_be_exact_booleans(
    o_root: Path, stage: str, expected: str,
) -> None:
    tree = _digest("a")
    valid_source = _source_result(_source_binding(o_root, tree=tree), True)
    invalid_source = replace(valid_source, reused_existing_generation=o_root / "private")
    valid_dependency = _dependency_result(_dependency_binding(o_root, tree=tree))
    invalid_dependency = replace(
        valid_dependency, reused_existing_generation=o_root / "private",
    )
    sources = (
        [invalid_source]
        if stage == "source_initial"
        else [valid_source, invalid_source]
        if stage == "source_final"
        else [valid_source, valid_source]
    )
    dependency = invalid_dependency if stage == "dependency" else valid_dependency
    with pytest.raises(BuilderDependencyCompositionError) as failure:
        _arguments(o_root, _sequenced_dependencies(sources, dependency))
    assert str(failure.value) == expected


@pytest.mark.parametrize("final", [False, True])
def test_each_source_observation_requires_current_live_authority(
    o_root: Path, final: bool,
) -> None:
    tree = _digest("a")
    valid = _source_result(_source_binding(o_root, tree=tree), True)
    invalid = _source_result(replace(valid.binding,
        source_lease_held_through_current_verification=False), True)
    sources = [valid, invalid] if final else [invalid]
    dependencies = _sequenced_dependencies(
        sources, _dependency_result(_dependency_binding(o_root, tree=tree)),
    )
    with pytest.raises(BuilderDependencyCompositionError) as failure:
        _arguments(o_root, dependencies)
    assert str(failure.value) == "BUILDER_DEPENDENCY_COMPOSITION_SOURCE_AUTHORITY_REQUIRED"


@pytest.mark.parametrize(
    "changes",
    [
        {"artifact_bytes_verified_at_publication": False},
        {"write_denial_verified": True},
        {"activation_eligible": True},
        {"dependency_tree_digest": _digest("d")},
    ],
)
def test_dependency_must_remain_verified_and_inert(
    o_root: Path, changes: dict[str, object],
) -> None:
    tree = _digest("a")
    source = _source_result(_source_binding(o_root, tree=tree), True)
    dependency = replace(_dependency_binding(o_root, tree=tree), **changes)
    with pytest.raises(BuilderDependencyCompositionError) as failure:
        _arguments(o_root, _sequenced_dependencies(
            [source, source], _dependency_result(dependency),
        ))
    assert str(failure.value) == "BUILDER_DEPENDENCY_COMPOSITION_DEPENDENCY_BINDING_INVALID"


@pytest.mark.parametrize(
    ("stage", "expected"),
    [
        ("source_initial", "BUILDER_DEPENDENCY_COMPOSITION_SOURCE_INITIAL_FAILED"),
        ("dependency", "BUILDER_DEPENDENCY_COMPOSITION_DEPENDENCY_FAILED"),
        ("source_final", "BUILDER_DEPENDENCY_COMPOSITION_SOURCE_FINAL_FAILED"),
    ],
)
def test_stage_failures_are_path_free_and_do_not_roll_back_source(
    o_root: Path, stage: str, expected: str,
) -> None:
    tree = _digest("a")
    source = _source_result(_source_binding(o_root, tree=tree), True)
    sentinel = source.binding.site_packages_root / "sentinel.py"
    sentinel.write_bytes(b"preserve\n")
    calls = {"source": 0}

    def source_call(**_kwargs):
        calls["source"] += 1
        if stage == "source_initial" or stage == "source_final" and calls["source"] == 2:
            raise RuntimeError("O:/private/source/path")
        return source

    def dependency_call(**_kwargs):
        if stage == "dependency":
            raise RuntimeError("O:/private/runtime/path")
        return _dependency_result(_dependency_binding(o_root, tree=tree))

    with pytest.raises(BuilderDependencyCompositionError) as failure:
        _arguments(o_root, _CompositionDependencies(source_call, dependency_call))
    assert str(failure.value) == expected
    assert sentinel.read_bytes() == b"preserve\n"


def test_public_binding_is_path_free_and_denies_unproved_authority(o_root: Path) -> None:
    tree = _digest("a")
    source = _source_result(_source_binding(o_root, tree=tree), True)
    result = _arguments(o_root, _sequenced_dependencies(
        [source, source], _dependency_result(_dependency_binding(o_root, tree=tree)),
    ))
    public = result.binding.public_binding
    assert all(not isinstance(value, Path) for value in public.values())
    false_suffixes = (
        "cross_store_atomicity_verified", "simultaneous_snapshot_verified",
        "post_return_immutability_verified", "persistent_write_denial_verified",
        "import_performed", "child_execution_performed", "activation_eligible",
        "a_grade_verified", "retrieval_rsi_verified",
    )
    assert all(public[f"builder_dependency_composition_{name}"] is False
               for name in false_suffixes)
