#!/usr/bin/env python3
"""OpenRouter client - unified LLM routing with fallback support.

Provides OpenAI-compatible access to multiple LLM providers via OpenRouter:
- Anthropic (Claude), OpenAI (GPT-4), Meta (Llama), Mistral, Google (Gemini)
- Cost tracking per request
- Preset support (@preset/foundups-agent)
- Web search plugin
- Fallback chain when local models fail

Usage:
    from modules.infrastructure.openrouter_client import OpenRouterClient

    client = OpenRouterClient()
    response = client.chat_completion(
        user_message="Explain quantum computing",
        system_prompt="You are a helpful assistant.",
    )
    if response.ok:
        print(response.content)
        print(f"Cost: ${response.cost:.4f}")
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv


def env_truthy(name: str, default: str = "0") -> bool:
    """Return True when env var is set to a truthy value."""
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


# Model aliases for convenience
MODEL_ALIASES: Dict[str, str] = {
    "sonnet": "anthropic/claude-sonnet-4",
    "claude": "anthropic/claude-sonnet-4",
    "opus": "anthropic/claude-opus-4",
    "haiku": "anthropic/claude-3.5-haiku",
    "gpt4": "openai/gpt-4o",
    "gpt4o": "openai/gpt-4o",
    "llama": "meta-llama/llama-3.1-70b-instruct",
    "llama70b": "meta-llama/llama-3.1-70b-instruct",
    "llama8b": "meta-llama/llama-3.1-8b-instruct",
    "mistral": "mistralai/mistral-large",
    "gemini": "google/gemini-pro-1.5",
    # Special: use configured preset with fallback chain
    "preset": "@preset/foundups-agent",
    "foundups": "@preset/foundups-agent",
}


@dataclass(frozen=True)
class OpenRouterConfig:
    """Runtime config for OpenRouter API."""

    api_key: str
    base_url: str
    default_model: str
    preset: str
    timeout_sec: float
    fallback_enabled: bool
    web_search: bool

    @classmethod
    def from_env(cls) -> "OpenRouterConfig":
        """Load config from environment variables."""
        load_dotenv()

        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            # Check for alternative key names
            api_key = os.getenv("OPENROUTER_KEY", "").strip()

        base_url = os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ).strip().rstrip("/")

        default_model = os.getenv(
            "OPENROUTER_DEFAULT_MODEL", "anthropic/claude-sonnet-4"
        ).strip()

        preset = os.getenv("OPENROUTER_PRESET", "foundups-agent").strip()

        timeout_raw = os.getenv("OPENROUTER_TIMEOUT_SEC", "60").strip() or "60"
        try:
            timeout_sec = max(5.0, float(timeout_raw))
        except ValueError:
            timeout_sec = 60.0

        fallback_enabled = env_truthy("OPENROUTER_FALLBACK_ENABLED", "true")
        web_search = env_truthy("OPENROUTER_WEB_SEARCH", "false")

        return cls(
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
            preset=preset,
            timeout_sec=timeout_sec,
            fallback_enabled=fallback_enabled,
            web_search=web_search,
        )


@dataclass
class OpenRouterResponse:
    """Response from OpenRouter API with cost tracking."""

    ok: bool
    content: str
    model: str
    cost: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: Optional[str] = None
    raw: Optional[Dict[str, Any]] = field(default=None, repr=False)


class OpenRouterClient:
    """OpenRouter API client with OpenAI-compatible interface."""

    def __init__(self, config: Optional[OpenRouterConfig] = None):
        """Initialize client with config (defaults to env vars)."""
        self.config = config or OpenRouterConfig.from_env()
        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        """Lazy-init requests session."""
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def _headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/FOUNDUPS/Foundups-Agent",
            "X-Title": "FoundUps Agent",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _resolve_model(self, model: Optional[str], use_preset: bool = False) -> str:
        """Resolve model alias to full model ID.

        Args:
            model: Model name, alias, or None for default
            use_preset: If True and model is None, use @preset/foundups-agent
        """
        if not model:
            if use_preset and self.config.preset:
                return f"@preset/{self.config.preset}"
            return self.config.default_model

        model_lower = model.strip().lower()

        # Check aliases (includes "preset" -> "@preset/foundups-agent")
        if model_lower in MODEL_ALIASES:
            return MODEL_ALIASES[model_lower]

        # Preserve @preset/ models as-is (case-sensitive)
        if model.startswith("@preset/"):
            return model

        # Check if it's already a full model ID
        if "/" in model:
            return model

        # Try prefix matching
        for alias, full_id in MODEL_ALIASES.items():
            if model_lower.startswith(alias):
                return full_id

        return model

    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.config.api_key)

    def health(self) -> tuple[bool, str]:
        """Check OpenRouter API health."""
        if not self.is_configured():
            return False, "OPENROUTER_API_KEY not configured"

        try:
            resp = self.session.get(
                f"{self.config.base_url}/models",
                headers=self._headers(),
                timeout=10.0,
            )
            if resp.ok:
                return True, "OpenRouter API healthy"
            return False, f"API returned {resp.status_code}"
        except requests.RequestException as e:
            return False, f"Connection error: {e}"

    def list_models(self) -> List[str]:
        """List available models."""
        if not self.is_configured():
            return []

        try:
            resp = self.session.get(
                f"{self.config.base_url}/models",
                headers=self._headers(),
                timeout=self.config.timeout_sec,
            )
            if not resp.ok:
                return []

            data = resp.json()
            models = data.get("data", [])
            return [m.get("id", "") for m in models if m.get("id")]
        except Exception:
            return []

    def chat_completion(
        self,
        user_message: str,
        system_prompt: str = "You are a helpful assistant.",
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        use_preset: bool = True,
        web_search: Optional[bool] = None,
    ) -> OpenRouterResponse:
        """Send chat completion request to OpenRouter.

        Args:
            user_message: The user's message
            system_prompt: System prompt for context
            model: Model ID or alias (sonnet, gpt4, llama, etc.)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-2.0)
            use_preset: Use configured preset (foundups-agent)
            web_search: Enable web search plugin (overrides config)

        Returns:
            OpenRouterResponse with content, cost, and metadata
        """
        if not self.is_configured():
            return OpenRouterResponse(
                ok=False,
                content="",
                model="",
                error="OPENROUTER_API_KEY not configured",
            )

        resolved_model = self._resolve_model(model, use_preset=use_preset)

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        # Build payload
        payload: Dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        # Note: Presets are applied automatically when the API key has a default preset
        # assigned in the OpenRouter dashboard. No request-level parameter needed.
        # The use_preset parameter is kept for future compatibility if OpenRouter
        # adds request-level preset support.

        # Add web search plugin if enabled
        enable_search = web_search if web_search is not None else self.config.web_search
        if enable_search:
            payload["plugins"] = [{"id": "web-search"}]

        try:
            resp = self.session.post(
                f"{self.config.base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
                timeout=self.config.timeout_sec,
            )

            if not resp.ok:
                error_msg = f"API error {resp.status_code}"
                try:
                    error_data = resp.json()
                    if "error" in error_data:
                        error_msg = error_data["error"].get("message", error_msg)
                except Exception:
                    error_msg = resp.text[:200] if resp.text else error_msg

                return OpenRouterResponse(
                    ok=False,
                    content="",
                    model=resolved_model,
                    error=error_msg,
                )

            data = resp.json()

            # Extract content
            content = ""
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", "").strip()

            # Extract usage/cost
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

            # OpenRouter includes cost in response (in USD)
            cost = 0.0
            if "usage" in data and "total_cost" in data["usage"]:
                cost = data["usage"]["total_cost"]

            return OpenRouterResponse(
                ok=True,
                content=content,
                model=data.get("model", resolved_model),
                cost=cost,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                raw=data,
            )

        except requests.Timeout:
            return OpenRouterResponse(
                ok=False,
                content="",
                model=resolved_model,
                error=f"Request timed out after {self.config.timeout_sec}s",
            )
        except requests.RequestException as e:
            return OpenRouterResponse(
                ok=False,
                content="",
                model=resolved_model,
                error=f"Request error: {e}",
            )
        except Exception as e:
            return OpenRouterResponse(
                ok=False,
                content="",
                model=resolved_model,
                error=f"Unexpected error: {e}",
            )

    def startup_probe(self) -> Dict[str, Any]:
        """Probe OpenRouter availability for startup checks.

        Returns:
            Dict with keys: ok, detail, backend
        """
        if not self.is_configured():
            return {
                "ok": False,
                "detail": "OPENROUTER_API_KEY not set",
                "backend": None,
                "remediation": [
                    "Set OPENROUTER_API_KEY in .env",
                    "Get key from: https://openrouter.ai/keys",
                ],
            }

        ok, detail = self.health()

        if ok:
            return {
                "ok": True,
                "detail": f"openrouter_healthy: {detail}",
                "backend": "openrouter",
            }

        return {
            "ok": False,
            "detail": f"openrouter_unhealthy: {detail}",
            "backend": None,
            "remediation": [
                "Check OPENROUTER_API_KEY is valid",
                "Check OpenRouter status: https://status.openrouter.ai",
            ],
        }


# Singleton instance for convenience
_default_client: Optional[OpenRouterClient] = None


def get_openrouter_client() -> OpenRouterClient:
    """Get or create default OpenRouter client singleton."""
    global _default_client
    if _default_client is None:
        _default_client = OpenRouterClient()
    return _default_client


# Quick access functions
def openrouter_chat(
    message: str,
    system_prompt: str = "You are a helpful assistant.",
    model: Optional[str] = None,
    **kwargs,
) -> OpenRouterResponse:
    """Quick chat completion via default client."""
    return get_openrouter_client().chat_completion(
        user_message=message,
        system_prompt=system_prompt,
        model=model,
        **kwargs,
    )


def openrouter_health() -> tuple[bool, str]:
    """Quick health check via default client."""
    return get_openrouter_client().health()
