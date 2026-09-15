"""Bounded local operator-command inbox for the YouTube Live DAE.

The inbox lets a local supervising agent place explicit, auditable commands in
JSON while the DAE is running. It is not a generic prompt or shell channel:
only the small allowlist below can be dispatched.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List

from modules.communication.livechat.src.automation_gates import gate_snapshot

logger = logging.getLogger(__name__)

COMMAND_FILE_ENV = "YT_OPERATOR_COMMAND_FILE"
ACK_FILE_ENV = "YT_OPERATOR_COMMAND_ACK_FILE"
DEFAULT_COMMAND_FILE = "memory/youtube_dae_operator_commands.json"
DEFAULT_ACK_FILE = "memory/youtube_dae_operator_command_acks.json"
MAX_MESSAGE_LENGTH = 500


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class OperatorCommandQueue:
    """Poll a local JSON command inbox and persist exactly-once acknowledgements."""

    def __init__(
        self,
        dae: Any,
        command_path: Path | None = None,
        acknowledgement_path: Path | None = None,
        poll_interval_seconds: int = 60,
    ) -> None:
        self.dae = dae
        self.command_path = command_path or Path(os.getenv(COMMAND_FILE_ENV, DEFAULT_COMMAND_FILE))
        self.acknowledgement_path = acknowledgement_path or Path(os.getenv(ACK_FILE_ENV, DEFAULT_ACK_FILE))
        self.poll_interval_seconds = poll_interval_seconds
        self._next_poll_at = 0.0
        self.last_result: Dict[str, Any] = {"checked_at": None, "processed": 0}

    @staticmethod
    def _read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        if not path.exists():
            return default
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("[OPERATOR-COMMAND] Cannot read %s: %s", path, exc)
            return default
        return loaded if isinstance(loaded, dict) else default

    @staticmethod
    def _atomic_write(path: Path, value: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(f"{path.suffix}.tmp")
        temporary_path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary_path.replace(path)

    async def poll_once(self) -> Dict[str, Any]:
        """Process commands not already present in the acknowledgement ledger."""
        now = time.monotonic()
        if now < self._next_poll_at:
            self.last_result = {"checked_at": _utc_now(), "processed": 0, "status": "not_due"}
            return self.last_result
        self._next_poll_at = now + self.poll_interval_seconds
        inbox = self._read_json(self.command_path, {"version": 1, "commands": []})
        commands = inbox.get("commands", [])
        if not isinstance(commands, list):
            commands = []
        acknowledgements = self._read_json(self.acknowledgement_path, {"version": 1, "acknowledgements": []})
        recorded = acknowledgements.setdefault("acknowledgements", [])
        completed_ids = {item.get("id") for item in recorded if isinstance(item, dict) and isinstance(item.get("id"), str)}
        results: List[Dict[str, Any]] = []
        for command in commands:
            if not isinstance(command, dict):
                continue
            command_id = command.get("id")
            if not isinstance(command_id, str) or not command_id or command_id in completed_ids:
                continue
            result = await self._dispatch(command)
            recorded.append(result)
            completed_ids.add(command_id)
            results.append(result)
        if results:
            self._atomic_write(self.acknowledgement_path, acknowledgements)
        self.last_result = {"checked_at": _utc_now(), "processed": len(results), "results": results}
        return self.last_result

    async def _dispatch(self, command: Dict[str, Any]) -> Dict[str, Any]:
        command_id = command["id"]
        action = command.get("action")
        payload = command.get("payload", {})
        base = {"id": command_id, "action": action, "completed_at": _utc_now()}
        if not isinstance(payload, dict):
            return {**base, "status": "rejected", "reason": "payload_must_be_an_object"}
        if action == "status":
            return {**base, "status": "accepted", "result": {"gates": gate_snapshot()}}
        if action != "announce":
            return {**base, "status": "rejected", "reason": "action_not_allowlisted"}
        message = payload.get("message")
        if not isinstance(message, str) or not message.strip() or len(message) > MAX_MESSAGE_LENGTH:
            return {**base, "status": "rejected", "reason": "invalid_announce_message"}
        gates = gate_snapshot()
        if gates["stop_active"] or not gates["yt_automation"] or not gates["livechat_send"]:
            return {**base, "status": "blocked", "reason": "automation_gate_closed", "gates": gates}
        livechat = getattr(self.dae, "livechat", None)
        sender: Callable[..., Awaitable[bool]] | None = getattr(livechat, "send_chat_message", None)
        if sender is None:
            return {**base, "status": "blocked", "reason": "livechat_unavailable", "gates": gates}
        try:
            sent = await sender(message.strip(), response_type="operator")
        except Exception as exc:
            logger.exception("[OPERATOR-COMMAND] announce %s failed", command_id)
            return {**base, "status": "failed", "reason": type(exc).__name__}
        return {**base, "status": "accepted" if sent else "blocked", "result": {"sent": bool(sent)}}
