"""Static tests for REDDOG_MERGE_AUTHORITY_CONTRACT_PHASE1."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
CONTRACT_DOC = (
    REPO_ROOT
    / "docs"
    / "audits"
    / "architecture"
    / "REDDOG_MERGE_AUTHORITY_CONTRACT_PHASE1.md"
)

REQUIRED_SECTIONS = (
    "## Purpose",
    "## Direct-read evidence (WSP_50)",
    "## 1. Authority separation model",
    "## 2. Merge authority request",
    "## 3. Merge decision and receipt",
    "## 4. Required evidence inputs",
    "## 5. F0 and external FoundUp policy tiers",
    "## 6. Non-self promotion and reviewer integrity",
    "## 7. Protected surfaces",
    "## 8. CI and check-run policy",
    "## 9. HoloIndex boundary",
    "## 10. Fail-closed rejection rules",
    "## 11. WSP_15 sequence",
    "## 12. WSP_97 truth table",
    "## Explicit non-goals",
    "## Truth Boundary Checklist",
)

REQUIRED_MARKERS = (
    "MERGE AUTHORITY IS NOT REVIEW",
    "SIGNED, NON-SELF, CONSENSUS-CHECKED PROMOTION DECISION",
    "RedDogMergeAuthorityRequest",
    "RedDogMergeAuthorityDecision",
    "RedDogMergeAuthorityReceipt",
    "expected_head_sha",
    "machine-derived diff/scope summary",
    "promoter_principal_id",
    "author_principal_id",
    "author_reddog_id",
    "promoter_reddog_id",
    "Signed delegated work authority",
    "Signed receipt-chain verification",
    "WSP_96 consensus receipt",
    "HoloIndex freshness receipt",
    "INDEX_GAP",
    "f0_sovereign",
    "external_foundup",
    "SELF_PROMOTION_REJECTED",
    "SPECIFIED_NOT_IMPLEMENTED",
    "OBSERVED",
)

NON_GOALS = (
    "No runtime merge authority implementation.",
    "No `gh pr ready` or `gh pr merge` call.",
    "No GitHub API call.",
    "No branch, tag, release, deploy, publish, or protected-ref mutation.",
    "No shell runner change.",
    "No extension runtime wiring.",
    "No reward settlement.",
    "No HoloIndex re-index.",
)


@pytest.fixture(scope="module")
def contract_text() -> str:
    assert CONTRACT_DOC.is_file(), "merge authority contract missing"
    return CONTRACT_DOC.read_text(encoding="utf-8")


def test_merge_authority_contract_doc_exists(contract_text: str) -> None:
    assert len(contract_text) > 9000


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_merge_authority_contract_sections(section: str, contract_text: str) -> None:
    assert section in contract_text, f"missing section: {section}"


@pytest.mark.parametrize("marker", REQUIRED_MARKERS)
def test_merge_authority_contract_markers(marker: str, contract_text: str) -> None:
    assert marker in contract_text, f"missing marker: {marker}"


@pytest.mark.parametrize("line", NON_GOALS)
def test_merge_authority_contract_non_goals(line: str, contract_text: str) -> None:
    assert line in contract_text


def test_merge_authority_contract_requires_non_self_promotion(contract_text: str) -> None:
    for marker in (
        "Self-promotion is fail-closed",
        "author_principal_id == promoter_principal_id",
        "author_reddog_id == promoter_reddog_id",
        "same signing key signs author, reviewer, and promoter receipts",
    ):
        assert marker in contract_text


def test_merge_authority_contract_requires_machine_evidence_not_prose(contract_text: str) -> None:
    for marker in (
        "Machine-derived diff/scope summary",
        "RedDog prose cannot be the source of truth",
        "PR body text is the only evidence",
        "exact changed file list",
    ):
        assert marker in contract_text


def test_merge_authority_contract_requires_ci_exact_head(contract_text: str) -> None:
    for marker in (
        "exact `head_sha`",
        "expected-head lock",
        "different head SHA",
        "Re-running checks must preserve the same head SHA",
    ):
        assert marker in contract_text


def test_merge_authority_contract_forbids_runtime_holoindex_reindex(contract_text: str) -> None:
    assert "RedDog runtime never re-indexes HoloIndex during merge evaluation" in contract_text
    assert "WRE/CI must enqueue targeted re-index/freshness work" in contract_text
    assert "HOLOINDEX_REDDOG_MERGE_AUTHORITY_CONTRACT_INDEX_GAP_PHASE1" in contract_text


def test_merge_authority_contract_ascii_only(contract_text: str) -> None:
    non_ascii = [hex(ord(char)) for char in contract_text if ord(char) > 127]
    assert non_ascii == [], f"non-ASCII chars found: {non_ascii[:5]}"
