"""Static contract test for REDDOG_PROMPT_LIBRARY_CONTRACT_PHASE1."""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[4]
CONTRACT_DOC = (
    REPO_ROOT
    / "docs"
    / "contracts"
    / "REDDOG_PROMPT_LIBRARY_CONTRACT_PHASE1.md"
)

REQUIRED_SECTIONS = (
    "## Purpose",
    "## Non-goals",
    "## Current Evidence",
    "## Canonical Entities",
    "## PromptTemplate Schema",
    "## PromptReceipt Schema",
    "## PromptReceipt Approval Rules",
    "## PromptRun Schema",
    "## PromptOutcome Schema",
    "## PromptPatternPromotion Schema",
    "## Dispatch Boundary",
    "## HoloIndex Boundary",
    "## WSP_109 Domain Profile",
    "## WSP_15 Next Slices",
    "## Truth Boundary Checklist",
    "## Residual SPECIFIED_NOT_IMPLEMENTED",
)

REQUIRED_ENTITIES = (
    "PromptTemplate",
    "PromptReceipt",
    "PromptRun",
    "PromptOutcome",
    "PromptPatternPromotion",
    "PromptLibraryFreshnessReceipt",
)

REQUIRED_FIELDS = (
    "prompt_id",
    "prompt_digest",
    "template_id",
    "slice_name",
    "typed_grounding_receipt_digest",
    "wardrobe_selection_receipt_digest",
    "m2m_digest",
    "raw_ref",
    "prompt_relevance_passed",
    "fusion_quorum_passed",
    "approved_for_dispatch",
    "no_runtime_execution_performed",
    "no_repo_mutation_performed",
)

FORBIDDEN_OUTPUTS = (
    "git worktree add",
    "subprocess execution",
    "OpenClaw enqueue",
    "Hermes execution",
    "PR merge",
    "HoloIndex re-index",
    "reward settlement",
)


@pytest.fixture(scope="module")
def contract_text() -> str:
    assert CONTRACT_DOC.is_file(), "prompt library contract doc missing"
    return CONTRACT_DOC.read_text(encoding="utf-8")


def test_prompt_library_contract_doc_exists(contract_text: str) -> None:
    assert len(contract_text) > 9000


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_prompt_library_contract_sections(section: str, contract_text: str) -> None:
    assert section in contract_text, f"missing section: {section}"


@pytest.mark.parametrize("entity", REQUIRED_ENTITIES)
def test_prompt_library_contract_entities(entity: str, contract_text: str) -> None:
    assert entity in contract_text, f"missing entity: {entity}"


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_prompt_receipt_fields(field: str, contract_text: str) -> None:
    assert field in contract_text, f"missing PromptReceipt field: {field}"


@pytest.mark.parametrize("forbidden", FORBIDDEN_OUTPUTS)
def test_dispatch_boundary_forbids_live_actions(forbidden: str, contract_text: str) -> None:
    assert forbidden in contract_text, f"missing forbidden output: {forbidden}"


def test_prompt_receipt_approval_rules_are_fail_closed(contract_text: str) -> None:
    assert "approved_for_dispatch may be true only when all conditions hold" in contract_text
    assert "If any rule fails" in contract_text
    assert "WRE must not dispatch a worker" in contract_text


def test_holoindex_boundary_query_only(contract_text: str) -> None:
    assert "runtime_reindex_performed: false" in contract_text
    assert "RedDog runtime must never re-index HoloIndex" in contract_text
    assert "WRE/CI owns re-indexing" in contract_text


def test_wsp109_is_domain_profile_not_registry(contract_text: str) -> None:
    assert "domain_profile: wsp109_foundup_intake" in contract_text
    assert "They must not define a separate prompt library" in contract_text


def test_prompt_library_contract_truth_boundary(contract_text: str) -> None:
    assert "No runtime implementation | YES" in contract_text
    assert "No extension runtime mutation | YES" in contract_text
    assert "Runtime authority remains blocked | YES" in contract_text
    assert "SPECIFIED_NOT_IMPLEMENTED" in contract_text


def test_prompt_library_contract_ascii_only(contract_text: str) -> None:
    non_ascii = [hex(ord(char)) for char in contract_text if ord(char) > 127]
    assert non_ascii == [], f"non-ASCII chars found: {non_ascii[:5]}"
    assert "\x00" not in contract_text

