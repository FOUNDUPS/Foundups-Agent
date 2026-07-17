# -*- coding: utf-8 -*-
"""Tests for SECRETS_MCP_WSP71_OP_CLI_VAULT_RESOLVER_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.infrastructure.secrets_mcp.src.op_cli_secret_resolver import (
    OpCliCommandResult,
    OpCliSecretResolver,
)
from modules.infrastructure.secrets_mcp.src.vault_resolver import (
    AuditEvent,
    ResolveErrorCode,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "infrastructure"
    / "secrets_mcp"
    / "src"
    / "op_cli_secret_resolver.py"
)


class FakeRunner:
    def __init__(self, result: OpCliCommandResult | Exception) -> None:
        self.result = result
        self.calls: list[tuple[tuple[str, ...], float, int]] = []

    def __call__(
        self,
        argv: tuple[str, ...],
        *,
        timeout_s: float,
        max_stdout_chars: int,
    ) -> OpCliCommandResult:
        self.calls.append((argv, timeout_s, max_stdout_chars))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_op_cli_resolver_reads_canonical_reference_and_returns_secret_in_memory_only() -> None:
    events: list[AuditEvent] = []
    runner = FakeRunner(OpCliCommandResult(returncode=0, stdout="ed25519-secret"))
    resolver = OpCliSecretResolver(
        runner=runner,
        ttl_seconds=60,
        session_id="session-1",
        audit_callback=events.append,
    )

    result = resolver.resolve("op://prod-vault/reddog-signing/private", "signer:reddog")

    assert result.success is True
    assert result.get_value() == "ed25519-secret"
    assert result.reference == "op://prod-vault/reddog-signing/private"
    assert result.ttl_remaining == 60
    assert result.session_id == "session-1"
    assert runner.calls == [
        (
            ("op", "read", "op://prod-vault/reddog-signing/private", "--no-newline"),
            10.0,
            65536,
        )
    ]
    audit = result.to_audit_dict()
    assert "ed25519-secret" not in str(audit)
    assert "ed25519-secret" not in str(events[0].to_dict())
    assert events[0].requester_id == "signer:reddog"


def test_op_cli_resolver_fails_closed_without_leaking_stderr_or_stdout() -> None:
    runner = FakeRunner(
        OpCliCommandResult(
            returncode=1,
            stdout="SECRET_STDOUT_SHOULD_NOT_LEAK",
            stderr="SECRET_STDERR_SHOULD_NOT_LEAK",
        )
    )
    resolver = OpCliSecretResolver(runner=runner)

    result = resolver.resolve("op://prod-vault/reddog-signing/private")

    assert result.success is False
    assert result.error_code == ResolveErrorCode.COMMAND_FAILED
    assert result.get_value() is None
    text = str(result.to_audit_dict())
    assert "SECRET_STDOUT_SHOULD_NOT_LEAK" not in text
    assert "SECRET_STDERR_SHOULD_NOT_LEAK" not in text


def test_op_cli_resolver_rejects_invalid_reference_and_unsafe_executable_before_runner() -> None:
    runner = FakeRunner(OpCliCommandResult(returncode=0, stdout="secret"))

    invalid = OpCliSecretResolver(runner=runner).resolve("https://not-op")
    unsafe = OpCliSecretResolver(op_executable="op --account bad", runner=runner).resolve(
        "op://prod-vault/reddog-signing/private"
    )
    absolute_op = OpCliSecretResolver(op_executable="C:/Program Files/1Password/op.exe", runner=runner).resolve(
        "op://prod-vault/reddog-signing/private"
    )

    assert invalid.success is False
    assert invalid.error_code == ResolveErrorCode.INVALID_REFERENCE
    assert unsafe.success is False
    assert unsafe.error_code == ResolveErrorCode.RESOLVER_UNAVAILABLE
    assert absolute_op.success is True
    assert runner.calls == [
        (
            (
                "C:/Program Files/1Password/op.exe",
                "read",
                "op://prod-vault/reddog-signing/private",
                "--no-newline",
            ),
            10.0,
            65536,
        )
    ]


def test_op_cli_resolver_rejects_timeout_empty_large_and_runner_exception() -> None:
    timeout = OpCliSecretResolver(
        runner=FakeRunner(OpCliCommandResult(returncode=124, stdout="", timed_out=True))
    ).resolve("op://prod-vault/reddog-signing/private")
    empty = OpCliSecretResolver(
        runner=FakeRunner(OpCliCommandResult(returncode=0, stdout=""))
    ).resolve("op://prod-vault/reddog-signing/private")
    large = OpCliSecretResolver(
        runner=FakeRunner(OpCliCommandResult(returncode=0, stdout="x" * 6)),
        max_secret_chars=5,
    ).resolve("op://prod-vault/reddog-signing/private")
    raised = OpCliSecretResolver(runner=FakeRunner(RuntimeError("boom"))).resolve(
        "op://prod-vault/reddog-signing/private"
    )

    assert timeout.error_code == ResolveErrorCode.RESOLVER_UNAVAILABLE
    assert empty.error_code == ResolveErrorCode.UNKNOWN_REFERENCE
    assert large.error_code == ResolveErrorCode.OUTPUT_TOO_LARGE
    assert raised.error_code == ResolveErrorCode.RESOLVER_UNAVAILABLE
    assert all(result.success is False for result in (timeout, empty, large, raised))


def test_op_cli_resolver_ast_uses_no_shell_network_or_secret_persistence() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_imports = {"requests", "urllib", "httpx", "aiohttp", "socket"}
    banned_calls = {"eval", "exec", "compile", "__import__", "open"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = {alias.name.split(".", 1)[0] for alias in node.names}
            assert not roots & banned_imports
        if isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            assert root not in banned_imports
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute) and node.func.attr == "run":
                shell_keywords = [
                    keyword
                    for keyword in node.keywords
                    if keyword.arg == "shell"
                ]
                assert shell_keywords
                assert isinstance(shell_keywords[0].value, ast.Constant)
                assert shell_keywords[0].value.value is False
                assert node.args
                assert isinstance(node.args[0], ast.Call)
                assert isinstance(node.args[0].func, ast.Name)
                assert node.args[0].func.id == "list"
