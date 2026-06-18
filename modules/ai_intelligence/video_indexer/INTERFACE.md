# Video Indexer Interface

**WSP Compliance**: WSP 11 (Interface Protocol), WSP 49 (Module Structure)

## CLI Interface (Agent-Callable)

```bash
# Index all videos for a channel
python -m modules.ai_intelligence.video_indexer.cli --channel undaodu

# Index specific video
python -m modules.ai_intelligence.video_indexer.cli --channel move2japan --video-id abc123

# Check indexing status
python -m modules.ai_intelligence.video_indexer.cli --status

# List indexed videos for channel
python -m modules.ai_intelligence.video_indexer.cli --channel undaodu --list

# Force reindex (ignore existing)
python -m modules.ai_intelligence.video_indexer.cli --channel move2japan --reindex
```

### CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--channel`, `-c` | str | required | Channel: move2japan, undaodu, foundups, ravingantifa |
| `--video-id`, `-v` | str | - | Specific video ID to index |
| `--batch-size`, `-b` | int | 10 | Videos per batch |
| `--status`, `-s` | flag | - | Show indexing status |
| `--list`, `-l` | flag | - | List indexed videos |
| `--reindex` | flag | - | Force reindex existing |
| `--skip-holoindex` | flag | - | Skip ChromaDB (JSON only) |
| `--verbose` | flag | - | Verbose logging |

---

## Public API

### VideoIndexer (Main Orchestrator)

```python
from modules.ai_intelligence.video_indexer.src.video_indexer import VideoIndexer

class VideoIndexer:
    """
    Main orchestrator for video content indexing.

    Coordinates audio, visual, and multimodal analysis pipelines.
    """

    def __init__(
        self,
        channel: str,                    # "move2japan" | "undaodu" | "foundups"
        chroma_path: str = None,         # ChromaDB path (default: holo_index/chroma_store)
        artifact_path: str = None,       # JSON output path (default: video_index/)
        auto_launch: bool = True         # Auto-launch browser if not running
    ):
        """Initialize indexer for specific channel."""

    def index_video(
        self,
        video_id: str,                   # YouTube video ID
        include_visual: bool = True,     # Process visual frames
        include_clips: bool = True,      # Generate clip candidates
        force_reindex: bool = False      # Re-process even if exists
    ) -> IndexResult:
        """Index single video across all modalities."""

    def index_channel(
        self,
        max_videos: int = 50,            # Limit videos to process
        filter_type: str = "shorts",     # "shorts" | "videos" | "all"
        since_date: str = None           # Only videos after date
    ) -> List[IndexResult]:
        """Index multiple videos from channel."""

    def search(
        self,
        query: str,                      # Natural language query
        modality: str = "all",           # "audio" | "visual" | "all"
        top_k: int = 10,                 # Number of results
        min_relevance: float = 0.7       # Minimum similarity score
    ) -> List[SearchResult]:
        """Search indexed content across modalities."""
```

### AudioAnalyzer

```python
from modules.ai_intelligence.video_indexer.src.audio_analyzer import AudioAnalyzer

class AudioAnalyzer:
    """
    Audio content analysis: ASR, diarization, NLP extraction.

    Extends batch_transcriber.py with speaker identification.
    """

    def __init__(
        self,
        whisper_model: str = "base",     # Whisper model size
        enable_diarization: bool = True  # Speaker identification
    ):
        """Initialize audio analyzer."""

    def transcribe(
        self,
        audio_path: str                  # Path to audio file
    ) -> TranscriptResult:
        """Transcribe audio with timestamps."""

    def extract_quotes(
        self,
        transcript: TranscriptResult,
        min_length: int = 10,            # Minimum quote words
        max_length: int = 50             # Maximum quote words
    ) -> List[Quote]:
        """Extract notable quotes from transcript."""

    def identify_topics(
        self,
        transcript: TranscriptResult
    ) -> List[Topic]:
        """Extract topics using NLP."""
```

### VisualAnalyzer

```python
from modules.ai_intelligence.video_indexer.src.visual_analyzer import VisualAnalyzer

class VisualAnalyzer:
    """
    Visual content analysis: shots, faces, objects.
    """

    def __init__(
        self,
        frame_interval: float = 1.0,     # Seconds between frame samples
        enable_face_detection: bool = True
    ):
        """Initialize visual analyzer."""

    def extract_keyframes(
        self,
        video_path: str
    ) -> List[Keyframe]:
        """Extract representative frames from video."""

    def detect_shots(
        self,
        video_path: str,
        threshold: float = 0.3           # Scene change threshold
    ) -> List[Shot]:
        """Detect shot boundaries."""

    def analyze_frame(
        self,
        frame: np.ndarray
    ) -> FrameAnalysis:
        """Analyze single frame for faces, objects, text."""
```

### MultimodalAligner

```python
from modules.ai_intelligence.video_indexer.src.multimodal_aligner import MultimodalAligner

class MultimodalAligner:
    """
    Cross-modal alignment: sync audio moments with visual content.
    """

    def align_moments(
        self,
        audio_analysis: AudioAnalysis,
        visual_analysis: VisualAnalysis
    ) -> List[Moment]:
        """Align audio and visual moments."""

    def detect_highlights(
        self,
        moments: List[Moment],
        min_score: float = 0.8           # Highlight threshold
    ) -> List[Highlight]:
        """Detect high-engagement moments."""
```

### ClipGenerator

```python
from modules.ai_intelligence.video_indexer.src.clip_generator import ClipGenerator

class ClipGenerator:
    """
    Generate clip candidates for short-form content.
    """

    def generate_candidates(
        self,
        moments: List[Moment],
        min_duration: float = 15.0,      # Minimum clip seconds
        max_duration: float = 60.0       # Maximum clip seconds
    ) -> List[ClipCandidate]:
        """Generate clip candidates from moments."""

    def score_virality(
        self,
        clip: ClipCandidate
    ) -> float:
        """Score clip for viral potential (0-1)."""
```

### VideoIndexStore

```python
from modules.ai_intelligence.video_indexer.src.video_index_store import VideoIndexStore

class VideoIndexStore:
    """
    JSON artifact storage for video index data.
    """

    def __init__(
        self,
        base_path: str = "video_index"   # Output directory
    ):
        """Initialize store."""

    def save_index(
        self,
        video_id: str,
        index_data: IndexData
    ) -> str:
        """Save index to JSON, update metadata catalog, return path."""

    def load_index(
        self,
        video_id: str
    ) -> Optional[IndexData]:
        """Load existing index if available."""

    def list_indexed(
        self,
        channel: str = None              # Filter by channel
    ) -> List[str]:
        """List all indexed video IDs."""
```

### StudioAskIndexer (Browser-Based)

```python
from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import (
    run_video_indexing_cycle,
    run_indexing_daemon,
)

async def run_video_indexing_cycle(
    driver=None,
    channels: Optional[List[str]] = None,
    max_videos_per_channel: int = 3,
    browser: str = "chrome",
) -> Dict[str, Any]:
    """Run a single Ask-Gemini indexing cycle with progress telemetry."""

async def run_indexing_daemon(
    channels: Optional[List[str]] = None,
    max_videos_per_channel: int = 3,
    browser: str = "chrome",
    interval_minutes: int = 60,
    max_cycles: Optional[int] = None,
) -> Dict[str, Any]:
    """Run continuous indexing cycles with STOP/REINDEX signals."""
```

### Action Surface (typed SKILLz/ACTION SURFACE - Phase 1)

A typed, reusable capability surface so the CLI menu, OpenClaw/WRE, Hermes, or
any 0102 agent invoke the SAME governed indexing capability by action ID
instead of a one-off helper.

```python
from modules.ai_intelligence.video_indexer.src.action_surface import (
    VideoIndexAction,            # typed action IDs (string constants)
    StudioAskSingleVideoInput,   # typed input dataclass
    StudioAskSingleVideoOutput,  # typed output dataclass
    run_action,                  # dispatcher: run_action(action_id, **kwargs)
    run_studio_ask_single_video, # direct entry for the single_video action
    parse_video_id,              # raw ID or URL -> bare video ID
    port_for_browser,            # 'chrome'->9222, 'edge'->9223
    BROWSER_PORTS,
    ALL_ACTION_IDS,
    IMPLEMENTED_ACTION_IDS,
    REGISTERED_ONLY_ACTION_IDS,
)

# Action IDs
#   IMPLEMENTED (Phase 1):
#     VideoIndexAction.STUDIO_ASK_SINGLE_VIDEO = "video_index.studio_ask.single_video"
#   REGISTERED ONLY (NOT wired this phase -> 'not_implemented'):
#     STUDIO_ASK_CHANNEL_CYCLE = "video_index.studio_ask.channel_cycle"
#     STUDIO_ASK_DAEMON_CYCLE  = "video_index.studio_ask.daemon_cycle"
#     GEMINI_API_SINGLE_VIDEO  = "video_index.gemini_api.single_video"
#     WHISPER_LOCAL_TRANSCRIPT = "video_index.whisper.local_transcript"
#     SHORTS_SCHEDULER_CONSUME = "shorts_scheduler.consume_video_index"

@dataclass
class StudioAskSingleVideoInput:
    video_id: str               # raw ID OR a URL (parsed to bare ID)
    browser: str = "chrome"     # 'chrome' (9222) | 'edge' (9223)
    channel_id: Optional[str] = None
    persist: bool = True        # write memory/video_index/{channel}/{video_id}.json

@dataclass
class StudioAskSingleVideoOutput:
    success: bool
    video_id: str
    browser: str
    provider: str = "studio_ask"
    response_text_length: int = 0
    topics_count: int = 0
    saved_path: Optional[str] = None
    error: Optional[str] = None

async def run_studio_ask_single_video(
    inp: StudioAskSingleVideoInput,
) -> StudioAskSingleVideoOutput:
    """Bounded single-video Studio Ask index. Routes ONLY to
    StudioAskIndexer.ask_about_video (navigate + DOM scrape). NEVER calls the
    Gemini API, the Shorts Scheduler, or any publish/schedule/metadata-mutation
    path. Attaches to an already-authenticated browser session (no credentials).
    Fail-closed on error.

    STUDIO_ASK_CHANNEL_CONTEXT_PHASE1: the existing channel_id input is now
    REQUIRED for the single-video path (the worker sets the OWNING-channel
    context before asking). The action ID and the output schema are UNCHANGED;
    only new typed error VALUES are added to the existing 'error' field:
      - 'channel_unresolved'        - channel_id missing/blank/unknown
      - 'studio_target_unavailable' - no usable Studio/normal browser target
                                      (e.g. only a chrome://glic / Gemini side
                                      panel was open and no normal tab could be
                                      opened via the existing driver)
      - 'wrong_channel_context'     - the owning-channel edit surface did not
                                      load (permission/not-found/sign-in/Oops or
                                      absent title field after the timeout)
    On any of these the result is success=False and NOTHING is persisted."""

async def run_action(action_id: str, **kwargs) -> Any:
    """Route by typed action ID. Implemented IDs run real work; registered-only
    IDs return a 'not_implemented' result; unknown IDs raise ValueError."""
```

## Data Classes

```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class IndexResult:
    video_id: str
    channel: str
    title: str
    duration: float
    indexed_at: datetime
    audio_segments: int
    visual_frames: int
    clip_candidates: int
    success: bool
    error: Optional[str] = None

@dataclass
class SearchResult:
    video_id: str
    timestamp: float
    content: str
    modality: str          # "audio" | "visual" | "multimodal"
    relevance: float
    context: str           # Surrounding content

@dataclass
class Quote:
    text: str
    start_time: float
    end_time: float
    speaker: Optional[str]
    sentiment: float       # -1 to 1

@dataclass
class Moment:
    start_time: float
    end_time: float
    audio_content: str
    visual_description: str
    engagement_score: float

@dataclass
class ClipCandidate:
    start_time: float
    end_time: float
    title_suggestion: str
    hook: str              # Opening line
    virality_score: float
    moments: List[Moment]
```

## Error Handling

```python
class VideoIndexerError(Exception):
    """Base exception for video indexer."""

class VideoNotFoundError(VideoIndexerError):
    """Video ID not found on YouTube."""

class TranscriptionError(VideoIndexerError):
    """Audio transcription failed."""

class BrowserConnectionError(VideoIndexerError):
    """Could not connect to browser (Chrome/Edge)."""
```

## Event Hooks

```python
# Progress callbacks for long-running operations
indexer.on_progress = lambda pct, msg: print(f"{pct}%: {msg}")
indexer.on_video_complete = lambda result: log_result(result)
indexer.on_error = lambda error: handle_error(error)
```
