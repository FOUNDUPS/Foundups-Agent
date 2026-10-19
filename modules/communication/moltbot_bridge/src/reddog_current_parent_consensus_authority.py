"""Current parent consensus composed from protected owners and signed data.

Model artifacts and proof inputs are untrusted data, never injected verifiers.
No provider call, grant, worktree effect or runtime enrollment occurs here.
"""

from dataclasses import dataclass, asdict
from pathlib import Path

from . import reddog_current_parent_consent_verification as consent
from . import reddog_signer_current_principal_authority_resolver as principals
from .reddog_parent_consensus_proof import snapshot_parent_consensus_proof, SCHEMA
from .reddog_parent_consensus_model_evidence import snapshot_model_artifacts, verified_model_evidence
from .reddog_current_effect_reviewer_verification import _RuntimeSnapshot
from .reddog_reviewer_designation_contract import select_reviewer_designation, PARENT_PRIVILEGE
from .reddog_elevated_authority_consensus_evidence import consensus_receipt_matches, author_runtime_evidence_matches
from .reddog_elevated_authority_consensus_reviewer_evidence import consensus_decisions_verify
from .reddog_elevated_authority_consensus_capability import _mint_elevated_authority_consensus_capability
from .reddog_elevated_consensus_signer_reservation import reserve_elevated_consensus_nonce
from .reddog_elevated_authority_consensus_contract import canonical_authority_request_digest, canonical_json_digest, canonical_elevated_signing_request_digest


@dataclass(frozen=True, slots=True)
class CurrentParentConsensusAuthority:
    repo_root: Path
    owner_config_path: Path
    model_artifacts: dict
    proof: object = None

    def __call__(self, parent):
        """Existing resident supplier hook; serialized input is always reverified."""
        from .reddog_signer_delegated_authority_runtime import DelegatedAuthorityRuntimeRequest
        try:
            frozen, _, requested, _ = snapshot_parent_consensus_proof(self.proof)
            if type(parent) is not DelegatedAuthorityRuntimeRequest or requested != parent:
                return None
            return self.prepare(frozen)
        except Exception:
            return None

    def verify(self, proof):
        """Return ordinary checked data only after successful current lease exit."""
        try:
            frozen, _, _, _ = snapshot_parent_consensus_proof(proof)
            models = snapshot_model_artifacts(self.model_artifacts)
            repo = Path(self.repo_root).resolve()
            owner = consent.loader._load_owner_config(self.owner_config_path, repo=repo)
            if owner["schema_version"] not in {consent.loader.SCHEMA_VERSION_V12, consent.loader.SCHEMA_VERSION_V13}:
                return None
            selected, boundary = consent.loader._manifest_selection_from_owner(owner, repo=repo)
            with boundary._lease_current(selected) as selection:
                result = self._verify_leased(owner, repo, selection, frozen, models)
                if frozen != snapshot_parent_consensus_proof(proof)[0] or models != snapshot_model_artifacts(self.model_artifacts):
                    return None
            return result
        except Exception:
            return None

    def prepare(self, proof):
        checked = self.verify(proof)
        if checked is None:
            return None
        frozen, receipt, parent, _, _, expires = checked
        return _mint_elevated_authority_consensus_capability(
            authority_request_digest=canonical_authority_request_digest(parent),
            consensus_receipt_digest=receipt.receipt_id, expires_at=expires,
            authorized_signing_request_digests=frozenset(receipt.context.authorized_signing_request_digests),
            consensus_proof=frozen)

    def reserve(self, proof, *, signing_request_digest, now, grant_expires_at, nonce_authority):
        from .reddog_elevated_authority_consensus_signer_verification import _rehydrate_signing_request, _grant_request_matches
        try:
            if type(proof) is not dict or proof.get("schema_version") != SCHEMA:
                return None
            target = _rehydrate_signing_request(proof["target_signing_request"])
            frozen = {key: value for key, value in proof.items() if key != "target_signing_request"}
            checked = self.verify(frozen)
            if checked is None or not _grant_request_matches(target, proof, signing_request_digest):
                return None
            _, receipt, _, _, _, expires = checked
            if (type(now) is not int or type(grant_expires_at) is not int
                    or not receipt.context.issued_at <= now < grant_expires_at <= expires
                    or canonical_elevated_signing_request_digest(target) not in receipt.context.authorized_signing_request_digests):
                return None
            nonce = canonical_json_digest({"consensus_context": receipt.context.to_dict(), "target": signing_request_digest})
            return reserve_elevated_consensus_nonce(nonce_authority, nonce, expires_at=expires,
                subject="elevated-consensus:" + receipt.receipt_id,
                validity_check=lambda: self.verify(frozen) is not None)
        except Exception:
            return None

    def _verify_leased(self, owner, repo, selection, proof, models):
        frozen, receipt, parent, policy = snapshot_parent_consensus_proof(proof)
        if owner["schema_version"] not in {consent.loader.SCHEMA_VERSION_V12, consent.loader.SCHEMA_VERSION_V13} or selection["owner_config_id"] != owner["config_id"]:
            return None
        owner_before, selection_before = consent.canonical_json(owner), consent.canonical_json(dict(selection))
        started = consent._now_epoch()
        last = [started]
        def clock():
            now = consent._now_epoch()
            if type(now) is not int or type(last[0]) is not int or not 0 <= last[0] <= now:
                raise ValueError("parent_consensus_clock_invalid")
            last[0] = now
            return now
        assertion = frozen["parent_consent"]
        message = consent.canonical_parent_consent_signing_input({k: v for k, v in assertion.items() if k != "signature"})
        before = consent._snapshot(assertion, parent, policy)
        def endorsement():
            return consent._verify_leased(owner, owner_before, self.owner_config_path, repo, selection,
                assertion, assertion, parent, policy, before, message, clock())
        sovereign = endorsement()
        if sovereign is None:
            return None
        records, grants = consent.principals.load_current_generation_principal_artifact(repo_root=repo, selection=selection)
        records_before = consent.canonical_json({key: asdict(value) for key, value in records.items()})
        keys = principals._project_reviewer_keys(authority=owner["parent_reviewer_designation_authority"],
            designation=select_reviewer_designation(grants, PARENT_PRIVILEGE), records=records,
            policy=policy, selection=selection, parent=parent, now=clock(), _parent=True)
        try:
            return self._verify_reviews(owner, repo, selection, frozen, receipt, parent, policy,
                sovereign, records_before, grants, keys, models, clock, endorsement,
                owner_before, selection_before, proof)
        finally:
            keys.close()

    def _verify_reviews(self, owner, repo, selection, frozen, receipt, parent, policy,
                        sovereign, records_before, grants, keys, models, clock, endorsement,
                        owner_before, selection_before, proof):
        author, resolver = verified_model_evidence(owner_path=self.owner_config_path, repo=repo,
            owner_id=owner["config_id"], artifacts=models, clock=clock)
        runtime = _RuntimeSnapshot(resolver)
        now = clock()
        if (not author_runtime_evidence_matches(author, parent, now)
                or not consensus_receipt_matches(receipt, parent, canonical_authority_request_digest(parent),
                    policy, sovereign, now, _parent=True)
                or not consensus_decisions_verify(receipt, parent, consent.Ed25519SignatureVerifier(),
                    keys, runtime, policy, now, frozenset())):
            return None
        expiry = [sovereign.expires_at, author.expires_at, receipt.context.expires_at]
        for decision in receipt.decisions:
            key = keys.resolve(decision.reviewer_principal_id, decision.reviewer_principal_provider)
            expiry.append(key.expires_at)
        expiry.extend(evidence.expires_at for evidence, _ in runtime.records)
        if endorsement() != sovereign:
            return None
        current_records, current_grants = consent.principals.load_current_generation_principal_artifact(repo_root=repo, selection=selection)
        finish = clock()
        if (not runtime.current(finish) or finish >= min(expiry)
                or records_before != consent.canonical_json({key: asdict(value) for key, value in current_records.items()})
                or grants != current_grants or owner_before != consent.canonical_json(owner)
                or selection_before != consent.canonical_json(dict(selection))
                or frozen != snapshot_parent_consensus_proof(proof)[0]):
            return None
        return frozen, receipt, parent, policy, sovereign, min(expiry)
