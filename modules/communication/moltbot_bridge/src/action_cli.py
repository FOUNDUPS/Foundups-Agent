"""
Standalone action CLI for OpenClaw/IronClaw social + automation commands.

Purpose:
  - Run action commands independently of main.py menus.
  - Provide a repeatable test harness for 012 observation + feedback loops.

Supported command families:
  - linkedin action <action> key=value
  - x action <action> key=value
  - social campaign <campaign_name> key=value
  - youtube action <action> key=value
  - yt action <action> key=value
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[4]


def _env_truthy(name: str, default: str = "0") -> bool:
    """Return True when env var is set to a truthy value."""
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


def _run_adapter_skill_safety_gate() -> tuple[bool, str]:
    """
    Run Cisco skill-scan gate for direct adapter mode (non-DAE path).

    This closes the supply-chain gap where standalone adapter execution could
    bypass OpenClawDAE intent-gate preflight.
    """
    required = _env_truthy("OPENCLAW_SKILL_SCAN_REQUIRED", "1")
    enforced = _env_truthy("OPENCLAW_SKILL_SCAN_ENFORCED", "1")
    max_severity = os.getenv("OPENCLAW_SKILL_SCAN_MAX_SEVERITY", "medium")
    try:
        from .skill_safety_guard import run_skill_scan
    except Exception as exc:
        ok = not required
        return ok, f"skill safety guard unavailable: {exc}"

    skills_dir = REPO_ROOT / "modules/communication/moltbot_bridge/workspace/skills"
    report_dir = REPO_ROOT / "modules/communication/moltbot_bridge/reports"
    result = run_skill_scan(
        skills_dir=skills_dir,
        max_severity=max_severity,
        report_dir=report_dir,
    )
    if not result.available:
        ok = not required
    else:
        ok = result.passed or (not enforced)
    return ok, result.message


def _serialize_compact(value: Any, max_chars: int = 12000) -> str:
    """Serialize object to compact JSON/text bounded for memory storage."""
    try:
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        text = str(value)
    if len(text) > max_chars:
        return f"{text[: max_chars - 20]}...[truncated]"
    return text


def _store_action_outcome(
    *,
    command: str,
    mode: str,
    backend: Optional[str],
    sender: str,
    channel: str,
    session_key: str,
    item: Dict[str, Any],
) -> bool:
    """
    Persist standalone action execution into WRE PatternMemory (WSP 60/48).
    """
    try:
        from modules.infrastructure.wre_core.src.pattern_memory import (
            PatternMemory,
            SkillOutcome,
        )

        route = str(item.get("route", "unknown")).strip().lower() or "unknown"
        action = (
            str(item.get("action", item.get("campaign", "command")))
            .strip()
            .lower()
            or "command"
        )
        success = bool(item.get("success", False))
        duration_ms = int(item.get("duration_ms", 0) or 0)
        execution_id = f"actioncli-{uuid.uuid4().hex[:12]}"
        skill_name = f"action_cli_{route}_{action}".replace("-", "_")

        input_context = {
            "command": command,
            "mode": mode,
            "backend": backend or "",
            "sender": sender,
            "channel": channel,
            "session_key": session_key,
        }
        output_payload = {
            "route": route,
            "action": action,
            "success": success,
            "duration_ms": duration_ms,
            "result_preview": item.get("result", item.get("response", "")),
        }

        outcome = SkillOutcome(
            execution_id=execution_id,
            skill_name=skill_name,
            agent="openclaw_dae" if mode == "dae" else "action_cli",
            timestamp=datetime.now().isoformat(),
            input_context=_serialize_compact(input_context, max_chars=6000),
            output_result=_serialize_compact(output_payload, max_chars=10000),
            success=success,
            pattern_fidelity=1.0 if success else 0.4,
            outcome_quality=1.0 if success else 0.4,
            execution_time_ms=duration_ms,
            step_count=1,
            failed_at_step=None if success else 1,
            notes=(
                f"source=action_cli mode={mode} route={route} "
                f"backend={(backend or 'none')}"
            ),
        )
        PatternMemory().store_outcome(outcome)
        return True
    except Exception:
        return False


async def _dispatch_adapter_command(command: str, sender: str = "@UnDaoDu") -> Dict[str, Any]:
    """
    Dispatch a raw action command directly to adapter executors.
    """
    from .linkedin_social_adapter import (
        SUPPORTED_ACTIONS as LN_ACTIONS,
        _parse_action_command as parse_linkedin,
        execute_linkedin_action,
    )
    from .social_campaign_adapter import (
        SUPPORTED_CAMPAIGNS,
        _parse_campaign_command as parse_campaign,
        execute_social_campaign,
    )
    from .x_social_adapter import (
        SUPPORTED_ACTIONS as X_ACTIONS,
        _parse_action_command as parse_x,
        execute_x_action,
    )
    from .youtube_automation_adapter import (
        SUPPORTED_ACTIONS as YT_ACTIONS,
        _parse_action_command as parse_youtube,
        execute_youtube_action,
    )

    parsed_campaign = parse_campaign(command)
    if parsed_campaign is not None:
        campaign, params = parsed_campaign
        if campaign not in SUPPORTED_CAMPAIGNS:
            return {
                "success": False,
                "route": "social_campaign",
                "sender": sender,
                "campaign": campaign,
                "error": "unsupported_campaign",
                "supported": sorted(SUPPORTED_CAMPAIGNS),
            }
        result = await execute_social_campaign(campaign, params)
        return {
            "success": bool(result.get("success", False)),
            "route": "social_campaign",
            "sender": sender,
            "campaign": campaign,
            "params": params,
            "result": result,
        }

    parsed_linkedin = parse_linkedin(command)
    if parsed_linkedin is not None:
        action, params = parsed_linkedin
        if action not in LN_ACTIONS:
            return {
                "success": False,
                "route": "linkedin",
                "sender": sender,
                "action": action,
                "error": "unsupported_action",
                "supported": sorted(LN_ACTIONS),
            }
        result = await execute_linkedin_action(action, params)
        return {
            "success": bool(result.get("success", False)),
            "route": "linkedin",
            "sender": sender,
            "action": action,
            "params": params,
            "result": result,
        }

    parsed_x = parse_x(command)
    if parsed_x is not None:
        action, params = parsed_x
        if action not in X_ACTIONS:
            return {
                "success": False,
                "route": "x",
                "sender": sender,
                "action": action,
                "error": "unsupported_action",
                "supported": sorted(X_ACTIONS),
            }
        result = await execute_x_action(action, params)
        return {
            "success": bool(result.get("success", False)),
            "route": "x",
            "sender": sender,
            "action": action,
            "params": params,
            "result": result,
        }

    parsed_youtube = parse_youtube(command)
    if parsed_youtube is not None:
        action, params = parsed_youtube
        if action not in YT_ACTIONS:
            return {
                "success": False,
                "route": "youtube",
                "sender": sender,
                "action": action,
                "error": "unsupported_action",
                "supported": sorted(YT_ACTIONS),
            }
        result = await execute_youtube_action(action, params)
        return {
            "success": bool(result.get("success", False)),
            "route": "youtube",
            "sender": sender,
            "action": action,
            "params": params,
            "result": result,
        }

    return {
        "success": False,
        "route": "unmatched",
        "sender": sender,
        "error": "command_not_recognized",
        "command": command,
        "hints": [
            "linkedin action <action> key=value",
            "x action <action> key=value",
            "social campaign <campaign_name> key=value",
            "youtube action <action> key=value",
        ],
    }


async def _dispatch_via_dae(
    command: str,
    sender: str,
    channel: str,
    session_key: str,
    backend: str,
    no_api_keys: Optional[bool],
    model_target: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Dispatch command through full OpenClawDAE routing + permission gates.
    """
    from .openclaw_dae import OpenClawDAE

    # Gateway Continuity Layer: Create CLI continuity context for this action
    cli_continuity_ctx = None
    effective_session_key = session_key
    process_metadata: Dict[str, Any] = {"source_surface": "cli"}

    try:
        from .continuity_context import ContinuityManager
        cli_continuity_ctx = ContinuityManager.from_cli(
            command="action_cli",
            script_name="action_cli.py",
        )
        # Derive unique session_key from CLI continuity to avoid child ID collision
        effective_session_key = f"cli_action_{cli_continuity_ctx.continuity_id[:12]}"
        process_metadata["parent_continuity_id"] = cli_continuity_ctx.continuity_id

        # Record CLI action breadcrumb for cross-surface tracking
        try:
            from modules.infrastructure.database.src.agent_db import AgentDB
            db = AgentDB()
            db.add_breadcrumb(
                session_id=effective_session_key,
                action="cli_action_start",
                agent_id="0102",
                data={
                    "backend": backend,
                    "command": command[:100] if command else "",
                },
                continuity_id=cli_continuity_ctx.continuity_id,
                runtime_surface=cli_continuity_ctx.surface.value,
                sender_normalized=cli_continuity_ctx.sender_normalized,
            )
        except Exception:
            pass  # Breadcrumb recording is optional
    except Exception:
        # Graceful degradation - continuity is optional
        pass

    prev_openclaw_no_keys = os.getenv("OPENCLAW_NO_API_KEYS")
    prev_ironclaw_no_keys = os.getenv("IRONCLAW_NO_API_KEYS")
    try:
        if no_api_keys is not None:
            flag = "1" if no_api_keys else "0"
            os.environ["OPENCLAW_NO_API_KEYS"] = flag
            os.environ["IRONCLAW_NO_API_KEYS"] = flag

        dae = OpenClawDAE(
            repo_root=REPO_ROOT,
            conversation_backend=backend,
        )
        model_switch_response = None
        if model_target:
            model_switch_response = await dae.process(
                message=f"become {model_target}",
                sender=sender,
                channel=channel,
                session_key=f"{effective_session_key}_model_switch",
                metadata=process_metadata,
            )
        response = await dae.process(
            message=command,
            sender=sender,
            channel=channel,
            session_key=effective_session_key,
            metadata=process_metadata,
        )
    finally:
        if prev_openclaw_no_keys is None:
            os.environ.pop("OPENCLAW_NO_API_KEYS", None)
        else:
            os.environ["OPENCLAW_NO_API_KEYS"] = prev_openclaw_no_keys

        if prev_ironclaw_no_keys is None:
            os.environ.pop("IRONCLAW_NO_API_KEYS", None)
        else:
            os.environ["IRONCLAW_NO_API_KEYS"] = prev_ironclaw_no_keys

    lowered = (response or "").lower()
    success = bool(response) and not lowered.startswith("an error occurred during processing")
    return {
        "success": success,
        "route": "dae",
        "backend": backend,
        "sender": sender,
        "channel": channel,
        "model_switch_response": model_switch_response,
        "response": response,
    }


async def run_action_loop(
    command: str,
    *,
    sender: str = "@UnDaoDu",
    channel: str = "cli",
    session_key: str = "action_cli",
    repeat: int = 1,
    interval_sec: float = 0.0,
    via_dae: bool = False,
    backend: str = "openclaw",
    no_api_keys: Optional[bool] = None,
    model_target: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a raw action command once or repeatedly.
    """
    repeat = max(1, int(repeat))
    interval_sec = max(0.0, float(interval_sec))
    backend = (backend or "openclaw").strip().lower()
    if backend not in {"openclaw", "ironclaw"}:
        backend = "openclaw"
    if no_api_keys is None:
        no_api_keys = backend == "ironclaw"

    results = []
    for idx in range(repeat):
        started = time.perf_counter()
        if via_dae:
            item = await _dispatch_via_dae(
                command=command,
                sender=sender,
                channel=channel,
                session_key=session_key,
                backend=backend,
                no_api_keys=no_api_keys,
                model_target=model_target,
            )
        else:
            gate_ok, gate_msg = _run_adapter_skill_safety_gate()
            if not gate_ok:
                item = {
                    "success": False,
                    "route": "adapter",
                    "sender": sender,
                    "error": "skill_safety_blocked",
                    "message": gate_msg,
                }
            else:
                item = await _dispatch_adapter_command(command=command, sender=sender)
                item = dict(item)
                item["skill_safety_gate"] = gate_msg

        item = dict(item)
        item["iteration"] = idx + 1
        item["duration_ms"] = int((time.perf_counter() - started) * 1000)
        item["memory_stored"] = _store_action_outcome(
            command=command,
            mode="dae" if via_dae else "adapter",
            backend=backend if via_dae else None,
            sender=sender,
            channel=channel,
            session_key=session_key,
            item=item,
        )
        results.append(item)

        if idx < repeat - 1 and interval_sec > 0:
            await asyncio.sleep(interval_sec)

    return {
        "success": all(bool(r.get("success", False)) for r in results),
        "command": command,
        "mode": "dae" if via_dae else "adapter",
        "backend": backend if via_dae else None,
        "repeat": repeat,
        "interval_sec": interval_sec,
        "results": results,
    }


def run_action_command(
    command: str,
    *,
    sender: str = "@UnDaoDu",
    channel: str = "cli",
    session_key: str = "action_cli",
    repeat: int = 1,
    interval_sec: float = 0.0,
    via_dae: bool = False,
    backend: str = "openclaw",
    no_api_keys: Optional[bool] = None,
    model_target: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Synchronous helper wrapper for CLI and menu callers.
    """
    return asyncio.run(
        run_action_loop(
            command=command,
            sender=sender,
            channel=channel,
            session_key=session_key,
            repeat=repeat,
            interval_sec=interval_sec,
            via_dae=via_dae,
            backend=backend,
            no_api_keys=no_api_keys,
            model_target=model_target,
        )
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run OpenClaw/IronClaw action commands as standalone CLI events."
    )
    parser.add_argument(
        "--command",
        required=True,
        help=(
            "Raw command, e.g. "
            "\"linkedin action read_feed max_posts=3\" or "
            "\"youtube action comments channel=move2japan max_comments=2\""
        ),
    )
    parser.add_argument("--sender", default="@UnDaoDu", help="Sender label for logs/audit context.")
    parser.add_argument("--channel", default="cli", help="Channel label for logs/audit context.")
    parser.add_argument("--session-key", default="action_cli", help="Session key for DAE routing.")
    parser.add_argument("--repeat", type=int, default=1, help="Run this command N times.")
    parser.add_argument("--interval-sec", type=float, default=0.0, help="Delay between repeats.")
    parser.add_argument(
        "--via-dae",
        action="store_true",
        help="Route through OpenClawDAE (intent classification + permission gate).",
    )
    parser.add_argument(
        "--backend",
        choices=["openclaw", "ironclaw"],
        default="openclaw",
        help="Conversation backend when --via-dae is enabled.",
    )
    parser.add_argument(
        "--no-api-keys",
        choices=["auto", "on", "off"],
        default="auto",
        help="Key isolation mode for --via-dae. auto=ON for ironclaw, OFF for openclaw.",
    )
    parser.add_argument(
        "--model-target",
        default="",
        help="Pre-switch OpenClawDAE model in the same invocation, e.g. opus, codex, gpt5, qwen3.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of pretty-printed output.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    no_api_keys: Optional[bool]
    if args.no_api_keys == "on":
        no_api_keys = True
    elif args.no_api_keys == "off":
        no_api_keys = False
    else:
        no_api_keys = None

    result = run_action_command(
        command=args.command,
        sender=args.sender,
        channel=args.channel,
        session_key=args.session_key,
        repeat=args.repeat,
        interval_sec=args.interval_sec,
        via_dae=bool(args.via_dae),
        backend=args.backend,
        no_api_keys=no_api_keys,
        model_target=(args.model_target or "").strip() or None,
    )
    if args.compact:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
