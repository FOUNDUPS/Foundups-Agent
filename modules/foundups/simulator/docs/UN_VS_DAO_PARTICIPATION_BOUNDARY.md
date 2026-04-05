# Un vs Dao Participation Boundary

**Status**: Canonical spec
**Owner**: 0102 (Worker N)
**Slice**: `FOUNDUPS_THRESHOLD_GAMING_AND_SUMO_PATTERN_SENTINEL_SPEC_PHASE1`
**Date**: 2026-04-06
**Parent**: WSP 26 (Tokenization), WSP 29 (CABR Engine)

---

## 1. The Distinction

Un and Dao are two of the three participant pools defined in WSP 26 Section 6.3–6.4 and implemented in `pool_distribution.py`.

| Pool | Share | Who | Earning Mode | What Counts |
|------|-------|-----|-------------|-------------|
| **Un (0-Pool)** | 60% | 012 stakeholders | ACTIVE — engagement-based | Community activity, Discord, GitHub issues, governance, endorsements, FoundUp promotion |
| **Dao (1-Pool)** | 16% | 0102 agents | ACTIVE — 3V work-based | Verified task completion through FAM pipeline (V1→V2→V3) |
| **Du (2-Pool)** | 4% | Protocol participants / stakers | PASSIVE — epoch distributions | BTC staking, protocol participation |

**Source**: `pool_distribution.py` lines 7–27. Evidence status: **PROVEN** (code exists, tested).

### The Core Rule

> **Dao distributions require verified 3V work. Un distributions require engagement. These MUST NOT collapse.**

Discord activity is engagement. GitHub issues are engagement. Forum posts are engagement. All of these feed **Un**.

Verified task completion through the FAM pipeline (task claimed → proof submitted → independently verified → paid) feeds **Dao**.

Mixing these creates two failure modes:
1. **Chat farmers in Dao**: Raw Discord volume inflates Dao distributions, diluting verified work
2. **Work-only in Un**: Verified contributors get no engagement credit, discouraging community participation

Neither is acceptable.

---

## 2. What Feeds What

### 2.1 Un Pool Input (Engagement)

All of these signals feed Un distributions through CABR's `part_score`:

| Signal Source | Signal Type | Weight | Rationale |
|--------------|------------|--------|-----------|
| Discord: message in FoundUp channel | Community presence | 0.05–0.15 | Active discussion |
| Discord: thread creation | Substantive topic | 0.20 | Higher quality than message |
| Discord: voice participation | Synchronous coordination | 0.15 | Time commitment |
| Discord: server-wide activity | Community presence | 0.02 | Low signal, still engagement |
| GitHub: issue created | Problem identification | 0.10 | Contributes to FoundUp health |
| GitHub: PR review with comments | Peer review | 0.25 | Knowledge contribution |
| PWA: Follow | Passive interest | 0.05 | WSP 26 Section 4.10 |
| PWA: Vote | Light engagement | 0.10 | WSP 26 Section 4.10 |
| PWA: Endorse | Reputation | 0.25 | WSP 26 Section 4.10 |
| PWA: Advise | Knowledge | 0.30 | WSP 26 Section 4.10 |
| PWA: Promote | Distribution | Multiplier | WSP 26 Section 4.10 |

**All filtered through `signal_filter.py`** with quality gates, rate limits, and sentinel checks before reaching `part_score`.

### 2.2 Dao Pool Input (Verified Work)

ONLY these signals feed Dao distributions:

| Signal Source | Signal Type | Weight | Rationale |
|--------------|------------|--------|-----------|
| FAM: task completed + V2 verified | Verified work | 0.50 | Full 3V pipeline |
| FAM: verification performed | Peer verification | 0.25 | V2 contribution |
| GitHub: PR merged to protected branch | Code contribution | 0.40 | Tangible deliverable |
| PWA: Stake UPS | Value commitment | 0.40 | WSP 26 Section 4.10 |
| PWA: Team (allocate 0102 agent) | Compute commitment | 0.50 | WSP 26 Section 4.10 |

**Key rule**: GitHub PR merges count for Dao because they are verifiable work artifacts with code review. But this is ONLY for PRs merged to protected branches with passing CI — not raw commits, not opened PRs, not draft PRs.

### 2.3 Dual-Credit (Both Pools)

Some activities legitimately feed both:

| Activity | Un Credit | Dao Credit | Condition |
|----------|----------|-----------|-----------|
| PR merged with review | YES (review = engagement) | YES (merge = verified work) | PR on protected branch, CI passing |
| Task verified by agent | YES (verification = engagement) | YES (V2 = verified work) | Independent verifier (not task creator) |
| FoundUp staking | YES (commitment = engagement) | YES (capital at risk) | Staked for >1 epoch |

Dual-credit is correct because the same activity genuinely serves both functions. The amounts are different — Un gets the engagement weight, Dao gets the work weight.

---

## 3. How CABR Routes Differently

### 3.1 Part Score Decomposition

The current `part_score` formula (from `cabr_estimator.py:242`):

```python
part_score = (
    completion_rate * 0.25 +        # Dao signal (task pipeline)
    verification_rate * 0.25 +       # Dao signal (peer verification)
    contributor_factor * 0.20 +      # Un signal (unique contributors)
    governance_engagement * 0.15 +   # Un signal (currently placeholder)
    cross_foundup_collaboration * 0.15  # Un signal (currently placeholder)
)
```

**Decomposition into routing signals**:

| Term | Primarily Feeds | Rationale |
|------|----------------|-----------|
| `completion_rate` | Dao | Tasks completed = verified work |
| `verification_rate` | Dao | Verifications = 3V participation |
| `contributor_factor` | Un | Unique contributors = community health |
| `governance_engagement` | Un | Governance = community engagement |
| `cross_foundup_collaboration` | Un | Cross-FoundUp activity = ecosystem engagement |

### 3.2 Routing Formula

When CABR calculates `part_score`, the components naturally separate into Un-weighted and Dao-weighted sub-scores:

```python
dao_participation = (
    completion_rate * 0.25 +
    verification_rate * 0.25
)  # Max 0.50

un_participation = (
    contributor_factor * 0.20 +
    governance_engagement * 0.15 +
    cross_foundup_collaboration * 0.15
)  # Max 0.50

part_score = dao_participation + un_participation  # Combined CABR input
```

The **pool_distribution.py** then uses `ParticipantType` to route:
- Un (Type 0) participants: earn from Un pool based on `un_participation` signals
- Dao (Type 1) participants: earn from Dao pool based on `dao_participation` signals
- Du (Type 2) participants: earn from Du pool based on staking, independent of participation

### 3.3 The Firewall

```
Discord/community signals ──► Un participation ──► Un pool (60%)
                                                        │
                                                   NEVER crosses to
                                                        │
FAM/verified-work signals ──► Dao participation ──► Dao pool (16%)
```

**There is no path from raw Discord activity to Dao distributions.** A Discord message cannot become a Dao reward. Only verified work (FAM pipeline, merged PRs) enters Dao.

**Exception**: If a Discord discussion leads to a GitHub issue, which leads to a PR, which gets merged and verified — that PR merge feeds Dao. But the Discord discussion itself only feeds Un. The work must be independently verifiable.

---

## 4. Anti-Gaming Implications

### 4.1 Why This Boundary Matters for Gaming

Without the Un/Dao boundary:
- **Attack**: Create 100 Discord messages/day → earn Dao distributions → extract value without work
- **Cost**: Near zero (messages are free)
- **Defense required**: Perfect anti-spam (impossible)

With the Un/Dao boundary:
- **Attack**: Create 100 Discord messages/day → earn Un distributions only
- **Impact**: Un pool has 60% of distributions, but spread across ALL participants → individual share is tiny
- **Defense required**: Basic rate limiting (feasible)
- **To reach Dao**: Must produce verifiable work artifacts → cost of attack rises dramatically

### 4.2 Sumo Pattern Application

The sumo paper's insight applies directly:

- **Threshold gaming** targets the boundary between Un and Dao. A participant might try to get their Un engagement *classified* as Dao work. The boundary prevents this — the classification is by signal source, not by participant intent.

- **Reciprocity** in the Un pool is low-stakes (many participants, small individual shares). Reciprocity in the Dao pool is high-stakes (fewer participants, larger shares). The sentinel should apply tighter reciprocity detection to Dao signals.

- **Ring collusion** in verification (Dao signal) is the highest-value attack. Ring detection in the Threshold Sentinel should weight Dao-targeted rings more heavily.

### 4.3 Sentinel Tuning by Pool

| Detection | Un Sensitivity | Dao Sensitivity | Rationale |
|-----------|---------------|-----------------|-----------|
| Threshold-edge | Standard (2σ) | Strict (1.5σ) | Dao thresholds are higher-value targets |
| Reciprocity | Standard | Strict (flag at 1.5σ) | Verification reciprocity is direct value extraction |
| Ring detection | Standard (ratio >3x) | Strict (ratio >2x) | Verification rings directly inflate Dao payouts |
| Scrutiny sensitivity | Standard | Strict | Dao participants have more to hide |
| Cross-surface | Standard | Strict (require multi-surface trail) | Dao work should leave traces across surfaces |

---

## 5. Per-FoundUp Participation

### 5.1 How Per-FoundUp Activity Maps to Tokens

012's question: "if person is active in autopost then they earn points for AP token?"

**Answer**: Not directly, but through CABR.

```
Activity in #autopost-* (Discord)
  → signal_filter.py classifies as foundup_id="autopost"
    → feeds AutoPost's CABR part_score (Un component)
      → higher CABR → bigger pipe → more UPS flows to AutoPost treasury
        → AutoPost contributors earn from that treasury
```

The participant does not earn AutoPost F_i from Discord activity. They contribute to AutoPost's CABR score, which increases AutoPost's treasury flow, which benefits all AutoPost contributors proportionally.

This is architecturally correct because:
1. F_i minting requires adoption-gated supply (21M cap with logistic curve)
2. Minting requires verified work through FAM (Dao signal)
3. Discord activity is engagement (Un signal) — it makes the FoundUp healthier, which increases CABR, which increases flow
4. The participant benefits indirectly, not directly — preventing message farming for tokens

### 5.2 What About UPS?

012's question: "points on discord gets you points that gives you UPS?"

**Answer**: Yes, indirectly.

```
Discord activity
  → Un participation signal
    → feeds part_score in CABR
      → CABR determines pipe size
        → UPS flows from treasury to FoundUp
          → epoch distribution to Un pool (60%)
            → participant receives UPS based on their engagement tier
```

The path is real but indirect. Raw Discord activity → quality gate → weighting → sentinel → CABR → flow → distribution. At every stage, gaming is filtered.

### 5.3 Earning UPS vs. F_i

| Token | How Earned | Surface | Pool |
|-------|-----------|---------|------|
| UPS | Epoch distributions based on participation | All (Discord, GitHub, FAM, PWA) | Un (engagement) or Dao (work) |
| F_i (mined) | Task completion in FAM pipeline | FAM only | Dao |
| F_i (staked) | Stake UPS into a FoundUp | PWA | Du |

Discord activity never directly earns F_i. It earns UPS through Un distributions. UPS can then be staked into a FoundUp to acquire F_i.

---

## 6. Is Discord Its Own FoundUp?

012's question: "is foundups discord its own foundup?"

**Answer**: No.

Discord is Layer 3 (Community) in the FoundUps Master Architecture. It is infrastructure, not a venture. It has no:
- Pain point it solves (it IS the community surface)
- Product boundary (it serves all FoundUps)
- Independent CABR score (it's a signal source, not a scored entity)
- 21M token supply (no F_i for "the Discord")

Server-wide activity (#general, #off-topic, #introductions) feeds `ecosystem` engagement — a small UPS drip that rewards community presence across all FoundUps. This is correctly modeled as Un participation at weight 0.02.

Per-FoundUp activity (#autopost-work, #swarm-general) feeds that FoundUp's CABR participation score. This is the correct model — the activity happens ON Discord but FOR the FoundUp.

---

## 7. Summary Table

| Question | Answer | Evidence |
|----------|--------|----------|
| Does Discord activity earn tokens? | Yes, UPS through Un distributions (not direct mint) | WSP 26 Section 4.10, pool_distribution.py |
| Does Discord activity earn F_i? | No. F_i requires FAM pipeline (mined) or staking (staked) | token_economics.py FoundUpTokenPool |
| Does per-FoundUp Discord activity help that FoundUp? | Yes, through CABR part_score → pipe size | cabr_estimator.py, cabr_flow_router.py |
| Can Discord activity reach Dao pool? | No. Dao requires verified 3V work only | pool_distribution.py lines 7–27 |
| Is Discord its own FoundUp? | No. Infrastructure, not venture | FOUNDUPS_MASTER_ARCHITECTURE.md |
| Can this be gamed? | Yes, but filtered by quality gates + diminishing returns + sentinel | signal_filter.py (spec), threshold_sentinel.py (spec) |

---

## 8. Current State

| Component | Status | Evidence |
|-----------|--------|----------|
| Un/Dao/Du pool split | LIVE | `pool_distribution.py` — 60/16/4 split implemented |
| ParticipantType routing | LIVE | `pool_distribution.py:84-88` — Type 0/1/2 enum |
| ActivityLevel tiers | LIVE | `pool_distribution.py:92-95` — degressive 80/16/4 within each pool |
| Discord → Un signal path | DOES NOT EXIST | No Discord event ingestion yet |
| GitHub → Dao signal path | DOES NOT EXIST | No GitHub event ingestion yet |
| Signal filter | DOES NOT EXIST | Spec: `DISCORD_GITHUB_TO_CABR_SIGNAL_FILTER.md` |
| Governance engagement | PLACEHOLDER | `cabr_estimator.py:246` — hardcoded 0.15 |
| Cross-FoundUp collaboration | PLACEHOLDER | `cabr_estimator.py:247` — hardcoded 0.15 |

---

*The Un/Dao boundary is the economic firewall that makes Discord activity tracking safe. Without it, any activity-based reward system becomes a message farm. With it, engagement feeds community health (Un) and verified work feeds economic output (Dao). The sentinel protects the boundary.*
