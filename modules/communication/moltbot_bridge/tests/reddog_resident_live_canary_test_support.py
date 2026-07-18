"""Canonical local integration support for resident live-canary tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_receipt_store import (
    build_resident_control_loop_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_resident_live_canary import (
    LIVE_CANARY_CONFIRMATION,
    REQUIRED_JSON_ARTIFACTS,
    run_reddog_resident_live_canary,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    CHAIN_RESULTS_SCHEMA_VERSION,
    AtomicJsonResidentQueueChainResultsStore,
    record_resident_queue_stage_result,
    resident_queue_chain_receipt_id,
    resident_queue_chain_snapshot_is_canonical,
    resident_queue_chain_snapshot_revision,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_CHAIN_COMPLETE,
    _CHAIN,
    plan_reddog_resident_queue_orchestration,
)
from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
    build_reddog_verified_pattern_memory_sink,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_held_out_regression_gate_invoke import (
    invoke_reddog_wre_queue_authorized_held_out_regression_gate,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_pattern_memory_admission_invoke import (
    QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT,
    invoke_reddog_wre_queue_authorized_pattern_memory_admission,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_draft_pr_publish_invoke import (
    invoke_reddog_wre_queue_authorized_verified_draft_pr_publish,
)
from modules.communication.moltbot_bridge.src.reddog_wre_worktree_create import WORKTREE_CREATE_ACCEPT
from modules.communication.moltbot_bridge.tests.test_reddog_resident_queue_serial_loop import _snapshot


QUEUE_ID = "queue-1"
SLICE_NAME = "REDDOG_TEST_SLICE_PHASE1"
WORK_ORDER_ID = "work-order-1"
NOW = "2026-07-14T00:00:00+00:00"


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _roots(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "reddog-canary@example.invalid")
    _git(repo, "config", "user.name", "RedDog Canary Test")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-m", "test: seed live canary repo")
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    for filename in REQUIRED_JSON_ARTIFACTS:
        (runtime / filename).write_text(json.dumps({"kind": filename}), encoding="utf-8")
    return repo, runtime


def _kwargs(repo: Path, runtime: Path) -> dict[str, object]:
    return {
        "repo_root": repo,
        "runtime_root": runtime,
        "environ": {"OPENROUTER_API_KEY": "must-never-be-serialized"},
        "platform_name": "linux",
        "command_resolver": lambda command: f"/usr/bin/{command}",
        "command_probe": lambda argv, cwd: True,
        "socket_probe": lambda path: path.name == "reddog_signer.sock",
    }


class _DraftRunner:
    def push_branch(self, *, worktree_path: Path, branch_name: str):
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}

    def create_draft_pr(self, **_: object) -> str:
        return "https://github.com/FOUNDUPS/Foundups-Agent/pull/9999"


def _create_registered_worktree(repo: Path, runtime: Path) -> tuple[Path, str]:
    isolated = runtime.parent / "isolated-worker"
    _git(repo, "worktree", "add", "--detach", str(isolated), "HEAD")
    return isolated.resolve(), _git(isolated, "rev-parse", "HEAD")


def _draft_stage(isolated: Path, head: str) -> dict[str, object]:
    verifier = {
        "decision": "QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT",
        "verifier_result": {
            "decision": "AUTONOMOUS_SLICE_VERIFIER_ACCEPT",
            "accepted": True,
            "receipt": {
                "receipt_id": "wre_slice_verify_canary",
                "work_order_id": WORK_ORDER_ID,
                "slice_name": SLICE_NAME,
                "head_sha": head,
                "changed_paths": ["seed.txt"],
            },
        },
    }
    request = {
        "work_order_id": WORK_ORDER_ID,
        "pre_publish_branch_head_sha": head,
        "branch_name": "feat/reddog-live-canary-test",
        "base_branch": "main",
        "pr_title": "test: resident live canary evidence",
        "pr_body": "Canonical test-only draft receipt.",
        "worktree_path": str(isolated),
        "draft_pr_only": True,
        "mark_ready": False,
        "merge": False,
    }
    return invoke_reddog_wre_queue_authorized_verified_draft_pr_publish(
        explicit_queue_authorized_verified_draft_pr_publish_requested=True,
        queue_slice_verifier_result=verifier,
        publish_request=request,
        runner=_DraftRunner(),
    ).to_dict()


def _held_out_stage(head: str) -> dict[str, object]:
    ratchet = {
        "decision": "QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT",
        "ratchet_result": {
            "decision": "OUTCOME_RATCHET_RECORDED",
            "accepted": True,
            "receipt": {
                "ratchet_id": "outcome_ratchet_canary",
                "work_order_id": WORK_ORDER_ID,
                "slice_name": SLICE_NAME,
                "verifier_receipt_id": "wre_slice_verify_canary",
                "pattern_memory_eligible": True,
            },
        },
    }
    request = {
        "work_order_id": WORK_ORDER_ID,
        "slice_name": SLICE_NAME,
        "worker_id": "reddog-0102",
        "enable_pattern_memory_admission": True,
        "improvement_job": {"job_id": "imp_live_canary", "status": "pending", "dry_run": True},
        "verification_result": {
            "accepted": True,
            "decision": "AUTONOMOUS_SLICE_VERIFIER_ACCEPT",
            "receipt": {
                "receipt_id": "wre_slice_verify_canary",
                "work_order_id": WORK_ORDER_ID,
                "slice_name": SLICE_NAME,
                "head_sha": head,
            },
        },
        "held_out_regression": {
            "suite_id": "heldout-live-canary",
            "is_held_out": True,
            "independent": True,
            "generated_by_author": False,
            "evidence_author_id": "verifier-0102",
            "passed": True,
            "test_count": 1,
            "failure_count": 0,
            "suite_digest": "sha256:" + "1" * 64,
            "baseline_digest": "sha256:" + "2" * 64,
            "candidate_digest": "sha256:" + "3" * 64,
            "candidate_head_sha": head,
        },
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": "sha256:" + "4" * 64,
        },
    }
    return invoke_reddog_wre_queue_authorized_held_out_regression_gate(
        explicit_queue_authorized_held_out_regression_gate_requested=True,
        queue_verified_outcome_ratchet_result=ratchet,
        held_out_gate_request=request,
    ).to_dict()


def _stage_results(repo: Path, runtime: Path) -> dict[str, dict[str, object]]:
    isolated, head = _create_registered_worktree(repo, runtime)
    stages = {stage.key: {stage.status_field: stage.accepted_value} for stage in _CHAIN}
    stages["worktree_create"].update(
        worktree_create_result={"decision": WORKTREE_CREATE_ACCEPT, "worktree_path": str(isolated)}
    )
    stages["verified_draft_pr_publish"] = _draft_stage(isolated, head)
    stages["held_out_regression_gate"] = _held_out_stage(head)
    stages.pop("pattern_memory_admission")
    return stages


def _write_pre_state(repo: Path, runtime: Path) -> dict[str, object]:
    (runtime / "authoritative_work_state.json").write_text(json.dumps(_snapshot()), encoding="utf-8")
    store = AtomicJsonResidentQueueChainResultsStore(runtime / "resident_queue_chain_results.json")
    for stage_key, stage_result in _stage_results(repo, runtime).items():
        result = record_resident_queue_stage_result(
            work_state_snapshot=_snapshot(), store=store, stage_key=stage_key,
            stage_result=stage_result, now_iso=NOW, requested_queue_item_id=QUEUE_ID,
        )
        assert result.accepted is True
    state = dict(store.load())
    assert resident_queue_chain_snapshot_is_canonical(state) is True
    return state


def _control_receipt(repo: Path, **changes: object) -> dict[str, object]:
    receipt = build_resident_control_loop_receipt(
        result={
            "accepted": True, "status": "PASS", "rounds": 1, "serial_progress": 1,
            "claim_progress": 0, "control_lock_acquired": True,
            "receipt_ids": ("serial-receipt-1",), "rejection_reasons": (),
        },
        repo_root=repo,
        created_at="2026-07-14T00:00:00Z",
    ).to_dict()
    receipt.update(changes)
    return receipt


def _canonicalize_terminal_receipt(chain: dict[str, object]) -> None:
    stages = dict(chain["stage_results"])
    final_plan = plan_reddog_resident_queue_orchestration(
        _snapshot(), chain_results=stages, requested_queue_item_id=QUEUE_ID, now_iso=NOW
    )
    previous_stages = dict(stages)
    previous_stages.pop("pattern_memory_admission")
    previous_plan = plan_reddog_resident_queue_orchestration(
        _snapshot(), chain_results=previous_stages,
        requested_queue_item_id=QUEUE_ID, now_iso=NOW,
    )
    receipt = chain["receipts"][-1]
    receipt.update(
        recorded_stage="pattern_memory_admission",
        previous_plan_id=previous_plan.plan_id,
        next_plan_id=final_plan.plan_id,
        next_action=NEXT_QUEUE_CHAIN_COMPLETE,
        receipt_id=resident_queue_chain_receipt_id(
            queue_item_id=QUEUE_ID,
            selected_slice=SLICE_NAME,
            recorded_stage="pattern_memory_admission",
            previous_plan_id=previous_plan.plan_id,
            next_plan_id=final_plan.plan_id,
        ),
    )


def _runner(
    repo: Path,
    runtime: Path,
    *,
    chain_mutator=None,
    receipt_changes: dict[str, object] | None = None,
    result_receipt_id: str | None = None,
    rebind_after_mutation: bool = True,
    pattern_db_mutator=None,
):
    def run(_: Path) -> dict[str, object]:
        store = AtomicJsonResidentQueueChainResultsStore(runtime / "resident_queue_chain_results.json")
        chain = dict(store.load())
        held = chain["stage_results"]["held_out_regression_gate"]
        sink = build_reddog_verified_pattern_memory_sink(repo_root=repo, db_path=runtime / "pattern_memory.db")
        pattern = invoke_reddog_wre_queue_authorized_pattern_memory_admission(
            explicit_queue_authorized_pattern_memory_admission_requested=True,
            queue_held_out_gate_result=held,
            admission_request={"work_order_id": WORK_ORDER_ID},
            sink=sink,
        )
        assert pattern.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT
        recorded = record_resident_queue_stage_result(
            work_state_snapshot=_snapshot(), store=store, stage_key="pattern_memory_admission",
            stage_result=pattern.to_dict(), now_iso=NOW, requested_queue_item_id=QUEUE_ID,
        )
        assert recorded.accepted is True
        if pattern_db_mutator:
            pattern_db_mutator(runtime / "pattern_memory.db", pattern.receipt.pattern_memory_record_id)
        chain = dict(store.load())
        if chain_mutator:
            chain_mutator(chain)
            if rebind_after_mutation and chain.get("schema_version") == CHAIN_RESULTS_SCHEMA_VERSION:
                revision = resident_queue_chain_snapshot_revision(chain)
                chain["revision"] = revision
                if chain.get("receipts"):
                    chain["receipts"][-1]["store_revision"] = revision
        (runtime / "resident_queue_chain_results.json").write_text(json.dumps(chain), encoding="utf-8")
        control = _control_receipt(repo, **(receipt_changes or {}))
        (runtime / "resident_queue_control_loop_receipts.jsonl").write_text(
            json.dumps(control) + "\n", encoding="utf-8"
        )
        return {"accepted": True, "status": "PASS", "receipt_id": result_receipt_id or control["receipt_id"]}

    return run


def _execute(repo: Path, runtime: Path, **runner_kwargs: object):
    _write_pre_state(repo, runtime)
    return run_reddog_resident_live_canary(
        **_kwargs(repo, runtime), execute=True, confirmation=LIVE_CANARY_CONFIRMATION,
        queue_item_id=QUEUE_ID, control_loop_runner=_runner(repo, runtime, **runner_kwargs),
        now=lambda: __import__("datetime").datetime.fromisoformat(NOW),
    )
