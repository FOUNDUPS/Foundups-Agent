#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FoundUp Genesis Envelope Validator.

Validates envelopes against WSP rules BEFORE scaffold or implementation.
Prevents "vibes-based" development by enforcing testable criteria.

WSP Compliance:
    WSP 97: Implementation Truth -- no claims without evidence
    WSP 104: Namespace Protocol -- foundup_id format
    WSP 49: Module Structure -- validates required fields

Pattern Sources:
    - modules/ai_intelligence/video_indexer/skillz/transcript_ask/validator.py
    - modules/foundups/tests/test_namespace_guardrail.py
"""

from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass, field
from typing import Any, List, Optional, Set

from .envelope import (
    FoundUpGenesisEnvelope,
    LifecycleStage,
    BindingState,
    TruthMarker,
    is_valid_foundup_id,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Disallowed control / format character policy for PUBLIC DISPLAY fields
# (#823 -- ARCHITECT-pinned: reject, do NOT sanitize/strip/coerce).
# -----------------------------------------------------------------------------
#
# WHY: A public display field (proposed_name / tagline / description / etc.) is
# HOSTILE input. The #823 independent re-review found that a control char (e.g.
# U+0000) in proposed_name was ACCEPTED by the Phase-1 validators and then
# silently SANITIZED into a normal display name at envelope construction (via
# _normalize NFKC + redact_sensitive), producing a draft FoundUp with a
# laundered display name. The fix REJECTS such a value at validation time,
# BEFORE any envelope is constructed, and runs the detection on the RAW value
# BEFORE any normalization/redaction can hide the offending codepoint.
#
# POLICY (Addendum A -- PINNED; no open fork):
#   - Reject EVERY Unicode category Cc (C0 + C1 control). This single rule
#     already covers TAB U+0009, LF U+000A, CR U+000D, NUL U+0000, ESC U+001B,
#     DEL U+007F, and the C1 block U+0080-U+009F. Newline is therefore rejected
#     in description too (description is NOT exempt this phase).
#   - Reject this dangerous Unicode category Cf subset:
#       zero-width:  U+200B U+200C U+200D U+FEFF U+2060
#       bidi/isolate: U+202A U+202B U+202C U+202D U+202E
#                     U+2066 U+2067 U+2068 U+2069
#     (The rest of category Cf is NOT rejected this phase -- do not over-broaden.)
#
# This is deliberately NOT an ASCII-only rule: ordinary letters in any script
# (accented Latin, CJK, etc.), punctuation, and (if the validators already
# accept them) emoji are all category Lo/Ll/Lu/So/... and pass untouched. Only
# Cc and the pinned Cf codepoints are rejected.

# The dangerous Cf subset (zero-width joiners/spaces + bidi overrides/isolates).
_DISALLOWED_FORMAT_CODEPOINTS: Set[int] = frozenset({
    0x200B, 0x200C, 0x200D, 0xFEFF, 0x2060,            # zero-width
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,            # bidi embedding/override
    0x2066, 0x2067, 0x2068, 0x2069,                    # bidi isolates
})


def _contains_disallowed_display_char(s: str) -> bool:
    """True iff `s` contains a disallowed control/format codepoint (#823 policy).

    Detection is on the RAW value -- call this BEFORE any normalization/redaction
    so a laundering transform (NFKC / redact) can never hide the offending char.

    Rejects (Addendum A, PINNED):
      - any Unicode category Cc codepoint (C0 controls 0x00-0x1F incl. TAB/LF/CR,
        DEL 0x7F, and the C1 block 0x80-0x9F);
      - the dangerous Cf subset in _DISALLOWED_FORMAT_CODEPOINTS (zero-width
        U+200B/200C/200D/FEFF/2060; bidi/isolates U+202A-202E, U+2066-2069).

    A non-str argument is NOT this function's concern (callers reject non-strings
    via the field-type gate); for safety it returns False rather than raising.
    """
    if not isinstance(s, str):
        return False
    for ch in s:
        if unicodedata.category(ch) == "Cc":
            return True
        if ord(ch) in _DISALLOWED_FORMAT_CODEPOINTS:
            return True
    return False


def _reject_display_field(field_name: str, value: Any, errors: List[str]) -> None:
    """Append a SAFE rejection to `errors` if `value` is not a valid display string.

    A display field MUST be a string (Addendum B: a non-string present where a
    display value is expected is INVALID -> reject). If it is a string, it must
    not contain a disallowed control/format character (detected on the RAW value).

    The error names the field + policy class ONLY. It NEVER echoes the raw value,
    repr(value), the offending character, or any raw bytes (Addendum B: no leak).
    """
    if not isinstance(value, str):
        errors.append(
            f"{field_name} must be a string (non-string display field is invalid)"
        )
        return
    if _contains_disallowed_display_char(value):
        errors.append(
            f"{field_name} contains disallowed control/format character"
        )


# -----------------------------------------------------------------------------
# Validation Result
# -----------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """
    Result of envelope validation.

    Attributes:
        is_valid: Whether the envelope passed all checks
        errors: List of validation errors (blocking)
        warnings: List of validation warnings (non-blocking)
        passed_checks: List of checks that passed
    """
    is_valid: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    passed_checks: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "passed_checks": self.passed_checks,
        }


# -----------------------------------------------------------------------------
# Reserved IDs and Categories
# -----------------------------------------------------------------------------


# IDs that cannot be used (infrastructure, reserved, existing)
RESERVED_FOUNDUP_IDS: Set[str] = frozenset({
    # Infrastructure (never FoundUps)
    "openclaw", "wre", "holoindex", "holo_index", "pfmall", "hermes",
    "fam", "cabr", "dae", "mcp", "pavs",
    # Reserved prefixes
    "test", "tmp", "temp", "dev", "staging", "prod",
    # Existing FoundUps (check dynamically in production)
    "gotjunk_001", "kosei", "antifafm", "autopost", "science_swarm_hub",
})


# Valid categories per PFMALL_LAUNCH_CATALOG_TAXONOMY.md
VALID_CATEGORIES: Set[str] = frozenset({
    "marketplace", "media", "science", "games", "community",
    "tools", "education", "finance", "governance", "infrastructure",
    "uncategorized",
})


# Valid lifecycle stages at genesis
VALID_GENESIS_STAGES: Set[LifecycleStage] = frozenset({
    LifecycleStage.IDEA,
    LifecycleStage.INCUBATING,
})


# Valid binding states at genesis
VALID_GENESIS_BINDING: Set[BindingState] = frozenset({
    BindingState.UNBOUND,
    BindingState.DISCOVERABLE_ONLY,
})


# Truth markers that don't require evidence at genesis
GENESIS_TRUTH_MARKERS: Set[TruthMarker] = frozenset({
    TruthMarker.IDEA_ONLY,
    TruthMarker.SPECIFIED,
    TruthMarker.FUTURE_PHASE,
})


# -----------------------------------------------------------------------------
# Validator
# -----------------------------------------------------------------------------


class GenesisEnvelopeValidator:
    """
    Validates FoundUpGenesisEnvelope against WSP rules.

    Checks:
        1. foundup_id format (WSP 104)
        2. foundup_id not reserved
        3. lifecycle_stage is IDEA or INCUBATING only
        4. binding_state is UNBOUND or DISCOVERABLE_ONLY
        5. external_repo_requested is False
        6. acceptance_criteria have all four fields
        7. acceptance_criteria list is non-empty
        8. truth_state_map uses valid markers
        9. no implementation claims without evidence
        10. category is valid
        11. required fields are non-empty
    """

    def __init__(
        self,
        existing_ids: Optional[Set[str]] = None,
        strict_mode: bool = True,
    ):
        """
        Initialize validator.

        Args:
            existing_ids: Set of existing foundup_ids to check for conflicts
            strict_mode: If True, warnings become errors
        """
        self.existing_ids = existing_ids or set()
        self.strict_mode = strict_mode

    def validate(self, envelope: FoundUpGenesisEnvelope) -> ValidationResult:
        """
        Validate a genesis envelope.

        Returns:
            ValidationResult with errors, warnings, and passed checks.
        """
        result = ValidationResult()

        # Check 1: foundup_id format (WSP 104)
        # #428 leak fix (Addendum A): NEVER echo the raw foundup_id value. A
        # hand-built envelope can carry a control char in foundup_id; echoing it
        # would surface a raw control byte in the error string. The message names
        # the field + the rule ("invalid format" stable label) ONLY -- no raw
        # value, no repr(), no offending byte.
        if not envelope.foundup_id:
            result.errors.append("foundup_id is required")
        elif not is_valid_foundup_id(envelope.foundup_id):
            result.errors.append(
                "foundup_id has invalid format. "
                "Must be 3-50 chars, lowercase letters/digits/underscores, start with letter."
            )
        else:
            result.passed_checks.append("foundup_id_format")

        # Check 2: foundup_id not reserved
        # Field + rule label only; never echo the raw foundup_id (Addendum A).
        if envelope.foundup_id in RESERVED_FOUNDUP_IDS:
            result.errors.append(
                "foundup_id is reserved (infrastructure or existing)"
            )
        elif envelope.foundup_id in self.existing_ids:
            result.errors.append(
                "foundup_id already exists"
            )
        else:
            result.passed_checks.append("foundup_id_not_reserved")

        # Check 3: lifecycle_stage is valid at genesis
        # State the allowed-set NAMES only; do not echo the offending value
        # (Addendum A: field + policy + allowed-set names, never the input).
        if envelope.lifecycle_stage not in VALID_GENESIS_STAGES:
            result.errors.append(
                "lifecycle_stage not valid at genesis. "
                f"Must be one of: {sorted(s.value for s in VALID_GENESIS_STAGES)}"
            )
        else:
            result.passed_checks.append("lifecycle_stage_valid")

        # Check 4: binding_state is valid at genesis
        # Allowed-set names only; no echo of the offending value (Addendum A).
        if envelope.binding_state not in VALID_GENESIS_BINDING:
            result.errors.append(
                "binding_state not valid at genesis. "
                f"Must be one of: {sorted(s.value for s in VALID_GENESIS_BINDING)}"
            )
        else:
            result.passed_checks.append("binding_state_valid")

        # Check 5: external_repo_requested is False at genesis
        if envelope.external_repo_requested:
            result.errors.append(
                "external_repo_requested cannot be True at genesis. "
                "Must pass external-build-ready gate first."
            )
        else:
            result.passed_checks.append("external_repo_not_requested")

        # Check 6: acceptance_criteria have all four fields
        for i, ac in enumerate(envelope.acceptance_criteria):
            missing = []
            if not ac.observable:
                missing.append("observable")
            if not ac.method:
                missing.append("method")
            if not ac.oracle:
                missing.append("oracle")
            if not ac.pass_condition:
                missing.append("pass_condition")
            if missing:
                result.errors.append(
                    f"acceptance_criteria[{i}] missing fields: {missing}"
                )

        if envelope.acceptance_criteria and not any(
            e for e in result.errors if "acceptance_criteria" in e
        ):
            result.passed_checks.append("acceptance_criteria_complete")

        # Check 7: acceptance_criteria list is non-empty
        if not envelope.acceptance_criteria:
            result.warnings.append(
                "acceptance_criteria is empty. "
                "FoundUps should have testable acceptance criteria before implementation."
            )
        else:
            result.passed_checks.append("acceptance_criteria_present")

        # Check 8-9: truth_state_map validation
        for i, ts in enumerate(envelope.truth_state_map):
            if not ts.feature:
                result.errors.append(f"truth_state_map[{i}] missing feature name")
            # Check for implementation claims without evidence
            # Index + rule only; never echo the raw ts.feature value or the
            # marker value (Addendum A: feature is user-controlled free text).
            if ts.marker in {
                TruthMarker.IMPLEMENTED,
                TruthMarker.IMPLEMENTED_IN_TESTS,
                TruthMarker.PARTIAL,
            } and not ts.evidence:
                result.errors.append(
                    f"truth_state_map[{i}] claims an implementation marker "
                    "but has no evidence. WSP 97 violation."
                )

        if envelope.truth_state_map and not any(
            e for e in result.errors if "truth_state_map" in e
        ):
            result.passed_checks.append("truth_state_map_valid")

        # Check 10: category is valid
        # Allowed-set NAMES only; never echo the raw category value (Addendum A:
        # no "Invalid category: {category}" -- say "unknown category" + allowed set).
        if envelope.category and envelope.category.lower() not in VALID_CATEGORIES:
            result.warnings.append(
                "category is unknown (not in standard list). "
                f"Must be one of: {sorted(VALID_CATEGORIES)}"
            )
        else:
            result.passed_checks.append("category_valid")

        # Check 11: required display fields are non-empty AND carry no disallowed
        # control/format character (#823). These are PUBLIC display fields, so a
        # control char (Cc) or a dangerous format char (pinned Cf subset) is
        # REJECTED here -- detected on the RAW value, never sanitized. This is the
        # genesis-side line of defense for any caller that builds an envelope
        # directly (the intake path also rejects at validate_launch_request,
        # BEFORE this envelope is ever constructed).
        required_fields = ["name", "tagline", "description"]
        for fld in required_fields:
            val = getattr(envelope, fld, None)
            if not isinstance(val, str) or not val.strip():
                result.errors.append(f"'{fld}' is required and cannot be empty")
            elif _contains_disallowed_display_char(val):
                result.errors.append(
                    f"{fld} contains disallowed control/format character"
                )
            else:
                result.passed_checks.append(f"{fld}_present")

        # Strict mode: warnings become errors
        if self.strict_mode:
            result.errors.extend(result.warnings)
            result.warnings = []

        # Final verdict
        result.is_valid = len(result.errors) == 0

        # Update envelope with validation state
        envelope.is_valid = result.is_valid
        envelope.validation_errors = result.errors.copy()

        logger.info(
            "[GENESIS-VALIDATOR] %s: valid=%s, errors=%d, warnings=%d, passed=%d",
            envelope.foundup_id or "(no id)",
            result.is_valid,
            len(result.errors),
            len(result.warnings),
            len(result.passed_checks),
        )

        return result


# -----------------------------------------------------------------------------
# Convenience Function
# -----------------------------------------------------------------------------


def validate_genesis_envelope(
    envelope: FoundUpGenesisEnvelope,
    existing_ids: Optional[Set[str]] = None,
    strict_mode: bool = True,
) -> ValidationResult:
    """
    Validate a genesis envelope using default validator.

    Args:
        envelope: The envelope to validate
        existing_ids: Set of existing foundup_ids to check for conflicts
        strict_mode: If True, warnings become errors

    Returns:
        ValidationResult
    """
    validator = GenesisEnvelopeValidator(
        existing_ids=existing_ids,
        strict_mode=strict_mode,
    )
    return validator.validate(envelope)
