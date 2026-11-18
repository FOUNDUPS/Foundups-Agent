"""
Tests for Suno STT Lyrics Extractor.

Tests the fully automated pipeline:
    Suno CDN -> Download -> faster-whisper STT -> Dedup -> SQLite

WSP Compliance:
    - WSP 5: Test coverage for new functionality
    - WSP 72: Module independence (no cross-module test dependencies)
    - WSP 84: Validates FasterWhisperSTT reuse
"""

import hashlib
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]


class TestSunoAudioDownloader:
    """Tests for SunoAudioDownloader CDN download functionality."""

    def test_get_audio_url_format(self):
        """Test CDN URL construction."""
        from modules.platform_integration.antifafm_broadcaster.scripts.suno_stt_lyrics_extractor import (
            SunoAudioDownloader
        )

        downloader = SunoAudioDownloader()
        song_id = "e4dd0273-d1e9-47d3-871a-8218abad8bac"
        url = downloader.get_audio_url(song_id)

        assert url == f"https://cdn1.suno.ai/{song_id}.mp3"

    def test_cache_directory_creation(self):
        """Test cache directory is created."""
        from modules.platform_integration.antifafm_broadcaster.scripts.suno_stt_lyrics_extractor import (
            SunoAudioDownloader
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "test_cache"
            downloader = SunoAudioDownloader(cache_dir=cache_dir)

            assert cache_dir.exists()


class TestLyricsDeduplicator:
    """Tests for hash-based lyrics deduplication."""

    def test_hash_generation(self):
        """Test lyrics hash is deterministic."""
        from modules.platform_integration.antifafm_broadcaster.scripts.suno_stt_lyrics_extractor import (
            TranscribedLyrics, SongMetadata
        )

        song = SongMetadata(id="test123", title="Test Song")
        lyrics = "Hello world\nThis is a test"

        result1 = TranscribedLyrics.from_transcription(song, lyrics, 0.9)
        result2 = TranscribedLyrics.from_transcription(song, lyrics, 0.9)

        # Same lyrics should produce same hash
        assert result1.lyrics_hash == result2.lyrics_hash

    def test_hash_normalization(self):
        """Test hash ignores whitespace variations."""
        from modules.platform_integration.antifafm_broadcaster.scripts.suno_stt_lyrics_extractor import (
            TranscribedLyrics, SongMetadata
        )

        song = SongMetadata(id="test123")
        lyrics1 = "Hello   world"
        lyrics2 = "hello world"  # Different case, different spacing

        result1 = TranscribedLyrics.from_transcription(song, lyrics1, 0.9)
        result2 = TranscribedLyrics.from_transcription(song, lyrics2, 0.9)

        # Normalized lyrics should produce same hash
        assert result1.lyrics_hash == result2.lyrics_hash

    def test_deduplicator_stores_unique(self):
        """Test deduplicator stores unique lyrics."""
        from modules.platform_integration.antifafm_broadcaster.scripts.suno_stt_lyrics_extractor import (
            LyricsDeduplicator, TranscribedLyrics, SongMetadata
        )
        import gc

        tmpdir = tempfile.mkdtemp()
        try:
            db_path = Path(tmpdir) / "test_lyrics.db"
            dedup = LyricsDeduplicator(db_path=db_path)

            song = SongMetadata(id="song1", title="Test Song")
            result = TranscribedLyrics.from_transcription(song, "Unique lyrics here", 0.9)

            is_new, lyrics_hash = dedup.add_lyrics(result)

            assert is_new is True
            assert lyrics_hash == result.lyrics_hash
        finally:
            del dedup
            gc.collect()  # Release SQLite file locks on Windows

    def test_deduplicator_detects_duplicate(self):
        """Test deduplicator detects duplicate lyrics."""
        from modules.platform_integration.antifafm_broadcaster.scripts.suno_stt_lyrics_extractor import (
            LyricsDeduplicator, TranscribedLyrics, SongMetadata
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_lyrics.db"
            dedup = LyricsDeduplicator(db_path=db_path)

            lyrics = "Same lyrics for both songs"

            # First song
            song1 = SongMetadata(id="song1", title="Song 1")
            result1 = TranscribedLyrics.from_transcription(song1, lyrics, 0.9)
            is_new1, _ = dedup.add_lyrics(result1)

            # Second song with same lyrics
            song2 = SongMetadata(id="song2", title="Song 2")
            result2 = TranscribedLyrics.from_transcription(song2, lyrics, 0.85)
            is_new2, _ = dedup.add_lyrics(result2)

            assert is_new1 is True
            assert is_new2 is False  # Duplicate

    def test_deduplicator_stats(self):
        """Test deduplication statistics."""
        from modules.platform_integration.antifafm_broadcaster.scripts.suno_stt_lyrics_extractor import (
            LyricsDeduplicator, TranscribedLyrics, SongMetadata
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_lyrics.db"
            dedup = LyricsDeduplicator(db_path=db_path)

            # Add 3 songs with 2 unique lyrics
            for i, (lyrics, song_id) in enumerate([
                ("Lyrics A", "song1"),
                ("Lyrics A", "song2"),  # Duplicate
                ("Lyrics B", "song3"),
            ]):
                song = SongMetadata(id=song_id)
                result = TranscribedLyrics.from_transcription(song, lyrics, 0.9)
                dedup.add_lyrics(result)

            stats = dedup.get_stats()

            assert stats["unique_lyrics"] == 2
            assert stats["total_songs"] == 3
            assert stats["dedup_ratio"] == 1.5  # 3 songs / 2 unique


class TestSunoSTTTranscriber:
    """Tests for STT transcription wrapper."""

    def test_wsp84_reuse_import(self):
        """Test FasterWhisperSTT is imported from voice_command_ingestion (WSP 84)."""
        from modules.platform_integration.antifafm_broadcaster.scripts.suno_stt_lyrics_extractor import (
            SunoSTTTranscriber
        )

        transcriber = SunoSTTTranscriber(model_size="tiny")

        # Check the _initialize method imports from correct module
        import inspect
        source = inspect.getsource(transcriber._initialize)

        assert "voice_command_ingestion" in source
        assert "FasterWhisperSTT" in source


class TestSunoSTTLyricsExtractor:
    """Integration tests for full extraction pipeline."""

    def test_extractor_initialization(self, tmp_path):
        """Test extractor initializes correctly."""
        from modules.platform_integration.antifafm_broadcaster.scripts.suno_stt_lyrics_extractor import (
            SunoSTTLyricsExtractor
        )

        extractor = SunoSTTLyricsExtractor(
            model_size="tiny",
            db_path=tmp_path / "lyrics.db",
        )

        assert extractor.downloader is not None
        assert extractor.transcriber is not None
        assert extractor.deduplicator is not None

    def test_is_processed_check(self):
        """Test checking if song was already processed."""
        from modules.platform_integration.antifafm_broadcaster.scripts.suno_stt_lyrics_extractor import (
            SunoSTTLyricsExtractor, TranscribedLyrics, SongMetadata
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create extractor with temp DB
            extractor = SunoSTTLyricsExtractor(
                model_size="tiny",
                db_path=Path(tmpdir) / "test.db",
            )

            # Initially not processed
            assert extractor.deduplicator.is_processed("song123") is False

            # Add a song
            song = SongMetadata(id="song123")
            result = TranscribedLyrics.from_transcription(song, "Test lyrics", 0.9)
            extractor.deduplicator.add_lyrics(result)

            # Now should be processed
            assert extractor.deduplicator.is_processed("song123") is True


class TestCLIIntegration:
    """Tests for CLI argument parsing and execution."""

    def test_cli_help(self, tmp_path):
        """Test CLI help runs without error."""
        import subprocess

        result = subprocess.run(
            ["python", "modules/platform_integration/antifafm_broadcaster/scripts/suno_stt_lyrics_extractor.py", "--help"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env={**os.environ, "ANTIFAFM_LYRICS_DB": str(tmp_path / "lyrics.db")},
        )

        assert result.returncode == 0
        assert "playlist" in result.stdout.lower()
        assert "model" in result.stdout.lower()

    def test_cli_stats(self, tmp_path):
        """Test CLI stats command."""
        import subprocess

        result = subprocess.run(
            ["python", "modules/platform_integration/antifafm_broadcaster/scripts/suno_stt_lyrics_extractor.py", "--stats"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env={**os.environ, "ANTIFAFM_LYRICS_DB": str(tmp_path / "lyrics.db")},
        )

        assert result.returncode == 0
        assert "Unique lyrics" in result.stdout


class TestLaunchIntegration:
    """Tests for launch.py integration."""

    def test_run_suno_stt_extract_importable(self):
        """Test run_suno_stt_extract is importable from launch.py."""
        from modules.platform_integration.antifafm_broadcaster.scripts.launch import (
            run_suno_stt_extract
        )

        assert callable(run_suno_stt_extract)

    def test_direct_handler_action_config_json_valid(self):
        """The launch-handler JSON is valid but is not executable WRE Skillz."""
        import json

        skill_path = Path(__file__).parent.parent / "skillz" / "suno_stt_extract.json"

        with open(skill_path) as f:
            skill = json.load(f)

        assert skill["skill_id"] == "suno_stt_lyrics_extract"
        assert "handler" in skill
        assert skill["handler"]["function"] == "run_suno_stt_extract"
