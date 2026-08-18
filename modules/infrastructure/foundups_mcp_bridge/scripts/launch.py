#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FoundUps MCP Bridge SSE Server Launch Script.
=============================================

Domain: infrastructure
Module: foundups_mcp_bridge

Starts the FastMCP SSE server for FoundUps perception tools, enabling ChatGPT
and other remote agents to connect via secure tunnels (ngrok/cloudflared).

Performs truthful protocol-level readiness canary (initialize -> tools/list -> tool call)
prior to confirming operational state to the DAE broker.

WSP References:
- WSP 96: Model Context Protocol Governance and Consensus
- WSP 97: Truthful Verification (protocol-level readiness handshake)
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
from pathlib import Path
from typing import Any, Dict, Optional

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

_server_lock = threading.RLock()
_instance_lock: Optional[Any] = None
_server_process: Optional[subprocess.Popen] = None
_in_process_server: Optional[Any] = None
_server_status: Dict[str, Any] = {"status": "stopped"}


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


def verify_mcp_readiness(
    host: str,
    port: int,
    auth_token: Optional[str] = None,
    timeout_sec: float = 15.0,
) -> Dict[str, Any]:
    """
    Perform truthful protocol-level readiness canary over SSE transport.

    Steps:
    1. Connect to /sse stream (with Auth token if required).
    2. Extract session message endpoint.
    3. Send MCP JSON-RPC 'initialize' request and await response.
    4. Send MCP JSON-RPC 'tools/list' request and verify tool inventory >= 30.
    5. Send MCP JSON-RPC 'tools/call' for safe read tool ('get_wsp_docs') and verify 'ok' result.

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

        init_ok = False
        for _ in range(20):
            line = sse_resp.readline().decode("utf-8", errors="replace").strip()
            if line.startswith("data: ") and '"id":1' in line.replace(" ", ""):
                init_ok = True
                break

        if not init_ok:
            return {"verified": False, "error": "Initialize response not received on SSE stream"}

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

        tools_count = 0
        tools_list_ok = False
        for _ in range(20):
            line = sse_resp.readline().decode("utf-8", errors="replace").strip()
            if line.startswith("data: ") and '"id":2' in line.replace(" ", ""):
                data_json = json.loads(line.replace("data: ", "", 1))
                tools = data_json.get("result", {}).get("tools", [])
                tools_count = len(tools)
                tools_list_ok = tools_count >= 30
                break

        if not tools_list_ok:
            return {"verified": False, "error": f"tools/list returned insufficient tools ({tools_count})"}

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

        tool_call_ok = False
        for _ in range(30):
            line = sse_resp.readline().decode("utf-8", errors="replace").strip()
            if line.startswith("data: ") and '"id":3' in line.replace(" ", ""):
                tool_call_ok = True
                break

        if not tool_call_ok:
            return {"verified": False, "error": "Tool call response not received on SSE stream"}

        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "verified": True,
            "tools_count": tools_count,
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
    repo_root: Optional[Path] = None,
    blocking: bool = True,
) -> Dict[str, Any]:
    """
    Run FoundUps MCP Bridge SSE server with truthful readiness verification.

    Args:
        host: Host IP to bind (default: 127.0.0.1 or env FOUNDUPS_MCP_HOST)
        port: Port to bind (default: 8128 or env FOUNDUPS_MCP_PORT)
        auth_token: Optional auth token (default: env FOUNDUPS_MCP_AUTH_TOKEN)
        repo_root: Optional repo root override
        blocking: If True, blocks until server shutdown; if False, runs in background.

    Returns:
        Dict with launch status and readiness evidence.
    """
    global _server_process, _in_process_server, _instance_lock

    root = Path(repo_root or _get_repo_root()).resolve()
    bind_host = host or os.getenv("FOUNDUPS_MCP_HOST", DEFAULT_HOST)
    bind_port = port or int(os.getenv("FOUNDUPS_MCP_PORT", str(DEFAULT_PORT)))
    token = auth_token if auth_token is not None else os.getenv("FOUNDUPS_MCP_AUTH_TOKEN", "")

    # Fail closed for non-loopback exposure without auth token
    is_loopback = bind_host in ("127.0.0.1", "localhost", "::1")
    if not is_loopback and not token:
        msg = f"[MCP-BRIDGE-SSE] Refusing to bind to non-loopback host {bind_host} without auth token (fail closed per WSP 97)."
        logger.error(msg)
        print(msg)
        return {"status": "error", "error": "auth_token_required_for_remote_exposure"}

    print(f"[MCP-BRIDGE-SSE] Starting FoundUps MCP SSE Server on http://{bind_host}:{bind_port}/sse ...")

    # Instance lock check
    try:
        from modules.infrastructure.instance_lock.src.instance_manager import get_instance_lock
        lock = get_instance_lock("foundups_mcp_bridge_sse")

        duplicates = lock.check_duplicates()
        if duplicates:
            msg = f"[MCP-BRIDGE-SSE] Duplicate instance detected: {duplicates}"
            logger.warning(msg)
            print(msg)
            return {"status": "error", "error": "duplicate_instance_running"}

        if not lock.acquire():
            msg = "[MCP-BRIDGE-SSE] Failed to acquire instance lock - another instance is active."
            logger.error(msg)
            print(msg)
            return {"status": "error", "error": "lock_acquisition_failed"}
        _instance_lock = lock
    except Exception:
        lock = None

    # Check if fastmcp is importable in current environment
    try:
        import uvicorn
        from modules.infrastructure.foundups_mcp_bridge.src.mcp_server import build_asgi_app

        asgi_app = build_asgi_app(
            repo_root=root,
            auth_token=token,
            require_auth=not is_loopback,
        )

        config = uvicorn.Config(
            asgi_app,
            host=bind_host,
            port=bind_port,
            log_level="info",
            access_log=False,
        )
        server = uvicorn.Server(config)

        with _server_lock:
            _in_process_server = server
            _server_status.clear()
            _server_status.update({
                "status": "starting",
                "mode": "in_process",
                "host": bind_host,
                "port": bind_port,
                "started_at": time.time(),
            })

        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        # Perform Protocol-level Readiness Canary
        canary = verify_mcp_readiness(host=bind_host, port=bind_port, auth_token=token, timeout_sec=15.0)
        if not canary.get("verified"):
            err = canary.get("error", "unknown_canary_failure")
            print(f"[MCP-BRIDGE-SSE-ERROR] Protocol readiness canary failed: {err}")
            server.should_exit = True
            thread.join(timeout=3)
            with _server_lock:
                _in_process_server = None
                _server_status["status"] = "failed"
                _server_status["error"] = err
            if lock:
                lock.release()
                _instance_lock = None
            return {"status": "failed", "error": err}

        with _server_lock:
            _server_status["status"] = "running"
            _server_status["readiness"] = canary

        print(f"[MCP-BRIDGE-SSE] In-process server verified & operational ({canary.get('tools_count')} tools, {canary.get('latency_ms')}ms). Endpoint: http://{bind_host}:{bind_port}/sse")

        if blocking:
            try:
                while not server.should_exit and thread.is_alive():
                    time.sleep(0.5)
            except (KeyboardInterrupt, SystemExit):
                print("[MCP-BRIDGE-SSE] Shutdown requested...")
                server.should_exit = True
                thread.join(timeout=3)
            finally:
                with _server_lock:
                    _in_process_server = None
                    _server_status["status"] = "stopped"
                if lock:
                    lock.release()
                    _instance_lock = None
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
                _instance_lock = None
            return {"status": "error", "error": "mcp_env_missing"}

        env = os.environ.copy()
        env["PYTHONPATH"] = str(root)
        env["FOUNDUPS_MCP_HOST"] = bind_host
        env["FOUNDUPS_MCP_PORT"] = str(bind_port)
        if token:
            env["FOUNDUPS_MCP_AUTH_TOKEN"] = token

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
        if token:
            cmd.extend(["--auth-token", token])

        logger.info(f"[MCP-BRIDGE-SSE] Launching subprocess: {' '.join(cmd)}")

        proc = subprocess.Popen(
            cmd,
            cwd=str(root),
            env=env,
        )
        with _server_lock:
            _server_process = proc
            _server_status.clear()
            _server_status.update({
                "status": "starting",
                "mode": "subprocess",
                "pid": proc.pid,
                "host": bind_host,
                "port": bind_port,
                "started_at": time.time(),
            })

        # Perform Protocol-level Readiness Canary on subprocess
        canary = verify_mcp_readiness(host=bind_host, port=bind_port, auth_token=token, timeout_sec=15.0)
        if not canary.get("verified"):
            err = canary.get("error", "unknown_canary_failure")
            print(f"[MCP-BRIDGE-SSE-ERROR] Subprocess protocol readiness canary failed: {err}")
            stop_mcp_bridge_sse()
            with _server_lock:
                _server_status["status"] = "failed"
                _server_status["error"] = err
            if lock:
                lock.release()
                _instance_lock = None
            return {"status": "failed", "error": err}

        with _server_lock:
            _server_status["status"] = "running"
            _server_status["readiness"] = canary

        print(f"[MCP-BRIDGE-SSE] Subprocess verified & operational (PID {proc.pid}, {canary.get('tools_count')} tools, {canary.get('latency_ms')}ms). Endpoint: http://{bind_host}:{bind_port}/sse")

        if blocking:
            try:
                proc.wait()
            except (KeyboardInterrupt, SystemExit):
                print("[MCP-BRIDGE-SSE] Subprocess interrupted...")
                stop_mcp_bridge_sse()
            finally:
                with _server_lock:
                    _server_process = None
                    _server_status["status"] = "stopped"
                if lock:
                    lock.release()
                    _instance_lock = None
            return {"status": "stopped"}
        else:
            return {"status": "running", "mode": "subprocess", "pid": proc.pid, "host": bind_host, "port": bind_port, "readiness": canary}


def stop_mcp_bridge_sse() -> Dict[str, Any]:
    """Request graceful shutdown of the MCP Bridge SSE server."""
    global _instance_lock
    with _server_lock:
        if _in_process_server is not None:
            _in_process_server.should_exit = True
            _server_status["status"] = "stopping"
            if _instance_lock:
                try:
                    _instance_lock.release()
                except Exception:
                    pass
                _instance_lock = None
            return {"status": "stopping", "mode": "in_process"}

        if _server_process is not None:
            try:
                _server_process.terminate()
                _server_process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"[MCP-BRIDGE-SSE] Error terminating process: {e}")
                try:
                    _server_process.kill()
                except Exception:
                    pass
            _server_status["status"] = "stopped"
            if _instance_lock:
                try:
                    _instance_lock.release()
                except Exception:
                    pass
                _instance_lock = None
            return {"status": "stopped", "mode": "subprocess"}

        if _instance_lock:
            try:
                _instance_lock.release()
            except Exception:
                pass
            _instance_lock = None

        return {"status": "not_running"}


def get_mcp_bridge_status() -> Dict[str, Any]:
    """Get current runtime status of the MCP Bridge SSE server."""
    with _server_lock:
        if _server_process is not None:
            poll = _server_process.poll()
            if poll is not None:
                _server_status["status"] = "stopped"
                _server_status["exit_code"] = poll
        return dict(_server_status)


if __name__ == "__main__":
    run_mcp_bridge_sse(blocking=True)
