"""One-shot grant admission for resolve-per-sign signer backends.

This boundary stores no signing backend or secret material. A verified grant is
consumed before an injected factory resolves the configured keys, builds one
ephemeral backend, and signs one exact request. Production grant supply and
strict native-memory zeroization remain separate deployment gates.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Protocol

from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    IsolatedSignerBackend,
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    SignerKeyProviderDryRunResult,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant import (
    ExpectedSignerSecretGrantBinding,
    SignerSecretAccessGrantBoundary,
    SignerSecretAccessGrantRejected,
    signer_secret_access_request_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_resolve_per_sign_validation import (
    backend_identity_matches,
    factory_binding_matches,
    provider_result_matches,
    response_matches,
    signature_matches,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PrincipalKeyResolver,
    SignatureVerifier,
    constant_time_compare,
)

REJECT_SECRET_GRANT_REQUIRED = "REJECT_SIGNER_SECRET_GRANT_REQUIRED"
REJECT_SECRET_GRANT_INVALID = "REJECT_SIGNER_SECRET_GRANT_INVALID"
REJECT_SECRET_RESOLUTION_FAILED = "REJECT_SIGNER_SECRET_RESOLUTION_FAILED"
REJECT_EPHEMERAL_BACKEND_INVALID = "REJECT_SIGNER_EPHEMERAL_BACKEND_INVALID"


class EphemeralSignerBackendFactory(Protocol):
    signer_agent_id: str
    permission_snapshot_digest: str

    def __call__(self) -> SignerKeyProviderDryRunResult:
        """Resolve current keys and return one non-persistent backend."""


@dataclass(frozen=True)
class ResolvePerSignBinding:
    issuer_principal_id: str
    issuer_principal_provider: str
    issuer_public_key: str
    signer_agent_id: str
    signer_profile_id: str
    signing_key_ref_hash: str
    audit_mac_key_ref_hash: str
    key_epoch: str
    permission_snapshot_digest: str
    owner_config_id: str
    signer_generation_id: str
    signer_public_key: str
    signer_key_fingerprint: str
    replay_store_binding_digest: str
    replay_store_id: str
    replay_store_durability_receipt_id: str
    replay_store_instance_digest: str


@dataclass(frozen=True)
class ResolvePerSignSignerBackend(IsolatedSignerBackend):
    binding: ResolvePerSignBinding
    grant_boundary: SignerSecretAccessGrantBoundary
    signature_verifier: SignatureVerifier
    principal_key_resolver: PrincipalKeyResolver
    backend_factory: EphemeralSignerBackendFactory

    def sign(
        self, request: SigningRequest, peer: SignerPeerAttestation
    ) -> SigningResponse:
        return _reject(REJECT_SECRET_GRANT_REQUIRED)

    def sign_with_secret_grant(
        self,
        request: SigningRequest,
        peer: SignerPeerAttestation,
        grant: Mapping[str, Any],
    ) -> SigningResponse:
        if (
            type(request) is not SigningRequest
            or type(peer) is not SignerPeerAttestation
            or peer.boundary_attested is not True
            or not constant_time_compare(
                request.requester_principal_id, peer.peer_principal_id
            )
        ):
            return _reject(REJECT_SECRET_GRANT_INVALID)
        if not factory_binding_matches(self.backend_factory, self.binding):
            return _reject(REJECT_EPHEMERAL_BACKEND_INVALID)
        expected = self._expected(request, peer)
        if not (
            self.grant_boundary.replay_store_matches(expected)
            and self.grant_boundary.atomic_revocation
        ):
            return _reject(REJECT_SECRET_GRANT_INVALID)
        try:
            capability = self.grant_boundary.verify(
                grant,
                expected=expected,
                signature_verifier=self.signature_verifier,
                principal_key_resolver=self.principal_key_resolver,
            )
            consumed_grant = self.grant_boundary.consume(capability)
        except (SignerSecretAccessGrantRejected, TypeError, ValueError):
            return _reject(REJECT_SECRET_GRANT_INVALID)
        return self._resolve_and_sign(request, peer, consumed_grant)

    def _resolve_and_sign(
        self,
        request: SigningRequest,
        peer: SignerPeerAttestation,
        consumed_grant: Mapping[str, Any],
    ) -> SigningResponse:
        try:
            built = self.backend_factory()
        except Exception:
            return _reject(REJECT_SECRET_RESOLUTION_FAILED)
        if type(built) is not SignerKeyProviderDryRunResult or built.ok is not True:
            return _reject(REJECT_SECRET_RESOLUTION_FAILED)
        if not provider_result_matches(built, self.binding):
            return _reject(REJECT_EPHEMERAL_BACKEND_INVALID)
        backend = built.backend
        if (
            backend is None
            or backend is self
            or not backend_identity_matches(backend, self.binding)
        ):
            return _reject(REJECT_EPHEMERAL_BACKEND_INVALID)
        try:
            response = self.grant_boundary.authorize_consumed_use(
                consumed_grant, lambda: backend.sign(request, peer)
            )
            if type(response) is not SigningResponse or response.accepted is not True:
                return _reject(REJECT_EPHEMERAL_BACKEND_INVALID)
            if not (
                response_matches(response, request, self.binding)
                and signature_matches(
                    response, request, self.signature_verifier, self.binding
                )
            ):
                return _reject(REJECT_EPHEMERAL_BACKEND_INVALID)
            return response
        except SignerSecretAccessGrantRejected:
            return _reject(REJECT_SECRET_GRANT_INVALID)
        except Exception:
            return _reject(REJECT_EPHEMERAL_BACKEND_INVALID)
        finally:
            backend = None
            built = None

    def _expected(
        self, request: SigningRequest, peer: SignerPeerAttestation
    ) -> ExpectedSignerSecretGrantBinding:
        return ExpectedSignerSecretGrantBinding(
            **asdict(self.binding),
            signing_request_digest=signer_secret_access_request_digest(
                request.to_dict()
            ),
            requested_operation=request.requested_operation,
            authority_tier=request.authority_tier,
            attested_peer_principal_id=peer.peer_principal_id,
        )


def _reject(code: str) -> SigningResponse:
    return SigningResponse(
        accepted=False,
        rejection_code=code,
        no_secret_material_returned=True,
    )


__all__ = [
    "EphemeralSignerBackendFactory",
    "REJECT_EPHEMERAL_BACKEND_INVALID",
    "REJECT_SECRET_GRANT_INVALID",
    "REJECT_SECRET_GRANT_REQUIRED",
    "REJECT_SECRET_RESOLUTION_FAILED",
    "ResolvePerSignBinding",
    "ResolvePerSignSignerBackend",
]
