"""YouTube video publisher backed by the hardened YouTubeAuth boundary.

The uploader owns media validation and YouTube write operations. Credential
loading, refresh, account pinning and quota rotation stay in ``youtube_auth``.
No caller-facing API returns an OAuth credential or token path.
"""

from __future__ import annotations

import logging
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)


class YouTubeUploadError(Exception):
    """YouTube publishing failed without returning a verified video identity."""


@dataclass(frozen=True)
class YouTubePublishResult:
    """Authoritative identities returned by a completed YouTube write."""

    video_id: str
    channel_id: str
    privacy_status: str
    watch_url: str
    shorts_url: str
    playlist_id: Optional[str] = None
    playlist_item_id: Optional[str] = None


@dataclass(frozen=True)
class ChannelPolicy:
    credential_set: int
    expected_channel_env: str
    default_tags: tuple[str, ...]
    require_expected_channel: bool = False


CHANNEL_POLICIES = {
    "move2japan": ChannelPolicy(1, "YT_UPLOAD_CHANNEL_ID_MOVE2JAPAN", ("Shorts", "Japan", "Move2Japan")),
    "undaodu": ChannelPolicy(1, "YT_UPLOAD_CHANNEL_ID_UNDAODU", ("Shorts", "UnDaoDu")),
    "foundups": ChannelPolicy(10, "YT_UPLOAD_CHANNEL_ID_FOUNDUPS", ("Shorts", "FoundUps")),
    "antifafm": ChannelPolicy(10, "YT_UPLOAD_CHANNEL_ID_ANTIFAFM", ("Shorts", "antifaFM")),
    "foundups-mall": ChannelPolicy(
        10,
        "YT_UPLOAD_CHANNEL_ID_FOUNDUPS_MALL",
        ("FoundUps", "FoundupsMall"),
        require_expected_channel=True,
    ),
}

ALLOWED_PRIVACY = {"private", "unlisted", "public"}
ALLOWED_VIDEO_MIME = {"video/mp4", "video/webm", "video/quicktime"}


class YouTubeShortsUploader:
    """Publish YouTube videos through a channel-pinned authenticated service."""

    DEFAULT_TAGS = {key: list(policy.default_tags) for key, policy in CHANNEL_POLICIES.items()}

    @classmethod
    def get_supported_channels(cls) -> list[str]:
        return sorted(CHANNEL_POLICIES)

    def __init__(
        self,
        channel: str = "move2japan",
        *,
        youtube_service: Any = None,
        service_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        if channel not in CHANNEL_POLICIES:
            supported = ", ".join(self.get_supported_channels())
            raise YouTubeUploadError(f"Unknown channel: {channel}. Use: {supported}")

        self.channel = channel
        self.policy = CHANNEL_POLICIES[channel]
        if youtube_service is not None:
            self.youtube = youtube_service
        else:
            if service_factory is None:
                from modules.platform_integration.youtube_auth.src.youtube_auth import (
                    get_authenticated_service,
                )

                service_factory = get_authenticated_service
            try:
                self.youtube = service_factory(token_index=self.policy.credential_set)
            except Exception as exc:
                raise YouTubeUploadError(
                    f"Hardened YouTube authentication failed for {channel}: {exc}"
                ) from exc

        if self.youtube is None:
            raise YouTubeUploadError(f"No authenticated YouTube service returned for {channel}")

        self.channel_info = self._verify_authorized_channel()
        logger.info(
            "[UPLOAD-INIT] YouTube service initialized for %s (%s)",
            channel,
            self.channel_info["id"],
        )

    def _verify_authorized_channel(self) -> dict[str, str]:
        try:
            response = self.youtube.channels().list(part="id,snippet", mine=True).execute()
            items = response.get("items", [])
            if len(items) != 1:
                raise YouTubeUploadError(
                    f"Expected one authorized YouTube channel for {self.channel}; found {len(items)}"
                )
            item = items[0]
            channel_id = item.get("id", "").strip()
            title = item.get("snippet", {}).get("title", "").strip()
            if not channel_id:
                raise YouTubeUploadError("Authorized YouTube channel did not return an ID")

            expected = os.getenv(self.policy.expected_channel_env, "").strip()
            if self.policy.require_expected_channel and not expected:
                raise YouTubeUploadError(
                    f"{self.policy.expected_channel_env} must pin the Foundups Mall channel before publishing"
                )
            if expected and channel_id != expected:
                raise YouTubeUploadError(
                    f"Authorized channel mismatch for {self.channel}; refusing to publish"
                )
            if not expected:
                logger.warning(
                    "[UPLOAD-AUTH] %s is not configured; channel was observed but not policy-pinned",
                    self.policy.expected_channel_env,
                )
            return {"id": channel_id, "title": title}
        except YouTubeUploadError:
            raise
        except Exception as exc:
            raise YouTubeUploadError(f"Unable to verify authorized YouTube channel: {exc}") from exc

    @staticmethod
    def _media_type(video_path: str) -> str:
        guessed, _ = mimetypes.guess_type(video_path)
        if guessed not in ALLOWED_VIDEO_MIME:
            raise YouTubeUploadError(
                f"Unsupported upload media type: {guessed or 'unknown'}; use MP4, WebM, or QuickTime"
            )
        return guessed

    def publish_video(
        self,
        video_path: str,
        title: str,
        description: str,
        *,
        tags: Optional[list[str]] = None,
        privacy: str = "unlisted",
        playlist_id: Optional[str] = None,
        made_for_kids: bool = False,
        contains_synthetic_media: bool = False,
    ) -> YouTubePublishResult:
        """Upload one verified media file and optionally attach it to a playlist."""
        path = Path(video_path)
        if not path.is_file():
            raise YouTubeUploadError(f"Video file not found: {video_path}")
        if not title.strip():
            raise YouTubeUploadError("A YouTube title is required")
        if len(title) > 100:
            raise YouTubeUploadError("YouTube title exceeds 100 characters")
        if privacy not in ALLOWED_PRIVACY:
            raise YouTubeUploadError(f"Unsupported YouTube privacy status: {privacy}")

        mime_type = self._media_type(video_path)
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags if tags is not None else list(self.policy.default_tags),
                "categoryId": "22",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": made_for_kids,
                "containsSyntheticMedia": contains_synthetic_media,
            },
        }
        media = MediaFileUpload(
            video_path,
            mimetype=mime_type,
            resumable=True,
            chunksize=8 * 1024 * 1024,
        )
        try:
            request = self.youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
                notifySubscribers=False,
            )
            response = None
            last_logged = -10
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    if progress >= last_logged + 10:
                        logger.info("[UPLOAD-PROGRESS] %s%%", progress)
                        last_logged = progress
            video_id = str(response.get("id", "")).strip()
            if not video_id:
                raise YouTubeUploadError("YouTube upload completed without a video ID")

            playlist_item_id = None
            if playlist_id:
                playlist_response = self.youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": playlist_id,
                            "resourceId": {"kind": "youtube#video", "videoId": video_id},
                        }
                    },
                ).execute()
                playlist_item_id = str(playlist_response.get("id", "")).strip() or None

            return YouTubePublishResult(
                video_id=video_id,
                channel_id=self.channel_info["id"],
                privacy_status=privacy,
                watch_url=f"https://www.youtube.com/watch?v={video_id}",
                shorts_url=f"https://youtube.com/shorts/{video_id}",
                playlist_id=playlist_id,
                playlist_item_id=playlist_item_id,
            )
        except YouTubeUploadError:
            raise
        except Exception as exc:
            logger.error("[UPLOAD-ERROR] Upload failed: %s", exc)
            raise YouTubeUploadError(f"Upload failed: {exc}") from exc

    def publish_foundups_media(
        self,
        video_path: str,
        title: str,
        description: str,
        *,
        author_id: str,
        manifest_digest: str,
        playlist_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> YouTubePublishResult:
        """Publish a FoundUps-indexed unlisted video with a compact identity marker."""
        if not author_id.strip() or not manifest_digest.strip():
            raise YouTubeUploadError("FoundUps author ID and manifest digest are required")
        marker = (
            "\n\n[FOUNDUPS]\n"
            "schema=foundups.media.v1\n"
            f"author={author_id}\n"
            f"manifest={manifest_digest}"
        )
        foundups_tags = list(tags or self.policy.default_tags)
        if "FoundUps" not in foundups_tags:
            foundups_tags.append("FoundUps")
        return self.publish_video(
            video_path,
            title,
            description + marker,
            tags=foundups_tags,
            privacy="unlisted",
            playlist_id=playlist_id,
        )

    def upload_short(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[list[str]] = None,
        privacy: str = "public",
    ) -> str:
        """Backward-compatible Shorts helper returning only the Shorts URL."""
        if "#shorts" not in description.lower():
            description = f"{description} #Shorts"
        result = self.publish_video(
            video_path,
            title,
            description,
            tags=tags,
            privacy=privacy,
        )
        return result.shorts_url

    def get_channel_info(self) -> dict[str, str]:
        return dict(self.channel_info)

    def list_recent_shorts(self, max_results: int = 10) -> list[dict[str, str]]:
        try:
            channel_response = self.youtube.channels().list(
                part="contentDetails", mine=True
            ).execute()
            uploads_playlist_id = channel_response["items"][0]["contentDetails"][
                "relatedPlaylists"
            ]["uploads"]
            playlist_response = self.youtube.playlistItems().list(
                part="snippet", playlistId=uploads_playlist_id, maxResults=max_results
            ).execute()
            return [
                {
                    "video_id": item["snippet"]["resourceId"]["videoId"],
                    "title": item["snippet"]["title"],
                    "url": (
                        "https://youtube.com/shorts/"
                        f"{item['snippet']['resourceId']['videoId']}"
                    ),
                    "published_at": item["snippet"]["publishedAt"],
                }
                for item in playlist_response.get("items", [])
            ]
        except Exception as exc:
            logger.error("[UPLOAD-LIST] Error listing Shorts: %s", exc)
            return []
