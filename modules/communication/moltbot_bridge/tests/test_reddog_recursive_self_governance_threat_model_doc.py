"""Static doc-guard test for the RedDog recursive-self-governance threat model.

This is a STATIC presence-assertion test. It opens the threat-model decision doc
and asserts the required guards, principle, threat classes, sequence lock, and
Truth Boundary Checklist tokens are present. It contains NO runtime logic under
test, NO verifier, NO crypto, and imports NO moltbot_bridge / signing / verifier
runtime module. Dependency-light: pathlib + pytest + plain asserts only.

Slice: REDDOG_RECURSIVE_SELF_GOVERNANCE_THREAT_MODEL_PHASE1
"""

from pathlib import Path

import pytest

# Resolve repo root robustly from this test file's location:
# .../modules/communication/moltbot_bridge/tests/<this file>
#   parents[0]=tests parents[1]=moltbot_bridge parents[2]=communication
#   parents[3]=modules parents[4]=<repo root>
REPO_ROOT = Path(__file__).resolve().parents[4]
THREAT_MODEL_DOC = (
    REPO_ROOT
    / "docs"
    / "audits"
    / "architecture"
    / "REDDOG_RECURSIVE_SELF_GOVERNANCE_THREAT_MODEL_PHASE1.md"
)

# Seven governance guards, each must appear by its literal label.
REQUIRED_GUARD_LABELS = ("G1", "G2", "G3", "G4", "G5", "G6", "G7")

# Core principle (verbatim) + the recursive-self-governance threat categories.
REQUIRED_CONTENT = (
    "integrity is not authenticity",
    "key isolation",
    "supply-chain poisoning",
    "constant-time compare",
    "timing leak",
    "TOCTOU",
    "economic gaming",
    "fail-open",
)

# E0/E1 sequence-lock slice names (both must appear).
E0_SLICE = "REDDOG_SIGNING_KEY_ISOLATION_CONTRACT_PHASE1"
E1_SLICE = "REDDOG_WORK_ORDER_SIGNATURE_VERIFIER_PHASE1"

# Truth Boundary Checklist tokens that must be present.
REQUIRED_TRUTH_BOUNDARY_TOKENS = (
    "NO_RUNTIME_CODE",
    "NO_VERIFIER_IMPLEMENTATION",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert THREAT_MODEL_DOC.is_file(), (
        "threat-model doc missing at expected path: " + str(THREAT_MODEL_DOC)
    )
    return THREAT_MODEL_DOC.read_text(encoding="utf-8")


def test_doc_exists_and_nonempty(doc_text: str) -> None:
    assert len(doc_text) > 1000, "threat-model doc is unexpectedly short"


@pytest.mark.parametrize("label", REQUIRED_GUARD_LABELS)
def test_all_seven_guards_present(label: str, doc_text: str) -> None:
    assert label in doc_text, "missing governance guard label: " + label


@pytest.mark.parametrize("needle", REQUIRED_CONTENT)
def test_required_threat_content_present(needle: str, doc_text: str) -> None:
    assert needle in doc_text, "missing required content: " + needle


def test_core_principle_verbatim(doc_text: str) -> None:
    assert "integrity is not authenticity" in doc_text, (
        "verbatim core principle 'integrity is not authenticity' missing"
    )


def test_concurrency_toctou_present(doc_text: str) -> None:
    # Concurrency framing must accompany TOCTOU.
    assert "TOCTOU" in doc_text, "TOCTOU threat class missing"
    lowered = doc_text.lower()
    assert "concurrency" in lowered, "concurrency framing missing"


def test_dos_fail_open_present(doc_text: str) -> None:
    lowered = doc_text.lower()
    assert "dos" in lowered, "DoS threat class missing"
    assert "fail-open" in doc_text, "fail-open threat class missing"


def test_e0_before_e1_sequence_lock_present(doc_text: str) -> None:
    assert E0_SLICE in doc_text, "E0 slice name (" + E0_SLICE + ") missing"
    assert E1_SLICE in doc_text, "E1 slice name (" + E1_SLICE + ") missing"
    # The doc must state E1 is blocked until E0 lands.
    lowered = doc_text.lower()
    assert "e0 before e1" in lowered, "'E0 before E1' sequence-lock statement missing"
    assert "blocked until" in lowered, (
        "sequence lock must state E1 is BLOCKED until E0 lands"
    )


@pytest.mark.parametrize("token", REQUIRED_TRUTH_BOUNDARY_TOKENS)
def test_truth_boundary_checklist_tokens_present(token: str, doc_text: str) -> None:
    assert token in doc_text, "Truth Boundary Checklist missing token: " + token
