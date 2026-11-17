"""Credential-free tests of bounds and evidence labels, not live provider proofs."""
import base64
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "kids_research.py"
loader = importlib.util.spec_from_file_location("kids_research_local_test", MODULE_PATH)
engine = importlib.util.module_from_spec(loader)
loader.loader.exec_module(engine)
collect_trend_snapshot = engine.collect_trend_snapshot
generate_lyria_clip = engine.generate_lyria_clip
rank_observed_growth = engine.rank_observed_growth

VIDEO = "abcdefghijk"


def service(views="100"):
    youtube = Mock()
    youtube.search.return_value.list.return_value.execute.return_value = {
        "items": [{"id": {"videoId": VIDEO}}, {"id": {"videoId": VIDEO}}]}
    youtube.videos.return_value.list.return_value.execute.return_value = {
        "items": [{"id": VIDEO, "snippet": {"title": "Count to three"},
                   "statistics": {"viewCount": views}}]}
    return youtube


def snapshot(views, hour):
    return collect_trend_snapshot(service(views), ["counting songs"],
                                 observed_at=f"2026-10-23T{hour:02d}:00:00Z")


def test_bounded_search_strict_and_deduplicated():
    youtube = service()
    result = collect_trend_snapshot(youtube, ["counting songs", "colors"], max_results=3)
    assert len(result["videos"]) == 1
    assert youtube.search.return_value.list.call_count == 2
    assert youtube.search.return_value.list.call_args.kwargs["safeSearch"] == "strict"
    assert youtube.videos.return_value.list.call_count == 1
    assert youtube.videos.return_value.list.call_args.kwargs["id"] == VIDEO
    assert "maxResults" not in youtube.videos.return_value.list.call_args.kwargs
    assert result["videos"][0]["url"].endswith(VIDEO)


@pytest.mark.parametrize("kwargs", [{"queries": []}, {"queries": ["x"] * 6},
    {"queries": ["x"], "max_results": 11}, {"queries": ["x"], "max_results": True},
    {"queries": ["x"], "observed_at": "2026-10-23T01:00:00"}])
def test_rejects_unbounded_or_ambiguous_requests_before_api(kwargs):
    youtube = Mock()
    with pytest.raises(ValueError):
        collect_trend_snapshot(youtube, **kwargs)
    youtube.search.assert_not_called()


def test_baseline_is_not_trend_and_growth_uses_elapsed_time():
    before, after = snapshot("100", 1), snapshot("130", 3)
    assert rank_observed_growth(before)[0]["evidence"] == "baseline_only"
    row = rank_observed_growth(after, before)[0]
    assert row["view_delta"] == 30
    assert row["views_per_hour"] == 15
    assert row["evidence"] == "observed_growth"


@pytest.mark.parametrize("views,hour,label", [("90", 2, "counter_decreased"),
    (None, 2, "missing_statistics"), ("110", 1, "invalid_time_order")])
def test_unusable_comparisons_do_not_claim_growth(views, hour, label):
    row = rank_observed_growth(snapshot(views, hour), snapshot("100", 1))[0]
    assert row["evidence"] == label
    assert row["views_per_hour"] is None


def music_client(data=b"ID3synthetic-test-only"):
    client = Mock()
    client.interactions.create.return_value = SimpleNamespace(
        output_audio=SimpleNamespace(data=base64.b64encode(data).decode()), output_text="One two three")
    return client


def test_music_saves_provenance_without_claiming_rights_or_alignment(tmp_path):
    client = music_client()
    target = tmp_path / "song.mp3"
    result = generate_lyria_clip(client, "Original counting song", target)
    client.interactions.create.assert_called_once_with(model="lyria-3-clip-preview", input="Original counting song")
    assert target.read_bytes() == b"ID3synthetic-test-only"
    assert target.with_suffix(".metadata.json").exists()
    assert result["rights_status"] == "requires_review"
    assert result["measured_duration_seconds"] is None


def test_music_never_overwrites_or_spends_on_existing_output(tmp_path):
    target = tmp_path / "song.mp3"
    target.write_bytes(b"existing")
    client = Mock()
    with pytest.raises(FileExistsError):
        generate_lyria_clip(client, "song", target)
    client.interactions.create.assert_not_called()
    assert target.read_bytes() == b"existing"


def test_bad_audio_is_not_written(tmp_path):
    with pytest.raises(ValueError, match="MP3 signature"):
        generate_lyria_clip(music_client(b"not audio"), "song", tmp_path / "song.mp3")
    assert not list(tmp_path.iterdir())


def test_audio_byte_limit(monkeypatch, tmp_path):
    monkeypatch.setattr(engine, "MAX_AUDIO_BYTES", 4)
    with pytest.raises(ValueError, match="oversized"):
        generate_lyria_clip(music_client(), "song", tmp_path / "song.mp3")
    assert not list(tmp_path.iterdir())


def test_provider_failure_is_not_retried_or_persisted(tmp_path):
    client = Mock()
    client.interactions.create.side_effect = RuntimeError("provider unavailable")
    with pytest.raises(RuntimeError, match="provider unavailable"):
        generate_lyria_clip(client, "song", tmp_path / "song.mp3")
    assert client.interactions.create.call_count == 1
    assert not list(tmp_path.iterdir())


def test_bad_base64_is_not_written(tmp_path):
    client = music_client()
    client.interactions.create.return_value.output_audio.data = "not valid!"
    with pytest.raises(ValueError, match="invalid audio encoding"):
        generate_lyria_clip(client, "song", tmp_path / "song.mp3")
    assert not list(tmp_path.iterdir())


def test_empty_search_does_not_spend_statistics_call():
    youtube = service()
    youtube.search.return_value.list.return_value.execute.return_value = {"items": []}
    result = collect_trend_snapshot(youtube, ["counting"])
    assert result["videos"] == []
    youtube.videos.assert_not_called()
