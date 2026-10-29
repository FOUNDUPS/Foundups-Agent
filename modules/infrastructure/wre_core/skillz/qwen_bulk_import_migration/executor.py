#!/usr/bin/env python3
"""
Qwen Bulk Import Migration Skill Executor

Deterministic prototype for hardcoded-value registry-import migrations.
WSP Compliance: WSP 77 (Agent Coordination), WSP 50 (Pre-Action), WSP 84 (Code Reuse)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class MigrationChange:
    """Single change to be applied"""
    file: str
    line: int
    old: str
    new: str
    change_type: str = "replacement"  # replacement, import_add


@dataclass
class MigrationSpec:
    """Migration specification"""
    migration_type: str
    search_patterns: List[str]
    registry_module: str
    registry_imports: List[str]
    replacement_map: Dict[str, str]
    target_glob: str = "modules/**/*.py"
    exclude_patterns: List[str] = field(default_factory=list)
    dry_run: bool = True


@dataclass
class MigrationResult:
    """Result of migration execution"""
    files_scanned: int = 0
    files_modified: int = 0
    replacements_made: int = 0
    validation_passed: bool = True
    changes: List[MigrationChange] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# Built-in presets
PRESETS: Dict[str, MigrationSpec] = {
    "linkedin_registry": MigrationSpec(
        migration_type="registry_import",
        search_patterns=[
            "1263645", "68706058", "104834798", "35532191", "2199715",
            "96096638", "64659868", "76734687", "33433199", "377243"
        ],
        registry_module="modules.infrastructure.shared_utilities.linkedin_account_registry",
        registry_imports=["get_company_id", "get_default_company", "get_article_url", "get_admin_url"],
        replacement_map={
            "1263645": "get_company_id('foundups')",
            "68706058": "get_company_id('undaodu')",
            "104834798": "get_company_id('move2japan')",
            "35532191": "get_company_id('autonomouswall')",
            "2199715": "get_company_id('esingularity')",
            "96096638": "get_company_id('aiharmonic')",
            "64659868": "get_company_id('foundups100x100')",
            "76734687": "get_company_id('bitcloutfork')",
            "33433199": "get_company_id('decentralizedcrypto')",
            "377243": "get_company_id('eduit')",
        },
        target_glob="modules/**/*.py",
        exclude_patterns=[
            ".worktrees/", "__pycache__/", "linkedin_account_registry.py",
            "test_", ".git/", "node_modules/", "executor.py",
            "youtube_channel_registry.py", "qwen_bulk_import_migration/"
        ],
        dry_run=True
    ),
    "youtube_registry": MigrationSpec(
        migration_type="registry_import",
        search_patterns=[],  # To be populated
        registry_module="modules.infrastructure.shared_utilities.youtube_channel_registry",
        registry_imports=["get_channel_ids", "get_channels"],
        replacement_map={},
        target_glob="modules/**/*.py",
        exclude_patterns=[".worktrees/", "__pycache__/", "youtube_channel_registry.py"],
        dry_run=True
    ),
}


class BulkImportMigrator:
    """
    Rule-based migration prototype; no Qwen or Gemma inference is invoked.

    Phase 1: Identify files and plan configured literal replacements
    Phase 2: Apply a limited balanced-parentheses rule check
    Phase 3: Apply changes (if not dry_run)
    """

    def __init__(self, repo_root: Optional[Path] = None):
        # Path: executor.py -> qwen_bulk_import_migration -> skillz -> wre_core -> infrastructure -> modules -> repo_root
        self.repo_root = repo_root or Path(__file__).parent.parent.parent.parent.parent.parent
        self.llm_available = self._check_llm_availability()

    def _check_llm_availability(self) -> bool:
        """Check if local LLM (Qwen/Gemma) is available"""
        try:
            # Check for llama_cpp
            from llama_cpp import Llama
            return True
        except ImportError:
            logger.warning("[MIGRATION] llama_cpp not available, using rule-based migration")
            return False

    def execute(self, spec: MigrationSpec) -> MigrationResult:
        """Execute migration based on spec"""
        result = MigrationResult()

        # Phase 1: Find target files
        target_files = self._find_target_files(spec)
        result.files_scanned = len(target_files)

        logger.info(f"[MIGRATION] Scanning {len(target_files)} files for patterns: {spec.search_patterns[:3]}...")

        # Phase 2: Analyze each file and plan changes
        for file_path in target_files:
            changes = self._analyze_file(file_path, spec)
            if changes:
                result.changes.extend(changes)

        result.replacements_made = len([c for c in result.changes if c.change_type == "replacement"])
        result.files_modified = len(set(c.file for c in result.changes))

        # Phase 3: Apply the limited deterministic rule check.
        result.validation_passed = self._validate_changes(result.changes, spec)

        # Phase 4: Apply changes (if not dry_run)
        if not spec.dry_run and result.validation_passed:
            self._apply_changes(result.changes, spec)
            logger.info(f"[MIGRATION] Applied {result.replacements_made} changes to {result.files_modified} files")
        else:
            logger.info(f"[MIGRATION] Dry run: {result.replacements_made} changes in {result.files_modified} files")

        return result

    def _find_target_files(self, spec: MigrationSpec) -> List[Path]:
        """Find files matching target glob, excluding patterns"""
        files = []
        for path in self.repo_root.glob(spec.target_glob):
            if not path.is_file():
                continue

            path_str = str(path)
            excluded = any(exc in path_str for exc in spec.exclude_patterns)
            if not excluded:
                files.append(path)

        return files

    def _analyze_file(self, file_path: Path, spec: MigrationSpec) -> List[MigrationChange]:
        """Analyze file for migration opportunities"""
        changes = []

        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.warning(f"[MIGRATION] Cannot read {file_path}: {e}")
            return changes

        lines = content.split('\n')
        has_pattern = False
        needs_import = False

        # Check each line for patterns
        for line_num, line in enumerate(lines, 1):
            for pattern in spec.search_patterns:
                if pattern in line:
                    # Check if it's a string literal (quoted)
                    quoted_pattern = f'"{pattern}"' in line or f"'{pattern}'" in line
                    if quoted_pattern:
                        has_pattern = True
                        needs_import = True

                        # Generate replacement
                        replacement = spec.replacement_map.get(pattern)
                        if replacement:
                            new_line = line.replace(f'"{pattern}"', replacement)
                            new_line = new_line.replace(f"'{pattern}'", replacement)

                            if new_line != line:
                                changes.append(MigrationChange(
                                    file=str(file_path.relative_to(self.repo_root)),
                                    line=line_num,
                                    old=line.strip(),
                                    new=new_line.strip(),
                                    change_type="replacement"
                                ))

        # Add import if needed
        if needs_import and changes:
            import_line = self._generate_import_line(spec)
            changes.insert(0, MigrationChange(
                file=str(file_path.relative_to(self.repo_root)),
                line=1,
                old="",
                new=import_line,
                change_type="import_add"
            ))

        return changes

    def _generate_import_line(self, spec: MigrationSpec) -> str:
        """Generate import statement"""
        imports = ", ".join(spec.registry_imports)
        return f"from {spec.registry_module} import ({imports})"

    def _validate_changes(self, changes: List[MigrationChange], spec: MigrationSpec) -> bool:
        """Apply the prototype's limited balanced-parentheses rule check."""
        # Basic validation - check for syntax issues
        for change in changes:
            if change.change_type == "replacement":
                # Check balanced parentheses
                if change.new.count('(') != change.new.count(')'):
                    logger.error(f"[MIGRATION] Unbalanced parentheses in {change.file}:{change.line}")
                    return False

        return True

    def _apply_changes(self, changes: List[MigrationChange], spec: MigrationSpec):
        """Apply changes to files"""
        # Group changes by file
        changes_by_file: Dict[str, List[MigrationChange]] = {}
        for change in changes:
            if change.file not in changes_by_file:
                changes_by_file[change.file] = []
            changes_by_file[change.file].append(change)

        for file_rel, file_changes in changes_by_file.items():
            file_path = self.repo_root / file_rel

            # Create backup
            backup_path = file_path.with_suffix(file_path.suffix + '.bak')
            shutil.copy2(file_path, backup_path)

            # Read content
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            # Apply replacements (in reverse order to preserve line numbers)
            replacements = [c for c in file_changes if c.change_type == "replacement"]
            replacements.sort(key=lambda c: c.line, reverse=True)

            for change in replacements:
                idx = change.line - 1
                if 0 <= idx < len(lines):
                    # Apply the replacement
                    for pattern, replacement in spec.replacement_map.items():
                        lines[idx] = lines[idx].replace(f'"{pattern}"', replacement)
                        lines[idx] = lines[idx].replace(f"'{pattern}'", replacement)

            # Add import if needed
            import_changes = [c for c in file_changes if c.change_type == "import_add"]
            if import_changes:
                import_line = import_changes[0].new
                # Find insertion point (after existing imports)
                insert_idx = self._find_import_insertion_point(lines)
                lines.insert(insert_idx, import_line)

            # Write back
            file_path.write_text('\n'.join(lines), encoding='utf-8')
            logger.info(f"[MIGRATION] Updated {file_rel}")

    def _find_import_insertion_point(self, lines: List[str]) -> int:
        """Find where to insert new import"""
        last_import = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                last_import = i + 1
            elif stripped and not stripped.startswith('#') and not stripped.startswith('"""'):
                # Found non-import, non-comment line
                if last_import > 0:
                    break

        return max(last_import, 1)


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="Bulk Import Migration Tool")
    parser.add_argument("--spec", type=str, help="Path to migration spec JSON")
    parser.add_argument("--preset", type=str, choices=list(PRESETS.keys()), help="Use built-in preset")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview changes without applying")
    parser.add_argument("--apply", action="store_true", help="Apply changes (disables dry-run)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Load spec
    if args.preset:
        spec = PRESETS[args.preset]
        logger.info(f"[MIGRATION] Using preset: {args.preset}")
    elif args.spec:
        with open(args.spec, 'r') as f:
            spec_dict = json.load(f)
        spec = MigrationSpec(**spec_dict)
    else:
        parser.error("Either --spec or --preset required")
        return

    # Override dry_run if --apply specified
    if args.apply:
        spec.dry_run = False

    # Execute
    migrator = BulkImportMigrator()
    result = migrator.execute(spec)

    # Output results
    print(f"\n{'='*60}")
    print(f"Migration {'Preview' if spec.dry_run else 'Complete'}")
    print(f"{'='*60}")
    print(f"Files scanned: {result.files_scanned}")
    print(f"Files to modify: {result.files_modified}")
    print(f"Replacements: {result.replacements_made}")
    print(f"Validation: {'PASSED' if result.validation_passed else 'FAILED'}")

    if result.changes:
        print(f"\nChanges:")
        for change in result.changes[:20]:  # Show first 20
            if change.change_type == "import_add":
                print(f"  + [{change.file}] Add import: {change.new[:60]}...")
            else:
                print(f"  ~ [{change.file}:{change.line}]")
                print(f"    - {change.old[:60]}...")
                print(f"    + {change.new[:60]}...")

        if len(result.changes) > 20:
            print(f"  ... and {len(result.changes) - 20} more changes")

    if result.errors:
        print(f"\nErrors:")
        for err in result.errors:
            print(f"  ! {err}")

    # Output JSON for programmatic use
    if args.verbose:
        print(f"\n{'='*60}")
        print("JSON Output:")
        print(json.dumps({
            "files_scanned": result.files_scanned,
            "files_modified": result.files_modified,
            "replacements_made": result.replacements_made,
            "validation_passed": result.validation_passed,
            "changes": [{"file": c.file, "line": c.line, "type": c.change_type} for c in result.changes],
            "errors": result.errors
        }, indent=2))


if __name__ == "__main__":
    main()
