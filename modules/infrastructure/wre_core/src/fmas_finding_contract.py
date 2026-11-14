"""Normalized FMAS finding types shared by health and improvement layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


class FMASFindingType(str, Enum):
    """Normalized categories emitted by FMAS-compatible producers."""

    MISSING_SRC = "missing_src"
    MISSING_TESTS = "missing_tests"
    MISSING_TEST_README = "missing_test_readme"
    MISSING_DEPENDENCY_MANIFEST = "missing_dependency_manifest"
    NO_PYTHON_FILES = "no_python_files"
    SECURITY_VULNERABILITY = "security_vulnerability"
    SECRET_DETECTED = "secret_detected"
    WSP_VIOLATION = "wsp_violation"
    DOMAIN_VIOLATION = "domain_violation"
    ORPHAN_CAPABILITY = "orphan_capability"
    DOC_STALE = "doc_stale"
    UNKNOWN = "unknown"


class FMASSeverity(str, Enum):
    """Normalized FMAS severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class FMASFinding:
    """Normalized, serializable representation of one producer observation."""

    finding_id: str
    finding_type: FMASFindingType
    severity: FMASSeverity
    module_path: str
    file_path: Optional[str] = None
    message: str = ""
    raw_finding: str = ""
    wsp_refs: List[str] = field(default_factory=list)
    source: str = "fmas"
    detected_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "finding_id": self.finding_id,
            "finding_type": self.finding_type.value,
            "severity": self.severity.value,
            "module_path": self.module_path,
            "file_path": self.file_path,
            "message": self.message,
            "raw_finding": self.raw_finding,
            "wsp_refs": self.wsp_refs,
            "source": self.source,
            "detected_at": self.detected_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FMASFinding":
        """Deserialize from a normalized dictionary."""
        raw_refs = data.get("wsp_refs", [])
        if isinstance(raw_refs, str):
            wsp_refs = [raw_refs]
        elif isinstance(raw_refs, (list, tuple)):
            wsp_refs = [item for item in raw_refs if isinstance(item, str)]
        else:
            wsp_refs = []
        raw_source = data.get("source", "fmas")
        source = raw_source if isinstance(raw_source, str) else "fmas"
        finding = cls(
            finding_id=data["finding_id"],
            finding_type=FMASFindingType(data.get("finding_type", "unknown")),
            severity=FMASSeverity(data.get("severity", "medium")),
            module_path=data.get("module_path", ""),
            file_path=data.get("file_path"),
            message=data.get("message", ""),
            raw_finding=data.get("raw_finding", ""),
            wsp_refs=wsp_refs,
            source=source,
        )
        if data.get("detected_at"):
            finding.detected_at = datetime.fromisoformat(data["detected_at"])
        return finding
