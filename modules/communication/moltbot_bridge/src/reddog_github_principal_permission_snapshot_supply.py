"""GitHub principal and permission snapshot supplier for RedDog authority.

Slice: REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_PHASE1

This module bridges the existing read-only GitHub permission probe into the
authority-profile source supplier. It materializes two outside-repo inputs:

* PrincipalAuthorityRecord JSON
* PermissionSnapshot JSON

It does not infer private authority. The GitHub probe verifies the principal
login and repository permission; the caller must provide the principal public
key explicitly. This module does not sign, verify signatures, mutate signer
state, execute shell commands directly, enqueue OpenClaw, dispatch Hermes,
create worktrees, write repository files, or re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Tuple

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    PrincipalAuthorityRecord,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PermissionSnapshot,
)
from modules.platform_integration.github_integration.src.reddog_github_permission_probe import (
    PermissionProbeBackend,
    RepoPermissionProbeSnapshot,
    is_snapshot_fresh,
    probe_repo_permission,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)


GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_ACCEPT = (
    "GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_ACCEPT"
)
GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_REJECT = (
    "GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_REJECT"
)
PRINCIPAL_AUTHORITY_RECORD_SCHEMA_VERSION = "reddog_principal_authority_record.v1"
PERMISSION_SNAPSHOT_SUPPLY_SCHEMA_VERSION = "reddog_permission_snapshot_supply.v1"

_FOUNDUP_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")


class GitHubPrincipalPermissionSnapshotSupplyReason:
    MISSING_REPO_FULL_NAME = "missing_repo_full_name"
    MISSING_FOUNDUP_ID = "missing_foundup_id"
    INVALID_FOUNDUP_ID = "invalid_foundup_id"
    MISSING_PRINCIPAL_PUBLIC_KEY = "missing_principal_public_key"
    NON_ASCII_INPUT = "non_ascii_input"
    PROBE_NOT_AUTHENTICATED = "github_probe_not_authenticated"
    PROBE_STALE = "github_probe_stale"
    PROBE_SECRET_INCLUDED = "github_probe_secret_included"
    PERMISSION_NOT_WRITE_CAPABLE = "github_permission_not_write_capable"
    OUTPUT_PATH_INVALID = "output_path_invalid"
    OUTPUT_WRITE_FAILED = "output_write_failed"


@dataclass(frozen=True)
class GitHubPrincipalPermissionSnapshotSupplyResult:
    accepted: bool
    status: str
    receipt_id: Optional[str]
    principal_authority_record_path: Optional[str]
    permission_snapshot_path: Optional[str]
    principal_id: Optional[str]
    repo_full_name: Optional[str]
    foundup_id: Optional[str]
    permission_snapshot_digest: Optional[str]
    rejection_reasons: Tuple[str, ...]
    no_signing_performed: bool = True
    no_signature_verification_performed: bool = True
    no_signer_state_mutation_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed_by_supplier: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pattern_memory_write_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_github_principal_permission_snapshot_supply(
    *,
    repo_root: Path | str,
    repo_full_name: str,
    foundup_id: str,
    principal_public_key: str,
    principal_authority_record_output_path: Path | str | None,
    permission_snapshot_output_path: Path | str | None,
    principal_provider: str = "github",
    reward_account: str | None = None,
    owner_dae: str | None = None,
    principal_wallet: str | None = None,
    now: datetime | None = None,
    ttl_seconds: int = 300,
    probe_backend: PermissionProbeBackend | None = None,
) -> GitHubPrincipalPermissionSnapshotSupplyResult:
    """Materialize principal and permission inputs from a GitHub probe."""

    root = Path(repo_root).resolve()
    repo = str(repo_full_name or "").strip()
    fid = str(foundup_id or "").strip()
    public_key = str(principal_public_key or "").strip()
    provider = str(principal_provider or "github").strip()
    reasons: list[str] = []

    if not repo:
        reasons.append(GitHubPrincipalPermissionSnapshotSupplyReason.MISSING_REPO_FULL_NAME)
    if not fid:
        reasons.append(GitHubPrincipalPermissionSnapshotSupplyReason.MISSING_FOUNDUP_ID)
    elif not _valid_foundup_id(fid):
        reasons.append(GitHubPrincipalPermissionSnapshotSupplyReason.INVALID_FOUNDUP_ID)
    if not public_key:
        reasons.append(GitHubPrincipalPermissionSnapshotSupplyReason.MISSING_PRINCIPAL_PUBLIC_KEY)
    if not _ascii_deep(
        {
            "repo_full_name": repo,
            "foundup_id": fid,
            "principal_public_key": public_key,
            "principal_provider": provider,
            "reward_account": reward_account or "",
            "owner_dae": owner_dae or "",
            "principal_wallet": principal_wallet or "",
        }
    ):
        reasons.append(GitHubPrincipalPermissionSnapshotSupplyReason.NON_ASCII_INPUT)

    principal_path, principal_path_reasons = _runtime_output_path(
        principal_authority_record_output_path,
        root,
    )
    permission_path, permission_path_reasons = _runtime_output_path(
        permission_snapshot_output_path,
        root,
    )
    reasons.extend(principal_path_reasons)
    reasons.extend(permission_path_reasons)
    if reasons:
        return _reject(reasons, repo_full_name=repo, foundup_id=fid)

    assert principal_path is not None
    assert permission_path is not None
    checked = _utc_now(now)
    snapshot = probe_repo_permission(
        repo,
        principal_provider=provider,
        backend=probe_backend,
        now=checked,
        ttl_seconds=ttl_seconds,
    )
    reasons.extend(_probe_reasons(snapshot, now=checked))
    if reasons:
        return _reject(
            reasons,
            repo_full_name=repo,
            foundup_id=fid,
            principal_id=_principal_id(snapshot),
            permission_snapshot_digest=snapshot.evidence_digest,
        )

    principal = _principal_record(
        snapshot,
        foundup_id=fid,
        principal_public_key=public_key,
        reward_account=reward_account,
        owner_dae=owner_dae,
        principal_wallet=principal_wallet,
    )
    permission = _permission_snapshot(snapshot)
    principal_payload = _principal_payload(principal, snapshot)
    permission_payload = _permission_payload(permission, snapshot)
    receipt = _digest(
        {
            "principal": principal_payload,
            "permission": permission_payload,
            "principal_path": str(principal_path),
            "permission_path": str(permission_path),
        }
    )

    try:
        _write_json_atomic(principal_path, principal_payload)
        _write_json_atomic(permission_path, permission_payload)
    except Exception:
        return _reject(
            (GitHubPrincipalPermissionSnapshotSupplyReason.OUTPUT_WRITE_FAILED,),
            repo_full_name=repo,
            foundup_id=fid,
            principal_id=principal.principal_id,
            permission_snapshot_digest=permission.evidence_digest,
        )

    return GitHubPrincipalPermissionSnapshotSupplyResult(
        accepted=True,
        status=GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_ACCEPT,
        receipt_id=receipt,
        principal_authority_record_path=str(principal_path),
        permission_snapshot_path=str(permission_path),
        principal_id=principal.principal_id,
        repo_full_name=repo,
        foundup_id=fid,
        permission_snapshot_digest=permission.evidence_digest,
        rejection_reasons=(),
    )


def _probe_reasons(snapshot: RepoPermissionProbeSnapshot, *, now: datetime) -> list[str]:
    reasons: list[str] = []
    if snapshot.principal_login in {"", "unknown"} or snapshot.permission == "unknown":
        reasons.append(GitHubPrincipalPermissionSnapshotSupplyReason.PROBE_NOT_AUTHENTICATED)
    if not is_snapshot_fresh(snapshot, now=now):
        reasons.append(GitHubPrincipalPermissionSnapshotSupplyReason.PROBE_STALE)
    if snapshot.raw_secret_included:
        reasons.append(GitHubPrincipalPermissionSnapshotSupplyReason.PROBE_SECRET_INCLUDED)
    if not (snapshot.can_write or snapshot.can_admin):
        reasons.append(GitHubPrincipalPermissionSnapshotSupplyReason.PERMISSION_NOT_WRITE_CAPABLE)
    return reasons


def _principal_record(
    snapshot: RepoPermissionProbeSnapshot,
    *,
    foundup_id: str,
    principal_public_key: str,
    reward_account: str | None,
    owner_dae: str | None,
    principal_wallet: str | None,
) -> PrincipalAuthorityRecord:
    principal_id = _principal_id(snapshot)
    return PrincipalAuthorityRecord(
        principal_id=principal_id,
        principal_provider=snapshot.principal_provider,
        principal_public_key=principal_public_key,
        repo_scope=(snapshot.repo_full_name,),
        foundup_scope=(foundup_id,),
        verified_subject_digest=_digest(
            {
                "principal_id": principal_id,
                "principal_provider": snapshot.principal_provider,
                "repo_full_name": snapshot.repo_full_name,
                "github_permission_evidence_digest": snapshot.evidence_digest,
                "checked_at": snapshot.checked_at,
                "source": snapshot.source,
            }
        ),
        reward_account=reward_account or None,
        owner_dae=owner_dae or None,
        principal_wallet=principal_wallet or None,
    )


def _permission_snapshot(snapshot: RepoPermissionProbeSnapshot) -> PermissionSnapshot:
    return PermissionSnapshot(
        evidence_digest=snapshot.evidence_digest,
        expires_at=_epoch_from_iso(snapshot.expires_at),
        can_write=snapshot.can_write,
        can_admin=snapshot.can_admin,
        repo_full_name=snapshot.repo_full_name,
    )


def _principal_payload(
    principal: PrincipalAuthorityRecord,
    snapshot: RepoPermissionProbeSnapshot,
) -> dict[str, Any]:
    payload = principal.to_dict()
    payload["schema_version"] = PRINCIPAL_AUTHORITY_RECORD_SCHEMA_VERSION
    payload["github_permission_probe_digest"] = snapshot.evidence_digest
    payload["github_permission_checked_at"] = snapshot.checked_at
    payload["github_permission_expires_at"] = snapshot.expires_at
    payload["github_permission_level"] = snapshot.permission
    payload["github_permission_source"] = snapshot.source
    return payload


def _permission_payload(
    permission: PermissionSnapshot,
    snapshot: RepoPermissionProbeSnapshot,
) -> dict[str, Any]:
    payload = asdict(permission)
    payload["schema_version"] = PERMISSION_SNAPSHOT_SUPPLY_SCHEMA_VERSION
    payload["principal_id"] = _principal_id(snapshot)
    payload["principal_provider"] = snapshot.principal_provider
    payload["permission"] = snapshot.permission
    payload["checked_at"] = snapshot.checked_at
    payload["source"] = snapshot.source
    payload["default_branch"] = snapshot.default_branch
    payload["branch_protection_observed"] = snapshot.branch_protection_observed
    payload["raw_secret_included"] = snapshot.raw_secret_included
    return payload


def _principal_id(snapshot: RepoPermissionProbeSnapshot) -> str:
    return f"{snapshot.principal_provider}:{snapshot.principal_login}"


def _valid_foundup_id(value: str) -> bool:
    if value in {"*", "all", "repo", "root"}:
        return False
    if "/" in value or "\\" in value or ":" in value or ".." in value:
        return False
    return bool(_FOUNDUP_ID_RE.fullmatch(value))


def _runtime_output_path(value: Path | str | None, repo_root: Path) -> tuple[Path | None, list[str]]:
    if not value:
        return None, [GitHubPrincipalPermissionSnapshotSupplyReason.OUTPUT_PATH_INVALID]
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    resolved = path.resolve()
    if _is_inside(resolved, repo_root):
        return None, [GitHubPrincipalPermissionSnapshotSupplyReason.OUTPUT_PATH_INVALID]
    if resolved == repo_root or repo_root in resolved.parents:
        return None, [GitHubPrincipalPermissionSnapshotSupplyReason.OUTPUT_PATH_INVALID]
    return resolved, []


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    with runtime_operation_lock(str(path) + ".operation"):
        _write_json_atomic_unlocked(path, payload)


def _write_json_atomic_unlocked(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(path.parent),
        delete=False,
        newline="\n",
    ) as handle:
        json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def _epoch_from_iso(value: str | None) -> int:
    if not value:
        return 0
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.astimezone(timezone.utc).timestamp())


def _utc_now(now: datetime | None = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc)


def _digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _ascii_deep(value: Any) -> bool:
    if isinstance(value, str):
        return all(ord(char) < 128 for char in value)
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and _ascii_deep(key) and _ascii_deep(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_ascii_deep(item) for item in value)
    return True


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _reject(
    reasons: Tuple[str, ...] | list[str],
    *,
    repo_full_name: str | None = None,
    foundup_id: str | None = None,
    principal_id: str | None = None,
    permission_snapshot_digest: str | None = None,
) -> GitHubPrincipalPermissionSnapshotSupplyResult:
    return GitHubPrincipalPermissionSnapshotSupplyResult(
        accepted=False,
        status=GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_REJECT,
        receipt_id=None,
        principal_authority_record_path=None,
        permission_snapshot_path=None,
        principal_id=principal_id,
        repo_full_name=repo_full_name,
        foundup_id=foundup_id,
        permission_snapshot_digest=permission_snapshot_digest,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason))),
    )


__all__ = [
    "GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_ACCEPT",
    "GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_REJECT",
    "GitHubPrincipalPermissionSnapshotSupplyReason",
    "GitHubPrincipalPermissionSnapshotSupplyResult",
    "run_reddog_github_principal_permission_snapshot_supply",
]
