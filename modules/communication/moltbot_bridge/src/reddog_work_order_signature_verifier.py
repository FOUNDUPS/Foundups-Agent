#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RedDog work-order signature VERIFIER (E1: REDDOG_WORK_ORDER_SIGNATURE_VERIFIER_PHASE1).

VERIFICATION ONLY. This module does NOT sign, does NOT generate keys, does NOT store a
private key, does NOT execute anything. It validates a `RedDogDelegatedWorkAuthority`
against the ratified contract (REDDOG_PRINCIPAL_IDENTITY_AND_DELEGATION_CONTRACT_PHASE1)
and the key-isolation boundary (REDDOG_SIGNING_KEY_ISOLATION_CONTRACT_PHASE1, E0), by
generalizing the proven intake_auth_provider pattern:
    - verified SUBJECT (the signed payload), never free prompt text
    - canonical signing_input with a LITERAL domain-prefix strip (not delimiter split)
    - single-use durable nonce, consumed only AFTER signature success
    - bounded expiry via a single shared time gate with fixed leeway
    - fail-closed on any miss; reason CODES only (never expected-value / key material)

NONCE SEMANTICS (two distinct nonces; contract Section 3):
    - The IDENTITY credential (RedDogPrincipalIdentity) is a longer-lived, REUSABLE
      delegation instrument bounded by its TTL; its identity_nonce is an ISSUANCE-time
      concern and is NOT consumed here. The same identity may authorize many work orders
      within its TTL. (Consuming it per work order would wrongly lock out legitimate reuse.)
    - The WORK-AUTHORITY nonce is CONSUME-ONCE: it is durably consumed on a full ACCEPT
      (the terminal step, still AFTER signature success), so a work order cannot be replayed.
    In short: identity credential nonce != work-authority nonce; the identity is reusable
    within TTL, the work authority is single-use.

The raw asymmetric signature check is DEFERRED per contract Section 2 (no curve/library
chosen, no key generated here). It is provided by an injected `SignatureVerifier`; the
default is fail-closed. Tests inject a mock backend. `constant_time_compare` wraps
`hmac.compare_digest` for the signature/digest byte comparisons this module performs.

E0/E1 Sequence Lock: this verifier's ACCEPT is authority ONLY once E0's isolated signer
has landed; no signature is treated as authority until both E0 and E1 have landed and
passed gate review.

NAVIGATION:
    -> Verifies: RedDogDelegatedWorkAuthority (contract 1b) against its RedDogPrincipalIdentity (1a)
    -> Order: contract Section 11 (revocation-first -> two signatures -> freshness -> snapshot -> scope -> verb -> valve)
    -> Does NOT import: crypto keygen / signing libraries, subprocess, os, wallet, chain (AST-guarded by tests).
"""

from __future__ import annotations

import hmac
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Mapping, Optional, Protocol, Sequence, runtime_checkable

from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_work_order_base_ref,
)

# Domain-separation prefixes (contract Section 2, frozen).
PREFIX_IDENTITY = "reddog-identity.v1"
PREFIX_WORKAUTH = "reddog-workauth.v1"
PREFIX_RECEIPT = "reddog-receipt.v1"

# Fields EXCLUDED from any signed payload (contract Addendum A). Everything else present
# in the record is INCLUDED, so any added/removed/changed authority field breaks the
# signature (tamper-evident by construction).
_EXCLUDED_FROM_SIGNED = frozenset({"signature", "receipt_chain"})

ALLOWED_PRINCIPAL_PROVIDERS = frozenset({"github", "intake_session", "intake_invite"})


class WorkAuthorityVerificationPhase(str, Enum):
    PREFLIGHT_NON_CONSUMING = "PREFLIGHT_NON_CONSUMING"
    AUTHORITATIVE_USE = "AUTHORITATIVE_USE"


class ReasonCode:
    """Static rejection codes. NEVER carry secret / expected-signature / key material."""

    MALFORMED_PAYLOAD = "REJECT_MALFORMED_PAYLOAD"
    NON_ASCII = "REJECT_NON_ASCII_FIELD"
    MISSING_SIGNATURE = "REJECT_MISSING_SIGNATURE"
    IDENTITY_MISSING = "REJECT_IDENTITY_MISSING"
    IDENTITY_PROVIDER_INVALID = "REJECT_IDENTITY_PROVIDER_INVALID"
    REVOKED = "REJECT_REVOKED"
    KEY_EPOCH_REVOKED = "REJECT_KEY_EPOCH_REVOKED"
    IDENTITY_SIGNATURE_INVALID = "REJECT_IDENTITY_SIGNATURE_INVALID"
    WORKAUTH_SIGNATURE_INVALID = "REJECT_WORKAUTH_SIGNATURE_INVALID"
    PRINCIPAL_MISMATCH = "REJECT_PRINCIPAL_MISMATCH"
    REDDOG_ID_MISMATCH = "REJECT_REDDOG_ID_MISMATCH"
    REDDOG_KEY_MISMATCH = "REJECT_REDDOG_KEY_MISMATCH"
    EXPIRED_IDENTITY = "REJECT_EXPIRED_IDENTITY"
    EXPIRED_WORKAUTH = "REJECT_EXPIRED_WORKAUTH"
    ISSUED_IN_FUTURE = "REJECT_ISSUED_IN_FUTURE"
    NONCE_REPLAY = "REJECT_NONCE_REPLAY"
    SNAPSHOT_STALE = "REJECT_SNAPSHOT_STALE_OR_MISSING"
    SNAPSHOT_DIGEST_MISMATCH = "REJECT_SNAPSHOT_DIGEST_MISMATCH"
    SNAPSHOT_INSUFFICIENT = "REJECT_SNAPSHOT_DOES_NOT_GRANT_OP"
    REPO_OUT_OF_SCOPE = "REJECT_REPO_OUT_OF_SCOPE"
    FOUNDUP_OUT_OF_SCOPE = "REJECT_FOUNDUP_OUT_OF_SCOPE"
    FORBIDDEN_OPERATION = "REJECT_FORBIDDEN_OPERATION"
    EMPTY_EFFECTIVE_PATHS = "REJECT_EMPTY_EFFECTIVE_PATHS"
    VALVE_STATE = "REJECT_VALVE_STATE_UNSATISFIED"
    BACKEND_NOT_CONFIGURED = "REJECT_SIGNATURE_BACKEND_NOT_CONFIGURED"
    KEY_EPOCH_MISSING = "REJECT_KEY_EPOCH_MISSING"
    PATH_OUT_OF_SCOPE = "REJECT_PATH_OUT_OF_FOUNDUP_SCOPE"
    PRINCIPAL_KEY_UNTRUSTED = "REJECT_PRINCIPAL_KEY_NOT_TOKEN_VERIFIED"
    SELF_MINT_KEY_REUSE = "REJECT_PRINCIPAL_AND_REDDOG_KEY_IDENTICAL"


# Verbs that require admin (not merely write) permission on the snapshot (contract s7).
ADMIN_OPERATIONS = frozenset({"admin", "delete_repo", "manage_permissions", "force_push"})


def _is_ascii(value: Any) -> bool:
    return isinstance(value, str) and all(ord(c) < 128 for c in value)


def _assert_ascii_deep(obj: Any) -> bool:
    """Every string in the record (keys + values, nested) must be ASCII (contract s20)."""
    if isinstance(obj, str):
        return _is_ascii(obj)
    if isinstance(obj, Mapping):
        return all(_is_ascii(k) and _assert_ascii_deep(v) for k, v in obj.items())
    if isinstance(obj, (list, tuple)):
        return all(_assert_ascii_deep(v) for v in obj)
    return True  # ints / bools / None


def constant_time_compare(a: str, b: str) -> bool:
    """Constant-time equality for signature / digest strings (wraps hmac.compare_digest).

    Used wherever this module compares provided-vs-expected signature or digest bytes, so
    a mismatch position never leaks via timing (mirrors intake_auth `_verify_sig`).
    """
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def canonical_signing_input(record: Mapping[str, Any], prefix: str) -> str:
    """Contract Section 2 canonical form: <prefix-literal> + "." + canonical-json.

    Canonical JSON = UTF-8, keys sorted by code point, no whitespace, arrays in order,
    integers base-10, ASCII-only. INCLUDED = all present fields minus _EXCLUDED_FROM_SIGNED.
    The prefix is a LITERAL that the verify side prepends (not a delimiter split), so a
    "." inside a field can never change the parsed field set.
    """
    included = {k: v for k, v in record.items() if k not in _EXCLUDED_FROM_SIGNED}
    body = json.dumps(included, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return prefix + "." + body


@runtime_checkable
class SignatureVerifier(Protocol):
    """Injected raw signature check (asymmetric algorithm DEFERRED per contract Section 2).

    verify(public_key, signing_input, signature) -> bool. Implementations MUST use PUBLIC
    material only, MUST compare in constant time, and MUST NOT leak the expected value in
    any return / exception. This module never holds a private/signing secret.
    """

    def verify(self, public_key: str, signing_input: str, signature: str) -> bool: ...


class FailClosedSignatureVerifier:
    """Default backend: no algorithm configured -> reject everything (fail-closed)."""

    def verify(self, public_key: str, signing_input: str, signature: str) -> bool:
        return False


@runtime_checkable
class NonceStore(Protocol):
    def consume(self, nonce: str) -> bool:
        """Atomically record `nonce`. Return True if newly consumed, False if already present (replay)."""
        ...


class InMemoryNonceStore:
    """Single-process durable-consume stand-in (contract Section 3). SQLite-backed reuse
    is a later slice; this suffices for the verifier's atomic check-and-insert semantics."""

    def __init__(self) -> None:
        self._seen: set = set()

    def consume(self, nonce: str) -> bool:
        if not isinstance(nonce, str) or not nonce or nonce in self._seen:
            return False
        self._seen.add(nonce)
        return True



@runtime_checkable
class PermissionSnapshotResolver(Protocol):
    def resolve(self, digest: str) -> Optional["PermissionSnapshot"]: ...


@runtime_checkable
class RevocationOracle(Protocol):
    def is_revoked(
        self, *, reddog_id: str, fingerprint: str, principal_id: str, key_epoch: str
    ) -> bool: ...


@dataclass
class PermissionSnapshot:
    """Minimal fresh-permission snapshot (contract Section 7 / audit 2d)."""

    evidence_digest: str
    expires_at: int
    can_write: bool = False
    can_admin: bool = False
    repo_full_name: str = ""

    def is_fresh(self, now: int, leeway_s: int) -> bool:
        return now <= int(self.expires_at) + int(leeway_s)

    def grants(self, operation: str, repo_full_name: str) -> bool:
        if self.repo_full_name and self.repo_full_name != repo_full_name:
            return False
        # Verb-tier: admin operations require can_admin; others require write (contract s7).
        if str(operation) in ADMIN_OPERATIONS:
            return bool(self.can_admin)
        return bool(self.can_write or self.can_admin)


@runtime_checkable
class PrincipalKeyResolver(Protocol):
    def resolve(self, principal_id: str, principal_provider: str) -> Optional[str]:
        """Return the token-verified principal PUBLIC key on record for this subject, or None.

        This is the anti-self-mint trust anchor (contract Section 5 issuance basis): the
        principal_public_key in an untrusted identity record is accepted ONLY if it equals
        the key this resolver returns for a token-verified principal_id. Default is
        fail-closed (None -> reject)."""
        ...


class FailClosedPrincipalKeyResolver:
    """Default: no principal is token-verified -> reject every identity (fail-closed)."""

    def resolve(self, principal_id: str, principal_provider: str) -> Optional[str]:
        return None


@dataclass
class VerificationResult:
    accepted: bool
    reason_codes: List[str] = field(default_factory=list)
    work_order_id: Optional[str] = None

    def __bool__(self) -> bool:
        # A bare `if result:` must mean "authorized", never "an object exists" (fail-safe).
        return bool(self.accepted)

    def to_dict(self) -> dict:
        return {"accepted": self.accepted, "reason_codes": list(self.reason_codes),
                "work_order_id": self.work_order_id}


class WorkOrderRejected(Exception):
    """Raised by require_authorized when a work authority is not ACCEPTED. Carries only
    static reason codes (never secret / expected-signature material)."""

    def __init__(self, reason_codes: Sequence[str]) -> None:
        self.reason_codes = tuple(reason_codes)
        super().__init__("work order rejected: " + ",".join(self.reason_codes))


def require_authorized(result: VerificationResult) -> None:
    """Enforcement helper the CALLER MUST use: fail-closed unless result.accepted is True.
    A caller that ignores this and reads reason_codes truthiness (a non-empty list) would
    invert the decision; use this instead."""
    if not result.accepted:
        raise WorkOrderRejected(result.reason_codes)


def _path_within_foundup(path: str, foundup_id: str) -> bool:
    """True iff `path` is a safe, in-scope path under modules/foundups/<foundup_id>/.

    Rejects absolute, backslash, drive-colon, NUL, device-prefix, and any '..'/'.' or
    empty (Win32-normalized) segment -- the same class the live scaffold writer hardened.
    """
    if not isinstance(path, str) or not path or not _is_ascii(path):
        return False
    if "\x00" in path or "\\" in path or ":" in path or path.startswith("/"):
        return False
    for dp in ("//?/", "//./"):
        if path.startswith(dp):
            return False
    norm = path.replace("\\", "/")
    ceiling = f"modules/foundups/{foundup_id}/"
    if not norm.startswith(ceiling):
        return False
    for seg in norm.split("/"):
        if seg.strip(" \t") == ".." or seg.strip(" .\t") == "":
            return False
    return True


_REQUIRED_WORKAUTH_FIELDS = (
    "work_order_id", "work_order_digest", "base_ref", "principal_id", "reddog_id", "repo_full_name", "foundup_id",
    "allowed_paths", "denied_paths", "requested_operation", "permission_snapshot_digest",
    "wsp15_allocation_receipt_id", "wsp15_allocation_digest", "wsp15_priority",
    "wsp15_mps_total", "wsp15_reasoning_tier",
    "nonce", "issued_at", "expires_at", "valve_state_required", "key_epoch", "signature",
)
_REQUIRED_IDENTITY_FIELDS = (
    "principal_id", "principal_provider", "principal_public_key", "reddog_id",
    "reddog_public_key", "repo_scope", "foundup_scope", "issued_at", "expires_at", "signature",
)


def verify_delegated_work_authority(
    *,
    work_authority: Mapping[str, Any],
    identity: Mapping[str, Any],
    signature_verifier: SignatureVerifier,
    principal_key_resolver: PrincipalKeyResolver,
    nonce_store: NonceStore,
    snapshot_resolver: PermissionSnapshotResolver,
    revocation_oracle: RevocationOracle,
    now: int,
    required_valve_state: str,
    forbidden_operations: Sequence[str] = (),
    revoked_key_epochs: Sequence[str] = (),
    leeway_s: int = 60,
    verification_phase: WorkAuthorityVerificationPhase = (
        WorkAuthorityVerificationPhase.AUTHORITATIVE_USE
    ),
) -> VerificationResult:
    """Verify a signed RedDogDelegatedWorkAuthority. ACCEPT / REJECT with reason codes.

    Order = contract Section 11 (revocation-first). No execution side effect; the only
    state change is the atomic nonce consume, performed AFTER signature success.
    """
    wo_id = work_authority.get("work_order_id") if isinstance(work_authority, Mapping) else None
    result = VerificationResult(accepted=False, work_order_id=wo_id if isinstance(wo_id, str) else None)

    def reject(code: str) -> VerificationResult:
        result.accepted = False
        result.reason_codes.append(code)
        return result

    # ---- Structural + ASCII (contract s2/s20) -------------------------------
    if not isinstance(work_authority, Mapping) or not isinstance(identity, Mapping):
        return reject(ReasonCode.MALFORMED_PAYLOAD)
    for f in _REQUIRED_WORKAUTH_FIELDS:
        if work_authority.get(f) is None:
            return reject(ReasonCode.MISSING_SIGNATURE if f == "signature" else ReasonCode.MALFORMED_PAYLOAD)
    for f in _REQUIRED_IDENTITY_FIELDS:
        if identity.get(f) is None:
            return reject(ReasonCode.IDENTITY_MISSING)
    if not (_assert_ascii_deep(work_authority) and _assert_ascii_deep(identity)):
        return reject(ReasonCode.NON_ASCII)
    if str(identity.get("principal_provider")) not in ALLOWED_PRINCIPAL_PROVIDERS:
        return reject(ReasonCode.IDENTITY_PROVIDER_INVALID)
    try:
        canonical_work_order_base_ref(work_authority)
    except ValueError:
        return reject(ReasonCode.MALFORMED_PAYLOAD)
    work_order_digest = str(work_authority.get("work_order_digest") or "")
    if not (
        work_order_digest.startswith("sha256:")
        and len(work_order_digest) == 71
        and all(char in "0123456789abcdef" for char in work_order_digest[7:])
    ):
        return reject(ReasonCode.MALFORMED_PAYLOAD)
    if (
        not str(work_authority.get("wsp15_allocation_receipt_id") or "").startswith("sha256:")
        or not str(work_authority.get("wsp15_allocation_digest") or "").startswith("sha256:")
        or str(work_authority.get("wsp15_priority") or "") not in {"P0", "P1", "P2", "P3", "P4"}
        or type(work_authority.get("wsp15_mps_total")) is not int
        or str(work_authority.get("wsp15_reasoning_tier") or "") not in {"REGULAR", "HIGH", "ULTRA"}
    ):
        return reject(ReasonCode.MALFORMED_PAYLOAD)
    runtime_binding_id = str(work_authority.get("model_runtime_binding_receipt_id") or "")
    runtime_binding_digest = str(work_authority.get("model_runtime_binding_digest") or "")
    if (runtime_binding_id or runtime_binding_digest) and not (
        runtime_binding_id.startswith("reddog_model_runtime_binding:")
        and runtime_binding_digest.startswith("sha256:")
    ):
        return reject(ReasonCode.MALFORMED_PAYLOAD)

    principal_id = str(identity["principal_id"])
    reddog_id = str(identity["reddog_id"])
    reddog_public_key = str(identity["reddog_public_key"])
    principal_public_key = str(identity["principal_public_key"])
    fingerprint = str(identity.get("reddog_key_fingerprint", ""))
    key_epoch = str(work_authority.get("key_epoch", ""))
    if not key_epoch:
        return reject(ReasonCode.KEY_EPOCH_MISSING)

    # ---- 1. Revocation FIRST (contract s9/s11): wins over a valid signature --
    try:
        if revocation_oracle.is_revoked(
            reddog_id=reddog_id, fingerprint=fingerprint,
            principal_id=principal_id, key_epoch=key_epoch,
        ):
            return reject(ReasonCode.REVOKED)
    except Exception:
        return reject(ReasonCode.REVOKED)  # fail-closed
    if key_epoch in set(str(e) for e in revoked_key_epochs):
        return reject(ReasonCode.KEY_EPOCH_REVOKED)

    # ---- 2 (pre): anti-self-mint trust anchors -------------------------------
    # The principal key and the RedDog key MUST differ: the identity is signed by the
    # PRINCIPAL and the work order by the RedDog; one key signing both is a self-grant.
    if constant_time_compare(principal_public_key, reddog_public_key):
        return reject(ReasonCode.SELF_MINT_KEY_REUSE)
    # principal_public_key is trusted ONLY if it is the token-verified key on record for
    # this principal_id (contract Section 5 issuance basis). Fail-closed if unknown.
    try:
        trusted_principal_key = principal_key_resolver.resolve(
            principal_id, str(identity["principal_provider"])
        )
    except Exception:
        trusted_principal_key = None
    if not trusted_principal_key or not constant_time_compare(str(trusted_principal_key), principal_public_key):
        return reject(ReasonCode.PRINCIPAL_KEY_UNTRUSTED)

    # ---- 2a. Parent identity signature: PRINCIPAL-signed (anti-self-grant) ---
    try:
        id_input = canonical_signing_input(identity, PREFIX_IDENTITY)
        # strict `is True`: a lax backend returning a truthy non-bool must NOT accept.
        id_ok = signature_verifier.verify(principal_public_key, id_input, str(identity["signature"])) is True
    except Exception:
        id_ok = False
    if not id_ok:
        return reject(ReasonCode.IDENTITY_SIGNATURE_INVALID)

    # ---- 2b. Binding: work order must match its parent identity --------------
    if not constant_time_compare(str(work_authority["principal_id"]), principal_id):
        return reject(ReasonCode.PRINCIPAL_MISMATCH)
    if not constant_time_compare(str(work_authority["reddog_id"]), reddog_id):
        return reject(ReasonCode.REDDOG_ID_MISMATCH)
    wa_signer_key = work_authority.get("signer_public_key")
    if wa_signer_key is not None and not constant_time_compare(str(wa_signer_key), reddog_public_key):
        return reject(ReasonCode.REDDOG_KEY_MISMATCH)

    # ---- 2c. Work-order signature: by the delegated reddog key ---------------
    try:
        wa_input = canonical_signing_input(work_authority, PREFIX_WORKAUTH)
        wa_ok = signature_verifier.verify(reddog_public_key, wa_input, str(work_authority["signature"])) is True
    except Exception:
        wa_ok = False
    if not wa_ok:
        # covers payload tampering, non-canonical/field-reorder, changed allowed_paths /
        # foundup_id / permission_snapshot_digest / valve_state_required, wrong signer key.
        return reject(ReasonCode.WORKAUTH_SIGNATURE_INVALID)

    # ---- 3. Freshness (single shared time gate, contract s3) -----------------
    try:
        id_iat, id_exp = int(identity["issued_at"]), int(identity["expires_at"])
        wa_iat, wa_exp = int(work_authority["issued_at"]), int(work_authority["expires_at"])
    except (TypeError, ValueError):
        return reject(ReasonCode.MALFORMED_PAYLOAD)
    if now + leeway_s < id_iat or now + leeway_s < wa_iat:
        return reject(ReasonCode.ISSUED_IN_FUTURE)
    if now > id_exp + leeway_s:
        return reject(ReasonCode.EXPIRED_IDENTITY)
    if now > wa_exp + leeway_s:
        return reject(ReasonCode.EXPIRED_WORKAUTH)

    # ---- 5. Permission snapshot: fresh + digest-bound + grants verb (s7) -----
    #        (Nonce consume is DEFERRED to the terminal step 9 so a transient reject here
    #         cannot permanently burn a legitimate order's single-use nonce.)
    snap_digest = str(work_authority["permission_snapshot_digest"])
    try:
        snap = snapshot_resolver.resolve(snap_digest)
    except Exception:
        snap = None
    try:
        fresh = snap is not None and snap.is_fresh(now, leeway_s)
    except Exception:
        fresh = False
    if not fresh:
        return reject(ReasonCode.SNAPSHOT_STALE)
    if not constant_time_compare(str(snap.evidence_digest), snap_digest):
        return reject(ReasonCode.SNAPSHOT_DIGEST_MISMATCH)
    try:
        granted = snap.grants(str(work_authority["requested_operation"]), str(work_authority["repo_full_name"]))
    except Exception:
        granted = False
    if not granted:
        return reject(ReasonCode.SNAPSHOT_INSUFFICIENT)

    # ---- 6. Scope: repo + foundup within the identity ceiling (s5/s6) --------
    if str(work_authority["repo_full_name"]) not in set(map(str, identity["repo_scope"])):
        return reject(ReasonCode.REPO_OUT_OF_SCOPE)
    if str(work_authority["foundup_id"]) not in set(map(str, identity["foundup_scope"])):
        return reject(ReasonCode.FOUNDUP_OUT_OF_SCOPE)

    # ---- 7. Verb + path: forbidden ops; deny wins; effective set IN-SCOPE -----
    try:
        allowed = set(map(str, work_authority["allowed_paths"]))
        denied = set(map(str, work_authority["denied_paths"]))
    except Exception:
        return reject(ReasonCode.MALFORMED_PAYLOAD)
    if str(work_authority["requested_operation"]) in set(map(str, forbidden_operations)):
        return reject(ReasonCode.FORBIDDEN_OPERATION)
    effective = allowed - denied
    if not effective:
        return reject(ReasonCode.EMPTY_EFFECTIVE_PATHS)
    # Bind every effective path to the FoundUp's canonical ceiling: an in-scope,
    # validly-signed order still cannot target .github/workflows, secrets, or ../../.env.
    foundup_id = str(work_authority["foundup_id"])
    if not all(_path_within_foundup(p, foundup_id) for p in effective):
        return reject(ReasonCode.PATH_OUT_OF_SCOPE)

    # ---- 8. Valve: required state bound into the signed payload (s2/s7) ------
    if not constant_time_compare(str(work_authority["valve_state_required"]), str(required_valve_state)):
        return reject(ReasonCode.VALVE_STATE)

    # ---- 9. Nonce consume LAST. A preflight caller may explicitly defer this
    #         terminal mutation; the authoritative use-time caller must consume it.
    if verification_phase is WorkAuthorityVerificationPhase.PREFLIGHT_NON_CONSUMING:
        result.accepted = True
        return result
    if verification_phase is not WorkAuthorityVerificationPhase.AUTHORITATIVE_USE:
        return reject(ReasonCode.MALFORMED_PAYLOAD)
    try:
        consumed = nonce_store.consume(str(work_authority["nonce"]))
    except Exception:
        consumed = False
    if not consumed:
        return reject(ReasonCode.NONCE_REPLAY)

    result.accepted = True
    return result
