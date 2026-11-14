#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Closeout Validator - REDDOG_SESSION_CONTINUITY_CAPTURE_PHASE1

Validates session closeout JSON files for schema compliance and secret safety.

This validator is READ-ONLY. It does not mutate files.
It exits 0 on valid input, non-zero on failure.

Usage:
    python validate_session_closeout.py <session-file.json> [<session-file2.json> ...]
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Tuple

REQUIRED_FIELDS = [
    "schema_version",
    "record_type",
    "session_id",
    "source",
    "captured_at",
    "lane",
    "work_summary",
]
VALID_SOURCES = ["reddog_session", "cursor", "chatgpt", "antigravity"]
VALID_RECORD_TYPE = "reddog_session_closeout"
MAX_WORK_SUMMARY_LENGTH = 2000

SECRET_PATTERNS = [
    re.compile(r"AIza[a-zA-Z0-9_-]{30,}"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"hf_[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{36,}"),
    re.compile(r"gho_[a-zA-Z0-9]{36,}"),
    re.compile(r"github_pat_[a-zA-Z0-9_]{22,}"),
    re.compile(r"oauth_token[\"']?\s*[:=]\s*[\"'][^\"']{10,}[\"']", re.IGNORECASE),
    re.compile(r"refresh_token[\"']?\s*[:=]\s*[\"'][^\"']{10,}[\"']", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"[A-Z_]+_SECRET\s*=\s*[^\s]{5,}"),
    re.compile(r"[A-Z_]+_KEY\s*=\s*[^\s]{10,}"),
    re.compile(r"[A-Z_]+_TOKEN\s*=\s*[^\s]{10,}"),
    re.compile(r"password\s*[:=]\s*[\"'][^\"']{5,}[\"']", re.IGNORECASE),
    re.compile(r"[a-zA-Z0-9+/]{40,}={0,2}"),
]

RAW_TRANSCRIPT_MARKERS = [
    re.compile(r'"role"\s*:\s*"(assistant|user|system)"'),
    re.compile(r'"assistant"\s*:\s*"'),
    re.compile(r'"user"\s*:\s*"'),
    re.compile(r'"content"\s*:\s*"[^"]{500,}"'),
]


def validate_required_fields(data: dict) -> List[str]:
    """Check all required fields are present and non-empty."""
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing required field: {field}")
        elif not data[field]:
            errors.append(f"Empty required field: {field}")
    return errors


def validate_source(data: dict) -> List[str]:
    """Check source is one of the allowed values."""
    source = data.get("source", "")
    if source and source not in VALID_SOURCES:
        return [f"Invalid source '{source}'. Must be one of: {VALID_SOURCES}"]
    return []


def validate_record_type(data: dict) -> List[str]:
    """Check record_type is the expected value."""
    record_type = data.get("record_type", "")
    if record_type and record_type != VALID_RECORD_TYPE:
        return [f"Invalid record_type '{record_type}'. Must be: {VALID_RECORD_TYPE}"]
    return []


def validate_work_summary_length(data: dict) -> List[str]:
    """Check work_summary does not exceed max length."""
    summary = data.get("work_summary", "")
    if len(summary) > MAX_WORK_SUMMARY_LENGTH:
        return [
            f"work_summary exceeds {MAX_WORK_SUMMARY_LENGTH} chars "
            f"(actual: {len(summary)})"
        ]
    return []


def validate_no_secrets(content: str) -> List[str]:
    """Scan for secret-like patterns in the raw JSON content."""
    errors = []
    for pattern in SECRET_PATTERNS:
        matches = pattern.findall(content)
        if matches:
            sample = matches[0][:30] + "..." if len(matches[0]) > 30 else matches[0]
            errors.append(f"Secret pattern detected: {sample}")
    return errors


def validate_no_raw_transcripts(content: str) -> List[str]:
    """Reject raw transcript markers that indicate uncurated chat logs."""
    errors = []
    for pattern in RAW_TRANSCRIPT_MARKERS:
        if pattern.search(content):
            errors.append(
                f"Raw transcript marker detected (pattern: {pattern.pattern[:40]}...)"
            )
    return errors


def validate_session_file(filepath: Path) -> Tuple[bool, List[str]]:
    """Validate a single session closeout file."""
    errors = []

    if not filepath.exists():
        return False, [f"File not found: {filepath}"]

    if not filepath.suffix == ".json":
        return False, [f"File must be .json: {filepath}"]

    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return False, [f"Failed to read file: {e}"]

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]

    errors.extend(validate_required_fields(data))
    errors.extend(validate_source(data))
    errors.extend(validate_record_type(data))
    errors.extend(validate_work_summary_length(data))
    errors.extend(validate_no_secrets(content))
    errors.extend(validate_no_raw_transcripts(content))

    return len(errors) == 0, errors


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: validate_session_closeout.py <file.json> [<file2.json> ...]")
        print("Validates session closeout files for schema and secret safety.")
        return 1

    all_valid = True
    for arg in sys.argv[1:]:
        filepath = Path(arg)
        valid, errors = validate_session_file(filepath)

        if valid:
            print(f"[PASS] {filepath}")
        else:
            print(f"[FAIL] {filepath}")
            for error in errors:
                print(f"  - {error}")
            all_valid = False

    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
