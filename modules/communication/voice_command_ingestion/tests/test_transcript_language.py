"""Language and timestamp evidence, using local fakes without model downloads."""
import json
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from modules.communication.voice_command_ingestion.src.voice_command_ingestion import (
    FasterWhisperSTT, get_batch_transcriber, get_voice_ingestion,
)


@pytest.mark.parametrize('language,detected', [('ja', 'ja'), (None, 'ja'), ('en', 'en')])
def test_stt_preserves_requested_and_reported_language(language, detected):
    stt = FasterWhisperSTT(language=language)
    stt._initialized = True
    stt._model = Mock()
    stt._model.transcribe.return_value = (
        [SimpleNamespace(text=' 福井の温泉 ', end=1.5, avg_logprob=-0.1)],
        SimpleNamespace(language=detected),
    )
    result = stt.transcribe(np.zeros(16000, dtype=np.float32))
    assert stt._model.transcribe.call_args.kwargs['language'] == language
    assert result.language == detected
    assert result.text == '福井の温泉'
    assert result.end_ms == 1500


@pytest.mark.parametrize('language', ['ja', None])
def test_english_only_model_rejects_non_english_before_loading(language):
    with pytest.raises(ValueError, match='English-only'):
        FasterWhisperSTT(model_size='base.en', language=language)


def test_voice_default_compatible_and_japanese_supported():
    assert get_voice_ingestion()._stt.language == 'en'
    assert get_voice_ingestion(language='ja')._stt.language == 'ja'


def test_batch_keeps_language_offsets_and_unicode_in_saved_evidence(tmp_path):
    batch = get_batch_transcriber(language='ja', output_dir=str(tmp_path))
    assert batch._stt.language == 'ja'
    batch._stt._initialized = True
    batch._stt._model = Mock()
    batch._stt._model.transcribe.return_value = (
        [SimpleNamespace(text='福井の温泉', end=1.5, avg_logprob=-0.1)],
        SimpleNamespace(language='ja'),
    )
    chunk = SimpleNamespace(audio=np.zeros(16000, dtype=np.float32), sample_rate=16000,
                            timestamp_ms=30000, duration_sec=20)
    segments = list(batch.transcribe_video('abc123', 'clip', [chunk]))
    assert segments[0].language == 'ja'
    assert segments[0].timestamp_sec == 30
    batch.save_transcripts_jsonl(segments, 'clip.jsonl')
    saved = json.loads((tmp_path / 'clip.jsonl').read_text(encoding='utf-8'))
    assert saved['text'] == '福井の温泉'
    assert saved['language'] == 'ja'
    assert saved['url'] == 'https://youtu.be/abc123?t=30'
