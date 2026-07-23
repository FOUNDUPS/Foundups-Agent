# -*- coding: utf-8 -*-
"""Strict JSON schema boundary for supplied model runtime binding receipts."""

from __future__ import annotations

import json
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
    if not isinstance(value, Mapping):
        return None
    try:
        receipt = json.loads(
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
        )
    except (TypeError, ValueError):
        return None
    policy = receipt.get("policy")
    roles = receipt.get("role_bindings")
    exact = bool(
        set(receipt) == _BINDING_FIELDS
        and isinstance(policy, Mapping)
        and set(policy) == _POLICY_FIELDS
        and isinstance(roles, list)
        and all(
            isinstance(role, Mapping)
            and set(role) == _ROLE_BINDING_FIELDS
            for role in roles
        )
    )
    return receipt if exact else None


__all__ = ["normalize_exact_binding_receipt"]
