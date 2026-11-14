"""Disposable independent designation fixtures; no operational keys or authority."""

import base64
from copy import deepcopy
import hashlib
import importlib
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


PREFIX = "reddog-reviewer-designation.v1."
ROOT = "modules.communication.moltbot_bridge.src."


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest(value):
    return "sha256:" + hashlib.sha256(canonical(value).encode("ascii")).hexdigest()


def wire(prefix, raw):
    return prefix + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def public(key):
    return wire("ed25519-pub-v1:", key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw))


def sign(value, key, prefix=PREFIX):
    preimage = prefix + canonical({k: v for k, v in value.items() if k != "signature"})
    value["signature"] = wire("ed25519-sig-v1:", key.sign(preimage.encode("ascii")))
    return preimage


def fixture():
    issuer, reviewer = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    authority = dict(schema_version="reddog_reviewer_designation_authority.v1",
        privilege="designate_effect_reviewers", issuer_principal_id="issuer:test",
        issuer_principal_provider="test", issuer_public_key=public(issuer), issuer_key_epoch="issuer-1",
        repo_full_name="test/repo", foundup_id="test-foundup", policy_digest="sha256:" + "a" * 64,
        decision_schema_version="reddog_effect_reviewer_decision.v1", issued_at=900, expires_at=1100)
    entry = dict(principal_id="reviewer:test", principal_provider="test", public_key=public(reviewer),
        key_epoch="reviewer-epoch", authorized_roles=["critic"], issued_at=950, expires_at=1080)
    designation = {k: v for k, v in authority.items() if k != "issuer_public_key"}
    designation.update(schema_version="reddog_reviewer_designation.v1", owner_authority_digest=digest(authority),
        reviewers=[entry], issued_at=920, expires_at=1090, signature="")
    sign(designation, issuer)
    return authority, designation, issuer, reviewer


def contract():
    name = ROOT + "reddog_reviewer_designation_contract"
    assert importlib.util.find_spec(name) is not None, "reviewer_designation_contract_missing"
    return importlib.import_module(name)


def artifact(authority, designation):
    entry = designation["reviewers"][0]
    record = dict(principal_id=entry["principal_id"], principal_provider=entry["principal_provider"],
        principal_public_key=entry["public_key"], repo_scope=[authority["repo_full_name"]],
        foundup_scope=[authority["foundup_id"]], verified_subject_digest="sha256:" + "b" * 64,
        reward_account=None, owner_dae=None, principal_wallet=None)
    return dict(schema_version="reddog_authority_runtime_resolver_supply.v2",
        principals={"test|reviewer:test": record}, principal_count=1,
        resolver_supply_receipt_id="sha256:" + "c" * 64, no_holoindex_reindex_performed=True,
        reviewer_authorizations=[deepcopy(designation)])
