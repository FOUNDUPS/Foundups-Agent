"""Single build/reproof boundary for inert Holo query-runtime candidates."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat
from typing import Any, Callable, Mapping, Sequence

from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    confined_file_identity,
    secure_digest_confined_file_impl,
    secure_read_confined_bytes_impl,
)
from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    require_unnamed_data_stream_only,
)

from .reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    dependency_tree_digest,
    digest_bytes,
    validate_inventory as validate_dependency_inventory,
)
from .reddog_holoindex_base_runtime_contract import (
    DESCRIPTOR_NAME as BASE_DESCRIPTOR_NAME,
    PAYLOAD_DIRECTORY,
)
from .reddog_holoindex_dependency_runtime_contract import (
    DESCRIPTOR_NAME as DEPENDENCY_DESCRIPTOR_NAME,
)
from .reddog_holoindex_query_distribution_graph import (
    DistributionGraphLimits,
    DistributionProjection,
    derive_distribution_projection,
)
from .reddog_holoindex_query_runtime_candidate_contract import (
    CandidateLimits,
    candidate_inventory,
)
from .reddog_holoindex_query_runtime_candidate_descriptor import (
    candidate_descriptor,
    validate_candidate_pair,
)
from .reddog_holoindex_query_runtime_candidate_inputs import (
    CandidateDeclarations,
    CandidateInputError,
    bounded_candidate_declarations,
    bounded_composition_inputs,
    bounded_source_inputs,
)
from .reddog_holoindex_query_runtime_candidate_source import (
    CandidateSourceAuthority,
    verify_candidate_source_authority,
)
from .reddog_holoindex_runtime_composition_contract import (
    DESCRIPTOR_NAME as COMPOSITION_DESCRIPTOR_NAME,
    INTERPRETER_RELATIVE_PATH,
    SITE_PACKAGES_RELATIVE_PATH,
    RuntimeCompositionBinding,
)
from .reddog_holoindex_runtime_composition_descriptor import (
    verify_runtime_composition_generation,
)


class CandidateBindingError(RuntimeError):
    """Stable fail-closed candidate build or reproof error."""


def _fail(code: str) -> None:
    raise CandidateBindingError(code)


@dataclass(frozen=True)
class BoundCandidateEvidence:
    inventory: Mapping[str, Any]
    descriptor: Mapping[str, Any]


@dataclass(frozen=True)
class CandidateBindingLimits:
    max_binding_arguments: int = 16

    def validate(self) -> None:
        if type(self.max_binding_arguments) is not int or not (
            1 <= self.max_binding_arguments <= 16
        ):
            _fail("QUERY_RUNTIME_CANDIDATE_BINDING_LIMIT_INVALID")


@dataclass(frozen=True)
class _CandidateBindingDependencies:
    verify_composition: Callable[..., RuntimeCompositionBinding] = (
        verify_runtime_composition_generation
    )
    verify_source: Callable[..., CandidateSourceAuthority] = (
        verify_candidate_source_authority
    )


def build_bound_candidate(
    *, composition_kwargs: Mapping[str, Any],
    source_authority_kwargs: Mapping[str, Any],
    dependency_inventory: Mapping[str, Any],
    root_requirements: Sequence[Mapping[str, Any]],
    module_origins: Sequence[str],
    marker_environment: Mapping[str, str],
    dynamic_surfaces: Sequence[Mapping[str, Any]],
    observed_import_trace: Mapping[str, Any],
    temporary_runtime_volume: str,
    declared_subprocess_paths: Sequence[str] = (),
    graph_limits: DistributionGraphLimits = DistributionGraphLimits(),
    candidate_limits: CandidateLimits = CandidateLimits(),
    binding_limits: CandidateBindingLimits = CandidateBindingLimits(),
) -> BoundCandidateEvidence:
    """Reject governed builds until an exact evidence-builder runtime is bound."""

    _fail("QUERY_RUNTIME_CANDIDATE_BUILDER_RUNTIME_UNBOUND")


def _build_bound_candidate_for_test(
    *, composition_kwargs: Mapping[str, Any],
    source_authority_kwargs: Mapping[str, Any],
    dependency_inventory: Mapping[str, Any],
    root_requirements: Sequence[Mapping[str, Any]], module_origins: Sequence[str],
    marker_environment: Mapping[str, str],
    dynamic_surfaces: Sequence[Mapping[str, Any]],
    observed_import_trace: Mapping[str, Any], temporary_runtime_volume: str,
    declared_subprocess_paths: Sequence[str] = (),
    graph_limits: DistributionGraphLimits = DistributionGraphLimits(),
    candidate_limits: CandidateLimits = CandidateLimits(),
    binding_limits: CandidateBindingLimits = CandidateBindingLimits(),
    dependencies: _CandidateBindingDependencies,
) -> BoundCandidateEvidence:
    """Reprove source/composition around one inert candidate derivation."""

    composition_inputs, source_inputs, declarations = _bounded_build_inputs(
        composition_kwargs, source_authority_kwargs, root_requirements,
        dynamic_surfaces, module_origins, declared_subprocess_paths,
        candidate_limits, graph_limits, binding_limits,
    )
    source_before = _verify_source(dependencies, source_inputs)
    _bind_source_repo_root(source_before, composition_inputs)
    before = _verify_composition(dependencies, composition_inputs)
    validated_dependency, surfaces = _validated_inputs(
        before, dependency_inventory, declarations,
    )
    files = validated_dependency["files"]
    projection = _derive_projection(
        before, files, declarations.roots, declarations.origins,
        marker_environment, declarations.subprocesses, graph_limits,
    )
    _reject_transport_conflict(projection)
    evidence = _candidate_evidence(
        before, source_before, declarations.digest, projection,
        list(declarations.roots),
        surfaces, observed_import_trace, marker_environment,
        temporary_runtime_volume, candidate_limits,
    )
    after = _verify_composition(dependencies, composition_inputs)
    source_after = _verify_source(dependencies, source_inputs)
    if source_after != source_before or after != before:
        _fail("QUERY_RUNTIME_CANDIDATE_AUTHORITY_MUTATED_DURING_BUILD")
    return evidence


def _bounded_build_inputs(
    composition_kwargs: Mapping[str, Any], source_authority_kwargs: Mapping[str, Any],
    root_requirements: Sequence[Mapping[str, Any]],
    dynamic_surfaces: Sequence[Mapping[str, Any]], module_origins: Sequence[str],
    subprocesses: Sequence[str], candidate_limits: CandidateLimits,
    graph_limits: DistributionGraphLimits, binding_limits: CandidateBindingLimits,
) -> tuple[dict[str, Any], dict[str, Any], CandidateDeclarations]:
    try:
        candidate_limits.validate()
    except Exception as exc:
        raise CandidateBindingError("QUERY_RUNTIME_CANDIDATE_LIMIT_INVALID") from exc
    try:
        graph_limits.validate()
    except Exception as exc:
        raise CandidateBindingError("QUERY_DISTRIBUTION_GRAPH_LIMIT_INVALID") from exc
    binding_limits.validate()
    try:
        composition = bounded_composition_inputs(
            composition_kwargs, binding_limits.max_binding_arguments,
        )
        source = bounded_source_inputs(source_authority_kwargs)
        declarations = bounded_candidate_declarations(
            root_requirements, dynamic_surfaces, module_origins, subprocesses,
            candidate_limits, graph_limits,
        )
    except CandidateInputError as exc:
        raise CandidateBindingError(str(exc)) from exc
    return composition, source, declarations


def _bind_source_repo_root(
    source: CandidateSourceAuthority, composition_inputs: Mapping[str, Any],
) -> None:
    try:
        expected = source.repo_root.resolve(strict=True)
        roots = tuple(Path(value).absolute() for value in composition_inputs["repo_roots"])
    except (KeyError, OSError, TypeError):
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_REPO_ROOT_UNBOUND")
    normalized = os.path.normcase(str(expected))
    if (
        len(roots) != 1
        or sum(os.path.normcase(str(root)) == normalized for root in roots) != 1
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_REPO_ROOT_UNBOUND")


def _verify_composition(
    dependencies: _CandidateBindingDependencies, inputs: Mapping[str, Any],
) -> RuntimeCompositionBinding:
    try:
        return dependencies.verify_composition(**dict(inputs))
    except Exception as exc:
        raise CandidateBindingError(
            "QUERY_RUNTIME_CANDIDATE_COMPOSITION_VERIFICATION_FAILED"
        ) from exc


def _verify_source(
    dependencies: _CandidateBindingDependencies, inputs: Mapping[str, Any],
) -> CandidateSourceAuthority:
    try:
        return dependencies.verify_source(**dict(inputs))
    except Exception as exc:
        raise CandidateBindingError(
            "QUERY_RUNTIME_CANDIDATE_SOURCE_VERIFICATION_FAILED"
        ) from exc


def _validated_inputs(
    composition: RuntimeCompositionBinding, dependency_inventory: Mapping[str, Any],
    declarations: CandidateDeclarations,
) -> tuple[dict[str, Any], list[Mapping[str, Any]]]:
    _composition_truth(composition)
    dependency = validate_dependency_inventory(dependency_inventory)
    _bind_dependency_inventory(composition, dependency)
    surfaces = [
        dict(row, declaration_digest=declarations.digest)
        for row in declarations.raw_surfaces
    ]
    return dependency, surfaces


def _derive_projection(
    composition: RuntimeCompositionBinding, files: list[Mapping[str, Any]],
    roots: list[dict[str, Any]], module_origins: Sequence[str],
    marker_environment: Mapping[str, str], declared_subprocess_paths: Sequence[str],
    limits: DistributionGraphLimits,
) -> DistributionProjection:
    by_path = {str(row["path"]).casefold(): row for row in files}
    return derive_distribution_projection(
        inventory_rows=files,
        read_bytes=_confined_reader(
            composition.dependency_runtime.site_packages_root, by_path,
            limits.max_selected_file_bytes,
        ),
        root_requirements=roots,
        module_origins=module_origins,
        marker_environment=marker_environment,
        declared_subprocess_paths=declared_subprocess_paths,
        limits=limits,
    )


def _candidate_evidence(
    composition: RuntimeCompositionBinding, source: CandidateSourceAuthority,
    declaration_digest: str, projection: DistributionProjection,
    roots: list[dict[str, Any]],
    surfaces: list[Mapping[str, Any]], observed_import_trace: Mapping[str, Any],
    marker_environment: Mapping[str, str], temporary_runtime_volume: str,
    limits: CandidateLimits,
) -> BoundCandidateEvidence:
    inventory = candidate_inventory(
        runtime_composition={
            "generation_id": composition.generation_id,
            "descriptor_digest": composition.descriptor_digest,
        },
        backend_manifest_digest=source.backend_manifest_digest,
        source_authority=source.public_binding,
        declaration_digest=declaration_digest,
        projection=projection,
        runtime_volumes=_runtime_volumes(composition, temporary_runtime_volume),
        launch_dialect=_launch_dialect(marker_environment),
        components=_components(composition),
        root_requirements=roots,
        dynamic_surfaces=surfaces,
        observed_import_trace=observed_import_trace,
        limits=limits,
    )
    descriptor = candidate_descriptor(inventory, limits)
    validate_candidate_pair(inventory, descriptor, limits)
    return BoundCandidateEvidence(inventory, descriptor)


def reprove_bound_candidate(
    *, expected_inventory: Mapping[str, Any],
    expected_descriptor: Mapping[str, Any],
    **build_inputs: Any,
) -> BoundCandidateEvidence:
    """Reject governed reproof until an exact evidence-builder runtime is bound."""

    _fail("QUERY_RUNTIME_CANDIDATE_BUILDER_RUNTIME_UNBOUND")


def _reprove_bound_candidate_for_test(
    *, expected_inventory: Mapping[str, Any],
    expected_descriptor: Mapping[str, Any], build_inputs: Mapping[str, Any],
    dependencies: _CandidateBindingDependencies,
) -> BoundCandidateEvidence:
    observed = _build_bound_candidate_for_test(
        **dict(build_inputs), dependencies=dependencies,
    )
    if observed.inventory != expected_inventory or observed.descriptor != expected_descriptor:
        _fail("QUERY_RUNTIME_CANDIDATE_REPROOF_MISMATCH")
    return observed


def _composition_truth(composition: RuntimeCompositionBinding) -> None:
    if type(composition) is not RuntimeCompositionBinding:
        _fail("QUERY_RUNTIME_CANDIDATE_COMPOSITION_INVALID")
    expected = {
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
    if any(getattr(composition, name) is not value for name, value in expected.items()):
        _fail("QUERY_RUNTIME_CANDIDATE_COMPOSITION_TRUTH_INVALID")
    base, dependency = composition.base_runtime, composition.dependency_runtime
    paths = (
        composition.generation_root, composition.descriptor_path,
        base.generation_root, base.base_prefix_root, base.descriptor_path,
        composition.interpreter_path, dependency.generation_root,
        dependency.descriptor_path, dependency.site_packages_root,
        composition.site_packages_root,
    )
    if any(not _approved_absolute_path(path) for path in paths):
        _fail("QUERY_RUNTIME_CANDIDATE_VOLUME_INVALID")
    if (
        composition.descriptor_path
        != composition.generation_root / COMPOSITION_DESCRIPTOR_NAME
        or base.base_prefix_root != base.generation_root / PAYLOAD_DIRECTORY
        or base.descriptor_path != base.generation_root / BASE_DESCRIPTOR_NAME
        or composition.interpreter_path
        != base.base_prefix_root / INTERPRETER_RELATIVE_PATH
        or dependency.descriptor_path
        != dependency.generation_root / DEPENDENCY_DESCRIPTOR_NAME
        or dependency.site_packages_root
        != dependency.generation_root / SITE_PACKAGES_RELATIVE_PATH
        or composition.site_packages_root != dependency.site_packages_root
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_COMPOSITION_INVALID")


def _bind_dependency_inventory(
    composition: RuntimeCompositionBinding, inventory: Mapping[str, Any],
) -> None:
    dependency = composition.dependency_runtime
    rows, directories = inventory["files"], inventory["directories"]
    if (
        digest_bytes(canonical_json_bytes(inventory)) != dependency.inventory_digest
        or dependency_tree_digest(directories, rows) != dependency.dependency_tree_digest
        or len(rows) != dependency.file_count
        or len(directories) != dependency.directory_count
        or sum(row["size"] for row in rows) != dependency.total_bytes
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_DEPENDENCY_BINDING_MISMATCH")


def _reject_transport_conflict(projection: DistributionProjection) -> None:
    selected = {str(row.get("name") or "") for row in projection.distributions}
    if selected & {"fastapi", "uvicorn"}:
        _fail("QUERY_RUNTIME_CANDIDATE_STDLIB_TRANSPORT_CONFLICT")


def _runtime_volumes(
    composition: RuntimeCompositionBinding, temporary_runtime_volume: str,
) -> dict[str, str]:
    if type(temporary_runtime_volume) is not str or temporary_runtime_volume not in {"O", "E"}:
        _fail("QUERY_RUNTIME_CANDIDATE_VOLUME_INVALID")
    return {
        "base_runtime": _approved_volume(composition.base_runtime.generation_root),
        "dependency_runtime": _approved_volume(composition.dependency_runtime.generation_root),
        "temporary_runtime": _approved_volume(Path(f"{temporary_runtime_volume}:/candidate")),
    }


def _approved_volume(path: Path) -> str:
    if not _approved_absolute_path(path):
        _fail("QUERY_RUNTIME_CANDIDATE_VOLUME_INVALID")
    return path.drive.rstrip(":").upper()


def _approved_absolute_path(value: object) -> bool:
    return bool(
        isinstance(value, Path) and value.is_absolute()
        and value.drive.rstrip(":").upper() in {"O", "E"}
    )


def _launch_dialect(marker_environment: Mapping[str, str]) -> dict[str, Any]:
    return {
        "implementation": "cpython",
        "python_full_version": str(marker_environment.get("python_full_version") or ""),
        "platform_tag": "win_amd64", "flags": ["-I", "-S", "-B"],
        "standalone_base_runtime_required": True, "stdlib_transport_required": True,
        "site_import_allowed": False, "pth_processing_allowed": False,
    }


def _components(composition: RuntimeCompositionBinding) -> dict[str, str]:
    return {
        "base_generation_id": composition.base_runtime.generation_id,
        "base_descriptor_digest": composition.base_runtime.descriptor_digest,
        "base_tree_digest": composition.base_runtime.base_runtime_tree_digest,
        "dependency_generation_id": composition.dependency_runtime.generation_id,
        "dependency_descriptor_digest": composition.dependency_runtime.descriptor_digest,
        "dependency_inventory_digest": composition.dependency_runtime.inventory_digest,
        "dependency_tree_digest": composition.dependency_runtime.dependency_tree_digest,
    }


def _confined_reader(
    root: Path, inventory: Mapping[str, Mapping[str, Any]], maximum: int,
):
    def read(path: str) -> bytes:
        row = inventory.get(path.casefold())
        if row is None or row["size"] > maximum:
            _fail("QUERY_RUNTIME_CANDIDATE_PAYLOAD_INVALID")
        target = root / path
        try:
            before = os.lstat(target)
            identity = confined_file_identity(before)
            if not stat.S_ISREG(before.st_mode) or before.st_size != row["size"]:
                _fail("QUERY_RUNTIME_CANDIDATE_PAYLOAD_INVALID")
            proof = secure_digest_confined_file_impl(
                target, allowed_root=root, expected_identity=identity, max_bytes=maximum,
            )
            payload, cursor = secure_read_confined_bytes_impl(
                target, allowed_root=root, max_bytes=int(before.st_size) + 1,
            )
            require_unnamed_data_stream_only(target)
            stable = confined_file_identity(os.lstat(target)) == identity
        except CandidateBindingError:
            raise
        except Exception:
            _fail("QUERY_RUNTIME_CANDIDATE_PAYLOAD_UNAVAILABLE")
        if (
            cursor != before.st_size or len(payload) != before.st_size or not stable
            or proof.digest != row["sha256"] or digest_bytes(payload) != row["sha256"]
        ):
            _fail("QUERY_RUNTIME_CANDIDATE_PAYLOAD_CHANGED")
        return payload
    return read


__all__ = [
    "BoundCandidateEvidence", "CandidateBindingError", "CandidateBindingLimits",
    "build_bound_candidate", "reprove_bound_candidate",
]
