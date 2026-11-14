"""
YouTube Shorts AI Generator Module

Autonomous AI-powered YouTube Shorts creation using Google Veo 3.
Standalone module with read-only integration to existing youtube_auth.

WSP Compliance: WSP 3, 49, 80, 54
"""

from .shorts_orchestrator import ShortsOrchestrator
from .veo3_generator import Veo3Generator
from .sora2_generator import Sora2Generator
from .youtube_uploader import YouTubePublishResult, YouTubeShortsUploader, YouTubeUploadError
from .shorts_dae import ShortsDAE
from .shorts_pipeline import (
    ShortsBuildResult,
    ShortClipSelection,
    build_short_from_index,
    build_short_from_index_auto,
    find_latest_index_video_id,
    mark_index_short_built,
)

__all__ = [
    'ShortsOrchestrator',
    'Veo3Generator',
    'Sora2Generator',
    'YouTubeShortsUploader',
    'YouTubePublishResult',
    'YouTubeUploadError',
    'ShortsDAE',
    'ShortsBuildResult',
    'ShortClipSelection',
    'build_short_from_index',
    'build_short_from_index_auto',
    'find_latest_index_video_id',
    'mark_index_short_built',
]

__version__ = '0.1.0'
__status__ = 'POC'
