"""Exercise the CI classifier against real Git commit and tree objects."""

import os
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_merge_scope import classify, scope_plan


_PROSE = "docs/ci-pilot/examples/sample.md"
_POLICY = "WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md"
_REGISTRY = "modules/infrastructure/wre_core/skillz/skills_registry_v2.json"
_SKILL = "modules/infrastructure/wre_core/skillz/new_proposal/SKILL.md"
_MARKER = "# Proposed learning\n\n**Status:** PROPOSED / DOCUMENTATION ONLY\n"


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
        self.write(_REGISTRY, json.dumps({"skills": {"registered": {
            "location": "modules/infrastructure/wre_core/skillz/registered"}}}))
        self.write(_SKILL.replace("new_proposal", "existing"), "# Existing instructions\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD")
        self.git("checkout", "-qb", "topic")

    def git(self, *args):
        return subprocess.run(
            ["git", *args], check=True, capture_output=True, text=True, timeout=20
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
        files = (
            _PROSE,
            "docs/ci-pilot/examples/new-page.md",
            "docs/audits/agent_git_workflow_impact_audit.md",
            "docs/audits/prose/scoped-audit-20261110.md",
        )
        for filename in files:
            self.write(filename, "# Updated prose\n")
        self.git("add", ".")
        self.assertEqual(classify(*self.merge()), ("docs", sorted(files)))

    def test_audit_governance_stays_full(self):
        governance = "docs/audits/governance/WSP97_TEST_INVENTORY_REUSE_GATE_WSP81_NOTIFICATION_20260826.md"
        audit = "docs/audits/prose/current-audit.md"
        for filename in (governance, audit):
            self.write(filename, "# Audit\n")
        self.git("add", ".")
        self.assertEqual(classify(*self.merge()), ("full", [governance, audit]))

    def test_interface_queue_stays_full(self):
        queue = "docs/audits/INTERFACE_CLOSURE_QUEUE_BG.md"
        self.write(queue, "# Interface closure queue\n")
        self.git("add", ".")
        self.assertEqual(classify(*self.merge()), ("full", [queue]))

    def test_audit_prose_cannot_add_agent_instructions(self):
        instructions = "docs/audits/prose/agents.md"
        self.write(instructions, "# Agent instructions\n")
        self.git("add", ".")
        self.assertEqual(classify(*self.merge()), ("full", [instructions]))

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

    def test_new_unregistered_proposal_gets_governance_and_security_gates(self):
        self.write(_SKILL, _MARKER)
        self.git("add", _SKILL)
        revisions = self.merge()
        plan = scope_plan(*revisions)
        self.assertEqual(plan["lane"], "skill-proposal")
        self.assertEqual(plan["paths"], [_SKILL])
        self.assertEqual([plan[k] for k in ("base_sha", "head_sha", "merge_sha")], list(revisions))
        self.assertIn("proposal_skill_governance", plan["required_gates"])
        self.assertIn("markdown_structure_links", plan["required_gates"])
        self.assertIn("security", plan["required_gates"])
        self.assertNotIn("full_existing_ci", plan["required_gates"])

    def test_existing_skill_edit_cannot_relabel_itself_as_proposal(self):
        existing = _SKILL.replace("new_proposal", "existing")
        self.write(existing, _MARKER)
        self.git("add", existing)
        self.assertEqual(classify(*self.merge()), ("full", [existing]))

    def test_registered_new_directory_is_not_a_proposal_lane(self):
        registered = _SKILL.replace("new_proposal", "registered")
        self.write(registered, _MARKER)
        self.git("add", registered)
        self.assertEqual(classify(*self.merge()), ("full", [registered]))

    def test_skill_with_executable_frontmatter_stays_full(self):
        self.write(_SKILL, "---\npromotion_state: production\n---\n" + _MARKER)
        self.git("add", _SKILL)
        self.assertEqual(classify(*self.merge()), ("full", [_SKILL]))

    def test_skill_with_sibling_or_mixed_docs_stays_full(self):
        self.write(_SKILL, _MARKER)
        self.write(_PROSE, "# Changed ordinary prose\n")
        self.git("add", ".")
        self.assertEqual(classify(*self.merge()), ("full", sorted([_SKILL, _PROSE])))

    def test_deleted_prose_stays_full(self):
        self.git("rm", _PROSE)
        self.assertEqual(classify(*self.merge()), ("full", [_PROSE]))

    def test_python_workflow_security_and_unknown_markdown_stay_full(self):
        paths = ["runtime.py", ".github/workflows/ci.yml", ".gitleaks.toml", "docs/runtime-contract.md"]
        for path in paths:
            self.write(path, "# Changed contract\n")
        self.git("add", ".")
        plan = scope_plan(*self.merge())
        self.assertEqual(plan["lane"], "full")
        self.assertEqual(plan["paths"], sorted(paths))
        self.assertIn("full_existing_ci", plan["required_gates"])
        self.assertIn("security", plan["required_gates"])

    def test_missing_git_object_and_abbreviated_sha_are_not_evidence(self):
        self.write(_PROSE, "# Updated prose\n")
        self.git("add", _PROSE)
        base, head, merge = self.merge()
        for bad in ("0" * 40, head[:12]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                classify(base, bad, merge)


class PipelineContracts(unittest.TestCase):
    """Execute the actual aggregation shell, not an imitation of its policy."""

    def setUp(self):
        self.workflow = (Path(__file__).resolve().parents[2] / "workflows/ci.yml").read_text(encoding="utf-8")
        self.jobs = dict(re.findall(r"^  ([\w-]+):\n(.*?)(?=^  [\w-]+:|\Z)", self.workflow, re.M | re.S))
        git_bash = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
        self.bash = str(git_bash) if os.name == "nt" and git_bash.is_file() else shutil.which("bash")
        self.assertIsNotNone(self.bash, "Bash is required for CI pipeline regression evidence")

    def aggregator(self, job):
        body = self.jobs[job]
        self.assertIn("needs: [merge-scope-pilot, ci-pipeline-regressions]", body)
        self.assertIn("if: always()", body)
        match = re.search(r"name: Require successful exact-SHA CI scope verification\n.*?        run: \|\n(.*?)(?=\n      -|\Z)", body, re.S)
        self.assertIsNotNone(match)
        return "\n".join(line[10:] for line in match[1].splitlines())

    def run_aggregation(self, script, **updates):
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            env = dict(os.environ, PLAN_RESULT="success", PIPELINE_RESULT="success", FAST_PATH="true", PLAN_BASE="a" * 40,
                       EVENT_BASE="a" * 40, PLAN_HEAD="b" * 40, EVENT_HEAD="b" * 40,
                       PLAN_MERGE="c" * 40, GITHUB_SHA="c" * 40,
                       RUNNER_TEMP=directory.as_posix(), TEST_PYTHON=Path(sys.executable).as_posix(),
                       GITHUB_OUTPUT=(directory / "output").as_posix(),
                       GITHUB_STEP_SUMMARY=(directory / "summary").as_posix())
            env.update(updates)
            (directory / "merge-scope.json").write_text(json.dumps({
                "schema_version": env.get("TEST_SCHEMA", "ci_merge_scope.v1")}), encoding="utf-8")
            result = subprocess.run([self.bash, "--noprofile", "--norc", "-c", script],
                                    env=env, capture_output=True, timeout=10)
            output = (directory / "output").read_text() if (directory / "output").exists() else ""
            return result.returncode, output

    def test_absent_pending_failed_cancelled_or_stale_plan_never_success(self):
        for job in ("test", "wre-verification-contracts"):
            script = self.aggregator(job)
            for status in ("", "queued", "in_progress", "failure", "cancelled", "skipped"):
                with self.subTest(job=job, status=status):
                    self.assertEqual(self.run_aggregation(script, PLAN_RESULT=status)[0], 1)
                    self.assertEqual(self.run_aggregation(script, PIPELINE_RESULT=status)[0], 1)
            for field in ("PLAN_BASE", "PLAN_HEAD", "PLAN_MERGE", "FAST_PATH"):
                with self.subTest(job=job, field=field):
                    self.assertEqual(self.run_aggregation(script, **{field: "stale"})[0], 1)
            self.assertEqual(self.run_aggregation(script)[0], 0)
            code, output = self.run_aggregation(script, FAST_PATH="false")
            self.assertEqual(code, 0)
            self.assertNotIn("lane=docs", output)

    def test_server_opt_in_schema_and_live_base_control_publication(self):
        match = re.search(r"name: Publish validated scope after all applicable gates\n.*?        run: \|\n(.*?)(?=\n  [\w-]+:|\Z)",
                          self.jobs["merge-scope-pilot"], re.S)
        self.assertIsNotNone(match)
        script = "\n".join(line[10:] for line in match[1].splitlines())
        # Stub only external Git lookup and Python's executable name; execute
        # the actual publication condition and schema reader unchanged.
        script = ('git() { printf "%s\\trefs/heads/main\\n" "$LIVE_BASE"; return "$GIT_STATUS"; };\n'
                  'python3() { "$TEST_PYTHON" "$@"; };\n' + script)
        defaults = dict(LANE="docs", PR_BASE="a" * 40, LIVE_BASE="a" * 40,
                        BASE_REF="main", FAST_PATH_BASE="main", GIT_STATUS="0")
        for updates, expected in (
            ({}, "true"), ({"LANE": "skill-proposal"}, "true"),
            ({"FAST_PATH_BASE": ""}, "false"), ({"FAST_PATH_BASE": "another-base"}, "false"),
            ({"TEST_SCHEMA": ""}, "false"), ({"TEST_SCHEMA": "stale.v0"}, "false"),
            ({"LANE": ""}, "false"), ({"LANE": "full"}, "false"),
        ):
            with self.subTest(updates=updates):
                code, output = self.run_aggregation(script, **(defaults | updates))
                self.assertEqual(code, 0)
                self.assertEqual(output.strip(), "fast_path=" + expected)
        for updates in ({"LIVE_BASE": "b" * 40}, {"GIT_STATUS": "128"}):
            with self.subTest(updates=updates):
                code, output = self.run_aggregation(script, **(defaults | updates))
                self.assertNotEqual(code, 0)
                self.assertNotIn("fast_path=true", output)

    def test_trusted_selection_and_publish_order_preserve_security(self):
        planner = self.jobs["merge-scope-pilot"]
        self.assertIn('git --no-replace-objects show "$PR_BASE:.github/scripts/$script"', planner)
        self.assertIn('python3 -I -B "$RUNNER_TEMP/trusted-ci/ci_merge_scope.py"', planner)
        self.assertNotIn("unittest", planner)
        self.assertNotIn("scripts/generate_codex", planner)
        self.assertNotIn("python3 -c", planner)
        self.assertNotIn("continue-on-error", planner)
        self.assertLess(planner.index("Check proposal-only Skill"), planner.index("id: validated"))
        self.assertIn('"$live_base" == "$PR_BASE"', planner)
        self.assertIn('"$FAST_PATH_BASE" !=', planner)
        self.assertIn('"$FAST_PATH_BASE" == "$BASE_REF"', planner)
        self.assertIn('"$schema" == ci_merge_scope.v1', planner)
        self.assertNotIn("if:", self.jobs["security"])
        for job in ("lint", "security", "holoindex_freshness", "gotjunk-backend-security", "redteam_observation"):
            self.assertNotIn("needs: merge-scope-pilot", self.jobs[job])
        self.assertIn("branches: [main]", self.workflow)


if __name__ == "__main__":
    unittest.main()
