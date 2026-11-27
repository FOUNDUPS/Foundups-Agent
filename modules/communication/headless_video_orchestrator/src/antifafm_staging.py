# -*- coding: utf-8 -*-
"""Antifa FM headless staging, A/B/C benchmark rendering, decode verification, and 1/day slot planning.

Part of ``modules/communication/headless_video_orchestrator``. Reuses ``VideoEditor`` for segment
concatenation and ``ScheduleTracker`` for browser-free 1/day cadence previews while enforcing
canonical Antifa FM channel identity (``UCVSmg5aOhP4tnQ9KFUg97qA``). No paid model calls, Drive
writes, or live YouTube uploads run here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Any, Optional, Sequence

from modules.communication.youtube_shorts.src.video_editor import VideoEditor

from .media_signal_audit import (
    AFFILIATION_TERMS,
    ALLOWED_CLAIM_CATEGORIES,
    FACTUAL_CLAIM_CATEGORIES,
    analyze_audio_16k_mono,
    audit_satire_claims,
    compare_audio_sources,
    inspect_per_channel_sample_peaks,
    parse_embedded_srt,
    probe_media_artifact,
    run_media_cmd,
    sha256_file,
)

_SUBPROCESS_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)
ANTIFAFM_CANONICAL_CHANNEL_ID = "UCVSmg5aOhP4tnQ9KFUg97qA"


@dataclass(frozen=True)
class CutSpec:
    """Single cut specification for A/B/C benchmark or staged render."""

    scene_id: str
    start_sec: float
    duration_sec: float
    source_paths: tuple[str, ...]
    crop_box: Optional[tuple[int, int, int, int]] = None  # (x, y, w, h) on atlas/stage
    zoom_ratio: float = 1.0
    pan_dx_px: int = 0
    pan_dy_px: int = 0
    stepped_fps: Optional[int] = None
    lyric_cue: str = ""
    lyric_source: str = "none"
    lyric_confidence: Optional[float] = None


def _probe_image_dims(path: Path) -> tuple[int, int]:
    info = probe_media_artifact(path)
    video = info.get("video") or {}
    w, h = int(video.get("width") or 0), int(video.get("height") or 0)
    if w <= 0 or h <= 0:
        raise ValueError(f"Could not determine raster dimensions for {path}")
    return w, h


def _strict_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def render_benchmark_excerpt(
    *,
    variant_id: str,
    audio_path: str | Path,
    cuts: Sequence[CutSpec],
    output_path: str | Path,
    excerpt_start_sec: float = 0.0,
    orientation: str = "portrait",
    seed: int = 0,
    audio_fade_out_sec: float = 0.5,
) -> dict[str, Any]:
    """Render deterministic 720p 24fps H264/yuv420p AAC 192k excerpt and emit CutManifest."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", variant_id):
        raise ValueError("Invalid variant_id")
    if not cuts:
        raise ValueError("At least one CutSpec is required")
    if orientation not in {"portrait", "landscape"}:
        raise ValueError("orientation must be 'portrait' or 'landscape'")

    out_w, out_h = (720, 1280) if orientation == "portrait" else (1280, 720)
    target_out = Path(output_path).resolve()
    if target_out.exists():
        raise FileExistsError(f"Output already exists; refusing overwrite: {target_out}")
    target_out.parent.mkdir(parents=True, exist_ok=True)

    audio_file = Path(audio_path).resolve()
    audio_probe = probe_media_artifact(audio_file)
    total_duration = round(sum(c.duration_sec for c in cuts), 6)
    if total_duration <= 0 or total_duration >= 180.0:
        raise ValueError("Total cut duration must be > 0 and strictly < 180.0s")

    expected_cursor = 0.0
    for cut in cuts:
        if cut.duration_sec <= 0:
            raise ValueError(f"Invalid cut duration in {cut.scene_id}")
        if abs(cut.start_sec - expected_cursor) > 1e-3:
            raise ValueError(f"Cut {cut.scene_id} start_sec={cut.start_sec} is not contiguous with {expected_cursor}")
        if not cut.source_paths:
            raise ValueError(f"Cut {cut.scene_id} requires at least one source_path")
        if cut.lyric_cue and cut.lyric_source == "none":
            raise ValueError(f"Cut {cut.scene_id} supplies lyric_cue without provenance source")
        _strict_int(cut.pan_dx_px, "pan_dx_px")
        _strict_int(cut.pan_dy_px, "pan_dy_px")
        expected_cursor += cut.duration_sec

    t0 = time.perf_counter()
    cut_records: list[dict[str, Any]] = []
    unique_assets: set[str] = set()

    with tempfile.TemporaryDirectory(prefix=f"antifafm-{variant_id}-", dir=target_out.parent) as temp_dir:
        tmp = Path(temp_dir)
        segment_files: list[Path] = []

        for idx, cut in enumerate(cuts):
            src_files = [Path(p).resolve() for p in cut.source_paths]
            src_hashes = [sha256_file(p) for p in src_files]
            unique_assets.update(src_hashes)
            distinct_pose_count = len(set(src_hashes))

            # Inspect EVERY source frame so secondary images cannot smuggle low-res or mismatched geometry
            dims_per_frame = [_probe_image_dims(sf) for sf in src_files]
            if len(set(dims_per_frame)) > 1:
                raise ValueError(f"Cut {cut.scene_id} has mismatched frame dimensions across sequence: {dims_per_frame}")
            img_w, img_h = dims_per_frame[0]

            if cut.crop_box is not None:
                cx, cy, cw, ch = (_strict_int(v, "crop_box") for v in cut.crop_box)
                if cx < 0 or cy < 0 or cw <= 0 or ch <= 0 or cx + cw > img_w or cy + ch > img_h:
                    raise ValueError(f"Invalid crop_box {cut.crop_box} for {img_w}x{img_h} in {cut.scene_id}")
            else:
                cx, cy, cw, ch = 0, 0, img_w, img_h

            pan_dx = _strict_int(cut.pan_dx_px, "pan_dx_px")
            pan_dy = _strict_int(cut.pan_dy_px, "pan_dy_px")
            effective_cw = cw / max(1.0, float(cut.zoom_ratio))
            effective_ch = ch / max(1.0, float(cut.zoom_ratio))
            native_w_ratio = round(effective_cw / out_w, 4)
            native_h_ratio = round(effective_ch / out_h, 4)
            upscale_warning = min(native_w_ratio, native_h_ratio) < 1.0

            has_camera_move = (cut.zoom_ratio != 1.0) or (pan_dx != 0) or (pan_dy != 0)
            if distinct_pose_count >= 2:
                # Two distinct hashes prove only an unreviewed multi-image sequence, NOT character action.
                motion_class = "multi_image_sequence_unreviewed"
            elif has_camera_move:
                motion_class = "camera_only"
            else:
                motion_class = "static_hold"

            seg_path = tmp / f"seg_{idx:03d}.mp4"
            frames_total = max(1, round(cut.duration_sec * 24))

            if distinct_pose_count >= 2:
                step_fps = _strict_int(cut.stepped_fps or 12, "stepped_fps")
                if not (1 <= step_fps <= 24):
                    raise ValueError("stepped_fps must be between 1 and 24")
                concat_txt = tmp / f"poses_{idx:03d}.txt"
                step_dur = 1.0 / float(step_fps)
                repeats = max(2, math.ceil(cut.duration_sec / step_dur))
                lines = []
                for step_i in range(repeats):
                    pose_file = src_files[step_i % len(src_files)]
                    lines.append(f"file '{pose_file.as_posix()}'")
                    lines.append(f"duration {step_dur:.6f}")
                lines.append(f"file '{src_files[(repeats - 1) % len(src_files)].as_posix()}'")
                concat_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
                vf = (
                    f"crop={cw}:{ch}:{cx}:{cy},"
                    f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
                    f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p"
                )
                run_media_cmd(
                    ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-protocol_whitelist", "file,pipe", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-t", f"{cut.duration_sec:.6f}", "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "24", "-an", str(seg_path)],
                    timeout=90,
                )
            else:
                z_end = max(1.0, min(1.15, float(cut.zoom_ratio)))
                z_step = (z_end - 1.0) / max(1, frames_total - 1)
                vf = (
                    f"crop={cw}:{ch}:{cx}:{cy},"
                    f"scale={out_w * 2}:{out_h * 2}:force_original_aspect_ratio=increase,"
                    f"crop={out_w * 2}:{out_h * 2},"
                    f"zoompan=z='min(1.0+{z_step:.7f}*on,{z_end:.5f})':"
                    f"x='iw/2-(iw/zoom/2)+({pan_dx}*on/{max(1, frames_total)})':"
                    f"y='ih/2-(ih/zoom/2)+({pan_dy}*on/{max(1, frames_total)})':"
                    f"d={frames_total}:s={out_w}x{out_h}:fps=24,format=yuv420p"
                )
                run_media_cmd(
                    ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-protocol_whitelist", "file,pipe", "-loop", "1", "-i", str(src_files[0]), "-frames:v", str(frames_total), "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "24", "-an", str(seg_path)],
                    timeout=90,
                )

            segment_files.append(seg_path)
            cut_records.append(
                {
                    "scene_id": cut.scene_id,
                    "start_sec": round(cut.start_sec, 3),
                    "end_sec": round(cut.start_sec + cut.duration_sec, 3),
                    "duration_sec": round(cut.duration_sec, 3),
                    "source_sha256": src_hashes,
                    "distinct_source_hashes": distinct_pose_count,
                    "motion_class": motion_class,
                    "true_character_animation": False,
                    "character_action_review_status": "unreviewed_requires_independent_visual_eval",
                    "camera_params": {
                        "crop_box": [cx, cy, cw, ch],
                        "zoom_ratio": cut.zoom_ratio,
                        "pan_dx_px": pan_dx,
                        "pan_dy_px": pan_dy,
                    },
                    "action_params": {"stepped_fps": cut.stepped_fps if distinct_pose_count >= 2 else None},
                    "sharpness": {
                        "native_crop_width_ratio": native_w_ratio,
                        "native_crop_height_ratio": native_h_ratio,
                        "upscale_interpolation_warning": upscale_warning,
                    },
                    "lyric_alignment": {
                        "cue": cut.lyric_cue,
                        "source": cut.lyric_source,
                        "confidence": cut.lyric_confidence,
                    },
                }
            )

        if len(segment_files) == 1:
            stitched_video = segment_files[0]
        else:
            stitched_video = tmp / "stitched_visuals.mp4"
            editor = VideoEditor()
            editor.temp_dir = tmp
            editor.concatenate_clips([str(p) for p in segment_files], str(stitched_video), add_transitions=False)

        mux_cmd = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-protocol_whitelist", "file,pipe",
            "-i", str(stitched_video),
            "-ss", f"{excerpt_start_sec:.3f}", "-t", f"{total_duration:.3f}", "-i", str(audio_file),
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
        ]
        if audio_fade_out_sec > 0 and total_duration > audio_fade_out_sec:
            fade_st = max(0.0, total_duration - audio_fade_out_sec)
            mux_cmd.extend(["-af", f"afade=t=out:st={fade_st:.3f}:d={audio_fade_out_sec:.3f}"])
        mux_cmd.extend(["-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(target_out)])
        run_media_cmd(mux_cmd, timeout=120)

    wall_time_sec = round(time.perf_counter() - t0, 3)
    verification = verify_rendered_output(target_out, expected_width=out_w, expected_height=out_h, expected_fps=24.0)

    manifest = {
        "schema_version": "antifafm_cut_manifest.v1",
        "variant_id": variant_id,
        "seed": seed,
        "orientation": orientation,
        "excerpt_start_sec": excerpt_start_sec,
        "excerpt_duration_sec": total_duration,
        "input_audio_sha256": audio_probe["sha256"],
        "output_video_path": str(target_out),
        "output_video_sha256": verification["sha256"],
        "output_size_bytes": verification["size_bytes"],
        "unique_visual_asset_count": len(unique_assets),
        "wall_time_sec": wall_time_sec,
        "paid_request_count": 0,
        "paid_cost_usd": 0.0,
        "rsi_promotion_status": "candidate_unpromoted",
        "creative_quality_accepted": False,
        "cuts": cut_records,
        "verification": verification,
    }
    manifest_path = target_out.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def verify_rendered_output(
    video_path: str | Path,
    *,
    expected_width: int = 720,
    expected_height: int = 1280,
    expected_fps: float = 24.0,
    max_freeze_sec: float = 2.5,
    extract_frames_dir: Optional[str | Path] = None,
) -> dict[str, Any]:
    """Perform full FFmpeg decode, black/freeze/frame-count/per-channel-sample checks, and frame extraction."""
    target = Path(video_path).resolve()
    probe = probe_media_artifact(target)
    video = probe.get("video") or {}
    audio = probe.get("audio") or {}

    decode_proc = subprocess.run(
        [
            "ffmpeg", "-nostdin", "-hide_banner", "-v", "info", "-protocol_whitelist", "file,pipe",
            "-i", str(target),
            "-vf", f"blackdetect=d=0.1:pix_th=0.05,freezedetect=n=0.001:d={max_freeze_sec:.2f}",
            "-f", "null", "-",
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, creationflags=_SUBPROCESS_FLAGS,
    )
    decode_ok = decode_proc.returncode == 0
    stderr_log = decode_proc.stderr or ""
    black_segments = re.findall(r"black_start:([0-9.]+)\s+black_end:([0-9.]+)", stderr_log)
    freeze_segments = re.findall(r"lavfi\.freezedetect\.freeze_start:\s*([0-9.]+)", stderr_log)

    channel_peaks = inspect_per_channel_sample_peaks(target) if audio else None
    extracted_frames: list[dict[str, Any]] = []
    if extract_frames_dir is not None and video:
        frames_dir = Path(extract_frames_dir).resolve()
        frames_dir.mkdir(parents=True, exist_ok=True)
        dur = max(0.2, float(video.get("duration_sec") or probe["container_duration_sec"]))
        for label, ts in (("start", 0.1), ("mid", round(dur * 0.5, 3)), ("end", max(0.1, round(dur - 0.15, 3)))):
            frame_path = frames_dir / f"{target.stem}_{label}.png"
            run_media_cmd(["ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error", "-protocol_whitelist", "file,pipe", "-ss", f"{ts:.3f}", "-i", str(target), "-frames:v", "1", str(frame_path)], timeout=30)
            extracted_frames.append({"label": label, "timestamp_sec": ts, "path": str(frame_path), "sha256": sha256_file(frame_path)})

    duration_sec = float(video.get("duration_sec") or probe["container_duration_sec"])
    nb_frames = video.get("nb_frames")
    expected_frames = round(duration_sec * expected_fps)
    frame_count_ok = isinstance(nb_frames, int) and abs(nb_frames - expected_frames) <= 2

    failure_reasons: list[str] = []
    if not decode_ok:
        failure_reasons.append("full_decode_failed")
    if video.get("codec_name") != "h264" or video.get("pix_fmt") != "yuv420p":
        failure_reasons.append("video_codec_or_pix_fmt_mismatch")
    if video.get("width") != expected_width or video.get("height") != expected_height:
        failure_reasons.append("video_dimensions_mismatch")
    if abs(float(video.get("r_fps") or 0.0) - expected_fps) >= 0.05 or abs(float(video.get("avg_fps") or 0.0) - expected_fps) >= 0.2:
        failure_reasons.append("video_fps_mismatch")
    if not frame_count_ok:
        failure_reasons.append("video_frame_count_mismatch")
    if not (0.0 < duration_sec < 180.0):
        failure_reasons.append("duration_out_of_shorts_bounds")
    if audio.get("codec_name") != "aac" or channel_peaks is None or channel_peaks["max_sample_peak_norm"] <= 0.001 or channel_peaks["full_scale_samples"] > 0:
        failure_reasons.append("audio_missing_silent_clipped_or_non_aac")
    if black_segments:
        failure_reasons.append("black_segments_detected")
    if freeze_segments:
        failure_reasons.append("frozen_segments_detected")

    passed = len(failure_reasons) == 0
    return {
        "path": str(target),
        "sha256": probe["sha256"],
        "size_bytes": probe["size_bytes"],
        "full_decode_passed": decode_ok,
        "geometry_and_codec_ok": "video_codec_or_pix_fmt_mismatch" not in failure_reasons and "video_dimensions_mismatch" not in failure_reasons and "video_fps_mismatch" not in failure_reasons,
        "frame_count_matches_duration": frame_count_ok,
        "strictly_under_180s": 0.0 < duration_sec < 180.0,
        "audio_aac_and_sample_nonclipping": "audio_missing_silent_clipped_or_non_aac" not in failure_reasons,
        "stereo_true_peak_certified": False,
        "visual_and_listening_review_verified": False,
        "video": video,
        "audio": audio,
        "channel_sample_peaks": channel_peaks,
        "black_segment_count": len(black_segments),
        "freeze_segment_count": len(freeze_segments),
        "failure_reasons": failure_reasons,
        "extracted_frames": extracted_frames,
        "status": "TECHNICAL_DECODE_PASSED_REVIEW_REQUIRED" if passed else "FAILED_TECHNICAL_VERIFICATION",
    }


def check_duplicate_delivery(candidate_sha256: str, existing_sha256_set: Sequence[str]) -> dict[str, Any]:
    """Fail-closed SHA256 deduplication check before Drive or YouTube upload."""
    normalized = candidate_sha256.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise ValueError("candidate_sha256 must be a 64-hex SHA256 digest")
    known = {h.strip().lower() for h in existing_sha256_set if str(h).strip()}
    is_dup = normalized in known
    return {"candidate_sha256": normalized, "duplicate_detected": is_dup, "allow_upload": not is_dup}


def plan_daily_publish_slots(
    count: int,
    *,
    storage_dir: Optional[str | Path] = None,
    start_date: Optional[datetime] = None,
    time_slots_et: Sequence[str] = ("12:00",),
    allow_unqualified_tracker_preview: bool = False,
) -> list[dict[str, Any]]:
    """Browser-free 1/day Antifa FM slot preview reusing ScheduleTracker.preview_copy()."""
    if count < 1 or count > 30:
        raise ValueError("count must be 1..30")
    from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import ScheduleTracker

    base_tracker = ScheduleTracker(
        ANTIFAFM_CANONICAL_CHANNEL_ID,
        storage_dir=Path(storage_dir) if storage_dir is not None else None,
        persist=False,
    )
    preview = base_tracker.preview_copy()
    if not preview.calendar_ready and allow_unqualified_tracker_preview is not True:
        raise RuntimeError(
            "Live Studio Scheduled inventory is unqualified; pass allow_unqualified_tracker_preview=True "
            "only for offline dry-run simulation"
        )
    planned: list[dict[str, Any]] = []
    slots_list = list(time_slots_et) or ["12:00"]
    for idx in range(count):
        slot = preview.get_next_available_slot(slots_list, max_per_day=1, start_date=start_date, channel_tz="America/New_York")
        if slot is None:
            raise RuntimeError("No available daily scheduling slot within 60-day window")
        date_str, time_str = slot
        preview.increment(date_str, video_id=f"dryrun_{idx:04d}")
        planned.append(
            {
                "channel_id": ANTIFAFM_CANONICAL_CHANNEL_ID,
                "date": date_str,
                "time_et": time_str,
                "max_per_day": 1,
                "calendar_inventory_qualified": bool(preview.calendar_ready),
                "mode": "dry_run_preview_only",
            }
        )
    return planned


def stage_antifafm_daily_candidate(
    video_path: str | Path,
    *,
    channel_id: str,
    existing_sha256_set: Sequence[str] = (),
    storage_dir: Optional[str | Path] = None,
    start_date: Optional[datetime] = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Stage a technically decoded vertical MP4 for 1/day Antifa FM preview without live YouTube/browser."""
    if channel_id != ANTIFAFM_CANONICAL_CHANNEL_ID:
        raise PermissionError(f"Refusing non-AntifaFM channel {channel_id!r}; expected {ANTIFAFM_CANONICAL_CHANNEL_ID}")
    if dry_run is not True:
        raise PermissionError(
            "Live scheduled release is gated off in staging; dry_run must be literal True until "
            "Antifa FM OAuth set, YT_ALLOW_SCHEDULED_PUBLISH_AT, complete calendar inventory, and schedule readback are admitted"
        )

    verification = verify_rendered_output(video_path)
    if verification["status"] != "TECHNICAL_DECODE_PASSED_REVIEW_REQUIRED":
        raise ValueError(f"Candidate video failed technical verification: {verification['failure_reasons']}")

    dedup = check_duplicate_delivery(verification["sha256"], existing_sha256_set)
    if not dedup["allow_upload"]:
        raise FileExistsError(f"Duplicate candidate SHA256 refused: {verification['sha256']}")

    next_slot = plan_daily_publish_slots(
        1,
        storage_dir=storage_dir,
        start_date=start_date,
        allow_unqualified_tracker_preview=True,
    )[0]
    return {
        "status": "DRY_RUN_STAGED_NO_LIVE_INSERT",
        "channel_id": ANTIFAFM_CANONICAL_CHANNEL_ID,
        "artifact_sha256": verification["sha256"],
        "planned_daily_slot": next_slot,
        "verification": verification,
        "service_constructed": False,
        "live_insert_attempted": False,
    }
