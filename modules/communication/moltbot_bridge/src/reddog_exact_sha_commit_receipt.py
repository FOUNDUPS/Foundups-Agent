"""Dependency-light validation for resident exact-SHA commit receipts."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping


EXACT_SHA_COMMIT_RECEIPT_SCHEMA = (
    "reddog_resident_queue_exact_sha_commit_receipt.v1"
)
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def validate_exact_sha_commit_receipt(value: Any) -> bool:
    """Recompute the canonical receipt identity before downstream trust."""

    receipt = dict(_mapping(value))
    receipt_id = str(receipt.pop("receipt_id", "") or "")
    return bool(
        receipt.get("schema_version") == EXACT_SHA_COMMIT_RECEIPT_SCHEMA
        and all(_SHA_RE.fullmatch(str(receipt.get(name) or "")) for name in (
            "base_sha", "head_sha", "parent_sha", "tree_sha",
        ))
        and receipt.get("base_sha") == receipt.get("parent_sha")
        and receipt.get("base_sha") != receipt.get("head_sha")
        and receipt.get("effect_commit_state") == "COMMITTED"
        and receipt.get("reconciliation_required") is False
        and receipt.get("main_checkout_untouched") is True
        and receipt.get("no_push_performed") is True
        and receipt.get("no_pr_created") is True
        and receipt.get("no_merge_performed") is True
        and receipt_id == _canonical_digest(receipt)
    )


def _canonical_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


__all__ = ["EXACT_SHA_COMMIT_RECEIPT_SCHEMA", "validate_exact_sha_commit_receipt"]
