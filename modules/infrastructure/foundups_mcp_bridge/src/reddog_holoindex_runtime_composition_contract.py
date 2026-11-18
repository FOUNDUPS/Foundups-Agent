"""Strict path-free contract for one inert HoloIndex runtime composition."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .reddog_holoindex_base_runtime_contract import BaseRuntimeBinding
from .reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeBinding,
    canonical_json_bytes,
    digest_bytes,
    is_digest,
)


DESCRIPTOR_SCHEMA_VERSION = "holoindex_runtime_composition_descriptor.v1"
DESCRIPTOR_NAME = "holoindex_runtime_composition_descriptor.json"
PLATFORM_TAG = "windows"
BASE_COMPONENT_ROLE = "python_base_runtime"
DEPENDENCY_COMPONENT_ROLE = "python_dependency_runtime"
INTERPRETER_RELATIVE_PATH = "python.exe"
SITE_PACKAGES_RELATIVE_PATH = "site-packages"
ISOLATION_FLAGS = ("-I", "-S", "-B")

_DESCRIPTOR_KEYS = frozenset(
    {
        "schema_version",
        "status",
        "generation_id",
        "platform_tag",
        "base_runtime",
        "dependency_runtime",
        "launch_topology",
        "artifact_bytes_independently_reverified",
        "abi_compatibility_verified",
        "native_loader_closure_verified",
        "deterministic_effects_verified",
        "preimport_bootstrap_verified",
        "signature_verified",
        "write_denial_verified",
        "activation_eligible",
        "exact_runtime_closure_verified",
    }
)
_COMPONENT_KEYS = frozenset(
    {
        "role",
        "generation_id",
        "descriptor_digest",
        "inventory_digest",
        "tree_digest",
        "file_count",
        "directory_count",
        "total_bytes",
    }
)
_LAUNCH_KEYS = frozenset(
    {
        "interpreter_component_role",
        "interpreter_relative_path",
        "interpreter_content_digest",
        "interpreter_size",
        "dependency_component_role",
        "site_packages_relative_path",
        "isolation_flags",
    }
)


class RuntimeCompositionContractError(RuntimeError):
    """Stable fail-closed composition-contract error."""


def _fail(code: str) -> None:
    raise RuntimeCompositionContractError(code)


@dataclass(frozen=True)
class RuntimeCompositionLimits:
    max_descriptor_bytes: int = 32 * 1024

    def validate(self) -> None:
        if type(self.max_descriptor_bytes) is not int or self.max_descriptor_bytes <= 0:
            _fail("RUNTIME_COMPOSITION_LIMIT_INVALID")


@dataclass(frozen=True)
class RuntimeCompositionBinding:
    generation_root: Path
    descriptor_path: Path
    descriptor_digest: str
    generation_id: str
    base_runtime: BaseRuntimeBinding
    dependency_runtime: DependencyRuntimeBinding
    interpreter_path: Path
    interpreter_content_digest: str
    interpreter_size: int
    site_packages_root: Path
    artifact_bytes_independently_reverified: bool
    abi_compatibility_verified: bool
    native_loader_closure_verified: bool
    deterministic_effects_verified: bool
    preimport_bootstrap_verified: bool
    signature_verified: bool
    write_denial_verified: bool
    activation_eligible: bool
    exact_runtime_closure_verified: bool

    @property
    def public_binding(self) -> Mapping[str, object]:
        """Return the path-free evidence allowed across trust boundaries."""

        return {
            "runtime_composition_generation_id": self.generation_id,
            "runtime_composition_descriptor_digest": self.descriptor_digest,
            "base_runtime_generation_id": self.base_runtime.generation_id,
            "base_runtime_descriptor_digest": self.base_runtime.descriptor_digest,
            "base_runtime_inventory_digest": self.base_runtime.inventory_digest,
            "base_runtime_tree_digest": self.base_runtime.base_runtime_tree_digest,
            "dependency_runtime_generation_id": self.dependency_runtime.generation_id,
            "dependency_runtime_descriptor_digest": (
                self.dependency_runtime.descriptor_digest
            ),
            "dependency_runtime_inventory_digest": (
                self.dependency_runtime.inventory_digest
            ),
            "dependency_runtime_tree_digest": (
                self.dependency_runtime.dependency_tree_digest
            ),
            "interpreter_content_digest": self.interpreter_content_digest,
            "artifact_bytes_independently_reverified": (
                self.artifact_bytes_independently_reverified
            ),
            "abi_compatibility_verified": self.abi_compatibility_verified,
            "native_loader_closure_verified": self.native_loader_closure_verified,
            "deterministic_effects_verified": self.deterministic_effects_verified,
            "preimport_bootstrap_verified": self.preimport_bootstrap_verified,
            "signature_verified": self.signature_verified,
            "write_denial_verified": self.write_denial_verified,
            "activation_eligible": self.activation_eligible,
            "exact_runtime_closure_verified": self.exact_runtime_closure_verified,
        }


@dataclass(frozen=True)
class RuntimeCompositionMaterializationResult:
    binding: RuntimeCompositionBinding
    reused_existing_generation: bool


def runtime_composition_descriptor(
    *,
    base_runtime: BaseRuntimeBinding,
    dependency_runtime: DependencyRuntimeBinding,
    interpreter_content_digest: str,
    interpreter_size: int,
) -> dict[str, Any]:
    """Build the sole valid inert descriptor for two verified components."""

    base = _base_component(base_runtime)
    dependency = _dependency_component(dependency_runtime)
    launch = _launch_topology(interpreter_content_digest, interpreter_size)
    identity = _identity_projection(base, dependency, launch)
    return {
        **identity,
        "generation_id": digest_bytes(canonical_json_bytes(identity)),
        "status": "INERT",
        "artifact_bytes_independently_reverified": True,
        "abi_compatibility_verified": False,
        "native_loader_closure_verified": False,
        "deterministic_effects_verified": False,
        "preimport_bootstrap_verified": False,
        "signature_verified": False,
        "write_denial_verified": False,
        "activation_eligible": False,
        "exact_runtime_closure_verified": False,
    }


def validate_runtime_composition_descriptor(value: object) -> dict[str, Any]:
    """Validate exact shape, identity, ordering, types, and truthful non-claims."""

    source = _exact_mapping(
        value, _DESCRIPTOR_KEYS, "RUNTIME_COMPOSITION_DESCRIPTOR_INVALID"
    )
    if (
        source.get("schema_version") != DESCRIPTOR_SCHEMA_VERSION
        or source.get("status") != "INERT"
        or source.get("platform_tag") != PLATFORM_TAG
    ):
        _fail("RUNTIME_COMPOSITION_DESCRIPTOR_INVALID")
    base = _component(
        source.get("base_runtime"), BASE_COMPONENT_ROLE,
        "RUNTIME_COMPOSITION_BASE_BINDING_INVALID",
    )
    dependency = _component(
        source.get("dependency_runtime"), DEPENDENCY_COMPONENT_ROLE,
        "RUNTIME_COMPOSITION_DEPENDENCY_BINDING_INVALID",
    )
    launch = _validated_launch(source.get("launch_topology"))
    identity = _identity_projection(base, dependency, launch)
    if source.get("generation_id") != digest_bytes(canonical_json_bytes(identity)):
        _fail("RUNTIME_COMPOSITION_GENERATION_ID_INVALID")
    expected_truth = {
        "artifact_bytes_independently_reverified": True,
        "abi_compatibility_verified": False,
        "native_loader_closure_verified": False,
        "deterministic_effects_verified": False,
        "preimport_bootstrap_verified": False,
        "signature_verified": False,
        "write_denial_verified": False,
        "activation_eligible": False,
        "exact_runtime_closure_verified": False,
    }
    if any(source.get(name) is not expected for name, expected in expected_truth.items()):
        _fail("RUNTIME_COMPOSITION_DESCRIPTOR_TRUTH_INVALID")
    return dict(source)


def _base_component(binding: BaseRuntimeBinding) -> dict[str, Any]:
    return {
        "role": BASE_COMPONENT_ROLE,
        "generation_id": binding.generation_id,
        "descriptor_digest": binding.descriptor_digest,
        "inventory_digest": binding.inventory_digest,
        "tree_digest": binding.base_runtime_tree_digest,
        "file_count": binding.file_count,
        "directory_count": binding.directory_count,
        "total_bytes": binding.total_bytes,
    }


def _dependency_component(binding: DependencyRuntimeBinding) -> dict[str, Any]:
    return {
        "role": DEPENDENCY_COMPONENT_ROLE,
        "generation_id": binding.generation_id,
        "descriptor_digest": binding.descriptor_digest,
        "inventory_digest": binding.inventory_digest,
        "tree_digest": binding.dependency_tree_digest,
        "file_count": binding.file_count,
        "directory_count": binding.directory_count,
        "total_bytes": binding.total_bytes,
    }


def _launch_topology(digest: str, size: int) -> dict[str, Any]:
    if not is_digest(digest) or type(size) is not int or size <= 0:
        _fail("RUNTIME_COMPOSITION_INTERPRETER_BINDING_INVALID")
    return {
        "interpreter_component_role": BASE_COMPONENT_ROLE,
        "interpreter_relative_path": INTERPRETER_RELATIVE_PATH,
        "interpreter_content_digest": digest,
        "interpreter_size": size,
        "dependency_component_role": DEPENDENCY_COMPONENT_ROLE,
        "site_packages_relative_path": SITE_PACKAGES_RELATIVE_PATH,
        "isolation_flags": list(ISOLATION_FLAGS),
    }


def _identity_projection(
    base: Mapping[str, Any],
    dependency: Mapping[str, Any],
    launch: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": DESCRIPTOR_SCHEMA_VERSION,
        "platform_tag": PLATFORM_TAG,
        "base_runtime": dict(base),
        "dependency_runtime": dict(dependency),
        "launch_topology": dict(launch),
    }


def _component(value: object, role: str, error: str) -> dict[str, Any]:
    source = _exact_mapping(value, _COMPONENT_KEYS, error)
    if source.get("role") != role:
        _fail(error)
    for name in ("generation_id", "descriptor_digest", "inventory_digest", "tree_digest"):
        if not is_digest(source.get(name)):
            _fail(error)
    for name in ("file_count", "directory_count", "total_bytes"):
        if type(source.get(name)) is not int or int(source[name]) < 0:
            _fail(error)
    if source["file_count"] == 0 or source["total_bytes"] == 0:
        _fail(error)
    return dict(source)


def _validated_launch(value: object) -> dict[str, Any]:
    source = _exact_mapping(
        value, _LAUNCH_KEYS, "RUNTIME_COMPOSITION_LAUNCH_TOPOLOGY_INVALID"
    )
    if (
        source.get("interpreter_component_role") != BASE_COMPONENT_ROLE
        or source.get("interpreter_relative_path") != INTERPRETER_RELATIVE_PATH
        or source.get("dependency_component_role") != DEPENDENCY_COMPONENT_ROLE
        or source.get("site_packages_relative_path") != SITE_PACKAGES_RELATIVE_PATH
        or source.get("isolation_flags") != list(ISOLATION_FLAGS)
        or not is_digest(source.get("interpreter_content_digest"))
        or type(source.get("interpreter_size")) is not int
        or int(source["interpreter_size"]) <= 0
    ):
        _fail("RUNTIME_COMPOSITION_LAUNCH_TOPOLOGY_INVALID")
    return dict(source)


def _exact_mapping(value: object, keys: frozenset[str], error: str) -> Mapping[str, Any]:
    if type(value) is not dict or frozenset(value) != keys:
        _fail(error)
    return value


__all__ = [
    "DESCRIPTOR_NAME",
    "DESCRIPTOR_SCHEMA_VERSION",
    "RuntimeCompositionBinding",
    "RuntimeCompositionContractError",
    "RuntimeCompositionLimits",
    "RuntimeCompositionMaterializationResult",
    "runtime_composition_descriptor",
    "validate_runtime_composition_descriptor",
]
