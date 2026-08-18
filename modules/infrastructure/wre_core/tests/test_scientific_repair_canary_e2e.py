"""End-to-End Test Suite for Scientific Autonomous Self-Healing Canary (Slice 3).

Governed by WSP_00, WSP_15, WSP_50, WSP_80, WSP_97, WSP_109 (Issue #1522).
"""

from pathlib import Path
import pytest

from modules.infrastructure.wre_core.src.repair_operation_contract import (
    CounterexampleReceipt,
    FinalDisposition,
    RepairOperationState,
)
from modules.ai_intelligence.ai_gateway.src.independent_repair_verifier import (
    VerifierDisposition,
)
from modules.infrastructure.wre_core.src.scientific_repair_canary_orchestrator import (
    ScientificRepairCanaryOrchestrator,
)


def test_canary_e2e_successful_repair_cycle(tmp_path: Path) -> None:
    """Proves the complete autonomous scientific self-healing loop passes 100%."""
    orchestrator = ScientificRepairCanaryOrchestrator(repo_root=tmp_path)

    def mock_builder_patch(sandbox: Path) -> str:
        patch_file = sandbox / "fix.py"
        patch_file.write_text("def validate(token):\n    if not token:\n        raise ValueError('empty')\n")
        return "diff --git a/fix.py b/fix.py\n+ def validate(token): ..."

    def mock_deterministic_tests(sandbox: Path) -> tuple[bool, str]:
        assert (sandbox / "fix.py").exists()
        return True, "10/10 unit tests passed"

    def mock_independent_verifier(packet) -> tuple[VerifierDisposition, str, CounterexampleReceipt | None]:
        assert "Model A believes" not in packet.pain
        assert packet.builder_identity == "builder_model_a"
        return VerifierDisposition.ACCEPT, "Evidence proves root cause resolved without regression", None

    op, receipt = orchestrator.run_autonomous_repair_cycle(
        failure_id="fail-auth-empty-token",
        pain="Empty token allows unauthenticated access",
        desired_outcome="Empty token raises ValueError",
        reproduction_command=["python", "-c", "import sys; sys.stderr.write('AUTH_LEAK_INVARIANT'); sys.exit(1)"],
        failing_invariant="AUTH_LEAK_INVARIANT",
        builder_patch_fn=mock_builder_patch,
        deterministic_test_fn=mock_deterministic_tests,
        independent_verifier_fn=mock_independent_verifier,
        scratch_dir=tmp_path / "sandbox",
    )

    assert op.state == RepairOperationState.LEARNED
    assert op.final_disposition == FinalDisposition.ACCEPT
    assert receipt.all_stages_passed is True
    assert receipt.staged_branch_name == "repair/fail-auth-empty-token-canary"
    assert receipt.baseline_receipt_digest.startswith("sha256:")
    assert receipt.verifier_receipt_digest.startswith("sha256:")


def test_canary_e2e_non_reproducible_failure_halts_mutation(tmp_path: Path) -> None:
    """Proves that a non-reproducible failure stops immediately with NO MUTATION."""
    orchestrator = ScientificRepairCanaryOrchestrator(repo_root=tmp_path)

    op, receipt = orchestrator.run_autonomous_repair_cycle(
        failure_id="fail-transient-network",
        pain="Flaky network timeout",
        desired_outcome="Stable network",
        reproduction_command=["python", "-c", "import sys; sys.exit(0)"],  # Exits 0 -> not reproducible!
        failing_invariant="NETWORK_TIMEOUT",
        scratch_dir=tmp_path / "sandbox",
    )

    assert op.state == RepairOperationState.LEARNED
    assert op.final_disposition == FinalDisposition.ABANDON
    assert receipt.all_stages_passed is False
    assert receipt.staged_branch_name == ""
    assert op.baseline_receipt is None
    # Sandbox was NEVER created/mutated!
    assert not (tmp_path / "sandbox").exists()


def test_canary_e2e_model_b_rejection_halts_and_emits_counterexample(tmp_path: Path) -> None:
    """Proves that when Model B rejects, a structured CounterexampleReceipt is preserved."""
    orchestrator = ScientificRepairCanaryOrchestrator(repo_root=tmp_path)

    def mock_independent_verifier_rejection(packet) -> tuple[VerifierDisposition, str, CounterexampleReceipt | None]:
        ce = CounterexampleReceipt.create(
            objection_id="obj-canary-01",
            category="regression",
            claim="Fails on whitespace token",
            evidence="Token with spaces passes validation",
        )
        return VerifierDisposition.REJECT, "Candidate does not handle whitespace-only tokens", ce

    op, receipt = orchestrator.run_autonomous_repair_cycle(
        failure_id="fail-whitespace-token",
        pain="Whitespace token allows unauthenticated access",
        desired_outcome="Whitespace token raises ValueError",
        reproduction_command=["python", "-c", "import sys; sys.stderr.write('WHITESPACE_INVARIANT'); sys.exit(1)"],
        failing_invariant="WHITESPACE_INVARIANT",
        independent_verifier_fn=mock_independent_verifier_rejection,
        scratch_dir=tmp_path / "sandbox",
    )

    assert op.state == RepairOperationState.LEARNED
    assert op.final_disposition == FinalDisposition.ABANDON
    assert receipt.all_stages_passed is False
    assert len(op.counterexamples) == 1
    assert op.counterexamples[0].objection_id == "obj-canary-01"
