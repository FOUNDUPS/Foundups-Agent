#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fusion Redaction Gate -- deterministic, FAIL-CLOSED precondition for any future Fusion egress.

Slice: HERMES_FUSION_REDACTION_GATE_PHASE1. This is the security boundary the landed #832 contract
anticipates: "Privacy stays BLOCKED_PENDING_REDACTION_GATE until a separate redaction-gate slice
lands." This module IS that slice -- the precondition only. It does NOT enable any live OpenRouter
call: FusionMode.ALIAS / SERVER_TOOL / LOCAL_FALLBACK still raise RedactionGateBlocked (unchanged).

POLICY -- two action classes (REDACT vs BLOCK):
  REDACT  : credential/secret material that can be confidently removed (API keys, bearer tokens,
            .env secret values, complete private-key blocks, member PII, credential-bearing URLs).
            The value is replaced; the payload may PASS if the post-redaction re-scan is clean.
  BLOCK   : semantically unsafe content that must never leave even if a token is swapped (private
            chain-of-thought / hidden reasoning, merge-authorization tokens, source_authority
            mutation, CABR/payout/benefit-routing authority, internal governance instructions, and
            material the policy cannot confidently classify e.g. a malformed private-key header).
            Presence of ANY block category keeps status BLOCKED_PENDING_REDACTION_GATE.

WSP 97 TRUTH BOUNDARIES:
  DOES: deterministic REDACT vs BLOCK; emit a counts-only report + sha256:<64 hex> digests computed
        FROM THE REDACTED OUTPUT; PASS only when redaction ran AND a post-redaction re-scan finds
        zero REDACT residual AND zero BLOCK markers AND no error; FAIL CLOSED otherwise.
  DOES NOT: make any network call; read any env/API key (never imports os); enable any live Fusion
        mode; touch merge / CABR / payout / source-authority; echo raw input in any error/reason.

REUSE NOTE (WSP 84): an in-tree redactor exists -- redact_sensitive() (duplicated byte-for-byte in
ai_overseer/src/autofix_executor.py:99 and foundups/agent/src/kanban_plugin_contract.py:105) and
redact_secrets()/SECRET_CONTENT_PATTERNS (ai_gateway/src/openclaw_codebase_agent.py:118,146). They
return text-only (no report/digest/fail-closed gate, no REDACT-vs-BLOCK split) and live cross-domain.
A security gate must own its fail-closed verification and not couple a security primitive across WSP 3
domains, so this module is self-contained; its REDACT detector set is a documented SUPERSET of both
existing tables. Follow-up HERMES_REDACTOR_CONSOLIDATION may later unify all into shared_utilities.

WSP: WSP 11 (typed interface), WSP 50 (pre-action), WSP 84 (reuse evaluated), WSP 97 (truth boundary).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .fusion_adapter import REDACTION_BLOCKED, digest

REDACTION_GATE_PASSED = "REDACTION_GATE_PASSED"
REDACTION_POLICY_VERSION = "fusion_redaction.v1"

ACTION_REDACT = "redact"
ACTION_BLOCK = "block"

_PLACEHOLDER = "[REDACTED:{cat}]"

# Low-cardinality reasons -- NEVER echo raw input.
REASON_CLEAN = "clean"
REASON_REDACTED = "redacted"
REASON_BLOCKED_POLICY = "blocked_policy"
REASON_RESIDUAL = "residual_forbidden_pattern"
REASON_REDACTOR_ERROR = "redactor_error"
ALLOWED_REASONS = frozenset(
    {REASON_CLEAN, REASON_REDACTED, REASON_BLOCKED_POLICY, REASON_RESIDUAL, REASON_REDACTOR_ERROR}
)

# ---------------------------------------------------------------------------
# Detection policy -- (category, compiled pattern, action). ORDER MATTERS:
# complete private-key blocks are redacted FIRST; a lone/malformed remaining header then BLOCKS
# (cannot confidently redact a key body without a matching END).
#
# REDACT set is a documented SUPERSET of:
#   _REDACT_SUBS            (autofix_executor.py:64 / kanban_plugin_contract.py:75)
#   SECRET_CONTENT_PATTERNS (openclaw_codebase_agent.py:118)
# plus dispatch-required AKIA*/xox*/OPENROUTER_*.
# ---------------------------------------------------------------------------
_DETECTORS: Tuple[Tuple[str, "re.Pattern[str]", str], ...] = (
    # --- REDACT: confidently removable secret/PII material ---
    (
        "private_key_block",
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
            re.DOTALL | re.IGNORECASE,
        ),
        ACTION_REDACT,
    ),
    ("openai_anthropic_key", re.compile(r"\bsk-(?:or-|ant-api)?[A-Za-z0-9_\-]{16,}"), ACTION_REDACT),
    ("stripe_key", re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}"), ACTION_REDACT),
    (
        "bare_jwt",
        re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{6,}"),
        ACTION_REDACT,
    ),
    ("grok_key", re.compile(r"\bxai-[A-Za-z0-9_\-]{16,}"), ACTION_REDACT),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{10,}"), ACTION_REDACT),
    ("google_oauth_access", re.compile(r"\bya29\.[0-9A-Za-z._\-]{10,}"), ACTION_REDACT),
    ("google_oauth_refresh", re.compile(r"\b1//[0-9A-Za-z._\-]{10,}"), ACTION_REDACT),
    ("aws_akia", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), ACTION_REDACT),
    ("github_token", re.compile(r"\b(?:gh[posru]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,})"), ACTION_REDACT),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}"), ACTION_REDACT),
    ("bearer_token", re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._\-]{8,}"), ACTION_REDACT),
    ("openrouter_secret", re.compile(r"\bOPENROUTER_[A-Z_]*\s*[:=]\s*\S+", re.IGNORECASE), ACTION_REDACT),
    (
        "oauth_url_param",
        re.compile(r"[?&](?:code|access_token|refresh_token|id_token|token)=[^\s&\"'}]+", re.IGNORECASE),
        ACTION_REDACT,
    ),
    (
        "secret_kv",
        re.compile(
            r"\b(?:access_token|refresh_token|id_token|client_secret|client_id|user_code|"
            r"authorization_code|password|passwd|api_key|apikey|token)\b\s*[\"']?\s*[:=]\s*[\"']?[^\s&\"'}]+",
            re.IGNORECASE,
        ),
        ACTION_REDACT,
    ),
    (
        "env_secret_line",
        re.compile(r"\b[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|APIKEY|CREDENTIAL)\b\s*[:=]\s*\S+"),
        ACTION_REDACT,
    ),
    ("email_pii", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), ACTION_REDACT),
    # --- BLOCK: semantically unsafe; presence keeps status BLOCKED even if a token were swapped ---
    (
        "private_key_residual",
        re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.IGNORECASE),
        ACTION_BLOCK,
    ),
    (
        "private_reasoning",
        re.compile(
            r"(?i)(?:<\s*think(?:ing)?\b|</\s*think|<\s*scratchpad|chain[\s_\-]?of[\s_\-]?thought|"
            r"hidden[\s_\-]?reasoning|private[\s_\-]?reasoning)",
        ),
        ACTION_BLOCK,
    ),
    (
        "merge_authorization",
        re.compile(r"(?i)\b(?:pull_request_merge|merge[\s_\-]?token|auto[\s_\-]?merge[\s_\-]?token|merge[\s_\-]?authoriz\w*)\b"),
        ACTION_BLOCK,
    ),
    ("source_authority", re.compile(r"(?i)\bsource[\s_\-]?authority\b"), ACTION_BLOCK),
    (
        "cabr_payout_authority",
        re.compile(r"(?i)\b(?:cabr[\s_\-]?ready|cabr[\s_\-]?payout|payout[\s_\-]?ready|payout[\s_\-]?routing|benefit[\s_\-]?routing|capability_token\w*)\b"),
        ACTION_BLOCK,
    ),
    (
        "governance_instruction",
        re.compile(r"(?i)\b(?:internal[\s_\-]?governance|governance[\s_\-]?instruction|gate[\s_\-]?passed|grant[\s_\-]?authority)\b"),
        ACTION_BLOCK,
    ),
)

REDACT_CATEGORIES: Tuple[str, ...] = tuple(c for c, _, a in _DETECTORS if a == ACTION_REDACT)
BLOCK_CATEGORIES: Tuple[str, ...] = tuple(c for c, _, a in _DETECTORS if a == ACTION_BLOCK)


# ---------------------------------------------------------------------------
# Report + result (counts only -- never raw snippets / values / headers / prompt / context)
# ---------------------------------------------------------------------------


@dataclass
class RedactionReport:
    policy_version: str = REDACTION_POLICY_VERSION
    categories_hit: Dict[str, int] = field(default_factory=dict)
    blocked_categories: Tuple[str, ...] = ()
    residual_forbidden_count: int = 0
    error: bool = False


@dataclass
class RedactionGateResult:
    status: str
    reason: str
    redacted_prompt: Optional[str]
    redacted_context: Optional[str]
    prompt_digest: Optional[str]
    context_digest: Optional[str]
    report: RedactionReport

    @property
    def passed(self) -> bool:
        return self.status == REDACTION_GATE_PASSED


# ---------------------------------------------------------------------------
# Scan + redact
# ---------------------------------------------------------------------------


def scan_forbidden(text: object) -> List[str]:
    """Return all detector categories (REDACT or BLOCK) whose pattern matches `text`.

    Empty list == clean. A non-string input is itself forbidden (fail closed)."""
    if not isinstance(text, str):
        return ["non_text_input"]
    return [cat for cat, rx, _ in _DETECTORS if rx.search(text)]


def redact_text(text: object) -> Tuple[str, RedactionReport]:
    """Deterministically apply the policy. Returns (redacted_text, report).

    REDACT categories are replaced by a category placeholder; BLOCK categories are detected and
    recorded (never silently removed). The report carries category->count, blocked category names,
    and the post-redaction residual count -- never a raw value or snippet.
    """
    report = RedactionReport()
    if not isinstance(text, str):
        report.error = True
        report.residual_forbidden_count = 1
        return "", report
    out = text
    counts: Dict[str, int] = {}
    blocked: List[str] = []
    for cat, rx, action in _DETECTORS:
        n = sum(1 for _ in rx.finditer(out))
        if not n:
            continue
        counts[cat] = counts.get(cat, 0) + n
        if action == ACTION_BLOCK:
            blocked.append(cat)
        else:
            out = rx.sub(_PLACEHOLDER.format(cat=cat), out)
    report.categories_hit = counts
    report.blocked_categories = tuple(sorted(set(blocked)))
    # post-redaction re-scan: any REDACT pattern still present, or any BLOCK marker present
    report.residual_forbidden_count = len(scan_forbidden(out))
    return out, report


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------


def evaluate_redaction_gate(prompt: object, context: object = None) -> RedactionGateResult:
    """Deterministic, FAIL-CLOSED gate.

    PASS requires: prompt (and context if given) are text, redaction ran without error, NO block
    category was detected, and the post-redaction re-scan residual count is 0. Any other case ->
    BLOCKED_PENDING_REDACTION_GATE. Digests are computed FROM THE REDACTED OUTPUT, not raw input.
    """
    try:
        if not isinstance(prompt, str) or (context is not None and not isinstance(context, str)):
            return _blocked(REASON_REDACTOR_ERROR, RedactionReport(error=True))

        red_p, rep_p = redact_text(prompt)
        if context is not None:
            red_c, rep_c = redact_text(context)
        else:
            red_c, rep_c = None, RedactionReport()

        merged = _merge_reports(rep_p, rep_c, context is not None)
        if rep_p.error or rep_c.error:
            return _blocked(REASON_REDACTOR_ERROR, merged)
        if merged.blocked_categories:
            return _blocked(REASON_BLOCKED_POLICY, merged)
        # residual REDACT/BLOCK patterns left in the redacted output -> never pass dirty output
        post = len(scan_forbidden(red_p)) + (len(scan_forbidden(red_c)) if context is not None else 0)
        if post > 0:
            return _blocked(REASON_RESIDUAL, merged)

        reason = REASON_REDACTED if merged.categories_hit else REASON_CLEAN
        return RedactionGateResult(
            status=REDACTION_GATE_PASSED,
            reason=reason,
            redacted_prompt=red_p,
            redacted_context=red_c,
            prompt_digest=digest(red_p),
            context_digest=digest(red_c) if context is not None else None,
            report=merged,
        )
    except Exception:  # any error -> fail closed; reason carries NO raw input
        return _blocked(REASON_REDACTOR_ERROR, RedactionReport(error=True))


def redaction_status_for(prompt: object, context: object = None) -> str:
    """Convenience: return only the gate status string (PASSED or BLOCKED)."""
    return evaluate_redaction_gate(prompt, context).status


def _blocked(reason: str, report: RedactionReport) -> RedactionGateResult:
    return RedactionGateResult(
        status=REDACTION_BLOCKED,
        reason=reason,
        redacted_prompt=None,
        redacted_context=None,
        prompt_digest=None,
        context_digest=None,
        report=report,
    )


def _merge_reports(rep_p: RedactionReport, rep_c: RedactionReport, has_context: bool) -> RedactionReport:
    counts: Dict[str, int] = dict(rep_p.categories_hit)
    if has_context:
        for cat, n in rep_c.categories_hit.items():
            counts[cat] = counts.get(cat, 0) + n
    blocked = set(rep_p.blocked_categories)
    if has_context:
        blocked |= set(rep_c.blocked_categories)
    residual = rep_p.residual_forbidden_count + (rep_c.residual_forbidden_count if has_context else 0)
    return RedactionReport(
        policy_version=REDACTION_POLICY_VERSION,
        categories_hit=counts,
        blocked_categories=tuple(sorted(blocked)),
        residual_forbidden_count=residual,
        error=rep_p.error or (rep_c.error if has_context else False),
    )


__all__ = [
    "REDACTION_GATE_PASSED",
    "REDACTION_BLOCKED",
    "REDACTION_POLICY_VERSION",
    "ACTION_REDACT",
    "ACTION_BLOCK",
    "REDACT_CATEGORIES",
    "BLOCK_CATEGORIES",
    "ALLOWED_REASONS",
    "REASON_CLEAN",
    "REASON_REDACTED",
    "REASON_BLOCKED_POLICY",
    "REASON_RESIDUAL",
    "REASON_REDACTOR_ERROR",
    "RedactionReport",
    "RedactionGateResult",
    "scan_forbidden",
    "redact_text",
    "evaluate_redaction_gate",
    "redaction_status_for",
]
