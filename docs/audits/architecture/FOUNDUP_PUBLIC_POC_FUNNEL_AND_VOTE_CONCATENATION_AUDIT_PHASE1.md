# FoundUp Public PoC Funnel and VOTE Concatenation Audit - Phase 1

**Slice**: `FOUNDUP_PUBLIC_POC_FUNNEL_AND_VOTE_CONCATENATION_AUDIT_PHASE1`
**Worker**: W9
**Date**: 2026-05-14
**Mode**: DOCS_ONLY
**WSP Lock**: WSP_00 -> WSP_97 -> WSP_87 -> WSP_15 -> WSP_50

---

## Safety Labels

```
DOCS_ONLY
FUNNEL_AUDIT_ONLY
PUBLIC_POC_ONLY
NO_IMPLEMENTATION
NO_NEW_AUTH_SYSTEM
NO_DUPLICATE_VOTE_FOUNDUP
NO_GOVERNANCE_EXECUTION
NO_CABR_READY
NO_PAYOUT_READY
NO_DAO_ACTIVATION
NO_TARGETED_PERSUASION
NO_MICROTARGETING
GATED_PROTOTYPE_ONLY
```

---

## 1. Retrieval Summary

### 1.1 HoloIndex Preflight Results

| Query | Files Found | Key Findings | Assessment |
|-------|-------------|--------------|------------|
| "FoundUp public page Mall entry invite admission OAuth member gate" | 20 | pfmall tests, WSP 106, oauth_management | USEFUL |
| "VOTE FoundUp existing spec routes shell Mall public PWA" | 20 | shell_core.py, voteballots INTERFACE.md | USEFUL |
| "FoundUps Mall auth invite key admission key OAuth roles" | 20 | oauth_management, WSP 26/102/98 | USEFUL |
| "public PoC prototype gated FoundUp shell" | 20 | shell_core.py, pfmall api.py, WSP 98 | USEFUL |
| "WSP 100 DAE SmartDAO escalation public PoC prototype MVP" | 20 | WSP 100, smartdao_spawning, dae_gateway | USEFUL |

### 1.2 Retrieval Quality Assessment

| Dimension | Score | Notes |
|-----------|-------|-------|
| Noise | LOW | Relevant pfmall/auth results prioritized |
| Ordering | GOOD | Core shell_core.py and contracts retrieved first |
| Missing Artifacts | LOW | All key contracts found via glob fallback |
| Staleness Risk | LOW | Recent merged PRs (#618-620) verified |
| Duplication | NONE | No worktree duplication in results |

### 1.3 Fallback Searches Executed

| Pattern | Files Found | Key Evidence |
|---------|-------------|--------------|
| `invite\|admission\|OAuth\|member\|role\|gate\|access` | 50+ | shell_core.py `is_invite_only`, oauth_management module |
| `Mall\|mall\|shell\|PWA\|public page\|landing` | 30+ | pfmall shell_core, FOUNDUP_TEMPLATE.md |
| `VOTE\|vote\|candidate\|FEC\|funding` | 30+ | voteballots module, HXA test files |
| `FOUNDUP_TEMPLATE\|FoundUp` | 30+ | FOUNDUP_TEMPLATE.md, docs contracts |

### 1.4 Verdict

**USEFUL** - HoloIndex returned relevant infrastructure. Fallback grep confirmed complete coverage of auth/gate/entry patterns.

---

## 2. Current Public Surface Audit

### 2.1 Existing Public Surfaces

| Surface | Location | Status | Evidence |
|---------|----------|--------|----------|
| pfMALL Tile Field | `/member/` | IMPLEMENTED | `shell_core.py`, `member-sw.js` |
| FoundUp Welcome Page | `/member/foundup.html?id=` | TRANSITIONAL | PFMALL_FOUNDUP_ENTRY_AND_STAKE_GATE_CONTRACT.md |
| Discord Public | External (`discord.gg/*`) | OPERATIONAL | FOUNDUP_TEMPLATE.md |
| GitHub Public | External (`github.com/FOUNDUPS/*`) | OPERATIONAL | FOUNDUP_TEMPLATE.md |

### 2.2 No Dedicated Public FoundUp Landing Page

**Current state**: FoundUps do not have dedicated public-facing landing pages outside the Mall.

| What Exists | What Does Not Exist |
|-------------|---------------------|
| pfMALL catalog tile discovery | Public `/f/{foundup_id}` landing page |
| Transitional `foundup.html?id=` | External PWA entry surface |
| Discord/GitHub links | Anonymous-accessible PoC |
| Mall video autoplay | Standalone public experience |

### 2.3 Public Surface Gap

The architecture specifies `/f/{foundup_id}` as the canonical route (WSP 104), but:
- Current implementation uses `foundup.html?id=` (transitional)
- No public-accessible entry before Mall admission
- FoundUps are discoverable only within the admitted member experience

**Implication for VOTE**: A public VOTE PoC would require either:
1. A new external PWA route (outside Mall)
2. Or reusing the existing Mall `/f/voteballots` route with `required_subscription_tier: "free"` + `is_invite_only: false`

---

## 3. Current Mall Entry Audit

### 3.1 Mall Entry Flow (Per PFMALL_FOUNDUP_ENTRY_AND_STAKE_GATE_CONTRACT.md)

```
Guest (anonymous browser)
    |
    v [click FoundUp tile OR Enter FoundUp button]
Visitor (FoundUp Welcome)
    |
    v [join Discord/GitHub]
Community (public coordination)
    |
    v [wallet + stake proof]
Stakeholder (gated interior)
```

### 3.2 Entitlement Tiers (Per FOUNDUPS_ENTITLEMENT_TIERS.md)

| Tier | Description | Surface Access |
|------|-------------|----------------|
| **Guest** | Anonymous browser | pfMALL browse, video watch, GitHub read |
| **Visitor** | Entered FoundUp Welcome | Welcome page, Sentinel interact |
| **Community** | Joined Discord/GitHub | Discord read/post, GitHub contribute |
| **Stakeholder** | Wallet + stake verified | FoundUp Interior, governance, voting |
| **Operator** | 012-assigned | Elevated controls |

### 3.3 Gate Mechanisms

| Gate | Location | Status | Implementation |
|------|----------|--------|----------------|
| Mall Admission | Clerk auth | IMPLEMENTED | `/member/` requires Clerk sign-in |
| Invite-Only Flag | `is_invite_only` manifest field | IMPLEMENTED | shell_core.py validates |
| Subscription Tier | `required_subscription_tier` | IMPLEMENTED | Manifest field, not enforced runtime |
| Stake Gate | Wallet + UPS + F_i | NOT IMPLEMENTED | Phase 2 spec only |
| Sentinel | AI greeter | NOT IMPLEMENTED | Future phase |

### 3.4 Key Observation

**Mall admission (Clerk auth) is currently the ONLY enforced gate.**

The `is_invite_only` and `required_subscription_tier` fields exist in manifests but the shell does not enforce subscription tier checks at runtime (per PFMALL_ROUTING_DISCOVERY_MODEL.md Phase 1 status: "SPECIFIED_NOT_IMPLEMENTED").

---

## 4. Current Auth / Invite / Admission / OAuth Audit

### 4.1 OAuth Management Module

**Location**: `modules/platform_integration/utilities/oauth_management/`

**Purpose**: YouTube API credential rotation with quota management. NOT user auth.

| Capability | Status | Notes |
|------------|--------|-------|
| YouTube API OAuth | OPERATIONAL | 4 credential sets with rotation |
| User authentication | NOT IN SCOPE | oauth_management is API auth, not user auth |
| Wallet connect | NOT IMPLEMENTED | Stake gate spec only |

### 4.2 Mall Auth (Clerk)

**Location**: Tests reference Clerk (`test_gateway_terms_gate.py`, `test_video_mall_media_delivery.py`)

| Feature | Status | Evidence |
|---------|--------|----------|
| Clerk auth listener | IMPLEMENTED | `test_gateway_terms_gate.py:161` |
| OAuth confirm buttons | IMPLEMENTED | `test_gateway_terms_gate.py:105-110` |
| Service worker auth skip | IMPLEMENTED | `test_member_pwa_hardening.py:96-99` |
| Auth redirect to `/member/` | IMPLEMENTED | Test assertions confirm |

### 4.3 Invite / Admission Keys

**No explicit invite key or admission key system exists.**

The manifest field `is_invite_only: bool` is the only mechanism:
- `true` = "Angel Access" badge, pre-OPO gating planned
- `false` = public access (not enforced at runtime Phase 1)

### 4.4 Recommended Gate Abstraction

Based on codebase evidence, the correct abstraction is:

| Pattern | Current Name | Location |
|---------|--------------|----------|
| User auth | Clerk OAuth sign-in | Mall shell |
| FoundUp visibility | `is_invite_only` | foundup_manifest.json |
| Subscription gating | `required_subscription_tier` | foundup_manifest.json |
| Stake verification | Wallet signature + balance | NOT IMPLEMENTED |
| Role assignment | 012 manual | Discord roles |

**Do not call it "encrypted UI access"** - the codebase uses manifest fields and Clerk auth, not encryption.

---

## 5. Public FoundUp Funnel Thesis

### 5.1 Core Thesis

> Every FoundUp may benefit from a public-facing entry surface that exposes a PoC before requiring Mall admission.

### 5.2 Proposed Layer Model

```
LAYER 0: Public PoC (anonymous, no auth required)
    |
    v [interest demonstrated]
LAYER 1: Mall Discovery (Clerk auth required)
    |
    v [click Enter FoundUp]
LAYER 2: FoundUp Welcome (Visitor tier)
    |
    v [join community]
LAYER 3: Community Participation (Community tier)
    |
    v [wallet + stake]
LAYER 4: Stakeholder Interior (gated features)
    |
    v [maturity triggers]
LAYER 5: Governance (SmartDAO escalation)
```

### 5.3 Public PoC Layer Characteristics

| Characteristic | Requirement |
|----------------|-------------|
| Authentication | NONE (anonymous) |
| User data collection | NONE (privacy first) |
| Feature scope | Minimal wedge only |
| Upgrade path | Clear CTA to Mall/Community |
| Independence | Standalone PWA or static site |

### 5.4 Gated Prototype Characteristics

| Characteristic | Requirement |
|----------------|-------------|
| Authentication | Mall admission (Clerk) |
| Feature scope | Advanced features |
| Data persistence | IndexedDB with namespace isolation |
| Community integration | Discord/GitHub links |
| Agent coordination | OpenClaw routing |

---

## 6. Shared FoundUp Funnel Pattern Verdict

### 6.1 Should Every FoundUp Have a Public PoC Funnel?

**VERDICT: YES, optionally.**

A shared pattern makes sense because:
1. FoundUps share the same tiered progression (Guest -> Visitor -> Community -> Stakeholder)
2. The "first wedge" principle applies to all FoundUps (validate pain before building full product)
3. Infrastructure reuse (PWA shell, routing, analytics) reduces per-FoundUp cost

### 6.2 Shared vs FoundUp-Specific

| Layer | Shared Infrastructure | FoundUp-Specific |
|-------|----------------------|------------------|
| Public PoC shell | YES (PWA template) | FoundUp content/hooks |
| Mall integration | YES (shell_core.py) | FoundUp manifest |
| Community entry | YES (Discord template) | FoundUp-specific channels |
| Stake gate | YES (wallet connect) | FoundUp-specific thresholds |
| Interior features | NO | Entirely FoundUp-specific |

### 6.3 Pattern Template

```
public-{foundup_id}/           # Public PoC (standalone)
  index.html                   # Entry point
  poc/                         # PoC features
    {feature}.html             # Feature pages
  assets/                      # Static assets
  
/f/{foundup_id}/               # Mall-integrated (shell-loaded)
  app/                         # Protected features
    dashboard/
    analytics/
    governance/
```

---

## 7. VOTE Public PoC Definition

### 7.1 Existing VOTE State

| Component | Status | Evidence |
|-----------|--------|----------|
| Module directory | EXISTS | `modules/foundups/voteballots/` |
| Manifest | EXISTS | `foundup_manifest.json` (F0_DAE, incubating) |
| Architecture spec | EXISTS | 1307-line AI hooks doc |
| Implementation | NONE | `src/__init__.py` empty |
| Entry URL | EMPTY | `entry_url: ""` |
| Routes | PLANNED | `/f/voteballots` |

### 7.2 VOTE Public PoC Scope (Candidate)

Per VOTE_PAIN_RESEARCH_FIRST_WEDGE_AUDIT_PHASE1:

| Feature | Description | Public PoC? |
|---------|-------------|-------------|
| Conversational entry | Text input for candidate query | YES |
| Entity resolution | Name to FEC ID lookup | YES |
| Funding summary | Top 5 sources with confidence | YES |
| Attack source summary | Opposing spend info | YES |
| Evidence classification | WSP 97 4-tier labels | YES |
| One evidence card | Single deep-dive layer | YES |
| Plain-language answer | 3-line + follow-up | YES |
| Feedback capture | User corrections | YES |
| Trail termination marker | Where evidence stops | YES |

### 7.3 VOTE Public PoC Non-Goals

| Feature | Reason | Layer |
|---------|--------|-------|
| Speech-to-text | Complexity, not core wedge | Prototype |
| Discovery feed | Requires browsing infrastructure | Prototype |
| Alerts | Push notification infrastructure | Prototype |
| Saved topics | User account required | Prototype |
| Bulk exports | Data volume concerns | Prototype |
| Governance hooks | NO_GOVERNANCE_EXECUTION | SmartDAO |

---

## 8. VOTE Gated Prototype Boundary

### 8.1 Prototype Features (Mall-Gated)

| Feature | Trigger | Dependencies |
|---------|---------|--------------|
| Discovery feed | Browse candidates/races | Mall auth + IndexedDB |
| Alerts | Funding pattern changes | Push notification infra |
| Channel analytics | Aggregate spending data | HoloIndex integration |
| Narrative clustering | Attack ad grouping | ML pipeline |
| Support signals | User endorsements | Community tier |
| Multi-hop trace | 3+ hop funding trail | Compute budget |
| Saved/followed topics | Persistent user state | Mall auth + IndexedDB |

### 8.2 Prototype Access Requirements

| Requirement | Implementation |
|-------------|----------------|
| Mall admission | Clerk OAuth sign-in |
| Manifest readiness | `launch_readiness: "ready"` (currently "discoverable_only") |
| Entry URL | Configured (currently empty) |
| Shell loading | `/f/voteballots` route resolution |

### 8.3 Governance-Only Features (Later)

| Feature | Gate Required | Earliest Phase |
|---------|---------------|----------------|
| Challenge arbitration | CABR V2 proof | SmartDAO |
| Report bounties | Token system | SmartDAO |
| Source credibility scoring | Validator consensus | SmartDAO |
| Community fact-checking | DAO participation | SmartDAO |

---

## 9. Capability / Admission Gate Model

### 9.1 Recommended Abstraction

Based on codebase evidence, the gate model is:

| Gate Type | Mechanism | Current Status |
|-----------|-----------|----------------|
| **No auth** | Anonymous access | Public PoC layer |
| **Clerk OAuth** | Mall sign-in | Mall admission |
| **Manifest flag** | `is_invite_only`, `required_subscription_tier` | Visibility filter |
| **Wallet signature** | Challenge-response | NOT IMPLEMENTED |
| **Stake threshold** | UPS + F_i balance | NOT IMPLEMENTED |
| **Role assignment** | 012 manual via Discord | Operational |

### 9.2 Do Not Create New Auth System

**The codebase already has Clerk for user auth.**

Do not create:
- Custom invite key infrastructure
- New admission key system
- Alternative OAuth flow
- Token-based access control (beyond Clerk)

Instead, use:
- Anonymous access for public PoC
- Clerk OAuth for Mall admission
- Manifest fields for visibility control
- Wallet connect (when implemented) for stake verification

---

## 10. Preserve / Extend / Create-New / Do-Not-Touch Matrix

### 10.1 Preserve

| Component | Location | Rationale |
|-----------|----------|-----------|
| VOTE manifest | `voteballots/foundup_manifest.json` | Canonical identity |
| VOTE AI hooks architecture | `docs/VOTEBALLOTS_AI_HOOKS_ARCHITECTURE.md` | 1307-line spec complete |
| VOTE TypeScript interfaces | `adapters/typescript/*.ts` | Type contracts |
| pfMALL shell_core.py | `pfmall/shell_core.py` | Shell infrastructure |
| Entitlement tiers | FOUNDUPS_ENTITLEMENT_TIERS.md | Tier definitions |
| Entry/stake gate contract | PFMALL_FOUNDUP_ENTRY_AND_STAKE_GATE_CONTRACT.md | Gate architecture |

### 10.2 Extend

| Component | Extension | Rationale |
|-----------|-----------|-----------|
| VOTE manifest | Add `public_poc_url` field | Point to public PoC |
| FOUNDUP_TEMPLATE | Add public PoC component | Shared pattern |
| Entity resolution hook | Add conversational parsing | Per VOTE_SOLUTION_ARCHITECTURE_PACKET |
| Report generation | Add chat-style output | PoC UX |

### 10.3 Create-New (Minimal)

| Component | Purpose | Scope |
|-----------|---------|-------|
| Public PoC shell template | Shared PWA boilerplate | Docs + scaffold only |
| VOTE public landing | `/vote/` or `vote.foundups.org` | Single page + query |
| FEC API adapter | Data fetching | VOTE-specific |

### 10.4 Do-Not-Touch

| Component | Reason |
|-----------|--------|
| Clerk auth flow | Working, do not replace |
| oauth_management module | YouTube API only, not user auth |
| Wallet connect implementation | Phase 2, not PoC scope |
| Stake gate mechanics | NOT IMPLEMENTED, defer |
| CABR integration | NO_CABR_READY |
| Governance execution | NO_GOVERNANCE_EXECUTION |

---

## 11. Shared Infrastructure Hooks Needed

### 11.1 Existing Hooks (Reuse)

| Hook | Location | Purpose |
|------|----------|---------|
| Route resolution | `shell_core.resolve_route()` | URL -> FoundUp |
| Manifest loading | `shell_core.load_manifest()` | Validate + parse |
| Tile building | `shell_core.build_foundup_tile()` | Catalog display |
| State overlay | `StateOverlayProvider` protocol | Dynamic metrics |

### 11.2 New Shared Hooks (Optional)

| Hook | Purpose | Phase |
|------|---------|-------|
| `public_poc_redirect()` | Route public -> PoC | PoC |
| `community_entry_cta()` | Generate Discord/GitHub links | PoC |
| `upgrade_prompt()` | Guide public -> Mall | PoC |

### 11.3 VOTE-Specific Hooks

| Hook | Purpose | Source |
|------|---------|--------|
| `resolve_candidate()` | Name -> FEC ID | VOTE_SOLUTION_ARCHITECTURE |
| `fetch_funding()` | FEC API wrapper | VOTE_SOLUTION_ARCHITECTURE |
| `score_confidence()` | WSP 97 labels | VOTE AI hooks spec |
| `generate_quick_answer()` | 3-line response | VOTE AI hooks spec |
| `capture_feedback()` | User corrections | VOTE AI hooks spec |

---

## 12. Proposed Public-to-Prototype Flow

### 12.1 VOTE Flow

```
PUBLIC PoC (anonymous)
    |
    | vote.foundups.org OR /public/vote/
    |
    v
[User queries candidate]
    |
    v
[Quick answer + evidence card returned]
    |
    v
[User wants more features]
    |
    v
[CTA: "Join the Mall for alerts, discovery, and analytics"]
    |
    v
MALL ADMISSION (Clerk OAuth)
    |
    v
[User signs in]
    |
    v
VOTE PROTOTYPE (/f/voteballots)
    |
    v
[Discovery feed, alerts, saved topics, etc.]
    |
    v
[User joins community]
    |
    v
COMMUNITY (Discord + GitHub)
    |
    v
[Future: Stakeholder gate, governance]
```

### 12.2 Flow Invariants

1. Public PoC is ALWAYS anonymous (no data collection)
2. Mall admission is ALWAYS Clerk OAuth (no custom auth)
3. Prototype is ALWAYS within Mall shell
4. Community is ALWAYS Discord + GitHub
5. Governance is ALWAYS post-SmartDAO (future)

---

## 13. First VOTE Implementation Slice

### 13.1 Recommended Slice

**Slice**: `VOTE_PUBLIC_POC_FEC_ADAPTER_PHASE1`

**Scope**:
1. FEC Candidate API wrapper
2. Entity resolution (name -> FEC ID)
3. Basic funding summary
4. Single page HTML/JS PoC

**Deliverables**:
- `modules/foundups/voteballots/src/fec_adapter.py` (Python backend)
- `modules/foundups/voteballots/public/index.html` (Public PoC shell)
- Unit tests with known candidates

**Exit Criteria**:
- 90% entity resolution accuracy on 20 test candidates
- Funding summary returns top 5 sources
- WSP 97 confidence labels applied

### 13.2 Dependencies

```
VOTE_PUBLIC_POC_FEC_ADAPTER_PHASE1
    |
    v
VOTE_PUBLIC_POC_EVIDENCE_CARD_PHASE1
    |
    v
VOTE_PUBLIC_POC_QUICK_ANSWER_PHASE1
    |
    v
VOTE_PUBLIC_POC_SHELL_INTEGRATION_PHASE1
    |
    v
VOTE_PROTOTYPE_DISCOVERY_FEED_PHASE1
```

---

## 14. First Shared Funnel Infrastructure Slice

### 14.1 Recommended Slice

**Slice**: `FOUNDUP_PUBLIC_POC_TEMPLATE_PHASE1`

**Scope**:
1. Document public PoC pattern in FOUNDUP_TEMPLATE.md
2. Add `public_poc_url` field to manifest schema
3. Create minimal PWA scaffold

**Deliverables**:
- Update to `FOUNDUP_TEMPLATE.md` with public PoC component
- Update to `PFMALL_FOUNDUP_MANIFEST_SCHEMA.md` with field spec
- `modules/foundups/docs/PUBLIC_POC_SHELL_TEMPLATE.md` (scaffold doc)

**Exit Criteria**:
- Pattern documented
- Schema extended
- No runtime changes

---

## 15. Risks, Unknowns, Required Decisions

### 15.1 Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| FEC API rate limits | MEDIUM | Cache + batch requests |
| Public PoC hosting | LOW | Use existing Pages/CDN |
| Scope creep to prototype features | MEDIUM | Strict PoC boundary |
| Auth confusion | LOW | Clear public vs Mall boundary |
| VOTE name implies voting mechanism | LOW | Clarify in docs |

### 15.2 Unknowns

| Unknown | Impact | Resolution Path |
|---------|--------|-----------------|
| FEC API key availability | BLOCKING | Ops to provision |
| Public PoC domain | MEDIUM | `vote.foundups.org` or `/public/vote/` |
| Analytics for public PoC | LOW | Anonymous telemetry only |
| Mobile optimization | MEDIUM | PWA manifest + responsive |

### 15.3 Required Decisions

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Public PoC hosting | Subdomain vs path | Subdomain (cleaner separation) |
| Data persistence | None vs anonymous cache | None (privacy first) |
| Upgrade prompt style | Modal vs banner | Banner (less intrusive) |
| Community CTA | Discord only vs Discord+GitHub | Both (per FOUNDUP_TEMPLATE) |

---

## 16. WSP_15 Next-Slice Recommendation

### 16.1 Immediate Next (P0)

| Slice | Description | Dependency |
|-------|-------------|------------|
| `VOTE_PUBLIC_POC_FEC_ADAPTER_PHASE1` | FEC API wrapper + entity resolution | FEC API key |

**Rationale**: FEC adapter is foundational. All public PoC features depend on data access.

### 16.2 Parallel Work (P1)

| Slice | Description | Can Start |
|-------|-------------|-----------|
| `FOUNDUP_PUBLIC_POC_TEMPLATE_PHASE1` | Document shared pattern | Now |
| `VOTE_PUBLIC_POC_UI_SCAFFOLD_PHASE1` | HTML/JS shell | Now |

### 16.3 After FEC Adapter (P1)

| Slice | Description |
|-------|-------------|
| `VOTE_PUBLIC_POC_EVIDENCE_CARD_PHASE1` | Single deep-dive layer |
| `VOTE_PUBLIC_POC_QUICK_ANSWER_PHASE1` | 3-line response generator |

---

## 17. Summary

### 17.1 Core Findings

1. **Public FoundUp landing pages do not exist** - FoundUps are discoverable only within the Mall
2. **Clerk is the only enforced auth** - `is_invite_only` and `required_subscription_tier` are not runtime-enforced in Phase 1
3. **No new auth system needed** - Clerk OAuth for Mall, anonymous for public PoC
4. **VOTE should prove the public PoC pattern** - First FoundUp with external entry point
5. **Shared funnel pattern makes sense** - Reusable infrastructure reduces per-FoundUp cost

### 17.2 Recommended Gate Abstraction

| Layer | Gate | Mechanism |
|-------|------|-----------|
| Public PoC | None | Anonymous access |
| Mall | Clerk OAuth | Sign-in required |
| Prototype | Manifest flags | `is_invite_only`, `required_subscription_tier` |
| Stakeholder | Wallet signature | NOT IMPLEMENTED |
| Governance | CABR + ROC | NOT IMPLEMENTED |

### 17.3 WSP 97 Verdict

**FUNNEL_PATTERN_IDENTIFIED_IMPLEMENTATION_DEFERRED**

| Claim | Status | Evidence |
|-------|--------|----------|
| Public PoC surface exists | FALSE | No public landing pages |
| Mall entry exists | TRUE | Clerk auth + pfMALL |
| VOTE architecture complete | TRUE | 1307-line AI hooks spec |
| VOTE implementation exists | FALSE | `src/__init__.py` empty |
| New auth system needed | FALSE | Clerk + anonymous sufficient |
| Public PoC pattern shareable | TRUE | FOUNDUP_TEMPLATE extensible |

---

## Worker W9 Completion

**Slice**: `FOUNDUP_PUBLIC_POC_FUNNEL_AND_VOTE_CONCATENATION_AUDIT_PHASE1`
**Worktree**: Current agent worktree
**Branch**: `docs/foundup-public-poc-funnel-audit`
**Base Commit**: bde6d08d0
**Sub-Workers Used**: None (parallel research within single W9 context)
**Files Changed**: 1 (this audit)

### HoloIndex Assessment Summary

- **Useful**: YES - Core pfmall/auth infrastructure well-indexed
- **Noisy**: NO - Results relevant and ordered
- **Missing Files**: NO - All contracts found
- **Stale Results**: NO - Recent PRs verified
- **Ordering**: GOOD - Shell contracts prioritized
- **Fallback Needed**: YES - Grep confirmed coverage

### Current Codebase Evidence Summary

| Evidence Type | Finding |
|---------------|---------|
| Public surfaces | None external to Mall |
| Auth mechanism | Clerk OAuth (Mall), anonymous (public) |
| Gate abstraction | `is_invite_only` + `required_subscription_tier` manifest fields |
| VOTE state | Architecture complete, implementation empty |
| Shared infrastructure | shell_core.py, manifest schema, entitlement tiers |

### Recommended Gate Abstraction

**Do not create new auth/invite/admission system.**

Use:
- Anonymous access for public PoC
- Clerk OAuth for Mall admission
- Manifest fields for visibility control
- Wallet connect (future) for stake verification

### WSP_97 Verdict

**DOCS_ONLY_AUDIT_COMPLETE**

### WSP_15 Next-Slice Recommendation

`VOTE_PUBLIC_POC_FEC_ADAPTER_PHASE1` - FEC API integration foundation.

### W10 Readiness

**READY** - Staged, not pushed. Audit complete per WSP_15 scope discipline.

---

*Worker W9 complete for FOUNDUP_PUBLIC_POC_FUNNEL_AND_VOTE_CONCATENATION_AUDIT_PHASE1.*
