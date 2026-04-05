# Sumo Pattern to FoundUps Mapping

**Status**: Canonical spec
**Owner**: 0102 (Worker N)
**Slice**: `FOUNDUPS_THRESHOLD_GAMING_AND_SUMO_PATTERN_SENTINEL_SPEC_PHASE1`
**Date**: 2026-04-06

---

## 1. Source Paper

**Citation**: Duggan, Mark, and Steven D. Levitt. 2002. "Winning Isn't Everything: Corruption in Sumo Wrestling." *American Economic Review* 92 (5): 1594–1605.

- **NBER Working Paper**: No. 7798, July 2000
- **AER Published**: December 2002
- **Dataset**: 32,000 bouts, 281 wrestlers, January 1989 – January 2000
- **NBER URL**: https://www.nber.org/papers/w7798
- **PDF**: https://pricetheory.uchicago.edu/levitt/Papers/DugganLevitt2002.pdf

**Confirmed by**: Dietl, Lang & Werner (2010), *Journal of Sports Economics* 11(4): 383–396 (extended dataset, confirmed patterns). 2011 police investigation recovered cell phone texts proving match-fixing — 23 wrestlers expelled. Popularized in Levitt & Dubner, *Freakonomics* (2005), Chapter 1.

Evidence status: **PROVEN** (statistical inference confirmed by direct physical evidence in 2011).

---

## 2. The Sumo Detection Pattern

### 2.1 The Threshold Structure

In professional sumo, each wrestler fights 15 bouts per tournament (6 tournaments/year). A wrestler needs **8 wins** (kachi-koshi) to maintain or improve rank. Below 8 is demotion (make-koshi).

The 8th win is worth **>11 ranking points** versus ~3 for any other win. This creates a nonlinear incentive cliff at the 7-7 boundary.

### 2.2 Five Detection Signals

| Signal | Sumo Finding | Statistical Evidence |
|--------|-------------|---------------------|
| **Threshold-edge anomaly** | 7-7 wrestlers beat 8-6 opponents ~80% on Day 15 | Expected: 48.7%. Observed: ~80%. 26% of wrestlers finish exactly 8-8, vs 12.2% at 7-8 (expected: both 19.6%) |
| **Reciprocity** | Winner of bubble match loses rematch at ~40% | 80% → 40% → 50% across three consecutive meetings. Consistent with quid pro quo |
| **Stable-to-stable collusion** | Winning on bubble was more frequent between wrestlers who met often | Career-long relationships enable collusion. Rate rises over career, drops in final year (no future repayment) |
| **Scrutiny disappearance** | Win rate reverted to ~50% during media allegations | May 1996, Nov 1999, Jan 2000 — when media scrutinized, manipulation vanished temporarily |
| **Boundary-only overperformance** | Effect concentrated at 7-7 vs 8-6 (Day 15); not present at 8-7 vs 7-8 | Day 15 coefficient: 0.189 (SE: 0.035, p<0.01). Day 11 coefficient: 0.087 (SE: 0.032). Effect grows as deadline approaches |

### 2.3 Why Alternative Explanations Fail

Duggan & Levitt eliminated "increased effort" as an explanation:
1. Effort cannot explain the **reciprocity reversal** (80% → 40% → 50%)
2. Effort cannot explain the **media scrutiny disappearance**
3. Effort cannot explain the **career trajectory** (rising rate, dropping in final year)

Only deliberate coordination fits all five signals simultaneously.

---

## 3. Mapping to FoundUps Gaming Surfaces

### 3.1 Threshold Structures in FoundUps

| FoundUps Threshold | Equivalent to Sumo 8th Win | Where |
|-------------------|---------------------------|-------|
| CABR ≥ 0.618 | 8th win threshold | `cabr_estimator.py` line 25: `CABR_THRESHOLD = 0.618` |
| Activity tier transition (Du→Dao at 10x) | Rank promotion | `pool_distribution.py` lines 36–39: degressive tier model |
| Activity tier transition (Dao→Un at 100x) | Higher rank promotion | `pool_distribution.py` lines 36–39 |
| @Contributor promotion | Role upgrade | Discord blueprint: manual promotion by GitHub activity |
| @Core promotion | Trust tier | Discord blueprint: manual promotion by 012 |
| Staker hurdle (10x cumulative) | Post-hurdle rate reduction | `pool_distribution.py` line 98: `StakerHurdleState` |
| Epoch distribution cutoff | Tournament end | Epoch boundary in `pool_distribution.py` |

**Evidence status**: PROVEN that these thresholds exist in repo. INFERRED that they create gaming surfaces equivalent to sumo's 8th-win cliff.

### 3.2 Direct Pattern Mapping

#### A. Threshold-Edge Gaming → CABR Score Manipulation

**Sumo**: Activity spikes at exactly 7-7 (one win from threshold).

**FoundUps equivalent**: A FoundUp's `part_score` mysteriously spikes right when `total CABR` is at 0.55–0.61 (one bump from the 0.618 valve-open threshold). Or a participant's activity spikes right before a tier transition.

**Detection**: Monitor for activity-vs-distance-to-threshold correlation. Organic activity is threshold-independent. Gaming activity clusters at the boundary.

**Current repo state**: NOT DETECTED. `participation_sentinel.py` has no threshold-proximity detector. `cabr_estimator.py` has no boundary-anomaly check. **Status: OPEN — needs implementation.**

#### B. Reciprocity → Peer Verification Collusion

**Sumo**: A lets B win now, B lets A win next time. 80% → 40% → 50%.

**FoundUps equivalent**: Agent A verifies Agent B's task this epoch. Agent B verifies Agent A's task next epoch. Mutual verification rings inflate both participants' completion and verification rates.

**Detection**: Track directed verification graph. Flag pairs where `verify(A→B)` and `verify(B→A)` both exceed expected rates. The sumo paper's method: compare the pairwise win rate in "bubble" situations vs. non-bubble situations for the same pair.

**Current repo state**: PARTIALLY COVERED. `participation_sentinel.py` has Sybil detection (identical rewards), but NO reciprocity graph analysis. WSP 29 Section 6.2 specifies `max_related_validators: 1` in cross-validation rules, but this is spec only — not enforced in `cabr_estimator.py`. **Status: OPEN — needs reciprocity graph detector.**

#### C. Stable-to-Stable → Cross-FoundUp Ring Collusion

**Sumo**: Wrestlers from allied stables coordinate outcomes.

**FoundUps equivalent**: Agents from FoundUp X and FoundUp Y systematically verify each other's work. The `cross_foundup_collaboration` term in `part_score` (currently a 0.15 placeholder) could be gamed by fake cross-FoundUp verification rings.

**Detection**: Cluster analysis on the verification graph. Flag FoundUp pairs where cross-verification is statistically overrepresented vs. random pairing.

**Current repo state**: `cross_foundup_collaboration` is a PLACEHOLDER (hardcoded 0.15 in `cabr_estimator.py` line 247). No real data feeds it. **Status: OPEN — placeholder must become real signal with anti-ring protection before going live.**

#### D. Scrutiny Disappearance → Behavior Change Under Audit

**Sumo**: Cheating vanished during media scrutiny, returned when attention subsided.

**FoundUps equivalent**: Suspicious patterns disappear when the Participation Sentinel is announced or when audit results are published, then reappear when monitoring appears to lapse.

**Detection**: Track behavioral time-series. Compare anomaly rates in "sentinel-active" vs. "sentinel-quiet" periods. A statistically significant difference is itself an indicator of manipulation — organic behavior doesn't change based on monitoring status.

**Current repo state**: `ParticipationSentinel` runs continuously but has no meta-analysis of its own effect on participant behavior. **Status: OPEN — needs scrutiny-sensitivity meta-detector.**

#### E. Boundary-Only Overperformance → Selective Activity Spikes

**Sumo**: Anomalous performance only at the 7-7 boundary, not at other records.

**FoundUps equivalent**: A participant is average everywhere except right at tier boundaries (9.5x approaching 10x Dao threshold, or 0.61 CABR approaching 0.618). Organic improvement is gradual. Threshold-targeted spikes are not.

**Detection**: Compare activity distributions at boundary-adjacent ranges vs. non-boundary ranges. A participant whose activity is 2σ+ higher within 5% of any threshold, but average elsewhere, is flagged.

**Current repo state**: NO boundary-proximity analysis exists anywhere in the codebase. **Status: OPEN — needs boundary anomaly detector.**

---

## 4. Gaming Surface Inventory

### 4.1 Discord / Community

| Surface | Attack Vector | Sumo Pattern | Current Defense |
|---------|--------------|-------------|-----------------|
| Message volume | Spam for participation credit | Boundary overperformance | NONE — Discord activity not yet wired to CABR |
| Reaction farming | Bot-react to inflate engagement | Bot timing | YAGPDB automod (not yet configured) |
| Mutual boosting | A replies to B, B replies to A | Reciprocity | NONE |
| Category-specific activity | Spike activity in one FoundUp's channels before epoch | Threshold-edge | NONE |

### 4.2 GitHub / Issues / PRs

| Surface | Attack Vector | Sumo Pattern | Current Defense |
|---------|--------------|-------------|-----------------|
| Issue creation spam | Create trivial issues for task credit | Boundary overperformance | NONE |
| Mutual review | A reviews B's PR, B reviews A's PR | Reciprocity | GitHub CODEOWNERS (partial) |
| Self-merge | Merge own PRs without real review | Sybil | Branch protection rules (partial) |
| Commit inflation | Many tiny commits for activity count | Bot timing | NONE |

### 4.3 Task Claims / FAM Pipeline

| Surface | Attack Vector | Sumo Pattern | Current Defense |
|---------|--------------|-------------|-----------------|
| Task creation + self-claim | Create task → claim with alt → verify with another alt | Sybil + ring | WSP 29 Section 6.2: `max_related_validators: 1` (SPEC ONLY) |
| Verification rings | A verifies B, B verifies A, systematically | Reciprocity + stable collusion | Sybil detection in `participation_sentinel.py` (identical rewards only) |
| Threshold-targeted claims | Spike task claims when approaching tier boundary | Threshold-edge | NONE |

### 4.4 Peer Verification

| Surface | Attack Vector | Sumo Pattern | Current Defense |
|---------|--------------|-------------|-----------------|
| Rubber-stamping | Verify without inspecting | Scrutiny disappearance (less effort when not watched) | NONE |
| Reciprocal verification | Mutual verification agreements | Reciprocity | `max_related_validators: 1` (SPEC ONLY) |
| Ring verification | 3+ participants rotating verification duties | Stable-to-stable | NONE |

### 4.5 Stake / Endorsement / Governance

| Surface | Attack Vector | Sumo Pattern | Current Defense |
|---------|--------------|-------------|-----------------|
| Stake-and-dump | Stake to boost CABR, unstake immediately | Threshold-edge | 5% unstaking fee (partial deterrent) |
| Vote manipulation | Coordinate votes to influence governance | Ring collusion | NONE |
| Endorsement rings | Mutual endorsements for CABR weight | Reciprocity | NONE |

---

## 5. What Counts As What

### 5.1 Real Engagement (PROVEN by evidence trail)

- Code merged to protected branch with passing tests
- Issue resolved with linked PR
- Task completed with verifiable proof artifact
- UPS staked for >1 epoch (committed, not flash-stake)
- Substantive review comment that references specific code
- Documentation that fills a gap identified by audit

### 5.2 Suspicious Engagement (INFERRED by pattern)

- Activity spike correlated with threshold proximity
- Reciprocal verification between same pair >2x expected rate
- Activity in Discord channels with zero corresponding GitHub/task trail
- Identical or near-identical activity timestamps across accounts
- Engagement that drops when monitoring is announced

### 5.3 Verified Work (PROVEN by 3V pipeline)

- V1 (Validation): Task claim accepted, proof submitted
- V2 (Verification): Independent verifier confirms proof
- V3 (Valuation): CABR scores the aggregate impact

Only V3-scored work should feed Dao distributions. Everything else feeds Un engagement or is filtered out.

### 5.4 Reciprocal Collusion (INFERRED by directed graph)

- `verify(A→B)` AND `verify(B→A)` in same or adjacent epoch
- Rate exceeds expected pairwise rate by >2σ
- Pattern persists across multiple epochs

### 5.5 Threshold Gaming (INFERRED by boundary analysis)

- Activity within 5% of any threshold is >2σ above participant's non-boundary average
- Activity drops back to average after threshold is crossed
- Pattern repeats across multiple threshold-crossing events

---

## 6. Evidence Standard Applied

| Claim | Status | Source |
|-------|--------|--------|
| Sumo threshold gaming is statistically proven | PROVEN | Duggan & Levitt 2002, confirmed by 2011 police evidence |
| Reciprocity pattern (80%→40%→50%) is proven | PROVEN | Duggan & Levitt 2002, AER |
| Scrutiny disappearance is proven | PROVEN | Duggan & Levitt 2002, media period analysis |
| FoundUps has equivalent threshold structures | PROVEN | `CABR_THRESHOLD`, degressive tiers, staker hurdle in repo code |
| Threshold gaming will occur in FoundUps | INFERRED | Structural incentive equivalence; not yet observed (no live economy) |
| Current sentinel covers all sumo patterns | PROVEN FALSE | `participation_sentinel.py` covers concentration, velocity, Sybil, outliers. Missing: reciprocity, threshold-proximity, scrutiny-sensitivity, ring detection |
| Governance and cross-FoundUp participation terms are live | PROVEN FALSE | Both are hardcoded 0.15 placeholders in `cabr_estimator.py` lines 246–247 |

---

*This mapping provides the analytical model for the Threshold Gaming Sentinel. See: `THRESHOLD_GAMING_SENTINEL_SPEC.md` for the architecture.*
