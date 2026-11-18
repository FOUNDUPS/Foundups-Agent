"""Canonical digest helpers for model-runtime binding artifacts."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .model_runtime_binding import RedDogModelRuntimeBindingReceipt
from .model_signed_evidence import rehydrate_model_runtime_binding_receipt


def canonical_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def canonical_model_runtime_binding_digest(
    binding: RedDogModelRuntimeBindingReceipt | Mapping[str, Any],
) -> str:
    receipt = (
        binding
        if isinstance(binding, RedDogModelRuntimeBindingReceipt)
        else rehydrate_model_runtime_binding_receipt(binding)
    )
    return canonical_digest(receipt.to_dict())


def prefixed_digest(prefix: str, value: Any) -> str:
    return prefix + ":" + canonical_digest(value).removeprefix("sha256:")


def required_digest(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text.startswith("sha256:") or len(text) != 71:
        raise ValueError(f"{name}_invalid")
    return text


__all__ = [
    "canonical_digest",
    "canonical_model_runtime_binding_digest",
    "prefixed_digest",
    "required_digest",
]
