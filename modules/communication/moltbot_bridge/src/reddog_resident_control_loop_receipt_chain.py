"""Complete-chain verification for authenticated resident control receipts."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_receipt_store import (
    _validate_existing_receipts,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)


def verify_resident_control_loop_receipt_chain(
    receipts: Sequence[Mapping[str, Any]],
    *,
    expected_signer_public_key: str,
    expected_key_epoch: str,
    expected_consensus_receipt_digest: str,
    expected_authority_profile_digest: str,
    expected_authority_profile_source_receipt_id: str,
    expected_issuer_principal_id: str,
    signature_verifier: SignatureVerifier | None = None,
) -> None:
    """Verify every v2 record and link in a serialized append-only chain."""

    existing = "\n".join(
        json.dumps(dict(receipt), sort_keys=True, separators=(",", ":"))
        for receipt in receipts
    )
    if existing:
        existing += "\n"
    _validate_existing_receipts(
        existing,
        require_authenticated_current=True,
        expected_authentication={
            "signer_public_key": expected_signer_public_key,
            "key_epoch": expected_key_epoch,
            "consensus_receipt_digest": expected_consensus_receipt_digest,
            "authority_profile_digest": expected_authority_profile_digest,
            "authority_profile_source_receipt_id": (
                expected_authority_profile_source_receipt_id
            ),
            "issuer_principal_id": expected_issuer_principal_id,
            "signature_verifier": signature_verifier,
        },
    )


def verify_control_receipt_chain_against_profile(
    receipts: Sequence[Mapping[str, Any]],
    authority_profile: Mapping[str, Any],
) -> None:
    """Verify a chain against one confined authority-profile mapping."""

    profile_raw = json.dumps(
        dict(authority_profile),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    verify_resident_control_loop_receipt_chain(
        receipts,
        expected_signer_public_key=str(authority_profile["reddog_public_key"]),
        expected_key_epoch=str(authority_profile["key_epoch"]),
        expected_consensus_receipt_digest=str(
            authority_profile["consensus_receipt_digest"]
        ),
        expected_authority_profile_digest="sha256:"
        + hashlib.sha256(profile_raw.encode("utf-8")).hexdigest(),
        expected_authority_profile_source_receipt_id=str(
            authority_profile["authority_profile_source_receipt_id"]
        ),
        expected_issuer_principal_id=str(authority_profile["principal_id"]),
    )


__all__ = [
    "verify_control_receipt_chain_against_profile",
    "verify_resident_control_loop_receipt_chain",
]
