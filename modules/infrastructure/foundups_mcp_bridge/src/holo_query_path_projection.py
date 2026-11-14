"""Repository-relative projection for untrusted HoloIndex result paths."""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Mapping, NoReturn
from unicodedata import category

from holo_index.cli.direct_read_path_policy import WINDOWS_RESERVED
_PATH_FIELDS = ("path", "file", "location")
_PATH_ERROR = "query_evidence_path_outside_repository"
_LOCATION_DESCRIPTOR = re.compile(r"^(?:[1-9][0-9]*|[A-Za-z_][A-Za-z0-9_.]*\(\)|[A-Z][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)$")
_LOCATION_ANNOTATED_SYMBOL = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\s+\S(?:.*\S)?$")
_LOCATION_CALL = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\([^)]*\)$")
_LOCATION_ANNOTATION_SEPARATORS = (" - ", " \u2014 ", " \u2013 ")
_MAX_LOCATION_CHARS = 4_096
_SYMBOL_SUFFIXES = frozenset(
    ".c .cc .cpp .cs .go .h .hpp .java .js .jsx .md .mjs .py .rs .ts .tsx".split())


def _reject_path() -> NoReturn:
    raise ValueError(_PATH_ERROR)


def _unsafe_character(char: str) -> bool:
    return category(char) in {"Cc", "Cf", "Cs"} or (char.isspace() and char != " ")


def _root_flavor(value: str) -> tuple[str, PurePosixPath | PureWindowsPath]:
    text = str(value or "")
    if not text or any(_unsafe_character(char) for char in text):
        _reject_path()
    windows = PureWindowsPath(text)
    posix = PurePosixPath(text.replace("\\", "/"))
    if windows.drive and windows.is_absolute():
        return "windows", windows
    if windows.root and text.startswith("\\"):
        _reject_path()
    if posix.is_absolute() and not windows.drive:
        return "posix", posix
    _reject_path()


def _relative_parts(value: str) -> tuple[str, ...]:
    normalized = str(value or "").replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        _reject_path()
    windows = PureWindowsPath(value)
    if windows.drive or windows.root:
        _reject_path()
    return path.parts


def _validated_parts(parts: tuple[str, ...], *, windows: bool) -> tuple[str, ...]:
    if not parts:
        _reject_path()
    for part in parts:
        if part in {"", ".", ".."} or any(_unsafe_character(char) for char in part):
            _reject_path()
        if part.rstrip(" .") != part or any(char in '<>:"|?*' for char in part):
            _reject_path()
        if not windows:
            continue
        stem = part.split(".", 1)[0].rstrip(" .")
        if WINDOWS_RESERVED.fullmatch(stem):
            _reject_path()
    return parts


def _windows_projection(text: str, root: PureWindowsPath) -> tuple[str, ...]:
    windows = PureWindowsPath(text)
    posix = PurePosixPath(text.replace("\\", "/"))
    if posix.is_absolute() and not windows.drive:
        _reject_path()
    if any(part == ".." for part in windows.parts):
        _reject_path()
    if not windows.drive and not windows.root:
        return _relative_parts(text)
    if not windows.is_absolute():
        _reject_path()
    try:
        return windows.relative_to(root).parts
    except ValueError:
        _reject_path()


def _posix_projection(text: str, root: PurePosixPath) -> tuple[str, ...]:
    windows = PureWindowsPath(text)
    posix = PurePosixPath(text.replace("\\", "/"))
    if windows.drive or text.startswith("\\") or any(part == ".." for part in posix.parts):
        _reject_path()
    if not posix.is_absolute():
        return _relative_parts(text)
    try:
        return posix.relative_to(root).parts
    except ValueError:
        _reject_path()


def project_repository_path(value: str, repo_root: str) -> str:
    """Project one path beneath ``repo_root`` without host-dependent parsing."""
    text = str(value or "")
    if not text:
        return text
    flavor, root = _root_flavor(repo_root)
    project = _windows_projection if flavor == "windows" else _posix_projection
    parts = project(text, root)
    return PurePosixPath(
        *_validated_parts(parts, windows=flavor == "windows")
    ).as_posix()


def _location_parts(value: str) -> tuple[str, str]:
    split_at = value.rfind(":")
    if split_at <= 1:
        return value, ""
    descriptor_text = value[split_at + 1:]
    call = _LOCATION_CALL.match(descriptor_text)
    annotated = _LOCATION_ANNOTATED_SYMBOL.fullmatch(descriptor_text)
    descriptor = f"{call.group(1)}()" if call else (
        f"{annotated.group(1)}()" if annotated else descriptor_text)
    if not _LOCATION_DESCRIPTOR.fullmatch(descriptor):
        return value, ""
    return value[:split_at], descriptor


def _location_identity(value: str) -> str:
    if (
        not value
        or len(value) > _MAX_LOCATION_CHARS
        or value.rstrip(" .") != value
        or any(_unsafe_character(char) for char in value)
    ):
        _reject_path()
    for separator in _LOCATION_ANNOTATION_SEPARATORS:
        if separator in value:
            identity, annotation = value.split(separator, 1)
            if not identity or not annotation:
                _reject_path()
            return identity
    return value


def project_repository_location(
    value: str, repo_root: str, *, expected_path: str = "") -> str:
    """Project a path plus an optional bound line or code-symbol descriptor."""
    path_value, descriptor = _location_parts(_location_identity(value))
    projected = project_repository_path(path_value, repo_root)
    if expected_path:
        flavor, _root = _root_flavor(repo_root)
        matched = (
            projected.casefold() == expected_path.casefold()
            if flavor == "windows"
            else projected == expected_path
        )
        if not matched:
            _reject_path()
    if not descriptor:
        return projected
    if not descriptor.isdigit():
        if PurePosixPath(projected).suffix.lower() not in _SYMBOL_SUFFIXES:
            _reject_path()
    return f"{projected}:{descriptor}"


def project_result_hit(item: Mapping[str, Any], repo_root: str) -> dict[str, Any]:
    """Copy and project one canonical HoloIndex hit mapping."""
    projected = deepcopy(dict(item))
    if not any(field in projected for field in _PATH_FIELDS):
        raise ValueError("query_evidence_schema_invalid")
    for field in ("path", "file"):
        if field not in projected:
            continue
        value = projected[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError("query_evidence_path_invalid")
        projected[field] = project_repository_path(value, str(repo_root))
    expected = str(projected.get("path") or projected.get("file") or "")
    if "location" in projected:
        value = projected["location"]
        if not isinstance(value, str) or not value.strip():
            raise ValueError("query_evidence_path_invalid")
        projected["location"] = project_repository_location(
            value, str(repo_root), expected_path=expected,
        )
    flavor, _root = _root_flavor(str(repo_root))
    identities = {
        projected[field].casefold() if flavor == "windows" else projected[field]
        for field in ("path", "file") if field in projected
    }
    if len(identities) > 1:
        _reject_path()
    return projected


__all__ = ["project_repository_location", "project_repository_path",
           "project_result_hit"]
