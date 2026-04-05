# HoloIndex FoundUp Bridge Adapter Module
#
# Implements EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md
# WSP References: WSP 15, WSP 97

from .bridge_stub import (
    HoloIndexBridgeAdapter,
    validate_agent_request,
    BridgeResult,
    BridgeResponseData,
)

__all__ = [
    "HoloIndexBridgeAdapter",
    "validate_agent_request",
    "BridgeResult",
    "BridgeResponseData",
]
