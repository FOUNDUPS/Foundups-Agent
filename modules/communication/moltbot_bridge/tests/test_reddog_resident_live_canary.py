from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_receipt_store import (
    CONTROL_LOOP_RECEIPT_SCHEMA_VERSION,
    build_resident_control_loop_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_resident_live_canary import (
    LIVE_CANARY_BLOCKED,
    LIVE_CANARY_CONFIRMATION,
    LIVE_CANARY_PROOF_COMPLETE,
    LIVE_CANARY_PROOF_INCOMPLETE,
    LIVE_CANARY_READY,
    REQUIRED_JSON_ARTIFACTS,
    run_reddog_resident_live_canary,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
    PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    CHAIN_RESULTS_SCHEMA_VERSION,
    AtomicJsonResidentQueueChainResultsStore,
    record_resident_queue_stage_result,
    resident_queue_chain_snapshot_is_canonical,
    resident_queue_chain_snapshot_revision,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_control_lock import (
    CONTROL_LOOP_LOCK_PATH_ENV,
    acquire_resident_queue_control_lock,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE,
    _CHAIN,
    plan_reddog_resident_queue_orchestration,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_pattern_memory_admission_invoke import (
    QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT,
    canonical_pattern_memory_admission_identity,
    invoke_reddog_wre_queue_authorized_pattern_memory_admission,
)
from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
    build_reddog_verified_pattern_memory_sink,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_held_out_regression_gate_invoke import (
    invoke_reddog_wre_queue_authorized_held_out_regression_gate,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_draft_pr_publish_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT,
    invoke_reddog_wre_queue_authorized_verified_draft_pr_publish,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_worktree_create_invoke import (
    QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_worktree_create import (
    WORKTREE_CREATE_ACCEPT,
)
from modules.communication.moltbot_bridge.tests.test_reddog_resident_queue_serial_loop import (
    _snapshot,
)
from modules.infrastructure.wre_core.src.reddog_verified_draft_pr_publish import (
    VERIFIED_DRAFT_PR_PUBLISH_ACCEPT,
)
from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
PRODUCTION_PATHS = (
    SRC_ROOT / "reddog_resident_live_canary.py",
    SRC_ROOT / "reddog_resident_live_canary_evidence.py",
    SRC_ROOT / "reddog_resident_queue_control_lock.py",
    SRC_ROOT / "reddog_resident_control_loop_receipt_store.py",
)
COMMUNICATION_TEST_PATHS = (
    Path(__file__),
    Path(__file__).with_name("reddog_resident_live_canary_test_support.py"),
    Path(__file__).with_name("test_reddog_resident_live_canary_integration.py"),
)
from modules.communication.moltbot_bridge.tests.reddog_resident_live_canary_test_support import (
    NOW,
    QUEUE_ID,
    SLICE_NAME,
    _canonicalize_terminal_receipt,
    _control_receipt,
    _execute,
    _kwargs,
    _roots,
    _runner,
    _write_pre_state,
)


def test_readiness_is_non_executing_and_does_not_serialize_secret(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    receipt = run_reddog_resident_live_canary(**_kwargs(repo, runtime))

    assert receipt.status == LIVE_CANARY_READY
    assert receipt.ready_for_execution is True
    assert receipt.execution_invoked is False
    assert receipt.live_proof_complete is False
    serialized = (runtime / "live_canary_receipt.json").read_text(encoding="utf-8")
    assert "must-never-be-serialized" not in serialized
    assert json.loads(serialized)["secret_values_serialized"] is False


def test_windows_plane_is_truthfully_blocked(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    args = _kwargs(repo, runtime)
    args["platform_name"] = "win32"
    receipt = run_reddog_resident_live_canary(**args)

    assert receipt.status == LIVE_CANARY_BLOCKED
    assert "linux_execution_plane_required" in receipt.blockers


def test_execute_requires_exact_confirmation_and_never_calls_runner(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    called = False

    def runner(_: Path) -> dict[str, object]:
        nonlocal called
        called = True
        return {"accepted": True}

    receipt = run_reddog_resident_live_canary(
        **_kwargs(repo, runtime), execute=True, confirmation="wrong", control_loop_runner=runner
    )
    assert receipt.status == LIVE_CANARY_BLOCKED
    assert receipt.execution_invoked is False
    assert called is False
    assert "explicit_execution_confirmation_missing" in receipt.blockers


@pytest.mark.parametrize(
    ("changes", "blocker"),
    [
        ({"schema_version": "wrong"}, "control_receipt_schema_mismatch"),
        ({"accepted": False}, "control_receipt_not_accepted_pass"),
        ({"status": "WARN"}, "control_receipt_not_accepted_pass"),
        ({"control_lock_acquired": False}, "control_receipt_shared_lock_missing"),
        ({"repo_root_digest": "wrong"}, "control_receipt_repo_root_mismatch"),
        ({"serial_progress": 0}, "control_receipt_serial_progress_missing"),
    ],
)
def test_false_control_receipts_cannot_complete_proof(
    tmp_path: Path, changes: dict[str, object], blocker: str
) -> None:
    repo, runtime = _roots(tmp_path)
    receipt = _execute(repo, runtime, receipt_changes=changes)

    assert receipt.status == LIVE_CANARY_PROOF_INCOMPLETE
    assert blocker in receipt.blockers


def test_runner_result_must_match_one_new_persisted_control_receipt(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    receipt = _execute(repo, runtime, result_receipt_id="different-receipt")

    assert receipt.live_proof_complete is False
    assert "new_control_receipt_not_observed" in receipt.blockers


def test_preseeded_complete_chain_cannot_be_relabelled_as_new_live_proof(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    _write_pre_state(repo, runtime)
    _runner(repo, runtime)(repo)
    (runtime / "resident_queue_control_loop_receipts.jsonl").unlink()
    control = _control_receipt(repo)

    def runner(_: Path) -> dict[str, object]:
        (runtime / "resident_queue_control_loop_receipts.jsonl").write_text(
            json.dumps(control) + "\n", encoding="utf-8"
        )
        return {"accepted": True, "status": "PASS", "receipt_id": control["receipt_id"]}

    receipt = run_reddog_resident_live_canary(
        **_kwargs(repo, runtime), execute=True, confirmation=LIVE_CANARY_CONFIRMATION,
        queue_item_id=QUEUE_ID, control_loop_runner=runner,
        now=lambda: __import__("datetime").datetime.fromisoformat(NOW),
    )
    assert receipt.live_proof_complete is False
    assert "new_chain_revision_not_observed" in receipt.blockers


def test_live_proof_requires_a_pre_invocation_chain_revision(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    pre = _write_pre_state(repo, runtime)
    pre.pop("revision")
    (runtime / "resident_queue_chain_results.json").write_text(json.dumps(pre), encoding="utf-8")
    receipt = run_reddog_resident_live_canary(
        **_kwargs(repo, runtime), execute=True, confirmation=LIVE_CANARY_CONFIRMATION,
        queue_item_id=QUEUE_ID, control_loop_runner=_runner(repo, runtime),
        now=lambda: __import__("datetime").datetime.fromisoformat(NOW),
    )
    assert receipt.live_proof_complete is False
    assert "new_chain_revision_not_observed" in receipt.blockers


def test_receipt_path_allows_only_canonical_name_inside_runtime(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    canonical = runtime / "live_canary_receipt.json"
    receipt = run_reddog_resident_live_canary(
        **_kwargs(repo, runtime), receipt_path=canonical
    )
    assert receipt.status == LIVE_CANARY_READY
    assert canonical.is_file()


@pytest.mark.parametrize(
    "relative",
    [
        "resident_queue_chain_results.json",
        "resident_queue_control_loop_receipts.jsonl",
        "authoritative_work_state.json",
        "nested/live_canary_receipt.json",
    ],
)
def test_receipt_path_rejects_runtime_reserved_and_collision_paths(
    tmp_path: Path, relative: str
) -> None:
    repo, runtime = _roots(tmp_path)
    with pytest.raises(ValueError, match="receipt_path_reserved_or_collision"):
        run_reddog_resident_live_canary(
            **_kwargs(repo, runtime), receipt_path=runtime / relative
        )


def test_receipt_path_outside_repo_and_runtime_is_allowed(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    external = tmp_path / "receipts" / "canary.json"
    receipt = run_reddog_resident_live_canary(
        **_kwargs(repo, runtime), receipt_path=external
    )
    assert receipt.status == LIVE_CANARY_READY
    assert external.is_file()


def test_canonical_receipt_symlink_collision_is_rejected(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    target = runtime / "resident_queue_chain_results.json"
    target.write_text("preserve", encoding="utf-8")
    canonical = runtime / "live_canary_receipt.json"
    try:
        canonical.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ValueError, match="receipt_path_reserved_or_collision"):
        run_reddog_resident_live_canary(**_kwargs(repo, runtime))
    assert target.read_text(encoding="utf-8") == "preserve"


def test_receipt_path_inside_repo_is_rejected(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    with pytest.raises(ValueError, match="receipt_path_inside_repo"):
        run_reddog_resident_live_canary(
            **_kwargs(repo, runtime), receipt_path=repo / "receipt.json"
        )


def test_shared_control_lock_blocks_competing_main_control_loop(tmp_path: Path) -> None:
    import main

    repo, runtime = _roots(tmp_path)
    env = {"REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_LOCK_PATH": str(runtime / "control.lock")}
    with patch.dict(os.environ, env, clear=True):
        with acquire_resident_queue_control_lock(repo) as held:
            assert held.acquired is True
            with patch.object(
                main, "run_reddog_resident_queue_serial_loop_preflight"
            ) as serial_loop:
                assert main.run_reddog_resident_queue_control_loop_preflight(repo) is False
                serial_loop.assert_not_called()
    assert main.run_reddog_resident_queue_control_loop_preflight.last_result["status"] == "CONTROL_LOOP_LOCKED"


def test_shared_control_lock_excludes_a_competing_process(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    lock_path = runtime / "interprocess.lock"
    code = (
        "from modules.communication.moltbot_bridge.src.reddog_resident_queue_control_lock "
        "import acquire_resident_queue_control_lock, CONTROL_LOOP_LOCK_PATH_ENV\n"
        f"with acquire_resident_queue_control_lock(r'{repo}', "
        f"{{CONTROL_LOOP_LOCK_PATH_ENV: r'{lock_path}'}}) as lock:\n"
        " print(str(lock.acquired), flush=True)\n"
        " input()\n"
    )
    child = subprocess.Popen(
        [sys.executable, "-c", code], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, cwd=str(Path(__file__).resolve().parents[4]),
    )
    try:
        assert child.stdout is not None
        assert child.stdout.readline().strip() == "True"
        with acquire_resident_queue_control_lock(
            repo, {CONTROL_LOOP_LOCK_PATH_ENV: str(lock_path)}
        ) as competing:
            assert competing.acquired is False
            assert competing.reason == "control_loop_already_running"
    finally:
        if child.stdin is not None:
            child.stdin.write("\n")
            child.stdin.flush()
        child.wait(timeout=10)


def test_environment_is_restored_after_control_loop(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    before = os.environ.get("REDDOG_RESIDENT_QUEUE_BINDING_PROFILE")
    run_reddog_resident_live_canary(
        **_kwargs(repo, runtime), execute=True, confirmation=LIVE_CANARY_CONFIRMATION,
        control_loop_runner=lambda _: {"accepted": False, "status": "TEST_STOP"},
    )
    assert os.environ.get("REDDOG_RESIDENT_QUEUE_BINDING_PROFILE") == before


def test_actual_resident_chain_schema_and_constants_reach_complete_plan() -> None:
    stages = {stage.key: {stage.status_field: stage.accepted_value} for stage in _CHAIN}
    plan = plan_reddog_resident_queue_orchestration(
        _snapshot(), chain_results=stages, requested_queue_item_id=QUEUE_ID,
        now_iso="2026-07-14T00:00:00+00:00",
    )
    assert CONTROL_LOOP_RECEIPT_SCHEMA_VERSION == "reddog_resident_control_loop_receipt.v1"
    assert CHAIN_RESULTS_SCHEMA_VERSION == "reddog_resident_queue_chain_results.v1"
    assert plan.status == RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE
    assert len(plan.accepted_stages) == len(_CHAIN) + 1


def test_live_canary_production_files_and_functions_follow_wsp62() -> None:
    oversized_files = {
        path.name: len(path.read_text(encoding="utf-8").splitlines())
        for path in (*PRODUCTION_PATHS, *COMMUNICATION_TEST_PATHS)
        if len(path.read_text(encoding="utf-8").splitlines()) > 675
    }
    oversized_functions: dict[str, int] = {}
    for path in PRODUCTION_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.end_lineno:
                lines = node.end_lineno - node.lineno + 1
                if lines > 50:
                    oversized_functions[f"{path.name}:{node.name}"] = lines
    assert oversized_files == {}
    assert oversized_functions == {}
