"""Static contract tests for REDDOG_OPENCLAW_LIVE_ENQUEUE_CONTRACT_PHASE1 audit doc."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
LIVE_ENQUEUE_CONTRACT_DOC = (
    REPO_ROOT
    / "docs"
    / "audits"
    / "architecture"
    / "REDDOG_OPENCLAW_LIVE_ENQUEUE_CONTRACT_PHASE1.md"
)

REQUIRED_SECTIONS = (
    "## Direct-read evidence (WSP_50)",
    "## 1. Required inputs (live enqueue contract gate)",
    "## 2. Valve authority (mandatory)",
    "## 3. Canonical targets",
    "## 4. Receipt reconciliation chain",
    "## 5. Fail-closed rejection rules",
    "## 6. Output contract (this slice)",
    "## 7. Gate ordering (updated spine)",
    "## WSP_97 truth table",
    "## WSP_15 -- Next implementation slices (ordered)",
    "## Explicit non-goals",
)

REQUIRED_MARKERS = (
    "ProposedOpenClawIntakeRecord",
    "AdapterDryRunReceipt",
    "PolicyGateReceipt",
    "signature_gate_status",
    "SIGNATURE_GATE_ACCEPTED",
    "SignedReceiptChainVerificationResult",
    "reddog-receipt.v1",
    "RedDogWorkOrderReceipt",
    "ExecutionValveDecision",
    "VALVE_OPEN_DRYRUN_ONLY",
    "VALVE_OPEN_LIVE_ENQUEUE",
    "VALVE_OPEN_WORKTREE_CREATE",
    "RedDogOpenClawLiveEnqueueContractReceipt",
    "no_enqueue_performed",
    "no_execution_performed",
    "AssignmentDispatcher",
    "FORBIDDEN",
    "FoundUpJob",
    "autonomous_task",
    "SPECIFIED_NOT_IMPLEMENTED",
)


@pytest.fixture(scope="module")
def live_enqueue_contract_text() -> str:
    assert LIVE_ENQUEUE_CONTRACT_DOC.is_file(), "OpenClaw live enqueue contract audit doc missing"
    return LIVE_ENQUEUE_CONTRACT_DOC.read_text(encoding="utf-8")


def test_live_enqueue_contract_doc_exists(live_enqueue_contract_text: str) -> None:
    assert len(live_enqueue_contract_text) > 800


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_live_enqueue_contract_required_sections(section: str, live_enqueue_contract_text: str) -> None:
    assert section in live_enqueue_contract_text, f"missing section: {section}"


@pytest.mark.parametrize("marker", REQUIRED_MARKERS)
def test_live_enqueue_contract_required_markers(marker: str, live_enqueue_contract_text: str) -> None:
    assert marker in live_enqueue_contract_text, f"missing marker: {marker}"


def test_live_enqueue_contract_forbids_live_enqueue_in_slice(live_enqueue_contract_text: str) -> None:
    lower = live_enqueue_contract_text.lower()
    assert "forbidden" in lower
    assert "no runtime module emits" in lower or "no runtime enqueue module" in lower
    assert "live enqueue performed" in lower or "live_enqueue_performed" in lower


def test_live_enqueue_contract_dryrun_valve_insufficient(live_enqueue_contract_text: str) -> None:
    assert "insufficient" in live_enqueue_contract_text.lower()
    assert "VALVE_OPEN_DRYRUN_ONLY" in live_enqueue_contract_text
    assert "REJECT" in live_enqueue_contract_text


def test_live_enqueue_contract_ascii_only(live_enqueue_contract_text: str) -> None:
    non_ascii = [hex(ord(c)) for c in live_enqueue_contract_text if ord(c) > 127]
    assert non_ascii == [], f"non-ASCII chars found: {non_ascii[:5]}"
