"""Exercise the CI classifier against real Git commit and tree objects."""

import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_merge_scope import classify


_PROSE = "docs/ci-pilot/examples/sample.md"
_POLICY = "WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md"


class MergeScopeTest(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(temporary.name)
        self.git("init", "-q", "-b", "base")
        self.git("config", "user.name", "CI classifier test")
        self.git("config", "user.email", "ci-classifier@example.invalid")
        # Test the committed mode, independently of the filesystem mode.
        self.git("config", "core.filemode", "false")
        self.write(_PROSE, "# Initial prose\n")
        self.write("runtime.py", "pass\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD")
        self.git("checkout", "-qb", "topic")

    def git(self, *args):
        return subprocess.run(
            ["git", *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    def write(self, filename, content):
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def merge(self, *, replace=None):
        self.git("commit", "--allow-empty", "-qm", "topic")
        head = self.git("rev-parse", "HEAD")
        self.git("checkout", "-q", "base")
        self.git("merge", "--no-commit", "--no-ff", "topic")
        if replace:
            self.write(_PROSE, replace)
            self.git("add", _PROSE)
        self.git("commit", "-qm", "merge")
        return self.base, head, self.git("rev-parse", "HEAD")

    def test_inert_prose_addition_and_edit(self):
        extra = "docs/ci-pilot/examples/new-page.md"
        self.write(_PROSE, "# Updated prose\n")
        self.write(extra, "# New page\n")
        self.git("add", ".")
        self.assertEqual(classify(*self.merge()), ("docs", [extra, _PROSE]))

    def test_policy_precedes_prose(self):
        files = [
            _PROSE, _POLICY, "WSP_framework/ModLog.md", "WSP_knowledge/src/WSP_MASTER_INDEX.md",
            "AGENTS.md", ".agents/skills/example/SKILL.md",
        ]
        for filename in files:
            self.write(filename, "# Policy lane test\n")
        self.git("add", ".")
        self.assertEqual(classify(*self.merge()), ("policy", sorted(files)))

    def test_runtime_in_mixed_diff_forces_full(self):
        self.write(_PROSE, "# Updated prose\n")
        self.write("runtime.py", "print('runtime')\n")
        self.git("add", ".")
        self.assertEqual(classify(*self.merge()), ("full", [_PROSE, "runtime.py"]))

    def test_rename_forces_full_even_between_prose_paths(self):
        moved = "docs/ci-pilot/examples/relocated.md"
        self.git("mv", _PROSE, moved)
        self.assertEqual(classify(*self.merge()), ("full", [moved, _PROSE]))

    def test_mode_change_forces_full(self):
        self.git("update-index", "--chmod=+x", _PROSE)
        self.assertEqual(classify(*self.merge()), ("full", [_PROSE]))

    def test_merge_time_content_change_forces_full(self):
        self.write(_PROSE, "# Reviewed prose\n")
        self.git("add", _PROSE)
        self.assertEqual(
            classify(*self.merge(replace="# Unreviewed merge content\n")), ("full", [_PROSE])
        )

    def test_wrong_parent_or_checkout_raises(self):
        self.write(_PROSE, "# Updated prose\n")
        self.git("add", _PROSE)
        base, head, merge = self.merge()
        with self.assertRaisesRegex(ValueError, "parents"):
            classify(head, base, merge)
        with self.assertRaisesRegex(ValueError, "Checkout"):
            classify(base, head, head)

    def test_shallow_history_raises(self):
        self.write(_PROSE, "# Updated prose\n")
        self.git("add", _PROSE)
        base, head, merge = self.merge()
        Path(".git/shallow").write_text(f"{base}\n", encoding="ascii")
        with self.assertRaisesRegex(ValueError, "shallow"):
            classify(base, head, merge)


if __name__ == "__main__":
    unittest.main()
