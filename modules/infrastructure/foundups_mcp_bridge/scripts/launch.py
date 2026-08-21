#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FoundUps MCP Bridge Streamable HTTP Launch Script.
==================================================

Domain: infrastructure
Module: foundups_mcp_bridge

Starts the loopback FastMCP Streamable HTTP server for FoundUps perception
tools. Public HTTPS/OAuth remains the responsibility of a Secure MCP Tunnel.

Enforces strict concurrency contract:
- instance lock held <=> this process owns the live MCP server
- fail-closed: startup aborted if instance lock cannot be acquired
- centralized termination: signal -> bounded wait -> confirm dead -> release lock exactly once
- failure propagation: _active_runtime and lock retained if termination times out (never cleared)
- loopback-only binding; optional static bearer is a local development defense
- truthful protocol-level readiness canary (initialize -> tools/list validation -> tool call parsing)

WSP References:
- WSP 96: Model Context Protocol Governance and Consensus
- WSP 97: Truthful Verification (protocol readiness canary & perception boundaries)
- WSP 80: Cube-Level DAE Orchestration
- WSP 27: Universal DAE Architecture
"""

from __future__ import annotations

import io
import asyncio
import json
import logging
import math
import os
import re
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

REQUIRED_CANARY_TOOLS: Set[str] = {"holo_query_bundle"}

FORBIDDEN_CANARY_TOOLS: Set[str] = {
    "get_repo_tree",
    "read_file",
    "get_wsp_docs",
    "get_module_docs",
    "get_interface_doc",
    "get_test_docs",
    "get_modlog",
    "get_violations",
    "get_mission_history",
    "get_pattern_memory",
    "get_overseer_status",
    "get_coordination_state",
    "get_known_failure_patterns",
    "get_module_dependencies",
    "get_reverse_dependencies",
    "coordinate_mission",
    "spawn_agent_team",
    "trigger_skill",
    "write_file",
    "create_branch",
    "create_pr",
}

MCP_RUNTIME_VERSIONS = {
    "fastmcp": "2.13.0.2",
    "mcp": "1.20.0",
    "pydantic": "2.12.3",
    "uvicorn": "0.38.0",
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


@dataclass(frozen=True)
class MCPLaunchOptions:
    """Validated inputs for one loopback HTTP subprocess lifecycle."""

    root: Path
    host: str
    port: int
    token: str
    auth_enforced: bool


_state_lock = threading.RLock()
_active_runtime: Optional[MCPRuntimeHandle] = None

_CHILD_ENV_ALLOWLIST = frozenset({
    "COMSPEC", "HOME", "HOMEDRIVE", "HOMEPATH", "LANG", "LC_ALL",
    "LC_CTYPE", "NUMBER_OF_PROCESSORS", "OS", "PATH", "PATHEXT",
    "PROCESSOR_ARCHITECTURE", "SYSTEMROOT", "TEMP", "TMP", "TMPDIR",
    "TZ", "USERPROFILE", "WINDIR",
})


def _closed_child_base_env() -> dict[str, str]:
    """Copy only explicitly required OS/runtime fields into a child."""
    return {
        key: value for key, value in os.environ.items()
        if key.upper() in _CHILD_ENV_ALLOWLIST
    }


def _get_repo_root() -> Path:
    """Resolve repository root."""
    return Path(__file__).resolve().parent.parent.parent.parent.parent


def _get_mcp_env_python(repo_root: Path) -> Path:
    """Resolve one file-proven capable MCP interpreter across worktrees."""
    from holo_index.freshness_receipt import _git_ref_roots, _resolve_git_dir

    root = Path(repo_root).resolve()
    git_dir = _resolve_git_dir(root)
    common_root = _git_ref_roots(git_dir)[-1].parent if git_dir else root
    executable = Path("Scripts/python.exe") if sys.platform.startswith("win") else Path("bin/python")
    ordered = (
        Path(sys.executable),
        common_root / "foundups-mcp-p1" / "foundups-mcp-env" / executable,
        root / "foundups-mcp-p1" / "foundups-mcp-env" / executable,
    )
    candidates = tuple(dict.fromkeys(
        candidate.resolve(strict=False) for candidate in ordered
    ))
    for candidate in candidates:
        if _mcp_python_capable(candidate):
            return candidate.resolve()
    return candidates[-1]


def _mcp_python_capable(candidate: Path) -> bool:
    if not candidate.is_file() or candidate.is_symlink():
        return False
    code = (
        "import importlib.metadata as metadata,json,fastmcp,mcp,pydantic,uvicorn;"
        "names=('fastmcp','mcp','pydantic','uvicorn');"
        "print(json.dumps({name:metadata.version(name) for name in names},"
        "sort_keys=True,separators=(',',':')))"
    )
    try:
        result = subprocess.run(
            [str(candidate), "-I", "-c", code], capture_output=True,
            text=True, timeout=5.0, check=False, env=_closed_child_base_env(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    expected = json.dumps(MCP_RUNTIME_VERSIONS, sort_keys=True, separators=(",", ":"))
    return result.returncode == 0 and result.stdout.strip() == expected


def _mcp_runtime_python(candidate: Path) -> tuple[Path, Path | None]:
    """Bypass the Windows venv launcher so the owned PID is the server PID."""
    if not sys.platform.startswith("win"):
        return candidate, None
    environment_root = candidate.parent.parent
    config = environment_root / "pyvenv.cfg"
    try:
        fields = {
            key.strip(): value.strip()
            for line in config.read_text(encoding="utf-8").splitlines()
            if "=" in line
            for key, value in (line.split("=", 1),)
        }
    except OSError:
        return candidate, None
    base = Path(str(fields.get("executable") or "").strip())
    packages = environment_root / "Lib" / "site-packages"
    if not base.is_absolute() or not base.is_file() or base.is_symlink() or not packages.is_dir():
        return candidate, None
    return base.resolve(), packages.resolve()


def _mcp_child_env(repo_root: Path, candidate: Path, token: str = "") -> tuple[Path, dict[str, str]]:
    executable, packages = _mcp_runtime_python(candidate)
    env = _closed_child_base_env()
    python_paths = [str(repo_root)]
    if packages is not None:
        python_paths.append(str(packages))
    env["PYTHONPATH"] = os.pathsep.join(python_paths)
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if token:
        env["FOUNDUPS_MCP_AUTH_TOKEN"] = token
    else:
        env.pop("FOUNDUPS_MCP_AUTH_TOKEN", None)
    return executable, env


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
                logger.error("[MCP-BRIDGE] In-process server thread did not exit within timeout")
                return False, "stop_timeout_still_running"

    elif handle.mode == "subprocess" and handle.proc is not None:
        try:
            if handle.proc.poll() is None:
                handle.proc.terminate()
                handle.proc.wait(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            logger.warning("[MCP-BRIDGE] Subprocess did not terminate gracefully; sending kill signal")
            try:
                handle.proc.kill()
                handle.proc.wait(timeout=2.0)
            except Exception as exc:
                logger.error(f"[MCP-BRIDGE] Failed to kill subprocess: {exc}")
                return False, "stop_timeout_still_running"
        except Exception as exc:
            logger.error(f"[MCP-BRIDGE] Subprocess termination error: {exc}")
            return False, str(exc)

    # 2. Confirm dead
    if handle.is_alive():
        return False, "stop_timeout_still_running"

    # 3. Release lock exactly once
    if handle.lock:
        try:
            handle.lock.release()
        except Exception as exc:
            logger.debug(f"[MCP-BRIDGE] Lock release notice: {exc}")
        handle.lock = None

    return True, "stopped"


def _mcp_call_payload_ok(call_result: Any) -> bool:
    candidates = [getattr(call_result, "structuredContent", None)]
    for item in getattr(call_result, "content", ()):
        text = getattr(item, "text", None)
        if not isinstance(text, str):
            continue
        try:
            candidates.append(json.loads(text))
        except json.JSONDecodeError:
            pass
    return any(_mcp_bundle_response_ok(value) for value in candidates)


def _mcp_bundle_response_ok(value: Any) -> bool:
    """Validate the complete lexical canary receipt and exact byte proof."""
    if type(value) is not dict or value.get("status") != "ok":
        return False
    data = value.get("data")
    if type(data) is not dict:
        return False
    byte_count = data.get("public_projection_bytes")
    required = (
        data.get("schema_version") == "reddog_holo_query_bundle_mcp.v1"
        and data.get("ok") is True
        and type(data.get("owner_attempts")) is int
        and data.get("owner_attempts") == 0
        and data.get("no_holoindex_reindex_performed") is True
        and data.get("public_projection_bounded") is True
        and type(byte_count) is int and 0 < byte_count <= 256 * 1024
    )
    if not required:
        return False
    try:
        encoded = json.dumps(
            data, ensure_ascii=True, sort_keys=True, allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        return False
    return len(encoded) == byte_count


def _remote_tool_names_exact(names: set[str]) -> bool:
    """Require the direct client to observe exactly the canonical surface."""
    return names == REQUIRED_CANARY_TOOLS and not (FORBIDDEN_CANARY_TOOLS & names)


async def _verify_streamable_http(url: str, headers: Dict[str, str], timeout: float):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(
        url, headers=headers, timeout=timeout, sse_read_timeout=timeout,
    ) as (read_stream, write_stream, _session_id):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            if not _remote_tool_names_exact(names):
                raise ValueError("MCP tool boundary mismatch")
            called = await session.call_tool("holo_query_bundle", {
                "query": "WSP memory bundle", "limit": 1,
                "retrieval_mode": "lexical", "bundle_only": True,
            })
            if not _mcp_call_payload_ok(called):
                raise ValueError("MCP safe tool call invalid")
            return names


def _verify_readiness_subprocess(
    repo_root: Path, host: str, port: int, token: str, timeout: float,
) -> Dict[str, Any]:
    interpreter = _get_mcp_env_python(repo_root)
    if not _mcp_python_capable(interpreter):
        return {"verified": False, "error": "mcp_capable_python_missing"}
    executable, env = _mcp_child_env(repo_root, interpreter, token)
    env["PYTHONWARNINGS"] = "ignore"
    command = [
        str(executable), "-m",
        "modules.infrastructure.foundups_mcp_bridge.scripts.readiness_once",
        "--host", host, "--port", str(port), "--timeout", str(timeout),
    ]
    try:
        result = subprocess.run(
            command, cwd=str(repo_root), env=env, capture_output=True,
            text=True, timeout=timeout + 5.0, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"verified": False, "error": type(exc).__name__}
    if result.returncode != 0:
        return {"verified": False, "error": "mcp_readiness_process_failed"}
    if len(result.stdout) > 262_144 or len(result.stderr) > 262_144:
        return {"verified": False, "error": "mcp_readiness_output_cap"}
    try:
        value = json.loads(result.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"verified": False, "error": "mcp_readiness_response_invalid"}
    return value if _readiness_schema_valid(value) else {
        "verified": False, "error": "mcp_readiness_response_invalid"}


def _readiness_schema_valid(value: Any) -> bool:
    from modules.infrastructure.foundups_mcp_bridge.src.mcp_server import (
        REMOTE_READ_ONLY_ALLOWLIST,
    )
    expected = sorted(REMOTE_READ_ONLY_ALLOWLIST)
    latency = value.get("latency_ms") if isinstance(value, dict) else None
    return bool(
        isinstance(value, dict)
        and value.get("verified") is True
        and value.get("transport") == "streamable_http"
        and value.get("route") == "/mcp"
        and value.get("legacy_sse_authoritative") is False
        and type(value.get("tools_count")) is int
        and value.get("tools_count") == len(expected)
        and value.get("tool_names") == expected
        and isinstance(latency, (int, float)) and not isinstance(latency, bool)
        and math.isfinite(float(latency)) and float(latency) >= 0.0
    )


def _exception_text(error: BaseException) -> str:
    """Flatten bounded exception groups while redacting bearer credentials."""
    messages: list[str] = []
    _flatten_exception(error, messages, set(), 0)
    return " | ".join(messages)[:4096]


def _flatten_exception(
    error: BaseException, messages: list[str], seen: set[int], depth: int,
) -> None:
    """Collect at most 32 exception nodes and four nesting levels."""
    if id(error) in seen or depth > 4 or len(messages) >= 32:
        return
    seen.add(id(error))
    status = _exception_http_status(error)
    raw = str(error)[:1024]
    safe = re.sub(r"(?i)bearer\s+[^\s,;\]}]+", "Bearer [REDACTED]", raw)
    label = f"HTTP {status}" if status is not None else type(error).__name__
    messages.append(f"{label}: {safe}"[:512])
    nested = getattr(error, "exceptions", ())
    if isinstance(nested, (tuple, list)):
        for item in nested:
            if isinstance(item, BaseException):
                _flatten_exception(item, messages, seen, depth + 1)


def _exception_http_status(error: BaseException) -> Optional[int]:
    """Project an integer HTTP status from common client exception shapes."""
    for candidate in (
        getattr(error, "status_code", None), getattr(error, "code", None),
        getattr(getattr(error, "response", None), "status_code", None),
    ):
        if type(candidate) is int and 100 <= candidate <= 599:
            return candidate
    return None


def verify_mcp_readiness(
    host: str, port: int, auth_token: Optional[str] = None,
    timeout_sec: float = 15.0, repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Verify Streamable HTTP initialize/list/safe-call against canonical `/mcp`."""
    try:
        import mcp  # noqa: F401
    except ImportError:
        return _verify_readiness_subprocess(
            Path(repo_root or _get_repo_root()).resolve(), host, port,
            str(auth_token or ""), timeout_sec,
        )
    started, deadline, error = time.time(), time.time() + timeout_sec, ""
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    while time.time() < deadline:
        try:
            names = asyncio.run(_verify_streamable_http(
                f"http://{host}:{port}/mcp", headers,
                max(1.0, min(8.0, deadline - time.time())),
            ))
            return {
                "verified": True, "tools_count": len(names),
                "tool_names": sorted(names),
                "latency_ms": round((time.time() - started) * 1000, 2),
                "transport": "streamable_http", "route": "/mcp",
                "legacy_sse_authoritative": False,
            }
        except Exception as exc:
            error = _exception_text(exc)
            time.sleep(0.25)
    return {"verified": False, "error": f"Streamable HTTP readiness failed: {error}"}


def _resolve_launch_options(
    host: Optional[str], port: Optional[int], auth_token: Optional[str],
    require_auth: Optional[bool], repo_root: Optional[Path],
) -> tuple[Optional[MCPLaunchOptions], Optional[Dict[str, Any]]]:
    """Resolve and validate the bounded loopback launch boundary."""
    root = Path(repo_root or _get_repo_root()).resolve()
    bind_host = host or os.getenv("FOUNDUPS_MCP_HOST", DEFAULT_HOST)
    bind_port = port or int(os.getenv("FOUNDUPS_MCP_PORT", str(DEFAULT_PORT)))
    token = auth_token if auth_token is not None else os.getenv("FOUNDUPS_MCP_AUTH_TOKEN", "")
    if bind_host not in ("127.0.0.1", "localhost", "::1"):
        return None, {"status": "error", "error": "loopback_binding_required"}
    auth_enforced = bool(require_auth) if require_auth is not None else bool(token)
    if auth_enforced and not token:
        error = "auth_token_required_for_remote_exposure"
        logger.error("[MCP-BRIDGE] Auth enabled without a local token; refusing start")
        return None, {"status": "error", "error": error}
    return MCPLaunchOptions(
        root=root, host=bind_host, port=bind_port,
        token=token, auth_enforced=auth_enforced,
    ), None


def _existing_runtime_result() -> Optional[Dict[str, Any]]:
    """Return the one canonical already-running receipt when present."""
    global _active_runtime
    with _state_lock:
        handle = _active_runtime
        if handle is None:
            return None
        if not handle.is_alive():
            _release_lock(handle.lock)
            handle.lock = None
            if _active_runtime is handle:
                _active_runtime = None
            return None
        logger.warning("[MCP-BRIDGE] MCP server is already running")
        return {
            "status": "running", "already_running": True,
            "host": handle.host, "port": handle.port,
        }


def _acquire_http_lock() -> tuple[Optional[Any], Optional[Dict[str, Any]]]:
    """Acquire the unique HTTP runtime lock or fail closed."""
    try:
        from modules.infrastructure.instance_lock.src.instance_manager import get_instance_lock
        lock = get_instance_lock("foundups_mcp_bridge_http")
        if lock.check_duplicates():
            return None, {"status": "error", "error": "duplicate_instance_running"}
        if not lock.acquire():
            return None, {"status": "error", "error": "lock_acquisition_failed"}
        return lock, None
    except Exception:
        logger.exception("[MCP-BRIDGE] Instance lock system failure")
        return None, {"status": "error", "error": "lock_system_unavailable"}


def _release_lock(lock: Optional[Any]) -> None:
    """Release one held lock without masking the primary lifecycle result."""
    if lock is None:
        return
    try:
        lock.release()
    except Exception as exc:
        logger.debug("[MCP-BRIDGE] Lock release notice: %s", exc)


def _clear_active_runtime(expected: Optional[MCPRuntimeHandle] = None) -> None:
    """Clear only the expected owned runtime under the state lock."""
    global _active_runtime
    with _state_lock:
        if expected is None or _active_runtime is expected:
            _active_runtime = None


def _http_subprocess_spec(
    options: MCPLaunchOptions,
) -> tuple[Optional[list[str]], Optional[dict[str, str]], Optional[str]]:
    """Build the secret-free argv and private child environment."""
    interpreter = _get_mcp_env_python(options.root)
    if not interpreter.exists() or not _mcp_python_capable(interpreter):
        return None, None, "mcp_env_missing"
    executable, env = _mcp_child_env(options.root, interpreter, options.token)
    env["FOUNDUPS_MCP_HOST"] = options.host
    env["FOUNDUPS_MCP_PORT"] = str(options.port)
    env["FOUNDUPS_MCP_REQUIRE_AUTH"] = "1" if options.auth_enforced else "0"
    command = [
        str(executable), "-m",
        "modules.infrastructure.foundups_mcp_bridge.src.mcp_server",
        "--transport", "http", "--host", options.host,
        "--port", str(options.port),
    ]
    return command, env, None


def _readiness_failure(
    handle: MCPRuntimeHandle, canary: Dict[str, Any],
) -> Dict[str, Any]:
    """Terminate a failed startup without falsely releasing a live lock."""
    error = canary.get("error", "unknown_canary_failure")
    logger.error("[MCP-BRIDGE] Protocol readiness failed: %s", error)
    stopped, detail = _terminate_runtime(handle, timeout_sec=3.0)
    if stopped:
        _clear_active_runtime(handle)
    return {"status": "failed", "error": error, "termination": detail}


def _await_http_subprocess(
    handle: MCPRuntimeHandle, blocking: bool,
) -> Dict[str, Any]:
    """Return a live receipt or block until the canonical child is stopped."""
    assert handle.proc is not None
    if not blocking:
        return {
            "status": "running", "mode": "subprocess", "pid": handle.proc.pid,
            "host": handle.host, "port": handle.port,
            "readiness": handle.readiness,
        }
    try:
        handle.proc.wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("[MCP-BRIDGE] Subprocess interrupted")
    stopped, detail = _terminate_runtime(handle, timeout_sec=5.0)
    if not stopped:
        return {"status": "error", "error": detail}
    _clear_active_runtime(handle)
    return {"status": "stopped"}


def _launch_http_subprocess(
    options: MCPLaunchOptions, lock: Any, blocking: bool,
) -> Dict[str, Any]:
    """Start, verify, and own the one canonical MCP child process."""
    global _active_runtime
    command, env, error = _http_subprocess_spec(options)
    if error is not None:
        _release_lock(lock)
        return {"status": "error", "error": error}
    assert command is not None and env is not None
    proc = subprocess.Popen(command, cwd=str(options.root), env=env)
    handle = MCPRuntimeHandle(
        mode="subprocess", host=options.host, port=options.port,
        started_at=time.time(), lock=lock, proc=proc,
    )
    with _state_lock:
        _active_runtime = handle
    canary = verify_mcp_readiness(
        host=options.host, port=options.port, auth_token=options.token,
        timeout_sec=15.0, repo_root=options.root,
    )
    if not canary.get("verified"):
        return _readiness_failure(handle, canary)
    handle.readiness = canary
    logger.info(
        "[MCP-BRIDGE] Subprocess verified PID %s with %s tools",
        proc.pid, canary.get("tools_count"),
    )
    return _await_http_subprocess(handle, blocking)


def run_mcp_bridge_http(
    host: Optional[str] = None,
    port: Optional[int] = None,
    auth_token: Optional[str] = None,
    require_auth: Optional[bool] = None,
    repo_root: Optional[Path] = None,
    blocking: bool = True,
) -> Dict[str, Any]:
    """Run one canonical loopback Streamable HTTP subprocess lifecycle."""
    options, error = _resolve_launch_options(
        host, port, auth_token, require_auth, repo_root,
    )
    if error is not None:
        return error
    assert options is not None
    existing = _existing_runtime_result()
    if existing is not None:
        return existing
    print(
        f"[MCP-BRIDGE] Starting Streamable HTTP MCP on "
        f"http://{options.host}:{options.port}/mcp ..."
    )
    lock, error = _acquire_http_lock()
    if error is not None:
        return error
    try:
        return _launch_http_subprocess(options, lock, blocking)
    except Exception as exc:
        _release_lock(lock)
        _clear_active_runtime()
        return {"status": "error", "error": type(exc).__name__}


def stop_mcp_bridge_http(timeout_sec: float = 5.0) -> Dict[str, Any]:
    """
    Request graceful, verified shutdown of the active MCP HTTP server.

    Idempotent stop contract:
    - If no active runtime -> return {"status": "already_stopped"}
    - If active runtime -> signal exit, bounded wait for termination, verify port/server gone, release lock exactly once, clear global state.
    - If shutdown times out -> do NOT release lock; do NOT clear _active_runtime; return {"status": "error", "error": "stop_timeout_still_running"}.
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
        logger.error(f"[MCP-BRIDGE] Shutdown failed ({message}); retaining lock and runtime handle.")
        return {"status": "error", "error": message}

    with _state_lock:
        _active_runtime = None

    print("[MCP-BRIDGE] Verified clean shutdown.")
    return {"status": "stopped"}


def run_mcp_bridge_sse(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Deprecated name; starts the same canonical HTTP runtime and lock."""
    return run_mcp_bridge_http(*args, **kwargs)


def stop_mcp_bridge_sse(timeout_sec: float = 5.0) -> Dict[str, Any]:
    """Deprecated name; stops the same canonical HTTP runtime and lock."""
    return stop_mcp_bridge_http(timeout_sec=timeout_sec)


def get_mcp_bridge_status() -> Dict[str, Any]:
    """Get current truthful runtime status of the MCP HTTP server."""
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
    run_mcp_bridge_http(blocking=True)
