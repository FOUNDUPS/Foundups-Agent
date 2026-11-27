# -*- coding: utf-8 -*-
"""Media probing, embedded SRT parsing, 16kHz signal analysis, and satire provenance gates.

Part of ``modules/communication/headless_video_orchestrator``. Zero network or paid calls.
"""

from __future__ import annotations

from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import subprocess
import tempfile
from typing import Any, Mapping, Optional, Sequence
import wave

_SUBPROCESS_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)

ALLOWED_CLAIM_CATEGORIES = {
    "parody_opinion",
    "numeric_stat",
    "benefit_claim",
    "constitutional_legal",
    "phone_number",
    "allegation",
}
FACTUAL_CLAIM_CATEGORIES = {
    "numeric_stat",
    "benefit_claim",
    "constitutional_legal",
    "phone_number",
    "allegation",
}
AFFILIATION_TERMS = (
    "the onion official",
    "official onion",
    "spy magazine official",
    "affiliated with the onion",
)
_SRT_TIME_RE = re.compile(
    r"^(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*$"
)


def sha256_file(path: str | Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ValueError(f"Expected regular file: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_media_cmd(args: Sequence[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
            timeout=timeout,
            creationflags=_SUBPROCESS_FLAGS,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        tail = ((exc.stderr or "") if isinstance(getattr(exc, "stderr", None), str) else str(exc))[-1500:]
        raise RuntimeError(f"{args[0]} failed: {tail}") from exc


def _parse_fps(rate_str: str) -> float:
    if not rate_str or rate_str == "0/0":
        return 0.0
    try:
        val = float(Fraction(rate_str))
        return round(val, 4) if math.isfinite(val) and val > 0 else 0.0
    except (ValueError, ZeroDivisionError):
        return 0.0


def _stream_duration_sec(stream: Mapping[str, Any], fmt: Mapping[str, Any]) -> float:
    for candidate in (stream.get("duration"), fmt.get("duration")):
        try:
            value = float(candidate)
            if math.isfinite(value) and value > 0:
                return round(value, 6)
        except (TypeError, ValueError):
            continue
    try:
        value = float(int(stream["duration_ts"]) * Fraction(stream["time_base"]))
        if math.isfinite(value) and value > 0:
            return round(value, 6)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        pass
    return 0.0


def probe_media_artifact(path: str | Path) -> dict[str, Any]:
    """Inspect media streams, SHA256, frame count, and explicit subtitle stream existence."""
    target = Path(path).resolve()
    digest = sha256_file(target)
    size_bytes = target.stat().st_size
    proc = run_media_cmd(
        ["ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe", "-show_streams", "-show_format", "-of", "json", str(target)],
        timeout=30,
    )
    payload = json.loads(proc.stdout)
    streams = payload.get("streams", [])
    fmt = payload.get("format", {})

    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    subtitle_streams = [
        {"index": s.get("index"), "codec_name": s.get("codec_name"), "language": (s.get("tags") or {}).get("language")}
        for s in streams
        if s.get("codec_type") == "subtitle"
    ]

    video_info = None
    if video_streams:
        vs = video_streams[0]
        nb_raw = vs.get("nb_frames")
        video_info = {
            "codec_name": vs.get("codec_name"),
            "width": int(vs.get("width") or 0),
            "height": int(vs.get("height") or 0),
            "pix_fmt": vs.get("pix_fmt"),
            "avg_fps": _parse_fps(str(vs.get("avg_frame_rate") or "0/0")),
            "r_fps": _parse_fps(str(vs.get("r_frame_rate") or "0/0")),
            "nb_frames": int(nb_raw) if str(nb_raw or "").isdigit() else None,
            "duration_sec": _stream_duration_sec(vs, fmt),
        }

    audio_info = None
    if audio_streams:
        aus = audio_streams[0]
        audio_info = {
            "codec_name": aus.get("codec_name"),
            "sample_rate": int(aus.get("sample_rate") or 0),
            "channels": int(aus.get("channels") or 0),
            "bit_rate": int(aus.get("bit_rate") or 0) if str(aus.get("bit_rate") or "").isdigit() else None,
            "duration_sec": _stream_duration_sec(aus, fmt),
        }

    return {
        "path": str(target),
        "size_bytes": size_bytes,
        "sha256": digest,
        "format_name": fmt.get("format_name"),
        "container_duration_sec": _stream_duration_sec({}, fmt),
        "stream_count": len(streams),
        "video": video_info,
        "audio": audio_info,
        "subtitle_streams": subtitle_streams,
        "has_embedded_subtitles": bool(subtitle_streams),
    }


def _srt_to_sec(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_embedded_srt(srt_text: str, *, max_audio_duration_sec: Optional[float] = None) -> dict[str, Any]:
    """Separate positive-duration lyric cues from zero-duration or bracketed stage directions."""
    blocks = [b.strip() for b in re.split(r"\r?\n\s*\r?\n", srt_text.strip()) if b.strip()]
    lyric_cues: list[dict[str, Any]] = []
    stage_directions: list[dict[str, Any]] = []
    overlap_count = 0
    beyond_audio_count = 0
    prev_lyric_end = 0.0

    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        ts_idx = 1 if lines[0].isdigit() else 0
        if ts_idx >= len(lines):
            continue
        match = _SRT_TIME_RE.match(lines[ts_idx])
        if not match:
            continue
        start_sec = round(_srt_to_sec(*match.groups()[:4]), 3)
        end_sec = round(_srt_to_sec(*match.groups()[4:]), 3)
        text = " ".join(lines[ts_idx + 1 :]).strip()
        if not text:
            continue
        duration_sec = round(end_sec - start_sec, 3)
        if duration_sec < 0:
            raise ValueError(f"Negative subtitle cue duration at {start_sec}: {text}")
        if max_audio_duration_sec is not None and end_sec > max_audio_duration_sec + 0.05:
            beyond_audio_count += 1

        is_stage = (duration_sec == 0.0) or (text.startswith("[") and text.endswith("]"))
        entry = {"start_sec": start_sec, "end_sec": end_sec, "duration_sec": duration_sec, "text": text}
        if is_stage:
            stage_directions.append(entry)
        else:
            if start_sec < prev_lyric_end - 1e-3:
                overlap_count += 1
            prev_lyric_end = max(prev_lyric_end, end_sec)
            lyric_cues.append(entry)

    return {
        "total_cues": len(lyric_cues) + len(stage_directions),
        "positive_lyric_cue_count": len(lyric_cues),
        "stage_direction_count": len(stage_directions),
        "zero_duration_stage_direction_count": sum(1 for c in stage_directions if c["duration_sec"] == 0.0),
        "overlap_count": overlap_count,
        "beyond_audio_count": beyond_audio_count,
        "audio_alignment_verified": False,
        "lyric_cues": lyric_cues,
        "stage_directions": stage_directions,
    }


def _decode_pcm_samples(path: Path, *, sample_rate: int = 16000, mono: bool = True) -> tuple[int, int, tuple[int, ...]]:
    with tempfile.TemporaryDirectory(prefix="antifafm-pcm-") as temp_dir:
        wav_path = Path(temp_dir) / "decoded.wav"
        cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-protocol_whitelist", "file,pipe", "-i", str(path), "-vn"]
        if mono:
            cmd.extend(["-ac", "1"])
        cmd.extend(["-ar", str(sample_rate), "-f", "wav", str(wav_path)])
        run_media_cmd(cmd, timeout=60)
        with wave.open(str(wav_path), "rb") as wf:
            n_frames = wf.getnframes()
            channels = wf.getnchannels()
            sr = wf.getframerate()
            raw = wf.readframes(n_frames)
    total_samples = n_frames * channels
    samples = struct.unpack(f"<{total_samples}h", raw) if total_samples else ()
    return sr, channels, samples


def inspect_per_channel_sample_peaks(path: str | Path, *, sample_rate: int = 48000) -> dict[str, Any]:
    """Check decoded PCM sample peaks across all channels (not inter-sample true-peak ISP)."""
    sr, channels, samples = _decode_pcm_samples(Path(path).resolve(), sample_rate=sample_rate, mono=False)
    if not samples or channels < 1:
        return {"channels": 0, "max_sample_peak_norm": 0.0, "full_scale_samples": 0, "stereo_true_peak_certified": False}
    max_abs = max(abs(x) for x in samples)
    clipped = sum(1 for x in samples if abs(x) >= 32767)
    return {
        "sample_rate": sr,
        "channels": channels,
        "max_sample_peak_norm": round(max_abs / 32768.0, 4),
        "full_scale_samples": clipped,
        "stereo_true_peak_certified": False,
    }


def analyze_audio_16k_mono(
    path: str | Path,
    *,
    window_ms: int = 100,
    quantile: float = 0.85,
    preferred_max_sec: float = 178.5,
    hard_limit_sec: float = 180.0,
) -> dict[str, Any]:
    """Compute 16kHz mono normalized RMS, RMS positive-difference quantiles, and heuristic <180s window."""
    if not (0.5 <= quantile < 1.0):
        raise ValueError("quantile must be in [0.5, 1.0)")
    if not (0.0 < preferred_max_sec < hard_limit_sec <= 180.0):
        raise ValueError("preferred_max_sec must be positive and strictly below hard_limit_sec <= 180.0")
    target = Path(path).resolve()
    sr, _, samples = _decode_pcm_samples(target, sample_rate=16000, mono=True)
    if not samples:
        raise ValueError(f"Decoded audio is empty: {target}")

    duration_sec = len(samples) / float(sr)
    peak_abs = max(abs(x) for x in samples)
    clipped_samples = sum(1 for x in samples if abs(x) >= 32767)

    hop = max(1, int(sr * window_ms / 1000))
    rms_series = [
        math.sqrt(sum((s / 32768.0) ** 2 for s in samples[idx : idx + hop]) / hop)
        for idx in range(0, len(samples) - hop + 1, hop)
    ] or [math.sqrt(sum((s / 32768.0) ** 2 for s in samples) / len(samples))]

    max_rms = max(rms_series) or 1.0
    norm_rms = [r / max_rms for r in rms_series]
    pos_rms_diff = [max(0.0, norm_rms[i] - norm_rms[i - 1]) for i in range(1, len(norm_rms))]
    sorted_diff = sorted(pos_rms_diff)
    if sorted_diff:
        q_idx = min(len(sorted_diff) - 1, int(quantile * len(sorted_diff)))
        measured_threshold = sorted_diff[q_idx]
        p75_diff = sorted_diff[int(0.75 * len(sorted_diff))]
        p90_diff = sorted_diff[int(0.90 * len(sorted_diff))]
    else:
        measured_threshold = p75_diff = p90_diff = 0.0

    win_sec = hop / float(sr)
    energy_rise_timestamps_sec = [
        round((i + 1) * win_sec, 3) for i, val in enumerate(pos_rms_diff) if val > 0.0 and val >= measured_threshold
    ]

    if duration_sec <= preferred_max_sec:
        candidate_end_sec = round(duration_sec, 3)
    else:
        max_idx = min(len(norm_rms) - 1, int(preferred_max_sec / win_sec))
        min_idx = max(1, int((preferred_max_sec - 8.0) / win_sec))
        valley_idx = min(range(min_idx, max_idx + 1), key=lambda k: norm_rms[k])
        candidate_end_sec = round(min(preferred_max_sec, (valley_idx + 1) * win_sec), 3)

    end_win_idx = min(len(norm_rms), max(1, int(candidate_end_sec / win_sec)))
    tail_slice = norm_rms[max(0, end_win_idx - 10) : end_win_idx]
    tail_mean_rms = sum(tail_slice) / len(tail_slice) if tail_slice else 0.0
    needs_fade_out = tail_mean_rms > 0.15 or duration_sec > preferred_max_sec

    return {
        "path": str(target),
        "sha256": sha256_file(target),
        "sample_rate": sr,
        "duration_sec": round(duration_sec, 6),
        "mono_sample_peak_norm": round(peak_abs / 32768.0, 4),
        "mono_clipped_samples": clipped_samples,
        "window_ms": window_ms,
        "signal_metric": "normalized_rms_positive_first_difference",
        "mean_norm_rms": round(sum(norm_rms) / len(norm_rms), 4),
        "quantile": quantile,
        "rms_positive_diff_quantile_threshold": round(measured_threshold, 4),
        "rms_positive_diff_p75": round(p75_diff, 4),
        "rms_positive_diff_p90": round(p90_diff, 4),
        "energy_rise_count": len(energy_rise_timestamps_sec),
        "energy_rise_timestamps_sec": energy_rise_timestamps_sec[:120],
        "selection_threshold_validated": False,
        "musical_ending_verified": False,
        "candidate_excerpt": {
            "start_sec": 0.0,
            "end_sec": candidate_end_sec,
            "strictly_under_180s": candidate_end_sec < hard_limit_sec,
            "tail_mean_norm_rms": round(tail_mean_rms, 4),
            "heuristic_fade_out_sec": 1.5 if needs_fade_out else 0.0,
        },
    }


def compare_audio_sources(path_a: str | Path, path_b: str | Path) -> dict[str, Any]:
    """Compare two candidate audio containers (e.g. M4A vs MP3) before mixing or substituting."""
    probe_a = probe_media_artifact(path_a)
    probe_b = probe_media_artifact(path_b)
    _, _, samples_a = _decode_pcm_samples(Path(path_a).resolve(), sample_rate=16000, mono=True)
    _, _, samples_b = _decode_pcm_samples(Path(path_b).resolve(), sample_rate=16000, mono=True)

    hop = 1600
    env_a = [math.sqrt(sum((s / 32768.0) ** 2 for s in samples_a[i : i + hop]) / hop) for i in range(0, len(samples_a) - hop + 1, hop)]
    env_b = [math.sqrt(sum((s / 32768.0) ** 2 for s in samples_b[i : i + hop]) / hop) for i in range(0, len(samples_b) - hop + 1, hop)]
    n = min(len(env_a), len(env_b))
    corr = 0.0
    if n >= 2:
        mean_a = sum(env_a[:n]) / n
        mean_b = sum(env_b[:n]) / n
        num = sum((env_a[i] - mean_a) * (env_b[i] - mean_b) for i in range(n))
        den_a = math.sqrt(sum((env_a[i] - mean_a) ** 2 for i in range(n)))
        den_b = math.sqrt(sum((env_b[i] - mean_b) ** 2 for i in range(n)))
        if den_a > 0 and den_b > 0:
            corr = num / (den_a * den_b)

    dur_a = (probe_a.get("audio") or {}).get("duration_sec") or probe_a["container_duration_sec"]
    dur_b = (probe_b.get("audio") or {}).get("duration_sec") or probe_b["container_duration_sec"]
    dur_delta = abs(dur_a - dur_b)
    return {
        "source_a": {"path": probe_a["path"], "sha256": probe_a["sha256"], "duration_sec": dur_a},
        "source_b": {"path": probe_b["path"], "sha256": probe_b["sha256"], "duration_sec": dur_b},
        "byte_identical": probe_a["sha256"] == probe_b["sha256"],
        "duration_delta_sec": round(dur_delta, 4),
        "rms_envelope_correlation": round(corr, 4),
        "content_equivalent": (probe_a["sha256"] == probe_b["sha256"]) or (dur_delta <= 0.15 and corr >= 0.985),
    }


def audit_satire_claims(claims: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Fail-closed provenance check separating parody/opinion from factual assertions."""
    results = []
    blocked_ids = []
    for item in claims:
        claim_id = str(item.get("claim_id") or "").strip()
        text = str(item.get("text") or "").strip()
        category = str(item.get("category") or "").strip()
        provenance = str(item.get("provenance_ref") or "").strip()
        fictionalized = item.get("fictionalized") is True

        if not claim_id or not text or category not in ALLOWED_CLAIM_CATEGORIES:
            raise ValueError(f"Invalid claim entry: {claim_id or '<missing>'}")

        lower_text = text.lower()
        if any(term in lower_text for term in AFFILIATION_TERMS):
            status = "BLOCKED_AFFILIATION_CLAIM"
            blocked_ids.append(claim_id)
        elif category == "allegation" and not provenance:
            status = "BLOCKED_UNVERIFIED_ALLEGATION"
            blocked_ids.append(claim_id)
        elif category in FACTUAL_CLAIM_CATEGORIES and not (provenance or fictionalized):
            status = "BLOCKED_UNVERIFIED_CLAIM"
            blocked_ids.append(claim_id)
        else:
            status = "PASS_PARODY_OR_VERIFIED"

        results.append(
            {
                "claim_id": claim_id,
                "category": category,
                "fictionalized": fictionalized,
                "has_provenance": bool(provenance),
                "status": status,
            }
        )
    return {"ok": len(blocked_ids) == 0, "blocked_claim_ids": blocked_ids, "claims": results}
