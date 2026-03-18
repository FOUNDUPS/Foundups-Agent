#!/usr/bin/env python3
"""
Generic DAE runtime adapter for OpenClaw.

Provides a deterministic bridge from natural-language runtime commands to the
central DAE launch broker. This is the generic version of the PQN-specific
runtime control already present in `pqn_research_adapter.py`.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger("dae_runtime_adapter")


_DAE_ALIASES: Dict[str, str] = {
    "openclaw dae": "openclaw",
    "openclaw": "openclaw",
    "claw": "openclaw",
    "0102": "openclaw",
    "holodae": "holodae",
    "holo dae": "holodae",
    "git push dae": "git_push_dae",
    "git push": "git_push_dae",
    "social media dae": "social_media",
    "social media": "social_media",
    "social dae": "social_media",
    "vision dae": "vision_dae",
    "foundups vision dae": "vision_dae",
    "vision": "vision_dae",
    "liberty alert dae": "liberty_alert",
    "liberty alert": "liberty_alert",
    "training system": "training_system",
    "training dae": "training_system",
    "pqn research": "pqn_research",
    "pqn architect": "pqn_architect",
}

_MUTATING_VERBS = ("launch", "start", "stop")
_STATUS_VERBS = ("status", "show")
_TAIL_VERBS = ("tail",)
_FOLLOW_VERBS = ("watch", "follow")
_LIST_PATTERNS = (
    "list daes",
    "list launchable daes",
    "show daes",
    "show launchable daes",
    "what daes are available",
    "what daes are launchable",
)


def _normalize(message: str) -> str:
    text = (message or "").strip().lower()
    text = re.sub(r"[^a-z0-9_\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _get_launch_broker():
    try:
        from modules.infrastructure.dae_daemon.src.dae_launch_broker import (
            get_dae_launch_broker,
        )

        return get_dae_launch_broker()
    except Exception as exc:
        logger.debug("[DAE-RUNTIME] Launch broker unavailable: %s", exc)
        return None


def _get_dae_observer():
    try:
        from modules.infrastructure.dae_daemon.src.dae_observer import get_dae_observer

        return get_dae_observer()
    except Exception as exc:
        logger.debug("[DAE-RUNTIME] DAE observer unavailable: %s", exc)
        return None


def parse_dae_runtime_request(message: str) -> Optional[Dict[str, str]]:
    """Return normalized runtime request or None."""
    msg = _normalize(message)
    if not msg:
        return None

    cursor_match = re.search(r"\b(?:since|after|cursor)\s+(\d+)\b", msg)
    since_sequence = int(cursor_match.group(1)) if cursor_match else 0

    for pattern in _LIST_PATTERNS:
        if pattern in msg:
            return {
                "action": "list",
                "dae_id": "",
                "normalized_message": msg,
                "since_sequence": since_sequence,
            }

    action = ""
    if any(msg.startswith(f"{verb} ") or f" {verb} " in msg for verb in _MUTATING_VERBS):
        for verb in _MUTATING_VERBS:
            if msg.startswith(f"{verb} ") or f" {verb} " in msg:
                action = verb
                break
    elif any(msg.startswith(f"{verb} ") or f" {verb} " in msg for verb in _TAIL_VERBS):
        action = "tail"
    elif any(msg.startswith(f"{verb} ") or f" {verb} " in msg for verb in _FOLLOW_VERBS):
        action = "follow"
    elif any(msg.startswith(f"{verb} ") or f" {verb} " in msg for verb in _STATUS_VERBS):
        action = "live_status" if " live" in msg or msg.startswith("live ") else "status"

    if not action:
        return None

    for alias, dae_id in sorted(_DAE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if alias in msg:
            resolved_action = "follow" if action == "tail" and since_sequence > 0 else action
            return {
                "action": resolved_action,
                "dae_id": dae_id,
                "normalized_message": msg,
                "since_sequence": since_sequence,
            }

    if " dae" in msg or msg.endswith("dae"):
        resolved_action = "follow" if action == "tail" and since_sequence > 0 else action
        return {
            "action": resolved_action,
            "dae_id": "",
            "normalized_message": msg,
            "since_sequence": since_sequence,
        }
    return None


def is_dae_runtime_request(message: str) -> bool:
    return parse_dae_runtime_request(message) is not None


def classify_dae_runtime_category(message: str) -> Optional[str]:
    request = parse_dae_runtime_request(message)
    if not request:
        return None
    if request["action"] in {"status", "live_status", "tail", "follow", "list"}:
        return "monitor"
    return "system"


def _format_event_line(event: Dict[str, Any]) -> str:
    payload = event.get("payload", {}) or {}
    base = f"#{event.get('sequence_id')} {event.get('event_type')}"
    if event.get("event_type") == "action_performed":
        action = payload.get("action_type", "action")
        target = payload.get("target") or payload.get("details", {}).get("target") or payload.get("action_target")
        result = payload.get("result", "")
        parts = [base, f"action={action}"]
        if target:
            parts.append(f"target={target}")
        if result:
            parts.append(f"result={str(result)[:80]}")
        return " | ".join(parts)
    if event.get("event_type") == "dae_state_changed":
        return (
            f"{base} | {payload.get('old_state', 'unknown')} -> "
            f"{payload.get('new_state', 'unknown')} | reason={payload.get('reason', 'none')}"
        )
    if event.get("event_type") == "message_in":
        return f"{base} | from={payload.get('source', 'unknown')} | {payload.get('summary', '')[:80]}"
    if event.get("event_type") == "message_out":
        return f"{base} | to={payload.get('dest', 'unknown')} | {payload.get('summary', '')[:80]}"
    return base


def _format_live_status(snapshot: Dict[str, Any]) -> str:
    runtime = snapshot.get("runtime", {}) or {}
    lines = [
        f"DAE live status `{snapshot.get('dae_id')}`",
        f"state={snapshot.get('state')}",
        f"enabled={snapshot.get('enabled')}",
        f"registered={snapshot.get('registered')}",
    ]
    if snapshot.get("domain"):
        lines.append(f"domain={snapshot.get('domain')}")
    if snapshot.get("pid"):
        lines.append(f"pid={snapshot.get('pid')}")
    if snapshot.get("last_heartbeat_age_sec") is not None:
        lines.append(f"last_heartbeat_age_sec={snapshot.get('last_heartbeat_age_sec')}")
    if snapshot.get("next_cursor") is not None:
        lines.append(f"next_cursor={snapshot.get('next_cursor')}")
    if runtime:
        if "running" in runtime:
            lines.append(f"running={runtime.get('running')}")
        if "run_count" in runtime:
            lines.append(f"run_count={runtime.get('run_count')}")
        if runtime.get("last_error"):
            lines.append(f"last_error={runtime.get('last_error')}")
        elif runtime.get("last_result_summary"):
            lines.append(f"last_result={runtime.get('last_result_summary')}")

    recent_events = snapshot.get("recent_events", [])
    if recent_events:
        lines.append("recent_events:")
        lines.extend(f"- {_format_event_line(event)}" for event in recent_events)
    return "\n".join(lines)


def _format_follow_response(follow: Dict[str, Any]) -> str:
    dae_id = follow.get("dae_id") or "system"
    since_sequence = follow.get("since_sequence", 0)
    next_cursor = follow.get("next_cursor", since_sequence)
    events = follow.get("events", [])
    lines = [
        f"DAE follow `{dae_id}`",
        f"since_sequence={since_sequence}",
        f"next_cursor={next_cursor}",
        f"new_events={len(events)}",
    ]
    if events:
        lines.append("events:")
        lines.extend(f"- {_format_event_line(event)}" for event in events)
    return "\n".join(lines)


def handle_dae_runtime_intent(
    message: str,
    sender: str,
    *,
    allow_mutation: bool,
) -> str:
    """Handle launch/status/list/stop runtime commands."""
    request = parse_dae_runtime_request(message)
    if not request:
        return ""

    action = request["action"]
    dae_id = request["dae_id"]
    since_sequence = int(request.get("since_sequence", 0))

    observer = _get_dae_observer()
    broker = _get_launch_broker()

    if action == "list":
        if broker is None:
            return (
                "DAE runtime broker is not available. Start the system through `python main.py` "
                "so 0102 can bootstrap runtime launches."
            )
        launchable = broker.list_launchable_daes()
        if not launchable:
            return "No launchable DAEs are currently registered."
        lines = ["Launchable DAEs:"]
        for key in sorted(launchable):
            item = launchable[key]
            lines.append(
                f"- {key}: running={item.get('running')} enabled={item.get('enabled')} "
                f"domain={item.get('domain')} name={item.get('dae_name')}"
            )
        return "\n".join(lines)

    if not dae_id:
        return (
            "I could not resolve that DAE name. Use `list launchable daes` first, then "
            "launch/status/stop by the known runtime name."
        )

    if action == "tail":
        if observer is None:
            return "DAE observer is not available yet."
        events = observer.tail_events(dae_id=dae_id, limit=8)
        if not events:
            return f"No recent daemon events for `{dae_id}`."
        lines = [f"DAE event tail `{dae_id}`"]
        lines.extend(f"- {_format_event_line(event)}" for event in events)
        return "\n".join(lines)

    if action == "follow":
        if observer is None:
            return "DAE observer is not available yet."
        follow = observer.follow_events(
            dae_id=dae_id,
            since_sequence=since_sequence,
            limit=8,
        )
        return _format_follow_response(follow)

    if action == "live_status":
        if observer is None:
            return "DAE observer is not available yet."
        snapshot = observer.get_live_status(dae_id, limit=8)
        if not snapshot.get("registered"):
            return f"DAE runtime `{dae_id}` is not registered."
        return _format_live_status(snapshot)

    if action == "status":
        if broker is None:
            return (
                "DAE runtime broker is not available. Start the system through `python main.py` "
                "so 0102 can bootstrap runtime launches."
            )
        result = broker.get_runtime_status(dae_id)
        if not result.get("registered"):
            return f"DAE runtime `{dae_id}` is not registered."
        return (
            f"DAE runtime status `{dae_id}`\n"
            f"state={result.get('state')}\n"
            f"running={result.get('running')}\n"
            f"enabled={result.get('enabled')}\n"
            f"run_count={result.get('run_count')}\n"
            f"last_error={result.get('last_error') or 'none'}"
        )

    if not allow_mutation:
        return (
            "Runtime launch and stop commands require 012 authorization. "
            "Use `status <dae>` or `list launchable daes` for read-only inspection."
        )

    if broker is None:
        return (
            "DAE runtime broker is not available. Start the system through `python main.py` "
            "so 0102 can bootstrap runtime launches."
        )

    if action in {"launch", "start"}:
        result = broker.start_dae(dae_id, actor_id=sender)
        status = result.get("status", result.get("error", "unknown"))
        return (
            f"DAE runtime launch `{dae_id}` -> {status}.\n"
            f"started_at={result.get('started_at', 0)}"
        )

    if action == "stop":
        result = broker.stop_dae(dae_id, actor_id=sender)
        status = result.get("status", result.get("error", "unknown"))
        return f"DAE runtime stop `{dae_id}` -> {status}."

    return ""
