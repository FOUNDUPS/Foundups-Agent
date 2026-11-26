"""Static doc test for REDDOG_PROMPT_LIBRARY_AND_M2M_REGISTRY_AUDIT_PHASE1."""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[4]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "audits"
    / "architecture"
    / "REDDOG_PROMPT_LIBRARY_AND_M2M_REGISTRY_AUDIT_PHASE1.md"
)

REQUIRED_SECTIONS = (
    "## Purpose",
    "## Direct-read Evidence",
    "## HoloIndex Addendum",
    "## Current-state Map",
    "## WSP_97 Verdict",
    "## Why This Is Not WSP_109-only",
    "## Required PromptReceipt Schema",
    "## Required PromptRun Schema",
    "## Required PromptOutcome Schema",
    "## Orchestration Model",
    "## WSP_15 Implementation Sequence",
    "## Truth Boundary Checklist",
    "## Residual SPECIFIED_NOT_IMPLEMENTED",
)

REQUIRED_MARKERS = (
    "PROMPT_TEMPLATES_EXIST",
    "WSP_99_M2M_EXISTS",
    "EXECUTED_PROMPT_LIBRARY_MISSING",
    "PROMPT_RECEIPT_REGISTRY_MISSING",
    "HOLOINDEX_REDDOG_PROMPT_LIBRARY_M2M_REGISTRY_INDEX_GAP_PHASE1",
    "PromptReceipt",
    "PromptRun",
    "PromptOutcome",
    "WRE worker claim gate",
    "Fusion's role is review/refutation, not memory",
    "WSP_109 belongs as a domain profile inside the registry",
)

REQUIRED_SEQUENCE = (
    "REDDOG_PROMPT_LIBRARY_CONTRACT_PHASE1",
    "REDDOG_PROMPT_EXAMPLES_FIXTURE_LIBRARY_PHASE1",
    "REDDOG_PROMPT_M2M_COMPILATION_GATE_PHASE1",
    "REDDOG_PROMPT_RELEVANCE_AND_QUORUM_GATE_PHASE1",
    "REDDOG_PROMPT_LIBRARY_STORAGE_DRYRUN_PHASE1",
    "REDDOG_PROMPT_LIBRARY_RETRIEVAL_DRYRUN_PHASE1",
    "REDDOG_PROMPT_LIBRARY_TO_WRE_DISPATCH_DRYRUN_PHASE1",
    "REDDOG_PROMPT_RUN_OUTCOME_MEMORY_PHASE1",
    "REDDOG_PROMPT_LIBRARY_HOLOINDEX_FRESHNESS_PHASE1",
    "REDDOG_PROMPT_LIBRARY_RUNTIME_CONSUMPTION_PHASE1",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_DOC.is_file(), "prompt library audit doc missing"
    return AUDIT_DOC.read_text(encoding="utf-8")


def test_prompt_library_audit_doc_exists(audit_text: str) -> None:
    assert len(audit_text) > 9000


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_prompt_library_audit_sections(section: str, audit_text: str) -> None:
    assert section in audit_text, f"missing section: {section}"


@pytest.mark.parametrize("marker", REQUIRED_MARKERS)
def test_prompt_library_audit_markers(marker: str, audit_text: str) -> None:
    assert marker in audit_text, f"missing marker: {marker}"


@pytest.mark.parametrize("slice_name", REQUIRED_SEQUENCE)
def test_prompt_library_audit_sequence(slice_name: str, audit_text: str) -> None:
    assert slice_name in audit_text, f"missing WSP_15 slice: {slice_name}"


def test_prompt_library_audit_truth_boundary(audit_text: str) -> None:
    assert "SPECIFIED_NOT_IMPLEMENTED" in audit_text
    assert "No extension runtime mutation | YES" in audit_text
    assert "No HoloIndex re-index | YES" in audit_text
    assert "Runtime authority remains blocked | YES" in audit_text


def test_prompt_library_audit_separates_wsp99_from_wsp109(audit_text: str) -> None:
    assert "WSP_99" in audit_text
    assert "WSP_109" in audit_text
    assert "not the registry itself" in audit_text
    assert "domain profile inside the registry" in audit_text


def test_prompt_library_audit_ascii_only(audit_text: str) -> None:
    non_ascii = [hex(ord(char)) for char in audit_text if ord(char) > 127]
    assert non_ascii == [], f"non-ASCII chars found: {non_ascii[:5]}"
    assert "\x00" not in audit_text
