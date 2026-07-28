"""Tests for WRE_INDEPENDENT_EVIDENCE_PRODUCER_RUNTIME_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_work_authority_digest import (
    canonical_work_authority_digest,
)
from modules.infrastructure.wre_core.src import wre_independent_evidence_producer_runtime as ep
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
    verify_autonomous_slice_runtime,
)
from modules.infrastructure.wre_core.src.wre_independent_evidence_producer_runtime import (
    EVIDENCE_PRODUCER_ACCEPT,
    EVIDENCE_PRODUCER_REJECT,
    FAIL_CHECK_COMMAND_REJECTED,
    FAIL_CHECK_FAILED,
    FAIL_EXPLICIT_REQUEST,
    FAIL_HEAD_MISMATCH,
    FAIL_HOLOINDEX_EVIDENCE,
    FAIL_PROTECTED_SURFACE,
    FAIL_SCOPE_VIOLATION,
    FAIL_SECRET_IN_DIFF,
    FAIL_WORKTREE_INSIDE_REPO,
    CommandResult,
    produce_independent_slice_evidence,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "infrastructure"
    / "wre_core"
    / "src"
    / "wre_independent_evidence_producer_runtime.py"
)

BASE = "b" * 40
HEAD = "a" * 40
WORK_ORDER_ID = "wo-independent-evidence-001"
SLICE_NAME = "WRE_INDEPENDENT_EVIDENCE_PRODUCER_RUNTIME_PHASE1"
CHANGED = "modules/foundups/paccess_001/README.md"


class FakeRunner:
    def __init__(
        self,
        *,
        head: str = HEAD,
        changed_paths: str = CHANGED + "\n",
        diff_text: str | None = None,
        diff_truncated: bool = False,
        check_returncode: int = 0,
    ) -> None:
        self.head = head
        self.changed_paths = changed_paths
        self.diff_text = diff_text if diff_text is not None else (
            f"diff --git a/{CHANGED} b/{CHANGED}\n"
            f"+++ b/{CHANGED}\n"
            "+independent evidence producer fixture\n"
        )
        self.diff_truncated = diff_truncated
        self.check_returncode = check_returncode
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv, *, cwd: Path, timeout_s: int) -> CommandResult:
        _ = (cwd, timeout_s)
        argv_tuple = tuple(argv)
        self.calls.append(argv_tuple)
        if argv_tuple == ("git", "rev-parse", "HEAD"):
            return CommandResult(returncode=0, stdout=self.head + "\n")
        if argv_tuple[:3] == ("git", "diff", "--name-only"):
            return CommandResult(returncode=0, stdout=self.changed_paths)
        if argv_tuple[:3] == ("git", "diff", "--unified=0"):
            return CommandResult(returncode=0, stdout=self.diff_text, stdout_truncated=self.diff_truncated)
        return CommandResult(
            returncode=self.check_returncode,
            stdout="tests ok\n" if self.check_returncode == 0 else "",
            stderr="" if self.check_returncode == 0 else "tests failed\n",
        )


def _request(tmp_path: Path, **overrides):
    repo = tmp_path / "repo"
    worktree = tmp_path / "worktree"
    repo.mkdir(exist_ok=True)
    worktree.mkdir(exist_ok=True)
    payload = {
        "explicit_evidence_production_requested": True,
        "work_order_id": WORK_ORDER_ID,
        "slice_name": SLICE_NAME,
        "worker_id": "worker:author",
        "verifier_id": "worker:verifier",
        "repo_root": str(repo),
        "worktree_path": str(worktree),
        "operation_cwd": str(worktree),
        "base_sha": BASE,
        "head_sha": HEAD,
        "allowed_path_patterns": ["modules/foundups/paccess_001/**"],
        "forbidden_path_patterns": ["**/.env", "**/secrets/**"],
        "expected_changed_paths": [CHANGED],
        "required_checks": [
            {
                "name": "pytest",
                "argv": ["python", "-m", "pytest", "modules/foundups/paccess_001/tests", "-q"],
                "timeout_s": 30,
            }
        ],
        "holoindex_evidence": {
            "index_gap_detected": False,
            "retrieval_quality": "HIGH",
            "holoindex_freshness_receipt_digest": "sha256:" + "1" * 64,
        },
    }
    payload.update(overrides)
    return payload


def _verifier_request(produced):
    work_authority = {
        "authority_id": "authority-independent-evidence",
        "work_order_id": WORK_ORDER_ID,
    }
    return {
        "work_order_id": WORK_ORDER_ID,
        "slice_name": SLICE_NAME,
        "worker_id": "worker:author",
        "verifier_id": "worker:verifier",
        "assurance_reservation_id": "assurance-reservation-independent-evidence",
        "assurance_reservation_digest": "sha256:" + "6" * 64,
        "verifier_task_id": "reddog-worker-dispatch-independent-verifier",
        "base_sha": BASE,
        "head_sha": HEAD,
        "allowed_path_patterns": ["modules/foundups/paccess_001/**"],
        "expected_changed_paths": [CHANGED],
        "forbidden_path_patterns": ["**/.env", "**/secrets/**"],
        "diff_evidence": produced.diff_evidence,
        "test_evidence": produced.test_evidence,
        "signed_authority": {
            **work_authority,
            "accepted": True,
            "signature_gate_digest": canonical_work_authority_digest(work_authority),
        },
        "signed_receipt_chain": {
            "accepted": True,
            "terminal_receipt_hash": "sha256:" + "3" * 64,
        },
        "worktree_receipt": {
            "accepted": True,
            "receipt_id": "sha256:" + "4" * 64,
        },
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": "sha256:" + "5" * 64,
        },
        "pattern_memory_write_performed": False,
        "draft_pr_published": False,
        "merge_performed": False,
    }


def test_produces_verifier_compatible_machine_evidence(tmp_path: Path) -> None:
    runner = FakeRunner()
    result = produce_independent_slice_evidence(_request(tmp_path), runner=runner)

    assert result.accepted is True
    assert result.decision == EVIDENCE_PRODUCER_ACCEPT
    assert result.diff_evidence["source"] == "machine_derived"
    assert result.diff_evidence["red_dog_prose_source"] is False
    assert result.diff_evidence["changed_paths"] == [CHANGED]
    assert result.test_evidence["required_checks"][0]["conclusion"] == "success"
    assert result.receipt.no_holoindex_reindex_performed is True
    assert ("git", "rev-parse", "HEAD") in runner.calls

    verifier = verify_autonomous_slice_runtime(_verifier_request(result))
    assert verifier.accepted is True
    assert verifier.decision == AUTONOMOUS_SLICE_VERIFIER_ACCEPT


def test_requires_explicit_request_before_runner_calls(tmp_path: Path) -> None:
    runner = FakeRunner()
    req = _request(tmp_path, explicit_evidence_production_requested=False)

    result = produce_independent_slice_evidence(req, runner=runner)

    assert result.accepted is False
    assert result.decision == EVIDENCE_PRODUCER_REJECT
    assert FAIL_EXPLICIT_REQUEST in result.rejection_reasons
    assert runner.calls == []


def test_rejects_worktree_inside_repo_before_runner_calls(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    worktree = repo / "nested-worktree"
    worktree.mkdir(parents=True)
    runner = FakeRunner()
    req = _request(tmp_path, repo_root=str(repo), worktree_path=str(worktree), operation_cwd=str(worktree))

    result = produce_independent_slice_evidence(req, runner=runner)

    assert result.accepted is False
    assert FAIL_WORKTREE_INSIDE_REPO in result.rejection_reasons
    assert runner.calls == []


def test_head_sha_mismatch_rejects_without_checks(tmp_path: Path) -> None:
    runner = FakeRunner(head="c" * 40)

    result = produce_independent_slice_evidence(_request(tmp_path), runner=runner)

    assert result.accepted is False
    assert FAIL_HEAD_MISMATCH in result.rejection_reasons
    assert not any(call[0] == "python" for call in runner.calls)


def test_scope_violation_blocks_test_execution(tmp_path: Path) -> None:
    runner = FakeRunner(changed_paths=".github/workflows/deploy.yml\n")
    req = _request(tmp_path, expected_changed_paths=[".github/workflows/deploy.yml"])

    result = produce_independent_slice_evidence(req, runner=runner)

    assert result.accepted is False
    assert FAIL_SCOPE_VIOLATION in result.rejection_reasons
    assert FAIL_PROTECTED_SURFACE in result.rejection_reasons
    assert not any(call[0] == "python" for call in runner.calls)


def test_secret_in_diff_rejects_and_blocks_test_execution(tmp_path: Path) -> None:
    runner = FakeRunner(diff_text=f"+++ b/{CHANGED}\n+token=abc123\n")

    result = produce_independent_slice_evidence(_request(tmp_path), runner=runner)

    assert result.accepted is False
    assert FAIL_SECRET_IN_DIFF in result.rejection_reasons
    assert not any(call[0] == "python" for call in runner.calls)


def test_truncated_diff_rejects_and_blocks_test_execution(tmp_path: Path) -> None:
    runner = FakeRunner(diff_truncated=True)

    result = produce_independent_slice_evidence(_request(tmp_path), runner=runner)

    assert result.accepted is False
    assert ep.FAIL_DIFF_EVIDENCE in result.rejection_reasons
    assert not any(call[0] == "python" for call in runner.calls)


def test_unknown_check_command_rejected(tmp_path: Path) -> None:
    req = _request(
        tmp_path,
        required_checks=[{"name": "bad", "argv": ["powershell", "-Command", "Write-Host ok"]}],
    )

    result = produce_independent_slice_evidence(req, runner=FakeRunner())

    assert result.accepted is False
    assert FAIL_CHECK_COMMAND_REJECTED in result.rejection_reasons


def test_failed_required_check_rejects(tmp_path: Path) -> None:
    result = produce_independent_slice_evidence(_request(tmp_path), runner=FakeRunner(check_returncode=1))

    assert result.accepted is False
    assert FAIL_CHECK_FAILED in result.rejection_reasons
    assert result.test_evidence["required_checks"][0]["conclusion"] == "failure"


def test_holoindex_gap_rejects_before_runner_calls(tmp_path: Path) -> None:
    runner = FakeRunner()
    req = _request(
        tmp_path,
        holoindex_evidence={
            "index_gap_detected": True,
            "retrieval_quality": "INDEX_GAP",
            "holoindex_freshness_receipt_digest": "sha256:" + "1" * 64,
        },
    )

    result = produce_independent_slice_evidence(req, runner=runner)

    assert result.accepted is False
    assert FAIL_HOLOINDEX_EVIDENCE in result.rejection_reasons
    assert runner.calls == []


def test_ast_boundary_no_github_pr_merge_patternmemory_or_holoindex_writes() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {"requests", "urllib", "http", "socket", "github", "ghapi", "holo_index"}
    banned_import_fragments = {"pattern_memory", "reddog_verified_draft_pr_publish"}
    banned_calls = {"eval", "exec", "compile", "__import__"}
    banned_attrs = {"unlink", "remove", "rmdir", "rename", "Popen", "check_call", "check_output"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
                assert all(fragment not in alias.name for fragment in banned_import_fragments)
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
            assert all(fragment not in node.module for fragment in banned_import_fragments)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs
    src = MODULE_PATH.read_text(encoding="utf-8")
    assert "shell=False" in src
    assert "subprocess.run(" in src
