"""Fail-closed durability barriers for production-binding artifacts."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from .model_autoresearch_configured_gateway_durability import _fsync_directory


def seal_staged_artifacts(*paths: Path) -> None:
    try:
        for path in paths:
            _fsync_regular_file(path)
            _fsync_directory(path.parent)
    except OSError:
        raise ValueError("single_model_production_stage_durability_failed") from None


def fsync_published_parent(path: Path) -> None:
    try:
        _require_regular_identity(path)
        _fsync_directory(path.parent)
    except OSError:
        raise ValueError(
            "single_model_production_final_directory_durability_failed"
        ) from None


def _fsync_regular_file(path: Path) -> None:
    flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(str(path), flags)
    try:
        opened = os.fstat(descriptor)
        expected = os.stat(path, follow_symlinks=False)
        _require_same_regular_file(opened, expected)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _require_same_regular_file(expected, os.stat(path, follow_symlinks=False))


def _require_regular_identity(path: Path) -> None:
    if path.is_symlink():
        raise OSError("single_model_production_artifact_link_rejected")
    first = os.stat(path, follow_symlinks=False)
    second = os.stat(path, follow_symlinks=False)
    _require_same_regular_file(first, second)


def _require_same_regular_file(first: os.stat_result, second: os.stat_result) -> None:
    if (
        not stat.S_ISREG(first.st_mode)
        or not stat.S_ISREG(second.st_mode)
        or first.st_nlink != 1
        or second.st_nlink != 1
        or (first.st_dev, first.st_ino) != (second.st_dev, second.st_ino)
    ):
        raise OSError("single_model_production_artifact_identity_invalid")


__all__ = ["fsync_published_parent", "seal_staged_artifacts"]
