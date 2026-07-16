"""Tests for REDDOG_BOUNDED_ARTIFACT_GENERATION_BINDING_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_bounded_artifact_generation_runtime import (
    ARTIFACT_GENERATION_ACCEPT,
    ARTIFACT_GENERATION_REJECT,
    FAIL_ARTIFACTS_MISMATCH,
    FAIL_AUTHORITY,
    FAIL_CONTENT_INVALID,
    FAIL_EXPLICIT_REQUEST,
    FAIL_HOLOINDEX_EVIDENCE,
    FAIL_PLANNED_ARTIFACTS,
    FAIL_RECEIPT_CHAIN,
    FAIL_RUNNER_MISSING,
    FAIL_RUNNER_REJECTED,
    FAIL_SECRET_IN_CONTENT,
    ArtifactGenerationModelResult,
    generate_bounded_artifact_contents,
)
from modules.communication.moltbot_bridge.src import reddog_bounded_artifact_generation_runtime


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_bounded_artifact_generation_runtime.py"
)
ARTIFACT = "modules/foundups/paccess_001/README.md"


class FakeRunner:
    def __init__(
        self,
        *,
        artifact_contents: dict[str, str] | None = None,
        ok: bool = True,
        rejection_reasons: tuple[str, ...] = (),
    ) -> None:
        self.artifact_contents = artifact_contents or {ARTIFACT: "# pAccess\n"}
        self.ok = ok
        self.rejection_reasons = rejection_reasons
        self.calls: list[dict[str, object]] = []

    def generate_artifacts(
        self,
        *,
        prompt: str,
        context: str,
        binding: dict[str, object],
        timeout_seconds: int,
    ) -> ArtifactGenerationModelResult:
        self.calls.append(
            {
                "prompt": prompt,
                "context": context,
                "binding": binding,
                "timeout_seconds": timeout_seconds,
            }
        )
        return ArtifactGenerationModelResult(
            ok=self.ok,
            status="MODEL_OK" if self.ok else "MODEL_REJECTED",
            artifact_contents=self.artifact_contents,
            model_receipt_id="model-receipt-1" if self.ok else None,
            model_result_digest="sha256:" + ("1" * 64),
            made_network_call=False,
            rejection_reasons=self.rejection_reasons,
        )


def _request(**overrides: object) -> dict[str, object]:
    payload = {
        "explicit_artifact_generation_requested": True,
        "work_order_id": "work-order-1",
        "slice_name": "REDDOG_TEST_ARTIFACT_GENERATION_PHASE1",
        "task_summary": "Generate one bounded README artifact.",
        "planned_artifacts": [ARTIFACT],
        "evidence_context": "Direct-read evidence says create a README only.",
        "holoindex_evidence": {
            "index_gap_detected": False,
            "retrieval_quality": "HIGH",
            "holoindex_freshness_receipt_digest": "sha256:holo-fresh",
        },
        "signed_authority": {"accepted": True, "signature_gate_digest": "sha256:auth"},
        "signed_receipt_chain": {"accepted": True, "terminal_receipt_hash": "sha256:chain"},
        "timeout_seconds": 30,
    }
    payload.update(overrides)
    return payload


def test_valid_generation_returns_exact_bounded_artifacts() -> None:
    runner = FakeRunner()

    result = generate_bounded_artifact_contents(_request(), runner=runner)

    assert result.decision == ARTIFACT_GENERATION_ACCEPT
    assert result.accepted is True
    assert result.rejection_reasons == []
    assert result.artifact_contents == {ARTIFACT: "# pAccess\n"}
    assert result.receipt.accepted is True
    assert result.receipt.planned_artifacts == [ARTIFACT]
    assert result.receipt.no_file_write_performed is True
    assert result.no_shell_command_executed is True
    assert runner.calls
    assert runner.calls[0]["binding"]["work_order_id"] == "work-order-1"


def test_foundups_fusion_runner_loader_resolves_repo_bridge() -> None:
    runner = reddog_bounded_artifact_generation_runtime._load_foundups_fusion_runner()

    assert callable(runner)
    assert runner.__name__ == "_run_foundups_fusion"


def test_missing_explicit_request_rejects_before_runner() -> None:
    runner = FakeRunner()

    result = generate_bounded_artifact_contents(
        _request(explicit_artifact_generation_requested=False),
        runner=runner,
    )

    assert result.decision == ARTIFACT_GENERATION_REJECT
    assert FAIL_EXPLICIT_REQUEST in result.rejection_reasons
    assert runner.calls == []


def test_missing_runner_rejects_fail_closed() -> None:
    result = generate_bounded_artifact_contents(_request(), runner=None)

    assert result.decision == ARTIFACT_GENERATION_REJECT
    assert FAIL_RUNNER_MISSING in result.rejection_reasons


def test_holoindex_index_gap_blocks_generation_before_runner() -> None:
    runner = FakeRunner()

    result = generate_bounded_artifact_contents(
        _request(holoindex_evidence={"index_gap_detected": True, "retrieval_quality": "INDEX_GAP"}),
        runner=runner,
    )

    assert FAIL_HOLOINDEX_EVIDENCE in result.rejection_reasons
    assert runner.calls == []


def test_authority_and_receipt_chain_are_required_before_runner() -> None:
    runner = FakeRunner()

    result = generate_bounded_artifact_contents(
        _request(signed_authority={"accepted": False}, signed_receipt_chain={}),
        runner=runner,
    )

    assert FAIL_AUTHORITY in result.rejection_reasons
    assert FAIL_RECEIPT_CHAIN in result.rejection_reasons
    assert runner.calls == []


def test_runner_rejection_blocks_artifacts() -> None:
    result = generate_bounded_artifact_contents(
        _request(),
        runner=FakeRunner(ok=False, rejection_reasons=("model_quorum_failed",)),
    )

    assert result.decision == ARTIFACT_GENERATION_REJECT
    assert FAIL_RUNNER_REJECTED in result.rejection_reasons
    assert "model_quorum_failed" in result.rejection_reasons
    assert result.artifact_contents == {}


def test_extra_or_missing_artifact_path_rejects() -> None:
    result = generate_bounded_artifact_contents(
        _request(),
        runner=FakeRunner(artifact_contents={ARTIFACT: "ok", "modules/foundups/paccess_001/EXTRA.md": "bad"}),
    )

    assert FAIL_ARTIFACTS_MISMATCH in result.rejection_reasons
    assert result.accepted is False


def test_invalid_planned_artifact_path_rejects_before_runner() -> None:
    runner = FakeRunner()

    result = generate_bounded_artifact_contents(
        _request(planned_artifacts=[ARTIFACT, "../escape.md"]),
        runner=runner,
    )

    assert FAIL_PLANNED_ARTIFACTS in result.rejection_reasons
    assert runner.calls == []


def test_secret_marker_and_nul_content_reject() -> None:
    result = generate_bounded_artifact_contents(
        _request(),
        runner=FakeRunner(artifact_contents={ARTIFACT: "token=abc\x00"}),
    )

    assert FAIL_SECRET_IN_CONTENT in result.rejection_reasons
    assert FAIL_CONTENT_INVALID in result.rejection_reasons


def test_module_has_no_filesystem_shell_github_pr_or_holoindex_mutation() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "holo_index",
        "git",
    }
    banned_import_fragments = {
        "worktree_pr_runner",
        "reddog_wre_worktree_runner",
        "openclaw_supervisor",
        "hermes_job_executor",
        "pattern_memory",
    }
    banned_calls = {"eval", "exec", "compile", "__import__", "open"}
    banned_attrs = {
        "write_text",
        "write_bytes",
        "unlink",
        "remove",
        "rmdir",
        "rename",
        "system",
        "popen",
        "spawn",
        "run",
        "Popen",
        "check_call",
        "check_output",
    }

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

    for token in (
        "holo_index.py --index",
        "create_pull_request",
        "merge_performed=True",
        "settle_reward",
        "PatternMemory(",
    ):
        assert token not in source
