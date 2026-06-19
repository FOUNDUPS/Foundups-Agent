#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fusion ALIAS live path -- VALVE-GATED, redaction-gated, advisory-only OpenRouter call.

Slice: HERMES_FUSION_ALIAS_MODE_PHASE2. This is the first live OpenRouter integration, but it makes
ZERO live calls by default: the network call is gated behind a SOVEREIGN VALVE -- BOTH an env flag
(FUSION_ALIAS_LIVE_ENABLED, default OFF) AND a typed LiveFusionAuthorization (authority="012"). Raw
text is redacted ON ENTRY via the landed redaction gate; only the REDACTED text is ever sent; only
digests are retained. Output is ADVISORY only. SERVER_TOOL / LOCAL_FALLBACK stay blocked (not here).

WSP 97 TRUTH BOUNDARIES:
  DOES: redact raw on entry; refuse unless the gate PASSED; require env-flag AND typed 012 authorization
        before any call; send only the redacted text; one bounded request (no stream, no retry); parse
        into an advisory ModelContributionReceipt (digests from redacted output); fail closed everywhere.
  DOES NOT: make any call by default; send unredacted content; retain/log raw prompt/context; log the
        API key; enable SERVER_TOOL/LOCAL_FALLBACK; touch CABR/payout/source-authority/merge authority;
        add a new dependency (reuses `requests`, already used by ai_gateway).

Live input never becomes storage: raw prompt/context exist only as function arguments long enough to
call evaluate_redaction_gate(). They never enter FusionRequest, the receipt, a log, or any object field.

WSP: WSP 11 (interface), WSP 50 (pre-action), WSP 84 (reuse HTTP client), WSP 97 (truth boundary).
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests  # REUSED from ai_gateway's HTTP stack (ai_gateway.py imports requests) -- NOT a new dependency

from .fusion_adapter import (
    NOT_EVALUATED,
    FusionProvider,
    ModelContributionReceipt,
    digest,
)
from .fusion_redaction_gate import (
    REDACTION_GATE_PASSED,
    evaluate_redaction_gate,
    redact_text,
    scan_forbidden,
)

# --- config (all bounded) ----------------------------------------------------
ENV_LIVE_FLAG = "FUSION_ALIAS_LIVE_ENABLED"
ENV_API_KEY = "OPENROUTER_API_KEY"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_ALIAS_MODEL = "openrouter/fusion"
EXPECTED_AUTHORITY = "012"
EXPECTED_PURPOSE = "fusion_alias_live_call"
DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 60
DEFAULT_MAX_TOKENS = 1024
MAX_TOKENS_CEILING = 4096
RESPONSE_SUMMARY_CHARS = 200

# --- low-cardinality reasons (never echo raw input) --------------------------
REASON_OK = "ok"
REASON_VALVE_CLOSED = "valve_closed"
REASON_REDACTION_BLOCKED = "redaction_blocked"
REASON_AUTHORIZATION_MISSING = "authorization_missing"
REASON_MISSING_API_KEY = "missing_api_key"
REASON_BUDGET_EXCEEDED = "budget_exceeded"
REASON_TIMEOUT = "timeout"
REASON_HTTP_ERROR = "http_error"
REASON_MALFORMED_RESPONSE = "malformed_response"
ALIAS_REASONS = frozenset(
    {
        REASON_OK,
        REASON_VALVE_CLOSED,
        REASON_REDACTION_BLOCKED,
        REASON_AUTHORIZATION_MISSING,
        REASON_MISSING_API_KEY,
        REASON_BUDGET_EXCEEDED,
        REASON_TIMEOUT,
        REASON_HTTP_ERROR,
        REASON_MALFORMED_RESPONSE,
    }
)

STATUS_ADVISORY_OK = "advisory_ok"
STATUS_BLOCKED = "blocked"


@dataclass(frozen=True)
class LiveFusionAuthorization:
    """Typed sovereign authorization -- NOT a bool. A plain True/1/"true"/dict cannot satisfy it."""

    authorized: bool
    authority: str
    purpose: str

    def is_valid(self) -> bool:
        return (
            self.authorized is True
            and self.authority == EXPECTED_AUTHORITY
            and self.purpose == EXPECTED_PURPOSE
        )


@dataclass
class AliasLiveResult:
    status: str                 # STATUS_ADVISORY_OK | STATUS_BLOCKED
    reason: str                 # one of ALIAS_REASONS
    made_network_call: bool
    receipt: Optional[ModelContributionReceipt]


def _env_flag_enabled() -> bool:
    return os.getenv(ENV_LIVE_FLAG, "").strip().lower() in {"1", "true", "yes", "on"}


def _authorization_valid(authorization: object) -> bool:
    # Must be a real LiveFusionAuthorization instance -- bool/int/str/dict cannot coerce in.
    return isinstance(authorization, LiveFusionAuthorization) and authorization.is_valid()


def _blocked(reason: str, made_network_call: bool = False) -> AliasLiveResult:
    return AliasLiveResult(status=STATUS_BLOCKED, reason=reason, made_network_call=made_network_call, receipt=None)


def _receipt_id(task_id: object) -> str:
    return "rcpt_alias_" + hashlib.sha256(str(task_id).encode("utf-8")).hexdigest()[:12]


def _safe_response_summary(text: object) -> str:
    """Re-scan the model response with the same policy BEFORE it can enter the receipt.

    If the response carries any forbidden/block pattern, withhold it (store nothing raw). Otherwise a
    bounded, redacted summary is allowed. The full response is never stored.
    """
    if not isinstance(text, str):
        return "[no response]"
    redacted, report = redact_text(text)
    if report.blocked_categories or scan_forbidden(redacted):
        return "[response withheld: failed post-response scan]"
    return redacted[:RESPONSE_SUMMARY_CHARS]


def _build_receipt(
    task_id: object,
    slice_id: Optional[str],
    redacted_prompt_digest: str,
    response_text: object,
    token_usage: Optional[Dict[str, int]],
    latency_ms: Optional[float],
) -> ModelContributionReceipt:
    response_digest = digest(response_text) if isinstance(response_text, str) else digest("")
    return ModelContributionReceipt(
        receipt_id=_receipt_id(task_id),
        task_id=str(task_id),
        slice_id=slice_id,
        provider=FusionProvider.OPENROUTER.value,
        mode="alias",
        outer_model=OPENROUTER_ALIAS_MODEL,
        panel_models=[OPENROUTER_ALIAS_MODEL],
        judge_model=OPENROUTER_ALIAS_MODEL,
        prompt_digest=redacted_prompt_digest,
        response_digest=response_digest,
        consensus=_safe_response_summary(response_text),
        token_usage=token_usage,
        latency_ms=latency_ms,
        accepted_by_judge=False,
        later_verified_outcome=NOT_EVALUATED,
        wsp97_status=NOT_EVALUATED,
        redaction_status=REDACTION_GATE_PASSED,
        advisory_not_canonical=True,
    )


def run_alias_live(
    prompt: object,
    context: object = None,
    *,
    authorization: object = None,
    task_id: str = "alias-live",
    slice_id: Optional[str] = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> AliasLiveResult:
    """Run a redacted, valve-gated, advisory-only ALIAS call. Makes NO call unless every gate opens.

    Precedence (fail-closed): redaction gate PASSED -> env flag ON -> typed 012 authorization ->
    API key present -> budget within bounds -> ONE bounded POST. Any failure -> blocked, no raw leak.
    """
    # 1. Redact on entry. Raw prompt/context are used ONLY to compute the gate result and never stored.
    gate = evaluate_redaction_gate(prompt, context)
    if not gate.passed:
        return _blocked(REASON_REDACTION_BLOCKED)  # BLOCK category / dirty -> no request body is built

    # 2. Sovereign valve, part A: env flag. (Env flag ALONE cannot enable a call -- see part B.)
    if not _env_flag_enabled():
        return _blocked(REASON_VALVE_CLOSED)

    # 3. Sovereign valve, part B: typed 012 authorization (not bool-coercible).
    if not _authorization_valid(authorization):
        return _blocked(REASON_AUTHORIZATION_MISSING)

    # 4. API key (read via env; NEVER logged/echoed/stored).
    api_key = os.getenv(ENV_API_KEY)
    if not api_key:
        return _blocked(REASON_MISSING_API_KEY)

    # 5. Budget bounds.
    if not isinstance(max_tokens, int) or max_tokens <= 0 or max_tokens > MAX_TOKENS_CEILING:
        return _blocked(REASON_BUDGET_EXCEEDED)
    bounded_timeout = min(max(1, int(timeout_seconds)), MAX_TIMEOUT_SECONDS)

    # 6. Build the request from the REDACTED text ONLY (redacted prompt + redacted context, if any).
    #    No streaming, single request.
    messages: List[Dict[str, str]] = []
    if context is not None and gate.redacted_context:
        messages.append({"role": "system", "content": gate.redacted_context})
    messages.append({"role": "user", "content": gate.redacted_prompt})
    body: Dict[str, Any] = {
        "model": OPENROUTER_ALIAS_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": False,
    }
    headers = {"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}

    # 7. One bounded POST. No retry storm. Every error path is fail-closed advisory.
    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=body, timeout=bounded_timeout)
    except requests.exceptions.Timeout:
        return _blocked(REASON_TIMEOUT, made_network_call=True)
    except Exception:
        return _blocked(REASON_HTTP_ERROR, made_network_call=True)

    if getattr(resp, "status_code", 500) != 200:
        return _blocked(REASON_HTTP_ERROR, made_network_call=True)

    try:
        data = resp.json()
        response_text = data["choices"][0]["message"]["content"]
        token_usage = data.get("usage")
    except Exception:
        return _blocked(REASON_MALFORMED_RESPONSE, made_network_call=True)

    receipt = _build_receipt(task_id, slice_id, gate.prompt_digest, response_text, token_usage, None)
    return AliasLiveResult(status=STATUS_ADVISORY_OK, reason=REASON_OK, made_network_call=True, receipt=receipt)


def run_manual_smoke(argv: Optional[List[str]] = None) -> int:
    """MANUAL live smoke -- NOT a pytest, NOT collected by CI. Requires explicit opt-in:
    FUSION_ALIAS_LIVE_ENABLED=1, a real OPENROUTER_API_KEY, and the --authorize-012 argument.

    Without --authorize-012 it refuses. It prints only status/reason/digests -- never the API key.
    """
    import sys

    args = list(argv) if argv is not None else sys.argv[1:]
    if "--authorize-012" not in args:
        print("[fusion-alias smoke] refusing: pass --authorize-012 to authorize a live call.")
        return 2
    auth = LiveFusionAuthorization(authorized=True, authority=EXPECTED_AUTHORITY, purpose=EXPECTED_PURPOSE)
    result = run_alias_live("hello from the manual fusion alias smoke", authorization=auth, task_id="manual-smoke")
    print(
        "[fusion-alias smoke] status=%s reason=%s made_network_call=%s"
        % (result.status, result.reason, result.made_network_call)
    )
    if result.receipt is not None:
        print(
            "[fusion-alias smoke] receipt_id=%s redaction_status=%s advisory_not_canonical=%s"
            % (result.receipt.receipt_id, result.receipt.redaction_status, result.receipt.advisory_not_canonical)
        )
    return 0


__all__ = [
    "ENV_LIVE_FLAG",
    "ENV_API_KEY",
    "OPENROUTER_URL",
    "OPENROUTER_ALIAS_MODEL",
    "EXPECTED_AUTHORITY",
    "EXPECTED_PURPOSE",
    "MAX_TOKENS_CEILING",
    "ALIAS_REASONS",
    "REASON_OK",
    "REASON_VALVE_CLOSED",
    "REASON_REDACTION_BLOCKED",
    "REASON_AUTHORIZATION_MISSING",
    "REASON_MISSING_API_KEY",
    "REASON_BUDGET_EXCEEDED",
    "REASON_TIMEOUT",
    "REASON_HTTP_ERROR",
    "REASON_MALFORMED_RESPONSE",
    "STATUS_ADVISORY_OK",
    "STATUS_BLOCKED",
    "LiveFusionAuthorization",
    "AliasLiveResult",
    "run_alias_live",
    "run_manual_smoke",
]


if __name__ == "__main__":  # manual smoke entry -- never collected by pytest
    raise SystemExit(run_manual_smoke())
