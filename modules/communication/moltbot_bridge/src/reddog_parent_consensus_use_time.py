"""Current parent audit binding for the existing valve; never an effect grant."""

from dataclasses import dataclass
from pathlib import Path

from .reddog_current_parent_consensus_authority import CurrentParentConsensusAuthority
from .reddog_parent_consensus_proof import snapshot_parent_consensus_proof
from .reddog_runtime_artifact_manifest_contract import digest
from .reddog_work_order_binding import canonical_full_work_order_digest


@dataclass(frozen=True, slots=True)
class ParentConsensusUseTimeEvidence:
    authority: object
    proof: dict
    generation_binding: object
    observation_clock: object

    def matches(self, identity, work_authority, work_order):
        return verify_parent_use_time(self.authority, self.proof, self.generation_binding,
                                      identity, work_authority, work_order, self.observation_clock)


def verify_parent_use_time(authority, proof, binding, identity, work_authority, work_order, clock):
    from .reddog_signer_current_generation_runtime_binding import SignerCurrentGenerationRuntimeBinding
    from .reddog_signer_current_generation_use_time_gate import _generation_fresh
    from .reddog_current_parent_consent_verification import _now_epoch
    try:
        if (type(authority) is not CurrentParentConsensusAuthority
                or type(binding) is not SignerCurrentGenerationRuntimeBinding or binding.accepted is not True
                or any(type(value) is not dict for value in (identity, work_authority, work_order))):
            return False
        started = _now_epoch()
        observed_start = clock()
        inputs = digest(dict(identity=identity, authority=work_authority, work=work_order))
        frozen, _, parent, _ = snapshot_parent_consensus_proof(proof)
        if not _work_matches(authority, parent, binding, identity, work_authority, work_order):
            return False
        checked = authority.verify(frozen)
        if checked is None:
            return False
        assertion = checked[0]['parent_consent']
        finished = _now_epoch()
        observed_end = clock()
        fields = ('manifest_id', 'artifact_generation_digest', 'generation',
                  'generation_revision', 'owner_config_id', 'config_digest')
        return (type(started) is int and type(finished) is int and 0 <= started <= finished
                and type(observed_start) is int and type(observed_end) is int
                and 0 <= observed_start <= observed_end and _generation_fresh(binding, observed_end)
                and _generation_fresh(binding, finished)
                and all(assertion[field] == getattr(binding, field) for field in fields)
                and frozen == snapshot_parent_consensus_proof(proof)[0]
                and inputs == digest(dict(identity=identity, authority=work_authority, work=work_order)))
    except Exception:
        return False


def _work_matches(authority, parent, binding, identity, work_authority, work):
    from .reddog_delegated_authority_signing_plan import _workauth_signing_material
    from .reddog_signer_current_generation_runtime_binding import _digest as binding_digest
    expected, _ = _workauth_signing_material(parent, 'HIGH', True)
    received = {key: value for key, value in work_authority.items() if key not in {'signature', 'receipt_chain'}}
    expected.pop('receipt_chain', None)
    identity_fields = ('principal_id', 'principal_provider', 'principal_public_key',
                       'reddog_id', 'reddog_public_key', 'identity_nonce', 'issued_at')
    pair = authority.model_artifacts['author']
    model_pair = dict(model_selection_receipt=pair['selection'], model_runtime_binding_receipt=pair['binding'])
    return (received == expected and identity.get('expires_at') == parent.identity_expires_at
            and all(identity.get(name) == getattr(parent, name) for name in identity_fields)
            and binding.principal_binding_digest == binding_digest(dict(identity=identity, work_authority=work_authority))
            and binding.model_artifact_pair_digest == binding_digest(model_pair)
            and parent.work_order_digest == binding.model_work_order_digest == canonical_full_work_order_digest(work)
            and work.get('work_order_id') == parent.work_order_id)


def collect_parent_use_time(authority, binding, identity, work_authority, work_order, *, repo_root, clock):
    try:
        if type(authority) is not CurrentParentConsensusAuthority or Path(authority.repo_root).resolve() != Path(repo_root).resolve():
            return None
        frozen = snapshot_parent_consensus_proof(authority.proof)[0]
        evidence = ParentConsensusUseTimeEvidence(authority, frozen, binding, clock)
        return evidence if evidence.matches(identity, work_authority, work_order) else None
    except Exception:
        return None
