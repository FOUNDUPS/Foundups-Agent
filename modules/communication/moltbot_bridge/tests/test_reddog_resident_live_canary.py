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
    append_resident_control_loop_receipt,
    build_resident_control_loop_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_resident_live_canary import (
    LIVE_CANARY_BLOCKED,
    LIVE_CANARY_CONFIRMATION,
    run_reddog_resident_live_canary,
    _read_json_mapping,
)
from modules.communication.moltbot_bridge.src.reddog_resident_live_canary_evidence import (
    read_control_receipts,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    CHAIN_RESULTS_SCHEMA_VERSION,
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
from modules.communication.moltbot_bridge.tests.test_reddog_resident_queue_serial_loop import (
    _snapshot,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_live_canary_test_support import (
    NOW,
    QUEUE_ID,
    _SIGNING_CONTEXT,
    _control_receipt,
    _execute,
    _kwargs,
    _roots,
    _runner,
    _write_pre_state,
    _write_control_receipt_and_head,
)


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
PRODUCTION_PATHS = (
    SRC_ROOT / "reddog_resident_live_canary.py",
    SRC_ROOT / "reddog_resident_live_canary_evidence.py",
    SRC_ROOT / "reddog_resident_queue_control_lock.py",
    SRC_ROOT / "reddog_resident_control_loop_receipt_auth.py",
    SRC_ROOT / "reddog_resident_control_loop_receipt_chain.py",
    SRC_ROOT / "reddog_resident_control_loop_receipt_store.py",
    SRC_ROOT / "reddog_resident_control_loop_receipt_validation.py",
    SRC_ROOT / "reddog_resident_control_loop_signing_context.py",
    SRC_ROOT / "reddog_resident_control_loop_head_store.py",
    SRC_ROOT / "reddog_resident_control_loop_chain_state.py",
    SRC_ROOT / "reddog_resident_control_loop_outcomes.py",
    SRC_ROOT / "reddog_resident_control_loop_effects.py",
    SRC_ROOT / "reddog_resident_live_canary_environment.py",
    SRC_ROOT / "reddog_resident_live_canary_control_preflight.py",
)
COMMUNICATION_TEST_PATHS = (
    Path(__file__),
    Path(__file__).with_name("reddog_resident_live_canary_test_support.py"),
    Path(__file__).with_name("test_reddog_resident_live_canary_integration.py"),
)
def test_readiness_is_non_executing_and_does_not_serialize_secret(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    receipt = run_reddog_resident_live_canary(**_kwargs(repo, runtime))

    assert receipt.status == LIVE_CANARY_BLOCKED
    assert receipt.ready_for_execution is False
    assert receipt.execution_invoked is False
    assert receipt.live_proof_complete is False
    assert "canonical_signed_runtime_artifact_manifest_producer_missing" in receipt.blockers
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

    assert receipt.status == LIVE_CANARY_BLOCKED
    assert receipt.execution_invoked is False
    assert "canonical_signed_runtime_artifact_manifest_producer_missing" in (
        receipt.blockers
    )


def test_runner_result_must_match_one_new_persisted_control_receipt(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    receipt = _execute(repo, runtime, result_receipt_id="different-receipt")

    assert receipt.live_proof_complete is False
    assert "canonical_signed_runtime_artifact_manifest_producer_missing" in receipt.blockers


def test_malformed_control_receipt_stream_blocks_before_runner(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    (runtime / "resident_queue_control_loop_receipts.jsonl").write_text(
        "{malformed}\n",
        encoding="utf-8",
    )
    called = False

    def runner(_: Path) -> dict[str, object]:
        nonlocal called
        called = True
        return {"accepted": True}

    receipt = run_reddog_resident_live_canary(
        **_kwargs(repo, runtime),
        execute=True,
        confirmation=LIVE_CANARY_CONFIRMATION,
        control_loop_runner=runner,
    )

    assert called is False
    assert receipt.live_proof_complete is False
    assert "control_receipt_stream_invalid" in receipt.blockers


def test_valid_json_signature_tamper_blocks_before_runner(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    _write_pre_state(repo, runtime)
    control = _control_receipt(repo)
    _write_control_receipt_and_head(runtime, control)
    control["status"] = "TAMPERED"
    (runtime / "resident_queue_control_loop_receipts.jsonl").write_text(
        json.dumps(control) + "\n", encoding="utf-8"
    )
    called = False

    def runner(_: Path) -> dict[str, object]:
        nonlocal called
        called = True
        return {"accepted": True}

    receipt = run_reddog_resident_live_canary(
        **_kwargs(repo, runtime), execute=True,
        confirmation=LIVE_CANARY_CONFIRMATION, control_loop_runner=runner,
    )
    assert called is False
    assert receipt.live_proof_complete is False


def test_canary_blocks_when_signer_anchor_is_ahead_of_resident_chain(
    tmp_path: Path,
) -> None:
    from modules.communication.moltbot_bridge.src.reddog_signer_control_loop_anchor import (
        AtomicSignerControlLoopAnchorStore,
    )

    repo, runtime = _roots(tmp_path)
    first = _control_receipt(repo)
    _write_control_receipt_and_head(runtime, first)
    second = build_resident_control_loop_receipt(
        result={
            "accepted": True,
            "status": "PASS",
            "rounds": 1,
            "serial_progress": 1,
            "claim_progress": 0,
            "control_lock_acquired": True,
            "receipt_ids": (),
            "rejection_reasons": (),
        },
        repo_root=repo,
        created_at="2026-07-14T00:00:01Z",
        sequence_number=2,
        previous_receipt_id=str(first["receipt_id"]),
        cycle_id="canary-cycle-2",
        nonce="canary-nonce-2",
        signing_context=_SIGNING_CONTEXT,
    ).to_dict()
    config = json.loads(
        (runtime / "signer_service_config.json").read_text(encoding="utf-8")
    )
    store = AtomicSignerControlLoopAnchorStore(config["control_loop_anchor_path"])
    state = store.load()
    unsigned = {
        key: value
        for key, value in second.items()
        if key
        not in {
            "signature",
            "signer_audit_mac",
            "signer_audit_attestation_signature",
        }
    }
    response = {
        "signature": second["signature"],
        "audit_mac": second["signer_audit_mac"],
        "audit_attestation_signature": second[
            "signer_audit_attestation_signature"
        ],
    }
    prepared = store.prepare(unsigned)
    store.commit(
        unsigned, response, expected_revision=prepared.expected_revision
    )
    assert state["receipt_id"] == first["receipt_id"]

    receipt = run_reddog_resident_live_canary(**_kwargs(repo, runtime))
    assert receipt.status == LIVE_CANARY_BLOCKED
    assert "control_receipt_prestate_auth_or_integrity_invalid" in (
        receipt.blockers
    )
    assert "control_receipt_prestate_auth_or_integrity_invalid" in receipt.blockers


def test_signed_chain_suffix_truncation_blocks_before_runner(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    _write_pre_state(repo, runtime)
    path = runtime / "resident_queue_control_loop_receipts.jsonl"
    base_result = {
        "accepted": True, "status": "PASS", "rounds": 1,
        "serial_progress": 1, "claim_progress": 0, "receipt_ids": (),
        "child_execution_receipt_ids": (),
        "child_execution_evidence_digests": (), "child_execution_outcomes": (),
        "rejection_reasons": (), "control_lock_acquired": True,
        "dispatched_stages": (),
    }
    for index in (1, 2):
        append_resident_control_loop_receipt(
            path=path, result=base_result, repo_root=repo,
            created_at=f"2026-07-14T00:00:0{index}Z",
            cycle_id=f"truncate-cycle-{index}", nonce=f"truncate-nonce-{index}",
            signing_context=_SIGNING_CONTEXT, require_authentication=True,
            head_state_path=runtime / "authority_runtime_state.json",
        )
    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    path.write_text(first_line + "\n", encoding="utf-8")
    called = False

    def runner(_: Path) -> dict[str, object]:
        nonlocal called
        called = True
        return {"accepted": True}

    receipt = run_reddog_resident_live_canary(
        **_kwargs(repo, runtime), execute=True,
        confirmation=LIVE_CANARY_CONFIRMATION, control_loop_runner=runner,
    )
    assert called is False
    assert receipt.live_proof_complete is False
    assert "control_receipt_prestate_auth_or_integrity_invalid" in receipt.blockers


def test_head_consumed_evidence_tamper_blocks_before_runner(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    _write_pre_state(repo, runtime)
    control = _control_receipt(repo)
    _write_control_receipt_and_head(runtime, control)
    state_path = runtime / "authority_runtime_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["control_receipt_head"]["consumed_child_evidence_digests"] = [
        "sha256:" + "f" * 64
    ]
    state_path.write_text(json.dumps(state), encoding="utf-8")
    called = False

    def runner(_: Path) -> dict[str, object]:
        nonlocal called
        called = True
        return {"accepted": True}

    receipt = run_reddog_resident_live_canary(
        **_kwargs(repo, runtime),
        execute=True,
        confirmation=LIVE_CANARY_CONFIRMATION,
        control_loop_runner=runner,
    )

    assert called is False
    assert "control_receipt_prestate_auth_or_integrity_invalid" in receipt.blockers


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
    assert "control_receipt_prestate_auth_or_integrity_invalid" in receipt.blockers


def test_canary_rejects_control_receipt_stream_replacement(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    _write_pre_state(repo, runtime)

    def control(cycle: str, nonce: str) -> dict[str, object]:
        return build_resident_control_loop_receipt(
            result={
                "accepted": True,
                "status": "PASS",
                "rounds": 1,
                "serial_progress": 1,
                "claim_progress": 0,
                "receipt_ids": (),
                "rejection_reasons": (),
                "control_lock_acquired": True,
                "dispatched_stages": (),
            },
            repo_root=repo,
            created_at=NOW,
            cycle_id=cycle,
            nonce=nonce,
            signing_context=_SIGNING_CONTEXT,
        ).to_dict()

    original = control("canary-prefix-cycle", "canary-prefix-nonce")
    replacement = control("canary-replacement-cycle", "canary-replacement-nonce")
    path = runtime / "resident_queue_control_loop_receipts.jsonl"
    _write_control_receipt_and_head(runtime, original)

    def runner(_: Path) -> dict[str, object]:
        path.write_text(json.dumps(replacement) + "\n", encoding="utf-8")
        return {
            "accepted": True,
            "status": "PASS",
            "receipt_id": replacement["receipt_id"],
        }

    receipt = run_reddog_resident_live_canary(
        **_kwargs(repo, runtime), execute=True,
        confirmation=LIVE_CANARY_CONFIRMATION, queue_item_id=QUEUE_ID,
        control_loop_runner=runner,
        now=lambda: __import__("datetime").datetime.fromisoformat(NOW),
    )

    assert receipt.execution_invoked is False
    assert "canonical_signed_runtime_artifact_manifest_producer_missing" in (
        receipt.blockers
    )


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
    assert "canonical_signed_runtime_artifact_manifest_producer_missing" in receipt.blockers


def test_receipt_path_allows_only_canonical_name_inside_runtime(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    canonical = runtime / "live_canary_receipt.json"
    receipt = run_reddog_resident_live_canary(
        **_kwargs(repo, runtime), receipt_path=canonical
    )
    assert receipt.status == LIVE_CANARY_BLOCKED
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
    assert receipt.status == LIVE_CANARY_BLOCKED
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


def test_canary_and_evidence_reads_reject_linked_parent(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "artifact.json").write_text("{}", encoding="utf-8")
    (target / "receipts.jsonl").write_text("{}\n", encoding="utf-8")
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    assert _read_json_mapping(
        linked / "artifact.json", allowed_root=tmp_path
    ) == {}
    assert read_control_receipts(
        linked / "receipts.jsonl", allowed_root=tmp_path
    ) == ()


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
        from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
            claim_reddog_signed_worker_dispatch_tasks_until_idle,
        )

        with patch.dict(
            os.environ,
            {CONTROL_LOOP_LOCK_PATH_ENV: str(lock_path)},
            clear=False,
        ):
            result = claim_reddog_signed_worker_dispatch_tasks_until_idle(
                repo_root=repo,
                agent_db_factory=lambda: pytest.fail("AgentDB must not be opened"),
            )
        assert result["accepted"] is False
        assert "control_loop_already_running" in result["rejection_reasons"]
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
    assert CONTROL_LOOP_RECEIPT_SCHEMA_VERSION == "reddog_resident_control_loop_receipt.v2"
    assert CHAIN_RESULTS_SCHEMA_VERSION == "reddog_resident_queue_chain_results.v1"
    assert plan.status == RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE
    assert len(plan.accepted_stages) == len(_CHAIN) + 1


def test_live_canary_production_files_and_functions_follow_wsp62() -> None:
    exact_exemptions = {
        SRC_ROOT / "reddog_resident_live_canary.py",
    }
    oversized_files = {
        path.name: len(path.read_text(encoding="utf-8").splitlines())
        for path in (*PRODUCTION_PATHS, *COMMUNICATION_TEST_PATHS)
        if path not in exact_exemptions
        and len(path.read_text(encoding="utf-8").splitlines()) > 675
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


def test_modified_control_receipt_helpers_follow_wsp62() -> None:
    targets = {
        Path(__file__).resolve().parents[4] / "main.py": {
            "_reddog_record_queue_control_result",
            "_reddog_persist_queue_control_receipt",
            "_reddog_control_receipt_signer_limits",
            "_reddog_queue_stage_child_execution_outcomes",
            "run_reddog_resident_queue_control_loop_preflight",
            "_reddog_run_bounded_control_rounds",
            "_reddog_run_control_round",
            "run_reddog_openclaw_signed_worker_claim_loop_preflight",
        },
        SRC_ROOT / "openclaw_supervisor.py": {
            "_claim_reddog_signed_worker_dispatch_task_once_under_control_lock",
            "_claim_reddog_signed_worker_dispatch_tasks_until_idle_under_control_lock",
            "_signed_worker_claim_result",
            "_signed_worker_claim_loop_result",
            "_signed_worker_effect_attestations",
            "_signed_worker_loop_evidence",
            "_signed_worker_child_execution_outcomes",
            "_persist_reddog_signed_worker_dispatch_task_result",
        },
        SRC_ROOT / "reddog_ed25519_signer_backend.py": {
            "_valid_control_receipt_signing_payload",
            "_control_authority_policy_matches",
            "sign",
        },
        SRC_ROOT / "reddog_signed_worker_dispatch_task_executor.py": {
            "execute_reddog_signed_worker_dispatch_task",
            "_validated_worker_context",
            "_invoke_signed_worker_runner",
            "_accepted_execution_result",
        },
    }
    oversized = {}
    for path, names in targets.items():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
                lines = int(node.end_lineno or node.lineno) - node.lineno + 1
                if lines > 50:
                    oversized[f"{path.name}:{node.name}"] = lines
    assert oversized == {}
    bounded_modules = (
        SRC_ROOT / "reddog_authority_runtime_store.py",
    )
    assert {
        path.name: len(path.read_text(encoding="utf-8").splitlines())
        for path in bounded_modules
        if len(path.read_text(encoding="utf-8").splitlines()) > 675
    } == {}
