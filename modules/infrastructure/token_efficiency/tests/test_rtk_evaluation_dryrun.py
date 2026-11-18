# -*- coding: utf-8 -*-
"""Tests for RTK_EVALUATION_DRY_RUN_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.infrastructure.token_efficiency.src.compute_governor import (
    Routing,
    get_compute_governor,
    reset_compute_governor,
)
from modules.infrastructure.token_efficiency.src.rtk_evaluation_dryrun import (
    RtkDryRunDecision,
    RtkDryRunRejection,
    evaluate_rtk_candidate_dry_run,
)
from modules.infrastructure.token_efficiency.src.telemetry_service import (
    CompressionStatus,
    SourceLayer,
    get_telemetry_store,
    reset_telemetry_store,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "infrastructure"
    / "token_efficiency"
    / "src"
    / "rtk_evaluation_dryrun.py"
)


def _decision(command: str = "ls -la"):
    reset_compute_governor()
    return get_compute_governor().get_routing_recommendation(
        command=command,
        output_preview="alpha.txt\nbeta.txt\n",
        ctx_holo_present=True,
        index_gap_detected=False,
    )


def setup_function() -> None:
    reset_telemetry_store()
    reset_compute_governor()


def test_accepts_safe_candidate_and_records_measurement_telemetry() -> None:
    raw = "\n".join(f"file_{idx}.py" for idx in range(80))
    candidate = "80 python files"

    result = evaluate_rtk_candidate_dry_run(
        command="ls -la",
        raw_output=raw,
        candidate_output=candidate,
        raw_ref="raw_ref:ls-output:sha256",
        compute_decision=_decision(),
    )

    assert result.accepted is True
    assert result.decision == RtkDryRunDecision.ACCEPT
    assert result.bytes_saved > 0
    assert result.tokens_saved > 0
    assert result.savings_ratio > 0
    assert result.dry_run_only is True
    assert result.rtk_invoked is False
    assert result.command_executed is False
    assert result.compression_performed is False
    assert result.raw_content_persisted is False

    events = get_telemetry_store().get_all()
    assert len(events) == 1
    assert events[0].source_layer == SourceLayer.RTK_EVALUATION
    assert events[0].compression_status == CompressionStatus.COMPRESSED
    assert events[0].raw_ref_present is True


def test_rejects_when_compute_governor_did_not_allow_evaluation() -> None:
    decision = get_compute_governor().classify_command_for_evaluation("npm audit")
    assert decision.routing == Routing.BYPASS_REQUIRED

    result = evaluate_rtk_candidate_dry_run(
        command="npm audit",
        raw_output="audit output",
        candidate_output="summary",
        raw_ref="raw_ref:audit",
        compute_decision=decision,
    )

    assert result.accepted is False
    assert (
        RtkDryRunRejection.COMPUTE_DECISION_NOT_ALLOW_EVALUATION.value
        in result.rejection_reasons
    )


def test_rejects_raw_output_that_requires_bypass() -> None:
    result = evaluate_rtk_candidate_dry_run(
        command="cat .env",
        raw_output="API_KEY=sk-secret123456",
        candidate_output="config summary",
        raw_ref="raw_ref:env",
        compute_decision=_decision("cat .env"),
    )

    assert result.accepted is False
    assert RtkDryRunRejection.RAW_OUTPUT_REQUIRES_BYPASS.value in result.rejection_reasons
    assert result.bypass_class is not None
    assert get_telemetry_store().get_all()[0].compression_status == CompressionStatus.BYPASSED


def test_rejects_candidate_output_that_requires_bypass() -> None:
    result = evaluate_rtk_candidate_dry_run(
        command="echo hello",
        raw_output="hello world\n" * 20,
        candidate_output="token=sk-secret123456",
        raw_ref="raw_ref:echo",
        compute_decision=_decision("echo hello"),
    )

    assert result.accepted is False
    assert (
        RtkDryRunRejection.CANDIDATE_OUTPUT_REQUIRES_BYPASS.value
        in result.rejection_reasons
    )


def test_rejects_without_raw_ref_recovery_path() -> None:
    result = evaluate_rtk_candidate_dry_run(
        command="ls -la",
        raw_output="a\nb\nc\n",
        candidate_output="3 files",
        raw_ref="",
        compute_decision=_decision(),
    )

    assert result.accepted is False
    assert RtkDryRunRejection.RAW_REF_REQUIRED.value in result.rejection_reasons


def test_rejects_empty_candidate_output() -> None:
    result = evaluate_rtk_candidate_dry_run(
        command="ls -la",
        raw_output="a\nb\nc\n",
        candidate_output="",
        raw_ref="raw_ref:ls",
        compute_decision=_decision(),
    )

    assert result.accepted is False
    assert RtkDryRunRejection.CANDIDATE_OUTPUT_REQUIRED.value in result.rejection_reasons


def test_rejects_candidate_with_no_positive_savings() -> None:
    result = evaluate_rtk_candidate_dry_run(
        command="ls -la",
        raw_output="tiny",
        candidate_output="longer than tiny",
        raw_ref="raw_ref:tiny",
        compute_decision=_decision(),
    )

    assert result.accepted is False
    assert RtkDryRunRejection.NO_POSITIVE_SAVINGS.value in result.rejection_reasons


def test_rejects_runtime_reindex_flag_on_compute_decision() -> None:
    decision = _decision().to_dict()
    decision["runtime_reindex_allowed"] = True

    result = evaluate_rtk_candidate_dry_run(
        command="ls -la",
        raw_output="a\nb\nc\n",
        candidate_output="3 files",
        raw_ref="raw_ref:ls",
        compute_decision=decision,
    )

    assert result.accepted is False
    assert RtkDryRunRejection.RUNTIME_REINDEX_FORBIDDEN.value in result.rejection_reasons


def test_result_does_not_serialize_raw_output_or_candidate_output() -> None:
    result = evaluate_rtk_candidate_dry_run(
        command="ls -la",
        raw_output="very specific raw payload",
        candidate_output="specific candidate payload",
        raw_ref="raw_ref:payload",
        compute_decision=_decision(),
    )
    encoded = json.dumps(result.to_dict(), sort_keys=True)

    assert "very specific raw payload" not in encoded
    assert "specific candidate payload" not in encoded
    assert "raw_ref:payload" not in encoded


def test_result_is_deterministic_for_same_inputs() -> None:
    first = evaluate_rtk_candidate_dry_run(
        command="ls -la",
        raw_output="a\nb\nc\n",
        candidate_output="3 files",
        raw_ref="raw_ref:ls",
        compute_decision=_decision(),
    )
    second = evaluate_rtk_candidate_dry_run(
        command="ls -la",
        raw_output="a\nb\nc\n",
        candidate_output="3 files",
        raw_ref="raw_ref:ls",
        compute_decision=_decision(),
    )

    assert first.evaluation_id == second.evaluation_id
    assert first.raw_output_digest == second.raw_output_digest
    assert first.candidate_output_digest == second.candidate_output_digest


def test_m2m_outputs_include_dry_run_status() -> None:
    result = evaluate_rtk_candidate_dry_run(
        command="ls -la",
        raw_output="a\nb\nc\n",
        candidate_output="3 files",
        raw_ref="raw_ref:ls",
        compute_decision=_decision(),
    )

    compact = result.to_m2m_compact()
    yaml_text = result.to_m2m_yaml()
    assert "RTK_EVAL" in compact
    assert "dry_run_only: True" in yaml_text
    assert "rtk_invoked: False" in yaml_text


def test_ast_boundary_no_rtk_subprocess_command_execution_or_persistence() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_imports = {
        "subprocess",
        "os",
        "socket",
        "requests",
        "httpx",
        "sqlite3",
        "rtk",
        "holo_index",
        "agent_db",
    }
    forbidden_calls = {
        "run",
        "Popen",
        "system",
        "popen",
        "open",
        "index_all",
        "index_code",
        "index_docs",
        "compress",
        "execute",
        "create_autonomous_task",
    }
    imports = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    assert imports.isdisjoint(forbidden_imports)
    assert calls.isdisjoint(forbidden_calls)
