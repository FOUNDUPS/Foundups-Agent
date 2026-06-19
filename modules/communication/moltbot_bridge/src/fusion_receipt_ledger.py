#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fusion receipt ledger -- durable append-only persistence + ADVISORY WSP_97 scoring.

Slice: HERMES_FUSION_RECEIPT_PERSISTENCE_PHASE1. Stores ModelContributionReceipts as append-only JSONL
(one per line, digests only -- the receipt is already digest-only) and provides an advisory scoring seam
that evaluates a receipt against WSP_97 truth boundaries.

WSP 97 TRUTH BOUNDARIES:
  DOES: append a receipt as one JSON line (fail-closed -- refuse non-advisory / unserializable / any
        forbidden pattern); read the ledger skipping malformed lines; score a receipt against WSP_97
        (advisory verdict only).
  DOES NOT: make any network call / read any key (no egress); mutate CABR / payout / source-authority /
        merge state (scoring returns a verdict; cabr_status is ALWAYS NOT_SUBMITTED because no CABR
        consensus engine exists); rewrite existing ledger lines; add a new dependency (stdlib json only);
        commit a ledger artifact (store_path is a required, caller-chosen runtime path).

REUSE NOTE (WSP 84): mirrors the append-only JSONL idiom of holo_index/qwen_advisor/telemetry.py
(record_advisor_event: open("a") + json.dumps + newline) and reuses ModelContributionReceipt.to_dict()
/ is_valid_digest. The existing proof_of_compute_receipt.py / receipt_emitter.py are coupled to FoundUpJob
terminal states, so they are not imported here; a future HERMES_RECEIPT_LEDGER_CONSOLIDATION may unify them.

WSP: WSP 11 (interface), WSP 50 (pre-action), WSP 84 (reuse evaluated), WSP 97 (truth boundary).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .fusion_adapter import REDACTION_BLOCKED, ModelContributionReceipt, is_valid_digest
from .fusion_redaction_gate import REDACTION_GATE_PASSED, scan_forbidden

SCORE_WSP97_PASS = "wsp97_pass"
SCORE_WSP97_FAIL = "wsp97_fail"
CABR_NOT_SUBMITTED = "NOT_SUBMITTED"   # no CABR consensus engine exists; never asserts readiness

VALID_REDACTION_STATUSES = frozenset({REDACTION_GATE_PASSED, REDACTION_BLOCKED})


@dataclass
class ReceiptScore:
    wsp97_status: str          # SCORE_WSP97_PASS | SCORE_WSP97_FAIL
    cabr_status: str           # ALWAYS CABR_NOT_SUBMITTED
    advisory_only: bool        # ALWAYS True
    reasons: Tuple[str, ...]   # low-cardinality reason codes


def _as_record(receipt: object) -> Optional[Dict[str, Any]]:
    """Return the receipt as a dict, or None if it cannot be safely serialized (fail-closed).

    A ModelContributionReceipt is serialized via to_dict(), which itself raises if advisory_not_canonical
    was flipped -- so a non-advisory receipt becomes None here and is refused downstream.
    """
    try:
        if isinstance(receipt, ModelContributionReceipt):
            return receipt.to_dict()
        if isinstance(receipt, dict):
            return dict(receipt)
    except Exception:
        return None
    return None


def persist_receipt(receipt: object, store_path: object, *, received_at_iso: Optional[str] = None) -> bool:
    """Append one receipt as a JSON line (digests only). Returns True on write, False (fail-closed) when
    the receipt is non-advisory, cannot serialize, or its serialized form carries any forbidden pattern.

    Append-only: never rewrites existing lines. store_path is REQUIRED (no repo-committed default).
    """
    record = _as_record(receipt)
    if record is None:
        return False
    if record.get("advisory_not_canonical") is not True:
        return False
    if received_at_iso is not None and not isinstance(received_at_iso, str):
        return False  # fail-closed: the stamp must be a string (or None), never an arbitrary object
    record = dict(record)
    record["_received_at"] = received_at_iso
    # scan the EXACT record that would be written (including _received_at) -- nothing forbidden to disk
    if scan_forbidden(json.dumps(record, sort_keys=True)):
        return False
    path = Path(store_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
    return True


def load_receipts(store_path: object) -> List[Dict[str, Any]]:
    """Read the append-only ledger. Fail-closed: skip malformed/blank lines, never raise."""
    path = Path(store_path)
    if not path.is_file():     # missing OR a directory -> fail-closed, never raise
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def score_receipt(receipt: object) -> ReceiptScore:
    """Advisory WSP_97 scoring. NEVER mutates CABR / payout / source-authority.

    Fail-closed: any malformation or boundary violation -> wsp97_fail. cabr_status is ALWAYS
    NOT_SUBMITTED (no CABR engine), advisory_only is ALWAYS True. Returns a verdict object; writes nothing.
    """
    record = _as_record(receipt)
    if record is None:
        return ReceiptScore(SCORE_WSP97_FAIL, CABR_NOT_SUBMITTED, True, ("malformed_receipt",))
    reasons: List[str] = []
    if record.get("advisory_not_canonical") is not True:
        reasons.append("not_advisory")
    if not is_valid_digest(record.get("prompt_digest")):
        reasons.append("bad_prompt_digest")
    if record.get("redaction_status") not in VALID_REDACTION_STATUSES:
        reasons.append("bad_redaction_status")
    if scan_forbidden(json.dumps(record, sort_keys=True)):
        reasons.append("forbidden_content")
    status = SCORE_WSP97_FAIL if reasons else SCORE_WSP97_PASS
    return ReceiptScore(status, CABR_NOT_SUBMITTED, True, tuple(reasons))


__all__ = [
    "SCORE_WSP97_PASS",
    "SCORE_WSP97_FAIL",
    "CABR_NOT_SUBMITTED",
    "VALID_REDACTION_STATUSES",
    "ReceiptScore",
    "persist_receipt",
    "load_receipts",
    "score_receipt",
]
