"""Read-only WSP hints from Git-tracked working-tree files.

No application source is imported and no pattern database is opened. This is a
structural advisory scanner; FMAS owns exact-base size/exemption enforcement.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
import stat
import subprocess
from typing import Iterable, List, Optional

from modules.infrastructure.wre_core.src.wre_git_bounded_io import (
    git_read_environment, run_bounded_stdout,
)
from modules.infrastructure.wsp_core.src.wsp_domain_policy import (
    ARCHITECTURAL_EXCEPTIONS, CORE_DOMAINS, RESERVED_BLOCK_NAMES,
    evidenced_module_roots, unqualified_module_containers,
)


class WSPViolationType(Enum):
    NAMING_COHERENCE = "WSP 57 - Naming Coherence"
    FILE_SIZE = "WSP 62 - File Size Limit"
    COMPONENT_COUNT = "WSP 63 - Component Count"
    ORCHESTRATION = "WSP 65 - Single Orchestration"
    ARCHITECTURE = "WSP 3 - Architecture Organization"
    DOCUMENTATION = "WSP 22 - ModLog Documentation"
    TESTING = "WSP 6 - Test Coverage"
    DEPENDENCY = "WSP 12 - Dependency Management"
    SCAN_INCOMPLETE = "WSP 50 - Incomplete Repository Inspection"


@dataclass
class WSPViolation:
    violation_type: WSPViolationType
    description: str
    affected_files: List[str]
    severity: str
    wsp_protocol: int
    detection_time: datetime
    auto_fixable: bool
    fix_suggestion: Optional[str] = None


MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024


def _violation(kind, description, paths, severity, protocol, suggestion=None):
    return WSPViolation(kind, description, list(paths), severity, protocol,
                        datetime.now(), False, suggestion)


def _incomplete(path, reason):
    return _violation(WSPViolationType.SCAN_INCOMPLETE, reason, [path], "high", 50)


def _valid_relative(value):
    return (bool(value) and not any(c in value for c in "\\\x00:\r\n")
            and all(p not in {"", ".", ".."} for p in value.split("/")))


def _environment_path(value):
    return any(p.casefold() == ".env" or p.casefold().startswith(".env.")
               or p.casefold().endswith(".env") for p in value.split("/"))


class WSPComplianceChecker:
    """Inspect a Git root; optionally recall an explicit in-memory suppression set."""

    def __init__(self, project_root: Optional[Path] = None, *,
                 known_false_positives: Iterable[tuple[str, str]] = ()):
        self.project_root = Path(project_root or Path(__file__).resolve().parents[4]).absolute()
        self.known_false_positives = frozenset(known_false_positives)
        if any(not isinstance(x, tuple) or len(x) != 2
               or x[0] not in {"module", "root_file"}
               or type(x[1]) is not str or not x[1] for x in self.known_false_positives):
            raise ValueError("invalid_false_positive_snapshot")
        self._files = frozenset()
        self._remaining_bytes = MAX_TOTAL_BYTES

    def _git(self, *args, max_bytes=4 * 1024 * 1024):
        return run_bounded_stdout(
            ("git", "--no-optional-locks", "-C", str(self.project_root), *args),
            cwd=self.project_root, max_bytes=max_bytes, timeout_s=30,
            environment=git_read_environment(),
        ).decode("utf-8", errors="strict")

    def _inventory(self):
        root = self.project_root
        self._regular_metadata(root, directory=True)
        top = Path(self._git("rev-parse", "--show-toplevel", max_bytes=32768).strip())
        if top.resolve() != root.resolve():
            raise ValueError("repository_root_mismatch")
        inventory = self._git("ls-files", "--stage", "-z")
        if inventory and not inventory.endswith("\0"):
            raise ValueError("truncated_tracked_inventory")
        records = inventory.split("\0")
        files, errors = set(), []
        if len(records) > 100001:
            raise ValueError("tracked_inventory_limit")
        for record in filter(None, records):
            header, path = record.split("\t", 1)
            mode, _oid, stage = header.split()
            if stage != "0" or not _valid_relative(path) or path in files:
                raise ValueError("invalid_tracked_inventory")
            if _environment_path(path):
                continue  # Never open environment content, even if named *.py.
            if mode not in {"100644", "100755"}:
                errors.append(_incomplete(path, "Tracked link/submodule was not inspected"))
                continue
            files.add(path)
        self._files = frozenset(files)
        return errors

    @staticmethod
    def _regular_metadata(path, *, directory=False):
        metadata = path.lstat()
        if (stat.S_ISLNK(metadata.st_mode)
                or getattr(metadata, "st_file_attributes", 0) & 0x400):
            raise ValueError("redirected_path")
        expected = stat.S_ISDIR if directory else stat.S_ISREG
        if not expected(metadata.st_mode):
            raise ValueError("unexpected_file_type")
        return metadata

    def _tracked_file(self, relative):
        if relative not in self._files:
            return None
        path = self.project_root
        parts = relative.split("/")
        for index, part in enumerate(parts):
            path = path / part
            self._regular_metadata(path, directory=index < len(parts) - 1)
        return path

    def _is_known_false_positive(self, entity_type, entity_name):
        return (entity_type, entity_name) in self.known_false_positives

    def _module_roots(self):
        return [m for m in evidenced_module_roots(self._files)
                if not self._is_known_false_positive("module", m.split("/")[-1])]

    async def scan(self) -> List[WSPViolation]:
        """Refresh tracked inventory and return hints plus explicit incomplete-scan rows."""
        self._files = frozenset()
        self._remaining_bytes = MAX_TOTAL_BYTES
        try:
            violations = self._inventory()
        except (OSError, ValueError, UnicodeError, RuntimeError, subprocess.SubprocessError):
            return [_incomplete(".", "Git-tracked inventory unavailable or invalid")]
        for scanner in (self._scan_naming_coherence, self._scan_file_sizes,
                        self._scan_component_counts, self._scan_architecture_violations,
                        self._scan_modlog_violations, self._scan_test_coverage,
                        self._scan_dependency_violations, self._scan_root_directory_violations):
            violations.extend(await scanner())
        return violations

    async def _scan_naming_coherence(self):
        names, violations = {}, []
        for module in self._module_roots():
            name = module.split("/")[-1]
            if name in names:
                violations.append(_violation(WSPViolationType.NAMING_COHERENCE,
                    f"Duplicate module name '{name}' found", [names[name], module], "high", 57))
            else:
                names[name] = module
        return violations

    def _line_count(self, relative):
        path = self._tracked_file(relative)
        limit = min(MAX_FILE_BYTES, self._remaining_bytes)
        if limit <= 0:
            raise ValueError("scan_byte_budget_exhausted")
        with path.open("rb") as handle:
            data = handle.read(limit + 1)
        self._remaining_bytes -= len(data)
        if len(data) > limit:
            raise ValueError("source_byte_limit")
        return len(data.splitlines())

    async def _scan_file_sizes(self):
        violations = []
        for relative in sorted(self._files):
            if not relative.endswith(".py"):
                continue
            try:
                count = self._line_count(relative)
            except (OSError, ValueError):
                violations.append(_incomplete(relative, "Tracked Python source could not be fully inspected"))
                continue
            if count >= 800:
                violations.append(_violation(WSPViolationType.FILE_SIZE,
                    f"File reaches WSP62 advisory review range ({count} lines)", [relative],
                    "high" if count >= 1500 else "medium" if count > 1000 else "low", 62,
                    "Use FMAS exact-base/exemption checks before planning a refactor"))
        return violations

    async def _scan_component_counts(self):
        counts = Counter(p.rsplit("/", 1)[0] if "/" in p else "."
                         for p in self._files if p.endswith(".py"))
        return [_violation(WSPViolationType.COMPONENT_COUNT,
                f"Directory contains {count} direct Python components (>20 guideline)",
                [directory], "medium", 63)
                for directory, count in sorted(counts.items()) if count > 20]

    async def _scan_architecture_violations(self):
        violations = []
        domains = {p.split("/")[1] for p in self._files if p.startswith("modules/") and p.count("/") >= 2}
        for domain in sorted(domains - CORE_DOMAINS - ARCHITECTURAL_EXCEPTIONS):
            violations.append(_violation(WSPViolationType.ARCHITECTURE,
                f"Module domain '{domain}' not in WSP3 specification", [f"modules/{domain}"], "high", 3))
        misplaced = {"/".join(p.split("/")[:3]) for p in self._files
                     if p.startswith("modules/") and len(p.split("/")) >= 4
                     and p.split("/")[1] not in ARCHITECTURAL_EXCEPTIONS
                     and p.split("/")[2] in {"src", "tests"}}
        for path in sorted(misplaced):
            violations.append(_violation(WSPViolationType.ARCHITECTURE,
                "Domain-level source/tests must belong to an owned block", [path], "high", 3))
        for path in unqualified_module_containers(self._files):
            violations.append(_violation(WSPViolationType.ARCHITECTURE,
                "Tracked container lacks src/tests/root-contract evidence; review ownership",
                [path], "medium", 3))
        return violations

    def _required_file(self, module, suffix, kind, severity, protocol):
        relative = f"{module}/{suffix}"
        try:
            present = self._tracked_file(relative) is not None
        except (OSError, ValueError):
            return [_incomplete(relative, "Tracked module document is unavailable or redirected")]
        if present:
            return []
        return [_violation(kind, f"Missing tracked {suffix} file", [module], severity, protocol,
                           "Review the owning module and write substantive documentation")]

    async def _scan_modlog_violations(self):
        return [v for m in self._module_roots() for v in self._required_file(
            m, "ModLog.md", WSPViolationType.DOCUMENTATION, "medium", 22)]

    async def _scan_test_coverage(self):
        # Presence is documentation evidence only, never behavioral coverage.
        return [v for m in self._module_roots() for v in self._required_file(
            m, "tests/README.md", WSPViolationType.TESTING, "medium", 6)]

    async def _scan_dependency_violations(self):
        return [v for m in self._module_roots()
                if any(p.startswith(m + "/") and p.endswith(".py") for p in self._files)
                for v in self._required_file(m, "requirements.txt", WSPViolationType.DEPENDENCY, "low", 12)]

    async def _scan_root_directory_violations(self):
        allowed = {"holo_index.py", "main.py", "NAVIGATION.py", "setup.py", "__init__.py"}
        return [_violation(WSPViolationType.ARCHITECTURE,
                "Tracked root Python file needs an explicit owner/location", [p], "medium", 3,
                "Review callers and purpose before moving; preserve unique work")
                for p in sorted(self._files) if "/" not in p and p.endswith(".py")
                and p not in allowed and not self._is_known_false_positive("root_file", p)]
