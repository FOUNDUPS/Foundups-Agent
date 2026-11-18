"""Static contract tests for REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1 audit doc."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
EXECUTOR_CONTRACT_DOC = (
    REPO_ROOT
    / "docs"
    / "audits"
    / "architecture"
    / "REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1.md"
)

REQUIRED_SECTIONS = (
    "## 1. Entry conditions",
    "## 2. Worktree isolation",
    "## 3. Mutation boundaries",
    "## 4. Test / validation requirements",
    "## 5. Rollback / cleanup",
    "## 6. Executor output contract",
    "## 7. Explicit non-goals",
    "## WSP_97 truth table",
    "## WSP_15 — Next implementation slices",
)

REQUIRED_MARKERS = (
    "WREExecutorResult",
    "no_execution_performed",
    "PolicyGateReceipt",
    "RedDogWorkOrderReceipt",
    "SPECIFIED_NOT_IMPLEMENTED",
    "merge_performed: false",
)


@pytest.fixture(scope="module")
def executor_contract_text() -> str:
    assert EXECUTOR_CONTRACT_DOC.is_file(), "executor contract audit doc missing"
    return EXECUTOR_CONTRACT_DOC.read_text(encoding="utf-8")


def test_executor_contract_doc_exists(executor_contract_text: str) -> None:
    assert len(executor_contract_text) > 500


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_executor_contract_required_sections(section: str, executor_contract_text: str) -> None:
    assert section in executor_contract_text, f"missing section: {section}"


@pytest.mark.parametrize("marker", REQUIRED_MARKERS)
def test_executor_contract_required_markers(marker: str, executor_contract_text: str) -> None:
    assert marker in executor_contract_text, f"missing marker: {marker}"


def test_executor_contract_declares_no_runtime_implementation(executor_contract_text: str) -> None:
    assert "no executor implementation" in executor_contract_text.lower()
