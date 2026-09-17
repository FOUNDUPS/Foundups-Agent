"""Static contract for the Fukui City child protocol.

This verifies the reusable source/routing/identity guardrails only. It is not
proof that Gmail delivery, Article 6 eligibility, or a PPP/PFI proposal has
been accepted by Fukui City.
"""

from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = (
    MODULE_ROOT
    / "skillz"
    / "yumori_contact_ledger"
    / "FUKUI_CITY_CORRESPONDENCE.md"
)


def _text() -> str:
    return PROTOCOL.read_text(encoding="utf-8")


def test_city_protocol_is_child_of_existing_contact_skill() -> None:
    text = _text()
    assert "parent_skill: yumori_contact_ledger" in text
    assert "not** a second contact ledger" in text
    assert "SENT_FIRST_MOSHPIT_NOTIFY_0102" in text
    assert "Correspondence Routing" in text


def test_city_protocol_locks_canonical_principal_and_advisor_identity() -> None:
    text = _text()
    assert "UnDaoDu Michael J Trout" in text
    assert "https://jp.linkedin.com/in/openstartup" in text
    assert "generic `Michael Trout` search is insufficient" in text
    assert "Jorge Sabastian" in text
    assert "Jorge Sebastian" in text
    assert "named-entity canonicalization is now mandatory" in text


def test_city_protocol_loads_existing_sources_instead_of_researching_every_send() -> None:
    text = _text()
    for source in ("**05**", "**03**", "**03+05**", "**LANDOWNERS**", "**02**", "**04**"):
        assert source in text
    assert "Do not re-research settled project facts" in text
    assert "Current JHR/eSingularity public report" in text


def test_city_protocol_preserves_ppp_legal_truth_boundaries() -> None:
    text = _text()
    assert "PFI法第6条" in text
    assert "第6条以外" in text
    assert "SPC/SPV" in text
    assert "PSC/VFM" in text
    assert "15.8億円" in text
    assert "not YUMORI cash" in text
    assert "Listing a registered owner never means support or consent" in text


def test_city_protocol_blocks_closed_person_routes_and_private_recipient_dump() -> None:
    text = _text()
    assert "DO_NOT_ADDRESS_OR_CC" in text
    assert "PERSONAL_ROUTE_CLOSED" in text
    assert "hard denies" in text
    assert "Do not invent or guess undisclosed addresses" in text
    assert "Do not store private To/CC/BCC addresses" in text
    assert "@city.fukui" not in text
    assert "gmail.com" not in text


def test_city_protocol_requires_verification_correction_and_cross_layer_reconciliation() -> None:
    text = _text()
    assert "Verify the exact message in Gmail Sent" in text
    assert "smallest same-thread correction" in text
    assert "Gmail -> Email Log -> Contacts -> Action Queue -> YUMORI Moshpit" in text
    assert "Record agent errors/repairs separately in `0102 Moshpit`" in text


def test_city_protocol_resumes_from_receipts_after_interruptions() -> None:
    text = _text()
    assert "message-stream interruption" in text
    assert "inspect durable receipts first" in text
    assert "resume only incomplete steps" in text
    assert "Do not blindly replay large reads/writes" in text
