"""Independent verification for one inert HoloIndex runtime composition."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    confined_file_identity,
    secure_digest_confined_file_impl,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_text,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)
from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    require_unnamed_data_stream_only,
)

from .reddog_holoindex_acceptance_guards import (
    AcceptanceGuardError,
    StoreProof,
    prove_existing_isolated_store,
    verify_store_proof,
)
from .reddog_holoindex_base_runtime_contract import (
    INVENTORY_NAME as BASE_INVENTORY_NAME,
    BaseRuntimeLimits,
    parse_canonical_json as parse_base_canonical_json,
    validate_inventory as validate_base_inventory,
)
from .reddog_holoindex_base_runtime_descriptor import (
    BaseRuntimeDescriptorError,
    verify_base_runtime_generation,
)
from .reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeLimits,
    canonical_json_bytes,
    digest_bytes,
    is_digest,
)
from .reddog_holoindex_dependency_runtime_descriptor import (
    DependencyRuntimeDescriptorError,
    verify_dependency_runtime_generation,
)
from .reddog_holoindex_query_replica_orphans import OwnedDirectoryProof
from .reddog_holoindex_runtime_composition_contract import (
    DESCRIPTOR_NAME,
    RuntimeCompositionBinding,
    RuntimeCompositionContractError,
    RuntimeCompositionLimits,
    runtime_composition_descriptor,
    validate_runtime_composition_descriptor,
)


class RuntimeCompositionDescriptorError(RuntimeError):
    """Stable composition-generation verification error."""


def _fail(code: str) -> None:
    raise RuntimeCompositionDescriptorError(code)


@dataclass(frozen=True)
class VerifiedRuntimeCompositionComponents:
    base_runtime: Any
    dependency_runtime: Any
    interpreter_path: Path
    interpreter_content_digest: str
    interpreter_size: int


@dataclass(frozen=True)
class _VerifierDependencies:
    verify_base: Callable[..., Any] = verify_base_runtime_generation
    verify_dependency: Callable[..., Any] = verify_dependency_runtime_generation


def verify_runtime_composition_components(
    *,
    base_runtime_store_root: Path | str,
    base_generation_root: Path | str,
    dependency_runtime_store_root: Path | str,
    dependency_generation_root: Path | str,
    canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    base_limits: BaseRuntimeLimits = BaseRuntimeLimits(),
    dependency_limits: DependencyRuntimeLimits = DependencyRuntimeLimits(),
    dependencies: _VerifierDependencies = _VerifierDependencies(),
) -> VerifiedRuntimeCompositionComponents:
    """Reprove both payloads and the exact launchable interpreter member."""
    try:
        _require_disjoint_stores(Path(base_runtime_store_root),
                                 Path(dependency_runtime_store_root))
        base, dependency = _verified_component_pair(
            base_runtime_store_root=base_runtime_store_root,
            base_generation_root=base_generation_root,
            dependency_runtime_store_root=dependency_runtime_store_root,
            dependency_generation_root=dependency_generation_root,
            canonical_store=canonical_store,
            repo_roots=repo_roots,
            base_limits=base_limits,
            dependency_limits=dependency_limits,
            dependencies=dependencies,
        )
        interpreter_path, interpreter_digest, interpreter_size = (
            _interpreter_member(base, base_limits)
        )
        if dependency.site_packages_root != dependency.generation_root / "site-packages":
            _fail("RUNTIME_COMPOSITION_DEPENDENCY_TOPOLOGY_INVALID")
        return VerifiedRuntimeCompositionComponents(
            base, dependency, interpreter_path,
            interpreter_digest, interpreter_size,
        )
    except RuntimeCompositionDescriptorError:
        raise
    except (
        AcceptanceGuardError,
        BaseRuntimeDescriptorError,
        DependencyRuntimeDescriptorError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        raise RuntimeCompositionDescriptorError(str(exc)) from exc


def _verified_component_pair(
    *,
    base_runtime_store_root: Path | str,
    base_generation_root: Path | str,
    dependency_runtime_store_root: Path | str,
    dependency_generation_root: Path | str,
    canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    base_limits: BaseRuntimeLimits,
    dependency_limits: DependencyRuntimeLimits,
    dependencies: _VerifierDependencies,
) -> tuple[Any, Any]:
    """Run one forward pass, then a reverse pass over both components."""

    base_kwargs = {
        "runtime_store_root": base_runtime_store_root,
        "generation_root": base_generation_root,
        "canonical_store": canonical_store,
        "repo_roots": repo_roots,
        "limits": base_limits,
    }
    base_before = dependencies.verify_base(**base_kwargs)
    dependency = dependencies.verify_dependency(
        runtime_store_root=dependency_runtime_store_root,
        generation_root=dependency_generation_root,
        canonical_store=canonical_store,
        repo_roots=repo_roots,
        limits=dependency_limits,
    )
    dependency_kwargs = {
        "runtime_store_root": dependency_runtime_store_root,
        "generation_root": dependency_generation_root,
        "canonical_store": canonical_store,
        "repo_roots": repo_roots,
        "limits": dependency_limits,
    }
    return _reverse_component_reproof(
        base_before=base_before,
        dependency_before=dependency,
        base_kwargs=base_kwargs,
        dependency_kwargs=dependency_kwargs,
        dependencies=dependencies,
    )


def _reverse_component_reproof(
    *,
    base_before: Any,
    dependency_before: Any,
    base_kwargs: dict[str, Any],
    dependency_kwargs: dict[str, Any],
    dependencies: _VerifierDependencies,
) -> tuple[Any, Any]:
    """Detect one-shot cross-pass mutation without claiming write denial."""

    try:
        dependency_after = dependencies.verify_dependency(**dependency_kwargs)
        base_after = dependencies.verify_base(**base_kwargs)
    except (
        BaseRuntimeDescriptorError,
        DependencyRuntimeDescriptorError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        raise RuntimeCompositionDescriptorError(
            "RUNTIME_COMPOSITION_COMPONENT_MUTATED_DURING_VERIFICATION"
        ) from exc
    if base_after != base_before or dependency_after != dependency_before:
        _fail("RUNTIME_COMPOSITION_COMPONENT_MUTATED_DURING_VERIFICATION")
    return base_after, dependency_after


def verify_runtime_composition_generation(
    *,
    composition_store_root: Path | str,
    generation_root: Path | str,
    base_runtime_store_root: Path | str,
    base_generation_root: Path | str,
    dependency_runtime_store_root: Path | str,
    dependency_generation_root: Path | str,
    canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    composition_limits: RuntimeCompositionLimits = RuntimeCompositionLimits(),
    base_limits: BaseRuntimeLimits = BaseRuntimeLimits(),
    dependency_limits: DependencyRuntimeLimits = DependencyRuntimeLimits(),
    expected_generation_id: str | None = None,
) -> RuntimeCompositionBinding:
    """Verify one canonical composition and independently reprove both payloads."""

    components = verify_runtime_composition_components(
        base_runtime_store_root=base_runtime_store_root,
        base_generation_root=base_generation_root,
        dependency_runtime_store_root=dependency_runtime_store_root,
        dependency_generation_root=dependency_generation_root,
        canonical_store=canonical_store,
        repo_roots=repo_roots,
        base_limits=base_limits,
        dependency_limits=dependency_limits,
    )
    expected = expected_generation_id or f"sha256:{Path(str(generation_root)).name}"
    return _verify_composition_descriptor(
        composition_store_root=composition_store_root,
        generation_root=generation_root,
        expected_generation_id=expected,
        bind_canonical_name=True,
        owned_root=None,
        components=components,
        canonical_store=canonical_store,
        repo_roots=repo_roots,
        limits=composition_limits,
        component_store_roots=(
            Path(base_runtime_store_root), Path(dependency_runtime_store_root)
        ),
    )


def verify_runtime_composition_staging(
    *,
    composition_store_root: Path | str,
    staging_root: Path | str,
    expected_generation_id: str,
    owned_root: OwnedDirectoryProof,
    components: VerifiedRuntimeCompositionComponents,
    component_store_roots: tuple[Path | str, Path | str],
    canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    limits: RuntimeCompositionLimits = RuntimeCompositionLimits(),
) -> RuntimeCompositionBinding:
    """Verify unpublished process-owned composition bytes."""

    return _verify_composition_descriptor(
        composition_store_root=composition_store_root,
        generation_root=staging_root,
        expected_generation_id=expected_generation_id,
        bind_canonical_name=False,
        owned_root=owned_root,
        components=components,
        component_store_roots=component_store_roots,
        canonical_store=canonical_store,
        repo_roots=repo_roots,
        limits=limits,
    )


def _verify_composition_descriptor(
    *,
    composition_store_root: Path | str,
    generation_root: Path | str,
    expected_generation_id: str,
    bind_canonical_name: bool,
    owned_root: OwnedDirectoryProof | None,
    components: VerifiedRuntimeCompositionComponents,
    component_store_roots: tuple[Path | str, Path | str],
    canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    limits: RuntimeCompositionLimits,
) -> RuntimeCompositionBinding:
    try:
        limits.validate()
        if not is_digest(expected_generation_id):
            _fail("RUNTIME_COMPOSITION_GENERATION_ID_INVALID")
        store = _validated_store(
            composition_store_root, canonical_store=canonical_store,
            repo_roots=repo_roots,
        )
        _require_disjoint_stores(store.path, *map(Path, component_store_roots))
        generation, metadata = _literal_generation_child(
            generation_root, store, repo_roots
        )
        if owned_root is not None and (
            generation != owned_root.path
            or int(metadata.st_dev) != owned_root.device
            or int(metadata.st_ino) != owned_root.inode
        ):
            _fail("RUNTIME_COMPOSITION_STAGING_IDENTITY_CHANGED")
        if bind_canonical_name and generation.name != expected_generation_id[7:]:
            _fail("RUNTIME_COMPOSITION_GENERATION_NAME_INVALID")
        raw, descriptor = _verified_descriptor(
            generation, expected_generation_id, components, limits
        )
        verify_store_proof(
            store, canonical_store=canonical_store, repo_roots=repo_roots
        )
        return _binding(generation, raw, descriptor, components)
    except RuntimeCompositionDescriptorError:
        raise
    except (
        AcceptanceGuardError,
        RuntimeCompositionContractError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        raise RuntimeCompositionDescriptorError(str(exc)) from exc


def _verified_descriptor(
    generation: Path,
    expected_generation_id: str,
    components: VerifiedRuntimeCompositionComponents,
    limits: RuntimeCompositionLimits,
) -> tuple[str, dict[str, Any]]:
    _direct_generation_topology(generation)
    raw = _read_descriptor(generation, limits)
    descriptor = validate_runtime_composition_descriptor(_parse_canonical(raw))
    expected = runtime_composition_descriptor(
        base_runtime=components.base_runtime,
        dependency_runtime=components.dependency_runtime,
        interpreter_content_digest=components.interpreter_content_digest,
        interpreter_size=components.interpreter_size,
    )
    if descriptor != expected or descriptor["generation_id"] != expected_generation_id:
        _fail("RUNTIME_COMPOSITION_COMPONENT_BINDING_MISMATCH")
    if _read_descriptor(generation, limits) != raw:
        _fail("RUNTIME_COMPOSITION_DESCRIPTOR_CHANGED")
    return raw, descriptor


def _interpreter_member(base: Any, limits: BaseRuntimeLimits) -> tuple[Path, str, int]:
    text = secure_read_confined_text(
        base.generation_root / BASE_INVENTORY_NAME,
        allowed_root=base.generation_root,
        max_bytes=limits.max_inventory_bytes,
    )
    inventory = validate_base_inventory(parse_base_canonical_json(text))
    matches = [row for row in inventory["files"] if row["path"] == "python.exe"]
    if len(matches) != 1 or matches[0]["role"] != "python_executable":
        _fail("RUNTIME_COMPOSITION_INTERPRETER_MEMBER_INVALID")
    path = base.base_prefix_root / "python.exe"
    metadata = os.lstat(path)
    proof = secure_digest_confined_file_impl(
        path,
        allowed_root=base.base_prefix_root,
        expected_identity=confined_file_identity(metadata),
        max_bytes=limits.max_file_bytes,
    )
    require_unnamed_data_stream_only(path)
    if proof.digest != matches[0]["sha256"] or proof.size != matches[0]["size"]:
        _fail("RUNTIME_COMPOSITION_INTERPRETER_MEMBER_INVALID")
    return path, proof.digest, proof.size


def _binding(
    generation: Path,
    raw: str,
    descriptor: dict[str, Any],
    components: VerifiedRuntimeCompositionComponents,
) -> RuntimeCompositionBinding:
    truth = {
        name: bool(descriptor[name])
        for name in (
            "artifact_bytes_independently_reverified",
            "abi_compatibility_verified",
            "native_loader_closure_verified",
            "deterministic_effects_verified",
            "preimport_bootstrap_verified",
            "signature_verified",
            "write_denial_verified",
            "activation_eligible",
            "exact_runtime_closure_verified",
        )
    }
    return RuntimeCompositionBinding(
        generation_root=generation,
        descriptor_path=generation / DESCRIPTOR_NAME,
        descriptor_digest=digest_bytes(raw.encode("ascii")),
        generation_id=str(descriptor["generation_id"]),
        base_runtime=components.base_runtime,
        dependency_runtime=components.dependency_runtime,
        interpreter_path=components.interpreter_path,
        interpreter_content_digest=components.interpreter_content_digest,
        interpreter_size=components.interpreter_size,
        site_packages_root=components.dependency_runtime.site_packages_root,
        **truth,
    )


def _validated_store(
    root: Path | str, *, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
) -> StoreProof:
    for repo_root in repo_roots:
        validate_runtime_root_path(root, repo_root=repo_root)
    store = prove_existing_isolated_store(
        root, canonical_store=canonical_store, repo_roots=repo_roots
    )
    verify_store_proof(store, canonical_store=canonical_store, repo_roots=repo_roots)
    return store


def _literal_generation_child(
    value: Path | str, store: StoreProof, repo_roots: tuple[Path | str, ...],
) -> tuple[Path, os.stat_result]:
    raw = str(value or "")
    if not raw or "\x00" in raw or not Path(raw).is_absolute():
        _fail("RUNTIME_COMPOSITION_GENERATION_PATH_INVALID")
    for repo_root in repo_roots:
        validate_runtime_artifact_path(raw, repo_root=repo_root, allowed_root=store.path)
    generation = Path(os.path.abspath(raw))
    if os.path.normcase(str(generation.parent)) != os.path.normcase(str(store.path)):
        _fail("RUNTIME_COMPOSITION_GENERATION_PATH_INVALID")
    metadata = os.lstat(generation)
    if not stat.S_ISDIR(metadata.st_mode) or _is_link_or_reparse(generation, metadata):
        _fail("RUNTIME_COMPOSITION_GENERATION_PATH_INVALID")
    return generation, metadata


def _direct_generation_topology(root: Path) -> None:
    expected = {DESCRIPTOR_NAME, ".runtime-composition-publication-orphans"}
    entries = tuple(os.scandir(root))
    if {entry.name for entry in entries} != expected:
        _fail("RUNTIME_COMPOSITION_GENERATION_TOPOLOGY_INVALID")
    for entry in entries:
        path = Path(entry.path)
        metadata = os.lstat(path)
        wanted_directory = entry.name.startswith(".")
        if (
            _is_link_or_reparse(path, metadata)
            or stat.S_ISDIR(metadata.st_mode) is not wanted_directory
            or (not wanted_directory and not stat.S_ISREG(metadata.st_mode))
        ):
            _fail("RUNTIME_COMPOSITION_GENERATION_TOPOLOGY_INVALID")
        require_unnamed_data_stream_only(path)
    if tuple(os.scandir(root / ".runtime-composition-publication-orphans")):
        _fail("RUNTIME_COMPOSITION_GENERATION_TOPOLOGY_INVALID")


def _read_descriptor(root: Path, limits: RuntimeCompositionLimits) -> str:
    return secure_read_confined_text(
        root / DESCRIPTOR_NAME,
        allowed_root=root,
        max_bytes=limits.max_descriptor_bytes,
    )


def _parse_canonical(raw: str) -> dict[str, Any]:
    def strict(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if type(key) is not str or key in result:
                _fail("RUNTIME_COMPOSITION_JSON_DUPLICATE_KEY")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=strict, parse_constant=lambda _v: _fail(
            "RUNTIME_COMPOSITION_JSON_INVALID"
        ))
    except RuntimeCompositionDescriptorError:
        raise
    except Exception:
        _fail("RUNTIME_COMPOSITION_JSON_INVALID")
    if type(value) is not dict or canonical_json_bytes(value).decode("ascii") != raw:
        _fail("RUNTIME_COMPOSITION_JSON_INVALID")
    return value


def _require_disjoint_stores(*roots: Path) -> None:
    normalized = [Path(root).resolve(strict=True) for root in roots]
    for index, first in enumerate(normalized):
        for second in normalized[index + 1:]:
            try:
                common = Path(os.path.commonpath((str(first), str(second))))
            except ValueError:
                continue
            if common == first or common == second:
                _fail("RUNTIME_COMPOSITION_STORE_OVERLAP")


def _is_link_or_reparse(path: Path, metadata: os.stat_result) -> bool:
    return bool(
        stat.S_ISLNK(metadata.st_mode)
        or int(getattr(metadata, "st_file_attributes", 0))
        & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        or getattr(path, "is_junction", lambda: False)()
    )


__all__ = [
    "RuntimeCompositionDescriptorError",
    "VerifiedRuntimeCompositionComponents",
    "verify_runtime_composition_components",
    "verify_runtime_composition_generation",
    "verify_runtime_composition_staging",
]
