"""Non-replacing publication and owned cleanup for retained artifacts.

Windows renames the verified object by handle. POSIX uses non-replacing link
creation while retaining and rechecking the source. POSIX runtime directories
must be controlled by the same principal; pathname APIs cannot exclude an
arbitrary same-UID writer, and this module does not claim otherwise.
"""

from __future__ import annotations

import os
from pathlib import Path

from .model_autoresearch_configured_gateway_durability import _fsync_directory
from .model_autoresearch_production_binding_artifact_identity import (
    HeldProductionArtifact,
    ProductionArtifactProof,
    open_verified_artifact,
    proof_from_dict,
    read_held_json,
    require_proof,
    seal_staged_artifact,
    verify_held_artifact,
    verify_path,
)
from .model_provider_catalog_atomic_io import _rename_windows_descriptor


def publish_held_artifact(held: HeldProductionArtifact, final: Path) -> None:
    """Publish the retained object without overwriting a foreign final."""

    verify_held_artifact(held)
    if os.name != "nt" and held.allowed_links == 2:
        _finish_interrupted_posix_publication(held, final)
        return
    if held.path == final:
        _finish_publication(held, final)
        return
    if final.exists() or final.is_symlink():
        raise ValueError("single_model_production_output_ownership_conflict")
    if os.name == "nt":
        try:
            _rename_windows_descriptor(held.descriptor, final, replace_existing=False)
        except OSError:
            raise ValueError(
                "single_model_production_output_ownership_conflict"
            ) from None
    else:
        try:
            os.link(held.path, final, follow_symlinks=False)
        except FileExistsError:
            raise ValueError(
                "single_model_production_output_ownership_conflict"
            ) from None
        verify_path(final, held.proof, allowed_links=2)
        _unlink_owned_path(held.path, held.proof, allowed_links=2)
    held.path = final
    _finish_publication(held, final)


def open_interrupted_posix_publication(
    stage: Path, final: Path, proof: ProductionArtifactProof
) -> HeldProductionArtifact | None:
    """Open the exact two-link state left by death after POSIX link creation."""

    if os.name == "nt" or not (stage.exists() and final.exists()):
        return None
    held = open_verified_artifact(stage, proof, allowed_links=2)
    try:
        verify_path(final, proof, allowed_links=2)
        return held
    except BaseException:
        held.close()
        raise


def cleanup_owned_artifact(path: Path, proof: ProductionArtifactProof) -> None:
    try:
        verify_path(path, proof, allowed_links=1)
    except FileNotFoundError:
        return
    except OSError:
        raise ValueError("single_model_production_output_ownership_conflict") from None
    try:
        _unlink_owned_path(path, proof, allowed_links=1)
    except OSError:
        raise ValueError("single_model_production_owned_unlink_failed") from None


def _fsync_regular_file(path: Path) -> HeldProductionArtifact:
    """Retained compatibility seam for deterministic durability faults."""
    try:
        return seal_staged_artifact(path)
    except OSError as error:
        if "identity" in str(error) or "content_changed" in str(error):
            raise ValueError(
                "single_model_production_output_ownership_conflict"
            ) from None
        raise ValueError("single_model_production_stage_durability_failed") from None


def seal_staged_artifacts(*paths: Path) -> None:
    held = []
    try:
        held = [_fsync_regular_file(path) for path in paths]
    finally:
        for artifact in held:
            artifact.close()


def fsync_published_parent(path: Path) -> None:
    """Recheck a single-link final and flush its directory."""

    metadata = os.lstat(path)
    if metadata.st_nlink != 1:
        raise ValueError("single_model_production_final_directory_durability_failed")
    _fsync_directory(path.parent)


def _finish_publication(held: HeldProductionArtifact, final: Path) -> None:
    verify_path(final, held.proof, allowed_links=1)
    require_proof(os.fstat(held.descriptor), held.proof)
    fsync_published_parent(final)


def _finish_interrupted_posix_publication(
    held: HeldProductionArtifact, final: Path
) -> None:
    if held.path == final:
        raise ValueError("single_model_production_output_ownership_conflict")
    verify_held_artifact(held)
    verify_path(final, held.proof, allowed_links=2)
    _unlink_owned_path(held.path, held.proof, allowed_links=2)
    _fsync_directory(held.path.parent)
    if final.parent != held.path.parent:
        _fsync_directory(final.parent)
    held.path = final
    held.allowed_links = 1
    _finish_publication(held, final)


def _unlink_owned_path(
    path: Path, proof: ProductionArtifactProof, *, allowed_links: int
) -> None:
    verify_path(path, proof, allowed_links=allowed_links)
    path.unlink()


__all__ = [
    "HeldProductionArtifact",
    "ProductionArtifactProof",
    "cleanup_owned_artifact",
    "open_verified_artifact",
    "open_interrupted_posix_publication",
    "proof_from_dict",
    "publish_held_artifact",
    "read_held_json",
    "seal_staged_artifact",
    "seal_staged_artifacts",
    "fsync_published_parent",
    "verify_held_artifact",
]
