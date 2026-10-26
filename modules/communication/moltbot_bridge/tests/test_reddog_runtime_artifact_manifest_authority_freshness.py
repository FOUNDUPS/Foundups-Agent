"""Freshness regressions for fenced runtime-manifest authority."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_authority import (
    create_runtime_artifact_manifest_authority_boundary,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    InMemoryNonceStore,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import (
    NOW,
    VALVE,
    NoRevocation,
    PrincipalKeyResolver,
    SnapshotResolver,
    _build_harness,
)


def test_authority_expiry_during_fenced_operation_rejects(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path)
    clock = [NOW]
    boundary = create_runtime_artifact_manifest_authority_boundary(
        repo_root=harness.repo_root,
        runtime_root=harness.runtime_root,
        work_state_store=harness.work_state_store,
        signature_verifier=Ed25519SignatureVerifier(),
        principal_key_resolver=PrincipalKeyResolver(
            harness.principal_public_key
        ),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=SnapshotResolver(),
        revocation_oracle=NoRevocation(),
        required_valve_state=VALVE,
        trusted_clock=lambda: clock[0],
    )
    queue_item_id = harness.authority_boundary.require(
        harness.authority
    )["queue_item_id"]
    authority = boundary.issue(
        identity=harness.identity,
        work_authority=harness.work_authority,
        queue_item_id=queue_item_id,
        now_epoch=NOW,
    )

    with pytest.raises(ValueError, match="manifest_authority_rejected"):
        with boundary.revalidation_fence(authority, now_epoch=NOW):
            clock[0] = NOW + 1_000
