# -*- coding: utf-8 -*-
"""Deterministic offline tests for headless_video_orchestrator and Antifa FM staging."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess

import pytest

from modules.communication.headless_video_orchestrator.src import (
    ANTIFAFM_CANONICAL_CHANNEL_ID,
    CutSpec,
    HeadlessVideoOrchestrator,
    MusicVideoBuildError,
    MusicVideoRequest,
    analyze_audio_16k_mono,
    audit_satire_claims,
    check_duplicate_delivery,
    compare_audio_sources,
    parse_embedded_srt,
    plan_daily_publish_slots,
    probe_media_artifact,
    render_benchmark_excerpt,
    stage_antifafm_daily_candidate,
    verify_rendered_output,
)


def _make_textured_png(path: Path, width: int, height: int, seed_freq: int = 1) -> Path:
    """Create non-black textured test raster so blackdetect/freezedetect are genuinely exercised."""
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"testsrc2=s={width}x{height}:d=0.2:r=10",
            "-vf", f"hue=h={seed_freq * 45}",
            "-frames:v", "1", str(path),
        ],
        check=True,
        timeout=30,
    )
    return path


def _make_audio_pair(tmp_path: Path, duration_sec: float = 16.0) -> tuple[Path, Path]:
    wav = tmp_path / "tone.wav"
    m4a = tmp_path / "tone.m4a"
    mp3 = tmp_path / "tone.mp3"
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi",
            "-i", f"sine=frequency=220:sample_rate=48000:duration={duration_sec}",
            "-af", "volume='0.35+0.25*sin(2*PI*2*t)':eval=frame",
            str(wav),
        ],
        check=True,
        timeout=30,
    )
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav), "-c:a", "aac", "-b:a", "192k", str(m4a)],
        check=True,
        timeout=30,
    )
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav), "-c:a", "libmp3lame", "-b:a", "192k", str(mp3)],
        check=True,
        timeout=30,
    )
    return m4a, mp3


def test_parse_embedded_srt_separates_lyrics_from_stage_directions():
    sample_srt = (
        "1\n00:00:23,589 --> 00:00:23,589\n[Intro]\n\n"
        "2\n00:00:23,589 --> 00:00:26,238\nAn atheist monk with a microphone stand\n\n"
        "3\n00:00:26,238 --> 00:00:29,107\nLooked out at the pundits across the whole land\n\n"
        "4\n00:03:04,463 --> 00:03:08,967\n[End]\n"
    )
    parsed = parse_embedded_srt(sample_srt, max_audio_duration_sec=209.56)
    assert parsed["total_cues"] == 4
    assert parsed["positive_lyric_cue_count"] == 2
    assert parsed["stage_direction_count"] == 2
    assert parsed["zero_duration_stage_direction_count"] == 1
    assert parsed["overlap_count"] == 0
    assert parsed["beyond_audio_count"] == 0
    assert parsed["audio_alignment_verified"] is False


def test_audio_probe_comparison_and_honest_rms_diff_quantiles(tmp_path):
    m4a, mp3 = _make_audio_pair(tmp_path, duration_sec=6.0)
    probe = probe_media_artifact(m4a)
    assert probe["has_embedded_subtitles"] is False
    assert probe["subtitle_streams"] == []

    comp = compare_audio_sources(m4a, mp3)
    assert comp["byte_identical"] is False
    assert comp["rms_envelope_correlation"] >= 0.985
    assert comp["content_equivalent"] is True

    signal = analyze_audio_16k_mono(m4a, quantile=0.85)
    assert signal["sample_rate"] == 16000
    assert signal["mono_clipped_samples"] == 0
    assert signal["signal_metric"] == "normalized_rms_positive_first_difference"
    assert signal["rms_positive_diff_quantile_threshold"] > 0.0
    assert signal["selection_threshold_validated"] is False
    assert signal["musical_ending_verified"] is False
    assert signal["candidate_excerpt"]["strictly_under_180s"] is True


def test_satire_claim_provenance_gate_blocks_unverified_facts_and_affiliations():
    audit = audit_satire_claims(
        [
            {"claim_id": "c1", "text": "Cable anchors clutch giant toy pearls", "category": "parody_opinion"},
            {"claim_id": "c2", "text": "Dial 555-0102 imaginary hotline", "category": "phone_number", "fictionalized": True},
            {"claim_id": "c3", "text": "87.3% of bills vanish", "category": "numeric_stat"},
            {"claim_id": "c4", "text": "The Onion Official Presents", "category": "parody_opinion"},
            {"claim_id": "c5", "text": "Senator X committed felony bribery", "category": "allegation", "fictionalized": True},
        ]
    )
    assert audit["ok"] is False
    assert audit["blocked_claim_ids"] == ["c3", "c4", "c5"]


def test_ab_hybrid_benchmark_enforces_sharpness_unreviewed_motion_and_rejects_black_or_frozen(tmp_path):
    m4a, _ = _make_audio_pair(tmp_path, duration_sec=16.0)
    low_atlas = _make_textured_png(tmp_path / "low_atlas.png", 800, 1400, seed_freq=1)
    hi_stage = _make_textured_png(tmp_path / "hi_stage.png", 1600, 2800, seed_freq=2)
    pose_1 = _make_textured_png(tmp_path / "pose1.png", 720, 1280, seed_freq=3)
    pose_2 = _make_textured_png(tmp_path / "pose2.png", 720, 1280, seed_freq=5)
    mismatched_small = _make_textured_png(tmp_path / "small_pose.png", 360, 640, seed_freq=6)

    # Secondary pose with mismatched dimensions must be rejected!
    with pytest.raises(ValueError, match="mismatched frame dimensions"):
        render_benchmark_excerpt(
            variant_id="bad_secondary_pose",
            audio_path=m4a,
            cuts=[CutSpec(scene_id="bad", start_sec=0.0, duration_sec=1.5, source_paths=(str(pose_1), str(mismatched_small)))],
            output_path=tmp_path / "bad.mp4",
        )

    out_b = tmp_path / "variant_b.mp4"
    manifest_b = render_benchmark_excerpt(
        variant_id="B_shared_atlas_camera",
        audio_path=m4a,
        cuts=[
            CutSpec(
                scene_id="b_cut1",
                start_sec=0.0,
                duration_sec=2.0,
                source_paths=(str(low_atlas),),
                crop_box=(0, 0, 400, 700),
                zoom_ratio=1.035,
                pan_dx_px=16,
                lyric_cue="An atheist monk with a microphone stand",
                lyric_source="embedded_stream",
            )
        ],
        output_path=out_b,
    )
    cut_b = manifest_b["cuts"][0]
    assert cut_b["motion_class"] == "camera_only"
    assert cut_b["true_character_animation"] is False
    assert cut_b["sharpness"]["upscale_interpolation_warning"] is True
    assert manifest_b["rsi_promotion_status"] == "candidate_unpromoted"
    assert manifest_b["verification"]["status"] == "TECHNICAL_DECODE_PASSED_REVIEW_REQUIRED"

    out_c = tmp_path / "variant_c.mp4"
    manifest_c = render_benchmark_excerpt(
        variant_id="C_hybrid_stage_sprites",
        audio_path=m4a,
        cuts=[
            CutSpec(
                scene_id="c_wide",
                start_sec=0.0,
                duration_sec=1.5,
                source_paths=(str(hi_stage),),
                crop_box=(0, 0, 800, 1400),
                zoom_ratio=1.035,
                pan_dx_px=12,
            ),
            CutSpec(
                scene_id="c_action",
                start_sec=1.5,
                duration_sec=1.5,
                source_paths=(str(pose_1), str(pose_2)),
                stepped_fps=12,
            ),
        ],
        output_path=out_c,
    )
    assert manifest_c["cuts"][0]["sharpness"]["upscale_interpolation_warning"] is False
    assert manifest_c["cuts"][0]["motion_class"] == "camera_only"
    # Multi-hash sequence stays unreviewed (never auto-claims true_character_animation=True!)
    assert manifest_c["cuts"][1]["motion_class"] == "multi_image_sequence_unreviewed"
    assert manifest_c["cuts"][1]["true_character_animation"] is False

    # All-black frozen video MUST fail verify_rendered_output and stage_antifafm_daily_candidate
    black_mp4 = tmp_path / "all_black_frozen.mp4"
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=black:s=720x1280:d=3.0:r=24",
            "-i", str(m4a), "-t", "3.0",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", str(black_mp4),
        ],
        check=True,
        timeout=30,
    )
    black_ver = verify_rendered_output(black_mp4)
    assert black_ver["status"] == "FAILED_TECHNICAL_VERIFICATION"
    assert "black_segments_detected" in black_ver["failure_reasons"]
    assert "frozen_segments_detected" in black_ver["failure_reasons"]

    tracker_dir = tmp_path / "tracker"
    start_dt = datetime(2026, 11, 20, 12, 0, 0)
    with pytest.raises(ValueError, match="black_segments_detected"):
        stage_antifafm_daily_candidate(black_mp4, channel_id=ANTIFAFM_CANONICAL_CHANNEL_ID, storage_dir=tracker_dir, start_date=start_dt)

    # Unqualified calendar preview requires explicit opt-in flag
    with pytest.raises(RuntimeError, match="unqualified"):
        plan_daily_publish_slots(1, storage_dir=tracker_dir, start_date=start_dt)

    # Strict dry_run=True check (rejects False and string "false")
    with pytest.raises(PermissionError, match="non-AntifaFM"):
        stage_antifafm_daily_candidate(out_c, channel_id="UCSNTUXjAgpd4sgWYP0xoJgw", storage_dir=tracker_dir, start_date=start_dt)
    for bad_dry_run in (False, "false"):
        with pytest.raises(PermissionError, match="gated off"):
            stage_antifafm_daily_candidate(out_c, channel_id=ANTIFAFM_CANONICAL_CHANNEL_ID, storage_dir=tracker_dir, start_date=start_dt, dry_run=bad_dry_run)  # type: ignore[arg-type]

    staged = stage_antifafm_daily_candidate(out_c, channel_id=ANTIFAFM_CANONICAL_CHANNEL_ID, storage_dir=tracker_dir, start_date=start_dt)
    assert staged["status"] == "DRY_RUN_STAGED_NO_LIVE_INSERT"
    assert staged["planned_daily_slot"]["calendar_inventory_qualified"] is False
    assert staged["service_constructed"] is False
    assert staged["live_insert_attempted"] is False

    with pytest.raises(FileExistsError, match="Duplicate"):
        stage_antifafm_daily_candidate(
            out_c,
            channel_id=ANTIFAFM_CANONICAL_CHANNEL_ID,
            existing_sha256_set=[staged["artifact_sha256"]],
            storage_dir=tracker_dir,
            start_date=start_dt,
        )
    assert not check_duplicate_delivery(staged["artifact_sha256"], [staged["artifact_sha256"]])["allow_upload"]


def test_orchestrator_validates_profile_before_ffmpeg_and_formats_720p(tmp_path, monkeypatch):
    m4a, _ = _make_audio_pair(tmp_path, duration_sec=3.0)
    clip = tmp_path / "clip_with_wrong_audio.mp4"
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=s=640x360:d=2.0:r=24",
            "-f", "lavfi", "-i", "sine=frequency=880:duration=2.0",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(clip),
        ],
        check=True,
        timeout=30,
    )
    orch = HeadlessVideoOrchestrator()
    called = []
    orig_overlay = orch._overlay_audio
    monkeypatch.setattr(orch, "_overlay_audio", lambda **kw: (called.append(kw), orig_overlay(**kw))[1])

    with pytest.raises(MusicVideoBuildError, match="4K"):
        orch.build_music_video(MusicVideoRequest(audio_path=str(m4a), visual_paths=[str(clip)], output_dir=str(tmp_path), render_profile="4k"))
    with pytest.raises(MusicVideoBuildError, match="180.0"):
        orch.build_music_video(
            MusicVideoRequest(
                audio_path=str(m4a),
                visual_paths=[str(clip)],
                output_dir=str(tmp_path),
                aspect="shorts",
                render_profile="staging_720p",
                max_duration_sec=180.0,
            )
        )
    # Upfront validation must fail BEFORE _overlay_audio spawns any subprocess!
    assert called == []

    out = orch.build_music_video(
        MusicVideoRequest(
            audio_path=str(m4a),
            visual_paths=[str(clip)],
            output_dir=str(tmp_path / "out"),
            aspect="shorts",
            render_profile="staging_720p",
            max_duration_sec=2.0,
            audio_fade_out_sec=0.4,
        )
    )
    verified = verify_rendered_output(out.output_path, expected_width=720, expected_height=1280, expected_fps=24.0)
    assert verified["status"] == "TECHNICAL_DECODE_PASSED_REVIEW_REQUIRED"
