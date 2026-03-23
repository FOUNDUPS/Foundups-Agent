#!/usr/bin/env python3
"""
HoloDAE Gemma Root Violation Monitor
Following WSP 80 (Cube-Level DAE Orchestration) + WSP 93 (CodeIndex Surgical Intelligence)

MONITORING ARCHITECTURE:
- Qwen = Oversees monitoring coordination
- Gemma = Specialized root violation detection
- HoloIndex = Violation reporting integration

PURPOSE: Automatically detect root directory violations and alert 0102 during HoloIndex usage
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Set, Any
import asyncio
from datetime import datetime

class GemmaRootViolationMonitor:
    """Gemma-specialized root directory violation monitoring"""

    def __init__(self, repo_root: Path = None):
        # WSP 50: never assume current working directory.
        # Resolve repo root deterministically from this module's location.
        default_repo_root = Path(__file__).resolve().parents[4]
        self.root_path = (repo_root or default_repo_root).resolve()

        # WSP 60: persist under module-local memory (not repo root).
        module_root = Path(__file__).resolve().parents[1]  # .../root_violation_monitor/src
        self.violation_log = (module_root / "memory" / "root_violations.json").resolve()
        self.allowed_root_files = self._get_allowed_root_files()

        # Telemetry integration (WSP 91: Observability)
        try:
            from holo_index.qwen_advisor.output_formatter import TelemetryLogger
            self.telemetry_logger = TelemetryLogger(session_id=f"root-monitor-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        except ImportError:
            self.telemetry_logger = None  # Graceful degradation

        # Gemma specialization: Pattern recognition for violations
        self.violation_patterns = {
            'script_files': ['.py', '.sh', '.bat', '.ps1'],
            'temp_files': ['temp_', 'tmp_', '.tmp'],
            'log_files': ['.log'],
            'wsp_violations': ['WSP_', 'wsp_'],  # WSP prefix violations
            'debug_files': ['debug_', 'test_']
        }

        # Performance tracking
        self.monitoring_stats = {
            'scans_performed': 0,
            'violations_detected': 0,
            'false_positives': 0,
            'auto_corrections': 0
        }

    def _get_allowed_root_files(self) -> Set[str]:
        """Define allowed files in root directory per WSP standards"""
        return {
            '.coveragerc',         # Coverage configuration
            '.coverage',           # Coverage reports
            '.env',                # Environment variables
            '.env.example',        # Environment template
            '.firebaserc',         # Firebase CLI configuration
            '.gitignore',          # Git ignore rules
            '.mcp.json',           # MCP configuration
            'CLAUDE.md',           # Agent instructions
            'CONTRIBUTING.md',     # Repository contribution guide
            'Dockerfile',          # Container definition
            'LICENSE',             # License file
            'ModLog.md',           # Repository changelog
            'NAVIGATION.py',       # Navigation map / index
            'README.md',           # Project documentation
            'ROADMAP.md',          # Development roadmap
            'firebase.json',       # Firebase project configuration
            'firestore.indexes.json',  # Firestore index configuration
            'firestore.rules',     # Firestore rules
            'holo_index.py',       # HoloIndex launcher
            'main.py',             # Primary launcher
            'package-lock.json',   # Node lockfile
            'package.json',        # Node.js dependencies
            'pnpm-lock.yaml',      # pnpm lockfile
            'pyrightconfig.json',  # Type-checker configuration
            'pytest.ini',          # Test configuration
            'requirements.txt',    # Package dependencies
            'vercel.json',         # Deployment configuration
        }

    async def scan_root_violations(self) -> Dict[str, Any]:
        """Gemma-specialized root directory violation scanning"""

        violations = []
        root_files = set()

        try:
            # Get all files in root directory
            for item in os.listdir(self.root_path):
                item_path = self.root_path / item
                if item_path.is_file():
                    root_files.add(item)

            # Check for violations using Gemma pattern recognition
            for filename in root_files:
                violation_type = self._classify_violation_gemma(filename)
                if violation_type:
                    violations.append({
                        'filename': filename,
                        'violation_type': violation_type,
                        'severity': self._assess_severity(violation_type),
                        'auto_correctable': self._is_auto_correctable(filename, violation_type),
                        'detected_at': time.time(),
                        'recommended_action': self._get_recommended_action(filename, violation_type)
                    })

        except Exception as e:
            violations.append({
                'filename': 'SCAN_ERROR',
                'violation_type': 'scan_failure',
                'severity': 'critical',
                'error': str(e),
                'detected_at': time.time()
            })

        # Update monitoring stats
        self.monitoring_stats['scans_performed'] += 1
        self.monitoring_stats['violations_detected'] += len(violations)

        # Emit telemetry for AI Overseer (WSP 91: Observability)
        if violations and self.telemetry_logger:
            self.telemetry_logger.log_event(
                'system_alerts',
                source='gemma_root_monitor',
                alerts=[
                    f"{v['filename']}: {v['violation_type']} (severity: {v['severity']})"
                    for v in violations[:5]  # Limit to top 5 for brevity
                ],
                violation_count=len(violations),
                root_file_count=len(root_files)
            )

        scan_result = {
            'timestamp': time.time(),
            'total_root_files': len(root_files),
            'violations_found': len(violations),
            'violations': violations,
            'allowed_files_present': len(root_files & self.allowed_root_files),
            'monitoring_stats': self.monitoring_stats.copy()
        }

        # Save violation log
        await self._save_violation_log(scan_result)

        return scan_result

    def _classify_violation_gemma(self, filename: str) -> str:
        """Gemma pattern recognition for violation classification"""

        # Allowlist is authoritative (WSP 50: never assume; do not flag core entrypoints/docs).
        if filename in self.allowed_root_files:
            return None

        # Check WSP naming violations (highest priority)
        if any(filename.startswith(prefix) for prefix in self.violation_patterns['wsp_violations']):
            return 'wsp_naming_violation'

        # Check script files in root
        if any(filename.endswith(ext) for ext in self.violation_patterns['script_files']):
            return 'script_in_root'

        # Check temp files
        if any(temp in filename.lower() for temp in self.violation_patterns['temp_files']):
            return 'temp_file_in_root'

        # Check log files
        if any(filename.endswith(ext) for ext in self.violation_patterns['log_files']):
            return 'log_file_in_root'

        # Check debug/test files
        if any(prefix in filename.lower() for prefix in self.violation_patterns['debug_files']):
            return 'debug_file_in_root'

        # Default: unauthorized file in root
        return 'unauthorized_file'


    def _assess_severity(self, violation_type: str) -> str:
        """Assess violation severity using pattern recognition"""

        severity_map = {
            'wsp_naming_violation': 'critical',      # WSP 57 violation
            'script_in_root': 'high',                # WSP 49 violation
            'unauthorized_file': 'medium',           # WSP 3 violation
            'temp_file_in_root': 'low',              # Cleanup needed
            'log_file_in_root': 'low',               # Organization issue
            'debug_file_in_root': 'medium',          # Development cleanup
            'scan_failure': 'critical'               # System issue
        }

        return severity_map.get(violation_type, 'unknown')

    def _is_auto_correctable(self, filename: str, violation_type: str) -> bool:
        """Determine if violation can be auto-corrected"""

        # Scripts can be moved to modules
        if violation_type == 'script_in_root':
            return filename.endswith('.py')

        # Temp files can be moved to temp/
        if violation_type == 'temp_file_in_root':
            return True

        # Log files can be moved to logs/
        if violation_type == 'log_file_in_root':
            return True

        return False

    def _get_recommended_action(self, filename: str, violation_type: str) -> str:
        """Get recommended action for violation"""

        if violation_type == 'unauthorized_file':
            suffix = Path(filename).suffix.lower()
            if suffix == '.md':
                return f"Move {filename} to docs/ or a module docs/ directory"
            if suffix == '.json':
                return f"Move {filename} to data/ or a module data/ directory unless it is repo-level config"
            if suffix in {'.txt', '.out'}:
                return f"Move {filename} to temp/ or logs/ and gitignore it if it is only a run artifact"
            if suffix in {'.png', '.jpg', '.jpeg', '.gif', '.svg'}:
                return f"Move {filename} to docs/assets/ or a module docs/assets/ directory"

        actions = {
            'wsp_naming_violation': f'Move {filename} to docs/ directory (WSP 57 compliance)',
            'script_in_root': f'Move {filename} to appropriate module in modules/ (WSP 49)',
            'temp_file_in_root': f'Move {filename} to temp/ directory',
            'log_file_in_root': f'Move {filename} to logs/ directory',
            'debug_file_in_root': f'Move {filename} to tools/ or tests/ directory',
            'unauthorized_file': f'Review and move {filename} to appropriate location or add to allowed list'
        }

        return actions.get(violation_type, f'Manual review required for {filename}')

    async def _save_violation_log(self, scan_result: Dict[str, Any]):
        """Save violation log for historical tracking"""

        try:
            self.violation_log.parent.mkdir(parents=True, exist_ok=True)

            # Load existing log if it exists
            existing_log = []
            if self.violation_log.exists():
                with open(self.violation_log, 'r') as f:
                    existing_log = json.load(f)

            # Add new scan result
            existing_log.append(scan_result)

            # Keep only last 100 scans
            if len(existing_log) > 100:
                existing_log = existing_log[-100:]

            # Save updated log
            with open(self.violation_log, 'w') as f:
                json.dump(existing_log, f, indent=2, default=str)

        except Exception as e:
            print(f"[WARNING] Failed to save violation log: {e}")

    async def generate_violation_alert(self) -> str:
        """Generate violation alert for HoloIndex display"""

        scan_result = await self.scan_root_violations()

        if not scan_result['violations']:
            return ""  # No violations

        # Format alert for HoloIndex display
        alert_lines = [
            "[ALERT] WSP ROOT VIOLATION - NEEDS IMMEDIATE ATTENTION 0102! [ALERT]",
            f"[DATA] Scan Results: {scan_result['total_root_files']} files, {scan_result['violations_found']} violations",
            ""
        ]

        # Group violations by severity
        critical = [v for v in scan_result['violations'] if v['severity'] == 'critical']
        high = [v for v in scan_result['violations'] if v['severity'] == 'high']
        medium = [v for v in scan_result['violations'] if v['severity'] == 'medium']
        low = [v for v in scan_result['violations'] if v['severity'] == 'low']

        total_violations = len(scan_result['violations'])

        severity_buckets = {
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
        }

        summary_parts = []
        for name, bucket in severity_buckets.items():
            if bucket:
                summary_parts.append(f"{name}:{len(bucket)}")

        if summary_parts:
            alert_lines.append(f"[SUMMARY] Severity counts -> {', '.join(summary_parts)}")
            alert_lines.append("")

        max_per_bucket = 3
        total_displayed = 0

        for label, bucket, heading in [
            ("[U+1F534] CRITICAL", critical, "PRIORITY VIOLATIONS"),
            ("🟠 HIGH", high, "PRIORITY VIOLATIONS"),
            ("🟡 MEDIUM", medium, "PRIORITY VIOLATIONS"),
        ]:
            if not bucket:
                continue

            limited = bucket[:max_per_bucket]
            total_displayed += len(limited)

            if len(bucket) > max_per_bucket:
                alert_lines.append(f"{label} {heading}: {len(bucket)} total (showing {len(limited)})")
            else:
                alert_lines.append(f"{label} {heading}:")

            for v in limited:
                alert_lines.append(f"   • {v['filename']} - {v['violation_type']}")
                alert_lines.append(f"     +- {v['recommended_action']}")
            alert_lines.append("")

        remaining = total_violations - total_displayed
        if remaining > 0:
            alert_lines.append(f"[INFO] {remaining} additional violations not displayed.")

        alert_lines.append("[TIP] Run `python holo_index.py --fix-violations` to review and auto-correct the full list.")

        return "\n".join(alert_lines)

    async def auto_correct_violations(self) -> Dict[str, Any]:
        """Auto-correct correctable violations"""

        scan_result = await self.scan_root_violations()
        corrections_applied = []
        failed_corrections = []

        for violation in scan_result['violations']:
            if violation.get('auto_correctable', False):
                success = await self._apply_auto_correction(violation)
                if success:
                    corrections_applied.append(violation['filename'])
                    self.monitoring_stats['auto_corrections'] += 1
                else:
                    failed_corrections.append(violation['filename'])

        return {
            'corrections_applied': corrections_applied,
            'failed_corrections': failed_corrections,
            'total_processed': len(corrections_applied) + len(failed_corrections)
        }

    async def _apply_auto_correction(self, violation: Dict[str, Any]) -> bool:
        """Apply automatic correction for violation using Qwen coordination"""

        filename = violation['filename']
        violation_type = violation['violation_type']

        try:
            src_path = self.root_path / filename

            if violation_type == 'script_in_root':
                # Prefer deterministic placement for known root script patterns (fast, safe).
                target_location = self._determine_target_location_qwen(filename, analysis={})
                if target_location:
                    return self._move_with_git_or_rename(src_path, self.root_path / target_location)

                # Fall back to Qwen autonomous refactoring for ambiguous Python cases.
                if filename.endswith('.py'):
                    return await self._apply_qwen_refactoring(src_path, filename)
                return False

            elif violation_type == 'debug_file_in_root' and filename.startswith('test_'):
                # Use Qwen for test file placement
                return await self._apply_qwen_refactoring(src_path, filename)

            elif violation_type == 'temp_file_in_root':
                # Move temp files to temp directory
                dest_path = self.root_path / 'temp' / filename
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                src_path.rename(dest_path)
                return True

            elif violation_type == 'log_file_in_root':
                # Move log files to logs directory
                dest_path = self.root_path / 'logs' / filename
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                if dest_path.exists():
                    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    dest_path = dest_path.with_name(f"{dest_path.stem}-{stamp}{dest_path.suffix}")
                src_path.rename(dest_path)
                return True

        except Exception as e:
            print(f"[ERROR] Auto-correction failed for {filename}: {e}")
            return False

        return False

    def _move_with_git_or_rename(self, src_path: Path, dest_path: Path) -> bool:
        """
        Move a single file, preferring `git mv` when available.
        Falls back to filesystem rename for untracked artifacts.
        """
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Try git mv first (keeps history for tracked files)
            git_dir = self.root_path / ".git"
            if git_dir.exists():
                try:
                    import subprocess
                    result = subprocess.run(
                        ["git", "mv", str(src_path), str(dest_path)],
                        cwd=self.root_path,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )
                    if result.returncode == 0:
                        return True
                except Exception:
                    pass

            # Fall back to filesystem move (works for logs/temp/untracked)
            src_path.rename(dest_path)
            return True
        except Exception as e:
            print(f"[ERROR] Move failed for {src_path.name}: {e}")
            return False

    async def _apply_qwen_refactoring(self, src_path: Path, filename: str) -> bool:
        """Use Qwen autonomous refactoring to intelligently place file"""

        try:
            # Import Qwen orchestrator
            from holo_index.qwen_advisor.orchestration.autonomous_refactoring import AutonomousRefactoringOrchestrator

            # Initialize orchestrator
            orchestrator = AutonomousRefactoringOrchestrator(self.root_path)

            # Phase 1: Gemma analyzes file dependencies
            print(f"[QWEN] Analyzing {filename} dependencies...")
            analysis = orchestrator.analyze_module_dependencies(str(src_path))

            # Phase 2: Qwen determines target location based on imports
            target_location = self._determine_target_location_qwen(filename, analysis)

            if not target_location:
                print(f"[QWEN] Could not determine target location for {filename}")
                return False

            print(f"[QWEN] Moving {filename} -> {target_location}")

            # Phase 3: Execute *single-file* relocation plan (safe; avoids bulk directory moves)
            plan = orchestrator.generate_file_relocation_plan(
                source_file=str(src_path),
                target_file=target_location,
                analysis=analysis
            )

            results = orchestrator.execute_with_supervision(plan, auto_approve=True)

            # Phase 4: Learning - store pattern
            orchestrator.store_refactoring_pattern(
                module_path=str(src_path),
                target_location=target_location,
                plan=plan,
                results=results
            )

            return results.get('success', False)

        except Exception as e:
            print(f"[ERROR] Qwen refactoring failed for {filename}: {e}")
            return False

    def _determine_target_location_qwen(self, filename: str, analysis: Dict[str, Any]) -> str:
        """
        Determine a WSP-compliant target path (relative to repo root).

        NOTE: Despite the name, this function is intentionally allowed to use
        deterministic rules for high-frequency cases (fast, safe), and only rely
        on deeper analysis for ambiguous files.
        """

        lower = filename.lower()
        script_suffixes = (".py", ".sh", ".bat", ".ps1")

        if lower.startswith(("check_", "approve_", "get_")) and lower.endswith(script_suffixes):
            if "party" in lower:
                return f"modules/communication/livechat/tests/system_tests/{filename}"
            return f"scripts/verification/{filename}"

        if lower.startswith(("diagnose_", "debug_")) and lower.endswith(script_suffixes):
            return f"scripts/diagnostics/{filename}"

        if lower.startswith("launch_") and lower.endswith(script_suffixes):
            return f"scripts/launch/{filename}"

        if lower.startswith(("fix_", "batch_", "execute_", "demo_", "close_", "backup_")) and lower.endswith(script_suffixes):
            return f"scripts/{filename}"

        # Common root verification scripts → scripts/verification/
        if lower.startswith("verify_") and lower.endswith(".py"):
            if "party" in lower:
                return f"modules/communication/livechat/tests/system_tests/{filename}"
            return f"scripts/verification/{filename}"

        # Diagnostics / reproductions → scripts/diagnostics/
        if lower.startswith("diagnostic") and lower.endswith(".py"):
            return f"scripts/diagnostics/{filename}"
        if ("reproduce" in lower or "crash" in lower) and lower.endswith(".py"):
            return f"scripts/diagnostics/{filename}"

        # Environment probes → scripts/verification/
        if lower.startswith("env_") and lower.endswith(".py"):
            return f"scripts/verification/{filename}"

        # Test files go to module test directories
        if filename.startswith('test_'):
            # Analyze imports to determine which module this test belongs to
            import_refs = analysis.get('import_references', [])

            # Check for module imports in the file content
            try:
                with open(self.root_path / filename, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Pattern matching for module imports
                if 'holo_index' in content:
                    return 'holo_index/tests/' + filename
                elif 'youtube_shorts' in content or 'veo3' in content.lower():
                    return 'modules/communication/youtube_shorts/tests/' + filename
                elif 'linkedin' in content.lower():
                    return 'modules/platform_integration/linkedin_agent/tests/' + filename
                elif 'twitter' in content.lower() or 'x_twitter' in content:
                    return 'modules/platform_integration/x_twitter/tests/' + filename
                elif 'social_media_orchestrator' in content:
                    return 'modules/platform_integration/social_media_orchestrator/tests/' + filename

            except Exception as e:
                print(f"[QWEN] Could not analyze file content: {e}")

            # Default: holo_index tests
            return 'holo_index/tests/' + filename

        # Non-test scripts: analyze by functionality
        return None  # Qwen will need more sophisticated analysis for non-test files

# Integration point for HoloIndex
async def get_root_violation_alert() -> str:
    """Get root violation alert for HoloIndex display"""
    monitor = GemmaRootViolationMonitor()
    return await monitor.generate_violation_alert()

async def scan_and_correct_violations() -> Dict[str, Any]:
    """Scan for violations and apply auto-corrections"""
    monitor = GemmaRootViolationMonitor()
    corrections = await monitor.auto_correct_violations()
    return corrections

# Export for HoloIndex integration
__all__ = ['GemmaRootViolationMonitor', 'get_root_violation_alert', 'scan_and_correct_violations']
