"""Candidate-acceptance cleanup and session-lifecycle contracts."""

from .reddog_holoindex_candidate_acceptance_support import *  # noqa: F401,F403

def test_failed_refresh_without_handoff_preserves_stable_error_without_cleanup(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls, handoffs=[None, None])
    dependencies.ensure_operational = lambda **_kwargs: calls.append("maintenance") or SimpleNamespace(
        ready=False,
        status="FAILED",
        refreshed=False,
        error="HOLOINDEX_MAINTENANCE_REFRESH_FAILED",
        repo_head_sha=SHA,
        generation_id="",
        freshness_receipt_digest="",
    )

    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)

    names = [entry[0] if isinstance(entry, tuple) else entry for entry in calls]
    assert result.verdict == "FAIL"
    assert result.error == "HOLOINDEX_MAINTENANCE_REFRESH_FAILED"
    assert "query" not in names
    assert "cleanup_attempt" not in names
    assert "cleanup" not in names

def test_canonical_receipt_change_forces_fail_after_cleanup(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    proofs = iter(
        [
            SimpleNamespace(digest="sha256:" + "d" * 64, size=100),
            SimpleNamespace(digest="sha256:" + "8" * 64, size=100),
        ]
    )
    dependencies.read_digest = lambda *args, **kwargs: calls.append("canonical_digest") or next(proofs)
    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
    names = [entry[0] if isinstance(entry, tuple) else entry for entry in calls]
    assert result.verdict == "FAIL"
    assert result.error == "CANONICAL_RECEIPT_CHANGED"
    assert names.index("cleanup") < names.index("canonical_digest", names.index("cleanup"))

def test_cleanup_exception_cannot_block_environment_restore_or_fail_receipt(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    dependencies.cleanup_owner = lambda **_kwargs: (_ for _ in ()).throw(
        OSError("private cleanup detail")
    )
    prior = os.environ.get("HOLOINDEX_SSD_PATH")
    os.environ["HOLOINDEX_SSD_PATH"] = "prior-value"
    try:
        result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
        assert os.environ["HOLOINDEX_SSD_PATH"] == "prior-value"
    finally:
        if prior is None:
            os.environ.pop("HOLOINDEX_SSD_PATH", None)
        else:
            os.environ["HOLOINDEX_SSD_PATH"] = prior
    assert result.verdict == "FAIL"
    assert result.error == "OWNER_CLEANUP_FAILED"
    published = [entry[1] for entry in calls if isinstance(entry, tuple) and entry[0] == "publish"]
    assert published[0]["verdict"] == "FAIL"

def test_canonical_recheck_failure_never_claims_unchanged(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    initial = SimpleNamespace(digest="sha256:" + "d" * 64, size=100)
    reads = iter([initial, OSError("private read detail")])

    def read_digest(*_args, **_kwargs):
        calls.append("canonical_digest")
        value = next(reads)
        if isinstance(value, BaseException):
            raise value
        return value

    dependencies.read_digest = read_digest
    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
    published = [entry[1] for entry in calls if isinstance(entry, tuple) and entry[0] == "publish"]
    assert result.error == "CANONICAL_RECEIPT_RECHECK_FAILED"
    assert published[0]["canonical_receipt_unchanged"] is False

def test_ensure_exception_after_owner_start_is_captured_and_cleaned(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    owned = ("http://127.0.0.1:8127", "private-token")
    current: dict[str, tuple[str, str] | None] = {"handoff": None}

    dependencies.resolve_handoff = lambda: calls.append("handoff") or current["handoff"]

    def ensure_operational(**_kwargs):
        calls.append("maintenance")
        current["handoff"] = owned
        raise OSError("private startup detail")

    def cleanup_owner(*, expected_handoff, **_kwargs):
        calls.append(("cleanup", expected_handoff))
        assert expected_handoff == owned
        current["handoff"] = None
        return True

    dependencies.ensure_operational = ensure_operational
    dependencies.cleanup_owner = cleanup_owner
    prior = os.environ.get("HOLOINDEX_SSD_PATH")
    os.environ["HOLOINDEX_SSD_PATH"] = "prior-value"
    try:
        result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
        assert os.environ["HOLOINDEX_SSD_PATH"] == "prior-value"
    finally:
        if prior is None:
            os.environ.pop("HOLOINDEX_SSD_PATH", None)
        else:
            os.environ["HOLOINDEX_SSD_PATH"] = prior
    assert result.verdict == "FAIL"
    assert result.error == "CANDIDATE_ACCEPTANCE_FAILED"
    assert current["handoff"] is None
    assert ("cleanup", owned) in calls

def test_invalid_refresh_result_with_started_owner_is_still_cleaned(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    owned = ("http://127.0.0.1:8127", "private-token")
    current: dict[str, tuple[str, str] | None] = {"handoff": None}
    dependencies.resolve_handoff = lambda: calls.append("handoff") or current["handoff"]

    def ensure_operational(**_kwargs):
        calls.append("maintenance")
        current["handoff"] = owned
        return SimpleNamespace(
            ready=False,
            status="FAILED",
            refreshed=False,
            repo_head_sha=SHA,
            generation_id="",
            freshness_receipt_digest="",
        )

    dependencies.ensure_operational = ensure_operational
    dependencies.cleanup_owner = lambda *, expected_handoff, **_kwargs: (
        calls.append(("cleanup", expected_handoff)) or current.update(handoff=None) or True
    )
    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
    assert result.verdict == "FAIL"
    assert result.error == "OPERATIONAL_REFRESH_PROOF_INVALID"
    assert current["handoff"] is None
    assert ("cleanup", owned) in calls

def test_baseexception_after_owner_start_finalizes_then_preserves_interrupt(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    dependencies.query_owner = lambda **_kwargs: (_ for _ in ()).throw(
        KeyboardInterrupt()
    )
    prior = os.environ.get("HOLOINDEX_SSD_PATH")
    os.environ["HOLOINDEX_SSD_PATH"] = "prior-value"
    try:
        with pytest.raises(KeyboardInterrupt):
            run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
        assert os.environ["HOLOINDEX_SSD_PATH"] == "prior-value"
    finally:
        if prior is None:
            os.environ.pop("HOLOINDEX_SSD_PATH", None)
        else:
            os.environ["HOLOINDEX_SSD_PATH"] = prior
    names = [entry[0] if isinstance(entry, tuple) else entry for entry in calls]
    assert "cleanup" in names
    assert names[-2:] == ["canonical_digest", "publish"]
    published = [entry[1] for entry in calls if isinstance(entry, tuple) and entry[0] == "publish"]
    assert published[0]["verdict"] == "FAIL"

def test_process_session_lock_fails_second_concurrent_call_before_preflight(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    first_calls: list[object] = []
    second_calls: list[object] = []
    first_dependencies = _dependencies(tmp_path, first_calls)
    second_dependencies = _dependencies(tmp_path, second_calls)
    entered = threading.Event()
    release = threading.Event()
    first_result: list[object] = []
    original_validate = first_dependencies.validate_worktrees

    def blocking_validate(*args, **kwargs):
        entered.set()
        assert release.wait(timeout=5.0)
        return original_validate(*args, **kwargs)

    first_dependencies.validate_worktrees = blocking_validate
    worker = threading.Thread(
        target=lambda: first_result.append(
            run_candidate_acceptance(_config(tmp_path), dependencies=first_dependencies)
        )
    )
    worker.start()
    assert entered.wait(timeout=5.0)
    try:
        second = run_candidate_acceptance(
            _config(tmp_path), dependencies=second_dependencies
        )
    finally:
        release.set()
        worker.join(timeout=5.0)
    assert not worker.is_alive()
    assert second.verdict == "FAIL"
    assert second.error == "ACCEPTANCE_SESSION_BUSY"
    assert second.receipt_published is False
    assert second_calls == []
    assert first_result and first_result[0].verdict == "PASS"
