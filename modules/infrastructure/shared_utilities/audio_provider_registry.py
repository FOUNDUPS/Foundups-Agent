"""Audio provider registry with production gating.

Manages ASR (speech-to-text) and TTS (text-to-speech) provider selection
with explicit production/eval-only flags.

Provider Lifecycle:
    1. Register provider with metadata (name, type, license, production_enabled)
    2. Query preferred provider for role (asr/tts)
    3. Runtime checks gate eval-only providers from production paths

Usage:
    from modules.infrastructure.shared_utilities.audio_provider_registry import (
        get_audio_registry,
        AudioProviderType,
    )

    registry = get_audio_registry()

    # Get preferred ASR provider
    asr = registry.get_preferred("asr")
    print(f"Using {asr.name} for ASR")

    # Check if provider is production-ready
    if registry.is_production_enabled("voxtral_tts_eval"):
        # This will be False - voxtral is eval-only
        ...
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class AudioProviderType(str, Enum):
    """Audio provider capability type."""

    ASR = "asr"
    TTS = "tts"


class AudioLicense(str, Enum):
    """License classification for provider selection."""

    APACHE_2 = "apache-2.0"
    MIT = "mit"
    EVAL_ONLY = "eval-only"
    PROPRIETARY = "proprietary"


@dataclass
class AudioProvider:
    """Audio provider metadata."""

    name: str
    provider_type: AudioProviderType
    license: AudioLicense
    production_enabled: bool
    preferred: bool = False
    model_dir: str = ""
    description: str = ""
    voice_cloning: bool = False
    parameters: str = ""

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.provider_type.value,
            "license": self.license.value,
            "production_enabled": self.production_enabled,
            "preferred": self.preferred,
            "model_dir": self.model_dir,
            "voice_cloning": self.voice_cloning,
            "parameters": self.parameters,
        }


@dataclass
class AudioProviderRegistry:
    """Registry of available audio providers with production gating."""

    _providers: Dict[str, AudioProvider] = field(default_factory=dict)
    _initialized: bool = False

    def register(self, provider: AudioProvider) -> None:
        """Register an audio provider."""
        self._providers[provider.name] = provider

    def get(self, name: str) -> Optional[AudioProvider]:
        """Get provider by name."""
        return self._providers.get(name)

    def get_preferred(self, provider_type: str) -> Optional[AudioProvider]:
        """Get preferred provider for a type (asr/tts)."""
        ptype = AudioProviderType(provider_type)
        for provider in self._providers.values():
            if provider.provider_type == ptype and provider.preferred:
                return provider
        # Fallback to first production-enabled provider of type
        for provider in self._providers.values():
            if provider.provider_type == ptype and provider.production_enabled:
                return provider
        return None

    def is_production_enabled(self, name: str) -> bool:
        """Check if provider is enabled for production use."""
        provider = self._providers.get(name)
        if provider is None:
            return False
        return provider.production_enabled

    def list_providers(
        self, provider_type: Optional[str] = None, production_only: bool = False
    ) -> List[AudioProvider]:
        """List providers, optionally filtered."""
        result = []
        for provider in self._providers.values():
            if provider_type:
                ptype = AudioProviderType(provider_type)
                if provider.provider_type != ptype:
                    continue
            if production_only and not provider.production_enabled:
                continue
            result.append(provider)
        return result

    def list_voice_cloning_providers(self) -> List[AudioProvider]:
        """List providers with voice cloning capability."""
        return [p for p in self._providers.values() if p.voice_cloning]


# Singleton registry instance
_REGISTRY: Optional[AudioProviderRegistry] = None


def _env_truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


def _init_default_providers(registry: AudioProviderRegistry) -> None:
    """Initialize default provider registrations."""
    # ASR Providers
    registry.register(
        AudioProvider(
            name="cohere_transcribe",
            provider_type=AudioProviderType.ASR,
            license=AudioLicense.APACHE_2,
            production_enabled=True,
            preferred=True,
            model_dir="cohere-transcribe-2b",
            description="Cohere Transcribe 2B - open-source ASR",
            parameters="2B",
        )
    )
    registry.register(
        AudioProvider(
            name="whisper_local",
            provider_type=AudioProviderType.ASR,
            license=AudioLicense.MIT,
            production_enabled=True,
            preferred=False,
            model_dir="whisper-large-v3",
            description="OpenAI Whisper (local) - fallback ASR",
            parameters="1.5B",
        )
    )

    # TTS Providers
    registry.register(
        AudioProvider(
            name="qwen3_tts",
            provider_type=AudioProviderType.TTS,
            license=AudioLicense.APACHE_2,
            production_enabled=True,
            preferred=True,
            model_dir="qwen3-tts",
            description="Qwen3-TTS - open-source TTS with voice cloning",
            voice_cloning=True,
            parameters="TBD",
        )
    )
    registry.register(
        AudioProvider(
            name="edge_tts",
            provider_type=AudioProviderType.TTS,
            license=AudioLicense.PROPRIETARY,
            production_enabled=True,
            preferred=False,
            model_dir="",
            description="Microsoft Edge TTS - cloud fallback",
            voice_cloning=False,
        )
    )
    registry.register(
        AudioProvider(
            name="voxtral_tts_eval",
            provider_type=AudioProviderType.TTS,
            license=AudioLicense.EVAL_ONLY,
            production_enabled=False,  # CRITICAL: eval-only, not production
            preferred=False,
            model_dir="voxtral-tts-eval",
            description="Mistral Voxtral TTS 4B - EVAL ONLY (licensing restrictions)",
            voice_cloning=True,
            parameters="4B",
        )
    )


def get_audio_registry() -> AudioProviderRegistry:
    """Get the singleton audio provider registry."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = AudioProviderRegistry()
        _init_default_providers(_REGISTRY)
        _REGISTRY._initialized = True
    return _REGISTRY


def reset_registry() -> None:
    """Reset registry (for testing)."""
    global _REGISTRY
    _REGISTRY = None


# Convenience functions
def get_preferred_asr() -> Optional[AudioProvider]:
    """Get preferred ASR provider."""
    return get_audio_registry().get_preferred("asr")


def get_preferred_tts() -> Optional[AudioProvider]:
    """Get preferred TTS provider."""
    return get_audio_registry().get_preferred("tts")


def is_voxtral_allowed() -> bool:
    """Check if Voxtral is allowed (always False in production)."""
    # Explicit env override for eval environments only
    if _env_truthy("AUDIO_ALLOW_EVAL_PROVIDERS", "0"):
        return True
    return get_audio_registry().is_production_enabled("voxtral_tts_eval")
