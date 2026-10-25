"""Real local first-episode media; no accounts, paid calls or fake acceptance."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import wave

import pytest

pytest.importorskip("cairosvg")
np = pytest.importorskip("numpy")
pytest.importorskip("PIL")
ROOT = Path(__file__).resolve().parents[4]
SRC = Path(__file__).resolve().parents[1] / "src"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SRC / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RIG = ROOT / "modules/foundups/kids_episodes/series/little_shrew/character.svg"


@pytest.fixture(scope="module")
def animation():
    return load("little_shrew_animation")


@pytest.fixture(scope="module")
def preview():
    return load("little_shrew_preview")


def test_five_characters_motion_and_join_continuity(animation):
    scene = animation.ShrewScene(RIG)
    for time in (0, 4.99, 5, 9.99, 10, 14.99):
        assert scene.svg(time).count('data-character=') == 5
    still = np.asarray(scene.frame(3))[330:430, 340:900]
    moved = np.asarray(scene.frame(6))[330:430, 340:900]
    assert np.mean(abs(still.astype(float) - moved)) > 1
    import xml.etree.ElementTree as ET
    for time in (0, 2.5, 6, 12):
        root = ET.fromstring(scene.svg(time))
        characters = [g for g in root.iter() if "data-character" in g.attrib]
        assert all("scale(0.42)" in g.attrib["transform"] for g in characters[2:])
        assert all(next(iter(g)).attrib["href"] == "#sleepy" for g in characters[:4])
        assert next(iter(characters[4])).attrib["href"] == ("#sleepy" if time == 0 else "#neutral")
    # Fixed camera/set and nearly identical motion on both sides of each join.
    for join in (5, 10):
        before = np.asarray(scene.frame(join - 1/30)).astype(float)
        after = np.asarray(scene.frame(join)).astype(float)
        assert np.mean(abs(before - after)) < 2
    for time in (-1, 15, float("nan")):
        with pytest.raises(ValueError):
            scene.frame(time)


def test_audio_is_deterministic_bounded_and_exclusive(tmp_path, animation):
    paths = [tmp_path / name for name in ("a.wav", "b.wav")]
    for path in paths:
        cues = animation.compose_audio(path)
        with wave.open(str(path)) as audio:
            assert audio.getnframes() == 720000
            samples = np.frombuffer(audio.readframes(720000), dtype="<i2")
            assert 1000 < np.max(abs(samples.astype(float))) < 26214
        assert cues[-1]["end"] < 15
    assert paths[0].read_bytes() == paths[1].read_bytes()
    with pytest.raises(FileExistsError):
        animation.compose_audio(paths[0])


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_real_first_episode_and_provenance(tmp_path, preview):
    output = tmp_path / "preview"
    record = preview.produce_preview(output)
    assert record["status"] == "rendered_unreviewed"
    assert record["paid_calls"] == 0
    assert record["result"]["duration_seconds"] == 15
    for name, digest in record["assets_sha256"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    for name in ("b01.mp4", "b02.mp4", "b03.mp4", "little-shrew-episode-01.mp4"):
        data = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams",
                                                  "-of", "json", str(output / name)]))
        video = next(s for s in data["streams"] if s["codec_type"] == "video")
        assert video["nb_frames"] == ("450" if name.startswith("little") else "150")
    assert "00:00:05,800 --> 00:00:07,200" in (output / "little-shrew-episode-01.srt").read_text()
    original = (output / "provenance.json").read_bytes()
    with pytest.raises(FileExistsError):
        preview.produce_preview(output)
    assert (output / "provenance.json").read_bytes() == original
