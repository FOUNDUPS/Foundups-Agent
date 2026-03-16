"""Read-side DAEmon observer helpers for live status and event tails."""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

_observer_lock = threading.Lock()
_dae_observer: Optional["DAEObserver"] = None


class DAEObserver:
    """Read-only observer over the central DAEmon state and recent events."""

    def __init__(self, daemon=None) -> None:
        if daemon is None:
            from modules.infrastructure.dae_daemon.src.dae_daemon import get_central_daemon

            daemon = get_central_daemon()
        self._daemon = daemon

    def tail_events(
        self,
        *,
        dae_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        events = self._daemon.event_store.query_recent(
            dae_id=dae_id,
            event_type=event_type,
            limit=limit,
        )
        return [self._event_to_dict(event) for event in events]

    def get_live_status(self, dae_id: str, *, limit: int = 8) -> Dict[str, Any]:
        reg = self._daemon.registry.get(dae_id)
        recent_events = self.tail_events(dae_id=dae_id, limit=limit)
        runtime = self._get_runtime_status(dae_id)
        last_event = recent_events[-1] if recent_events else None
        last_action = None
        for event in reversed(recent_events):
            if event["event_type"] == "action_performed":
                last_action = event
                break

        heartbeat_age_sec = None
        if reg and reg.last_heartbeat:
            heartbeat_age_sec = round(max(0.0, time.time() - reg.last_heartbeat), 1)

        return {
            "registered": reg is not None or runtime.get("registered", False),
            "dae_id": dae_id,
            "dae_name": reg.dae_name if reg else runtime.get("dae_name", dae_id),
            "domain": reg.domain if reg else "",
            "state": reg.state.value if reg else runtime.get("state", "unknown"),
            "enabled": reg.enabled if reg else runtime.get("enabled", False),
            "pid": reg.pid if reg else None,
            "heartbeat_interval_sec": reg.heartbeat_interval_sec if reg else None,
            "last_heartbeat_age_sec": heartbeat_age_sec,
            "runtime": runtime,
            "recent_events": recent_events,
            "last_event": last_event,
            "last_action": last_action,
        }

    def get_system_live_status(self, *, limit: int = 12) -> Dict[str, Any]:
        return {
            "dashboard": self._daemon.get_dashboard(),
            "recent_events": self.tail_events(limit=limit),
        }

    def _get_runtime_status(self, dae_id: str) -> Dict[str, Any]:
        try:
            from modules.infrastructure.dae_daemon.src.dae_launch_broker import get_dae_launch_broker

            broker = get_dae_launch_broker()
        except Exception:
            return {}

        try:
            return broker.get_runtime_status(dae_id)
        except Exception:
            return {}

    @staticmethod
    def _event_to_dict(event: Any) -> Dict[str, Any]:
        payload = dict(event.payload or {})
        return {
            "sequence_id": event.sequence_id,
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "dae_id": event.dae_id,
            "actor_id": event.actor_id,
            "timestamp": event.timestamp,
            "payload": payload,
        }


def get_dae_observer(daemon=None) -> DAEObserver:
    global _dae_observer
    with _observer_lock:
        if _dae_observer is None:
            _dae_observer = DAEObserver(daemon=daemon)
        return _dae_observer


def reset_dae_observer() -> None:
    global _dae_observer
    with _observer_lock:
        _dae_observer = None
