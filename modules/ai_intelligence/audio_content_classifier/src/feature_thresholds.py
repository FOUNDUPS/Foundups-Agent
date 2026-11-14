"""
feature_thresholds.py - Externalized decision thresholds and weights.

R&D PoC ONLY (Slice: RND_MUSIC_VS_TALK_DETECTION_POC). NOT wired into scheduling.

WHY THIS FILE EXISTS (WSP 5 tunability):
    The acoustic music-vs-talk discriminator decides via a weighted score over
    classic music/speech discriminator features. Keeping every threshold and
    weight in named constants here lets the live eval (scripts/live_classify.py)
    and 012 calibrate decision boundaries WITHOUT touching decision logic in
    audio_content_classifier.py. Unit test test_thresholds_externalized proves
    that overriding a constant moves the boundary.

PROVENANCE OF FEATURES (classic music/speech discrimination, signal-level):
    spectral_flatness        - Music is more tonal/structured across a sustained
                               window; high flatness => noise-like, low flatness
                               => tonal. Sustained tonal energy (instruments,
                               sung notes) trends toward MUSIC. librosa.feature.
                               spectral_flatness.
    harmonic_percussive_ratio- Music carries strong harmonic + percussive energy
                               (HPSS); speech is dominated by transient, less
                               sustained harmonic structure. librosa.effects.hpss.
                               HIGH ratio (sustained harmonics) => MUSIC.
    zero_crossing_rate       - Speech (esp. fricatives/consonants) has HIGH ZCR;
                               sustained musical tones have LOWER ZCR. HIGH ZCR
                               => TALK. librosa.feature.zero_crossing_rate.
    tempo_bpm / beat_strength- Music has a stable tempo and strong beat;
                               speech does not. STRONG beat => MUSIC.
                               librosa.beat.beat_track / onset envelope.
    rms_dynamic_range        - Speech has wide RMS dynamics (pauses between
                               phrases, syllable stress); music (esp. mastered
                               shorts) is more compressed/sustained. WIDE range
                               => TALK. librosa.feature.rms.
    mfcc_var                 - Variance of MFCCs over time; speech timbre shifts
                               rapidly (phonemes), sustained music is steadier in
                               some bands but lyric singing varies - used as a
                               weak supporting signal only.

FUSION SIGNALS (openai-whisper segment dicts, OPTIONAL):
    avg_no_speech_prob       - Mean whisper segment no_speech_prob. HIGH => the
                               STT model itself judged "no speech" even if it
                               still emitted tokens (the sung-lyrics confound).
    avg_compression_ratio    - Abnormally high whisper compression_ratio is a
                               known marker of repetitive/degenerate text often
                               seen when transcribing music; treated as a weak
                               MUSIC nudge.

NOTE: thresholds below are STARTING POINTS for the live eval. They are explicitly
documented as un-calibrated until the labeled-set run in TestModLog.md scores them.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Per-feature decision thresholds (a feature votes "music" or "talk" relative
# to its threshold; magnitude of crossing feeds the weighted score).
# ---------------------------------------------------------------------------
THRESHOLDS = {
    # spectral_flatness: BELOW this leans MUSIC (tonal), ABOVE leans noise/talk.
    "spectral_flatness_music_below": 0.30,
    # harmonic_percussive_ratio: ABOVE this leans MUSIC (sustained harmonics).
    "harmonic_percussive_ratio_music_above": 1.6,
    # zero_crossing_rate: ABOVE this leans TALK (fricatives/consonants).
    "zero_crossing_rate_talk_above": 0.12,
    # beat_strength: ABOVE this leans MUSIC (stable strong beat).
    "beat_strength_music_above": 0.45,
    # tempo_bpm: a plausible musical tempo band reinforces MUSIC.
    "tempo_bpm_music_low": 60.0,
    "tempo_bpm_music_high": 180.0,
    # rms_dynamic_range: ABOVE this leans TALK (wide dynamics / pauses).
    "rms_dynamic_range_talk_above": 0.22,
    # mfcc_var: ABOVE this leans TALK (rapid timbral phoneme shifts).
    "mfcc_var_talk_above": 55.0,
    # avg_no_speech_prob: ABOVE this is a strong MUSIC fusion nudge even when
    # words were transcribed (the lyrics confound defense).
    "avg_no_speech_prob_music_above": 0.50,
    # avg_compression_ratio: ABOVE this is a weak MUSIC fusion nudge.
    "avg_compression_ratio_music_above": 2.4,
}

# ---------------------------------------------------------------------------
# Weights for the weighted vote. Acoustic signals dominate (signal-level
# robustness to the lyrics-as-text confound); STT fusion signals are additive
# nudges, never strong enough alone to flip a clear acoustic decision.
# Positive contribution => MUSIC, negative => TALK.
# ---------------------------------------------------------------------------
WEIGHTS = {
    "spectral_flatness": 1.0,
    "harmonic_percussive_ratio": 1.4,
    "zero_crossing_rate": 1.2,
    "beat_strength": 1.6,        # strongest single acoustic discriminator
    "tempo_bpm": 0.6,
    "rms_dynamic_range": 1.0,
    "mfcc_var": 0.5,            # weak supporting signal
    # fusion (only applied when whisper segments are injected/available)
    "avg_no_speech_prob": 1.1,  # confound defense, but < combined acoustic weight
    "avg_compression_ratio": 0.4,
}

# Score (sum of signed weighted votes) is squashed to confidence via this scale.
# Larger => need stronger evidence to reach high confidence.
SCORE_CONFIDENCE_SCALE = 4.0

# Minimum |score| treated as a real decision; below this confidence stays modest.
DECISION_DEADZONE = 0.0
