"""Tests for wsp49_interface_gap_scanner skill (read-only discovery)."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_discover_finds_module_without_interface(tmp_path: Path) -> None:
    root = tmp_path
    (root / "modules" / "infrastructure" / "fake_gap").mkdir(parents=True)
    (root / "modules" / "infrastructure" / "fake_gap" / "README.md").write_text("# Fake", encoding="utf-8")
    (root / "modules" / "infrastructure" / "fake_gap" / "src").mkdir()
    (root / "modules" / "infrastructure" / "fake_gap" / "src" / "__init__.py").write_text(
        '__all__ = ["foo"]\ndef foo(): return 1\n',
        encoding="utf-8",
    )

    from modules.ai_intelligence.ai_overseer.skillz.wsp49_interface_gap_scanner.executor import (
        discover_interface_gaps,
        rank_gaps,
    )

    raw = discover_interface_gaps(root)
    assert len(raw) >= 1
    paths = {r["path"] for r in raw}
    assert "modules/infrastructure/fake_gap" in paths
    row = next(r for r in raw if r["path"] == "modules/infrastructure/fake_gap")
    assert "README.md" in row["context_files"]
    assert row["symbol_hints"].get("__all__") == ["foo"]

    ranked = rank_gaps(raw)
    assert all("prompt_pack" in r and r["rank"] >= 1 for r in ranked)
    fake = next(r for r in ranked if r["module_name"] == "fake_gap")
    assert "WSP 11 INTERFACE draft" in fake["prompt_pack"]


def test_skips_when_interface_present(tmp_path: Path) -> None:
    root = tmp_path
    m = root / "modules" / "communication" / "ok_mod"
    (m / "src").mkdir(parents=True)
    (m / "INTERFACE.md").write_text("# API\n", encoding="utf-8")

    from modules.ai_intelligence.ai_overseer.skillz.wsp49_interface_gap_scanner.executor import (
        discover_interface_gaps,
    )

    assert discover_interface_gaps(root) == []


def test_domain_rank_order_infrastructure_before_foundups(tmp_path: Path) -> None:
    root = tmp_path
    for domain, name in (
        ("foundups", "aaa_early_alpha"),
        ("infrastructure", "zzz_late"),
    ):
        d = root / "modules" / domain / name / "src"
        d.mkdir(parents=True)

    from modules.ai_intelligence.ai_overseer.skillz.wsp49_interface_gap_scanner.executor import (
        discover_interface_gaps,
        rank_gaps,
    )

    ranked = rank_gaps(discover_interface_gaps(root))
    assert ranked[0]["domain"] == "infrastructure"
    assert ranked[1]["domain"] == "foundups"


def test_context_files_rank_before_alphabet_within_domain(tmp_path: Path) -> None:
    """CO: within the same domain, more context_files beats earlier A–Z name."""
    root = tmp_path
    thin = root / "modules" / "infrastructure" / "aaa_thin" / "src"
    thin.mkdir(parents=True)
    (thin / "__init__.py").write_text('__all__ = ["a"]\n', encoding="utf-8")

    rich = root / "modules" / "infrastructure" / "zzz_rich"
    (rich / "src").mkdir(parents=True)
    (rich / "README.md").write_text("# Z\n", encoding="utf-8")
    (rich / "ModLog.md").write_text("# M\n", encoding="utf-8")
    (rich / "requirements.txt").write_text("x\n", encoding="utf-8")
    (rich / "src" / "__init__.py").write_text('__all__ = ["z"]\n', encoding="utf-8")

    from modules.ai_intelligence.ai_overseer.skillz.wsp49_interface_gap_scanner.executor import (
        discover_interface_gaps,
        rank_gaps,
    )

    ranked = rank_gaps(discover_interface_gaps(root))
    infra = [r for r in ranked if r["domain"] == "infrastructure"]
    assert len(infra) == 2
    assert infra[0]["module_name"] == "zzz_rich"
    assert infra[1]["module_name"] == "aaa_thin"
    assert len(infra[0]["context_files"]) > len(infra[1]["context_files"])
