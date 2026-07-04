#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FoundUp LIVE scaffold writer (FOUNDUP_SCAFFOLD_WRITER_LIVE_PHASE1).

The FIRST real repo-writing FoundUp slice. Security-sensitive. It materializes the
planned WSP-49 scaffold artifacts into an ISOLATED git worktree (a separate checkout,
never the main working tree), commits them to a feature branch, and opens a DRAFT PR
ONLY. It NEVER mutates main, the registry, public/API routes, secrets, or the WSP
framework, and NEVER marks a PR ready or merges.

This orchestration module contains NO subprocess/git/gh calls. Every git/worktree/PR
side effect is delegated to an INJECTED runner (WorktreeRunner). The real runner lives
in the approved helper `worktree_pr_runner.py`; tests inject a FakeRunner. The file
materialization reuses the 3-round-adversarially-hardened dry-run writer
(scaffold_writer_dryrun.materialize_scaffold_dry_run), which fail-closes on any
repo-inside / registry / traversal / denied / existing-module / non-canonical target.

Authorization (ALL required before any side effect):
    preauth_ready, operation==create_foundup, valve_state==VALVE_OPEN_WORKTREE_CREATE,
    registry_write==False, merge_authority==False, draft_pr_only==True,
    no_live_write_performed==True, supplied packet digest matches the packet,
    scaffold_contract digest matches the packet's scaffold_plan_digest, a valid
    sovereign token bound to the valve env, the valve env resolving to
    VALVE_OPEN_WORKTREE_CREATE, allowed_paths == [modules/foundups/<id>/**], denied
    paths covering .env/secrets/registry/routes/WSP framework, an isolated worktree
    OUTSIDE the main repo, and a target module path that does not exist on base.

NAVIGATION:
    -> Consumes: LiveWriterPreauthPacket (#924) + FoundUpScaffoldContract (#921/#922)
    -> Uses: scaffold_writer_dryrun.materialize_scaffold_dry_run (#923, hardened)
    -> Delegates side effects to: worktree_pr_runner.WorktreeRunner (injected)
    -> Does NOT import subprocess/git/gh/os (AST-guarded by tests).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

VALVE_OPEN_WORKTREE_CREATE = "VALVE_OPEN_WORKTREE_CREATE"
REQUESTED_OPERATION = "create_foundup"
_FOUNDUP_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,49}$")  # WSP 104

# Repo regions a FoundUp scaffold write may NEVER touch (belt-and-braces over the
# contract's own denied_paths). Checked against every artifact + the module_path.
_HARD_DENIED_MARKERS = (
    ".env", "secrets", "foundup_registry.json",
    "public/", "api/", "wsp_framework/", ".git/",
)


@dataclass
class FoundUpLiveWriterResult:
    """Return-value-only result of a live scaffold write attempt."""

    result_id: str
    foundup_id: str
    ok: bool
    rejection_code: Optional[str] = None
    rejection_reason: Optional[str] = None
    preauth_packet_digest: Optional[str] = None
    valve_decision_digest: Optional[str] = None
    worktree_path: Optional[str] = None
    branch_name: Optional[str] = None
    planned_artifacts_count: int = 0
    written_artifacts_count: int = 0
    written_artifacts: List[str] = field(default_factory=list)
    rejected_paths: List[str] = field(default_factory=list)
    validation_results: List[Dict[str, Any]] = field(default_factory=list)
    draft_pr_url: Optional[str] = None
    receipts: List[Dict[str, Any]] = field(default_factory=list)
    registry_mutated: bool = False
    main_mutated: bool = False
    public_routes_mutated: bool = False
    api_routes_mutated: bool = False
    secrets_accessed: bool = False
    merge_performed: bool = False
    cleanup_plan: str = ""
    rollback_plan: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


def _digest(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _default_repo_root() -> Path:
    # modules/foundups/agent/src/foundup_scaffold_writer_live.py -> parents[4] = repo root
    root = Path(__file__).resolve().parents[4]
    if not (root / "WSP_framework").exists() and not (root / ".git").exists():
        raise RuntimeError("foundup_scaffold_writer_live: repo-root sentinel missing (fail-closed)")
    return root


def _is_inside(child: Path, parent: Path) -> bool:
    child, parent = child.resolve(), parent.resolve()
    return child == parent or parent in child.parents


def _touches_hard_denied(rel_path: str) -> bool:
    low = str(rel_path).replace("\\", "/").lower()
    # rstrip only (preserve LEADING dots so dotfile names like .env are compared intact).
    base = low.rsplit("/", 1)[-1].rstrip(" .")
    if base in (".env", "foundup_registry.json"):
        return True
    for marker in _HARD_DENIED_MARKERS:
        m = marker.lower()
        if m.endswith("/") and (low.startswith(m) or ("/" + m) in low):
            return True
        if not m.endswith("/") and (base == m or ("/" + m + "/") in ("/" + low + "/")):
            return True
    return False


def run_foundup_scaffold_writer_live(
    *,
    preauth_packet: Dict[str, Any],
    scaffold_contract: Dict[str, Any],
    supplied_packet_digest: str,
    sovereign_token: str,
    valve_env: Any,
    runner: Any,
    worktree_path: Path,
    base_branch: str = "main",
    repo_root: Optional[Path] = None,
) -> FoundUpLiveWriterResult:
    """Author a NEW FoundUp scaffold in an isolated worktree + open a draft PR ONLY.

    All authorization guards run BEFORE any runner call. On any failure after the
    worktree is created, the runner's cleanup is invoked and a rollback plan recorded.
    NEVER mutates main / registry / routes / secrets, and NEVER merges or marks ready.
    """
    fid = str(preauth_packet.get("foundup_id", ""))
    result = FoundUpLiveWriterResult(
        result_id="", foundup_id=fid, ok=False,
        planned_artifacts_count=int(preauth_packet.get("planned_artifacts_count", 0) or 0),
        rollback_plan=(
            "No mutation to main/registry/routes. If a worktree was created, it is "
            "removed via runner.cleanup_worktree; the feature branch/draft PR (if any) "
            "may be deleted by 012. Main working tree is never touched."
        ),
    )
    repo = Path(repo_root) if repo_root is not None else _default_repo_root()
    worktree_created = False

    def _receipt(step: str, **kw: Any) -> None:
        entry = {"step": step}
        entry.update(kw)
        result.receipts.append(entry)

    def _finalize() -> FoundUpLiveWriterResult:
        result.result_id = "livewrite_" + hashlib.sha256(
            _digest({
                "foundup_id": fid, "ok": result.ok,
                "packet_digest": result.preauth_packet_digest,
                "pr": result.draft_pr_url, "reject": result.rejection_code,
            }).encode("utf-8")
        ).hexdigest()[:16]
        return result

    def _reject(code: str, reason: str) -> FoundUpLiveWriterResult:
        result.ok = False
        result.rejection_code = code
        result.rejection_reason = reason[:300]
        _receipt("rejected", code=code)
        if worktree_created:
            try:
                clean = runner.cleanup_worktree(worktree_path=worktree_path)
            except Exception as exc:  # cleanup must not mask the rejection
                clean = {"ok": False, "error": type(exc).__name__}
            result.cleanup_plan = "worktree removed after rejection"
            _receipt("cleanup_planned", detail=clean)
        else:
            result.cleanup_plan = "no worktree created; nothing to clean up"
            _receipt("cleanup_planned", detail="no_worktree")
        return _finalize()

    # ---- Guard 1: preauth readiness + attestations --------------------------
    if preauth_packet.get("preauth_ready") is not True:
        return _reject("FAIL_PREAUTH_NOT_READY", "preauth packet is not ready")
    if preauth_packet.get("requested_operation") != REQUESTED_OPERATION:
        return _reject("FAIL_INVALID_OPERATION", "requested_operation != create_foundup")
    if preauth_packet.get("requested_valve_state") != VALVE_OPEN_WORKTREE_CREATE:
        return _reject("FAIL_INVALID_VALVE_STATE", "requested_valve_state != VALVE_OPEN_WORKTREE_CREATE")
    for flag, want in (
        ("registry_write", False), ("merge_authority", False),
        ("draft_pr_only", True), ("no_live_write_performed", True),
    ):
        if bool(preauth_packet.get(flag)) is not want:
            return _reject("FAIL_PREAUTH_ATTESTATION", f"preauth attestation {flag} != {want}")

    # ---- Guard 2: packet digest binding -------------------------------------
    recomputed = _digest(preauth_packet)
    result.preauth_packet_digest = recomputed
    if supplied_packet_digest != recomputed:
        return _reject("FAIL_PREAUTH_DIGEST_MISMATCH", "supplied packet digest != recomputed digest")

    # ---- Guard 3: foundup_id + module_path pin ------------------------------
    if not _FOUNDUP_ID_RE.match(fid):
        return _reject("FAIL_INVALID_FOUNDUP_ID", "foundup_id not a valid WSP-104 token")
    module_path = f"modules/foundups/{fid}"
    if str(preauth_packet.get("module_path", "")).replace("\\", "/").rstrip("/") != module_path:
        return _reject("FAIL_INVALID_MODULE_PATH", "packet module_path != modules/foundups/{id}")

    # ---- Guard 4: allowed/denied paths --------------------------------------
    if list(preauth_packet.get("allowed_paths", [])) != [f"{module_path}/**"]:
        return _reject("FAIL_ALLOWED_PATHS", "allowed_paths must be exactly [module_path/**]")
    denied = [str(d).lower() for d in preauth_packet.get("denied_paths", [])]
    if not any(".env" in d for d in denied):
        return _reject("FAIL_DENIED_PATHS", "denied_paths must include .env")

    # ---- Guard 5: contract digest binding -----------------------------------
    if _digest(scaffold_contract) != preauth_packet.get("scaffold_plan_digest"):
        return _reject("FAIL_CONTRACT_DIGEST_MISMATCH", "scaffold_contract digest != packet scaffold_plan_digest")
    if str(scaffold_contract.get("module_path")) != module_path:
        return _reject("FAIL_INVALID_MODULE_PATH", "contract module_path mismatch")

    # ---- Guard 6: sovereign token + valve -----------------------------------
    env = valve_env.to_dict() if hasattr(valve_env, "to_dict") else dict(valve_env or {})
    env_token = str(env.get("sovereign_worktree_token") or "")
    if not str(sovereign_token or "").strip() or str(sovereign_token) != env_token:
        return _reject("FAIL_SOVEREIGN_TOKEN", "sovereign token absent or not bound to valve env")
    from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
        _resolve_valve_state,
    )
    valve_state = _resolve_valve_state(env, [])
    # valve_decision_digest binds the DECISION, never the raw token.
    result.valve_decision_digest = _digest({
        "valve_state": valve_state,
        "worktree_create_enabled": bool(env.get("valve_worktree_create_enabled")),
        "token_digest": _digest(env_token),
    })
    if valve_state != VALVE_OPEN_WORKTREE_CREATE:
        return _reject("FAIL_VALVE_NOT_OPEN", f"valve state {valve_state} != VALVE_OPEN_WORKTREE_CREATE")

    # ---- Guard 7: per-artifact allowed-scope + denied + traversal -----------
    planned = list(scaffold_contract.get("scaffold_artifacts", []))
    for art in planned:
        norm = str(art).replace("\\", "/")
        # A segment is a traversal if it is '..' (incl trailing-space '.. ') or is
        # empty after stripping whitespace/dots (e.g. '.', '...', '') per Win32.
        bad_seg = any(
            s.strip(" \t") == ".." or s.strip(" .\t") == "" for s in norm.split("/")
        )
        if norm.startswith("/") or ":" in norm or bad_seg:
            result.rejected_paths.append(norm)
            return _reject("FAIL_PATH_TRAVERSAL", "artifact path is absolute/traversal/drive")
        if not norm.startswith(f"{module_path}/"):
            result.rejected_paths.append(norm)
            return _reject("FAIL_PATH_OUT_OF_SCOPE", "artifact escapes allowed module path")
        if _touches_hard_denied(norm):
            result.rejected_paths.append(norm)
            return _reject("FAIL_DENIED_PATH", "artifact touches a hard-denied region")

    # ---- Guard 8: target must not exist on base; worktree must be isolated ---
    # Anchor on the UNION of the supplied repo AND the sentinel-checked true repo root:
    # a mis-pointed repo_root can NEVER shrink the forbidden zone (matches the
    # materializer's own anchoring).
    roots = {repo.resolve(), _default_repo_root().resolve()}
    if any((r / module_path).exists() for r in roots):
        return _reject("FAIL_MODULE_EXISTS", "target module path already exists on base")
    wt = Path(worktree_path)
    # Must be ABSOLUTE: a relative path resolves against the orchestration cwd at
    # guard time but against the runner's repo_root at git time -- a divergence that
    # could place the worktree inside main. Fail closed before any resolution.
    if not wt.is_absolute():
        return _reject("FAIL_WORKTREE_NOT_ABSOLUTE", "worktree_path must be absolute")
    # Reject Windows device / extended-length prefixes (\\?\ , \\.\ , //?/ , //./ ,
    # and the \\?\UNC\ form which begins with \\?\). They DISABLE Win32 path
    # normalization: is_absolute() is True and .resolve() keeps a DISTINCT anchor
    # (e.g. \\?\O:\), so a path physically INSIDE the repo would evade the _is_inside
    # isolation checks below and let a live write land in main. Compare the RAW and the
    # resolved string; pathlib renders '/' as '\' on Windows so the backslash prefixes
    # catch the '//?/'-style inputs there, and the slash prefixes catch them on POSIX.
    _raw = str(worktree_path)
    _res = str(wt.resolve())
    for _p in ("\\\\?\\", "\\\\.\\", "//?/", "//./"):
        if _raw.startswith(_p) or _res.startswith(_p):
            return _reject(
                "FAIL_WORKTREE_DEVICE_PREFIX",
                "extended-length/device-prefixed worktree path is forbidden",
            )
    wt_r = wt.resolve()
    if wt_r == Path(wt_r.anchor) or any(_is_inside(wt, r) or _is_inside(r, wt) for r in roots):
        return _reject("FAIL_WORKTREE_INSIDE_MAIN", "worktree must be an isolated dir outside every repo root")

    # ---- Guard 9: target branch must be a feature branch, never protected -----
    branch_name = str(preauth_packet.get("target_branch") or f"feat/foundup-live-writer-{fid}")
    if branch_name in ("main", "master", base_branch) or not branch_name.startswith("feat/"):
        return _reject("FAIL_PROTECTED_BRANCH_TARGET", "target branch must be a feat/* branch, never protected")

    _receipt("preauth_verified", packet_digest=result.preauth_packet_digest)
    _receipt("valve_opened", valve_decision_digest=result.valve_decision_digest)
    result.branch_name = branch_name
    result.worktree_path = str(wt)

    # ---- Resolve the materializer BEFORE any side effect --------------------
    # A deferred import that first executes AFTER the worktree exists could fail at
    # import time (a transitive import error) and orphan a partial worktree with NO
    # cleanup, because the ImportError would escape the guarded region below. Bind it
    # here while worktree_created is still False, so an import failure fails closed as a
    # pre-side-effect rejection with nothing to clean up.
    try:
        from modules.foundups.agent.src.scaffold_writer_dryrun import (
            materialize_scaffold_dry_run,
        )
    except Exception as exc:
        return _reject(
            "FAIL_MATERIALIZER_IMPORT",
            f"materializer import failed before any side effect: {type(exc).__name__}",
        )

    # ---- Create isolated worktree (runner) ----------------------------------
    # git may touch disk (dir + admin entry) even when the create ultimately FAILS,
    # so any create failure must still attempt cleanup. Mark cleanup-needed defensively.
    try:
        wt_receipt = runner.create_worktree(
            worktree_path=wt, branch_name=branch_name, base_branch=base_branch,
        )
    except Exception as exc:
        worktree_created = True  # force best-effort cleanup of a partial worktree
        return _reject("FAIL_WORKTREE_CREATE", f"worktree creation raised: {type(exc).__name__}")
    if not isinstance(wt_receipt, dict) or wt_receipt.get("ok") is not True:
        worktree_created = True  # partial create possible -> force best-effort cleanup
        return _reject("FAIL_WORKTREE_CREATE", "runner.create_worktree did not succeed")
    worktree_created = True
    _receipt("worktree_created", branch=branch_name)

    # ---- Materialize + validate (wrapped: ANY exception after worktree creation
    #      routes through _reject -> guaranteed cleanup + rollback receipt) -----
    # (materialize_scaffold_dry_run was imported above, before the worktree existed.)
    try:
        # Pre-seed guard: a fresh worktree must NOT already contain the target module.
        if (wt / module_path).exists():
            return _reject("FAIL_WORKTREE_NOT_CLEAN", "worktree already contains the target module path")
        mat = materialize_scaffold_dry_run(scaffold_contract, output_root=wt, real_repo_root=repo)
        if not mat.ok:
            return _reject("FAIL_WRITE_REJECTED", f"materialize failed: {mat.rejection_code}")
        if mat.registry_mutated or mat.wrote_to_main_repo:
            return _reject("FAIL_WRITER_SIDE_EFFECT", "materializer reported a real-repo/registry side effect")
        result.written_artifacts = [
            str(Path(p).relative_to(wt)).replace("\\", "/") for p in mat.files_written
        ]
        result.written_artifacts_count = len(result.written_artifacts)
        _receipt("write_completed", written=result.written_artifacts_count)

        planned_rel = sorted(str(a).replace("\\", "/") for a in planned)
        written_rel = sorted(result.written_artifacts)
        # Validate the ACTUAL on-disk module subtree equals the plan EXACTLY -- defeats a
        # pre-seeded worktree that smuggled extra files under the module path.
        target_dir = wt / module_path
        on_disk = sorted(
            str(p.relative_to(wt)).replace("\\", "/")
            for p in target_dir.rglob("*") if p.is_file()
        ) if target_dir.exists() else []
        result.validation_results.append({
            "planned_count": len(planned_rel),
            "written_count": len(written_rel),
            "on_disk_count": len(on_disk),
            "exact_match": written_rel == planned_rel == on_disk,
        })
        if written_rel != planned_rel or on_disk != planned_rel:
            return _reject("FAIL_PLAN_ARTIFACT_MISMATCH", "written/on-disk artifact set != planned set")
        _receipt("validation_completed", exact_match=True)
    except Exception as exc:
        return _reject("FAIL_LIVE_WRITE_EXCEPTION", f"materialize/validation raised: {type(exc).__name__}")

    # ---- Commit + push + DRAFT PR (runner) ----------------------------------
    try:
        commit = runner.commit_all(
            worktree_path=wt, add_paths=[module_path],
            message=f"feat(foundup): scaffold {fid} (draft)",
        )
        push = runner.push_branch(worktree_path=wt, branch_name=branch_name)
        pr_url = runner.create_draft_pr(
            branch_name=branch_name, base_branch=base_branch,
            title=f"feat(foundup): scaffold {fid} (draft, live writer)",
            body=(
                f"Live scaffold for `{fid}` in an isolated worktree. Draft only -- "
                "no merge, no registry write, no main mutation. Authorized by preauth "
                f"packet `{result.preauth_packet_digest}` + valve `{result.valve_decision_digest}`."
            ),
        )
    except Exception as exc:
        return _reject("FAIL_PR_STEP", f"commit/push/pr failed: {type(exc).__name__}")
    if not isinstance(commit, dict) or commit.get("ok") is not True:
        return _reject("FAIL_PR_STEP", "commit did not succeed")
    if not isinstance(push, dict) or push.get("ok") is not True:
        return _reject("FAIL_PR_STEP", "push did not succeed")
    if not pr_url or not isinstance(pr_url, str):
        return _reject("FAIL_PR_STEP", "draft PR was not created")
    result.draft_pr_url = pr_url
    _receipt("draft_pr_created", url=pr_url, draft=True, merged=False, ready=False)

    result.cleanup_plan = (
        f"worktree at {wt} may be removed via runner.cleanup_worktree once 012 has "
        "reviewed the draft PR; branch/PR left intact for review."
    )
    _receipt("cleanup_planned", detail="review_then_remove_worktree")
    result.ok = True
    return _finalize()
