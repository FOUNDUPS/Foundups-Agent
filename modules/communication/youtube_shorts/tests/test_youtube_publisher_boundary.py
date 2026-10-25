from __future__ import annotations

from pathlib import Path

import pytest

# Load the publisher owner without importing unrelated generation SDKs.
import importlib.util
import sys


@pytest.fixture(autouse=True)
def publisher_owner(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "story_publisher_under_test", Path(__file__).parents[1] / "src/youtube_uploader.py"
    )
    owner = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, owner)
    spec.loader.exec_module(owner)
    monkeypatch.setitem(globals(), "YouTubeShortsUploader", owner.YouTubeShortsUploader)
    monkeypatch.setitem(globals(), "YouTubeUploadError", owner.YouTubeUploadError)



class ExecuteCall:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class UploadCall:
    def next_chunk(self):
        return None, {"id": "video-123"}


class Channels:
    def __init__(self, channel_id="channel-10"):
        self.channel_id = channel_id

    def list(self, **kwargs):
        if kwargs["part"] == "contentDetails":
            return ExecuteCall({"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "uploads"}}}]})
        return ExecuteCall({"items": [{"id": self.channel_id, "snippet": {"title": "Foundups"}}]})


class Videos:
    def __init__(self):
        self.insert_args = None

    def insert(self, **kwargs):
        self.insert_args = kwargs
        return UploadCall()


class PlaylistItems:
    def __init__(self):
        self.insert_args = None

    def insert(self, **kwargs):
        self.insert_args = kwargs
        return ExecuteCall({"id": "playlist-item-1"})

    def list(self, **kwargs):
        return ExecuteCall({"items": []})


class FakeYouTube:
    def __init__(self, channel_id="channel-10"):
        self._channels = Channels(channel_id)
        self._videos = Videos()
        self._playlist_items = PlaylistItems()

    def channels(self):
        return self._channels

    def videos(self):
        return self._videos

    def playlistItems(self):
        return self._playlist_items


def video_file(tmp_path: Path, suffix=".mp4") -> str:
    path = tmp_path / f"capture{suffix}"
    path.write_bytes(b"video")
    return str(path)


def test_uses_hardened_pinned_auth_factory(monkeypatch):
    monkeypatch.setenv("YT_UPLOAD_CHANNEL_ID_FOUNDUPS", "channel-10")
    calls = []

    def factory(**kwargs):
        calls.append(kwargs)
        return FakeYouTube()

    uploader = YouTubeShortsUploader("foundups", service_factory=factory)

    assert calls == [{"token_index": 10}]
    assert uploader.get_channel_info() == {"id": "channel-10", "title": "Foundups"}


def test_rejects_authorized_channel_mismatch(monkeypatch):
    monkeypatch.setenv("YT_UPLOAD_CHANNEL_ID_FOUNDUPS", "expected")

    with pytest.raises(YouTubeUploadError, match="channel mismatch"):
        YouTubeShortsUploader("foundups", youtube_service=FakeYouTube("other"))


def test_foundups_mall_requires_explicit_channel_pin(monkeypatch):
    monkeypatch.delenv("YT_UPLOAD_CHANNEL_ID_FOUNDUPS_MALL", raising=False)

    with pytest.raises(YouTubeUploadError, match="must pin"):
        YouTubeShortsUploader("foundups-mall", youtube_service=FakeYouTube())


def test_publishes_unlisted_and_attaches_playlist(tmp_path, monkeypatch):
    monkeypatch.setenv("YT_UPLOAD_CHANNEL_ID_FOUNDUPS_MALL", "channel-10")
    service = FakeYouTube()
    uploader = YouTubeShortsUploader("foundups-mall", youtube_service=service)

    result = uploader.publish_foundups_media(
        video_file(tmp_path),
        "AutoPost capture",
        "A test capture",
        author_id="fup_author",
        manifest_digest="abc123",
        playlist_id="playlist-1",
    )

    body = service._videos.insert_args["body"]
    assert body["status"]["privacyStatus"] == "unlisted"
    assert body["snippet"]["description"].endswith("manifest=abc123")
    assert service._videos.insert_args["notifySubscribers"] is False
    assert service._playlist_items.insert_args["body"]["snippet"] == {
        "playlistId": "playlist-1",
        "resourceId": {"kind": "youtube#video", "videoId": "video-123"},
    }
    assert result.video_id == "video-123"
    assert result.playlist_item_id == "playlist-item-1"
    assert result.privacy_status == "unlisted"


def test_upload_short_keeps_backward_compatible_url(tmp_path, monkeypatch):
    monkeypatch.setenv("YT_UPLOAD_CHANNEL_ID_FOUNDUPS", "channel-10")
    service = FakeYouTube()
    uploader = YouTubeShortsUploader("foundups", youtube_service=service)

    url = uploader.upload_short(video_file(tmp_path), "Short", "Description")

    assert url == "https://youtube.com/shorts/video-123"
    assert service._videos.insert_args["body"]["status"]["privacyStatus"] == "public"
    assert service._videos.insert_args["body"]["snippet"]["description"].endswith("#Shorts")


def test_rejects_non_video_file(tmp_path, monkeypatch):
    monkeypatch.setenv("YT_UPLOAD_CHANNEL_ID_FOUNDUPS", "channel-10")
    uploader = YouTubeShortsUploader("foundups", youtube_service=FakeYouTube())

    with pytest.raises(YouTubeUploadError, match="Unsupported upload media type"):
        uploader.publish_video(video_file(tmp_path, ".txt"), "Title", "Description")


@pytest.mark.parametrize("configured", ["0", "-1", "abc"])
def test_story_channel_rejects_invalid_oauth_override(monkeypatch, configured):
    monkeypatch.delenv("YT_UPLOAD_CREDENTIAL_SET_US_STORY_TIME", raising=False)
    if configured is not None:
        monkeypatch.setenv("YT_UPLOAD_CREDENTIAL_SET_US_STORY_TIME", configured)
    calls = []
    with pytest.raises(YouTubeUploadError, match="positive OAuth set"):
        YouTubeShortsUploader("us_story_time", service_factory=lambda **kw: calls.append(kw))
    assert calls == []


@pytest.mark.parametrize("pin", [None, "main-foundups"])
def test_story_channel_rejects_wrong_identity_or_conflicting_pin(monkeypatch, pin):
    monkeypatch.delenv("YT_UPLOAD_CHANNEL_ID_US_STORY_TIME", raising=False)
    if pin:
        monkeypatch.setenv("YT_UPLOAD_CHANNEL_ID_US_STORY_TIME", pin)
    service = FakeYouTube("wrong-channel")
    with pytest.raises(YouTubeUploadError):
        YouTubeShortsUploader("us_story_time", youtube_service=service)
    assert service._videos.insert_args is None


def test_story_episode_uses_selected_oauth_and_kids_review_upload(tmp_path, monkeypatch):
    monkeypatch.setenv("YT_UPLOAD_CREDENTIAL_SET_US_STORY_TIME", "23")
    monkeypatch.setenv("YT_UPLOAD_CHANNEL_ID_US_STORY_TIME", "UCfo9NxwyjAQvaVn3cEjXT4g")
    service = FakeYouTube("UCfo9NxwyjAQvaVn3cEjXT4g")
    calls = []
    def factory(**kwargs):
        calls.append(kwargs)
        return service
    uploader = YouTubeShortsUploader("us_story_time", service_factory=factory)
    uploader.publish_story_episode(video_file(tmp_path), "Little Shrew", "Preview",
                                   contains_synthetic_media=False)
    assert calls == [{"token_index": 23}]
    assert service._videos.insert_args["body"]["status"] == {
        "privacyStatus": "unlisted", "selfDeclaredMadeForKids": True,
        "containsSyntheticMedia": False,
    }
    assert service._videos.insert_args["notifySubscribers"] is False


def test_story_helper_refuses_other_channel_and_ambiguous_disclosure(tmp_path, monkeypatch):
    monkeypatch.setenv("YT_UPLOAD_CHANNEL_ID_FOUNDUPS", "channel-10")
    uploader = YouTubeShortsUploader("foundups", youtube_service=FakeYouTube())
    with pytest.raises(YouTubeUploadError, match="us_story_time"):
        uploader.publish_story_episode(video_file(tmp_path), "Title", "Preview",
                                       contains_synthetic_media=False)
    monkeypatch.setenv("YT_UPLOAD_CHANNEL_ID_US_STORY_TIME", "UCfo9NxwyjAQvaVn3cEjXT4g")
    uploader = YouTubeShortsUploader("us_story_time", youtube_service=FakeYouTube("UCfo9NxwyjAQvaVn3cEjXT4g"))
    with pytest.raises(YouTubeUploadError, match="boolean"):
        uploader.publish_story_episode(video_file(tmp_path), "Title", "Preview",
                                       contains_synthetic_media="false")


@pytest.mark.parametrize("override", [None, ""])
def test_story_channel_reuses_foundups_oauth_by_default(monkeypatch, override):
    monkeypatch.delenv("YT_UPLOAD_CREDENTIAL_SET_US_STORY_TIME", raising=False)
    if override is not None:
        monkeypatch.setenv("YT_UPLOAD_CREDENTIAL_SET_US_STORY_TIME", override)
    monkeypatch.delenv("YT_UPLOAD_CHANNEL_ID_US_STORY_TIME", raising=False)
    calls = []
    def factory(**kwargs):
        calls.append(kwargs)
        return FakeYouTube("UCfo9NxwyjAQvaVn3cEjXT4g")
    YouTubeShortsUploader("us_story_time", service_factory=factory)
    assert calls == [{"token_index": 10}]
