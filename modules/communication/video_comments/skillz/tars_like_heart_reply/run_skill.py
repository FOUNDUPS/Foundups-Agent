"""
0102 Comment Engagement Skill Runner
====================================

WSP 96 Compliant skill execution entry point.
Invokes the CommentEngagementDAE for autonomous Like + Heart + Reply.

Usage:
    python run_skill.py --max-comments 5 --reply-text "0102 was here"
    python run_skill.py --channel UC-LSSlOZwpGIRIYihaz8zCw --dom-only
    python run_skill.py --browser-port 9223  # Edge for FoundUps
"""

import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(repo_root))

# ═══════════════════════════════════════════════════════════════════════════
# CRITICAL: Pre-parse --browser-port BEFORE importing DAE
# The DAE reads FOUNDUPS_CHROME_PORT at module level, so we must set it first.
# ═══════════════════════════════════════════════════════════════════════════
_preparse = argparse.ArgumentParser(add_help=False)
_preparse.add_argument("--browser-port", type=int, default=9222)
_preargs, _ = _preparse.parse_known_args()
os.environ["FOUNDUPS_CHROME_PORT"] = str(_preargs.browser_port)
#
# IMPORTANT (WSP 50: never assume): port-based automation may target Chrome (9222) OR Edge (9223).
# ActionRouter needs an explicit browser type hint because FoundUpsDriver is ChromeDriver-based.
_edge_port_env = os.getenv("FOUNDUPS_EDGE_PORT") or os.getenv("EDGE_DEBUG_PORT") or "9223"
try:
    _edge_port = int(str(_edge_port_env).strip())
except Exception:
    _edge_port = 9223
browser_type = "edge" if _preargs.browser_port == _edge_port else "chrome"
os.environ["FOUNDUPS_BROWSER_TYPE"] = browser_type
os.environ["ACTION_ROUTER_BROWSER_TYPE"] = browser_type
os.environ["BROWSER_DEBUG_PORT"] = str(_preargs.browser_port)

# Load environment variables (e.g., GROK_API_KEY/XAI_API_KEY) for intelligent replies.
# This is intentionally done before importing skill modules so they see the env on import.
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(dotenv_path=repo_root / ".env", override=False)
except Exception:
    pass

from modules.communication.video_comments.skillz.tars_like_heart_reply.comment_engagement_dae import (
    CommentEngagementDAE,
    execute_skill
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def _resolve_channel_id(channel_arg: str) -> str:
    """
    Resolve a channel argument to a concrete YouTube channel id.

    Supports either:
    - Raw channel id: "UC...."
    - Named aliases: "move2japan" | "undaodu" | "antifafm"

    Channel IDs are read from environment to allow 012 to reconfigure without code edits.
    """
    raw = (channel_arg or "").strip()
    if not raw:
        return os.getenv("MOVE2JAPAN_CHANNEL_ID", "UC-LSSlOZwpGIRIYihaz8zCw")

    # If it already looks like a channel id, pass through.
    if raw.startswith("UC") and len(raw) >= 10:
        return raw

    alias = raw.lower()
    if alias in {"move2japan", "m2j"}:
        return os.getenv("MOVE2JAPAN_CHANNEL_ID", "UC-LSSlOZwpGIRIYihaz8zCw")
    if alias in {"undaodu", "ud"}:
        return os.getenv("UNDAODU_CHANNEL_ID", "UCfHM9Fw9HD-NwiS0seD_oIA")
    if alias in {"antifafm", "antifa", "ravingantifa", "ra"}:  # ravingantifa = legacy alias
        return os.getenv("ANTIFAFM_CHANNEL_ID", "UCVSmg5aOhP4tnQ9KFUg97qA")

    # Unknown alias: assume caller intended a raw id.
    return raw


# Default channel (env-driven)
DEFAULT_CHANNEL = os.getenv("MOVE2JAPAN_CHANNEL_ID", "UC-LSSlOZwpGIRIYihaz8zCw")  # Move2Japan


def _final_heartbeat(result):
    """A comments halt is a distinct settled outcome, including failed persistence."""
    import time
    from modules.communication.livechat.src.automation_gates import comments_exit_code
    stats = result.get('stats', {}) if isinstance(result, dict) else {}
    return {'timestamp': time.time(), 'comments_processed': stats.get('comments_processed', 0),
            'state': 'halted' if comments_exit_code(result) else 'completed'}


async def main():
    parser = argparse.ArgumentParser(
        description="0102 Autonomous Comment Engagement",
        epilog="""
Preset Profiles (simplifies switch management):
  --profile=heart-only    : Only heart (fast, testing)
  --profile=like-heart    : Like + Heart (no replies)
  --profile=full          : All actions (production)
  --profile=test          : Heart only + fast mode

Or use individual switches for custom configuration.
        """
    )

    # Preset profile switch (simplifies configuration)
    parser.add_argument(
        "--profile",
        type=str,
        choices=["heart-only", "like-heart", "full", "test", "occam"],
        help="Preset configuration profile (overrides individual switches)"
    )

    parser.add_argument(
        "--channel",
        type=str,
        default=DEFAULT_CHANNEL,
        help="YouTube channel ID (UC...) or alias: move2japan | undaodu | antifafm"
    )
    parser.add_argument(
        "--video",
        type=str,
        default=None,
        help="YouTube video ID (for live stream comments, otherwise uses channel inbox)"
    )
    parser.add_argument(
        "--max-comments",
        type=int,
        default=5,
        help="Max comments to process"
    )
    parser.add_argument(
        "--reply-text",
        type=str,
        default="",
        help="Reply text (empty = no reply)"
    )
    # Action switches (simplified per user request: Like+Heart are similar, one switch)
    parser.add_argument(
        "--no-engagement",
        action="store_true",
        help="Skip Like + Heart (both are simple DOM clicks)"
    )
    parser.add_argument(
        "--no-like",
        action="store_true",
        help="Skip like action only (use with --no-engagement for neither)"
    )
    parser.add_argument(
        "--no-heart",
        action="store_true",
        help="Skip heart action only (use with --no-engagement for neither)"
    )
    parser.add_argument(
        "--no-reply",
        action="store_true",
        help="Skip ALL reply functionality (no replies posted)"
    )

    # Reply layer switches (for incremental testing of refactored code)
    parser.add_argument(
        "--reply-basic-only",
        action="store_true",
        help="Basic reply posting ONLY (skip AI: no intelligent generation, classification, semantic state)"
    )
    parser.add_argument(
        "--no-classification",
        action="store_true",
        help="Skip commenter classification layer (Layer 3)"
    )
    parser.add_argument(
        "--no-semantic-state",
        action="store_true",
        help="Skip semantic state computation (WSP 44, Layer 4)"
    )
    parser.add_argument(
        "--dom-only",
        action="store_true",
        help="DOM only (no vision verification)"
    )
    parser.add_argument(
        "--no-refresh",
        action="store_true",
        help="Don't refresh page between batches"
    )
    parser.add_argument(
        "--no-intelligent-reply",
        action="store_true",
        help="Disable intelligent reply (use custom --reply-text only)"
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output result as JSON for subprocess parsing"
    )
    parser.add_argument(
        "--debug-tags",
        action="store_true",
        help="Append debug tags to posted replies (commenter type + WSP44 state)"
    )
    parser.add_argument(
        "--fast-mode",
        action="store_true",
        help="FAST tempo (10x faster, 0.1x delays) - rapid testing"
    )
    parser.add_argument(
        "--medium-mode",
        action="store_true",
        help="MEDIUM tempo (4x faster, 0.25x delays) - quick diagnostics"
    )
    parser.add_argument(
        "--browser-port",
        type=int,
        default=9222,
        help="Browser debug port (9222=Chrome, 9223=Edge)"
    )
    parser.add_argument(
        "--heartbeat-file",
        type=str,
        default=None,
        help="Path to heartbeat file for supervisor monitoring (rotation_supervisor)"
    )

    args = parser.parse_args()

    # Resolve channel alias → concrete channel id (WSP 50: never assume)
    args.channel = _resolve_channel_id(args.channel)

    # Note: browser_port env var already set at module level (pre-parse)
    # This ensures CHROME_PORT is correct before DAE import

    # Apply YT_ENGAGEMENT_TEMPO if set in environment (priority)
    tempo = os.getenv("YT_ENGAGEMENT_TEMPO", "012").upper()
    if args.fast_mode:
        tempo = "FAST"
    elif args.medium_mode:
        tempo = "MEDIUM"

    os.environ["YT_ENGAGEMENT_TEMPO"] = tempo

    # Apply preset profile (overrides individual switches)
    if args.profile:
        if args.profile == "heart-only":
            args.no_engagement = False
            args.no_like = True  # Only heart
            args.no_heart = False
            args.no_reply = True
            args.medium_mode = False
        elif args.profile == "like-heart":
            args.no_engagement = False
            args.no_reply = True
            args.medium_mode = False
        elif args.profile == "full":
            args.no_engagement = False
            args.no_like = False
            args.no_heart = False
            args.no_reply = False
            args.medium_mode = False
        elif args.profile == "test":
            args.no_engagement = False
            args.no_like = True  # Only heart
            args.no_heart = False
            args.no_reply = True
            args.medium_mode = True
        elif args.profile == "occam":
            # Occam's Razor Debugging: Strip logic, test mechanisms
            args.no_engagement = False
            args.no_like = False
            args.no_heart = False 
            args.no_reply = False # Test reply flow
            
            # Use standard 012 mode (tempo=1.0) to reproduce delay issue
            args.medium_mode = False
            args.fast_mode = False
            
            # Set Occam bypass in environment
            os.environ["YT_OCCAM_MODE"] = "true"
            os.environ["YT_REPLY_BASIC_ONLY"] = "true"
            logger.info("[PROFILE] OCCAM MODE ACTIVATED: AI/DB layers DISABLED.")

    # Apply --no-engagement (overrides --no-like and --no-heart)
    if args.no_engagement:
        args.no_like = True
        args.no_heart = True

    if args.debug_tags:
        os.environ["YT_REPLY_DEBUG_TAGS"] = "1"

    # Set reply layer switches via environment (read by CommentProcessor)
    if args.reply_basic_only:
        os.environ["YT_REPLY_BASIC_ONLY"] = "1"
    if args.no_classification:
        os.environ["YT_NO_CLASSIFICATION"] = "1"
    if args.no_semantic_state:
        os.environ["YT_NO_SEMANTIC_STATE"] = "1"

    # Suppress banner if JSON output mode
    if not args.json_output:
        print(f"\n{'='*60}")
        print(" 0102 COMMENT ENGAGEMENT SKILL")
        print(f"{'='*60}")
        if args.profile:
            print(f" Profile: {args.profile.upper()}")
        print(f" Configuration:")
        print(f"   Channel: {args.channel}")
        print(f"   Video: {args.video or '(channel inbox)'}")
        print(f"   Max comments: {args.max_comments}")
        print(f" Action Switches:")
        print(f"   Engagement: {'OFF (no like/heart)' if args.no_engagement else 'ON'}")
        print(f"   Like: {'ON' if not args.no_like else 'OFF'} | Heart: {'ON' if not args.no_heart else 'OFF'}")
        print(f"   Reply: {'OFF' if args.no_reply else 'ON'}")
        if not args.no_reply:
            print(f" Reply Layers:")
            if args.reply_basic_only:
                print(f"   Mode: BASIC ONLY (DOM posting, no AI)")
            else:
                print(f"   Layer 1 (DOM Posting): ON")
                print(f"   Layer 2 (AI Generation): {'ON' if not args.no_intelligent_reply else 'OFF'}")
                print(f"   Layer 3 (Classification): {'ON' if not args.no_classification else 'OFF'}")
                print(f"   Layer 4 (Semantic State): {'ON' if not args.no_semantic_state else 'OFF'}")
                print(f"   Layer 5 (Debug Tags): {'ON' if args.debug_tags else 'OFF'}")
        print(f" Feature Switches:")
        print(f"   Vision: {'ON' if not args.dom_only else 'OFF'}")
        print(f"   Refresh Between: {'ON' if not args.no_refresh else 'OFF'}")
        print(f"   Tempo: {tempo} ({'10x faster' if tempo == 'FAST' else '4x faster' if tempo == 'MEDIUM' else 'Human-like'})")
        print(f"{'='*60}\n")

    # WSP 91: DAEmon Observability - Log ALL configuration switches
    logger.info(f"[DAEMON][DAE-INIT] 🎬 Initializing Comment Engagement DAE...")
    logger.info(f"[DAEMON][DAE-INIT] Configuration:")
    logger.info(f"[DAEMON][DAE-INIT]   Channel: {args.channel}")
    logger.info(f"[DAEMON][DAE-INIT]   Video: {args.video or 'None (Studio inbox)'}")
    logger.info(f"[DAEMON][DAE-INIT]   Max comments: {args.max_comments} (0=UNLIMITED)")
    logger.info(f"[DAEMON][DAE-INIT] Action Switches:")
    logger.info(f"[DAEMON][DAE-INIT]   do_like: {not args.no_like}")
    logger.info(f"[DAEMON][DAE-INIT]   do_heart: {not args.no_heart}")
    logger.info(f"[DAEMON][DAE-INIT]   do_reply: {not args.no_reply}")
    logger.info(f"[DAEMON][DAE-INIT]   use_intelligent_reply: {not args.no_intelligent_reply}")
    if not args.no_reply:
        logger.info(f"[DAEMON][DAE-INIT] Reply Layer Switches:")
        logger.info(f"[DAEMON][DAE-INIT]   reply_basic_only: {args.reply_basic_only} {'(skip AI layers 2-5)' if args.reply_basic_only else ''}")
        logger.info(f"[DAEMON][DAE-INIT]   no_classification: {args.no_classification} {'(skip Layer 3)' if args.no_classification else ''}")
        logger.info(f"[DAEMON][DAE-INIT]   no_semantic_state: {args.no_semantic_state} {'(skip Layer 4)' if args.no_semantic_state else ''}")
        logger.info(f"[DAEMON][DAE-INIT]   debug_tags: {args.debug_tags} {'(Layer 5 enabled)' if args.debug_tags else '(Layer 5 disabled)'}")
    logger.info(f"[DAEMON][DAE-INIT] Feature Switches:")
    logger.info(f"[DAEMON][DAE-INIT]   use_vision: {'enabled' if not args.dom_only else 'disabled (DOM-only)'}")
    logger.info(f"[DAEMON][DAE-INIT]   refresh_between: {not args.no_refresh}")
    tempo_multipliers = {'FAST': '0.1x', 'MEDIUM': '0.25x'}
    multiplier = tempo_multipliers.get(tempo, '1.0x')
    logger.info(f"[DAEMON][DAE-INIT]   engagement_tempo: {tempo} (multiplier: {multiplier})")

    from modules.communication.livechat.src.automation_gates import comment_stop_result
    halted = comment_stop_result()
    if halted:
        if args.json_output:
            import json
            print(json.dumps(halted))
        return halted
    dae = CommentEngagementDAE(
        channel_id=args.channel,
        video_id=args.video,
        use_vision=not args.dom_only,
        use_dom=True
    )

    # Heartbeat task for rotation supervisor monitoring
    heartbeat_task = None
    heartbeat_stop = asyncio.Event()

    async def _heartbeat_writer():
        """Background task to write heartbeat file for supervisor."""
        from pathlib import Path
        import json
        import time

        while not heartbeat_stop.is_set():
            try:
                # Get stats from DAE if available
                stats = getattr(dae, '_current_stats', {})
                heartbeat_data = {
                    "timestamp": time.time(),
                    "comments_processed": stats.get("comments_processed", 0),
                    "likes": stats.get("likes", 0),
                    "hearts": stats.get("hearts", 0),
                    "replies": stats.get("replies", 0),
                    "channel": args.channel,
                    "state": "running",
                }
                Path(args.heartbeat_file).write_text(json.dumps(heartbeat_data))
            except Exception:
                pass  # Non-critical
            await asyncio.sleep(5)  # Write every 5s

    try:
        browser_type = "Edge" if args.browser_port == 9223 else "Chrome"
        logger.info(f"[DAEMON][DAE-CONNECT] 🔌 Connecting to {browser_type} (port {args.browser_port})...")
        await dae.connect()
        logger.info(f"[DAEMON][DAE-CONNECT] ✅ Connected successfully")

        # Start heartbeat writer if supervisor provided heartbeat file
        if args.heartbeat_file:
            logger.info(f"[DAEMON][HEARTBEAT] Starting heartbeat writer → {args.heartbeat_file}")
            heartbeat_task = asyncio.create_task(_heartbeat_writer())

        logger.info(f"[DAEMON][DAE-NAVIGATE] 🧭 Navigating to inbox...")
        await dae.navigate_to_inbox()
        logger.info(f"[DAEMON][DAE-NAVIGATE] ✅ Navigation complete")

        logger.info(f"[DAEMON][DAE-ENGAGE] 🎯 Starting comment engagement...")
        logger.info(f"[DAEMON][DAE-ENGAGE]   Actions: Like={not args.no_like} | Heart={not args.no_heart} | Reply={not args.no_reply}")
        logger.info(f"[DAEMON][DAE-ENGAGE]   Intelligent replies: {not args.no_intelligent_reply}")
        logger.info(f"[DAEMON][DAE-ENGAGE]   Refresh between batches: {not args.no_refresh}")

        result = await dae.engage_all_comments(
            max_comments=args.max_comments,
            do_like=not args.no_like,
            do_heart=not args.no_heart,
            do_reply=not args.no_reply,
            reply_text=args.reply_text,
            refresh_between=not args.no_refresh,
            use_intelligent_reply=not args.no_intelligent_reply
        )

        logger.info(f"[DAEMON][DAE-COMPLETE] ✅ Engagement complete: {result.get('stats', {})}")
        
        # Output JSON if requested (for subprocess parsing)
        if args.json_output:
            import json
            print(json.dumps(result, default=str))
        
        return result
        
    except Exception as e:
        logger.error(f"[DAEMON][DAE-ERROR] ❌ FATAL ERROR: {e}")
        logger.error(f"[ERROR] Skill execution failed: {e}", exc_info=True)
        error_result = {'error': str(e), 'stats': {'comments_processed': 0, 'errors': 1}}
        if args.json_output:
            import json
            print(json.dumps(error_result))
        return error_result

    finally:
        # Stop heartbeat writer
        if heartbeat_task:
            heartbeat_stop.set()
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            # Write final heartbeat
            if args.heartbeat_file:
                try:
                    from pathlib import Path
                    import json
                    import time
                    final_data = _final_heartbeat(result if 'result' in dir() else None)
                    Path(args.heartbeat_file).write_text(json.dumps(final_data))
                except Exception:
                    pass

        logger.info(f"[DAEMON][DAE-CLEANUP] 🧹 Closing DAE connection...")
        dae.close()
        logger.info(f"[DAEMON][DAE-CLEANUP] ✅ Cleanup complete")


if __name__ == "__main__":
    from modules.communication.livechat.src.automation_gates import comments_exit_code
    raise SystemExit(comments_exit_code(asyncio.run(main())))
