"""
YouTube Menu - YouTube DAEs submenu handlers for FoundUps Agent CLI.

Extracted from main.py per WSP 62 (file size enforcement).
Contains: Live Chat Monitor, Comment Engagement, Shorts Scheduler/Generator,
Stats, Full Production Mode, AI Overseer modes.
"""

import os
import sys
import time
import asyncio
import logging
from typing import Optional, Dict, Any

from modules.infrastructure.cli.src.utilities import env_truthy, select_channel
from modules.infrastructure.cli.src.youtube_controls import (
    yt_switch_summary,
    yt_controls_menu,
)
from modules.infrastructure.shared_utilities.youtube_channel_registry import (
    get_channels,
    get_channel_keys,
    get_channel_by_key,
    get_channel_by_id,
    get_rotation_order,
    group_channels_by_browser,
    add_channel,
)
from modules.communication.youtube_shorts.src.clip_exporter import export_clip, ClipExportError
from modules.communication.youtube_shorts.src.video_editor import VideoEditor, VideoEditorError
from modules.communication.headless_video_orchestrator.src.oss_adapters import (
    run_ai_shorts_generator,
    ExternalToolError,
)

# antifaFM preflight (ANTIFAFM_PREFLIGHT_RELOCATION_AUDIT_20260516)
try:
    from modules.platform_integration.antifafm_broadcaster.src.preflight import (
        preflight_check_for_menu,
        run_preflight,
        format_preflight_status,
    )
    PREFLIGHT_AVAILABLE = True
except ImportError:
    PREFLIGHT_AVAILABLE = False

logger = logging.getLogger(__name__)


def _run_shorts_flow(
    engine_label: str,
    system_label: str,
    mode_label: str,
    duration_label: str,
    engine_key: str,
    args,
    enable_key_hygiene: bool,
) -> None:
    """Run YouTube Shorts generation flow for specified engine."""
    print(f"\n[MENU] YouTube Shorts Generator [{engine_label}]")
    print("=" * 60)
    print("Channel: Move2Japan (9,020 subscribers)")
    print(f"System: {system_label}")
    print("=" * 60)

    topic = input("\n[TIP] Enter topic (e.g., 'Cherry blossoms in Tokyo'): ").strip()

    if not topic:
        print("[WARN] No topic entered - returning to menu")
        return

    try:
        from modules.communication.youtube_shorts.src.shorts_orchestrator import ShortsOrchestrator
        from modules.communication.youtube_shorts.src.veo3_generator import Veo3ApiKeyCompromisedError

        print(f"\n[MENU] Generating YouTube Short ({engine_label}): {topic}")
        print(f"  Mode: {mode_label}")
        print(f"  Duration: {duration_label}")
        print("  Privacy: PUBLIC")

        orchestrator = ShortsOrchestrator(channel="move2japan", default_engine="auto")

        youtube_url = orchestrator.create_and_upload(
            topic=topic,
            duration=15,
            enhance_prompt=True,
            fast_mode=True,
            privacy="public",
            use_3act=True,
            engine=engine_key
        )

        print(f"\n[INFO]SHORT PUBLISHED!")
        print(f"   URL: {youtube_url}")
        print(f"   Channel: Move2Japan")

    except Exception as e:
        # Check for Veo3 API key compromised error
        error_class_name = type(e).__name__
        if error_class_name == "Veo3ApiKeyCompromisedError":
            print(f"\n[ERROR]YouTube Shorts generation failed: {e}")
            if enable_key_hygiene:
                try:
                    from modules.infrastructure.shared_utilities.key_hygiene import KeyHygiene

                    KeyHygiene(service="veo3", urls=KeyHygiene.default_genai_urls()).maybe_prompt_rotation(
                        key_source=getattr(e, "key_source", "unknown"),
                        fingerprint=getattr(e, "fingerprint", None) or "sha256:unknown",
                        reason_hint="compromised",
                        interactive=True,
                    )
                except Exception:
                    pass
        else:
            print(f"\n[ERROR]YouTube Shorts generation failed: {e}")

        # Avoid dumping stack traces in normal runs (too noisy for DAEmon logs).
        if getattr(args, 'verbose', False) or env_truthy("FOUNDUPS_DEBUG_SHORTS", "false"):
            import traceback
            traceback.print_exc()


def handle_youtube_menu(
    args,
    should_skip,
    pm,
    monitor_youtube,
    enable_key_hygiene: bool,
) -> bool:
    """
    Handle YouTube DAEs submenu.
    
    Returns True if menu should exit back to main menu, False to continue in YouTube menu.
    """
    print("\n[MENU] YouTube DAEs")
    print("=" * 60)
    print(f"Active switches: {yt_switch_summary()} (00=Controls)")
    print("")
    print("== LIVE OPERATIONS ==")
    print("1. [DAE] Live Chat Monitor (AutoModeratorDAE)")
    print("2. [DAE] Comment Engagement (Broadcast Controls)")
    print("6. [ALL] Full Production Mode (Live+Comments+Scheduler)")
    print("7. [AI] AI Overseer Mode (Qwen/Gemma Monitoring)")
    print("")
    print("== CONTENT AUTOMATION ==")
    print("3. [DAE] Shorts Scheduler (Enhance + Schedule)")
    print("4. [DAE] Shorts Generator (Veo3/Sora2)")
    print("")
    print("== KNOWLEDGE INDEXING ==")
    print("8. [INDEX] YouTube Indexing (Digital Twin Learning)")
    print("5. [INFO] YouTube Stats")
    print("9. [LAB] Video Lab (Clip/Repurpose)")
    print("")
    print("== STREAMING ==")
    print("10. [DAE] antifaFM Broadcaster (Radio -> YouTube Live)")
    print("")
    print("== OPERATIONS ==")
    print("R. [OPS] Rotation Controls (Account Swap/Test)")
    print("C. [OPS] Channel Registry (Add/Manage)")
    print("00. Controls (Local Switches)")
    print("0. Back to Main Menu")
    print("=" * 60)

    yt_choice = input("\nSelect YouTube DAE: ").strip().upper()

    if yt_choice == "R":
        # Rotation Controls (Account Swap/Test)
        _handle_rotation_controls_menu()
        return False
    elif yt_choice == "C":
        _handle_channel_registry_menu()
        return False

    elif yt_choice == "00":
        yt_controls_menu()
        return False
    
    elif yt_choice == "1":
        # 1.1 Live Chat Monitor DAE - Direct launch with 012 profile (ADR-013)
        print("\n[DAE] Live Chat Monitor - 012 Operational Profile")
        print("=" * 60)

        # === PREFLIGHT CHECK (ANTIFAFM_PREFLIGHT_RELOCATION_AUDIT_20260516) ===
        # Informational: shows antifaFM/OBS status before starting monitor
        if PREFLIGHT_AVAILABLE:
            ready, status_msg = preflight_check_for_menu(
                require_obs=False,  # Non-strict: OBS is optional for monitor
                require_youtube=False,
            )
            print("\n" + status_msg)
            print("=" * 60)
            if not ready:
                print("[INFO] Monitor will start. For antifaFM streaming, use option 10.")
            print()

        env_overrides = {
            "YT_ENGAGEMENT_TEMPO": "012",
            "YT_REPLY_BASIC_ONLY": "false",
            "YT_COMMENT_ONLY_MODE": "false"
        }

        # Auto-kill existing instances
        try:
            from modules.infrastructure.instance_lock.src.instance_manager import get_instance_lock
            lock = get_instance_lock("youtube_monitor")
            duplicates = lock.check_duplicates(quiet=True)
            if duplicates:
                print(f"[MENU] Killing {len(duplicates)} existing instance(s)...")
                lock.kill_pids(duplicates)
                time.sleep(1)
        except Exception as e:
            logger.debug(f"Cleanup failed: {e}")

        asyncio.run(monitor_youtube(disable_lock=False, enable_ai_monitoring=False, env_overrides=env_overrides))
        return False

    elif yt_choice == "2":
        # 1.2 Comment Engagement - 012 Control Plane (broadcast settings)
        _handle_comment_engagement_menu()
        return False

    elif yt_choice == "3":
        # 1.3 Shorts Scheduler DAE + Selenium Tests
        _handle_shorts_scheduler_menu()
        return False

    elif yt_choice == "4":
        # 1.4 Shorts Generator DAE (submenu for Veo3/Sora2)
        print("\n[DAE] Shorts Generator")
        print("=" * 60)
        print("1. Veo3 (Gemini - 3-Act Story)")
        print("2. Sora2 (Live Action Cinematic)")
        print("0. Back")
        print("=" * 60)

        engine_choice = input("Select engine: ").strip()

        if engine_choice == "1":
            _run_shorts_flow(
                engine_label="Gemini/Veo 3",
                system_label="3-Act Story (Setup -> Shock -> 0102 Reveal)",
                mode_label="Emergence Journal POC",
                duration_label="~16s (2.5s clips merged)",
                engine_key="veo3",
                args=args,
                enable_key_hygiene=enable_key_hygiene,
            )
        elif engine_choice == "2":
            _run_shorts_flow(
                engine_label="Sora2 Live Action",
                system_label="3-Act Story (Cinematic Reveal)",
                mode_label="Cinematic Sora2 (live-action focus)",
                duration_label="15s cinematic (single clip)",
                engine_key="sora2",
                args=args,
                enable_key_hygiene=enable_key_hygiene,
            )
        return False

    elif yt_choice == "5":
        # 1.5 YouTube Stats
        print("\n[INFO] YouTube Stats")
        try:
            from modules.communication.youtube_shorts.src.shorts_orchestrator import ShortsOrchestrator
            orch = ShortsOrchestrator(channel="move2japan", default_engine="auto")
            stats = orch.get_stats()

            print(f"\n  Total Shorts: {stats['total_shorts']}")
            print(f"  Uploaded: {stats['uploaded']}")
            print(f"  Total Cost: ${stats['total_cost_usd']}")
            print(f"  Avg Cost: ${stats['average_cost_per_short']}")
            if stats.get('engine_usage'):
                print(f"  Engine Usage: {stats['engine_usage']}")

            recent = stats.get('recent_shorts') or []
            if recent:
                print(f"\n  Recent Shorts:")
                for s in recent[-3:]:
                    print(f"    - {s.get('topic', 'N/A')[:40]}...")
                    print(f"      {s.get('youtube_url', 'N/A')}")
        except Exception as e:
            print(f"[ERROR] Failed to get stats: {e}")
        return False

    elif yt_choice == "6":
        # 1.6 Full Production Mode (runs Live Chat + Comments)
        print("\n[ALL] Full YouTube Production Mode")
        print("=" * 60)
        print("This will start:")
        print("  - Live Chat Monitor (AutoModeratorDAE)")
        print("  - Comment Engagement DAE (Like/Heart/Reply)")
        print("=" * 60)
        print("[INFO] Starting Full Production Mode with 012 profile...")

        env_overrides = {
            "YT_ENGAGEMENT_TEMPO": "012",
            "YT_REPLY_BASIC_ONLY": "false",
            "YT_COMMENT_ONLY_MODE": "false"
        }

        # Auto-kill any existing instances
        try:
            from modules.infrastructure.instance_lock.src.instance_manager import get_instance_lock
            lock = get_instance_lock("youtube_monitor")
            duplicates = lock.check_duplicates(quiet=True)
            if duplicates:
                print(f"[MENU] Killing {len(duplicates)} existing instance(s)...")
                lock.kill_pids(duplicates)
                time.sleep(1)
        except Exception as e:
            logger.debug(f"Pre-launch cleanup failed: {e}")

        asyncio.run(monitor_youtube(disable_lock=False, enable_ai_monitoring=False, env_overrides=env_overrides))
        return False

    elif yt_choice == "7":
        # 1.7 AI Overseer Mode
        print("\n[AI] AI Overseer Mode (Qwen/Gemma Monitoring)")
        print("=" * 60)
        print("Profiles: 1=012  2=FAST  3=MEDIUM  4=Minimal  5=Occam  6=Comment-Only")
        print("=" * 60)

        ai_profile = input("Select profile [1-6, default=1]: ").strip() or "1"

        env_overrides = {"YT_COMMENT_ONLY_MODE": "false"}
        if ai_profile == "2":
            env_overrides.update({"YT_ENGAGEMENT_TEMPO": "FAST", "COMMUNITY_DEBUG_SUBPROCESS": "true"})
        elif ai_profile == "3":
            env_overrides.update({"YT_ENGAGEMENT_TEMPO": "MEDIUM", "COMMUNITY_DEBUG_SUBPROCESS": "true"})
        elif ai_profile == "4":
            env_overrides.update({"YT_ENGAGEMENT_TEMPO": "012", "YT_REPLY_BASIC_ONLY": "true"})
        elif ai_profile == "5":
            env_overrides.update({"YT_ENGAGEMENT_TEMPO": "012", "YT_REPLY_BASIC_ONLY": "true", "YT_OCCAM_MODE": "true"})
        elif ai_profile == "6":
            env_overrides.update({"YT_ENGAGEMENT_TEMPO": "012", "YT_REPLY_BASIC_ONLY": "false", "YT_COMMENT_ONLY_MODE": "true"})
        else:
            env_overrides.update({"YT_ENGAGEMENT_TEMPO": "012", "YT_REPLY_BASIC_ONLY": "false"})

        print("[AI] Starting with AI Overseer monitoring...")
        try:
            asyncio.run(monitor_youtube(disable_lock=False, enable_ai_monitoring=True, env_overrides=env_overrides))
        except KeyboardInterrupt:
            print("\n[STOP] Stopped by user")
        except Exception as e:
            print(f"\n[ERROR] Failed: {e}")
        return False

    elif yt_choice == "8":
        # 1.8 YouTube Indexing (Digital Twin Learning)
        from modules.infrastructure.cli.src.indexing_menu import handle_indexing_menu
        handle_indexing_menu()
        return False

    elif yt_choice == "9":
        # Video Lab (clip/export/format)
        _handle_video_lab_menu()
        return False

    elif yt_choice == "10":
        # antifaFM Broadcaster (Radio -> YouTube Live)
        _handle_antifafm_broadcaster_menu()
        return False

    elif yt_choice == "0":
        print("[BACK] Returning to main menu...")
        return True
    else:
        print("[ERROR] Invalid choice")
        return False


def _handle_comment_engagement_menu() -> None:
    """Handle Comment Engagement submenu (broadcast settings)."""
    print("\n[MENU] Comment Engagement (Broadcast Controls)")
    print("=" * 60)
    try:
        from modules.communication.video_comments.src.commenting_control_plane import (
            load_broadcast,
            set_promo,
            clear_promo,
        )
    except Exception as e:
        print(f"[ERROR] Commenting control plane unavailable: {e}")
        return

    def _summary(cfg) -> str:
        enabled = "ON" if cfg.enabled else "OFF"
        handles = " ".join(cfg.promo_handles) if cfg.promo_handles else "(none)"
        msg = (cfg.promo_message or "").strip() or "(none)"
        return f"enabled={enabled} | handles={handles} | message={msg}"

    while True:
        cfg = load_broadcast()
        print("\n" + "-" * 60)
        print("COMMENTING SUBMENU (012 -> Comment DAE)")
        print("Broadcast controls (promo injection) - use 6 for comment-only")
        print(f"Switches: {yt_switch_summary()} (00=Controls)")
        print(f"Current: {_summary(cfg)}")
        print("-" * 60)
        print("  1) Toggle enabled (promo injection on replies)")
        print("  2) Set promo handles (space-separated, e.g. @NewChannel @Other)")
        print("  3) Set promo message (free text)")
        print("  4) Clear promo + disable")
        print("  5) Back")
        print("  6) Start COMMENT-ONLY (NO live chat agent)")
        print("  00) Controls (local switches)")
        print("")
        print("  TIP: For full DAE (comments+stream+livechat), use main menu 1→1")
        print("  TIP: Or just TYPE your message to inject it into replies")

        choice_raw = input("inject> ").strip()
        choice = choice_raw.lower()
        if choice in {"5", "back", "b", "exit", "quit"}:
            break
        if choice in {"00", "controls", "c"}:
            yt_controls_menu()
            continue
        if choice in {"1", "toggle"}:
            set_promo(enabled=not cfg.enabled, updated_by="012")
            continue
        if choice in {"2", "handles"}:
            raw = input("handles> ").strip()
            handles = [h for h in raw.split() if h.strip()]
            set_promo(promo_handles=handles, updated_by="012")
            continue
        if choice in {"3", "message", "msg"}:
            msg = input("message> ").strip()
            set_promo(promo_message=msg, updated_by="012")
            continue
        if choice in {"4", "clear"}:
            clear_promo()
            continue
        if choice in {"6", "start", "run", "comment-only", "comments-only", "co"}:
            print("\n[DAE] COMMENT-ONLY MODE (NO Live Chat Agent)")
            print("=" * 60)
            print("Auto-rotates through ALL channels:")
            groups = group_channels_by_browser(role="comments")
            chrome_names = [ch.get("name", ch.get("key")) for ch in groups.get("chrome", [])]
            edge_names = [ch.get("name", ch.get("key")) for ch in groups.get("edge", [])]
            print(f"  Chrome (9222): {' + '.join(chrome_names) if chrome_names else '(none)'}")
            print(f"  Edge (9223): {' + '.join(edge_names) if edge_names else '(none)'}")
            print("")
            print("🔒 Stream detection: DISABLED")
            print("🔒 Live chat agent: DISABLED")
            print("✅ Comment engagement: RUNS CONTINUOUSLY")
            print("=" * 60)

            try:
                from modules.communication.livechat.src.auto_moderator_dae import AutoModeratorDAE

                # Set comment-only mode BEFORE launching
                os.environ["YT_COMMENT_ONLY_MODE"] = "true"

                print("[INFO] Starting COMMENT-ONLY DAE...")
                print("[INFO] YT_COMMENT_ONLY_MODE=true (no stream detection, no live chat)")
                print("[INFO] Press Ctrl+C to stop")

                dae = AutoModeratorDAE(enable_ai_monitoring=False)
                asyncio.run(dae.run())
            except KeyboardInterrupt:
                print("\n[STOP] Comment-Only DAE stopped by user")
            except ImportError as e:
                print(f"[ERROR] Could not import: {e}")
                import traceback
                traceback.print_exc()
            except Exception as e:
                print(f"[ERROR] Failed: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # Reset the env var after exit
                os.environ.pop("YT_COMMENT_ONLY_MODE", None)
            continue

        # SMART INPUT: If not a menu option, treat as promo message to inject
        # This makes the UX intuitive - just type content and it gets queued, then DAE launches
        if choice_raw and len(choice_raw) > 2:
            # Looks like content, not a menu option - preserve original case
            print(f"\n[SMART] Setting promo message: \"{choice_raw}\"")
            set_promo(promo_message=choice_raw, enabled=True, updated_by="012")
            print("[SMART] ✅ Promo injection ENABLED - launching comment DAE...")
            print("")

            # Launch comment-only DAE with promo injection
            print("[DAE] COMMENT-ONLY MODE with PROMO INJECTION")
            print("=" * 60)
            groups = group_channels_by_browser(role="comments")
            chrome_names = [ch.get("name", ch.get("key")) for ch in groups.get("chrome", [])]
            edge_names = [ch.get("name", ch.get("key")) for ch in groups.get("edge", [])]
            print(f"  Chrome (9222): {' + '.join(chrome_names) if chrome_names else '(none)'}")
            print(f"  Edge (9223): {' + '.join(edge_names) if edge_names else '(none)'}")
            print(f"  Promo: \"{choice_raw}\"")
            print("=" * 60)

            try:
                from modules.communication.livechat.src.auto_moderator_dae import AutoModeratorDAE

                os.environ["YT_COMMENT_ONLY_MODE"] = "true"
                print("[INFO] Starting COMMENT-ONLY DAE with promo injection...")
                print("[INFO] Press Ctrl+C to stop")

                dae = AutoModeratorDAE(enable_ai_monitoring=False)
                asyncio.run(dae.run())
            except KeyboardInterrupt:
                print("\n[STOP] Comment DAE stopped by user")
            except ImportError as e:
                print(f"[ERROR] Could not import: {e}")
            except Exception as e:
                print(f"[ERROR] Failed: {e}")
                import traceback
                traceback.print_exc()
            finally:
                os.environ.pop("YT_COMMENT_ONLY_MODE", None)
            continue

        print("Unknown option (type a number 1-6, or type your message directly)")


def _handle_video_lab_menu() -> None:
    """Handle Video Lab submenu for clip export/formatting."""
    while True:
        print("\n[LAB] Video Lab - Clip/Repurpose")
        print("=" * 60)
        print("1. Export clip from cached/local video (ffmpeg trim)")
        print("2. Format existing MP4 to Shorts 9:16 (1080x1920)")
        print("3. Show cache locations")
        print("4. Download YouTube video to cache (yt-dlp)")
        print("5. Auto-clip with AI-Youtube-Shorts-Generator (OSS)")
        print("6. Generator health check (Veo3/Sora2)")
        print("7. Build Short from indexed clip candidates")
        print("0. Back")
        print("=" * 60)

        choice = input("video-lab> ").strip()
        if choice in {"0", "back", "b"}:
            break

        if choice == "3":
            print("\nCache locations:")
            print("  - Download cache: memory/video_cache/<video_id>.mp4")
            print("  - Lab outputs:    memory/video_lab/clips/")
            input("\nPress Enter to continue...")
            continue

        if choice == "4":
            video_id = input("video_id (YouTube ID): ").strip()
            quality = input("max quality (360p/480p/720p/1080p) [720p]: ").strip() or "720p"
            try:
                # Lazy import to avoid loading cv2 unless needed
                from modules.ai_intelligence.video_indexer.src.visual_analyzer import VisualAnalyzer

                va = VisualAnalyzer()
                path = va.download_video(video_id=video_id, use_cache=True, max_quality=quality)
                if path:
                    print(f"\n[OK] Cached to: {path}")
                else:
                    print("\n[WARN] Download returned no path (check logs).")
            except Exception as e:
                print(f"[ERROR] Download failed: {e}")
            input("\nPress Enter to continue...")
            continue

        if choice == "5":
            input_ref = input("YouTube URL or local file path: ").strip()
            try:
                out_path = run_ai_shorts_generator(input_ref=input_ref)
                print(f"\n[OK] OSS short created: {out_path}")
            except ExternalToolError as e:
                print(f"[ERROR] {e}")
            input("\nPress Enter to continue...")
            continue

        if choice == "6":
            from modules.communication.youtube_shorts.src.generator_health_check import (
                check_veo3,
                check_sora2,
            )

            run_test = input("Run API generation test? (y/N): ").strip().lower() == "y"
            target = input("Target generator: 1=Veo3 2=Sora2 3=Both [3]: ").strip() or "3"

            results = []
            if target in {"1", "3"}:
                results.append(check_veo3(test_generate=run_test))
            if target in {"2", "3"}:
                results.append(check_sora2(test_generate=run_test))

            print("\n[RESULTS]")
            for r in results:
                status = "OK" if r.ok else "FAIL"
                line = f"- {r.name}: {status} | {r.details}"
                if r.output_path:
                    line += f" | output={r.output_path}"
                print(line)
            input("\nPress Enter to continue...")
            continue

        if choice == "7":
            from modules.communication.youtube_shorts.src.shorts_pipeline import build_short_from_index_auto

            auto_mode = env_truthy("YT_VIDEO_LAB_AUTO_MODE", "false")
            default_channel = (
                os.getenv("YT_VIDEO_LAB_CHANNEL_KEY")
                or os.getenv("YT_SHORTS_SCHEDULER_CHANNEL_KEY")
                or "move2japan"
            ).strip().lower() or "move2japan"
            default_video_id = os.getenv("YT_VIDEO_LAB_VIDEO_ID", "").strip()
            default_min_dur = os.getenv("YT_VIDEO_LAB_MIN_DURATION", "15").strip() or "15"
            default_max_dur = os.getenv("YT_VIDEO_LAB_MAX_DURATION", "60").strip() or "60"
            default_quality = os.getenv("YT_VIDEO_LAB_QUALITY", "720p").strip() or "720p"
            auto_pick = env_truthy("YT_VIDEO_LAB_AUTO_PICK", "true" if auto_mode else "false")

            if auto_mode:
                channel_key = default_channel
                video_id = default_video_id
                min_dur = default_min_dur
                max_dur = default_max_dur
                quality = default_quality
            else:
                available_channels = "/".join(get_channel_keys())
                channel_key = input(
                    f"channel ({available_channels}) [{default_channel}]: "
                ).strip().lower() or default_channel
                video_id = input(f"source video_id [{default_video_id}]: ").strip() or default_video_id
                min_dur = input(f"min duration seconds [{default_min_dur}]: ").strip() or default_min_dur
                max_dur = input(f"max duration seconds [{default_max_dur}]: ").strip() or default_max_dur
                quality = input(
                    f"cache quality (360p/480p/720p/1080p) [{default_quality}]: "
                ).strip() or default_quality

            if not channel_key:
                print("[ERROR] channel is required.")
                if not auto_mode:
                    input("\nPress Enter to continue...")
                continue

            try:
                min_val = float(min_dur)
                max_val = float(max_dur)
            except ValueError:
                print("[ERROR] Invalid duration values.")
                if not auto_mode:
                    input("\nPress Enter to continue...")
                continue

            try:
                result = build_short_from_index_auto(
                    channel_key=channel_key,
                    video_id=video_id or None,
                    min_duration=min_val,
                    max_duration=max_val,
                    format_shorts=True,
                    max_quality=quality,
                    auto_pick=auto_pick,
                    mark_index=True,
                )
                print(f"\n[OK] Short built: {result.output_path}")
                print(f"  source: {result.selection.selection_source} {result.selection.start_time:.1f}-{result.selection.end_time:.1f}s")
            except Exception as e:
                print(f"[ERROR] Build failed: {e}")
                if not auto_mode:
                    input("\nPress Enter to continue...")
                continue

            # Optional upload (API uploader supports multiple channels)
            auto_upload = env_truthy("YT_VIDEO_LAB_AUTO_UPLOAD", "false")
            if auto_mode:
                do_upload = auto_upload
            else:
                default_upload = "y" if auto_upload else "n"
                raw = input(f"Upload via API as unlisted? (y/N) [{default_upload}]: ").strip().lower()
                if not raw:
                    raw = default_upload
                do_upload = raw == "y"
            if do_upload:
                try:
                    from modules.communication.youtube_shorts.src.youtube_uploader import YouTubeShortsUploader

                    uploader = YouTubeShortsUploader(channel=channel_key)
                    resolved_video_id = result.selection.source_video_id or video_id or ""
                    title_default = (
                        os.getenv("YT_VIDEO_LAB_TITLE", "").strip()
                        or result.selection.title_hint
                        or (f"Clip {resolved_video_id}" if resolved_video_id else "Clip")
                    )
                    desc_default = (
                        os.getenv("YT_VIDEO_LAB_DESCRIPTION", "").strip()
                        or result.selection.description_hint
                        or (f"Clip from {resolved_video_id}" if resolved_video_id else "Clip from archive")
                    )
                    privacy = os.getenv("YT_VIDEO_LAB_PRIVACY", "unlisted").strip().lower() or "unlisted"

                    if auto_mode:
                        title = title_default
                        description = desc_default
                    else:
                        title = input(f"Title [{title_default}]: ").strip() or title_default
                        description = input(f"Description [{desc_default}]: ").strip() or desc_default

                    url = uploader.upload_short(
                        video_path=result.output_path,
                        title=title,
                        description=description,
                        privacy=privacy,
                    )
                    print(f"[OK] Uploaded: {url}")
                except Exception as e:
                    print(f"[ERROR] Upload failed: {e}")

            if not auto_mode:
                input("\nPress Enter to continue...")
            continue

        if choice == "1":
            video_id = input("video_id (YouTube ID): ").strip()
            start = input("start time (sec or mm:ss): ").strip()
            end = input("end time (sec or mm:ss): ").strip()
            explicit_path = input("optional source path (leave blank to use cache): ").strip()
            use_shorts = input("format to Shorts 9:16? (y/N): ").strip().lower() == "y"

            try:
                raw_path, shorts_path = export_clip(
                    video_id=video_id,
                    start_time=start,
                    end_time=end,
                    source_path=explicit_path or None,
                    format_shorts=use_shorts,
                )
                print(f"\n[OK] Clip saved: {raw_path}")
                if shorts_path:
                    print(f"[OK] Shorts formatted: {shorts_path}")
            except ClipExportError as e:
                print(f"[ERROR] {e}")
            input("\nPress Enter to continue...")
            continue

        if choice == "2":
            path = input("MP4 path to format: ").strip()
            try:
                editor = VideoEditor()
                formatted = editor.ensure_shorts_format(path)
                print(f"\n[OK] Shorts formatted: {formatted}")
            except VideoEditorError as e:
                print(f"[ERROR] {e}")
            except Exception as e:
                print(f"[ERROR] Failed: {e}")
            input("\nPress Enter to continue...")
            continue

        print("[ERROR] Invalid choice")


def _handle_antifafm_broadcaster_menu() -> None:
    """Handle antifaFM Broadcaster submenu (Radio -> YouTube Live)."""
    print("\n[DAE] antifaFM Broadcaster")
    print("=" * 60)
    print("Streams antifaFM.com radio to YouTube Live via FFmpeg")
    print("Icecast -> FFmpeg -> RTMP -> YouTube Live")
    print("=" * 60)

    # === PREFLIGHT CHECK (ANTIFAFM_PREFLIGHT_RELOCATION_AUDIT_20260516) ===
    # Show OBS/YouTube readiness before broadcaster menu
    if PREFLIGHT_AVAILABLE:
        ready, status_msg = preflight_check_for_menu(
            require_obs=True,  # Strict: OBS required for broadcaster
            require_youtube=True,
        )
        print("\n" + status_msg)
        print("=" * 60)
        if not ready:
            print("[WARN] Not all components ready. Broadcasting may fail.")
            proceed = input("Continue anyway? [Y/n]: ").strip().lower()
            if proceed == 'n':
                return
        print()

    try:
        from modules.platform_integration.antifafm_broadcaster.src import AntifaFMBroadcaster
    except ImportError as e:
        print(f"[ERROR] Broadcaster module not available: {e}")
        input("\nPress Enter to continue...")
        return

    broadcaster = AntifaFMBroadcaster(enable_ai_monitoring=False)
    status = broadcaster.get_status()

    # === PREFLIGHT CHECK ===
    # If stream is running, check health and uptime
    if status['status'] == 'broadcasting':
        uptime_sec = status.get('uptime_seconds', 0) or 0
        uptime_hrs = uptime_sec / 3600
        health = status.get('health', {})
        health_state = health.get('state', 'unknown')
        restart_count = health.get('restart_count', 0)

        print("\n" + "=" * 60)
        print("[PREFLIGHT] Stream is LIVE")
        print("=" * 60)
        print(f"  Uptime:        {status.get('uptime_formatted', 'N/A')} ({uptime_hrs:.1f} hours)")
        print(f"  Health:        {health_state}")
        print(f"  Restarts:      {restart_count}")

        # Check if stream has been running too long (>10 hours)
        if uptime_hrs > 10:
            print()
            print("[WARN] Stream has been running for over 10 hours!")
            print("       Long-running streams can degrade. Restart recommended.")
            print()
            restart = input("Restart stream now? [y/N]: ").strip().lower()
            if restart == 'y':
                print("[RADIO] Restarting broadcast...")
                asyncio.run(broadcaster.stop())
                import time
                time.sleep(3)  # Brief pause before restart
                success = asyncio.run(broadcaster.start())
                if success:
                    print("[OK] Broadcast restarted successfully")
                else:
                    print("[ERROR] Restart failed - check logs")
                status = broadcaster.get_status()
        print("=" * 60)

    while True:
        print("\n" + "-" * 60)
        print(f"Status: {status['status']}")
        print(f"Stream URL: {status['stream_url']}")
        print(f"Visual: {status['visual_path']}")
        print(f"Stream Key: {'configured' if status['stream_key_configured'] else 'NOT SET'}")
        if status['uptime_formatted']:
            print(f"Uptime: {status['uptime_formatted']}")
        print("-" * 60)
        print("1. Start broadcast")
        print("2. Stop broadcast")
        print("3. Refresh status")
        print("4. View telemetry (last 10)")
        print("-" * 60)
        print("== SCHEMA TESTING ==")
        print("5. [TEST] Cycle through all schemas")
        print("6. [TEST] Lookup karaoke lyrics for song")
        print("7. [TEST] View lyrics cache stats")
        print("8. [OPS] Set schema signal (for live switching)")
        print("-" * 60)
        print("== DIAGNOSTICS ==")
        print("9. [HEALTH] View stream health details")
        print("-" * 60)
        print("0. Back")
        print("-" * 60)

        choice = input("antifafm> ").strip()

        if choice == "0":
            break

        if choice == "1":
            if not status['stream_key_configured']:
                print("[ERROR] Set ANTIFAFM_YOUTUBE_STREAM_KEY first")
                input("\nPress Enter to continue...")
                continue
            print("[RADIO] Starting broadcast...")
            success = asyncio.run(broadcaster.start())
            if success:
                print("[OK] Broadcasting to YouTube Live")
            else:
                print("[ERROR] Failed to start broadcast")
            status = broadcaster.get_status()
            continue

        if choice == "2":
            print("[RADIO] Stopping broadcast...")
            asyncio.run(broadcaster.stop())
            print("[OK] Broadcast stopped")
            status = broadcaster.get_status()
            continue

        if choice == "3":
            status = broadcaster.get_status()
            print(f"[OK] Status refreshed: {status['status']}")
            continue

        if choice == "4":
            telemetry_path = broadcaster.telemetry_path
            if telemetry_path.exists():
                import json
                with open(telemetry_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                print(f"\n[TELEMETRY] Last 10 entries from {telemetry_path}:")
                for line in lines[-10:]:
                    try:
                        entry = json.loads(line)
                        print(f"  {entry['timestamp']} | {entry['status']} | uptime={entry['uptime_seconds']:.0f}s")
                    except Exception:
                        print(f"  {line.strip()}")
            else:
                print("[INFO] No telemetry file yet (starts after first broadcast)")
            input("\nPress Enter to continue...")
            continue

        if choice == "5":
            _test_all_schemas()
            continue

        if choice == "6":
            _test_karaoke_lookup()
            continue

        if choice == "7":
            _show_lyrics_cache_stats()
            continue

        if choice == "8":
            _set_schema_signal()
            continue

        if choice == "9":
            # Show detailed health diagnostics
            print("\n[HEALTH] Stream Health Details")
            print("=" * 60)
            status = broadcaster.get_status()
            health = status.get('health', {})
            streamer = status.get('streamer', {})

            print(f"  Status:          {status.get('status', 'unknown')}")
            print(f"  Uptime:          {status.get('uptime_formatted', 'N/A')}")
            uptime_sec = status.get('uptime_seconds', 0) or 0
            print(f"  Uptime (hours):  {uptime_sec / 3600:.2f}")
            print()
            print("  [Health Monitor]")
            print(f"    State:         {health.get('state', 'N/A')}")
            print(f"    Restart count: {health.get('restart_count', 0)}")
            print(f"    Last check:    {health.get('last_check', 'N/A')}")
            print()
            print("  [FFmpeg Streamer]")
            print(f"    Running:       {streamer.get('running', False)}")
            print(f"    Healthy:       {streamer.get('healthy', False)}")
            print(f"    Frame count:   {streamer.get('frame_count', 'N/A')}")

            # Show last 3 telemetry entries
            telemetry_path = broadcaster.telemetry_path
            if telemetry_path.exists():
                import json
                with open(telemetry_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                print()
                print("  [Recent Telemetry]")
                for line in lines[-3:]:
                    try:
                        entry = json.loads(line)
                        print(f"    {entry['timestamp'][:19]} | {entry['status']} | up={entry['uptime_seconds']:.0f}s")
                    except Exception:
                        pass
            print("=" * 60)
            input("\nPress Enter to continue...")
            continue

        print("[ERROR] Invalid choice")


def _test_all_schemas() -> None:
    """Cycle through all schemas and show FFmpeg filters."""
    try:
        from modules.platform_integration.antifafm_broadcaster.src.scheme_manager import (
            SchemeManager, OutputScheme
        )
    except ImportError as e:
        print(f"[ERROR] Could not import scheme_manager: {e}")
        input("\nPress Enter to continue...")
        return

    manager = SchemeManager()
    print("\n[TEST] Cycling through all schemas...")
    print("=" * 60)
    for scheme in OutputScheme:
        manager.set_scheme(scheme)
        filter_str = manager.build_ffmpeg_filter()
        print(f"\n{scheme.value}:")
        print(f"  Filter: {filter_str[:80]}...")
    print("=" * 60)
    input("\nPress Enter to continue...")


def _test_karaoke_lookup() -> None:
    """Test karaoke lyrics lookup for a specific song."""
    try:
        from modules.platform_integration.antifafm_broadcaster.scripts.launch import (
            get_cached_lyrics
        )
    except ImportError as e:
        print(f"[ERROR] Could not import launch: {e}")
        input("\nPress Enter to continue...")
        return

    print("\n[TEST] Karaoke Lyrics Lookup")
    print("=" * 60)
    artist = input("Artist (or Enter for 'UnDaoDu'): ").strip() or "UnDaoDu"
    title = input("Title: ").strip()
    if not title:
        print("[ERROR] Title required")
        input("\nPress Enter to continue...")
        return

    lyrics = get_cached_lyrics(artist, title)
    if lyrics:
        print(f"\n[OK] Found {len(lyrics)} lines:")
        for ts, text in lyrics[:10]:
            mins, secs = ts // 60000, (ts % 60000) // 1000
            print(f"  [{mins:02d}:{secs:02d}] {text[:60]}")
        if len(lyrics) > 10:
            print(f"  ... and {len(lyrics) - 10} more lines")
    else:
        print("[MISS] No lyrics found in cache")
    input("\nPress Enter to continue...")


def _show_lyrics_cache_stats() -> None:
    """Show lyrics cache statistics with source breakdown."""
    try:
        from modules.platform_integration.antifafm_broadcaster.scripts.launch import (
            _get_lyrics_db
        )
    except ImportError as e:
        print(f"[ERROR] Could not import launch: {e}")
        input("\nPress Enter to continue...")
        return

    print("\n[LYRICS CACHE] Statistics")
    print("=" * 60)
    try:
        conn = _get_lyrics_db()
        # Get total
        cursor = conn.execute("SELECT COUNT(*) FROM modules_lyrics_cache")
        total = cursor.fetchone()[0]
        print(f"  Total songs: {total}")

        # Get breakdown by source
        cursor = conn.execute(
            "SELECT source, COUNT(*) FROM modules_lyrics_cache GROUP BY source ORDER BY COUNT(*) DESC"
        )
        print(f"  By source:")
        for source, count in cursor.fetchall():
            print(f"    {source}: {count}")
    except Exception as e:
        print(f"[ERROR] Database error: {e}")
    print("=" * 60)
    input("\nPress Enter to continue...")


def _set_schema_signal() -> None:
    """Set schema signal for live switching."""
    try:
        from modules.platform_integration.antifafm_broadcaster.src.scheme_manager import (
            OutputScheme, write_scheme_signal, read_scheme_signal
        )
    except ImportError as e:
        print(f"[ERROR] Could not import scheme_manager: {e}")
        input("\nPress Enter to continue...")
        return

    print("\n[OPS] Schema Signal Control")
    print("=" * 60)
    print("Available schemas:")
    for i, scheme in enumerate(OutputScheme, 1):
        print(f"  {i}. {scheme.value}")
    print("=" * 60)
    choice = input("\nSelect schema (or Enter to read current): ").strip()
    if not choice:
        current, ts = read_scheme_signal()
        if current:
            print(f"[INFO] Current signal: {current} (set at {ts})")
        else:
            print("[INFO] No signal currently set")
    else:
        try:
            scheme = list(OutputScheme)[int(choice) - 1]
            write_scheme_signal(scheme.value)
            print(f"[OK] Signal set to: {scheme.value}")
        except (ValueError, IndexError):
            print("[ERROR] Invalid selection")
    input("\nPress Enter to continue...")


def _handle_shorts_scheduler_menu() -> None:
    """Handle Shorts Scheduler submenu."""
    # Hot-reload Shorts Scheduler launcher for long-lived menu sessions (0102-first).
    import importlib
    import modules.platform_integration.youtube_shorts_scheduler.scripts.launch as shorts_launch
    shorts_launch = importlib.reload(shorts_launch)
    show_shorts_scheduler_menu = shorts_launch.show_shorts_scheduler_menu
    run_multi_channel_scheduler = shorts_launch.run_multi_channel_scheduler
    run_continuous_scheduler = shorts_launch.run_continuous_scheduler

    while True:
        sched_choice = show_shorts_scheduler_menu()

        if sched_choice == "1":
            # Chrome (9222): Move2Japan + UnDaoDu
            print("\n[CHROME] Scheduling shorts for Move2Japan + UnDaoDu...")
            run_multi_channel_scheduler(browser="chrome", mode="schedule", max_per_channel=9999)
            input("\nPress Enter to continue...")
        elif sched_choice == "2":
            # Edge (9223): FoundUps + antifaFM
            print("\n[EDGE] Scheduling shorts for FoundUps + antifaFM...")
            run_multi_channel_scheduler(browser="edge", mode="schedule", max_per_channel=9999)
            input("\nPress Enter to continue...")
        elif sched_choice == "3":
            # BOTH: Run Chrome AND Edge in parallel
            import concurrent.futures
            print("\n[PARALLEL] Scheduling shorts on Chrome AND Edge simultaneously...")
            print("=" * 60)

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                chrome_future = executor.submit(
                    run_multi_channel_scheduler,
                    browser="chrome", mode="schedule", max_per_channel=9999
                )
                edge_future = executor.submit(
                    run_multi_channel_scheduler,
                    browser="edge", mode="schedule", max_per_channel=9999
                )

                # Wait for both to complete
                chrome_result = chrome_future.result()
                edge_result = edge_future.result()

            print("\n" + "=" * 60)
            print("[COMPLETE] Both browsers finished scheduling")
            print(f"  Chrome: {chrome_result.get('total_scheduled', 0)} scheduled")
            print(f"  Edge: {edge_result.get('total_scheduled', 0)} scheduled")
            input("\nPress Enter to continue...")
        elif sched_choice == "4":
            # CONTINUOUS: Auto-rotate both browsers until Ctrl+C
            print("\n[CONTINUOUS] Starting autonomous rotation mode...")
            print("Press Ctrl+C to stop")
            run_continuous_scheduler(browser="both", mode="schedule", max_per_channel=9999)
            input("\nPress Enter to continue...")
        elif sched_choice == "0":
            break
        else:
            print("[ERROR] Invalid choice")


def _handle_channel_registry_menu() -> None:
    """Add/manage YouTube channels in the shared registry."""
    import re

    def _slugify(value: str) -> str:
        cleaned = re.sub(r"[^a-z0-9]+", "", value.lower())
        return cleaned or value.lower().replace(" ", "")

    while True:
        channels = get_channels()
        print("\n[OPS] Channel Registry")
        print("=" * 60)
        if channels:
            for idx, ch in enumerate(channels, start=1):
                name = ch.get("name", ch.get("key"))
                key = ch.get("key", "")
                cid = ch.get("id", "")
                browser = (ch.get("browser") or {}).get("comment_browser", "chrome")
                roles = ch.get("roles", {})
                role_flags = ",".join([r for r, enabled in roles.items() if enabled])
                print(f"{idx}) {name} ({key}) id={cid} browser={browser} roles={role_flags}")
        else:
            print("[WARN] No channels found in registry.")

        print("-" * 60)
        print("1) Add channel")
        print("0) Back")
        print("=" * 60)

        choice = input("channel-registry> ").strip().lower()
        if choice in {"0", "back", "b", "exit", "quit"}:
            break
        if choice != "1":
            print("[ERROR] Invalid choice")
            continue

        name = input("Channel name (e.g., NewChannel): ").strip()
        if not name:
            print("[ERROR] Channel name is required.")
            continue

        key_default = _slugify(name)
        key = input(f"Channel key [{key_default}]: ").strip().lower() or key_default
        channel_id = input("Channel ID (UC...): ").strip()
        if not channel_id:
            print("[ERROR] Channel ID is required.")
            continue

        handle_default = f"@{name.replace(' ', '')}"
        handle = input(f"Handle [{handle_default}]: ").strip() or handle_default
        timezone_default = "America/New_York"
        timezone = input(f"Timezone [{timezone_default}]: ").strip() or timezone_default

        browser = input("Comment browser (chrome/edge) [chrome]: ").strip().lower() or "chrome"
        if browser not in {"chrome", "edge"}:
            print("[ERROR] Invalid browser. Use chrome or edge.")
            continue

        section_raw = input("Account section (0/1) [0]: ").strip() or "0"
        try:
            account_section = int(section_raw)
        except ValueError:
            print("[ERROR] Invalid account section. Use 0 or 1.")
            continue

        def _yn(prompt: str, default_yes: bool = True) -> bool:
            default = "Y" if default_yes else "N"
            raw = input(f"{prompt} [{default}]: ").strip().lower()
            if not raw:
                return default_yes
            return raw in {"y", "yes", "true", "1"}

        roles = {
            "live_check": _yn("Include in live checks?", True),
            "comments": _yn("Include in comment rotation?", True),
            "shorts": _yn("Include in shorts scheduling?", True),
            "indexing": _yn("Include in indexing rotation?", True),
        }

        channel_payload = {
            "key": key,
            "id": channel_id,
            "name": name,
            "handle": handle,
            "timezone": timezone,
            "roles": roles,
            "browser": {
                "comment_browser": browser,
                "preferred_port": 9222 if browser == "chrome" else 9223,
                "available_ports": [9222, 9223],
                "account_section": account_section,
            },
        }

        ok, msg = add_channel(channel_payload)
        print(f"[{'OK' if ok else 'ERROR'}] {msg}")


def _handle_rotation_controls_menu() -> None:
    """Handle Rotation Controls submenu for account swapping and testing."""
    CHANNELS = []
    for key in get_rotation_order(role="comments"):
        ch = get_channel_by_key(key)
        if ch and ch.get("name"):
            CHANNELS.append(ch["name"])
    if not CHANNELS:
        CHANNELS = ["Move2Japan", "UnDaoDu", "FoundUps", "antifaFM"]

    while True:
        # Get current rotation state from env
        rotation_enabled = env_truthy("YT_ROTATION_ENABLED", "true")
        default_order = ",".join(CHANNELS) if CHANNELS else "Move2Japan,UnDaoDu,FoundUps,antifaFM"
        current_order = os.getenv("YT_ROTATION_ORDER", default_order)
        halt_on_error = env_truthy("YT_ROTATION_HALT_ON_ERROR", "false")

        print("\n[OPS] Rotation Controls - Account Swap/Test")
        print("=" * 60)
        print(f"Rotation: {'ENABLED' if rotation_enabled else 'DISABLED'}")
        print(f"Order: {current_order}")
        print(f"Halt on error: {'YES' if halt_on_error else 'NO'}")
        print("-" * 60)
        print("1. Test swap to channel (with UI-TARS verify)")
        print("2. Check rotation status (current channel)")
        print("3. Toggle rotation (enable/disable)")
        print("4. Toggle halt on error")
        print("5. Set rotation order")
        print("6. Quick swap: Move2Japan -> UnDaoDu")
        print("7. Quick swap: UnDaoDu -> Move2Japan")
        print("-" * 40)
        print("8. [SIMPLE] In-Browser Rotation (Edge: FoundUps → antifaFM)")
        print("9. [SIMPLE] In-Browser Rotation (Chrome: Move2Japan → UnDaoDu)")
        print("0. Back")
        print("=" * 60)

        choice = input("rotation> ").strip()

        if choice in {"0", "back", "b"}:
            break

        if choice == "1":
            # Test swap to channel
            print("\nAvailable channels:")
            for i, ch in enumerate(CHANNELS, 1):
                print(f"  {i}. {ch}")
            ch_choice = input(f"Select channel [1-{len(CHANNELS)}]: ").strip()
            try:
                ch_idx = int(ch_choice) - 1
                if 0 <= ch_idx < len(CHANNELS):
                    target = CHANNELS[ch_idx]
                    print(f"\n[TEST] Swapping to {target}...")
                    _test_swap_to_channel(target)
                else:
                    print("[ERROR] Invalid channel")
            except ValueError:
                print(f"[ERROR] Enter a number 1-{len(CHANNELS)}")
            input("\nPress Enter to continue...")
            continue

        if choice == "2":
            # Check rotation status
            print("\n[STATUS] Checking current channel...")
            _check_rotation_status()
            input("\nPress Enter to continue...")
            continue

        if choice == "3":
            # Toggle rotation
            new_val = "false" if rotation_enabled else "true"
            os.environ["YT_ROTATION_ENABLED"] = new_val
            from modules.infrastructure.cli.src.utilities import update_env_file
            update_env_file("YT_ROTATION_ENABLED", new_val)
            print(f"[OK] Rotation {'ENABLED' if new_val == 'true' else 'DISABLED'}")
            continue

        if choice == "4":
            # Toggle halt on error
            new_val = "false" if halt_on_error else "true"
            os.environ["YT_ROTATION_HALT_ON_ERROR"] = new_val
            from modules.infrastructure.cli.src.utilities import update_env_file
            update_env_file("YT_ROTATION_HALT_ON_ERROR", new_val)
            print(f"[OK] Halt on error: {'YES' if new_val == 'true' else 'NO'}")
            continue

        if choice == "5":
            # Set rotation order
            print("\nCurrent order:", current_order)
            print("Enter new order (comma-separated):")
            print(f"  Example: {default_order}")
            new_order = input("Order: ").strip()
            if new_order:
                os.environ["YT_ROTATION_ORDER"] = new_order
                from modules.infrastructure.cli.src.utilities import update_env_file
                update_env_file("YT_ROTATION_ORDER", new_order)
                print(f"[OK] Rotation order: {new_order}")
            continue

        if choice == "6":
            # Quick swap Move2Japan -> UnDaoDu
            print("\n[QUICK] Move2Japan -> UnDaoDu")
            _test_swap_to_channel("UnDaoDu")
            input("\nPress Enter to continue...")
            continue

        if choice == "7":
            # Quick swap UnDaoDu -> Move2Japan
            print("\n[QUICK] UnDaoDu -> Move2Japan")
            _test_swap_to_channel("Move2Japan")
            input("\nPress Enter to continue...")
            continue

        if choice == "8":
            # Simple In-Browser Rotation - Edge (FoundUps → antifaFM)
            # Uses TarsAccountSwapper directly, no subprocess spawning
            _run_agentic_rotation("edge")
            input("\nPress Enter to continue...")
            continue

        if choice == "9":
            # Simple In-Browser Rotation - Chrome (Move2Japan → UnDaoDu)
            # Uses TarsAccountSwapper directly, no subprocess spawning
            _run_agentic_rotation("chrome")
            input("\nPress Enter to continue...")
            continue

        print("[ERROR] Invalid choice")


def _test_swap_to_channel(target: str) -> None:
    """Test account swapping to a specific channel with UI-TARS verification."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        # Connect to existing Chrome instance
        options = Options()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

        print(f"[INFO] Connecting to Chrome on port 9222...")
        driver = webdriver.Chrome(options=options)
        print(f"[OK] Connected. Current URL: {driver.current_url[:60]}...")

        # Import and run swapper
        from modules.communication.video_comments.skillz.tars_account_swapper.account_swapper_skill import TarsAccountSwapper

        swapper = TarsAccountSwapper(driver, ui_tars_verify=True)
        result = asyncio.run(swapper.swap_to(target, navigate_to_comments=True))

        if result:
            print(f"[OK] Successfully swapped to {target}")
        else:
            print(f"[FAIL] Swap to {target} failed - check logs for details")

    except Exception as e:
        print(f"[ERROR] Swap test failed: {e}")
        import traceback
        traceback.print_exc()


def _check_rotation_status() -> None:
    """Check current rotation status and active channel."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        import re

        # Try Chrome first
        for port, browser in [(9222, "Chrome"), (9223, "Edge")]:
            try:
                options = Options()
                options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
                driver = webdriver.Chrome(options=options)

                url = driver.current_url or ""
                print(f"\n[{browser}] Port {port}")
                print(f"  URL: {url[:80]}...")

                # Extract channel ID from URL
                match = re.search(r"channel/([^/?#]+)", url)
                if match:
                    channel_id = match.group(1)
                    # Map channel ID to name
                    ch = get_channel_by_id(channel_id)
                    channel_name = ch.get("name") if ch else f"Unknown ({channel_id})"
                    print(f"  Active Channel: {channel_name}")
                else:
                    print("  Active Channel: (not on channel page)")

                driver.quit()
            except Exception as e:
                print(f"\n[{browser}] Port {port}: Not connected ({e})")

    except ImportError as e:
        print(f"[ERROR] Selenium not available: {e}")


def _run_agentic_rotation(browser: str) -> None:
    """
    Run the Agentic Rotation Supervisor for a browser.

    This uses the simple in-browser rotation pattern:
    - Connects to browser once (Edge 9223 or Chrome 9222)
    - Uses TarsAccountSwapper to swap between accounts
    - Runs engagement on each channel sequentially
    - Per-channel timeout via asyncio.wait_for (5 min default)
    """
    try:
        from modules.communication.livechat.src.simple_rotation import SimpleRotation

        # Get user settings
        timeout = int(input("Per-channel timeout (seconds, default=300): ").strip() or "300")
        max_comments = int(input("Max comments per channel (default=10): ").strip() or "10")

        channels = ["FoundUps", "antifaFM"] if browser == "edge" else ["Move2Japan", "UnDaoDu"]

        print("")
        print("=" * 60)
        print(f"[ROTATION] Simple In-Browser Rotation - {browser.upper()}")
        print(f"  Timeout: {timeout}s per channel")
        print(f"  Max comments: {max_comments}")
        print(f"  Channels: {' → '.join(channels)}")
        print(f"  Method: TarsAccountSwapper (no subprocess)")
        print("=" * 60)
        print("")

        rotation = SimpleRotation(
            browser=browser,
            channel_timeout=timeout,
        )

        result = asyncio.run(rotation.run_rotation(
            channels=channels,
            max_comments=max_comments,
        ))

        print("")
        print("=" * 60)
        print("[ROTATION] Complete")
        print(f"  Successful: {len(result.successful_channels)}/{len(channels)}")
        print(f"  Total comments: {result.total_comments}")
        print(f"  Time: {result.elapsed_seconds:.1f}s")
        if result.failed_channels:
            print(f"  Failed: {result.failed_channels}")
        print("=" * 60)

    except ImportError as e:
        print(f"[ERROR] Simple rotation not available: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"[ERROR] Rotation failed: {e}")
        import traceback
        traceback.print_exc()
