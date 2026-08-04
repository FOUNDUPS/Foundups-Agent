"""Opaque activation proof for signed verified-outcome PatternMemory rows."""

from __future__ import annotations

import hashlib
import json
import threading
import weakref
from dataclasses import dataclass
from typing import Any, Mapping


class VerifiedOutcomePatternMemoryActivation:
    """Process-local proof minted from one ACTIVE authority envelope."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "VerifiedOutcomePatternMemoryActivation":
        raise TypeError("verified_outcome_pattern_memory_activation_factory_required")

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("verified_outcome_pattern_memory_activation_is_immutable")

    def __reduce_ex__(self, _protocol: int) -> Any:
        raise TypeError("verified_outcome_pattern_memory_activation_pickle_forbidden")


@dataclass(frozen=True)
class _ActivationSeal:
    record_id: str
    record_digest: str
    envelope_digest: str


_LOCK = threading.Lock()
_ACTIVATIONS: weakref.WeakKeyDictionary[
    VerifiedOutcomePatternMemoryActivation, _ActivationSeal
] = weakref.WeakKeyDictionary()


def _mint_pattern_memory_activation(
    *, record_id: str, record: Mapping[str, Any], envelope_digest: str
) -> VerifiedOutcomePatternMemoryActivation:
    """Mint only after the publisher has reloaded exact ACTIVE authority."""

    if not record_id or not envelope_digest.startswith("sha256:"):
        raise ValueError("verified_outcome_pattern_memory_activation_binding_invalid")
    capability = object.__new__(VerifiedOutcomePatternMemoryActivation)
    with _LOCK:
        _ACTIVATIONS[capability] = _ActivationSeal(
            record_id=record_id,
            record_digest=_digest(record),
            envelope_digest=envelope_digest,
        )
    return capability


def consume_pattern_memory_activation(
    capability: Any, *, record_id: str, record: Mapping[str, Any]
) -> bool:
    """Consume one opaque activation proof for one exact canonical record."""

    if type(capability) is not VerifiedOutcomePatternMemoryActivation:
        return False
    with _LOCK:
        seal = _ACTIVATIONS.pop(capability, None)
    return bool(
        seal is not None
        and seal.record_id == record_id
        and seal.record_digest == _digest(record)
        and seal.envelope_digest.startswith("sha256:")
    )


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "VerifiedOutcomePatternMemoryActivation",
    "consume_pattern_memory_activation",
]
