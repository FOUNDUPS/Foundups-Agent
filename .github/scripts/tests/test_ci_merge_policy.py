"""Regression coverage for changed WSP mirror and catalog checks."""

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_merge_policy import (
    FRAMEWORK, INDEX, KNOWLEDGE, SKILL_REGISTRY, policy_issues, proposal_skill_issues,
)


_PROPOSAL = "modules/infrastructure/wre_core/skillz/example_proposal/SKILL.md"
_DOCUMENT = """# Proposed capability

**Status:** PROPOSED / DOCUMENTATION ONLY

## Intent and boundary
Describe an idea; this document grants no runtime or effect authority.

## Governance and source of truth
WSP_00, WSP_15, WSP_48, WSP_95, WSP_97 and WSP_110 remain authoritative.

## Acceptance and learning proof
Independent outcome and regression evidence precedes any admission request.

## Handoff and next action
The existing module owner reviews a separately authorized implementation.
"""


class PolicyChecks(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.addCleanup(os.chdir, Path.cwd())
        os.chdir(directory.name)
        FRAMEWORK.mkdir(parents=True)
        KNOWLEDGE.mkdir(parents=True)

    def write_pair(self, name, text):
        for root in (FRAMEWORK, KNOWLEDGE):
            (root / name).write_text(text, encoding="utf-8")

    def test_changed_mirror_matches_and_unrelated_drift_is_ignored(self):
        self.write_pair(INDEX.name, "| WSP 34 |")
        name = "WSP_34_Git_Operations_Protocol.md"
        self.write_pair(name, "paired")
        (FRAMEWORK / "WSP_MODULE_VIOLATIONS.md").write_text("old drift", encoding="utf-8")
        self.assertEqual(policy_issues("base", [str(FRAMEWORK / name)]), [])

        (KNOWLEDGE / name).write_text("different", encoding="utf-8")
        self.assertEqual(
            policy_issues("base", [str(FRAMEWORK / name)]),
            [f"WSP mirror mismatch: {name}"],
        )

    def test_new_protocol_requires_unique_file_and_index_entry(self):
        self.write_pair(INDEX.name, "| WSP 34 |")
        name = "WSP_110_New_Protocol.md"
        self.write_pair(name, "paired")
        self.write_pair("WSP_110_Duplicate.md", "another")
        self.assertEqual(
            policy_issues("base", [str(FRAMEWORK / name)]),
            [
                "WSP 110 must have exactly one canonical protocol file",
                "WSP 110 is missing from the master index",
            ],
        )

    def test_changed_index_cannot_drop_existing_protocol_or_reuse_next_number(self):
        self.write_pair("WSP_34_Git_Operations_Protocol.md", "paired")
        self.write_pair(INDEX.name, "| WSP 35 |\n- **Next Available Number**: WSP 35")
        previous = "| WSP 34 |\n- **Next Available Number**: WSP 35"
        with patch("ci_merge_policy.subprocess.check_output", return_value=previous):
            self.assertEqual(
                policy_issues("base", [str(INDEX)]),
                [
                    "WSP master index has an incorrect next available number",
                    "WSP 34 is missing from the master index",
                ],
            )


class ProposalSkillChecks(unittest.TestCase):
    """Real Git base evidence, synthetic proposals, and no runtime imports."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.addCleanup(os.chdir, Path.cwd())
        os.chdir(directory.name)
        self.git("init", "-q", "-b", "base")
        self.git("config", "user.name", "CI proposal test")
        self.git("config", "user.email", "ci-proposal@example.invalid")
        self.registry({})
        self.commit_base()
        self.write(_PROPOSAL, _DOCUMENT)

    def git(self, *args):
        return subprocess.run(
            ["git", *args], check=True, capture_output=True, text=True, timeout=10,
        ).stdout.strip()

    def write(self, filename, text):
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def registry(self, skills):
        self.write(SKILL_REGISTRY, json.dumps({"version": "2.0", "skills": skills}))

    def commit_base(self):
        self.git("add", ".")
        self.git("commit", "--allow-empty", "-qm", "base fixture")
        self.base = self.git("rev-parse", "HEAD")

    def issues(self):
        return proposal_skill_issues(self.base, [_PROPOSAL])

    def test_new_proposal_and_canonical_skillz_name_are_documentation_only(self):
        self.assertEqual(self.issues(), [])
        canonical = Path(_PROPOSAL).with_name("SKILLz.md")
        Path(_PROPOSAL).rename(canonical)
        self.assertEqual(proposal_skill_issues(self.base, [canonical.as_posix()]), [])

    def test_existing_skill_directory_cannot_be_relabelled_as_a_new_proposal(self):
        self.commit_base()
        self.write(_PROPOSAL, _DOCUMENT.replace("Describe an idea", "A revised idea"))
        self.assertIn("Existing Skill directories", "\n".join(self.issues()))

    def test_actual_proposal_status_with_explicit_nonactivation_suffix(self):
        status = "**Status:** PROPOSED / DOCUMENTATION ONLY"
        self.write(_PROPOSAL, _DOCUMENT.replace(
            status, status + " — no runtime, account, credential, trial, or worker activation."
        ))
        self.assertEqual(self.issues(), [])

    def test_registered_candidate_requires_full_verification(self):
        for location in (str(Path(_PROPOSAL).parent.as_posix()), _PROPOSAL):
            with self.subTest(location=location):
                self.registry({"alias": {"location": location}})
                self.assertIn("Registered Skill", "\n".join(self.issues()))

    def test_removed_base_registration_does_not_downgrade_verification(self):
        Path(_PROPOSAL).unlink()
        self.registry({"alias": {"location": Path(_PROPOSAL).parent.as_posix()}})
        self.commit_base()
        self.registry({})
        self.write(_PROPOSAL, _DOCUMENT)
        self.assertIn("Registered Skill", "\n".join(self.issues()))

    def test_registered_name_collision_requires_full_verification(self):
        self.registry({"example_proposal": {"location": ".claude/skills/another"}})
        self.assertIn("Registered Skill", "\n".join(self.issues()))

    def test_adjacent_executor_manifest_alternative_and_unknown_files_are_rejected(self):
        for name in ("executor.py", "SKILL_MANIFEST.json", "SKILLz.md", "README.md"):
            with self.subTest(name=name):
                adjacent = Path(_PROPOSAL).with_name(name)
                adjacent.write_text("synthetic fixture", encoding="utf-8")
                self.assertIn("Adjacent files", "\n".join(self.issues()))
                adjacent.unlink()

    def test_missing_malformed_and_unknown_registry_evidence_fails_closed(self):
        for text in ("{", "{}", '{"skills": []}', '{"skills": {"bad": {}}}',
                     '{"skills": {"bad": {"location": "../outside"}}}'):
            with self.subTest(text=text):
                self.write(SKILL_REGISTRY, text)
                self.assertIn("registry evidence is unavailable", "\n".join(self.issues()))
        SKILL_REGISTRY.unlink()
        self.assertIn("registry evidence is unavailable", "\n".join(self.issues()))

    def test_missing_base_registry_and_unknown_base_are_not_success(self):
        SKILL_REGISTRY.unlink()
        Path(_PROPOSAL).unlink()
        self.commit_base()
        self.registry({})
        self.write(_PROPOSAL, _DOCUMENT)
        self.assertIn("registry evidence is unavailable", "\n".join(self.issues()))
        self.assertTrue(proposal_skill_issues("f" * 40, [_PROPOSAL]))
        self.assertTrue(proposal_skill_issues("main", [_PROPOSAL]))

    def test_frontmatter_including_prototype_or_production_is_outside_pilot(self):
        for state in ("prototype", "production", "proposed"):
            with self.subTest(state=state):
                self.write(_PROPOSAL, f"---\npromotion_state: {state}\n---\n" + _DOCUMENT)
                self.assertIn("frontmatter requires full", "\n".join(self.issues()))

    def test_required_status_sections_and_governance_references_are_enforced(self):
        for before, after in (
            ("**Status:** PROPOSED / DOCUMENTATION ONLY", "**Status:** PRODUCTION"),
            ("## Intent and boundary", "## A different heading"),
            ("WSP_95", "Unspecified policy"),
            ("Describe an idea; this document grants no runtime or effect authority.", ""),
        ):
            with self.subTest(before=before):
                self.write(_PROPOSAL, _DOCUMENT.replace(before, after))
                self.assertTrue(self.issues())

    def test_comments_or_fenced_examples_cannot_supply_the_document_schema(self):
        for text in ("```markdown\n" + _DOCUMENT + "```\n", "<!--\n" + _DOCUMENT + "-->\n",
                     "<!--\n" + _DOCUMENT):
            with self.subTest(text=text[:10]):
                self.write(_PROPOSAL, text)
                self.assertTrue(self.issues())

    def test_invalid_encoding_nul_and_oversized_documents_are_rejected(self):
        for raw in (b"\xff", _DOCUMENT.encode() + b"\0", b"x" * (128 * 1024 + 1)):
            with self.subTest(size=len(raw)):
                Path(_PROPOSAL).write_bytes(raw)
                self.assertTrue(self.issues())

    def test_link_component_and_nonregular_document_are_rejected(self):
        original = Path.lstat
        for target, mode in (
            (Path(_PROPOSAL).parent, stat.S_IFLNK),
            (Path(_PROPOSAL), stat.S_IFDIR),
        ):
            with self.subTest(target=target):
                def synthetic_stat(path):
                    return SimpleNamespace(st_mode=mode) if path == target else original(path)
                with patch.object(Path, "lstat", autospec=True, side_effect=synthetic_stat):
                    self.assertTrue(self.issues())

    def test_empty_unknown_and_mixed_paths_are_rejected(self):
        for paths in ([], [_PROPOSAL, "runtime.py"], ["../SKILL.md"], [".agents/skills/test/SKILL.md"]):
            with self.subTest(paths=paths):
                self.assertTrue(proposal_skill_issues(self.base, paths))


if __name__ == "__main__":
    unittest.main()
