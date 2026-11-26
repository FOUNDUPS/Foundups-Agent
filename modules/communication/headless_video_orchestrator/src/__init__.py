"""
Headless Video Orchestrator exports.
"""

from .orchestrator import (
    HeadlessVideoOrchestrator,
    MusicVideoRequest,
    MusicVideoOutput,
    MusicVideoBuildError,
)
from .oss_adapters import run_ai_shorts_generator, ExternalToolError
from .antifafm_staging import (
    ANTIFAFM_CANONICAL_CHANNEL_ID,
    CutSpec,
    analyze_audio_16k_mono,
    audit_satire_claims,
    check_duplicate_delivery,
    compare_audio_sources,
    parse_embedded_srt,
    plan_daily_publish_slots,
    probe_media_artifact,
    render_benchmark_excerpt,
    sha256_file,
    stage_antifafm_daily_candidate,
    verify_rendered_output,
)

__all__ = [
    "HeadlessVideoOrchestrator",
    "MusicVideoRequest",
    "MusicVideoOutput",
    "MusicVideoBuildError",
    "run_ai_shorts_generator",
    "ExternalToolError",
    "ANTIFAFM_CANONICAL_CHANNEL_ID",
    "CutSpec",
    "analyze_audio_16k_mono",
    "audit_satire_claims",
    "check_duplicate_delivery",
    "compare_audio_sources",
    "parse_embedded_srt",
    "plan_daily_publish_slots",
    "probe_media_artifact",
    "render_benchmark_excerpt",
    "sha256_file",
    "stage_antifafm_daily_candidate",
    "verify_rendered_output",
]
