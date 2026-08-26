#!/usr/bin/env python3
"""
Suno STT Lyrics Extractor - Fully Automated via Speech-to-Text

Uses faster-whisper to transcribe lyrics directly from Suno audio files.
No browser automation needed - just audio download + STT transcription.

"Everything 012 does, 0102 should be able to do" - ZERO manual work.

WSP Compliance:
    - WSP 84 (Code Reuse): Reuses FasterWhisperSTT from voice_command_ingestion
    - WSP 50 (Pre-Action): HoloIndex search found BatchTranscriber/FasterWhisperSTT
    - WSP 72 (Independence): Suno-specific logic isolated, STT reused

Architecture:
    Suno CDN (cdn1.suno.ai/{id}.mp3)
        ↓
    SunoAudioDownloader (download + cache)
        ↓
    SunoSTTTranscriber (wraps FasterWhisperSTT from voice_command_ingestion)
        ↓
    LyricsDeduplicator (hash-based dedup, SQLite storage)
        ↓
    ffcpln_lyrics.db

Usage:
    # Extract lyrics from 012's full playlist:
    python suno_stt_lyrics_extractor.py --playlist "3adb1878-12f8-4c1c-a815-bde3d7d320ed"

    # Test with first 5 songs:
    python suno_stt_lyrics_extractor.py --playlist "..." --max 5

    # Use larger model for accuracy:
    python suno_stt_lyrics_extractor.py --playlist "..." --model small

Requirements:
    pip install faster-whisper librosa
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sqlite3
import sys
import tempfile
import time
from contextlib import closing
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Generator
import urllib.request
import urllib.error

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Fix Windows console encoding only for the interactive CLI. Importers such as
# pytest own their capture streams and must not have them replaced.
if __name__ == "__main__" and sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
AUDIO_CACHE_DIR = DATA_DIR / "suno_audio_cache"
LYRICS_DB = DATA_DIR / "ffcpln_lyrics.db"
PROGRESS_FILE = DATA_DIR / "suno_stt_progress.json"

# Suno CDN URL pattern
SUNO_CDN_URL = "https://cdn1.suno.ai/{song_id}.mp3"


@dataclass
class SongMetadata:
    """Song metadata from Suno."""
    id: str
    title: str = ""
    artist: str = "UnDaoDu"
    style: str = ""
    duration_sec: int = 0
    url: str = ""


@dataclass
class TranscribedLyrics:
    """Transcribed lyrics with metadata."""
    song_id: str
    title: str
    artist: str
    lyrics: str
    lyrics_hash: str
    confidence: float
    duration_sec: int
    word_count: int
    style: str = ""
    transcribed_at: str = ""

    @classmethod
    def from_transcription(cls, song: SongMetadata, lyrics: str, confidence: float) -> 'TranscribedLyrics':
        """Create from transcription result."""
        # Normalize lyrics for hashing
        normalized = re.sub(r'\s+', ' ', lyrics.lower().strip())
        lyrics_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]

        return cls(
            song_id=song.id,
            title=song.title or f"Song_{song.id[:8]}",
            artist=song.artist,
            lyrics=lyrics,
            lyrics_hash=lyrics_hash,
            confidence=confidence,
            duration_sec=song.duration_sec,
            word_count=len(lyrics.split()),
            style=song.style,
            transcribed_at=datetime.now(timezone.utc).isoformat()
        )


class SunoAudioDownloader:
    """Downloads audio from Suno CDN."""

    def __init__(self, cache_dir: Path = AUDIO_CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_audio_url(self, song_id: str) -> str:
        """Get CDN URL for song audio."""
        return SUNO_CDN_URL.format(song_id=song_id)

    def download(self, song_id: str, force: bool = False) -> Optional[Path]:
        """Download audio file from Suno CDN.

        Args:
            song_id: Suno song ID
            force: Re-download even if cached

        Returns:
            Path to downloaded audio file, or None on failure
        """
        cache_path = self.cache_dir / f"{song_id}.mp3"

        # Use cache if available
        if cache_path.exists() and not force:
            logger.debug(f"[CACHE] Using cached: {song_id}")
            return cache_path

        url = self.get_audio_url(song_id)
        logger.info(f"[DOWNLOAD] {url}")

        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            })

            with urllib.request.urlopen(req, timeout=60) as resp:
                audio_data = resp.read()

            # Save to cache
            with open(cache_path, 'wb') as f:
                f.write(audio_data)

            logger.info(f"[DOWNLOAD] Saved: {cache_path.name} ({len(audio_data) / 1024 / 1024:.1f} MB)")
            return cache_path

        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.warning(f"[DOWNLOAD] Not found (404): {song_id}")
            else:
                logger.error(f"[DOWNLOAD] HTTP error {e.code}: {song_id}")
            return None
        except Exception as e:
            logger.error(f"[DOWNLOAD] Failed: {song_id} - {e}")
            return None


class SunoSTTTranscriber:
    """Transcribes Suno audio to lyrics using FasterWhisperSTT.

    WSP 84 Compliance: Reuses FasterWhisperSTT from voice_command_ingestion
    instead of duplicating the Whisper loading/transcription logic.
    """

    def __init__(self, model_size: str = "base", device: str = "cpu"):
        """Initialize transcriber.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v3)
            device: Device for inference (cpu, cuda)
        """
        self.model_size = model_size
        self.device = device
        self._stt = None
        self._initialized = False

    def _initialize(self) -> bool:
        """Lazy load STT engine from voice_command_ingestion (WSP 84)."""
        if self._initialized:
            return True

        try:
            # Reuse existing FasterWhisperSTT from voice_command_ingestion
            from modules.communication.voice_command_ingestion.src.voice_command_ingestion import (
                FasterWhisperSTT
            )

            logger.info(f"[STT] Loading FasterWhisperSTT (WSP 84 reuse): {self.model_size} on {self.device}")
            self._stt = FasterWhisperSTT(
                model_size=self.model_size,
                device=self.device,
                compute_type="int8" if self.device == "cpu" else "float16",
            )
            self._initialized = True
            logger.info("[STT] Engine ready (reusing voice_command_ingestion.FasterWhisperSTT)")
            return True

        except ImportError as e:
            logger.error(f"[STT] Could not import FasterWhisperSTT: {e}")
            logger.error("[STT] Install: pip install faster-whisper")
            return False
        except Exception as e:
            logger.error(f"[STT] Failed to initialize: {e}")
            return False

    def transcribe(self, audio_path: Path) -> Tuple[str, float]:
        """Transcribe audio file to text.

        Args:
            audio_path: Path to audio file

        Returns:
            (transcription text, average confidence)
        """
        if not self._initialize():
            return "", 0.0

        try:
            import numpy as np
            import librosa

            logger.info(f"[STT] Transcribing: {audio_path.name}")

            # Load audio at 16kHz mono (Whisper's expected format)
            audio, sr = librosa.load(str(audio_path), sr=16000, mono=True)

            # Use the reused FasterWhisperSTT.transcribe() method
            event = self._stt.transcribe(audio, sample_rate=16000)

            if event is None:
                return "", 0.0

            # The existing STT returns single-line text, but for lyrics we want line breaks
            # Re-transcribe with segments for better lyrics formatting
            if hasattr(self._stt, '_model') and self._stt._model is not None:
                segments, info = self._stt._model.transcribe(
                    str(audio_path),
                    beam_size=5,
                    language="en",
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 500},
                )

                text_parts = []
                total_logprob = 0.0
                segment_count = 0

                for segment in segments:
                    text = segment.text.strip()
                    if text:
                        text_parts.append(text)
                        total_logprob += segment.avg_logprob
                        segment_count += 1

                full_text = "\n".join(text_parts)

                if segment_count > 0:
                    avg_logprob = total_logprob / segment_count
                    confidence = min(1.0, max(0.0, 1.0 + avg_logprob / 5))
                else:
                    confidence = 0.0

                logger.info(f"[STT] Transcribed: {len(full_text)} chars, {segment_count} segments, conf={confidence:.2f}")
                return full_text, confidence

            # Fallback: use single-line result
            return event.text, event.confidence

        except ImportError:
            logger.error("[STT] librosa not installed. Run: pip install librosa")
            return "", 0.0
        except Exception as e:
            logger.error(f"[STT] Transcription failed: {e}")
            return "", 0.0


class LyricsDeduplicator:
    """Hash-based lyrics deduplication with SQLite storage."""

    def __init__(self, db_path: Optional[Path] = None):
        configured_path = os.getenv("ANTIFAFM_LYRICS_DB")
        self.db_path = Path(db_path or configured_path or LYRICS_DB)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # sqlite3.Connection.__exit__ commits or rolls back but does not close
        # the handle. Explicit closing is required before Windows temp cleanup.
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS unique_lyrics (
                    lyrics_hash TEXT PRIMARY KEY,
                    lyrics TEXT NOT NULL,
                    canonical_title TEXT,
                    word_count INTEGER,
                    created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS song_lyrics_map (
                    song_id TEXT PRIMARY KEY,
                    lyrics_hash TEXT NOT NULL,
                    title TEXT,
                    artist TEXT,
                    confidence REAL,
                    style TEXT,
                    duration_sec INTEGER,
                    transcribed_at TEXT,
                    FOREIGN KEY (lyrics_hash) REFERENCES unique_lyrics(lyrics_hash)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_song_lyrics_hash
                ON song_lyrics_map(lyrics_hash)
            """)
            conn.commit()

    def add_lyrics(self, result: TranscribedLyrics) -> Tuple[bool, str]:
        """Add transcribed lyrics with deduplication.

        Returns:
            (is_new, lyrics_hash) - is_new=True if this is a new unique lyrics
        """
        with closing(sqlite3.connect(self.db_path)) as conn:
            # Check if hash exists
            existing = conn.execute(
                "SELECT lyrics_hash FROM unique_lyrics WHERE lyrics_hash = ?",
                (result.lyrics_hash,)
            ).fetchone()

            is_new = existing is None

            if is_new:
                # New unique lyrics
                conn.execute("""
                    INSERT INTO unique_lyrics (lyrics_hash, lyrics, canonical_title, word_count, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (result.lyrics_hash, result.lyrics, result.title, result.word_count, result.transcribed_at))
                logger.info(f"[DEDUP] New unique lyrics: {result.lyrics_hash} ({result.word_count} words)")
            else:
                logger.info(f"[DEDUP] Duplicate lyrics: {result.lyrics_hash}")

            # Map song to lyrics
            conn.execute("""
                INSERT OR REPLACE INTO song_lyrics_map
                (song_id, lyrics_hash, title, artist, confidence, style, duration_sec, transcribed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (result.song_id, result.lyrics_hash, result.title, result.artist,
                  result.confidence, result.style, result.duration_sec, result.transcribed_at))

            conn.commit()

        return is_new, result.lyrics_hash

    def get_stats(self) -> Dict:
        """Get deduplication statistics."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            unique_count = conn.execute("SELECT COUNT(*) FROM unique_lyrics").fetchone()[0]
            song_count = conn.execute("SELECT COUNT(*) FROM song_lyrics_map").fetchone()[0]

            # Get songs per hash distribution
            dist = conn.execute("""
                SELECT lyrics_hash, COUNT(*) as cnt
                FROM song_lyrics_map
                GROUP BY lyrics_hash
                ORDER BY cnt DESC
                LIMIT 10
            """).fetchall()

        return {
            "unique_lyrics": unique_count,
            "total_songs": song_count,
            "dedup_ratio": song_count / unique_count if unique_count > 0 else 0,
            "top_duplicates": [{"hash": h, "count": c} for h, c in dist]
        }

    def is_processed(self, song_id: str) -> bool:
        """Check if song was already processed."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            result = conn.execute(
                "SELECT 1 FROM song_lyrics_map WHERE song_id = ?",
                (song_id,)
            ).fetchone()
        return result is not None


class SunoPlaylistFetcher:
    """Fetches song IDs from Suno playlist via studio-api with cursor pagination.

    Uses Suno's studio-api.prod.suno.com endpoint with cursor-based pagination
    to fetch ALL songs in a playlist (not limited to 50).
    """

    STUDIO_API_BASE = "https://studio-api.prod.suno.com/api/playlist"

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Origin': 'https://suno.com',
            'Referer': 'https://suno.com/',
        }

    def get_playlist_songs(self, playlist_id: str) -> Generator[SongMetadata, None, None]:
        """Get ALL songs from Suno playlist using API cursor pagination.

        Uses studio-api.prod.suno.com with cursor-based pagination to
        fetch the complete playlist (238+ songs).
        """
        logger.info(f"[PLAYLIST] Fetching via API: {playlist_id}")

        # Use API pagination (primary method - gets all songs)
        try:
            yield from self._fetch_with_api_pagination(playlist_id)
            return
        except Exception as e:
            logger.warning(f"[PLAYLIST] API pagination failed: {e}, trying fallback")

        # Fallback: Simple HTTP (only gets ~50 songs from HTML)
        yield from self._fetch_with_http(playlist_id)

    def _fetch_with_api_pagination(self, playlist_id: str) -> Generator[SongMetadata, None, None]:
        """Use Suno studio-api with cursor pagination to get ALL songs."""
        import urllib.parse

        cursor = None
        page = 0
        total_yielded = 0
        yielded_ids = set()

        while True:
            page += 1

            # Build API URL with cursor
            api_url = f"{self.STUDIO_API_BASE}/{playlist_id}"
            if cursor:
                api_url += f"?cursor={urllib.parse.quote(cursor)}"

            logger.info(f"[PLAYLIST] API page {page}...")

            try:
                req = urllib.request.Request(api_url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
            except Exception as e:
                logger.error(f"[PLAYLIST] API request failed: {e}")
                break

            # Extract clips from response
            clips = data.get('playlist_clips', [])
            if not clips:
                logger.info(f"[PLAYLIST] No more clips on page {page}")
                break

            # Process each clip
            for clip_wrapper in clips:
                clip = clip_wrapper.get('clip', {})
                song_id = clip.get('id')

                if not song_id or song_id in yielded_ids:
                    continue

                yielded_ids.add(song_id)
                total_yielded += 1

                # Extract metadata
                metadata = clip.get('metadata', {})
                yield SongMetadata(
                    id=song_id,
                    title=clip.get('title', ''),
                    artist=clip.get('display_name', 'UnDaoDu'),
                    style=metadata.get('tags', '') or metadata.get('prompt', ''),
                    duration_sec=int(metadata.get('duration', 0) or 0),
                    url=clip.get('audio_url', f"https://cdn1.suno.ai/{song_id}.mp3")
                )

            logger.info(f"[PLAYLIST] Page {page}: {len(clips)} clips, {total_yielded} total")

            # Get next cursor for pagination
            cursor = data.get('next_cursor')
            if not cursor:
                logger.info(f"[PLAYLIST] No next_cursor - reached end")
                break

            # Safety limit
            if page >= 20:
                logger.warning(f"[PLAYLIST] Safety limit reached at page {page}")
                break

        logger.info(f"[PLAYLIST] API pagination complete: {total_yielded} songs")

    def _fetch_with_http(self, playlist_id: str) -> Generator[SongMetadata, None, None]:
        """Fallback HTTP fetch (limited to ~50 songs)."""
        playlist_url = f"https://suno.com/playlist/{playlist_id}"
        yielded_ids = set()

        try:
            req = urllib.request.Request(playlist_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode('utf-8')

            # Extract song IDs from HTML
            song_ids = set(re.findall(r'/song/([a-f0-9-]{36})', html))

            # Check __NEXT_DATA__ for JSON data with metadata
            next_data_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>([^<]+)</script>', html)
            if next_data_match:
                try:
                    next_data = json.loads(next_data_match.group(1))
                    props = next_data.get('props', {}).get('pageProps', {})

                    for key in ['clips', 'songs', 'playlist', 'tracks']:
                        items = props.get(key, [])
                        if isinstance(items, dict):
                            items = items.get('clips', []) or items.get('songs', [])

                        for item in items if isinstance(items, list) else []:
                            if isinstance(item, dict):
                                song_id = item.get('id') or item.get('clip_id')
                                if song_id and song_id not in yielded_ids:
                                    yielded_ids.add(song_id)
                                    yield SongMetadata(
                                        id=song_id,
                                        title=item.get('title', ''),
                                        artist=item.get('display_name', 'UnDaoDu'),
                                        style=item.get('metadata', {}).get('tags', ''),
                                        duration_sec=int(item.get('metadata', {}).get('duration', 0) or 0),
                                        url=f"https://suno.com/song/{song_id}"
                                    )
                except json.JSONDecodeError:
                    pass

            # Yield remaining songs (from HTML regex) with minimal metadata
            for song_id in song_ids:
                if song_id not in yielded_ids:
                    yielded_ids.add(song_id)
                    yield SongMetadata(
                        id=song_id,
                        url=f"https://suno.com/song/{song_id}"
                    )

            logger.info(f"[PLAYLIST] HTTP fallback found {len(yielded_ids)} songs")

        except Exception as e:
            logger.error(f"[PLAYLIST] Failed to fetch playlist: {e}")

    def get_song_ids_from_url_list(self, url_list: List[str]) -> Generator[SongMetadata, None, None]:
        """Extract song IDs from list of Suno URLs."""
        for url in url_list:
            match = re.search(r'/song/([a-f0-9-]{36})', url)
            if match:
                yield SongMetadata(
                    id=match.group(1),
                    url=url
                )


class SunoSTTLyricsExtractor:
    """Main orchestrator for fully automated lyrics extraction."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        skip_processed: bool = True,
        db_path: Optional[Path] = None,
    ):
        """Initialize extractor.

        Args:
            model_size: Whisper model (tiny, base, small, medium, large-v3)
            device: Inference device (cpu, cuda)
            skip_processed: Skip already processed songs
            db_path: Explicit lyrics database path; tests and isolated callers
                should supply this or set ``ANTIFAFM_LYRICS_DB``.
        """
        self.downloader = SunoAudioDownloader()
        self.transcriber = SunoSTTTranscriber(model_size, device)
        self.deduplicator = LyricsDeduplicator(db_path=db_path)
        self.playlist_fetcher = SunoPlaylistFetcher()
        self.skip_processed = skip_processed

        # Progress tracking
        self.progress = {
            "processed": [],
            "failed": [],
            "started_at": None,
            "playlist_id": None
        }

    def _load_progress(self):
        """Load progress from file."""
        if PROGRESS_FILE.exists():
            try:
                with open(PROGRESS_FILE, 'r') as f:
                    self.progress = json.load(f)
            except:
                pass

    def _save_progress(self):
        """Save progress to file."""
        PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(self.progress, f, indent=2)

    def extract_from_playlist(
        self,
        playlist_id: str,
        max_songs: int = 0,
        start_index: int = 0
    ) -> Dict:
        """Extract lyrics from all songs in a Suno playlist.

        Args:
            playlist_id: Suno playlist ID
            max_songs: Maximum songs to process (0 = all)
            start_index: Start from this index

        Returns:
            Statistics dict
        """
        self._load_progress()
        self.progress["playlist_id"] = playlist_id
        self.progress["started_at"] = datetime.utcnow().isoformat()

        # Fetch song list
        songs = list(self.playlist_fetcher.get_playlist_songs(playlist_id))

        if max_songs > 0:
            songs = songs[:max_songs]

        songs = songs[start_index:]

        stats = {
            "total": len(songs),
            "processed": 0,
            "new_lyrics": 0,
            "duplicates": 0,
            "failed": 0,
            "skipped": 0
        }

        logger.info(f"[EXTRACT] Starting extraction of {len(songs)} songs")

        for i, song in enumerate(songs):
            song_num = i + start_index + 1
            logger.info(f"\n[{song_num}/{len(songs) + start_index}] Processing: {song.id}")

            # Skip if already processed
            if self.skip_processed and self.deduplicator.is_processed(song.id):
                logger.info(f"[SKIP] Already processed: {song.id}")
                stats["skipped"] += 1
                continue

            # Skip if in current session's processed list
            if song.id in self.progress["processed"]:
                stats["skipped"] += 1
                continue

            try:
                # Download audio
                audio_path = self.downloader.download(song.id)
                if not audio_path:
                    logger.warning(f"[FAIL] Could not download: {song.id}")
                    stats["failed"] += 1
                    self.progress["failed"].append(song.id)
                    continue

                # Transcribe
                lyrics, confidence = self.transcriber.transcribe(audio_path)

                if not lyrics or len(lyrics) < 20:
                    logger.warning(f"[FAIL] No lyrics transcribed: {song.id}")
                    stats["failed"] += 1
                    self.progress["failed"].append(song.id)
                    continue

                # Create result and deduplicate
                result = TranscribedLyrics.from_transcription(song, lyrics, confidence)
                is_new, lyrics_hash = self.deduplicator.add_lyrics(result)

                if is_new:
                    stats["new_lyrics"] += 1
                else:
                    stats["duplicates"] += 1

                stats["processed"] += 1
                self.progress["processed"].append(song.id)

                # Log progress
                logger.info(f"[OK] {song.title or song.id}: {result.word_count} words, hash={lyrics_hash}")

            except Exception as e:
                logger.error(f"[ERROR] {song.id}: {e}")
                stats["failed"] += 1
                self.progress["failed"].append(song.id)

            # Save progress periodically
            if (i + 1) % 5 == 0:
                self._save_progress()

            # Rate limit (be nice to Suno CDN)
            time.sleep(1)

        self._save_progress()

        # Final stats
        dedup_stats = self.deduplicator.get_stats()
        stats.update(dedup_stats)

        return stats

    def extract_single(self, song_id: str) -> Optional[TranscribedLyrics]:
        """Extract lyrics from a single song.

        Args:
            song_id: Suno song ID

        Returns:
            TranscribedLyrics or None
        """
        song = SongMetadata(id=song_id, url=f"https://suno.com/song/{song_id}")

        # Download
        audio_path = self.downloader.download(song_id)
        if not audio_path:
            return None

        # Transcribe
        lyrics, confidence = self.transcriber.transcribe(audio_path)
        if not lyrics:
            return None

        # Create result
        result = TranscribedLyrics.from_transcription(song, lyrics, confidence)

        # Store
        self.deduplicator.add_lyrics(result)

        return result


def import_stt_to_karaoke_cache(limit: int = 0) -> dict:
    """
    Bridge STT lyrics from ffcpln_lyrics.db to karaoke cache (lyrics_cache.db).

    Converts plain text lyrics to timed format and imports into the live
    karaoke system's SQLite cache.

    Args:
        limit: Max songs to import (0 = all)

    Returns:
        Dict with import statistics
    """
    from modules.platform_integration.antifafm_broadcaster.scripts.launch import (
        _save_lyrics_to_cache
    )

    stats = {"imported": 0, "skipped": 0, "errors": 0}

    # Read from STT database
    with closing(sqlite3.connect(Path(os.getenv("ANTIFAFM_LYRICS_DB", str(LYRICS_DB))))) as conn:
        cursor = conn.execute("""
            SELECT m.song_id, m.title, m.artist, m.duration_sec, l.lyrics
            FROM song_lyrics_map m
            JOIN unique_lyrics l ON m.lyrics_hash = l.lyrics_hash
            ORDER BY m.transcribed_at DESC
        """)
        rows = cursor.fetchall()

    logger.info(f"[BRIDGE] Found {len(rows)} songs in STT database")

    for i, (song_id, title, artist, duration_sec, lyrics_text) in enumerate(rows):
        if limit > 0 and i >= limit:
            break

        try:
            # Convert plain text to timed lyrics
            timed_lyrics = _estimate_lyrics_timing(lyrics_text, duration_sec or 180)

            if not timed_lyrics:
                stats["skipped"] += 1
                continue

            # Save to karaoke cache (UPSERT handles duplicates)
            _save_lyrics_to_cache(artist, title, timed_lyrics, source='whisper-stt')
            stats["imported"] += 1

            if stats["imported"] % 20 == 0:
                logger.info(f"[BRIDGE] Imported {stats['imported']} songs...")

        except Exception as e:
            logger.error(f"[BRIDGE] Error importing {title}: {e}")
            stats["errors"] += 1

    logger.info(f"[BRIDGE] Complete: {stats['imported']} imported, {stats['skipped']} skipped, {stats['errors']} errors")
    return stats


def _estimate_lyrics_timing(lyrics_text: str, duration_sec: int = 180) -> list:
    """
    Estimate timing for plain text lyrics.

    Distributes lyrics evenly across the song duration.

    Args:
        lyrics_text: Plain text lyrics (newline separated)
        duration_sec: Song duration in seconds

    Returns:
        List of (timestamp_ms, text) tuples
    """
    lines = [line.strip() for line in lyrics_text.split('\n') if line.strip()]

    if not lines:
        return []

    # Distribute evenly across 90% of song duration (leave buffer at end)
    usable_duration = duration_sec * 0.90
    interval_ms = int((usable_duration * 1000) / len(lines))

    # Minimum 2 seconds per line
    interval_ms = max(interval_ms, 2000)

    timed_lyrics = []
    current_ms = 5000  # Start 5 seconds in

    for line in lines:
        timed_lyrics.append((current_ms, line))
        current_ms += interval_ms

    return timed_lyrics


def main():
    parser = argparse.ArgumentParser(
        description="Extract lyrics from Suno using Speech-to-Text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract from 012's full playlist (238 songs):
  python suno_stt_lyrics_extractor.py --playlist "3adb1878-12f8-4c1c-a815-bde3d7d320ed"

  # Test with first 5 songs:
  python suno_stt_lyrics_extractor.py --playlist "..." --max 5

  # Use better model for accuracy:
  python suno_stt_lyrics_extractor.py --playlist "..." --model small

  # Extract single song:
  python suno_stt_lyrics_extractor.py --song "b75f73f7-e535-4e40-982b-b59342ac1291"

  # Show stats:
  python suno_stt_lyrics_extractor.py --stats

  # Import STT lyrics to karaoke cache:
  python suno_stt_lyrics_extractor.py --import-to-cache
        """
    )

    parser.add_argument("--playlist", "-p", help="Suno playlist ID")
    parser.add_argument("--song", "-s", help="Single Suno song ID")
    parser.add_argument("--max", "-m", type=int, default=0, help="Max songs to process")
    parser.add_argument("--start", type=int, default=0, help="Start from song index")
    parser.add_argument("--model", default="base", choices=["tiny", "base", "small", "medium", "large-v3"],
                       help="Whisper model size (default: base)")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"], help="Inference device")
    parser.add_argument("--force", action="store_true", help="Re-process already processed songs")
    parser.add_argument("--stats", action="store_true", help="Show deduplication stats")
    parser.add_argument("--import-to-cache", action="store_true", dest="import_cache",
                       help="Import STT lyrics to karaoke cache (lyrics_cache.db)")

    args = parser.parse_args()

    print("=" * 70)
    print("[SUNO STT LYRICS EXTRACTOR] Fully Automated via faster-whisper")
    print("=" * 70)

    if args.stats:
        dedup = LyricsDeduplicator()
        stats = dedup.get_stats()
        print(f"\n[STATS] Deduplication Statistics:")
        print(f"  Unique lyrics:  {stats['unique_lyrics']}")
        print(f"  Total songs:    {stats['total_songs']}")
        print(f"  Dedup ratio:    {stats['dedup_ratio']:.2f}x")
        print(f"\n  Top duplicates:")
        for d in stats['top_duplicates'][:5]:
            print(f"    {d['hash']}: {d['count']} songs")
        return

    if args.import_cache:
        print(f"\n[BRIDGE] Importing STT lyrics to karaoke cache...")
        stats = import_stt_to_karaoke_cache(limit=args.max)
        print(f"\n[BRIDGE] Import Complete:")
        print(f"  Imported:  {stats['imported']}")
        print(f"  Skipped:   {stats['skipped']} (already in cache)")
        print(f"  Errors:    {stats['errors']}")
        return

    if not args.playlist and not args.song:
        parser.print_help()
        print("\n[ERROR] Specify --playlist or --song")
        return

    extractor = SunoSTTLyricsExtractor(
        model_size=args.model,
        device=args.device,
        skip_processed=not args.force
    )

    if args.song:
        # Single song extraction
        print(f"\n[EXTRACT] Single song: {args.song}")
        result = extractor.extract_single(args.song)
        if result:
            print(f"\n[SUCCESS] Extracted lyrics:")
            print(f"  Title:      {result.title}")
            print(f"  Words:      {result.word_count}")
            print(f"  Hash:       {result.lyrics_hash}")
            print(f"  Confidence: {result.confidence:.2f}")
            print(f"\n  Lyrics preview:\n{result.lyrics[:500]}...")
        else:
            print("[FAILED] Could not extract lyrics")
    else:
        # Playlist extraction
        print(f"\n[EXTRACT] Playlist: {args.playlist}")
        print(f"  Model: {args.model}")
        print(f"  Device: {args.device}")
        if args.max > 0:
            print(f"  Max songs: {args.max}")

        stats = extractor.extract_from_playlist(
            playlist_id=args.playlist,
            max_songs=args.max,
            start_index=args.start
        )

        print("\n" + "=" * 70)
        print("[EXTRACTION COMPLETE]")
        print("=" * 70)
        print(f"  Total songs:    {stats['total']}")
        print(f"  Processed:      {stats['processed']}")
        print(f"  New lyrics:     {stats['new_lyrics']}")
        print(f"  Duplicates:     {stats['duplicates']}")
        print(f"  Failed:         {stats['failed']}")
        print(f"  Skipped:        {stats['skipped']}")
        print(f"\n  Unique lyrics in DB: {stats.get('unique_lyrics', 'N/A')}")
        print(f"  Total songs in DB:   {stats.get('total_songs', 'N/A')}")
        print(f"  Dedup ratio:         {stats.get('dedup_ratio', 0):.2f}x")


if __name__ == "__main__":
    main()
