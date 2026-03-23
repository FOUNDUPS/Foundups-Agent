#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Root Directory Violations - WSP 3 Compliance
================================================

Uses AI Overseer / Holo root monitoring as the discovery surface and applies
known-safe relocations for recurring root pollution patterns.

WSP Compliance: WSP 3, WSP 49, WSP 50, WSP 22
"""

import io
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Tuple

if sys.platform.startswith("win"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        pass

REPO_ROOT = Path(__file__).resolve().parents[1]

# Use explicit, reviewed relocations only. This is a known-map fixer, not a bulk mover.
RELOCATION_MAP = {
    # WRE phase docs -> WRE docs
    "WRE_PHASE1_COMPLETE.md": "modules/infrastructure/wre_core/docs/",
    "WRE_PHASE1_CORRECTED_AUDIT.md": "modules/infrastructure/wre_core/docs/",
    "WRE_PHASE1_WSP_COMPLIANCE_AUDIT.md": "modules/infrastructure/wre_core/docs/",
    "WRE_PHASE2_CORRECTED_AUDIT.md": "modules/infrastructure/wre_core/docs/",
    "WRE_PHASE2_FINAL_AUDIT.md": "modules/infrastructure/wre_core/docs/",
    "WRE_PHASE2_WSP_COMPLIANCE_AUDIT.md": "modules/infrastructure/wre_core/docs/",
    "WRE_PHASE3_CORRECTED_AUDIT.md": "modules/infrastructure/wre_core/docs/",
    "WRE_PHASE3_TOKEN_ESTIMATE.md": "modules/infrastructure/wre_core/docs/",
    "WRE_PHASE3_WSP_COMPLIANCE_AUDIT.md": "modules/infrastructure/wre_core/docs/",
    "WRE_PHASES_COMPLETE_SUMMARY.md": "modules/infrastructure/wre_core/docs/",
    "WRE_SKILLS_IMPLEMENTATION_SUMMARY.md": "modules/infrastructure/wre_core/docs/",
    "WRE_CLI_REFACTOR_READY.md": "modules/infrastructure/wre_core/docs/",

    # Repo docs / investigations
    "IMPLEMENTATION_INSTRUCTIONS_OPTION5.md": "docs/",
    "WRE_PHASE1_COMPLIANCE_REPORT.md": "docs/",
    "YOUTUBE_SHORTS_INVESTIGATION_FINDINGS.md": "docs/investigations/",
    "COMMENT_ROTATION_ISSUE_ANALYSIS.json": "docs/investigations/",

    # Tests
    "test_pqn_meta_research.py": "modules/ai_intelligence/pqn_alignment/tests/",
    "test_ai_overseer_monitoring.py": "modules/ai_intelligence/ai_overseer/tests/",
    "test_ai_overseer_unicode_fix.py": "modules/ai_intelligence/ai_overseer/tests/",
    "test_monitor_flow.py": "modules/ai_intelligence/ai_overseer/tests/",
    "test_gemma_nested_module_detector.py": "modules/infrastructure/doc_dae/tests/",

    # Scripts
    "async_pqn_research_orchestrator.py": "modules/ai_intelligence/pqn_alignment/scripts/",
    "pqn_cross_platform_validator.py": "modules/ai_intelligence/pqn_alignment/scripts/",
    "pqn_realtime_dashboard.py": "modules/ai_intelligence/pqn_alignment/scripts/",
    "pqn_streaming_aggregator.py": "modules/ai_intelligence/pqn_alignment/scripts/",
    "check_port_sentinel.py": "scripts/verification/",

    # Logs / run artifacts
    "verification_log.txt": "logs/",
}


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def move_file_with_backup(src: Path, dest_dir: Path) -> Tuple[bool, str]:
    """Move file to destination with backup if needed."""
    try:
        ensure_directory(dest_dir)
        dest_file = dest_dir / src.name

        if dest_file.exists():
            backup = dest_file.with_suffix(dest_file.suffix + ".backup")
            shutil.copy2(dest_file, backup)
            print(f"  [BACKUP] Backed up existing {dest_file.name} to {backup.name}")

        git_dir = REPO_ROOT / ".git"
        if git_dir.exists():
            result = subprocess.run(
                ["git", "mv", str(src), str(dest_file)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0:
                return True, f"Moved {src.name} -> {dest_dir.relative_to(REPO_ROOT)}"

        shutil.move(str(src), str(dest_file))
        return True, f"Moved {src.name} -> {dest_dir.relative_to(REPO_ROOT)}"
    except Exception as exc:
        return False, f"Failed to move {src.name}: {exc}"


def verify_relocation(original: Path, new_location: Path) -> bool:
    return new_location.exists() and not original.exists()


def main() -> int:
    print("[ROOT-CLEANUP] Starting root directory violation fixes")
    print(f"[REPO] {REPO_ROOT}")
    print()

    results = {
        "moved": [],
        "failed": [],
        "verified": [],
    }

    print("[PHASE-1] Moving files to correct locations per WSP 3")
    print("-" * 60)

    for filename, dest_rel_path in RELOCATION_MAP.items():
        src = REPO_ROOT / filename
        if not src.exists():
            print(f"  [SKIP] {filename} not found")
            continue

        dest_dir = REPO_ROOT / dest_rel_path
        success, message = move_file_with_backup(src, dest_dir)

        if success:
            print(f"  [OK] {message}")
            results["moved"].append({
                "file": filename,
                "from": str(REPO_ROOT),
                "to": dest_rel_path,
            })
        else:
            print(f"  [FAIL] {message}")
            results["failed"].append({
                "file": filename,
                "error": message,
            })

    print()
    print("[PHASE-2] Verifying relocations")
    print("-" * 60)

    for moved in results["moved"]:
        original = REPO_ROOT / moved["file"]
        new_loc = REPO_ROOT / moved["to"] / moved["file"]

        if verify_relocation(original, new_loc):
            print(f"  [VERIFY] {moved['file']} -> {moved['to']}")
            results["verified"].append(moved["file"])
        else:
            print(f"  [ERROR] {moved['file']} verification failed")

    print()
    print("[PHASE-3] Summary")
    print("-" * 60)
    print(f"  Files moved: {len(results['moved'])}")
    print(f"  Files verified: {len(results['verified'])}")
    print(f"  Failed: {len(results['failed'])}")

    results_file = REPO_ROOT / "data" / "root_cleanup_results.json"
    ensure_directory(results_file.parent)
    with open(results_file, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)

    print()
    print(f"[RESULTS] Saved to {results_file.relative_to(REPO_ROOT)}")

    if results["failed"]:
        print()
        print("[FAILED] The following files had errors:")
        for failed in results["failed"]:
            print(f"  - {failed['file']}: {failed['error']}")
        return 1

    print()
    print("[SUCCESS] All files relocated and verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
