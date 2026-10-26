"""Offline contract and real FFmpeg render checks; no provider credentials."""
import importlib.util
from pathlib import Path
import shutil
import subprocess

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "kids_episode.py"
loader = importlib.util.spec_from_file_location("kids_episode_local_test", MODULE_PATH)
engine = importlib.util.module_from_spec(loader)
loader.loader.exec_module(engine)


def episode():
    return {"schema_version": 1, "title": "Clap and count", "learning_objective": "Count to three",
            "activity": "Clap three times", "age_band": "3-5", "language": "en",
            "duration_seconds": 15, "preset": "draft", "orientation": "landscape",
            "clips": [{"path": "clip.mp4", "start": 0, "duration": 15}],
            "music": {"path": "music.wav", "rights_evidence": "Original test tone"},
            "captions": [{"start": 0, "end": 5, "text": "One, two, three!"},
                         {"start": 5, "end": 15, "text": "Clap with me!"}]}


def test_validate_copy_and_srt():
    original = episode()
    result = engine.validate_episode(original)
    assert result == original and result is not original
    assert "00:00:05,000 --> 00:00:15,000\nClap with me!" in engine.captions_srt(result["captions"])


@pytest.mark.parametrize("field,value", [("duration_seconds", 14), ("duration_seconds", float("nan")),
                                         ("duration_seconds", True), ("preset", "high"),
                                         ("orientation", "square"), ("preset", []), ("schema_version", True),
                                         ("activity", ""), ("captions", [])])
def test_bad_contract(field, value):
    spec = episode()
    spec[field] = value
    with pytest.raises(ValueError):
        engine.validate_episode(spec)


@pytest.mark.parametrize("start,end,text", [(6, 4, "wrong"), (0, 16, "long"),
                                           (0, float("inf"), "inf"), (0, 2, r"{\pos(0,0)}"),
                                           (0, 2, "<b>tag</b>"), (0, 2, "newline\ntext"),
                                           (0, 0.00001, "too brief")])
def test_bad_caption(start, end, text):
    spec = episode()
    spec["captions"] = [{"start": start, "end": end, "text": text}]
    with pytest.raises(ValueError):
        engine.validate_episode(spec)


def test_overlap_and_short_timeline():
    spec = episode()
    spec["captions"][1]["start"] = 4
    with pytest.raises(ValueError, match="non-overlapping"):
        engine.validate_episode(spec)
    spec = episode()
    spec["clips"][0]["duration"] = 8
    with pytest.raises(ValueError, match="total"):
        engine.validate_episode(spec)


def test_rights_required():
    spec = episode()
    del spec["music"]["rights_evidence"]
    with pytest.raises(ValueError, match="rights_evidence"):
        engine.validate_episode(spec)


def test_existing_output_preserved(tmp_path):
    target = tmp_path / "existing.mp4"
    target.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        engine.render_episode(episode(), target)
    assert target.read_bytes() == b"keep"


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg unavailable")
    root = tmp_path_factory.mktemp("kids media ' quotes")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "color=c=blue:s=160x90:r=30:d=16", "-c:v", "libx264", "-threads", "1",
                    str(root / "clip.mp4")], check=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=16", str(root / "music.wav")], check=True)
    return root


@pytest.mark.parametrize("orientation,preset", [("landscape", "draft"), ("portrait", "draft"), ("landscape", "final")])
def test_real_render(media, orientation, preset):
    spec = episode()
    spec["orientation"] = orientation
    spec["preset"] = preset
    spec["clips"] = [{"path": "clip.mp4", "start": 0, "duration": 8},
                     {"path": "clip.mp4", "start": 2, "duration": 7}]
    if orientation == "portrait":
        spec["voice"] = {"path": "music.wav"}
    output = media / f"{orientation}-{preset}.mp4"
    result = engine.render_episode(spec, output, base_dir=media)
    assert abs(result["duration_seconds"] - 15) <= 0.1
    probe = engine._probe(output)
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    dimensions = (1920, 1080) if preset == "final" else ((854, 480) if orientation == "landscape" else (480, 854))
    assert (video["width"], video["height"]) == dimensions
    assert any(s["codec_type"] == "audio" for s in probe["streams"])
    assert float(video["duration"]) == 15
    assert video["nb_frames"] == "450"
    assert output.with_suffix(".srt").read_text() == engine.captions_srt(spec["captions"])
    # A captioned frame must differ from the solid-color source. Decode pixels,
    # checking the subtitle region has bright pixels rather than only blue.
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "14", "-i", str(output),
                          "-frames:v", "1", "-vf", "scale=160:90", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    assert any(raw[i] > 120 and raw[i+1] > 120 for i in range(60 * 160 * 3, len(raw)-2, 3))


def test_source_too_short_rejected(media):
    spec = episode()
    spec["clips"][0]["start"] = 2
    with pytest.raises(ValueError, match="exceeds"):
        engine.render_episode(spec, media / "too-short.mp4", base_dir=media)
    assert not (media / "too-short.mp4").exists()


def test_mixed_stream_duration_rejected(media):
    mixed = media / "short-video-long-audio.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "color=c=blue:s=160x90:r=30:d=5", "-i", str(media / "music.wav"),
                    "-c:v", "libx264", "-threads", "1", "-c:a", "aac", str(mixed)], check=True)
    probe = engine._probe(mixed)
    assert float(probe["format"]["duration"]) >= 15
    assert engine._stream_duration(next(s for s in probe["streams"] if s["codec_type"] == "video")) == 5
    spec = episode()
    spec["clips"][0]["path"] = mixed.name
    with pytest.raises(ValueError, match="exceeds"):
        engine.render_episode(spec, media / "mixed-out.mp4", base_dir=media)
    assert not (media / "mixed-out.mp4").exists()
    assert not (media / "mixed-out.srt").exists()


def test_unknown_stream_duration_rejected():
    with pytest.raises(ValueError, match="unknown"):
        engine._stream_duration({"nb_frames": "450", "avg_frame_rate": "30/1"})
    assert engine._stream_duration({"duration_ts": 450, "time_base": "1/30"}) == 15


def test_render_rejects_short_final_video(media, monkeypatch):
    original = engine._probe
    def probe(path):
        result = original(path)
        if Path(path).name == "render.mp4":
            video = next(s for s in result["streams"] if s["codec_type"] == "video")
            video["duration"] = "5.000000"
            video["duration_ts"] = 5 * 15360
            video["time_base"] = "1/15360"
            video["nb_frames"] = "150"
        return result
    monkeypatch.setattr(engine, "_probe", probe)
    with pytest.raises(RuntimeError, match="coverage"):
        engine.render_episode(episode(), media / "invalid-final.mp4", base_dir=media)
    assert not (media / "invalid-final.mp4").exists()


@pytest.mark.parametrize("transition,seconds", [("crossfade", 0.2), ("fade_black", 0),
                                               ("fade_black", 0.3), ("fade_black", float("nan"))])
def test_invalid_transition(transition, seconds):
    spec = episode()
    spec.update(transition=transition, transition_seconds=seconds)
    with pytest.raises(ValueError, match="transition"):
        engine.validate_episode(spec)


def _picture_pixel(path, seconds):
    result = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(seconds), "-i", str(path),
                             "-frames:v", "1", "-vf", "crop=4:4:10:10", "-f", "rawvideo",
                             "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    return result.stdout


def _audio_energy(path, seconds):
    import array
    result = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(seconds), "-i", str(path),
                             "-t", "0.1", "-vn", "-f", "s16le", "-ac", "1", "-"],
                            capture_output=True, check=True)
    samples = array.array("h", result.stdout)
    assert samples
    return sum(float(s) ** 2 for s in samples) / len(samples)


def test_fade_black_keeps_exact_timeline_and_continuous_audio(media):
    spec = episode()
    spec.update(transition="fade_black", transition_seconds=0.2)
    spec["clips"] = [{"path": "clip.mp4", "start": 0, "duration": 8},
                     {"path": "clip.mp4", "start": 0, "duration": 7}]
    output = media / "fade.mp4"
    engine.render_episode(spec, output, base_dir=media)
    video = next(s for s in engine._probe(output)["streams"] if s["codec_type"] == "video")
    assert float(video["duration"]) == 15 and video["nb_frames"] == "450"
    assert max(_picture_pixel(output, 7)) > 200
    assert max(_picture_pixel(output, 8)) < 10
    assert max(_picture_pixel(output, 8.5)) > 200
    assert _audio_energy(output, 7.95) > 1000


@pytest.fixture(scope="module")
def story_inputs(media):
    output = media / "assembly-source.mp4"
    engine.render_episode(episode(), output, base_dir=media)
    return output


def test_assemble_story_retains_full_video_and_audio(story_inputs):
    output = story_inputs.parent / "story.mp4"
    result = engine.assemble_episodes([story_inputs, story_inputs], output)
    assert result["episode_count"] == 2 and result["duration_seconds"] == 30
    probe = engine._probe(output)
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    audio = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    assert video["nb_frames"] == "900" and float(video["duration"]) == 30
    assert float(audio["duration"]) == pytest.approx(30, abs=0.1)
    assert _audio_energy(output, 14.95) > 1000
    assert _audio_energy(output, 29) > 1000
    assert max(_picture_pixel(output, 29)) > 200
    original_bytes = output.read_bytes()
    with pytest.raises(FileExistsError):
        engine.assemble_episodes([story_inputs], output)
    assert output.read_bytes() == original_bytes


def test_assemble_rejects_dimension_mismatch(story_inputs, monkeypatch):
    original = engine._probe
    calls = 0
    def probe(path):
        nonlocal calls
        calls += 1
        result = original(path)
        if calls == 2:
            video = next(s for s in result["streams"] if s["codec_type"] == "video")
            video["width"], video["height"] = 480, 854
        return result
    monkeypatch.setattr(engine, "_probe", probe)
    output = story_inputs.parent / "mismatch.mp4"
    with pytest.raises(ValueError, match="dimensions"):
        engine.assemble_episodes([story_inputs, story_inputs], output)
    assert not output.exists()


def test_assemble_rejects_non_episode_and_unbounded_list(media):
    with pytest.raises(ValueError, match="1-24"):
        engine.assemble_episodes([], media / "empty.mp4")
    with pytest.raises(ValueError, match="1-24"):
        engine.assemble_episodes([media / "clip.mp4"] * 25, media / "too-many.mp4")
    with pytest.raises(ValueError, match="one video and one audio"):
        engine.assemble_episodes([media / "clip.mp4"], media / "no-audio.mp4")
