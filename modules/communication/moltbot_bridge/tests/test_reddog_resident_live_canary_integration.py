"""Fail-closed integration boundary for the blocked live-canary proof path."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
    build_reddog_verified_pattern_memory_sink,
    reddog_verified_pattern_memory_record_id,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_pattern_memory_admission_invoke import (
    canonical_pattern_memory_admission_identity,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_live_canary_test_support import (
    _canonicalize_terminal_receipt,
    _execute,
    _roots,
)
from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory


def _assert_missing_anchor_block(receipt) -> None:
    assert receipt.live_proof_complete is False
    assert (
        "canonical_signed_runtime_artifact_manifest_selection_verifier_missing"
        in receipt.blockers
    )


def test_live_proof_uses_canonical_store_git_and_pattern_memory(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    receipt = _execute(repo, runtime)

    _assert_missing_anchor_block(receipt)
    assert receipt.execution_invoked is False


@pytest.mark.parametrize(
    ("mutator", "blocker"),
    [
        (lambda chain: chain.update(schema_version="wrong"), "chain_results_schema_mismatch"),
        (lambda chain: chain.update(queue_item_id="other"), "chain_envelope_plan_mismatch"),
        (lambda chain: chain.update(receipts=chain["receipts"][:-1]), "new_chain_store_receipt_not_observed"),
        (lambda chain: chain["receipts"][-1].pop("recorded_stage"), "new_chain_store_receipt_malformed"),
        (
            lambda chain: chain["receipts"][-1].update(recorded_stage="other_nonempty_stage"),
            "final_chain_store_receipt_transition_mismatch",
        ),
        (
            lambda chain: chain["receipts"][-1].update(previous_plan_id="sha256:wrong-previous"),
            "final_chain_store_receipt_transition_mismatch",
        ),
        (
            lambda chain: chain["receipts"][-1].update(next_plan_id="sha256:wrong-final"),
            "final_chain_store_receipt_transition_mismatch",
        ),
        (
            lambda chain: chain["receipts"][-1].update(next_action="OTHER_NONEMPTY_ACTION"),
            "final_chain_store_receipt_transition_mismatch",
        ),
        (
            lambda chain: chain["stage_results"]["held_out_regression_gate"]["gate_result"]["receipt"].update(candidate_head_sha="c" * 40),
            "key_receipt_lineage_mismatch",
        ),
        (
            lambda chain: chain["stage_results"]["pattern_memory_admission"]["receipt"].update(work_order_id="other"),
            "key_receipt_lineage_mismatch",
        ),
    ],
)
def test_false_chain_evidence_cannot_complete_proof(tmp_path: Path, mutator, blocker: str) -> None:
    repo, runtime = _roots(tmp_path)
    receipt = _execute(repo, runtime, chain_mutator=mutator)
    _assert_missing_anchor_block(receipt)


def test_forged_chain_store_revision_fails_canonical_verification(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    receipt = _execute(
        repo, runtime,
        chain_mutator=lambda chain: chain["receipts"][-1].update(store_revision="wrong"),
        rebind_after_mutation=False,
    )
    _assert_missing_anchor_block(receipt)


@pytest.mark.parametrize("field", ["admission_id", "pattern_memory_record_id", "record_digest"])
def test_pattern_memory_receipt_requires_all_durable_ids(tmp_path: Path, field: str) -> None:
    repo, runtime = _roots(tmp_path)

    def mutate(chain):
        chain["stage_results"]["pattern_memory_admission"]["receipt"].pop(field)

    receipt = _execute(repo, runtime, chain_mutator=mutate)
    _assert_missing_anchor_block(receipt)


def test_pattern_memory_record_must_read_back_from_canonical_db(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)

    def delete_record(db_path: Path, record_id: str) -> None:
        memory = PatternMemory(db_path=db_path)
        try:
            memory.conn.execute("DELETE FROM skill_outcomes WHERE execution_id = ?", (record_id,))
            memory.conn.commit()
        finally:
            memory.close()

    receipt = _execute(repo, runtime, pattern_db_mutator=delete_record)
    _assert_missing_anchor_block(receipt)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("work_order_id", "wrong-but-valid-work-order"),
        ("slice_name", "WRONG_BUT_VALID_SLICE"),
        ("candidate_head_sha", "f" * 40),
    ],
)
def test_digest_valid_db_context_must_match_plan_draft_and_git_head(
    tmp_path: Path, field: str, value: str
) -> None:
    repo, runtime = _roots(tmp_path)
    replacement: dict[str, str] = {}

    def mutate_db(db_path: Path, record_id: str) -> None:
        sink = build_reddog_verified_pattern_memory_sink(repo_root=repo, db_path=db_path)
        assert sink is not None
        record = sink.load_verified_outcome(record_id)
        assert record is not None
        modified = {**record, field: value}
        new_id = reddog_verified_pattern_memory_record_id(modified)
        memory = PatternMemory(db_path=db_path)
        try:
            memory.conn.execute(
                "INSERT INTO skill_outcomes "
                "SELECT ?, skill_name, agent, timestamp, input_context, ?, success, "
                "pattern_fidelity, outcome_quality, execution_time_ms, step_count, "
                "failed_at_step, notes FROM skill_outcomes WHERE execution_id = ?",
                (new_id, json.dumps(modified, sort_keys=True), record_id),
            )
            memory.conn.commit()
        finally:
            memory.close()
        admission_id, digest = canonical_pattern_memory_admission_identity(modified, new_id)
        replacement.update(
            admission_id=admission_id,
            pattern_memory_record_id=new_id,
            record_digest=digest,
        )

    def mutate_chain(chain: dict[str, object]) -> None:
        chain["stage_results"]["pattern_memory_admission"]["receipt"].update(replacement)
        _canonicalize_terminal_receipt(chain)

    receipt = _execute(
        repo, runtime, pattern_db_mutator=mutate_db, chain_mutator=mutate_chain
    )
    _assert_missing_anchor_block(receipt)


@pytest.mark.parametrize(
    "failure",
    ["stage", "invoke", "missing", "not_git", "inside", "unregistered", "head"],
)
def test_worktree_proof_requires_registered_git_worktree(tmp_path: Path, failure: str) -> None:
    repo, runtime = _roots(tmp_path)

    def mutate(chain):
        stage = chain["stage_results"]["worktree_create"]
        result = stage["worktree_create_result"]
        if failure == "stage":
            stage["decision"] = "REJECT"
        elif failure == "invoke":
            result["decision"] = "REJECT"
        elif failure == "missing":
            result["worktree_path"] = str(runtime / "absent")
        elif failure == "not_git":
            Path(result["worktree_path"], ".git").unlink()
        elif failure == "inside":
            inside = repo / "worker"
            inside.mkdir()
            (inside / ".git").write_text("gitdir: inside", encoding="utf-8")
            result["worktree_path"] = str(inside)
        elif failure == "unregistered":
            clone = runtime.parent / "unregistered-clone"
            subprocess.run(
                ["git", "clone", "--no-hardlinks", str(repo), str(clone)],
                capture_output=True, text=True, check=True,
            )
            result["worktree_path"] = str(clone)
        else:
            forged = "f" * 40
            chain["stage_results"]["verified_draft_pr_publish"]["publish_result"]["receipt"]["verified_head_sha"] = forged
            chain["stage_results"]["held_out_regression_gate"]["gate_result"]["receipt"]["candidate_head_sha"] = forged

    receipt = _execute(repo, runtime, chain_mutator=mutate)
    _assert_missing_anchor_block(receipt)


@pytest.mark.parametrize("execute", [False, True], ids=["readiness-only", "execute-requested"])
def test_blocked_canary_never_invokes_deferred_callbacks(tmp_path: Path, monkeypatch, execute: bool) -> None:
    """Current readiness rejection does not exercise downstream mutations."""
    from datetime import datetime
    from unittest.mock import Mock

    from modules.communication.moltbot_bridge.src import reddog_verified_pattern_memory_sink as sink
    from modules.communication.moltbot_bridge.tests import reddog_resident_live_canary_test_support as support

    repo, runtime = _roots(tmp_path)
    support._write_pre_state(repo, runtime)
    chain_path = runtime / "resident_queue_chain_results.json"
    before = chain_path.read_bytes()
    chain_mutator = Mock(side_effect=AssertionError("chain mutation must not run"))
    pattern_mutator = Mock(side_effect=AssertionError("database mutation must not run"))
    memory_constructor = Mock(side_effect=AssertionError("PatternMemory must not open"))
    monkeypatch.setattr(sink, "PatternMemory", memory_constructor)
    runner = Mock(wraps=support._runner(
        repo, runtime, chain_mutator=chain_mutator, pattern_db_mutator=pattern_mutator
    ))

    receipt = support.run_reddog_resident_live_canary(
        **support._kwargs(repo, runtime), execute=execute,
        confirmation=support.LIVE_CANARY_CONFIRMATION,
        queue_item_id=support.QUEUE_ID, control_loop_runner=runner,
        now=lambda: datetime.fromisoformat(support.NOW),
    )

    _assert_missing_anchor_block(receipt)
    assert receipt.status == "BLOCKED"
    assert receipt.execution_requested is execute
    assert receipt.execution_invoked is False
    runner.assert_not_called()
    chain_mutator.assert_not_called()
    pattern_mutator.assert_not_called()
    memory_constructor.assert_not_called()
    assert chain_path.read_bytes() == before
    assert not (runtime / "pattern_memory.db").exists()


@pytest.mark.parametrize(
    ("mutation", "expected_blockers"),
    [
        ("prestate", ("resident_chain_not_complete", "new_chain_store_receipt_not_observed")),
        ("schema", ("chain_results_schema_mismatch",)),
        ("revision", ("chain_results_revision_invalid",)),
    ],
    ids=["incomplete-prestate", "schema-mismatch", "revision-mismatch"],
)
def test_uninvoked_chain_leaf_reports_specific_blockers(tmp_path: Path, mutation: str, expected_blockers) -> None:
    """Exercise pure chain checks without admitting or executing a canary."""
    from modules.communication.moltbot_bridge.src import reddog_resident_live_canary_evidence as evidence
    from modules.communication.moltbot_bridge.tests import reddog_resident_live_canary_test_support as support

    repo, runtime = _roots(tmp_path)
    state = support._write_pre_state(repo, runtime)
    chain_path = runtime / "resident_queue_chain_results.json"
    before = chain_path.read_bytes()
    previous_revision = state["revision"]
    if mutation == "schema":
        state["schema_version"] = "wrong"
    elif mutation == "revision":
        state["revision"] = "sha256:" + "0" * 64
    invocation = evidence.CanaryInvocationEvidence(
        confirmed=False, invoked=False, blockers=("synthetic_evidence_only",),
        control_result={}, control_receipt={}, control_receipt_id=None,
        previous_revision=previous_revision, observed_revision=state["revision"],
        pre_chain_receipt_ids=evidence.chain_receipt_ids(state),
        work_state=support._snapshot(), chain_state=state,
    )

    plan, blockers = evidence._chain_evidence(invocation, support.QUEUE_ID, support.NOW)

    assert blockers == expected_blockers
    assert (plan is not None) is (mutation == "prestate")
    assert invocation.invoked is False
    assert chain_path.read_bytes() == before


def _synthetic_final_receipt_inputs():
    """Build structural inputs, not an admitted invocation or planner result."""
    from dataclasses import replace
    from modules.communication.moltbot_bridge.src.reddog_resident_live_canary_evidence import CanaryInvocationEvidence
    from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
        NEXT_QUEUE_CHAIN_COMPLETE, NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE,
        RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE, RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY,
        ResidentQueueOrchestrationPlan,
    )
    from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
        resident_queue_chain_receipt_id,
    )

    previous = ResidentQueueOrchestrationPlan(
        accepted=True, status=RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY,
        plan_id="synthetic-previous-plan", selected_queue_item_id="synthetic-queue",
        selected_slice="SYNTHETIC_RECEIPT", current_stage="pattern_memory_admission",
        next_action=NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE,
    )
    final = replace(
        previous, status=RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE,
        plan_id="synthetic-final-plan", current_stage=None, next_action=NEXT_QUEUE_CHAIN_COMPLETE,
    )
    transition = {
        "queue_item_id": final.selected_queue_item_id, "selected_slice": final.selected_slice,
        "recorded_stage": "pattern_memory_admission", "previous_plan_id": previous.plan_id,
        "next_plan_id": final.plan_id,
    }
    receipt = {
        **transition, "receipt_id": resident_queue_chain_receipt_id(**transition),
        "next_action": NEXT_QUEUE_CHAIN_COMPLETE, "store_revision": "sha256:" + "2" * 64,
    }
    seen_id = resident_queue_chain_receipt_id(
        **{**transition, "previous_plan_id": "synthetic-older-plan"}
    )
    invocation = CanaryInvocationEvidence(
        confirmed=False, invoked=False, blockers=("synthetic_evidence_only",),
        control_result={}, control_receipt={}, control_receipt_id=None,
        previous_revision="sha256:" + "1" * 64, observed_revision=receipt["store_revision"],
        pre_chain_receipt_ids=frozenset({seen_id}), work_state={},
        chain_state={"receipts": [receipt]},
    )
    return invocation, previous, final


_FINAL_RECEIPT_TRANSITION_BLOCKER = "final_chain_store_receipt_transition_mismatch"


@pytest.mark.parametrize(
    ("target", "field", "value", "expected_blocker"),
    [
        pytest.param("none", None, None, None, id="structural-control"),
        pytest.param("seen", None, None, "new_chain_store_receipt_not_observed", id="no-new-receipt"),
        pytest.param("old-final", None, None, "final_chain_store_receipt_not_new", id="final-already-observed"),
        pytest.param("remove", "recorded_stage", None, "new_chain_store_receipt_malformed", id="malformed-shape"),
        pytest.param("receipt", "queue_item_id", "other-queue", "new_chain_store_receipt_envelope_mismatch", id="queue-mismatch"),
        pytest.param("receipt", "selected_slice", "OTHER_SLICE", "new_chain_store_receipt_envelope_mismatch", id="slice-mismatch"),
        pytest.param("receipt", "store_revision", "other-revision", "new_chain_store_receipt_revision_mismatch", id="revision-mismatch"),
        pytest.param("receipt", "recorded_stage", "other-stage", _FINAL_RECEIPT_TRANSITION_BLOCKER, id="wrong-stage"),
        pytest.param("receipt", "previous_plan_id", "other-previous", _FINAL_RECEIPT_TRANSITION_BLOCKER, id="wrong-previous-plan"),
        pytest.param("receipt", "next_plan_id", "other-final", _FINAL_RECEIPT_TRANSITION_BLOCKER, id="wrong-next-plan"),
        pytest.param("receipt", "next_action", "OTHER_ACTION", _FINAL_RECEIPT_TRANSITION_BLOCKER, id="wrong-next-action"),
        pytest.param("receipt", "receipt_id", "sha256:" + "9" * 64, _FINAL_RECEIPT_TRANSITION_BLOCKER, id="wrong-derived-id"),
        pytest.param("previous", "accepted", False, _FINAL_RECEIPT_TRANSITION_BLOCKER, id="previous-rejected"),
        pytest.param("previous", "status", "OTHER_STATUS", _FINAL_RECEIPT_TRANSITION_BLOCKER, id="previous-wrong-status"),
        pytest.param("previous", "current_stage", "other-stage", _FINAL_RECEIPT_TRANSITION_BLOCKER, id="previous-wrong-stage"),
        pytest.param("previous", "next_action", "OTHER_ACTION", _FINAL_RECEIPT_TRANSITION_BLOCKER, id="previous-wrong-action"),
    ],
)
def test_final_chain_receipt_predicate_is_structural_and_nonmutating(target, field, value, expected_blocker) -> None:
    from copy import deepcopy
    from dataclasses import replace
    from modules.communication.moltbot_bridge.src.reddog_resident_live_canary_evidence import (
        _new_chain_receipt_blockers,
    )

    invocation, previous, final = _synthetic_final_receipt_inputs()
    receipt = invocation.chain_state["receipts"][0]
    if target == "seen":
        invocation = replace(invocation, pre_chain_receipt_ids=frozenset({receipt["receipt_id"]}))
    elif target == "old-final":
        invocation.chain_state["receipts"].append(
            {**receipt, "receipt_id": next(iter(invocation.pre_chain_receipt_ids))}
        )
    elif target == "remove":
        receipt.pop(field)
    elif target == "receipt":
        receipt[field] = value
    elif target == "previous":
        previous = replace(previous, **{field: value})
    before = deepcopy((invocation, previous, final))

    blockers = _new_chain_receipt_blockers(invocation, previous, final)

    assert blockers == (() if expected_blocker is None else (expected_blocker,))
    assert (invocation, previous, final) == before
    assert invocation.invoked is False
    assert invocation.confirmed is False



def _synthetic_pattern_readback_inputs(tmp_path, record_overrides, storage):
    """Seed only an explicit disposable DB; this is not sink activation."""
    import sqlite3
    from dataclasses import replace
    from modules.communication.moltbot_bridge.tests.test_reddog_verified_pattern_memory_sink import (
        _record, _seed_active,
    )
    from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_pattern_memory_admission_invoke import (
        QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT,
    )

    repo, runtime = tmp_path / "repo", tmp_path / "runtime"
    repo.mkdir()
    runtime.mkdir()
    original = _record()
    record = {**original, **record_overrides}
    invocation, _, final = _synthetic_final_receipt_inputs()
    assert invocation.invoked is False
    plan = replace(final, selected_slice=original["slice_name"])
    draft = {
        "work_order_id": original["work_order_id"], "slice_name": original["slice_name"],
        "head": original["candidate_head_sha"],
    }
    worktree = {"head": original["candidate_head_sha"]}
    record_id = reddog_verified_pattern_memory_record_id(record)
    admission_id, digest = canonical_pattern_memory_admission_identity(record, record_id)
    stage = {
        "decision": QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT,
        "pattern_memory_write_performed": True, "no_merge_performed": True,
        "receipt": {"admission_id": admission_id, "pattern_memory_record_id": record_id,
                    "record_digest": digest},
    }
    db_path = runtime / "pattern_memory.db"
    if storage != "absent":
        _seed_active(db_path, record_id, record)
    if storage == "deleted":
        connection = sqlite3.connect(db_path)
        try:
            connection.execute("DELETE FROM skill_outcomes WHERE execution_id = ?", (record_id,))
            connection.commit()
        finally:
            connection.close()
    return repo, runtime, record, plan, draft, worktree, stage


def _pattern_readback_skill_rows(db_path):
    """Snapshot logical outcomes, not schema/seed writes or raw DB bytes."""
    import sqlite3

    if not db_path.is_file():
        return None
    connection = sqlite3.connect(db_path)
    try:
        return tuple(connection.execute("SELECT * FROM skill_outcomes ORDER BY execution_id"))
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("target", "field", "value"),
    [
        pytest.param("control", None, None, id="canonical-synthetic-record"),
        pytest.param("remove", "admission_id", None, id="missing-admission-id"),
        pytest.param("remove", "pattern_memory_record_id", None, id="missing-record-id"),
        pytest.param("remove", "record_digest", None, id="missing-record-digest"),
        pytest.param("storage", None, "absent", id="database-absent"),
        pytest.param("storage", None, "deleted", id="record-deleted"),
        pytest.param("receipt", "admission_id", "pattern_memory_admission_" + "0" * 16, id="admission-identity-mismatch"),
        pytest.param("receipt", "record_digest", "sha256:" + "0" * 64, id="record-digest-mismatch"),
        pytest.param("record", "work_order_id", "other-work-order", id="reidentified-wrong-ticket"),
        pytest.param("record", "slice_name", "OTHER_SLICE", id="reidentified-wrong-slice"),
        pytest.param("record", "candidate_head_sha", "f" * 40, id="reidentified-wrong-commit"),
        pytest.param("plan", None, None, id="plan-absent"),
        pytest.param("plan", "selected_slice", "OTHER_SLICE", id="plan-slice-mismatch"),
        pytest.param("draft", "slice_name", "OTHER_SLICE", id="draft-slice-mismatch"),
        pytest.param("draft", "head", "f" * 40, id="draft-head-mismatch"),
        pytest.param("worktree", "head", "f" * 40, id="worktree-head-mismatch"),
        pytest.param("stage", "decision", "REJECT", id="stage-rejected"),
        pytest.param("stage", "pattern_memory_write_performed", False, id="write-not-performed"),
        pytest.param("stage", "no_merge_performed", False, id="no-merge-not-confirmed"),
    ],
)
def test_pattern_readback_leaf_requires_receipt_and_context(tmp_path, target, field, value) -> None:
    """Real disposable readback qualifies this leaf, not a live canary proof."""
    from copy import deepcopy
    from dataclasses import replace
    from modules.communication.moltbot_bridge.src.reddog_resident_live_canary_evidence import (
        _pattern_memory_evidence,
    )

    overrides = {field: value} if target == "record" else {}
    storage = value if target == "storage" else "present"
    repo, runtime, record, plan, draft, worktree, stage = _synthetic_pattern_readback_inputs(
        tmp_path, overrides, storage,
    )
    receipt = stage["receipt"]
    if target == "remove":
        receipt.pop(field)
    elif target == "receipt":
        receipt[field] = value
    elif target == "plan":
        plan = None if field is None else replace(plan, **{field: value})
    elif target in ("draft", "worktree", "stage"):
        {"draft": draft, "worktree": worktree, "stage": stage}[target][field] = value
    if target == "record":
        assert canonical_pattern_memory_admission_identity(record, receipt["pattern_memory_record_id"]) == (
            receipt["admission_id"], receipt["record_digest"],
        )
    stages = {"pattern_memory_admission": stage}
    before = deepcopy((stages, record, plan, draft, worktree))
    db_path = runtime / "pattern_memory.db"
    rows_before = _pattern_readback_skill_rows(db_path)

    result = _pattern_memory_evidence(stages, repo, runtime, plan, draft, worktree)

    assert result == {
        "blockers": () if target == "control" else ("highest_profile_completion_evidence_missing",),
        "admission_id": receipt.get("admission_id"),
        "record_id": receipt.get("pattern_memory_record_id"),
        "record_digest": receipt.get("record_digest"),
    }
    assert (stages, record, plan, draft, worktree) == before
    assert _pattern_readback_skill_rows(db_path) == rows_before
    if storage == "absent":
        assert not db_path.exists()
