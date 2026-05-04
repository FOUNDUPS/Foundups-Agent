"""Trade FoundUp - Execution Guard Tests

Tests for simulation guard layer in src/guards.py.

WSP References:
- WSP 97: Truth Boundaries (all guards enforce simulation-only)
"""
import pytest

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from guards import (
    # Exceptions
    NoMoneyModeViolation,
    WalletSigningViolation,
    OrderPlacementViolation,
    TruthBoundaryViolation,
    ExecutionGuardViolation,
    # Assertions
    assert_no_money_mode,
    assert_no_wallet_signing,
    assert_no_order_placement,
    assert_no_real_trades,
    assert_no_capital_deployment,
    assert_no_private_key_access,
    # Policy validation
    PolicyValidationResult,
    validate_execution_guard_policy,
    validate_truth_fields,
    # Context manager
    SimulationGuard,
    create_phase0_guard,
    is_phase0_compliant,
    get_phase0_violations,
)
from contracts import (
    ExecutionGuardPolicy,
    TruthFields,
    UnsupportedOperationError,
    DEFAULT_EXECUTION_GUARD,
    DEFAULT_TRUTH_FIELDS,
)


class TestGuardExceptions:
    """Guard exception tests."""

    def test_no_money_mode_violation_message(self):
        """NoMoneyModeViolation has correct message."""
        exc = NoMoneyModeViolation("test_op", "test context")
        assert "test_op" in str(exc)
        assert "test context" in str(exc)
        assert exc.operation == "test_op"
        assert exc.context == "test context"

    def test_wallet_signing_violation_message(self):
        """WalletSigningViolation has correct message."""
        exc = WalletSigningViolation("sign_tx")
        assert "sign_tx" in str(exc)
        assert exc.operation == "sign_tx"

    def test_order_placement_violation_message(self):
        """OrderPlacementViolation has correct message."""
        exc = OrderPlacementViolation("place_order")
        assert "place_order" in str(exc)

    def test_truth_boundary_violation(self):
        """TruthBoundaryViolation has correct attributes."""
        exc = TruthBoundaryViolation("dry_run_mode", True, False)
        assert exc.field == "dry_run_mode"
        assert exc.expected is True
        assert exc.actual is False
        assert "dry_run_mode" in str(exc)

    def test_execution_guard_violation(self):
        """ExecutionGuardViolation has correct violations list."""
        exc = ExecutionGuardViolation(["violation1", "violation2"])
        assert exc.violations == ["violation1", "violation2"]
        assert "violation1" in str(exc)


class TestAssertNoMoneyMode:
    """assert_no_money_mode tests."""

    def test_default_policy_passes(self):
        """Default policy passes no-money assertion."""
        # Should not raise
        assert_no_money_mode()

    def test_explicit_no_money_mode_passes(self):
        """Policy with no_money_mode=True passes."""
        policy = ExecutionGuardPolicy(no_money_mode=True)
        # Should not raise
        assert_no_money_mode(policy)

    def test_no_money_mode_false_raises(self):
        """Policy with no_money_mode=False raises."""
        policy = ExecutionGuardPolicy(no_money_mode=False)
        with pytest.raises(NoMoneyModeViolation):
            assert_no_money_mode(policy)

    def test_no_money_mode_with_operation(self):
        """Exception includes operation name."""
        policy = ExecutionGuardPolicy(no_money_mode=False)
        with pytest.raises(NoMoneyModeViolation) as exc_info:
            assert_no_money_mode(policy, operation="buy_token")
        assert exc_info.value.operation == "buy_token"


class TestAssertNoWalletSigning:
    """assert_no_wallet_signing tests."""

    def test_default_policy_passes(self):
        """Default policy passes wallet signing assertion."""
        # Should not raise
        assert_no_wallet_signing()

    def test_block_wallet_signing_true_passes(self):
        """Policy with block_wallet_signing=True passes."""
        policy = ExecutionGuardPolicy(block_wallet_signing=True)
        # Should not raise
        assert_no_wallet_signing(policy)

    def test_block_wallet_signing_false_raises(self):
        """Policy with block_wallet_signing=False raises."""
        policy = ExecutionGuardPolicy(block_wallet_signing=False)
        with pytest.raises(WalletSigningViolation):
            assert_no_wallet_signing(policy)


class TestAssertNoOrderPlacement:
    """assert_no_order_placement tests."""

    def test_default_policy_passes(self):
        """Default policy passes order placement assertion."""
        # Should not raise
        assert_no_order_placement()

    def test_block_order_placement_true_passes(self):
        """Policy with block_order_placement=True passes."""
        policy = ExecutionGuardPolicy(block_order_placement=True)
        # Should not raise
        assert_no_order_placement(policy)

    def test_block_order_placement_false_raises(self):
        """Policy with block_order_placement=False raises."""
        policy = ExecutionGuardPolicy(block_order_placement=False)
        with pytest.raises(OrderPlacementViolation):
            assert_no_order_placement(policy)


class TestAssertNoRealTrades:
    """assert_no_real_trades tests."""

    def test_default_policy_passes(self):
        """Default policy passes real trades assertion."""
        # Should not raise
        assert_no_real_trades()

    def test_block_real_trades_false_raises(self):
        """Policy with block_real_trades=False raises."""
        policy = ExecutionGuardPolicy(block_real_trades=False)
        with pytest.raises(UnsupportedOperationError):
            assert_no_real_trades(policy)


class TestAssertNoCapitalDeployment:
    """assert_no_capital_deployment tests."""

    def test_default_policy_passes(self):
        """Default policy passes capital deployment assertion."""
        # Should not raise
        assert_no_capital_deployment()

    def test_block_capital_deployment_false_raises(self):
        """Policy with block_capital_deployment=False raises."""
        policy = ExecutionGuardPolicy(block_capital_deployment=False)
        with pytest.raises(UnsupportedOperationError):
            assert_no_capital_deployment(policy)


class TestAssertNoPrivateKeyAccess:
    """assert_no_private_key_access tests."""

    def test_default_policy_passes(self):
        """Default policy passes private key assertion."""
        # Should not raise
        assert_no_private_key_access()

    def test_block_private_keys_false_raises(self):
        """Policy with block_private_keys=False raises."""
        policy = ExecutionGuardPolicy(block_private_keys=False)
        with pytest.raises(UnsupportedOperationError):
            assert_no_private_key_access(policy)


class TestValidateExecutionGuardPolicy:
    """validate_execution_guard_policy tests."""

    def test_default_policy_valid(self):
        """Default policy is Phase 0 compliant."""
        policy = ExecutionGuardPolicy()
        result = validate_execution_guard_policy(policy)
        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_no_money_mode_false_violation(self):
        """no_money_mode=False is a violation."""
        policy = ExecutionGuardPolicy(no_money_mode=False)
        result = validate_execution_guard_policy(policy, require_phase0=True)
        assert result.is_valid is False
        assert "no_money_mode must be True in Phase 0" in result.violations

    def test_dry_run_mode_false_violation(self):
        """dry_run_mode=False is a violation."""
        policy = ExecutionGuardPolicy(dry_run_mode=False)
        result = validate_execution_guard_policy(policy, require_phase0=True)
        assert result.is_valid is False
        assert "dry_run_mode must be True in Phase 0" in result.violations

    def test_block_real_trades_false_violation(self):
        """block_real_trades=False is a violation."""
        policy = ExecutionGuardPolicy(block_real_trades=False)
        result = validate_execution_guard_policy(policy, require_phase0=True)
        assert result.is_valid is False
        assert "block_real_trades must be True in Phase 0" in result.violations

    def test_ethical_blocks_always_required(self):
        """Ethical blocks (wash trading, etc.) always required."""
        policy = ExecutionGuardPolicy(
            block_wash_trading=False,
            block_market_manipulation=False,
        )
        result = validate_execution_guard_policy(policy, require_phase0=True)
        assert result.is_valid is False
        assert "block_wash_trading must be True" in result.violations
        assert "block_market_manipulation must be True" in result.violations

    def test_non_phase0_mode_permissive(self):
        """Non-Phase 0 mode doesn't enforce simulation constraints."""
        policy = ExecutionGuardPolicy(no_money_mode=False)
        result = validate_execution_guard_policy(policy, require_phase0=False)
        assert result.is_valid is True


class TestValidateTruthFields:
    """validate_truth_fields tests."""

    def test_default_truth_fields_valid(self):
        """Default truth fields are Phase 0 compliant."""
        fields = TruthFields()
        result = validate_truth_fields(fields)
        assert result.is_valid is True

    def test_dry_run_mode_false_violation(self):
        """dry_run_mode=False is a violation."""
        fields = TruthFields(dry_run_mode=False)
        result = validate_truth_fields(fields, require_phase0=True)
        assert result.is_valid is False
        assert "dry_run_mode must be True in Phase 0" in result.violations

    def test_real_execution_performed_violation(self):
        """real_execution_performed=True is a violation."""
        fields = TruthFields(real_execution_performed=True)
        result = validate_truth_fields(fields, require_phase0=True)
        assert result.is_valid is False
        assert "real_execution_performed must be False in Phase 0" in result.violations

    def test_verification_complete_violation(self):
        """verification_complete=True is a violation."""
        fields = TruthFields(verification_complete=True)
        result = validate_truth_fields(fields, require_phase0=True)
        assert result.is_valid is False

    def test_cabr_ready_violation(self):
        """cabr_ready=True is a violation."""
        fields = TruthFields(cabr_ready=True)
        result = validate_truth_fields(fields, require_phase0=True)
        assert result.is_valid is False

    def test_payout_ready_violation(self):
        """payout_ready=True is a violation."""
        fields = TruthFields(payout_ready=True)
        result = validate_truth_fields(fields, require_phase0=True)
        assert result.is_valid is False


class TestPolicyValidationResult:
    """PolicyValidationResult tests."""

    def test_to_dict(self):
        """Result serializes to dict."""
        result = PolicyValidationResult(
            is_valid=False,
            violations=["v1", "v2"],
            warnings=["w1"],
        )
        d = result.to_dict()
        assert d["is_valid"] is False
        assert len(d["violations"]) == 2
        assert len(d["warnings"]) == 1


class TestSimulationGuard:
    """SimulationGuard context manager tests."""

    def test_context_manager_valid_policy(self):
        """Context manager works with valid policy."""
        with SimulationGuard() as guard:
            # Should not raise
            guard.assert_simulation_only()

    def test_context_manager_invalid_policy_raises_on_enter(self):
        """Context manager raises on entry with invalid policy."""
        policy = ExecutionGuardPolicy(no_money_mode=False)
        with pytest.raises(ExecutionGuardViolation):
            with SimulationGuard(policy=policy):
                pass

    def test_context_manager_invalid_truth_fields_raises(self):
        """Context manager raises with invalid truth fields."""
        fields = TruthFields(real_execution_performed=True)
        with pytest.raises(ExecutionGuardViolation):
            with SimulationGuard(truth_fields=fields):
                pass

    def test_assert_simulation_only_outside_context(self):
        """assert_simulation_only raises when not in context."""
        guard = SimulationGuard()
        with pytest.raises(RuntimeError):
            guard.assert_simulation_only()

    def test_assert_operation_allowed(self):
        """assert_operation_allowed works in context."""
        with SimulationGuard() as guard:
            # Unknown operations pass
            guard.assert_operation_allowed("unknown_operation")

            # Known blocked operations fail
            with pytest.raises(UnsupportedOperationError):
                guard.assert_operation_allowed("real_trade")

    def test_get_blocked_operations(self):
        """get_blocked_operations returns all blocked operations."""
        with SimulationGuard() as guard:
            blocked = guard.get_blocked_operations()
            assert "real_trade" in blocked
            assert "wallet_sign" in blocked
            assert "private_key_access" in blocked
            assert "order_place" in blocked
            assert "capital_deploy" in blocked
            assert "wash_trade" in blocked
            assert "market_manipulate" in blocked
            assert "conceal_bot" in blocked
            assert "fake_volume" in blocked


class TestCreatePhase0Guard:
    """create_phase0_guard convenience function tests."""

    def test_creates_valid_guard(self):
        """create_phase0_guard creates valid guard."""
        guard = create_phase0_guard()
        with guard:
            guard.assert_simulation_only()


class TestIsPhase0Compliant:
    """is_phase0_compliant convenience function tests."""

    def test_default_policies_compliant(self):
        """Default policies are compliant."""
        assert is_phase0_compliant(DEFAULT_EXECUTION_GUARD, DEFAULT_TRUTH_FIELDS)

    def test_invalid_policy_not_compliant(self):
        """Invalid policy not compliant."""
        policy = ExecutionGuardPolicy(no_money_mode=False)
        assert is_phase0_compliant(policy, DEFAULT_TRUTH_FIELDS) is False

    def test_invalid_truth_fields_not_compliant(self):
        """Invalid truth fields not compliant."""
        fields = TruthFields(real_execution_performed=True)
        assert is_phase0_compliant(DEFAULT_EXECUTION_GUARD, fields) is False


class TestGetPhase0Violations:
    """get_phase0_violations convenience function tests."""

    def test_no_violations_with_defaults(self):
        """Default policies have no violations."""
        violations = get_phase0_violations(DEFAULT_EXECUTION_GUARD, DEFAULT_TRUTH_FIELDS)
        assert len(violations) == 0

    def test_returns_all_violations(self):
        """Returns all violations from both policy and truth fields."""
        policy = ExecutionGuardPolicy(no_money_mode=False)
        fields = TruthFields(real_execution_performed=True)
        violations = get_phase0_violations(policy, fields)
        assert "no_money_mode must be True in Phase 0" in violations
        assert "real_execution_performed must be False in Phase 0" in violations


class TestPhase0GuardIntegration:
    """Integration tests for Phase 0 guard workflow."""

    def test_full_simulation_workflow(self):
        """Complete simulation workflow with guards."""
        # Create Phase 0 compliant guard
        guard = create_phase0_guard()

        # Enter simulation context
        with guard:
            # Verify simulation mode
            guard.assert_simulation_only("analysis_operation")

            # Verify all execution operations blocked
            blocked_ops = guard.get_blocked_operations()
            for op in blocked_ops:
                with pytest.raises(UnsupportedOperationError):
                    guard.assert_operation_allowed(op)

    def test_guard_prevents_execution_claims(self):
        """Guard prevents false execution claims."""
        with create_phase0_guard() as guard:
            # Cannot claim real execution
            policy = guard.policy
            assert policy.no_money_mode is True
            assert policy.dry_run_mode is True

            # Cannot claim execution performed
            fields = guard.truth_fields
            assert fields.real_execution_performed is False
            assert fields.verification_complete is False
            assert fields.cabr_ready is False
            assert fields.payout_ready is False
