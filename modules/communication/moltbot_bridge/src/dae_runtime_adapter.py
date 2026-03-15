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
from typing import Dict, Optional

logger = logging.getLogger("dae_runtime_adapter")


_DAE_ALIASES: Dict[str, str] = {
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


def parse_dae_runtime_request(message: str) -> Optional[Dict[str, str]]:
    """Return normalized runtime request or None."""
    msg = _normalize(message)
    if not msg:
        return None

    for pattern in _LIST_PATTERNS:
        if pattern in msg:
            return {"action": "list", "dae_id": "", "normalized_message": msg}

    action = ""
    if any(msg.startswith(f"{verb} ") or f" {verb} " in msg for verb in _MUTATING_VERBS):
        for verb in _MUTATING_VERBS:
            if msg.startswith(f"{verb} ") or f" {verb} " in msg:
                action = verb
                break
    elif any(msg.startswith(f"{verb} ") or f" {verb} " in msg for verb in _STATUS_VERBS):
        action = "status"

    if not action:
        return None

    for alias, dae_id in sorted(_DAE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if alias in msg:
            return {"action": action, "dae_id": dae_id, "normalized_message": msg}

    if " dae" in msg or msg.endswith("dae"):
        return {"action": action, "dae_id": "", "normalized_message": msg}
    return None


def is_dae_runtime_request(message: str) -> bool:
    return parse_dae_runtime_request(message) is not None


def classify_dae_runtime_category(message: str) -> Optional[str]:
    request = parse_dae_runtime_request(message)
    if not request:
        return None
    if request["action"] in {"status", "list"}:
        return "monitor"
    return "system"


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

    broker = _get_launch_broker()
    if broker is None:
        return (
            "DAE runtime broker is not available. Start the system through `python main.py` "
            "so 0102 can bootstrap runtime launches."
        )

    action = request["action"]
    dae_id = request["dae_id"]

    if action == "list":
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

    if action == "status":
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
