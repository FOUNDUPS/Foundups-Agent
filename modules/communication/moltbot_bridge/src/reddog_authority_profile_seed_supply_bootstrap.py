"""Main-startup bootstrap for RedDog authority-profile seed supply.

Slice: REDDOG_AUTHORITY_PROFILE_SEED_SUPPLY_MAIN_PREFLIGHT_PHASE1

This adapter reads resident runtime receipts from outside-repo JSON files and
materializes the authority-profile seed consumed by the existing
authority-profile source supplier.

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
from typing import Any, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_authority_profile_seed_supply import (
    AUTHORITY_PROFILE_SEED_SUPPLY_ACCEPT,
    run_reddog_authority_profile_seed_supply,
)


AUTHORITY_PROFILE_SEED_BOOTSTRAP_APPLIED = "AUTHORITY_PROFILE_SEED_BOOTSTRAP_APPLIED"
AUTHORITY_PROFILE_SEED_BOOTSTRAP_NOT_READY = "AUTHORITY_PROFILE_SEED_BOOTSTRAP_NOT_READY"


@dataclass(frozen=True)
class AuthorityProfileSeedBootstrapResult:
    accepted: bool
    status: str
    seed_supply_receipt_id: Optional[str]
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


def run_reddog_authority_profile_seed_supply_bootstrap(
    *,
    repo_root: Path | str,
    architect_determination_path: Path | str | None,
    model_selection_receipt_path: Path | str | None,
    memex_supply_receipt_path: Path | str | None,
    principal_authority_record_path: Path | str | None,
    permission_snapshot_path: Path | str | None,
    output_path: Path | str | None,
    reddog_id: str,
    reddog_public_key: str,
    now_epoch: int | None = None,
    foundup_id: str | None = None,
    requested_operation: str = "feature_slice",
    allowed_paths: Sequence[str] = (),
    denied_paths: Sequence[str] = (),
    valve_state_required: str = "",
    key_epoch: str = "epoch-1",
    required_tests: Sequence[str] = (),
    required_policy_gates: Sequence[str] = (),
    consensus_receipt_digest: str | None = None,
    sovereign_authorization_digest: str | None = None,
    identity_ttl_seconds: int = 3600,
    work_authority_ttl_seconds: int = 900,
) -> AuthorityProfileSeedBootstrapResult:
    """Materialize the authority-profile seed from resident runtime files."""

    root = Path(repo_root).resolve()
    determination, determination_reasons = _read_json_outside_repo(
        root,
        architect_determination_path,
        missing_reason="missing_architect_determination_path",
        inside_reason="architect_determination_path_inside_repo",
        malformed_reason="malformed_architect_determination",
    )
    model_selection, model_reasons = _read_json_outside_repo(
        root,
        model_selection_receipt_path,
        missing_reason="missing_model_selection_receipt_path",
        inside_reason="model_selection_receipt_path_inside_repo",
        malformed_reason="malformed_model_selection_receipt",
    )
    memex_supply, memex_reasons = _read_json_outside_repo(
        root,
        memex_supply_receipt_path,
        missing_reason="missing_memex_supply_receipt_path",
        inside_reason="memex_supply_receipt_path_inside_repo",
        malformed_reason="malformed_memex_supply_receipt",
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
    reasons = [
        *determination_reasons,
        *model_reasons,
        *memex_reasons,
        *principal_reasons,
        *snapshot_reasons,
    ]
    if reasons:
        return _not_ready(reasons)

    assert determination is not None
    assert model_selection is not None
    assert memex_supply is not None
    assert principal is not None
    assert snapshot is not None
    supply = run_reddog_authority_profile_seed_supply(
        repo_root=root,
        architect_determination=determination,
        model_selection_receipt=model_selection,
        memex_supply_receipt=memex_supply,
        principal_authority_record=principal,
        permission_snapshot=snapshot,
        output_path=output_path,
        reddog_id=reddog_id,
        reddog_public_key=reddog_public_key,
        now_epoch=int(now_epoch if now_epoch is not None else time.time()),
        foundup_id=foundup_id,
        requested_operation=requested_operation,
        allowed_paths=allowed_paths,
        denied_paths=denied_paths,
        valve_state_required=valve_state_required or "VALVE_OPEN_WORKTREE_CREATE",
        key_epoch=key_epoch,
        required_tests=required_tests,
        required_policy_gates=required_policy_gates,
        consensus_receipt_digest=consensus_receipt_digest,
        sovereign_authorization_digest=sovereign_authorization_digest,
        identity_ttl_seconds=identity_ttl_seconds,
        work_authority_ttl_seconds=work_authority_ttl_seconds,
    )
    if not supply.accepted or supply.status != AUTHORITY_PROFILE_SEED_SUPPLY_ACCEPT:
        return _not_ready(supply.rejection_reasons or ("authority_profile_seed_supply_rejected",))
    return AuthorityProfileSeedBootstrapResult(
        accepted=True,
        status=AUTHORITY_PROFILE_SEED_BOOTSTRAP_APPLIED,
        seed_supply_receipt_id=supply.seed_supply_receipt_id,
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
    return child_r == parent.resolve() or parent.resolve() in child_r.parents


def _not_ready(reasons: tuple[str, ...] | list[str]) -> AuthorityProfileSeedBootstrapResult:
    return AuthorityProfileSeedBootstrapResult(
        accepted=False,
        status=AUTHORITY_PROFILE_SEED_BOOTSTRAP_NOT_READY,
        seed_supply_receipt_id=None,
        output_path=None,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason))),
    )


__all__ = [
    "AUTHORITY_PROFILE_SEED_BOOTSTRAP_APPLIED",
    "AUTHORITY_PROFILE_SEED_BOOTSTRAP_NOT_READY",
    "AuthorityProfileSeedBootstrapResult",
    "run_reddog_authority_profile_seed_supply_bootstrap",
]
