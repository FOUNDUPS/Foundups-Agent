"""Tests for model AutoResearch output evidence bundles."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src import (
    model_autoresearch_output_evidence_bundle as evidence_module,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_output_evidence_bundle import (
    InMemoryModelAutoResearchOutputEvidenceStore,
    JsonlModelAutoResearchOutputEvidenceStore,
    build_model_autoresearch_output_evidence_record,
    read_model_autoresearch_output_evidence_jsonl,
    rehydrate_model_autoresearch_output_evidence_record,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution import (
    REPO_ROOT,
)


MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "ai_intelligence"
    / "ai_gateway"
    / "src"
    / "model_autoresearch_output_evidence_bundle.py"
)


def _record(response_text: str = "bounded answer"):
    return build_model_autoresearch_output_evidence_record(
        task_id="task-001",
        prompt_digest="sha256:prompt",
        candidate_id="model/panel",
        candidate_topology_digest="model_panel_topology:123",
        role="principal",
        provider="provider",
        model="model-a",
        policy_digest="configured_gateway_runner_policy:abc",
        response_text=response_text,
        latency_ms=10,
        input_tokens=5,
        output_tokens=2,
        cost_estimate_usd=0.01,
    )


def test_output_evidence_record_rehydrates_and_binds_response_digest() -> None:
    record = _record("the cited answer")

    rehydrated = rehydrate_model_autoresearch_output_evidence_record(record.to_dict())

    assert rehydrated.record_id == record.record_id
    assert rehydrated.response_text == "the cited answer"
    assert rehydrated.response_digest.startswith("sha256:")


def test_output_evidence_rejects_tampered_response_text() -> None:
    payload = _record("original answer").to_dict()
    payload["response_text"] = "changed answer"

    try:
        rehydrate_model_autoresearch_output_evidence_record(payload)
    except ValueError as exc:
        assert str(exc) == "model_autoresearch_output_evidence_response_digest_mismatch"
    else:
        raise AssertionError("expected response digest mismatch")


def test_output_evidence_rejects_tampered_record_id() -> None:
    payload = _record("original answer").to_dict()
    payload["record_id"] = "model_autoresearch_output_evidence:forged"

    try:
        rehydrate_model_autoresearch_output_evidence_record(payload)
    except ValueError as exc:
        assert str(exc) == "model_autoresearch_output_evidence_record_id_mismatch"
    else:
        raise AssertionError("expected record id mismatch")


def test_jsonl_store_writes_outside_repo_and_rehydrates_records(tmp_path: Path) -> None:
    path = tmp_path / "runtime" / "model_outputs.jsonl"
    store = JsonlModelAutoResearchOutputEvidenceStore(path, repo_root=REPO_ROOT)

    record_id = store.append(_record("outside repo evidence"))
    records = read_model_autoresearch_output_evidence_jsonl(path, repo_root=REPO_ROOT)

    assert records[0].record_id == record_id
    assert records[0].response_text == "outside repo evidence"
    line = path.read_text(encoding="utf-8").strip()
    assert json.loads(line)["record_id"] == record_id


def test_jsonl_store_fsyncs_record_before_reporting_success(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[int] = []
    monkeypatch.setattr(evidence_module.os, "fsync", calls.append)
    path = tmp_path / "runtime" / "model_outputs.jsonl"
    store = JsonlModelAutoResearchOutputEvidenceStore(path, repo_root=REPO_ROOT)
    store.append(_record("durable evidence"))
    assert len(calls) == 1


def test_jsonl_store_rejects_inside_repo_path() -> None:
    inside = REPO_ROOT / "model_outputs.jsonl"

    try:
        JsonlModelAutoResearchOutputEvidenceStore(inside, repo_root=REPO_ROOT)
    except ValueError as exc:
        assert str(exc) == "model_autoresearch_output_evidence_path_inside_repo"
    else:
        raise AssertionError("expected inside-repo path rejection")


def test_output_evidence_rejects_secret_markers_before_store_write() -> None:
    store = InMemoryModelAutoResearchOutputEvidenceStore()

    try:
        store.append(_record("token=abc123"))
    except ValueError as exc:
        assert str(exc) == "model_autoresearch_output_evidence_secret_detected"
    else:
        raise AssertionError("expected secret rejection")

    assert store.records == []


def test_output_evidence_module_has_no_network_command_runtime_or_holoindex_imports() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "openai",
        "holo_index",
        "pattern_memory",
        "git",
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls

    assert "extension.js" not in source
