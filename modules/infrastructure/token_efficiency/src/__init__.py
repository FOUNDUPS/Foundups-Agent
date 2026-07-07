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
]
