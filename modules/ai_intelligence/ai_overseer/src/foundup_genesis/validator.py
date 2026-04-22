#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FoundUp Genesis Envelope Validator.

Validates envelopes against WSP rules BEFORE scaffold or implementation.
Prevents "vibes-based" development by enforcing testable criteria.

WSP Compliance:
    WSP 97: Implementation Truth — no claims without evidence
    WSP 104: Namespace Protocol — foundup_id format
    WSP 49: Module Structure — validates required fields

Pattern Sources:
    - modules/ai_intelligence/video_indexer/skillz/transcript_ask/validator.py
    - modules/foundups/tests/test_namespace_guardrail.py
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Set

from .envelope import (
    FoundUpGenesisEnvelope,
    LifecycleStage,
    BindingState,
    TruthMarker,
    is_valid_foundup_id,
)

logger = logging.getLogger(__name__)


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
        if not envelope.foundup_id:
            result.errors.append("foundup_id is required")
        elif not is_valid_foundup_id(envelope.foundup_id):
            result.errors.append(
                f"foundup_id '{envelope.foundup_id}' invalid format. "
                "Must be 3-50 chars, lowercase letters/digits/underscores, start with letter."
            )
        else:
            result.passed_checks.append("foundup_id_format")

        # Check 2: foundup_id not reserved
        if envelope.foundup_id in RESERVED_FOUNDUP_IDS:
            result.errors.append(
                f"foundup_id '{envelope.foundup_id}' is reserved (infrastructure or existing)"
            )
        elif envelope.foundup_id in self.existing_ids:
            result.errors.append(
                f"foundup_id '{envelope.foundup_id}' already exists"
            )
        else:
            result.passed_checks.append("foundup_id_not_reserved")

        # Check 3: lifecycle_stage is valid at genesis
        if envelope.lifecycle_stage not in VALID_GENESIS_STAGES:
            result.errors.append(
                f"lifecycle_stage '{envelope.lifecycle_stage.value}' not valid at genesis. "
                f"Must be one of: {[s.value for s in VALID_GENESIS_STAGES]}"
            )
        else:
            result.passed_checks.append("lifecycle_stage_valid")

        # Check 4: binding_state is valid at genesis
        if envelope.binding_state not in VALID_GENESIS_BINDING:
            result.errors.append(
                f"binding_state '{envelope.binding_state.value}' not valid at genesis. "
                f"Must be one of: {[s.value for s in VALID_GENESIS_BINDING]}"
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
            if ts.marker in {
                TruthMarker.IMPLEMENTED,
                TruthMarker.IMPLEMENTED_IN_TESTS,
                TruthMarker.PARTIAL,
            } and not ts.evidence:
                result.errors.append(
                    f"truth_state_map[{i}] '{ts.feature}' claims '{ts.marker.value}' "
                    "but has no evidence. WSP 97 violation."
                )

        if envelope.truth_state_map and not any(
            e for e in result.errors if "truth_state_map" in e
        ):
            result.passed_checks.append("truth_state_map_valid")

        # Check 10: category is valid
        if envelope.category and envelope.category.lower() not in VALID_CATEGORIES:
            result.warnings.append(
                f"category '{envelope.category}' not in standard list: {sorted(VALID_CATEGORIES)}"
            )
        else:
            result.passed_checks.append("category_valid")

        # Check 11: required fields are non-empty
        required_fields = ["name", "tagline", "description"]
        for fld in required_fields:
            val = getattr(envelope, fld, None)
            if not val or not val.strip():
                result.errors.append(f"'{fld}' is required and cannot be empty")
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
