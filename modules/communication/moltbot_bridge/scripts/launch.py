#!/usr/bin/env python3
"""Broker-managed OpenClaw resident service launcher."""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_runtime_lock = threading.RLock()
_runtime_server: Any = None
_runtime_status: Dict[str, Any] = {}


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
