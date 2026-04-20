#!/usr/bin/env python3
"""
PR Scope Guard - Prevents mixed-scope PRs from merging.

Compares expected files declared in PR body against actual changed files.
Fails if files outside the declared scope appear.

Motivation: PR #384 incident where DJ-OBS commits entered main through
a rolodex PR via branch contamination. See BH1 forensics report.

Usage:
    python pr_scope_guard.py --pr-body "..." --changed-files file1.py file2.py
    python pr_scope_guard.py --pr-number 123  # Fetches from GitHub API

Required PR body format:
    Window: AG5
    Slice: BH2
    Lane: Process
    Expected files:
    - path/to/file1.py
    - path/to/file2.py

Exit codes:
    0 - All changed files are within declared scope
    1 - Scope violation detected (unexpected files)
    2 - Missing required PR body fields
    3 - Parse error or invalid input
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Optional


def parse_pr_body(body: str) -> dict:
    """Extract Window, Slice, Lane, and Expected files from PR body."""
    result = {
        "window": None,
        "slice": None,
        "lane": None,
        "expected_files": [],
        "errors": [],
    }

    lines = body.split("\n")

    for line in lines:
        line_stripped = line.strip()

        if line_stripped.lower().startswith("window:"):
            result["window"] = line_stripped.split(":", 1)[1].strip()
        elif line_stripped.lower().startswith("slice:"):
            result["slice"] = line_stripped.split(":", 1)[1].strip()
        elif line_stripped.lower().startswith("lane:"):
            result["lane"] = line_stripped.split(":", 1)[1].strip()

    expected_section = re.search(
        r"expected files:\s*\n((?:\s*[-*]\s*.+\n?)+)",
        body,
        re.IGNORECASE | re.MULTILINE,
    )

    if expected_section:
        file_lines = expected_section.group(1)
        for line in file_lines.split("\n"):
            match = re.match(r"\s*[-*]\s*(.+)", line)
            if match:
                filepath = match.group(1).strip().strip("`")
                if filepath:
                    result["expected_files"].append(filepath)

    if not result["window"]:
        result["errors"].append("Missing 'Window:' field in PR body")
    if not result["slice"]:
        result["errors"].append("Missing 'Slice:' field in PR body")
    if not result["expected_files"]:
        result["errors"].append("Missing 'Expected files:' section in PR body")

    return result


def check_scope(expected_files: list[str], changed_files: list[str]) -> dict:
    """Compare expected files against changed files."""
    expected_set = set(expected_files)
    changed_set = set(changed_files)

    in_scope = changed_set & expected_set
    out_of_scope = changed_set - expected_set
    missing = expected_set - changed_set

    return {
        "pass": len(out_of_scope) == 0,
        "in_scope": sorted(in_scope),
        "out_of_scope": sorted(out_of_scope),
        "missing": sorted(missing),
        "expected_count": len(expected_set),
        "changed_count": len(changed_set),
    }


def fetch_pr_info(pr_number: int) -> tuple[str, list[str]]:
    """Fetch PR body and changed files from GitHub API."""
    try:
        body_result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "body"],
            capture_output=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
        body_data = json.loads(body_result.stdout)
        body = body_data.get("body", "")

        files_result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "files"],
            capture_output=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
        files_data = json.loads(files_result.stdout)
        changed_files = [f["path"] for f in files_data.get("files", [])]

        return body, changed_files
    except subprocess.CalledProcessError as e:
        print(f"Error fetching PR #{pr_number}: {e.stderr}", file=sys.stderr)
        sys.exit(3)
    except json.JSONDecodeError as e:
        print(f"Error parsing GitHub response: {e}", file=sys.stderr)
        sys.exit(3)


def format_report(parsed: dict, scope_result: dict, pr_number: Optional[int] = None) -> str:
    """Format the scope check report."""
    lines = []
    lines.append("=" * 60)
    lines.append("PR SCOPE GUARD REPORT")
    lines.append("=" * 60)

    if pr_number:
        lines.append(f"PR: #{pr_number}")
    lines.append(f"Window: {parsed['window'] or 'NOT DECLARED'}")
    lines.append(f"Slice: {parsed['slice'] or 'NOT DECLARED'}")
    lines.append(f"Lane: {parsed['lane'] or 'NOT DECLARED'}")
    lines.append("")

    if parsed["errors"]:
        lines.append("PARSE ERRORS:")
        for err in parsed["errors"]:
            lines.append(f"  - {err}")
        lines.append("")

    lines.append(f"Expected files: {scope_result['expected_count']}")
    lines.append(f"Changed files: {scope_result['changed_count']}")
    lines.append("")

    if scope_result["out_of_scope"]:
        lines.append("OUT OF SCOPE (VIOLATION):")
        for f in scope_result["out_of_scope"]:
            lines.append(f"  - {f}")
        lines.append("")

    if scope_result["in_scope"]:
        lines.append("IN SCOPE:")
        for f in scope_result["in_scope"]:
            lines.append(f"  + {f}")
        lines.append("")

    if scope_result["missing"]:
        lines.append("EXPECTED BUT NOT CHANGED:")
        for f in scope_result["missing"]:
            lines.append(f"  ? {f}")
        lines.append("")

    lines.append("=" * 60)
    if scope_result["pass"] and not parsed["errors"]:
        lines.append("RESULT: PASS - All files within declared scope")
    elif parsed["errors"]:
        lines.append("RESULT: FAIL - Missing required PR body fields")
    else:
        lines.append("RESULT: FAIL - Scope violation detected")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="PR Scope Guard - Prevents mixed-scope PRs"
    )
    parser.add_argument(
        "--pr-number",
        type=int,
        help="GitHub PR number (fetches body and files via gh CLI)",
    )
    parser.add_argument(
        "--pr-body",
        type=str,
        help="PR body text (alternative to --pr-number)",
    )
    parser.add_argument(
        "--changed-files",
        nargs="*",
        help="List of changed files (alternative to --pr-number)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of text report",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Also fail if expected files are missing from changes",
    )

    args = parser.parse_args()

    if args.pr_number:
        body, changed_files = fetch_pr_info(args.pr_number)
    elif args.pr_body and args.changed_files:
        body = args.pr_body
        changed_files = args.changed_files
    else:
        parser.error("Either --pr-number or both --pr-body and --changed-files required")
        return

    parsed = parse_pr_body(body)

    if parsed["errors"]:
        if args.json:
            print(json.dumps({"pass": False, "errors": parsed["errors"]}, indent=2))
        else:
            print(format_report(parsed, {"pass": False, "expected_count": 0,
                  "changed_count": len(changed_files), "in_scope": [],
                  "out_of_scope": changed_files, "missing": []}, args.pr_number))
        sys.exit(2)

    scope_result = check_scope(parsed["expected_files"], changed_files)

    if args.strict and scope_result["missing"]:
        scope_result["pass"] = False

    if args.json:
        output = {
            "pass": scope_result["pass"],
            "window": parsed["window"],
            "slice": parsed["slice"],
            "lane": parsed["lane"],
            **scope_result,
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_report(parsed, scope_result, args.pr_number))

    sys.exit(0 if scope_result["pass"] else 1)


if __name__ == "__main__":
    main()
