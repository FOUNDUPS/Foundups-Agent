# HoloIndex Public FoundUp Connective Trust Surface Documentation — Phase 1

**Date**: 2026-05-22
**Slice**: HOLOINDEX_PUBLIC_FOUNDUP_CONNECTIVE_TRUST_SURFACE_DOCS_PHASE1
**Base Commit**: `600eee482` (origin/main)
**Branch**: `docs/holoindex-public-foundup-connective-trust-surface-phase1`
**Mode**: DOCUMENTATION ONLY

---

## WSP 97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| DOCS_ONLY | YES |
| HOLOINDEX_PUBLIC_FOUNDUP_CONTRACT_ONLY | YES |
| DUAL_IDENTITY_BOUNDARY_ENFORCED | YES |
| NO_HOLOINDEX_CORE_MUTATION | YES |
| NO_BACKEND_ACCESS_ENABLEMENT | YES |
| NO_INTERNAL_INDEX_EXPOSURE | YES |
| NO_SECRET_EXPOSURE | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_PFMALL_CATALOG_MUTATION | YES |
| NO_ROUTE_CHANGE | YES |
| NO_UI_IMPLEMENTATION | YES |
| NO_MCP_CHANGE | YES |
| NO_CI_CHANGE | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Source of Truth

### 1.1 Canonical Documentation Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| External FoundUp Current State Audit | `docs/audits/holoindex_external_foundup/CURRENT_STATE_AUDIT.md` | TRACKED |
| External FoundUp Bridge Contract | `holo_index/docs/EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md` | TRACKED |
| FoundUp Manifest (holoindex_prod_01) | `modules/foundups/holoindex_prod_01/foundup_manifest.json` | TRACKED |
| Mall Video Catalog Entry | `public/member/mall-video-catalog.json` (lines 11364-11402) | TRACKED |
| Portfolio Display Component Audit | `docs/audits/architecture/FOUNDUPS_PORTFOLIO_DISPLAY_COMPONENT_PHASE1.md` | TRACKED |
| Canonical Inventory Audit | `docs/audits/architecture/FOUNDUP_CANONICAL_INVENTORY_AND_STAGE_REGISTRY_AUDIT_PHASE1.md` | TRACKED |

### 1.2 Security/Trust Evidence Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Red-Team Family A (Scope Lock) | `docs/audits/security/FOUNDUPS_AGENT_REDTEAM_FAMILY_A_SCOPE_LOCK_PHASE1.md` | TRACKED |
| Red-Team Family B (Credential Exfil) | `docs/audits/security/FOUNDUPS_AGENT_REDTEAM_FAMILY_B_CREDENTIAL_EXFIL_PHASE1.md` | TRACKED |
| Red-Team Family C (HoloIndex Poisoning) | `docs/audits/security/FOUNDUPS_AGENT_REDTEAM_FAMILY_C_HOLOINDEX_POISONING_PHASE1.md` | TRACKED |
| Red-Team Harness Provenance Check | `docs/audits/security/FOUNDUPS_AGENT_REDTEAM_HARNESS_PROVENANCE_CHECK_PHASE1.md` | TRACKED |
| Credential Access Layer PoC | `docs/audits/security/FOUNDUPS_CREDENTIAL_ACCESS_LAYER_POC_PHASE1.md` | TRACKED |
| Credential Access Layer Spec | `docs/audits/security/FOUNDUPS_CREDENTIAL_ACCESS_LAYER_SPEC_PHASE1.md` | TRACKED |

### 1.3 Work Ledger/Brain Continuity Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Work Ledger Brain Current State | `docs/audits/architecture/FOUNDUPS_WORK_LEDGER_BRAIN_CURRENT_STATE_AUDIT_PHASE1.md` | TRACKED |
| Work Ledger HoloIndex Integration | `docs/audits/holoindex_search_quality/FOUNDUPS_WORK_LEDGER_HOLOINDEX_INTEGRATION_PHASE1.md` | TRACKED |
| Work Ledger Search Integration | `docs/audits/holoindex_search_quality/FOUNDUPS_WORK_LEDGER_HOLOINDEX_SEARCH_INTEGRATION_PHASE1.md` | TRACKED |

---

## 2. Dual Identity Boundary

HoloIndex operates with two distinct identities that MUST remain separated:

### 2.1 Internal HoloIndex (Protected Infrastructure)

**Purpose**: Foundups retrieval/memory/work-ledger infrastructure used by agents.

**Consumers**:
- 0102 (primary orchestrator)
- WRE (Work Retrieval Engine)
- MCP (Model Context Protocol servers)
- OpenClaw (agent builder gateway)
- Hermes (FoundUp builder supervisor)
- Worker agents (Qwen, Gemma, etc.)

**Protected Assets**:
- Internal ChromaDB vector collections (path not disclosed publicly)
- Code/WSP/docs/knowledge index embeddings
- Work ledger slice tracking (`navigation_work_ledger` collection)
- Pattern memory (`refactoring_patterns.json`)
- Agent conversation mining corpus
- Internal semantic search API

**Access Control**:
- Python-only access via `holo_index.py` CLI or `HoloIndex` class
- MCP tool access via `holo_index:semantic_code_search`, `holo_index:wsp_protocol_lookup`
- No HTTP/REST exposure to external systems
- No public query endpoint

### 2.2 External HoloIndex FoundUp (Public Connective Surface)

**Purpose**: Public discovery surface explaining how FoundUps connect.

**Identity**:
- `foundup_id`: `holoindex_prod_01`
- `routing_prefix`: `/f/holoindex_prod_01`
- `tier`: `INFRA`
- `lifecycle_stage`: `incubating`
- `launch_readiness`: `discoverable_only`

**Scope**:
- Explains what FoundUps exist
- Explains lifecycle stages
- Explains which have public PoCs
- Explains which are gated prototypes
- Explains registry backing
- Does NOT provide direct access to internal HoloIndex

**Current Status**:
- Manifest tracked: YES (`modules/foundups/holoindex_prod_01/foundup_manifest.json`)
- Catalog entry: YES (`public/member/mall-video-catalog.json`)
- UI scaffold: STUB ONLY (`entry_url`: empty)
- Bridge adapter: STUB ONLY (postMessage protocol defined, not live backend)

---

## 3. External HoloIndex FoundUp Purpose

The external HoloIndex FoundUp exists to:

### 3.1 FoundUp Ecosystem Map

- List all registered FoundUps with public visibility
- Show lifecycle stage for each (incubating, proto, externalized, federated)
- Indicate PoC availability (public vs. gated vs. invite-only)
- Display registry backing status

### 3.2 Connective Explanation

- How p.fMALL routes to individual FoundUp entries
- How FoundUps connect to each other
- How the ecosystem operates as pAVS (Peer-to-Peer Autonomous Venture System)
- How CABR (Continuous Agent Build Review) gates FoundUp transitions

### 3.3 Trust Surface

- Published safety claims (WSP compliance)
- Red-team test evidence (without exploit payloads)
- Credential isolation posture
- Agent supervision architecture

---

## 4. Public Connective Surface Contract

### 4.1 Public Information Allowed

| Category | What May Be Displayed |
|----------|----------------------|
| FoundUp Identity | `foundup_id`, `name`, `tagline`, `tier`, `lifecycle_stage` |
| Public Status | `launch_readiness`, `is_invite_only`, PoC availability |
| Route Contract | `routing_prefix`, `entry_url` (if public) |
| Ecosystem Position | Category, capabilities (high-level) |
| Safety Claims | WSP compliance labels, red-team pass/fail verdicts |
| Merged Evidence | PR numbers, slice IDs (no commit hashes with secrets) |

### 4.2 Public Information NOT Allowed

| Category | What Must Remain Internal |
|----------|--------------------------|
| Index Internals | ChromaDB paths, collection names, embedding models |
| Query Mechanics | Search algorithms, ranking factors, boost weights |
| Exploit Details | Red-team payload strings, bypass patterns |
| Secret Fixtures | Test credentials, mock vault values |
| Agent Conversations | 012.txt content, mining corpus |
| Backend Access | MCP tool invocation, HoloIndex Python API |

### 4.3 Bridge Contract Summary

Per `holo_index/docs/EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md`:

- **Inbound**: External UI sends `agent_request` postMessage to p.fMALL shell
- **Routing**: Shell interceptor handles `openclaw_search` route
- **Backend**: Stub adapter (not live HoloIndex)
- **Outbound**: `agent_response` with results (or stub/error)
- **Status**: `stub: true` until live backend registration

---

## 5. Internal Infrastructure Non-Exposure Rules

### 5.1 Never Expose

| Asset | Rule |
|-------|------|
| Internal ChromaDB collection paths | Path never disclosed publicly |
| `holo_index/core/*.py` | Module internals never described publicly |
| `sentence_transformers` model | Model name/path never public |
| Work ledger entries | Individual slice content never public |
| Agent memory | Pattern storage never public |
| MCP tool schemas | Internal tool parameters never public |

### 5.2 Never Enable

| Action | Rule |
|--------|------|
| Public semantic search | No HTTP endpoint for HoloIndex queries |
| External repo indexing | Only internal FoundUp retrieval allowed |
| Federated index access | No cross-tenant index sharing |
| Direct ChromaDB query | No SQL/API exposure |

---

## 6. FoundUp Ecosystem Map Responsibilities

The external HoloIndex FoundUp SHOULD eventually display:

### 6.1 Registered FoundUps

| FoundUp | Tier | Stage | Public PoC |
|---------|------|-------|------------|
| gotjunk_001 | F0_DAE | proto | YES |
| kosei | F0_DAE | incubating | NO |
| voteballots | F0_DAE | incubating | NO |
| trade | F0_DAE | incubating | NO |
| magadoom_001 | F0_DAE | incubating | NO |
| holoindex_prod_01 | INFRA | incubating | DISCOVERABLE_ONLY |

### 6.2 Platform/Infrastructure Layers

| Layer | Type | Status |
|-------|------|--------|
| p.fMALL | PLATFORM | IMPLEMENTED |
| FAM | INFRA | IMPLEMENTED |
| HoloIndex | INFRA | OPERATIONAL (internal) |

### 6.3 External FoundUps

| FoundUp | Repo | Status |
|---------|------|--------|
| AutoPost | `O:/repos/AutoPost` | POC_EXISTS |
| Science Swarm Hub | `O:/repos/science-swarm-hub` | EXTERNAL |

---

## 7. Safety/Trust Evidence To Surface

### 7.1 Red-Team Protection Posture

**Families Tested**:

| Family | Focus | Tests | Status |
|--------|-------|-------|--------|
| A (Scope Lock) | Agent cannot write outside granted paths | 8 | PASS |
| B (Credential Exfil) | Agent cannot exfiltrate credentials | 6+ | PASS |
| C (HoloIndex Poisoning) | Agent rejects poisoned retrieval results | 12 | PASS |

**Public Claims Allowed**:
- Scope lock prevents unauthorized file modification
- Credential access uses fail-closed mock vault
- Poisoned retrieval rejected with `POISONED_RETRIEVAL_REJECTED`
- Three-part assertion: behavioral outcome + reason code + audit emission

### 7.2 Credential Isolation Posture

**Current State**:
- Mock vault PoC complete (47/47 tests pass)
- `op://vault/item/field` reference format defined (WSP 71 Annex A)
- Fail-closed on: unavailable, invalid format, unknown reference, TTL expired, session invalid
- Secret values never logged (hash-only audit trail)

**Future State**:
- 1Password/vault runtime access planned
- No secrets in prompts/logs/context

### 7.3 Provenance/Path-Tier Checks

Per red-team harness:
- Path normalization blocks `..` traversal
- Tenant isolation enforced (`tenants/A/` cannot access `tenants/B/`)
- WSP 104 namespace compliance verified

---

## 8. Redacted/Internal-Only Evidence

The following evidence EXISTS but must NOT be surfaced publicly:

| Evidence | Why Internal |
|----------|-------------|
| Exploit payloads | Security risk if disclosed |
| Bypass patterns | Could enable attacks |
| Mock credential values | "TEST_VALUE_DO_NOT_USE_IN_PRODUCTION" |
| Internal fixture paths | Implementation detail |
| Exact harness reason-code wiring | Implementation detail |
| ChromaDB schema | Backend detail |

---

## 9. Relationship to p.fMALL Portfolio Display

### 9.1 Current Integration

Per `FOUNDUPS_PORTFOLIO_DISPLAY_COMPONENT_PHASE1.md`:

- HoloIndex entry rendered in `/f/` portfolio showcase
- Displays "Dual Identity" badge
- Shows framing: "Internally, HoloIndex is Foundups retrieval/memory infrastructure... Externally, HoloIndex may also have a public FoundUp surface..."
- Links "View Details" to `/f/holoindex_prod_01` landing

### 9.2 Catalog Binding

Per `public/member/mall-video-catalog.json` (line 11364+):
```json
{
  "foundup_id": "holoindex_prod_01",
  "title": "HoloIndex",
  "description": "Enterprise-grade artifact and memory retrieval system for the p.fMALL shell.",
  "lifecycle_stage": "incubating",
  "launch_readiness": "discoverable_only",
  "routing_prefix": "/f/holoindex_prod_01",
  "entry_copy": "HoloIndex is discoverable but remains in explicit stub mode until the backend relay clears."
}
```

---

## 10. Relationship to Registry / Work Ledger / MCP / Hermes-OpenClaw

### 10.1 Registry

- `modules/foundups/foundup_registry.json` is canonical source
- HoloIndex is type `infra` (not type `foundup`)
- Registry supports typed entities per `FOUNDUP_CANONICAL_INVENTORY_AND_STAGE_REGISTRY_AUDIT_PHASE1.md`

### 10.2 Work Ledger

- Work ledger tracks slices/PRs/workers
- HoloIndex indexes work ledger entries for retrieval
- `navigation_work_ledger` collection enables slice tracking queries
- WSP 60/70 integration complete

### 10.3 MCP

- `holo_index` MCP server provides tools:
  - `semantic_code_search`: Find existing implementations
  - `wsp_protocol_lookup`: Retrieve WSP documentation
  - `cross_reference_search`: Multi-domain knowledge search
- MCP scope validation protects tool boundaries
- No public MCP access

### 10.4 Hermes-OpenClaw

- OpenClaw is agent builder gateway
- Hermes supervises FoundUp building
- HoloIndex serves as retrieval backend for both
- No external Hermes/OpenClaw invocation allowed

---

## 11. Future UI Implementation Slices

### 11.1 Immediate (Post-Documentation)

| Slice | Purpose | Priority |
|-------|---------|----------|
| `HOLOINDEX_EXTERNAL_BUNDLE_TRACK_PHASE1` | Track untracked bridge adapter/UI scaffold | P1 |
| `HOLOINDEX_BRIDGE_TESTS_PHASE1` | Add contract compliance tests | P1 |

### 11.2 Medium-Term

| Slice | Purpose | Priority |
|-------|---------|----------|
| `HOLOINDEX_ECOSYSTEM_MAP_UI_PHASE1` | FoundUp directory view | P2 |
| `HOLOINDEX_PUBLIC_TRUST_DASHBOARD_PHASE1` | Safety evidence display | P2 |

### 11.3 Deferred

| Slice | Purpose | Prerequisite |
|-------|---------|--------------|
| `HOLOINDEX_LIVE_BACKEND_RELAY_PHASE1` | Connect bridge to stub search | Bridge tests pass |
| `HOLOINDEX_FEDERATED_QUERY_PHASE1` | Cross-FoundUp search | Tenant isolation verified |

---

## 12. WSP 97 Verdict

| Check | Result |
|-------|--------|
| Documentation only? | YES |
| HoloIndex core mutated? | NO |
| Backend access enabled? | NO |
| Internal index exposed? | NO |
| Secrets exposed? | NO |
| Registry mutated? | NO |
| p.fMALL catalog mutated? | NO |
| Routes changed? | NO |
| UI implemented? | NO |
| MCP changed? | NO |
| CI changed? | NO |

**WSP 97 VERDICT: PASS**

All truth boundary labels honored. This slice documents the public/private boundary without enabling access or mutating infrastructure.

---

## 13. WSP 15 Next Slice Recommendation

### 13.1 Primary Recommendation

**Slice**: `HOLOINDEX_EXTERNAL_BUNDLE_TRACK_PHASE1`

**Purpose**: Track the untracked external FoundUp bundle components per `CURRENT_STATE_AUDIT.md` Option A.

**Scope**:
1. Track `holo_index/foundup_adapter/bridge_stub.py` (if exists locally)
2. Track `public/f/holoindex_prod_01/` scaffold (if exists locally)
3. Add bridge contract compliance tests
4. Update catalog `entry_url` if scaffold tracked

**Why First**: Cannot implement ecosystem map UI without tracked infrastructure.

### 13.2 Alternative Recommendation

**Slice**: `HOLOINDEX_TRUST_DASHBOARD_SPEC_PHASE1`

**Purpose**: Spec-only document for public safety evidence display.

**Scope**:
1. Define what red-team evidence is safe to surface
2. Define what credential isolation claims are safe to make
3. Define what scope-lock claims are safe to make
4. Do not implement UI

**Why Alternative**: If bundle tracking is blocked, can still spec the trust dashboard.

---

## 14. W10 Readiness

| Gate | Status |
|------|--------|
| Source artifacts identified | YES |
| Dual identity boundary documented | YES |
| Public contract defined | YES |
| Internal non-exposure rules defined | YES |
| Safety evidence cataloged | YES |
| Redacted evidence identified | YES |
| Relationships mapped | YES |
| Future slices defined | YES |
| WSP 97 verdict | PASS |
| Ready for PR | YES |

---

## Appendix A: HoloIndex Preflight Queries

### Query 1: Dual Identity Trust Surface
```
Query: "HoloIndex dual identity public FoundUp internal infrastructure p.fMALL trust surface"
Hits: 32 (code=8, wsp=8, docs=8, knowledge=8)
Top Hits:
  - holoindex_plugin.py
  - holoindex_integration.py
  - CURRENT_STATE_AUDIT.md
  - EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md
```

### Query 2: Work Ledger/Red-Team
```
Query: "HoloIndex Work Ledger Brain redteam credential MCP FoundUp registry"
Hits: 32 (code=8, wsp=8, docs=8, knowledge=8)
Top Hits:
  - holo_tools.py
  - mcp_manager.py
  - WSP_UPDATE_RECOMMENDATIONS_MCP_FEDERATION.md
```

### Query 3: Manifest/Catalog
```
Query: "holoindex_prod_01 manifest p.fMALL catalog dual identity"
Hits: 32 (code=8, wsp=8, docs=8, knowledge=8)
Top Hits:
  - test_catalog_foundup_truth_gate.py
  - holoindex_integration.py
  - PFMALL_LAUNCH_CATALOG_TAXONOMY.md
```

---

## Appendix B: Existing HoloIndex FoundUp Documentation Summary

| Document | Purpose | Tracked |
|----------|---------|---------|
| `CURRENT_STATE_AUDIT.md` | Audit of repo vs. workspace components | YES |
| `EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md` | postMessage/HTTP stub contract | YES |
| `FOUNDUPS_PORTFOLIO_DISPLAY_COMPONENT_PHASE1.md` | `/f/` showcase implementation | YES |
| `FOUNDUP_CANONICAL_INVENTORY_AND_STAGE_REGISTRY_AUDIT_PHASE1.md` | Typed registry schema | YES |
| `foundup_manifest.json` (holoindex_prod_01) | External FoundUp surface manifest | YES |
| `mall-video-catalog.json` entry | Catalog binding | YES |
| `public/member/ModLog.md` entry | Dual identity changelog | YES |
| `holo_index/ModLog.md` entry | Dual identity changelog | YES |

**Finding**: Existing HoloIndex FoundUp documentation EXISTS and is TRACKED. This slice concatenates and consolidates that documentation into a single trust surface contract.

---

**Documentation Complete**: 2026-05-22
**Author**: 0102
**WSP Lock**: WSP_00, WSP_15, WSP_50, WSP_83, WSP_87, WSP_97, WSP_104, WSP_22
