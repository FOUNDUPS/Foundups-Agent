#!/usr/bin/env python3
"""Tests for audio provider registry and voice cloning policy."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from modules.infrastructure.shared_utilities.audio_provider_registry import (
    AudioLicense,
    AudioProvider,
    AudioProviderRegistry,
    AudioProviderType,
    get_audio_registry,
    get_preferred_asr,
    get_preferred_tts,
    is_voxtral_allowed,
    reset_registry,
)
from modules.infrastructure.shared_utilities.voice_cloning_policy import (
    PolicyResult,
    VoiceCloneRequest,
    VoiceCloningPolicy,
    get_voice_policy,
    reset_policy,
)


class TestAudioProviderRegistry:
    """Tests for AudioProviderRegistry."""

    def setup_method(self):
        reset_registry()

    def teardown_method(self):
        reset_registry()

    def test_get_preferred_asr_returns_cohere_transcribe(self):
        """Cohere Transcribe should be preferred ASR."""
        asr = get_preferred_asr()
        assert asr is not None
        assert asr.name == "cohere_transcribe"
        assert asr.preferred is True
        assert asr.production_enabled is True

    def test_get_preferred_tts_returns_qwen3_tts(self):
        """Qwen3-TTS should be preferred TTS."""
        tts = get_preferred_tts()
        assert tts is not None
        assert tts.name == "qwen3_tts"
        assert tts.preferred is True
        assert tts.production_enabled is True

    def test_voxtral_is_not_production_enabled(self):
        """Voxtral TTS should be blocked in production."""
        registry = get_audio_registry()
        assert registry.is_production_enabled("voxtral_tts_eval") is False

    def test_is_voxtral_allowed_returns_false_by_default(self, monkeypatch):
        """is_voxtral_allowed should return False without env override."""
        monkeypatch.delenv("AUDIO_ALLOW_EVAL_PROVIDERS", raising=False)
        assert is_voxtral_allowed() is False

    def test_is_voxtral_allowed_with_env_override(self, monkeypatch):
        """is_voxtral_allowed should return True with env override."""
        monkeypatch.setenv("AUDIO_ALLOW_EVAL_PROVIDERS", "1")
        assert is_voxtral_allowed() is True

    def test_list_voice_cloning_providers(self):
        """Should list providers with voice cloning capability."""
        registry = get_audio_registry()
        cloning_providers = registry.list_voice_cloning_providers()
        names = [p.name for p in cloning_providers]
        assert "qwen3_tts" in names
        assert "voxtral_tts_eval" in names
        assert "edge_tts" not in names

    def test_list_production_only_providers(self):
        """Should filter out eval-only providers."""
        registry = get_audio_registry()
        prod_providers = registry.list_providers(production_only=True)
        names = [p.name for p in prod_providers]
        assert "voxtral_tts_eval" not in names
        assert "cohere_transcribe" in names
        assert "qwen3_tts" in names


class TestVoiceCloningPolicy:
    """Tests for VoiceCloningPolicy."""

    def setup_method(self):
        reset_policy()

    def teardown_method(self):
        reset_policy()

    def test_deny_without_whitelist(self, tmp_path):
        """Should deny if voice not in whitelist."""
        policy = VoiceCloningPolicy(
            allowed_voices=set(),
            consent_store_path=tmp_path / "consents.json",
        )
        request = VoiceCloneRequest(
            voice_id="voice_012",
            requester="test",
            purpose="test",
        )
        result = policy.check(request)
        assert result.allowed is False
        assert "whitelist" in result.reason.lower()

    def test_deny_without_consent(self, tmp_path):
        """Should deny if consent not recorded."""
        policy = VoiceCloningPolicy(
            allowed_voices={"voice_012"},
            consent_store_path=tmp_path / "consents.json",
        )
        request = VoiceCloneRequest(
            voice_id="voice_012",
            requester="test",
            purpose="test",
        )
        result = policy.check(request)
        assert result.allowed is False
        assert "consent" in result.reason.lower()

    def test_allow_with_whitelist_and_consent(self, tmp_path):
        """Should allow with valid whitelist and consent."""
        policy = VoiceCloningPolicy(
            allowed_voices={"voice_012"},
            consent_store_path=tmp_path / "consents.json",
        )
        policy.record_consent("voice_012", "operator_012")
        request = VoiceCloneRequest(
            voice_id="voice_012",
            requester="test",
            purpose="test",
        )
        result = policy.check(request)
        assert result.allowed is True

    def test_deny_with_expired_consent(self, tmp_path):
        """Should deny if consent has expired."""
        policy = VoiceCloningPolicy(
            allowed_voices={"voice_012"},
            consent_store_path=tmp_path / "consents.json",
        )
        # Record consent that expired yesterday
        policy.record_consent(
            "voice_012",
            "operator_012",
            expires_at=datetime.utcnow() - timedelta(days=1),
        )
        request = VoiceCloneRequest(
            voice_id="voice_012",
            requester="test",
            purpose="test",
        )
        result = policy.check(request)
        assert result.allowed is False
        assert "expired" in result.reason.lower()

    def test_kill_switch_blocks_all(self, tmp_path):
        """Kill switch should block all requests."""
        policy = VoiceCloningPolicy(
            allowed_voices={"voice_012"},
            consent_store_path=tmp_path / "consents.json",
        )
        policy.record_consent("voice_012", "operator_012")
        policy.engage_kill_switch()

        request = VoiceCloneRequest(
            voice_id="voice_012",
            requester="test",
            purpose="test",
        )
        result = policy.check(request)
        assert result.allowed is False
        assert "kill switch" in result.reason.lower()

    def test_disengage_kill_switch_restores_access(self, tmp_path):
        """Disengaging kill switch should restore access."""
        policy = VoiceCloningPolicy(
            allowed_voices={"voice_012"},
            consent_store_path=tmp_path / "consents.json",
        )
        policy.record_consent("voice_012", "operator_012")
        policy.engage_kill_switch()
        policy.disengage_kill_switch()

        request = VoiceCloneRequest(
            voice_id="voice_012",
            requester="test",
            purpose="test",
        )
        result = policy.check(request)
        assert result.allowed is True

    def test_consent_persistence(self, tmp_path):
        """Consents should persist across policy instances."""
        consent_path = tmp_path / "consents.json"

        # Create policy and record consent
        policy1 = VoiceCloningPolicy(
            allowed_voices={"voice_012"},
            consent_store_path=consent_path,
        )
        policy1.record_consent("voice_012", "operator_012")
        policy1.add_to_whitelist("voice_012")

        # Create new policy instance
        policy2 = VoiceCloningPolicy(
            consent_store_path=consent_path,
        )

        request = VoiceCloneRequest(
            voice_id="voice_012",
            requester="test",
            purpose="test",
        )
        result = policy2.check(request)
        assert result.allowed is True
