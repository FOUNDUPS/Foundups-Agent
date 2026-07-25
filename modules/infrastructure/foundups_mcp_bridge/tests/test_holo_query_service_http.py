"""Transport-level tests for the dependency-free HoloIndex HTTP runtime."""

from __future__ import annotations

import http.client
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_holoindex_owner_query_client as owner_client,
)
from modules.communication.moltbot_bridge.src.reddog_holoindex_query_adapter import (
    HoloIndexReadOnlyQueryAdapter,
)
from modules.infrastructure.foundups_mcp_bridge.src import (
    holo_query_service_http as http_module,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service import (
    BASELINE_COLLECTIONS,
    QUERY_PATH,
    HoloIndexQueryOwnerService,
    main,
)
from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_service import (
    _receipt as _service_receipt,
)


TOKEN = "stdlib-owner-service-token-with-strong-length"
SHA = "a" * 40
SPACE_FINGERPRINT = "sha256:" + ("1" * 64)


def _receipt(repo_root: Path, ssd_path: Path) -> Mapping[str, Any]:
    return _service_receipt(
        repo_root=repo_root.resolve(strict=False),
        ssd_path=ssd_path.resolve(strict=False),
    )


class _Backend:
    retrieval_mode = "semantic"
    collection_embedding_space_map = {
        name: SPACE_FINGERPRINT for name in BASELINE_COLLECTIONS
    }

    def search(
        self,
        query: str,
        *,
        limit: int,
        doc_type_filter: str,
    ) -> Mapping[str, Any]:
        return {
            "wsp_hits": [{"path": "WSP_framework/src/WSP_97.md"}],
            "knowledge_hits": [{"path": "WSP_knowledge/docs/Papers/example.md"}],
            "metadata": {
                "retrieval_mode": "semantic",
                "embedding_backend": "sentence_transformers",
                "collection_embedding_space_map": {
                    name: SPACE_FINGERPRINT for name in BASELINE_COLLECTIONS
                },
            },
        }


def _owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> HoloIndexQueryOwnerService:
    monkeypatch.setenv("HOLOINDEX_QUERY_SERVICE_TOKEN", TOKEN)
    ssd_path = tmp_path / "holo-store"
    return HoloIndexQueryOwnerService(
        repo_root=tmp_path,
        ssd_path=ssd_path,
        backend_factory=lambda _path: _Backend(),
        receipt_loader=lambda _path: _receipt(tmp_path, ssd_path),
        repository_state_reader=lambda _root: SimpleNamespace(
            proven_clean=True,
            head_sha=SHA,
            error="",
        ),
    )


def test_stdlib_runtime_serves_authenticated_generation_bound_query(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _owner(tmp_path, monkeypatch)
    server = http_module.create_stdlib_server(
        owner,
        host="127.0.0.1",
        port=0,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = http.client.HTTPConnection(
        "127.0.0.1",
        server.server_address[1],
        timeout=2,
    )
    try:
        body = json.dumps(
            {
                "query": "find operational contract",
                "limit": 8,
                "doc_type_filter": "all",
                "expected_repo_head_sha": SHA,
            }
        )
        connection.request(
            "POST",
            QUERY_PATH,
            body=body,
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json",
            },
        )
        response = connection.getresponse()
        payload = json.loads(response.read())
        assert response.status == 200
        assert payload["ok"] is True
        assert payload["freshness"] == "CURRENT"
        assert payload["raw_result"]["wsp_hits"]
        assert payload["raw_result"]["knowledge_hits"]
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        owner.close()


def test_reddog_adapter_queries_live_owner_without_opening_local_chroma(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _owner(tmp_path, monkeypatch)
    server = http_module.create_stdlib_server(
        owner,
        host="127.0.0.1",
        port=0,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(
        owner_client,
        "read_repository_state",
        lambda _root: SimpleNamespace(
            proven_clean=True,
            head_sha=SHA,
            error="",
        ),
    )
    try:
        result = HoloIndexReadOnlyQueryAdapter(
            repo_root=tmp_path,
            service_url=f"http://127.0.0.1:{server.server_address[1]}",
            service_token=TOKEN,
        ).query(
            query="find operational contract",
            allowed_paths=(
                "WSP_framework/src/WSP_97.md",
                "WSP_knowledge/docs/Papers/example.md",
            ),
            limit=8,
        )
        assert result["ok"] is True
        assert result["freshness"] == "CURRENT"
        assert result["retrieval_mode"] == "semantic"
        assert result["repo_head_sha"] == SHA
        assert result["freshness_generation_id"] == _receipt(
            tmp_path,
            tmp_path / "holo-store",
        )["generation_id"]
        assert {hit["path"] for hit in result["hits"]} == {
            "WSP_framework/src/WSP_97.md",
            "WSP_knowledge/docs/Papers/example.md",
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        owner.close()


def test_main_dispatches_to_stdlib_when_fastapi_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class FakeOwner:
        def close(self) -> None:
            events.append("owner_closed")

    class FakeServer:
        def serve_forever(self) -> None:
            events.append("served")

        def server_close(self) -> None:
            events.append("server_closed")

    monkeypatch.setenv("HOLOINDEX_QUERY_SERVICE_TOKEN", TOKEN)
    monkeypatch.setattr(http_module, "FastAPI", None)
    monkeypatch.setattr(
        http_module,
        "HoloIndexQueryOwnerService",
        lambda **_kwargs: FakeOwner(),
    )
    monkeypatch.setattr(
        http_module,
        "create_stdlib_server",
        lambda _owner, **_kwargs: FakeServer(),
    )
    monkeypatch.setattr(
        http_module,
        "_start_parent_process_watchdog",
        lambda parent_pid: events.append(f"watchdog_started:{parent_pid}"),
    )
    assert (
        main(
            [
                "--host",
                "127.0.0.1",
                "--port",
                "8127",
                "--parent-pid",
                "1234",
            ]
        )
        == 0
    )
    assert events == [
        "watchdog_started:1234",
        "served",
        "server_closed",
        "owner_closed",
    ]


def test_parent_process_watchdog_exits_after_parent_wait_returns() -> None:
    exits: list[int] = []
    waited: list[int] = []

    thread = http_module._start_parent_process_watchdog(
        1234,
        wait_for_parent_exit=lambda parent_pid: waited.append(parent_pid),
        terminate_process=exits.append,
    )
    thread.join(timeout=1)

    assert waited == [1234]
    assert exits == [0]
    assert thread.is_alive() is False


def test_parent_process_watchdog_fails_closed_on_waiter_error() -> None:
    exits: list[int] = []

    def fail_waiter(_parent_pid: int) -> None:
        raise RuntimeError("synthetic watcher failure")

    thread = http_module._start_parent_process_watchdog(
        1234,
        wait_for_parent_exit=fail_waiter,
        terminate_process=exits.append,
    )
    thread.join(timeout=1)

    assert exits == [0]
    assert thread.is_alive() is False


def test_parent_process_wait_rejects_mismatched_claimed_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    windows_waits: list[int] = []
    monkeypatch.setattr(http_module.os, "getppid", lambda: 4321)
    monkeypatch.setattr(http_module.os, "name", "nt")
    monkeypatch.setattr(
        http_module,
        "_wait_for_windows_parent_exit",
        windows_waits.append,
    )

    http_module._wait_for_parent_exit(1234)

    assert windows_waits == []


def test_parent_process_watchdog_exits_real_child_after_parent_exit(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "parent-exit-observed.txt"
    child_template = (
        "import os,time;"
        "from pathlib import Path;"
        "from modules.infrastructure.foundups_mcp_bridge.src."
        "holo_query_service_http import _start_parent_process_watchdog;"
        "_start_parent_process_watchdog({parent_pid},terminate_process="
        "lambda code:(Path({marker!r}).write_text(str(code)),os._exit(code))[1]);"
        "time.sleep(30)"
    )
    parent_code = (
        "import os,subprocess,sys,time;"
        f"template={child_template!r};"
        f"code=template.format(parent_pid=os.getpid(),marker={str(marker)!r});"
        "child=subprocess.Popen([sys.executable,'-B','-c',code],"
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
        "stderr=subprocess.DEVNULL,shell=False);"
        "print(child.pid,flush=True);"
        "time.sleep(0.5)"
    )
    parent = subprocess.Popen(
        [sys.executable, "-B", "-c", parent_code],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
    )
    child_pid = 0
    try:
        assert parent.stdout is not None
        child_pid = int(parent.stdout.readline().strip())
        assert parent.wait(timeout=5) == 0
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not marker.exists():
            time.sleep(0.1)
        assert marker.read_text(encoding="utf-8") == "0"
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=3)
        if child_pid and not marker.exists():
            try:
                os.kill(child_pid, signal.SIGTERM)
            except OSError:
                pass
