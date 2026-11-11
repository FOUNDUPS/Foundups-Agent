"""Offline transport and pipeline tests; no live model-quality claim."""
import base64
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

path = Path(__file__).resolve().parents[1] / "src/openrouter_storyboard.py"
spec = importlib.util.spec_from_file_location("openrouter_storyboard_test", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=")


def setup(tmp_path):
    ref = tmp_path / "character.png"
    ref.write_bytes(PNG)
    config = SimpleNamespace(name="openrouter", base_url=m.BASE_URL, api_key="test-credential")
    transport = Mock(return_value={"data": [{"b64_json": base64.b64encode(PNG).decode(), "media_type": "image/png"}]})
    authorize = Mock(return_value=True)
    image = m.OpenRouterStoryboard(config, references=[{"path": ref,
        "sha256": hashlib.sha256(PNG).hexdigest(), "rights_evidence": "Owned test fixture"}],
        authorize=authorize, transport=transport)
    return image, transport, authorize, {"shot_id": "shot_01", "prompt": "Six sleeping shrews"}, {"output_dir": str(tmp_path)}


def test_reference_request_and_output(tmp_path):
    image, transport, authorize, shot, context = setup(tmp_path)
    result = image(shot, context)
    url, key, payload = transport.call_args.args
    assert url == m.BASE_URL + "/images"
    assert payload["model"] == m.MODEL and payload["n"] == 1
    assert payload["provider"] == {"allow_fallbacks": False}
    assert payload["input_references"][0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert Path(result["path"]).read_bytes() == PNG
    assert result["status"] == "generated_unreviewed"
    assert "test-credential" not in Path(result["intent_path"]).read_text()
    assert authorize.call_args.args[0] == "storyboard_image"
    with pytest.raises(FileExistsError):
        image(shot, context)
    assert transport.call_count == 1


@pytest.mark.parametrize("failure", ["denied", "changed_reference", "bad_id", "missing_dir"])
def test_preflight_no_egress(tmp_path, failure):
    image, transport, authorize, shot, context = setup(tmp_path)
    if failure == "denied": authorize.return_value = False
    if failure == "changed_reference": (tmp_path / "character.png").write_bytes(b"changed")
    if failure == "bad_id": shot["shot_id"] = "../escape"
    if failure == "missing_dir": context["output_dir"] = str(tmp_path / "absent")
    with pytest.raises((ValueError, PermissionError, FileNotFoundError)):
        image(shot, context)
    transport.assert_not_called()


@pytest.mark.parametrize("result", [{}, {"data": []}, {"data": [{"url": "https://example.com/image.png"}]},
    {"data": [{"b64_json": "bad!"}]}, {"data": [{"b64_json": base64.b64encode(b"not image").decode()}]},
    {"data": [{"b64_json": base64.b64encode(PNG).decode(), "media_type": "image/jpeg"}]}])
def test_bad_response_retains_intent_and_blocks_replay(tmp_path, result):
    image, transport, _, shot, context = setup(tmp_path)
    transport.return_value = result
    with pytest.raises(ValueError): image(shot, context)
    with pytest.raises(FileExistsError): image(shot, context)
    assert transport.call_count == 1


def test_transport_failure_redacted_and_no_retry(tmp_path):
    image, transport, _, shot, context = setup(tmp_path)
    transport.side_effect = RuntimeError("test-credential provider payload")
    with pytest.raises(RuntimeError) as error: image(shot, context)
    assert "test-credential" not in str(error.value)
    with pytest.raises(FileExistsError): image(shot, context)
    assert transport.call_count == 1


@pytest.mark.parametrize("verdict", [False, None, "true"])
def test_review_failure_blocks_video(tmp_path, verdict):
    image, _, _, shot, context = setup(tmp_path)
    video = Mock()
    adapter = m.StoryboardVideoShot(image, review_frame=Mock(return_value=verdict), generate_video=video)
    with pytest.raises(ValueError): adapter(shot, context)
    video.assert_not_called()


def test_video_receives_actual_reviewed_frame(tmp_path):
    image, _, _, shot, context = setup(tmp_path)
    video = Mock(return_value={"path": "movie.mp4", "rights_evidence": "test"})
    adapter = m.StoryboardVideoShot(image, review_frame=Mock(return_value=True), generate_video=video)
    assert adapter(shot, context)["path"] == "movie.mp4"
    assert Path(video.call_args.args[0]["start_frame"]["path"]).read_bytes() == PNG
    assert "start_frame" not in shot


def test_review_mutation_blocks_video(tmp_path):
    image, _, _, shot, context = setup(tmp_path)
    def review(frame, *_):
        Path(frame["path"]).write_bytes(b"changed")
        return True
    video = Mock()
    with pytest.raises(ValueError, match="changed"):
        m.StoryboardVideoShot(image, review_frame=review, generate_video=video)(shot, context)
    video.assert_not_called()
