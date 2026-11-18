"""RedDog signed receipt chain verifier (no signing, no execution).

Slice: REDDOG_SIGNED_RECEIPT_CHAIN_PHASE1

Implements the SignedReceipt verifier from
docs/contracts/REDDOG_PRINCIPAL_IDENTITY_AND_DELEGATION_CONTRACT_PHASE1.md.
This module does NOT sign, generate keys, hold private keys, write rewards, execute
commands, enqueue OpenClaw/Hermes work, or mutate the repo. It only verifies
externally signed receipt records against an injected signature verifier.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    FailClosedSignatureVerifier,
    PREFIX_RECEIPT,
    canonical_signing_input,
)

SIGNED_RECEIPT_CHAIN_ACCEPT = "SIGNED_RECEIPT_CHAIN_ACCEPT"
SIGNED_RECEIPT_CHAIN_REJECT = "SIGNED_RECEIPT_CHAIN_REJECT"


class ReceiptChainReason:
    MALFORMED_RECEIPT = "REJECT_MALFORMED_RECEIPT"
    NON_ASCII = "REJECT_NON_ASCII_RECEIPT"
    MISSING_SIGNATURE = "REJECT_MISSING_RECEIPT_SIGNATURE"
    SIGNATURE_INVALID = "REJECT_RECEIPT_SIGNATURE_INVALID"
    WORK_ORDER_MISMATCH = "REJECT_RECEIPT_WORK_ORDER_MISMATCH"
    REDDOG_MISMATCH = "REJECT_RECEIPT_REDDOG_MISMATCH"
    PREV_HASH_MISMATCH = "REJECT_RECEIPT_PREV_HASH_MISMATCH"
    REWARD_ACCOUNT_MISMATCH = "REJECT_RECEIPT_REWARD_ACCOUNT_MISMATCH"
    ISSUED_IN_FUTURE = "REJECT_RECEIPT_ISSUED_IN_FUTURE"
    EMPTY_CHAIN = "REJECT_EMPTY_RECEIPT_CHAIN"
    BACKEND_NOT_CONFIGURED = "REJECT_RECEIPT_SIGNATURE_BACKEND_NOT_CONFIGURED"


class ReceiptSignatureVerifier(Protocol):
    def verify(self, public_key: str, signing_input: str, signature: str) -> bool: ...


@dataclass
class SignedReceipt:
    receipt_id: str
    work_order_id: str
    reddog_id: str
    prev_receipt_hash: Optional[str]
    covered_action_digest: str
    reward_account: Optional[str]
    issued_at: int
    signature: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SignedReceiptChainVerificationResult:
    decision: str
    accepted: bool
    reason_codes: List[str] = field(default_factory=list)
    verified_count: int = 0
    receipt_hashes: List[str] = field(default_factory=list)
    terminal_receipt_hash: Optional[str] = None
    no_reward_settlement_performed: bool = True
    no_execution_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _is_ascii_deep(value: Any) -> bool:
    if isinstance(value, str):
        return all(ord(c) < 128 for c in value)
    if isinstance(value, Mapping):
        return all(isinstance(k, str) and _is_ascii_deep(k) and _is_ascii_deep(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return all(_is_ascii_deep(v) for v in value)
    return True


def signed_receipt_from_mapping(value: Mapping[str, Any]) -> Optional[SignedReceipt]:
    try:
        return SignedReceipt(
            receipt_id=str(value["receipt_id"]),
            work_order_id=str(value["work_order_id"]),
            reddog_id=str(value["reddog_id"]),
            prev_receipt_hash=None if value.get("prev_receipt_hash") is None else str(value.get("prev_receipt_hash")),
            covered_action_digest=str(value["covered_action_digest"]),
            reward_account=None if value.get("reward_account") is None else str(value.get("reward_account")),
            issued_at=int(value["issued_at"]),
            signature="" if value.get("signature") is None else str(value.get("signature", "")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def build_receipt_payload_for_signing(
    *,
    receipt_id: str,
    work_order_id: str,
    reddog_id: str,
    prev_receipt_hash: Optional[str],
    covered_action_digest: str,
    reward_account: Optional[str],
    issued_at: int,
) -> Dict[str, Any]:
    """Return the canonical SignedReceipt fields before an external signer adds signature."""
    return {
        "receipt_id": receipt_id,
        "work_order_id": work_order_id,
        "reddog_id": reddog_id,
        "prev_receipt_hash": prev_receipt_hash,
        "covered_action_digest": covered_action_digest,
        "reward_account": reward_account,
        "issued_at": int(issued_at),
    }


def receipt_payload_hash(receipt: SignedReceipt | Mapping[str, Any]) -> str:
    """Hash the canonical receipt signing input (prefix + JSON, excluding signature)."""
    payload = receipt.to_dict() if isinstance(receipt, SignedReceipt) else dict(receipt)
    signing_input = canonical_signing_input(payload, PREFIX_RECEIPT)
    return hashlib.sha256(signing_input.encode("utf-8")).hexdigest()


def verify_signed_receipt_chain(
    receipts: Sequence[SignedReceipt | Mapping[str, Any]],
    *,
    reddog_public_key: str,
    signature_verifier: Optional[ReceiptSignatureVerifier] = None,
    work_order_id: str,
    reddog_id: str,
    identity_reward_account: Optional[str] = None,
    now: Optional[int] = None,
    max_future_skew_s: int = 60,
    allow_empty: bool = True,
) -> SignedReceiptChainVerificationResult:
    """Verify ordered SignedReceipt records.

    Empty chains are valid at work-authority issuance when allow_empty=True, but they
    contain no reward-bearing receipts. Any non-empty chain must be fully signed and
    hash-linked.
    """
    verifier = signature_verifier or FailClosedSignatureVerifier()
    if not receipts:
        if allow_empty:
            return SignedReceiptChainVerificationResult(
                decision=SIGNED_RECEIPT_CHAIN_ACCEPT,
                accepted=True,
                verified_count=0,
            )
        return SignedReceiptChainVerificationResult(
            decision=SIGNED_RECEIPT_CHAIN_REJECT,
            accepted=False,
            reason_codes=[ReceiptChainReason.EMPTY_CHAIN],
        )

    reason_codes: List[str] = []
    receipt_hashes: List[str] = []
    expected_prev: Optional[str] = None
    checked_now = int(now) if now is not None else None

    for raw in receipts:
        receipt = raw if isinstance(raw, SignedReceipt) else signed_receipt_from_mapping(raw)
        if receipt is None:
            reason_codes.append(ReceiptChainReason.MALFORMED_RECEIPT)
            break
        payload = receipt.to_dict()
        if not _is_ascii_deep(payload):
            reason_codes.append(ReceiptChainReason.NON_ASCII)
        if not receipt.signature:
            reason_codes.append(ReceiptChainReason.MISSING_SIGNATURE)
        if receipt.work_order_id != work_order_id:
            reason_codes.append(ReceiptChainReason.WORK_ORDER_MISMATCH)
        if receipt.reddog_id != reddog_id:
            reason_codes.append(ReceiptChainReason.REDDOG_MISMATCH)
        if receipt.prev_receipt_hash != expected_prev:
            reason_codes.append(ReceiptChainReason.PREV_HASH_MISMATCH)
        if identity_reward_account is not None and receipt.reward_account is not None:
            if receipt.reward_account != identity_reward_account:
                reason_codes.append(ReceiptChainReason.REWARD_ACCOUNT_MISMATCH)
        if checked_now is not None and receipt.issued_at > checked_now + max_future_skew_s:
            reason_codes.append(ReceiptChainReason.ISSUED_IN_FUTURE)

        try:
            ok = verifier.verify(
                reddog_public_key,
                canonical_signing_input(payload, PREFIX_RECEIPT),
                receipt.signature,
            ) is True
        except Exception:
            ok = False
        if not ok:
            reason_codes.append(ReceiptChainReason.SIGNATURE_INVALID)

        receipt_hash = receipt_payload_hash(payload)
        receipt_hashes.append(receipt_hash)
        expected_prev = receipt_hash

    if reason_codes:
        return SignedReceiptChainVerificationResult(
            decision=SIGNED_RECEIPT_CHAIN_REJECT,
            accepted=False,
            reason_codes=list(dict.fromkeys(reason_codes)),
            verified_count=0,
            receipt_hashes=receipt_hashes,
            terminal_receipt_hash=receipt_hashes[-1] if receipt_hashes else None,
        )

    return SignedReceiptChainVerificationResult(
        decision=SIGNED_RECEIPT_CHAIN_ACCEPT,
        accepted=True,
        verified_count=len(receipt_hashes),
        receipt_hashes=receipt_hashes,
        terminal_receipt_hash=receipt_hashes[-1],
    )


__all__ = [
    "ReceiptChainReason",
    "SIGNED_RECEIPT_CHAIN_ACCEPT",
    "SIGNED_RECEIPT_CHAIN_REJECT",
    "SignedReceipt",
    "SignedReceiptChainVerificationResult",
    "build_receipt_payload_for_signing",
    "receipt_payload_hash",
    "signed_receipt_from_mapping",
    "verify_signed_receipt_chain",
]
