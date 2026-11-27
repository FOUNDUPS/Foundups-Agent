# -*- coding: utf-8 -*-
"""
Read-only local archive format parsers, provenance conflict detectors, and timestamp/speaker classifiers.

WSP Compliance: WSP 50, WSP 62 (< 800 lines, all functions <= 50 lines), WSP 72, WSP 84, WSP 97.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .transcript_admission_guard import (
    SPEAKER_UNKNOWN,
    SPEAKER_UNVERIFIED_LABEL,
    SPEAKER_VERIFIED,
    classify_speaker_attribution,
    detect_metadata_contradictions,
    detect_mislabeled_summary,
    parse_bool_flag,
    parse_strict_timestamp,
)

MAX_RECORD_FILE_BYTES = 8 * 1024 * 1024
MAX_JSONL_LINES = 5000

STATUS_INDEXED = "INDEXED"
STATUS_BLOCKED_MISSING_TRANSCRIPT = "BLOCKED_MISSING_TRANSCRIPT"
STATUS_ERROR_UNREADABLE = "ERROR_UNREADABLE"

TIMESTAMP_GENUINE = "GENUINE"
TIMESTAMP_PARTIAL_START_ONLY = "PARTIAL_START_ONLY"
TIMESTAMP_ABSENT = "ABSENT"
TIMESTAMP_INVALID = "INVALID"
TIMESTAMP_NONMONOTONIC = "NONMONOTONIC"

MEDIA_EXTENSIONS = frozenset({
    ".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv", ".wmv", ".m4v",
    ".mp3", ".m4a", ".wav", ".flac", ".opus", ".ogg", ".aac",
})

VERBATIM_SOURCES = frozenset({
    "youtube", "youtube_transcript", "youtube_dom", "youtube_captions", "youtube_json3",
    "srt", "vtt", "whisper", "whisper_transcript", "faster_whisper",
    "asr_verbatim", "human_verbatim", "verbatim", "jsonl_transcript",
})

SEMANTIC_SUMMARY_SOURCES = frozenset({
    "gemini", "gemini_summary", "studio_ask", "youtube_studio_ask",
    "youtube_ask_gemini", "ask_studio", "ask_gemini", "summary",
})

_BRACKET_VIDEO_ID_RE = re.compile(r"\[([A-Za-z0-9_-]{11})\]")
_BARE_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_CUE_TIMING_RE = re.compile(
    r"(?P<start>(?:\d{1,2}:)?\d{1,2}:\d{2}[,.]\d{1,3})\s*-->\s*"
    r"(?P<end>(?:\d{1,2}:)?\d{1,2}:\d{2}[,.]\d{1,3})"
)
_INLINE_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class PilotSegment:
    """Indexed searchable segment with honest timestamp, speaker, and provenance metadata."""
    record_id: str
    video_id: str
    source_path: str
    channel: Optional[str]
    title: str
    text: str
    t_start: Optional[float]
    t_end: Optional[float]
    has_genuine_timestamps: bool
    timestamp_status: str
    speaker: Optional[str]
    speaker_status: str = SPEAKER_UNKNOWN
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PilotRecordStatus:
    """Per-record ingestion outcome with speaker and timestamp audit metadata."""
    source_path: str
    video_id: str
    channel: Optional[str]
    title: str
    record_format: str
    status: str
    segment_count: int
    has_genuine_timestamps: bool
    provenance: Dict[str, Any] = field(default_factory=dict)
    blocker_reason: Optional[str] = None
    has_mixed_speakers: bool = False
    has_unknown_speakers: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def parse_timestamp_seconds(value: Any) -> Optional[float]:
    """Parse numeric seconds or strict MM:SS / HH:MM:SS(.mmm); return None when absent/invalid."""
    sec, ok = parse_strict_timestamp(value)
    return sec if ok else None


def classify_timestamps(
    t_start: Optional[float], t_end: Optional[float], *, allow_zero_without_end: bool = True
) -> Tuple[Optional[float], Optional[float], bool, str]:
    """Normalize (t_start, t_end) honestly; flag inverted or dangling-end timestamps INVALID."""
    if t_start is None and t_end is not None:
        return None, None, False, TIMESTAMP_INVALID
    if t_start is not None and t_end is not None and t_end < t_start:
        return None, None, False, TIMESTAMP_INVALID
    if (t_start is None and t_end is None) or (t_start == 0.0 and t_end == 0.0):
        return None, None, False, TIMESTAMP_ABSENT
    if t_start == 0.0 and t_end is None and not allow_zero_without_end:
        return None, None, False, TIMESTAMP_ABSENT
    if t_start is not None and t_end is not None:
        return t_start, t_end, True, TIMESTAMP_GENUINE
    return t_start, None, True, TIMESTAMP_PARTIAL_START_ONLY


def _evaluate_segment_timing(
    start_raw: Any, end_raw: Any, *, has_start: bool, has_end: bool,
    allow_zero: bool, prev_max_start: Optional[float],
) -> Tuple[Optional[float], Optional[float], bool, str, Optional[float]]:
    """Validate raw start/end fields strictly and enforce sequence monotonicity."""
    t_s, s_ok = parse_strict_timestamp(start_raw) if has_start else (None, True)
    t_e, e_ok = parse_strict_timestamp(end_raw) if has_end else (None, True)
    if not s_ok or not e_ok:
        return None, None, False, TIMESTAMP_INVALID, prev_max_start
    norm_s, norm_e, genuine, status = classify_timestamps(t_s, t_e, allow_zero_without_end=allow_zero)
    if status == TIMESTAMP_INVALID or not genuine or norm_s is None:
        return norm_s, norm_e, genuine, status, prev_max_start
    if prev_max_start is not None and norm_s < prev_max_start:
        return None, None, False, TIMESTAMP_NONMONOTONIC, prev_max_start
    return norm_s, norm_e, True, status, norm_s


def infer_video_id_from_path(path: Path) -> str:
    """Extract YouTube video_id from bracketed yt-dlp names or multi-suffix stems."""
    bracket_match = _BRACKET_VIDEO_ID_RE.search(path.name)
    if bracket_match:
        return bracket_match.group(1)
    for suffix in (".info.json", ".en.vtt", ".en.srt", ".ja.vtt", ".ja.srt"):
        if path.name.lower().endswith(suffix):
            return path.name[: -len(suffix)].strip() or path.stem
    if "." in path.stem:
        candidate = path.stem.split(".")[0]
        if _BARE_VIDEO_ID_RE.match(candidate):
            return candidate
    return path.stem.strip() or path.name


def _blocked_status(
    source_path: str, video_id: str, channel: Optional[str], title: str,
    fmt: str, reason: str, prov: Optional[Dict[str, Any]] = None, status: str = STATUS_BLOCKED_MISSING_TRANSCRIPT,
) -> Tuple[PilotRecordStatus, List[PilotSegment]]:
    return PilotRecordStatus(
        source_path=source_path, video_id=video_id, channel=channel, title=title,
        record_format=fmt, status=status, segment_count=0, has_genuine_timestamps=False,
        provenance=prov or {}, blocker_reason=reason,
    ), []


def _indexed_status(
    source_path: str, video_id: str, channel: Optional[str], title: str,
    fmt: str, segments: List[PilotSegment], prov: Dict[str, Any],
) -> Tuple[PilotRecordStatus, List[PilotSegment]]:
    known = {s.speaker.lower() for s in segments if s.speaker and s.speaker_status != SPEAKER_UNKNOWN}
    has_unk = any(s.speaker_status == SPEAKER_UNKNOWN for s in segments)
    has_mix = len(known) > 1 or (len(known) >= 1 and has_unk and len(segments) > 1)
    enriched_prov = {**prov, "has_unknown_speakers": has_unk, "has_mixed_speakers": has_mix}
    for s in segments:
        s.provenance.setdefault("has_unknown_speakers", has_unk)
        s.provenance.setdefault("has_mixed_speakers", has_mix)
    return PilotRecordStatus(
        source_path=source_path, video_id=video_id, channel=channel, title=title,
        record_format=fmt, status=STATUS_INDEXED, segment_count=len(segments),
        has_genuine_timestamps=any(s.has_genuine_timestamps for s in segments),
        provenance=enriched_prov, has_mixed_speakers=has_mix, has_unknown_speakers=has_unk,
    ), segments


def segments_from_dict_list(
    raw_segments: Sequence[Any], *, record_id: str, video_id: str, source_path: str,
    channel: Optional[str], title: str, provenance: Dict[str, Any],
    ask_segments_ref: Optional[List[Dict[str, Any]]] = None,
    record_metadata: Optional[Dict[str, Any]] = None,
) -> List[PilotSegment]:
    """Convert segment dicts into PilotSegments with strict timestamp & speaker status."""
    out: List[PilotSegment] = []
    prev_max: Optional[float] = None
    for idx, item in enumerate(raw_segments):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or item.get("content") or item.get("summary") or item.get("topic") or "").strip()
        if not text:
            continue
        s_key = next((k for k in ("start", "start_time", "timestamp_sec", "t_start", "time") if k in item and item[k] is not None), None)
        e_key = next((k for k in ("end", "end_time", "end_sec", "t_end") if k in item and item[k] is not None), None)
        allow_zero = True
        if ask_segments_ref is not None and idx < len(ask_segments_ref) and isinstance(ask_segments_ref[idx], dict):
            orig_t, orig_ok = parse_strict_timestamp(ask_segments_ref[idx].get("time"))
            if not orig_ok or orig_t is None:
                allow_zero = False
        norm_s, norm_e, genuine, ts_status, prev_max = _evaluate_segment_timing(
            item[s_key] if s_key else None, item[e_key] if e_key else None,
            has_start=s_key is not None, has_end=e_key is not None,
            allow_zero=allow_zero, prev_max_start=prev_max,
        )
        spk, spk_status = classify_speaker_attribution(item, record_metadata)
        out.append(PilotSegment(
            record_id=record_id, video_id=video_id, source_path=source_path, channel=channel,
            title=title, text=text, t_start=norm_s, t_end=norm_e, has_genuine_timestamps=genuine,
            timestamp_status=ts_status, speaker=spk, speaker_status=spk_status, provenance=dict(provenance),
        ))
    return out


def parse_json3_payload(
    data: Any, source_path: str, record_id: str, video_id: str, channel: Optional[str], title: str
) -> Tuple[PilotRecordStatus, List[PilotSegment]]:
    """Parse yt-dlp YouTube timedtext JSON3 events with strict timing & monotonicity."""
    prov = {"transcript_source": "youtube_json3", "indexer": "yt_dlp_subtitles", "is_verbatim": True, "training_eligible": True, "record_format": "json3"}
    events = data.get("events") if isinstance(data, dict) else None
    extracted: List[PilotSegment] = []
    prev_max: Optional[float] = None
    for ev in events if isinstance(events, list) else []:
        segs = ev.get("segs") if isinstance(ev, dict) else None
        if not isinstance(segs, list):
            continue
        text = re.sub(r"\s+", " ", "".join(str(s.get("utf8") or "") for s in segs if isinstance(s, dict))).strip()
        if not text:
            continue
        has_s = "tStartMs" in ev and ev["tStartMs"] is not None
        has_d = "dDurationMs" in ev and ev["dDurationMs"] is not None
        ts_ms, dur_ms = ev.get("tStartMs"), ev.get("dDurationMs")
        s_val = (float(ts_ms) / 1000.0) if (has_s and not isinstance(ts_ms, bool) and isinstance(ts_ms, (int, float))) else (ts_ms if has_s else None)
        e_val = ((float(ts_ms) + float(dur_ms)) / 1000.0) if (isinstance(s_val, float) and has_d and not isinstance(dur_ms, bool) and isinstance(dur_ms, (int, float)) and dur_ms > 0) else (dur_ms if (has_d and not isinstance(dur_ms, (int, float))) else None)
        norm_s, norm_e, genuine, ts_status, prev_max = _evaluate_segment_timing(
            s_val, e_val, has_start=has_s, has_end=e_val is not None, allow_zero=True, prev_max_start=prev_max
        )
        extracted.append(PilotSegment(
            record_id=record_id, video_id=video_id, source_path=source_path, channel=channel,
            title=title, text=text, t_start=norm_s, t_end=norm_e, has_genuine_timestamps=genuine,
            timestamp_status=ts_status, speaker=None, speaker_status=SPEAKER_UNKNOWN, provenance=dict(prov),
        ))
    return _indexed_status(source_path, video_id, channel, title, "json3", extracted, prov) if extracted else _blocked_status(source_path, video_id, channel, title, "json3", "empty_json3_events", prov)


def _build_verbatim_or_flagged_prov(
    data: Dict[str, Any], raw_segs: Sequence[Any], declared_src: str, indexer: str,
    fmt: str, conflicts: List[str], any_ineligible: bool,
) -> Dict[str, Any]:
    """Build provenance dict, downgrading is_verbatim/training_eligible on conflicts or mislabeled summaries."""
    mislabeled = detect_mislabeled_summary(data, raw_segs, has_verbatim_claim=True)
    compromised = bool(conflicts) or (mislabeled is not None) or any_ineligible
    eff_src = "unknown_conflict" if conflicts else ("mislabeled_summary" if mislabeled else declared_src)
    return {
        "transcript_source": eff_src,
        "declared_transcript_source": declared_src,
        "indexer": indexer or (declared_src if not compromised else "unknown"),
        "is_verbatim": not compromised,
        "training_eligible": not compromised,
        "provenance_conflict": bool(conflicts),
        "conflict_reasons": list(conflicts),
        "mislabeled_summary_suspected": mislabeled is not None,
        "mislabeled_reason": mislabeled,
        "record_format": fmt,
    }


def _parse_json_dict_record(
    data: Dict[str, Any], file_path: Path, record_id: str, default_vid: str,
    hint_channel: Optional[str], hint_title: Optional[str], include_semantic_summaries: bool,
) -> Tuple[PilotRecordStatus, List[PilotSegment]]:
    """Parse video_indexer JSON artifact without premature verbatim short-circuiting."""
    src = str(file_path)
    meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    meta_prov = meta.get("provenance") if isinstance(meta.get("provenance"), dict) else {}
    audio = data.get("audio") if isinstance(data.get("audio"), dict) else {}
    gem = data.get("gemini_summary") if isinstance(data.get("gemini_summary"), dict) else {}

    vid = str(data.get("video_id") or data.get("id") or "").strip() or default_vid
    parent_ch = file_path.parent.name if file_path.parent.name not in {"", "."} else None
    ch = str(data.get("channel") or meta.get("channel") or data.get("uploader") or hint_channel or "").strip() or parent_ch
    title = str(data.get("title") or meta.get("title") or hint_title or "").strip()
    is_info = file_path.name.lower().endswith(".info.json") or any(k in data for k in ("webpage_url", "extractor", "formats", "_type"))
    raw_src = str(data.get("transcript_source") or meta.get("transcript_source") or "").strip().lower()
    indexer = str(data.get("indexer") or meta.get("indexer") or meta_prov.get("provider") or "").strip().lower()
    ext_m = str(audio.get("extraction_method") or "").strip().lower()
    conflicts = detect_metadata_contradictions(data)
    any_inelig = any(parse_bool_flag(d.get("training_eligible")) in (False, "invalid") for d in (data, meta, meta_prov))

    if indexer == "scheduler_stub":
        prov = {"transcript_source": raw_src or "none", "indexer": "scheduler_stub", "is_verbatim": False, "training_eligible": False, "record_format": "scheduler_stub_json"}
        return _blocked_status(src, vid, ch, title, "scheduler_stub_json", "missing_transcript_scheduler_stub", prov)

    for vf in ("youtube_transcript", "whisper_transcript"):
        if isinstance(data.get(vf), list) and data[vf]:
            prov = _build_verbatim_or_flagged_prov(data, data[vf], vf, indexer, "video_index_json", conflicts, any_inelig)
            if not prov["is_verbatim"] and not include_semantic_summaries:
                return _blocked_status(src, vid, ch, title, "video_index_json", "contradictory_or_mislabeled_transcript_blocked", prov)
            segs = segments_from_dict_list(data[vf], record_id=record_id, video_id=vid, source_path=src, channel=ch, title=title, provenance=prov, record_metadata=meta)
            if segs:
                return _indexed_status(src, vid, ch, title, "video_index_json", segs, prov)

    return _parse_generic_json_content(
        data, meta, audio, gem, src, record_id, vid, ch, title, is_info, raw_src, indexer, ext_m, conflicts, any_inelig, include_semantic_summaries
    )


def _parse_generic_json_content(
    data: Dict[str, Any], meta: Dict[str, Any], audio: Dict[str, Any], gem: Dict[str, Any], src: str,
    record_id: str, vid: str, ch: Optional[str], title: str, is_info: bool, raw_src: str, indexer: str,
    ext_m: str, conflicts: List[str], any_inelig: bool, include_semantic_summaries: bool,
) -> Tuple[PilotRecordStatus, List[PilotSegment]]:
    """Extract generic segments or untimed summaries, preserving conflict/mislabeled flags."""
    fmt = "yt_dlp_info_json" if is_info else "video_index_json"
    is_sem = raw_src in SEMANTIC_SUMMARY_SOURCES or indexer in SEMANTIC_SUMMARY_SOURCES or ext_m in SEMANTIC_SUMMARY_SOURCES or any_inelig or bool(gem)
    claims_verb = (not is_sem) and (raw_src in VERBATIM_SOURCES or ext_m in VERBATIM_SOURCES)
    cand_segs = data.get("segments") if isinstance(data.get("segments"), list) else (audio.get("segments") if isinstance(audio.get("segments"), list) else [])

    if claims_verb:
        prov = _build_verbatim_or_flagged_prov(data, cand_segs, raw_src or ext_m, indexer, fmt, conflicts, any_inelig)
    else:
        prov = {
            "transcript_source": "unknown_conflict" if conflicts else (raw_src or ext_m or indexer or ("gemini_summary" if is_sem else "unknown")),
            "indexer": indexer or "unknown", "is_verbatim": False, "training_eligible": False,
            "provenance_conflict": bool(conflicts), "conflict_reasons": list(conflicts),
            "mislabeled_summary_suspected": False, "record_format": fmt,
        }
    if not prov["is_verbatim"] and not include_semantic_summaries:
        return _blocked_status(src, vid, ch, title, fmt, "semantic_or_conflicted_summary_excluded", prov)

    ask_segs = gem.get("ask_segments") if isinstance(gem.get("ask_segments"), list) else None
    for container, ref in ((data.get("segments"), None), (audio.get("segments"), ask_segs), (ask_segs, None)):
        if isinstance(container, list) and container:
            segs = segments_from_dict_list(container, record_id=record_id, video_id=vid, source_path=src, channel=ch, title=title, provenance=prov, ask_segments_ref=ref, record_metadata=meta)
            if segs:
                return _indexed_status(src, vid, ch, title, fmt, segs, prov)

    for key_val in (data.get("transcript"), data.get("full_text"), audio.get("transcript_summary"), gem.get("ask_response"), data.get("transcript_summary")):
        if isinstance(key_val, str) and key_val.strip():
            if claims_verb and detect_mislabeled_summary(data, [{"text": key_val}], has_verbatim_claim=True):
                prov = {**prov, "transcript_source": "mislabeled_summary", "is_verbatim": False, "training_eligible": False, "mislabeled_summary_suspected": True}
            spk, spk_st = classify_speaker_attribution(data, meta)
            seg = PilotSegment(
                record_id=record_id, video_id=vid, source_path=src, channel=ch, title=title,
                text=key_val.strip(), t_start=None, t_end=None, has_genuine_timestamps=False,
                timestamp_status=TIMESTAMP_ABSENT, speaker=spk, speaker_status=spk_st, provenance=prov,
            )
            return _indexed_status(src, vid, ch, title, fmt, [seg], prov)

    blk_fmt = "yt_dlp_info_json" if is_info else "metadata_only_json"
    return _blocked_status(src, vid, ch, title, blk_fmt, "metadata_only_missing_transcript" if is_info else "missing_transcript_segments", prov)


def parse_json_file(
    file_path: Path, record_id: str, default_vid: str, hint_channel: Optional[str],
    hint_title: Optional[str], include_semantic_summaries: bool,
) -> Tuple[PilotRecordStatus, List[PilotSegment]]:
    """Parse JSON file (IndexData, yt-dlp info, JSON3, or segment array)."""
    src = str(file_path)
    data = json.loads(file_path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("events"), list):
        return parse_json3_payload(data, src, record_id, default_vid, hint_channel, hint_title or "")
    if isinstance(data, list):
        prov = {"transcript_source": "unlabeled_segment_list", "indexer": "unknown", "is_verbatim": False, "training_eligible": False, "record_format": "segment_list_json"}
        segs = segments_from_dict_list(data, record_id=record_id, video_id=default_vid, source_path=src, channel=hint_channel, title=hint_title or "", provenance=prov)
        return _indexed_status(src, default_vid, hint_channel, hint_title or "", "segment_list_json", segs, prov) if segs else _blocked_status(src, default_vid, hint_channel, hint_title or "", "segment_list_json", "empty_transcript_segments", prov)
    if not isinstance(data, dict):
        return _blocked_status(src, default_vid, hint_channel, hint_title or "", "json", "json_root_not_object_or_array", status=STATUS_ERROR_UNREADABLE)
    return _parse_json_dict_record(data, file_path, record_id, default_vid, hint_channel, hint_title, include_semantic_summaries)


def parse_jsonl_file(
    file_path: Path, record_id: str, default_vid: str, hint_channel: Optional[str], hint_title: Optional[str]
) -> Tuple[PilotRecordStatus, List[PilotSegment]]:
    """Parse JSONL transcript rows with strict timestamp & speaker status."""
    src = str(file_path)
    prov = {"transcript_source": "jsonl_transcript", "indexer": "local_jsonl", "is_verbatim": True, "training_eligible": True, "record_format": "jsonl"}
    extracted: List[PilotSegment] = []
    vid, title, ch = default_vid, hint_title or "", hint_channel
    prev_max: Optional[float] = None
    with open(file_path, "r", encoding="utf-8") as fh:
        for line_num, raw_line in enumerate(fh, start=1):
            if line_num > MAX_JSONL_LINES:
                break
            if not raw_line.strip():
                continue
            row = json.loads(raw_line.strip())
            if not isinstance(row, dict):
                continue
            meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            out_obj = row.get("output") if isinstance(row.get("output"), dict) else {}
            text = str(row.get("text") or row.get("content") or out_obj.get("next_utterance_text") or "").strip()
            if not text:
                continue
            vid = str(row.get("video_id") or meta.get("video_id") or "").strip() or vid
            title = str(row.get("title") or meta.get("title") or title).strip()
            ch = str(row.get("channel") or meta.get("channel") or "").strip() or ch
            s_pair = next(((True, d[k]) for d in (row, meta) for k in ("timestamp_sec", "t_start", "start_time", "start") if k in d and d[k] is not None), (False, None))
            e_pair = next(((True, d[k]) for d in (row, meta) for k in ("end_sec", "t_end", "end_time", "end") if k in d and d[k] is not None), (False, None))
            norm_s, norm_e, genuine, ts_status, prev_max = _evaluate_segment_timing(
                s_pair[1], e_pair[1], has_start=s_pair[0], has_end=e_pair[0], allow_zero=True, prev_max_start=prev_max
            )
            spk_src = row if "speaker" in row else meta
            spk, spk_st = classify_speaker_attribution(spk_src, meta)
            extracted.append(PilotSegment(
                record_id=record_id, video_id=vid, source_path=src, channel=ch, title=title,
                text=text, t_start=norm_s, t_end=norm_e, has_genuine_timestamps=genuine,
                timestamp_status=ts_status, speaker=spk, speaker_status=spk_st, provenance=dict(prov),
            ))
    return _indexed_status(src, vid, ch, title, "jsonl", extracted, prov) if extracted else _blocked_status(src, vid, ch, title, "jsonl", "empty_jsonl_transcript", prov)


def parse_caption_file(
    file_path: Path, record_id: str, video_id: str, channel: Optional[str], title: Optional[str], *, fmt: str
) -> Tuple[PilotRecordStatus, List[PilotSegment]]:
    """Parse SRT or WebVTT captions with strict timestamp bounds and monotonicity."""
    src = str(file_path)
    prov = {"transcript_source": fmt, "indexer": f"local_{fmt}_captions", "is_verbatim": True, "training_eligible": True, "record_format": fmt}
    raw_text = file_path.read_text(encoding="utf-8", errors="replace")
    extracted: List[PilotSegment] = []
    last_seen = ""
    prev_max: Optional[float] = None
    for block in re.split(r"\r?\n\r?\n+", raw_text.strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines or lines[0].upper().startswith(("WEBVTT", "NOTE", "STYLE")):
            continue
        match_pair = next(((i, _CUE_TIMING_RE.search(ln)) for i, ln in enumerate(lines[:3]) if _CUE_TIMING_RE.search(ln)), None)
        if not match_pair:
            continue
        t_idx, m = match_pair
        assert m is not None
        cue_lines: List[str] = []
        for raw_cue in lines[t_idx + 1 :]:
            clean = re.sub(r"\s+", " ", _INLINE_TAG_RE.sub("", raw_cue).replace("&nbsp;", " ").replace("&amp;", "&")).strip()
            if clean and clean != last_seen:
                cue_lines.append(clean)
                last_seen = clean
        if cue_lines:
            norm_s, norm_e, genuine, ts_status, prev_max = _evaluate_segment_timing(
                m.group("start"), m.group("end"), has_start=True, has_end=True, allow_zero=True, prev_max_start=prev_max
            )
            extracted.append(PilotSegment(
                record_id=record_id, video_id=video_id, source_path=src, channel=channel, title=title or "",
                text=" ".join(cue_lines), t_start=norm_s, t_end=norm_e, has_genuine_timestamps=genuine,
                timestamp_status=ts_status, speaker=None, speaker_status=SPEAKER_UNKNOWN, provenance=dict(prov),
            ))
    return _indexed_status(src, video_id, channel, title or "", fmt, extracted, prov) if extracted else _blocked_status(src, video_id, channel, title or "", fmt, f"empty_{fmt}_captions", prov)


def parse_txt_file(
    file_path: Path, record_id: str, video_id: str, channel: Optional[str], title: Optional[str]
) -> Tuple[PilotRecordStatus, List[PilotSegment]]:
    """Parse untimed plain text transcript (timestamps strictly None / ABSENT, speaker None / unknown)."""
    src = str(file_path)
    prov = {"transcript_source": "plain_txt", "indexer": "local_txt", "is_verbatim": True, "training_eligible": False, "record_format": "txt"}
    raw_text = file_path.read_text(encoding="utf-8", errors="replace").strip()
    if not raw_text:
        return _blocked_status(src, video_id, channel, title or "", "txt", "empty_txt_transcript", prov)
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\r?\n\r?\n+", raw_text) if p.strip()]
    segs = [
        PilotSegment(
            record_id=record_id, video_id=video_id, source_path=src, channel=channel, title=title or "",
            text=p, t_start=None, t_end=None, has_genuine_timestamps=False,
            timestamp_status=TIMESTAMP_ABSENT, speaker=None, speaker_status=SPEAKER_UNKNOWN, provenance=dict(prov),
        )
        for p in paras
    ]
    return _indexed_status(src, video_id, channel, title or "", "txt", segs, prov)
