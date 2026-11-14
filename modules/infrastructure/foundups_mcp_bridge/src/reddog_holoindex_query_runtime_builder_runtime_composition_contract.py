"""Path-free contract for inert builder-runtime composition."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping

from .reddog_holoindex_base_runtime_contract import (
    DESCRIPTOR_NAME as BASE_DESCRIPTOR_NAME,
    PAYLOAD_DIRECTORY,
    BaseRuntimeBinding,
)
from .reddog_holoindex_dependency_runtime_contract import is_digest
from .reddog_holoindex_query_runtime_builder_dependency_composition_contract import (
    BuilderDependencyCompositionBinding,
    build_builder_dependency_composition_binding,
    require_inert_dependency_runtime,
)
from .reddog_holoindex_runtime_composition_contract import (
    DESCRIPTOR_NAME,
    INTERPRETER_RELATIVE_PATH,
    RuntimeCompositionBinding,
)


_FALSE_FIELDS = (
    "source_current_verification_authority_at_return",
    "cross_store_atomicity_verified",
    "simultaneous_snapshot_verified",
    "post_return_immutability_verified",
    "persistent_write_denial_verified",
    "official_provenance_authenticated",
    "signature_verified",
    "installation_performed",
    "import_performed",
    "child_execution_performed",
    "authenticated_producer_verified",
    "process_authority_verified",
    "preimport_loader_authority_verified",
    "abi_compatibility_verified",
    "native_loader_closure_verified",
    "subprocess_closure_verified",
    "exact_runtime_closure_verified",
    "deterministic_effects_verified",
    "write_denial_verified",
    "activation_eligible",
    "a_grade_verified",
    "retrieval_rsi_verified",
)


class BuilderRuntimeCompositionError(RuntimeError):
    """Stable path-free builder-runtime composition failure."""


def _fail(code: str) -> None:
    raise BuilderRuntimeCompositionError(code)


def _approved_absolute_path(value: object) -> bool:
    return (
        isinstance(value, Path)
        and value.is_absolute()
        and value.drive.rstrip(":").upper() in {"O", "E"}
    )


def _positive_counts(values: tuple[object, ...]) -> bool:
    return all(type(value) is int and value > 0 for value in values)


def _base_runtime_truth(binding: object) -> None:
    if type(binding) is not BaseRuntimeBinding:
        _fail("BUILDER_RUNTIME_COMPOSITION_RUNTIME_BINDING_INVALID")
    paths = (
        binding.generation_root, binding.base_prefix_root, binding.descriptor_path,
    )
    digests = (
        binding.descriptor_digest, binding.generation_id,
        binding.inventory_digest, binding.base_runtime_tree_digest,
    )
    false_claims = (
        binding.native_loader_closure_verified,
        binding.deterministic_effects_verified, binding.signature_verified,
        binding.write_denial_verified, binding.activation_eligible,
        binding.exact_runtime_closure_verified,
    )
    if (
        any(not _approved_absolute_path(path) for path in paths)
        or any(not is_digest(value) for value in digests)
        or not _positive_counts((binding.file_count, binding.total_bytes))
        or type(binding.directory_count) is not int
        or binding.directory_count < 0
        or binding.artifact_bytes_verified_at_publication is not True
        or any(value is not False for value in false_claims)
        or binding.generation_id != binding.base_runtime_tree_digest
        or binding.base_prefix_root != binding.generation_root / PAYLOAD_DIRECTORY
        or binding.descriptor_path != binding.generation_root / BASE_DESCRIPTOR_NAME
    ):
        _fail("BUILDER_RUNTIME_COMPOSITION_RUNTIME_BINDING_INVALID")


def require_inert_runtime_composition(binding: RuntimeCompositionBinding) -> None:
    """Require descriptor-authenticated inert topology without upgrading it."""

    if type(binding) is not RuntimeCompositionBinding:
        _fail("BUILDER_RUNTIME_COMPOSITION_RUNTIME_BINDING_INVALID")
    paths = (
        binding.generation_root, binding.descriptor_path, binding.interpreter_path,
        binding.site_packages_root,
    )
    digests = (
        binding.descriptor_digest, binding.generation_id,
        binding.interpreter_content_digest,
    )
    false_claims = (
        binding.abi_compatibility_verified,
        binding.native_loader_closure_verified,
        binding.deterministic_effects_verified,
        binding.preimport_bootstrap_verified, binding.signature_verified,
        binding.write_denial_verified, binding.activation_eligible,
        binding.exact_runtime_closure_verified,
    )
    if (
        any(not _approved_absolute_path(path) for path in paths)
        or any(not is_digest(value) for value in digests)
        or type(binding.interpreter_size) is not int
        or binding.interpreter_size <= 0
        or binding.artifact_bytes_independently_reverified is not True
        or any(value is not False for value in false_claims)
        or binding.descriptor_path != binding.generation_root / DESCRIPTOR_NAME
        or binding.interpreter_path
        != binding.base_runtime.base_prefix_root / INTERPRETER_RELATIVE_PATH
        or binding.site_packages_root
        != binding.dependency_runtime.site_packages_root
    ):
        _fail("BUILDER_RUNTIME_COMPOSITION_RUNTIME_BINDING_INVALID")
    _base_runtime_truth(binding.base_runtime)


def _dependency_identity(binding) -> tuple[object, ...]:
    return (
        *(os.path.normcase(str(path.absolute())) for path in (
            binding.generation_root, binding.site_packages_root,
            binding.descriptor_path,
        )),
        binding.descriptor_digest, binding.generation_id,
        binding.inventory_digest, binding.dependency_tree_digest,
        binding.file_count, binding.directory_count, binding.total_bytes,
        binding.artifact_bytes_verified_at_publication,
        binding.write_denial_verified, binding.activation_eligible,
    )


def require_exact_dependency_identity(
    builder: BuilderDependencyCompositionBinding,
    runtime: RuntimeCompositionBinding,
) -> None:
    if _dependency_identity(builder.dependency) != _dependency_identity(
        runtime.dependency_runtime
    ):
        _fail("BUILDER_RUNTIME_COMPOSITION_DEPENDENCY_MISMATCH")
    require_inert_dependency_runtime(runtime.dependency_runtime)


def require_builder_dependency_composition(
    binding: BuilderDependencyCompositionBinding,
) -> None:
    if type(binding) is not BuilderDependencyCompositionBinding:
        _fail("BUILDER_RUNTIME_COMPOSITION_BUILDER_DEPENDENCY_FAILED")
    validation_failed = False
    try:
        observed = build_builder_dependency_composition_binding(
            source=binding.source, dependency=binding.dependency,
        )
    except Exception:
        validation_failed = True
        observed = None
    if validation_failed:
        _fail("BUILDER_RUNTIME_COMPOSITION_BUILDER_DEPENDENCY_FAILED")
    if observed != binding:
        _fail("BUILDER_RUNTIME_COMPOSITION_BUILDER_DEPENDENCY_FAILED")


@dataclass(frozen=True)
class BuilderRuntimeCompositionBinding:
    builder_dependency: BuilderDependencyCompositionBinding
    runtime_composition: RuntimeCompositionBinding

    @property
    def public_binding(self) -> Mapping[str, object]:
        source = self.builder_dependency.source
        dependency = self.builder_dependency.dependency
        runtime = self.runtime_composition
        result = {
            "builder_runtime_composition_source_generation_id": source.generation_id,
            "builder_runtime_composition_source_descriptor_digest": (
                source.descriptor_digest
            ),
            "builder_runtime_composition_source_inventory_digest": (
                source.inventory_digest
            ),
            "builder_runtime_composition_wheel_sha256": source.wheel_sha256,
            "builder_runtime_composition_member_set_digest": source.member_set_digest,
            "builder_runtime_composition_dependency_generation_id": (
                dependency.generation_id
            ),
            "builder_runtime_composition_dependency_descriptor_digest": (
                dependency.descriptor_digest
            ),
            "builder_runtime_composition_dependency_inventory_digest": (
                dependency.inventory_digest
            ),
            "builder_runtime_composition_dependency_tree_digest": (
                dependency.dependency_tree_digest
            ),
            "builder_runtime_composition_runtime_generation_id": runtime.generation_id,
            "builder_runtime_composition_runtime_descriptor_digest": (
                runtime.descriptor_digest
            ),
            "builder_runtime_composition_dependency_identity_verified": True,
            "builder_runtime_composition_existing_verifiers_reused": True,
            "builder_runtime_composition_sequential_proof_only": True,
            "builder_runtime_composition_inert_only": True,
        }
        result.update(runtime.base_runtime.public_binding)
        result.update(runtime.public_binding)
        result.update({f"builder_runtime_composition_{name}": False
                       for name in _FALSE_FIELDS})
        return result


@dataclass(frozen=True)
class BuilderRuntimeCompositionResult:
    binding: BuilderRuntimeCompositionBinding
    source_initial_reused_existing_generation: bool
    dependency_reused_existing_generation: bool
    source_final_reused_existing_generation: bool
    runtime_composition_reused_existing_generation: bool

    @property
    def builder_dependency_reused_existing_generation(self) -> bool:
        return all((
            self.source_initial_reused_existing_generation,
            self.dependency_reused_existing_generation,
            self.source_final_reused_existing_generation,
        ))


def build_builder_runtime_composition_binding(
    *, builder_dependency: BuilderDependencyCompositionBinding,
    runtime_composition: RuntimeCompositionBinding,
) -> BuilderRuntimeCompositionBinding:
    require_builder_dependency_composition(builder_dependency)
    if type(runtime_composition) is not RuntimeCompositionBinding:
        _fail("BUILDER_RUNTIME_COMPOSITION_RUNTIME_BINDING_INVALID")
    require_exact_dependency_identity(builder_dependency, runtime_composition)
    require_inert_runtime_composition(runtime_composition)
    return BuilderRuntimeCompositionBinding(builder_dependency, runtime_composition)


__all__ = [
    "BuilderRuntimeCompositionBinding", "BuilderRuntimeCompositionError",
    "BuilderRuntimeCompositionResult", "build_builder_runtime_composition_binding",
    "require_exact_dependency_identity", "require_inert_runtime_composition",
]
