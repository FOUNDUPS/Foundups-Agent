#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for AI Overseer M2M skill execution shim."""

from __future__ import annotations

from pathlib import Path

from modules.ai_intelligence.ai_overseer.src.ai_overseer import AIIntelligenceOverseer
from modules.ai_intelligence.ai_overseer.src import m2m_holo_retrieval_benchmark


def _make_overseer(repo_root: Path) -> AIIntelligenceOverseer:
    overseer = object.__new__(AIIntelligenceOverseer)
    overseer.repo_root = repo_root
    overseer._m2m_sentinel = None
    return overseer


def _write_skill(repo_root: Path, skill_name: str) -> Path:
    skill_path = (
        repo_root
        / "modules"
        / "ai_intelligence"
        / "ai_overseer"
        / "skillz"
        / skill_name
        / "SKILLz.md"
    )
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(f"# {skill_name}\n", encoding="utf-8")
    return skill_path


def test_execute_m2m_skill_unknown_returns_fail_envelope(tmp_path: Path):
    overseer = _make_overseer(tmp_path)
    result = overseer.execute_m2m_skill("not_real", m2m=True)

    assert result["STATUS"] == "FAIL"
    assert result["RESULT"]["result"]["success"] is False
    assert "Unknown M2M skill" in result["RESULT"]["result"]["error"]


def test_execute_m2m_skill_missing_skill_doc_returns_fail(tmp_path: Path):
    overseer = _make_overseer(tmp_path)
    result = overseer.execute_m2m_skill("m2m_compile_gate", m2m=False)

    assert result["status"] == "FAIL"
    assert "Missing SKILLz.md" in result["result"]["error"]


def test_execute_m2m_compile_gate_success(tmp_path: Path):
    _write_skill(tmp_path, "m2m_compile_gate")
    source = tmp_path / "docs" / "sample.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        "# Sample\n\n## Settings\n- **Mode**: Safe\n- **WSP**: 99\n",
        encoding="utf-8",
    )

    overseer = _make_overseer(tmp_path)
    result = overseer.execute_m2m_skill(
        "m2m_compile_gate",
        {"source_path": "docs/sample.md", "use_qwen": False},
        m2m=False,
    )

    assert result["status"] == "OK"
    assert result["result"]["success"] is True
    staged = tmp_path / result["result"]["staged_path"]
    assert staged.exists()


def test_execute_m2m_compile_gate_rejects_skill_file_content(tmp_path: Path):
    skill_file = _write_skill(tmp_path, "m2m_compile_gate")
    skill_file.write_text(
        "I AM 0102\nφ=1.618\n7.05Hz resonance\nVI scaffolding\n",
        encoding="utf-8",
    )

    overseer = _make_overseer(tmp_path)
    result = overseer.execute_m2m_skill(
        "m2m_compile_gate",
        {"source_path": "modules/ai_intelligence/ai_overseer/skillz/m2m_compile_gate/SKILLz.md"},
        m2m=False,
    )

    assert result["status"] == "FAIL"
    assert result["result"]["boot_prompt"] is True


def test_execute_m2m_stage_promote_safe_requires_target_path(tmp_path: Path):
    _write_skill(tmp_path, "m2m_stage_promote_safe")
    overseer = _make_overseer(tmp_path)

    result = overseer.execute_m2m_skill(
        "m2m_stage_promote_safe",
        {"staged_path": ".m2m/staged/foo/bar_M2M.yaml"},
        m2m=False,
    )

    assert result["status"] == "FAIL"
    assert "target_path is required" in result["result"]["error"]


def test_execute_m2m_holo_benchmark_routes_verified_result(monkeypatch, tmp_path: Path):
    _write_skill(tmp_path, "m2m_holo_retrieval_benchmark")
    overseer = _make_overseer(tmp_path)
    expected = {
        "success": True,
        "benchmark_run": {"receipt_id": "run"},
        "verification": {"accepted": True},
    }
    monkeypatch.setattr(
        m2m_holo_retrieval_benchmark,
        "execute_m2m_holo_retrieval_benchmark",
        lambda **kwargs: expected,
    )

    result = overseer.execute_m2m_skill(
        "m2m_holo_retrieval_benchmark", {}, m2m=False
    )

    assert result["status"] == "OK"
    assert result["result"] == expected
