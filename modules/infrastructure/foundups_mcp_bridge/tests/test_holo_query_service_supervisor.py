"""Tests for the host-owned HoloIndex query-service lifecycle boundary."""

from __future__ import annotations

import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    holo_query_service_supervisor as supervisor_module,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service_supervisor import (
    HEALTH_SCHEMA_VERSION,
    OWNER_HOST,
    OWNER_MODULE,
    SERVICE_TOKEN_ENV,
    SERVICE_URL_ENV,
    HoloQueryServiceSupervisor,
    HoloQueryServiceSupervisorError,
)


TOKEN = "x" * 64


class _FakeProcess:
    def __init__(
        self,
        *,
        returncode: int | None = None,
        wait_timeouts: int = 0,
    ) -> None:
        self.returncode = returncode
        self.wait_timeouts = wait_timeouts
        self.wait_calls = 0
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def wait(self, *, timeout: float) -> int:
        del timeout
        self.wait_calls += 1
        if self.wait_calls <= self.wait_timeouts:
            raise subprocess.TimeoutExpired("owner", 1)
        self.returncode = -9 if self.killed else 0
        return self.returncode


def _install_successful_start(
    monkeypatch: pytest.MonkeyPatch,
    process: _FakeProcess,
) -> dict[str, Any]:
    launch: dict[str, Any] = {}

    def fake_popen(command: list[str], **kwargs: Any) -> _FakeProcess:
        launch["command"] = list(command)
        launch["kwargs"] = {**kwargs, "env": dict(kwargs["env"])}
        return process

    monkeypatch.setattr(supervisor_module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        supervisor_module,
        "_authenticated_health_probe",
        lambda **kwargs: kwargs["token"] == TOKEN,
    )
    monkeypatch.setattr(
        supervisor_module.secrets,
        "token_urlsafe",
        lambda _bytes: TOKEN,
    )
    return launch


def test_start_uses_argv_loopback_secret_and_authenticated_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess()
    launch = _install_successful_start(monkeypatch, process)
    registered: list[Any] = []
    unregistered: list[Any] = []
    monkeypatch.setattr(
        supervisor_module.atexit,
        "register",
        lambda callback: registered.append(callback),
    )
    monkeypatch.setattr(
        supervisor_module.atexit,
        "unregister",
        lambda callback: unregistered.append(callback),
    )

    owner = HoloQueryServiceSupervisor(repo_root=tmp_path, port=9137).start()

    assert owner.is_ready is True
    assert launch["command"] == [
        supervisor_module.sys.executable,
        "-B",
        "-m",
        OWNER_MODULE,
        "--host",
        OWNER_HOST,
        "--port",
        "9137",
    ]
    options = launch["kwargs"]
    assert options["shell"] is False
    assert options["cwd"] == str(tmp_path.resolve())
    assert options["stdin"] is subprocess.DEVNULL
    assert options["stdout"] is subprocess.DEVNULL
    assert options["stderr"] is subprocess.DEVNULL
    assert options["env"][SERVICE_TOKEN_ENV] == TOKEN
    assert SERVICE_URL_ENV not in options["env"]
    assert registered

    owner.stop()
    assert process.terminated is True
    assert unregistered
    assert owner.is_ready is False


def test_start_passes_explicit_ssd_path_and_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess()
    launch = _install_successful_start(monkeypatch, process)
    monkeypatch.setattr(supervisor_module.atexit, "register", lambda _callback: None)
    monkeypatch.setattr(supervisor_module.atexit, "unregister", lambda _callback: None)
    ssd_path = tmp_path / "holo-store"
    owner = HoloQueryServiceSupervisor(
        repo_root=tmp_path,
        ssd_path=ssd_path,
    ).start()

    assert owner.start() is owner
    assert launch["kwargs"]["env"][supervisor_module.SSD_PATH_ENV] == str(
        ssd_path.resolve()
    )
    owner.stop()


def test_environment_handoff_is_child_only_and_invalidated_if_owner_dies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess()
    _install_successful_start(monkeypatch, process)
    monkeypatch.setattr(supervisor_module.atexit, "register", lambda _callback: None)
    monkeypatch.setattr(supervisor_module.atexit, "unregister", lambda _callback: None)
    owner = HoloQueryServiceSupervisor(repo_root=tmp_path, port=9138).start()
    base = {"SAFE_VALUE": "preserved"}

    child_environment = owner.environment_for_child(base)

    assert base == {"SAFE_VALUE": "preserved"}
    assert child_environment["SAFE_VALUE"] == "preserved"
    assert child_environment[SERVICE_URL_ENV] == "http://127.0.0.1:9138"
    assert child_environment[SERVICE_TOKEN_ENV] == TOKEN
    process.returncode = 7
    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        owner.environment_for_child(base)
    assert error.value.code == "HOLOINDEX_QUERY_SERVICE_NOT_READY"
    assert owner._token == ""
    owner.stop()


def test_startup_timeout_terminates_owner_and_never_exposes_token_in_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess()
    captured_environment: dict[str, str] = {}

    def fake_popen(_command: list[str], **kwargs: Any) -> _FakeProcess:
        captured_environment.update(kwargs["env"])
        return process

    now = {"value": 0.0}
    monkeypatch.setattr(supervisor_module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        supervisor_module,
        "_authenticated_health_probe",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(
        supervisor_module,
        "_authenticated_health_rejection",
        lambda **_kwargs: "",
    )
    monkeypatch.setattr(
        supervisor_module.secrets,
        "token_urlsafe",
        lambda _bytes: TOKEN,
    )
    monkeypatch.setattr(
        supervisor_module.time,
        "monotonic",
        lambda: now["value"],
    )
    monkeypatch.setattr(
        supervisor_module.time,
        "sleep",
        lambda seconds: now.__setitem__("value", now["value"] + seconds),
    )
    owner = HoloQueryServiceSupervisor(
        repo_root=tmp_path,
        startup_timeout_seconds=1.0,
        probe_interval_seconds=0.25,
    )

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        owner.start()

    assert error.value.code == "HOLOINDEX_QUERY_SERVICE_STARTUP_TIMEOUT"
    assert TOKEN not in str(error.value)
    assert captured_environment[SERVICE_TOKEN_ENV] == TOKEN
    assert process.terminated is True
    assert owner.is_ready is False


def test_startup_stops_immediately_on_authenticated_stale_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess()
    monkeypatch.setattr(
        supervisor_module.subprocess,
        "Popen",
        lambda _command, **_kwargs: process,
    )
    monkeypatch.setattr(
        supervisor_module,
        "_authenticated_health_probe",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(
        supervisor_module,
        "_authenticated_health_rejection",
        lambda **_kwargs: "REPO_HEAD_MISMATCH",
    )
    monkeypatch.setattr(
        supervisor_module.secrets,
        "token_urlsafe",
        lambda _bytes: TOKEN,
    )
    owner = HoloQueryServiceSupervisor(
        repo_root=tmp_path,
        startup_timeout_seconds=300.0,
    )

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        owner.start()

    assert error.value.code == "REPO_HEAD_MISMATCH"
    assert process.terminated is True
    assert owner.is_ready is False


def test_health_rejection_accepts_only_terminal_authenticated_contract() -> None:
    base = {
        "schema_version": HEALTH_SCHEMA_VERSION,
        "ok": False,
        "source": "holoindex",
        "loopback_only": True,
        "no_holoindex_reindex_performed": True,
        "error": "STALE_INDEX",
    }
    assert supervisor_module._health_rejection_code(base) == "STALE_INDEX"
    assert supervisor_module._health_rejection_code({**base, "error": "UNAUTHORIZED"}) == ""
    assert supervisor_module._health_rejection_code({**base, "loopback_only": False}) == ""
    assert supervisor_module._health_rejection_code({**base, "schema_version": "wrong"}) == ""


def test_startup_fails_closed_when_spawned_owner_exits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess(returncode=2)
    _install_successful_start(monkeypatch, process)
    owner = HoloQueryServiceSupervisor(repo_root=tmp_path)

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        owner.start()

    assert error.value.code == "HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP"
    assert owner.is_ready is False


def test_startup_fails_if_owner_exits_after_health_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess()
    monkeypatch.setattr(
        supervisor_module.subprocess,
        "Popen",
        lambda _command, **_kwargs: process,
    )
    monkeypatch.setattr(
        supervisor_module.secrets,
        "token_urlsafe",
        lambda _bytes: TOKEN,
    )

    def exit_during_probe(**_kwargs: Any) -> bool:
        process.returncode = 9
        return True

    monkeypatch.setattr(
        supervisor_module,
        "_authenticated_health_probe",
        exit_during_probe,
    )
    owner = HoloQueryServiceSupervisor(repo_root=tmp_path)

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        owner.start()

    assert error.value.code == "HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP"


@pytest.mark.parametrize(
    ("token_factory", "expected_code"),
    [
        (lambda _bytes: "short", "HOLOINDEX_QUERY_SERVICE_TOKEN_GENERATION_FAILED"),
        (
            lambda _bytes: (_ for _ in ()).throw(RuntimeError("entropy unavailable")),
            "HOLOINDEX_QUERY_SERVICE_TOKEN_GENERATION_FAILED",
        ),
    ],
)
def test_token_generation_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    token_factory: Any,
    expected_code: str,
) -> None:
    monkeypatch.setattr(
        supervisor_module.secrets,
        "token_urlsafe",
        token_factory,
    )
    owner = HoloQueryServiceSupervisor(repo_root=tmp_path)

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        owner.start()

    assert error.value.code == expected_code


def test_spawn_and_repo_root_failures_use_stable_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_root = HoloQueryServiceSupervisor(repo_root=tmp_path / "missing")
    with pytest.raises(HoloQueryServiceSupervisorError) as missing_error:
        missing_root.start()
    assert (
        missing_error.value.code
        == "HOLOINDEX_QUERY_SERVICE_REPO_ROOT_UNAVAILABLE"
    )

    monkeypatch.setattr(
        supervisor_module.secrets,
        "token_urlsafe",
        lambda _bytes: TOKEN,
    )
    monkeypatch.setattr(
        supervisor_module.subprocess,
        "Popen",
        lambda _command, **_kwargs: (_ for _ in ()).throw(OSError("blocked")),
    )
    owner = HoloQueryServiceSupervisor(repo_root=tmp_path)
    with pytest.raises(HoloQueryServiceSupervisorError) as spawn_error:
        owner.start()
    assert spawn_error.value.code == "HOLOINDEX_QUERY_SERVICE_SPAWN_FAILED"
    assert TOKEN not in str(spawn_error.value)


def test_stop_kills_owner_that_ignores_terminate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess(wait_timeouts=1)
    _install_successful_start(monkeypatch, process)
    monkeypatch.setattr(supervisor_module.atexit, "register", lambda _callback: None)
    monkeypatch.setattr(supervisor_module.atexit, "unregister", lambda _callback: None)
    owner = HoloQueryServiceSupervisor(repo_root=tmp_path).start()

    owner.stop()

    assert process.terminated is True
    assert process.killed is True
    assert process.wait_calls == 2


def test_context_manager_stops_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess()
    _install_successful_start(monkeypatch, process)
    monkeypatch.setattr(supervisor_module.atexit, "register", lambda _callback: None)
    monkeypatch.setattr(supervisor_module.atexit, "unregister", lambda _callback: None)

    with HoloQueryServiceSupervisor(repo_root=tmp_path) as owner:
        assert owner.is_ready is True

    assert process.terminated is True
    assert owner.is_ready is False


def test_health_probe_requires_exact_authenticated_ready_contract() -> None:
    observed_authorization: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
            observed_authorization.append(self.headers.get("Authorization", ""))
            payload = json.dumps(
                {
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
                    "repo_head_sha": "a" * 40,
                    "freshness_generation_id": "sha256:generation",
                    "freshness_receipt_digest": "sha256:receipt",
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args: object) -> None:
            return

    server = ThreadingHTTPServer((OWNER_HOST, 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert supervisor_module._authenticated_health_probe(
            host=OWNER_HOST,
            port=server.server_address[1],
            token=TOKEN,
            timeout_seconds=1.0,
        )
        assert observed_authorization == [f"Bearer {TOKEN}"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _binding_health_handler() -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            payload = json.dumps(
                {
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
                    "repo_head_sha": "a" * 40,
                    "freshness_generation_id": "sha256:generation",
                    "freshness_receipt_digest": "sha256:receipt",
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args: object) -> None:
            return

    return Handler


def test_health_probe_rejects_expected_binding_mismatch() -> None:
    server = ThreadingHTTPServer(
        (OWNER_HOST, 0),
        _binding_health_handler(),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert not supervisor_module._authenticated_health_probe(
            host=OWNER_HOST,
            port=server.server_address[1],
            token=TOKEN,
            timeout_seconds=1.0,
            expected_repo_head_sha="b" * 40,
            expected_generation_id="sha256:generation",
        )
        assert not supervisor_module._authenticated_health_probe(
            host=OWNER_HOST,
            port=server.server_address[1],
            token=TOKEN,
            timeout_seconds=1.0,
            expected_repo_head_sha="a" * 40,
            expected_generation_id="sha256:generation",
            expected_receipt_digest="sha256:other",
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_health_probe_rejects_non_loopback_without_sending_secret() -> None:
    assert (
        supervisor_module._authenticated_health_probe(
            host="localhost",
            port=8127,
            token=TOKEN,
            timeout_seconds=1.0,
        )
        is False
    )


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (503, b"{}"),
        (200, b"not-json"),
        (200, b"[]"),
    ],
)
def test_health_probe_rejects_error_and_malformed_responses(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    body: bytes,
) -> None:
    class Response:
        def __init__(self) -> None:
            self.status = status

        def read(self, _limit: int) -> bytes:
            return body

    class Connection:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        def request(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        def getresponse(self) -> Response:
            return Response()

        def close(self) -> None:
            pass

    monkeypatch.setattr(
        supervisor_module.http.client,
        "HTTPConnection",
        Connection,
    )
    assert (
        supervisor_module._authenticated_health_probe(
            host=OWNER_HOST,
            port=8127,
            token=TOKEN,
            timeout_seconds=1.0,
        )
        is False
    )
