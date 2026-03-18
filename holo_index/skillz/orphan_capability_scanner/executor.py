#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orphan Capability Scanner - WRE-Connected Skill

Finds code with CLI entrypoints that isn't WRE-connected and generates
SKILLz.md templates to connect it autonomously.

Problem: "Tons of code sitting waiting for 012 to use... 012 will never use it."
Solution: Autonomous scanner that finds orphans and generates connection templates.

WSP Compliance: WSP 77 (Agent Coordination), WSP 88 (Orphan Analysis), WSP 103 (CLI Standard)
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

# Ensure repo root is in path
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass
class CapabilityInfo:
    """Information about a detected capability (CLI entrypoint)."""
    path: str
    module_name: str
    has_main: bool = False
    has_json_flag: bool = False
    has_skillz_md: bool = False
    skillz_md_path: Optional[str] = None
    line_count: int = 0
    suggested_trigger: str = "manual"
    category: str = "unknown"


@dataclass
class ScanResult:
    """Result of orphan capability scan."""
    scan_timestamp: str
    total_cli_entrypoints: int = 0
    registered_skills: int = 0
    orphans: List[CapabilityInfo] = field(default_factory=list)
    wre_connected: List[CapabilityInfo] = field(default_factory=list)
    templates_generated: int = 0
    scan_duration_ms: float = 0.0


class OrphanCapabilityScanner:
    """
    Unified scanner combining:
    - GemmaOrphanDetector (import-based orphan detection)
    - OpenClawCapabilityAudit (CLI coverage analysis)
    - WSP88OrphanAnalyzer (import chain tracing)

    Plus: SKILLz.md cross-referencing and template generation.
    """

    # Directories to scan for CLI capabilities
    SCAN_DIRS = ["modules", "holo_index", "automation", "tools"]

    # Exclude patterns (always excluded)
    EXCLUDE_PATTERNS = {"__pycache__", ".git", "node_modules", "venv", ".venv", ".worktrees"}

    # Test patterns (excluded by default, include with --include-tests)
    TEST_PATTERNS = {"tests", "test_", "_test.py", "conftest.py"}

    # Known entry point patterns (not orphans)
    ENTRY_POINT_NAMES = {"main.py", "__main__.py", "cli.py", "run_skill.py", "executor.py"}

    def __init__(self, repo_root: Optional[Path] = None, include_tests: bool = False):
        self.repo_root = repo_root or REPO_ROOT
        self.include_tests = include_tests
        self.capabilities: Dict[str, CapabilityInfo] = {}
        self.skillz_registry: Set[str] = set()

    def scan(self) -> ScanResult:
        """
        Run full orphan capability scan.

        Returns:
            ScanResult with orphans and WRE-connected capabilities
        """
        import time
        start_time = time.time()

        result = ScanResult(
            scan_timestamp=datetime.now(timezone.utc).isoformat()
        )

        # Phase 1: Find all CLI entrypoints
        print("[SCAN] Phase 1: Finding CLI entrypoints...")
        self._find_cli_entrypoints()
        result.total_cli_entrypoints = len(self.capabilities)
        print(f"[SCAN] Found {result.total_cli_entrypoints} CLI entrypoints")

        # Phase 2: Load SKILLz.md registry
        print("[SCAN] Phase 2: Loading SKILLz.md registry...")
        self._load_skillz_registry()
        result.registered_skills = len(self.skillz_registry)
        print(f"[SCAN] Found {result.registered_skills} registered skills")

        # Phase 3: Cross-reference and classify
        print("[SCAN] Phase 3: Cross-referencing capabilities...")
        self._cross_reference_skillz()

        # Phase 4: Categorize results
        for cap in self.capabilities.values():
            if cap.has_skillz_md:
                result.wre_connected.append(cap)
            else:
                result.orphans.append(cap)

        # Sort orphans by line count (larger = more valuable to connect)
        result.orphans.sort(key=lambda x: -x.line_count)

        result.scan_duration_ms = (time.time() - start_time) * 1000
        print(f"[SCAN] Complete: {len(result.orphans)} orphans, "
              f"{len(result.wre_connected)} connected, "
              f"{result.scan_duration_ms:.0f}ms")

        return result

    def _find_cli_entrypoints(self):
        """Find all Python files with `if __name__ == "__main__"` blocks."""
        main_pattern = re.compile(r'if\s+__name__\s*==\s*["\']__main__["\']')
        json_pattern = re.compile(r'--json|argparse.*json|\.add_argument.*json')

        for scan_dir in self.SCAN_DIRS:
            dir_path = self.repo_root / scan_dir
            if not dir_path.exists():
                continue

            for py_file in dir_path.rglob("*.py"):
                # Skip excluded directories
                if any(excl in str(py_file) for excl in self.EXCLUDE_PATTERNS):
                    continue

                # Skip test files unless explicitly included
                if not self.include_tests:
                    path_lower = str(py_file).lower()
                    if any(test_pat in path_lower for test_pat in self.TEST_PATTERNS):
                        continue

                try:
                    content = py_file.read_text(encoding="utf-8", errors="replace")

                    has_main = bool(main_pattern.search(content))
                    if not has_main:
                        continue

                    has_json = bool(json_pattern.search(content))
                    line_count = content.count("\n")

                    # Determine category from path
                    rel_path = py_file.relative_to(self.repo_root)
                    category = self._categorize_path(rel_path)

                    # Suggest trigger based on category
                    trigger = self._suggest_trigger(category, py_file.name)

                    cap = CapabilityInfo(
                        path=str(rel_path),
                        module_name=self._path_to_module(rel_path),
                        has_main=True,
                        has_json_flag=has_json,
                        line_count=line_count,
                        category=category,
                        suggested_trigger=trigger,
                    )

                    self.capabilities[str(rel_path)] = cap

                except Exception as e:
                    print(f"[WARN] Error reading {py_file}: {e}")

    def _load_skillz_registry(self):
        """Load all registered SKILLz.md files."""
        for skillz_file in self.repo_root.rglob("SKILLz.md"):
            if any(excl in str(skillz_file) for excl in self.EXCLUDE_PATTERNS):
                continue

            # Get the skill directory
            skill_dir = skillz_file.parent
            rel_dir = skill_dir.relative_to(self.repo_root)

            # Look for executor.py or run_skill.py in same directory
            for executor_name in ["executor.py", "run_skill.py", "skill.py"]:
                executor_path = skill_dir / executor_name
                if executor_path.exists():
                    rel_executor = str(executor_path.relative_to(self.repo_root))
                    self.skillz_registry.add(rel_executor)
                    break

            # Also register the skill directory itself
            self.skillz_registry.add(str(rel_dir))

    def _cross_reference_skillz(self):
        """Cross-reference capabilities with SKILLz.md registry."""
        for path, cap in self.capabilities.items():
            # Check if this file or its directory has a SKILLz.md
            path_obj = Path(path)

            # Direct match
            if path in self.skillz_registry:
                cap.has_skillz_md = True
                cap.skillz_md_path = str(path_obj.parent / "SKILLz.md")
                continue

            # Check parent directory
            parent_dir = str(path_obj.parent)
            if parent_dir in self.skillz_registry:
                cap.has_skillz_md = True
                cap.skillz_md_path = str(path_obj.parent / "SKILLz.md")
                continue

            # Check for SKILLz.md in same directory
            skillz_path = self.repo_root / path_obj.parent / "SKILLz.md"
            if skillz_path.exists():
                cap.has_skillz_md = True
                cap.skillz_md_path = str(path_obj.parent / "SKILLz.md")

    def _categorize_path(self, rel_path: Path) -> str:
        """Categorize a file based on its path."""
        path_str = str(rel_path).lower()

        if "platform_integration" in path_str:
            return "platform"
        elif "ai_intelligence" in path_str:
            return "ai"
        elif "infrastructure" in path_str:
            return "infrastructure"
        elif "communication" in path_str:
            return "communication"
        elif "holo_index" in path_str:
            return "holoindex"
        elif "monitoring" in path_str:
            return "monitoring"
        else:
            return "other"

    def _suggest_trigger(self, category: str, filename: str) -> str:
        """Suggest appropriate trigger for a capability."""
        if "dae" in filename.lower() or "daemon" in filename.lower():
            return "cadence:continuous"
        elif "audit" in filename.lower() or "report" in filename.lower():
            return "cadence:daily"
        elif "go_live" in filename.lower() or "stream" in filename.lower():
            return "event:stream_start"
        elif "post" in filename.lower() or "publish" in filename.lower():
            return "event:content_ready"
        elif category == "monitoring":
            return "cadence:hourly"
        elif category == "platform":
            return "event:platform_trigger"
        else:
            return "manual"

    def _path_to_module(self, rel_path: Path) -> str:
        """Convert file path to Python module name."""
        parts = list(rel_path.parts)
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        return ".".join(parts)

    def generate_templates(self, orphans: List[CapabilityInfo], limit: int = 10) -> List[str]:
        """
        Generate SKILLz.md templates for top orphans.

        Args:
            orphans: List of orphan capabilities
            limit: Maximum templates to generate

        Returns:
            List of generated template paths
        """
        templates_dir = self.repo_root / "reports" / "orphan_skillz_templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        generated = []

        for cap in orphans[:limit]:
            template = self._create_skillz_template(cap)

            # Create filename from module path
            safe_name = cap.module_name.replace(".", "_").replace("/", "_")
            template_path = templates_dir / f"{safe_name}_SKILLz.md"

            template_path.write_text(template, encoding="utf-8")
            generated.append(str(template_path))
            print(f"[GEN] Created template: {template_path.name}")

        return generated

    def _create_skillz_template(self, cap: CapabilityInfo) -> str:
        """Create a SKILLz.md template for an orphan capability."""

        # Extract skill name from path
        skill_name = Path(cap.path).stem

        # Determine appropriate agents
        if cap.category in ("ai", "holoindex"):
            agents = "[qwen, gemma]"
            primary = "qwen"
        else:
            agents = "[qwen]"
            primary = "qwen"

        template = f"""---
name: {skill_name}
description: TODO - Add description for {skill_name}
version: 1.0_prototype
author: 0102
created: {datetime.now().strftime("%Y-%m-%d")}
agents: {agents}
primary_agent: {primary}
intent_type: TODO
promotion_state: prototype
pattern_fidelity_threshold: 0.85
trigger:
  {cap.suggested_trigger.replace(":", ": ")}
---

# {skill_name.replace("_", " ").title()}

**Purpose**: TODO - Describe what this skill does

**Source**: `{cap.path}`
**Lines**: {cap.line_count}
**Category**: {cap.category}

---

## What This Skill Does

TODO - Document the capability

---

## Execution

```bash
python {cap.path} --help
{"python " + cap.path + " --json" if cap.has_json_flag else "# TODO: Add --json support per WSP 103"}
```

---

## WRE Connection

- **Trigger**: `{cap.suggested_trigger}`
- **Agent**: {primary}
- **JSON Output**: {"Yes" if cap.has_json_flag else "No - needs WSP 103 compliance"}

---

## Autonomy Test

Can N compute cycles complete without 012?

**TODO** - Verify autonomous operation

---

*Auto-generated by orphan_capability_scanner on {datetime.now().strftime("%Y-%m-%d")}*
*WSP Compliance*: WSP 77 (Agent Coordination), WSP 103 (CLI Standard)
"""
        return template


def main():
    """Main entry point for orphan capability scanner."""
    parser = argparse.ArgumentParser(
        description="Orphan Capability Scanner - Find unconnected code and generate WRE templates"
    )
    parser.add_argument("--scan", action="store_true", help="Run full scan")
    parser.add_argument("--generate", type=int, metavar="N", help="Generate templates for top N orphans")
    parser.add_argument("--json", action="store_true", help="Output JSON (for OpenClaw)")
    parser.add_argument("--summary", action="store_true", help="Print summary only")
    parser.add_argument("--include-tests", action="store_true", help="Include test files (excluded by default)")

    args = parser.parse_args()

    scanner = OrphanCapabilityScanner(include_tests=args.include_tests)
    result = scanner.scan()

    # Generate templates if requested
    if args.generate:
        templates = scanner.generate_templates(result.orphans, args.generate)
        result.templates_generated = len(templates)

    # Output format
    if args.json:
        # Convert to JSON-serializable format
        output = {
            "scan_timestamp": result.scan_timestamp,
            "total_cli_entrypoints": result.total_cli_entrypoints,
            "registered_skills": result.registered_skills,
            "orphan_count": len(result.orphans),
            "wre_connected_count": len(result.wre_connected),
            "templates_generated": result.templates_generated,
            "scan_duration_ms": result.scan_duration_ms,
            "orphans": [asdict(o) for o in result.orphans[:20]],  # Limit JSON output
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        print("\n" + "=" * 60)
        print("ORPHAN CAPABILITY SCAN RESULTS")
        print("=" * 60)
        print(f"Total CLI entrypoints: {result.total_cli_entrypoints}")
        print(f"Registered SKILLz.md:  {result.registered_skills}")
        print(f"Orphans (unconnected): {len(result.orphans)}")
        print(f"WRE-connected:         {len(result.wre_connected)}")
        print(f"Scan time:             {result.scan_duration_ms:.0f}ms")

        if result.orphans and not args.summary:
            print("\n[TOP 10 ORPHANS - Largest First]")
            for i, orphan in enumerate(result.orphans[:10], 1):
                json_flag = "[JSON]" if orphan.has_json_flag else ""
                print(f"  {i}. {orphan.path}")
                print(f"      {orphan.line_count} lines | {orphan.category} | {orphan.suggested_trigger} {json_flag}")

        if result.templates_generated:
            print(f"\n[TEMPLATES] Generated {result.templates_generated} SKILLz.md templates")
            print(f"  Location: reports/orphan_skillz_templates/")


if __name__ == "__main__":
    main()
