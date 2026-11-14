"""Semantic-first HoloIndex contract for WRE memory preflight."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from modules.infrastructure.wre_core.recursive_improvement.src import memory_preflight as mp


def _bundle_payload(mode: str, backend: str) -> str:
    return json.dumps(
        {
            "ok": True,
            "task_retrieval": {
                "metadata": {
                    "retrieval_mode": mode,
                    "embedding_backend": backend,
                    "routing_active": False,
                }
            },
            "structured_memory": {
                "artifacts": [
                    {
                        "relative_path": "README.md",
                        "path": "modules/demo/README.md",
                        "tier": 0,
                        "required": True,
                        "exists": True,
                    },
                    {
                        "relative_path": "INTERFACE.md",
                        "path": "modules/demo/INTERFACE.md",
                        "tier": 0,
                        "required": True,
                        "exists": True,
                    },
                ]
            },
        }
    )


def test_semantic_mode_is_default_and_clears_inherited_lexical_flags():
    assert mp._resolve_holo_retrieval_mode({}) == "semantic"
    assert mp._resolve_holo_retrieval_mode({"WRE_HOLO_RETRIEVAL_MODE": "invalid"}) == "semantic"

    env = mp._build_holo_query_env(
        {"HOLO_SKIP_MODEL": "1", "HOLO_OFFLINE": "1", "KEEP_ME": "yes"},
        "semantic",
    )

    assert "HOLO_SKIP_MODEL" not in env
    assert env["HOLO_OFFLINE"] == "1"
    assert env["HOLOINDEX_QUERY_READONLY"] == "1"
    assert env["HOLO_SILENT"] == "1"
    assert env["KEEP_ME"] == "yes"


def test_explicit_lexical_mode_sets_skip_model():
    assert mp._resolve_holo_retrieval_mode({"WRE_HOLO_RETRIEVAL_MODE": "lexical"}) == "lexical"
    env = mp._build_holo_query_env({}, "lexical")
    assert env["HOLO_SKIP_MODEL"] == "1"
    assert env["HOLOINDEX_QUERY_READONLY"] == "1"


def test_holo_bundle_receipts_semantic_backend(monkeypatch, tmp_path):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs["env"]
        return SimpleNamespace(
            returncode=0,
            stdout=_bundle_payload("semantic", "sentence_transformers"),
            stderr="",
        )

    monkeypatch.delenv("WRE_HOLO_RETRIEVAL_MODE", raising=False)
    monkeypatch.setenv("HOLO_SKIP_MODEL", "1")
    monkeypatch.setenv("HOLO_OFFLINE", "1")
    monkeypatch.setattr(mp.subprocess, "run", fake_run)

    bundle = mp.MemoryPreflightGuard(tmp_path)._retrieve_via_holo_bundle(
        "modules/demo", "semantic architecture retrieval"
    )

    assert "--bundle-json" in captured["cmd"]
    assert "HOLO_SKIP_MODEL" not in captured["env"]
    assert captured["env"]["HOLO_OFFLINE"] == "1"
    assert bundle.requested_retrieval_mode == "semantic"
    assert bundle.retrieval_mode == "semantic"
    assert bundle.embedding_backend == "sentence_transformers"
    assert bundle.semantic_requirement_met is True
    assert bundle.to_dict()["semantic_requirement_met"] is True


def test_preflight_fails_closed_when_semantic_request_degrades(monkeypatch, tmp_path):
    module_dir = tmp_path / "modules" / "demo"
    module_dir.mkdir(parents=True)
    (module_dir / "README.md").write_text("# Demo\n", encoding="utf-8")
    (module_dir / "INTERFACE.md").write_text("# Interface\n", encoding="utf-8")

    degraded = mp.MemoryBundle(
        module_path="modules/demo",
        artifacts=[
            mp.ArtifactInfo(str(module_dir / "README.md"), "modules/demo/README.md", 0, True, True),
            mp.ArtifactInfo(str(module_dir / "INTERFACE.md"), "modules/demo/INTERFACE.md", 0, True, True),
        ],
        missing_required=[],
        missing_optional=[],
        duplication_rate_proxy=0.0,
        ordering_confidence=None,
        staleness_risk=None,
        tier0_complete=True,
        preflight_passed=True,
        requested_retrieval_mode="semantic",
        retrieval_mode="lexical",
        embedding_backend="none",
        semantic_requirement_met=False,
    )
    guard = mp.MemoryPreflightGuard(tmp_path)
    monkeypatch.setattr(guard, "_retrieve_via_holo_bundle", lambda **_kwargs: degraded)

    with pytest.raises(mp.MemoryPreflightError, match="semantic retrieval was required") as exc_info:
        guard.run_preflight("modules/demo", "semantic audit")
    assert "Restore the cached embedding model" in exc_info.value.required_action

    guard.allow_degraded = True
    receipt = guard.run_preflight("modules/demo", "semantic audit")
    assert receipt.preflight_passed is True
    assert receipt.semantic_requirement_met is False
    assert receipt.retrieval_mode == "lexical"
