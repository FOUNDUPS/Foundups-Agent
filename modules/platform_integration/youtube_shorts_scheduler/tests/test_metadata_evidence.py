"""Offline evidence, preservation and learning-boundary regressions."""
import copy
import json
import sys
import types
from unittest.mock import Mock

import pytest

from modules.platform_integration.youtube_shorts_scheduler.src.metadata_evidence import validated_video_evidence
from modules.platform_integration.youtube_shorts_scheduler.src.index_weave import build_index_metadata_context
from modules.platform_integration.youtube_shorts_scheduler.src.content_generator import generate_clickbait_title_from_index
from modules.platform_integration.youtube_shorts_scheduler.src.schedule_dba import record_schedule_outcome
from modules.platform_integration.youtube_shorts_scheduler.src.scheduler import YouTubeShortsScheduler
from modules.platform_integration.youtube_shorts_scheduler.skillz.ffcpln_title_enhance.executor import (
    FFCPLNTitleEnhanceSkill, SkillContext, enhance_title_with_skill, enhance_description_with_skill,
)


def artifact():
    return {"video_id": "clip", "indexed_at": "2026-10-25T00:00:00Z",
            "transcript_source": "gemini_summary", "audio": {"transcript_summary": "College football in Fukui."},
            "visual": {}, "metadata": {"retrieval_eligible": True,
            "topics": ["FFCPLN"], "summary": "Unrelated legacy template",
            "provenance": {"provider": "youtube_studio_ask", "identity_verified": True,
                           "requested_video_id": "clip", "response_video_id": "clip", "response_sha256": "digest"}}}


@pytest.mark.parametrize("mutation", [
    lambda a: a.update(video_id="other"),
    lambda a: a.update(transcript_source="scheduler_stub"),
    lambda a: a["metadata"]["provenance"].update(response_video_id="other"),
    lambda a: a["metadata"]["provenance"].update(identity_verified=False),
    lambda a: a.update(audio=[]),
    lambda a: a["audio"].update(transcript_summary=""),
    lambda a: a["metadata"].update(retrieval_eligible=False),
])
def test_rejects_unusable_evidence(mutation):
    a = artifact()
    mutation(a)
    assert validated_video_evidence(a, "clip") is None


@pytest.mark.parametrize("source,key", [("youtube", "youtube_transcript"), ("whisper", "whisper_transcript"), ("stacked", "youtube_transcript")])
def test_canonical_transcript_routes(source, key):
    a = artifact()
    a.update(transcript_source=source)
    a[key] = [{"start": 0, "end": 4, "text": "Football in Fukui"}]
    evidence = validated_video_evidence(a, "clip")
    assert evidence["modality"] == "speech_transcript"
    assert evidence["coverage"] == "provided_segments_only"
    a[key][0]["end"] = -1
    assert validated_video_evidence(a, "clip") is None


def test_visual_summary_is_not_speech():
    a = artifact()
    a["audio"] = {}
    a["visual"] = {"description": "A football field."}
    assert validated_video_evidence(a, "clip")["modality"] == "visual_summary"


def test_stub_and_duration_cannot_make_music():
    context = SkillContext("Japanese football", "Existing body", video_duration=50)
    skill = FFCPLNTitleEnhanceSkill()
    assert skill._analyze_content(context) == "unknown"
    result = skill.execute(context)
    assert (result.enhanced_title, result.enhanced_description) == ("Japanese football", "Existing body")
    assert enhance_title_with_skill("Keep") == "Keep"
    assert enhance_description_with_skill("Body") == "Body"


def test_skill_evidence_and_preserve_mode():
    context = SkillContext("Old", "Old body", video_id="clip", index_json=artifact())
    result = FFCPLNTitleEnhanceSkill().execute(context)
    assert result.enhanced_title == "College football in Fukui."
    assert "FFCPLN" not in result.enhanced_description
    assert "M2M_CONTEXT" in result.enhanced_description
    assert len(result.enhanced_description) <= 5000
    assert result.confidence == 0  # No invented performance confidence.
    context.preserve_metadata = True
    assert FFCPLNTitleEnhanceSkill().execute(context).enhanced_description == "Old body"


def test_builder_uses_content_and_is_idempotent(tmp_path):
    folder = tmp_path / "channel"
    folder.mkdir()
    (folder / "clip.json").write_text(json.dumps(artifact()))
    kw = dict(channel_key="channel", video_id="clip", original_title="Inherited music title",
              inform_title=True, base_dir=tmp_path)
    first = build_index_metadata_context(base_description="Existing body", **kw)
    assert first.new_title == "College football in Fukui."
    assert "FFCPLN" not in first.new_description
    second = build_index_metadata_context(base_description=first.new_description, **kw)
    assert second.new_description == first.new_description
    assert build_index_metadata_context(base_description="x" * 5000, **kw) is None
    bad = artifact()
    bad["video_id"] = "other"
    (folder / "clip.json").write_text(json.dumps(bad))
    assert build_index_metadata_context(base_description="Existing body", **kw) is None


@pytest.mark.asyncio
async def test_scheduler_missing_evidence_never_edits(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_INDEXER_ARTIFACT_PATH", str(tmp_path))
    scheduler = object.__new__(YouTubeShortsScheduler)
    scheduler.channel_key = "move2japan"
    scheduler.dom = Mock()
    scheduler.dom.get_current_description.return_value = "Existing body"
    assert await scheduler._update_video_metadata(video_id="clip", original_title="Football", date_str="date", time_str="time")
    scheduler.dom.edit_title.assert_not_called()
    scheduler.dom.edit_description.assert_not_called()


@pytest.mark.parametrize("verified,wrong_id", [(False, False), (True, False), (True, True)])
def test_learning_requires_matched_readback(monkeypatch, verified, wrong_id):
    stored = []
    fake = types.ModuleType("modules.infrastructure.wre_core.src.pattern_memory")
    fake.PatternMemory = lambda **kw: types.SimpleNamespace(store_outcome=stored.append)
    fake.SkillOutcome = lambda **kw: types.SimpleNamespace(**kw)
    monkeypatch.setitem(sys.modules, fake.__name__, fake)
    details = {"requested_timezone": "America/New_York", "readback": {"independent": True, "channel_id": "channel", "video_id": "other" if wrong_id else "clip",
               "date_str": "date", "time_str": "time", "timezone": "America/New_York", "visibility": "scheduled"}} if verified else {}
    assert record_schedule_outcome(channel_id="channel", video_id="clip", date_str="date", time_str="time", mode="test", success=True, details=details)
    assert stored[0].success is (verified and not wrong_id)
    assert stored[0].outcome_quality == (1.0 if verified and not wrong_id else 0.0)
    assert json.loads(stored[0].output_result)["performance_measured"] is False


@pytest.mark.parametrize("field,value", [("date_str", "wrong"), ("time_str", "wrong"), ("timezone", "America/Los_Angeles")])
def test_learning_rejects_wrong_slot(monkeypatch, field, value):
    stored = []
    fake = types.ModuleType("modules.infrastructure.wre_core.src.pattern_memory")
    fake.PatternMemory = lambda **kw: types.SimpleNamespace(store_outcome=stored.append)
    fake.SkillOutcome = lambda **kw: types.SimpleNamespace(**kw)
    monkeypatch.setitem(sys.modules, fake.__name__, fake)
    readback = {"independent": True, "channel_id": "channel", "video_id": "clip", "date_str": "date",
                "time_str": "time", "timezone": "America/New_York", "visibility": "scheduled"}
    readback[field] = value
    record_schedule_outcome(channel_id="channel", video_id="clip", date_str="date", time_str="time",
                            mode="test", success=True, details={"requested_timezone": "America/New_York", "readback": readback})
    assert stored[0].success is False


def test_failed_analyzer_and_malformed_stt():
    a = artifact()
    a["success"] = False
    assert validated_video_evidence(a, "clip") is None
    a = artifact()
    a.update(transcript_source="whisper", audio="broken")
    assert validated_video_evidence(a, "clip") is None


def test_description_opt_out_is_byte_preserving(tmp_path):
    (tmp_path / "channel").mkdir()
    (tmp_path / "channel" / "clip.json").write_text(json.dumps(artifact()))
    original = "Keep this exact text.\n\n"
    ctx = build_index_metadata_context(channel_key="channel", video_id="clip", original_title="Keep",
                                      base_description=original, enhance_description=False, base_dir=tmp_path)
    assert ctx.new_description == original
