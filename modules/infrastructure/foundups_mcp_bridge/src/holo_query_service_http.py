#!/usr/bin/env python3
"""Loopback HTTP transports for the private HoloIndex query owner."""

from __future__ import annotations

import argparse
import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from holo_index.repository_state import runtime_repository_root

from .holo_query_service import (
    DEFAULT_BIND_HOST,
    DEFAULT_PORT,
    HEALTH_PATH,
    MIN_BEARER_TOKEN_CHARS,
    QUERY_PATH,
    TOKEN_ENV,
    TOKEN_TOO_SHORT_ERROR,
    HoloIndexQueryOwnerService,
    validate_bind_host,
)
from .reddog_holoindex_query_replica_descriptor import (
    QueryReplicaDescriptorError,
)
from .reddog_holoindex_acceptance_guards import (
    AcceptanceGuardError,
    prove_existing_isolated_store,
)

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from starlette.concurrency import run_in_threadpool
except ImportError:  # pragma: no cover - stdlib runtime covers this environment
    FastAPI = None  # type: ignore[assignment]
    Request = Any  # type: ignore[assignment,misc]
    JSONResponse = None  # type: ignore[assignment]
    run_in_threadpool = None  # type: ignore[assignment]


def _http_status(result: Mapping[str, Any]) -> int:
    if result.get("ok") is True:
        return 200
    return {
        "UNAUTHORIZED": 401,
        "AUTH_NOT_CONFIGURED": 503,
        TOKEN_TOO_SHORT_ERROR: 503,
        "REQUEST_TOO_LARGE": 413,
        "QUERY_TIMEOUT": 504,
        "QUERY_QUEUE_TIMEOUT": 503,
        "OWNER_BUSY": 503,
        "SEMANTIC_BACKEND_UNAVAILABLE": 503,
        "HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE": 503,
        "HOLOINDEX_TIER0_INCOMPLETE": 409,
        "HOLOINDEX_TIER0_LOOKUP_FAILED": 503,
        "SEMANTIC_CANARY_EMPTY": 503,
        "HEALTH_UNAVAILABLE": 503,
        "MISSING_GENERATION_BINDING": 409,
        "REPO_HEAD_MISMATCH": 409,
        "STALE_INDEX": 409,
        "GENERATION_CHANGED_DURING_QUERY": 409,
        "NOT_FOUND": 404,
        "CONTENT_LENGTH_REQUIRED": 411,
    }.get(str(result.get("error") or ""), 400)


def _new_fastapi_owner(
    service: HoloIndexQueryOwnerService | None,
) -> tuple[HoloIndexQueryOwnerService, Any]:
    if FastAPI is None or JSONResponse is None:
        raise RuntimeError("FASTAPI_DEPENDENCY_UNAVAILABLE_USE_STDLIB_RUNTIME")
    owner = service or HoloIndexQueryOwnerService(
        repo_root=runtime_repository_root(Path(__file__).resolve().parents[4])
    )
    application = FastAPI(
        title="Private HoloIndex Query Owner",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    return owner, application


def create_holo_query_app(
    service: HoloIndexQueryOwnerService | None = None,
) -> Any:
    """Build exactly two FastAPI routes; TestClient is not required."""
    owner, application = _new_fastapi_owner(service)

    @application.post(QUERY_PATH)
    async def query_route(request: Request) -> Any:
        authorization = request.headers.get("authorization")
        auth_error = owner.authorization_error(authorization)
        if auth_error:
            result = owner._auth_failure(auth_error)
            return JSONResponse(result, status_code=_http_status(result))
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > owner.max_request_bytes:
                result = owner._auth_failure("REQUEST_TOO_LARGE")
                return JSONResponse(result, status_code=413)
            body.extend(chunk)
        try:
            payload = json.loads(bytes(body))
        except (json.JSONDecodeError, UnicodeDecodeError):
            result = owner._auth_failure("INVALID_JSON")
            return JSONResponse(result, status_code=400)
        result = await run_in_threadpool(
            owner.handle_query,
            payload,
            authorization=authorization,
            request_size=len(body),
        )
        return JSONResponse(result, status_code=_http_status(result))

    @application.get(HEALTH_PATH)
    async def health_route(request: Request) -> Any:
        result = await run_in_threadpool(
            owner.handle_health,
            authorization=request.headers.get("authorization"),
        )
        return JSONResponse(result, status_code=_http_status(result))

    application.state.holoindex_owner_service = owner
    return application


class _OwnerRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    @property
    def _owner(self) -> HoloIndexQueryOwnerService:
        return getattr(self.server, "holoindex_owner_service")

    def log_message(self, _format: str, *args: Any) -> None:
        return  # Never log bearer headers, query strings, or payloads.

    def _send(
        self,
        result: Mapping[str, Any],
        status: int | None = None,
    ) -> None:
        body = json.dumps(
            result,
            separators=(",", ":"),
            default=str,
        ).encode()
        self.send_response(status or _http_status(result))
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def _not_found(self) -> None:
        self._send(self._owner._auth_failure("NOT_FOUND"), 404)

    def do_GET(self) -> None:  # noqa: N802
        if urlsplit(self.path).path != HEALTH_PATH:
            self._not_found()
            return
        self._send(
            self._owner.handle_health(
                authorization=self.headers.get("Authorization")
            )
        )

    def do_POST(self) -> None:  # noqa: N802
        if urlsplit(self.path).path != QUERY_PATH:
            self._not_found()
            return
        owner = self._owner
        authorization = self.headers.get("Authorization")
        auth_error = owner.authorization_error(authorization)
        if auth_error:
            self._send(owner._auth_failure(auth_error))
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._send(owner._auth_failure("CONTENT_LENGTH_REQUIRED"), 411)
            return
        if length < 0 or length > owner.max_request_bytes:
            self._send(owner._auth_failure("REQUEST_TOO_LARGE"), 413)
            return
        self.connection.settimeout(owner.query_timeout_seconds)
        try:
            body = self.rfile.read(length)
        except (TimeoutError, socket.timeout):
            self._send(owner._auth_failure("QUERY_TIMEOUT"), 504)
            return
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send(owner._auth_failure("INVALID_JSON"), 400)
            return
        result = owner.handle_query(
            payload,
            authorization=authorization,
            request_size=len(body),
        )
        self._send(result)


def create_stdlib_server(
    service: HoloIndexQueryOwnerService,
    *,
    host: str = DEFAULT_BIND_HOST,
    port: int = DEFAULT_PORT,
) -> ThreadingHTTPServer:
    """Create the dependency-free loopback HTTP runtime."""
    bind_host = validate_bind_host(host)
    server = ThreadingHTTPServer(
        (bind_host, int(port)),
        _OwnerRequestHandler,
    )
    server.holoindex_owner_service = service  # type: ignore[attr-defined]
    server.daemon_threads = True
    return server


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Private HoloIndex query owner"
    )
    parser.add_argument("--host", default=DEFAULT_BIND_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--parent-pid", type=int, default=0)
    parser.add_argument("--canonical-ssd-path", default="")
    parser.add_argument("--query-replica-root", default="")
    return parser


def _wait_for_windows_parent_exit(parent_pid: int) -> None:
    import ctypes
    from ctypes import wintypes

    synchronize = 0x00100000
    infinite = 0xFFFFFFFF
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.OpenProcess(synchronize, False, int(parent_pid))
    if not handle:
        return
    try:
        kernel32.WaitForSingleObject(handle, infinite)
    finally:
        kernel32.CloseHandle(handle)


def _wait_for_parent_exit(parent_pid: int) -> None:
    if os.getppid() != parent_pid:
        return
    if os.name == "nt":
        _wait_for_windows_parent_exit(parent_pid)
        return
    while os.getppid() == parent_pid:
        time.sleep(0.25)


def _start_parent_process_watchdog(
    parent_pid: int,
    *,
    wait_for_parent_exit: Any = _wait_for_parent_exit,
    terminate_process: Any = os._exit,
) -> threading.Thread:
    """Exit the private owner after its exact supervisor process terminates."""

    def wait_for_parent() -> None:
        try:
            wait_for_parent_exit(parent_pid)
        except Exception:
            pass
        terminate_process(0)

    thread = threading.Thread(
        target=wait_for_parent,
        name="holoindex-owner-parent-watchdog",
        daemon=True,
    )
    thread.start()
    return thread


def _serve_owner(owner: HoloIndexQueryOwnerService, host: str, port: int) -> None:
    if FastAPI is not None:
        import uvicorn
        uvicorn.run(
            create_holo_query_app(owner), host=host, port=port, workers=1,
            access_log=False, log_level="warning",
        )
        return
    server = create_stdlib_server(owner, host=host, port=port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        owner.close()


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        host = validate_bind_host(args.host)
    except ValueError:
        print("HOLOINDEX_QUERY_SERVICE_LOOPBACK_REQUIRED")
        return 2
    if not 1 <= int(args.port) <= 65_535:
        print("HOLOINDEX_QUERY_SERVICE_INVALID_PORT")
        return 2
    if int(args.parent_pid) < 0:
        print("HOLOINDEX_QUERY_SERVICE_INVALID_PARENT_PID")
        return 2
    token = str(os.environ.pop(TOKEN_ENV, "") or "").strip()
    if not token:
        print("HOLOINDEX_QUERY_SERVICE_TOKEN_REQUIRED")
        return 2
    if len(token) < MIN_BEARER_TOKEN_CHARS:
        print(TOKEN_TOO_SHORT_ERROR)
        return 2
    repo_root = runtime_repository_root(Path(__file__).resolve().parents[4])
    if not args.canonical_ssd_path or not args.query_replica_root:
        print("HOLOINDEX_QUERY_REPLICA_REQUIRED")
        return 2
    try:
        replica_proof = prove_existing_isolated_store(
            args.query_replica_root,
            canonical_store=args.canonical_ssd_path,
            repo_roots=(repo_root,),
        )
    except (AcceptanceGuardError, QueryReplicaDescriptorError, OSError, ValueError):
        print("HOLOINDEX_QUERY_REPLICA_INVALID")
        return 2
    if args.parent_pid:
        _start_parent_process_watchdog(int(args.parent_pid))
    try:
        owner = HoloIndexQueryOwnerService(
            repo_root=repo_root,
            canonical_ssd_path=args.canonical_ssd_path,
            query_replica_root_proof=replica_proof,
            bearer_token=token,
        )
    except (QueryReplicaDescriptorError, OSError, ValueError):
        print("HOLOINDEX_QUERY_REPLICA_INVALID")
        return 2
    _serve_owner(owner, host, int(args.port))
    return 0


# The private supervisor constructs the application after capturing and
# deleting the bearer from the child environment. Importing this module never
# creates a secret-bearing owner instance.
app = None

__all__ = [
    "FastAPI",
    "app",
    "create_holo_query_app",
    "create_stdlib_server",
    "_start_parent_process_watchdog",
    "_wait_for_parent_exit",
    "main",
]

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
