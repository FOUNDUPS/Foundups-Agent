# -*- coding: utf-8 -*-
"""
RedDog Compute Governor (P4)

Routes compression decisions BEFORE tool execution. Governor classifies command
intent but cannot prove output safety. No pre-output decision may authorize
real compression.

CRITICAL: ALLOW_EVALUATION_DRY_RUN means "candidate for RTK dry-run evaluation,"
NOT "compression approved." Final compression requires output-level bypass check.

Contract: docs/contracts/REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1.md Section 2
WSP: WSP_97 (truth boundary), WSP_99 (M2M protocol)

WSP_97 Truth Labels:
- OBSERVED: P1 bypass classifier, P2 fidelity gate, P3 telemetry service exist
- INFERRED: Pre-tool governor can classify command intent, not prove output safety
- SPECIFIED_NOT_IMPLEMENTED: RTK integration (P5/P6)

Truth Boundary Checklist:
- NO_RTK_DEPENDENCY: no RTK binary or subprocess
- NO_COMMAND_EXECUTION: no shell/subprocess calls
- NO_COMPRESSION_PERFORMED: routing decision only
- NO_COMPRESSION_AUTHORITY: ALLOW_EVALUATION_DRY_RUN != approval
- NO_HOLOINDEX_MUTATION: query-only reference
- NO_OPENCLAW_HERMES_WRE_WIRING: no execution integration
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

from .bypass_classifier import BypassClassifier, BypassClass, get_bypass_classifier
from .telemetry_service import (
    TokenCompressionEvent,
    SourceLayer,
    Operation,
    ContentType,
    build_token_compression_event,
    get_telemetry_store,
)


class Phase(Enum):
    """Governor decision phase."""
    PRE_OUTPUT = "PRE_OUTPUT"
    OUTPUT_PREVIEW = "OUTPUT_PREVIEW"


class Routing(Enum):
    """Routing decision - NOT compression authority."""
    ALLOW_EVALUATION_DRY_RUN = "ALLOW_EVALUATION_DRY_RUN"  # Candidate only, not approval
    BYPASS_REQUIRED = "BYPASS_REQUIRED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECT = "REJECT"


class CommandType(Enum):
    """Known command types for classification."""
    GIT = "git"
    PYTEST = "pytest"
    NPM = "npm"
    PIP = "pip"
    PYTHON = "python"
    LS = "ls"
    ECHO = "echo"
    CAT = "cat"
    GREP = "grep"
    FIND = "find"
    GH = "gh"
    AZ = "az"
    AWS = "aws"
    KUBECTL = "kubectl"
    DOCKER = "docker"
    CURL = "curl"
    WGET = "wget"
    SSH = "ssh"
    SCP = "scp"
    OPENSSL = "openssl"
    GPG = "gpg"
    UNKNOWN = "unknown"


# Commands that ALWAYS require bypass (security/auth/provenance)
BYPASS_COMMANDS = frozenset([
    "npm audit", "npm outdated", "pip audit", "safety check",
    "git secrets", "git-secrets", "gitleaks", "trufflehog",
    "gh auth", "az login", "aws configure", "aws sts",
    "kubectl config", "kubectl auth",
    "ssh-keygen", "ssh-add", "gpg --gen-key", "gpg --export",
    "openssl genrsa", "openssl req", "openssl x509",
    "docker login", "docker secret",
])

# Command prefixes that indicate bypass
BYPASS_PREFIXES = frozenset([
    "gh auth", "az login", "aws sts", "aws secretsmanager",
    "kubectl get secret", "kubectl describe secret",
    "vault ", "1password ", "op ",
])

# Safe commands (evaluation candidates, NOT compression authority)
SAFE_COMMANDS = frozenset([
    "ls", "dir", "echo", "cat", "head", "tail", "wc",
    "pwd", "cd", "mkdir", "touch", "cp", "mv",
    "grep", "find", "which", "type", "env",
    "date", "cal", "uptime", "whoami", "hostname",
    "python --version", "node --version", "npm --version",
    "git status", "git branch", "git log", "git diff",
    "pytest --collect-only", "pip list", "pip show",
])


def compute_command_digest(command: str) -> str:
    """Compute SHA256 digest of command (never store raw)."""
    return hashlib.sha256(command.encode("utf-8")).hexdigest()


def redact_command(command: str) -> str:
    """
    Create redacted summary of command for logging.

    Preserves command structure, redacts potential secrets.
    """
    # Redact anything that looks like a token/key/password
    redacted = re.sub(
        r'(token|key|password|secret|auth|credential|api[_-]?key)[\s=:]+\S+',
        r'\1=***',
        command,
        flags=re.IGNORECASE
    )
    # Redact quoted strings that might be secrets
    redacted = re.sub(r'"[^"]{20,}"', '"***"', redacted)
    redacted = re.sub(r"'[^']{20,}'", "'***'", redacted)
    # Truncate long commands
    if len(redacted) > 100:
        redacted = redacted[:97] + "..."
    return redacted


def extract_command_type(command: str) -> CommandType:
    """Extract command type from command string."""
    cmd = command.strip().lower()

    # Check exact matches first
    for ct in CommandType:
        if ct == CommandType.UNKNOWN:
            continue
        if cmd.startswith(ct.value + " ") or cmd == ct.value:
            return ct

    # Check common patterns
    if cmd.startswith("python") or cmd.startswith("py "):
        return CommandType.PYTHON
    if cmd.startswith("npm ") or cmd.startswith("npx "):
        return CommandType.NPM
    if cmd.startswith("pip ") or cmd.startswith("pip3 "):
        return CommandType.PIP

    return CommandType.UNKNOWN


def is_bypass_command(command: str) -> tuple[bool, str | None]:
    """
    Check if command requires bypass.

    Returns (True, bypass_class) or (False, None).
    """
    cmd_lower = command.lower().strip()

    # Check exact bypass commands
    for bc in BYPASS_COMMANDS:
        if bc in cmd_lower:
            return True, "BYPASS_SECURITY"

    # Check bypass prefixes
    for prefix in BYPASS_PREFIXES:
        if cmd_lower.startswith(prefix):
            return True, "BYPASS_AUTH"

    # Check for auth/credential patterns in command
    auth_patterns = ["--token", "--password", "--secret", "--key", "--credential", "--auth"]
    for pattern in auth_patterns:
        if pattern in cmd_lower:
            return True, "BYPASS_AUTH"

    return False, None


def is_safe_command(command: str) -> bool:
    """Check if command is in the safe list (evaluation candidate)."""
    cmd_lower = command.lower().strip()

    for safe in SAFE_COMMANDS:
        if cmd_lower.startswith(safe):
            return True

    return False


@dataclass
class RedDogComputeDecision:
    """
    Governor routing decision.

    CRITICAL: ALLOW_EVALUATION_DRY_RUN is NOT compression authority.
    It means "candidate for RTK dry-run evaluation" only.
    Final compression requires output-level bypass classification.
    """
    # Identity
    decision_id: str
    timestamp: int

    # Command info (never raw command)
    command_digest: str
    command_redacted_summary: str
    command_type: CommandType

    # Decision
    phase: Phase
    routing: Routing
    bypass_class: str | None = None
    confidence: float = 0.0

    # Telemetry
    telemetry_event_id: str | None = None

    # Context
    ctx_holo_present: bool = False
    index_gap_detected: bool = False

    # Invariants (must always be these values)
    runtime_reindex_allowed: bool = False
    no_command_execution: bool = True
    no_rtk_invocation: bool = True
    no_compression_performed: bool = True

    # Reasons
    reason_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary (raw command never included)."""
        d = asdict(self)
        d["command_type"] = self.command_type.value
        d["phase"] = self.phase.value
        d["routing"] = self.routing.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RedDogComputeDecision":
        """Deserialize from dictionary."""
        return cls(
            decision_id=d["decision_id"],
            timestamp=d["timestamp"],
            command_digest=d["command_digest"],
            command_redacted_summary=d["command_redacted_summary"],
            command_type=CommandType(d["command_type"]),
            phase=Phase(d["phase"]),
            routing=Routing(d["routing"]),
            bypass_class=d.get("bypass_class"),
            confidence=d.get("confidence", 0.0),
            telemetry_event_id=d.get("telemetry_event_id"),
            ctx_holo_present=d.get("ctx_holo_present", False),
            index_gap_detected=d.get("index_gap_detected", False),
            runtime_reindex_allowed=d.get("runtime_reindex_allowed", False),
            no_command_execution=d.get("no_command_execution", True),
            no_rtk_invocation=d.get("no_rtk_invocation", True),
            no_compression_performed=d.get("no_compression_performed", True),
            reason_codes=d.get("reason_codes", []),
        )

    def to_m2m_compact(self) -> str:
        """Emit as M2M compact format."""
        return (
            f"GOVERNOR:{self.decision_id[:8]} "
            f"PHASE:{self.phase.value} "
            f"ROUTING:{self.routing.value} "
            f"TYPE:{self.command_type.value} "
            f"CONF:{self.confidence:.2f} "
            f"BYPASS:{self.bypass_class or 'none'}"
        )

    def to_m2m_yaml(self) -> str:
        """Emit as M2M YAML format."""
        lines = [
            "REDDOG_COMPUTE_DECISION:",
            f"  decision_id: {self.decision_id}",
            f"  timestamp: {self.timestamp}",
            f"  command_digest: {self.command_digest[:16]}...",
            f"  command_redacted: {self.command_redacted_summary}",
            f"  command_type: {self.command_type.value}",
            f"  phase: {self.phase.value}",
            f"  routing: {self.routing.value}",
            f"  bypass_class: {self.bypass_class}",
            f"  confidence: {self.confidence:.4f}",
            f"  telemetry_event_id: {self.telemetry_event_id}",
            "  context:",
            f"    ctx_holo_present: {self.ctx_holo_present}",
            f"    index_gap_detected: {self.index_gap_detected}",
            "  invariants:",
            f"    runtime_reindex_allowed: {self.runtime_reindex_allowed}",
            f"    no_command_execution: {self.no_command_execution}",
            f"    no_rtk_invocation: {self.no_rtk_invocation}",
            f"    no_compression_performed: {self.no_compression_performed}",
            f"  reason_codes: {self.reason_codes}",
        ]
        return "\n".join(lines)


def generate_decision_id(command_digest: str, phase: Phase) -> str:
    """Generate deterministic decision ID."""
    content = f"{command_digest}:{phase.value}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]


class ComputeGovernorError(Exception):
    """Raised when governor encounters an error."""
    pass


class ComputeGovernor:
    """
    RedDog Compute Governor.

    Routes compression decisions but does NOT authorize compression.
    ALLOW_EVALUATION_DRY_RUN means candidate only.
    """

    def __init__(self):
        self.bypass_classifier = get_bypass_classifier()

    def classify_command_for_evaluation(
        self,
        command: str,
        *,
        ctx_holo_present: bool = False,
        index_gap_detected: bool = False,
    ) -> RedDogComputeDecision:
        """
        Classify command for potential compression evaluation.

        This is PRE_OUTPUT phase - no output exists yet.
        Result is NEVER compression authority, only evaluation candidacy.

        Args:
            command: Raw command string (used ephemerally, never stored)
            ctx_holo_present: Whether CTX.HOLO context exists
            index_gap_detected: Whether index gap was detected

        Returns:
            RedDogComputeDecision with routing recommendation
        """
        command_digest = compute_command_digest(command)
        command_redacted = redact_command(command)
        command_type = extract_command_type(command)
        decision_id = generate_decision_id(command_digest, Phase.PRE_OUTPUT)
        timestamp = int(time.time())
        reason_codes = []

        # Check for invariant violations that require REJECT
        if index_gap_detected:
            # Check if this is a security-sensitive context
            is_bypass, bypass_class = is_bypass_command(command)
            if is_bypass:
                reason_codes.append("INDEX_GAP_ON_SECURITY_CONTEXT")
                return RedDogComputeDecision(
                    decision_id=decision_id,
                    timestamp=timestamp,
                    command_digest=command_digest,
                    command_redacted_summary=command_redacted,
                    command_type=command_type,
                    phase=Phase.PRE_OUTPUT,
                    routing=Routing.REJECT,
                    bypass_class=bypass_class,
                    confidence=1.0,
                    ctx_holo_present=ctx_holo_present,
                    index_gap_detected=index_gap_detected,
                    reason_codes=reason_codes,
                )

        # Check if command requires bypass
        is_bypass, bypass_class = is_bypass_command(command)
        if is_bypass:
            reason_codes.append("COMMAND_REQUIRES_BYPASS")
            return RedDogComputeDecision(
                decision_id=decision_id,
                timestamp=timestamp,
                command_digest=command_digest,
                command_redacted_summary=command_redacted,
                command_type=command_type,
                phase=Phase.PRE_OUTPUT,
                routing=Routing.BYPASS_REQUIRED,
                bypass_class=bypass_class,
                confidence=0.95,
                ctx_holo_present=ctx_holo_present,
                index_gap_detected=index_gap_detected,
                reason_codes=reason_codes,
            )

        # Check if command is in safe list
        if is_safe_command(command):
            reason_codes.append("SAFE_COMMAND_EVALUATION_CANDIDATE")
            return RedDogComputeDecision(
                decision_id=decision_id,
                timestamp=timestamp,
                command_digest=command_digest,
                command_redacted_summary=command_redacted,
                command_type=command_type,
                phase=Phase.PRE_OUTPUT,
                routing=Routing.ALLOW_EVALUATION_DRY_RUN,  # NOT compression authority
                bypass_class=None,
                confidence=0.8,
                ctx_holo_present=ctx_holo_present,
                index_gap_detected=index_gap_detected,
                reason_codes=reason_codes,
            )

        # Unknown command -> NEEDS_REVIEW
        reason_codes.append("UNKNOWN_COMMAND")
        return RedDogComputeDecision(
            decision_id=decision_id,
            timestamp=timestamp,
            command_digest=command_digest,
            command_redacted_summary=command_redacted,
            command_type=command_type,
            phase=Phase.PRE_OUTPUT,
            routing=Routing.NEEDS_REVIEW,
            bypass_class=None,
            confidence=0.5,
            ctx_holo_present=ctx_holo_present,
            index_gap_detected=index_gap_detected,
            reason_codes=reason_codes,
        )

    def get_routing_recommendation(
        self,
        command: str,
        output_preview: str | None = None,
        *,
        ctx_holo_present: bool = False,
        index_gap_detected: bool = False,
    ) -> RedDogComputeDecision:
        """
        Get routing recommendation with optional output preview.

        If output_preview is provided, content-level bypass classification
        is performed and can OVERRIDE command-level classification.

        Args:
            command: Raw command string (ephemeral)
            output_preview: Optional output snippet for content check
            ctx_holo_present: Whether CTX.HOLO exists
            index_gap_detected: Whether index gap detected

        Returns:
            RedDogComputeDecision with routing recommendation
        """
        # Start with command-level classification
        decision = self.classify_command_for_evaluation(
            command,
            ctx_holo_present=ctx_holo_present,
            index_gap_detected=index_gap_detected,
        )

        # If no output preview, return command-level decision
        if output_preview is None:
            return decision

        # Output preview provided - check content-level bypass
        command_digest = decision.command_digest
        command_redacted = decision.command_redacted_summary
        command_type = decision.command_type
        decision_id = generate_decision_id(command_digest, Phase.OUTPUT_PREVIEW)
        timestamp = int(time.time())
        reason_codes = list(decision.reason_codes)
        reason_codes.append("OUTPUT_PREVIEW_CHECKED")

        # Check output content for bypass patterns
        bypass_decision = self.bypass_classifier.classify(
            command=command,
            output=output_preview,
        )

        if bypass_decision.bypassed:
            # Content-level bypass overrides command-level safety
            reason_codes.append("OUTPUT_CONTENT_REQUIRES_BYPASS")
            return RedDogComputeDecision(
                decision_id=decision_id,
                timestamp=timestamp,
                command_digest=command_digest,
                command_redacted_summary=command_redacted,
                command_type=command_type,
                phase=Phase.OUTPUT_PREVIEW,
                routing=Routing.BYPASS_REQUIRED,
                bypass_class=bypass_decision.classification.value,
                confidence=bypass_decision.confidence,
                ctx_holo_present=ctx_holo_present,
                index_gap_detected=index_gap_detected,
                reason_codes=reason_codes,
            )

        # Output preview doesn't require bypass
        # Still only ALLOW_EVALUATION_DRY_RUN, not compression authority
        reason_codes.append("OUTPUT_PREVIEW_SAFE")
        return RedDogComputeDecision(
            decision_id=decision_id,
            timestamp=timestamp,
            command_digest=command_digest,
            command_redacted_summary=command_redacted,
            command_type=command_type,
            phase=Phase.OUTPUT_PREVIEW,
            routing=Routing.ALLOW_EVALUATION_DRY_RUN,
            bypass_class=None,
            confidence=0.85,
            ctx_holo_present=ctx_holo_present,
            index_gap_detected=index_gap_detected,
            reason_codes=reason_codes,
        )


def record_decision_telemetry(decision: RedDogComputeDecision) -> TokenCompressionEvent:
    """
    Record governor decision as telemetry event.

    Args:
        decision: The routing decision to record

    Returns:
        TokenCompressionEvent recorded to in-memory store
    """
    # Map routing to compression status
    from .telemetry_service import CompressionStatus

    if decision.routing == Routing.BYPASS_REQUIRED:
        status = CompressionStatus.BYPASSED
    elif decision.routing == Routing.REJECT:
        status = CompressionStatus.ERROR
    else:
        status = CompressionStatus.NOT_APPLICABLE  # Routing only, no compression

    event = build_token_compression_event(
        source_layer=SourceLayer.BYPASS_CLASSIFIER,  # Governor uses bypass classifier
        operation=Operation.CLASSIFY,
        content_type=ContentType.UNKNOWN,  # Command classification
        input_bytes=len(decision.command_digest),
        output_bytes=len(decision.command_digest),  # No size change (routing only)
        bypass_decision=decision.bypass_class,
        ctx_holo_present=decision.ctx_holo_present,
        index_gap_detected=decision.index_gap_detected,
    )

    # Record to store
    store = get_telemetry_store()
    store.record(event)

    return event


def validate_decision(decision: RedDogComputeDecision) -> tuple[bool, list[str]]:
    """
    Validate decision invariants.

    Returns (valid, errors).
    """
    errors = []

    # Invariant: runtime_reindex_allowed must be False
    if decision.runtime_reindex_allowed:
        errors.append("runtime_reindex_allowed must be False")

    # Invariant: no_command_execution must be True
    if not decision.no_command_execution:
        errors.append("no_command_execution must be True")

    # Invariant: no_rtk_invocation must be True
    if not decision.no_rtk_invocation:
        errors.append("no_rtk_invocation must be True")

    # Invariant: no_compression_performed must be True
    if not decision.no_compression_performed:
        errors.append("no_compression_performed must be True")

    # Check decision_id not empty
    if not decision.decision_id:
        errors.append("decision_id cannot be empty")

    # Check command_digest not empty
    if not decision.command_digest:
        errors.append("command_digest cannot be empty")

    return len(errors) == 0, errors


# Module singleton
_governor: ComputeGovernor | None = None


def get_compute_governor() -> ComputeGovernor:
    """Get or create the compute governor singleton."""
    global _governor
    if _governor is None:
        _governor = ComputeGovernor()
    return _governor


def reset_compute_governor() -> None:
    """Reset the compute governor (for tests)."""
    global _governor
    _governor = None
