"""
live_classify.py - ISOLATED LIVE ENTRYPOINT for the music-vs-talk PoC.

=============================================================================
THIS IS THE ONLY PLACE REAL MODELS / REAL AUDIO RUN. NEVER EXECUTED IN PYTEST.
Slice: RND_MUSIC_VS_TALK_DETECTION_POC   Worker-Lane: RND-MUSIC-TALK
=============================================================================

PURPOSE:
    012 validates the PoC on labeled real shorts here (NOT via pytest). Given a
    local .wav/.mp3 OR a YouTube --video-id, this script:
      1. Loads real audio (librosa, or VideoArchiveExtractor.extract_audio for an
         id - reused, not reinvented; unlisted via YT_DLP_COOKIES_BROWSER).
      2. OPTIONALLY transcribes with openai-whisper to harvest real segment
         no_speech_prob / compression_ratio for acoustic+stt_fusion.
      3. Calls classify_content and prints label + confidence + full signals.
      4. OPTIONALLY cross-checks the existing Gemini/Studio content_category
         ORACLE if an index artifact is present (agreement only; NOT a build dep).

RUN:
    python -m modules.ai_intelligence.audio_content_classifier.scripts.live_classify --path clip.wav
    python -m modules.ai_intelligence.audio_content_classifier.scripts.live_classify --video-id VIDEOID --whisper
    (close any live Chrome/Edge debug session first to avoid the cookie lock.)

WSP 84 reuse:
    - VideoArchiveExtractor.extract_audio:
        modules/platform_integration/youtube_live_audio/src/youtube_live_audio.py:405
    - openai-whisper segment dicts (no_speech_prob/compression_ratio): standard.

ISOLATION: read-only; never writes/re-indexes the artifact; never imports the
scheduler. All heavy imports are LAZY and inside functions.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from typing import Any, Dict, List, Optional

from modules.ai_intelligence.audio_content_classifier.src.audio_content_classifier import (
    ClassificationResult,
    classify_content,
)


def _fetch_audio_for_video_id(video_id: str) -> Optional[str]:
    """Reuse VideoArchiveExtractor to fetch 16kHz mono audio for a video id.

    Returns a local .wav path or None. LAZY import keeps the module hermetic.
    """
    try:
        from modules.platform_integration.youtube_live_audio.src.youtube_live_audio import (
            VideoArchiveExtractor,
        )
        import numpy as np
        import soundfile as sf  # optional; only the live path needs it
    except ImportError as exc:
        print(f"[live_classify] cannot fetch by video-id (missing dep): {exc}", file=sys.stderr)
        return None

    extractor = VideoArchiveExtractor()
    audio = extractor.extract_audio(video_id)
    if audio is None:
        print(f"[live_classify] extract_audio returned None for {video_id}", file=sys.stderr)
        return None
    # Persist the float32 array to a temp wav so classify_content can load it.
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, np.asarray(audio, dtype="float32"), 16000)
    return tmp.name


def _whisper_segments(wav_path: str) -> Optional[List[Dict[str, Any]]]:
    """Transcribe with openai-whisper and return segment dicts for fusion.

    LAZY import; returns None if whisper is unavailable (acoustic-only fallback).
    """
    try:
        import whisper
    except ImportError as exc:
        print(f"[live_classify] whisper unavailable, acoustic-only: {exc}", file=sys.stderr)
        return None
    model = whisper.load_model("base")
    result = model.transcribe(wav_path)
    segments = result.get("segments", []) or []
    # Keep only the keys the fusion consumes (no_speech_prob/compression_ratio).
    return [
        {
            "text": s.get("text", ""),
            "no_speech_prob": s.get("no_speech_prob"),
            "compression_ratio": s.get("compression_ratio"),
            "avg_logprob": s.get("avg_logprob"),
        }
        for s in segments
    ]


def _oracle_content_category(video_id: Optional[str]) -> Optional[str]:
    """Best-effort read of the existing Gemini/Studio content_category artifact.

    ORACLE ONLY: used to report agreement, never as a build dependency. Returns
    None if no artifact is present (the usual case for unlisted scheduler shorts).
    Implemented as a defensive glob so it never breaks the live run.
    """
    if not video_id:
        return None
    try:
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[4]
        # Defensive search across known index artifact roots; read-only.
        candidates = list(repo_root.glob(f"**/{video_id}*.json"))
        for c in candidates[:25]:
            try:
                data = json.loads(c.read_text(encoding="utf-8"))
            except Exception:
                continue
            cat = data.get("content_category") if isinstance(data, dict) else None
            if cat:
                return str(cat)
    except Exception as exc:  # never let the oracle break the run
        print(f"[live_classify] oracle lookup skipped: {exc}", file=sys.stderr)
    return None


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Music-vs-talk PoC live classifier (R&D).")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--path", help="local .wav/.mp3 to classify")
    src.add_argument("--video-id", help="YouTube video id (reuses VideoArchiveExtractor)")
    parser.add_argument("--whisper", action="store_true", help="run openai-whisper for STT fusion")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    wav_path = args.path
    if args.video_id:
        wav_path = _fetch_audio_for_video_id(args.video_id)
        if not wav_path:
            print("[live_classify] no audio available; aborting", file=sys.stderr)
            return 2

    segments = _whisper_segments(wav_path) if args.whisper else None
    result: ClassificationResult = classify_content(wav_path, segments=segments)
    oracle = _oracle_content_category(args.video_id)

    payload = {
        "input": args.path or args.video_id,
        "label": result.label,
        "confidence": round(result.confidence, 4),
        "method": result.method,
        "signals": {k: (round(v, 5) if isinstance(v, float) else v) for k, v in result.signals.items()},
        "oracle_content_category": oracle,
        "oracle_agreement": (
            None if oracle is None else (
                (result.label == "music" and "music" in oracle.lower())
                or (result.label == "talk" and "music" not in oracle.lower())
            )
        ),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"label      : {payload['label']}")
        print(f"confidence : {payload['confidence']}")
        print(f"method     : {payload['method']}")
        print(f"oracle     : {oracle} (agreement={payload['oracle_agreement']})")
        print("signals    :")
        for k, v in payload["signals"].items():
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
