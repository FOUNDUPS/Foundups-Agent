"""Main-startup bootstrap for authority-runtime resolver artifact supply."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_resolver_artifact_supply import (
    AUTHORITY_RUNTIME_RESOLVER_SUPPLY_ACCEPT,
    run_reddog_authority_runtime_resolver_artifact_supply,
)


AUTHORITY_RUNTIME_RESOLVER_BOOTSTRAP_APPLIED = "AUTHORITY_RUNTIME_RESOLVER_BOOTSTRAP_APPLIED"
AUTHORITY_RUNTIME_RESOLVER_BOOTSTRAP_NOT_READY = "AUTHORITY_RUNTIME_RESOLVER_BOOTSTRAP_NOT_READY"


@dataclass(frozen=True)
class AuthorityRuntimeResolverBootstrapResult:
    accepted: bool
    status: str
    resolver_supply_receipt_id: Optional[str]
    principal_records_path: Optional[str]
    permission_snapshots_path: Optional[str]
    rejection_reasons: tuple[str, ...]
    no_signing_performed: bool = True
    no_signature_verification_performed: bool = True
    no_signer_state_mutation_performed: bool = True
    no_authority_runtime_invoked: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_work_state_mutation_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pattern_memory_write_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_authority_runtime_resolver_artifact_supply_bootstrap(
    *,
    repo_root: Path | str,
    principal_authority_record_path: Path | str | None,
    permission_snapshot_path: Path | str | None,
    principal_records_output_path: Path | str | None,
    permission_snapshots_output_path: Path | str | None,
) -> AuthorityRuntimeResolverBootstrapResult:
    """Materialize resolver stores from singular authority runtime files."""

    root = Path(repo_root).resolve()
    principal, principal_reasons = _read_json_outside_repo(
        root,
        principal_authority_record_path,
        missing_reason="missing_principal_authority_record_path",
        inside_reason="principal_authority_record_path_inside_repo",
        malformed_reason="malformed_principal_authority_record",
    )
    snapshot, snapshot_reasons = _read_json_outside_repo(
        root,
        permission_snapshot_path,
        missing_reason="missing_permission_snapshot_path",
        inside_reason="permission_snapshot_path_inside_repo",
        malformed_reason="malformed_permission_snapshot",
    )
    reasons = [*principal_reasons, *snapshot_reasons]
    if reasons:
        return _not_ready(reasons)

    assert principal is not None
    assert snapshot is not None
    supply = run_reddog_authority_runtime_resolver_artifact_supply(
        repo_root=root,
        principal_authority_record=principal,
        permission_snapshot=snapshot,
        principal_records_output_path=principal_records_output_path,
        permission_snapshots_output_path=permission_snapshots_output_path,
    )
    if not supply.accepted or supply.status != AUTHORITY_RUNTIME_RESOLVER_SUPPLY_ACCEPT:
        return _not_ready(supply.rejection_reasons or ("authority_runtime_resolver_supply_rejected",))
    return AuthorityRuntimeResolverBootstrapResult(
        accepted=True,
        status=AUTHORITY_RUNTIME_RESOLVER_BOOTSTRAP_APPLIED,
        resolver_supply_receipt_id=supply.resolver_supply_receipt_id,
        principal_records_path=supply.principal_records_path,
        permission_snapshots_path=supply.permission_snapshots_path,
        rejection_reasons=(),
    )


def _read_json_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
    malformed_reason: str,
) -> tuple[Mapping[str, Any] | None, tuple[str, ...]]:
    if not value:
        return None, (missing_reason,)
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    resolved = path.resolve()
    if _is_inside(resolved, repo_root):
        return None, (inside_reason,)
    if not resolved.exists() or not resolved.is_file():
        return None, (missing_reason,)
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except Exception:
        return None, (malformed_reason,)
    if not isinstance(payload, Mapping):
        return None, (malformed_reason,)
    return payload, ()


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _not_ready(reasons: tuple[str, ...] | list[str]) -> AuthorityRuntimeResolverBootstrapResult:
    return AuthorityRuntimeResolverBootstrapResult(
        accepted=False,
        status=AUTHORITY_RUNTIME_RESOLVER_BOOTSTRAP_NOT_READY,
        resolver_supply_receipt_id=None,
        principal_records_path=None,
        permission_snapshots_path=None,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason))),
    )


__all__ = [
    "AUTHORITY_RUNTIME_RESOLVER_BOOTSTRAP_APPLIED",
    "AUTHORITY_RUNTIME_RESOLVER_BOOTSTRAP_NOT_READY",
    "AuthorityRuntimeResolverBootstrapResult",
    "run_reddog_authority_runtime_resolver_artifact_supply_bootstrap",
]
