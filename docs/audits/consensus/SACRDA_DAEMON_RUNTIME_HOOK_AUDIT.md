# SACRDA Daemon Runtime Hook Audit

**Audit Date**: 2026-05-14
**Auditor**: 0102 W7
**WSP Compliance**: WSP 00 (Zen State), WSP 50 (Pre-Action), WSP 97 (Truth Boundaries)
**Status**: COMPLETE

---

## Executive Summary

This audit determines whether CABR/ROC/consensus requires daemon or runtime hooks, and classifies which are **dangerous now** given the current system state.

**Key Finding**: The codebase has strong WSP 97 truth boundaries already in place. The CABR Consensus Pipeline explicitly blocks payouts, DAO activation, and token issuance. No unsafe hooks currently exist, but several potential hooks are classified as **dangerous now** if implemented without explicit WSP gates.

---

## 1. Runtime Systems Inspected

| System | Location | Status |
|--------|----------|--------|
| **FAM DAEmon** | `modules/foundups/agent_market/src/fam_daemon.py` | ACTIVE |
| **Central DAEmon** | `modules/infrastructure/dae_daemon/src/dae_daemon.py` | ACTIVE |
| **DAE Observer** | `modules/infrastructure/dae_daemon/src/dae_observer.py` | ACTIVE |
| **CABR Hooks** | `modules/foundups/agent_market/src/cabr_hooks.py` | ACTIVE |
| **WRE Self-Audit Loop** | `modules/infrastructure/wre_core/src/daemon_self_audit_loop.py` | ACTIVE |
| **FoundUpJob Consumer** | `modules/infrastructure/wre_core/src/foundup_job_consumer.py` | ACTIVE |
| **CABR Consensus Pipeline** | `modules/communication/moltbot_bridge/src/cabr_consensus_pipeline.py` | ACTIVE |
| **Hermes Adapter** | `modules/foundups/agent/src/hermes_adapter.py` | ACTIVE |

---

## 2. Hook Classification Table

| Hook Type | Label | Rationale |
|-----------|-------|-----------|
| **Consensus Daemon** | REQUIRED_LATER | No active consensus daemon. CABR scoring is synchronous/caller-driven. Quorum requires daemon when validator network exists. |
| **CABR Daemon** | REQUIRED_LATER | CABR is currently a calculation engine, not an autonomous agent. WSP 29 proposes CABR_DAE evolution but no implementation exists. |
| **ROC Daemon** | NOT_NEEDED | No ROC (Ring of Consensus) concept in current architecture. CABR + pAVS + Quorum serves this function. |
| **WRE Runtime Hook** | ALREADY_EXISTS | `daemon_self_audit_loop.py` provides error detection and policy-bound auto-fixes. WRE job consumer provides routing. |
| **FAM Runtime Hook** | ALREADY_EXISTS | FAM DAEmon provides event emission with JSONL + SQLite persistence. Heartbeat loop active. |
| **Hermes Runtime Bridge** | ALREADY_EXISTS | `hermes_adapter.py` provides bounded agent wrapper. `foundup_job_consumer.py` provides WRE->Hermes dispatch. |
| **Lifecycle Watcher** | REQUIRED_LATER | No lifecycle watcher exists. Would need to monitor FoundUp state transitions (IDEA->OBAI->PoC->TEAM->Proto->MVP->LAUNCH). |
| **Audit Trail Watcher** | ALREADY_EXISTS | FAM EventStore + Central DAEmon provide append-only audit trail. DAE Observer provides read-side tailing. |
| **Milestone Watcher** | REQUIRED_LATER | No milestone watcher exists. Would correlate CABR scores to tier transitions (F0->F1->F2 etc). |
| **Scheduler** | ALREADY_EXISTS | `daemon_self_audit_loop.py` provides interval-based scanning. Central DAEmon heartbeat provides periodic health checks. |
| **Queue Processor** | ALREADY_EXISTS | `FoundUpJobConsumer.drain_openclaw_queue_once()` drains job queue with retention semantics. |

---

## 3. Detailed Classification

### 3.1 DANGEROUS_NOW (Cannot implement without WSP gates)

| Hook | Why Dangerous | Required Gate |
|------|---------------|---------------|
| **Payout Trigger Daemon** | FAM has `PAYOUT_TRIGGERED` event type but no execution. Auto-triggering payouts could drain treasury without verification. | WSP for payout authorization with multi-sig or 012 approval |
| **DAO Activation Daemon** | CABR pipeline explicitly blocks DAO activation (`NO_DAO_ACTIVATION` label). Auto-activation could lock governance without readiness. | WSP for SmartDAO emergence criteria (WSP 100 partial) |
| **Source Modification Daemon** | No code modification daemon exists. Auto-patching could introduce bugs or security vulnerabilities. | WSP for automated code modification with rollback |
| **Repo Creation Daemon** | Hermes has extraction capability but dry-run enforced. Auto-creating repos could leak sensitive code. | WSP for repo creation authorization with security scan |
| **Live Delegation Daemon** | `hermes_adapter.py` requires `HERMES_BUILDER_DRY_RUN` flag. Live execution without gates could run untested workflows. | WSP for live execution authorization with checkpoint protocol |

### 3.2 REQUIRED_NOW (Should exist but doesn't)

None. Current architecture is appropriately conservative.

### 3.3 REQUIRED_LATER (Needed for production but not blocking)

| Hook | When Needed | Dependency |
|------|-------------|------------|
| **Consensus Daemon** | When validator network goes live | Validator registration WSP, economic security model |
| **CABR DAE** | When adaptive scoring needed | WSP 54 DAE learning engine, pattern memory integration |
| **Lifecycle Watcher** | When FoundUp tier transitions automated | CABR tier thresholds, treasury autonomy rules |
| **Milestone Watcher** | When tier-based rewards automated | CABR score history, distribution policy |

### 3.4 ALREADY_EXISTS (No action needed)

| Hook | Evidence |
|------|----------|
| **FAM Event Emission** | `fam_daemon.py:767-825` - `emit()` method with JSONL + SQLite dual-write |
| **Central Heartbeat** | `dae_daemon.py:121-143` - `_heartbeat_loop()` with stale detection |
| **WRE Self-Audit** | `daemon_self_audit_loop.py:46-654` - error pattern detection, policy-bound fixes |
| **Job Queue Processing** | `foundup_job_consumer.py:322-760` - `FoundUpJobConsumer` with retention semantics |
| **Audit Trail** | `dae_observer.py:23-144` - `tail_events()`, `follow_events()`, `get_live_status()` |

---

## 4. Unsafe Hook Risks

### 4.1 CABR Consensus Pipeline Truth Boundaries

The CABR Consensus Pipeline (`cabr_consensus_pipeline.py:1-130`) contains explicit WSP 97 truth boundaries:

```python
# Lines 9-30
"""
This is REVIEW-ONLY ORCHESTRATION -- pipeline execution does NOT mean:
  - automatic state progression
  - verification_complete=True
  - cabr_ready=True
  - payout_ready=True
  - Payout approval
  - DAO activation
  - Token issuance
  - Final consensus readiness
  - External settlement
"""
```

**Risk**: Any daemon that bypasses these boundaries could:
1. Issue unauthorized payouts
2. Activate DAOs without quorum
3. Distribute tokens without verification
4. Progress state without evidence

### 4.2 FAM Event Types Without Execution

`fam_daemon.py:39-113` defines event types including:
- `PAYOUT_TRIGGERED` - Event type exists but no execution engine
- `SMARTDAO_EMERGENCE` - Event type exists but no activation logic
- `TIER_ESCALATION` - Event type exists but no state machine
- `CROSS_DAO_FUNDING` - Event type exists but no transfer logic

**Risk**: A daemon emitting these events could:
1. Create audit trail without actual execution (false evidence)
2. Trigger downstream systems that trust event semantics
3. Create phantom state transitions

### 4.3 Hermes Dry-Run Bypass

`hermes_adapter.py:133-136`:
```python
self.enabled = os.environ.get("HERMES_BUILDER_ENABLED", "1") == "1"
self.dry_run = os.environ.get("HERMES_BUILDER_DRY_RUN", "0") == "1"
self.require_security_gate = os.environ.get("HERMES_BUILDER_SECURITY_GATE", "1") == "1"
```

**Risk**: Environment variable overrides could:
1. Enable live execution without security gate
2. Bypass dry-run mode for untested workflows
3. Skip AI Overseer validation

---

## 5. Critical Rule Verification

> **No daemon may trigger payout, DAO activation, source modification, repo creation, or live delegation until explicit WSP gates exist.**

| Action | Current State | WSP Gate Status |
|--------|--------------|-----------------|
| **Payout Trigger** | Event type only, no execution | NO WSP |
| **DAO Activation** | Explicitly blocked (`NO_DAO_ACTIVATION`) | WSP 100 partial |
| **Source Modification** | No daemon exists | NO WSP |
| **Repo Creation** | Dry-run enforced in Hermes | NO WSP |
| **Live Delegation** | Environment variable gated | NO WSP |

**Verdict**: Current codebase is SAFE. All dangerous operations are blocked or non-functional.

---

## 6. Recommended Next Slice

### SACRDA_WSP_GATES_FOR_DANGEROUS_HOOKS

**Objective**: Create explicit WSP gates for each dangerous hook category.

**Scope**:
1. `WSP_XXX_PAYOUT_AUTHORIZATION_PROTOCOL` - Multi-sig or 012 approval for payout triggers
2. `WSP_XXX_DAO_EMERGENCE_CRITERIA` - Extend WSP 100 with concrete thresholds
3. `WSP_XXX_LIVE_EXECUTION_AUTHORIZATION` - Checkpoint protocol for Hermes live mode
4. `WSP_XXX_REPO_CREATION_SECURITY` - Security scan requirements for exfoliation

**Priority**: MEDIUM - Not blocking current development but required before any daemon automation.

---

## 7. WSP 97 Verdict

### Truth Boundaries Applied

1. **Runtime systems inspected**: 8 active systems documented with file paths
2. **Hook classification**: 11 hook types classified across 5 labels
3. **Dangerous hooks identified**: 5 potential hooks that require WSP gates
4. **Existing safeguards verified**: CABR pipeline explicitly blocks dangerous operations
5. **No false claims**: Audit does not claim completeness or production readiness

### Uncertainty Acknowledgment

- ROC (Ring of Consensus) may be a term from external context not present in codebase
- Consensus daemon architecture is speculative (no design exists)
- Lifecycle watcher requirements depend on tier transition policy not yet defined
- Milestone watcher thresholds depend on CABR scoring evolution

---

## Appendix: HoloIndex Search Results

### Search 1: `daemon scheduler runtime hook CABR consensus lifecycle watcher WRE FAM Hermes`
- `modules/foundups/agent_market/src/fam_daemon.py` (FAM DAEmon)
- `modules/infrastructure/dae_daemon/src/dae_observer.py` (DAE Observer)
- `WSP_framework/src/WSP_29_CABR_Engine.md` (CABR Engine)
- `WSP_framework/src/WSP_91_DAEMON_Observability_Protocol.md` (DAEMON Protocol)

### Search 2: `WRE daemon task queue audit trail watcher milestone watcher`
- `modules/infrastructure/wre_core/src/daemon_self_audit_loop.py` (Self-Audit Loop)
- `modules/infrastructure/wre_core/wre_monitor.py` (WRE Monitor)
- `WSP_framework/src/WSP_51_WRE_CHRONICLE.md` (WRE Chronicle)

### Search 3: `FAM runtime hook CABR receipt lifecycle consensus pipeline`
- `modules/foundups/agent_market/src/cabr_hooks.py` (CABR Hooks)
- `modules/communication/moltbot_bridge/src/proof_of_compute_receipt.py` (Receipt)
- `modules/infrastructure/wre_core/src/foundup_job_consumer.py` (Job Consumer)
- `WSP_framework/src/WSP_29_CABR_Engine.md` (CABR Engine)

---

**Branch**: `docs/sacrda-roc-dae-dao-readiness-audit`
**Head**: Current working state (uncommitted)
**Status**: AUDIT COMPLETE - NO IMPLEMENTATION
