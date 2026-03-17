"""
Indexing Menu - YouTube indexing submenu for FoundUps Agent CLI.

Extracted from main.py per WSP 62 (file size enforcement).
Contains: Gemini indexing, Whisper indexing, Test video, Batch index, Training data.
"""

import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path

from modules.infrastructure.cli.src.utilities import select_channel
from modules.infrastructure.shared_utilities.youtube_channel_registry import group_channels_by_browser


def handle_indexing_menu() -> None:
    """Handle YouTube Indexing submenu (Digital Twin Learning)."""
    print("\n[INDEX] YouTube Channel Indexing")
    print("=" * 60)
    print("Creates searchable knowledge base from 012's videos")
    print("Each video saved as JSON with transcripts, topics, timestamps")
    print("=" * 60)
    print("1. [GEMINI] Gemini AI Indexing (fast, no download)")
    print("2. [DAEMON] Continuous Indexing (24/7 daemon mode)")
    print("3. [LOCAL] Whisper Indexing (yt-dlp + faster-whisper)")
    print("4. [TEST] Test Video Indexing (single video)")
    print("5. [BATCH] Batch Index Channel (bulk process)")
    print("6. [ENHANCE] Batch Enhance Videos (AI Training Data)")
    print("7. [TRAIN] Extract Training Data (Gemma quality filter)")
    print("0. Back")
    print("=" * 60)

    idx_choice = input("\nSelect indexing method: ").strip()

    if idx_choice == "1":
        _handle_gemini_indexing()
    elif idx_choice == "2":
        _handle_daemon_indexing()
    elif idx_choice == "3":
        _handle_whisper_indexing()
    elif idx_choice == "4":
        _handle_test_video_indexing()
    elif idx_choice == "5":
        _handle_batch_indexing()
    elif idx_choice == "6":
        _handle_batch_enhancement()
    elif idx_choice == "7":
        _handle_training_data_extraction()
    elif idx_choice == "0":
        pass  # Back to YT menu


def _handle_gemini_indexing() -> None:
    """Handle Gemini-based indexing - BROWSER-AWARE like commenting."""
    print("\n[GEMINI] Autonomous Video Indexing")
    print("=" * 60)
    print("Browser rotation (same as comment engagement):")
    groups = group_channels_by_browser(role="indexing")
    chrome_names = [ch.get("name", ch.get("key")) for ch in groups.get("chrome", [])]
    edge_names = [ch.get("name", ch.get("key")) for ch in groups.get("edge", [])]
    print(f"  Chrome (9222): {' + '.join(chrome_names) if chrome_names else '(none)'}")
    print(f"  Edge (9223): {' + '.join(edge_names) if edge_names else '(none)'}")
    print("Indexes ALL videos per channel until complete")
    print("=" * 60)

    try:
        from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import run_video_indexing_cycle

        groups = group_channels_by_browser(role="indexing")
        chrome_channels = [ch.get("id") for ch in groups.get("chrome", []) if ch.get("id")]
        edge_channels = [ch.get("id") for ch in groups.get("edge", []) if ch.get("id")]

        total_indexed = 0

        # Phase 1: Chrome channels (UnDaoDu, Move2Japan)
        print("\n[PHASE 1] Chrome (9222): Registry channels")
        result = asyncio.run(run_video_indexing_cycle(
            channels=chrome_channels,
            max_videos_per_channel=9999,  # Index ALL
            browser="chrome"
        ))
        total_indexed += result.get('total_indexed', 0)
        print(f"[CHROME] Indexed {result.get('total_indexed', 0)} videos")

        # Phase 2: Edge channels (FoundUps + antifaFM)
        print("\n[PHASE 2] Edge (9223): Registry channels")
        result = asyncio.run(run_video_indexing_cycle(
            channels=edge_channels,
            max_videos_per_channel=9999,  # Index ALL
            browser="edge"
        ))
        total_indexed += result.get('total_indexed', 0)
        print(f"[EDGE] Indexed {result.get('total_indexed', 0)} videos")

        print(f"\n[RESULT] Total indexed: {total_indexed} videos across all channels")
    except ImportError as e:
        print(f"[ERROR] studio_ask_indexer not available: {e}")
    except Exception as e:
        print(f"[ERROR] Indexing failed: {e}")
        import traceback
        traceback.print_exc()


def _handle_daemon_indexing() -> None:
    """Handle continuous 24/7 daemon indexing mode."""
    print("\n[DAEMON] Continuous Video Indexing")
    print("=" * 60)
    print("Runs indexing in a continuous loop with configurable intervals.")
    print("Creates STOP file to stop: memory/STOP_VIDEO_INDEXER")
    print("=" * 60)

    groups = group_channels_by_browser(role="indexing")
    chrome_names = [ch.get("name", ch.get("key")) for ch in groups.get("chrome", [])]
    edge_names = [ch.get("name", ch.get("key")) for ch in groups.get("edge", [])]
    print(f"  Chrome (9222): {' + '.join(chrome_names) if chrome_names else '(none)'}")
    print(f"  Edge (9223): {' + '.join(edge_names) if edge_names else '(none)'}")
    print("")

    # Get configuration
    videos_per_cycle = input("Videos per channel per cycle [10]: ").strip() or "10"
    interval = input("Interval between cycles (minutes) [15]: ").strip() or "15"
    max_cycles = input("Max cycles (0=infinite) [0]: ").strip() or "0"

    try:
        videos_per_cycle = int(videos_per_cycle)
        interval = int(interval)
        max_cycles = int(max_cycles) if max_cycles != "0" else None
    except ValueError:
        print("[ERROR] Invalid input - using defaults")
        videos_per_cycle, interval, max_cycles = 10, 15, None

    print(f"\n[CONFIG] Videos/channel/cycle: {videos_per_cycle}")
    print(f"[CONFIG] Interval: {interval} minutes")
    print(f"[CONFIG] Max cycles: {max_cycles if max_cycles else 'unlimited'}")
    print("\n[INFO] Press Ctrl+C to stop or create: memory/STOP_VIDEO_INDEXER")
    print("[STARTING] Daemon mode...\n")

    try:
        from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import run_video_indexing_cycle

        groups = group_channels_by_browser(role="indexing")
        chrome_channels = [ch.get("id") for ch in groups.get("chrome", []) if ch.get("id")]
        edge_channels = [ch.get("id") for ch in groups.get("edge", []) if ch.get("id")]

        # Custom dual-browser daemon loop
        async def dual_browser_daemon():
            cycles = 0
            total_indexed = 0
            stop_file = Path("memory") / "STOP_VIDEO_INDEXER"

            while True:
                if stop_file.exists():
                    print("[DAEMON] STOP file detected")
                    break
                if max_cycles and cycles >= max_cycles:
                    print(f"[DAEMON] Reached max cycles ({max_cycles})")
                    break

                cycles += 1
                print(f"\n[DAEMON] === Cycle {cycles} ===")

                # Phase 1: Chrome channels
                if chrome_channels:
                    print(f"[DAEMON] Chrome channels: {len(chrome_channels)}")
                    result = await run_video_indexing_cycle(
                        channels=chrome_channels,
                        max_videos_per_channel=videos_per_cycle,
                        browser="chrome"
                    )
                    indexed = result.get('total_indexed', 0)
                    total_indexed += indexed
                    print(f"[DAEMON] Chrome indexed: {indexed}")

                # Phase 2: Edge channels
                if edge_channels:
                    print(f"[DAEMON] Edge channels: {len(edge_channels)}")
                    result = await run_video_indexing_cycle(
                        channels=edge_channels,
                        max_videos_per_channel=videos_per_cycle,
                        browser="edge"
                    )
                    indexed = result.get('total_indexed', 0)
                    total_indexed += indexed
                    print(f"[DAEMON] Edge indexed: {indexed}")

                print(f"[DAEMON] Cycle {cycles} complete. Total indexed: {total_indexed}")
                print(f"[DAEMON] Sleeping {interval} minutes...")

                # Interruptible sleep
                for _ in range(interval * 6):  # Check every 10 seconds
                    if stop_file.exists():
                        break
                    await asyncio.sleep(10)

            return {"cycles": cycles, "total_indexed": total_indexed}

        result = asyncio.run(dual_browser_daemon())
        print(f"\n[DAEMON] Stopped after {result.get('cycles', 0)} cycles")
        print(f"[DAEMON] Total videos indexed: {result.get('total_indexed', 0)}")

    except KeyboardInterrupt:
        print("\n[DAEMON] Stopped by user (Ctrl+C)")
    except ImportError as e:
        print(f"[ERROR] studio_ask_indexer not available: {e}")
    except Exception as e:
        print(f"[ERROR] Daemon failed: {e}")
        import traceback
        traceback.print_exc()


def _handle_whisper_indexing() -> None:
    """Handle legacy whisper-based indexing."""
    try:
        from modules.communication.voice_command_ingestion.scripts.index_channel import (
            run_indexing_menu
        )
        run_indexing_menu()
    except ImportError as e:
        print(f"[ERROR] Could not import indexing module: {e}")
        print("[TIP] Install: pip install faster-whisper yt-dlp chromadb sentence-transformers")
    except Exception as e:
        print(f"[ERROR] Indexing menu failed: {e}")
        import traceback
        traceback.print_exc()


def _handle_test_video_indexing() -> None:
    """Handle test single video indexing."""
    print("\n[TEST] Single Video Indexing Test")
    video_id = input("Enter YouTube video ID: ").strip()
    if video_id:
        try:
            from modules.ai_intelligence.video_indexer.src.gemini_video_analyzer import GeminiVideoAnalyzer
            from modules.ai_intelligence.video_indexer.src.video_index_store import VideoIndexStore, IndexData

            print(f"[INFO] Analyzing video {video_id}...")
            analyzer = GeminiVideoAnalyzer()
            result = analyzer.analyze_video(video_id)

            if result.success:
                repo_root = Path(__file__).resolve().parents[4]
                artifact_root = repo_root / "memory" / "video_index" / "test"
                # Save to JSON
                store = VideoIndexStore(base_path=str(artifact_root))
                index_data = IndexData(
                    video_id=result.video_id,
                    channel="test",
                    title=result.title,
                    duration=result.duration or 0,
                    indexed_at=datetime.now().isoformat(),
                    audio={"segments": [s.__dict__ for s in result.segments], "transcript_summary": result.transcript_summary},
                    visual={"description": result.visual_description},
                    moments=[],
                    clips=[],
                    metadata={"topics": result.topics, "speakers": result.speakers, "key_points": result.key_points}
                )
                path = store.save_index(video_id, index_data)
                print(f"\n[SUCCESS] Video indexed!")
                print(f"  Title: {result.title}")
                print(f"  Topics: {', '.join(result.topics[:5])}")
                print(f"  Saved to: {path}")
            else:
                print(f"[ERROR] Analysis failed: {result.error}")
        except Exception as e:
            print(f"[ERROR] Test failed: {e}")
            import traceback
            traceback.print_exc()


def _handle_batch_indexing() -> None:
    """Handle batch index channel."""
    from pathlib import Path

    print("\n[BATCH] Batch Index Channel Videos")
    print("=" * 60)
    channel = select_channel()
    batch_size = input("Batch size [50]: ").strip() or "50"
    delay = input("Delay between API calls (seconds) [10]: ").strip() or "10"

    # Resolve paths relative to repo root (4 levels up from this file)
    repo_root = Path(__file__).resolve().parents[4]
    video_file = repo_root / "data" / f"{channel}_video_ids.txt"
    script_path = repo_root / "scripts" / "batch_index_videos.py"

    if not video_file.exists():
        print(f"[ERROR] Video ID file not found: {video_file}")
        print("[TIP] Create video ID file or fetch from YouTube API")
    else:
        try:
            import subprocess
            cmd = [
                sys.executable,
                str(script_path),
                "--batch-size", batch_size,
                "--delay", delay,
                "--channel", channel,
                "--video-file", str(video_file),
                "--max-retries", "3"
            ]
            print(f"[INFO] Running: {' '.join(cmd)}")
            subprocess.run(cmd, cwd=str(repo_root))
        except Exception as e:
            print(f"[ERROR] Batch indexing failed: {e}")
            import traceback
            traceback.print_exc()


def _handle_batch_enhancement() -> None:
    """Handle batch enhancement of indexed videos with AI training data."""
    from pathlib import Path
    import json

    print("\n[ENHANCE] Batch Enhance Videos for Digital Twin Training")
    print("=" * 60)
    print("Enhances indexed videos with training_data fields:")
    print("  - quotable_moments (012's authentic voice)")
    print("  - personas, topics, training pairs")
    print("  - WSP 15 quality tiers (0=LOW, 1=MED, 2=HIGH)")
    print("")
    print("Provider rotation: Grok -> OpenAI -> Gemini")
    print("Checkpoint/resume: Automatically saves progress")
    print("=" * 60)

    channel = select_channel()

    # Resolve paths relative to repo root (4 levels up from this file)
    repo_root = Path(__file__).resolve().parents[4]
    checkpoint_file = repo_root / "memory" / f"enhancement_checkpoint_{channel}.json"
    video_dir = repo_root / "memory" / "video_index" / channel
    script_path = repo_root / "scripts" / "batch_enhance_videos.py"

    if not video_dir.exists():
        print(f"[ERROR] No indexed videos found: {video_dir}")
        print("[TIP] Run indexing first (Options 1-4)")
        return

    # Count videos
    total_videos = len(list(video_dir.glob("*.json")))
    completed = 0

    if checkpoint_file.exists():
        try:
            state = json.loads(checkpoint_file.read_text(encoding="utf-8"))
            completed = len(state.get("completed", []))
        except:
            pass

    print(f"\nChannel: {channel}")
    print(f"Total indexed videos: {total_videos}")
    print(f"Already enhanced: {completed}")
    print(f"Remaining: {total_videos - completed}")
    print("")
    print("Actions:")
    print("  1. Enhance next batch (25 videos)")
    print("  2. Enhance ALL remaining")
    print("  3. Show status only")
    print("  4. Reset checkpoint (start over)")
    print("  0. Back")

    action = input("\nSelect action: ").strip()

    if action == "0":
        return
    elif action == "3":
        # Show status
        try:
            import subprocess
            subprocess.run(
                [sys.executable, str(script_path), "--status", "--channel", channel],
                cwd=str(repo_root)
            )
        except Exception as e:
            print(f"[ERROR] Status check failed: {e}")
        return
    elif action == "4":
        # Reset checkpoint
        confirm = input("Are you sure? This will restart from scratch (y/n): ").strip().lower()
        if confirm == "y":
            if checkpoint_file.exists():
                checkpoint_file.unlink()
                print("[INFO] Checkpoint reset. Next run will start fresh.")
            else:
                print("[INFO] No checkpoint to reset.")
        return
    elif action in ("1", "2"):
        max_videos = 25 if action == "1" else 9999

        # 0102 handles provider rotation autonomously (Grok -> OpenAI -> Gemini)
        try:
            import subprocess
            cmd = [
                sys.executable,
                str(script_path),
                "--max-videos", str(max_videos),
                "--resume",
                "--channel", channel
            ]
            print(f"\n[INFO] 0102 autonomous enhancement starting...")
            print("[INFO] Provider rotation: Grok -> OpenAI -> Gemini (auto)")
            print("[INFO] Press Ctrl+C to stop (progress saved)\n")
            subprocess.run(cmd, cwd=str(repo_root))
        except KeyboardInterrupt:
            print("\n[STOP] Enhancement stopped (progress saved)")
        except Exception as e:
            print(f"[ERROR] Enhancement failed: {e}")
            import traceback
            traceback.print_exc()


def _handle_training_data_extraction() -> None:
    """Handle extract training data with Gemma quality filter."""
    from pathlib import Path

    print("\n[TRAIN] Extract Training Data for Digital Twin")
    print("=" * 60)
    channel = select_channel()
    use_gemma = input("Use Gemma quality filter? (y/n) [y]: ").strip().lower() != "n"

    # Resolve paths relative to repo root (4 levels up from this file)
    repo_root = Path(__file__).resolve().parents[4]
    input_dir = repo_root / "memory" / "video_index" / channel
    output_dir = repo_root / "memory" / "training_data" / channel

    if not input_dir.exists():
        print(f"[ERROR] No indexed videos found: {input_dir}")
        print("[TIP] Run indexing first (Option 1 or 4)")
    else:
        try:
            from modules.ai_intelligence.video_indexer.src.dataset_builder import DatasetBuilder

            print(f"[INFO] Processing {input_dir}...")
            builder = DatasetBuilder(use_gemma=use_gemma)
            result = builder.process_folder(str(input_dir), str(output_dir))

            print("\n[SUCCESS] Training data extracted!")
            print(f"  Videos processed: {result['videos_processed']}")
            print(f"  Training rows: {result['training_rows']}")
            print(f"  Voice clips: {result['voice_clips']}")
            print(f"  Training-worthy (HIGH tier): {result['training_worthy']}")
            print(f"  Output: {output_dir}/")

            # Show output files
            for f in output_dir.glob("*"):
                size = f.stat().st_size / 1024
                print(f"    - {f.name} ({size:.1f} KB)")
        except Exception as e:
            print(f"[ERROR] Training data extraction failed: {e}")
            import traceback
            traceback.print_exc()
