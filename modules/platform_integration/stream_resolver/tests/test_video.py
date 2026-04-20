
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

import logging
from utils.logging_config import setup_logging
from modules.platform_integration.youtube_auth.src.youtube_auth import get_authenticated_service
from modules.platform_integration.stream_resolver.src import check_video_details
from utils.env_loader import get_env_variable

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def main():
    # Get the video ID from environment
    video_id = get_env_variable("YOUTUBE_VIDEO_ID")
    if not video_id:
        logger.error("No video ID found in environment variables")
        return

    logger.info(f"Checking details for video ID: {video_id}")

    try:
        # Get authenticated service (updated to use new oauth_management module)
        auth_result = get_authenticated_service()
        if not auth_result:
            logger.error("Failed to get authenticated service")
            return
            
        youtube_service, credentials = auth_result

        # Check video details
        video_details = check_video_details(youtube_service, video_id)
        if video_details:
            logger.info("Video details:")
            logger.info(f"Title: {video_details.get('snippet', {}).get('title')}")
            logger.info(f"Status: {video_details.get('snippet', {}).get('status', {}).get('privacyStatus')}")
            live_details = video_details.get('liveStreamingDetails', {})
            if live_details:
                logger.info("Livestream details:")
                logger.info(f"Actual start time: {live_details.get('actualStartTime')}")
                logger.info(f"Actual end time: {live_details.get('actualEndTime')}")
                logger.info(f"Scheduled start time: {live_details.get('scheduledStartTime')}")
                logger.info(f"Concurrent viewers: {live_details.get('concurrentViewers')}")
            else:
                logger.info("No livestream details found")
        else:
            logger.error("Video not found or no details available")

    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    main() 
