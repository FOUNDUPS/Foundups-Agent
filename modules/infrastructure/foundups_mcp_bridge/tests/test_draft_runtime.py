"""Exercise the real loopback transport in a separately running process."""

import asyncio
from datetime import timedelta
from importlib.metadata import version
import os
from pathlib import Path
import socket
import subprocess
import sys
from threading import Thread
from time import monotonic, sleep

from cryptography.fernet import Fernet
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import pytest
import uvicorn

from .test_draft_server import (
    ACCOUNT, ARGS, DIGEST, ISSUER, RESOURCE, DraftCorrection, DraftJournal,
    DraftPolicy, FakeGmail, Verifier, build_app,
)


def _serve(directory: Path) -> None:
    journal = DraftJournal(directory / "synthetic.sqlite3", Fernet(Fernet.generate_key()))
    service = DraftCorrection(DraftPolicy(ACCOUNT, ACCOUNT, DIGEST, "req1", 100, 300),
                              FakeGmail(), journal, clock=lambda: 200)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        app = build_app(service, Verifier(), issuer=ISSUER, resource_url=RESOURCE, port=port)
        server = uvicorn.Server(uvicorn.Config(app, access_log=False, proxy_headers=False,
                                              log_level="error", timeout_graceful_shutdown=3))

        def stop_from_parent():
            sys.stdin.buffer.readline()
            server.should_exit = True

        Thread(target=stop_from_parent, daemon=True).start()
        candidate = directory / "ready.tmp"
        candidate.write_text(str(port), encoding="ascii")
        candidate.replace(directory / "port")
        server.run(sockets=[listener])


def _ready(process, directory):
    deadline = monotonic() + 12
    with httpx.Client(timeout=0.3, trust_env=False) as client:
        while monotonic() < deadline and process.poll() is None:
            marker = directory / "port"
            if marker.exists():
                origin = f"http://127.0.0.1:{int(marker.read_text(encoding='ascii'))}"
                try:
                    response = client.get(origin + "/health")
                except httpx.TransportError:
                    pass
                else:
                    if response.status_code == 200 and response.json() == {"status": "ok"}:
                        return origin
            sleep(0.05)
    pytest.fail("separate draft MCP process did not become ready")


async def _exercise(origin):
    url = origin + "/mcp"
    async with httpx.AsyncClient(timeout=4, trust_env=False) as client:
        denied = await client.post(url, headers={"Accept": "application/json, text/event-stream"},
                                   json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert denied.status_code == 401
        client.headers["Authorization"] = "Bearer write"
        async with streamable_http_client(url, http_client=client) as (reader, writer, session_id):
            async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=4)) as mcp:
                initialized = await mcp.initialize()
                assert initialized.serverInfo.name == "FoundUps Private Draft Sender"
                assert session_id() is None
                tools = await mcp.list_tools()
                assert {tool.name for tool in tools.tools} == {"inspect_draft", "set_draft_sender"}
                inspected = await mcp.call_tool("inspect_draft", {})
                assert inspected.structuredContent["digest"] == DIGEST
                assert "Private synthetic marker" not in str(inspected)
                preview = await mcp.call_tool("set_draft_sender", ARGS)
                assert preview.structuredContent["status"] == "preview"
                denied = await mcp.call_tool("send_email", {})
                assert denied.isError
                written = await mcp.call_tool("set_draft_sender", {**ARGS, "dry_run": False})
                assert written.structuredContent["status"] == "verified"
                assert written.structuredContent["verification_receipt"]["current_message_id"] == "m2"

        # A new client connection reads the same independently running service state.
        async with streamable_http_client(url, http_client=client) as (reader, writer, _):
            async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=4)) as mcp:
                await mcp.initialize()
                inspected = await mcp.call_tool("inspect_draft", {})
                assert inspected.structuredContent["current_message_id"] == "m2"
                assert inspected.structuredContent["digest"] == preview.structuredContent["after_digest"]


@pytest.mark.skipif(version("mcp") != "1.30.0", reason="requires the admitted MCP runtime")
def test_separate_loopback_process_start_invoke_reconnect_and_shutdown(tmp_path):
    root = Path(__file__).resolve().parents[4]
    environment = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "WINDIR", "TMP", "TEMP")
                   if key in os.environ}
    with subprocess.Popen(
        [sys.executable, "-B", "-m", "modules.infrastructure.foundups_mcp_bridge.tests.test_draft_runtime",
         str(tmp_path)],
        cwd=root, env=environment, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    ) as process:
        graceful = False
        try:
            assert process.pid != os.getpid()
            origin = _ready(process, tmp_path)
            asyncio.run(_exercise(origin))
        finally:
            if process.poll() is None:
                try:
                    process.stdin.write(b"stop\n")
                    process.stdin.flush()
                    process.wait(timeout=6)
                    graceful = True
                except (BrokenPipeError, subprocess.TimeoutExpired):
                    process.kill()
                    process.wait(timeout=3)
        assert graceful and process.returncode == 0


if __name__ == "__main__":
    _serve(Path(sys.argv[1]))
