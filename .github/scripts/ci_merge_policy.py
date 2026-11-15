"""Validate the changed WSP mirrors and catalog in the merge scope pilot."""

import argparse
import json
import re
import stat
import subprocess
import sys
from collections import Counter
from pathlib import Path, PurePosixPath


FRAMEWORK = Path("WSP_framework/src")
KNOWLEDGE = Path("WSP_knowledge/src")
INDEX = FRAMEWORK / "WSP_MASTER_INDEX.md"
PROTOCOL = re.compile(r"WSP_(\d{1,3})_.+\.md")
CATALOG_ROW = re.compile(r"^\|\s*WSP\s+(\d{1,3})\s*\|", re.MULTILINE)
NEXT_NUMBER = re.compile(r"\*\*Next Available Number\*\*:\s*WSP\s+(\d+)")
SKILL_REGISTRY = Path("modules/infrastructure/wre_core/skillz/skills_registry_v2.json")
PROPOSAL_PATH = re.compile(
    r"modules/[a-z0-9_]+/[a-z0-9_]+/skillz/[a-z0-9_-]+/SKILL(?:z)?\.md"
)
PROPOSAL_STATUS = "**Status:** PROPOSED / DOCUMENTATION ONLY"
_PROPOSAL_STATUS_SUFFIX = " — no runtime, account, credential, trial, or worker activation."
PROPOSAL_SECTIONS = (
    ("intent", "boundary"),
    ("governance", "source", "truth"),
    ("acceptance", "learning", "proof"),
    ("handoff", "next", "action"),
)
_MAX_SKILL_BYTES = 128 * 1024
_MAX_REGISTRY_BYTES = 2 * 1024 * 1024


def policy_issues(base, paths):
    """Report changed mirror drift and invalid numbered protocol entries."""
    names = {
        path.name for path in map(Path, paths)
        if path.parent in {FRAMEWORK, KNOWLEDGE} and path.name.startswith("WSP_")
    }
    if not names:
        return []

    # Proposal verification must not import any candidate repository modules.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/wsp_protection"))
    from archive_synchronizer import compare_framework_to_knowledge

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
            ["git", "show", f"{base}:{INDEX.as_posix()}"], encoding="utf-8", timeout=10
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


def _git_evidence(*args):
    try:
        return subprocess.run(
            ["git", "--no-replace-objects", "--literal-pathspecs", *args],
            check=True, capture_output=True, timeout=10,
        ).stdout
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise ValueError("Exact-base Git evidence is unavailable") from error


def _regular_bytes(path, limit):
    current = Path()
    for component in path.parts:
        current /= component
        metadata = current.lstat()
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise ValueError("Links and reparse components are not proposal documents")
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("Expected a regular file")
    with path.open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError("Document exceeds its verification size bound")
    return content


def _registry(raw):
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("skills"), dict):
        raise ValueError("Skill registry has an unknown schema")
    locations = set()
    for entry in value["skills"].values():
        location = entry.get("location") if isinstance(entry, dict) else None
        if (
            not isinstance(location, str) or not location or "\\" in location
            or ":" in location or PurePosixPath(location).is_absolute()
            or any(part in {".", ".."} for part in location.split("/"))
            or str(PurePosixPath(location)) != location
        ):
            raise ValueError("Skill registry contains an unknown location")
        locations.add(location)
    return set(value["skills"]), locations


def _proposal_structure(text):
    """Check a documentation shape, never execution or promotion authority."""
    issues = []
    if text.lstrip("\ufeff \t\r\n").startswith("---"):
        issues.append("Skill frontmatter requires full verification")
    # Comments and fenced examples cannot supply the visible document schema.
    visible = []
    fence = None
    for line in re.sub(r"<!--.*?(?:-->|\Z)", "", text, flags=re.DOTALL).splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            run, suffix = marker.groups()
            if fence is None:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence) and not suffix.strip():
                fence = None
            continue
        if fence is None:
            visible.append(line)
    text = "\n".join(visible)
    statuses = [
        line.strip() for line in visible
        if re.match(r"^\*\*Status(?::\*\*|\*\*:)", line, re.IGNORECASE)
    ]
    if len(statuses) != 1 or statuses[0] not in {
        PROPOSAL_STATUS, PROPOSAL_STATUS + _PROPOSAL_STATUS_SUFFIX,
    }:
        issues.append("Expected one explicit PROPOSED / DOCUMENTATION ONLY status")
    headings = list(re.finditer(r"^#{1,6}[ \t]+([^\n]+)$", text, re.MULTILINE))
    for required in PROPOSAL_SECTIONS:
        matches = [
            index for index, heading in enumerate(headings)
            if set(required) <= set(re.findall(r"[a-z]+", heading[1].lower()))
        ]
        if len(matches) != 1:
            issues.append("Expected one proposal section: " + "/".join(required))
        else:
            index = matches[0]
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            if not text[headings[index].end():end].strip():
                issues.append("Empty proposal section: " + "/".join(required))
    for number in (0, 15, 48, 95, 97, 110):
        if not re.search(rf"\bWSP[ _-]{number:02d}(?![A-Za-z0-9])", text):
            issues.append(f"Missing proposal governance reference: WSP_{number:02d}")
    return issues


def proposal_skill_issues(base, paths):
    """Verify new, unregistered documentation proposals; grant no admission.

    The caller separately proves the complete exact-base/head/test-merge diff.
    Existing Skill directories, ambiguous evidence and every executable bundle
    remain outside this bounded pilot, irrespective of an author's status label.
    """
    if (
        not re.fullmatch(r"[0-9a-f]{40}", str(base))
        or not isinstance(paths, (list, tuple)) or not paths
    ):
        return ["Proposal verification requires an exact base and changed paths"]
    if any(not isinstance(path, str) or not PROPOSAL_PATH.fullmatch(path) for path in paths):
        return ["Proposal scope contains an unsupported path"]
    try:
        if _git_evidence("cat-file", "-t", base).strip() != b"commit":
            raise ValueError("Expected an exact base commit")
        registry_object = f"{base}:{SKILL_REGISTRY.as_posix()}"
        if int(_git_evidence("cat-file", "-s", registry_object)) > _MAX_REGISTRY_BYTES:
            raise ValueError("Base registry exceeds its verification size bound")
        registries = (
            _registry(_git_evidence("cat-file", "blob", registry_object)),
            _registry(_regular_bytes(SKILL_REGISTRY, _MAX_REGISTRY_BYTES)),
        )
    except (OSError, ValueError, UnicodeError) as error:
        return [f"Proposal registry evidence is unavailable: {error}"]
    issues = []
    for filename in sorted(set(paths)):
        path = Path(filename)
        directory = path.parent.as_posix()
        try:
            if _git_evidence("ls-tree", "-z", base, "--", directory):
                raise ValueError("Existing Skill directories require full verification")
            if any(
                path.parent.name in names or any(
                    location == directory or location.startswith(directory + "/")
                    or directory.startswith(location + "/") for location in locations
                ) for names, locations in registries
            ):
                raise ValueError("Registered Skill documents require full verification")
            raw = _regular_bytes(path, _MAX_SKILL_BYTES)
            if set(path.parent.iterdir()) != {path}:
                raise ValueError("Adjacent files or executable bundles require full verification")
            if b"\0" in raw:
                raise ValueError("NUL bytes are not proposal documentation")
            issues.extend(f"{filename}: {issue}" for issue in _proposal_structure(raw.decode("utf-8")))
        except (OSError, ValueError, UnicodeError) as error:
            issues.append(f"{filename}: {error}")
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-proposals", action="store_true")
    parser.add_argument("base")
    parser.add_argument("scope_file")
    args = parser.parse_args()
    scope = json.loads(Path(args.scope_file).read_text(encoding="utf-8"))
    verifier = proposal_skill_issues if args.skill_proposals else policy_issues
    failures = verifier(args.base, scope["paths"])
    for issue in failures:
        print(issue, file=sys.stderr)
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
