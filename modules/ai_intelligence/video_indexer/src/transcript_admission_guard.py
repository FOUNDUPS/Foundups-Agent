# -*- coding: utf-8 -*-
"""
Shared fail-closed provenance, speaker attribution, summary-leakage, and timestamp guards.

WSP Compliance:
    WSP 50: Pre-Action Verification (contradictory metadata & mislabeled summary detection)
    WSP 62: Large File / Function Discipline (< 400 lines, all functions <= 50 lines)
    WSP 84: Code Reuse (shared by DatasetBuilder and LocalArchiveRetrievalPilot)
    WSP 97: Truth Boundary (preserve 'unknown'/None; never invent '012' or 0.0 timestamps)
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

SPEAKER_VERIFIED = "verified"
SPEAKER_UNVERIFIED_LABEL = "unverified_label"
SPEAKER_UNKNOWN = "unknown"

ALLOWED_VERBATIM_SOURCES = frozenset({
    "youtube", "youtube_transcript", "youtube_dom", "youtube_captions", "youtube_json3",
    "srt", "vtt", "whisper", "whisper_transcript", "faster_whisper",
    "asr_verbatim", "human_verbatim", "verbatim", "jsonl_transcript",
})

DISALLOWED_TRANSCRIPT_SOURCES = frozenset({
    "gemini", "gemini_summary", "studio_ask", "youtube_studio_ask",
    "youtube_ask_gemini", "ask_studio", "ask_gemini", "summary",
    "synthetic", "generated", "llm",
})

DISALLOWED_PROVIDERS = frozenset({
    "gemini", "gemini_summary", "studio_ask", "youtube_studio_ask",
    "youtube_ask_gemini", "ask_studio", "ask_gemini",
})

NON_TARGET_SPEAKERS = frozenset({
    "guest", "interviewer", "other", "music", "narrator", "audience", "caller",
})

ALLOWED_PRINCIPAL_SPEAKERS = frozenset({
    "012", "michael trauth", "michael", "undaodu",
})

EXCLUDED_MUSIC_CHANNELS = frozenset({
    "antifafm", "ravingantifa",
})

_UNKNOWN_SPEAKER_TOKENS = frozenset({
    "", "unknown", "unspecified", "unidentified", "none", "null", "n/a", "?",
})

_NUMERIC_SEC_SUFFIX_RE = re.compile(r"^\d+(?:\.\d+)?s$")

_THIRD_PERSON_SUMMARY_RE = re.compile(
    r"(?:"
    r"^\s*(?:the\s+(?:speaker|creator|host|presenter|narrator|author|father|video|clip)"
    r"|in\s+this\s+(?:video|segment|clip|section)"
    r"|introduction\s+by\b|overview\s+of\b|summary\s+of\b"
    r"|highlights\s+and\s+atmosphere\s+from\b|speculation\s+that\s+the\b)"
    r"|\b(?:the\s+(?:speaker|creator|host|presenter)\s+"
    r"(?:introduces|discusses|explains|examines|describes|reflects|notes|mentions|"
    r"critiques|outlines|argues|highlights|demonstrates|concludes|summarizes))\b"
    r"|\"source_video_id\"\s*:|\"content_category\"\s*:"
    r")",
    re.IGNORECASE,
)


def parse_bool_flag(value: Any) -> Optional[bool | str]:
    """Normalize boolean eligibility/consent flags; return 'invalid' on ambiguous values."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        norm = value.strip().lower()
        if norm in {"true", "1", "yes"}:
            return True
        if norm in {"false", "0", "no", "denied", "unconsented", "third_party", "guest", "music"}:
            return False
        return "invalid"
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    return "invalid"


def parse_strict_timestamp(value: Any, *, blank_is_absent: bool = True) -> Tuple[Optional[float], bool]:
    """Parse numeric or MM:SS / HH:MM:SS(.mmm) timestamp strictly.

    Returns:
        (seconds_or_None, is_valid) where (None, True) means genuinely absent and
        (None, False) means malformed/out-of-range (NaN, Inf, bool, negative, sec>=60).
    """
    if value is None:
        return None, True
    if isinstance(value, bool):
        return None, False
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value) or value < 0:
            return None, False
        return round(float(value), 3), True
    if not isinstance(value, str):
        return None, False
    raw = value.strip().replace(",", ".")
    if not raw:
        return (None, True) if blank_is_absent else (None, False)
    if _NUMERIC_SEC_SUFFIX_RE.match(raw):
        raw = raw[:-1]
    if ":" in raw:
        return _parse_colon_timestamp(raw)
    try:
        num = float(raw)
    except ValueError:
        return None, False
    if math.isnan(num) or math.isinf(num) or num < 0:
        return None, False
    return round(num, 3), True


def _parse_colon_timestamp(raw: str) -> Tuple[Optional[float], bool]:
    """Validate MM:SS or HH:MM:SS(.mmm) bounds strictly (0 <= min < 60, 0 <= sec < 60)."""
    parts = raw.split(":")
    try:
        if len(parts) == 2 and parts[0].isdigit():
            mins, secs = int(parts[0]), float(parts[1])
            if math.isnan(secs) or math.isinf(secs) or not (0.0 <= secs < 60.0):
                return None, False
            return round(mins * 60 + secs, 3), True
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            hrs, mins, secs = int(parts[0]), int(parts[1]), float(parts[2])
            if math.isnan(secs) or math.isinf(secs) or not (0 <= mins < 60) or not (0.0 <= secs < 60.0):
                return None, False
            return round(hrs * 3600 + mins * 60 + secs, 3), True
    except ValueError:
        return None, False
    return None, False


def classify_speaker_attribution(
    segment: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[str], str]:
    """Classify segment speaker without ever inventing '012' for missing/blank speakers.

    Returns:
        (speaker_label_or_None, status) where status in {'verified', 'unverified_label', 'unknown'}.
    """
    raw = segment.get("speaker")
    if raw is None or isinstance(raw, bool) or not isinstance(raw, str):
        return None, SPEAKER_UNKNOWN
    cleaned = raw.strip()
    if cleaned.lower() in _UNKNOWN_SPEAKER_TOKENS:
        return None, SPEAKER_UNKNOWN

    meta = metadata if isinstance(metadata, dict) else {}
    seg_ver = segment.get("speaker_verified")
    if seg_ver is False or (seg_ver is not None and not isinstance(seg_ver, bool)):
        return cleaned, SPEAKER_UNVERIFIED_LABEL
    meta_ver = meta.get("speaker_verified") if "speaker_verified" in meta else meta.get("diarization_verified")
    if seg_ver is True or (seg_ver is None and meta_ver is True):
        return cleaned, SPEAKER_VERIFIED
    return cleaned, SPEAKER_UNVERIFIED_LABEL


def summarize_record_speakers(
    segments: Sequence[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Compute record-level speaker attribution summary across segments."""
    known_speakers: List[str] = []
    seen_lower: Set[str] = set()
    has_unknown = False
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        spk, status = classify_speaker_attribution(seg, metadata)
        if status == SPEAKER_UNKNOWN or spk is None:
            has_unknown = True
        elif spk.lower() not in seen_lower:
            seen_lower.add(spk.lower())
            known_speakers.append(spk)
    has_mixed = len(known_speakers) > 1 or (len(known_speakers) >= 1 and has_unknown and len(segments) > 1)
    return {
        "known_speakers": known_speakers,
        "has_unknown_speakers": has_unknown,
        "has_mixed_speakers": has_mixed,
    }


def _distinct_nonempty(values: Sequence[Any], *, lower: bool = True) -> List[str]:
    out: List[str] = []
    for val in values:
        if val is None or isinstance(val, (bool, dict, list)):
            continue
        s = str(val).strip()
        if not s:
            continue
        norm = s.lower() if lower else s
        if norm not in out:
            out.append(norm)
    return out


def detect_metadata_contradictions(data: Dict[str, Any]) -> List[str]:
    """Detect contradictory provenance, eligibility, consent, or identity fields across layers."""
    meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    prov = meta.get("provenance") if isinstance(meta.get("provenance"), dict) else {}
    audio = data.get("audio") if isinstance(data.get("audio"), dict) else {}
    conflicts: List[str] = []
    for flag in ("training_eligible", "consent"):
        parsed = [parse_bool_flag(d.get(flag)) for d in (data, meta, prov) if flag in d and d.get(flag) is not None]
        if "invalid" in parsed:
            conflicts.append(f"invalid_{flag}_flag")
        elif True in parsed and False in parsed:
            conflicts.append(f"{flag}_layer_conflict")
    vids = _distinct_nonempty(
        [data.get("video_id"), meta.get("video_id"), prov.get("requested_video_id"), prov.get("response_video_id")],
        lower=False,
    )
    if len(vids) > 1:
        conflicts.append("video_id_conflict")
    if prov.get("identity_verified") is False:
        conflicts.append("identity_unverified")
    if len(_distinct_nonempty([data.get("channel"), meta.get("channel")])) > 1:
        conflicts.append("channel_conflict")
    ts_sources = _distinct_nonempty([data.get("transcript_source"), meta.get("transcript_source"), prov.get("transcript_source")])
    indexers = _distinct_nonempty([data.get("indexer"), meta.get("indexer"), prov.get("indexer")])
    providers = _distinct_nonempty([data.get("provider"), meta.get("provider"), prov.get("provider")])
    ext_methods = _distinct_nonempty([audio.get("extraction_method"), meta.get("extraction_method")])
    for vals, label in ((ts_sources, "transcript_source"), (indexers, "indexer"), (providers, "provider"), (ext_methods, "extraction_method")):
        if len(vals) > 1:
            conflicts.append(f"{label}_conflict")
    has_yt = isinstance(data.get("youtube_transcript"), list) and bool(data.get("youtube_transcript"))
    has_wh = isinstance(data.get("whisper_transcript"), list) and bool(data.get("whisper_transcript"))
    has_verbatim_claim = has_yt or has_wh or any(s in ALLOWED_VERBATIM_SOURCES for s in (*ts_sources, *ext_methods))
    has_disallowed = (
        any(s in DISALLOWED_TRANSCRIPT_SOURCES for s in (*ts_sources, *ext_methods))
        or any(p in DISALLOWED_PROVIDERS for p in (*indexers, *providers))
    )
    if has_verbatim_claim and has_disallowed:
        conflicts.append("verbatim_vs_summary_provenance_conflict")
    return conflicts


def detect_mislabeled_summary(
    data: Dict[str, Any], segments: Sequence[Any], *, has_verbatim_claim: bool
) -> Optional[str]:
    """Detect Gemini/Studio Ask or 3rd-person summary content disguised as a verbatim transcript."""
    if not has_verbatim_claim:
        return None
    meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    prov = meta.get("provenance") if isinstance(meta.get("provenance"), dict) else {}
    audio = data.get("audio") if isinstance(data.get("audio"), dict) else {}

    models = _distinct_nonempty([data.get("model"), meta.get("model"), prov.get("model")])
    if any(m.startswith("gemini") for m in models):
        return "gemini_model_on_verbatim_claim"

    if (
        (isinstance(data.get("gemini_summary"), dict) and bool(data.get("gemini_summary")))
        or (isinstance(audio.get("transcript_summary"), str) and bool(audio["transcript_summary"].strip()))
        or (isinstance(data.get("transcript_summary"), str) and bool(data["transcript_summary"].strip()))
    ):
        return "summary_payload_on_verbatim_claim"

    for seg in segments:
        if not isinstance(seg, dict):
            continue
        if ("summary" in seg or "ask_segments" in seg) and "text" not in seg:
            return "summary_segment_schema"
        text = str(seg.get("text") or seg.get("content") or seg.get("summary") or "").strip()
        if text and _THIRD_PERSON_SUMMARY_RE.search(text):
            return "third_person_summary_text"
    return None
