"""POSIX recovery for non-replacing immutable-record creation."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from .model_autoresearch_configured_gateway_durability import _fsync_store_lineage
from .model_provider_catalog_atomic_io import _read_descriptor


def repair_interrupted_posix_commit(path: Path, payload: bytes) -> None:
    if os.name == "nt":
        return
    try:
        target = os.lstat(path)
    except FileNotFoundError:
        return
    if not stat.S_ISREG(target.st_mode) or target.st_nlink != 2:
        return
    matches = []
    pattern = f".{path.name}.*.pending"
    for candidate in path.parent.glob(pattern):
        try:
            metadata = os.lstat(candidate)
        except FileNotFoundError:
            continue
        if (metadata.st_dev, metadata.st_ino) == (target.st_dev, target.st_ino):
            matches.append(candidate)
    if len(matches) != 1 or target.st_size != len(payload):
        raise OSError("configured_gateway_interrupted_commit_ambiguous")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        if _read_descriptor(descriptor, len(payload) + 1) != payload:
            raise OSError("configured_gateway_interrupted_commit_ambiguous")
    finally:
        os.close(descriptor)
    matches[0].unlink()
    _verify_repaired_target(path, target, len(payload))
    _fsync_store_lineage(path.parent, path.parent)


def _verify_repaired_target(path: Path, prior: os.stat_result, size: int) -> None:
    current = os.lstat(path)
    if (
        not stat.S_ISREG(current.st_mode)
        or current.st_nlink != 1
        or (current.st_dev, current.st_ino) != (prior.st_dev, prior.st_ino)
        or current.st_size != size
    ):
        raise OSError("configured_gateway_interrupted_commit_ambiguous")


__all__ = ["repair_interrupted_posix_commit"]
