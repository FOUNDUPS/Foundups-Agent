"""Composed elevated-authority chain through real production seams."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from types import SimpleNamespace

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src import (
    reddog_signer_independent_secret_grant_provider as provider_module,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_signer_client import (
    ElevatedConsensusExternalSignerClient,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_signer_verification import (
    ElevatedConsensusSignerAuthority,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
)
from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_e2e_support import (
    NOW,
    Resolver,
    build_route,
    public_key,
)
from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_test_doubles import (
    TestConsensusNonceAuthority,
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
    _PrincipalResolver,
    _SnapshotResolver,
    _issue_authority,
    _principal,
    _request,
    _snapshot,
)


class _RoleRoutingSigner:
    def __init__(self, clients):
        self.clients = clients
        self.responses = []

    def sign_with_secret_grant(self, request, grant):
        response = self.clients[request.signer_role].sign_with_secret_grant(
            request, grant
        )
        self.responses.append(response)
        return response


def test_complete_elevated_consensus_chain_commits_authority(
    tmp_path, monkeypatch
) -> None:
    principal_key = Ed25519PrivateKey.generate()
    reddog_key = Ed25519PrivateKey.generate()
    request = _request(
        principal_public_key=public_key(principal_key),
        reddog_public_key=public_key(reddog_key),
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
    authority = _authority(request)
    signer, routing_signer = _external_signer(
        tmp_path, monkeypatch, authority,
        {"principal": principal_key, "reddog": reddog_key},
    )
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()
    runtime_root.mkdir()
    store_path = runtime_root / "authority.json"
    store = AtomicJsonAuthorityRuntimeStore(
        store_path, allowed_root=runtime_root, repo_root=repo_root
    )

    result = _issue_authority(
        request=request, store=store, signer=signer,
        principal_resolver=_PrincipalResolver(principal),
        snapshot_resolver=_SnapshotResolver(
            {request.permission_snapshot_digest: _snapshot(expires_at=NOW + 600)}
        ),
        elevated_consensus_capability=capability, now=NOW,
    )

    assert result.accepted is True, (
        result.receipt.rejection_reasons, routing_signer.responses
    )
    assert len(result.receipt.store_revision) == 64
    assert request.work_order_id in store.load()["issued_authorities"]
    restarted = AtomicJsonAuthorityRuntimeStore(
        store_path, allowed_root=runtime_root, repo_root=repo_root
    )
    assert request.work_order_id in restarted.load()["issued_authorities"]


def _authority(request):
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
        nonce_authority=TestConsensusNonceAuthority(),
    )


def _external_signer(tmp_path, monkeypatch, authority, target_keys):
    providers, clients, policies = {}, {}, {}
    for role, target_key in target_keys.items():
        root = tmp_path / role
        root.mkdir()
        provider, client, policy = build_route(
            root, role, target_key, Ed25519PrivateKey.generate(), authority
        )
        providers[role], clients[role] = provider, client
        policies[str(provider.owner_config_path)] = policy

    @contextmanager
    def owner_lease(*, owner_config_path, **_kwargs):
        policy = policies[str(owner_config_path)]
        yield SimpleNamespace(
            policy=policy,
            resolver=Resolver(
                policy["grant_authority_principal_id"],
                policy["grant_authority_principal_provider"],
                policy["grant_authority_public_key"],
            ),
        )

    monkeypatch.setattr(
        provider_module, "lease_validated_owner_e0_current_admission", owner_lease
    )
    routing = _RoleRoutingSigner(clients)
    return ElevatedConsensusExternalSignerClient(
        signer=routing,
        principal_grant_provider=providers["principal"],
        reddog_grant_provider=providers["reddog"],
    ), routing
