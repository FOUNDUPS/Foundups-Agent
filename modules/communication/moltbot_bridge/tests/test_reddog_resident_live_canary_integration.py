"""Fail-closed integration boundary for the blocked live-canary proof path."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_resident_live_canary import (
    LIVE_CANARY_PROOF_COMPLETE,
)
from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
    build_reddog_verified_pattern_memory_sink,
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
    assert "canonical_signed_runtime_artifact_manifest_producer_missing" in receipt.blockers


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
        new_id = sink.store_verified_outcome(modified)
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
