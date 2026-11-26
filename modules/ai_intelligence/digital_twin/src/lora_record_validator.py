"""Fail-closed JSONL record admission and non-fabricating diagnostic inspector.

Separates read-only inspection (preserving None/'unknown' without inventing '012'
or 0.0) from strict fail-closed training admission at VoiceLoRATrainer.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

DEFAULT_SYSTEM_PROMPT = "You are 012's Digital Twin."
PRINCIPAL_SPEAKER_IDS = frozenset({"012", "undaodu", "michael trauth"})
UNKNOWN_SPEAKER_VALUES = frozenset({"unknown", "unattributed", "unidentified", "unverified", "none", "null", "n/a", "?"})
PLACEHOLDER_GROUP_IDS = UNKNOWN_SPEAKER_VALUES | frozenset({"__default__", "default", "placeholder", "na", "tbd", "unset"})
MUSIC_OR_RESTRICTED_CHANNELS = frozenset({"antifafm", "ravingantifa", "ffcpln_music", "music"})
DISALLOWED_PROVENANCE_VALUES = frozenset({
    "gemini", "gemini_summary", "studio_ask", "ask_studio", "youtube_studio_ask", "youtube_ask_gemini",
    "summary", "ai_summary", "synthetic_summary", "generated_summary", "auto_summary", "llm_summary",
    "scheduler_stub", "unverified", "unknown", "synthetic",
})
DISALLOWED_MODEL_SUBSTRINGS = ("gemini", "studio_ask", "ask_studio", "gpt-", "claude", "bard", "palm")
DISALLOWED_CONSENT_VALUES = frozenset({"false", "no", "denied", "revoked", "unverified", "unknown", "pending", "third_party", "guest", "music", "restricted", "copyrighted"})
SUMMARY_PAYLOAD_KEYS = frozenset({"summary", "gemini_summary", "transcript_summary", "ask_segments", "studio_ask", "summary_text", "video_summary", "chapter_summaries"})
VERBATIM_SOURCE_FAMILIES = {
    "youtube": frozenset({"youtube", "youtube_transcript", "youtube_captions", "manual_captions", "yt_captions"}),
    "whisper": frozenset({"whisper", "whisper_transcript", "faster_whisper", "openai_whisper", "whisper_asr"}),
    "human": frozenset({"human", "manual", "verbatim_human"}),
}
_THIRD_PERSON_SUMMARY_RE = re.compile(
    r"(?:^|[.!?]\s+|\n\s*)(?:(?:summary|key\s+takeaways|video\s+summary|segment\s+summary)\s*:|"
    r"(?:in\s+this\s+(?:video|segment|clip|stream|episode|recording|part)\s*,\s*)?"
    r"(?:the\s+(?:speaker|creator|host|presenter|author|narrator|youtuber|vlogger|"
    r"father|man|commentator|founder|video|segment|clip|stream)|012|michael(?:\s+trauth)?|undaodu)\s+"
    r"(?:introduces|discusses|explains|describes|criticizes|critiques|argues|outlines|"
    r"summarizes|highlights|emphasizes|reflects|examines|explores|talks\s+about|"
    r"speaks\s+about|points\s+out|shares\s+his|addresses|concludes|demonstrates|"
    r"notes\s+that|states\s+that)\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class InspectedVoiceRecord:
    """Read-only diagnostic inspection result preserving unknown/absent metadata."""
    line_num: int
    admissible_for_training: bool
    rejection_reasons: tuple[str, ...]
    messages: Optional[dict[str, str]]
    group_id: Optional[str]
    training_eligible: Optional[bool]
    verbatim_families: tuple[str, ...]
    consent_granted: Optional[bool]
    speaker: Optional[str]
    speaker_status: str
    t_start: Optional[float]
    t_end: Optional[float]
    timestamp_status: str
    segment_idx: Optional[int] = None
    record_bucket: str = "__default__"


@dataclass(frozen=True)
class ValidatedVoiceRecord:
    """Training-admitted SFT example with verified principal speaker and provenance."""
    line_num: int
    messages: dict[str, str]
    group_id: str
    speaker: str
    speaker_status: str
    t_start: Optional[float]
    t_end: Optional[float]
    timestamp_status: str
    segment_idx: Optional[int] = None
    record_bucket: str = "__default__"

    def to_lineage_dict(self) -> dict[str, Any]:
        return {
            "line_num": self.line_num, "group_id": self.group_id, "speaker": self.speaker,
            "speaker_status": self.speaker_status, "t_start": self.t_start, "t_end": self.t_end,
            "timestamp_status": self.timestamp_status, "segment_idx": self.segment_idx,
        }


def _reject_nonfinite_constant(token: str) -> Any:
    raise ValueError(f"Non-finite JSON constant {token!r} is forbidden")


def _extract_containers(record: dict[str, Any], line_num: int) -> list[tuple[str, dict[str, Any]]]:
    containers: list[tuple[str, dict[str, Any]]] = [("record", record)]
    for key in ("metadata", "audio"):
        raw = record.get(key)
        if raw is not None:
            if not isinstance(raw, dict):
                raise ValueError(f"Invalid {key!r} on line {line_num}: expected dict.")
            containers.append((key, raw))
    for parent_name, parent in list(containers):
        if "provenance" in parent and parent["provenance"] is not None:
            prov = parent["provenance"]
            if isinstance(prov, dict):
                containers.append((f"{parent_name}.provenance", prov))
            elif not isinstance(prov, str):
                raise ValueError(f"Invalid 'provenance' in {parent_name} on line {line_num}: expected dict or str.")
    return containers


def _check_provenance_string(field_name: str, value: Any, line_num: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid provenance field {field_name!r} on line {line_num}: expected non-empty string.")
    norm = value.strip().lower()
    substrings = ("gemini", "studio_ask", "ask_studio", "summary", "scheduler_stub")
    if norm in DISALLOWED_PROVENANCE_VALUES or any(tok in norm for tok in substrings):
        raise ValueError(f"Disallowed non-verbatim provenance ({field_name}={value!r}) on line {line_num}.")
    return norm


def _source_family(norm_val: str) -> Optional[str]:
    return next((fam for fam, members in VERBATIM_SOURCE_FAMILIES.items() if norm_val in members), None)


def _validate_consent_and_channel(
    cname: str, cdict: dict[str, Any], line_num: int, consent_truths: set[bool], channels: set[str]
) -> None:
    for ckey in ("consent", "training_consent", "voice_consent", "rights_status"):
        if ckey in cdict and (ckey != "rights_status" or cdict[ckey] is not None):
            cval = cdict[ckey]
            if type(cval) is bool:
                if not cval:
                    raise ValueError(f"Unconsented or restricted record on line {line_num}: {cname}.{ckey}=False.")
                if ckey != "rights_status":
                    consent_truths.add(True)
            elif isinstance(cval, str) and cval.strip():
                if cval.strip().lower() in DISALLOWED_CONSENT_VALUES:
                    raise ValueError(f"Unconsented or restricted record on line {line_num}: {cname}.{ckey}={cval!r}.")
                if ckey != "rights_status":
                    raise ValueError(f"Consent field {cname}.{ckey} must be boolean True on line {line_num}, got {cval!r}.")
            else:
                raise ValueError(f"Invalid {ckey!r} on line {line_num}: {cval!r}.")
    for ch_key in ("channel", "channel_name", "source_channel"):
        if ch_key in cdict and cdict[ch_key] is not None:
            ch_val = cdict[ch_key]
            if not isinstance(ch_val, str) or not ch_val.strip():
                raise ValueError(f"Invalid {ch_key!r} on line {line_num}.")
            ch_norm = ch_val.strip().lower()
            if ch_norm in MUSIC_OR_RESTRICTED_CHANNELS:
                raise ValueError(f"Restricted music/non-voice channel ({ch_val!r}) on line {line_num}.")
            channels.add(ch_norm)


def _validate_provenance_and_model(
    cname: str, cdict: dict[str, Any], line_num: int, seen_by_key: dict[str, str], families: set[str]
) -> None:
    for pkey in ("transcript_source", "source_type", "indexer", "extraction_method", "provider"):
        if pkey in cdict and cdict[pkey] is not None:
            norm = _check_provenance_string(f"{cname}.{pkey}", cdict[pkey], line_num)
            if pkey in seen_by_key and seen_by_key[pkey] != norm:
                raise ValueError(f"Contradictory metadata for {pkey!r} on line {line_num}: {seen_by_key[pkey]!r} vs {norm!r}.")
            seen_by_key[pkey] = norm
            fam = _source_family(norm)
            if fam is not None:
                families.add(fam)
    if "provenance" in cdict and isinstance(cdict["provenance"], str):
        fam = _source_family(_check_provenance_string(f"{cname}.provenance", cdict["provenance"], line_num))
        if fam is not None:
            families.add(fam)
    if "type" in cdict and isinstance(cdict["type"], str) and "summary" in cdict["type"].lower():
        raise ValueError(f"Disallowed summary record type ({cname}.type={cdict['type']!r}) on line {line_num}.")
    for mkey in ("model", "generator", "teacher_model", "llm_model", "enhancer_model"):
        if mkey in cdict and cdict[mkey] is not None:
            mval = cdict[mkey]
            if not isinstance(mval, str) or not mval.strip():
                raise ValueError(f"Invalid {mkey!r} on line {line_num}.")
            if any(tok in mval.strip().lower() for tok in DISALLOWED_MODEL_SUBSTRINGS):
                raise ValueError(f"Mislabeled summary model provenance ({cname}.{mkey}={mval!r}) on line {line_num}.")


def _validate_eligibility_and_provenance(
    containers: list[tuple[str, dict[str, Any]]], assistant_text: str, line_num: int
) -> tuple[bool, tuple[str, ...], bool]:
    seen_by_key: dict[str, str] = {}
    families, consent_truths, channels = set(), set(), set()
    saw_eligible = False
    for cname, cdict in containers:
        if "training_eligible" in cdict:
            if cdict["training_eligible"] is not True:
                raise ValueError(f"Ineligible training record on line {line_num}: {cname}.training_eligible={cdict['training_eligible']!r}.")
            saw_eligible = True
        if "is_verbatim" in cdict and cdict["is_verbatim"] is not True:
            raise ValueError(f"Non-verbatim record on line {line_num}: {cname}.is_verbatim={cdict['is_verbatim']!r}.")
        for flag in ("is_summary", "mislabeled_summary_suspected", "provenance_conflict"):
            if flag in cdict and cdict[flag] is not False and cdict[flag] is not None:
                raise ValueError(f"Summary or provenance conflict flag ({cname}.{flag}={cdict[flag]!r}) on line {line_num}.")
        for sum_key in SUMMARY_PAYLOAD_KEYS:
            if cdict.get(sum_key) is not None:
                raise ValueError(f"Mislabeled summary payload ({cname}.{sum_key}) on line {line_num}.")
        _validate_consent_and_channel(cname, cdict, line_num, consent_truths, channels)
        _validate_provenance_and_model(cname, cdict, line_num, seen_by_key, families)
    if len(channels) > 1:
        raise ValueError(f"Contradictory channel metadata on line {line_num}: {sorted(channels)!r}.")
    if len(families) > 1:
        raise ValueError(f"Contradictory transcript provenance families on line {line_num}: {sorted(families)!r}.")
    if _THIRD_PERSON_SUMMARY_RE.search(assistant_text):
        raise ValueError(f"Mislabeled summary as transcript on line {line_num}: 3rd-person summary phrasing detected.")
    return saw_eligible, tuple(sorted(families)), bool(consent_truths)


def _collect_container_speaker(
    cname: str, cdict: dict[str, Any], line_num: int, discovered: list[str], verified_flags: set[bool]
) -> None:
    for mix_key in ("has_mixed_speakers", "has_unknown_speakers"):
        if mix_key in cdict and cdict[mix_key] is not False and cdict[mix_key] is not None:
            raise ValueError(f"Mixed or unknown speakers ({cname}.{mix_key}={cdict[mix_key]!r}) on line {line_num}.")
    if "speakers" in cdict and cdict["speakers"] is not None:
        spk_list = cdict["speakers"]
        if not isinstance(spk_list, list) or not spk_list or not all(isinstance(s, str) and s.strip() for s in spk_list):
            raise ValueError(f"Invalid 'speakers' list in {cname} on line {line_num}.")
        norms = {s.strip().lower() for s in spk_list}
        if len(norms) > 1 or any(n in UNKNOWN_SPEAKER_VALUES or n not in PRINCIPAL_SPEAKER_IDS for n in norms):
            raise ValueError(f"Mixed, unknown, or non-principal speakers ({spk_list!r}) on line {line_num}.")
        discovered.extend(norms)
    for skey in ("speaker", "target_speaker", "speaker_id", "speaker_name"):
        if skey in cdict:
            sval = cdict[skey]
            if not isinstance(sval, str) or not sval.strip():
                raise ValueError(f"Missing or blank speaker attribution ({cname}.{skey}={sval!r}) on line {line_num}.")
            snorm = sval.strip().lower()
            if snorm in UNKNOWN_SPEAKER_VALUES:
                raise ValueError(f"Unknown speaker attribution ({cname}.{skey}={sval!r}) on line {line_num}.")
            if snorm not in PRINCIPAL_SPEAKER_IDS:
                raise ValueError(f"Non-principal or mixed speaker ({cname}.{skey}={sval!r}) on line {line_num}.")
            discovered.append(snorm)
    if "speaker_verified" in cdict:
        vflag = cdict["speaker_verified"]
        if type(vflag) is not bool or vflag is not True:
            raise ValueError(f"Unverified speaker attribution ({cname}.speaker_verified={vflag!r}) on line {line_num}.")
        verified_flags.add(True)
    for st_key in ("speaker_status", "attribution_status"):
        if st_key in cdict:
            st_val = cdict[st_key]
            if not isinstance(st_val, str) or st_val.strip().lower() != "verified":
                raise ValueError(f"Unverified {st_key} ({cname}.{st_key}={st_val!r}) on line {line_num}.")
            verified_flags.add(True)


def _inspect_speaker_state(
    containers: list[tuple[str, dict[str, Any]]], line_num: int
) -> tuple[Optional[str], str]:
    discovered: list[str] = []
    verified_flags: set[bool] = set()
    for cname, cdict in containers:
        _collect_container_speaker(cname, cdict, line_num, discovered, verified_flags)
    if len(set(discovered)) > 1:
        raise ValueError(f"Contradictory speaker IDs across containers on line {line_num}: {sorted(set(discovered))!r}.")
    if not discovered:
        if verified_flags:
            raise ValueError(f"Missing speaker attribution despite verification flag on line {line_num}.")
        return None, "unknown"
    return discovered[0], ("verified" if verified_flags else "unverified_label")


def _parse_colon_timestamp(text: str, field_name: str, line_num: int) -> float:
    parts = text.split(":")
    if len(parts) not in (2, 3) or any(not p or p[0] in "+-" for p in parts):
        raise ValueError(f"Malformed colon timestamp ({field_name}={text!r}) on line {line_num}.")
    try:
        if len(parts) == 2:
            minutes, seconds = int(parts[0]), float(parts[1])
            if minutes < 0 or not math.isfinite(seconds) or not (0.0 <= seconds < 60.0):
                raise ValueError("MM:SS out of bounds")
            return minutes * 60.0 + seconds
        hours, minutes, seconds = int(parts[0]), int(parts[1]), float(parts[2])
        if hours < 0 or not (0 <= minutes < 60) or not math.isfinite(seconds) or not (0.0 <= seconds < 60.0):
            raise ValueError("HH:MM:SS out of bounds")
        return hours * 3600.0 + minutes * 60.0 + seconds
    except ValueError as exc:
        raise ValueError(f"Invalid colon timestamp ({field_name}={text!r}) on line {line_num}.") from exc


def _parse_single_timestamp(raw_val: Any, field_name: str, line_num: int) -> float:
    if isinstance(raw_val, bool):
        raise ValueError(f"Invalid boolean timestamp for {field_name!r} on line {line_num}.")
    if isinstance(raw_val, (int, float)):
        val = float(raw_val)
        if not math.isfinite(val) or val < 0.0:
            raise ValueError(f"Invalid non-finite or negative timestamp ({field_name}={raw_val!r}) on line {line_num}.")
        return val
    if not isinstance(raw_val, str):
        raise ValueError(f"Unsupported timestamp type for {field_name!r} on line {line_num}: {type(raw_val).__name__}.")
    text = raw_val.strip()
    if not text:
        raise ValueError(f"Blank string timestamp for {field_name!r} on line {line_num}.")
    if ":" in text:
        return _parse_colon_timestamp(text, field_name, line_num)
    try:
        val = float(text)
    except ValueError as exc:
        raise ValueError(f"Unparseable timestamp ({field_name}={raw_val!r}) on line {line_num}.") from exc
    if not math.isfinite(val) or val < 0.0:
        raise ValueError(f"Invalid non-finite or negative timestamp ({field_name}={raw_val!r}) on line {line_num}.")
    return val


def _validate_timestamps(
    containers: list[tuple[str, dict[str, Any]]], line_num: int
) -> tuple[Optional[float], Optional[float], str, Optional[int]]:
    starts, ends, seg_indices, explicit_statuses = [], [], [], []
    for cname, cdict in containers:
        for skey in ("t_start", "start", "start_time", "start_sec"):
            if skey in cdict and cdict[skey] is not None:
                starts.append(_parse_single_timestamp(cdict[skey], f"{cname}.{skey}", line_num))
        for ekey in ("t_end", "end", "end_time", "end_sec"):
            if ekey in cdict and cdict[ekey] is not None:
                ends.append(_parse_single_timestamp(cdict[ekey], f"{cname}.{ekey}", line_num))
        if "segment_idx" in cdict and cdict["segment_idx"] is not None:
            sidx = cdict["segment_idx"]
            if type(sidx) is not int or sidx < 0:
                raise ValueError(f"Invalid segment_idx ({cname}.segment_idx={sidx!r}) on line {line_num}.")
            seg_indices.append(sidx)
        if "timestamp_status" in cdict and cdict["timestamp_status"] is not None:
            st = cdict["timestamp_status"]
            if not isinstance(st, str) or st.strip().lower() in {
                "invalid", "timestamp_invalid", "nonmonotonic", "timestamp_nonmonotonic"
            }:
                raise ValueError(f"Invalid timestamp_status ({st!r}) on line {line_num}.")
            explicit_statuses.append(st.strip().lower())
    if len(starts) > 1 and max(starts) - min(starts) > 1e-6:
        raise ValueError(f"Contradictory start timestamps on line {line_num}: {starts!r}.")
    if len(ends) > 1 and max(ends) - min(ends) > 1e-6:
        raise ValueError(f"Contradictory end timestamps on line {line_num}: {ends!r}.")
    if len(set(seg_indices)) > 1:
        raise ValueError(f"Contradictory segment_idx values on line {line_num}: {seg_indices!r}.")
    t_start, t_end = (starts[0] if starts else None), (ends[0] if ends else None)
    if t_start is None and t_end is not None:
        raise ValueError(f"Dangling end timestamp without start timestamp (t_end={t_end}) on line {line_num}.")
    if t_start is not None and t_end is not None and t_end < t_start:
        raise ValueError(f"Inverted timestamps (t_end={t_end} < t_start={t_start}) on line {line_num}.")
    if (t_start is not None or t_end is not None) and any(s in {"absent", "timestamp_absent"} for s in explicit_statuses):
        raise ValueError(f"Contradictory timestamp_status='absent' with numeric timestamps on line {line_num}.")
    status = "unknown" if t_start is None else ("partial_start_only" if t_end is None else "verified_span")
    return t_start, t_end, status, (seg_indices[0] if seg_indices else None)


def _extract_group_id(containers: list[tuple[str, dict[str, Any]]], line_num: int) -> Optional[str]:
    discovered: list[str] = []
    for cname, cdict in containers:
        for key in ("video_id", "source_id", "source_video", "source"):
            if key in cdict and cdict[key] is not None:
                raw_val = cdict[key]
                if not isinstance(raw_val, str) or not raw_val.strip():
                    raise ValueError(f"Invalid {cname}.{key} on line {line_num}: must be a non-empty string.")
                cleaned = raw_val.strip()
                if cleaned.lower() in PLACEHOLDER_GROUP_IDS:
                    raise ValueError(f"Placeholder or unknown source/video group ID ({cname}.{key}={raw_val!r}) on line {line_num}.")
                discovered.append(cleaned)
    if not discovered:
        return None
    canonical = discovered[0]
    for other in discovered[1:]:
        if other != canonical:
            raise ValueError(f"Conflicting source/video group IDs on line {line_num}: {canonical!r} vs {other!r}.")
    return canonical


def _inspect_provenance_slice(
    containers: list[tuple[str, dict[str, Any]]], ast_text: str, line_num: int, reasons: list[str]
) -> tuple[Optional[bool], tuple[str, ...], Optional[bool]]:
    try:
        saw_el, fams, saw_c = _validate_eligibility_and_provenance(containers, ast_text, line_num)
        for ok, reason in ((saw_el, "missing_training_eligible"), (bool(fams), "missing_verbatim_provenance"), (saw_c, "missing_explicit_consent")):
            if not ok:
                reasons.append(reason)
        return (True if saw_el else None), fams, (True if saw_c else None)
    except ValueError:
        reasons.append("disallowed_or_contradictory_provenance")
        return False, (), False


def inspect_sft_record(record: Any, line_num: int = 1) -> InspectedVoiceRecord:
    """Non-training diagnostic inspector: preserves None/'unknown' without fabricating '012' or 0.0."""
    if not isinstance(record, dict):
        return InspectedVoiceRecord(line_num, False, ("non_dict_record",), None, None, None, (), None, None, "unknown", None, None, "unknown")
    try:
        containers = _extract_containers(record, line_num)
    except ValueError:
        return InspectedVoiceRecord(line_num, False, ("invalid_container_shape",), None, None, None, (), None, None, "unknown", None, None, "unknown")
    reasons: list[str] = []
    sys_v, usr_v, ast_v = record.get("system", DEFAULT_SYSTEM_PROMPT), record.get("user", ""), record.get("assistant")
    msgs = {"system": sys_v, "user": usr_v, "assistant": ast_v} if (isinstance(sys_v, str) and sys_v.strip() and isinstance(usr_v, str) and isinstance(ast_v, str) and ast_v.strip()) else None
    if msgs is None:
        reasons.append("invalid_messages")
    elig_v, fams, cons_v = _inspect_provenance_slice(containers, ast_v if isinstance(ast_v, str) else "", line_num, reasons)
    try:
        speaker, speaker_status = _inspect_speaker_state(containers, line_num)
        if speaker is None or speaker_status != "verified":
            reasons.append("missing_speaker_attribution" if speaker is None else "unverified_speaker_attribution")
    except ValueError as exc:
        speaker, speaker_status = None, ("unknown" if ("Unknown speaker" in str(exc) or "Missing or blank speaker" in str(exc)) else "invalid")
        reasons.append("invalid_or_mixed_speaker")
    try:
        t_start, t_end, ts_status, seg_idx = _validate_timestamps(containers, line_num)
    except ValueError:
        t_start, t_end, ts_status, seg_idx = None, None, "invalid", None
        reasons.append("invalid_timestamps")
    try:
        group_id = _extract_group_id(containers, line_num)
        if group_id is None:
            reasons.append("missing_group_id")
    except ValueError:
        group_id = None
        reasons.append("invalid_or_placeholder_group_id")
    b_raw = record.get("type")
    bucket = b_raw.strip().lower() if isinstance(b_raw, str) and b_raw.strip() else "__default__"
    return InspectedVoiceRecord(line_num, not reasons, tuple(reasons), msgs, group_id, elig_v, fams, cons_v, speaker, speaker_status, t_start, t_end, ts_status, seg_idx, bucket)


def _enforce_training_admission_flags(require_verified_speaker: Any, require_explicit_admission: Any) -> None:
    if type(require_verified_speaker) is not bool or require_verified_speaker is not True:
        raise ValueError("Admission invariant: require_verified_speaker must be True; use inspect_sft_record().")
    if type(require_explicit_admission) is not bool or require_explicit_admission is not True:
        raise ValueError("Admission invariant: require_explicit_admission must be True; use inspect_sft_record().")


def validate_sft_record(record: Any, line_num: int, *, require_verified_speaker: bool = True, require_explicit_admission: bool = True) -> ValidatedVoiceRecord:
    """Fail-closed training-boundary validator requiring all 5 explicit admission proofs."""
    _enforce_training_admission_flags(require_verified_speaker, require_explicit_admission)
    if not isinstance(record, dict):
        raise ValueError(f"Invalid record on line {line_num}: expected JSON object (dict), got {type(record).__name__}.")
    containers = _extract_containers(record, line_num)
    sys_v, usr_v, ast_v = record.get("system", DEFAULT_SYSTEM_PROMPT), record.get("user", ""), record.get("assistant")
    if not isinstance(sys_v, str) or not sys_v.strip() or not isinstance(usr_v, str):
        raise ValueError(f"Invalid 'system' or 'user' field on line {line_num}.")
    if not isinstance(ast_v, str) or not ast_v.strip():
        raise ValueError(f"Missing or empty 'assistant' target on line {line_num}: must be a non-empty string.")
    saw_eligible, families, saw_consent = _validate_eligibility_and_provenance(containers, ast_v, line_num)
    speaker, speaker_status = _inspect_speaker_state(containers, line_num)
    t_start, t_end, ts_status, seg_idx = _validate_timestamps(containers, line_num)
    group_id = _extract_group_id(containers, line_num)
    if not saw_eligible or not families or not saw_consent:
        missing = "training_eligible=True" if not saw_eligible else ("verbatim provenance (transcript_source)" if not families else "explicit positive consent=True")
        raise ValueError(f"Missing required {missing} on line {line_num}.")
    if speaker is None or speaker_status != "verified":
        msg = "Missing required principal speaker attribution" if speaker is None else f"Unverified speaker label ({speaker!r}); verified speaker required"
        raise ValueError(f"{msg} on line {line_num}.")
    if group_id is None:
        raise ValueError(f"Missing required source/video group ID (video_id/source_id) on line {line_num}.")
    b_raw = record.get("type")
    bucket = b_raw.strip().lower() if isinstance(b_raw, str) and b_raw.strip() else "__default__"
    return ValidatedVoiceRecord(line_num, {"system": sys_v, "user": usr_v, "assistant": ast_v}, group_id, speaker, speaker_status, t_start, t_end, ts_status, seg_idx, bucket)


def _enforce_sequence_monotonicity(records: list[ValidatedVoiceRecord]) -> None:
    last_by_stream: dict[tuple[str, str], ValidatedVoiceRecord] = {}
    for rec in records:
        prev = last_by_stream.get((rec.group_id, rec.record_bucket))
        if prev is not None:
            if rec.segment_idx is not None and prev.segment_idx is not None and rec.segment_idx < prev.segment_idx:
                raise ValueError(f"Nonmonotonic segment_idx on line {rec.line_num} for group {rec.group_id!r}: {rec.segment_idx} < {prev.segment_idx} (line {prev.line_num}).")
            if rec.t_start is not None and prev.t_start is not None:
                if rec.t_start < prev.t_start:
                    raise ValueError(f"Nonmonotonic timestamps on line {rec.line_num} for group {rec.group_id!r}: t_start={rec.t_start} < previous t_start={prev.t_start} (line {prev.line_num}).")
                if prev.t_end is not None and rec.t_start < prev.t_end:
                    raise ValueError(f"Nonmonotonic overlapping timestamps on line {rec.line_num} for group {rec.group_id!r}: t_start={rec.t_start} < previous t_end={prev.t_end} (line {prev.line_num}).")
        if rec.t_start is not None or rec.segment_idx is not None:
            last_by_stream[(rec.group_id, rec.record_bucket)] = rec


def load_and_validate_records(
    data_path: str | Path, *, require_verified_speaker: bool = True, require_explicit_admission: bool = True
) -> list[ValidatedVoiceRecord]:
    """Parse JSONL strictly and enforce fail-closed training admission + monotonicity."""
    _enforce_training_admission_flags(require_verified_speaker, require_explicit_admission)
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"Data not found: {path}")
    if not path.is_file():
        raise ValueError(f"Data path is not a regular file: {path}")
    records: list[ValidatedVoiceRecord] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_num, raw_line in enumerate(handle, start=1):
            if not (stripped := raw_line.strip()):
                continue
            try:
                parsed = json.loads(stripped, parse_constant=_reject_nonfinite_constant)
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"Malformed JSON on line {line_num} in {path}: {exc}") from exc
            records.append(validate_sft_record(parsed, line_num))
    if not records:
        raise ValueError(f"Training data file contains zero valid examples: {path}")
    _enforce_sequence_monotonicity(records)
    return records
