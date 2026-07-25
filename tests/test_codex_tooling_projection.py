"""Contract tests for deterministic Codex tooling projections."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_codex_tooling_projection as projection  # noqa: E402


def test_checked_in_projection_is_current() -> None:
    assert projection.projection_differences() == ()


def test_agents_projection_changes_only_header_and_adds_notice() -> None:
    source_lines = projection.CLAUDE_INSTRUCTIONS.read_text(
        encoding="utf-8"
    ).replace("\r\n", "\n").splitlines()
    target_lines = projection.AGENTS_INSTRUCTIONS.read_text(
        encoding="utf-8"
    ).splitlines()

    assert target_lines[0] == source_lines[0].replace(
        "# CLAUDE.md",
        "# AGENTS.md",
        1,
    )
    assert target_lines[1] == projection.GENERATED_NOTICE
    assert target_lines[2:] == source_lines[1:]


def test_skill_projection_is_exact_and_excludes_metadata() -> None:
    expected = projection.canonical_skill_files()
    actual = {
        path.relative_to(projection.CODEX_SKILLS)
        for path in projection.CODEX_SKILLS.rglob("*")
        if path.is_file()
    }

    assert actual == set(expected)
    assert not (projection.CODEX_SKILLS / "_meta").exists()
    for relative, payload in expected.items():
        assert (projection.CODEX_SKILLS / relative).read_bytes() == payload


def test_codex_mcp_projection_matches_canonical_json_and_pins_versions() -> None:
    canonical = json.loads(projection.MCP_CONFIG.read_text(encoding="utf-8"))
    generated = tomllib.loads(projection.CODEX_CONFIG.read_text(encoding="utf-8"))

    assert generated["mcp_servers"] == canonical["mcpServers"]
    chrome_args = canonical["mcpServers"]["chrome-devtools"]["args"]
    assert all("@latest" not in value for value in chrome_args)
    assert "chrome-devtools-mcp@1.6.0" in chrome_args


def test_generator_rejects_unknown_mcp_fields() -> None:
    payload = {
        "mcpServers": {
            "unsafe": {
                "command": "python",
                "args": [],
                "unknown": "must-fail",
            }
        }
    }

    try:
        projection.render_codex_config(payload)
    except ValueError as error:
        assert str(error) == "mcp_server_unsupported_fields:unsafe"
    else:
        raise AssertionError("unsupported MCP fields must fail closed")


def test_generator_rejects_sensitive_mcp_environment_values() -> None:
    payload = {
        "mcpServers": {
            "unsafe": {
                "command": "python",
                "args": [],
                "env": {"API_TOKEN": "must-not-project"},
            }
        }
    }

    try:
        projection.render_codex_config(payload)
    except ValueError as error:
        assert str(error) == "mcp_server_sensitive_value_forbidden:unsafe"
    else:
        raise AssertionError("sensitive MCP environment values must fail closed")


def test_generator_does_not_delete_unexpected_local_skill_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    skills = tmp_path / ".agents" / "skills"
    unexpected = skills / "local-only" / "SKILL.md"
    unexpected.parent.mkdir(parents=True)
    unexpected.write_text("local data", encoding="utf-8")
    canonical_claude = tmp_path / "CLAUDE.md"
    canonical_claude.write_text("# CLAUDE.md\n", encoding="utf-8")
    canonical_mcp = tmp_path / ".mcp.json"
    canonical_mcp.write_text(
        '{"mcpServers":{"safe":{"command":"python","args":[]}}}',
        encoding="utf-8",
    )
    canonical_skills = tmp_path / ".claude" / "skills"
    sample_skill = canonical_skills / "sample" / "SKILL.md"
    sample_skill.parent.mkdir(parents=True)
    sample_skill.write_text("canonical", encoding="utf-8")
    monkeypatch.setattr(projection, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(projection, "CLAUDE_INSTRUCTIONS", canonical_claude)
    monkeypatch.setattr(projection, "MCP_CONFIG", canonical_mcp)
    monkeypatch.setattr(projection, "CLAUDE_SKILLS", canonical_skills)
    monkeypatch.setattr(projection, "CODEX_SKILLS", skills)
    monkeypatch.setattr(projection, "AGENTS_INSTRUCTIONS", tmp_path / "AGENTS.md")
    monkeypatch.setattr(
        projection,
        "CODEX_CONFIG",
        tmp_path / ".codex" / "config.toml",
    )

    with pytest.raises(ValueError, match="unexpected_codex_skill_projection_entries"):
        projection.write_projection()

    assert unexpected.read_text(encoding="utf-8") == "local data"


@pytest.mark.parametrize(
    "field_value",
    (
        {"args": ["--credential=opaque"]},
        {"cwd": "token/private"},
        {"env": {"SAFE_NAME": "sk-abcdefghijklmnop"}},
    ),
)
def test_generator_rejects_sensitive_mcp_values(field_value) -> None:
    server = {"command": "python", "args": []}
    server.update(field_value)

    with pytest.raises(ValueError, match="sensitive_value_forbidden"):
        projection.render_codex_config({"mcpServers": {"unsafe": server}})


def test_output_path_rejects_linked_ancestors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    linked = repo / ".codex"
    try:
        linked.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    monkeypatch.setattr(projection, "REPO_ROOT", repo)

    with pytest.raises(ValueError, match="link_rejected"):
        projection._validated_output_path(linked / "config.toml")


@pytest.mark.parametrize(
    ("target_parts", "linked_parts"),
    (
        (("AGENTS.md",), ("AGENTS.md",)),
        ((".codex", "config.toml"), (".codex",)),
        ((".agents", "skills", "demo", "SKILL.md"), (".agents",)),
        ((".agents", "skills", "demo", "SKILL.md"), (".agents", "skills", "demo")),
        (
            (".agents", "skills", "demo", "SKILL.md"),
            (".agents", "skills", "demo", "SKILL.md"),
        ),
    ),
)
def test_output_path_checks_every_expected_ancestor(
    tmp_path: Path,
    monkeypatch,
    target_parts,
    linked_parts,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    linked = repo.joinpath(*linked_parts)
    monkeypatch.setattr(projection, "REPO_ROOT", repo)
    monkeypatch.setattr(
        projection,
        "_is_link_or_junction",
        lambda path: path == linked,
    )

    with pytest.raises(ValueError, match="link_rejected"):
        projection._validated_output_path(repo.joinpath(*target_parts))


def test_atomic_batch_rolls_back_when_replacement_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    first = repo / "first.txt"
    second = repo / "second.txt"
    first.write_text("old-first", encoding="utf-8")
    second.write_text("old-second", encoding="utf-8")
    monkeypatch.setattr(projection, "REPO_ROOT", repo)
    real_replace = projection.os.replace
    calls = 0

    def fail_second_replace(source, target):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected replacement failure")
        return real_replace(source, target)

    monkeypatch.setattr(projection.os, "replace", fail_second_replace)

    with pytest.raises(OSError, match="injected replacement failure"):
        projection._atomic_write_many(
            {
                first: b"new-first",
                second: b"new-second",
            }
        )

    assert first.read_text(encoding="utf-8") == "old-first"
    assert second.read_text(encoding="utf-8") == "old-second"
