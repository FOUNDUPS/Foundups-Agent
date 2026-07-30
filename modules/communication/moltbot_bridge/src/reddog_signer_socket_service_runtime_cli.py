"""CLI adapter for the RedDog signer socket runtime service.

Slice: REDDOG_SIGNER_SOCKET_SERVICE_RUNTIME_CLI_PHASE1

This module is the signer-owned executable surface for starting the bounded
isolated signer socket service from an outside-repo JSON config. It does not
wire into ``main.py`` or RedDog model output. The RedDog resident queue still
only consumes an already-available signer socket.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Optional, Protocol, Sequence

from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import (
    serve_reddog_isolated_signer_socket_bounded,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_bootstrap import (
    SignerSocketServiceRuntimeBootstrapResult,
    run_reddog_signer_socket_service_runtime_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    ServeSignerSocketBounded,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWaterStore,
)
from modules.infrastructure.secrets_mcp.src.op_cli_secret_resolver import OpCliSecretResolver
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    FailClosedPrincipalKeyResolver,
    PrincipalKeyResolver,
)


SIGNER_SOCKET_SERVICE_RUNTIME_CLI_ACCEPT = "SIGNER_SOCKET_SERVICE_RUNTIME_CLI_ACCEPT"
SIGNER_SOCKET_SERVICE_RUNTIME_CLI_REJECT = "SIGNER_SOCKET_SERVICE_RUNTIME_CLI_REJECT"


class ResolverFactory(Protocol):
    """Factory for building the signer-owned WSP71 resolver."""

    def __call__(
        self,
        *,
        op_executable: str,
        timeout_s: float,
        ttl_seconds: int,
        session_id: str,
    ) -> object:
        """Return a resolver implementing ``resolve(reference, requester_id)``."""


class ManifestSelectionLoader(Protocol):
    """Load one opaque authenticated current-generation manifest selection."""

    def __call__(
        self,
        *,
        repo_root: Path,
        config_path: Path,
        run_packet_path: Path,
    ) -> tuple[object, Any]:
        """Return ``(selection, boundary)`` or raise fail-closed."""


def build_reddog_signer_socket_service_runtime_cli_parser() -> argparse.ArgumentParser:
    """Build the signer-service CLI parser."""

    parser = argparse.ArgumentParser(
        prog="reddog-signer-socket-service",
        description="Start the RedDog isolated signer socket service from a WSP71 config.",
    )
    parser.add_argument("--repo-root", required=True, help="Repository root used for path containment checks.")
    parser.add_argument("--config", required=True, help="Outside-repo signer service JSON config.")
    parser.add_argument(
        "--expected-config-digest",
        help="Launch-authorized sha256 digest for proposal-enabled config.",
    )
    parser.add_argument(
        "--run-packet",
        help="Exact outside-repo launch packet used for signer instance binding.",
    )
    parser.add_argument("--op-executable", default="op", help="1Password CLI executable path/name.")
    parser.add_argument("--op-timeout-s", type=float, default=10.0, help="op read timeout in seconds.")
    parser.add_argument("--ttl-seconds", type=int, default=300, help="Credential TTL for resolver receipts.")
    parser.add_argument("--session-id", default="op-cli-session", help="Audit session identifier.")
    return parser


def run_reddog_signer_socket_service_runtime_cli(
    argv: Optional[Sequence[str]] = None,
    *,
    resolver_factory: ResolverFactory = OpCliSecretResolver,
    serve_bounded: ServeSignerSocketBounded = serve_reddog_isolated_signer_socket_bounded,
    emit: Callable[[str], None] = print,
    principal_key_resolver: PrincipalKeyResolver | None = None,
    proposal_replay_high_water_store: ProposalReplayHighWaterStore | None = None,
    manifest_selection_loader: ManifestSelectionLoader | None = None,
) -> int:
    """Run the signer service CLI and emit an audit-safe JSON receipt."""

    parser = build_reddog_signer_socket_service_runtime_cli_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    selection, selection_boundary = _load_manifest_selection(
        manifest_selection_loader,
        repo_root=Path(args.repo_root),
        config_path=Path(args.config),
        run_packet_path=(Path(args.run_packet) if args.run_packet else None),
    )
    result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=Path(args.repo_root),
        config_path=Path(args.config),
        resolver_factory=lambda: resolver_factory(
            op_executable=args.op_executable,
            timeout_s=float(args.op_timeout_s),
            ttl_seconds=int(args.ttl_seconds),
            session_id=str(args.session_id),
        ),  # type: ignore[arg-type]
        serve_bounded=serve_bounded,
        expected_config_digest=args.expected_config_digest,
        run_packet_path=(Path(args.run_packet) if args.run_packet else None),
        expected_session_id=str(args.session_id),
        principal_key_resolver=(
            principal_key_resolver
            or FailClosedPrincipalKeyResolver()
        ),
        proposal_replay_high_water_store=(
            proposal_replay_high_water_store
        ),
        manifest_selection=selection,
        manifest_selection_boundary=selection_boundary,
    )
    emit(_receipt_json(result))
    return 0 if result.accepted else 2


def _load_manifest_selection(
    loader: ManifestSelectionLoader | None,
    *,
    repo_root: Path,
    config_path: Path,
    run_packet_path: Path | None,
) -> tuple[object | None, Any | None]:
    if loader is None or run_packet_path is None:
        return None, None
    try:
        return loader(
            repo_root=repo_root,
            config_path=config_path,
            run_packet_path=run_packet_path,
        )
    except Exception:
        return None, None


def _receipt_json(result: SignerSocketServiceRuntimeBootstrapResult) -> str:
    payload = {
        "status": (
            SIGNER_SOCKET_SERVICE_RUNTIME_CLI_ACCEPT
            if result.accepted
            else SIGNER_SOCKET_SERVICE_RUNTIME_CLI_REJECT
        ),
        "result": result.to_dict(),
        "no_main_runtime_wiring": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_pr_created": True,
        "no_reward_settlement_performed": True,
        "no_holoindex_reindex_performed": True,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Console entrypoint."""

    return run_reddog_signer_socket_service_runtime_cli(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))


__all__ = [
    "SIGNER_SOCKET_SERVICE_RUNTIME_CLI_ACCEPT",
    "SIGNER_SOCKET_SERVICE_RUNTIME_CLI_REJECT",
    "build_reddog_signer_socket_service_runtime_cli_parser",
    "main",
    "run_reddog_signer_socket_service_runtime_cli",
]
