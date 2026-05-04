"""Trade FoundUp - Execution Guards

Simulation guard functions and policy validators.
All guards enforce WSP 97 truth boundaries.

WSP References:
- WSP 97: Truth Boundaries (no false execution claims)
- WSP 104: FoundUp Route Namespace

Phase 0 Constraints:
- no_money_mode: True (always)
- dry_run_mode: True (always)
- All execution operations blocked
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from .contracts import (
        ExecutionGuardPolicy,
        TruthFields,
        UnsupportedOperationError,
        DEFAULT_EXECUTION_GUARD,
        DEFAULT_TRUTH_FIELDS,
    )
except ImportError:
    from contracts import (
        ExecutionGuardPolicy,
        TruthFields,
        UnsupportedOperationError,
        DEFAULT_EXECUTION_GUARD,
        DEFAULT_TRUTH_FIELDS,
    )


# ---------------------------------------------------------------------------
# Guard Exceptions
# ---------------------------------------------------------------------------


class NoMoneyModeViolation(UnsupportedOperationError):
    """Raised when no-money mode is violated."""

    def __init__(self, operation: str, context: Optional[str] = None):
        message = f"No-money mode violation: '{operation}' attempted"
        if context:
            message += f" - {context}"
        super().__init__(message)
        self.operation = operation
        self.context = context


class WalletSigningViolation(UnsupportedOperationError):
    """Raised when wallet signing is attempted."""

    def __init__(self, operation: str, context: Optional[str] = None):
        message = f"Wallet signing violation: '{operation}' attempted"
        if context:
            message += f" - {context}"
        super().__init__(message)
        self.operation = operation
        self.context = context


class OrderPlacementViolation(UnsupportedOperationError):
    """Raised when order placement is attempted."""

    def __init__(self, operation: str, context: Optional[str] = None):
        message = f"Order placement violation: '{operation}' attempted"
        if context:
            message += f" - {context}"
        super().__init__(message)
        self.operation = operation
        self.context = context


class TruthBoundaryViolation(Exception):
    """Raised when truth boundary is violated."""

    def __init__(self, field: str, expected: Any, actual: Any):
        message = f"Truth boundary violation: {field} expected={expected}, actual={actual}"
        super().__init__(message)
        self.field = field
        self.expected = expected
        self.actual = actual


class ExecutionGuardViolation(Exception):
    """Raised when execution guard policy is violated."""

    def __init__(self, violations: List[str]):
        message = f"Execution guard violations: {', '.join(violations)}"
        super().__init__(message)
        self.violations = violations


# ---------------------------------------------------------------------------
# Guard Assertions
# ---------------------------------------------------------------------------


def assert_no_money_mode(
    policy: Optional[ExecutionGuardPolicy] = None,
    operation: Optional[str] = None,
    context: Optional[str] = None,
) -> None:
    """Assert that no-money mode is enforced.

    Raises NoMoneyModeViolation if no_money_mode is False.

    Args:
        policy: Execution guard policy (uses default if not provided)
        operation: Operation being attempted (for error context)
        context: Additional context for error message

    Raises:
        NoMoneyModeViolation: If no_money_mode is False
    """
    guard = policy or DEFAULT_EXECUTION_GUARD
    if not guard.no_money_mode:
        raise NoMoneyModeViolation(
            operation=operation or "unknown",
            context=context or "Phase 0 requires no_money_mode=True",
        )


def assert_no_wallet_signing(
    policy: Optional[ExecutionGuardPolicy] = None,
    operation: Optional[str] = None,
    context: Optional[str] = None,
) -> None:
    """Assert that wallet signing is blocked.

    Raises WalletSigningViolation if wallet signing is not blocked.

    Args:
        policy: Execution guard policy (uses default if not provided)
        operation: Operation being attempted (for error context)
        context: Additional context for error message

    Raises:
        WalletSigningViolation: If block_wallet_signing is False
    """
    guard = policy or DEFAULT_EXECUTION_GUARD
    if not guard.block_wallet_signing:
        raise WalletSigningViolation(
            operation=operation or "wallet_sign",
            context=context or "Phase 0 blocks all wallet signing",
        )


def assert_no_order_placement(
    policy: Optional[ExecutionGuardPolicy] = None,
    operation: Optional[str] = None,
    context: Optional[str] = None,
) -> None:
    """Assert that order placement is blocked.

    Raises OrderPlacementViolation if order placement is not blocked.

    Args:
        policy: Execution guard policy (uses default if not provided)
        operation: Operation being attempted (for error context)
        context: Additional context for error message

    Raises:
        OrderPlacementViolation: If block_order_placement is False
    """
    guard = policy or DEFAULT_EXECUTION_GUARD
    if not guard.block_order_placement:
        raise OrderPlacementViolation(
            operation=operation or "order_place",
            context=context or "Phase 0 blocks all order placement",
        )


def assert_no_real_trades(
    policy: Optional[ExecutionGuardPolicy] = None,
    operation: Optional[str] = None,
    context: Optional[str] = None,
) -> None:
    """Assert that real trades are blocked.

    Args:
        policy: Execution guard policy (uses default if not provided)
        operation: Operation being attempted
        context: Additional context for error message

    Raises:
        UnsupportedOperationError: If block_real_trades is False
    """
    guard = policy or DEFAULT_EXECUTION_GUARD
    if not guard.block_real_trades:
        raise UnsupportedOperationError(
            f"Real trade violation: '{operation or 'real_trade'}' attempted. "
            f"{context or 'Phase 0 blocks all real trades'}"
        )


def assert_no_capital_deployment(
    policy: Optional[ExecutionGuardPolicy] = None,
    operation: Optional[str] = None,
    context: Optional[str] = None,
) -> None:
    """Assert that capital deployment is blocked.

    Args:
        policy: Execution guard policy (uses default if not provided)
        operation: Operation being attempted
        context: Additional context for error message

    Raises:
        UnsupportedOperationError: If block_capital_deployment is False
    """
    guard = policy or DEFAULT_EXECUTION_GUARD
    if not guard.block_capital_deployment:
        raise UnsupportedOperationError(
            f"Capital deployment violation: '{operation or 'capital_deploy'}' attempted. "
            f"{context or 'Phase 0 blocks all capital deployment'}"
        )


def assert_no_private_key_access(
    policy: Optional[ExecutionGuardPolicy] = None,
    operation: Optional[str] = None,
    context: Optional[str] = None,
) -> None:
    """Assert that private key access is blocked.

    Args:
        policy: Execution guard policy (uses default if not provided)
        operation: Operation being attempted
        context: Additional context for error message

    Raises:
        UnsupportedOperationError: If block_private_keys is False
    """
    guard = policy or DEFAULT_EXECUTION_GUARD
    if not guard.block_private_keys:
        raise UnsupportedOperationError(
            f"Private key access violation: '{operation or 'private_key_access'}' attempted. "
            f"{context or 'Phase 0 blocks all private key access'}"
        )


# ---------------------------------------------------------------------------
# Policy Validation
# ---------------------------------------------------------------------------


@dataclass
class PolicyValidationResult:
    """Result of policy validation."""

    is_valid: bool
    violations: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "violations": self.violations,
            "warnings": self.warnings,
        }


def validate_execution_guard_policy(
    policy: ExecutionGuardPolicy,
    require_phase0: bool = True,
) -> PolicyValidationResult:
    """Validate an execution guard policy.

    Args:
        policy: Policy to validate
        require_phase0: If True, requires Phase 0 constraints

    Returns:
        PolicyValidationResult with validation status
    """
    violations = []
    warnings = []

    if require_phase0:
        # Phase 0 requires no-money mode
        if not policy.no_money_mode:
            violations.append("no_money_mode must be True in Phase 0")

        # Phase 0 requires dry-run mode
        if not policy.dry_run_mode:
            violations.append("dry_run_mode must be True in Phase 0")

        # All execution blocks must be enabled
        if not policy.block_real_trades:
            violations.append("block_real_trades must be True in Phase 0")
        if not policy.block_wallet_signing:
            violations.append("block_wallet_signing must be True in Phase 0")
        if not policy.block_private_keys:
            violations.append("block_private_keys must be True in Phase 0")
        if not policy.block_order_placement:
            violations.append("block_order_placement must be True in Phase 0")
        if not policy.block_capital_deployment:
            violations.append("block_capital_deployment must be True in Phase 0")

        # Ethical blocks must be enabled (always)
        if not policy.block_wash_trading:
            violations.append("block_wash_trading must be True")
        if not policy.block_market_manipulation:
            violations.append("block_market_manipulation must be True")
        if not policy.block_bot_concealment:
            violations.append("block_bot_concealment must be True")
        if not policy.block_fake_volume:
            violations.append("block_fake_volume must be True")

    return PolicyValidationResult(
        is_valid=len(violations) == 0,
        violations=violations,
        warnings=warnings,
    )


def validate_truth_fields(
    fields: TruthFields,
    require_phase0: bool = True,
) -> PolicyValidationResult:
    """Validate truth fields.

    Args:
        fields: TruthFields to validate
        require_phase0: If True, requires Phase 0 constraints

    Returns:
        PolicyValidationResult with validation status
    """
    violations = []
    warnings = []

    if require_phase0:
        if not fields.dry_run_mode:
            violations.append("dry_run_mode must be True in Phase 0")
        if not fields.no_money_mode:
            violations.append("no_money_mode must be True in Phase 0")
        if fields.real_execution_performed:
            violations.append("real_execution_performed must be False in Phase 0")
        if fields.verification_complete:
            violations.append("verification_complete must be False in Phase 0")
        if fields.cabr_ready:
            violations.append("cabr_ready must be False in Phase 0")
        if fields.payout_ready:
            violations.append("payout_ready must be False in Phase 0")

    return PolicyValidationResult(
        is_valid=len(violations) == 0,
        violations=violations,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Guard Context Manager
# ---------------------------------------------------------------------------


class SimulationGuard:
    """Context manager for enforcing simulation mode.

    Ensures all operations within the context are simulation-only.

    Usage:
        with SimulationGuard() as guard:
            guard.assert_simulation_only()
            # ... perform simulation operations ...
    """

    def __init__(
        self,
        policy: Optional[ExecutionGuardPolicy] = None,
        truth_fields: Optional[TruthFields] = None,
    ):
        self.policy = policy or DEFAULT_EXECUTION_GUARD
        self.truth_fields = truth_fields or DEFAULT_TRUTH_FIELDS
        self._active = False

    def __enter__(self) -> "SimulationGuard":
        # Validate policy on entry
        policy_result = validate_execution_guard_policy(self.policy)
        if not policy_result.is_valid:
            raise ExecutionGuardViolation(policy_result.violations)

        # Validate truth fields on entry
        truth_result = validate_truth_fields(self.truth_fields)
        if not truth_result.is_valid:
            raise ExecutionGuardViolation(truth_result.violations)

        self._active = True
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        self._active = False
        # Don't suppress exceptions
        return False

    def assert_simulation_only(self, operation: Optional[str] = None) -> None:
        """Assert simulation-only mode is active."""
        if not self._active:
            raise RuntimeError("SimulationGuard is not active")

        assert_no_money_mode(self.policy, operation)
        self.truth_fields.assert_no_execution()

    def assert_operation_allowed(self, operation: str) -> None:
        """Assert an operation is allowed under current policy."""
        if not self._active:
            raise RuntimeError("SimulationGuard is not active")

        self.policy.assert_operation_allowed(operation)

    def get_blocked_operations(self) -> List[str]:
        """Get list of blocked operations."""
        blocked = []
        if self.policy.block_real_trades:
            blocked.append("real_trade")
        if self.policy.block_wallet_signing:
            blocked.append("wallet_sign")
        if self.policy.block_private_keys:
            blocked.append("private_key_access")
        if self.policy.block_order_placement:
            blocked.append("order_place")
        if self.policy.block_capital_deployment:
            blocked.append("capital_deploy")
        if self.policy.block_wash_trading:
            blocked.append("wash_trade")
        if self.policy.block_market_manipulation:
            blocked.append("market_manipulate")
        if self.policy.block_bot_concealment:
            blocked.append("conceal_bot")
        if self.policy.block_fake_volume:
            blocked.append("fake_volume")
        return blocked


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------


def create_phase0_guard() -> SimulationGuard:
    """Create a simulation guard with Phase 0 defaults."""
    return SimulationGuard(
        policy=ExecutionGuardPolicy(),
        truth_fields=TruthFields(),
    )


def is_phase0_compliant(
    policy: ExecutionGuardPolicy,
    truth_fields: TruthFields,
) -> bool:
    """Check if policy and truth fields are Phase 0 compliant."""
    policy_result = validate_execution_guard_policy(policy, require_phase0=True)
    truth_result = validate_truth_fields(truth_fields, require_phase0=True)
    return policy_result.is_valid and truth_result.is_valid


def get_phase0_violations(
    policy: ExecutionGuardPolicy,
    truth_fields: TruthFields,
) -> List[str]:
    """Get all Phase 0 violations for policy and truth fields."""
    policy_result = validate_execution_guard_policy(policy, require_phase0=True)
    truth_result = validate_truth_fields(truth_fields, require_phase0=True)
    return policy_result.violations + truth_result.violations
