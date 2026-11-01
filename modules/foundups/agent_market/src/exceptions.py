"""Domain exceptions for FoundUps Agent Market.

WSP References:
- WSP 50: Error handling with domain exceptions
- WSP 11: Public API contract stability
"""


class AgentMarketError(Exception):
    """Base error for module-level failures."""


class ValidationError(AgentMarketError):
    """Schema validation failed."""


class NotFoundError(AgentMarketError):
    """Requested entity does not exist."""


class InvalidStateTransitionError(AgentMarketError):
    """Task transition is not valid for current state.

    Raised when attempting a lifecycle transition that violates
    the deterministic state machine:
        OPEN -> CLAIMED -> SUBMITTED -> VERIFIED -> PAID
    """


# Alias for backwards compatibility with task_pipeline.py
StateTransitionError = InvalidStateTransitionError


class PermissionDeniedError(AgentMarketError):
    """Actor lacks permission for action."""


class ImmutableFieldError(AgentMarketError):
    """Attempted to modify immutable metadata."""


class CABRGateError(AgentMarketError):
    """CABR score gate failed - distribution blocked."""


class IdempotencyError(AgentMarketError):
    """Operation already completed - duplicate request detected."""


class RewardConstraintError(AgentMarketError):
    """Reward amount violates constraints (zero, negative, exceeds budget)."""
