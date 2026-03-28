#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io

"""
# === UTF-8 ENFORCEMENT (WSP 90) ===
# Prevent UnicodeEncodeError on Windows systems
# Only apply when running as main script, not during import
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===

Qwen Log Parser - Extract Structured Entries from Daemon Logs
WSP Compliance: WSP 93 (Surgical Intelligence), WSP 50 (Pre-Action Verification)
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class LogEntry:
    """Structured log entry from daemon log"""
    line_number: int
    timestamp: Optional[str] = None
    logger_name: Optional[str] = None
    level: Optional[str] = None
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    entry_type: str = "unknown"  # qwen_decision, error, warning, info, debug

    def __repr__(self):
        return f"LogEntry(line={self.line_number}, type={self.entry_type}, msg={self.message[:50]}...)"


class DaemonLogParser:
    """
    Parse daemon logs into structured entries for Qwen analysis
    Handles mixed content: AI conversations, daemon logs, HoloIndex output
    """

    # Regex patterns for different log formats
    TIMESTAMP_PATTERN = re.compile(r'^\[?(\d{2}:\d{2}:\d{2})\]?')
    LOGGER_PATTERN = re.compile(r'\[([\w\-\.]+)\]')
    LEVEL_PATTERN = re.compile(r'\[(DEBUG|INFO|WARNING|ERROR|CRITICAL)\]')

    # Qwen decision markers
    QWEN_SCORE_PATTERN = re.compile(r'[BOT][AI] \[QWEN-SCORE\] (.+): ([\d\.]+)')
    QWEN_DECISION_PATTERN = re.compile(r'[BOT][AI] \[QWEN-(\w+)\]')

    # Module path pattern
    MODULE_PATTERN = re.compile(r'modules\.[\w\.]+')

    # HoloIndex search pattern
    HOLO_SEARCH_PATTERN = re.compile(r'python holo_index\.py --search [\'"](.+)[\'"]')

    def __init__(self):
        self.entries: List[LogEntry] = []

    def parse_file(self, log_file: Path) -> List[LogEntry]:
        """
        Parse entire daemon log file into structured entries

        Args:
            log_file: Path to log file (e.g., 012.txt)

        Returns:
            List of LogEntry objects
        """
        logger.info(f"[LOG-PARSER] Parsing daemon log: {log_file}")

        if not log_file.exists():
            logger.error(f"[LOG-PARSER] File not found: {log_file}")
            return []

        self.entries = []

        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        logger.info(f"[LOG-PARSER] Total lines: {len(lines)}")

        for line_num, line in enumerate(lines, start=1):
            entry = self._parse_line(line_num, line)
            if entry:
                self.entries.append(entry)

        logger.info(f"[LOG-PARSER] Parsed {len(self.entries)} structured entries")

        # Group entries by execution phases
        self._group_by_phase()

        return self.entries

    def _parse_line(self, line_num: int, line: str) -> Optional[LogEntry]:
        """Parse single line into LogEntry"""
        line = line.strip()

        if not line:
            return None

        entry = LogEntry(line_number=line_num, message=line)

        # Extract timestamp
        timestamp_match = self.TIMESTAMP_PATTERN.search(line)
        if timestamp_match:
            entry.timestamp = timestamp_match.group(1)

        # Extract logger name
        logger_match = self.LOGGER_PATTERN.search(line)
        if logger_match:
            entry.logger_name = logger_match.group(1)

        # Extract log level
        level_match = self.LEVEL_PATTERN.search(line)
        if level_match:
            entry.level = level_match.group(1)

        # Classify entry type
        entry.entry_type = self._classify_entry(line, entry)

        # Extract metadata based on type
        self._extract_metadata(entry, line)

        return entry

    def _classify_entry(self, line: str, entry: LogEntry) -> str:
        """Classify log entry type"""
        # Qwen decision markers
        if '[BOT][AI] [QWEN-SCORE]' in line:
            return 'qwen_score'
        if '[BOT][AI] [QWEN-' in line:
            return 'qwen_decision'

        # Error/warning levels
        if entry.level == 'ERROR':
            return 'error'
        if entry.level == 'WARNING':
            return 'warning'

        # HoloIndex searches
        if 'python holo_index.py' in line:
            return 'holo_search'

        # Module references
        if self.MODULE_PATTERN.search(line):
            return 'module_reference'

        # Stream detection
        if 'broadcastContent' in line or 'stream' in line.lower():
            return 'stream_detection'

        # Default classification
        if entry.level:
            return entry.level.lower()

        return 'unknown'

    def _extract_metadata(self, entry: LogEntry, line: str):
        """Extract structured metadata from log entry"""
        # Qwen scores
        if entry.entry_type == 'qwen_score':
            score_match = self.QWEN_SCORE_PATTERN.search(line)
            if score_match:
                entry.metadata['channel'] = score_match.group(1)
                entry.metadata['score'] = float(score_match.group(2))

        # Module paths
        module_match = self.MODULE_PATTERN.search(line)
        if module_match:
            entry.metadata['module_path'] = module_match.group(0)

        # HoloIndex searches
        holo_match = self.HOLO_SEARCH_PATTERN.search(line)
        if holo_match:
            entry.metadata['search_query'] = holo_match.group(1)

        # Extract video IDs (11-char alphanumeric YouTube IDs)
        video_id_pattern = re.compile(r'\b([A-Za-z0-9_-]{11})\b')
        video_ids = video_id_pattern.findall(line)
        if video_ids:
            entry.metadata['video_ids'] = video_ids

    def _group_by_phase(self):
        """Group log entries by execution phases"""
        # Identify execution phases: search -> detect -> connect -> poll
        phases = {
            'search': [],
            'detect': [],
            'connect': [],
            'poll': [],
            'error': [],
            'qwen_decision': []
        }

        for entry in self.entries:
            if entry.entry_type == 'holo_search':
                phases['search'].append(entry)
            elif entry.entry_type == 'stream_detection':
                phases['detect'].append(entry)
            elif 'connect' in entry.message.lower():
                phases['connect'].append(entry)
            elif 'poll' in entry.message.lower():
                phases['poll'].append(entry)
            elif entry.entry_type in ['error', 'warning']:
                phases['error'].append(entry)
            elif entry.entry_type.startswith('qwen_'):
                phases['qwen_decision'].append(entry)

        logger.info(f"[LOG-PARSER] Phase grouping:")
        for phase, entries in phases.items():
            if entries:
                logger.info(f"  {phase}: {len(entries)} entries")

    def get_entries_by_type(self, entry_type: str) -> List[LogEntry]:
        """Get all entries of specific type"""
        return [e for e in self.entries if e.entry_type == entry_type]

    def get_entries_by_line_range(self, start: int, end: int) -> List[LogEntry]:
        """Get entries within line number range"""
        return [e for e in self.entries if start <= e.line_number <= end]

    def get_qwen_decisions(self) -> List[LogEntry]:
        """Get all Qwen decision entries"""
        return [e for e in self.entries if e.entry_type.startswith('qwen_')]

    def get_errors_and_warnings(self) -> List[LogEntry]:
        """Get all error and warning entries"""
        return [e for e in self.entries if e.entry_type in ['error', 'warning']]

    def get_priority_decisions(self) -> List[LogEntry]:
        """Get all priority scoring decisions"""
        return self.get_entries_by_type('qwen_score')

    def extract_issue_patterns(self) -> Dict[str, List[LogEntry]]:
        """
        Extract common issue patterns from logs

        Returns:
            Dict mapping issue type to list of relevant log entries
        """
        issues = {
            'priority_inversion': [],
            'connection_failures': [],
            'quota_errors': [],
            'authentication_issues': [],
            'stream_detection_failures': []
        }

        for entry in self.entries:
            # Priority inversion: Qwen scores where higher score chosen over lower
            if entry.entry_type == 'qwen_score':
                issues['priority_inversion'].append(entry)

            # Connection failures
            if 'connection' in entry.message.lower() and entry.entry_type in ['error', 'warning']:
                issues['connection_failures'].append(entry)

            # Quota errors (429, rate limit)
            if '429' in entry.message or 'quota' in entry.message.lower():
                issues['quota_errors'].append(entry)

            # Authentication issues
            if 'auth' in entry.message.lower() and entry.entry_type in ['error', 'warning']:
                issues['authentication_issues'].append(entry)

            # Stream detection failures
            if 'stream' in entry.message.lower() and entry.entry_type in ['error', 'warning']:
                issues['stream_detection_failures'].append(entry)

        # Filter out empty issue categories
        issues = {k: v for k, v in issues.items() if v}

        if issues:
            logger.info(f"[LOG-PARSER] Extracted {len(issues)} issue patterns:")
            for issue_type, entries in issues.items():
                logger.info(f"  {issue_type}: {len(entries)} occurrences")

        return issues

    def format_for_qwen(self, entries: List[LogEntry], max_lines: int = 50) -> str:
        """
        Format log entries for Qwen LLM analysis

        Args:
            entries: List of LogEntry objects
            max_lines: Maximum number of lines to include

        Returns:
            Formatted string for Qwen prompt
        """
        formatted = []

        for entry in entries[:max_lines]:
            line_str = f"[{entry.line_number:04d}]"

            if entry.timestamp:
                line_str += f" {entry.timestamp}"

            if entry.level:
                line_str += f" [{entry.level}]"

            if entry.logger_name:
                line_str += f" {entry.logger_name}"

            line_str += f": {entry.message[:100]}"

            if entry.metadata:
                line_str += f" | {entry.metadata}"

            formatted.append(line_str)

        return "\n".join(formatted)


def parse_daemon_log(log_file: Path) -> List[LogEntry]:
    """
    Convenience function to parse daemon log file

    Args:
        log_file: Path to daemon log file

    Returns:
        List of structured LogEntry objects
    """
    parser = DaemonLogParser()
    return parser.parse_file(log_file)


if __name__ == "__main__":
    # Test with 012.txt
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        log_path = Path(sys.argv[1])
    else:
        import os
        corpus_name = os.getenv("OPENCLAW_TRAINING_CORPUS", "012.txt")
        log_path = Path(f"O:/Foundups-Agent/{corpus_name}")

    entries = parse_daemon_log(log_path)

    print(f"\n[PARSER TEST] Parsed {len(entries)} entries from {log_path}")

    # Show sample entries
    print("\n[SAMPLE ENTRIES]")
    for entry in entries[:10]:
        print(entry)

    # Show Qwen decisions
    qwen_entries = [e for e in entries if e.entry_type.startswith('qwen_')]
    print(f"\n[QWEN DECISIONS] Found {len(qwen_entries)} Qwen decision entries")
    for entry in qwen_entries[:5]:
        print(f"  Line {entry.line_number}: {entry.message[:80]}")

    # Show priority scores
    score_entries = [e for e in entries if e.entry_type == 'qwen_score']
    print(f"\n[PRIORITY SCORES] Found {len(score_entries)} priority scoring entries")
    for entry in score_entries[:5]:
        print(f"  Line {entry.line_number}: {entry.metadata}")
