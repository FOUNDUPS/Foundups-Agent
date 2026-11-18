"""
test_classify_contract.py - Hermetic API/contract + fail-safe tests.

NO live models, NO real audio, NO network. The orchestrator classify_content is
exercised with extract_acoustic_features and audio loading monkeypatched, so the
wiring (features -> _decide) is asserted without touching disk or any model.

Slice: RND_MUSIC_VS_TALK_DETECTION_POC
"""

import builtins

import pytest

from modules.ai_intelligence.audio_content_classifier.src import audio_content_classifier as acc


def _music_features():
    return {
        "spectral_flatness": 0.10,
        "harmonic_percussive_ratio": 3.5,
        "zero_crossing_rate": 0.05,
        "tempo_bpm": 120.0,
        "beat_strength": 0.85,
        "rms_dynamic_range": 0.08,
        "mfcc_var": 20.0,
    }


def test_classify_content_mocks_extractor(monkeypatch, tmp_path):
    """classify_content wires extracted features -> _decide, never touching a model.

    We monkeypatch the librosa load + feature extraction so no real audio/model
    runs; the path merely needs to exist for the fail-safe gate to pass.
    """
    fake_path = tmp_path / "clip.wav"
    fake_path.write_bytes(b"RIFF....")  # existence only; never really decoded

    # Stub librosa.load to return a dummy waveform without decoding the bytes.
    import types
    fake_librosa = types.SimpleNamespace(load=lambda *a, **k: ([0.0, 0.1, 0.0], 16000))
    monkeypatch.setitem(__import__("sys").modules, "librosa", fake_librosa)
    monkeypatch.setattr(acc, "extract_acoustic_features", lambda *a, **k: _music_features())

    result = acc.classify_content(str(fake_path))
    assert result.label == "music"
    assert result.method in ("acoustic", "acoustic+stt_fusion")
    assert result.confidence > 0.0


def test_classify_content_fusion_via_segments(monkeypatch, tmp_path):
    """Injected segments flip method to acoustic+stt_fusion through classify_content."""
    fake_path = tmp_path / "clip.wav"
    fake_path.write_bytes(b"RIFF....")
    import types
    fake_librosa = types.SimpleNamespace(load=lambda *a, **k: ([0.0, 0.1], 16000))
    monkeypatch.setitem(__import__("sys").modules, "librosa", fake_librosa)
    monkeypatch.setattr(acc, "extract_acoustic_features", lambda *a, **k: _music_features())

    segments = [{"text": "sung words", "no_speech_prob": 0.8, "compression_ratio": 2.6}]
    result = acc.classify_content(str(fake_path), segments=segments)
    assert result.method == "acoustic+stt_fusion"
    assert result.label == "music"


def test_failsafe_missing_file():
    """Nonexistent path -> unavailable fail-safe, no exception."""
    result = acc.classify_content("/no/such/file/at/all.wav")
    assert result.label == "talk"
    assert result.confidence == 0.0
    assert result.method == "unavailable"


def test_failsafe_missing_deps(monkeypatch, tmp_path):
    """Simulated ImportError on librosa -> unavailable, no hang/raise."""
    fake_path = tmp_path / "clip.wav"
    fake_path.write_bytes(b"RIFF....")

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "librosa":
            raise ImportError("simulated: librosa not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    result = acc.classify_content(str(fake_path))
    assert result.method == "unavailable"
    assert result.label == "talk"
    assert result.confidence == 0.0


def test_failsafe_audio_load_failure(monkeypatch, tmp_path):
    """librosa.load raising (corrupt file) -> unavailable, no exception escapes."""
    fake_path = tmp_path / "clip.wav"
    fake_path.write_bytes(b"not-audio")
    import types

    def _boom(*a, **k):
        raise RuntimeError("corrupt audio")

    fake_librosa = types.SimpleNamespace(load=_boom)
    monkeypatch.setitem(__import__("sys").modules, "librosa", fake_librosa)
    result = acc.classify_content(str(fake_path))
    assert result.method == "unavailable"


def test_signals_dict_keys_present():
    """Every successful result exposes all documented acoustic signal keys."""
    result = acc._decide(_music_features())
    for key in acc.ACOUSTIC_SIGNAL_KEYS:
        assert key in result.signals, f"missing documented signal key: {key}"


def test_classification_result_shape():
    """ClassificationResult fields match the published contract."""
    result = acc._decide(_music_features())
    assert result.label in ("music", "talk")
    assert 0.0 <= result.confidence <= 1.0
    assert result.method in ("acoustic", "acoustic+stt_fusion", "unavailable")
    assert isinstance(result.signals, dict)
