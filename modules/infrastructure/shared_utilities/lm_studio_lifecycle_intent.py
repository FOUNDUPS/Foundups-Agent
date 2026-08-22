"""Durable, content-minimal recovery intent for one LM Studio node lease."""

from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_text,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)
from modules.infrastructure.shared_utilities.runtime_atomic_replace import (
    atomic_replace_runtime_text,
)


INTENT_SCHEMA_VERSION = "lm_studio_lifecycle_intent.v1"
MAX_INTENT_BYTES = 16_384
_TERMINAL_PHASES = frozenset(
    {"recovered_absent", "unload_confirmed"}
)
_VALID_PHASES = _TERMINAL_PHASES | frozenset(
    {"prepared", "load_requested", "load_confirmed", "quarantined"}
)


@dataclass(frozen=True)
class LMStudioLifecycleIntent:
    intent_id: str
    transaction_id: str
    node_scope_digest: str
    model_key: str
    requested_config_digest: str
    phase: str
    instance_id: str | None
    created_unix_ms: int
    updated_unix_ms: int
    schema_version: str = INTENT_SCHEMA_VERSION

    @property
    def terminal(self) -> bool:
        return self.phase in _TERMINAL_PHASES

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LMStudioLifecycleIntentJournal:
    """One atomically replaced intent file per physical loopback node/port."""

    def __init__(self, node_scope_digest: str, runtime_root: Path | None = None):
        self.repo_root = Path(__file__).resolve().parents[3]
        candidate = runtime_root or (
            Path(tempfile.gettempdir()) / "foundups-lm-studio-lifecycle"
        )
        self.runtime_root = validate_runtime_root_path(
            candidate, repo_root=self.repo_root
        )
        self.node_scope_digest = _required_digest(node_scope_digest)
        self.path = self.runtime_root / f"{self.node_scope_digest}.intent.json"

    def read(self) -> LMStudioLifecycleIntent | None:
        try:
            text = secure_read_confined_text(
                self.path,
                allowed_root=self.runtime_root,
                max_bytes=MAX_INTENT_BYTES,
            )
        except FileNotFoundError:
            return None
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("lm_studio_lifecycle_intent_json_invalid") from exc
        if not isinstance(payload, Mapping):
            raise ValueError("lm_studio_lifecycle_intent_shape_invalid")
        return rehydrate_lm_studio_lifecycle_intent(payload)

    def prepare(
        self, model_key: str, requested_config_digest: str
    ) -> LMStudioLifecycleIntent:
        now = int(time.time() * 1000)
        body = {
            "schema_version": INTENT_SCHEMA_VERSION,
            "transaction_id": str(uuid.uuid4()),
            "node_scope_digest": self.node_scope_digest,
            "model_key": _required_text("model_key", model_key),
            "requested_config_digest": _required_digest(requested_config_digest),
            "phase": "prepared",
            "instance_id": None,
            "created_unix_ms": now,
            "updated_unix_ms": now,
        }
        intent = LMStudioLifecycleIntent(intent_id=_intent_id(body), **body)
        self._write(intent)
        return intent

    def transition(
        self,
        intent: LMStudioLifecycleIntent,
        phase: str,
        *,
        instance_id: str | None = None,
    ) -> LMStudioLifecycleIntent:
        if phase not in _VALID_PHASES:
            raise ValueError("lm_studio_lifecycle_intent_phase_invalid")
        next_intent = replace(
            intent,
            phase=phase,
            instance_id=(
                _required_text("instance_id", instance_id)
                if instance_id is not None
                else intent.instance_id
            ),
            updated_unix_ms=max(int(time.time() * 1000), intent.updated_unix_ms),
            intent_id="",
        )
        body = next_intent.to_dict()
        body.pop("intent_id")
        next_intent = replace(next_intent, intent_id=_intent_id(body))
        self._write(next_intent)
        return next_intent

    def _write(self, intent: LMStudioLifecycleIntent) -> None:
        encoded = json.dumps(
            intent.to_dict(), sort_keys=True, separators=(",", ":")
        )
        if len(encoded.encode("utf-8")) > MAX_INTENT_BYTES:
            raise ValueError("lm_studio_lifecycle_intent_too_large")
        target = validate_runtime_artifact_path(
            self.path,
            repo_root=self.repo_root,
            allowed_root=self.runtime_root,
        )
        atomic_replace_runtime_text(target, encoded)


def rehydrate_lm_studio_lifecycle_intent(
    payload: Mapping[str, Any],
) -> LMStudioLifecycleIntent:
    phase = str(payload.get("phase") or "")
    if phase not in _VALID_PHASES:
        raise ValueError("lm_studio_lifecycle_intent_phase_invalid")
    instance_id = payload.get("instance_id")
    if instance_id is not None:
        instance_id = _required_text("instance_id", instance_id)
    created = _required_timestamp(payload.get("created_unix_ms"))
    updated = _required_timestamp(payload.get("updated_unix_ms"))
    if updated < created:
        raise ValueError("lm_studio_lifecycle_intent_time_invalid")
    body = {
        "schema_version": INTENT_SCHEMA_VERSION,
        "transaction_id": _required_uuid(payload.get("transaction_id")),
        "node_scope_digest": _required_digest(payload.get("node_scope_digest")),
        "model_key": _required_text("model_key", payload.get("model_key")),
        "requested_config_digest": _required_digest(
            payload.get("requested_config_digest")
        ),
        "phase": phase,
        "instance_id": instance_id,
        "created_unix_ms": created,
        "updated_unix_ms": updated,
    }
    if payload.get("schema_version") != INTENT_SCHEMA_VERSION:
        raise ValueError("lm_studio_lifecycle_intent_schema_invalid")
    intent_id = str(payload.get("intent_id") or "")
    if not hmac.compare_digest(intent_id, _intent_id(body)):
        raise ValueError("lm_studio_lifecycle_intent_id_invalid")
    return LMStudioLifecycleIntent(intent_id=intent_id, **body)


def _intent_id(body: Mapping[str, Any]) -> str:
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return "lm_studio_lifecycle_intent:" + hashlib.sha256(encoded).hexdigest()


def _required_digest(value: Any) -> str:
    text = str(value or "")
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError("lm_studio_lifecycle_intent_digest_invalid")
    return text


def _required_text(name: str, value: Any) -> str:
    text = str(value or "").strip()
    if not text or len(text.encode()) > 512 or any(ord(c) < 32 for c in text):
        raise ValueError(f"lm_studio_lifecycle_intent_{name}_invalid")
    return text


def _required_uuid(value: Any) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except ValueError as exc:
        raise ValueError("lm_studio_lifecycle_intent_transaction_id_invalid") from exc


def _required_timestamp(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("lm_studio_lifecycle_intent_time_invalid")
    return value


__all__ = [
    "LMStudioLifecycleIntent",
    "LMStudioLifecycleIntentJournal",
    "rehydrate_lm_studio_lifecycle_intent",
]
