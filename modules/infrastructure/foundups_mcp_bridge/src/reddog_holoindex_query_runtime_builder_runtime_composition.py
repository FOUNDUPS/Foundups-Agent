"""Compose the exact packaging builder dependency with an inert base runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .reddog_holoindex_base_runtime_contract import BaseRuntimeLimits
from .reddog_holoindex_dependency_runtime_contract import DependencyRuntimeLimits
from .reddog_holoindex_query_runtime_builder_dependency_composition import (
    compose_pinned_builder_dependency_runtime,
)
from .reddog_holoindex_query_runtime_builder_dependency_composition_contract import (
    BuilderDependencyCompositionResult,
)
from .reddog_holoindex_query_runtime_builder_packaging_source_contract import (
    BuilderPackagingSourceLimits,
)
from .reddog_holoindex_query_runtime_builder_runtime_composition_contract import (
    BuilderRuntimeCompositionError,
    BuilderRuntimeCompositionResult,
    build_builder_runtime_composition_binding,
    require_builder_dependency_composition,
)
from .reddog_holoindex_runtime_composition_contract import (
    RuntimeCompositionLimits,
    RuntimeCompositionMaterializationResult,
)
from .reddog_holoindex_runtime_composition_materializer import (
    materialize_runtime_composition,
)


@dataclass(frozen=True)
class _BuilderRuntimeCompositionDependencies:
    builder_dependency_composer: Callable[..., BuilderDependencyCompositionResult]
    runtime_composition_materializer: Callable[
        ..., RuntimeCompositionMaterializationResult
    ]


_SEALED_DEPENDENCIES = _BuilderRuntimeCompositionDependencies(
    compose_pinned_builder_dependency_runtime, materialize_runtime_composition,
)


def _fail(code: str) -> None:
    raise BuilderRuntimeCompositionError(code)


def _builder_dependency_call(
    *, dependencies: _BuilderRuntimeCompositionDependencies,
    wheel_path: Path | str, wheel_store_root: Path | str,
    source_store_root: Path | str, dependency_runtime_store_root: Path | str,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    source_limits: BuilderPackagingSourceLimits,
    dependency_limits: DependencyRuntimeLimits,
) -> BuilderDependencyCompositionResult:
    call_failed = False
    try:
        result = dependencies.builder_dependency_composer(
            wheel_path=wheel_path, wheel_store_root=wheel_store_root,
            source_store_root=source_store_root,
            runtime_store_root=dependency_runtime_store_root,
            canonical_store=canonical_store, repo_roots=repo_roots,
            source_limits=source_limits, dependency_limits=dependency_limits,
        )
    except Exception:
        call_failed = True
        result = None
    if call_failed:
        _fail("BUILDER_RUNTIME_COMPOSITION_BUILDER_DEPENDENCY_FAILED")
    if type(result) is not BuilderDependencyCompositionResult or any(
        type(value) is not bool for value in (
            result.source_initial_reused_existing_generation,
            result.dependency_reused_existing_generation,
            result.source_final_reused_existing_generation,
        )
    ):
        _fail("BUILDER_RUNTIME_COMPOSITION_BUILDER_DEPENDENCY_FAILED")
    require_builder_dependency_composition(result.binding)
    return result


def _runtime_composition_call(
    *, dependencies: _BuilderRuntimeCompositionDependencies,
    builder: BuilderDependencyCompositionResult,
    composition_store_root: Path | str, base_runtime_store_root: Path | str,
    base_generation_root: Path | str, dependency_runtime_store_root: Path | str,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    composition_limits: RuntimeCompositionLimits, base_limits: BaseRuntimeLimits,
    dependency_limits: DependencyRuntimeLimits,
) -> RuntimeCompositionMaterializationResult:
    call_failed = False
    try:
        result = dependencies.runtime_composition_materializer(
            composition_store_root=composition_store_root,
            base_runtime_store_root=base_runtime_store_root,
            base_generation_root=base_generation_root,
            dependency_runtime_store_root=dependency_runtime_store_root,
            dependency_generation_root=builder.binding.dependency.generation_root,
            canonical_store=canonical_store, repo_roots=repo_roots,
            composition_limits=composition_limits, base_limits=base_limits,
            dependency_limits=dependency_limits,
        )
    except Exception:
        call_failed = True
        result = None
    if call_failed:
        _fail("BUILDER_RUNTIME_COMPOSITION_RUNTIME_FAILED")
    if (
        type(result) is not RuntimeCompositionMaterializationResult
        or type(result.reused_existing_generation) is not bool
    ):
        _fail("BUILDER_RUNTIME_COMPOSITION_RUNTIME_FAILED")
    return result


def _result(
    builder: BuilderDependencyCompositionResult,
    runtime: RuntimeCompositionMaterializationResult,
) -> BuilderRuntimeCompositionResult:
    binding = build_builder_runtime_composition_binding(
        builder_dependency=builder.binding, runtime_composition=runtime.binding,
    )
    return BuilderRuntimeCompositionResult(
        binding=binding,
        source_initial_reused_existing_generation=(
            builder.source_initial_reused_existing_generation
        ),
        dependency_reused_existing_generation=(
            builder.dependency_reused_existing_generation
        ),
        source_final_reused_existing_generation=(
            builder.source_final_reused_existing_generation
        ),
        runtime_composition_reused_existing_generation=(
            runtime.reused_existing_generation
        ),
    )


def _compose_pinned_builder_runtime_for_test(
    *, wheel_path: Path | str, wheel_store_root: Path | str,
    source_store_root: Path | str, dependency_runtime_store_root: Path | str,
    base_runtime_store_root: Path | str, base_generation_root: Path | str,
    composition_store_root: Path | str, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    source_limits: BuilderPackagingSourceLimits = BuilderPackagingSourceLimits(),
    dependency_limits: DependencyRuntimeLimits = DependencyRuntimeLimits(),
    base_limits: BaseRuntimeLimits = BaseRuntimeLimits(),
    composition_limits: RuntimeCompositionLimits = RuntimeCompositionLimits(),
    dependencies: _BuilderRuntimeCompositionDependencies = _SEALED_DEPENDENCIES,
) -> BuilderRuntimeCompositionResult:
    """Test seam; production always uses the two sealed public materializers."""

    builder = _builder_dependency_call(
        dependencies=dependencies, wheel_path=wheel_path,
        wheel_store_root=wheel_store_root, source_store_root=source_store_root,
        dependency_runtime_store_root=dependency_runtime_store_root,
        canonical_store=canonical_store, repo_roots=repo_roots,
        source_limits=source_limits, dependency_limits=dependency_limits,
    )
    runtime = _runtime_composition_call(
        dependencies=dependencies, builder=builder,
        composition_store_root=composition_store_root,
        base_runtime_store_root=base_runtime_store_root,
        base_generation_root=base_generation_root,
        dependency_runtime_store_root=dependency_runtime_store_root,
        canonical_store=canonical_store, repo_roots=repo_roots,
        composition_limits=composition_limits, base_limits=base_limits,
        dependency_limits=dependency_limits,
    )
    return _result(builder, runtime)


def compose_pinned_builder_runtime(
    *, wheel_path: Path | str, wheel_store_root: Path | str,
    source_store_root: Path | str, dependency_runtime_store_root: Path | str,
    base_runtime_store_root: Path | str, base_generation_root: Path | str,
    composition_store_root: Path | str, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    source_limits: BuilderPackagingSourceLimits = BuilderPackagingSourceLimits(),
    dependency_limits: DependencyRuntimeLimits = DependencyRuntimeLimits(),
    base_limits: BaseRuntimeLimits = BaseRuntimeLimits(),
    composition_limits: RuntimeCompositionLimits = RuntimeCompositionLimits(),
) -> BuilderRuntimeCompositionResult:
    """Create/reprove only the inert builder runtime; never launch a process."""

    call_failed = False
    try:
        result = _compose_pinned_builder_runtime_for_test(
            wheel_path=wheel_path, wheel_store_root=wheel_store_root,
            source_store_root=source_store_root,
            dependency_runtime_store_root=dependency_runtime_store_root,
            base_runtime_store_root=base_runtime_store_root,
            base_generation_root=base_generation_root,
            composition_store_root=composition_store_root,
            canonical_store=canonical_store, repo_roots=repo_roots,
            source_limits=source_limits, dependency_limits=dependency_limits,
            base_limits=base_limits, composition_limits=composition_limits,
            dependencies=_SEALED_DEPENDENCIES,
        )
    except BuilderRuntimeCompositionError:
        raise
    except Exception:
        call_failed = True
        result = None
    if call_failed:
        _fail("BUILDER_RUNTIME_COMPOSITION_FAILED")
    return result


__all__ = [
    "BuilderRuntimeCompositionError", "compose_pinned_builder_runtime",
]
