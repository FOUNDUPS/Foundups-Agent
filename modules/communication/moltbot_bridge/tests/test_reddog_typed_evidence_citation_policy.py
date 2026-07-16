from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_typed_evidence_citation_policy import (
    SOURCE_CLASS_EXTERNAL_RESEARCH,
    SOURCE_CLASS_MEMEX,
    SOURCE_CLASS_REPO_FILE,
    SOURCE_CLASS_UNKNOWN,
    classify_evidence_ref,
    validate_typed_evidence_citations,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_typed_evidence_citation_policy.py"
)
FILE_REF = "file:docs/work_ledger.schema.json:sha256:file:lines:1"
MEMEX_REF = "memex:sha256:brain-view:sha256:record:current_state"
EXTERNAL_REF = "external:sha256_snapshot:content:sha256_content"


def test_classifies_known_evidence_ref_types() -> None:
    assert classify_evidence_ref(FILE_REF) == SOURCE_CLASS_REPO_FILE
    assert classify_evidence_ref(MEMEX_REF) == SOURCE_CLASS_MEMEX
    assert classify_evidence_ref(EXTERNAL_REF) == SOURCE_CLASS_EXTERNAL_RESEARCH
    assert classify_evidence_ref("http://example.test") == SOURCE_CLASS_UNKNOWN


def test_file_evidence_alone_is_valid_for_current_repo_claim() -> None:
    result = validate_typed_evidence_citations(
        refs=(FILE_REF,),
        allowed_file_refs=(FILE_REF,),
    )

    assert result.accepted is True


def test_memex_can_supplement_file_evidence() -> None:
    result = validate_typed_evidence_citations(
        refs=(FILE_REF, MEMEX_REF),
        allowed_file_refs=(FILE_REF,),
        allowed_memex_refs=(MEMEX_REF,),
    )

    assert result.accepted is True


def test_external_research_can_be_primary_when_file_evidence_is_not_required() -> None:
    result = validate_typed_evidence_citations(
        refs=(EXTERNAL_REF,),
        allowed_file_refs=(),
        allowed_external_refs=(EXTERNAL_REF,),
        require_file_evidence=False,
    )

    assert result.accepted is True


def test_memex_can_supplement_external_research_but_not_replace_it() -> None:
    accepted = validate_typed_evidence_citations(
        refs=(EXTERNAL_REF, MEMEX_REF),
        allowed_file_refs=(),
        allowed_external_refs=(EXTERNAL_REF,),
        allowed_memex_refs=(MEMEX_REF,),
        require_file_evidence=False,
    )
    rejected = validate_typed_evidence_citations(
        refs=(MEMEX_REF,),
        allowed_file_refs=(),
        allowed_memex_refs=(MEMEX_REF,),
        require_file_evidence=False,
    )

    assert accepted.accepted is True
    assert rejected.accepted is False
    assert "memex_cannot_replace_primary_evidence" in rejected.rejection_reasons


def test_memex_cannot_replace_file_evidence_for_repo_audit_finding() -> None:
    result = validate_typed_evidence_citations(
        refs=(MEMEX_REF,),
        allowed_file_refs=(FILE_REF,),
        allowed_memex_refs=(MEMEX_REF,),
    )

    assert result.accepted is False
    assert "memex_cannot_replace_repo_file_evidence" in result.rejection_reasons


def test_unknown_or_unallowed_refs_fail_closed() -> None:
    result = validate_typed_evidence_citations(
        refs=(FILE_REF, "memex:unknown:unknown:identity", "external:unknown", "raw:unknown"),
        allowed_file_refs=(FILE_REF,),
        allowed_memex_refs=(MEMEX_REF,),
    )

    assert result.accepted is False
    assert "unknown_memex_evidence_ref" in result.rejection_reasons
    assert "unknown_external_evidence_ref" in result.rejection_reasons
    assert "unknown_evidence_ref_type" in result.rejection_reasons


def test_typed_citation_policy_is_read_only_by_ast() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_imports = {"subprocess", "requests", "httpx", "sqlite3", "os"}
    forbidden_calls = {"open", "write_text", "write_bytes", "system", "popen"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in forbidden_imports
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in forbidden_imports
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_calls
            if isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls
