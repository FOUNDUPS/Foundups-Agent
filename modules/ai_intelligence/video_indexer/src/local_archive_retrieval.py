# -*- coding: utf-8 -*-
"""
Bounded Local YouTube Archive Retrieval Pilot (<= 10 records, read-only, offline).

WSP Compliance:
    WSP 50: Pre-Action Verification (explicit missing-transcript blocker reporting)
    WSP 62: Large File / Function Discipline (< 800 lines, all functions <= 50 lines)
    WSP 72: Module Independence (offline local dependencies only)
    WSP 84: Code Reuse (VideoIndexStore artifact schemas + VoiceMemory TF-IDF pattern)
    WSP 97: Truth Boundary (genuine timestamps vs None/ABSENT; zero external calls or ASR)
"""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from .local_archive_parsers import (
    MAX_JSONL_LINES,
    MAX_RECORD_FILE_BYTES,
    MEDIA_EXTENSIONS,
    SEMANTIC_SUMMARY_SOURCES,
    SPEAKER_UNKNOWN,
    SPEAKER_UNVERIFIED_LABEL,
    SPEAKER_VERIFIED,
    STATUS_BLOCKED_MISSING_TRANSCRIPT,
    STATUS_ERROR_UNREADABLE,
    STATUS_INDEXED,
    TIMESTAMP_ABSENT,
    TIMESTAMP_GENUINE,
    TIMESTAMP_INVALID,
    TIMESTAMP_NONMONOTONIC,
    TIMESTAMP_PARTIAL_START_ONLY,
    VERBATIM_SOURCES,
    PilotRecordStatus,
    PilotSegment,
    infer_video_id_from_path,
    parse_caption_file,
    parse_json3_payload,
    parse_json_file,
    parse_jsonl_file,
    parse_txt_file,
)

logger = logging.getLogger(__name__)

MAX_PILOT_RECORDS = 10

ENGLISH_STOPWORDS = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any",
    "are", "as", "at", "be", "because", "been", "before", "being", "below", "between",
    "both", "but", "by", "can", "could", "did", "do", "does", "doing", "down", "during",
    "each", "few", "for", "from", "further", "get", "got", "had", "has", "have", "having",
    "he", "her", "here", "hers", "herself", "him", "himself", "his", "how", "i", "if",
    "in", "into", "is", "it", "its", "itself", "just", "me", "more", "most", "my",
    "myself", "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other",
    "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so",
    "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "why", "will", "with", "would", "you", "your", "yours", "yourself",
    "yourselves",
})

_WORD_TOKEN_RE = re.compile(r"[a-z0-9_]+")
_CJK_SEQ_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]+")


@dataclass
class PilotQueryHit:
    """Structured search hit grounded to an exact local archive path, speaker, and timestamps."""
    rank: int
    score: float
    video_id: str
    source_path: str
    channel: Optional[str]
    title: str
    t_start: Optional[float]
    t_end: Optional[float]
    has_genuine_timestamps: bool
    timestamp_status: str
    snippet: str
    provenance: Dict[str, Any]
    speaker: Optional[str] = None
    speaker_status: str = SPEAKER_UNKNOWN
    deep_link: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PilotQueryResponse:
    """Structured query response with explicit not_found and blocker counts."""
    query: str
    hits: List[PilotQueryHit]
    hit_count: int
    not_found: bool
    min_score: float
    backend: str
    indexed_records: int
    indexed_segments: int
    blocked_missing_transcript_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "hits": [h.to_dict() for h in self.hits],
            "hit_count": self.hit_count,
            "not_found": self.not_found,
            "min_score": self.min_score,
            "backend": self.backend,
            "indexed_records": self.indexed_records,
            "indexed_segments": self.indexed_segments,
            "blocked_missing_transcript_count": self.blocked_missing_transcript_count,
        }


def _build_deep_link(
    video_id: str, t_start: Optional[float], has_genuine_timestamps: bool = True
) -> Optional[str]:
    vid = (video_id or "").strip()
    if vid and has_genuine_timestamps and t_start is not None:
        return f"https://www.youtube.com/watch?v={vid}&t={int(t_start)}s"
    return None


def _token_forms(token: str) -> set[str]:
    """Return token and lightweight morphological stem variants."""
    forms = {token}
    if len(token) >= 5 and token.endswith("ing"):
        forms.add(token[:-3])
    elif len(token) >= 5 and token.endswith("ed"):
        forms.add(token[:-2])
    elif len(token) >= 4 and token.endswith("es"):
        forms.add(token[:-2])
    elif len(token) >= 4 and token.endswith("s"):
        forms.add(token[:-1])
    return forms


def _extract_query_units(text: str) -> List[set[str]]:
    """Extract per-term feature groups (word+stems or CJK bigrams) preserving OOV count."""
    lowered = (text or "").lower()
    units: List[set[str]] = []
    for token in _WORD_TOKEN_RE.findall(lowered):
        if token in ENGLISH_STOPWORDS or (len(token) < 2 and not token.isdigit()):
            continue
        units.append(_token_forms(token))
    for seq in _CJK_SEQ_RE.findall(lowered):
        if len(seq) == 1:
            units.append({seq})
        else:
            units.extend({seq[i : i + 2]} for i in range(len(seq) - 1))
    return units


def _extract_content_features(text: str) -> set[str]:
    """Extract union of content features across all terms in text."""
    features: set[str] = set()
    for unit in _extract_query_units(text):
        features.update(unit)
    return features


def _resolve_entry_hints(
    entry: Union[str, Path, Dict[str, Any]], record_idx: int
) -> Tuple[Optional[Path], str, Optional[str], Optional[str]]:
    """Resolve file_path, video_id, channel, and title hints from path or manifest dict."""
    if not isinstance(entry, dict):
        p = Path(entry)
        return p, infer_video_id_from_path(p), None, None
    raw_p = entry.get("transcript_path") or entry.get("source_path") or entry.get("path") or entry.get("file_path") or entry.get("metadata_path")
    vid = str(entry.get("video_id") or "").strip() or None
    ch = str(entry.get("channel") or "").strip() or None
    title = str(entry.get("title") or "").strip() or None
    if not raw_p:
        return None, vid or f"record_{record_idx}", ch, title
    file_path = Path(str(raw_p))
    if entry.get("metadata_path") and entry.get("transcript_path"):
        mp = Path(str(entry["metadata_path"]))
        if mp.exists() and mp.stat().st_size <= MAX_RECORD_FILE_BYTES:
            try:
                m_obj = json.loads(mp.read_text(encoding="utf-8", errors="replace"))
                if isinstance(m_obj, dict):
                    vid = vid or str(m_obj.get("video_id") or m_obj.get("id") or "").strip() or None
                    ch = ch or str(m_obj.get("channel") or m_obj.get("uploader") or "").strip() or None
                    title = title or str(m_obj.get("title") or "").strip() or None
            except Exception:
                pass
    return file_path, vid or infer_video_id_from_path(file_path), ch, title


def _dispatch_file_parse(
    file_path: Path, record_id: str, vid: str, ch: Optional[str],
    title: Optional[str], include_semantic_summaries: bool,
) -> Tuple[PilotRecordStatus, List[PilotSegment]]:
    """Validate file safety boundaries and dispatch to format-specific parser."""
    src = str(file_path)
    if not file_path.exists():
        return PilotRecordStatus(src, vid, ch, title or "", "missing_file", STATUS_ERROR_UNREADABLE, 0, False, {}, "file_not_found"), []
    sfx = file_path.suffix.lower()
    if sfx in MEDIA_EXTENSIONS:
        return PilotRecordStatus(
            src, vid, ch, title or "", "media_untranscribed", STATUS_BLOCKED_MISSING_TRANSCRIPT,
            0, False, {"media_extension": sfx, "asr_triggered": False},
            "media_file_without_transcript_no_asr_permitted",
        ), []
    size = file_path.stat().st_size
    if size > MAX_RECORD_FILE_BYTES and sfx != ".jsonl":
        return PilotRecordStatus(
            src, vid, ch, title or "", sfx.lstrip(".") or "unknown", STATUS_ERROR_UNREADABLE,
            0, False, {"file_size_bytes": size}, f"exceeds_bounded_pilot_file_size:{size}",
        ), []
    if file_path.name.lower().endswith(".json3") or sfx == ".json3":
        return parse_json3_payload(json.loads(file_path.read_text(encoding="utf-8")), src, record_id, vid, ch, title or "")
    if sfx == ".json":
        return parse_json_file(file_path, record_id, vid, ch, title, include_semantic_summaries)
    if sfx == ".jsonl":
        return parse_jsonl_file(file_path, record_id, vid, ch, title)
    if sfx in {".srt", ".vtt"}:
        return parse_caption_file(file_path, record_id, vid, ch, title, fmt=sfx.lstrip("."))
    if sfx == ".txt":
        return parse_txt_file(file_path, record_id, vid, ch, title)
    return PilotRecordStatus(src, vid, ch, title or "", sfx.lstrip(".") or "unknown", STATUS_BLOCKED_MISSING_TRANSCRIPT, 0, False, {}, f"unsupported_format:{sfx}"), []


class LocalArchiveRetrievalPilot:
    """Bounded (<= 10 records) read-only local YouTube archive retrieval pilot."""

    def __init__(
        self, max_records: int = MAX_PILOT_RECORDS, min_score: float = 0.12,
        include_semantic_summaries: bool = True, force_lexical_fallback: bool = False,
    ) -> None:
        if isinstance(max_records, bool) or not isinstance(max_records, int) or not (1 <= max_records <= MAX_PILOT_RECORDS):
            raise ValueError(f"Bounded retrieval pilot requires 1 <= max_records <= {MAX_PILOT_RECORDS}; got {max_records!r}")
        self.max_records = max_records
        self.min_score = float(min_score)
        self.include_semantic_summaries = bool(include_semantic_summaries)
        self.force_lexical_fallback = bool(force_lexical_fallback)
        self.records: List[PilotRecordStatus] = []
        self.segments: List[PilotSegment] = []
        self.truncated_over_cap: int = 0
        self._vectorizer: Any = None
        self._tfidf_matrix: Any = None
        self._segment_features: List[set[str]] = []
        self._lexical_idf: Dict[str, float] = {}
        self._backend: str = "empty_index"

    @property
    def blocked_records(self) -> List[PilotRecordStatus]:
        return [r for r in self.records if r.status == STATUS_BLOCKED_MISSING_TRANSCRIPT]

    @property
    def indexed_records(self) -> List[PilotRecordStatus]:
        return [r for r in self.records if r.status == STATUS_INDEXED]

    def load_records(
        self, sources: Sequence[Union[str, Path, Dict[str, Any]]], *, reject_over_cap: bool = True
    ) -> Dict[str, Any]:
        """Load at most `self.max_records` (<= 10) local archive records read-only."""
        items = list(sources)
        if len(items) > self.max_records:
            if reject_over_cap:
                raise ValueError(f"Record count {len(items)} exceeds bounded pilot hard cap (max_records={self.max_records})")
            self.truncated_over_cap = len(items) - self.max_records
            items = items[: self.max_records]
        else:
            self.truncated_over_cap = 0
        self.records, self.segments = [], []
        for idx, entry in enumerate(items[: self.max_records]):
            self._ingest_entry(entry, idx)
        self._build_index()
        return self.get_summary()

    def load_directory(self, directory: Union[str, Path], *, reject_over_cap: bool = False) -> Dict[str, Any]:
        """Discover and load up to `self.max_records` candidate files from a directory."""
        dir_path = Path(directory)
        if not dir_path.is_dir():
            raise FileNotFoundError(f"Archive directory not found: {dir_path}")
        exts = {".json", ".jsonl", ".srt", ".vtt", ".json3", ".txt", *MEDIA_EXTENSIONS}
        candidates = sorted(p for p in dir_path.rglob("*") if p.is_file() and p.suffix.lower() in exts)
        return self.load_records(candidates, reject_over_cap=reject_over_cap)

    def load_manifest(self, manifest_path: Union[str, Path], *, reject_over_cap: bool = True) -> Dict[str, Any]:
        """Load sample records from a read-only JSON manifest file."""
        path = Path(manifest_path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        entries = raw if isinstance(raw, list) else None
        if isinstance(raw, dict):
            entries = next((raw[k] for k in ("samples", "selected_samples", "pilot_samples", "representative_samples", "records") if isinstance(raw.get(k), list)), None)
            if entries is None and isinstance(raw.get("part2_representative_samples_max_10"), dict):
                cand = raw["part2_representative_samples_max_10"].get("samples")
                entries = cand if isinstance(cand, list) else None
        if not isinstance(entries, list):
            raise ValueError(f"Manifest {path} must contain a list under samples/records")
        return self.load_records(entries, reject_over_cap=reject_over_cap)

    def _ingest_entry(self, entry: Union[str, Path, Dict[str, Any]], record_idx: int) -> None:
        file_path, vid, ch, title = _resolve_entry_hints(entry, record_idx)
        if file_path is None:
            self.records.append(PilotRecordStatus(
                "<missing_path>", vid, ch, title or "", "manifest_entry",
                STATUS_BLOCKED_MISSING_TRANSCRIPT, 0, False, {"manifest_only": True},
                "manifest_entry_missing_transcript_path",
            ))
            return
        try:
            status, segs = _dispatch_file_parse(file_path, f"rec_{record_idx}", vid, ch, title, self.include_semantic_summaries)
            self.records.append(status)
            self.segments.extend(segs)
        except Exception as exc:
            logger.warning("[ARCHIVE-PILOT] Failed reading %s: %s", file_path, exc)
            self.records.append(PilotRecordStatus(
                str(file_path), vid, ch, title or "", file_path.suffix.lower().lstrip(".") or "unknown",
                STATUS_ERROR_UNREADABLE, 0, False, {}, f"{type(exc).__name__}:{exc}",
            ))

    def _build_index(self) -> None:
        """Build local in-memory TF-IDF + lexical feature index (zero network/downloads)."""
        self._vectorizer, self._tfidf_matrix = None, None
        self._segment_features = [_extract_content_features(s.text) for s in self.segments]
        self._lexical_idf = {}
        if not self.segments:
            self._backend = "empty_index"
            return
        n_docs = len(self.segments)
        df_counts: Dict[str, int] = {}
        for feats in self._segment_features:
            for f in feats:
                df_counts[f] = df_counts.get(f, 0) + 1
        self._lexical_idf = {f: math.log((1.0 + n_docs) / (1.0 + df)) + 1.0 for f, df in df_counts.items()}
        if self.force_lexical_fallback:
            self._backend = "lexical_fallback"
            return
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            vec = TfidfVectorizer(max_features=10000, stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
            self._tfidf_matrix = vec.fit_transform([s.text for s in self.segments])
            self._vectorizer, self._backend = vec, "tfidf"
        except Exception:
            self._backend = "lexical_fallback"

    def _query_unit_weights(self, q_units: List[set[str]]) -> Tuple[List[Tuple[set[str], float, bool]], float]:
        """Compute per-unit IDF weights (assigning true OOV IDF) and L2 OOV norm factor."""
        oov_idf = math.log(1.0 + len(self.segments)) + 1.5
        weighted: List[Tuple[set[str], float, bool]] = []
        in_sq = total_sq = 0.0
        for u in q_units:
            in_vocab = any(f in self._lexical_idf for f in u)
            w = max((self._lexical_idf[f] for f in u if f in self._lexical_idf), default=oov_idf)
            weighted.append((u, w, in_vocab))
            total_sq += w * w
            if in_vocab:
                in_sq += w * w
        oov_norm = math.sqrt(in_sq / max(total_sq, 1e-9)) if total_sq > 0 else 0.0
        return weighted, oov_norm

    def _lexical_score(
        self, weighted_units: List[Tuple[set[str], float, bool]], seg_idx: int
    ) -> Tuple[float, float]:
        """Return (oov_aware_lexical_score, matched_unit_coverage) for segment `seg_idx`."""
        d_feats = self._segment_features[seg_idx]
        if not weighted_units or not d_feats:
            return 0.0, 0.0
        matched_count = 0
        m_w = q_w = 0.0
        for u, w, _ in weighted_units:
            q_w += w
            if u & d_feats:
                matched_count += 1
                m_w += w
        if matched_count == 0:
            return 0.0, 0.0
        unit_cov = matched_count / len(weighted_units)
        idfcov = m_w / max(q_w, 1e-9)
        return min(1.0, idfcov * unit_cov), unit_cov

    def _score_candidates(
        self, cleaned_query: str, q_units: List[set[str]], threshold: float, verbatim_only: bool
    ) -> List[Tuple[float, int]]:
        tfidf_scores = None
        if self._backend == "tfidf" and self._vectorizer is not None and self._tfidf_matrix is not None:
            try:
                from sklearn.metrics.pairwise import cosine_similarity
                tfidf_scores = cosine_similarity(self._vectorizer.transform([cleaned_query]), self._tfidf_matrix)[0]
            except Exception:
                tfidf_scores = None
        weighted_units, oov_norm = self._query_unit_weights(q_units)
        is_cjk = bool(_CJK_SEQ_RE.search(cleaned_query))
        scored: List[Tuple[float, int]] = []
        for idx, seg in enumerate(self.segments):
            if verbatim_only and not seg.provenance.get("is_verbatim"):
                continue
            lex, unit_cov = self._lexical_score(weighted_units, idx)
            if unit_cov == 0.0:
                continue
            if tfidf_scores is not None:
                attenuated_t = float(tfidf_scores[idx]) * oov_norm * unit_cov
                score = max(attenuated_t, lex) if is_cjk else (attenuated_t if attenuated_t > 0 else lex * 0.5)
            else:
                score = lex
            if score >= threshold:
                scored.append((round(score, 6), idx))
        scored.sort(key=lambda p: (-p[0], self.segments[p[1]].source_path, self.segments[p[1]].t_start if self.segments[p[1]].t_start is not None else float("inf")))
        return scored

    def query(
        self, query_text: str, *, top_k: int = 5, min_score: Optional[float] = None, verbatim_only: bool = False
    ) -> PilotQueryResponse:
        """Query the bounded local index and return grounded hits or explicit not_found."""
        threshold = self.min_score if min_score is None else float(min_score)
        cleaned = (query_text or "").strip()
        q_units = _extract_query_units(cleaned)
        if not cleaned or not q_units or not self.segments or top_k <= 0:
            return PilotQueryResponse(query_text, [], 0, True, threshold, self._backend, len(self.indexed_records), len(self.segments), len(self.blocked_records))
        scored = self._score_candidates(cleaned, q_units, threshold, verbatim_only)
        hits = [
            PilotQueryHit(
                rank=r, score=sc, video_id=self.segments[i].video_id, source_path=self.segments[i].source_path,
                channel=self.segments[i].channel, title=self.segments[i].title, t_start=self.segments[i].t_start,
                t_end=self.segments[i].t_end, has_genuine_timestamps=self.segments[i].has_genuine_timestamps,
                timestamp_status=self.segments[i].timestamp_status, snippet=self.segments[i].text,
                provenance=dict(self.segments[i].provenance), speaker=self.segments[i].speaker,
                speaker_status=self.segments[i].speaker_status,
                deep_link=_build_deep_link(
                    self.segments[i].video_id, self.segments[i].t_start, self.segments[i].has_genuine_timestamps
                ),
            )
            for r, (sc, i) in enumerate(scored[:top_k], start=1)
        ]
        return PilotQueryResponse(query_text, hits, len(hits), len(hits) == 0, threshold, self._backend, len(self.indexed_records), len(self.segments), len(self.blocked_records))

    def get_summary(self) -> Dict[str, Any]:
        """Return complete structured audit summary of loaded records and blockers."""
        return {
            "max_records_cap": self.max_records,
            "hard_ceiling": MAX_PILOT_RECORDS,
            "total_records_loaded": len(self.records),
            "indexed_records": len(self.indexed_records),
            "blocked_missing_transcript_count": len(self.blocked_records),
            "error_unreadable_count": sum(1 for r in self.records if r.status == STATUS_ERROR_UNREADABLE),
            "truncated_over_cap": self.truncated_over_cap,
            "indexed_segments": len(self.segments),
            "backend": self._backend,
            "records": [r.to_dict() for r in self.records],
            "blocked_records": [r.to_dict() for r in self.blocked_records],
        }


def run_local_archive_pilot(
    sources: Sequence[Union[str, Path, Dict[str, Any]]], queries: Sequence[str], *,
    max_records: int = MAX_PILOT_RECORDS, top_k: int = 5, min_score: float = 0.12,
    include_semantic_summaries: bool = True, reject_over_cap: bool = True,
) -> Dict[str, Any]:
    """Run bounded local archive retrieval pilot end-to-end (read-only, zero network)."""
    pilot = LocalArchiveRetrievalPilot(max_records=max_records, min_score=min_score, include_semantic_summaries=include_semantic_summaries)
    summary = pilot.load_records(sources, reject_over_cap=reject_over_cap)
    return {"summary": summary, "query_results": [pilot.query(q, top_k=top_k).to_dict() for q in queries]}
