"""No-delete quarantine for failed query-replica staging directories."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from .reddog_holoindex_acceptance_guards import (
    QuarantinedPathProof,
    _is_link_or_reparse,
    _normalized,
)
from .reddog_private_json_publication import quarantine_owned_path_no_replace


@dataclass(frozen=True)
class OwnedDirectoryProof:
    """Exact identity proof for a staging directory created by this process."""

    path: Path
    device: int
    inode: int


def owned_directory(path: Path) -> OwnedDirectoryProof:
    metadata = os.lstat(path)
    if not stat.S_ISDIR(metadata.st_mode) or _is_link_or_reparse(path, metadata):
        raise RuntimeError("QUERY_REPLICA_STAGING_INVALID")
    return OwnedDirectoryProof(path, int(metadata.st_dev), int(metadata.st_ino))


def quarantine_owned_staging(
    proof: OwnedDirectoryProof | None, *, allowed_root: Path,
    orphan_root: Path, token: str,
) -> QuarantinedPathProof | None:
    """Preserve an unchanged staging identity; never delete or follow links."""

    if proof is None:
        return None
    try:
        metadata = os.lstat(proof.path)
    except FileNotFoundError:
        return None
    if (
        int(metadata.st_dev) != proof.device
        or int(metadata.st_ino) != proof.inode
        or not stat.S_ISDIR(metadata.st_mode)
        or _is_link_or_reparse(proof.path, metadata)
    ):
        raise RuntimeError("QUERY_REPLICA_STAGING_QUARANTINE_UNSAFE")
    return quarantine_owned_path_no_replace(
        proof.path, allowed_root=_normalized(allowed_root),
        orphan_root=_normalized(orphan_root), label="staging", token=token,
        max_bytes=0,
    )


__all__ = ["OwnedDirectoryProof", "owned_directory", "quarantine_owned_staging"]
