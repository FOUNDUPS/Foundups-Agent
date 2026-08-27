"""Supervisor startup and runtime-selection contracts."""

from .holo_query_service_supervisor_support import *  # noqa: F401,F403


def _assert_successful_start_launch(
    owner: _RawHoloQueryServiceSupervisor,
    launch: dict[str, Any],
    tmp_path: Path,
) -> None:
    site_flags = ["-S"] if os.name == "nt" else []
    assert launch["command"] == [
        owner.python_executable, *site_flags, "-B", "-m", OWNER_MODULE,
        "--host", OWNER_HOST, "--port", "9137", "--parent-pid",
        str(supervisor_module.os.getpid()), "--canonical-ssd-path",
        str(tmp_path / "canonical"), "--query-replica-root",
        str(tmp_path / "replica"),
    ]
    options = launch["kwargs"]
    assert options["shell"] is False
    assert options["cwd"] == str(tmp_path.resolve())
    assert options["stdin"] is subprocess.DEVNULL
    assert options["stdout"] is subprocess.DEVNULL
    assert options["stderr"] is subprocess.DEVNULL
    assert options["env"][SERVICE_TOKEN_ENV] == TOKEN
    assert SERVICE_URL_ENV not in options["env"]
    assert launch["probe_timeouts"] == [DEFAULT_OWNER_STARTUP_PROBE_TIMEOUT_SECONDS]
    assert launch["probe_bindings"] == [("", "", "", "")]

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
    _assert_successful_start_launch(owner, launch, tmp_path)
    assert registered

    owner.stop()
    assert process.terminated is True
    assert unregistered
    assert owner.is_ready is False

def test_windows_venv_runtime_keeps_direct_parent_and_site_packages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    venv = tmp_path / ".venv"
    scripts = venv / "Scripts"
    site_packages = venv / "Lib" / "site-packages"
    scripts.mkdir(parents=True)
    site_packages.mkdir(parents=True)
    launcher = scripts / "python.exe"
    base = tmp_path / "Python312" / "python.exe"
    launcher.write_bytes(b"launcher")
    base.parent.mkdir()
    base.write_bytes(b"python")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "attacker-controlled"))

    executable, pythonpath = supervisor_module._owner_python_runtime(
        str(launcher),
        platform_name="nt",
        current_executable=str(launcher),
        base_executable=str(base),
        current_prefix=str(venv),
        base_prefix=str(base.parent),
    )

    assert executable == str(base.resolve())
    assert pythonpath == (str(site_packages.resolve()),)
    environment = supervisor_module._owner_environment(
        TOKEN,
        pythonpath,
    )
    assert environment["PYTHONPATH"].split(supervisor_module.os.pathsep)[0] == str(
        site_packages.resolve()
    )
    assert environment["PYTHONPATH"] == str(site_packages.resolve())

def test_non_current_or_non_windows_interpreter_is_not_rewritten(
    tmp_path: Path,
) -> None:
    requested = tmp_path / "other" / "python"

    assert supervisor_module._owner_python_runtime(
        str(requested),
        platform_name="posix",
        current_executable=str(tmp_path / "venv" / "python"),
        base_executable=str(tmp_path / "base" / "python"),
        current_prefix=str(tmp_path / "venv"),
        base_prefix=str(tmp_path / "base"),
    ) == (str(requested), ())

@pytest.mark.parametrize("missing", ["base", "site_packages"])
def test_windows_venv_runtime_fails_closed_when_runtime_path_missing(
    tmp_path: Path,
    missing: str,
) -> None:
    venv = tmp_path / ".venv"
    launcher = venv / "Scripts" / "python.exe"
    site_packages = venv / "Lib" / "site-packages"
    base = tmp_path / "Python312" / "python.exe"
    launcher.parent.mkdir(parents=True)
    launcher.write_bytes(b"launcher")
    if missing != "site_packages":
        site_packages.mkdir(parents=True)
    if missing != "base":
        base.parent.mkdir()
        base.write_bytes(b"python")

    assert supervisor_module._owner_python_runtime(
        str(launcher),
        platform_name="nt",
        current_executable=str(launcher),
        base_executable=str(base),
        current_prefix=str(venv),
        base_prefix=str(base.parent),
    ) == (str(launcher), ())

def test_windows_venv_runtime_rejects_out_of_prefix_site_packages(
    tmp_path: Path,
) -> None:
    venv = tmp_path / ".venv"
    launcher = venv / "Scripts" / "python.exe"
    base = tmp_path / "Python312" / "python.exe"
    outside = tmp_path / "outside" / "site-packages"
    launcher.parent.mkdir(parents=True)
    launcher.write_bytes(b"launcher")
    base.parent.mkdir()
    base.write_bytes(b"python")
    outside.mkdir(parents=True)

    assert supervisor_module._owner_python_runtime(
        str(launcher),
        platform_name="nt",
        current_executable=str(launcher),
        base_executable=str(base),
        current_prefix=str(venv),
        base_prefix=str(base.parent),
        site_packages_path=str(outside),
    ) == (str(launcher), ())

def test_windows_venv_runtime_does_not_rewrite_other_interpreter(
    tmp_path: Path,
) -> None:
    current = tmp_path / ".venv" / "Scripts" / "python.exe"
    requested = tmp_path / "other" / "python.exe"
    base = tmp_path / "Python312" / "python.exe"
    site_packages = tmp_path / ".venv" / "Lib" / "site-packages"
    current.parent.mkdir(parents=True)
    current.write_bytes(b"launcher")
    requested.parent.mkdir()
    requested.write_bytes(b"other")
    base.parent.mkdir()
    base.write_bytes(b"python")
    site_packages.mkdir(parents=True)

    assert supervisor_module._owner_python_runtime(
        str(requested),
        platform_name="nt",
        current_executable=str(current),
        base_executable=str(base),
        current_prefix=str(tmp_path / ".venv"),
        base_prefix=str(base.parent),
    ) == (str(requested), ())

@pytest.mark.skipif(
    os.name != "nt" or sys.prefix == sys.base_prefix,
    reason="Windows virtualenv redirector regression",
)
def test_current_windows_venv_runtime_creates_direct_child() -> None:
    executable, pythonpath = supervisor_module._owner_python_runtime(
        sys.executable,
    )
    environment = supervisor_module._owner_environment(
        TOKEN,
        pythonpath,
    )
    child = subprocess.Popen(
        [
            executable,
            "-B",
            "-c",
            "import os; print(os.getppid(), flush=True)",
        ],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
    )
    stdout, stderr = child.communicate(timeout=10)

    assert child.returncode == 0, stderr
    assert int(stdout.strip()) == os.getpid()
    assert executable != sys.executable
    assert pythonpath

def test_start_proves_exact_binding_in_its_single_authoritative_health_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess()
    launch = _install_successful_start(monkeypatch, process)
    monkeypatch.setattr(supervisor_module.atexit, "register", lambda _callback: None)
    monkeypatch.setattr(supervisor_module.atexit, "unregister", lambda _callback: None)
    expected = (
        "a" * 40,
        "sha256:" + ("d" * 64),
        "sha256:" + ("b" * 64),
        "sha256:" + ("c" * 64),
    )

    owner = HoloQueryServiceSupervisor(repo_root=tmp_path).start(
        expected_repo_head_sha=expected[0],
        expected_repo_root_digest=expected[1],
        expected_generation_id=expected[2],
        expected_receipt_digest=expected[3],
    )

    assert owner.is_ready is True
    assert owner.verified_binding == expected
    assert launch["probe_bindings"] == [expected]
    owner.stop()
    assert owner.verified_binding == ("", "", "", "")

def test_start_passes_explicit_storage_argv_without_ambient_ssd_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess()
    launch = _install_successful_start(monkeypatch, process)
    monkeypatch.setenv("HOLOINDEX_SSD_PATH", str(tmp_path / "ambient-trap"))
    monkeypatch.setattr(supervisor_module.atexit, "register", lambda _callback: None)
    monkeypatch.setattr(supervisor_module.atexit, "unregister", lambda _callback: None)
    ssd_path = tmp_path / "holo-store"
    replica_root = tmp_path / "query-replica"
    owner = HoloQueryServiceSupervisor(
        repo_root=tmp_path,
        canonical_ssd_path=ssd_path,
        query_replica_root=replica_root,
    ).start()

    assert owner.start() is owner
    command = launch["command"]
    assert command[command.index("--canonical-ssd-path") + 1] == str(ssd_path.resolve())
    assert command[command.index("--query-replica-root") + 1] == str(
        replica_root.resolve()
    )
    assert "HOLOINDEX_SSD_PATH" not in launch["kwargs"]["env"]
    owner.stop()

def test_replica_capability_is_reverified_before_spawn_and_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess()
    _install_successful_start(monkeypatch, process)
    events: list[str] = []
    popen = supervisor_module.subprocess.Popen
    exchange = supervisor_module._authenticated_health_exchange

    def verified() -> object:
        events.append("capability")
        return _synthetic_replica_capability()

    def spawn(*args: Any, **kwargs: Any):
        events.append("spawn")
        return popen(*args, **kwargs)

    def health(**kwargs: Any):
        events.append("health")
        return exchange(**kwargs)

    monkeypatch.setattr(supervisor_module.subprocess, "Popen", spawn)
    monkeypatch.setattr(supervisor_module, "_authenticated_health_exchange", health)
    owner = HoloQueryServiceSupervisor(
        repo_root=tmp_path,
        canonical_ssd_path=tmp_path / "canonical",
        query_replica_root=tmp_path / "replica",
        replica_capability_verifier=verified,
    ).start(expected_replica_binding=("descriptor", "generation", "replica", "path"))

    assert events == ["capability", "spawn", "capability", "health"]
    owner.stop()

def test_replica_swap_after_spawn_fails_closed_before_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess()
    launch = _install_successful_start(monkeypatch, process)
    calls = 0

    def changed() -> object:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("QUERY_REPLICA_BINDING_CHANGED")
        return _synthetic_replica_capability()

    owner = HoloQueryServiceSupervisor(
        repo_root=tmp_path,
        canonical_ssd_path=tmp_path / "canonical",
        query_replica_root=tmp_path / "replica",
        replica_capability_verifier=changed,
    )
    with pytest.raises(ValueError, match="QUERY_REPLICA_BINDING_CHANGED"):
        owner.start(expected_replica_binding=("descriptor", "generation", "replica", "path"))

    assert process.terminated is True
    assert "probe_bindings" not in launch
    assert owner.is_ready is False

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
        "_authenticated_health_exchange",
        lambda **_kwargs: supervisor_module.AuthenticatedOwnerHealthProof(
            False, "", ("", "", "", "")
        ),
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
        "_authenticated_health_exchange",
        lambda **_kwargs: supervisor_module.AuthenticatedOwnerHealthProof(
            False, "REPO_HEAD_MISMATCH", ("", "", "", "")
        ),
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
    assert supervisor_module._health_rejection_code(
        {**base, "error": "SEMANTIC_BACKEND_UNAVAILABLE"}
    ) == "SEMANTIC_BACKEND_UNAVAILABLE"
    assert supervisor_module._health_rejection_code(
        {**base, "error": "QUERY_TIMEOUT"}
    ) == "QUERY_TIMEOUT"
    assert supervisor_module._health_rejection_code({**base, "error": "UNAUTHORIZED"}) == ""
    assert supervisor_module._health_rejection_code({**base, "loopback_only": False}) == ""
    assert supervisor_module._health_rejection_code({**base, "schema_version": "wrong"}) == ""
