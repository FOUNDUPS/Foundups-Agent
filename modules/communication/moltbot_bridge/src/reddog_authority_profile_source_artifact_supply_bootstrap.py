"""Main-startup bootstrap for RedDog authority-profile source supply.

Slice: REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1

This adapter reads outside-repo authority seed, token-verified principal, and
permission snapshot JSON inputs, then materializes the authority-profile source
artifact consumed by the architect FIX promotion bridge.

It does not sign, verify signatures, mutate signer state, mutate work state,
spawn workers, create worktrees, execute shell commands, enqueue OpenClaw,
dispatch Hermes, create PRs, settle rewards, write PatternMemory, or re-index
HoloIndex.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_authority_profile_source_artifact_supply import (
    AUTHORITY_PROFILE_SOURCE_SUPPLY_ACCEPT,
    run_reddog_authority_profile_source_artifact_supply,
)


AUTHORITY_PROFILE_SOURCE_BOOTSTRAP_APPLIED = "AUTHORITY_PROFILE_SOURCE_BOOTSTRAP_APPLIED"
AUTHORITY_PROFILE_SOURCE_BOOTSTRAP_NOT_READY = "AUTHORITY_PROFILE_SOURCE_BOOTSTRAP_NOT_READY"


@dataclass(frozen=True)
class AuthorityProfileSourceBootstrapResult:
    accepted: bool
    status: str
    authority_profile_source_receipt_id: Optional[str]
    output_path: Optional[str]
    rejection_reasons: tuple[str, ...]
    no_signing_performed: bool = True
    no_signature_verification_performed: bool = True
    no_signer_state_mutation_performed: bool = True
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


def run_reddog_authority_profile_source_artifact_supply_bootstrap(
    *,
    repo_root: Path | str,
    authority_seed_path: Path | str | None,
    principal_authority_record_path: Path | str | None,
    permission_snapshot_path: Path | str | None,
    output_path: Path | str | None,
    now_epoch: int | None = None,
    leeway_s: int = 60,
) -> AuthorityProfileSourceBootstrapResult:
    """Materialize the authority-profile source artifact from runtime files."""

    root = Path(repo_root).resolve()
    seed, seed_reasons = _read_json_outside_repo(
        root,
        authority_seed_path,
        missing_reason="missing_authority_profile_seed_path",
        inside_reason="authority_profile_seed_path_inside_repo",
        malformed_reason="malformed_authority_profile_seed",
    )
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
    reasons = [*seed_reasons, *principal_reasons, *snapshot_reasons]
    if reasons:
        return _not_ready(reasons)

    assert seed is not None
    assert principal is not None
    assert snapshot is not None
    supply = run_reddog_authority_profile_source_artifact_supply(
        repo_root=root,
        authority_seed=seed,
        principal_authority_record=principal,
        permission_snapshot=snapshot,
        output_path=output_path,
        now_epoch=int(now_epoch if now_epoch is not None else time.time()),
        leeway_s=leeway_s,
    )
    if not supply.accepted or supply.status != AUTHORITY_PROFILE_SOURCE_SUPPLY_ACCEPT:
        return _not_ready(supply.rejection_reasons or ("authority_profile_source_supply_rejected",))
    return AuthorityProfileSourceBootstrapResult(
        accepted=True,
        status=AUTHORITY_PROFILE_SOURCE_BOOTSTRAP_APPLIED,
        authority_profile_source_receipt_id=supply.authority_profile_source_receipt_id,
        output_path=supply.output_path,
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


def _not_ready(reasons: tuple[str, ...] | list[str]) -> AuthorityProfileSourceBootstrapResult:
    return AuthorityProfileSourceBootstrapResult(
        accepted=False,
        status=AUTHORITY_PROFILE_SOURCE_BOOTSTRAP_NOT_READY,
        authority_profile_source_receipt_id=None,
        output_path=None,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason))),
    )


__all__ = [
    "AUTHORITY_PROFILE_SOURCE_BOOTSTRAP_APPLIED",
    "AUTHORITY_PROFILE_SOURCE_BOOTSTRAP_NOT_READY",
    "AuthorityProfileSourceBootstrapResult",
    "run_reddog_authority_profile_source_artifact_supply_bootstrap",
]
