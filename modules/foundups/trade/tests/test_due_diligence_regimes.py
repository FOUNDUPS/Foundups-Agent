"""Trade Synthetic Regime Pack — Decision-Shape Evidence Tests

Slice: TRADE_DUE_DILIGENCE_SYNTHETIC_REGIME_PACK_PHASE1
Worker: W6
Spec: TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1 (PR #683)
Engine: TRADE_DUE_DILIGENCE_SCORING_ENGINE_PHASE1 (PR #687)

Test policy (per operator's patched W6 prompt)
----------------------------------------------
This is an EVIDENCE-PACK slice, NOT engine acceptance testing.

Per-regime tests MUST fail on:
  - nondeterministic output (same regime → different score bytes)
  - invalid DecisionBand value
  - malformed TradeDueDiligenceScore (component out of [0,100], etc.)
  - missing component score
  - forbidden import / field violation
  - any boundary violation (real-trading authorization, live SDK import, etc.)

Per-regime tests MUST NOT fail solely because expected_band != actual_band.
Expected-vs-actual divergence is recorded as evidence in the audit doc and
routed to a future targeted engine-tuning slice.

WSP 97 Truth Boundary
---------------------
- Pure computation against synthetic deterministic fixtures.
- No network, no wallet, no order placement, no exchange SDK import.
- No Trade status change (Trade stays Phase 0 simulation-only).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Mirror the convention used by test_due_diligence_scoring.py (PR #687):
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
# Plus the tests/ directory so `fixtures.due_diligence_regimes` resolves
# (the fixtures/ package lives at tests/fixtures/).
sys.path.insert(0, str(Path(__file__).parent))

from contracts import (  # noqa: E402
    DecisionBand,
    TradeDueDiligenceScore,
    assert_no_real_trading_authorized,
)
from due_diligence_scoring import DueDiligenceScoringEngine  # noqa: E402

from fixtures.due_diligence_regimes import (  # noqa: E402
    ALL_REGIME_CONSTRUCTORS,
    FIXTURE_REFERENCE_TIME,
    HARD_DISQUALIFIER_NAMES,
    build_regime_result,
    component_scores,
    detect_hard_disqualifiers,
    deterministic_hash,
)

# Alias: tests call the engine with the same instant the fixtures used to
# compute candidate.timestamp offsets. Post-#691 the engine requires an
# explicit `evaluation_time`; this guarantees byte-identical determinism
# without any rounding mask.
FIXED_EVAL_TIME = FIXTURE_REFERENCE_TIME


# ---------------------------------------------------------------------------
# Forbidden imports / fields — mirror PR #687 test guard so this slice can
# never silently introduce a boundary-violating import via the fixture file.
# ---------------------------------------------------------------------------

FORBIDDEN_IMPORTS = frozenset({
    "requests", "urllib", "urllib3", "httpx", "aiohttp",
    "websocket", "websockets", "socket", "asyncio",
    "ccxt", "web3", "alpaca", "binance", "coinbase", "kraken",
    "ib_insync", "ftx", "bitfinex", "polygon", "yfinance",
    "eth_account", "cryptography",
})

FORBIDDEN_FIELDS = frozenset({
    "api_key", "secret", "signer", "wallet_private_key", "order_id",
    "endpoint", "exchange_client",
})


def _read_source(rel_path: str) -> str:
    p = Path(__file__).parent / rel_path
    return p.read_text(encoding="utf-8")


def test_regime_fixture_has_no_forbidden_imports():
    """The regime fixture file must not import any networking / exchange SDK."""
    src = _read_source("fixtures/due_diligence_regimes.py")
    for mod in FORBIDDEN_IMPORTS:
        # match `import X`, `from X import`, `from X.` boundaries
        for pat in (f"import {mod}", f"from {mod} import", f"from {mod}."):
            assert pat not in src, (
                f"Forbidden import pattern {pat!r} present in due_diligence_regimes.py"
            )


def test_regime_fixture_has_no_forbidden_fields():
    """Fixture must not reference any wallet/order/key field names."""
    src = _read_source("fixtures/due_diligence_regimes.py").lower()
    for field in FORBIDDEN_FIELDS:
        assert field.lower() not in src, (
            f"Forbidden field name {field!r} present in due_diligence_regimes.py"
        )


def test_regime_test_file_has_no_forbidden_imports():
    """This test file must not import any networking / exchange SDK either."""
    src = _read_source("test_due_diligence_regimes.py")
    for mod in FORBIDDEN_IMPORTS:
        for pat in (f"import {mod}", f"from {mod} import", f"from {mod}."):
            assert pat not in src, (
                f"Forbidden import pattern {pat!r} present in test_due_diligence_regimes.py"
            )


# ---------------------------------------------------------------------------
# Registry-level invariants
# ---------------------------------------------------------------------------

def test_registry_has_all_seven_mandatory_regimes():
    """All 7 mandatory regime IDs must be present (slice operator constraint)."""
    expected_prefixes = {
        "R1_organic_launch_clean_socials",
        "R2_influencer_pump_high_concentration",
        "R3_dead_x_no_telegram",
        "R4_issuer_prior_rug_history",
        "R5_whale_accumulation_then_dump",
        "R6_telegram_active_low_authenticity",
        "R7_bonding_curve_migration_risk",
    }
    actual_ids = {ctor().regime_id for ctor in ALL_REGIME_CONSTRUCTORS}
    missing = expected_prefixes - actual_ids
    assert not missing, f"Missing mandatory regimes: {missing}"


def test_registry_regime_ids_are_unique():
    """No duplicate regime_id across the registry."""
    ids = [ctor().regime_id for ctor in ALL_REGIME_CONSTRUCTORS]
    assert len(ids) == len(set(ids)), f"Duplicate regime_id present: {ids}"


# ---------------------------------------------------------------------------
# Per-regime tests (parametrized) — operator-patched policy
# ---------------------------------------------------------------------------

# Each regime is parametrized by its constructor function; pytest IDs use the
# regime_id so failures are obvious.
def _all_regimes():
    return [pytest.param(ctor, id=ctor().regime_id) for ctor in ALL_REGIME_CONSTRUCTORS]


@pytest.fixture
def scoring_engine() -> DueDiligenceScoringEngine:
    """Fresh deterministic engine per test."""
    return DueDiligenceScoringEngine()


@pytest.mark.parametrize("regime_ctor", _all_regimes())
def test_regime_score_is_well_formed(regime_ctor, scoring_engine):
    """The engine output for each regime is a structurally-valid score."""
    regime = regime_ctor()
    score = scoring_engine.score(
        regime.candidate,
        evaluation_time=FIXED_EVAL_TIME,
        issuer_report=regime.issuer_report,
        wallet_reports=regime.wallet_reports,
        social_report=regime.social_report,
        influencer_report=regime.influencer_report,
    )

    assert isinstance(score, TradeDueDiligenceScore)
    # All 10 components are present and inside the [0, 100] range.
    comps = component_scores(score)
    assert set(comps.keys()) == {
        "launch_timing", "issuer_history", "social_authenticity",
        "telegram_quality", "influencer_risk", "holder_distribution",
        "whale_risk", "prior_token_history", "bonding_curve", "rug_honeypot",
    }
    for name, v in comps.items():
        assert 0.0 <= v <= 100.0, f"{regime.regime_id}: {name}={v} outside [0,100]"
    assert 0.0 <= score.total_score <= 100.0
    assert 0.0 <= score.risk_score <= 100.0
    assert 0.0 <= score.evidence_confidence <= 1.0
    # risk_score is the complement of total_score per engine convention.
    assert abs((score.total_score + score.risk_score) - 100.0) < 0.01


@pytest.mark.parametrize("regime_ctor", _all_regimes())
def test_regime_band_is_valid(regime_ctor, scoring_engine):
    """The decision band returned must be a valid DecisionBand value."""
    regime = regime_ctor()
    score = scoring_engine.score(
        regime.candidate,
        evaluation_time=FIXED_EVAL_TIME,
        issuer_report=regime.issuer_report,
        wallet_reports=regime.wallet_reports,
        social_report=regime.social_report,
        influencer_report=regime.influencer_report,
    )
    assert isinstance(score.decision_band, DecisionBand), (
        f"{regime.regime_id}: decision_band must be a DecisionBand enum, "
        f"got {type(score.decision_band)!r}"
    )
    # And it must be one of the four canonical values.
    assert score.decision_band in {
        DecisionBand.REJECT,
        DecisionBand.OBSERVE,
        DecisionBand.SIMULATE_ONLY,
        DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW,
    }


@pytest.mark.parametrize("regime_ctor", _all_regimes())
def test_regime_no_band_authorizes_real_trading(regime_ctor, scoring_engine):
    """No decision band may authorize real trading (boundary invariant).

    `contracts.assert_no_real_trading_authorized(band)` is a runtime check
    that asserts `not authorized_for_real_trading` — it passes silently
    when the boundary is intact, and raises only if someone has flipped the
    `authorized_for_real_trading` flag to True (i.e. removed the boundary).
    This test calls it directly and lets a real raise propagate as a
    boundary-violation test failure.
    """
    regime = regime_ctor()
    score = scoring_engine.score(
        regime.candidate,
        evaluation_time=FIXED_EVAL_TIME,
        issuer_report=regime.issuer_report,
        wallet_reports=regime.wallet_reports,
        social_report=regime.social_report,
        influencer_report=regime.influencer_report,
    )
    # Must NOT raise — if it does, the Phase 0 boundary has been removed.
    assert_no_real_trading_authorized(score.decision_band)


@pytest.mark.parametrize("regime_ctor", _all_regimes())
def test_regime_scoring_is_deterministic(regime_ctor, scoring_engine):
    """Same regime scored twice in the same test → identical deterministic hash.

    Post-#691 (clock fix): the scoring engine no longer reads an implicit
    clock; `evaluation_time` is required and explicit. Passing the same
    FIXED_EVAL_TIME to both calls produces byte-identical component scores
    with no rounding mask. This test asserts true byte-identical determinism.
    """
    regime = regime_ctor()
    score_a = scoring_engine.score(
        regime.candidate,
        evaluation_time=FIXED_EVAL_TIME,
        issuer_report=regime.issuer_report,
        wallet_reports=regime.wallet_reports,
        social_report=regime.social_report,
        influencer_report=regime.influencer_report,
    )
    score_b = scoring_engine.score(
        regime.candidate,
        evaluation_time=FIXED_EVAL_TIME,
        issuer_report=regime.issuer_report,
        wallet_reports=regime.wallet_reports,
        social_report=regime.social_report,
        influencer_report=regime.influencer_report,
    )
    hash_a = deterministic_hash(score_a)
    hash_b = deterministic_hash(score_b)
    assert hash_a == hash_b, (
        f"{regime.regime_id}: scoring is nondeterministic. "
        f"hash_a={hash_a} hash_b={hash_b}"
    )
    # And components are bit-equal between the two runs.
    assert component_scores(score_a) == component_scores(score_b)


@pytest.mark.parametrize("regime_ctor", _all_regimes())
def test_regime_hard_disqualifiers_consistent_with_band(regime_ctor, scoring_engine):
    """If any hard disqualifier triggers, the resulting band must be REJECT
    or OBSERVE (per contracts.determine_decision_band)."""
    regime = regime_ctor()
    score = scoring_engine.score(
        regime.candidate,
        evaluation_time=FIXED_EVAL_TIME,
        issuer_report=regime.issuer_report,
        wallet_reports=regime.wallet_reports,
        social_report=regime.social_report,
        influencer_report=regime.influencer_report,
    )
    disqs = detect_hard_disqualifiers(score)
    if disqs:
        # rug_honeypot < 20 OR issuer_history < 20 force REJECT;
        # evidence_confidence < 0.5 forces OBSERVE. Either way, band must
        # NOT be SIMULATE_ONLY or CANDIDATE_FOR_FUTURE_REVIEW.
        assert score.decision_band in {DecisionBand.REJECT, DecisionBand.OBSERVE}, (
            f"{regime.regime_id}: hard disqualifiers {disqs} but band is "
            f"{score.decision_band.value}"
        )
    # All disqualifier names belong to the documented set.
    assert set(disqs).issubset(set(HARD_DISQUALIFIER_NAMES))


# ---------------------------------------------------------------------------
# Expected vs Actual — RECORDED, never blocking (per operator's patched policy)
# ---------------------------------------------------------------------------

def test_expected_vs_actual_table_is_complete_for_all_regimes(scoring_engine):
    """Build the expected-vs-actual table for ALL regimes in one pass.

    Failure modes (per patched policy):
      - structurally-invalid result (missing field / wrong shape)
      - nondeterministic across two re-runs
      - boundary violation

    NOT a failure: expected_band != actual_band. That is documented as the
    regime's `band_match=False` row in the per-regime result.
    """
    required_fields = {
        "regime_id",
        "description",
        "expected_band",
        "actual_band",
        "band_match",
        "total_score",
        "risk_score",
        "evidence_confidence",
        "component_scores",
        "hard_disqualifiers_triggered",
        "deterministic_hash",
        "band_rationale",
    }
    rows: List[Dict[str, Any]] = []
    for ctor in ALL_REGIME_CONSTRUCTORS:
        regime = ctor()
        score = scoring_engine.score(
            regime.candidate,
            evaluation_time=FIXED_EVAL_TIME,
            issuer_report=regime.issuer_report,
            wallet_reports=regime.wallet_reports,
            social_report=regime.social_report,
            influencer_report=regime.influencer_report,
        )
        result = build_regime_result(regime, score)
        # Schema check
        missing = required_fields - set(result.keys())
        assert not missing, (
            f"{regime.regime_id}: result row missing fields {missing}"
        )
        # actual_band must be a valid enum value string
        assert result["actual_band"] in {b.value for b in DecisionBand}
        rows.append(result)

    # Determinism across the WHOLE pack: re-score every regime and compare
    # hashes — protects against a regime whose RNG-like inputs would shift
    # only when interleaved with others (none are expected; this is a guard).
    rerun_hashes = []
    for ctor in ALL_REGIME_CONSTRUCTORS:
        regime = ctor()
        score = scoring_engine.score(
            regime.candidate,
            evaluation_time=FIXED_EVAL_TIME,
            issuer_report=regime.issuer_report,
            wallet_reports=regime.wallet_reports,
            social_report=regime.social_report,
            influencer_report=regime.influencer_report,
        )
        rerun_hashes.append(deterministic_hash(score))
    original_hashes = [r["deterministic_hash"] for r in rows]
    assert rerun_hashes == original_hashes, (
        "Pack-level determinism violation: per-regime hashes changed across "
        "back-to-back full passes.\n"
        f"original={original_hashes}\nrerun   ={rerun_hashes}"
    )

    # Print the full table to stdout so test runs (with -s) emit the evidence
    # snapshot inline; audit doc consumes the same content via the helper
    # script described in the audit. Pytest swallows by default unless -s,
    # which is fine for normal CI.
    print("\n[REGIME-PACK-EVIDENCE]")
    print(json.dumps(rows, indent=2, sort_keys=True))


# ---------------------------------------------------------------------------
# Source-tree boundary proof (no Trade src/ mutation by this slice)
# ---------------------------------------------------------------------------

def test_fixture_file_does_not_touch_engine_internals():
    """Sanity guard — the fixture file builds engine *inputs* only; it must
    not reach into engine internals (e.g. _WEIGHTS dict, __setattr__ hooks,
    enum extension hooks). The git-diff proof in the audit doc is the
    authoritative no-mutation evidence; this is an in-suite tripwire so
    a future fixture edit that crosses the boundary fails fast.

    Forbidden surface tokens are assembled from fragments to avoid
    self-referential matching against the literal in this test file.
    """
    src = _read_source("fixtures/due_diligence_regimes.py")
    forbidden_surfaces = [
        "DueDiligenceScoringEngine" + "._WEIGHTS",
        "TradeDueDiligenceScore" + "._WEIGHTS",
        "TradeDueDiligenceScore" + ".__setattr__",
        "DecisionBand" + "._missing_",
    ]
    for bad in forbidden_surfaces:
        assert bad not in src, (
            f"Fixture file references engine-internal mutation surface: {bad!r}"
        )
