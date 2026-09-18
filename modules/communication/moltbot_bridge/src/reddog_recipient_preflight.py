"""Fail-closed recipient authorization for outbound correspondence.

This module is provider-agnostic. It does not send mail. It verifies that the
final recipient transaction matches the freshest authoritative routing
evidence and produces a receipt that a sender can persist and compare against
provider read-back.
"""

from __future__ import annotations

from dataclasses import dataclass
from email.utils import parseaddr
from enum import Enum, IntEnum
from typing import Iterable, Mapping, Sequence


class EvidenceLevel(IntEnum):
    PUBLIC_DIRECTORY = 10
    PRIOR_THREAD = 20
    CONTACTS = 30
    ROUTING_POLICY = 40
    EXPLICIT_PROVIDER = 50


class RoutePolicy(str, Enum):
    ALLOW = "ALLOW"
    DO_NOT_ADDRESS_OR_CC = "DO_NOT_ADDRESS_OR_CC"
    PERSONAL_ROUTE_CLOSED = "PERSONAL_ROUTE_CLOSED"
    BCC_ONLY = "BCC_ONLY"
    ORGANIZATION_ONLY = "ORGANIZATION_ONLY"


class RecipientRole(str, Enum):
    TO = "TO"
    CC = "CC"
    BCC = "BCC"


class PreflightDecision(str, Enum):
    SEND = "SEND"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class RouteEvidence:
    identity_id: str
    address: str
    source: str
    level: EvidenceLevel
    policy: RoutePolicy | None = None
    entity_kind: str = "organization"
    current: bool = True


@dataclass(frozen=True)
class ProposedRecipient:
    identity_id: str
    role: RecipientRole
    address: str


@dataclass(frozen=True)
class RecipientCheck:
    identity_id: str
    role: RecipientRole
    proposed_address: str
    authoritative_address: str | None
    authoritative_source: str | None
    policy: RoutePolicy
    exact_match: bool
    duplicate_coverage: bool
    allowed: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PreflightReceipt:
    decision: PreflightDecision
    checks: tuple[RecipientCheck, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ReadbackVerification:
    ok: bool
    reasons: tuple[str, ...]


def normalize_address(value: str) -> str:
    """Normalize display-name syntax and case without changing address characters."""
    _, parsed = parseaddr(value.strip())
    address = parsed or value.strip()
    return address.strip().lower()


def _resolve_address(
    identity_id: str,
    evidence: Sequence[RouteEvidence],
) -> tuple[RouteEvidence | None, tuple[str, ...]]:
    candidates = [e for e in evidence if e.identity_id == identity_id and e.current]
    if not candidates:
        return None, ("UNKNOWN_ROUTE",)

    top_level = max(e.level for e in candidates)
    top = [e for e in candidates if e.level == top_level]
    addresses = {normalize_address(e.address) for e in top}
    if len(addresses) != 1:
        return None, ("CONFLICTING_AUTHORITATIVE_ADDRESSES",)
    return top[0], ()


def _resolve_policy(
    identity_id: str,
    evidence: Sequence[RouteEvidence],
) -> tuple[RoutePolicy, tuple[str, ...]]:
    candidates = [
        e
        for e in evidence
        if e.identity_id == identity_id and e.current and e.policy is not None
    ]
    if not candidates:
        return RoutePolicy.ALLOW, ()

    top_level = max(e.level for e in candidates)
    top = [e for e in candidates if e.level == top_level]
    policies = {e.policy for e in top}
    if len(policies) != 1:
        return RoutePolicy.ALLOW, ("CONFLICTING_AUTHORITATIVE_POLICIES",)
    return next(iter(policies)), ()


def preflight_recipients(
    proposed: Sequence[ProposedRecipient],
    evidence: Sequence[RouteEvidence],
    *,
    already_sent_addresses: Iterable[str] = (),
    allow_duplicate_coverage: bool = False,
) -> PreflightReceipt:
    """Validate a concrete To/CC/BCC transaction.

    Address authority and consent/routing policy are resolved independently.
    This prevents a newer address observation from silently reopening an older
    binding route closure. Any unknown, conflicting, closed, near-match, or
    duplicate recipient fails the entire transaction closed.
    """
    sent = {normalize_address(x) for x in already_sent_addresses}
    checks: list[RecipientCheck] = []
    global_reasons: list[str] = []

    seen: set[tuple[RecipientRole, str]] = set()
    for recipient in proposed:
        proposed_address = normalize_address(recipient.address)
        key = (recipient.role, proposed_address)
        reasons: list[str] = []

        if key in seen:
            reasons.append("DUPLICATE_RECIPIENT_IN_TRANSACTION")
        seen.add(key)

        route, route_reasons = _resolve_address(recipient.identity_id, evidence)
        policy, policy_reasons = _resolve_policy(recipient.identity_id, evidence)
        reasons.extend(route_reasons)
        reasons.extend(policy_reasons)

        authoritative_address = None
        source = None
        exact_match = False

        if route is not None:
            authoritative_address = normalize_address(route.address)
            source = route.source
            exact_match = proposed_address == authoritative_address
            if not exact_match:
                reasons.append("EXACT_ADDRESS_MISMATCH")

            if policy is RoutePolicy.ORGANIZATION_ONLY and route.entity_kind != "organization":
                reasons.append("ROLE_POLICY_VIOLATION_ORGANIZATION_ONLY")

        if policy in {
            RoutePolicy.DO_NOT_ADDRESS_OR_CC,
            RoutePolicy.PERSONAL_ROUTE_CLOSED,
        }:
            reasons.append(policy.value)
        elif policy is RoutePolicy.BCC_ONLY and recipient.role is not RecipientRole.BCC:
            reasons.append("ROLE_POLICY_VIOLATION_BCC_ONLY")

        duplicate_coverage = proposed_address in sent
        if duplicate_coverage and not allow_duplicate_coverage:
            reasons.append("DUPLICATE_SENT_COVERAGE")

        allowed = not reasons
        checks.append(
            RecipientCheck(
                identity_id=recipient.identity_id,
                role=recipient.role,
                proposed_address=proposed_address,
                authoritative_address=authoritative_address,
                authoritative_source=source,
                policy=policy,
                exact_match=exact_match,
                duplicate_coverage=duplicate_coverage,
                allowed=allowed,
                reasons=tuple(reasons),
            )
        )
        global_reasons.extend(
            f"{recipient.identity_id}:{reason}" for reason in reasons
        )

    if not proposed:
        global_reasons.append("EMPTY_RECIPIENT_SET")

    decision = PreflightDecision.SEND if not global_reasons else PreflightDecision.BLOCK
    return PreflightReceipt(
        decision=decision,
        checks=tuple(checks),
        reasons=tuple(global_reasons),
    )


def verify_sent_readback(
    receipt: PreflightReceipt,
    actual: Mapping[RecipientRole, Sequence[str]],
) -> ReadbackVerification:
    """Compare provider read-back with the exact approved transaction."""
    if receipt.decision is not PreflightDecision.SEND:
        return ReadbackVerification(False, ("PREFLIGHT_NOT_SENDABLE",))

    expected = {(check.role, check.proposed_address) for check in receipt.checks}
    observed = {
        (role, normalize_address(address))
        for role, addresses in actual.items()
        for address in addresses
    }

    reasons: list[str] = []
    if expected - observed:
        reasons.append("SENT_READBACK_MISSING_RECIPIENT")
    if observed - expected:
        reasons.append("SENT_READBACK_EXTRA_RECIPIENT")
    return ReadbackVerification(ok=not reasons, reasons=tuple(reasons))
