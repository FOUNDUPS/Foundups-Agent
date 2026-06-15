#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FoundUp LaunchRequest -- public intake seam that produces a genesis envelope.

The PUBLIC front-door to WRE FoundUp creation (#806 launch flow). A typed
LaunchRequest carries ONLY user-authored proposal data; the authentication/invite
facts come from a TRUSTED server-side LaunchRequestIntakeContext, never the public
payload. Once validated, the request PRODUCES the EXISTING FoundUpGenesisEnvelope
(WSP 64 enhance-before-create -- no parallel intake envelope).

WSP 97 TRUTH BOUNDARIES:
  - Public payload can NEVER self-authenticate, carry code, request a repo, or claim
    source_authority / a gate-merge token. The intake gate depends ONLY on the
    trusted context (Addendum C).
  - The produced envelope ALWAYS has external_repo_requested=False, lifecycle in
    {IDEA, INCUBATING}, and never carries source_authority (the builder owns it).
  - This module imports no Hermes/Kanban runtime, writes no Kanban DB, spawns no
    worker, publishes no card, touches no PFmall UI or registry/manifest, and runs
    no subprocess/network/file-write. It REUSES (imports, does not copy) the #807
    kanban_plugin_contract authority-scan + redaction + path-hygiene helpers.
  - Phase 1 defines the TRUSTED CONTEXT CONTRACT; it does NOT implement real auth /
    invite verification -- that is FOUNDUP_LAUNCH_REQUEST_AUTH_CONTEXT_PROVIDER_PHASE2.

NAVIGATION:
  -> Produces: FoundUpGenesisEnvelope (.envelope) validated by .validator
  -> Reuses: modules/foundups/agent/src/kanban_plugin_contract.py (#807)
  -> Tested by: tests/test_foundup_launch_request.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

# REUSE (import, do not copy) the #807 WRE-side contract helpers.
from modules.foundups.agent.src.kanban_plugin_contract import (
    redact_sensitive,
    _scan_authority,
    _normalize,
)
from .envelope import (
    BindingState,
    FoundUpGenesisEnvelope,
    LifecycleStage,
    is_valid_foundup_id,
)
from .validator import VALID_CATEGORIES, validate_genesis_envelope

__all__ = [
    "LaunchRequest",
    "LaunchRequestIntakeContext",
    "LaunchValidationResult",
    "LaunchRequestError",
    "validate_launch_request",
    "to_genesis_envelope",
    "ALLOWED_LAUNCH_FIELDS",
    "AUTH_CONTEXT_PROVIDER_SLICE",
]

# The Phase-2 slice that implements the real server-side authn/invite verifier
# which POPULATES LaunchRequestIntakeContext. Phase 1 only defines the contract.
AUTH_CONTEXT_PROVIDER_SLICE = "FOUNDUP_LAUNCH_REQUEST_AUTH_CONTEXT_PROVIDER_PHASE2"

# The ONLY fields a public LaunchRequest payload may carry (proposal data).
ALLOWED_LAUNCH_FIELDS = frozenset({
    "proposed_name",
    "problem_statement",
    "intended_users",
    "category",
    "reference_urls",
    "requested_type",
    "requester_handle",
})

# Auth/gate/identity assertions a PUBLIC payload may NEVER carry (Addendum C).
# Matched after normalization so case/camel/separator variants are caught.
_FORBIDDEN_AUTH_FIELDS = frozenset({
    "authenticated", "is_authenticated", "invite_token_present", "invite_token_verified",
    "invite_verified", "auth", "authorization", "authorized", "role", "roles",
    "admin", "is_admin", "gate_passed", "approved", "approval", "verified",
    "permission", "permissions", "privilege", "privileged", "elevated",
})

_URL_SCHEMES_OK = ("http://", "https://")


class LaunchRequestError(ValueError):
    """Raised when an invalid LaunchRequest is mapped to a genesis envelope."""


@dataclass
class LaunchRequest:
    """Public proposal data ONLY. Carries no auth/gate/repo/source_authority field."""

    proposed_name: str
    problem_statement: str = ""
    intended_users: str = ""
    category: str = "uncategorized"
    reference_urls: List[str] = field(default_factory=list)
    requested_type: str = ""
    requester_handle: str = ""  # advisory text only; trusted handle comes from context

    def to_dict(self) -> Dict[str, Any]:
        # Redact secret VALUES from every free-text field before storage.
        return {
            "proposed_name": redact_sensitive(self.proposed_name),
            "problem_statement": redact_sensitive(self.problem_statement),
            "intended_users": redact_sensitive(self.intended_users),
            "category": self.category,
            "reference_urls": list(self.reference_urls),
            "requested_type": redact_sensitive(self.requested_type),
            "requester_handle": redact_sensitive(self.requester_handle),
        }


@dataclass
class LaunchRequestIntakeContext:
    """TRUSTED server-side intake metadata. NEVER populated from the public payload.

    Phase 1 is the contract only; the real authn/invite verifier that sets these is
    FOUNDUP_LAUNCH_REQUEST_AUTH_CONTEXT_PROVIDER_PHASE2.
    """

    authenticated: bool = False
    invite_token_verified: bool = False
    requester_handle: Optional[str] = None


@dataclass
class LaunchValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.ok = self.ok and not self.errors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scan_auth_fields(node: Any, trail: str, errors: List[str]) -> None:
    """Recursively reject any key that asserts authentication/authority (Addendum C)."""
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str) and _normalize(key) in _FORBIDDEN_AUTH_FIELDS:
                errors.append(
                    f"{trail}{key}: public payload cannot self-assert auth/authority "
                    f"(intake facts come from the trusted context, not the request)"
                )
            _scan_auth_fields(value, f"{trail}{key}.", errors)
    elif isinstance(node, (list, tuple, set)):
        for idx, item in enumerate(node):
            _scan_auth_fields(item, f"{trail}{idx}.", errors)


def _check_url_ref(field_name: str, value: Any, errors: List[str]) -> None:
    if not isinstance(value, str) or not value:
        errors.append(f"{field_name}: reference must be a non-empty URL string")
        return
    if not all(32 <= ord(c) < 127 for c in value):
        errors.append(f"{field_name}: reference must be printable ASCII")
        return
    if not value.lower().startswith(_URL_SCHEMES_OK):
        errors.append(f"{field_name}: reference must be a public http(s) URL (no local paths / file://)")
    bad = set(";|&$`><(){}\n\r\t\\\"'") & set(value)
    if bad:
        errors.append(f"{field_name}: shell/code metacharacters in reference: {sorted(bad)}")


def _slug_foundup_id(name: str) -> str:
    """Derive a WSP-104 foundup_id from a proposed name (lowercase, underscores)."""
    norm = _normalize(name)  # NFKC + camel-split + casefold + sep->underscore + collapse
    cleaned = "".join(c if (c.isalnum() or c == "_") else "_" for c in norm)
    cleaned = "_".join(p for p in cleaned.split("_") if p)
    if not cleaned:
        cleaned = "foundup"
    if not cleaned[0].isalpha():
        cleaned = "f_" + cleaned
    cleaned = cleaned[:50]
    while len(cleaned) < 3:
        cleaned += "x"
    return cleaned


# ---------------------------------------------------------------------------
# Validation + mapping
# ---------------------------------------------------------------------------

def validate_launch_request(
    payload: Union[LaunchRequest, Dict[str, Any]],
    context: LaunchRequestIntakeContext,
) -> LaunchValidationResult:
    """Validate a public LaunchRequest against a TRUSTED intake context."""
    errors: List[str] = []

    if not isinstance(context, LaunchRequestIntakeContext):
        return LaunchValidationResult(
            ok=False,
            errors=["a trusted LaunchRequestIntakeContext is required (not a payload field)"],
        )

    data = payload.to_dict() if hasattr(payload, "to_dict") else dict(payload)

    # 1. payload may carry ONLY allowed proposal fields.
    allowed_norm = {_normalize(a) for a in ALLOWED_LAUNCH_FIELDS}
    for key in data:
        if not isinstance(key, str) or _normalize(key) not in allowed_norm:
            errors.append(f"forbidden/unknown payload field: {key!r}")

    # 2. payload cannot self-assert auth/authority (Addendum C).
    _scan_auth_fields(data, "", errors)

    # 3. reuse #807 authority scan: gate-pass / merge / repo / source_authority /
    #    dao / payout / cabr / real-execution / verified -- on keys AND string values.
    _scan_authority(data, "", errors)

    # 4. reference_urls are public http(s) refs only.
    for i, url in enumerate(data.get("reference_urls", []) or []):
        _check_url_ref(f"reference_urls[{i}]", url, errors)

    # 5. minimal proposal shape.
    if not str(data.get("proposed_name", "")).strip():
        errors.append("proposed_name is required")

    # 6. INTAKE GATE (Addendum C): depends ONLY on the trusted context.
    if not (context.authenticated or context.invite_token_verified):
        errors.append(
            "intake gated: requires context.authenticated or context.invite_token_verified "
            "(public payload cannot open the gate)"
        )

    return LaunchValidationResult(ok=not errors, errors=errors)


def to_genesis_envelope(
    payload: Union[LaunchRequest, Dict[str, Any]],
    context: LaunchRequestIntakeContext,
) -> FoundUpGenesisEnvelope:
    """Map a VALIDATED LaunchRequest to a draft FoundUpGenesisEnvelope.

    Invariants: external_repo_requested=False; lifecycle in {IDEA, INCUBATING};
    requested_by comes from the trusted context (never the payload); no
    source_authority is set (the envelope has no such field; the builder owns it).
    """
    result = validate_launch_request(payload, context)
    if not result.ok:
        raise LaunchRequestError("; ".join(result.errors))

    data = payload.to_dict() if hasattr(payload, "to_dict") else dict(payload)
    # Redact at the SINK: a raw inbound dict has NOT been through LaunchRequest.to_dict(),
    # so every free-text value that flows into the envelope (name / tagline / description)
    # must be redacted here -- never trust the caller to have redacted (SENTINEL finding).
    proposed_name = redact_sensitive(str(data["proposed_name"]).strip())
    problem = redact_sensitive(str(data.get("problem_statement", "")).strip())
    category = data.get("category") if data.get("category") in VALID_CATEGORIES else "uncategorized"

    return FoundUpGenesisEnvelope(
        foundup_id=_slug_foundup_id(proposed_name),
        name=proposed_name,
        tagline=(problem[:80] if problem else proposed_name),
        description=(problem if problem else proposed_name),
        category=category,
        # requested_by is taken from the TRUSTED context, NOT the public payload.
        requested_by=(context.requester_handle or "public_intake"),
        lifecycle_stage=LifecycleStage.IDEA,
        binding_state=BindingState.UNBOUND,
        external_repo_requested=False,  # FORCED -- public input can never request a repo
        notes=redact_sensitive(str(data.get("intended_users", ""))),
    )
