"""Process-local, one-shot admission for RedDog live-enqueue side effects."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease import (
    AuthoritativeUseLease,
    consume_authoritative_use_lease,
    is_authoritative_use_lease,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease_contract import (
    authoritative_use_effect_digest,
)


def _digest(value: Mapping[str, Any]) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _lease_digest(work_order_id: str, evidence: Mapping[str, Any]) -> str:
    return authoritative_use_effect_digest(
        "live_enqueue",
        {"work_order_id": work_order_id, "evidence_digest": _digest(evidence)},
    )


@dataclass(frozen=True, slots=True)
class LiveEnqueueAdmissionCapability:
    work_order_id: str
    evidence_digest: str
    _authoritative_use_lease: AuthoritativeUseLease
    _seal: object


class InMemoryLiveEnqueueAdmissionRegistry:
    """Bind a verified authority lease to one exact live-enqueue evidence set."""

    def __init__(self) -> None:
        self._seal = object()
        self._lock = threading.Lock()
        self._capabilities: dict[str, LiveEnqueueAdmissionCapability] = {}

    def issue(
        self,
        *,
        work_order_id: Optional[str],
        evidence: Mapping[str, Any],
        signed_authority_reverified: bool,
        authoritative_use_lease: Optional[AuthoritativeUseLease],
    ) -> bool:
        identifier = str(work_order_id or "").strip()
        lease_digest = _lease_digest(identifier, evidence)
        if (
            not identifier
            or signed_authority_reverified is not True
            or not is_authoritative_use_lease(
                authoritative_use_lease,
                effect_kind="live_enqueue",
                effect_request_digest=lease_digest,
            )
        ):
            return False
        capability = LiveEnqueueAdmissionCapability(
            work_order_id=identifier,
            evidence_digest=_digest(evidence),
            _authoritative_use_lease=authoritative_use_lease,
            _seal=self._seal,
        )
        with self._lock:
            self._capabilities[identifier] = capability
        return True

    def consume(
        self,
        *,
        work_order_id: Optional[str],
        evidence: Mapping[str, Any],
    ) -> Optional[LiveEnqueueAdmissionCapability]:
        identifier = str(work_order_id or "").strip()
        with self._lock:
            capability = self._capabilities.pop(identifier, None)
        if capability is None or capability._seal is not self._seal:
            return None
        if capability.evidence_digest != _digest(evidence):
            return None
        if not consume_authoritative_use_lease(
            capability._authoritative_use_lease,
            effect_kind="live_enqueue",
            effect_request_digest=_lease_digest(identifier, evidence),
        ):
            return None
        return capability


__all__ = [
    "InMemoryLiveEnqueueAdmissionRegistry",
    "LiveEnqueueAdmissionCapability",
]
