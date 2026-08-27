"""Canonical parsing primitives for text emitted by the WSP 62 producer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .improvement_job_identity import canonical_improvement_repo_path


_WSP62_PATTERN = re.compile(
    r"^WSP\s+62\s+(?P<level>[A-Z_]+):\s*(?P<body>.+)$",
    re.IGNORECASE,
)
_WSP62_PATH_PATTERN = re.compile(
    r"(?P<path>(?:[^\s():/]+/)+[^\s():/]+\."
    r"(?:json|jsx|js|tsx|ts|yaml|yml|html|css|py|md))(?=$|[:\s(])",
    re.IGNORECASE,
)
_MAX_WSP62_FINDING_CHARS = 8192


@dataclass(frozen=True, slots=True)
class ParsedWSP62Finding:
    """Syntactic WSP 62 fields; authority is established by health triage."""

    level: str
    body: str
    file_path: Optional[str]
    module_path: str


def _module_from_path(file_path: Optional[str]) -> str:
    if not file_path:
        return ""
    parts = file_path.split("/")
    if len(parts) >= 3 and parts[0] == "modules":
        return "/".join(parts[:3])
    return ""


def parse_wsp62_finding_text(raw_finding: str) -> Optional[ParsedWSP62Finding]:
    """Parse one WSP 62 line without granting it provenance or authority."""
    if not isinstance(raw_finding, str) or not (
        0 < len(raw_finding) <= _MAX_WSP62_FINDING_CHARS
    ):
        return None
    match = _WSP62_PATTERN.match(raw_finding)
    if not match:
        return None
    body = match.group("body")
    path_match = _WSP62_PATH_PATTERN.search(body)
    file_path = path_match.group("path").replace("\\", "/") if path_match else None
    if file_path and not file_path.startswith("modules/"):
        file_path = f"modules/{file_path}"
    file_path = canonical_improvement_repo_path(file_path) if file_path else None
    if file_path and not file_path.startswith("modules/"):
        file_path = None
    return ParsedWSP62Finding(
        level=match.group("level").upper(),
        body=body,
        file_path=file_path,
        module_path=_module_from_path(file_path),
    )
