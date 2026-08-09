"""Canonical wire validation for delegated-authority signer requests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import fields
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    DelegatedAuthorityRuntimeRequest,
)

_REQUEST_FIELDS = frozenset(
    field.name for field in fields(DelegatedAuthorityRuntimeRequest)
)
_SEQUENCE_FIELDS = frozenset({"allowed_paths", "denied_paths"})
_MAPPING_FIELDS = frozenset(
    {"progressive_policy_stage_receipt", "wsp15_allocation_receipt"}
)
_INTEGER_FIELDS = frozenset(
    {"wsp15_mps_total", "issued_at", "identity_expires_at", "work_authority_expires_at"}
)
_OPTIONAL_FIELDS = frozenset(
    field.name
    for field in fields(DelegatedAuthorityRuntimeRequest)
    if field.default is None
)


def rehydrate_delegated_authority_request(
    payload: Mapping[str, Any],
) -> DelegatedAuthorityRuntimeRequest:
    """Validate the exact signer-request wire schema before reconstructing it."""

    if set(payload) != _REQUEST_FIELDS:
        raise ValueError("delegated authority request schema mismatch")
    values = dict(payload)
    for name in _SEQUENCE_FIELDS:
        value = values[name]
        if not isinstance(value, (list, tuple)) or any(
            not isinstance(item, str) or not item for item in value
        ):
            raise ValueError(f"invalid delegated authority request field: {name}")
        values[name] = tuple(value)
    for name in _INTEGER_FIELDS:
        if type(values[name]) is not int:
            raise ValueError(f"invalid delegated authority request field: {name}")
    for name in _MAPPING_FIELDS:
        if not isinstance(values[name], Mapping) or not values[name]:
            raise ValueError(f"invalid delegated authority request field: {name}")
        values[name] = dict(values[name])
    for name in _OPTIONAL_FIELDS:
        if values[name] is not None and (
            not isinstance(values[name], str) or not values[name]
        ):
            raise ValueError(f"invalid delegated authority request field: {name}")
    text_fields = (
        _REQUEST_FIELDS - _SEQUENCE_FIELDS - _MAPPING_FIELDS - _INTEGER_FIELDS
        - _OPTIONAL_FIELDS
    )
    for name in text_fields:
        if not isinstance(values[name], str) or not values[name]:
            raise ValueError(f"invalid delegated authority request field: {name}")
    return DelegatedAuthorityRuntimeRequest(**values)


def canonical_delegated_authority_request_digest(
    payload: Mapping[str, Any],
) -> str:
    """Digest an exact, typed signer request using the dry-run wire encoding."""

    normalized = rehydrate_delegated_authority_request(payload).to_dict()
    encoded = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


__all__ = [
    "canonical_delegated_authority_request_digest",
    "rehydrate_delegated_authority_request",
]
