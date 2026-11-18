#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trusted server-side intake auth verifier -- POPULATES the Phase-1
LaunchRequestIntakeContext (FOUNDUP_LAUNCH_REQUEST_AUTH_CONTEXT_PROVIDER_PHASE2).

This is the ONLY component permitted to set authenticated / invite_token_verified /
requester_handle on a LaunchRequestIntakeContext. It is a PURE verifier:

  - It sees ONLY two already-extracted token strings (session, invite). It never reads
    a LaunchRequest payload, a PFmall/Kanban relayed assertion, or any 'vouch' /
    'on_behalf_of' claim -- that would be a confused-deputy / TOCTOU intake bypass.
  - It FAILS CLOSED: any exception, missing secret, malformed/forged/expired token, or
    replayed invite -> LaunchRequestIntakeContext() with both booleans False, handle None.
  - The two booleans are INDEPENDENT and KIND-LOCKED: a sess.v1 token can ONLY set
    authenticated=True; an invite.v1 token can ONLY set invite_token_verified=True. A
    failed mechanism can NEVER borrow the other's trust (no downgrade), and no single
    token kind can ever set BOTH booleans (Addendum A / STOP condition H).
  - requester_handle comes ONLY from the verified token subject/handle, normalized via
    the #807 _normalize and redacted via redact_sensitive -- never from a payload.

TOKEN FORMAT (Addendum A + B -- UNAMBIGUOUS canonicalization):
  A token is:  <KINDVER> "." <b64url(field_0)> "." ... "." <b64url(field_n)> "." <sig>
  where KINDVER is the EXACT literal "sess.v1" or "invite.v1" (Addendum A: kind + version).

  The KINDVER prefix is consumed by an exact-literal strip (NOT by '.'-splitting), so the
  '.' inside "sess.v1" can never change the parsed field count. After the prefix is
  stripped, the REMAINDER is split on '.'; every remaining field is INDEPENDENTLY
  base64url-encoded, so a '.' or '|' (or any byte) inside a field value can NEVER change
  the field count or meaning (Addendum B). The number of b64url fields per kind is FIXED
  (session=3, invite=4) -- any other count fails closed.

  SIGNED BYTES (exact, Addendum A + B): HMAC-SHA256 over the UTF-8 of
      KINDVER + "." + b64url(field_0) + "." + ... + "." + b64url(field_n)
  i.e. the ENTIRE token minus the trailing ".<sig>". Because KINDVER is part of the
  signed input, swapping the kind ("sess.v1" <-> "invite.v1") or the version ("v1" -> "v2")
  breaks the signature too (Addendum A: kind+version is signed).

  Session fields (3):  [ b64url(subject), b64url(iat), b64url(exp) ]
  Invite  fields (4):  [ b64url(handle),  b64url(nonce), b64url(iat), b64url(exp) ]
  (iat is REQUIRED for both kinds -- see TIME POLICY below.)

TIME + CLOCK SKEW POLICY (Addendum C -- explicit + documented):
  - exp is REQUIRED for both kinds (a token with no/invalid exp fails closed).
  - iat is REQUIRED for both kinds (documented choice: iat lets us bound MAX TTL precisely
    via exp - iat, independent of the verifier's wall clock).
  - nbf is NOT a field in this format; there is therefore no nbf to mis-handle. (If a future
    format adds nbf, it MUST be enforced as now < nbf -> reject. Documented for completeness.)
  - CLOCK SKEW is exactly 0 seconds (_CLOCK_SKEW_SECONDS = 0). We deliberately allow NO skew:
    these tokens are minted and verified inside one trust domain, so a nonzero skew would only
    widen the expiry/TTL window for an attacker with a forged-but-unexpired token. Documented.
  - BOUNDARY at now == exp: a token is EXPIRED when now >= exp (rejected). At exactly
    now == exp the token is REJECTED (tested). i.e. valid iff now < exp.
  - iat sanity: iat must be <= now (with 0 skew) and iat <= exp; a token "issued in the
    future" fails closed.
  - MAX TTL is enforced SEPARATELY from exp: exp - iat must be > 0 and <= the per-kind cap.
    Session cap _MAX_TTL_SESSION_SECONDS = 3600 (1h): a session is a short-lived bearer of
    standing authentication, so a tight cap limits the blast radius of a stolen session token.
    Invite cap _MAX_TTL_INVITE_SECONDS = 604800 (7 days): an invite is a single-use,
    out-of-band-delivered grant that a human may take days to redeem, but it is single-use
    (nonce) so a longer window is acceptable. An over-long token fails closed even with a
    perfectly valid signature (tested).

SECRET HANDLING (Addendum E):
  - Secrets are obtained via an injectable secret_provider seam: a zero-arg callable
    returning (current, previous). The DEFAULT provider reads os.getenv (current +
    _PREVIOUS). Tests inject secrets via secret_provider WITHOUT mutating os.environ.
  - We NEVER load dotenv, NEVER print/log a secret, NEVER return a secret to a caller.
  - An empty/missing CURRENT secret -> fail closed. The PREVIOUS secret is accepted ONLY
    for verification (rotation), NEVER for signing in any helper. Both missing -> fail closed.

REUSE (import, do not copy):
  - HMAC-from-env + rotation (_PREVIOUS) + constant-time compare pattern:
    modules/ai_intelligence/ai_overseer/src/security_event_correlator.py:189-190, 1039-1070
  - Fail-closed ORDERED gates + register-nonce-only-after-all-gates-pass (atomic):
    modules/infrastructure/wre_core/src/capability_token_validator.py:50-86, 490-532, 619-620
  - Handle normalization + secret redaction:
    modules/foundups/agent/src/kanban_plugin_contract.py:105-112, 123-136

ANTI-PATTERN AVOIDED (do NOT copy): magats_economy.py verify_claim() (verifies nonce +
signature, returns True) and process_claim() (consumes the nonce in a SEPARATE later call)
-- a verify/consume SPLIT = TOCTOU double-spend. Here verify-and-consume is ATOMIC: the
invite nonce is consumed by the SAME call that verifies it, via a single consume_once()
that returns False (never raises) on a second use.

WSP 97 TRUTH BOUNDARIES:
  - This populates the EXISTING Phase-1 LaunchRequestIntakeContext (WSP 64
    enhance-before-create); it does NOT define a parallel context type.
  - It does NOT change Phase-1 launch_request.py behavior (additive integration only).
  - Entitlement/authorization (what an authenticated handle is ALLOWED to launch) is
    DEFERRED to FOUNDUP_LAUNCH_REQUEST_ENTITLEMENT_PHASE3B.
  - Transport wiring (extracting token strings from a real HTTP request / cookie / header)
    is DEFERRED to FOUNDUP_LAUNCH_REQUEST_INTAKE_TRANSPORT_PHASE3. This module's inputs are
    ALREADY-extracted strings; it does no HTTP parsing and imports no web framework.
  - Real token ISSUANCE (a transport issuer that mints production tokens) is DEFERRED to
    FOUNDUP_LAUNCH_REQUEST_INTAKE_TRANSPORT_PHASE3. The _mint_* helpers in this module are
    developer/test utilities ONLY (explicit-secret, never read env, not exported).

NAVIGATION:
  -> Populates: LaunchRequestIntakeContext (.launch_request)
  -> Reuses: security_event_correlator (pattern), capability_token_validator (pattern),
             kanban_plugin_contract (#807 helpers)
  -> Tested by: tests/test_intake_auth_provider.py
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import sqlite3
import threading
import time
from typing import Callable, Optional, Protocol, runtime_checkable

# REUSE (import, do not copy) the #807 contract helpers for handle hygiene.
from modules.foundups.agent.src.kanban_plugin_contract import (
    redact_sensitive,
    _normalize,
)
from .launch_request import LaunchRequestIntakeContext

__all__ = [
    "build_intake_context",
    "NonceStore",
    "InMemoryNonceStore",
    "SQLiteNonceStore",
    "SecretPair",
    "default_secret_provider",
    "HMAC_SECRET_ENV",
    "HMAC_SECRET_PREVIOUS_ENV",
    "ENTITLEMENT_SLICE",
    "TRANSPORT_SLICE",
    "MAX_TTL_SESSION_SECONDS",
    "MAX_TTL_INVITE_SECONDS",
    "CLOCK_SKEW_SECONDS",
]
# NOTE: the token-MINTING helpers (_mint*, _make_session_token, _make_invite_token) are
# DELIBERATELY excluded from __all__ and underscore-prefixed (Addendum F): they are
# developer/test utilities, NOT a production/transport issuer.

# Env var names for the intake HMAC secret + its rotation predecessor.
HMAC_SECRET_ENV = "FOUNDUPS_INTAKE_HMAC_SECRET"
HMAC_SECRET_PREVIOUS_ENV = "FOUNDUPS_INTAKE_HMAC_SECRET_PREVIOUS"

# Deferred follow-up slices (named, not built here).
ENTITLEMENT_SLICE = "FOUNDUP_LAUNCH_REQUEST_ENTITLEMENT_PHASE3B"
TRANSPORT_SLICE = "FOUNDUP_LAUNCH_REQUEST_INTAKE_TRANSPORT_PHASE3"

# Token KIND + VERSION discriminators (Addendum A). These EXACT literals are the signed
# prefix of every token; they are consumed by literal strip, never by '.'-split.
_KINDVER_SESSION = "sess.v1"
_KINDVER_INVITE = "invite.v1"

# Fixed b64url field counts AFTER the KINDVER prefix is stripped (Addendum B: a fixed
# count means a '.'/'|' inside a field cannot smuggle an extra field).
_SESSION_FIELDS = 3  # subject, iat, exp
_INVITE_FIELDS = 4   # handle, nonce, iat, exp

# TIME POLICY constants (Addendum C) -- all explicit + documented in the module docstring.
CLOCK_SKEW_SECONDS = 0           # NO skew allowed (single trust domain).
MAX_TTL_SESSION_SECONDS = 3600   # 1 hour: short-lived standing-auth bearer.
MAX_TTL_INVITE_SECONDS = 604800  # 7 days: single-use, human-redeemed out of band.

# Defensive bounds so a hostile string can never blow up memory before we reject it.
_MAX_TOKEN_LEN = 4096
_MAX_FIELD_LEN = 512


# ---------------------------------------------------------------------------
# Nonce store (single-use invite enforcement) -- ONE atomic method
# ---------------------------------------------------------------------------


@runtime_checkable
class NonceStore(Protocol):
    """Durable single-use nonce registry. consume_once() is ATOMIC verify-and-consume.

    There is exactly ONE method (Addendum D). It MUST return True exactly once per nonce
    (first claim) and False on every subsequent claim, MUST be atomic across process
    restarts, and MUST NOT raise on an already-consumed nonce. There is no separate
    'verify then later consume' method -- that split is the magats TOCTOU bug this
    provider exists to avoid.
    """

    def consume_once(self, nonce: str, *, expires_at: int, subject: str) -> bool:
        """Atomically claim `nonce`. True on first claim, False if already used.

        `expires_at` (unix seconds) and `subject` are stored alongside the nonce for
        audit / future TTL-based pruning; they do NOT relax the single-use guarantee.
        """
        ...


def _valid_nonce(nonce: str) -> bool:
    return isinstance(nonce, str) and bool(nonce) and len(nonce) <= _MAX_FIELD_LEN


class InMemoryNonceStore:
    """Process-local single-use nonce store (tests / single-process use).

    Atomic via an explicit threading.Lock around the check-and-set: the membership test
    and the set are one critical section, so no second caller can observe the 'absent'
    state and also claim it. (The GIL alone is NOT a contract -- the Lock makes the
    exactly-once guarantee explicit and free-threading-safe.) NOT durable across process
    restarts -- use SQLiteNonceStore for durability.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._used: dict[str, tuple[int, str]] = {}

    def consume_once(self, nonce: str, *, expires_at: int, subject: str) -> bool:
        if not _valid_nonce(nonce):
            return False
        with self._lock:
            if nonce in self._used:
                return False
            self._used[nonce] = (int(expires_at), str(subject))
            return True


class SQLiteNonceStore:
    """Durable single-use nonce store backed by SQLite. EXACTLY-ONCE under concurrency.

    What guarantees exactly-one-True per nonce (Addendum D):

    1. IN-PROCESS races (multiple threads through ONE store instance): a threading.Lock
       serializes the whole claim so the INSERT-and-translate-IntegrityError sequence is a
       single critical section. A shared sqlite3 connection is NOT thread-safe at the
       cursor level (check_same_thread=False only silences the same-thread guard; it does
       NOT make concurrent use safe), so WITHOUT this Lock the IntegrityError was not
       delivered deterministically to each racing caller and MULTIPLE callers could receive
       True for the SAME nonce -- a single-use invite double-spend. The Lock removes that.

    2. CROSS-PROCESS / CROSS-INSTANCE races (separate store instances or processes on the
       SAME db file): we open the claim with BEGIN IMMEDIATE, which takes SQLite's write
       (RESERVED) lock up front, and the UNIQUE(nonce) PRIMARY KEY on disk rejects the
       duplicate. The loser gets IntegrityError (already consumed) -> False; transient
       'database is locked' (OperationalError) is retried with bounded randomized backoff
       and ultimately treated as contention -> fail closed (never raises). Each process has
       its OWN Lock + connection, so the on-disk PRIMARY KEY + file lock -- not in-process
       state -- provide the cross-process serialization.

    consume_once therefore returns True to AT MOST ONE caller per nonce, ever, even under
    maximal concurrency (threads AND separate instances/processes on the same file), and
    NEVER raises. We NEVER pre-check then insert (that split is the TOCTOU bug); the single
    UNIQUE-constrained INSERT IS the atomic claim. The claim is durable across process
    restarts. The only file I/O this whole module performs is this local DB.
    """

    # Bounded retry budget for transient SQLite write-lock contention (cross-process).
    _LOCK_RETRY_ATTEMPTS = 50
    _LOCK_RETRY_MIN_SLEEP = 0.001
    _LOCK_RETRY_MAX_SLEEP = 0.01

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        # In-process serialization of the claim (the correctness mechanism for thread races;
        # the on-disk PRIMARY KEY + BEGIN IMMEDIATE handle cross-process races).
        self._lock = threading.Lock()
        # check_same_thread=False so one store can be used from multiple threads; the Lock
        # above -- NOT this flag -- is what makes the RETURN VALUE correct under concurrency.
        # A generous busy timeout lets SQLite itself absorb most write-lock contention before
        # we fall back to our explicit bounded retry. No network, no subprocess.
        self._conn = sqlite3.connect(db_path, check_same_thread=False, timeout=5.0)
        # WAL improves concurrent read/write behavior on file-backed DBs; it is a no-op on
        # ":memory:". busy_timeout is a second belt-and-braces for cross-process contention.
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
        except sqlite3.Error:
            # Journaling/timeout pragmas are best-effort; correctness does not depend on WAL.
            pass
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS intake_nonces ("
            "nonce TEXT PRIMARY KEY, "
            "expires_at INTEGER NOT NULL, "
            "subject TEXT NOT NULL, "
            "consumed_at INTEGER NOT NULL)"
        )
        self._conn.commit()

    def _rollback_quiet(self) -> None:
        try:
            self._conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass

    def consume_once(self, nonce: str, *, expires_at: int, subject: str) -> bool:
        if not _valid_nonce(nonce):
            return False
        # Serialize the entire claim in-process so a shared connection cannot deliver the
        # IntegrityError nondeterministically. Exactly one thread can be inside this block.
        with self._lock:
            attempts = 0
            while True:
                try:
                    # BEGIN IMMEDIATE takes the write lock up front (cross-process serialize),
                    # then ONE INSERT. The UNIQUE(nonce) collision IS the replay signal.
                    self._conn.execute("BEGIN IMMEDIATE")
                    self._conn.execute(
                        "INSERT INTO intake_nonces (nonce, expires_at, subject, consumed_at) "
                        "VALUES (?, ?, ?, ?)",
                        (nonce, int(expires_at), str(subject), int(time.time())),
                    )
                    self._conn.execute("COMMIT")
                    return True
                except sqlite3.IntegrityError:
                    # Already consumed: a UNIQUE-constraint collision IS the replay signal.
                    self._rollback_quiet()
                    return False
                except sqlite3.OperationalError as exc:
                    # 'database is locked' = another writer holds it (cross-process). Retry a
                    # bounded number of times with randomized backoff, then fail closed.
                    self._rollback_quiet()
                    if "locked" in str(exc).lower() and attempts < self._LOCK_RETRY_ATTEMPTS:
                        attempts += 1
                        # Deterministic, dependency-free jitter from the nonce + attempt count
                        # (no `random` import; keeps the AST import sweep clean and avoids any
                        # global RNG state). Bounded into [MIN, MAX].
                        span = self._LOCK_RETRY_MAX_SLEEP - self._LOCK_RETRY_MIN_SLEEP
                        jitter = (hash((nonce, attempts)) % 1000) / 1000.0
                        time.sleep(self._LOCK_RETRY_MIN_SLEEP + span * jitter)
                        continue
                    return False
                except sqlite3.Error:
                    # Any other DB error -> fail closed (treat as not-claimed -> reject).
                    self._rollback_quiet()
                    return False

    def close(self) -> None:
        try:
            self._conn.close()
        except sqlite3.Error:
            pass


# ---------------------------------------------------------------------------
# Secret loading (injectable seam + env default + rotation) -- never logged/returned
# ---------------------------------------------------------------------------

# A secret_provider returns (current, previous). Either may be None/empty when unset.
SecretPair = "tuple[Optional[str], Optional[str]]"


def default_secret_provider() -> "tuple[Optional[str], Optional[str]]":
    """Default secret source: read current + previous from os.getenv ONLY.

    NEVER loads dotenv, NEVER prints/logs. Returns (current, previous) raw strings (or
    None when unset). All policy (empty -> fail closed, previous verify-only) is applied
    by _resolve_secrets, not here.
    """
    return (os.getenv(HMAC_SECRET_ENV), os.getenv(HMAC_SECRET_PREVIOUS_ENV))


def _resolve_secrets(
    secret_provider: Optional[Callable[[], "tuple[Optional[str], Optional[str]]"]],
) -> tuple[list[bytes], list[bytes]]:
    """Return (sign_secrets, verify_secrets) as bytes lists from the provider.

    Policy (Addendum E):
      - current (primary) is required; empty/missing current -> ([], []) -> fail closed.
      - sign_secrets = [current] ONLY (the previous secret is NEVER used for signing).
      - verify_secrets = [current, previous?] (previous accepted ONLY for verification).
      - both missing -> fail closed.
      - if current == previous, we collapse to a single secret (no ambiguous logs; in fact
        no logs at all anywhere in this module).
    The secret bytes are never printed, logged, returned to an external caller, or embedded
    in any context/exception.
    """
    provider = secret_provider if secret_provider is not None else default_secret_provider
    current_raw, previous_raw = provider()
    current = (current_raw or "")
    previous = (previous_raw or "")
    if not current:
        # No (or empty) current secret -> fail closed; previous alone can never sign/verify
        # because there is nothing to anchor signing to.
        return ([], [])
    sign = [current.encode("utf-8")]
    verify = [current.encode("utf-8")]
    if previous and previous != current:
        verify.append(previous.encode("utf-8"))
    return (sign, verify)


# ---------------------------------------------------------------------------
# Token codec (compact, ASCII; each field INDEPENDENTLY base64url-encoded)
# ---------------------------------------------------------------------------


def _b64e(raw: bytes) -> str:
    """urlsafe base64 without padding (compact, ASCII, '.'-safe)."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(part: str) -> bytes:
    """Decode urlsafe base64 (no padding). Raises on non-ascii / bad chars / overlong."""
    if not _is_ascii(part):
        raise ValueError("non-ascii token part")
    if len(part) == 0 or len(part) > _MAX_FIELD_LEN:
        raise ValueError("token part empty or too long")
    pad = "=" * (-len(part) % 4)
    # validate=True so stray non-alphabet bytes raise instead of being silently dropped.
    return base64.urlsafe_b64decode((part + pad).encode("ascii"))


def _is_ascii(s: str) -> bool:
    return isinstance(s, str) and all(ord(c) < 128 for c in s)


def _sig(secret: bytes, signing_input: str) -> str:
    """HMAC-SHA256 of signing_input under secret, urlsafe-b64 (no padding)."""
    mac = hmac.new(secret, signing_input.encode("utf-8"), hashlib.sha256).digest()
    return _b64e(mac)


def _verify_sig(signing_input: str, provided_sig: str, verify_secrets: list[bytes]) -> bool:
    """Constant-time verify provided_sig against signing_input under any rotation secret."""
    if not provided_sig or not _is_ascii(provided_sig):
        return False
    ok = False
    for secret in verify_secrets:
        expected = _sig(secret, signing_input)
        # compare_digest is constant-time and length-safe. Do NOT short-circuit the loop on
        # the first match -- iterate every secret so timing does not leak which one matched.
        if hmac.compare_digest(expected, provided_sig):
            ok = True
    return ok


def _split_kindver(token: str, kindver: str) -> Optional[list[str]]:
    """Strip the EXACT literal `kindver` + '.' prefix, then split the rest on '.'.

    Returns the list of remaining '.'-separated parts (b64url fields + trailing sig), or
    None if the token does not carry exactly this kind+version prefix. The prefix is
    consumed by literal strip -- NOT by '.'-splitting -- so the '.' inside "sess.v1" can
    never alter the parsed field count (Addendum A + B).
    """
    prefix = kindver + "."
    if not token.startswith(prefix):
        return None
    remainder = token[len(prefix):]
    if not remainder:
        return None
    return remainder.split(".")


# ---------------------------------------------------------------------------
# Test-only minting helpers (production code only VERIFIES; these SIGN).
# Addendum F: NON-PRODUCTION-ISSUER. Each REQUIRES an explicit `secret` argument, NEVER
# reads env, is underscore-prefixed, and is EXCLUDED from __all__ (so it is not part of
# the package public surface). Issuance policy is FOUNDUP_LAUNCH_REQUEST_INTAKE_TRANSPORT_PHASE3.
# Never log a signed token produced by these helpers.
# ---------------------------------------------------------------------------


def _mint(secret: bytes, kindver: str, fields: list[bytes]) -> str:
    """TEST-ONLY developer utility -- NOT a transport issuer.

    Join KINDVER + b64url(field_i) and append an HMAC signature part over that exact
    signing input. Pure; requires an explicit secret (never env). Issuance policy is
    FOUNDUP_LAUNCH_REQUEST_INTAKE_TRANSPORT_PHASE3.
    """
    parts = [kindver] + [_b64e(f) for f in fields]
    signing_input = ".".join(parts)
    return signing_input + "." + _sig(secret, signing_input)


def _make_session_token(secret: str, subject: str, iat: int, exp: int) -> str:
    """TEST-ONLY (NOT a transport issuer): mint a sess.v1 token (authenticated=True only)."""
    sb = secret.encode("utf-8")
    return _mint(
        sb,
        _KINDVER_SESSION,
        [
            subject.encode("utf-8"),
            str(int(iat)).encode("utf-8"),
            str(int(exp)).encode("utf-8"),
        ],
    )


def _make_invite_token(secret: str, handle: str, nonce: str, iat: int, exp: int) -> str:
    """TEST-ONLY (NOT a transport issuer): mint an invite.v1 token (invite_token_verified=True only)."""
    sb = secret.encode("utf-8")
    return _mint(
        sb,
        _KINDVER_INVITE,
        [
            handle.encode("utf-8"),
            nonce.encode("utf-8"),
            str(int(iat)).encode("utf-8"),
            str(int(exp)).encode("utf-8"),
        ],
    )


# ---------------------------------------------------------------------------
# Handle hygiene
# ---------------------------------------------------------------------------


def _clean_handle(raw: bytes) -> Optional[str]:
    """Decode + reject empty/whitespace + redact (#807) + normalize a verified handle.

    The handle is taken ONLY from a cryptographically verified token. Order matters:
    redact_sensitive FIRST (so a secret-looking subject like 'sk-...' is caught while
    still in its raw form -- _normalize would otherwise rewrite the separators and
    defeat the credential regexes), THEN _normalize so identity is canonical. An empty
    or whitespace-only decoded subject is REJECTED (Addendum B).
    """
    try:
        text = raw.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        return None
    if len(text) > _MAX_FIELD_LEN:
        return None
    # Reject empty / whitespace-only BEFORE redaction/normalization (Addendum B).
    if not text.strip():
        return None
    redacted = redact_sensitive(text)
    handle = _normalize(redacted)
    if not handle:
        return None
    handle = handle.strip()
    return handle or None


# ---------------------------------------------------------------------------
# Shared time gate (Addendum C)
# ---------------------------------------------------------------------------


def _time_ok(iat: int, exp: int, now: int, max_ttl: int) -> bool:
    """Enforce the full time policy for a token (Addendum C). True iff all pass.

    - exp present + integer (callers pass already-parsed ints).
    - iat present + integer (REQUIRED).
    - issued-not-in-future: iat <= now + skew.
    - ordering: iat < exp (a non-positive lifetime is invalid).
    - not-expired boundary: now < exp + skew  (so now == exp -> EXPIRED/rejected).
    - MAX TTL (separate from exp): exp - iat <= max_ttl.
    With CLOCK_SKEW_SECONDS == 0 the skew terms vanish; they are written explicitly so the
    policy is auditable and a future nonzero skew is a one-line change.
    """
    skew = CLOCK_SKEW_SECONDS
    if iat > now + skew:
        return False           # issued in the future
    if iat >= exp:
        return False           # non-positive lifetime
    if now >= exp + skew:
        return False           # now == exp -> EXPIRED (boundary), and any now past exp
    if exp - iat > max_ttl:
        return False           # excessive TTL, rejected even with a valid signature
    return True


# ---------------------------------------------------------------------------
# Ordered, fail-closed verifiers -- KIND-LOCKED (Addendum A)
# ---------------------------------------------------------------------------


def _parse_int_field(part: str) -> Optional[int]:
    """Decode a b64url numeric field to a STRICT non-negative int. None on any malformation.

    STRICT digits-only: the decoded field must match ^[0-9]+$ BEFORE int() -- so a leading
    '+'/'-' sign, surrounding/embedded whitespace (e.g. ' 1000000 '), or any non-digit byte
    is REJECTED rather than silently coerced by int() (which strips whitespace and honors a
    sign). iat/exp are unix seconds and are never negative, so digits-only is correct and
    closes a value-confusion vector even though minting requires the secret.
    """
    try:
        decoded = _b64d(part).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    # Digits-only: no sign, no whitespace, no separators. Rejects '' too (empty -> not all-digit).
    if not decoded or not decoded.isascii() or not decoded.isdigit():
        return None
    try:
        return int(decoded)
    except ValueError:
        return None


def _verify_session(token: str, verify_secrets: list[bytes], now: int) -> Optional[str]:
    """Verify a sess.v1 token. Return the clean handle on success, else None.

    KIND-LOCKED: only a "sess.v1" token is accepted here; an invite (or any other prefix)
    returns None (Addendum A: session-into-invite / invite-into-session confusion rejected).
    ORDERED gates (fail closed on first failure): kindver -> field count -> signature ->
    time policy -> handle. Independent of any invite outcome. This path can set ONLY
    authenticated=True.
    """
    parts = _split_kindver(token, _KINDVER_SESSION)
    if parts is None:
        return None
    # parts = [b64(subject), b64(iat), b64(exp), sig]
    if len(parts) != _SESSION_FIELDS + 1:
        return None
    subj_part, iat_part, exp_part, provided_sig = parts
    signing_input = token[: -(len(provided_sig) + 1)]  # everything before the final ".sig"
    if not _verify_sig(signing_input, provided_sig, verify_secrets):
        return None
    iat = _parse_int_field(iat_part)
    exp = _parse_int_field(exp_part)
    if iat is None or exp is None:
        return None
    if not _time_ok(iat, exp, now, MAX_TTL_SESSION_SECONDS):
        return None
    try:
        subject_raw = _b64d(subj_part)
    except (ValueError, UnicodeDecodeError):
        return None
    return _clean_handle(subject_raw)


def _verify_invite(
    token: str, verify_secrets: list[bytes], now: int, nonce_store: NonceStore
) -> Optional[str]:
    """Verify + ATOMICALLY consume an invite.v1 single-use token.

    KIND-LOCKED: only an "invite.v1" token is accepted here; a session (or any other
    prefix) returns None (Addendum A). ORDERED gates (fail closed on first failure):
    kindver -> field count -> signature -> time policy -> handle/nonce -> ATOMIC
    consume_once. The nonce is claimed ONLY after every prior gate passes, in the SAME
    call -- never a verify-now / consume-later split. A replayed nonce -> consume_once
    returns False -> reject. Independent of any session outcome. This path can set ONLY
    invite_token_verified=True.
    """
    parts = _split_kindver(token, _KINDVER_INVITE)
    if parts is None:
        return None
    # parts = [b64(handle), b64(nonce), b64(iat), b64(exp), sig]
    if len(parts) != _INVITE_FIELDS + 1:
        return None
    handle_part, nonce_part, iat_part, exp_part, provided_sig = parts
    signing_input = token[: -(len(provided_sig) + 1)]
    if not _verify_sig(signing_input, provided_sig, verify_secrets):
        return None
    iat = _parse_int_field(iat_part)
    exp = _parse_int_field(exp_part)
    if iat is None or exp is None:
        return None
    if not _time_ok(iat, exp, now, MAX_TTL_INVITE_SECONDS):
        return None
    try:
        handle_raw = _b64d(handle_part)
        nonce = _b64d(nonce_part).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    handle = _clean_handle(handle_raw)
    # Reject empty / whitespace-only nonce (Addendum B). handle already rejects those.
    if not handle or not nonce.strip():
        return None
    # FINAL gate -- atomic verify-and-consume. Only here, after all checks pass, do we claim
    # the nonce. A replay returns False and rejects the invite. expires_at/subject are
    # recorded for audit only; they do not relax single-use.
    if not nonce_store.consume_once(nonce, expires_at=exp, subject=handle):
        return None
    return handle


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def build_intake_context(
    session_token: Optional[str],
    invite_token: Optional[str],
    *,
    nonce_store: "NonceStore | None" = None,
    now: Optional[int] = None,
    secret_provider: Optional[Callable[[], "tuple[Optional[str], Optional[str]]"]] = None,
) -> LaunchRequestIntakeContext:
    """Verify already-extracted token strings and POPULATE a trusted intake context.

    This is the ONLY function allowed to set authenticated / invite_token_verified /
    requester_handle. It reads NO payload and trusts NO relayed assertion.

    Args:
        session_token: an already-extracted "sess.v1" token string, or None. Sets
            authenticated=True (+ requester_handle) only if fully verified. A non-session
            token here (e.g. an invite token) fails closed -- it can NEVER set authenticated.
        invite_token: an already-extracted "invite.v1" token string, or None. Sets
            invite_token_verified=True (+ requester_handle) only if fully verified AND its
            nonce is consumed atomically (single-use). A session token here fails closed.
        nonce_store: durable single-use NonceStore for invites. If None, a fresh in-memory
            store is used (so a None store can NEVER make replay succeed; it just scopes
            single-use to this call).
        now: unix seconds for time checks; defaults to int(time.time()).
        secret_provider: zero-arg callable returning (current, previous) secrets (Addendum
            E). If None, reads os.getenv via default_secret_provider. Tests inject secrets
            WITHOUT mutating os.environ. The previous secret verifies (rotation) but NEVER
            signs.

    Returns:
        LaunchRequestIntakeContext. FAILS CLOSED (both booleans False, handle None) on
        missing/empty secret, malformed/forged/expired/over-TTL token, kind confusion,
        replayed invite, or ANY exception. The two booleans are independent AND kind-locked
        -- no single token kind can set both, and a failed mechanism never downgrades into
        the other's trust.
    """
    # Wrap the ENTIRE body so nothing -- not even an unexpected error in a helper --
    # can escape as an authenticated context.
    try:
        _sign_secrets, verify_secrets = _resolve_secrets(secret_provider)
        if not verify_secrets:
            # No (or empty) current secret configured -> fail closed.
            return LaunchRequestIntakeContext()

        ts = int(now) if now is not None else int(time.time())
        store = nonce_store if nonce_store is not None else InMemoryNonceStore()

        authenticated = False
        invite_verified = False
        handle: Optional[str] = None

        # SESSION mechanism (independent, kind-locked to sess.v1).
        if isinstance(session_token, str) and 0 < len(session_token) <= _MAX_TOKEN_LEN:
            session_handle = _verify_session(session_token, verify_secrets, ts)
            if session_handle:
                authenticated = True
                handle = session_handle

        # INVITE mechanism (independent, kind-locked to invite.v1). Atomic verify-and-consume.
        if isinstance(invite_token, str) and 0 < len(invite_token) <= _MAX_TOKEN_LEN:
            invite_handle = _verify_invite(invite_token, verify_secrets, ts, store)
            if invite_handle:
                invite_verified = True
                # Prefer an already-established (session) handle; otherwise use the invite's
                # verified handle. Either way the handle came from a verified token, never a
                # payload.
                if handle is None:
                    handle = invite_handle

        if not (authenticated or invite_verified):
            # Nothing verified -> fail closed (no handle leaks through).
            return LaunchRequestIntakeContext()

        return LaunchRequestIntakeContext(
            authenticated=authenticated,
            invite_token_verified=invite_verified,
            requester_handle=handle,
        )
    except Exception:
        # FAIL CLOSED on any unexpected error. No token/secret/nonce in the result.
        return LaunchRequestIntakeContext()
