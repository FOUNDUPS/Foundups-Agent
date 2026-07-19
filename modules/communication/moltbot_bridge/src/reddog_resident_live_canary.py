"""Operator harness for one guarded resident RedDog live canary.

Slice: REDDOG_RESIDENT_LIVE_CANARY_PHASE1

This module does not implement queue orchestration.  It validates the operator
boundary for the existing highest guarded resident profile and, only after an
explicit confirmation, delegates once to ``main.py``'s bounded resident control
loop.  A live proof is reported only when that invocation creates both a new
chain revision and a new control-loop receipt and the existing planner proves
the complete draft-PR-only chain.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_resident_live_canary_environment import (
    build_live_canary_environment,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
    PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY,
)
from modules.communication.moltbot_bridge.src.reddog_resident_live_canary_evidence import (
    CanaryInvocationEvidence,
    chain_receipt_ids,
    evaluate_live_proof,
    read_control_receipts,
    select_new_control_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_resident_live_canary_control_preflight import (
    verify_live_canary_control_prestate,
)
from modules.communication.moltbot_bridge.src.reddog_resident_runtime_artifact_readiness import (
    validate_reddog_resident_runtime_artifacts,
)


LIVE_CANARY_SCHEMA_VERSION = "reddog_resident_live_canary_receipt.v1"
LIVE_CANARY_CONFIRMATION = "REDDOG_RESIDENT_LIVE_CANARY_PHASE1"
LIVE_CANARY_READY = "READY_FOR_EXECUTION"
LIVE_CANARY_BLOCKED = "BLOCKED"
LIVE_CANARY_EXECUTION_FAILED = "EXECUTION_FAILED"
LIVE_CANARY_PROOF_INCOMPLETE = "LIVE_PROOF_INCOMPLETE"
LIVE_CANARY_PROOF_COMPLETE = "LIVE_PROOF_COMPLETE"

REQUIRED_JSON_ARTIFACTS = (
    "authoritative_work_state.json",
    "authority_profile.json",
    "authority_profile_source.json",
    "execution_valve_env.json",
    "permission_snapshots.json",
    "principal_authority_records.json",
    "signer_service_config.json",
    "signer_service_run_packet.json",
)


@dataclass(frozen=True)
class LiveCanaryReadinessCheck:
    name: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class LiveCanaryReceipt:
    schema_version: str
    receipt_id: str
    created_at: str
    status: str
    profile: str
    execution_requested: bool
    execution_confirmed: bool
    execution_invoked: bool
    ready_for_execution: bool
    control_loop_accepted: bool
    live_proof_complete: bool
    readiness_checks: tuple[LiveCanaryReadinessCheck, ...]
    blockers: tuple[str, ...]
    control_receipt_id: Optional[str]
    previous_chain_revision: Optional[str]
    observed_chain_revision: Optional[str]
    chain_plan_id: Optional[str]
    verified_draft_pr_receipt_id: Optional[str]
    verified_draft_pr_url: Optional[str]
    pattern_memory_admission_id: Optional[str]
    pattern_memory_record_id: Optional[str]
    pattern_memory_record_digest: Optional[str]
    accepted_stage_count: int
    repo_root_digest: str
    runtime_root_digest: str
    authorization_mode: Optional[str]
    authorization_binding_digest: Optional[str]
    draft_pr_only: bool = True
    merge_authority_available: bool = False
    no_merge_performed: bool = True
    runtime_state_outside_repo: bool = True
    isolated_worktree_observed: bool = False
    secret_values_serialized: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["readiness_checks"] = [asdict(item) for item in self.readiness_checks]
        payload["blockers"] = list(self.blockers)
        return payload


ControlLoopRunner = Callable[[Path], Mapping[str, Any]]
CommandResolver = Callable[[str], Optional[str]]
CommandProbe = Callable[[Sequence[str], Path], bool]
SocketProbe = Callable[[Path], bool]


@dataclass(frozen=True)
class _CanaryContext:
    repo_root: Path
    runtime_root: Path
    receipt_path: Path
    environ: Mapping[str, str]
    platform_name: str


def run_reddog_resident_live_canary(
    *,
    repo_root: Path | str, runtime_root: Path | str,
    receipt_path: Path | str | None = None,
    execute: bool = False,
    confirmation: str = "",
    queue_item_id: str = "",
    max_rounds: int = 8,
    environ: Optional[Mapping[str, str]] = None,
    platform_name: Optional[str] = None,
    command_resolver: CommandResolver = shutil.which,
    command_probe: Optional[CommandProbe] = None,
    socket_probe: Optional[SocketProbe] = None, control_loop_runner: Optional[ControlLoopRunner] = None,
    now: Optional[Callable[[], datetime]] = None,
) -> LiveCanaryReceipt:
    """Assess readiness and optionally invoke the existing resident control loop."""
    context = _canary_context(repo_root, runtime_root, receipt_path, environ, platform_name)
    timestamp = (now or (lambda: datetime.now(timezone.utc)))().astimezone(timezone.utc).isoformat()
    checks = _readiness_checks(
        repo_root=context.repo_root,
        runtime_root=context.runtime_root,
        receipt_path=context.receipt_path,
        environ=context.environ,
        platform_name=context.platform_name,
        command_resolver=command_resolver,
        command_probe=command_probe or _command_succeeds,
        socket_probe=socket_probe or _is_unix_socket,
        max_rounds=max_rounds,
        queue_item_id=queue_item_id,
        now_epoch=int(datetime.fromisoformat(timestamp).timestamp()),
    )
    invocation = _invoke_canary(
        context=context,
        checks=checks,
        execute=execute,
        confirmation=confirmation,
        queue_item_id=queue_item_id,
        max_rounds=max_rounds,
        runner=control_loop_runner or _run_existing_control_loop,
    )
    proof = evaluate_live_proof(
        repo_root=context.repo_root,
        runtime_root=context.runtime_root,
        queue_item_id=queue_item_id,
        invocation=invocation,
        now_iso=timestamp,
    )
    receipt = _build_live_canary_receipt(context, checks, invocation, proof, execute, timestamp)
    _persist_receipt(context, receipt)
    return receipt


def _persist_receipt(context: _CanaryContext, receipt: LiveCanaryReceipt) -> None:
    _write_json_atomic(
        context.receipt_path,
        receipt.to_dict(),
        repo_root=context.repo_root,
        runtime_root=context.runtime_root,
    )


def _canary_context(
    repo_root: Path | str,
    runtime_root: Path | str,
    receipt_path: Path | str | None,
    environ: Optional[Mapping[str, str]],
    platform_name: Optional[str],
) -> _CanaryContext:
    root = Path(repo_root).resolve()
    runtime = Path(runtime_root).resolve()
    target = _validated_receipt_path(root, runtime, receipt_path)
    return _CanaryContext(
        repo_root=root,
        runtime_root=runtime,
        receipt_path=target,
        environ=dict(os.environ if environ is None else environ),
        platform_name=str(platform_name or sys.platform).lower(),
    )


def _validated_receipt_path(
    repo_root: Path,
    runtime_root: Path,
    receipt_path: Path | str | None,
) -> Path:
    canonical_path = runtime_root / "live_canary_receipt.json"
    if canonical_path.is_symlink():
        raise ValueError("receipt_path_reserved_or_collision")
    canonical = canonical_path.resolve()
    target = Path(receipt_path).resolve() if receipt_path else canonical
    if _is_inside(target, repo_root):
        raise ValueError("receipt_path_inside_repo")
    if _is_inside(target, runtime_root) and target != canonical:
        raise ValueError("receipt_path_reserved_or_collision")
    return target


def _invoke_canary(
    *,
    context: _CanaryContext, checks: Sequence[LiveCanaryReadinessCheck],
    execute: bool, confirmation: str,
    queue_item_id: str, max_rounds: int,
    runner: ControlLoopRunner,
) -> CanaryInvocationEvidence:
    blockers = [check.reason for check in checks if not check.passed]
    confirmed = execute and confirmation == LIVE_CANARY_CONFIRMATION
    if execute and not confirmed:
        blockers.append("explicit_execution_confirmation_missing")
    chain_path = context.runtime_root / "resident_queue_chain_results.json"
    control_path = context.runtime_root / "resident_queue_control_loop_receipts.jsonl"
    pre_chain_state = _read_json_mapping(chain_path, allowed_root=context.runtime_root)
    previous_revision = _text(pre_chain_state.get("revision"))
    pre_chain_ids = chain_receipt_ids(pre_chain_state)
    pre_control_receipts = _read_control_receipt_stream(
        control_path, blockers, allowed_root=context.runtime_root
    )
    _verify_control_receipts(context, pre_control_receipts, blockers)
    invoked = execute and confirmed and not blockers
    result = _invoke_control_runner(
        context, runner, queue_item_id, max_rounds, invoked
    )
    chain_state = _read_json_mapping(chain_path, allowed_root=context.runtime_root)
    control_receipt_id = _text(result.get("receipt_id"))
    post_control_receipts = _verified_post_control_receipts(
        context, control_path, pre_control_receipts, blockers
    )
    control_receipt = select_new_control_receipt(
        pre_control_receipts,
        post_control_receipts,
        control_receipt_id,
    )
    return CanaryInvocationEvidence(
        confirmed=confirmed,
        invoked=invoked,
        blockers=tuple(blockers),
        control_result=result,
        previous_revision=previous_revision,
        observed_revision=_text(chain_state.get("revision")),
        control_receipt_id=control_receipt_id,
        control_receipt=control_receipt,
        pre_chain_receipt_ids=pre_chain_ids,
        work_state=_read_json_mapping(
            context.runtime_root / "authoritative_work_state.json",
            allowed_root=context.runtime_root,
        ),
        chain_state=chain_state,
    )


def _invoke_control_runner(
    context: _CanaryContext, runner: ControlLoopRunner,
    queue_item_id: str, max_rounds: int, invoked: bool,
) -> Mapping[str, Any]:
    if not invoked:
        return {}
    overlay = build_live_canary_environment(
        runtime_root=context.runtime_root, environ=context.environ,
        queue_item_id=queue_item_id, max_rounds=max_rounds,
    )
    with _temporary_environment(overlay):
        return _mapping(runner(context.repo_root))


def _verified_post_control_receipts(
    context: _CanaryContext,
    path: Path,
    pre_receipts: tuple[Mapping[str, Any], ...],
    blockers: list[str],
) -> tuple[Mapping[str, Any], ...]:
    post_receipts = _read_control_receipt_stream(
        path, blockers, allowed_root=context.runtime_root
    )
    if len(post_receipts) < len(pre_receipts) or post_receipts[
        : len(pre_receipts)
    ] != pre_receipts:
        blockers.append("control_receipt_stream_not_append_only")
    try:
        profile = _read_json_mapping(
            context.runtime_root / "authority_profile.json",
            allowed_root=context.runtime_root,
        )
        source = _read_json_mapping(
            context.runtime_root / "authority_profile_source.json",
            allowed_root=context.runtime_root,
        )
        verify_live_canary_control_prestate(
            runtime_root=context.runtime_root,
            receipts=post_receipts,
            authority_profile=profile,
            authority_profile_source=source,
            expected_source_receipt_id=str(
                context.environ.get("REDDOG_AUTHORITY_PROFILE_SOURCE_RECEIPT_ID")
                or ""
            ),
            signer_anchor_path=_signer_anchor_path(context),
        )
    except (KeyError, TypeError, ValueError):
        blockers.append("control_receipt_stream_auth_or_integrity_invalid")
    return post_receipts


def _verify_control_receipts(
    context: _CanaryContext,
    receipts: tuple[Mapping[str, Any], ...],
    blockers: list[str],
) -> None:
    try:
        profile = _read_json_mapping(
            context.runtime_root / "authority_profile.json",
            allowed_root=context.runtime_root,
        )
        source = _read_json_mapping(
            context.runtime_root / "authority_profile_source.json",
            allowed_root=context.runtime_root,
        )
        expected_source = str(
            context.environ.get("REDDOG_AUTHORITY_PROFILE_SOURCE_RECEIPT_ID") or ""
        )
        verify_live_canary_control_prestate(
            runtime_root=context.runtime_root,
            receipts=receipts,
            authority_profile=profile,
            authority_profile_source=source,
            expected_source_receipt_id=expected_source,
            signer_anchor_path=_signer_anchor_path(context),
        )
    except (KeyError, TypeError, ValueError):
        blockers.append("control_receipt_prestate_auth_or_integrity_invalid")


def _signer_anchor_path(context: _CanaryContext) -> Path:
    config = _read_json_mapping(
        context.runtime_root / "signer_service_config.json",
        allowed_root=context.runtime_root,
    )
    value = str(config.get("control_loop_anchor_path") or "").strip()
    if not value:
        raise ValueError("signer_control_loop_anchor_path_missing")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("signer_control_loop_anchor_path_invalid")
    return path.resolve()


def _read_control_receipt_stream(
    path: Path,
    blockers: list[str],
    *,
    allowed_root: Path,
) -> tuple[Mapping[str, Any], ...]:
    try:
        return read_control_receipts(path, allowed_root=allowed_root)
    except ValueError:
        blockers.append("control_receipt_stream_invalid")
        return ()


def _readiness_checks(
    *,
    repo_root: Path,
    runtime_root: Path,
    receipt_path: Path,
    environ: Mapping[str, str],
    platform_name: str,
    command_resolver: CommandResolver,
    command_probe: CommandProbe,
    socket_probe: SocketProbe,
    max_rounds: int,
    queue_item_id: str,
    now_epoch: int,
) -> list[LiveCanaryReadinessCheck]:
    checks = [
        _check("linux_execution_plane", platform_name.startswith("linux"), "linux_execution_plane_required"),
        _check("repo_root", repo_root.is_dir() and (repo_root / ".git").exists(), "repo_root_invalid"),
        _check("runtime_root_outside_repo", not _is_inside(runtime_root, repo_root), "runtime_root_inside_repo"),
        _check("receipt_outside_repo", not _is_inside(receipt_path, repo_root), "receipt_path_inside_repo"),
        _check("max_rounds", isinstance(max_rounds, int) and 1 <= max_rounds <= 8, "invalid_max_rounds"),
        _check("git_available", bool(command_resolver("git")), "git_not_available"),
        _check("gh_available", bool(command_resolver("gh")), "gh_not_available"),
        _check(
            "git_worktree_ready",
            command_probe(("git", "rev-parse", "--is-inside-work-tree"), repo_root),
            "git_worktree_not_ready",
        ),
        _check(
            "gh_authenticated",
            command_probe(("gh", "auth", "status"), repo_root),
            "gh_not_authenticated",
        ),
        _check("openrouter_key_reference", bool(str(environ.get("OPENROUTER_API_KEY") or "")), "openrouter_api_key_missing"),
    ]
    for filename in REQUIRED_JSON_ARTIFACTS:
        valid = _valid_json_mapping(
            runtime_root / filename,
            allowed_root=runtime_root,
        )
        checks.append(_check(f"artifact:{filename}", valid, f"missing_or_malformed:{filename}"))
    semantic = validate_reddog_resident_runtime_artifacts(
        repo_root=repo_root, runtime_root=runtime_root,
        queue_item_id=queue_item_id, now_epoch=now_epoch,
    )
    for item in semantic.checks:
        reason = item.rejection_reasons[0] if item.rejection_reasons else ""
        checks.append(_check(f"semantic:{item.filename}", item.accepted, reason))
    socket_path = runtime_root / "reddog_signer.sock"
    checks.append(_check("signer_socket", socket_probe(socket_path), "signer_socket_not_ready"))
    return checks


def _run_existing_control_loop(repo_root: Path) -> Mapping[str, Any]:
    import main

    accepted = main.run_reddog_resident_queue_control_loop_preflight(repo_root)
    result = _mapping(getattr(main.run_reddog_resident_queue_control_loop_preflight, "last_result", {}))
    if not result:
        return {"accepted": bool(accepted), "status": "CONTROL_RESULT_MISSING"}
    return result


def _build_live_canary_receipt(
    context: _CanaryContext,
    checks: Sequence[LiveCanaryReadinessCheck],
    invocation: CanaryInvocationEvidence,
    proof: Mapping[str, Any],
    execute: bool, created_at: str,
) -> LiveCanaryReceipt:
    blockers = list(invocation.blockers)
    if invocation.invoked:
        blockers.extend(str(value) for value in proof.get("blockers", ()))
    blockers = list(dict.fromkeys(blockers))
    ready = all(check.passed for check in checks)
    control_accepted = invocation.control_result.get("accepted") is True
    live_complete = invocation.invoked and proof.get("complete") is True
    status = _canary_status(invocation.invoked, control_accepted, live_complete, blockers)
    authorization = _canary_authorization_binding(context.runtime_root)
    seed = _receipt_seed(created_at, status, invocation, blockers, authorization)
    return LiveCanaryReceipt(
        schema_version=LIVE_CANARY_SCHEMA_VERSION,
        receipt_id="reddog_live_canary_" + _digest(seed)[:16],
        created_at=created_at,
        status=status,
        profile=PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY,
        execution_requested=bool(execute),
        execution_confirmed=invocation.confirmed,
        execution_invoked=invocation.invoked,
        ready_for_execution=ready,
        control_loop_accepted=control_accepted,
        live_proof_complete=live_complete,
        readiness_checks=tuple(checks),
        blockers=tuple(blockers),
        control_receipt_id=invocation.control_receipt_id,
        previous_chain_revision=invocation.previous_revision,
        observed_chain_revision=invocation.observed_revision,
        chain_plan_id=proof.get("plan_id"),
        verified_draft_pr_receipt_id=proof.get("draft_pr_receipt_id"),
        verified_draft_pr_url=proof.get("draft_pr_url"),
        pattern_memory_admission_id=proof.get("pattern_memory_admission_id"),
        pattern_memory_record_id=proof.get("pattern_memory_record_id"),
        pattern_memory_record_digest=proof.get("pattern_memory_record_digest"),
        accepted_stage_count=int(proof.get("accepted_stage_count") or 0),
        repo_root_digest=_digest(str(context.repo_root)),
        runtime_root_digest=_digest(str(context.runtime_root)),
        authorization_mode=authorization.get("authorization_mode"),
        authorization_binding_digest=authorization.get("authorization_binding_digest"),
        no_merge_performed=not invocation.invoked or proof.get("no_merge_performed") is True,
        runtime_state_outside_repo=not _is_inside(context.runtime_root, context.repo_root),
        isolated_worktree_observed=proof.get("isolated_worktree_observed") is True,
    )


def _canary_status(
    invoked: bool,
    control_accepted: bool,
    live_complete: bool,
    blockers: Sequence[str],
) -> str:
    if live_complete:
        return LIVE_CANARY_PROOF_COMPLETE
    if invoked and not control_accepted:
        return LIVE_CANARY_EXECUTION_FAILED
    if invoked:
        return LIVE_CANARY_PROOF_INCOMPLETE
    return LIVE_CANARY_BLOCKED if blockers else LIVE_CANARY_READY


def _receipt_seed(
    created_at: str,
    status: str,
    invocation: CanaryInvocationEvidence,
    blockers: Sequence[str],
    authorization: Mapping[str, Optional[str]],
) -> dict[str, Any]:
    return {
        "created_at": created_at,
        "status": status,
        "profile": PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY,
        "execution_invoked": invocation.invoked,
        "control_receipt_id": invocation.control_receipt_id,
        "observed_chain_revision": invocation.observed_revision,
        "blockers": list(blockers),
        "authorization_mode": authorization.get("authorization_mode"),
        "authorization_binding_digest": authorization.get("authorization_binding_digest"),
    }


def _canary_authorization_binding(runtime_root: Path) -> dict[str, Optional[str]]:
    payload = _read_json_mapping(
        runtime_root / "execution_valve_env.json",
        allowed_root=runtime_root,
    )
    mode = _text(payload.get("authorization_mode"))
    digest = _text(payload.get("authorization_binding_digest"))
    return {
        "authorization_mode": mode or None,
        "authorization_binding_digest": digest or None,
    }


@contextmanager
def _temporary_environment(values: Mapping[str, str]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _write_json_atomic(
    path: Path,
    payload: Mapping[str, Any],
    *,
    repo_root: Path,
    runtime_root: Path,
) -> None:
    if path.is_symlink():
        raise ValueError("receipt_path_reserved_or_collision")
    resolved = path.resolve()
    if _is_inside(resolved, repo_root):
        raise ValueError("receipt_path_inside_repo")
    canonical = (runtime_root / "live_canary_receipt.json").resolve()
    if _is_inside(resolved, runtime_root) and resolved != canonical:
        raise ValueError("receipt_path_reserved_or_collision")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{resolved.name}.", suffix=".tmp", dir=str(resolved.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, sort_keys=True, indent=2, ensure_ascii=True)
            handle.write("\n")
        os.replace(temporary, resolved)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _valid_json_mapping(path: Path, *, allowed_root: Path) -> bool:
    return bool(_read_json_mapping(path, allowed_root=allowed_root))


def _read_json_mapping(path: Path, *, allowed_root: Path) -> Mapping[str, Any]:
    try:
        with runtime_operation_lock(str(path) + ".operation"):
            payload = read_reddog_runtime_json_mapping(
                path,
                allowed_root=allowed_root,
            )
    except Exception:
        return {}
    return payload


def _is_unix_socket(path: Path) -> bool:
    try:
        return stat.S_ISSOCK(path.stat().st_mode)
    except OSError:
        return False


def _command_succeeds(argv: Sequence[str], cwd: Path) -> bool:
    """Run an audit-safe readiness command without returning its output."""

    try:
        completed = subprocess.run(
            list(argv),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def _check(name: str, passed: bool, failure_reason: str) -> LiveCanaryReadinessCheck:
    return LiveCanaryReadinessCheck(name=name, passed=bool(passed), reason="ok" if passed else failure_reason)


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def _text(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def build_reddog_resident_live_canary_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reddog-resident-live-canary",
        description="Assess or explicitly execute one highest-profile resident RedDog canary.",
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--receipt-path")
    parser.add_argument("--queue-item-id", default="")
    parser.add_argument("--max-rounds", type=int, default=8)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_reddog_resident_live_canary_parser().parse_args(list(argv) if argv is not None else None)
    receipt = run_reddog_resident_live_canary(
        repo_root=args.repo_root,
        runtime_root=args.runtime_root,
        receipt_path=args.receipt_path,
        execute=args.execute,
        confirmation=args.confirm,
        queue_item_id=args.queue_item_id,
        max_rounds=args.max_rounds,
    )
    print(json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0 if receipt.status in {LIVE_CANARY_READY, LIVE_CANARY_PROOF_COMPLETE} else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))


__all__ = [
    "LIVE_CANARY_BLOCKED",
    "LIVE_CANARY_CONFIRMATION",
    "LIVE_CANARY_EXECUTION_FAILED",
    "LIVE_CANARY_PROOF_COMPLETE",
    "LIVE_CANARY_PROOF_INCOMPLETE",
    "LIVE_CANARY_READY",
    "LiveCanaryReadinessCheck",
    "LiveCanaryReceipt",
    "build_reddog_resident_live_canary_parser",
    "main",
    "run_reddog_resident_live_canary",
]
