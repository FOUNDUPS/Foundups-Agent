"""Read-only GitHub permission probe for RedDog governed work orders.

Slice: REDDOG_GITHUB_PERMISSION_PROBE_PHASE1
Contract: docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md

Reports current repository permission for an authenticated principal.
Does NOT create branches, PRs, commits, merges, or mutate repository content.

Allowed read-only `gh` invocations (when default backend is used):
- `gh auth status`
- `gh api user` (GET)
- `gh repo view <repo> --json viewerPermission,defaultBranchRef,nameWithOwner`
- `gh api repos/{owner}/{repo}/branches/{branch}/protection` (GET, optional)
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Tuple

logger = logging.getLogger(__name__)

PERMISSION_LEVELS = frozenset({"admin", "maintain", "write", "triage", "read", "none", "unknown"})
READ_ONLY_GH_COMMANDS = frozenset(
    {
        "auth status",
        "api user",
        "repo view",
        "api repos/",
    }
)

_SECRET_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9_]+"),
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"gho_[A-Za-z0-9_]+"),
    re.compile(r"ghu_[A-Za-z0-9_]+"),
)


@dataclass
class RepoPermissionProbeSnapshot:
    repo_full_name: str
    principal_login: str
    principal_provider: str
    permission: str
    can_read: bool
    can_write: bool
    can_admin: bool
    source: str
    checked_at: str
    expires_at: Optional[str]
    token_scopes: List[str] = field(default_factory=list)
    branch_protection_observed: str = "unknown"
    default_branch: str = "unknown"
    evidence_digest: str = ""
    raw_secret_included: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_repo_permission_snapshot(self) -> Dict[str, str]:
        """Map into #889 RedDogGovernedWorkOrder.repo_permission_snapshot shape."""
        return {
            "permission_level": self.permission,
            "captured_at": self.checked_at,
            "source": self.source,
            "digest": self.evidence_digest,
        }


class PermissionProbeBackend(Protocol):
    def probe(self, repo_full_name: str) -> Mapping[str, Any]:
        """Return backend fields: authenticated, login, permission, default_branch, scopes, branch_protection."""


def _utc_now(now: Optional[datetime] = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc)


def _iso8601(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def _sanitize_text(text: str) -> str:
    cleaned = text
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    return cleaned


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def permission_to_capabilities(permission: str) -> Tuple[bool, bool, bool]:
    """Conservative capability mapping for probe snapshots."""
    level = (permission or "unknown").strip().lower()
    if level in {"admin", "maintain", "write"}:
        return True, True, level == "admin"
    if level in {"triage", "read"}:
        return True, False, False
    return False, False, False


def normalize_permission(raw: Optional[str]) -> str:
    if not raw:
        return "unknown"
    level = raw.strip().lower()
    if level in PERMISSION_LEVELS:
        return level
    return "unknown"


def is_snapshot_fresh(snapshot: RepoPermissionProbeSnapshot, *, now: Optional[datetime] = None) -> bool:
    if not snapshot.expires_at:
        return True
    try:
        expires = datetime.fromisoformat(snapshot.expires_at.replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return _utc_now(now) <= expires.astimezone(timezone.utc)
    except ValueError:
        return False


def _run_gh_readonly(args: List[str], *, timeout: int = 20) -> Tuple[int, str, str]:
    cmd = ["gh", *args]
    cmd_text = " ".join(cmd)
    if not any(marker in cmd_text for marker in READ_ONLY_GH_COMMANDS):
        raise ValueError(f"gh command not allowlisted for read-only probe: {cmd_text}")
    if any(token in cmd_text for token in ("--show-token", "auth login", "auth refresh")):
        raise ValueError(f"gh command blocked for secret safety: {cmd_text}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    stdout = _sanitize_text(result.stdout or "")
    stderr = _sanitize_text(result.stderr or "")
    return result.returncode, stdout, stderr


class GhCliPermissionProbeBackend:
    """Read-only GitHub permission probe via gh CLI."""

    def probe(self, repo_full_name: str) -> Mapping[str, Any]:
        auth_code, auth_out, auth_err = _run_gh_readonly(["auth", "status"])
        authenticated = auth_code == 0 and "Logged in" in auth_out
        scopes: List[str] = []
        for line in (auth_out + "\n" + auth_err).splitlines():
            if "Token scopes:" in line or "token scopes:" in line.lower():
                _, _, tail = line.partition(":")
                scopes = [s.strip("'\" ") for s in tail.split(",") if s.strip()]

        login = "unknown"
        permission = "unknown"
        default_branch = "unknown"
        branch_protection: str = "unknown"

        if authenticated:
            user_code, user_out, _ = _run_gh_readonly(["api", "user"])
            if user_code == 0 and user_out.strip():
                try:
                    login = str(json.loads(user_out).get("login") or "unknown")
                except json.JSONDecodeError:
                    login = "unknown"

            repo_code, repo_out, _ = _run_gh_readonly(
                [
                    "repo",
                    "view",
                    repo_full_name,
                    "--json",
                    "viewerPermission,defaultBranchRef,nameWithOwner",
                ]
            )
            if repo_code == 0 and repo_out.strip():
                try:
                    payload = json.loads(repo_out)
                    permission = normalize_permission(payload.get("viewerPermission"))
                    ref = payload.get("defaultBranchRef") or {}
                    default_branch = str(ref.get("name") or "unknown")
                except json.JSONDecodeError:
                    permission = "unknown"
            else:
                permission = "none" if repo_code != 0 else "unknown"

            if default_branch not in {"unknown", ""}:
                owner, _, repo = repo_full_name.partition("/")
                if owner and repo:
                    prot_code, _, _ = _run_gh_readonly(
                        ["api", f"repos/{owner}/{repo}/branches/{default_branch}/protection"]
                    )
                    if prot_code == 0:
                        branch_protection = "true"
                    elif prot_code == 404:
                        branch_protection = "false"
                    else:
                        branch_protection = "unknown"

        return {
            "authenticated": authenticated,
            "login": login,
            "permission": permission,
            "default_branch": default_branch,
            "scopes": scopes,
            "branch_protection_observed": branch_protection,
            "source": "gh_cli",
        }


def probe_repo_permission(
    repo_full_name: str,
    *,
    principal_login: Optional[str] = None,
    principal_provider: str = "github",
    backend: Optional[PermissionProbeBackend] = None,
    now: Optional[datetime] = None,
    ttl_seconds: int = 300,
) -> RepoPermissionProbeSnapshot:
    """Probe read-only GitHub repository permission for the current authenticated principal."""
    checked = _utc_now(now)
    expires = checked + timedelta(seconds=max(1, ttl_seconds))

    try:
        raw = backend.probe(repo_full_name) if backend is not None else GhCliPermissionProbeBackend().probe(repo_full_name)
    except Exception as exc:
        logger.debug("permission probe failed closed: %s", _sanitize_text(str(exc)))
        raw = {
            "authenticated": False,
            "login": "unknown",
            "permission": "unknown",
            "default_branch": "unknown",
            "scopes": [],
            "branch_protection_observed": "unknown",
            "source": "gh_cli",
        }

    permission = normalize_permission(str(raw.get("permission", "unknown")))
    if not raw.get("authenticated"):
        permission = "unknown"

    can_read, can_write, can_admin = permission_to_capabilities(permission)
    login = principal_login or str(raw.get("login") or "unknown")

    snapshot_core = {
        "repo_full_name": repo_full_name,
        "principal_login": login,
        "principal_provider": principal_provider,
        "permission": permission,
        "can_read": can_read,
        "can_write": can_write,
        "can_admin": can_admin,
        "source": str(raw.get("source") or "unknown"),
        "checked_at": _iso8601(checked),
        "expires_at": _iso8601(expires),
        "token_scopes": list(raw.get("scopes") or []),
        "branch_protection_observed": str(raw.get("branch_protection_observed") or "unknown"),
        "default_branch": str(raw.get("default_branch") or "unknown"),
        "raw_secret_included": False,
    }
    digest = _canonical_digest(snapshot_core)

    return RepoPermissionProbeSnapshot(
        evidence_digest=f"sha256:{digest}",
        **snapshot_core,
    )


def build_probe_backend_from_callable(
    fn: Callable[[str], Mapping[str, Any]]
) -> PermissionProbeBackend:
    class _CallableBackend:
        def probe(self, repo_full_name: str) -> Mapping[str, Any]:
            return fn(repo_full_name)

    return _CallableBackend()
