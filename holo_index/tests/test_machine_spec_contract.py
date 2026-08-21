#!/usr/bin/env python3
"""Contract tests for HoloIndex machine-language governance."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

import holo_index.query_result_contract as result_contract
import holo_index.query_result_contract_schema as contract_schema
from holo_index.query_result_contract import (
    COLLECTION_NAMES,
    SEARCH_METADATA_KEYS,
    SEARCH_RESPONSE_KEYS,
    SEARCH_RESULT_CONTRACT,
    validate_search_result,
)
from holo_index.core.search_engine import _coerce_priority, _format_hit
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


def _canonical_result() -> dict:
    empty: list[dict] = []
    code = [{
        "need": "contract", "location": "holo_index/query_result_contract.py",
        "similarity": "90.0%", "cube": "holo_index", "type": "code",
        "priority": 5.0, "preview": "contract",
    }]
    backend_map = {name: "sentence_transformers" for name in COLLECTION_NAMES}
    space_map = {name: "sha256:" + ("a" * 64) for name in COLLECTION_NAMES}
    return {
        "code_hits": code, "wsp_hits": empty, "test_hits": empty, "code": code,
        "wsps": empty, "tests": empty, "skills": empty, "skill_hits": empty,
        "symbol_hits": empty, "docs_hits": empty, "knowledge_hits": empty,
        "docs": empty, "knowledge": empty, "work_ledger_hits": empty,
        "work_ledger": empty,
        "metadata": {
            "query": "contract", "code_count": 1, "wsp_count": 0,
            "test_count": 0, "skill_count": 0, "symbol_count": 0,
            "docs_count": 0, "knowledge_count": 0, "work_ledger_count": 0,
            "timestamp": "2026-08-15T00:00:00+00:00", "cached": False,
            "retrieval_mode": "semantic", "embedding_backend": "sentence_transformers",
            "backend_quality": "production", "quality_gate": "PASS",
            "tier0_module_target": None,
            "routing_active": False, "collection_backend_map": backend_map,
            "collection_embedding_space_map": space_map,
        },
    }


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
    search_contract = contracts["search_response_contract"]
    response_keys = set(search_contract["response_keys"])
    metadata_keys = set(search_contract["metadata_keys"])

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
        "tier0_module_target",
    } <= metadata_keys
    assert payload["durability"]["ssd_root_default_posix"] == (
        "$XDG_DATA_HOME/foundups/holoindex; "
        "fallback ~/.local/share/foundups/holoindex"
    )


def test_executable_search_contract_matches_authoritative_machine_spec() -> None:
    contract = _payload()["contracts"]["search_response_contract"]
    assert SEARCH_RESULT_CONTRACT == contract
    assert tuple(contract["response_keys"]) == SEARCH_RESPONSE_KEYS
    assert tuple(contract["metadata_keys"]) == SEARCH_METADATA_KEYS
    assert set(EXPECTED_BASELINE + EXPECTED_OPTIONAL) == COLLECTION_NAMES
    validate_search_result(_canonical_result(), expected_query="contract")


def test_exact_metadata_document_provenance_is_schema_supported() -> None:
    raw = _canonical_result()
    raw["code_hits"] = raw["code"] = []
    raw["metadata"]["code_count"] = 0
    exact = {
        "title": "Moltbot Bridge",
        "summary": "Module contract",
        "path": "modules/communication/moltbot_bridge/README.md",
        "slice_id": None,
        "similarity": None,
        "retrieval_provenance": "exact_metadata",
        "type": "module_readme",
        "priority": 8.0,
    }
    raw["docs_hits"] = raw["docs"] = [exact]
    raw["metadata"]["docs_count"] = 1

    validate_search_result(raw, expected_query="contract")

    forged = deepcopy(raw)
    forged["docs_hits"][0].pop("retrieval_provenance")
    with pytest.raises(ValueError, match="query_evidence_schema_invalid"):
        validate_search_result(forged, expected_query="contract")


@pytest.mark.parametrize(
    "target",
    [
        "modules/communication/moltbot_bridge/src",
        "modules/communication/../escape",
        "modules/communication/.hidden",
        "modules\\communication\\moltbot_bridge",
        "outside/communication/moltbot_bridge",
        "",
    ],
)
def test_tier0_module_target_metadata_rejects_noncanonical_paths(
    target: str,
) -> None:
    raw = _canonical_result()
    raw["metadata"]["tier0_module_target"] = target

    with pytest.raises(ValueError, match="query_evidence_schema_invalid"):
        validate_search_result(raw, expected_query="contract")


def test_tier0_module_target_accepts_canonical_path_or_null() -> None:
    for target in (None, "modules/communication/moltbot_bridge"):
        raw = _canonical_result()
        raw["metadata"]["tier0_module_target"] = target
        validate_search_result(raw, expected_query="contract")


@pytest.mark.parametrize(
    ("kind", "bucket", "alias", "count", "metadata", "document"),
    [
        ("code", "code_hits", "code", "code_count", {"need": "n", "type": "code", "cube": "c", "priority": 5}, "holo_index/a.py:run()"),
        ("test", "test_hits", "tests", "test_count", {"test_id": "t", "path": "holo_index/tests/test_a.py", "description": "d", "capabilities": "c", "priority": 4}, "d"),
        ("skill", "skill_hits", "skills", "skill_count", {"skill_name": "s", "description": "d", "primary_agent": "0102", "intent_type": "audit", "promotion_state": "PROVEN", "path": "skillz/s/SKILLz.md", "priority": 3}, "d"),
        ("docs", "docs_hits", "docs", "docs_count", {"title": "d", "summary": "s", "path": "holo_index/README.md", "type": "docs", "priority": 2}, "d"),
        ("knowledge", "knowledge_hits", "knowledge", "knowledge_count", {"title": "k", "summary": "s", "path": "WSP_knowledge/docs/Papers/k.md", "type": "knowledge", "priority": 2}, "d"),
        ("wsp", "wsp_hits", "wsps", "wsp_count", {"wsp": "WSP_97", "title": "w", "summary": "s", "path": "WSP_framework/src/WSP_97.md", "cube": "WSP", "priority": 5}, "d"),
        ("symbol", "symbol_hits", "", "symbol_count", {"wsp": None, "title": "run", "summary": "s", "path": "holo_index/a.py", "cube": None, "priority": 1}, "d"),
        ("work_ledger", "work_ledger_hits", "work_ledger", "work_ledger_count", {"wsp": None, "title": "slice", "summary": "active", "path": "docs/work.json", "cube": None, "priority_num": 4}, "d"),
    ],
)
def test_real_producer_hit_families_satisfy_machine_contract(
    kind: str, bucket: str, alias: str, count: str,
    metadata: dict, document: str,
) -> None:
    raw = _canonical_result()
    raw["code_hits"] = raw["code"] = []
    raw["metadata"]["code_count"] = 0
    priority = _coerce_priority(metadata)
    hit = _format_hit(kind, metadata, document, 0.9, 1.0, priority)
    hit.pop("_sort_key")
    raw[bucket] = [hit]
    if alias:
        raw[alias] = [hit]
    raw["metadata"][count] = 1
    assert isinstance(hit["priority"], float)
    validate_search_result(raw, expected_query="contract")


@pytest.mark.parametrize(
    "case",
    [
        "missing", "unknown", "alias", "count", "query", "score",
        "cross_bucket", "priority_type", "similarity_type", "nonfinite",
        "huge_priority", "huge_confidence",
        "backend_key", "backend_value", "fingerprint",
    ],
)
def test_executable_search_contract_rejects_noncanonical_evidence(case: str) -> None:
    raw = deepcopy(_canonical_result())
    if case == "missing":
        raw.pop("tests")
    elif case == "unknown":
        raw["extra"] = []
    elif case == "alias":
        raw["code"] = []
    elif case == "count":
        raw["metadata"]["code_count"] = 0
    elif case == "query":
        raw["metadata"]["query"] = "substituted"
    elif case == "score":
        raw["code_hits"][0]["score"] = 1.0
    elif case == "cross_bucket":
        raw["code_hits"][0]["title"] = "forged"
    elif case == "priority_type":
        raw["code_hits"][0]["priority"] = "high"
    elif case == "similarity_type":
        raw["code_hits"][0]["similarity"] = 0.9
    elif case == "nonfinite":
        raw["code_hits"][0]["confidence"] = float("nan")
    elif case == "huge_priority":
        raw["code_hits"][0]["priority"] = 10**10000
    elif case == "huge_confidence":
        raw["code_hits"][0]["confidence"] = -(10**10000)
    elif case == "backend_key":
        raw["metadata"]["collection_backend_map"]["extra"] = "sentence_transformers"
    elif case == "backend_value":
        raw["metadata"]["collection_backend_map"]["navigation_code"] = "forged"
    else:
        raw["metadata"]["collection_embedding_space_map"]["navigation_code"] = "forged"
    with pytest.raises(ValueError, match="query_evidence_schema_invalid"):
        validate_search_result(raw, expected_query="contract")


def test_declared_hit_rule_controls_runtime_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _canonical_result()
    monkeypatch.setitem(result_contract._HIT_RULES, "priority", "unsupported")
    with pytest.raises(ValueError, match="query_evidence_schema_invalid"):
        validate_search_result(raw, expected_query="contract")
    monkeypatch.setitem(result_contract._HIT_RULES, "priority", "string_or_null")
    with pytest.raises(ValueError, match="query_evidence_schema_invalid"):
        validate_search_result(raw, expected_query="contract")
    raw["code_hits"][0]["priority"] = "high"
    validate_search_result(raw, expected_query="contract")


def test_declared_metadata_rule_controls_runtime_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _canonical_result()
    monkeypatch.setitem(
        result_contract._METADATA_RULES["field_rules"], "cached", "string"
    )
    with pytest.raises(ValueError, match="query_evidence_schema_invalid"):
        validate_search_result(raw, expected_query="contract")
    raw["metadata"]["cached"] = "false"
    validate_search_result(raw, expected_query="contract")


@pytest.mark.parametrize(
    ("rule_group", "field", "rule"),
    [
        ("hit", "confidence", "unsupported"),
        ("hit", "confidence", []),
        ("hit", "confidence", {}),
        ("hit", "confidence", None),
        ("hit", "confidence", 1),
        ("metadata", "collection_backend_map", "map:unsupported"),
        ("hit", "undeclared_field", "string"),
    ],
)
def test_all_declared_rules_compile_before_evidence_use(
    monkeypatch: pytest.MonkeyPatch, rule_group: str, field: str, rule: object
) -> None:
    rules = (
        result_contract._HIT_RULES
        if rule_group == "hit"
        else result_contract._METADATA_RULES["field_rules"]
    )
    monkeypatch.setitem(rules, field, rule)
    with pytest.raises(RuntimeError, match="holoindex_machine_contract_invalid"):
        result_contract._validate_declared_rules()


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("hit_schemas", []),
        ("hit_schemas", {"code": []}),
        ("hit_schemas", {"code": {"required": {}, "optional": []}}),
        ("hit_value_rules", []),
        ("metadata_value_rules", None),
    ],
)
def test_machine_loader_normalizes_malformed_structures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str, value: object
) -> None:
    payload = json.loads(SPEC_JSON.read_text(encoding="utf-8"))
    payload["contracts"]["search_response_contract"][key] = value
    malformed = tmp_path / "machine.json"
    malformed.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(contract_schema, "MACHINE_SPEC_PATH", malformed)
    with pytest.raises(RuntimeError, match="holoindex_machine_contract_invalid"):
        contract_schema.load_search_result_contract()


@pytest.mark.parametrize(
    ("group", "key", "value"),
    [
        ("contract", "response_keys", None),
        ("contract", "response_keys", [[]]),
        ("contract", "response_keys", ["metadata", "metadata"]),
        ("contract", "metadata_keys", None),
        ("contract", "collection_names", None),
        ("contract", "collection_backends", [{}]),
        ("bucket_schemas", "code_hits", None),
        ("bucket_schemas", "code_hits", ["unknown"]),
        ("aliases", "code", []),
        ("aliases", "code", "unknown_hits"),
        ("counts", "code_count", []),
        ("counts", "code_count", "unknown_hits"),
    ],
)
def test_machine_loader_normalizes_malformed_nested_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    group: str,
    key: str,
    value: object,
) -> None:
    payload = json.loads(SPEC_JSON.read_text(encoding="utf-8"))
    contract = payload["contracts"]["search_response_contract"]
    target = contract if group == "contract" else contract[group]
    target[key] = value
    malformed = tmp_path / "machine.json"
    malformed.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(contract_schema, "MACHINE_SPEC_PATH", malformed)
    with pytest.raises(RuntimeError, match="holoindex_machine_contract_invalid"):
        contract_schema.load_search_result_contract()


def test_machine_loader_rejects_non_mapping_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = json.loads(SPEC_JSON.read_text(encoding="utf-8"))
    payload["contracts"]["search_response_contract"] = []
    malformed = tmp_path / "machine.json"
    malformed.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(contract_schema, "MACHINE_SPEC_PATH", malformed)
    with pytest.raises(RuntimeError, match="holoindex_machine_contract_invalid"):
        contract_schema.load_search_result_contract()


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

