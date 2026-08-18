"""Independent failure reproduction and baseline receipt sealing.

Governed by WSP_00, WSP_50, WSP_97 (Issue #1522).

Invariant:
A failure observation does NOT grant mutation authority.
Require independent reproduction before repair admission.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Sequence

from .repair_operation_contract import (
    BaselineReceipt,
    NonReproducibleClassification,
)


def _get_git_head_sha(repo_root: Path) -> str:
    """Read current git HEAD SHA deterministically."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
            timeout=5.0,
        )
        return str(res.stdout).strip().lower()
    except Exception:
        return "0000000000000000000000000000000000000000"


def _get_environment_digest(repo_root: Path) -> str:
    """Compute environment and config digest."""
    import hashlib
    raw = f"py:{os.name}:{repo_root}"
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def attempt_failure_reproduction(
    *,
    repo_root: Path,
    failure_id: str,
    reproduction_command: str | Sequence[str],
    failing_invariant: str,
    relevant_tests: Sequence[str] = (),
    timeout_seconds: float = 60.0,
    authority_declaration: str = "TIER_1_INTERNAL_MODULE",
) -> tuple[bool, BaselineReceipt | None, NonReproducibleClassification | None, str]:
    """
    Attempt to independently reproduce a reported failure in a clean read-only manner.

    Returns:
        (reproduced, baseline_receipt, non_repro_classification, diagnostic_reason)
    """
    cmd = (
        reproduction_command
        if isinstance(reproduction_command, (list, tuple))
        else reproduction_command.split()
    )

    try:
        res = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=isinstance(reproduction_command, str) and (" " in reproduction_command and os.name == "nt"),
        )
    except subprocess.TimeoutExpired:
        return (
            False,
            None,
            NonReproducibleClassification.TRANSIENT,
            f"Reproduction command timed out after {timeout_seconds}s",
        )
    except Exception as exc:
        return (
            False,
            None,
            NonReproducibleClassification.ENVIRONMENT_SKEW,
            f"Reproduction command execution error: {exc}",
        )

    stdout = str(res.stdout or "")
    stderr = str(res.stderr or "")
    combined_log = f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    # If the command succeeded (exit code 0), the failure was NOT reproduced!
    if res.returncode == 0:
        return (
            False,
            None,
            NonReproducibleClassification.ALREADY_RESOLVED,
            "Reproduction command exited with code 0 (expected failure)",
        )

    # If an expected failing invariant was declared, check that it appears in output
    if failing_invariant and failing_invariant not in combined_log:
        return (
            False,
            None,
            NonReproducibleClassification.OBSERVER_DEFECT,
            f"Command failed (exit {res.returncode}) but did not match failing invariant: {failing_invariant}",
        )

    # Failure reproduced and authenticated!
    head_sha = _get_git_head_sha(repo_root)
    env_digest = _get_environment_digest(repo_root)

    cmd_str = (
        reproduction_command
        if isinstance(reproduction_command, str)
        else " ".join(reproduction_command)
    )

    receipt = BaselineReceipt.create(
        failure_id=failure_id,
        failing_invariant=failing_invariant,
        head_sha=head_sha,
        environment_digest=env_digest,
        reproduction_command=cmd_str,
        exit_code=res.returncode,
        bounded_log_evidence=combined_log[:16384],
        relevant_tests=relevant_tests,
        authority_declaration=authority_declaration,
    )

    return (True, receipt, None, "Failure authenticated and reproduced successfully")
