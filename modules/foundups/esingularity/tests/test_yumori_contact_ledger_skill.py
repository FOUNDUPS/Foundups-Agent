"""Static skill/registry contracts, not proof of a deployed media executor."""

import json
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
MODULES_ROOT = Path(__file__).resolve().parents[3]
SKILL_PATH = MODULE_ROOT / "skillz" / "yumori_contact_ledger" / "SKILLz.md"
CONTEXT_PATH = MODULE_ROOT / "docs" / "YUMORI_CONTACT_LEDGER_CONTEXT.md"
ROLE_PATH = SKILL_PATH.parent / "MEDIA_DAE_ROLES.json"
SKILL_REGISTRY_PATH = (
    MODULES_ROOT / "infrastructure" / "wre_core" / "skillz" / "skills_registry_v2.json"
)


def test_yumori_contact_skill_is_registered_as_prototype() -> None:
    registry = json.loads(SKILL_REGISTRY_PATH.read_text(encoding="utf-8"))
    entry = registry["skills"]["yumori_contact_ledger"]
    assert registry["total_skills"] == len(registry["skills"])
    assert entry["location"] == "modules/foundups/esingularity/skillz/yumori_contact_ledger"
    assert entry["version"] == "0.5.0"
    assert entry["promotion_state"] == "prototype"
    assert entry["intent_type"] == "MAINTENANCE"
    assert "WSP 95" in entry["wsp_chain"]
    assert "WSP 97" in entry["wsp_chain"]


def test_skill_preserves_gmail_lineage_and_external_truth_boundary() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    assert "message_id" in skill
    assert "thread_id" in skill
    assert "Do not add a custom campaign tracking signature" in skill
    assert "YUMORI.me Contacts" in skill
    assert "YUMORI.me Moshpit" in skill
    assert "YUMORI.me Contacts Pics" in skill
    assert "NEEDS_VERIFICATION" in skill
    assert "The Skillz grants no Gmail or Drive mutation authority by itself" in skill
    assert "GMAIL_RECEIPT_REQUIRED" in skill
    assert "Asia/Tokyo" in skill
    assert "Materiality controls summary prominence, not receipt retention" in skill


def test_government_correspondence_uses_live_routing_without_repo_pii() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    assert "Government correspondence operating contract" in skill
    assert "Repo first for project truth" in skill
    assert "Read correspondence before drafting" in skill
    assert "Card fallback" in skill
    assert "Japanese-first government drafting" in skill
    assert "Correspondence Routing" in skill
    assert "DEFAULT_BCC" in skill
    assert "No private addresses in Git" in skill
    assert "Do not guess undisclosed internal addresses" in skill
    assert "Post-send reconciliation" in skill


def test_context_contract_names_the_live_sources_without_private_dump() -> None:
    context = CONTEXT_PATH.read_text(encoding="utf-8")
    assert "`YUMORI.me Contacts`" in context
    assert "`Email Log` tab" in context
    assert "`YUMORI.me Moshpit`" in context
    assert "`YUMORI.me Contacts Pics`" in context
    assert "Do not hard-code Drive file IDs or private contact dumps" in context
    assert "Gmail `Message ID`" in context
    assert "Gmail `thread_id`" in context


def test_media_profiles_define_role_bound_deliverables() -> None:
    packet = json.loads(ROLE_PATH.read_text(encoding="utf-8"))
    roles = packet["roles"]
    assert set(roles) == {
        "LOCAL_MEDIA_DAE", "REGIONAL_MEDIA_DAE", "NATIONAL_MEDIA_DAE",
        "PRESS_WRITER", "PRESS_EDITOR", "RELEASE_MANAGER", "CORRESPONDENCE_CURATOR",
    }
    for profile in roles.values():
        for field in ("trigger", "objective", "required_sources", "output", "acceptance", "handoff"):
            assert profile[field], field
        assert profile["handoff"] in set(roles) | {"RECONCILED"}


def test_media_profiles_separate_editorial_hooks() -> None:
    packet = json.loads(ROLE_PATH.read_text(encoding="utf-8"))
    profiles = [packet["roles"][name] for name in (
        "LOCAL_MEDIA_DAE", "REGIONAL_MEDIA_DAE", "NATIONAL_MEDIA_DAE"
    )]
    assert len({p["hook"] for p in profiles}) == 3
    assert len({p["editorial_scope"] for p in profiles}) == 3
    assert "onsen" in profiles[0]["hook"]
    assert "existing data-center disputes" in profiles[2]["hook"]
    assert "documented editorial remit" in packet["scope_rule"]
    assert all(p["handoff"] == "PRESS_WRITER" for p in profiles)


def test_media_roles_preserve_duty_authority_boundary() -> None:
    packet = json.loads(ROLE_PATH.read_text(encoding="utf-8"))
    roles = packet["roles"]
    assert packet["identity"] == "0102"
    assert packet["status"] == "SPECIFIED_NOT_RUNTIME_BOUND"
    assert packet["parent_skill"] == "yumori_contact_ledger"
    for role in ("PRESS_WRITER", "PRESS_EDITOR", "CORRESPONDENCE_CURATOR"):
        assert roles[role]["can_send"] is False
    assert roles["RELEASE_MANAGER"]["can_send"] == (
        "ONLY_WITH_CURRENT_PRINCIPAL_AUTHORIZATION_AND_CONNECTOR_PERMISSION"
    )
    assert roles["PRESS_WRITER"]["handoff"] == "PRESS_EDITOR"
    assert roles["PRESS_EDITOR"]["handoff"] == "RELEASE_MANAGER"
    assert roles["RELEASE_MANAGER"]["handoff"] == "CORRESPONDENCE_CURATOR"
    assert "HOLD" in packet["workflow_states"]
    assert "unresolved_prior_send" in packet["hold_conditions"]


def test_media_profiles_bind_sources_and_receipt_requirements() -> None:
    packet = json.loads(ROLE_PATH.read_text(encoding="utf-8"))
    assert packet["canonical_report_url"] == "https://esingularity.ai/reports/jhr"
    assert "Prefer the website JHR hub over LinkedIn" in packet["link_rule"]
    assert {
        "hook", "why_now", "verified_evidence", "strongest_counterpoint",
        "single_reporting_request", "source_urls", "photo_provenance",
        "press_contact_source", "dedupe_result", "authorization", "send_state",
    } <= set(packet["required_pitch_fields"])
    curator = packet["roles"]["CORRESPONDENCE_CURATOR"]
    assert "message_id" in curator["output"]
    assert "Asia/Tokyo" in curator["output"]
    assert "Draft creation is never a sent event" in curator["acceptance"]
    assert "All scoped emails retain receipts, not just prominent milestones" in curator["acceptance"]


def test_media_profiles_are_registered_without_new_skill_entries() -> None:
    packet = json.loads(ROLE_PATH.read_text(encoding="utf-8"))
    registry = json.loads(SKILL_REGISTRY_PATH.read_text(encoding="utf-8"))
    entry = registry["skills"]["yumori_contact_ledger"]
    assert set(entry["logical_roles"]) == set(packet["roles"])
    assert not (set(packet["roles"]) & set(registry["skills"]))


def _gmail_entry_gate() -> str:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    start = skill.index("## Mandatory Gmail entry gate: SENT_FIRST_MOSHPIT_NOTIFY_0102")
    return skill[start:skill.index("## Parent workflow", start)]


def _gmail_regression_cases() -> dict[str, tuple[str, str, str]]:
    cases = {}
    for line in _gmail_entry_gate().splitlines():
        if not line.startswith("| "):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 4 and cells[0] not in {"Case", "---"}:
            assert cells[0] not in cases, "Duplicate regression case"
            cases[cells[0]] = (cells[1], cells[2], cells[3])
    return cases


def test_gmail_entry_gate_runs_in_required_order_before_branching() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    gate = _gmail_entry_gate()
    ordered_steps = (
        "1. **Sent first.**",
        "2. **Compare every relevant draft against Sent.**",
        "3. **Check the Mosh Pit, not the ModLog.**",
        "4. **Notify 0102 before status or action.**",
    )
    positions = [gate.index(step) for step in ordered_steps]
    assert positions == sorted(positions)
    parent = skill.split("## Parent workflow", 1)[1].split("## Conditional reply branches", 1)[0]
    assert parent.lstrip().startswith("1. Run `SENT_FIRST_MOSHPIT_NOTIFY_0102`")
    assert "applies to every invocation" in gate
    assert "first mailbox search" in gate


def test_gmail_entry_gate_preserves_earlier_send_with_distinct_newer_draft() -> None:
    cases = _gmail_regression_cases()
    evidence, result, action = cases["earlier_sent_later_draft"]
    assert "Earlier VOTE NO request is SENT" in evidence
    assert "distinct draft" in evidence
    assert result.startswith("EARLIER_SENT_NEW_DRAFT;")
    assert "The earlier VOTE NO message was sent; the later AI Koban update remains a separate draft." in result
    assert "NOTIFY_0102" in action
    assert "no automatic resend" in action
    assert "A newer unsent update does not erase an earlier successful send." in _gmail_entry_gate()


def test_gmail_entry_gate_repairs_missing_receipt_instead_of_resending() -> None:
    cases = _gmail_regression_cases()
    assert cases["sent_missing_moshpit"][1] == "SENT_LOG_GAP"
    assert "REPAIR_LOG" in cases["sent_missing_moshpit"][2]
    assert "never resend" in cases["sent_missing_moshpit"][2]
    assert cases["moshpit_sent_no_gmail_receipt"][1] == "UNVERIFIED_RECORD"
    assert "HOLD" in cases["moshpit_sent_no_gmail_receipt"][2]
    gate = " ".join(_gmail_entry_gate().split())
    assert "Fetch Gmail IDs referenced by the Mosh Pit that the initial search missed." in gate
    assert "Repository ModLog entries record software work, not whether correspondence was sent." in gate


def test_gmail_entry_gate_notification_has_evidence_and_no_implied_send_power() -> None:
    gate = _gmail_entry_gate()
    for field in (
        "project_scope", "mailbox_scope", "checked_window", "as_of", "sent_search_complete",
        "prior_send_state", "sent_message_ids", "sent_thread_ids", "sent_local_dates",
        "actual_recipient_coverage", "draft_message_id", "draft_relation", "content_delta",
        "moshpit_receipt_state", "moshpit_event_dates", "email_log_state", "conflicts",
        "recommended_action", "send_hold", "notification_target",
    ):
        assert f"`{field}`" in gate, field
    assert "notification_target` (0102)" in gate
    normalized = " ".join(gate.split())
    assert "The gate returns a reconciliation decision, not send authority." in normalized
    assert "no email-to-self or separate agent is implied" in normalized
    assert "without a configured, authorized channel and a receipt" in normalized


def test_gmail_entry_gate_covers_uncertainty_duplicates_and_partial_recipients() -> None:
    cases = _gmail_regression_cases()
    assert set(cases) == {
        "earlier_sent_later_draft", "exact_sent_copy_draft_remains", "sent_missing_moshpit",
        "moshpit_sent_no_gmail_receipt", "incomplete_sent_search", "partial_recipient_coverage",
        "draft_without_sent_match", "no_draft",
    }
    assert all("NOTIFY_0102" in case[2] for case in cases.values())
    assert cases["incomplete_sent_search"][1] == "UNKNOWN"
    assert "HOLD" in cases["incomplete_sent_search"][2]
    assert "never claim unsent" in cases["incomplete_sent_search"][2]
    assert cases["exact_sent_copy_draft_remains"][1] == "SAME_MESSAGE_SENT"
    assert "preserve draft; no duplicate send" in cases["exact_sent_copy_draft_remains"][2]
    assert cases["partial_recipient_coverage"][1] == "PARTIAL_RECIPIENT_COVERAGE"
    assert "no blanket resend" in cases["partial_recipient_coverage"][2]
    assert cases["draft_without_sent_match"][1] == "NO_SENT_MATCH_IN_CHECKED_SCOPE"
    assert "await applicable send authorization" in cases["draft_without_sent_match"][2]
    assert cases["no_draft"][1] == "NO_RELEVANT_DRAFT"
