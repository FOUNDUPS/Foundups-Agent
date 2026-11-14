"""Shared authority invariants for signed model evidence."""

from __future__ import annotations

from typing import Any, Mapping


def validated_trusted_model_evidence_keys(
    trusted_public_keys: Mapping[tuple[str, str, str], str],
) -> dict[tuple[str, str, str], str]:
    keys = dict(trusted_public_keys)
    if any(
        not isinstance(key, tuple)
        or len(key) != 3
        or not all(isinstance(part, str) and part for part in key)
        for key in keys
    ):
        raise ValueError("trusted_model_evidence_key_tuple_required")
    return keys


def assert_independent_model_evidence_signers(
    benchmark: Any,
    promotion: Any,
) -> None:
    if (
        benchmark.signer_public_key == promotion.signer_public_key
        or benchmark.signer_key_fingerprint == promotion.signer_key_fingerprint
    ):
        raise ValueError("benchmark_and_promotion_signers_not_independent")


def assert_independent_panel_authority(
    receipt: Any,
    entries: tuple[Any, ...],
) -> None:
    signatures = tuple(
        signature
        for entry in entries
        for signature in (
            entry.benchmark_signature_receipt,
            entry.promotion_signature_receipt,
        )
    )
    if receipt.signer_public_key in {
        signature.signer_public_key for signature in signatures
    } or receipt.signer_key_fingerprint in {
        signature.signer_key_fingerprint for signature in signatures
    }:
        raise ValueError("panel_authority_signer_not_independent")


__all__ = [
    "assert_independent_model_evidence_signers",
    "assert_independent_panel_authority",
    "validated_trusted_model_evidence_keys",
]
