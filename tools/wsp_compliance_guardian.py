#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

WSP Compliance Guardian - Complete WSP Framework Enforcement System
Implements WSP 48 Recursive Self-Improvement with automatic compliance monitoring

This is the critical protector of WSP structural standards and the final authority
on framework compliance. Implements dual-layer protection with deterministic validation
and semantic intelligence per WSP 48, WSP 64, and WSP 22 protocols.

Core Responsibilities:
- Validate module directory structures (src/, tests/, docs/)
- Verify mandatory file existence (README.md, __init__.py, ModLog.md, ROADMAP.md)
- Enforce test file correspondence - every Python source must have test coverage
- Validate WSP documentation compliance (WSP 22, WSP 49, WSP 62, WSP 60)
- Perform deep semantic analysis to detect subtle violations
- Generate recursive improvement recommendations with actionable remediation
- Automatically update ModLog.md with all changes (WSP 22)
- Self-heal and learn from violations (WSP 48)
"""

import ast
import os
import sys
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# Configure logging with Unicode safety
# Use custom handler to avoid Unicode errors on Windows
class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            # Remove emojis for console output on Windows
            msg = msg.encode('ascii', 'ignore').decode('ascii')
            self.stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        SafeStreamHandler(sys.stdout),
        logging.FileHandler('wsp_compliance.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class ComplianceLevel(Enum):
    """WSP Compliance severity levels"""
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    CRITICAL = "CRITICAL"

class WSPStandard(Enum):
    """WSP Standards enforced by the guardian"""
    WSP_22 = "Module documentation requirements"
    WSP_49 = "Directory structure standards"
    WSP_62 = "File size compliance thresholds"
    WSP_60 = "Memory architecture validation"
    WSP_64 = "Violation prevention protocol"
    WSP_48 = "Recursive self-improvement"
    WSP_5 = "Test coverage requirements"
    WSP_34 = "Test documentation standards"

@dataclass
class Violation:
    """Represents a WSP compliance violation"""
    standard: WSPStandard
    level: ComplianceLevel
    file_path: Optional[str]
    description: str
    remediation: str
    line_number: Optional[int] = None
    context: Optional[str] = None

@dataclass
class ComplianceReport:
    """Complete compliance report for a module or system"""
    module_path: str
    timestamp: datetime
    violations: List[Violation] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    overall_status: ComplianceLevel = ComplianceLevel.PASS
    
    def add_violation(self, violation: Violation):
        """Add a violation and update overall status"""
        self.violations.append(violation)
        # Update overall status based on worst violation
        if violation.level == ComplianceLevel.CRITICAL:
            self.overall_status = ComplianceLevel.CRITICAL
        elif violation.level == ComplianceLevel.FAIL and self.overall_status != ComplianceLevel.CRITICAL:
            self.overall_status = ComplianceLevel.FAIL
        elif violation.level == ComplianceLevel.WARNING and self.overall_status == ComplianceLevel.PASS:
            self.overall_status = ComplianceLevel.WARNING

class WSPComplianceGuardian:
    """
    The WSP Compliance Guardian - Ultimate authority on framework compliance
    Implements WSP 48 recursive self-improvement with automatic violation prevention
    """
    
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.violations_memory: Dict[str, List[Violation]] = {}
        self.learning_patterns: Dict[str, int] = {}  # Track recurring violations
        self.auto_fix_enabled = True
        self.semantic_analysis_enabled = True
        
    def analyze_module(self, module_path: Path) -> ComplianceReport:
        """
        Perform comprehensive WSP compliance analysis on a module
        Implements dual-layer protection: deterministic + semantic
        """
        report = ComplianceReport(
            module_path=str(module_path),
            timestamp=datetime.now()
        )
        
        logger.info(f"[SEARCH] Analyzing module: {module_path}")
        
        # Layer 1: Deterministic validation
        self._validate_structure(module_path, report)
        self._validate_mandatory_files(module_path, report)
        self._validate_test_coverage(module_path, report)
        self._validate_documentation(module_path, report)
        
        # Layer 2: Semantic analysis (if enabled)
        if self.semantic_analysis_enabled:
            self._perform_semantic_analysis(module_path, report)
        
        # WSP 48: Learn from violations and suggest improvements
        self._learn_from_violations(report)
        self._generate_improvements(report)
        
        # Auto-fix violations if enabled
        if self.auto_fix_enabled and report.violations:
            self._attempt_auto_fix(module_path, report)
        
        return report
    
    def _validate_structure(self, module_path: Path, report: ComplianceReport):
        """Validate WSP 49 directory structure standards"""
        required_dirs = ['src', 'tests', 'docs']
        
        for dir_name in required_dirs:
            dir_path = module_path / dir_name
            if not dir_path.exists():
                violation = Violation(
                    standard=WSPStandard.WSP_49,
                    level=ComplianceLevel.FAIL,
                    file_path=str(dir_path),
                    description=f"Missing required directory: {dir_name}/",
                    remediation=f"Create directory: mkdir -p {dir_path}"
                )
                report.add_violation(violation)
                
                # WSP 48: Auto-create missing directory
                if self.auto_fix_enabled:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"[OK] Auto-created missing directory: {dir_path}")
    
    def _validate_mandatory_files(self, module_path: Path, report: ComplianceReport):
        """Validate WSP 22 mandatory file requirements"""
        mandatory_files = {
            'README.md': 'Module documentation',
            '__init__.py': 'Python package marker',
            'ModLog.md': 'Module change log (WSP 22)',
            'ROADMAP.md': 'Development roadmap (WSP 22)',
            'tests/README.md': 'Test documentation (WSP 34)',
            'tests/TestModLog.md': 'Test execution log (WSP 34)'
        }
        
        for file_name, purpose in mandatory_files.items():
            file_path = module_path / file_name
            if not file_path.exists():
                violation = Violation(
                    standard=WSPStandard.WSP_22 if 'ModLog' in file_name or 'ROADMAP' in file_name else WSPStandard.WSP_49,
                    level=ComplianceLevel.FAIL,
                    file_path=str(file_path),
                    description=f"Missing mandatory file: {file_name} ({purpose})",
                    remediation=f"Create {file_name} with appropriate content for {purpose}"
                )
                report.add_violation(violation)
                
                # WSP 48: Auto-create missing file with template
                if self.auto_fix_enabled:
                    self._create_file_from_template(file_path, file_name, module_path.name)
    
    def _validate_test_coverage(self, module_path: Path, report: ComplianceReport):
        """Validate WSP 5 test coverage requirements"""
        src_dir = module_path / 'src'
        tests_dir = module_path / 'tests'
        
        if src_dir.exists():
            python_files = list(src_dir.glob('**/*.py'))
            for src_file in python_files:
                if src_file.name == '__init__.py':
                    continue
                    
                # Expected test file
                relative_path = src_file.relative_to(src_dir)
                test_file = tests_dir / relative_path.parent / f"test_{relative_path.name}"
                
                if not test_file.exists():
                    violation = Violation(
                        standard=WSPStandard.WSP_5,
                        level=ComplianceLevel.WARNING,
                        file_path=str(src_file),
                        description=f"No corresponding test file for {src_file.name}",
                        remediation=f"Create test file: {test_file}"
                    )
                    report.add_violation(violation)
                elif self._is_unimplemented_test(test_file):
                    report.add_violation(Violation(
                        standard=WSPStandard.WSP_5, level=ComplianceLevel.WARNING,
                        file_path=str(test_file),
                        description=f"Behavioral coverage unimplemented or source invalid: {test_file.name}",
                        remediation="Implement behavioral assertions and validate the test source",
                    ))
    
    def _validate_documentation(self, module_path: Path, report: ComplianceReport):
        """Validate WSP 22 documentation compliance"""
        # Check ModLog.md for recent updates
        modlog_path = module_path / 'ModLog.md'
        if modlog_path.exists():
            content = modlog_path.read_text(encoding='utf-8', errors='ignore')
            
            # Check if ModLog has been updated recently
            if datetime.now().strftime('%Y-%m') not in content:
                violation = Violation(
                    standard=WSPStandard.WSP_22,
                    level=ComplianceLevel.WARNING,
                    file_path=str(modlog_path),
                    description="ModLog.md hasn't been updated this month",
                    remediation="Update ModLog.md with recent changes"
                )
                report.add_violation(violation)
        
        # Check Python files for docstrings
        src_dir = module_path / 'src'
        if src_dir.exists():
            for py_file in src_dir.glob('**/*.py'):
                if py_file.name == '__init__.py':
                    continue
                    
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                if not content.strip().startswith('"""'):
                    violation = Violation(
                        standard=WSPStandard.WSP_22,
                        level=ComplianceLevel.WARNING,
                        file_path=str(py_file),
                        description="Python file missing module docstring",
                        remediation="Add module-level docstring at the beginning of the file"
                    )
                    report.add_violation(violation)
    
    def _perform_semantic_analysis(self, module_path: Path, report: ComplianceReport):
        """
        Perform deep semantic analysis to detect subtle violations
        This goes beyond simple file checking to understand code patterns
        """
        logger.info(f"[AI] Performing semantic analysis on {module_path}")
        
        # Check for anti-patterns
        src_dir = module_path / 'src'
        if src_dir.exists():
            for py_file in src_dir.glob('**/*.py'):
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                
                # Check for WSP 62 file size violations
                if len(content) > 50000:  # ~1500 lines assuming 33 chars/line
                    violation = Violation(
                        standard=WSPStandard.WSP_62,
                        level=ComplianceLevel.WARNING,
                        file_path=str(py_file),
                        description=f"File exceeds recommended size ({len(content)} chars)",
                        remediation="Consider splitting into smaller, focused modules"
                    )
                    report.add_violation(violation)
                
                # Check for hardcoded paths (WSP 60 memory architecture)
                if 'C:\\\\' in content or '/home/' in content:
                    violation = Violation(
                        standard=WSPStandard.WSP_60,
                        level=ComplianceLevel.WARNING,
                        file_path=str(py_file),
                        description="Hardcoded paths detected - violates portability",
                        remediation="Use Path objects and relative paths"
                    )
                    report.add_violation(violation)
    
    def _learn_from_violations(self, report: ComplianceReport):
        """
        WSP 48: Learn from violations to prevent future occurrences
        Track patterns and increase severity for recurring violations
        """
        for violation in report.violations:
            key = f"{violation.standard.name}:{violation.description}"
            
            # Track violation frequency
            if key not in self.learning_patterns:
                self.learning_patterns[key] = 0
            self.learning_patterns[key] += 1
            
            # Escalate severity for recurring violations
            if self.learning_patterns[key] > 3:
                violation.level = ComplianceLevel.CRITICAL
                logger.warning(f"[U+26A0]️ Recurring violation escalated to CRITICAL: {key}")
    
    def _generate_improvements(self, report: ComplianceReport):
        """Generate recursive improvement recommendations"""
        if report.violations:
            # Group violations by standard
            by_standard: Dict[WSPStandard, List[Violation]] = {}
            for v in report.violations:
                if v.standard not in by_standard:
                    by_standard[v.standard] = []
                by_standard[v.standard].append(v)
            
            # Generate improvements
            for standard, violations in by_standard.items():
                if len(violations) > 2:
                    report.improvements.append(
                        f"Systemic {standard.name} violations detected. "
                        f"Consider implementing automated {standard.value} checking in CI/CD pipeline."
                    )
            
            # WSP 48 recursive improvement
            if self.learning_patterns:
                top_violations = sorted(self.learning_patterns.items(), 
                                      key=lambda x: x[1], reverse=True)[:3]
                for pattern, count in top_violations:
                    report.improvements.append(
                        f"Recurring pattern ({count} times): {pattern}. "
                        f"Implement preventive measures in development workflow."
                    )
    
    def _attempt_auto_fix(self, module_path: Path, report: ComplianceReport):
        """
        WSP 48: Attempt to automatically fix violations
        This implements the self-healing capability
        """
        logger.info(f"[TOOL] Attempting auto-fix for {len(report.violations)} violations")
        
        fixed_count = 0
        for violation in report.violations:
            if violation.level in [ComplianceLevel.WARNING, ComplianceLevel.FAIL]:
                if self._auto_fix_violation(module_path, violation):
                    fixed_count += 1
                    logger.info(f"[OK] Auto-fixed: {violation.description}")
        
        if fixed_count > 0:
            # Update ModLog with auto-fixes
            self._update_modlog(module_path, report, fixed_count)
    
    def _auto_fix_violation(self, module_path: Path, violation: Violation) -> bool:
        """Attempt to automatically fix a specific violation"""
        try:
            if violation.standard == WSPStandard.WSP_49:
                # Create missing directories
                if 'Missing required directory' in violation.description:
                    Path(violation.file_path).mkdir(parents=True, exist_ok=True)
                    return True
            
            elif violation.standard == WSPStandard.WSP_22:
                # Create missing documentation files
                if 'Missing mandatory file' in violation.description:
                    file_path = Path(violation.file_path)
                    file_name = file_path.name
                    self._create_file_from_template(file_path, file_name, module_path.name)
                    return True
            
            elif violation.standard == WSPStandard.WSP_5:
                # Create test file skeleton
                if 'No corresponding test file' in violation.description:
                    test_path = Path(violation.remediation.split(': ')[1])
                    self._create_test_skeleton(test_path, violation.file_path)
                    logger.warning("Scaffold created; behavioral coverage remains missing")
                    return False
                    
        except Exception as e:
            logger.error(f"Auto-fix failed: {e}")
        
        return False
    
    def _create_file_from_template(self, file_path: Path, file_name: str, module_name: str):
        """Create a file from WSP-compliant template"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        templates = {
            'README.md': f"""# {module_name} Module

## Overview
This module implements {module_name} functionality for the Foundups-Agent system.

## WSP Compliance
- WSP 22: Module documentation maintained
- WSP 49: Proper directory structure
- WSP 5: Test coverage requirements

## Installation
```bash
pip install -r requirements.txt
```

## Usage
```python
from {module_name} import main_function
```

## Development Status
See ROADMAP.md for development phases and ModLog.md for change history.
""",
            'ModLog.md': f"""# {module_name} Module - ModLog

## WSP 22 ModLog Protocol
- **Purpose**: Track module-specific changes per WSP 22
- **Format**: Reverse chronological order (newest first)
- **Scope**: Module-specific features, fixes, and WSP compliance

---

## MODLOG ENTRIES

### [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] - Initial Creation
**WSP Protocol**: WSP 22 (Module ModLog Protocol)
**Phase**: Foundation Setup
**Agent**: ComplianceGuardian (WSP 48)

#### Changes
- [OK] Module structure created per WSP 49
- [OK] ModLog.md initialized per WSP 22
- [OK] Compliance validation completed

---

*This ModLog maintains comprehensive module history per WSP 22 protocol*
""",
            'ROADMAP.md': f"""# {module_name} Module - Development Roadmap

## WSP 22 Roadmap Protocol
Per WSP 22, this roadmap defines the development phases for the {module_name} module.

## Development Phases

### Phase 1: POC (Proof of Concept) - v0.x.x
**Status**: [U+1F6A7] In Progress
**Target**: Basic functionality demonstration

#### Objectives
- [ ] Core functionality implementation
- [ ] Basic test coverage (>60%)
- [ ] Initial documentation

### Phase 2: Prototype - v1.x.x
**Status**: [CLIPBOARD] Planned
**Target**: Enhanced integration

#### Objectives
- [ ] Full feature implementation
- [ ] Test coverage >85%
- [ ] WSP compliance validation

### Phase 3: MVP (Minimum Viable Product) - v2.x.x
**Status**: [U+1F52E] Future
**Target**: Production-ready

#### Objectives
- [ ] Complete feature set
- [ ] Test coverage >90%
- [ ] Full WSP compliance

---

*Roadmap maintained per WSP 22 protocol*
""",
            '__init__.py': f'"""\n{module_name} module initialization\nWSP compliant module structure\n"""\n\n__version__ = "0.0.1"\n',
            'TestModLog.md': f"""# {module_name} Test Execution Log

## WSP 34 Test Documentation Protocol
This log tracks test execution results for the {module_name} module.

---

## Test Execution History

### [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] - Initial Test Setup
**Test Coverage**: 0% (No tests yet)
**Status**: ⏳ Pending implementation

---

*Test log maintained per WSP 34 protocol*
"""
        }
        
        # Handle special cases
        if file_name == 'tests/README.md':
            file_name = 'TestModLog.md'
        elif file_name == 'tests/TestModLog.md':
            file_name = 'TestModLog.md'
        
        template = templates.get(file_name, f"# {file_name}\n\nWSP compliant file created by ComplianceGuardian\n")
        file_path.write_text(template, encoding='utf-8')
        logger.info(f"[OK] Created {file_path} from template")
    
    def _scaffold_paths(self, test_path: Path, source_path: str):
        """Resolve in-project paths before creating any scaffold artifact."""
        root = self.project_root.resolve()
        source = Path(source_path)
        target = Path(test_path)
        source = (source if source.is_absolute() else root / source).resolve()
        target = (target if target.is_absolute() else root / target).resolve()
        relative = source.relative_to(root)
        target.relative_to(root)
        if not source.is_file() or source.suffix != '.py':
            raise ValueError("Scaffold source must be an existing project Python file")
        parts = relative.with_suffix('').parts
        if any(not part.replace('_', '').isalnum() for part in parts):
            raise ValueError("Scaffold source has an unsupported module path")
        if target.suffix != '.py' or not target.name.startswith('test_'):
            raise ValueError("Scaffold destination must be a project test_*.py file")
        return target, '.'.join(parts), source.stem

    def _create_test_skeleton(self, test_path: Path, source_path: str):
        """Create an explicitly unimplemented scaffold, never coverage proof."""
        target, source_module, source_name = self._scaffold_paths(test_path, source_path)
        class_name = 'Test' + source_name.title().replace('_', '')
        test_content = f'''"""Test scaffold for {source_name}; SPECIFIED_NOT_IMPLEMENTED.

No behavioral coverage exists yet. Production code is not imported during
collection. Replace the placeholders with behavioral assertions before removing
the scaffold marker and skip. SOURCE_MODULE is the intended future test subject.
"""
import pytest

WRE_TEST_MODE = "scaffold"
SOURCE_MODULE = {source_module!r}
pytestmark = pytest.mark.skip(reason="SPECIFIED_NOT_IMPLEMENTED: test scaffold")


class {class_name}:
    """Pending behavioral tests for {source_name}."""

    def test_initialization(self):
        """TODO: verify initialization behavior."""
        pytest.fail("Replace scaffold with behavioral assertions")

    def test_basic_functionality(self):
        """TODO: verify core behavior."""
        pytest.fail("Replace scaffold with behavioral assertions")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
'''
        ast.parse(test_content, filename=str(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('x', encoding='utf-8', newline='\n') as handle:
            handle.write(test_content)
        logger.info("Created unimplemented test scaffold: %s", target)

    @staticmethod
    def _is_unimplemented_test(test_path: Path) -> bool:
        """Keep invalid or declared scaffold source visible as missing coverage."""
        try:
            tree = ast.parse(test_path.read_bytes(), filename=str(test_path))
        except (OSError, SyntaxError, UnicodeError):
            return True
        return any(
            isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
            and node.value.value == 'scaffold'
            and any(isinstance(target, ast.Name) and target.id == 'WRE_TEST_MODE'
                    for target in node.targets)
            for node in tree.body
        )

    def _update_modlog(self, module_path: Path, report: ComplianceReport, fixed_count: int):
        """Update ModLog.md with compliance actions"""
        modlog_path = module_path / 'ModLog.md'
        
        if not modlog_path.exists():
            self._create_file_from_template(modlog_path, 'ModLog.md', module_path.name)
        
        # Read existing content with error handling
        try:
            content = modlog_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                content = modlog_path.read_text(encoding='utf-8-sig')
            except:
                # Fall back to creating new file
                self._create_file_from_template(modlog_path, 'ModLog.md', module_path.name)
                content = modlog_path.read_text(encoding='utf-8')
        
        # Find the insertion point (after "## MODLOG ENTRIES")
        lines = content.split('\n')
        insert_index = -1
        for i, line in enumerate(lines):
            if '## MODLOG ENTRIES' in line:
                insert_index = i + 2  # Skip the blank line
                break
        
        if insert_index == -1:
            # If no MODLOG ENTRIES section, add at end
            insert_index = len(lines)
        
        # Create new entry
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_entry = f"""
### [{timestamp}] - WSP Compliance Auto-Fix
**WSP Protocol**: WSP 48 (Recursive Self-Improvement)
**Phase**: Compliance Enforcement
**Agent**: ComplianceGuardian

#### Changes
- [OK] Auto-fixed {fixed_count} compliance violations
- [OK] Violations analyzed: {len(report.violations)}
- [OK] Overall status: {report.overall_status.value}

#### Violations Fixed
"""
        
        for violation in report.violations[:5]:  # Show first 5
            new_entry += f"- {violation.standard.name}: {violation.description}\n"
        
        if len(report.violations) > 5:
            new_entry += f"- ... and {len(report.violations) - 5} more\n"
        
        new_entry += "\n---\n"
        
        # Insert the new entry
        lines.insert(insert_index, new_entry)
        
        # Write back
        modlog_path.write_text('\n'.join(lines), encoding='utf-8')
        logger.info(f"[OK] Updated ModLog.md with compliance actions")
    
    def generate_compliance_report(self, output_path: Optional[Path] = None) -> str:
        """Generate comprehensive compliance report for the entire project"""
        logger.info("[ROCKET] Starting comprehensive WSP compliance analysis")
        
        all_reports = []
        modules_dir = self.project_root / 'modules'
        
        # Analyze each module
        for domain_dir in modules_dir.iterdir():
            if domain_dir.is_dir() and not domain_dir.name.startswith('.'):
                for module_dir in domain_dir.iterdir():
                    if module_dir.is_dir() and not module_dir.name.startswith('.'):
                        report = self.analyze_module(module_dir)
                        all_reports.append(report)
        
        # Generate summary report
        summary = self._generate_summary_report(all_reports)
        
        # Save report if path provided
        if output_path:
            output_path.write_text(summary, encoding='utf-8')
            logger.info(f"[U+1F4C4] Report saved to: {output_path}")
        
        return summary
    
    def _generate_summary_report(self, reports: List[ComplianceReport]) -> str:
        """Generate a summary report from all module reports"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        total_violations = sum(len(r.violations) for r in reports)
        critical_count = sum(1 for r in reports for v in r.violations if v.level == ComplianceLevel.CRITICAL)
        fail_count = sum(1 for r in reports for v in r.violations if v.level == ComplianceLevel.FAIL)
        warning_count = sum(1 for r in reports for v in r.violations if v.level == ComplianceLevel.WARNING)
        
        summary = f"""# WSP Compliance Report
Generated: {timestamp}
Guardian: WSP Compliance Guardian v1.0

## Executive Summary
- **Modules Analyzed**: {len(reports)}
- **Total Violations**: {total_violations}
- **Critical**: {critical_count}
- **Failures**: {fail_count}
- **Warnings**: {warning_count}

## Compliance Status by WSP Standard
"""
        
        # Count violations by standard
        by_standard: Dict[WSPStandard, int] = {}
        for report in reports:
            for violation in report.violations:
                if violation.standard not in by_standard:
                    by_standard[violation.standard] = 0
                by_standard[violation.standard] += 1
        
        for standard, count in sorted(by_standard.items(), key=lambda x: x[1], reverse=True):
            status = "[FAIL]" if count > 10 else "[U+26A0]️" if count > 5 else "[OK]"
            summary += f"- {status} **{standard.name}**: {count} violations - {standard.value}\n"
        
        summary += "\n## Module Details\n\n"
        
        # Add details for each module
        for report in sorted(reports, key=lambda r: len(r.violations), reverse=True)[:10]:
            if report.violations:
                status_icon = "[FAIL]" if report.overall_status == ComplianceLevel.CRITICAL else "[U+26A0]️"
                summary += f"### {status_icon} {report.module_path}\n"
                summary += f"- **Status**: {report.overall_status.value}\n"
                summary += f"- **Violations**: {len(report.violations)}\n"
                
                # Show top violations
                for v in report.violations[:3]:
                    summary += f"  - {v.standard.name}: {v.description}\n"
                
                if len(report.violations) > 3:
                    summary += f"  - ... and {len(report.violations) - 3} more\n"
                
                summary += "\n"
        
        # Add improvement recommendations
        summary += "## Recursive Improvement Recommendations\n\n"
        
        all_improvements = []
        for report in reports:
            all_improvements.extend(report.improvements)
        
        # Deduplicate and show top improvements
        unique_improvements = list(set(all_improvements))
        for improvement in unique_improvements[:10]:
            summary += f"- {improvement}\n"
        
        # Add learning patterns
        if self.learning_patterns:
            summary += "\n## Learning Patterns (WSP 48)\n\n"
            summary += "Recurring violations that need systemic fixes:\n\n"
            
            for pattern, count in sorted(self.learning_patterns.items(), 
                                        key=lambda x: x[1], reverse=True)[:5]:
                summary += f"- **{count} occurrences**: {pattern}\n"
        
        summary += f"""
## Emergency Escalation
Critical violations requiring immediate attention: {critical_count}

## WSP Guardian Commitment
The WSP Compliance Guardian will continue monitoring and enforcing framework integrity.
All violations have been logged and will be tracked for recursive improvement per WSP 48.

---
*Report generated by WSP Compliance Guardian - The ultimate authority on WSP framework compliance*
"""
        
        return summary


def main():
    """Main entry point for WSP Compliance Guardian"""
    project_root = Path(__file__).parent.parent
    
    # Initialize the guardian
    guardian = WSPComplianceGuardian(project_root)
    
    # Generate comprehensive report
    report_path = project_root / 'WSP_COMPLIANCE_REPORT.md'
    report = guardian.generate_compliance_report(report_path)
    
    print(report)
    print(f"\n[OK] Full report saved to: {report_path}")
    
    # Show learning patterns
    if guardian.learning_patterns:
        print("\n[AI] Learning Patterns Detected:")
        for pattern, count in sorted(guardian.learning_patterns.items(), 
                                    key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {count}x: {pattern}")


if __name__ == "__main__":
    main()