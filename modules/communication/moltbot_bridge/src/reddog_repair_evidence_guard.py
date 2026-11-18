#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RedDog repair-evidence GUARD (REDDOG_REPAIR_PRESERVES_EVIDENCE_PHASE1).

Wires the Determine contract's repair-preservation validator into the RedDog schema-repair
path. When a primary RedDog advisory answer carries a Determine answer block, a schema-repair
pass (which exists to ADD missing sections) must NOT drop, reorder, weaken, or fabricate the
evidence-backed Determine answers. This module:

  - EXTRACTS the protected Determine answer block from a primary/repaired output. The block is
    serialized as a fenced JSON array under a `## Determine Answers` header, so extraction is
    a robust `json.loads` -- NOT another fragile markdown parser (the question-list parser was
    hardened over 23 CoR rounds; we do not re-derive answer parsing).
  - BUILDS a protected-block context string (with each answer's file:line evidence refs) to
    inject into the repair_minimal context, so the repair model is told to reproduce the block
    UNCHANGED and may only add missing schema sections.
  - GUARDS the repaired output by REUSING reddog_determine_answer_contract.assert_repair_preserves
    (and validate_answer_set). This module contains NO preservation RULES of its own -- every
    drop/reorder/weaken/fabricate rule lives in the contract. On ANY preservation failure the
    decision is KEEP_ORIGINAL (reject the weakened repair, keep the primary output + its
    validation failure), fail-closed. A repair that destroys the whole answer block is likewise
    KEEP_ORIGINAL.

Backward compatible: a prompt with no (well-formed) Determine list, or a primary output with no
Determine answer block, yields has_determine=False and keep_original=False -- the existing
schema-repair behavior is unchanged.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_determine_answer_contract import (
    DetermineAnswer,
    DetermineQuestion,
    _safe_int,
    assert_repair_preserves,
    is_determine_list_wellformed,
    normalize_evidence_ref,
    parse_determine_questions,
    validate_answer_set,
)

# Canonical serialization of the Determine answer block in a RedDog output. A `## Determine
# Answers` header followed by a fenced JSON array of answer objects. Robust round-trip: emit
# with serialize_determine_answers, read back with extract_determine_answers (json.loads).
DETERMINE_ANSWERS_HEADER = "## Determine Answers"
# Detects a Determine-answers heading. DELIBERATELY BROAD: any heading whose text CONTAINS
# "determine answers" -- LEADING words ("## Final Determine Answers") AND trailing text ("##
# Determine Answers (FINAL)", ": ", "- authoritative"), at any indent -- so a near-canonical
# second block is still counted for the >1 -> fail-closed ambiguity rule and still registers in
# _has_answer_block. BOTH Markdown heading styles are covered: ATX ("## Determine Answers") and
# SETEXT (a "Determine Answers" text line underlined by === or ---). [ \t] (not \s) so it never
# crosses a newline or false-matches a fenced JSON body line (which starts with a quote, not a
# hash/underline). "PROTECTED_DETERMINE_ANSWERS" is NOT matched: "determine" there is preceded by
# "_" (no \b) and "determine_answers" has "_" not [ \t] between the two words.
_ATX_HEADER_RE = re.compile(
    r"^[ \t]*#{1,6}[ \t]+[^\n]*\bdetermine[ \t]+answers\b", re.IGNORECASE | re.MULTILINE)
_SETEXT_HEADER_RE = re.compile(
    r"^[ \t]*[^\n]*\bdetermine[ \t]+answers\b[^\n]*\n[ \t]*(?:=+|-+)[ \t]*$",
    re.IGNORECASE | re.MULTILINE)
_WS_RE = re.compile(r"\s+")


def _answer_block_headers(text: str) -> list:
    """All Determine-answers heading matches (ATX + SETEXT). >1 => ambiguous => fail closed."""
    if not isinstance(text, str) or not text:
        return []
    return list(_ATX_HEADER_RE.finditer(text)) + list(_SETEXT_HEADER_RE.finditer(text))


def _oneline(s: str) -> str:
    """Collapse all whitespace (incl. newlines) to single spaces so a free-form field (an
    evidence ref, label, answer) cannot inject a Markdown header/fence into a physical digest
    line of the protected context."""
    return _WS_RE.sub(" ", s).strip()
# First fenced code block after the header. The fence is VARIABLE length (`{3,} / ~{3,}) and the
# CLOSING fence must EXACTLY match the opening (backreference), so a serialized block whose JSON
# body contains an inner backtick run (e.g. a question_text quoting ```) does not close early --
# serialize_determine_answers always opens with a fence strictly longer than any inner run.
_FENCE_BLOCK_RE = re.compile(
    r"(?P<fence>`{3,}|~{3,})[^\n]*\n(?P<body>.*?)(?:\n)?(?P=fence)", re.DOTALL)


class RepairGuardReason:
    """Guard-level reason codes (block-level; answer-level rules stay in the contract)."""

    DROPPED_DETERMINE_BLOCK = "FAIL_REPAIR_DROPPED_DETERMINE_BLOCK"
    UNPARSEABLE_DETERMINE_BLOCK = "FAIL_REPAIR_UNPARSEABLE_DETERMINE_BLOCK"
    DUPLICATE_PRIMARY_INDEX = "FAIL_REPAIR_DUPLICATE_PRIMARY_INDEX"


@dataclass
class RepairGuardDecision:
    """The guard's decision. `keep_original` True means: reject the repaired output and keep the
    primary output (with its original validation failure) -- the repair weakened/dropped evidence."""

    has_determine: bool
    preserved: bool
    keep_original: bool
    reason_codes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "has_determine": self.has_determine,
            "preserved": self.preserved,
            "keep_original": self.keep_original,
            "reason_codes": list(self.reason_codes),
        }


# ---------------------------------------------------------------------------
# Serialization / extraction (fenced-JSON adapter -- NOT a markdown parser)
# ---------------------------------------------------------------------------

def _answer_to_obj(a: Any) -> dict:
    if isinstance(a, DetermineAnswer):
        return {
            "index": a.index,
            "question_text": a.question_text,
            "answer": a.answer,
            "wsp97_label": a.wsp97_label,
            "evidence_refs": list(a.evidence_refs),
        }
    if isinstance(a, Mapping):
        refs = a.get("evidence_refs")
        return {
            "index": a.get("index"),
            "question_text": a.get("question_text", ""),
            "answer": a.get("answer", ""),
            "wsp97_label": a.get("wsp97_label", ""),
            # tolerant: a scalar/dict evidence_refs normalizes to [] instead of raising a
            # TypeError from iterating a non-iterable (CoR robustness).
            "evidence_refs": [str(r) for r in refs] if isinstance(refs, (list, tuple)) else [],
        }
    raise TypeError("answer must be DetermineAnswer or mapping")


def _fence_for(body: str) -> str:
    """A backtick fence STRICTLY longer than the longest backtick run in body, so no inner run
    (e.g. a ``` quoted inside a question_text JSON string) can close the block early -- the
    JSON layer and the Markdown-fence layer stay isolated and the block always round-trips."""
    longest = run = 0
    for ch in body:
        if ch == "`":
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return "`" * max(3, longest + 1)


def serialize_determine_answers(answers: Sequence[Any]) -> str:
    """Serialize an answer set to the canonical `## Determine Answers` fenced-JSON block."""
    payload = [_answer_to_obj(a) for a in answers]
    body = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
    fence = _fence_for(body)
    return DETERMINE_ANSWERS_HEADER + "\n\n" + fence + "json\n" + body + "\n" + fence


def extract_determine_answers(output_text: str) -> Optional[List[dict]]:
    """Extract the raw answer objects from an output's `## Determine Answers` fenced-JSON block.

    Returns None when there is NO Determine answer block (nothing to protect -- backward-compat
    no-op) OR when the block is present but its fenced payload cannot be parsed as a JSON array
    of objects (fail-closed: a destroyed/garbled block is treated by the caller as a dropped
    block -> KEEP_ORIGINAL). Returns a list (possibly empty) of raw dicts otherwise.
    """
    if not isinstance(output_text, str) or not output_text:
        return None
    headers = _answer_block_headers(output_text)
    if not headers:
        return None  # no Determine answer block at all
    if len(headers) > 1:
        return None  # AMBIGUOUS: multiple blocks (ATX and/or SETEXT) -> fail closed (a benign
        #              block must not shield a fabricated/weakened second block from the guard)
    m = headers[0]
    fence = _FENCE_BLOCK_RE.search(output_text, m.end())
    if not fence:
        return None  # header but no fenced payload -> unparseable (caller fails closed)
    try:
        data = json.loads(fence.group("body"))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, list) or not all(isinstance(x, Mapping) for x in data):
        return None
    return [dict(x) for x in data]


def _has_answer_block(output_text: str) -> bool:
    """True if a Determine-answers heading (ATX or SETEXT) is present (regardless of payload)."""
    return bool(_answer_block_headers(output_text))


def _questions_from_answers(answers: Sequence[Any]) -> List[DetermineQuestion]:
    """Synthesize a question list from a primary answer block (index + question_text), so the
    guard protects the primary's OWN answers when the prompt's Determine list is malformed or
    absent -- a self-describing block must never fail OPEN. Deduped by (coerced) index. The
    source_number is the index, so a CONTIGUOUS primary is well-formed (full validation runs)
    while a non-contiguous one fails the reused validator's contiguity check (fail-closed)."""
    out: List[DetermineQuestion] = []
    seen: set = set()
    for a in answers:
        obj = _answer_to_obj(a)
        idx = _safe_int(obj.get("index"))
        if idx in seen:
            continue
        seen.add(idx)
        out.append(DetermineQuestion(index=idx, text=str(obj.get("question_text", "")),
                                     source_number=idx))
    return out


# ---------------------------------------------------------------------------
# Protected-block context (injected into repair_minimal)
# ---------------------------------------------------------------------------

def build_protected_repair_context(primary_answers: Sequence[Any]) -> str:
    """Build the protected-block context to prepend to the repair_minimal context.

    Includes the exact serialized answer block PLUS a per-answer digest that surfaces the
    file:line evidence refs (so the repair model sees the evidence it must not drop -- not just
    a summary). Instructs the model to reproduce the block UNCHANGED and only add missing
    sections. Returns '' when there are no answers (no protected block -> no context change).
    """
    objs = [_answer_to_obj(a) for a in primary_answers]
    if not objs:
        return ""
    lines = [
        "## PROTECTED_DETERMINE_ANSWERS",
        "The primary pass produced the Determine answer block below. Reproduce it UNCHANGED in",
        "your repaired output (same `## Determine Answers` fenced JSON). You may ADD missing",
        "schema sections elsewhere. Do NOT drop or reorder answers, weaken a determination (e.g.",
        "OBSERVED -> a vague NEEDS_VERIFICATION), remove any file:line evidence ref, fabricate a",
        "new evidence anchor, or collapse the answers into prose.",
        "",
        "Protected answers and their evidence (must survive repair):",
    ]
    for o in objs:
        # Every interpolated field is collapsed to a single physical line: a free-form field
        # (esp. an evidence_ref) with an embedded newline could otherwise inject a rogue
        # "## Determine Answers" header/fence into the digest and break the context round-trip.
        refs = [_oneline(str(r)) for r in (o.get("evidence_refs") or [])]
        refs_str = ", ".join(refs) if refs else "(none -- NEEDS_VERIFICATION)"
        lines.append(
            "- #" + _oneline(str(o.get("index"))) + " [" + _oneline(str(o.get("wsp97_label"))) + "] "
            + _oneline(str(o.get("answer"))) + " -- evidence: " + refs_str)
    lines.append("")
    lines.append(serialize_determine_answers(primary_answers))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The guard (REUSES assert_repair_preserves -- no rules re-implemented here)
# ---------------------------------------------------------------------------

def _decide(
    qs: Sequence[DetermineQuestion],
    primary_answers: Sequence[Any],
    repaired_answers: Sequence[Any],
) -> RepairGuardDecision:
    """Core decision (assumes we have already decided to protect; qs may be prompt-parsed OR
    synthesized from the primary block). Duplicate-primary integrity + delegate to the contract."""
    prim = list(primary_answers)
    # A primary that answers the SAME question index more than once is internally contradictory
    # (which determination is authoritative is undefined -- a last-wins resolution could silently
    # accept a weakened label). We cannot certify preservation against an inconsistent primary ->
    # keep original, fail-closed. Block-level integrity check, not an answer-level rule.
    valid_q = {q.index for q in qs}
    prim_valid_indices = [i for i in (_safe_int(_answer_to_obj(a)["index"]) for a in prim)
                          if i in valid_q]
    if len(set(prim_valid_indices)) != len(prim_valid_indices):
        return RepairGuardDecision(
            has_determine=True, preserved=False, keep_original=True,
            reason_codes=[RepairGuardReason.DUPLICATE_PRIMARY_INDEX])
    # REUSES assert_repair_preserves for ALL answer-level rules (no rules re-implemented here). A
    # PRESENT-but-empty primary ([]) still delegates so a fabricating repair is caught.
    rep = assert_repair_preserves(qs, prim, repaired_answers)
    return RepairGuardDecision(
        has_determine=True, preserved=rep.valid, keep_original=not rep.valid,
        reason_codes=list(rep.reason_codes))


def guard_repair(
    questions: Sequence[DetermineQuestion],
    primary_answers: Sequence[Any],
    repaired_answers: Sequence[Any],
) -> RepairGuardDecision:
    """Decide whether a repaired answer set preserves the primary's Determine evidence.

    No-op (has_determine=False, keep_original=False) only when there is no well-formed question
    list. Otherwise the decision REUSES assert_repair_preserves: preserved == its verdict;
    keep_original == not preserved. This function contains no drop/reorder/weaken/fabricate rules.
    """
    qs = list(questions)
    if not qs or not is_determine_list_wellformed(qs):
        return RepairGuardDecision(has_determine=False, preserved=True, keep_original=False)
    return _decide(qs, primary_answers, repaired_answers)


def guard_repair_from_outputs(
    prompt: str,
    primary_output: str,
    repaired_output: str,
) -> RepairGuardDecision:
    """End-to-end guard over raw markdown outputs (used by the extension repair path).

    The decision to protect is gated on the PRIMARY emitting a Determine answer block -- NOT on the
    prompt (a malformed/absent prompt Determine list must not fail OPEN when the primary carries a
    genuine, self-describing block). Fail-closed edges:
      - primary has NO block at all -> no-op (existing schema-repair behavior unchanged).
      - primary HAS a block but it is ambiguous/unparseable -> KEEP_ORIGINAL.
      - primary block present; prompt questions used if well-formed, else SYNTHESIZED from the
        primary block (protect the primary's own answers).
      - repaired DROPPED the block (no header) or it is UNPARSEABLE -> KEEP_ORIGINAL.
    """
    primary_answers = extract_determine_answers(primary_output)
    if primary_answers is None:
        if _has_answer_block(primary_output):
            # primary emitted a block but it is ambiguous (multiple blocks) or unparseable -> a
            # protected-but-unreadable evidence block must not fail OPEN -> keep original.
            return RepairGuardDecision(
                has_determine=True, preserved=False, keep_original=True,
                reason_codes=[RepairGuardReason.UNPARSEABLE_DETERMINE_BLOCK])
        # no Determine block at all -> nothing to protect, existing behavior unchanged.
        return RepairGuardDecision(has_determine=False, preserved=True, keep_original=False)

    # Primary HAS a block. Prefer the prompt's parsed questions; if the prompt's Determine list is
    # malformed or absent, DERIVE the questions from the primary block itself (never fail OPEN).
    questions = parse_determine_questions(prompt if isinstance(prompt, str) else "")
    if not questions or not is_determine_list_wellformed(questions):
        questions = _questions_from_answers(primary_answers)

    repaired_answers = extract_determine_answers(repaired_output)
    if repaired_answers is None:
        # The repair dropped or garbled the entire protected block -> reject, keep original.
        reason = (RepairGuardReason.UNPARSEABLE_DETERMINE_BLOCK
                  if _has_answer_block(repaired_output)
                  else RepairGuardReason.DROPPED_DETERMINE_BLOCK)
        return RepairGuardDecision(
            has_determine=True, preserved=False, keep_original=True, reason_codes=[reason])

    if not questions:
        # A present-but-empty primary ([]) with no prompt questions yields no anchor. A repair that
        # materialized a non-empty block is not a reformat -> keep original; empty stays no-op.
        if repaired_answers:
            return RepairGuardDecision(
                has_determine=True, preserved=False, keep_original=True,
                reason_codes=[RepairGuardReason.UNPARSEABLE_DETERMINE_BLOCK])
        return RepairGuardDecision(has_determine=False, preserved=True, keep_original=False)

    return _decide(questions, primary_answers, repaired_answers)
