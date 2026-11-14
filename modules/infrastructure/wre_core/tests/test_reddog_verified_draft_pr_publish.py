"""Tests for REDDOG_VERIFIED_DRAFT_PR_PUBLISH_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.infrastructure.wre_core.src import reddog_verified_draft_pr_publish as publish
from modules.infrastructure.wre_core.src import wre_autonomous_slice_verifier_runtime as verify

HEAD_SHA = "a" * 40
PATH = "modules/communication/moltbot_bridge/tests/fixtures/reddog_pilot/README.md"


class FakeRunner:
    def __init__(self, *, push_ok: bool = True, pr_url: str | None = None) -> None:
        self.push_ok = push_ok
        self.pr_url = pr_url or "https://github.com/FOUNDUPS/Foundups-Agent/pull/1000"
        self.calls: list = []

    def push_branch(self, *, worktree_path: Path, branch_name: str):
        self.calls.append(("push_branch", str(worktree_path), branch_name))
        return {"ok": self.push_ok, "stdout": "", "stderr": "" if self.push_ok else "fail"}

    def create_draft_pr(self, *, branch_name: str, base_branch: str, title: str, body: str):
        self.calls.append(("create_draft_pr", branch_name, base_branch, title, body))
        if self.pr_url == "RAISE":
            raise RuntimeError("draft pr failed")
        return self.pr_url


def _verifier_result(*, accepted: bool = True) -> dict:
    return {
        "decision": (
            verify.AUTONOMOUS_SLICE_VERIFIER_ACCEPT
            if accepted
            else verify.AUTONOMOUS_SLICE_VERIFIER_REJECT
        ),
        "accepted": accepted,
        "receipt": {
            "receipt_id": "wre_slice_verify_1234",
            "work_order_id": "wo-publish-1",
            "slice_name": "REDDOG_VERIFIED_DRAFT_PR_PUBLISH_PHASE1",
            "worker_id": "worker:author",
            "verifier_id": "worker:verifier",
            "head_sha": HEAD_SHA,
            "changed_paths": [PATH],
        },
    }


def _verifier_result_with_runtime_binding() -> dict:
    result = _verifier_result()
    result["receipt"]["model_runtime_binding_receipt_id"] = "reddog_model_runtime_binding:test"
    result["receipt"]["model_runtime_binding_digest"] = "sha256:" + ("1" * 64)
    return result


def valid_request() -> dict:
    return {
        "verifier_result": _verifier_result(),
        "pre_publish_branch_head_sha": HEAD_SHA,
        "branch_name": "feat/reddog-verified-draft-pr-publish-phase1",
        "base_branch": "main",
        "pr_title": "feat(reddog): verified draft pr publish",
        "pr_body": "Verified by WRE autonomous slice verifier.",
        "worktree_path": "O:/tmp/reddog-worker",
        "draft_pr_only": True,
        "mark_ready": False,
        "merge": False,
    }


def assert_reject(req: dict, code: str) -> None:
    runner = FakeRunner()
    result = publish.publish_verified_draft_pr(req, runner=runner)

    assert result.accepted is False
    assert result.decision == publish.VERIFIED_DRAFT_PR_PUBLISH_REJECT
    assert code in result.rejection_reasons
    assert code in result.receipt.rejection_reasons
    assert result.no_ready_performed is True
    assert result.no_merge_performed is True
    assert result.no_pattern_memory_write_performed is True


def test_publishes_draft_pr_only_after_accepted_verifier_result() -> None:
    runner = FakeRunner()
    result = publish.publish_verified_draft_pr(valid_request(), runner=runner)

    assert result.accepted is True
    assert result.decision == publish.VERIFIED_DRAFT_PR_PUBLISH_ACCEPT
    assert result.rejection_reasons == []
    assert result.receipt.draft_pr_url.endswith("/pull/1000")
    assert result.receipt.verified_head_sha == HEAD_SHA
    assert result.receipt.changed_paths == [PATH]
    assert result.receipt.model_runtime_binding_receipt_id is None
    assert result.receipt.model_runtime_binding_digest == ""
    assert result.receipt.no_ready_performed is True
    assert result.receipt.no_merge_performed is True
    assert result.receipt.no_pattern_memory_write_performed is True
    assert [call[0] for call in runner.calls] == ["push_branch", "create_draft_pr"]


def test_publish_receipt_carries_verifier_model_runtime_binding() -> None:
    req = valid_request()
    req["verifier_result"] = _verifier_result_with_runtime_binding()

    result = publish.publish_verified_draft_pr(req, runner=FakeRunner())

    assert result.accepted is True
    assert (
        result.receipt.model_runtime_binding_receipt_id
        == "reddog_model_runtime_binding:test"
    )
    assert result.receipt.model_runtime_binding_digest == "sha256:" + ("1" * 64)


def test_rejects_publish_runtime_binding_override() -> None:
    req = valid_request()
    req["verifier_result"] = _verifier_result_with_runtime_binding()
    req["model_runtime_binding_receipt_id"] = "reddog_model_runtime_binding:test"
    req["model_runtime_binding_digest"] = "sha256:" + ("2" * 64)
    runner = FakeRunner()

    result = publish.publish_verified_draft_pr(req, runner=runner)

    assert result.accepted is False
    assert publish.FAIL_MODEL_RUNTIME_BINDING in result.rejection_reasons
    assert runner.calls == []


def test_rejects_unaccepted_or_malformed_verifier_result_before_runner() -> None:
    req = valid_request()
    req["verifier_result"] = _verifier_result(accepted=False)
    runner = FakeRunner()
    result = publish.publish_verified_draft_pr(req, runner=runner)

    assert result.accepted is False
    assert publish.FAIL_VERIFIER_NOT_ACCEPTED in result.rejection_reasons
    assert runner.calls == []


def test_rejects_head_mismatch_before_push() -> None:
    req = valid_request()
    req["pre_publish_branch_head_sha"] = "b" * 40
    runner = FakeRunner()
    result = publish.publish_verified_draft_pr(req, runner=runner)

    assert result.accepted is False
    assert publish.FAIL_HEAD_MISMATCH in result.rejection_reasons
    assert runner.calls == []


def test_rejects_bad_branch_policy() -> None:
    req = valid_request()
    req["branch_name"] = "main"
    assert_reject(req, publish.FAIL_BRANCH_POLICY)

    req = valid_request()
    req["base_branch"] = "release"
    assert_reject(req, publish.FAIL_BRANCH_POLICY)


def test_rejects_non_draft_or_ready_merge_request() -> None:
    req = valid_request()
    req["draft_pr_only"] = False
    assert_reject(req, publish.FAIL_DRAFT_ONLY)

    req = valid_request()
    req["mark_ready"] = True
    assert_reject(req, publish.FAIL_DRAFT_ONLY)

    req = valid_request()
    req["merge"] = True
    assert_reject(req, publish.FAIL_DRAFT_ONLY)


def test_rejects_missing_metadata_or_secret_in_body() -> None:
    req = valid_request()
    req["pr_title"] = ""
    assert_reject(req, publish.FAIL_PR_METADATA)

    req = valid_request()
    req["verifier_result"]["receipt"]["changed_paths"] = []
    assert_reject(req, publish.FAIL_PR_METADATA)

    req = valid_request()
    req["pr_body"] = "api_key = leak"
    assert_reject(req, publish.FAIL_SECRET_IN_PR_METADATA)


def test_rejects_push_failure_without_creating_pr() -> None:
    runner = FakeRunner(push_ok=False)
    result = publish.publish_verified_draft_pr(valid_request(), runner=runner)

    assert result.accepted is False
    assert result.rejection_reasons == [publish.FAIL_PUSH_BRANCH]
    assert [call[0] for call in runner.calls] == ["push_branch"]


def test_rejects_create_draft_pr_exception() -> None:
    runner = FakeRunner(pr_url="RAISE")
    result = publish.publish_verified_draft_pr(valid_request(), runner=runner)

    assert result.accepted is False
    assert result.rejection_reasons == [publish.FAIL_CREATE_DRAFT_PR]
    assert [call[0] for call in runner.calls] == ["push_branch", "create_draft_pr"]


def test_rejects_non_github_pr_url() -> None:
    runner = FakeRunner(pr_url="not-a-pr-url")
    result = publish.publish_verified_draft_pr(valid_request(), runner=runner)

    assert result.accepted is False
    assert result.rejection_reasons == [publish.FAIL_PR_URL]


def test_receipt_is_deterministic_and_json_serializable() -> None:
    first = publish.publish_verified_draft_pr(valid_request(), runner=FakeRunner())
    second = publish.publish_verified_draft_pr(valid_request(), runner=FakeRunner())

    assert first.receipt.receipt_id == second.receipt.receipt_id
    dumped = json.dumps(first.to_dict(), sort_keys=True)
    assert "verified_draft_pr_" in dumped
    assert first.receipt.no_merge_performed is True
    assert first.no_merge_performed is True


def test_ast_boundary_no_direct_git_gh_merge_or_memory_write() -> None:
    path = Path("modules/infrastructure/wre_core/src/reddog_verified_draft_pr_publish.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = set()
    calls = set()
    constants = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            constants.append(node.value.lower())

    forbidden_imports = {
        "os",
        "subprocess",
        "socket",
        "requests",
        "sqlite3",
        "modules.infrastructure.wre_core.src.pattern_memory",
    }
    forbidden_calls = {
        "open",
        "eval",
        "exec",
        "system",
        "popen",
        "run",
        "check_call",
        "check_output",
        "store_outcome",
        "merge_pr",
        "mark_ready",
    }
    forbidden_strings = ("gh pr ready", "gh pr merge", "--merge", "store_outcome(")

    assert imports.isdisjoint(forbidden_imports)
    assert calls.isdisjoint(forbidden_calls)
    assert not any(item in text for text in constants for item in forbidden_strings)
