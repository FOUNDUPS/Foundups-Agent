"""Bounded RedDog worktree worker execution pilot.

Slice: REDDOG_BOUNDED_WORKTREE_WORKER_EXECUTION_PILOT_PHASE1

This module is the first narrow pilot that may materialize a scoped text change
inside an already-created isolated worktree. It requires the existing WRE
worktree spine, generic writer dry-run, and governed shell dry-run receipts to
have accepted first. It does not execute shell commands, push, create PRs,
merge, enqueue OpenClaw, dispatch Hermes, settle rewards, or mutate HoloIndex.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_generic_agent_worktree_writer_dryrun import (
    GENERIC_WRITER_DRYRUN_ACCEPT,
    PIN_INDEPENDENT_DENYLIST,
)
from modules.communication.moltbot_bridge.src.reddog_wre_cwd_guard import (
    WreCwdGuardResult,
    validate_wre_worker_operation_cwd,
)
from modules.communication.moltbot_bridge.src.reddog_wre_governed_shell_runner_dryrun import (
    GOVERNED_SHELL_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_operational_spine import (
    WORKTREE_SPINE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_worktree_create import (
    WORKTREE_CREATE_ACCEPT,
)

BOUNDED_WORKTREE_PILOT_ACCEPT = "BOUNDED_WORKTREE_PILOT_ACCEPT"
BOUNDED_WORKTREE_PILOT_REJECT = "BOUNDED_WORKTREE_PILOT_REJECT"

FAIL_WORKTREE_SPINE = "FAIL_WORKTREE_SPINE"
FAIL_GENERIC_WRITER_DRYRUN = "FAIL_GENERIC_WRITER_DRYRUN"
FAIL_GOVERNED_SHELL_DRYRUN = "FAIL_GOVERNED_SHELL_DRYRUN"
FAIL_CWD_GUARD = "FAIL_CWD_GUARD"
FAIL_WORKTREE_MISSING = "FAIL_WORKTREE_MISSING"
FAIL_CANONICAL_ROOT_INVALID = "FAIL_CANONICAL_ROOT_INVALID"
FAIL_ARTIFACTS_MISMATCH = "FAIL_ARTIFACTS_MISMATCH"
FAIL_ARTIFACT_OUTSIDE_ROOT = "FAIL_ARTIFACT_OUTSIDE_ROOT"
FAIL_DENIED_ARTIFACT = "FAIL_DENIED_ARTIFACT"
FAIL_CONTENT_INVALID = "FAIL_CONTENT_INVALID"
FAIL_SYMLINK_PATH = "FAIL_SYMLINK_PATH"
FAIL_HOLOINDEX_INDEX_GAP = "FAIL_HOLOINDEX_INDEX_GAP"

MAX_PILOT_FILES = 8
MAX_FILE_BYTES = 64 * 1024
MAX_TOTAL_BYTES = 256 * 1024
SECRET_MARKERS = (
    "api_key",
    "apikey",
    "authorization:",
    "bearer ",
    "begin private key",
    "private_key",
    "password=",
    "secret=",
    "token=",
)


@dataclass(frozen=True)
class BoundedWorktreePilotReceipt:
    receipt_id: str
    work_order_id: str
    worktree_path: str
    canonical_root: str
    written_artifacts: List[str]
    artifact_manifest_digest: str
    written_artifact_digest: str
    worktree_spine_result_digest: str
    generic_writer_receipt_digest: str
    governed_shell_receipt_digest: str
    cwd_guard_receipt_digest: str
    validation_command_executed: bool = False
    draft_pr_created: bool = False
    merge_performed: bool = False
    openclaw_enqueue_performed: bool = False
    hermes_dispatch_performed: bool = False
    reward_settlement_performed: bool = False
    holoindex_reindex_performed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BoundedWorktreeWorkerExecutionPilotResult:
    decision: str
    accepted: bool
    rejection_reasons: List[str]
    receipt: Optional[BoundedWorktreePilotReceipt]
    cwd_guard: Optional[WreCwdGuardResult]
    task_execution_performed: bool
    file_edit_performed: bool
    shell_command_executed: bool = False
    draft_pr_created: bool = False
    merge_performed: bool = False
    openclaw_enqueue_performed: bool = False
    hermes_dispatch_performed: bool = False
    reward_settlement_performed: bool = False
    holoindex_reindex_performed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict() if self.receipt else None
        payload["cwd_guard"] = self.cwd_guard.to_dict() if self.cwd_guard else None
        return payload


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return value
    return {}


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _dedupe(values: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def _normalize_repo_path(value: str) -> Optional[str]:
    text = str(value or "").replace("\\", "/").strip()
    if not text or text.startswith("/") or text.startswith(("\\\\?\\", "\\\\.\\", "//?/", "//./")):
        return None
    parts: List[str] = []
    for raw in text.split("/"):
        part = raw.strip(" \t").rstrip(" .")
        if not part or part in {".", ".."} or ":" in part:
            return None
        parts.append(part)
    return "/".join(parts)


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _path_denied(path: str) -> bool:
    base = path.rsplit("/", 1)[-1].rstrip(" .").lower()
    if base in {".env", "foundup_registry.json"}:
        return True
    for pattern in PIN_INDEPENDENT_DENYLIST:
        pat = pattern.replace("\\", "/").strip()
        if fnmatch.fnmatch(path.lower(), pat.lower()):
            return True
        if pat.endswith("/**"):
            stem = pat[:-3].lower().rstrip("/")
            if path.lower() == stem or path.lower().startswith(stem + "/"):
                return True
    return False


def _content_reasons(contents: Mapping[str, Any]) -> List[str]:
    reasons: List[str] = []
    if not contents or len(contents) > MAX_PILOT_FILES:
        reasons.append(FAIL_ARTIFACTS_MISMATCH)
    total = 0
    for value in contents.values():
        if not isinstance(value, str) or "\x00" in value:
            reasons.append(FAIL_CONTENT_INVALID)
            continue
        lower = value.lower()
        if any(marker in lower for marker in SECRET_MARKERS):
            reasons.append(FAIL_CONTENT_INVALID)
        size = len(value.encode("utf-8"))
        total += size
        if size > MAX_FILE_BYTES:
            reasons.append(FAIL_CONTENT_INVALID)
    if total > MAX_TOTAL_BYTES:
        reasons.append(FAIL_CONTENT_INVALID)
    return reasons


def _parent_has_symlink(path: Path, stop_at: Path) -> bool:
    current = path
    stop = stop_at.resolve()
    while current != stop and current != current.parent:
        if current.exists() and current.is_symlink():
            return True
        current = current.parent
    return False


def _validate_receipts(
    req: Mapping[str, Any],
) -> tuple[List[str], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    reasons: List[str] = []
    spine = _mapping(req.get("worktree_spine_result"))
    worktree_create = _mapping(spine.get("worktree_create_result"))
    writer = _mapping(req.get("generic_writer_dryrun_result"))
    writer_receipt = _mapping(writer.get("receipt"))
    shell = _mapping(req.get("governed_shell_dryrun_result"))
    shell_receipt = _mapping(shell.get("receipt"))

    if spine.get("decision") != WORKTREE_SPINE_ACCEPT:
        reasons.append(FAIL_WORKTREE_SPINE)
    if worktree_create.get("decision") != WORKTREE_CREATE_ACCEPT:
        reasons.append(FAIL_WORKTREE_SPINE)
    if (
        spine.get("no_file_edit_performed") is not True
        or spine.get("no_task_execution_performed") is not True
    ):
        reasons.append(FAIL_WORKTREE_SPINE)
    if writer.get("decision") != GENERIC_WRITER_DRYRUN_ACCEPT or not writer_receipt:
        reasons.append(FAIL_GENERIC_WRITER_DRYRUN)
    if writer_receipt and (
        writer_receipt.get("no_write_performed") is not True
        or writer_receipt.get("no_worktree_created") is not True
        or writer_receipt.get("no_shell_performed") is not True
    ):
        reasons.append(FAIL_GENERIC_WRITER_DRYRUN)
    if shell.get("decision") != GOVERNED_SHELL_DRYRUN_ACCEPT or not shell_receipt:
        reasons.append(FAIL_GOVERNED_SHELL_DRYRUN)
    if shell_receipt and shell_receipt.get("no_command_executed") is not True:
        reasons.append(FAIL_GOVERNED_SHELL_DRYRUN)
    return reasons, spine, writer_receipt, shell_receipt


def _validate_artifacts(
    *,
    contents: Mapping[str, Any],
    writer_receipt: Mapping[str, Any],
    canonical_root: str,
) -> tuple[List[str], List[str]]:
    reasons = _content_reasons(contents)
    normalized_contents: Dict[str, Any] = {}
    for raw, value in contents.items():
        normalized = _normalize_repo_path(str(raw))
        if normalized is None:
            reasons.append(FAIL_ARTIFACTS_MISMATCH)
            continue
        normalized_contents[normalized] = value
    planned = sorted(str(v) for v in writer_receipt.get("planned_artifacts") or [])
    supplied = sorted(normalized_contents)
    if planned != supplied:
        reasons.append(FAIL_ARTIFACTS_MISMATCH)
    for rel in supplied:
        if not (rel == canonical_root or rel.startswith(canonical_root.rstrip("/") + "/")):
            reasons.append(FAIL_ARTIFACT_OUTSIDE_ROOT)
        if _path_denied(rel):
            reasons.append(FAIL_DENIED_ARTIFACT)
    return reasons, supplied


def _materialize_text_artifacts(
    *,
    worktree_path: Path,
    canonical_root: str,
    artifact_contents: Mapping[str, Any],
) -> Dict[str, str]:
    written: Dict[str, str] = {}
    root = (worktree_path / canonical_root).resolve()
    for raw, content in artifact_contents.items():
        rel = _normalize_repo_path(str(raw))
        if rel is None:
            raise ValueError("invalid_artifact_path")
        target = (worktree_path / rel).resolve()
        if not _is_inside(target, root):
            raise ValueError("artifact_outside_root")
        if _parent_has_symlink(target.parent, worktree_path):
            raise ValueError("symlink_parent")
        if target.exists() and target.is_symlink():
            raise ValueError("symlink_target")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(content), encoding="utf-8", newline="\n")
        if not _is_inside(target.resolve(), root):
            raise ValueError("artifact_escape_after_write")
        written[rel] = _digest(target.read_text(encoding="utf-8"))
    return written


def run_bounded_worktree_worker_execution_pilot(
    request: Mapping[str, Any],
) -> BoundedWorktreeWorkerExecutionPilotResult:
    """Run one bounded text-materialization pilot inside an isolated worktree."""
    req = _mapping(request)
    reasons, spine, writer_receipt, shell_receipt = _validate_receipts(req)

    work_order_id = str(req.get("work_order_id") or spine.get("work_order_id") or "")
    repo_root = Path(str(req.get("repo_root") or ""))
    worktree_path = Path(str(req.get("worktree_path") or ""))
    operation_cwd = Path(str(req.get("operation_cwd") or req.get("worktree_path") or ""))
    cwd_guard: Optional[WreCwdGuardResult] = None

    try:
        cwd_guard = validate_wre_worker_operation_cwd(
            repo_root=repo_root,
            worktree_path=worktree_path,
            operation_cwd=operation_cwd,
        )
        if not cwd_guard.ok:
            reasons.append(FAIL_CWD_GUARD)
    except Exception:
        reasons.append(FAIL_CWD_GUARD)

    if not worktree_path.exists() or not worktree_path.is_dir():
        reasons.append(FAIL_WORKTREE_MISSING)

    canonical_root = _normalize_repo_path(
        str(req.get("canonical_root") or writer_receipt.get("canonical_root") or "")
    )
    if not canonical_root:
        reasons.append(FAIL_CANONICAL_ROOT_INVALID)

    contents = (
        req.get("artifact_contents")
        if isinstance(req.get("artifact_contents"), Mapping)
        else {}
    )
    supplied: List[str] = []
    if canonical_root:
        artifact_reasons, supplied = _validate_artifacts(
            contents=contents,
            writer_receipt=writer_receipt,
            canonical_root=canonical_root,
        )
        reasons.extend(artifact_reasons)

    holo = _mapping(req.get("holoindex_evidence"))
    if (
        holo.get("index_gap_detected") is True
        or str(holo.get("retrieval_quality") or "").upper() == "INDEX_GAP"
    ):
        reasons.append(FAIL_HOLOINDEX_INDEX_GAP)

    deduped = _dedupe(reasons)
    if deduped:
        return BoundedWorktreeWorkerExecutionPilotResult(
            decision=BOUNDED_WORKTREE_PILOT_REJECT,
            accepted=False,
            rejection_reasons=deduped,
            receipt=None,
            cwd_guard=cwd_guard,
            task_execution_performed=False,
            file_edit_performed=False,
        )

    assert canonical_root is not None
    try:
        written = _materialize_text_artifacts(
            worktree_path=worktree_path,
            canonical_root=canonical_root,
            artifact_contents=contents,
        )
    except ValueError as exc:
        code = FAIL_SYMLINK_PATH if "symlink" in str(exc) else FAIL_ARTIFACT_OUTSIDE_ROOT
        return BoundedWorktreeWorkerExecutionPilotResult(
            decision=BOUNDED_WORKTREE_PILOT_REJECT,
            accepted=False,
            rejection_reasons=[code],
            receipt=None,
            cwd_guard=cwd_guard,
            task_execution_performed=False,
            file_edit_performed=False,
        )

    artifact_digest = _digest({"written": written})
    receipt_seed = {
        "work_order_id": work_order_id,
        "canonical_root": canonical_root,
        "written_artifacts": sorted(written),
        "artifact_digest": artifact_digest,
        "worktree_spine_result_digest": str(spine.get("result_digest") or _digest(spine)),
    }
    receipt = BoundedWorktreePilotReceipt(
        receipt_id=(
            "bounded_wt_pilot_"
            + hashlib.sha256(_digest(receipt_seed).encode("utf-8")).hexdigest()[:16]
        ),
        work_order_id=work_order_id,
        worktree_path=str(worktree_path.resolve()),
        canonical_root=canonical_root,
        written_artifacts=sorted(supplied),
        artifact_manifest_digest=str(writer_receipt.get("artifact_manifest_digest") or ""),
        written_artifact_digest=artifact_digest,
        worktree_spine_result_digest=str(spine.get("result_digest") or _digest(spine)),
        generic_writer_receipt_digest=str(
            writer_receipt.get("receipt_id") or _digest(writer_receipt)
        ),
        governed_shell_receipt_digest=str(
            shell_receipt.get("run_receipt_id") or _digest(shell_receipt)
        ),
        cwd_guard_receipt_digest=_digest(cwd_guard.to_dict() if cwd_guard else {}),
    )
    return BoundedWorktreeWorkerExecutionPilotResult(
        decision=BOUNDED_WORKTREE_PILOT_ACCEPT,
        accepted=True,
        rejection_reasons=[],
        receipt=receipt,
        cwd_guard=cwd_guard,
        task_execution_performed=True,
        file_edit_performed=True,
    )


__all__ = [
    "BOUNDED_WORKTREE_PILOT_ACCEPT",
    "BOUNDED_WORKTREE_PILOT_REJECT",
    "BoundedWorktreePilotReceipt",
    "BoundedWorktreeWorkerExecutionPilotResult",
    "FAIL_ARTIFACTS_MISMATCH",
    "FAIL_ARTIFACT_OUTSIDE_ROOT",
    "FAIL_CANONICAL_ROOT_INVALID",
    "FAIL_CONTENT_INVALID",
    "FAIL_CWD_GUARD",
    "FAIL_DENIED_ARTIFACT",
    "FAIL_GENERIC_WRITER_DRYRUN",
    "FAIL_GOVERNED_SHELL_DRYRUN",
    "FAIL_HOLOINDEX_INDEX_GAP",
    "FAIL_SYMLINK_PATH",
    "FAIL_WORKTREE_MISSING",
    "FAIL_WORKTREE_SPINE",
    "run_bounded_worktree_worker_execution_pilot",
]
