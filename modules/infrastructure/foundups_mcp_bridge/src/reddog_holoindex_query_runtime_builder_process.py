"""Actual-process proof for an inert RedDog query evidence builder."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat
import sys
from typing import Mapping

from holo_index.repository_state import repository_root_digest
from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    confined_file_identity,
    secure_digest_confined_file_impl,
)
from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    require_unnamed_data_stream_only,
)

from .reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    digest_bytes,
)
from .reddog_holoindex_process_image import (
    ProcessExecutableProof,
    current_process_image_path,
    prove_process_executable_path,
)
from .reddog_holoindex_query_runtime_builder_contract import (
    BuilderProcessAuthority,
    _process_authority_capability,
)
from .reddog_holoindex_runtime_composition_contract import RuntimeCompositionBinding
from .reddog_holoindex_runtime_composition_descriptor import (
    verify_runtime_composition_generation,
)


class QueryRuntimeBuilderProcessError(RuntimeError):
    """Stable fail-closed actual-process authority error."""


def _fail(code: str) -> None:
    raise QueryRuntimeBuilderProcessError(code)


@dataclass(frozen=True)
class BuilderProcessObservation:
    executable: Path
    isolated: int
    no_site: int
    dont_write_bytecode: int
    ignore_environment: int
    no_user_site: int
    sys_prefix: Path
    sys_base_prefix: Path
    sys_exec_prefix: Path
    sys_base_exec_prefix: Path
    sys_path: tuple[Path, ...]
    stdlib_zip_name: str


def prove_builder_process_authority(
    *, composition_verification_kwargs: Mapping[str, object],
    repo_root: Path | str,
) -> BuilderProcessAuthority:
    """Bind the OS-reported running image and isolated Python state."""

    try:
        before = verify_runtime_composition_generation(
            **dict(composition_verification_kwargs)
        )
        image = current_process_image_path()
        proof = prove_process_executable_path(image)
        observation = _actual_process_observation(image)
        authority = _prove_builder_process_authority(
            composition=before, repo_root=Path(repo_root),
            observation=observation, executable_proof=proof,
        )
        after = verify_runtime_composition_generation(
            **dict(composition_verification_kwargs)
        )
    except QueryRuntimeBuilderProcessError:
        raise
    except Exception:
        _fail("QUERY_BUILDER_PROCESS_AUTHORITY_UNAVAILABLE")
    if after != before:
        _fail("QUERY_BUILDER_PROCESS_COMPOSITION_MUTATED_DURING_PROOF")
    return _process_authority_capability(authority)


def _actual_process_observation(image: Path) -> BuilderProcessObservation:
    return BuilderProcessObservation(
        executable=image, isolated=int(sys.flags.isolated),
        no_site=int(sys.flags.no_site),
        dont_write_bytecode=int(sys.flags.dont_write_bytecode),
        ignore_environment=int(sys.flags.ignore_environment),
        no_user_site=int(sys.flags.no_user_site),
        sys_prefix=Path(sys.prefix), sys_base_prefix=Path(sys.base_prefix),
        sys_exec_prefix=Path(sys.exec_prefix),
        sys_base_exec_prefix=Path(sys.base_exec_prefix),
        sys_path=tuple(Path(value) for value in sys.path),
        stdlib_zip_name=f"python{sys.version_info.major}{sys.version_info.minor}.zip",
    )


def _prove_builder_process_authority_for_test(
    *, composition: RuntimeCompositionBinding, repo_root: Path,
    observation: BuilderProcessObservation,
    executable_proof: ProcessExecutableProof,
) -> BuilderProcessAuthority:
    """Private deterministic seam; production observations are never injected."""

    binding = _prove_builder_process_authority(
        composition=composition, repo_root=repo_root,
        observation=observation, executable_proof=executable_proof,
    )
    return _process_authority_capability(binding)


def _prove_builder_process_authority(
    *, composition: RuntimeCompositionBinding, repo_root: Path,
    observation: BuilderProcessObservation,
    executable_proof: ProcessExecutableProof,
) -> dict[str, object]:
    if (
        type(composition) is not RuntimeCompositionBinding
        or type(observation) is not BuilderProcessObservation
        or type(executable_proof) is not ProcessExecutableProof
    ):
        _fail("QUERY_BUILDER_PROCESS_INPUT_INVALID")
    roots = _validated_roots(composition, repo_root)
    _validate_observation(composition, observation, executable_proof, roots)
    image_digest, image_size = _hash_image(executable_proof)
    if (
        image_digest != composition.interpreter_content_digest
        or image_size != composition.interpreter_size
    ):
        _fail("QUERY_BUILDER_PROCESS_IMAGE_MISMATCH")
    launch = {
        "executable": image_digest,
        "isolated": observation.isolated,
        "no_site": observation.no_site,
        "dont_write_bytecode": observation.dont_write_bytecode,
        "ignore_environment": observation.ignore_environment,
        "no_user_site": observation.no_user_site,
        "prefix_roles": _prefix_roles(observation, roots),
    }
    sys_path_roles = [
        {"role": _path_role(path, roots), "relative": _relative_role_path(path, roots)}
        for path in observation.sys_path
    ]
    return {
        "runtime_composition_generation_id": composition.generation_id,
        "runtime_composition_descriptor_digest": composition.descriptor_digest,
        "builder_source_root_digest": repository_root_digest(roots["builder_source"]),
        "dependency_runtime_inventory_digest": composition.dependency_runtime.inventory_digest,
        "process_image_content_digest": image_digest,
        "process_image_size": image_size,
        "launch_state_digest": digest_bytes(canonical_json_bytes(launch)),
        "sys_path_digest": digest_bytes(canonical_json_bytes(sys_path_roles)),
        "actual_process_image_verified": True,
        "isolation_verified": True,
        "native_loaded_image_closure_verified": False,
    }


def _validated_roots(
    composition: RuntimeCompositionBinding, repo_root: Path,
) -> Mapping[str, Path]:
    roots = {
        "base_runtime": composition.base_runtime.base_prefix_root,
        "dependency_runtime": composition.dependency_runtime.site_packages_root,
        "builder_source": repo_root,
    }
    if (
        composition.interpreter_path != roots["base_runtime"] / "python.exe"
        or composition.site_packages_root != roots["dependency_runtime"]
        or len({os.path.normcase(str(path.absolute())) for path in roots.values()}) != 3
        or any(
            _within(left, right) or _within(right, left)
            for index, left in enumerate(roots.values())
            for right in tuple(roots.values())[index + 1:]
        )
    ):
        _fail("QUERY_BUILDER_PROCESS_TOPOLOGY_INVALID")
    for root in roots.values():
        _validate_existing_path(root)
        if (
            not root.is_absolute() or not root.is_dir()
            or root.drive.rstrip(":").upper() not in {"O", "E"}
        ):
            _fail("QUERY_BUILDER_PROCESS_VOLUME_INVALID")
    return roots


def _validate_observation(
    composition: RuntimeCompositionBinding,
    observation: BuilderProcessObservation,
    proof: ProcessExecutableProof,
    roots: Mapping[str, Path],
) -> None:
    if (
        observation.executable != proof.path
        or observation.executable != composition.interpreter_path
        or (observation.isolated, observation.no_site,
            observation.dont_write_bytecode, observation.ignore_environment,
            observation.no_user_site) != (1, 1, 1, 1, 1)
        or not observation.sys_path
    ):
        _fail("QUERY_BUILDER_PROCESS_ISOLATION_INVALID")
    paths = observation.sys_path
    expected = _expected_sys_path(observation, roots)
    if tuple(str(path) for path in paths) != tuple(str(path) for path in expected):
        _fail("QUERY_BUILDER_PROCESS_SYS_PATH_INVALID")
    for path in paths:
        if path.exists():
            _validate_existing_path(path)
    _prefix_roles(observation, roots)


def _prefix_roles(
    observation: BuilderProcessObservation, roots: Mapping[str, Path],
) -> dict[str, str]:
    prefixes = {
        "prefix": observation.sys_prefix,
        "base_prefix": observation.sys_base_prefix,
        "exec_prefix": observation.sys_exec_prefix,
        "base_exec_prefix": observation.sys_base_exec_prefix,
    }
    for value in prefixes.values():
        _validate_existing_path(value)
        if value != roots["base_runtime"]:
            _fail("QUERY_BUILDER_PROCESS_PREFIX_INVALID")
    return {name: _relative_role_path(value, roots) for name, value in prefixes.items()}


def _expected_sys_path(
    observation: BuilderProcessObservation, roots: Mapping[str, Path],
) -> tuple[Path, ...]:
    name = observation.stdlib_zip_name
    if (
        not name.startswith("python") or not name.endswith(".zip")
        or not name[6:-4].isdigit() or not 2 <= len(name[6:-4]) <= 3
    ):
        _fail("QUERY_BUILDER_PROCESS_SYS_PATH_INVALID")
    base = roots["base_runtime"]
    return (
        base / name, base / "DLLs", base / "Lib", base,
        roots["dependency_runtime"], roots["builder_source"],
    )


def _path_role(path: Path, roots: Mapping[str, Path]) -> str:
    matches = [name for name, root in roots.items() if _within(path, root)]
    if len(matches) != 1:
        _fail("QUERY_BUILDER_PROCESS_PATH_AUTHORITY_INVALID")
    return matches[0]


def _relative_role_path(path: Path, roots: Mapping[str, Path]) -> str:
    role = _path_role(path, roots)
    relative = path.absolute().relative_to(roots[role].absolute()).as_posix()
    return "." if not relative else relative


def _within(path: Path, root: Path) -> bool:
    try:
        path.absolute().relative_to(root.absolute())
        return True
    except ValueError:
        return False


def _validate_existing_path(path: Path) -> None:
    try:
        candidate = path.absolute()
        current = Path(candidate.anchor)
        for part in candidate.parts[1:]:
            current /= part
            metadata = os.lstat(current)
            attributes = int(getattr(metadata, "st_file_attributes", 0))
            if (
                stat.S_ISLNK(metadata.st_mode)
                or attributes & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
                or getattr(current, "is_junction", lambda: False)()
            ):
                _fail("QUERY_BUILDER_PROCESS_PATH_AUTHORITY_INVALID")
            require_unnamed_data_stream_only(current)
    except OSError:
        _fail("QUERY_BUILDER_PROCESS_PATH_AUTHORITY_INVALID")


def _hash_image(proof: ProcessExecutableProof) -> tuple[str, int]:
    try:
        metadata = os.lstat(proof.path)
        identity = confined_file_identity(metadata)
        if (
            (identity.device, identity.inode, identity.size, identity.modified_ns,
             stat.S_IFMT(identity.mode), identity.links) != proof.identity
        ):
            _fail("QUERY_BUILDER_PROCESS_IMAGE_MUTATED")
        result = secure_digest_confined_file_impl(
            proof.path, allowed_root=proof.path.parent,
            expected_identity=identity, max_bytes=max(identity.size, 1),
        )
        require_unnamed_data_stream_only(proof.path)
    except QueryRuntimeBuilderProcessError:
        raise
    except Exception:
        _fail("QUERY_BUILDER_PROCESS_IMAGE_UNAVAILABLE")
    return result.digest, result.size


__all__ = [
    "BuilderProcessObservation",
    "QueryRuntimeBuilderProcessError",
    "prove_builder_process_authority",
]
