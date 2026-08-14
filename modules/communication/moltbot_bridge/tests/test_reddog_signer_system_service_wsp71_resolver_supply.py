"""Security tests for signer-owned production WSP 71 resolver supply."""

from __future__ import annotations

import ast
import os
import stat
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_signer_system_service_wsp71_resolver_supply as target,
)
from modules.infrastructure.secrets_mcp.src.op_cli_secret_resolver import (
    OpCliCommandResult,
)


MODULE_PATH = Path(target.__file__).resolve()
OWNER_ID = "sha256:" + "a" * 64


class _Runner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, argv, *, timeout_s, max_stdout_chars):
        self.calls.append(tuple(argv))
        return OpCliCommandResult(returncode=0, stdout="secret-in-memory")


def _trusted_executable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"#!/bin/sh\n")
    os.chmod(path, 0o755)


def test_factory_resolves_only_after_root_owned_executable_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "usr" / "bin" / "op"
    _trusted_executable(executable)
    runner = _Runner()
    monkeypatch.setattr(target, "SYSTEM_SERVICE_OP_EXECUTABLE", executable)
    monkeypatch.setattr(target.sys, "platform", "linux")
    monkeypatch.setattr(target, "_require_root_owned_executable", lambda path: None)

    factory = target.SystemServiceWsp71ResolverFactory(OWNER_ID, runner=runner)
    assert runner.calls == []

    result = factory().resolve("op://Foundups/reddog/private", "signer:reddog")

    assert result.success is True
    assert result.get_value() == "secret-in-memory"
    assert runner.calls == [
        (str(executable), "read", "op://Foundups/reddog/private", "--no-newline")
    ]
    assert "secret-in-memory" not in str(result.to_audit_dict())


def test_factory_rejects_invalid_owner_before_secret_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _Runner()
    executable_checks: list[Path] = []
    monkeypatch.setattr(
        target,
        "_require_root_owned_executable",
        lambda path: executable_checks.append(path),
    )

    with pytest.raises(ValueError, match="owner_config_id_invalid"):
        target.SystemServiceWsp71ResolverFactory("sha256-looking", runner=runner)()

    assert runner.calls == []
    assert executable_checks == []


def test_executable_gate_rejects_missing_symlink_and_writable_binary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(target.sys, "platform", "linux")
    missing = tmp_path / "missing" / "op"
    with pytest.raises(ValueError, match="executable_unavailable"):
        target._require_root_owned_executable(missing)

    executable = tmp_path / "op"
    _trusted_executable(executable)
    link = tmp_path / "op-link"
    try:
        link.symlink_to(executable)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(ValueError, match="executable_invalid"):
        target._require_root_owned_executable(link)

    os.chmod(executable, stat.S_IRWXU | stat.S_IWGRP | stat.S_IXGRP)
    with pytest.raises(ValueError, match="executable_untrusted"):
        target._require_root_owned_executable(executable)


@pytest.mark.skipif(not target.sys.platform.startswith("linux"), reason="Linux only")
def test_executable_gate_accepts_root_owned_linux_binary() -> None:
    target._require_root_owned_executable(Path("/usr/bin/env"))


def test_supply_module_has_no_secret_persistence_or_shell_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_calls = {"open", "eval", "exec", "compile", "write_text", "write_bytes"}
    banned_imports = {"subprocess", "socket", "requests", "httpx"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not {alias.name.split(".", 1)[0] for alias in node.names} & banned_imports
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".", 1)[0] not in banned_imports
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_calls
