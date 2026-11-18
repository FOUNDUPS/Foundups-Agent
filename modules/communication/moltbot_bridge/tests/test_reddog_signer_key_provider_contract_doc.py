#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static contract checks for REDDOG_SIGNER_KEY_PROVIDER_CONTRACT_PHASE1.

This slice freezes the signer key-provider boundary only. It must not introduce
runtime key loading, signer launch, vault configuration, or authority behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DOC = (
    _REPO_ROOT
    / "docs"
    / "contracts"
    / "REDDOG_SIGNER_KEY_PROVIDER_CONTRACT_PHASE1.md"
)


@pytest.fixture(scope="module")
def doc() -> str:
    assert _DOC.exists(), f"contract doc missing: {_DOC}"
    return _DOC.read_text(encoding="utf-8")


def test_doc_declares_decision_only_scope(doc: str) -> None:
    assert "decision-only" in doc
    assert "No runtime key loading" in doc
    assert "NO_KEY_LOADING: PASS" in doc
    assert "DOCS_AND_STATIC_TESTS_ONLY: PASS" in doc


def test_wsp71_permission_validated_retrieval_not_reference_possession(doc: str) -> None:
    low = doc.lower()
    assert "wsp 71" in low
    assert "op://vault/item/field" in low
    assert "possession of an `op://` reference string is not authority" in low
    assert "permission-validated retrieval" in low
    assert "secrets_read" in low


def test_mock_vault_resolver_is_not_production_authority(doc: str) -> None:
    assert "MockVaultResolver" in doc
    assert "MOCK_VAULT_ONLY" in doc
    assert "NO_REAL_SECRET_ACCESS" in doc
    assert "Production code must not use `MockVaultResolver`" in doc
    assert "FAIL_PROVIDER_MOCK_IN_PRODUCTION" in doc


def test_runtime_never_receives_secret_references_or_values(doc: str) -> None:
    low = doc.lower()
    assert "runtime never sends `signing_key_ref`" in low
    assert "runtime never learns the signing key reference" in low
    assert "plaintext key bytes" in low
    assert "secret values must never appear" in low
    assert "copy-md" in low


def test_signing_and_audit_keys_are_distinct(doc: str) -> None:
    low = doc.lower()
    assert "audit_mac_key_ref" in low
    assert "signing_key_ref == audit_mac_key_ref" in low
    assert "fails closed" in low
    assert "distinct from the signing key" in low


def test_public_fingerprint_not_secret_hash(doc: str) -> None:
    low = doc.lower()
    assert "derived only from public verification material" in low
    assert "must never be `sha256(secret)`" in low
    assert "public key mismatch fails closed" in low
    assert "fingerprint mismatch fails closed" in low


def test_ttl_and_current_key_only_rules(doc: str) -> None:
    low = doc.lower()
    assert "ttl is enforced at use time" in low
    assert "current signing key only" in low
    assert "previous key epochs are" in low
    assert "must not be loadable for signing" in low


def test_holoindex_boundary_is_query_only(doc: str) -> None:
    low = doc.lower()
    assert "must not re-index holoindex" in low
    assert "hoLOINDEX_REDDOG_SIGNER_KEY_PROVIDER_CONTRACT_INDEX_GAP_PHASE1".lower() in low
    assert "governed wre or ci indexing work item" in low


def test_sequence_names_dryrun_before_runtime(doc: str) -> None:
    assert "REDDOG_SIGNER_KEY_PROVIDER_DRYRUN_PHASE1" in doc
    assert "REDDOG_SIGNER_SOCKET_PEER_CREDENTIAL_ATTESTOR_PHASE1" in doc
    assert "REDDOG_ISOLATED_SIGNER_PROCESS_ENTRYPOINT_PHASE1" in doc
    assert "Production vault resolution" in doc
    assert "remain blocked until separately authorized" in doc


def test_failure_codes_are_coarse_and_non_secret(doc: str) -> None:
    assert "FAIL_PROVIDER_PERMISSION_DENIED" in doc
    assert "FAIL_PROVIDER_PUBLIC_KEY_MISMATCH" in doc
    assert "FAIL_PROVIDER_AUDIT_KEY_MISSING" in doc
    assert "must not include expected public key fragments" in doc
    assert "secret lengths" in doc


def test_doc_is_ascii_clean() -> None:
    raw = _DOC.read_bytes()
    non_ascii = [i for i, b in enumerate(raw) if b > 127]
    assert not non_ascii, f"non-ASCII bytes at {non_ascii[:5]}"
    assert raw.count(0) == 0
