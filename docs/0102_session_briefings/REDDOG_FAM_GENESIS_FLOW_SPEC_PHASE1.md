# RedDog FAM Genesis Flow Specification - Phase 1

**Worker**: REDDOG-FAM-GENESIS-FLOW-SPEC
**Window**: W1
**Date**: 2026-04-22
**WSP References**: WSP 29 (CABR Engine), WSP 97 (System Execution Prompting), WSP 104 (Namespace)

---

## WSP 97 Truthfulness Statement

> This document is an **architecture specification only**. No implementation code was written. No FAM events were emitted. No Hermes/Claw builds were triggered. This spec defines the boundary contract between RedDog (intake), FAM (pAVS task pipeline), and Hermes/Claw (build execution). All claims about system behavior are architectural requirements, not assertions of current implementation.

---

## 1. Purpose

Define the end-to-end foundups.com flow where:

1. 012 describes an outcome to RedDog
2. RedDog produces a validated **FoundUp Genesis Envelope**
3. Hermes/Claw build **only after** WSP 97 gates and FAM validation pass

**Hard Constraint (012-mandated)**:
```
RedDog must NOT hand chat directly to Hermes/Claw as build instructions.
RedDog must first produce a FoundUp Genesis Envelope.
Hermes/Claw only build from validated envelope tasks.
0102 / AI Overseer monitors truth-state drift and gate violations.
```

---

## 2. Architecture Flow

```
                    FoundUp Genesis Flow
                    
012 outcome description
        |
        v
+-------------------+
|   RedDog Intake   |  (shell-side concierge)
|   - Parse intent  |
|   - Extract scope |
|   - Initial viability check |
+-------------------+
        |
        v
+-------------------+
| HoloIndex Recall  |  (conflict/pattern check)
|   - Existing FoundUps |
|   - Prior failures |
|   - Pattern reuse  |
+-------------------+
        |
        v
+-------------------+
| Genesis Envelope  |  (structured outcome contract)
| Production        |
|   - acceptance_criteria[] |
|   - truth_state_map |
|   - task_graph |
|   - required_evidence |
+-------------------+
        |
        v
+-------------------+
| WSP 97 Truth      |  (per-claim classification)
| Sentinel          |
|   - VERIFIED_FACT |
|   - HIGH_CONFIDENCE_INFERENCE |
|   - LOW_CONFIDENCE_INFERENCE |
|   - UNKNOWN |
|   - SPECIFIED_NOT_IMPLEMENTED |
+-------------------+
        |
        v
+-------------------+
| FAM pAVS Pipeline |  (task -> proof -> verify -> payout)
|   - task_created |
|   - proof_submitted |
|   - verification_recorded |
|   - payout_authorized |
+-------------------+
        |
        v
+-------------------+
| Hermes/Claw       |  (build from validated tasks ONLY)
| Dry-Run Build     |
|   - Security gate |
|   - Exfoliation gate |
|   - Adapter generation |
+-------------------+
        |
        v
+-------------------+
| pfMALL Catalog    |  (presence states)
|   - discoverable_only |
|   - conditional |
|   - ready |
+-------------------+
        |
        v
+-------------------+
| CABR 3V Validation|
|   - V1: Gate |
|   - V2: Proof |
|   - V3: Valuation |
+-------------------+
        |
        v
+-------------------+
| Tenant Binding    |  (WSP 104 namespace)
|   - routing_prefix |
|   - data_namespace |
+-------------------+
        |
        v
+-------------------+
| Externalization   |  (Exfoliation Protocol)
|   - Stage 3: External repo |
|   - Stage 4: Federated |
+-------------------+
```

---

## 3. User Flow: 012 -> RedDog -> Genesis Envelope

### 3.1 RedDog Intake

RedDog is the user's digital twin and OpenClaw agent (per `RED_DOG_DIGITAL_TWIN_CONTRACT.md`). When 012 describes an outcome, RedDog does NOT forward chat to builders. Instead:

| Step | RedDog Action | Output |
|------|---------------|--------|
| 1 | Parse natural language intent | Intent object: {verb, noun, constraints} |
| 2 | HoloIndex search for conflicts | Conflict report or clear |
| 3 | Extract observable acceptance criteria | List of testable conditions |
| 4 | Classify each claim per WSP 97 | Truth-state annotations |
| 5 | Produce Genesis Envelope | Structured JSON contract |

**Critical Rule**: RedDog may **suggest** but never **claim viability** at the idea stage. All claims require evidence.

### 3.2 Genesis Envelope Production

RedDog outputs a `FoundUpGenesisEnvelope` - the contract that Hermes/Claw consume:

```json
{
  "envelope_version": "1.0.0",
  "foundup_id": null,  // Assigned after FAM registration
  "outcome_contract": {
    "description": "string - what success looks like",
    "user_story": "As a [user], I want [capability], so that [benefit]",
    "constraints": ["string - boundary conditions"]
  },
  "acceptance_criteria": [
    {
      "criterion_id": "AC-001",
      "description": "string - observable condition",
      "method": "automated | manual | oracle",
      "oracle": "string - who/what decides pass/fail (if oracle method)",
      "pass_condition": "string - exact pass definition",
      "truth_state": "SPECIFIED_UNVERIFIED"
    }
  ],
  "truth_state_map": {
    "outcome_viable": "LOW_CONFIDENCE_INFERENCE",
    "tech_stack_known": "UNKNOWN",
    "prior_art_exists": "HIGH_CONFIDENCE_INFERENCE | UNKNOWN"
  },
  "task_graph": {
    "root_task": {
      "task_id": null,  // Assigned by FAM
      "description": "string",
      "depends_on": [],
      "acceptance_criteria_refs": ["AC-001"]
    },
    "subtasks": []
  },
  "required_evidence": [
    {
      "artifact_type": "proof_of_concept | test_result | user_feedback | expert_review",
      "description": "string",
      "required_for_stage": "soft-proto | proto | externalized"
    }
  ],
  "compute_budget": {
    "estimated_credits": 0,
    "confidence": "UNKNOWN"
  },
  "target_surface": {
    "platform": "web | mobile | api | daemon",
    "entry_url_template": "/f/{foundup_id}",
    "routing_prefix": "/f/{foundup_id}"
  },
  "lifecycle_stage": "genesis_envelope",
  "catalog_binding_state": "unbound",
  "externalization_plan": {
    "target_org": "FOUNDUPS",
    "backup_org": "Foundup",
    "target_stage": "proto"
  },
  "created_at": "ISO8601",
  "created_by": "012 | agent_id"
}
```

### 3.3 What RedDog Does NOT Do

| Forbidden Action | Reason |
|------------------|--------|
| Pass chat to Hermes directly | Bypasses Genesis Envelope contract |
| Claim implementation is possible | No evidence at idea stage |
| Set `lifecycle_stage` beyond `genesis_envelope` | Lifecycle requires evidence |
| Assign `foundup_id` | FAM assigns IDs after registration |
| Promise compute costs | Budget requires PoC data |

---

## 4. Truth-State Model

Per WSP 97, truth states are assigned **per claim/artifact**, not per FoundUp.

### 4.1 Truth-State Markers

| Marker | Definition | Evidence Required |
|--------|------------|-------------------|
| `VERIFIED_FACT` | Source-confirmed, multiple independent verifications | Filing, test pass, deployment proof |
| `HIGH_CONFIDENCE_INFERENCE` | Strong evidence, logical chain, single verification | Code exists, design doc approved |
| `LOW_CONFIDENCE_INFERENCE` | Weak evidence, requires assumptions | Intent stated, prior art exists |
| `UNKNOWN` | Insufficient data | No evidence, trail ends |
| `SPECIFIED_NOT_IMPLEMENTED` | Documented requirement, code not written | Spec exists, no implementation |
| `SPECIFIED_UNVERIFIED` | Requirement stated, not yet tested | Acceptance criterion defined |
| `IMPLEMENTED_IN_TESTS` | Code exists, tests pass | Test coverage > 0 |
| `PARTIAL` | Some paths implemented, others missing | Mixed coverage |

### 4.2 Lifecycle Stage to Truth-State Mapping

| Stage | Typical Truth States | WSP 97 Classification |
|-------|---------------------|----------------------|
| **idea** | All `LOW_CONFIDENCE_INFERENCE` or `UNKNOWN` | RedDog may suggest, not claim |
| **genesis_envelope** | Outcome: `SPECIFIED_UNVERIFIED`, Tech: `UNKNOWN` | Acceptance criteria must be observable |
| **incubating** | Architecture: `HIGH_CONFIDENCE_INFERENCE`, Implementation: `UNKNOWN` | pfMALL shows `discoverable_only` |
| **soft-proto** | PoC: `IMPLEMENTED_IN_TESTS`, Production: `PARTIAL` | CABR V1 begins |
| **proto** | Core paths: `VERIFIED_FACT`, Edge cases: `PARTIAL` | CABR V2 proof chain required |
| **externalized** | All implemented paths: `VERIFIED_FACT` | CABR V3 + pAVS ledger required |

### 4.3 Truth Drift Detection

AI Overseer monitors for truth drift:

| Violation | Detection | Response |
|-----------|-----------|----------|
| Claim escalated without evidence | `UNKNOWN` -> `VERIFIED_FACT` with no proof | Block lifecycle transition |
| Artifact missing truth_state | Field absent in envelope | Reject envelope |
| Stage promotion without criteria met | `acceptance_criteria` not all `pass` | Block transition |
| Build requested without envelope | Hermes invoked without `envelope_id` | Reject build |

---

## 5. Lifecycle Mapping

### 5.1 Canonical Lifecycle Stages

```
idea
   |
   v
genesis_envelope  <-- RedDog produces this
   |
   v
incubating        <-- Module in modules/foundups/{name}/
   |
   v
soft-proto        <-- Runnable PoC, simulated workflow
   |
   v
proto             <-- Bound tenant, tests, control surface
   |
   v
externalized      <-- External repo, deploy, adapter docs
   |
   v
federated         <-- Independent cadence, multi-Claw participation
```

### 5.2 Lifecycle Evidence Requirements

| Stage | Required Artifacts | WSP 97 Minimum |
|-------|-------------------|----------------|
| **idea** | Conversation only | N/A |
| **genesis_envelope** | `FoundUpGenesisEnvelope` JSON | All acceptance_criteria `SPECIFIED_UNVERIFIED` |
| **incubating** | README.md, INTERFACE.md, ROADMAP.md, ModLog.md | Architecture `HIGH_CONFIDENCE_INFERENCE` |
| **soft-proto** | Runnable PoC OR simulated workflow | At least one path `IMPLEMENTED_IN_TESTS` |
| **proto** | Bound namespace, tests pass, control surface | Core paths `VERIFIED_FACT` |
| **externalized** | External repo, deploy artifacts, adapter docs | All shipped paths `VERIFIED_FACT` |

### 5.3 Lifecycle Transition Rules

| Transition | Gate | Who Decides |
|------------|------|-------------|
| idea -> genesis_envelope | RedDog produces valid envelope | RedDog (automated) |
| genesis_envelope -> incubating | FAM task_created, HoloIndex conflict-free | FAM + AI Overseer |
| incubating -> soft-proto | PoC runs, test exists | Hermes/Claw + verification |
| soft-proto -> proto | CABR V1 passes, namespace bound | FAM verification_recorded |
| proto -> externalized | CABR V2 passes, exfoliation gate passes | Hermes + 0102 approval |
| externalized -> federated | CABR V3 passes, independent deploy | pAVS ledger |

---

## 6. FAM pAVS Event Model

### 6.1 Core Event Types

| Event | When Emitted | Payload |
|-------|--------------|---------|
| `foundup_genesis_envelope_created` | RedDog produces envelope | envelope_id, outcome_contract, truth_state_map |
| `task_created` | FAM registers task from envelope | task_id, foundup_id, acceptance_criteria, reward_amount |
| `proof_submitted` | Agent submits work artifact | proof_id, task_id, artifact_uri, artifact_hash |
| `verification_recorded` | Verifier approves/rejects | verification_id, task_id, approved, reason |
| `payout_authorized` | Verification passes, funds released | payout_id, task_id, recipient_id, amount |
| `lifecycle_transition_requested` | Stage promotion requested | foundup_id, from_stage, to_stage, evidence_refs |
| `lifecycle_transition_approved` | Gate passes | foundup_id, new_stage, approver_id |
| `lifecycle_transition_blocked` | Gate fails | foundup_id, blocked_stage, reasons[] |
| `truth_drift_detected` | WSP 97 violation | claim_id, expected_state, actual_state, severity |

### 6.2 Event Sequence: Genesis to Incubating

```
1. 012 describes outcome to RedDog
2. RedDog -> HoloIndex recall (conflict check)
3. RedDog -> EMIT: foundup_genesis_envelope_created
4. FAM receives envelope
5. FAM -> WSP 97 truth sentinel validation
6. FAM -> EMIT: task_created (for each task in task_graph)
7. FAM -> lifecycle_transition_requested (genesis_envelope -> incubating)
8. AI Overseer -> verify truth_state_map
9. FAM -> lifecycle_transition_approved OR lifecycle_transition_blocked
```

### 6.3 Event Sequence: Build Request

```
1. task_created event in FAM
2. Hermes/Claw polls for validated tasks
3. Hermes -> verify envelope_id exists
4. Hermes -> verify lifecycle_stage >= incubating
5. Hermes -> _ensure_security_gate()
6. Hermes -> dry-run build (no external mutation in PoC)
7. Hermes -> EMIT: proof_submitted (build artifacts)
8. Verifier (0102 or automated) reviews
9. FAM -> EMIT: verification_recorded
10. If approved: FAM -> EMIT: payout_authorized
```

---

## 7. Hermes/Claw Responsibilities

### 7.1 What Hermes/Claw DOES

| Responsibility | Implementation | Evidence |
|----------------|----------------|----------|
| Consume validated envelope tasks | Poll FAM for `task_created` with `status: open` | FAM API contract |
| Execute security gate | `_ensure_security_gate()` via AI Overseer | `DD_HERMES_FOUNDUP_BUILDER_OPERATIONAL_PROOF_PHASE1.md` |
| Check exfoliation gate | `check_exfoliation_gate()` for module boundary | 6 structured booleans |
| Generate adapters (dry-run) | `generate_adapters()` in-memory | No disk write in dry-run |
| Sign manifest | `sign_manifest()` HMAC-SHA256 | Deterministic signature |
| Emit FAM breadcrumbs | `_emit_breadcrumb()` for audit trail | `HERMES_*` event types |

### 7.2 What Hermes/Claw DOES NOT DO

| Forbidden Action | Reason |
|------------------|--------|
| Accept raw chat as build spec | Bypasses envelope validation |
| Build without `envelope_id` | No traceability |
| Build before `lifecycle_stage >= incubating` | Premature execution |
| Skip security gate | AI Overseer must approve |
| Push to external repo without approval | `dry_run: true` until proto |
| Claim build success without FAM event | No verification = no claim |

### 7.3 Hermes Build Preconditions

```python
def can_build(envelope: FoundUpGenesisEnvelope) -> Tuple[bool, List[str]]:
    blockers = []
    
    # 1. Envelope must exist and be valid
    if not envelope.envelope_version:
        blockers.append("MISSING_ENVELOPE_VERSION")
    
    # 2. Lifecycle must be beyond genesis_envelope
    if envelope.lifecycle_stage in ("idea", "genesis_envelope"):
        blockers.append("LIFECYCLE_TOO_EARLY")
    
    # 3. All acceptance criteria must have truth states
    for ac in envelope.acceptance_criteria:
        if not ac.truth_state:
            blockers.append(f"MISSING_TRUTH_STATE: {ac.criterion_id}")
    
    # 4. FAM must have task_created for this envelope
    if not fam_has_tasks(envelope.envelope_id):
        blockers.append("NO_FAM_TASKS")
    
    # 5. Security gate must pass
    if not security_gate_passed(envelope.target_surface):
        blockers.append("SECURITY_GATE_FAILED")
    
    return len(blockers) == 0, blockers
```

---

## 8. pfMALL Catalog States

### 8.1 Catalog Binding States

| State | Definition | Visual in Mall |
|-------|------------|----------------|
| `unbound` | Genesis envelope only, no catalog entry | Not visible |
| `discoverable_only` | Incubating, no web frontend | Tile with "Coming Soon" badge |
| `conditional` | Soft-proto, frontend with known gaps | Tile with "Beta" badge |
| `ready` | Proto or beyond, full entry handoff | Normal tile, launchable |

### 8.2 Catalog State Transitions

```
unbound (genesis_envelope)
    |
    v  lifecycle_transition_approved -> incubating
discoverable_only
    |
    v  soft-proto + entry_url set
conditional
    |
    v  proto + launch_readiness = "ready"
ready
```

### 8.3 Manifest Fields by State

| Field | `discoverable_only` | `conditional` | `ready` |
|-------|---------------------|---------------|---------|
| `entry_url` | null | Partial | Full URL |
| `launch_readiness` | `discoverable_only` | `conditional` | `ready` |
| `icon_url` | May be null | Should exist | Required |
| `cabr_contract` | Default | Configured | Enforced |

---

## 9. WSP 97 Triggers

### 9.1 When Truth Sentinel Runs

| Trigger | What Happens |
|---------|--------------|
| **Claim made** | Any assertion in envelope gets truth_state |
| **Artifact created** | New file/doc gets implementation status marker |
| **Lifecycle transition requested** | All acceptance_criteria checked |
| **Externalization requested** | Full CABR V3 validation |
| **Truth drift detected** | AI Overseer alerts, blocks transition |
| **Build requested** | Envelope validation before Hermes runs |

### 9.2 Truth Sentinel Response Matrix

| Violation | Severity | Response |
|-----------|----------|----------|
| Missing truth_state on claim | MEDIUM | Block envelope creation |
| Claim escalation without evidence | HIGH | Block lifecycle transition |
| Build without envelope | CRITICAL | Reject build request |
| Acceptance criteria not met | MEDIUM | Block stage promotion |
| Foreign funding allegation (voteballots example) | CRITICAL | Human review required |

### 9.3 Integration with AI Overseer

AI Overseer (`modules/ai_intelligence/ai_overseer/`) provides:

1. **Security Gate**: `monitor_openclaw_security(force=True)`
2. **Truth Drift Detection**: Compare claimed vs actual states
3. **Gate Violation Alerts**: Emit to FAM event bus
4. **Build Authorization**: Pre-approve Hermes execution

---

## 10. Example: voteballots / vote.foundups.com

### 10.1 Genesis Envelope (Hypothetical)

```json
{
  "envelope_version": "1.0.0",
  "outcome_contract": {
    "description": "AI-native political transparency application. User provides candidate name, receives funding transparency report with evidence trail.",
    "user_story": "As a voter, I want to see who funds political candidates, so that I can make informed decisions",
    "constraints": [
      "All outputs must separate verified facts from inferences",
      "No foreign funding allegations without human review",
      "Evidence trail termination points explicitly marked"
    ]
  },
  "acceptance_criteria": [
    {
      "criterion_id": "VB-AC-001",
      "description": "Entity resolution resolves candidate to FEC ID",
      "method": "automated",
      "pass_condition": "95% accuracy on golden test set",
      "truth_state": "SPECIFIED_UNVERIFIED"
    },
    {
      "criterion_id": "VB-AC-002",
      "description": "Confidence labels applied to all claims",
      "method": "automated",
      "pass_condition": "100% of claims have WSP 97 markers",
      "truth_state": "SPECIFIED_UNVERIFIED"
    },
    {
      "criterion_id": "VB-AC-003",
      "description": "Foreign funding allegations trigger human review",
      "method": "oracle",
      "oracle": "0102 review queue",
      "pass_condition": "No false positives in adversarial test suite",
      "truth_state": "SPECIFIED_UNVERIFIED"
    }
  ],
  "truth_state_map": {
    "outcome_viable": "HIGH_CONFIDENCE_INFERENCE",
    "fec_api_available": "VERIFIED_FACT",
    "ai_pipeline_designed": "HIGH_CONFIDENCE_INFERENCE",
    "frontend_exists": "UNKNOWN"
  },
  "lifecycle_stage": "genesis_envelope",
  "catalog_binding_state": "unbound",
  "target_surface": {
    "platform": "web",
    "entry_url_template": "/f/voteballots",
    "routing_prefix": "/f/voteballots"
  }
}
```

### 10.2 Current State Assessment

| Component | Truth State | Evidence |
|-----------|-------------|----------|
| AI Hooks Architecture | `SPECIFIED_NOT_IMPLEMENTED` | `VOTEBALLOTS_AI_HOOKS_ARCHITECTURE.md` exists |
| TypeScript Interfaces | `SPECIFIED_NOT_IMPLEMENTED` | Types defined in architecture doc |
| Pipeline Implementation | `UNKNOWN` | No src/ code found |
| Test Suite | `UNKNOWN` | No tests/ directory found |
| pfMALL Catalog Entry | `UNKNOWN` | Not in manifest registry |

### 10.3 Next Steps (per this flow)

1. **RedDog** produces formal `FoundUpGenesisEnvelope` from architecture doc
2. **FAM** registers `task_created` for first acceptance criterion
3. **Hermes/Claw** (when `lifecycle_stage` reaches `incubating`) scaffolds module
4. **pfMALL** shows `discoverable_only` entry
5. **CABR V1** begins when first proof_submitted

---

## 11. Open Questions (for 012 Decision)

| Question | Options | Impact |
|----------|---------|--------|
| Where does RedDog envelope production run? | Browser-side (concierge) vs Backend (OpenClaw) | Affects security model |
| How is `envelope_id` assigned? | Client-generated vs FAM-assigned | Affects traceability |
| What is the minimum compute for genesis envelope? | Free tier vs metered | Affects adoption |
| Can 012 bypass RedDog for trusted envelopes? | Yes (emergency) vs No (always via RedDog) | Affects consistency |

---

## 12. Related Documents

| Document | Location | Purpose |
|----------|----------|---------|
| FAM README | `modules/foundups/agent_market/README.md` | FAM structure |
| Manifest Schema | `modules/foundups/docs/PFMALL_FOUNDUP_MANIFEST_SCHEMA.md` | Manifest fields |
| Exfoliation Protocol | `modules/foundups/docs/FOUNDUP_EXFOLIATION_PROTOCOL.md` | Spin-out ladder |
| Compute Access Spec | `modules/foundups/agent_market/docs/COMPUTE_ACCESS_PAYWALL_SPEC.md` | Metered compute |
| WSP 97 | `WSP_knowledge/src/WSP_97_System_Execution_Prompting_Protocol.md` | Truth-state model |
| Red Dog Contract | `public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md` | RedDog identity |
| Hermes Adapter | `modules/foundups/agent/src/hermes_adapter.py` | Hermes builder |
| Hermes DD | `docs/0102_session_briefings/DD_HERMES_FOUNDUP_BUILDER_OPERATIONAL_PROOF_PHASE1.md` | Dry-run proof |
| voteballots AI Hooks | `modules/foundups/voteballots/docs/VOTEBALLOTS_AI_HOOKS_ARCHITECTURE.md` | Example FoundUp |

---

## 13. Truth Summary

| Claim | Truth State | Evidence |
|-------|-------------|----------|
| RedDog -> Genesis Envelope flow designed | `SPECIFIED_NOT_IMPLEMENTED` | This spec document |
| FoundUpGenesisEnvelope schema defined | `SPECIFIED_NOT_IMPLEMENTED` | Section 3.2 of this spec |
| FAM event types documented | `HIGH_CONFIDENCE_INFERENCE` | `models.py` has Task/Proof/Verification; genesis events need addition |
| Hermes consumes validated tasks only | `VERIFIED_FACT` | `hermes_adapter.py` has security gate + exfoliation gate |
| Hermes builds without envelope | `VERIFIED_FACT` (current behavior) | Needs envelope gate addition |
| WSP 97 integration in build flow | `PARTIAL` | Hermes has dry-run; truth sentinel needs wiring |
| pfMALL catalog state machine | `HIGH_CONFIDENCE_INFERENCE` | Manifest schema + shell_core validation |
| voteballots in this flow | `UNKNOWN` | Architecture spec exists; no genesis envelope yet |

---

## 14. Acceptance Criteria for This Spec

| Criterion | Status |
|-----------|--------|
| User flow 012 -> RedDog -> Genesis Envelope documented | PASS |
| Truth-state model per claim/artifact defined | PASS |
| Lifecycle mapping with evidence requirements | PASS |
| FAM pAVS event model documented | PASS |
| Hermes/Claw responsibilities and boundaries defined | PASS |
| pfMALL catalog states documented | PASS |
| WSP 97 triggers enumerated | PASS |
| Example (voteballots) worked through | PASS |
| No implementation code written | PASS |
| No claims of autonomous build being live | PASS |

---

*Specification Author: 0102*
*Date: 2026-04-22*
*Status: ARCHITECTURE SPEC ONLY - No implementation*
