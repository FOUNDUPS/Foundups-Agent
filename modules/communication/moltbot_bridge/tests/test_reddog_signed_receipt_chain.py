#!/usr/bin/env python3
"""Tests for REDDOG_SIGNED_RECEIPT_CHAIN_PHASE1.

The mock signer below is TEST ONLY. Production code verifies externally signed
receipts through an injected verifier and never signs, generates keys, executes
commands, settles rewards, or mutates the repo.
"""

from __future__ import annotations

import ast
import hashlib
import hmac
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_signed_receipt_chain import (
    ReceiptChainReason,
    SIGNED_RECEIPT_CHAIN_ACCEPT,
    SIGNED_RECEIPT_CHAIN_REJECT,
    build_receipt_payload_for_signing,
    receipt_payload_hash,
    verify_signed_receipt_chain,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PREFIX_RECEIPT,
    canonical_signing_input,
)

_PUB = "pub:reddog"
_SECRET = b"test-only-secret"
_WORK_ORDER = "wo-signed-receipts"
_REDDOG = "reddog:paccess"
_REWARD = "ups:012:paccess"


class _MockReceiptCrypto:
    def sign(self, public_key: str, signing_input: str) -> str:
        assert public_key == _PUB
        return hmac.new(_SECRET, signing_input.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify(self, public_key: str, signing_input: str, signature: str) -> bool:
        if public_key != _PUB:
            return False
        expected = hmac.new(_SECRET, signing_input.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


def _receipt(
    receipt_id: str = "rcpt-1",
    *,
    prev_receipt_hash=None,
    covered_action_digest: str = "sha256:action-1",
    work_order_id: str = _WORK_ORDER,
    reddog_id: str = _REDDOG,
    reward_account: str | None = _REWARD,
    issued_at: int = 1000,
) -> dict:
    payload = build_receipt_payload_for_signing(
        receipt_id=receipt_id,
        work_order_id=work_order_id,
        reddog_id=reddog_id,
        prev_receipt_hash=prev_receipt_hash,
        covered_action_digest=covered_action_digest,
        reward_account=reward_account,
        issued_at=issued_at,
    )
    payload["signature"] = _MockReceiptCrypto().sign(_PUB, canonical_signing_input(payload, PREFIX_RECEIPT))
    return payload


def _verify(receipts, **overrides):
    params = dict(
        reddog_public_key=_PUB,
        signature_verifier=_MockReceiptCrypto(),
        work_order_id=_WORK_ORDER,
        reddog_id=_REDDOG,
        identity_reward_account=_REWARD,
        now=1100,
    )
    params.update(overrides)
    return verify_signed_receipt_chain(receipts, **params)


def test_empty_chain_accepts_as_no_reward_yet():
    result = _verify([])

    assert result.decision == SIGNED_RECEIPT_CHAIN_ACCEPT
    assert result.accepted is True
    assert result.verified_count == 0
    assert result.terminal_receipt_hash is None
    assert result.no_reward_settlement_performed is True
    assert result.no_execution_performed is True


def test_empty_chain_can_fail_closed_when_required():
    result = _verify([], allow_empty=False)

    assert result.decision == SIGNED_RECEIPT_CHAIN_REJECT
    assert result.accepted is False
    assert result.reason_codes == [ReceiptChainReason.EMPTY_CHAIN]


def test_valid_first_signed_receipt_accepts():
    receipt = _receipt()
    result = _verify([receipt])

    assert result.accepted is True
    assert result.verified_count == 1
    assert result.receipt_hashes == [receipt_payload_hash(receipt)]
    assert result.terminal_receipt_hash == receipt_payload_hash(receipt)


def test_two_receipt_hash_chain_accepts():
    first = _receipt("rcpt-1")
    second = _receipt("rcpt-2", prev_receipt_hash=receipt_payload_hash(first), covered_action_digest="sha256:action-2")

    result = _verify([first, second])

    assert result.accepted is True
    assert result.verified_count == 2
    assert result.receipt_hashes == [receipt_payload_hash(first), receipt_payload_hash(second)]
    assert result.terminal_receipt_hash == receipt_payload_hash(second)


def test_missing_signature_is_not_reward_bearing():
    receipt = _receipt()
    receipt["signature"] = ""

    result = _verify([receipt])

    assert result.accepted is False
    assert ReceiptChainReason.MISSING_SIGNATURE in result.reason_codes
    assert ReceiptChainReason.SIGNATURE_INVALID in result.reason_codes


def test_tampered_covered_action_digest_rejects_signature():
    receipt = _receipt()
    receipt["covered_action_digest"] = "sha256:tampered"

    result = _verify([receipt])

    assert result.accepted is False
    assert result.reason_codes == [ReceiptChainReason.SIGNATURE_INVALID]


def test_wrong_previous_hash_rejects_chain():
    first = _receipt("rcpt-1")
    second = _receipt("rcpt-2", prev_receipt_hash="sha256:not-the-first")

    result = _verify([first, second])

    assert result.accepted is False
    assert ReceiptChainReason.PREV_HASH_MISMATCH in result.reason_codes


def test_work_order_mismatch_rejects_receipt():
    receipt = _receipt(work_order_id="wo-other")

    result = _verify([receipt])

    assert result.accepted is False
    assert ReceiptChainReason.WORK_ORDER_MISMATCH in result.reason_codes


def test_reddog_mismatch_rejects_receipt():
    receipt = _receipt(reddog_id="reddog:other")

    result = _verify([receipt])

    assert result.accepted is False
    assert ReceiptChainReason.REDDOG_MISMATCH in result.reason_codes


def test_reward_account_mismatch_rejects_receipt():
    receipt = _receipt(reward_account="ups:attacker")

    result = _verify([receipt])

    assert result.accepted is False
    assert ReceiptChainReason.REWARD_ACCOUNT_MISMATCH in result.reason_codes


def test_issued_at_future_skew_rejects_receipt():
    receipt = _receipt(issued_at=5000)

    result = _verify([receipt], now=1000, max_future_skew_s=60)

    assert result.accepted is False
    assert ReceiptChainReason.ISSUED_IN_FUTURE in result.reason_codes


def test_non_ascii_receipt_rejects():
    receipt = _receipt(receipt_id="rcpt-1")
    receipt["receipt_id"] = "rcpt-cafe-\u00e9"

    result = _verify([receipt])

    assert result.accepted is False
    assert ReceiptChainReason.NON_ASCII in result.reason_codes


def test_default_verifier_fails_closed_on_non_empty_chain():
    receipt = _receipt()

    result = verify_signed_receipt_chain(
        [receipt],
        reddog_public_key=_PUB,
        work_order_id=_WORK_ORDER,
        reddog_id=_REDDOG,
        identity_reward_account=_REWARD,
        now=1100,
    )

    assert result.accepted is False
    assert result.reason_codes == [ReceiptChainReason.SIGNATURE_INVALID]


def test_malformed_mapping_rejects():
    result = _verify([{"receipt_id": "rcpt-missing-fields"}])

    assert result.accepted is False
    assert result.reason_codes == [ReceiptChainReason.MALFORMED_RECEIPT]


def test_ast_boundary_no_signing_or_execution_surface():
    path = Path("modules/communication/moltbot_bridge/src/reddog_signed_receipt_chain.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = set()
    calls = set()
    names = set()
    constants = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            constants.append(node.value.lower())
        elif isinstance(node, ast.Name):
            names.add(node.id.lower())

    forbidden_import_fragments = (
        "subprocess",
        "socket",
        "os",
        "secrets",
        "cryptography",
        "nacl",
        "ecdsa",
        "web3",
        "wallet",
        "hmac",
    )
    forbidden_calls = {"open", "eval", "exec", "system", "popen", "run", "check_call", "check_output"}
    assert not any(fragment in imported for imported in imports for fragment in forbidden_import_fragments)
    assert not (calls & forbidden_calls)
    assert not any("begin private key" in value or "mock-secret" in value for value in constants)
    assert not any(name in {"private_key", "secret", "sign"} for name in names)
