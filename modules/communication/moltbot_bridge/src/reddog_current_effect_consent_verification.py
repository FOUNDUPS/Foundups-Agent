"""Authenticate detached exact-effect consent under one current owner lease.

The returned record is data, not an execution permit or parent authority.
"""

from dataclasses import asdict
from pathlib import Path
import time

from . import reddog_signer_system_service_manifest_selection_loader as loader
from . import reddog_signer_owner_e0_principal_authority as principals
from .reddog_effect_consent_contract import (
    validate_effect_consent_assertion, validate_effect_consent_authority,
    canonical_effect_consent_signing_input, effect_consent_authority_digest,
)
from .reddog_ed25519_signature_verifier_backend import Ed25519SignatureVerifier
from .reddog_runtime_artifact_manifest_contract import canonical_json, raw_digest
from .reddog_elevated_authority_consensus_policy import (
    EffectSovereignAuthorizationEvidence, SovereignAuthorizationEvidence,
)
from .reddog_elevated_authority_consensus_evidence import effect_sovereign_authorization_matches
from .reddog_authoritative_use_lease_contract import validate_authoritative_use_lease_request


def _now_epoch():
    return int(time.time())


def resolve_current_effect_sovereign_authorization(
    *, owner_config_path, repo_root, assertion, context, parent, target, expected_target, policy,
):
    """Authenticate endorsement of one exact effect; ordinary failures return None."""
    try:
        checked = validate_effect_consent_assertion(assertion)
        message = canonical_effect_consent_signing_input({k: v for k, v in checked.items() if k != "signature"})
        evidence = _evidence(checked, message)
        inputs = dict(context=context, parent=parent, target=target, expected_target=expected_target, policy=policy)
        before = _snapshot(assertion, inputs)
        now = _now_epoch()
        if not effect_sovereign_authorization_matches(evidence, **inputs, now=now):
            return None
        repo = Path(repo_root).resolve()
        owner = loader._load_owner_config(owner_config_path, repo=repo)
        if owner["schema_version"] not in {loader.SCHEMA_VERSION_V6, loader.SCHEMA_VERSION_V7}:
            return None
        selected, boundary = loader._manifest_selection_from_owner(owner, repo=repo)
        with boundary._lease_current(selected) as selection:
            if selection["owner_config_id"] != owner["config_id"]:
                return None
            result = _verify_leased(owner, owner_config_path, repo, selection, checked,
                                    assertion, inputs, before, evidence, message, now)
        return result
    except Exception:
        return None


def _snapshot(assertion, inputs):
    from .reddog_signer_delegated_authority_runtime import DelegatedAuthorityRuntimeRequest, SigningRequest
    from .reddog_elevated_authority_consensus_effect_context import EffectApprovalContext
    from .reddog_elevated_authority_consensus_policy import ElevatedConsensusPolicy

    types = {"parent": DelegatedAuthorityRuntimeRequest, "target": SigningRequest,
             "context": EffectApprovalContext, "policy": ElevatedConsensusPolicy, "expected_target": dict}
    if any(type(inputs[name]) is not kind for name, kind in types.items()):
        raise ValueError("effect_consent_input_type_invalid")
    return canonical_json({"assertion": validate_effect_consent_assertion(assertion),
        "context": inputs["context"].to_dict(), "parent": inputs["parent"].to_dict(),
        "target": asdict(inputs["target"]), "expected_target": inputs["expected_target"],
        "policy": asdict(inputs["policy"])})


def _evidence(assertion, message):
    return EffectSovereignAuthorizationEvidence(
        authorization_digest=raw_digest(message.encode("ascii")),
        parent_authorization=SovereignAuthorizationEvidence(**assertion["parent_authorization"]),
        parent_authority_request_digest=assertion["parent_authority_request_digest"],
        target_signing_request_digest=assertion["target_signing_request_digest"],
        effect_request_digest=assertion["effect_request_digest"],
        consensus_policy_digest=assertion["policy_digest"],
        issued_at=assertion["issued_at"], expires_at=assertion["expires_at"],
    )


def _scope_matches(authority, assertion, inputs, payload, selection):
    shared = set(authority) - {"schema_version", "issuer_public_key", "issued_at", "expires_at"}
    if any(authority[key] != assertion[key] for key in shared):
        return False
    parent, target = inputs["parent"], inputs["target"]
    expected = {
        "repo_full_name": parent.repo_full_name, "foundup_id": parent.foundup_id,
        "policy_digest": inputs["policy"].policy_digest, "reddog_id": parent.reddog_id,
        "requester_principal_id": target.requester_principal_id,
        "beneficiary_principal_id": parent.principal_id,
        "beneficiary_principal_provider": parent.principal_provider,
        "target_signer_profile_id": payload["signer_profile_id"],
        "target_signer_public_key": target.signer_public_key, "target_signer_key_epoch": target.key_epoch,
    }
    current = ("manifest_id", "artifact_generation_digest", "generation",
               "generation_revision", "owner_config_id", "config_digest")
    return (assertion["owner_authority_digest"] == effect_consent_authority_digest(authority)
            and all(authority[key] == value for key, value in expected.items())
            and all(payload[key] == selection[key] for key in current)
            and payload["signer_public_key"] == target.signer_public_key
            and payload["key_epoch"] == target.key_epoch)


def _records_match(authority, records, parent):
    requester = [record for record in records.values()
                 if record.principal_id == authority["requester_principal_id"]]
    if len(requester) != 1:
        return False
    for role, key in (("issuer", authority["issuer_public_key"]),
                      ("requester", None), ("beneficiary", parent.principal_public_key)):
        identity, provider = authority[role + "_principal_id"], authority[role + "_principal_provider"]
        record = records.get(provider + "|" + identity)
        if (record is None or record.principal_id != identity or record.principal_provider != provider
                or (key is not None and record.principal_public_key != key)
                or authority["repo_full_name"] not in record.repo_scope
                or authority["foundup_id"] not in record.foundup_scope):
            return False
    return True


def _records_snapshot(authority, records):
    return canonical_json({role: asdict(records[
        authority[role + "_principal_provider"] + "|" + authority[role + "_principal_id"]
    ]) for role in ("issuer", "requester", "beneficiary")})


def _effect_consent_interval_matches(authority, assertion, context, parent, payload, selection, now) -> bool:
    return (0 <= authority['issued_at'] <= assertion['issued_at'] <= context.issued_at <= now
            < context.expires_at <= assertion['expires_at'] <= min(authority['expires_at'],
                selection['manifest_expires_at'], selection['selection_expires_at'],
                assertion['parent_authorization']['expires_at'], parent.identity_expires_at,
                parent.work_authority_expires_at, payload['expires_at'])) and (0 <= selection['selection_issued_at'] <= now)


def _current(authority, assertion, evidence, inputs, selection, records, now):
    times = [selection[k] for k in ("manifest_expires_at", "selection_expires_at", "selection_issued_at")]
    if type(now) is not int or any(type(value) is not int or value < 0 for value in times):
        return False
    payload = validate_authoritative_use_lease_request(inputs["target"], now_epoch=now)
    return (payload is not None and _scope_matches(authority, assertion, inputs, payload, selection)
            and _records_match(authority, records, inputs["parent"])
            and _effect_consent_interval_matches(authority, assertion, inputs["context"], inputs["parent"], payload, selection, now)
            and effect_sovereign_authorization_matches(evidence, **inputs, now=now))


def _verify_leased(owner, owner_path, repo, selection, checked, assertion, inputs, before, evidence, message, now):
    """Private already-leased check, for future composition under the same owner."""
    authority = validate_effect_consent_authority(owner["effect_consent_authority"])
    selected_before = canonical_json(dict(selection))
    records, _ = principals.load_current_generation_principal_artifact(repo_root=repo, selection=selection)
    try:
        if not _current(authority, checked, evidence, inputs, selection, records, now):
            return None
        records_before = _records_snapshot(authority, records)
        if Ed25519SignatureVerifier().verify(authority["issuer_public_key"], message, checked["signature"]) is not True:
            return None
        current_owner = loader._load_owner_config(owner_path, repo=repo)
        finish = _now_epoch()
        if (type(finish) is not int or finish < now or current_owner != owner
                or before != _snapshot(assertion, inputs)
                or selected_before != canonical_json(dict(selection))
                or records_before != _records_snapshot(authority, records)
                or not _current(authority, checked, evidence, inputs, selection, records, finish)):
            return None
        return evidence
    finally:
        authority.clear()
