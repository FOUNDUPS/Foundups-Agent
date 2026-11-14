"""Typed records for the exact-SHA HoloIndex authority transaction."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


GitRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class RedDogHoloIndexAuthorityTransactionResult:
    """Secret-free exact-SHA authority transaction result."""

    ready: bool
    status: str
    target_repo_head_sha: str = ""
    observed_origin_main_sha: str = ""
    generation_id: str = ""
    freshness_receipt_digest: str = ""
    refreshed: bool = False
    error: str = ""


@dataclass(frozen=True)
class AuthorityContext:
    workspace: Path
    root: Path
    target_sha: str
    expected_digest: str
    ssd_path: Path
    environ: Mapping[str, str]


@dataclass(frozen=True)
class AuthorityDependencies:
    git_runner: GitRunner
    ensure_current: Callable[..., Any]
    activate_replica: Callable[..., Any]
    cleanup_owner: Callable[[], None]
    lease_factory: Callable[[Path | str], Any]


@dataclass(frozen=True)
class PreparedAuthority:
    observed_sha: str
    operational: Any


__all__ = [
    "AuthorityContext",
    "AuthorityDependencies",
    "GitRunner",
    "PreparedAuthority",
    "RedDogHoloIndexAuthorityTransactionResult",
]
