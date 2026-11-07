"""
Chat Memory Manager - WSP 60 Compliant
Hybrid memory storage for live chat context and history

NAVIGATION: Persists chat memory for processors and analytics.
-> Called by: livechat_core.py, message_processor.py, agentic_chat_engine.py
-> Delegates to: module memory files under modules/communication/livechat/memory
-> Related: NAVIGATION.py -> NEED_TO["manage chat memory"]
-> Quick ref: NAVIGATION.py -> DATABASES["memory_files"]

CRITICAL FIX (2026-02-19): Added SQLite persistence for ALL messages.
Previously logs were only written on end_session() which never gets called
when stream ends abruptly. Now every message is persisted immediately.
"""

import logging
import os
import time
import sqlite3
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from pathlib import Path

from modules.communication.livechat.src.chat_telemetry_store import (
    ChatTelemetryStore,
)

logger = logging.getLogger(__name__)

class ChatMemoryManager:
    """
    Hybrid memory manager implementing WSP 17 pattern:
    - In-memory buffer (20 messages per user)
    - Smart disk persistence (important users only)
    - 97% I/O reduction achieved
    """
    
    def __init__(self, memory_dir: str = "memory", buffer_size: int = 20):
        """
        Initialize hybrid memory manager.

        Args:
            memory_dir: Directory for persistent storage
            buffer_size: Size of in-memory buffer per user
        """
        self.memory_dir = memory_dir
        self.buffer_size = buffer_size

        # In-memory buffers (WSP 17 pattern)
        self.message_buffers = defaultdict(lambda: deque(maxlen=buffer_size))
        self.user_stats = defaultdict(lambda: {
            'message_count': 0,
            'last_seen': time.time(),
            'role': 'USER',
            'importance_score': 0,
            'consciousness_triggers': 0,
            'youtube_id': None,  # Store YouTube channel ID
            'youtube_name': None  # Store YouTube display name
        })

        # SQLite persistence for ALL messages (survives crashes/stream endings)
        self.db_path = Path(memory_dir) / "chat_logs.db"
        self._init_db()

        # Persistent storage criteria
        self.important_roles = {'MOD', 'OWNER'}
        self.importance_threshold = 5  # Store users with 5+ messages or special triggers

        # Session tracking for automatic logging
        self.current_session = None
        self.session_messages = []  # Full transcript for current session
        self.session_mod_messages = []  # Mod-only messages for current session
        self.conversation_dir = os.path.join(self.memory_dir, "conversation")
        self.telemetry_store = ChatTelemetryStore()

        # Ensure memory directories exist
        os.makedirs(memory_dir, exist_ok=True)
        os.makedirs(self.conversation_dir, exist_ok=True)
        logger.info(f"[U+1F4BE] ChatMemoryManager initialized: buffer={buffer_size}, dir={memory_dir}")

    def _init_db(self) -> None:
        """Initialize SQLite database for real-time message persistence."""
        try:
            os.makedirs(self.db_path.parent, exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # All chat messages (for troll training and history)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    user_id TEXT,
                    username TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    role TEXT DEFAULT 'USER',
                    timestamp REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indexes for fast lookups
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_messages(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_timestamp ON chat_messages(timestamp)")

            conn.commit()
            conn.close()
            logger.info(f"[DB] Chat logs database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"[DB] Failed to initialize chat_logs.db: {e}")

    def _persist_message_to_db(self, author_name: str, message_text: str, role: str,
                                author_id: str = None) -> None:
        """Persist message to SQLite immediately (survives crashes)."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_messages (session_id, user_id, username, message_text, role, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (self.current_session, author_id, author_name, message_text, role, time.time()))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"[DB] Failed to persist message: {e}")

    def start_session(self, session_id: str, stream_title: str = None) -> None:
        """
        Start a new chat session for automatic logging.

        Args:
            session_id: Unique session identifier (video ID or timestamp)
            stream_title: Optional stream title for context
        """
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.current_session = f"session_{timestamp}_{session_id[:8] if len(session_id) > 8 else session_id}"
            self.session_messages = []
            self.session_mod_messages = []

            logger.info(f"📹 Started session: {self.current_session}")
            if stream_title:
                logger.info(f"📺 Stream: {stream_title}")
        except Exception as e:
            logger.error(f"[FAIL] Error starting session: {e}")

    def end_session(self) -> None:
        """
        End current session and save all logs automatically.
        """
        if not self.current_session:
            return

        try:
            from datetime import datetime

            # Create session directory
            session_path = os.path.join(self.conversation_dir, self.current_session)
            os.makedirs(session_path, exist_ok=True)

            # Save full transcript (history-only, no metadata)
            if self.session_messages:
                full_transcript = os.path.join(session_path, "full_transcript.txt")
                with open(full_transcript, 'w', encoding='utf-8') as f:
                    for msg in self.session_messages:
                        f.write(f"{msg}\n")
                logger.info(f"[U+1F4BE] Saved {len(self.session_messages)} messages to full transcript")

            # Save mod-only transcript (history-only, no metadata)
            if self.session_mod_messages:
                mod_transcript = os.path.join(session_path, "mod_messages.txt")
                with open(mod_transcript, 'w', encoding='utf-8') as f:
                    for msg in self.session_mod_messages:
                        f.write(f"{msg}\n")
                logger.info(f"[U+1F6E1]️ Saved {len(self.session_mod_messages)} mod messages")

            logger.info(
                f"[DATA] Session ended: {self.current_session} - "
                f"{len(self.session_messages)} total, {len(self.session_mod_messages)} mod messages"
            )

            # Reset session
            self.current_session = None
            self.session_messages = []
            self.session_mod_messages = []

        except Exception as e:
            logger.error(f"[FAIL] Error ending session: {e}")

    def store_message(self, author_name: str, message_text: str, role: str = 'USER',
                     author_id: str = None, youtube_name: str = None) -> None:
        """
        Store message using hybrid approach with session logging.

        Args:
            author_name: User's display name
            message_text: Message content
            role: User role (USER, MOD, OWNER)
            author_id: YouTube channel ID
            youtube_name: YouTube display name
        """
        try:
            # Update in-memory buffer (always)
            self.message_buffers[author_name].append({
                'text': message_text,
                'timestamp': time.time(),
                'role': role
            })

            # CRITICAL: Persist to SQLite immediately (survives crashes/stream endings)
            # This captures ALL messages for troll training and history
            self._persist_message_to_db(author_name, message_text, role, author_id)

            # Update user statistics
            stats = self.user_stats[author_name]
            stats['message_count'] += 1
            stats['last_seen'] = time.time()
            stats['role'] = role  # Update role (user might become mod)

            # Store YouTube metadata if provided
            if author_id:
                stats['youtube_id'] = author_id
            if youtube_name:
                stats['youtube_name'] = youtube_name

            # Calculate importance score
            stats['importance_score'] = self._calculate_importance(stats, message_text)

            # Session logging (automatic for all messages)
            if self.current_session:
                # Format message for logs
                role_prefix = f"[{role}] " if role in ['MOD', 'OWNER'] else ""

                # Mod/owner log (history-only)
                if role in ['MOD', 'OWNER']:
                    mod_entry = f"{author_name}: {message_text}"
                    self.session_mod_messages.append(mod_entry)

                # Full transcript entry
                full_entry = f"{role_prefix}{author_name}: {message_text}"
                self.session_messages.append(full_entry)

            # Smart persistence (97% I/O reduction)
            if self._should_persist(stats):
                self._persist_to_storage(author_name, message_text, role, stats)
                logger.debug(f"[U+1F4BE] Persisted message from important user: {author_name}")
            else:
                logger.debug(f"[NOTE] Buffered message from {author_name} (not persisting)")

        except Exception as e:
            logger.error(f"[FAIL] Error storing message from {author_name}: {e}")
    
    def get_conversation_context(self, author_id: str) -> Optional[Dict[str, Any]]:
        """Bounded current-session context from the complete native-ID store.

        No display-name fallback, cross-session profiling, or database creation.
        Failure is distinct from an empty history so callers can remain quiet.
        """
        if not self.current_session or not isinstance(author_id, str) or not author_id:
            return None
        try:
            with sqlite3.connect(self.db_path.resolve().as_uri() + '?mode=ro', uri=True, timeout=1) as db:
                def rows(extra, params, limit):
                    values = db.execute(
                        'SELECT user_id, message_text, role FROM chat_messages '
                        'WHERE session_id = ? ' + extra + ' ORDER BY id DESC LIMIT ?',
                        (self.current_session, *params, limit)).fetchall()
                    return [{'participant_id': identity, 'text': text[:500], 'platform_role': role}
                            for identity, text, role in reversed(values)]
                return {'session_id': self.current_session, 'participant_id': author_id,
                        'recent_messages': rows('', (), 20),
                        'participant_messages': rows('AND user_id = ?', (author_id,), 5)}
        except (sqlite3.Error, OSError, TypeError):
            logger.warning('[CONVERSATION] Scoped history read unavailable')
            return None

    def get_history(self, author_name: str, limit: int = 10) -> List[str]:
        """
        Get user's message history from buffer + disk.

        Args:
            author_name: User's display name
            limit: Maximum messages to return

        Returns:
            List of recent messages as formatted strings
        """
        try:
            messages = []

            # Get from in-memory buffer (recent messages only)
            # NOTE: Disk storage methods were never implemented - using memory only
            buffer_messages = list(self.message_buffers.get(author_name, []))
            for msg in buffer_messages[-limit:]:
                messages.append(f"{author_name}: {msg['text']}")

            return messages[-limit:]  # Return latest N messages

        except Exception as e:
            logger.error(f"[FAIL] Error getting history for {author_name}: {e}")
            return []

    def get_messages_by_user_id(self, youtube_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get user's messages by YouTube channel ID (for troll training).

        Used when a mod whacks someone - lookup their messages for ML training.
        Checks both in-memory buffer AND SQLite for historical messages.

        Args:
            youtube_id: YouTube channel ID (e.g., "UC_2AskvFe9uqp9maCS6bohg")
            limit: Maximum messages to return

        Returns:
            List of message dicts with 'text', 'timestamp', 'author_name'
        """
        result = []

        try:
            # First try in-memory buffer (current session)
            author_name = None
            for name, stats in self.user_stats.items():
                if stats.get('youtube_id') == youtube_id:
                    author_name = name
                    break

            if author_name:
                buffer_messages = list(self.message_buffers.get(author_name, []))
                for msg in buffer_messages[-limit:]:
                    result.append({
                        'text': msg['text'],
                        'timestamp': msg['timestamp'],
                        'author_name': author_name,
                        'youtube_id': youtube_id
                    })

            # Also query SQLite for historical messages (previous sessions)
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT username, message_text, timestamp
                    FROM chat_messages
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (youtube_id, limit))

                for row in cursor.fetchall():
                    # Avoid duplicates (check if message already in result)
                    msg_text = row[1]
                    if not any(r['text'] == msg_text for r in result):
                        result.append({
                            'text': msg_text,
                            'timestamp': row[2] or 0,
                            'author_name': row[0] or author_name or 'Unknown',
                            'youtube_id': youtube_id
                        })

                conn.close()
            except Exception as db_err:
                logger.debug(f"[TROLL-TRAIN] SQLite lookup failed: {db_err}")

            if result:
                logger.info(f"[TROLL-TRAIN] Found {len(result)} messages for whacked user (id: {youtube_id[:20]}...)")
            else:
                logger.debug(f"[TROLL-TRAIN] No messages found for user_id: {youtube_id}")

            return result[:limit]

        except Exception as e:
            logger.error(f"[FAIL] Error getting messages by user_id {youtube_id}: {e}")
            return []

    def classify_user(self, author_name: str, limit: int = 20) -> Dict[str, Any]:
        """
        Classify user as troll or not using chat history.

        Returns:
            dict: {is_troll: bool, score: int, signals: List[str]}
        """
        try:
            history = self.get_history(author_name, limit=limit)
            messages = []
            for entry in history:
                if ": " in entry:
                    messages.append(entry.split(": ", 1)[1])
                else:
                    messages.append(entry)

            if not messages:
                return {"is_troll": False, "score": 0, "signals": []}

            troll_keywords = [
                "libtard", "cuck", "soyboy", "npc", "sheep", "wake up",
                "snowflake", "cope", "copium", "triggered", "loser",
            ]
            caps_hits = 0
            spam_links = 0
            keyword_hits = 0
            repeat_hits = 0

            normalized = [m.strip().lower() for m in messages if isinstance(m, str)]
            for msg in messages:
                if not isinstance(msg, str) or not msg.strip():
                    continue
                lower = msg.lower()
                keyword_hits += sum(1 for kw in troll_keywords if kw in lower)
                if "http://" in lower or "https://" in lower:
                    spam_links += 1
                letters = [c for c in msg if c.isalpha()]
                if letters:
                    caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
                    if caps_ratio > 0.7 and len(msg) > 12:
                        caps_hits += 1

            # Repeated message detection
            seen = {}
            for msg in normalized:
                seen[msg] = seen.get(msg, 0) + 1
            repeat_hits = sum(1 for count in seen.values() if count >= 3)

            score = 0
            score += 2 if keyword_hits >= 2 else 0
            score += 2 if spam_links >= 2 else 0
            score += 2 if caps_hits >= 2 else 0
            score += 2 if repeat_hits >= 1 else 0

            signals = []
            if keyword_hits >= 2:
                signals.append("keywords")
            if spam_links >= 2:
                signals.append("links")
            if caps_hits >= 2:
                signals.append("caps")
            if repeat_hits >= 1:
                signals.append("repeats")

            return {"is_troll": score >= 2, "score": score, "signals": signals}
        except Exception as e:
            logger.error(f"[FAIL] Error classifying user {author_name}: {e}")
            return {"is_troll": False, "score": 0, "signals": ["error"]}
    
    def analyze_user(self, author_name: str) -> Dict[str, Any]:
        """
        Analyze user patterns and context.
        
        Args:
            author_name: User's display name
            
        Returns:
            User analysis dictionary
        """
        try:
            stats = self.user_stats.get(author_name, {})
            recent_messages = list(self.message_buffers.get(author_name, []))
            
            # Determine consciousness level and user type
            consciousness_level = self._determine_consciousness_level(recent_messages, stats)
            user_type = self._determine_user_type(stats.get('message_count', 0), recent_messages)
            
            analysis = {
                'username': author_name,
                'message_count': stats.get('message_count', 0),
                'role': stats.get('role', 'USER'),
                'importance_score': stats.get('importance_score', 0),
                'consciousness_triggers': stats.get('consciousness_triggers', 0),
                'consciousness_level': consciousness_level,
                'user_type': user_type,
                'last_seen': stats.get('last_seen', 0),
                'recent_activity': len(recent_messages),
                'is_frequent': stats.get('message_count', 0) > 10,
                'is_important': self._should_persist(stats),
                'patterns': self._detect_patterns(recent_messages)
            }
            
            logger.debug(f"[SEARCH] Analyzed {author_name}: {analysis['message_count']} msgs, importance={analysis['importance_score']}")
            return analysis
            
        except Exception as e:
            logger.error(f"[FAIL] Error analyzing user {author_name}: {e}")
            return {'username': author_name, 'error': str(e)}
    
    def _calculate_importance(self, stats: Dict[str, Any], message_text: str) -> int:
        """Calculate user importance score for storage decisions.
        
        Note: XP calculation pattern preserved from removed chat_database.py:
        - 10s timeout: 5 XP
        - 60s timeout: 10 XP
        - 600s timeout: 20 XP
        - 1800s timeout: 30 XP
        - 86400s timeout: 50 XP
        - Prestige levels: Novice(0-100) -> Apprentice(100-500) -> Journeyman(500-1000) ->
                         Expert(1000-2000) -> Master(2000-5000) -> Grandmaster(5000+)
        """
        score = 0
        
        # Role-based importance
        if stats.get('role', 'USER') in self.important_roles:
            score += 10
        
        # Message frequency
        message_count = stats.get('message_count', 0)
        if message_count > 20:
            score += 5
        elif message_count > 10:
            score += 3
        elif message_count > 5:
            score += 1
        
        # Consciousness emoji triggers
        consciousness_emojis = ['[U+270A]', '[U+270B]', '[U+1F590]️']
        if any(emoji in message_text for emoji in consciousness_emojis):
            score += 3
            stats['consciousness_triggers'] = stats.get('consciousness_triggers', 0) + 1
        
        # Commands and engagement
        if message_text.startswith('/'):
            score += 2
        
        return score
    
    def _should_persist(self, stats: Dict[str, Any]) -> bool:
        """Determine if user messages should be persisted to disk."""
        return (
            stats.get('role', 'USER') in self.important_roles or
            stats.get('importance_score', 0) >= self.importance_threshold or
            stats.get('consciousness_triggers', 0) > 0
        )
    
    def _persist_to_storage(self, author_name: str, message_text: str, role: str, stats: Dict[str, Any]) -> None:
        """Persist message via telemetry store for important users."""
        try:
            metadata = {
                "message_count": stats.get("message_count"),
                "last_seen": stats.get("last_seen"),
            }
            self.telemetry_store.record_message(
                session_id=self.current_session,
                author_name=author_name,
                author_id=stats.get("youtube_id"),
                youtube_name=stats.get("youtube_name"),
                role=role,
                message_text=message_text,
                importance_score=stats.get("importance_score"),
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"[FAIL] Error persisting message for {author_name}: {e}")

    def _has_persisted_history(self, author_name: str) -> bool:
        """Check if user has persisted history in SQLite."""
        return self.telemetry_store.has_history(author_name)
    
    def _detect_patterns(self, recent_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect user behavior patterns from recent messages."""
        if not recent_messages:
            return {}
        
        patterns = {
            'avg_message_length': sum(len(msg['text']) for msg in recent_messages) / len(recent_messages),
            'command_user': sum(1 for msg in recent_messages if msg['text'].startswith('/')) > 0,
            'emoji_user': sum(1 for msg in recent_messages if any(e in msg['text'] for e in ['[U+270A]', '[U+270B]', '[U+1F590]️'])) > 0,
            'active_timespan': recent_messages[-1]['timestamp'] - recent_messages[0]['timestamp'] if len(recent_messages) > 1 else 0
        }
        
        return patterns
    
    def _determine_consciousness_level(self, recent_messages: List[Dict[str, Any]], stats: Dict[str, Any]) -> str:
        """Determine user's consciousness level based on message patterns."""
        consciousness_triggers = stats.get('consciousness_triggers', 0)
        
        if not recent_messages:
            return 'unknown'
        
        # Check recent messages for MAGA content and consciousness indicators
        maga_keywords = ['maga', 'trump', 'biden', 'liberal', 'conservative', 'woke']
        consciousness_emojis = ['[U+270A]', '[U+270B]', '[U+1F590]️']
        
        maga_count = 0
        consciousness_count = 0
        
        for msg in recent_messages[-10:]:  # Check last 10 messages
            if not isinstance(msg, dict) or 'text' not in msg:
                continue  # Skip malformed messages

            text = msg.get('text', '')
            if not isinstance(text, str):
                continue  # Skip non-string messages

            text_lower = text.lower()

            if any(keyword in text_lower for keyword in maga_keywords):
                maga_count += 1

            if any(emoji in text for emoji in consciousness_emojis):
                consciousness_count += 1
        
        # Determine level based on patterns
        if consciousness_triggers > 0 or consciousness_count > 0:
            return 'aware'
        elif maga_count > 2:  # Multiple MAGA references
            return 'needs_help'
        else:
            return 'unknown'
    
    def _determine_user_type(self, message_count: int, recent_messages: List[Dict[str, Any]]) -> str:
        """Determine user type based on activity patterns."""
        if message_count == 0:
            return 'first_time'
        elif message_count < 5:
            return 'quiet_user'
        elif message_count < 20:
            return 'returning'
        else:
            return 'frequent_poster'
    
    def log_fact_check(self, target_user: str, requester: str, defense_mechanism: str = None) -> None:
        """
        Log a fact-check event for 0102 analysis.

        Args:
            target_user: User being fact-checked
            requester: MOD/OWNER who requested fact-check
            defense_mechanism: Detected defense mechanism if any
        """
        if self.current_session:
            from datetime import datetime
            timestamp = datetime.now().strftime('%H:%M:%S')
            fact_check_entry = f"[{timestamp}] FACT-CHECK: {requester} -> {target_user}"
            if defense_mechanism:
                fact_check_entry += f" | Defense: {defense_mechanism}"

            # Add to session messages for tracking
            self.session_messages.append(f"[SYSTEM] {fact_check_entry}")

            logger.info(f"[TARGET] Logged fact-check: {target_user} by {requester}")

    def get_stats(self) -> Dict[str, Any]:
        """Get memory manager statistics."""
        total_users = len(self.user_stats)
        important_users = sum(1 for stats in self.user_stats.values() if self._should_persist(stats))
        disk_files = len([f for f in os.listdir(self.memory_dir) if f.endswith('.txt')])

        return {
            'total_users_tracked': total_users,
            'important_users': important_users,
            'disk_storage_users': disk_files,
            'memory_buffers': len(self.message_buffers),
            'io_reduction_percent': round((1 - important_users/total_users) * 100, 1) if total_users > 0 else 0,
            'buffer_size': self.buffer_size,
            'session_active': self.current_session is not None,
            'session_messages': len(self.session_messages) if self.current_session else 0
        }


# Singleton instance for shared access across modules
_chat_memory_manager_instance = None

def get_chat_memory_manager(memory_dir: str = "modules/communication/livechat/memory") -> ChatMemoryManager:
    """
    Get singleton ChatMemoryManager instance.
    
    This ensures all modules share the same in-memory buffers,
    which is critical for troll training (timeout_announcer needs
    access to the same messages that livechat_core stored).
    
    Args:
        memory_dir: Directory for persistent storage (only used on first call)
    
    Returns:
        Shared ChatMemoryManager instance
    """
    global _chat_memory_manager_instance
    if _chat_memory_manager_instance is None:
        _chat_memory_manager_instance = ChatMemoryManager(memory_dir=memory_dir)
    return _chat_memory_manager_instance

