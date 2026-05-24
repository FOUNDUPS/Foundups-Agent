"""
Quick Answer Generation for VoteBallots FoundUp.

Transforms confidence-scored funding summaries into max 3-line, evidence-backed
answers suitable for display in the p.fMALL Vote shell.

Design Principles:
- NO LLM calls - pure template-based generation
- NO new facts - only surfaces what confidence_scoring already labeled
- MAX 3 lines enforced at generation time
- Trail termination markers preserved in output
- Source references surfaced for transparency

WSP 97 Compliance:
- NO_LLM_CALL: Pure template generation, no AI
- NO_NEW_FACTS: Only surfaces existing confidence-scored data
- MAX_3_LINES_ENFORCED: Truncates with "..." and human review note
- HUMAN_REVIEW_FOR_HIGH_RISK_CLAIMS: Preserves review triggers
- TRAIL_TERMINATION_MARKERS_PRESERVED: Shows where evidence stops

Political Safety Boundaries:
- NO_TARGETED_PERSUASION
- NO_CANDIDATE_RECOMMENDATION
- NO_FOREIGN_FUNDING_CLAIM
- NO_DARK_MONEY_AS_VERIFIED_FACT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .confidence_scoring import (
    ConfidenceLabel,
    ConfidenceScoredFundingSummary,
    ConfidenceScoredFundingSource,
    ConfidenceScoringStatus,
    HumanReviewTrigger,
)


# =============================================================================
# Output Format Types
# =============================================================================


class AnswerFormat(Enum):
    """Output format for quick answers."""

    PLAIN_TEXT = "plain_text"
    """Plain text with no formatting markers."""

    MARKDOWN = "markdown"
    """Markdown with inline formatting."""

    SHELL_DISPLAY = "shell_display"
    """Format optimized for p.fMALL Vote shell display."""


# =============================================================================
# Confidence Indicators
# =============================================================================


_CONFIDENCE_INDICATORS = {
    ConfidenceLabel.VERIFIED_FACT: {
        "plain_text": "(verified)",
        "markdown": "[verified]",
        "shell_display": "[V]",
    },
    ConfidenceLabel.HIGH_CONFIDENCE_INFERENCE: {
        "plain_text": "(high confidence)",
        "markdown": "[high]",
        "shell_display": "[H]",
    },
    ConfidenceLabel.LOW_CONFIDENCE_INFERENCE: {
        "plain_text": "(low confidence)",
        "markdown": "[low]",
        "shell_display": "[L]",
    },
    ConfidenceLabel.UNKNOWN: {
        "plain_text": "(unknown)",
        "markdown": "[?]",
        "shell_display": "[?]",
    },
}


# =============================================================================
# Data Types
# =============================================================================


@dataclass
class QuickAnswer:
    """Generated answer with provenance tracking.

    Attributes:
        lines: Answer text lines (max 3 lines enforced).
        confidence_label: Overall confidence for the answer.
        requires_human_review: True if any source triggered human review.
        human_review_reasons: List of applicable review triggers.
        trail_terminated: True if evidence trail has termination markers.
        trail_termination_reason: Readable reason for trail termination.
        source_summary_id: Identifier for the source summary (candidate_id).
        truncated: True if content was truncated to fit max lines.
        original_line_count: Number of lines before truncation.
    """

    lines: List[str] = field(default_factory=list)
    confidence_label: ConfidenceLabel = ConfidenceLabel.UNKNOWN
    requires_human_review: bool = False
    human_review_reasons: List[HumanReviewTrigger] = field(default_factory=list)
    trail_terminated: bool = False
    trail_termination_reason: Optional[str] = None
    source_summary_id: str = ""
    truncated: bool = False
    original_line_count: int = 0

    @property
    def text(self) -> str:
        """Return answer as joined text."""
        return "\n".join(self.lines)

    @property
    def line_count(self) -> int:
        """Return number of lines in answer."""
        return len(self.lines)


# =============================================================================
# Template Constants
# =============================================================================


# Maximum lines for quick answer (WSP 97: MAX_3_LINES_ENFORCED)
MAX_LINES = 3

# Truncation indicator
TRUNCATION_INDICATOR = "..."

# Human review note appended when content is truncated
TRUNCATION_REVIEW_NOTE = "[more sources - see full report]"

# Human review warning prefix
HUMAN_REVIEW_PREFIX = "[!] "

# Trail termination prefix
TRAIL_TERMINATION_PREFIX = "[trail stops] "


# =============================================================================
# Formatting Functions
# =============================================================================


def _get_confidence_indicator(
    label: ConfidenceLabel,
    format: AnswerFormat,
) -> str:
    """Get confidence indicator string for label and format.

    Args:
        label: Confidence label to indicate.
        format: Output format.

    Returns:
        Confidence indicator string.
    """
    indicators = _CONFIDENCE_INDICATORS.get(label, _CONFIDENCE_INDICATORS[ConfidenceLabel.UNKNOWN])
    return indicators.get(format.value, indicators["plain_text"])


def format_funding_line(
    source_name: str,
    amount: float,
    confidence: ConfidenceLabel,
    format: AnswerFormat = AnswerFormat.PLAIN_TEXT,
) -> str:
    """Format a single funding source line with confidence indicator.

    Args:
        source_name: Name of the funding source.
        amount: Dollar amount from this source.
        confidence: Confidence label for this source.
        format: Output format.

    Returns:
        Formatted funding line string.
    """
    indicator = _get_confidence_indicator(confidence, format)

    if format == AnswerFormat.MARKDOWN:
        return f"- ${amount:,.0f} from {source_name} {indicator}"
    elif format == AnswerFormat.SHELL_DISPLAY:
        return f"{indicator} ${amount:,.0f} from {source_name}"
    else:  # PLAIN_TEXT
        return f"${amount:,.0f} from {source_name} {indicator}"


def format_total_line(
    total_raised: float,
    candidate_name: Optional[str],
    confidence: ConfidenceLabel,
    format: AnswerFormat = AnswerFormat.PLAIN_TEXT,
) -> str:
    """Format the total raised line.

    Args:
        total_raised: Total amount raised.
        candidate_name: Candidate name (optional).
        confidence: Overall confidence label.
        format: Output format.

    Returns:
        Formatted total line string.
    """
    indicator = _get_confidence_indicator(confidence, format)

    if candidate_name:
        if format == AnswerFormat.MARKDOWN:
            return f"**{candidate_name}** raised ${total_raised:,.0f} {indicator}"
        elif format == AnswerFormat.SHELL_DISPLAY:
            return f"{indicator} {candidate_name}: ${total_raised:,.0f} total"
        else:  # PLAIN_TEXT
            return f"{candidate_name} raised ${total_raised:,.0f} {indicator}"
    else:
        if format == AnswerFormat.SHELL_DISPLAY:
            return f"{indicator} Total raised: ${total_raised:,.0f}"
        else:
            return f"Total raised: ${total_raised:,.0f} {indicator}"


def format_trail_termination_line(
    reason: str,
    format: AnswerFormat = AnswerFormat.PLAIN_TEXT,
) -> str:
    """Format trail termination line.

    Args:
        reason: Trail termination reason.
        format: Output format.

    Returns:
        Formatted trail termination line.
    """
    if format == AnswerFormat.MARKDOWN:
        return f"*{TRAIL_TERMINATION_PREFIX}{reason}*"
    elif format == AnswerFormat.SHELL_DISPLAY:
        return f"[?] {reason}"
    else:  # PLAIN_TEXT
        return f"{TRAIL_TERMINATION_PREFIX}{reason}"


def format_human_review_line(
    triggers: List[HumanReviewTrigger],
    format: AnswerFormat = AnswerFormat.PLAIN_TEXT,
) -> str:
    """Format human review warning line.

    Args:
        triggers: List of human review triggers.
        format: Output format.

    Returns:
        Formatted human review line.
    """
    trigger_names = [t.value.replace("_", " ") for t in triggers[:2]]  # Max 2 reasons
    reason_text = ", ".join(trigger_names)

    if format == AnswerFormat.MARKDOWN:
        return f"**[Requires review]**: {reason_text}"
    elif format == AnswerFormat.SHELL_DISPLAY:
        return f"[!] Review needed: {reason_text}"
    else:  # PLAIN_TEXT
        return f"{HUMAN_REVIEW_PREFIX}Requires review: {reason_text}"


def truncate_with_review_note(
    lines: List[str],
    max_lines: int,
    has_more: bool,
) -> List[str]:
    """Truncate lines and add human review note if content was cut.

    Args:
        lines: Original lines.
        max_lines: Maximum lines allowed.
        has_more: True if there is more content beyond these lines.

    Returns:
        Truncated lines with review note if applicable.
    """
    if len(lines) <= max_lines and not has_more:
        return lines

    # Truncate to max_lines - 1 to leave room for truncation note
    if len(lines) >= max_lines:
        truncated = lines[: max_lines - 1]
        truncated.append(TRUNCATION_REVIEW_NOTE)
        return truncated
    else:
        # Lines fit but there's more content
        if has_more and len(lines) == max_lines:
            truncated = lines[: max_lines - 1]
            truncated.append(TRUNCATION_REVIEW_NOTE)
            return truncated
        return lines


# =============================================================================
# Core Generation Function
# =============================================================================


def generate_quick_answer(
    scored_summary: ConfidenceScoredFundingSummary,
    format: AnswerFormat = AnswerFormat.PLAIN_TEXT,
    max_lines: int = MAX_LINES,
) -> QuickAnswer:
    """Generate a quick answer from confidence-scored funding summary.

    Transforms a ConfidenceScoredFundingSummary into a max 3-line answer
    suitable for display. This function:
    - Uses ONLY template-based generation (NO LLM calls)
    - Surfaces ONLY existing confidence-scored data (NO new facts)
    - Enforces MAX 3 lines (truncates with review note)
    - Preserves human review triggers
    - Shows trail termination markers

    IMPORTANT: This function does NOT:
    - Call any LLM or AI model
    - Generate new facts or inferences
    - Make recommendations
    - Generate persuasion language
    - Exceed max_lines

    Args:
        scored_summary: Output from score_funding_summary_confidence().
        format: Output format (plain_text, markdown, shell_display).
        max_lines: Maximum lines in answer (default 3, enforced).

    Returns:
        QuickAnswer with max 3 lines, confidence label, and review flags.

    WSP 97 Compliance:
        NO_LLM_CALL - This is pure template generation.
        NO_NEW_FACTS - Only surfaces existing labeled data.
        MAX_3_LINES_ENFORCED - Truncates with review note.
    """
    # Enforce max_lines bounds
    max_lines = min(max(max_lines, 1), MAX_LINES)

    # Handle non-success status
    if not scored_summary.is_successful:
        error_msg = scored_summary.error_message or scored_summary.status.value
        return QuickAnswer(
            lines=[f"[Error] {error_msg}"],
            confidence_label=ConfidenceLabel.UNKNOWN,
            requires_human_review=True,
            human_review_reasons=[HumanReviewTrigger.TRAIL_TERMINATION_SIGNIFICANT],
            trail_terminated=True,
            trail_termination_reason="Data retrieval failed",
            source_summary_id=scored_summary.candidate_id or "",
        )

    # Build answer lines
    all_lines: List[str] = []

    # Line 1: Total raised (if available)
    if scored_summary.total_raised > 0:
        total_line = format_total_line(
            scored_summary.total_raised,
            scored_summary.candidate_name,
            scored_summary.overall_confidence,
            format,
        )
        all_lines.append(total_line)

    # Lines 2+: Top funding sources (up to 2 more)
    for source in scored_summary.scored_sources[:2]:
        source_line = format_funding_line(
            source.source_name,
            source.amount,
            source.confidence_label,
            format,
        )
        all_lines.append(source_line)

    # Determine if we have more content than can be shown
    has_more_sources = len(scored_summary.scored_sources) > 2
    has_trail_markers = len(scored_summary.trail_termination_markers) > 0
    has_human_review = scored_summary.human_review_required

    # Check if we need to add status lines
    status_lines_needed = []

    if has_human_review and len(scored_summary.all_human_review_triggers) > 0:
        review_line = format_human_review_line(
            scored_summary.all_human_review_triggers,
            format,
        )
        status_lines_needed.append(review_line)

    # Calculate total potential lines
    total_potential_lines = len(all_lines) + len(status_lines_needed)
    original_line_count = total_potential_lines

    # Determine if truncation is needed
    needs_truncation = total_potential_lines > max_lines or has_more_sources

    # Build final lines with truncation
    if needs_truncation:
        # Prioritize: total line, then sources, then truncation note
        if len(all_lines) >= max_lines:
            final_lines = all_lines[: max_lines - 1]
            final_lines.append(TRUNCATION_REVIEW_NOTE)
        elif len(all_lines) + 1 <= max_lines and has_more_sources:
            final_lines = all_lines[:]
            if len(final_lines) < max_lines:
                final_lines.append(TRUNCATION_REVIEW_NOTE)
        else:
            final_lines = truncate_with_review_note(all_lines, max_lines, has_more_sources)
    else:
        final_lines = all_lines[:]
        # Add status lines if they fit
        for status_line in status_lines_needed:
            if len(final_lines) < max_lines:
                final_lines.append(status_line)

    # Ensure we don't exceed max_lines
    final_lines = final_lines[:max_lines]

    # Determine trail termination info
    trail_terminated = len(scored_summary.trail_termination_markers) > 0
    trail_reason = None
    if trail_terminated and scored_summary.trail_termination_markers:
        # Use first marker as primary reason
        trail_reason = scored_summary.trail_termination_markers[0].value.replace("_", " ")

    return QuickAnswer(
        lines=final_lines,
        confidence_label=scored_summary.overall_confidence,
        requires_human_review=scored_summary.human_review_required,
        human_review_reasons=scored_summary.all_human_review_triggers,
        trail_terminated=trail_terminated,
        trail_termination_reason=trail_reason,
        source_summary_id=scored_summary.candidate_id or "",
        truncated=needs_truncation,
        original_line_count=original_line_count,
    )


# =============================================================================
# Convenience Functions
# =============================================================================


def generate_shell_answer(
    scored_summary: ConfidenceScoredFundingSummary,
) -> QuickAnswer:
    """Generate a quick answer optimized for p.fMALL shell display.

    Args:
        scored_summary: Output from score_funding_summary_confidence().

    Returns:
        QuickAnswer formatted for shell display.
    """
    return generate_quick_answer(scored_summary, format=AnswerFormat.SHELL_DISPLAY)


def generate_markdown_answer(
    scored_summary: ConfidenceScoredFundingSummary,
) -> QuickAnswer:
    """Generate a quick answer in markdown format.

    Args:
        scored_summary: Output from score_funding_summary_confidence().

    Returns:
        QuickAnswer formatted as markdown.
    """
    return generate_quick_answer(scored_summary, format=AnswerFormat.MARKDOWN)


def is_answer_ready_for_display(answer: QuickAnswer) -> bool:
    """Check if answer is ready for display without human review.

    Args:
        answer: QuickAnswer to check.

    Returns:
        True if answer can be displayed without human review.
    """
    # Not ready if human review is required
    if answer.requires_human_review:
        return False

    # Not ready if confidence is unknown
    if answer.confidence_label == ConfidenceLabel.UNKNOWN:
        return False

    # Not ready if no content
    if len(answer.lines) == 0:
        return False

    return True


def get_answer_confidence_summary(answer: QuickAnswer) -> str:
    """Get a brief confidence summary for the answer.

    Args:
        answer: QuickAnswer to summarize.

    Returns:
        Brief confidence summary string.
    """
    label = answer.confidence_label.value.replace("_", " ")

    if answer.requires_human_review:
        return f"{label} (review required)"
    elif answer.truncated:
        return f"{label} (truncated)"
    elif answer.trail_terminated:
        return f"{label} (trail stops)"
    else:
        return label
