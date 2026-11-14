"""Stable current-process executable proof for isolated Holo child launch."""

from __future__ import annotations

import os
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator


class ProcessExecutableProofError(RuntimeError):
    """The current process image or stable identity could not be proven."""


@dataclass(frozen=True)
class ProcessExecutableProof:
    path: Path
    identity: tuple[int, int, int, int, int, int]


@dataclass(frozen=True)
class ProcessExecutableCapability:
    """Live executable identity retained until the runner returns."""

    descriptor: int
    launch_path: Path
    pass_fds: tuple[int, ...]


def _fail() -> None:
    raise ProcessExecutableProofError("RUNTIME_EXECUTABLE_UNPROVEN")


def _is_link_or_reparse(path: Path, metadata: os.stat_result) -> bool:
    return bool(
        stat.S_ISLNK(metadata.st_mode)
        or int(getattr(metadata, "st_file_attributes", 0))
        & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        or getattr(path, "is_junction", lambda: False)()
    )


def _normalized(path: Path | str) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _identity(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_size),
        int(metadata.st_mtime_ns), int(stat.S_IFMT(metadata.st_mode)),
        int(getattr(metadata, "st_nlink", 1)),
    )


def _validated_raw_path(value: Path | str) -> Path:
    raw = os.fspath(value)
    candidate = Path(raw)
    try:
        if (
            not raw or "\x00" in raw or not candidate.is_absolute()
            or any(part in {".", ".."} for part in candidate.parts)
            or _normalized(raw) != os.path.normcase(raw)
        ):
            _fail()
        current = Path(candidate.anchor)
        for part in candidate.parts[1:]:
            current /= part
            metadata = os.lstat(current)
            if _is_link_or_reparse(current, metadata):
                _fail()
        resolved = candidate.resolve(strict=True)
        metadata = os.lstat(candidate)
        if (
            _normalized(resolved) != _normalized(candidate)
            or not stat.S_ISREG(metadata.st_mode)
            or int(getattr(metadata, "st_nlink", 1)) != 1
            or (os.name != "nt" and not os.access(candidate, os.X_OK))
        ):
            _fail()
    except (OSError, RuntimeError, ValueError):
        _fail()
    return candidate


def _windows_current_process_image() -> Path:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    reader = kernel32.GetModuleFileNameW
    reader.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    reader.restype = wintypes.DWORD
    buffer = ctypes.create_unicode_buffer(32768)
    length = reader(None, buffer, len(buffer))
    if length <= 0 or length >= len(buffer) - 1:
        _fail()
    return Path(buffer.value)


def current_process_image_path() -> Path:
    """Read the running image from the OS, never mutable Python attributes."""

    if os.name == "nt":
        return _windows_current_process_image()
    if os.path.exists("/proc/self/exe"):
        try:
            return Path(os.readlink("/proc/self/exe"))
        except OSError:
            pass
    _fail()


def _open_verified(path: Path, expected: tuple[int, ...]) -> tuple[int, object | None]:
    if os.name == "nt":
        from .reddog_holoindex_acceptance_windows import (
            open_windows_verified_regular_file,
            validate_windows_file_descriptor_exact_path,
        )

        descriptor = open_windows_verified_regular_file(
            path, expected_identity=tuple(expected[:4]) + (expected[5],)
        )
        try:
            validate_windows_file_descriptor_exact_path(descriptor, path)
        except BaseException:
            os.close(descriptor)
            raise
        return descriptor, None
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    final = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
    if _normalized(final) != _normalized(path):
        os.close(descriptor)
        _fail()
    return descriptor, None


def _close_verified(descriptor: int, parent: object | None) -> None:
    os.close(descriptor)
    if parent is not None:
        parent.close()


def prove_process_executable_path(path: Path | str) -> ProcessExecutableProof:
    """Prove one canonical private regular executable by descriptor identity."""

    try:
        candidate = _validated_raw_path(path)
        expected = _identity(os.lstat(candidate))
        descriptor, parent = _open_verified(candidate, expected)
        try:
            if _identity(os.fstat(descriptor)) != expected:
                _fail()
        finally:
            _close_verified(descriptor, parent)
        return ProcessExecutableProof(candidate, expected)
    except (OSError, TypeError, ValueError, ProcessExecutableProofError):
        _fail()


def prove_current_process_executable(
    image_reader: Callable[[], Path] = current_process_image_path,
) -> ProcessExecutableProof:
    return prove_process_executable_path(image_reader())


def revalidate_process_executable(proof: object) -> Path:
    """Compatibility-only point revalidation; not launch authority."""

    if not isinstance(proof, ProcessExecutableProof):
        _fail()
    current = prove_process_executable_path(proof.path)
    if current != proof:
        _fail()
    return proof.path


@contextmanager
def hold_process_executable_for_launch(
    proof: object,
) -> Iterator[ProcessExecutableCapability]:
    """Retain one exact executable capability across the actual runner call."""

    descriptor = -1
    parent: object | None = None
    try:
        if not isinstance(proof, ProcessExecutableProof):
            _fail()
        candidate = _validated_raw_path(proof.path)
        if _identity(os.lstat(candidate)) != proof.identity:
            _fail()
        descriptor, parent = _open_verified(candidate, proof.identity)
        if _identity(os.fstat(descriptor)) != proof.identity:
            _fail()
        if os.name == "nt":
            capability = ProcessExecutableCapability(descriptor, candidate, ())
        else:
            descriptor_path = Path("/proc/self/fd") / str(descriptor)
            if (
                not descriptor_path.exists()
                or _normalized(Path(os.readlink(descriptor_path)))
                != _normalized(candidate)
            ):
                _fail()
            capability = ProcessExecutableCapability(
                descriptor, descriptor_path, (descriptor,)
            )
    except (OSError, TypeError, ValueError, ProcessExecutableProofError):
        if descriptor >= 0:
            _close_verified(descriptor, parent)
        _fail()
    try:
        yield capability
    finally:
        _close_verified(descriptor, parent)


__all__ = [
    "ProcessExecutableCapability", "ProcessExecutableProof",
    "ProcessExecutableProofError",
    "current_process_image_path", "prove_current_process_executable",
    "hold_process_executable_for_launch", "prove_process_executable_path",
    "revalidate_process_executable",
]
