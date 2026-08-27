"""Supervisor canonical and replica binding contracts."""

from .holo_query_service_supervisor_support import *  # noqa: F401,F403

@pytest.mark.skipif(os.name != "nt", reason="Windows checkout-local venv contract")
def test_supervisor_prefers_checkout_local_runtime_packages(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "authority"
    runtime_root = tmp_path / "workspace"
    site_packages = runtime_root / ".venv" / "Lib" / "site-packages"
    repo_root.mkdir()
    site_packages.mkdir(parents=True)
    (runtime_root / ".venv" / "pyvenv.cfg").write_text(
        "\n".join(
            (
                f"home = {Path(sys._base_executable).parent}",
                "include-system-site-packages = false",
                f"version = {sys.version_info.major}.{sys.version_info.minor}.0",
                f"executable = {sys._base_executable}",
            )
        ),
        encoding="utf-8",
    )

    owner = HoloQueryServiceSupervisor(
        repo_root=repo_root,
        runtime_root=runtime_root,
        python_executable=sys.executable,
    )

    assert owner.runtime_root == runtime_root.resolve()
    assert owner._pythonpath_entries == (str(site_packages.resolve()),)

    alternate = tmp_path / "different-python.exe"
    alternate_owner = HoloQueryServiceSupervisor(
        repo_root=repo_root,
        runtime_root=runtime_root,
        python_executable=alternate,
    )
    assert alternate_owner.python_executable == str(alternate)
    assert alternate_owner._pythonpath_entries == ()

@pytest.mark.skipif(os.name != "nt", reason="Windows checkout-local venv contract")
def test_supervisor_rejects_unbound_virtualenv_package_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        supervisor_module,
        "_owner_python_runtime",
        lambda _executable: ("python.exe", ("C:/attacker/site-packages",)),
    )
    monkeypatch.setattr(
        supervisor_module,
        "trusted_holo_site_packages",
        lambda _root, **_kwargs: (),
    )

    owner = HoloQueryServiceSupervisor(
        repo_root=tmp_path / "authority",
        runtime_root=tmp_path / "missing-runtime",
        python_executable=sys.executable,
    )

    assert owner.python_executable == "python.exe"
    assert owner._pythonpath_entries == ()

def test_health_rejection_treats_authenticated_ready_binding_mismatch_as_terminal(
) -> None:
    payload = {
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
        "repo_head_sha": "a" * 40,
        "repo_root_digest": "sha256:" + ("d" * 64),
        "freshness_generation_id": "sha256:" + ("b" * 64),
        "freshness_receipt_digest": "sha256:" + ("c" * 64),
        "query_replica_descriptor_digest": REPLICA_BINDING[0],
        "query_replica_generation_id": REPLICA_BINDING[1],
        "query_replica_id": REPLICA_BINDING[2],
        "query_replica_path_identity_digest": REPLICA_BINDING[3],
    }

    assert (
        supervisor_module._health_binding_rejection_code(
            payload,
            expected_repo_head_sha="d" * 40,
            expected_repo_root_digest="sha256:" + ("d" * 64),
            expected_generation_id="sha256:" + ("b" * 64),
            expected_receipt_digest="sha256:" + ("c" * 64),
            expected_replica_binding=REPLICA_BINDING,
        )
        == supervisor_module.BINDING_MISMATCH_ERROR
    )
    assert (
        supervisor_module._health_binding_rejection_code(
            payload,
            expected_repo_head_sha="a" * 40,
            expected_repo_root_digest="sha256:" + ("d" * 64),
            expected_generation_id="sha256:" + ("b" * 64),
            expected_receipt_digest="sha256:" + ("c" * 64),
            expected_replica_binding=REPLICA_BINDING,
        )
        == ""
    )

def test_health_requires_all_four_replica_fields_when_replica_is_expected() -> None:
    payload = {
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
        "repo_head_sha": "a" * 40,
        "repo_root_digest": "sha256:" + ("d" * 64),
        "freshness_generation_id": "sha256:" + ("b" * 64),
        "freshness_receipt_digest": "sha256:" + ("c" * 64),
        "query_replica_descriptor_digest": REPLICA_BINDING[0],
        "query_replica_generation_id": REPLICA_BINDING[1],
        "query_replica_id": REPLICA_BINDING[2],
        "query_replica_path_identity_digest": REPLICA_BINDING[3],
    }
    canonical = dict(
        expected_repo_head_sha="a" * 40,
        expected_repo_root_digest="sha256:" + ("d" * 64),
        expected_generation_id="sha256:" + ("b" * 64),
        expected_receipt_digest="sha256:" + ("c" * 64),
    )
    replica = ("descriptor", "generation", "replica", "path")

    assert supervisor_module._health_contract_ready(
        payload, **canonical, expected_replica_binding=replica
    )
    assert not supervisor_module._health_contract_ready(
        {**payload, "query_replica_id": ""},
        **canonical,
        expected_replica_binding=replica,
    )
    assert not supervisor_module._health_contract_ready(
        payload,
        **canonical,
        expected_replica_binding=("descriptor", "", "replica", "path"),
    )
    assert supervisor_module._health_binding_rejection_code(
        {**payload, "query_replica_id": ""},
        **canonical,
        expected_replica_binding=replica,
    ) == supervisor_module.BINDING_MISMATCH_ERROR

def test_health_without_complete_expected_replica_binding_is_never_ready() -> None:
    payload = {
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
        "repo_head_sha": "a" * 40,
        "repo_root_digest": "sha256:" + ("d" * 64),
        "freshness_generation_id": "sha256:" + ("b" * 64),
        "freshness_receipt_digest": "sha256:" + ("c" * 64),
    }
    canonical = dict(
        expected_repo_head_sha="a" * 40,
        expected_repo_root_digest="sha256:" + ("d" * 64),
        expected_generation_id="sha256:" + ("b" * 64),
        expected_receipt_digest="sha256:" + ("c" * 64),
    )

    assert not supervisor_module._health_contract_ready(payload, **canonical)
    assert not supervisor_module._health_contract_ready(
        payload,
        **canonical,
        expected_replica_binding=("descriptor", "", "replica", "path"),
    )

def test_supervisor_partial_replica_binding_fails_before_spawn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spawn = Mock(side_effect=AssertionError("partial binding must not spawn"))
    monkeypatch.setattr(supervisor_module.subprocess, "Popen", spawn)
    owner = _RawHoloQueryServiceSupervisor(
        repo_root=tmp_path,
        canonical_ssd_path=tmp_path / "canonical",
        query_replica_root=tmp_path / "replica",
        replica_capability_verifier=lambda: object(),
    )

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        owner.start(
            expected_replica_binding=("descriptor", "", "replica", "path")
        )

    assert error.value.code == "HOLOINDEX_QUERY_REPLICA_REQUIRED"
    spawn.assert_not_called()

@pytest.mark.parametrize(
    "binding_factory",
    [
        pytest.param(lambda: "abcd", id="string"),
        pytest.param(lambda: ["a", "b", "c", "d"], id="list"),
        pytest.param(lambda: _TupleBinding(("a", "b", "c", "d")), id="tuple-subclass"),
        pytest.param(lambda: (_StringField("a"), "b", "c", "d"), id="str-subclass"),
        pytest.param(lambda: b"abcd", id="bytes"),
        pytest.param(lambda: {"a": 1, "b": 2, "c": 3, "d": 4}, id="mapping"),
        pytest.param(lambda: (item for item in ("a", "b", "c", "d")), id="generator"),
        pytest.param(lambda: (7, "b", "c", "d"), id="int-element"),
        pytest.param(lambda: (True, "b", "c", "d"), id="bool-element"),
        pytest.param(lambda: (" ", "b", "c", "d"), id="whitespace"),
        pytest.param(lambda: (" a ", "b", "c", "d"), id="surrounding-whitespace"),
        pytest.param(lambda: ("", "b", "c", "d"), id="empty"),
        pytest.param(lambda: ("a", "b", "c"), id="under-length"),
        pytest.param(lambda: ("a", "b", "c", "d", "e"), id="over-length"),
        pytest.param(lambda: (("a",), "b", "c", "d"), id="nested"),
    ],
)
def test_malformed_replica_start_binding_fails_before_every_side_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    binding_factory: Any,
) -> None:
    events: list[str] = []
    owner = _RawHoloQueryServiceSupervisor(
        repo_root=tmp_path,
        canonical_ssd_path=tmp_path / "canonical",
        query_replica_root=tmp_path / "replica",
        replica_capability_verifier=lambda: events.append("verify"),
        expected_replica_binding=REPLICA_BINDING,
    )
    monkeypatch.setattr(owner, "stop", lambda: events.append("stop"))
    monkeypatch.setattr(owner, "_spawn", lambda: events.append("spawn"))

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        owner.start(expected_replica_binding=binding_factory())  # type: ignore[arg-type]

    assert error.value.code == "HOLOINDEX_QUERY_REPLICA_REQUIRED"
    assert events == []

@pytest.mark.parametrize(
    "binding_factory",
    [
        pytest.param(lambda: "abcd", id="string"),
        pytest.param(lambda: ["a", "b", "c", "d"], id="list"),
        pytest.param(lambda: _TupleBinding(("a", "b", "c", "d")), id="tuple-subclass"),
        pytest.param(lambda: (_StringField("a"), "b", "c", "d"), id="str-subclass"),
        pytest.param(lambda: b"abcd", id="bytes"),
        pytest.param(lambda: {"a": 1, "b": 2, "c": 3, "d": 4}, id="mapping"),
        pytest.param(lambda: (item for item in ("a", "b", "c", "d")), id="generator"),
        pytest.param(lambda: (7, "b", "c", "d"), id="int-element"),
        pytest.param(lambda: (True, "b", "c", "d"), id="bool-element"),
        pytest.param(lambda: (" ", "b", "c", "d"), id="whitespace"),
        pytest.param(lambda: (" a ", "b", "c", "d"), id="surrounding-whitespace"),
        pytest.param(lambda: ("", "b", "c", "d"), id="empty"),
        pytest.param(lambda: ("a", "b", "c"), id="under-length"),
        pytest.param(lambda: ("a", "b", "c", "d", "e"), id="over-length"),
        pytest.param(lambda: (("a",), "b", "c", "d"), id="nested"),
    ],
)
def test_health_rejects_malformed_expected_replica_binding_without_raising(
    binding_factory: Any,
) -> None:
    payload = _ready_health_payload(replica_binding=REPLICA_BINDING)

    assert not supervisor_module._health_contract_ready(
        payload,
        expected_repo_head_sha=str(payload["repo_head_sha"]),
        expected_repo_root_digest=str(payload["repo_root_digest"]),
        expected_generation_id=str(payload["freshness_generation_id"]),
        expected_receipt_digest=str(payload["freshness_receipt_digest"]),
        expected_replica_binding=binding_factory(),  # type: ignore[arg-type]
    )

@pytest.mark.parametrize(
    ("actual_value", "formerly_coerced_value"),
    [
        pytest.param(7, "7", id="int"),
        pytest.param(True, "True", id="bool"),
        pytest.param(["replica"], "['replica']", id="list"),
        pytest.param({"replica": 1}, "{'replica': 1}", id="mapping"),
        pytest.param(_StringField("replica"), "replica", id="str-subclass"),
        pytest.param(" replica ", " replica ", id="surrounding-whitespace"),
    ],
)
def test_health_never_coerces_malformed_actual_replica_fields(
    actual_value: object,
    formerly_coerced_value: str,
) -> None:
    expected = (
        REPLICA_BINDING[0], REPLICA_BINDING[1],
        formerly_coerced_value, REPLICA_BINDING[3],
    )
    payload = _ready_health_payload(replica_binding=REPLICA_BINDING)
    payload["query_replica_id"] = actual_value
    canonical = dict(
        expected_repo_head_sha=str(payload["repo_head_sha"]),
        expected_repo_root_digest=str(payload["repo_root_digest"]),
        expected_generation_id=str(payload["freshness_generation_id"]),
        expected_receipt_digest=str(payload["freshness_receipt_digest"]),
        expected_replica_binding=expected,
    )

    assert not supervisor_module._health_contract_ready(payload, **canonical)
    assert (
        supervisor_module._health_binding_rejection_code(payload, **canonical)
        == supervisor_module.BINDING_MISMATCH_ERROR
    )

@pytest.mark.parametrize(
    "replica_binding",
    [
        pytest.param(("same", "same", "same", "same"), id="duplicates-allowed"),
        pytest.param(
            tuple("sha256:" + character * 64 for character in "abcd"),
            id="production-digest-shape",
        ),
    ],
)
def test_health_accepts_exact_valid_replica_bindings(
    replica_binding: tuple[str, str, str, str],
) -> None:
    payload = _ready_health_payload(replica_binding=replica_binding)

    assert supervisor_module._health_contract_ready(
        payload,
        expected_repo_head_sha=str(payload["repo_head_sha"]),
        expected_repo_root_digest=str(payload["repo_root_digest"]),
        expected_generation_id=str(payload["freshness_generation_id"]),
        expected_receipt_digest=str(payload["freshness_receipt_digest"]),
        expected_replica_binding=replica_binding,
    )

@pytest.mark.parametrize(
    "actual_value",
    [
        pytest.param(7, id="int"),
        pytest.param(True, id="bool"),
        pytest.param(["head"], id="list"),
        pytest.param({"head": 1}, id="mapping"),
        pytest.param(b"head", id="bytes"),
        pytest.param(_StringField("head"), id="str-subclass"),
        pytest.param(" ", id="whitespace"),
        pytest.param(" head ", id="surrounding-whitespace"),
        pytest.param("head\x00tail", id="nul"),
        pytest.param("head\x1ftail", id="control"),
        pytest.param(("head",), id="nested"),
    ],
)
def test_health_rejects_malformed_actual_canonical_fields_without_coercion(
    actual_value: object,
) -> None:
    payload = _ready_health_payload(replica_binding=REPLICA_BINDING)
    payload["repo_head_sha"] = actual_value
    expected = dict(
        expected_repo_head_sha="",
        expected_repo_root_digest="",
        expected_generation_id="",
        expected_receipt_digest="",
        expected_replica_binding=REPLICA_BINDING,
    )

    assert not supervisor_module._health_contract_ready(payload, **expected)
    assert (
        supervisor_module._health_binding_rejection_code(payload, **expected)
        == supervisor_module.BINDING_MISMATCH_ERROR
    )

def test_health_never_invokes_hostile_canonical_field_methods() -> None:
    calls: list[str] = []
    payload = _ready_health_payload(replica_binding=REPLICA_BINDING)
    payload["repo_head_sha"] = _HostileField(calls)
    expected = dict(
        expected_repo_head_sha="",
        expected_repo_root_digest="",
        expected_generation_id="",
        expected_receipt_digest="",
        expected_replica_binding=REPLICA_BINDING,
    )

    assert not supervisor_module._health_contract_ready(payload, **expected)
    assert (
        supervisor_module._health_binding_rejection_code(payload, **expected)
        == supervisor_module.BINDING_MISMATCH_ERROR
    )
    assert calls == []

@pytest.mark.parametrize(
    "expected_value",
    [
        pytest.param(7, id="int"),
        pytest.param(True, id="bool"),
        pytest.param(["head"], id="list"),
        pytest.param({"head": 1}, id="mapping"),
        pytest.param(b"head", id="bytes"),
        pytest.param(_StringField("head"), id="str-subclass"),
        pytest.param(" ", id="whitespace"),
        pytest.param(" head ", id="surrounding-whitespace"),
        pytest.param("head\x00tail", id="nul"),
        pytest.param("head\x1ftail", id="control"),
        pytest.param(("head",), id="nested"),
    ],
)
def test_health_rejects_malformed_expected_canonical_fields(
    expected_value: object,
) -> None:
    payload = _ready_health_payload(replica_binding=REPLICA_BINDING)
    expected = dict(
        expected_repo_head_sha=expected_value,
        expected_repo_root_digest="",
        expected_generation_id="",
        expected_receipt_digest="",
        expected_replica_binding=REPLICA_BINDING,
    )

    assert not supervisor_module._health_contract_ready(payload, **expected)
    assert (
        supervisor_module._health_binding_rejection_code(payload, **expected)
        == supervisor_module.BINDING_MISMATCH_ERROR
    )

def test_health_never_invokes_hostile_expected_canonical_methods() -> None:
    calls: list[str] = []
    payload = _ready_health_payload(replica_binding=REPLICA_BINDING)
    expected = dict(
        expected_repo_head_sha=_HostileField(calls),
        expected_repo_root_digest="",
        expected_generation_id="",
        expected_receipt_digest="",
        expected_replica_binding=REPLICA_BINDING,
    )

    assert not supervisor_module._health_contract_ready(payload, **expected)
    assert (
        supervisor_module._health_binding_rejection_code(payload, **expected)
        == supervisor_module.BINDING_MISMATCH_ERROR
    )
    assert calls == []

@pytest.mark.parametrize(
    "expected",
    [
        pytest.param(("", "sha256:" + "d" * 64, "", "sha256:" + "c" * 64), id="mixed-wildcards"),
        pytest.param(
            (
                "a" * 40,
                "sha256:" + "d" * 64,
                "sha256:" + "b" * 64,
                "sha256:" + "c" * 64,
            ),
            id="full-production-shape",
        ),
    ],
)
def test_health_accepts_exact_canonical_controls(
    expected: tuple[str, str, str, str],
) -> None:
    payload = _ready_health_payload(replica_binding=REPLICA_BINDING)

    assert supervisor_module._health_contract_ready(
        payload,
        expected_repo_head_sha=expected[0],
        expected_repo_root_digest=expected[1],
        expected_generation_id=expected[2],
        expected_receipt_digest=expected[3],
        expected_replica_binding=REPLICA_BINDING,
    )

def test_malformed_expected_canonical_fails_before_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    connection = Mock(side_effect=AssertionError("invalid expected binding connected"))
    monkeypatch.setattr(supervisor_module.http.client, "HTTPConnection", connection)

    proof = supervisor_module._authenticated_health_exchange(
        host=OWNER_HOST,
        port=8127,
        token=TOKEN,
        timeout_seconds=1.0,
        expected_repo_head_sha=_HostileField(calls),  # type: ignore[arg-type]
        expected_replica_binding=REPLICA_BINDING,
    )

    assert proof.ready is False
    assert proof.rejection == supervisor_module.BINDING_MISMATCH_ERROR
    assert calls == []
    connection.assert_not_called()

def test_malformed_canonical_start_binding_fails_before_side_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    events: list[str] = []
    owner = _RawHoloQueryServiceSupervisor(
        repo_root=tmp_path,
        canonical_ssd_path=tmp_path / "canonical",
        query_replica_root=tmp_path / "replica",
        replica_capability_verifier=lambda: events.append("verify"),
        expected_replica_binding=REPLICA_BINDING,
    )
    monkeypatch.setattr(owner, "stop", lambda: events.append("stop"))
    monkeypatch.setattr(owner, "_spawn", lambda: events.append("spawn"))

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        owner.start(expected_repo_head_sha=_HostileField(calls))  # type: ignore[arg-type]

    assert error.value.code == supervisor_module.BINDING_MISMATCH_ERROR
    assert calls == []
    assert events == []

def test_startup_rejects_hostile_ready_proof_canonical_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    process = _FakeProcess()
    _install_successful_start(monkeypatch, process)
    monkeypatch.setattr(
        supervisor_module,
        "_authenticated_health_exchange",
        lambda **_kwargs: supervisor_module.AuthenticatedOwnerHealthProof(
            ready=True,
            rejection="",
            binding=(
                _HostileField(calls), "root", "generation", "receipt",
            ),  # type: ignore[arg-type]
            replica_binding=REPLICA_BINDING,
        ),
    )
    owner = HoloQueryServiceSupervisor(repo_root=tmp_path)

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        owner.start()

    assert error.value.code == supervisor_module.BINDING_MISMATCH_ERROR
    assert calls == []
    assert owner.is_ready is False

def test_json_health_boundary_rejects_malformed_canonical_scalar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _ready_health_payload(replica_binding=REPLICA_BINDING)
    payload["repo_head_sha"] = 7

    class Response:
        status = 200

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

    monkeypatch.setattr(supervisor_module.http.client, "HTTPConnection", Connection)

    proof = supervisor_module._authenticated_health_exchange(
        host=OWNER_HOST,
        port=8127,
        token=TOKEN,
        timeout_seconds=1.0,
        expected_replica_binding=REPLICA_BINDING,
    )

    assert proof.ready is False
    assert proof.rejection == supervisor_module.BINDING_MISMATCH_ERROR
    assert proof.binding == ("", "", "", "")
