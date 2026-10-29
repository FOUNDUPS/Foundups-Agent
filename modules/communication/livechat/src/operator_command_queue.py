"""Trusted-local, allowlisted YouTube commands with durable attempt claims.

An uncertain attempt is terminal: without provider idempotency/readback we cannot
promise exactly-once delivery. This inbox does not grant network/WRE authority.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from modules.communication.livechat.src.automation_gates import gate_snapshot
from modules.infrastructure.shared_utilities.runtime_artifact_safety import runtime_operation_lock

logger = logging.getLogger(__name__)
COMMAND_FILE_ENV = "YT_012_MANIFEST_FILE"
ACK_FILE_ENV = "YT_012_MANIFEST_ACK_FILE"
DEFAULT_COMMAND_FILE = "memory/012_manifest.json"
DEFAULT_ACK_FILE = "memory/012_manifest_acknowledgements.json"
DEFAULT_STATE_FILE = "memory/012_manifest_state.json"
REPO_ROOT = Path(__file__).resolve().parents[4]
MAX_MESSAGE_LENGTH = 500
MAX_CHAT_LENGTH = 200
MAX_JSON_BYTES = 4 * 1024 * 1024
ALLOWED_CONTEXT_SURFACES = {"livechat", "comments"}
_TERMINAL = {"accepted", "blocked", "rejected", "failed", "unknown", "simulated", "expired", "superseded"}
_ACTIVE_LEDGERS: set[str] = set()
_ACTIVE_GUARD = threading.Lock()


def _resolve_path(path: Path | str) -> Path:
    path = Path(path)
    return (path if path.is_absolute() else REPO_ROOT / path).resolve()


def resolve_manifest_state_path() -> Path:
    """Use one checkout-rooted path in both the producer and comment reader."""
    return _resolve_path(os.getenv("YT_012_MANIFEST_STATE_FILE", DEFAULT_STATE_FILE))


def load_active_theme(surface: str):
    """Read private, unexpired context for one surface without mutating receipts."""
    try:
        raw = OperatorCommandQueue._read_json(resolve_manifest_state_path(), {'version': 1})
        context = raw.get('active_context')
        if not isinstance(context, dict) or surface not in ALLOWED_CONTEXT_SURFACES:
            return None
        surfaces, expiry = context.get('surfaces'), context.get('expires_at_unix')
        message = context.get('message')
        if (not isinstance(surfaces, list) or not surfaces
                or any(not isinstance(s, str) or s not in ALLOWED_CONTEXT_SURFACES for s in surfaces)
                or surface not in surfaces or not _finite_number(expiry) or expiry <= time.time()
                or not isinstance(message, str) or not message.strip() or len(message) > MAX_MESSAGE_LENGTH):
            return None
        return dict(context)
    except (OSError, ValueError, TypeError, OverflowError):
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finite_number(value: Any) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def enqueue_operator_command(command: dict, *, command_path=None, acknowledgement_path=None) -> str:
    """Append one immutable command under the queue's existing ledger lock.

    Producers own only the inbox. Acknowledgements and active state stay queue-owned.
    """
    inbox_path = _resolve_path(command_path or os.getenv(COMMAND_FILE_ENV, DEFAULT_COMMAND_FILE))
    ledger_path = _resolve_path(acknowledgement_path or os.getenv(ACK_FILE_ENV, DEFAULT_ACK_FILE))
    if inbox_path == ledger_path:
        raise ValueError('manifest_paths_must_be_distinct')
    if (not isinstance(command, dict) or not isinstance(command.get('id'), str)
            or not 1 <= len(command['id']) <= 200
            or command.get('action') not in {'status', 'set_context', 'clear_context', 'announce'}
            or not isinstance(command.get('payload', {}), dict)):
        raise ValueError('invalid_command')
    identity = os.path.normcase(str(ledger_path))
    with runtime_operation_lock(identity, timeout_seconds=5):
        inbox = OperatorCommandQueue._read_json(inbox_path, {'version': 1, 'commands': []})
        ledger = OperatorCommandQueue._read_json(ledger_path, {'version': 1, 'acknowledgements': []})
        commands, rows = inbox.get('commands'), ledger.get('acknowledgements')
        if not isinstance(commands, list) or not isinstance(rows, list) or len(commands) >= 100:
            raise ValueError('invalid_or_full_manifest')
        if any(not isinstance(row, dict) for row in commands + rows):
            raise ValueError('invalid_manifest_entry')
        if any(row.get('id') == command['id'] for row in commands + rows):
            raise ValueError('command_id_already_exists')
        inbox['commands'] = [*commands, command]
        OperatorCommandQueue._atomic_write(inbox_path, inbox)
    return command['id']


class OperatorCommandQueue:
    """Serialize one ledger and claim before effects; never retry unknown work."""

    def __init__(self, dae: Any, command_path: Path | None = None,
                 acknowledgement_path: Path | None = None, state_path: Path | None = None,
                 poll_interval_seconds: float = 60, dispatch_timeout_seconds: float = 30) -> None:
        self.dae = dae
        self.command_path = _resolve_path(command_path if command_path is not None else os.getenv(COMMAND_FILE_ENV, DEFAULT_COMMAND_FILE))
        self.acknowledgement_path = _resolve_path(acknowledgement_path if acknowledgement_path is not None else os.getenv(ACK_FILE_ENV, DEFAULT_ACK_FILE))
        self.state_path = _resolve_path(state_path) if state_path is not None else resolve_manifest_state_path()
        if len({self.command_path, self.acknowledgement_path, self.state_path}) != 3:
            raise ValueError("manifest_paths_must_be_distinct")
        if not _finite_number(poll_interval_seconds) or not 0 <= poll_interval_seconds <= 3600:
            raise ValueError("invalid_poll_interval")
        if not _finite_number(dispatch_timeout_seconds) or not 0 < dispatch_timeout_seconds <= 300:
            raise ValueError("invalid_dispatch_timeout")
        self.poll_interval_seconds = poll_interval_seconds
        self.dispatch_timeout_seconds = dispatch_timeout_seconds
        self._next_poll_at = 0.0
        self.last_result: dict[str, Any] = {"checked_at": None, "processed": 0}

    @staticmethod
    def _read_json(path: Path, default: dict) -> dict:
        try:
            with path.open("rb") as stream:
                raw = stream.read(MAX_JSON_BYTES + 1)
        except FileNotFoundError:
            return default
        if len(raw) > MAX_JSON_BYTES:
            raise ValueError("manifest_file_too_large")
        loaded = json.loads(raw)
        if not isinstance(loaded, dict) or type(loaded.get("version")) is not int or loaded["version"] != 1:
            raise ValueError("invalid_manifest_version_or_shape")
        return loaded

    @staticmethod
    def _atomic_write(path: Path, value: dict) -> None:
        data = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
        if len(data) > MAX_JSON_BYTES:
            raise ValueError("manifest_file_too_large")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(f"{path.suffix}.tmp")
        with temporary_path.open("wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(path)

    async def poll_once(self) -> dict:
        now = time.monotonic()
        if now < self._next_poll_at:
            return self._summary("not_due")
        identity = os.path.normcase(str(self.acknowledgement_path))
        # Windows named mutexes are thread-reentrant: also exclude async peers
        # on this thread. The existing OS lock excludes other processes.
        with _ACTIVE_GUARD:
            if identity in _ACTIVE_LEDGERS:
                return self._summary("busy")
            _ACTIVE_LEDGERS.add(identity)
        try:
            with runtime_operation_lock(identity, timeout_seconds=0.01):
                self._next_poll_at = now + self.poll_interval_seconds
                return await self._poll_locked()
        except TimeoutError:
            return self._summary("busy")
        finally:
            with _ACTIVE_GUARD:
                _ACTIVE_LEDGERS.remove(identity)

    def _summary(self, status: str) -> dict:
        self.last_result = {"checked_at": _utc_now(), "processed": 0, "status": status}
        return self.last_result

    async def _poll_locked(self) -> dict:
        inbox = self._read_json(self.command_path, {"version": 1, "commands": []})
        ledger = self._read_json(self.acknowledgement_path, {"version": 1, "acknowledgements": []})
        self._read_json(self.state_path, {"version": 1, "active_context": None})
        commands, recorded = inbox.get("commands"), ledger.get("acknowledgements")
        if not isinstance(commands, list) or len(commands) > 100 or not isinstance(recorded, list):
            raise ValueError("invalid_manifest_lists")
        rows = {}
        for row in recorded:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"] or row["id"] in rows:
                raise ValueError("invalid_acknowledgement_id")
            if row.get("status") not in _TERMINAL | {"deferred"}:
                raise ValueError("invalid_acknowledgement_status")
            if row["status"] == "deferred" and (
                not _finite_number(row.get("first_seen_unix")) or not isinstance(row.get("command_digest"), str)
                or len(row["command_digest"]) != 64
            ):
                raise ValueError("invalid_pending_acknowledgement")
            rows[row["id"]] = row
        digests = {}
        for command in commands:
            if not isinstance(command, dict) or not isinstance(command.get("id"), str) or not 1 <= len(command["id"]) <= 200:
                raise ValueError("invalid_command_id")
            digest = hashlib.sha256(json.dumps(command, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()).hexdigest()
            if command["id"] in digests and digests[command["id"]] != digest:
                raise ValueError("conflicting_command_id")
            if command["id"] in rows and rows[command["id"]].get("command_digest", digest) != digest:
                raise ValueError("command_id_payload_changed")
            digests[command["id"]] = digest
        results = []
        seen = set()
        for command in commands:
            command_id, digest = command["id"], digests[command["id"]]
            if command_id in seen:
                continue
            seen.add(command_id)
            row = rows.get(command_id)
            if row is not None:
                if row.get("command_digest", digest) != digest:
                    raise ValueError("command_id_payload_changed")
                if row["status"] != "deferred":
                    continue  # Includes old terminal receipts without digests.
            else:
                row = {"id": command_id, "action": command.get("action"), "command_digest": digest,
                       "first_seen_unix": time.time(), "status": "unknown"}
                recorded.append(row)
                rows[command_id] = row
            # Persist uncertainty before any context/provider effect. Cancellation
            # or a failed final write leaves this tombstone, never an auto-retry.
            for field in ("reason", "result", "gates", "completed_at"):
                row.pop(field, None)
            row["status"] = "unknown"
            self._atomic_write(self.acknowledgement_path, ledger)
            try:
                result = await asyncio.wait_for(self._dispatch(command, row, recorded), self.dispatch_timeout_seconds)
            except Exception as exc:
                result = {"status": "unknown", "reason": type(exc).__name__}
            row.update(result, completed_at=_utc_now())
            self._atomic_write(self.acknowledgement_path, ledger)
            self._write_receipt(row)  # Telemetry cannot precede the durable result.
            results.append(dict(row))
        self.last_result = {"checked_at": _utc_now(), "processed": len(results), "results": results}
        return self.last_result

    def _write_receipt(self, result: dict) -> None:
        status = result["status"]
        delivery_unknown = result.get("result", {}).get("delivery_verified") is False
        health = "green" if status == "accepted" and not delivery_unknown else "amber" if status in {"accepted", "deferred", "unknown", "simulated"} else "red"
        state = self._read_json(self.state_path, {"version": 1, "active_context": None})
        state["last_receipt"] = {key: result.get(key) for key in ("id", "action", "status", "reason", "result")}
        state["last_receipt"].update(health=health, recorded_at=_utc_now())
        self._atomic_write(self.state_path, state)

    async def watch_forever(self) -> None:
        while True:
            try:
                await self.poll_once()
            except Exception as exc:
                self._summary("blocked")
                self.last_result["reason"] = type(exc).__name__
                logger.warning("[012-MANIFEST] Poll blocked: %s", type(exc).__name__)
            await asyncio.sleep(max(1, self.poll_interval_seconds))

    async def _dispatch(self, command: dict, row: dict, recorded: list) -> dict:
        action, payload = command.get("action"), command.get("payload", {})
        if not isinstance(payload, dict):
            return {"status": "rejected", "reason": "payload_must_be_an_object"}
        if action == "status":
            return {"status": "accepted", "result": {"gates": gate_snapshot()}}
        if action == "clear_context":
            self._atomic_write(self.state_path, {"version": 1, "active_context": None, "updated_at": _utc_now()})
            return {"status": "accepted", "result": {"context": "cleared"}}
        if action not in ("announce", "set_context"):
            return {"status": "rejected", "reason": "action_not_allowlisted"}
        message = payload.get("message")
        surfaces = payload.get("surfaces", ["livechat", "comments"]) if action == "set_context" else ["livechat"]
        if not isinstance(surfaces, list) or not surfaces or any(not isinstance(s, str) or s not in ALLOWED_CONTEXT_SURFACES for s in surfaces):
            return {"status": "rejected", "reason": "invalid_context_surfaces"}
        limit = MAX_CHAT_LENGTH if "livechat" in surfaces else MAX_MESSAGE_LENGTH
        if not isinstance(message, str) or not message.strip() or len(message) > limit:
            return {"status": "rejected", "reason": "invalid_message"}
        ttl = payload.get("ttl_seconds", 3600)
        if type(ttl) is not int or not 60 <= ttl <= 86400:
            return {"status": "rejected", "reason": "invalid_ttl"}
        expires = row["first_seen_unix"] + ttl
        if expires <= time.time():
            return {"status": "expired", "reason": "command_expired"}
        if action == "set_context":
            later_rows = recorded[recorded.index(row) + 1:]
            if any(r.get("action") in ("set_context", "clear_context") and r["status"] not in {"rejected", "blocked", "expired"} for r in later_rows):
                return {"status": "superseded", "reason": "newer_context_command"}
        gates = gate_snapshot()
        if (gates["stop_active"] or not gates["yt_automation"]
            or ("livechat" in surfaces and (not gates["livechat_send"] or not gates["announcements"]))
            or ("comments" in surfaces and not gates["comment_engagement"])):
            return {"status": "blocked", "reason": "automation_gate_closed", "gates": gates}
        if "livechat" in surfaces and gates["livechat_dry_run"]:
            return {"status": "simulated", "result": {"sender_accepted": False, "delivery_verified": False}}
        sender = getattr(getattr(self.dae, "livechat", None), "send_chat_message", None)
        if action == 'announce' and not callable(sender):
            return {"status": "deferred", "reason": "livechat_unavailable"}
        result = {}
        if action == "set_context":
            context = {"message": message.strip(), "surfaces": surfaces, "updated_at": _utc_now(),
                       "expires_at_unix": expires, "source_command_id": command["id"]}
            self._atomic_write(self.state_path, {"version": 1, "active_context": context})
            result["context"] = context
            # Context is private behavioral guidance. Only announce publishes.
            result["context_activated"] = True
            result["public_message_sent"] = False
            return {"status": "accepted", "result": result}
        if "livechat" not in surfaces:
            return {"status": "accepted", "result": result}
        sent = await sender(message.strip(), response_type="operator")
        result.update(sender_accepted=sent is True, delivery_verified=False)
        return {"status": "accepted" if sent is True else "unknown", "result": result}

