#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FoundUps MCP Bridge SSE Server Launch Script.
=============================================

Domain: infrastructure
Module: foundups_mcp_bridge

Starts the FastMCP SSE server for FoundUps perception tools, enabling ChatGPT
and other remote agents to connect via secure tunnels (ngrok/cloudflared).

Enforces strict concurrency contract:
- instance lock held <=> this process owns the live MCP server
- fail-closed: startup aborted if instance lock cannot be acquired
- centralized termination: signal -> bounded wait -> confirm dead -> release lock exactly once
- idempotent stop with truthful STOP_TIMEOUT reporting (lock not released on timeout)
- fail-closed remote authentication (secret passed via env only; never argv/logs)
- truthful protocol-level readiness canary (initialize -> tools/list validation -> tool call parsing)

WSP References:
- WSP 96: Model Context Protocol Governance and Consensus
- WSP 97: Truthful Verification (protocol readiness canary & perception boundaries)
- WSP 80: Cube-Level DAE Orchestration
- WSP 27: Universal DAE Architecture
"""

from __future__ import annotations

import io
import json
import logging
import os
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

# === UTF-8 ENFORCEMENT (WSP 90) ===
if __name__ == "__main__" and sys.platform.startswith("win"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        pass
# === END UTF-8 ENFORCEMENT ===

logger = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8128

REQUIRED_CANARY_TOOLS: Set[str] = {
    "get_repo_tree",
    "read_file",
    "get_wsp_docs",
    "get_reddog_state",
    "get_reddog_analysis_context",
}

FORBIDDEN_CANARY_TOOLS: Set[str] = {
    "coordinate_mission",
    "spawn_agent_team",
    "trigger_skill",
    "write_file",
    "create_branch",
    "create_pr",
}


@dataclass
class MCPRuntimeHandle:
    """Encapsulates all runtime handles and locks for an active MCP server instance."""
    mode: str  # 'in_process' or 'subprocess'
    host: str
    port: int
    started_at: float
    lock: Optional[Any] = None
    server: Optional[Any] = None  # uvicorn.Server for in_process
    thread: Optional[threading.Thread] = None  # thread for in_process
    proc: Optional[subprocess.Popen] = None  # Popen for subprocess
    readiness: Dict[str, Any] = field(default_factory=dict)

    def is_alive(self) -> bool:
        """Check if underlying server thread or subprocess is currently active."""
        if self.mode == "in_process":
            return bool(self.thread and self.thread.is_alive())
        elif self.mode == "subprocess":
            return bool(self.proc and self.proc.poll() is None)
        return False


_state_lock = threading.RLock()
_active_runtime: Optional[MCPRuntimeHandle] = None


def _get_repo_root() -> Path:
    """Resolve repository root."""
    return Path(__file__).resolve().parent.parent.parent.parent.parent


def _get_mcp_env_python(repo_root: Path) -> Path:
    """Find python executable in foundups-mcp-env."""
    if sys.platform.startswith("win"):
        python_exe = repo_root / "foundups-mcp-p1" / "foundups-mcp-env" / "Scripts" / "python.exe"
    else:
        python_exe = repo_root / "foundups-mcp-p1" / "foundups-mcp-env" / "bin" / "python"
    return python_exe


def _terminate_runtime(handle: Optional[MCPRuntimeHandle], timeout_sec: float = 5.0) -> Tuple[bool, str]:
    """
    Centralized shutdown helper enforcing the strict lifecycle contract:
    1. Signal shutdown to server / process.
    2. Bounded wait for thread exit or process exit.
    3. Confirm dead. If still running, return failure without releasing lock.
    4. Release lock exactly once.
    5. Return success status.
    """
    if handle is None:
        return True, "already_stopped"

    # 1. Signal shutdown
    if handle.mode == "in_process" and handle.server is not None:
        handle.server.should_exit = True
        if handle.thread is not None:
            handle.thread.join(timeout=timeout_sec)
            if handle.thread.is_alive():
                logger.error("[MCP-BRIDGE-SSE] In-process server thread did not exit within timeout")
                return False, "stop_timeout_still_running"

    elif handle.mode == "subprocess" and handle.proc is not None:
        try:
            handle.proc.terminate()
            handle.proc.wait(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            logger.warning("[MCP-BRIDGE-SSE] Subprocess did not terminate gracefully; sending kill signal")
            try:
                handle.proc.kill()
                handle.proc.wait(timeout=2.0)
            except Exception as exc:
                logger.error(f"[MCP-BRIDGE-SSE] Failed to kill subprocess: {exc}")
                return False, "stop_timeout_still_running"
        except Exception as exc:
            logger.error(f"[MCP-BRIDGE-SSE] Subprocess termination error: {exc}")
            return False, str(exc)

    # 2. Confirm dead
    if handle.is_alive():
        return False, "stop_timeout_still_running"

    # 3. Release lock exactly once
    if handle.lock:
        try:
            handle.lock.release()
        except Exception as exc:
            logger.debug(f"[MCP-BRIDGE-SSE] Lock release notice: {exc}")
        handle.lock = None

    return True, "stopped"


def verify_mcp_readiness(
    host: str,
    port: int,
    auth_token: Optional[str] = None,
    timeout_sec: float = 15.0,
) -> Dict[str, Any]:
    """
    Perform truthful protocol-level readiness canary over SSE transport.

    Steps:
    1. Connect to /sse stream (with Auth header if required).
    2. Extract session message endpoint.
    3. Send MCP JSON-RPC 'initialize' request -> verify response & capabilities.
    4. Send MCP JSON-RPC 'tools/list' request -> verify required read tools present and mutation tools absent.
    5. Send MCP JSON-RPC 'tools/call' for 'get_wsp_docs' -> parse result and assert inner status == 'ok'.

    Args:
        host: Server host
        port: Server port
        auth_token: Optional Bearer auth token
        timeout_sec: Maximum time to wait for complete verification

    Returns:
        Dict with verification results ('verified': True/False, metrics, error).
    """
    start_time = time.time()
    deadline = start_time + timeout_sec

    headers = {"Accept": "text/event-stream"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    sse_url = f"http://{host}:{port}/sse"

    # Step 1: Connect to SSE
    sse_resp = None
    msg_endpoint = None
    last_err = ""

    while time.time() < deadline:
        try:
            req = urllib.request.Request(sse_url, headers=headers)
            sse_resp = urllib.request.urlopen(req, timeout=3.0)
            if sse_resp.status == 200:
                for _ in range(10):
                    line = sse_resp.readline().decode("utf-8", errors="replace").strip()
                    if line.startswith("data: "):
                        msg_endpoint = line.replace("data: ", "").strip()
                        break
                if msg_endpoint:
                    break
        except Exception as exc:
            last_err = str(exc)
            time.sleep(0.5)

    if not msg_endpoint or not sse_resp:
        return {
            "verified": False,
            "error": f"Failed to establish SSE session within {timeout_sec}s: {last_err}",
        }

    try:
        msg_url = f"http://{host}:{port}{msg_endpoint}"
        post_headers = {"Content-Type": "application/json"}
        if auth_token:
            post_headers["Authorization"] = f"Bearer {auth_token}"

        # Step 2: Initialize
        init_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "FoundUps-Canary", "version": "1.0.0"},
            },
        }).encode("utf-8")

        req = urllib.request.Request(msg_url, data=init_req, headers=post_headers)
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status not in (200, 202):
                return {"verified": False, "error": f"Initialize POST returned {resp.status}"}

        init_data = None
        for _ in range(20):
            line = sse_resp.readline().decode("utf-8", errors="replace").strip()
            if line.startswith("data: ") and '"id":1' in line.replace(" ", ""):
                try:
                    init_data = json.loads(line.replace("data: ", "", 1))
                except Exception:
                    pass
                break

        if not init_data or "error" in init_data or "result" not in init_data:
            return {"verified": False, "error": f"Invalid initialize response: {init_data}"}

        # Step 3: Tools List
        list_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }).encode("utf-8")

        req = urllib.request.Request(msg_url, data=list_req, headers=post_headers)
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status not in (200, 202):
                return {"verified": False, "error": f"tools/list POST returned {resp.status}"}

        tools_data = None
        for _ in range(20):
            line = sse_resp.readline().decode("utf-8", errors="replace").strip()
            if line.startswith("data: ") and '"id":2' in line.replace(" ", ""):
                try:
                    tools_data = json.loads(line.replace("data: ", "", 1))
                except Exception:
                    pass
                break

        if not tools_data or "error" in tools_data or "result" not in tools_data:
            return {"verified": False, "error": f"Invalid tools/list response: {tools_data}"}

        tools_list = tools_data.get("result", {}).get("tools", [])
        tool_names = {t.get("name") for t in tools_list if isinstance(t, dict)}

        # Verify required perception tools exist
        missing_required = REQUIRED_CANARY_TOOLS - tool_names
        if missing_required:
            return {"verified": False, "error": f"Missing required perception tools: {sorted(missing_required)}"}

        # Verify forbidden mutation tools are absent
        present_forbidden = FORBIDDEN_CANARY_TOOLS & tool_names
        if present_forbidden:
            return {"verified": False, "error": f"Disallowed mutation tools exposed: {sorted(present_forbidden)}"}

        # Step 4: Tool Call Canary (get_wsp_docs - safe read tool)
        call_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_wsp_docs",
                "arguments": {},
            },
        }).encode("utf-8")

        req = urllib.request.Request(msg_url, data=call_req, headers=post_headers)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            if resp.status not in (200, 202):
                return {"verified": False, "error": f"tools/call POST returned {resp.status}"}

        call_data = None
        for _ in range(30):
            line = sse_resp.readline().decode("utf-8", errors="replace").strip()
            if line.startswith("data: ") and '"id":3' in line.replace(" ", ""):
                try:
                    call_data = json.loads(line.replace("data: ", "", 1))
                except Exception:
                    pass
                break

        if not call_data or "error" in call_data or "result" not in call_data:
            return {"verified": False, "error": f"Tool call error response: {call_data}"}

        # Parse and verify inner bridge result envelope
        result_content = call_data.get("result", {}).get("content", [])
        inner_status_ok = False
        for item in result_content:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    inner_json = json.loads(item.get("text", "{}"))
                    if inner_json.get("status") == "ok" and "wsp_docs" in inner_json.get("data", {}):
                        inner_status_ok = True
                        break
                except Exception:
                    pass

        if not inner_status_ok:
            return {"verified": False, "error": f"Tool call returned invalid or error payload: {call_data}"}

        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "verified": True,
            "tools_count": len(tool_names),
            "tool_names": sorted(tool_names),
            "latency_ms": elapsed_ms,
        }

    except Exception as exc:
        return {"verified": False, "error": str(exc)}
    finally:
        try:
            sse_resp.close()
        except Exception:
            pass


def run_mcp_bridge_sse(
    host: Optional[str] = None,
    port: Optional[int] = None,
    auth_token: Optional[str] = None,
    require_auth: Optional[bool] = None,
    repo_root: Optional[Path] = None,
    blocking: bool = True,
) -> Dict[str, Any]:
    """
    Run FoundUps MCP Bridge SSE server with truthful readiness verification.

    Maintains invariant: instance lock held <=> this process owns the live MCP server.
    Fails closed if instance lock cannot be acquired or if remote exposure lacks auth.

    Args:
        host: Host IP to bind (default: 127.0.0.1 or env FOUNDUPS_MCP_HOST)
        port: Port to bind (default: 8128 or env FOUNDUPS_MCP_PORT)
        auth_token: Optional auth token (default: env FOUNDUPS_MCP_AUTH_TOKEN)
        require_auth: Explicit flag to enforce authentication (default: True if tunnel/remote/token configured)
        repo_root: Optional repo root override
        blocking: If True, blocks until server shutdown; if False, runs in background.

    Returns:
        Dict with launch status and readiness evidence.
    """
    global _active_runtime

    root = Path(repo_root or _get_repo_root()).resolve()
    bind_host = host or os.getenv("FOUNDUPS_MCP_HOST", DEFAULT_HOST)
    bind_port = port or int(os.getenv("FOUNDUPS_MCP_PORT", str(DEFAULT_PORT)))
    token = auth_token if auth_token is not None else os.getenv("FOUNDUPS_MCP_AUTH_TOKEN", "")

    # Determine auth enforcement: fail closed for remote exposure or explicit tunnel mode
    is_loopback = bind_host in ("127.0.0.1", "localhost", "::1")
    is_tunnel_mode = os.getenv("FOUNDUPS_MCP_TUNNEL_MODE", "0") == "1"

    if require_auth is not None:
        auth_enforced = require_auth
    else:
        # Default: require auth if token present, non-loopback, or tunnel mode
        auth_enforced = bool(token or is_tunnel_mode or not is_loopback)

    if auth_enforced and not token:
        msg = (
            f"[MCP-BRIDGE-SSE] Refusing to start MCP server without auth token when "
            f"auth enforcement is enabled (host={bind_host}, tunnel_mode={is_tunnel_mode}). "
            f"Failing closed per WSP 97."
        )
        logger.error(msg)
        print(msg)
        return {"status": "error", "error": "auth_token_required_for_remote_exposure"}

    with _state_lock:
        if _active_runtime is not None and _active_runtime.is_alive():
            msg = f"[MCP-BRIDGE-SSE] MCP server is already running on {_active_runtime.host}:{_active_runtime.port}"
            logger.warning(msg)
            print(msg)
            return {
                "status": "running",
                "already_running": True,
                "host": _active_runtime.host,
                "port": _active_runtime.port,
            }

    print(f"[MCP-BRIDGE-SSE] Starting FoundUps MCP SSE Server on http://{bind_host}:{bind_port}/sse ...")

    # Acquire instance lock (fail-closed if unavailable)
    try:
        from modules.infrastructure.instance_lock.src.instance_manager import get_instance_lock
        lock = get_instance_lock("foundups_mcp_bridge_sse")

        duplicates = lock.check_duplicates()
        if duplicates:
            msg = f"[MCP-BRIDGE-SSE] Duplicate instance detected: {duplicates} (failing closed per WSP 97)."
            logger.error(msg)
            print(msg)
            return {"status": "error", "error": "duplicate_instance_running"}

        if not lock.acquire():
            msg = "[MCP-BRIDGE-SSE] Failed to acquire instance lock - another instance is active."
            logger.error(msg)
            print(msg)
            return {"status": "error", "error": "lock_acquisition_failed"}
    except Exception as exc:
        msg = f"[MCP-BRIDGE-SSE] Instance lock system failure: {exc} (failing closed per WSP 97)."
        logger.error(msg)
        print(msg)
        return {"status": "error", "error": "lock_system_unavailable"}

    # Check if fastmcp is importable in current environment
    try:
        import uvicorn
        from modules.infrastructure.foundups_mcp_bridge.src.mcp_server import build_asgi_app

        asgi_app = build_asgi_app(
            repo_root=root,
            auth_token=token,
            require_auth=auth_enforced,
        )

        config = uvicorn.Config(
            asgi_app,
            host=bind_host,
            port=bind_port,
            log_level="info",
            access_log=False,
        )
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        handle = MCPRuntimeHandle(
            mode="in_process",
            host=bind_host,
            port=bind_port,
            started_at=time.time(),
            lock=lock,
            server=server,
            thread=thread,
        )

        with _state_lock:
            _active_runtime = handle

        # Perform Protocol-level Readiness Canary
        canary = verify_mcp_readiness(host=bind_host, port=bind_port, auth_token=token, timeout_sec=15.0)
        if not canary.get("verified"):
            err = canary.get("error", "unknown_canary_failure")
            print(f"[MCP-BRIDGE-SSE-ERROR] Protocol readiness canary failed: {err}")
            _terminate_runtime(handle, timeout_sec=3.0)
            with _state_lock:
                _active_runtime = None
            return {"status": "failed", "error": err}

        handle.readiness = canary
        print(f"[MCP-BRIDGE-SSE] In-process server verified & operational ({canary.get('tools_count')} allowlisted tools, {canary.get('latency_ms')}ms). Endpoint: http://{bind_host}:{bind_port}/sse")

        if blocking:
            try:
                while not server.should_exit and thread.is_alive():
                    time.sleep(0.5)
            except (KeyboardInterrupt, SystemExit):
                print("[MCP-BRIDGE-SSE] Shutdown requested...")
            finally:
                _terminate_runtime(handle, timeout_sec=5.0)
                with _state_lock:
                    _active_runtime = None
                print("[MCP-BRIDGE-SSE] Server stopped.")
            return {"status": "stopped"}
        else:
            return {"status": "running", "mode": "in_process", "host": bind_host, "port": bind_port, "readiness": canary}

    except ImportError:
        # FastMCP not in current venv -> Launch subprocess using foundups-mcp-env
        python_exe = _get_mcp_env_python(root)
        if not python_exe.exists():
            msg = f"[MCP-BRIDGE-SSE] Neither fastmcp in current Python nor foundups-mcp-env found at: {python_exe}"
            logger.error(msg)
            print(msg)
            if lock:
                lock.release()
            return {"status": "error", "error": "mcp_env_missing"}

        env = os.environ.copy()
        env["PYTHONPATH"] = str(root)
        env["FOUNDUPS_MCP_HOST"] = bind_host
        env["FOUNDUPS_MCP_PORT"] = str(bind_port)
        if token:
            env["FOUNDUPS_MCP_AUTH_TOKEN"] = token
        if auth_enforced:
            env["FOUNDUPS_MCP_REQUIRE_AUTH"] = "1"

        # Notice: auth_token is passed strictly via environment, NEVER on argv or logs
        cmd = [
            str(python_exe),
            "-m",
            "modules.infrastructure.foundups_mcp_bridge.src.mcp_server",
            "--transport",
            "sse",
            "--host",
            bind_host,
            "--port",
            str(bind_port),
        ]

        logger.info(f"[MCP-BRIDGE-SSE] Launching subprocess on {bind_host}:{bind_port}")

        proc = subprocess.Popen(
            cmd,
            cwd=str(root),
            env=env,
        )

        handle = MCPRuntimeHandle(
            mode="subprocess",
            host=bind_host,
            port=bind_port,
            started_at=time.time(),
            lock=lock,
            proc=proc,
        )

        with _state_lock:
            _active_runtime = handle

        # Perform Protocol-level Readiness Canary on subprocess
        canary = verify_mcp_readiness(host=bind_host, port=bind_port, auth_token=token, timeout_sec=15.0)
        if not canary.get("verified"):
            err = canary.get("error", "unknown_canary_failure")
            print(f"[MCP-BRIDGE-SSE-ERROR] Subprocess protocol readiness canary failed: {err}")
            _terminate_runtime(handle, timeout_sec=3.0)
            with _state_lock:
                _active_runtime = None
            return {"status": "failed", "error": err}

        handle.readiness = canary
        print(f"[MCP-BRIDGE-SSE] Subprocess verified & operational (PID {proc.pid}, {canary.get('tools_count')} allowlisted tools, {canary.get('latency_ms')}ms). Endpoint: http://{bind_host}:{bind_port}/sse")

        if blocking:
            try:
                proc.wait()
            except (KeyboardInterrupt, SystemExit):
                print("[MCP-BRIDGE-SSE] Subprocess interrupted...")
            finally:
                _terminate_runtime(handle, timeout_sec=5.0)
                with _state_lock:
                    _active_runtime = None
            return {"status": "stopped"}
        else:
            return {"status": "running", "mode": "subprocess", "pid": proc.pid, "host": bind_host, "port": bind_port, "readiness": canary}


def stop_mcp_bridge_sse(timeout_sec: float = 5.0) -> Dict[str, Any]:
    """
    Request graceful, verified shutdown of the active MCP Bridge SSE server.

    Idempotent stop contract:
    - If no active runtime -> return {"status": "already_stopped"}
    - If active runtime -> signal exit, bounded wait for termination, verify port/server gone, release lock exactly once, clear global state.
    - If shutdown times out -> do NOT release lock; return {"status": "error", "error": "stop_timeout_still_running"}.
    """
    global _active_runtime

    with _state_lock:
        handle = _active_runtime
        if handle is None or not handle.is_alive():
            if handle and handle.lock:
                try:
                    handle.lock.release()
                except Exception:
                    pass
            _active_runtime = None
            return {"status": "already_stopped"}

    success, message = _terminate_runtime(handle, timeout_sec=timeout_sec)
    if not success:
        return {"status": "error", "error": message}

    with _state_lock:
        _active_runtime = None

    print("[MCP-BRIDGE-SSE] Verified clean shutdown.")
    return {"status": "stopped"}


def get_mcp_bridge_status() -> Dict[str, Any]:
    """Get current truthful runtime status of the MCP Bridge SSE server."""
    global _active_runtime
    with _state_lock:
        handle = _active_runtime
        if handle is None:
            return {"status": "stopped", "running": False}

        alive = handle.is_alive()
        if not alive:
            if handle.lock:
                try:
                    handle.lock.release()
                except Exception:
                    pass
                handle.lock = None
            _active_runtime = None
            return {"status": "stopped", "running": False}

        status_dict: Dict[str, Any] = {
            "status": "running",
            "running": True,
            "mode": handle.mode,
            "host": handle.host,
            "port": handle.port,
            "started_at": handle.started_at,
            "readiness": handle.readiness,
        }
        if handle.proc:
            status_dict["pid"] = handle.proc.pid
        return status_dict


if __name__ == "__main__":
    run_mcp_bridge_sse(blocking=True)
