"""Canonical HoloIndex storage-path and failure contract.

This module is intentionally dependency-light so CLI, core, and runtime
adapters can resolve the same store without importing ChromaDB or model code.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping


HOLOINDEX_SSD_PATH_ENV = "HOLOINDEX_SSD_PATH"
LEGACY_HOLO_SSD_PATH_ENV = "HOLO_SSD_PATH"
READONLY_QUERY_ENV = "HOLOINDEX_QUERY_READONLY"

STORAGE_UNAVAILABLE_CODE = "HOLOINDEX_STORAGE_UNAVAILABLE"
STORAGE_NOT_WRITABLE_CODE = "HOLOINDEX_STORAGE_NOT_WRITABLE"
STORAGE_PATH_MISMATCH_CODE = "HOLOINDEX_STORAGE_PATH_MISMATCH"
COLLECTION_UNAVAILABLE_CODE = "HOLOINDEX_COLLECTION_UNAVAILABLE"

_WRITE_DENIAL_MARKERS = (
    "attempt to write a readonly database",
    "attempt to write a read-only database",
    "readonly database",
    "read-only database",
    "permission denied",
    "access is denied",
    "access denied",
    "operation not permitted",
    "code: 8",
)


class HoloIndexStorageError(RuntimeError):
    """Stable, machine-readable HoloIndex storage failure."""

    def __init__(
        self,
        code: str,
        *,
        path: str | Path,
        operation: str,
        detail: str = "",
    ) -> None:
        self.code = str(code)
        self.path = Path(path)
        self.operation = str(operation)
        self.detail = str(detail)
        message = f"[{self.code}] {self.operation} failed for {self.path}"
        if self.detail:
            message += f": {self.detail}"
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Return the public error shape used by CLI/runtime adapters."""

        return {
            "ok": False,
            "error": self.code,
            "operation": self.operation,
            "ssd_path": str(self.path),
            "detail": self.detail,
        }


def _platform_default_ssd_path(environ: Mapping[str, str]) -> Path:
    """Return an absolute default that cannot become repo-relative on POSIX."""

    if os.name == "nt":
        return Path("E:/HoloIndex")
    xdg_data_home = str(environ.get("XDG_DATA_HOME", "")).strip()
    configured_data_home = Path(xdg_data_home).expanduser() if xdg_data_home else None
    data_home = (
        configured_data_home
        if configured_data_home is not None and configured_data_home.is_absolute()
        else Path.home() / ".local" / "share"
    )
    return data_home / "foundups" / "holoindex"


def _absolute_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve(strict=False)


def resolve_holoindex_ssd_path(
    explicit: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolve one canonical store root.

    Precedence is explicit argument, ``HOLOINDEX_SSD_PATH``, legacy
    ``HOLO_SSD_PATH``, then a platform-safe absolute default.
    """

    env = os.environ if environ is None else environ
    explicit_text = str(explicit).strip() if explicit is not None else ""
    candidate: str | Path
    if explicit_text:
        candidate = explicit_text
    else:
        canonical_env = str(env.get(HOLOINDEX_SSD_PATH_ENV, "")).strip()
        legacy_env = str(env.get(LEGACY_HOLO_SSD_PATH_ENV, "")).strip()
        candidate = canonical_env or legacy_env or _platform_default_ssd_path(env)
    return _absolute_path(candidate)


def storage_path_identity(path: str | Path) -> str:
    """Return a case-normalized absolute identity for singleton binding."""

    return os.path.normcase(str(_absolute_path(path)))


def readonly_query_enabled(*, environ: Mapping[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return str(env.get(READONLY_QUERY_ENV, "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }


def classify_storage_exception(
    exc: BaseException,
    *,
    path: str | Path,
    operation: str,
) -> HoloIndexStorageError:
    """Map backend-specific failures onto stable public storage codes."""

    raw_detail = str(exc).strip()
    normalized = raw_detail.lower()
    code = (
        STORAGE_NOT_WRITABLE_CODE
        if any(marker in normalized for marker in _WRITE_DENIAL_MARKERS)
        else STORAGE_UNAVAILABLE_CODE
    )
    detail = f"{type(exc).__name__}: {raw_detail}" if raw_detail else type(exc).__name__
    return HoloIndexStorageError(
        code,
        path=path,
        operation=operation,
        detail=detail,
    )


__all__ = [
    "COLLECTION_UNAVAILABLE_CODE",
    "HOLOINDEX_SSD_PATH_ENV",
    "HoloIndexStorageError",
    "LEGACY_HOLO_SSD_PATH_ENV",
    "READONLY_QUERY_ENV",
    "STORAGE_NOT_WRITABLE_CODE",
    "STORAGE_PATH_MISMATCH_CODE",
    "STORAGE_UNAVAILABLE_CODE",
    "classify_storage_exception",
    "readonly_query_enabled",
    "resolve_holoindex_ssd_path",
    "storage_path_identity",
]
