# -*- coding: utf-8 -*-
"""WSP 71 op:// resolver backed by the 1Password CLI.

Slice: SECRETS_MCP_WSP71_OP_CLI_VAULT_RESOLVER_PHASE1

This module implements the WSP 71 Annex A ``op://`` runtime-resolution
boundary for production-capable callers. It invokes ``op read <reference>``
through an injected command runner, never through a shell, and never serializes
secret stdout/stderr into receipts, logs, prompts, or repository files.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional, Protocol

from modules.infrastructure.secrets_mcp.src.vault_resolver import (
    DEFAULT_TTL_SECONDS,
    AuditEvent,
    ResolveErrorCode,
    ResolveResult,
    hash_reference,
    parse_op_reference,
)


OP_CLI_SECRET_RESOLVER_MODE = "WSP71_OP_CLI"
DEFAULT_OP_EXECUTABLE = "op"
DEFAULT_OP_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_SECRET_CHARS = 65536


@dataclass(frozen=True)
class OpCliCommandResult:
    """Sanitized command result from the injected op CLI runner."""

    returncode: int
    stdout: str
    stderr: str = ""
    timed_out: bool = False


class OpCliCommandRunner(Protocol):
    """Command runner boundary for deterministic tests and production op CLI."""

    def __call__(
        self,
        argv: tuple[str, ...],
        *,
        timeout_s: float,
        max_stdout_chars: int,
    ) -> OpCliCommandResult:
        """Run ``argv`` and return captured output."""


class SubprocessOpCliCommandRunner:
    """Minimal shell-free runner for ``op read``."""

    def __call__(
        self,
        argv: tuple[str, ...],
        *,
        timeout_s: float,
        max_stdout_chars: int,
    ) -> OpCliCommandResult:
        try:
            completed = subprocess.run(
                list(argv),
                capture_output=True,
                text=True,
                timeout=timeout_s,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return OpCliCommandResult(returncode=124, stdout="", timed_out=True)
        stdout = completed.stdout
        if len(stdout) > max_stdout_chars:
            stdout = stdout[: max_stdout_chars + 1]
        return OpCliCommandResult(
            returncode=int(completed.returncode),
            stdout=stdout,
            stderr="",
        )


class OpCliSecretResolver:
    """Resolve ``op://`` references with the 1Password CLI."""

    def __init__(
        self,
        *,
        op_executable: str = DEFAULT_OP_EXECUTABLE,
        timeout_s: float = DEFAULT_OP_TIMEOUT_SECONDS,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        max_secret_chars: int = DEFAULT_MAX_SECRET_CHARS,
        session_id: str = "op-cli-session",
        runner: Optional[OpCliCommandRunner] = None,
        audit_callback: Optional[Callable[[AuditEvent], None]] = None,
    ) -> None:
        self._op_executable = op_executable
        self._timeout_s = timeout_s
        self._ttl_seconds = ttl_seconds
        self._max_secret_chars = max_secret_chars
        self._session_id = session_id
        self._runner = runner or SubprocessOpCliCommandRunner()
        self._audit_callback = audit_callback

    def resolve(self, reference: str, requester_id: Optional[str] = None) -> ResolveResult:
        """Resolve an op reference and return the secret value only in memory."""

        parsed = parse_op_reference(reference)
        if parsed is None:
            return self._fail(reference, ResolveErrorCode.INVALID_REFERENCE, requester_id)
        canonical = parsed.canonical()
        if not _op_executable_allowed(self._op_executable):
            return self._fail(canonical, ResolveErrorCode.RESOLVER_UNAVAILABLE, requester_id)
        if self._ttl_seconds <= 0:
            return self._fail(canonical, ResolveErrorCode.TTL_EXPIRED, requester_id)
        if self._timeout_s <= 0 or self._max_secret_chars <= 0:
            return self._fail(canonical, ResolveErrorCode.RESOLVER_UNAVAILABLE, requester_id)

        argv = (self._op_executable, "read", canonical, "--no-newline")
        try:
            result = self._runner(
                argv,
                timeout_s=self._timeout_s,
                max_stdout_chars=self._max_secret_chars,
            )
        except Exception:
            return self._fail(canonical, ResolveErrorCode.RESOLVER_UNAVAILABLE, requester_id)
        if result.timed_out:
            return self._fail(canonical, ResolveErrorCode.RESOLVER_UNAVAILABLE, requester_id)
        if result.returncode != 0:
            return self._fail(canonical, ResolveErrorCode.COMMAND_FAILED, requester_id)
        if len(result.stdout) > self._max_secret_chars:
            return self._fail(canonical, ResolveErrorCode.OUTPUT_TOO_LARGE, requester_id)
        if result.stdout == "":
            return self._fail(canonical, ResolveErrorCode.UNKNOWN_REFERENCE, requester_id)

        event = self._emit(canonical, True, None, requester_id)
        return ResolveResult(
            success=True,
            reference=canonical,
            reference_hash=event.reference_hash,
            ttl_remaining=int(self._ttl_seconds),
            session_id=self._session_id,
            _secret_value=result.stdout,
        )

    def _fail(
        self,
        reference: str,
        code: ResolveErrorCode,
        requester_id: Optional[str],
    ) -> ResolveResult:
        event = self._emit(reference, False, code, requester_id)
        return ResolveResult(
            success=False,
            reference=reference,
            reference_hash=event.reference_hash,
            error_code=code,
            error_message=code.value,
            ttl_remaining=0,
            session_id=self._session_id,
            _secret_value=None,
        )

    def _emit(
        self,
        reference: str,
        success: bool,
        code: Optional[ResolveErrorCode],
        requester_id: Optional[str],
    ) -> AuditEvent:
        event = AuditEvent(
            event_type="secret_access",
            reference=reference,
            reference_hash=hash_reference(reference),
            session_id=self._session_id,
            success=success,
            error_code=code.value if code else None,
            timestamp=_utc_timestamp(),
            ttl_applied=int(self._ttl_seconds) if success else None,
            requester_id=requester_id,
        )
        if self._audit_callback:
            self._audit_callback(event)
        return event


def _op_executable_allowed(value: str) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    stripped = value.strip()
    if stripped != value:
        return False
    basename = stripped.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return basename in {"op", "op.exe"}


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "DEFAULT_MAX_SECRET_CHARS",
    "DEFAULT_OP_EXECUTABLE",
    "DEFAULT_OP_TIMEOUT_SECONDS",
    "OP_CLI_SECRET_RESOLVER_MODE",
    "OpCliCommandResult",
    "OpCliCommandRunner",
    "OpCliSecretResolver",
    "SubprocessOpCliCommandRunner",
]
