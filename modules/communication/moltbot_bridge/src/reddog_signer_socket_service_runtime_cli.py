"""Retired signer runtime CLI retained as a fail-closed compatibility surface.

Production signer startup is owned exclusively by
``reddog_signer_system_service_entrypoint``. This legacy command accepts its
former arguments so old service definitions fail with a structured receipt;
it never loads authority, resolves secrets, or binds a socket.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Callable, Optional, Sequence


SIGNER_SOCKET_SERVICE_RUNTIME_CLI_ACCEPT = "SIGNER_SOCKET_SERVICE_RUNTIME_CLI_ACCEPT"
SIGNER_SOCKET_SERVICE_RUNTIME_CLI_REJECT = "SIGNER_SOCKET_SERVICE_RUNTIME_CLI_REJECT"
FAIL_SIGNER_RUNTIME_CLI_RETIRED = "FAIL_SIGNER_RUNTIME_CLI_RETIRED_USE_SYSTEM_SERVICE"


def build_reddog_signer_socket_service_runtime_cli_parser() -> argparse.ArgumentParser:
    """Parse the legacy command without performing any signer action."""

    parser = argparse.ArgumentParser(
        prog="reddog-signer-socket-service",
        description=(
            "Retired. Use reddog-signer-system-service with a root-owned "
            "owner-authority configuration."
        ),
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--expected-config-digest")
    parser.add_argument("--run-packet")
    parser.add_argument("--owner-authority-config")
    parser.add_argument("--op-executable", default="op")
    parser.add_argument("--op-timeout-s", type=float, default=10.0)
    parser.add_argument("--ttl-seconds", type=int, default=300)
    parser.add_argument("--session-id", default="op-cli-session")
    return parser


def run_reddog_signer_socket_service_runtime_cli(
    argv: Optional[Sequence[str]] = None,
    *,
    emit: Callable[[str], None] = print,
) -> int:
    """Reject the retired entrypoint before authority or secret access."""

    build_reddog_signer_socket_service_runtime_cli_parser().parse_args(
        list(argv) if argv is not None else None
    )
    emit(_receipt_json())
    return 2


def _receipt_json() -> str:
    payload = {
        "status": SIGNER_SOCKET_SERVICE_RUNTIME_CLI_REJECT,
        "result": None,
        "rejection_reasons": [FAIL_SIGNER_RUNTIME_CLI_RETIRED],
        "replacement_entrypoint": "reddog-signer-system-service",
        "no_authority_loaded": True,
        "no_secret_resolver_constructed": True,
        "no_socket_bound": True,
        "no_main_runtime_wiring": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_pr_created": True,
        "no_reward_settlement_performed": True,
        "no_holoindex_reindex_performed": True,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def main(argv: Optional[Sequence[str]] = None) -> int:
    return run_reddog_signer_socket_service_runtime_cli(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))


__all__ = [
    "FAIL_SIGNER_RUNTIME_CLI_RETIRED",
    "SIGNER_SOCKET_SERVICE_RUNTIME_CLI_ACCEPT",
    "SIGNER_SOCKET_SERVICE_RUNTIME_CLI_REJECT",
    "build_reddog_signer_socket_service_runtime_cli_parser",
    "main",
    "run_reddog_signer_socket_service_runtime_cli",
]
