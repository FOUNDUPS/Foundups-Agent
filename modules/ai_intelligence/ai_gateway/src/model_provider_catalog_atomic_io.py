"""Low-level atomic I/O primitives for provider catalog artifacts."""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Callable


def _write_all(stream: BinaryIO, payload: bytes) -> None:
    written = stream.write(payload)
    if written != len(payload):
        raise OSError("runtime_artifact_temp_write_incomplete")


def _before_commit(_path: Path) -> None:
    """Trusted no-op seam for deterministic publication failure tests."""


@dataclass(frozen=True)
class AtomicArtifactOps:
    """Trusted low-level seams used only by offline durability tests."""

    writer: Callable[[BinaryIO, bytes], None] = _write_all
    fsync: Callable[[int], None] = os.fsync
    replacer: Callable[[Path, Path], None] = os.replace
    before_commit: Callable[[Path], None] = _before_commit


@dataclass(frozen=True)
class _TempArtifactProof:
    device: int
    inode: int
    size: int
    digest: str


@dataclass(frozen=True)
class _VerifiedTemp:
    path: Path
    descriptor: int
    proof: _TempArtifactProof


@dataclass(frozen=True)
class _PriorTarget:
    payload: bytes | None
    mode: int | None


def _same_identity(metadata: os.stat_result, proof: _TempArtifactProof) -> bool:
    return (
        proof.inode > 0
        and metadata.st_ino > 0
        and (metadata.st_dev, metadata.st_ino) == (proof.device, proof.inode)
    )


def _valid_metadata(metadata: os.stat_result, proof: _TempArtifactProof) -> bool:
    return (
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_nlink == 1
        and metadata.st_size == proof.size
        and _same_identity(metadata, proof)
    )


def _verify_descriptor_content(
    descriptor: int, proof: _TempArtifactProof, payload: bytes
) -> None:
    content = _read_descriptor(descriptor, proof.size + 1)
    if content != payload or hashlib.sha256(content).hexdigest() != proof.digest:
        raise ValueError("runtime_artifact_temp_content_mismatch")


def _read_descriptor(descriptor: int, limit: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks = []
    remaining = limit
    while remaining > 0:
        chunk = os.read(descriptor, remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _open_verification_descriptor(path: Path) -> int:
    if os.name != "nt":
        return os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    return _open_windows_descriptor(path, 0x80000000)


def _open_windows_publication_descriptor(path: Path) -> int:
    return _open_windows_descriptor(path, 0x80000000 | 0x00010000)


def _open_windows_descriptor(path: Path, desired_access: int) -> int:
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    handle = create_file(
        str(path),
        desired_access,
        0x00000001 | 0x00000002 | 0x00000004,
        None,
        3,
        0x00000080 | 0x00200000,
        None,
    )
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return msvcrt.open_osfhandle(
            handle, os.O_RDONLY | getattr(os, "O_BINARY", 0)
        )
    except Exception:
        close_handle(handle)
        raise


def _publish_verified(
    verified: _VerifiedTemp,
    target: Path,
    replacer: Callable[[Path, Path], None],
    payload: bytes,
) -> _VerifiedTemp:
    if os.name == "nt" and replacer is os.replace:
        descriptor = _open_windows_publication_descriptor(verified.path)
        replacement = _VerifiedTemp(verified.path, descriptor, verified.proof)
        try:
            if not _valid_metadata(os.fstat(descriptor), verified.proof):
                raise ValueError("runtime_artifact_temp_changed_before_commit")
            _verify_descriptor_content(descriptor, verified.proof, payload)
            _rename_windows_descriptor(descriptor, target)
        except Exception:
            os.close(descriptor)
            raise
        os.close(verified.descriptor)
        return replacement
    replacer(verified.path, target)
    return verified


def _rename_windows_descriptor(descriptor: int, target: Path) -> None:
    import ctypes
    import msvcrt
    from ctypes import wintypes

    class _FileRenameInfoHead(ctypes.Structure):
        _fields_ = [
            ("replace", wintypes.BOOLEAN),
            ("root", wintypes.HANDLE),
            ("name_len", wintypes.DWORD),
        ]

    nt_path = _windows_nt_path(target)
    raw_name = nt_path.encode("utf-16-le")
    name_offset = _FileRenameInfoHead.name_len.offset + ctypes.sizeof(
        wintypes.DWORD
    )
    size = ctypes.sizeof(_FileRenameInfoHead) + len(raw_name)
    buffer = ctypes.create_string_buffer(size)
    header = _FileRenameInfoHead.from_buffer(buffer)
    header.replace, header.root, header.name_len = 1, None, len(raw_name)
    ctypes.memmove(ctypes.addressof(buffer) + name_offset, raw_name, len(raw_name))
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    rename = kernel32.SetFileInformationByHandle
    rename.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    rename.restype = wintypes.BOOL
    if not rename(msvcrt.get_osfhandle(descriptor), 3, buffer, size):
        raise ctypes.WinError(ctypes.get_last_error())


def _windows_nt_path(path: Path) -> str:
    resolved = str(path.resolve())
    if resolved.startswith("\\\\"):
        return "\\??\\UNC\\" + resolved.lstrip("\\")
    return "\\??\\" + resolved


def _snapshot_target(target: Path, mode: int | None) -> _PriorTarget:
    if mode is None:
        return _PriorTarget(None, None)
    named = os.lstat(target)
    descriptor = _open_verification_descriptor(target)
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_ino <= 0
            or named.st_ino <= 0
            or opened.st_size != named.st_size
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
        ):
            raise ValueError("runtime_artifact_target_changed")
        return _PriorTarget(_read_descriptor(descriptor, opened.st_size), mode)
    finally:
        os.close(descriptor)


def _restore_prior_target(target: Path, prior: _PriorTarget) -> None:
    if prior.payload is None:
        target.unlink(missing_ok=True)
        _fsync_parent(target.parent, os.fsync)
        return
    if _target_matches_prior(target, prior):
        return
    descriptor, raw_temp = tempfile.mkstemp(
        prefix=f".{target.name}.restore.", suffix=".tmp", dir=target.parent
    )
    temporary: Path | None = Path(raw_temp)
    try:
        with os.fdopen(descriptor, "w+b", closefd=True) as stream:
            _write_all(stream, prior.payload)
            stream.flush()
            if prior.mode is not None and hasattr(os, "fchmod"):
                os.fchmod(stream.fileno(), prior.mode)
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        temporary = None
        if not _target_matches_prior(target, prior):
            raise OSError("runtime_artifact_prior_target_restore_mismatch")
        _fsync_parent(target.parent, os.fsync)
    finally:
        _remove_temp(temporary)


def _target_matches_prior(target: Path, prior: _PriorTarget) -> bool:
    try:
        named = os.lstat(target)
        descriptor = os.open(
            target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        )
    except (OSError, ValueError):
        return False
    try:
        opened = os.fstat(descriptor)
        return (
            prior.payload is not None
            and stat.S_ISREG(opened.st_mode)
            and (opened.st_dev, opened.st_ino) == (named.st_dev, named.st_ino)
            and stat.S_IMODE(opened.st_mode) == prior.mode
            and _read_descriptor(descriptor, opened.st_size + 1) == prior.payload
        )
    finally:
        os.close(descriptor)


def _remove_temp(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _remove_owned_temp(
    path: Path | None, proof: _TempArtifactProof | None
) -> None:
    if path is None:
        return
    if proof is None:
        _remove_temp(path)
        return
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return
    if _valid_metadata(metadata, proof):
        _remove_temp(path)


def _cleanup_failed_publication(
    verified: _VerifiedTemp | None,
    temporary: Path | None,
    proof: _TempArtifactProof | None,
) -> None:
    if verified is not None:
        os.close(verified.descriptor)
    _remove_owned_temp(temporary, proof)


def _release_native_publication(
    verified: _VerifiedTemp | None, native_handle_published: bool
) -> _VerifiedTemp | None:
    if native_handle_published and verified is not None:
        os.close(verified.descriptor)
        return None
    return verified


def _fsync_parent(parent: Path, fsync: Callable[[int], None]) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(parent, flags)
    except (OSError, NotImplementedError):
        return
    try:
        fsync(descriptor)
    except (OSError, NotImplementedError):
        pass
    finally:
        os.close(descriptor)
