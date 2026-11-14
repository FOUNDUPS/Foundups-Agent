#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Static contract test for FOUNDUP_SCAFFOLD_CONTRACT_PHASE1.

Decision/contract-only slice: this test asserts the CONTRACT DOC is complete and
that NO runtime scaffold writer / mutation was introduced by the slice. It reads
the doc and checks stable anchor strings (Addendum F, items 1-9). No runtime
import, no filesystem write, no scaffold behavior.

WSP: 49, 50, 97, 109
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = _REPO_ROOT / "docs" / "audits" / "architecture" / "FOUNDUP_SCAFFOLD_CONTRACT_PHASE1.md"


@pytest.fixture(scope="module")
def doc() -> str:
    assert _CONTRACT.exists(), f"contract doc missing: {_CONTRACT}"
    return _CONTRACT.read_text(encoding="utf-8")


# Addendum F.1 -- create_foundup defined AND distinct from extract_foundup
def test_create_foundup_defined_and_not_aliased(doc: str) -> None:
    assert "create_foundup" in doc
    assert "extract_foundup" in doc
    assert "CREATE_FOUNDUP_MUST_NOT_ALIAS_EXTRACT" in doc
    assert "MUST NOT resolve to" in doc  # explicit non-alias rule
    assert "creation_mode" in doc         # disambiguator if build_foundup is the carrier


# Addendum F.2 -- WSP-49 scaffold artifacts enumerated (incl. memory/)
def test_wsp49_artifacts_enumerated(doc: str) -> None:
    required = [
        "README.md", "INTERFACE.md", "ROADMAP.md", "ModLog.md",
        "requirements.txt", "TestModLog.md", "foundup_manifest.json",
        "src/", "tests/", "memory/",
    ]
    missing = [a for a in required if a not in doc]
    assert missing == [], f"scaffold artifact set incomplete: {missing}"
    assert "WSP_49" in doc


# Addendum F.3 -- manifest fields enumerated (build_contract + execution_routing)
def test_manifest_fields_enumerated(doc: str) -> None:
    for token in (
        "build_contract", "execution_routing", "required_gates",
        "forbidden_paths", "declarative_only",
        "policy_required_sovereign_valve_for_non_dry_run",
    ):
        assert token in doc, f"manifest contract missing: {token}"


# Addendum F.4 -- registry seed specified but NOT written
def test_registry_seed_specified_not_written(doc: str) -> None:
    assert "REGISTRY_SEED_SPECIFIED_NOT_WRITTEN" in doc
    assert "NO_REGISTRY_MUTATION" in doc
    assert "foundup_registry.json" in doc


# Addendum F.5 -- valve requirements explicit
def test_valve_requirements_explicit(doc: str) -> None:
    assert "VALVE_OPEN_WORKTREE_CREATE" in doc
    assert "sovereign" in doc.lower()
    # 11 numbered valve conditions present.
    for n in range(1, 12):
        assert f"\n{n}." in doc, f"valve condition {n} missing"


# Addendum F.6 -- Hermes real-write paths out of scope
def test_hermes_real_write_out_of_scope(doc: str) -> None:
    assert "NO_HERMES_FAM_EXECUTION" in doc
    assert "REDDOG_DOES_NOT_DIRECTLY_WRITE_FILES" in doc


# Addendum F.7 -- no runtime scaffold writer added by this slice
def test_no_runtime_scaffold_writer_added(doc: str) -> None:
    assert "NO_RUNTIME_SCAFFOLD_WRITER" in doc
    # No writer source module exists yet (the executor is a FUTURE slice).
    for candidate in (
        _REPO_ROOT / "modules/foundups/agent/src/foundup_scaffold_writer.py",
        _REPO_ROOT / "modules/foundups/src/foundup_scaffold_writer.py",
        _REPO_ROOT / "modules/foundups/agent/src/scaffold_plan_executor.py",
    ):
        assert not candidate.exists(), f"unexpected runtime writer present: {candidate}"


# Addendum F.8 -- no branch/worktree/file mutation in this slice (scope guards)
def test_scope_guards_present(doc: str) -> None:
    for guard in (
        "DECISION_CONTRACT_ONLY",
        "NO_WORKTREE_CREATION",
        "NO_BRANCH_OR_FILE_MUTATION_IN_THIS_SLICE",
        "NO_SKILLZ_AUTHORING",
    ):
        assert guard in doc, f"scope guard missing: {guard}"


# Addendum F.9 -- HoloIndex INDEX_GAP recorded
def test_holoindex_index_gap_recorded(doc: str) -> None:
    assert "HOLOINDEX_FOUNDUP_SCAFFOLD_CONTRACT_DISCOVERABILITY_PHASE1" in doc
    assert "INDEX_GAP" in doc


# WSP_97 hygiene -- audit doc must be ASCII-clean
def test_contract_doc_is_ascii_clean(doc: str) -> None:
    offenders = [(i + 1, repr(ch)) for i, line in enumerate(doc.splitlines())
                 for ch in line if ord(ch) > 127]
    assert offenders == [], f"non-ASCII in contract doc: {offenders[:8]}"
