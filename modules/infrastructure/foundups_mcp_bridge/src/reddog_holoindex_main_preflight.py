"""Narrow main.py policy seams for the RedDog HoloIndex owner boundary."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

from .reddog_holoindex_maintenance_handshake import (
    ensure_reddog_holoindex_operational,
)


PREFLIGHT_FAILED_ERROR = "HOLOINDEX_OPERATIONAL_PREFLIGHT_FAILED"


def _result(
    *,
    repo_root: Path,
    maintenance_requested: bool,
):
    if maintenance_requested:
        return ensure_reddog_holoindex_operational(
            repo_root=repo_root,
            requested=True,
            auto_maintenance=True,
        )
    return ensure_reddog_holoindex_operational(
        repo_root=repo_root,
        requested=True,
        auto_maintenance=False,
    )


def run_interactive_owner_preflight(
    *,
    repo_root: Path,
    maintenance_requested: bool,
    enforced: bool,
) -> bool:
    """Run the interactive owner policy with explicit fail-closed semantics."""
    required = bool(enforced or maintenance_requested)
    try:
        result = _result(
            repo_root=repo_root,
            maintenance_requested=maintenance_requested,
        )
        ready, status, error = result.ready, result.status, result.error
    except Exception:
        ready, status, error = False, "FAILED", PREFLIGHT_FAILED_ERROR
    label = "PASS" if ready else ("FAIL" if required else "WARN")
    print(
        f"[REDDOG-HOLO-OWNER] preflight={label} "
        f"status={status} error={error or '(none)'}"
    )
    return bool(ready or not required)


def _headless_requested(environ: Mapping[str, str]) -> bool:
    request_flags = (
        "OPENCLAW_AUTO_TASKS_ENABLED",
        "OPENCLAW_MAINTENANCE_ENABLED",
        "REDDOG_READONLY_AUDIT_SWARM_ENQUEUE_ENABLED",
        "REDDOG_READONLY_AUDIT_RESEARCH_DECISION_E2E_ENABLED",
    )
    return any(str(environ.get(name, "0")) != "0" for name in request_flags)


def run_headless_owner_preflight(
    repo_root: Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Require the exact-HEAD owner before autonomous headless work starts."""
    env = os.environ if environ is None else environ
    if not _headless_requested(env):
        return True
    try:
        result = ensure_reddog_holoindex_operational(
            repo_root=repo_root,
            requested=True,
            environ=env,
        )
    except Exception:
        print(
            "[HEADLESS-HOLO] preflight=FAIL "
            f"status=FAILED error={PREFLIGHT_FAILED_ERROR}"
        )
        return False
    label = "PASS" if result.ready else "FAIL"
    print(
        f"[HEADLESS-HOLO] preflight={label} status={result.status} "
        f"refreshed={result.refreshed} error={result.error or '(none)'}"
    )
    return bool(result.ready)


__all__ = [
    "PREFLIGHT_FAILED_ERROR",
    "run_headless_owner_preflight",
    "run_interactive_owner_preflight",
]
