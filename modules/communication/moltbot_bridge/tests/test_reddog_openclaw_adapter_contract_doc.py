"""Static contract tests for REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1 audit doc."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
ADAPTER_CONTRACT_DOC = (
    REPO_ROOT
    / "docs"
    / "audits"
    / "architecture"
    / "REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1.md"
)

REQUIRED_SECTIONS = (
    "## Ownership ruling",
    "## 1. Source objects",
    "## 2. Target object options",
    "## 3. Field mapping",
    "## 4. Gate ordering",
    "## 5. Rejection rules",
    "## 6. Receipt reconciliation model",
    "## 7. Explicit non-goals",
    "## WSP_97 truth table",
    "## WSP_15 — Next implementation slices",
)

REQUIRED_MARKERS = (
    "AssignmentDispatcher",
    "SIMULATED_SCAFFOLD",
    "FoundUpJob",
    "autonomous_task",
    "no_execution_performed",
    "PolicyGateReceipt",
    "WREExecutorPlan",
    "SPECIFIED_NOT_IMPLEMENTED",
    "OpenClaw Supervisor",
)


@pytest.fixture(scope="module")
def adapter_contract_text() -> str:
    assert ADAPTER_CONTRACT_DOC.is_file(), "OpenClaw adapter contract audit doc missing"
    return ADAPTER_CONTRACT_DOC.read_text(encoding="utf-8")


def test_adapter_contract_doc_exists(adapter_contract_text: str) -> None:
    assert len(adapter_contract_text) > 800


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_adapter_contract_required_sections(section: str, adapter_contract_text: str) -> None:
    assert section in adapter_contract_text, f"missing section: {section}"


@pytest.mark.parametrize("marker", REQUIRED_MARKERS)
def test_adapter_contract_required_markers(marker: str, adapter_contract_text: str) -> None:
    assert marker in adapter_contract_text, f"missing marker: {marker}"


def test_adapter_contract_forbids_assignment_dispatcher_target(adapter_contract_text: str) -> None:
    assert "FORBIDDEN" in adapter_contract_text
    assert "Do not wire" in adapter_contract_text
    lower = adapter_contract_text.lower()
    assert "assignmentdispatcher" in lower
    assert "simulated" in lower


def test_adapter_contract_declares_no_runtime_implementation(adapter_contract_text: str) -> None:
    assert "no runtime adapter implementation" in adapter_contract_text.lower()
