#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FMAS-to-ImprovementJob Bridge — Finding Parser and Mapper

Parses FMAS (Foundups Modular Audit System) findings and creates
ImprovementJob instances for codebase repair orchestration.

Architecture:
  FMAS Report (JSON/strings) -> FMASFinding (normalized) -> ImprovementJob

This is parsing/contract bridge only.
No FMAS execution.
No repair execution.
No worker wiring.

WSP Compliance:
  WSP 11  : Interface contract (typed API)
  WSP 15  : Low-lying fruit priority derivation
  WSP 50  : Pre-Action Verification (scope extraction)
  WSP 97  : System Execution Prompting (dry_run=True always)

WSP 97 TRUTH BOUNDARIES:
  - All created ImprovementJobs have dry_run=True
  - This is parsing only - no execution logic
  - Malformed findings fail truthfully with error, not silent failure
  - No CABR/payout/reward fields created

NAVIGATION:
  -> Uses: improvement_job_contract.py (ImprovementJob, ImprovementType, etc.)
  -> Called by: Future execute_improvement, improvement_router
  -> Input: tools/modular_audit/modular_audit.py output
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .fmas_finding_contract import FMASFinding, FMASFindingType, FMASSeverity
from .improvement_job_contract import (
    ImprovementJob,
    ImprovementReasonCode,
    ImprovementRiskLevel,
    ImprovementScope,
    ImprovementStatus,
    ImprovementType,
    WSP15Priority,
    create_improvement_job,
)
from .fmas_wsp62_contract import ParsedWSP62Finding, parse_wsp62_finding_text

logger = logging.getLogger("fmas_improvement_bridge")


# ---------------------------------------------------------------------------
# FMAS String Parsers
# ---------------------------------------------------------------------------


# Regex patterns for FMAS output strings
_FMAS_PATTERNS = {
    "missing_src": re.compile(
        r"(?:ERROR|CRITICAL):\s*Module\s*['\"]?([^'\"]+)['\"]?\s*is\s+missing\s+the\s+src/\s*directory",
        re.IGNORECASE,
    ),
    "missing_tests": re.compile(
        r"(?:ERROR|CRITICAL):\s*Module\s*['\"]?([^'\"]+)['\"]?\s*is\s+missing\s+the\s+tests/\s*directory",
        re.IGNORECASE,
    ),
    "missing_test_readme": re.compile(
        r"WARNING:\s*Module\s*['\"]?([^'\"]+)['\"]?\s*is\s+missing\s+tests/README\.md",
        re.IGNORECASE,
    ),
    "missing_dependency_manifest": re.compile(
        r"WARNING:\s*Module\s*['\"]?([^'\"]+)['\"]?\s*is\s+missing\s+dependency\s+manifest",
        re.IGNORECASE,
    ),
    "no_python_files": re.compile(
        r"WARNING:\s*Module\s*['\"]?([^'\"]+)['\"]?\s*has\s+no\s+Python\s+files",
        re.IGNORECASE,
    ),
    "security_vulnerability": re.compile(
        r"SECURITY_VULNERABILITY_(\w+):\s*(.+)",
        re.IGNORECASE,
    ),
    "secret_detected": re.compile(
        r"SECRET_DETECTED:\s*Potential\s+secret\s+in\s+([^:]+):(\d+)",
        re.IGNORECASE,
    ),
    "domain_violation": re.compile(
        r"(?:ERROR|WARNING):\s*Module\s*['\"]?([^'\"]+)['\"]?\s*(?:outside|invalid|unknown).*domain",
        re.IGNORECASE,
    ),
}

def generate_finding_id(raw_finding: str, module_path: str) -> str:
    """
    Generate deterministic finding ID.

    Format: fmas_{hash[:12]}
    Hash input: raw_finding + module_path
    """
    hash_input = f"{raw_finding}:{module_path}"
    return f"fmas_{hashlib.sha256(hash_input.encode()).hexdigest()[:12]}"


def parse_fmas_string(raw_finding: str) -> Optional[FMASFinding]:
    """
    Parse a single FMAS output string into FMASFinding.

    Args:
        raw_finding: Raw FMAS output string (e.g., "ERROR: Module 'x' is missing...")

    Returns:
        FMASFinding if parseable, None if not recognized.
    """
    raw_finding = raw_finding.strip()
    if not raw_finding:
        return None

    wsp62_finding = parse_wsp62_finding_text(raw_finding)
    if wsp62_finding:
        return _build_wsp62_finding(wsp62_finding, raw_finding)

    # Try each pattern
    for finding_type_key, pattern in _FMAS_PATTERNS.items():
        match = pattern.search(raw_finding)
        if match:
            return _build_finding_from_match(finding_type_key, match, raw_finding)

    # Unknown finding type
    return _build_unknown_finding(raw_finding)


def _build_wsp62_finding(
    parsed: ParsedWSP62Finding,
    raw_finding: str,
) -> FMASFinding:
    """Build a scoped WSP 62 finding without collapsing its trusted level."""
    severity = {
        "CRITICAL": FMASSeverity.CRITICAL,
        "ERROR": FMASSeverity.HIGH,
        "EXEMPTION_EXPIRED": FMASSeverity.INFO,
        "ADVISORY_ARCHIVE": FMASSeverity.INFO,
        "WARNING": FMASSeverity.MEDIUM,
        "APPROACHING": FMASSeverity.LOW,
        "WATCH": FMASSeverity.LOW,
        "INHERITED": FMASSeverity.INFO,
        "INHERITED_METADATA": FMASSeverity.INFO,
    }.get(parsed.level, FMASSeverity.INFO)
    return FMASFinding(
        finding_id=generate_finding_id(raw_finding, parsed.module_path),
        finding_type=FMASFindingType.WSP_VIOLATION,
        severity=severity,
        module_path=parsed.module_path,
        file_path=parsed.file_path,
        message=parsed.body,
        raw_finding=raw_finding,
        wsp_refs=["WSP 62"],
        source="fmas_wsp62",
    )


def _build_finding_from_match(
    finding_type_key: str,
    match: re.Match,
    raw_finding: str,
) -> FMASFinding:
    """Build FMASFinding from regex match."""
    groups = match.groups()

    # Extract module path from first capture group (for most patterns)
    module_path = groups[0] if groups else ""
    file_path = None
    message = raw_finding
    wsp_refs = []

    # Determine finding type and severity
    finding_type = FMASFindingType.UNKNOWN
    severity = FMASSeverity.MEDIUM

    if finding_type_key == "missing_src":
        finding_type = FMASFindingType.MISSING_SRC
        severity = FMASSeverity.HIGH
        wsp_refs = ["WSP 49"]
        message = f"Module '{module_path}' missing src/ directory"

    elif finding_type_key == "missing_tests":
        finding_type = FMASFindingType.MISSING_TESTS
        severity = FMASSeverity.MEDIUM
        wsp_refs = ["WSP 49", "WSP 5"]
        message = f"Module '{module_path}' missing tests/ directory"

    elif finding_type_key == "missing_test_readme":
        finding_type = FMASFindingType.MISSING_TEST_README
        severity = FMASSeverity.LOW
        wsp_refs = ["WSP 49"]
        message = f"Module '{module_path}' missing tests/README.md"

    elif finding_type_key == "missing_dependency_manifest":
        finding_type = FMASFindingType.MISSING_DEPENDENCY_MANIFEST
        severity = FMASSeverity.LOW
        wsp_refs = ["WSP 12"]
        message = f"Module '{module_path}' missing dependency manifest"

    elif finding_type_key == "no_python_files":
        finding_type = FMASFindingType.NO_PYTHON_FILES
        severity = FMASSeverity.MEDIUM
        wsp_refs = ["WSP 49"]
        message = f"Module '{module_path}' has no Python files in src/"

    elif finding_type_key == "security_vulnerability":
        finding_type = FMASFindingType.SECURITY_VULNERABILITY
        severity_str = groups[0].upper() if groups else "MEDIUM"
        severity = _map_security_severity(severity_str)
        wsp_refs = ["WSP 4", "WSP 71"]
        message = groups[1] if len(groups) > 1 else raw_finding
        # Module path not directly in security findings
        module_path = ""

    elif finding_type_key == "secret_detected":
        finding_type = FMASFindingType.SECRET_DETECTED
        severity = FMASSeverity.CRITICAL
        wsp_refs = ["WSP 71"]
        file_path = groups[0] if groups else None
        message = f"Potential secret detected in {file_path}"
        module_path = _extract_module_from_path(file_path) if file_path else ""

    elif finding_type_key == "domain_violation":
        finding_type = FMASFindingType.DOMAIN_VIOLATION
        severity = FMASSeverity.MEDIUM
        wsp_refs = ["WSP 3"]
        message = f"Module '{module_path}' has domain structure violation"

    finding_id = generate_finding_id(raw_finding, module_path)

    return FMASFinding(
        finding_id=finding_id,
        finding_type=finding_type,
        severity=severity,
        module_path=module_path,
        file_path=file_path,
        message=message,
        raw_finding=raw_finding,
        wsp_refs=wsp_refs,
        source="fmas",
    )


def _build_unknown_finding(raw_finding: str) -> FMASFinding:
    """Build FMASFinding for unrecognized FMAS output."""
    # Try to extract module path from generic patterns
    module_match = re.search(r"Module\s*['\"]?([^'\"]+)['\"]?", raw_finding)
    module_path = module_match.group(1) if module_match else ""

    # Determine severity from prefix
    severity = FMASSeverity.INFO
    if raw_finding.startswith("CRITICAL"):
        severity = FMASSeverity.CRITICAL
    elif raw_finding.startswith("ERROR"):
        severity = FMASSeverity.HIGH
    elif raw_finding.startswith("WARNING"):
        severity = FMASSeverity.MEDIUM

    finding_id = generate_finding_id(raw_finding, module_path)

    return FMASFinding(
        finding_id=finding_id,
        finding_type=FMASFindingType.UNKNOWN,
        severity=severity,
        module_path=module_path,
        message=raw_finding,
        raw_finding=raw_finding,
        source="fmas",
    )


def _map_security_severity(severity_str: str) -> FMASSeverity:
    """Map security vulnerability severity string to FMASSeverity."""
    severity_map = {
        "CRITICAL": FMASSeverity.CRITICAL,
        "HIGH": FMASSeverity.HIGH,
        "MEDIUM": FMASSeverity.MEDIUM,
        "LOW": FMASSeverity.LOW,
    }
    return severity_map.get(severity_str.upper(), FMASSeverity.MEDIUM)


def _extract_module_from_path(file_path: str) -> str:
    """Extract module path from file path."""
    if not file_path:
        return ""
    # Normalize path
    file_path = file_path.replace("\\", "/")
    # Look for modules/domain/module pattern
    match = re.search(r"modules/([^/]+/[^/]+)", file_path)
    if match:
        return f"modules/{match.group(1)}"
    return ""


# ---------------------------------------------------------------------------
# FMAS Dict Parsers (for structured input)
# ---------------------------------------------------------------------------


def parse_fmas_dict(finding_dict: Dict[str, Any]) -> FMASFinding:
    """
    Parse a structured FMAS finding dict into FMASFinding.

    Supports both:
      - Direct FMASFinding-like dicts (finding_type, severity, etc.)
      - FMAS-native dicts (type, level, module, etc.)

    Args:
        finding_dict: Dict with finding data

    Returns:
        FMASFinding instance

    Raises:
        ValueError: If dict is malformed (missing required fields)
    """
    if not finding_dict:
        raise ValueError("Finding dict is empty")

    # Check for direct FMASFinding format
    if "finding_id" in finding_dict and "finding_type" in finding_dict:
        return FMASFinding.from_dict(finding_dict)

    # Parse FMAS-native format
    finding_type_str = finding_dict.get("type", finding_dict.get("finding_type", "unknown"))
    severity_str = finding_dict.get("severity", finding_dict.get("level", "medium"))
    module_path = finding_dict.get("module_path", finding_dict.get("module", ""))
    file_path = finding_dict.get("file_path", finding_dict.get("file"))
    message = finding_dict.get("message", finding_dict.get("description", ""))
    wsp_refs = finding_dict.get("wsp_refs", finding_dict.get("wsp", []))
    raw = finding_dict.get("raw_finding", finding_dict.get("raw", ""))

    # Normalize finding type
    finding_type = _normalize_finding_type(finding_type_str)

    # Normalize severity
    severity = _normalize_severity(severity_str)

    # Generate finding ID if not provided
    finding_id = finding_dict.get("finding_id")
    if not finding_id:
        finding_id = generate_finding_id(raw or message, module_path)

    return FMASFinding(
        finding_id=finding_id,
        finding_type=finding_type,
        severity=severity,
        module_path=module_path,
        file_path=file_path,
        message=message,
        raw_finding=raw,
        wsp_refs=wsp_refs if isinstance(wsp_refs, list) else [wsp_refs],
        source=finding_dict.get("source", "fmas"),
    )


def _normalize_finding_type(type_str: str) -> FMASFindingType:
    """Normalize finding type string to enum."""
    type_map = {
        "missing_src": FMASFindingType.MISSING_SRC,
        "missing_tests": FMASFindingType.MISSING_TESTS,
        "missing_test_readme": FMASFindingType.MISSING_TEST_README,
        "missing_dependency": FMASFindingType.MISSING_DEPENDENCY_MANIFEST,
        "missing_dependency_manifest": FMASFindingType.MISSING_DEPENDENCY_MANIFEST,
        "no_python": FMASFindingType.NO_PYTHON_FILES,
        "no_python_files": FMASFindingType.NO_PYTHON_FILES,
        "security": FMASFindingType.SECURITY_VULNERABILITY,
        "security_vulnerability": FMASFindingType.SECURITY_VULNERABILITY,
        "secret": FMASFindingType.SECRET_DETECTED,
        "secret_detected": FMASFindingType.SECRET_DETECTED,
        "wsp_violation": FMASFindingType.WSP_VIOLATION,
        "wsp": FMASFindingType.WSP_VIOLATION,
        "domain": FMASFindingType.DOMAIN_VIOLATION,
        "domain_violation": FMASFindingType.DOMAIN_VIOLATION,
        "orphan": FMASFindingType.ORPHAN_CAPABILITY,
        "orphan_capability": FMASFindingType.ORPHAN_CAPABILITY,
        "doc_stale": FMASFindingType.DOC_STALE,
        "stale_doc": FMASFindingType.DOC_STALE,
    }
    try:
        return FMASFindingType(type_str.lower())
    except ValueError:
        return type_map.get(type_str.lower(), FMASFindingType.UNKNOWN)


def _normalize_severity(severity_str: str) -> FMASSeverity:
    """Normalize severity string to enum."""
    severity_map = {
        "critical": FMASSeverity.CRITICAL,
        "crit": FMASSeverity.CRITICAL,
        "high": FMASSeverity.HIGH,
        "error": FMASSeverity.HIGH,
        "medium": FMASSeverity.MEDIUM,
        "med": FMASSeverity.MEDIUM,
        "warning": FMASSeverity.MEDIUM,
        "warn": FMASSeverity.MEDIUM,
        "low": FMASSeverity.LOW,
        "info": FMASSeverity.INFO,
        "notice": FMASSeverity.INFO,
    }
    return severity_map.get(severity_str.lower(), FMASSeverity.MEDIUM)


# ---------------------------------------------------------------------------
# FMAS Finding -> ImprovementJob Mapping
# ---------------------------------------------------------------------------


def map_fmas_type_to_improvement_type(finding: FMASFinding) -> ImprovementType:
    """
    Map FMAS finding type to ImprovementType.

    Args:
        finding: FMASFinding to map

    Returns:
        Appropriate ImprovementType for the finding
    """
    type_map = {
        FMASFindingType.MISSING_SRC: ImprovementType.MODULE_REPAIR,
        FMASFindingType.MISSING_TESTS: ImprovementType.TEST_HYGIENE,
        FMASFindingType.MISSING_TEST_README: ImprovementType.DOC_LEDGER_HYGIENE,
        FMASFindingType.MISSING_DEPENDENCY_MANIFEST: ImprovementType.MODULE_REPAIR,
        FMASFindingType.NO_PYTHON_FILES: ImprovementType.MODULE_REPAIR,
        FMASFindingType.SECURITY_VULNERABILITY: ImprovementType.MODULE_REPAIR,
        FMASFindingType.SECRET_DETECTED: ImprovementType.MODULE_REPAIR,
        FMASFindingType.WSP_VIOLATION: ImprovementType.WSP_VIOLATION,
        FMASFindingType.DOMAIN_VIOLATION: ImprovementType.WSP_VIOLATION,
        FMASFindingType.ORPHAN_CAPABILITY: ImprovementType.ORPHAN_CONNECTION,
        FMASFindingType.DOC_STALE: ImprovementType.DOC_LEDGER_HYGIENE,
        FMASFindingType.UNKNOWN: ImprovementType.FMAS_SCAN,
    }
    return type_map.get(finding.finding_type, ImprovementType.FMAS_SCAN)


def map_fmas_severity_to_risk(finding: FMASFinding) -> ImprovementRiskLevel:
    """
    Map FMAS severity to ImprovementRiskLevel.

    Args:
        finding: FMASFinding to map

    Returns:
        Appropriate risk level for the finding
    """
    severity_map = {
        FMASSeverity.CRITICAL: ImprovementRiskLevel.HIGH,
        FMASSeverity.HIGH: ImprovementRiskLevel.HIGH,
        FMASSeverity.MEDIUM: ImprovementRiskLevel.MEDIUM,
        FMASSeverity.LOW: ImprovementRiskLevel.LOW,
        FMASSeverity.INFO: ImprovementRiskLevel.LOW,
    }
    return severity_map.get(finding.severity, ImprovementRiskLevel.MEDIUM)


def build_scope_from_fmas_finding(finding: FMASFinding) -> ImprovementScope:
    """
    Build ImprovementScope from FMAS finding.

    Args:
        finding: FMASFinding to extract scope from

    Returns:
        ImprovementScope with module_path, file_paths, wsp_refs
    """
    file_paths = []
    if finding.file_path:
        file_paths.append(finding.file_path)

    # Determine allowed paths based on finding type
    allowed_paths = []
    if finding.module_path:
        allowed_paths.append(f"{finding.module_path}/**")
    elif finding.file_path:
        # Allow the specific file and its directory
        allowed_paths.append(finding.file_path)

    # Block sensitive paths
    blocked_paths = [
        "**/.env",
        "**/credentials.json",
        "**/secrets.py",
        "**/*.key",
        "**/*.pem",
    ]

    return ImprovementScope(
        module_path=finding.module_path,
        file_paths=file_paths,
        wsp_refs=finding.wsp_refs,
        allowed_paths=allowed_paths,
        blocked_paths=blocked_paths,
    )


def derive_wsp15_priority(finding: FMASFinding) -> WSP15Priority:
    """
    Derive WSP15Priority from FMAS finding characteristics.

    Low-lying fruit criteria:
      - LOW/INFO severity
      - Single file or documentation change
      - No security implications

    Args:
        finding: FMASFinding to analyze

    Returns:
        WSP15Priority with appropriate scoring
    """
    # Determine complexity
    if finding.finding_type in (
        FMASFindingType.MISSING_TEST_README,
        FMASFindingType.MISSING_DEPENDENCY_MANIFEST,
        FMASFindingType.DOC_STALE,
    ):
        complexity = "trivial"
    elif finding.finding_type in (
        FMASFindingType.MISSING_TESTS,
        FMASFindingType.MISSING_SRC,
        FMASFindingType.NO_PYTHON_FILES,
    ):
        complexity = "simple"
    elif finding.finding_type in (
        FMASFindingType.WSP_VIOLATION,
        FMASFindingType.DOMAIN_VIOLATION,
        FMASFindingType.ORPHAN_CAPABILITY,
    ):
        complexity = "moderate"
    else:
        complexity = "complex"

    # Determine blast radius
    if finding.file_path and not finding.module_path:
        blast_radius = "single_file"
    elif finding.module_path:
        blast_radius = "single_module"
    else:
        blast_radius = "unknown"

    # Security findings always require review
    is_security = finding.finding_type in (
        FMASFindingType.SECURITY_VULNERABILITY,
        FMASFindingType.SECRET_DETECTED,
    )

    # Determine if low-lying fruit
    is_low_lying = (
        finding.severity in (FMASSeverity.LOW, FMASSeverity.INFO)
        and complexity in ("trivial", "simple")
        and blast_radius == "single_file"
        and not is_security
    )

    # Determine if architect review required
    requires_review = (
        finding.severity in (FMASSeverity.CRITICAL, FMASSeverity.HIGH)
        or is_security
        or complexity == "complex"
        or blast_radius in ("cross_module", "system_wide", "unknown")
    )

    reason = f"FMAS {finding.finding_type.value}: {finding.severity.value} severity, {complexity} complexity"

    return WSP15Priority(
        low_lying_fruit=is_low_lying,
        estimated_complexity=complexity,
        blast_radius=blast_radius,
        requires_architect_review=requires_review,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Main Bridge Functions
# ---------------------------------------------------------------------------


def parse_fmas_finding(
    finding: Dict[str, Any],
    *,
    idempotency_key: Optional[str] = None,
    requested_by: str = "fmas_bridge",
) -> ImprovementJob:
    """Parse one FMAS dict into a dry-run ImprovementJob proposal."""
    if not finding:
        raise ValueError("Finding dict is empty")
    fmas_finding = parse_fmas_dict(finding)
    job = _create_job_from_fmas_finding(
        fmas_finding,
        idempotency_key=idempotency_key,
        requested_by=requested_by,
    )
    if _is_untrusted_wsp62_finding(fmas_finding):
        _block_untrusted_wsp62_job(job)
    return job


def _is_untrusted_wsp62_finding(finding: FMASFinding) -> bool:
    """Recognize WSP 62 content without trusting caller-controlled labels."""
    if finding.source.strip().casefold() == "fmas_wsp62":
        return True
    if any(
        parse_wsp62_finding_text(text.strip()) is not None
        for text in (finding.raw_finding, finding.message)
        if isinstance(text, str) and text.strip()
    ):
        return True
    normalized_refs = {
        re.sub(r"[^a-z0-9]", "", str(reference).casefold())
        for reference in finding.wsp_refs
    }
    return "wsp62" in normalized_refs


def _create_job_from_fmas_finding(
    fmas_finding: FMASFinding,
    *,
    idempotency_key: Optional[str] = None,
    requested_by: str = "fmas_bridge",
) -> ImprovementJob:
    """Map one already-admitted normalized finding to a dry-run job."""

    improvement_type = map_fmas_type_to_improvement_type(fmas_finding)
    risk_level = map_fmas_severity_to_risk(fmas_finding)
    scope = build_scope_from_fmas_finding(fmas_finding)
    wsp15_priority = derive_wsp15_priority(fmas_finding)
    job = create_improvement_job(
        finding_id=fmas_finding.finding_id,
        improvement_type=improvement_type,
        scope=scope,
        risk_level=risk_level,
        requested_by=requested_by,
        payload={
            "fmas_finding": fmas_finding.to_dict(),
            "source": fmas_finding.source,
        },
        idempotency_key=idempotency_key,
    )
    job.wsp15_priority = wsp15_priority
    job.evidence_refs.append(f"FMAS:{fmas_finding.finding_id}")
    return job


def _block_untrusted_wsp62_job(job: ImprovementJob) -> None:
    """Quarantine WSP 62 input that bypassed the governed health gate."""
    job.status = ImprovementStatus.BLOCKED
    job.status_reason_code = ImprovementReasonCode.FAIL_VALIDATION_ERROR
    job.status_reason_human = "WSP 62 input requires run_wsp62_health_audit authority"


def parse_fmas_findings(findings: List[Dict[str, Any]]) -> List[ImprovementJob]:
    """
    Parse multiple FMAS findings and create ImprovementJobs.

    Malformed findings are logged but not raised (graceful degradation).

    Args:
        findings: List of FMAS finding dicts

    Returns:
        List of ImprovementJobs (may be smaller than input if some failed)
    """
    jobs = []
    for i, finding in enumerate(findings):
        try:
            job = parse_fmas_finding(finding)
            jobs.append(job)
        except Exception as e:
            logger.warning(
                "[FMAS_BRIDGE] Failed to parse finding %d: %s",
                i, str(e),
            )
            # Create a BLOCKED job for malformed findings
            job = _create_blocked_job_for_malformed(finding, str(e))
            jobs.append(job)
    return jobs


def parse_fmas_strings(raw_findings: List[str]) -> List[ImprovementJob]:
    """
    Parse raw FMAS output strings and create ImprovementJobs.

    For current FMAS text output (not structured JSON).

    Args:
        raw_findings: List of FMAS output strings

    Returns:
        List of ImprovementJobs
    """
    jobs = []
    for raw in raw_findings:
        fmas_finding = parse_fmas_string(raw)
        if fmas_finding:
            try:
                job = parse_fmas_finding(fmas_finding.to_dict())
                jobs.append(job)
            except Exception as e:
                logger.warning(
                    "[FMAS_BRIDGE] Failed to convert finding: %s",
                    str(e),
                )
    return jobs


def _create_blocked_job_for_malformed(
    finding: Dict[str, Any],
    error_msg: str,
) -> ImprovementJob:
    """Create a BLOCKED ImprovementJob for malformed findings."""
    finding_id = generate_finding_id(str(finding), "malformed")

    job = create_improvement_job(
        finding_id=finding_id,
        improvement_type=ImprovementType.FMAS_SCAN,
        risk_level=ImprovementRiskLevel.MEDIUM,
        requested_by="fmas_bridge",
        payload={
            "raw_finding": finding,
            "parse_error": error_msg,
        },
    )

    job.status = ImprovementStatus.BLOCKED
    job.status_reason_code = ImprovementReasonCode.FAIL_VALIDATION_ERROR
    job.status_reason_human = f"Malformed FMAS finding: {error_msg}"

    return job
