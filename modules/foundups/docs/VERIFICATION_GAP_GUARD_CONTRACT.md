# Verification Gap Guard Contract

**Status**: Specification (ADR)
**Owner**: 0102
**Slice**: `PFM3_VERIFICATION_GAP_GUARD_SPEC_PHASE1`
**WSP References**: WSP 97 (Truth Boundaries), WSP 11 (Interface Protocol)

---

## 1. Purpose

VerificationGapGuard is a policy contract that enforces human review requirements for protected decision classes. AI systems (server-side agents, browser-side Gemma, local models) may surface anomaly signals, but they cannot be the sole judge for decisions that carry fraud accusations, reward denial, reputation impact, legal exposure, or payout finality.

**Canonical Rule**: AI surfaces. Humans decide. The gap is guarded.

---

## 2. Protected Decision Classes

The following decision classes MUST route to human review before finalization. No AI agent (server-side or client-side) may unilaterally execute these:

| Class | Description | Example |
|-------|-------------|---------|
| `fraud_accusation` | Labeling a participant or FoundUp as fraudulent | "This submission is a scam" |
| `scam_accusation` | Labeling content or behavior as a scam | "Fake engagement pattern detected" |
| `deepfake_accusation` | Labeling media as synthetically manipulated | "This video contains deepfake" |
| `reward_denial` | Blocking or denying earned rewards/payouts | "UPS payout denied due to violation" |
| `reputation_impact` | Publishing negative reputation to trust ledger | "Contributor score reduced" |
| `legal_exposure` | Decisions that create legal liability | "Report to platform/authorities" |
| `identity_risk` | Decisions affecting identity/account status | "Account flagged for review" |
| `trust_ledger_publication` | Writing to Public Trust Ledger | "Published verification event" |
| `wallet_action` | Token transfers, staking, payout execution | "UPS transferred to wallet" |
| `payout_finality` | Marking payout as final/irreversible | "CABR payout finalized" |

---

## 3. AI Agent Boundaries

### 3.1 What AI Agents MAY Do

| Action | Allowed | Example |
|--------|---------|---------|
| Surface anomaly signal | YES | "Unusual pattern detected in submission X" |
| Summarize evidence | YES | "3 of 5 validators flagged this task" |
| Open relevant panel | YES | "Opening verification wall for review" |
| Request human review | YES | "Routing to human reviewer for decision" |
| Compute confidence score | YES | "Anomaly confidence: 0.87" |
| Log audit trail | YES | "Anomaly surfaced at 2026-04-27T12:00:00Z" |
| Alert/notify RedDog | YES | "RedDog notification: review required" |

### 3.2 What AI Agents MAY NOT Do

| Action | Blocked | Reason |
|--------|---------|--------|
| Deny rewards unilaterally | BLOCKED | Protected: reward_denial |
| Publish fraud accusation | BLOCKED | Protected: fraud_accusation |
| Write to Public Trust Ledger | BLOCKED | Protected: trust_ledger_publication |
| Execute payout/wallet action | BLOCKED | Protected: wallet_action |
| Finalize reputation score | BLOCKED | Protected: reputation_impact |
| Label as scam/deepfake | BLOCKED | Protected: scam_accusation, deepfake_accusation |
| Trigger legal action | BLOCKED | Protected: legal_exposure |
| Suspend/ban identity | BLOCKED | Protected: identity_risk |

---

## 4. Browser/Local AI Truth Boundary

Browser-side and local AI (e.g., WebGPU Gemma, on-device models) have additional constraints beyond server-side agents:

### 4.1 Local AI MAY Do

| Action | Allowed |
|--------|---------|
| Classify user intent locally | YES (advisory only) |
| Summarize low-risk content | YES (display only) |
| Surface anomaly flags to UI | YES (visual indicator) |
| Pre-filter obvious spam | YES (soft filter, reversible) |
| Suggest next action | YES (recommendation only) |

### 4.2 Local AI MAY NOT Do

| Action | Blocked | Reason |
|--------|---------|--------|
| Bypass human/policy review | BLOCKED | Local model output is advisory |
| Deny rewards | BLOCKED | Protected decision class |
| Accuse fraud/scam/deepfake | BLOCKED | Protected decision class |
| Publish to trust ledger | BLOCKED | Protected decision class |
| Trigger payout/wallet action | BLOCKED | Protected decision class |
| Make final reputation decision | BLOCKED | Protected decision class |
| Route around pAVS verification | BLOCKED | pAVS is authoritative |

### 4.3 Device Routing Constraint

Local device routing (e.g., "send to local Gemma for classification") CANNOT substitute for server-side pAVS/CABR verification. Device-side models are triage/UX assistants, not verification authorities.

---

## 5. RedDog Notification Protocol

RedDog is the user-facing agent surface in p.fMALL. When VerificationGapGuard intercepts a protected decision:

### 5.1 RedDog MAY

- Display alert/notification about pending review
- Summarize what anomaly was detected
- Open the Verification Wall panel
- Explain what human review means
- Track notification acknowledgment

### 5.2 RedDog MAY NOT

- Execute the protected decision on behalf of AI
- Claim the decision has been made
- Punish or deny rewards before human review
- Publish accusations to any ledger
- Finalize legal/reputation decisions

### 5.3 Notification Event

```typescript
interface RedDogVerificationAlert {
  alert_id: string;
  event_id: string;              // VerificationGapEvent.event_id
  foundup_id: string;
  summary: string;               // Human-readable summary
  action_required: "human_review" | "acknowledge" | "info_only";
  panel_to_open?: "verification_wall" | "task_detail" | "evidence";
  created_at: string;            // ISO 8601
}
```

---

## 6. Integration Points

### 6.1 pFMALL Verification Wall

- UI surface for human reviewers
- Displays pending VerificationGapEvents
- Allows approve/reject/escalate actions
- Records decision with reviewer identity

### 6.2 RedDog Notification Event

- Surfaces alerts in user's RedDog panel
- Links to Verification Wall for action
- Tracks acknowledgment state

### 6.3 pAVS Verification Seam

- Existing `PAVSVerificationResult` flows through guard
- Protected decisions blocked until human review
- `cabr_ready` and `payout_ready` remain false until cleared

### 6.4 Future CABR/PoB/Reward Engine

- Consumes cleared verification events
- Will not process events with `requires_human_review = true`
- Final payout requires human-cleared path

### 6.5 Future Public Trust Ledger

- Protected decision class: `trust_ledger_publication`
- Guard blocks AI-initiated ledger writes
- Human review required before any publication

---

## 7. VerificationGapEvent Schema

```typescript
interface VerificationGapEvent {
  // Identity
  event_id: string;              // Deterministic: sha256(foundup_id:tenant_id:anomaly_type:created_at)[:16]
  foundup_id: string;            // Which FoundUp this relates to
  tenant_id: string;             // Which tenant/user triggered
  
  // Source
  source_panel: string;          // "reddog" | "verification_wall" | "agent_surface" | "local_gemma"
  source_agent?: string;         // Agent ID if applicable
  
  // Anomaly
  anomaly_type: AnomalyType;     // See AnomalyType enum
  risk_class: ProtectedClass;    // Which protected class
  confidence: number;            // 0.0-1.0 (AI confidence, advisory only)
  
  // Evidence
  evidence_refs: string[];       // Links to evidence artifacts
  evidence_summary?: string;     // Human-readable summary
  
  // Review Gate
  requires_human_review: boolean;  // Always true for protected classes
  human_reviewer_id?: string;      // Set after review
  human_decision?: "approved" | "rejected" | "escalated";
  human_decision_at?: string;      // ISO 8601
  human_decision_reason?: string;
  
  // Agent Boundaries
  allowed_agent_actions: AgentAction[];
  blocked_agent_actions: AgentAction[];
  
  // Audit
  created_at: string;            // ISO 8601
  updated_at: string;            // ISO 8601
}

type AnomalyType =
  | "pattern_mismatch"
  | "confidence_below_threshold"
  | "duplicate_submission"
  | "velocity_anomaly"
  | "content_flag"
  | "identity_mismatch"
  | "evidence_incomplete"
  | "external_report";

type ProtectedClass =
  | "fraud_accusation"
  | "scam_accusation"
  | "deepfake_accusation"
  | "reward_denial"
  | "reputation_impact"
  | "legal_exposure"
  | "identity_risk"
  | "trust_ledger_publication"
  | "wallet_action"
  | "payout_finality";

type AgentAction =
  | "surface_anomaly"
  | "summarize_evidence"
  | "open_panel"
  | "request_review"
  | "compute_confidence"
  | "log_audit"
  | "notify_reddog"
  | "deny_reward"           // BLOCKED
  | "publish_accusation"    // BLOCKED
  | "write_trust_ledger"    // BLOCKED
  | "execute_payout"        // BLOCKED
  | "finalize_reputation"   // BLOCKED
  | "trigger_legal"         // BLOCKED
  | "suspend_identity";     // BLOCKED
```

---

## 8. WSP 97 Truth Boundaries

### 8.1 What This Contract DOES

- Defines protected decision classes
- Specifies AI agent boundaries (allowed/blocked)
- Specifies browser/local AI boundaries
- Defines RedDog notification protocol
- Lists integration points
- Provides event schema
- Establishes review gate requirement

### 8.2 What This Contract DOES NOT

- Implement fraud detection algorithms
- Implement legal/reputation judgment logic
- Implement reward denial mechanics
- Implement browser Gemma
- Modify PWA UI code
- Modify OpenClaw/Hermes/FAM/pAVS code
- Create runtime enforcement (skeleton phase)

### 8.3 What This Contract ENABLES

- Future VerificationGapGuard implementation
- Future Verification Wall UI
- Future RedDog notification integration
- Future CABR/PoB guard integration
- Future Public Trust Ledger guard
- Consistent policy across all AI surfaces

---

## 9. Follow-Up: Skeleton/Interface Recommendation

**Next atomic slice**: `PFM3_VERIFICATION_GAP_GUARD_SKELETON_PHASE2`

Skeleton should create:

```
modules/foundups/pfmall/src/verification_gap_guard.py
  - VerificationGapEvent dataclass
  - ProtectedClass enum
  - AnomalyType enum
  - AgentAction enum
  - is_protected_action(action: AgentAction) -> bool
  - requires_human_review(event: VerificationGapEvent) -> bool
  - block_protected_action(event: VerificationGapEvent, action: AgentAction) -> BlockedActionResult

modules/foundups/pfmall/tests/test_verification_gap_guard.py
  - test_protected_classes_require_review
  - test_allowed_actions_pass
  - test_blocked_actions_fail
  - test_local_ai_boundary_enforced
```

**Do not implement skeleton in this slice.**

---

## 10. Related Documents

- [PFMALL_SHELL_CONTRACT.md](PFMALL_SHELL_CONTRACT.md) — Shell responsibilities
- [PFMALL_DATA_ISOLATION_MODEL.md](PFMALL_DATA_ISOLATION_MODEL.md) — Data boundaries
- [PFMALL_STATE_OVERLAY_CONTRACT.md](PFMALL_STATE_OVERLAY_CONTRACT.md) — State management
- [proof_of_compute_receipt.py](../../communication/moltbot_bridge/src/proof_of_compute_receipt.py) — Receipt schema
- [pavs_verification_seam.py](../../communication/moltbot_bridge/src/pavs_verification_seam.py) — pAVS integration

---

## Appendix: Decision Record

**ADR-VGG-001**: Verification Gap Guard Policy Contract

- **Date**: 2026-04-27
- **Status**: Accepted
- **Context**: AI agents (server and browser) can surface anomalies but must not make protected decisions
- **Decision**: Establish policy contract with explicit protected classes and agent boundaries
- **Consequences**: All AI surfaces must route protected decisions to human review
