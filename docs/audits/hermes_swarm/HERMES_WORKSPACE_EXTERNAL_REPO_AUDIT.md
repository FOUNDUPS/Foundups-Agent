# HERMES_WORKSPACE_EXTERNAL_REPO_AUDIT

**Date**: 2026-05-03  
**Status**: COMPLETE  
**Slice**: FOUNDUPS_WORKSPACE_EXTERNAL_REPO_AUDIT_RECONCILE_PHASE1  
**Type**: External Repository Inspection Audit

---

## 1. External Repository Inspected

| Field | Value |
|-------|-------|
| **Repository** | https://github.com/outsourc-e/hermes-workspace |
| **Commit SHA** | `6485d2002f6a5c615fa000b2d8f0945d7dadc738` |
| **Commit Date** | 2026-05-02T18:37:06Z |
| **Commit Message** | fix(swarm): write runtime.json on stop + sync roster model on start (#238) |
| **License** | MIT (Copyright (c) 2026 Eric outsourc-e) |
| **Version** | v2.1.3 (per README badge) |

---

## 2. Prior Audit Correction

**The prior Python Hermes Agent hook audit targeted the wrong surface.**

| Prior Audit | Target | Actual Content |
|-------------|--------|----------------|
| `vendor/hermes-agent/gateway/hooks.py` | Python gateway hooks | Runtime event callbacks |
| `vendor/hermes-agent/tools/delegate_tool.py` | In-session delegation | Single-session subagents |

**Correct target**: `outsourc-e/hermes-workspace` is a **web-based swarm control plane** with:
- tmux-backed persistent workers
- Kanban task board UI
- SwarmBrief/checkpoint protocol
- Multi-worker orchestration
- Memory/handoff management

The vendored `hermes-agent` is the **runtime backend**. The `hermes-workspace` is the **swarm control plane UI**.

---

## 3. Integration Surfaces Documented

### 3.1 swarm.yaml

**Location**: Repository root  
**Purpose**: Worker roster configuration

**Structure**:
```yaml
workers:
  swarm1:
    name: "Overflow"
    role: "overflow"
    model: "claude-sonnet-4-5-20241022"
    status: "offline"
    maxConcurrentTasks: 1
    acceptsBroadcast: false
  swarm2:
    name: "Foundation"
    role: "foundation"
    model: "claude-sonnet-4-5-20241022"
    status: "ready"
    specialty: "Backend runtime, API design, state management"
    ...
```

**Key Fields**:
- `workers.<id>.role`: Preset role (orchestrator, builder, reviewer, etc.)
- `workers.<id>.model`: OpenAI-compatible model identifier
- `workers.<id>.status`: ready | offline | busy
- `workers.<id>.specialty`: Natural language capability description
- `workers.<id>.maxConcurrentTasks`: Concurrent task limit
- `workers.<id>.acceptsBroadcast`: Whether to receive broadcast tasks

**FoundUps Mapping**: Maps to `foundups-swarm.yaml` with 0102-prefixed roles.

---

### 3.2 SwarmBrief Packets

**Source**: `docs/swarm/ARCHITECTURE.md` Section 3  
**Purpose**: Minimal operating contract for worker execution

**Schema** (inferred from documentation):
```
brief_id       : string    # Unique identifier
worker         : string    # Target worker ID
project        : string    # Project context

goal           : string    # One sentence objective
why_now        : string    # Trigger/urgency
scope          : string[]  # Bounded work items
deliverables   : string[]  # Exact output paths
test_or_proof  : string[]  # Verification commands
constraints    : string[]  # Hard limits
budget         : number    # Wall-clock hours

escalation:
  on_blocked   : string    # Route when blocked
  on_done      : string    # Route when complete
```

**Key Principle**: "A brief is not a prompt dump. It is the smallest operating contract that lets a worker execute without inventing scope."

**FoundUps Mapping**: `WSPTaskPacket` schema in `WRE_GATEWAY_ADAPTER_DESIGN.md` Section 4.

---

### 3.3 Checkpoint Protocol

**Source**: `docs/swarm/ARCHITECTURE.md` checkpoint section  
**Purpose**: Structured state/evidence reporting from workers

**Format**:
```
STATE: DONE | BLOCKED | NEEDS_INPUT | HANDOFF | IN_PROGRESS | NEEDS_REVIEW
FILES_CHANGED: path1, path2 | none
COMMANDS_RUN: cmd1, cmd2 | none
RESULT: Concrete result with evidence
BLOCKER: Description of obstacle | none
NEXT_ACTION: Exact recommended next step
```

**Key Principle**: "Good checkpoints contain evidence. Bad checkpoints contain adjectives."

**FoundUps Mapping**: `ConsumerResult` in `WRE_GATEWAY_ADAPTER_DESIGN.md` Section 5.

---

### 3.4 Kanban/Task API

**Source**: `src/server/swarm-kanban-store.ts`  
**Endpoint**: Internal store, not HTTP API

**Lanes**: `['backlog', 'ready', 'running', 'review', 'blocked', 'done']`

**Card Fields**:
- `id`: UUID
- `title`: Task description
- `spec`: Detailed specification
- `acceptanceCriteria`: Array of criteria
- `assignedWorker`: Worker ID
- `reviewer`: Reviewer ID
- `missionId`: Mission grouping
- `reportPath`: Path to report artifacts
- `createdAt`, `updatedAt`: Timestamps

**Persistence**: `~/.hermes/swarm2-kanban.json`

**FoundUps Mapping**: FoundUpJob queue + FAM Kanban view (future).

---

### 3.5 tmux Dispatch/Lifecycle

**Source**: `src/routes/api/swarm-dispatch.ts`, `src/server/swarm-lifecycle.ts`

**Dispatch Endpoint**: `POST /api/swarm-dispatch`

**Request Schema**:
```typescript
{
  workerIds: string[];           // Target workers
  prompt: string;                // Task instruction
  assignments?: Assignment[];    // Structured assignments
  timeoutSeconds?: number;       // 10-600 seconds
  waitForCheckpoint?: boolean;   // Sync wait
  missionId?: string;            // Mission grouping
  missionTitle?: string;         // Mission label
}
```

**Lifecycle States** (token-based):
- `healthy`: < 250k tokens
- `watch`: 250k-400k tokens
- `handoff_required`: 400k-500k tokens
- `renew_required`: > 500k tokens

**Handoff Mechanism**:
1. Worker prompted to write checkpoint
2. Session killed
3. New session started with resume prompt

**FoundUps Mapping**: `HermesJobExecutor` dispatch + `ConsumerResult` lifecycle.

---

## 4. Comparison with Canonical Docs

### 4.1 FOUNDUPS_AGENT_WORKSPACE_FORK_PLAN.md

| Aspect | Canonical Doc | External Repo Audit |
|--------|---------------|---------------------|
| External repo URL | Listed (no SHA) | SHA `6485d20...` verified |
| Architecture boundary | Documented | Confirmed accurate |
| SwarmBrief schema | Inferred | Confirmed from ARCHITECTURE.md |
| Checkpoint protocol | Documented | Confirmed format |
| Worker roles | 11 roles listed | 12 workers in swarm.yaml |
| tmux lifecycle | Documented | Confirmed states/thresholds |

**Verdict**: Canonical doc is accurate. Add verified SHA reference.

### 4.2 WRE_GATEWAY_ADAPTER_DESIGN.md

| Aspect | Canonical Doc | External Repo Audit |
|--------|---------------|---------------------|
| WSP task packet | Defined | Compatible with SwarmBrief |
| Checkpoint mapping | Defined | Compatible with external format |
| Truth field preservation | Defined | No external counterpart (FoundUps-specific) |
| Retention semantics | Defined | No external counterpart (FoundUps-specific) |

**Verdict**: Canonical doc is FoundUps-specific extension. No conflicts with external repo.

### 4.3 HERMES_WORKSPACE_BINDING_CONTRACT.md

| Aspect | Canonical Doc | External Repo Audit |
|--------|---------------|---------------------|
| WorkspaceBinding schema | Defined | Not in external repo (FoundUps-specific) |
| Path constraints | Defined | External uses `WORKSPACE PATH` prompt injection |
| Evidence output | Defined | External uses mission-specific paths |

**Verdict**: Canonical doc is FoundUps-specific contract. External uses simpler prompt injection.

---

## 5. Recommendations

### 5.1 Amend Canonical Fork Plan

Add verified external SHA to `FOUNDUPS_AGENT_WORKSPACE_FORK_PLAN.md`:

```markdown
## 1. Executive Summary

...

- **Source Commit**: `6485d2002f6a5c615fa000b2d8f0945d7dadc738` (2026-05-02)
- **Audit Reference**: [HERMES_WORKSPACE_EXTERNAL_REPO_AUDIT.md](../audits/hermes_swarm/HERMES_WORKSPACE_EXTERNAL_REPO_AUDIT.md)
```

### 5.2 No Updates Needed

The following docs are accurate and do not require updates:
- `WRE_GATEWAY_ADAPTER_DESIGN.md` - FoundUps-specific, no conflicts
- `HERMES_WORKSPACE_BINDING_CONTRACT.md` - FoundUps-specific, no conflicts

### 5.3 Future Work

| Item | Priority | Notes |
|------|----------|-------|
| Pin external version | P1 | Before fork, pin to verified SHA |
| Test dispatch API | P2 | Verify endpoint schema against audit |
| Validate checkpoint format | P2 | Parse external checkpoints in ConsumerResult |

---

## 6. WSP 97 Verdict

| Boundary | Status |
|----------|--------|
| No live delegation enabled | PASS - docs only |
| No verification_complete claims | PASS - always false |
| No CABR/payout claims | PASS - no token operations |
| No autonomous execution claims | PASS - dry-run only |
| Truth fields preserved | PASS - WSP 97 fields documented |

**Overall**: WSP 97 COMPLIANT

---

## 7. Files Inspected

### External Repository (outsourc-e/hermes-workspace)

| File | Purpose |
|------|---------|
| `README.md` | Project overview, setup instructions |
| `swarm.yaml` | Worker roster configuration |
| `docs/swarm/ARCHITECTURE.md` | SwarmBrief/checkpoint protocol |
| `docs/swarm/ROLES.md` | Worker role definitions |
| `docs/swarm/QUICKSTART.md` | Setup and first mission guide |
| `skills/workspace-dispatch/SKILL.md` | Mission decomposition logic |
| `src/routes/api/swarm-dispatch.ts` | Dispatch API endpoint |
| `src/server/swarm-kanban-store.ts` | Kanban persistence |
| `src/server/swarm-lifecycle.ts` | Worker lifecycle management |
| `src/server/swarm-memory.ts` | Checkpoint/memory storage |
| `src/server/swarm-notifications.ts` | Event routing |
| `LICENSE` | MIT license |

### FoundUps Repository (this repo)

| File | Purpose |
|------|---------|
| `docs/architecture/FOUNDUPS_AGENT_WORKSPACE_FORK_PLAN.md` | Canonical fork plan |
| `docs/architecture/WRE_GATEWAY_ADAPTER_DESIGN.md` | Gateway adapter design |
| `docs/audits/hermes_swarm/HERMES_WORKSPACE_BINDING_CONTRACT.md` | Workspace binding contract |

---

## Appendix: External Repo Structure

```
outsourc-e/hermes-workspace/
├── README.md
├── swarm.yaml
├── package.json
├── docs/
│   └── swarm/
│       ├── ARCHITECTURE.md
│       ├── QUICKSTART.md
│       ├── README.md
│       ├── ROLES.md
│       └── SKILLS.md
├── skills/
│   └── workspace-dispatch/
│       └── SKILL.md
└── src/
    ├── routes/
    │   └── api/
    │       ├── swarm-dispatch.ts
    │       ├── swarm-kanban.ts
    │       └── swarm-health.ts
    └── server/
        ├── swarm-kanban-store.ts
        ├── swarm-lifecycle.ts
        ├── swarm-memory.ts
        └── swarm-notifications.ts
```

---

**Audit completed by**: 0102 W3  
**WSP Compliance**: WSP 50 (Pre-Action), WSP 97 (Truth Boundaries)
