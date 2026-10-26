"""Bounded, injected provider adapters for kids episode research and music.

No credentials, daemon, uploads, or paid calls occur on import. Observations are
public metadata, not proof of educational value or permission to reuse content.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MUSIC_MODEL = "lyria-3-clip-preview"
MAX_AUDIO_BYTES = 32 * 1024 * 1024


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def collect_trend_snapshot(
    youtube_service: Any, queries: list[str], *, region: str = "US",
    language: str = "en", max_results: int = 5, observed_at: str | None = None,
) -> dict:
    """At most five searches and one statistics call; never paginate or retry.

    The caller supplies the existing authenticated YouTube service. Quota errors
    propagate: this function does not rotate accounts or hide partial failures.
    """
    if not 1 <= len(queries) <= 5 or any(
        not isinstance(q, str) or not q.strip() or len(q) > 200 for q in queries
    ):
        raise ValueError("Supply one to five nonempty queries of at most 200 characters")
    if type(max_results) is not int or not 1 <= max_results <= 10:
        raise ValueError("max_results must be an integer between 1 and 10")
    if not re.fullmatch(r"[A-Z]{2}", region) or not re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z]+)?", language):
        raise ValueError("Invalid region or language")
    timestamp = _time(observed_at).isoformat() if observed_at else datetime.now(timezone.utc).isoformat()
    candidates: dict[str, list[str]] = {}
    for query in queries:
        response = youtube_service.search().list(
            part="snippet", q=query.strip(), type="video", safeSearch="strict",
            regionCode=region, relevanceLanguage=language, order="date",
            maxResults=max_results,
        ).execute()
        for item in response.get("items", [])[:max_results]:
            video_id = item.get("id", {}).get("videoId", "")
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                candidates.setdefault(video_id, []).append(query.strip())
    rows = []
    if candidates:
        response = youtube_service.videos().list(
            part="snippet,statistics,contentDetails,status", id=",".join(candidates),
        ).execute()
        seen = set()
        for item in response.get("items", [])[:50]:
            video_id = item.get("id")
            if video_id not in candidates or video_id in seen:
                continue
            seen.add(video_id)
            raw_views = item.get("statistics", {}).get("viewCount")
            views = int(raw_views) if str(raw_views).isdigit() else None
            snippet = item.get("snippet", {})
            rows.append({
                "video_id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": snippet.get("title", ""), "channel_id": snippet.get("channelId"),
                "published_at": snippet.get("publishedAt"), "view_count": views,
                "observed_at": timestamp, "queries": candidates[video_id],
                "made_for_kids": item.get("status", {}).get("madeForKids"),
                "duration": item.get("contentDetails", {}).get("duration"),
            })
    return {"schema": "kids.trend_snapshot.v1", "observed_at": timestamp,
            "region": region, "language": language, "videos": rows,
            "scope": "bounded_topic_search_not_global_trending"}


def rank_observed_growth(current: dict, previous: dict | None = None) -> list[dict]:
    """Rank measured view growth, keeping baselines/invalid comparisons separate."""
    if previous and any(current.get(k) != previous.get(k) for k in ("region", "language")):
        raise ValueError("Snapshots must use the same region and language")
    old = {v["video_id"]: v for v in (previous or {}).get("videos", [])}
    ranked = []
    for row in current["videos"]:
        result = dict(row, evidence="baseline_only", views_per_hour=None, view_delta=None)
        prior = old.get(row["video_id"])
        if prior:
            elapsed = (_time(row["observed_at"]) - _time(prior["observed_at"])).total_seconds()
            views, before = row.get("view_count"), prior.get("view_count")
            if elapsed <= 0:
                result["evidence"] = "invalid_time_order"
            elif type(views) is not int or type(before) is not int or min(views, before) < 0:
                result["evidence"] = "missing_statistics"
            elif views < before:
                result["evidence"] = "counter_decreased"
            else:
                result.update(evidence="observed_growth", view_delta=views - before,
                              views_per_hour=(views - before) * 3600 / elapsed)
        ranked.append(result)
    return sorted(ranked, key=lambda v: (v["views_per_hour"] is not None,
                  v["views_per_hour"] or 0), reverse=True)


def generate_lyria_clip(client: Any, prompt: str, output_path: str | Path) -> dict:
    """One explicit potentially paid API request; save bounded audio/provenance.

    client must support the official interactions.create API. This function does
    not infer commercial rights or caption timings from provider success. Its
    fixed 30-second output still requires editing to the 15-second episode.
    """
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 4000:
        raise ValueError("Music prompt must contain 1 to 4000 characters")
    target = Path(output_path)
    metadata_path = target.with_suffix(".metadata.json")
    if target.suffix.lower() != ".mp3" or not target.parent.is_dir():
        raise ValueError("Use an .mp3 target in an existing output directory")
    if target.exists() or metadata_path.exists():
        raise FileExistsError("Music output or metadata already exists")
    response = client.interactions.create(model=MUSIC_MODEL, input=prompt.strip())
    audio = getattr(response, "output_audio", None)
    encoded = getattr(audio, "data", None)
    if not isinstance(encoded, (str, bytes)) or not encoded or len(encoded) > ((MAX_AUDIO_BYTES + 2) // 3) * 4:
        raise ValueError("Provider returned missing or oversized audio")
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Provider returned invalid audio encoding") from exc
    if not decoded or len(decoded) > MAX_AUDIO_BYTES:
        raise ValueError("Provider returned empty or oversized audio")
    # Check an MP3 signature without claiming complete decoder/media validation.
    if not (decoded.startswith(b"ID3") or (len(decoded) >= 2 and decoded[0] == 255 and decoded[1] & 224 == 224)):
        raise ValueError("Provider audio has no MP3 signature")
    metadata = {
        "schema": "kids.music_asset.v1", "provider": "google", "model": MUSIC_MODEL,
        "generated_at": datetime.now(timezone.utc).isoformat(), "path": str(target),
        "sha256": hashlib.sha256(decoded).hexdigest(), "bytes": len(decoded),
        "provider_documented_duration_seconds": 30, "measured_duration_seconds": None,
        "prompt": prompt.strip(), "lyrics": str(getattr(response, "output_text", "") or "")[:20000],
        "source": "https://ai.google.dev/gemini-api/docs/music-generation",
        "rights_status": "requires_review", "caption_alignment_status": "not_performed",
    }
    with target.open("xb") as stream:
        stream.write(decoded)
    try:
        with metadata_path.open("x", encoding="utf-8") as stream:
            json.dump(metadata, stream, ensure_ascii=False, indent=2)
    except Exception:
        target.unlink()  # Only this invocation's exclusively created output.
        raise
    return metadata
