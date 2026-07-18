"""Fail-closed helpers for runtime artifacts and untrusted telemetry text."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import tempfile
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping


_DEVICE_PATH_PREFIXES = ("\\\\", "//?/", "//./")
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
_PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN [^-\r\n]*PRIVATE KEY-----.*?"
    r"(?:-----END [^-\r\n]*PRIVATE KEY-----|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b((?:(?:[a-z0-9]+[_-])*(?:api[_-]?key|access[_-]?token|"
    r"refresh[_-]?token|auth(?:orization)?|password|passwd|secret|private[_-]?key|"
    r"client[_-]?secret|cookie|session[_-]?id)(?:[_-][a-z0-9]+)*|token|"
    r"(?:[a-z0-9]+[_-])*(?:id|auth|session|oauth|csrf)[_-]?token))"
    r"\b\s*[:=](?!\s*\[REDACTED(?:_[A-Z]+)?\])\s*"
    r"(?:\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,;]+)"
)
_QUERY_SECRET = re.compile(
    r"(?i)([?&](?:api[_-]?key|access[_-]?token|token|auth|password|secret|signature)=)"
    r"(?!\[REDACTED\])[^&#\s]+"
)
_AUTH_HEADER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]+")
_COOKIE_HEADER = re.compile(
    r"(?i)\b(set-cookie|cookie)\s*:(?!\s*\[REDACTED\])\s*[^\r\n]+"
)
_CREDENTIAL_URL = re.compile(
    r"(?i)\b([a-z][a-z0-9+.-]*://[^\s/:@]+:)(?!\[REDACTED\])[^\s/@]+(@)"
)
_KNOWN_TOKEN = re.compile(
    r"(?i)\b(?:sk-[a-z0-9_-]{12,}|gh[opusr]_[a-z0-9_]{12,}|"
    r"ya29\.[a-z0-9_-]{12,}|AKIA[0-9A-Z]{16}|AIza[a-z0-9_-]{20,}|"
    r"xox[baprs]-[a-z0-9-]{12,})\b"
)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_SENSITIVE_MAPPING_KEY = re.compile(
    r"(?i)(?:(?:^|_)(?:api_key|access_token|refresh_token|authorization|password|"
    r"passwd|secret|private_key|client_secret|cookie|session_id|sovereign_token)"
    r"(?:$|_)|^token$|(?:^|_)(?:id|auth|session|oauth|csrf)_?token$)"
)


@dataclass(frozen=True)
class RuntimeTextRedaction:
    text: str
    replacements: int
    truncated: bool


def validate_runtime_artifact_path(
    path: Path | str,
    *,
    repo_root: Path | str,
    allowed_root: Path | str | None = None,
) -> Path:
    """Resolve a writable artifact path outside source and within its runtime root."""

    raw = str(path or "").strip()
    if not raw or "\x00" in raw or raw.startswith(_DEVICE_PATH_PREFIXES):
        raise ValueError("runtime_artifact_path_invalid")
    _validate_path_components(raw)

    repo = Path(repo_root).resolve()
    allowed = Path(allowed_root).resolve() if allowed_root else None
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        if allowed is None:
            raise ValueError("runtime_artifact_path_not_absolute")
        candidate = allowed / candidate
    if _contains_link_component(candidate):
        raise ValueError("runtime_artifact_path_link_rejected")
    resolved = candidate.resolve()

    if resolved.parent == resolved:
        raise ValueError("runtime_artifact_path_filesystem_root")
    if _is_relative_to(resolved, repo):
        raise ValueError("runtime_artifact_path_inside_repo")
    if allowed is not None:
        if _is_relative_to(allowed, repo):
            raise ValueError("runtime_artifact_root_inside_repo")
        if _is_relative_to(repo, allowed):
            raise ValueError("runtime_artifact_root_contains_repo")
        if not _is_relative_to(resolved, allowed):
            raise ValueError("runtime_artifact_path_outside_runtime_root")
    return _without_windows_extended_prefix(resolved)


def validate_runtime_root_path(path: Path | str, *, repo_root: Path | str) -> Path:
    """Validate that a runtime root is neither source nor an ancestor of source."""

    return validate_runtime_artifact_path(
        path,
        repo_root=repo_root,
        allowed_root=path,
    )


def secure_append_runtime_text(
    path: Path | str,
    text: str,
    *,
    repo_root: Path | str,
    allowed_root: Path | str | None = None,
    validate_existing: Callable[[str], None] | None = None,
    max_existing_bytes: int = 8 * 1024 * 1024,
) -> Path:
    """Append text under a cross-process lock with link and descriptor checks."""

    target = validate_runtime_artifact_path(
        path,
        repo_root=repo_root,
        allowed_root=allowed_root,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target = validate_runtime_artifact_path(
        target,
        repo_root=repo_root,
        allowed_root=allowed_root,
    )
    encoded = text.encode("utf-8")

    with _exclusive_lock(target):
        target = validate_runtime_artifact_path(
            path,
            repo_root=repo_root,
            allowed_root=allowed_root,
        )
        descriptor, created = _open_runtime_file(target)
        final_path: Path | None = None
        opened_stat: os.stat_result | None = None
        cleanup_created = False
        try:
            opened_stat = os.fstat(descriptor)
            _require_private_regular_file(opened_stat)
            final_path = _descriptor_final_path(descriptor)
            _verify_descriptor_path(
                final_path,
                expected=target,
                repo_root=repo_root,
                allowed_root=allowed_root,
            )
            if opened_stat.st_size > max_existing_bytes:
                raise ValueError("runtime_artifact_retention_limit_exceeded")
            os.lseek(descriptor, 0, os.SEEK_SET)
            existing = _read_descriptor_text(descriptor, opened_stat.st_size)
            if validate_existing is not None:
                validate_existing(existing)
            os.lseek(descriptor, 0, os.SEEK_END)
            remaining = memoryview(encoded)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise OSError("runtime_artifact_append_incomplete")
                remaining = remaining[written:]
            os.fsync(descriptor)
        except Exception:
            cleanup_created = created and final_path is not None
            raise
        finally:
            os.close(descriptor)
            if cleanup_created and final_path is not None and opened_stat is not None:
                _remove_created_file(final_path, opened_stat)
    return target


def secure_replace_runtime_text(
    path: Path | str,
    text: str,
    *,
    repo_root: Path | str,
    allowed_root: Path | str | None = None,
) -> Path:
    """Replace a runtime artifact through a verified file descriptor."""

    target = validate_runtime_artifact_path(
        path,
        repo_root=repo_root,
        allowed_root=allowed_root,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target = validate_runtime_artifact_path(
        target,
        repo_root=repo_root,
        allowed_root=allowed_root,
    )
    with _exclusive_lock(target):
        target = validate_runtime_artifact_path(
            path,
            repo_root=repo_root,
            allowed_root=allowed_root,
        )
        descriptor, created = _open_runtime_file(target)
        final_path: Path | None = None
        opened_stat: os.stat_result | None = None
        cleanup_created = False
        try:
            opened_stat = os.fstat(descriptor)
            _require_private_regular_file(opened_stat)
            final_path = _descriptor_final_path(descriptor)
            _verify_descriptor_path(
                final_path,
                expected=target,
                repo_root=repo_root,
                allowed_root=allowed_root,
            )
            os.ftruncate(descriptor, 0)
            os.lseek(descriptor, 0, os.SEEK_SET)
            remaining = memoryview(text.encode("utf-8"))
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise OSError("runtime_artifact_replace_incomplete")
                remaining = remaining[written:]
            os.fsync(descriptor)
        except Exception:
            cleanup_created = created and final_path is not None
            raise
        finally:
            os.close(descriptor)
            if cleanup_created and final_path is not None and opened_stat is not None:
                _remove_created_file(final_path, opened_stat)
    return target


@contextmanager
def runtime_operation_lock(identity: Path | str) -> Iterator[None]:
    """Serialize a bounded runtime operation without creating repo lock files."""

    raw = str(identity or "").strip()
    if not raw or len(raw) > 8192 or "\x00" in raw:
        raise ValueError("runtime_operation_lock_identity_invalid")
    with _exclusive_lock(Path(raw)):
        yield


def redact_runtime_text(value: object, *, max_chars: int = 4096) -> RuntimeTextRedaction:
    """Normalize, bound, and redact secret-shaped text before runtime persistence."""

    raw = unicodedata.normalize("NFKC", str(value or ""))
    normalized = "".join(
        char
        for char in raw
        if char in "\t\r\n" or unicodedata.category(char) not in {"Cc", "Cf"}
    )
    limit = max(int(max_chars), 0)
    processing_limit = max(limit * 16, 64 * 1024)
    processing_truncated = len(normalized) > processing_limit
    text = normalized[:processing_limit]
    replacements = 0

    def replace(pattern: re.Pattern[str], replacement: str | object) -> None:
        nonlocal text, replacements
        text, count = pattern.subn(replacement, text)
        replacements += count

    replace(_PRIVATE_KEY_BLOCK, "[REDACTED_PRIVATE_KEY]")
    replace(_COOKIE_HEADER, lambda match: f"{match.group(1)}: [REDACTED]")
    replace(_AUTH_HEADER, lambda match: f"{match.group(1)} [REDACTED]")
    replace(
        _SENSITIVE_ASSIGNMENT,
        lambda match: f"{match.group(1)}=[REDACTED]",
    )
    replace(_QUERY_SECRET, lambda match: f"{match.group(1)}[REDACTED]")
    replace(_CREDENTIAL_URL, lambda match: f"{match.group(1)}[REDACTED]{match.group(2)}")
    replace(_KNOWN_TOKEN, "[REDACTED_TOKEN]")
    replace(_JWT, "[REDACTED_JWT]")
    if _contains_secret_shape(text):
        text = "[REDACTION_FAILED]"
        replacements += 1
    truncated = processing_truncated or len(text) > limit
    return RuntimeTextRedaction(
        text=text[:limit],
        replacements=replacements,
        truncated=truncated,
    )


def secure_read_confined_bytes(
    path: Path | str,
    *,
    allowed_root: Path | str,
    offset: int = 0,
    max_bytes: int = 64 * 1024,
) -> tuple[bytes, int]:
    """Read a source file only after its descriptor proves root confinement."""

    raw = str(path or "").strip()
    if not raw or "\x00" in raw or raw.startswith(_DEVICE_PATH_PREFIXES):
        raise ValueError("confined_read_path_invalid")
    root_candidate = Path(os.path.abspath(Path(allowed_root).expanduser()))
    expected_candidate = Path(raw).expanduser()
    if not expected_candidate.is_absolute():
        expected_candidate = root_candidate / expected_candidate
    expected_candidate = Path(os.path.abspath(expected_candidate))
    if not _is_relative_to(expected_candidate, root_candidate):
        raise ValueError("confined_read_path_outside_root")
    if _contains_link_component(root_candidate) or _contains_link_component(
        expected_candidate
    ):
        raise ValueError("confined_read_path_link_rejected")

    root = _without_windows_extended_prefix(root_candidate.resolve(strict=True))
    expected = _without_windows_extended_prefix(
        expected_candidate.resolve(strict=True)
    )
    if not _is_relative_to(expected, root):
        raise ValueError("confined_read_path_outside_root")

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(expected, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("confined_read_target_not_regular")
        final_path = _descriptor_final_path(descriptor)
        final_resolved = _without_windows_extended_prefix(final_path.resolve(strict=True))
        if not _is_relative_to(final_resolved, root):
            raise ValueError("confined_read_descriptor_outside_root")
        if os.path.normcase(str(final_resolved)) != os.path.normcase(str(expected)):
            raise ValueError("confined_read_descriptor_path_mismatch")
        position = min(max(int(offset), 0), int(metadata.st_size))
        os.lseek(descriptor, position, os.SEEK_SET)
        data = os.read(descriptor, max(min(int(max_bytes), 1024 * 1024), 0))
        return data, int(os.lseek(descriptor, 0, os.SEEK_CUR))
    finally:
        os.close(descriptor)


def redact_runtime_value(
    value: Any,
    *,
    max_depth: int = 8,
    max_items: int = 128,
    max_text_chars: int = 4096,
) -> Any:
    """Recursively redact nested runtime reports before persistence or feedback."""

    def walk(item: Any, depth: int) -> Any:
        if depth > max_depth:
            return "[REDACTED_DEPTH_LIMIT]"
        if isinstance(item, Mapping):
            result: dict[str, Any] = {}
            for index, (raw_key, raw_value) in enumerate(item.items()):
                if index >= max_items:
                    result["_truncated"] = True
                    break
                key = redact_runtime_text(raw_key, max_chars=128).text
                if _SENSITIVE_MAPPING_KEY.search(key.replace("-", "_")):
                    result[key] = "[REDACTED]"
                else:
                    result[key] = walk(raw_value, depth + 1)
            return result
        if isinstance(item, tuple):
            return tuple(walk(entry, depth + 1) for entry in item[:max_items])
        if isinstance(item, list):
            return [walk(entry, depth + 1) for entry in item[:max_items]]
        if isinstance(item, (set, frozenset)):
            return [walk(entry, depth + 1) for entry in list(item)[:max_items]]
        if isinstance(item, str):
            return redact_runtime_text(item, max_chars=max_text_chars).text
        if item is None or isinstance(item, (bool, int, float)):
            return item
        return redact_runtime_text(item, max_chars=max_text_chars).text

    return walk(value, 0)


def _contains_secret_shape(text: str) -> bool:
    return any(
        pattern.search(text)
        for pattern in (
            _PRIVATE_KEY_BLOCK,
            _COOKIE_HEADER,
            _AUTH_HEADER,
            _SENSITIVE_ASSIGNMENT,
            _QUERY_SECRET,
            _CREDENTIAL_URL,
            _KNOWN_TOKEN,
            _JWT,
        )
    )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _without_windows_extended_prefix(path: Path) -> Path:
    raw = str(path)
    normalized = raw.replace("\\", "/")
    if normalized.startswith("//?/UNC/"):
        return Path("//" + normalized[8:])
    if normalized.startswith("//?/"):
        return Path(normalized[4:])
    return path


def _validate_path_components(raw: str) -> None:
    candidate = Path(raw)
    anchor = candidate.anchor
    for component in candidate.parts:
        if component == anchor:
            continue
        if component.endswith((" ", ".")):
            raise ValueError("runtime_artifact_path_ambiguous_component")
        basename = component.split(".", 1)[0].upper()
        if basename in _WINDOWS_RESERVED_NAMES:
            raise ValueError("runtime_artifact_path_reserved_name")
        if ":" in component:
            raise ValueError("runtime_artifact_path_alternate_stream")


def _contains_link_component(path: Path) -> bool:
    current = Path(path.anchor) if path.is_absolute() else Path()
    for component in path.parts:
        if component == path.anchor:
            continue
        current = current / component
        if not current.exists():
            continue
        metadata = os.lstat(current)
        reparse = bool(
            getattr(metadata, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        )
        if (
            stat.S_ISLNK(metadata.st_mode)
            or reparse
            or bool(getattr(current, "is_junction", lambda: False)())
        ):
            return True
    return False


def _require_private_regular_file(metadata: os.stat_result) -> None:
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("runtime_artifact_target_not_regular")
    if int(getattr(metadata, "st_nlink", 1)) != 1:
        raise ValueError("runtime_artifact_target_link_count")


def _open_runtime_file(path: Path) -> tuple[int, bool]:
    common = os.O_RDWR | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        return os.open(path, common), False
    except FileNotFoundError:
        try:
            return os.open(path, common | os.O_CREAT | os.O_EXCL, 0o600), True
        except FileExistsError:
            return os.open(path, common), False


def _descriptor_final_path(descriptor: int) -> Path:
    if os.name == "nt":
        import ctypes
        import msvcrt
        from ctypes import wintypes

        handle = msvcrt.get_osfhandle(descriptor)
        buffer = ctypes.create_unicode_buffer(32768)
        get_final_path = ctypes.windll.kernel32.GetFinalPathNameByHandleW
        get_final_path.argtypes = [
            wintypes.HANDLE,
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
        ]
        get_final_path.restype = wintypes.DWORD
        length = get_final_path(
            handle,
            buffer,
            len(buffer),
            0,
        )
        if length <= 0 or length >= len(buffer):
            raise OSError("runtime_artifact_final_path_unavailable")
        return _without_windows_extended_prefix(Path(buffer.value))
    proc_path = Path(f"/proc/self/fd/{descriptor}")
    if proc_path.exists():
        return proc_path.resolve(strict=True)
    raise OSError("runtime_artifact_final_path_unavailable")


def _verify_descriptor_path(
    final_path: Path,
    *,
    expected: Path,
    repo_root: Path | str,
    allowed_root: Path | str | None,
) -> None:
    verified = validate_runtime_artifact_path(
        final_path,
        repo_root=repo_root,
        allowed_root=allowed_root,
    )
    if os.path.normcase(str(verified)) != os.path.normcase(str(expected)):
        raise ValueError("runtime_artifact_descriptor_path_mismatch")


def _read_descriptor_text(descriptor: int, size: int) -> str:
    remaining = max(int(size), 0)
    chunks: list[bytes] = []
    while remaining:
        chunk = os.read(descriptor, min(remaining, 64 * 1024))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks).decode("utf-8")


def _remove_created_file(path: Path, expected: os.stat_result) -> None:
    try:
        current = path.stat()
        if (current.st_dev, current.st_ino) == (expected.st_dev, expected.st_ino):
            path.unlink(missing_ok=True)
    except OSError:
        pass


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    lock_key = hashlib.sha256(os.path.normcase(str(path)).encode("utf-8")).hexdigest()
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        create_mutex = kernel32.CreateMutexW
        create_mutex.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        create_mutex.restype = wintypes.HANDLE
        wait_for_single = kernel32.WaitForSingleObject
        wait_for_single.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        wait_for_single.restype = wintypes.DWORD
        release_mutex = kernel32.ReleaseMutex
        release_mutex.argtypes = [wintypes.HANDLE]
        release_mutex.restype = wintypes.BOOL
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL
        handle = create_mutex(None, False, f"Local\\FoundupsRuntime-{lock_key}")
        if not handle:
            raise OSError("runtime_artifact_mutex_create_failed")
        wait_result = wait_for_single(handle, 0xFFFFFFFF)
        if wait_result not in (0x00000000, 0x00000080):
            close_handle(handle)
            raise OSError("runtime_artifact_mutex_wait_failed")
        try:
            yield
        finally:
            release_mutex(handle)
            close_handle(handle)
        return

    import fcntl

    lock_root = Path(tempfile.gettempdir()) / "foundups-runtime-locks"
    lock_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = lock_root / f"{lock_key}.lock"
    descriptor = os.open(
        lock_path,
        os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        _require_private_regular_file(os.fstat(descriptor))
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


__all__ = [
    "RuntimeTextRedaction",
    "redact_runtime_text",
    "redact_runtime_value",
    "runtime_operation_lock",
    "secure_append_runtime_text",
    "secure_read_confined_bytes",
    "secure_replace_runtime_text",
    "validate_runtime_artifact_path",
    "validate_runtime_root_path",
]
