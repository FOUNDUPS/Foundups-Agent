"""Runtime DAE launch broker.

Bridges a running system to launchable DAE entrypoints without re-entering the
interactive main menu. This is the missing runtime activation layer between:

    main.py/bootstrap -> central DAEmon -> OpenClaw / 012 control surface

WSP intent:
    - main.py registers launchable DAEs at bootstrap time
    - OpenClaw or other controllers can start/stop/query them at runtime
    - central DAEmon stays the canonical event/state ledger
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from modules.infrastructure.dae_daemon.src.schemas import DAEEventType, DAERegistration, DAEState

logger = logging.getLogger(__name__)

_broker_lock = threading.Lock()
_launch_broker: Optional["DAELaunchBroker"] = None


@dataclass
class DAELaunchSpec:
    """Declarative runtime launch contract for a DAE."""

    dae_id: str
    dae_name: str
    domain: str
    start_callable: Callable[..., Any]
    module_path: str = ""
    description: str = ""
    default_kwargs: Dict[str, Any] = field(default_factory=dict)
    stop_callable: Optional[Callable[..., Any]] = None
    heartbeat_interval_sec: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DAERuntimeHandle:
    """Live broker-managed runtime handle."""

    spec: DAELaunchSpec
    thread: threading.Thread
    actor_id: str
    launch_kwargs: Dict[str, Any]
    started_at: float
    run_count: int = 0
    completed_at: float = 0.0
    last_error: str = ""
    last_result_summary: str = ""
    consecutive_import_failures: int = 0  # WSP 97: Circuit breaker for import errors

    @property
    def is_alive(self) -> bool:
        return self.thread.is_alive()


# WSP 97: Circuit breaker constants for import-time failures
MAX_IMPORT_FAILURES = 3  # Detach DAE after 3 consecutive import errors


class DAELaunchBroker:
    """Runtime broker for starting/stopping DAEs inside a running system."""

    def __init__(self, daemon=None, heartbeat_tick_sec: float = 10.0) -> None:
        if daemon is None:
            from modules.infrastructure.dae_daemon.src.dae_daemon import get_central_daemon

            daemon = get_central_daemon()

        self._daemon = daemon
        self._heartbeat_tick_sec = heartbeat_tick_sec
        self._lock = threading.RLock()
        self._specs: Dict[str, DAELaunchSpec] = {}
        self._handles: Dict[str, DAERuntimeHandle] = {}
        self._import_failures: Dict[str, int] = {}  # WSP 97: Track import failures per dae_id
        self._stop_event = threading.Event()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="DAELaunchBroker-heartbeat",
            daemon=True,
        )
        self._heartbeat_thread.start()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_launch_spec(self, spec: DAELaunchSpec) -> DAELaunchSpec:
        """Register or refresh a launchable DAE spec."""
        with self._lock:
            self._specs[spec.dae_id] = spec

            reg = self._daemon.registry.get(spec.dae_id)
            metadata = {
                "launchable": True,
                "broker_managed": True,
                "description": spec.description,
                **spec.metadata,
            }
            if reg is None:
                self._daemon.register_dae(
                    DAERegistration(
                        dae_id=spec.dae_id,
                        dae_name=spec.dae_name,
                        domain=spec.domain,
                        module_path=spec.module_path,
                        heartbeat_interval_sec=spec.heartbeat_interval_sec,
                        metadata=metadata,
                    )
                )
            else:
                reg.dae_name = spec.dae_name
                reg.domain = spec.domain
                reg.module_path = spec.module_path or reg.module_path
                reg.heartbeat_interval_sec = spec.heartbeat_interval_sec
                reg.metadata.update(metadata)
        return spec

    def get_launch_spec(self, dae_id: str) -> Optional[DAELaunchSpec]:
        return self._specs.get(dae_id)

    def list_launchable_daes(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {
                dae_id: {
                    "dae_name": spec.dae_name,
                    "domain": spec.domain,
                    "description": spec.description,
                    "running": bool(self._handles.get(dae_id) and self._handles[dae_id].is_alive),
                    "enabled": self._daemon.registry.is_enabled(dae_id),
                }
                for dae_id, spec in self._specs.items()
            }

    def list_launchable(self) -> Dict[str, Dict[str, Any]]:
        """Compatibility alias for runtime callers."""
        return self.list_launchable_daes()

    # ------------------------------------------------------------------
    # Runtime control
    # ------------------------------------------------------------------

    def start_dae(
        self,
        dae_id: str,
        *,
        actor_id: str = "0102",
        launch_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Start a registered DAE in a broker-managed background thread."""
        launch_kwargs = dict(launch_kwargs or {})
        spec = self._specs.get(dae_id)
        if spec is None:
            return {
                "success": False,
                "dae_id": dae_id,
                "error": "not_registered",
            }

        if not self._daemon.registry.is_enabled(dae_id):
            return {
                "success": False,
                "dae_id": dae_id,
                "error": "disabled",
            }

        with self._lock:
            current = self._handles.get(dae_id)
            if current and current.is_alive:
                return {
                    "success": True,
                    "dae_id": dae_id,
                    "status": "already_running",
                    "started_at": current.started_at,
                }

            kwargs = {**spec.default_kwargs, **launch_kwargs}
            self._daemon.registry.set_state(dae_id, DAEState.STARTING, "broker_launch_requested")
            self._daemon.registry.report_event(
                dae_id,
                DAEEventType.ACTION_PERFORMED,
                {
                    "action_type": "launch_requested",
                    "actor_id": actor_id,
                    "launch_kwargs": kwargs,
                },
            )

            thread = threading.Thread(
                target=self._run_launch,
                name=f"DAELaunchBroker-{dae_id}",
                args=(spec, actor_id, kwargs),
                daemon=True,
            )
            handle = DAERuntimeHandle(
                spec=spec,
                thread=thread,
                actor_id=actor_id,
                launch_kwargs=kwargs,
                started_at=time.time(),
                run_count=(current.run_count + 1) if current else 1,
            )
            self._handles[dae_id] = handle
            thread.start()

        return {
            "success": True,
            "dae_id": dae_id,
            "status": "starting",
            "started_at": handle.started_at,
        }

    def stop_dae(self, dae_id: str, *, actor_id: str = "0102") -> Dict[str, Any]:
        """Stop a running DAE when a stop hook exists."""
        spec = self._specs.get(dae_id)
        handle = self._handles.get(dae_id)
        if spec is None or handle is None or not handle.is_alive:
            return {
                "success": False,
                "dae_id": dae_id,
                "error": "not_running",
            }
        if spec.stop_callable is None:
            return {
                "success": False,
                "dae_id": dae_id,
                "error": "stop_unsupported",
            }

        self._daemon.registry.set_state(dae_id, DAEState.STOPPING, "broker_stop_requested")
        self._daemon.registry.report_event(
            dae_id,
            DAEEventType.ACTION_PERFORMED,
            {
                "action_type": "stop_requested",
                "actor_id": actor_id,
            },
        )
        try:
            spec.stop_callable()
            self._daemon.registry.set_state(dae_id, DAEState.STOPPED, "broker_stopped")
            self._daemon.registry.report_event(
                dae_id,
                DAEEventType.ACTION_PERFORMED,
                {
                    "action_type": "stop_completed",
                    "actor_id": actor_id,
                },
            )
            return {"success": True, "dae_id": dae_id, "status": "stopped"}
        except Exception as exc:
            self._daemon.registry.set_state(dae_id, DAEState.CRASHED, f"stop_failed:{exc}")
            return {"success": False, "dae_id": dae_id, "error": str(exc)}

    def get_runtime_status(self, dae_id: str) -> Dict[str, Any]:
        spec = self._specs.get(dae_id)
        reg = self._daemon.registry.get(dae_id)
        handle = self._handles.get(dae_id)
        state_value = reg.state.value if reg else "unknown"
        running_states = {
            DAEState.STARTING.value,
            DAEState.RUNNING.value,
            DAEState.DEGRADED.value,
            DAEState.STOPPING.value,
        }
        return {
            "registered": spec is not None,
            "dae_id": dae_id,
            "dae_name": spec.dae_name if spec else (reg.dae_name if reg else dae_id),
            "enabled": reg.enabled if reg else False,
            "state": state_value,
            "running": state_value in running_states,
            "thread_alive": bool(handle and handle.is_alive),
            "last_error": handle.last_error if handle else "",
            "last_result_summary": handle.last_result_summary if handle else "",
            "started_at": handle.started_at if handle else 0.0,
            "completed_at": handle.completed_at if handle else 0.0,
            "run_count": handle.run_count if handle else 0,
        }

    def get_status(self, dae_id: str) -> Dict[str, Any]:
        """Compatibility alias for runtime callers."""
        return self.get_runtime_status(dae_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_launch(self, spec: DAELaunchSpec, actor_id: str, kwargs: Dict[str, Any]) -> None:
        dae_id = spec.dae_id
        handle = self._handles[dae_id]
        reg = self._daemon.registry.get(dae_id)
        if reg:
            reg.pid = os.getpid()

        self._daemon.registry.set_state(dae_id, DAEState.RUNNING, "broker_started")
        # WSP 97: Clear import failure count on successful start (imports passed)
        self._import_failures.pop(dae_id, None)
        self._daemon.registry.report_event(
            dae_id,
            DAEEventType.DAE_STARTED,
            {"actor_id": actor_id},
        )

        try:
            result = spec.start_callable(**kwargs)
            handle.last_result_summary = _summarize_result(result)
            self._daemon.registry.report_event(
                dae_id,
                DAEEventType.ACTION_PERFORMED,
                {
                    "action_type": "launch_completed",
                    "actor_id": actor_id,
                    "result": handle.last_result_summary,
                },
            )
            self._daemon.registry.set_state(dae_id, DAEState.STOPPED, "launch_completed")
        except Exception as exc:
            handle.last_error = str(exc)
            error_type = type(exc).__name__

            # WSP 97: Circuit breaker for import-time failures (track at broker level)
            is_import_error = isinstance(exc, (ImportError, ModuleNotFoundError))
            import_failure_count = self._import_failures.get(dae_id, 0)
            if is_import_error:
                import_failure_count += 1
                self._import_failures[dae_id] = import_failure_count

            # Log verbosity: ERROR on first failure, DEBUG on subsequent (reduce noise)
            if import_failure_count <= 1:
                logger.exception("[DAE-BROKER] Launch failed for %s", dae_id)
            else:
                logger.debug(
                    "[DAE-BROKER] Repeated %s for %s (%d/%d): %s",
                    error_type, dae_id, import_failure_count,
                    MAX_IMPORT_FAILURES, handle.last_error[:100]
                )

            self._daemon.registry.report_event(
                dae_id,
                DAEEventType.ACTION_PERFORMED,
                {
                    "action_type": "launch_failed",
                    "actor_id": actor_id,
                    "error": handle.last_error[:200],
                    "import_failure_count": import_failure_count,
                },
            )

            # WSP 97: Detach after MAX_IMPORT_FAILURES to stop restart loop
            if is_import_error and import_failure_count >= MAX_IMPORT_FAILURES:
                logger.error(
                    "[DAE-BROKER] Import failures exceeded for %s - DETACHED (install deps in venv)",
                    dae_id
                )
                self._daemon.registry.set_state(
                    dae_id, DAEState.DETACHED,
                    f"import_failures_exceeded:{handle.last_error[:100]}"
                )
                # Also disable to prevent is_enabled() from allowing restarts
                self._daemon.registry.disable(dae_id)
            else:
                self._daemon.registry.set_state(dae_id, DAEState.CRASHED, handle.last_error[:200])
        finally:
            handle.completed_at = time.time()
            self._daemon.registry.report_event(
                dae_id,
                DAEEventType.DAE_STOPPED,
                {"actor_id": actor_id},
            )

    def _heartbeat_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                with self._lock:
                    for dae_id, handle in list(self._handles.items()):
                        if not handle.is_alive:
                            continue
                        self._daemon.registry.report_heartbeat(
                            dae_id,
                            {
                                "broker_managed": True,
                                "thread_name": handle.thread.name,
                                "actor_id": handle.actor_id,
                            },
                        )
            except Exception as exc:
                logger.debug("[DAE-BROKER] Heartbeat tick error: %s", exc)
            self._stop_event.wait(timeout=self._heartbeat_tick_sec)

    def stop(self) -> None:
        self._stop_event.set()
        if self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=3.0)


def _summarize_result(result: Any) -> str:
    if result is None:
        return "ok"
    if isinstance(result, dict):
        if "status" in result:
            return str(result["status"])[:200]
        if "message" in result:
            return str(result["message"])[:200]
    return str(result)[:200]


def get_dae_launch_broker(daemon=None) -> DAELaunchBroker:
    global _launch_broker
    with _broker_lock:
        if _launch_broker is None:
            _launch_broker = DAELaunchBroker(daemon=daemon)
        return _launch_broker


def reset_dae_launch_broker() -> None:
    global _launch_broker
    with _broker_lock:
        if _launch_broker is not None:
            _launch_broker.stop()
            _launch_broker = None
