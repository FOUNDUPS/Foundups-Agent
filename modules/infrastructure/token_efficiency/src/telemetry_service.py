# -*- coding: utf-8 -*-
"""
Token Efficiency Telemetry Service (P3)

Records compression/fidelity events for token efficiency measurement.
In-memory only; no persistent storage in this slice.

Contract: docs/contracts/REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1.md Section 8
WSP: WSP_97 (truth boundary), WSP_99 (M2M protocol)

WSP_97 Truth Labels:
- OBSERVED: Contract Section 8a TokenCompressionEvent schema
- SPECIFIED_NOT_IMPLEMENTED: persistence (in-memory only for this slice)

Truth Boundary Checklist:
- NO_RTK_DEPENDENCY: no RTK binary or subprocess
- NO_COMMAND_EXECUTION: no shell/subprocess calls
- NO_SECRET_PERSISTENCE: only hashes/lengths, never raw content
- NO_HOLOINDEX_MUTATION: query-only reference
- NO_OPENCLAW_HERMES_WRE_WIRING: no execution integration
- IN_MEMORY_ONLY: no disk persistence
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class SourceLayer(Enum):
    """Source layer for telemetry events."""
    WSP99_M2M = "WSP99_M2M"
    RTK_EVALUATION = "RTK_EVALUATION"
    BYPASS_CLASSIFIER = "BYPASS_CLASSIFIER"
    FIDELITY_GATE = "FIDELITY_GATE"
    UNKNOWN = "UNKNOWN"


class Operation(Enum):
    """Operation type for telemetry events."""
    COMPILE = "compile"
    DECOMPILE = "decompile"
    CLASSIFY = "classify"
    EVALUATE = "evaluate"
    BYPASS = "bypass"
    FIDELITY_CHECK = "fidelity_check"


class ContentType(Enum):
    """Content type for telemetry events."""
    M2M_PROMPT = "m2m_prompt"
    TOOL_OUTPUT = "tool_output"
    RAW_REF = "raw_ref"
    UNKNOWN = "unknown"


class CompressionStatus(Enum):
    """Compression status."""
    COMPRESSED = "compressed"
    BYPASSED = "bypassed"
    UNCHANGED = "unchanged"
    ERROR = "error"
    NOT_APPLICABLE = "not_applicable"


# Token estimation: ~4 chars per token (conservative estimate)
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """
    Estimate token count from text.

    Uses a conservative 4 chars per token estimate.
    Returns 0 for empty text, never negative.

    Args:
        text: Input text to estimate

    Returns:
        Estimated token count (non-negative integer)
    """
    if not text:
        return 0
    # Ceiling division for conservative estimate
    return max(0, (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN)


def compute_content_hash(content: str) -> str:
    """
    Compute SHA256 hash of content.

    Args:
        content: Content to hash

    Returns:
        Hex digest of SHA256 hash
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass
class TokenCompressionEvent:
    """
    Telemetry event for token compression/efficiency measurement.

    Per Contract Section 8a TokenCompressionEvent schema.

    INVARIANTS (Section 8b):
    - NO_NEGATIVE_SAVINGS: bytes_saved/tokens_saved >= 0 for compressed
    - NO_CONTENT_IN_TELEMETRY: only hashes/lengths, never raw content
    - BYPASS_BEFORE_TELEMETRY: bypass decision recorded before metrics
    """
    # Identity
    event_id: str
    timestamp: int  # Unix timestamp

    # Source
    source_layer: SourceLayer
    operation: Operation
    content_type: ContentType

    # Input metrics (no raw content)
    input_bytes: int
    input_estimated_tokens: int

    # Output metrics
    output_bytes: int
    output_estimated_tokens: int

    # Savings (computed)
    bytes_saved: int
    tokens_saved: int
    savings_ratio: float  # 0.0 to 1.0

    # Status
    compression_status: CompressionStatus
    bypass_decision: str | None = None  # Bypass class if bypassed
    fidelity_status: str | None = None  # Fidelity check result

    # Context flags
    raw_ref_present: bool = False
    ctx_holo_present: bool = False
    index_gap_detected: bool = False

    # Safety invariants (must always be these values)
    runtime_reindex_allowed: bool = False
    no_command_execution: bool = True
    no_rtk_invocation: bool = True
    no_secret_persistence: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        d = asdict(self)
        d["source_layer"] = self.source_layer.value
        d["operation"] = self.operation.value
        d["content_type"] = self.content_type.value
        d["compression_status"] = self.compression_status.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TokenCompressionEvent":
        """Deserialize from dictionary."""
        return cls(
            event_id=d["event_id"],
            timestamp=d["timestamp"],
            source_layer=SourceLayer(d["source_layer"]),
            operation=Operation(d["operation"]),
            content_type=ContentType(d["content_type"]),
            input_bytes=d["input_bytes"],
            input_estimated_tokens=d["input_estimated_tokens"],
            output_bytes=d["output_bytes"],
            output_estimated_tokens=d["output_estimated_tokens"],
            bytes_saved=d["bytes_saved"],
            tokens_saved=d["tokens_saved"],
            savings_ratio=d["savings_ratio"],
            compression_status=CompressionStatus(d["compression_status"]),
            bypass_decision=d.get("bypass_decision"),
            fidelity_status=d.get("fidelity_status"),
            raw_ref_present=d.get("raw_ref_present", False),
            ctx_holo_present=d.get("ctx_holo_present", False),
            index_gap_detected=d.get("index_gap_detected", False),
            runtime_reindex_allowed=d.get("runtime_reindex_allowed", False),
            no_command_execution=d.get("no_command_execution", True),
            no_rtk_invocation=d.get("no_rtk_invocation", True),
            no_secret_persistence=d.get("no_secret_persistence", True),
        )

    def to_m2m_compact(self) -> str:
        """Emit as M2M compact format."""
        status = self.compression_status.value.upper()
        return (
            f"TELEMETRY:{self.event_id[:8]} "
            f"SRC:{self.source_layer.value} "
            f"OP:{self.operation.value} "
            f"STATUS:{status} "
            f"IN_TOK:{self.input_estimated_tokens} "
            f"OUT_TOK:{self.output_estimated_tokens} "
            f"SAVED:{self.tokens_saved} "
            f"RATIO:{self.savings_ratio:.3f}"
        )

    def to_m2m_yaml(self) -> str:
        """Emit as M2M YAML format."""
        lines = [
            "TOKEN_COMPRESSION_EVENT:",
            f"  event_id: {self.event_id}",
            f"  timestamp: {self.timestamp}",
            f"  source_layer: {self.source_layer.value}",
            f"  operation: {self.operation.value}",
            f"  content_type: {self.content_type.value}",
            f"  compression_status: {self.compression_status.value}",
            "  metrics:",
            f"    input_bytes: {self.input_bytes}",
            f"    input_tokens: {self.input_estimated_tokens}",
            f"    output_bytes: {self.output_bytes}",
            f"    output_tokens: {self.output_estimated_tokens}",
            f"    bytes_saved: {self.bytes_saved}",
            f"    tokens_saved: {self.tokens_saved}",
            f"    savings_ratio: {self.savings_ratio:.4f}",
            "  context:",
            f"    bypass_decision: {self.bypass_decision}",
            f"    fidelity_status: {self.fidelity_status}",
            f"    raw_ref_present: {self.raw_ref_present}",
            f"    ctx_holo_present: {self.ctx_holo_present}",
            f"    index_gap_detected: {self.index_gap_detected}",
            "  invariants:",
            f"    runtime_reindex_allowed: {self.runtime_reindex_allowed}",
            f"    no_command_execution: {self.no_command_execution}",
            f"    no_rtk_invocation: {self.no_rtk_invocation}",
            f"    no_secret_persistence: {self.no_secret_persistence}",
        ]
        return "\n".join(lines)


class TelemetryValidationError(Exception):
    """Raised when telemetry event validation fails."""

    def __init__(self, field: str, value: Any, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Telemetry validation failed: {field}={value} - {reason}")


@dataclass
class ValidationResult:
    """Result of event validation."""
    valid: bool
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def generate_event_id(
    source_layer: SourceLayer,
    operation: Operation,
    content_type: ContentType,
    input_bytes: int,
    output_bytes: int,
    bypass_decision: str | None = None,
) -> str:
    """
    Generate deterministic event ID from canonical content.

    Excludes timestamp for stable test assertions.

    Args:
        source_layer: Event source
        operation: Operation type
        content_type: Content type
        input_bytes: Input size
        output_bytes: Output size
        bypass_decision: Bypass class if any

    Returns:
        Deterministic event ID (32 chars hex)
    """
    canonical = (
        f"{source_layer.value}:"
        f"{operation.value}:"
        f"{content_type.value}:"
        f"{input_bytes}:"
        f"{output_bytes}:"
        f"{bypass_decision or 'none'}"
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def build_token_compression_event(
    source_layer: SourceLayer,
    operation: Operation,
    content_type: ContentType,
    input_bytes: int,
    output_bytes: int,
    *,
    bypass_decision: str | None = None,
    fidelity_status: str | None = None,
    raw_ref_present: bool = False,
    ctx_holo_present: bool = False,
    index_gap_detected: bool = False,
    timestamp: int | None = None,
) -> TokenCompressionEvent:
    """
    Build a TokenCompressionEvent with computed fields.

    Validates invariants and computes savings.

    Args:
        source_layer: Source of the event
        operation: Operation performed
        content_type: Type of content
        input_bytes: Input size in bytes
        output_bytes: Output size in bytes
        bypass_decision: Bypass class if bypassed
        fidelity_status: Fidelity check result
        raw_ref_present: Whether raw_ref exists
        ctx_holo_present: Whether CTX.HOLO exists
        index_gap_detected: Whether index gap was detected
        timestamp: Unix timestamp (defaults to now)

    Returns:
        Validated TokenCompressionEvent

    Raises:
        TelemetryValidationError: If invariants violated
    """
    # Validate non-negative counts
    if input_bytes < 0:
        raise TelemetryValidationError("input_bytes", input_bytes, "must be non-negative")
    if output_bytes < 0:
        raise TelemetryValidationError("output_bytes", output_bytes, "must be non-negative")

    # Estimate tokens
    input_tokens = estimate_tokens("x" * input_bytes)  # Approximate
    output_tokens = estimate_tokens("x" * output_bytes)

    # Compute savings
    bytes_saved = input_bytes - output_bytes
    tokens_saved = input_tokens - output_tokens

    # Compute ratio (safe division)
    if input_bytes > 0:
        savings_ratio = bytes_saved / input_bytes
    else:
        savings_ratio = 0.0

    # Determine status
    if bypass_decision:
        compression_status = CompressionStatus.BYPASSED
        # Bypassed content must not claim positive savings
        if bytes_saved > 0:
            bytes_saved = 0
            tokens_saved = 0
            savings_ratio = 0.0
    elif output_bytes > input_bytes:
        # Output larger than input - this is a negative savings scenario
        compression_status = CompressionStatus.UNCHANGED
        # Don't fake positive savings
        bytes_saved = input_bytes - output_bytes  # Will be negative
        savings_ratio = bytes_saved / input_bytes if input_bytes > 0 else 0.0
    elif output_bytes == input_bytes:
        compression_status = CompressionStatus.UNCHANGED
    else:
        compression_status = CompressionStatus.COMPRESSED

    # Generate event ID (deterministic, excludes timestamp)
    event_id = generate_event_id(
        source_layer, operation, content_type,
        input_bytes, output_bytes, bypass_decision
    )

    # Timestamp
    ts = timestamp if timestamp is not None else int(time.time())

    return TokenCompressionEvent(
        event_id=event_id,
        timestamp=ts,
        source_layer=source_layer,
        operation=operation,
        content_type=content_type,
        input_bytes=input_bytes,
        input_estimated_tokens=input_tokens,
        output_bytes=output_bytes,
        output_estimated_tokens=output_tokens,
        bytes_saved=bytes_saved,
        tokens_saved=tokens_saved,
        savings_ratio=savings_ratio,
        compression_status=compression_status,
        bypass_decision=bypass_decision,
        fidelity_status=fidelity_status,
        raw_ref_present=raw_ref_present,
        ctx_holo_present=ctx_holo_present,
        index_gap_detected=index_gap_detected,
        runtime_reindex_allowed=False,  # Invariant: always False
        no_command_execution=True,  # Invariant: always True
        no_rtk_invocation=True,  # Invariant: always True
        no_secret_persistence=True,  # Invariant: always True
    )


def validate_token_event(event: TokenCompressionEvent) -> ValidationResult:
    """
    Validate a TokenCompressionEvent against invariants.

    Args:
        event: Event to validate

    Returns:
        ValidationResult with errors if any
    """
    errors = []

    # Invariant: runtime_reindex_allowed must be False
    if event.runtime_reindex_allowed:
        errors.append("runtime_reindex_allowed must be False")

    # Invariant: no_command_execution must be True
    if not event.no_command_execution:
        errors.append("no_command_execution must be True")

    # Invariant: no_rtk_invocation must be True
    if not event.no_rtk_invocation:
        errors.append("no_rtk_invocation must be True")

    # Invariant: no_secret_persistence must be True
    if not event.no_secret_persistence:
        errors.append("no_secret_persistence must be True")

    # Invariant: non-negative input counts
    if event.input_bytes < 0:
        errors.append(f"input_bytes cannot be negative: {event.input_bytes}")
    if event.input_estimated_tokens < 0:
        errors.append(f"input_estimated_tokens cannot be negative: {event.input_estimated_tokens}")

    # Invariant: non-negative output counts
    if event.output_bytes < 0:
        errors.append(f"output_bytes cannot be negative: {event.output_bytes}")
    if event.output_estimated_tokens < 0:
        errors.append(f"output_estimated_tokens cannot be negative: {event.output_estimated_tokens}")

    # Invariant: bypassed content cannot claim compression
    if event.compression_status == CompressionStatus.BYPASSED:
        if event.bytes_saved > 0 or event.tokens_saved > 0:
            errors.append("Bypassed event cannot claim positive savings")

    # Invariant: UNKNOWN content must not claim compression
    if event.content_type == ContentType.UNKNOWN:
        if event.compression_status == CompressionStatus.COMPRESSED:
            errors.append("UNKNOWN content type cannot be marked as compressed")

    # Invariant: event_id must be non-empty
    if not event.event_id:
        errors.append("event_id cannot be empty")

    return ValidationResult(valid=len(errors) == 0, errors=errors)


@dataclass
class TelemetrySummary:
    """Summary of telemetry events."""
    total_events: int
    total_input_bytes: int
    total_output_bytes: int
    total_input_tokens: int
    total_output_tokens: int
    total_bytes_saved: int
    total_tokens_saved: int
    overall_savings_ratio: float
    events_by_status: dict[str, int]
    events_by_source: dict[str, int]
    events_by_operation: dict[str, int]
    bypassed_count: int
    compressed_count: int
    error_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_m2m_yaml(self) -> str:
        """Emit as M2M YAML format."""
        lines = [
            "TELEMETRY_SUMMARY:",
            f"  total_events: {self.total_events}",
            f"  total_input_bytes: {self.total_input_bytes}",
            f"  total_output_bytes: {self.total_output_bytes}",
            f"  total_input_tokens: {self.total_input_tokens}",
            f"  total_output_tokens: {self.total_output_tokens}",
            f"  total_bytes_saved: {self.total_bytes_saved}",
            f"  total_tokens_saved: {self.total_tokens_saved}",
            f"  overall_savings_ratio: {self.overall_savings_ratio:.4f}",
            f"  bypassed_count: {self.bypassed_count}",
            f"  compressed_count: {self.compressed_count}",
            f"  error_count: {self.error_count}",
            "  events_by_status:",
        ]
        for status, count in sorted(self.events_by_status.items()):
            lines.append(f"    {status}: {count}")
        lines.append("  events_by_source:")
        for src, count in sorted(self.events_by_source.items()):
            lines.append(f"    {src}: {count}")
        return "\n".join(lines)


def summarize_token_events(events: list[TokenCompressionEvent]) -> TelemetrySummary:
    """
    Summarize a list of telemetry events.

    Args:
        events: List of events to summarize

    Returns:
        TelemetrySummary with aggregated metrics
    """
    if not events:
        return TelemetrySummary(
            total_events=0,
            total_input_bytes=0,
            total_output_bytes=0,
            total_input_tokens=0,
            total_output_tokens=0,
            total_bytes_saved=0,
            total_tokens_saved=0,
            overall_savings_ratio=0.0,
            events_by_status={},
            events_by_source={},
            events_by_operation={},
            bypassed_count=0,
            compressed_count=0,
            error_count=0,
        )

    total_input_bytes = sum(e.input_bytes for e in events)
    total_output_bytes = sum(e.output_bytes for e in events)
    total_input_tokens = sum(e.input_estimated_tokens for e in events)
    total_output_tokens = sum(e.output_estimated_tokens for e in events)
    total_bytes_saved = sum(e.bytes_saved for e in events)
    total_tokens_saved = sum(e.tokens_saved for e in events)

    overall_ratio = total_bytes_saved / total_input_bytes if total_input_bytes > 0 else 0.0

    # Count by status
    events_by_status: dict[str, int] = {}
    for e in events:
        key = e.compression_status.value
        events_by_status[key] = events_by_status.get(key, 0) + 1

    # Count by source
    events_by_source: dict[str, int] = {}
    for e in events:
        key = e.source_layer.value
        events_by_source[key] = events_by_source.get(key, 0) + 1

    # Count by operation
    events_by_operation: dict[str, int] = {}
    for e in events:
        key = e.operation.value
        events_by_operation[key] = events_by_operation.get(key, 0) + 1

    bypassed = sum(1 for e in events if e.compression_status == CompressionStatus.BYPASSED)
    compressed = sum(1 for e in events if e.compression_status == CompressionStatus.COMPRESSED)
    errors = sum(1 for e in events if e.compression_status == CompressionStatus.ERROR)

    return TelemetrySummary(
        total_events=len(events),
        total_input_bytes=total_input_bytes,
        total_output_bytes=total_output_bytes,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        total_bytes_saved=total_bytes_saved,
        total_tokens_saved=total_tokens_saved,
        overall_savings_ratio=overall_ratio,
        events_by_status=events_by_status,
        events_by_source=events_by_source,
        events_by_operation=events_by_operation,
        bypassed_count=bypassed,
        compressed_count=compressed,
        error_count=errors,
    )


class InMemoryTelemetryStore:
    """
    In-memory telemetry storage (no persistence).

    Per Contract Section 8b: NO_CONTENT_IN_TELEMETRY - stores events, not raw content.
    """

    def __init__(self, max_events: int = 10000):
        self._events: list[TokenCompressionEvent] = []
        self._max_events = max_events

    def record(self, event: TokenCompressionEvent) -> None:
        """
        Record a telemetry event.

        Validates before recording.

        Args:
            event: Event to record

        Raises:
            TelemetryValidationError: If validation fails
        """
        result = validate_token_event(event)
        if not result.valid:
            raise TelemetryValidationError(
                "event", event.event_id, "; ".join(result.errors)
            )

        self._events.append(event)

        # Rotate if over limit (FIFO)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

    def get_all(self) -> list[TokenCompressionEvent]:
        """Get all recorded events."""
        return list(self._events)

    def get_summary(self) -> TelemetrySummary:
        """Get summary of all events."""
        return summarize_token_events(self._events)

    def clear(self) -> None:
        """Clear all events."""
        self._events.clear()

    def count(self) -> int:
        """Get event count."""
        return len(self._events)


# Module-level singleton (in-memory only)
_telemetry_store: InMemoryTelemetryStore | None = None


def get_telemetry_store() -> InMemoryTelemetryStore:
    """Get or create the telemetry store singleton."""
    global _telemetry_store
    if _telemetry_store is None:
        _telemetry_store = InMemoryTelemetryStore()
    return _telemetry_store


def reset_telemetry_store() -> None:
    """Reset the telemetry store (for tests)."""
    global _telemetry_store
    _telemetry_store = None
