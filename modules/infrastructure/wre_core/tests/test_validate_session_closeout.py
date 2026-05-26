# -*- coding: utf-8 -*-
"""Tests for session closeout validator.

REDDOG_SESSION_CONTINUITY_CAPTURE_PHASE1

These tests verify the validator correctly:
- Accepts valid session closeout files
- Rejects missing required fields
- Rejects oversized work_summary
- Rejects secret-like patterns
- Rejects raw transcript markers

All tests use synthetic data. No network calls, no .env reads.
"""

import json
import tempfile
from pathlib import Path

import pytest

from modules.infrastructure.wre_core.scripts.validate_session_closeout import (
    MAX_WORK_SUMMARY_LENGTH,
    validate_no_raw_transcripts,
    validate_no_secrets,
    validate_record_type,
    validate_required_fields,
    validate_session_file,
    validate_source,
    validate_work_summary_length,
)


def _create_valid_session() -> dict:
    """Create a minimal valid session object."""
    return {
        "schema_version": "1.0.0",
        "record_type": "reddog_session_closeout",
        "session_id": "test-session-001",
        "source": "reddog_session",
        "captured_at": "2026-05-27T10:00:00Z",
        "lane": "w6",
        "work_summary": "Test session for validator verification.",
    }


class TestRequiredFields:
    """Test required field validation."""

    def test_valid_session_passes(self):
        data = _create_valid_session()
        errors = validate_required_fields(data)
        assert errors == []

    def test_missing_session_id_fails(self):
        data = _create_valid_session()
        del data["session_id"]
        errors = validate_required_fields(data)
        assert any("session_id" in e for e in errors)

    def test_missing_source_fails(self):
        data = _create_valid_session()
        del data["source"]
        errors = validate_required_fields(data)
        assert any("source" in e for e in errors)

    def test_empty_work_summary_fails(self):
        data = _create_valid_session()
        data["work_summary"] = ""
        errors = validate_required_fields(data)
        assert any("work_summary" in e for e in errors)


class TestSourceValidation:
    """Test source field validation."""

    def test_valid_source_passes(self):
        data = {"source": "reddog_session"}
        errors = validate_source(data)
        assert errors == []

    def test_cursor_source_passes(self):
        data = {"source": "cursor"}
        errors = validate_source(data)
        assert errors == []

    def test_invalid_source_fails(self):
        data = {"source": "invalid_source"}
        errors = validate_source(data)
        assert len(errors) == 1
        assert "Invalid source" in errors[0]


class TestRecordTypeValidation:
    """Test record_type field validation."""

    def test_valid_record_type_passes(self):
        data = {"record_type": "reddog_session_closeout"}
        errors = validate_record_type(data)
        assert errors == []

    def test_invalid_record_type_fails(self):
        data = {"record_type": "invalid_type"}
        errors = validate_record_type(data)
        assert len(errors) == 1
        assert "Invalid record_type" in errors[0]


class TestWorkSummaryLength:
    """Test work_summary length validation."""

    def test_short_summary_passes(self):
        data = {"work_summary": "Short summary."}
        errors = validate_work_summary_length(data)
        assert errors == []

    def test_max_length_summary_passes(self):
        data = {"work_summary": "x" * MAX_WORK_SUMMARY_LENGTH}
        errors = validate_work_summary_length(data)
        assert errors == []

    def test_oversized_summary_fails(self):
        data = {"work_summary": "x" * (MAX_WORK_SUMMARY_LENGTH + 1)}
        errors = validate_work_summary_length(data)
        assert len(errors) == 1
        assert "exceeds" in errors[0]


class TestSecretDetection:
    """Test secret pattern detection."""

    def test_clean_content_passes(self):
        content = '{"work_summary": "Normal work completed."}'
        errors = validate_no_secrets(content)
        assert errors == []

    def test_openai_key_detected(self):
        content = '{"api_key": "sk-abcdefghij1234567890abcd"}'
        errors = validate_no_secrets(content)
        assert len(errors) >= 1
        assert any("Secret pattern" in e for e in errors)

    def test_google_api_key_detected(self):
        content = '{"key": "AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567"}'
        errors = validate_no_secrets(content)
        assert len(errors) >= 1
        assert any("Secret pattern" in e for e in errors)

    def test_github_pat_detected(self):
        content = '{"token": "github_pat_abcdefghij1234567890ab"}'
        errors = validate_no_secrets(content)
        assert len(errors) >= 1
        assert any("Secret pattern" in e for e in errors)

    def test_env_secret_pattern_detected(self):
        content = '"OBS_WEBSOCKET_SECRET=mySecretPassword123"'
        errors = validate_no_secrets(content)
        assert len(errors) >= 1


class TestRawTranscriptDetection:
    """Test raw transcript marker detection."""

    def test_curated_content_passes(self):
        content = '{"work_summary": "Completed PR review and merge."}'
        errors = validate_no_raw_transcripts(content)
        assert errors == []

    def test_role_assistant_detected(self):
        content = '{"messages": [{"role": "assistant", "content": "Hello"}]}'
        errors = validate_no_raw_transcripts(content)
        assert len(errors) >= 1
        assert any("Raw transcript marker" in e for e in errors)

    def test_role_user_detected(self):
        content = '{"messages": [{"role": "user", "content": "Hello"}]}'
        errors = validate_no_raw_transcripts(content)
        assert len(errors) >= 1

    def test_assistant_key_detected(self):
        content = '{"assistant": "This is the AI response"}'
        errors = validate_no_raw_transcripts(content)
        assert len(errors) >= 1


class TestFullFileValidation:
    """Test end-to-end file validation."""

    def test_valid_file_passes(self, tmp_path: Path):
        session = _create_valid_session()
        filepath = tmp_path / "valid_session.json"
        filepath.write_text(json.dumps(session), encoding="utf-8")

        valid, errors = validate_session_file(filepath)
        assert valid is True
        assert errors == []

    def test_missing_file_fails(self, tmp_path: Path):
        filepath = tmp_path / "nonexistent.json"
        valid, errors = validate_session_file(filepath)
        assert valid is False
        assert any("not found" in e for e in errors)

    def test_invalid_json_fails(self, tmp_path: Path):
        filepath = tmp_path / "invalid.json"
        filepath.write_text("{not valid json", encoding="utf-8")

        valid, errors = validate_session_file(filepath)
        assert valid is False
        assert any("Invalid JSON" in e for e in errors)

    def test_non_json_extension_fails(self, tmp_path: Path):
        filepath = tmp_path / "session.yaml"
        filepath.write_text("{}", encoding="utf-8")

        valid, errors = validate_session_file(filepath)
        assert valid is False
        assert any(".json" in e for e in errors)

    def test_file_with_secret_fails(self, tmp_path: Path):
        session = _create_valid_session()
        session["leaked_key"] = "sk-abcdefghij1234567890abcd"
        filepath = tmp_path / "leaky_session.json"
        filepath.write_text(json.dumps(session), encoding="utf-8")

        valid, errors = validate_session_file(filepath)
        assert valid is False
        assert any("Secret pattern" in e for e in errors)

    def test_file_with_transcript_fails(self, tmp_path: Path):
        session = _create_valid_session()
        session["raw_chat"] = [{"role": "assistant", "content": "Hello"}]
        filepath = tmp_path / "transcript_session.json"
        filepath.write_text(json.dumps(session), encoding="utf-8")

        valid, errors = validate_session_file(filepath)
        assert valid is False
        assert any("Raw transcript" in e for e in errors)


class TestValidatorNoMutation:
    """Test that validator does not mutate input files."""

    def test_validator_does_not_modify_file(self, tmp_path: Path):
        """Validator is read-only and must not rewrite the input file."""
        session = _create_valid_session()
        filepath = tmp_path / "immutable_session.json"
        original_content = json.dumps(session, indent=2)
        filepath.write_text(original_content, encoding="utf-8")

        original_mtime = filepath.stat().st_mtime
        original_size = filepath.stat().st_size

        valid, errors = validate_session_file(filepath)

        assert valid is True
        assert filepath.read_text(encoding="utf-8") == original_content
        assert filepath.stat().st_mtime == original_mtime
        assert filepath.stat().st_size == original_size

    def test_validator_does_not_modify_invalid_file(self, tmp_path: Path):
        """Validator must not modify even invalid files."""
        session = _create_valid_session()
        session["leaked_key"] = "sk-abcdefghij1234567890abcd"
        filepath = tmp_path / "invalid_immutable.json"
        original_content = json.dumps(session, indent=2)
        filepath.write_text(original_content, encoding="utf-8")

        original_mtime = filepath.stat().st_mtime

        valid, errors = validate_session_file(filepath)

        assert valid is False
        assert filepath.read_text(encoding="utf-8") == original_content
        assert filepath.stat().st_mtime == original_mtime
