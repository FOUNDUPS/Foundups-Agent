"""
Per-set OAuth browser executable resolution (WSP 84 single source of truth).

The OAuth consent flow must open a SPECIFIC browser per credential set so the
operator lands in the right Google profile:

    - Set 1  -> Chrome (UnDaoDu / Move2Japan account)
    - Set 10 -> Edge   (FoundUps / antifaFM account)

Historically the browser executable path was hardcoded inline in
youtube_auth.py (one literal per browser, no env override, no 32/64-bit
fallback), while authorize_set1.py / authorize_set10.py used a richer
candidate order (env var, then 64-bit, then x86). That duplication drifted:
the inline Set 10 path pointed at the x86 Edge location only.

This module centralizes the candidate ordering so there is ONE place that
decides which executable to launch. The order EXACTLY mirrors the authorize
scripts:

    Set 1  (Chrome): CHROME_PATH env, 64-bit Chrome, x86 Chrome
    Set 10 (Edge):   EDGE_PATH   env, 64-bit Edge,   x86 Edge

Import-light by design: only `os` at module load. The dependency on
oauth_health.reauth_command_for is imported lazily inside the error path to
avoid any import-cycle risk.
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

# Candidate executable paths per credential set, in resolution order.
# These MUST mirror authorize_set1.py / authorize_set10.py exactly.
# The env-var slot is represented by its variable NAME; it is resolved at
# call time so tests and operators can override via the environment.
_CHROME_CANDIDATES = (
    ("env", "CHROME_PATH"),
    ("literal", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    ("literal", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
)

_EDGE_CANDIDATES = (
    ("env", "EDGE_PATH"),
    ("literal", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ("literal", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
)

# set_id -> (browser_name, candidate tuple)
_SET_BROWSER = {
    1: ("chrome", _CHROME_CANDIDATES),
    10: ("edge", _EDGE_CANDIDATES),
}


class BrowserNotFoundError(Exception):
    """
    Raised when no browser executable can be resolved for a credential set.

    Carries enough context for an operator to act:
        set_id          -- the credential set we tried to resolve a browser for
        attempted_paths -- the concrete candidate paths checked (in order)
        operator_action -- the exact reauth command to run (from oauth_health),
                           or a generic hint for unknown sets
    """

    def __init__(
        self,
        set_id: int,
        attempted_paths: List[str],
        operator_action: str,
        message: Optional[str] = None,
    ) -> None:
        self.set_id = set_id
        self.attempted_paths = attempted_paths
        self.operator_action = operator_action
        if message is None:
            message = (
                f"No browser executable found for credential set {set_id}. "
                f"Attempted: {attempted_paths}. Operator action: {operator_action}"
            )
        super().__init__(message)


def _operator_action_for(set_id: int) -> str:
    """Lazy import of oauth_health to avoid import cycles at module load."""
    from modules.platform_integration.youtube_auth.src.oauth_health import (
        reauth_command_for,
    )

    return reauth_command_for(set_id)


def _resolve_candidates(candidates) -> Tuple[Optional[str], List[str]]:
    """
    Walk candidate specs in order, returning (first_existing_path, attempted).

    `attempted` lists the concrete paths we actually checked (env vars resolved
    to their value, unset env vars skipped) so the error message is truthful.
    """
    attempted: List[str] = []
    for kind, value in candidates:
        if kind == "env":
            path = os.getenv(value)
            if not path:
                continue
        else:
            path = value
        attempted.append(path)
        if os.path.exists(path):
            return path, attempted
    return None, attempted


def resolve_browser_for_set(set_id: int) -> Tuple[str, str]:
    """
    Resolve (browser_name, executable_path) for an OAuth credential set.

    Args:
        set_id: credential set id (1 -> Chrome, 10 -> Edge).

    Returns:
        (browser_name, executable_path) where executable_path is the first
        candidate that os.path.exists().

    Raises:
        BrowserNotFoundError: if the set is unknown, or no candidate path
            exists on this machine. The exception carries the operator_action
            (reauth command) so callers can log it and operators can act.
    """
    entry = _SET_BROWSER.get(set_id)
    if entry is None:
        raise BrowserNotFoundError(
            set_id=set_id,
            attempted_paths=[],
            operator_action=_operator_action_for(set_id),
            message=(
                f"Unknown credential set {set_id}: no browser mapping defined "
                f"(known sets: {sorted(_SET_BROWSER)})."
            ),
        )

    browser_name, candidates = entry
    path, attempted = _resolve_candidates(candidates)
    if path is None:
        raise BrowserNotFoundError(
            set_id=set_id,
            attempted_paths=attempted,
            operator_action=_operator_action_for(set_id),
        )
    return browser_name, path
