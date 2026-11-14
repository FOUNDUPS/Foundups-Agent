#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Static doc test for REDDOG_SIGNING_KEY_ISOLATION_CONTRACT_PHASE1 (E0).

Decision-only slice: this test asserts the key-isolation contract encodes the
CoR-hardened boundary invariants AND the strict E0/E1 sequence lock, and that it
introduces NO runtime code. It reads the .md and checks stable anchor strings +
ASCII cleanliness. NO runtime import, NO filesystem write, NO authority behavior.

WSP: 22, 50, 54, 64, 71, 95, 96, 97
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DOC = (
    _REPO_ROOT / "docs" / "audits" / "architecture"
    / "REDDOG_SIGNING_KEY_ISOLATION_CONTRACT_PHASE1.md"
)


@pytest.fixture(scope="module")
def doc() -> str:
    assert _DOC.exists(), f"E0 contract doc missing: {_DOC}"
    return _DOC.read_text(encoding="utf-8")


# ---- boundary invariants (the CoR-hardened corrections) ---------------------
def test_distinct_os_principal_mandatory(doc: str) -> None:
    low = doc.lower()
    assert "distinct os principal" in low
    # same-user separation is explicitly insufficient
    assert "insufficient and forbidden" in low or "not a security boundary" in low
    assert "pr_set_dumpable" in low and "rlimit_core" in low
    assert "ptrace" in low


def test_kernel_peer_credential_not_request_body(doc: str) -> None:
    low = doc.lower()
    assert "so_peercred" in low or "getpeereid" in low
    assert "kernel-attested" in low or "kernel peer credential" in low or "peer credential" in low
    assert "advisory/audit-only" in low or "advisory/audit only" in low


def test_sign_what_you_validate(doc: str) -> None:
    low = doc.lower()
    assert "single source of truth" in low
    assert "canonical_payload" in low


def test_high_authority_needs_cosign_and_rate_cap(doc: str) -> None:
    low = doc.lower()
    assert "co-sign" in low or "cosign" in low or "consensus" in low
    assert "signing alone is never sufficient" in low or "signing alone never sufficient" in low
    assert "rate" in low and "cap" in low


def test_fingerprint_not_secret_hash_and_keyed_audit(doc: str) -> None:
    low = doc.lower()
    assert "never sha256(secret)" in low or "never `sha256(secret)`" in low
    assert "public material" in low
    assert "audit_mac" in low  # keyed/chained, not caller-predictable hash


def test_wsp71_permission_validated_retrieval(doc: str) -> None:
    low = doc.lower()
    assert "permission-validated retrieval" in low
    assert "permissiondeniederror" in low
    # vault handle possession is NOT authority
    assert "not possession" in low or "not the real credential" in low or "not possession of an" in low or "not string possession" in low


# ---- THE SEQUENCE LOCK (012 required assertion) -----------------------------
def test_e1_blocked_until_e0_lands(doc: str) -> None:
    low = doc.lower()
    assert "e1 verifier implementation is blocked until e0 lands" in low


def test_sequence_lock_block_present(doc: str) -> None:
    assert "E0/E1 Sequence Lock:" in doc
    assert "MUST NOT begin implementation until" in doc
    assert "non-authoritative and must be discarded or revalidated" in doc
    assert "No signature may be treated as authority until both E0 and E1 have landed" in doc


def test_no_parallel_build_relaxation(doc: str) -> None:
    """The stricter gate must not be relaxed to 'parallel build allowed'."""
    low = doc.lower()
    assert "may be authored and unit-tested in parallel" not in low
    assert "production trust, not code authoring" not in low


# ---- decision-only ----------------------------------------------------------
def test_declares_decision_only_no_code(doc: str) -> None:
    assert "Decision / contract ONLY" in doc
    assert "SPECIFIED_NOT_IMPLEMENTED" in doc
    assert "no signer code" in doc or "writes a contract only" in doc


# ---- ASCII gate -------------------------------------------------------------
def test_doc_is_ascii_clean() -> None:
    raw = _DOC.read_bytes()
    non_ascii = [i for i, b in enumerate(raw) if b > 127]
    assert not non_ascii, f"non-ASCII bytes at {non_ascii[:5]}"
    assert raw.count(0) == 0, "doc contains NUL bytes"
