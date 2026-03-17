#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skills 2.0 Batch Updater - Add Skills 2.0 fields to all SKILL.md and SKILLz.md files.

Adds:
- category: workflow | capability-uplift
- evals: [] (benchmark test cases)
- retirement_date: null (for capability-uplift only)

WSP Compliance: WSP 97 (CoT/CoR), WSP 103 (CLI Standard)
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass
class UpdateResult:
    """Result of updating a single skill file."""
    path: str
    updated: bool
    fields_added: List[str]
    category: str
    error: Optional[str] = None


@dataclass
class BatchResult:
    """Result of batch update operation."""
    total_files: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    results: List[UpdateResult] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []


class Skills2BatchUpdater:
    """
    Batch updater for Skills 2.0 compliance.

    Finds all SKILL.md and SKILLz.md files and adds:
    - category: workflow | capability-uplift
    - evals: []
    - retirement_date: null
    """

    # Skills 2.0 fields to add
    SKILLS2_FIELDS = {
        "category": "workflow",  # default, can be overridden
        "evals": [],
        "retirement_date": None,
    }

    # Patterns to detect skill category
    CAPABILITY_UPLIFT_PATTERNS = [
        "pdf", "powerpoint", "presentation", "excel", "word",
        "image", "video", "audio", "ocr", "parsing"
    ]

    WORKFLOW_PATTERNS = [
        "orchestrat", "dae", "daemon", "monitor", "audit",
        "enhancement", "refactor", "compliance", "validation",
        "moderation", "engagement", "content", "generation"
    ]

    def __init__(self, repo_root: Optional[Path] = None, dry_run: bool = False):
        self.repo_root = repo_root or REPO_ROOT
        self.dry_run = dry_run

    def find_all_skills(self) -> List[Path]:
        """Find all SKILL.md and SKILLz.md files."""
        skills = []

        # Find SKILL.md
        for skill_file in self.repo_root.rglob("SKILL.md"):
            if ".worktrees" not in str(skill_file) and "__pycache__" not in str(skill_file):
                skills.append(skill_file)

        # Find SKILLz.md
        for skill_file in self.repo_root.rglob("SKILLz.md"):
            if ".worktrees" not in str(skill_file) and "__pycache__" not in str(skill_file):
                skills.append(skill_file)

        return sorted(skills)

    def parse_frontmatter(self, content: str) -> Tuple[Dict, str, str]:
        """
        Parse YAML frontmatter from skill file.

        Returns:
            (frontmatter_dict, frontmatter_str, body_str)
        """
        if not content.startswith("---"):
            return {}, "", content

        # Find end of frontmatter
        end_match = re.search(r'\n---\s*\n', content[3:])
        if not end_match:
            return {}, "", content

        frontmatter_str = content[4:end_match.start() + 3]
        body_str = content[end_match.end() + 3:]

        # Parse YAML manually (simple key: value)
        frontmatter = {}
        for line in frontmatter_str.split("\n"):
            line = line.strip()
            if ":" in line and not line.startswith("#"):
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                # Handle arrays
                if value.startswith("[") and value.endswith("]"):
                    value = [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
                elif value.lower() == "null" or value == "":
                    value = None
                elif value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                frontmatter[key] = value

        return frontmatter, frontmatter_str, body_str

    def detect_category(self, path: Path, frontmatter: Dict) -> str:
        """Detect skill category based on name and content."""
        name = frontmatter.get("name", path.parent.name).lower()
        description = str(frontmatter.get("description", "")).lower()
        combined = f"{name} {description}"

        # Check for capability-uplift patterns
        for pattern in self.CAPABILITY_UPLIFT_PATTERNS:
            if pattern in combined:
                return "capability-uplift"

        # Default to workflow
        return "workflow"

    def update_skill_file(self, skill_path: Path) -> UpdateResult:
        """Update a single skill file with Skills 2.0 fields."""
        result = UpdateResult(
            path=str(skill_path.relative_to(self.repo_root)),
            updated=False,
            fields_added=[],
            category="workflow"
        )

        try:
            content = skill_path.read_text(encoding="utf-8")
            frontmatter, fm_str, body = self.parse_frontmatter(content)

            if not frontmatter:
                result.error = "No frontmatter found"
                return result

            # Check which fields need to be added
            fields_to_add = []

            if "category" not in frontmatter:
                fields_to_add.append("category")
                category = self.detect_category(skill_path, frontmatter)
                result.category = category
            else:
                result.category = frontmatter.get("category", "workflow")

            if "evals" not in frontmatter:
                fields_to_add.append("evals")

            # Only add retirement_date for capability-uplift
            if result.category == "capability-uplift" and "retirement_date" not in frontmatter:
                fields_to_add.append("retirement_date")

            if not fields_to_add:
                result.updated = False
                return result

            # Build new frontmatter
            new_fm_lines = []
            for line in fm_str.split("\n"):
                new_fm_lines.append(line)

            # Add new fields before closing ---
            if "category" in fields_to_add:
                new_fm_lines.append(f"category: {result.category}")
            if "evals" in fields_to_add:
                new_fm_lines.append("evals: []")
            if "retirement_date" in fields_to_add:
                new_fm_lines.append("retirement_date: null")

            new_content = "---\n" + "\n".join(new_fm_lines) + "\n---\n" + body

            if not self.dry_run:
                skill_path.write_text(new_content, encoding="utf-8")

            result.updated = True
            result.fields_added = fields_to_add

        except Exception as e:
            result.error = str(e)

        return result

    def run_batch_update(self) -> BatchResult:
        """Run batch update on all skill files."""
        result = BatchResult()

        skills = self.find_all_skills()
        result.total_files = len(skills)

        print(f"[SCAN] Found {len(skills)} skill files")

        for skill_path in skills:
            update_result = self.update_skill_file(skill_path)
            result.results.append(update_result)

            if update_result.error:
                result.errors += 1
                print(f"[ERROR] {update_result.path}: {update_result.error}")
            elif update_result.updated:
                result.updated += 1
                fields = ", ".join(update_result.fields_added)
                mode = "[DRY-RUN]" if self.dry_run else "[UPDATED]"
                print(f"{mode} {update_result.path} (+{fields})")
            else:
                result.skipped += 1

        return result


def main():
    parser = argparse.ArgumentParser(
        description="Skills 2.0 Batch Updater - Add category, evals, retirement_date to all skills"
    )
    parser.add_argument("--scan", action="store_true", help="Scan and report (no changes)")
    parser.add_argument("--update", action="store_true", help="Update all skill files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without writing")
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    updater = Skills2BatchUpdater(dry_run=args.dry_run or args.scan)

    if args.scan or args.update or args.dry_run:
        result = updater.run_batch_update()

        if args.json:
            output = {
                "total_files": result.total_files,
                "updated": result.updated,
                "skipped": result.skipped,
                "errors": result.errors,
                "dry_run": args.dry_run or args.scan,
                "results": [asdict(r) for r in result.results if r.updated or r.error]
            }
            print(json.dumps(output, indent=2))
        else:
            print("\n" + "=" * 60)
            print("SKILLS 2.0 BATCH UPDATE RESULTS")
            print("=" * 60)
            print(f"Total skill files: {result.total_files}")
            print(f"Updated:           {result.updated}")
            print(f"Skipped (up-to-date): {result.skipped}")
            print(f"Errors:            {result.errors}")

            if args.dry_run or args.scan:
                print("\n[DRY-RUN] No files were modified. Use --update to apply changes.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
