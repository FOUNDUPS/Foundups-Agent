"""Central AI Model Registry - Single source of truth for all AI model versions.

UPDATE THIS FILE when providers release new models.
All other modules should import from here, not hardcode model IDs.

Last Updated: 2026-02-22
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Dict, Optional


class ModelStatus(Enum):
    """Model lifecycle status."""
    CURRENT = "current"      # Active, recommended
    LEGACY = "legacy"        # Works but newer available
    DEPRECATED = "deprecated"  # Will be removed soon
    SUNSET = "sunset"        # No longer available


@dataclass
class ModelInfo:
    """Model metadata."""
    model_id: str
    provider: str
    status: ModelStatus
    release_date: Optional[date] = None
    sunset_date: Optional[date] = None
    notes: str = ""

    @property
    def is_usable(self) -> bool:
        return self.status in (ModelStatus.CURRENT, ModelStatus.LEGACY)


# =============================================================================
# OPENAI MODELS
# =============================================================================
OPENAI_MODELS: Dict[str, ModelInfo] = {
    # Current (Feb 2026)
    "gpt-5.2": ModelInfo(
        model_id="gpt-5.2",
        provider="openai",
        status=ModelStatus.CURRENT,
        notes="Flagship thinking model - coding, agentic tasks ($1.75/$14 per 1M)"
    ),
    "gpt-5.2-codex": ModelInfo(
        model_id="gpt-5.2-codex",
        provider="openai",
        status=ModelStatus.CURRENT,
        notes="Optimized for agentic coding (Codex environments)"
    ),
    "gpt-5": ModelInfo(
        model_id="gpt-5",
        provider="openai",
        status=ModelStatus.CURRENT,
        notes="General purpose, replaces GPT-4o ($1.25/$10 per 1M)"
    ),
    "o3": ModelInfo(
        model_id="o3",
        provider="openai",
        status=ModelStatus.SUNSET,
        release_date=date(2025, 4, 16),
        notes="No longer available - use o3-pro or gpt-5.2"
    ),
    "o3-pro": ModelInfo(
        model_id="o3-pro",
        provider="openai",
        status=ModelStatus.CURRENT,
        notes="Extended reasoning (Responses API) ($20/$80 per 1M)"
    ),
    "o4-mini": ModelInfo(
        model_id="o4-mini",
        provider="openai",
        status=ModelStatus.CURRENT,
        release_date=date(2025, 4, 16),
        notes="Fast reasoning model ($1.10/$4.40 per 1M)"
    ),
    # Deprecated/Sunset (retired Feb 13, 2026)
    "gpt-4o": ModelInfo(
        model_id="gpt-4o",
        provider="openai",
        status=ModelStatus.SUNSET,
        release_date=date(2024, 5, 13),
        sunset_date=date(2026, 2, 13),
        notes="RETIRED Feb 2026 — use gpt-5 or gpt-5.2"
    ),
    "gpt-4o-mini": ModelInfo(
        model_id="gpt-4o-mini",
        provider="openai",
        status=ModelStatus.SUNSET,
        release_date=date(2024, 7, 18),
        sunset_date=date(2026, 2, 13),
        notes="RETIRED Feb 2026 — use gpt-5"
    ),
    "o1": ModelInfo(
        model_id="o1",
        provider="openai",
        status=ModelStatus.DEPRECATED,
        release_date=date(2024, 12, 5),
        notes="Superseded by o3"
    ),
    "o1-mini": ModelInfo(
        model_id="o1-mini",
        provider="openai",
        status=ModelStatus.DEPRECATED,
        release_date=date(2024, 9, 12),
        notes="Superseded by o4-mini"
    ),
    "o3-mini": ModelInfo(
        model_id="o3-mini",
        provider="openai",
        status=ModelStatus.DEPRECATED,
        release_date=date(2025, 1, 31),
        notes="Superseded by o4-mini"
    ),
    "gpt-4-turbo": ModelInfo(
        model_id="gpt-4-turbo",
        provider="openai",
        status=ModelStatus.SUNSET,
        release_date=date(2024, 4, 9),
        notes="RETIRED — use gpt-5.2"
    ),
    "gpt-4": ModelInfo(
        model_id="gpt-4",
        provider="openai",
        status=ModelStatus.SUNSET,
        release_date=date(2023, 3, 14),
        sunset_date=date(2025, 6, 1),
        notes="RETIRED — use gpt-5.2"
    ),
    "gpt-3.5-turbo": ModelInfo(
        model_id="gpt-3.5-turbo",
        provider="openai",
        status=ModelStatus.SUNSET,
        release_date=date(2023, 3, 1),
        notes="RETIRED — use gpt-5"
    ),
}

# =============================================================================
# ANTHROPIC MODELS
# =============================================================================
ANTHROPIC_MODELS: Dict[str, ModelInfo] = {
    # Current (2026) - Claude 4.x family
    "claude-opus-4-6": ModelInfo(
        model_id="claude-opus-4-6",
        provider="anthropic",
        status=ModelStatus.CURRENT,
        notes="Most capable - complex code, research"
    ),
    "claude-sonnet-4-5-20250929": ModelInfo(
        model_id="claude-sonnet-4-5-20250929",
        provider="anthropic",
        status=ModelStatus.CURRENT,
        release_date=date(2025, 9, 29),
        notes="Balanced - good for most tasks"
    ),
    "claude-haiku-4-5-20251001": ModelInfo(
        model_id="claude-haiku-4-5-20251001",
        provider="anthropic",
        status=ModelStatus.CURRENT,
        release_date=date(2025, 10, 1),
        notes="Fast, cheap - quick tasks"
    ),
    # Deprecated - Claude 3.x family
    "claude-3-opus-20240229": ModelInfo(
        model_id="claude-3-opus-20240229",
        provider="anthropic",
        status=ModelStatus.DEPRECATED,
        release_date=date(2024, 2, 29),
        notes="Use claude-opus-4-6 instead"
    ),
    "claude-3-sonnet-20240229": ModelInfo(
        model_id="claude-3-sonnet-20240229",
        provider="anthropic",
        status=ModelStatus.DEPRECATED,
        release_date=date(2024, 2, 29),
        notes="Use claude-sonnet-4-5 instead"
    ),
    "claude-3-haiku-20240307": ModelInfo(
        model_id="claude-3-haiku-20240307",
        provider="anthropic",
        status=ModelStatus.DEPRECATED,
        release_date=date(2024, 3, 7),
        notes="Use claude-haiku-4-5 instead"
    ),
}

# =============================================================================
# GOOGLE GEMINI MODELS
# =============================================================================
GEMINI_MODELS: Dict[str, ModelInfo] = {
    # Current (2026) - Gemini 3 preview + 2.5 stable
    "gemini-3-pro-preview": ModelInfo(
        model_id="gemini-3-pro-preview",
        provider="google",
        status=ModelStatus.CURRENT,
        notes="Latest Gemini - reasoning + multimodal (preview)"
    ),
    "gemini-3-flash-preview": ModelInfo(
        model_id="gemini-3-flash-preview",
        provider="google",
        status=ModelStatus.CURRENT,
        notes="Fast frontier-class performance (preview)"
    ),
    "gemini-2.5-pro": ModelInfo(
        model_id="gemini-2.5-pro",
        provider="google",
        status=ModelStatus.CURRENT,
        release_date=date(2025, 3, 25),
        notes="Stable reasoning model - production recommended"
    ),
    "gemini-2.5-flash": ModelInfo(
        model_id="gemini-2.5-flash",
        provider="google",
        status=ModelStatus.CURRENT,
        release_date=date(2025, 4, 17),
        notes="Stable fast model - production recommended"
    ),
    "gemini-2.5-flash-lite": ModelInfo(
        model_id="gemini-2.5-flash-lite",
        provider="google",
        status=ModelStatus.CURRENT,
        notes="Cost-efficient, high throughput"
    ),
    # Deprecated (shutdown March 31, 2026)
    "gemini-2.0-flash": ModelInfo(
        model_id="gemini-2.0-flash",
        provider="google",
        status=ModelStatus.DEPRECATED,
        release_date=date(2024, 12, 11),
        sunset_date=date(2026, 3, 31),
        notes="SHUTDOWN March 31 2026 — use gemini-2.5-flash"
    ),
    "gemini-pro": ModelInfo(
        model_id="gemini-pro",
        provider="google",
        status=ModelStatus.DEPRECATED,
        release_date=date(2023, 12, 6),
        notes="Use gemini-2.5-pro instead"
    ),
    "gemini-pro-vision": ModelInfo(
        model_id="gemini-pro-vision",
        provider="google",
        status=ModelStatus.DEPRECATED,
        release_date=date(2023, 12, 6),
        notes="Use gemini-2.5-pro (multimodal built-in)"
    ),
}

# =============================================================================
# GROK MODELS (X.AI)
# =============================================================================
GROK_MODELS: Dict[str, ModelInfo] = {
    # Current (Feb 2026) - Grok 4 family
    "grok-4": ModelInfo(
        model_id="grok-4",
        provider="xai",
        status=ModelStatus.CURRENT,
        notes="Flagship Grok - most intelligent ($3/$15 per 1M)"
    ),
    "grok-4-fast": ModelInfo(
        model_id="grok-4-fast",
        provider="xai",
        status=ModelStatus.CURRENT,
        notes="Fast reasoning model ($0.20/$0.50 per 1M)"
    ),
    "grok-code-fast-1": ModelInfo(
        model_id="grok-code-fast-1",
        provider="xai",
        status=ModelStatus.CURRENT,
        notes="Agentic coding model ($0.20/$1.50 per 1M)"
    ),
    "grok-3-mini": ModelInfo(
        model_id="grok-3-mini",
        provider="xai",
        status=ModelStatus.CURRENT,
        notes="Lightweight reasoning ($0.30/$0.50 per 1M)"
    ),
    # Legacy
    "grok-3": ModelInfo(
        model_id="grok-3",
        provider="xai",
        status=ModelStatus.LEGACY,
        notes="Previous flagship — use grok-4"
    ),
    # Deprecated
    "grok-2": ModelInfo(
        model_id="grok-2",
        provider="xai",
        status=ModelStatus.DEPRECATED,
        notes="Use grok-4 or grok-4-fast instead"
    ),
}

# =============================================================================
# LOCAL MODELS (LM Studio / Ollama / llama.cpp)
# =============================================================================
LOCAL_MODELS: Dict[str, ModelInfo] = {
    "local/qwen-coder-7b": ModelInfo(
        model_id="local/qwen-coder-7b",
        provider="lm_studio_local",
        status=ModelStatus.CURRENT,
        notes="Default local coding model (qwen-coder-7b)"
    ),
    "local/qwen3-4b": ModelInfo(
        model_id="local/qwen3-4b",
        provider="lm_studio_local",
        status=ModelStatus.CURRENT,
        notes="General local reasoning/chat model (qwen3-4b)"
    ),
    "local/gemma-270m": ModelInfo(
        model_id="local/gemma-270m",
        provider="lm_studio_local",
        status=ModelStatus.CURRENT,
        notes="Fast local triage/classification model (gemma-270m)"
    ),
    "qwen2.5:7b": ModelInfo(
        model_id="qwen2.5:7b",
        provider="ollama",
        status=ModelStatus.LEGACY,
        notes="Legacy local model - prefer local/qwen3-4b or local/qwen-coder-7b"
    ),
    "gemma2:2b": ModelInfo(
        model_id="gemma2:2b",
        provider="ollama",
        status=ModelStatus.LEGACY,
        notes="Legacy local model - prefer local/gemma-270m"
    ),
    "llama3.2:3b": ModelInfo(
        model_id="llama3.2:3b",
        provider="ollama",
        status=ModelStatus.LEGACY,
        notes="Legacy local model - prefer local/qwen3-4b"
    ),
}

# =============================================================================
# COMBINED REGISTRY
# =============================================================================
ALL_MODELS: Dict[str, ModelInfo] = {
    **OPENAI_MODELS,
    **ANTHROPIC_MODELS,
    **GEMINI_MODELS,
    **GROK_MODELS,
    **LOCAL_MODELS,
}

# =============================================================================
# RECOMMENDED MODELS BY TASK
# =============================================================================
RECOMMENDED_MODELS = {
    # 012's activity routing matrix (primary task types) — Feb 2026 current
    "coding": ["claude-opus-4-6", "gpt-5.2-codex", "grok-code-fast-1", "gemini-2.5-pro"],
    "math": ["o3", "o4-mini", "gemini-2.5-pro", "claude-opus-4-6"],
    "reasoning": ["o3-pro", "gpt-5.2", "claude-opus-4-6", "gemini-2.5-pro"],
    "social": ["grok-4", "gpt-5", "claude-sonnet-4-5-20250929"],
    "research": ["gemini-2.5-pro", "gpt-5.2", "claude-sonnet-4-5-20250929"],
    # Secondary task types
    "code_review": ["claude-opus-4-6", "gpt-5.2-codex", "gemini-2.5-pro"],
    "analysis": ["gpt-5.2", "claude-sonnet-4-5-20250929", "o3"],
    "creative": ["claude-sonnet-4-5-20250929", "gpt-5", "gemini-2.5-flash"],
    "quick": ["grok-4-fast", "gpt-5", "claude-haiku-4-5-20251001", "gemini-2.5-flash"],
    # Local models
    "local_fast": ["local/gemma-270m"],
    "local_smart": ["local/qwen3-4b"],
    "local_code": ["local/qwen-coder-7b"],
}

# =============================================================================
# TASK CLASSIFICATION KEYWORDS (activity routing sub-task classifier)
# =============================================================================
TASK_KEYWORDS = {
    "coding": ["code", "implement", "refactor", "debug", "fix", "bug",
               "function", "class", "module", "test", "pytest", "git",
               "commit", "PR", "build", "compile", "deploy", "script"],
    "math": ["calculate", "equation", "optimize", "algorithm", "probability",
             "statistics", "tokenomics", "distribution", "formula", "proof",
             "demurrage", "backing ratio", "epoch"],
    "reasoning": ["plan", "strategy", "architecture", "design", "tradeoff",
                  "compare", "evaluate", "decide", "prioritize", "roadmap",
                  "should we", "what approach", "how should"],
    "social": ["tweet", "post", "reply", "comment", "roast", "edgy", "meme",
               "troll", "political", "X post", "grok", "social media",
               "magat", "liberty", "raving"],
    "research": ["search", "find", "lookup", "paper", "documentation",
                 "investigate", "explore", "summarize", "report", "audit",
                 "what is", "how does", "explain"],
    "creative": ["write", "story", "script", "content", "blog", "video",
                 "description", "tagline", "copy", "narrative", "litepaper"],
    "quick": ["define", "translate", "convert", "format", "list", "count"],
}


def classify_task(prompt: str) -> str:
    """Classify a prompt into a task type using keyword matching.

    Returns the best-matching task type from TASK_KEYWORDS.
    Falls back to 'reasoning' if no keywords match (safest default).
    """
    prompt_lower = prompt.lower()
    scores = {}
    for task_type, keywords in TASK_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in prompt_lower)
        if score > 0:
            scores[task_type] = score

    if not scores:
        return "reasoning"
    return max(scores, key=scores.get)

# =============================================================================
# MIGRATION MAP (deprecated -> current)
# =============================================================================
MIGRATION_MAP = {
    # OpenAI (Feb 2026 — GPT-4o/o1/o3-mini all retired)
    "gpt-4": "gpt-5",
    "gpt-3.5-turbo": "gpt-5",
    "gpt-4-turbo": "gpt-5.2",
    "gpt-4o": "gpt-5",
    "gpt-4o-mini": "gpt-5",
    "o1": "o3-pro",
    "o1-mini": "o4-mini",
    "o3-mini": "o4-mini",
    # Anthropic
    "claude-3-opus-20240229": "claude-opus-4-6",
    "claude-3-sonnet-20240229": "claude-sonnet-4-5-20250929",
    "claude-3-haiku-20240307": "claude-haiku-4-5-20251001",
    # Gemini (2.0-flash shutdown March 31 2026)
    "gemini-pro": "gemini-2.5-pro",
    "gemini-pro-vision": "gemini-2.5-pro",
    "gemini-1.0-pro": "gemini-2.5-pro",
    "gemini-2.0-flash": "gemini-2.5-flash",
    # Grok (grok-2 deprecated, grok-4 is flagship)
    "grok-2": "grok-4",
    # Local model refresh (LM Studio local stack)
    "qwen2.5:7b": "local/qwen3-4b",
    "gemma2:2b": "local/gemma-270m",
    "llama3.2:3b": "local/qwen3-4b",
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_model(model_id: str) -> Optional[ModelInfo]:
    """Get model info by ID."""
    return ALL_MODELS.get(model_id)


def get_current_models(provider: Optional[str] = None) -> Dict[str, ModelInfo]:
    """Get all current (non-deprecated) models."""
    models = {
        k: v for k, v in ALL_MODELS.items()
        if v.status == ModelStatus.CURRENT
    }
    if provider:
        models = {k: v for k, v in models.items() if v.provider == provider}
    return models


def get_deprecated_models() -> Dict[str, ModelInfo]:
    """Get all deprecated models (need migration)."""
    return {
        k: v for k, v in ALL_MODELS.items()
        if v.status in (ModelStatus.DEPRECATED, ModelStatus.SUNSET)
    }


def check_model_status(model_id: str) -> tuple[bool, str]:
    """Check if a model ID is current.

    Returns:
        (is_ok, message)
    """
    model = ALL_MODELS.get(model_id)
    if model is None:
        return False, f"Unknown model: {model_id}"

    if model.status == ModelStatus.CURRENT:
        return True, f"{model_id} is current"
    elif model.status == ModelStatus.LEGACY:
        return True, f"{model_id} works but newer models available"
    elif model.status == ModelStatus.DEPRECATED:
        return False, f"{model_id} is DEPRECATED: {model.notes}"
    else:
        return False, f"{model_id} is SUNSET (no longer available)"


def audit_codebase_models(model_ids: list[str]) -> dict:
    """Audit a list of model IDs for obsolete references.

    Returns dict with current, legacy, deprecated, unknown lists.
    """
    result = {
        "current": [],
        "legacy": [],
        "deprecated": [],
        "unknown": [],
    }

    for model_id in model_ids:
        model = ALL_MODELS.get(model_id)
        if model is None:
            result["unknown"].append(model_id)
        elif model.status == ModelStatus.CURRENT:
            result["current"].append(model_id)
        elif model.status == ModelStatus.LEGACY:
            result["legacy"].append(model_id)
        else:
            result["deprecated"].append(model_id)

    return result


def print_registry_status():
    """Print registry status summary."""
    current = get_current_models()
    deprecated = get_deprecated_models()

    print("=" * 60)
    print("AI MODEL REGISTRY STATUS")
    print("=" * 60)
    print(f"\nCurrent Models ({len(current)}):")
    for model_id, info in sorted(current.items(), key=lambda x: x[1].provider):
        print(f"  [{info.provider:10}] {model_id}")

    print(f"\nDeprecated Models ({len(deprecated)}):")
    for model_id, info in sorted(deprecated.items(), key=lambda x: x[1].provider):
        print(f"  [{info.provider:10}] {model_id} -> {info.notes}")

    print("\nRecommended by Task:")
    for task, models in RECOMMENDED_MODELS.items():
        print(f"  {task}: {models[0]}")


if __name__ == "__main__":
    print_registry_status()
