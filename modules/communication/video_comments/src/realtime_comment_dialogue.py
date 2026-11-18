"""
Real-time Comment Dialogue System - WSP 27/80 Compliant
Enables real-time back-and-forth conversations in YouTube comments
Similar to Facebook/Messenger comment threading

Enhanced with browser-based like capability (WSP V5 integration)
- API for replies (fast, reliable)
- UI-TARS Vision for likes (API doesn't support liking comments)
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from collections import defaultdict
import googleapiclient.errors

from modules.platform_integration.youtube_auth.src.youtube_auth import (
    list_video_comments, 
    reply_to_comment,
    get_latest_video_id
)
from modules.communication.livechat.src.agentic_chat_engine import AgenticChatEngine
from modules.communication.livechat.src.chat_memory_manager import ChatMemoryManager
try:
    from modules.communication.video_comments.src.llm_comment_generator import LLMCommentGenerator
except ImportError:
    LLMCommentGenerator = None

# V5 Integration: Browser-based likes via UI-TARS Vision
try:
    from modules.infrastructure.browser_actions.src.youtube_actions import YouTubeActions
    BROWSER_ACTIONS_AVAILABLE = True
except ImportError:
    YouTubeActions = None
    BROWSER_ACTIONS_AVAILABLE = False

logger = logging.getLogger(__name__)

class CommentThread:
    """Represents an active comment conversation thread"""
    
    def __init__(self, parent_id: str, author: str):
        self.parent_id = parent_id
        self.author = author
        self.messages = []  # List of (author, text, timestamp) tuples
        self.last_activity = datetime.now()
        self.is_active = True
        self.context = {}  # Conversation context
    
    def add_message(self, author: str, text: str):
        """Add a message to the thread"""
        self.messages.append((author, text, datetime.now()))
        self.last_activity = datetime.now()
    
    def get_conversation_history(self) -> str:
        """Get formatted conversation history"""
        history = []
        for author, text, timestamp in self.messages:
            history.append(f"{author}: {text}")
        return "\n".join(history)
    
    def should_close(self) -> bool:
        """Check if thread should be closed (5 min inactivity)"""
        return (datetime.now() - self.last_activity) > timedelta(minutes=5)


class RealtimeCommentDialogue:
    """
    Real-time comment dialogue system for YouTube
    Monitors and maintains conversations in comment threads
    """
    
    def __init__(self, youtube_service, channel_id: str, memory_dir: str = "memory"):
        """
        Initialize real-time dialogue system
        
        Args:
            youtube_service: Authenticated YouTube service
            channel_id: Channel ID to monitor
            memory_dir: Directory for memory persistence
        """
        self.youtube = youtube_service
        self.channel_id = channel_id
        self.memory_dir = memory_dir
        self.is_running = False
        
        # Active conversation threads
        self.active_threads: Dict[str, CommentThread] = {}
        
        # Track all processed comment IDs
        self.processed_comments: Set[str] = set()
        
        # Track which comments we've replied to
        self.our_replies: Dict[str, str] = {}  # comment_id -> our_reply_id
        
        # Response generation - Use LLM if available
        if LLMCommentGenerator:
            try:
                self.llm_generator = LLMCommentGenerator()
                logger.info("[BOT] Using LLM for intelligent comment responses")
            except Exception as e:
                logger.warning(f"[U+26A0]️ LLM initialization failed: {e}")
                self.llm_generator = None
        else:
            self.llm_generator = None
            logger.info("[U+26A0]️ No LLM available, using template responses")
        
        self.chat_engine = AgenticChatEngine()  # Fallback
        self.memory_manager = ChatMemoryManager(memory_dir)
        
        # Real-time monitoring intervals
        self.rapid_check_interval = 5   # 5 seconds for active threads
        self.normal_check_interval = 15  # 15 seconds for new comments
        self.idle_check_interval = 60   # 60 seconds when no activity
        
        # Track video being monitored
        self.current_video_id = None
        self.video_check_time = datetime.now()
        
        # V5 Integration: Browser-based like capability
        self.youtube_actions = None
        self.auto_like_on_reply = True  # Like comments when replying
        self.likes_enabled = BROWSER_ACTIONS_AVAILABLE
        if BROWSER_ACTIONS_AVAILABLE:
            try:
                self.youtube_actions = YouTubeActions(profile='youtube_move2japan')
                logger.info("[V5] Browser-based likes enabled via UI-TARS Vision")
            except Exception as e:
                logger.warning(f"[V5] Browser actions unavailable: {e}")
                self.youtube_actions = None
                self.likes_enabled = False
        
        logger.info(f"[LIVE] Real-time Comment Dialogue initialized for channel: {channel_id}")
    
    async def start(self):
        """Start real-time comment monitoring and dialogue"""
        self.is_running = True
        logger.info("[ROCKET] Real-time Comment Dialogue starting...")
        
        # Run multiple monitoring tasks concurrently
        await asyncio.gather(
            self.monitor_new_comments(),      # Check for new top-level comments
            self.monitor_active_threads(),    # Monitor active conversations
            self.cleanup_inactive_threads()   # Clean up old threads
        )
    
    async def monitor_new_comments(self):
        """Monitor for new top-level comments to start conversations"""
        while self.is_running:
            try:
                # Get current video
                if not self.current_video_id or \
                   (datetime.now() - self.video_check_time) > timedelta(minutes=5):
                    self.current_video_id = get_latest_video_id(self.youtube, self.channel_id)
                    self.video_check_time = datetime.now()
                
                if self.current_video_id:
                    # Fetch recent comments
                    comments = list_video_comments(
                        self.youtube, 
                        self.current_video_id, 
                        max_results=25  # Check last 25 comments
                    )
                    
                    for comment in comments:
                        await self.process_new_comment(comment)
                
                # Adjust interval based on activity
                interval = self.normal_check_interval
                if self.active_threads:
                    interval = self.rapid_check_interval
                elif not self.current_video_id:
                    interval = self.idle_check_interval
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error monitoring new comments: {e}")
                await asyncio.sleep(30)
    
    async def process_new_comment(self, comment: Dict[str, Any]):
        """Process a potentially new comment"""
        comment_id = comment['id']
        
        # Skip if already processed
        if comment_id in self.processed_comments:
            return
        
        self.processed_comments.add(comment_id)
        
        # Extract comment details
        snippet = comment.get('snippet', {})
        text = snippet.get('textDisplay', '')
        author = snippet.get('authorDisplayName', '')
        parent_id = snippet.get('parentId')
        
        # Check if this is a reply to one of our comments
        if parent_id and parent_id in self.our_replies:
            # This is a reply to us - continue the conversation!
            await self.handle_reply_to_us(parent_id, comment_id, author, text)
        
        # Check if we should start a new conversation
        elif not parent_id and await self.should_engage(text, author):
            # Start a new conversation thread
            await self.start_conversation(comment_id, author, text)
    
    async def should_engage(self, text: str, author: str) -> bool:
        """
        Determine if we should engage with this comment
        More aggressive engagement for real-time dialogue
        """
        text_lower = text.lower()
        
        # Always engage with consciousness triggers
        if '[U+270A][U+270B][U+1F590]' in text:
            return True
        
        # Engage with questions
        if '?' in text:
            return True
        
        # Engage with mentions
        if any(m in text_lower for m in ['0102', 'bot', 'undaodu', 'move2japan']):
            return True
        
        # Engage with greetings for friendly dialogue
        if any(g in text_lower for g in ['hello', 'hi', 'hey', 'sup', 'yo']):
            return True
        
        # Check user history
        user_memory = self.memory_manager.get_user_memory(author)
        if user_memory and user_memory.get('interaction_count', 0) > 2:
            return True
        
        # Random engagement (10% chance) to increase activity
        import random
        if random.random() < 0.1:
            return True
        
        return False
    
    async def like_comment(self, video_id: str, comment_id: str) -> bool:
        """
        Like a comment using browser automation (V5 Integration)
        
        YouTube API does NOT support liking comments, so we use
        UI-TARS Vision to interact with the browser.
        
        Args:
            video_id: YouTube video ID
            comment_id: Comment thread ID
            
        Returns:
            True if like succeeded
        """
        if not self.youtube_actions:
            logger.warning("[V5] Browser actions not available for liking")
            return False
        
        try:
            result = await self.youtube_actions.like_comment(video_id, comment_id)
            if result.success:
                logger.info(f"[LIKE] Liked comment {comment_id[:10]}...")
            else:
                logger.warning(f"[LIKE] Failed to like comment: {result.error}")
            return result.success
        except Exception as e:
            logger.error(f"[V5] Like failed: {e}")
            return False

    async def like_and_reply(
        self, 
        video_id: str, 
        comment_id: str, 
        reply_text: str
    ) -> Dict[str, bool]:
        """
        Like and reply to a comment in one operation.
        
        Uses:
        - UI-TARS Vision for liking (browser automation)
        - YouTube API for replying (fast, reliable)
        
        Args:
            video_id: YouTube video ID
            comment_id: Comment thread ID
            reply_text: Response text
            
        Returns:
            Dict with like_success and reply_success
        """
        result = {'like_success': False, 'reply_success': False}
        
        # Like via browser (background, don't block reply)
        if self.likes_enabled and self.youtube_actions:
            try:
                like_result = await self.youtube_actions.like_comment(video_id, comment_id)
                result['like_success'] = like_result.success
                if like_result.success:
                    logger.info(f"[V5] Liked comment before replying")
            except Exception as e:
                logger.warning(f"[V5] Like failed, continuing with reply: {e}")
        
        # Reply via API (reliable)
        try:
            reply_id = reply_to_comment(self.youtube, comment_id, reply_text)
            result['reply_success'] = reply_id is not None
        except Exception as e:
            logger.error(f"Reply failed: {e}")
        
        return result

    async def start_conversation(self, comment_id: str, author: str, text: str):
        """Start a new conversation thread"""
        try:
            logger.info(f"[CHAT] Starting conversation with {author}")
            
            # Create thread
            thread = CommentThread(comment_id, author)
            thread.add_message(author, text)
            self.active_threads[comment_id] = thread
            
            # Generate contextual response
            response = await self.generate_dialogue_response(thread, text, author)
            
            if response:
                # V5: Like and reply together if enabled
                if self.auto_like_on_reply and self.current_video_id:
                    result = await self.like_and_reply(
                        self.current_video_id, comment_id, response
                    )
                    if result['like_success']:
                        logger.info(f"[V5] Liked comment from {author}")
                    reply_id = comment_id if result['reply_success'] else None
                else:
                    # Original: Reply only
                    reply_id = reply_to_comment(self.youtube, comment_id, response)
                
                if reply_id:
                    self.our_replies[comment_id] = reply_id
                    thread.add_message("0102", response)
                    logger.info(f"[OK] Started dialogue with {author}: {response[:50]}...")
                
                # Update memory
                self.memory_manager.update_user_memory(author, {
                    'last_dialogue': datetime.now().isoformat(),
                    'dialogue_count': 1
                })
                
        except Exception as e:
            logger.error(f"Failed to start conversation: {e}")
    
    async def handle_reply_to_us(self, parent_id: str, comment_id: str, 
                                  author: str, text: str):
        """Handle a reply to one of our comments - continue the dialogue!"""
        try:
            logger.info(f"[REFRESH] {author} replied to us: {text[:50]}...")
            
            # Get or create thread
            thread = self.active_threads.get(parent_id)
            if not thread:
                thread = CommentThread(parent_id, author)
                self.active_threads[parent_id] = thread
            
            # Add their reply to thread
            thread.add_message(author, text)
            
            # Generate contextual response based on conversation history
            response = await self.generate_dialogue_response(thread, text, author)
            
            if response:
                # Continue the conversation!
                reply_id = reply_to_comment(self.youtube, comment_id, response)
                self.our_replies[comment_id] = reply_id
                thread.add_message("0102", response)
                
                logger.info(f"[OK] Continued dialogue with {author}: {response[:50]}...")
                
                # Update memory with conversation progress
                self.memory_manager.update_user_memory(author, {
                    'last_dialogue': datetime.now().isoformat(),
                    'dialogue_messages': len(thread.messages),
                    'dialogue_context': thread.context
                })
                
        except Exception as e:
            logger.error(f"Failed to continue dialogue: {e}")
    
    async def monitor_active_threads(self):
        """Monitor active threads for new replies"""
        while self.is_running:
            try:
                if not self.active_threads:
                    await asyncio.sleep(10)
                    continue
                
                # Check each active thread for new replies
                for thread_id, thread in list(self.active_threads.items()):
                    if thread.should_close():
                        logger.info(f"[U+1F4D5] Closing inactive thread with {thread.author}")
                        del self.active_threads[thread_id]
                        continue
                    
                    # Check for new replies in this thread
                    # (YouTube API doesn't have real-time push, so we poll)
                    await self.check_thread_replies(thread_id, thread)
                
                # Rapid checks when threads are active
                await asyncio.sleep(self.rapid_check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring threads: {e}")
                await asyncio.sleep(10)
    
    async def check_thread_replies(self, thread_id: str, thread: CommentThread):
        """Check a specific thread for new replies"""
        # This would need YouTube API support for fetching replies to a specific comment
        # For now, new replies are caught by monitor_new_comments()
        pass
    
    async def cleanup_inactive_threads(self):
        """Clean up inactive conversation threads"""
        while self.is_running:
            try:
                # Clean up every minute
                await asyncio.sleep(60)
                
                inactive = []
                for thread_id, thread in self.active_threads.items():
                    if thread.should_close():
                        inactive.append(thread_id)
                
                for thread_id in inactive:
                    thread = self.active_threads[thread_id]
                    logger.info(f"[U+1F9F9] Cleaning up thread with {thread.author}")
                    
                    # Save conversation to memory
                    self.memory_manager.update_user_memory(thread.author, {
                        'past_conversations': thread.get_conversation_history()
                    })
                    
                    del self.active_threads[thread_id]
                
            except Exception as e:
                logger.error(f"Error in cleanup: {e}")
    
    async def generate_dialogue_response(self, thread: CommentThread, 
                                        text: str, author: str) -> Optional[str]:
        """
        Generate response for ongoing dialogue
        Takes into account conversation history and context
        """
        try:
            # Build rich context
            context = {
                'platform': 'youtube_comments',
                'dialogue_mode': True,
                'author': author,
                'channel': 'Move2Japan',
                'conversation_length': len(thread.messages),
                'conversation_history': thread.get_conversation_history()[-500:],  # Last 500 chars
                'thread_context': thread.context
            }
            
            # Get user memory for deeper personalization
            user_memory = self.memory_manager.get_user_memory(author)
            if user_memory:
                context['user_history'] = user_memory
                context['is_returning_user'] = True
            
            # Add personality based on conversation length
            if len(thread.messages) > 4:
                context['personality'] = 'friendly and casual'
            elif len(thread.messages) > 2:
                context['personality'] = 'engaged and curious'
            else:
                context['personality'] = 'welcoming and helpful'
            
            # Preserve the exact reviewed text. This legacy nested route remains
            # unqualified for public use and cannot fill missing identity with templates.
            if not self.llm_generator:
                return None
            return self.llm_generator.generate_dialogue_response(thread, text, author)
            
        except Exception as e:
            logger.error(f"Failed to generate dialogue response: {e}")
            return None
    
    def stop(self):
        """Stop the dialogue system"""
        self.is_running = False
        
        # V5: Close browser resources
        if self.youtube_actions:
            try:
                self.youtube_actions.close()
                logger.info("[V5] Browser actions closed")
            except Exception as e:
                logger.warning(f"[V5] Error closing browser: {e}")
        
        logger.info("Real-time Comment Dialogue stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        return {
            'running': self.is_running,
            'active_threads': len(self.active_threads),
            'processed_comments': len(self.processed_comments),
            'current_video': self.current_video_id,
            'likes_enabled': self.likes_enabled,
            'auto_like_on_reply': self.auto_like_on_reply,
            'v5_integration': BROWSER_ACTIONS_AVAILABLE,
            'threads': [
                {
                    'author': t.author,
                    'messages': len(t.messages),
                    'last_activity': t.last_activity.isoformat()
                }
                for t in self.active_threads.values()
            ]
        }