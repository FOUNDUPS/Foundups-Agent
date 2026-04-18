#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security Pattern Memory - SQLite Storage for Vulnerability Outcomes

SEC5 — SECURITY_PATTERN_MEMORY_PHASE1

Stores security scan, trigger, and policy outcomes for recall.
Enables 0102 to query vulnerability history without re-scanning.

Architecture:
- SEC1 scanner produces normalized scan results
- SEC2 policy produces routing decisions
- SEC3 WRE skill writes scan reports
- SEC4 trigger detector proposes scans
- SEC5 (this) stores outcomes only - NO remediation

WSP Compliance:
- WSP 60: Module Memory Architecture (pattern recall)
- WSP 97: Truthful claims (observations only, no remediation learning yet)
"""

import hashlib
import json
import logging
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def _utc_iso() -> str:
    """Return current UTC timestamp as ISO string."""
    return _utc_now().isoformat()


@dataclass
class SecurityFinding:
    """
    Normalized security finding for pattern memory storage.

    Fields align with SEC1 VulnerabilityFinding + SEC2 policy decision.
    """
    # Identification
    fingerprint: str              # SHA256 hash of (tool, finding_id, target, package)
    finding_id: str               # CVE-XXXX, SNYK-XXX, rule-id, etc.
    tool: str                     # snyk, trivy, semgrep

    # Location
    target: str                   # Scan target path
    package_name: Optional[str] = None
    package_version: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None

    # Severity
    severity: str = "unknown"     # critical, high, medium, low, info, unknown
    title: str = ""
    description: str = ""

    # Policy decision (from SEC2)
    policy_decision: str = "report_only"  # gate_012, modlog_only, report_only, ignore
    requires_012: bool = False

    # Tracking
    status: str = "open"          # open, ignored, resolved, false_positive
    first_seen: str = ""          # ISO timestamp
    last_seen: str = ""           # ISO timestamp
    times_seen: int = 1

    # Source
    source_report_path: Optional[str] = None

    # Fix info (observed, not generated)
    fix_available: bool = False
    fix_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def compute_fingerprint(
        cls,
        tool: str,
        finding_id: str,
        target: str,
        package_name: Optional[str] = None,
    ) -> str:
        """
        Compute deterministic fingerprint for deduplication.

        Fingerprint = SHA256(tool:finding_id:target:package)
        """
        components = [
            tool.lower(),
            finding_id,
            target,
            package_name or "",
        ]
        content = ":".join(components)
        return hashlib.sha256(content.encode()).hexdigest()[:32]


class SecurityPatternMemory:
    """
    Security Pattern Memory - SQLite storage for vulnerability outcomes.

    Stores observations only. Does NOT generate or store remediation.

    Usage:
        memory = SecurityPatternMemory()

        # Store a finding
        finding = SecurityFinding(
            fingerprint=SecurityFinding.compute_fingerprint("snyk", "CVE-2024-001", "."),
            finding_id="CVE-2024-001",
            tool="snyk",
            target=".",
            severity="critical",
            policy_decision="gate_012",
            requires_012=True,
        )
        memory.store_finding(finding)

        # Query findings
        open_critical = memory.list_open_findings(min_severity="critical")
        summary = memory.summarize_findings()
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize security pattern memory database.

        Args:
            db_path: Path to SQLite database file.
                     Defaults to wre_core/data/security_pattern_memory.db
        """
        if db_path is None:
            self.db_path = Path(__file__).parent.parent / "data" / "security_pattern_memory.db"
        else:
            self.db_path = Path(db_path)

        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self._initialize_schema()
        logger.info(f"[SECURITY-PATTERN-MEMORY] Initialized - db={self.db_path}")

    def _initialize_schema(self) -> None:
        """Create database schema if not exists."""
        cursor = self.conn.cursor()

        # Security findings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_findings (
                fingerprint TEXT PRIMARY KEY,
                finding_id TEXT NOT NULL,
                tool TEXT NOT NULL,
                target TEXT NOT NULL,
                package_name TEXT,
                package_version TEXT,
                file_path TEXT,
                line_number INTEGER,
                severity TEXT NOT NULL,
                title TEXT,
                description TEXT,
                policy_decision TEXT NOT NULL,
                requires_012 INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                times_seen INTEGER NOT NULL DEFAULT 1,
                source_report_path TEXT,
                fix_available INTEGER DEFAULT 0,
                fix_version TEXT
            )
        """)

        # Indexes for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_security_findings_severity
            ON security_findings(severity)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_security_findings_status
            ON security_findings(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_security_findings_tool
            ON security_findings(tool)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_security_findings_last_seen
            ON security_findings(last_seen DESC)
        """)

        self.conn.commit()
        logger.debug("[SECURITY-PATTERN-MEMORY] Schema initialized")

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.debug("[SECURITY-PATTERN-MEMORY] Connection closed")

    def store_finding(self, finding: SecurityFinding) -> bool:
        """
        Store or update a security finding.

        If fingerprint exists, increments times_seen and updates last_seen.
        Otherwise, inserts new finding.

        Args:
            finding: SecurityFinding to store

        Returns:
            True if new finding, False if updated existing
        """
        cursor = self.conn.cursor()
        now = _utc_iso()

        # Check if exists
        cursor.execute(
            "SELECT fingerprint, times_seen FROM security_findings WHERE fingerprint = ?",
            (finding.fingerprint,)
        )
        existing = cursor.fetchone()

        if existing:
            # Update existing
            new_times_seen = existing["times_seen"] + 1
            cursor.execute("""
                UPDATE security_findings
                SET last_seen = ?,
                    times_seen = ?,
                    severity = ?,
                    policy_decision = ?,
                    requires_012 = ?,
                    source_report_path = ?,
                    fix_available = ?,
                    fix_version = ?
                WHERE fingerprint = ?
            """, (
                now,
                new_times_seen,
                finding.severity,
                finding.policy_decision,
                1 if finding.requires_012 else 0,
                finding.source_report_path,
                1 if finding.fix_available else 0,
                finding.fix_version,
                finding.fingerprint,
            ))
            self.conn.commit()

            logger.info(
                "[SECURITY-PATTERN-MEMORY] Updated finding - fingerprint=%s, times_seen=%d",
                finding.fingerprint[:8],
                new_times_seen,
            )
            return False
        else:
            # Insert new
            first_seen = finding.first_seen or now
            last_seen = finding.last_seen or now

            cursor.execute("""
                INSERT INTO security_findings (
                    fingerprint, finding_id, tool, target,
                    package_name, package_version, file_path, line_number,
                    severity, title, description,
                    policy_decision, requires_012, status,
                    first_seen, last_seen, times_seen,
                    source_report_path, fix_available, fix_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                finding.fingerprint,
                finding.finding_id,
                finding.tool,
                finding.target,
                finding.package_name,
                finding.package_version,
                finding.file_path,
                finding.line_number,
                finding.severity,
                finding.title,
                finding.description,
                finding.policy_decision,
                1 if finding.requires_012 else 0,
                finding.status,
                first_seen,
                last_seen,
                finding.times_seen,
                finding.source_report_path,
                1 if finding.fix_available else 0,
                finding.fix_version,
            ))
            self.conn.commit()

            logger.info(
                "[SECURITY-PATTERN-MEMORY] Stored new finding - fingerprint=%s, severity=%s",
                finding.fingerprint[:8],
                finding.severity,
            )
            return True

    def get_finding_by_fingerprint(self, fingerprint: str) -> Optional[SecurityFinding]:
        """
        Retrieve finding by fingerprint.

        Args:
            fingerprint: Finding fingerprint

        Returns:
            SecurityFinding if found, None otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM security_findings WHERE fingerprint = ?",
            (fingerprint,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_finding(row)

    def _row_to_finding(self, row: sqlite3.Row) -> SecurityFinding:
        """Convert database row to SecurityFinding."""
        return SecurityFinding(
            fingerprint=row["fingerprint"],
            finding_id=row["finding_id"],
            tool=row["tool"],
            target=row["target"],
            package_name=row["package_name"],
            package_version=row["package_version"],
            file_path=row["file_path"],
            line_number=row["line_number"],
            severity=row["severity"],
            title=row["title"] or "",
            description=row["description"] or "",
            policy_decision=row["policy_decision"],
            requires_012=bool(row["requires_012"]),
            status=row["status"],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            times_seen=row["times_seen"],
            source_report_path=row["source_report_path"],
            fix_available=bool(row["fix_available"]),
            fix_version=row["fix_version"],
        )

    def list_open_findings(
        self,
        min_severity: Optional[str] = None,
        tool: Optional[str] = None,
        limit: int = 100,
    ) -> List[SecurityFinding]:
        """
        List open (non-resolved) findings.

        Args:
            min_severity: Filter by minimum severity (critical, high, medium, low)
            tool: Filter by tool name
            limit: Maximum results

        Returns:
            List of open findings, ordered by severity then last_seen
        """
        cursor = self.conn.cursor()

        # Severity ordering
        severity_order = {
            "critical": 1,
            "high": 2,
            "medium": 3,
            "low": 4,
            "info": 5,
            "unknown": 6,
        }

        query = "SELECT * FROM security_findings WHERE status = 'open'"
        params: List[Any] = []

        if min_severity:
            min_order = severity_order.get(min_severity.lower(), 6)
            # Include this severity and higher
            included = [s for s, o in severity_order.items() if o <= min_order]
            placeholders = ",".join("?" * len(included))
            query += f" AND severity IN ({placeholders})"
            params.extend(included)

        if tool:
            query += " AND tool = ?"
            params.append(tool.lower())

        query += " ORDER BY last_seen DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        findings = [self._row_to_finding(row) for row in rows]

        # Sort by severity priority
        findings.sort(key=lambda f: severity_order.get(f.severity.lower(), 6))

        return findings

    def list_findings_requiring_012(self, limit: int = 50) -> List[SecurityFinding]:
        """
        List findings that require 012 review.

        Returns:
            List of findings where requires_012=True and status=open
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM security_findings
            WHERE requires_012 = 1 AND status = 'open'
            ORDER BY last_seen DESC
            LIMIT ?
        """, (limit,))

        return [self._row_to_finding(row) for row in cursor.fetchall()]

    def summarize_findings(self) -> Dict[str, Any]:
        """
        Generate summary statistics for all findings.

        Returns:
            Dict with counts by severity, status, tool, and totals
        """
        cursor = self.conn.cursor()

        # Total counts
        cursor.execute("SELECT COUNT(*) as total FROM security_findings")
        total = cursor.fetchone()["total"]

        # By severity
        cursor.execute("""
            SELECT severity, COUNT(*) as count
            FROM security_findings
            GROUP BY severity
        """)
        by_severity = {row["severity"]: row["count"] for row in cursor.fetchall()}

        # By status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM security_findings
            GROUP BY status
        """)
        by_status = {row["status"]: row["count"] for row in cursor.fetchall()}

        # By tool
        cursor.execute("""
            SELECT tool, COUNT(*) as count
            FROM security_findings
            GROUP BY tool
        """)
        by_tool = {row["tool"]: row["count"] for row in cursor.fetchall()}

        # Open high/critical count
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM security_findings
            WHERE status = 'open' AND severity IN ('critical', 'high')
        """)
        open_high_critical = cursor.fetchone()["count"]

        # Repeated findings (seen more than once)
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM security_findings
            WHERE times_seen > 1
        """)
        repeated = cursor.fetchone()["count"]

        # Requiring 012 review
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM security_findings
            WHERE requires_012 = 1 AND status = 'open'
        """)
        pending_012 = cursor.fetchone()["count"]

        return {
            "total_findings": total,
            "by_severity": by_severity,
            "by_status": by_status,
            "by_tool": by_tool,
            "open_high_critical": open_high_critical,
            "repeated_findings": repeated,
            "pending_012_review": pending_012,
            "generated_at": _utc_iso(),
        }

    def update_status(
        self,
        fingerprint: str,
        status: str,
    ) -> bool:
        """
        Update finding status.

        Args:
            fingerprint: Finding fingerprint
            status: New status (open, ignored, resolved, false_positive)

        Returns:
            True if updated, False if not found
        """
        valid_statuses = {"open", "ignored", "resolved", "false_positive"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")

        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE security_findings SET status = ?, last_seen = ? WHERE fingerprint = ?",
            (status, _utc_iso(), fingerprint)
        )
        self.conn.commit()

        if cursor.rowcount > 0:
            logger.info(
                "[SECURITY-PATTERN-MEMORY] Updated status - fingerprint=%s, status=%s",
                fingerprint[:8],
                status,
            )
            return True
        return False

    def get_repeated_findings(self, min_times: int = 2) -> List[SecurityFinding]:
        """
        Get findings that have been seen multiple times.

        Args:
            min_times: Minimum times_seen threshold

        Returns:
            List of repeated findings, ordered by times_seen desc
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM security_findings
            WHERE times_seen >= ?
            ORDER BY times_seen DESC
        """, (min_times,))

        return [self._row_to_finding(row) for row in cursor.fetchall()]

    def store_from_scan_report(
        self,
        scan_report: Dict[str, Any],
    ) -> Dict[str, int]:
        """
        Store findings from a normalized scan report (SEC3 output).

        Args:
            scan_report: Dict with scan_tool, target, findings, policy_decision fields

        Returns:
            Dict with counts: {"new": N, "updated": M}
        """
        tool = scan_report.get("scan_tool", "unknown")
        target = scan_report.get("target", ".")
        findings = scan_report.get("findings", [])
        default_policy = scan_report.get("policy_decision", "report_only")
        requires_012 = scan_report.get("requires_012", False)
        source_path = scan_report.get("raw_report_path")

        new_count = 0
        updated_count = 0

        for finding_data in findings:
            finding_id = finding_data.get("vuln_id", "UNKNOWN")
            package_name = finding_data.get("package_name")

            fingerprint = SecurityFinding.compute_fingerprint(
                tool=tool,
                finding_id=finding_id,
                target=target,
                package_name=package_name,
            )

            finding = SecurityFinding(
                fingerprint=fingerprint,
                finding_id=finding_id,
                tool=tool,
                target=target,
                package_name=package_name,
                package_version=finding_data.get("package_version"),
                file_path=finding_data.get("file_path"),
                line_number=finding_data.get("line_number"),
                severity=finding_data.get("severity", "unknown"),
                title=finding_data.get("title", ""),
                description=finding_data.get("description", ""),
                policy_decision=default_policy,
                requires_012=requires_012 or finding_data.get("severity") == "critical",
                fix_available=finding_data.get("fix_available", False),
                fix_version=finding_data.get("fix_version"),
                source_report_path=source_path,
            )

            is_new = self.store_finding(finding)
            if is_new:
                new_count += 1
            else:
                updated_count += 1

        logger.info(
            "[SECURITY-PATTERN-MEMORY] Stored scan report - tool=%s, new=%d, updated=%d",
            tool,
            new_count,
            updated_count,
        )

        return {"new": new_count, "updated": updated_count}
