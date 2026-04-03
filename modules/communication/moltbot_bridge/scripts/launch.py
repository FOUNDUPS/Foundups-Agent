#!/usr/bin/env python3
"""Broker-managed OpenClaw resident service launcher."""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_runtime_lock = threading.RLock()
_runtime_server: Any = None
_runtime_status: Dict[str, Any] = {}
_supervisor_lock = threading.RLock()
_supervisor_runtime: Any = None
_supervisor_status: Dict[str, Any] = {}
_broker_bootstrapped: bool = False


def _ensure_broker_bootstrap() -> None:
    """
    Ensure broker has DAE specs registered before supervisor starts.

    This self-bootstrap fixes the "openclaw_runtime_not_registered" escalation
    when supervisor is started standalone (not via main.py bootstrap).

    Safe to call multiple times - uses module-level flag to avoid re-registration.
    """
    global _broker_bootstrapped
    if _broker_bootstrapped:
        return

    try:
        from modules.infrastructure.dae_daemon.src.dae_launch_broker import (
            get_dae_launch_broker,
        )

        broker = get_dae_launch_broker()
        if broker and len(broker.list_launchable_daes()) > 0:
            # Already bootstrapped by main.py
            _broker_bootstrapped = True
            return

        # Import and call main.py's bootstrap function
        # GUARD: Suppress supervisor autostart to avoid recursive start
        # (we're already inside run_openclaw_supervisor_service)
        logger.info("[SUPERVISOR-BOOTSTRAP] Broker has no specs - self-bootstrapping (register only)")
        try:
            from main import bootstrap_runtime_dae_launches

            # Save and suppress autostart env gates
            saved_supervisor_autostart = os.getenv("OPENCLAW_SUPERVISOR_AUTOSTART")
            saved_resident_autostart = os.getenv("OPENCLAW_RESIDENT_AUTOSTART")
            os.environ["OPENCLAW_SUPERVISOR_AUTOSTART"] = "0"
            os.environ["OPENCLAW_RESIDENT_AUTOSTART"] = "0"

            try:
                bootstrap_runtime_dae_launches()
            finally:
                # Restore original env values
                if saved_supervisor_autostart is not None:
                    os.environ["OPENCLAW_SUPERVISOR_AUTOSTART"] = saved_supervisor_autostart
                else:
                    os.environ.pop("OPENCLAW_SUPERVISOR_AUTOSTART", None)
                if saved_resident_autostart is not None:
                    os.environ["OPENCLAW_RESIDENT_AUTOSTART"] = saved_resident_autostart
                else:
                    os.environ.pop("OPENCLAW_RESIDENT_AUTOSTART", None)

            _broker_bootstrapped = True
            logger.info("[SUPERVISOR-BOOTSTRAP] Self-bootstrap complete (specs registered, no autostart)")
        except ImportError:
            # Fallback: Register minimal specs for supervisor to function
            logger.warning("[SUPERVISOR-BOOTSTRAP] main.py import failed, registering minimal specs")
            _register_minimal_openclaw_specs(broker)
            _broker_bootstrapped = True
    except Exception as exc:
        logger.error("[SUPERVISOR-BOOTSTRAP] Bootstrap failed: %s", exc)


def _register_minimal_openclaw_specs(broker: Any) -> None:
    """Register minimal DAE specs for supervisor to function without full main.py bootstrap."""
    from modules.infrastructure.dae_daemon.src.dae_launch_broker import DAELaunchSpec

    # Register openclaw resident spec
    broker.register_launch_spec(
        DAELaunchSpec(
            dae_id="openclaw",
            dae_name="OpenClaw Resident Service",
            domain="communication",
            module_path="modules.communication.moltbot_bridge.scripts.launch",
            start_callable=run_openclaw_resident_service,
            stop_callable=stop_openclaw_resident_service,
            heartbeat_interval_sec=15.0,
            description="Resident OpenClaw webhook/control-plane service.",
        )
    )
    logger.info("[SUPERVISOR-BOOTSTRAP] Registered minimal openclaw spec")


def _resolve_host(host: Optional[str]) -> str:
    return (
        host
        or os.getenv("OPENCLAW_RESIDENT_HOST")
        or os.getenv("OPENCLAW_BRIDGE_HOST")
        or "127.0.0.1"
    )


def _resolve_port(port: Optional[int]) -> int:
    raw = (
        str(port)
        if port is not None
        else (
            os.getenv("OPENCLAW_RESIDENT_PORT")
            or os.getenv("OPENCLAW_BRIDGE_PORT")
            or os.getenv("MOLTBOT_BRIDGE_PORT")
            or "18800"
        )
    )
    return int(raw)


def run_openclaw_resident_service(
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> Dict[str, Any]:
    """Run the OpenClaw webhook receiver as the resident OpenClaw DAE surface."""
    from modules.communication.moltbot_bridge.src.webhook_receiver import app

    import uvicorn

    resolved_host = _resolve_host(host)
    resolved_port = _resolve_port(port)
    log_level = os.getenv("OPENCLAW_RESIDENT_LOG_LEVEL", "info").strip() or "info"

    config = uvicorn.Config(
        app,
        host=resolved_host,
        port=resolved_port,
        log_level=log_level,
        access_log=False,
    )
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None

    with _runtime_lock:
        global _runtime_server
        _runtime_server = server
        _runtime_status.clear()
        _runtime_status.update(
            {
                "host": resolved_host,
                "port": resolved_port,
                "log_level": log_level,
                "status": "starting",
            }
        )

    logger.info(
        "[OPENCLAW-RESIDENT] Starting resident service on %s:%s",
        resolved_host,
        resolved_port,
    )

    try:
        server.run()
    finally:
        started = bool(getattr(server, "started", False))
        with _runtime_lock:
            if _runtime_server is server:
                _runtime_server = None
                _runtime_status.update(
                    {
                        "host": resolved_host,
                        "port": resolved_port,
                        "log_level": log_level,
                        "status": "stopped" if started else "failed",
                    }
                )

    if not bool(getattr(server, "started", False)):
        raise RuntimeError(
            f"openclaw_resident_start_failed:{resolved_host}:{resolved_port}"
        )

    return {
        "status": "stopped",
        "host": resolved_host,
        "port": resolved_port,
    }


def stop_openclaw_resident_service() -> Dict[str, Any]:
    """Request shutdown for the broker-managed resident OpenClaw service."""
    with _runtime_lock:
        server = _runtime_server
        if server is None:
            return {"status": "not_running"}

        server.should_exit = True
        _runtime_status["status"] = "stopping"
        return {
            "status": "stopping",
            "host": _runtime_status.get("host", "127.0.0.1"),
            "port": _runtime_status.get("port", 18800),
        }


def get_openclaw_resident_status() -> Dict[str, Any]:
    """Return best-effort resident service status for broker callers."""
    with _runtime_lock:
        server = _runtime_server
        status = dict(_runtime_status)
        status["running"] = bool(server and not getattr(server, "should_exit", False))
        return status


def run_openclaw_supervisor_service(repo_root: Optional[str] = None) -> Dict[str, Any]:
    """Run the explicit OpenClaw supervisor state machine as a broker-managed runtime."""
    from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
        OpenClawSupervisor,
    )

    resolved_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[4]

    # Self-bootstrap: Ensure broker has DAE specs registered before supervisor starts.
    # This fixes the "openclaw_runtime_not_registered" escalation when supervisor
    # is started standalone (not via main.py bootstrap).
    _ensure_broker_bootstrap()

    supervisor = OpenClawSupervisor(repo_root=resolved_root)

    with _supervisor_lock:
        global _supervisor_runtime
        _supervisor_runtime = supervisor
        _supervisor_status.clear()
        _supervisor_status.update(
            {
                "repo_root": str(resolved_root),
                "status": "running",
            }
        )

    try:
        result = supervisor.run_forever()
        with _supervisor_lock:
            if _supervisor_runtime is supervisor:
                _supervisor_runtime = None
                _supervisor_status.update({"status": result.get("status", "stopped")})
        return result
    finally:
        with _supervisor_lock:
            if _supervisor_runtime is supervisor:
                _supervisor_runtime = None


def stop_openclaw_supervisor_service() -> Dict[str, Any]:
    """Request shutdown for the broker-managed OpenClaw supervisor service."""
    with _supervisor_lock:
        supervisor = _supervisor_runtime
        if supervisor is None:
            return {"status": "not_running"}

        supervisor.stop()
        _supervisor_status["status"] = "stopping"
        return {
            "status": "stopping",
            "repo_root": _supervisor_status.get("repo_root", ""),
        }
