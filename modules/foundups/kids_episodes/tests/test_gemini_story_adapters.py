"""Offline provider-contract tests; no actual semantic review or paid calls."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

PATH = Path(__file__).resolve().parents[1] / "src/gemini_story_adapters.py"
spec = importlib.util.spec_from_file_location("gemini_story_adapters_test", PATH)
adapters = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapters)


def client(result):
    model = Mock()
    model.models.generate_content.return_value = SimpleNamespace(text=json.dumps(result))
    return model


def review_fixture(tmp_path):
    video = b"\x00\x00\x00\x18ftypmp42synthetic-test-fixture"
    path = tmp_path / "episode.mp4"
    path.write_bytes(video)
    context = {"artifact_sha256": hashlib.sha256(video).hexdigest(),
               "reviewer_id": "independent-reviewer", "producer_id": "producer",
               "bible": {"characters": "Original snail"}, "assets": [],
               "final_render_captions": [{"start": 0, "end": 3, "text": "Hello"}]}
    return video, {"video_path": str(path)}, {"learning_objective": "Count three"}, context


def valid_review():
    return {"checks": {key: True for key in adapters.CHECKS},
            "feedback": "At 0:03 the numeral matches; fixture response only."}


def test_planner_uses_explicit_model_and_structured_schema():
    api = client({"title": "Draft"})
    planner = adapters.GeminiStoryPlanner(api, model="configured-planner-model")
    request = {"raw_story": "Snail counts three leaves.", "supported_durations": [4, 6, 8]}
    assert planner(request) == {"title": "Draft"}
    args = api.models.generate_content.call_args.kwargs
    assert args["model"] == "configured-planner-model"
    assert args["config"]["response_mime_type"] == "application/json"
    schema = args["config"]["response_json_schema"]
    shot = schema["properties"]["episodes"]["items"]["properties"]["shots"]["items"]
    assert shot["properties"]["generation_seconds"]["enum"] == [4, 6, 8]
    assert request["raw_story"] in args["contents"][0]


@pytest.mark.parametrize("raw", ['{"title":NaN}', '{"title":"a","title":"b"}', '[]', '```json\n{}\n```'])
def test_planner_rejects_malformed_json(raw):
    api = client({})
    api.models.generate_content.return_value.text = raw
    planner = adapters.GeminiStoryPlanner(api, model="configured")
    with pytest.raises(ValueError):
        planner({"raw_story": "Story", "supported_durations": [6]})


@pytest.mark.parametrize("durations", [[], [True], [float("nan")], [float("inf")], [0], [121]])
def test_bad_generation_durations_rejected_before_spend(durations):
    api = Mock()
    planner = adapters.GeminiStoryPlanner(api, model="configured")
    with pytest.raises(ValueError):
        planner({"raw_story": "Story", "supported_durations": durations})
    api.models.generate_content.assert_not_called()


def test_reviewer_sends_actual_bytes_and_binds_result(tmp_path):
    video, rendered, episode, context = review_fixture(tmp_path)
    api, factory = client(valid_review()), Mock(return_value="SDK_VIDEO_PART")
    reviewer = adapters.GeminiEpisodeReviewer(api, model="configured-review-model",
        part_from_bytes=factory, reviewer_id="independent-reviewer")
    result = reviewer(rendered, episode, context)
    factory.assert_called_once_with(data=video, mime_type="video/mp4")
    args = api.models.generate_content.call_args.kwargs
    assert args["contents"][0] == "SDK_VIDEO_PART"
    assert "final_render_captions" in args["contents"][1]
    assert result["artifact_sha256"] == hashlib.sha256(video).hexdigest()
    assert result["reviewer_id"] == context["reviewer_id"]


@pytest.mark.parametrize("kind", ["missing", "string", "empty_feedback", "extra"])
def test_review_never_defaults_to_pass(tmp_path, kind):
    _, rendered, episode, context = review_fixture(tmp_path)
    result = valid_review()
    if kind == "missing":
        del result["checks"]["rights"]
    elif kind == "string":
        result["checks"]["education"] = "true"
    elif kind == "extra":
        result["checks"]["new"] = True
    else:
        result["feedback"] = " "
    reviewer = adapters.GeminiEpisodeReviewer(client(result), model="configured",
        part_from_bytes=Mock(), reviewer_id="independent-reviewer")
    with pytest.raises(ValueError):
        reviewer(rendered, episode, context)


def test_negative_review_stays_negative(tmp_path):
    _, rendered, episode, context = review_fixture(tmp_path)
    result = valid_review()
    result["checks"]["rights"] = False
    reviewer = adapters.GeminiEpisodeReviewer(client(result), model="configured",
        part_from_bytes=Mock(), reviewer_id="independent-reviewer")
    assert reviewer(rendered, episode, context)["checks"]["rights"] is False


@pytest.mark.parametrize("defect", ["changed_bytes", "same_actor", "wrong_actor", "oversized", "signature"])
def test_preflight_rejects_before_api(tmp_path, monkeypatch, defect):
    _, rendered, episode, context = review_fixture(tmp_path)
    if defect == "changed_bytes":
        context["artifact_sha256"] = "0" * 64
    elif defect == "same_actor":
        context["producer_id"] = context["reviewer_id"]
    elif defect == "wrong_actor":
        context["reviewer_id"] = "another-reviewer"
    elif defect == "oversized":
        monkeypatch.setattr(adapters, "MAX_VIDEO_BYTES", 8)
    else:
        Path(rendered["video_path"]).write_bytes(b"not a video")
    api = Mock()
    reviewer = adapters.GeminiEpisodeReviewer(api, model="configured",
        part_from_bytes=Mock(), reviewer_id="independent-reviewer")
    with pytest.raises(ValueError):
        reviewer(rendered, episode, context)
    api.models.generate_content.assert_not_called()


def test_provider_failure_propagates_without_retry(tmp_path):
    _, rendered, episode, context = review_fixture(tmp_path)
    api = Mock()
    api.models.generate_content.side_effect = RuntimeError("provider unavailable")
    reviewer = adapters.GeminiEpisodeReviewer(api, model="configured",
        part_from_bytes=Mock(), reviewer_id="independent-reviewer")
    with pytest.raises(RuntimeError):
        reviewer(rendered, episode, context)
    assert api.models.generate_content.call_count == 1
