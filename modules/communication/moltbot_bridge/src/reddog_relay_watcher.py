"""Bounded relay watcher for an explicitly admitted resident host.

Uses ModuleDB state and the existing process lock. It creates no daemon,
connector, credentials or authority. Cloud MCP tools are NOT Python APIs;
the host must provide authenticated, finite-timeout bindings and admission.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Callable

from modules.communication.moltbot_bridge.src.reddog_relay_poll_store import (
    RelayPollStore, digest, timestamp,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import runtime_operation_lock


def _token(value, name, limit=256):
    if (not isinstance(value, str) or not value or len(value) > limit
            or any(ord(c) < 32 for c in value)):
        raise ValueError("relay_invalid_" + name)
    return value


@dataclass(frozen=True)
class RelaySource:
    provider: str
    account: str
    container: str
    receiver: str
    destination: str

    def binding(self):
        return {name: _token(value, name) for name, value in vars(self).items()}

    @property
    def key(self):
        # One local owner per account/container, not one per self-declared worker.
        return digest([self.provider, self.account, self.container])


@dataclass(frozen=True)
class RelayMessage:
    message_id: str
    sender: str
    recipient: str
    kind: str
    payload: str

    @property
    def content_digest(self):
        return digest(vars(self))


@dataclass(frozen=True)
class RelaySnapshot:
    source_key: str
    watermark: str
    messages: tuple[RelayMessage, ...]
    complete: bool


@dataclass(frozen=True)
class EffectProof:
    operation_id: str
    attempt: int
    outcome: str  # APPLIED, TERMINAL_NOT_APPLIED, UNKNOWN
    proof_id: str = ""


@dataclass(frozen=True)
class RelayBindings:
    # read returns a complete normalized scope, not a raw/untrusted Doc envelope.
    # admit independently checks origin, scope and current execution authority.
    # perform rechecks use-time authority; phase distinguishes ACK from forward.
    # reconcile must use authoritative terminal provider evidence, never absence
    # from an eventually consistent lookup as TERMINAL_NOT_APPLIED.
    read: Callable[..., RelaySnapshot]
    admit: Callable[[RelaySource, RelayMessage], bool]
    perform: Callable[..., EffectProof]
    reconcile: Callable[..., EffectProof]
    timeout_seconds: float

    def __post_init__(self):
        if type(self.timeout_seconds) not in (int, float) or not 0 < self.timeout_seconds <= 60:
            raise ValueError("relay_connector_timeout_required")
        if not all(callable(f) for f in (self.read, self.admit, self.perform, self.reconcile)):
            raise ValueError("relay_connector_bindings_required")


class RelayUnavailable(Exception):
    def __init__(self, code="PROVIDER_UNAVAILABLE", retry_after=60):
        self.code = _token(code, "error_code", 96)
        if type(retry_after) not in (int, float) or not 1 <= retry_after <= 86400:
            raise ValueError("relay_invalid_retry_after")
        self.retry_after = float(retry_after)
        super().__init__(self.code)


class RelayWatcher:
    """One tick per due observation; an existing owner may drive bounded run()."""

    def __init__(self, store: RelayPollStore, source: RelaySource,
                 bindings: RelayBindings | None, *, clock=time.time):
        self.store, self.source, self.bindings, self.clock = store, source, bindings, clock
        self.binding = source.binding()
        self.owner = uuid.uuid4().hex
        self.lock_identity = f"{store.db_identity}:relay:{source.key}"

    def tick(self):
        if self.bindings is None:
            return {"status": "BLOCKED_CONNECTOR_BINDINGS", "poll_performed": False}
        try:
            with runtime_operation_lock(self.lock_identity, timeout_seconds=0.01):
                return self._tick_locked()
        except TimeoutError:
            return {"status": "BLOCKED_WORKER_OWNERSHIP", "poll_performed": False}

    def _result(self, status, *, polled, **extra):
        state = self.store.checkpoint(self.source.key)
        return {"status": status, "poll_performed": polled,
                "delay_seconds": state["delay"], "next_due": state["next_due"],
                "watermark": state["watermark"], **extra}

    def _tick_locked(self):
        now = timestamp(self.clock())
        state = self.store.initialize(self.source.key, self.binding, now)
        if now < state["last_attempt_at"]:
            return self._result("BLOCKED_CLOCK_ROLLBACK", polled=False)
        if now < state["next_due"]:
            return self._result("WAITING", polled=False)
        started_at = now
        self.store.claim_local_owner(self.source.key, self.owner)
        try:
            snapshot = self.bindings.read(self.source, state["watermark"], timeout_seconds=self.bindings.timeout_seconds)
            messages = self._validate_snapshot(snapshot)
            now = timestamp(self.clock())
            if now < started_at:
                return self._result("BLOCKED_CLOCK_ROLLBACK", polled=True)
            activity = self.store.ingest(self.source.key, snapshot.watermark, messages.values(), now)
        except RelayUnavailable as exc:
            return self._observation_failure(started_at, "BLOCKED_PROVIDER", exc.code, exc.retry_after)
        except Exception as exc:
            # Never retain provider exception text, bodies or credentials.
            return self._observation_failure(started_at, "BLOCKED_OBSERVATION", type(exc).__name__, 60)
        blocked = []
        for operation in self.store.pending(self.source.key):
            message = messages.get(operation["message_id"])
            if message is None or message.content_digest != operation["content_digest"]:
                blocked.append("SOURCE_MISSING_OR_CHANGED")
                continue
            if operation["phase"] == "forward" and not self.store.ack_applied(self.source.key, message.message_id):
                blocked.append("ACK_NOT_CONFIRMED")
                continue
            reason = self._dispatch(message, operation)
            if reason:
                blocked.append(reason)
        return self._result("BLOCKED_EFFECT" if blocked else "OBSERVED", polled=True,
                            new_activity=activity, blockers=sorted(set(blocked)))

    def _observation_failure(self, started_at, status, code, retry_after):
        now = timestamp(self.clock())
        if now < started_at:
            return self._result("BLOCKED_CLOCK_ROLLBACK", polled=True)
        self.store.defer_error(self.source.key, now, code, retry_after)
        return self._result(status, polled=True, reason=code)

    def _validate_snapshot(self, snapshot):
        if (not isinstance(snapshot, RelaySnapshot) or snapshot.complete is not True
                or snapshot.source_key != self.source.key):
            raise ValueError("relay_incomplete_or_wrong_source")
        _token(snapshot.watermark, "watermark", 2048)
        if not isinstance(snapshot.messages, tuple) or len(snapshot.messages) > 1000:
            raise ValueError("relay_snapshot_bound_exceeded")
        all_ids, accepted = {}, {}
        for message in snapshot.messages:
            if not isinstance(message, RelayMessage):
                raise ValueError("relay_message_type_invalid")
            for field in ("message_id", "sender", "recipient", "kind"):
                _token(getattr(message, field), field)
            if not isinstance(message.payload, str) or len(message.payload.encode("utf-8")) > 16384:
                raise ValueError("relay_message_payload_bound_exceeded")
            if message.message_id in all_ids and all_ids[message.message_id] != message.content_digest:
                raise ValueError("relay_duplicate_id_conflict")
            all_ids[message.message_id] = message.content_digest
            if (message.sender == self.source.receiver or message.kind == "ack"
                    or message.recipient != self.source.receiver):
                continue
            admitted = self.bindings.admit(self.source, message)
            if type(admitted) is not bool:
                raise ValueError("relay_admission_not_explicit")
            if admitted:
                accepted[message.message_id] = message
        return accepted

    def _save_proof(self, proof, operation_id, attempt):
        if (not isinstance(proof, EffectProof) or proof.operation_id != operation_id
                or type(proof.attempt) is not int or proof.attempt != attempt):
            raise ValueError("relay_effect_proof_binding_invalid")
        if proof.outcome == "UNKNOWN":
            return False
        if proof.outcome not in ("APPLIED", "TERMINAL_NOT_APPLIED"):
            raise ValueError("relay_effect_proof_outcome_invalid")
        _token(proof.proof_id, "proof_id")
        self.store.record_proof(operation_id, attempt, proof.outcome, proof.proof_id, timestamp(self.clock()))
        return True

    def _dispatch(self, message, operation):
        op_id, phase = operation["operation_id"], operation["phase"]
        try:
            if operation["state"] not in ("READY", "INFLIGHT"):
                return "OPERATION_STATE_INVALID"
            if operation["state"] == "INFLIGHT":
                proof = self.bindings.reconcile(self.source, message, phase, op_id, operation["attempt"], timeout_seconds=self.bindings.timeout_seconds)
                if not self._save_proof(proof, op_id, operation["attempt"]):
                    return "EFFECT_OUTCOME_UNKNOWN"
                if proof.outcome == "APPLIED":
                    return None
            # Re-check host admission at use time, including after reconciliation.
            if self.bindings.admit(self.source, message) is not True:
                return "ADMISSION_REVOKED"
            attempt = self.store.start_operation(op_id)  # durable BEFORE any side effect
            proof = self.bindings.perform(self.source, message, phase, op_id, attempt, timeout_seconds=self.bindings.timeout_seconds)
            if not self._save_proof(proof, op_id, attempt):
                return "EFFECT_OUTCOME_UNKNOWN"
            return None if proof.outcome == "APPLIED" else "EFFECT_NOT_APPLIED"
        except Exception:
            # INFLIGHT remains durable on exceptions and process death; replay
            # must reconcile, never blindly resubmit an uncertain side effect.
            return "EFFECT_RECONCILIATION_REQUIRED"

    def run(self, stop_event, *, max_checks: int):
        """Drive bounded checks on the caller's existing thread; no thread spawn.

        Bindings must implement finite provider deadlines. stop_event interrupts
        waits, not an in-flight connector call. No default runtime calls run().
        """
        if type(max_checks) is not int or not 1 <= max_checks <= 10000:
            raise ValueError("relay_invalid_check_bound")
        results = []
        while len(results) < max_checks and not stop_event.is_set():
            result = self.tick()
            if result["poll_performed"]:
                results.append(result)
                if result["status"] == "BLOCKED_CLOCK_ROLLBACK":
                    return {"status": result["status"], "checks": results}
            elif result["status"] != "WAITING":
                return {"status": result["status"], "checks": results}
            if len(results) < max_checks:
                delay = max(0, result["next_due"] - timestamp(self.clock()))
                if stop_event.wait(min(delay, 60)):
                    break
        return {"status": "STOPPED" if stop_event.is_set() else "CHECK_LIMIT", "checks": results}
