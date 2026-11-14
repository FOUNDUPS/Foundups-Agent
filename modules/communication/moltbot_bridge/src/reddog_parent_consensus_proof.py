"""Bounded parent proof data; parsing establishes no authority."""

from dataclasses import asdict, fields
import json

from .reddog_elevated_authority_consensus_policy import ElevatedConsensusPolicy, elevated_consensus_policy_valid
from .reddog_elevated_authority_consensus_rehydration import rehydrate_consensus_receipt, MAX_CONSENSUS_RECEIPT_BYTES
from .reddog_parent_consent_contract import validate_parent_consent_assertion

SCHEMA = "reddog_elevated_consensus_proof.v2"
MAX_PARENT_PROOF_BYTES = 2 * MAX_CONSENSUS_RECEIPT_BYTES


def snapshot_parent_consensus_proof(proof):
    from .reddog_elevated_authority_consensus_signer_verification import _rehydrate_authority_request
    names = {"schema_version", "consensus_receipt", "authority_request", "parent_consent", "policy"}
    if type(proof) is not dict or set(proof) != names or proof["schema_version"] != SCHEMA:
        raise ValueError("parent_consensus_proof_shape_invalid")
    encoded = json.dumps(proof, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    if len(encoded.encode("ascii")) > MAX_PARENT_PROOF_BYTES:
        raise ValueError("parent_consensus_proof_size_invalid")
    frozen = json.loads(encoded)
    raw = frozen["policy"]
    if type(raw) is not dict or set(raw) != {field.name for field in fields(ElevatedConsensusPolicy)}:
        raise ValueError("parent_consensus_policy_shape_invalid")
    if (type(raw["reviewer_membership"]) is not list or type(raw["required_roles"]) is not list
            or any(type(row) is not list for row in raw["reviewer_membership"])):
        raise ValueError("parent_consensus_policy_shape_invalid")
    policy = ElevatedConsensusPolicy(**{**raw, "reviewer_membership": tuple(tuple(row) for row in raw["reviewer_membership"]),
                                       "required_roles": tuple(raw["required_roles"])})
    if not elevated_consensus_policy_valid(policy):
        raise ValueError("parent_consensus_policy_invalid")
    validate_parent_consent_assertion(frozen["parent_consent"])
    parent = _rehydrate_authority_request(frozen["authority_request"])
    if json.loads(json.dumps(parent.to_dict(), allow_nan=False)) != frozen["authority_request"]:
        raise ValueError("parent_consensus_request_shape_invalid")
    return frozen, rehydrate_consensus_receipt(frozen["consensus_receipt"]), parent, policy


def build_parent_consensus_proof(*, receipt, parent, assertion, policy):
    return snapshot_parent_consensus_proof(dict(schema_version=SCHEMA,
        consensus_receipt=receipt.to_dict(), authority_request=parent.to_dict(),
        parent_consent=assertion, policy=asdict(policy)))[0]
