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

Qwen Log Analyzer - LLM-Powered Daemon Log Analysis
Uses Qwen 1.5B for intelligent pattern extraction and root cause analysis
WSP Compliance: WSP 93 (Surgical Intelligence), WSP 77 (Intelligent Orchestration)
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from holo_index.qwen_advisor.log_parser import LogEntry, DaemonLogParser
from holo_index.qwen_advisor.llm_engine import QwenInferenceEngine

logger = logging.getLogger(__name__)


@dataclass
class DiagnosisResult:
    """Structured diagnosis from Qwen analysis"""
    issue_id: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    file: Optional[str] = None
    line: Optional[int] = None
    current_behavior: str = ""
    expected_behavior: str = ""
    root_cause: str = ""
    fix: str = ""
    code_change: Optional[str] = None
    test_case: Optional[str] = None
    log_evidence: List[int] = field(default_factory=list)  # Line numbers
    confidence: float = 0.0  # 0.0 to 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'issue_id': self.issue_id,
            'severity': self.severity,
            'file': self.file,
            'line': self.line,
            'current_behavior': self.current_behavior,
            'expected_behavior': self.expected_behavior,
            'root_cause': self.root_cause,
            'fix': self.fix,
            'code_change': self.code_change,
            'test_case': self.test_case,
            'log_evidence': self.log_evidence,
            'confidence': self.confidence
        }

    def __repr__(self):
        location = f"{self.file}:{self.line}" if self.file and self.line else "unknown"
        return f"DiagnosisResult({self.severity} - {self.issue_id} at {location})"


class QwenLogAnalyzer:
    """
    Qwen-powered log analysis engine
    Provides intelligent root cause analysis and actionable recommendations
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize Qwen log analyzer

        Args:
            model_path: Optional path to Qwen model (uses default if None)
        """
        self.qwen_engine = QwenInferenceEngine(model_path=model_path)
        self.parser = DaemonLogParser()
        self.diagnoses: List[DiagnosisResult] = []

    def analyze_log_file(self, log_file: Path, focus: Optional[str] = None) -> List[DiagnosisResult]:
        """
        Analyze entire daemon log file

        Args:
            log_file: Path to daemon log file
            focus: Optional focus area (e.g., "priority scoring", "stream detection")

        Returns:
            List of DiagnosisResult objects with actionable recommendations
        """
        logger.info(f"[QWEN-ANALYZER] Analyzing log file: {log_file}")

        # Parse log file
        entries = self.parser.parse_file(log_file)

        if not entries:
            logger.warning(f"[QWEN-ANALYZER] No entries parsed from {log_file}")
            return []

        # Extract issue patterns
        issues = self.parser.extract_issue_patterns()

        logger.info(f"[QWEN-ANALYZER] Found {len(issues)} issue categories")

        # Analyze each issue category
        self.diagnoses = []

        for issue_type, issue_entries in issues.items():
            logger.info(f"[QWEN-ANALYZER] Analyzing issue: {issue_type} ({len(issue_entries)} entries)")

            diagnosis = self.analyze_log_segment(
                entries=issue_entries,
                context=focus or issue_type,
                issue_type=issue_type
            )

            if diagnosis:
                self.diagnoses.append(diagnosis)

        logger.info(f"[QWEN-ANALYZER] Generated {len(self.diagnoses)} diagnoses")

        return self.diagnoses

    def analyze_log_segment(
        self,
        entries: List[LogEntry],
        context: str,
        issue_type: str = "unknown"
    ) -> Optional[DiagnosisResult]:
        """
        Analyze specific log segment using Qwen LLM

        Args:
            entries: List of relevant log entries
            context: Analysis context (what to focus on)
            issue_type: Type of issue being analyzed

        Returns:
            DiagnosisResult with Qwen's analysis
        """
        if not entries:
            return None

        logger.info(f"[QWEN-ANALYZER] Analyzing {len(entries)} entries for: {context}")

        # Format entries for Qwen
        formatted_log = self.parser.format_for_qwen(entries, max_lines=50)

        # Build Qwen prompt
        prompt = self._build_diagnosis_prompt(formatted_log, context, issue_type)

        # Get Qwen analysis
        try:
            response = self.qwen_engine.generate_response(
                prompt=prompt,
                system_prompt="You are debugging a YouTube livestream daemon. Provide surgical precision in your diagnosis - exact file paths, line numbers, and code fixes."
            )

            # Parse Qwen response into DiagnosisResult
            diagnosis = self._parse_qwen_response(response, entries, issue_type)

            if diagnosis:
                logger.info(f"[QWEN-ANALYZER] Diagnosis: {diagnosis}")
                return diagnosis

        except Exception as e:
            logger.error(f"[QWEN-ANALYZER] Analysis failed: {e}")
            return None

        return None

    def _build_diagnosis_prompt(self, formatted_log: str, context: str, issue_type: str) -> str:
        """Build intelligent prompt for Qwen diagnosis"""
        prompt = f"""You are debugging a YouTube livestream daemon.

**Log Context**: {context}
**Issue Type**: {issue_type}

**Log Excerpt** (last 50 relevant lines):
```
{formatted_log}
```

**Your Task**:
Analyze these logs and provide a surgical diagnosis.

**Identify**:
1. **Root Cause**: What is causing this issue? (be specific)
2. **File & Line**: Exact file path and line number where the fix should be made
3. **Current Behavior**: What is happening now?
4. **Expected Behavior**: What should happen instead?
5. **The Fix**: Specific code change needed
6. **Why This Happened**: Architectural or logical flaw

**Output Format** (JSON):
{{
  "file": "modules/path/to/file.py",
  "line": 123,
  "current_behavior": "Description of current behavior",
  "expected_behavior": "Description of expected behavior",
  "root_cause": "Why this is happening",
  "fix": "What to change",
  "code_change": "Specific code snippet to fix",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "confidence": 0.85
}}

Focus on surgical precision - exact locations and actionable fixes."""

        return prompt

    def _parse_qwen_response(
        self,
        response: str,
        entries: List[LogEntry],
        issue_type: str
    ) -> Optional[DiagnosisResult]:
        """
        Parse Qwen LLM response into DiagnosisResult

        Args:
            response: Raw Qwen response text
            entries: Original log entries analyzed
            issue_type: Type of issue

        Returns:
            DiagnosisResult object or None if parsing failed
        """
        try:
            # Try to extract JSON from response
            # Qwen might wrap JSON in markdown code blocks
            json_str = response

            # Remove markdown code blocks if present
            if '```json' in json_str:
                json_str = json_str.split('```json')[1].split('```')[0]
            elif '```' in json_str:
                json_str = json_str.split('```')[1].split('```')[0]

            # Parse JSON
            data = json.loads(json_str.strip())

            # Create DiagnosisResult
            diagnosis = DiagnosisResult(
                issue_id=f"{issue_type.upper()}_001",
                severity=data.get('severity', 'MEDIUM'),
                file=data.get('file'),
                line=data.get('line'),
                current_behavior=data.get('current_behavior', ''),
                expected_behavior=data.get('expected_behavior', ''),
                root_cause=data.get('root_cause', ''),
                fix=data.get('fix', ''),
                code_change=data.get('code_change'),
                test_case=data.get('test_case'),
                log_evidence=[e.line_number for e in entries],
                confidence=data.get('confidence', 0.7)
            )

            return diagnosis

        except json.JSONDecodeError as e:
            logger.warning(f"[QWEN-ANALYZER] Failed to parse JSON response: {e}")

            # Fallback: Create diagnosis from raw text
            return self._create_fallback_diagnosis(response, entries, issue_type)

        except Exception as e:
            logger.error(f"[QWEN-ANALYZER] Response parsing error: {e}")
            return None

    def _create_fallback_diagnosis(
        self,
        response: str,
        entries: List[LogEntry],
        issue_type: str
    ) -> DiagnosisResult:
        """Create diagnosis from unstructured Qwen response"""
        # Extract file:line pattern if present
        import re
        file_line_pattern = re.compile(r'(modules/[\w/]+\.py):(\d+)')
        match = file_line_pattern.search(response)

        file_path = match.group(1) if match else None
        line_num = int(match.group(2)) if match else None

        return DiagnosisResult(
            issue_id=f"{issue_type.upper()}_001",
            severity="MEDIUM",
            file=file_path,
            line=line_num,
            current_behavior="See Qwen analysis",
            expected_behavior="See Qwen analysis",
            root_cause=response[:500],  # First 500 chars
            fix="See full Qwen analysis",
            log_evidence=[e.line_number for e in entries],
            confidence=0.5
        )

    def analyze_priority_inversion(self, log_file: Path) -> Optional[DiagnosisResult]:
        """
        Specialized analysis for priority inversion issues
        (e.g., Move2Japan score 1.00 not chosen over UnDaoDu 5.38)

        Args:
            log_file: Path to daemon log file

        Returns:
            DiagnosisResult for priority inversion issue
        """
        logger.info("[QWEN-ANALYZER] Analyzing priority inversion issue")

        # Parse log
        entries = self.parser.parse_file(log_file)

        # Get priority scoring entries
        priority_entries = self.parser.get_priority_decisions()

        if not priority_entries:
            logger.warning("[QWEN-ANALYZER] No priority scoring entries found")
            return None

        # Analyze with specific context
        return self.analyze_log_segment(
            entries=priority_entries,
            context="Why isn't the channel with lowest score (best match) being chosen?",
            issue_type="priority_inversion"
        )

    def generate_action_report(self, output_file: Optional[Path] = None) -> str:
        """
        Generate actionable report for 0102 agent

        Args:
            output_file: Optional path to save JSON report

        Returns:
            Formatted text report
        """
        if not self.diagnoses:
            return "[QWEN-ANALYZER] No diagnoses available"

        report_lines = [
            "=" * 80,
            "QWEN LOG ANALYSIS - ACTION REPORT FOR 0102",
            "=" * 80,
            f"\nTotal Issues Found: {len(self.diagnoses)}",
            ""
        ]

        for i, diagnosis in enumerate(self.diagnoses, 1):
            report_lines.extend([
                f"\n{'=' * 80}",
                f"ISSUE #{i}: {diagnosis.issue_id}",
                f"{'=' * 80}",
                f"Severity: {diagnosis.severity}",
                f"Confidence: {diagnosis.confidence:.0%}",
                ""
            ])

            if diagnosis.file and diagnosis.line:
                report_lines.append(f"Location: {diagnosis.file}:{diagnosis.line}")

            report_lines.extend([
                f"\nCurrent Behavior:",
                f"  {diagnosis.current_behavior}",
                f"\nExpected Behavior:",
                f"  {diagnosis.expected_behavior}",
                f"\nRoot Cause:",
                f"  {diagnosis.root_cause}",
                f"\nRecommended Fix:",
                f"  {diagnosis.fix}"
            ])

            if diagnosis.code_change:
                report_lines.extend([
                    f"\nCode Change:",
                    f"```python",
                    f"{diagnosis.code_change}",
                    f"```"
                ])

            if diagnosis.test_case:
                report_lines.extend([
                    f"\nTest Case:",
                    f"  {diagnosis.test_case}"
                ])

            if diagnosis.log_evidence:
                evidence_str = ", ".join(str(line) for line in diagnosis.log_evidence[:5])
                if len(diagnosis.log_evidence) > 5:
                    evidence_str += f" ... (+{len(diagnosis.log_evidence)-5} more)"
                report_lines.append(f"\nLog Evidence: Lines {evidence_str}")

        report = "\n".join(report_lines)

        # Save JSON version if requested
        if output_file:
            json_data = [d.to_dict() for d in self.diagnoses]
            with open(output_file, 'w') as f:
                json.dump(json_data, f, indent=2)
            logger.info(f"[QWEN-ANALYZER] Saved JSON report: {output_file}")

        return report


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

    # Create analyzer
    analyzer = QwenLogAnalyzer()

    # Analyze log file
    diagnoses = analyzer.analyze_log_file(log_path, focus="stream prioritization")

    # Generate report
    report = analyzer.generate_action_report()
    print(report)

    # Save JSON
    json_output = log_path.parent / f"{log_path.stem}_diagnosis.json"
    analyzer.generate_action_report(output_file=json_output)
