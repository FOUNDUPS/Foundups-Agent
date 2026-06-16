#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Framework-agnostic INTAKE ADAPTER -- transport-neutral request -> draft envelope.

FOUNDUP_LAUNCH_REQUEST_INTAKE_TRANSPORT_PHASE3.

This is the missing wiring between a transport (whatever framework receives a request)
and the EXISTING intake pipeline. It is PURE orchestration + token EXTRACTION:

  1. It extracts the session/invite TOKEN STRINGS only from TRANSPORT METADATA
     (headers + cookies), NEVER from the body. A body field named session_token /
     invite_token / authenticated / on_behalf_of / vouch can NEVER authenticate.
  2. It calls the EXISTING Phase-2 build_intake_context (#821) to verify those strings,
     the EXISTING Phase-1 validate_launch_request + to_genesis_envelope (#810) to produce
     a DRAFT FoundUpGenesisEnvelope. It REIMPLEMENTS none of that verification/mapping.
  3. It returns a DRAFT envelope dict OR a SAFE generic rejection. It does NOT speak HTTP
     (http_status is advisory only), writes no catalog/repo/registry/Kanban, makes no
     entitlement decision, and imports NO web framework / network / subprocess.

CRITICAL ORDERING (012's load-bearing requirement: an INVALID proposal must NOT consume a
single-use invite). The pipeline is STRICTLY ordered so that EVERY body-shape failure is
PRE-PROVIDER (zero build_intake_context calls -> the invite nonce is never claimed):

  1. normalize headers/cookies (case-insensitive names; detect collisions)   [pre-provider]
  2. enforce max_body_bytes BEFORE any decode/parse (oversize -> reject)      [pre-provider]
  3. parse + validate the proposal body: UTF-8 only, JSON OBJECT only,
     allowlisted proposal fields only, reject auth-ish/unknown fields,
     require non-empty proposed_name                                         [pre-provider]
  4. extract token strings (session/invite) from headers/cookies             [pre-provider]
  5. call build_intake_context EXACTLY ONCE  (the ONLY provider call)        [PROVIDER]
  6. validate_launch_request(proposal_dict, context)                         [post-provider]
  7. to_genesis_envelope(...) -> draft envelope                              [post-provider]

PRE-PROVIDER failures (status=rejected, ZERO provider calls, invite NOT consumed):
  - oversize body (step 2)
  - invalid UTF-8 body / non-JSON / JSON that is not an object (step 3)
  - unknown / forbidden / auth-ish proposal field, missing proposed_name (step 3)
  - any header/cookie token EXTRACTION ambiguity that makes a mechanism unusable BUT note:
    a *missing/ambiguous* token does NOT pre-empt the provider; we still call the provider
    EXACTLY ONCE with whatever clean strings we have (possibly both None) so the
    fail-closed authentication decision is made in ONE place (#821). What is rejected
    PRE-PROVIDER for extraction is only the per-mechanism ambiguity that nullifies that
    mechanism's token (the string is dropped to None); the body has already passed.

POST-PROVIDER failures (status=rejected, provider WAS called exactly once):
  - the verified context opens no gate (not authenticated / invite not verified) -> #810
    validate_launch_request fails the intake gate -> generic not_authorized.
  - (the proposal body already passed its own allowlist gate pre-provider, so post-provider
    rejections are authentication/gate failures, mapped to the generic not_authorized.)

RESULT IS NOT A SECRET SIDE CHANNEL (Addendum C): IntakeResult.reason is low-cardinality
enum-like -- exactly one of {created, invalid_request, not_authorized}. It NEVER carries
token parse details, signature/replay/nonce facts, raw body text, or header/cookie values.
Forged / expired / replayed / missing / malformed tokens are INDISTINGUISHABLE in the
result (all -> not_authorized).

REUSE (import, do not copy):
  - Phase-2 verifier (#821), the ONLY thing that verifies tokens / consumes the invite:
    .intake_auth_provider.build_intake_context  (default _provider seam)
  - Phase-1 pipeline (#810): .launch_request.validate_launch_request / to_genesis_envelope
  - Phase-1 PAYLOAD policy (REUSED WHOLE for the PRE-PROVIDER body gate so an invalid body is
    rejected BEFORE the provider is ever called): the SAME public validate_launch_request is
    run as a PAYLOAD PRE-FLIGHT against a strictly-local throwaway
    LaunchRequestIntakeContext(authenticated=True). That dummy context forces ONLY the intake
    gate open so preflight.ok reflects PAYLOAD VALIDITY ALONE -- every payload check at once:
    allowed-fields, auth-field scan, #807 authority scan, reference_urls (_check_url_ref), and
    non-empty proposed_name. This makes the pre-gate a COMPLETE SUPERSET of the post-provider
    payload checks, so no payload defect (now OR future) can reach the provider and burn an
    invite. validate_launch_request has NO side effects (consumes no nonce), so the preflight +
    the real validate (step 6) are harmless. The dummy context is NEVER returned, NEVER used as
    the real context, and NEVER reaches build_intake_context -- it is not an auth bypass.
  NOTE: the real intake GATE (authenticated / invite_token_verified) is still decided ONLY by
  the provider-built context in step 6; the preflight tests payload shape, not authentication.

NOT ROUTED THROUGH (confused-deputy hazard -- verified by direct read):
  - modules/foundups/pfmall/http_api.py is GET-only (no POST intake; @app.get only).
  - modules/communication/moltbot_bridge/src/webhook_receiver.py is a GENERIC OpenClaw
    router (POST /webhook/openclaw -> OpenClawDAE.process); routing proposals through it
    would trust a relayed/generic assertion. This adapter is framework-agnostic and is NOT
    wired into either; SURFACE BINDING is deferred (see SURFACE_BINDING_SLICE).

DEFERRED (named, not built here):
  - FOUNDUP_LAUNCH_REQUEST_INTAKE_SURFACE_BINDING_PHASE3C: bind this adapter to a concrete
    transport surface (the function that reads a real request and calls intake_request).
  - FOUNDUP_LAUNCH_REQUEST_ENTITLEMENT_PHASE3B: what a verified handle is ALLOWED to launch.

NAVIGATION:
  -> Calls (exactly once): build_intake_context (#821) -> validate_launch_request +
     to_genesis_envelope (#810)
  -> Tested by: tests/test_intake_transport.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Union

# REUSE the EXISTING pipeline (#810/#821) -- sibling intake modules only. No reimplementation.
from .intake_auth_provider import build_intake_context
from .launch_request import (
    LaunchRequestError,
    LaunchRequestIntakeContext,
    to_genesis_envelope,
    validate_launch_request,
)

__all__ = [
    "intake_request",
    "IntakeResult",
    "SURFACE_BINDING_SLICE",
    "ENTITLEMENT_SLICE",
]
# Internal helpers (_extract_*, _parse_body, etc.) are deliberately NOT exported: they are
# extraction primitives that must not be reachable as a public surface (could leak a token).

# Deferred follow-up slices (named, not built here).
SURFACE_BINDING_SLICE = "FOUNDUP_LAUNCH_REQUEST_INTAKE_SURFACE_BINDING_PHASE3C"
ENTITLEMENT_SLICE = "FOUNDUP_LAUNCH_REQUEST_ENTITLEMENT_PHASE3B"

# Transport header / cookie names (case-insensitive for header NAMES only).
_AUTHORIZATION_HEADER = "authorization"
_INVITE_HEADER = "x-foundup-invite"
_SESSION_COOKIE = "foundup_session"
_INVITE_COOKIE = "foundup_invite"
_BEARER_PREFIX = "bearer "  # matched case-insensitively on the scheme only

# Token KINDVER prefixes (must match #821). Used ONLY to reject obvious non-tokens early;
# the AUTHORITATIVE verification (signature/time/kind-lock) is #821's job, not ours.
_SESSION_KINDVER = "sess.v1"
_INVITE_KINDVER = "invite.v1"

# Defensive token-string bound (mirrors #821 _MAX_TOKEN_LEN). A hostile mega-string is
# dropped to None here so it never reaches the verifier; #821 also bounds it independently.
_MAX_TOKEN_LEN = 4096

# Low-cardinality, enum-like reasons (Addendum C). These are the ONLY strings reason may
# ever take. NONE of them encodes token/signature/replay/nonce/body specifics.
_REASON_CREATED = "created"
_REASON_INVALID = "invalid_request"     # body-shape failure (pre-provider)
_REASON_NOT_AUTHORIZED = "not_authorized"  # any auth/gate failure (provider/post-provider)

# Advisory HTTP status codes (the adapter does NOT speak HTTP; this is a hint only).
_HTTP_CREATED = 201
_HTTP_BAD_REQUEST = 400
_HTTP_UNAUTHORIZED = 401


@dataclass
class IntakeResult:
    """Outcome of a transport-neutral intake attempt.

    status: "created" (a draft envelope was produced) or "rejected".
    envelope: on success, the DRAFT FoundUpGenesisEnvelope.to_dict(); else None.
    reason: SAFE low-cardinality enum-like string -- one of
        {created, invalid_request, not_authorized}. NEVER carries token/secret/nonce/body
        detail (Addendum C); it is not a secret side channel.
    http_status: ADVISORY only (201/400/401). This adapter does not speak HTTP.
    """

    status: str
    envelope: Optional[dict]
    reason: str
    http_status: int


def _rejected(reason: str, http_status: int) -> IntakeResult:
    """Build a rejection with NO envelope and a generic, low-cardinality reason."""
    return IntakeResult(status="rejected", envelope=None, reason=reason, http_status=http_status)


def _invalid_request() -> IntakeResult:
    """PRE-PROVIDER body-shape failure: invalid_request / 400. Zero provider calls."""
    return _rejected(_REASON_INVALID, _HTTP_BAD_REQUEST)


def _not_authorized() -> IntakeResult:
    """Auth/gate failure: not_authorized / 401. Same reason for forged/expired/replayed/
    missing/malformed -- no auth oracle (Addendum C)."""
    return _rejected(_REASON_NOT_AUTHORIZED, _HTTP_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Step 1: header / cookie normalization (case-insensitive NAMES; reject collisions)
# ---------------------------------------------------------------------------


def _normalize_name_map(mapping: Optional[Mapping[str, str]]) -> Optional[dict]:
    """Lowercase header/cookie NAMES into a plain dict. Returns None if a case-insensitive
    name COLLISION is representable in the input (e.g. both 'Authorization' and
    'authorization', or duplicate cookie names) -- ambiguous transport metadata is rejected
    fail-closed (Addendum A). VALUES are left byte-for-byte untouched here.
    """
    if mapping is None:
        return {}
    out: dict = {}
    try:
        items = list(mapping.items())
    except Exception:
        return None
    for raw_name, value in items:
        if not isinstance(raw_name, str) or not isinstance(value, str):
            return None
        name = raw_name.lower()
        if name in out:
            # Two distinct input keys fold to the same lowercased name -> collision.
            return None
        out[name] = value
    return out


# ---------------------------------------------------------------------------
# Step 2+3: body size gate + parse + proposal-field allowlist gate (PRE-PROVIDER)
# ---------------------------------------------------------------------------


def _parse_and_validate_body(
    body: Union[bytes, str, Mapping], max_body_bytes: int
) -> Optional[dict]:
    """Enforce size -> decode UTF-8 -> JSON OBJECT -> proposal-field allowlist. PRE-PROVIDER.

    Returns a clean plain proposal dict on success, or None on ANY body-shape failure (the
    caller maps None -> invalid_request with ZERO provider calls, so an invalid/oversize
    body never consumes a single-use invite). The raw body is NEVER logged.

    Ordering inside this function mirrors the load-bearing requirement:
      a) max_body_bytes BEFORE any decode/parse
      b) UTF-8 decode only (invalid UTF-8 -> reject)
      c) JSON parse; must be a JSON OBJECT (reject arrays/strings/numbers/bools/null)
      d) COPY into a new plain dict (no proxy/mutable side effects)
      e) COMPLETE payload preflight via validate_launch_request (reject unknown / auth-ish /
         authority / bad reference_urls; require a non-empty proposed_name STRING) -- see
         _proposal_fields_ok. A superset of the post-provider payload checks.
    """
    # (a) size BEFORE parse. For str, count UTF-8 bytes (the wire size). For a Mapping body,
    # serialize a copy deterministically and bound THAT (a mapping has no wire form).
    if isinstance(body, (bytes, bytearray)):
        if len(body) > max_body_bytes:
            return None
        raw_bytes = bytes(body)
        try:
            text = raw_bytes.decode("utf-8")  # (b) strict UTF-8 only
        except (UnicodeDecodeError, ValueError):
            return None
        parsed = _json_object(text)
        if parsed is None:
            return None
    elif isinstance(body, str):
        try:
            byte_len = len(body.encode("utf-8"))
        except (UnicodeEncodeError, ValueError):
            return None
        if byte_len > max_body_bytes:
            return None
        parsed = _json_object(body)
        if parsed is None:
            return None
    elif isinstance(body, Mapping):
        # A Mapping body did not arrive as wire bytes; COPY it into a plain dict first (no
        # proxy/mutable side effects -- Addendum B), then bound its serialized size so a
        # giant in-memory mapping is still rejected pre-provider.
        try:
            parsed = {k: v for k, v in body.items()}
        except Exception:
            return None
        try:
            approx = json.dumps(parsed, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return None
        if len(approx.encode("utf-8")) > max_body_bytes:
            return None
    else:
        # bytes/str/Mapping only.
        return None

    # (d) COPY into a fresh plain dict (already a dict from _json_object / mapping copy, but
    # re-copy defensively so nothing aliases caller state).
    data = dict(parsed)

    # (e) proposal-field allowlist gate -- REUSE Phase-1 policy, applied PRE-PROVIDER.
    if not _proposal_fields_ok(data):
        return None
    return data


def _json_object(text: str) -> Optional[dict]:
    """Parse `text` as JSON and require a JSON OBJECT. Reject arrays/strings/numbers/bools/
    null (Addendum B). Returns the dict or None. Never logs `text`."""
    try:
        value = json.loads(text)
    except (ValueError, TypeError, RecursionError):
        return None
    if not isinstance(value, dict):
        return None
    return value


def _proposal_fields_ok(data: Mapping[str, Any]) -> bool:
    """COMPLETE PRE-PROVIDER body gate -- a SUPERSET of validate_launch_request's PAYLOAD
    checks, so NO payload defect (now or future) can reach the provider and burn a
    single-use invite (SENTINEL FINDING 1).

    Strategy: run the EXISTING public validator as a PAYLOAD PRE-FLIGHT against a STRICTLY
    LOCAL throwaway LaunchRequestIntakeContext(authenticated=True). That dummy context is
    used ONLY to force the intake GATE open (validate_launch_request.step 6) so that
    `preflight.ok` reflects PAYLOAD VALIDITY ALONE -- every payload check at once:
        - allowed-fields allowlist        (launch_request.py:208-211)
        - auth-ish field scan             (_scan_auth_fields, launch_request.py:214)
        - #807 authority scan             (_scan_authority, launch_request.py:218)
        - reference_urls validation       (_check_url_ref, launch_request.py:221-222)  <-- the
          check OMITTED by the old pre-gate, which let a bad reference_urls entry slip past
          pre-provider and burn the invite POST-provider.
        - non-empty proposed_name         (launch_request.py:225-226)

    SECURITY NOTE -- this is NOT an auth bypass. The dummy context is a throwaway created and
    discarded INSIDE this function; it is NEVER returned, NEVER used as the real context, and
    NEVER reaches build_intake_context. The REAL intake gate is still decided ONLY by the
    provider-built context in intake_request (step 6). validate_launch_request has NO side
    effects (it consumes no nonce, touches no store), so calling it here for a payload preflight
    and AGAIN for real (with the trusted context) is harmless.

    FINDING 3 (stricter than Phase 1): proposed_name must be a NON-EMPTY str INSTANCE. Phase 1
    coerces via str(), so str(None)=='None' / str(123)=='123' would pass its non-empty check; we
    do NOT change Phase 1, we enforce the stricter type rule HERE so a typed/null name rejects
    PRE-provider with zero provider calls (no envelope named 'None'/'123' can ever be produced).
    """
    # FINDING 3: require a real non-empty string instance BEFORE the preflight (reject
    # None / int / bool / dict / list names that str()-coercion would otherwise let through).
    name = data.get("proposed_name", "")
    if not isinstance(name, str) or not name.strip():
        return False

    # FINDING 1: COMPLETE payload preflight. The dummy authenticated context forces the gate
    # open so preflight.ok == "payload has NO defect" (fields/auth/authority/reference_urls/name).
    # This dummy is LOCAL-ONLY -- never returned, never the real context (see SECURITY NOTE).
    preflight = validate_launch_request(dict(data), LaunchRequestIntakeContext(authenticated=True))
    return preflight.ok


# ---------------------------------------------------------------------------
# Step 4: token EXTRACTION from transport metadata (NEVER the body)
# ---------------------------------------------------------------------------


def _token_value_ok(token: str, expected_kindver: str) -> bool:
    """A token VALUE must be clean and carry the expected KINDVER prefix.

    Addendum E: VALUES are NOT lowercased / NFKC-normalized / internally stripped. Only
    external whitespace around the WHOLE token was trimmed by the caller. Here we reject a
    token that contains control chars, internal whitespace, a comma, or any non-ASCII, and
    require the EXACT ASCII KINDVER prefix (so a fullwidth / Unicode-lookalike prefix can
    never be coerced into a valid sess.v1/invite.v1). We never transform the value.
    """
    if not isinstance(token, str) or not token:
        return False
    if len(token) > _MAX_TOKEN_LEN:
        return False
    for ch in token:
        o = ord(ch)
        if o < 0x20 or o == 0x7F:   # control chars (incl. CR/LF/TAB)
            return False
        if o > 0x7F:                # non-ASCII (rejects fullwidth lookalikes)
            return False
        if ch.isspace():            # internal ASCII whitespace
            return False
        if ch == ",":               # comma (Authorization list separator)
            return False
    # EXACT ASCII prefix -- value is NOT normalized to make it match.
    return token.startswith(expected_kindver + ".")


# RFC 7230 OWS = SP / HTAB only. Addendum E permits trimming ONLY this external ASCII set;
# bare str.strip() would also strip the FULL Unicode-whitespace class (CR, LF, VTAB 0x0B,
# FF 0x0C, NBSP U+00A0, U+2003, U+2028, ZWSP U+200B), which would COERCE a token decorated
# with those characters into validity (SENTINEL FINDING 2). _token_value_ok then rejects any
# control/CR/LF/non-ASCII that survives this OWS-only trim, so the boundary char itself fails.
_OWS = " \t"


def _trim_outer(value: Optional[str]) -> Optional[str]:
    """Trim ONLY external RFC-7230 OWS (SP / HTAB) around the whole token (Addendum E). No
    inner change, and NO stripping of CR/LF/VTAB/FF/NBSP/Unicode-whitespace -- those are left
    on the value so _token_value_ok rejects them (FINDING 2)."""
    if not isinstance(value, str):
        return None
    return value.strip(_OWS)


def _extract_session(headers: dict, cookies: dict) -> Optional[str]:
    """Extract a session token: Authorization Bearer takes precedence; the session cookie is
    used ONLY if Authorization is entirely absent (Addendum A).

    - Authorization present but malformed (not exactly one 'Bearer <token>') -> the session
      mechanism is rejected (return None); we do NOT fall back to the cookie.
    - Header token AND cookie token both present but DIFFER -> reject (return None).
    - Returned value is the UNMODIFIED token (outer-trim only) iff it passes _token_value_ok.
    """
    auth_raw = headers.get(_AUTHORIZATION_HEADER)
    cookie_tok = _trim_outer(cookies.get(_SESSION_COOKIE)) if cookies else None

    if auth_raw is not None:
        header_tok = _parse_single_bearer(auth_raw)
        if header_tok is None:
            # Authorization present but malformed/multiple -> reject; NO cookie fallback.
            return None
        if not _token_value_ok(header_tok, _SESSION_KINDVER):
            return None
        if cookie_tok is not None and cookie_tok != header_tok:
            # Header + cookie both present and DIFFER -> ambiguous -> reject.
            return None
        return header_tok

    # Authorization absent -> cookie only.
    if cookie_tok is None:
        return None
    if not _token_value_ok(cookie_tok, _SESSION_KINDVER):
        return None
    return cookie_tok


def _parse_single_bearer(auth_raw: str) -> Optional[str]:
    """Return the single Bearer token from an Authorization header, else None.

    Rejects: multiple Bearer tokens, a comma-separated credential list, or a scheme that is
    not exactly 'Bearer'. The scheme match is case-insensitive; the TOKEN VALUE is not
    altered beyond the OWS outer trim (Addendum A + E).

    FINDING 2: outer trims use OWS only (SP / HTAB), NOT bare str.strip(). A token decorated
    with a leading/trailing CR/LF/VTAB/FF/NBSP/Unicode-whitespace is therefore NOT trimmed to
    validity here -- the residual char is left on the token so _token_value_ok (and the
    internal-whitespace guard below) rejects it as not_authorized. The scheme/token split is
    on an ASCII SP/HTAB run only (not the Unicode-whitespace class) so a Unicode separator can
    never be coerced into a valid 'Bearer <token>' delimiter either."""
    if not isinstance(auth_raw, str):
        return None
    stripped = auth_raw.strip(_OWS)  # OWS-only outer trim (FINDING 2)
    if not stripped:
        return None
    # A comma indicates a credential list / multiple tokens -> reject the mechanism.
    if "," in stripped:
        return None
    # Scheme + token, split on the FIRST ASCII SP/HTAB run only. We deliberately do NOT use
    # str.split(None,...) (which splits on the FULL Unicode-whitespace class), so a CR/LF/VTAB/
    # FF/NBSP/U+2028/etc separator cannot masquerade as the scheme/token delimiter (FINDING 2).
    scheme, sep, token = _split_first_ows(stripped)
    if not sep:
        return None
    if scheme.lower() + " " != _BEARER_PREFIX:
        return None
    token = token.strip(_OWS)  # OWS-only outer trim (FINDING 2)
    # A second 'Bearer' (or ANY internal whitespace -- ASCII or Unicode) means multiple tokens
    # / a smuggled separator -> reject. (_token_value_ok independently rejects these too.)
    if not token or any(c.isspace() for c in token):
        return None
    return token


def _split_first_ows(value: str) -> tuple[str, str, str]:
    """Split `value` once on the FIRST run of ASCII OWS (SP/HTAB) only.

    Returns (before, separator, after). `separator` is the matched OWS run (truthy) when a
    split occurred, or "" when there is no SP/HTAB in `value` (no split -> caller rejects).
    Unlike str.split(None, 1) this NEVER treats CR/LF/VTAB/FF/NBSP/U+2028/etc as a delimiter,
    so a Unicode-whitespace separator cannot be coerced into a valid scheme/token boundary."""
    n = len(value)
    i = 0
    while i < n and value[i] not in _OWS:
        i += 1
    if i >= n:
        return (value, "", "")
    j = i
    while j < n and value[j] in _OWS:
        j += 1
    return (value[:i], value[i:j], value[j:])


def _extract_invite(headers: dict, cookies: dict) -> Optional[str]:
    """Extract an invite token: X-FoundUp-Invite header takes precedence; the invite cookie
    is used ONLY if the header is absent (Addendum A).

    - Header present but malformed (fails _token_value_ok) -> reject; NO cookie fallback.
    - Header token AND cookie token both present but DIFFER -> reject.
    """
    header_raw = headers.get(_INVITE_HEADER)
    cookie_tok = _trim_outer(cookies.get(_INVITE_COOKIE)) if cookies else None

    if header_raw is not None:
        header_tok = _trim_outer(header_raw)
        if not _token_value_ok(header_tok or "", _INVITE_KINDVER):
            # Header present but malformed -> reject; NO cookie fallback.
            return None
        if cookie_tok is not None and cookie_tok != header_tok:
            return None
        return header_tok

    if cookie_tok is None:
        return None
    if not _token_value_ok(cookie_tok, _INVITE_KINDVER):
        return None
    return cookie_tok


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def intake_request(
    headers: Mapping[str, str],
    body: Union[bytes, str, Mapping],
    *,
    cookies: Optional[Mapping[str, str]] = None,
    nonce_store=None,
    now=None,
    secret_provider=None,
    max_body_bytes: int = 16 * 1024,
    _provider: Optional[Callable] = None,
) -> IntakeResult:
    """Turn a transport-neutral request into a DRAFT FoundUpGenesisEnvelope or a SAFE reject.

    Args:
        headers: transport request headers (case-insensitive NAMES). Token strings are
            extracted ONLY from here (and cookies), NEVER from the body.
        body: the proposal body as bytes, str, or a Mapping of proposal fields. Carries
            proposal data ONLY; a token-looking body field can NEVER authenticate.
        cookies: transport cookies (optional). Session/invite cookies are used ONLY as a
            fallback when the corresponding header is absent (Addendum A).
        nonce_store: durable single-use NonceStore passed straight to #821 (single-use
            invite). If None, #821 scopes single-use to this call.
        now: unix seconds for #821 time checks (defaults to wall clock inside #821).
        secret_provider: zero-arg (current, previous) secret seam passed to #821 (Addendum
            E); tests inject without mutating os.environ.
        max_body_bytes: hard cap enforced BEFORE any decode/parse (default 16 KiB).
        _provider: injection seam for the provider (default build_intake_context). Tests use
            it to spy that the provider is called EXACTLY ONCE (Addendum D) without
            monkeypatching globals. It is verified to be called once on a valid body and
            ZERO times on an invalid/oversize body.

    Returns:
        IntakeResult. FAILS CLOSED: any unexpected error -> generic rejection (never an
        authenticated/created result). reason is low-cardinality {created, invalid_request,
        not_authorized}; it never leaks token/secret/nonce/body detail. The envelope is a
        DRAFT, RETURNED only -- no catalog/repo/registry/Kanban write, no entitlement.
    """
    provider = _provider if _provider is not None else build_intake_context
    try:
        # --- Step 1: normalize header/cookie NAMES; reject case collisions (pre-provider).
        norm_headers = _normalize_name_map(headers)
        norm_cookies = _normalize_name_map(cookies)
        if norm_headers is None or norm_cookies is None:
            return _invalid_request()

        # --- Steps 2+3: size gate + UTF-8 + JSON-object + proposal allowlist (pre-provider).
        # ANY body-shape failure returns here with ZERO provider calls, so a single-use
        # invite is NEVER consumed by an invalid/oversize/non-object/auth-field body.
        proposal = _parse_and_validate_body(body, max_body_bytes)
        if proposal is None:
            return _invalid_request()

        # --- Step 4: extract token strings from transport metadata ONLY (never the body).
        session_token = _extract_session(norm_headers, norm_cookies)
        invite_token = _extract_invite(norm_headers, norm_cookies)

        # --- Step 5: call the EXISTING verifier EXACTLY ONCE (the only provider call). It is
        # the ONLY thing that verifies tokens / consumes the invite nonce. We reach it only
        # AFTER the body passed every gate above (Addendum D).
        context = provider(
            session_token,
            invite_token,
            nonce_store=nonce_store,
            now=now,
            secret_provider=secret_provider,
        )

        # --- Step 6: validate the proposal against the TRUSTED context (#810). If the
        # context opened no gate (nothing verified), this fails the intake gate.
        result = validate_launch_request(proposal, context)
        if not result.ok:
            # Post-provider: an auth/gate failure. Generic reason -- no auth oracle.
            return _not_authorized()

        # --- Step 7: map the validated proposal to a DRAFT envelope (#810). requested_by
        # comes from the TRUSTED context handle, NEVER a body requester_handle.
        envelope = to_genesis_envelope(proposal, context)
        return IntakeResult(
            status="created",
            envelope=envelope.to_dict(),
            reason=_REASON_CREATED,
            http_status=_HTTP_CREATED,
        )
    except LaunchRequestError:
        # to_genesis_envelope re-validates and raises on a gate failure -> auth/gate reject.
        return _not_authorized()
    except Exception:
        # FAIL CLOSED on ANY unexpected error -> generic rejection. Never an authenticated
        # result; never a token/secret/nonce/body detail in the reason.
        return _not_authorized()
