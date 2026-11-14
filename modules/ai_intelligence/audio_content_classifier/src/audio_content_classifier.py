"""
audio_content_classifier.py - Acoustic music-vs-talk discriminator (R&D PoC).

=============================================================================
R&D PoC ONLY - NOT WIRED INTO SCHEDULING
Slice: RND_MUSIC_VS_TALK_DETECTION_POC   Worker-Lane: RND-MUSIC-TALK
=============================================================================

WHAT THIS IS (Approach B):
    A librosa-based acoustic music/speech discriminator, OPTIONALLY fused with
    openai-whisper segment no_speech_prob / compression_ratio. It answers ONE
    question about a short audio/video: is the dominant content MUSIC or TALK?

WHY ACOUSTIC (the lyrics-as-text confound):
    Text-only methods (transcript keyword gates, Gemma-on-transcript) are fooled
    by sung lyrics: a Suno song with words transcribes to words and looks like
    "talk". At the SIGNAL level, sung lyrics stay acoustically MUSIC (sustained
    harmonics, steady beat, low ZCR). This module decides on the waveform, so
    text presence does not flip the label. See feature_thresholds.py for the
    per-feature provenance.

WSP 84 REUSE MAP (cited file:line):
    - librosa MFCC/feature extraction pattern:
        modules/platform_integration/acoustic_lab/src/acoustic_processor.py:160
        (_extract_fingerprint -> librosa.feature.mfcc, n_mfcc=13)
    - audio fetch for the LIVE path (16kHz mono float32, unlisted-cookie support):
        modules/platform_integration/youtube_live_audio/src/youtube_live_audio.py:405
        (VideoArchiveExtractor.extract_audio; YT_DLP_COOKIES_BROWSER at :451)
    - whisper segment dicts carry no_speech_prob/avg_logprob/compression_ratio
        (openai-whisper transcribe standard; consumed here as injectable signals)
    - Gemma transcript tie-breaker (OPTIONAL, secondary, flag-gated):
        modules/ai_intelligence/video_indexer/src/gemma_segment_classifier.py:63
        ([music]/[applause] bracket keywords at :99-101)

WSP 49 / #819-#820 ISOLATION CONTRACT:
    This module MUST NOT import from, or be imported by,
    modules/platform_integration/youtube_shorts_scheduler. It is READ-ONLY w.r.t.
    the system: it reads audio/artifacts, never writes the index artifact, never
    re-indexes, never deletes. All heavy/optional integrations (librosa, whisper,
    VideoArchiveExtractor, Gemma) are LAZY-imported behind guards so this module
    imports cleanly with ZERO heavy deps installed, and unit tests run hermetically
    by injecting features + whisper segment dicts.

FAIL-SAFE CONTRACT (never raises into a caller, never hangs):
    On a missing file, missing dependency, or extraction failure, classify_content
    returns ClassificationResult(label="talk", confidence=0.0, method="unavailable").
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import feature_thresholds as ft

logger = logging.getLogger(__name__)

# Documented signal keys always present on a successful (non-unavailable) result.
ACOUSTIC_SIGNAL_KEYS = (
    "spectral_flatness",
    "harmonic_percussive_ratio",
    "zero_crossing_rate",
    "tempo_bpm",
    "beat_strength",
    "rms_dynamic_range",
    "mfcc_var",
)
# Optional fusion keys (present only when whisper segments are supplied/available).
STT_SIGNAL_KEYS = (
    "avg_no_speech_prob",
    "avg_compression_ratio",
)


@dataclass
class ClassificationResult:
    """Result of a music-vs-talk classification.

    Attributes:
        label: 'music' | 'talk'. On unavailable, fail-safe default is 'talk'.
        confidence: 0.0-1.0. 0.0 means UNAVAILABLE (no decision was made).
        method: 'acoustic' | 'acoustic+stt_fusion' | 'unavailable'.
        signals: dict of the feature values that drove the decision (see
            ACOUSTIC_SIGNAL_KEYS, optionally STT_SIGNAL_KEYS).
    """

    label: str
    confidence: float
    method: str
    signals: Dict[str, Any] = field(default_factory=dict)


def _unavailable(reason: str, partial_signals: Optional[Dict[str, Any]] = None) -> ClassificationResult:
    """Build the fail-safe result. Never raises, never hangs."""
    logger.warning("[AUDIO-CLASSIFY] unavailable: %s", reason)
    return ClassificationResult(
        label="talk",
        confidence=0.0,
        method="unavailable",
        signals=dict(partial_signals or {}),
    )


# ---------------------------------------------------------------------------
# Feature extraction (lazy librosa). Pure-ish: a function of the waveform.
# Unit tests do NOT call this; they monkeypatch it or call _decide directly.
# ---------------------------------------------------------------------------
def extract_acoustic_features(wav_float32_mono_16k, sample_rate: int = 16000) -> Dict[str, float]:
    """Extract classic music/speech discriminator features via librosa.

    Args:
        wav_float32_mono_16k: 1-D float32 numpy array, mono, ~16kHz.
        sample_rate: sample rate of the array (default 16000).

    Returns:
        dict with every key in ACOUSTIC_SIGNAL_KEYS.

    Raises:
        ImportError if librosa/numpy are not installed (caller guards this).
    The librosa.feature.mfcc usage mirrors acoustic_processor.py:189.
    """
    import numpy as np  # lazy
    import librosa  # lazy

    y = np.asarray(wav_float32_mono_16k, dtype=np.float32)
    if y.ndim > 1:
        y = np.mean(y, axis=0).astype(np.float32)

    # spectral flatness (tonal vs noise-like)
    flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))

    # harmonic / percussive energy ratio via HPSS
    harmonic, percussive = librosa.effects.hpss(y)
    h_energy = float(np.sum(harmonic.astype(np.float64) ** 2))
    p_energy = float(np.sum(percussive.astype(np.float64) ** 2))
    # sustained-harmonic content relative to total non-percussive baseline
    denom = p_energy + 1e-9
    hp_ratio = float(h_energy / denom)

    # zero crossing rate (speech fricatives -> high)
    zcr = float(np.mean(librosa.feature.zero_crossing_rate(y=y)))

    # tempo + beat strength (music -> stable strong beat)
    onset_env = librosa.onset.onset_strength(y=y, sr=sample_rate)
    tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sample_rate)
    tempo_bpm = float(np.atleast_1d(tempo)[0]) if tempo is not None else 0.0
    beat_strength = float(np.mean(onset_env)) if onset_env.size else 0.0

    # rms dynamic range (speech -> wide range with pauses)
    rms = librosa.feature.rms(y=y)[0]
    if rms.size:
        rms_dynamic_range = float(np.max(rms) - np.min(rms))
    else:
        rms_dynamic_range = 0.0

    # mfcc variance over time (weak supporting signal)
    mfcc = librosa.feature.mfcc(y=y, sr=sample_rate, n_mfcc=13)
    mfcc_var = float(np.mean(np.var(mfcc, axis=1)))

    return {
        "spectral_flatness": flatness,
        "harmonic_percussive_ratio": hp_ratio,
        "zero_crossing_rate": zcr,
        "tempo_bpm": tempo_bpm,
        "beat_strength": beat_strength,
        "rms_dynamic_range": rms_dynamic_range,
        "mfcc_var": mfcc_var,
    }


# ---------------------------------------------------------------------------
# STT fusion signal aggregation. Operates on INJECTED whisper segment dicts so
# unit tests need no model. Each segment is a dict with optional keys
# no_speech_prob / compression_ratio (openai-whisper standard).
# ---------------------------------------------------------------------------
def aggregate_stt_signals(segments: Optional[List[Dict[str, Any]]]) -> Dict[str, float]:
    """Aggregate whisper segment dicts into mean fusion signals.

    Returns an empty dict if no usable segments are provided (=> acoustic-only).
    """
    if not segments:
        return {}
    nsp_vals: List[float] = []
    cr_vals: List[float] = []
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        if "no_speech_prob" in seg and seg["no_speech_prob"] is not None:
            try:
                nsp_vals.append(float(seg["no_speech_prob"]))
            except (TypeError, ValueError):
                pass
        if "compression_ratio" in seg and seg["compression_ratio"] is not None:
            try:
                cr_vals.append(float(seg["compression_ratio"]))
            except (TypeError, ValueError):
                pass
    out: Dict[str, float] = {}
    if nsp_vals:
        out["avg_no_speech_prob"] = sum(nsp_vals) / len(nsp_vals)
    if cr_vals:
        out["avg_compression_ratio"] = sum(cr_vals) / len(cr_vals)
    return out


def _confidence_from_score(score: float) -> float:
    """Squash a signed weighted score to a 0.5-1.0 confidence magnitude.

    confidence 1.0 is asymptotic; a score of 0 yields 0.5 (max uncertainty,
    but still a real decision, distinct from 0.0 == unavailable).
    """
    import math

    mag = abs(score) / max(ft.SCORE_CONFIDENCE_SCALE, 1e-9)
    # logistic-ish squash mapped into [0.5, 1.0)
    conf = 0.5 + 0.5 * (1.0 - math.exp(-mag))
    # clamp into a sane, never-exactly-0.0 success band
    return float(min(0.999, max(0.5, conf)))


def _decide(features: Dict[str, float], stt_signals: Optional[Dict[str, float]] = None) -> ClassificationResult:
    """Core decision: weighted vote over acoustic features (+ optional STT fusion).

    Positive score => MUSIC, negative => TALK. This is the unit under test for
    the lyrics-confound and rap-over-beat cases; it touches NO disk or model.
    """
    stt_signals = stt_signals or {}
    th = ft.THRESHOLDS
    w = ft.WEIGHTS
    score = 0.0

    # spectral_flatness: low => music (+), high => talk (-)
    sf = features.get("spectral_flatness", 0.5)
    score += w["spectral_flatness"] * (th["spectral_flatness_music_below"] - sf) / max(th["spectral_flatness_music_below"], 1e-9)

    # harmonic_percussive_ratio: high => music (+)
    hp = features.get("harmonic_percussive_ratio", 1.0)
    score += w["harmonic_percussive_ratio"] * (hp - th["harmonic_percussive_ratio_music_above"]) / max(th["harmonic_percussive_ratio_music_above"], 1e-9)

    # zero_crossing_rate: high => talk (-)
    zcr = features.get("zero_crossing_rate", 0.1)
    score += w["zero_crossing_rate"] * (th["zero_crossing_rate_talk_above"] - zcr) / max(th["zero_crossing_rate_talk_above"], 1e-9)

    # beat_strength: high => music (+) -- strongest discriminator
    bs = features.get("beat_strength", 0.0)
    score += w["beat_strength"] * (bs - th["beat_strength_music_above"]) / max(th["beat_strength_music_above"], 1e-9)

    # tempo_bpm: within a musical band reinforces music (+), else mild talk (-)
    tempo = features.get("tempo_bpm", 0.0)
    if th["tempo_bpm_music_low"] <= tempo <= th["tempo_bpm_music_high"]:
        score += w["tempo_bpm"]
    else:
        score -= w["tempo_bpm"] * 0.5

    # rms_dynamic_range: wide => talk (-)
    rdr = features.get("rms_dynamic_range", 0.0)
    score += w["rms_dynamic_range"] * (th["rms_dynamic_range_talk_above"] - rdr) / max(th["rms_dynamic_range_talk_above"], 1e-9)

    # mfcc_var: high => talk (-)
    mv = features.get("mfcc_var", 0.0)
    score += w["mfcc_var"] * (th["mfcc_var_talk_above"] - mv) / max(th["mfcc_var_talk_above"], 1e-9)

    method = "acoustic"

    # ---- STT fusion (the lyrics-confound defense) ----
    if stt_signals:
        method = "acoustic+stt_fusion"
        nsp = stt_signals.get("avg_no_speech_prob")
        if nsp is not None and nsp >= th["avg_no_speech_prob_music_above"]:
            # whisper itself doubts speech despite emitting words => nudge MUSIC
            score += w["avg_no_speech_prob"]
        cr = stt_signals.get("avg_compression_ratio")
        if cr is not None and cr >= th["avg_compression_ratio_music_above"]:
            score += w["avg_compression_ratio"]

    label = "music" if score >= ft.DECISION_DEADZONE else "talk"
    confidence = _confidence_from_score(score)

    signals: Dict[str, Any] = {k: features.get(k) for k in ACOUSTIC_SIGNAL_KEYS}
    for k in STT_SIGNAL_KEYS:
        if k in stt_signals:
            signals[k] = stt_signals[k]
    signals["_score"] = score

    return ClassificationResult(label=label, confidence=confidence, method=method, signals=signals)


# ---------------------------------------------------------------------------
# Orchestrator (public API). Wires extraction -> fusion -> decision, all behind
# lazy imports + guards. The LIVE audio fetch path is reused, not reinvented.
# ---------------------------------------------------------------------------
def classify_content(
    audio_or_video_path: str,
    *,
    transcript: Optional[str] = None,
    segments: Optional[List[Dict[str, Any]]] = None,
    sample_rate: int = 16000,
) -> ClassificationResult:
    """Classify a short's dominant content as 'music' or 'talk'.

    Args:
        audio_or_video_path: Path to a local .wav/.mp3 (the audio is loaded via
            librosa). A YouTube video_id LIVE path is exercised only by
            scripts/live_classify.py, not here.
        transcript: OPTIONAL transcript text (currently unused by the acoustic
            decision; reserved for the OPTIONAL Gemma tie-breaker in the live
            entrypoint, and accepted so the contract is stable + testable).
        segments: OPTIONAL list of whisper segment dicts (no_speech_prob /
            compression_ratio). When supplied, enables acoustic+stt_fusion AND
            makes the decision deterministically unit-testable without a model.
        sample_rate: sample rate to assume for the loaded waveform.

    Returns:
        ClassificationResult. Never raises into the caller; on any failure
        returns method='unavailable', label='talk', confidence=0.0.
    """
    # Fail-safe: missing file.
    if not audio_or_video_path or not os.path.exists(audio_or_video_path):
        return _unavailable(f"path missing: {audio_or_video_path!r}")

    # Lazy-load the waveform (guard missing deps).
    try:
        import numpy as np  # noqa: F401  (guard only)
        import librosa
    except ImportError as exc:  # deps absent => fail-safe, never hang/raise
        return _unavailable(f"librosa/numpy unavailable: {exc}")

    try:
        y, sr = librosa.load(audio_or_video_path, sr=sample_rate, mono=True)
    except Exception as exc:  # corrupt/unsupported file => fail-safe
        return _unavailable(f"audio load failed: {exc}")

    # Extract features (guarded).
    try:
        features = extract_acoustic_features(y, sample_rate=sr)
    except Exception as exc:
        return _unavailable(f"feature extraction failed: {exc}")

    # Fuse any provided STT segment signals (no model call here).
    stt_signals = aggregate_stt_signals(segments)

    return _decide(features, stt_signals)
