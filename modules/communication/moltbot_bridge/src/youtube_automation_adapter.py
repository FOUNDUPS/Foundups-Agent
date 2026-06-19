"""
YouTube automation adapter for OpenClaw/IronClaw AUTOMATION + SCHEDULE intents.

Command format (strict):
  youtube action <action> key=value key2="value 2"
  yt action <action> key=value

Supported actions:
  comments          -> like/heart/reply runner (YouTube Studio comments)
  indexing          -> video indexer CLI
  scheduling        -> shorts scheduler CLI
  schedule_priority -> what_should_i_schedule SKILLz (read-only channel need ranking)

Examples:
  youtube action comments channel=move2japan max_comments=3 like=true heart=true reply=false
  youtube action indexing channel=undaodu batch_size=5
  youtube action scheduling channel=foundups max_videos=3 dry_run=true
  youtube action schedule_priority upcoming_days=7
"""

from __future__ import annotations

import asyncio
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


SUPPORTED_ACTIONS = {"comments", "indexing", "scheduling", "schedule_priority"}

ACTION_ALIASES = {
    "comment": "comments",
    "engage_comments": "comments",
    "youtube_comments": "comments",
    "index": "indexing",
    "video_indexing": "indexing",
    "schedule": "scheduling",
    "scheduler": "scheduling",
    "shorts_scheduler": "scheduling",
    # what_should_i_schedule SKILLz: read-only channel scheduling-priority ranking
    "what_should_i_schedule": "schedule_priority",
    "schedule_next": "schedule_priority",
    "scheduling_priority": "schedule_priority",
}

# Repo root: modules/communication/moltbot_bridge/src -> parents[4]
REPO_ROOT = Path(__file__).resolve().parents[4]


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_param(params: Dict[str, str], key: str, default: int) -> int:
    raw = params.get(key)
    if raw is None:
        return default
    try:
        return int(str(raw).strip())
    except Exception:
        return default


def _parse_action_command(message: str) -> Optional[Tuple[str, Dict[str, str]]]:
    text = (message or "").strip()
    if not text:
        return None

    lowered = text.lower()
    prefix = None
    if lowered.startswith("youtube action "):
        prefix = "youtube action "
    elif lowered.startswith("yt action "):
        prefix = "yt action "
    if not prefix:
        return None

    remainder = text[len(prefix) :].strip()
    if not remainder:
        return None

    parts = shlex.split(remainder)
    if not parts:
        return None

    raw_action = parts[0].strip().lower()
    action = ACTION_ALIASES.get(raw_action, raw_action)
    if action not in SUPPORTED_ACTIONS:
        return action, {}

    params: Dict[str, str] = {}
    for token in parts[1:]:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if key:
            params[key] = value
    return action, params


def _extract_json_tail(stdout_text: str) -> Optional[Dict[str, Any]]:
    for line in reversed((stdout_text or "").splitlines()):
        line = line.strip()
        if not line:
            continue
        if line.startswith("{") and line.endswith("}"):
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                continue
    return None


def _run_subprocess(
    cmd: list[str],
    timeout_s: int,
) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "success": False,
            "error": f"timeout after {timeout_s}s",
            "command": cmd,
            "stdout_tail": (exc.stdout or "")[-1000:],
            "stderr_tail": (exc.stderr or "")[-1000:],
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {"success": False, "error": str(exc), "command": cmd}

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""

    return {
        "success": completed.returncode == 0,
        "returncode": completed.returncode,
        "command": cmd,
        "stdout_tail": "\n".join(stdout.splitlines()[-40:]),
        "stderr_tail": "\n".join(stderr.splitlines()[-40:]),
    }


def _build_comments_command(params: Dict[str, str]) -> list[str]:
    channel = params.get("channel", "move2japan")
    max_comments = _int_param(params, "max_comments", 3)
    browser_port = _int_param(params, "browser_port", 9222)

    do_like = _truthy(params.get("like", "true"))
    do_heart = _truthy(params.get("heart", "true"))
    do_reply = _truthy(params.get("reply", "false"))
    use_intelligent_reply = _truthy(params.get("intelligent_reply", "false"))
    dry_run = _truthy(params.get("dry_run", "false"))

    if dry_run:
        do_like = False
        do_heart = False
        do_reply = False

    cmd = [
        sys.executable,
        "-m",
        "modules.communication.video_comments.skillz.tars_like_heart_reply.run_skill",
        "--channel",
        channel,
        "--max-comments",
        str(max_comments),
        "--browser-port",
        str(browser_port),
        "--json-output",
    ]

    profile = params.get("profile", "").strip()
    if profile:
        cmd.extend(["--profile", profile])

    video_id = params.get("video_id", "").strip()
    if video_id:
        cmd.extend(["--video", video_id])

    reply_text = params.get("reply_text", "").strip()
    if reply_text:
        cmd.extend(["--reply-text", reply_text])

    if not do_like:
        cmd.append("--no-like")
    if not do_heart:
        cmd.append("--no-heart")
    if not do_reply:
        cmd.append("--no-reply")
    if not use_intelligent_reply:
        cmd.append("--no-intelligent-reply")

    if _truthy(params.get("dom_only", "false")):
        cmd.append("--dom-only")
    if _truthy(params.get("no_refresh", "false")):
        cmd.append("--no-refresh")
    if _truthy(params.get("debug_tags", "false")):
        cmd.append("--debug-tags")

    return cmd


def _build_indexing_command(params: Dict[str, str]) -> list[str]:
    cmd = [sys.executable, "-m", "modules.ai_intelligence.video_indexer.cli"]

    if _truthy(params.get("status", "false")):
        cmd.append("--status")
        return cmd

    channel = params.get("channel", "").strip()
    if channel:
        cmd.extend(["--channel", channel])

    video_id = params.get("video_id", "").strip()
    if video_id:
        cmd.extend(["--video-id", video_id])

    batch_size = _int_param(params, "batch_size", 10)
    cmd.extend(["--batch-size", str(batch_size)])

    if _truthy(params.get("reindex", "false")):
        cmd.append("--reindex")
    if _truthy(params.get("skip_holoindex", "false")):
        cmd.append("--skip-holoindex")
    if _truthy(params.get("list", "false")):
        cmd.append("--list")
    if _truthy(params.get("verbose", "false")):
        cmd.append("--verbose")

    return cmd


def _build_scheduling_command(params: Dict[str, str]) -> list[str]:
    cmd = [sys.executable, "-m", "modules.platform_integration.youtube_shorts_scheduler.cli"]

    if _truthy(params.get("list_channels", "false")):
        cmd.append("--list-channels")
        return cmd

    channel = params.get("channel", "").strip()
    if channel:
        cmd.extend(["--channel", channel])

    max_videos = _int_param(params, "max_videos", 5)
    cmd.extend(["--max-videos", str(max_videos)])

    browser = params.get("browser", "").strip().lower()
    if browser in {"chrome", "edge"}:
        cmd.extend(["--browser", browser])

    if _truthy(params.get("dry_run", "false")):
        cmd.append("--dry-run")
    if _truthy(params.get("verbose", "false")):
        cmd.append("--verbose")

    return cmd


def _build_schedule_priority_command(params: Dict[str, str]) -> list[str]:
    """Build the read-only what_should_i_schedule SKILLz invocation.

    Agent/DAE-invoked channel scheduling-priority ranking. No browser, no mutation.
    """
    cmd = [
        sys.executable,
        "-m",
        "modules.platform_integration.youtube_shorts_scheduler.skillz.what_should_i_schedule.run_skill",
        "--upcoming-days",
        str(_int_param(params, "upcoming_days", 7)),
        "--json",
    ]
    if _truthy(params.get("no_signals", "false")):
        cmd.append("--no-signals")
    return cmd


async def execute_youtube_action(action: str, params: Dict[str, str]) -> Dict[str, Any]:
    if action == "comments":
        cmd = _build_comments_command(params)
        timeout_s = _int_param(params, "timeout_s", 1200)
        run_result = await asyncio.to_thread(_run_subprocess, cmd, timeout_s)
        parsed = _extract_json_tail(run_result.get("stdout_tail", ""))
        success = bool(run_result.get("success", False))
        if isinstance(parsed, dict) and parsed.get("error"):
            success = False
        return {
            "success": success,
            "action": action,
            "result": parsed,
            **run_result,
        }

    if action == "indexing":
        cmd = _build_indexing_command(params)
        timeout_s = _int_param(params, "timeout_s", 1800)
        run_result = await asyncio.to_thread(_run_subprocess, cmd, timeout_s)
        return {"success": bool(run_result.get("success", False)), "action": action, **run_result}

    if action == "scheduling":
        cmd = _build_scheduling_command(params)
        timeout_s = _int_param(params, "timeout_s", 1800)
        run_result = await asyncio.to_thread(_run_subprocess, cmd, timeout_s)
        return {"success": bool(run_result.get("success", False)), "action": action, **run_result}

    if action == "schedule_priority":
        cmd = _build_schedule_priority_command(params)
        timeout_s = _int_param(params, "timeout_s", 120)
        run_result = await asyncio.to_thread(_run_subprocess, cmd, timeout_s)
        parsed = _extract_json_tail(run_result.get("stdout_tail", ""))
        success = bool(run_result.get("success", False))
        if isinstance(parsed, dict) and parsed.get("success") is False:
            success = False
        return {
            "success": success,
            "action": action,
            "result": parsed,
            **run_result,
        }

    return {"success": False, "action": action, "error": "unsupported action"}


async def handle_youtube_automation_intent(message: str, sender: str = "") -> Optional[str]:
    """
    Handle AUTOMATION/SCHEDULE intent when explicit YouTube action command is used.

    Returns formatted response text or None when message is not a command.
    """
    parsed = _parse_action_command(message)
    if parsed is None:
        return None

    action, params = parsed
    if action not in SUPPORTED_ACTIONS:
        return (
            "YouTube action not recognized.\n"
            f"Requested: {action}\n"
            f"Supported: {', '.join(sorted(SUPPORTED_ACTIONS))}\n"
            "Format: youtube action <comments|indexing|scheduling> key=value"
        )

    try:
        result = await execute_youtube_action(action, params)
        return (
            f"YouTube action executed for {sender or 'unknown_sender'}:\n"
            f"{json.dumps(result, indent=2, ensure_ascii=False)}"
        )
    except Exception as exc:  # pragma: no cover - defensive
        return f"YouTube action execution error: {exc}"

