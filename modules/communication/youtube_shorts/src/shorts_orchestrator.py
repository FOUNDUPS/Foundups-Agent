"""
YouTube Shorts Orchestrator

Manages the complete Shorts creation flow:
1. Topic input
2. Optional prompt enhancement
3. Veo 3 or Sora2 generates video
4. Upload to YouTube
5. Return published URL

WSP Compliance:
- Comprehensive daemon logging for full flow monitoring
- Step-by-step tracking from topic to YouTube upload
- Integration with main.py DAE logging system
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict
from .veo3_generator import Veo3Generator, Veo3GenerationError, InsufficientCreditsError
from .sora2_generator import Sora2GenerationError
from .youtube_uploader import YouTubeShortsUploader, YouTubeUploadError, YouTubeUploadPolicyBlocked

# Initialize logger for daemon monitoring
logger = logging.getLogger(__name__)


class ShortsOrchestrator:
    """
    Main orchestration for autonomous YouTube Shorts creation.

    Coordinates the full flow from topic input to YouTube upload.
    """

    def __init__(self, channel: str = "move2japan", default_engine: str = "veo3"):
        """
        Initialize orchestrator with generator and uploader.

        Args:
            channel: YouTube channel to use ("move2japan" or "undaodu")
                    Default: "move2japan" for Move2Japan talking baby Shorts
            default_engine: Preferred generator ('veo3', 'sora2', or 'auto')
        """

        logger.info("[U+1F3AC] [SHORTS-INIT] Initializing YouTube Shorts Orchestrator")
        logger.info(f"[U+1F4FA] [SHORTS-INIT] Target channel: {channel.upper()}")

        self.default_engine = (default_engine or "veo3").lower()
        if self.default_engine not in {"veo3", "sora2", "auto"}:
            logger.warning("[SHORTS-INIT] Unknown engine '%s', defaulting to Veo3", self.default_engine)
            self.default_engine = "veo3"

        self.generators: Dict[str, object] = {}
        bootstrap_engine = "veo3" if self.default_engine == "auto" else self.default_engine
        try:
            self.generator = self._get_generator(bootstrap_engine)
            self.last_engine_used = bootstrap_engine
        except ImportError as exc:
            if bootstrap_engine != "veo3":
                raise
            logger.warning("[SHORTS-INIT] Veo3 unavailable (%s); falling back to Sora2", exc)
            self.default_engine = "sora2"
            self.generator = self._get_generator("sora2")
            self.last_engine_used = "sora2"

        self.uploader = YouTubeShortsUploader(channel=channel)
        self.channel = channel

        # Memory for tracking created Shorts
        module_root = Path(__file__).parent.parent
        self.memory_file = module_root / "memory" / "generated_shorts.json"
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing memory
        self.shorts_memory = self._load_memory()

        logger.info(f"[U+2701] [SHORTS-INIT] Orchestrator initialized for {channel.upper()}")
        logger.info(f"[U+1F4BE] [SHORTS-INIT] Memory: {len(self.shorts_memory)} Shorts tracked")
        logger.info(f"[U+1F4C1] [SHORTS-INIT] Memory file: {self.memory_file}")

    def _load_memory(self) -> list:
        """Load Shorts memory from JSON file."""
        if self.memory_file.exists():
            with open(self.memory_file) as f:
                return json.load(f)
        return []

    def _save_memory(self):
        """Save Shorts memory to JSON file."""
        with open(self.memory_file, 'w') as f:
            json.dump(self.shorts_memory, f, indent=2)

    def _select_engine(self, topic: str, requested: Optional[str] = None) -> str:
        """Determine which generator engine to use for a given topic."""

        if requested:
            normalized = requested.lower()
            if normalized == 'auto':
                return self._suggest_engine(topic)
            if normalized in {'veo3', 'sora2'}:
                return normalized
            logger.warning("[SHORTS-ENGINE] Unknown requested engine '%s' - falling back", requested)

        if self.default_engine == 'sora2':
            return 'sora2'

        suggested = self._suggest_engine(topic)
        if suggested == 'sora2':
            return 'sora2'

        return 'veo3'

    def _suggest_engine(self, topic: str) -> str:
        """Heuristic auto-selection between Veo3 and Sora2."""

        topic_lower = topic.lower()
        sora_keywords = {"live action", "photorealistic", "realistic", "cinematic", "documentary", "hyperreal", "movie", "film", "human"}
        if any(keyword in topic_lower for keyword in sora_keywords):
            return 'sora2'

        return 'veo3'

    def _get_generator(self, engine: str):
        """
        Lazy-load generator instances with graceful fallbacks.

        Catches ImportError specifically to handle missing dependencies.
        Falls back from Veo3 -> Sora2 automatically if Veo3 unavailable.
        Prevents infinite recursion if both generators fail.
        """
        import sys

        normalized = (engine or 'veo3').lower()
        if normalized == 'auto':
            normalized = self._suggest_engine('')

        # Return cached generator if available
        if normalized in self.generators:
            logger.debug(f"[SHORTS-ENGINE] [OK] Using cached {normalized.upper()} generator (no import needed)")
            return self.generators[normalized]

        logger.info(f"[SHORTS-ENGINE] [SEARCH] Requesting {normalized.upper()} generator")
        logger.debug(f"[SHORTS-ENGINE] Currently cached generators: {list(self.generators.keys())}")

        # Not cached - need to load
        logger.info(f"[SHORTS-ENGINE] [BOX] Loading {normalized.upper()} generator for first time...")
        logger.debug(f"[SHORTS-ENGINE] Python: {sys.executable}")

        try:
            if normalized == 'sora2':
                logger.info(f"[SHORTS-ENGINE] [TOOL] Importing Sora2Generator from sora2_generator.py...")
                from .sora2_generator import Sora2Generator
                logger.info(f"[SHORTS-ENGINE] [TOOL] Instantiating Sora2Generator()...")
                generator = Sora2Generator()
                logger.info(f"[SHORTS-ENGINE] [OK] Sora2Generator loaded successfully")
            else:
                # Veo3Generator already imported at top
                logger.info(f"[SHORTS-ENGINE] [TOOL] Instantiating Veo3Generator() (already imported at module top)...")
                generator = Veo3Generator()
                logger.info(f"[SHORTS-ENGINE] [OK] Veo3Generator loaded successfully")

        except ImportError as exc:
            # SPECIFIC: Catch dependency import errors (google.genai, etc.)
            logger.error(f"[SHORTS-ENGINE] [FAIL] {normalized.upper()} ImportError: {exc}")
            logger.error(f"[SHORTS-ENGINE] [PIN] Error type: {type(exc).__name__}")
            logger.error(f"[SHORTS-ENGINE] [PIN] Error details: {str(exc)}")

            # Prevent infinite recursion: only fallback if not already trying Sora2
            if normalized == 'veo3':
                logger.warning(f"[SHORTS-ENGINE] [REFRESH] FALLBACK TRIGGERED: Veo3 -> Sora2")
                logger.warning(f"[SHORTS-ENGINE] [REFRESH] Reason: Veo3 dependencies missing ({exc})")
                logger.warning(f"[SHORTS-ENGINE] [REFRESH] Attempting Sora2 as fallback...")
                return self._get_generator('sora2')  # One-time fallback
            else:
                # Both generators failed - re-raise with helpful message
                logger.error(f"[SHORTS-ENGINE] [ALERT] CRITICAL: Both Veo3 AND Sora2 unavailable!")
                logger.error(f"[SHORTS-ENGINE] [ALERT] Veo3 failed with: {exc}")
                logger.error(f"[SHORTS-ENGINE] [ALERT] Sora2 ALSO failed (current error)")
                logger.error(f"")
                logger.error(f"[SHORTS-ENGINE] [SEARCH] TROUBLESHOOTING STEPS:")
                logger.error(f"  1. Check package: pip show google-genai")
                logger.error(f"  2. Reinstall: pip install google-genai --upgrade")
                logger.error(f"  3. Test import: python -c 'import google.genai as genai; print(genai.__version__)'")
                logger.error(f"  4. Python path: {sys.executable}")
                logger.error(f"  5. Check if running in correct environment (venv/conda)")
                logger.error(f"")
                raise ImportError(f"No video generators available. Both Veo3 and Sora2 failed to load.") from exc

        except Exception as exc:
            # OTHER: Runtime errors (config, API keys, etc.)
            logger.error(f"[SHORTS-ENGINE] [FAIL] {normalized.upper()} initialization failed (NON-IMPORT ERROR)")
            logger.error(f"[SHORTS-ENGINE] [PIN] Error type: {type(exc).__name__}")
            logger.error(f"[SHORTS-ENGINE] [PIN] Error details: {str(exc)}")
            logger.warning(f"[SHORTS-ENGINE] [U+26A0] NOT falling back - this is a runtime error, not missing dependencies")
            raise  # Don't fallback on runtime errors, only import errors

        # Cache and return the successfully loaded generator
        logger.info(f"[SHORTS-ENGINE] [U+1F4BE] Caching {normalized.upper()} generator for future use")
        self.generators[normalized] = generator
        logger.info(f"[SHORTS-ENGINE] [DATA] Available generators: {list(self.generators.keys())}")
        return generator

    def _select_engine(self, topic: str, requested: Optional[str] = None) -> str:
        """Determine which generator engine to use for a given topic."""

        if requested:
            normalized = requested.lower()
            if normalized == 'auto':
                return self._suggest_engine(topic)
            if normalized in {'veo3', 'sora2'}:
                return normalized
            logger.warning(f"[SHORTS-ENGINE] Unknown requested engine '{requested}' - falling back to auto")

        if self.default_engine == 'sora2':
            return 'sora2'

        suggested = self._suggest_engine(topic)
        if suggested == 'sora2':
            return 'sora2'

        return 'veo3'

    def _suggest_engine(self, topic: str) -> str:
        """Heuristic auto-selection between Veo3 and Sora2."""

        topic_lower = topic.lower()
        sora_keywords = {"live action", "photorealistic", "realistic", "cinematic", "documentary", "hyperreal", "movie", "film", "human"}
        if any(keyword in topic_lower for keyword in sora_keywords):
            return 'sora2'

        return 'veo3'

    def create_and_upload(
        self,
        topic: str,
        duration: int = 15,
        enhance_prompt: bool = True,
        fast_mode: bool = True,
        privacy: str = "public",
        use_3act: bool = True,
        engine: Optional[str] = None,
        progress_callback: Optional[callable] = None,
        policy_fingerprint: Optional[str] = None,
    ) -> str:
        """
        Complete Shorts flow: generate and upload.

        Args:
            topic: Simple topic (e.g., "Cherry blossoms in Tokyo")
            duration: Video length in seconds (15-60)
                     Default: 15 (uses 3-act multi-clip system)
            enhance_prompt: Use Gemini to enhance topic (ignored if use_3act=True)
            fast_mode: Use Veo 3 Fast (cheaper) vs standard
            privacy: "public", "unlisted", or "private"
            use_3act: Use 3-act multi-clip system (recommended for 15s Shorts)
                     Default: True
            engine: Force generator selection ('veo3', 'sora2', 'auto', or None)
            progress_callback: Optional callable(message: str) for progress updates

        Returns:
            str: YouTube Shorts URL

        Raises:
            Veo3GenerationError: If video generation fails
            Sora2GenerationError: If Sora2 generation fails
            YouTubeUploadError: If upload fails
            InsufficientCreditsError: If quota exceeded

        Notes:
            - 3-act system: Setup -> Shock -> 0102 Reveal (baby IS 0102)
            - Economics: 3x5s = $6 vs 30s = $12 (50% cheaper)
            - Sora2 enables live-action cinematic prompts via OpenAI when selected
        """

        intent_policy = self.uploader.get_shorts_policy()  # no generation while paused/unknown
        if ((policy_fingerprint is not None and policy_fingerprint != intent_policy["fingerprint"])
                or ("topics" in intent_policy and topic not in intent_policy["topics"])):
            raise YouTubeUploadPolicyBlocked("Selected topic directive changed before generation")
        engine_to_use = self._select_engine(topic, engine)
        generator = self._get_generator(engine_to_use)
        self.generator = generator
        self.last_engine_used = engine_to_use

        print()
        print("=" * 60)
        print("YouTube Shorts Creation Flow")
        print("=" * 60)
        print(f"[INPUT] Topic: {topic}")
        print(f"  Engine: {engine_to_use.upper()}")

        start_time = time.time()

        try:
            # Step 1 & 2: Generate video
            # Use 3-act system for 15s, single clip for other durations
            if use_3act and duration == 15 and hasattr(generator, "generate_three_act_short"):
                print("[0102] Generating 3-act Short (Setup -> Shock -> Reveal)...")
                video_path = generator.generate_three_act_short(
                    topic=topic,
                    fast_mode=fast_mode,
                    mode="journal"
                )
                video_prompt = f"3-act story via {engine_to_use}: {topic}"

            else:
                if enhance_prompt and hasattr(generator, "enhance_prompt"):
                    print("[0102 Processing] Enhancing prompt with Move2Japan style...")
                    video_prompt = generator.enhance_prompt(topic)
                else:
                    video_prompt = topic

                print(f"[0102] Generating video with {engine_to_use.upper()}...")
                video_path = generator.generate_video(
                    prompt=video_prompt,
                    duration=duration,
                    fast_mode=fast_mode,
                    progress_callback=progress_callback
                )

            title = topic[:100]
            description = f"""{topic}

Generated with AI for Move2Japan

#Shorts #Japan #AI"""

            tags = ["Shorts", "Japan", "Move2Japan", "AI"]

            topic_lower = topic.lower()
            if "cherry" in topic_lower or "sakura" in topic_lower:
                tags.append("CherryBlossoms")
            if "tokyo" in topic_lower:
                tags.append("Tokyo")
            if "food" in topic_lower:
                tags.append("JapaneseFood")

            print("[0102] Uploading to YouTube...")
            fresh_policy = self.uploader.get_shorts_policy()
            if fresh_policy["fingerprint"] != intent_policy["fingerprint"]:
                raise YouTubeUploadPolicyBlocked("Generation directive changed; retain artifact without uploading")
            if progress_callback:
                progress_callback("[U+1F4E4] Uploading to YouTube... Almost there!")

            youtube_url = self.uploader.upload_short(
                video_path=video_path,
                title=title,
                description=description,
                tags=tags,
                privacy=privacy,
                policy_fingerprint=intent_policy["fingerprint"],
            )

            # Notify chat with final YouTube link
            if progress_callback:
                progress_callback(f"Upload accepted; saved-state verification pending: {youtube_url}")

            elapsed_time = time.time() - start_time
            estimated_cost = duration * getattr(generator, 'cost_per_second', 0.0)

            short_record = {
                "id": youtube_url.split('/')[-1],
                "topic": topic,
                "prompt": video_prompt,
                "video_path": video_path,
                "youtube_url": youtube_url,
                "duration": duration,
                "cost": estimated_cost,
                "privacy": privacy,
                "engine": engine_to_use,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "processing_time": round(elapsed_time, 2),
                "status": "uploaded",
                "verification_status": "independent_readback_required",
            }

            self.shorts_memory.append(short_record)
            self._save_memory()

            print()
            print("=" * 60)
            print("UPLOAD ACCEPTED - SAVED-STATE VERIFICATION PENDING")
            print("=" * 60)
            print(f"  Topic: {topic}")
            print(f"  URL: {youtube_url}")
            print(f"  Duration: {duration}s")
            print(f"  Cost: ${estimated_cost:.2f}")
            print(f"  Engine: {engine_to_use.upper()}")
            print(f"  Processing time: {elapsed_time:.1f}s")
            print(f"  Privacy: {privacy}")
            print("=" * 60)
            print()

            return youtube_url

        except (Veo3GenerationError, Sora2GenerationError) as e:
            print(f"[ERROR] Video generation failed: {e}")
            raise

        except YouTubeUploadError as e:
            print(f"[ERROR] YouTube upload failed: {e}")
            raise

        except InsufficientCreditsError as e:
            print(f"[ERROR] {e}")
            raise

        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            raise
    def generate_video_only(
        self,
        topic: str,
        duration: int = 30,
        enhance_prompt: bool = True,
        fast_mode: bool = True,
        engine: Optional[str] = None
    ) -> str:
        """
        Generate video without uploading.

        Args:
            topic: Video topic
            duration: Video length in seconds
            enhance_prompt: Use Gemini/Sora prompt enhancement when available
            fast_mode: Generator-specific fast mode flag
            engine: Optional override for generator selection

        Returns:
            str: Path to generated .mp4 file
        """

        engine_to_use = self._select_engine(topic, engine)
        generator = self._get_generator(engine_to_use)
        self.generator = generator
        self.last_engine_used = engine_to_use

        if enhance_prompt and hasattr(generator, 'enhance_prompt'):
            video_prompt = generator.enhance_prompt(topic)
        else:
            video_prompt = topic

        return generator.generate_video(
            prompt=video_prompt,
            duration=duration,
            fast_mode=fast_mode
        )

    def upload_existing(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[list] = None,
        privacy: str = "public"
    ) -> str:
        """
        Upload pre-existing video as Short.

        Args:
            video_path: Path to .mp4 file
            title: Video title
            description: Video description
            tags: List of tags
            privacy: Privacy setting

        Returns:
            str: YouTube Shorts URL
        """

        return self.uploader.upload_short(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            privacy=privacy
        )

    def get_stats(self) -> Dict:
        """
        Get statistics about created Shorts.

        Returns:
            dict: Stats including total count, cost, etc.
        """

        total_shorts = len(self.shorts_memory)
        total_cost = sum(s.get('cost', 0.0) for s in self.shorts_memory)
        total_duration = sum(s.get('duration', 0) for s in self.shorts_memory)

        uploaded_count = sum(1 for s in self.shorts_memory if s.get('status') == 'uploaded')

        engine_usage: Dict[str, int] = {}
        for short in self.shorts_memory:
            engine_key = short.get('engine', 'veo3')
            engine_usage[engine_key] = engine_usage.get(engine_key, 0) + 1

        return {
            "total_shorts": total_shorts,
            "uploaded": uploaded_count,
            "total_cost_usd": round(total_cost, 2),
            "total_duration_seconds": total_duration,
            "average_cost_per_short": round(total_cost / total_shorts, 2) if total_shorts > 0 else 0,
            "engine_usage": engine_usage,
            "recent_shorts": self.shorts_memory[-5:]  # Last 5
        }

    def list_shorts(self, limit: int = 10) -> list:
        """
        List recently created Shorts.

        Args:
            limit: Number of Shorts to return

        Returns:
            list: List of Short records
        """

        return self.shorts_memory[-limit:]


if __name__ == "__main__":
    # Test orchestrator
    orchestrator = ShortsOrchestrator()

    # Show stats
    stats = orchestrator.get_stats()
    print(f"\nShorts Statistics:")
    print(f"  Total created: {stats['total_shorts']}")
    print(f"  Total cost: ${stats['total_cost_usd']}")
    print(f"  Average cost: ${stats['average_cost_per_short']}")

    # Note: Actual generation costs money, so commented out
    # url = orchestrator.create_and_upload(
    #     topic="Cherry blossoms falling in a serene Japanese garden",
    #     duration=30
    # )
    # print(f"\nCreated Short: {url}")




