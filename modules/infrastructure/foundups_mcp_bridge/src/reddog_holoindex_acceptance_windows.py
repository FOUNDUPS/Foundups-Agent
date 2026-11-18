"""Narrow Windows verified-handle primitives for isolated Holo acceptance."""

from __future__ import annotations
import ctypes
import os
import stat
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

_GENERIC_READ = 0x80000000
_GENERIC_WRITE = 0x40000000
_DELETE = 0x00010000
_FILE_READ_ATTRIBUTES = 0x00000080
_FILE_SHARE_READ = 0x00000001
_OPEN_EXISTING = 3
_CREATE_NEW = 1
_FILE_ATTRIBUTE_NORMAL = 0x00000080
_FILE_ATTRIBUTE_DIRECTORY = 0x00000010
_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_FILE_RENAME_INFO_CLASS = 3
_FILE_ATTRIBUTE_TAG_INFO_CLASS = 9
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
_DUPLICATE_SAME_ACCESS = 0x00000002

class _FileAttributeTagInfo(ctypes.Structure):
    _fields_ = [
        ("FileAttributes", wintypes.DWORD),
        ("ReparseTag", wintypes.DWORD),
    ]

class _FileRenameInfo(ctypes.Structure):
    _fields_ = [
        ("ReplaceIfExists", wintypes.BOOL),
        ("RootDirectory", wintypes.HANDLE),
        ("FileNameLength", wintypes.DWORD),
        ("FileName", wintypes.WCHAR * 1),
    ]

@dataclass
class WindowsDirectoryLease:
    """Pinned non-reparse directory with stable final path and file identity."""

    path: Path
    handle: int
    identity: tuple[int, int]

    def close(self) -> None:
        if self.handle:
            _close_handle(self.handle)
            self.handle = 0


@dataclass
class WindowsFileLease:
    """Pinned regular file retained as a raw handle, outside CRT limits."""

    path: Path
    handle: int
    expected_identity: tuple[int, int, int, int, int] | None
    writable: bool = False

    def close(self) -> None:
        if self.handle:
            _close_handle(self.handle)
            self.handle = 0

def _kernel32() -> ctypes.WinDLL:
    if os.name != "nt":
        raise OSError("acceptance_windows_api_unavailable")
    return ctypes.WinDLL("kernel32", use_last_error=True)

def _api_path(path: Path) -> str:
    raw = os.path.abspath(os.fspath(path))
    if raw.startswith("\\\\?\\"):
        return raw
    if raw.startswith("\\\\"):
        return "\\\\?\\UNC\\" + raw[2:]
    return "\\\\?\\" + raw

def _normalized(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))

def _close_handle(handle: int) -> None:
    kernel32 = _kernel32()
    close = kernel32.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    close(handle)


def _open_handle(
    path: Path,
    *,
    desired_access: int,
    share_mode: int,
    flags: int,
    creation_disposition: int = _OPEN_EXISTING,
) -> int:
    kernel32 = _kernel32()
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
    handle = create_file(
        _api_path(path),
        desired_access,
        share_mode,
        None,
        creation_disposition,
        flags,
        None,
    )
    if handle in (0, -1, _INVALID_HANDLE_VALUE):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(handle)


def _attributes(handle: int) -> int:
    kernel32 = _kernel32()
    get_info = kernel32.GetFileInformationByHandleEx
    get_info.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    get_info.restype = wintypes.BOOL
    info = _FileAttributeTagInfo()
    if not get_info(
        handle,
        _FILE_ATTRIBUTE_TAG_INFO_CLASS,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(info.FileAttributes)


def _final_path(handle: int) -> Path:
    kernel32 = _kernel32()
    get_path = kernel32.GetFinalPathNameByHandleW
    get_path.argtypes = [
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    get_path.restype = wintypes.DWORD
    buffer = ctypes.create_unicode_buffer(32768)
    length = get_path(handle, buffer, len(buffer), 0)
    if length <= 0 or length >= len(buffer):
        raise OSError("acceptance_windows_final_path_unavailable")
    raw = buffer.value
    if raw.startswith("\\\\?\\UNC\\"):
        raw = "\\\\" + raw[8:]
    elif raw.startswith("\\\\?\\"):
        raw = raw[4:]
    return Path(raw)


def _require_handle_path(handle: int, expected: Path, *, directory: bool) -> None:
    attributes = _attributes(handle)
    if attributes & _FILE_ATTRIBUTE_REPARSE_POINT:
        raise ValueError("acceptance_windows_reparse_rejected")
    if bool(attributes & _FILE_ATTRIBUTE_DIRECTORY) is not directory:
        raise ValueError("acceptance_windows_handle_type_invalid")
    if _normalized(_final_path(handle)) != _normalized(expected):
        raise ValueError("acceptance_windows_handle_path_changed")


def _descriptor_handle(descriptor: int) -> int:
    import msvcrt

    return int(msvcrt.get_osfhandle(descriptor))


def _descriptor_identity(descriptor: int) -> tuple[int, int, int, int, int]:
    metadata = os.fstat(descriptor)
    return (
        int(metadata.st_dev),
        int(metadata.st_ino),
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
        int(getattr(metadata, "st_nlink", 1)),
    )


def _duplicate_handle(handle: int) -> int:
    kernel32 = _kernel32()
    current_process = kernel32.GetCurrentProcess
    current_process.restype = wintypes.HANDLE
    duplicate = kernel32.DuplicateHandle
    duplicate.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    duplicate.restype = wintypes.BOOL
    process = current_process()
    duplicated = wintypes.HANDLE()
    if not duplicate(
        process,
        wintypes.HANDLE(handle),
        process,
        ctypes.byref(duplicated),
        0,
        False,
        _DUPLICATE_SAME_ACCESS,
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(duplicated.value)


def _duplicate_descriptor(handle: int, *, writable: bool = False) -> int:
    import msvcrt

    duplicated = _duplicate_handle(handle)
    descriptor = -1
    try:
        flags = (
            (os.O_RDWR if writable else os.O_RDONLY)
            | getattr(os, "O_BINARY", 0)
        )
        descriptor = msvcrt.open_osfhandle(duplicated, flags)
        duplicated = 0
        return descriptor
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        elif duplicated:
            _close_handle(duplicated)
        raise


def _identity_from_handle(handle: int) -> tuple[int, int, int, int, int]:
    descriptor = _duplicate_descriptor(handle)
    try:
        return _descriptor_identity(descriptor)
    finally:
        os.close(descriptor)


def open_windows_directory_lease(
    path: Path,
    *,
    expected_identity: tuple[int, int] | None = None,
    require_delete_authority: bool = True,
) -> WindowsDirectoryLease:
    """Pin a directory while denying write/delete sharing and prove identity."""

    handle = _open_handle(
        path,
        desired_access=_FILE_READ_ATTRIBUTES | (_DELETE if require_delete_authority else 0),
        share_mode=_FILE_SHARE_READ,
        flags=_FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OPEN_REPARSE_POINT,
    )
    try:
        _require_handle_path(handle, path, directory=True)
        identity_value = _identity_from_handle(handle)
        identity = (identity_value[0], identity_value[1])
        if expected_identity is not None and identity != expected_identity:
            raise ValueError("acceptance_windows_directory_identity_changed")
        lease = WindowsDirectoryLease(Path(path), handle, identity)
        handle = 0
        return lease
    except BaseException:
        if handle:
            _close_handle(handle)
        raise
def validate_windows_directory_lease(lease: WindowsDirectoryLease) -> None:
    """Re-prove one pinned directory from its live handle."""

    if not lease.handle:
        raise ValueError("acceptance_windows_directory_lease_closed")
    _require_handle_path(lease.handle, lease.path, directory=True)
    identity = _identity_from_handle(lease.handle)
    if (identity[0], identity[1]) != lease.identity:
        raise ValueError("acceptance_windows_directory_identity_changed")


def validate_windows_directory_lease_exact_path(
    lease: WindowsDirectoryLease,
) -> None:
    """Reject a case- or Unicode-spelling alias for a pinned directory."""
    validate_windows_directory_lease(lease)
    _validate_exact_path_parts(
        _final_path(lease.handle), lease.path,
        "acceptance_windows_directory_path_case_alias",
    )


def _require_parent(path: Path, parent: WindowsDirectoryLease) -> None:
    validate_windows_directory_lease(parent)
    if _normalized(path.parent) != _normalized(parent.path):
        raise ValueError("acceptance_windows_parent_path_mismatch")


def open_windows_source_file(
    path: Path,
    parent: WindowsDirectoryLease,
    *,
    expected_identity: tuple[int, int, int, int, int],
) -> int:
    """Open one private regular source through a pinned verified parent."""

    import msvcrt

    _require_parent(path, parent)
    handle = _open_handle(
        path,
        desired_access=_GENERIC_READ | _FILE_READ_ATTRIBUTES,
        share_mode=_FILE_SHARE_READ,
        flags=_FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT,
    )
    descriptor = -1
    try:
        descriptor = msvcrt.open_osfhandle(
            handle, os.O_RDONLY | getattr(os, "O_BINARY", 0)
        )
        handle = 0
        validate_windows_file_descriptor(
            descriptor, path, expected_identity=expected_identity
        )
        validate_windows_directory_lease(parent)
        return descriptor
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        elif handle:
            _close_handle(handle)
        raise


def open_windows_verified_regular_file(
    path: Path, *, expected_identity: tuple[int, int, int, int, int]
) -> int:
    """Open one exact non-reparse regular file without parent mutation rights."""

    import msvcrt

    handle = _open_handle(
        path,
        desired_access=_GENERIC_READ | _FILE_READ_ATTRIBUTES,
        share_mode=_FILE_SHARE_READ,
        flags=_FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT,
    )
    descriptor = -1
    try:
        descriptor = msvcrt.open_osfhandle(
            handle, os.O_RDONLY | getattr(os, "O_BINARY", 0)
        )
        handle = 0
        validate_windows_file_descriptor(
            descriptor, path, expected_identity=expected_identity
        )
        return descriptor
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        elif handle:
            _close_handle(handle)
        raise


def create_windows_destination_file(
    path: Path, parent: WindowsDirectoryLease
) -> int:
    """Create one absent private file while its verified parent remains pinned."""

    import msvcrt

    _require_parent(path, parent)
    handle = _open_handle(
        path,
        desired_access=_GENERIC_READ | _GENERIC_WRITE | _DELETE | _FILE_READ_ATTRIBUTES,
        share_mode=_FILE_SHARE_READ,
        flags=_FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT,
        creation_disposition=_CREATE_NEW,
    )
    descriptor = -1
    try:
        descriptor = msvcrt.open_osfhandle(
            handle, os.O_RDWR | getattr(os, "O_BINARY", 0)
        )
        handle = 0
        identity = validate_windows_file_descriptor(descriptor, path)
        if identity[2] != 0:
            raise ValueError("acceptance_windows_destination_not_empty")
        validate_windows_directory_lease(parent)
        return descriptor
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        elif handle:
            _close_handle(handle)
        raise


def open_windows_source_file_lease(
    path: Path,
    parent: WindowsDirectoryLease,
    *,
    expected_identity: tuple[int, int, int, int, int],
) -> WindowsFileLease:
    """Pin one private source file without consuming a CRT descriptor."""

    _require_parent(path, parent)
    handle = _open_handle(
        path,
        desired_access=_GENERIC_READ | _FILE_READ_ATTRIBUTES,
        share_mode=_FILE_SHARE_READ,
        flags=_FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT,
    )
    try:
        lease = WindowsFileLease(Path(path), handle, expected_identity)
        validate_windows_file_lease(lease)
        validate_windows_directory_lease(parent)
        handle = 0
        return lease
    finally:
        if handle:
            _close_handle(handle)


def create_windows_destination_file_lease(
    path: Path,
    parent: WindowsDirectoryLease,
) -> WindowsFileLease:
    """Create and pin one private destination outside CRT descriptor limits."""

    _require_parent(path, parent)
    handle = _open_handle(
        path,
        desired_access=(
            _GENERIC_READ | _GENERIC_WRITE | _DELETE | _FILE_READ_ATTRIBUTES
        ),
        share_mode=_FILE_SHARE_READ,
        flags=_FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT,
        creation_disposition=_CREATE_NEW,
    )
    try:
        lease = WindowsFileLease(Path(path), handle, None, writable=True)
        identity = validate_windows_file_lease(lease)
        if identity[2] != 0:
            raise ValueError("acceptance_windows_destination_not_empty")
        validate_windows_directory_lease(parent)
        handle = 0
        return lease
    finally:
        if handle:
            _close_handle(handle)


def open_windows_file_lease_descriptor(lease: WindowsFileLease) -> int:
    """Open one transient CRT descriptor from a retained raw file handle."""

    validate_windows_file_lease(lease)
    descriptor = _duplicate_descriptor(lease.handle, writable=lease.writable)
    try:
        validate_windows_file_descriptor(
            descriptor,
            lease.path,
            expected_identity=lease.expected_identity,
        )
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def validate_windows_file_lease(
    lease: WindowsFileLease,
) -> tuple[int, int, int, int, int]:
    """Re-prove one retained raw file handle without retaining a CRT slot."""

    if not lease.handle:
        raise ValueError("acceptance_windows_file_lease_closed")
    _require_handle_path(lease.handle, lease.path, directory=False)
    descriptor = _duplicate_descriptor(lease.handle, writable=lease.writable)
    try:
        return validate_windows_file_descriptor(
            descriptor,
            lease.path,
            expected_identity=lease.expected_identity,
        )
    finally:
        os.close(descriptor)


def validate_windows_file_descriptor(
    descriptor: int,
    path: Path,
    *,
    expected_identity: tuple[int, int, int, int, int] | None = None,
) -> tuple[int, int, int, int, int]:
    """Prove final path, regular type, link count, volume and file identity."""

    _require_handle_path(_descriptor_handle(descriptor), path, directory=False)
    metadata = os.fstat(descriptor)
    identity = _descriptor_identity(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or identity[4] != 1:
        raise ValueError("acceptance_windows_file_not_private_regular")
    if expected_identity is not None and identity != expected_identity:
        raise ValueError("acceptance_windows_file_identity_changed")
    return identity


def validate_windows_file_descriptor_exact_path(
    descriptor: int, path: Path
) -> None:
    """Reject a case-only alias while preserving volume-anchor equivalence."""
    _validate_exact_path_parts(
        _final_path(_descriptor_handle(descriptor)), path,
        "acceptance_windows_handle_path_case_alias",
    )


def _validate_exact_path_parts(actual: Path, expected_path: Path, error: str) -> None:
    expected = Path(os.path.abspath(os.fspath(expected_path)))
    if (
        not expected.is_absolute()
        or len(expected.parts) != len(actual.parts)
        or os.path.normcase(expected.anchor) != os.path.normcase(actual.anchor)
        or expected.parts[1:] != actual.parts[1:]
    ):
        raise ValueError(error)


def _rename_no_replace(file_handle: int, target: Path) -> None:
    encoded = _api_path(target).encode("utf-16-le")
    offset = _FileRenameInfo.FileName.offset
    # Match the proven FILE_RENAME_INFO allocation pattern: retain the
    # structure's trailing WCHAR/alignment and append the full byte name.
    size = ctypes.sizeof(_FileRenameInfo) + len(encoded)
    storage = ctypes.create_string_buffer(size)
    info = ctypes.cast(storage, ctypes.POINTER(_FileRenameInfo)).contents
    info.ReplaceIfExists = False
    info.RootDirectory = None
    info.FileNameLength = len(encoded)
    ctypes.memmove(ctypes.addressof(storage) + offset, encoded, len(encoded))
    kernel32 = _kernel32()
    set_info = kernel32.SetFileInformationByHandle
    set_info.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    set_info.restype = wintypes.BOOL
    if not set_info(file_handle, _FILE_RENAME_INFO_CLASS, storage, size):
        error = ctypes.get_last_error()
        if error in {5, 32, 80, 183}:
            raise FileExistsError(error, "acceptance_receipt_target_exists")
        raise ctypes.WinError(error)


def _require_descriptor_identity(
    descriptor: int,
    path: Path,
    expected_identity: tuple[int, int, int],
    error: str,
) -> None:
    import msvcrt

    _require_handle_path(msvcrt.get_osfhandle(descriptor), path, directory=False)
    metadata = os.fstat(descriptor)
    identity = (
        int(metadata.st_dev),
        int(metadata.st_ino),
        int(metadata.st_size),
    )
    if identity != expected_identity:
        raise ValueError(error)


def publish_windows_temp_no_replace(
    temporary: Path,
    target: Path,
    *,
    expected_identity: tuple[int, int, int],
) -> None:
    """Rename one verified temp to an absent sibling without replacement."""

    import msvcrt

    if _normalized(temporary.parent) != _normalized(target.parent):
        raise ValueError("acceptance_receipt_not_same_parent")
    parent_handle = _open_handle(
        target.parent,
        desired_access=_FILE_READ_ATTRIBUTES,
        share_mode=_FILE_SHARE_READ,
        flags=_FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OPEN_REPARSE_POINT,
    )
    file_handle = 0
    descriptor = -1
    try:
        _require_handle_path(parent_handle, target.parent, directory=True)
        file_handle = _open_handle(
            temporary,
            desired_access=_GENERIC_READ | _DELETE | _FILE_READ_ATTRIBUTES,
            share_mode=_FILE_SHARE_READ,
            flags=_FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT,
        )
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        descriptor = msvcrt.open_osfhandle(file_handle, flags)
        file_handle = 0
        _require_descriptor_identity(
            descriptor,
            temporary,
            expected_identity,
            "acceptance_receipt_temp_identity_changed",
        )
        _rename_no_replace(msvcrt.get_osfhandle(descriptor), target)
        _require_descriptor_identity(
            descriptor,
            target,
            expected_identity,
            "acceptance_receipt_published_identity_changed",
        )
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        elif file_handle:
            _close_handle(file_handle)
        _close_handle(parent_handle)


__all__ = [
    "WindowsDirectoryLease",
    "WindowsFileLease",
    "create_windows_destination_file",
    "create_windows_destination_file_lease",
    "open_windows_file_lease_descriptor",
    "open_windows_directory_lease",
    "open_windows_source_file",
    "open_windows_source_file_lease",
    "open_windows_verified_regular_file",
    "publish_windows_temp_no_replace",
    "validate_windows_directory_lease",
    "validate_windows_directory_lease_exact_path",
    "validate_windows_file_descriptor",
    "validate_windows_file_descriptor_exact_path",
    "validate_windows_file_lease",
]
