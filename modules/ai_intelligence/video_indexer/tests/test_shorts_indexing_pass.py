"""
INDEXER_SHORTS_PASS_PHASE1 - mock-only tests for the Shorts indexing pass.

GOAL: the video indexer must index Shorts as well as long-form. On origin/main
``index_channel_videos`` enumerates ONLY ``videos/upload`` and SKIPS short rows
(``if "short" in row_text: continue``) -- so shorts are NEVER indexed. These
tests assert that:

  1. the shorts pass (content_type="short") navigates ``videos/short``,
     KEEPS short rows, and writes artifacts with metadata.content_type == "short";
  2. the upload pass still indexes long-form and SKIPS short rows;
  3. a ["short"] channel (foundups) runs ONLY the shorts pass;
  4. a ["short","upload"] channel (move2japan) runs BOTH passes.

NON-VACUITY: tests 1 and 4 FAIL on current (pre-change) code because no short
artifact is ever produced. NO live browser / network: a FakeDriver returns
mocked rows by URL and ask_about_video / audio-observe are monkeypatched.

WSP 5 (coverage), WSP 50 (verify), WSP 84 (reuse existing mock patterns).
"""

import json
from pathlib import Path

import pytest

from modules.ai_intelligence.video_indexer.src import studio_ask_indexer
from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import (
    AskResult,
    StudioAskIndexer,
)


# ---------------------------------------------------------------------------
# Fake Selenium driver (NO live browser): rows are chosen by the navigated URL.
# ---------------------------------------------------------------------------

class _FakeLink:
    def __init__(self, href):
        self._href = href

    def get_attribute(self, _name):
        return self._href


class _FakeRow:
    """A Studio video row. ``text`` drives the LIVE/Shorts detection."""

    def __init__(self, video_id, text):
        self._link = _FakeLink(f"https://studio.youtube.com/video/{video_id}/edit")
        self.text = text

    def find_element(self, _by, _selector):
        return self._link


class _FakeDriver:
    """Returns long-form rows for /videos/upload and short rows for /videos/short."""

    def __init__(self):
        self.current_url = ""
        self.navigated = []

    def get(self, url):
        self.current_url = url
        self.navigated.append(url)

    def execute_script(self, _script, *args):
        # No sort button in the fake DOM -> indexer keeps default order.
        return "no_sort_button"

    def find_elements(self, _by, _selector):
        if self.current_url.endswith("/videos/short"):
            # Shorts list: every row is a Short.
            return [
                _FakeRow("short001", "My Short #shorts"),
                _FakeRow("short002", "Another short video"),
            ]
        # Upload (long-form) list: one long-form row plus a stray Short row.
        return [
            _FakeRow("long001", "Full length stream live recording"),
            _FakeRow("shortX", "leftover short #short"),
        ]


def _make_indexer(monkeypatch, tmp_path):
    """Build an indexer wired to a temp INDEX_ROOT with fast, mocked I/O."""
    index_root = tmp_path / "video_index"
    monkeypatch.setattr(studio_ask_indexer, "INDEX_ROOT", index_root)
    # Never touch real audio/network.
    monkeypatch.setattr(studio_ask_indexer, "_observe_audio_label", lambda vid: None)

    indexer = StudioAskIndexer(driver=_FakeDriver(), max_videos_per_cycle=10)

    # No real human delays.
    async def _no_delay(*_a, **_k):
        return None

    monkeypatch.setattr(indexer, "_human_delay", _no_delay)

    # ask_about_video returns a successful AskResult for any id (no browser).
    async def _fake_ask(video_id, *_a, **_k):
        return AskResult(
            video_id=video_id,
            title=f"Title {video_id}",
            response_text="Topics: a, b",
            topics=["a", "b"],
            timestamps=[{"time": "0:05", "topic": "T", "summary": "S"}],
            success=True,
        )

    monkeypatch.setattr(indexer, "ask_about_video", _fake_ask)
    return indexer, index_root


def _load_artifacts(channel_dir: Path):
    """Return {video_id: parsed_json} for all artifacts under a channel dir."""
    if not channel_dir.exists():
        return {}
    out = {}
    for p in channel_dir.glob("*.json"):
        out[p.stem] = json.loads(p.read_text(encoding="utf-8"))
    return out


# ---------------------------------------------------------------------------
# 1. Shorts pass indexes shorts with content_type == "short".
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_shorts_pass_indexes_short_rows(monkeypatch, tmp_path):
    indexer, index_root = _make_indexer(monkeypatch, tmp_path)

    result = await indexer.index_channel_videos(
        "UCSNTUXjAgpd4sgWYP0xoJgw",  # foundups
        content_type="short",
    )

    # Navigated the SHORTS list, not the upload list.
    assert any(u.endswith("/videos/short") for u in indexer.driver.navigated)
    assert result["content_type"] == "short"
    assert result["indexed"] == 2

    arts = _load_artifacts(index_root / "foundups")
    assert set(arts) == {"short001", "short002"}, "shorts must be indexed"
    for vid, data in arts.items():
        # NON-VACUITY: the gap on origin/main is that shorts are never indexed,
        # so this artifact + label cannot exist there.
        assert data["metadata"]["content_type"] == "short", vid


# ---------------------------------------------------------------------------
# 2. Upload pass still indexes long-form and SKIPS shorts.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_pass_skips_shorts(monkeypatch, tmp_path):
    indexer, index_root = _make_indexer(monkeypatch, tmp_path)

    result = await indexer.index_channel_videos(
        "UC-LSSlOZwpGIRIYihaz8zCw",  # move2japan
        content_type="upload",
    )

    assert any(u.endswith("/videos/upload") for u in indexer.driver.navigated)
    assert result["content_type"] == "upload"

    arts = _load_artifacts(index_root / "move2japan")
    # The stray short row ("shortX") on the upload list is skipped.
    assert "shortX" not in arts
    assert "long001" in arts
    assert arts["long001"]["metadata"]["content_type"] == "upload"


# ---------------------------------------------------------------------------
# 3 & 4. Per-channel content_types decide which passes run.
# ---------------------------------------------------------------------------

def test_resolve_passes_short_only_channel():
    # foundups registry content_types == ["short"] -> shorts pass only.
    passes = studio_ask_indexer._resolve_index_passes("UCSNTUXjAgpd4sgWYP0xoJgw")
    assert passes == ["short"]


def test_resolve_passes_both_channel():
    # move2japan registry content_types == ["short","upload"] -> both passes,
    # normalized to upload-then-short.
    passes = studio_ask_indexer._resolve_index_passes("UC-LSSlOZwpGIRIYihaz8zCw")
    assert passes == ["upload", "short"]


def test_resolve_passes_unknown_channel_defaults_both():
    passes = studio_ask_indexer._resolve_index_passes("UC_does_not_exist")
    assert passes == ["upload", "short"]


@pytest.mark.asyncio
async def test_cycle_runs_passes_per_content_types(monkeypatch, tmp_path):
    """run_video_indexing_cycle: ["short"] chan -> shorts only; both -> both."""
    index_root = tmp_path / "video_index"
    monkeypatch.setattr(studio_ask_indexer, "INDEX_ROOT", index_root)
    monkeypatch.setenv("YT_VIDEO_INDEXING_ENABLED", "true")
    # No STOP file, no Gemini analysis pass.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(studio_ask_indexer, "_stop_active", lambda: False)
    monkeypatch.setattr(studio_ask_indexer, "_consume_reindex_signal", lambda: False)
    monkeypatch.setattr(studio_ask_indexer, "_count_indexed_by_channel", lambda root: {})

    # Record every (channel_id, content_type) pass that actually runs.
    calls = []

    async def _fake_index(self, channel_id, force_reindex=False, content_type="upload"):
        calls.append((channel_id, content_type))
        return {
            "channel_id": channel_id,
            "content_type": content_type,
            "indexed": 1,
            "skipped": 0,
            "failed": 0,
            "videos": [f"{content_type}_vid"],
        }

    monkeypatch.setattr(StudioAskIndexer, "index_channel_videos", _fake_index)

    foundups = "UCSNTUXjAgpd4sgWYP0xoJgw"   # ["short"]
    move2japan = "UC-LSSlOZwpGIRIYihaz8zCw"  # ["short","upload"]

    result = await studio_ask_indexer.run_video_indexing_cycle(
        driver=_FakeDriver(),
        channels=[foundups, move2japan],
        max_videos_per_channel=5,
    )

    # foundups: shorts pass ONLY.
    assert (foundups, "short") in calls
    assert (foundups, "upload") not in calls
    # move2japan: BOTH passes.
    assert (move2japan, "upload") in calls
    assert (move2japan, "short") in calls

    # Merged per-channel summary keeps a per-pass breakdown.
    assert set(result["channels"][foundups]["passes"]) == {"short"}
    assert set(result["channels"][move2japan]["passes"]) == {"upload", "short"}


@pytest.mark.asyncio
async def test_cycle_one_pass_error_does_not_abort_other(monkeypatch, tmp_path):
    """A failing pass is isolated; the sibling pass still indexes."""
    monkeypatch.setattr(studio_ask_indexer, "INDEX_ROOT", tmp_path / "video_index")
    monkeypatch.setenv("YT_VIDEO_INDEXING_ENABLED", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(studio_ask_indexer, "_stop_active", lambda: False)
    monkeypatch.setattr(studio_ask_indexer, "_consume_reindex_signal", lambda: False)
    monkeypatch.setattr(studio_ask_indexer, "_count_indexed_by_channel", lambda root: {})

    async def _fake_index(self, channel_id, force_reindex=False, content_type="upload"):
        if content_type == "upload":
            raise RuntimeError("upload pass blew up")
        return {
            "channel_id": channel_id,
            "content_type": content_type,
            "indexed": 3,
            "skipped": 0,
            "failed": 0,
            "videos": ["s1", "s2", "s3"],
        }

    monkeypatch.setattr(StudioAskIndexer, "index_channel_videos", _fake_index)

    move2japan = "UC-LSSlOZwpGIRIYihaz8zCw"  # both passes
    result = await studio_ask_indexer.run_video_indexing_cycle(
        driver=_FakeDriver(),
        channels=[move2japan],
        max_videos_per_channel=5,
    )

    ch = result["channels"][move2japan]
    # Shorts pass still produced its 3 videos despite the upload pass raising.
    assert ch["indexed"] == 3
    assert "upload" in ch["pass_errors"]
