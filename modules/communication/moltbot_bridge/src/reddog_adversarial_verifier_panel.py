#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RedDog adversarial verifier PANEL (REDDOG_ADVERSARIAL_VERIFIER_PANEL_PHASE1).

The Determine contract (#933) validates answer SHAPE; the repair guard (#934) preserves evidence
through repair; symbol windows (#935) deliver deep evidence. This module adds the missing layer: a
DETERMINISTIC second pass that VERIFIES each Determine answer's cited file:line evidence EXISTS and
SUPPORTS the claim, and does NOT CONTRADICT the authoritative scorecard telemetry. Fail-closed: an
unverifiable / unreadable / unsupported / contradicted / evidence-absent claim is REFUTED -- it never
passes by default.

DETERMINISTIC panel (no live model, no network, no randomness): per claim, an independent set of
refute lenses (existence / support / consistency) runs; the aggregation is FAIL-CLOSED -- a claim is
verified ONLY if NO lens refutes it. REUSES reddog_determine_answer_contract (answer shape, WSP_97
labels, evidence normalization); it adds NO answer-level rules. Evidence reading is INJECTED
(read_evidence(norm_ref) -> content|None) so the core is PURE (stdlib-only, no subprocess/os/network/
open); the live path injects the governed direct-read (path#symbol / path:line window).

APPENDIX A (HoloIndex freshness boundary, 012 ruling): the verifier is QUERY-ONLY -- it NEVER
re-indexes. It DETECTS an INDEX_GAP from the scorecard and EMITS an advisory INDEX_GAP_EVENT /
INDEX_GAP_RECOMMENDATION; it performs NO live WRE enqueue, CI mutation, or re-index (a governed
downstream slice owns that). direct-read success is NOT HoloIndex freshness success -- a claim whose
evidence was reachable only via direct-read while the index missed it is still VERIFIED (the file is
real), but the freshness gap is RECORDED in the emitted event, not silently dropped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_determine_answer_contract import (
    DetermineAnswer,
    NEEDS_VERIFICATION_ANSWER,
    NEEDS_VERIFICATION_LABEL,
    WSP97_LABELS,
    _is_file_line,
    normalize_evidence_ref,
)


# Per-claim verdicts. OBSERVED_VERIFIED / INFERRED are the answer's own WSP_97 label AFTER the
# evidence passed every lens; NEEDS_VERIFICATION is an honest abstention (no evidence claimed);
# REFUTED means at least one lens refuted the claim -> fail-closed.
class Verdict:
    OBSERVED_VERIFIED = "OBSERVED_VERIFIED"
    INFERRED = "INFERRED"
    NEEDS_VERIFICATION = "NEEDS_VERIFICATION"
    REFUTED = "REFUTED"


class RefuteReason:
    EVIDENCE_REF_INVALID = "REFUTE_EVIDENCE_REF_INVALID"     # not a normalizable file:line ref
    EVIDENCE_ABSENT = "REFUTE_EVIDENCE_ABSENT"               # read_evidence returned None/empty
    SUPPORT_NOT_FOUND = "REFUTE_SUPPORT_NOT_FOUND"           # window does not reference the claim's subject
    SCORECARD_CONTRADICTION = "REFUTE_SCORECARD_CONTRADICTION"   # cited path rejected/absent per telemetry
    INVALID_LABEL = "REFUTE_INVALID_LABEL"                   # answer carries a non-WSP_97 label
    NO_EVIDENCE_FOR_CLAIM = "REFUTE_NO_EVIDENCE_FOR_CLAIM"   # evidence-bearing answer with zero file:line refs
    MALFORMED_ANSWER = "REFUTE_MALFORMED_ANSWER"             # answer entry is not a mapping/answer object


# A code-identifier anchor from a question: snake_case, CamelCase, or ALL_CAPS token (>=4 chars). Prose
# words ("does", "gate", "the") are NOT anchors, so support is only enforced when the claim actually
# names a symbol/subject that should appear in its evidence.
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# Ubiquitous boilerplate identifiers that appear in nearly every file, so a window merely containing
# one proves NOTHING about the claim's operative subject. Excluded from the support-anchor set so a
# question that incidentally names boilerplate (e.g. "... after get_logger init") cannot have an
# unrelated window 'support' it via that decoy while the real subject is absent.
_SUPPORT_STOPWORDS = frozenset({
    "get_logger", "getlogger", "logger", "logging", "__init__", "__main__", "__name__", "__file__",
    "__doc__", "__enter__", "__exit__", "__repr__", "__str__", "self", "cls", "super", "args", "kwargs",
    "main", "run", "setup", "teardown", "init", "wrapper", "decorator", "callback",
})


@dataclass
class ClaimVerdict:
    index: int
    verdict: str
    refutations: List[str] = field(default_factory=list)
    checked_refs: List[str] = field(default_factory=list)   # normalized file:line refs actually checked
    notes: List[str] = field(default_factory=list)          # transparency (e.g. support not checkable)

    @property
    def refuted(self) -> bool:
        return self.verdict == Verdict.REFUTED


# A note (NOT a refutation) surfaced when support could not be checked deterministically because the
# claim's question is pure prose (no code-identifier subject to match). The claim still verifies on
# existence + consistency; semantic support of a prose claim is a downstream (model-panel) concern.
NOTE_SUPPORT_UNCHECKABLE = "NOTE_SUPPORT_NOT_DETERMINISTICALLY_CHECKABLE"


def _as_list(v: Any) -> list:
    """Coerce a scorecard sequence field to a list, FAILING CLOSED to [] for any non-list/tuple (a
    malformed scalar/None scorecard must not crash the verifier)."""
    return list(v) if isinstance(v, (list, tuple)) else []


@dataclass
class VerifierReport:
    claims: List[ClaimVerdict] = field(default_factory=list)
    verified: bool = False                  # True iff NO claim is REFUTED
    refuted_count: int = 0
    index_gap_event: Optional[dict] = None  # advisory only (non-mutating)

    def to_dict(self) -> dict:
        return {
            "verified": self.verified,
            "refuted_count": self.refuted_count,
            "claims": [{"index": c.index, "verdict": c.verdict,
                        "refutations": list(c.refutations), "checked_refs": list(c.checked_refs),
                        "notes": list(c.notes)}
                       for c in self.claims],
            "index_gap_event": self.index_gap_event,
        }


# ---------------------------------------------------------------------------
# Anchors / support
# ---------------------------------------------------------------------------

def _claim_anchors(question_text: str) -> List[str]:
    """Code-identifier anchors a claim's evidence should reference (snake_case / CamelCase / ALL_CAPS,
    >=4 chars). Empty when the question is pure prose (support is then not deterministically checkable)."""
    anchors = []
    seen = set()
    for tok in _IDENT_RE.findall(str(question_text or "")):
        if len(tok) < 4:
            continue
        is_snake = "_" in tok
        is_camel = any(c.isupper() for c in tok[1:]) and any(c.islower() for c in tok)
        is_allcaps = tok.isupper()
        if not (is_snake or is_camel or is_allcaps):
            continue
        key = tok.lower()
        if key in seen or key in _SUPPORT_STOPWORDS:   # skip dups + ubiquitous boilerplate decoys
            continue
        seen.add(key)
        anchors.append(tok)
    return anchors


# ---------------------------------------------------------------------------
# Refute lenses (each returns a list of RefuteReason codes; empty == no objection)
# ---------------------------------------------------------------------------

def _lens_existence(answer: DetermineAnswer, file_line_refs: List[str],
                    read_evidence: Callable[[str], Optional[str]],
                    scorecard: Mapping[str, Any]) -> List[str]:
    """EXISTENCE: every cited file:line ref must read to real, non-empty content."""
    if not file_line_refs:
        return [RefuteReason.NO_EVIDENCE_FOR_CLAIM]
    reasons = []
    for ref in file_line_refs:
        try:
            content = read_evidence(ref)
        except Exception:
            content = None
        # Content must have at least one VISIBLE character (printable + non-whitespace). str.strip()
        # does NOT remove NUL / zero-width chars, so a window of only NUL or zero-width space would
        # read as present; require a genuinely visible glyph so such invisible windows fail closed.
        if not (isinstance(content, str) and any(ch.isprintable() and not ch.isspace() for ch in content)):
            reasons.append(RefuteReason.EVIDENCE_ABSENT)
            break
    return reasons


def _is_operative_anchor(tok: str) -> bool:
    """An OPERATIVE symbol (a specific function/class/constant a claim is ABOUT) vs a bare domain noun.
    snake_case / CONSTANT_CASE (has '_') is operative; CamelCase is operative only with >=2 internal
    case transitions ('FoundUpJob', 'FoundUpGenesisEnvelope'), so bare domain nouns ('FoundUp',
    'OpenClaw') are NOT treated as operative (they appear everywhere and would over-refute)."""
    if "_" in tok:
        return True
    return sum(1 for i in range(1, len(tok)) if tok[i].isupper() and tok[i - 1].islower()) >= 2


def _lens_support(answer: DetermineAnswer, file_line_refs: List[str],
                  read_evidence: Callable[[str], Optional[str]],
                  scorecard: Mapping[str, Any]) -> List[str]:
    """SUPPORT: the cited windows must reference the claim's OPERATIVE subject(s). EVERY operative
    symbol the question names (snake_case / multi-word CamelCase / CONSTANT_CASE) must appear as a
    whole token in some cited window -- so a comparison/decoy symbol (e.g. extract_foundup in a
    build_foundup claim) cannot alone carry support. A question that names ONLY bare domain nouns /
    ubiquitous ALL_CAPS words (no operative symbol) -- like pure prose -- is NOT decidable here: a
    single common decoy word ('INDEX', 'FoundUp') appearing in an unrelated window proves NOTHING, so
    support ABSTAINS (existence + consistency still gate, and the caller surfaces
    NOTE_SUPPORT_UNCHECKABLE) rather than false-verifying on a decoy or false-refuting a legit noun."""
    operative = [a for a in _claim_anchors(getattr(answer, "question_text", "")) if _is_operative_anchor(a)]
    if not operative:
        return []                       # no operative subject -> support is not deterministically decidable
    required = {a.lower() for a in operative}
    matched: set = set()
    for ref in file_line_refs:
        try:
            content = read_evidence(ref)
        except Exception:
            content = None
        if isinstance(content, str) and content:
            # WHOLE-identifier match, not substring: 'build_foundup' must be a real token in the
            # window, so 'prebuild_foundups_registry' / 'build_foundup_v2' do NOT falsely support it.
            toks = {t.lower() for t in _IDENT_RE.findall(content)}
            matched |= (required & toks)
    # EVERY operative symbol must be present (a decoy/comparison symbol cannot alone carry the claim).
    return [] if required.issubset(matched) else [RefuteReason.SUPPORT_NOT_FOUND]


def _lens_consistency(answer: DetermineAnswer, file_line_refs: List[str],
                      read_evidence: Callable[[str], Optional[str]],
                      scorecard: Mapping[str, Any]) -> List[str]:
    """CONSISTENCY: a cited evidence path must not be one the authoritative scorecard says was REJECTED
    / never available. Citing a path the telemetry proves was not readable contradicts the claim."""
    rejected = set()
    for item in _as_list(scorecard.get("direct_read_rejected")):
        if isinstance(item, Mapping):
            p = item.get("path")
        else:
            p = item
        if isinstance(p, str) and p:
            rejected.add(_path_of(p))
    if not rejected:
        return []
    for ref in file_line_refs:
        if _path_of(ref) in rejected:
            return [RefuteReason.SCORECARD_CONTRADICTION]
    return []


DEFAULT_PANEL: List[Callable[..., List[str]]] = [_lens_existence, _lens_support, _lens_consistency]


def _path_of(ref: str) -> str:
    """Bare path of a `path:line` / `path#Lline` / `path` ref (lower-cased), for scorecard comparison."""
    s = str(ref or "").replace("\\", "/")
    s = s.split("#", 1)[0]
    # strip a trailing :<digits> or #L<digits> line locator
    s = re.sub(r":\d+$", "", s)
    return s.strip().lower()


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------

def _file_line_refs(answer: DetermineAnswer) -> List[str]:
    """Normalized file:line evidence refs of an answer (Run-Trace / bare / vague refs excluded)."""
    out = []
    for raw in (answer.evidence_refs or []):
        norm = normalize_evidence_ref(raw)
        if norm and _is_file_line(norm):
            out.append(norm)
    return out


def _is_needs_verification(answer: DetermineAnswer) -> bool:
    return (answer.answer == NEEDS_VERIFICATION_ANSWER
            and answer.wsp97_label == NEEDS_VERIFICATION_LABEL
            and not answer.evidence_refs)


def build_index_gap_event(scorecard: Mapping[str, Any]) -> Optional[dict]:
    """ADVISORY, NON-MUTATING INDEX_GAP emission (Appendix A). Records the stale targets and a
    recommendation; performs NO live WRE enqueue / CI mutation / re-index. Returns None when the
    scorecard reports no index gap."""
    if not isinstance(scorecard, Mapping):
        return None                     # malformed scorecard -> fail closed to no event (never crash)
    # Recognize the FULL authoritative gap vocabulary, matching the canonical producer/consumer
    # reddog_governed_work_order_dryrun.py (retrieval_quality == "INDEX_GAP" OR index_gap_detected).
    # Appendix A: a direct-read fallback masks a stale index, so it too is a gap that must be RECORDED
    # (never discarded) -- fail-closed toward recording the advisory, since emission is non-mutating.
    gap = (bool(scorecard.get("index_gap_detected"))
           or str(scorecard.get("retrieval_quality") or "").upper() == "INDEX_GAP"
           or bool(scorecard.get("direct_read_fallback_used")))
    if not gap:
        return None
    stale = [p for p in _as_list(scorecard.get("direct_read_paths")) if isinstance(p, str)]
    return {
        "event": "INDEX_GAP",
        "severity": "advisory",
        "index_gap_detected": True,
        "stale_targets": stale,   # index missed these; they were reachable only via direct-read
        "recommendation": "INDEX_GAP_RECOMMENDATION: targeted re-index of the listed targets is a "
                          "governed WRE/CI maintenance action -- NOT performed here.",
        "boundary": "advisory-only; no live WRE enqueue / CI mutation / re-index in this slice; "
                    "direct-read success is not HoloIndex freshness success",
    }


def verify_answer_set(
    answers: Sequence[Any],
    scorecard: Optional[Mapping[str, Any]] = None,
    read_evidence: Optional[Callable[[str], Optional[str]]] = None,
    *,
    panel: Optional[Sequence[Callable[..., List[str]]]] = None,
) -> VerifierReport:
    """Deterministically verify that each answer's cited evidence EXISTS + SUPPORTS the claim +
    does not CONTRADICT the scorecard. FAIL-CLOSED: a claim is verified ONLY if NO lens refutes it.

    - An honest NEEDS_VERIFICATION abstention (no evidence) verdicts NEEDS_VERIFICATION (not refuted).
    - An evidence-bearing answer with an invalid WSP_97 label is REFUTED.
    - read_evidence is INJECTED; when absent (or a ref cannot be read) the existence lens fails closed.
    - INDEX_GAP is EMITTED as an advisory event only (non-mutating).
    """
    board = scorecard if isinstance(scorecard, Mapping) else {}
    reader = read_evidence if callable(read_evidence) else (lambda _ref: None)
    lenses = list(panel) if panel else DEFAULT_PANEL
    # A non-iterable `answers` coerces to [] (never crash); each entry is coerced INLINE so a
    # non-mapping poison entry (a scalar / str from partial model output) becomes a fail-closed
    # REFUTED claim rather than an uncaught AttributeError (a crash IS a bypass).
    answer_list = list(answers) if isinstance(answers, (list, tuple)) else []

    report = VerifierReport(index_gap_event=build_index_gap_event(board))
    for pos, raw in enumerate(answer_list):
        if isinstance(raw, DetermineAnswer):
            a = raw
        elif isinstance(raw, Mapping):
            a = DetermineAnswer.from_obj(raw)
        else:
            report.claims.append(ClaimVerdict(pos, Verdict.REFUTED, [RefuteReason.MALFORMED_ANSWER]))
            continue
        if _is_needs_verification(a):
            report.claims.append(ClaimVerdict(a.index, Verdict.NEEDS_VERIFICATION))
            continue
        if a.wsp97_label not in WSP97_LABELS:
            report.claims.append(ClaimVerdict(
                a.index, Verdict.REFUTED, [RefuteReason.INVALID_LABEL]))
            continue
        refs = _file_line_refs(a)
        refutations: List[str] = []
        for lens in lenses:
            refutations.extend(lens(a, refs, reader, board))
        # dedup, order-stable
        seen: set = set()
        refutations = [r for r in refutations if not (r in seen or seen.add(r))]
        if refutations:
            report.claims.append(ClaimVerdict(a.index, Verdict.REFUTED, refutations, refs))
        else:
            verdict = Verdict.INFERRED if a.wsp97_label == "INFERRED" else Verdict.OBSERVED_VERIFIED
            # Transparency: a claim with NO operative code symbol (pure prose OR only bare domain
            # nouns / ubiquitous ALL_CAPS words) verified on existence + consistency, but support was
            # NOT deterministically checkable -- surface it so such evidence-relevance is never
            # SILENTLY presented as fully verified (a decoy noun must not read as SUPPORT-verified).
            has_operative = any(_is_operative_anchor(t) for t in _claim_anchors(a.question_text))
            notes = [] if has_operative else [NOTE_SUPPORT_UNCHECKABLE]
            report.claims.append(ClaimVerdict(a.index, verdict, [], refs, notes))

    report.refuted_count = sum(1 for c in report.claims if c.refuted)
    report.verified = report.refuted_count == 0
    return report
