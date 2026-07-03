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

AUDIT MODE (REDDOG_AUDIT_MODE_REDACTION_PHASE1, slice 3/3) -- OFF by default:
  Governance audits must READ governance STRUCTURE (enum member names, dataclass field lists,
  gate/action-name constants, WSP refs). In the default (non-audit) path the four STRUCTURAL block
  categories -- source_authority, merge_authorization, cabr_payout_authority, governance_instruction
  -- match on the bare IDENTIFIER and so BLOCK the whole payload, stripping the very structure a
  governance audit must see. When audit_mode=True those four categories become AUDIT-VISIBLE: the
  identifier text is PRESERVED, but secret/payout/authority VALUES are STILL removed --
    * every REDACT detector remains active unchanged (API keys/tokens/creds always removed);
    * audit-only VALUE redactors strip the RHS bound to a structural identifier
      (payout AMOUNTS, merge-authorization TOKENS/grants, secret-shaped values).
  audit_mode NEVER relaxes: private_reasoning (free-text always BLOCKS), private_key_residual
  (malformed header -> cannot confidently redact -> BLOCKS), and every REDACT category. The line
  between value and structure is: KEEP the left-hand key/identifier + enum member names; REDACT the
  right-hand value. When ambiguous, REDACT (fail-closed). audit_mode default False keeps the
  non-audit path byte-identical (backward compatible).

WSP 97 TRUTH BOUNDARIES:
  DOES: deterministic REDACT vs BLOCK; emit a counts-only report + sha256:<64 hex> digests computed
        FROM THE REDACTED OUTPUT; PASS only when redaction ran AND a post-redaction re-scan finds
        zero REDACT residual AND zero BLOCK markers AND no error; FAIL CLOSED otherwise; when
        audit_mode=True, preserve STRUCTURAL governance identifiers while still redacting their
        secret/payout/authority VALUES (never weakens any REDACT category or secret pattern).
  DOES NOT: make any network call; read any env/API key (never imports os); enable any live Fusion
        mode; touch merge / CABR / payout / source-authority; echo raw input in any error/reason;
        (audit_mode) leak any secret VALUE, payout AMOUNT, or authorization TOKEN, or relax
        private_reasoning / private_key_residual / any REDACT category.

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

# REDDOG_REDACTION_PER_TARGET_ISOLATION_PHASE1 -- marker-aware per-target redaction isolation.
# The extension packs required direct-read target excerpts into ONE merged context, each delimited
# by this stable marker (JS const REQUIRED_TARGET_MARKER_PREFIX in extension.js). Before this slice the
# WHOLE merged context was redaction-gated as one unit: a single hard-block token (private_reasoning /
# private_key_residual) in ONE required excerpt blocked the ENTIRE payload -> redacted_context=None ->
# every required target dropped, even in audit_mode. This slice ONLY changes the GRANULARITY of the
# block (per-target instead of whole-payload); it NEVER relaxes what is blocked. A blocked target's body
# is OMITTED and replaced with a notice (its secrets never reach the model); clean targets survive.
REQUIRED_TARGET_MARKER_PREFIX = "### Required direct-read target: "
# Stable notice that replaces a blocked target's body. The category names are the low-cardinality
# BLOCK category identifiers (never raw content). The marker is preserved so the model still learns the
# target existed but was withheld; only the fenced body is replaced.
_REQUIRED_TARGET_BLOCKED_NOTICE = "[REQUIRED TARGET REDACTED: blocked by {cats}]"


def _normalize_required_target_path(raw: object) -> str:
    """Normalize a required-target path label for authoritative-set comparison.

    REDDOG_REQUIRED_TARGET_MARKER_FORGERY_HARDENING_PHASE1: backslash -> forward slash, drop a
    trailing "(bounded excerpt)" packer note, strip surrounding whitespace, and lowercase. Used ONLY
    to decide whether a marker-delimited section's path is in the authoritative packed set; it never
    changes what is scanned or redacted.
    """
    s = str(raw or "").replace("\\", "/").strip()
    note = " (bounded excerpt)"
    if s.endswith(note):
        s = s[: -len(note)].strip()
    return s.lower()

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
# AUDIT MODE (REDDOG_AUDIT_MODE_REDACTION_PHASE1, slice 3/3)
#
# The four STRUCTURAL block categories below match on the bare governance
# identifier (enum/field/gate/action name). In audit_mode they become
# AUDIT-VISIBLE: the identifier is preserved (not blocked) so a governance audit
# can read the structure, while dedicated audit-only VALUE redactors + every
# existing REDACT detector still remove any secret value / payout amount /
# authorization token. private_reasoning and private_key_residual are NOT in
# this set -- they always BLOCK (free-text / ambiguous -> fail-closed).
# ---------------------------------------------------------------------------
AUDIT_STRUCTURAL_CATEGORIES: frozenset = frozenset({
    "source_authority",
    "merge_authorization",
    "cabr_payout_authority",
    "governance_instruction",
})

# REDACT categories whose always-on detector swallows the key IDENTIFIER along
# with the value. In audit mode they are handled by key-preserving audit variants
# below instead, so the always-on versions are skipped (audit_mode only) to keep
# the left-hand key name readable. Secret VALUES are still fully removed either way.
AUDIT_KEY_PRESERVING_SUPERSEDES: frozenset = frozenset({"secret_kv", "env_secret_line"})

# Audit-only VALUE redactors -- run ONLY when audit_mode=True, BEFORE structural
# identifiers are preserved, so preserving an identifier can never leak a value.
# Each strips the RIGHT-HAND-SIDE value/amount/token while keeping the left-hand
# identifier readable. These ADD redaction (never subtract); they are appended to
# the always-on REDACT set for the audit scan.
#   * payout AMOUNTS bound to a cabr/payout identifier (numbers, currency)
#   * merge-authorization TOKEN/grant values bound to a merge identifier
#   * governance/source grant VALUES bound to those identifiers
# NOTE: the identifier itself (LHS) is preserved by (\bkey\b[\s:=]+) capture.
_AUDIT_VALUE_REDACTORS: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    # Key-preserving secret-KV redactor: keep the LHS key name + separator as
    # readable structure, redact ONLY the RHS value. Runs before the always-on
    # secret_kv detector (which would otherwise swallow the key name too). Same
    # key set as secret_kv so audit output keeps `api_key`, `token`, etc.
    (
        "audit_secret_kv_value",
        re.compile(
            r"(?i)\b((?:access_token|refresh_token|id_token|client_secret|client_id|user_code|"
            r"authorization_code|password|passwd|api_key|apikey|token)"
            r"\b\s*[:=]\s*[\"']?)"
            r"[^\s&\"'}]+",
        ),
    ),
    # Key-preserving env-secret-line redactor: keep the FOO_SECRET/BAR_TOKEN key,
    # redact only its value. Runs before env_secret_line for the same reason.
    (
        "audit_env_secret_value",
        re.compile(
            r"\b([A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|APIKEY|CREDENTIAL)"
            r"\b\s*[:=]\s*)"
            r"\S+",
        ),
    ),
    (
        "audit_payout_amount",
        re.compile(
            r"(?i)\b((?:cabr[\s_\-]?payout|payout[\s_\-]?amount|payout|cabr)"
            r"[\w\s]*?[:=]\s*)"
            r"\$?\d[\d,]*(?:\.\d+)?",
        ),
    ),
    (
        "audit_merge_token",
        re.compile(
            r"(?i)\b((?:merge[\s_\-]?authoriz\w*|merge[\s_\-]?token|"
            r"auto[\s_\-]?merge[\s_\-]?token|pull_request_merge|grant[\s_\-]?authority)"
            r"[\w\s]*?[:=]\s*)"
            r"[\"']?[^\s\"'}]+",
        ),
    ),
    (
        "audit_authority_grant",
        re.compile(
            r"(?i)\b((?:source[\s_\-]?authority[\s_\-]?override|"
            r"governance[\s_\-]?grant|grant[\s_\-]?token)"
            r"[\w\s]*?[:=]\s*)"
            r"[\"']?[^\s\"'}]+",
        ),
    ),
)


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
    # REDDOG_REDACTION_PER_TARGET_ISOLATION_PHASE1 -- per-required-target isolation telemetry.
    # All default empty/zero so the non-audit / no-marker path stays byte-identical (backward compat):
    # these fields are populated ONLY when audit-mode marker-aware isolation actually ran.
    required_targets_redaction_checked: int = 0
    required_targets_redaction_passed: int = 0
    required_targets_redaction_blocked: int = 0
    required_targets_redaction_blocked_paths: Tuple[str, ...] = ()
    required_targets_redaction_blocked_reasons: Tuple[str, ...] = ()


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


def scan_forbidden(text: object, audit_mode: bool = False) -> List[str]:
    """Return all detector categories (REDACT or BLOCK) whose pattern matches `text`.

    Empty list == clean. A non-string input is itself forbidden (fail closed).

    In audit_mode the four AUDIT_STRUCTURAL_CATEGORIES are EXCLUDED from the residual
    scan (their identifiers are intentionally preserved as readable structure). Every
    other category -- all REDACT secret patterns, private_reasoning, private_key_residual
    -- is scanned unchanged, so a leaked secret value still shows up as residual.
    """
    if not isinstance(text, str):
        return ["non_text_input"]
    hits = [cat for cat, rx, _ in _DETECTORS if rx.search(text)]
    if audit_mode:
        # Structural identifiers are intentionally preserved; the key-preserving
        # audit variants supersede secret_kv/env_secret_line (which would otherwise
        # re-match the surviving `key = [REDACTED:...]` structure and read as residual).
        excluded = AUDIT_STRUCTURAL_CATEGORIES | AUDIT_KEY_PRESERVING_SUPERSEDES
        hits = [cat for cat in hits if cat not in excluded]
    return hits


def redact_text(text: object, audit_mode: bool = False) -> Tuple[str, RedactionReport]:
    """Deterministically apply the policy. Returns (redacted_text, report).

    REDACT categories are replaced by a category placeholder; BLOCK categories are detected and
    recorded (never silently removed). The report carries category->count, blocked category names,
    and the post-redaction residual count -- never a raw value or snippet.

    When audit_mode=True: the audit-only VALUE redactors run FIRST (stripping payout amounts /
    merge tokens / grant values while preserving their left-hand identifiers), then the four
    AUDIT_STRUCTURAL_CATEGORIES are recorded (categories_hit) but NOT added to blocked_categories --
    their bare identifier text is preserved as readable governance structure. All REDACT secret
    detectors and the non-structural block categories (private_reasoning, private_key_residual)
    behave exactly as in the default path, so no secret value can leak.
    """
    report = RedactionReport()
    if not isinstance(text, str):
        report.error = True
        report.residual_forbidden_count = 1
        return "", report
    out = text
    counts: Dict[str, int] = {}
    blocked: List[str] = []
    # Audit-only VALUE redactors first: strip RHS value/amount/token, keep the LHS identifier.
    if audit_mode:
        for cat, rx in _AUDIT_VALUE_REDACTORS:
            n = sum(1 for _ in rx.finditer(out))
            if not n:
                continue
            counts[cat] = counts.get(cat, 0) + n
            # \1 preserves the captured "identifier:" LHS; the RHS value is replaced.
            out = rx.sub(lambda m: m.group(1) + _PLACEHOLDER.format(cat=cat), out)
    for cat, rx, action in _DETECTORS:
        # In audit mode the key-preserving audit variants above already redacted the
        # VALUE for these key/value shapes (keeping the key name). Skipping the always-on
        # versions here prevents them from re-swallowing the surviving `key = [REDACTED]`
        # structure. The audit variants cover the identical key set, so no secret value
        # can escape -- and every provider-specific secret pattern (sk-/AIza/ghp_/bearer/
        # JWT/...) is a SEPARATE detector that stays fully active.
        if audit_mode and cat in AUDIT_KEY_PRESERVING_SUPERSEDES:
            continue
        n = sum(1 for _ in rx.finditer(out))
        if not n:
            continue
        counts[cat] = counts.get(cat, 0) + n
        if action == ACTION_BLOCK:
            # In audit mode, structural governance identifiers are preserved (not blocked).
            if audit_mode and cat in AUDIT_STRUCTURAL_CATEGORIES:
                continue
            blocked.append(cat)
        else:
            out = rx.sub(_PLACEHOLDER.format(cat=cat), out)
    report.categories_hit = counts
    report.blocked_categories = tuple(sorted(set(blocked)))
    # post-redaction re-scan: any REDACT pattern still present, or any BLOCK marker present
    report.residual_forbidden_count = (
        len(scan_forbidden(out, audit_mode=True)) if audit_mode else len(scan_forbidden(out))
    )
    return out, report


# ---------------------------------------------------------------------------
# REDDOG_REDACTION_PER_TARGET_ISOLATION_PHASE1 -- marker-aware per-target isolation
# ---------------------------------------------------------------------------


def _section_is_blocked(section_body: str) -> Tuple[bool, Tuple[str, ...]]:
    """Return (is_blocked, block_category_names) for ONE required-target section body.

    A section is "blocked" iff, under AUDIT-MODE scanning, it triggers at least one
    NON-audit-structural ACTION_BLOCK category (private_reasoning / private_key_residual).
    This reuses redact_text(audit_mode=True): its blocked_categories already excludes the four
    AUDIT_STRUCTURAL_CATEGORIES (they are preserved as readable structure, never blocked). So the
    ONLY categories that can appear here are the always-block ones -- exactly the spec's
    "non-audit-structural ACTION_BLOCK category". No detector is relaxed; this only asks the
    existing audit-mode policy whether THIS section would block.
    """
    _redacted, rep = redact_text(section_body, audit_mode=True)
    return (bool(rep.blocked_categories), tuple(rep.blocked_categories))


def _isolate_required_targets(
    context: str,
    authoritative_paths: Optional[Tuple[str, ...]] = None,
) -> Optional[Tuple[str, Dict[str, object]]]:
    """Marker-aware per-target redaction isolation for an audit-mode merged context.

    REDDOG_REQUIRED_TARGET_MARKER_FORGERY_HARDENING_PHASE1: `authoritative_paths` is the AUTHORITATIVE
    list of required-target paths the packer actually packed (threaded from the JS packer via the
    bridge payload). When it is provided (non-None), a marker-delimited section is only treated as a
    REQUIRED-TARGET SECTION when its path label is IN that list; a marker whose path is NOT authoritative
    (a phantom minted by file CONTENT, e.g. a self-referential audit body that literally contains
    "### Required direct-read target: fake/evil.py") is treated as ORDINARY content -- folded back into
    the preceding real section verbatim, never counted as its own checked/passed/blocked section, and
    never able to mint a blocked_path. Consequently checked/passed/blocked/missing can never exceed the
    authoritative count and blocked_paths is a subset of the authoritative paths. When
    `authoritative_paths` is None (e.g. legacy callers / no list threaded) behavior is byte-identical to
    the pre-hardening path (every marker section is checked), so the JS pack-time marker neutralization
    is the defense-in-depth that keeps phantom markers out of the packed body in the first place.

    Splits `context` into a preamble plus per-required-target sections delimited by the stable
    marker REQUIRED_TARGET_MARKER_PREFIX, evaluates each section's block status INDEPENDENTLY,
    OMITS only the sections that trigger a non-audit-structural block (replacing their body with a
    stable notice while keeping the marker), preserves all other sections verbatim, and reassembles.

    Returns (reassembled_context, telemetry) when isolation applied, or None to signal "fall back to
    the existing whole-context gate" (no markers present, or the split is ambiguous -> FAIL CLOSED).

    Fail-closed contract: if parsing/reassembly is at all ambiguous, return None so the caller runs
    the unchanged whole-context block. This never PASSES a payload that the whole-context gate blocks;
    it only splits an already-audit-mode context so ONE bad target cannot drop the clean ones.
    """
    if not isinstance(context, str):
        return None
    marker = REQUIRED_TARGET_MARKER_PREFIX
    first = context.find(marker)
    if first == -1:
        return None  # no required-target markers -> unchanged whole-context path

    preamble = context[:first]
    # Split the remainder on the marker. re.split keeps every occurrence boundary; because the marker
    # begins each section, splitting on it and re-prefixing is unambiguous and order-preserving.
    remainder = context[first:]
    raw_sections = remainder.split(marker)
    # raw_sections[0] is "" (remainder starts with the marker); every subsequent item is one section
    # body WITHOUT its leading marker. A malformed split (nothing after the marker) -> fail closed.
    sections = [s for s in raw_sections[1:]]
    if not sections:
        return None

    # REDDOG_REQUIRED_TARGET_MARKER_FORGERY_HARDENING_PHASE1: build the authoritative lookup set.
    # None => no list threaded (legacy path, every marker section is a required-target section).
    # A provided list => only sections whose path is in the set are required-target sections; the rest
    # are phantom markers (file content) folded back as ordinary text.
    authoritative_set: Optional[set] = None
    if authoritative_paths is not None:
        authoritative_set = {
            _normalize_required_target_path(p) for p in authoritative_paths if str(p or "").strip()
        }

    checked = 0
    passed = 0
    blocked_paths: List[str] = []
    blocked_reasons: List[str] = []
    rebuilt: List[str] = []
    for body in sections:
        # The path is the first line after the marker (may carry a "(bounded excerpt)" suffix and
        # then a fenced block). Keep the ENTIRE original body for survivors (byte-identical); only a
        # blocked section is rewritten. The path label is telemetry-only.
        newline = body.find("\n")
        header_line = body if newline == -1 else body[:newline]
        path_label = header_line.strip()
        # Authoritative gate: when an authoritative list is threaded, a marker whose path is NOT in it
        # is a PHANTOM minted by file content. Fold it back verbatim (marker + body) into the preceding
        # output as ORDINARY content -- it is NOT a required-target section, so it is neither checked nor
        # counted and can never contribute a blocked_path. Its content still flows to the whole-context
        # gate via reassembly (so any real secret in it is still value-redacted / fails closed there).
        if authoritative_set is not None and _normalize_required_target_path(path_label) not in authoritative_set:
            if rebuilt:
                rebuilt[-1] = rebuilt[-1] + marker + body
            else:
                preamble = preamble + marker + body
            continue
        checked += 1
        is_blocked, cats = _section_is_blocked(body)
        if is_blocked:
            blocked_paths.append(path_label)
            for c in cats:
                if c not in blocked_reasons:
                    blocked_reasons.append(c)
            # The block-category NAMES themselves contain their own trigger substrings
            # (e.g. the literal "private_reasoning" matches the private_reasoning detector).
            # Sanitize the name for the IN-CONTEXT notice (underscore -> dot) so the notice can
            # never re-trigger a detector and re-block the reassembled payload. The REAL
            # underscore names are preserved ONLY in the counts-only telemetry (never scanned).
            safe_cats = ", ".join(c.replace("_", ".") for c in cats) if cats else "policy"
            notice = _REQUIRED_TARGET_BLOCKED_NOTICE.format(cats=safe_cats)
            # Preserve the marker + path header so the model knows the target existed; replace the
            # BODY (fenced content) with the notice. The blocked content never reaches egress.
            rebuilt.append(marker + header_line + "\n" + notice + "\n")
        else:
            passed += 1
            rebuilt.append(marker + body)

    reassembled = preamble + "".join(rebuilt)
    telemetry: Dict[str, object] = {
        "required_targets_redaction_checked": checked,
        "required_targets_redaction_passed": passed,
        "required_targets_redaction_blocked": len(blocked_paths),
        "required_targets_redaction_blocked_paths": tuple(blocked_paths),
        "required_targets_redaction_blocked_reasons": tuple(blocked_reasons),
    }
    return reassembled, telemetry


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------


def evaluate_redaction_gate(
    prompt: object,
    context: object = None,
    audit_mode: bool = False,
    required_target_paths: Optional[Tuple[str, ...]] = None,
) -> RedactionGateResult:
    """Deterministic, FAIL-CLOSED gate.

    PASS requires: prompt (and context if given) are text, redaction ran without error, NO block
    category was detected, and the post-redaction re-scan residual count is 0. Any other case ->
    BLOCKED_PENDING_REDACTION_GATE. Digests are computed FROM THE REDACTED OUTPUT, not raw input.

    audit_mode (default False -> byte-identical to the pre-slice-3 path): preserves the four
    AUDIT_STRUCTURAL_CATEGORIES identifiers as readable governance structure while still redacting
    every secret VALUE / payout AMOUNT / authorization TOKEN. Secret redaction is NEVER weakened.

    REDDOG_REDACTION_PER_TARGET_ISOLATION_PHASE1 (audit_mode + required-target markers only):
    the merged context is FIRST split by REQUIRED_TARGET_MARKER_PREFIX and each required-target
    section is evaluated for a non-audit-structural block INDEPENDENTLY. A blocked section's body is
    OMITTED (marker + a redaction notice survive; its secrets never reach egress) while every other
    section is preserved; the reassembled context then flows through the UNCHANGED whole-context gate
    (so audit-mode value-redaction still applies to survivors and any residual still fails closed).
    This changes ONLY the GRANULARITY of the block (per-target vs whole-payload), never what is
    blocked. If no markers exist or the split is ambiguous -> fall back to the whole-context path.

    REDDOG_REQUIRED_TARGET_MARKER_FORGERY_HARDENING_PHASE1: `required_target_paths` is the AUTHORITATIVE
    list of packed required-target paths (threaded from the JS packer). When provided, per-target
    isolation only treats a marker-delimited section as a required-target section when its path is in
    this list; a marker minted by file CONTENT (path not in the list) is ordinary content and cannot
    inflate the isolation counts / blocked_paths. This changes only how sections are IDENTIFIED as
    required targets -- no detector is relaxed and the whole-context gate still redacts every survivor.
    """
    try:
        if not isinstance(prompt, str) or (context is not None and not isinstance(context, str)):
            return _blocked(REASON_REDACTOR_ERROR, RedactionReport(error=True))

        # Per-target isolation (audit_mode + markers only). Runs BEFORE the whole-context gate on a
        # COPY of the context; survivors + notices reassemble into gate_context. Fail-closed: when it
        # returns None (no markers / ambiguous split) the original context flows through unchanged.
        gate_context = context
        target_telemetry: Optional[Dict[str, object]] = None
        if audit_mode and isinstance(context, str):
            isolated = _isolate_required_targets(context, required_target_paths)
            if isolated is not None:
                gate_context, target_telemetry = isolated

        # Call redact_text/scan_forbidden with the EXACT pre-slice-3 signature on the
        # default path (no audit kwarg) so the non-audit behavior is byte-identical and
        # single-arg monkeypatched doubles keep working. Only audit runs pass the kwarg.
        if audit_mode:
            red_p, rep_p = redact_text(prompt, audit_mode=True)
            if gate_context is not None:
                red_c, rep_c = redact_text(gate_context, audit_mode=True)
            else:
                red_c, rep_c = None, RedactionReport()
        else:
            red_p, rep_p = redact_text(prompt)
            if gate_context is not None:
                red_c, rep_c = redact_text(gate_context)
            else:
                red_c, rep_c = None, RedactionReport()

        merged = _merge_reports(rep_p, rep_c, context is not None)
        if target_telemetry is not None:
            merged.required_targets_redaction_checked = int(target_telemetry["required_targets_redaction_checked"])
            merged.required_targets_redaction_passed = int(target_telemetry["required_targets_redaction_passed"])
            merged.required_targets_redaction_blocked = int(target_telemetry["required_targets_redaction_blocked"])
            merged.required_targets_redaction_blocked_paths = tuple(target_telemetry["required_targets_redaction_blocked_paths"])
            merged.required_targets_redaction_blocked_reasons = tuple(target_telemetry["required_targets_redaction_blocked_reasons"])
        if rep_p.error or rep_c.error:
            return _blocked(REASON_REDACTOR_ERROR, merged)
        if merged.blocked_categories:
            return _blocked(REASON_BLOCKED_POLICY, merged)
        # residual REDACT/BLOCK patterns left in the redacted output -> never pass dirty output
        if audit_mode:
            post = len(scan_forbidden(red_p, audit_mode=True)) + (
                len(scan_forbidden(red_c, audit_mode=True)) if context is not None else 0
            )
        else:
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


def redaction_status_for(prompt: object, context: object = None, audit_mode: bool = False) -> str:
    """Convenience: return only the gate status string (PASSED or BLOCKED)."""
    return evaluate_redaction_gate(prompt, context, audit_mode=audit_mode).status


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
    "AUDIT_STRUCTURAL_CATEGORIES",
    "REQUIRED_TARGET_MARKER_PREFIX",
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
