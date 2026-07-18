#!/usr/bin/env python3
"""Contract tests for HoloIndex machine-language governance."""

from __future__ import annotations

import json
from pathlib import Path

from holo_index.source_scope import CANONICAL_SOURCE_SCOPE_IDS


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_JSON = REPO_ROOT / "holo_index" / "docs" / "HOLO_INDEX_MACHINE_LANGUAGE_SPEC_0102.json"
INTERFACE_MD = REPO_ROOT / "holo_index" / "INTERFACE.md"
CLI_REFERENCE_MD = REPO_ROOT / "holo_index" / "CLI_REFERENCE.md"
EXPECTED_BASELINE = (
    "navigation_code",
    "navigation_symbols",
    "navigation_wsp",
    "navigation_tests",
    "navigation_skills",
    "navigation_docs",
    "navigation_knowledge",
)
EXPECTED_OPTIONAL = ("navigation_work_ledger", "navigation_vocabulary")


def _payload() -> dict:
    return json.loads(SPEC_JSON.read_text(encoding="utf-8"))


def test_machine_spec_json_is_valid_and_authoritative() -> None:
    assert SPEC_JSON.exists(), f"missing spec file: {SPEC_JSON}"
    payload = _payload()

    assert payload.get("spec_id") == "holo_index.machine_language.v1"
    assert payload.get("source_of_truth_policy"), "missing source_of_truth_policy section"

    policy = payload["source_of_truth_policy"]
    assert policy.get("authoritative_machine_contract") == "holo_index/docs/HOLO_INDEX_MACHINE_LANGUAGE_SPEC_0102.json"
    assert policy.get("human_interface_contract") == "holo_index/INTERFACE.md"
    assert policy.get("operator_menu_atlas_non_normative") == "holo_index/CLI_REFERENCE.md"


def test_machine_spec_references_existing_entrypoints() -> None:
    payload = _payload()
    for reference in payload["entrypoints"].values():
        relative_path = str(reference).split("::", 1)[0]
        assert (REPO_ROOT / relative_path).is_file(), reference

    for layer in payload["runtime_layers"]:
        references = (
            [layer["primary_file"]]
            if "primary_file" in layer
            else layer.get("primary_files", [])
        )
        for relative_path in references:
            assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_machine_spec_collection_and_source_scope_contract_is_exact() -> None:
    payload = _payload()
    collections = {
        item["name"]: item
        for item in payload["collections"]
    }

    assert tuple(payload["baseline_full_refresh_collections"]) == EXPECTED_BASELINE
    assert tuple(payload["optional_collections"]) == EXPECTED_OPTIONAL
    assert set(collections) == set(EXPECTED_BASELINE + EXPECTED_OPTIONAL)
    assert {
        name: collections[name]["source_scope_id"]
        for name in EXPECTED_BASELINE
    } == CANONICAL_SOURCE_SCOPE_IDS
    assert all(not collections[name]["source_scope_id"] for name in EXPECTED_OPTIONAL)


def test_machine_spec_search_and_platform_storage_contract_is_complete() -> None:
    payload = _payload()
    contracts = payload["contracts"]
    response_keys = set(contracts["search_response_required_keys"])
    metadata_keys = set(contracts["search_metadata_keys"])

    assert {
        "symbol_hits",
        "docs_hits",
        "knowledge_hits",
        "docs",
        "knowledge",
        "work_ledger_hits",
        "work_ledger",
    } <= response_keys
    assert {
        "docs_count",
        "knowledge_count",
        "work_ledger_count",
        "retrieval_mode",
        "embedding_backend",
        "backend_quality",
        "quality_gate",
        "routing_active",
        "collection_backend_map",
    } <= metadata_keys
    assert payload["durability"]["ssd_root_default_posix"] == (
        "$XDG_DATA_HOME/foundups/holoindex; "
        "fallback ~/.local/share/foundups/holoindex"
    )


def test_interface_declares_source_of_truth_policy() -> None:
    assert INTERFACE_MD.exists(), f"missing interface file: {INTERFACE_MD}"
    text = INTERFACE_MD.read_text(encoding="utf-8")

    assert "Source-of-truth policy:" in text
    assert "Authoritative machine contract" in text
    assert "non-normative" in text


def test_cli_reference_declares_non_normative_status() -> None:
    assert CLI_REFERENCE_MD.exists(), f"missing cli reference: {CLI_REFERENCE_MD}"
    text = CLI_REFERENCE_MD.read_text(encoding="utf-8")

    assert "not an exhaustive CLI flag list" in text
    assert "Canonical machine schema lives in `holo_index/docs/HOLO_INDEX_MACHINE_LANGUAGE_SPEC_0102.json`." in text

