"""
Unit tests for OpenClaw voice cue parsing and STT artifact tolerance.
"""

from contextlib import nullcontext
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from modules.infrastructure.cli.src.openclaw_voice import (
    _control_command,
    _extract_barge_payload,
    _is_meaningful_utterance,
    _is_meaningful_utterance_mode,
    _normalize_stt_aliases,
)


def test_speech_import_does_not_boot_main_menu():
    result = subprocess.run([sys.executable, "-c",
        "import sys; import modules.infrastructure.cli.src.openclaw_voice; "
        "assert 'modules.infrastructure.cli.src.main_menu' not in sys.modules"],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_whisper_backend_language_environment_and_override(monkeypatch):
    from modules.infrastructure.cli.src.openclaw_voice import WhisperSTTBackend
    monkeypatch.setenv("OPENCLAW_VOICE_STT_LANGUAGE", "ja")
    backend = WhisperSTTBackend()
    assert backend.available() and backend._stt.language == "ja"
    explicit = WhisperSTTBackend(language="en")
    assert explicit.available() and explicit._stt.language == "en"


@pytest.mark.parametrize("decoder", ["modern_string", "modern_list", "legacy_batch"])
def test_cohere_passes_japanese_to_processor(monkeypatch, decoder):
    from modules.infrastructure.cli.src import openclaw_voice as voice
    seen = []
    class Processor:
        def __call__(self, audio, **kwargs):
            seen.append(kwargs)
            return {"audio_chunk_index": [(0, None)]}
        def decode(self, tokens, **kwargs):
            assert kwargs["language"] == "ja"
            assert kwargs["audio_chunk_index"] == [(0, None)]
            return "日本語です" if decoder == "modern_string" else ["日本語です"]
        def batch_decode(self, tokens, **kwargs):
            return ["日本語です"]
    processor = Processor()
    if decoder == "legacy_batch":
        processor.decode = None
    model = SimpleNamespace(parameters=lambda: iter([SimpleNamespace(device="cpu")]),
                            generate=lambda **kw: [[1]])
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(no_grad=nullcontext))
    monkeypatch.setattr(voice, "_get_cohere_stt_singleton", lambda: (processor, model))
    result = voice.CohereTranscribeBackend(language="ja").transcribe(np.zeros(16000))
    assert result == "日本語です" and seen[0]["language"] == "ja"


def test_google_uses_japanese_locale(monkeypatch):
    from modules.infrastructure.cli.src.openclaw_voice import GoogleSTTBackend
    seen = []
    monkeypatch.setitem(sys.modules, "speech_recognition", SimpleNamespace(AudioData=lambda *a: a))
    backend = GoogleSTTBackend(language="ja")
    backend._recognizer = SimpleNamespace(recognize_google=lambda audio, **kw: seen.append(kw) or "日本語")
    assert backend.transcribe(np.zeros(16000)) == "日本語"
    assert seen == [{"language": "ja-JP"}]


def test_extract_barge_payload_accepts_standard_cue_prefix():
    is_barge, payload = _extract_barge_payload(
        "0102 come in come in",
        cue="0102",
        require_cue=True,
    )
    assert is_barge is True
    assert payload == "come in come in"


def test_extract_barge_payload_strips_repeated_cue_prefix():
    is_barge, payload = _extract_barge_payload(
        "0102 0102 come in come in",
        cue="0102",
        require_cue=True,
    )
    assert is_barge is True
    assert payload == "come in come in"


def test_extract_barge_payload_accepts_digit_artifact_variant():
    # STT artifact example from live logs.
    is_barge, payload = _extract_barge_payload(
        "0, 2, 0, 1, 0",
        cue="0102",
        require_cue=True,
    )
    assert is_barge is True
    assert payload == ""


def test_extract_barge_payload_accepts_spoken_numeric_prefix():
    is_barge, payload = _extract_barge_payload(
        "zero, one, zero, two, say affirmative",
        cue="0102",
        require_cue=True,
    )
    assert is_barge is True
    assert payload == "say affirmative"


def test_extract_barge_payload_rejects_noncue_when_required():
    is_barge, payload = _extract_barge_payload(
        "just testing voice input",
        cue="0102",
        require_cue=True,
    )
    assert is_barge is False
    assert payload == "just testing voice input"


def test_control_command_accepts_natural_exit_phrase():
    assert _control_command("no, let's exit out of this voice mode") == "exit"


def test_control_command_accepts_backend_switch_phrase():
    assert _control_command("switch backend to ironclaw") == "backend:ironclaw"
    assert _control_command("backend openclaw") == "backend:openclaw"


def test_is_meaningful_utterance_rejects_noise_fragments():
    assert _is_meaningful_utterance(". . . .") is False
    assert _is_meaningful_utterance("0 1 0") is False
    assert _is_meaningful_utterance("can you hear me") is True


def test_is_meaningful_utterance_allows_single_word_model_query():
    assert _is_meaningful_utterance("model") is True


def test_is_meaningful_utterance_rejects_weak_single_tokens():
    assert _is_meaningful_utterance("well") is False
    assert _is_meaningful_utterance("next") is False


def test_is_meaningful_utterance_strict_rejects_incomplete_fragment():
    assert _is_meaningful_utterance_mode("what's your", strict=True) is False
    assert _is_meaningful_utterance_mode("can you hear me now", strict=True) is True


def test_normalize_stt_aliases_maps_qwen_variants():
    assert _normalize_stt_aliases("are you quinn") == "are you qwen"
    assert _normalize_stt_aliases("switch model to coin") == "switch model to qwen"


def test_normalize_stt_aliases_normalizes_spoken_0102_prefix():
    assert _normalize_stt_aliases("zero one zero two say affirmative") == "0102 say affirmative"
    assert _normalize_stt_aliases("0 2 0 1 status") == "0102 status"
