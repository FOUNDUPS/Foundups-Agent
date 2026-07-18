#!/usr/bin/env python3
"""
FoundUps AI Gateway - Unified AI Service Access
===============================================

Provides intelligent routing, fallback, and load balancing across multiple AI providers.

Features:
- Automatic fallback between providers
- Task-specific model selection
- Cost optimization
- Load balancing
- Usage monitoring

Usage:
    from ai_gateway import AIGateway

    gateway = AIGateway()
    response = gateway.call_with_fallback("Analyze this code", task_type="code_review")
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import requests
import json

# Import model registry for centralized model management
from .model_registry import (
    RECOMMENDED_MODELS,
    classify_task,
    get_current_models,
    check_model_status,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GatewayResult:
    """Result from AI gateway call"""
    response: str
    provider: str
    model: str
    duration: float
    cost_estimate: float
    success: bool


@dataclass
class ProviderConfig:
    """Configuration for AI provider"""
    name: str
    api_key: Optional[str]
    base_url: str
    models: Dict[str, str]  # task_type -> model_name
    cost_per_token: float
    rate_limit: int  # requests per minute
    timeout: int = 30
    output_cost_per_token: float = 0.0
    automatic_routing_enabled: bool = True


class AIGateway:
    """
    AI Gateway for unified access to multiple AI providers.

    Provides intelligent routing, automatic fallback, and cost optimization
    across OpenAI, Anthropic, Grok, Google Gemini, and explicitly selected
    OpenRouter models used by governed AutoResearch campaigns.
    """

    def __init__(self, gateway_key: Optional[str] = None):
        """
        Initialize AI Gateway

        Args:
            gateway_key: Primary gateway API key (optional)
        """
        self.gateway_key = gateway_key or os.getenv('AI_GATEWAY_API_KEY')

        # Configure AI providers
        self.providers = self._setup_providers()

        # Usage tracking
        self.usage_stats = {
            'calls': 0,
            'failures': 0,
            'provider_usage': {},
            'task_distribution': {}
        }

        logger.info(f"[AI-GATEWAY] Initialized with {len([p for p in self.providers.values() if p.api_key])} active providers")

    def _get_env_int(self, name: str, default: int) -> int:
        """Read an int from env with a safe fallback."""
        value = os.getenv(name)
        if value is None or value == "":
            return default
        try:
            return int(value)
        except ValueError:
            logger.warning(f"[AI-GATEWAY] Invalid {name} value: {value}")
            return default

    def _get_env_float(self, name: str, default: float) -> float:
        """Read a float from env with a safe fallback."""
        value = os.getenv(name)
        if value is None or value == "":
            return default
        try:
            return float(value)
        except ValueError:
            logger.warning(f"[AI-GATEWAY] Invalid {name} value: {value}")
            return default

    def _get_provider_max_tokens(self, provider_name: str, default: int) -> int:
        """Resolve max_tokens for provider from env overrides."""
        provider_key = f"{provider_name.upper()}_MAX_TOKENS"
        if os.getenv(provider_key):
            return self._get_env_int(provider_key, default)
        if os.getenv("MAX_TOKENS"):
            return self._get_env_int("MAX_TOKENS", default)
        return self._get_env_int("LLM_MAX_TOKENS", default)

    def _get_provider_temperature(self, provider_name: str, default: float) -> float:
        """Resolve temperature for provider from env overrides."""
        provider_key = f"{provider_name.upper()}_TEMPERATURE"
        if os.getenv(provider_key):
            return self._get_env_float(provider_key, default)
        if os.getenv("TEMPERATURE"):
            return self._get_env_float("TEMPERATURE", default)
        return self._get_env_float("LLM_TEMPERATURE", default)

    def _setup_providers(self) -> Dict[str, ProviderConfig]:
        """Set up AI provider configurations"""

        return {
            'openai': ProviderConfig(
                name='openai',
                api_key=os.getenv('OPENAI_API_KEY'),
                base_url='https://api.openai.com/v1',
                models={
                    'coding': 'gpt-5.2-codex',     # Agentic coding ($1.75/$14 per 1M)
                    'code_review': 'gpt-5.2-codex',
                    'math': 'o4-mini',              # Fast reasoning ($1.10/$4.40 per 1M)
                    'reasoning': 'o3-pro',          # Deep reasoning (Responses API)
                    'social': 'gpt-5',              # General purpose ($1.25/$10 per 1M)
                    'research': 'gpt-5.2',          # Flagship thinking ($1.75/$14 per 1M)
                    'analysis': 'gpt-5.2',
                    'creative': 'gpt-5',
                    'quick': 'gpt-5',
                },
                cost_per_token=0.00175,
                rate_limit=60
            ),

            'anthropic': ProviderConfig(
                name='anthropic',
                api_key=os.getenv('ANTHROPIC_API_KEY'),
                base_url='https://api.anthropic.com/v1',
                models={
                    'coding': 'claude-opus-4-6',    # Opus for code (012's rule)
                    'code_review': 'claude-opus-4-6',
                    'math': 'claude-opus-4-6',
                    'reasoning': 'claude-opus-4-6',
                    'social': 'claude-sonnet-4-5-20250929',
                    'research': 'claude-sonnet-4-5-20250929',
                    'analysis': 'claude-sonnet-4-5-20250929',
                    'creative': 'claude-haiku-4-5-20251001',
                    'quick': 'claude-haiku-4-5-20251001',
                },
                cost_per_token=0.015,
                rate_limit=50
            ),

            'grok': ProviderConfig(
                name='grok',
                api_key=os.getenv('GROK_API_KEY') or os.getenv('XAI_API_KEY'),
                base_url='https://api.x.ai/v1',
                models={
                    'coding': 'grok-code-fast-1',   # Agentic coding ($0.20/$1.50 per 1M)
                    'code_review': 'grok-4',         # Flagship ($3/$15 per 1M)
                    'math': 'grok-4',
                    'reasoning': 'grok-4',
                    'social': 'grok-4',              # Grok primary for social/edgy
                    'research': 'grok-4',
                    'analysis': 'grok-4',
                    'creative': 'grok-4',
                    'quick': 'grok-4-fast',          # Fast reasoning ($0.20/$0.50 per 1M)
                },
                cost_per_token=0.0002,
                rate_limit=30
            ),

            'gemini': ProviderConfig(
                name='gemini',
                api_key=os.getenv('GEMINI_API_KEY'),
                base_url='https://generativelanguage.googleapis.com/v1',
                models={
                    'coding': 'gemini-2.5-pro',
                    'code_review': 'gemini-2.5-pro',
                    'math': 'gemini-2.5-pro',       # Thinking model for math
                    'reasoning': 'gemini-2.5-pro',
                    'social': 'gemini-2.5-flash',
                    'research': 'gemini-2.5-pro',   # Gemini primary for research
                    'analysis': 'gemini-2.5-pro',
                    'creative': 'gemini-2.5-flash',
                    'quick': 'gemini-2.5-flash',
                },
                cost_per_token=0.0005,
                rate_limit=60
            ),

            # OpenRouter is intentionally absent from the ordinary fallback
            # order. It is available for exact provider/model assignments from
            # the governed AutoResearch configured-gateway runner.
            'openrouter': ProviderConfig(
                name='openrouter',
                api_key=os.getenv('OPENROUTER_API_KEY'),
                base_url='https://openrouter.ai/api/v1',
                models={
                    'coding': 'moonshotai/kimi-k3',
                    'code_review': 'moonshotai/kimi-k3',
                    'math': 'moonshotai/kimi-k3',
                    'reasoning': 'moonshotai/kimi-k3',
                    'research': 'moonshotai/kimi-k3',
                    'analysis': 'moonshotai/kimi-k3',
                    'creative': 'moonshotai/kimi-k3',
                    'quick': 'moonshotai/kimi-k3',
                },
                cost_per_token=0.000003,
                rate_limit=30,
                timeout=120,
                output_cost_per_token=0.000015,
                automatic_routing_enabled=False,
            )
        }

    def call_with_fallback(self, prompt: str, task_type: str = "general",
                          max_retries: int = 3) -> GatewayResult:
        """
        Call AI providers with automatic fallback

        Args:
            prompt: The prompt to send to AI
            task_type: Type of task (code_review, analysis, creative, quick)
            max_retries: Maximum number of provider retries

        Returns:
            GatewayResult with response and metadata
        """
        self.usage_stats['calls'] += 1
        self.usage_stats['task_distribution'][task_type] = \
            self.usage_stats['task_distribution'].get(task_type, 0) + 1

        # Get provider priority order for this task
        provider_order = self._get_provider_priority(task_type)

        for provider_name in provider_order:
            provider = self.providers[provider_name]

            if not provider.api_key:
                continue

            try:
                start_time = time.time()
                response = self._call_provider(provider, prompt, task_type)
                duration = time.time() - start_time

                # Estimate cost (rough calculation)
                cost_estimate = len(prompt.split()) * provider.cost_per_token

                # Track usage
                self.usage_stats['provider_usage'][provider_name] = \
                    self.usage_stats['provider_usage'].get(provider_name, 0) + 1

                return GatewayResult(
                    response=response,
                    provider=provider_name,
                    model=provider.models.get(task_type, 'default'),
                    duration=duration,
                    cost_estimate=cost_estimate,
                    success=True
                )

            except Exception as e:
                logger.warning(f"[U+26A0]️ {provider_name} failed: {e}")
                self.usage_stats['failures'] += 1
                continue

        # All providers failed
        return GatewayResult(
            response="",
            provider="none",
            model="",
            duration=0,
            cost_estimate=0,
            success=False
        )

    def call_optimized(self, prompt: str, task_type: str = "general") -> GatewayResult:
        """
        Call the most cost-effective provider available for the task

        Args:
            prompt: The prompt to send
            task_type: Type of task

        Returns:
            GatewayResult from cheapest available provider
        """
        # Sort providers by cost for this task
        available_providers = [
            (name, config) for name, config in self.providers.items()
            if config.api_key and config.automatic_routing_enabled
        ]

        # Sort by cost_per_token ascending (cheapest first)
        available_providers.sort(key=lambda x: x[1].cost_per_token)

        for provider_name, provider in available_providers:
            try:
                start_time = time.time()
                response = self._call_provider(provider, prompt, task_type)
                duration = time.time() - start_time

                cost_estimate = len(prompt.split()) * provider.cost_per_token

                return GatewayResult(
                    response=response,
                    provider=provider_name,
                    model=provider.models.get(task_type, 'default'),
                    duration=duration,
                    cost_estimate=cost_estimate,
                    success=True
                )

            except Exception as e:
                logger.debug(f"Cost-optimized {provider_name} failed: {e}")
                continue

        return GatewayResult("", "none", "", 0, 0, False)

    def classify_and_call(self, prompt: str) -> GatewayResult:
        """Auto-classify prompt into task type, then route to best provider.

        This is the orchestration bridge: OpenClaw intent -> classify -> route.
        Reports model selection to DAEmon if available.
        """
        task_type = classify_task(prompt)
        logger.info(f"[AI-GATEWAY] Classified as '{task_type}' -> {RECOMMENDED_MODELS.get(task_type, ['?'])[0]}")

        result = self.call_with_fallback(prompt, task_type)

        # Report to DAEmon (cardiovascular observation)
        if result.success:
            self._report_model_selection(task_type, result.provider, result.model)

        return result

    def _report_model_selection(self, task_type: str, provider: str, model: str) -> None:
        """Report model selection to central DAEmon for cardiovascular tracking."""
        try:
            from modules.infrastructure.dae_daemon.src.dae_adapter import CentralDAEAdapter
            if not hasattr(self, '_dae_adapter'):
                self._dae_adapter = CentralDAEAdapter(
                    dae_id="ai_gateway", dae_name="AI Gateway",
                    domain="ai_intelligence",
                    module_path="modules.ai_intelligence.ai_gateway.src.ai_gateway",
                )
                self._dae_adapter.register()
            self._dae_adapter.report_action(
                action_type="model_selection",
                target=model,
                result=f"task={task_type} provider={provider} model={model}",
            )
        except Exception:
            pass  # Graceful if DAEmon not available

    def _get_provider_priority(self, task_type: str) -> List[str]:
        """Get provider priority order for task type.

        012's activity routing matrix (Feb 2026):
            coding     -> Opus (anthropic) first
            math       -> o4-mini/o3 (openai) first
            reasoning  -> o3/o3-pro (openai) first
            social     -> Grok-4 first (less inhibited)
            research   -> Gemini first (deep research)
        """
        task_routing = {
            'coding': ['anthropic', 'openai', 'gemini', 'grok'],
            'code_review': ['anthropic', 'openai', 'gemini', 'grok'],
            'math': ['openai', 'gemini', 'anthropic', 'grok'],
            'reasoning': ['openai', 'gemini', 'anthropic', 'grok'],
            'social': ['grok', 'openai', 'anthropic', 'gemini'],
            'research': ['gemini', 'openai', 'anthropic', 'grok'],
            'analysis': ['openai', 'anthropic', 'gemini', 'grok'],
            'creative': ['anthropic', 'openai', 'gemini', 'grok'],
            'quick': ['grok', 'gemini', 'openai', 'anthropic'],
        }

        return task_routing.get(task_type, ['anthropic', 'openai', 'gemini', 'grok'])

    def _call_provider(self, provider: ProviderConfig, prompt: str, task_type: str) -> str:
        """Call specific AI provider"""

        model = provider.models.get(task_type, provider.models.get('quick', 'default'))

        if provider.name in {'openai', 'openrouter'}:
            return self._call_openai(provider, prompt, model)
        elif provider.name == 'anthropic':
            return self._call_anthropic(provider, prompt, model)
        elif provider.name == 'grok':
            return self._call_grok(provider, prompt, model)
        elif provider.name == 'gemini':
            return self._call_gemini(provider, prompt, model)
        else:
            raise ValueError(f"Unknown provider: {provider.name}")

    def _call_openai(self, provider: ProviderConfig, prompt: str, model: str) -> str:
        """Call OpenAI API"""
        default_max_tokens = 4096 if provider.name == 'openrouter' and model == 'moonshotai/kimi-k3' else 1000
        max_tokens = self._get_provider_max_tokens(provider.name, default_max_tokens)
        temperature = self._get_provider_temperature(provider.name, 0.7)
        headers = {
            'Authorization': f'Bearer {provider.api_key}',
            'Content-Type': 'application/json'
        }

        data = {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
        }
        if provider.name == 'openrouter' and model == 'moonshotai/kimi-k3':
            # OpenRouter lists Kimi K3 with mandatory max reasoning and without
            # temperature support. Preserve the published request contract.
            data['reasoning'] = {'effort': 'max'}
        else:
            data['temperature'] = temperature

        response = requests.post(
            f"{provider.base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=provider.timeout
        )
        response.raise_for_status()

        result = response.json()
        return result['choices'][0]['message']['content'].strip()

    def _call_anthropic(self, provider: ProviderConfig, prompt: str, model: str) -> str:
        """Call Anthropic API"""
        max_tokens = self._get_provider_max_tokens(provider.name, 1000)
        temperature = self._get_provider_temperature(provider.name, 0.7)
        headers = {
            'x-api-key': provider.api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }

        data = {
            'model': model,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'messages': [{'role': 'user', 'content': prompt}]
        }

        response = requests.post(
            f"{provider.base_url}/messages",
            headers=headers,
            json=data,
            timeout=provider.timeout
        )
        response.raise_for_status()

        result = response.json()
        return result['content'][0]['text'].strip()

    def _call_grok(self, provider: ProviderConfig, prompt: str, model: str) -> str:
        """Call Grok API"""
        max_tokens = self._get_provider_max_tokens(provider.name, 1000)
        temperature = self._get_provider_temperature(provider.name, 0.7)
        headers = {
            'Authorization': f'Bearer {provider.api_key}',
            'Content-Type': 'application/json'
        }

        data = {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': temperature
        }

        response = requests.post(
            f"{provider.base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=provider.timeout
        )
        response.raise_for_status()

        result = response.json()
        return result['choices'][0]['message']['content'].strip()

    def _call_gemini(self, provider: ProviderConfig, prompt: str, model: str) -> str:
        """Call Google Gemini API"""
        max_tokens = self._get_provider_max_tokens(provider.name, 1000)
        temperature = self._get_provider_temperature(provider.name, 0.7)
        data = {
            'contents': [{
                'parts': [{'text': prompt}]
            }],
            'generationConfig': {
                'maxOutputTokens': max_tokens,
                'temperature': temperature
            }
        }

        params = {
            'key': provider.api_key
        }

        response = requests.post(
            f"{provider.base_url}/models/{model}:generateContent",
            params=params,
            json=data,
            timeout=provider.timeout
        )
        response.raise_for_status()

        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text'].strip()

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            'total_calls': self.usage_stats['calls'],
            'failure_rate': self.usage_stats['failures'] / max(self.usage_stats['calls'], 1),
            'provider_usage': self.usage_stats['provider_usage'],
            'task_distribution': self.usage_stats['task_distribution']
        }

    def get_available_providers(self) -> List[str]:
        """Get list of providers with valid API keys"""
        return [name for name, config in self.providers.items() if config.api_key]


# Convenience functions
def quick_call(prompt: str, task_type: str = "general") -> str:
    """Quick gateway call without creating instance"""
    gateway = AIGateway()
    result = gateway.call_with_fallback(prompt, task_type)
    return result.response if result.success else "AI call failed"


def test_gateway() -> bool:
    """Test gateway functionality"""
    gateway = AIGateway()

    # Test basic connectivity
    providers = gateway.get_available_providers()
    if not providers:
        print("[ERROR] No AI providers configured")
        return False

    print(f"[SUCCESS] Found {len(providers)} configured providers: {', '.join(providers)}")

    # Test simple call
    try:
        result = gateway.call_with_fallback("Hello, test message", "quick")
        if result.success:
            print(f"[SUCCESS] Gateway test successful - {result.provider} responded in {result.duration:.2f}s")
            return True
        else:
            print("[ERROR] Gateway test failed - no providers responded")
            return False
    except Exception as e:
        print(f"[ERROR] Gateway test error: {e}")
        return False


if __name__ == '__main__':
    # CLI interface
    import argparse

    parser = argparse.ArgumentParser(description='FoundUps AI Gateway')
    parser.add_argument('--test', action='store_true', help='Test gateway connectivity')
    parser.add_argument('--call', help='Make a test call')
    parser.add_argument('--task-type', default='general', help='Task type for call')
    parser.add_argument('--stats', action='store_true', help='Show usage statistics')

    args = parser.parse_args()

    gateway = AIGateway()

    if args.test:
        success = test_gateway()
        exit(0 if success else 1)

    elif args.call:
        result = gateway.call_with_fallback(args.call, args.task_type)
        if result.success:
            print(f"[AI] {result.provider} ({result.model}): {result.response}")
            print(f"[TIME] {result.duration:.2f}s | [COST] ~${result.cost_estimate:.4f}")
        else:
            print("[ERROR] Call failed - no providers available")
            exit(1)

    elif args.stats:
        stats = gateway.get_usage_stats()
        print("[STATS] AI Gateway Usage Statistics:")
        print(f"   Total calls: {stats['total_calls']}")
        print(f"   Failure rate: {stats['failure_rate']:.2%}")
        print(f"   Provider usage: {stats['provider_usage']}")
        print(f"   Task distribution: {stats['task_distribution']}")

    else:
        parser.print_help()
