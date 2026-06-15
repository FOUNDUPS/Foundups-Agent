"""
FoundUp Genesis — RedDog intake capability for AI Overseer.

Creates validated FoundUpGenesisEnvelope before any new FoundUp is scaffolded.
WSP 97: No implementation claims without evidence.

Modules:
    envelope: FoundUpGenesisEnvelope schema and dataclasses
    validator: Validates envelopes against WSP rules
    launch_request: Public intake seam -> produces the genesis envelope (gated)
"""

from .envelope import (
    FoundUpGenesisEnvelope,
    AcceptanceCriterion,
    TruthStateEntry,
    LifecycleStage,
    BindingState,
)
from .validator import (
    GenesisEnvelopeValidator,
    ValidationResult,
    validate_genesis_envelope,
)
from .launch_request import (
    LaunchRequest,
    LaunchRequestIntakeContext,
    LaunchValidationResult,
    LaunchRequestError,
    validate_launch_request,
    to_genesis_envelope,
)

__all__ = [
    "FoundUpGenesisEnvelope",
    "AcceptanceCriterion",
    "TruthStateEntry",
    "LifecycleStage",
    "BindingState",
    "GenesisEnvelopeValidator",
    "ValidationResult",
    "validate_genesis_envelope",
    "LaunchRequest",
    "LaunchRequestIntakeContext",
    "LaunchValidationResult",
    "LaunchRequestError",
    "validate_launch_request",
    "to_genesis_envelope",
]
