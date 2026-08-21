"""Supervisor authenticated health-boundary contracts."""

from .holo_query_service_supervisor_support import *  # noqa: F401,F403

@pytest.mark.parametrize(
    "kind",
    ["dict-subclass", "mapping", "user-dict", "mapping-proxy", "list", "string", "object"],
)
def test_all_health_seams_reject_non_exact_dict_without_method_calls(
    kind: str,
) -> None:
    payload, calls = _malformed_health_container(kind)
    expected = dict(
        expected_repo_head_sha="",
        expected_repo_root_digest="",
        expected_generation_id="",
        expected_receipt_digest="",
        expected_replica_binding=REPLICA_BINDING,
    )

    assert health_module._health_binding(payload) == ("", "", "", "")  # type: ignore[arg-type]
    assert health_module._health_replica_binding(payload) == ("", "", "", "")  # type: ignore[arg-type]
    assert health_module._health_rejection_code(payload) == ""  # type: ignore[arg-type]
    assert health_module._health_binding_rejection_code(payload, **expected) == ""  # type: ignore[arg-type]
    assert not health_module._health_contract_ready(payload, **expected)  # type: ignore[arg-type]
    assert calls == []

@pytest.mark.parametrize(
    "kind",
    ["dict-subclass", "mapping", "user-dict", "mapping-proxy", "list", "string", "object"],
)
def test_json_decoder_rejects_non_exact_dict_without_method_calls(
    kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload, calls = _malformed_health_container(kind)

    class Response:
        status = 200

        def read(self, _limit: int) -> bytes:
            return b"{}"

    connection = Mock()
    connection.getresponse.return_value = Response()
    monkeypatch.setattr(
        health_module.json, "loads", lambda _value, **_kwargs: payload,
    )

    assert health_module._read_health_payload(connection, TOKEN) is None
    assert calls == []

@pytest.mark.parametrize(
    "kind",
    ["dict-subclass", "mapping", "user-dict", "mapping-proxy", "list", "string", "object"],
)
def test_authenticated_exchange_rejects_non_exact_dict_without_formatting(
    kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload, calls = _malformed_health_container(kind)
    connection = Mock()
    monkeypatch.setattr(health_module, "_read_health_payload", lambda *_args: payload)
    monkeypatch.setattr(
        health_module.http.client, "HTTPConnection", lambda *_args, **_kwargs: connection,
    )

    proof = health_module._authenticated_health_exchange(
        host=OWNER_HOST,
        port=8127,
        token=TOKEN,
        timeout_seconds=1.0,
        expected_replica_binding=REPLICA_BINDING,
    )

    assert proof == health_module.AuthenticatedOwnerHealthProof(
        False, "", ("", "", "", "")
    )
    assert calls == []
    connection.close.assert_called_once_with()

def test_json_decoder_admits_exact_plain_dict() -> None:
    payload = _ready_health_payload(replica_binding=REPLICA_BINDING)

    class Response:
        status = 200

        def read(self, _limit: int) -> bytes:
            return json.dumps(payload).encode("utf-8")

    connection = Mock()
    connection.getresponse.return_value = Response()

    observed = health_module._read_health_payload(connection, TOKEN)

    assert type(observed) is dict
    assert observed == payload

@pytest.mark.parametrize(
    "key",
    (
        "schema_version", "ok", "source", "status", "loopback_only",
        "freshness", "error", "stale_reasons", "index_gap_detected",
        "no_holoindex_reindex_performed", "retrieval_mode", "repo_head_sha",
        "repo_root_digest", "freshness_generation_id",
        "freshness_receipt_digest", "query_replica_descriptor_digest",
        "query_replica_generation_id", "query_replica_id",
        "query_replica_path_identity_digest",
    ),
)
def test_duplicate_health_keys_never_admit_ready_or_terminal(
    key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = _install_health_json_response(
        monkeypatch, _duplicate_health_key_body(key),
    )

    proof = _exchange_health_json()

    assert proof == health_module.AuthenticatedOwnerHealthProof(
        False, "", ("", "", "", ""), ("", "", "", ""),
    )
    _assert_complete_health_exchange(events)

def test_nested_duplicate_health_key_is_rejected_at_any_depth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = _health_json_body_with_prefix('"extra":{"key":1,"key":2},')
    events = _install_health_json_response(monkeypatch, body)

    proof = _exchange_health_json()

    assert not proof.ready
    assert proof.rejection == ""
    _assert_complete_health_exchange(events)

@pytest.mark.parametrize("constant", ("NaN", "Infinity", "-Infinity"))
def test_nonstandard_json_constants_never_admit_ready(
    constant: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = _health_json_body_with_prefix(f'"extra":{constant},')
    events = _install_health_json_response(monkeypatch, body)

    proof = _exchange_health_json()

    assert not proof.ready
    assert proof.rejection == ""
    _assert_complete_health_exchange(events)

def test_unique_deep_health_json_below_recursion_limit_remains_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nested = "[" * 64 + "0" + "]" * 64
    body = _health_json_body_with_prefix(f'"extra":{nested},')
    events = _install_health_json_response(monkeypatch, body)

    proof = _exchange_health_json()

    assert proof.ready
    _assert_complete_health_exchange(events)

def test_health_json_over_recursion_limit_fails_closed_without_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nested = "[" * 2_000 + "0" + "]" * 2_000
    body = _health_json_body_with_prefix(f'"extra":{nested},')
    events = _install_health_json_response(monkeypatch, body)

    proof = _exchange_health_json()

    assert not proof.ready
    assert proof.rejection == ""
    _assert_complete_health_exchange(events)

@pytest.mark.parametrize(
    ("body", "status"),
    (
        pytest.param(b"null", 200, id="null"),
        pytest.param(b"true", 200, id="boolean"),
        pytest.param(b"7", 200, id="number"),
        pytest.param(b'"text"', 200, id="string"),
        pytest.param(b"[]", 200, id="array"),
        pytest.param(b"{", 200, id="malformed"),
        pytest.param(b"\xff", 200, id="invalid-utf8"),
        pytest.param(b" " * 65_537, 200, id="oversized"),
        pytest.param(b"{}", 201, id="invalid-status"),
    ),
)
def test_invalid_health_json_representations_close_exactly_once(
    body: bytes,
    status: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = _install_health_json_response(monkeypatch, body, status=status)

    proof = _exchange_health_json()

    assert not proof.ready
    assert proof.rejection == ""
    _assert_complete_health_exchange(events)

def test_incomplete_health_read_fails_closed_with_partial_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failure = http.client.IncompleteRead(b'{"ok":', 19)
    events = _install_health_transport_failure(
        monkeypatch, stage="read", failure=failure,
    )

    proof = _exchange_health_json()

    assert failure.partial == b'{"ok":'
    assert not proof.ready
    assert proof.rejection == ""
    assert events == ["connect", "request", "getresponse", "read", "close"]

@pytest.mark.parametrize(
    ("stage", "failure"),
    (
        pytest.param("getresponse", http.client.BadStatusLine("bad"), id="bad-status"),
        pytest.param(
            "getresponse", http.client.RemoteDisconnected("closed"),
            id="remote-disconnected",
        ),
        pytest.param(
            "getresponse", http.client.ResponseNotReady(), id="response-not-ready",
        ),
        pytest.param(
            "request", http.client.CannotSendRequest(), id="cannot-send-request",
        ),
    ),
)
def test_http_exception_family_returns_unavailable_and_closes(
    stage: str,
    failure: Exception,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = _install_health_transport_failure(
        monkeypatch, stage=stage, failure=failure,
    )

    proof = _exchange_health_json()

    assert not proof.ready
    assert proof.rejection == ""
    expected = ["connect", "request"]
    if stage == "getresponse":
        expected.append("getresponse")
    assert events == expected + ["close"]

@pytest.mark.parametrize("stage", ("request", "getresponse", "read"))
@pytest.mark.parametrize(
    "failure", (TimeoutError("timeout"), OSError("transport")),
    ids=("timeout", "os-error"),
)
def test_health_timeout_and_oserror_controls_preserve_close_order(
    stage: str,
    failure: Exception,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = _install_health_transport_failure(
        monkeypatch, stage=stage, failure=failure,
    )

    proof = _exchange_health_json()

    assert not proof.ready
    assert proof.rejection == ""
    expected = ["connect", "request"]
    if stage in {"getresponse", "read"}:
        expected.append("getresponse")
    if stage == "read":
        expected.append("read")
    assert events == expected + ["close"]

@pytest.mark.parametrize(
    "close_failure",
    (http.client.HTTPException("close"), OSError("close")),
    ids=("http-exception", "os-error"),
)
def test_close_transport_failure_does_not_mask_ready_result(
    close_failure: Exception,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = _install_health_transport_failure(
        monkeypatch, close_failure=close_failure,
    )

    proof = _exchange_health_json()

    assert proof.ready
    assert events == ["connect", "request", "getresponse", "read", "close"]

def test_close_oserror_does_not_mask_prior_http_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = _install_health_transport_failure(
        monkeypatch, stage="request", failure=http.client.CannotSendRequest(),
        close_failure=OSError("close"),
    )

    proof = _exchange_health_json()

    assert not proof.ready
    assert proof.rejection == ""
    assert events == ["connect", "request", "close"]

@pytest.mark.parametrize(("field", "kind"), _INVALID_TRANSPORT_CASES)
def test_health_exchange_rejects_transport_scalars_before_methods_or_connection(
    field: str,
    kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    connection = Mock(side_effect=AssertionError("invalid transport connected"))
    monkeypatch.setattr(health_module.http.client, "HTTPConnection", connection)
    kwargs: dict[str, object] = {
        "host": OWNER_HOST, "port": 8127, "token": TOKEN,
        "timeout_seconds": 1.0, "expected_replica_binding": REPLICA_BINDING,
    }
    kwargs[field] = _invalid_transport_value(kind, calls)

    proof = health_module._authenticated_health_exchange(**kwargs)  # type: ignore[arg-type]

    assert proof == health_module.AuthenticatedOwnerHealthProof(
        False, "", ("", "", "", "")
    )
    assert calls == []
    connection.assert_not_called()

@pytest.mark.parametrize(
    "kind",
    [
        "hostile", "str-subclass", "bool", "bytes", "none", "mapping",
        "generator", "empty", "whitespace", "control", "short",
    ],
)
def test_read_health_payload_rejects_token_before_request_or_formatting(
    kind: str,
) -> None:
    calls: list[str] = []
    connection = Mock()

    assert health_module._read_health_payload(  # type: ignore[arg-type]
        connection, _invalid_transport_value(kind, calls)
    ) is None
    assert calls == []
    connection.request.assert_not_called()

def test_health_wrappers_inherit_hostile_transport_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    connection = Mock(side_effect=AssertionError("wrapper connected"))
    monkeypatch.setattr(health_module.http.client, "HTTPConnection", connection)
    kwargs = dict(
        host=OWNER_HOST, port=_HostileTransport(calls), token=TOKEN,
        timeout_seconds=1.0, expected_replica_binding=REPLICA_BINDING,
    )

    assert not health_module._authenticated_health_probe(**kwargs)
    assert health_module._authenticated_health_rejection(**kwargs) == ""
    assert calls == []
    connection.assert_not_called()

def test_expected_binding_rejects_before_hostile_transport_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    connection = Mock(side_effect=AssertionError("invalid expected connected"))
    monkeypatch.setattr(health_module.http.client, "HTTPConnection", connection)

    proof = health_module._authenticated_health_exchange(
        host=_HostileTransport(calls),  # type: ignore[arg-type]
        port=8127, token=TOKEN, timeout_seconds=1.0,
        expected_repo_head_sha=_HostileTransport(calls),  # type: ignore[arg-type]
        expected_replica_binding=REPLICA_BINDING,
    )

    assert proof.rejection == supervisor_module.BINDING_MISMATCH_ERROR
    assert calls == []
    connection.assert_not_called()

@pytest.mark.parametrize(
    "kind",
    [
        "string", "list", "tuple-subclass", "hostile", "partial", "bytes",
        "mapping", "generator", "bool-element", "whitespace", "empty", "over",
    ],
)
def test_expected_replica_rejects_before_connection_or_methods(
    kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    connection = Mock(side_effect=AssertionError("invalid replica connected"))
    monkeypatch.setattr(health_module.http.client, "HTTPConnection", connection)

    proof = health_module._authenticated_health_exchange(
        host=OWNER_HOST, port=8127, token=TOKEN, timeout_seconds=1.0,
        expected_replica_binding=_invalid_replica_expectation(kind, calls),
    )

    assert proof == health_module.AuthenticatedOwnerHealthProof(
        False, supervisor_module.BINDING_MISMATCH_ERROR,
        ("", "", "", ""), ("", "", "", ""),
    )
    assert calls == []
    connection.assert_not_called()

def test_health_wrappers_inherit_hostile_replica_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    connection = Mock(side_effect=AssertionError("wrapper connected"))
    monkeypatch.setattr(health_module.http.client, "HTTPConnection", connection)
    kwargs = dict(
        host=OWNER_HOST, port=8127, token=TOKEN, timeout_seconds=1.0,
        expected_replica_binding=_HostileReplicaExpectation(calls),
    )

    assert not health_module._authenticated_health_probe(**kwargs)
    assert (
        health_module._authenticated_health_rejection(**kwargs)
        == supervisor_module.BINDING_MISMATCH_ERROR
    )
    assert calls == []
    connection.assert_not_called()

def test_malformed_canonical_precedes_replica_and_transport_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    connection = Mock(side_effect=AssertionError("invalid expectations connected"))
    monkeypatch.setattr(health_module.http.client, "HTTPConnection", connection)

    proof = health_module._authenticated_health_exchange(
        host=_HostileTransport(calls), port=8127, token=TOKEN,
        timeout_seconds=1.0,
        expected_repo_head_sha=_HostileTransport(calls),
        expected_replica_binding=_HostileReplicaExpectation(calls),
    )

    assert proof.rejection == supervisor_module.BINDING_MISMATCH_ERROR
    assert calls == []
    connection.assert_not_called()

def test_valid_replica_and_transport_construct_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = Mock()
    monkeypatch.setattr(health_module, "_read_health_payload", lambda *_args: None)
    constructor = Mock(return_value=connection)
    monkeypatch.setattr(health_module.http.client, "HTTPConnection", constructor)

    health_module._authenticated_health_exchange(
        host=OWNER_HOST, port=8127, token=TOKEN, timeout_seconds=1.0,
        expected_replica_binding=REPLICA_BINDING,
    )

    constructor.assert_called_once_with(OWNER_HOST, 8127, timeout=1.0)

@pytest.mark.parametrize(
    ("field", "value"),
    [("host", OWNER_HOST), ("token", "x" * 32), ("port", 1), ("port", 65535),
     ("timeout_seconds", 1), ("timeout_seconds", 0.01), ("timeout_seconds", 300.0)],
)
def test_health_exchange_admits_exact_transport_controls(
    field: str,
    value: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = Mock()
    monkeypatch.setattr(health_module, "_read_health_payload", lambda *_args: None)
    constructor = Mock(return_value=connection)
    monkeypatch.setattr(health_module.http.client, "HTTPConnection", constructor)
    kwargs: dict[str, object] = {
        "host": OWNER_HOST, "port": 8127, "token": TOKEN,
        "timeout_seconds": 1.0, "expected_replica_binding": REPLICA_BINDING,
    }
    kwargs[field] = value

    health_module._authenticated_health_exchange(**kwargs)  # type: ignore[arg-type]

    constructor.assert_called_once_with(
        kwargs["host"], kwargs["port"], timeout=float(kwargs["timeout_seconds"])
    )

def test_health_rejection_never_invokes_hostile_metadata_methods() -> None:
    calls: list[str] = []
    payload = _ready_health_payload(replica_binding=REPLICA_BINDING)
    payload["error"] = _HostileField(calls)
    expected = dict(
        expected_repo_head_sha="",
        expected_repo_root_digest="",
        expected_generation_id="",
        expected_receipt_digest="",
        expected_replica_binding=REPLICA_BINDING,
    )

    assert not supervisor_module._health_contract_ready(payload, **expected)
    assert supervisor_module._health_rejection_code(payload) == ""
    assert supervisor_module._health_binding_rejection_code(payload, **expected) == ""
    assert calls == []

def test_startup_rejects_malformed_ready_proof_replica_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess()
    _install_successful_start(monkeypatch, process)
    monkeypatch.setattr(
        supervisor_module,
        "_authenticated_health_exchange",
        lambda **_kwargs: supervisor_module.AuthenticatedOwnerHealthProof(
            ready=True,
            rejection="",
            binding=("a" * 40, "root", "generation", "receipt"),
            replica_binding=("descriptor", "generation", True, "path"),  # type: ignore[arg-type]
        ),
    )
    owner = HoloQueryServiceSupervisor(repo_root=tmp_path)

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        owner.start()

    assert error.value.code == supervisor_module.BINDING_MISMATCH_ERROR
    assert owner.is_ready is False

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

    def exit_during_probe(**_kwargs: Any):
        process.returncode = 9
        return supervisor_module.AuthenticatedOwnerHealthProof(
            True,
            "",
            (
                "a" * 40,
                "sha256:" + ("d" * 64),
                "sha256:" + ("b" * 64),
                "sha256:" + ("c" * 64),
            ),
        )

    monkeypatch.setattr(
        supervisor_module,
        "_authenticated_health_exchange",
        exit_during_probe,
    )
    owner = HoloQueryServiceSupervisor(repo_root=tmp_path)

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        owner.start()

    assert error.value.code == "HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP"
