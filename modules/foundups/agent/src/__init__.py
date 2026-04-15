"""
FoundUps Agent Module

Agent lifecycle management and FoundUp building capabilities.
Hermes + dynamic model routing for autonomous FoundUp extraction.
MCP Bridge v1.4 perception layer for intelligent decisions.

Models:
- UI-TARS 1.5 7B: Vision (eyes)
- Qwen Coder 7B: Code generation
- Gemma4: Base reasoning
- Gemma 270M: Fast triage
- Qwen3-TTS: Voice/TTS

Perception (MCP Bridge v1.4):
- Layer 0: Sense (repo, docs, overseer)
- Layer 1: Dependency + Diff
- Layer 2: Impact Prediction
- Layer 3: HoloIndex Recall
- Layer 4: Signal Normalization
"""

__version__ = "0.5.0"
__all__ = [
    "HermesFoundUpBuilder",
    "DEFAULT_QWEN_CONFIG",
    "HermesModelRouter",
    "TaskCapability",
    "get_model_router",
    "route_to_model",
    "MCP_BRIDGE_AVAILABLE",
]

from .hermes_adapter import HermesFoundUpBuilder, DEFAULT_QWEN_CONFIG, MCP_BRIDGE_AVAILABLE
from .hermes_model_router import (
    HermesModelRouter,
    TaskCapability,
    get_model_router,
    route_to_model,
)
