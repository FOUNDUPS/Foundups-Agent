"""Static tests for REDDOG_WRE_GOVERNED_SHELL_RUNNER_CONTRACT_PHASE1."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
CONTRACT_DOC = (
    REPO_ROOT
    / "docs"
    / "audits"
    / "architecture"
    / "REDDOG_WRE_GOVERNED_SHELL_RUNNER_CONTRACT_PHASE1.md"
)

REQUIRED_SECTIONS = (
    "## Purpose",
    "## Direct-read evidence (WSP_50)",
    "## 1. Governed shell command profile",
    "## 2. Governed shell run request",
    "## 3. Required authority inputs",
    "## 4. Command policy",
    "## 5. CWD and worktree boundary",
    "## 6. Secret and environment boundary",
    "## 7. Receipt contract",
    "## 8. HoloIndex boundary",
    "## 9. Fail-closed rejection rules",
    "## 10. WSP_15 sequence",
    "## 11. WSP_97 truth table",
    "## Explicit non-goals",
    "## Truth Boundary Checklist",
)

REQUIRED_MARKERS = (
    "SHELL AUTHORITY IS NOT A STRING",
    "GovernedShellCommandProfile",
    "GovernedShellRunRequest",
    "GovernedShellRunReceipt",
    "argv_prefix",
    "shell=True",
    "RedDogDelegatedWorkAuthority",
    "SignedReceiptChainVerificationResult",
    "ExecutionValveDecision",
    "VALVE_OPEN_WORKTREE_CREATE",
    "WreCwdGuardResult",
    "GenericAgentWorktreeWriterDryRunReceipt",
    "WSP_71",
    "secret_env_refs",
    "stdout_digest",
    "stderr_digest",
    "no_merge_performed",
    "no_reward_settlement_performed",
    "no_holoindex_reindex_performed",
    "HOLOINDEX_REDDOG_WRE_GOVERNED_SHELL_RUNNER_CONTRACT_INDEX_GAP_PHASE1",
    "SPECIFIED_NOT_IMPLEMENTED",
    "OBSERVED",
)

NON_GOALS = (
    "No shell runner implementation.",
    "No subprocess invocation.",
    "No file mutation.",
    "No worktree creation.",
    "No PR/merge/release/deploy/publish.",
    "No reward settlement.",
    "No extension runtime wiring.",
    "No HoloIndex re-index.",
)


@pytest.fixture(scope="module")
def contract_text() -> str:
    assert CONTRACT_DOC.is_file(), "governed shell runner contract missing"
    return CONTRACT_DOC.read_text(encoding="utf-8")


def test_governed_shell_runner_contract_doc_exists(contract_text: str) -> None:
    assert len(contract_text) > 8500


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_governed_shell_runner_contract_sections(section: str, contract_text: str) -> None:
    assert section in contract_text, f"missing section: {section}"


@pytest.mark.parametrize("marker", REQUIRED_MARKERS)
def test_governed_shell_runner_contract_markers(marker: str, contract_text: str) -> None:
    assert marker in contract_text, f"missing marker: {marker}"


@pytest.mark.parametrize("line", NON_GOALS)
def test_governed_shell_runner_contract_non_goals(line: str, contract_text: str) -> None:
    assert line in contract_text


def test_governed_shell_runner_contract_requires_argv_only_no_shell(contract_text: str) -> None:
    assert "argv-list prefix" in contract_text
    assert "shell command string" in contract_text
    assert "shell metacharacter interpretation" in contract_text


def test_governed_shell_runner_contract_forbids_merge_and_publish(contract_text: str) -> None:
    for marker in (
        "git push",
        "git merge",
        "gh pr ready",
        "gh pr merge",
        "release",
        "publish",
        "deploy",
    ):
        assert marker in contract_text


def test_governed_shell_runner_contract_requires_cwd_guard(contract_text: str) -> None:
    for marker in (
        "validate_wre_worker_operation_cwd(...)",
        "operation_cwd inside isolated worktree",
        "operation_cwd outside shared repo root",
        "no Windows device or extended-length prefix",
    ):
        assert marker in contract_text


def test_governed_shell_runner_contract_requires_secret_boundary(contract_text: str) -> None:
    for marker in (
        "raw secret values are never accepted",
        "private keys are never accepted",
        "secret resolver must permission-check",
        "output is redacted before receipt",
    ):
        assert marker in contract_text


def test_governed_shell_runner_contract_forbids_runtime_holoindex_reindex(contract_text: str) -> None:
    assert "RedDog runtime must not re-index HoloIndex" in contract_text
    assert "HoloIndex `--index-*`, `--reindex-*`" in contract_text
    assert "WRE/CI owns freshness receipts" in contract_text


def test_governed_shell_runner_contract_ascii_only(contract_text: str) -> None:
    non_ascii = [hex(ord(char)) for char in contract_text if ord(char) > 127]
    assert non_ascii == [], f"non-ASCII chars found: {non_ascii[:5]}"
