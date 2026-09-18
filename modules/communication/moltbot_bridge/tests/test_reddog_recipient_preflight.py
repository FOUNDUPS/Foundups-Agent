from modules.communication.moltbot_bridge.src.reddog_recipient_preflight import (
    EvidenceLevel,
    PreflightDecision,
    ProposedRecipient,
    RecipientRole,
    RouteEvidence,
    RoutePolicy,
    normalize_address,
    preflight_recipients,
    verify_sent_readback,
)


def ev(identity, address, level=EvidenceLevel.CONTACTS, **kw):
    return RouteEvidence(identity, address, "test", level, **kw)


def test_newer_explicit_provider_route_overrides_stale_contacts():
    receipt = preflight_recipients(
        [ProposedRecipient("org-1", RecipientRole.TO, "new-route@example.org")],
        [
            ev("org-1", "old-route@example.org", EvidenceLevel.CONTACTS),
            ev("org-1", "new-route@example.org", EvidenceLevel.EXPLICIT_PROVIDER),
        ],
    )
    assert receipt.decision is PreflightDecision.SEND
    assert receipt.checks[0].authoritative_address == "new-route@example.org"


def test_near_match_hyphen_difference_blocks():
    receipt = preflight_recipients(
        [ProposedRecipient("org-1", RecipientRole.TO, "team-a@example.org")],
        [ev("org-1", "teama@example.org", EvidenceLevel.EXPLICIT_PROVIDER)],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert "org-1:EXACT_ADDRESS_MISMATCH" in receipt.reasons


def test_personal_route_closed_blocks_even_exact_address():
    receipt = preflight_recipients(
        [ProposedRecipient("person-1", RecipientRole.TO, "person@example.org")],
        [
            ev(
                "person-1",
                "person@example.org",
                EvidenceLevel.ROUTING_POLICY,
                policy=RoutePolicy.PERSONAL_ROUTE_CLOSED,
                entity_kind="person",
            )
        ],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert "person-1:PERSONAL_ROUTE_CLOSED" in receipt.reasons


def test_bcc_only_policy_blocks_cc():
    receipt = preflight_recipients(
        [ProposedRecipient("observer-1", RecipientRole.CC, "observer@example.org")],
        [
            ev(
                "observer-1",
                "observer@example.org",
                EvidenceLevel.ROUTING_POLICY,
                policy=RoutePolicy.BCC_ONLY,
            )
        ],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert "observer-1:ROLE_POLICY_VIOLATION_BCC_ONLY" in receipt.reasons


def test_newer_address_evidence_does_not_silently_reopen_closed_route():
    receipt = preflight_recipients(
        [ProposedRecipient("person-1", RecipientRole.TO, "person@example.org")],
        [
            ev(
                "person-1",
                "person@example.org",
                EvidenceLevel.ROUTING_POLICY,
                policy=RoutePolicy.PERSONAL_ROUTE_CLOSED,
                entity_kind="person",
            ),
            ev(
                "person-1",
                "person@example.org",
                EvidenceLevel.EXPLICIT_PROVIDER,
                entity_kind="person",
            ),
        ],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert "person-1:PERSONAL_ROUTE_CLOSED" in receipt.reasons


def test_duplicate_sent_coverage_blocks_by_default():
    receipt = preflight_recipients(
        [ProposedRecipient("org-1", RecipientRole.TO, "route@example.org")],
        [ev("org-1", "route@example.org")],
        already_sent_addresses=["route@example.org"],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert "org-1:DUPLICATE_SENT_COVERAGE" in receipt.reasons


def test_conflicting_top_precedence_routes_block():
    receipt = preflight_recipients(
        [ProposedRecipient("org-1", RecipientRole.TO, "a@example.org")],
        [
            ev("org-1", "a@example.org", EvidenceLevel.EXPLICIT_PROVIDER),
            ev("org-1", "b@example.org", EvidenceLevel.EXPLICIT_PROVIDER),
        ],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert "org-1:CONFLICTING_AUTHORITATIVE_ADDRESSES" in receipt.reasons


def test_unknown_route_blocks():
    receipt = preflight_recipients(
        [ProposedRecipient("missing", RecipientRole.TO, "x@example.org")],
        [],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert "missing:UNKNOWN_ROUTE" in receipt.reasons


def test_display_name_and_case_normalize_without_character_rewrite():
    assert normalize_address("Example Person <User.Name+tag@Example.Org>") == (
        "user.name+tag@example.org"
    )


def test_mixed_transaction_blocks_if_one_recipient_fails():
    receipt = preflight_recipients(
        [
            ProposedRecipient("good", RecipientRole.TO, "good@example.org"),
            ProposedRecipient("bad", RecipientRole.CC, "wrong@example.org"),
        ],
        [
            ev("good", "good@example.org"),
            ev("bad", "right@example.org"),
        ],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert receipt.checks[0].allowed is True
    assert receipt.checks[1].allowed is False


def test_sent_readback_matches_approved_transaction():
    receipt = preflight_recipients(
        [
            ProposedRecipient("a", RecipientRole.TO, "a@example.org"),
            ProposedRecipient("b", RecipientRole.BCC, "B Person <b@example.org>"),
        ],
        [ev("a", "a@example.org"), ev("b", "b@example.org")],
    )
    result = verify_sent_readback(
        receipt,
        {
            RecipientRole.TO: ["A <A@example.org>"],
            RecipientRole.CC: [],
            RecipientRole.BCC: ["b@example.org"],
        },
    )
    assert result.ok is True


def test_sent_readback_detects_extra_or_missing_recipient():
    receipt = preflight_recipients(
        [ProposedRecipient("a", RecipientRole.TO, "a@example.org")],
        [ev("a", "a@example.org")],
    )
    result = verify_sent_readback(
        receipt,
        {
            RecipientRole.TO: ["other@example.org"],
            RecipientRole.CC: [],
            RecipientRole.BCC: [],
        },
    )
    assert result.ok is False
    assert "SENT_READBACK_MISSING_RECIPIENT" in result.reasons
    assert "SENT_READBACK_EXTRA_RECIPIENT" in result.reasons
