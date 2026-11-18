#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the RedDog repair-evidence GUARD.

Slice: REDDOG_REPAIR_PRESERVES_EVIDENCE_PHASE1
WSP:   50, 97

The guard REUSES reddog_determine_answer_contract.assert_repair_preserves (no duplicated
preservation rules). These tests cover 012's 10 acceptance bars + serialization round-trip +
fail-closed block-drop edges + backward-compat no-op.
"""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import reddog_repair_evidence_guard as g
from modules.communication.moltbot_bridge.src.reddog_repair_evidence_guard import (
    RepairGuardReason,
    build_protected_repair_context,
    extract_determine_answers,
    guard_repair,
    guard_repair_from_outputs,
    serialize_determine_answers,
)
from modules.communication.moltbot_bridge.src.reddog_determine_answer_contract import (
    ReasonCode,
    parse_determine_questions,
    validate_answer_set,
)

AUDIT_PROMPT = """Audit the FoundUp creation monorepo WSP_109 execution path.

Required direct-read targets:
- WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md
- modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py

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


def _questions():
    return parse_determine_questions(AUDIT_PROMPT)


def _answer(idx, text, ans="yes", label="OBSERVED", ev=None):
    return {"index": idx, "question_text": text, "answer": ans, "wsp97_label": label,
            "evidence_refs": ev if ev is not None else [f"modules/x/file_{idx}.py:{idx * 10}"]}


def _primary_answers(qs):
    out = []
    for q in qs:
        if q.index == 8:
            out.append(_answer(8, q.text, ans="decision", label="INFERRED",
                               ev=["docs/audits/architecture/REDDOG_FOUNDUP_CREATION_EXECUTION_PATH_AUDIT_PHASE1.md:200"]))
        else:
            out.append(_answer(q.index, q.text))
    return out


def _output_with_block(answers, extra_sections=""):
    """A RedDog-style markdown output that carries the Determine answer block."""
    return ("## Decision\n\nProceed.\n\n" + serialize_determine_answers(answers)
            + "\n\n## WSP_15 Priority\n\nHIGH." + (("\n\n" + extra_sections) if extra_sections else ""))


# --- serialization round-trip ------------------------------------------------
def test_serialize_extract_round_trip() -> None:
    qs = _questions()
    answers = _primary_answers(qs)
    text = _output_with_block(answers)
    extracted = extract_determine_answers(text)
    assert extracted is not None and len(extracted) == 8
    # extracted answers validate against the questions (round-trip is loss-free)
    assert validate_answer_set(qs, extracted).valid is True
    assert [a["index"] for a in extracted] == list(range(1, 9))


def test_extract_none_when_no_block() -> None:
    assert extract_determine_answers("## Decision\n\nNo determine block here.\n") is None


def test_extract_none_when_block_unparseable() -> None:
    text = "## Determine Answers\n\n```json\n{ this is not valid json ]\n```\n"
    assert extract_determine_answers(text) is None


# --- ACCEPTANCE 1: 8 answers with file:line preserved 8/8 --------------------
def test_acceptance_1_eight_answers_preserved() -> None:
    qs = _questions()
    prim = _primary_answers(qs)
    rep = copy.deepcopy(prim)  # repair reproduced the block unchanged
    d = guard_repair(qs, prim, rep)
    assert d.has_determine is True and d.preserved is True and d.keep_original is False
    assert d.reason_codes == []


# --- ACCEPTANCE 2 / 8: repair adds a missing section, answers unchanged ------
def test_acceptance_2_and_8_repair_adds_section_preserves_answers() -> None:
    qs = _questions()
    prim = _primary_answers(qs)
    # end-to-end: primary output has the block; repaired output adds a Verification gaps section
    primary_out = _output_with_block(prim)
    repaired_out = _output_with_block(prim, extra_sections="## Verification gaps\n\nNone blocking.")
    d = guard_repair_from_outputs(AUDIT_PROMPT, primary_out, repaired_out)
    assert d.has_determine is True and d.preserved is True and d.keep_original is False


# --- ACCEPTANCE 3: dropped answer rejected ----------------------------------
def test_acceptance_3_dropped_answer_rejected() -> None:
    qs = _questions()
    prim = _primary_answers(qs)
    rep = copy.deepcopy(prim)[:-1]  # repair dropped Q8 (the verdict)
    d = guard_repair(qs, prim, rep)
    assert d.preserved is False and d.keep_original is True
    assert ReasonCode.REPAIR_COLLAPSED_TO_PROSE in d.reason_codes


# --- ACCEPTANCE 4: reordered answers rejected -------------------------------
def test_acceptance_4_reordered_answers_rejected() -> None:
    qs = _questions()
    prim = _primary_answers(qs)
    rep = list(reversed(copy.deepcopy(prim)))
    d = guard_repair(qs, prim, rep)
    assert d.preserved is False and d.keep_original is True
    assert ReasonCode.REPAIR_INVALID_ANSWERS in d.reason_codes


# --- ACCEPTANCE 5: removed file:line evidence rejected ----------------------
def test_acceptance_5_removed_evidence_rejected() -> None:
    qs = _questions()
    prim = _primary_answers(qs)
    rep = copy.deepcopy(prim)
    rep[2]["evidence_refs"] = []  # repair dropped Q3's file:line evidence
    d = guard_repair(qs, prim, rep)
    assert d.preserved is False and d.keep_original is True
    assert ReasonCode.REPAIR_DROPPED_EVIDENCE in d.reason_codes


# --- ACCEPTANCE 6: OBSERVED -> vague NEEDS_VERIFICATION rejected -------------
def test_acceptance_6_observed_downgraded_to_nv_rejected() -> None:
    qs = _questions()
    prim = _primary_answers(qs)
    rep = copy.deepcopy(prim)
    rep[2] = {"index": 3, "question_text": qs[2].text, "answer": "needs_verification",
              "wsp97_label": "NEEDS_VERIFICATION", "evidence_refs": []}  # weakened, evidence dropped
    d = guard_repair(qs, prim, rep)
    assert d.preserved is False and d.keep_original is True
    assert (ReasonCode.REPAIR_CHANGED_DETERMINATION in d.reason_codes
            or ReasonCode.REPAIR_DROPPED_EVIDENCE in d.reason_codes)


# --- ACCEPTANCE 7: fabricated file:line (not in original) rejected ----------
def test_acceptance_7_fabricated_evidence_rejected() -> None:
    qs = _questions()
    prim = _primary_answers(qs)
    # Q3 entered repair with weak (non-normalizing) evidence; repair keeps it AND adds a
    # manufactured file:line anchor -> fabrication.
    prim[2] = {"index": 3, "question_text": qs[2].text, "answer": "yes",
               "wsp97_label": "OBSERVED", "evidence_refs": ["the orchestrator file says so"]}
    rep = copy.deepcopy(prim)
    rep[2]["evidence_refs"] = ["the orchestrator file says so", "modules/FABRICATED.py:7"]
    d = guard_repair(qs, prim, rep)
    assert d.preserved is False and d.keep_original is True
    assert ReasonCode.REPAIR_FABRICATED_EVIDENCE in d.reason_codes


# --- ACCEPTANCE 9: protected repair context includes file:line refs ---------
def test_acceptance_9_protected_context_includes_evidence_refs() -> None:
    qs = _questions()
    prim = _primary_answers(qs)
    ctx = build_protected_repair_context(prim)
    assert "PROTECTED_DETERMINE_ANSWERS" in ctx
    # the actual direct-read file:line refs are present, not just a summary
    assert "modules/x/file_1.py:10" in ctx
    assert "modules/x/file_7.py:70" in ctx
    assert "REDDOG_FOUNDUP_CREATION_EXECUTION_PATH_AUDIT_PHASE1.md:200" in ctx
    # and the exact serialized block is embedded so the model can reproduce it verbatim
    assert g.DETERMINE_ANSWERS_HEADER in ctx
    # round-trips: the embedded block extracts back to the same 8 answers
    assert len(extract_determine_answers(ctx) or []) == 8


# --- ACCEPTANCE 10: FoundUp creation audit fixture valid after repair -------
def test_acceptance_10_foundup_audit_fixture_preserved_end_to_end() -> None:
    qs = _questions()
    prim = _primary_answers(qs)
    primary_out = _output_with_block(prim)
    repaired_out = _output_with_block(copy.deepcopy(prim),
                                      extra_sections="## Next safest step\n\nWire the guard.")
    d = guard_repair_from_outputs(AUDIT_PROMPT, primary_out, repaired_out)
    assert d.has_determine is True and d.preserved is True and d.keep_original is False
    # the repaired block still validates as a complete 8-answer audit
    assert validate_answer_set(qs, extract_determine_answers(repaired_out)).valid is True


# --- fail-closed: repair destroyed / garbled the whole block ----------------
def test_from_outputs_dropped_block_keeps_original() -> None:
    qs = _questions()
    prim = _primary_answers(qs)
    primary_out = _output_with_block(prim)
    repaired_out = "## Decision\n\nProceed.\n\n## Summary\n\nAll good, see above.\n"  # block gone
    d = guard_repair_from_outputs(AUDIT_PROMPT, primary_out, repaired_out)
    assert d.preserved is False and d.keep_original is True
    assert RepairGuardReason.DROPPED_DETERMINE_BLOCK in d.reason_codes


def test_from_outputs_unparseable_repair_block_keeps_original() -> None:
    prim = _primary_answers(_questions())
    primary_out = _output_with_block(prim)
    repaired_out = "## Determine Answers\n\n```json\n[ not valid json\n```\n"
    d = guard_repair_from_outputs(AUDIT_PROMPT, primary_out, repaired_out)
    assert d.preserved is False and d.keep_original is True
    assert RepairGuardReason.UNPARSEABLE_DETERMINE_BLOCK in d.reason_codes


# --- backward-compat no-op (only when the PRIMARY carries no block) ----------
def test_no_block_anywhere_is_noop() -> None:
    """No Determine block in the primary -> nothing to protect -> no-op (unchanged behavior),
    regardless of whether the prompt has a Determine list."""
    d1 = guard_repair_from_outputs("Just a plain prompt, no determine list.",
                                   "## Decision\n\nprose only.\n", "## Decision\n\nprose.\n")
    assert d1.has_determine is False and d1.keep_original is False
    # AUDIT_PROMPT has a list, but the primary emitted no block -> still a no-op
    d2 = guard_repair_from_outputs(AUDIT_PROMPT, "## Decision\n\nProse only, no block.\n",
                                   "## Decision\n\nProse.\n\n## Findings\n\nAdded.\n")
    assert d2.has_determine is False and d2.keep_original is False


def test_no_prompt_list_but_primary_block_is_protected() -> None:
    """CoR R4: a primary that emitted a Determine block is protected even when the PROMPT has no
    Determine list (the block is self-describing) -- it does NOT fail OPEN. Faithful repair
    preserves; an evidence strip is rejected."""
    qs = _questions()
    prim = _primary_answers(qs)
    d_ok = guard_repair_from_outputs("Plain prompt, no determine list.",
                                     _output_with_block(prim),
                                     _output_with_block(prim) + "\n\n## Findings\n\nadded.")
    assert d_ok.has_determine is True and d_ok.keep_original is False
    rep = copy.deepcopy(prim)
    rep[2]["evidence_refs"] = []
    d_strip = guard_repair_from_outputs("Plain prompt, no determine list.",
                                        _output_with_block(prim), _output_with_block(rep))
    assert d_strip.keep_original is True
    assert ReasonCode.REPAIR_DROPPED_EVIDENCE in d_strip.reason_codes


def test_malformed_prompt_list_but_primary_block_is_protected() -> None:
    """MAJOR (CoR R4): a MALFORMED prompt Determine list must NOT disable protection when the
    primary emitted a real block -- questions are synthesized from the primary block, and a
    weakening repair is rejected (previously this fail-OPENed and accepted the strip)."""
    bad_prompt = "Audit.\n\nDetermine:\n1. a? 2. b?\nEnd.\n"  # fused -> MALFORMED
    qs = _questions()
    prim = _primary_answers(qs)
    rep = copy.deepcopy(prim)
    rep[0] = {"index": 1, "question_text": qs[0].text, "answer": "needs_verification",
              "wsp97_label": "NEEDS_VERIFICATION", "evidence_refs": []}  # OBSERVED->NV + ev stripped
    d = guard_repair_from_outputs(bad_prompt, _output_with_block(prim), _output_with_block(rep))
    assert d.has_determine is True and d.keep_original is True
    assert (ReasonCode.REPAIR_DROPPED_EVIDENCE in d.reason_codes
            or ReasonCode.REPAIR_CHANGED_DETERMINATION in d.reason_codes)


# --- CoR R1 regressions -----------------------------------------------------
def test_cor_surplus_index_answer_drop_rejected() -> None:
    """ANSWER_DROP blocker: a primary that answers MORE indices than the prompt has questions
    (surplus indices) must have those answers preserved too -- dropping a surplus evidence-backed
    answer is rejected (keep_original), not silently accepted."""
    qs = parse_determine_questions("Determine:\n1. a?\n2. b?\n3. c?\n")
    assert len(qs) == 3
    prim = [_answer(1, qs[0].text), _answer(2, qs[1].text), _answer(3, qs[2].text),
            _answer(4, "surplus sub-finding four", ev=["modules/valve.py:44"]),
            _answer(5, "surplus sub-finding five", ev=["modules/gate.py:55"])]
    rep = copy.deepcopy(prim)[:3]  # repair dropped the surplus answers 4 and 5
    d = guard_repair(qs, prim, rep)
    assert d.preserved is False and d.keep_original is True
    assert ReasonCode.REPAIR_COLLAPSED_TO_PROSE in d.reason_codes


def test_cor_dual_block_repaired_output_rejected() -> None:
    """EVIDENCE_FABRICATION: a repaired output with TWO `## Determine Answers` blocks (a benign
    copy + a fabricated one) is ambiguous -> extract fails closed -> keep_original."""
    qs = _questions()
    prim = _primary_answers(qs)
    fabricated = copy.deepcopy(prim)
    fabricated[1]["evidence_refs"] = ["modules/TOTALLY_FAKE.py:999"]
    repaired_out = ("## Decision\n\nOK.\n\n" + serialize_determine_answers(prim)
                    + "\n\n" + serialize_determine_answers(fabricated) + "\n")
    d = guard_repair_from_outputs(AUDIT_PROMPT, _output_with_block(prim), repaired_out)
    assert d.keep_original is True
    assert RepairGuardReason.UNPARSEABLE_DETERMINE_BLOCK in d.reason_codes


def test_cor_dual_block_primary_output_fails_closed() -> None:
    """EVIDENCE_FABRICATION (symmetric): a primary with two blocks (empty decoy + real answers)
    must not silently disable protection -> keep_original (not a backward-compat no-op)."""
    qs = _questions()
    prim = _primary_answers(qs)
    primary_out = ("## Decision\n\nOK.\n\n" + serialize_determine_answers([])
                   + "\n\n" + serialize_determine_answers(prim) + "\n")
    d = guard_repair_from_outputs(AUDIT_PROMPT, primary_out, _output_with_block(prim))
    assert d.has_determine is True and d.keep_original is True
    assert RepairGuardReason.UNPARSEABLE_DETERMINE_BLOCK in d.reason_codes


def test_cor_question_text_with_backticks_round_trips() -> None:
    """CONTEXT_TRUNCATION blocker: a question_text containing a triple-backtick must not collapse
    the serialized block's fence -- serialize/extract round-trips via a variable-length fence."""
    qs = _questions()
    prim = _primary_answers(qs)
    prim[0]["question_text"] = "Does the ```json determine block schema exist?"
    text = serialize_determine_answers(prim)
    extracted = extract_determine_answers(text)
    assert extracted is not None and len(extracted) == 8
    assert extracted[0]["question_text"] == prim[0]["question_text"]


def test_cor_backtick_question_primary_protected_end_to_end() -> None:
    """CONTEXT_TRUNCATION blocker (end-to-end): a primary whose question quotes fenced code must
    still be protected -- a repair that strips its evidence is rejected (pre-fix this failed OPEN
    because the broken primary fence made extraction None -> no-op accept)."""
    prompt = ("Audit.\n\nDetermine:\n1. Does the ```json determine schema exist?\n"
              "2. Is the valve closed?\nEnd.\n")
    qs = parse_determine_questions(prompt)
    assert len(qs) == 2
    prim = [_answer(1, qs[0].text, ev=["modules/x/schema.py:12"]),
            _answer(2, qs[1].text, ans="no", ev=["modules/x/valve.py:99"])]
    rep = copy.deepcopy(prim)
    rep[1]["evidence_refs"] = []  # repair strips Q2's evidence
    d = guard_repair_from_outputs(prompt, _output_with_block(prim), _output_with_block(rep))
    assert d.has_determine is True and d.keep_original is True
    assert ReasonCode.REPAIR_DROPPED_EVIDENCE in d.reason_codes


def test_cor_protected_context_round_trips_with_backticks() -> None:
    """Acceptance 9 must hold even when a question_text contains ``` (variable-length fence)."""
    qs = _questions()
    prim = _primary_answers(qs)
    prim[0]["question_text"] = "Is the ```python valve``` closed by default?"
    ctx = build_protected_repair_context(prim)
    assert len(extract_determine_answers(ctx) or []) == 8
    assert "modules/x/file_7.py:70" in ctx


def test_cor_empty_array_primary_plus_fabrication_rejected() -> None:
    """REDACTION_FALLBACK: a PRESENT-but-empty `[]` primary block is not a no-op -- a repair that
    materializes fabricated file:line answers for the empty original must be rejected."""
    qs = _questions()
    fab = _primary_answers(qs)  # 8 anchored answers, all fabricated relative to the empty original
    d = guard_repair(qs, [], fab)
    assert d.has_determine is True and d.preserved is False and d.keep_original is True
    assert ReasonCode.REPAIR_FABRICATED_EVIDENCE in d.reason_codes


def test_cor_empty_array_primary_end_to_end_rejects_fabrication() -> None:
    qs = _questions()
    primary_out = _output_with_block([])  # header + empty [] array
    repaired_out = _output_with_block(_primary_answers(qs))  # fabricated full set
    d = guard_repair_from_outputs(AUDIT_PROMPT, primary_out, repaired_out)
    assert d.has_determine is True and d.keep_original is True
    assert ReasonCode.REPAIR_FABRICATED_EVIDENCE in d.reason_codes


# --- CoR R2 regressions -----------------------------------------------------
@pytest.mark.parametrize("variant_header", [
    "## Determine Answers (FINAL)",
    "## Determine Answers:",
    "### Determine Answers - authoritative",
    "        ## Determine Answers",  # over-indented copy
])
def test_cor_near_canonical_second_block_fails_closed(variant_header) -> None:
    """EVIDENCE_FABRICATION (R2): a fabricated 2nd block under a NEAR-canonical header (trailing
    text / extra indent) must still be counted -> ambiguous -> keep_original. The broadened
    header detector counts any '# ... determine answers' heading, not just the byte-exact one."""
    qs = _questions()
    prim = _primary_answers(qs)
    fabricated = copy.deepcopy(prim)
    fabricated[1]["evidence_refs"] = ["modules/FAKE.py:999"]
    fab_block = variant_header + "\n\n```json\n" + json.dumps(
        [{"index": a["index"], "question_text": a["question_text"], "answer": a["answer"],
          "wsp97_label": a["wsp97_label"], "evidence_refs": a["evidence_refs"]} for a in fabricated],
        indent=2, sort_keys=True) + "\n```"
    repaired_out = ("## Decision\n\nOK.\n\n" + serialize_determine_answers(prim)
                    + "\n\n" + fab_block + "\n")
    d = guard_repair_from_outputs(AUDIT_PROMPT, _output_with_block(prim), repaired_out)
    assert d.keep_original is True
    assert RepairGuardReason.UNPARSEABLE_DETERMINE_BLOCK in d.reason_codes


def test_cor_evidence_ref_newline_header_injection_neutralized() -> None:
    """CONTEXT_TRUNCATION (R2): an evidence_ref carrying an embedded newline + a rogue canonical
    header/fence must NOT inject a second header into the protected-context digest -- the context
    still round-trips to exactly the primary answers (acceptance 9 holds)."""
    qs = _questions()
    prim = _primary_answers(qs)
    prim[0]["evidence_refs"] = ["modules/a.py:1\n## Determine Answers\n```json\n[]\n```"]
    ctx = build_protected_repair_context(prim)
    # exactly one canonical block survives -> the context round-trips to all 8 answers
    extracted = extract_determine_answers(ctx)
    assert extracted is not None and len(extracted) == 8
    # the real file:line token is still visible in the digest (defanged onto one line)
    assert "modules/a.py:1" in ctx


# --- CoR R3 regressions -----------------------------------------------------
@pytest.mark.parametrize("variant_header", [
    "## Final Determine Answers",
    "## Corrected Determine Answers",
    "## Authoritative Determine Answers",
])
def test_cor_leading_word_second_block_fails_closed(variant_header) -> None:
    """EVIDENCE_FABRICATION (R3): a fabricated 2nd block under a LEADING-word heading ('Final
    Determine Answers') must still be counted -> ambiguous -> keep_original. (R2 broadened for
    trailing text; R3 broadens for a leading word.)"""
    qs = _questions()
    prim = _primary_answers(qs)
    fabricated = copy.deepcopy(prim)
    fabricated[1]["evidence_refs"] = ["modules/FAKE.py:999"]
    fab_block = variant_header + "\n\n```json\n" + json.dumps(
        [{"index": a["index"], "question_text": a["question_text"], "answer": a["answer"],
          "wsp97_label": a["wsp97_label"], "evidence_refs": a["evidence_refs"]} for a in fabricated],
        indent=2, sort_keys=True) + "\n```"
    repaired_out = ("## Decision\n\nOK.\n\n" + serialize_determine_answers(prim)
                    + "\n\n" + fab_block + "\n")
    d = guard_repair_from_outputs(AUDIT_PROMPT, _output_with_block(prim), repaired_out)
    assert d.keep_original is True
    assert RepairGuardReason.UNPARSEABLE_DETERMINE_BLOCK in d.reason_codes


def test_cor_protected_context_single_header_unaffected_by_broadened_regex() -> None:
    """The broadened header regex must NOT match the '## PROTECTED_DETERMINE_ANSWERS' wrapper, so
    the protected context still contains exactly one canonical block and round-trips."""
    qs = _questions()
    prim = _primary_answers(qs)
    ctx = build_protected_repair_context(prim)
    assert "## PROTECTED_DETERMINE_ANSWERS" in ctx
    assert len(extract_determine_answers(ctx) or []) == 8  # exactly one block counted


@pytest.mark.parametrize("bad_refs", [7, {"x": 1}, "modules/x.py:1", None, True])
def test_cor_scalar_evidence_refs_fail_closed_no_crash(bad_refs) -> None:
    """REDACTION_FALLBACK (R3): a non-list `evidence_refs` (a scalar/dict) must FAIL CLOSED to no
    evidence, never raise a TypeError. A repair keeping a scalar-evidence answer is rejected."""
    qs = _questions()
    prim = _primary_answers(qs)
    rep = copy.deepcopy(prim)
    rep[2]["evidence_refs"] = bad_refs  # non-list -> coerced to [] -> evidence lost
    d = guard_repair(qs, prim, rep)  # must not raise
    assert d.keep_original is True
    # also the protect/context path must not raise on a scalar-ref primary
    prim2 = copy.deepcopy(prim)
    prim2[0]["evidence_refs"] = bad_refs
    ctx = build_protected_repair_context(prim2)  # must not raise
    assert "PROTECTED_DETERMINE_ANSWERS" in ctx


def test_cor_scalar_evidence_refs_end_to_end_no_crash() -> None:
    qs = _questions()
    prim = _primary_answers(qs)
    bad = copy.deepcopy(prim)
    bad[0]["evidence_refs"] = 7  # scalar in the fenced JSON is legal JSON
    d = guard_repair_from_outputs(AUDIT_PROMPT, _output_with_block(prim), _output_with_block(bad))
    assert d.keep_original is True  # evidence lost on Q1 -> rejected, never raises


def test_cor_duplicate_primary_index_keeps_original() -> None:
    """LABEL_WEAKEN (R3): a primary that answers the SAME index twice with conflicting labels is
    internally contradictory -> unresolvable -> keep_original (a last-wins resolution must not
    silently accept a weaker label)."""
    qs = _questions()
    prim = _primary_answers(qs)
    # duplicate index 1: OBSERVED then INFERRED (conflicting)
    prim.insert(1, _answer(1, qs[0].text, ans="yes", label="INFERRED"))
    rep = [_answer(1, qs[0].text, ans="yes", label="INFERRED")] + _primary_answers(qs)[1:]
    d = guard_repair(qs, prim, rep)
    assert d.has_determine is True and d.keep_original is True
    assert RepairGuardReason.DUPLICATE_PRIMARY_INDEX in d.reason_codes


# --- CoR R4 regressions -----------------------------------------------------
def _fab_json(answers) -> str:
    return json.dumps(
        [{"index": a["index"], "question_text": a["question_text"], "answer": a["answer"],
          "wsp97_label": a["wsp97_label"], "evidence_refs": a["evidence_refs"]} for a in answers],
        indent=2, sort_keys=True)


@pytest.mark.parametrize("underline", ["=================", "-----------------"])
def test_cor_setext_second_block_fails_closed(underline) -> None:
    """EVIDENCE_FABRICATION (R4 blocker): a fabricated 2nd block under a SETEXT heading (no '#',
    the title 'Determine Answers' underlined by === or ---) must still be counted as a block ->
    ambiguous -> keep_original. Pre-fix the ATX-only counter missed it."""
    qs = _questions()
    prim = _primary_answers(qs)
    fabricated = copy.deepcopy(prim)
    fabricated[1]["evidence_refs"] = ["modules/FABRICATED.py:999"]
    setext_block = "Determine Answers\n" + underline + "\n\n```json\n" + _fab_json(fabricated) + "\n```"
    repaired_out = ("## Decision\n\nOK.\n\n" + setext_block + "\n\n"
                    + serialize_determine_answers(prim) + "\n")
    d = guard_repair_from_outputs(AUDIT_PROMPT, _output_with_block(prim), repaired_out)
    assert d.keep_original is True
    assert RepairGuardReason.UNPARSEABLE_DETERMINE_BLOCK in d.reason_codes


def test_cor_setext_primary_second_block_fails_closed() -> None:
    """The symmetric primary-side SETEXT ambiguity: a primary with an ATX block + a SETEXT block
    must fail closed (not silently disable protection)."""
    qs = _questions()
    prim = _primary_answers(qs)
    primary_out = ("## Decision\n\nOK.\n\n" + serialize_determine_answers(prim)
                   + "\n\nDetermine Answers\n===\n\n```json\n" + _fab_json(prim) + "\n```\n")
    d = guard_repair_from_outputs(AUDIT_PROMPT, primary_out, _output_with_block(prim))
    assert d.has_determine is True and d.keep_original is True
    assert RepairGuardReason.UNPARSEABLE_DETERMINE_BLOCK in d.reason_codes


# --- purity: guard imports the contract, adds no forbidden deps -------------
def test_guard_module_is_pure() -> None:
    src = Path(g.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imported.add((n.module or "").split(".")[0])
    forbidden = {"subprocess", "os", "socket", "requests", "urllib", "http", "sys"}
    assert not (imported & forbidden), f"guard must be pure: {imported & forbidden}"


def test_guard_doc_is_ascii_clean() -> None:
    raw = Path(g.__file__).read_bytes()
    assert not [i for i, b in enumerate(raw) if b > 127]
    assert raw.count(0) == 0
