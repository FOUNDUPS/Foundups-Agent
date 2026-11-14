"""Join parent and exact-effect consent under the caller's one current lease."""

from pathlib import Path

from . import reddog_current_effect_signing_authority as effects
from .reddog_current_parent_consensus_authority import CurrentParentConsensusAuthority
from .reddog_parent_consensus_model_evidence import snapshot_model_artifacts, verified_model_evidence
from .reddog_runtime_artifact_manifest_contract import canonical_json
from .reddog_effect_consensus_proof import parent_proof_from_effect


def verify_parent_bound_effect_leased(authority, owner, repo, selection, proof, context, parent, target):
    current = authority.parent_authority
    if (type(current) is not CurrentParentConsensusAuthority
            or Path(current.repo_root).resolve() != repo
            or Path(current.owner_config_path).resolve() != Path(authority.owner_config_path).resolve()):
        return None
    models = snapshot_model_artifacts(current.model_artifacts)
    owner_before, selection_before, proof_before = canonical_json(owner), canonical_json(dict(selection)), canonical_json(proof)
    started = effects._now_epoch()
    checked = current._verify_leased(owner, repo, selection, parent_proof_from_effect(proof), models)
    if checked is None or checked[2] != parent:
        return None
    _, _, _, policy, sovereign, parent_expiry = checked
    author, runtime = verified_model_evidence(owner_path=authority.owner_config_path, repo=repo,
        owner_id=owner["config_id"], artifacts=models, clock=effects._now_epoch)
    if not effects.author_runtime_evidence_matches(author, parent, started):
        return None
    inputs = dict(context=context, target=target, expected_target=target.to_dict(), policy=policy, parent=parent)
    assertion = proof["consensus_receipt"]["consent"]
    evidence = effects._consent_leased(authority, owner, repo, selection, assertion, inputs, effects._now_epoch())
    if evidence is None or evidence.parent_authorization != sovereign:
        return None
    reviews = dict(context=context, target=target, expected_target=target.to_dict(), policy=policy,
        authority_request=parent, decisions=proof["consensus_receipt"]["decisions"],
        runtime_evidence_resolver=runtime, revoked_key_epochs=frozenset())
    expires = [parent_expiry, context.expires_at, evidence.expires_at, author.expires_at]
    if effects.reviews._verify_leased(owner, authority.owner_config_path, repo, selection,
            reviews, effects.reviews._input_snapshot(reviews), valid_until=expires) is not True:
        return None
    final = current._verify_leased(owner, repo, selection, parent_proof_from_effect(proof), models)
    finish = effects._now_epoch()
    if (final is None or final[4] != sovereign or type(started) is not int or type(finish) is not int
            or not 0 <= started <= finish < min(expires) or owner_before != canonical_json(owner)
            or selection_before != canonical_json(dict(selection)) or proof_before != canonical_json(proof)
            or models != snapshot_model_artifacts(current.model_artifacts)):
        return None
    # A later nonce commit re-enters the owner, rereads protected artifacts and
    # performs actual signatures/model verification; no released lease is reused.
    return started, min(expires), lambda: authority._verify(proof, _final_use=True) is not None
