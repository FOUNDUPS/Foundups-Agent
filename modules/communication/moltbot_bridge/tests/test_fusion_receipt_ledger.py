#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the Fusion receipt ledger (HERMES_FUSION_RECEIPT_PERSISTENCE_PHASE1).

Egress-free: no network, no key. Append-only persistence + advisory WSP_97 scoring. Synthetic secrets
only (split fragments). No skip / no xfail. No ledger artifact is committed -- tests use tmp_path.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.fusion_receipt_ledger import (
    CABR_NOT_SUBMITTED,
    SCORE_WSP97_FAIL,
    SCORE_WSP97_PASS,
    ReceiptScore,
    load_receipts,
    persist_receipt,
    score_receipt,
)
from modules.communication.moltbot_bridge.src.fusion_adapter import (
    ModelContributionReceipt,
    REDACTION_BLOCKED,
    digest,
)
from modules.communication.moltbot_bridge.src.fusion_redaction_gate import REDACTION_GATE_PASSED
import modules.communication.moltbot_bridge.src.fusion_receipt_ledger as ledger_mod

MODULE_SRC = Path(ledger_mod.__file__)
SECRET = "s" "k-" + "A" * 48   # synthetic redactable secret


def _mock_receipt(**over):
    base = dict(
        receipt_id="r1",
        task_id="t1",
        provider="mock",
        mode="mock",
        outer_model="o",
        panel_models=["m"],
        judge_model="j",
        prompt_digest=digest("redacted prompt"),
        response_digest=digest("resp"),
        consensus="a clean advisory consensus",
        redaction_status=REDACTION_GATE_PASSED,
    )
    base.update(over)
    return ModelContributionReceipt(**base)


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------


def test_persist_and_load_roundtrip(tmp_path):
    store = tmp_path / "ledger.jsonl"
    assert persist_receipt(_mock_receipt(), store, received_at_iso="2026-06-20T00:00:00Z") is True
    records = load_receipts(store)
    assert len(records) == 1
    assert records[0]["receipt_id"] == "r1"
    assert records[0]["_received_at"] == "2026-06-20T00:00:00Z"
    assert records[0]["advisory_not_canonical"] is True


def test_append_only(tmp_path):
    store = tmp_path / "ledger.jsonl"
    persist_receipt(_mock_receipt(receipt_id="r1"), store)
    first = store.read_text(encoding="utf-8")
    persist_receipt(_mock_receipt(receipt_id="r2"), store)
    after = store.read_text(encoding="utf-8")
    assert after.startswith(first)             # earlier line untouched
    assert len(load_receipts(store)) == 2


def test_non_advisory_receipt_not_persisted(tmp_path):
    store = tmp_path / "ledger.jsonl"
    r = _mock_receipt()
    r.advisory_not_canonical = False           # flipped after construction
    assert persist_receipt(r, store) is False
    assert not store.exists()                  # nothing written


def test_dict_non_advisory_not_persisted(tmp_path):
    store = tmp_path / "ledger.jsonl"
    bad = _mock_receipt().to_dict()
    bad["advisory_not_canonical"] = False
    assert persist_receipt(bad, store) is False
    assert load_receipts(store) == []


def test_forbidden_content_not_persisted(tmp_path):
    store = tmp_path / "ledger.jsonl"
    leaky = _mock_receipt(consensus="leaked " + SECRET)
    assert persist_receipt(leaky, store) is False
    assert not store.exists()


def test_persisted_record_has_no_raw_secret(tmp_path):
    store = tmp_path / "ledger.jsonl"
    persist_receipt(_mock_receipt(), store)
    raw = store.read_text(encoding="utf-8")
    assert SECRET not in raw
    assert "sha256:" in raw                     # digests present


def test_forbidden_received_at_is_scanned_and_refused(tmp_path):
    # the timestamp param is scanned with the rest of the record (it lands in the written line)
    store = tmp_path / "ledger.jsonl"
    assert persist_receipt(_mock_receipt(), store, received_at_iso="stamp " + SECRET) is False
    assert not store.exists()


def test_non_string_received_at_refused(tmp_path):
    store = tmp_path / "ledger.jsonl"
    assert persist_receipt(_mock_receipt(), store, received_at_iso=12345) is False  # type: ignore[arg-type]
    assert not store.exists()


def test_load_on_directory_path_fails_closed(tmp_path):
    d = tmp_path / "a_dir"
    d.mkdir()
    assert load_receipts(d) == []   # directory -> [], never raises


def test_persist_requires_explicit_store_path():
    # no repo-committed default path -> store_path is a required positional argument
    with pytest.raises(TypeError):
        persist_receipt(_mock_receipt())  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# load fail-closed
# ---------------------------------------------------------------------------


def test_load_missing_file_returns_empty(tmp_path):
    assert load_receipts(tmp_path / "nope.jsonl") == []


def test_load_skips_malformed_lines(tmp_path):
    store = tmp_path / "ledger.jsonl"
    persist_receipt(_mock_receipt(receipt_id="good"), store)
    with store.open("a", encoding="utf-8") as fh:
        fh.write("this is not json\n")
        fh.write("\n")
        fh.write("[1,2,3]\n")        # valid json but not a dict
    records = load_receipts(store)
    assert len(records) == 1 and records[0]["receipt_id"] == "good"


# ---------------------------------------------------------------------------
# advisory scoring
# ---------------------------------------------------------------------------


def test_score_clean_receipt_passes():
    s = score_receipt(_mock_receipt())
    assert s.wsp97_status == SCORE_WSP97_PASS
    assert s.reasons == ()
    assert s.cabr_status == CABR_NOT_SUBMITTED and s.advisory_only is True


def test_score_blocked_redaction_status_still_valid():
    s = score_receipt(_mock_receipt(redaction_status=REDACTION_BLOCKED))
    assert s.wsp97_status == SCORE_WSP97_PASS


def test_score_fail_not_advisory():
    rec = _mock_receipt().to_dict()
    rec["advisory_not_canonical"] = False
    s = score_receipt(rec)
    assert s.wsp97_status == SCORE_WSP97_FAIL and "not_advisory" in s.reasons


def test_score_fail_bad_digest():
    rec = _mock_receipt().to_dict()
    rec["prompt_digest"] = "raw not a digest"
    s = score_receipt(rec)
    assert s.wsp97_status == SCORE_WSP97_FAIL and "bad_prompt_digest" in s.reasons


def test_score_fail_bad_redaction_status():
    rec = _mock_receipt().to_dict()
    rec["redaction_status"] = "something_else"
    s = score_receipt(rec)
    assert "bad_redaction_status" in s.reasons


def test_score_fail_forbidden_content():
    rec = _mock_receipt().to_dict()
    rec["consensus"] = "echoed " + SECRET
    s = score_receipt(rec)
    assert s.wsp97_status == SCORE_WSP97_FAIL and "forbidden_content" in s.reasons


def test_score_malformed_input_fails_closed():
    for bad in [123, None, "string", ["list"]]:
        s = score_receipt(bad)
        assert s.wsp97_status == SCORE_WSP97_FAIL and "malformed_receipt" in s.reasons


def test_score_never_asserts_cabr_readiness():
    inputs = [_mock_receipt(), _mock_receipt().to_dict(), 123, {"advisory_not_canonical": True}]
    for inp in inputs:
        s = score_receipt(inp)
        assert s.cabr_status == CABR_NOT_SUBMITTED   # NEVER a readiness assertion
        assert s.advisory_only is True
        assert isinstance(s, ReceiptScore)


# ---------------------------------------------------------------------------
# boundaries: no egress / no dependency / no authority mutation
# ---------------------------------------------------------------------------


def test_module_imports_no_egress_no_authority_no_new_dep():
    tree = ast.parse(MODULE_SRC.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                roots.add((node.module or "").split(".")[0])
    # stdlib only (intra-package relative imports are level>0 and excluded). No os/requests/cabr import
    # means the module structurally cannot read env/keys, call the network, or mutate a CABR/payout engine.
    allowed = {"json", "dataclasses", "pathlib", "typing", "__future__"}
    assert roots <= allowed, f"unexpected top-level imports: {roots - allowed}"
    forbidden = {"os", "sys", "requests", "httpx", "aiohttp", "openai", "openrouter", "socket", "subprocess"}
    assert not (forbidden & roots)


def test_module_makes_no_calls_to_os_or_network():
    # AST: no os.getenv / os.environ / requests.* / open(write) calls anywhere in the ledger
    tree = ast.parse(MODULE_SRC.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in ("getenv", "environ"), "ledger must not read env"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            base = node.func.value
            if isinstance(base, ast.Name):
                assert base.id not in ("requests", "httpx", "subprocess"), "ledger must not call network/subprocess"
