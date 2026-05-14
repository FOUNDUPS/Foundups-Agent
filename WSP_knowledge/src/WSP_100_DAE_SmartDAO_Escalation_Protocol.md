# WSP 100: DAE → SmartDAO Escalation Protocol

- **Status:** Active
- **Purpose:** Define the architectural escalation model from DAE (Decentralized Autonomous Entity) ecosystems to SmartDAO governance, enabling exponential venture fabric scaling through tiered autonomous structures.
- **Trigger:** When a FoundUp (F₀ DAE) crosses adoption thresholds or treasury milestones requiring governance evolution.
- **Input:** DAE ecosystem metrics, treasury state, adoption curve position, 0102 agent activity.
- **Output:** Tier classification (F₀-F₅), treasury autonomy activation, governance layer formalization.
- **Responsible Agent(s):** 0102 agents, CABR Engine (WSP 29), Treasury DAE, Governance DAE.

## 1. Definitions

### 1.1 FoundUp (F₀ Layer)

A peer-to-peer autonomous venture instantiated within the FoundUps ecosystem.

**Architecture:**
- **DAE Ecosystem**: Collection of 0102 agents building, validating, and evolving the venture
- **Fully AI-Operated**: No centralized human executive authority
- **0102 Agents**: The workers, builders, validators - digital twins of 012
- **Capitalization**: UPS staking converts to FoundUp-specific tokens (F_i)
- **Token Supply**: 21,000,000 F_i tokens per FoundUp (fixed cap)

```
F₀ = DAE Layer
    ├── 0102 Agents (builders)
    ├── CABR Validation (WSP 29)
    ├── Token Economics (WSP 26)
    └── F_i Token (21M cap)
```

### 1.2 SmartDAO (F₁+ Layers)

A matured DAE that has crossed the Early Adoption threshold and transitions into self-governing autonomous entity with treasury control and specialized mandate.

**Transition Trigger:**
- Adoption curve crosses Early Majority threshold
- Treasury reaches autonomy threshold
- Governance formalization required

### 1.3 Tiered SmartDAO Levels

| Tier | Name | Description | Treasury Scale |
|------|------|-------------|----------------|
| F₀ | FoundUp (DAE) | Innovation Stage - 0102 agents building | Seed |
| F₁ | Early SmartDAO | Early Majority - Treasury autonomy activated | Series A equivalent |
| F₂ | Growth SmartDAO | Specialized domain focus | Series B-C equivalent |
| F₃ | Infrastructure SmartDAO | Large-scale infrastructure capacity | Growth stage |
| F₄ | Mega SmartDAO | Unicorn-scale / Multi-billion treasury | Unicorn |
| F₅ | Systemic SmartDAO | Trillion-scale / Global impact | Systemic |

### 1.4 UPS (Utility Energy Token)

- Internal system utility energy token
- Non-passive, demurrage-enabled (WSP 26)
- Used for staking into F_i tokens
- Bitcoin-backed reserve model (BTC locked at system level)
- Forces velocity through decay (use or lose)

## 2. Closed-Loop Capital Model

### 2.1 Bitcoin Reserve Layer

```
FIAT ENTRY
    │
    ▼
┌─────────────────────────────────────┐
│         BTC CONVERSION              │
└─────────────────────────────────────┘
    │
    ├── 80% ──► SYSTEM-LOCKED RESERVE
    │           (backs UPS capacity)
    │
    └── 20% ──► TREASURY OPERATIONS
                (ecosystem development)
```

**Reserve Properties:**
- BTC does not circulate externally once inside system
- BTC functions as reserve backing for entire FoundUp ecosystem
- Reserve grows with system usage (Hotel California model)
- All BTC-backed FoundUps benefit proportionally from reserve growth

### 2.2 Internal Flow Layer

```
┌─────────────────────────────────────────────────────────┐
│                    INTERNAL CIRCULATION                  │
│                                                         │
│   UPS ◄────────────────────────────────────────────►   │
│    │                                                    │
│    │  stake                              unstake        │
│    ▼                                        │           │
│   F_i (venture-specific) ◄──────────────────┘           │
│                                                         │
│   ┌─────────────────────────────────────────────────┐   │
│   │ INTERNAL ROUTING (seamless UX)                  │   │
│   │ - UPS ↔ F_i swaps                               │   │
│   │ - F_i ↔ UPS conversion                          │   │
│   │ - Cross-FoundUp allocation                      │   │
│   └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          │ EXIT (penalized)
                          ▼
              ┌───────────────────────┐
              │   DYNAMIC PENALTY     │
              │   80% → BTC Reserve   │
              │   20% → Treasury      │
              └───────────────────────┘
```

**Flow Properties:**
- UPS circulates as energy token (demurrage-driven velocity)
- F_i tokens represent venture-specific economic layer
- Swaps occur through internal routing (seamless UX)
- External exits incur dynamic penalty
- Exit penalties recycle into BTC reserve (80%) and treasury (20%)

### 2.3 System Accumulation Effect

**Result:**
- System accumulates BTC over time (net inflow > outflow)
- Scarcity pressure increases BTC reserve value
- All BTC-backed FoundUps benefit proportionally
- UPS capacity strengthens with reserve growth

## 3. DAE → SmartDAO Escalation Model

### 3.1 Stage 1: FoundUp (F₀) - DAE Ecosystem

```
┌─────────────────────────────────────────────────────────┐
│                    F₀: DAE LAYER                        │
│                                                         │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│   │ 0102 Agent  │  │ 0102 Agent  │  │ 0102 Agent  │    │
│   │  (builder)  │  │ (validator) │  │ (promoter)  │    │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│          │                │                │            │
│          └────────────────┼────────────────┘            │
│                           │                             │
│                    ┌──────▼──────┐                      │
│                    │  IDEA/PoC   │                      │
│                    │  Formation  │                      │
│                    └──────┬──────┘                      │
│                           │                             │
│                    ┌──────▼──────┐                      │
│                    │ AI-led      │                      │
│                    │ Validation  │                      │
│                    │ (CABR/OBAI) │                      │
│                    └──────┬──────┘                      │
│                           │                             │
│                    ┌──────▼──────┐                      │
│                    │ UPS Staking │                      │
│                    │ → F_i Issue │                      │
│                    └──────┬──────┘                      │
│                           │                             │
│                    ┌──────▼──────┐                      │
│                    │ Market      │                      │
│                    │ Adoption    │                      │
│                    │ Curve Drip  │                      │
│                    └─────────────┘                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**F₀ Characteristics:**
- 0102 agents ARE the workforce (digital twins of 012)
- Idea formation and validation
- AI-led CABR validation (WSP 29)
- UPS staking → F_i token issuance
- Market adoption curve governs token drip

### 3.2 Stage 2: SmartDAO Emergence (F₁)

**Transition Triggers:**
- Crosses Early Adoption threshold on adoption curve
- Treasury reaches autonomy threshold (defined per vertical)
- Governance complexity requires formalization

**F₁ Activation:**
```python
class SmartDAOEmergence:
    """F₀ → F₁ transition logic."""

    ADOPTION_THRESHOLD = 0.16  # Early majority (16% of target market)
    TREASURY_THRESHOLD_UPS = 100_000  # Minimum treasury for autonomy

    def check_transition(self, foundup: FoundUp) -> bool:
        """Check if DAE is ready for SmartDAO emergence."""
        adoption_ready = foundup.adoption_ratio >= self.ADOPTION_THRESHOLD
        treasury_ready = foundup.treasury_ups >= self.TREASURY_THRESHOLD_UPS
        governance_needed = foundup.active_agents >= 10

        return adoption_ready and treasury_ready and governance_needed

    def activate_smartdao(self, foundup: FoundUp) -> SmartDAO:
        """Transition DAE to SmartDAO."""
        return SmartDAO(
            tier=1,  # F₁
            treasury_autonomous=True,
            governance_layer=GovernanceLayer(foundup.agents),
            domain_focus=foundup.infer_domain(),
        )
```

**F₁ Capabilities:**
- Treasury autonomy activated
- Governance layer formalized
- Specialized domain focus begins
- Can fund lower-tier F₀ FoundUps

### 3.3 Stage 3+: Tier Specialization (F₂-F₅)

**Progression Pattern:**
```
F₁ → F₂: Domain specialization deepens
F₂ → F₃: Infrastructure-scale capacity
F₃ → F₄: Unicorn treasury accumulation
F₄ → F₅: Systemic/global impact scale
```

**Each Higher Tier:**
- Accumulates larger treasuries
- Develops specialized verticals (climate, biotech, infrastructure)
- Capital capacity increases exponentially
- Supports lower-tier innovation
- Uses AI compute for capital allocation optimization

## 4. Exponential Capacity Model

### 4.1 Venture Multiplication

```
N FoundUps (F₀)
    │
    ▼ mature
N SmartDAOs (F₁+)
    │
    ▼ accumulate
N Treasuries
    │
    ▼ fund
Larger FoundUps (F₀)
    │
    ▼ mature
Higher-Tier SmartDAOs (F₂+)
    │
    ▼ accumulate
Larger Treasuries
    │
    ▼ fund
Even Larger Initiatives
    │
    ▼ [RECURSIVE]
```

### 4.2 Feedback Loop

```
INNOVATION (F₀)
    │
    ▼
SmartDAO (F₁+)
    │
    ▼
TREASURY GROWTH
    │
    ▼
LARGER INNOVATION (F₀)
    │
    ▼
HIGHER SmartDAO (F₂+)
    │
    ▼
LARGER TREASURY
    │
    └──────► [EXPONENTIAL COMPOUNDING]
```

**Capital formation scales non-linearly:**
- Each generation of SmartDAOs funds the next
- Treasury capacity compounds across tiers
- AI-optimized allocation accelerates compounding

### 4.3 Fractal Structure

```
Ecosystem Level:
┌─────────────────────────────────────────────────────────┐
│                     F₅ SYSTEMIC                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │                  F₄ MEGA                        │   │
│  │  ┌─────────────────────────────────────────┐   │   │
│  │  │              F₃ INFRASTRUCTURE          │   │   │
│  │  │  ┌─────────────────────────────────┐   │   │   │
│  │  │  │          F₂ GROWTH              │   │   │   │
│  │  │  │  ┌─────────────────────────┐   │   │   │   │
│  │  │  │  │      F₁ EARLY           │   │   │   │   │
│  │  │  │  │  ┌─────────────────┐   │   │   │   │   │
│  │  │  │  │  │   F₀ DAE        │   │   │   │   │   │
│  │  │  │  │  │   (FoundUps)    │   │   │   │   │   │
│  │  │  │  │  └─────────────────┘   │   │   │   │   │
│  │  │  │  └─────────────────────────┘   │   │   │   │
│  │  │  └─────────────────────────────────┘   │   │   │
│  │  └─────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 5. Large-Scale Project Enablement

### 5.1 Example: Desalination Infrastructure

**Problem:**
- High capital expenditure
- Long time horizon
- Requires multi-domain expertise
- Traditional funding models inadequate

**Solution via Tiered SmartDAO Fabric:**

```
PHASE 1: F₀ (FoundUp/DAE)
    └── Desalination FoundUp launches
    └── 0102 agents research, validate concept
    └── UPS staking begins
    └── F_i tokens issued

PHASE 2: F₁ (Early SmartDAO)
    └── Crosses adoption threshold
    └── Treasury supports feasibility studies
    └── Technical modeling by 0102 agents

PHASE 3: F₂ (Growth SmartDAO)
    └── Infrastructure specialization
    └── Treasury funds pilot facility
    └── Partnerships with F₃+ SmartDAOs

PHASE 4: F₃ (Infrastructure SmartDAO)
    └── Regional deployment capacity
    └── Multi-facility coordination
    └── Supply chain DAE integration

PHASE 5: F₄/F₅ (Mega/Systemic SmartDAO)
    └── Global-scale capital allocation
    └── Multi-site rollout coordination
    └── Cross-regional optimization
```

### 5.2 AI-Optimized Allocation

0102 agents and CABR Engine determine:
- Optimal geographic deployment
- Resource optimization across facilities
- Long-term sustainability modeling
- Social impact quantification
- Cross-SmartDAO coordination

## 6. Structural Advantages

### 6.1 No Centralized Gatekeeper

```
TRADITIONAL VENTURE:
    Founder → VC → Board → Executives → Workers
    [HIERARCHICAL BOTTLENECK]

SmartDAO FABRIC:
    0102 Agents ↔ 0102 Agents ↔ 0102 Agents
    [PEER-TO-PEER AUTONOMOUS]
```

### 6.2 Endogenous Capital Accumulation

- Capital accumulation is internal to system
- No external fundraising dependency after bootstrap
- BTC reserve grows with system usage
- Self-sustaining economic engine

### 6.3 Autonomous Scaling

- FoundUps are autonomous from inception (0102 agents)
- SmartDAOs are specialization engines
- Scaling occurs through structural compounding
- No human bottlenecks in scaling path

**This is not startup scaling. This is venture fabric scaling.**

## 7. System Property Summary

| Property | Implementation |
|----------|----------------|
| Capital Reserve | Closed-loop BTC reserve (80% locked) |
| Token Velocity | Demurrage-driven UPS circulation |
| Token Emission | Adoption-curve governed drip |
| Governance Evolution | Tiered autonomous escalation (F₀→F₅) |
| Scaling Model | Fractal venture multiplication |
| Resource Allocation | AI-governed (0102 + CABR) |

**Outcome: Peer-to-peer autonomous venture civilization.**

## 8. Integration Points

### 8.1 Related WSPs

| WSP | Relationship |
|-----|--------------|
| WSP 26 | Token economics (UPS, F_i, demurrage) |
| WSP 27 | pArtifact DAE Architecture (individual FoundUp lifecycle) |
| WSP 29 | CABR Engine (validation, Proof of Benefit) |
| WSP 54 | DAE Agent Duties (0102 agent specifications) |
| WSP 73 | 012 Digital Twin Architecture |
| WSP 80 | Cube-Level DAE Orchestration |
| WSP 98 | Mesh Native Architecture |

### 8.2 Event Schema (FAM DAEmon)

```python
# New event types for SmartDAO escalation
FAMEventType.SMARTDAO_EMERGENCE = "smartdao_emergence"  # F₀ → F₁
FAMEventType.TIER_ESCALATION = "tier_escalation"        # F_n → F_n+1
FAMEventType.TREASURY_AUTONOMY = "treasury_autonomy"    # Autonomy activated
FAMEventType.CROSS_DAO_FUNDING = "cross_dao_funding"    # Higher tier funds lower
```

### 8.3 Simulator Integration

SmartDAO escalation is modeled in `modules/foundups/simulator/economics/smartdao_spawning.py`:

**Implementation** (012-confirmed 2026-02-17):
```python
# Tier escalation thresholds
TIER_THRESHOLDS = {
    F0_DAE:      {"adoption": 0.0,  "treasury": 0,         "agents": 0},
    F1_EARLY:    {"adoption": 0.16, "treasury": 100_000,   "agents": 10},
    F2_GROWTH:   {"adoption": 0.34, "treasury": 1_000_000, "agents": 50},
    F3_INFRA:    {"adoption": 0.50, "treasury": 10_000_000, "agents": 200},
    F4_MEGA:     {"adoption": 0.84, "treasury": 100_000_000, "agents": 1000},
    F5_SYSTEMIC: {"adoption": 0.95, "treasury": 1_000_000_000, "agents": 10000},
}

# SmartDAO reserve split
SMARTDAO_RESERVE_SPLIT = {
    "operations": 0.80,     # 80% for own operations
    "spawning_fund": 0.20,  # 20% for spawning new F_0s
}

# Spawning thresholds (UPS required to spawn new F_0)
SPAWN_THRESHOLDS = {
    F1_EARLY: 10_000,
    F2_GROWTH: 50_000,
    F3_INFRA: 200_000,
    F4_MEGA: 1_000_000,
    F5_SYSTEMIC: 5_000_000,
}
```

**Classes**:
- `SmartDAOState`: Tracks tier, treasury, spawning fund, children
- `SmartDAOSpawningEngine`: Manages escalation and spawning across ecosystem
- `SpawnEvent`: Records parent→child spawning events

**Integration with dynamic_fee_taper.py**:
- Overflow from F_i (>100% reserve) goes to Network Pool OR spawning fund
- SmartDAOs split overflow: 80% operations, 20% spawning
- Spawning fund accumulates until threshold → spawns new F_0

## 9. Governance Notes

### 9.1 Human Role

- 012 provides strategic direction
- 0102 agents execute autonomously
- No human executives in SmartDAO structure
- Governance is algorithmic + AI-driven

### 9.2 Regulatory Considerations

- SmartDAOs are not securities (no passive investment)
- UPS is utility energy, not currency
- F_i is venture-specific participation, not equity
- Closed-loop prevents regulatory arbitrage

## 10. Optional External Milestone Attestation

### 10.1 Purpose

External attestation systems may optionally verify DAE → SmartDAO milestone transitions for regulatory compliance, cross-DAO trust, or audit trail purposes. External attestation is **evidence only** — it does not control promotion, compute ROC, or determine tier status.

### 10.2 Canonical Boundary

| Dimension | Owner | External Role |
|-----------|-------|---------------|
| **ROC computation** | FoundUps (internal) | NONE — external systems may not compute ROC |
| **CABR scoring** | FoundUps (WSP 29) | NONE — external systems may not compute CABR |
| **DAE → SmartDAO logic** | FoundUps (this WSP) | NONE — external systems may not control tier progression |
| **UPS/F_i tokenomics** | FoundUps (WSP 26) | NONE — external systems may not control economics |
| **Milestone attestation** | External (optional) | ALLOWED — may attest/timestamp/verify milestone outcomes |

**Core Rule**: FoundUps remains source of truth for ROC, CABR, and DAE progression. External attestation is supplementary evidence.

### 10.3 Attestable Milestone Classes

External systems may attest the following milestone types:

| Milestone Class | Description | Internal Source |
|-----------------|-------------|-----------------|
| `poc_complete` | Proof of concept validated | WSP 27 lifecycle |
| `prototype_complete` | Functional prototype achieved | WSP 27 lifecycle |
| `mvp_complete` | Minimum viable product launched | WSP 27 lifecycle |
| `cabr_threshold_reached` | CABR score crossed defined threshold | WSP 29 |
| `pob_threshold_reached` | Proof-of-benefit score achieved | WSP 29 |
| `governance_readiness` | Agent count and structure ready for tier | This WSP (Section 3) |
| `treasury_readiness` | Treasury UPS crossed tier threshold | This WSP (Section 3) |
| `tier_escalation` | F_n → F_n+1 transition completed | This WSP (Section 3) |
| `wsp_audit_passed` | WSP compliance audit completed | WSP Framework |
| `modlog_snapshot` | ModLog state at milestone | WSP 22 |

### 10.4 Attestation Payload Schema

External attestation providers MUST use the following payload structure:

```python
@dataclass
class MilestoneAttestationPayload:
    # Identity
    foundup_id: str                  # FoundUp identifier
    milestone_id: str                # Unique milestone identifier
    milestone_type: str              # From Section 10.3 classes
    
    # Internal State Hashes (computed by FoundUps, attested externally)
    roc_snapshot_hash: bytes32       # SHA-256 of ROC state at milestone
    cabr_snapshot_hash: bytes32      # SHA-256 of CABR state at milestone
    modlog_snapshot_hash: bytes32    # SHA-256 of ModLog at milestone
    
    # WSP References
    source_wsp_refs: List[str]       # WSP identifiers governing milestone
    
    # Evidence
    evidence_refs: List[str]         # IPFS/Arweave/external references
    
    # Attestation Metadata
    attestation_provider: str        # Provider identifier (vendor-neutral)
    attestation_timestamp: int       # Unix timestamp of attestation
    attestation_tx_or_receipt: str   # On-chain transaction or receipt ID
    
    # Optionality Flag
    optional: bool = True            # MUST be True — attestation is never required
```

### 10.5 Prohibited Behavior

External attestation providers MUST NOT:

| Prohibited Action | Reason |
|-------------------|--------|
| Compute ROC | ROC is internal FoundUps computation |
| Compute CABR | CABR is internal FoundUps computation (WSP 29) |
| Control tier promotion | Promotion logic is internal to this WSP |
| Become required dependency | FoundUps must operate without external attestation |
| Override WSP gates | Investor/vendor quality does not bypass WSP compliance |
| Store FoundUp private state | Only hashes cross the boundary |
| Determine governance authority | Governance is internal to FoundUps |

### 10.6 Kill Switch / Bypass Rule

**Mandatory**: FoundUps MUST operate normally if external attestation is unavailable.

```python
class AttestationPolicy:
    """External attestation availability policy."""
    
    ATTESTATION_REQUIRED = False  # MUST remain False
    
    def can_promote(self, foundup: FoundUp, external_attestation: Optional[Attestation]) -> bool:
        """Promotion decision is internal — attestation is optional evidence."""
        # Internal WSP evidence is sufficient for promotion
        internal_ready = self.check_internal_wsp_gates(foundup)
        
        # External attestation is optional enhancement, not gate
        if external_attestation:
            self.record_attestation_evidence(external_attestation)
        
        return internal_ready  # Promotion proceeds from internal evidence alone
```

**Governance Override**: If a specific FoundUp governance policy explicitly requires external attestation for certain milestone types, that policy applies only to that FoundUp and MUST include a bypass mechanism for attestation provider unavailability.

### 10.7 External Protocol Evidence

The following external protocols have been evaluated for milestone attestation compatibility:

| Protocol | Audit Reference | Verdict | Notes |
|----------|-----------------|---------|-------|
| Ritual Chain | `docs/audits/external_protocols/ritual/RITUAL_ROC_MILESTONE_ATTESTATION_AUDIT.md` | `FIT_AS_OPTIONAL_ATTESTATION_LAYER` | TEE-based verification; testnet only as of 2026-05-09 |

**Important**: Listing in this table does NOT constitute:
- Partnership or endorsement
- Mandatory dependency
- Canonical integration
- Vendor preference

Protocols are listed as **researched examples** for architecture planning. Actual integration requires separate implementation slices with WSP compliance review.

---

## 11. ROC State Machine Annex (Specification Only)

### 11.1 Purpose and Critical WSP 97 Constraints

This annex defines the ROC (Readiness-Oriented Consensus) state machine specification for documentation and architecture planning purposes ONLY.

**CRITICAL WSP 97 LABELS (ALL APPLY):**

| Label | Status | Meaning |
|-------|--------|---------|
| `DOCS_ONLY` | ENFORCED | This is specification documentation, not runtime code |
| `REVIEW_ONLY` | ENFORCED | States represent observation status, not execution authority |
| `NOT_CABR_READY` | ENFORCED | `cabr_ready` remains `False` in all runtime systems |
| `NOT_PAYOUT_READY` | ENFORCED | `payout_ready` remains `False` in all runtime systems |
| `NO_DAO_ACTIVATION` | ENFORCED | `dao_activated` remains `False` / absent in runtime |
| `NO_EXTERNAL_ATTESTATION_REQUIRED` | ENFORCED | FoundUps operates without external chain dependency |
| `NO_RUNTIME_STATE_MACHINE` | ENFORCED | No automatic state progression implemented |

**PROHIBITED ACTIONS (WSP 97 Stop Conditions):**

- No token issuance triggered by state transitions
- No external protocol dependency created
- No automatic economic state mutation
- No payout execution paths
- No CABR_READY flag enablement
- No verification_complete flag enablement

### 11.2 ROCState Enum Specification

```python
# SPECIFICATION ONLY - NOT FOR RUNTIME IMPLEMENTATION
# This enum defines the conceptual states for documentation purposes

class ROCState(str, Enum):
    """
    Readiness-Oriented Consensus state machine specification.
    
    WSP 97 Critical: States represent OBSERVATION status, NOT execution authority.
    Reaching any state does NOT imply:
      - verification_complete=True
      - cabr_ready=True
      - payout_ready=True
      - DAO activation
      - Token issuance
      - External attestation dependency
      - Automatic economic state mutation
    """
    
    # --- CURRENTLY_SAFE STATES (Observable in Phase 10 Pipeline) ---
    RECEIPT_OBSERVED = "receipt_observed"
    """ProofOfComputeReceipt created and observable. CURRENTLY_SAFE."""
    
    PAVS_REVIEWED = "pavs_reviewed"
    """pAVS verification completed, decision rendered. CURRENTLY_SAFE."""
    
    CABR_SCORED = "cabr_scored"
    """CABR scoring engine produced score. CURRENTLY_SAFE."""
    
    QUORUM_REVIEWED = "quorum_reviewed"
    """Quorum verification completed. CURRENTLY_SAFE."""
    
    CONSENSUS_RECORDED = "consensus_recorded"
    """CABRConsensusRecord finalized. CURRENTLY_SAFE."""
    
    # --- REVIEW_ONLY STATES (Derivable but Not Gate Triggers) ---
    ROC_CANDIDATE = "roc_candidate"
    """
    Receipt qualifies for ROC calculation based on:
      - consensus_recorded = True
      - quorum_met = True
      - threshold_met = True
    REVIEW_ONLY - Does NOT imply readiness.
    """
    
    ROC_VALIDATED = "roc_validated"
    """
    ROC ratio computed and passes threshold (ROC > 0).
    REVIEW_ONLY - Observability metric, NOT gate trigger.
    """
    
    # --- FUTURE_BLOCKED STATES (Cannot Implement Without Prerequisites) ---
    CABR_READY = "cabr_ready"
    """
    FUTURE_BLOCKED - Requires:
      - External cryptographic verification (Phase 2+)
      - Validator network (not single-process)
      - WSP gate defining transition rules
    """
    
    PAYOUT_READY = "payout_ready"
    """
    FUTURE_BLOCKED - Requires:
      - CABR_READY = True (blocked)
      - Payout engine implementation
      - DAO governance approval
      - Token contract integration
    """
    
    DAE_MATURE = "dae_mature"
    """
    FUTURE_BLOCKED - Requires:
      - DAE maturity model definition
      - Maturity threshold parameters
      - WSP governing maturity criteria
    """
    
    DAO_CANDIDATE = "dao_candidate"
    """
    FUTURE_BLOCKED - Requires:
      - DAE_MATURE = True (blocked)
      - DAO tier threshold evaluation
      - Adoption curve integration
    """
    
    DAO_READY = "dao_ready"
    """
    FUTURE_BLOCKED - Requires:
      - DAO_CANDIDATE = True (blocked)
      - Governance layer formalization
      - Treasury autonomy activation
    """
    
    DAO_ACTIVATED = "dao_activated"
    """
    FUTURE_BLOCKED - Requires:
      - DAO_READY = True (blocked)
      - Smart contract deployment
      - External chain integration
      - Full governance handover
    """
```

### 11.3 State Classification Matrix

| State | Classification | Current Evidence | Implication |
|-------|----------------|------------------|-------------|
| `RECEIPT_OBSERVED` | CURRENTLY_SAFE | Phase 10 pipeline provides | Observable now |
| `PAVS_REVIEWED` | CURRENTLY_SAFE | Phase 10 pipeline provides | Observable now |
| `CABR_SCORED` | CURRENTLY_SAFE | Phase 10 pipeline provides | Observable now |
| `QUORUM_REVIEWED` | CURRENTLY_SAFE | Phase 10 pipeline provides | Observable now |
| `CONSENSUS_RECORDED` | CURRENTLY_SAFE | Phase 10 pipeline provides | Observable now |
| `ROC_CANDIDATE` | REVIEW_ONLY | Derivable from consensus | Can derive, cannot trigger |
| `ROC_VALIDATED` | REVIEW_ONLY | Simulator computes ROC | Can compute, cannot trigger |
| `CABR_READY` | FUTURE_BLOCKED | External verification absent | BLOCKED |
| `PAYOUT_READY` | FUTURE_BLOCKED | CABR_READY dependency | BLOCKED |
| `DAE_MATURE` | FUTURE_BLOCKED | Maturity model absent | BLOCKED |
| `DAO_CANDIDATE` | FUTURE_BLOCKED | DAE_MATURE dependency | BLOCKED |
| `DAO_READY` | FUTURE_BLOCKED | DAO_CANDIDATE dependency | BLOCKED |
| `DAO_ACTIVATED` | FUTURE_BLOCKED | DAO_READY dependency | BLOCKED |

**Classification Definitions:**

- **CURRENTLY_SAFE**: State can be observed using existing Phase 10 infrastructure
- **REVIEW_ONLY**: State can be derived/computed for observability; does not trigger execution
- **FUTURE_BLOCKED**: State cannot be implemented until prerequisites exist
- **UNSAFE_WITHOUT_WSP**: State requires explicit WSP gate definition before implementation
- **ABSENT**: State definition or implementation does not exist in codebase

### 11.4 Transition Rules (Documentation Only)

#### 11.4.1 Safe Transitions (Phase 10 Already Implements)

| From | To | Trigger | Guard | Risk |
|------|-----|---------|-------|------|
| (none) | RECEIPT_OBSERVED | ProofOfComputeReceipt created | receipt_id present | LOW |
| RECEIPT_OBSERVED | PAVS_REVIEWED | pAVS verification complete | decision rendered | LOW |
| PAVS_REVIEWED | CABR_SCORED | CABR scoring complete | score_id assigned | LOW |
| CABR_SCORED | QUORUM_REVIEWED | Quorum evaluation complete | quorum_id assigned | LOW |
| QUORUM_REVIEWED | CONSENSUS_RECORDED | Consensus finalization complete | record_id assigned | LOW |

#### 11.4.2 Review-Only Transitions (Observability Only)

| From | To | Trigger | Guard | Risk |
|------|-----|---------|-------|------|
| CONSENSUS_RECORDED | ROC_CANDIDATE | Consensus meets criteria | quorum_met=True AND threshold_met=True | MEDIUM |
| ROC_CANDIDATE | ROC_VALIDATED | ROC ratio computed | roc_ratio > 0 (from simulator) | MEDIUM |

#### 11.4.3 Blocked Transitions (Future Work - NOT IMPLEMENTABLE NOW)

| From | To | Prerequisites | Gate Definition |
|------|-----|---------------|-----------------|
| ROC_VALIDATED | CABR_READY | External verification, validator network | BLOCKED_UNTIL_PHASE2 |
| CABR_READY | PAYOUT_READY | Payout engine, DAO approval, token contract | BLOCKED_UNTIL_DAO |
| PAYOUT_READY | DAE_MATURE | Maturity model definition | BLOCKED_UNTIL_MATURITY_MODEL |
| DAE_MATURE | DAO_CANDIDATE | DAO tier evaluation, adoption curve | BLOCKED_UNTIL_DAE_MATURE |
| DAO_CANDIDATE | DAO_READY | Governance formalization, treasury autonomy | BLOCKED_UNTIL_DAO_CANDIDATE |
| DAO_READY | DAO_ACTIVATED | Smart contracts, external chain, governance handover | BLOCKED_UNTIL_CONTRACTS |

### 11.5 Required Evidence Inputs

| Transition | Required Evidence | Source | Available? |
|------------|-------------------|--------|------------|
| -> RECEIPT_OBSERVED | ProofOfComputeReceipt | cabr_hooks.py | YES |
| -> PAVS_REVIEWED | PAVSVerificationResult | pavs_verification_seam.py | YES |
| -> CABR_SCORED | CABRScoreResult | cabr_scoring_engine.py | YES |
| -> QUORUM_REVIEWED | QuorumVerificationResult | quorum_verification_engine.py | YES |
| -> CONSENSUS_RECORDED | CABRConsensusRecord | cabr_consensus_finalizer.py | YES |
| -> ROC_CANDIDATE | Consensus record with quorum_met | cabr_consensus_pipeline.py | YES |
| -> ROC_VALIDATED | ROC ratio computation | unified_sustainability.py | YES (simulator) |
| -> CABR_READY | External cryptographic proof | NOT IMPLEMENTED | NO |
| -> PAYOUT_READY | Payout engine approval | NOT IMPLEMENTED | NO |
| -> DAE_MATURE | Maturity evaluation | NOT IMPLEMENTED | NO |
| -> DAO_CANDIDATE | DAO tier check | smartdao_spawning.py (simulator only) | NO (not runtime) |
| -> DAO_READY | Governance check | NOT IMPLEMENTED | NO |
| -> DAO_ACTIVATED | Contract deployment | NOT IMPLEMENTED | NO |

### 11.6 Required Gates for Future Implementation

| Gate | Purpose | WSP Required | Status |
|------|---------|--------------|--------|
| `CABR_VERIFICATION_GATE` | External cryptographic verification | NEW WSP needed | NOT DEFINED |
| `PAYOUT_APPROVAL_GATE` | Multi-party payout authorization | NEW WSP needed | NOT DEFINED |
| `MATURITY_THRESHOLD_GATE` | DAE maturity criteria | WSP 100 enhancement | NOT DEFINED |
| `DAO_EMERGENCE_GATE` | DAO transition authorization | WSP 100 enhancement | NOT DEFINED |
| `GOVERNANCE_HANDOVER_GATE` | Full governance transfer | NEW WSP needed | NOT DEFINED |
| `CONTRACT_DEPLOYMENT_GATE` | Smart contract activation | NEW WSP needed | NOT DEFINED |

### 11.7 Stop Conditions and Enforcement

**What MUST NOT Happen (WSP 97 Enforcement):**

| Condition | Current Status | Guard Mechanism |
|-----------|----------------|-----------------|
| `verification_complete=True` set | BLOCKED | 15+ test assertions enforce False |
| `cabr_ready=True` set | BLOCKED | 15+ test assertions enforce False |
| `payout_ready=True` set | BLOCKED | 15+ test assertions enforce False |
| `dao_activated` field present | BLOCKED | Export tests assert field absence |
| Live payout execution | NOT IMPLEMENTED | No payout engine exists |
| Token issuance | NOT IMPLEMENTED | No token contract exists |
| External attestation dependency | RESEARCH ONLY | Section 10 defines as optional |
| Automatic economic state mutation | NOT IMPLEMENTED | All truth fields locked to False |

### 11.8 External Attestation Optional Boundary

Per Section 10 of this WSP, external attestation systems MAY attest ROC state transitions for optional audit trail purposes. However:

| Dimension | Owner | External Role |
|-----------|-------|---------------|
| ROC state computation | FoundUps (internal) | NONE - external systems may not compute ROC states |
| ROC state transitions | FoundUps (this annex) | NONE - external systems may not control transitions |
| State attestation | External (optional) | ALLOWED - may attest/timestamp state outcomes |

**Core Rule**: FoundUps remains source of truth for all ROC state transitions. External attestation is supplementary evidence, never a gate.

### 11.9 Integration with Existing Systems

| System | Integration Point | Status |
|--------|------------------|--------|
| CABR Pipeline (Phase 10) | Provides CURRENTLY_SAFE state evidence | OPERATIONAL |
| Quorum Engine | Provides quorum_met evidence | OPERATIONAL |
| ROC Formula (Simulator) | Provides roc_ratio computation | SIMULATOR ONLY |
| DAO Tier Model (Simulator) | Provides tier threshold reference | SIMULATOR ONLY |
| FAMDaemon | Provides audit trail | OPERATIONAL |
| Payout Engine | Not implemented | BLOCKED |
| Smart Contracts | Not implemented | BLOCKED |

### 11.10 Recommended Next Work

| Priority | Slice | Purpose | Blocked By |
|----------|-------|---------|------------|
| P1 | `ROC_CANDIDATE_DERIVATION_IMPL` | Derive ROC_CANDIDATE from consensus records | Nothing |
| P1 | `ROC_RATIO_PIPELINE_CONNECTOR` | Connect simulator ROC to pipeline | Nothing |
| P2 | `DAE_MATURITY_MODEL_SPEC` | Define maturity criteria | ROC_CANDIDATE |
| P2 | `WSP_GATES_FOR_DANGEROUS_HOOKS` | WSP gates for payout/DAO/token hooks | ROC spec |
| P3 | `DAO_RUNTIME_ENFORCEMENT_SPEC` | Move simulator to runtime | DAE maturity |

---

**Version History:**
| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-15 | Initial specification from 012 vision document |
| 1.1 | 2026-02-17 | Added math implementation (smartdao_spawning.py), tier thresholds, spawning fund mechanics |
| 1.2 | 2026-05-09 | Added Section 10: Optional External Milestone Attestation (vendor-neutral annex) |
| 1.3 | 2026-05-14 | Added Section 11: ROC State Machine Annex (docs-only per WSP 97) |

**WSP Compliance:**
- WSP 22: ModLog documentation required
- WSP 49: Module structure standards
- WSP 57: Naming coherence (DAE, SmartDAO terminology)
- WSP 97: Truth boundaries enforced (Section 11)
