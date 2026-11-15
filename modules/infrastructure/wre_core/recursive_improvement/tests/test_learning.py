# -*- coding: utf-8 -*-
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
    build_reddog_verified_pattern_memory_sink,
    reddog_verified_pattern_memory_record_id,
)
from modules.communication.moltbot_bridge.src.reddog_work_authority_digest import (
    canonical_work_authority_digest,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_held_out_regression_gate_invoke import (
    QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT,
    invoke_reddog_wre_queue_authorized_held_out_regression_gate,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_pattern_memory_admission_invoke import (
    QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT,
    QueueAuthorizedPatternMemoryAdmissionInvokeReason,
    invoke_reddog_wre_queue_authorized_pattern_memory_admission,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_outcome_ratchet_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT,
)
from modules.infrastructure.wre_core.recursive_improvement.src.core import Improvement
from modules.infrastructure.wre_core.recursive_improvement.src.learning import (
    RecursiveLearningEngine,
    process_error,
)
from modules.infrastructure.wre_core.skillz.wre_skills_loader import WRESkillsLoader
from modules.infrastructure.wre_core.src.reddog_direction import (
    AdvanceOutcome,
    RedDogDirector,
)
from modules.infrastructure.wre_core.src.reddog_held_out_recursive_improvement_regression_gate import (
    HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT,
    HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_REJECT,
    evaluate_held_out_recursive_improvement_regression_gate,
)
from modules.infrastructure.wre_core.src.reddog_verified_draft_pr_publish import (
    VERIFIED_DRAFT_PR_PUBLISH_ACCEPT,
)
from modules.infrastructure.wre_core.src.reddog_verified_outcome_ratchet import (
    OUTCOME_RATCHET_RECORDED,
    InMemoryOutcomeRatchetStore,
    ratchet_verified_outcome,
)
from modules.infrastructure.wre_core.src.skill_runtime_admission import (
    admit_runtime_skill,
)
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
    verify_autonomous_slice_runtime,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
BASE_SHA = "b" * 40
HEAD_SHA = "a" * 40
PILOT_PATH = "modules/communication/moltbot_bridge/tests/fixtures/reddog_pilot/README.md"

# === UTF-8 ENFORCEMENT (WSP 90) ===
# Prevent UnicodeEncodeError on Windows systems
# Only apply when running as main script, not during import
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        pass  # UTF-8 wrapping handled by entrypoint (WSP 90)
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===


def _digest(ch: str) -> str:
    return "sha256:" + ch * 64


def _isolated_engine(tmp_path: Path) -> RecursiveLearningEngine:
    engine = RecursiveLearningEngine.__new__(RecursiveLearningEngine)
    engine.project_root = tmp_path
    engine.memory_root = tmp_path / "memory"
    engine.memory_root.mkdir(parents=True, exist_ok=True)
    engine.error_patterns = {}
    engine.solutions = {}
    engine.improvements = {}
    engine.metrics = {
        "errors_processed": 0,
        "patterns_extracted": 0,
        "solutions_generated": 0,
        "improvements_applied": 0,
        "tokens_saved": None,
        "total_tokens_saved": 0,
        "token_reduction_measured": False,
        "learning_velocity": 0.1,
    }
    return engine


def _synthetic_valid_evidence() -> Dict[str, Any]:
    return {
        "verification_result": {
            "accepted": True,
            "decision": AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
            "receipt": {
                "receipt_id": "wre_slice_verify_test_1",
                "work_order_id": "wo-rsi-test-1",
                "worker_id": "worker:author-1",
                "verifier_id": "worker:verifier-1",
                "head_sha": HEAD_SHA,
            },
        },
        "ratchet_result": {
            "accepted": True,
            "decision": OUTCOME_RATCHET_RECORDED,
            "receipt": {
                "ratchet_id": "outcome_ratchet_test_1",
                "verifier_receipt_id": "wre_slice_verify_test_1",
                "work_order_id": "wo-rsi-test-1",
            },
        },
        "held_out_gate_result": {
            "accepted": True,
            "decision": HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT,
            "receipt": {
                "gate_id": "held_out_recursive_gate_test_1",
                "ratchet_id": "outcome_ratchet_test_1",
                "verifier_receipt_id": "wre_slice_verify_test_1",
                "pattern_memory_admission_allowed": True,
            },
        },
    }


@pytest.mark.asyncio
async def test_process_error():
    engine = RecursiveLearningEngine()
    error = ValueError("Test WSP violation")
    improvement = await process_error(error)
    assert isinstance(improvement, Improvement)
    assert improvement.pattern_id is not None
    assert improvement.solution_id is not None


@pytest.mark.asyncio
async def test_apply_improvement_legacy_unauthenticated_fails_closed(tmp_path: Path):
    engine = _isolated_engine(tmp_path)
    improvement = Improvement(
        improvement_id="imp-legacy-unauth-1",
        pattern_id="pat-1",
        solution_id="sol-1",
        target="modules/x/y/README.md",
        change_type="update",
        before_state="before",
        after_state="after",
    )

    applied = await engine.apply_improvement(improvement)

    assert applied is False
    assert improvement.applied is False
    assert improvement.applied_at is None
    assert improvement.metrics["application_status"] == "blocked_unimplemented"
    assert engine.metrics["improvements_applied"] == 0
    assert engine.metrics["tokens_saved"] is None
    assert engine.metrics["token_reduction_measured"] is False
    persisted = json.loads(
        (
            engine.memory_root
            / "improvements"
            / improvement.change_type
            / f"{improvement.improvement_id}.json"
        ).read_text(encoding="utf-8")
    )
    assert persisted["applied"] is False
    assert persisted["metrics"]["application_status"] == "blocked_unimplemented"


@pytest.mark.asyncio
async def test_apply_improvement_rejects_self_verified_or_rejected_gate(tmp_path: Path):
    engine = _isolated_engine(tmp_path)
    calls = 0

    def _applicator(before_state: str, after_state: str):
        nonlocal calls
        calls += 1
        return after_state, lambda: before_state

    self_verified = _synthetic_valid_evidence()
    self_verified["verification_result"]["receipt"]["verifier_id"] = "worker:author-1"
    imp_self = Improvement(
        improvement_id="imp-reject-self",
        pattern_id="pat-1",
        solution_id="sol-1",
        target="modules/x/y/README.md",
        change_type="update",
        before_state="before-1",
        after_state="after-1",
    )
    assert (
        await engine.apply_improvement(
            imp_self,
            verification_evidence=self_verified,
            target_applicator=_applicator,
        )
        is False
    )
    assert calls == 0
    assert imp_self.applied is False
    assert imp_self.applied_at is None
    assert imp_self.metrics["application_status"] == "blocked_verification_rejected"

    rejected_gate = _synthetic_valid_evidence()
    rejected_gate["held_out_gate_result"]["accepted"] = False
    rejected_gate["held_out_gate_result"]["decision"] = (
        HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_REJECT
    )
    rejected_gate["held_out_gate_result"]["receipt"]["pattern_memory_admission_allowed"] = False
    imp_gate = Improvement(
        improvement_id="imp-reject-gate",
        pattern_id="pat-1",
        solution_id="sol-1",
        target="modules/x/y/README.md",
        change_type="update",
        before_state="before-2",
        after_state="after-2",
    )
    assert (
        await engine.apply_improvement(
            imp_gate,
            verification_evidence=rejected_gate,
            target_applicator=_applicator,
        )
        is False
    )
    assert calls == 0
    assert imp_gate.applied is False
    assert imp_gate.applied_at is None
    assert imp_gate.metrics["application_status"] == "blocked_verification_rejected"

    imp_no_op = Improvement(
        improvement_id="imp-reject-noop",
        pattern_id="pat-1",
        solution_id="sol-1",
        target="modules/x/y/README.md",
        change_type="update",
        before_state="unchanged",
        after_state="unchanged",
    )
    assert (
        await engine.apply_improvement(
            imp_no_op,
            verification_evidence=_synthetic_valid_evidence(),
            target_applicator=lambda b, _a: (b, lambda: b),
        )
        is False
    )
    assert imp_no_op.applied is False
    assert imp_no_op.metrics["application_status"] == "blocked_verification_rejected"
    assert engine.metrics["improvements_applied"] == 0


@pytest.mark.asyncio
async def test_bounded_rsi_cycle_end_to_end_apply_and_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    assert (REPO_ROOT / "modules").is_dir()

    # Ensure isolated git worktrees locate the active interpreter's skill-scanner binary,
    # or fall back to live manifest verification on hosted CI runners where the dev-only
    # cisco-ai-skill-scanner CLI is omitted from requirements.txt.
    if shutil.which("skill-scanner") is None:
        exe_name = "skill-scanner.exe" if sys.platform.startswith("win") else "skill-scanner"
        candidate_scanner = Path(sys.executable).resolve().parent / exe_name
        if candidate_scanner.is_file():
            monkeypatch.setenv("OPENCLAW_SKILL_SCANNER_BIN", str(candidate_scanner))
        else:
            from modules.communication.moltbot_bridge.src.skill_safety_guard import (
                SkillScanResult,
            )
            from modules.infrastructure.wre_core.src import (
                skill_runtime_admission as admission_mod,
            )
            from modules.infrastructure.wre_core.src.skill_manifest_guard import (
                verify_skill_manifest,
            )

            def _manifest_verified_ci_scan(*, skills_dir: Path, **_kwargs) -> SkillScanResult:
                manifest = verify_skill_manifest(
                    skills_dir=skills_dir,
                    manifest_path=skills_dir / "SKILL_MANIFEST.json",
                    required=True,
                )
                return SkillScanResult(
                    available=True,
                    passed=manifest.passed,
                    exit_code=0 if manifest.passed else 3,
                    skills_dir=str(skills_dir),
                    report_path=None,
                    message="skills passed safety scan" if manifest.passed else manifest.message,
                    manifest_available=manifest.available,
                    manifest_passed=manifest.passed,
                    manifest_path=manifest.manifest_path,
                    manifest_message=manifest.message,
                )

            monkeypatch.setattr(admission_mod, "SKILL_SCANNER_AVAILABLE", True)
            monkeypatch.setattr(admission_mod, "run_skill_scan", _manifest_verified_ci_scan)

    # 1. Observe -> Propose -> Direct (remains dry-run and fail-closed on execution).
    director = RedDogDirector()
    proposals = director.observe_propose_direct(
        [
            {
                "type": "doc_stale",
                "severity": "low",
                "file_path": PILOT_PATH,
                "message": "Bounded pilot documentation refresh",
            }
        ]
    )
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.job.dry_run is True
    advance = director.advance_to_execution(proposal)
    assert advance.advanced is False
    assert advance.outcome == AdvanceOutcome.BLOCKED

    # 2. Admit production runtime skill through the live manifest + scanner gate.
    #    max_severity="high" allows Cisco's SKILLz.md FILE_MAGIC_MISMATCH (MEDIUM)
    #    heuristic while blocking any HIGH/CRITICAL supply-chain finding.
    loader = WRESkillsLoader(repo_root=REPO_ROOT)
    admitted, _admission_msg, skill_fingerprint = admit_runtime_skill(
        skills_loader=loader,
        skill_name="auto_test_registry_audit",
        repo_root=REPO_ROOT,
        cache={},
        required=True,
        enforced=True,
        always_scan=True,
        ttl_seconds=900,
        max_severity="high",
    )
    assert admitted is True
    assert isinstance(skill_fingerprint, str) and len(skill_fingerprint) == 64

    # 3. Verify bounded autonomous slice via independent non-author verifier.
    work_order_id = f"wo-{proposal.job.job_id}"
    slice_name = "WRE_RSI_BOUNDED_END_TO_END_SLICE"
    signed_authority_payload: Dict[str, Any] = {
        "authority_id": "authority-rsi-e2e-1",
        "work_order_id": work_order_id,
    }
    signed_authority_digest = canonical_work_authority_digest(signed_authority_payload)
    verify_request = {
        "work_order_id": work_order_id,
        "slice_name": slice_name,
        "worker_id": "worker:author-0102",
        "verifier_id": "worker:verifier-0102",
        "assurance_reservation_id": "assurance-reservation-" + "1" * 20,
        "assurance_reservation_digest": _digest("0"),
        "verifier_task_id": "reddog-worker-dispatch-" + "2" * 16,
        "base_sha": BASE_SHA,
        "head_sha": HEAD_SHA,
        "allowed_path_patterns": [
            "modules/communication/moltbot_bridge/tests/fixtures/reddog_pilot/**"
        ],
        "expected_changed_paths": [PILOT_PATH],
        "forbidden_path_patterns": ["**/.env", "**/secrets/**"],
        "diff_evidence": {
            "source": "machine_derived",
            "red_dog_prose_source": False,
            "base_sha": BASE_SHA,
            "head_sha": HEAD_SHA,
            "diff_digest": _digest("1"),
            "changed_paths": [PILOT_PATH],
            "added_lines": ["bounded pilot fixture update"],
        },
        "test_evidence": {
            "head_sha": HEAD_SHA,
            "test_evidence_digest": _digest("2"),
            "required_checks": [
                {"name": "pytest", "head_sha": HEAD_SHA, "conclusion": "success"},
                {"name": "security", "head_sha": HEAD_SHA, "conclusion": "pass"},
            ],
        },
        "signed_authority": {
            "accepted": True,
            **signed_authority_payload,
            "signature_gate_digest": signed_authority_digest,
        },
        "signed_receipt_chain": {
            "accepted": True,
            "terminal_receipt_hash": _digest("4"),
        },
        "worktree_receipt": {
            "accepted": True,
            "receipt_digest": _digest("5"),
        },
        "bounded_worker_pilot_receipt": {
            "accepted": True,
            "receipt_id": "bounded_wt_pilot_rsi_e2e",
        },
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": _digest("6"),
        },
        "pattern_memory_write_performed": False,
        "draft_pr_published": False,
        "merge_performed": False,
    }
    verification_result = verify_autonomous_slice_runtime(
        verify_request,
        trusted_work_authority_digest=signed_authority_digest,
    )
    assert verification_result.accepted is True
    assert verification_result.decision == AUTONOMOUS_SLICE_VERIFIER_ACCEPT

    # 4. Record verified outcome in ratchet (fail-closed against pattern memory write).
    holoindex_evidence = {
        "index_gap_detected": False,
        "holoindex_freshness_receipt_digest": _digest("6"),
    }
    ratchet_store = InMemoryOutcomeRatchetStore()
    ratchet_request = {
        "work_order_id": work_order_id,
        "slice_name": slice_name,
        "outcome_status": "accepted",
        "request_receipt": {"request_id": proposal.job.job_id},
        "execution_receipts": [{"receipt_id": f"skill_admit_{skill_fingerprint[:12]}"}],
        "verification_result": verification_result.to_dict(),
        "publish_result": {
            "accepted": True,
            "decision": VERIFIED_DRAFT_PR_PUBLISH_ACCEPT,
            "receipt": {
                "receipt_id": "verified-draft-pr-rsi-e2e",
                "work_order_id": work_order_id,
                "slice_name": slice_name,
                "verifier_receipt_id": verification_result.receipt.receipt_id,
            },
        },
        "cost_receipt": {"total_tokens": 120, "estimated_cost_usd": 0.01},
        "latency_receipt": {"wall_time_ms": 25, "queue_time_ms": 5},
        "acceptance_receipt": {"accepted": True},
        "failure_receipt": None,
        "holoindex_evidence": holoindex_evidence,
    }
    ratchet_result = ratchet_verified_outcome(ratchet_request, store=ratchet_store)
    assert ratchet_result.accepted is True
    assert ratchet_result.decision == OUTCOME_RATCHET_RECORDED
    assert ratchet_result.receipt.verifier_receipt_id == verification_result.receipt.receipt_id
    assert ratchet_result.receipt.pattern_memory_write_performed is False

    # 5. Evaluate independent held-out regression gate.
    gate_request = {
        "work_order_id": work_order_id,
        "slice_name": slice_name,
        "worker_id": "worker:author-0102",
        "enable_pattern_memory_admission": True,
        "improvement_job": {
            "job_id": proposal.job.job_id,
            "finding_id": proposal.job.finding_id,
            "improvement_type": proposal.job.improvement_type.value,
            "status": proposal.job.status.value,
            "dry_run": proposal.job.dry_run,
        },
        "verification_result": verification_result.to_dict(),
        "ratchet_result": ratchet_result.to_dict(),
        "held_out_regression": {
            "suite_id": "heldout-wre-recursive-e2e-001",
            "is_held_out": True,
            "independent": True,
            "generated_by_author": False,
            "evidence_author_id": "worker:verifier-0102",
            "passed": True,
            "test_count": 12,
            "failure_count": 0,
            "suite_digest": _digest("7"),
            "baseline_digest": _digest("8"),
            "candidate_digest": _digest("9"),
            "candidate_head_sha": HEAD_SHA,
        },
        "holoindex_evidence": holoindex_evidence,
    }
    gate_result = evaluate_held_out_recursive_improvement_regression_gate(gate_request)
    assert gate_result.accepted is True
    assert gate_result.decision == HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT
    assert gate_result.receipt.pattern_memory_admission_allowed is True

    # 6. Pattern memory staging succeeds while active write remains fail-closed.
    sink = build_reddog_verified_pattern_memory_sink(
        repo_root=REPO_ROOT,
        db_path=tmp_path / "runtime" / "pattern_memory.db",
    )
    assert sink is not None
    staging_record = {
        "record_type": "reddog_verified_recursive_improvement_outcome",
        "work_order_id": work_order_id,
        "slice_name": slice_name,
        "gate_id": gate_result.receipt.gate_id,
        "ratchet_id": ratchet_result.receipt.ratchet_id,
        "verifier_receipt_id": verification_result.receipt.receipt_id,
        "improvement_job_id": gate_result.receipt.improvement_job_id,
        "held_out_suite_id": gate_result.receipt.held_out_suite_id,
        "candidate_head_sha": gate_result.receipt.candidate_head_sha,
        "regression_test_count": gate_result.receipt.regression_test_count,
        "pattern_memory_admission_allowed": True,
    }
    staged_id = sink.stage_verified_outcome(staging_record)
    assert staged_id == reddog_verified_pattern_memory_record_id(staging_record)
    assert sink.load_verified_outcome(staged_id) is None
    with pytest.raises(ValueError, match="verified_outcome_activation_capability_required"):
        sink.store_verified_outcome(staging_record)

    queue_gate_invoke = invoke_reddog_wre_queue_authorized_held_out_regression_gate(
        explicit_queue_authorized_held_out_regression_gate_requested=True,
        queue_verified_outcome_ratchet_result={
            "decision": QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT,
            "ratchet_result": ratchet_result.to_dict(),
        },
        held_out_gate_request=gate_request,
    )
    assert queue_gate_invoke.decision == QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT
    assert queue_gate_invoke.gate_result is not None

    admission_refusal = invoke_reddog_wre_queue_authorized_pattern_memory_admission(
        explicit_queue_authorized_pattern_memory_admission_requested=True,
        queue_held_out_gate_result={
            "decision": queue_gate_invoke.decision,
            "gate_result": queue_gate_invoke.gate_result.to_dict(),
        },
        admission_request={"work_order_id": work_order_id},
        sink=sink,
    )
    assert (
        admission_refusal.decision
        == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
    )
    assert (
        QueueAuthorizedPatternMemoryAdmissionInvokeReason.SINK_WRITE_FAILED
        in admission_refusal.rejection_reasons
    )
    assert admission_refusal.pattern_memory_write_performed is False

    class _AuthorizedRecordingSink:
        def __init__(self) -> None:
            self.records: list[dict[str, Any]] = []

        def store_verified_outcome(self, record: dict[str, Any]) -> str:
            self.records.append(dict(record))
            return reddog_verified_pattern_memory_record_id(record)

    recording_sink = _AuthorizedRecordingSink()
    admission_accept = invoke_reddog_wre_queue_authorized_pattern_memory_admission(
        explicit_queue_authorized_pattern_memory_admission_requested=True,
        queue_held_out_gate_result={
            "decision": queue_gate_invoke.decision,
            "gate_result": queue_gate_invoke.gate_result.to_dict(),
        },
        admission_request={"work_order_id": work_order_id},
        sink=recording_sink,
    )
    assert (
        admission_accept.decision
        == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT
    )
    assert admission_accept.pattern_memory_write_performed is True
    assert len(recording_sink.records) == 1

    # 7. Verified application + deterministic rollback on isolated RecursiveLearningEngine.
    engine = _isolated_engine(tmp_path)
    target_file = tmp_path / "target_artifact.md"
    before_text = "# Pilot Doc\nstatus: stale\n"
    after_text = "# Pilot Doc\nstatus: refreshed\n"
    target_file.write_text(before_text, encoding="utf-8")

    improvement = Improvement(
        improvement_id=f"imp-{proposal.job.job_id}",
        pattern_id="pat-rsi-e2e",
        solution_id="sol-rsi-e2e",
        target=str(target_file),
        change_type="update",
        before_state=before_text,
        after_state=after_text,
    )

    def _target_applicator(before_state: str, desired_after_state: str):
        target_file.write_text(desired_after_state, encoding="utf-8")

        def _rollback() -> str:
            target_file.write_text(before_state, encoding="utf-8")
            return target_file.read_text(encoding="utf-8")

        return target_file.read_text(encoding="utf-8"), _rollback

    evidence = {
        "verification_result": verification_result,
        "ratchet_result": ratchet_result,
        "held_out_gate_result": gate_result,
    }
    applied = await engine.apply_improvement(
        improvement,
        verification_evidence=evidence,
        target_applicator=_target_applicator,
    )
    expected_before_digest = hashlib.sha256(before_text.encode("utf-8")).hexdigest()
    expected_after_digest = hashlib.sha256(after_text.encode("utf-8")).hexdigest()

    assert applied is True
    assert target_file.read_text(encoding="utf-8") == after_text
    assert improvement.applied is True
    assert isinstance(improvement.applied_at, str) and bool(improvement.applied_at)
    assert improvement.after_state == after_text
    assert improvement.rollback_available is True
    assert improvement.metrics["application_status"] == "applied_verified"
    assert improvement.metrics["verifier_receipt_id"] == verification_result.receipt.receipt_id
    assert improvement.metrics["ratchet_id"] == ratchet_result.receipt.ratchet_id
    assert improvement.metrics["gate_id"] == gate_result.receipt.gate_id
    assert improvement.metrics["before_state_digest"] == f"sha256:{expected_before_digest}"
    assert improvement.metrics["after_state_digest"] == f"sha256:{expected_after_digest}"
    assert improvement.metrics["rollback_available"] is True
    assert engine.metrics["improvements_applied"] == 1
    assert engine.metrics["tokens_saved"] is None
    assert engine.metrics["token_reduction_measured"] is False

    rolled_back = await engine.rollback_improvement(improvement)
    assert rolled_back is True
    assert target_file.read_text(encoding="utf-8") == before_text
    assert improvement.applied is False
    assert improvement.after_state == before_text
    assert improvement.rollback_available is False
    assert improvement.metrics["application_status"] == "rolled_back"
    assert isinstance(improvement.metrics["rolled_back_at"], str)
    assert improvement.metrics["rollback_verified"] is True
    assert improvement.metrics["rollback_available"] is False
    assert engine.metrics["improvements_applied"] == 0
    assert await engine.rollback_improvement(improvement) is False


@pytest.mark.asyncio
async def test_apply_improvement_unmeasured_preserves_none_tokens_saved(tmp_path: Path):
    engine = _isolated_engine(tmp_path)
    before_text = "alpha\n"
    after_text = "beta\n"
    imp = Improvement(
        improvement_id="imp-unmeasured-1",
        pattern_id="pat-1",
        solution_id="sol-1",
        target="modules/x/y/README.md",
        change_type="update",
        before_state=before_text,
        after_state=after_text,
    )

    applied = await engine.apply_improvement(
        imp,
        verification_evidence=_synthetic_valid_evidence(),
        target_applicator=lambda b, a: (a, lambda: b),
        measurement_evidence=None,
    )

    assert applied is True
    assert imp.tokens_saved is None
    assert imp.metrics["token_reduction_measured"] is False
    assert engine.metrics["tokens_saved"] is None
    assert engine.metrics["total_tokens_saved"] == 0


@pytest.mark.asyncio
async def test_apply_and_rollback_measured_benefit_tracks_and_subtracts_tokens_saved(
    tmp_path: Path,
):
    engine = _isolated_engine(tmp_path)
    engine.metrics.pop("total_tokens_saved", None)  # verify safe default initialization

    file_one = tmp_path / "one.md"
    before_one = "state: baseline-1\n"
    after_one = "state: improved-1\n"
    file_one.write_text(before_one, encoding="utf-8")

    def _make_file_applicator(path: Path):
        def _apply(before_state: str, desired_after_state: str):
            path.write_text(desired_after_state, encoding="utf-8")

            def _rollback() -> str:
                path.write_text(before_state, encoding="utf-8")
                return path.read_text(encoding="utf-8")

            return path.read_text(encoding="utf-8"), _rollback

        return _apply

    imp1 = Improvement(
        improvement_id="imp-measured-1",
        pattern_id="pat-1",
        solution_id="sol-1",
        target=str(file_one),
        change_type="update",
        before_state=before_one,
        after_state=after_one,
    )
    before_one_hex = hashlib.sha256(before_one.encode("utf-8")).hexdigest()
    after_one_hex = hashlib.sha256(after_one.encode("utf-8")).hexdigest()

    applied_one = await engine.apply_improvement(
        imp1,
        verification_evidence=_synthetic_valid_evidence(),
        target_applicator=_make_file_applicator(file_one),
        measurement_evidence={
            "measurement_receipt_id": "meas-rcpt-001",
            "evaluator_id": "worker:bench-evaluator-1",
            "work_order_id": "wo-rsi-test-1",
            "baseline_tokens": 1200,
            "candidate_tokens": 750,
            "before_state_digest": f"sha256:{before_one_hex}",
            "after_state_digest": f"sha256:{after_one_hex}",
            "baseline_latency_ms": 420.5,
            "candidate_latency_ms": 310.0,
        },
    )

    assert applied_one is True
    assert imp1.applied is True
    assert imp1.tokens_saved == 450
    assert imp1.metrics["token_reduction_measured"] is True
    assert imp1.metrics["measurement_receipt_id"] == "meas-rcpt-001"
    assert imp1.metrics["evaluator_id"] == "worker:bench-evaluator-1"
    assert imp1.metrics["baseline_tokens"] == 1200
    assert imp1.metrics["candidate_tokens"] == 750
    assert imp1.metrics["baseline_latency_ms"] == 420.5
    assert imp1.metrics["candidate_latency_ms"] == 310.0
    assert imp1.metrics["latency_ms_saved"] == pytest.approx(110.5)
    assert engine.metrics["total_tokens_saved"] == 450

    persisted_one = json.loads(
        (
            engine.memory_root
            / "improvements"
            / imp1.change_type
            / f"{imp1.improvement_id}.json"
        ).read_text(encoding="utf-8")
    )
    restored_imp1 = Improvement.from_dict(persisted_one)
    assert restored_imp1.tokens_saved == 450
    assert restored_imp1.metrics["token_reduction_measured"] is True

    file_two = tmp_path / "two.md"
    before_two = "state: baseline-2\n"
    after_two = "state: improved-2\n"
    file_two.write_text(before_two, encoding="utf-8")
    imp2 = Improvement(
        improvement_id="imp-measured-2",
        pattern_id="pat-2",
        solution_id="sol-2",
        target=str(file_two),
        change_type="update",
        before_state=before_two,
        after_state=after_two,
    )
    before_two_hex = hashlib.sha256(before_two.encode("utf-8")).hexdigest()
    after_two_hex = hashlib.sha256(after_two.encode("utf-8")).hexdigest()

    applied_two = await engine.apply_improvement(
        imp2,
        verification_evidence=_synthetic_valid_evidence(),
        target_applicator=_make_file_applicator(file_two),
        measurement_evidence={
            "measurement_receipt_id": "meas-rcpt-002",
            "evaluator_id": "worker:bench-evaluator-2",
            "work_order_id": "wo-rsi-test-1",
            "baseline_tokens": 500,
            "candidate_tokens": 300,
            "before_state_digest": before_two_hex,
            "after_state_digest": after_two_hex,
        },
    )
    assert applied_two is True
    assert imp2.tokens_saved == 200
    assert engine.metrics["total_tokens_saved"] == 650

    rolled_one = await engine.rollback_improvement(imp1)
    assert rolled_one is True
    assert engine.metrics["total_tokens_saved"] == 200
    assert imp1.metrics["rolled_back_tokens_saved"] == 450
    assert imp1.tokens_saved is None
    assert imp1.metrics["token_reduction_measured"] is False

    # Verify clamp >= 0 if aggregate counter was lower than rolled-back delta
    engine.metrics["total_tokens_saved"] = 50
    rolled_two = await engine.rollback_improvement(imp2)
    assert rolled_two is True
    assert engine.metrics["total_tokens_saved"] == 0
    assert imp2.metrics["rolled_back_tokens_saved"] == 200
    assert imp2.tokens_saved is None
    assert imp2.metrics["token_reduction_measured"] is False


@pytest.mark.asyncio
async def test_apply_improvement_rejects_self_authored_or_regressive_measurement_fail_closed(
    tmp_path: Path,
):
    engine = _isolated_engine(tmp_path)
    calls = 0

    def _never_called_applicator(before_state: str, after_state: str):
        nonlocal calls
        calls += 1
        return after_state, lambda: before_state

    invalid_cases = [
        (
            "self-authored-exact",
            {
                "measurement_receipt_id": "meas-bad-1",
                "evaluator_id": "worker:author-1",
                "work_order_id": "wo-rsi-test-1",
                "baseline_tokens": 500,
                "candidate_tokens": 400,
            },
        ),
        (
            "self-authored-padded",
            {
                "measurement_receipt_id": "meas-bad-2",
                "evaluator_id": "  worker:author-1  ",
                "work_order_id": "wo-rsi-test-1",
                "baseline_tokens": 500,
                "candidate_tokens": 400,
            },
        ),
        (
            "regressive-tokens",
            {
                "measurement_receipt_id": "meas-bad-3",
                "evaluator_id": "worker:evaluator-1",
                "work_order_id": "wo-rsi-test-1",
                "baseline_tokens": 500,
                "candidate_tokens": 501,
            },
        ),
        (
            "bool-tokens",
            {
                "measurement_receipt_id": "meas-bad-4",
                "evaluator_id": "worker:evaluator-1",
                "work_order_id": "wo-rsi-test-1",
                "baseline_tokens": True,
                "candidate_tokens": False,
            },
        ),
        (
            "negative-tokens",
            {
                "measurement_receipt_id": "meas-bad-5",
                "evaluator_id": "worker:evaluator-1",
                "work_order_id": "wo-rsi-test-1",
                "baseline_tokens": 100,
                "candidate_tokens": -1,
            },
        ),
        ("non-mapping", ["not", "a", "mapping"]),
    ]

    for label, bad_measurement in invalid_cases:
        imp = Improvement(
            improvement_id=f"imp-meas-reject-{label}",
            pattern_id="pat-1",
            solution_id="sol-1",
            target="modules/x/y/README.md",
            change_type="update",
            before_state="before",
            after_state="after",
        )
        result = await engine.apply_improvement(
            imp,
            verification_evidence=_synthetic_valid_evidence(),
            target_applicator=_never_called_applicator,
            measurement_evidence=bad_measurement,  # type: ignore[arg-type]
        )
        assert result is False, label
        assert calls == 0, label
        assert imp.applied is False, label
        assert imp.applied_at is None, label
        assert imp.tokens_saved is None, label
        assert imp.metrics["token_reduction_measured"] is False, label
        assert imp.metrics["application_status"] == "blocked_measurement_rejected", label

    assert engine.metrics["improvements_applied"] == 0
    assert engine.metrics["total_tokens_saved"] == 0


@pytest.mark.asyncio
async def test_apply_improvement_rejects_mismatched_work_order_or_digests_and_rolls_back(
    tmp_path: Path,
):
    engine = _isolated_engine(tmp_path)
    target_file = tmp_path / "digest_guarded.md"
    before_text = "line: before\n"
    after_text = "line: expected-after\n"
    target_file.write_text(before_text, encoding="utf-8")

    before_hex = hashlib.sha256(before_text.encode("utf-8")).hexdigest()
    after_hex = hashlib.sha256(after_text.encode("utf-8")).hexdigest()
    wrong_hex = "f" * 64

    calls = 0

    def _counting_applicator(before_state: str, desired_after_state: str):
        nonlocal calls
        calls += 1
        target_file.write_text(desired_after_state, encoding="utf-8")
        return target_file.read_text(encoding="utf-8"), lambda: before_state

    for label, overrides in [
        ("work-order-mismatch", {"work_order_id": "wo-other-999"}),
        ("before-digest-mismatch", {"before_state_digest": f"sha256:{wrong_hex}"}),
        ("after-digest-mismatch-pre", {"after_state_digest": f"sha256:{wrong_hex}"}),
    ]:
        imp = Improvement(
            improvement_id=f"imp-digest-{label}",
            pattern_id="pat-1",
            solution_id="sol-1",
            target=str(target_file),
            change_type="update",
            before_state=before_text,
            after_state=after_text,
        )
        measurement = {
            "measurement_receipt_id": f"meas-{label}",
            "evaluator_id": "worker:evaluator-1",
            "work_order_id": "wo-rsi-test-1",
            "baseline_tokens": 300,
            "candidate_tokens": 200,
            "before_state_digest": f"sha256:{before_hex}",
            "after_state_digest": f"sha256:{after_hex}",
            **overrides,
        }
        assert (
            await engine.apply_improvement(
                imp,
                verification_evidence=_synthetic_valid_evidence(),
                target_applicator=_counting_applicator,
                measurement_evidence=measurement,
            )
            is False
        )
        assert calls == 0, label
        assert target_file.read_text(encoding="utf-8") == before_text
        assert imp.applied is False
        assert imp.metrics["application_status"] == "blocked_measurement_rejected"

    # Post-applicator digest mismatch: applicator mutates target to unexpected text,
    # engine must invoke rollback_fn() and reject fail-closed.
    rollback_invoked = False

    def _divergent_applicator(before_state: str, _desired_after_state: str):
        target_file.write_text("line: unexpected-mutation\n", encoding="utf-8")

        def _rollback() -> str:
            nonlocal rollback_invoked
            rollback_invoked = True
            target_file.write_text(before_state, encoding="utf-8")
            return target_file.read_text(encoding="utf-8")

        return target_file.read_text(encoding="utf-8"), _rollback

    imp_post = Improvement(
        improvement_id="imp-digest-post-divergent",
        pattern_id="pat-1",
        solution_id="sol-1",
        target=str(target_file),
        change_type="update",
        before_state=before_text,
        after_state=after_text,
    )
    assert (
        await engine.apply_improvement(
            imp_post,
            verification_evidence=_synthetic_valid_evidence(),
            target_applicator=_divergent_applicator,
            measurement_evidence={
                "measurement_receipt_id": "meas-post-divergent",
                "evaluator_id": "worker:evaluator-1",
                "work_order_id": "wo-rsi-test-1",
                "baseline_tokens": 300,
                "candidate_tokens": 200,
                "before_state_digest": f"sha256:{before_hex}",
                "after_state_digest": f"sha256:{after_hex}",
            },
        )
        is False
    )
    assert rollback_invoked is True
    assert target_file.read_text(encoding="utf-8") == before_text
    assert imp_post.applied is False
    assert imp_post.applied_at is None
    assert imp_post.tokens_saved is None
    assert imp_post.metrics["token_reduction_measured"] is False
    assert imp_post.metrics["application_status"] == "blocked_measurement_rejected"
    assert engine.metrics["improvements_applied"] == 0
    assert engine.metrics["total_tokens_saved"] == 0
