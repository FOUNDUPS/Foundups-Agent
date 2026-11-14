#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the RedDog Determine question/answer CONTRACT.

Slice: REDDOG_DETERMINE_QUESTION_ANSWER_CONTRACT_PHASE1
WSP:   50, 97

Acceptance: the FoundUp-creation audit prompt (8 Determine questions) must produce
exactly 8 answers; missing evidence -> explicit NEEDS_VERIFICATION, never omitted;
schema repair cannot collapse answers into summary prose.
"""

from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import reddog_determine_answer_contract as c
from modules.communication.moltbot_bridge.src.reddog_determine_answer_contract import (
    ReasonCode,
    assert_repair_preserves,
    build_answer_template,
    is_determine_list_wellformed,
    normalize_evidence_ref,
    parse_determine_questions,
    validate_answer_set,
)

# --- FoundUp-creation audit fixture (8 Determine questions) ------------------
AUDIT_PROMPT = """Audit the FoundUp creation monorepo WSP_109 execution path.

Required direct-read targets:
- WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md
- modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py
- modules/foundups/agent/src/hermes_foundup_job_executor.py
- modules/communication/moltbot_bridge/src/foundup_job_contract.py

Determine:
1. Does any code autonomously write a NEW FoundUp scaffold to disk today?
2. Is the OpenClaw genesis gate BUILT and wired into dispatch?
3. Is the genesis gate input-starved (nothing populates the envelope)?
4. Does Hermes build_foundup equal extract_foundup of an existing module?
5. Does FoundUpJob carry a first-class create action with create fields?
6. Does the RedDog spine fail-closed (no_mutation / no_execution by default)?
7. Is the execution valve CLOSED by default?
8. What is the verdict and the next safest slice?

End with WSP_15 priority and next safest slice.
"""


def _answer(idx, text, ans="yes", label="OBSERVED", ev=None):
    return {"index": idx, "question_text": text, "answer": ans, "wsp97_label": label,
            "evidence_refs": ev if ev is not None else [f"modules/x/file_{idx}.py:{idx * 10}"]}


def _valid_answers(questions):
    out = []
    for q in questions:
        if q.index == 8:  # a decision question
            out.append(_answer(8, q.text, ans="decision", label="INFERRED",
                                ev=["docs/audits/architecture/REDDOG_FOUNDUP_CREATION_EXECUTION_PATH_AUDIT_PHASE1.md:200"]))
        else:
            out.append(_answer(q.index, q.text))
    return out


# --- parsing ----------------------------------------------------------------
def test_parses_exactly_8_determine_questions() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    assert len(qs) == 8
    assert [q.index for q in qs] == list(range(1, 9))
    assert "autonomously write a NEW FoundUp scaffold" in qs[0].text
    assert qs[7].text.startswith("What is the verdict")


def test_no_determine_block_returns_empty() -> None:
    assert parse_determine_questions("Just a prompt with no determine list.") == []
    r = validate_answer_set([], [])
    assert r.valid is False and ReasonCode.NO_DETERMINE_BLOCK in r.reason_codes


# --- ACCEPTANCE: 8 questions -> exactly 8 answers ---------------------------
def test_foundup_audit_produces_exactly_8_answers() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    r = validate_answer_set(qs, _valid_answers(qs))
    assert r.valid is True, r.reason_codes
    assert r.question_count == 8 and r.answered_count == 8


# --- CONSOLIDATED ACCEPTANCE (012-required, single assertion block) ---------
def test_acceptance_foundup_audit_fixture() -> None:
    """012 acceptance gate: the FoundUp-creation audit fixture (a) parses exactly 8
    Determine questions, (b) validates exactly 8 answers, (c) rejects 7/8, and
    (d) rejects a summary-prose collapse of the answer set."""
    qs = parse_determine_questions(AUDIT_PROMPT)

    # (a) parses exactly 8
    assert len(qs) == 8 and [q.source_number for q in qs] == list(range(1, 9))

    # (b) validates exactly 8 answers
    ok = validate_answer_set(qs, _valid_answers(qs))
    assert ok.valid is True and ok.question_count == 8 and ok.answered_count == 8

    # (c) rejects 7/8 (one Determine item unanswered)
    seven = _valid_answers(qs)[:-1]
    r7 = validate_answer_set(qs, seven)
    assert r7.valid is False and ReasonCode.MISSING_ANSWER in r7.reason_codes
    assert 8 in r7.per_question

    # (d) rejects summary prose that collapses the answers into one
    prose = [{"index": 1, "question_text": qs[0].text, "answer": "partial",
              "wsp97_label": "INFERRED", "evidence_refs": ["modules/x/y.py:1"]}]
    rc = assert_repair_preserves(qs, _valid_answers(qs), prose)
    assert rc.valid is False and ReasonCode.REPAIR_COLLAPSED_TO_PROSE in rc.reason_codes


# --- missing answer ---------------------------------------------------------
def test_missing_answer_fails() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = _valid_answers(qs)[:-1]  # drop Q8
    r = validate_answer_set(qs, ans)
    assert r.valid is False and ReasonCode.MISSING_ANSWER in r.reason_codes
    assert 8 in r.per_question


# --- reordered answer -------------------------------------------------------
def test_reordered_answer_fails() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = _valid_answers(qs)
    ans[0], ans[1] = ans[1], ans[0]  # swap Q1/Q2 order
    r = validate_answer_set(qs, ans)
    assert r.valid is False and ReasonCode.ANSWER_REORDERED in r.reason_codes


# --- unlabeled answer -------------------------------------------------------
def test_unlabeled_answer_fails() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = _valid_answers(qs)
    ans[2]["wsp97_label"] = ""
    r = validate_answer_set(qs, ans)
    assert r.valid is False and ReasonCode.MISSING_LABEL in r.reason_codes


def test_invalid_label_fails() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = _valid_answers(qs)
    ans[2]["wsp97_label"] = "PROBABLY"
    r = validate_answer_set(qs, ans)
    assert r.valid is False and ReasonCode.INVALID_LABEL in r.reason_codes


# --- answer without evidence ------------------------------------------------
def test_answer_without_evidence_fails() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = _valid_answers(qs)
    ans[3]["evidence_refs"] = []  # non-NEEDS_VERIFICATION with no evidence
    r = validate_answer_set(qs, ans)
    assert r.valid is False and ReasonCode.MISSING_EVIDENCE in r.reason_codes


# --- missing evidence -> NEEDS_VERIFICATION accepted (not omitted) ----------
def test_missing_evidence_becomes_needs_verification_not_omitted() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = _valid_answers(qs)
    ans[4] = {"index": 5, "question_text": qs[4].text, "answer": "needs_verification",
              "wsp97_label": "NEEDS_VERIFICATION", "evidence_refs": []}
    r = validate_answer_set(qs, ans)
    assert r.valid is True, r.reason_codes  # explicit NEEDS_VERIFICATION is allowed


def test_needs_verification_with_evidence_is_misuse() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = _valid_answers(qs)
    ans[4] = {"index": 5, "question_text": qs[4].text, "answer": "needs_verification",
              "wsp97_label": "NEEDS_VERIFICATION", "evidence_refs": ["modules/x.py:1"]}
    r = validate_answer_set(qs, ans)
    assert r.valid is False and ReasonCode.NEEDS_VERIFICATION_MISUSE in r.reason_codes


# --- invented answer --------------------------------------------------------
def test_invented_answer_fails() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = _valid_answers(qs)
    ans.append(_answer(9, "an invented question not in the Determine list"))
    r = validate_answer_set(qs, ans)
    assert r.valid is False and ReasonCode.INVENTED_ANSWER in r.reason_codes


def test_altered_question_text_fails() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = _valid_answers(qs)
    ans[0]["question_text"] = "a paraphrased version of the question"
    r = validate_answer_set(qs, ans)
    assert r.valid is False and ReasonCode.QUESTION_TEXT_ALTERED in r.reason_codes


# --- evidence normalization (012 addition) ----------------------------------
def test_evidence_normalization() -> None:
    assert normalize_evidence_ref("modules/x/y.py:42") == "modules/x/y.py:42"
    assert normalize_evidence_ref("modules/x/y.py#L42") == "modules/x/y.py:42"  # #Lline -> :line
    assert normalize_evidence_ref("WSP_109.md:5") == "WSP_109.md:5"             # whitelisted ext + line
    assert normalize_evidence_ref("Run Trace:gate_state") == "run_trace:gate_state"
    # vague refs rejected
    assert normalize_evidence_ref("the file says so") is None
    assert normalize_evidence_ref("somewhere in the code") is None
    assert normalize_evidence_ref("build_foundup") is None
    assert normalize_evidence_ref("x.py:notaline") is None


def test_evidence_requires_line_and_rejects_fabrication_and_traversal() -> None:
    # BLOCKER (CoR): a bare path with no line is NOT evidence-grade
    assert normalize_evidence_ref("modules/x/y.py") is None
    assert normalize_evidence_ref("WSP_framework/src/WSP_109.md") is None
    # dotted identifiers that are not files must be rejected
    assert normalize_evidence_ref("Orchestrator.dispatch") is None
    assert normalize_evidence_ref("a.b") is None
    assert normalize_evidence_ref("valve.closed:1") is None       # ".closed" not a code ext
    assert normalize_evidence_ref("genesis_gate.wired") is None
    # traversal / absolute / line-0 rejected
    assert normalize_evidence_ref("../../.env:1") is None
    assert normalize_evidence_ref("/etc/passwd:1") is None
    assert normalize_evidence_ref("modules/x.py:0") is None


def test_unicode_digit_line_locator_rejected() -> None:
    """MAJOR (CoR R20): a NON-ASCII line locator (Arabic-Indic / fullwidth / extended-Arabic
    digit) is unresolvable junk -- no editor/grep/LSP can resolve `file.py:<unicode-digit>` --
    and must be rejected at the shape gate (same class as `x.py:notaline`), not int()-coerced
    into a valid-looking file:line."""
    # chr() keeps this SOURCE pure-ASCII; the runtime chars are real Unicode digits.
    for cp in (0x0669, 0xFF15, 0x06F7):  # Arabic-Indic 9, fullwidth 5, extended-Arabic 7
        ch = chr(cp)
        assert normalize_evidence_ref("modules/x.py:" + ch) is None
        assert normalize_evidence_ref("modules/x.py#L" + ch) is None
    # a whole answer set 'evidenced' only by unicode-digit refs must NOT validate as complete
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = [{"index": q.index, "question_text": q.text, "answer": "yes",
            "wsp97_label": "OBSERVED", "evidence_refs": ["modules/x/y.py:" + chr(0x0669)]}
           for q in qs]
    r = validate_answer_set(qs, ans)
    assert r.valid is False and ReasonCode.VAGUE_EVIDENCE in r.reason_codes


@pytest.mark.parametrize("bad_refs", [7, {"x": 1}, "modules/x.py:1", None, True])
def test_scalar_evidence_refs_fails_closed_not_crash(bad_refs) -> None:
    """CoR robustness: a non-list `evidence_refs` (scalar/dict) must coerce to [] (-> no
    evidence -> MISSING/VAGUE), never raise a TypeError from iterating a non-iterable."""
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = _valid_answers(qs)
    ans[3]["evidence_refs"] = bad_refs  # Q4 answer carries a non-list evidence_refs
    r = validate_answer_set(qs, ans)  # must not raise
    assert r.valid is False
    assert (ReasonCode.MISSING_EVIDENCE in r.reason_codes
            or ReasonCode.VAGUE_EVIDENCE in r.reason_codes)


def test_non_integer_index_fails_closed_not_crash() -> None:
    """CoR R20 robustness: a non-integer answer index ('3abc') must fail CLOSED (coerced to 0
    -> out of the 1..N range -> INVENTED_ANSWER, real question stays MISSING_ANSWER), never
    raise an uncaught ValueError inside the validator."""
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = _valid_answers(qs)
    ans[2]["index"] = "3abc"  # Q3's answer now has a non-integer index
    r = validate_answer_set(qs, ans)  # must not raise
    assert r.valid is False
    assert ReasonCode.INVENTED_ANSWER in r.reason_codes
    assert 3 in r.per_question and ReasonCode.MISSING_ANSWER in r.per_question[3]


def test_fabricated_dotted_evidence_8answer_set_fails() -> None:
    """BLOCKER (CoR): an 8/8 set 'evidenced' by fabricated dotted tokens must NOT validate."""
    qs = parse_determine_questions(AUDIT_PROMPT)
    fake = ["Orchestrator.dispatch", "genesis_gate.wired", "envelope.py", "build_foundup.py",
            "a.b", "reddog.spine", "valve.closed", "verdict.md"]
    ans = []
    for q in qs:
        ans.append({"index": q.index, "question_text": q.text, "answer": "yes",
                    "wsp97_label": "OBSERVED", "evidence_refs": [fake[q.index - 1]]})
    r = validate_answer_set(qs, ans)
    assert r.valid is False
    assert ReasonCode.VAGUE_EVIDENCE in r.reason_codes


def test_observed_requires_file_line_not_only_run_trace() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = _valid_answers(qs)
    ans[0] = {"index": 1, "question_text": qs[0].text, "answer": "yes",
              "wsp97_label": "OBSERVED", "evidence_refs": ["Run Trace:gate_state"]}  # no file:line
    r = validate_answer_set(qs, ans)
    assert r.valid is False and ReasonCode.LABEL_ANSWER_COUPLING in r.reason_codes


# --- parser miscount regressions (CoR) --------------------------------------
def test_same_line_fusion_is_flagged_malformed_not_guessed() -> None:
    """Same-line fusion is ambiguous (fused item vs authored intra-question) -> fail-closed
    MALFORMED (one item per physical line), never silently split or absorbed."""
    prompt = "Determine:\n1. Q one?\n2. Q two?\n3. Q three? 4. Q four?\n5. Q five?\n"
    qs = parse_determine_questions(prompt)
    assert is_determine_list_wellformed(qs) is False
    r = validate_answer_set(qs, build_answer_template(qs))
    assert r.valid is False and ReasonCode.DETERMINE_LIST_MALFORMED in r.reason_codes


def test_final_line_fusion_flagged_malformed() -> None:
    """BLOCKER-class (CoR R2/R5/R7): a fused final line must NOT silently drop the verdict
    item; with one-item-per-line it is flagged MALFORMED (contiguity and/or fusion)."""
    prompt = ("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n"
              "7. Is the valve closed by default? 8. What is the verdict and next slice?\n")
    qs = parse_determine_questions(prompt)
    assert is_determine_list_wellformed(qs) is False


def test_imperative_period_fusion_flagged_malformed() -> None:
    """BLOCKER (CoR R7): an imperative item ending in '.' fused to the next must not be
    silently absorbed -> MALFORMED."""
    prompt = ("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n"
              "7. Confirm the execution valve is closed by default. 8. State the verdict.\n")
    qs = parse_determine_questions(prompt)
    assert is_determine_list_wellformed(qs) is False
    r = validate_answer_set(qs, build_answer_template(qs))
    assert r.valid is False and ReasonCode.DETERMINE_LIST_MALFORMED in r.reason_codes


@pytest.mark.parametrize("boundary", [
    "7. Confirm the valve is closed by default 8. State the verdict.",   # bare word
    "7. Confirm the valve is closed, 8. State the verdict.",             # comma
    "7. Confirm the following: 8. State the verdict.",                   # colon
    "7. Confirm the valve (per spec) 8. State the verdict.",            # close-paren
    "7. Confirm the valve is closed; 8. State the verdict.",            # semicolon
])
def test_non_terminator_uppercase_fusion_flagged_malformed(boundary: str) -> None:
    """BLOCKER (CoR R8): fusion after comma/colon/semicolon/paren/bare-word, where the
    second item begins with a capital (a new Determine clause), must be MALFORMED."""
    prompt = "Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n" + boundary + "\n"
    qs = parse_determine_questions(prompt)
    assert is_determine_list_wellformed(qs) is False
    r = validate_answer_set(qs, build_answer_template(qs))
    assert r.valid is False and ReasonCode.DETERMINE_LIST_MALFORMED in r.reason_codes


def test_inline_ordinal_in_question_body_flagged_malformed() -> None:
    """MAXIMALLY FAIL-CLOSED (CoR R10): ANY inline `N. ` ordinal in a question body means a
    possible fused item -> MALFORMED (author reworods the number, e.g. 'WSP 3' / 'stage 8')."""
    for body in ("1. Does deployment reach stage 8. cleanly by default?",
                 "1. Map the finding to WSP 3. priority tier for routing?"):
        _assert_malformed("Determine:\n" + body + "\n")


def test_wrapped_continuation_starting_with_next_ordinal_flagged_malformed() -> None:
    """MAJOR (CoR R12): a question wrapping onto a line that starts with the next ordinal
    must not silently truncate + fabricate -> MALFORMED (items must end in ? ! . )."""
    _assert_malformed("Determine:\n1. Is X true?\n2. Is Y true?\n"
                      "3. Given the above, does the system behave\n4. correctly under load?\n")
    _assert_malformed("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n"
                      "7. Is the valve CLOSED by default and does it\n8. remain closed across restarts?\n")


def test_spaceless_wrap_fold_flagged_malformed() -> None:
    """BLOCKER (CoR R13): a spaceless next-ordinal on a wrap line ('8.remain' / '8)remain')
    must also trip the fusion safety net -> MALFORMED, not silently swallowed."""
    _assert_malformed("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n"
                      "7. Is the valve CLOSED by default and does it\n8.remain closed across restarts?\n")
    _assert_malformed("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n"
                      "7. Is the valve CLOSED by default and does it\n8)remain closed across restarts?\n")


def test_unicode_control_separator_fusion_flagged_malformed() -> None:
    """MAJOR (CoR R16): a fused line joined by a Unicode/control line boundary (which
    str.splitlines would split) must stay one physical line and be caught -> MALFORMED."""
    for cp in (0x2028, 0x2029, 0x85, 0x0b, 0x0c, 0x1c, 0x1d, 0x1e):
        sep = chr(cp)
        prompt = ("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n"
                  "7. Is the valve closed by default?" + sep + "8. What is the verdict?\n")
        qs = parse_determine_questions(prompt)
        assert is_determine_list_wellformed(qs) is False, f"sep U+{cp:04X} not flagged"


def test_crlf_line_endings_parse_correctly() -> None:
    prompt = "Determine:\r\n1. a?\r\n2. b?\r\n3. c?\r\n"
    qs = parse_determine_questions(prompt)
    assert len(qs) == 3 and is_determine_list_wellformed(qs) is True


def test_digit_initial_fused_body_after_terminator_flagged_malformed() -> None:
    """MAJOR (CoR R15): a fused ordinal whose body begins with a DIGIT ('?8.2nd') must not
    masquerade as a decimal and evade the fusion net -> MALFORMED."""
    _assert_malformed("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n"
                      "7. Is the execution valve closed by default?8.2nd: state the verdict?\n")


def test_digit_initial_wrap_after_unterminated_item_flagged_malformed() -> None:
    """BLOCKER (CoR R17): a digit-initial body ('8.2 State') wrapping an UNTERMINATED item
    must not be silently swallowed -> MALFORMED."""
    for body in ("8.2 State the verdict and the next safest slice",
                 "8)2 State the verdict", "8.0 verdict and next slice", "9.9 verdict"):
        _assert_malformed("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n"
                          "7. Is the execution valve closed by default and does it hold\n" + body + "\n")


def test_blank_preceded_digit_initial_ordinal_flagged_malformed() -> None:
    """BLOCKER (CoR R21): a digit-initial ordinal body ('8.2nd', '8)2', zero-padded '08.')
    preceded by a BLANK line (which reset pending_blank and previously skipped the fold-ordinal
    guard) was silently dropped, under-counting the verdict item. It must fail closed MALFORMED
    -- the ordinal-initial check now runs regardless of blank / open-item state."""
    for body in ("8.2nd item: what is the verdict and the next safest slice?",
                 "8)2 State the verdict and next slice?",
                 "08. What is the verdict and the next safest slice?"):
        _assert_malformed("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n"
                          "7. Is the execution valve CLOSED by default?\n\n" + body + "\n")


def test_lone_zero_ordinal_aside_after_blank_stays_benign() -> None:
    """Contrast to R21: a lone '0.' aside (value 0, NOT a 1-based item) after a blank line is a
    benign skipped aside, not a dropped item -- the clean 1..N list still validates."""
    qs = parse_determine_questions("Determine:\n1. a?\n2. b?\n3. c?\n\n0. a trailing aside note\n")
    assert [q.source_number for q in qs] == [1, 2, 3]
    assert is_determine_list_wellformed(qs) is True


def test_same_line_digit_initial_fusion_non_question_boundary_flagged_malformed() -> None:
    """BLOCKER (CoR R18): same-line fusion with a digit-initial second body after a '.'/','/
    ':'/bare-word boundary ('...closed. 8.2 State...') must be MALFORMED."""
    for boundary in (". 8.2 State the verdict?", ", 8.2 State the verdict?",
                     ": 8.2 State the verdict?", " 8.2 State the verdict?", " 8)2 State the verdict?"):
        _assert_malformed("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n"
                          "7. Confirm the execution valve is closed" + boundary + "\n")


def test_decimal_after_word_still_not_flagged() -> None:
    """A real decimal (not preceded by ? or !) stays prose, not fusion."""
    qs = parse_determine_questions("Determine:\n1. Is the ratio 1.5 or higher and is v2.0 shipped?\n")
    assert len(qs) == 1 and is_determine_list_wellformed(qs) is True


def test_terminated_consecutive_items_not_flagged_as_wrap() -> None:
    """The normal case: consecutive items that each end in '?' are real items, not wraps."""
    qs = parse_determine_questions("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n")
    assert len(qs) == 4 and is_determine_list_wellformed(qs) is True


def test_zero_numbered_item_does_not_bypass_malformed_gate() -> None:
    """BLOCKER (CoR R11): a `0.` item must not disable the contiguity/fusion checks."""
    # 0 + same-line fusion
    _assert_malformed("Determine:\n0. context?\n1. Q one?\n2. Q two?\n3. Q three? 4. Q four?\n5. Q five?\n")
    # 0 + gap (real item 4 dropped)
    _assert_malformed("Determine:\n0. preamble?\n1. a?\n2. b?\n3. c?\n5. e?\n6. f?\n7. g?\n8. h?\n")
    # 0 + duplicate
    _assert_malformed("Determine:\n0. p?\n1. a?\n2. b?\n2. b-again?\n3. c?\n")


def test_zero_prefixed_line_is_not_treated_as_item() -> None:
    """A literal '0.' line is not a Determine item (numbers are 1-based); a clean 1..N list
    with a leading '0.' aside still parses to the N real items and validates."""
    qs = parse_determine_questions("Determine:\n0. this is a preamble aside\n1. a?\n2. b?\n3. c?\n")
    assert [q.source_number for q in qs] == [1, 2, 3]
    assert is_determine_list_wellformed(qs) is True


def test_spaceless_fusion_flagged_malformed() -> None:
    """BLOCKER (CoR R10): a spaceless boundary `default?8.` must NOT silently drop item 8."""
    for boundary in ("7. Is the execution valve closed by default?8. State the verdict.",
                     "7. Confirm the valve is closed.8. State the verdict.",
                     '7. Confirm the valve is closed 8. "State" the verdict.'):
        _assert_malformed("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n" + boundary + "\n")


def test_decimal_and_version_numbers_not_flagged() -> None:
    """Decimals/versions ('3.14', '2.0') have no space after the dot -> not fusion."""
    qs = parse_determine_questions("Determine:\n1. Is 3.14 the value of pi and is v2.0 shipped?\n")
    assert len(qs) == 1 and is_determine_list_wellformed(qs) is True


def test_authored_intra_question_ordinal_flagged_malformed() -> None:
    """MAJOR (CoR R7): a single item containing '? <N+1>.' must not fabricate a phantom
    item -> flagged MALFORMED rather than silently over-counted."""
    prompt = "Determine:\n1. a?\n2. b?\n3. First part? 4. really part of 3?\n"
    qs = parse_determine_questions(prompt)
    assert is_determine_list_wellformed(qs) is False


def test_stopword_in_wrapped_continuation_not_truncated() -> None:
    """MAJOR (CoR R2): a wrapped line starting 'return:' must not truncate the list."""
    prompt = ("Determine:\n1. a?\n2. b?\n3. Is behavior X, and does it\n"
              "return: the correct envelope when input-starved?\n4. d?\n5. e?\n")
    qs = parse_determine_questions(prompt)
    assert len(qs) == 5  # Q4/Q5 not discarded by the 'return:' continuation
    assert "return: the correct envelope" in qs[2].text  # continuation folded into Q3


def test_slash_path_without_file_extension_rejected() -> None:
    """MAJOR (CoR R2): 'orchestrator/dispatch:1' (slash, no file ext) is fabricated evidence."""
    assert normalize_evidence_ref("orchestrator/dispatch:1") is None
    assert normalize_evidence_ref("genesis_gate/wired:2") is None
    assert normalize_evidence_ref("modules/foundups/paccess_001:5") is None  # directory, not a file
    assert normalize_evidence_ref("modules/x/y.py:5") == "modules/x/y.py:5"


def test_midlist_note_after_blank_does_not_truncate() -> None:
    """BLOCKER (CoR R3): a blank + prose note between items must not drop the tail."""
    prompt = ("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n\n"
              "(Note: the following items concern runtime state.)\n"
              "5. e?\n6. f?\n7. g?\n8. verdict?\n\nEnd with WSP_15 priority.\n")
    qs = parse_determine_questions(prompt)
    assert len(qs) == 8
    assert [q.source_number for q in qs] == list(range(1, 9))
    assert qs[7].text == "verdict?"  # trailing 'End with...' skipped, not folded


def test_trailing_end_with_after_blank_is_skipped() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    assert len(qs) == 8
    assert "End with" not in qs[7].text  # not polluted into the last question


def test_run_trace_only_evidence_fails_for_all_evidence_bearing_labels() -> None:
    """MAJOR (CoR R3): a whole audit 'evidenced' only by Run Trace fields must NOT validate."""
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = []
    for q in qs:
        ans.append({"index": q.index, "question_text": q.text, "answer": "yes",
                    "wsp97_label": "INFERRED", "evidence_refs": [f"Run Trace:field_{q.index}"]})
    r = validate_answer_set(qs, ans)
    assert r.valid is False and ReasonCode.LABEL_ANSWER_COUPLING in r.reason_codes


def test_run_trace_supplementary_to_file_line_is_allowed() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = _valid_answers(qs)
    ans[0]["evidence_refs"] = ["modules/x/y.py:5", "Run Trace:gate_state"]  # file:line + run trace
    r = validate_answer_set(qs, ans)
    assert r.valid is True, r.reason_codes


def test_no_space_after_separator_item_recovered() -> None:
    """BLOCKER (CoR R5): `8.verdict?` (no space after the dot) must still be item 8, not
    absorbed into Q7 -- while a decimal like `3.14` is NOT a numbered item."""
    prompt = ("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n"
              "7. Is the execution valve CLOSED by default?\n"
              "8.What is the verdict and the next safest slice?\n")
    qs = parse_determine_questions(prompt)
    assert len(qs) == 8
    assert [q.source_number for q in qs] == list(range(1, 9))
    assert qs[7].text.startswith("What is the verdict")


def test_decimal_is_not_a_numbered_item() -> None:
    # a decimal whose integer part != this item's (num+1) stays prose, not a phantom item.
    prompt = "Determine:\n1. Is 3.14 the value of pi in this file?\n2. b?\n3. c?\n"
    qs = parse_determine_questions(prompt)
    assert len(qs) == 3 and is_determine_list_wellformed(qs) is True
    assert "3.14" in qs[0].text


def test_decimal_equal_to_num_plus_one_is_flagged_failclosed() -> None:
    """DOCUMENTED LIMITATION: a decimal whose integer part coincidentally equals the item's
    num+1 ('2. Is 3.14 ...' -> 3==2+1) is shape-identical to a fused item 3, so it is
    flagged MALFORMED (fail-closed). Rare; a real audit prompt does not hit it. Reword the
    number (e.g. 'pi' or '3.1416')."""
    qs = parse_determine_questions("Determine:\n1. a?\n2. Is 3.14 the value of pi?\n3. c?\n")
    assert is_determine_list_wellformed(qs) is False


def _assert_malformed(prompt: str) -> None:
    qs = parse_determine_questions(prompt)
    assert is_determine_list_wellformed(qs) is False
    r = validate_answer_set(qs, build_answer_template(qs))
    assert r.valid is False and ReasonCode.DETERMINE_LIST_MALFORMED in r.reason_codes


def test_overindented_trailing_item_flagged_malformed() -> None:
    """BLOCKER (CoR R4/R9): an over-indented numbered line is ambiguous (mis-indented item
    vs nested sub-item) -> MALFORMED, never silently absorbed OR materialized."""
    _assert_malformed("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n"
                      "7. Is the execution valve CLOSED by default?\n"
                      "  8. What is the verdict and the next safest slice?\n")


def test_inconsistent_indentation_flagged_malformed() -> None:
    """BLOCKER (CoR R4): items at inconsistent indentation must not collapse/guess."""
    _assert_malformed("Determine:\n1. a?\n  2. b?\n  3. c?\n  4. d?\n")


def test_sequential_nested_subitem_flagged_malformed() -> None:
    """BLOCKER (CoR R9): a nested sub-item numbered to CONTINUE the count (over-count risk)
    must be MALFORMED, not materialized into a phantom question."""
    _assert_malformed("Determine:\n1. a?\n2. b?\n   3. an over-indented sub-detail of item two\n"
                      "4. c?\n5. d?\n6. e?\n7. f?\n8. g?\n9. verdict?\n")


def test_overindented_item_after_blank_line_flagged_malformed() -> None:
    """MAJOR (CoR R14): a blank line before an over-indented item must NOT bypass the
    over-indent gate (over-count / phantom item)."""
    _assert_malformed("Determine:\n1. Does code write a scaffold?\n2. Is the genesis gate built:\n\n"
                      "   3. is dispatch wired?\n4. Is it input-starved?\n5. Does build==extract?\n"
                      "6. Fail-closed by default?\n7. Valve closed?\n8. Verdict?\n")


def test_nonsequential_indented_lowercase_flagged_malformed() -> None:
    """MAJOR (CoR R9): a non-sequential over-indented line (under-count risk) must be
    MALFORMED, not silently folded away."""
    _assert_malformed("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n7. g?\n"
                      "    80. and finally state the verdict and next slice\n")


def test_degenerate_dotfile_evidence_rejected() -> None:
    """MINOR (CoR R4): '.py:1' / '....py:1' have no real basename."""
    assert normalize_evidence_ref(".py:1") is None
    assert normalize_evidence_ref("....py:1") is None
    assert normalize_evidence_ref("a.py:1") == "a.py:1"


def test_sequential_ordinal_in_prose_not_fabricated_as_item() -> None:
    """MAJOR (CoR R6): a next-ordinal token inside a final question's prose must NOT
    fabricate a phantom item or truncate the real question."""
    prompt = ("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n"
              "7. Does deployment reach stage 8. cleanly?\n")
    qs = parse_determine_questions(prompt)
    assert len(qs) == 7
    assert [q.source_number for q in qs] == list(range(1, 8))
    assert qs[6].text == "Does deployment reach stage 8. cleanly?"  # intact, not split


def test_sequential_ordinal_in_prose_midlist_not_fabricated() -> None:
    prompt = "Determine:\n1. a?\n2. Map the finding to WSP 3. priority tier?\n3. c?\n"
    qs = parse_determine_questions(prompt)
    assert len(qs) == 3
    assert qs[1].text == "Map the finding to WSP 3. priority tier?"  # 'WSP 3.' is prose, not item 3


def test_non_sequential_inline_number_not_split() -> None:
    """MINOR (CoR R3): an inline number that is not exactly N+1 stays as body text (no gap-fill)."""
    prompt = "Determine:\n1. a?\n2. b?\n3. Does step 6. matter here?\n4. d?\n"
    qs = parse_determine_questions(prompt)
    assert len(qs) == 4  # '6.' inside Q3 is NOT promoted to an item
    assert [q.source_number for q in qs] == [1, 2, 3, 4]
    assert "6. matter here" in qs[2].text


def test_nested_sublist_flagged_malformed() -> None:
    """A nested numbered sub-list is an over-indented numbered line -> MALFORMED (Determine
    lists must be flat; author flattens or de-numbers the sub-bullets)."""
    _assert_malformed("Determine:\n1. Q one?\n2. Q two, consider:\n   1. sub factor a\n"
                      "   2. sub factor b\n3. Q three?\n")


def test_gapped_source_numbers_malformed() -> None:
    prompt = "Determine:\n1. a?\n2. b?\n4. c?\n"
    qs = parse_determine_questions(prompt)
    assert is_determine_list_wellformed(qs) is False


# --- fence-blindness regressions (CoR R19) ----------------------------------
def test_trailing_fenced_numbered_block_not_absorbed() -> None:
    """MAJOR (CoR R19): a trailing fenced sample-output block whose numbered lines RESTART at 1
    (values <= the real count, so they cannot be a dropped tail) must NOT be absorbed as
    Determine questions (over-count). The audit stays exactly 8 and validates; an answer set
    padded with an invented index is rejected. (A fenced sample numbered to CONTINUE the list
    is a different, ambiguous case -> MALFORMED, covered by the R22 test below.)"""
    fenced = "```"
    prompt = (AUDIT_PROMPT.rstrip("\n") + "\n\nSample expected output format:\n"
              + fenced + "\n1. finding alpha resolved.\n2. finding beta resolved.\n" + fenced + "\n")
    qs = parse_determine_questions(prompt)
    assert len(qs) == 8
    assert [q.source_number for q in qs] == list(range(1, 9))
    assert is_determine_list_wellformed(qs) is True
    # the correct 8-answer audit validates (the fenced sample was ignored, not absorbed)
    assert validate_answer_set(qs, _valid_answers(qs)).valid is True
    # an answer set padded with an invented index is rejected
    padded = _valid_answers(qs) + [
        _answer(9, "finding alpha resolved.", ans="yes", label="OBSERVED", ev=["modules/x/y.py:9"])]
    r = validate_answer_set(qs, padded)
    assert r.valid is False and ReasonCode.INVENTED_ANSWER in r.reason_codes


def test_balanced_fence_swallowing_contiguous_tail_flagged_malformed() -> None:
    """BLOCKER (CoR R22): a BALANCED (closed) fence enclosing the CONTIGUOUS TAIL items drops
    them silently; the remaining prefix stays contiguous so contiguity alone cannot catch it.
    A fenced ordinal == materialized_count + 1 is shape-indistinguishable from a dropped-then-
    fenced real tail item -> MALFORMED (fail-closed). The high-value verdict item is exactly
    what a careless paste (or an adversary) would fence away."""
    fenced = "```"
    # items 7,8 fenced right after a 6-item prefix (7 == 6+1 continuation)
    _assert_malformed("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n"
                      + fenced + "\n7. Is the valve CLOSED by default?\n"
                      "8. What is the verdict and next safest slice?\n" + fenced + "\n")
    # a single fenced tail item (8 after a 7-item prefix) also drops the verdict -> MALFORMED
    _assert_malformed("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n5. e?\n6. f?\n7. g?\n"
                      + fenced + "\n8. What is the verdict and next safest slice?\n" + fenced + "\n")
    # the continuation-numbered trailing sample (9,10 after 8) is likewise ambiguous
    _assert_malformed(AUDIT_PROMPT.rstrip("\n") + "\n\n"
                      + fenced + "\n9. finding alpha.\n10. finding beta.\n" + fenced + "\n")


def test_fenced_example_determine_before_real_block_ignored() -> None:
    """MAJOR (CoR R19, variant): a fenced EXAMPLE `Determine:` list before the real block
    must be skipped -- only the real top-level block is parsed (no example-question merge)."""
    fenced = "```"
    prompt = ("Here is the required output format:\n" + fenced + "\n"
              "Determine:\n1. Did we resolve alpha?\n2. Did we resolve beta?\n" + fenced + "\n\n"
              "Determine:\n1. Does any code write a scaffold today?\n2. Is the genesis gate wired?\n")
    qs = parse_determine_questions(prompt)
    assert len(qs) == 2
    assert [q.source_number for q in qs] == [1, 2]
    assert qs[0].text.startswith("Does any code write a scaffold")
    assert "resolve alpha" not in qs[0].text and "resolve alpha" not in qs[1].text


def test_determine_only_inside_fence_yields_no_block() -> None:
    """A Determine list that exists ONLY inside a code fence is not audit scope: no top-level
    marker -> empty parse -> NO_DETERMINE_BLOCK (fail-closed, never a fenced-example audit)."""
    fenced = "```"
    prompt = ("Example only:\n" + fenced + "\nDetermine:\n1. a?\n2. b?\n" + fenced + "\n")
    qs = parse_determine_questions(prompt)
    assert qs == []
    r = validate_answer_set(qs, [])
    assert r.valid is False and ReasonCode.NO_DETERMINE_BLOCK in r.reason_codes


def test_midlist_fenced_numbers_ignored_real_items_resume() -> None:
    """A fenced block INTERRUPTING the list (e.g. an inline sample) must have its numbered
    lines ignored; the real items resume after the fence and stay contiguous -> exactly N."""
    fenced = "```"
    prompt = ("Determine:\n1. a?\n2. b?\n3. c?\n"
              + fenced + "\n9. phantom sample line.\n10. another phantom.\n" + fenced + "\n"
              "4. d?\n5. e?\n")
    qs = parse_determine_questions(prompt)
    assert [q.source_number for q in qs] == [1, 2, 3, 4, 5]
    assert is_determine_list_wellformed(qs) is True
    assert "phantom" not in " ".join(q.text for q in qs)


def test_unclosed_fence_after_marker_truncates_flagged_malformed() -> None:
    """MAJOR (CoR R20): an UNCLOSED (odd-parity) code fence opened AFTER the marker silently
    swallows the tail items to EOF (the R19 fence machinery's symmetric partner). The
    truncated list is still contiguous, so it must be flagged MALFORMED via an EOF in_fence
    guard, never certified as a complete short list."""
    for f in ("```", "~~~"):
        # stray fence after item 4 swallows items 5-8
        _assert_malformed("Determine:\n1. a?\n2. b?\n3. c?\n4. d?\n" + f + "\n"
                          "5. e?\n6. f?\n7. g?\n8. verdict?\n")
        # unclosed fence at the very end (no tail items) is also unbalanced -> MALFORMED
        _assert_malformed("Determine:\n1. a?\n2. b?\n3. c?\n" + f + "\nSample:\n9. x.\n")


# --- repair evasion regressions (CoR) ---------------------------------------
def test_repair_cannot_change_determination() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    orig = _valid_answers(qs)
    orig[0] = {"index": 1, "question_text": qs[0].text, "answer": "needs_verification",
               "wsp97_label": "NEEDS_VERIFICATION", "evidence_refs": []}
    repaired = copy.deepcopy(orig)
    repaired[0] = {"index": 1, "question_text": qs[0].text, "answer": "yes",  # invented determination
                   "wsp97_label": "OBSERVED", "evidence_refs": ["modules/x.py:5"]}
    r = assert_repair_preserves(qs, orig, repaired)
    assert r.valid is False and ReasonCode.REPAIR_CHANGED_DETERMINATION in r.reason_codes


def test_repair_reordered_answers_fails() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    orig = _valid_answers(qs)
    repaired = list(reversed(copy.deepcopy(orig)))  # same set, reordered
    r = assert_repair_preserves(qs, orig, repaired)
    assert r.valid is False and ReasonCode.REPAIR_INVALID_ANSWERS in r.reason_codes


def test_repair_to_invalid_answer_set_fails() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    orig = _valid_answers(qs)
    repaired = copy.deepcopy(orig)
    repaired[3]["wsp97_label"] = ""  # repaired set is itself invalid (unlabeled)
    r = assert_repair_preserves(qs, orig, repaired)
    assert r.valid is False and ReasonCode.REPAIR_INVALID_ANSWERS in r.reason_codes


def test_vague_evidence_fails_validation() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = _valid_answers(qs)
    ans[1]["evidence_refs"] = ["the orchestrator file says it is wired"]
    r = validate_answer_set(qs, ans)
    assert r.valid is False and ReasonCode.VAGUE_EVIDENCE in r.reason_codes


# --- repair preserves evidence + list (012 core: no prose collapse) ---------
def test_repair_collapse_to_prose_fails() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    orig = _valid_answers(qs)
    repaired = [{"index": 1, "question_text": qs[0].text, "answer": "partial",
                 "wsp97_label": "INFERRED", "evidence_refs": ["modules/x.py:1"]}]  # collapsed to 1 prose answer
    r = assert_repair_preserves(qs, orig, repaired)
    assert r.valid is False and ReasonCode.REPAIR_COLLAPSED_TO_PROSE in r.reason_codes


def test_repair_dropping_evidence_fails() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    orig = _valid_answers(qs)
    repaired = copy.deepcopy(orig)
    repaired[2]["evidence_refs"] = []  # repair dropped Q3's evidence
    r = assert_repair_preserves(qs, orig, repaired)
    assert r.valid is False and ReasonCode.REPAIR_DROPPED_EVIDENCE in r.reason_codes


@pytest.mark.parametrize("weak_ev", [
    ["the orchestrator file says it is wired"],   # vague prose (no file:line)
    [],                                           # empty (an unevidenced original)
    ["modules/x/file_3.py:0"],                    # line 0 -> normalizes to nothing
    ["Run Trace:gate_state"],                     # Run-Trace-only (no file:line anchor)
])
def test_repair_fabricating_evidence_for_weak_original_fails(weak_ev) -> None:
    """MAJOR (CoR R19): a repair may reformat prose but may NOT SOURCE a file:line anchor the
    original lacked. An answer whose original evidence did not normalize to a file:line
    (vague / empty / line-0 / Run-Trace-only) must not leave repair with a fabricated anchor.
    The empty original set makes the superset check vacuously pass, so this is the guard that
    stops 'repair rewrites evidence IN'."""
    qs = parse_determine_questions(AUDIT_PROMPT)
    orig = _valid_answers(qs)
    # Q3 keeps a real determination but weak/absent evidence going INTO repair.
    orig[2] = {"index": 3, "question_text": qs[2].text, "answer": "yes",
               "wsp97_label": "OBSERVED", "evidence_refs": list(weak_ev)}
    repaired = copy.deepcopy(orig)
    # keep the weak original refs (so the superset check passes) and ADD a manufactured
    # file:line anchor -- the exact "cleanup" move the fabrication guard must reject.
    repaired[2]["evidence_refs"] = list(weak_ev) + ["modules/fabricated.py:7"]
    r = assert_repair_preserves(qs, orig, repaired)
    assert r.valid is False and ReasonCode.REPAIR_FABRICATED_EVIDENCE in r.reason_codes


def test_repair_materializing_anchored_answer_for_omitted_index_fails() -> None:
    """MAJOR (CoR R20): a repair may not MATERIALIZE a fresh file:line-anchored answer for a
    Determine question the original OMITTED (the exact case a repair is invoked for). The
    per-index guards key on the original and skip omitted indices, so this is caught by the
    dedicated omitted-index fabrication check."""
    qs = parse_determine_questions(AUDIT_PROMPT)
    orig = _valid_answers(qs)[:-1]  # original OMITS Q8 -> would trigger a repair
    repaired = copy.deepcopy(orig) + [
        {"index": 8, "question_text": qs[7].text, "answer": "yes",
         "wsp97_label": "OBSERVED", "evidence_refs": ["modules/TOTALLY_FABRICATED.py:1"]}]
    r = assert_repair_preserves(qs, orig, repaired)
    assert r.valid is False and ReasonCode.REPAIR_FABRICATED_EVIDENCE in r.reason_codes


def test_repair_materializing_needs_verification_for_omitted_index_allowed() -> None:
    """Contrast: a repair MAY surface an omitted index as an explicit NEEDS_VERIFICATION
    abstention (no file:line) -- that is honest completion of a silent omission (the contract's
    anti-omission intent), not fabrication of an anchored determination."""
    qs = parse_determine_questions(AUDIT_PROMPT)
    orig = _valid_answers(qs)[:-1]  # omits Q8
    repaired = copy.deepcopy(orig) + [
        {"index": 8, "question_text": qs[7].text, "answer": "needs_verification",
         "wsp97_label": "NEEDS_VERIFICATION", "evidence_refs": []}]
    r = assert_repair_preserves(qs, orig, repaired)
    assert r.valid is True, r.reason_codes


def test_repair_strengthening_existing_file_line_evidence_is_allowed() -> None:
    """Contrast: when the original ALREADY had a file:line anchor, a repair MAY add more
    file:line refs (repair strengthens, it does not manufacture) -- no fabrication flag."""
    qs = parse_determine_questions(AUDIT_PROMPT)
    orig = _valid_answers(qs)  # Q3 default ev = ["modules/x/file_3.py:30"]
    repaired = copy.deepcopy(orig)
    repaired[2]["evidence_refs"] = ["modules/x/file_3.py:30", "modules/x/file_3.py:88"]
    r = assert_repair_preserves(qs, orig, repaired)
    assert r.valid is True, r.reason_codes


def test_repair_dropping_surplus_original_index_fails() -> None:
    """CoR (repair-guard R1): a repair that drops an ORIGINAL answer at a SURPLUS index (beyond
    len(qs)) must be rejected. The per-question steps iterate `for q in qs` and skip surplus
    indices, so the original-answered-index coverage check in step 1 is what catches it."""
    qs = parse_determine_questions("Determine:\n1. a?\n2. b?\n3. c?\n")
    orig = [_answer(1, qs[0].text), _answer(2, qs[1].text), _answer(3, qs[2].text),
            _answer(4, "surplus sub-finding", ev=["modules/valve.py:44"])]
    repaired = copy.deepcopy(orig)[:3]  # dropped the surplus index-4 answer + its evidence
    r = assert_repair_preserves(qs, orig, repaired)
    assert r.valid is False and ReasonCode.REPAIR_COLLAPSED_TO_PROSE in r.reason_codes


def test_repair_reformatting_evidence_is_allowed() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    orig = _valid_answers(qs)
    repaired = copy.deepcopy(orig)
    # reformat #L <-> : is preserved (normalized equal); adding evidence is allowed
    repaired[0]["evidence_refs"] = ["modules/x/file_1.py#L10", "modules/x/file_1.py:99"]
    r = assert_repair_preserves(qs, orig, repaired)
    assert r.valid is True, r.reason_codes


def test_repair_altering_questions_fails() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    orig = _valid_answers(qs)
    repaired = copy.deepcopy(orig)
    repaired[0]["question_text"] = "reworded question"
    r = assert_repair_preserves(qs, orig, repaired)
    assert r.valid is False and ReasonCode.REPAIR_ALTERED_QUESTIONS in r.reason_codes


# --- template ---------------------------------------------------------------
def test_build_answer_template_one_per_question() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    tmpl = build_answer_template(qs)
    assert len(tmpl) == 8
    assert [t["index"] for t in tmpl] == list(range(1, 9))
    assert all(t["answer"] == "" and t["evidence_refs"] == [] for t in tmpl)


# --- no invented answers / static codes / purity ----------------------------
def test_reason_codes_are_static_no_leak() -> None:
    qs = parse_determine_questions(AUDIT_PROMPT)
    ans = _valid_answers(qs)
    ans[0]["evidence_refs"] = ["the file says"]
    r = validate_answer_set(qs, ans)
    assert all(code.startswith("FAIL_") for code in r.reason_codes)


def test_module_is_pure_no_subprocess_os_network() -> None:
    src = Path(c.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imported.add((n.module or "").split(".")[0])
    forbidden = {"subprocess", "os", "socket", "requests", "urllib", "http", "pathlib", "sys"}
    assert not (imported & forbidden), f"contract must be pure text: {imported & forbidden}"
    called = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            called.add(n.func.id)
    assert not (called & {"eval", "exec", "compile", "__import__", "open"})


def test_doc_is_ascii_clean() -> None:
    raw = Path(c.__file__).read_bytes()
    assert not [i for i, b in enumerate(raw) if b > 127]
    assert raw.count(0) == 0
