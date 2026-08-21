"""Candidate-acceptance binding and integrity contracts."""

from .reddog_holoindex_candidate_acceptance_support import *  # noqa: F401,F403

def test_cross_process_session_lease_busy_fails_before_preflight(tmp_path: Path) -> None:
    from holo_index.maintenance_lock import MaintenanceLeaseBusy
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    dependencies.acquire_session_lease = lambda _config: (_ for _ in ()).throw(
        MaintenanceLeaseBusy("already held")
    )
    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
    assert result.verdict == "FAIL"
    assert result.error == "ACCEPTANCE_SESSION_BUSY"
    assert result.receipt_published is False
    assert calls == []

@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repo_head_sha", "9" * 40),
        ("freshness_generation_id", "sha256:" + "9" * 64),
        ("freshness_receipt_digest", "sha256:" + "8" * 64),
        ("authority_repo_root_digest", "sha256:" + "7" * 64),
    ],
)
def test_activation_binding_drift_fails_after_private_cleanup(
    tmp_path: Path, field: str, value: str,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    bad = _activation_result(tmp_path)
    bad[field] = value
    dependencies.activate_supported_wrapper = lambda **_kwargs: calls.append(
        "activation"
    ) or bad

    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)

    names = [entry[0] if isinstance(entry, tuple) else entry for entry in calls]
    assert result.verdict == "FAIL"
    assert result.error == "ACTIVATION_QUERY_PROOF_INVALID"
    assert names.index("cleanup") < names.index("activation")
    assert "snapshot" not in names

def test_activation_receipt_tamper_fails_closed(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    bad = _activation_result(tmp_path)
    receipt = dict(bad["query_receipt"])
    receipt["receipt_id"] = "sha256:" + "0" * 64
    bad["query_receipt"] = receipt
    dependencies.activate_supported_wrapper = lambda **_kwargs: bad

    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)

    assert result.verdict == "FAIL"
    assert result.error == "ACTIVATION_QUERY_RECEIPT_INVALID"

def test_post_activation_collection_drift_fails_closed(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    dependencies.verify_collection_snapshots = (
        lambda *args, **kwargs: calls.append("snapshot") or ["holo_index_code"]
    )

    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)

    assert result.verdict == "FAIL"
    assert result.error == "SEMANTIC_STORE_PROOF_CHANGED"

def test_activation_keyboard_interrupt_finalizes_and_propagates(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    dependencies.activate_supported_wrapper = lambda **_kwargs: (_ for _ in ()).throw(
        KeyboardInterrupt()
    )

    with pytest.raises(KeyboardInterrupt):
        run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)

    names = [entry[0] if isinstance(entry, tuple) else entry for entry in calls]
    assert "cleanup" in names
    assert "publish" in names

def test_snapshot_keyboard_interrupt_closes_proof_finalizes_and_propagates(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    dependencies.verify_collection_snapshots = lambda *_args, **_kwargs: (
        (_ for _ in ()).throw(KeyboardInterrupt())
    )
    with pytest.raises(KeyboardInterrupt):
        run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
    assert "receipt_close" in calls
    assert calls.count("receipt_revalidate") == 2
    assert "publish" in [entry[0] if isinstance(entry, tuple) else entry for entry in calls]

def test_second_receipt_revalidation_failure_fails_closed(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    class ReplacedProof(_ReceiptProof):
        def revalidate(self) -> None:
            super().revalidate()
            if self.calls.count("receipt_revalidate") == 2:
                raise ValueError("replaced during probe")

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    dependencies.open_receipt_proof = lambda **_kwargs: ReplacedProof(calls)
    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
    assert result.verdict == "FAIL"
    assert result.error == "SEMANTIC_STORE_RECEIPT_INVALID"

def test_typed_semantic_runtime_error_is_not_flattened(tmp_path: Path) -> None:
    from holo_index.isolated_collection_snapshot_probe import IsolatedSnapshotProbeError
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    dependencies.verify_collection_snapshots = lambda *_args, **_kwargs: (
        (_ for _ in ()).throw(IsolatedSnapshotProbeError("UNSUPPORTED_CHROMADB_VERSION"))
    )
    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)
    assert result.verdict == "FAIL"
    assert result.error == "UNSUPPORTED_CHROMADB_VERSION"

def test_activation_exception_is_stable_fail_closed(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    dependencies.activate_supported_wrapper = lambda **_kwargs: (_ for _ in ()).throw(
        OSError("private activation detail")
    )

    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)

    assert result.verdict == "FAIL"
    assert result.error == "ACTIVATION_QUERY_FAILED"

def test_activation_leaked_handoff_fails_closed(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        run_candidate_acceptance,
    )

    (tmp_path / "receipts").mkdir()
    calls: list[object] = []
    dependencies = _dependencies(tmp_path, calls)
    owned = ("http://127.0.0.1:8127", "owned")
    leaked = ("http://127.0.0.1:8127", "leaked")
    current: dict[str, tuple[str, str] | None] = {"handoff": None}
    dependencies.resolve_handoff = lambda: current["handoff"]

    def ensure(**_kwargs):
        current["handoff"] = owned
        return _operational_proof()

    def cleanup(*, expected_handoff, **_kwargs):
        assert expected_handoff == owned
        current["handoff"] = None
        return True

    def activate(**_kwargs):
        current["handoff"] = leaked
        return _activation_result(tmp_path)

    dependencies.ensure_operational = ensure
    dependencies.cleanup_owner = cleanup
    dependencies.activate_supported_wrapper = activate

    result = run_candidate_acceptance(_config(tmp_path), dependencies=dependencies)

    assert result.verdict == "FAIL"
    assert result.error == "ACTIVATION_OWNER_HANDOFF_LEAKED"
    assert current["handoff"] == leaked
