#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Static doc test for REDDOG_RECURSIVE_SELF_GOVERNANCE_THREAT_MODEL_PHASE1.

Decision-only slice: this test asserts the threat-model doc is complete (threat
families G1-G7 + the sharpened-E requirements) and that it introduces NO runtime
code / NO verifier implementation. It reads the .md and checks stable anchor
strings + ASCII cleanliness. NO runtime import, NO filesystem write, NO authority
behavior.

WSP: 22, 48, 50, 64, 96, 97
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DOC = (
    _REPO_ROOT / "docs" / "audits" / "architecture"
    / "REDDOG_RECURSIVE_SELF_GOVERNANCE_THREAT_MODEL_PHASE1.md"
)


@pytest.fixture(scope="module")
def doc() -> str:
    assert _DOC.exists(), f"threat-model doc missing: {_DOC}"
    return _DOC.read_text(encoding="utf-8")


# ---- all seven threat families present --------------------------------------
@pytest.mark.parametrize("family", ["G1", "G2", "G3", "G4", "G5", "G6", "G7"])
def test_threat_family_present(doc: str, family: str) -> None:
    assert f"### {family}" in doc, f"threat family {family} missing"


# ---- integrity is not authenticity ------------------------------------------
def test_integrity_not_authenticity_present(doc: str) -> None:
    low = doc.lower()
    assert "integrity, not authenticity" in low
    # and it must not overclaim that derivation proves authorization
    assert "self-asserted derivation is never authority" in low


# ---- key isolation / supply-chain poisoning ---------------------------------
def test_key_isolation_and_supply_chain_present(doc: str) -> None:
    low = doc.lower()
    assert "key isolation" in low
    assert "supply chain" in low or "supply-chain" in low
    # the decisive insight: poisoned in-process code emits a VALID signature
    assert "reaching the vault" in low or "reach the vault" in low or "reach the host vault" in low


# ---- constant-time compare / no timing leak ---------------------------------
def test_constant_time_and_no_timing_leak_present(doc: str) -> None:
    low = doc.lower()
    assert "constant-time" in low
    assert "timing" in low
    assert "compare_digest" in low  # names the concrete control


# ---- concurrency / TOCTOU ---------------------------------------------------
def test_concurrency_toctou_present(doc: str) -> None:
    low = doc.lower()
    assert "toctou" in low
    assert "concurren" in low  # concurrency / concurrent


# ---- economic gaming --------------------------------------------------------
def test_economic_gaming_present(doc: str) -> None:
    low = doc.lower()
    assert "economic" in low
    assert "goodhart" in low or "reward-farming" in low or "self-dealing" in low


# ---- DoS / fail-open --------------------------------------------------------
def test_dos_and_fail_open_present(doc: str) -> None:
    low = doc.lower()
    assert "dos" in low or "budget exhaustion" in low
    assert "fail-open" in low


# ---- decision-only: no runtime code / no verifier implementation ------------
def test_declares_no_runtime_code_and_no_verifier(doc: str) -> None:
    assert "Decision-only threat model" in doc
    assert "SPECIFIED_NOT_IMPLEMENTED" in doc
    # explicitly defers the verifier; does not implement it here
    assert "Do NOT open verifier code until C is finalized" in doc
    assert "adds NO code" in doc or "No code" in doc


# ---- ASCII gate -------------------------------------------------------------
def test_doc_is_ascii_clean() -> None:
    raw = _DOC.read_bytes()
    non_ascii = [i for i, b in enumerate(raw) if b > 127]
    assert not non_ascii, f"non-ASCII bytes at {non_ascii[:5]}"
    assert raw.count(0) == 0, "doc contains NUL bytes"
