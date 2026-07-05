#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Static doc test for REDDOG_OPERATOR_LOOP_AND_GENERIC_SPINE_AUDIT_PHASE1.

Decision/contract-only slice: this test asserts the two decision docs are complete
and that the operator-loop binding does NOT overclaim authenticity. It reads the
.md files and checks stable anchor strings + an ASCII-cleanliness gate. NO runtime
import, NO filesystem write, NO authority behavior.

Gate enforced (from 012): "no claim that WSP derivation proves authenticity."

WSP: 22, 48, 50, 64, 97
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_ARCH = _REPO_ROOT / "docs" / "audits" / "architecture"
_AUDIT = _ARCH / "REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_AUDIT_PHASE1.md"
_BINDING = _ARCH / "REDDOG_OPERATOR_LOOP_WSP97_BINDING_PHASE1.md"


@pytest.fixture(scope="module")
def audit() -> str:
    assert _AUDIT.exists(), f"audit doc missing: {_AUDIT}"
    return _AUDIT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def binding() -> str:
    assert _BINDING.exists(), f"binding doc missing: {_BINDING}"
    return _BINDING.read_text(encoding="utf-8")


# ---- generic-spine audit doc -------------------------------------------------
def test_audit_verdict_present(audit: str) -> None:
    assert "KEEP_FOUNDUP_SPECIFIC_FOR_NOW" in audit
    assert "EXTRACT_GENERIC_SPINE_CONTRACT_NEXT" in audit


def test_audit_records_both_latent_blockers(audit: str) -> None:
    # caller-supplied allowed_paths destroys containment
    assert "allowed_paths" in audit and "containment" in audit
    # writer authorizes on the low-level valve resolver, skipping the full spine
    assert "_resolve_valve_state(env, [])" in audit


def test_audit_hard_rule_generic_not_unbounded(audit: str) -> None:
    assert "GENERIC DOES NOT MEAN UNBOUNDED" in audit


def test_audit_index_gap_recorded(audit: str) -> None:
    assert "INDEX_GAP" in audit
    assert "HOLOINDEX_FOUNDUP_SCAFFOLD_WRITER_LIVE_DISCOVERABILITY_PHASE1" in audit


# ---- operator-loop binding doc ----------------------------------------------
def test_binding_has_five_mandatory_questions(binding: str) -> None:
    for q in (
        "What WSP governs this?",
        "What repo evidence proves it?",
        "What authority scope applies?",
        "What execution plane am I in?",
        "What must remain impossible?",
    ):
        assert q in binding, f"missing mandatory question: {q}"


def test_binding_active_derive_not_passive_validate(binding: str) -> None:
    assert "passive-validate" in binding or "passive validate" in binding
    assert "active-derive" in binding or "ACTIVE-DERIVED" in binding
    assert "404-417" in binding  # pins the as-built passive-validate site


def test_binding_extends_wsp97_not_new_wsp(binding: str) -> None:
    # WSP 64: enhance existing, do not mint a new WSP.
    assert "WSP 64" in binding
    assert "EXTEND" in binding or "extends WSP 97" in binding or "binding subsection" in binding


def test_binding_has_protected_oracle_and_permanent_invariants(binding: str) -> None:
    assert "PROTECTED surface" in binding                 # 5A
    assert "Permanent system invariants" in binding       # 5B
    assert "preamble replay" in binding.lower()           # replay invariant
    assert "self-consensus" in binding.lower() or "self-signing" in binding.lower()


def test_binding_binds_derived_wsp_to_actual_work(binding: str) -> None:
    assert "FAIL_WSP_WORK_MISMATCH" in binding            # 5C


# ---- THE GATE: integrity, not authenticity ----------------------------------
def test_binding_states_integrity_not_authenticity(binding: str) -> None:
    low = binding.lower()
    assert "integrity" in low and "authenticity" in low
    assert "integrity, not authenticity" in low


def test_binding_does_not_claim_derivation_proves_authenticity(binding: str) -> None:
    """012 gate: the doc must not claim WSP derivation proves authorization/authenticity."""
    low = binding.lower()
    forbidden = (
        "derivation proves authenticity",
        "derivation proves authorization",
        "wsp derivation proves auth",
        "derived therefore authorized",
        "asked wsp first means authorized",
    )
    for phrase in forbidden:
        assert phrase not in low, f"authenticity overclaim present: {phrase!r}"
    # And it must explicitly forbid the valve trusting the unsigned label until slice D.
    assert "must not" in low and "unsigned" in low


# ---- ASCII gate (both docs) -------------------------------------------------
@pytest.mark.parametrize("path", [_AUDIT, _BINDING])
def test_docs_are_ascii_clean(path: Path) -> None:
    raw = path.read_bytes()
    non_ascii = [i for i, b in enumerate(raw) if b > 127]
    assert not non_ascii, f"{path.name} has non-ASCII bytes at {non_ascii[:5]}"
    assert raw.count(0) == 0, f"{path.name} contains NUL bytes"
