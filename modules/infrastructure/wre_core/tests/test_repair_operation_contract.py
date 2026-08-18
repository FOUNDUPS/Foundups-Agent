"""Tests for Scientific Autonomous Self-Healing Operation Contract.

Governed by WSP_00, WSP_50, WSP_97 (Issue #1522 / Slice 1).
"""

from pathlib import Path
import pytest

from modules.infrastructure.wre_core.src.repair_operation_contract import (
    AuthorityTier,
    BaselineReceipt,
    CounterexampleReceipt,
    ExperimentBudget,
    FinalDisposition,
    NonReproducibleClassification,
    RepairOperationState,
    ResearchQuarantineArtifact,
    ScientificRepairOperation,
)
from modules.infrastructure.wre_core.src.repair_baseline_verifier import (
    attempt_failure_reproduction,
)


def test_state_machine_valid_happy_path() -> None:
    """Test standard scientific progression through the valid state lifecycle."""
    op = ScientificRepairOperation(
        operation_id="op-test-001",
        cycle_id="cycle-001",
        dae_id="reddog-dae",
        failure_id="fail-fastmcp-auth",
        state=RepairOperationState.OBSERVED,
        pain="FastMCP auth fails open",
        desired_outcome="FastMCP fails closed",
    )

    assert op.state == RepairOperationState.OBSERVED
    op.transition_to(RepairOperationState.REPRODUCING)
    assert op.state == RepairOperationState.REPRODUCING
    op.transition_to(RepairOperationState.REPRODUCED)
    assert op.state == RepairOperationState.REPRODUCED
    op.transition_to(RepairOperationState.BASELINED)
    assert op.state == RepairOperationState.BASELINED
    op.transition_to(RepairOperationState.RESEARCHING)
    assert op.state == RepairOperationState.RESEARCHING
    op.transition_to(RepairOperationState.HYPOTHESIS_DEFINED)
    assert op.state == RepairOperationState.HYPOTHESIS_DEFINED
    op.transition_to(RepairOperationState.ADMISSION_PENDING)
    assert op.state == RepairOperationState.ADMISSION_PENDING
    op.transition_to(RepairOperationState.ADMITTED)
    assert op.state == RepairOperationState.ADMITTED
    op.transition_to(RepairOperationState.SANDBOX_PREPARING)
    assert op.state == RepairOperationState.SANDBOX_PREPARING
    op.transition_to(RepairOperationState.EXPERIMENTING)
    assert op.state == RepairOperationState.EXPERIMENTING
    op.transition_to(RepairOperationState.DETERMINISTIC_VERIFY)
    assert op.state == RepairOperationState.DETERMINISTIC_VERIFY
    op.transition_to(RepairOperationState.INDEPENDENT_VERIFY)
    assert op.state == RepairOperationState.INDEPENDENT_VERIFY
    op.transition_to(RepairOperationState.ACCEPTED)
    assert op.state == RepairOperationState.ACCEPTED
    op.transition_to(RepairOperationState.LEARNED)
    assert op.state == RepairOperationState.LEARNED


def test_invalid_state_transitions_fail_closed() -> None:
    """Proves that unauthorized state skips are strictly forbidden and raise ValueError."""
    op = ScientificRepairOperation(
        operation_id="op-test-002",
        cycle_id="cycle-001",
        dae_id="reddog-dae",
        failure_id="fail-auth",
        state=RepairOperationState.OBSERVED,
        pain="Test pain",
        desired_outcome="Test outcome",
    )

    # Cannot skip directly to ACCEPTED
    with pytest.raises(ValueError, match="Invalid state transition"):
        op.transition_to(RepairOperationState.ACCEPTED)

    # Cannot skip directly to EXPERIMENTING without reproduction and admission
    with pytest.raises(ValueError, match="Invalid state transition"):
        op.transition_to(RepairOperationState.EXPERIMENTING)


def test_non_reproducible_path_halts_mutation() -> None:
    """Proves that unauthenticated/non-reproducible observations branch cleanly to LEARNED."""
    op = ScientificRepairOperation(
        operation_id="op-test-003",
        cycle_id="cycle-001",
        dae_id="reddog-dae",
        failure_id="fail-transient",
        state=RepairOperationState.OBSERVED,
        pain="Transient glitch",
        desired_outcome="Stable",
    )

    op.transition_to(RepairOperationState.REPRODUCING)
    op.non_reproducible_classification = NonReproducibleClassification.TRANSIENT
    op.transition_to(RepairOperationState.NON_REPRODUCIBLE, reason="Telemetry transient glitch")
    assert op.state == RepairOperationState.NON_REPRODUCIBLE

    # From NON_REPRODUCIBLE, cannot jump to EXPERIMENTING
    with pytest.raises(ValueError, match="Invalid state transition"):
        op.transition_to(RepairOperationState.EXPERIMENTING)

    # Can transition to LEARNED
    op.transition_to(RepairOperationState.LEARNED)
    assert op.state == RepairOperationState.LEARNED


def test_counterexample_and_budget_exhaustion() -> None:
    """Proves that verifier rejections emit counterexamples and decrement retry budget."""
    budget = ExperimentBudget(max_iterations=2)
    op = ScientificRepairOperation(
        operation_id="op-test-004",
        cycle_id="cycle-001",
        dae_id="reddog-dae",
        failure_id="fail-edge-case",
        state=RepairOperationState.INDEPENDENT_VERIFY,
        pain="Failing invariant",
        desired_outcome="Passing invariant",
        budget=budget,
    )

    assert not op.budget_exhausted()

    # Model B rejects with structured counterexample #1
    ce1 = CounterexampleReceipt.create(
        objection_id="obj-001",
        category="regression",
        claim="Fails on empty token",
        evidence="Missing ValueError check",
        requested_test="test_empty_token",
    )
    op.record_counterexample(ce1)
    assert op.consumed_iterations == 1
    assert not op.budget_exhausted()

    # Retries experiment
    op.transition_to(RepairOperationState.EXPERIMENTING)
    op.transition_to(RepairOperationState.DETERMINISTIC_VERIFY)
    op.transition_to(RepairOperationState.INDEPENDENT_VERIFY)

    # Model B rejects with structured counterexample #2
    ce2 = CounterexampleReceipt.create(
        objection_id="obj-002",
        category="regression",
        claim="Still fails on whitespace token",
        evidence="strip() missing",
    )
    op.record_counterexample(ce2)
    assert op.consumed_iterations == 2
    assert op.budget_exhausted()

    # Budget exhausted -> must ABANDON or ESCALATE, cannot loop infinitely
    op.final_disposition = FinalDisposition.ABANDON
    op.transition_to(RepairOperationState.ABANDONED, reason="Budget exhausted after 2 rejections")
    assert op.state == RepairOperationState.ABANDONED


def test_baseline_receipt_tamper_detection() -> None:
    """Proves BaselineReceipt validates canonical digest and detects tampering."""
    receipt = BaselineReceipt.create(
        failure_id="fail-cve-001",
        failing_invariant="AttributeError: 'NoneType' object has no attribute 'secret'",
        head_sha="80328ac3d80328ac3d80328ac3d80328ac3d8032",
        environment_digest="sha256:11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
        reproduction_command="pytest tests/test_failure.py",
        exit_code=1,
        bounded_log_evidence="Traceback ...",
        relevant_tests=["tests/test_failure.py"],
    )

    assert receipt.verify_integrity() is True

    # Tamper with exit_code
    tampered = BaselineReceipt(
        schema_version=receipt.schema_version,
        failure_id=receipt.failure_id,
        failing_invariant=receipt.failing_invariant,
        head_sha=receipt.head_sha,
        environment_digest=receipt.environment_digest,
        reproduction_command=receipt.reproduction_command,
        exit_code=0,  # Tampered
        bounded_log_evidence=receipt.bounded_log_evidence,
        relevant_tests=receipt.relevant_tests,
        authority_declaration=receipt.authority_declaration,
        created_at=receipt.created_at,
        receipt_digest=receipt.receipt_digest,
    )
    assert tampered.verify_integrity() is False


def test_attempt_failure_reproduction_reproduced(tmp_path: Path) -> None:
    """Test reproduction verifier when failure is genuine and matches invariant."""
    repro, receipt, non_repro, msg = attempt_failure_reproduction(
        repo_root=tmp_path,
        failure_id="test-fail-1",
        reproduction_command=["python", "-c", "import sys; sys.stderr.write('CRITICAL_FAIL_SIG'); sys.exit(1)"],
        failing_invariant="CRITICAL_FAIL_SIG",
        relevant_tests=["test_sig.py"],
    )

    assert repro is True
    assert non_repro is None
    assert receipt is not None
    assert receipt.exit_code == 1
    assert "CRITICAL_FAIL_SIG" in receipt.bounded_log_evidence
    assert receipt.verify_integrity() is True


def test_attempt_failure_reproduction_already_resolved(tmp_path: Path) -> None:
    """Test reproduction verifier when command exits 0 (not reproducible)."""
    repro, receipt, non_repro, msg = attempt_failure_reproduction(
        repo_root=tmp_path,
        failure_id="test-fail-2",
        reproduction_command=["python", "-c", "import sys; sys.exit(0)"],
        failing_invariant="CRITICAL_FAIL_SIG",
    )

    assert repro is False
    assert receipt is None
    assert non_repro == NonReproducibleClassification.ALREADY_RESOLVED


def test_attempt_failure_reproduction_mismatched_invariant(tmp_path: Path) -> None:
    """Test reproduction verifier when command fails but with wrong error."""
    repro, receipt, non_repro, msg = attempt_failure_reproduction(
        repo_root=tmp_path,
        failure_id="test-fail-3",
        reproduction_command=["python", "-c", "import sys; sys.stderr.write('DIFFERENT_ERR'); sys.exit(1)"],
        failing_invariant="EXPECTED_EXACT_INVARIANT",
    )

    assert repro is False
    assert receipt is None
    assert non_repro == NonReproducibleClassification.OBSERVER_DEFECT
