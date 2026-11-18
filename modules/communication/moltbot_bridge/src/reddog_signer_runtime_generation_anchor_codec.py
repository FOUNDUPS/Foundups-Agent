"""Canonical serialization and authentication for signer generation anchors."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    is_sha256,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    SignerRuntimeGenerationActivation,
    SignerRuntimeGenerationBinding,
    SignerRuntimeGenerationHighWater,
    SignerRuntimeGenerationSigner,
    SignerRuntimeGenerationVerifier,
)


SCHEMA_VERSION = "reddog_signer_runtime_generation_anchor.v1"
_MAX_AUTHENTICATION_TAG_LENGTH = 4096


def decode_signer_runtime_generation_state(
    state: Mapping[str, Any],
    *,
    anchor_id: str,
    verifier: SignerRuntimeGenerationVerifier,
    high_water_store_id: str,
    high_water_durability_receipt_id: str,
) -> SignerRuntimeGenerationActivation | None:
    if not state:
        return None
    _validate_state_header(
        state,
        anchor_id=anchor_id,
        verifier=verifier,
        high_water_store_id=high_water_store_id,
        high_water_durability_receipt_id=high_water_durability_receipt_id,
    )
    binding = _binding_from_state(state)
    _validate_binding(binding)
    previous = state.get("previous_revision")
    _validate_expected_revision(previous)
    revision = str(state.get("revision") or "")
    if revision != _state_revision(state):
        raise ValueError("generation_anchor_revision_invalid")
    tag = str(state.get("authentication_tag") or "")
    _validate_authentication_tag(tag)
    unsigned = dict(state)
    unsigned.pop("authentication_tag")
    unsigned.pop("revision")
    if not verifier.verify(_authentication_input(unsigned), tag):
        raise ValueError("generation_anchor_authentication_invalid")
    return SignerRuntimeGenerationActivation(
        anchor_id=anchor_id,
        **asdict(binding),
        previous_revision=previous,
        authenticator_id=verifier.authenticator_id,
        high_water_store_id=high_water_store_id,
        high_water_durability_receipt_id=high_water_durability_receipt_id,
        authentication_tag=tag,
        revision=revision,
    )


def _validate_state_header(
    state: Mapping[str, Any],
    *,
    anchor_id: str,
    verifier: SignerRuntimeGenerationVerifier,
    high_water_store_id: str,
    high_water_durability_receipt_id: str,
) -> None:
    expected_fields = {
        "schema_version",
        "anchor_id",
        "generation",
        "manifest_id",
        "artifact_generation_digest",
        "config_digest",
        "config_raw_digest",
        "run_packet_digest",
        "previous_revision",
        "authenticator_id",
        "high_water_store_id",
        "high_water_durability_receipt_id",
        "authentication_tag",
        "revision",
    }
    if set(state) != expected_fields:
        raise ValueError("generation_anchor_state_shape_invalid")
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("generation_anchor_schema_invalid")
    if state.get("anchor_id") != anchor_id:
        raise ValueError("generation_anchor_identity_mismatch")
    if state.get("authenticator_id") != verifier.authenticator_id:
        raise ValueError("generation_anchor_authenticator_mismatch")
    if (
        state.get("high_water_store_id") != high_water_store_id
        or state.get("high_water_durability_receipt_id")
        != high_water_durability_receipt_id
    ):
        raise ValueError("generation_anchor_high_water_mismatch")


def _unsigned_state(
    binding: SignerRuntimeGenerationBinding,
    *,
    anchor_id: str,
    authenticator_id: str,
    high_water_store_id: str,
    high_water_durability_receipt_id: str,
    previous_revision: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "anchor_id": anchor_id,
        **asdict(binding),
        "previous_revision": previous_revision,
        "authenticator_id": authenticator_id,
        "high_water_store_id": high_water_store_id,
        "high_water_durability_receipt_id": high_water_durability_receipt_id,
    }


def _binding_from_state(
    state: Mapping[str, Any],
) -> SignerRuntimeGenerationBinding:
    return SignerRuntimeGenerationBinding(
        generation=state.get("generation"),
        manifest_id=state.get("manifest_id"),
        artifact_generation_digest=state.get("artifact_generation_digest"),
        config_digest=state.get("config_digest"),
        config_raw_digest=state.get("config_raw_digest"),
        run_packet_digest=state.get("run_packet_digest"),
    )


def _validate_binding(binding: SignerRuntimeGenerationBinding) -> None:
    if not isinstance(binding, SignerRuntimeGenerationBinding):
        raise TypeError("generation_anchor_binding_type_invalid")
    if type(binding.generation) is not int or binding.generation < 1:
        raise ValueError("generation_anchor_generation_invalid")
    values = (
        binding.manifest_id,
        binding.artifact_generation_digest,
        binding.config_digest,
        binding.config_raw_digest,
        binding.run_packet_digest,
    )
    if not all(is_sha256(value) for value in values):
        raise ValueError("generation_anchor_binding_digest_invalid")


def _require_next_generation(
    current: SignerRuntimeGenerationActivation | None,
    binding: SignerRuntimeGenerationBinding,
) -> None:
    expected = 1 if current is None else current.generation + 1
    if binding.generation != expected:
        raise ValueError("generation_anchor_generation_not_monotonic")
    if current is not None and (
        binding.manifest_id == current.manifest_id
        or binding.artifact_generation_digest
        == current.artifact_generation_digest
    ):
        raise ValueError("generation_anchor_generation_replay")


def _require_expected_revision(
    current: SignerRuntimeGenerationActivation | None,
    expected_revision: str | None,
) -> None:
    actual = None if current is None else current.revision
    if actual != expected_revision:
        raise RuntimeError("generation_anchor_revision_conflict")


def _validate_expected_revision(value: Any) -> None:
    if value is not None and (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError("generation_anchor_expected_revision_invalid")


def _require_signer(value: Any) -> SignerRuntimeGenerationSigner:
    if not callable(getattr(value, "authenticate", None)):
        raise ValueError("generation_anchor_signer_invalid")
    _require_ascii_text(
        getattr(value, "authenticator_id", None),
        "authenticator_id",
    )
    return value


def _require_verifier(value: Any) -> SignerRuntimeGenerationVerifier:
    if not callable(getattr(value, "verify", None)) or callable(
        getattr(value, "authenticate", None)
    ):
        raise ValueError("generation_anchor_verifier_invalid")
    _require_ascii_text(
        getattr(value, "authenticator_id", None),
        "authenticator_id",
    )
    return value


def _authenticated_state(
    unsigned: Mapping[str, Any],
    signer: SignerRuntimeGenerationSigner,
    verifier: SignerRuntimeGenerationVerifier,
) -> dict[str, Any]:
    payload = _authentication_input(unsigned)
    tag = signer.authenticate(payload)
    _validate_authentication_tag(tag)
    if not verifier.verify(payload, tag):
        raise ValueError("generation_anchor_authentication_rejected")
    return {**unsigned, "authentication_tag": tag}


def _high_water(
    value: SignerRuntimeGenerationActivation | None,
) -> SignerRuntimeGenerationHighWater | None:
    if value is None:
        return None
    return SignerRuntimeGenerationHighWater(
        generation=value.generation,
        revision=value.revision,
    )


def _validate_authentication_tag(value: Any) -> None:
    if (
        not isinstance(value, str)
        or not value
        or not value.isascii()
        or len(value) > _MAX_AUTHENTICATION_TAG_LENGTH
    ):
        raise ValueError("generation_anchor_authentication_tag_invalid")


def _require_ascii_text(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or not value.isascii()
        or len(value) > 1024
    ):
        raise ValueError(f"generation_anchor_{name}_invalid")
    return value.strip()


def _paths_overlap(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents


def _authentication_input(state: Mapping[str, Any]) -> bytes:
    return json.dumps(
        state,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _state_revision(state: Mapping[str, Any]) -> str:
    unsigned = dict(state)
    unsigned.pop("revision", None)
    return hashlib.sha256(_authentication_input(unsigned)).hexdigest()


__all__ = [
    "SCHEMA_VERSION",
    "decode_signer_runtime_generation_state",
]
