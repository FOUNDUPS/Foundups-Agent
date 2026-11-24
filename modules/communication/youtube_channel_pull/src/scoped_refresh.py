"""Bounded, public-API-only refresh of HPC's approved YouTube collection.

This extends the known-channel ingest owner, not exploratory source admission.
The caller supplies a public YouTube service and owns atomic persistence and
publication. No OAuth, filesystem writes, subprocesses or scheduling occur here.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import re


APPROVED_CHANNEL_ID = "UC-LSSlOZwpGIRIYihaz8zCw"
RECEIPT_SCHEMA = "hpc_youtube_refresh.v1"
VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")
TOPICS = {
    "#SchumerOUT": re.compile(r"(?<!\w)schumer[\s_-]*out(?!\w)", re.IGNORECASE),
    "#HasanForSpeaker": re.compile(r"(?<!\w)hasan[\s_-]*for[\s_-]*speaker(?!\w)", re.IGNORECASE),
    "#Hasan4Speaker": re.compile(r"(?<!\w)hasan[\s_-]*4[\s_-]*speaker(?!\w)", re.IGNORECASE),
}
DURATION = re.compile(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?\Z")


class ScopedRefreshError(ValueError):
    """An incomplete or inconsistent source cannot replace the published state."""


def _utc(value: datetime | None = None) -> datetime:
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise ScopedRefreshError("A timezone-aware UTC observation is required")
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_time(value) -> datetime:
    if not isinstance(value, str):
        raise ScopedRefreshError("Missing source timestamp")
    try:
        return _utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except (TypeError, ValueError) as error:
        raise ScopedRefreshError("Invalid source timestamp") from error


def ensure_refresh_fresh(receipt: dict, *, now: datetime | None = None) -> None:
    """Refuse stale/future/incomplete receipts before publishing their output."""
    current = _utc(now)
    if (receipt.get("schema_version") != RECEIPT_SCHEMA
            or receipt.get("complete") is not True
            or receipt.get("source_channel_id") != APPROVED_CHANNEL_ID):
        raise ScopedRefreshError("Incomplete HPC refresh receipt")
    checked = _parse_time(receipt.get("checked_at"))
    expires = _parse_time(receipt.get("expires_at"))
    if (checked > current + timedelta(minutes=5) or expires <= checked
            or expires - checked > timedelta(hours=24) or current >= expires):
        raise ScopedRefreshError("HPC source verification is stale or future-dated")


def matched_topics(snippet: dict) -> dict[str, list[str]]:
    """Match actual source fields, including tags, without search-title inference."""
    tags = snippet.get("tags", [])
    if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
        raise ScopedRefreshError("Malformed source tags")
    fields = {"title": [snippet.get("title", "")],
              "description": [snippet.get("description", "")], "tags": tags}
    if any(not isinstance(value, str) for values in fields.values() for value in values):
        raise ScopedRefreshError("Malformed source snippet text")
    return {topic: [field for field, values in fields.items()
                    if any(pattern.search(value) for value in values)]
            for topic, pattern in TOPICS.items()
            if any(pattern.search(value) for values in fields.values() for value in values)}


def _execute(youtube, endpoint: str, calls: dict, **params) -> dict:
    calls[endpoint] = calls.get(endpoint, 0) + 1
    # Deliberately avoid interpolating exception bodies: API errors can include
    # request URLs containing the developer key. The CLI reports only this code.
    try:
        response = getattr(youtube, endpoint)().list(**params).execute()
    except Exception:
        raise ScopedRefreshError(f"YouTube {endpoint} request failed") from None
    if not isinstance(response, dict) or not isinstance(response.get("items"), list):
        raise ScopedRefreshError(f"Malformed YouTube {endpoint} response")
    return response


def _duration_seconds(value) -> int:
    match = DURATION.fullmatch(value) if isinstance(value, str) else None
    if not match or not any(match.groups()):
        raise ScopedRefreshError("Malformed source duration")
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def _source_record(video: dict, checked_at: str, now: datetime) -> tuple[dict, str | None]:
    snippet, status, details = (video.get(key) for key in ("snippet", "status", "contentDetails"))
    if not all(isinstance(item, dict) for item in (snippet, status, details)):
        raise ScopedRefreshError("Incomplete source video metadata")
    if snippet.get("channelId") != APPROVED_CHANNEL_ID:
        raise ScopedRefreshError("Video metadata does not belong to the approved source")
    if status.get("privacyStatus") != "public":
        return {}, "not_public"
    if status.get("embeddable") is not True:
        return {}, "not_embeddable"
    if status.get("uploadStatus") != "processed":
        return {}, "not_processed"
    if details.get("regionRestriction"):
        return {}, "region_restricted"
    if details.get("contentRating", {}).get("ytRating") == "ytAgeRestricted":
        return {}, "age_restricted"
    if snippet.get("liveBroadcastContent", "none") != "none":
        return {}, "live_or_upcoming"
    title, creator = snippet.get("title"), snippet.get("channelTitle")
    if not isinstance(title, str) or not title.strip() or not isinstance(creator, str) or not creator.strip():
        raise ScopedRefreshError("Missing authentic video title or creator credit")
    published = _parse_time(snippet.get("publishedAt"))
    if published > now + timedelta(minutes=5):
        return {}, "future_publication"
    duration = _duration_seconds(details.get("duration"))
    if duration <= 0:
        return {}, "empty_duration"
    topics = matched_topics(snippet)
    if not topics:
        return {}, "no_topic_match"
    video_id = video["id"]
    return {
        "video_id": video_id, "title": title, "timestamp": _iso(published),
        "duration_seconds": duration,
        # A watch URL is valid for regular videos and Shorts. API duration does
        # not establish Shorts membership, so new admissions never infer it.
        "source_url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "source_channel_id": APPROVED_CHANNEL_ID, "source_label": creator,
        "source_channel_url": f"https://www.youtube.com/channel/{APPROVED_CHANNEL_ID}",
        "matched_topics": topics, "publication_eligible": True,
        "source_checked_at": checked_at,
    }, None


def refresh_scoped_projection(
    youtube, config: dict, source: dict, *, previous_receipt: dict | None = None,
    now: datetime | None = None, max_pages: int = 100,
) -> tuple[dict, dict]:
    """Return refreshed HPC curation + a 24-hour public-source receipt.

    Existing editorial fields and order survive; source-owned metadata is
    rechecked for every retained ID. Newly eligible uploads are appended by
    descending source publication time (ID breaks ties). Ineligible old records
    stay in curation with ``publication_eligible=False`` for reversible recovery;
    the projection caller MUST exclude those records from its public output.

    The first run scans the complete uploads playlist within ``max_pages``.
    Incremental runs stop after the page containing the prior leading upload.
    Pass no previous receipt for a periodic complete metadata/backfill audit.
    This cannot discover edited hashtags outside an incremental scan's window.
    """
    current = _utc(now)
    if (config.get("foundup_id") != "hpc" or config.get("source_foundup_id") != "move2japan"
            or source.get("foundup_id") != "move2japan"
            or source.get("source_type") != "youtube_channel"
            or source.get("source_id") != APPROVED_CHANNEL_ID):
        raise ScopedRefreshError("HPC refresh is limited to its established approved source")
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= 100:
        raise ScopedRefreshError("max_pages must be between 1 and 100")
    existing = config.get("videos")
    if not isinstance(existing, list) or len(existing) > 10000:
        raise ScopedRefreshError("Invalid scoped curation records")
    existing_ids = []
    for record in existing:
        video_id = record.get("video_id") if isinstance(record, dict) else None
        if not isinstance(video_id, str) or not VIDEO_ID.fullmatch(video_id) or video_id in existing_ids:
            raise ScopedRefreshError("Invalid or duplicate curated video ID")
        existing_ids.append(video_id)

    frontier = None
    if previous_receipt is not None:
        # A stale receipt remains a useful traversal checkpoint, never release
        # authority. Source identity and non-future checkpoint dates still bind.
        if (previous_receipt.get("schema_version") != RECEIPT_SCHEMA
                or previous_receipt.get("complete") is not True
                or previous_receipt.get("source_channel_id") != APPROVED_CHANNEL_ID
                or _parse_time(previous_receipt.get("checked_at")) > current + timedelta(minutes=5)):
            raise ScopedRefreshError("Invalid incremental source checkpoint")
        frontier = previous_receipt.get("last_seen_upload_id")
        if frontier is not None and (not isinstance(frontier, str) or not VIDEO_ID.fullmatch(frontier)):
            raise ScopedRefreshError("Invalid incremental upload frontier")

    checked_at = _iso(current)
    calls: dict[str, int] = {}
    channel_response = _execute(youtube, "channels", calls, part="contentDetails", id=APPROVED_CHANNEL_ID)
    channels = channel_response["items"]
    if len(channels) != 1 or channels[0].get("id") != APPROVED_CHANNEL_ID:
        raise ScopedRefreshError("Expected the single approved public source channel")
    playlist = channels[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if not isinstance(playlist, str) or not playlist:
        raise ScopedRefreshError("Approved channel has no uploads playlist")

    ids, seen, duplicate_ids, seen_tokens = [], set(), [], set()
    token, reached_frontier, pages = None, False, 0
    while True:
        params = {"part": "contentDetails", "playlistId": playlist, "maxResults": 50}
        if token:
            params["pageToken"] = token
        response = _execute(youtube, "playlistItems", calls, **params)
        pages += 1
        for item in response["items"]:
            video_id = item.get("contentDetails", {}).get("videoId")
            if not isinstance(video_id, str) or not VIDEO_ID.fullmatch(video_id):
                raise ScopedRefreshError("Malformed uploads playlist video ID")
            if video_id in seen:
                duplicate_ids.append(video_id)
            else:
                ids.append(video_id)
                seen.add(video_id)
            reached_frontier = reached_frontier or (frontier is not None and video_id == frontier)
        next_token = response.get("nextPageToken")
        if next_token is not None and (not isinstance(next_token, str) or not next_token):
            raise ScopedRefreshError("Malformed uploads page token")
        if not next_token or reached_frontier:
            break
        if next_token in seen_tokens:
            raise ScopedRefreshError("Repeated uploads page token")
        if pages >= max_pages:
            raise ScopedRefreshError("Uploads scan exceeded page limit; no publication update")
        seen_tokens.add(next_token)
        token = next_token

    requested_ids = list(dict.fromkeys([*ids, *existing_ids]))
    metadata = {}
    for offset in range(0, len(requested_ids), 50):
        batch = requested_ids[offset:offset + 50]
        response = _execute(youtube, "videos", calls, part="snippet,status,contentDetails", id=",".join(batch))
        for video in response["items"]:
            video_id = video.get("id")
            if video_id not in batch or video_id in metadata:
                raise ScopedRefreshError("Unexpected or duplicate source video metadata")
            metadata[video_id] = video

    records, excluded = {}, []
    for video_id in requested_ids:
        if video_id not in metadata:
            excluded.append({"video_id": video_id, "reason": "unavailable"})
            continue
        record, reason = _source_record(metadata[video_id], checked_at, current)
        if reason:
            excluded.append({"video_id": video_id, "reason": reason})
        else:
            records[video_id] = record

    refreshed = deepcopy(config)
    refreshed["videos"] = []
    for old in deepcopy(existing):
        video_id = old["video_id"]
        if video_id in records:
            record = records[video_id]
            # Preserve reviewed source URLs/thumbnails (e.g. verified Shorts)
            # while updating authoritative title, creator and eligibility.
            record = dict(record)
            for key in ("source_url", "thumbnail_url"):
                if key in old:
                    record[key] = old[key]
                else:
                    # Legacy reviewed entries intentionally rely on the
                    # projection's verified Shorts/portrait defaults. Do not
                    # inject a new generic regular-video presentation for them.
                    record.pop(key, None)
            refreshed["videos"].append({**old, **record})
        else:
            refreshed["videos"].append({**old, "publication_eligible": False, "source_checked_at": checked_at})
    additions = [record for video_id, record in records.items() if video_id not in existing_ids]
    additions.sort(key=lambda record: (record["timestamp"], record["video_id"]), reverse=True)
    for record in additions:
        refreshed["videos"].append({**record, "editorial_label": "Commentary"})

    receipt = {
        "schema_version": RECEIPT_SCHEMA, "foundup_id": "hpc", "complete": True,
        "source_channel_id": APPROVED_CHANNEL_ID, "uploads_playlist": playlist,
        "checked_at": checked_at, "expires_at": _iso(current + timedelta(hours=24)),
        "scan_mode": "incremental" if frontier else "full",
        "reached_frontier": reached_frontier, "last_seen_upload_id": ids[0] if ids else frontier,
        "pages": pages, "scanned_unique_ids": len(ids), "duplicate_ids": duplicate_ids,
        "metadata_ids_checked": len(requested_ids), "api_requests": calls,
        "added_ids": [record["video_id"] for record in additions],
        "eligible_ids": [record["video_id"] for record in refreshed["videos"] if record["publication_eligible"]],
        "excluded": excluded,
    }
    ensure_refresh_fresh(receipt, now=current)
    return refreshed, receipt
