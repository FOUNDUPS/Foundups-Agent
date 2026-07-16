"""Main-startup bridge for RedDog architect FIX promotion.

Slice: REDDOG_ARCHITECT_FIX_PROMOTION_MAIN_PREFLIGHT_PHASE1

This adapter consumes already-produced backend architect, model-selection,
Memex-supply, and authority-profile receipts from outside-repo runtime files.
It promotes one FIX determination into the authoritative work-state queue and
writes the promoted authority profile consumed by the resident serial loop.

It does not sign authority, spawn workers, create worktrees, run shell commands,
enqueue OpenClaw, dispatch Hermes, publish PRs, admit PatternMemory, settle
rewards, mutate source files, or re-index HoloIndex.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_architect_fix_signed_wsp15_work_order_promotion import (
    ARCHITECT_FIX_WSP15_PROMOTION_ACCEPT,
    promote_reddog_architect_fix_to_signed_wsp15_work_order,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_refresh_runtime import (
    AtomicJsonAuthoritativeWorkStateStore,
)


REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED = (
    "REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED"
)
REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_NOT_READY = (
    "REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_NOT_READY"
)


@dataclass(frozen=True)
class RedDogMainArchitectFixPromotionBootstrapResult:
    """Result returned to ``main.py`` for startup reporting."""

    accepted: bool
    status: str
    promotion_receipt_id: Optional[str]
    queue_item_id: Optional[str]
    claim_id: Optional[str]
    selected_slice: Optional[str]
    authority_profile_path: Optional[str]
    committed_revision: Optional[str]
    rejection_reasons: tuple[str, ...]
    no_signing_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_main_architect_fix_promotion_bootstrap(
    *,
    repo_root: Path | str,
    work_state_path: Path | str | None,
    architect_determination_path: Path | str | None,
    model_selection_receipt_path: Path | str | None,
    memex_supply_receipt_path: Path | str | None,
    authority_profile_source_path: Path | str | None,
    authority_profile_output_path: Path | str | None,
    worker_id: str = "reddog-main-architect-fix-promotion",
    now_iso: str | None = None,
) -> RedDogMainArchitectFixPromotionBootstrapResult:
    """Promote one backend architect FIX determination into the resident queue."""

    root = Path(repo_root).resolve()
    reasons: list[str] = []

    work_state_file, work_state_reasons = _resolve_existing_file_outside_repo(
        root,
        work_state_path,
        missing_reason="missing_authoritative_work_state_path",
        inside_reason="work_state_path_inside_repo",
    )
    reasons.extend(work_state_reasons)
    determination, determination_reasons = _read_json_outside_repo(
        root,
        architect_determination_path,
        missing_reason="missing_architect_determination_path",
        inside_reason="architect_determination_path_inside_repo",
        unreadable_reason="malformed_architect_determination",
    )
    reasons.extend(determination_reasons)
    model_selection, model_reasons = _read_json_outside_repo(
        root,
        model_selection_receipt_path,
        missing_reason="missing_model_selection_receipt_path",
        inside_reason="model_selection_receipt_path_inside_repo",
        unreadable_reason="malformed_model_selection_receipt",
    )
    reasons.extend(model_reasons)
    memex_supply, memex_reasons = _read_json_outside_repo(
        root,
        memex_supply_receipt_path,
        missing_reason="missing_memex_supply_receipt_path",
        inside_reason="memex_supply_receipt_path_inside_repo",
        unreadable_reason="malformed_memex_supply_receipt",
    )
    reasons.extend(memex_reasons)
    authority_profile, profile_reasons = _read_json_outside_repo(
        root,
        authority_profile_source_path,
        missing_reason="missing_authority_profile_source_path",
        inside_reason="authority_profile_source_path_inside_repo",
        unreadable_reason="malformed_authority_profile_source",
    )
    reasons.extend(profile_reasons)
    output_path, output_reasons = _resolve_output_outside_repo(
        root,
        authority_profile_output_path,
        missing_reason="missing_authority_profile_output_path",
        inside_reason="authority_profile_output_path_inside_repo",
    )
    reasons.extend(output_reasons)

    if reasons:
        return _not_ready(reasons)

    assert work_state_file is not None
    assert output_path is not None
    assert determination is not None
    assert model_selection is not None
    assert memex_supply is not None
    assert authority_profile is not None

    output_probe_reasons = _probe_atomic_output(output_path)
    if output_probe_reasons:
        return _not_ready(output_probe_reasons)

    store = AtomicJsonAuthoritativeWorkStateStore(work_state_file)
    result = promote_reddog_architect_fix_to_signed_wsp15_work_order(
        architect_determination=determination,
        work_state_store=store,
        authority_profile=authority_profile,
        model_selection_receipt=model_selection,
        memex_supply_receipt=memex_supply,
        worker_id=worker_id,
        now_iso=now_iso or datetime.now(timezone.utc).isoformat(),
    )
    if not result.accepted or result.status != ARCHITECT_FIX_WSP15_PROMOTION_ACCEPT:
        return _not_ready(result.rejection_reasons or ("architect_fix_promotion_rejected",))
    if result.authority_profile is None or result.receipt is None:
        return _not_ready(("architect_fix_promotion_missing_profile",))

    try:
        _write_json_atomic(output_path, result.authority_profile)
    except Exception:
        return _not_ready(("authority_profile_output_write_failed",))

    return RedDogMainArchitectFixPromotionBootstrapResult(
        accepted=True,
        status=REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED,
        promotion_receipt_id=result.receipt.promotion_receipt_id,
        queue_item_id=result.receipt.queue_item_id,
        claim_id=result.receipt.claim_id,
        selected_slice=result.receipt.selected_slice,
        authority_profile_path=str(output_path),
        committed_revision=result.receipt.committed_revision,
        rejection_reasons=(),
    )


def _read_json_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
    unreadable_reason: str,
) -> tuple[Optional[Mapping[str, Any]], list[str]]:
    path, reasons = _resolve_existing_file_outside_repo(
        repo_root,
        value,
        missing_reason=missing_reason,
        inside_reason=inside_reason,
    )
    if reasons:
        return None, reasons
    assert path is not None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, [unreadable_reason]
    if not isinstance(payload, Mapping):
        return None, [unreadable_reason]
    return payload, []


def _resolve_existing_file_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
) -> tuple[Optional[Path], list[str]]:
    if not value:
        return None, [missing_reason]
    path = Path(value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()
    if _is_inside(path, repo_root):
        return None, [inside_reason]
    if not path.exists() or not path.is_file():
        return None, [missing_reason]
    return path, []


def _resolve_output_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
) -> tuple[Optional[Path], list[str]]:
    if not value:
        return None, [missing_reason]
    path = Path(value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()
    if _is_inside(path, repo_root):
        return None, [inside_reason]
    return path, []


def _probe_atomic_output(path: Path) -> list[str]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".probe", dir=str(path.parent))
        os.close(fd)
        os.replace(tmp_name, tmp_name)
        os.unlink(tmp_name)
    except Exception:
        return ["authority_profile_output_not_writable"]
    return []


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, sort_keys=True, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _not_ready(reasons: tuple[str, ...] | list[str]) -> RedDogMainArchitectFixPromotionBootstrapResult:
    return RedDogMainArchitectFixPromotionBootstrapResult(
        accepted=False,
        status=REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_NOT_READY,
        promotion_receipt_id=None,
        queue_item_id=None,
        claim_id=None,
        selected_slice=None,
        authority_profile_path=None,
        committed_revision=None,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason))),
    )


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


__all__ = [
    "REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED",
    "REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_NOT_READY",
    "RedDogMainArchitectFixPromotionBootstrapResult",
    "run_reddog_main_architect_fix_promotion_bootstrap",
]
