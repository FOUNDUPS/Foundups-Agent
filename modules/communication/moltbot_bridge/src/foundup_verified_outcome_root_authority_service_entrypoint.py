"""Root-owned service entrypoint for verified-outcome admission authority."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Sequence

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_socket_service import (
    RootAuthoritySocketServiceResult,
    serve_root_authority_bounded,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    KernelPeerCredentialAttestor,
    PeerCredentialPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader import (
    load_root_authority_service_dependencies,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="foundup-verified-outcome-root-authority",
        description="Serve root-owned verified-outcome reserve/commit decisions.",
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--owner-authority-config", required=True)
    parser.add_argument("--max-requests", type=int, default=128)
    return parser


def run_entrypoint(
    argv: Sequence[str] | None = None,
    *,
    emit: Callable[[str], None] = print,
) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        dependencies = load_root_authority_service_dependencies(
            args.owner_authority_config,
            repo_root=Path(args.repo_root).resolve(),
        )
        attestor = KernelPeerCredentialAttestor(_peer_policy(dependencies))
        result = serve_root_authority_bounded(
            repo_root=Path(args.repo_root).resolve(),
            socket_path=dependencies.socket_path,
            signer_gid=dependencies.signer_gid,
            state=dependencies.state,
            snapshot_supplier=dependencies.snapshot_supplier,
            revocation_authority=getattr(dependencies, "revocation_authority", None),
            peer_attestor=attestor,
            max_requests=args.max_requests,
        )
    except Exception:
        result = RootAuthoritySocketServiceResult(
            accepted=False,
            status="ROOT_AUTHORITY_SERVICE_REJECT",
            rejection_reasons=("root_authority_service_startup_rejected",),
        )
    emit(json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":")))
    return 0 if result.accepted else 2


def main(argv: Sequence[str] | None = None) -> int:
    return run_entrypoint(argv)


def _peer_policy(dependencies):
    from .foundup_verified_outcome_root_revocation_protocol import GRANT_PEER_PRINCIPAL

    principals = {dependencies.signer_uid: dependencies.signer_principal_id}
    groups = (dependencies.signer_gid,)
    grant = getattr(dependencies, "grant_peer_identity", None)
    if grant is not None:
        if (type(grant) is not tuple or len(grant) != 2
                or any(type(value) is not int or value <= 0 for value in grant)
                or grant[0] in principals):
            raise ValueError("root_authority_grant_peer_invalid")
        principals[grant[0]] = GRANT_PEER_PRINCIPAL
        groups = tuple(sorted(set((*groups, grant[1]))))
    return PeerCredentialPolicy(principals, allowed_gids=groups,
        credential_source_prefix="kernel_root_authority_peer")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))


__all__ = ["build_parser", "main", "run_entrypoint"]
