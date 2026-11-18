"""
test_decision_logic.py - Hermetic unit tests for the music-vs-talk decision.

NO live models, NO audio files, NO network. Every test injects crafted feature
vectors and/or whisper segment dicts and asserts the REAL decision logic in
_decide. This is the non-vacuous core: it proves the lyrics-as-text confound is
defeated at the signal level (the whole reason Approach B was chosen).

Slice: RND_MUSIC_VS_TALK_DETECTION_POC
"""

import importlib

import pytest

from modules.ai_intelligence.audio_content_classifier.src import audio_content_classifier as acc
from modules.ai_intelligence.audio_content_classifier.src import feature_thresholds as ft


def _music_features():
    """Hand-crafted instrumental-music feature vector."""
    return {
        "spectral_flatness": 0.10,          # tonal -> music
        "harmonic_percussive_ratio": 3.5,   # sustained harmonics -> music
        "zero_crossing_rate": 0.05,         # low ZCR -> music
        "tempo_bpm": 120.0,                 # stable musical tempo
        "beat_strength": 0.85,              # strong beat -> music
        "rms_dynamic_range": 0.08,          # compressed/sustained -> music
        "mfcc_var": 20.0,                   # steady timbre
    }


def _speech_features():
    """Hand-crafted talking-head speech feature vector."""
    return {
        "spectral_flatness": 0.55,          # noise-like -> talk
        "harmonic_percussive_ratio": 0.6,   # weak sustained harmonics -> talk
        "zero_crossing_rate": 0.22,         # high ZCR (fricatives) -> talk
        "tempo_bpm": 0.0,                   # no stable tempo
        "beat_strength": 0.10,              # no beat -> talk
        "rms_dynamic_range": 0.45,          # wide dynamics / pauses -> talk
        "mfcc_var": 95.0,                   # rapid phoneme shifts -> talk
    }


def test_decide_pure_music_features():
    """Instrumental-music features -> music, confidence > 0.7."""
    result = acc._decide(_music_features())
    assert result.label == "music"
    assert result.confidence > 0.7
    assert result.method == "acoustic"


def test_decide_pure_speech_features():
    """Speech features -> talk, confidence > 0.7."""
    result = acc._decide(_speech_features())
    assert result.label == "talk"
    assert result.confidence > 0.7
    assert result.method == "acoustic"


def test_lyrics_confound_sung_words():
    """THE CONFOUND TEST.

    Features are acoustically MUSIC, but we inject whisper segments containing
    real transcribed WORDS plus a HIGH avg_no_speech_prob (whisper itself doubts
    speech). Fusion must STILL return 'music' -> proves text presence does not
    flip the label, which is exactly where text-only methods fail.
    """
    features = _music_features()
    # whisper transcribed lyrics-as-words yet flagged high no_speech_prob
    segments = [
        {"text": "we are the champions my friend", "no_speech_prob": 0.82, "compression_ratio": 2.6},
        {"text": "and we'll keep on fighting", "no_speech_prob": 0.77, "compression_ratio": 2.7},
    ]
    stt = acc.aggregate_stt_signals(segments)
    result = acc._decide(features, stt)
    assert result.label == "music"
    assert result.method == "acoustic+stt_fusion"
    # fusion signals must be surfaced for auditability
    assert "avg_no_speech_prob" in result.signals
    assert result.signals["avg_no_speech_prob"] >= 0.7


def test_rap_spoken_over_beat():
    """Borderline rap/spoken-over-beat: words + steady strong beat + speech-like ZCR.

    Documented tie-break: beat_strength threshold wins -> 'music'. Method must be
    acoustic+stt_fusion because whisper segments are supplied.
    """
    features = {
        "spectral_flatness": 0.32,          # slightly noisy
        "harmonic_percussive_ratio": 1.7,   # moderate harmonics
        "zero_crossing_rate": 0.14,         # speech-ish ZCR
        "tempo_bpm": 95.0,                  # hip-hop tempo band
        "beat_strength": 0.80,              # STRONG beat -> tie-break to music
        "rms_dynamic_range": 0.20,          # moderate
        "mfcc_var": 50.0,                   # moderate
    }
    segments = [
        {"text": "spitting bars over this beat", "no_speech_prob": 0.30, "compression_ratio": 2.1},
    ]
    stt = acc.aggregate_stt_signals(segments)
    result = acc._decide(features, stt)
    assert result.label == "music"
    assert result.method == "acoustic+stt_fusion"


def test_thresholds_externalized(monkeypatch):
    """Overriding a feature_thresholds constant moves the decision boundary,
    proving tunability without touching decision logic (live-eval calibration).
    """
    # A near-neutral feature set that lands on 'talk' by default.
    features = {
        "spectral_flatness": 0.30,
        "harmonic_percussive_ratio": 1.5,
        "zero_crossing_rate": 0.12,
        "tempo_bpm": 200.0,                 # outside default musical band
        "beat_strength": 0.40,              # just below default music threshold
        "rms_dynamic_range": 0.22,
        "mfcc_var": 55.0,
    }
    baseline = acc._decide(features)

    # Lower the beat threshold so this same vector now reads as music.
    patched = dict(ft.THRESHOLDS)
    patched["beat_strength_music_above"] = 0.20
    patched["tempo_bpm_music_high"] = 220.0
    monkeypatch.setattr(ft, "THRESHOLDS", patched)
    tuned = acc._decide(features)

    assert baseline.label != tuned.label or baseline.signals["_score"] < tuned.signals["_score"]
    # specifically: the tuned, looser thresholds should now classify as music
    assert tuned.label == "music"


def test_aggregate_stt_signals_empty():
    """No segments -> empty fusion dict (acoustic-only path)."""
    assert acc.aggregate_stt_signals(None) == {}
    assert acc.aggregate_stt_signals([]) == {}
    # malformed entries are ignored, not raised
    assert acc.aggregate_stt_signals([{"text": "no probs here"}, "not-a-dict"]) == {}


def test_module_imports_without_heavy_deps():
    """The module must import cleanly even if heavy deps are absent (guarded)."""
    mod = importlib.reload(acc)
    assert hasattr(mod, "classify_content")
    assert hasattr(mod, "ClassificationResult")
