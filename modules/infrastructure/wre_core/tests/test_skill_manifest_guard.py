#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for skill manifest hash/signature verification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.infrastructure.wre_core.src.skill_manifest_guard import (
    generate_skill_manifest,
    verify_skill_manifest,
)


def test_manifest_verification_passes_for_untampered_files(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    (skills_dir / "a").mkdir(parents=True)
    (skills_dir / "a" / "SKILL.md").write_text("# ok", encoding="utf-8")
    manifest = skills_dir / "SKILL_MANIFEST.json"
    generate_skill_manifest(skills_dir, manifest_path=manifest)

    result = verify_skill_manifest(skills_dir, manifest_path=manifest, required=True)
    assert result.passed is True
    assert result.checked_files == 1
    assert result.signature_verified is False


def test_manifest_verification_fails_on_hash_mismatch(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    (skills_dir / "a").mkdir(parents=True)
    skill_file = skills_dir / "a" / "SKILL.md"
    skill_file.write_text("# v1", encoding="utf-8")
    manifest = skills_dir / "SKILL_MANIFEST.json"
    generate_skill_manifest(skills_dir, manifest_path=manifest)
    skill_file.write_text("# v2", encoding="utf-8")

    result = verify_skill_manifest(skills_dir, manifest_path=manifest, required=True)
    assert result.passed is False
    assert "a/SKILL.md" in result.mismatched_files


def test_manifest_binds_adjacent_executor(tmp_path: Path):
    skills_dir = tmp_path / "skill"
    skills_dir.mkdir()
    (skills_dir / "SKILLz.md").write_text("# skill", encoding="utf-8")
    executor = skills_dir / "executor.py"
    executor.write_text("def execute(task): return {}\n", encoding="utf-8")
    manifest = skills_dir / "SKILL_MANIFEST.json"

    payload = generate_skill_manifest(skills_dir, manifest_path=manifest)

    assert {entry["path"] for entry in payload["files"]} == {
        "SKILLz.md",
        "executor.py",
    }
    executor.write_text("raise RuntimeError\n", encoding="utf-8")
    result = verify_skill_manifest(skills_dir, manifest_path=manifest, required=True)
    assert result.passed is False
    assert "executor.py" in result.mismatched_files


def test_manifest_rejects_malformed_or_duplicate_entries(tmp_path: Path):
    skills_dir = tmp_path / "skill"
    skills_dir.mkdir()
    (skills_dir / "SKILLz.md").write_text("# skill", encoding="utf-8")
    manifest = skills_dir / "SKILL_MANIFEST.json"
    manifest.write_text(
        json.dumps(
            {
                "files": [
                    {"path": "SKILLz.md", "sha256": "0" * 64},
                    {"path": "SKILLz.md", "sha256": "0" * 64},
                ]
            }
        ),
        encoding="utf-8",
    )

    result = verify_skill_manifest(skills_dir, required=True)

    assert result.passed is False
    assert result.message == "manifest contains invalid entry"


def test_manifest_rejects_root_directory_link(tmp_path: Path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "SKILLz.md").write_text("# skill", encoding="utf-8")
    generate_skill_manifest(real, manifest_path=real / "SKILL_MANIFEST.json")
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("directory links are unavailable on this host")

    result = verify_skill_manifest(linked, required=True)

    assert result.passed is False
    assert "root" in result.message
    with pytest.raises(ValueError, match="root"):
        generate_skill_manifest(linked)


def test_manifest_signature_verification_passes_with_hmac_key(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    (skills_dir / "a").mkdir(parents=True)
    (skills_dir / "a" / "SKILL.md").write_text("# signed", encoding="utf-8")
    manifest = skills_dir / "SKILL_MANIFEST.json"
    generate_skill_manifest(skills_dir, manifest_path=manifest, hmac_key="secret-key")

    result = verify_skill_manifest(
        skills_dir,
        manifest_path=manifest,
        required=True,
        verify_signature=True,
        hmac_key="secret-key",
    )
    assert result.passed is True
    assert result.signature_verified is True
