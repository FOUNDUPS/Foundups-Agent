"""Public RedDog admission contract; Lick evidence is not authentication.

See extensions/reddog/docs/REDDOG_PUBLIC_SURFACE_ADMISSION.md.
No model, network, biometric, private-memory, or work authority lives here.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
import re
from types import MappingProxyType
import unicodedata


SURFACE_ORIGINS = MappingProxyType({
    "foundups": frozenset({"https://foundups.com"}),
    "esingularity": frozenset({"https://esingularity.ai", "https://www.esingularity.ai"}),
    "yumori": frozenset({"https://yumori.me", "https://www.yumori.me"}),
    "autopost": frozenset({"https://autopost.foundups.com"}),
})
CONSENT_VERSION = "reddog.public-guest.v1"
LICK_CONSENT_VERSION = "reddog.lick.open.v1"
ACTOR_CLAIMS = frozenset({"human", "agent", "unspecified"})
LICK_PROFILE_MODES = frozenset({"guest", "named"})
LICK_RETENTIONS = frozenset({"session"})
PUBLIC_OPERATIONS = frozenset({
    "encounter", "lick", "challenge", "turn", "status", "withdraw",
})
REQUEST_FIELDS = MappingProxyType({
    "encounter": frozenset({"consent", "consent_version", "actor_claim"}),
    "lick": frozenset({"consent", "consent_version", "actor_claim", "profile_mode",
                       "display_name", "retention"}),
    "challenge": frozenset({"challenge"}),
    "turn": frozenset({"nonce", "revision", "message"}),
    "status": frozenset(),
    "withdraw": frozenset(),
})
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class PublicAdmissionError(ValueError):
    """Fixed, public-safe rejection; never echo a token or request body."""

    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class PublicPolicy:
    """Operator may lower these ceilings; no public unlimited tier exists."""

    session_seconds: int = 600
    idle_seconds: int = 120
    session_turns: int = 10
    subject_sessions_daily: int = 3
    global_sessions_daily: int = 200
    subject_turns_daily: int = 20
    global_turns_daily: int = 1000
    concurrent_calls: int = 4
    input_chars: int = 2000
    output_tokens: int = 256
    reply_chars: int = 4000
    request_seconds: int = 15

    def __post_init__(self) -> None:
        for item in fields(self):
            value = getattr(self, item.name)
            if type(value) is not int or not 1 <= value <= item.default:
                raise PublicAdmissionError("public_policy_invalid")
        if self.idle_seconds > self.session_seconds:
            raise PublicAdmissionError("public_policy_invalid")


def checked_clock(now: int) -> int:
    if type(now) is not int or not 0 <= now <= 253402300799:
        raise PublicAdmissionError("public_clock_invalid", 503)
    return now


def checked_hex(value: str, field: str) -> str:
    if type(value) is not str or HEX64.fullmatch(value) is None:
        raise PublicAdmissionError(f"public_{field}_invalid")
    return value


def checked_surface(surface: str, origin: str) -> str:
    if type(surface) is not str or type(origin) is not str:
        raise PublicAdmissionError("public_surface_denied", 403)
    if origin not in SURFACE_ORIGINS.get(surface, ()):
        raise PublicAdmissionError("public_surface_denied", 403)
    return surface


def checked_text(value: str, limit: int) -> str:
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise PublicAdmissionError("public_text_invalid")
    if any(unicodedata.category(c) in {"Cc", "Cf", "Cs"}
           and c not in "\n\r\t" for c in value):
        raise PublicAdmissionError("public_text_invalid")
    return value.strip()


def encounter_request(body: dict) -> str:
    if type(body) is not dict or set(body) != REQUEST_FIELDS["encounter"]:
        raise PublicAdmissionError("public_encounter_shape_invalid")
    if body["consent"] is not True or body["consent_version"] != CONSENT_VERSION:
        raise PublicAdmissionError("public_consent_required", 403)
    claim = body["actor_claim"]
    if type(claim) is not str or claim not in ACTOR_CLAIMS:
        raise PublicAdmissionError("public_actor_claim_invalid")
    return claim


def lick_encounter_request(body: dict) -> tuple[str, str | None]:
    """Validate the open-source, non-biometric AutoPost Lick request."""
    if type(body) is not dict or set(body) != REQUEST_FIELDS["lick"]:
        raise PublicAdmissionError("lick_encounter_shape_invalid")
    if body["consent"] is not True or body["consent_version"] != LICK_CONSENT_VERSION:
        raise PublicAdmissionError("lick_consent_required", 403)
    if type(body["retention"]) is not str or body["retention"] not in LICK_RETENTIONS:
        raise PublicAdmissionError("lick_retention_invalid")
    claim = body["actor_claim"]
    if type(claim) is not str or claim not in ACTOR_CLAIMS:
        raise PublicAdmissionError("public_actor_claim_invalid")
    mode, display_name = body["profile_mode"], body["display_name"]
    if type(mode) is not str or mode not in LICK_PROFILE_MODES:
        raise PublicAdmissionError("lick_profile_claim_invalid")
    if mode == "guest" and display_name is None:
        return claim, None
    if mode == "named" and type(display_name) is str:
        return claim, checked_text(display_name, 80)
    raise PublicAdmissionError("lick_profile_claim_invalid")


def lick_challenge_request(body: dict) -> str:
    if type(body) is not dict or set(body) != REQUEST_FIELDS["challenge"]:
        raise PublicAdmissionError("lick_challenge_shape_invalid")
    return checked_hex(body["challenge"], "challenge")


def lick_receipt(*, encounter: str, profile_id: str, claim: str,
                 display_name: str | None, surface: str, issued: int,
                 expires: int) -> dict:
    """Non-authoritative receipt: continuity proof, never identity or access."""
    return {
        "schema_version": "reddog.lick.receipt.v1",
        "encounter_id": encounter,
        "profile": {
            "schema_version": "reddog.lick.encounter-profile.v1",
            "profile_id": profile_id,
            "actor_claim": claim,
            "display_name": display_name,
            "identity_state": "provisional",
        },
        "surface": surface,
        "consent": {"version": LICK_CONSENT_VERSION, "scope": "current_encounter",
                    "retention": "session"},
        "proofs": [{"kind": "randomized_challenge_continuity", "result": "completed"}],
        "issued_at": issued,
        "expires_at": expires,
        "identity_verified": False,
        "human_presence_proven": False,
        "biometrics_collected": False,
        "signed": False,
        "authority_granted": "none",
    }


def turn_request(body: dict, policy: PublicPolicy) -> tuple[str, int, str]:
    if type(body) is not dict or set(body) != REQUEST_FIELDS["turn"]:
        raise PublicAdmissionError("public_turn_shape_invalid")
    revision = body["revision"]
    if type(revision) is not int or not 0 <= revision <= policy.session_turns:
        raise PublicAdmissionError("public_revision_invalid")
    return (checked_hex(body["nonce"], "nonce"), revision,
            checked_text(body["message"], policy.input_chars))


def lick_verification_evidence(encounter: str, claim: str, expires: int, *,
                               consent_version: str) -> dict:
    """Unsigned, self-claim evidence for the 3V Verification input only."""
    if (type(consent_version) is not str
            or consent_version not in {CONSENT_VERSION, LICK_CONSENT_VERSION}):
        raise PublicAdmissionError("public_consent_version_invalid")
    return {
        "schema_version": "reddog.lick.public-verification.v1",
        "encounter_id": encounter,
        "stage": "verification",
        "actor_claim": claim,
        "consent_version": consent_version,
        "expires_at": expires,
        "identity_state": "provisional",
        "identity_verified": False,
        "human_presence_proven": False,
        "agent_assistance_detected": None,
        "assistance_assessment": "not_performed",
        "signed": False,
        "authority_granted": "none",
        "validation": "not_evaluated",
        "valuation": "not_evaluated",
    }
