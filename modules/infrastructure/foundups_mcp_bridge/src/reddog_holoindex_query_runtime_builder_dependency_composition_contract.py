"""Path-free contract for sequential builder dependency composition."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeBinding,
    is_digest,
)
from .reddog_holoindex_query_runtime_builder_packaging_source_contract import (
    BuilderPackagingSourceBinding,
)


_FALSE_FIELDS = (
    "cross_store_atomicity_verified",
    "simultaneous_snapshot_verified",
    "post_return_immutability_verified",
    "persistent_write_denial_verified",
    "official_provenance_authenticated",
    "signature_verified",
    "installation_performed",
    "import_performed",
    "child_execution_performed",
    "builder_runtime_authenticated",
    "preimport_loader_authority_verified",
    "native_loader_closure_verified",
    "subprocess_closure_verified",
    "exact_runtime_closure_verified",
    "deterministic_effects_verified",
    "activation_eligible",
    "a_grade_verified",
    "retrieval_rsi_verified",
)


class BuilderDependencyCompositionError(RuntimeError):
    """Stable path-free composition failure."""


def _fail(code: str) -> None:
    raise BuilderDependencyCompositionError(code)


def _absolute_paths(paths: tuple[Path, ...], code: str) -> None:
    if any(not isinstance(path, Path) or not path.is_absolute() for path in paths):
        _fail(code)


def _positive_counts(values: tuple[int, ...], code: str) -> None:
    if any(type(value) is not int or value <= 0 for value in values):
        _fail(code)


def require_live_builder_packaging_source(
    binding: BuilderPackagingSourceBinding,
) -> None:
    """Require one current fixed-pin source result without trusting history."""

    if type(binding) is not BuilderPackagingSourceBinding:
        _fail("BUILDER_DEPENDENCY_COMPOSITION_SOURCE_BINDING_INVALID")
    _absolute_paths(
        (
            binding.generation_root,
            binding.site_packages_root,
            binding.wheel_path,
            binding.descriptor_path,
        ),
        "BUILDER_DEPENDENCY_COMPOSITION_SOURCE_BINDING_INVALID",
    )
    digests = (
        binding.descriptor_digest,
        binding.generation_id,
        binding.inventory_digest,
        binding.wheel_sha256,
        binding.member_set_digest,
        binding.dependency_tree_digest,
    )
    if any(not is_digest(value) for value in digests):
        _fail("BUILDER_DEPENDENCY_COMPOSITION_SOURCE_BINDING_INVALID")
    _positive_counts(
        (binding.member_count, binding.expanded_bytes),
        "BUILDER_DEPENDENCY_COMPOSITION_SOURCE_BINDING_INVALID",
    )
    if type(binding.directory_count) is not int or binding.directory_count < 0:
        _fail("BUILDER_DEPENDENCY_COMPOSITION_SOURCE_BINDING_INVALID")
    if type(binding.source_lease_held_through_publication) is not bool:
        _fail("BUILDER_DEPENDENCY_COMPOSITION_SOURCE_BINDING_INVALID")
    if (
        binding.reviewed_pin_match is not True
        or binding.source_lease_held_through_current_verification is not True
    ):
        _fail("BUILDER_DEPENDENCY_COMPOSITION_SOURCE_AUTHORITY_REQUIRED")


def builder_packaging_source_identity(
    binding: BuilderPackagingSourceBinding,
) -> tuple[object, ...]:
    """Return durable identity while excluding call-local publication truth."""

    require_live_builder_packaging_source(binding)
    paths = (
        binding.generation_root,
        binding.site_packages_root,
        binding.wheel_path,
        binding.descriptor_path,
    )
    return (
        *(os.path.normcase(str(path)) for path in paths),
        binding.descriptor_digest,
        binding.generation_id,
        binding.inventory_digest,
        binding.wheel_sha256,
        binding.member_set_digest,
        binding.dependency_tree_digest,
        binding.member_count,
        binding.directory_count,
        binding.expanded_bytes,
    )


def require_same_builder_packaging_source(
    initial: BuilderPackagingSourceBinding,
    final: BuilderPackagingSourceBinding,
) -> None:
    if builder_packaging_source_identity(initial) != builder_packaging_source_identity(final):
        _fail("BUILDER_DEPENDENCY_COMPOSITION_SOURCE_CHANGED")


def require_inert_dependency_runtime(binding: DependencyRuntimeBinding) -> None:
    if type(binding) is not DependencyRuntimeBinding:
        _fail("BUILDER_DEPENDENCY_COMPOSITION_DEPENDENCY_BINDING_INVALID")
    _absolute_paths(
        (binding.generation_root, binding.site_packages_root, binding.descriptor_path),
        "BUILDER_DEPENDENCY_COMPOSITION_DEPENDENCY_BINDING_INVALID",
    )
    digests = (
        binding.descriptor_digest,
        binding.generation_id,
        binding.inventory_digest,
        binding.dependency_tree_digest,
    )
    if any(not is_digest(value) for value in digests):
        _fail("BUILDER_DEPENDENCY_COMPOSITION_DEPENDENCY_BINDING_INVALID")
    _positive_counts(
        (binding.file_count, binding.total_bytes),
        "BUILDER_DEPENDENCY_COMPOSITION_DEPENDENCY_BINDING_INVALID",
    )
    if type(binding.directory_count) is not int or binding.directory_count < 0:
        _fail("BUILDER_DEPENDENCY_COMPOSITION_DEPENDENCY_BINDING_INVALID")
    if (
        binding.artifact_bytes_verified_at_publication is not True
        or binding.write_denial_verified is not False
        or binding.activation_eligible is not False
        or binding.generation_id != binding.dependency_tree_digest
    ):
        _fail("BUILDER_DEPENDENCY_COMPOSITION_DEPENDENCY_BINDING_INVALID")


@dataclass(frozen=True)
class BuilderDependencyCompositionBinding:
    source: BuilderPackagingSourceBinding
    dependency: DependencyRuntimeBinding

    @property
    def public_binding(self) -> Mapping[str, object]:
        result = dict(self.source.public_binding)
        result.update(self.dependency.public_binding)
        result.update(
            {
                "builder_dependency_composition_source_generation_id": (
                    self.source.generation_id
                ),
                "builder_dependency_composition_dependency_generation_id": (
                    self.dependency.generation_id
                ),
                "builder_dependency_composition_dependency_tree_digest": (
                    self.source.dependency_tree_digest
                ),
                "builder_dependency_composition_source_reverified_after_dependency_materialization": True,
                "builder_dependency_composition_dependency_tree_digest_match": True,
                "builder_dependency_composition_sequential_proof_only": True,
            }
        )
        result.update(
            {
                f"builder_dependency_composition_{name}": False
                for name in _FALSE_FIELDS
            }
        )
        return result


@dataclass(frozen=True)
class BuilderDependencyCompositionResult:
    binding: BuilderDependencyCompositionBinding
    source_initial_reused_existing_generation: bool
    dependency_reused_existing_generation: bool
    source_final_reused_existing_generation: bool


def build_builder_dependency_composition_binding(
    *, source: BuilderPackagingSourceBinding,
    dependency: DependencyRuntimeBinding,
) -> BuilderDependencyCompositionBinding:
    require_live_builder_packaging_source(source)
    require_inert_dependency_runtime(dependency)
    if source.dependency_tree_digest != dependency.generation_id:
        _fail("BUILDER_DEPENDENCY_COMPOSITION_TREE_DIGEST_MISMATCH")
    return BuilderDependencyCompositionBinding(source=source, dependency=dependency)


__all__ = [
    "BuilderDependencyCompositionBinding",
    "BuilderDependencyCompositionError",
    "BuilderDependencyCompositionResult",
    "build_builder_dependency_composition_binding",
    "builder_packaging_source_identity",
    "require_inert_dependency_runtime",
    "require_live_builder_packaging_source",
    "require_same_builder_packaging_source",
]
