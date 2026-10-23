"""Bounded exact-effect proof transport and one-use local permission seals.

Wire data is not authority. The independent signer must verify it again.
"""

from copy import deepcopy
import json
import threading
from weakref import WeakKeyDictionary

from .reddog_elevated_authority_consensus_contract import canonical_json_digest
from .reddog_elevated_authority_consensus_effect_context import rehydrate_effect_approval_context
from .reddog_elevated_authority_consensus_rehydration import MAX_CONSENSUS_RECEIPT_BYTES
from .reddog_signer_secret_access_grant_contract import signer_secret_access_request_digest

SCHEMA = "reddog_effect_consensus_proof.v1"
SCHEMA_V2 = "reddog_effect_consensus_proof.v2"
MAX_EFFECT_PROOF_BYTES = 2 * MAX_CONSENSUS_RECEIPT_BYTES
_LOCK = threading.Lock()
_PERMITS = WeakKeyDictionary()


class VerifiedEffectSigningPermit:
    """A process-local seal; construction alone never registers permission."""

    __slots__ = ("__weakref__",)


def build_effect_consensus_proof(*, context, decisions, consent, parent, target, parent_consensus_proof=None):
    proof = {
        "schema_version": SCHEMA,
        "consensus_receipt": {"context": context.to_dict(), "decisions": decisions,
                              "consent": consent},
        "authority_request": parent.to_dict(),
        "target_signing_request": target.to_dict(),
    }
    if parent_consensus_proof is not None:
        from .reddog_parent_consensus_proof import snapshot_parent_consensus_proof
        checked_parent = snapshot_parent_consensus_proof(parent_consensus_proof)[0]
        if canonical_json_digest(checked_parent.pop("authority_request")) != canonical_json_digest(parent.to_dict()):
            raise ValueError("effect_parent_proof_mismatch")
        proof.update(schema_version=SCHEMA_V2, parent_consensus_proof=checked_parent)
    proof["consensus_receipt"]["receipt_id"] = _receipt_id(proof)
    return snapshot_effect_consensus_proof(proof)[0]


def _receipt_id(proof):
    body = deepcopy(proof)
    body["consensus_receipt"].pop("receipt_id", None)
    return canonical_json_digest(body)


def snapshot_effect_consensus_proof(proof):
    """Parse exact bounded wire data; authenticate none of its assertions."""
    from .reddog_elevated_authority_consensus_signer_verification import (
        _rehydrate_authority_request, _rehydrate_signing_request,
    )

    modern = type(proof) is dict and proof.get("schema_version") == SCHEMA_V2
    expected = {"schema_version", "consensus_receipt", "authority_request", "target_signing_request"}
    if modern:
        expected.add("parent_consensus_proof")
    if type(proof) is not dict or set(proof) != expected or proof["schema_version"] not in {SCHEMA, SCHEMA_V2}:
        raise ValueError("effect_signing_proof_schema_invalid")
    encoded = json.dumps(proof, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(encoded.encode("utf-8")) > MAX_EFFECT_PROOF_BYTES:
        raise ValueError("effect_signing_proof_size_invalid")
    frozen = json.loads(encoded)
    receipt = frozen["consensus_receipt"]
    if type(receipt) is not dict or set(receipt) != {"receipt_id", "context", "decisions", "consent"}:
        raise ValueError("effect_signing_receipt_schema_invalid")
    if type(receipt["receipt_id"]) is not str or receipt["receipt_id"] != _receipt_id(frozen):
        raise ValueError("effect_signing_receipt_digest_invalid")
    context = rehydrate_effect_approval_context(receipt["context"])
    parent = _rehydrate_authority_request(frozen["authority_request"])
    target = _rehydrate_signing_request(frozen["target_signing_request"])
    from .reddog_effect_consent_contract import ASSERTION_SCHEMA_V2
    if modern:
        from .reddog_parent_consensus_proof import snapshot_parent_consensus_proof
        _, _, checked_parent, _ = snapshot_parent_consensus_proof(parent_proof_from_effect(frozen))
        if (checked_parent != parent or type(receipt["consent"]) is not dict
                or receipt["consent"].get("schema_version") != ASSERTION_SCHEMA_V2):
            raise ValueError("effect_parent_proof_mismatch")
    elif type(receipt["consent"]) is dict and receipt["consent"].get("schema_version") == ASSERTION_SCHEMA_V2:
        raise ValueError("effect_parent_proof_missing")
    if target.to_dict() != frozen["target_signing_request"] or target.consensus_receipt_digest is not None:
        raise ValueError("effect_signing_target_invalid")
    return frozen, context, parent, target


def _mint_effect_signing_permit(proof, *, expires_at):
    frozen, _, _, target = snapshot_effect_consensus_proof(proof)
    permit = VerifiedEffectSigningPermit()
    with _LOCK:
        _PERMITS[permit] = (signer_secret_access_request_digest(target.to_dict()), expires_at, frozen)
    return permit


def consume_effect_signing_permit(permit, *, signing_request, now, include_expiry=False):
    if type(permit) is not VerifiedEffectSigningPermit or type(now) is not int:
        return None
    try:
        digest = signer_secret_access_request_digest(signing_request.to_dict())
    except Exception:
        return None
    with _LOCK:
        seal = _PERMITS.get(permit)
        if seal is None or not 0 <= now < seal[1] or digest != seal[0]:
            return None
        _PERMITS.pop(permit, None)
        proof = deepcopy(seal[2])
        return (proof, seal[1]) if include_expiry else proof


def discard_effect_signing_permit(permit):
    if type(permit) is VerifiedEffectSigningPermit:
        with _LOCK:
            _PERMITS.pop(permit, None)


def parent_proof_from_effect(proof):
    material = proof["parent_consensus_proof"]
    if type(material) is not dict or "authority_request" in material:
        raise ValueError("effect_parent_proof_duplicate_parent")
    return {**material, "authority_request": proof["authority_request"]}
