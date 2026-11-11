"""Real local FFmpeg story assembly with explicitly synthetic provider/review seams.

No model, credentials, network, live admission, pedagogical approval or publishing
is exercised. The synthetic reviewer tests the callback contract, not education.
"""
import array
import hashlib
import importlib.util
from pathlib import Path
import shutil
import subprocess

import pytest


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[4]
STORY = _load("kids_story_real_render_test", ROOT / "modules/foundups/kids_episodes/src/story_pipeline.py")
ENGINE = _load("kids_engine_real_story_test", ROOT / "modules/communication/youtube_shorts/src/kids_episode.py")


def _ffmpeg(*args):
    return subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", *map(str, args)],
                          capture_output=True, check=True, timeout=60)


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_two_episode_story_real_render_assembly_and_reviewed_resume(tmp_path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg and ffprobe required for local render integration")
    fixture_dir = tmp_path / "synthetic fixtures"
    fixture_dir.mkdir()
    for color in ("red", "blue"):
        _ffmpeg("-f", "lavfi", "-i", f"color=c={color}:s=160x90:r=30:d=6",
                "-c:v", "libx264", "-threads", "1", fixture_dir / f"{color}.mp4")
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=15", fixture_dir / "music.wav")
    first_sentence, second_sentence = "Pip counts three seeds. ", "Pip plants the three seeds."
    raw_story = first_sentence + second_sentence
    draft = {"title": "Pip's seed story", "age_band": "3-5", "language": "en",
             "bible": {"characters": "Original bird Pip", "world": "A quiet garden",
                       "visual_style": "Synthetic solid-color integration fixtures"},
             "episodes": []}
    for index, (title, start, end, before, after) in enumerate([
            ("Count seeds", 0, len(first_sentence), "Seeds in a cup", "Three seeds counted"),
            ("Plant seeds", len(first_sentence), len(raw_story), "Three seeds counted", "Three seeds planted")]):
        draft["episodes"].append({"title": title, "source_start": start, "source_end": end,
            "learning_objective": "Count three seeds", "activity": "Count aloud to three",
            "start_state": before, "end_state": after,
            "shots": [{"prompt": f"Synthetic fixture shot {index}-{shot}",
                       "generation_seconds": 6, "edit_seconds": 5} for shot in range(3)],
            "captions": [{"start": 0, "end": 15, "text": f"{title}: one, two, three!"}]})
    plan = STORY.compile_plan(raw_story, draft, request_id="synthetic-render-integration")
    ids = [episode["episode_id"] for episode in plan["episodes"]]
    assert len(set(ids)) == 2
    assert plan["episodes"][1]["previous_episode_id"] == ids[0]
    assert plan["episodes"][0]["previous_episode_id"] is None
    assert all(shot["generation_seconds"] == 6 and shot["edit_seconds"] == 5
               for episode in plan["episodes"] for shot in episode["shots"])

    binding = hashlib.sha256(b"synthetic test binding; not authenticated live authority").hexdigest()
    maximum = {"generate_shot": 6, "produce_audio": 2, "render": 2,
               "review": 4, "assemble": 2, "review_story": 2}
    admitted = dict.fromkeys(maximum, 0)
    calls = dict.fromkeys(("shot", "audio", "render", "review", "assemble", "review_story"), 0)

    def authorize(stage, context):
        # This closure is the test's deliberately synthetic admission seam.
        assert stage in maximum and context["project_id"] == plan["project_id"]
        assert context["plan_digest"] == plan["plan_digest"]
        if stage != "assemble":
            assert context["execution_binding_digest"] == binding
        admitted[stage] += 1
        return admitted[stage] <= maximum[stage]

    def generate_shot(shot, context):
        calls["shot"] += 1
        assert shot["generation_seconds"] == 6
        color = "red" if context["episode_id"] == ids[0] else "blue"
        output = Path(context["output_dir"]) / f"{shot['shot_id']}.mp4"
        shutil.copyfile(fixture_dir / f"{color}.mp4", output)
        return {"path": str(output), "rights_evidence": "Synthetic FFmpeg color fixture, no provider call"}

    def produce_audio(episode, context):
        calls["audio"] += 1
        output = Path(context["output_dir"]) / "music.wav"
        shutil.copyfile(fixture_dir / "music.wav", output)
        return {"music": {"path": str(output), "rights_evidence": "Synthetic FFmpeg sine fixture"},
                "captions": episode["captions"]}

    def render(spec, output_path, *, base_dir):
        calls["render"] += 1
        return ENGINE.render_episode(spec, output_path, base_dir=base_dir)

    def review(result, episode, context):
        calls["review"] += 1
        assert _hash(result["video_path"]) == context["artifact_sha256"]
        assert len(context["assets"]) == 4
        assert context["final_render_captions"] == episode["captions"]
        subtitle = Path(result["captions_path"]).read_text(encoding="utf-8")
        assert "00:00:00,000 --> 00:00:15,000" in subtitle
        assert episode["captions"][0]["text"] in subtitle
        return {"artifact_sha256": context["artifact_sha256"], "reviewer_id": "synthetic-independent-reviewer",
                "checks": {check: True for check in STORY.CHECKS},
                "feedback": "Synthetic six-check contract response; no pedagogical review claimed"}

    def assemble(paths, output_path):
        calls["assemble"] += 1
        assert len(paths) == 2 and all(eid in path for eid, path in zip(ids, paths))
        return ENGINE.assemble_episodes(paths, output_path)

    def review_story(artifact, compiled, context):
        calls["review_story"] += 1
        assert compiled == plan and _hash(artifact["path"]) == context["artifact_sha256"]
        return {"artifact_sha256": context["artifact_sha256"], "reviewer_id": "synthetic-independent-reviewer",
                "checks": {check: True for check in (*STORY.CHECKS, "joins")},
                "feedback": "Synthetic seven-check response including joins; no live approval claimed"}

    kwargs = dict(authorize=authorize, generate_shot=generate_shot, produce_audio=produce_audio,
                  render_episode=render, review_episode=review, assemble_story=assemble,
                  review_story=review_story, producer_id="synthetic-producer",
                  reviewer_id="synthetic-independent-reviewer", execution_binding_digest=binding)
    result = STORY.run_story(plan, tmp_path, **kwargs)
    assert result["status"] == "story_reviewed"
    assert [episode["episode_id"] for episode in result["episodes"]] == ids
    output = Path(result["story_video"]["path"])
    probe = ENGINE._probe(output)
    video = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")
    assert video["nb_frames"] == "900" and float(video["duration"]) == 30
    assert float(audio["duration"]) == pytest.approx(30, abs=0.1)
    # Confirm episode order survives assembly; sample above the caption area.
    for seconds, channel in ((1, 0), (29, 2)):
        pixel = _ffmpeg("-ss", seconds, "-i", output, "-frames:v", 1,
                        "-vf", "crop=4:4:10:10", "-f", "rawvideo", "-pix_fmt", "rgb24", "-").stdout
        assert pixel and pixel[channel] > 200
    samples = array.array("h", _ffmpeg("-ss", 14.95, "-i", output, "-t", 0.1,
                                       "-vn", "-f", "s16le", "-ac", 1, "-").stdout)
    assert samples and sum(float(sample) ** 2 for sample in samples) / len(samples) > 1000
    assert calls == {"shot": 6, "audio": 2, "render": 2, "review": 2, "assemble": 1, "review_story": 1}
    original_digest = _hash(output)
    resumed = STORY.run_story(plan, tmp_path, **kwargs)
    assert resumed["status"] == "story_reviewed" and _hash(output) == original_digest
    assert calls == {"shot": 6, "audio": 2, "render": 2, "review": 4, "assemble": 1, "review_story": 2}
    assert admitted == maximum
    assert not list(tmp_path.glob("*.lock"))
