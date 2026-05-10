# HXA5 External Federation Architecture Audit: p.fMALL + pAVS

**Audit Date**: 2026-05-09  
**Slice**: `HXA5_EXTERNAL_FEDERATION_PFMALL_PAVS_AUDIT_PHASE1`  
**Worker**: W2  
**WSP Lock**: WSP 00 → WSP 97 → WSP 15 → WSP 50  
**Mode**: Architecture audit — no code edits

---

## 1. Executive Summary

### Verdict: `ARCHITECTURE_SPECIFIED_TRANSPORT_REAL_BACKENDS_PARTIAL`

The external federation architecture for p.fMALL + pAVS is **well-specified at the architecture level**. The pAVS MCP Server has real HTTP/JSON transport (MCPA8). 6/8 tools have real backends. Key gaps remain in deployment, SDK packaging, and CABR backend.

**Internal factory status**: OpenClaw → Hermes trunk execution PROVEN (HXA3).

**External federation status**: Architecture locked (WSP 103), transport real, SDKs not deployed.

---

## 2. Architecture Evidence Summary

### 2.1 Governing Protocols

| Protocol | Purpose | Status |
|----------|---------|--------|
| WSP 103 | FoundUp Federation Protocol | ACTIVE since 2026-03-15 |
| WSP 104 | Route Namespace and Tenant Isolation | ACTIVE |
| WSP 96 | MCP Governance and Consensus | ACTIVE |

### 2.2 Key Architecture Documents

| Document | Location | Purpose |
|----------|----------|---------|
| `PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md` | `modules/foundups/docs/` | External repo + in-scope route model |
| `PFMALL_FOUNDUP_ENTRY_AND_STAKE_GATE_CONTRACT.md` | `modules/foundups/docs/` | Entry flow and stake verification |
| `PFMALL_SHELL_CONTRACT.md` | `modules/foundups/docs/` | Shell responsibilities and postMessage |
| `EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md` | `holo_index/docs/` | HoloIndex bridge contract |

---

## 3. Two Access Surfaces

The external federation has **two distinct access surfaces**:

### 3.1 p.fMALL Shell (User-Facing)

**Purpose**: PWA gateway for user navigation into FoundUps.

**Access Model**:
- Users install p.fMALL as PWA
- Navigate to `/f/{foundup_id}` routes
- FoundUps may live in separate repos but deploy to in-scope routes
- Shell mediates auth (wallet connect + stake verification)

**Entry Flow**:
```
Mall Discovery → FoundUp Welcome → Public Community → Stakeholder Gate → Stakeholder Interior
```

**Current Status**:
- Mall Discovery: DEPLOYED (`public/member/index.html`)
- FoundUp Welcome: TRANSITIONAL (`foundup.html`)
- Stakeholder Gate: NOT IMPLEMENTED
- Stakeholder Interior: NOT IMPLEMENTED

### 3.2 pAVS MCP Server (Agent/Repo-Facing)

**Purpose**: Infrastructure API for external FoundUp repos to access compute.

**Access Model**:
- External FoundUps register via `foundup_register` tool
- Receive API key scoped to their `foundup_id`
- Call pAVS tools via HTTP/JSON POST `/tool`
- Auth enforced per tool (MCPA1 Slice 6)

**Current Status**:
- Transport: `HTTP_JSON` (REAL — MCPA8)
- Auth: `BASIC_AUTH_ENFORCEMENT` (REAL — Slice 6)
- Registry: `LOCAL_JSON` persistent (REAL — Slice 7)
- Backends: 6/8 REAL, 2/8 PLACEHOLDER

---

## 4. pAVS Tool Backend Status

| Tool | Backend Status | Delegates To |
|------|---------------|--------------|
| `holo_search` | REAL | S2/HoloIndex |
| `fam_emit` | REAL | FAM DAEmon |
| `pattern_recall` | REAL | PatternMemory |
| `pattern_store` | REAL | PatternMemory |
| `gemma_classify` | REAL | GemmaRAGInference |
| `qwen_plan` | REAL | QwenInferenceEngine |
| `cabr_validate` | PLACEHOLDER | Hardcoded `score=0.85` |
| `foundup_register` | STUB | Generates key, persists locally |

**Tracked Remediation**: MCPA10+ for CABR backend.

---

## 5. External FoundUp Integration Pattern

### 5.1 Registration Flow

```
1. External FoundUp calls POST /tool
   {"tool_name": "foundup_register", "arguments": {"foundup_id": "X", "repo_url": "..."}}

2. pAVS validates uniqueness per WSP 104 namespace guardrails
   - unique foundup_id
   - unique routing_prefix = /f/{foundup_id}
   - unique data_namespace = idb_{foundup_id}

3. pAVS generates API key: fp_xxxxxxxxxxxx

4. Persists to ~/.pavs_mcp/registrations.json

5. Returns {api_key, endpoint}
```

### 5.2 Tool Call Flow

```
1. External FoundUp calls POST /tool
   {
     "tool_name": "holo_search",
     "arguments": {"query": "...", "limit": 10},
     "api_key": "fp_xxxxxxxxxxxx"
   }

2. pAVS validates api_key ownership

3. Rejects cross-tenant foundup_id attempts

4. Delegates to real backend (S2/HoloIndex)

5. Returns {result, meta: {real_backend: true, delegated_to: "S2"}}
```

### 5.3 SDK Packaging Status

| SDK | Package | Registry | Status |
|-----|---------|----------|--------|
| TypeScript | `@foundups/pavs-sdk` | npm | PLANNED |
| Python | `foundups-pavs` | PyPI | PLANNED |

**Current workaround**: Direct HTTP/JSON calls to `/tool` endpoint.

---

## 6. Access Tiers (WSP 103)

| Tier | Criteria | Access Level |
|------|----------|--------------|
| **Angel** | $195/mo subscription | All pre-OPO FoundUps |
| **Du Staker** | UPS staked in specific F_i | That FoundUp's repo |
| **Contributor** | PRs merged / CABR verified | Repos they contributed to |
| **Member** | Free tier registered | Public repos only |

**Autonomous Access Flow** (WSP 103 Section "Autonomous Access Gating"):
```
User subscribes → FAM event → Access DAE → GitHub API → Invite sent
```

**Status**: Architecture specified, Access DAE NOT IMPLEMENTED.

---

## 7. p.fMALL Shell Contract Summary

### 7.1 Shell Responsibilities (LOCKED)

- App Shell (service worker, offline cache)
- Launch Catalog (`catalog.json`)
- Router (`/f/{foundup_id}/*`)
- Auth Gateway (wallet connect, tier verification)
- Nav Chrome (top bar, wallet display)
- HoloIndex Client (search bar)
- Notification Bus (cross-FoundUp postMessage)
- Telemetry Collector (ROC metrics)

### 7.2 Shell Non-Responsibilities (LOCKED)

- FoundUp internal state/UI/business logic
- FoundUp-specific data storage (each owns IndexedDB namespace)
- Agent execution (OpenClaw/WRE, not shell)
- Token operations (blockchain layer, not shell)
- FoundUp-to-FoundUp direct communication

### 7.3 Communication Protocol

All shell ↔ FoundUp communication uses `postMessage` with typed schema:

```typescript
interface ShellMessage {
  type: "shell_event";
  event: ShellEventType;  // route_change | auth_state | ups_balance | notification | theme_change | shell_ready
  payload: Record<string, unknown>;
  timestamp: string;
  nonce: string;
}

interface FoundUpMessage {
  type: "foundup_event";
  foundup_id: string;
  event: FoundUpEventType;  // navigate | agent_request | ups_spend | notification_send | title_update | ready
  payload: Record<string, unknown>;
  timestamp: string;
  nonce: string;
}
```

---

## 8. External Repo Model (WSP 103)

### 8.1 Target Architecture

```
GitHub Dual-Remote Pattern:

FOUNDUPS Org (origin):           Foundup Personal (backup):
  FOUNDUPS/AutoPost (PRIVATE) <--> Foundup/AutoPost (PRIVATE)
  FOUNDUPS/GotJunk (PRIVATE)  <--> Foundup/GotJunk (PRIVATE)
  ...

Connection:
  [FoundUp Repo] --HTTP/JSON--> [pAVS MCP Server] --> [WRE Infrastructure]
```

### 8.2 Spin-Out Candidates

| Module | Status | Priority |
|--------|--------|----------|
| gotjunk | In monorepo | P1 |
| move2japan | In monorepo | P1 |
| social_twin | In monorepo | P2 |
| pqn_portal | In monorepo | P2 |
| AutoPost | Already separate | DONE |

### 8.3 Two Pipes (External FoundUp Route Contract)

| Pipe | Purpose | Protocol |
|------|---------|----------|
| Control Pipe | Metadata, task catalog, agent assignment | API/service contract |
| Experience Pipe | User entry to FoundUp | Route navigation (`/f/{foundup_id}`) |

**Invariant**: Mall brokers requests into FoundUp's exposed task/control surface. Mall does not invent work for a FoundUp.

---

## 9. Gap Analysis

### 9.1 Blockers

| Gap | Impact | Remediation |
|-----|--------|-------------|
| `cabr_validate` is placeholder | External FoundUps get fake CABR scores | MCPA10 |
| SDKs not published | External devs must use raw HTTP | MCPA11 |
| Access DAE not implemented | Autonomous GitHub access gating unavailable | Separate slice |
| Stakeholder Gate not implemented | No wallet-verified interior access | Phase 2 per entry contract |

### 9.2 Non-Blockers

| Item | Status | Notes |
|------|--------|-------|
| HTTP transport | REAL | MCPA8 landed |
| Auth enforcement | REAL | Slice 6 landed |
| Registry persistence | REAL | Slice 7 landed |
| 6/8 tool backends | REAL | Delegating to real infrastructure |
| Architecture docs | COMPLETE | WSP 103, 104, shell contract, route contract |

---

## 10. Recommended Next Steps

### P0: Complete Internal Factory First
- HXA3 trunk proof PASSED (VoteBallots dry-run reaches Hermes)
- Next: HXA4 real execution sandbox (actual FoundUp build)

### P1: CABR Backend (MCPA10)
- Connect `cabr_validate` to real CABR engine
- Remove placeholder `score=0.85`

### P2: SDK Packaging (MCPA11)
- Publish `@foundups/pavs-sdk` to npm
- Publish `foundups-pavs` to PyPI

### P3: Access DAE Implementation
- Implement `FoundUpAccessDAE` per WSP 103
- Connect to GitHub API for autonomous access gating

### P4: Stakeholder Gate (Phase 2)
- Implement wallet connect integration
- Stake threshold verification
- Gate UI

---

## 11. WSP 97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| pAVS MCP transport is real | VERIFIED | README.md: `HTTP_JSON (MCPA8)` |
| 6/8 tools have real backends | VERIFIED | README.md status banner |
| Auth enforcement is real | VERIFIED | `MCPA1 Slice 6` |
| Registry persists locally | VERIFIED | `~/.pavs_mcp/registrations.json` |
| WSP 103 defines federation | VERIFIED | Protocol ACTIVE since 2026-03-15 |
| SDKs are deployed | FALSE | README.md: `Planned` |
| Access DAE is implemented | FALSE | WSP 103: code snippet, not deployed |
| CABR backend is real | FALSE | `cabr_validate`: hardcoded placeholder |

### 11.1 Uncertainty Acknowledgment

| Item | Uncertainty |
|------|-------------|
| CABR engine connection complexity | MEDIUM |
| SDK publishing timeline | LOW |
| Access DAE GitHub API rate limits | MEDIUM |
| Stakeholder gate wallet integration | HIGH |

---

## 12. Sources

### Internal (FoundUps)
- `modules/infrastructure/pavs_mcp/README.md` — pAVS status banner
- `modules/infrastructure/pavs_mcp/INTERFACE.md` — API documentation
- `modules/foundups/docs/PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md` — External repo model
- `modules/foundups/docs/PFMALL_FOUNDUP_ENTRY_AND_STAKE_GATE_CONTRACT.md` — Entry flow
- `modules/foundups/docs/PFMALL_SHELL_CONTRACT.md` — Shell responsibilities
- `holo_index/docs/EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md` — HoloIndex bridge
- `WSP_framework/src/WSP_103_FoundUp_Federation_Protocol.md` — Federation architecture
- `WSP_framework/src/WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md` — Namespace guardrails

---

## 13. Conclusion

External federation architecture is **well-specified and partially implemented**. The pAVS MCP Server has real transport and 75% real backends. The p.fMALL shell contract defines clear isolation boundaries. WSP 103/104 lock the federation and namespace rules.

**Internal factory must work first** (HXA3 proves trunk). Then CABR backend completion (MCPA10) enables external FoundUps to receive real validation scores. SDK publishing (MCPA11) enables ergonomic integration.

**Verdict**: Ready for external FoundUp onboarding once CABR backend is real and SDKs are published.

---

*Audit performed by Worker W2 under WSP 97 truth boundaries.*
