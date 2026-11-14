"""One-time root installer for verified-outcome authority state."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Sequence

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service import (
    initialize_root_authority_state,
)
from modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader import (
    load_root_authority_service_dependencies,
)


@dataclass(frozen=True)
class RootAuthorityProvisionResult:
    accepted: bool
    status: str
    rejection_reasons: tuple[str, ...]
    no_signing_key_loaded: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="foundup-verified-outcome-root-authority-provision",
        description="Provision root authority state exactly once.",
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--owner-authority-config", required=True)
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
        initialize_root_authority_state(
            dependencies.state,
            dependencies.snapshot_supplier(),
            now_epoch=int(time.time()),
        )
        result = RootAuthorityProvisionResult(
            accepted=True,
            status="ROOT_AUTHORITY_PROVISION_ACCEPT",
            rejection_reasons=(),
        )
    except Exception:
        result = RootAuthorityProvisionResult(
            accepted=False,
            status="ROOT_AUTHORITY_PROVISION_REJECT",
            rejection_reasons=("root_authority_provision_rejected",),
        )
    emit(json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":")))
    return 0 if result.accepted else 2


def main(argv: Sequence[str] | None = None) -> int:
    return run_entrypoint(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))


__all__ = ["RootAuthorityProvisionResult", "build_parser", "main", "run_entrypoint"]
