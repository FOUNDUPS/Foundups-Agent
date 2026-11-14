"""Opaque root-anchor client fixture for durable revocation tests."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src import (
    foundup_verified_outcome_root_revocation_client as client_module,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_state import (
    INSTALLATION_BINDING,
    RootVerifiedOutcomeAuthorityState,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_client import (
    RootRevocationAnchorAuthority,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_protocol import (
    OP_ADVANCE,
    RootRevocationResponse,
    request_from_bytes,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    SignerGrantRevocationAuthorityBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_store import (
    SignerGrantRevocationAuthorityStore,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)


def open_anchor_state(
    policy: Mapping[str, Any], repo_root: Path
) -> RootVerifiedOutcomeAuthorityState:
    parent = Path(policy["revocation_root"]).parent
    stores = []
    roots = {
        "state": "anchor-primary",
        "state_witness": "anchor-witness",
        "installation": "anchor-installation",
    }
    for name in ("state", "state_witness", "installation"):
        root = parent / roots[name]
        stores.append(SqliteMonotonicAuthorityStore(
            root / f"{name}.sqlite3", allowed_root=root, repo_root=repo_root,
            store_id=f"revocation-anchor-{name}",
            durability_receipt_id=_digest(f"anchor-{name}-durable"),
        ))
    state = RootVerifiedOutcomeAuthorityState(
        *stores, repo_root=repo_root, require_root_ownership=False
    )
    if stores[2].load(INSTALLATION_BINDING) is None:
        state.initialize(
            generation=ProposalReplayHighWater(1, _digest("anchor-owner")[7:]),
            replay_binding=_digest("anchor-bootstrap-binding"),
            replay_anchor=ProposalReplayHighWater(
                1, _digest("anchor-bootstrap")[7:]
            ),
            installation_revision=_digest("anchor-installation")[7:],
        )
    return state


def anchor_client(
    policy: Mapping[str, Any], binding: SignerGrantRevocationAuthorityBinding,
    store: SignerGrantRevocationAuthorityStore,
    root_state: RootVerifiedOutcomeAuthorityState,
) -> RootRevocationAnchorAuthority:
    class Exchange:
        def __init__(self) -> None:
            self.root_state = root_state

        def exchange(self, raw: bytes) -> bytes:
            request = request_from_bytes(raw)
            current = root_state.load(request.binding_digest)
            if request.operation == OP_ADVANCE:
                current = _advance(request, current, root_state, store)
            return _response(request, current, accepted=True)

    authority = object.__new__(RootRevocationAnchorAuthority)
    client_module._issue_client(authority, client_module._ClientState(
        descriptor={"descriptor_id": _digest("root-descriptor")},
        owner_config_id=str(policy["owner_config_id"]),
        policy={
            key: str(value) if isinstance(value, Path) else value
            for key, value in policy.items()
        },
        binding=binding, exchange=Exchange(),
        request_signer=lambda _value: "ed25519-sig-v1:" + "A" * 86,
    ))
    return authority


def raw_anchor(authority: RootRevocationAnchorAuthority):
    return client_module._lookup_client(authority).exchange.root_state


def _advance(request, current, root_state, store):
    local = store.state()
    candidate = local.pending if (
        local.pending is not None
        and local.pending["snapshot_id"] == request.snapshot_id
    ) else local.current
    if candidate is None or candidate["snapshot_id"] != request.snapshot_id:
        raise ValueError("test_anchor_candidate_missing")
    wanted = high_water(candidate)
    expected = None if local.current is None else high_water(local.current)
    if current != wanted:
        root_state.advance(request.binding_digest, expected=expected, next_value=wanted)
    return root_state.load(request.binding_digest)


def _response(request, value, *, accepted: bool) -> bytes:
    return RootRevocationResponse(
        status="ACCEPT" if accepted else "REJECT", request_id=request.request_id,
        descriptor_id=request.descriptor_id, owner_config_id=request.owner_config_id,
        policy_id=request.policy_id, binding_digest=request.binding_digest,
        snapshot_id=None if value is None else "sha256:" + value.state_revision,
        state=("ADVANCED" if request.operation == OP_ADVANCE else "LOADED")
        if accepted else "REJECTED",
        sequence=None if value is None else value.sequence,
        revision=None if value is None else value.state_revision,
        reason="" if accepted else "rejected",
    ).to_bytes()


def high_water(snapshot: Mapping[str, Any]) -> ProposalReplayHighWater:
    return ProposalReplayHighWater(
        sequence=int(snapshot["sequence"]),
        state_revision=str(snapshot["snapshot_id"])[7:],
    )


def _digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("ascii")).hexdigest()


__all__ = ["anchor_client", "high_water", "open_anchor_state", "raw_anchor"]
