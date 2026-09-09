"""Japan Hyperscaler Report (JHR) significance-gated research cycle.

WSP_97 boundary: this module does not claim to have browsed, verified, drafted,
or published anything unless evidence records are supplied by an external
retriever and pass the gate below.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Callable, Iterable, Mapping, Sequence, Any


HIGH_SIGNAL_KINDS = {
    "national_policy",
    "prefectural_policy",
    "municipal_policy",
    "hyperscale_campus",
    "grid_capacity",
    "transmission",
    "zoning",
    "community_response",
    "fukui_position",
    "cogdc_thesis_change",
}

SOURCE_WEIGHTS = {
    "OFFICIAL": 4,
    "REPORTED": 3,
    "COMMUNITY": 2,
    "ANALYSIS": 1,
}


@dataclass(frozen=True)
class EvidenceRecord:
    title: str
    url: str
    source_class: str
    event_kind: str
    published_at: str = ""
    jurisdiction: str = "Japan"
    summary: str = ""
    materiality: int = 1
    corroborated: bool = False

    def score(self) -> int:
        source = SOURCE_WEIGHTS.get(self.source_class.upper(), 0)
        kind = 3 if self.event_kind in HIGH_SIGNAL_KINDS else 0
        corroboration = 2 if self.corroborated else 0
        materiality = max(0, min(int(self.materiality), 5))
        return source + kind + corroboration + materiality


@dataclass
class JHRCycleResult:
    run_at: str
    publish: bool
    significance_score: int
    reason: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    draft_metadata: dict[str, Any] = field(default_factory=dict)
    wsp_97: dict[str, Any] = field(default_factory=dict)


def _dedupe(records: Iterable[EvidenceRecord]) -> list[EvidenceRecord]:
    seen: set[tuple[str, str]] = set()
    out: list[EvidenceRecord] = []
    for record in records:
        key = (record.url.strip().lower(), record.title.strip().lower())
        if not record.url or key in seen:
            continue
        seen.add(key)
        out.append(record)
    return out


def assess_significance(records: Sequence[EvidenceRecord], threshold: int = 12) -> tuple[bool, int, str]:
    verified = [r for r in records if r.source_class.upper() in SOURCE_WEIGHTS and r.url]
    if not verified:
        return False, 0, "NO_REPORT: no verified evidence records"

    high_signal = [r for r in verified if r.event_kind in HIGH_SIGNAL_KINDS]
    if not high_signal:
        return False, sum(r.score() for r in verified), "NO_REPORT: no high-signal event"

    score = sum(r.score() for r in high_signal)
    official = any(r.source_class.upper() == "OFFICIAL" for r in high_signal)
    corroborated = any(r.corroborated for r in high_signal)

    if score < threshold:
        return False, score, f"NO_REPORT: significance score {score} below threshold {threshold}"
    if not (official or corroborated):
        return False, score, "NO_REPORT: high-signal claim lacks official or corroborated support"

    return True, score, "REPORT_REQUIRED: verified material change"


def run_jhr_cycle(
    retriever: Callable[[], Iterable[EvidenceRecord]] | None = None,
    *,
    threshold: int = 12,
    now: datetime | None = None,
) -> JHRCycleResult:
    """Run one evidence-first JHR assessment cycle.

    The retriever is intentionally injected. Network/search implementation belongs
    to the external research adapter so unit tests stay deterministic and JHR does
    not silently imply internet access.
    """

    run_time = now or datetime.now(timezone.utc)
    if retriever is None:
        records: list[EvidenceRecord] = []
        retrieval_status = "not_connected"
    else:
        records = _dedupe(list(retriever()))
        retrieval_status = "completed"

    publish, score, reason = assess_significance(records, threshold=threshold)

    evidence_dicts = [asdict(r) | {"score": r.score()} for r in records]
    draft_metadata: dict[str, Any] = {}
    if publish:
        jurisdictions = sorted({r.jurisdiction for r in records if r.event_kind in HIGH_SIGNAL_KINDS})
        draft_metadata = {
            "series": "Japan Hyperscaler Report",
            "slug_prefix": "jhr",
            "language_priority": ["ja", "en"],
            "jurisdictions": jurisdictions,
            "required_sections": [
                "What changed",
                "Why it matters",
                "Chiba/Inzai signal",
                "Fukui implication",
                "COG DC implication",
                "Sources",
            ],
            "seo_tags": [
                "Japan Hyperscaler Report",
                "Japan data center",
                "hyperscale",
                "Inzai",
                "Chiba data center",
                "GX strategic area",
                "Watt-Bit",
                "Fukui data center",
                "COG DC",
                "eSingularity",
            ],
        }

    wsp_97 = {
        "outcome": "completed",
        "wsps_applied": ["WSP_97"],
        "truth_boundary": "publish=false unless verified evidence passes significance gate",
        "action_evidence": {
            "retrieve": retrieval_status,
            "dedupe": len(records),
            "verify": len([r for r in records if r.source_class.upper() in SOURCE_WEIGHTS]),
            "assess": score,
            "decide": "publish" if publish else "no_publish",
        },
    }

    return JHRCycleResult(
        run_at=run_time.isoformat(),
        publish=publish,
        significance_score=score,
        reason=reason,
        evidence=evidence_dicts,
        draft_metadata=draft_metadata,
        wsp_97=wsp_97,
    )
