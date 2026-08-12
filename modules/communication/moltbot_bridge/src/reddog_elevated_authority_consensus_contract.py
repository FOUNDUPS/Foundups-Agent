"""Canonical signed-review contract for elevated RedDog authority."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping


CONSENSUS_SCHEMA_VERSION = "reddog_elevated_authority_consensus.v1"
DECISION_SCHEMA_VERSION = "reddog_elevated_authority_reviewer_decision.v1"
DECISION_SIGNING_PREFIX = "reddog-elevated-consensus-review.v1"
APPROVE = "APPROVE"


@dataclass(frozen=True)
class ElevatedAuthorityConsensusContext:
    schema_version: str
    authority_request_digest: str
    sovereign_authorization_digest: str
    consensus_policy_digest: str
    authorized_signing_request_digests: tuple[str, ...]
    required_approvals: int
    required_roles: tuple[str, ...]
    nonce: str
    issued_at: int
    expires_at: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["required_roles"] = list(self.required_roles)
        payload["authorized_signing_request_digests"] = list(
            self.authorized_signing_request_digests
        )
        return payload


@dataclass(frozen=True)
class ElevatedAuthorityReviewerDecision:
    schema_version: str
    decision_id: str
    reviewer_principal_id: str
    reviewer_principal_provider: str
    reviewer_public_key: str
    reviewer_key_epoch: str
    reviewer_role: str
    reviewer_model_id: str
    model_selection_receipt_id: str
    model_selection_digest: str
    model_runtime_binding_receipt_id: str
    model_runtime_binding_digest: str
    consensus_context_digest: str
    decision: str
    signature: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ElevatedAuthorityConsensusReceipt:
    schema_version: str
    receipt_id: str
    context: ElevatedAuthorityConsensusContext
    decisions: tuple[ElevatedAuthorityReviewerDecision, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "context": self.context.to_dict(),
            "decisions": [decision.to_dict() for decision in self.decisions],
        }


def canonical_json_digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def canonical_authority_request_digest(request: Any) -> str:
    payload = request.to_dict() if hasattr(request, "to_dict") else request
    if not isinstance(payload, Mapping):
        raise ValueError("elevated_consensus_authority_request_invalid")
    # These two proof identifiers point back to this projection. Their exact
    # values are independently bound by the signed consensus context.
    projected = dict(payload)
    projected.pop("consensus_receipt_digest", None)
    projected.pop("sovereign_authorization_digest", None)
    return canonical_json_digest(projected)


def canonical_elevated_signing_request_digest(request: Any) -> str:
    payload = request.to_dict() if hasattr(request, "to_dict") else request
    if not isinstance(payload, Mapping):
        raise ValueError("elevated_consensus_signing_request_invalid")
    projected = dict(payload)
    projected.pop("consensus_receipt_digest", None)
    projected.pop("elevated_consensus_proof", None)
    signing_input = projected.get("signing_input")
    if type(signing_input) is not str:
        raise ValueError("elevated_consensus_signing_input_invalid")
    marker = signing_input.find(".{")
    if marker <= 0:
        raise ValueError("elevated_consensus_signing_input_invalid")
    prefix, body = signing_input[:marker], signing_input[marker + 1 :]
    parsed = json.loads(body, object_pairs_hook=_reject_duplicate_json_pairs)
    if not isinstance(parsed, dict) or not prefix:
        raise ValueError("elevated_consensus_signing_input_invalid")
    canonical_input = prefix + "." + json.dumps(
        parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )
    if signing_input != canonical_input or projected.get("payload_digest") != (
        canonical_json_digest({"signing_input": signing_input})
    ):
        raise ValueError("elevated_consensus_signing_input_noncanonical")
    embedded_consensus = parsed.get("consensus_receipt_digest")
    request_consensus = payload.get("consensus_receipt_digest")
    if embedded_consensus is not None and embedded_consensus != request_consensus:
        raise ValueError("elevated_consensus_signing_context_mismatch")
    parsed.pop("consensus_receipt_digest", None)
    projected_input = prefix + "." + json.dumps(
        parsed,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    projected["signing_input"] = projected_input
    projected["payload_digest"] = canonical_json_digest(
        {"signing_input": projected_input}
    )
    return canonical_json_digest(projected)


def _reject_duplicate_json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("elevated_consensus_signing_input_duplicate_key")
        result[key] = value
    return result


def canonical_consensus_context_digest(
    context: ElevatedAuthorityConsensusContext,
) -> str:
    return canonical_json_digest(context.to_dict())


def canonical_reviewer_decision_signing_input(
    decision: ElevatedAuthorityReviewerDecision,
) -> str:
    payload = decision.to_dict()
    payload.pop("signature")
    body = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )
    return DECISION_SIGNING_PREFIX + "." + body


def canonical_consensus_receipt_digest(
    receipt: ElevatedAuthorityConsensusReceipt,
) -> str:
    payload = receipt.to_dict()
    payload.pop("receipt_id")
    return canonical_json_digest(payload)


__all__ = [
    "APPROVE", "CONSENSUS_SCHEMA_VERSION", "DECISION_SCHEMA_VERSION",
    "ElevatedAuthorityConsensusContext", "ElevatedAuthorityConsensusReceipt",
    "ElevatedAuthorityReviewerDecision", "canonical_authority_request_digest",
    "canonical_elevated_signing_request_digest",
    "canonical_consensus_context_digest", "canonical_consensus_receipt_digest",
    "canonical_reviewer_decision_signing_input",
]
