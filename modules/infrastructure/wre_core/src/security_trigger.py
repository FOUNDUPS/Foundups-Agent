#!/usr/bin/env python3
"""
SEC4 — Security Scan Trigger Detector

Detects security-relevant file changes and proposes SEC3 skill execution.
Default mode is report-only (proposals only, no auto-execution).

Architecture:
- SEC1: Scanner execution (subprocess)
- SEC2: Policy routing
- SEC3: WRE skill wrapper
- SEC4 (this): Trigger detection

WSP Compliance:
- WSP 97: Truthful distinction between "proposed", "executed", "skipped"
- WSP 77: Agent coordination
- WSP 27: DAE architecture
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)


ScanType = Literal["sca", "container", "sast", "iac", "all"]


@dataclass
class SecurityTriggerPattern:
    """Pattern for matching security-relevant files."""

    pattern: str
    scan_type: ScanType
    description: str
    priority: int = 1  # Higher = more urgent


# Security-relevant file patterns
SECURITY_PATTERNS: List[SecurityTriggerPattern] = [
    # Dependency files -> SCA scan
    SecurityTriggerPattern(
        pattern=r"requirements.*\.txt$",
        scan_type="sca",
        description="Python dependencies",
        priority=2,
    ),
    SecurityTriggerPattern(
        pattern=r"pyproject\.toml$",
        scan_type="sca",
        description="Python project config",
        priority=2,
    ),
    SecurityTriggerPattern(
        pattern=r"setup\.py$",
        scan_type="sca",
        description="Python setup file",
        priority=2,
    ),
    SecurityTriggerPattern(
        pattern=r"package\.json$",
        scan_type="sca",
        description="Node.js dependencies",
        priority=2,
    ),
    SecurityTriggerPattern(
        pattern=r"package-lock\.json$",
        scan_type="sca",
        description="Node.js lock file",
        priority=2,
    ),
    SecurityTriggerPattern(
        pattern=r"yarn\.lock$",
        scan_type="sca",
        description="Yarn lock file",
        priority=2,
    ),
    SecurityTriggerPattern(
        pattern=r"Gemfile(\.lock)?$",
        scan_type="sca",
        description="Ruby dependencies",
        priority=2,
    ),
    SecurityTriggerPattern(
        pattern=r"go\.(mod|sum)$",
        scan_type="sca",
        description="Go dependencies",
        priority=2,
    ),
    SecurityTriggerPattern(
        pattern=r"Cargo\.(toml|lock)$",
        scan_type="sca",
        description="Rust dependencies",
        priority=2,
    ),
    # Container files -> Trivy scan
    SecurityTriggerPattern(
        pattern=r"Dockerfile.*$",
        scan_type="container",
        description="Docker image definition",
        priority=3,
    ),
    SecurityTriggerPattern(
        pattern=r"docker-compose.*\.ya?ml$",
        scan_type="container",
        description="Docker Compose config",
        priority=2,
    ),
    SecurityTriggerPattern(
        pattern=r"\.dockerignore$",
        scan_type="container",
        description="Docker ignore file",
        priority=1,
    ),
    # CI/CD files -> IaC scan
    SecurityTriggerPattern(
        pattern=r"\.github/workflows/.*\.ya?ml$",
        scan_type="iac",
        description="GitHub Actions workflow",
        priority=3,
    ),
    SecurityTriggerPattern(
        pattern=r"\.gitlab-ci\.ya?ml$",
        scan_type="iac",
        description="GitLab CI config",
        priority=3,
    ),
    SecurityTriggerPattern(
        pattern=r"cloudbuild\.ya?ml$",
        scan_type="iac",
        description="Google Cloud Build config",
        priority=2,
    ),
    # IaC files
    SecurityTriggerPattern(
        pattern=r".*\.tf$",
        scan_type="iac",
        description="Terraform config",
        priority=2,
    ),
    SecurityTriggerPattern(
        pattern=r"kubernetes/.*\.ya?ml$",
        scan_type="iac",
        description="Kubernetes manifest",
        priority=2,
    ),
    SecurityTriggerPattern(
        pattern=r"k8s/.*\.ya?ml$",
        scan_type="iac",
        description="Kubernetes manifest",
        priority=2,
    ),
]

# Non-security file patterns (skip scan)
SKIP_PATTERNS: List[str] = [
    r"\.md$",
    r"\.txt$",
    r"\.rst$",
    r"\.json$",  # Generic JSON (not package.json)
    r"docs/",
    r"test.*\.py$",
    r"__pycache__/",
    r"\.git/",
]


@dataclass
class ScanProposal:
    """Proposal for a security scan."""

    scan_type: ScanType
    tool: str  # snyk, trivy, semgrep
    target: str
    reason: str
    triggered_by: List[str]  # Files that triggered this
    priority: int
    status: str = "proposed"  # proposed, executed, skipped


@dataclass
class TriggerReport:
    """Report from trigger detection."""

    generated_at: str
    changed_files: List[str]
    security_relevant_files: List[str]
    proposals: List[ScanProposal]
    skipped_files: List[str]
    mode: str = "report_only"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "generated_at": self.generated_at,
            "changed_files": self.changed_files,
            "security_relevant_files": self.security_relevant_files,
            "proposals": [
                {
                    "scan_type": p.scan_type,
                    "tool": p.tool,
                    "target": p.target,
                    "reason": p.reason,
                    "triggered_by": p.triggered_by,
                    "priority": p.priority,
                    "status": p.status,
                }
                for p in self.proposals
            ],
            "skipped_files": self.skipped_files,
            "mode": self.mode,
        }


class SecurityTriggerDetector:
    """
    Detects security-relevant file changes and proposes scans.

    Default mode is report-only: proposals are generated but not executed.
    Execution requires explicit call to execute_proposals().

    Example:
        detector = SecurityTriggerDetector()
        report = detector.detect_from_git_diff("HEAD~1", "HEAD")
        for proposal in report.proposals:
            print(f"Propose {proposal.tool} scan: {proposal.reason}")
    """

    def __init__(
        self,
        patterns: Optional[List[SecurityTriggerPattern]] = None,
        repo_root: Optional[Path] = None,
    ) -> None:
        """
        Initialize detector.

        Args:
            patterns: Custom patterns (default: SECURITY_PATTERNS)
            repo_root: Repository root for git commands
        """
        self.patterns = patterns or SECURITY_PATTERNS
        self.repo_root = repo_root or Path.cwd()
        self._compiled_patterns: Dict[str, re.Pattern] = {}
        self._compiled_skip: List[re.Pattern] = []
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns."""
        for pattern in self.patterns:
            self._compiled_patterns[pattern.pattern] = re.compile(
                pattern.pattern, re.IGNORECASE
            )
        for skip in SKIP_PATTERNS:
            self._compiled_skip.append(re.compile(skip, re.IGNORECASE))

    def _should_skip(self, filepath: str) -> bool:
        """Check if file should be skipped."""
        # Don't skip package.json even though .json is in skip list
        if "package.json" in filepath or "package-lock.json" in filepath:
            return False
        # Don't skip requirements*.txt files
        if "requirements" in filepath.lower() and filepath.endswith(".txt"):
            return False
        for skip_re in self._compiled_skip:
            if skip_re.search(filepath):
                return True
        return False

    def _match_patterns(self, filepath: str) -> List[SecurityTriggerPattern]:
        """Find all patterns matching a file."""
        matches = []
        for pattern in self.patterns:
            pattern_re = self._compiled_patterns[pattern.pattern]
            if pattern_re.search(filepath):
                matches.append(pattern)
        return matches

    def _scan_type_to_tool(self, scan_type: ScanType) -> str:
        """Map scan type to SEC3 tool name."""
        mapping = {
            "sca": "snyk",
            "container": "trivy",
            "sast": "semgrep",
            "iac": "trivy",
            "all": "all",
        }
        return mapping.get(scan_type, "snyk")

    def detect(self, changed_files: List[str]) -> TriggerReport:
        """
        Detect security-relevant changes in a list of files.

        Args:
            changed_files: List of changed file paths

        Returns:
            TriggerReport with proposals
        """
        generated_at = datetime.now(timezone.utc).isoformat()
        security_files: List[str] = []
        skipped_files: List[str] = []
        proposals_by_type: Dict[ScanType, ScanProposal] = {}

        for filepath in changed_files:
            # Check skip patterns
            if self._should_skip(filepath):
                skipped_files.append(filepath)
                continue

            # Match security patterns
            matches = self._match_patterns(filepath)
            if not matches:
                skipped_files.append(filepath)
                continue

            security_files.append(filepath)

            # Create/update proposals for each match
            for match in matches:
                if match.scan_type not in proposals_by_type:
                    proposals_by_type[match.scan_type] = ScanProposal(
                        scan_type=match.scan_type,
                        tool=self._scan_type_to_tool(match.scan_type),
                        target=".",
                        reason=match.description,
                        triggered_by=[filepath],
                        priority=match.priority,
                    )
                else:
                    # Add to existing proposal
                    proposal = proposals_by_type[match.scan_type]
                    if filepath not in proposal.triggered_by:
                        proposal.triggered_by.append(filepath)
                    # Upgrade priority if higher
                    if match.priority > proposal.priority:
                        proposal.priority = match.priority

        # Sort proposals by priority (descending)
        proposals = sorted(
            proposals_by_type.values(),
            key=lambda p: p.priority,
            reverse=True,
        )

        return TriggerReport(
            generated_at=generated_at,
            changed_files=changed_files,
            security_relevant_files=security_files,
            proposals=proposals,
            skipped_files=skipped_files,
            mode="report_only",
        )

    def detect_from_git_diff(
        self,
        base_ref: str = "HEAD~1",
        head_ref: str = "HEAD",
    ) -> TriggerReport:
        """
        Detect security-relevant changes from git diff.

        Args:
            base_ref: Base git ref (default: HEAD~1)
            head_ref: Head git ref (default: HEAD)

        Returns:
            TriggerReport with proposals
        """
        try:
            cmd = [
                "git",
                "diff",
                "--name-only",
                base_ref,
                head_ref,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_root,
                check=True,
            )
            changed_files = [
                f.strip() for f in result.stdout.strip().split("\n") if f.strip()
            ]
            return self.detect(changed_files)
        except subprocess.CalledProcessError as e:
            logger.error("Git diff failed: %s", e)
            return TriggerReport(
                generated_at=datetime.now(timezone.utc).isoformat(),
                changed_files=[],
                security_relevant_files=[],
                proposals=[],
                skipped_files=[],
                mode="error",
            )

    def detect_from_staged(self) -> TriggerReport:
        """Detect from staged (git add) files."""
        try:
            cmd = ["git", "diff", "--name-only", "--cached"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_root,
                check=True,
            )
            changed_files = [
                f.strip() for f in result.stdout.strip().split("\n") if f.strip()
            ]
            return self.detect(changed_files)
        except subprocess.CalledProcessError as e:
            logger.error("Git diff staged failed: %s", e)
            return TriggerReport(
                generated_at=datetime.now(timezone.utc).isoformat(),
                changed_files=[],
                security_relevant_files=[],
                proposals=[],
                skipped_files=[],
                mode="error",
            )


def get_security_trigger() -> SecurityTriggerDetector:
    """Factory function for SecurityTriggerDetector."""
    return SecurityTriggerDetector()
