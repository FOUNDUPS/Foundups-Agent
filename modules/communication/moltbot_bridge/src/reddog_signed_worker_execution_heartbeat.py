"""Process-local heartbeat for one exact signed-worker execution lease."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from threading import Event, Thread
from typing import Any, Iterator, Mapping

from modules.infrastructure.database.src.signed_worker_execution_lease import (
    renew_signed_worker_execution_lease,
)


HEARTBEAT_INTERVAL_SECONDS = 120
HEARTBEAT_EXTENSION_SECONDS = 900


@dataclass
class SignedWorkerExecutionHeartbeatState:
    """Observable local state for one bounded renewal loop."""

    healthy: bool = True
    renewal_count: int = 0


@contextmanager
def signed_worker_execution_heartbeat(
    *,
    db: Any,
    task_id: str,
    context: Mapping[str, Any],
    interval_seconds: int = HEARTBEAT_INTERVAL_SECONDS,
    extension_seconds: int = HEARTBEAT_EXTENSION_SECONDS,
) -> Iterator[SignedWorkerExecutionHeartbeatState]:
    """Renew the durable lease while the synchronous worker call is active."""

    state = SignedWorkerExecutionHeartbeatState()
    stop = Event()
    thread = Thread(
        target=_renewal_loop,
        kwargs={
            "db": db,
            "task_id": task_id,
            "context": dict(context),
            "stop": stop,
            "state": state,
            "interval_seconds": interval_seconds,
            "extension_seconds": extension_seconds,
        },
        name=f"reddog-lease-{task_id[-12:]}",
        daemon=True,
    )
    thread.start()
    try:
        yield state
    finally:
        stop.set()
        thread.join(timeout=max(1.0, min(float(interval_seconds), 5.0)))
        if thread.is_alive():
            state.healthy = False


def _renewal_loop(
    *,
    db: Any,
    task_id: str,
    context: Mapping[str, Any],
    stop: Event,
    state: SignedWorkerExecutionHeartbeatState,
    interval_seconds: int,
    extension_seconds: int,
) -> None:
    if interval_seconds <= 0 or extension_seconds <= 0:
        state.healthy = False
        return
    while not stop.wait(interval_seconds):
        if not renew_signed_worker_execution_lease(
            db,
            task_id=task_id,
            context=context,
            extension_seconds=extension_seconds,
        ):
            state.healthy = False
            return
        state.renewal_count += 1


__all__ = [
    "HEARTBEAT_EXTENSION_SECONDS",
    "HEARTBEAT_INTERVAL_SECONDS",
    "SignedWorkerExecutionHeartbeatState",
    "signed_worker_execution_heartbeat",
]
