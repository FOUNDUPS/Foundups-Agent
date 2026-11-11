"""
Chat Poller Component

Handles YouTube Live Chat API polling and message retrieval.
Separated from the main LiveChatListener for better maintainability.

NAVIGATION: Pulls chat batches for LiveChatCore.
-> Called by: livechat_core.py::ChatPoller usage
-> Delegates to: MessageProcessor (via LiveChatCore), QuotaAwarePoller
-> Related: NAVIGATION.py -> MODULE_GRAPH["core_flows"]["message_processing_flow"]
-> Quick ref: NAVIGATION.py -> NEED_TO["poll chat messages"]
"""

import logging
import time
import asyncio
from typing import List, Dict, Any, Optional
import googleapiclient.errors
from utils.throttling import calculate_dynamic_delay

logger = logging.getLogger(__name__)

class ChatPoller:
    """Handles polling YouTube Live Chat API for new messages."""
    
    def __init__(self, youtube_service, live_chat_id, channel_name=None, channel_id=None):
        self.youtube = youtube_service
        self.live_chat_id = live_chat_id
        self.channel_name = channel_name or "StreamOwner"
        self.channel_id = channel_id or "owner"
        self.next_page_token = None
        self.poll_interval_ms = 10000  # Default: 10 seconds
        self.error_backoff_seconds = 5  # Initial backoff for errors
        self.max_backoff_seconds = 60  # Maximum backoff time
        self.first_poll = True  # Track if this is the first poll
        self.connection_time = None  # Track when we connected
        
        # Deduplication tracking - prevent counting same timeout multiple times
        self.seen_event_ids = set()  # Track event IDs we've already processed
        self.event_dedup_window = {}  # Track recent events by key for deduplication
        
    async def poll_messages(self, viewer_count: int = 100) -> List[Dict[str, Any]]:
        """
        Poll the YouTube API for new chat messages.
        
        Args:
            viewer_count: Current viewer count for dynamic delay calculation
            
        Returns:
            List of new chat messages
        """
        try:
            logger.debug(f"[REFRESH] Polling chat messages for live chat ID: {self.live_chat_id}")
            
            response = await self._make_api_call()
            
            # Update polling interval based on server response
            self._update_polling_interval(response, viewer_count)
            
            # Reset error backoff on success
            self.error_backoff_seconds = 5
            
            items = response.get("items", [])
            messages = []
            
            for item in items:
                if "snippet" in item:
                    snippet = item["snippet"]
                    author = item.get("authorDetails", {})
                    event_type = snippet.get("type")

                    # Preserve the available initial text batch without replaying
                    # old commands, donations or response triggers after reconnect.
                    if (self.first_poll and snippet.get("displayMessage")
                            and event_type not in {"messageDeletedEvent", "userBannedEvent"}):
                        messages.append({**item, "_capture_only": True})
                        continue
                    
                    # Handle moderation events (bans/timeouts)
                    if event_type == "messageDeletedEvent":
                        deleted_details = snippet.get("messageDeletedDetails", {})
                        # authorDetails should contain the moderator who deleted the message
                        moderator_name = author.get("displayName", self.channel_name) if author else self.channel_name
                        moderator_id = author.get("channelId", self.channel_id) if author else self.channel_id
                        # The deleted message text contains the target info
                        deleted_text = deleted_details.get("deletedMessageText", "")
                        target_name = "MAGAT"  # We don't know who was deleted from this event
                        published_at = snippet.get("publishedAt", "")
                        
                        # Skip old events on first poll (historical data)
                        if self.first_poll:
                            logger.debug(f"⏭️ Skipping historical timeout: {target_name}")
                        else:
                            logger.info(f"[U+1F528] TIMEOUT EVENT DETECTED! Target: {target_name} by {moderator_name}")
                            messages.append({
                                "type": "timeout_event",
                                "deleted_text": deleted_text,
                                "target_name": target_name,
                                "target_channel_id": "",  # We don't know the target's channel ID
                                # Use the moderator info from authorDetails
                                "moderator_name": moderator_name,  
                                "moderator_id": moderator_id,
                                "duration_seconds": 10,  # Message deletion is typically 10s timeout
                                "published_at": published_at,
                                "is_live": True  # This is a live timeout
                            })
                    elif event_type == "userBannedEvent":
                        ban_details = snippet.get("userBannedDetails", {})
                        banned_user = ban_details.get("bannedUserDetails", {})
                        target_name = banned_user.get("displayName", "MAGAT")
                        published_at = snippet.get("publishedAt", "")
                        
                        # Create deduplication key
                        event_id = item.get("id", "")
                        mod_id = author.get("channelId", self.channel_id) if author else self.channel_id
                        mod_name = author.get("displayName", self.channel_name) if author else self.channel_name
                        target_id = banned_user.get("channelId", "")
                        dedup_key = f"{mod_id}:{target_id}:{published_at}"
                        
                        # Skip if we've already processed this exact event
                        if event_id and event_id in self.seen_event_ids:
                            logger.debug(f"⏭️ Skipping duplicate ban event ID: {event_id}")
                            continue
                        
                        # Skip if we've seen this EXACT mod/target/time combo recently (within 0.5 seconds)
                        # This prevents true duplicates but allows rapid-fire timeouts on same target
                        current_time = time.time()
                        if dedup_key in self.event_dedup_window:
                            if current_time - self.event_dedup_window[dedup_key] < 0.5:
                                logger.debug(f"⏭️ Skipping duplicate ban: {mod_name} -> {target_name} (exact same timestamp)")
                                continue
                            else:
                                # Same target but different time - this is a multi-whack!
                                logger.info(f"[U+1F525] RAPID TIMEOUT: {mod_name} -> {target_name} again!")
                        
                        # Mark as seen
                        if event_id:
                            self.seen_event_ids.add(event_id)
                        self.event_dedup_window[dedup_key] = current_time
                        
                        # Clean old dedup entries (older than 60 seconds)
                        self.event_dedup_window = {k: v for k, v in self.event_dedup_window.items() 
                                                  if current_time - v < 60}
                        
                        # Skip old events on first poll (historical data)
                        if self.first_poll:
                            logger.debug(f"⏭️ Skipping historical ban: {target_name}")
                        else:
                            # Log the ban with clear details
                            duration = ban_details.get("banDurationSeconds", 0)
                            is_perm = ban_details.get("banType") == "permanent"
                            ban_type = "PERMABAN" if is_perm else f"{duration}s timeout"
                            logger.info(f"[TARGET] FRAG: {mod_name} -> {target_name} ({ban_type})")
                            
                            # Track unique targets for multi-whack detection
                            if not hasattr(self, 'recent_targets'):
                                self.recent_targets = {}
                            
                            mod_targets_key = f"{mod_id}:{current_time//10}"  # Group by 10-second windows
                            if mod_targets_key not in self.recent_targets:
                                self.recent_targets[mod_targets_key] = set()
                            self.recent_targets[mod_targets_key].add(target_name)
                            
                            # Log if this is part of a multi-whack
                            target_count = len(self.recent_targets[mod_targets_key])
                            if target_count > 1:
                                logger.info(f"[U+1F525] MULTI-WHACK: {mod_name} has {target_count} frags in 10s!")
                            
                            # Debug: Show all frags in this window
                            logger.debug(f"[DATA] {mod_name}'s 10s window: {self.recent_targets[mod_targets_key]}")
                            messages.append({
                                "type": "ban_event",
                                "target_name": target_name,
                                "target_channel_id": target_id,
                                # Use the deduplicated moderator info
                                "moderator_name": mod_name,
                                "moderator_id": mod_id,
                                "is_permanent": ban_details.get("banType") == "permanent",
                                "duration_seconds": ban_details.get("banDurationSeconds", 0),
                                "published_at": published_at,
                                "is_live": True  # This is a live ban
                            })

                    elif event_type == "superChatEvent":
                        # Super Chat event - extract purchase amount and message
                        super_chat_details = snippet.get("superChatDetails", {})
                        amount_micros = super_chat_details.get("amountMicros", 0)
                        amount_usd = amount_micros / 1_000_000  # Convert micros to dollars
                        currency = super_chat_details.get("currency", "USD")
                        amount_display = super_chat_details.get("amountDisplayString", f"${amount_usd:.2f}")
                        user_comment = super_chat_details.get("userComment", "")
                        tier = super_chat_details.get("tier", 0)

                        donor_name = author.get("displayName", "Anonymous")
                        donor_id = author.get("channelId", "")
                        published_at = snippet.get("publishedAt", "")

                        # Skip historical Super Chats on first poll
                        if self.first_poll:
                            logger.debug(f"⏭️ Skipping historical Super Chat from {donor_name}")
                        else:
                            logger.info(f"💰 SUPER CHAT: {donor_name} donated {amount_display} ({currency}) - Tier {tier}")
                            if user_comment:
                                logger.info(f"💬 Super Chat message: {user_comment}")

                            messages.append({
                                "type": "super_chat_event",
                                "donor_name": donor_name,
                                "donor_id": donor_id,
                                "amount_micros": amount_micros,
                                "amount_usd": amount_usd,
                                "currency": currency,
                                "amount_display": amount_display,
                                "message": user_comment,
                                "tier": tier,
                                "published_at": published_at,
                                "is_live": True
                            })

                    else:
                        # Regular chat message - skip historical messages on first poll
                        if self.first_poll:
                            logger.debug(f"⏭️ Skipping historical message on first poll")
                        else:
                            # Return full item for processing
                            messages.append(item)
            
            # After first poll, mark as no longer first
            if self.first_poll:
                self.first_poll = False
                self.connection_time = time.time()
                if messages:
                    logger.info(f"[CAPTURE] Retaining {len(messages)} initial text messages without reply processing")
            
            if messages:
                logger.debug(f"📨 Received {len(messages)} new items")
            else:
                logger.debug("📭 No new messages")
                
            return messages
            
        except googleapiclient.errors.HttpError as e:
            logger.error(f"[FAIL] API Error polling messages: {e}")
            raise  # Let the caller handle auth errors
        except Exception as e:
            logger.error(f"[FAIL] Unexpected error polling chat: {e}")
            await self._handle_polling_error()
            return []
    
    async def _make_api_call(self) -> Dict[str, Any]:
        """Make the actual API call to get chat messages."""
        # Check if we're in NO-QUOTA mode
        if not self.youtube or not self.live_chat_id:
            # NO-QUOTA mode - can't fetch messages without API
            # Return empty response to prevent errors
            return {
                "items": [],
                "pollingIntervalMillis": 30000,  # Default 30s interval
                "nextPageToken": None
            }

        # Run the synchronous API call in a thread to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.youtube.liveChatMessages().list(
                liveChatId=self.live_chat_id,
                part="snippet,authorDetails",
                pageToken=self.next_page_token
            ).execute()
        )
    
    def _update_polling_interval(self, response: Dict[str, Any], viewer_count: int):
        """Update polling interval based on server response and viewer count."""
        # Get server's recommended polling interval
        server_poll_interval = response.get("pollingIntervalMillis", 10000)
        if not isinstance(server_poll_interval, int):
            server_poll_interval = 10000  # Safe default for mock mode
        
        # Calculate dynamic delay based on viewer count
        try:
            if isinstance(viewer_count, int):
                dynamic_delay = calculate_dynamic_delay(viewer_count)
            else:
                dynamic_delay = 10.0  # Safe default
        except Exception:
            dynamic_delay = 10.0  # Fallback delay
        
        # Use the larger of server's interval or our calculated interval
        self.poll_interval_ms = max(server_poll_interval, int(dynamic_delay * 1000))
        
        # Update next page token
        self.next_page_token = response.get("nextPageToken")
        
        logger.debug(f"⏱️ Updated poll interval: {self.poll_interval_ms}ms")
    
    async def _handle_polling_error(self):
        """Handle polling errors with exponential backoff."""
        logger.warning(f"⏳ Backing off for {self.error_backoff_seconds} seconds")
        await asyncio.sleep(self.error_backoff_seconds)
        
        # Exponential backoff with maximum limit
        self.error_backoff_seconds = min(self.error_backoff_seconds * 2, self.max_backoff_seconds)
    
    def get_poll_interval_seconds(self) -> float:
        """Get the current polling interval in seconds."""
        return self.poll_interval_ms / 1000.0
    
    def reset_polling_state(self):
        """Reset polling state (useful after reconnection)."""
        self.next_page_token = None
        self.error_backoff_seconds = 5
        logger.info("[REFRESH] Polling state reset")
