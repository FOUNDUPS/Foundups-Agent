"""Exact non-initial HIGH composition; existing lease, custody and signer owners."""
from dataclasses import dataclass
from pathlib import Path
import time

from .reddog_grant_authority_service import (
    GrantAuthorityServiceDependencies, _current_inputs, REJECT,
)
from .reddog_signer_delegated_authority_runtime import SigningRequest, SigningResponse
from .reddog_signer_secret_grant_authority_policy import SECRET_GRANT_SIGNING_OPERATION
from .reddog_signer_secret_grant_issuance import validate_secret_grant_signing_request
from .reddog_signer_secret_grant_durable_rate_authority import DurableSignerSecretGrantRateAuthority
from .reddog_signer_wsp71_ephemeral_backend_factory import Wsp71EphemeralSignerBackendFactory
from modules.infrastructure.secrets_mcp.src.systemd_credential_secret_resolver import SystemdCredentialSecretResolver


def _high_models(repo, path, policy):
    from .reddog_parent_consensus_model_evidence import load_protected_parent_model_artifacts, verified_model_evidence
    artifacts = load_protected_parent_model_artifacts(owner_config_path=path,
        repo_root=repo, expected_owner_config_id=policy['owner_config_id'])
    verified_model_evidence(owner_path=path, repo=repo, owner_id=policy['owner_config_id'],
        artifacts=artifacts, clock=lambda: int(time.time()))
    return artifacts


def _high_authority(repo, path, dependencies, scope, models):
    from .reddog_consensus_nonce_authority import ProtectedConsensusNonceAuthority
    from .reddog_current_parent_consensus_authority import CurrentParentConsensusAuthority
    from .reddog_current_effect_signing_authority import CurrentEffectSigningAuthority
    from .reddog_elevated_authority_consensus_signer_verification import ElevatedConsensusSignerAuthority
    from .reddog_signer_owner_e0_current_selection import _scope_admission
    nonce = dependencies.consensus_nonce_authority
    if (type(nonce) is not ProtectedConsensusNonceAuthority or nonce._owner.path != path
            or nonce._owner.repo != repo):
        raise ValueError('grant_service_consensus_custody_required')
    current = _scope_admission(scope, owner_config_path=path, repo_root=repo)[1]
    nonce._owner.current(current)
    parent = CurrentParentConsensusAuthority(repo, path, models)
    # The scoped route accepts only canonical parent/effect-v2 proofs. Legacy
    # resolver slots are unreachable; never install permissive placeholder APIs.
    effect = CurrentEffectSigningAuthority(repo, path, None, None, None, None,
        nonce, parent_authority=parent)
    return ElevatedConsensusSignerAuthority(None, None, None, None, None, None,
        nonce, parent_authority=parent, effect_authority=effect, _live_scope=scope)


@dataclass(frozen=True, slots=True)
class _CurrentHighGrantBackend:
    repo: Path
    owner_path: Path
    dependencies: GrantAuthorityServiceDependencies

    def authorize(self, action):
        from .reddog_grant_authority_wsp71_permission_rehydration import _authorize_current_grant_authority_scoped_use
        return _authorize_current_grant_authority_scoped_use(owner_config_path=self.owner_path,
            repo_root=self.repo, owner_policy=self.dependencies.owner_policy,
            now_epoch=int(time.time()), revocation_oracle=self.dependencies.revocation_oracle, action=action)

    def sign(self, request, peer):
        from .reddog_parent_consensus_proof import SCHEMA as PARENT_SCHEMA
        from .reddog_effect_consensus_proof import SCHEMA_V2
        policy = self.dependencies.owner_policy
        if (type(request) is not SigningRequest or request.requested_operation != SECRET_GRANT_SIGNING_OPERATION
                or request.authority_tier != 'HIGH' or type(request.elevated_consensus_proof) is not dict
                or request.elevated_consensus_proof.get('schema_version') not in {PARENT_SCHEMA, SCHEMA_V2}
                or getattr(peer, 'boundary_attested', False) is not True
                or getattr(peer, 'peer_principal_id', None) != policy['grant_requester_principal_id']):
            return SigningResponse(accepted=False, rejection_code=REJECT)
        try:
            return self.authorize(lambda scope: self._sign_current(request, peer, scope))
        except Exception:
            return SigningResponse(accepted=False, rejection_code=REJECT)

    def _sign_current(self, request, peer, scope):
        _, policy = _current_inputs(self.repo, self.owner_path, self.dependencies)
        if validate_secret_grant_signing_request(request, policy, now_epoch=int(time.time())) is None:
            return SigningResponse(accepted=False, rejection_code=REJECT)
        models = _high_models(self.repo, self.owner_path, self.dependencies.owner_policy)
        elevated = _high_authority(self.repo, self.owner_path, self.dependencies, scope, models)
        if not _high_proof_current(elevated, request.elevated_consensus_proof, scope):
            return SigningResponse(accepted=False, rejection_code=REJECT)
        built = Wsp71EphemeralSignerBackendFactory(profile=self.dependencies.issuer_profile,
            resolver=SystemdCredentialSecretResolver(self.dependencies.credential_binding),
            secret_grant_authority_policy=policy,
            secret_grant_rate_authority=DurableSignerSecretGrantRateAuthority(self.dependencies.replay_store),
            elevated_consensus_signer_authority=elevated)()
        if not built.ok or built.backend is None:
            return SigningResponse(accepted=False, rejection_code=REJECT)
        result = built.backend.sign(request, peer)
        if models != _high_models(self.repo, self.owner_path, self.dependencies.owner_policy):
            raise ValueError('grant_service_models_changed')
        return result


def _high_proof_current(authority, proof, scope):
    from .reddog_parent_consensus_proof import SCHEMA
    if proof['schema_version'] == SCHEMA:
        frozen = {k: v for k, v in proof.items() if k != 'target_signing_request'}
        return authority.parent_authority._verify_scoped(frozen, scope) is not None
    return authority.effect_authority._verify(proof, _scope=scope) is not None
