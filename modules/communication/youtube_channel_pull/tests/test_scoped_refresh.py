"""Behavioral coverage for HPC's bounded public-source admission path."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from modules.communication.youtube_channel_pull.src.scoped_refresh import (
    APPROVED_CHANNEL_ID, ScopedRefreshError, ensure_refresh_fresh,
    matched_topics, refresh_scoped_projection,
)


NOW = datetime(2026, 11, 25, 1, tzinfo=timezone.utc)
TARGET = "8qO3908bKAM"
OLD = "iJuguXpbRR4"
OTHER = "sSzWdw7MNjs"
SOURCE = {"foundup_id": "move2japan", "source_type": "youtube_channel", "source_id": APPROVED_CHANNEL_ID}


def metadata(video_id=TARGET, **updates):
    record = {
        "id": video_id,
        "snippet": {
            "title": "HasanAbi 4 House Speaker 🏠🔊 #hasan4speaker",
            "description": "", "tags": [], "channelId": APPROVED_CHANNEL_ID,
            "channelTitle": "Move2Japan", "publishedAt": "2026-11-24T10:00:00Z",
            "liveBroadcastContent": "none",
        },
        "status": {"privacyStatus": "public", "embeddable": True, "uploadStatus": "processed"},
        "contentDetails": {"duration": "PT1H39M50S"},
    }
    for key, value in updates.items():
        record[key].update(value)
    return record


def config():
    return {
        "foundup_id": "hpc", "source_foundup_id": "move2japan", "topic": "#SchumerOUT",
        "videos": [{"video_id": OLD, "title": "Old reviewed title", "duration_seconds": 60,
                    "timestamp": "2026-11-11T01:00:25Z", "editorial_label": "Satire",
                    "stable_id": "reviewed-1", "note": "Preserve editorial note"}],
    }


class YouTube:
    def __init__(self, pages=None, videos=None):
        self.pages = pages or [[TARGET, OLD]]
        self.videos_by_id = videos if videos is not None else {TARGET: metadata(), OLD: metadata(OLD)}
        self.calls = []
        self.response_transform = lambda method, response: response

    def endpoint(self, method):
        owner = self

        class Endpoint:
            def list(self, **params):
                self.params = params
                owner.calls.append((method, params))
                return self

            def execute(self):
                if method == "channels":
                    response = {"items": [{"id": APPROVED_CHANNEL_ID, "contentDetails": {
                        "relatedPlaylists": {"uploads": "UU-LSSlOZwpGIRIYihaz8zCw"}}}]}
                elif method == "playlistItems":
                    page = int(self.params.get("pageToken", 0))
                    response = {"items": [{"contentDetails": {"videoId": video_id}} for video_id in owner.pages[page]]}
                    if page + 1 < len(owner.pages):
                        response["nextPageToken"] = str(page + 1)
                else:
                    response = {"items": [deepcopy(owner.videos_by_id[video_id])
                                          for video_id in self.params["id"].split(",")
                                          if video_id in owner.videos_by_id]}
                return owner.response_transform(method, response)

        return Endpoint()

    def channels(self):
        return self.endpoint("channels")

    def playlistItems(self):
        return self.endpoint("playlistItems")

    def videos(self):
        return self.endpoint("videos")


def test_exact_requested_regular_video_added_and_editorial_state_preserved():
    before = config()
    saved = deepcopy(before)
    refreshed, receipt = refresh_scoped_projection(YouTube(), before, SOURCE, now=NOW)
    assert before == saved  # caller state is never mutated
    assert [video["video_id"] for video in refreshed["videos"]] == [OLD, TARGET]
    old, added = refreshed["videos"]
    assert {key: old[key] for key in ("editorial_label", "stable_id", "note")} == {
        "editorial_label": "Satire", "stable_id": "reviewed-1", "note": "Preserve editorial note"}
    assert added["title"] == metadata()["snippet"]["title"]
    assert added["duration_seconds"] == 5990  # observed regular video; no Shorts-only limit
    assert added["source_url"] == f"https://www.youtube.com/watch?v={TARGET}"
    assert added["source_label"] == "Move2Japan"
    assert added["source_channel_id"] == APPROVED_CHANNEL_ID
    assert receipt["added_ids"] == [TARGET]
    assert receipt["eligible_ids"] == [OLD, TARGET]
    assert receipt["api_requests"] == {"channels": 1, "playlistItems": 1, "videos": 1}


@pytest.mark.parametrize("field,text,topic", [
    ("title", "#sChUmErOuT", "#SchumerOUT"),
    ("description", "Watch #HaSaNfOrSpEaKeR!", "#HasanForSpeaker"),
    ("tags", "Hasan4Speaker", "#Hasan4Speaker"),
    ("title", "Schumer out", "#SchumerOUT"),
    ("description", "Hasan for Speaker", "#HasanForSpeaker"),
])
def test_topics_match_real_fields_case_insensitively(field, text, topic):
    snippet = {"title": "Other title", "description": "", "tags": []}
    snippet[field] = [text] if field == "tags" else text
    assert matched_topics(snippet) == {topic: [field]}


@pytest.mark.parametrize("text", ["preSchumerOUT", "#SchumerOUTside", "#Hasan4Speakerly", "#HasanForSpeakers", "Hasan House Speaker"])
def test_topic_boundaries_and_no_inference_from_nearby_words(text):
    assert matched_topics({"title": text}) == {}


def test_incremental_rerun_deduplicates_all_stored_ids_and_rechecks_old_records():
    initial, receipt = refresh_scoped_projection(YouTube(), config(), SOURCE, now=NOW)
    service = YouTube(pages=[[OTHER, TARGET, TARGET], [OLD]], videos={
        TARGET: metadata(), OLD: metadata(OLD), OTHER: metadata(OTHER),
    })
    result, rerun = refresh_scoped_projection(service, initial, SOURCE, previous_receipt=receipt, now=NOW + timedelta(hours=6))
    assert [v["video_id"] for v in result["videos"]] == [OLD, TARGET, OTHER]
    assert rerun["added_ids"] == [OTHER]
    assert rerun["duplicate_ids"] == [TARGET]
    assert rerun["reached_frontier"] is True
    assert rerun["pages"] == 1
    videos_call = next(params for method, params in service.calls if method == "videos")
    assert set(videos_call["id"].split(",")) == {OLD, TARGET, OTHER}
    again, final = refresh_scoped_projection(YouTube(pages=[[OTHER, TARGET, OLD]], videos=service.videos_by_id),
                                            result, SOURCE, previous_receipt=rerun, now=NOW + timedelta(hours=12))
    assert [v["video_id"] for v in again["videos"]] == [OLD, TARGET, OTHER]
    assert final["added_ids"] == []


@pytest.mark.parametrize("updates,reason", [
    ({"status": {"privacyStatus": "private"}}, "not_public"),
    ({"status": {"privacyStatus": "unlisted"}}, "not_public"),
    ({"status": {"embeddable": False}}, "not_embeddable"),
    ({"status": {"uploadStatus": "uploaded"}}, "not_processed"),
    ({"contentDetails": {"regionRestriction": {"blocked": ["JP"]}}}, "region_restricted"),
    ({"contentDetails": {"regionRestriction": {"allowed": ["US"]}}}, "region_restricted"),
    ({"contentDetails": {"contentRating": {"ytRating": "ytAgeRestricted"}}}, "age_restricted"),
    ({"snippet": {"liveBroadcastContent": "upcoming"}}, "live_or_upcoming"),
    ({"snippet": {"publishedAt": "2026-11-26T00:00:00Z"}}, "future_publication"),
    ({"snippet": {"title": "Unrelated", "description": "", "tags": []}}, "no_topic_match"),
])
def test_ineligible_new_video_is_excluded_and_old_metadata_retained(updates, reason):
    service = YouTube(videos={TARGET: metadata(**updates), OLD: metadata(OLD, **updates)})
    before = config()
    refreshed, receipt = refresh_scoped_projection(service, before, SOURCE, now=NOW)
    assert receipt["added_ids"] == []
    assert receipt["eligible_ids"] == []
    assert refreshed["videos"][0]["publication_eligible"] is False
    assert refreshed["videos"][0]["note"] == before["videos"][0]["note"]
    assert {item["reason"] for item in receipt["excluded"]} == {reason}


def test_missing_ids_are_unavailable_and_source_credit_is_authentic():
    service = YouTube(videos={TARGET: metadata(snippet={"channelTitle": "Updated actual creator name"})})
    result, receipt = refresh_scoped_projection(service, config(), SOURCE, now=NOW)
    assert result["videos"][0]["publication_eligible"] is False
    assert result["videos"][1]["source_label"] == "Updated actual creator name"
    assert receipt["excluded"] == [{"video_id": OLD, "reason": "unavailable"}]


def test_documented_editorial_hold_blocks_matching_upload_until_reviewed_removal():
    held_id = "B0P1Zci5Pxo"
    reviewed = config()
    reviewed["editorial_exclusions"] = {held_id: "Stephen Miller-led co-topic; prior reviewed exclusion"}
    service = YouTube(pages=[[held_id, TARGET, OLD]], videos={
        held_id: metadata(held_id, snippet={"title": "A real #SchumerOUT match"}),
        TARGET: metadata(), OLD: metadata(OLD),
    })
    refreshed, receipt = refresh_scoped_projection(service, reviewed, SOURCE, now=NOW)
    assert held_id not in [video["video_id"] for video in refreshed["videos"]]
    assert held_id not in receipt["eligible_ids"]
    assert receipt["added_ids"] == [TARGET]
    assert {"video_id": held_id, "reason": "editorial_hold",
            "editorial_reason": reviewed["editorial_exclusions"][held_id]} in receipt["excluded"]
    refreshed["editorial_exclusions"].pop(held_id)  # explicit curation review is the admission boundary
    admitted, reviewed_receipt = refresh_scoped_projection(service, refreshed, SOURCE, now=NOW)
    assert held_id in [video["video_id"] for video in admitted["videos"]]
    assert reviewed_receipt["added_ids"] == [held_id]


@pytest.mark.parametrize("missing_held_metadata", [False, True])
def test_retained_editorial_hold_survives_reruns_even_when_metadata_is_unavailable(missing_held_metadata):
    held_id = "B0P1Zci5Pxo"
    reviewed = config()
    reviewed["editorial_exclusions"] = {held_id: "Prior editorial review hold"}
    reviewed["videos"].append({"video_id": held_id, "title": "Retain old review evidence", "note": "old editorial note",
                               "editorial_label": "Opinion", "stable_id": "held-retained-1"})
    videos = {OLD: metadata(OLD), TARGET: metadata()}
    if not missing_held_metadata:
        videos[held_id] = metadata(held_id)
    service = YouTube(videos=videos)
    refreshed, receipt = refresh_scoped_projection(service, reviewed, SOURCE, now=NOW)
    retained = next(video for video in refreshed["videos"] if video["video_id"] == held_id)
    assert retained["publication_eligible"] is False
    assert retained["editorial_label"] == "Opinion"
    assert retained["stable_id"] == "held-retained-1"
    assert retained["note"] == "old editorial note"
    assert receipt["excluded"] == [{"video_id": held_id, "reason": "editorial_hold", "editorial_reason": "Prior editorial review hold"}]
    rerun, next_receipt = refresh_scoped_projection(service, refreshed, SOURCE, previous_receipt=receipt, now=NOW)
    assert held_id not in next_receipt["eligible_ids"]
    assert [video["video_id"] for video in rerun["videos"]] == [OLD, held_id, TARGET]


@pytest.mark.parametrize("holds", [["B0P1Zci5Pxo"], {"not-an-id": "Hold"}, {"B0P1Zci5Pxo": ""}, {"B0P1Zci5Pxo": False}])
def test_malformed_editorial_exclusions_fail_before_source_requests(holds):
    service = YouTube()
    with pytest.raises(ScopedRefreshError):
        refresh_scoped_projection(service, {**config(), "editorial_exclusions": holds}, SOURCE, now=NOW)
    assert service.calls == []


def test_bounded_full_pagination_batches_metadata_and_stable_addition_order():
    ids = [f"v{i:010d}" for i in range(110)]
    service = YouTube(pages=[ids[:50], ids[49:99], ids[99:]], videos={v: metadata(v) for v in ids})
    result, receipt = refresh_scoped_projection(service, {**config(), "videos": []}, SOURCE, now=NOW)
    assert receipt["scanned_unique_ids"] == 110
    assert receipt["pages"] == 3
    assert receipt["duplicate_ids"] == [ids[49]]
    assert len([call for call in service.calls if call[0] == "videos"]) == 3
    assert [v["video_id"] for v in result["videos"]] == sorted(ids, reverse=True)
    assert all(len(params["id"].split(",")) <= 50 for method, params in service.calls if method == "videos")


@pytest.mark.parametrize("failure", ["page_limit", "repeated_token", "source_mismatch", "malformed_metadata", "duplicate_metadata", "api_error"])
def test_incomplete_source_failure_preserves_input(failure):
    service = YouTube()
    kwargs = {}
    if failure == "page_limit":
        service.pages = [[TARGET], [OLD]]
        kwargs["max_pages"] = 1
    elif failure == "repeated_token":
        service.pages = [[TARGET], [OLD], [OTHER]]
        service.response_transform = lambda method, response: {**response, "nextPageToken": "1"} if method == "playlistItems" else response
    elif failure == "source_mismatch":
        service.videos_by_id[TARGET] = metadata(snippet={"channelId": "UC-unapproved"})
    elif failure == "malformed_metadata":
        service.videos_by_id[TARGET]["snippet"].pop("channelTitle")
    elif failure == "duplicate_metadata":
        service.response_transform = lambda method, response: {"items": response["items"] * 2} if method == "videos" else response
    elif failure == "api_error":
        def error_response(method, response):
            raise RuntimeError("private API request diagnostics")
        service.response_transform = error_response
    before = config()
    saved = deepcopy(before)
    with pytest.raises(ScopedRefreshError):
        refresh_scoped_projection(service, before, SOURCE, now=NOW, **kwargs)
    assert before == saved


def test_unapproved_source_and_duplicate_curation_refused_before_api():
    service = YouTube()
    with pytest.raises(ScopedRefreshError):
        refresh_scoped_projection(service, config(), {**SOURCE, "source_id": "UC-other"}, now=NOW)
    assert service.calls == []
    before = config()
    before["videos"] *= 2
    with pytest.raises(ScopedRefreshError):
        refresh_scoped_projection(service, before, SOURCE, now=NOW)
    assert service.calls == []


def test_receipt_freshness_expiry_future_dates_and_incomplete_state():
    _, receipt = refresh_scoped_projection(YouTube(), config(), SOURCE, now=NOW)
    ensure_refresh_fresh(receipt, now=NOW + timedelta(hours=23, minutes=59))
    with pytest.raises(ScopedRefreshError):
        ensure_refresh_fresh(receipt, now=NOW + timedelta(hours=24))
    with pytest.raises(ScopedRefreshError):
        ensure_refresh_fresh(receipt, now=NOW - timedelta(minutes=6))
    with pytest.raises(ScopedRefreshError):
        ensure_refresh_fresh({**receipt, "complete": False}, now=NOW)
    with pytest.raises(ScopedRefreshError):
        ensure_refresh_fresh({**receipt, "expires_at": "2026-11-27T01:00:00Z"}, now=NOW)


def test_preserves_verified_short_links_and_all_editorial_ids():
    before = config()
    before["videos"][0].update({"source_url": f"https://www.youtube.com/shorts/{OLD}",
                               "thumbnail_url": f"https://i.ytimg.com/vi/{OLD}/oardefault.jpg"})
    result, _ = refresh_scoped_projection(YouTube(), before, SOURCE, now=NOW)
    assert result["videos"][0]["source_url"] == before["videos"][0]["source_url"]
    assert result["videos"][0]["thumbnail_url"] == before["videos"][0]["thumbnail_url"]


def test_preserves_legacy_absent_source_links_and_portrait_defaults():
    before = config()
    result, _ = refresh_scoped_projection(YouTube(), before, SOURCE, now=NOW)
    assert "source_url" not in result["videos"][0]
    assert "thumbnail_url" not in result["videos"][0]
    assert result["videos"][1]["source_url"] == f"https://www.youtube.com/watch?v={TARGET}"
    assert result["videos"][1]["thumbnail_url"] == f"https://i.ytimg.com/vi/{TARGET}/hqdefault.jpg"


def test_live_seed_preserves_published_order_and_local_editorial_corrections():
    from scripts.refresh_mall_catalog import seed_hpc_from_live

    local = config()
    local["videos"].append({"video_id": OTHER, "editorial_label": "Opinion", "note": "Local unpublished addition"})
    before = deepcopy(local)
    live = {"hpc": {"lane": {
        "foundup_id": "hpc", "source_id": APPROVED_CHANNEL_ID,
        "videos": [
            {"video_id": TARGET, "title": "Published target", "editorial_label": "Commentary"},
            {"video_id": OLD, "title": "Published older title", "editorial_label": "Opinion"},
        ],
    }}}
    published_before = deepcopy(live)
    result = seed_hpc_from_live(local, live)
    assert [video["video_id"] for video in result["videos"]] == [TARGET, OLD, OTHER]
    assert result["videos"][1]["editorial_label"] == "Satire"
    assert result["videos"][1]["stable_id"] == "reviewed-1"
    assert result["videos"][1]["note"] == "Preserve editorial note"
    assert result["videos"][2]["note"] == "Local unpublished addition"
    assert local == before
    assert live == published_before


@pytest.mark.parametrize("failure", ["wrong_source", "wrong_foundup", "duplicate", "invalid_id"])
def test_live_seed_refuses_ambiguous_published_identity(failure):
    from scripts.refresh_mall_catalog import seed_hpc_from_live

    lane = {"foundup_id": "hpc", "source_id": APPROVED_CHANNEL_ID, "videos": [{"video_id": OLD}]}
    if failure == "wrong_source":
        lane["source_id"] = "UC-other"
    elif failure == "wrong_foundup":
        lane["foundup_id"] = "other"
    elif failure == "duplicate":
        lane["videos"] *= 2
    else:
        lane["videos"][0]["video_id"] = "invalid"
    with pytest.raises(ValueError):
        seed_hpc_from_live(config(), {"hpc": {"lane": lane}})


@pytest.fixture
def scoped_script_files(tmp_path, monkeypatch):
    """Use the real projection owner with all writable files in a temporary root."""
    from scripts import refresh_mall_catalog as script
    from modules.communication.youtube_channel_pull.src import scoped_refresh

    original_root = script.REPO_ROOT
    local_config = json.loads((original_root / script.SCOPED_PROJECTIONS[0]).read_text(encoding="utf-8"))
    local_config["videos"] = config()["videos"]
    catalog_bytes = script.CATALOG_PATH.read_bytes()
    public = json.loads(script.SCOPED_CATALOG_PATH.read_text(encoding="utf-8"))
    public["independent-other"] = {"lane": {"videos": [{"video_id": OTHER}], "editorial": "retain exactly"}}
    projection_path = tmp_path / script.SCOPED_PROJECTIONS[0]
    catalog_path = tmp_path / "public/member/mall-video-catalog.json"
    public_path = catalog_path.with_name("mall-public-video-catalog.json")
    receipt_path = tmp_path / "docs/audits/pfmall_youtube_ingest/hpc_refresh.json"
    for path in (projection_path, catalog_path, receipt_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    projection_path.write_text(json.dumps(local_config), encoding="utf-8")
    catalog_path.write_bytes(catalog_bytes)
    public_path.write_text(json.dumps(public), encoding="utf-8")
    monkeypatch.setattr(script, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(script, "CATALOG_PATH", catalog_path)
    monkeypatch.setattr(script, "SCOPED_CATALOG_PATH", public_path)
    monkeypatch.setattr(script, "HPC_REFRESH_RECEIPT", receipt_path)
    original_refresh = scoped_refresh.refresh_scoped_projection
    original_freshness = scoped_refresh.ensure_refresh_fresh

    def fixed_clock_refresh(*args, **kwargs):
        return original_refresh(*args, **{**kwargs, "now": NOW})

    def fixed_clock_freshness(receipt, **kwargs):
        return original_freshness(receipt, now=NOW)

    monkeypatch.setattr(scoped_refresh, "refresh_scoped_projection", fixed_clock_refresh)
    monkeypatch.setattr(scoped_refresh, "ensure_refresh_fresh", fixed_clock_freshness)
    return script, projection_path, catalog_path, public_path, receipt_path, public


def test_normal_refresh_entry_preserves_other_collections_and_general_mall(scoped_script_files):
    import hashlib

    script, projection_path, catalog_path, public_path, receipt_path, public_before = scoped_script_files
    general_before = catalog_path.read_bytes()
    receipt = script.refresh_hpc_collection(YouTube(), apply=True)
    updated_public = json.loads(public_path.read_text(encoding="utf-8"))
    updated_config = json.loads(projection_path.read_text(encoding="utf-8"))
    assert catalog_path.read_bytes() == general_before
    assert updated_public["independent-other"] == public_before["independent-other"]
    assert [video["video_id"] for video in updated_public["hpc"]["lane"]["videos"]] == [OLD, TARGET]
    assert updated_public["hpc"]["lane"]["videos"][-1]["duration_seconds"] == 5990
    assert len({video["video_id"] for video in updated_config["videos"]}) == len(updated_config["videos"])
    assert receipt["catalog_sha256"] == hashlib.sha256(public_path.read_bytes()).hexdigest()
    assert receipt["projection_sha256"] == hashlib.sha256(projection_path.read_bytes()).hexdigest()
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt


def test_normal_refresh_dry_run_and_source_failure_do_not_write(scoped_script_files):
    script, projection_path, catalog_path, public_path, receipt_path, _ = scoped_script_files
    paths = (projection_path, catalog_path, public_path)
    before = {path: path.read_bytes() for path in paths}
    script.refresh_hpc_collection(YouTube(), apply=False)
    assert {path: path.read_bytes() for path in paths} == before
    assert not receipt_path.exists()
    service = YouTube(videos={TARGET: metadata(snippet={"channelId": "UC-unapproved"}), OLD: metadata(OLD)})
    with pytest.raises(ScopedRefreshError):
        script.refresh_hpc_collection(service, apply=True)
    assert {path: path.read_bytes() for path in paths} == before
    assert not receipt_path.exists()


def test_scoped_output_replacement_failure_restores_original_files(tmp_path, monkeypatch):
    from scripts.refresh_mall_catalog import write_scoped_outputs

    first, second = tmp_path / "curation.json", tmp_path / "public.json"
    first.write_bytes(b"original curation")
    second.write_bytes(b"original public")
    replace = Path.replace

    def fail_second(temporary, destination):
        if destination == second:
            raise OSError("simulated second replacement failure")
        return replace(temporary, destination)

    monkeypatch.setattr(Path, "replace", fail_second)
    with pytest.raises(OSError):
        write_scoped_outputs({first: b"new curation", second: b"new public"})
    assert first.read_bytes() == b"original curation"
    assert second.read_bytes() == b"original public"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["curation.json", "public.json"]
