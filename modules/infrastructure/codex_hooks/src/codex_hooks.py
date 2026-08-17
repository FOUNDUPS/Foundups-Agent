#!/usr/bin/env python3
"""Deterministic FoundUps policy gates for Codex lifecycle hook events.

The process reads exactly one Codex hook event object from stdin and emits at
most one hook response object on stdout. It never reads a transcript or stores
prompt/tool contents.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class RepoContext:
    """Minimal repository identity used by lifecycle policy."""

    root: Path
    branch: str
    head: str
    worktree_kind: str


SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("google_api_key", re.compile(r"AIza[A-Za-z0-9_-]{30,}")),
    ("openai_api_key", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ("huggingface_token", re.compile(r"hf_[A-Za-z0-9]{20,}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("github_fine_grained_token", re.compile(r"github_pat_[A-Za-z0-9_]{22,}")),
    (
        "oauth_token_assignment",
        re.compile(r"(?:oauth|refresh)_token[\"']?\s*[:=]\s*[\"'][^\"']{10,}[\"']", re.IGNORECASE),
    ),
    ("bearer_token", re.compile(r"\bbearer\s+[A-Za-z0-9._-]{20,}", re.IGNORECASE)),
    (
        "secret_assignment",
        re.compile(
            r"\b[A-Z][A-Z0-9_]*(?:SECRET|TOKEN|API_KEY)\s*[:=]\s*[\"']?[^\s\"']{10,}",
            re.IGNORECASE,
        ),
    ),
    (
        "password_assignment",
        re.compile(r"\bpassword\s*[:=]\s*[\"'][^\"']{8,}[\"']", re.IGNORECASE),
    ),
)


_BROAD_DESTRUCTIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\brm\s+-rf\s+(?:/|~|\$HOME)(?:\s|$)", re.IGNORECASE),
    re.compile(r"\bRemove-Item\b[^\r\n]*\b-Recurse\b[^\r\n]*(?:\$HOME|~|[A-Za-z]:\\(?:\s|$))", re.IGNORECASE),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
    re.compile(r"\bgit\s+clean\s+-[^\s]*[xX][^\s]*\b", re.IGNORECASE),
)

_MAIN_GIT_MUTATIONS = re.compile(
    r"\bgit\s+(?:add|commit|push|merge|rebase|cherry-pick|reset|clean)\b",
    re.IGNORECASE,
)

_ENV_READ_COMMAND = re.compile(
    r"\b(?:Get-Content|Select-String|cat|type|more|findstr|rg)\b",
    re.IGNORECASE,
)

_ENV_PATH = re.compile(r"(?:^|[\\/\s'\"])(?:\.env)(?:[.\\/\s'\"]|$)", re.IGNORECASE)


def _run(
    args: Sequence[str],
    *,
    cwd: Path,
    timeout: int = 30,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=dict(env) if env is not None else None,
        check=False,
    )


def _git_value(
    cwd: Path,
    *args: str,
    runner: CommandRunner = _run,
) -> str:
    result = runner(("git", *args), cwd=cwd, timeout=15)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def resolve_repo_context(
    cwd: str | Path,
    *,
    runner: CommandRunner = _run,
) -> RepoContext | None:
    """Resolve repository facts without mutating Git state."""

    start = Path(cwd).resolve()
    root_text = _git_value(start, "rev-parse", "--show-toplevel", runner=runner)
    if not root_text:
        return None
    root = Path(root_text).resolve()
    branch = _git_value(root, "branch", "--show-current", runner=runner) or "DETACHED"
    head = _git_value(root, "rev-parse", "--short=12", "HEAD", runner=runner) or "UNKNOWN"
    common_text = _git_value(
        root,
        "rev-parse",
        "--path-format=absolute",
        "--git-common-dir",
        runner=runner,
    )
    worktree_kind = "unknown"
    if common_text:
        common_parent = Path(common_text).resolve().parent
        worktree_kind = "primary" if common_parent == root else "linked"
    return RepoContext(root=root, branch=branch, head=head, worktree_kind=worktree_kind)


def _session_stop(reason: str) -> dict[str, Any]:
    return {
        "continue": False,
        "stopReason": reason,
        "systemMessage": reason,
    }


def _pretool_deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def scan_prompt_for_secrets(prompt: str) -> list[str]:
    """Return secret classifications only; never return matching values."""

    return [name for name, pattern in SECRET_PATTERNS if pattern.search(prompt)]


def handle_user_prompt_submit(event: Mapping[str, Any]) -> dict[str, Any] | None:
    prompt = event.get("prompt", "")
    if not isinstance(prompt, str):
        return {
            "decision": "block",
            "reason": "Prompt rejected because its wire value is not text.",
        }
    classifications = scan_prompt_for_secrets(prompt)
    if not classifications:
        return None
    labels = ", ".join(sorted(classifications))
    return {
        "decision": "block",
        "reason": f"Potential secret detected ({labels}). Redact the value and submit again.",
    }


def _patch_targets_env(command: str) -> bool:
    target_pattern = re.compile(
        r"^\*\*\*\s+(?:Add|Update|Delete)\s+File:\s+(?:.*[\\/])?\.env(?:[.\\/]|$)",
        re.IGNORECASE | re.MULTILINE,
    )
    return bool(target_pattern.search(command))


def _bash_reads_env(command: str) -> bool:
    without_exclusions = re.sub(r"![^\s'\"]*\.env[^\s'\"]*", "", command, flags=re.IGNORECASE)
    return bool(_ENV_READ_COMMAND.search(without_exclusions) and _ENV_PATH.search(without_exclusions))


def tool_denial_reason(
    event: Mapping[str, Any],
    context: RepoContext | None,
) -> str | None:
    """Return a deterministic denial reason for non-negotiable policy breaches."""

    tool_name = str(event.get("tool_name", ""))
    tool_input = event.get("tool_input", {})
    if not isinstance(tool_input, Mapping):
        return "Tool call rejected because its input is not an object."
    command = tool_input.get("command", "")
    if not isinstance(command, str):
        return "Tool call rejected because its command is not text."

    is_edit = tool_name in {"apply_patch", "Edit", "Write"}
    if is_edit and _patch_targets_env(command):
        return "Edits to credential environment files are forbidden."
    if tool_name == "Bash" and _bash_reads_env(command):
        return "Reading credential environment-file contents is forbidden."

    if any(pattern.search(command) for pattern in _BROAD_DESTRUCTIVE_PATTERNS):
        return "Broad destructive filesystem or Git operations are forbidden."
    if re.search(r"\bgit\s+push\b[^\r\n]*(?:--force(?:-with-lease)?|\s-f(?:\s|$))", command, re.IGNORECASE):
        return "Force pushes are disabled for FoundUps operations."
    if re.search(r"\bpython(?:3|\.exe)?\b[^\r\n]*\bholo_index\.py\b[^\r\n]*--(?:index|search)", command, re.IGNORECASE):
        return "Use the governed HoloIndex owner-query path; raw search/reindex is forbidden."

    if context is None:
        if is_edit:
            return "Repository identity could not be resolved; file edits are fail-closed."
        return None
    if context.branch in {"main", "master", "DETACHED"}:
        if is_edit:
            return "Repository edits require a named isolated branch/worktree, not main or detached HEAD."
        if tool_name == "Bash" and _MAIN_GIT_MUTATIONS.search(command):
            return "Git mutations require a named isolated branch/worktree, not main or detached HEAD."
    return None


def handle_pre_tool_use(
    event: Mapping[str, Any],
    *,
    runner: CommandRunner = _run,
) -> dict[str, Any] | None:
    cwd = event.get("cwd", os.getcwd())
    context = resolve_repo_context(str(cwd), runner=runner)
    reason = tool_denial_reason(event, context)
    return _pretool_deny(reason) if reason else None


def _parse_json_line(output: str) -> dict[str, Any] | None:
    for line in reversed(output.splitlines()):
        candidate = line.strip()
        if not candidate.startswith("{"):
            continue
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def handle_session_start(
    event: Mapping[str, Any],
    *,
    runner: CommandRunner = _run,
) -> dict[str, Any]:
    cwd = event.get("cwd", os.getcwd())
    context = resolve_repo_context(str(cwd), runner=runner)
    if context is None:
        return _session_stop("FoundUps WSP_00 gate could not resolve the repository root.")

    awakening = context.root / "WSP_agentic" / "scripts" / "functional_0102_awakening_v2.py"
    tracker = (
        context.root
        / "modules"
        / "infrastructure"
        / "monitoring"
        / "src"
        / "wsp_00_zen_state_tracker.py"
    )
    if not awakening.is_file() or not tracker.is_file():
        return _session_stop("FoundUps WSP_00 gate artifacts are missing from this checkout.")

    child_env = os.environ.copy()
    child_env.pop("WSP_AWAKENING_WRITE_TRACKED", None)
    awaken_result = runner(
        (sys.executable, "-u", str(awakening)),
        cwd=context.root,
        timeout=120,
        env=child_env,
    )
    if awaken_result.returncode != 0:
        return _session_stop("FoundUps WSP_00 awakening failed; repository work is halted.")

    tracker_result = runner(
        (sys.executable, str(tracker), "--check", "--strict", "--json"),
        cwd=context.root,
        timeout=30,
        env=child_env,
    )
    gate = _parse_json_line(tracker_result.stdout)
    if tracker_result.returncode != 0 or not gate or not gate.get("is_zen_compliant"):
        return _session_stop("FoundUps strict WSP_00 compliance gate failed; repository work is halted.")

    source = str(event.get("source", "unknown"))
    additional_context = (
        "FoundUps lifecycle gate passed. "
        f"WSP_00 is_zen_compliant=true; session_source={source}; "
        f"branch={context.branch}; head={context.head}; worktree={context.worktree_kind}. "
        "Apply WSP_97 retrieval and evidence gates before edits. "
        "Never expose credential files or mutate shared main."
    )
    return {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional_context,
        },
    }


def handle_stop(
    event: Mapping[str, Any],
    *,
    runner: CommandRunner = _run,
) -> dict[str, Any] | None:
    if bool(event.get("stop_hook_active")):
        return None
    cwd = event.get("cwd", os.getcwd())
    context = resolve_repo_context(str(cwd), runner=runner)
    if context is None:
        return None
    for args in (("git", "diff", "--check"), ("git", "diff", "--cached", "--check")):
        result = runner(args, cwd=context.root, timeout=30)
        if result.returncode != 0:
            return {
                "decision": "block",
                "reason": "Completion gate failed: resolve git diff --check errors, then stop again.",
            }
    return None


def dispatch_hook(
    event: Mapping[str, Any],
    *,
    runner: CommandRunner = _run,
) -> dict[str, Any] | None:
    """Dispatch one Codex lifecycle event to its deterministic handler."""

    event_name = event.get("hook_event_name")
    if event_name == "SessionStart":
        return handle_session_start(event, runner=runner)
    if event_name == "UserPromptSubmit":
        return handle_user_prompt_submit(event)
    if event_name == "PreToolUse":
        return handle_pre_tool_use(event, runner=runner)
    if event_name == "Stop":
        return handle_stop(event, runner=runner)
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Invalid Codex hook input: {exc}", file=sys.stderr)
        return 1
    if not isinstance(event, dict):
        print("Invalid Codex hook input: expected a JSON object", file=sys.stderr)
        return 1
    response = dispatch_hook(event)
    if response is not None:
        print(json.dumps(response, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
