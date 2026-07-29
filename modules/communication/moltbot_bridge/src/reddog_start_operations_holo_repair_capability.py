"""Process-local, one-shot authority for start-operations Holo repair."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any, Mapping


def _digest(value: Mapping[str, Any]) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class StartOperationsHoloRepairCapability:
    task_id: str
    context_digest: str
    _seal: object


class InMemoryStartOperationsHoloRepairRegistry:
    """Issue and consume an exact repair admission once in this process."""

    def __init__(self) -> None:
        self._seal = object()
        self._lock = threading.Lock()
        self._capabilities: dict[str, StartOperationsHoloRepairCapability] = {}

    def issue(
        self, *, task_id: str, context: Mapping[str, Any]
    ) -> StartOperationsHoloRepairCapability | None:
        identifier = str(task_id or "").strip()
        if not identifier or not isinstance(context, Mapping):
            return None
        capability = StartOperationsHoloRepairCapability(
            task_id=identifier,
            context_digest=_digest(context),
            _seal=self._seal,
        )
        with self._lock:
            self._capabilities[identifier] = capability
        return capability

    def consume(
        self,
        *,
        task_id: str,
        context: Mapping[str, Any],
        capability: Any,
    ) -> bool:
        identifier = str(task_id or "").strip()
        context_digest = _digest(context)
        with self._lock:
            expected = self._capabilities.get(identifier)
            accepted = bool(
                expected is not None
                and capability is expected
                and expected._seal is self._seal
                and expected.context_digest == context_digest
            )
            if accepted:
                self._capabilities.pop(identifier, None)
            return accepted


REGISTRY = InMemoryStartOperationsHoloRepairRegistry()


__all__ = [
    "InMemoryStartOperationsHoloRepairRegistry",
    "REGISTRY",
    "StartOperationsHoloRepairCapability",
]
