# External Swarm OpenClaw Hermes Current State Reconciliation (Phase 1)

**Slice**: `EXTERNAL_SWARM_OPENCLAW_HERMES_CURRENT_STATE_RECONCILIATION_PHASE1`
**Worker**: W8
**Date**: 2026-05-17
**Mode**: Audit / spec only
**WSP Lock**: WSP_00 → WSP_97 → WSP_50 → WSP_46 → WSP_48 → WSP_80 → WSP_100 → WSP_15

---

## 1. Retrieval Summary

### HoloIndex Preflight Results

| Query | Top Hits |
|-------|----------|
| OpenClaw dry run policy flags | `openclaw_permission_policy.py`, `openclaw_foundup_orchestrator.py`, `WSP_11`, `HXA1_AUDIT` |
| FoundUps Agent Workspace fork plan | `hermes_adapter.py`, `hermes_job_executor.py`, `FOUNDUPS_AGENT_WORKSPACE_FORK_PLAN.md` |
| WRE Hermes delegate runtime | `hermes_job_executor.py`, `foundup_job_consumer.py`, `WRE_DESTRUCTIVE_ACTION_GUARD.md` |
| RedDog 012 digital twin | `twin_boot.py`, `lora_trainer.py`, `WSP_73_012_Digital_Twin_Architecture.md` |
| WSP 48 recursive improvement | `wsp48_improver.py`, `recursive_exchange_protocol.py`, `WSP_48_Recursive_Self_Improvement_Protocol.md` |

**Internal Artifact Coverage**: 40+ files across code, WSP, docs, knowledge base.

---

## 2. External Source Summary

### Sources Inspected

| Source | Status | Last Verified |
|--------|--------|---------------|
| [github.com/openclaw/openclaw/releases](https://github.com/openclaw/openclaw/releases) | Fetched | 2026-05-17 |
| [github.com/outsourc-e/hermes-workspace](https://github.com/outsourc-e/hermes-workspace) | Fetched | 2026-05-17 |
| [github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | Searched | 2026-05-17 |

---

## 3. OpenClaw Current State

### Release Versions

| Type | Version | Date |
|------|---------|------|
| **Latest Beta** | v2026.5.16-beta.3 | 2026-05-16 |
| **Latest Stable** | Not explicitly listed (pre-v2026.5.x) | - |

### Key Features Since 2026.5.2 (Affecting FoundUps Assumptions)

| Feature | Description | Impact on FoundUps |
|---------|-------------|-------------------|
| **Claude CLI Backend Restored** | Anthropic staff confirmed OpenClaw-style Claude CLI usage allowed | Validates our OpenClaw→Claude Code integration path |
| **Subagent Task Visibility** | Delegation appears in first visible message, not system prompt | May affect WRE task packet framing |
| **Hydrated resolvedSkills Cache** | Skills cached across warm gateway turns keyed by redacted config | Aligns with our skill snapshot pattern |
| **In-process Subagent Dispatch** | Same-process handoffs bypass Gateway RPC loopback | Relevant for nested agent orchestration |
| **MCP Servers per Agent ID** | Optional allowlist scoping MCP to specific agents | Supports our per-FoundUp capability isolation |
| **Media/File Sniffing** | Input bytes sniffed before trusting MIME headers | Security pattern we should adopt |
| **Model Auth Status Card** | OAuth health and provider pressure visibility | Observability pattern for CABR |
| **Session Data Scoping by Agent ID** | Prevents cross-leakage between agents | Validates our tenant isolation design |

### Features NOT Yet in OpenClaw (Still FoundUps-Specific)

| Feature | Status |
|---------|--------|
| CABR consensus pipeline | FoundUps-only |
| WSP governance framework | FoundUps-only |
| pAVS verification seam | FoundUps-only |
| Proof-of-compute receipts | FoundUps-only |
| WRE retention semantics | FoundUps-only |

---

## 4. Hermes Workspace Current State

### Architecture (v2 as of 2026-05)

| Component | Port | Function |
|-----------|------|----------|
| **UI Layer** | 3000 | React/TypeScript workspace: chat, terminal, memory, skills, inspector |
| **Gateway** | 8642 | Real-time SSE streaming, `/v1/chat/completions`, model enumeration |
| **Dashboard** | 9119 | Sessions, model mix, cost ledger, attention card, ops strip, MCP catalog |
| **Worker Pool** | N/A | Persistent tmux-backed workers with role-based dispatch |

### Key Design Decisions

| Decision | Implication |
|----------|-------------|
| **Zero-fork** | Runs on vanilla `NousResearch/hermes-agent` via official installer |
| **Not a fork—a wrapper** | FoundUps can adopt same pattern without forking Hermes Agent |
| **Role-based dispatch** | Builder, reviewer, docs, research, ops, triage, QA, lab lanes |
| **Persistent tmux workers** | Context preserved across tasks (aligns with our WRE session model) |
| **Kanban board** | Backlog, ready, running, review, blocked, done lanes |
| **Checkpoint system** | Proof-bearing task verification and handoff tracking |

---

## 5. Hermes Agent / Swarm Surface

### Core Capabilities (NousResearch/hermes-agent)

| Capability | Description |
|------------|-------------|
| **Isolated Subagents** | Own conversations, terminals, Python RPC scripts |
| **Orchestrator Role** | Can spawn workers, gated by `delegation.orchestrator_enabled` |
| **Max Spawn Depth** | Bounded by `delegation.max_spawn_depth` (default 2) |
| **File Coordination Layer** | Concurrent siblings share filesystem state without clobbering |
| **YantrikDB Memory** | `think()` canonicalizes, `conflicts()` surfaces contradictions, `recall()` with `why_retrieved` |
| **Autonomous Skill Creation** | Skills created after complex tasks, self-improve during use |
| **Skills Hub Standard** | Compatible across Hermes, Claude Code, Cursor, Codex |

### Delegation Architecture

```
Orchestrator (orchestrator_enabled=True)
    └── Worker 1 (spawn_depth=1)
    └── Worker 2 (spawn_depth=1)
        └── Sub-worker 2a (spawn_depth=2, max reached)
```

---

## 6. FoundUps Existing Assumptions

### From FOUNDUPS_AGENT_WORKSPACE_FORK_PLAN.md (2026-05-03)

| Assumption | Status |
|------------|--------|
| Fork from outsourc-e/hermes-workspace | **STALE** — v2 is zero-fork wrapper |
| Verified SHA: `6485d2002f` | **STALE** — new commits since 2026-05-02 |
| FoundUps Core owns governance, Workspace owns execution | **VALID** |
| Gateway API / WSP Task Packet boundary | **VALID** |
| tmux workers for persistent context | **VALID** |

### From HXA1 Audit (2026-05-07)

| Assumption | Status |
|------------|--------|
| Runtime path stops at queue | **VALID** — still true |
| HERMES_DELEGATE_ENABLED=0 default | **VALID** — controlled harness proven (HXA14) |
| Two divergent `execute_foundup_job` symbols | **VALID** — architectural debt remains |
| Receipts unreachable in canonical path | **VALID** — no job.status mutation in WRE path |

### From Memory: hermes_architecture.md (30 days old)

| Assumption | Status |
|------------|--------|
| 012→0102→MCP→Hermes flow | **VALID** |
| FAM breadcrumbs for audit trail | **VALID** |
| No WRE per FoundUp (adapters only) | **VALID** — aligns with Hermes Workspace wrapper model |
| HermesFoundUpBuilder v0.5.1 | **POTENTIALLY STALE** — version may have changed |

---

## 7. Stale Assumptions

| Assumption | Source | Why Stale | Update Required |
|------------|--------|-----------|-----------------|
| Fork hermes-workspace | FORK_PLAN.md | v2 is zero-fork wrapper, not fork | Update doc to "wrap, not fork" |
| Verified SHA 6485d2002f | FORK_PLAN.md | Commits since 2026-05-02 | Re-audit upstream HEAD |
| HermesFoundUpBuilder v0.5.1 | memory | May have updated | Verify current version |
| No in-process subagent dispatch | implicit | OpenClaw now supports same-process handoffs | Evaluate for WRE |
| Skills not cached across turns | implicit | OpenClaw caches hydrated skills | Adopt pattern |

---

## 8. Adopt / Wrap / Fork / Avoid Matrix

| External Capability | Exists Externally | Exists Internally | Adopt | Wrap | Fork | Avoid | Evidence | Risk |
|---------------------|-------------------|-------------------|-------|------|------|-------|----------|------|
| **Hermes Workspace UI** | YES (outsourc-e) | NO | - | YES | - | - | Zero-fork model proven | LOW |
| **tmux Worker Pool** | YES (hermes-workspace) | NO | - | YES | - | - | Role-based dispatch | LOW |
| **OpenClaw Gateway** | YES (openclaw) | YES (moltbot_bridge) | - | - | - | - | Already integrated | NONE |
| **Claude CLI Backend** | YES (openclaw) | YES (claude-code) | YES | - | - | - | Anthropic approved | LOW |
| **MCP per Agent ID** | YES (openclaw) | PARTIAL | YES | - | - | - | Per-FoundUp isolation | LOW |
| **Media/File Sniffing** | YES (openclaw) | NO | YES | - | - | - | Security hardening | LOW |
| **Skills Hub Standard** | YES (hermes) | YES (skillz/) | YES | - | - | - | Cross-agent compat | LOW |
| **YantrikDB Memory** | YES (hermes) | NO (use HoloIndex) | - | - | - | AVOID | HoloIndex is sovereign | MED |
| **Hermes Agent Core** | YES (NousResearch) | NO | - | YES | - | - | Wrapper via adapter | LOW |
| **Delegation max_spawn_depth** | YES (hermes) | NO (use WRE) | - | - | - | - | WRE handles depth | NONE |
| **Checkpoint System** | YES (hermes-workspace) | YES (CABR) | - | - | - | - | CABR is sovereign | NONE |
| **Orchestrator Role** | YES (hermes) | YES (WRE) | - | - | - | - | WRE orchestrates | NONE |

---

## 9. Impact on WRE

| Area | Impact | Action |
|------|--------|--------|
| **Session Data Scoping** | OpenClaw scopes by agent ID | WRE already does per-job isolation — ALIGNED |
| **In-process Subagent Dispatch** | Evaluate for nested WRE jobs | Future slice: consider bypassing HTTP for internal routing |
| **Skills Cache Warming** | Adopt warm cache pattern | Consider caching skill snapshots in WRE consumer |
| **Delegation Depth Bounds** | Already bounded by HXA gates | No change needed |
| **Retention Semantics** | FoundUps-only | External systems do not affect |

---

## 10. Impact on RedDog / 012 Digital Twin

| Area | Impact | Action |
|------|--------|--------|
| **Preference Capsule** | No external equivalent | Remain sovereign |
| **LoRA Training** | Hermes has autonomous skill creation | Complementary, not conflicting |
| **Edge Observer** | No direct Hermes equivalent | Remain sovereign |
| **012 Memory** | YantrikDB exists but HoloIndex preferred | Do not adopt YantrikDB |

---

## 11. Impact on FoundUps Agent Workspace

| Area | Impact | Action |
|------|--------|--------|
| **Fork Plan** | Stale — update to wrapper model | Revise FOUNDUPS_AGENT_WORKSPACE_FORK_PLAN.md |
| **Upstream SHA** | Stale — re-verify | Audit latest hermes-workspace HEAD |
| **Kanban Lanes** | Hermes has backlog/ready/running/review/blocked/done | Align with WRE job states |
| **Role-based Dispatch** | Builder/reviewer/docs/research/ops/triage/QA/lab | Map to FoundUp DAE roles |

---

## 12. Impact on HXA Safety Gates

| Gate | External Feature | Impact | Action |
|------|------------------|--------|--------|
| **HERMES_DELEGATE_ENABLED** | Hermes has `delegation.orchestrator_enabled` | Similar pattern | ALIGNED |
| **controlled_harness** | No external equivalent | Remain HXA-gated | No change |
| **repo_created=False** | No external equivalent | Remain HXA-gated | No change |
| **production_source_modified=False** | No external equivalent | Remain HXA-gated | No change |
| **Real delegate invocation** | Hermes has `delegate_task` | HXA16 required before adoption | BLOCKED |

---

## 13. Required Doc Updates

| Document | Update Required |
|----------|-----------------|
| `FOUNDUPS_AGENT_WORKSPACE_FORK_PLAN.md` | Change "fork" to "wrap"; update verified SHA; add v2 architecture notes |
| `memory/hermes_architecture.md` | Verify HermesFoundUpBuilder version; add Hermes Workspace v2 notes |
| `HXA1_AUDIT` | Add reference to OpenClaw v2026.5.16 features |
| `WSP_106_FoundUp_API_Gateway_Protocol.md` | Consider adding MCP per-agent-ID scoping |

---

## 14. Recommended Next Slices

**WSP_97 Correction**: HXA16 through HXA30 are already complete/merged. This audit must not reopen stale HXA slices.

| Priority | Slice | Rationale |
|----------|-------|-----------|
| **P0** | `FOUNDUPS_AGENT_WORKSPACE_WRAPPER_MODEL_UPDATE_PHASE1` | Update stale "fork" language to "wrap"; keep external systems optional; no runtime change |
| **P1** | `OPENCLAW_V2026_5_FEATURE_ADOPTION_AUDIT_PHASE1` | Audit MCP per-agent-ID, skills cache, media sniffing, Claude CLI; decide adopt/wrap without live delegation |
| **P2** | `HERMES_OPENCLAW_CAPABILITY_RECONCILIATION_AUDIT_PHASE1` | Compare HXA/Hermes guard stack against updated external capabilities; keep `HERMES_DELEGATE_ENABLED=0`; no live dispatch |

---

## WSP_97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| OpenClaw latest beta fetched | VERIFIED | v2026.5.16-beta.3 |
| Hermes Workspace v2 is zero-fork wrapper | VERIFIED | GitHub README |
| FoundUps fork plan is stale | VERIFIED | Predates v2 architecture |
| HXA gates remain required | VERIFIED | No external equivalent |
| HXA16-HXA30 already complete/merged | VERIFIED | Not reopened by this audit |
| No live delegation enabled | ENFORCED | Audit only |
| No external system mandatory | ENFORCED | All adopt/wrap optional |
| No payout/DAO readiness claims | ENFORCED | Not applicable to audit |

### External Systems Optionality Confirmation

| External System | Status | Optionality |
|-----------------|--------|-------------|
| OpenClaw | Optional wrapper/adoption layer | FoundUps can operate without |
| Hermes Workspace | Optional wrapper | FoundUps can operate without |
| Hermes Agent | Optional reference | FoundUps can operate without |
| HoloIndex | **Sovereign memory source** | Required (not external) |
| YantrikDB | **Not adopted** | HoloIndex preferred |

---

## Test Evidence

```
python -m pytest modules/infrastructure/wre_core/tests/test_hermes_job_executor.py -q
94 passed in 0.42s
```

---

## Sources

- [OpenClaw Releases](https://github.com/openclaw/openclaw/releases)
- [Hermes Workspace](https://github.com/outsourc-e/hermes-workspace)
- [NousResearch Hermes Agent](https://github.com/NousResearch/hermes-agent)
- [Hermes Agent Documentation](https://hermes-agent.nousresearch.com/docs/)

---

*Audit performed by Worker W8 under WSP_00 → WSP_97 → WSP_50 → WSP_46 → WSP_48 → WSP_80 → WSP_100 → WSP_15.*
*Slice: EXTERNAL_SWARM_OPENCLAW_HERMES_CURRENT_STATE_RECONCILIATION_PHASE1*
