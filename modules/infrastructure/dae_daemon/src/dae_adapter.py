"""DAE Adapter — Layer 5.

Lightweight adapter that any existing DAE can use to register with
the centralized daemon WITHOUT changing class hierarchy.

Usage:
    adapter = CentralDAEAdapter(dae_id="fam_daemon", dae_name="FAM DAEmon", domain="foundups")
    adapter.register()
    adapter.start_heartbeat(health_fn=lambda: {"cpu": 0.3})
    # ... DAE runs ...
    adapter.report_message_in("012", "hello")
    adapter.report_action("process", "message", "ok")
    # ... on shutdown ...
    adapter.stop()

WSP Compliance:
    WSP 72: Imports only Layer 0 + Layer 4 (singleton)
"""

import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

from modules.infrastructure.dae_daemon.src.schemas import (
    DAEEventType,
    DAERegistration,
    DAEState,
    SecuritySeverity,
)

logger = logging.getLogger(__name__)


class CentralDAEAdapter:
    """Non-invasive adapter for registering a DAE with the central daemon."""

    def __init__(
        self,
        dae_id: str,
        dae_name: str,
        domain: str,
        module_path: str = "",
        heartbeat_interval: float = 60.0,
    ) -> None:
        self._dae_id = dae_id
        self._dae_name = dae_name
        self._domain = domain
        self._module_path = module_path
        self._heartbeat_interval = heartbeat_interval

        self._daemon = None  # Lazy — resolved on register()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._registered = False

    @property
    def dae_id(self) -> str:
        return self._dae_id

    @property
    def is_registered(self) -> bool:
        return self._registered

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, pid: Optional[int] = None) -> bool:
        """Register with the central daemon. Graceful no-op if unavailable."""
        try:
            from modules.infrastructure.dae_daemon.src.dae_daemon import get_central_daemon
            self._daemon = get_central_daemon()
            reg = DAERegistration(
                dae_id=self._dae_id,
                dae_name=self._dae_name,
                domain=self._domain,
                module_path=self._module_path,
                heartbeat_interval_sec=self._heartbeat_interval,
                pid=pid,
            )
            self._daemon.register_dae(reg)
            self._registered = True
            logger.info("[DAE-ADAPTER] %s registered with central daemon", self._dae_id)
            return True
        except Exception as exc:
            logger.debug("[DAE-ADAPTER] %s registration failed (central daemon unavailable): %s", self._dae_id, exc)
            return False

    # ------------------------------------------------------------------
    # State reporting
    # ------------------------------------------------------------------

    def report_started(self, pid: Optional[int] = None) -> None:
        """Report that this DAE has started."""
        if not self._daemon:
            return
        reg = self._daemon.registry.get(self._dae_id)
        if reg and pid:
            reg.pid = pid
        self._daemon.registry.set_state(self._dae_id, DAEState.RUNNING, "started")

    def report_stopped(self) -> None:
        """Report that this DAE has stopped."""
        if not self._daemon:
            return
        self._daemon.registry.set_state(self._dae_id, DAEState.STOPPED, "stopped")

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    def start_heartbeat(self, health_fn: Optional[Callable[[], Dict[str, Any]]] = None) -> None:
        """Start periodic heartbeat reporting.

        Args:
            health_fn: Optional callable returning health payload dict.
        """
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return

        self._stop_event.clear()
        self._health_fn = health_fn or (lambda: {})

        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name=f"DAEAdapter-{self._dae_id}-heartbeat",
            daemon=True,
        )
        self._heartbeat_thread.start()
        logger.debug("[DAE-ADAPTER] %s heartbeat started (every %.0fs)", self._dae_id, self._heartbeat_interval)

    def _heartbeat_loop(self) -> None:
        while not self._stop_event.is_set():
            if self._daemon:
                try:
                    health = self._health_fn()
                    self._daemon.registry.report_heartbeat(self._dae_id, health)
                except Exception as exc:
                    logger.debug("[DAE-ADAPTER] %s heartbeat error: %s", self._dae_id, exc)
            self._stop_event.wait(timeout=self._heartbeat_interval)

    def stop_heartbeat(self) -> None:
        """Stop the heartbeat thread."""
        self._stop_event.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=3.0)

    # ------------------------------------------------------------------
    # Cardiovascular observation (messages + actions)
    # ------------------------------------------------------------------

    def report_message_in(self, source: str, summary: str = "") -> None:
        """Report an incoming message observed by this DAE."""
        if not self._daemon:
            return
        self._daemon.registry.report_event(
            self._dae_id,
            DAEEventType.MESSAGE_IN,
            {"source": source, "summary": summary[:200]},
        )

    def report_message_out(self, dest: str, summary: str = "") -> None:
        """Report an outgoing message from this DAE."""
        if not self._daemon:
            return
        self._daemon.registry.report_event(
            self._dae_id,
            DAEEventType.MESSAGE_OUT,
            {"dest": dest, "summary": summary[:200]},
        )

    def report_action(
        self,
        action_type: str,
        target: str = "",
        result: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Report an action performed by this DAE."""
        if not self._daemon:
            return
        payload = {
            "action_type": action_type,
            "target": target,
            "result": result[:200],
        }
        if details:
            payload["details"] = details
        self._daemon.registry.report_event(
            self._dae_id,
            DAEEventType.ACTION_PERFORMED,
            payload,
        )

    def report_security_event(self, reason: str, severity: str = "warning") -> None:
        """Report a security event. May trigger killswitch."""
        if not self._daemon:
            return
        self._daemon.registry.report_event(
            self._dae_id,
            DAEEventType.SECURITY_VIOLATION,
            {"reason": reason, "severity": severity},
        )

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Stop heartbeat and report DAE stopped."""
        self.stop_heartbeat()
        self.report_stopped()
