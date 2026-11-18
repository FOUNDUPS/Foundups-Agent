"""Real-transport cold-start regression for the Holo owner supervisor."""

from __future__ import annotations

import ast
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import threading
import time
from typing import Any

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    holo_query_service_supervisor as supervisor_module,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service_supervisor import (
    HEALTH_SCHEMA_VERSION,
    HoloQueryServiceSupervisor,
    OWNER_HOST,
    SERVICE_TOKEN_ENV,
)
from .holo_query_service_supervisor_support import (
    TEST_RUNTIME_ROOT,
    _synthetic_replica_capability,
)


TOKEN = "s" * 64
DELAY_SECONDS = 0.15
ORDINARY_PROBE_SECONDS = 0.05
STARTUP_PROBE_SECONDS = 0.4
TOTAL_STARTUP_SECONDS = 1.0
BINDING = (
    "a" * 40,
    "sha256:" + "d" * 64,
    "sha256:" + "b" * 64,
    "sha256:" + "c" * 64,
)
REPLICA_BINDING = tuple("sha256:" + character * 64 for character in "ef01")
RUNTIME_ENVIRONMENT_DIGEST = "sha256:" + "9" * 64


class _Process:
    def __init__(self) -> None:
        self.terminated = False
        self.terminate_calls = 0

    def poll(self) -> int | None:
        return 0 if self.terminated else None

    def terminate(self) -> None:
        self.terminate_calls += 1
        self.terminated = True

    def wait(self, timeout: float | None = None) -> int:
        return 0

    def kill(self) -> None:
        self.terminated = True


class _SlowOwnerHarness:
    def __init__(
        self, port: int, canonical_root: Path, replica_root: Path,
        events: list[str],
    ) -> None:
        self.port = port
        self.canonical_root = canonical_root
        self.replica_root = replica_root
        self.events = events
        self.requests: list[str] = []
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.process = _Process()
        self.spawn_count = 0

    def popen(self, command: list[str], **kwargs: Any) -> _Process:
        self.spawn_count += 1
        self.events.append("spawn")
        assert kwargs["env"][SERVICE_TOKEN_ENV] == TOKEN
        assert "HOLOINDEX_SSD_PATH" not in kwargs["env"]
        assert command[command.index("--canonical-ssd-path") + 1] == str(
            self.canonical_root
        )
        assert command[command.index("--query-replica-root") + 1] == str(
            self.replica_root
        )
        requests = self.requests

        class SlowReadyHandler(BaseHTTPRequestHandler):
            def log_message(self, _format: str, *_args: Any) -> None:
                return

            def do_GET(self) -> None:  # noqa: N802
                requests.append(self.headers.get("Authorization", ""))
                time.sleep(DELAY_SECONDS)
                body = json.dumps(_ready_payload()).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except BrokenPipeError:
                    return

        self.server = ThreadingHTTPServer((OWNER_HOST, self.port), SlowReadyHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self.process

    def close(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((OWNER_HOST, 0))
        return int(probe.getsockname()[1])


def _cold_start_owner(
    tmp_path: Path,
    canonical_root: Path,
    replica_root: Path,
    events: list[str],
    port: int,
) -> HoloQueryServiceSupervisor:
    return HoloQueryServiceSupervisor(
        repo_root=tmp_path,
        runtime_root=TEST_RUNTIME_ROOT,
        canonical_ssd_path=canonical_root,
        query_replica_root=replica_root,
        replica_capability_verifier=lambda: (
            events.append("verify") or _synthetic_replica_capability(REPLICA_BINDING)
        ),
        expected_replica_binding=REPLICA_BINDING,
        _runtime_environment_resolver_for_test=(
            lambda **_kwargs: RUNTIME_ENVIRONMENT_DIGEST
        ),
        port=port,
        startup_timeout_seconds=TOTAL_STARTUP_SECONDS,
        probe_timeout_seconds=ORDINARY_PROBE_SECONDS,
    )


def test_supervisor_cold_start_uses_longer_real_http_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    port = _free_port()
    canonical_root = tmp_path / "canonical"
    replica_root = tmp_path / "replica"
    events: list[str] = []
    harness = _SlowOwnerHarness(port, canonical_root, replica_root, events)
    monkeypatch.setattr(supervisor_module.subprocess, "Popen", harness.popen)
    monkeypatch.setattr(supervisor_module.secrets, "token_urlsafe", lambda _n: TOKEN)
    monkeypatch.setattr(
        supervisor_module,
        "DEFAULT_OWNER_STARTUP_PROBE_TIMEOUT_SECONDS",
        STARTUP_PROBE_SECONDS,
    )
    owner = _cold_start_owner(tmp_path, canonical_root, replica_root, events, port)
    try:
        owner.start(
            expected_repo_head_sha=BINDING[0],
            expected_repo_root_digest=BINDING[1],
            expected_generation_id=BINDING[2],
            expected_receipt_digest=BINDING[3],
        )
        assert owner.is_ready is True
        assert owner.verified_binding == BINDING
        assert owner.verified_replica_binding == REPLICA_BINDING
        assert harness.spawn_count == 1
        assert events == ["verify", "spawn", "verify"]
        assert harness.requests == [f"Bearer {TOKEN}"]
        assert supervisor_module._authenticated_health_probe(
            host=OWNER_HOST,
            port=port,
            token=TOKEN,
            timeout_seconds=ORDINARY_PROBE_SECONDS,
            expected_repo_head_sha=BINDING[0],
            expected_repo_root_digest=BINDING[1],
            expected_generation_id=BINDING[2],
            expected_receipt_digest=BINDING[3],
            expected_replica_binding=REPLICA_BINDING,
        ) is False
    finally:
        owner.stop()
        harness.close()

    assert ORDINARY_PROBE_SECONDS < DELAY_SECONDS
    assert DELAY_SECONDS < STARTUP_PROBE_SECONDS < TOTAL_STARTUP_SECONDS
    assert harness.spawn_count == 1
    assert harness.process.terminate_calls == 1
    assert harness.thread is not None and not harness.thread.is_alive()


def test_supervisor_change_reduces_wsp62_debt() -> None:
    path = Path(supervisor_module.__file__)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    supervisor_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "HoloQueryServiceSupervisor"
    )
    start = next(
        node for node in supervisor_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "start"
    )

    assert len(source.splitlines()) <= 688
    assert supervisor_class.end_lineno - supervisor_class.lineno + 1 <= 200
    assert start.end_lineno - start.lineno + 1 <= 50


def _ready_payload() -> dict[str, Any]:
    return {
        "schema_version": HEALTH_SCHEMA_VERSION,
        "ok": True,
        "source": "holoindex",
        "status": "ready",
        "loopback_only": True,
        "freshness": "CURRENT",
        "error": "",
        "stale_reasons": [],
        "index_gap_detected": False,
        "no_holoindex_reindex_performed": True,
        "retrieval_mode": "semantic",
        "retrieval_runtime_ranker_digest": "sha256:" + ("e" * 64),
        "runtime_environment_digest": RUNTIME_ENVIRONMENT_DIGEST,
        "repo_head_sha": BINDING[0],
        "repo_root_digest": BINDING[1],
        "freshness_generation_id": BINDING[2],
        "freshness_receipt_digest": BINDING[3],
        "query_replica_descriptor_digest": REPLICA_BINDING[0],
        "query_replica_generation_id": REPLICA_BINDING[1],
        "query_replica_id": REPLICA_BINDING[2],
        "query_replica_path_identity_digest": REPLICA_BINDING[3],
    }
