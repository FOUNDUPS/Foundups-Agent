# -*- coding: utf-8 -*-
"""Tests for RTK_OPENCLAW_HERMES_ADAPTER_DRYRUN_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.infrastructure.token_efficiency.src.compute_governor import (
    Routing,
    get_compute_governor,
    reset_compute_governor,
)
from modules.infrastructure.token_efficiency.src.rtk_openclaw_hermes_adapter_dryrun import (
    RtkAdapterDryRunDecision,
    RtkAdapterDryRunRejection,
    RtkAdapterOutputMode,
    RtkAdapterSurface,
    plan_rtk_openclaw_hermes_adapter_dry_run,
)
from modules.infrastructure.token_efficiency.src.telemetry_service import (
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
    / "rtk_openclaw_hermes_adapter_dryrun.py"
)


def setup_function() -> None:
    reset_compute_governor()
    reset_telemetry_store()


def _raw_output() -> str:
    return "\n".join(f"module_{idx}.py" for idx in range(100))


def test_accepts_openclaw_candidate_without_rewriting_output() -> None:
    result = plan_rtk_openclaw_hermes_adapter_dry_run(
        surface=RtkAdapterSurface.OPENCLAW,
        command="ls -la",
        command_output=_raw_output(),
        candidate_output="100 python modules",
        raw_ref="raw_ref:openclaw-output:sha256",
        ctx_holo_present=True,
    )

    assert result.accepted is True
    assert result.decision == RtkAdapterDryRunDecision.ACCEPT
    assert result.surface == RtkAdapterSurface.OPENCLAW
    assert result.output_mode == (
        RtkAdapterOutputMode.DRY_RUN_CANDIDATE_MEASURED_RAW_OUTPUT_PRESERVED
    )
    assert result.compute_routing == Routing.ALLOW_EVALUATION_DRY_RUN.value
    assert result.evaluation_decision is not None
    assert result.bytes_saved > 0
    assert result.tokens_saved > 0
    assert result.output_rewritten is False
    assert result.raw_output_preserved is True
    assert result.openclaw_wired is False
    assert result.command_executed is False
    assert result.rtk_invoked is False

    events = get_telemetry_store().get_all()
    assert len(events) == 1
    assert events[0].source_layer == SourceLayer.RTK_EVALUATION


def test_accepts_hermes_candidate_without_hermes_wiring() -> None:
    result = plan_rtk_openclaw_hermes_adapter_dry_run(
        surface="hermes",
        command="echo scaffold",
        command_output="scaffold line\n" * 50,
        candidate_output="scaffold repeated 50 times",
        raw_ref="raw_ref:hermes-output:sha256",
    )

    assert result.accepted is True
    assert result.surface == RtkAdapterSurface.HERMES
    assert result.hermes_wired is False
    assert result.wre_wired is False
    assert result.extension_wired is False


def test_rejects_unsupported_surface_before_telemetry() -> None:
    result = plan_rtk_openclaw_hermes_adapter_dry_run(
        surface="WRE_LIVE",
        command="ls -la",
        command_output=_raw_output(),
        candidate_output="100 files",
        raw_ref="raw_ref:wre-output",
    )

    assert result.accepted is False
    assert result.surface is None
    assert RtkAdapterDryRunRejection.UNSUPPORTED_SURFACE.value in result.rejection_reasons
    assert result.output_mode == RtkAdapterOutputMode.RAW_OUTPUT_PRESERVED
    assert get_telemetry_store().count() == 0


def test_rejects_missing_raw_ref() -> None:
    result = plan_rtk_openclaw_hermes_adapter_dry_run(
        surface=RtkAdapterSurface.OPENCLAW,
        command="ls -la",
        command_output=_raw_output(),
        candidate_output="100 files",
        raw_ref="",
    )

    assert result.accepted is False
    assert RtkAdapterDryRunRejection.RAW_REF_REQUIRED.value in result.rejection_reasons
    assert RtkAdapterDryRunRejection.RTK_EVALUATION_REJECTED.value in result.rejection_reasons


def test_rejects_empty_candidate_output() -> None:
    result = plan_rtk_openclaw_hermes_adapter_dry_run(
        surface=RtkAdapterSurface.OPENCLAW,
        command="ls -la",
        command_output=_raw_output(),
        candidate_output="",
        raw_ref="raw_ref:empty-candidate",
    )

    assert result.accepted is False
    assert (
        RtkAdapterDryRunRejection.CANDIDATE_OUTPUT_REQUIRED.value
        in result.rejection_reasons
    )


def test_rejects_sensitive_raw_output_via_governor_and_evaluator() -> None:
    result = plan_rtk_openclaw_hermes_adapter_dry_run(
        surface=RtkAdapterSurface.OPENCLAW,
        command="cat .env",
        command_output="token=sk-secret123456789",
        candidate_output="environment variables summary",
        raw_ref="raw_ref:env",
    )

    assert result.accepted is False
    assert (
        RtkAdapterDryRunRejection.COMPUTE_DECISION_NOT_ALLOW_EVALUATION.value
        in result.rejection_reasons
    )
    assert RtkAdapterDryRunRejection.RTK_EVALUATION_REJECTED.value in result.rejection_reasons
    assert result.bytes_saved == 0
    assert result.output_rewritten is False


def test_rejects_security_command_even_with_short_candidate() -> None:
    result = plan_rtk_openclaw_hermes_adapter_dry_run(
        surface=RtkAdapterSurface.HERMES,
        command="npm audit",
        command_output="0 vulnerabilities",
        candidate_output="clean",
        raw_ref="raw_ref:npm-audit",
    )

    assert result.accepted is False
    assert result.compute_routing == Routing.BYPASS_REQUIRED.value
    assert (
        RtkAdapterDryRunRejection.COMPUTE_DECISION_NOT_ALLOW_EVALUATION.value
        in result.rejection_reasons
    )


def test_rejects_no_positive_savings_from_p5_evaluator() -> None:
    result = plan_rtk_openclaw_hermes_adapter_dry_run(
        surface=RtkAdapterSurface.OPENCLAW,
        command="ls -la",
        command_output="tiny",
        candidate_output="longer than tiny",
        raw_ref="raw_ref:tiny",
    )

    assert result.accepted is False
    assert RtkAdapterDryRunRejection.RTK_EVALUATION_REJECTED.value in result.rejection_reasons
    assert "NO_POSITIVE_SAVINGS" in result.rejection_reasons


def test_rejects_injected_compute_decision_with_runtime_reindex_enabled() -> None:
    decision = get_compute_governor().get_routing_recommendation(
        command="ls -la",
        output_preview=_raw_output(),
    ).to_dict()
    decision["runtime_reindex_allowed"] = True

    result = plan_rtk_openclaw_hermes_adapter_dry_run(
        surface=RtkAdapterSurface.OPENCLAW,
        command="ls -la",
        command_output=_raw_output(),
        candidate_output="100 files",
        raw_ref="raw_ref:reindex",
        compute_decision=decision,
    )

    assert result.accepted is False
    assert RtkAdapterDryRunRejection.RUNTIME_REINDEX_FORBIDDEN.value in result.rejection_reasons


def test_result_does_not_serialize_raw_command_output_candidate_or_raw_ref() -> None:
    result = plan_rtk_openclaw_hermes_adapter_dry_run(
        surface=RtkAdapterSurface.OPENCLAW,
        command="echo secret phrase",
        command_output="raw command output unique phrase",
        candidate_output="candidate unique phrase",
        raw_ref="raw_ref:unique-secret-reference",
    )

    encoded = json.dumps(result.to_dict(), sort_keys=True)
    assert "echo secret phrase" not in encoded
    assert "raw command output unique phrase" not in encoded
    assert "candidate unique phrase" not in encoded
    assert "raw_ref:unique-secret-reference" not in encoded


def test_receipt_id_deterministic_for_same_inputs() -> None:
    first = plan_rtk_openclaw_hermes_adapter_dry_run(
        surface=RtkAdapterSurface.OPENCLAW,
        command="ls -la",
        command_output=_raw_output(),
        candidate_output="100 files",
        raw_ref="raw_ref:deterministic",
    )
    second = plan_rtk_openclaw_hermes_adapter_dry_run(
        surface=RtkAdapterSurface.OPENCLAW,
        command="ls -la",
        command_output=_raw_output(),
        candidate_output="100 files",
        raw_ref="raw_ref:deterministic",
    )

    assert first.adapter_receipt_id == second.adapter_receipt_id
    assert first.command_digest == second.command_digest
    assert first.raw_output_digest == second.raw_output_digest


def test_m2m_outputs_preserve_dry_run_invariants() -> None:
    result = plan_rtk_openclaw_hermes_adapter_dry_run(
        surface=RtkAdapterSurface.OPENCLAW,
        command="ls -la",
        command_output=_raw_output(),
        candidate_output="100 files",
        raw_ref="raw_ref:m2m",
    )

    compact = result.to_m2m_compact()
    yaml_text = result.to_m2m_yaml()
    assert "RTK_SEAM" in compact
    assert "REWRITE:false" in compact
    assert "RTK_OPENCLAW_HERMES_ADAPTER_DRY_RUN:" in yaml_text
    assert "output_rewritten: False" in yaml_text
    assert "raw_output_preserved: True" in yaml_text


def test_to_dict_is_json_serializable() -> None:
    result = plan_rtk_openclaw_hermes_adapter_dry_run(
        surface=RtkAdapterSurface.HERMES,
        command="echo hello",
        command_output="hello\n" * 20,
        candidate_output="hello repeated",
        raw_ref="raw_ref:json",
    )

    encoded = json.dumps(result.to_dict(), sort_keys=True)
    assert result.adapter_receipt_id in encoded


def test_ast_boundary_no_runtime_execution_live_wiring_or_holoindex_mutation() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_imports = {
        "subprocess",
        "os",
        "socket",
        "requests",
        "httpx",
        "sqlite3",
        "holo_index",
        "agent_db",
        "openclaw_supervisor",
        "hermes_job_executor",
        "wre_core",
    }
    forbidden_calls = {
        "Popen",
        "system",
        "popen",
        "open",
        "index_all",
        "index_code",
        "index_docs",
        "execute",
        "create_autonomous_task",
        "enqueue",
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
    assert all(not item.startswith("rtk.") for item in imports)
    assert "rtk" not in imports
    assert calls.isdisjoint(forbidden_calls)
