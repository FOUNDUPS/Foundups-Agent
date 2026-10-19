"""Project reverified model artifacts using only current protected verifier inputs."""

import json

from . import reddog_model_runtime_verifier_bootstrap as models
from .reddog_elevated_authority_consensus_policy import AuthorRuntimeEvidence
from .reddog_signer_system_service_owner_inputs import load_system_service_model_runtime_verifier
from .reddog_model_verifier_selection_inputs import SelectionReadBudget
from .reddog_runtime_artifact_manifest_contract import digest
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import verification_receipt_digest


def snapshot_model_artifacts(value):
    if type(value) is not dict or set(value) != {"author", "reviewers"}:
        raise ValueError("parent_model_artifacts_invalid")
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    if len(encoded.encode("ascii")) > 1024 * 1024:
        raise ValueError("parent_model_artifacts_too_large")
    frozen = json.loads(encoded)
    reviewers = frozen["reviewers"]
    if type(reviewers) is not dict or not 1 <= len(reviewers) <= 8:
        raise ValueError("parent_model_reviewers_invalid")
    for record in (frozen["author"], *reviewers.values()):
        if (type(record) is not dict or set(record) != {"model_id", "selection", "binding"}
                or type(record["model_id"]) is not str or not record["model_id"]
                or type(record["selection"]) is not dict or type(record["binding"]) is not dict):
            raise ValueError("parent_model_record_invalid")
    return frozen


def verified_model_evidence(*, owner_path, repo, owner_id, artifacts, clock):
    from . import reddog_signer_system_service_manifest_selection_loader as loader
    owner = loader._load_owner_config(owner_path, repo=repo)
    pairs = {(record['selection'].get('receipt_id'), digest(record['selection']))
             for record in (artifacts['author'], *artifacts['reviewers'].values())}
    entries = owner['model_verifier_authority']['entries']
    if (owner['config_id'] != owner_id or len(pairs) != 1 + len(artifacts['reviewers'])
            or pairs != {(entry['selection_receipt_id'], entry['selection_receipt_digest']) for entry in entries}):
        raise ValueError('parent_model_selection_set_mismatch')
    budget = SelectionReadBudget()
    def load(record):
        return load_system_service_model_runtime_verifier(owner_config_path=owner_path,
            repo_root=repo, expected_owner_config_id=owner_id, trusted_now_epoch=clock,
            selection_receipt_id=record['selection']['receipt_id'],
            selection_receipt_digest=digest(record['selection']), _read_budget=budget)
    author = artifacts["author"]
    verifier = load(author)
    receipt = models.verified_runtime_binding_receipt(author["binding"])
    capability = None
    try:
        if receipt is None or author["model_id"] not in receipt.model_ids:
            raise ValueError("parent_author_model_unbound")
        started = clock()
        capability = models.ModelRuntimeBindingUseTimeVerifier.verify(verifier,
            binding=author["binding"], selection=author["selection"])
        verified = models.consume_verified_runtime_binding_capability(capability,
            binding=author["binding"], selection=author["selection"], receipt=receipt)
        finish = clock()
        if (verified is None or type(started) is not int or type(finish) is not int
                or not verified.verified_at <= started <= finish < verified.valid_until):
            raise ValueError("parent_author_model_not_current")
        evidence = AuthorRuntimeEvidence(verified.selection_receipt_id, verified.selection_receipt_digest,
            verified.runtime_binding_receipt_id, verified.runtime_binding_digest,
            verified.receipt_id, verification_receipt_digest(verified), verified.valid_until)
    finally:
        models.discard_verified_runtime_binding_capability(capability)
    records = {identity: models.ReviewerRuntimeArtifacts(record["model_id"], record["selection"],
               record["binding"], load(record)) for identity, record in artifacts["reviewers"].items()}
    return evidence, models.ModelRuntimeReviewerEvidenceResolver(records)
