#!/usr/bin/env python3
"""
Periodic Stream Monitor - WSP-compliant
Checks for YouTube streams every 30 minutes using NO-QUOTA method
When stream detected: Posts to LinkedIn/X, initiates 0102 and MAGAdoom

WSP 3: Enterprise Domain Architecture
WSP 87: Alternative detection without API quota
"""

# === UTF-8 ENFORCEMENT (WSP 90) ===
import sys
import io
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===


import os
import sys
import time
import logging
import json
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Add parent path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from modules.platform_integration.stream_resolver.src.no_quota_stream_checker import NoQuotaStreamChecker
from modules.infrastructure.shared_utilities.single_instance import SingleInstanceEnforcer
from utils.env_loader import get_env_variable

logger = logging.getLogger(__name__)


class PeriodicStreamMonitor:
    """Monitor YouTube channels for live streams every 30 minutes"""

    def __init__(self):
        self.checker = NoQuotaStreamChecker()
        self.check_interval = 1800  # 30 minutes in seconds
        self.running = False
        self.last_detected_video_id = None
        self.channels_to_monitor = []

        # Load channels from environment
        self._load_channels()

        # Single instance enforcement
        self.instance_enforcer = SingleInstanceEnforcer("stream_monitor")

        # Session state file
        self.session_file = "memory/stream_session.json"
        self._load_session()

    def _load_channels(self):
        """Load channel configuration"""
        # Primary channels to monitor
        self.channels_to_monitor = [
            {
                'id': 'UC-LSSlOZwpGIRIYihaz8zCw',
                'handle': '@MOVE2JAPAN',
                'name': 'MOVE2JAPAN'
            },
            {
                'id': 'UCSNTUXjAgpd4sgWYP0xoJgw',
                'handle': '@Foundups',
                'name': 'Foundups'
            }
        ]

    def _load_session(self):
        """Load previous session state"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r', encoding="utf-8") as f:
                    session = json.load(f)
                    self.last_detected_video_id = session.get('last_video_id')
                    logger.info(f"[SESSION] Loaded previous video: {self.last_detected_video_id}")
        except Exception as e:
            logger.error(f"[ERROR] Loading session: {e}")

    def _save_session(self):
        """Save current session state"""
        try:
            os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
            with open(self.session_file, 'w', encoding="utf-8") as f:
                json.dump({
                    'last_video_id': self.last_detected_video_id,
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"[ERROR] Saving session: {e}")

    def _trigger_social_media_posting(self, video_data: Dict[str, Any]):
        """Trigger LinkedIn and X posting when stream detected"""
        # antifaFM posts to GeoZai LinkedIn (104834798), not FoundUps LinkedIn (1263645)
        # Routing is handled by channels_config.json
        logger.info("="*60)
        logger.info("[SOCIAL] TRIGGERING SOCIAL MEDIA POSTING")
        logger.info("="*60)

        try:
            # Import social media orchestrator
            from modules.platform_integration.social_media_orchestrator.src.simple_posting_orchestrator import SimplePostingOrchestrator
            import asyncio

            orchestrator = SimplePostingOrchestrator()

            # Prepare stream info
            stream_url = f"https://www.youtube.com/watch?v={video_data['video_id']}"
            stream_title = video_data.get('title', 'Stream')

            logger.info(f"[SOCIAL] Stream Title: {stream_title[:100]}...")
            logger.info(f"[SOCIAL] Stream URL: {stream_url}")

            # Use the orchestrator's post_stream_notification which has duplicate prevention
            logger.info("[SOCIAL] Using orchestrator with database duplicate prevention...")

            # Run the async method in a new event loop
            async def post_async():
                result = await orchestrator.post_stream_notification(
                    stream_title=stream_title,
                    stream_url=stream_url
                )
                return result

            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(post_async())

                # Log results
                if result.all_successful():
                    logger.info(f"[SUCCESS] Posted to {result.success_count} platforms successfully!")
                else:
                    if result.success_count > 0:
                        logger.info(f"[PARTIAL] Posted to {result.success_count}/{len(result.results)} platforms")
                    else:
                        logger.warning(f"[WARNING] No platforms posted successfully")

                    # Log individual platform results
                    for platform_result in result.results:
                        if not platform_result.success:
                            logger.warning(f"[{platform_result.platform.value.upper()}] {platform_result.message}")
                        else:
                            logger.info(f"[{platform_result.platform.value.upper()}] Success")

            finally:
                loop.close()

        except Exception as e:
            logger.error(f"[ERROR] Social media posting failed: {e}")

    def _initiate_0102_orchestrator(self, video_data: Dict[str, Any]):
        """Initiate 0102 orchestrator for stream engagement"""
        logger.info("="*60)
        logger.info("[0102] INITIATING 0102 ORCHESTRATOR")
        logger.info("="*60)

        try:
            # Import 0102 orchestrator
            from importlib import import_module
            ZeroOneZeroTwo = import_module(
                "modules.ai_intelligence.0102_orchestrator.src.zero_one_zero_two"
            ).ZeroOneZeroTwo

            orchestrator = ZeroOneZeroTwo()

            # Activate with stream context
            context = {
                'video_id': video_data['video_id'],
                'title': video_data.get('title', 'Stream'),
                'channel': video_data.get('channel', 'YouTube'),
                'url': f"https://www.youtube.com/watch?v={video_data['video_id']}",
                'timestamp': datetime.now().isoformat()
            }

            logger.info("[0102] Activating orchestrator with stream context...")
            orchestrator.activate(context)
            logger.info("[SUCCESS] 0102 orchestrator activated!")

        except Exception as e:
            logger.error(f"[ERROR] 0102 orchestrator activation failed: {e}")

    def _engage_magadoom_module(self, video_data: Dict[str, Any]):
        """Engage MAGAdoom gamification module"""
        logger.info("="*60)
        logger.info("[MAGADOOM] ENGAGING MAGADOOM MODULE")
        logger.info("="*60)

        try:
            # Check if whack_a_magat module exists
            whack_module_path = "modules/gamification/whack_a_magat/src/magadoom_engagement.py"
            if os.path.exists(whack_module_path):
                from modules.gamification.whack_a_magat.src.magadoom_engagement import MAGAdoomEngagement

                magadoom = MAGAdoomEngagement()

                # Activate with stream data
                logger.info("[MAGADOOM] Activating gamification...")
                magadoom.activate_for_stream({
                    'video_id': video_data['video_id'],
                    'channel': video_data.get('channel'),
                    'viewers': 'Live audience'
                })
                logger.info("[SUCCESS] MAGAdoom module engaged!")
            else:
                logger.info("[INFO] MAGAdoom module not available")

        except Exception as e:
            logger.error(f"[ERROR] MAGAdoom engagement failed: {e}")

    def _initiate_api_system(self, video_data: Dict[str, Any]):
        """Initiate the full API system for chat engagement"""
        logger.info("="*60)
        logger.info("[API] INITIATING API SYSTEM")
        logger.info("="*60)

        try:
            # Set environment variable for YouTube DAE
            os.environ['YOUTUBE_VIDEO_ID'] = video_data['video_id']
            logger.info(f"[API] Set YOUTUBE_VIDEO_ID: {video_data['video_id']}")

            # Import and activate YouTube DAE
            from modules.communication.livechat.src.auto_moderator_dae import YouTubeDAE

            dae = YouTubeDAE()
            logger.info("[API] Starting YouTube DAE for chat engagement...")

            # Run in separate thread to not block monitoring
            dae_thread = threading.Thread(target=dae.run, daemon=True)
            dae_thread.start()

            logger.info("[SUCCESS] API system initiated!")

        except Exception as e:
            logger.error(f"[ERROR] API system initiation failed: {e}")

    def check_for_streams(self) -> Optional[Dict[str, Any]]:
        """Check all channels for live streams"""
        logger.info("\n" + "="*60)
        logger.info(f"[MONITOR] Checking for live streams at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)

        for channel in self.channels_to_monitor:
            logger.info(f"\n[CHECK] Checking {channel['name']} ({channel['handle']})...")

            try:
                # Check for live stream using NO-QUOTA method
                result = self.checker.check_channel_for_live(channel['id'])

                if result and result.get('live'):
                    video_id = result.get('video_id')

                    # Check if this is a new stream
                    if video_id != self.last_detected_video_id:
                        logger.info("="*60)
                        logger.info(f"[NEW STREAM DETECTED] {channel['name']}")
                        logger.info(f"  Video ID: {video_id}")
                        logger.info(f"  Title: {result.get('title', 'Unknown')}")
                        logger.info(f"  URL: https://www.youtube.com/watch?v={video_id}")
                        logger.info("="*60)

                        # Save as last detected
                        self.last_detected_video_id = video_id
                        self._save_session()

                        # Add channel info to result
                        result['channel_name'] = channel['name']
                        result['channel_handle'] = channel['handle']

                        return result
                    else:
                        logger.info(f"[KNOWN] Stream {video_id} already processed")

            except Exception as e:
                logger.error(f"[ERROR] Checking {channel['name']}: {e}")

        logger.info("[MONITOR] No new live streams found")
        return None

    def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("="*60)
        logger.info("[START] Periodic Stream Monitor Started")
        logger.info(f"  Check interval: {self.check_interval} seconds (30 minutes)")
        logger.info(f"  Channels: {', '.join([c['name'] for c in self.channels_to_monitor])}")
        logger.info("="*60)

        while self.running:
            try:
                # Check for streams
                stream_data = self.check_for_streams()

                if stream_data:
                    # New stream detected! Trigger all systems
                    logger.info("\n" + "="*60)
                    logger.info("[ACTIVATION] NEW STREAM - TRIGGERING ALL SYSTEMS")
                    logger.info("="*60)

                    # 1. Post to social media (LinkedIn then X)
                    self._trigger_social_media_posting(stream_data)

                    # 2. Initiate API system for chat
                    self._initiate_api_system(stream_data)

                    # 3. Activate 0102 orchestrator
                    self._initiate_0102_orchestrator(stream_data)

                    # 4. Engage MAGAdoom module
                    self._engage_magadoom_module(stream_data)

                    logger.info("\n" + "="*60)
                    logger.info("[COMPLETE] All systems activated for stream!")
                    logger.info("="*60)

                # Wait for next check (30 minutes)
                logger.info(f"\n[SLEEP] Next check in {self.check_interval} seconds...")
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("\n[STOP] Monitor interrupted by user")
                break
            except Exception as e:
                logger.error(f"[ERROR] Monitor loop error: {e}")
                time.sleep(60)  # Brief delay on error

    def start(self):
        """Start the periodic monitor"""
        if not self.instance_enforcer.acquire_lock():
            logger.error("[ERROR] Another instance of stream monitor is already running")
            return False

        self.running = True
        try:
            self.monitor_loop()
        finally:
            self.running = False
            self.instance_enforcer.release_lock()

        return True

    def stop(self):
        """Stop the monitor"""
        logger.info("[STOP] Stopping stream monitor...")
        self.running = False


def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    monitor = PeriodicStreamMonitor()

    try:
        monitor.start()
    except KeyboardInterrupt:
        logger.info("\n[EXIT] Stream monitor stopped by user")
    except Exception as e:
        logger.error(f"[FATAL] Stream monitor error: {e}")
    finally:
        monitor.stop()


if __name__ == "__main__":
    main()