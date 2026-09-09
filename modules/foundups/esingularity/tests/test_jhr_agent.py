from datetime import datetime, timezone
from pathlib import Path

from modules.foundups.esingularity.jhr import agent


def test_no_evidence_never_becomes_public_report(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(agent, "discover", lambda _query: [])
    result = agent.assess(tmp_path, now=datetime(2026, 9, 9, tzinfo=timezone.utc))
    assert result.status == "NO_EVIDENCE"
    assert result.publish_candidate is False
    assert result.evidence_count == 0


def test_high_signal_discovery_is_candidate_not_published(monkeypatch, tmp_path: Path):
    item = agent.EvidenceItem(
        title="GX戦略地域 データセンター集積 印西 住民 景観 騒音",
        url="https://example.jp/report",
        published_at="2026-09-09T00:00:00+00:00",
        source_host="example.jp",
        query="test",
        primary_source=False,
        signal_score=20,
        fingerprint="abc",
    )
    monkeypatch.setattr(agent, "discover", lambda _query: [item])
    result = agent.assess(tmp_path, now=datetime(2026, 9, 9, tzinfo=timezone.utc))
    assert result.status == "RESEARCH_CANDIDATE"
    assert result.publish_candidate is True
    assert "primary_source_verification_required" in result.reasons


def test_due_gate_respects_last_assessment(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("JHR_RUNTIME_DIR", str(tmp_path))
    (tmp_path / "state.json").write_text(
        '{"last_assessed_at":"2026-09-09T00:00:00+00:00"}', encoding="utf-8"
    )
    assert agent.assessment_due(
        tmp_path, now=datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)
    ) is False
