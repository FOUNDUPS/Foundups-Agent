from modules.foundups.esingularity.jhr.src.jhr_agent import (
    EvidenceRecord,
    assess_significance,
    run_jhr_cycle,
)


def test_no_evidence_means_no_report():
    result = run_jhr_cycle()
    assert result.publish is False
    assert result.significance_score == 0
    assert result.reason.startswith("NO_REPORT")
    assert result.wsp_97["action_evidence"]["retrieve"] == "not_connected"


def test_low_signal_vendor_story_does_not_publish():
    records = [
        EvidenceRecord(
            title="Vendor marketing update",
            url="https://example.com/vendor",
            source_class="REPORTED",
            event_kind="vendor_marketing",
            materiality=2,
        )
    ]
    publish, _, reason = assess_significance(records)
    assert publish is False
    assert "no high-signal" in reason


def test_official_material_policy_change_publishes():
    records = [
        EvidenceRecord(
            title="GX data-center concentration policy",
            url="https://www.meti.go.jp/example",
            source_class="OFFICIAL",
            event_kind="national_policy",
            materiality=5,
            corroborated=True,
        )
    ]
    result = run_jhr_cycle(lambda: records)
    assert result.publish is True
    assert result.significance_score >= 12
    assert result.reason.startswith("REPORT_REQUIRED")
    assert "Fukui implication" in result.draft_metadata["required_sections"]


def test_duplicate_evidence_is_counted_once():
    record = EvidenceRecord(
        title="Inzai zoning change",
        url="https://example.com/inzai",
        source_class="OFFICIAL",
        event_kind="zoning",
        materiality=5,
        corroborated=True,
    )
    result = run_jhr_cycle(lambda: [record, record])
    assert len(result.evidence) == 1
