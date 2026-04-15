"""
Hermes Model Router - Dynamic Model Switching for FoundUp Builder

Routes Hermes agent requests to appropriate LLM based on task type:
- Vision tasks → UI-TARS 1.5 7B (eyes)
- Code tasks → Qwen Coder 7B
- Reasoning → Gemma4 (base)
- Fast triage → Gemma 270M
- Voice/TTS → Qwen3-TTS

Integrates with existing local_llm_resolver and orchestration_switchboard.

WSP References:
- WSP 77: Agent Coordination
- WSP 15: MPS Priority (task routing)
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# LM Studio endpoint
LM_STUDIO_BASE = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")


class TaskCapability(Enum):
    """Task types for model routing."""
    VISION = "vision"           # Screenshot analysis, UI element detection
    CODE = "code"               # Code generation, refactoring
    REASONING = "reasoning"     # Complex planning, analysis
    TRIAGE = "triage"           # Fast binary decisions
    VOICE = "voice"             # Text-to-speech, transcription


@dataclass
class ModelSpec:
    """Model specification for routing."""
    model_id: str
    capability: TaskCapability
    context_length: int
    supports_vision: bool = False
    supports_tools: bool = False
    tool_parser: str = "hermes"


# Model registry - maps to what's loaded in LM Studio
MODEL_REGISTRY: Dict[TaskCapability, ModelSpec] = {
    TaskCapability.VISION: ModelSpec(
        model_id="ui-tars-1.5-7b",
        capability=TaskCapability.VISION,
        context_length=4096,
        supports_vision=True,
        supports_tools=False,
    ),
    TaskCapability.CODE: ModelSpec(
        model_id="qwen-coder-7b",
        capability=TaskCapability.CODE,
        context_length=32768,
        supports_vision=False,
        supports_tools=True,
        tool_parser="qwen",
    ),
    TaskCapability.REASONING: ModelSpec(
        model_id="gemma4-e2b",
        capability=TaskCapability.REASONING,
        context_length=8192,
        supports_vision=False,
        supports_tools=True,
        tool_parser="hermes",
    ),
    TaskCapability.TRIAGE: ModelSpec(
        model_id="gemma-270m",
        capability=TaskCapability.TRIAGE,
        context_length=2048,
        supports_vision=False,
        supports_tools=False,
    ),
    TaskCapability.VOICE: ModelSpec(
        model_id="qwen3-tts",
        capability=TaskCapability.VOICE,
        context_length=4096,
        supports_vision=False,
        supports_tools=False,
    ),
}

# Fallback chain if preferred model unavailable
FALLBACK_CHAIN = {
    TaskCapability.VISION: [TaskCapability.REASONING],  # Can't fallback vision
    TaskCapability.CODE: [TaskCapability.REASONING],
    TaskCapability.REASONING: [TaskCapability.CODE, TaskCapability.TRIAGE],
    TaskCapability.TRIAGE: [TaskCapability.REASONING],
    TaskCapability.VOICE: [],  # No fallback for voice
}


class HermesModelRouter:
    """
    Routes Hermes requests to appropriate LLM model based on task type.

    Usage:
        router = HermesModelRouter()

        # Get model for vision task
        spec = router.get_model(TaskCapability.VISION)
        # Returns ModelSpec(model_id="ui-tars-1.5-7b", ...)

        # Route based on task description
        spec = router.route_task("analyze screenshot and find button")
        # Returns VISION model spec

        # Get Hermes CLI args for a capability
        args = router.get_hermes_args(TaskCapability.CODE)
        # Returns ["--model", "qwen-coder-7b", "--provider", "lmstudio", ...]
    """

    def __init__(self, base_url: str = None):
        """
        Initialize model router.

        Args:
            base_url: LM Studio API base URL
        """
        self.base_url = base_url or LM_STUDIO_BASE
        self._available_models: Optional[set] = None

    def _refresh_available_models(self) -> set:
        """Query LM Studio for available models."""
        if self._available_models is not None:
            return self._available_models

        try:
            import urllib.request
            import json

            req = urllib.request.Request(f"{self.base_url}/models", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                self._available_models = {m["id"] for m in data.get("data", [])}
                logger.info(f"[MODEL-ROUTER] Available models: {self._available_models}")
                return self._available_models
        except Exception as e:
            logger.warning(f"[MODEL-ROUTER] Could not query LM Studio: {e}")
            return set()

    def is_model_available(self, model_id: str) -> bool:
        """Check if a model is loaded in LM Studio."""
        available = self._refresh_available_models()
        return model_id in available

    def get_model(self, capability: TaskCapability) -> Optional[ModelSpec]:
        """
        Get model spec for a capability, with fallback chain.

        Args:
            capability: The task capability needed

        Returns:
            ModelSpec for best available model, or None if none available
        """
        # Try preferred model first
        preferred = MODEL_REGISTRY.get(capability)
        if preferred and self.is_model_available(preferred.model_id):
            logger.debug(f"[MODEL-ROUTER] {capability.value} -> {preferred.model_id}")
            return preferred

        # Try fallback chain
        for fallback_cap in FALLBACK_CHAIN.get(capability, []):
            fallback = MODEL_REGISTRY.get(fallback_cap)
            if fallback and self.is_model_available(fallback.model_id):
                logger.info(f"[MODEL-ROUTER] {capability.value} -> {fallback.model_id} (fallback)")
                return fallback

        logger.warning(f"[MODEL-ROUTER] No model available for {capability.value}")
        return None

    def route_task(self, task_description: str) -> Optional[ModelSpec]:
        """
        Route task to appropriate model based on description.

        Args:
            task_description: Natural language task description

        Returns:
            ModelSpec for best model to handle task
        """
        desc_lower = task_description.lower()

        # Vision keywords
        if any(kw in desc_lower for kw in [
            "screenshot", "image", "visual", "see", "look", "find button",
            "click", "ui element", "screen", "tars", "vision"
        ]):
            return self.get_model(TaskCapability.VISION)

        # Code keywords
        if any(kw in desc_lower for kw in [
            "code", "function", "class", "refactor", "implement", "fix bug",
            "python", "javascript", "test", "module", "script"
        ]):
            return self.get_model(TaskCapability.CODE)

        # Voice keywords
        if any(kw in desc_lower for kw in [
            "voice", "speak", "tts", "audio", "speech", "transcribe"
        ]):
            return self.get_model(TaskCapability.VOICE)

        # Fast triage keywords
        if any(kw in desc_lower for kw in [
            "quick", "fast", "triage", "yes/no", "simple", "binary"
        ]):
            return self.get_model(TaskCapability.TRIAGE)

        # Default to reasoning
        return self.get_model(TaskCapability.REASONING)

    def get_hermes_args(self, capability: TaskCapability) -> list:
        """
        Get Hermes CLI arguments for a capability.

        Args:
            capability: Task capability

        Returns:
            List of CLI arguments for Hermes
        """
        spec = self.get_model(capability)
        if not spec:
            return []

        args = [
            "--model", spec.model_id,
            "--provider", "lmstudio",
        ]

        if spec.supports_tools:
            args.extend(["--tool-parser", spec.tool_parser])

        return args

    def get_hermes_config(self, capability: TaskCapability) -> Dict[str, Any]:
        """
        Get Hermes config dict for a capability.

        Args:
            capability: Task capability

        Returns:
            Config dict for Hermes
        """
        spec = self.get_model(capability)
        if not spec:
            return {}

        return {
            "model": {
                "default": spec.model_id,
                "provider": "lmstudio",
                "base_url": self.base_url,
            },
            "agent": {
                "max_turns": 30 if spec.supports_tools else 1,
            },
        }


# Singleton instance
_router_instance: Optional[HermesModelRouter] = None


def get_model_router() -> HermesModelRouter:
    """Get singleton model router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = HermesModelRouter()
    return _router_instance


def route_to_model(task_description: str) -> Optional[ModelSpec]:
    """
    Convenience function to route a task to appropriate model.

    Args:
        task_description: What the task needs to do

    Returns:
        ModelSpec for best model
    """
    return get_model_router().route_task(task_description)


# Quick capability check functions
def needs_vision(task: str) -> bool:
    """Check if task requires vision model."""
    spec = route_to_model(task)
    return spec is not None and spec.supports_vision


def get_code_model() -> Optional[ModelSpec]:
    """Get code generation model."""
    return get_model_router().get_model(TaskCapability.CODE)


def get_vision_model() -> Optional[ModelSpec]:
    """Get vision model for UI-TARS tasks."""
    return get_model_router().get_model(TaskCapability.VISION)


def get_base_model() -> Optional[ModelSpec]:
    """Get base reasoning model (Gemma4)."""
    return get_model_router().get_model(TaskCapability.REASONING)
