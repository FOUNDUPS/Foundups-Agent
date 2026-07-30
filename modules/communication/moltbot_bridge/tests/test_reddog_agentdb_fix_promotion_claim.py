"""Tests for durable cross-process RedDog FIX promotion claims."""

from __future__ import annotations

import ast
import inspect
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from holo_index.repository_state import RepositoryState
import modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime as readonly_runtime
from modules.communication.moltbot_bridge.src.reddog_agentdb_fix_promotion_claim import (
    AgentDbFixPromotionClaimStore,
    claim_next_reddog_fix_promotion,
)
from modules.communication.moltbot_bridge.src.reddog_agentdb_fix_promotion_claim_fence import (
    FixPromotionClaimFenceLost,
    execute_with_fix_promotion_claim_fence,
)
from modules.communication.moltbot_bridge.src.reddog_main_fix_promotion_claim_handoff import (
    MAIN_FIX_CLAIM_HANDOFF_APPLIED,
    MAIN_FIX_CLAIM_HANDOFF_REJECT,
    MainFixPromotionClaimHandoffResult,
    run_reddog_main_fix_promotion_claim_handoff,
)
import modules.communication.moltbot_bridge.src.reddog_resident_fix_promotion_artifact_handoff as artifact_handoff
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    AgentDbArchitectDeterminationStore,
    run_reddog_backend_architect_determination_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle import (
    AgentDbResidentArchitectCycleStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
    resident_queue_runtime_flag_enabled,
)
import modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle as cycle_runtime
from modules.communication.moltbot_bridge.tests.architect_proposal_test_helpers import (
    architect_model_output,
    runtime_kwargs as backend_runtime_kwargs,
)
from modules.communication.moltbot_bridge.tests.test_reddog_backend_architect_determination_runtime import (
    FakeArchitectRunner,
    NOW as BACKEND_NOW,
    _build_inputs,
)
from modules.communication.moltbot_bridge.tests.test_reddog_resident_architect_durable_agentdb_cycle import (
    _bound_intent,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _memex_supply,
)
from modules.infrastructure.database.src.db_manager import DatabaseManager


REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_ROOT = REPO_ROOT / "modules" / "communication" / "moltbot_bridge" / "src"
NOW = datetime(2026, 7, 30, tzinfo=timezone.utc)
TOUCHED_FUNCTION_NO_GROWTH = {
    "reddog_architect_fix_promotion_transaction.py": {
        "_reconstruct_committed_result": 158,
        "_build_receipt": 55,
    },
    "reddog_architect_fix_signed_wsp15_work_order_promotion.py": {
        "promote_reddog_architect_fix_to_signed_wsp15_work_order": 179,
    },
    "reddog_main_architect_fix_promotion_bootstrap.py": {
        "run_reddog_main_architect_fix_promotion_bootstrap": 132,
    },
    "reddog_resident_fix_promotion_artifact_handoff.py": {
        "run_reddog_resident_fix_promotion_artifact_handoff": 77,
    },
}


@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "claims.db"))
    monkeypatch.setattr(
        readonly_runtime,
        "read_repository_state",
        lambda *args, **kwargs: RepositoryState(
            head_sha="f9ac824d8",
            clean=True,
            state_digest="sha256:resident-clean",
        ),
    )
    DatabaseManager.reset_for_tests()
    yield
    DatabaseManager.reset_for_tests()


def _seed_fix_cycle(*, include_memex: bool = True):
    inputs = _build_inputs()
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    result = run_reddog_backend_architect_determination_runtime(
        **backend_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=AgentDbArchitectDeterminationStore(),
        model_runner=FakeArchitectRunner(
            architect_model_output(inputs["allocation"], evidence_ref)
        ),
        now_iso=BACKEND_NOW,
    )
    assert result.accepted is True
    assert result.receipt is not None
    cycle_store = AgentDbResidentArchitectCycleStore()
    record = cycle_runtime._new_record(_bound_intent(), retry_count=0)
    assert cycle_store.create_cycle(record)["ok"]
    enqueued = cycle_store.transition_cycle(
        str(record["intent_id"]),
        expected_revision=0,
        expected_statuses=("SUBMITTED",),
        updates={"status": "ENQUEUED"},
    )["record"]
    running = cycle_store.transition_cycle(
        str(record["intent_id"]),
        expected_revision=1,
        expected_statuses=("ENQUEUED",),
        updates={"status": "RUNNING"},
    )["record"]
    determined = cycle_store.transition_cycle(
        str(record["intent_id"]),
        expected_revision=2,
        expected_statuses=("RUNNING",),
        updates={
            "status": "DETERMINED",
            "snapshot_id": result.receipt.snapshot_receipt_id,
            "architect_action": "FIX",
            "architect_determination_id": result.receipt.determination_receipt_id,
            "queue_candidate_count": 1,
            "initial_bootstrap": (
                {
                    "memex_snapshot_supply_receipt": _memex_supply(
                        snapshot_receipt_id=result.receipt.snapshot_receipt_id,
                        snapshot_content_digest=result.receipt.snapshot_content_digest,
                    )
                }
                if include_memex
                else {}
            ),
        },
    )["record"]
    return SimpleNamespace(
        intent_id=determined["intent_id"],
        cycle_id=determined["cycle_id"],
        snapshot_id=determined["snapshot_id"],
        architect_determination_id=determined["architect_determination_id"],
    )


def test_claim_binds_terminal_fix_candidate_and_wsp15_receipt() -> None:
    cycle = _seed_fix_cycle()

    claim = claim_next_reddog_fix_promotion(worker_id="main-0102", now=NOW)

    assert claim.accepted is True
    assert claim.intent_id == cycle.intent_id
    assert claim.cycle_id == cycle.cycle_id
    assert claim.snapshot_id == cycle.snapshot_id
    assert claim.determination_id == cycle.architect_determination_id
    assert claim.queue_candidate_id
    assert claim.wsp15_allocation_receipt_id
    assert claim.no_execution_authority_granted is True


def test_empty_agentdb_is_idle_without_creating_cycle_truth() -> None:
    claim = claim_next_reddog_fix_promotion(worker_id="main", now=NOW)

    assert claim.accepted is False
    assert AgentDbFixPromotionClaimStore().determined_intent_ids() == ()


def test_active_lease_blocks_second_claim_and_expired_lease_recovers() -> None:
    _seed_fix_cycle()
    first = claim_next_reddog_fix_promotion(
        worker_id="main-a",
        now=NOW,
        lease_seconds=60,
    )

    blocked = claim_next_reddog_fix_promotion(
        worker_id="main-b",
        now=NOW + timedelta(seconds=30),
    )
    recovered = claim_next_reddog_fix_promotion(
        worker_id="main-b",
        now=NOW + timedelta(seconds=61),
    )

    assert first.accepted is True
    assert blocked.accepted is False
    assert recovered.accepted is True
    assert recovered.claim_id == first.claim_id
    assert recovered.lease_id != first.lease_id


def test_completed_claim_is_exactly_once() -> None:
    _seed_fix_cycle()
    store = AgentDbFixPromotionClaimStore()
    claim = claim_next_reddog_fix_promotion(worker_id="main", now=NOW)

    assert store.complete(claim, now=NOW + timedelta(seconds=1)) is True
    assert store.complete(claim, now=NOW + timedelta(seconds=2)) is False
    assert claim_next_reddog_fix_promotion(
        worker_id="other",
        now=NOW + timedelta(hours=1),
    ).accepted is False


def test_release_makes_claim_immediately_recoverable() -> None:
    _seed_fix_cycle()
    store = AgentDbFixPromotionClaimStore()
    first = claim_next_reddog_fix_promotion(worker_id="main-a", now=NOW)

    assert store.release(first, now=NOW + timedelta(seconds=1)) is True
    second = claim_next_reddog_fix_promotion(
        worker_id="main-b",
        now=NOW + timedelta(seconds=2),
    )
    assert second.accepted is True
    assert second.claim_id == first.claim_id


def test_two_concurrent_claimers_cannot_both_win() -> None:
    _seed_fix_cycle()

    def claim(worker: str):
        return claim_next_reddog_fix_promotion(worker_id=worker, now=NOW)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, ("main-a", "main-b")))

    assert sum(result.accepted for result in results) == 1


def test_tampered_cycle_is_never_claimed() -> None:
    cycle = _seed_fix_cycle()
    store = AgentDbFixPromotionClaimStore()
    db = store._db()
    with db.db.get_connection() as conn:
        conn.execute(
            """
            UPDATE reddog_resident_architect_cycles
            SET cycle_json = replace(cycle_json, '"architect_action":"FIX"',
                '"architect_action":"STOP"')
            WHERE intent_id = ?
            """,
            (cycle.intent_id,),
        )

    assert claim_next_reddog_fix_promotion(worker_id="main", now=NOW).accepted is False


def test_main_bridge_materializes_existing_handoff_artifacts(tmp_path: Path) -> None:
    cycle = _seed_fix_cycle()
    runtime = tmp_path / "runtime"

    result = run_reddog_main_fix_promotion_claim_handoff(
        repo_root=REPO_ROOT,
        architect_determination_output_path=runtime / "determination.json",
        memex_supply_receipt_output_path=runtime / "memex.json",
        worker_id="main",
        now=NOW,
    )

    assert result.accepted is True
    assert result.status == MAIN_FIX_CLAIM_HANDOFF_APPLIED
    assert result.claim and result.claim.intent_id == cycle.intent_id
    assert Path(str(result.architect_determination_path)).is_file()
    assert Path(str(result.memex_supply_receipt_path)).is_file()
    assert result.no_signing_performed is True
    assert result.no_queue_mutation_performed is True


def test_main_bridge_releases_claim_when_handoff_rejects(tmp_path: Path) -> None:
    _seed_fix_cycle(include_memex=False)

    rejected = run_reddog_main_fix_promotion_claim_handoff(
        repo_root=REPO_ROOT,
        architect_determination_output_path=tmp_path / "runtime" / "determination.json",
        memex_supply_receipt_output_path=tmp_path / "runtime" / "memex.json",
        worker_id="main-a",
        now=NOW,
    )
    retried = claim_next_reddog_fix_promotion(
        worker_id="main-b",
        now=NOW + timedelta(seconds=1),
    )

    assert rejected.accepted is False
    assert retried.accepted is True


def test_main_durable_claim_rejection_never_falls_back_to_stale_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import main
    import modules.ai_intelligence.ai_gateway.src.model_selection_artifact_supply_bootstrap as model_supply
    import modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap as bootstrap
    import modules.communication.moltbot_bridge.src.reddog_main_fix_promotion_claim_handoff as handoff

    monkeypatch.setenv("REDDOG_AGENTDB_FIX_PROMOTION_CLAIM", "1")
    monkeypatch.setenv("REDDOG_ARCHITECT_FIX_PROMOTION_RUNTIME", "1")
    monkeypatch.setenv(
        "REDDOG_ARCHITECT_FIX_DETERMINATION_PATH",
        str(tmp_path / "stale-determination.json"),
    )
    monkeypatch.setattr(
        handoff,
        "run_reddog_main_fix_promotion_claim_handoff",
        lambda **kwargs: MainFixPromotionClaimHandoffResult(
            False,
            MAIN_FIX_CLAIM_HANDOFF_REJECT,
            None,
            None,
            None,
            ("cycle_integrity_invalid",),
        ),
    )
    monkeypatch.setattr(
        bootstrap,
        "run_reddog_main_architect_fix_promotion_bootstrap",
        lambda **kwargs: pytest.fail("legacy promotion fallback must not run"),
    )
    monkeypatch.setattr(
        model_supply,
        "run_reddog_model_selection_artifact_supply_bootstrap",
        lambda **kwargs: pytest.fail("suppliers must not run after invalid claim"),
    )

    assert main.run_reddog_architect_fix_promotion_preflight(REPO_ROOT) is True


def test_main_durable_claim_rejection_fails_when_promotion_is_enforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import main
    import modules.communication.moltbot_bridge.src.reddog_main_fix_promotion_claim_handoff as handoff

    monkeypatch.setenv("REDDOG_AGENTDB_FIX_PROMOTION_CLAIM", "1")
    monkeypatch.setenv("REDDOG_ARCHITECT_FIX_PROMOTION_RUNTIME", "1")
    monkeypatch.setenv("REDDOG_ARCHITECT_FIX_PROMOTION_ENFORCED", "1")
    monkeypatch.setattr(
        handoff,
        "run_reddog_main_fix_promotion_claim_handoff",
        lambda **kwargs: MainFixPromotionClaimHandoffResult(
            False,
            MAIN_FIX_CLAIM_HANDOFF_REJECT,
            None,
            None,
            None,
            ("cycle_integrity_invalid",),
        ),
    )

    assert main.run_reddog_architect_fix_promotion_preflight(REPO_ROOT) is False


def test_main_idle_claim_stops_before_model_suppliers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import main
    import modules.ai_intelligence.ai_gateway.src.model_selection_artifact_supply_bootstrap as model_supply
    import modules.communication.moltbot_bridge.src.reddog_main_fix_promotion_claim_handoff as handoff

    monkeypatch.setenv("REDDOG_AGENTDB_FIX_PROMOTION_CLAIM", "1")
    monkeypatch.setenv("REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY", "1")
    monkeypatch.setattr(
        handoff,
        "run_reddog_main_fix_promotion_claim_handoff",
        lambda **kwargs: MainFixPromotionClaimHandoffResult(
            False,
            MAIN_FIX_CLAIM_HANDOFF_REJECT,
            None,
            None,
            None,
            (),
        ),
    )
    monkeypatch.setattr(
        model_supply,
        "run_reddog_model_selection_artifact_supply_bootstrap",
        lambda **kwargs: pytest.fail("suppliers must not run without a claim"),
    )

    assert main.run_reddog_architect_fix_promotion_preflight(REPO_ROOT) is True


def test_main_claim_runtime_error_stops_before_model_suppliers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import main
    import modules.ai_intelligence.ai_gateway.src.model_selection_artifact_supply_bootstrap as model_supply
    import modules.communication.moltbot_bridge.src.reddog_main_fix_promotion_claim_handoff as handoff

    monkeypatch.setenv("REDDOG_AGENTDB_FIX_PROMOTION_CLAIM", "1")
    monkeypatch.setenv("REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY", "1")

    def fail_claim(**kwargs):
        raise RuntimeError("injected")

    monkeypatch.setattr(
        handoff,
        "run_reddog_main_fix_promotion_claim_handoff",
        fail_claim,
    )
    monkeypatch.setattr(
        model_supply,
        "run_reddog_model_selection_artifact_supply_bootstrap",
        lambda **kwargs: pytest.fail("suppliers must not run after claim failure"),
    )

    assert main.run_reddog_architect_fix_promotion_preflight(REPO_ROOT) is True


def test_forged_work_state_cannot_short_circuit_claim_reverification() -> None:
    signature = inspect.signature(run_reddog_main_fix_promotion_claim_handoff)

    assert "authoritative_work_state_path" not in signature.parameters
    assert "already_applied" not in MainFixPromotionClaimHandoffResult.__dataclass_fields__


def test_profile_derived_claim_rejection_never_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import main
    import modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap as bootstrap
    import modules.communication.moltbot_bridge.src.reddog_main_fix_promotion_claim_handoff as handoff

    monkeypatch.setattr(
        handoff,
        "run_reddog_main_fix_promotion_claim_handoff",
        lambda **kwargs: MainFixPromotionClaimHandoffResult(
            False,
            MAIN_FIX_CLAIM_HANDOFF_REJECT,
            None,
            None,
            None,
            ("cycle_integrity_invalid",),
        ),
    )
    monkeypatch.setattr(
        bootstrap,
        "run_reddog_main_architect_fix_promotion_bootstrap",
        lambda **kwargs: pytest.fail("profile claim must not fall through"),
    )
    with patch.dict(
        "os.environ",
        {"REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code"},
        clear=True,
    ):
        assert main.run_reddog_architect_fix_promotion_preflight(REPO_ROOT) is True


def test_profile_prefers_durable_claim_unless_legacy_mode_is_explicit() -> None:
    profile = {"REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code"}

    assert resident_queue_runtime_flag_enabled(
        profile,
        "REDDOG_AGENTDB_FIX_PROMOTION_CLAIM",
    )
    assert not resident_queue_runtime_flag_enabled(
        {**profile, "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF": "1"},
        "REDDOG_AGENTDB_FIX_PROMOTION_CLAIM",
    )
    assert resident_queue_runtime_flag_enabled(
        {
            **profile,
            "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF": "1",
            "REDDOG_AGENTDB_FIX_PROMOTION_CLAIM": "1",
        },
        "REDDOG_AGENTDB_FIX_PROMOTION_CLAIM",
    )


def test_main_aborts_before_promotion_when_claim_lease_is_lost(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import main
    import modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap as bootstrap

    _seed_fix_cycle()
    monkeypatch.setenv("REDDOG_AGENTDB_FIX_PROMOTION_CLAIM", "1")
    monkeypatch.setenv("REDDOG_ARCHITECT_FIX_PROMOTION_RUNTIME", "1")
    monkeypatch.setenv(
        "REDDOG_ARCHITECT_FIX_DETERMINATION_PATH",
        str(tmp_path / "runtime" / "determination.json"),
    )
    monkeypatch.setenv(
        "REDDOG_MEMEX_SUPPLY_RECEIPT_PATH",
        str(tmp_path / "runtime" / "memex.json"),
    )
    monkeypatch.setattr(
        AgentDbFixPromotionClaimStore,
        "renew",
        lambda self, claim, **kwargs: False,
    )
    monkeypatch.setattr(
        bootstrap,
        "run_reddog_main_architect_fix_promotion_bootstrap",
        lambda **kwargs: pytest.fail("promotion must not run after lease loss"),
    )

    assert main.run_reddog_architect_fix_promotion_preflight(REPO_ROOT) is True


def test_renewed_lease_blocks_reclaim_and_expired_renewal_fails() -> None:
    _seed_fix_cycle()
    store = AgentDbFixPromotionClaimStore()
    claim = claim_next_reddog_fix_promotion(
        worker_id="main",
        now=NOW,
        lease_seconds=60,
    )

    assert store.renew(
        claim,
        now=NOW + timedelta(seconds=30),
        lease_seconds=900,
    )
    assert claim_next_reddog_fix_promotion(
        worker_id="other",
        now=NOW + timedelta(seconds=61),
    ).accepted is False
    assert store.renew(claim, now=NOW + timedelta(seconds=931)) is False
    assert store.complete(claim, now=NOW + timedelta(seconds=931)) is False


def test_reclaimed_lease_fences_stale_worker_before_operation() -> None:
    _seed_fix_cycle()
    store = AgentDbFixPromotionClaimStore()
    stale = claim_next_reddog_fix_promotion(
        worker_id="stale", now=NOW, lease_seconds=30
    )
    current = claim_next_reddog_fix_promotion(
        worker_id="current", now=NOW + timedelta(seconds=31)
    )
    calls: list[dict[str, object]] = []

    with pytest.raises(FixPromotionClaimFenceLost):
        execute_with_fix_promotion_claim_fence(
            store,
            stale,
            lambda fence: calls.append(dict(fence)),
            now=NOW + timedelta(seconds=31),
        )

    assert current.accepted is True
    assert current.claim_revision > stale.claim_revision
    assert calls == []


def test_fenced_success_atomically_binds_promotion_receipt() -> None:
    _seed_fix_cycle()
    store = AgentDbFixPromotionClaimStore()
    claim = claim_next_reddog_fix_promotion(worker_id="main", now=NOW)
    expected = SimpleNamespace(
        accepted=True,
        receipt=SimpleNamespace(
            promotion_receipt_id="architect_fix_promotion:test",
            committed_revision="sha256:committed",
        ),
    )

    result = execute_with_fix_promotion_claim_fence(
        store,
        claim,
        lambda fence: expected,
        now=NOW + timedelta(seconds=1),
    )

    assert result is expected
    with store._db().db.get_connection() as conn:
        row = conn.execute(
            "SELECT status, promotion_receipt_id, committed_revision "
            "FROM reddog_fix_promotion_claims WHERE claim_id = ?",
            (claim.claim_id,),
        ).fetchone()
    assert row["status"] == "APPLIED"
    assert row["promotion_receipt_id"] == "architect_fix_promotion:test"
    assert row["committed_revision"] == "sha256:committed"


def test_corrupted_existing_claim_binding_is_never_leased() -> None:
    cycle = _seed_fix_cycle()
    store = AgentDbFixPromotionClaimStore()
    determination = store.load_determination(cycle.architect_determination_id)
    candidate = determination["queue_candidate"]
    allocation = candidate["wsp15_allocation_receipt"]
    store.determined_intent_ids()
    with store._db().db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO reddog_fix_promotion_claims
            (claim_id, intent_id, cycle_id, determination_id, queue_candidate_id,
             wsp15_receipt_id, status, revision, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING', 0, ?)
            """,
            (
                "sha256:attacker",
                cycle.intent_id,
                cycle.cycle_id,
                cycle.architect_determination_id,
                "sha256:wrong-candidate",
                allocation["receipt_id"],
                NOW.isoformat().replace("+00:00", "Z"),
            ),
        )

    assert claim_next_reddog_fix_promotion(worker_id="main", now=NOW).accepted is False


def test_materialization_rejects_determination_changed_after_claim(
    tmp_path: Path,
) -> None:
    cycle = _seed_fix_cycle()
    store = AgentDbFixPromotionClaimStore()
    claim = claim_next_reddog_fix_promotion(worker_id="main", now=NOW)
    determination = dict(store.load_determination(cycle.architect_determination_id))
    determination["queue_candidate"] = dict(determination["queue_candidate"])
    determination["queue_candidate"]["queue_candidate_id"] = "sha256:replacement"
    with store._db().db.get_connection() as conn:
        conn.execute(
            "UPDATE reddog_architect_determinations SET determination_json = ? "
            "WHERE determination_receipt_id = ?",
            (
                json.dumps(determination, sort_keys=True, separators=(",", ":")),
                cycle.architect_determination_id,
            ),
        )

    result = artifact_handoff.run_reddog_resident_fix_promotion_artifact_handoff(
        repo_root=REPO_ROOT,
        intent_id=cycle.intent_id,
        architect_determination_output_path=tmp_path / "determination.json",
        memex_supply_receipt_output_path=tmp_path / "memex.json",
        expected_claim_binding={
            "cycle_id": claim.cycle_id,
            "snapshot_id": claim.snapshot_id,
            "determination_id": claim.determination_id,
            "queue_candidate_id": claim.queue_candidate_id,
            "wsp15_allocation_receipt_id": claim.wsp15_allocation_receipt_id,
        },
    )

    assert result.accepted is False
    assert "fix_claim_binding_mismatch" in result.rejection_reasons
    assert not (tmp_path / "determination.json").exists()


def test_artifact_pair_failure_restores_previous_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cycle = _seed_fix_cycle()
    determination_path = tmp_path / "determination.json"
    memex_path = tmp_path / "memex.json"
    determination_path.write_bytes(b"old-determination")
    memex_path.write_bytes(b"old-memex")
    original = artifact_handoff._write_json_atomic
    calls = 0

    def fail_second(path, payload):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected")
        original(path, payload)

    monkeypatch.setattr(artifact_handoff, "_write_json_atomic", fail_second)
    result = artifact_handoff.run_reddog_resident_fix_promotion_artifact_handoff(
        repo_root=REPO_ROOT,
        intent_id=cycle.intent_id,
        architect_determination_output_path=determination_path,
        memex_supply_receipt_output_path=memex_path,
    )

    assert result.accepted is False
    assert determination_path.read_bytes() == b"old-determination"
    assert memex_path.read_bytes() == b"old-memex"


def test_claim_modules_have_no_execution_or_network_imports() -> None:
    banned = {"subprocess", "requests", "urllib", "http", "socket", "git"}
    paths = [
        *SRC_ROOT.glob("reddog_agentdb_fix_promotion_claim*.py"),
        SRC_ROOT / "reddog_agentdb_architect_determination_reader.py",
        SRC_ROOT / "reddog_main_fix_promotion_claim_handoff.py",
        SRC_ROOT / "reddog_main_fix_promotion_claim_preparation.py",
        SRC_ROOT / "reddog_main_fix_promotion_claim_runtime.py",
    ]
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".", 1)[0] not in banned for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".", 1)[0] not in banned


def test_claim_modules_stay_within_wsp62_bounds() -> None:
    paths = [
        *SRC_ROOT.glob("reddog_agentdb_fix_promotion_claim*.py"),
        SRC_ROOT / "reddog_agentdb_architect_determination_reader.py",
        SRC_ROOT / "reddog_main_fix_promotion_claim_handoff.py",
        SRC_ROOT / "reddog_main_fix_promotion_claim_preparation.py",
        SRC_ROOT / "reddog_main_fix_promotion_claim_runtime.py",
    ]
    for path in paths:
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 200
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = node.end_lineno or node.lineno
                assert end - node.lineno + 1 <= 50, f"{path.name}:{node.name}"


def test_touched_legacy_functions_do_not_grow_past_base() -> None:
    for filename, ceilings in TOUCHED_FUNCTION_NO_GROWTH.items():
        tree = ast.parse((SRC_ROOT / filename).read_text(encoding="utf-8"))
        sizes = {
            node.name: (node.end_lineno or node.lineno) - node.lineno + 1
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for name, ceiling in ceilings.items():
            assert sizes[name] <= ceiling, f"{filename}:{name}"
