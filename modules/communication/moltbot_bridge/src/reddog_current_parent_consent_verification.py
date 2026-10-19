"""Authenticate one detached parent endorsement, without issuing any authority."""

from dataclasses import asdict
from pathlib import Path
import time

from . import reddog_signer_system_service_manifest_selection_loader as loader
from . import reddog_signer_owner_e0_principal_authority as principals
from .reddog_parent_consent_contract import (
    COMMON_FIELDS, CURRENT_FIELDS, validate_parent_consent_assertion,
    validate_parent_consent_authority, canonical_parent_consent_signing_input,
    parent_consent_authority_digest, ParentConsentEvidence,
)
from .reddog_ed25519_signature_verifier_backend import Ed25519SignatureVerifier
from .reddog_runtime_artifact_manifest_contract import canonical_json, raw_digest, is_sha256
from .reddog_elevated_authority_consensus_contract import canonical_authority_request_digest
from .reddog_elevated_authority_consensus_policy import ElevatedConsensusPolicy, elevated_consensus_policy_valid


def _now_epoch():
    return int(time.time())


def _snapshot(assertion, parent, policy):
    from .reddog_signer_delegated_authority_runtime import DelegatedAuthorityRuntimeRequest
    if type(parent) is not DelegatedAuthorityRuntimeRequest or type(policy) is not ElevatedConsensusPolicy:
        raise ValueError("parent_consent_request_type_invalid")
    return canonical_json({"assertion": validate_parent_consent_assertion(assertion),
                           "parent": parent.to_dict(), "policy": asdict(policy)})


def resolve_current_parent_sovereign_authorization(*, owner_config_path, repo_root, assertion, parent, policy):
    """Return ordinary evidence only after a current lease exits successfully.

    No callback, trusted key, clock or selected generation is caller supplied.
    Registration withdrawal/rotation revokes future resolutions; this is not a
    per-assertion revocation store or a substitute for downstream final-use gates.
    """
    try:
        before = _snapshot(assertion, parent, policy)
        checked = validate_parent_consent_assertion(assertion)
        body = {key: value for key, value in checked.items() if key != "signature"}
        message = canonical_parent_consent_signing_input(body)
        started = _now_epoch()
        if type(started) is not int or started < 0:
            return None
        repo = Path(repo_root).resolve()
        owner = loader._load_owner_config(owner_config_path, repo=repo)
        if owner["schema_version"] != loader.SCHEMA_VERSION_V11:
            return None
        owner_before = canonical_json(owner)
        selected, boundary = loader._manifest_selection_from_owner(owner, repo=repo)
        with boundary._lease_current(selected) as selection:
            result = _verify_leased(owner, owner_before, owner_config_path, repo, selection,
                                    checked, assertion, parent, policy, before, message, started)
        return result
    except Exception:
        return None


def _scope_matches(authority, assertion, parent, selection):
    shared = COMMON_FIELDS - {"schema_version", "issued_at", "expires_at"}
    bindings = {"beneficiary_principal_id": parent.principal_id,
        "beneficiary_principal_provider": parent.principal_provider,
        "beneficiary_public_key": parent.principal_public_key,
        "reddog_id": parent.reddog_id, "reddog_public_key": parent.reddog_public_key,
        "reddog_key_epoch": parent.key_epoch, "repo_full_name": parent.repo_full_name,
        "foundup_id": parent.foundup_id, "requested_operation": parent.requested_operation}
    return (all(authority[key] == assertion[key] for key in shared)
            and all(authority[key] == value for key, value in bindings.items())
            and assertion["owner_authority_digest"] == parent_consent_authority_digest(authority)
            and assertion["authority_request_digest"] == canonical_authority_request_digest(parent)
            and all(type(selection[key]) is type(assertion[key])
                    and selection[key] == assertion[key] for key in CURRENT_FIELDS))


def _records_snapshot(authority, records):
    values = {}
    for role in ("issuer", "beneficiary"):
        identity, provider = authority[role + "_principal_id"], authority[role + "_principal_provider"]
        record = records.get(provider + "|" + identity)
        key = authority[role + "_public_key"]
        if (record is None or record.principal_id != identity or record.principal_provider != provider
                or record.principal_public_key != key or authority["repo_full_name"] not in record.repo_scope
                or authority["foundup_id"] not in record.foundup_scope):
            raise ValueError("parent_consent_principal_binding_invalid")
        values[role] = asdict(record)
    return canonical_json(values)


def _current(authority, assertion, parent, policy, selection, now):
    from .reddog_signer_delegated_authority_runtime import delegated_authority_tier
    times = (parent.issued_at, parent.identity_expires_at, parent.work_authority_expires_at,
             selection["selection_issued_at"], selection["selection_expires_at"], selection["manifest_expires_at"])
    if type(now) is not int or any(type(value) is not int or not 0 <= value <= 2**63 - 1 for value in times):
        return False
    return (elevated_consensus_policy_valid(policy)
            and policy.policy_digest == authority["policy_digest"] == assertion["policy_digest"]
            and delegated_authority_tier(parent) == "HIGH"
            and type(parent.work_order_id) is str and 0 < len(parent.work_order_id) <= 256
            and parent.work_order_id.isascii() and bool(parent.work_order_id.strip())
            and is_sha256(parent.work_order_digest)
            and max(parent.issued_at, selection["selection_issued_at"]) <= assertion["issued_at"]
            and authority["issued_at"] <= assertion["issued_at"] <= now < assertion["expires_at"]
            <= min(authority["expires_at"], *times[1:3], *times[4:])
            and _scope_matches(authority, assertion, parent, selection))


def _evidence(assertion, parent, message):
    fields = ("principal_id", "principal_provider", "principal_public_key", "reddog_id",
              "reddog_public_key", "repo_full_name", "foundup_id", "work_order_id", "key_epoch")
    return ParentConsentEvidence(
        authorization_digest=raw_digest(message.encode("ascii")),
        authority_request_digest=assertion["authority_request_digest"],
        expires_at=assertion["expires_at"], consensus_policy_digest=assertion["policy_digest"],
        **{key: getattr(parent, key) for key in fields})


def _verify_leased(owner, owner_before, path, repo, selection, checked, assertion, parent, policy, before, message, started):
    authority = validate_parent_consent_authority(owner["parent_consent_authority"])
    if selection["owner_config_id"] != owner["config_id"]:
        return None
    selected_before = canonical_json(dict(selection))
    records, _ = principals.load_current_generation_principal_artifact(repo_root=repo, selection=selection)
    records_before = _records_snapshot(authority, records)
    if not _current(authority, checked, parent, policy, selection, started):
        return None
    if Ed25519SignatureVerifier().verify(authority["issuer_public_key"], message, checked["signature"]) is not True:
        return None
    current_owner = loader._load_owner_config(path, repo=repo)
    current_records, _ = principals.load_current_generation_principal_artifact(repo_root=repo, selection=selection)
    finish = _now_epoch()
    if (type(finish) is not int or finish < started or canonical_json(current_owner) != owner_before
            or canonical_json(owner) != owner_before or before != _snapshot(assertion, parent, policy)
            or selected_before != canonical_json(dict(selection))
            or records_before != _records_snapshot(authority, records)
            or records_before != _records_snapshot(authority, current_records)
            or not _current(authority, checked, parent, policy, selection, finish)):
        return None
    return _evidence(checked, parent, message)
