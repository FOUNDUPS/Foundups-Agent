"""Fail-closed guards for isolated RedDog HoloIndex candidate acceptance.

This module performs no maintenance and starts no service.  It proves the
filesystem, repository, model-copy, and receipt-publication preconditions used
by the acceptance orchestrator.
"""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from holo_index.authority_worktree import (
    _git_common_dir as read_git_common_dir,
    resolve_holoindex_authority_root,
)
from holo_index.repository_state import (
    RepositoryState,
    read_repository_state,
    repository_root_digest,
)
from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    secure_read_confined_bytes_impl,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    redact_runtime_value,
)

from .reddog_holoindex_acceptance_windows import publish_windows_temp_no_replace
from .reddog_holoindex_process_image import (
    ProcessExecutableProof,
    ProcessExecutableProofError,
    prove_current_process_executable,
)
from .reddog_sealed_holo_runtime import trusted_holo_site_packages


ACCEPTANCE_SCHEMA_VERSION = "reddog_holoindex_candidate_acceptance.v1"


class AcceptanceGuardError(RuntimeError):
    """Bounded public failure code from a candidate-acceptance guard."""


@dataclass(frozen=True)
class WorktreeProof:
    expected_sha: str
    candidate_root_digest: str
    authority_root_digest: str
    candidate_state_digest: str
    authority_state_digest: str


@dataclass(frozen=True)
class RuntimeRootProof:
    runtime_root_digest: str
    runtime_state_digest: str
    site_packages: tuple[str, ...]
    base_executable_proof: ProcessExecutableProof


@dataclass(frozen=True)
class StoreProof:
    path: Path
    device: int
    inode: int
    mode: int
    attributes: int


@dataclass(frozen=True)
class FileDigestProof:
    digest: str
    size: int


def _fail(code: str) -> None:
    raise AcceptanceGuardError(code)


def _normalized(path: Path | str) -> Path:
    raw = str(path or "").strip()
    if not raw or "\x00" in raw:
        _fail("PATH_INVALID")
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        _fail("PATH_NOT_ABSOLUTE")
    return Path(os.path.abspath(candidate))


def _same_path(first: Path, second: Path) -> bool:
    return os.path.normcase(str(first.resolve(strict=False))) == os.path.normcase(
        str(second.resolve(strict=False))
    )


def _relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _is_link_or_reparse(
    path: Path, metadata: os.stat_result | None = None
) -> bool:
    try:
        current = os.lstat(path) if metadata is None else metadata
    except OSError:
        return False
    return bool(
        stat.S_ISLNK(current.st_mode)
        or (
            getattr(current, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        )
        or getattr(path, "is_junction", lambda: False)()
    )


def _reject_link_components(path: Path) -> None:
    current = Path(path.anchor)
    for component in path.parts:
        if component == path.anchor:
            continue
        current /= component
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            continue
        except OSError:
            _fail("PATH_COMPONENT_UNAVAILABLE")
        if _is_link_or_reparse(current, metadata):
            _fail("PATH_LINK_OR_REPARSE_REJECTED")


def _reject_overlap(path: Path, protected: Iterable[Path | str]) -> None:
    for raw in protected:
        other = _normalized(raw)
        if (
            _same_path(path, other)
            or _relative_to(path, other)
            or _relative_to(other, path)
        ):
            _fail("PATH_OVERLAP_REJECTED")


def _authority_detached(authority_root: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(authority_root), "symbolic-ref", "-q", "HEAD"],
            capture_output=True,
            timeout=5.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return result.returncode == 1 and not result.stdout.strip()


def validate_acceptance_worktrees(
    candidate_root: Path | str,
    authority_root: Path | str,
    *,
    expected_sha: str,
    state_reader: Callable[[Path], RepositoryState] = read_repository_state,
    selection_resolver: Callable[..., Any] = resolve_holoindex_authority_root,
    detached_reader: Callable[[Path], bool] = _authority_detached,
) -> WorktreeProof:
    """Require clean, distinct, related worktrees at one exact commit."""

    candidate = _normalized(candidate_root)
    authority = _normalized(authority_root)
    sha = str(expected_sha).strip().lower()
    if len(sha) != 40 or any(character not in "0123456789abcdef" for character in sha):
        _fail("EXPECTED_SHA_INVALID")
    if _same_path(candidate, authority):
        _fail("WORKTREES_NOT_DISTINCT")
    candidate_state = state_reader(candidate)
    authority_state = state_reader(authority)
    if not candidate_state.proven_clean or not authority_state.proven_clean:
        _fail("WORKTREE_NOT_CLEAN")
    if candidate_state.head_sha.lower() != sha or authority_state.head_sha.lower() != sha:
        _fail("WORKTREE_HEAD_MISMATCH")
    selection = selection_resolver(
        candidate,
        environment={"REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT": str(authority)},
        state_reader=state_reader,
    )
    if (
        not selection.accepted
        or not _same_path(selection.selected_root, authority)
        or bool(selection.workspace_overlay_present)
        or selection.workspace_head_sha.lower() != sha
        or selection.authority_head_sha.lower() != sha
    ):
        _fail("WORKTREE_AUTHORITY_REJECTED")
    if not detached_reader(authority):
        _fail("AUTHORITY_NOT_DETACHED")
    return WorktreeProof(
        expected_sha=sha,
        candidate_root_digest=repository_root_digest(candidate),
        authority_root_digest=str(selection.authority_root_digest),
        candidate_state_digest=candidate_state.state_digest,
        authority_state_digest=authority_state.state_digest,
    )


def _runtime_dependencies(
    runtime: Path, site_packages_resolver: Callable[..., tuple[str, ...]],
    process_image_prover: Callable[[], ProcessExecutableProof],
) -> tuple[Path, ProcessExecutableProof]:
    try:
        executable_proof = process_image_prover()
        site_packages = tuple(
            site_packages_resolver(runtime, base_executable=executable_proof.path)
        )
    except (AttributeError, OSError, TypeError, ValueError, ProcessExecutableProofError):
        _fail("RUNTIME_EXECUTABLE_UNPROVEN")
    if len(site_packages) != 1:
        _fail("RUNTIME_SITE_PACKAGES_UNPROVEN")
    dependency_path = Path(site_packages[0]).resolve(strict=False)
    expected = (runtime / ".venv" / "Lib" / "site-packages").resolve(strict=False)
    if dependency_path != expected or not dependency_path.is_dir():
        _fail("RUNTIME_SITE_PACKAGES_UNPROVEN")
    return dependency_path, executable_proof


def validate_acceptance_runtime_root(
    candidate_root: Path | str,
    authority_root: Path | str,
    runtime_root: Path | str,
    *,
    state_reader: Callable[[Path], RepositoryState] = read_repository_state,
    common_dir_reader: Callable[[Path], Path | None] = read_git_common_dir,
    site_packages_resolver: Callable[..., tuple[str, ...]] = trusted_holo_site_packages,
    reparse_reader: Callable[[Path], bool] = _is_link_or_reparse,
    process_image_prover: Callable[[], ProcessExecutableProof] = prove_current_process_executable,
) -> RuntimeRootProof:
    """Prove a clean related checkout supplies one trusted dependency path."""

    candidate = _normalized(candidate_root)
    authority = _normalized(authority_root)
    runtime = _normalized(runtime_root)
    if _same_path(runtime, candidate) or _same_path(runtime, authority):
        _fail("RUNTIME_ROOT_NOT_DISTINCT")
    if not runtime.is_dir():
        _fail("RUNTIME_ROOT_MISSING")
    if reparse_reader(runtime):
        _fail("RUNTIME_ROOT_REPARSE_REJECTED")
    state = state_reader(runtime)
    if not state.proven_clean:
        _fail("RUNTIME_ROOT_NOT_CLEAN")
    common_dirs = tuple(common_dir_reader(root) for root in (candidate, authority, runtime))
    identities = {
        os.path.normcase(str(value.resolve(strict=False)))
        for value in common_dirs
        if value is not None
    }
    if any(value is None for value in common_dirs) or len(identities) != 1:
        _fail("RUNTIME_ROOT_UNRELATED")
    dependency_path, executable_proof = _runtime_dependencies(
        runtime, site_packages_resolver, process_image_prover
    )
    return RuntimeRootProof(
        runtime_root_digest=repository_root_digest(runtime),
        runtime_state_digest=state.state_digest,
        site_packages=(str(dependency_path),),
        base_executable_proof=executable_proof,
    )


def validate_isolated_store_target(
    path: Path | str,
    *,
    canonical_store: Path | str,
    repo_roots: Iterable[Path | str],
) -> Path:
    """Validate a new store target disjoint from source and canonical state."""

    target = _normalized(path)
    if target.parent == target:
        _fail("STORE_FILESYSTEM_ROOT_REJECTED")
    _reject_link_components(target)
    _reject_overlap(target, (canonical_store, *tuple(repo_roots)))
    if target.exists():
        _fail("STORE_ALREADY_EXISTS")
    if not target.parent.is_dir():
        _fail("STORE_PARENT_MISSING")
    return target


def _store_proof(path: Path) -> StoreProof:
    metadata = os.lstat(path)
    if not stat.S_ISDIR(metadata.st_mode) or _is_link_or_reparse(path, metadata):
        _fail("STORE_NOT_PRIVATE_DIRECTORY")
    return StoreProof(
        path=path,
        device=int(metadata.st_dev),
        inode=int(metadata.st_ino),
        mode=int(metadata.st_mode),
        attributes=int(getattr(metadata, "st_file_attributes", 0)),
    )


def create_isolated_store(
    path: Path | str,
    *,
    canonical_store: Path | str,
    repo_roots: Iterable[Path | str],
) -> StoreProof:
    target = validate_isolated_store_target(
        path, canonical_store=canonical_store, repo_roots=repo_roots
    )
    try:
        target.mkdir(mode=0o700)
    except OSError as exc:
        raise AcceptanceGuardError("STORE_CREATE_FAILED") from exc
    return _store_proof(target)


def prove_existing_isolated_store(
    path: Path | str,
    *,
    canonical_store: Path | str,
    repo_roots: Iterable[Path | str],
) -> StoreProof:
    """Create a capability for one existing disjoint private store root."""

    target = _normalized(path)
    if target.parent == target:
        _fail("STORE_FILESYSTEM_ROOT_REJECTED")
    _reject_link_components(target)
    _reject_overlap(target, (canonical_store, *tuple(repo_roots)))
    try:
        return _store_proof(target)
    except OSError as exc:
        raise AcceptanceGuardError("STORE_PROOF_UNAVAILABLE") from exc


def verify_store_proof(
    proof: StoreProof,
    *,
    canonical_store: Path | str,
    repo_roots: Iterable[Path | str],
) -> None:
    path = _normalized(proof.path)
    _reject_link_components(path)
    _reject_overlap(path, (canonical_store, *tuple(repo_roots)))
    try:
        current = _store_proof(path)
    except OSError as exc:
        raise AcceptanceGuardError("STORE_PROOF_UNAVAILABLE") from exc
    if current != proof:
        _fail("STORE_IDENTITY_CHANGED")


def read_bounded_digest(
    path: Path | str, *, allowed_root: Path | str, max_bytes: int
) -> FileDigestProof:
    if max_bytes <= 0:
        _fail("DIGEST_BOUND_INVALID")
    try:
        payload, offset = secure_read_confined_bytes_impl(
            path, allowed_root=allowed_root, max_bytes=max_bytes + 1
        )
    except (OSError, ValueError) as exc:
        raise AcceptanceGuardError("BOUNDED_READ_FAILED") from exc
    if len(payload) > max_bytes or offset > max_bytes:
        _fail("BOUNDED_READ_EXCEEDED")
    return FileDigestProof(
        digest="sha256:" + hashlib.sha256(payload).hexdigest(), size=len(payload)
    )


from .reddog_private_json_publication import (  # noqa: E402
    PublishedPrivateJsonProof,
    QuarantinedPathProof,
    atomic_publish_acceptance_receipt,
    atomic_publish_private_json,
    atomic_publish_private_json_proven,
    quarantine_proven_private_json,
    verify_proven_private_json,
)


from .reddog_holoindex_acceptance_model_copy import (  # noqa: E402
    ArtifactFileProof,
    ExpectedArtifactFile,
    ModelCopyLimits,
    ModelCopyProof,
    copy_model_snapshot,
)


__all__ = [
    "ACCEPTANCE_SCHEMA_VERSION",
    "AcceptanceGuardError",
    "ArtifactFileProof",
    "ExpectedArtifactFile",
    "FileDigestProof",
    "ModelCopyLimits",
    "ModelCopyProof",
    "PublishedPrivateJsonProof",
    "QuarantinedPathProof",
    "StoreProof",
    "RuntimeRootProof",
    "WorktreeProof",
    "atomic_publish_acceptance_receipt",
    "atomic_publish_private_json",
    "atomic_publish_private_json_proven",
    "copy_model_snapshot",
    "create_isolated_store",
    "prove_existing_isolated_store",
    "read_bounded_digest",
    "quarantine_proven_private_json",
    "verify_proven_private_json",
    "validate_acceptance_worktrees",
    "validate_isolated_store_target",
    "verify_store_proof",
]
