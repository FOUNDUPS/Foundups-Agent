#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw FoundUp Orchestrator — Genesis Validation Gate.

Mandatory gate enforcing genesis envelope validation BEFORE any
FoundUp execution handoff to Hermes/Claw or FAM pipeline.

Architecture Flow (per REDDOG_FAM_GENESIS_FLOW_SPEC_PHASE1.md):
    012 outcome → RedDog → Genesis Envelope → [THIS GATE] → FAM/Hermes

WSP Compliance:
    WSP 97: Implementation Truth — reason codes are explicit, no fake claims
    WSP 15: Safety — blocking invalid requests before execution
    WSP 50: Pre-Action Verification — validate before mutate

Slice: OC3_GENESIS_VALIDATION_GATE_PHASE1
Worker: W3
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("openclaw_foundup_orchestrator")


# -----------------------------------------------------------------------------
# Failure Reason Codes (WSP 97 explicit)
# -----------------------------------------------------------------------------


class GenesisGateReason(Enum):
    """Explicit reason codes for gate block/allow decisions."""

    # Blocking reasons
    NO_ENVELOPE = "NO_ENVELOPE"  # No genesis envelope provided
    ENVELOPE_INVALID = "ENVELOPE_INVALID"  # Envelope failed validation
    LIFECYCLE_TOO_EARLY = "LIFECYCLE_TOO_EARLY"  # idea/genesis_envelope not allowed
    MISSING_ACCEPTANCE_CRITERIA = "MISSING_ACCEPTANCE_CRITERIA"
    MISSING_TRUTH_STATE = "MISSING_TRUTH_STATE"  # WSP 97 violation
    FOUNDUP_ID_INVALID = "FOUNDUP_ID_INVALID"  # WSP 104 violation
    EXTERNAL_REPO_PREMATURE = "EXTERNAL_REPO_PREMATURE"  # Can't request external at genesis
    BINDING_STATE_INVALID = "BINDING_STATE_INVALID"  # Wrong binding state for stage
    VALIDATOR_UNAVAILABLE = "VALIDATOR_UNAVAILABLE"  # Can't load validator
    ENVELOPE_PARSE_ERROR = "ENVELOPE_PARSE_ERROR"  # Malformed envelope data

    # Allow reasons
    GATE_PASSED = "GATE_PASSED"  # All checks passed
    BYPASS_AUTHORIZED = "BYPASS_AUTHORIZED"  # 012 emergency override


# -----------------------------------------------------------------------------
# Gate Result
# -----------------------------------------------------------------------------


@dataclass
class GenesisGateResult:
    """Result of genesis validation gate check.

    Attributes:
        allowed: Whether execution can proceed
        reason: Primary reason code
        errors: List of validation errors (if blocked)
        warnings: Non-blocking issues (for logging)
        envelope_summary: Summary of validated envelope (if allowed)
        checked_at: Timestamp of gate check
        checked_by: Identifier of gate checker
    """

    allowed: bool
    reason: GenesisGateReason
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    envelope_summary: Optional[Dict[str, Any]] = None
    checked_at: datetime = field(default_factory=datetime.now)
    checked_by: str = "openclaw_genesis_gate"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging/audit."""
        return {
            "allowed": self.allowed,
            "reason": self.reason.value,
            "errors": self.errors,
            "warnings": self.warnings,
            "envelope_summary": self.envelope_summary,
            "checked_at": self.checked_at.isoformat(),
            "checked_by": self.checked_by,
        }


# -----------------------------------------------------------------------------
# Orchestrator
# -----------------------------------------------------------------------------


class OpenClawFoundUpOrchestrator:
    """
    OpenClaw orchestrator with mandatory genesis validation gate.

    This orchestrator sits between intent capture (RedDog/OpenClaw conversation)
    and execution handoff (FAM pipeline, Hermes build). It enforces that all
    FoundUp operations pass through genesis envelope validation first.

    Gate Enforcement Points:
        1. launch_foundup() — validates before FAM launch
        2. build_foundup() — validates before Hermes build
        3. promote_lifecycle() — validates before stage transition

    Security Model:
        - No execution without valid genesis envelope
        - Explicit reason codes for all blocks (WSP 97)
        - Audit trail via logging
        - 012 bypass requires explicit authorization flag
    """

    def __init__(
        self,
        strict_mode: bool = True,
        allow_012_bypass: bool = False,
    ):
        """
        Initialize orchestrator.

        Args:
            strict_mode: If True, warnings become blocking errors
            allow_012_bypass: If True, 012 can override gate (emergency only)
        """
        self.strict_mode = strict_mode
        self.allow_012_bypass = allow_012_bypass
        self._validator = None
        self._validator_loaded = False

        logger.info(
            "[GENESIS-GATE] Orchestrator initialized | strict=%s bypass=%s",
            strict_mode,
            allow_012_bypass,
        )

    def _get_validator(self):
        """Lazy-load genesis envelope validator from ai_overseer."""
        if self._validator_loaded:
            return self._validator

        try:
            from modules.ai_intelligence.ai_overseer.src.foundup_genesis.validator import (
                GenesisEnvelopeValidator,
            )

            self._validator = GenesisEnvelopeValidator(strict_mode=self.strict_mode)
            self._validator_loaded = True
            logger.info("[GENESIS-GATE] Validator loaded from ai_overseer")
            return self._validator
        except ImportError as exc:
            logger.error("[GENESIS-GATE] Failed to load validator: %s", exc)
            self._validator_loaded = True  # Don't retry
            return None

    def _get_envelope_class(self):
        """Get FoundUpGenesisEnvelope class for parsing."""
        try:
            from modules.ai_intelligence.ai_overseer.src.foundup_genesis.envelope import (
                FoundUpGenesisEnvelope,
            )

            return FoundUpGenesisEnvelope
        except ImportError:
            return None

    def validate_genesis_envelope(
        self,
        envelope_data: Dict[str, Any],
        actor_id: str = "openclaw",
        bypass_012: bool = False,
    ) -> GenesisGateResult:
        """
        Validate a genesis envelope before execution handoff.

        This is the primary gate method. All FoundUp operations must
        pass through this validation before proceeding.

        Args:
            envelope_data: Dict representation of FoundUpGenesisEnvelope
            actor_id: Who is requesting the validation
            bypass_012: If True and allow_012_bypass enabled, skip validation

        Returns:
            GenesisGateResult with allowed/blocked decision and reason
        """
        # 012 emergency bypass
        if bypass_012 and self.allow_012_bypass and actor_id == "012":
            logger.warning(
                "[GENESIS-GATE] 012 bypass authorized for envelope"
            )
            return GenesisGateResult(
                allowed=True,
                reason=GenesisGateReason.BYPASS_AUTHORIZED,
                envelope_summary={"foundup_id": envelope_data.get("foundup_id", "unknown")},
            )

        # Check 1: Envelope data present
        if not envelope_data:
            logger.warning("[GENESIS-GATE] BLOCKED: No envelope data")
            return GenesisGateResult(
                allowed=False,
                reason=GenesisGateReason.NO_ENVELOPE,
                errors=["No genesis envelope data provided"],
            )

        # Check 2: Validator available
        validator = self._get_validator()
        if validator is None:
            logger.error("[GENESIS-GATE] BLOCKED: Validator unavailable")
            return GenesisGateResult(
                allowed=False,
                reason=GenesisGateReason.VALIDATOR_UNAVAILABLE,
                errors=["Genesis envelope validator could not be loaded"],
            )

        # Check 3: Parse envelope
        envelope_class = self._get_envelope_class()
        if envelope_class is None:
            logger.error("[GENESIS-GATE] BLOCKED: Envelope class unavailable")
            return GenesisGateResult(
                allowed=False,
                reason=GenesisGateReason.VALIDATOR_UNAVAILABLE,
                errors=["FoundUpGenesisEnvelope class could not be loaded"],
            )

        try:
            envelope = envelope_class.from_dict(envelope_data)
        except Exception as exc:
            logger.warning("[GENESIS-GATE] BLOCKED: Parse error: %s", exc)
            return GenesisGateResult(
                allowed=False,
                reason=GenesisGateReason.ENVELOPE_PARSE_ERROR,
                errors=[f"Failed to parse envelope: {exc}"],
            )

        # Check 4: Run validator
        validation_result = validator.validate(envelope)

        if not validation_result.is_valid:
            logger.warning(
                "[GENESIS-GATE] BLOCKED: Validation failed for %s | errors=%d",
                envelope.foundup_id,
                len(validation_result.errors),
            )
            # Map validator errors to specific reason codes
            reason = self._classify_validation_errors(validation_result.errors)
            return GenesisGateResult(
                allowed=False,
                reason=reason,
                errors=validation_result.errors,
                warnings=validation_result.warnings,
                envelope_summary={"foundup_id": envelope.foundup_id},
            )

        # All checks passed
        logger.info(
            "[GENESIS-GATE] ALLOWED: %s | passed=%d checks",
            envelope.foundup_id,
            len(validation_result.passed_checks),
        )
        return GenesisGateResult(
            allowed=True,
            reason=GenesisGateReason.GATE_PASSED,
            warnings=validation_result.warnings,
            envelope_summary={
                "foundup_id": envelope.foundup_id,
                "name": envelope.name,
                "category": envelope.category,
                "lifecycle_stage": envelope.lifecycle_stage.value,
                "binding_state": envelope.binding_state.value,
                "acceptance_criteria_count": len(envelope.acceptance_criteria),
                "truth_state_entries": len(envelope.truth_state_map),
                "is_valid": True,
            },
        )

    def _classify_validation_errors(self, errors: List[str]) -> GenesisGateReason:
        """Map validation errors to the most specific reason code."""
        error_text = " ".join(errors).lower()

        if "foundup_id" in error_text and ("invalid" in error_text or "format" in error_text):
            return GenesisGateReason.FOUNDUP_ID_INVALID
        if "lifecycle_stage" in error_text:
            return GenesisGateReason.LIFECYCLE_TOO_EARLY
        if "acceptance_criteria" in error_text:
            return GenesisGateReason.MISSING_ACCEPTANCE_CRITERIA
        if "truth_state" in error_text or "wsp 97" in error_text:
            return GenesisGateReason.MISSING_TRUTH_STATE
        if "external_repo" in error_text:
            return GenesisGateReason.EXTERNAL_REPO_PREMATURE
        if "binding_state" in error_text:
            return GenesisGateReason.BINDING_STATE_INVALID

        return GenesisGateReason.ENVELOPE_INVALID

    # -------------------------------------------------------------------------
    # Gated Execution Methods
    # -------------------------------------------------------------------------

    def launch_foundup(
        self,
        envelope_data: Dict[str, Any],
        actor_id: str = "openclaw",
        bypass_012: bool = False,
    ) -> Dict[str, Any]:
        """
        Launch a FoundUp with mandatory genesis validation.

        Gate: validate_genesis_envelope must pass before FAM handoff.

        Args:
            envelope_data: Genesis envelope as dict
            actor_id: Who is launching
            bypass_012: Emergency bypass flag

        Returns:
            Dict with success/blocked status and details
        """
        # Gate check
        gate_result = self.validate_genesis_envelope(
            envelope_data, actor_id, bypass_012
        )

        if not gate_result.allowed:
            return {
                "success": False,
                "blocked": True,
                "gate_result": gate_result.to_dict(),
                "action": "launch_foundup",
                "next_steps": self._suggest_remediation(gate_result),
            }

        # Gate passed — proceed to FAM
        # NOTE: Actual FAM handoff would go here
        # For this slice, we return the gate-passed result
        logger.info(
            "[GENESIS-GATE] Launch authorized for %s",
            gate_result.envelope_summary.get("foundup_id"),
        )
        return {
            "success": True,
            "blocked": False,
            "gate_result": gate_result.to_dict(),
            "action": "launch_foundup",
            "status": "GENESIS_VALIDATED_READY_FOR_FAM",
            "envelope_summary": gate_result.envelope_summary,
        }

    def build_foundup(
        self,
        envelope_data: Dict[str, Any],
        actor_id: str = "openclaw",
        bypass_012: bool = False,
    ) -> Dict[str, Any]:
        """
        Build a FoundUp with mandatory genesis validation.

        Gate: validate_genesis_envelope must pass before Hermes build.

        Per REDDOG_FAM_GENESIS_FLOW_SPEC Section 7.2:
        - Hermes DOES NOT accept raw chat as build spec
        - Hermes requires envelope_id
        - Hermes requires lifecycle_stage >= incubating

        Args:
            envelope_data: Genesis envelope as dict
            actor_id: Who is building
            bypass_012: Emergency bypass flag

        Returns:
            Dict with success/blocked status and details
        """
        # Gate check
        gate_result = self.validate_genesis_envelope(
            envelope_data, actor_id, bypass_012
        )

        if not gate_result.allowed:
            return {
                "success": False,
                "blocked": True,
                "gate_result": gate_result.to_dict(),
                "action": "build_foundup",
                "next_steps": self._suggest_remediation(gate_result),
            }

        # Additional build-specific check: lifecycle must be >= incubating
        lifecycle = gate_result.envelope_summary.get("lifecycle_stage", "idea")
        if lifecycle in ("idea",):
            logger.warning(
                "[GENESIS-GATE] Build blocked: lifecycle %s too early for Hermes",
                lifecycle,
            )
            return {
                "success": False,
                "blocked": True,
                "gate_result": {
                    "allowed": False,
                    "reason": GenesisGateReason.LIFECYCLE_TOO_EARLY.value,
                    "errors": [
                        f"lifecycle_stage '{lifecycle}' not ready for build. "
                        "Must be 'incubating' or later."
                    ],
                },
                "action": "build_foundup",
                "next_steps": [
                    "Complete genesis envelope validation",
                    "Transition to incubating stage via FAM",
                    "Then retry build request",
                ],
            }

        # Gate passed — ready for Hermes
        logger.info(
            "[GENESIS-GATE] Build authorized for %s",
            gate_result.envelope_summary.get("foundup_id"),
        )
        return {
            "success": True,
            "blocked": False,
            "gate_result": gate_result.to_dict(),
            "action": "build_foundup",
            "status": "GENESIS_VALIDATED_READY_FOR_HERMES",
            "envelope_summary": gate_result.envelope_summary,
        }

    def promote_lifecycle(
        self,
        envelope_data: Dict[str, Any],
        target_stage: str,
        actor_id: str = "openclaw",
    ) -> Dict[str, Any]:
        """
        Promote FoundUp lifecycle stage with validation.

        Gate: Genesis envelope must be valid AND promotion rules must be met.

        Args:
            envelope_data: Genesis envelope as dict
            target_stage: Target lifecycle stage
            actor_id: Who is promoting

        Returns:
            Dict with success/blocked status and details
        """
        # Gate check
        gate_result = self.validate_genesis_envelope(envelope_data, actor_id)

        if not gate_result.allowed:
            return {
                "success": False,
                "blocked": True,
                "gate_result": gate_result.to_dict(),
                "action": "promote_lifecycle",
                "target_stage": target_stage,
                "next_steps": self._suggest_remediation(gate_result),
            }

        # Lifecycle promotion is delegated to FAM
        # This gate only ensures the envelope is valid
        logger.info(
            "[GENESIS-GATE] Promotion check passed for %s -> %s",
            gate_result.envelope_summary.get("foundup_id"),
            target_stage,
        )
        return {
            "success": True,
            "blocked": False,
            "gate_result": gate_result.to_dict(),
            "action": "promote_lifecycle",
            "target_stage": target_stage,
            "status": "GENESIS_VALIDATED_PROMOTION_READY",
            "envelope_summary": gate_result.envelope_summary,
        }

    def _suggest_remediation(self, gate_result: GenesisGateResult) -> List[str]:
        """Suggest remediation steps based on failure reason."""
        suggestions = {
            GenesisGateReason.NO_ENVELOPE: [
                "Create a FoundUpGenesisEnvelope via RedDog intake",
                "Ensure envelope is passed to orchestrator",
            ],
            GenesisGateReason.ENVELOPE_INVALID: [
                "Review validation errors",
                "Fix envelope fields per WSP 104 and WSP 97",
                "Re-validate with GenesisEnvelopeValidator",
            ],
            GenesisGateReason.LIFECYCLE_TOO_EARLY: [
                "Lifecycle must be 'incubating' or later for execution",
                "Complete FAM registration to transition from genesis_envelope",
            ],
            GenesisGateReason.MISSING_ACCEPTANCE_CRITERIA: [
                "Add acceptance criteria with observable, method, oracle, pass_condition",
                "FoundUps require testable criteria before implementation",
            ],
            GenesisGateReason.MISSING_TRUTH_STATE: [
                "Add truth_state_map entries for all features",
                "Use WSP 97 markers: IDEA_ONLY, SPECIFIED, FUTURE_PHASE at genesis",
            ],
            GenesisGateReason.FOUNDUP_ID_INVALID: [
                "foundup_id must be 3-50 chars, lowercase letters/digits/underscores",
                "Must start with a letter (WSP 104 format)",
            ],
            GenesisGateReason.EXTERNAL_REPO_PREMATURE: [
                "external_repo_requested must be False at genesis",
                "Repo provisioning happens after proto stage",
            ],
            GenesisGateReason.BINDING_STATE_INVALID: [
                "binding_state at genesis must be 'unbound' or 'discoverable_only'",
                "'conditional' and 'ready' require implementation evidence",
            ],
            GenesisGateReason.VALIDATOR_UNAVAILABLE: [
                "Check ai_overseer module installation",
                "Verify foundup_genesis package is importable",
            ],
            GenesisGateReason.ENVELOPE_PARSE_ERROR: [
                "Check envelope data format",
                "Ensure all required fields are present",
                "Use FoundUpGenesisEnvelope.to_dict() output as reference",
            ],
        }

        return suggestions.get(gate_result.reason, ["Review validation errors"])


# -----------------------------------------------------------------------------
# Module-Level Convenience Functions
# -----------------------------------------------------------------------------

_orchestrator: Optional[OpenClawFoundUpOrchestrator] = None


def get_orchestrator(
    strict_mode: bool = True,
    allow_012_bypass: bool = False,
) -> OpenClawFoundUpOrchestrator:
    """Get or create the singleton orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = OpenClawFoundUpOrchestrator(
            strict_mode=strict_mode,
            allow_012_bypass=allow_012_bypass,
        )
    return _orchestrator


def validate_genesis_before_execution(
    envelope_data: Dict[str, Any],
    actor_id: str = "openclaw",
) -> GenesisGateResult:
    """
    Convenience function for genesis gate validation.

    Use this as the primary entry point for gate checks.
    """
    return get_orchestrator().validate_genesis_envelope(envelope_data, actor_id)


# -----------------------------------------------------------------------------
# Runtime Dispatch Entrypoint (OC1 Wiring)
# -----------------------------------------------------------------------------


def dispatch_foundup(dae: Any, intent: Any) -> str:
    """
    Dispatch FOUNDUP intent through orchestrator entrypoint.

    Phase 1: Routes all intents to FAM adapter with safe fallback.
    Phase 2+ will add genesis validation gate before FAM handoff.

    WSP 97 Note: This dispatch does NOT claim genesis validation is enforced.
    Genesis gate (OC3) is available but not mandatory in Phase 1.

    Args:
        dae: OpenClawDAE instance
        intent: Classified OpenClawIntent

    Returns:
        Response string from FAM adapter or fallback message
    """
    route_decision = {"route": "fam_adapter", "reason": "phase1_passthrough"}

    logger.info(
        "[OPENCLAW-FOUNDUP-ORCH] dispatch | route=%s reason=%s sender=%s",
        route_decision["route"],
        route_decision["reason"],
        intent.sender,
    )

    # Phase 1: Direct FAM handoff with preserved fallback behavior
    try:
        from .fam_adapter import handle_fam_intent

        response = handle_fam_intent(intent.raw_message, intent.sender)
        logger.info(
            "[OPENCLAW-FOUNDUP-ORCH] fam_complete | route=%s len=%d",
            route_decision["route"],
            len(response) if response else 0,
        )
        return response
    except ImportError as exc:
        logger.warning("[OPENCLAW-FOUNDUP-ORCH] fam_unavailable | error=%s", exc)
        return (
            "FoundUps Agent Market not available. "
            "Check that fam_adapter.py exists."
        )
    except Exception as exc:
        logger.error("[OPENCLAW-FOUNDUP-ORCH] fam_error | error=%s", exc)
        return f"FAM error: {exc}"
