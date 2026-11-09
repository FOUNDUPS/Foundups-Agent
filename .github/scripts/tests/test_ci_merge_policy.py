"""Regression coverage for changed WSP mirror and catalog checks."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_merge_policy import FRAMEWORK, INDEX, KNOWLEDGE, policy_issues


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


if __name__ == "__main__":
    unittest.main()
