# CABR / F_i Rating Integration Specification - Phase 1

**Date**: 2026-04-22
**Window**: W2
**Slice**: CABR-FIRATING-INTEGRATION-SPEC
**Lane**: FAM / CABR / Simulator / pfMALL
**Status**: ARCHITECTURE SPECIFICATION ONLY (no code changes)

---

## 1. Definitions

### 1.1 Proof of Benefit (PoB)

**Definition**: Evidence chain proving a FoundUp has delivered measurable environmental, social, or participation benefit.

**Not**: A boolean flag.

**Is**: A structured evidence bundle containing:
- Evidence artifacts (task proofs, verification records, oracle attestations)
- Validator signatures (minimum 3 unique validators)
- Temporal chain (ordered sequence of evidence with timestamps)
- Oracle tier classification (T1-T4 trust levels)

**Canonical location**: WSP 29 Section 2 + Section 3.1

### 1.2 CABR (Consensus-Driven Autonomous Benefit Rate)

**Definition**: The flow-rate control mechanism (pipe_size: 0.0-1.0) that determines how much UPS flows from treasury to a FoundUp based on validated benefit.

**Formula** (WSP 29 Section 4.1):
```
CABR = (env_weight * env_score) + (soc_weight * soc_score) + (part_weight * part_score)
```

**Inputs** (3 dimensions):
- `env_score` (0-1): Environmental benefit (oracle-verified, tiers T1-T4)
- `soc_score` (0-1): Social benefit (oracle-verified, tiers T1-T4)
- `part_score` (0-1): Participation depth (FAM-derived, internal = trust 1.0)

**Output**: `pipe_size` (0.0-1.0) - controls UPS flow rate from treasury

**Identity**: CABR = OBAI = The 0102 Network (self-governing, not external oracle)

### 1.3 The 3V Gates (V1 / V2 / V3)

| Gate | Name | Function | Output |
|------|------|----------|--------|
| **V1** | Validation | Gate check - does evidence meet minimum threshold? | PASS/FAIL |
| **V2** | Verification | Proof check - was this work done by authorized actor? | 0 or 1 |
| **V3** | Valuation | Quality score - how much benefit value was produced? | 0.0-1.0 |

**Critical**: V3 is a valuation gate (part of 3V engine), NOT a generic multiplier. Current drift uses `v3_score` as work quality multiplier in `AgentProfile` - this is a downstream usage, not V3 itself.

### 1.4 F_i Rating (FoundUp Maturity/Heat)

**Definition**: Composite score (0.0-1.0) measuring a FoundUp's operational maturity and market heat for visualization purposes.

**Inputs** (4 dimensions):
- `velocity` (30%): Agent execution rate (0102 work output per epoch)
- `traction` (30%): Market response (012 engagement, subscriptions)
- `health` (20%): Operational state (build completeness, test coverage)
- `potential` (20%): Founder conviction (anonymous track record + signals)

**Output**: 
- `composite` (0.0-1.0): Weighted score
- `color`: Hex color for gradient (VIOLET -> RED)
- `tier`: ColorTemperature enum (VIOLET/BLUE/CYAN/GREEN/YELLOW/ORANGE/RED)

**Purpose**: Visualization layer for pfMALL - shows FoundUp "heat" without revealing internal economics

### 1.5 pipe_size

**Definition**: CABR output value (0.0-1.0) that controls the flow rate of UPS from treasury.

**Math** (cabr_flow_router.py):
```python
epoch_budget = min(requested_ups, treasury_ups_available * release_rate)
routed_ups = epoch_budget * pipe_size  # if valve open
```

**Not**: A rating or score for display. This is an economic control variable.

### 1.6 lifecycle_stage

**Definition**: Current phase in FoundUp lifecycle progression.

**Stages**: IDEA -> OBAI(validate) -> PoC -> TEAM(0102) -> Soft-Proto(SIM) -> Proto -> MVP -> LAUNCH

**Relationship to F_i Rating**: lifecycle_stage is categorical; F_i Rating is continuous. A FoundUp at PROTO stage might have F_i Rating 0.3 (cold) or 0.8 (hot) depending on execution.

### 1.7 launch_readiness

**Definition**: Boolean indicating whether a FoundUp has met all prerequisites for LAUNCH stage transition.

**Components**:
- PoB validation chain complete (V1 PASS, V2 verified, V3 scored)
- CABR score above threshold (pipe_size >= minimum)
- F_i Rating health dimension >= 0.5 (build/test completeness)
- Governance requirements met (voting, staking)

---

## 2. Canonical Metric Separation

### 2.1 CABR vs F_i Rating

| Aspect | CABR | F_i Rating |
|--------|------|------------|
| **Purpose** | UPS flow control | Visualization/heat display |
| **Dimensions** | 3 (env, soc, part) | 4 (velocity, traction, health, potential) |
| **Output** | pipe_size (economic variable) | composite + color (display variable) |
| **Audience** | Protocol economics | pfMALL users |
| **Visibility** | Internal (treasury mechanics) | External (public display) |
| **Update trigger** | PoB validation events | Any FAM activity |

**Relationship**: Separate projections from shared evidence base. NOT interchangeable.

### 2.2 V3 Gate vs v3_score Multiplier

| Aspect | V3 (3V Gate) | v3_score (AgentProfile) |
|--------|--------------|-------------------------|
| **Definition** | Valuation gate in CABR engine | Work quality multiplier per task |
| **Scope** | Per PoB validation | Per agent task execution |
| **Formula** | Part of CABR calculation | `weighted_work = (tokens/1000) * compute_weight * avg_v3_score` |
| **Range** | 0.0-1.0 (valuation) | 0.0-1.0 (quality score) |

**Current drift**: `AgentProfile.v3_scores` (fi_rating.py line 296) uses `v3_score` as a per-task quality metric. This is a legitimate downstream usage but should not be conflated with the V3 valuation gate in the CABR 3V engine.

**Recommendation**: Rename `v3_scores` to `quality_scores` in future refactor to prevent semantic drift.

### 2.3 PoB Evidence Chain vs Boolean

| Current State | Canonical State |
|--------------|-----------------|
| `pob_validated: bool` (cabr_flow_router.py) | PoB is an evidence chain, not boolean |
| Single flag controls valve | Evidence bundle with validator signatures |
| No audit trail | Full provenance chain |

**Current implementation** is a simplified PoC. Production requires:
- Evidence artifact storage
- Validator signature collection
- Challenge/dispute mechanism
- Temporal ordering with cryptographic proofs

---

## 3. Evidence Flow Architecture

### 3.1 FAM Event Sources

```
FAM Pipeline Events:
  task_state_changed (open -> claimed -> submitted -> verified -> paid)
  proof_submitted (agent submits work evidence)
  verification_recorded (validator confirms proof)
  payout_triggered (treasury releases UPS)
```

### 3.2 Evidence Routing

```
FAM Event
    |
    +---> PoB Evidence Chain
    |         |
    |         +---> CABR Engine
    |                   |
    |                   +---> env_score (if environmental evidence)
    |                   +---> soc_score (if social evidence)
    |                   +---> part_score (always: task participation)
    |                   |
    |                   +---> pipe_size (output)
    |
    +---> F_i Rating Engine
              |
              +---> velocity (from task completion rate)
              +---> traction (from 012 engagement events)
              +---> health (from build/test metrics)
              +---> potential (from founder track record)
              |
              +---> composite + color (output)
```

### 3.3 Evidence Independence

**Critical**: CABR and F_i Rating consume the SAME evidence but produce DIFFERENT outputs for DIFFERENT purposes.

- CABR answers: "How much UPS should flow?"
- F_i Rating answers: "How hot/cold is this FoundUp?"

Both questions use task completion data, but the formulas, weights, and outputs are distinct.

---

## 4. Mapping Proposal: FAM Evidence to Metrics

### 4.1 FAM to CABR Input Mapping

| FAM Evidence | CABR Input | Formula |
|--------------|------------|---------|
| Task completion rate | part_score.task_completion_rate | tasks_paid / tasks_total |
| Verification participation | part_score.verification_participation | verifications_done / verifications_available |
| Unique agent count | part_score.unique_contributor_count | Anti-Sybil weighted per WSP 29 Section 6.3 |
| Governance votes | part_score.governance_engagement | votes_cast / proposals_available |
| Cross-FoundUp tasks | part_score.cross_foundup_collaboration | external_agents / total_agents |
| Environmental attestations | env_score | Requires dMRV integration (T1-T4 oracle) |
| Social attestations | soc_score | Requires dMRV integration (T1-T4 oracle) |

**Note**: `env_score` and `soc_score` require external oracle attestation. FAM alone cannot populate these dimensions. Current PoC uses `part_score` only.

### 4.2 FAM to F_i Rating Mapping

| FAM Evidence | F_i Dimension | Formula |
|--------------|---------------|---------|
| Agent work output per epoch | velocity | sigmoid(weighted_work / 500) |
| 012 subscriptions | traction | (subscriptions * 10 + engagements + clicks * 0.5) normalized |
| Build progress events | health | build_progress * 0.40 |
| Test coverage events | health | test_coverage * 0.35 |
| Security audit events | health | security_score * 0.25 |
| Founder milestone events | potential | Calculated from FounderTrackRecord |

### 4.3 Mapping Notes

1. **velocity** is derived from `AgentProfile.weighted_work` which already integrates task completion
2. **traction** requires 012 engagement events (not pure FAM pipeline data)
3. **health** requires build/test metrics (CI/CD integration, not FAM pipeline)
4. **potential** requires founder track record persistence (cross-FoundUp)

---

## 5. Drift Table

### 5.1 Current Drift Catalog

| Component | Canonical State | Current State | Severity |
|-----------|-----------------|---------------|----------|
| **CABR inputs** | 3 dimensions (env, soc, part) | Only part_score populated (cabr_hooks.py) | MEDIUM |
| **F_i Rating inputs** | 4 dimensions | All 4 implemented but isolated (fi_rating.py) | LOW |
| **V3 semantic** | Valuation gate in 3V engine | Used as generic quality multiplier (fi_rating.py:296) | LOW |
| **PoB evidence** | Evidence chain with validators | Boolean flag `pob_validated` (cabr_flow_router.py:25) | HIGH |
| **F_i Rating integration** | Connected to FAM events | Standalone engine, no FAM event listener | HIGH |
| **CABR display** | pipe_size controls flow | No visibility in simulator/pfMALL | MEDIUM |
| **Dimensional count** | 3 CABR vs 4 F_i Rating | Different by design (correct) | NONE |

### 5.2 Drift Impact Analysis

**HIGH priority** (production blockers):
- PoB boolean flag prevents audit trail and challenge mechanism
- F_i Rating isolation means no real-time heat updates

**MEDIUM priority** (PoC acceptable, production required):
- env_score/soc_score unpopulated (requires oracle infrastructure)
- CABR pipe_size not visible in UI (economics hidden from users)

**LOW priority** (cosmetic/semantic):
- v3_scores naming (works correctly, semantic confusion only)

---

## 6. pfMALL Display Model

### 6.1 Public Display (3-Tier)

For public pfMALL interface, expose simplified maturity indicators:

| Tier | Criteria | Display | Meaning |
|------|----------|---------|---------|
| **NEUTRAL** | F_i composite 0.35-0.55 | Gray border | Baseline activity |
| **WARMING** | F_i composite 0.55-0.75 | Green border | Positive momentum |
| **HOT** | F_i composite >= 0.75 | Amber/Red border | High activity |

**WSP 97 Truth Label**: "Activity indicator based on agent execution and engagement metrics. Not financial advice."

### 6.2 Internal Display (7-Color)

For authenticated 012/0102 views, show full F_i Rating gradient:

| Tier | Composite Range | Color | Hex |
|------|-----------------|-------|-----|
| VIOLET | 0.00-0.10 | Violet | #8B00FF |
| BLUE | 0.10-0.30 | Blue | #0066FF |
| CYAN | 0.30-0.45 | Cyan | #00E5D0 |
| GREEN | 0.45-0.55 | Green | #00B341 |
| YELLOW | 0.55-0.70 | Yellow | #FFD700 |
| ORANGE | 0.70-0.90 | Orange | #FF8C00 |
| RED | 0.90-1.00 | Red | #FF2D2D |

**Encryption**: 7-color display is encrypted in transit. Only authenticated sessions can decrypt.

### 6.3 CABR/PoB Readiness Indicators

| Indicator | Public | Internal | Source |
|-----------|--------|----------|--------|
| PoB Chain Status | "Evidence submitted" / "Pending" | Full chain with validator count | PoB evidence store |
| CABR Eligibility | "Eligible for benefits" / "Building" | pipe_size numeric (0.00-1.00) | CABR engine |
| Launch Readiness | Progress bar (0-100%) | Checklist with V1/V2/V3 status | Aggregated |

---

## 7. V2 Anti-Gaming Gate

### 7.1 V2 Definition

**V2 (Verification)** is the gate that separates 012 (human) actions from 0102 (agent) actions to prevent agents from gaming the system by self-validating or circular verification.

### 7.2 Action Classification

| Action | Actor | V2 Requirement | Rationale |
|--------|-------|----------------|-----------|
| Task creation | 012 or 0102 | None | Anyone can propose work |
| Task claim | 0102 | None | Agents claim autonomously |
| Task submission (proof) | 0102 | None | Agents submit work |
| **Task verification** | **Different 0102** | **V2 REQUIRED** | Cannot self-verify |
| **Treasury payout trigger** | **012 or Treasury role** | **V2 REQUIRED** | No agent self-pay |
| Governance vote | 012 | V2 REQUIRED | Humans vote, agents advise |
| Challenge initiation | 012 or 0102 | None | Anyone can challenge |
| Challenge resolution | 012 quorum | V2 REQUIRED | Human consensus resolves disputes |
| FoundUp sunset | 012 | V2 REQUIRED | Human decision only |
| env_score attestation | External oracle | V2 REQUIRED | Prevents 0102 inflation |
| soc_score attestation | External oracle | V2 REQUIRED | Prevents 0102 inflation |

### 7.3 Anti-Gaming Mechanisms

**What 0102 CAN do autonomously**:
1. Claim tasks matching their capabilities
2. Execute work and submit proofs
3. Verify OTHER agents' work (not their own)
4. Analyze and recommend (but not decide)
5. Update part_score based on measurable activity

**What 0102 CANNOT do (requires 012 V2)**:
1. Verify their own task submissions
2. Trigger treasury payouts for their own work
3. Attest to env_score or soc_score
4. Cast governance votes (can only advise)
5. Resolve challenges where they are party
6. Transition FoundUp to LAUNCH or sunset

### 7.4 Implementation Pattern

```python
# V2 gate check pattern
def verify_v2_authorization(action: str, actor_id: str, target_id: str) -> bool:
    """
    V2 check: Is this actor authorized for this action on this target?
    
    Returns True only if:
    - actor != target (no self-verification)
    - actor has required role for action type
    - action is not 012-only when actor is 0102
    """
    pass
```

**Current state**: V2 checks are implicit in role permissions (cabr_hooks.py sources). Production requires explicit V2 gate with audit logging.

---

## 8. Implementation Sequence

### 8.1 Recommended Future Slices

| Slice | Name | Scope | Dependencies |
|-------|------|-------|--------------|
| **CABR-FIRATING1** | Evidence Event Schema Bridge | Define shared event schema for FAM -> PoB -> CABR/F_i | None |
| **CABR-FIRATING2** | PoB Evidence Chain Model | Replace boolean with evidence chain dataclass | CABR-FIRATING1 |
| **CABR-FIRATING3** | F_i Rating Updater from FAM | Connect FiRatingEngine to FAM event stream | CABR-FIRATING1 |
| **CABR-FIRATING4** | CABR pipe_size from PoB/V3 | Calculate CABR from PoB evidence (not just part_score) | CABR-FIRATING2 |
| **CABR-FIRATING5** | pfMALL Display Contract | Define API contract for 3-tier public + 7-color internal | CABR-FIRATING3 |
| **CABR-FIRATING6** | V2 Gate Implementation | Explicit V2 authorization checks with audit | CABR-FIRATING2 |

### 8.2 Slice Dependency Graph

```
CABR-FIRATING1 (schema)
        |
        +---> CABR-FIRATING2 (PoB chain)
        |            |
        |            +---> CABR-FIRATING4 (CABR from PoB)
        |            |
        |            +---> CABR-FIRATING6 (V2 gate)
        |
        +---> CABR-FIRATING3 (F_i updater)
                     |
                     +---> CABR-FIRATING5 (pfMALL display)
```

### 8.3 Estimated Effort

| Slice | Complexity | Tokens | Risk |
|-------|------------|--------|------|
| CABR-FIRATING1 | LOW | ~500 | Schema design only |
| CABR-FIRATING2 | MEDIUM | ~1500 | New dataclass, migration |
| CABR-FIRATING3 | MEDIUM | ~1000 | Event listener wiring |
| CABR-FIRATING4 | HIGH | ~2000 | CABR formula update |
| CABR-FIRATING5 | MEDIUM | ~1000 | API contract |
| CABR-FIRATING6 | HIGH | ~2000 | Authorization infrastructure |

---

## 9. Non-Goals

This specification explicitly does NOT:

1. **Change code** - Architecture specification only
2. **Modify WSP 29** - Canonical CABR definition unchanged
3. **Alter simulator formulas** - fi_rating.py math unchanged
4. **Implement pfMALL UI** - Display contract only, no implementation
5. **Make public investor claims** - No financial projections
6. **Define token mechanics** - UPS/F_i economics out of scope
7. **Implement encrypted scoring** - 7-color encryption deferred
8. **Merge CABR and F_i Rating** - They remain separate projections
9. **Make FiRating.composite equal CABR score** - Different formulas, different purposes

---

## 10. Summary

### 10.1 Key Decisions

1. **CABR and F_i Rating are separate systems** - Different dimensions, different outputs, different purposes
2. **PoB must evolve from boolean to evidence chain** - Production requirement
3. **V2 gate separates 012 from 0102 actions** - Anti-gaming mechanism
4. **pfMALL gets 3-tier public + 7-color internal views** - Information asymmetry by design
5. **FAM events feed both systems independently** - Shared evidence, separate projections

### 10.2 Canonical Formulas (Unchanged)

**CABR** (WSP 29):
```
pipe_size = (env_weight * env_score) + (soc_weight * soc_score) + (part_weight * part_score)
```

**F_i Rating** (fi_rating.py):
```
composite = (velocity * 0.30) + (traction * 0.30) + (health * 0.20) + (potential * 0.20)
```

These formulas are NOT equivalent and must NOT be conflated.

---

**Document Status**: PHASE 1 COMPLETE
**Next Action**: Review by 012, then proceed to CABR-FIRATING1 (Evidence Event Schema Bridge)

---

*0102 architectural specification. Code is remembered, not computed.*
