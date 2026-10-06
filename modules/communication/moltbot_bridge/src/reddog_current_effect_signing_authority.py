"""Current-owner effect approval composed into grant-signer admission.

Constructor dependencies are trusted composition inputs, not self-enrollment.
No default runtime, policy, nonce authority, or signing credentials are minted.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import time

from . import reddog_current_effect_consent_verification as consent
from . import reddog_current_effect_reviewer_verification as reviews
from .reddog_effect_consensus_proof import snapshot_effect_consensus_proof, _mint_effect_signing_permit
from .reddog_elevated_authority_consensus_contract import canonical_json_digest
from .reddog_elevated_authority_consensus_evidence import author_runtime_evidence_matches
from .reddog_elevated_consensus_signer_reservation import reserve_elevated_consensus_nonce
from .reddog_runtime_artifact_manifest_contract import canonical_json
from .reddog_signer_secret_access_grant_contract import signer_secret_access_request_digest


def _now_epoch():
    return int(time.time())


@dataclass(frozen=True, slots=True)
class CurrentEffectSigningAuthority:
    repo_root: Path
    owner_config_path: Path
    policy_resolver: object
    runtime_evidence_resolver: object
    author_runtime_evidence_resolver: object
    sovereign_authorization_resolver: object
    nonce_authority: object
    revoked_key_epochs: frozenset[str] = frozenset()

    def prepare_permit(self, proof):
        checked = self._verify(proof)
        if checked is None:
            return None
        frozen, _, _, expires, _ = checked
        return _mint_effect_signing_permit(frozen, expires_at=expires)

    def reserve(self, proof, *, signing_request_digest, now, grant_expires_at=None):
        if type(now) is not int or now < 0:
            return None
        checked = self._verify(proof)
        if checked is None:
            return None
        frozen, context, target, expires, current = checked
        if type(grant_expires_at) is not int or not now < grant_expires_at <= expires:
            return None
        digest = signer_secret_access_request_digest(target.to_dict())
        if digest != signing_request_digest or not context.issued_at <= now < expires:
            return None
        nonce = canonical_json_digest({"effect_context": context.to_dict(), "target": digest})
        try:
            return reserve_elevated_consensus_nonce(
                self.nonce_authority, nonce, expires_at=expires,
                subject="effect-consensus:" + frozen["consensus_receipt"]["receipt_id"],
                validity_check=current,
            )
        except Exception:
            return None

    def _verify(self, proof):
        try:
            frozen, context, parent, target = snapshot_effect_consensus_proof(proof)
            repo = Path(self.repo_root).resolve()
            owner = reviews.loader._load_owner_config(self.owner_config_path, repo=repo)
            if owner["schema_version"] != reviews.loader.SCHEMA_VERSION_V7:
                return None
            selected, boundary = reviews.loader._manifest_selection_from_owner(owner, repo=repo)
            with boundary._lease_current(selected) as selection:
                interval = self._verify_leased(owner, repo, selection, frozen, context, parent, target)
            if interval is None or not interval[2]():
                return None
            snapshot_effect_consensus_proof(frozen)
            return frozen, context, target, interval[1], interval[2]
        except Exception:
            return None

    def _verify_leased(self, owner, repo, selection, proof, context, parent, target):
        start = _now_epoch()
        if type(start) is not int or selection["owner_config_id"] != owner["config_id"]:
            return None
        selected_before = canonical_json(dict(selection))
        policy = self.policy_resolver.resolve(context.consensus_policy_digest)
        author = self.author_runtime_evidence_resolver.resolve(parent.model_runtime_binding_verification_receipt_id)
        if not author_runtime_evidence_matches(author, parent, start):
            return None
        author_before, policy_before = asdict(author), asdict(policy)
        common = dict(context=context, target=target, expected_target=target.to_dict(), policy=policy)
        assertion = proof["consensus_receipt"]["consent"]
        consent_inputs = dict(common, parent=parent)
        consent_result = _consent_leased(self, owner, repo, selection, assertion, consent_inputs, start)
        if consent_result is None:
            return None
        sovereign = self.sovereign_authorization_resolver.resolve(parent.sovereign_authorization_digest)
        if type(sovereign) is not type(consent_result.parent_authorization) or sovereign != consent_result.parent_authorization:
            return None
        sovereign_before = asdict(sovereign)
        review_inputs = dict(common, authority_request=parent,
            decisions=proof["consensus_receipt"]["decisions"],
            runtime_evidence_resolver=self.runtime_evidence_resolver,
            revoked_key_epochs=self.revoked_key_epochs)
        valid_until = [context.expires_at, author.expires_at]
        completion_checks = []
        if reviews._verify_leased(owner, self.owner_config_path, repo, selection,
                review_inputs, reviews._input_snapshot(review_inputs), valid_until=valid_until,
                completion_checks=completion_checks) is not True:
            return None
        if _consent_leased(self, owner, repo, selection, assertion, consent_inputs, _now_epoch()) is None:
            return None
        finish = _now_epoch()
        valid = (type(finish) is int and finish >= start
                and author_before == asdict(author) and policy_before == asdict(policy)
                and sovereign_before == asdict(sovereign)
                and author_runtime_evidence_matches(author, parent, finish)
                and selected_before == canonical_json(dict(selection)))
        expires = min(valid_until)
        def current():
            now = _now_epoch()
            return (type(now) is int and start <= now < expires
                    and author_before == asdict(author) and policy_before == asdict(policy)
                    and sovereign_before == asdict(sovereign)
                    and all(check(now) for check in completion_checks))
        return (start, expires, current) if valid else None


def _consent_leased(authority, owner, repo, selection, assertion, inputs, now):
    checked = consent.validate_effect_consent_assertion(assertion)
    message = consent.canonical_effect_consent_signing_input({k: v for k, v in checked.items() if k != "signature"})
    return consent._verify_leased(
        owner, authority.owner_config_path, repo, selection, checked, assertion,
        inputs, consent._snapshot(assertion, inputs), consent._evidence(checked, message), message, now,
    )
