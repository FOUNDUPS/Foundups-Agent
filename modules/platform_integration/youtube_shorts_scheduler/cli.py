#!/usr/bin/env python3
"""
YouTube Shorts Scheduler - CLI Interface

Agent-callable CLI wrapper for scheduling automation.
Enables IronClaw/OpenClaw to invoke scheduling directly.

WSP Compliance:
    WSP 72: Module Independence (standalone CLI)
    WSP 11: Interface Documentation

Usage:
    python -m modules.platform_integration.youtube_shorts_scheduler.cli --channel move2japan --preflight
    python -m modules.platform_integration.youtube_shorts_scheduler.cli --channel undaodu --video-ids abcdefghijk,lmnopqrstuv --max-videos 1 --preserve-metadata
    python -m modules.platform_integration.youtube_shorts_scheduler.cli --list-channels
"""

import argparse
import asyncio
import json
import importlib.util
import logging
import re
import sys
from urllib.request import urlopen

# UTF-8 enforcement (WSP 90) - entry point only
if __name__ == '__main__' and sys.platform.startswith('win'):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def scheduling_preflight(channel, browser=None):
    """Probe existing local transport only; never launch or authenticate a browser."""
    from .src.channel_config import get_channel_config

    config = get_channel_config(channel)
    if not config:
        return {'success': False, 'status': 'unknown_channel', 'channel': channel}
    port = config['chrome_port']
    expected_browser = 'edge' if port == 9223 else 'chrome'
    result = {
        'channel': channel, 'channel_id': config['id'],
        'browser': expected_browser, 'debug_port': port,
        'timezone': config.get('timezone'), 'main_py_required': False,
        'browser_transport_ready': False, 'authentication': 'unverified',
        'scheduling_verified': False,
        'metadata_generation': 'existing_templates_not_transcript_verified',
    }
    if browser and browser != expected_browser:
        return {**result, 'success': False, 'status': 'browser_channel_mismatch'}
    if importlib.util.find_spec('selenium') is None:
        return {**result, 'success': False, 'status': 'missing_selenium'}
    try:
        # Loopback endpoint, bounded read, no cookies, tokens or page titles returned.
        with urlopen(f'http://127.0.0.1:{port}/json/version', timeout=2) as response:
            version = json.loads(response.read(65536))
        result['browser_transport_ready'] = bool(version.get('webSocketDebuggerUrl'))
    except (OSError, ValueError):
        pass
    ready = result['browser_transport_ready']
    return {**result, 'success': ready,
            'status': 'transport_ready_authentication_unverified' if ready else 'browser_unavailable'}


async def run_scheduling(args):
    """Use the existing scheduler's real async interface and preserve the host browser."""
    from .src.scheduler import YouTubeShortsScheduler

    scheduler = YouTubeShortsScheduler(channel_key=args.channel, dry_run=args.dry_run)
    try:
        if not scheduler.connect_browser():
            return {'success': False, 'status': 'browser_connection_failed'}
        options = {'max_videos': args.max_videos, 'update_metadata': not args.preserve_metadata}
        if getattr(args, 'video_ids', None) is not None:
            options['video_ids'] = args.video_ids
        result = await scheduler.run_scheduling_cycle(**options)
        rows = result.get('scheduled', [])
        errors = result.get('errors', [])
        result.update({
            'success': not bool(errors) and not bool(result.get('error')) and result.get('batch_complete', True),
            'dry_run': args.dry_run,
            'total_scheduled': 0 if args.dry_run else len(rows),
            'total_planned': len(rows) if args.dry_run else 0,
            'metadata_policy': 'preserve' if args.preserve_metadata else 'existing_templates',
            # Legacy DOM success is not independent saved-state evidence.
            'scheduling_verified': False,
            'verification_status': 'preview_only' if args.dry_run else 'independent_readback_required',
        })
        if args.dry_run:
            result['planned'] = result.pop('scheduled', [])
            result['scheduled'] = []
        return result
    finally:
        # This command attaches to a shared host session; don't quit 012's browser.
        scheduler.disconnect()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='YouTube Shorts Scheduler - Agent CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Schedule videos for Move2Japan channel
  python -m modules.platform_integration.youtube_shorts_scheduler.cli --channel move2japan --preflight

  # Schedule with limit
  python -m modules.platform_integration.youtube_shorts_scheduler.cli --channel undaodu --video-ids abcdefghijk,lmnopqrstuv --max-videos 1 --preserve-metadata

  # List available channels
  python -m modules.platform_integration.youtube_shorts_scheduler.cli --list-channels

  # Dry run (show what would be scheduled)
  python -m modules.platform_integration.youtube_shorts_scheduler.cli --channel move2japan --video-ids abcdefghijk,lmnopqrstuv --dry-run --preserve-metadata
        """
    )

    parser.add_argument('--channel', '-c', type=str,
                        help='Channel key: move2japan, undaodu, foundups')
    parser.add_argument('--max-videos', '-m', type=int, default=0,
                        help='Optional processing limit; default 0 schedules the whole batch')
    parser.add_argument('--video-ids', type=str,
                        help='Comma-separated clip IDs in desired order; schedules the entire selected batch')
    parser.add_argument('--list-channels', action='store_true',
                        help='List available channels and exit')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be scheduled without executing')
    parser.add_argument('--preflight', action='store_true',
                        help='Read-only host transport check; no browser launch or scheduling')
    parser.add_argument('--preserve-metadata', action='store_true',
                        help='Schedule without replacing the existing title or description')
    parser.add_argument('--browser', '-b', type=str, default=None,
                        choices=['chrome', 'edge'],
                        help='Validate browser against channel registry (default: registry)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')

    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # List channels mode
    if args.list_channels:
        try:
            from modules.infrastructure.shared_utilities.youtube_channel_registry import get_channels
            channels = get_channels()
            print("\n[CHANNELS] Available for scheduling:")
            for ch in channels:
                print(f"  - {ch['key']}: {ch['name']} ({ch['id']})")
            return 0
        except ImportError as e:
            logger.error(f"Failed to load channel registry: {e}")
            return 1

    # Require channel for scheduling
    if not args.channel:
        parser.error("--channel is required (or use --list-channels)")
    args.channel = args.channel.lower()
    if args.max_videos < 0:
        parser.error("--max-videos must be nonnegative; 0 schedules the whole batch")
    if args.video_ids is not None:
        ids = [item.strip() for item in args.video_ids.split(',')]
        if not ids or any(not re.fullmatch(r'[A-Za-z0-9_-]{11}', item) for item in ids):
            parser.error("--video-ids requires comma-separated 11-character YouTube IDs")
        args.video_ids = list(dict.fromkeys(ids))

    # Recent-clip discovery belongs to the existing publish_daily_clips skill.
    # Until that owner supplies a selection, never fall through to the backlog.
    if not args.preflight and args.video_ids is None:
        print(json.dumps({
            'success': False, 'status': 'clip_selection_required',
            'error': 'Resolve the requested recent clips before scheduling; pass --video-ids.',
        }))
        return 2

    # Execute scheduling
    try:
        result = scheduling_preflight(args.channel, args.browser)
        if result['success'] and not args.preflight:
            result = asyncio.run(run_scheduling(args))
        result['mode'] = 'preflight' if args.preflight else ('preview' if args.dry_run else 'schedule')
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get('success') else 1

    except ImportError as e:
        logger.error(f"Failed to import scheduler: {e}")
        print(json.dumps({'success': False, 'status': 'missing_dependency', 'error': str(e)}))
        return 1
    except Exception as e:
        logger.error(f"Scheduling failed: {e}")
        print(json.dumps({'success': False, 'status': 'scheduling_failed', 'error': str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
