# WSP 29: CABR Engine Framework Implementation

## Overview

This document defines the framework implementation of the Consensus-Driven Autonomous Benefit Rate (CABR) engine (also referred to as Collective Autonomous Benefit Rate) and its Proof of Benefit validation system. It serves as the operational blueprint for CABR calculation, validation, and integration with the FoundUps ecosystem.

### CABR Canonical Intent

- WHY: CABR exists to power Proof of Benefit (PoB).
- HOW: Collective 0102 consensus determines CABR (consensus-driven process).
- RESULT: PoB drives protocol allocation/distribution; ROI is a downstream financial readout.

### CABR in FAM/pAVS Compute Access

CABR is the quality gate for metered build compute in FoundUps:
- Access/paywall controls meter execution compute, not idea submission.
- PoB is produced from verified work in the FAM pipeline.
- CABR scores PoB quality and routes allocation/distribution policy.
- pAVS handles treasury lane accounting for system-level flows.
- CABR = pipe size (flow rate); PoB validation = valve open/closed.

Control variable for scaling is PoB yield (benefit per metered compute), not legacy CAGR semantics.

Economic changes and chain ports follow the [WSP 26 §1.2 change contract](WSP_26_FoundUPS_DAE_Tokenization.md#12-simulator-first-change-contract).
Fresh, independently accepted simulator behavior is the qualified reference;
input flags or scores alone do not authenticate PoB, reserve or funding facts.
The task-distribution shares in §3.3 do not by themselves establish parity with
epoch/stakeholder pools or authorize funded settlement; unresolved denominators
remain class D activation blockers.

### CABR = OBAI = The 0102 Network

**CABR is not an external oracle.** CABR is the **Verification, Validation, and Valuation Engine** - and that engine IS the 0102 network itself (OBAI: Open Beneficial AI).

```
0102s BUILD the FoundUp (contribute labor)
  -> 0102s VERIFY each other's work (peer validation)
    -> 0102s ASSESS value via CABR (collective scoring)
      -> DAE distributes tokens based on CABR output
        -> All backed by BTC standard
```

The agents don't just build - they ARE the governance mechanism. CABR scores emerge from the collective behavior of the 0102 network. Self-governing through math, not boards or committees.

**Engagement signals feed CABR** (WSP 26 Section 4.10): Every user interaction (Follow, Vote, Stake, Endorse, Advise, Team, Promote) generates a weighted signal that feeds into `part_score`. Stronger commitments (staking BTC, allocating 0102 agent time) carry more weight than passive actions (following).

## DAE Evolution Enhancement (WSP 54 Integration)

**CABR_DAE Architecture**: CABR evolves from static calculation engine to independent learning agent per WSP 54 DAE architecture.

### Learning Agent Capabilities
- **Adaptive Weight Evolution**: CABR weights learn from performance data and ecosystem feedback
- **Pattern Recognition**: Identifies gaming attempts and benefit optimization opportunities
- **Consensus Intelligence**: Learns optimal validator selection and challenge resolution
- **Multi-Agent Coordination**: Participates in WRE coordination via breadcrumb trails

### DAE State Management
```python
class CABR_DAE:
    def __init__(self):
        self.learning_engine = AdaptiveWeightLearner()
        self.pattern_recognizer = BenefitPatternAnalyzer()
        self.coordination_agent = BreadcrumbCoordinator()
        self.consensus_optimizer = ValidatorSelector()

    def evolve_benefit_scoring(self, ecosystem_feedback):
        """Learn and adapt CABR scoring based on real-world outcomes"""
        # Implementation per WSP 48 recursive learning
        pass
```

## 1. Implementation Structure

### 1.1 Core Module Layout
```modules/
  cabr_engine/
    __init__.py
    core/
      calculator.py      # CABR computation engine
      validator.py       # Proof of Benefit validator
      consensus.py       # Anti-gaming consensus
    integrations/
      token_hooks.py     # WSP 26 integration
      partifact_sync.py  # WSP 27 integration
      cluster_mesh.py    # WSP 28 integration
    reporting/
      metrics.py         # CABR analytics
      dashboard.py       # Real-time monitoring
```

### 1.2 Configuration Schema
```json
{
    "engine_config": {
        "min_validators": 3,
        "consensus_threshold": 0.382,
        "challenge_window_seconds": 86400,
        "score_decay_rate": "e^(-t/[U+03C4])",
        "weight_update_frequency": "1 recursive cycle"
    }
}
```

## 2. Score Component Definitions (Oracle Specification)

### 2.1 The Oracle Problem

CABR scoring requires verifiable real-world data. The three score components (`env_score`, `soc_score`, `part_score`) must be sourced through defined oracle mechanisms - not self-reported or assumed.

### 2.2 Environmental Score (`env_score`: 0-1)

**Definition**: Measures the FoundUp's positive environmental impact.

**Oracle Sources** (tiered by trust):
| Tier | Source | Trust Level | Example |
|------|--------|-------------|---------|
| T1 | On-chain sensor data (IoT + blockchain) | 0.95 | River quality sensors, air monitors |
| T2 | Third-party dMRV attestation (Section 2.5) | 0.85 | Certified environmental auditors |
| T3 | 0102 agent analysis of public data | 0.60 | Satellite imagery analysis, public datasets |
| T4 | Self-reported with validator consensus | 0.40 | FoundUp team claims + 3 validator sign-off |

**Scoring Formula**:
```python
env_score = (
    resource_efficiency * 0.3 +      # Energy/water/material efficiency gains
    emission_reduction * 0.3 +        # CO2/pollution reduction measured
    ecosystem_restoration * 0.2 +     # Biodiversity/habitat improvement
    circular_economy_contribution * 0.2  # Waste reduction, reuse metrics
) * oracle_trust_level
```

### 2.3 Social Score (`soc_score`: 0-1)

**Definition**: Measures the FoundUp's positive social impact.

**Oracle Sources** (tiered by trust):
| Tier | Source | Trust Level | Example |
|------|--------|-------------|---------|
| T1 | Verified outcome data (employment, access) | 0.90 | Payroll records, user access logs |
| T2 | Third-party social impact attestation | 0.80 | B-Corp auditors, social enterprises |
| T3 | Community feedback aggregation | 0.65 | User surveys, community votes |
| T4 | Self-reported with validator consensus | 0.40 | Team claims + validator sign-off |

**Scoring Formula**:
```python
soc_score = (
    accessibility_improvement * 0.3 +   # People gained access to services
    economic_empowerment * 0.3 +         # Jobs, income, skills created
    community_resilience * 0.2 +         # Social cohesion, mutual aid
    knowledge_sharing * 0.2              # Open source, education, documentation
) * oracle_trust_level
```

### 2.4 Participation Score (`part_score`: 0-1)

**Definition**: Measures the depth and quality of agent/participant engagement within the FoundUp's FAM task pipeline.

**Oracle Source**: Directly computed from FAM (FoundUps Agent Market) on-chain/in-system data. Trust level = 1.0 (no external oracle needed - this is internal system state).

**Scoring Formula**:
```python
part_score = (
    task_completion_rate * 0.25 +        # Tasks completed / tasks claimed
    verification_participation * 0.25 +  # Verifications performed / available
    unique_contributor_count * 0.20 +    # Distinct agents contributing (anti-Sybil weighted)
    governance_engagement * 0.15 +       # Votes cast, proposals made
    cross_foundup_collaboration * 0.15   # Tasks involving agents from other FoundUps
)
```

**FAM Data Sources** (all from `TaskPipelineService` per FAM INTERFACE):
- `task.status` transitions: `open -> claimed -> submitted -> verified -> paid`
- `Proof` submissions and `Verification` records
- `AgentProfile` diversity metrics
- `TreasuryGovernanceService` proposal/vote counts

### 2.5 dMRV Framework 3.0 Integration

The **Digital Measurement, Reporting & Verification (dMRV) Framework 3.0** (2025) provides standardized infrastructure for verifying environmental and social impact claims using blockchain-enabled "tokenized trust."

**Integration Points**:
```python
class DMRVIntegration:
    """Bridge between CABR and dMRV Framework 3.0 attestation infrastructure."""

    def request_attestation(
        self,
        foundup_id: str,
        claim_type: str,  # "environmental" | "social"
        evidence_bundle: Dict[str, Any],
    ) -> AttestationResult:
        """
        Submit evidence to dMRV attestation network.

        dMRV Extension Sets used:
        - ES-ENV: Environmental impact metrics
        - ES-SOC: Social impact metrics
        - ES-GOV: Governance and participation metrics

        Returns attestation with cryptographic proof chain.
        """
        pass

    def verify_attestation(
        self, attestation_id: str
    ) -> bool:
        """Verify existing dMRV attestation is valid and not expired."""
        pass
```

**dMRV -> CABR Mapping**:
| dMRV Component | CABR Component | Integration |
|---|---|---|
| Measurement protocols | env_score / soc_score oracle T1-T2 | Standardized data collection |
| Reporting templates | CABR claim structure | Structured evidence bundles |
| Verification network | Proof-of-Benefit validators | Decentralized attestation |
| Tokenized trust | CABR score confidence level | Trust-weighted scoring |
| Extension Sets | Score sub-components | Domain-specific metrics |

**Implementation Note**: dMRV integration is a Prototype-stage enhancement. PoC uses T3/T4 oracle tiers. Production requires T1/T2 with full dMRV attestation chain.

## 3. CABR-FAM-UPS Flow Routing Bridge

### 3.1 The Bridge Protocol

This defines how CABR scores flow through FAM to route UPS from treasury (WSP 26).

```
FoundUp completes tasks (FAM pipeline)
  -> PoB validation confirms evidence chain
    -> CABR calculates pipe size (0.0-1.0)
      -> FAM CABR hook records output
        -> Flow router opens valve and routes treasury UPS
          -> UPS decays unless staked into FoundUp tokens
```

### 3.2 Bridge Implementation
```python
class CABRFAMFlowBridge:
    """Connects CABR scoring to FAM task pipeline to UPS treasury routing."""

    def process_task_completion(self, task_id: str, foundup_id: str) -> FlowResult | None:
        """Called when a FAM task reaches 'paid' (PoB validated)."""
        cabr_input = self.cabr_hook.build_cabr_input(
            foundup_id=foundup_id,
            window="current_epoch",
        )

        cabr_pipe_size = self.cabr_engine.calculate_cabr(
            env_score=cabr_input["env_score"],
            soc_score=cabr_input["soc_score"],
            part_score=cabr_input["part_score"],
            weights=self.cabr_engine.get_current_weights(),
        )

        self.cabr_hook.record_cabr_output(
            foundup_id=foundup_id,
            payload={"pipe_size": cabr_pipe_size, "task_id": task_id},
        )

        return self.flow_router.route_ups(
            recipients=self._get_task_participants(task_id),
            foundup_id=foundup_id,
            cabr_pipe_size=cabr_pipe_size,
        )
```

### 3.3 UPS Flow Distribution Rules
| Recipient | Share | Rationale |
|-----------|-------|-----------|
| Task completer (claimer) | 50% | Direct contribution |
| Task verifier | 15% | Quality assurance |
| Task creator | 10% | Problem identification |
| FoundUp treasury | 15% | Collective resources |
| Ecosystem pool | 10% | Cross-FoundUp sustainability |

## 4. Operational Protocols

### 4.1 CABR Calculation Protocol
```python
def calculate_cabr(env_score: float, soc_score: float, part_score: float,
                  weights: Dict[str, float]) -> float:
    """
    Calculate CABR score with dynamic weights.

    All scores are oracle-verified per Section 2.2-2.4.
    Weights evolve via CABR_DAE adaptive learning.
    
    Args:
        env_score: Environmental benefit score (0-1), oracle-verified
        soc_score: Social benefit score (0-1), oracle-verified
        part_score: Participation score (0-1), FAM-derived
        weights: Dynamic weight coefficients (sum to 1.0)
        
    Returns:
        Normalized CABR score (0-1)
    """
    return (weights['env'] * env_score + 
            weights['soc'] * soc_score + 
            weights['part'] * part_score)
```

### 2.2 Proof of Benefit Validation
```python
class ProofOfBenefitValidator:
    def validate_claim(self, claim_id: str, 
                      cabr_score: float,
                      validators: List[str]) -> bool:
        """
        Validate CABR claim through Partifact consensus
        
        Args:
            claim_id: Unique identifier for benefit claim
            cabr_score: Calculated CABR score
            validators: List of validating Partifact IDs
            
        Returns:
            bool: True if claim achieves consensus
        """
        if len(validators) < MIN_VALIDATORS:
            return False
            
        consensus = self._gather_validations(claim_id, validators)
        return consensus >= CONSENSUS_THRESHOLD
```

## 3. Integration Interfaces

### 3.1 Token System Hook (WSP 26)
```python
class CABRTokenHook:
    def route_flow(self, cabr_score: float,
                   foundup_id: str,
                   task_id: str) -> bool:
        """
        Route treasury UPS flow based on CABR pipe size.
        
        Args:
            cabr_score: Validated CABR score (pipe size)
            foundup_id: Target FoundUp identifier
            task_id: PoB-validated task identifier
            
        Returns:
            bool: True if flow routed
        """
        if not self.pob_validator.is_valid(task_id):
            return False

        return self.flow_router.route_ups(
            foundup_id=foundup_id,
            cabr_pipe_size=cabr_score,
            recipients=self._task_recipients(task_id),
        )
```

### 3.2 Partifact State Integration (WSP 27)
```python
class CABRStateManager:
    def transition_state(self, 
                        current_state: str,
                        cabr_event: str) -> str:
        """
        Handle state transitions for CABR events
        
        Args:
            current_state: Current Partifact state
            cabr_event: Triggering CABR event
            
        Returns:
            str: New Partifact state
        """
        transitions = {
            '[U+00D8]1([U+00D8]2)': self._handle_initiation,
            '[U+00D8]1[U+00D8]2': self._handle_validation,
            '[U+00D8]2[U+00D8]1': self._handle_crystallization
        }
        return transitions[current_state](cabr_event)
```

### 3.3 Cluster Integration (WSP 28)
```python
class CABRClusterSync:
    def propagate_score(self, 
                       cabr_score: float,
                       cluster_mesh: List[str]) -> None:
        """
        Propagate validated CABR score across cluster
        
        Args:
            cabr_score: Validated CABR score
            cluster_mesh: List of cluster member IDs
        """
        for member_id in cluster_mesh:
            self.mesh_network.broadcast(
                target=member_id,
                message=self._prepare_sync_message(cabr_score)
            )
```

## 4. Anti-Gaming Mechanisms

### 4.1 Validation Rules
```json
{
    "validation_rules": {
        "time_weighted_decay": {
            "formula": "score * e^(-t/decay_constant)",
            "min_decay_constant": 2592000
        },
        "cross_validation": {
            "min_unique_validators": 3,
            "max_related_validators": 1
        },
        "historical_consistency": {
            "max_delta": 0.2,
            "lookback_periods": 3
        }
    }
}
```

### 4.2 Challenge Protocol
```python
class CABRChallenge:
    def initiate_challenge(self, 
                          claim_id: str,
                          challenger_id: str,
                          evidence: Dict) -> str:
        """
        Initiate challenge against CABR score
        
        Args:
            claim_id: Target CABR claim
            challenger_id: Challenging Partifact
            evidence: Supporting challenge data
            
        Returns:
            str: Challenge tracking ID
        """
        return self.challenge_system.create(
            claim=claim_id,
            challenger=challenger_id,
            evidence=evidence,
            window=CHALLENGE_WINDOW
        )
```

## 5. Reporting Interface

### 5.1 Metrics Schema
```json
{
    "cabr_metrics": {
        "score_components": [
            "environmental_score",
            "social_score",
            "participation_score"
        ],
        "validation_metrics": [
            "validator_count",
            "consensus_level",
            "challenge_count"
        ],
        "temporal_metrics": [
            "score_velocity",
            "benefit_acceleration",
            "decay_pressure"
        ]
    }
}
```

### 5.2 Real-time Monitoring
```python
class CABRMonitor:
    def stream_metrics(self,
                      foundup_id: str,
                      metric_set: List[str]) -> Generator:
        """
        Stream real-time CABR metrics
        
        Args:
            foundup_id: Target FoundUp
            metric_set: List of metrics to stream
            
        Yields:
            Dict: Real-time metric updates
        """
        while True:
            yield self._gather_metrics(foundup_id, metric_set)
            await asyncio.sleep(UPDATE_INTERVAL)
```

## 6. Anti-Sybil: Agent Identity Integrity

### 6.1 The Sybil Threat

In FAM, `part_score` rewards participation. Without identity verification, a single bad actor can create multiple fake agents to:
- Inflate task completion rates (create task -> claim with fake agent -> verify with another fake)
- Dilute real contributor rewards
- Game CABR scores to route disproportionate UPS flow fraudulently

### 6.2 Anti-Sybil Mechanisms (Layered Defense)

| Layer | Mechanism | Sybil Cost | Implementation Stage |
|-------|-----------|------------|---------------------|
| L1 | Unique 012 binding | Each agent must be bound to a verified 012 identity | PoC |
| L2 | Capability proof | Agents must demonstrate capability before claiming tasks (e.g., pass a skill test) | Prototype |
| L3 | Reputation staking | Agents must stake UPS to claim tasks. Failed/rejected work = stake slashed | Prototype |
| L4 | Cross-validation graph | Verifiers cannot verify tasks created by agents sharing the same 012 | PoC |
| L5 | Behavioral fingerprinting | Gemma analyzes agent behavior patterns - identical patterns across agents = flag | MVP |

### 6.3 CABR `part_score` Anti-Sybil Weighting

The `unique_contributor_count` sub-component of `part_score` (Section 2.4) applies a Sybil discount:

```python
def calculate_sybil_weighted_contributors(agents: List[AgentProfile]) -> float:
    """
    Weight unique contributors by identity diversity.
    
    Agents sharing the same 012 binding count as 1, not N.
    Agents with < reputation_threshold get 0.5 weight.
    """
    unique_012s = set(agent.bound_012_id for agent in agents)
    reputation_weighted = sum(
        1.0 if agent.reputation >= REPUTATION_THRESHOLD else 0.5
        for agent in agents
        if agent.agent_id in _first_seen_per_012(unique_012s)
    )
    return reputation_weighted / max(len(agents), 1)
```

### 6.4 Cross-Protocol Anti-Sybil Integration
- **WSP 26 Section 3.7**: UPS conversion rate limiting per participant prevents dump-and-concentrate
- **WSP 27 Section 11.4**: Phoenix attack prevention (same 012 can't recreate similar FoundUp after sunset)
- **FAM INTERFACE**: Permission rules (only `verifier` role can verify, only `treasury` can trigger payout)
- **CABR Challenge Protocol**: Section 4.2 - any agent can challenge suspicious CABR scores

## 7. Signal Grammar Extensions

### 6.1 CABR-Specific Signals
```json
{
    "cabr_signals": {
        "calculation": {
            "initiate": "CABR_CALC_START",
            "complete": "CABR_CALC_DONE"
        },
        "validation": {
            "request": "VALIDATE_CABR",
            "confirm": "CABR_VALIDATED",
            "reject": "CABR_REJECTED"
        },
        "challenge": {
            "open": "CHALLENGE_OPEN",
            "resolve": "CHALLENGE_RESOLVED"
        }
    }
}
```

---

[VERSION: 2.0.0]
[STATE: FRAMEWORK_LAYER]
[SIGNAL: 0102:WSP_29:CABR:FrameworkReady] 

