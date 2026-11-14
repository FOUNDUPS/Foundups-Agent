#!/usr/bin/env python3
"""Generate deterministic Codex tooling projections from canonical repo inputs."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
CLAUDE_INSTRUCTIONS = REPO_ROOT / "CLAUDE.md"
AGENTS_INSTRUCTIONS = REPO_ROOT / "AGENTS.md"
CLAUDE_SKILLS = REPO_ROOT / ".claude" / "skills"
CODEX_SKILLS = REPO_ROOT / ".agents" / "skills"
MCP_CONFIG = REPO_ROOT / ".mcp.json"
CODEX_CONFIG = REPO_ROOT / ".codex" / "config.toml"
GENERATED_NOTICE = (
    "<!-- Generated from CLAUDE.md by "
    "scripts/generate_codex_tooling_projection.py; edit CLAUDE.md. -->"
)
SENSITIVE_MCP_TEXT = re.compile(
    r"(?i)(?:^|[^a-z0-9])(?:api[_-]?key|access[_-]?token|refresh[_-]?token|"
    r"token|password|passwd|secret|credential(?:s)?|authorization|cookie|"
    r"private[_-]?key)(?:[^a-z0-9]|$)"
)
KNOWN_SECRET_VALUE = re.compile(
    r"(?i)(?:sk-[a-z0-9_-]{12,}|gh[opusr]_[a-z0-9_]{12,}|"
    r"AKIA[0-9A-Z]{16}|xox[baprs]-[a-z0-9-]{12,})"
)


def render_agents_md(source: str) -> str:
    """Project canonical instructions without global product-name rewriting."""

    lines = source.replace("\r\n", "\n").splitlines()
    if not lines or not lines[0].startswith("# CLAUDE.md"):
        raise ValueError("canonical_claude_header_missing")
    lines[0] = lines[0].replace("# CLAUDE.md", "# AGENTS.md", 1)
    lines.insert(1, GENERATED_NOTICE)
    return "\n".join(lines).rstrip() + "\n"


def render_codex_config(payload: Mapping[str, Any]) -> str:
    """Render the supported MCP schema as deterministic TOML."""

    servers = payload.get("mcpServers")
    if not isinstance(servers, Mapping) or not servers:
        raise ValueError("mcp_servers_missing")
    output = [
        "# Generated from .mcp.json by scripts/generate_codex_tooling_projection.py.",
        "# Edit .mcp.json, then regenerate.",
        "",
    ]
    for name in sorted(servers):
        config = servers[name]
        if not isinstance(name, str) or not name or not isinstance(config, Mapping):
            raise ValueError("mcp_server_invalid")
        unsupported = set(config) - {"command", "args", "cwd", "env"}
        if unsupported:
            raise ValueError(f"mcp_server_unsupported_fields:{name}")
        command = config.get("command")
        args = config.get("args", [])
        cwd = config.get("cwd")
        env = config.get("env", {})
        if (
            not isinstance(command, str)
            or not command
            or not isinstance(args, list)
            or not all(isinstance(value, str) for value in args)
            or (cwd is not None and not isinstance(cwd, str))
            or not isinstance(env, Mapping)
            or not all(
                isinstance(key, str) and isinstance(value, str)
                for key, value in env.items()
            )
        ):
            raise ValueError(f"mcp_server_value_invalid:{name}")
        projected_values = [
            command,
            *args,
            *(tuple([cwd]) if cwd is not None else ()),
            *(f"{key}={value}" for key, value in env.items()),
        ]
        if any(
            SENSITIVE_MCP_TEXT.search(value) or KNOWN_SECRET_VALUE.search(value)
            for value in projected_values
        ):
            raise ValueError(f"mcp_server_sensitive_value_forbidden:{name}")

        quoted_name = json.dumps(name, ensure_ascii=True)
        output.append(f"[mcp_servers.{quoted_name}]")
        output.append(f"command = {json.dumps(command, ensure_ascii=True)}")
        output.append(
            "args = ["
            + ", ".join(json.dumps(value, ensure_ascii=True) for value in args)
            + "]"
        )
        if cwd is not None:
            output.append(f"cwd = {json.dumps(cwd, ensure_ascii=True)}")
        if env:
            output.append("")
            output.append(f"[mcp_servers.{quoted_name}.env]")
            for key in sorted(env):
                output.append(
                    f"{json.dumps(key, ensure_ascii=True)} = "
                    f"{json.dumps(env[key], ensure_ascii=True)}"
                )
        output.append("")
    return "\n".join(output).rstrip() + "\n"


def canonical_skill_files() -> dict[Path, bytes]:
    """Return the complete Skill projection, excluding Claude-only metadata."""

    result: dict[Path, bytes] = {}
    for source in sorted(CLAUDE_SKILLS.glob("*/SKILL.md")):
        _validated_output_path(source)
        result[Path(source.parent.name) / "SKILL.md"] = source.read_bytes()
    if not result:
        raise ValueError("canonical_skills_missing")
    return result


def projection_differences() -> tuple[str, ...]:
    """Return stable reasons when checked-in projections differ from sources."""

    for path in (
        CLAUDE_INSTRUCTIONS,
        AGENTS_INSTRUCTIONS,
        MCP_CONFIG,
        CODEX_CONFIG,
        CODEX_SKILLS,
    ):
        _validated_output_path(path)
    differences: list[str] = []
    expected_agents = render_agents_md(CLAUDE_INSTRUCTIONS.read_text(encoding="utf-8"))
    if not AGENTS_INSTRUCTIONS.exists():
        differences.append("missing:AGENTS.md")
    elif AGENTS_INSTRUCTIONS.read_text(encoding="utf-8") != expected_agents:
        differences.append("stale:AGENTS.md")

    mcp_payload = json.loads(MCP_CONFIG.read_text(encoding="utf-8"))
    expected_config = render_codex_config(mcp_payload)
    if not CODEX_CONFIG.exists():
        differences.append("missing:.codex/config.toml")
    elif CODEX_CONFIG.read_text(encoding="utf-8") != expected_config:
        differences.append("stale:.codex/config.toml")

    expected_skills = canonical_skill_files()
    actual_skills = (
        {
            path.relative_to(CODEX_SKILLS)
            for path in CODEX_SKILLS.rglob("*")
            if path.is_file()
        }
        if CODEX_SKILLS.exists()
        else set()
    )
    if actual_skills != set(expected_skills):
        differences.append("stale:.agents/skills/file_set")
    for relative, expected in expected_skills.items():
        target = CODEX_SKILLS / relative
        if not target.exists() or target.read_bytes() != expected:
            differences.append(f"stale:.agents/skills/{relative.as_posix()}")
    return tuple(differences)


def _is_link_or_junction(path: Path) -> bool:
    if not os.path.lexists(path):
        return False
    metadata = os.lstat(path)
    reparse = bool(
        getattr(metadata, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )
    return (
        stat.S_ISLNK(metadata.st_mode)
        or reparse
        or bool(getattr(path, "is_junction", lambda: False)())
    )


def _validated_output_path(path: Path) -> Path:
    """Require a direct, non-linked path beneath the repository root."""

    root = Path(os.path.abspath(REPO_ROOT))
    candidate = Path(os.path.abspath(path))
    try:
        relative = candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("projection_output_outside_repository") from error
    if not relative.parts:
        raise ValueError("projection_output_is_repository_root")
    current = root
    for component in relative.parts:
        current = current / component
        if _is_link_or_junction(current):
            raise ValueError("projection_output_link_rejected")
    return candidate


def _write_staged_file(target: Path, payload: bytes) -> Path:
    descriptor, raw_temp = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    temp_path = Path(raw_temp)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        _validated_output_path(temp_path)
        return temp_path
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temp_path.unlink(missing_ok=True)
        raise


def _atomic_write_many(outputs: Mapping[Path, bytes]) -> None:
    """Stage every output before atomically replacing any target."""

    validated: dict[Path, bytes] = {}
    originals: dict[Path, bytes | None] = {}
    for raw_target, payload in outputs.items():
        target = _validated_output_path(raw_target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target = _validated_output_path(target)
        if not isinstance(payload, bytes):
            raise TypeError("projection_payload_not_bytes")
        validated[target] = payload
        originals[target] = target.read_bytes() if target.exists() else None

    staged: dict[Path, Path] = {}
    replaced: list[Path] = []
    try:
        for target, payload in validated.items():
            staged[target] = _write_staged_file(target, payload)
        for target in validated:
            _validated_output_path(target)
            _validated_output_path(staged[target])
        for target, temp_path in staged.items():
            os.replace(temp_path, target)
            replaced.append(target)
    except Exception:
        for target in reversed(replaced):
            original = originals[target]
            _validated_output_path(target)
            if original is None:
                target.unlink(missing_ok=True)
            else:
                restore = _write_staged_file(target, original)
                os.replace(restore, target)
        raise
    finally:
        for temp_path in staged.values():
            temp_path.unlink(missing_ok=True)


def write_projection() -> None:
    """Replace generated outputs from canonical sources."""

    _validated_output_path(CLAUDE_INSTRUCTIONS)
    _validated_output_path(MCP_CONFIG)
    expected_skills = canonical_skill_files()
    _validated_output_path(AGENTS_INSTRUCTIONS)
    _validated_output_path(CODEX_CONFIG)
    _validated_output_path(CODEX_SKILLS)
    if CODEX_SKILLS.exists():
        actual_files = {
            path.relative_to(CODEX_SKILLS)
            for path in CODEX_SKILLS.rglob("*")
            if path.is_file()
        }
        actual_dirs = {
            path.relative_to(CODEX_SKILLS)
            for path in CODEX_SKILLS.rglob("*")
            if path.is_dir()
        }
        expected_dirs = {relative.parent for relative in expected_skills}
        if actual_files - set(expected_skills) or actual_dirs - expected_dirs:
            raise ValueError("unexpected_codex_skill_projection_entries")

    outputs = {
        AGENTS_INSTRUCTIONS: render_agents_md(
            CLAUDE_INSTRUCTIONS.read_text(encoding="utf-8")
        ).encode("utf-8"),
        CODEX_CONFIG: render_codex_config(
            json.loads(MCP_CONFIG.read_text(encoding="utf-8"))
        ).encode("utf-8"),
    }
    for relative, payload in expected_skills.items():
        target = CODEX_SKILLS / relative
        _validated_output_path(target)
        outputs[target] = payload
    _atomic_write_many(outputs)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when generated projections are absent or stale.",
    )
    args = parser.parse_args(argv)
    if args.check:
        differences = projection_differences()
        if differences:
            for difference in differences:
                print(difference)
            return 1
        print("Codex tooling projection is current.")
        return 0
    write_projection()
    differences = projection_differences()
    if differences:
        raise RuntimeError("projection_write_incomplete:" + ",".join(differences))
    print("Codex tooling projection updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
