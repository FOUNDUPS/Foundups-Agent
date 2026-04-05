# Threshold Gaming Sentinel Spec

**Status**: Canonical spec
**Owner**: 0102 (Worker N)
**Slice**: `FOUNDUPS_THRESHOLD_GAMING_AND_SUMO_PATTERN_SENTINEL_SPEC_PHASE1`
**Date**: 2026-04-06
**Parent**: WSP 29 (CABR Engine), WSP 26 (Tokenization)

---

## 1. Architecture Call

### Where Anti-Gaming Lives

```
CABR / 3V Engine
  ├── cabr_estimator.py          ← CABR scoring (env, soc, part)
  ├── participation_sentinel.py  ← existing: concentration, velocity, Sybil, outliers
  ├── threshold_sentinel.py      ← NEW: threshold gaming, reciprocity, rings, scrutiny
  └── signal_filter.py           ← NEW: raw event → verified participation signal
```

**Anti-gaming is owned by CABR's 3V engine.** Not WSP 15 (prioritization only). Not a standalone module. Not infrastructure.

**Rationale**:
- WSP 15 scores what to build next (Complexity × Importance × Deferability × Impact). It is a planning tool. It has no runtime scoring, no economic gate, no consensus mechanism. File: `WSP_knowledge/src/WSP_15_Module_Prioritization_Scoring_System.md`.
- WSP 29 defines CABR as "the Verification, Validation, and Valuation Engine" — the runtime quality/economic gate. Anti-gaming is a quality gate function. File: `WSP_knowledge/src/WSP_29_CABR_Engine.md`.
- 3V (V1: Validation, V2: Verification, V3: Valuation) is the evaluation engine inside CABR. It is not separate from CABR — it IS how CABR judges evidence.
- The existing `participation_sentinel.py` already lives in `simulator/economics/` and integrates with CABR. The threshold sentinel extends this, not replaces it.

**Evidence status**: PROVEN (WSP 15 text confirms prioritization-only scope; WSP 29 text confirms CABR as runtime quality gate; `participation_sentinel.py` already exists in CABR's economics layer).

### Boundary Lock

| Component | Owns | Does NOT Own |
|-----------|------|-------------|
| WSP 15 | Module prioritization scoring (P0–P4) | Runtime anti-gaming, token economics, consensus |
| CABR / 3V | Runtime quality gate, anti-gaming, participation scoring, PoB validation | Development planning, sprint scheduling |
| Participation Sentinel (existing) | Concentration, velocity, Sybil, statistical outliers | Threshold proximity, reciprocity, rings, scrutiny |
| Threshold Sentinel (new) | Threshold proximity, reciprocity, ring detection, scrutiny sensitivity | General statistical anomalies (leave to existing sentinel) |
| Signal Filter (new) | Raw event → verified signal conversion | CABR score calculation (leave to `cabr_estimator.py`) |

---

## 2. Threshold Gaming Detection

### 2.1 Threshold-Edge Anomaly Detector

**Model**: Sumo 7-7 boundary overperformance (Duggan & Levitt 2002).

**FoundUps implementation**:

```python
class ThresholdEdgeDetector:
    """Detect activity spikes correlated with threshold proximity."""

    THRESHOLDS = [
        {"name": "cabr_valve", "value": 0.618, "field": "cabr_total"},
        {"name": "du_to_dao", "value": 10.0, "field": "allocation_ratio"},
        {"name": "dao_to_un", "value": 100.0, "field": "allocation_ratio"},
        {"name": "staker_hurdle", "value": 10.0, "field": "cumulative_ratio"},
    ]
    PROXIMITY_BAND = 0.05  # 5% of threshold value
    SIGMA_THRESHOLD = 2.0  # Activity must be 2σ+ above non-boundary average

    def detect(self, participant_id, activity_history, current_metric_values):
        """
        For each threshold:
        1. Is participant within proximity band? (e.g., CABR at 0.59-0.617)
        2. Is current activity > 2σ above their non-boundary average?
        3. Does activity drop after crossing threshold?

        If all three: THRESHOLD_GAMING alert.
        """
```

**What makes this persuasive** (per sumo paper): The detection is not "they're active near a threshold" — it's the *differential*. A participant whose activity is uniformly high is not gaming. A participant whose activity is average everywhere except within 5% of a threshold is gaming.

**Alert type**: `THRESHOLD_GAMING`
**Severity**: 0.4 (first occurrence) → escalates by 0.15 per repeat.

### 2.2 Reciprocity Detector

**Model**: Sumo rematch reversal (80% → 40% → 50%).

**FoundUps implementation**:

```python
class ReciprocityDetector:
    """Detect mutual favor exchange in verification pairs."""

    LOOKBACK_EPOCHS = 10
    EXPECTED_PAIRWISE_RATE = 0.5  # Random pairing baseline
    SIGMA_THRESHOLD = 2.0

    def detect(self, verification_graph):
        """
        Build directed verification graph: edges = verify(A→B).
        For each pair (A,B):
        1. Count verify(A→B) and verify(B→A) in lookback window
        2. Compare to expected rate for random pairing
        3. Flag if both directions exceed 2σ

        Additional sumo-pattern check:
        4. After a "bubble" verification (near threshold), does
           the verifier receive a reciprocal verification in the
           next epoch? Track the 80/40/50 signature.
        """
```

**Key insight from sumo**: The reciprocity signal is strongest when combined with threshold proximity. A verifies B's task when B is at the CABR boundary → B verifies A's task when A is at the boundary next epoch. The combination of threshold-edge + reciprocity is the strongest collusion indicator.

**Alert type**: `RECIPROCAL_VERIFICATION`
**Severity**: 0.5 (first pair detection) → 0.7 if combined with threshold proximity.

### 2.3 Ring Detection (Closed Validation Rings)

**Model**: Sumo stable-to-stable collusion.

**FoundUps implementation**:

```python
class RingDetector:
    """Detect closed validation rings (3+ participants)."""

    MIN_RING_SIZE = 3
    MAX_RING_SIZE = 8  # Larger rings are unstable (game theory)
    LOOKBACK_EPOCHS = 20

    def detect(self, verification_graph):
        """
        1. Build directed verification graph
        2. Find strongly connected components (SCCs) of size 3-8
        3. For each SCC:
           a. Calculate internal verification density
           b. Compare to external verification density
           c. If internal/external ratio > 3x: flag as ring
        4. Check for cross-FoundUp rings (same agents verifying
           each other across different FoundUp task pipelines)

        Ring severity scales with:
        - Ring size (larger = more organized)
        - Internal/external ratio (higher = more exclusive)
        - Persistence (more epochs = more deliberate)
        - Cross-FoundUp span (wider = more systematic)
        """
```

**Sumo lesson**: Stable-to-stable patterns were long-running (career-length). The ring detector should track persistence over many epochs, not just snapshot detection.

**Alert type**: `VALIDATION_RING`
**Severity**: 0.6 (base) + 0.05 per member beyond 3 + 0.1 if cross-FoundUp.

### 2.4 Scrutiny-Sensitivity Meta-Detector

**Model**: Sumo cheating disappeared during media scrutiny periods.

**FoundUps implementation**:

```python
class ScrutinySensitivityDetector:
    """Detect behavior that changes based on monitoring status."""

    SCRUTINY_EVENTS = [
        "sentinel_report_published",
        "audit_announced",
        "manual_investigation_opened",
        "alert_resolved_with_action",
    ]

    def detect(self, activity_timeline, scrutiny_events):
        """
        1. Segment activity timeline into scrutiny/non-scrutiny windows
        2. For each participant:
           a. Calculate anomaly rate in scrutiny windows
           b. Calculate anomaly rate in non-scrutiny windows
           c. If ratio < 0.5 (anomalies halve under scrutiny): flag
        3. Participants whose behavior changes significantly
           based on monitoring status are MORE suspicious, not less.

        The meta-insight: organic behavior is monitoring-invariant.
        Gaming behavior is monitoring-sensitive.
        """
```

**Alert type**: `SCRUTINY_SENSITIVE`
**Severity**: 0.7 (this is a strong indicator — innocent people don't change behavior when watched).

### 2.5 Cross-Surface Inconsistency Detector

**Extension beyond sumo** (FoundUps-specific).

```python
class CrossSurfaceDetector:
    """Detect participants with high activity on one surface but zero on others."""

    def detect(self, participant_id, discord_activity, github_activity, task_activity):
        """
        Flag: high Discord activity + zero GitHub/task trail.
        Flag: high task claims + zero code merged.
        Flag: high verification count + zero own task completion.

        Organic contributors leave traces across surfaces.
        Gaming targets the cheapest surface only.
        """
```

**Alert type**: `CROSS_SURFACE_INCONSISTENCY`
**Severity**: 0.3 (informational — some participants genuinely only use one surface).

---

## 3. Integration Architecture

### 3.1 How Threshold Sentinel Relates to Existing Sentinel

```
Raw Events (Discord, GitHub, FAM, Stake)
  │
  ▼
signal_filter.py  ←  NEW: converts raw events to verified signals
  │
  ├──► participation_sentinel.py  (existing)
  │     - concentration (Gini)
  │     - velocity anomaly
  │     - Sybil pattern
  │     - statistical outliers
  │
  └──► threshold_sentinel.py  (NEW)
        - threshold-edge anomaly
        - reciprocity
        - ring detection
        - scrutiny sensitivity
        - cross-surface inconsistency
  │
  ▼
cabr_estimator.py
  │
  ├── part_score calculation (with sentinel-filtered inputs)
  ├── governance_engagement (currently placeholder 0.15)
  └── cross_foundup_collaboration (currently placeholder 0.15)
  │
  ▼
cabr_flow_router.py → UPS distribution
```

### 3.2 Sentinel Coordination

Both sentinels run on the same epoch data. They do NOT duplicate detection:

| Detection | Participation Sentinel (existing) | Threshold Sentinel (new) |
|-----------|----------------------------------|-------------------------|
| Concentration (Gini) | YES | no |
| Velocity anomaly | YES | no |
| Sybil (identical rewards) | YES | no |
| Statistical outliers (Z-score) | YES | no |
| Threshold-edge anomaly | no | YES |
| Reciprocity | no | YES |
| Ring detection | no | YES |
| Scrutiny sensitivity | no | YES |
| Cross-surface inconsistency | no | YES |

Combined alert feed goes to CABR for score adjustment.

### 3.3 CABR Score Impact

Sentinel alerts do NOT directly reduce CABR scores. They:

1. **Filter signals**: Flagged activity is excluded from `part_score` inputs before scoring
2. **Flag participants**: Flagged participants' contributions get reduced weight in `unique_contributor_count`
3. **Trigger review**: High-severity alerts require manual review before next epoch distribution
4. **Feed CABR_DAE learning**: Alert patterns feed the adaptive weight learner (WSP 29 DAE Evolution)

This prevents the sentinel from becoming an attack surface itself (where you could game the sentinel to suppress competitors).

---

## 4. Agentic Design

The Threshold Sentinel is an **agentic component** within the CABR 3V engine:

### 4.1 Agent Properties

```python
class ThresholdSentinelAgent:
    """
    Agentic sentinel operating within CABR's 3V evaluation engine.

    Properties:
    - Autonomous: runs every epoch without human trigger
    - Learning: stores detection patterns in PatternMemory
    - Adaptive: adjusts thresholds based on false-positive feedback
    - Coordinated: shares alerts with ParticipationSentinel via FAM events
    - Bounded: cannot modify CABR scores directly (only filter inputs)
    """

    def epoch_cycle(self, epoch_data):
        """
        Per-epoch autonomous cycle:
        1. Ingest raw events from all surfaces
        2. Run all 5 detectors
        3. Merge with ParticipationSentinel alerts
        4. Emit filtered participation signals to cabr_estimator
        5. Store patterns for learning
        6. Escalate high-severity to 012 review queue
        """
```

### 4.2 Learning Loop

```
Epoch N: Sentinel flags participant X as THRESHOLD_GAMING
  → 012 reviews: confirms (true positive) or dismisses (false positive)
    → PatternMemory stores outcome
      → Sentinel adjusts SIGMA_THRESHOLD for next epoch
        → Fewer false positives over time
```

### 4.3 WRE Integration

The sentinel is a WRE skill (discoverable, triggerable, executable, remembered):
- **Discoverable**: SKILLz.md in threshold_sentinel module
- **Triggerable**: epoch boundary event
- **Executable**: Gemma for fast binary classification (suspicious/not), Qwen for strategic pattern analysis
- **Remembered**: PatternMemory stores detection outcomes

---

## 5. Current Repo State: What Is Real vs. Placeholder

| Component | Status | File | Evidence |
|-----------|--------|------|----------|
| `ParticipationSentinel` | LIVE (code exists, tested) | `simulator/economics/participation_sentinel.py` | 571 lines, 5 detection vectors, singleton pattern |
| `CABREstimator` | LIVE (code exists, tested) | `simulator/ai/cabr_estimator.py` | 278 lines, AI + heuristic estimation |
| `part_score` calculation | LIVE but INCOMPLETE | `cabr_estimator.py:242` | completion_rate and verification_rate are real; governance (0.15) and cross_foundup (0.15) are hardcoded placeholders |
| `CABR_THRESHOLD = 0.618` | LIVE | `cabr_estimator.py:25` | Used in `meets_threshold()` |
| Degressive tier model | LIVE | `pool_distribution.py:36-39` | Du/Dao/Un activity levels with 80/16/4 split |
| Staker hurdle state machine | LIVE | `pool_distribution.py:98` | PRE_HURDLE → HURDLE_MET → POST_HURDLE_LOCKED |
| Anti-Sybil weighting | SPEC ONLY | WSP 29 Section 6.2–6.3 | `max_related_validators: 1` in spec, not enforced in code |
| Challenge protocol | SPEC ONLY | WSP 29 Section 4.2 | `CABRChallenge` class in spec, no implementation |
| Threshold Sentinel | DOES NOT EXIST | — | This spec defines it |
| Signal Filter | DOES NOT EXIST | — | This spec defines it |
| Ring Detector | DOES NOT EXIST | — | This spec defines it |
| Reciprocity Detector | DOES NOT EXIST | — | This spec defines it |
| Scrutiny Sensitivity Detector | DOES NOT EXIST | — | This spec defines it |

---

## 6. Recommendation

### RECOMMEND: `CABR_3V_THRESHOLD_SENTINEL`

Place a new `threshold_sentinel.py` in `modules/foundups/simulator/economics/` alongside the existing `participation_sentinel.py`. Add a new `signal_filter.py` in the same location. Both integrate into `cabr_estimator.py`'s `update_participation()` method.

### Implementation Order (Smallest Correct Steps)

**Layer 1** — Signal Filter (prerequisite for everything else)
- Create `signal_filter.py`
- Define event schema for Discord, GitHub, FAM inputs
- Implement raw-event → verified-signal conversion
- Wire into `cabr_estimator.py:update_participation()`
- Replace hardcoded governance (0.15) and cross_foundup (0.15) with real filtered inputs
- Test: filter correctly passes organic signals, blocks empty/duplicate signals

**Layer 2** — Threshold-Edge Detector (highest-value detection)
- Create `threshold_sentinel.py` with `ThresholdEdgeDetector`
- Implement proximity-band analysis for all 4 threshold types
- Implement activity differential (boundary vs. non-boundary)
- Test: synthetic data with known threshold-gaming pattern → detector fires
- Test: synthetic data with organic activity near threshold → detector does NOT fire

**Layer 3** — Reciprocity Detector
- Add `ReciprocityDetector` to `threshold_sentinel.py`
- Implement directed verification graph
- Implement pairwise rate comparison
- Implement threshold-proximity × reciprocity correlation
- Test: synthetic verification pairs with known collusion → detector fires

**Layer 4** — Ring Detector
- Add `RingDetector` to `threshold_sentinel.py`
- Implement SCC finding on verification graph
- Implement internal/external density ratio
- Test: synthetic ring of 4 participants → detector fires

**Layer 5** — Meta-Detectors
- Add `ScrutinySensitivityDetector`
- Add `CrossSurfaceDetector`
- These require multiple epochs of data to be meaningful
- Test: synthetic time-series with scrutiny-correlated behavior change

**Layer 6** — PatternMemory Integration
- Store detection outcomes for learning
- Implement threshold adjustment based on false-positive feedback
- Wire into WRE as discoverable skill

Each layer is tested independently before the next. Each layer is a single PR. No big-bang.

---

## 7. Non-Goals

- No code edits in this spec
- No tokenomics redesign
- No Discord bot implementation
- No runtime model changes
- No "AI solves cheating" claims — the sentinel detects patterns, humans judge

---

*WSP 97 Applied: Inspected current repo truth (cabr_estimator.py, participation_sentinel.py, pool_distribution.py). Compared against WSP 29 spec. Identified drift (placeholder terms, missing detectors). Defined smallest valid corrections (6-layer implementation order). Preserved chain of custody (all claims marked PROVEN/INFERRED/OPEN).*
