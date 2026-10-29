"""Bounded, metadata-only secret hints for Git-tracked module source.

This heuristic is not the hosted tree/history security gate. Environment files
are reported by name without opening them; test directories are not exempted.
"""

from pathlib import Path
import re
import stat
from typing import Iterable, List, NamedTuple, Optional


MAX_FILE_BYTES = 2 * 1024 * 1024
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".yaml", ".yml", ".conf", ".config"}


class SourceHint(NamedTuple):
    """Only location metadata crosses the source-inspection boundary."""
    category: str
    path: str
    line: Optional[int] = None


def _literal_pattern(names: str, minimum: int) -> str:
    """Require a complete credential identifier and a quoted literal value."""
    return (
        rf"(?i)(?<![\w-])(?:[a-z0-9]+[_-])*(?:{names})[\"']?\s*[=:]\s*"
        rf"(?P<quote>[\"'])(?P<value>[^\"'\r\n]{{{minimum},}})(?P=quote)"
    )


SECRET_PATTERNS = [
    _literal_pattern("password|passwd|pwd", 8),
    _literal_pattern("api[_-]?key|apikey|secret|token|access[_-]?key", 16),
    _literal_pattern("private[_-]?key", 32),
    r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----",
    r"(?i)mongodb://[^/\s]+:[^@\s]+@",
    r"(?i)postgres://[^/\s]+:[^@\s]+@",
]


def _environment_name(path: Path) -> bool:
    name = path.name.casefold()
    return name == ".env" or name.startswith(".env.") or name.endswith(".env")


def _source_bytes(root: Path, relative: str) -> bytes:
    """Reject redirects and special files before a bounded content read."""
    parts = relative.split("/")
    if not relative.startswith("modules/") or any(p in {"", ".", ".."} for p in parts):
        raise ValueError("invalid tracked path")
    if "\\" in relative or "\x00" in relative:
        raise ValueError("invalid tracked path")
    current = root
    for part in parts:
        current = current / part
        metadata = current.lstat()
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise ValueError("redirected path")
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("non-regular file")
    with current.open("rb") as handle:
        data = handle.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("file exceeds byte limit")
    return data


def inspect_tracked_source(modules_dir: Path, tracked_paths: Iterable[str]) -> List[SourceHint]:
    """Inspect selected tracked working-tree sources without returning values."""
    findings = []
    patterns = [re.compile(pattern) for pattern in SECRET_PATTERNS]
    for relative in sorted(set(tracked_paths)):
        path = Path(relative)
        if _environment_name(path):
            findings.append(SourceHint("environment", relative))
            continue
        if path.suffix.casefold() not in SOURCE_SUFFIXES:
            continue
        try:
            content = _source_bytes(modules_dir.parent, relative).decode("utf-8-sig", errors="strict")
        except (OSError, UnicodeError, ValueError):
            findings.append(SourceHint("incomplete", relative))
            continue
        for number, line in enumerate(content.splitlines(), 1):
            if any(pattern.search(line) for pattern in patterns):
                findings.append(SourceHint("literal", relative, number))
    return findings
