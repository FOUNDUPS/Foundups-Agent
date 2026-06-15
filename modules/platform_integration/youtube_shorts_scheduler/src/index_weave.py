"""
Index Weave - Schedule ↔ Index ↔ Description (Digital Twin) integration.

Purpose:
    - Ensure a scheduled video has a local index JSON artifact.
    - Weave a compact "0102 DIGITAL TWIN INDEX" JSON block into description.
    - Update index JSON with scheduling + description_sync metadata.

WSP alignment:
    - WSP 27: DAE orchestration layer (scheduler triggers indexing)
    - WSP 60: Memory artifacts live in memory/video_index/{channel}/
    - WSP 73: Digital Twin architecture (description-as-cloud-memory)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


INDEX_BLOCK_HEADER = "0102 DIGITAL TWIN INDEX v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_hashtag(topic: str) -> str:
    # Remove spaces/punct that break hashtags; keep ascii-ish for reliability.
    cleaned = "".join(ch for ch in topic.strip() if ch.isalnum())
    return cleaned[:32]


def _safe_str(value: Any, *, max_len: int = 280) -> str:
    if not isinstance(value, str):
        return ""
    s = value.strip().replace("\r\n", "\n").replace("\r", "\n")
    if len(s) > max_len:
        s = s[: max_len - 3].rstrip() + "..."
    return s


def build_human_description_context(index_json: Dict[str, Any]) -> str:
    """
    Build a small human-facing context block from the index JSON.

    This is separate from the Digital Twin block (cloud memory); it is meant to
    increase description relevance/SEO while staying deterministic.
    """
    metadata = index_json.get("metadata") or {}
    summary = _safe_str(metadata.get("summary"), max_len=360)

    key_points = metadata.get("key_points") or []
    if not isinstance(key_points, list):
        key_points = []
    key_points = [_safe_str(k, max_len=120) for k in key_points if isinstance(k, str)]
    key_points = [k for k in key_points if k][:3]

    topics = metadata.get("topics") or []
    if not isinstance(topics, list):
        topics = []
    topics = [_safe_str(t, max_len=48) for t in topics if isinstance(t, str)]
    topics = [t for t in topics if t][:5]

    lines: List[str] = []
    if summary:
        lines.append("Summary:")
        lines.append(summary)

    if key_points:
        lines.append("")
        lines.append("Key points:")
        for kp in key_points:
            lines.append(f"- {kp}")

    if topics:
        lines.append("")
        lines.append("Topics:")
        lines.append(", ".join(topics))

    return "\n".join(lines).strip()


def inject_context_into_description(*, base_description: str, context_block: str) -> str:
    """
    Insert `context_block` into the description before the first hashtag block,
    if possible; otherwise append near the end.
    """
    base = (base_description or "").rstrip()
    context = (context_block or "").strip()
    if not context:
        return base

    # Avoid duplicating the same context if rerun.
    if context in base:
        return base

    # Common pattern in existing templates: split before first "\n\n#"
    parts = base.split("\n\n#", 1)
    if len(parts) == 2:
        head, tail = parts[0], parts[1]
        return f"{head}\n\n{context}\n\n#{tail}".rstrip()

    return f"{base}\n\n{context}".rstrip()


def get_index_base_dir() -> Path:
    # Keep consistent with video_indexer config/env.
    return Path(os.getenv("VIDEO_INDEXER_ARTIFACT_PATH", "memory/video_index"))


def get_index_json_path(*, channel_key: str, video_id: str, base_dir: Optional[Path] = None) -> Path:
    base = base_dir or get_index_base_dir()
    return base / channel_key.lower() / f"{video_id}.json"


def load_index_json(*, channel_key: str, video_id: str, base_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    path = get_index_json_path(channel_key=channel_key, video_id=video_id, base_dir=base_dir)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("[INDEX-WEAVE] Failed to read index json (%s): %s", path, exc)
        return None


def save_index_json(
    *,
    channel_key: str,
    video_id: str,
    data: Dict[str, Any],
    base_dir: Optional[Path] = None,
) -> bool:
    path = get_index_json_path(channel_key=channel_key, video_id=video_id, base_dir=base_dir)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception as exc:
        logger.warning("[INDEX-WEAVE] Failed to write index json (%s): %s", path, exc)
        return False


@dataclass(frozen=True)
class EnsureIndexResult:
    ok: bool
    used_existing: bool
    indexed_now: bool
    path: Optional[str] = None
    error: Optional[str] = None


def _extract_topics_from_title(title: str) -> List[str]:
    """Extract meaningful topics from video title using keyword detection."""
    if not title:
        return ["FFCPLN", "Music"]

    title_lower = title.lower()
    detected: List[str] = []

    # Topic keyword mappings (keyword -> topic)
    topic_keywords = {
        "ffcpln": "FFCPLN",
        "maga": "MAGA",
        "ice": "ICE",
        "trump": "Trump",
        "fascist": "Anti-Fascism",
        "antifa": "Anti-Fascism",
        "resist": "Resistance",
        "music": "Music",
        "song": "Music",
        "anthem": "Music",
        "epstein": "Epstein",
        "pedo": "Accountability",
        "nazi": "Anti-Fascism",
        "christian": "Christian Nationalism",
        "immigrant": "Immigration",
        "deport": "Immigration",
        "protest": "Protest",
        "raid": "ICE Raids",
    }

    for keyword, topic in topic_keywords.items():
        if keyword in title_lower and topic not in detected:
            detected.append(topic)

    # Ensure we have at least the defaults
    if not detected:
        detected = ["FFCPLN", "Music"]
    elif "FFCPLN" not in detected:
        detected.insert(0, "FFCPLN")

    return detected[:5]  # Max 5 topics


def _generate_key_point_from_title(title: str) -> List[str]:
    """Generate a key point from the title for description context."""
    if not title or len(title.strip()) < 10:
        return []

    clean_title = title.strip()
    # Remove common emoji prefixes/suffixes
    for emoji in ["🔥", "❌", "💀", "🚨", "⚠️", "👀", "🎵", "🎶"]:
        clean_title = clean_title.replace(emoji, "").strip()

    # Generate a key point based on title content
    title_lower = clean_title.lower()
    if "ffcpln" in title_lower:
        return [f"Part of the FFCPLN collection: {clean_title[:60]}"]
    elif "maga" in title_lower:
        return [f"Exposing MAGA hypocrisy: {clean_title[:60]}"]
    elif "ice" in title_lower:
        return [f"Documenting ICE cruelty: {clean_title[:60]}"]
    elif clean_title:
        return [f"Featured content: {clean_title[:60]}"]

    return []


def create_stub_index_json(
    *,
    channel_key: str,
    video_id: str,
    title: str = "",
    base_description: str = "",
    categories: Optional[List[str]] = None,
    topics: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Create a lightweight local-only index JSON for new uploads/unlisted videos.

    This is intentionally minimal and deterministic (no network calls). It enables:
    - description enhancement during scheduling
    - later enrichment by full indexers (Gemini/Whisper/browser) without losing linkage

    Enhanced to extract topics and key points from title for better description context.
    Channel-aware: Uses channel_key to set appropriate categories and summaries.
    """
    # Channel-aware default categories
    channel_defaults = {
        "move2japan": (["FFCPLN", "Music", "Japan", "Travel"], "Move2Japan FFCPLN short"),
        "foundups": (["pAVS", "AI", "Startup", "OpenClaw", "Agents"], "FoundUps pAVS short"),
        "undaodu": (["Mindfulness", "Spirituality", "Zen", "Meditation"], "UnDaoDu mindfulness short"),
        "antifafm": (["FFCPLN", "Music", "Political", "Shorts"], "antifaFM FFCPLN short"),
    }

    channel_lower = (channel_key or "").lower()
    default_cats, summary_prefix = channel_defaults.get(channel_lower, (["FFCPLN", "Music", "Shorts"], "FFCPLN short"))

    cats = categories[:] if categories else default_cats

    # Extract topics from title for richer metadata
    tops = topics[:] if topics else _extract_topics_from_title(title)

    # Generate key point from title for description context
    key_points = _generate_key_point_from_title(title)

    summary = f"{summary_prefix} (index stub; enrich later)."
    if isinstance(title, str) and title.strip():
        summary = f"{summary_prefix}: {title.strip()}"

    return {
        "video_id": video_id,
        "title": title or "",
        "indexed_at": _now_iso(),
        "indexer": "scheduler_stub",
        "audio": {
            "segments": [],
            "transcript_summary": "",
        },
        "visual": {
            "description": "",
            "keyframes": [],
        },
        "metadata": {
            "duration": "",
            "topics": tops,
            "speakers": [],
            "key_points": key_points,
            "summary": summary,
            "base_description_template": (base_description or "")[:500],
        },
        "classification": {
            "discovered_categories": cats,
            "book_references": [],
            "era": "modern",
            "themes": cats,
            "0102_relevance": {
                "bell_state_reference": False,
                "direct_address": False,
                "emergence_content": False,
                "anomaly_event": False,
                "anomaly_date": None,
            },
            "confidence": 0.30,
            "classified_by": "scheduler_stub",
            "classification_version": "v1",
        },
        "scheduling": {
            "is_scheduled": False,
            "scheduled_publish_date": None,
            "related_video_id": None,
            "scheduling_batch": None,
            "scheduled_at": None,
            "scheduled_by": None,
        },
        "description_sync": {
            "synced_to_youtube": False,
            "last_sync": None,
            "condensed_index": "",
        },
    }


def ensure_index_json(
    *,
    channel_key: str,
    video_id: str,
    allow_indexing_if_missing: bool = True,
    index_to_holoindex: bool = True,
    mode: str = "stub",
    stub_title: str = "",
    stub_base_description: str = "",
    base_dir: Optional[Path] = None,
) -> EnsureIndexResult:
    """
    Ensure `memory/video_index/{channel}/{video_id}.json` exists.

    Indexing mechanism (Tier 1):
        Gemini API via video_indexer.gemini_video_analyzer (no download).
    """
    path = get_index_json_path(channel_key=channel_key, video_id=video_id, base_dir=base_dir)
    if path.exists():
        return EnsureIndexResult(ok=True, used_existing=True, indexed_now=False, path=str(path))

    if not allow_indexing_if_missing:
        return EnsureIndexResult(ok=False, used_existing=False, indexed_now=False, path=str(path), error="missing")

    # Default for NEW unlisted Shorts: create a stub index immediately (no API calls).
    if (mode or "").lower() == "stub":
        stub = create_stub_index_json(
            channel_key=channel_key,
            video_id=video_id,
            title=stub_title,
            base_description=stub_base_description,
        )
        ok = save_index_json(channel_key=channel_key, video_id=video_id, data=stub, base_dir=base_dir)
        if ok:
            return EnsureIndexResult(ok=True, used_existing=False, indexed_now=True, path=str(path))
        return EnsureIndexResult(ok=False, used_existing=False, indexed_now=False, path=str(path), error="stub_write_failed")

    # Optional Tier 1: Gemini API indexing (costly; use when you explicitly want full indexing).
    if (mode or "").lower() not in ("gemini",):
        return EnsureIndexResult(ok=False, used_existing=False, indexed_now=False, path=str(path), error=f"unknown_mode:{mode}")

    try:
        from modules.ai_intelligence.video_indexer.src.gemini_video_analyzer import (
            GeminiVideoAnalyzer,
            save_analysis_result,
        )
    except Exception as exc:
        return EnsureIndexResult(
            ok=False,
            used_existing=False,
            indexed_now=False,
            path=str(path),
            error=f"gemini_indexer_unavailable: {exc}",
        )

    try:
        analyzer = GeminiVideoAnalyzer()
        result = analyzer.analyze_video(video_id)
        if not getattr(result, "success", False):
            return EnsureIndexResult(
                ok=False,
                used_existing=False,
                indexed_now=False,
                path=str(path),
                error=f"gemini_failed: {getattr(result, 'error', 'unknown')}",
            )

        out_dir = (base_dir or get_index_base_dir())
        saved_path = save_analysis_result(result, output_dir=str(out_dir), channel=channel_key, index_to_holoindex=index_to_holoindex)

        # Final confirmation
        if path.exists():
            return EnsureIndexResult(ok=True, used_existing=False, indexed_now=True, path=saved_path)

        # If the computed path didn't exist, fall back to saved_path check
        if saved_path and Path(saved_path).exists():
            return EnsureIndexResult(ok=True, used_existing=False, indexed_now=True, path=saved_path)

        return EnsureIndexResult(ok=False, used_existing=False, indexed_now=False, path=saved_path, error="index_write_missing")
    except Exception as exc:
        return EnsureIndexResult(ok=False, used_existing=False, indexed_now=False, path=str(path), error=str(exc))


def build_topic_hashtags(index_json: Dict[str, Any], *, max_tags: int = 5) -> List[str]:
    topics = []
    try:
        topics = (index_json.get("metadata") or {}).get("topics") or []
    except Exception:
        topics = []

    tags: List[str] = []
    for t in topics:
        if not isinstance(t, str):
            continue
        ht = _sanitize_hashtag(t)
        if ht:
            tags.append(f"#{ht}")
        if len(tags) >= max_tags:
            break
    return tags


def build_digital_twin_index_block(
    *,
    channel_key: str,
    video_id: str,
    index_json: Dict[str, Any],
) -> str:
    """
    Build a compact JSON block intended to be appended to the YouTube description.
    """
    metadata = index_json.get("metadata") or {}
    audio = index_json.get("audio") or {}

    key_points = metadata.get("key_points") or []
    key = key_points[0] if key_points and isinstance(key_points[0], str) else ""
    key = key.replace('"', "'")[:80]

    segs = audio.get("segments") or []
    seg_count = len(segs) if isinstance(segs, list) else 0

    cats: List[str] = []
    classification = index_json.get("classification") or {}
    if isinstance(classification, dict):
        dc = classification.get("discovered_categories") or []
        if isinstance(dc, list):
            cats = [c for c in dc if isinstance(c, str)][:4]
    if not cats:
        cats = [channel_key]

    topics = metadata.get("topics") or []
    if not isinstance(topics, list):
        topics = []
    topics = [t for t in topics if isinstance(t, str)][:5]

    indexed_at = index_json.get("indexed_at") or ""
    if isinstance(indexed_at, str):
        indexed_date = indexed_at[:10]
    else:
        indexed_date = ""

    payload = {
        "id": video_id,
        "channel": channel_key,
        "cat": cats,
        "topics": topics,
        "key": key,
        "segments": seg_count,
        "indexed": indexed_date,
        "twin_version": "0102.dt.v1",
    }

    return (
        "════════════════════════════════════════\n"
        f"{INDEX_BLOCK_HEADER}\n"
        "════════════════════════════════════════\n"
        f"{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n"
        "════════════════════════════════════════"
    )


def remove_existing_index_block(description: str) -> str:
    """
    Remove any previous 0102 index block to avoid duplication.
    """
    if INDEX_BLOCK_HEADER not in description:
        return description

    lines = description.splitlines()
    out: List[str] = []
    i = 0
    while i < len(lines):
        if INDEX_BLOCK_HEADER in lines[i]:
            # Walk backwards to remove leading separators if present.
            j = len(out) - 1
            while j >= 0 and out[j].strip("═").strip() == "":
                j -= 1
            out = out[: j + 1]

            # Skip forward until after the trailing separator line.
            i += 1
            while i < len(lines) and "════════" not in lines[i]:
                i += 1
            # Consume trailing separator line(s)
            while i < len(lines) and "════════" in lines[i]:
                i += 1
            continue

        out.append(lines[i])
        i += 1

    return "\n".join(out).rstrip()


def weave_description(
    *,
    base_description: str,
    index_block: Optional[str],
    extra_hashtags: Optional[List[str]] = None,
) -> str:
    """
    Produce description with (optional) index block and optional extra hashtags.
    """
    desc = remove_existing_index_block(base_description or "").rstrip()

    if extra_hashtags:
        hashtags_line = " ".join([h for h in extra_hashtags if isinstance(h, str) and h.startswith("#")])
        if hashtags_line and hashtags_line not in desc:
            desc = f"{desc}\n\n{hashtags_line}".rstrip()

    if index_block:
        desc = f"{desc}\n\n{index_block}".rstrip()

    return desc


@dataclass(frozen=True)
class MetadataContext:
    """
    Read-only context computed from an EXISTING index artifact.

    This carries the woven title/description that the scheduling/publish path
    applies via the live DOM. It is produced WITHOUT any live YouTube mutation
    and WITHOUT creating/refreshing the index artifact (no ensure_index_json,
    no save_index_json, no create_stub_index_json, no GeminiVideoAnalyzer).

    A None return from build_index_metadata_context() means "artifact missing ->
    skip enhancement" (NOT "index now").
    """
    new_title: str
    new_description: str
    used_index: bool


def build_index_metadata_context(
    *,
    channel_key: str,
    video_id: str,
    original_title: str,
    base_description: str,
    inform_title: bool = False,
    enhance_description: bool = True,
    base_dir: Optional[Path] = None,
) -> Optional[MetadataContext]:
    """
    PURE, read-only context builder (Phase 1 decoupling).

    Reads an EXISTING index artifact and composes the woven title/description.
    It NEVER touches the DOM/driver (takes no dom argument), NEVER creates or
    refreshes the artifact, and NEVER imports/instantiates GeminiVideoAnalyzer.

    Returns:
        MetadataContext when an artifact is present (used_index=True), carrying
        the composed new_title/new_description.
        None when the artifact is MISSING (load_index_json returned None) -> the
        caller treats this as "skip enhancement", NOT "index now".

    Composition mirrors the scheduling read path exactly so the live write bytes
    are unchanged for the artifact-present case:
        - optional index-informed title (inform_title)
        - optional human-facing context injection (enhance_description)
        - topic hashtags + Digital Twin index block woven into the description
    """
    idx = load_index_json(channel_key=channel_key, video_id=video_id, base_dir=base_dir)
    if not isinstance(idx, dict):
        # Artifact missing -> caller skips enhancement (does NOT index now).
        return None

    new_title = original_title
    if inform_title:
        try:
            from .content_generator import generate_clickbait_title_from_index

            new_title = generate_clickbait_title_from_index(
                original_title=original_title,
                index_json=idx,
            )
        except Exception as exc:
            logger.debug("[INDEX-WEAVE] Index-informed title skipped: %s", exc)
            new_title = original_title

    enhanced_base = base_description
    if enhance_description:
        context = build_human_description_context(idx)
        enhanced_base = inject_context_into_description(
            base_description=base_description,
            context_block=context,
        )

    tags = build_topic_hashtags(idx, max_tags=5)
    block = build_digital_twin_index_block(
        channel_key=channel_key,
        video_id=video_id,
        index_json=idx,
    )
    new_description = weave_description(
        base_description=enhanced_base,
        index_block=block,
        extra_hashtags=tags,
    )

    return MetadataContext(
        new_title=new_title,
        new_description=new_description,
        used_index=True,
    )


def update_index_after_schedule(
    *,
    index_json: Dict[str, Any],
    channel_key: str,
    video_id: str,
    date_str: str,
    time_str: str,
    scheduled_by: str = "0102",
    description_index_block: Optional[str] = None,
) -> Dict[str, Any]:
    updated = dict(index_json)

    publish_iso = f"{date_str}T{time_str}:00"
    updated["scheduling"] = {
        "is_scheduled": True,
        "scheduled_publish_date": publish_iso,
        "scheduled_at": _now_iso(),
        "scheduled_by": scheduled_by,
        "scheduling_batch": "youtube_shorts_scheduler",
    }

    if description_index_block:
        updated["description_sync"] = {
            "synced_to_youtube": True,
            "last_sync": _now_iso(),
            "condensed_index": description_index_block,
        }

    # Ensure top-level ids are present for downstream tooling
    updated.setdefault("video_id", video_id)
    updated.setdefault("channel", channel_key)

    return updated

