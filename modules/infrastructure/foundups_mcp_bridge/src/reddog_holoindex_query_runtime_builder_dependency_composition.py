"""Sequentially compose verified packaging source and inert dependency runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeLimits,
    DependencyRuntimeMaterializationResult,
)
from .reddog_holoindex_dependency_runtime_materializer import (
    materialize_dependency_runtime,
)
from .reddog_holoindex_query_runtime_builder_dependency_composition_contract import (
    BuilderDependencyCompositionError,
    BuilderDependencyCompositionResult,
    build_builder_dependency_composition_binding,
    require_inert_dependency_runtime,
    require_live_builder_packaging_source,
    require_same_builder_packaging_source,
)
from .reddog_holoindex_query_runtime_builder_packaging_source_contract import (
    BuilderPackagingSourceLimits,
    BuilderPackagingSourceMaterializationResult,
)
from .reddog_holoindex_query_runtime_builder_packaging_source_materializer import (
    materialize_pinned_builder_packaging_source,
)


@dataclass(frozen=True)
class _CompositionDependencies:
    source_materializer: Callable[..., BuilderPackagingSourceMaterializationResult]
    dependency_materializer: Callable[..., DependencyRuntimeMaterializationResult]


_SEALED_DEPENDENCIES = _CompositionDependencies(
    source_materializer=materialize_pinned_builder_packaging_source,
    dependency_materializer=materialize_dependency_runtime,
)


def _fail(code: str, cause: Exception | None = None) -> None:
    error = BuilderDependencyCompositionError(code)
    if cause is None:
        raise error
    raise error from cause


def _source_call(
    *, dependencies: _CompositionDependencies,
    source_kwargs: dict[str, Any],
    error_code: str,
) -> BuilderPackagingSourceMaterializationResult:
    try:
        result = dependencies.source_materializer(**source_kwargs)
    except Exception as exc:
        _fail(error_code, exc)
    if (
        type(result) is not BuilderPackagingSourceMaterializationResult
        or type(result.reused_existing_generation) is not bool
    ):
        _fail(error_code)
    require_live_builder_packaging_source(result.binding)
    return result


def _dependency_call(
    *, dependencies: _CompositionDependencies,
    source: BuilderPackagingSourceMaterializationResult,
    runtime_store_root: Path | str,
    canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    limits: DependencyRuntimeLimits,
) -> DependencyRuntimeMaterializationResult:
    try:
        result = dependencies.dependency_materializer(
            source_site_packages=source.binding.site_packages_root,
            runtime_store_root=runtime_store_root,
            canonical_store=canonical_store,
            repo_roots=repo_roots,
            limits=limits,
        )
    except Exception as exc:
        _fail("BUILDER_DEPENDENCY_COMPOSITION_DEPENDENCY_FAILED", exc)
    if (
        type(result) is not DependencyRuntimeMaterializationResult
        or type(result.reused_existing_generation) is not bool
    ):
        _fail("BUILDER_DEPENDENCY_COMPOSITION_DEPENDENCY_FAILED")
    require_inert_dependency_runtime(result.binding)
    return result


def _source_arguments(
    *, wheel_path: Path | str,
    wheel_store_root: Path | str,
    source_store_root: Path | str,
    canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    limits: BuilderPackagingSourceLimits,
) -> dict[str, Any]:
    return {
        "wheel_path": wheel_path,
        "wheel_store_root": wheel_store_root,
        "source_store_root": source_store_root,
        "canonical_store": canonical_store,
        "repo_roots": repo_roots,
        "limits": limits,
    }


def _result(
    initial: BuilderPackagingSourceMaterializationResult,
    dependency: DependencyRuntimeMaterializationResult,
    final: BuilderPackagingSourceMaterializationResult,
) -> BuilderDependencyCompositionResult:
    require_same_builder_packaging_source(initial.binding, final.binding)
    binding = build_builder_dependency_composition_binding(
        source=final.binding, dependency=dependency.binding,
    )
    return BuilderDependencyCompositionResult(
        binding=binding,
        source_initial_reused_existing_generation=initial.reused_existing_generation,
        dependency_reused_existing_generation=dependency.reused_existing_generation,
        source_final_reused_existing_generation=final.reused_existing_generation,
    )


def _compose_builder_dependency_runtime_for_test(
    *, wheel_path: Path | str,
    wheel_store_root: Path | str,
    source_store_root: Path | str,
    runtime_store_root: Path | str,
    canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    source_limits: BuilderPackagingSourceLimits = BuilderPackagingSourceLimits(),
    dependency_limits: DependencyRuntimeLimits = DependencyRuntimeLimits(),
    dependencies: _CompositionDependencies = _SEALED_DEPENDENCIES,
) -> BuilderDependencyCompositionResult:
    """Test seam; public operation uses only sealed materializers."""

    source_kwargs = _source_arguments(
        wheel_path=wheel_path,
        wheel_store_root=wheel_store_root,
        source_store_root=source_store_root,
        canonical_store=canonical_store,
        repo_roots=repo_roots,
        limits=source_limits,
    )
    initial = _source_call(
        dependencies=dependencies,
        source_kwargs=source_kwargs,
        error_code="BUILDER_DEPENDENCY_COMPOSITION_SOURCE_INITIAL_FAILED",
    )
    dependency = _dependency_call(
        dependencies=dependencies,
        source=initial,
        runtime_store_root=runtime_store_root,
        canonical_store=canonical_store,
        repo_roots=repo_roots,
        limits=dependency_limits,
    )
    final = _source_call(
        dependencies=dependencies,
        source_kwargs=source_kwargs,
        error_code="BUILDER_DEPENDENCY_COMPOSITION_SOURCE_FINAL_FAILED",
    )
    return _result(initial, dependency, final)


def compose_pinned_builder_dependency_runtime(
    *, wheel_path: Path | str,
    wheel_store_root: Path | str,
    source_store_root: Path | str,
    runtime_store_root: Path | str,
    canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    source_limits: BuilderPackagingSourceLimits = BuilderPackagingSourceLimits(),
    dependency_limits: DependencyRuntimeLimits = DependencyRuntimeLimits(),
) -> BuilderDependencyCompositionResult:
    """Compose two inert generations without a cross-store lock or rollback."""

    try:
        return _compose_builder_dependency_runtime_for_test(
            wheel_path=wheel_path,
            wheel_store_root=wheel_store_root,
            source_store_root=source_store_root,
            runtime_store_root=runtime_store_root,
            canonical_store=canonical_store,
            repo_roots=repo_roots,
            source_limits=source_limits,
            dependency_limits=dependency_limits,
            dependencies=_SEALED_DEPENDENCIES,
        )
    except BuilderDependencyCompositionError:
        raise
    except Exception as exc:
        _fail("BUILDER_DEPENDENCY_COMPOSITION_FAILED", exc)


__all__ = [
    "BuilderDependencyCompositionError",
    "compose_pinned_builder_dependency_runtime",
]
