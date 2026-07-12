"""Static contract tests for REDDOG_OPERATOR_LOOP_WARDROBE_SELECTION_CONTRACT_PHASE1."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
CONTRACT_DOC = (
    REPO_ROOT
    / "docs"
    / "audits"
    / "architecture"
    / "REDDOG_OPERATOR_LOOP_WARDROBE_SELECTION_CONTRACT_PHASE1.md"
)

REQUIRED_SECTIONS = (
    "## Purpose",
    "## Direct-read evidence (WSP_50)",
    "## 1. Canonical wardrobe profiles",
    "## 2. Selection inputs",
    "## 3. Selection output receipt",
    "## 4. WSP_97 decision rules",
    "## 5. HoloIndex and freshness boundary",
    "## 6. Relationship to live enqueue",
    "## 7. WSP_15 prioritization",
    "## 8. WSP_97 truth table",
    "## Explicit non-goals",
    "## Truth Boundary Checklist",
)

REQUIRED_WARDROBES = (
    "wsp97_solo_retrieval",
    "wsp97_architect_audit",
    "wsp97_implementation_slice",
    "wsp97_sovereign_execution",
)

REQUIRED_RECEIPT_FIELDS = (
    "RedDogOperatorLoopWardrobeSelectionReceipt",
    "selection_id",
    "selected_wardrobe",
    "wsp97_depth",
    "selected_context_mode",
    "selected_model_mode",
    "selected_effort",
    "execution_plane",
    "wre_required",
    "authority_boundary",
    "holoindex_query_digest",
    "holoindex_freshness_label",
    "index_gap_detected",
    "direct_read_required",
    "skillz_candidates",
    "lane_refs",
    "rejection_reasons",
    "no_execution_performed",
    "no_enqueue_performed",
    "implementation_status",
)

REQUIRED_MARKERS = (
    "WSP_95",
    "WSP_97",
    "WSP_45",
    "WSP_15",
    "HoloIndex",
    "INDEX_GAP",
    "SPECIFIED_NOT_IMPLEMENTED",
    "OBSERVED",
    "INFERRED",
    "REDDOG_EXTENSION_TO_LIVE_ENQUEUE_EXPLICIT_VALVE_INVOKE_PHASE1",
    "HOLOINDEX_REDDOG_OPERATOR_LOOP_WARDROBE_SELECTION_CONTRACT_INDEX_GAP_PHASE1",
)


@pytest.fixture(scope="module")
def contract_text() -> str:
    assert CONTRACT_DOC.is_file(), "operator loop wardrobe selection contract missing"
    return CONTRACT_DOC.read_text(encoding="utf-8")


def test_operator_loop_wardrobe_contract_doc_exists(contract_text: str) -> None:
    assert len(contract_text) > 6000


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_operator_loop_wardrobe_contract_sections(section: str, contract_text: str) -> None:
    assert section in contract_text, f"missing section: {section}"


@pytest.mark.parametrize("wardrobe", REQUIRED_WARDROBES)
def test_operator_loop_wardrobe_contract_profiles(wardrobe: str, contract_text: str) -> None:
    assert wardrobe in contract_text, f"missing wardrobe profile: {wardrobe}"


@pytest.mark.parametrize("field", REQUIRED_RECEIPT_FIELDS)
def test_operator_loop_wardrobe_contract_receipt_fields(field: str, contract_text: str) -> None:
    assert field in contract_text, f"missing receipt field: {field}"


@pytest.mark.parametrize("marker", REQUIRED_MARKERS)
def test_operator_loop_wardrobe_contract_markers(marker: str, contract_text: str) -> None:
    assert marker in contract_text, f"missing marker: {marker}"


def test_operator_loop_wardrobe_contract_behavior_skillz_is_noncanonical(contract_text: str) -> None:
    assert "behavior skillz" in contract_text.lower()
    assert "non-canonical" in contract_text.lower()
    assert "WSP-native concept is" in contract_text


def test_operator_loop_wardrobe_contract_forbids_runtime_authority(contract_text: str) -> None:
    lower = contract_text.lower()
    assert "no runtime selector implementation" in lower
    assert "no openclaw live enqueue" in lower
    assert "no wre shell or worktree write" in lower
    assert "no git, pr, push, or merge authority" in lower
    assert "no holoindex re-index" in lower


def test_operator_loop_wardrobe_contract_holoindex_boundary(contract_text: str) -> None:
    assert "RedDog runtime may query HoloIndex" in contract_text
    assert "RedDog runtime must not re-index HoloIndex" in contract_text
    assert "WRE/CI owns re-indexing" in contract_text


def test_operator_loop_wardrobe_contract_live_enqueue_requires_receipt(contract_text: str) -> None:
    assert "raw model" in contract_text.lower()
    assert "RedDogOperatorLoopWardrobeSelectionReceipt" in contract_text
    assert "live enqueue is forbidden" in contract_text.lower()


def test_operator_loop_wardrobe_contract_ascii_only(contract_text: str) -> None:
    non_ascii = [hex(ord(char)) for char in contract_text if ord(char) > 127]
    assert non_ascii == [], f"non-ASCII chars found: {non_ascii[:5]}"
