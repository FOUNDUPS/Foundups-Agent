#!/usr/bin/env python3
"""IronClaw gateway client + runtime security helpers.

Provides:
- OpenAI-compatible chat call wrapper for IronClaw sidecar.
- Health/model probes for CLI status checks.
- Environment scrubbing helper to launch IronClaw without API keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


def env_truthy(name: str, default: str = "0") -> bool:
    """Return True when env var is set to a truthy value."""
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


SENSITIVE_ENV_KEYS: tuple[str, ...] = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "CLAUDE_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_AISTUDIO_API_KEY",
    "GOOGLE_API_KEY",
    "GROK_API_KEY",
    "DEEPSEEK_API_KEY",
    "AZURE_OPENAI_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AI_GATEWAY_API_KEY",
    "SERPER_API_KEY",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
)


def scrub_sensitive_env(
    env: Dict[str, str],
    blocked_keys: Iterable[str] = SENSITIVE_ENV_KEYS,
) -> Dict[str, str]:
    """Return env copy with sensitive API-key style variables removed."""
    scrubbed = dict(env)
    for key in blocked_keys:
        scrubbed.pop(key, None)
    return scrubbed


@dataclass(frozen=True)
class IronClawGatewayConfig:
    """Runtime config for IronClaw OpenAI-compatible gateway."""

    base_url: str
    model: str
    auth_token: str
    timeout_sec: float
    no_api_keys: bool

    @classmethod
    def from_env(cls) -> "IronClawGatewayConfig":
        base_url = os.getenv("IRONCLAW_BASE_URL", "http://127.0.0.1:3000").strip().rstrip("/")
        model = os.getenv("IRONCLAW_MODEL", "local/qwen-coder-7b").strip()
        auth_token = (
            os.getenv("IRONCLAW_AUTH_TOKEN", "").strip()
            or os.getenv("GATEWAY_AUTH_TOKEN", "").strip()
            or os.getenv("FOUNDUPS_WEBHOOK_TOKEN", "").strip()
        )
        timeout_raw = os.getenv("IRONCLAW_TIMEOUT_SEC", "15").strip() or "15"
        try:
            timeout_sec = max(1.0, float(timeout_raw))
        except ValueError:
            timeout_sec = 15.0

        no_api_keys = env_truthy("IRONCLAW_NO_API_KEYS", "1")
        return cls(
            base_url=base_url,
            model=model,
            auth_token=auth_token,
            timeout_sec=timeout_sec,
            no_api_keys=no_api_keys,
        )


class IronClawGatewayClient:
    """Minimal OpenAI-compatible IronClaw gateway client."""

    def __init__(self, config: Optional[IronClawGatewayConfig] = None):
        self.config = config or IronClawGatewayConfig.from_env()

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.auth_token:
            headers["Authorization"] = f"Bearer {self.config.auth_token}"
        return headers

    def health(self) -> tuple[bool, str]:
        """Probe health endpoint(s)."""
        try:
            import requests
        except Exception as exc:  # pragma: no cover - defensive
            return False, f"requests unavailable: {exc}"

        diagnostics: List[str] = []
        for path in ("/api/health", "/health"):
            try:
                resp = requests.get(
                    f"{self.config.base_url}{path}",
                    headers=self._headers(),
                    timeout=self.config.timeout_sec,
                )
                if resp.ok:
                    return True, f"healthy via {path}"
                diagnostics.append(f"{path}={resp.status_code}")
            except Exception as exc:
                diagnostics.append(f"{path}=error:{type(exc).__name__}")

        # Some OpenAI-compatible gateways do not expose explicit health endpoints.
        # Treat a successful model-list response as healthy.
        try:
            resp = requests.get(
                f"{self.config.base_url}/v1/models",
                headers=self._headers(),
                timeout=self.config.timeout_sec,
            )
            if resp.ok:
                return True, "healthy via /v1/models"
            diagnostics.append(f"/v1/models={resp.status_code}")
        except Exception as exc:
            diagnostics.append(f"/v1/models=error:{type(exc).__name__}")

        detail = ", ".join(diagnostics) if diagnostics else "no probe data"
        return False, f"health probes failed ({detail})"

    def list_models(self) -> List[str]:
        """Return model IDs from /v1/models, or empty list on failure."""
        try:
            import requests

            resp = requests.get(
                f"{self.config.base_url}/v1/models",
                headers=self._headers(),
                timeout=self.config.timeout_sec,
            )
            if not resp.ok:
                return []
            payload = resp.json()
            data = payload.get("data", []) if isinstance(payload, dict) else []
            models: List[str] = []
            for item in data:
                if isinstance(item, dict):
                    mid = str(item.get("id", "")).strip()
                    if mid:
                        models.append(mid)
            return models
        except Exception:
            return []

    def chat_completion(
        self,
        user_message: str,
        system_prompt: str,
        max_tokens: int = 80,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """Call OpenAI-compatible /v1/chat/completions and return content."""
        try:
            import requests
        except Exception:
            return None

        resolved_model = (model or "").strip() or self.config.model
        payload = {
            "model": resolved_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            resp = requests.post(
                f"{self.config.base_url}/v1/chat/completions",
                json=payload,
                headers=self._headers(),
                timeout=self.config.timeout_sec,
            )
            if not resp.ok:
                return None

            body = resp.json()
            if isinstance(body, dict):
                choices = body.get("choices", [])
                if choices and isinstance(choices[0], dict):
                    msg = choices[0].get("message", {})
                    if isinstance(msg, dict):
                        content = str(msg.get("content", "")).strip()
                        if content:
                            return content
            return None
        except Exception:
            return None

    def startup_probe(self) -> Dict[str, Any]:
        """
        Higher-level startup probe with actionable remediation.

        Checks IronClaw health, and if down, probes LM Studio as fallback.
        Returns detailed status with remediation steps.

        Returns:
            Dict with keys: ok, detail, remediation (if not ok)
        """
        # First try IronClaw
        ironclaw_ok, ironclaw_detail = self.health()

        if ironclaw_ok:
            return {
                "ok": True,
                "detail": f"ironclaw_healthy: {ironclaw_detail}",
                "backend": "ironclaw",
            }

        # IronClaw down - check LM Studio fallback
        lm_studio_url = os.getenv("SIM_QWEN_BACKEND_URL", "http://127.0.0.1:1234")
        use_local = os.getenv("SIM_QWEN_BACKEND", "").lower() == "local"

        lm_studio_ok = False
        lm_studio_detail = ""

        if use_local:
            try:
                import requests

                # LM Studio exposes /v1/models
                resp = requests.get(
                    f"{lm_studio_url}/v1/models",
                    timeout=5.0,
                )
                if resp.ok:
                    lm_studio_ok = True
                    lm_studio_detail = f"lm_studio responding at {lm_studio_url}"
            except Exception as e:
                lm_studio_detail = f"lm_studio probe failed: {e}"

        if lm_studio_ok:
            return {
                "ok": True,
                "detail": f"ironclaw_down but lm_studio_fallback_ok at {lm_studio_url}",
                "backend": "lm_studio",
            }

        # Both down - provide remediation
        remediation = []

        # IronClaw remediation
        start_cmd = os.getenv("IRONCLAW_START_CMD", "").strip()
        if start_cmd:
            remediation.append(f"Run: {start_cmd}")
        else:
            remediation.append(
                "Set IRONCLAW_START_CMD in .env (e.g., 'ironclaw start' or "
                "'cargo run --release --manifest-path temp/_vendor/ironclaw/Cargo.toml')"
            )

        # LM Studio remediation
        if use_local:
            remediation.append(f"Or start LM Studio and load a model (expecting {lm_studio_url})")
        else:
            remediation.append("Or set SIM_QWEN_BACKEND=local and start LM Studio")

        return {
            "ok": False,
            "detail": f"ironclaw_down ({ironclaw_detail}), lm_studio_unavailable",
            "remediation": remediation,
            "backend": None,
        }
