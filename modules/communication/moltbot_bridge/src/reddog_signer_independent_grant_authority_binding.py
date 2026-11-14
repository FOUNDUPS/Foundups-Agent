"""Public client identity for one independently hosted grant authority."""

from __future__ import annotations

from dataclasses import dataclass

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    IsolatedSignerClient,
)


@dataclass(frozen=True, slots=True)
class IndependentGrantAuthorityBinding:
    """Bind a public signer client to its signed grant-authority identity."""

    client: IsolatedSignerClient
    authority_root: str
    principal_id: str
    principal_provider: str
    public_key: str
    key_epoch: str
    requester_principal_id: str


__all__ = ["IndependentGrantAuthorityBinding"]
