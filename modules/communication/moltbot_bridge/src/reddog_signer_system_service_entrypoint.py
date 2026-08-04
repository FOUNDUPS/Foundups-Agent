"""Stable signer-owned system-service entrypoint.

The operating system service manager starts this module with only the fixed
repository root and root-owned owner-authority configuration path. Rotating
runtime paths are accepted only from one authenticated current-generation
capability. Secret resolution remains fail closed until the E0 boundary is
implemented. The entrypoint never executes serialized argv and does not spawn
the signer process or invoke a shell.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import (
    serve_reddog_isolated_signer_socket_bounded,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_bootstrap import (
    SignerSocketServiceRuntimeBootstrapResult,
    run_reddog_signer_socket_service_runtime_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    ServeSignerSocketBounded,
)
from modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader import (
    load_system_service_manifest_selection,
    load_system_service_verified_outcome_signing_authority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_process_isolation_gate import (
    SignerProcessIsolationReceipt,
    enforce_signer_process_isolation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    PeerCredentialPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    FailClosedPrincipalKeyResolver,
    PrincipalKeyResolver,
)
from modules.infrastructure.secrets_mcp.src.vault_resolver import (
    ResolveErrorCode,
    ResolveResult,
    hash_reference,
)

SYSTEM_SERVICE_ENTRYPOINT_ACCEPT = "SYSTEM_SERVICE_ENTRYPOINT_ACCEPT"
SYSTEM_SERVICE_ENTRYPOINT_REJECT = "SYSTEM_SERVICE_ENTRYPOINT_REJECT"
FAIL_SYSTEM_SERVICE_SELECTION = "system_service_selection_invalid"


class _UnavailableSystemServiceResolver:
    """Fail closed until E0 supplies an authenticated external resolver."""

    @staticmethod
    def resolve(
        reference: str,
        requester_id: Optional[str] = None,
    ) -> ResolveResult:
        return ResolveResult(
            success=False,
            reference=reference,
            reference_hash=hash_reference(reference),
            error_code=ResolveErrorCode.RESOLVER_UNAVAILABLE,
            error_message="system_service_secret_resolver_not_admitted",
            session_id=requester_id,
        )


def build_signer_system_service_parser() -> argparse.ArgumentParser:
    """Build the stable service-manager command parser."""

    parser = argparse.ArgumentParser(
        prog="reddog-signer-system-service",
        description="Start the current authenticated RedDog signer generation.",
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--owner-authority-config", required=True)
    return parser


def run_reddog_signer_system_service_entrypoint(
    argv: Optional[Sequence[str]] = None,
    *,
    emit: Callable[[str], None] = print,
) -> int:
    """Run the production entrypoint without injectable authority loaders."""

    args = build_signer_system_service_parser().parse_args(
        list(argv) if argv is not None else None
    )
    return _run_entrypoint_args(
        args,
        resolver_factory=_UnavailableSystemServiceResolver,
        serve_bounded=serve_reddog_isolated_signer_socket_bounded,
        emit=emit,
        principal_key_resolver=FailClosedPrincipalKeyResolver(),
        proposal_replay_high_water_store=None,
        verified_outcome_authority_loader=(
            load_system_service_verified_outcome_signing_authority
        ),
    )


def _run_entrypoint_args(
    args: argparse.Namespace,
    *,
    resolver_factory: Callable[..., object],
    serve_bounded: ServeSignerSocketBounded,
    emit: Callable[[str], None],
    principal_key_resolver: PrincipalKeyResolver,
    proposal_replay_high_water_store: ProposalReplayHighWaterStore | None,
    verified_outcome_authority_loader: Callable[..., object] | None = None,
    process_isolation_gate: Callable[
        [PeerCredentialPolicy], SignerProcessIsolationReceipt
    ] = enforce_signer_process_isolation,
) -> int:
    root = Path(args.repo_root).resolve()
    owner_path = Path(args.owner_authority_config).resolve()
    try:
        manifest_selection, selection_boundary = (
            load_system_service_manifest_selection(
                owner_config_path=owner_path,
                repo_root=root,
            )
        )
        verified_outcome_authority = (
            verified_outcome_authority_loader(
                owner_config_path=owner_path,
                repo_root=root,
            )
            if verified_outcome_authority_loader is not None
            else None
        )
    except Exception:
        emit(_receipt_json(None, (FAIL_SYSTEM_SERVICE_SELECTION,)))
        return 2
    result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=root,
        config_path=None,
        resolver_factory=resolver_factory,
        serve_bounded=serve_bounded,
        expected_config_digest=None,
        run_packet_path=None,
        expected_session_id=None,
        expected_owner_authority_config_path=owner_path,
        principal_key_resolver=principal_key_resolver,
        proposal_replay_high_water_store=proposal_replay_high_water_store,
        verified_outcome_signing_authority=verified_outcome_authority,
        process_isolation_required=True,
        process_isolation_gate=process_isolation_gate,
        manifest_selection=manifest_selection,
        manifest_selection_boundary=selection_boundary,
    )
    emit(_receipt_json(result, ()))
    return 0 if result.accepted else 2

def _receipt_json(
    result: SignerSocketServiceRuntimeBootstrapResult | None,
    reasons: tuple[str, ...],
) -> str:
    accepted = result is not None and result.accepted is True
    payload = {
        "status": (
            SYSTEM_SERVICE_ENTRYPOINT_ACCEPT
            if accepted
            else SYSTEM_SERVICE_ENTRYPOINT_REJECT
        ),
        "result": result.to_dict() if result is not None else None,
        "rejection_reasons": list(
            reasons or (result.rejection_reasons if result else ())
        ),
        "no_serialized_argv_executed": True,
        "no_signer_process_spawned": True,
        "secret_resolution_mode": "fail_closed_e0_not_admitted",
        "no_shell_invoked": True,
        "no_main_runtime_wiring": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_pr_created": True,
        "no_holoindex_reindex_performed": True,
    }
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    return run_reddog_signer_system_service_entrypoint(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))


__all__ = [
    "SYSTEM_SERVICE_ENTRYPOINT_ACCEPT",
    "SYSTEM_SERVICE_ENTRYPOINT_REJECT",
    "build_signer_system_service_parser",
    "main",
    "run_reddog_signer_system_service_entrypoint",
]
