"""Typed, statically-allowlisted, shell=False auto-fix executor.

SECURITY PROPERTY: "config selects, never injects."
Skill config may only SELECT which allowlisted ``FixAction`` runs (with validated,
discrete params). It can NEVER supply a command string that reaches a shell:
- there is no ``shell=True`` anywhere on this path;
- argv is built from a code-defined static allowlist (``_ALLOWLIST``); params are
  inserted as discrete, enum-validated argv elements, never string-concatenated;
- a command-shaped config field (``fix_command`` / ``fix_commands``) is REJECTED,
  not silently ignored (``assert_no_command_fields``);
- an unknown / unmapped ``fix_action`` is REJECTED, never executed.

Autonomy is preserved: allowlisted fixes still run end-to-end without any human/012
runtime approval gate. The boundary is code-enforced (typed allowlist + shell=False),
not a human in the loop.

Predecessor: PR #767 AI_OVERSEER_AUTOFIX_SHELL_EXEC_GOVERNANCE_AUDIT.
Remediation: AI_OVERSEER_AUTOFIX_SHELL_EXEC_REMEDIATION_PHASE1.
"""

from __future__ import annotations

import enum
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Repo root: .../modules/ai_intelligence/ai_overseer/src/autofix_executor.py -> parents[4]
REPO_ROOT = Path(__file__).resolve().parents[4]

# Default subprocess timeouts (seconds). Discrete, code-defined; never config-sourced.
_DEFAULT_TIMEOUT = 300
_STDIO_TAIL = 500


class FixAction(enum.Enum):
    """The ONLY auto-fix actions that may run a subprocess.

    Derived from the actual live skill config
    (modules/communication/livechat/skillz/youtube_daemon_monitor.json) on
    origin/main 0b55b5cdd. ``install_missing_library`` is intentionally ABSENT:
    no live config uses it (latent), so it is rejected rather than implemented.
    """

    REAUTHORIZE = "run_reauthorization_script"
    ROTATION_RECOVERY = "trigger_next_rotation"


# Validated param enums (discrete allowlists; reject anything else).
_ALLOWED_BROWSERS = ("chrome", "edge")
_ALLOWED_OPERATIONS = ("comments", "shorts")

# Config fields that must never carry an executable command string for auto-fix.
_FORBIDDEN_CONFIG_FIELDS = ("fix_command", "fix_commands")

# WSP_97 evidence safety: redact credential-adjacent material from any captured output
# (stdout/stderr/error text) BEFORE it is stored in an EvidencePacket. Auto-fix actions
# are OAuth-adjacent, so raw output could contain auth URLs, tokens, codes, or secrets.
_REDACTION = "[REDACTED]"
_REDACT_SUBS = (
    # sensitive key followed by a value:  key=val | key: val | "key": "val"
    (
        re.compile(
            r"(\b(?:access_token|refresh_token|id_token|client_secret|client_id|"
            r"user_code|authorization_code|password|passwd|api_key|apikey|token)\b"
            r"\s*[\"']?\s*[:=]\s*[\"']?)([^\s&\"'}]+)",
            re.IGNORECASE,
        ),
        r"\1" + _REDACTION,
    ),
    # OAuth URL query params:  ?code=... &access_token=... &refresh_token=...
    (
        re.compile(
            r"([?&](?:code|access_token|refresh_token|id_token|token)=)[^\s&\"'}]+",
            re.IGNORECASE,
        ),
        r"\1" + _REDACTION,
    ),
    # env-style KEY=VALUE for sensitive suffixes
    (
        re.compile(r"(\b[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|APIKEY)\s*[:=]\s*)(\S+)"),
        r"\1" + _REDACTION,
    ),
    # bearer tokens
    (re.compile(r"(\b[Bb]earer\s+)[A-Za-z0-9._\-]+"), r"\1" + _REDACTION),
    # known token shapes (redact the value even out of key=value context)
    (re.compile(r"\bya29\.[0-9A-Za-z._\-]+"), _REDACTION),       # Google OAuth access token
    (re.compile(r"\b1//[0-9A-Za-z._\-]{10,}"), _REDACTION),      # Google OAuth refresh token
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{10,}"), _REDACTION),      # Google API key
    (re.compile(r"\bsk-[A-Za-z0-9]{16,}"), _REDACTION),          # OpenAI-style key
    (re.compile(r"\bgh[posru]_[A-Za-z0-9]{16,}"), _REDACTION),   # GitHub token
)


def redact_sensitive(text: Optional[str]) -> str:
    """Redact credential-adjacent material (tokens, OAuth codes/URLs, secrets) from text."""
    if not text:
        return ""
    out = str(text)
    for pattern, repl in _REDACT_SUBS:
        out = pattern.sub(repl, out)
    return out


class FixActionRejected(Exception):
    """Raised when an action/param/config field is not allowlisted. Never executes."""


def _reauthorize_argv(params: Dict[str, Any]) -> List[str]:
    """OAuth reauth: a FIXED script (live config uses only reauthorize_set1.py).

    No params are accepted; the script path is code-defined, never config-sourced.
    """
    script = (
        REPO_ROOT
        / "modules"
        / "platform_integration"
        / "youtube_auth"
        / "scripts"
        / "reauthorize_set1.py"
    )
    return [sys.executable, str(script)]


def _rotation_argv(params: Dict[str, Any]) -> List[str]:
    """Rotation recovery: fixed argv vector with enum-validated browser/operation.

    Params come from runtime breadcrumb metadata, NOT from a command string.
    """
    browser = params.get("browser", "edge")
    operation = params.get("operation", "comments")
    if browser not in _ALLOWED_BROWSERS:
        raise FixActionRejected(
            f"invalid browser {browser!r}; allowed={_ALLOWED_BROWSERS}"
        )
    if operation not in _ALLOWED_OPERATIONS:
        raise FixActionRejected(
            f"invalid operation {operation!r}; allowed={_ALLOWED_OPERATIONS}"
        )
    return [
        sys.executable,
        "-m",
        "modules.communication.livechat.src.rotation_supervisor",
        "--browser",
        browser,
        "--operation",
        operation,
        "--timeout",
        "300",
    ]


# Static, code-defined allowlist: FixAction -> argv builder (returns list[str]).
_ALLOWLIST: Dict[FixAction, Callable[[Dict[str, Any]], List[str]]] = {
    FixAction.REAUTHORIZE: _reauthorize_argv,
    FixAction.ROTATION_RECOVERY: _rotation_argv,
}


@dataclass
class EvidencePacket:
    """Structured, SAFE post-execution evidence. Never stores secrets/tokens/env."""

    action: str
    decision: str  # "ALLOWED" | "REJECTED"
    argv_safe: List[str] = field(default_factory=list)
    cwd: str = ""
    timeout: int = 0
    returncode: Optional[int] = None
    pid: Optional[int] = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    timestamp: str = ""
    success: bool = False
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "decision": self.decision,
            "argv": list(self.argv_safe),
            "cwd": self.cwd,
            "timeout": self.timeout,
            "returncode": self.returncode,
            "pid": self.pid,
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
            "timestamp": self.timestamp,
            "success": self.success,
            "reason": self.reason,
        }


def resolve_fix_action(fix_action: Optional[str]) -> FixAction:
    """Map a config-supplied fix_action string to an allowlisted FixAction, or REJECT."""
    if not fix_action:
        raise FixActionRejected("missing fix_action")
    for action in FixAction:
        if action.value == fix_action:
            return action
    raise FixActionRejected(f"unmapped fix_action {fix_action!r}")


def assert_no_command_fields(config: Optional[Dict[str, Any]]) -> None:
    """REJECT (not ignore) command-shaped config fields for auto-fix actions."""
    present = [f for f in _FORBIDDEN_CONFIG_FIELDS if f in (config or {})]
    if present:
        raise FixActionRejected(
            f"command-shaped config fields are forbidden for auto-fix: {present}"
        )


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def execute_fix(
    fix_action: Optional[str],
    config: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    *,
    wait: bool = True,
    cwd: Optional[Path] = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> EvidencePacket:
    """Execute an allowlisted auto-fix with shell=False, or return a REJECTED packet.

    Args:
        fix_action: config-supplied action selector (string).
        config: the skill config dict (scanned for forbidden command fields).
        params: validated discrete params (e.g. {"browser": "edge", "operation": "comments"}).
        wait: True -> subprocess.run (blocking); False -> subprocess.Popen (non-blocking spawn).
        cwd: working directory (defaults to repo root).
        timeout: blocking-run timeout seconds.

    Returns:
        EvidencePacket. On any rejection or error, decision="REJECTED"/success=False and
        NOTHING is executed.
    """
    cwd_str = str(cwd or REPO_ROOT)

    # --- Static boundary: reject command-shaped config + unmapped action BEFORE exec ---
    try:
        assert_no_command_fields(config)
        action = resolve_fix_action(fix_action)
        argv = _ALLOWLIST[action](params or {})
    except FixActionRejected as exc:
        return EvidencePacket(
            action=str(fix_action),
            decision="REJECTED",
            cwd=cwd_str,
            timeout=timeout,
            timestamp=_now_iso(),
            success=False,
            reason=str(exc),
        )

    # --- shell=False execution (the only execution path) ---
    try:
        if wait:
            proc = subprocess.run(
                argv,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd_str,
            )
            return EvidencePacket(
                action=action.value,
                decision="ALLOWED",
                argv_safe=list(argv),
                cwd=cwd_str,
                timeout=timeout,
                returncode=proc.returncode,
                # Redact BEFORE truncation so no token straddles the tail boundary.
                stdout_tail=redact_sensitive(proc.stdout)[-_STDIO_TAIL:],
                stderr_tail=redact_sensitive(proc.stderr)[-_STDIO_TAIL:],
                timestamp=_now_iso(),
                success=proc.returncode == 0,
                reason="completed",
            )
        proc_p = subprocess.Popen(  # noqa: S603 - argv list, shell=False, allowlisted
            argv,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd_str,
        )
        return EvidencePacket(
            action=action.value,
            decision="ALLOWED",
            argv_safe=list(argv),
            cwd=cwd_str,
            timeout=timeout,
            pid=proc_p.pid,
            timestamp=_now_iso(),
            success=True,
            reason="spawned",
        )
    except Exception as exc:  # subprocess error (timeout, OSError, ...)
        return EvidencePacket(
            action=action.value,
            decision="ALLOWED",
            argv_safe=list(argv),
            cwd=cwd_str,
            timeout=timeout,
            timestamp=_now_iso(),
            success=False,
            reason=redact_sensitive(f"execution_error: {type(exc).__name__}: {exc}"),
        )
