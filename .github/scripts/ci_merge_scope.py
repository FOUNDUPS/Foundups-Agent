"""Classify a verified GitHub pull request test-merge diff for CI."""

import argparse
import json
import re
import subprocess


_SHA = re.compile(r"[0-9a-f]{40}")
_PROSE = re.compile(
    r"docs/(?:ci-pilot/examples|audits/prose)/"
    r"(?!(?:agents|claude|gemini|skillz?)\.md$)[a-z0-9]+(?:[-_][a-z0-9]+)*\.md"
    r"|docs/audits/agent_git_workflow_impact_audit\.md"
)
_POLICY = re.compile(
    r"(?:AGENTS|CLAUDE|GEMINI)\.md"
    r"|WSP_(?:framework|knowledge)/src/WSP_(?:[0-9]+_[A-Za-z0-9_.-]+|MASTER_INDEX)\.md"
    r"|WSP_framework/ModLog\.md"
    r"|\.(?:agent|agents|claude|codex)/skills/[A-Za-z0-9_/-]+/SKILL\.md"
    r"|\.github/(?:copilot-instructions\.md|instructions/[A-Za-z0-9_.-]+\.instructions\.md)"
)
_SKILL_PROPOSAL = re.compile(
    r"modules/[a-z][a-z0-9_]*/[a-z][a-z0-9_]*/skillz/"
    r"[a-z][a-z0-9_]*/SKILLz?\.md"
)
_REGISTRY = "modules/infrastructure/wre_core/skillz/skills_registry_v2.json"
SCHEMA = "ci_merge_scope.v1"


def _git(*args):
    try:
        return subprocess.run(
            ["git", "--no-replace-objects", *args], check=True, capture_output=True,
            timeout=30,
        ).stdout
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError(f"Git {args[0]} failed; evidence is unavailable") from error


def _changes(before, after):
    raw = _git(
        "diff", "--raw", "-z", "--no-abbrev", "--no-renames", "--no-ext-diff",
        "--no-textconv", "--ignore-submodules=none", before, after, "--",
    )
    records = raw.split(b"\0")
    if records[-1] != b"" or len(records) % 2 != 1:
        raise ValueError("Malformed Git diff")
    changes = {}
    for metadata, filename in zip(records[:-1:2], records[1:-1:2]):
        fields = metadata.split()
        path = filename.decode("utf-8", errors="surrogateescape")
        if len(fields) != 5 or not metadata.startswith(b":") or not path or path in changes:
            raise ValueError("Malformed Git diff record")
        changes[path] = fields
    return changes


def _new_proposal(base, merge, path):
    """Only a new, unregistered, non-executable proposal can use this pilot."""
    directory = path.rsplit("/", 1)[0]
    if _git("ls-tree", "-r", "--name-only", base, "--", directory).strip():
        return False
    members = _git("ls-tree", "-r", "--name-only", merge, "--", directory).splitlines()
    if members != [path.encode("ascii")]:
        return False
    for revision in (base, merge):
        registry = json.loads(_git("show", f"{revision}:{_REGISTRY}"))
        skills = registry.get("skills") if isinstance(registry, dict) else None
        if not isinstance(skills, dict) or any(not isinstance(x, dict) for x in skills.values()):
            raise ValueError("Skill registry evidence is malformed")
        if any(entry.get("location", "").rstrip("/") == directory for entry in skills.values()):
            return False
    content = _git("show", f"{merge}:{path}")
    if len(content) > 128 * 1024 or b"\0" in content:
        return False
    text = content.decode("utf-8", errors="strict")
    return not text.startswith("---") and "**Status:** PROPOSED / DOCUMENTATION ONLY" in text


def classify(base: str, head: str, merge: str) -> tuple[str, list[str]]:
    """Return (lane, paths), raising if exact Git evidence cannot be verified."""
    if not all(_SHA.fullmatch(sha) for sha in (base, head, merge)):
        raise ValueError("Expected full base, head and merge commit IDs")
    if _git("rev-parse", "--is-shallow-repository").strip() != b"false":
        raise ValueError("Git history is shallow")
    if _git("rev-parse", "HEAD").strip() != merge.encode():
        raise ValueError("Checkout does not match the event merge SHA")
    parents = _git("rev-list", "--parents", "-n", "1", merge).split()
    if parents != [sha.encode() for sha in (merge, base, head)]:
        raise ValueError("Merge parents do not match the event base and head")
    merge_bases = _git("merge-base", "--all", base, head).split()
    if len(merge_bases) != 1:
        raise ValueError("Expected one unambiguous merge base")

    reviewed = _changes(merge_bases[0].decode("ascii"), head)
    integrated = _changes(base, merge)
    paths = sorted(reviewed.keys() | integrated.keys())
    # Comparing blob IDs as well as paths detects merge-time changes to the
    # reviewed content. Neither an empty diff nor ambiguous evidence qualifies.
    if not paths or reviewed != integrated:
        return "full", paths

    lanes = set()
    for path, (old_mode, new_mode, _, _, status) in reviewed.items():
        regular_change = (
            (old_mode, new_mode, status) == (b":000000", b"100644", b"A")
            or (old_mode, new_mode, status) == (b":100644", b"100644", b"M")
        )
        if not regular_change:
            return "full", paths
        if _POLICY.fullmatch(path):
            lanes.add("policy")
        elif _PROSE.fullmatch(path):
            lanes.add("docs")
        elif _SKILL_PROPOSAL.fullmatch(path) and status == b"A":
            try:
                eligible = _new_proposal(base, merge, path)
            except (ValueError, UnicodeError, TypeError, AttributeError):
                eligible = False
            if not eligible:
                return "full", paths
            lanes.add("skill-proposal")
        else:
            return "full", paths
    # Preserve the historical policy shadow classification, never its omission.
    if lanes <= {"docs", "policy"}:
        return ("policy" if "policy" in lanes else "docs"), paths
    return (next(iter(lanes)) if len(lanes) == 1 else "full"), paths


def scope_plan(base, head, merge):
    """An exact-Git CI plan, not WRE dependency or promotion authority."""
    lane, paths = classify(base, head, merge)
    gates = ["security", "lint", "holoindex_freshness"]
    if lane in {"docs", "skill-proposal"}:
        gates += ["markdown_structure_links"]
        if lane == "skill-proposal":
            gates += ["proposal_skill_governance"]
    else:
        gates += ["full_existing_ci", "wre_verification_contracts"]
    return dict(schema_version=SCHEMA, base_sha=base, head_sha=head,
                merge_sha=merge, lane=lane, paths=paths, required_gates=gates)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--merge", required=True)
    args = parser.parse_args()
    try:
        plan = scope_plan(args.base, args.head, args.merge)
    except ValueError as error:
        parser.exit(1, f"Merge scope unavailable: {error}\n")
    print(json.dumps(plan))


if __name__ == "__main__":
    main()
