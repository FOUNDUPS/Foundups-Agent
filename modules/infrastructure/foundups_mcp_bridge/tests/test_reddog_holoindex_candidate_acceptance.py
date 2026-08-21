"""Candidate-acceptance configuration and owner-handoff contracts."""

from .reddog_holoindex_candidate_acceptance_support import *  # noqa: F401,F403


def _run_acceptance_preserving_environment(tmp_path: Path, dependencies):
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    prior = os.environ.get("HOLOINDEX_SSD_PATH")
    os.environ["HOLOINDEX_SSD_PATH"] = "prior-value"
    try:
        result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
        assert os.environ["HOLOINDEX_SSD_PATH"] == "prior-value"
        return result
    finally:
        if prior is None:
            os.environ.pop("HOLOINDEX_SSD_PATH", None)
        else:
            os.environ["HOLOINDEX_SSD_PATH"] = prior


def _assert_acceptance_order(names: list[str]) -> None:
    assert names.index("canonical_digest") < names.index("create_store")
    assert names.index("runtime") < names.index("create_store")
    assert names.index("port") < names.index("maintenance")
    assert names.index("maintenance") < names.index("query")
    assert names.index("cleanup") < names.index("activation")
    assert names.index("activation") < names.index("rehydrate")
    assert names.index("rehydrate") < names.index("receipt_open")
    assert names.index("receipt_open") < names.index("snapshot")
    assert names.count("receipt_revalidate") == 2


def _assert_published_acceptance(payload: dict[str, object], tmp_path: Path) -> None:
    assert payload["verdict"] == "PASS"
    assert payload["owner_runtime_root_digest"] == "sha256:" + "0" * 64
    assert payload["direct_query_count"] == 2
    assert payload["activation_query_count"] == 1
    assert str(payload["activation_query_receipt_digest"]).startswith("sha256:")
    assert payload["semantic_store_proof_unchanged"] is True
    assert str(payload["owner_session_digest"]).startswith("sha256:")
    assert "private-token" not in str(payload)
    assert "127.0.0.1" not in str(payload)
    assert str(tmp_path / "runtime" / ".venv" / "Lib" / "site-packages") not in str(payload)
    assert str(tmp_path / "python.exe") not in str(payload)

def test_candidate_acceptance_config_requires_owner_runtime_root() -> None:
    from dataclasses import fields

    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        CandidateAcceptanceConfig,
    )

    assert "owner_runtime_root" in {field.name for field in fields(CandidateAcceptanceConfig)}

def test_activation_ignores_ambient_explicit_authority(monkeypatch, tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_candidate_acceptance as acceptance,
    )

    observed: dict[str, object] = {}
    monkeypatch.setenv("REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT", str(tmp_path / "foreign"))
    monkeypatch.setattr(
        acceptance,
        "resolve_holoindex_authority_root",
        lambda root, **kwargs: observed.update(root=root, **kwargs) or "selection",
    )
    monkeypatch.setattr(
        acceptance,
        "supported_owner_query_once",
        lambda payload, **kwargs: observed.update(payload=payload, wrapper=kwargs)
        or {"ok": True},
    )

    result = acceptance._activate_supported_wrapper(
        repo_root=tmp_path, query="activation", limit=1
    )
    selector = observed["wrapper"]["select_authority"]
    assert selector(tmp_path) == "selection"
    assert observed["environment"] == {}
    assert result == {"ok": True}

def test_default_mode_never_creates_store_or_runs_maintenance(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    calls: list[object] = []
    result = run_candidate_acceptance(
        _config(tmp_path, real_mode=False), dependencies=_dependencies(tmp_path, calls)
    )
    assert result.verdict == "NOT_RUN"
    assert calls == []

def test_pre_owner_failure_publishes_empty_session_digest(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    dependencies.validate_worktrees = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        ValueError("pre-owner")
    )
    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
    published = [entry[1] for entry in calls if isinstance(entry, tuple) and entry[0] == "publish"]
    assert result.verdict == "FAIL"
    assert published[0]["owner_session_digest"] == ""

def test_real_acceptance_executes_exact_order_and_restores_environment(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        K1_ACCEPTANCE_QUERY,
        K12_INCIDENT_QUERY,
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    observed_maintenance: dict[str, object] = {}
    dependencies.ensure_operational = lambda **kwargs: (
        observed_maintenance.update(kwargs) or calls.append("maintenance") or _operational_proof()
    )
    result = _run_acceptance_preserving_environment(tmp_path, dependencies)
    assert result.verdict == "PASS"
    query_calls = [entry for entry in calls if isinstance(entry, tuple) and entry[0] == "query"]
    assert query_calls == [
        ("query", (K1_ACCEPTANCE_QUERY, 1)),
        ("query", (K12_INCIDENT_QUERY, 12)),
    ]
    names = [entry[0] if isinstance(entry, tuple) else entry for entry in calls]
    _assert_acceptance_order(names)
    snapshot = next(entry[1] for entry in calls if isinstance(entry, tuple) and entry[0] == "snapshot")
    assert snapshot["runtime_site_packages"] == (
        str(tmp_path / "runtime" / ".venv" / "Lib" / "site-packages"),
    )
    assert snapshot["base_executable_proof"] is not None
    assert names[-2:] == ["canonical_digest", "publish"]
    published = [entry[1] for entry in calls if isinstance(entry, tuple) and entry[0] == "publish"]
    _assert_published_acceptance(published[0], tmp_path)
    assert observed_maintenance["repo_root"] == _config(tmp_path).candidate_root
    assert observed_maintenance["owner_runtime_root"] == _config(tmp_path).owner_runtime_root

def test_actual_handshake_failure_chain_uses_dependency_runtime_without_optimism(
    tmp_path: Path, monkeypatch
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_maintenance_handshake as handshake,
    )
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    observed: dict[str, object] = {}
    dependencies = _dependencies(tmp_path, calls, handoffs=[None, None])

    def fail_locked(**kwargs):
        observed.update(kwargs)
        return handshake.RedDogHoloIndexOperationalResult(
            ready=False,
            status=handshake.OPERATIONAL_FAILED,
            error=handshake.REFRESH_FAILED_ERROR,
        )

    monkeypatch.setattr(handshake, "_ensure_locked", fail_locked)
    dependencies.ensure_operational = handshake.ensure_reddog_holoindex_operational
    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)

    assert result.verdict == "FAIL"
    assert result.error == handshake.REFRESH_FAILED_ERROR
    assert observed["repo_root"] == _config(tmp_path).candidate_root.resolve()
    assert observed["owner_runtime_root"] == _config(tmp_path).owner_runtime_root.resolve()
    assert "query" not in calls

def test_non_refreshed_maintenance_fails_without_query_and_cleans_started_owner(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    dependencies.ensure_operational = lambda **kwargs: calls.append("maintenance") or SimpleNamespace(
        ready=True,
        status="READY",
        refreshed=False,
        error="",
        repo_head_sha=SHA,
        generation_id=GENERATION,
        freshness_receipt_digest=RECEIPT_DIGEST,
    )
    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
    names = [entry[0] if isinstance(entry, tuple) else entry for entry in calls]
    assert result.verdict == "FAIL"
    assert "query" not in names
    assert names.count("cleanup") == 1
    assert [entry[1]["verdict"] for entry in calls if isinstance(entry, tuple) and entry[0] == "publish"] == ["FAIL"]

def test_query_binding_failure_still_cleans_only_proven_owner(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    bad = _query_result()
    bad["repo_head_sha"] = "9" * 40
    dependencies.query_owner = lambda **kwargs: calls.append(("query", kwargs["limit"])) or bad
    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
    names = [entry[0] if isinstance(entry, tuple) else entry for entry in calls]
    assert result.verdict == "FAIL"
    assert names.count("query") == 1
    assert names.count("cleanup") == 1

def test_handoff_race_fails_without_cleaning_foreign_owner(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(
        tmp_path,
        calls,
        handoffs=[
            None,
            ("http://127.0.0.1:8127", "ours"),
            ("http://127.0.0.1:8127", "foreign"),
        ],
    )
    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
    names = [entry[0] if isinstance(entry, tuple) else entry for entry in calls]
    assert result.verdict == "FAIL"
    assert "cleanup" not in names
    assert result.error == "OWNER_HANDOFF_OWNERSHIP_CHANGED"
    published = [entry[1] for entry in calls if isinstance(entry, tuple) and entry[0] == "publish"]
    assert published[0]["verdict"] == "FAIL"
    assert published[0]["owner_session_digest"].startswith("sha256:")
    assert "ours" not in str(published[0])

def test_foreign_literal_loopback_listener_rejects_before_maintenance(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service_supervisor import (
        OWNER_HOST,
        _owner_port_available,
    )
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    dependencies.port_available = _owner_port_available
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind((OWNER_HOST, 8127))
        listener.listen(1)
        result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
    names = [entry[0] if isinstance(entry, tuple) else entry for entry in calls]
    assert result.verdict == "FAIL"
    assert result.error == "OWNER_PORT_NOT_AVAILABLE"
    assert "maintenance" not in names
    assert "query" not in names
    assert "cleanup_attempt" not in names
    assert "cleanup" not in names

def test_preexisting_private_handoff_rejects_without_owner_effects(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    foreign = ("http://127.0.0.1:8127", "foreign-private-token")
    dependencies = _dependencies(tmp_path, calls, handoffs=[foreign])
    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
    names = [entry[0] if isinstance(entry, tuple) else entry for entry in calls]
    assert result.verdict == "FAIL"
    assert result.error == "OWNER_HANDOFF_ALREADY_PRESENT"
    assert "maintenance" not in names
    assert "query" not in names
    assert "cleanup_attempt" not in names
    assert "cleanup" not in names

def test_port_race_after_precheck_preserves_port_failure_without_owner_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        holo_query_service_supervisor as supervisor_module,
    )
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls, handoffs=[None, None])
    spawned: list[bool] = []
    monkeypatch.setattr(
        supervisor_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: spawned.append(True),
    )
    dependencies.ensure_operational = _port_race_result(
        supervisor_module, tmp_path, calls
    )
    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
    names = [entry[0] if isinstance(entry, tuple) else entry for entry in calls]
    assert result.verdict == "FAIL"
    assert result.error == "OWNER_PORT_NOT_AVAILABLE"
    assert names.count("maintenance") == 1
    assert "query" not in names
    assert "cleanup_attempt" not in names
    assert "cleanup" not in names
    assert spawned == []

def test_operational_response_without_new_private_handoff_is_never_reused(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls, handoffs=[None, None])
    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
    names = [entry[0] if isinstance(entry, tuple) else entry for entry in calls]
    assert result.verdict == "FAIL"
    assert result.error == "NEW_PRIVATE_OWNER_HANDOFF_MISSING"
    assert "query" not in names
    assert "cleanup_attempt" not in names
    assert "cleanup" not in names
