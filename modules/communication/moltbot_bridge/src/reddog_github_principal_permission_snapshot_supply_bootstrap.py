"""Main bootstrap for GitHub principal/permission snapshot supply."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from modules.communication.moltbot_bridge.src.reddog_github_principal_permission_snapshot_supply import (
    GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_ACCEPT,
    run_reddog_github_principal_permission_snapshot_supply,
)
from modules.platform_integration.github_integration.src.reddog_github_permission_probe import (
    PermissionProbeBackend,
)


GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_BOOTSTRAP_APPLIED = (
    "GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_BOOTSTRAP_APPLIED"
)
GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_BOOTSTRAP_NOT_READY = (
    "GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_BOOTSTRAP_NOT_READY"
)


@dataclass(frozen=True)
class GitHubPrincipalPermissionSnapshotBootstrapResult:
    accepted: bool
    status: str
    receipt_id: Optional[str]
    principal_authority_record_path: Optional[str]
    permission_snapshot_path: Optional[str]
    principal_id: Optional[str]
    permission_snapshot_digest: Optional[str]
    rejection_reasons: tuple[str, ...]
    no_signing_performed: bool = True
    no_signature_verification_performed: bool = True
    no_signer_state_mutation_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed_by_bootstrap: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pattern_memory_write_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_github_principal_permission_snapshot_supply_bootstrap(
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
    now_iso: str | None = None,
    ttl_seconds: int = 300,
    probe_backend: PermissionProbeBackend | None = None,
) -> GitHubPrincipalPermissionSnapshotBootstrapResult:
    """Materialize principal authority and permission snapshot runtime files."""

    result = run_reddog_github_principal_permission_snapshot_supply(
        repo_root=repo_root,
        repo_full_name=repo_full_name,
        foundup_id=foundup_id,
        principal_public_key=principal_public_key,
        principal_authority_record_output_path=principal_authority_record_output_path,
        permission_snapshot_output_path=permission_snapshot_output_path,
        principal_provider=principal_provider,
        reward_account=reward_account,
        owner_dae=owner_dae,
        principal_wallet=principal_wallet,
        now=_parse_now(now_iso),
        ttl_seconds=ttl_seconds,
        probe_backend=probe_backend,
    )
    if not result.accepted or result.status != GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_ACCEPT:
        return _not_ready(result.rejection_reasons)
    return GitHubPrincipalPermissionSnapshotBootstrapResult(
        accepted=True,
        status=GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_BOOTSTRAP_APPLIED,
        receipt_id=result.receipt_id,
        principal_authority_record_path=result.principal_authority_record_path,
        permission_snapshot_path=result.permission_snapshot_path,
        principal_id=result.principal_id,
        permission_snapshot_digest=result.permission_snapshot_digest,
        rejection_reasons=(),
    )


def _parse_now(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _not_ready(reasons: tuple[str, ...] | list[str]) -> GitHubPrincipalPermissionSnapshotBootstrapResult:
    return GitHubPrincipalPermissionSnapshotBootstrapResult(
        accepted=False,
        status=GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_BOOTSTRAP_NOT_READY,
        receipt_id=None,
        principal_authority_record_path=None,
        permission_snapshot_path=None,
        principal_id=None,
        permission_snapshot_digest=None,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason))),
    )


__all__ = [
    "GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_BOOTSTRAP_APPLIED",
    "GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_BOOTSTRAP_NOT_READY",
    "GitHubPrincipalPermissionSnapshotBootstrapResult",
    "run_reddog_github_principal_permission_snapshot_supply_bootstrap",
]
