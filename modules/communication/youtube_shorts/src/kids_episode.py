"""Local 15-second educational episode assembly; no generation or publishing.

Run directly (avoids optional provider imports in the legacy package initializer)::

    python modules/communication/youtube_shorts/src/kids_episode.py episode.json --output out.mp4

Minimal JSON contract (paths relative to the JSON file)::

    {"schema_version": 1, "title": "Count and clap", "learning_objective": "Count to three",
     "activity": "Clap three times", "age_band": "3-5", "language": "en",
     "duration_seconds": 15, "preset": "draft", "orientation": "landscape",
     "clips": [{"path": "shot.mp4", "start": 0, "duration": 15}],
     "music": {"path": "song.wav", "rights_evidence": "Original composition"},
     "captions": [{"start": 0, "end": 5, "text": "One, two, three!"}]}

Optional voice={"path": "voice.wav"} replaces source clip audio and mixes with
quieter music. Caption timings are supplied/aligned upstream, not inferred here.
Rights evidence is a required declaration, not an automated legal verification.
Optional transition="fade_black", transition_seconds=0.2 fades the picture at
internal shot edges without shortening the timeline or interrupting music.
assemble_episodes(paths, output_path) joins compatible 15-second renders; the
caller owns review decisions, and assembled output requires its own review.
"""
from __future__ import annotations

import argparse
import copy
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

DURATION = 15.0
PRESETS = {"draft": (854, 480, "28", "veryfast"), "final": (1920, 1080, "18", "medium")}


def _number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{field} must be a finite number")
    return float(value)


def _text(value, field, limit=300):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} must contain 1-{limit} characters")
    if any(ord(c) < 32 for c in value):
        raise ValueError(f"{field} cannot contain control characters")
    return value.strip()


def validate_episode(spec: dict) -> dict:
    """Return a normalized copy or raise ValueError; perform no IO."""
    if not isinstance(spec, dict):
        raise ValueError("episode must be an object")
    result = copy.deepcopy(spec)
    if type(result.get("schema_version")) is not int or result["schema_version"] != 1:
        raise ValueError("schema_version must be 1")
    for field in ("title", "learning_objective", "activity", "age_band", "language"):
        result[field] = _text(result.get(field), field)
    if _number(result.get("duration_seconds"), "duration_seconds") != DURATION:
        raise ValueError("episode duration must be exactly 15 seconds")
    if not isinstance(result.get("preset"), str) or result["preset"] not in PRESETS:
        raise ValueError("preset must be draft or final")
    if result.get("orientation") not in ("landscape", "portrait"):
        raise ValueError("orientation must be landscape or portrait")
    transition = result.get("transition", "cut")
    if transition not in ("cut", "fade_black"):
        raise ValueError("transition must be cut or fade_black")
    fade_seconds = _number(result.get("transition_seconds", 0.2), "transition_seconds")
    if not 0 < fade_seconds <= 0.25:
        raise ValueError("transition_seconds must be greater than 0 and at most 0.25")
    clips = result.get("clips")
    if not isinstance(clips, list) or not 1 <= len(clips) <= 8:
        raise ValueError("clips must contain 1-8 shots")
    for clip in clips:
        if not isinstance(clip, dict):
            raise ValueError("clip must be an object")
        clip["path"] = _text(clip.get("path"), "clip.path", 4096)
        clip["start"] = _number(clip.get("start", 0), "clip.start")
        clip["duration"] = _number(clip.get("duration"), "clip.duration")
        if clip["start"] < 0 or not 0 < clip["duration"] <= DURATION:
            raise ValueError("clip start must be nonnegative and duration within 15 seconds")
    if transition == "fade_black" and any(c["duration"] < fade_seconds * 2 for c in clips):
        raise ValueError("clips must be at least twice the fade duration")
    if not math.isclose(sum(c["duration"] for c in clips), DURATION, abs_tol=1e-6):
        raise ValueError("clip durations must total 15 seconds")
    for kind in ("music", "voice"):
        if kind == "voice" and kind not in result:
            continue
        asset = result.get(kind)
        if not isinstance(asset, dict):
            raise ValueError(f"{kind} must be an object")
        asset["path"] = _text(asset.get("path"), f"{kind}.path", 4096)
    result["music"]["rights_evidence"] = _text(result["music"].get("rights_evidence"), "music.rights_evidence", 2000)
    if "captions_in_scene" in result and type(result["captions_in_scene"]) is not bool:
        raise ValueError("captions_in_scene must be Boolean")
    captions = result.get("captions")
    if not isinstance(captions, list) or not 1 <= len(captions) <= 30:
        raise ValueError("captions must contain 1-30 timed cues")
    previous_end = 0.0
    for cue in captions:
        if not isinstance(cue, dict):
            raise ValueError("caption must be an object")
        cue["start"] = _number(cue.get("start"), "caption.start")
        cue["end"] = _number(cue.get("end"), "caption.end")
        cue["text"] = _text(cue.get("text"), "caption.text", 140)
        if any(c in cue["text"] for c in "\\{}<>"):
            raise ValueError("captions must be plain text, without subtitle markup")
        if not previous_end <= cue["start"] < cue["end"] <= DURATION:
            raise ValueError("captions must be ordered, non-overlapping, and within 15 seconds")
        if round(cue["end"] * 1000) <= round(cue["start"] * 1000):
            raise ValueError("caption must last at least one millisecond")
        previous_end = cue["end"]
    return result


def _timestamp(seconds):
    milliseconds = round(seconds * 1000)
    return f"00:00:{milliseconds // 1000:02d},{milliseconds % 1000:03d}"


def captions_srt(captions):
    return "\n".join(f"{i}\n{_timestamp(c['start'])} --> {_timestamp(c['end'])}\n{c['text']}\n"
                     for i, c in enumerate(captions, 1))


def _run(args, *, cwd=None, timeout=180):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True, timeout=timeout)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"{args[0]} failed: {exc.stderr[-2000:]}") from exc


def _probe(path):
    return json.loads(_run(["ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe",
                            "-show_streams", "-show_format", "-of", "json", str(path)], timeout=30).stdout)


def _stream_duration(stream):
    """Require coverage of the selected stream, never the enclosing container.

    Some containers omit per-stream durations. Reject those instead of assuming
    that a longer audio track proves video coverage. Remux/transcode such assets
    to a duration-bearing MP4/WAV before submitting them to this local editor.
    Frame-count/rate estimates are not used for input VFR streams.
    """
    durations = []
    for value in (stream.get("duration"),):
        try:
            duration = float(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(duration) and duration > 0:
            durations.append(duration)
    try:
        duration = float(int(stream["duration_ts"]) * Fraction(stream["time_base"]))
        if math.isfinite(duration) and duration > 0:
            durations.append(duration)
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        pass
    if not durations:
        raise ValueError("Selected media stream duration is unknown; remux/transcode to MP4 or WAV")
    return min(durations)


def _asset(path, base_dir, kind):
    resolved = (Path(base_dir) / path).resolve()
    extensions = {"video": {".mp4", ".mov", ".webm", ".mkv"},
                  "audio": {".wav", ".mp3", ".m4a", ".ogg", ".flac"}}
    if not resolved.is_file() or resolved.suffix.lower() not in extensions[kind]:
        raise ValueError(f"Expected a local {kind} file: {path}")
    probe = _probe(resolved)
    streams = [s for s in probe.get("streams", []) if s.get("codec_type") == kind]
    if not streams:
        raise ValueError(f"Missing {kind} stream: {path}")
    return resolved, _stream_duration(streams[0])


def render_episode(spec: dict, output_path, *, base_dir=".") -> dict:
    """Render MP4 and adjacent SRT; reject existing outputs and short assets.

    Does not attest educational review, music rights, or publishing approval.
    Source clip audio is intentionally discarded. Requires FFmpeg with libass.
    """
    episode = validate_episode(spec)
    output = Path(output_path).resolve()
    sidecar = output.with_suffix(".srt")
    if output.suffix.lower() != ".mp4":
        raise ValueError("output must be an MP4 path")
    if output.exists() or sidecar.exists():
        raise FileExistsError("MP4 or subtitle output already exists")
    width, height, crf, speed = PRESETS[episode["preset"]]
    if episode["orientation"] == "portrait":
        width, height = height, width
    inputs = []
    for clip in episode["clips"]:
        path, duration = _asset(clip["path"], base_dir, "video")
        if clip["start"] + clip["duration"] > duration + 0.04:
            raise ValueError("clip trim exceeds source duration")
        inputs.append(path)
    music, duration = _asset(episode["music"]["path"], base_dir, "audio")
    if duration < DURATION - 0.04:
        raise ValueError("music must cover the 15-second episode")
    inputs.append(music)
    if "voice" in episode:
        voice, duration = _asset(episode["voice"]["path"], base_dir, "audio")
        inputs.append(voice)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="kids-episode-", dir=output.parent) as temp:
        temp = Path(temp)
        subtitle_text = captions_srt(episode["captions"])
        (temp / "captions.srt").write_text(subtitle_text, encoding="utf-8")
        args = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-filter_complex_threads", "1"]
        for path in inputs:
            args += ["-protocol_whitelist", "file,pipe", "-i", str(path)]
        filters = []
        for i, clip in enumerate(episode["clips"]):
            fades = ""
            if episode.get("transition", "cut") == "fade_black":
                fade_seconds = episode.get("transition_seconds", 0.2)
                if i > 0:
                    fades += f",fade=t=in:st=0:d={fade_seconds}"
                if i < len(episode["clips"]) - 1:
                    fades += f",fade=t=out:st={clip['duration']-fade_seconds}:d={fade_seconds}"
            filters.append(f"[{i}:v:0]setpts=PTS-STARTPTS,trim=start={clip['start']}:duration={clip['duration']},setpts=PTS-STARTPTS,"
                           f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                           f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p{fades}[v{i}]")
        count = len(episode["clips"])
        filters.append("".join(f"[v{i}]" for i in range(count)) + f"concat=n={count}:v=1:a=0[assembled]")
        if episode.get("captions_in_scene") is True:
            filters.append("[assembled]null[video]")
        else:
            filters.append("[assembled]subtitles=captions.srt:force_style='FontName=DejaVu Sans,FontSize=22,"
                           "PrimaryColour=&H0000FFFF,OutlineColour=&H00181818,BorderStyle=1,Outline=2,"
                           "Shadow=0,Alignment=2,MarginV=25'[video]")
        music_volume = "0.20" if "voice" in episode else "0.80"
        filters.append(f"[{count}:a:0]asetpts=PTS-STARTPTS,atrim=duration=15,volume={music_volume}[music]")
        if "voice" in episode:
            filters.append(f"[{count+1}:a:0]asetpts=PTS-STARTPTS,atrim=duration=15,apad=whole_dur=15[voice]")
            filters.append("[music][voice]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=0[audio]")
        else:
            filters.append("[music]alimiter=limit=0.95:level=0[audio]")
        args += ["-filter_complex", ";".join(filters), "-map", "[video]", "-map", "[audio]",
                 "-t", "15", "-c:v", "libx264", "-threads", "2", "-preset", speed, "-crf", crf,
                 "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", "render.mp4"]
        _run(args, cwd=temp)
        measured = _probe(temp / "render.mp4")
        measured_duration = float(measured["format"]["duration"])
        if abs(measured_duration - DURATION) > 0.10:
            raise RuntimeError("render duration failed verification")
        video_streams = [s for s in measured.get("streams", []) if s.get("codec_type") == "video"]
        if (len(video_streams) != 1 or
                (video_streams[0].get("width"), video_streams[0].get("height")) != (width, height) or
                not any(s.get("codec_type") == "audio" for s in measured.get("streams", []))):
            raise RuntimeError("render stream verification failed")
        # Container duration can be supplied by audio alone. Independently
        # require the encoded video timeline and its fixed-rate frame count.
        video = video_streams[0]
        if (abs(_stream_duration(video) - DURATION) > 1 / 30 or
                video.get("nb_frames") != "450" or
                Fraction(video.get("avg_frame_rate", "0")) != 30):
            raise RuntimeError("render video coverage failed verification")
        # Same-volume hard links publish complete files without replacing an
        # existing or concurrent output, and avoid copying a video into RAM.
        os.link(temp / "render.mp4", output)
        try:
            os.link(temp / "captions.srt", sidecar)
        except BaseException:
            output.unlink()
            raise
    return {"video_path": str(output), "captions_path": str(sidecar), "duration_seconds": measured_duration,
            "width": width, "height": height, "preset": episode["preset"], "status": "rendered_unreviewed"}


def assemble_episodes(paths, output_path) -> dict:
    """Join 1-24 compatible 15-second renders with their existing audio/captions.

    Inputs must have one H264 video stream at 30fps/450 frames and one AAC audio
    stream spanning 15 seconds, with matching draft/final dimensions. Audio is
    normalized to stereo/48kHz and each timeline starts at zero before concat.
    Burned captions remain visible; no combined subtitle sidecar is generated.
    The caller owns review selection. This function does not attest review or
    authorize publishing; the final story is returned as assembled_unreviewed.
    """
    if not isinstance(paths, (list, tuple)) or not 1 <= len(paths) <= 24:
        raise ValueError("paths must contain 1-24 episode files")
    output = Path(output_path).resolve()
    if output.suffix.lower() != ".mp4":
        raise ValueError("output must be an MP4 path")
    if output.exists():
        raise FileExistsError("story output already exists")
    inputs, dimensions = [], None
    allowed_dimensions = {(854, 480), (480, 854), (1920, 1080), (1080, 1920)}
    for path in paths:
        resolved = Path(path).resolve()
        if not resolved.is_file() or resolved.suffix.lower() != ".mp4":
            raise ValueError("Each episode must be a local MP4")
        probe = _probe(resolved)
        videos = [stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"]
        audios = [stream for stream in probe.get("streams", []) if stream.get("codec_type") == "audio"]
        if len(videos) != 1 or len(audios) != 1:
            raise ValueError("Each episode must contain one video and one audio stream")
        video, audio = videos[0], audios[0]
        size = (video.get("width"), video.get("height"))
        if size not in allowed_dimensions or (dimensions is not None and size != dimensions):
            raise ValueError("Episode dimensions must match a single draft/final preset")
        if (video.get("codec_name") != "h264" or audio.get("codec_name") != "aac" or
                abs(_stream_duration(video) - DURATION) > 1 / 30 or
                abs(_stream_duration(audio) - DURATION) > 0.1 or
                video.get("nb_frames") != "450" or
                Fraction(video.get("avg_frame_rate", "0")) != 30):
            raise ValueError("Each episode must provide 15 seconds of H264/AAC at 30fps/450 frames")
        dimensions = size
        inputs.append(resolved)
    output.parent.mkdir(parents=True, exist_ok=True)
    expected_duration = DURATION * len(inputs)
    with tempfile.TemporaryDirectory(prefix="kids-story-", dir=output.parent) as temp:
        temp = Path(temp)
        args = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-filter_complex_threads", "1"]
        filters = []
        for i, path in enumerate(inputs):
            args += ["-protocol_whitelist", "file,pipe", "-threads", "1", "-i", str(path)]
            filters += [f"[{i}:v:0]setpts=PTS-STARTPTS,trim=duration=15,setsar=1,fps=30,format=yuv420p[v{i}]",
                        f"[{i}:a:0]asetpts=PTS-STARTPTS,atrim=duration=15,aresample=48000,"
                        f"aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]"]
        filters.append("".join(f"[v{i}][a{i}]" for i in range(len(inputs))) +
                       f"concat=n={len(inputs)}:v=1:a=1[video][audio]")
        args += ["-filter_complex", ";".join(filters), "-map", "[video]", "-map", "[audio]",
                 "-t", str(expected_duration), "-c:v", "libx264", "-threads", "2", "-preset", "medium",
                 "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                 "-movflags", "+faststart", "story.mp4"]
        _run(args, cwd=temp, timeout=900)
        probe = _probe(temp / "story.mp4")
        video = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), {})
        audio = next((s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), {})
        if (abs(_stream_duration(video) - expected_duration) > 1 / 30 or
                abs(_stream_duration(audio) - expected_duration) > 0.1 or
                video.get("nb_frames") != str(450 * len(inputs)) or
                Fraction(video.get("avg_frame_rate", "0")) != 30 or
                (video.get("width"), video.get("height")) != dimensions):
            raise RuntimeError("assembled story stream verification failed")
        os.link(temp / "story.mp4", output)
    return {"video_path": str(output), "duration_seconds": expected_duration,
            "width": dimensions[0], "height": dimensions[1], "episode_count": len(inputs),
            "status": "assembled_unreviewed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.spec.stat().st_size > 65536:
        parser.error("episode spec exceeds 64 KiB")
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    print(json.dumps(render_episode(spec, args.output, base_dir=args.spec.resolve().parent), indent=2))


if __name__ == "__main__":
    main()
