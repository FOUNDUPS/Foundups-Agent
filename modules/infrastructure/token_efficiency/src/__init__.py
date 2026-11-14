# Token Efficiency Module (WSP-99 + RTK stack).
#
# P1: Bypass classifier - determines which outputs must remain raw
# P2: M2M fidelity gate - round-trip validation
# P3: Telemetry service - token savings measurement
# P4: RedDog compute governor - routing decisions
# P5: RTK evaluation - dry-run only
# P6: RTK adapter - integration seam
#
# Contract: docs/contracts/REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1.md
# WSP: WSP_97, WSP_99

from .bypass_classifier import (
    BypassClass,
    BypassClassifier,
    BypassDecision,
    get_bypass_classifier,
)

from .m2m_fidelity_gate import (
    M2MFidelityGate,
    M2MFidelityResult,
    FidelityError,
    CTXHolo,
    HoloStatus,
    HoloMode,
    HoloInvariants,
    IndexGapEvent,
    RawRef,
    assert_m2m_fidelity,
    to_m2m_compact,
    to_m2m_yaml,
    HOLO_REQUIRED_MODES,
)

from .telemetry_service import (
    TokenCompressionEvent,
    TelemetrySummary,
    TelemetryValidationError,
    ValidationResult,
    SourceLayer,
    Operation,
    ContentType,
    CompressionStatus,
    InMemoryTelemetryStore,
    estimate_tokens,
    compute_content_hash,
    generate_event_id,
    build_token_compression_event,
    validate_token_event,
    summarize_token_events,
    get_telemetry_store,
    reset_telemetry_store,
)

from .compute_governor import (
    ComputeGovernor,
    RedDogComputeDecision,
    ComputeGovernorError,
    Phase,
    Routing,
    CommandType,
    compute_command_digest,
    redact_command,
    extract_command_type,
    is_bypass_command,
    is_safe_command,
    generate_decision_id,
    record_decision_telemetry,
    validate_decision,
    get_compute_governor,
    reset_compute_governor,
)

from .rtk_evaluation_dryrun import (
    RtkDryRunDecision,
    RtkDryRunRejection,
    RtkEvaluationDryRunResult,
    evaluate_rtk_candidate_dry_run,
)

from .rtk_openclaw_hermes_adapter_dryrun import (
    RtkAdapterDryRunDecision,
    RtkAdapterDryRunRejection,
    RtkAdapterOutputMode,
    RtkAdapterSurface,
    RtkOpenClawHermesAdapterDryRunResult,
    plan_rtk_openclaw_hermes_adapter_dry_run,
)

__all__ = [
    # Bypass classifier (P1)
    "BypassClass",
    "BypassClassifier",
    "BypassDecision",
    "get_bypass_classifier",
    # M2M fidelity gate (P2)
    "M2MFidelityGate",
    "M2MFidelityResult",
    "FidelityError",
    "CTXHolo",
    "HoloStatus",
    "HoloMode",
    "HoloInvariants",
    "IndexGapEvent",
    "RawRef",
    "assert_m2m_fidelity",
    "to_m2m_compact",
    "to_m2m_yaml",
    "HOLO_REQUIRED_MODES",
    # Telemetry service (P3)
    "TokenCompressionEvent",
    "TelemetrySummary",
    "TelemetryValidationError",
    "ValidationResult",
    "SourceLayer",
    "Operation",
    "ContentType",
    "CompressionStatus",
    "InMemoryTelemetryStore",
    "estimate_tokens",
    "compute_content_hash",
    "generate_event_id",
    "build_token_compression_event",
    "validate_token_event",
    "summarize_token_events",
    "get_telemetry_store",
    "reset_telemetry_store",
    # Compute governor (P4)
    "ComputeGovernor",
    "RedDogComputeDecision",
    "ComputeGovernorError",
    "Phase",
    "Routing",
    "CommandType",
    "compute_command_digest",
    "redact_command",
    "extract_command_type",
    "is_bypass_command",
    "is_safe_command",
    "generate_decision_id",
    "record_decision_telemetry",
    "validate_decision",
    "get_compute_governor",
    "reset_compute_governor",
    # RTK evaluation dry-run (P5)
    "RtkDryRunDecision",
    "RtkDryRunRejection",
    "RtkEvaluationDryRunResult",
    "evaluate_rtk_candidate_dry_run",
    # OpenClaw/Hermes RTK adapter dry-run (P6)
    "RtkAdapterDryRunDecision",
    "RtkAdapterDryRunRejection",
    "RtkAdapterOutputMode",
    "RtkAdapterSurface",
    "RtkOpenClawHermesAdapterDryRunResult",
    "plan_rtk_openclaw_hermes_adapter_dry_run",
]
