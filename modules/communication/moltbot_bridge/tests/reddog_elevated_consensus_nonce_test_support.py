"""Grant-authority signing fixture for consensus nonce transaction tests."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_capability import (
    prepare_elevated_authority_signing_permit,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_signer_client import (
    admit_secret_grant_consensus,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_signer_verification import (
    ElevatedConsensusSignerAuthority,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    HIGH_AUTHORITY_TIER,
    build_delegated_authority_signing_requests,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_issuance import (
    build_secret_grant_signing_request,
)
from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_e2e_support import (
    NOW,
    Resolver,
    build_route,
    public_key,
)
from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_test_support import (
    TestAuthorRuntimeEvidenceResolver,
    TestConsensusVerifier,
    TestPolicyResolver,
    TestReviewerKeyResolver,
    TestReviewerRuntimeEvidenceResolver,
    TestSovereignAuthorizationResolver,
    verified_consensus_for_request,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_delegated_authority_runtime import (
    _principal,
    _request,
)


def build_grant_signing_case(
    root: Path,
    nonce_authority,
):
    target_key, grant_key = (
        Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    )
    request = _request(
        principal_public_key=public_key(target_key),
        issued_at=NOW - 5,
        identity_expires_at=NOW + 3600,
        work_authority_expires_at=NOW + 300,
    )
    principal = replace(
        _principal(), principal_public_key=request.principal_public_key
    )
    request, capability, _ = verified_consensus_for_request(
        request, now=NOW, principal=principal
    )
    consensus_authority = _consensus_authority(request, nonce_authority)
    provider, _, policy = build_route(
        root, "principal", target_key, grant_key, consensus_authority
    )
    provider = replace(provider, ttl_seconds=120)
    owner = SimpleNamespace(
        policy=policy,
        resolver=Resolver(
            "grant:owner", "local", policy["grant_authority_public_key"]
        ),
    )
    signing_request = _grant_request(
        provider, owner, request, principal, capability, policy
    )
    backend = next(
        cell.cell_contents
        for cell in provider.grant_authority.client.connector.__closure__
        if hasattr(cell.cell_contents, "private_key")
    )
    peer = SignerPeerAttestation(
        "provider:grant-client", "unix_socket", "SO_PEERCRED", True
    )
    return backend, signing_request, peer


def _consensus_authority(request, nonce_authority):
    return ElevatedConsensusSignerAuthority(
        signature_verifier=TestConsensusVerifier(),
        reviewer_key_resolver=TestReviewerKeyResolver(),
        runtime_evidence_resolver=TestReviewerRuntimeEvidenceResolver(NOW),
        author_runtime_evidence_resolver=TestAuthorRuntimeEvidenceResolver(
            request, NOW
        ),
        sovereign_authorization_resolver=TestSovereignAuthorizationResolver(
            request, NOW
        ),
        policy_resolver=TestPolicyResolver(),
        nonce_authority=nonce_authority,
    )


def _grant_request(provider, owner, request, principal, capability, policy):
    plan = build_delegated_authority_signing_requests(
        request, principal, authority_tier=HIGH_AUTHORITY_TIER,
        has_runtime_binding=True,
    )
    permit = prepare_elevated_authority_signing_permit(
        capability, authority_request=request,
        signing_requests=plan[2:], now=NOW,
    )
    proof = admit_secret_grant_consensus(plan[2], permit, now=NOW)
    binding = provider._resolve_binding(owner)
    grant_policy = provider._authority_policy(owner, binding)
    grant = provider._unsigned_grant(plan[2], binding, policy, NOW)
    return build_secret_grant_signing_request(
        grant, policy=grant_policy,
        consensus_receipt_digest=request.consensus_receipt_digest,
        elevated_consensus_proof=proof,
    )


__all__ = ["build_grant_signing_case"]
