"""Validate the changed WSP mirrors and catalog in the merge scope pilot."""

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path("tools/wsp_protection").resolve()))
from archive_synchronizer import compare_framework_to_knowledge


FRAMEWORK = Path("WSP_framework/src")
KNOWLEDGE = Path("WSP_knowledge/src")
INDEX = FRAMEWORK / "WSP_MASTER_INDEX.md"
PROTOCOL = re.compile(r"WSP_(\d{1,3})_.+\.md")
CATALOG_ROW = re.compile(r"^\|\s*WSP\s+(\d{1,3})\s*\|", re.MULTILINE)
NEXT_NUMBER = re.compile(r"\*\*Next Available Number\*\*:\s*WSP\s+(\d+)")


def policy_issues(base, paths):
    """Report changed mirror drift and invalid numbered protocol entries."""
    names = {
        path.name for path in map(Path, paths)
        if path.parent in {FRAMEWORK, KNOWLEDGE} and path.name.startswith("WSP_")
    }
    if not names:
        return []

    report = compare_framework_to_knowledge(FRAMEWORK, KNOWLEDGE)
    drift = set(report.missing_in_knowledge + report.drifted_in_knowledge + report.extra_in_knowledge)
    issues = [f"WSP mirror mismatch: {name}" for name in sorted(names & drift)]

    index_text = INDEX.read_text(encoding="utf-8")
    rows = Counter(map(int, CATALOG_ROW.findall(index_text)))
    indexed = set(rows)
    counts = Counter(
        int(match[1]) for path in FRAMEWORK.glob("WSP_*.md")
        if (match := PROTOCOL.fullmatch(path.name))
    )
    changed = {int(match[1]) for name in names if (match := PROTOCOL.fullmatch(name))}
    if INDEX.name in names:
        previous = subprocess.check_output(
            ["git", "show", f"{base}:{INDEX.as_posix()}"], encoding="utf-8"
        )
        previous_rows = Counter(map(int, CATALOG_ROW.findall(previous)))
        previously_indexed = set(previous_rows)
        for number in sorted(rows - previous_rows):
            if rows[number] > 1:
                issues.append(f"WSP {number:02d} has a new duplicate master index row")
        changed.update((previously_indexed - indexed) & counts.keys())
        next_number = NEXT_NUMBER.findall(index_text)
        if indexed != previously_indexed or next_number != NEXT_NUMBER.findall(previous):
            # The catalog may reserve numbers before their files land.
            if next_number != [str(max(indexed | counts.keys()) + 1)]:
                issues.append("WSP master index has an incorrect next available number")
    for number in sorted(changed):
        if counts[number] != 1:
            issues.append(f"WSP {number:02d} must have exactly one canonical protocol file")
        if number not in indexed and (number != 0 or "WSP_00_Zen_State_Attainment_Protocol.md" not in index_text):
            issues.append(f"WSP {number:02d} is missing from the master index")
    return issues


if __name__ == "__main__":
    base_sha, scope_file = sys.argv[1:]
    scope = json.loads(Path(scope_file).read_text(encoding="utf-8"))
    failures = policy_issues(base_sha, scope["paths"])
    for issue in failures:
        print(issue, file=sys.stderr)
    sys.exit(bool(failures))
