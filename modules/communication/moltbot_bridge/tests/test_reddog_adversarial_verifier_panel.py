#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the RedDog adversarial verifier PANEL.

Slice: REDDOG_ADVERSARIAL_VERIFIER_PANEL_PHASE1
WSP:   50, 84, 97

Deterministic verification that each Determine answer's cited evidence EXISTS + SUPPORTS the claim +
does not CONTRADICT the scorecard, fail-closed. INDEX_GAP is emitted advisory-only (non-mutating).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import reddog_adversarial_verifier_panel as v
from modules.communication.moltbot_bridge.src.reddog_adversarial_verifier_panel import (
    RefuteReason,
    Verdict,
    build_index_gap_event,
    verify_answer_set,
)


def _ans(idx, qtext, ans="yes", label="OBSERVED", refs=None):
    return {"index": idx, "question_text": qtext, "answer": ans, "wsp97_label": label,
            "evidence_refs": refs if refs is not None else [f"modules/x/f{idx}.py:{idx}"]}


def _reader(mapping):
    """Injected evidence reader: ref -> window content (or None for absent)."""
    def read(ref):
        return mapping.get(ref)
    return read


# 8 answers whose questions each name a code symbol; each cited window contains that symbol.
def _verified_8():
    qs = [
        (1, "Does any code autonomously write a NEW FoundUp scaffold via create_foundup?"),
        (2, "Is the OpenClaw genesis gate validate_genesis_envelope wired into dispatch?"),
        (3, "Is the genesis gate input-starved (nothing populates FoundUpGenesisEnvelope)?"),
        (4, "Does Hermes build_foundup equal extract_foundup of an existing module?"),
        (5, "Does FoundUpJob carry a first-class create action?"),
        (6, "Does the RedDog spine fail_closed by default?"),
        (7, "Is the execution valve VALVE_OPEN closed by default?"),
        (8, "What is the verdict and next safest slice?"),
    ]
    anchors = ["create_foundup", "validate_genesis_envelope", "FoundUpGenesisEnvelope",
               "build_foundup", "FoundUpJob", "fail_closed", "VALVE_OPEN", "verdict"]
    answers, evidence = [], {}
    for (idx, q), anchor in zip(qs, anchors):
        ref = f"modules/x/f{idx}.py:{idx}"
        label = "INFERRED" if idx == 8 else "OBSERVED"
        ans = "decision" if idx == 8 else "yes"
        answers.append(_ans(idx, q, ans=ans, label=label, refs=[ref]))
        # q8 (verdict) is prose-ish; give it a supporting window anyway
        evidence[ref] = f"def {anchor}(job):\n    return {anchor}  # real code line {idx}" if idx != 8 \
            else "The verdict is: proceed. next safest slice named."
    # q4's question names BOTH build_foundup and extract_foundup (an equality claim) -> its evidence
    # must reference BOTH operative symbols, not just one.
    evidence["modules/x/f4.py:4"] = "def build_foundup(job):\n    return extract_foundup(job)  # build == extract"
    return answers, evidence


# --- ACCEPTANCE: verified 8/8 ------------------------------------------------
def test_verified_eight_of_eight():
    answers, evidence = _verified_8()
    r = verify_answer_set(answers, {}, _reader(evidence))
    assert r.verified is True and r.refuted_count == 0
    verdicts = {c.index: c.verdict for c in r.claims}
    assert verdicts[1] == Verdict.OBSERVED_VERIFIED
    assert verdicts[8] == Verdict.INFERRED       # label preserved after verification
    assert r.index_gap_event is None


# --- fabricated / absent evidence -> REFUTED (fail-closed) -------------------
def test_fabricated_ref_absent_is_refuted():
    answers, evidence = _verified_8()
    # Q3's cited file does not exist in the reader (fabricated) -> absent
    del evidence["modules/x/f3.py:3"]
    r = verify_answer_set(answers, {}, _reader(evidence))
    assert r.verified is False
    c3 = next(c for c in r.claims if c.index == 3)
    assert c3.verdict == Verdict.REFUTED and RefuteReason.EVIDENCE_ABSENT in c3.refutations


# --- evidence exists but does not SUPPORT the claim -> REFUTED ---------------
def test_non_supporting_window_is_refuted():
    answers, evidence = _verified_8()
    # Q4 claims build_foundup but the window mentions neither build_foundup nor extract_foundup
    evidence["modules/x/f4.py:4"] = "def unrelated_helper():\n    return 0  # no anchor here"
    r = verify_answer_set(answers, {}, _reader(evidence))
    c4 = next(c for c in r.claims if c.index == 4)
    assert c4.verdict == Verdict.REFUTED and RefuteReason.SUPPORT_NOT_FOUND in c4.refutations


# --- scorecard contradiction -> REFUTED -------------------------------------
def test_scorecard_rejected_path_is_refuted():
    answers, evidence = _verified_8()
    scorecard = {"direct_read_rejected": [{"path": "modules/x/f2.py", "reason": "denied_basename"}]}
    r = verify_answer_set(answers, scorecard, _reader(evidence))
    c2 = next(c for c in r.claims if c.index == 2)
    assert c2.verdict == Verdict.REFUTED and RefuteReason.SCORECARD_CONTRADICTION in c2.refutations


# --- honest NEEDS_VERIFICATION abstention passes through --------------------
def test_needs_verification_abstention_passthrough():
    answers = [_ans(1, "Is the gate wired?", ans="needs_verification", label="NEEDS_VERIFICATION", refs=[])]
    r = verify_answer_set(answers, {}, _reader({}))
    assert r.claims[0].verdict == Verdict.NEEDS_VERIFICATION
    assert r.verified is True                     # an abstention is not a refutation


# --- evidence-bearing answer with NO file:line evidence -> REFUTED ----------
def test_evidence_bearing_with_no_file_line_is_refuted():
    # OBSERVED answer whose only "evidence" is a Run-Trace (not a file:line) -> no anchor to verify
    answers = [_ans(1, "Is build_foundup wired?", refs=["Run Trace:gate_state"])]
    r = verify_answer_set(answers, {}, _reader({}))
    assert r.claims[0].verdict == Verdict.REFUTED
    assert RefuteReason.NO_EVIDENCE_FOR_CLAIM in r.claims[0].refutations


def test_invalid_label_is_refuted():
    answers = [_ans(1, "Is build_foundup wired?", label="PROBABLY", refs=["modules/x/f1.py:1"])]
    r = verify_answer_set(answers, {}, _reader({"modules/x/f1.py:1": "def build_foundup(): ..."}))
    assert r.claims[0].verdict == Verdict.REFUTED and RefuteReason.INVALID_LABEL in r.claims[0].refutations


# --- prose-only claim (no code anchors): support abstains BUT is surfaced ----
def test_prose_only_claim_support_abstains_with_note():
    # question has no code-identifier anchor -> support cannot be decided -> not refuted on support,
    # but the report SURFACES that support was not deterministically checked (not silently "verified")
    answers = [_ans(1, "Is it done and ready?", refs=["modules/x/f1.py:1"])]
    r = verify_answer_set(answers, {}, _reader({"modules/x/f1.py:1": "some prose in the file"}))
    assert r.claims[0].verdict == Verdict.OBSERVED_VERIFIED     # existence + consistency pass
    assert v.NOTE_SUPPORT_UNCHECKABLE in r.claims[0].notes      # support-uncheckable is transparent


# --- CoR R1: SUPPORT must be WHOLE-identifier, not substring -----------------
def test_support_substring_does_not_falsely_verify():
    """CoR R1 (blocker): 'build_foundup' must be a whole token in the window -- a window mentioning
    only 'prebuild_foundups_registry' (substring) must NOT verify the build_foundup claim."""
    answers = [_ans(1, "Does Hermes build_foundup write a scaffold?", refs=["modules/x/f1.py:1"])]
    substr = {"modules/x/f1.py:1": "def prebuild_foundups_registry():\n    return None  # unrelated"}
    r = verify_answer_set(answers, {}, _reader(substr))
    assert r.claims[0].verdict == Verdict.REFUTED and RefuteReason.SUPPORT_NOT_FOUND in r.claims[0].refutations
    # and a REAL whole-token occurrence supports it
    real = {"modules/x/f1.py:1": "def build_foundup(job):\n    return job"}
    r2 = verify_answer_set(answers, {}, _reader(real))
    assert r2.claims[0].verdict == Verdict.OBSERVED_VERIFIED


def test_support_rejects_versioned_sibling_token():
    """'build_foundup' must not be supported by 'build_foundup_v2' (a different identifier)."""
    answers = [_ans(1, "Is build_foundup wired?", refs=["modules/x/f1.py:1"])]
    r = verify_answer_set(answers, {}, _reader({"modules/x/f1.py:1": "x = build_foundup_v2()"}))
    assert r.claims[0].verdict == Verdict.REFUTED and RefuteReason.SUPPORT_NOT_FOUND in r.claims[0].refutations


# --- CoR R1: malformed scorecard must fail closed, not crash ----------------
@pytest.mark.parametrize("bad", [7, "modules/x/f1.py", {"path": "x"}, None])
def test_malformed_scorecard_fields_do_not_crash(bad):
    """CoR R1 (major): scalar/None scorecard sequence fields must coerce to [] (no crash)."""
    answers = [_ans(1, "Is build_foundup wired?", refs=["modules/x/f1.py:1"])]
    reader = _reader({"modules/x/f1.py:1": "def build_foundup(): ..."})
    sc = {"index_gap_detected": True, "direct_read_paths": bad, "direct_read_rejected": bad}
    r = verify_answer_set(answers, sc, reader)                  # must not raise
    assert r.claims[0].verdict == Verdict.OBSERVED_VERIFIED
    # index_gap_event still emitted (advisory), stale_targets coerced to a list
    assert r.index_gap_event is not None and isinstance(r.index_gap_event["stale_targets"], list)


# --- INDEX_GAP: advisory, non-mutating --------------------------------------
def test_index_gap_event_emitted_advisory_non_mutating():
    ev = build_index_gap_event({"index_gap_detected": True,
                                "direct_read_fallback_used": True,
                                "direct_read_paths": ["modules/x/f1.py", "modules/x/f2.py"]})
    assert ev is not None
    assert ev["event"] == "INDEX_GAP" and ev["severity"] == "advisory"
    assert ev["stale_targets"] == ["modules/x/f1.py", "modules/x/f2.py"]
    assert "not performed here" in ev["recommendation"].lower()
    assert "no live wre enqueue" in ev["boundary"].lower()
    assert ev["wre_work_item"]["decision"] == "WORKITEM_PLANNED"
    item = ev["wre_work_item"]["work_item"]
    assert item["recommended_action"] == "targeted_reindex"
    assert item["live_wre_enqueue_performed"] is False
    assert item["no_reindex_performed"] is True
    assert item["no_agentdb_mutation_performed"] is True
    # the event carries NO live enqueue/mutation directive -- it is a pure advisory record
    assert set(ev.keys()) == {"event", "severity", "index_gap_detected", "stale_targets",
                              "recommendation", "boundary", "wre_work_item"}


def test_no_index_gap_no_event():
    assert build_index_gap_event({"index_gap_detected": False}) is None
    assert build_index_gap_event({}) is None


@pytest.mark.parametrize("bad", [None, 7, "x", [1, 2], (1,)])
def test_build_index_gap_event_non_mapping_fails_closed(bad):
    """CoR R2 (minor): the public helper must fail closed to None on a non-Mapping scorecard."""
    assert build_index_gap_event(bad) is None


# --- CoR R2: ubiquitous boilerplate decoy cannot carry support --------------
def test_boilerplate_decoy_anchor_does_not_carry_support():
    """CoR R2 (major): a question that incidentally names a ubiquitous identifier (get_logger) must
    NOT be verified by an unrelated window containing only that boilerplate -- the operative subject
    (create_foundup) must actually appear."""
    answers = [_ans(1, "Does create_foundup write a scaffold after get_logger init?",
                    refs=["modules/unrelated/other.py:12"])]
    decoy = {"modules/unrelated/other.py:12": "logger = get_logger(__name__)\ndef totally_unrelated():\n    pass"}
    r = verify_answer_set(answers, {}, _reader(decoy))
    assert r.claims[0].verdict == Verdict.REFUTED and RefuteReason.SUPPORT_NOT_FOUND in r.claims[0].refutations
    # the operative subject present -> verified
    real = {"modules/unrelated/other.py:12": "logger = get_logger(__name__)\ndef create_foundup(): ..."}
    r2 = verify_answer_set(answers, {}, _reader(real))
    assert r2.claims[0].verdict == Verdict.OBSERVED_VERIFIED


def test_multi_anchor_comparison_decoy_is_refuted():
    """CoR R4 (major): a question naming an operative subject X (build_foundup) AND a comparison
    symbol Y (extract_foundup) must NOT be verified by a window containing only Y -- EVERY operative
    symbol must be referenced, so a decoy/comparison symbol cannot carry a claim about X."""
    answers = [_ans(1, "Does Hermes build_foundup write a scaffold, or just call extract_foundup?",
                    refs=["modules/x/f1.py:1"])]
    only_y = {"modules/x/f1.py:1": "def extract_foundup(module):\n    return read(module)  # extract only"}
    r = verify_answer_set(answers, {}, _reader(only_y))
    assert r.claims[0].verdict == Verdict.REFUTED and RefuteReason.SUPPORT_NOT_FOUND in r.claims[0].refutations
    # both operative symbols present -> verified
    both = {"modules/x/f1.py:1": "def build_foundup(job):\n    return extract_foundup(job)  # build==extract"}
    r2 = verify_answer_set(answers, {}, _reader(both))
    assert r2.claims[0].verdict == Verdict.OBSERVED_VERIFIED


def test_context_noun_not_required_only_operative_symbol():
    """A bare domain noun ('FoundUp') is NOT an operative anchor, so an operative-symbol claim need
    not also contain the domain noun (avoids over-refuting a legitimate window)."""
    answers = [_ans(1, "Does create_foundup write a NEW FoundUp scaffold?", refs=["modules/x/f1.py:1"])]
    # window has the operative symbol but not the bare domain noun 'FoundUp'
    r = verify_answer_set(answers, {}, _reader({"modules/x/f1.py:1": "def create_foundup(spec):\n    return build(spec)"}))
    assert r.claims[0].verdict == Verdict.OBSERVED_VERIFIED


def test_question_with_only_boilerplate_anchor_abstains_with_note():
    """A question whose ONLY identifiers are boilerplate has no operative subject -> support abstains
    (transparency note), not a false verification via the boilerplate."""
    answers = [_ans(1, "Does get_logger run at __init__?", refs=["modules/x/f1.py:1"])]
    r = verify_answer_set(answers, {}, _reader({"modules/x/f1.py:1": "logger = get_logger(__name__)"}))
    assert r.claims[0].verdict == Verdict.OBSERVED_VERIFIED and v.NOTE_SUPPORT_UNCHECKABLE in r.claims[0].notes


def test_direct_read_masked_index_still_verifies_but_records_gap():
    """A claim whose evidence was reachable only via direct-read (index missed it) is still VERIFIED
    (the file is real), but the INDEX_GAP is RECORDED, not discarded -- direct-read != freshness."""
    answers = [_ans(1, "Does build_foundup exist?", refs=["modules/x/f1.py:1"])]
    scorecard = {"index_gap_detected": True, "direct_read_paths": ["modules/x/f1.py"]}
    r = verify_answer_set(answers, scorecard, _reader({"modules/x/f1.py:1": "def build_foundup(): ..."}))
    assert r.claims[0].verdict == Verdict.OBSERVED_VERIFIED     # evidence real -> verified
    assert r.index_gap_event and "modules/x/f1.py" in r.index_gap_event["stale_targets"]


def test_domain_noun_only_decoy_is_not_silently_verified():
    """CoR R5 (blocker): a claim whose question names NO operative symbol -- only bare domain nouns /
    common ALL_CAPS words (FoundUp, WRITER, INDEX) -- must NOT be SILENTLY verified by an unrelated
    window that merely contains one such decoy word. Support cannot be decided, so it ABSTAINS with a
    surfaced NOTE_SUPPORT_UNCHECKABLE (never presented as fully SUPPORT-verified on a ubiquitous word)."""
    answers = [_ans(1, "Is the FoundUp scaffold WRITER isolated so it cannot escape to INDEX mutation?",
                    refs=["modules/z/unrelated.py:9"])]
    decoy = {"modules/z/unrelated.py:9": "INDEX = build_registry()  # bumps a shared counter, no isolation"}
    r = verify_answer_set(answers, {}, _reader(decoy))
    # existence + consistency still pass, but support was NOT checkable -> surfaced, not silent
    assert v.NOTE_SUPPORT_UNCHECKABLE in r.claims[0].notes
    # and a genuine operative-symbol claim in the same shape is still fully verified (no note)
    op = [_ans(1, "Is the writer isolated in isolate_writer()?", refs=["modules/z/unrelated.py:9"])]
    r2 = verify_answer_set(op, {}, _reader({"modules/z/unrelated.py:9": "def isolate_writer(): ..."}))
    assert r2.claims[0].verdict == Verdict.OBSERVED_VERIFIED and not r2.claims[0].notes


@pytest.mark.parametrize("scorecard", [
    {"retrieval_quality": "INDEX_GAP", "direct_read_paths": ["modules/x/f1.py"]},
    {"direct_read_fallback_used": True, "direct_read_paths": ["modules/x/f1.py"]},
])
def test_index_gap_via_retrieval_tier_is_recorded_not_discarded(scorecard):
    """CoR R5 (major): the freshness gap must be recorded when signaled via the INDEX_GAP retrieval
    tier / direct-read fallback -- matching the canonical dryrun gate -- not ONLY via the boolean
    flag. A direct-read-masked claim still verifies WHILE the gap is emitted (direct-read != fresh)."""
    ev = build_index_gap_event(scorecard)
    assert ev is not None and ev["event"] == "INDEX_GAP" and "modules/x/f1.py" in ev["stale_targets"]
    answers = [_ans(1, "Does build_foundup exist?", refs=["modules/x/f1.py:1"])]
    r = verify_answer_set(answers, scorecard, _reader({"modules/x/f1.py:1": "def build_foundup(): ..."}))
    assert r.claims[0].verdict == Verdict.OBSERVED_VERIFIED     # evidence real -> still verified
    assert r.index_gap_event and "modules/x/f1.py" in r.index_gap_event["stale_targets"]  # gap RECORDED


@pytest.mark.parametrize("invisible", ["\x00\x00", "\u200b\u200b", "\x00 \t\n"])
def test_invisible_only_window_fails_closed_as_absent(invisible):
    """CoR R5 (minor): a window of only NUL / zero-width chars has no visible content -- str.strip()
    would treat it as present, so existence must require a genuinely visible glyph and fail closed."""
    answers = [_ans(1, "Is it done and ready?", refs=["modules/x/f1.py:1"])]
    r = verify_answer_set(answers, {}, _reader({"modules/x/f1.py:1": invisible}))
    assert r.claims[0].verdict == Verdict.REFUTED and RefuteReason.EVIDENCE_ABSENT in r.claims[0].refutations


# --- fail-closed aggregation: any refuted claim => set not verified ---------
def test_fail_closed_any_refuted_claim():
    answers, evidence = _verified_8()
    del evidence["modules/x/f5.py:5"]              # one absent
    r = verify_answer_set(answers, {}, _reader(evidence))
    assert r.verified is False and r.refuted_count == 1


def test_reader_that_raises_fails_closed_not_crash():
    def boom(_ref):
        raise RuntimeError("reader blew up")
    answers = [_ans(1, "Is build_foundup wired?", refs=["modules/x/f1.py:1"])]
    r = verify_answer_set(answers, {}, boom)       # must not raise
    assert r.claims[0].verdict == Verdict.REFUTED and RefuteReason.EVIDENCE_ABSENT in r.claims[0].refutations


# --- empty input no-op ------------------------------------------------------
def test_empty_answers_is_verified_empty():
    r = verify_answer_set([], {}, _reader({}))
    assert r.verified is True and r.claims == [] and r.refuted_count == 0


# --- CoR R3: malformed answers must fail closed, not crash ------------------
def test_non_mapping_answer_entry_is_refuted_not_crash():
    """CoR R3 (major): a poison non-mapping entry (scalar/str from partial model output) must become
    a fail-closed REFUTED claim, never an uncaught AttributeError (a crash is a bypass)."""
    good = _ans(1, "Is build_foundup wired?", refs=["modules/x/f1.py:1"])
    r = verify_answer_set([good, "poison", 7], {}, _reader({"modules/x/f1.py:1": "def build_foundup(): ..."}))
    assert r.verified is False                      # the poison entries refute the set
    poison = [c for c in r.claims if c.verdict == Verdict.REFUTED]
    assert len(poison) == 2 and all(RefuteReason.MALFORMED_ANSWER in c.refutations for c in poison)


@pytest.mark.parametrize("bad", [None, 7, "notalist", {"index": 1}])
def test_non_iterable_answers_fails_closed_empty(bad):
    """A non-list/tuple `answers` coerces to an empty (vacuously verified) report -- never crashes."""
    r = verify_answer_set(bad, {}, _reader({}))     # must not raise
    assert r.claims == [] and r.verified is True


# --- purity / ascii ---------------------------------------------------------
def test_module_is_pure_no_io():
    src = Path(v.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imported.add((n.module or "").split(".")[0])
    forbidden = {"subprocess", "os", "socket", "requests", "urllib", "http", "sys"}
    assert not (imported & forbidden), f"verifier must be pure (I/O injected): {imported & forbidden}"
    called = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            called.add(n.func.id)
    assert not (called & {"open", "eval", "exec", "compile", "__import__"})


def test_doc_is_ascii_clean():
    raw = Path(v.__file__).read_bytes()
    assert not [i for i, b in enumerate(raw) if b > 127]
    assert raw.count(0) == 0
