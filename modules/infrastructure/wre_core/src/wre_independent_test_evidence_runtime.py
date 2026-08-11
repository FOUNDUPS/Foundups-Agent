"""Bounded check execution for the independent WRE evidence producer."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from modules.infrastructure.wre_core.src.wre_test_differential_runtime import (
    produce_test_differential_evidence,
)

FAIL_REQUIRED_CHECKS = "FAIL_REQUIRED_CHECKS"
FAIL_CHECK_COMMAND_REJECTED = "FAIL_CHECK_COMMAND_REJECTED"
FAIL_CHECK_FAILED = "FAIL_CHECK_FAILED"
FAIL_RUNNER_EXCEPTION = "FAIL_RUNNER_EXCEPTION"
MAX_CHECKS = 8
MAX_ARGV = 24


@dataclass(frozen=True)
class IndependentTestEvidence:
    records: tuple[dict[str, Any], ...]
    command_records: tuple[dict[str, Any], ...]
    rejection_reasons: tuple[str, ...]
    differential_evidence: dict[str, Any]
    differential_capability: object | None = None


def execute_independent_test_evidence(
    request: Mapping[str, Any], *, runner: Any, operation_cwd: Path,
    worktree_path: Path, repo_root: Path, head_sha: str,
) -> IndependentTestEvidence:
    """Run ordinary checks and one optional verifier-owned pytest differential."""
    checks = request.get("required_checks")
    if not isinstance(checks, list) or not checks or len(checks) > MAX_CHECKS:
        return _result(reasons=[FAIL_REQUIRED_CHECKS])
    policy = request.get("test_impact_policy")
    differential_requested = isinstance(policy, Mapping) and bool(policy)
    records: list[dict[str, Any]] = []
    commands: list[dict[str, Any]] = []
    reasons: list[str] = []
    deferred_pytest = 0
    for check in checks:
        item = check if isinstance(check, Mapping) else {}
        argv = item.get("argv")
        if not _allowed_argv(argv):
            reasons.append(FAIL_CHECK_COMMAND_REJECTED)
            continue
        args = tuple(str(value) for value in argv)
        if differential_requested and _is_pytest(args):
            deferred_pytest += 1
            if list(_pytest_args(args)) != list(policy.get("selection_args", ())):
                reasons.append(FAIL_CHECK_COMMAND_REJECTED)
            continue
        _run_one(item, args, runner, operation_cwd, head_sha, records, commands, reasons)
    differential: dict[str, Any] = {}
    differential_capability: object | None = None
    if differential_requested:
        if deferred_pytest != 1 or reasons:
            reasons.append(FAIL_REQUIRED_CHECKS)
        else:
            produced = produce_test_differential_evidence(
                request, worktree_path=worktree_path, repo_root=repo_root
            )
            differential = produced.evidence
            differential_capability = produced.verification_capability
            reasons.extend(produced.rejection_reasons)
    return _result(
        records, commands, reasons, differential, differential_capability,
    )


def _run_one(
    check: Mapping[str, Any], argv: tuple[str, ...], runner: Any, cwd: Path,
    head_sha: str, records: list[dict[str, Any]], commands: list[dict[str, Any]],
    reasons: list[str],
) -> None:
    try:
        result = runner.run(argv, cwd=cwd, timeout_s=_timeout(check.get("timeout_s")))
    except Exception:
        reasons.append(FAIL_RUNNER_EXCEPTION)
        return
    commands.append(_command_record(str(check.get("name") or "required_check"), argv, result))
    conclusion = "success" if result.returncode == 0 and result.timed_out is False else "failure"
    records.append({
        "name": str(check.get("name") or argv[0]), "head_sha": head_sha,
        "conclusion": conclusion, "returncode": result.returncode,
        "timed_out": result.timed_out, "argv_digest": _digest(list(argv)),
        "stdout_digest": _digest(result.stdout), "stderr_digest": _digest(result.stderr),
        "duration_ms": result.duration_ms,
    })
    if conclusion != "success":
        reasons.append(FAIL_CHECK_FAILED)


def _allowed_argv(value: Any) -> bool:
    if not isinstance(value, list) or not value or len(value) > MAX_ARGV:
        return False
    argv = [str(item) for item in value]
    if any(not item or any(char in item for char in "\x00\n\r") for item in argv):
        return False
    first = argv[0].lower()
    if first in {"python", "python3", "py"}:
        return len(argv) >= 3 and argv[1] == "-m" and argv[2] in {"pytest", "ruff", "mypy"}
    return first in {"pytest", "ruff", "mypy"}


def _is_pytest(argv: Sequence[str]) -> bool:
    return argv[0].lower() == "pytest" or (
        len(argv) >= 3 and argv[0].lower() in {"python", "python3", "py"}
        and argv[1:3] == ("-m", "pytest")
    )


def _pytest_args(argv: Sequence[str]) -> tuple[str, ...]:
    return tuple(argv[3:] if argv[0].lower() in {"python", "python3", "py"} else argv[1:])


def _timeout(value: Any) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = 60
    return max(1, min(parsed, 3600))


def _command_record(name: str, argv: Sequence[str], result: Any) -> dict[str, Any]:
    return {
        "name": name, "argv_digest": _digest(list(argv)),
        "returncode": result.returncode, "stdout_digest": _digest(result.stdout),
        "stderr_digest": _digest(result.stderr), "duration_ms": result.duration_ms,
        "timed_out": result.timed_out, "stdout_truncated": result.stdout_truncated,
        "stderr_truncated": result.stderr_truncated,
    }


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _result(
    records: Sequence[dict[str, Any]] = (), commands: Sequence[dict[str, Any]] = (),
    reasons: Sequence[str] = (), differential: Mapping[str, Any] | None = None,
    capability: object | None = None,
) -> IndependentTestEvidence:
    return IndependentTestEvidence(
        tuple(records), tuple(commands), tuple(dict.fromkeys(reasons)),
        dict(differential or {}), capability,
    )


__all__ = ["IndependentTestEvidence", "execute_independent_test_evidence"]
