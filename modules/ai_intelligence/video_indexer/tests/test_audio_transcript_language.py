"""Test real analyzer conversion without YouTube requests or model downloads."""
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from modules.ai_intelligence.video_indexer.src.audio_analyzer import AudioAnalyzer


def test_batch_factory_gets_language_and_output_directory(tmp_path):
    analyzer = AudioAnalyzer(language='ja', output_dir=str(tmp_path))
    with patch('modules.communication.voice_command_ingestion.src.voice_command_ingestion.get_batch_transcriber') as factory:
        analyzer._get_batch_transcriber()
    factory.assert_called_once_with(model_size='base', language='ja', output_dir=str(tmp_path))


@pytest.mark.parametrize('languages,expected', [(['ja'], 'ja'), (['ja', 'en'], 'mixed'), (['unknown'], 'unknown')])
def test_video_language_and_chunk_offsets_survive_conversion(monkeypatch, languages, expected):
    extractor = Mock()
    extractor.stream_video_chunks.return_value = []
    monkeypatch.setitem(sys.modules, 'modules.platform_integration.youtube_live_audio.src.youtube_live_audio',
                        SimpleNamespace(VideoArchiveExtractor=lambda: extractor))
    ydl = Mock()
    ydl.extract_info.return_value = {'title': 'clip'}
    context = Mock()
    context.__enter__ = Mock(return_value=ydl)
    context.__exit__ = Mock(return_value=False)
    monkeypatch.setitem(sys.modules, 'yt_dlp', SimpleNamespace( YoutubeDL=lambda opts: context))
    analyzer = AudioAnalyzer()
    analyzer._batch_transcriber = Mock()
    analyzer._batch_transcriber.transcribe_video.return_value = [
        SimpleNamespace(text='福井の温泉', timestamp_sec=30+i*10, end_sec=40+i*10,
                        confidence=0.9, language=language)
        for i, language in enumerate(languages)
    ]
    result = analyzer.transcribe_video('abc123')
    assert result.language == expected
    assert result.segments[0].start_time == 30
    assert result.duration == 30+10*len(languages)


def test_local_file_passes_japanese_language(tmp_path):
    audio = tmp_path / 'audio.wav'
    audio.touch()
    analyzer = AudioAnalyzer(language='ja')
    analyzer._whisper = Mock()
    analyzer._whisper.transcribe.return_value = {'segments': [], 'language': 'ja', 'text': ''}
    result = analyzer.transcribe_file(str(audio))
    assert analyzer._whisper.transcribe.call_args.kwargs['language'] == 'ja'
    assert result.language == 'ja'
