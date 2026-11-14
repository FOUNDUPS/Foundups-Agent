"""Supervisor lifecycle and live-probe contracts."""

from .holo_query_service_supervisor_support import *  # noqa: F401,F403

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

def test_occupied_port_fails_before_process_spawn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spawned: list[bool] = []
    tokens: list[bool] = []
    monkeypatch.setattr(
        supervisor_module.secrets,
        "token_urlsafe",
        lambda _bytes: tokens.append(True) or TOKEN,
    )
    monkeypatch.setattr(
        supervisor_module,
        "_owner_port_available",
        lambda _host, _port: False,
    )
    monkeypatch.setattr(
        supervisor_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: spawned.append(True),
    )

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        HoloQueryServiceSupervisor(repo_root=tmp_path).start()

    assert error.value.code == supervisor_module.PORT_IN_USE_ERROR
    assert spawned == []
    assert tokens == []

def test_port_probe_detects_real_loopback_listener(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.undo()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind((OWNER_HOST, 0))
        listener.listen(1)
        port = int(listener.getsockname()[1])
        assert supervisor_module._owner_port_available(OWNER_HOST, port) is False

    assert supervisor_module._owner_port_available(OWNER_HOST, port) is True

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

def test_context_manager_without_full_route_fails_closed(tmp_path: Path) -> None:
    owner = _RawHoloQueryServiceSupervisor(repo_root=tmp_path)

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        with owner:
            pytest.fail("route-less context must not enter")

    assert error.value.code == "HOLOINDEX_QUERY_REPLICA_REQUIRED"
    assert not owner.is_ready

def test_health_probe_requires_exact_authenticated_ready_contract() -> None:
    observed_authorization: list[str] = []
    server = ThreadingHTTPServer(
        (OWNER_HOST, 0), _binding_health_handler(observed_authorization),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert supervisor_module._authenticated_health_probe(
            host=OWNER_HOST,
            port=server.server_address[1],
            token=TOKEN,
            timeout_seconds=1.0,
            expected_replica_binding=REPLICA_BINDING,
        )
        assert observed_authorization == [f"Bearer {TOKEN}"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

def test_health_probe_accepts_semantic_response_beyond_legacy_one_second() -> None:
    server = ThreadingHTTPServer((OWNER_HOST, 0), _slow_semantic_health_handler())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert DEFAULT_OWNER_PROBE_TIMEOUT_SECONDS == 30.0
        assert supervisor_module._authenticated_health_probe(
            host=OWNER_HOST,
            port=int(server.server_address[1]),
            token=TOKEN,
            timeout_seconds=DEFAULT_OWNER_PROBE_TIMEOUT_SECONDS,
            expected_replica_binding=REPLICA_BINDING,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

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
            expected_repo_root_digest="sha256:" + ("d" * 64),
            expected_generation_id="sha256:generation",
            expected_replica_binding=REPLICA_BINDING,
        )
        assert not supervisor_module._authenticated_health_probe(
            host=OWNER_HOST,
            port=server.server_address[1],
            token=TOKEN,
            timeout_seconds=1.0,
            expected_repo_head_sha="a" * 40,
            expected_repo_root_digest="sha256:" + ("e" * 64),
            expected_generation_id="sha256:generation",
            expected_replica_binding=REPLICA_BINDING,
        )
        assert not supervisor_module._authenticated_health_probe(
            host=OWNER_HOST,
            port=server.server_address[1],
            token=TOKEN,
            timeout_seconds=1.0,
            expected_repo_head_sha="a" * 40,
            expected_repo_root_digest="sha256:" + ("d" * 64),
            expected_generation_id="sha256:generation",
            expected_receipt_digest="sha256:other",
            expected_replica_binding=REPLICA_BINDING,
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

@pytest.mark.parametrize(
    ("status", "error"),
    (
        (400, "QUERY_OWNER_POISONED"),
        (503, "SEMANTIC_BACKEND_UNAVAILABLE"),
        (504, "QUERY_TIMEOUT"),
    ),
)
def test_health_exchange_reads_authenticated_terminal_error(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    error: str,
) -> None:
    payload = {
        "schema_version": HEALTH_SCHEMA_VERSION,
        "ok": False,
        "source": "holoindex",
        "loopback_only": True,
        "no_holoindex_reindex_performed": True,
        "error": error,
    }

    class Response:
        def __init__(self) -> None:
            self.status = status

        def read(self, _limit: int) -> bytes:
            return json.dumps(payload).encode("utf-8")

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
        supervisor_module.http.client, "HTTPConnection", Connection
    )
    assert supervisor_module._authenticated_health_rejection(
        host=OWNER_HOST,
        port=8127,
        token=TOKEN,
        timeout_seconds=1.0,
        expected_replica_binding=REPLICA_BINDING,
    ) == error
