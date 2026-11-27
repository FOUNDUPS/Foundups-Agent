# -*- coding: utf-8 -*-
"""Headless Video Orchestrator - Assemble music videos from audio + visuals."""

from dataclasses import dataclass
from pathlib import Path
import subprocess
import tempfile
from typing import List, Optional

from modules.communication.youtube_shorts.src.video_editor import VideoEditor, VideoEditorError

_SUBPROCESS_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class MusicVideoBuildError(Exception):
    """Raised when music video assembly fails."""


@dataclass
class MusicVideoRequest:
    """Input contract for music video assembly."""

    audio_path: str
    visual_paths: List[str]
    output_dir: str = "memory/video_lab/music_videos"
    aspect: str = "shorts"  # "shorts" | "landscape" | "raw"
    add_transitions: bool = False
    loop_video: bool = False
    render_profile: str = "legacy"  # "legacy" | "staging_720p"
    max_duration_sec: Optional[float] = None
    audio_fade_out_sec: float = 0.0


@dataclass
class MusicVideoOutput:
    """Output contract for music video assembly."""

    output_path: str
    formatted_path: Optional[str]
    combined_visual_path: Optional[str]


class HeadlessVideoOrchestrator:
    """Builds a music video by stitching visuals and overlaying audio."""

    def __init__(self, editor: Optional[VideoEditor] = None) -> None:
        self.editor = editor or VideoEditor()

    def build_music_video(self, req: MusicVideoRequest) -> MusicVideoOutput:
        """Assemble a music video from audio + visuals after upfront validation."""
        aspect = (req.aspect or "raw").strip().lower()
        profile = (req.render_profile or "legacy").strip().lower()
        if "4k" in aspect or "4k" in profile or "2160" in profile:
            raise MusicVideoBuildError("4K output is disallowed; use staging_720p or legacy")
        if profile not in {"legacy", "staging_720p"}:
            raise MusicVideoBuildError(f"Unknown render_profile: {req.render_profile}")
        if aspect not in {"shorts", "landscape", "raw", ""}:
            raise MusicVideoBuildError(f"Unknown aspect: {req.aspect}")

        max_dur = req.max_duration_sec
        if profile == "staging_720p":
            if aspect not in {"shorts", "landscape"}:
                raise MusicVideoBuildError("staging_720p requires aspect 'shorts' or 'landscape'")
            if aspect == "shorts":
                if max_dur is None:
                    max_dur = 178.5
                if max_dur <= 0 or max_dur >= 180.0:
                    raise MusicVideoBuildError("Shorts staging requires 0 < max_duration_sec < 180.0")
            elif max_dur is not None and max_dur <= 0:
                raise MusicVideoBuildError("max_duration_sec must be positive")

        if not req.audio_path:
            raise MusicVideoBuildError("audio_path is required")
        audio_path = Path(req.audio_path)
        if not audio_path.exists():
            raise MusicVideoBuildError(f"audio file not found: {audio_path}")

        if not req.visual_paths:
            raise MusicVideoBuildError("visual_paths must contain at least one video")
        visual_paths = [Path(p) for p in req.visual_paths]
        for path in visual_paths:
            if not path.exists():
                raise MusicVideoBuildError(f"visual clip not found: {path}")

        output_dir = Path(req.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        stem = audio_path.stem or "music_video"
        combined_visual_path: Optional[Path] = None

        if len(visual_paths) == 1:
            visual_path = visual_paths[0]
        else:
            combined_visual_path = output_dir / f"{stem}_visuals.mp4"
            with tempfile.TemporaryDirectory(prefix="hvo-concat-", dir=output_dir) as tmp_concat:
                prev_temp = self.editor.temp_dir
                self.editor.temp_dir = Path(tmp_concat)
                try:
                    self.editor.concatenate_clips(
                        [str(p) for p in visual_paths],
                        str(combined_visual_path),
                        add_transitions=req.add_transitions,
                    )
                except VideoEditorError as exc:
                    raise MusicVideoBuildError(str(exc)) from exc
                finally:
                    self.editor.temp_dir = prev_temp
            visual_path = combined_visual_path

        assembled_path = output_dir / f"{stem}_mv.mp4"
        self._overlay_audio(
            video_path=str(visual_path),
            audio_path=str(audio_path),
            output_path=str(assembled_path),
            loop_video=req.loop_video,
        )

        formatted_path: Optional[str] = None
        if profile == "staging_720p":
            formatted_path = self._ensure_staging_720p_format(
                str(assembled_path),
                aspect=aspect,
                max_duration_sec=max_dur,
                audio_fade_out_sec=req.audio_fade_out_sec,
            )
        elif aspect == "shorts":
            formatted_path = self.editor.ensure_shorts_format(str(assembled_path))
        elif aspect == "landscape":
            formatted_path = self._ensure_landscape_format(str(assembled_path))

        final_path = formatted_path or str(assembled_path)
        return MusicVideoOutput(
            output_path=final_path,
            formatted_path=formatted_path,
            combined_visual_path=str(combined_visual_path) if combined_visual_path else None,
        )

    def _overlay_audio(
        self,
        *,
        video_path: str,
        audio_path: str,
        output_path: str,
        loop_video: bool,
    ) -> None:
        """Combine video stream 0:v:0 with supplied soundtrack 1:a:0 under finite timeout."""
        cmd = ["ffmpeg", "-nostdin", "-y"]
        if loop_video:
            cmd.extend(["-stream_loop", "-1"])
        cmd.extend([
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path,
        ])
        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=180, creationflags=_SUBPROCESS_FLAGS)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            stderr = exc.stderr.decode(errors="ignore") if getattr(exc, "stderr", None) else str(exc)
            raise MusicVideoBuildError(f"ffmpeg overlay failed: {stderr}") from exc

    def _ensure_staging_720p_format(
        self,
        video_path: str,
        *,
        aspect: str,
        max_duration_sec: Optional[float],
        audio_fade_out_sec: float,
    ) -> str:
        """Format vertical 720x1280 or horizontal 1280x720 24fps H264/yuv420p AAC 192k."""
        width, height = (720, 1280) if aspect == "shorts" else (1280, 720)
        suffix = ".shorts720p.mp4" if aspect == "shorts" else ".landscape720p.mp4"
        output_path = str(Path(video_path).with_suffix(suffix))
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p"
        )
        cmd = ["ffmpeg", "-nostdin", "-y", "-i", video_path]
        if max_duration_sec is not None:
            cmd.extend(["-t", f"{max_duration_sec:.3f}"])
        cmd.extend(["-vf", vf])
        if audio_fade_out_sec > 0 and max_duration_sec and max_duration_sec > audio_fade_out_sec:
            fade_start = max(0.0, max_duration_sec - audio_fade_out_sec)
            cmd.extend(["-af", f"afade=t=out:st={fade_start:.3f}:d={audio_fade_out_sec:.3f}"])
        cmd.extend([
            "-c:v", "libx264", "-preset", "fast", "-crf", "21",
            "-pix_fmt", "yuv420p", "-r", "24",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
            output_path,
        ])
        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=180, creationflags=_SUBPROCESS_FLAGS)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            stderr = exc.stderr.decode(errors="ignore") if getattr(exc, "stderr", None) else str(exc)
            raise MusicVideoBuildError(f"ffmpeg staging_720p failed: {stderr}") from exc
        return output_path

    def _ensure_landscape_format(self, video_path: str) -> str:
        """Ensure 16:9 output for legacy longform under finite timeout."""
        output_path = str(Path(video_path).with_suffix(".landscape.mp4"))
        cmd = [
            "ffmpeg", "-nostdin", "-y", "-i", video_path,
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            output_path,
        ]
        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=180, creationflags=_SUBPROCESS_FLAGS)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            stderr = exc.stderr.decode(errors="ignore") if getattr(exc, "stderr", None) else str(exc)
            raise MusicVideoBuildError(f"ffmpeg landscape format failed: {stderr}") from exc
        return output_path
