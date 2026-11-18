#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WSP framework drift sentinel managed by AI Overseer.

Audits canonical `WSP_framework/src` against backup `WSP_knowledge/src`,
persists machine-readable reports, and returns a normalized status payload.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


@dataclass
class WSPFrameworkAuditStatus:
    available: bool
    cached: bool
    checked_at: float
    ttl_sec: int
    framework_path: str
    knowledge_path: str
    framework_count: int
    knowledge_count: int
    common_count: int
    drift_count: int
    framework_only: List[str]
    knowledge_only: List[str]
    drift_files: List[str]
    index_issues: List[str]
    severity: str
    message: str
    report_path: Optional[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "cached": self.cached,
            "checked_at": self.checked_at,
            "ttl_sec": self.ttl_sec,
            "framework_path": self.framework_path,
            "knowledge_path": self.knowledge_path,
            "framework_count": self.framework_count,
            "knowledge_count": self.knowledge_count,
            "common_count": self.common_count,
            "drift_count": self.drift_count,
            "framework_only": self.framework_only,
            "knowledge_only": self.knowledge_only,
            "drift_files": self.drift_files,
            "index_issues": self.index_issues,
            "severity": self.severity,
            "message": self.message,
            "report_path": self.report_path,
        }


class WSPFrameworkSentinel:
    """AI Overseer-owned WSP framework drift and index sentinel."""

    def __init__(
        self,
        repo_root: Path,
        *,
        framework_path: Optional[Path] = None,
        knowledge_path: Optional[Path] = None,
        cache_path: Optional[Path] = None,
    ):
        self.repo_root = Path(repo_root)
        self.framework_path = framework_path or (self.repo_root / "WSP_framework" / "src")
        self.knowledge_path = knowledge_path or (self.repo_root / "WSP_knowledge" / "src")
        memory_dir = self.repo_root / "modules" / "ai_intelligence" / "ai_overseer" / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        self.cache_path = cache_path or (memory_dir / "wsp_framework_audit_cache.json")
        self.latest_report_path = memory_dir / "wsp_framework_audit_latest.json"
        self.history_path = memory_dir / "wsp_framework_audit_history.jsonl"

    def check(self, *, force: bool = False) -> Dict[str, Any]:
        """Run a WSP framework audit (or use fresh cache)."""
        ttl_sec = max(_env_int("WSP_FRAMEWORK_AUDIT_TTL_SEC", 900), 0)
        now = time.time()

        cached = self._load_json(self.cache_path)
        if cached and not force:
            checked_at = float(cached.get("checked_at", 0))
            if checked_at > 0 and (now - checked_at) < ttl_sec:
                cached["cached"] = True
                return cached

        status = self._run_audit(now=now, ttl_sec=ttl_sec)
        payload = status.as_dict()
        self._write_json(self.cache_path, payload)
        self._write_json(self.latest_report_path, payload)
        self._append_history(payload)
        return payload

    def _run_audit(self, *, now: float, ttl_sec: int) -> WSPFrameworkAuditStatus:
        framework_exists = self.framework_path.exists()
        knowledge_exists = self.knowledge_path.exists()
        if not framework_exists:
            return WSPFrameworkAuditStatus(
                available=False,
                cached=False,
                checked_at=now,
                ttl_sec=ttl_sec,
                framework_path=str(self.framework_path),
                knowledge_path=str(self.knowledge_path),
                framework_count=0,
                knowledge_count=0,
                common_count=0,
                drift_count=0,
                framework_only=[],
                knowledge_only=[],
                drift_files=[],
                index_issues=["WSP_framework/src missing"],
                severity="critical",
                message="WSP framework source path missing",
                report_path=str(self.latest_report_path),
            )

        framework_hashes = self._hash_wsp_files(self.framework_path)
        knowledge_hashes = self._hash_wsp_files(self.knowledge_path) if knowledge_exists else {}

        framework_ids = set(framework_hashes.keys())
        knowledge_ids = set(knowledge_hashes.keys())
        common_ids = framework_ids & knowledge_ids

        drift_files = sorted([wsp_id for wsp_id in common_ids if framework_hashes[wsp_id] != knowledge_hashes[wsp_id]])
        framework_only = sorted(framework_ids - knowledge_ids)
        knowledge_only = sorted(knowledge_ids - framework_ids)
        index_issues = self._check_master_index(framework_ids)
        allow_knowledge_only = os.getenv("WSP_FRAMEWORK_ALLOW_KNOWLEDGE_ONLY", "1") != "0"

        severity = "ok"
        if not knowledge_exists:
            severity = "warning"
            index_issues = [*index_issues, "WSP_knowledge/src missing"]
        elif drift_files or framework_only or index_issues:
            severity = "warning"
        elif knowledge_only and not allow_knowledge_only:
            severity = "warning"

        if severity == "ok":
            if knowledge_only:
                message = (
                    "WSP framework and knowledge backup are in sync "
                    f"(backup_only={len(knowledge_only)})"
                )
            else:
                message = "WSP framework and knowledge backup are in sync"
        else:
            message = (
                f"drift={len(drift_files)} framework_only={len(framework_only)} "
                f"knowledge_only={len(knowledge_only)} index_issues={len(index_issues)}"
            )

        return WSPFrameworkAuditStatus(
            available=True,
            cached=False,
            checked_at=now,
            ttl_sec=ttl_sec,
            framework_path=str(self.framework_path),
            knowledge_path=str(self.knowledge_path),
            framework_count=len(framework_ids),
            knowledge_count=len(knowledge_ids),
            common_count=len(common_ids),
            drift_count=len(drift_files),
            framework_only=framework_only,
            knowledge_only=knowledge_only,
            drift_files=drift_files,
            index_issues=index_issues,
            severity=severity,
            message=message,
            report_path=str(self.latest_report_path),
        )

    def _check_master_index(self, framework_ids: set[str]) -> List[str]:
        issues: List[str] = []
        index_path = self.framework_path / "WSP_MASTER_INDEX.md"
        if not index_path.exists():
            return ["WSP_MASTER_INDEX.md missing"]

        try:
            text = index_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ["WSP_MASTER_INDEX.md unreadable"]

        index_numbers = {
            int(match.group(1))
            for match in re.finditer(r"^\|\s*WSP\s+(\d{1,3})\s*\|", text, re.MULTILINE)
        }
        file_numbers = set()
        for wsp_id in framework_ids:
            match = re.match(r"^WSP_(\d{1,3})", wsp_id)
            if match:
                file_numbers.add(int(match.group(1)))

        # WSP_00 is indexed in the entry-layer table with a different format.
        missing_rows = sorted(n for n in (file_numbers - index_numbers) if n != 0)
        if missing_rows:
            issues.append("master_index missing rows for: " + ", ".join(f"WSP {n:02d}" for n in missing_rows))

        # Allocation grows over time; an indexed reservation also owns its
        # number even when a canonical protocol file has not landed yet.
        expected_next = max(file_numbers | index_numbers, default=0) + 1
        declarations = [line.strip() for line in text.splitlines()
                        if "Next Available Number" in line]
        declaration = (re.fullmatch(r"(?:-\s+)?\*\*Next Available Number\*\*:\s*WSP\s+(\d{1,3})",
                                    declarations[0])
                       if len(declarations) == 1 else None)
        if declaration is None or int(declaration.group(1)) != expected_next:
            issues.append(f"master_index next available number must uniquely declare WSP {expected_next}")

        return issues

    @staticmethod
    def _hash_wsp_files(base_path: Path) -> Dict[str, str]:
        hashes: Dict[str, str] = {}
        if not base_path.exists():
            return hashes
        for file_path in sorted(base_path.glob("WSP_*.md")):
            if not re.match(r"^WSP_\d{1,3}[A-Za-z]?(?:_|$)", file_path.stem):
                continue
            try:
                digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
                hashes[file_path.stem] = digest
            except OSError:
                continue
        return hashes

    @staticmethod
    def _load_json(path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _append_history(self, payload: Dict[str, Any]) -> None:
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload) + "\n")
        except Exception:
            pass
