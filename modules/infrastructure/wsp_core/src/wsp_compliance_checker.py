"""
WSP Compliance Checker (Infrastructure)
Scans the repository for WSP violations (platform-agnostic).

WSP Compliance:
- WSP 3: Architecture organization
- WSP 22: ModLog documentation
- WSP 57: Naming coherence
- WSP 60: Pattern memory (false-positive recall)
- WSP 62: File size limit
- WSP 63: Component count
- WSP 6: Test coverage
- WSP 12: Dependency management
"""

import logging
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Iterator, List, Optional, Any

# Pattern memory for learned false positives (WSP 48/60)
try:
    from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory
except Exception:
    PatternMemory = None

logger = logging.getLogger(__name__)


class WSPViolationType(Enum):
    """Types of WSP violations"""
    NAMING_COHERENCE = "WSP 57 - Naming Coherence"
    FILE_SIZE = "WSP 62 - File Size Limit"
    COMPONENT_COUNT = "WSP 63 - Component Count"
    ORCHESTRATION = "WSP 65 - Single Orchestration"
    ARCHITECTURE = "WSP 3 - Architecture Organization"
    DOCUMENTATION = "WSP 22 - ModLog Documentation"
    TESTING = "WSP 6 - Test Coverage"
    DEPENDENCY = "WSP 12 - Dependency Management"


@dataclass
class WSPViolation:
    """WSP violation information"""
    violation_type: WSPViolationType
    description: str
    affected_files: List[str]
    severity: str  # "critical", "high", "medium", "low"
    wsp_protocol: int
    detection_time: datetime
    auto_fixable: bool
    fix_suggestion: Optional[str] = None


class WSPComplianceChecker:
    """
    Platform-agnostic WSP compliance scanner.
    """
    IGNORED_DIR_NAMES = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
    }

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).resolve().parents[4]
        self.pattern_memory: Optional[Any] = None
        if PatternMemory:
            try:
                self.pattern_memory = PatternMemory()
            except Exception as exc:
                logger.warning("PatternMemory unavailable for false-positive checks: %s", exc)

    def _should_skip_path(self, path: Path) -> bool:
        """Skip hidden, virtualenv, cache, and symlink-heavy paths."""
        if path.name in self.IGNORED_DIR_NAMES:
            return True
        if path.is_symlink():
            return True
        return any(part in self.IGNORED_DIR_NAMES for part in path.parts)

    def _safe_iterdir(self, path: Path) -> Iterator[Path]:
        """Yield directory entries while tolerating inaccessible paths."""
        try:
            for entry in path.iterdir():
                if self._should_skip_path(entry):
                    continue
                yield entry
        except OSError as exc:
            logger.debug("Skipping inaccessible directory %s: %s", path, exc)

    def _safe_walk(self, root: Path) -> Iterator[Path]:
        """Depth-first traversal that skips inaccessible or ignored paths."""
        stack = [root]
        while stack:
            current = stack.pop()
            for entry in self._safe_iterdir(current):
                yield entry
                try:
                    if entry.is_dir():
                        stack.append(entry)
                except OSError as exc:
                    logger.debug("Skipping inaccessible path %s: %s", entry, exc)

    def _iter_python_files(self, root: Path) -> Iterator[Path]:
        """Yield Python files under root using safe traversal."""
        for path in self._safe_walk(root):
            if path.suffix == ".py":
                yield path

    def _iter_directories(self, root: Path) -> Iterator[Path]:
        """Yield directories under root using safe traversal."""
        for path in self._safe_walk(root):
            try:
                if path.is_dir():
                    yield path
            except OSError as exc:
                logger.debug("Skipping inaccessible directory %s: %s", path, exc)

    def _is_known_false_positive(self, entity_type: str, entity_name: str) -> bool:
        """Check pattern memory for known false positives before flagging."""
        if not self.pattern_memory:
            return False
        try:
            details = self.pattern_memory.get_false_positive_reason(entity_type, entity_name)
            if details:
                reason = details.get("reason")
                actual_location = details.get("actual_location")
                note = f": {reason}" if reason else ""
                if actual_location:
                    note += f" (actual: {actual_location})"
                logger.info("Skipping known false positive %s '%s'%s", entity_type, entity_name, note)
                return True
        except Exception as exc:
            logger.warning("False-positive lookup failed for %s '%s': %s", entity_type, entity_name, exc)
        return False

    async def scan(self) -> List[WSPViolation]:
        """Run all WSP compliance scans."""
        violations: List[WSPViolation] = []
        violations.extend(await self._scan_naming_coherence())
        violations.extend(await self._scan_file_sizes())
        violations.extend(await self._scan_component_counts())
        violations.extend(await self._scan_architecture_violations())
        violations.extend(await self._scan_modlog_violations())
        violations.extend(await self._scan_test_coverage())
        violations.extend(await self._scan_dependency_violations())
        violations.extend(await self._scan_root_directory_violations())  # WSP 3 root file check
        return violations

    async def _scan_naming_coherence(self) -> List[WSPViolation]:
        violations: List[WSPViolation] = []
        module_names = {}
        modules_dir = self.project_root / "modules"
        if modules_dir.exists():
            for domain_dir in self._safe_iterdir(modules_dir):
                try:
                    is_domain_dir = domain_dir.is_dir()
                except OSError as exc:
                    logger.debug("Skipping inaccessible module domain %s: %s", domain_dir, exc)
                    continue
                if is_domain_dir and not domain_dir.name.startswith('.'):
                    for module_dir in self._safe_iterdir(domain_dir):
                        try:
                            is_module_dir = module_dir.is_dir()
                        except OSError as exc:
                            logger.debug("Skipping inaccessible module directory %s: %s", module_dir, exc)
                            continue
                        if is_module_dir and not module_dir.name.startswith('.'):
                            module_name = module_dir.name
                            if self._is_known_false_positive("module", module_name):
                                continue
                            if module_name in module_names:
                                violations.append(WSPViolation(
                                    violation_type=WSPViolationType.NAMING_COHERENCE,
                                    description=f"Duplicate module name '{module_name}' found",
                                    affected_files=[str(module_names[module_name]), str(module_dir)],
                                    severity="high",
                                    wsp_protocol=57,
                                    detection_time=datetime.now(),
                                    auto_fixable=False,
                                    fix_suggestion="Remove duplicate module or rename to ensure uniqueness"
                                ))
                            else:
                                module_names[module_name] = module_dir
        return violations

    async def _scan_file_sizes(self) -> List[WSPViolation]:
        violations: List[WSPViolation] = []
        for py_file in self._iter_python_files(self.project_root):
            if py_file.name.startswith('.') or 'test' in py_file.name:
                continue
            try:
                rel_parts = py_file.relative_to(self.project_root).parts
                if len(rel_parts) >= 3 and rel_parts[0] == "modules":
                    module_name = rel_parts[2]
                    if self._is_known_false_positive("module", module_name):
                        continue
            except ValueError:
                pass
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    line_count = sum(1 for _ in f)
                if line_count > 500:
                    violations.append(WSPViolation(
                        violation_type=WSPViolationType.FILE_SIZE,
                        description=f"File exceeds 500 lines ({line_count} lines)",
                        affected_files=[str(py_file.relative_to(self.project_root))],
                        severity="medium" if line_count < 750 else "high",
                        wsp_protocol=62,
                        detection_time=datetime.now(),
                        auto_fixable=False,
                        fix_suggestion="Refactor into smaller components or extract functionality"
                    ))
            except Exception as e:
                logger.warning("Could not scan %s: %s", py_file, e)
        return violations

    async def _scan_component_counts(self) -> List[WSPViolation]:
        violations: List[WSPViolation] = []
        for directory in self._iter_directories(self.project_root):
            if directory.name.startswith('.'):
                continue
            if self._is_known_false_positive("module", directory.name):
                continue
            py_files = list(self._iter_python_files(directory))
            if len(py_files) > 20:
                violations.append(WSPViolation(
                    violation_type=WSPViolationType.COMPONENT_COUNT,
                    description=f"Directory contains {len(py_files)} components (>20 limit)",
                    affected_files=[str(directory.relative_to(self.project_root))],
                    severity="medium",
                    wsp_protocol=63,
                    detection_time=datetime.now(),
                    auto_fixable=False,
                    fix_suggestion="Organize components into subdirectories by function"
                ))
        return violations

    async def _scan_architecture_violations(self) -> List[WSPViolation]:
        violations: List[WSPViolation] = []
        modules_dir = self.project_root / "modules"
        if not modules_dir.exists():
            return violations
        expected_domains = {
            "ai_intelligence", "communication", "platform_integration",
            "infrastructure", "foundups", "gamification", "blockchain",
            "development", "aggregation", "wre_core"
        }
        for item in self._safe_iterdir(modules_dir):
            try:
                is_dir = item.is_dir()
            except OSError as exc:
                logger.debug("Skipping inaccessible module domain %s: %s", item, exc)
                continue
            if is_dir and not item.name.startswith('.'):
                if self._is_known_false_positive("module", item.name):
                    continue
                if item.name not in expected_domains:
                    violations.append(WSPViolation(
                        violation_type=WSPViolationType.ARCHITECTURE,
                        description=f"Module domain '{item.name}' not in WSP 3 specification",
                        affected_files=[str(item.relative_to(self.project_root))],
                        severity="high",
                        wsp_protocol=3,
                        detection_time=datetime.now(),
                        auto_fixable=False,
                        fix_suggestion="Move modules to appropriate WSP 3 domain or update specification"
                    ))
        return violations

    async def _scan_modlog_violations(self) -> List[WSPViolation]:
        violations: List[WSPViolation] = []
        modules_dir = self.project_root / "modules"
        if not modules_dir.exists():
            return violations
        for domain_dir in self._safe_iterdir(modules_dir):
            try:
                is_domain_dir = domain_dir.is_dir()
            except OSError as exc:
                logger.debug("Skipping inaccessible module domain %s: %s", domain_dir, exc)
                continue
            if not is_domain_dir or domain_dir.name.startswith('.'):
                continue
            for module_dir in self._safe_iterdir(domain_dir):
                try:
                    is_module_dir = module_dir.is_dir()
                except OSError as exc:
                    logger.debug("Skipping inaccessible module directory %s: %s", module_dir, exc)
                    continue
                if not is_module_dir or module_dir.name.startswith('.'):
                    continue
                if self._is_known_false_positive("module", module_dir.name):
                    continue
                modlog_file = module_dir / "ModLog.md"
                if not modlog_file.exists():
                    violations.append(WSPViolation(
                        violation_type=WSPViolationType.DOCUMENTATION,
                        description="Missing ModLog.md file",
                        affected_files=[str(module_dir.relative_to(self.project_root))],
                        severity="medium",
                        wsp_protocol=22,
                        detection_time=datetime.now(),
                        auto_fixable=True,
                        fix_suggestion="Create ModLog.md file with module development history"
                    ))
        return violations

    async def _scan_test_coverage(self) -> List[WSPViolation]:
        violations: List[WSPViolation] = []
        modules_dir = self.project_root / "modules"
        if not modules_dir.exists():
            return violations
        for domain_dir in self._safe_iterdir(modules_dir):
            try:
                is_domain_dir = domain_dir.is_dir()
            except OSError as exc:
                logger.debug("Skipping inaccessible module domain %s: %s", domain_dir, exc)
                continue
            if not is_domain_dir or domain_dir.name.startswith('.'):
                continue
            for module_dir in self._safe_iterdir(domain_dir):
                try:
                    is_module_dir = module_dir.is_dir()
                except OSError as exc:
                    logger.debug("Skipping inaccessible module directory %s: %s", module_dir, exc)
                    continue
                if not is_module_dir or module_dir.name.startswith('.'):
                    continue
                if self._is_known_false_positive("module", module_dir.name):
                    continue
                tests_dir = module_dir / "tests"
                if not tests_dir.exists():
                    violations.append(WSPViolation(
                        violation_type=WSPViolationType.TESTING,
                        description="Missing tests directory",
                        affected_files=[str(module_dir.relative_to(self.project_root))],
                        severity="medium",
                        wsp_protocol=6,
                        detection_time=datetime.now(),
                        auto_fixable=True,
                        fix_suggestion="Create tests directory with test files and README.md"
                    ))
                elif not (tests_dir / "README.md").exists():
                    violations.append(WSPViolation(
                        violation_type=WSPViolationType.TESTING,
                        description="Missing tests/README.md file",
                        affected_files=[str(tests_dir.relative_to(self.project_root))],
                        severity="low",
                        wsp_protocol=6,
                        detection_time=datetime.now(),
                        auto_fixable=True,
                        fix_suggestion="Create tests/README.md with testing strategy documentation"
                    ))
        return violations

    async def _scan_dependency_violations(self) -> List[WSPViolation]:
        violations: List[WSPViolation] = []
        modules_dir = self.project_root / "modules"
        if not modules_dir.exists():
            return violations
        for domain_dir in self._safe_iterdir(modules_dir):
            try:
                is_domain_dir = domain_dir.is_dir()
            except OSError as exc:
                logger.debug("Skipping inaccessible module domain %s: %s", domain_dir, exc)
                continue
            if not is_domain_dir or domain_dir.name.startswith('.'):
                continue
            for module_dir in self._safe_iterdir(domain_dir):
                try:
                    is_module_dir = module_dir.is_dir()
                except OSError as exc:
                    logger.debug("Skipping inaccessible module directory %s: %s", module_dir, exc)
                    continue
                if not is_module_dir or module_dir.name.startswith('.'):
                    continue
                if self._is_known_false_positive("module", module_dir.name):
                    continue
                py_files = list(self._iter_python_files(module_dir))
                if py_files and not (module_dir / "requirements.txt").exists():
                    violations.append(WSPViolation(
                        violation_type=WSPViolationType.DEPENDENCY,
                        description="Missing requirements.txt file",
                        affected_files=[str(module_dir.relative_to(self.project_root))],
                        severity="low",
                        wsp_protocol=12,
                        detection_time=datetime.now(),
                        auto_fixable=True,
                        fix_suggestion="Create requirements.txt with module dependencies"
                    ))
        return violations

    async def _scan_root_directory_violations(self) -> List[WSPViolation]:
        """
        Scan for WSP 3 violations in project root directory.

        Per WSP 3: Only specific entry point files should be in root.
        All other Python files should be in modules/, tests/, or scripts/.

        WSP 48: Checks pattern memory for known false positives before flagging.
        """
        violations: List[WSPViolation] = []

        # Legitimate root files (entry points and navigation)
        allowed_root_files = {
            'holo_index.py',   # CLI entry point
            'main.py',         # Main entry point
            'NAVIGATION.py',   # Module navigation map (WSP 50)
            'setup.py',        # Package setup
            '__init__.py',     # Package marker
        }

        # Scan for Python files in root
        for py_file in self.project_root.glob('*.py'):
            if py_file.name in allowed_root_files:
                continue

            # WSP 48: Check if this is a known false positive
            if self._is_known_false_positive('root_file', py_file.name):
                continue

            # Determine suggested location based on file prefix
            suggestion = "Move to tests/ or scripts/ or module-specific directory"
            if py_file.name.startswith('test_'):
                suggestion = "Move to tests/ directory"
            elif py_file.name.startswith(('check_', 'diagnose_', 'inspect_', 'troubleshoot_')):
                suggestion = "Move to scripts/ directory"
            elif py_file.name.startswith(('poc_', 'example_', 'demo_')):
                suggestion = "Move to scripts/archive/ or delete if obsolete"

            violations.append(WSPViolation(
                violation_type=WSPViolationType.ARCHITECTURE,
                description=f"Python file in root directory (should be in module/tests/scripts)",
                affected_files=[py_file.name],
                severity="medium",
                wsp_protocol=3,
                detection_time=datetime.now(),
                auto_fixable=False,
                fix_suggestion=suggestion
            ))

        return violations
