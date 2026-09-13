from modules.communication.voice_command_ingestion import VoiceCommandIngestion
from modules.communication.voice_command_ingestion import FasterWhisperSTT, get_voice_ingestion
from types import SimpleNamespace

import numpy as np
import pytest


def test_default_trigger_token():
    ingestion = VoiceCommandIngestion()
    assert ingestion.trigger_token == "0102"


@pytest.mark.parametrize("language", ["en", "ja", None])
def test_whisper_receives_selected_language(language):
    calls = []
    segment = SimpleNamespace(text="日本語の伝言", end=1, avg_logprob=-0.1)
    stt = FasterWhisperSTT(language=language)
    stt._initialized = True
    stt._model = SimpleNamespace(transcribe=lambda audio, **kw: (calls.append(kw) or [segment], None))
    result = stt.transcribe(np.zeros(16000, dtype=np.float32))
    assert result.text == "日本語の伝言"
    assert calls[0]["language"] == language
    assert get_voice_ingestion(language=language)._stt.language == language


@pytest.mark.parametrize("language", ["ja", None])
def test_english_only_model_rejected_for_multilingual_requests(language):
    with pytest.raises(ValueError, match="English-only"):
        FasterWhisperSTT(model_size="base.en", language=language)


def test_default_stays_english_and_invalid_language_rejected():
    assert FasterWhisperSTT().language == "en"
    with pytest.raises(ValueError, match="language"):
        FasterWhisperSTT(language="ja-JP")
