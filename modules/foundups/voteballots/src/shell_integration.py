"""
Shell Integration Layer for VoteBallots FoundUp.

Packages QuickAnswer data into a structured shell payload contract for
future p.fMALL Vote shell consumption. This is a LOCAL payload definition
only - it does NOT activate routes, modify manifests, or interact with
the actual shell runtime.

Design Principles:
- LOCAL_SHELL_PAYLOAD_ONLY: Defines payload structure, not shell behavior
- NO_PUBLIC_LAUNCH: No route activation or public surface changes
- NO_MANIFEST_MUTATION: foundup_manifest.json unchanged
- NO_LLM_CALL: Pure data transformation
- NO_NEW_FACTS: Only repackages existing QuickAnswer data

WSP 97 Compliance:
- ANSWER_LINES_PRESERVED: Lines copied exactly from QuickAnswer
- CONFIDENCE_LABELS_PRESERVED: Confidence label preserved
- SOURCE_TRACE_PRESERVED: Source summary ID preserved
- TRAIL_TERMINATION_MARKERS_PRESERVED: Trail termination preserved
- HUMAN_REVIEW_TRIGGER_PRESERVED: Review triggers preserved

Political Safety Boundaries:
- NO_TARGETED_PERSUASION
- NO_CANDIDATE_RECOMMENDATION
- NO_MICROTARGETING
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .confidence_scoring import ConfidenceLabel, HumanReviewTrigger
from .quick_answer import AnswerFormat, QuickAnswer, is_answer_ready_for_display


# =============================================================================
# Constants
# =============================================================================

# Canonical FoundUp identity (from foundup_manifest.json - NOT mutated)
FOUNDUP_ID = "voteballots"

# Route namespace per WSP 104 (from foundup_manifest.json - NOT mutated)
ROUTE_NAMESPACE = "/f/voteballots"

# App mount point (conventional path, NOT activated)
APP_MOUNT = "/f/voteballots/app"


# =============================================================================
# Status Enum
# =============================================================================


class ShellPayloadStatus(Enum):
    """Status of shell payload build operation."""

    SUCCESS = "success"
    """Payload built successfully, ready for shell consumption."""

    NOT_READY_FOR_DISPLAY = "not_ready_for_display"
    """QuickAnswer not ready for display (requires human review or unknown)."""

    EMPTY_ANSWER = "empty_answer"
    """QuickAnswer has no content lines."""

    INVALID_INPUT = "invalid_input"
    """Input QuickAnswer is None or malformed."""

    BUILD_ERROR = "build_error"
    """Unexpected error during payload build."""


# =============================================================================
# Data Types
# =============================================================================


@dataclass
class VoteShellPayload:
    """Shell payload contract for Vote quick answer display.

    This is a LOCAL data contract only. It defines the structured payload
    that would be sent to the p.fMALL Vote shell for rendering. This slice
    does NOT activate routes or interact with the actual shell.

    Attributes:
        status: Build operation status.
        foundup_id: Canonical FoundUp identifier ("voteballots").
        route_namespace: WSP 104 route namespace ("/f/voteballots").
        app_mount: Application mount point ("/f/voteballots/app").
        answer_format: Format used for answer generation.
        lines: Answer text lines (max 3, preserved exactly).
        confidence_label: Overall confidence classification.
        source_trace_id: Source summary ID for provenance.
        trail_termination_markers: List of trail termination reasons.
        human_review_required: True if human review is required.
        human_review_triggers: List of active review triggers.
        display_ready: True if payload is ready for immediate display.
        truncated: True if answer was truncated.
        warnings: List of warning messages for the shell.
        error_message: Error message if status is not SUCCESS.
    """

    status: ShellPayloadStatus = ShellPayloadStatus.SUCCESS
    foundup_id: str = FOUNDUP_ID
    route_namespace: str = ROUTE_NAMESPACE
    app_mount: str = APP_MOUNT
    answer_format: AnswerFormat = AnswerFormat.SHELL_DISPLAY
    lines: List[str] = field(default_factory=list)
    confidence_label: ConfidenceLabel = ConfidenceLabel.UNKNOWN
    source_trace_id: str = ""
    trail_termination_markers: List[str] = field(default_factory=list)
    human_review_required: bool = False
    human_review_triggers: List[HumanReviewTrigger] = field(default_factory=list)
    display_ready: bool = False
    truncated: bool = False
    warnings: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        """Return True if payload was built successfully."""
        return self.status == ShellPayloadStatus.SUCCESS

    @property
    def line_count(self) -> int:
        """Return number of answer lines."""
        return len(self.lines)

    def to_dict(self) -> dict:
        """Convert payload to dictionary for serialization.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return {
            "status": self.status.value,
            "foundup_id": self.foundup_id,
            "route_namespace": self.route_namespace,
            "app_mount": self.app_mount,
            "answer_format": self.answer_format.value,
            "lines": self.lines,
            "confidence_label": self.confidence_label.value,
            "source_trace_id": self.source_trace_id,
            "trail_termination_markers": self.trail_termination_markers,
            "human_review_required": self.human_review_required,
            "human_review_triggers": [t.value for t in self.human_review_triggers],
            "display_ready": self.display_ready,
            "truncated": self.truncated,
            "warnings": self.warnings,
            "error_message": self.error_message,
        }


# =============================================================================
# Validation Results
# =============================================================================


@dataclass
class PayloadValidationResult:
    """Result of payload validation.

    Attributes:
        valid: True if payload is valid.
        errors: List of validation errors.
        warnings: List of validation warnings.
    """

    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# =============================================================================
# Core Functions
# =============================================================================


def build_vote_shell_payload(
    answer: QuickAnswer,
    answer_format: AnswerFormat = AnswerFormat.SHELL_DISPLAY,
) -> VoteShellPayload:
    """Build a shell payload from a QuickAnswer.

    Packages QuickAnswer data into a structured shell payload contract.
    This function:
    - Preserves answer lines exactly (NO modification)
    - Preserves confidence labels
    - Preserves source trace ID
    - Preserves trail termination markers
    - Preserves human review triggers
    - Adds shell-specific routing metadata
    - Determines display readiness

    IMPORTANT: This function does NOT:
    - Activate any routes
    - Modify any manifests
    - Interact with shell runtime
    - Call any LLM or network
    - Generate new facts

    Args:
        answer: QuickAnswer from generate_quick_answer() or generate_shell_answer().
        answer_format: Format used for the answer (default SHELL_DISPLAY).

    Returns:
        VoteShellPayload with preserved data and routing metadata.

    WSP 97 Compliance:
        LOCAL_SHELL_PAYLOAD_ONLY - This is a data contract, not route activation.
        ANSWER_LINES_PRESERVED - Lines copied exactly.
        CONFIDENCE_LABELS_PRESERVED - Confidence label preserved.
    """
    # Handle None input
    if answer is None:
        return VoteShellPayload(
            status=ShellPayloadStatus.INVALID_INPUT,
            display_ready=False,
            error_message="QuickAnswer input is None",
        )

    # Handle empty answer
    if len(answer.lines) == 0:
        return VoteShellPayload(
            status=ShellPayloadStatus.EMPTY_ANSWER,
            confidence_label=answer.confidence_label,
            source_trace_id=answer.source_summary_id,
            human_review_required=answer.requires_human_review,
            human_review_triggers=list(answer.human_review_reasons),
            display_ready=False,
            error_message="QuickAnswer has no content lines",
        )

    # Check display readiness
    display_ready = is_answer_ready_for_display(answer)

    # Build warnings list
    warnings: List[str] = []

    if answer.truncated:
        warnings.append("Answer was truncated to fit display limits")

    if answer.trail_terminated:
        warnings.append(f"Evidence trail stopped: {answer.trail_termination_reason or 'unknown reason'}")

    if answer.requires_human_review and not display_ready:
        warnings.append("Human review required before display")

    if answer.confidence_label == ConfidenceLabel.UNKNOWN:
        warnings.append("Overall confidence is UNKNOWN")

    # Build trail termination markers list
    trail_markers: List[str] = []
    if answer.trail_terminated and answer.trail_termination_reason:
        trail_markers.append(answer.trail_termination_reason)

    # Determine status
    if display_ready:
        status = ShellPayloadStatus.SUCCESS
    else:
        status = ShellPayloadStatus.NOT_READY_FOR_DISPLAY

    return VoteShellPayload(
        status=status,
        foundup_id=FOUNDUP_ID,
        route_namespace=ROUTE_NAMESPACE,
        app_mount=APP_MOUNT,
        answer_format=answer_format,
        lines=list(answer.lines),  # Copy to avoid mutation
        confidence_label=answer.confidence_label,
        source_trace_id=answer.source_summary_id,
        trail_termination_markers=trail_markers,
        human_review_required=answer.requires_human_review,
        human_review_triggers=list(answer.human_review_reasons),
        display_ready=display_ready,
        truncated=answer.truncated,
        warnings=warnings,
        error_message=None if display_ready else "Answer not ready for display",
    )


def validate_vote_shell_payload(payload: VoteShellPayload) -> PayloadValidationResult:
    """Validate a VoteShellPayload for completeness and correctness.

    Checks that all required fields are present and valid. This validation
    is for the LOCAL payload contract - it does not validate against
    actual shell requirements.

    Args:
        payload: VoteShellPayload to validate.

    Returns:
        PayloadValidationResult with validation status, errors, and warnings.

    WSP 97 Compliance:
        LOCAL_SHELL_PAYLOAD_ONLY - Validates local contract, not shell.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Handle None input
    if payload is None:
        return PayloadValidationResult(
            valid=False,
            errors=["Payload is None"],
        )

    # Required field: foundup_id
    if not payload.foundup_id:
        errors.append("Missing required field: foundup_id")
    elif payload.foundup_id != FOUNDUP_ID:
        warnings.append(f"Unexpected foundup_id: {payload.foundup_id} (expected {FOUNDUP_ID})")

    # Required field: route_namespace
    if not payload.route_namespace:
        errors.append("Missing required field: route_namespace")
    elif payload.route_namespace != ROUTE_NAMESPACE:
        warnings.append(f"Unexpected route_namespace: {payload.route_namespace}")

    # Required field: app_mount
    if not payload.app_mount:
        errors.append("Missing required field: app_mount")

    # Content validation for SUCCESS status
    if payload.status == ShellPayloadStatus.SUCCESS:
        if len(payload.lines) == 0:
            errors.append("SUCCESS status but no answer lines")

        if not payload.display_ready:
            warnings.append("SUCCESS status but display_ready is False")

    # Human review consistency
    if payload.human_review_required and len(payload.human_review_triggers) == 0:
        warnings.append("human_review_required is True but no triggers specified")

    # Trail termination consistency
    if len(payload.trail_termination_markers) > 0 and payload.confidence_label == ConfidenceLabel.VERIFIED_FACT:
        warnings.append("Trail termination markers present but confidence is VERIFIED_FACT")

    return PayloadValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


# =============================================================================
# Convenience Functions
# =============================================================================


def build_ready_payload(answer: QuickAnswer) -> VoteShellPayload:
    """Build a shell payload only if answer is ready for display.

    Convenience function that returns a NOT_READY_FOR_DISPLAY payload
    if the answer would require human review.

    Args:
        answer: QuickAnswer to package.

    Returns:
        VoteShellPayload with appropriate status.
    """
    return build_vote_shell_payload(answer, AnswerFormat.SHELL_DISPLAY)


def is_payload_ready(payload: VoteShellPayload) -> bool:
    """Check if payload is ready for shell display.

    Args:
        payload: VoteShellPayload to check.

    Returns:
        True if payload is ready for display.
    """
    return (
        payload.status == ShellPayloadStatus.SUCCESS
        and payload.display_ready
        and len(payload.lines) > 0
    )


def get_payload_summary(payload: VoteShellPayload) -> str:
    """Get a brief summary of payload status.

    Args:
        payload: VoteShellPayload to summarize.

    Returns:
        Brief status summary string.
    """
    if payload.status == ShellPayloadStatus.SUCCESS:
        return f"Ready: {payload.line_count} lines, {payload.confidence_label.value}"
    elif payload.status == ShellPayloadStatus.NOT_READY_FOR_DISPLAY:
        if payload.human_review_required:
            return "Not ready: human review required"
        return "Not ready: display conditions not met"
    elif payload.status == ShellPayloadStatus.EMPTY_ANSWER:
        return "Not ready: empty answer"
    elif payload.status == ShellPayloadStatus.INVALID_INPUT:
        return "Error: invalid input"
    else:
        return f"Error: {payload.status.value}"
