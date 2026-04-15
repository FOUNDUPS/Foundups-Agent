"""
FoundUps Agent Module

Agent lifecycle management and FoundUp building capabilities.
Hermes + dynamic model routing for autonomous FoundUp extraction.

Models:
- UI-TARS 1.5 7B: Vision (eyes)
- Qwen Coder 7B: Code generation
- Gemma4: Base reasoning
- Gemma 270M: Fast triage
- Qwen3-TTS: Voice/TTS
"""

__version__ = "0.4.0"
__all__ = [
    "HermesFoundUpBuilder",
    "DEFAULT_QWEN_CONFIG",
    "HermesModelRouter",
    "TaskCapability",
    "get_model_router",
    "route_to_model",
]

from .hermes_adapter import HermesFoundUpBuilder, DEFAULT_QWEN_CONFIG
from .hermes_model_router import (
    HermesModelRouter,
    TaskCapability,
    get_model_router,
    route_to_model,
)
