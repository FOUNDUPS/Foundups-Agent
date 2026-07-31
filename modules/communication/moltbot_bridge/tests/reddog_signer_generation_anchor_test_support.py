"""Narrow high-water test doubles for signer generation anchor tests."""

from __future__ import annotations

import threading

from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    SignerRuntimeGenerationHighWater,
    SignerRuntimeGenerationPendingAdvance,
)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


class DurableHighWaterStore:
    def __init__(self) -> None:
        self._values: dict[str, SignerRuntimeGenerationHighWater] = {}
        self._witness_values: dict[
            str, SignerRuntimeGenerationHighWater
        ] = {}
        self._pending = {}
        self._lock = threading.Lock()

    def load(self, anchor_id: str) -> SignerRuntimeGenerationHighWater | None:
        with self._lock:
            return self._values.get(anchor_id)

    def advance(
        self,
        anchor_id: str,
        *,
        expected: SignerRuntimeGenerationHighWater | None,
        next_value: SignerRuntimeGenerationHighWater,
    ) -> None:
        with self._lock:
            if self._values.get(anchor_id) != expected:
                raise RuntimeError("test_high_water_conflict")
            self._values[anchor_id] = next_value

    def witness_load(self, anchor_id: str):
        with self._lock:
            return self._witness_values.get(anchor_id)

    def witness_advance(
        self, anchor_id: str, *, expected, next_value
    ) -> None:
        with self._lock:
            if self._witness_values.get(anchor_id) != expected:
                raise RuntimeError("test_witness_conflict")
            self._witness_values[anchor_id] = next_value

    def pending(self, anchor_id: str):
        with self._lock:
            return self._pending.get(anchor_id)

    def prepare(
        self,
        anchor_id: str,
        *,
        expected,
        next_value,
        previous_anchor_state_json="{}",
    ):
        with self._lock:
            if (
                self._values.get(anchor_id) != expected
                or anchor_id in self._pending
            ):
                raise RuntimeError("test_high_water_conflict")
            pending = SignerRuntimeGenerationPendingAdvance(
                transaction_id=_sha("a"),
                expected=expected,
                next_value=next_value,
                previous_anchor_state_json=previous_anchor_state_json,
            )
            self._pending[anchor_id] = pending
            return pending

    def commit_prepared(self, anchor_id: str, transaction_id: str) -> None:
        with self._lock:
            pending = self._pending.get(anchor_id)
            if pending is None or pending.transaction_id != transaction_id:
                raise RuntimeError("test_high_water_pending_missing")
            self._values[anchor_id] = pending.next_value
            del self._pending[anchor_id]

    def abort_prepared(self, anchor_id: str, transaction_id: str) -> None:
        with self._lock:
            pending = self._pending.get(anchor_id)
            if pending is None or pending.transaction_id != transaction_id:
                raise RuntimeError("test_high_water_pending_missing")
            del self._pending[anchor_id]


class LegacyHighWaterStore:
    def __init__(self) -> None:
        self._value = None

    def load(self, anchor_id: str):
        del anchor_id
        return self._value

    def advance(self, anchor_id: str, *, expected, next_value) -> None:
        del anchor_id
        if self._value != expected:
            raise RuntimeError("test_high_water_conflict")
        self._value = next_value

    def witness_load(self, anchor_id: str):
        del anchor_id
        return self._value

    def witness_advance(self, anchor_id: str, *, expected, next_value):
        return self.advance(
            anchor_id, expected=expected, next_value=next_value
        )


class FailingHighWaterStore(DurableHighWaterStore):
    def prepare(self, *args, **kwargs):
        del args, kwargs
        raise RuntimeError("test_high_water_unavailable")


class NoOpHighWaterStore(DurableHighWaterStore):
    def commit_prepared(self, *args, **kwargs) -> None:
        del args, kwargs


__all__ = [
    "DurableHighWaterStore",
    "FailingHighWaterStore",
    "LegacyHighWaterStore",
    "NoOpHighWaterStore",
]
