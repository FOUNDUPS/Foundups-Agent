"""Per-use current-generation principal authority resolution for signer E0."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityRecord,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_principal_authority import (
    load_current_generation_principal_authority_resolver,
)


@dataclass(frozen=True)
class ManifestBoundCurrentPrincipalAuthorityResolver:
    """Lease and re-read the current signed generation for every resolution."""

    repo_root: Path
    boundary: Any
    clock: Callable[[], float] = field(default=time.time, repr=False)

    def resolve(
        self, principal_id: str, principal_provider: str
    ) -> PrincipalAuthorityRecord | None:
        return self._resolve("resolve", principal_id, principal_provider)

    def resolve_unique(self, principal_id: str) -> PrincipalAuthorityRecord | None:
        return self._resolve("resolve_unique", principal_id)

    def _resolve(self, method: str, *args: str) -> PrincipalAuthorityRecord | None:
        capability = self.boundary.select({}, now_epoch=int(self.clock()))
        with self.boundary._lease_current(capability) as selection:
            resolver = load_current_generation_principal_authority_resolver(
                repo_root=self.repo_root.resolve(), selection=selection
            )
            return getattr(resolver, method)(*args)


__all__ = ["ManifestBoundCurrentPrincipalAuthorityResolver"]
