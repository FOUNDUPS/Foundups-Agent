"""Falsification tests for inert builder-runtime composition."""

from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_query_runtime_builder_runtime_composition as composition_module,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_dependency_composition_contract import (
    BuilderDependencyCompositionBinding,
    BuilderDependencyCompositionResult,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging_source_contract import (
    BuilderPackagingSourceBinding,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_runtime_composition import (
    _BuilderRuntimeCompositionDependencies,
    _compose_pinned_builder_runtime_for_test,
    compose_pinned_builder_runtime,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_runtime_composition_contract import (
    BuilderRuntimeCompositionError,
    _FALSE_FIELDS,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_runtime_composition_contract import (
    DESCRIPTOR_NAME as RUNTIME_COMPOSITION_DESCRIPTOR_NAME,
    RuntimeCompositionMaterializationResult,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_runtime_composition_materializer import (
    materialize_runtime_composition,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging_wheel import (
    PACKAGING_26_WHEEL_FILENAME,
    PACKAGING_26_WHEEL_SHA256,
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
    with tempfile.TemporaryDirectory(prefix="reddog-builder-runtime-", dir=parent) as raw:
        yield Path(raw).resolve()


def _source_binding(root: Path, dependency) -> BuilderPackagingSourceBinding:
    generation_root = root / "source" / _digest("b").removeprefix("sha256:")
    return BuilderPackagingSourceBinding(
        generation_root=generation_root,
        site_packages_root=generation_root / "site-packages",
        wheel_path=generation_root / "wheel" / "packaging.whl",
        descriptor_path=generation_root / "builder-packaging-source.json",
        descriptor_digest=_digest("1"), generation_id=_digest("b"),
        inventory_digest=_digest("2"), wheel_sha256=_digest("3"),
        member_set_digest=_digest("4"),
        dependency_tree_digest=dependency.generation_id,
        member_count=dependency.file_count,
        directory_count=dependency.directory_count,
        expanded_bytes=dependency.total_bytes,
        reviewed_pin_match=True,
        source_lease_held_through_publication=False,
        source_lease_held_through_current_verification=True,
    )


def _builder_dependency(root: Path, dependency) -> BuilderDependencyCompositionResult:
    return BuilderDependencyCompositionResult(
        binding=BuilderDependencyCompositionBinding(
            source=_source_binding(root, dependency), dependency=dependency,
        ),
        source_initial_reused_existing_generation=True,
        dependency_reused_existing_generation=True,
        source_final_reused_existing_generation=True,
    )


def _dependencies(builder, runtime, events=None):
    trace = events if events is not None else []

    def builder_call(**_kwargs):
        trace.append("builder_dependency")
        return builder

    def runtime_call(**kwargs):
        trace.append("runtime_composition")
        assert kwargs["dependency_generation_root"] == builder.binding.dependency.generation_root
        return runtime(**kwargs) if callable(runtime) else runtime

    return _BuilderRuntimeCompositionDependencies(builder_call, runtime_call)


def _arguments(root: Path, fixture, dependencies):
    return _compose_pinned_builder_runtime_for_test(
        wheel_path=root / "packaging.whl",
        wheel_store_root=root / "wheel-store",
        source_store_root=root / "source-store",
        dependency_runtime_store_root=fixture.dependency_store,
        base_runtime_store_root=fixture.base_store,
        base_generation_root=fixture.base.binding.generation_root,
        composition_store_root=fixture.composition_store,
        canonical_store=fixture.canonical,
        repo_roots=(fixture.repo,),
        base_limits=BASE_LIMITS,
        dependency_limits=DEPENDENCY_LIMITS,
        dependencies=dependencies,
    )


def test_exact_builder_dependency_is_composed_with_existing_runtime(o_root: Path) -> None:
    fixture = materialized_runtime_components(o_root)
    builder = _builder_dependency(o_root, fixture.dependency.binding)
    events: list[str] = []
    result = _arguments(
        o_root, fixture, _dependencies(builder, materialize_runtime_composition, events),
    )
    assert events == ["builder_dependency", "runtime_composition"]
    assert result.binding.builder_dependency == builder.binding
    assert result.binding.runtime_composition.dependency_runtime == builder.binding.dependency
    assert result.builder_dependency_reused_existing_generation is True
    assert result.runtime_composition_reused_existing_generation is False
    assert {path.name for path in result.binding.runtime_composition.generation_root.iterdir()} == {
        RUNTIME_COMPOSITION_DESCRIPTOR_NAME,
        ".runtime-composition-publication-orphans",
    }


def test_exact_reuse_is_reported_without_inflating_authority(o_root: Path) -> None:
    fixture = materialized_runtime_components(o_root)
    builder = _builder_dependency(o_root, fixture.dependency.binding)
    dependencies = _dependencies(builder, materialize_runtime_composition)
    first = _arguments(o_root, fixture, dependencies)
    second = _arguments(o_root, fixture, dependencies)
    assert first.binding == second.binding
    assert second.runtime_composition_reused_existing_generation is True
    public = second.binding.public_binding
    assert public["builder_runtime_composition_dependency_identity_verified"] is True
    assert public["builder_runtime_composition_inert_only"] is True


@pytest.mark.integration
def test_public_join_composes_the_reviewed_wheel_with_an_exact_base(
    o_root: Path,
) -> None:
    wheel = Path(
        "O:/RedDog-Builder-Artifacts/packaging/26.0"
    ) / PACKAGING_26_WHEEL_SHA256 / PACKAGING_26_WHEEL_FILENAME
    if not wheel.is_file():
        pytest.skip("reviewed O:/E: packaging wheel is not provisioned")
    fixture = materialized_runtime_components(o_root)
    before = hashlib.sha256(wheel.read_bytes()).hexdigest()
    arguments = {
        "wheel_path": wheel, "wheel_store_root": wheel.parent,
        "source_store_root": o_root / "builder-source",
        "dependency_runtime_store_root": fixture.dependency_store,
        "base_runtime_store_root": fixture.base_store,
        "base_generation_root": fixture.base.binding.generation_root,
        "composition_store_root": fixture.composition_store,
        "canonical_store": fixture.canonical, "repo_roots": (fixture.repo,),
        "base_limits": BASE_LIMITS,
    }
    first = compose_pinned_builder_runtime(**arguments)
    second = compose_pinned_builder_runtime(**arguments)
    assert first.binding == second.binding
    assert first.runtime_composition_reused_existing_generation is False
    assert second.builder_dependency_reused_existing_generation is True
    assert second.runtime_composition_reused_existing_generation is True
    assert second.binding.runtime_composition.interpreter_path == (
        second.binding.runtime_composition.base_runtime.base_prefix_root / "python.exe"
    )
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == before


@pytest.mark.parametrize(
    ("builder_change", "runtime_change", "expected"),
    [
        ({"source_initial_reused_existing_generation": Path("O:/private")}, {},
         "BUILDER_RUNTIME_COMPOSITION_BUILDER_DEPENDENCY_FAILED"),
        ({"dependency_reused_existing_generation": Path("O:/private")}, {},
         "BUILDER_RUNTIME_COMPOSITION_BUILDER_DEPENDENCY_FAILED"),
        ({"source_final_reused_existing_generation": Path("O:/private")}, {},
         "BUILDER_RUNTIME_COMPOSITION_BUILDER_DEPENDENCY_FAILED"),
        ({}, {"reused_existing_generation": Path("O:/private")},
         "BUILDER_RUNTIME_COMPOSITION_RUNTIME_FAILED"),
    ],
)
def test_reuse_authority_rejects_non_booleans(
    o_root: Path, builder_change, runtime_change, expected: str,
) -> None:
    fixture = materialized_runtime_components(o_root)
    builder = replace(
        _builder_dependency(o_root, fixture.dependency.binding), **builder_change,
    )
    runtime = materialize_runtime_composition(
        composition_store_root=fixture.composition_store,
        base_runtime_store_root=fixture.base_store,
        base_generation_root=fixture.base.binding.generation_root,
        dependency_runtime_store_root=fixture.dependency_store,
        dependency_generation_root=fixture.dependency.binding.generation_root,
        canonical_store=fixture.canonical, repo_roots=(fixture.repo,),
        base_limits=BASE_LIMITS, dependency_limits=DEPENDENCY_LIMITS,
    )
    runtime = replace(runtime, **runtime_change)
    with pytest.raises(BuilderRuntimeCompositionError) as failure:
        _arguments(o_root, fixture, _dependencies(builder, runtime))
    assert str(failure.value) == expected


@pytest.mark.parametrize(
    ("stage", "expected"),
    [
        ("builder", "BUILDER_RUNTIME_COMPOSITION_BUILDER_DEPENDENCY_FAILED"),
        ("runtime", "BUILDER_RUNTIME_COMPOSITION_RUNTIME_FAILED"),
    ],
)
def test_raw_mappings_cannot_replace_typed_results(
    o_root: Path, stage: str, expected: str,
) -> None:
    fixture = materialized_runtime_components(o_root)
    builder = _builder_dependency(o_root, fixture.dependency.binding)
    runtime = materialize_runtime_composition(
        composition_store_root=fixture.composition_store,
        base_runtime_store_root=fixture.base_store,
        base_generation_root=fixture.base.binding.generation_root,
        dependency_runtime_store_root=fixture.dependency_store,
        dependency_generation_root=fixture.dependency.binding.generation_root,
        canonical_store=fixture.canonical, repo_roots=(fixture.repo,),
        base_limits=BASE_LIMITS, dependency_limits=DEPENDENCY_LIMITS,
    )
    dependencies = _BuilderRuntimeCompositionDependencies(
        (lambda **_kwargs: {}) if stage == "builder" else (lambda **_kwargs: builder),
        (lambda **_kwargs: {}) if stage == "runtime" else (lambda **_kwargs: runtime),
    )
    with pytest.raises(BuilderRuntimeCompositionError) as failure:
        _arguments(o_root, fixture, dependencies)
    assert str(failure.value) == expected


def test_result_subclasses_cannot_replace_exact_contract_types(o_root: Path) -> None:
    fixture = materialized_runtime_components(o_root)
    builder = _builder_dependency(o_root, fixture.dependency.binding)
    runtime = materialize_runtime_composition(
        composition_store_root=fixture.composition_store,
        base_runtime_store_root=fixture.base_store,
        base_generation_root=fixture.base.binding.generation_root,
        dependency_runtime_store_root=fixture.dependency_store,
        dependency_generation_root=fixture.dependency.binding.generation_root,
        canonical_store=fixture.canonical, repo_roots=(fixture.repo,),
        base_limits=BASE_LIMITS, dependency_limits=DEPENDENCY_LIMITS,
    )

    class DerivedBuilderResult(BuilderDependencyCompositionResult):
        pass

    class DerivedRuntimeResult(RuntimeCompositionMaterializationResult):
        pass

    derived_builder = DerivedBuilderResult(
        builder.binding, builder.source_initial_reused_existing_generation,
        builder.dependency_reused_existing_generation,
        builder.source_final_reused_existing_generation,
    )
    derived_runtime = DerivedRuntimeResult(runtime.binding, runtime.reused_existing_generation)
    cases = (
        (derived_builder, runtime,
         "BUILDER_RUNTIME_COMPOSITION_BUILDER_DEPENDENCY_FAILED"),
        (builder, derived_runtime, "BUILDER_RUNTIME_COMPOSITION_RUNTIME_FAILED"),
    )
    for candidate_builder, candidate_runtime, expected in cases:
        with pytest.raises(BuilderRuntimeCompositionError) as failure:
            _arguments(
                o_root, fixture,
                _dependencies(candidate_builder, candidate_runtime),
            )
        assert str(failure.value) == expected


@pytest.mark.parametrize(
    ("stage", "expected"),
    [
        ("builder", "BUILDER_RUNTIME_COMPOSITION_BUILDER_DEPENDENCY_FAILED"),
        ("runtime", "BUILDER_RUNTIME_COMPOSITION_RUNTIME_FAILED"),
    ],
)
def test_stage_failure_is_path_free_and_preserves_existing_generations(
    o_root: Path, stage: str, expected: str,
) -> None:
    fixture = materialized_runtime_components(o_root)
    builder = _builder_dependency(o_root, fixture.dependency.binding)
    sentinel = builder.binding.dependency.site_packages_root / "alpha.py"

    def fail(**_kwargs):
        raise RuntimeError("O:/private/runtime/path")

    dependencies = _BuilderRuntimeCompositionDependencies(
        fail if stage == "builder" else lambda **_kwargs: builder,
        fail if stage == "runtime" else materialize_runtime_composition,
    )
    with pytest.raises(BuilderRuntimeCompositionError) as failure:
        _arguments(o_root, fixture, dependencies)
    assert str(failure.value) == expected
    assert failure.value.__cause__ is None
    assert failure.value.__context__ is None
    assert sentinel.read_text(encoding="utf-8") == "VALUE = 1\n"


def test_builder_failure_stops_before_runtime_stage(o_root: Path) -> None:
    fixture = materialized_runtime_components(o_root)
    events: list[str] = []

    def builder_failure(**_kwargs):
        events.append("builder_dependency")
        raise RuntimeError("O:/private/builder/path")

    def forbidden_runtime(**_kwargs):
        events.append("runtime_composition")
        raise AssertionError("runtime stage must not execute")

    dependencies = _BuilderRuntimeCompositionDependencies(
        builder_failure, forbidden_runtime,
    )
    with pytest.raises(BuilderRuntimeCompositionError):
        _arguments(o_root, fixture, dependencies)
    assert events == ["builder_dependency"]


def test_public_fallback_error_has_no_private_exception_graph(
    o_root: Path, monkeypatch,
) -> None:
    fixture = materialized_runtime_components(o_root)

    def unexpected_failure(**_kwargs):
        raise RuntimeError("O:/private/public/path")

    monkeypatch.setattr(
        composition_module, "_compose_pinned_builder_runtime_for_test",
        unexpected_failure,
    )
    with pytest.raises(BuilderRuntimeCompositionError) as failure:
        compose_pinned_builder_runtime(
            wheel_path=o_root / "packaging.whl",
            wheel_store_root=o_root / "wheel-store",
            source_store_root=o_root / "source-store",
            dependency_runtime_store_root=fixture.dependency_store,
            base_runtime_store_root=fixture.base_store,
            base_generation_root=fixture.base.binding.generation_root,
            composition_store_root=fixture.composition_store,
            canonical_store=fixture.canonical, repo_roots=(fixture.repo,),
            base_limits=BASE_LIMITS, dependency_limits=DEPENDENCY_LIMITS,
        )
    assert str(failure.value) == "BUILDER_RUNTIME_COMPOSITION_FAILED"
    assert failure.value.__cause__ is None
    assert failure.value.__context__ is None


@pytest.mark.parametrize(
    "field",
    [
        "generation_root", "site_packages_root", "descriptor_path",
        "generation_id", "descriptor_digest", "inventory_digest",
        "dependency_tree_digest", "file_count", "directory_count", "total_bytes",
        "artifact_bytes_verified_at_publication", "write_denial_verified",
        "activation_eligible",
    ],
)
def test_every_dependency_identity_field_must_match(
    o_root: Path, field: str,
) -> None:
    fixture = materialized_runtime_components(o_root)
    builder = _builder_dependency(o_root, fixture.dependency.binding)
    runtime = materialize_runtime_composition(
        composition_store_root=fixture.composition_store,
        base_runtime_store_root=fixture.base_store,
        base_generation_root=fixture.base.binding.generation_root,
        dependency_runtime_store_root=fixture.dependency_store,
        dependency_generation_root=fixture.dependency.binding.generation_root,
        canonical_store=fixture.canonical, repo_roots=(fixture.repo,),
        base_limits=BASE_LIMITS, dependency_limits=DEPENDENCY_LIMITS,
    )
    value = runtime.binding.dependency_runtime
    original = getattr(value, field)
    if type(original) is bool:
        replacement = not original
    elif isinstance(original, Path):
        replacement = original.parent / "other"
    elif type(original) is int:
        replacement = original + 1
    else:
        replacement = _digest("f")
    changed_dependency = replace(value, **{field: replacement})
    changed_runtime = replace(runtime, binding=replace(
        runtime.binding, dependency_runtime=changed_dependency,
    ))
    with pytest.raises(BuilderRuntimeCompositionError) as failure:
        _arguments(o_root, fixture, _dependencies(builder, changed_runtime))
    assert str(failure.value) == "BUILDER_RUNTIME_COMPOSITION_DEPENDENCY_MISMATCH"


@pytest.mark.parametrize(
    "field",
    [
        "abi_compatibility_verified", "native_loader_closure_verified",
        "deterministic_effects_verified", "preimport_bootstrap_verified",
        "signature_verified", "write_denial_verified", "activation_eligible",
        "exact_runtime_closure_verified",
    ],
)
def test_runtime_authority_cannot_be_laundered(o_root: Path, field: str) -> None:
    fixture = materialized_runtime_components(o_root)
    builder = _builder_dependency(o_root, fixture.dependency.binding)
    runtime = materialize_runtime_composition(
        composition_store_root=fixture.composition_store,
        base_runtime_store_root=fixture.base_store,
        base_generation_root=fixture.base.binding.generation_root,
        dependency_runtime_store_root=fixture.dependency_store,
        dependency_generation_root=fixture.dependency.binding.generation_root,
        canonical_store=fixture.canonical, repo_roots=(fixture.repo,),
        base_limits=BASE_LIMITS, dependency_limits=DEPENDENCY_LIMITS,
    )
    changed = replace(runtime, binding=replace(runtime.binding, **{field: True}))
    with pytest.raises(BuilderRuntimeCompositionError) as failure:
        _arguments(o_root, fixture, _dependencies(builder, changed))
    assert str(failure.value) == "BUILDER_RUNTIME_COMPOSITION_RUNTIME_BINDING_INVALID"


def test_public_binding_is_path_free_and_denies_process_authority(o_root: Path) -> None:
    fixture = materialized_runtime_components(o_root)
    builder = _builder_dependency(o_root, fixture.dependency.binding)
    result = _arguments(
        o_root, fixture, _dependencies(builder, materialize_runtime_composition),
    )
    public = result.binding.public_binding
    assert all(not isinstance(value, Path) for value in public.values())
    expected_false = {
        f"builder_runtime_composition_{name}" for name in _FALSE_FIELDS
    }
    assert expected_false.issubset(public)
    assert all(public[name] is False for name in expected_false)
