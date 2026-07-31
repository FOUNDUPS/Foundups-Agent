"""Canonical namespace binding for an independent generation witness."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    is_sha256,
)


SCHEMA_VERSION = "reddog_signer_runtime_generation_witness_binding.v1"


@dataclass(frozen=True)
class SignerRuntimeGenerationWitnessBinding:
    authenticator_id: str
    signer_public_key_fingerprint: str
    key_epoch: str
    runtime_root_digest: str
    high_water_store_id: str
    high_water_durability_receipt_id: str
    witness_store_id: str
    witness_durability_receipt_id: str

    def context_digest(self) -> str:
        _validate(self)
        return _digest(
            {"schema_version": SCHEMA_VERSION, **asdict(self)}
        )

    def anchor_binding_digest(self, anchor_id: str) -> str:
        anchor = _ascii(anchor_id, "anchor_id")
        return _digest(
            {
                "schema_version": SCHEMA_VERSION,
                **asdict(self),
                "anchor_id": anchor,
            }
        )


def require_generation_witness_binding(
    value: Any,
    *,
    authenticator_id: str,
    high_water_store_id: str,
    high_water_durability_receipt_id: str,
    witness_store_id: str,
    witness_durability_receipt_id: str,
) -> SignerRuntimeGenerationWitnessBinding:
    if not isinstance(value, SignerRuntimeGenerationWitnessBinding):
        raise ValueError("generation_witness_binding_type_invalid")
    _validate(value)
    expected = (
        _ascii(authenticator_id, "authenticator_id"),
        _ascii(high_water_store_id, "high_water_store_id"),
        _sha256(
            high_water_durability_receipt_id,
            "high_water_durability_receipt_id",
        ),
        _ascii(witness_store_id, "witness_store_id"),
        _sha256(
            witness_durability_receipt_id,
            "witness_durability_receipt_id",
        ),
    )
    actual = (
        value.authenticator_id,
        value.high_water_store_id,
        value.high_water_durability_receipt_id,
        value.witness_store_id,
        value.witness_durability_receipt_id,
    )
    if actual != expected:
        raise ValueError("generation_witness_binding_authority_mismatch")
    return value


def _validate(value: SignerRuntimeGenerationWitnessBinding) -> None:
    _ascii(value.authenticator_id, "authenticator_id")
    _sha256(
        value.signer_public_key_fingerprint,
        "signer_public_key_fingerprint",
    )
    _ascii(value.key_epoch, "key_epoch")
    _sha256(value.runtime_root_digest, "runtime_root_digest")
    _ascii(value.high_water_store_id, "high_water_store_id")
    _sha256(
        value.high_water_durability_receipt_id,
        "high_water_durability_receipt_id",
    )
    _ascii(value.witness_store_id, "witness_store_id")
    _sha256(
        value.witness_durability_receipt_id,
        "witness_durability_receipt_id",
    )


def _ascii(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or not value.isascii()
        or len(value) > 1024
    ):
        raise ValueError(f"generation_witness_{name}_invalid")
    return value.strip()


def _sha256(value: Any, name: str) -> str:
    if not is_sha256(value):
        raise ValueError(f"generation_witness_{name}_invalid")
    return str(value)


def _digest(value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


__all__ = [
    "SignerRuntimeGenerationWitnessBinding",
    "require_generation_witness_binding",
]
