"""Lexical admission policy for governed repository direct reads."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


DENY_BASENAMES = frozenset({
    ".env", ".npmrc", ".pypirc", ".netrc", ".git-credentials", ".dockerconfigjson",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
})
DENY_SEGMENTS = frozenset({
    ".git", ".ssh", ".gnupg", ".aws", ".azure", ".gcloud",
    "node_modules", "__pycache__", ".venv",
})
DENY_SUFFIXES = (".pem", ".key", ".p12", ".keystore", ".pfx", ".jks", ".vsix")
DENY_SUBSTRINGS = ("secret", "credential", "token")
SOURCE_EXTENSIONS = frozenset({
    ".c", ".cc", ".cpp", ".cs", ".go", ".h", ".hpp", ".java",
    ".js", ".jsx", ".md", ".mjs", ".py", ".rs", ".rst", ".ts", ".tsx",
})
SENSITIVE_DATA_NAME = re.compile(
    r"(?:^|[._-])(?:api[_-]?keys?|auth|private[_-]?keys?|service[_-]?accounts?|"
    r"signing[_-]?keys?)(?=[._-]|$)", re.IGNORECASE,
)
WINDOWS_RESERVED = re.compile(
    r"^(?:CON|PRN|AUX|NUL|(?:COM|LPT)(?:[1-9]|\u00b9|\u00b2|\u00b3))$", re.IGNORECASE,
)
SSH_KEY_BASENAME = re.compile(
    r"^id_(?:rsa|dsa|ecdsa|ed25519)(?:\.pub)?(?:[._-]|$)", re.IGNORECASE,
)
SENSITIVE_CONTAINER = re.compile(
    r"(?:^|[._-])(?:secrets?|credentials?|api[_-]?keys?|private[_-]?keys?|"
    r"signing[_-]?keys?|service[_-]?accounts?)(?=[._-]|$)|"
    r"^(?:tokens?)(?:[._-](?:data|store|cache|secret|vault))?$", re.IGNORECASE,
)
SENSITIVE_SOURCE_BASENAME = re.compile(
    r"(?:^|[._-])(?:secrets?|credentials?|api[_-]?keys?|private[_-]?keys?|"
    r"signing[_-]?keys?|service[_-]?accounts?)(?=[._-]|$)", re.IGNORECASE,
)


def _canonical_segments(value: str) -> list[str]:
    return [segment.rstrip(". ") for segment in value.lower().split("/")]


def _is_source_path(parts: list[str]) -> bool:
    return bool(parts) and Path(parts[-1]).suffix.lower() in SOURCE_EXTENSIONS


def _is_reserved_segment(segment: str) -> bool:
    return bool(WINDOWS_RESERVED.fullmatch(segment.split(".", 1)[0]))


def _is_secret_data(parts: list[str]) -> bool:
    base = parts[-1]
    if any(SENSITIVE_CONTAINER.search(segment) for segment in parts):
        return True
    if _is_source_path(parts):
        return bool(SENSITIVE_SOURCE_BASENAME.search(base))
    return any(marker in segment for segment in parts for marker in DENY_SUBSTRINGS) \
        or bool(SENSITIVE_DATA_NAME.search(base))


def _has_denied_suffix(base: str) -> bool:
    return any(
        base == suffix[1:] or base.startswith(suffix[1:] + ".")
        or base.endswith(suffix) or f"{suffix}." in base
        for suffix in DENY_SUFFIXES
    )


def direct_read_deny_reason(rel_norm: str) -> Optional[str]:
    """Return a stable denial reason without touching the filesystem."""

    if not rel_norm:
        return "path_missing"
    if any(ord(character) < 32 or ord(character) == 127 for character in rel_norm):
        return "path_missing"
    if rel_norm.startswith(("/", "//")) or (len(rel_norm) >= 2 and rel_norm[1] == ":"):
        return "absolute_path"
    if ":" in rel_norm:
        return "alternate_data_stream"
    parts = _canonical_segments(rel_norm)
    if any(not part or part in {".", ".."} for part in parts):
        return "traversal"
    if any(_is_reserved_segment(part) for part in parts):
        return "denied_segment"
    if any(
        part in DENY_SEGMENTS or part == ".env" or part.startswith(".env.")
        or SENSITIVE_CONTAINER.search(part)
        for part in parts[:-1]
    ):
        return "denied_segment"
    if parts[-1] in DENY_SEGMENTS:
        return "denied_segment"
    if _is_secret_data(parts):
        return "denied_secret_like"
    base = parts[-1]
    if SSH_KEY_BASENAME.match(base):
        return "denied_basename"
    if any(base == name or base.startswith(name + ".") for name in DENY_BASENAMES):
        return "denied_basename"
    if _has_denied_suffix(base):
        return "denied_extension"
    return None


def normalize_direct_read_path(raw: str) -> str:
    """Normalize quoting and separators while preserving absolute prefixes."""

    normalized = str(raw or "").strip().replace("\\", "/").strip("`'\"")
    if normalized in ("", "."):
        return ""
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized
