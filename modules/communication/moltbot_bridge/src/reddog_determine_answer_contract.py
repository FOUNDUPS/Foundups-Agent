#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RedDog Determine question/answer CONTRACT (REDDOG_DETERMINE_QUESTION_ANSWER_CONTRACT_PHASE1).

When a prompt carries a `Determine:` numbered list, RedDog MUST answer each item
explicitly, in order, with a WSP_97 truth label and file:LINE evidence (or an explicit
NEEDS_VERIFICATION when evidence is genuinely absent -- never a silent omission).

This module is a self-contained CONTRACT + VALIDATOR (it does NOT generate answers and is
NOT yet wired into RedDog's output path -- that is a later integration slice). It:
  - parses the Determine numbered list (preserving question text AND the author's source
    numbers, which must be a contiguous 1..N -- a fused/nested/gapped list is MALFORMED),
  - validates an answer set (one answer per question, in order, labeled, evidenced,
    no invented answers, no vague/traversal evidence), fail-closed,
  - normalizes file:line evidence refs and rejects bare paths / vague prose / traversal,
  - guards a repair pass so it cannot collapse answers into prose, drop the evidence
    packet, reorder, produce an invalid set, or CHANGE a determination.

EVIDENCE BOUNDARY (WSP_97, important): normalize_evidence_ref performs a SHAPE check only.
A well-formed `path:line` is NOT verified to exist, to be in-repo, or to actually support
the claim. Verifying that an evidence ref exists and supports the answer is a DOWNSTREAM
concern (the adversarial verifier panel slice). This contract stops silent omission,
invented answers, vague/traversal refs, and repair-drops-evidence; it does NOT (and cannot
here) prove an evidence ref is truthful.

NEEDS_VERIFICATION is allowed ONLY when evidence is absent (and then REQUIRED -- absence is
never silent). Every evidence-bearing answer (OBSERVED / INFERRED / SPECIFIED_NOT_IMPLEMENTED)
requires at least one file:line ref; a `Run Trace:<field>` reference is SUPPLEMENTARY and is
never the sole evidence (this tightens the audit doc's "path:line OR Run Trace" note, because
an all-Run-Trace audit is unverifiable at this layer -- Run Trace truth is a downstream
verifier-panel concern).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

# Frozen enums (contract).
ANSWER_VALUES = frozenset({"yes", "no", "partial", "unknown", "decision", "needs_verification"})
WSP97_LABELS = frozenset({"OBSERVED", "INFERRED", "SPECIFIED_NOT_IMPLEMENTED", "NEEDS_VERIFICATION"})
EVIDENCE_BEARING_LABELS = frozenset({"OBSERVED", "INFERRED", "SPECIFIED_NOT_IMPLEMENTED"})
NEEDS_VERIFICATION_ANSWER = "needs_verification"
NEEDS_VERIFICATION_LABEL = "NEEDS_VERIFICATION"

# Recognized source-file extensions (a dotted token with none of these, and no '/', is an
# identifier/prose -- e.g. "Orchestrator.dispatch", "valve.closed" -- not evidence).
_CODE_EXTENSIONS = frozenset({
    "py", "md", "json", "ts", "tsx", "js", "jsx", "txt", "yaml", "yml", "toml", "rs",
    "go", "html", "css", "cfg", "ini", "sh", "sql", "xml", "rst", "mjs", "cjs", "java",
})


def _safe_int(v: Any) -> int:
    """Coerce to int, FAILING CLOSED to 0 on any non-integer (never raises)."""
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _as_ref_list(v: Any) -> List[str]:
    """Coerce evidence_refs to a list of str, FAILING CLOSED to [] for any non-list/tuple (a
    scalar/dict/None). A model-emitted scalar `evidence_refs` (e.g. 7) must normalize to no
    evidence, never raise a TypeError from iterating a non-iterable (CoR robustness, mirrors
    _safe_int for index)."""
    if isinstance(v, (list, tuple)):
        return [str(r) for r in v]
    return []


class ReasonCode:
    """Static validation reason codes (no invented / free-text answers pass)."""

    NO_DETERMINE_BLOCK = "FAIL_NO_DETERMINE_BLOCK"
    DETERMINE_LIST_MALFORMED = "FAIL_DETERMINE_LIST_MALFORMED"
    MISSING_ANSWER = "FAIL_MISSING_ANSWER"
    ANSWER_REORDERED = "FAIL_ANSWER_REORDERED"
    INVENTED_ANSWER = "FAIL_INVENTED_ANSWER"
    DUPLICATE_ANSWER = "FAIL_DUPLICATE_ANSWER"
    QUESTION_TEXT_ALTERED = "FAIL_QUESTION_TEXT_ALTERED"
    INVALID_ANSWER_VALUE = "FAIL_INVALID_ANSWER_VALUE"
    MISSING_LABEL = "FAIL_MISSING_LABEL"
    INVALID_LABEL = "FAIL_INVALID_LABEL"
    LABEL_ANSWER_COUPLING = "FAIL_LABEL_ANSWER_COUPLING"
    VAGUE_EVIDENCE = "FAIL_VAGUE_EVIDENCE"
    MISSING_EVIDENCE = "FAIL_MISSING_EVIDENCE"
    NEEDS_VERIFICATION_MISUSE = "FAIL_NEEDS_VERIFICATION_MISUSE"
    # repair-preserve
    REPAIR_COLLAPSED_TO_PROSE = "FAIL_REPAIR_COLLAPSED_TO_PROSE"
    REPAIR_ALTERED_QUESTIONS = "FAIL_REPAIR_ALTERED_QUESTIONS"
    REPAIR_DROPPED_EVIDENCE = "FAIL_REPAIR_DROPPED_EVIDENCE"
    REPAIR_FABRICATED_EVIDENCE = "FAIL_REPAIR_FABRICATED_EVIDENCE"
    REPAIR_INVALID_ANSWERS = "FAIL_REPAIR_INVALID_ANSWERS"
    REPAIR_CHANGED_DETERMINATION = "FAIL_REPAIR_CHANGED_DETERMINATION"


@dataclass
class DetermineQuestion:
    index: int              # 1-based position in the parsed list
    text: str               # preserved question text
    source_number: int = 0  # the author's printed number (must be contiguous 1..N)


@dataclass
class DetermineAnswer:
    index: int
    question_text: str
    answer: str
    wsp97_label: str
    evidence_refs: List[str] = field(default_factory=list)

    @staticmethod
    def from_obj(obj: Mapping[str, Any]) -> "DetermineAnswer":
        return DetermineAnswer(
            # A non-integer index (e.g. "3abc") must FAIL CLOSED as index 0 (out of the 1..N
            # valid range -> INVENTED_ANSWER, real question stays MISSING_ANSWER), never raise
            # an uncaught ValueError inside the validator (CoR R20 robustness).
            index=_safe_int(obj.get("index", 0)),
            question_text=str(obj.get("question_text", "")),
            answer=str(obj.get("answer", "")).strip().lower(),
            wsp97_label=str(obj.get("wsp97_label", "")).strip(),
            evidence_refs=_as_ref_list(obj.get("evidence_refs")),
        )


@dataclass
class DetermineValidation:
    valid: bool
    reason_codes: List[str] = field(default_factory=list)
    per_question: Dict[int, List[str]] = field(default_factory=dict)
    answered_count: int = 0
    question_count: int = 0

    def to_dict(self) -> dict:
        return {"valid": self.valid, "reason_codes": list(self.reason_codes),
                "per_question": {k: list(v) for k, v in self.per_question.items()},
                "answered_count": self.answered_count, "question_count": self.question_count}


@dataclass
class RepairValidation:
    valid: bool
    reason_codes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_DETERMINE_MARKER = re.compile(r"^\s*determine\s*:", re.IGNORECASE)
# A numbered item: `N.`/`N)` then EITHER a space+body OR (no-space) a body starting with a
# NON-digit (so `8.verdict?` is an item but the decimal `3.14 is pi?` is not).
# Item numbers are 1-based ([1-9]\d*): a literal "0." line is NOT a Determine item.
# num is ASCII digits ([1-9][0-9]*, not \d*): a Unicode-digit "number" is not a real ordinal
# and must not be int()-coerced into a phantom source number.
_NUMBERED = re.compile(
    r"^(?P<indent>\s*)(?P<num>[1-9][0-9]*)\s*[.)](?:\s+(?P<body>\S.*)|(?P<body_ns>[^\d\s].*))$")


def _body_of(m: "re.Match") -> str:
    return m.group("body") or m.group("body_ns") or ""


# Same-line FUSION detector -- MAXIMALLY FAIL-CLOSED (fail-closed: one Determine item per
# physical line). After 10 CoR rounds, terminator/case/whitespace heuristics all proved
# leaky (spaceless "?8.", digit/quote-initial "8. 2-part", lowercase clauses), so the rule
# is now absolute: a question body may contain NO inline numbered ordinal (`N.` / `N)`
# followed by whitespace + content). ANY such token means a second item was fused onto the
# line -> the list is flagged MALFORMED (never silently split / absorbed / materialized).
# Note: the item's OWN leading number is consumed by _NUMBERED before the body, so a lone
# "8.verdict?" item is fine; decimals/versions ("3.14", "2.0") have a DIGIT after '.' and
# (not being preceded by ?/!) do not match. Alternatives:
#   (1) [?!]\s*\d+\s*[.)]\d  -- an ordinal abutting a sentence terminator even when a DIGIT
#       follows ("?8.2nd", "?8.2 State"); a genuine decimal never directly follows ? or !.
#   (2) \d+\s*[.)](?:\s+\S|[^\d\s])  -- a spaced ("8. remain") or spaceless non-digit
#       ("8.remain", "8)remain") inline ordinal, mirroring _NUMBERED's item openers.
# Authoring constraint (documented): a question referencing a number like "WSP 3." or
# "stage 8." must drop the trailing period ("WSP 3", "stage 8").
_FUSION = re.compile(r"[?!]\s*\d+\s*[.)]\d|\d+\s*[.)](?:\s+\S|[^\d\s])")
# Split on ASCII newlines ONLY. str.splitlines() also breaks on U+2028/U+2029/NEL/VT/FF/
# FS/GS/RS, which the "one item per physical line" fusion invariant does not account for --
# a fused line joined by one of those would be silently split. Keeping them INSIDE the
# physical line lets _FUSION catch the fused ordinal (Python \s covers those chars) -> MALFORMED.
_LINE_SPLIT = re.compile(r"\r\n|\r|\n")
# A Markdown code fence opener/closer (``` or ~~~, any indent, optional info string). The
# Determine block is TOP-LEVEL prose; a fenced region (a sample-output block, a numbered log
# transcript, or an EXAMPLE `Determine:` list) is NOT audit scope and its numbered lines must
# never be absorbed as questions. The parser tracks fence parity and ignores fenced content
# for BOTH the marker search and item collection (CoR R19: the parser was fence-blind and
# greedily over-counted a trailing fenced `9.`/`10.` sample into the question list).
_FENCE = re.compile(r"^\s*(?:```|~~~)")
# A skipped/folded line that itself BEGINS with a numbered ordinal is a dropped item,
# regardless of separator/case/digit-initial body ("8.2 State", "8)2 State", "8. remain",
# "8.remain", zero-padded "08. verdict"). A genuine decimal/version never starts such a line
# (it is always mid-body), so this does not false-positive. The number is captured so a lone
# "0." (value 0, NOT a 1-based item -- a benign aside) can be excluded from the drop check.
_FOLD_ORDINAL = re.compile(r"^\s*(?P<n>\d+)\s*[.)]")
# A SAME-LINE inline ordinal (after a boundary char) equal to the item's own number + 1 is
# a fused second item, even when its body is digit-initial ("...closed. 8.2 State...") which
# the shape-only _FUSION cannot distinguish from a decimal. A genuine decimal's integer part
# rarely equals num+1 in mid-body, so gating on the SEQUENTIAL value breaks the tie.
_SEQ_INLINE = re.compile(r"(?:^|[\s.,;:)!?])\s*(?P<n>[1-9]\d*)\s*[.)]\S")
_WS = re.compile(r"\s+")

# Sentinel source_number for a structurally-ambiguous list (an over-indented numbered line):
# it is unresolvable shape-only, so the list fails closed as MALFORMED.
_MALFORMED_SENTINEL = -1
_OVERINDENT_MARKER_TEXT = "<over-indented numbered line: Determine list must be flat>"
_UNCLOSED_FENCE_MARKER_TEXT = "<unclosed code fence after marker: Determine list truncated>"
_FENCED_TAIL_MARKER_TEXT = "<fenced ordinal continues the list tail: ambiguous with dropped items>"


def _norm_text(s: str) -> str:
    return _WS.sub(" ", str(s)).strip()


def parse_determine_questions(prompt: str) -> List[DetermineQuestion]:
    """Extract the ordered Determine questions (with the author's source numbers).

    Finds the first `Determine:` marker, then collects the base-indented numbered items
    (`N.` / `N)`), ONE per physical line (same-line fusion is NOT split -- it is detected
    and flagged MALFORMED by is_determine_list_wellformed). A mis-indented item whose number
    sequentially continues the list is materialized; a genuine nested sub-list (restarts)
    is folded as continuation; notes/section headers are skipped (never truncate). Source
    numbers are preserved so a fused / gapped / restarted list is detectable as MALFORMED.
    """
    if not isinstance(prompt, str) or not prompt:
        return []
    lines = _LINE_SPLIT.split(prompt)
    # Find the first TOP-LEVEL `Determine:` marker -- one that is NOT inside a ``` / ~~~ code
    # fence. A fenced `Determine:` (an example / sample block) is skipped so its numbered lines
    # cannot be mistaken for the real audit scope (CoR R19). An unclosed fence that swallows
    # the only marker yields no block -> NO_DETERMINE_BLOCK (fail-closed).
    start = None
    in_fence = False
    for i, ln in enumerate(lines):
        if _FENCE.match(ln):
            in_fence = not in_fence
            continue
        if not in_fence and _DETERMINE_MARKER.match(ln):
            start = i
            break
    if start is None:
        return []

    questions: List[DetermineQuestion] = []
    cur_body: Optional[List[str]] = None
    cur_num: Optional[int] = None
    base_indent: Optional[int] = None
    pending_blank = False
    saw_overindent = False
    fenced_ordinals: set = set()  # ordinal-initial numbers (>=1) seen INSIDE a code fence

    def flush() -> None:
        nonlocal cur_body, cur_num
        if cur_body is not None:
            questions.append(DetermineQuestion(
                len(questions) + 1, _norm_text(" ".join(cur_body)), cur_num or 0))
            cur_body, cur_num = None, None

    def open_line(num: int, body: str) -> None:
        # ONE item per physical line. Same-line fusion is NOT split here -- the fused text
        # stays in the body and is flagged MALFORMED by is_determine_list_wellformed (via
        # _FUSION). Additionally, a same-line inline ordinal equal to num+1 (incl. a
        # digit-initial "8.2" body that _FUSION's decimal-exclusion misses) is flagged here.
        nonlocal cur_body, cur_num, saw_overindent
        for mm in _SEQ_INLINE.finditer(body):
            if int(mm.group("n")) == num + 1:
                saw_overindent = True
                break
        cur_num, cur_body = num, [body]

    in_fence = False
    for ln in lines[start + 1:]:
        if _FENCE.match(ln):
            # A code fence is a structural boundary: close any open item and IGNORE all
            # fenced content. Numbered lines inside a fence (sample output, a numbered log,
            # an example Determine block) are NOT Determine items and must not be absorbed
            # (CoR R19 over-count). The list may legitimately resume with real items after
            # the fence closes; source-number contiguity still guards over/under-count.
            flush()
            in_fence = not in_fence
            pending_blank = True  # a real item after the fence is fresh, never a wrap-fold
            continue
        if in_fence:
            # Record ordinal-initial numbers inside the fence. A fenced ordinal that would
            # CONTIGUOUSLY continue the real list (value == materialized_count + 1) is
            # indistinguishable, shape-only, from a dropped-then-fenced tail item, so it fails
            # closed at EOF (CoR R22). A restart-at-1 or non-contiguous fenced sample leaves
            # count+1 absent and stays benign.
            fo = _FOLD_ORDINAL.match(ln)
            if fo and int(fo.group("n")) >= 1:
                fenced_ordinals.add(int(fo.group("n")))
            continue
        m = _NUMBERED.match(ln)
        if m:
            indent = len(m.group("indent").expandtabs())
            if base_indent is None:
                base_indent = indent
            if indent > base_indent:
                # An over-indented numbered line is AMBIGUOUS: a mis-indented real item
                # (editor/paste artifact) vs a sequentially-numbered nested sub-item. Both
                # are indistinguishable shape-only, so -- like same-line fusion -- the list
                # fails closed as MALFORMED (Determine lists must be FLAT: one item per line,
                # no indentation variation). Flag it REGARDLESS of a preceding blank line
                # (base_indent is pinned to the first item); fold the text if an item is open.
                if cur_body is not None:
                    cur_body.append(ln.strip())
                saw_overindent = True
                pending_blank = False
                continue
            # WRAP ambiguity: a base-indent numbered line that sequentially continues the
            # list (num == cur+1) but follows an UNTERMINATED open item (its text so far does
            # not end in ? ! .) is a wrapped continuation-that-starts-with-the-next-ordinal
            # vs a real next item -- indistinguishable shape-only. Fold it so its inline
            # ordinal trips _FUSION -> MALFORMED (fail-closed). Normal items end in '?' (or
            # '.'), so consecutive real items are unaffected.
            if (cur_body is not None and not pending_blank
                    and int(m.group("num")) == (cur_num or 0) + 1
                    and not _norm_text(" ".join(cur_body)).rstrip().endswith(("?", "!", "."))):
                cur_body.append(ln.strip())
                saw_overindent = True  # a wrapped line starting with an ordinal = dropped item
                pending_blank = False
                continue
            flush()
            open_line(int(m.group("num")), _body_of(m))
            pending_blank = False
        elif not ln.strip():
            flush()          # blank line closes the current item; list may resume or end
            pending_blank = True
        else:
            # non-numbered, non-blank line. If it STARTS with an ordinal whose value is a valid
            # item number (>=1) -- a digit-initial body "8.2 State" / "8)2 ..." or a zero-padded
            # "08. ..." that _NUMBERED does not open -- it is a possibly-DROPPED item and must
            # trip MALFORMED, whether or not an item is open or a blank intervened (CoR R21: the
            # blank-preceded / no-open-item path previously skipped this check and silently
            # dropped the item). A lone "0." (value 0) is NOT a 1-based item -> benign aside.
            # Any other prose (note / header / aside) is SKIPPED (never truncate) and folded into
            # an open item only when no blank intervened.
            fo = _FOLD_ORDINAL.match(ln)
            if fo and int(fo.group("n")) >= 1:
                saw_overindent = True
            if cur_body is not None and not pending_blank:
                cur_body.append(ln.strip())
    flush()
    # Structural ambiguity -> mark MALFORMED (fail-closed). Three triggers:
    #  - saw_overindent: an over-indented numbered line / ordinal-initial fold.
    #  - in_fence at EOF: an UNCLOSED (odd-parity) code fence opened AFTER the marker
    #    silently swallowed the tail items to EOF (CoR R20). Symmetric partner to an unclosed
    #    fence that swallows the MARKER (-> NO_DETERMINE_BLOCK above).
    #  - fenced_tail: a BALANCED fence enclosed a numbered ordinal == materialized_count + 1,
    #    i.e. what would be the CONTIGUOUS TAIL of the list (CoR R22). The remaining prefix is
    #    contiguous, so contiguity alone cannot catch it; shape-only it is indistinguishable
    #    from a dropped-then-fenced real tail item -> fail closed.
    fenced_tail = (len(questions) + 1) in fenced_ordinals
    if saw_overindent or in_fence or fenced_tail:
        if saw_overindent:
            marker = _OVERINDENT_MARKER_TEXT
        elif in_fence:
            marker = _UNCLOSED_FENCE_MARKER_TEXT
        else:
            marker = _FENCED_TAIL_MARKER_TEXT
        questions.append(DetermineQuestion(len(questions) + 1, marker, _MALFORMED_SENTINEL))
    return questions


def is_determine_list_wellformed(questions: Sequence[DetermineQuestion]) -> bool:
    """The author's source numbers must be a contiguous 1..N (no fusion/gap/restart/dup).

    Only a FULLY hand-constructed list (ALL source numbers <=0) is exempt (cannot be
    checked). A single 0/negative MIXED with real parser numbers is NOT exempt -- it falls
    through to the contiguity check and fails MALFORMED (parser item numbers are 1-based).
    """
    nums = [q.source_number for q in questions]
    if any(n == _MALFORMED_SENTINEL for n in nums):
        return False  # an over-indented numbered line made the structure ambiguous
    if nums and all(n <= 0 for n in nums):
        return True  # fully hand-constructed (no source numbers at all) -- cannot be checked
    if nums != list(range(1, len(questions) + 1)):
        return False  # a mixed 0/negative with real numbers falls through here -> MALFORMED
    # A same-line fusion (a sentence terminator immediately followed by an inline ordinal,
    # e.g. "Q3? 4. Q4?" / "...default. 8. State...") is ambiguous with an authored intra-
    # question boundary -> fail-closed as MALFORMED, never guessed. Prose numbers after a
    # word ("reach stage 8.", "map to WSP 3.") lack the terminator and do NOT trip this.
    if any(_FUSION.search(q.text) for q in questions):
        return False
    return True


# ---------------------------------------------------------------------------
# Evidence normalization  (SHAPE check only -- see EVIDENCE BOUNDARY in module docstring)
# ---------------------------------------------------------------------------

_PATH = r"[A-Za-z0-9_.\-/]+"
# LINE IS MANDATORY for path refs: a bare path is NOT evidence-grade. The line locator is
# ASCII digits ([0-9]+, NOT \d+): Python's \d matches Unicode decimal digits (Arabic-Indic,
# fullwidth, ...) which int() then coerces to a positive int, so a junk ref like `file.py:<U+0669>`
# would otherwise pass the shape gate as a resolvable file:line. No editor / grep / LSP /
# downstream verifier can resolve a non-ASCII line number -- it is the same defect class as
# `x.py:notaline` and must fail closed (CoR R20).
_EVIDENCE_RE = re.compile(r"^(?P<path>" + _PATH + r")(?:#L(?P<l1>[0-9]+)|:(?P<l2>[0-9]+))$")
_RUN_TRACE_RE = re.compile(r"^run[_\- ]?trace\s*:\s*(?P<field>[A-Za-z0-9_.\-]+)$", re.IGNORECASE)


def normalize_evidence_ref(ref: str) -> Optional[str]:
    """Normalize a single evidence ref to canonical `path:line` or `run_trace:field`.

    Accepts `path:line`, `path#Lline` (both -> `path:line`), or `Run Trace:<field>`.
    REJECTS (returns None): a bare path with no line, vague prose (has spaces), dotted
    identifiers with no source-file extension ("Orchestrator.dispatch"), traversal/absolute
    paths ("../../.env:1", "/etc/passwd:1"), and line 0. SHAPE ONLY -- existence/truth of
    the ref is NOT checked here (see EVIDENCE BOUNDARY).
    """
    if not isinstance(ref, str):
        return None
    s = ref.strip()
    if not s:
        return None
    rt = _RUN_TRACE_RE.match(s)  # checked first (legitimately contains the space in "Run Trace")
    if rt:
        return "run_trace:" + rt.group("field")
    if " " in s:
        return None  # vague prose ("the file says") has spaces
    m = _EVIDENCE_RE.match(s)
    if not m:
        return None  # no mandatory line locator -> not evidence-grade
    path = m.group("path")
    if path.startswith("/") or ".." in path.split("/"):
        return None  # absolute or traversal
    # The FINAL path segment must be a source FILE (whitelisted extension), for ALL paths
    # -- so "orchestrator/dispatch:1" (a slash path with no file) is rejected, not just
    # the slash-free "Orchestrator.dispatch:1".
    last = path.rsplit("/", 1)[-1]
    if "." not in last:
        return None
    base, ext = last.rsplit(".", 1)
    if ext.lower() not in _CODE_EXTENSIONS:
        return None
    if not re.search(r"[A-Za-z0-9]", base):
        return None  # degenerate filename like ".py" / "....py" (no real basename)
    line = m.group("l1") or m.group("l2")
    if int(line) <= 0:
        return None
    return f"{path}:{line}"


def _is_file_line(norm_ref: str) -> bool:
    return ":" in norm_ref and not norm_ref.startswith("run_trace:")


def _normalized_evidence_set(refs: Sequence[str]) -> Tuple[set, bool]:
    out, ok = set(), True
    for r in refs:
        n = normalize_evidence_ref(r)
        if n is None:
            ok = False
        else:
            out.add(n)
    return out, ok


# ---------------------------------------------------------------------------
# Answer-set validation
# ---------------------------------------------------------------------------

def _coerce_answers(answers: Sequence[Any]) -> List[DetermineAnswer]:
    return [a if isinstance(a, DetermineAnswer) else DetermineAnswer.from_obj(a) for a in answers]


def validate_answer_set(
    questions: Sequence[DetermineQuestion],
    answers: Sequence[Any],
) -> DetermineValidation:
    """Fail-closed validation that `answers` covers every Determine question explicitly,
    in order, labeled, and evidenced. No invented answers; no vague/traversal evidence;
    absence of evidence is only OK as an explicit NEEDS_VERIFICATION."""
    qs = list(questions)
    ans = _coerce_answers(answers)
    result = DetermineValidation(valid=False, question_count=len(qs))

    if not qs:
        result.reason_codes.append(ReasonCode.NO_DETERMINE_BLOCK)
        return result
    if not is_determine_list_wellformed(qs):
        result.reason_codes.append(ReasonCode.DETERMINE_LIST_MALFORMED)
        return result  # a mis-parsed list cannot be certified complete

    by_index: Dict[int, List[DetermineAnswer]] = {}
    for a in ans:
        by_index.setdefault(a.index, []).append(a)

    valid_indices = {q.index for q in qs}
    for a in ans:
        if a.index not in valid_indices:
            result.reason_codes.append(ReasonCode.INVENTED_ANSWER)
    for idx, group in by_index.items():
        if idx in valid_indices and len(group) > 1:
            result.reason_codes.append(ReasonCode.DUPLICATE_ANSWER)

    ordered_indices = [a.index for a in ans if a.index in valid_indices]
    if ordered_indices != sorted(ordered_indices):
        result.reason_codes.append(ReasonCode.ANSWER_REORDERED)

    result.answered_count = len({a.index for a in ans if a.index in valid_indices})

    for q in qs:
        codes: List[str] = []
        group = by_index.get(q.index, [])
        if not group:
            result.per_question[q.index] = [ReasonCode.MISSING_ANSWER]
            continue
        a = group[0]
        if _norm_text(a.question_text) != _norm_text(q.text):
            codes.append(ReasonCode.QUESTION_TEXT_ALTERED)
        if a.answer not in ANSWER_VALUES:
            codes.append(ReasonCode.INVALID_ANSWER_VALUE)
        if not a.wsp97_label:
            codes.append(ReasonCode.MISSING_LABEL)
        elif a.wsp97_label not in WSP97_LABELS:
            codes.append(ReasonCode.INVALID_LABEL)

        ev_set, ev_ok = _normalized_evidence_set(a.evidence_refs)
        is_nv = (a.answer == NEEDS_VERIFICATION_ANSWER) or (a.wsp97_label == NEEDS_VERIFICATION_LABEL)
        if is_nv:
            # NEEDS_VERIFICATION allowed ONLY when evidence is absent, answer+label BOTH set.
            if not (a.answer == NEEDS_VERIFICATION_ANSWER
                    and a.wsp97_label == NEEDS_VERIFICATION_LABEL
                    and len(a.evidence_refs) == 0):
                codes.append(ReasonCode.NEEDS_VERIFICATION_MISUSE)
        else:
            # evidence-bearing answer: label must be evidence-bearing + real evidence present.
            if a.wsp97_label in WSP97_LABELS and a.wsp97_label not in EVIDENCE_BEARING_LABELS:
                codes.append(ReasonCode.LABEL_ANSWER_COUPLING)
            if not a.evidence_refs:
                codes.append(ReasonCode.MISSING_EVIDENCE)
            elif not ev_ok or not ev_set:
                codes.append(ReasonCode.VAGUE_EVIDENCE)
            elif not any(_is_file_line(e) for e in ev_set):
                # every evidence-bearing answer needs >=1 file:line anchor; a Run Trace
                # field is SUPPLEMENTARY, never the sole evidence (tightens audit-doc s7
                # per the adversarial finding that an all-Run-Trace audit is unverifiable).
                codes.append(ReasonCode.LABEL_ANSWER_COUPLING)
        if codes:
            result.per_question[q.index] = codes

    for codes in result.per_question.values():
        result.reason_codes.extend(codes)
    seen: set = set()
    result.reason_codes = [c for c in result.reason_codes if not (c in seen or seen.add(c))]
    result.valid = not result.reason_codes
    return result


# ---------------------------------------------------------------------------
# Repair-preserve guard
# ---------------------------------------------------------------------------

def assert_repair_preserves(
    original_questions: Sequence[DetermineQuestion],
    original_answers: Sequence[Any],
    repaired_answers: Sequence[Any],
) -> RepairValidation:
    """A repair pass may rewrite prose but MUST NOT collapse answers into summary prose,
    reorder/alter the Determine list, drop the evidence packet, produce an invalid set, or
    CHANGE a determination (answer value / label)."""
    qs = list(original_questions)
    orig = _coerce_answers(original_answers)
    rep = _coerce_answers(repaired_answers)
    result = RepairValidation(valid=False)

    # 1. one answer per question survives (no collapse to prose) AND every ORIGINAL-answered
    #    index survives. The len(qs) check catches a collapse below the question count; the
    #    original-coverage check additionally catches a repair that drops an answer the primary
    #    produced at an index OUTSIDE 1..len(qs) (a surplus/over-answered index) -- those are
    #    invisible to the per-question (`for q in qs`) steps, so without this a surplus answer
    #    could be dropped with its evidence and still pass (fail-closed instead).
    rep_indices = [a.index for a in rep if a.index in {q.index for q in qs}]
    rep_all_indices = {a.index for a in rep}
    orig_answered_indices = {a.index for a in orig}
    if len(set(rep_indices)) < len(qs) or not orig_answered_indices.issubset(rep_all_indices):
        result.reason_codes.append(ReasonCode.REPAIR_COLLAPSED_TO_PROSE)

    # 2. Determine list preserved (indices + question text)
    rep_by_index = {a.index: a for a in rep}
    for q in qs:
        ra = rep_by_index.get(q.index)
        if ra is None or _norm_text(ra.question_text) != _norm_text(q.text):
            result.reason_codes.append(ReasonCode.REPAIR_ALTERED_QUESTIONS)
            break

    # 3. evidence preserved: repaired evidence must be a SUPERSET of the UNION of every
    #    original occurrence's valid refs at that index (a duplicate original whose last
    #    entry is weak must not let a repair silently swap away real evidence).
    orig_by_index = {a.index: a for a in orig}
    orig_ev_by_index: Dict[int, set] = {}
    for a in orig:
        s, _ = _normalized_evidence_set(a.evidence_refs)
        orig_ev_by_index.setdefault(a.index, set()).update(s)
    for q in qs:
        ra = rep_by_index.get(q.index)
        if ra is None or q.index not in orig_ev_by_index:
            continue
        r_set, _ = _normalized_evidence_set(ra.evidence_refs)
        o_set = orig_ev_by_index[q.index]
        if not o_set.issubset(r_set):
            result.reason_codes.append(ReasonCode.REPAIR_DROPPED_EVIDENCE)
            break
        # A repair REFORMATS prose; it may NOT SOURCE a file:line anchor the original lacked.
        # If the original had zero normalizable file:line evidence at this index (its refs were
        # vague / empty / line-0 / Run-Trace-only) but the repaired answer now presents one, the
        # repair FABRICATED the audit anchor. The subset check above is vacuously satisfied by an
        # empty original set (empty.issubset(anything) is True), so this is the guard that stops
        # "repair rewrites evidence IN" (CoR R19). Adding refs to an answer that ALREADY had a
        # file:line anchor stays allowed (repair may strengthen, not manufacture, evidence).
        if (not any(_is_file_line(e) for e in o_set)
                and any(_is_file_line(e) for e in r_set)):
            result.reason_codes.append(ReasonCode.REPAIR_FABRICATED_EVIDENCE)
            break

    # 3b. a repair may not MATERIALIZE an anchored answer for a Determine question the original
    #     never answered: sourcing a fresh file:line-anchored determination for an OMITTED index
    #     is fabrication, not reformatting (a repair completes formatting, it does not complete
    #     the audit). The per-index checks in step 3/4 SKIP omitted indices (they key on the
    #     original), so an invented answer at a brand-new index would otherwise pass unchecked
    #     (CoR R20). An honest materialized NEEDS_VERIFICATION abstention (no file:line) is
    #     allowed -- surfacing "unanswered" explicitly is the contract's anti-omission intent.
    orig_indices = {a.index for a in orig}
    valid_q_indices = {q.index for q in qs}
    for a in rep:
        if a.index in valid_q_indices and a.index not in orig_indices:
            r_set, _ = _normalized_evidence_set(a.evidence_refs)
            if any(_is_file_line(e) for e in r_set):
                result.reason_codes.append(ReasonCode.REPAIR_FABRICATED_EVIDENCE)
                break

    # 4. determination unchanged: repair rewrites PROSE, not the answer value / label
    for q in qs:
        oa, ra = orig_by_index.get(q.index), rep_by_index.get(q.index)
        if oa is None or ra is None:
            continue
        if oa.answer != ra.answer or oa.wsp97_label != ra.wsp97_label:
            result.reason_codes.append(ReasonCode.REPAIR_CHANGED_DETERMINATION)
            break

    # 5. the repaired set must itself be a VALID answer set (order/dup/label/evidence)
    if not validate_answer_set(qs, rep).valid:
        result.reason_codes.append(ReasonCode.REPAIR_INVALID_ANSWERS)

    seen: set = set()
    result.reason_codes = [c for c in result.reason_codes if not (c in seen or seen.add(c))]
    result.valid = not result.reason_codes
    return result


def build_answer_template(questions: Sequence[DetermineQuestion]) -> List[dict]:
    """Skeleton one-answer-per-question set (blank), to enforce the shape at generation
    time so no Determine item is silently omitted."""
    return [
        {"index": q.index, "question_text": q.text, "answer": "", "wsp97_label": "", "evidence_refs": []}
        for q in questions
    ]
