"""Strict rehydration for elevated-authority consensus wire receipts."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_contract import (
    CONSENSUS_SCHEMA_VERSION,
    DECISION_SCHEMA_VERSION,
    ElevatedAuthorityConsensusContext,
    ElevatedAuthorityConsensusReceipt,
    ElevatedAuthorityReviewerDecision,
)

MAX_CONSENSUS_RECEIPT_BYTES = 8192
MAX_CONSENSUS_DECISIONS = 8
MAX_CONSENSUS_TEXT_CHARS = 4096


def rehydrate_consensus_receipt(
    value: Mapping[str, Any],
) -> ElevatedAuthorityConsensusReceipt:
    if not isinstance(value, Mapping) or not _bounded_wire_value(value):
        raise ValueError("elevated_consensus_receipt_size_invalid")
    if set(value) != {"schema_version", "receipt_id", "context", "decisions"}:
        raise ValueError("elevated_consensus_receipt_schema_invalid")
    context = _rehydrate_context(value.get("context"))
    raw_decisions = value.get("decisions")
    if (
        not isinstance(raw_decisions, Sequence)
        or isinstance(raw_decisions, (str, bytes))
        or not 1 <= len(raw_decisions) <= MAX_CONSENSUS_DECISIONS
    ):
        raise ValueError("elevated_consensus_decisions_invalid")
    receipt = ElevatedAuthorityConsensusReceipt(
        schema_version=_text(value, "schema_version"),
        receipt_id=_text(value, "receipt_id"),
        context=context,
        decisions=tuple(_rehydrate_decision(item) for item in raw_decisions),
    )
    if receipt.schema_version != CONSENSUS_SCHEMA_VERSION:
        raise ValueError("elevated_consensus_receipt_schema_invalid")
    if not _sha256_digest(receipt.receipt_id):
        raise ValueError("elevated_consensus_receipt_id_invalid")
    if not _ascii_deep(receipt.to_dict()):
        raise ValueError("elevated_consensus_receipt_non_ascii")
    return receipt


def _rehydrate_context(value: Any) -> ElevatedAuthorityConsensusContext:
    fields = set(ElevatedAuthorityConsensusContext.__dataclass_fields__)
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError("elevated_consensus_context_schema_invalid")
    roles = value.get("required_roles")
    signing_digests = value.get("authorized_signing_request_digests")
    if (
        not isinstance(roles, list)
        or not 1 <= len(roles) <= MAX_CONSENSUS_DECISIONS
        or any(not _bounded_text(role) for role in roles)
    ):
        raise ValueError("elevated_consensus_roles_invalid")
    if (
        not isinstance(signing_digests, list)
        or len(signing_digests) != 2
        or len(set(signing_digests)) != 2
        or any(not _sha256_digest(item) for item in signing_digests)
    ):
        raise ValueError("elevated_consensus_signing_digests_invalid")
    context = ElevatedAuthorityConsensusContext(
        schema_version=_text(value, "schema_version"),
        authority_request_digest=_text(value, "authority_request_digest"),
        sovereign_authorization_digest=_text(value, "sovereign_authorization_digest"),
        consensus_policy_digest=_text(value, "consensus_policy_digest"),
        authorized_signing_request_digests=tuple(signing_digests),
        required_approvals=_integer(value, "required_approvals"),
        required_roles=tuple(roles),
        nonce=_text(value, "nonce"),
        issued_at=_integer(value, "issued_at"),
        expires_at=_integer(value, "expires_at"),
    )
    if any(
        not _sha256_digest(item)
        for item in (
            context.authority_request_digest,
            context.sovereign_authorization_digest,
            context.consensus_policy_digest,
        )
    ) or not 0 <= context.issued_at < context.expires_at:
        raise ValueError("elevated_consensus_context_value_invalid")
    return context


def _rehydrate_decision(value: Any) -> ElevatedAuthorityReviewerDecision:
    fields = set(ElevatedAuthorityReviewerDecision.__dataclass_fields__)
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError("elevated_consensus_decision_schema_invalid")
    if any(not _bounded_text(value[field]) for field in fields):
        raise ValueError("elevated_consensus_decision_field_invalid")
    decision = ElevatedAuthorityReviewerDecision(**dict(value))
    if decision.schema_version != DECISION_SCHEMA_VERSION:
        raise ValueError("elevated_consensus_decision_schema_invalid")
    if any(
        not _sha256_digest(item)
        for item in (
            decision.consensus_context_digest,
            decision.model_selection_digest,
            decision.model_runtime_binding_digest,
        )
    ):
        raise ValueError("elevated_consensus_decision_digest_invalid")
    return decision


def _text(value: Mapping[str, Any], field: str) -> str:
    item = value.get(field)
    if not _bounded_text(item):
        raise ValueError(f"elevated_consensus_{field}_invalid")
    return item


def _integer(value: Mapping[str, Any], field: str) -> int:
    item = value.get(field)
    if type(item) is not int:
        raise ValueError(f"elevated_consensus_{field}_invalid")
    return item


def _ascii_deep(value: Any) -> bool:
    if isinstance(value, str):
        return value.isascii()
    if isinstance(value, Mapping):
        return all(
            isinstance(key, str) and key.isascii() and _ascii_deep(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return all(_ascii_deep(item) for item in value)
    return value is None or type(value) in {bool, int}


def _sha256_digest(value: Any) -> bool:
    return bool(
        type(value) is str
        and len(value) == 71
        and value.startswith("sha256:")
        and all(char in "0123456789abcdef" for char in value[7:])
    )


def _bounded_text(value: Any) -> bool:
    return bool(
        type(value) is str
        and value
        and len(value) <= MAX_CONSENSUS_TEXT_CHARS
        and value.isascii()
    )


def _bounded_wire_value(value: Mapping[str, Any]) -> bool:
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError):
        return False
    return len(encoded) <= MAX_CONSENSUS_RECEIPT_BYTES


__all__ = ["rehydrate_consensus_receipt"]
