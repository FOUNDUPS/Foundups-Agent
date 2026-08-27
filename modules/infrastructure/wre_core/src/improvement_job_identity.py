"""Identity and path primitives shared by WRE improvement-job contracts.

These helpers are deliberately independent of the ImprovementJob enums and
dataclasses so parsers can validate repository paths without importing the
full orchestration contract or creating a circular dependency.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Optional


_WINDOWS_RESERVED_BASENAMES = frozenset(
    {"con", "prn", "aux", "nul", "clock$"}
    | {f"com{index}" for index in range(1, 10)}
    | {f"lpt{index}" for index in range(1, 10)}
)


def _is_windows_aliased_segment(segment: str) -> bool:
    """Reject names Windows can alias to a different filesystem object."""
    if segment.endswith((".", " ")) or ":" in segment:
        return True
    basename = segment.split(".", 1)[0].casefold()
    return basename in _WINDOWS_RESERVED_BASENAMES


def canonical_improvement_repo_path(
    value: str,
    *,
    allow_glob: bool = False,
) -> Optional[str]:
    """Return one canonical repository-relative path or ``None``."""
    if not isinstance(value, str) or not value or "\x00" in value:
        return None
    normalized = value.replace("\\", "/")
    if normalized.startswith(("/", "//")) or re.match(r"^[A-Za-z]:", normalized):
        return None
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return None
    if any(_is_windows_aliased_segment(part) for part in parts):
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in normalized):
        return None
    if not allow_glob and any(char in normalized for char in "*?[]"):
        return None
    return "/".join(parts)


def generate_idempotent_improvement_job_id(
    improvement_type: Any,
    idempotency_key: str,
) -> str:
    """Return a stable job ID for one immutable finding/audit binding."""
    if not idempotency_key or not idempotency_key.strip():
        raise ValueError("idempotency_key is required")
    type_value = getattr(improvement_type, "value", improvement_type)
    if not isinstance(type_value, str) or not type_value:
        raise ValueError("improvement_type must provide a non-empty string value")
    material = f"{type_value}:{idempotency_key}".encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()[:20]
    type_slug = type_value.replace("_", "")[:12]
    return f"imp_{type_slug}_{digest}"
