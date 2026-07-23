# -*- coding: utf-8 -*-
"""Strict JSON schema boundary for supplied model runtime binding receipts."""

from __future__ import annotations

import json
import math
from typing import Any, Mapping, Optional


_BINDING_FIELDS = {
    "schema_version",
    "receipt_id",
    "decision",
    "runtime_surface",
    "catalog_snapshot_id",
    "selection_receipt_id",
    "task_family",
    "principal_model",
    "panel_models",
    "role_bindings",
    "benchmark_evidence_receipt_ids",
    "promotion_evidence_receipt_ids",
    "signed_promotion_receipt_ids",
    "policy",
    "rejection_reasons",
}
_POLICY_FIELDS = {
    "schema_version",
    "task_family",
    "runtime_surface",
    "min_verifier_pass_rate",
    "required_task_set_digest",
    "required_held_out_split_digest",
    "required_verifier_digest",
    "max_panel_models",
    "required_panel_topology_digest",
    "authority_receipt_id",
}
_ROLE_BINDING_FIELDS = {"role", "model_id", "provider"}


def normalize_exact_binding_receipt(
    value: Any,
) -> Optional[dict[str, Any]]:
    """Return detached JSON only when every nested schema is exact."""
    try:
        if not isinstance(value, Mapping):
            return None
        value.get("schema_version")
        receipt = _canonical_json_value(value)
        json.dumps(
            receipt,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        if not isinstance(receipt, dict):
            return None
        policy = receipt.get("policy")
        roles = receipt.get("role_bindings")
        exact = bool(
            set(receipt) == _BINDING_FIELDS
            and isinstance(policy, dict)
            and set(policy) == _POLICY_FIELDS
            and isinstance(roles, list)
            and all(
                isinstance(role, dict)
                and set(role) == _ROLE_BINDING_FIELDS
                for role in roles
            )
        )
        return receipt if exact else None
    except Exception:
        return None


def normalize_canonical_json_mapping(
    value: Any,
) -> Optional[dict[str, Any]]:
    """Detach one exact JSON mapping; reject hostile or noncanonical values."""
    try:
        if not isinstance(value, Mapping):
            return None
        value.get("")
        normalized = _canonical_json_value(value)
        json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        return normalized if isinstance(normalized, dict) else None
    except Exception:
        return None


def _canonical_json_value(value: Any) -> Any:
    value_type = type(value)
    if value is None or value_type in (str, bool, int):
        return value
    if value_type is float:
        if not math.isfinite(value):
            raise ValueError("non_finite_json_number")
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str or key in normalized:
                raise TypeError("noncanonical_json_mapping")
            normalized[key] = _canonical_json_value(item)
        return normalized
    if value_type is list:
        return [_canonical_json_value(item) for item in value]
    raise TypeError("noncanonical_json_type")


__all__ = [
    "normalize_canonical_json_mapping",
    "normalize_exact_binding_receipt",
]
