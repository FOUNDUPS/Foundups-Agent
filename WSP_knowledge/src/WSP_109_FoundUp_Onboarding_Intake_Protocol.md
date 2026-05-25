# WSP 109: FoundUp Onboarding Intake Protocol

**Version**: 1.1.0  
**Status**: Draft  
**Created**: 2026-05-25  
**Author**: 0102  
**Predecessor**: PR #717 (Shield onboarding validation)  
**Generalizes**: `modules/foundups/docs/FOUNDUP_ONBOARDING_PROTOCOL_PHASE1.md` (module-level evidence)  

---

## Audience

**Primary**: 0102 agents, RedDog intake agent, architect agent, WRE routing surfaces.

**012 Role**: 012 is the idea source, not the protocol operator.

**Core Statement**: 012 speaks the idea; 0102 executes WSP 109 intake.

---

## Canonical Authority

| Location | Authority |
|----------|-----------|
| `WSP_framework/src/` | **CANONICAL** — source of truth |
| `WSP_knowledge/src/` | **MIRROR** — synchronized backup copy |

The mirror exists because prior 0102 activity has deleted or corrupted framework files. The mirror improves recovery, auditability, and drift detection. Framework is canonical; knowledge is backup.

---

## Purpose

WSP 109 defines how a raw 012 idea becomes an architect-ready FoundUp intake packet.

It does NOT build the FoundUp.  
It does NOT replace WRE.  
It does NOT hard-code worker topology.  
It prepares the handoff.

When 012 says "add this FoundUp, follow WSP 109", 0102/RedDog executes this protocol to add it to the codebase monorepo following WSPs.

---

## Trigger

WSP 109 activates when:

1. 012 expresses a new FoundUp concept (spoken, written, or implied)
2. An architect or RedDog agent recognizes unstructured FoundUp potential
3. A worker receives a "create new FoundUp" directive without existing intake packet

---

## Scope Boundary

### WSP 109 DOES

- Convert spoken/unstructured idea into structured intake packet
- Define required output contracts (OUTCOME, SOLUTION, PAIN, etc.)
- Classify entity type (foundup, external_foundup, skeleton_candidate, etc.)
- Produce WRE-ready artifacts for downstream routing
- Hand off to architect/WRE for execution

### WSP 109 DOES NOT

- Write code
- Update registry (that's downstream work)
- Configure DNS or domains
- Create tokens or wallets
- Create public routes
- Replace WRE orchestration
- Hard-code worker assignments
- Create SKILLz (that's WSP 95)

---

## First Principle

A FoundUp begins as a spoken signal.

WSP 109 converts that signal into structured intake.

WRE recursively routes that intake through the existing agentic development framework.

---

## RedDog/0102 Intake Role

The intake conversation follows this pattern:

```
012 spoken idea
    |
    v
RedDog / 0102 intake conversation
    |
    v
WSP 109 architect packet
    |
    v
WRE orchestration layer
    |
    v
Architect routes work
    |
    v
Specialized workers execute
    |
    v
Results return to architect / WRE
    |
    v
PoC / Prototype / MVP progression
```

During intake, RedDog/0102 must:

1. **Listen** - Capture the core problem/opportunity
2. **Clarify** - Ask targeted questions to fill gaps
3. **Classify** - Determine entity type per decision tree
4. **Structure** - Produce the required output contracts
5. **Hand off** - Deliver packet to WRE/architect

---

## Required Output Packet

WSP 109 produces eight structured artifacts:

| Artifact | Purpose | Required |
|----------|---------|----------|
| `INTAKE_SOURCE.md` | Captures origin and provenance of intake | YES |
| `OUTCOME.md` | What success looks like for the user | YES |
| `SOLUTION.md` | How the FoundUp solves the problem | YES |
| `PAIN.md` | What pain point drives adoption | YES |
| `POC_SCOPE.md` | Minimum viable proof-of-concept boundary | YES |
| `PROTOTYPE_GATE.md` | Criteria to advance from POC to prototype | YES |
| `SKILLS_MAP.md` | Candidate skillz for future wardrobe | YES |
| `FOUNDUP_MANIFEST_DRAFT.md` | Draft manifest for registry seed | YES |

These are NOT final build instructions. They are WRE-ready intake artifacts.

### Packet Output Order

Intake may discover pain first, but the packet must output in FoundUp architect order:

```
OUTCOME -> SOLUTION -> PAIN -> POC_SCOPE -> PROTOTYPE_GATE -> SKILLS_MAP -> FOUNDUP_MANIFEST_DRAFT
```

Rationale:
- 012 may speak from pain
- Architect needs outcome first
- Build path follows solution
- Adoption pressure follows pain
- PoC boundary prevents prototype creep

---

## Contract Definitions

### INTAKE_SOURCE.md Contract

```markdown
# {FoundUp Name} - Intake Source

## Source Type
{spoken_012 | pasted_prompt | external_0102_discussion | prior_session_summary}

## Raw Input Summary
{Brief summary of original input - what 012 said or what was pasted}

## Inferred FoundUp Name
{Name derived from intake conversation}

## Proposed FoundUp ID
{lowercase_underscore format}

## Assumptions
- {Assumption 1}
- {Assumption 2}

## Unresolved Questions
- {Question 1}
- {Question 2}

## Duplicate Discovery Status
{NEW_FOUNDUP | EXISTING_FOUNDUP_UPDATE | POSSIBLE_DUPLICATE | LEGITIMATE_FORK | DERIVATIVE_FOUNDUP | EXTERNAL_FOUNDUP_REFERENCE}

## Provenance Note
{Any relevant context about source - session ID, conversation reference, etc.}
```

Core rule: A new 0102 session must be able to onboard a FoundUp from an external prior discussion without requiring full chat history.

### OUTCOME.md Contract

```markdown
# {FoundUp Name} - Outcome Definition

## User Outcome
{What the user achieves when the FoundUp succeeds}

## Success Metrics
- {Metric 1}
- {Metric 2}
- {Metric 3}

## Anti-Outcomes (What This Is NOT)
- {Anti-outcome 1}
- {Anti-outcome 2}
```

### SOLUTION.md Contract

```markdown
# {FoundUp Name} - Solution Definition

## Core Solution
{One-paragraph description of how the FoundUp solves the problem}

## Key Capabilities
1. {Capability 1}
2. {Capability 2}
3. {Capability 3}

## Differentiation
{Why this solution vs alternatives}

## Technical Approach
{High-level technical strategy - not implementation details}
```

### PAIN.md Contract

```markdown
# {FoundUp Name} - Pain Definition

## Primary Pain Point
{The core problem that drives adoption}

## Pain Severity
- Frequency: {daily/weekly/monthly/occasional}
- Impact: {high/medium/low}
- Alternatives: {none/poor/adequate}

## Target User
{Who experiences this pain most acutely}

## Pain Evidence
{How we know this pain exists - research, signals, 012 insight}
```

### POC_SCOPE.md Contract

```markdown
# {FoundUp Name} - POC Scope

## Minimum Viable POC
{The smallest thing that proves the concept works}

## Included in POC
- {Feature 1}
- {Feature 2}

## Explicitly Excluded from POC
- {Excluded 1}
- {Excluded 2}

## Success Criteria
{How we know POC is complete}

## Trust Wedge
{What free value proves trustworthiness}
```

### PROTOTYPE_GATE.md Contract

```markdown
# {FoundUp Name} - Prototype Gate

## POC -> Prototype Criteria
- [ ] {Criterion 1}
- [ ] {Criterion 2}
- [ ] {Criterion 3}

## Prototype Scope Expansion
{What prototype adds beyond POC}

## Risk Gates
- [ ] Privacy validated
- [ ] Security reviewed
- [ ] Compliance checked (if applicable)
```

### SKILLS_MAP.md Contract

```markdown
# {FoundUp Name} - Skills Map

## Candidate SKILLz (Not Created - WSP 95 Governs)

| Skill Name | Purpose | Priority |
|------------|---------|----------|
| {skill_1} | {purpose} | {P1/P2/P3} |
| {skill_2} | {purpose} | {P1/P2/P3} |

## WRE Integration Points
- {Integration 1}
- {Integration 2}

## Future Slice
FOUNDUP_{ID}_SKILLZ_WARDROBE_PHASE1
```

### FOUNDUP_MANIFEST_DRAFT.md Contract

```markdown
# {FoundUp Name} - Manifest Draft

## Registry Fields (Draft)

| Field | Value |
|-------|-------|
| foundup_id | {lowercase_underscore} |
| display_name | {Human Name} |
| entity_type | {foundup/external_foundup/skeleton_candidate/...} |
| module_path | modules/foundups/{id} |
| stage | incubating |
| tier | F0_DAE |
| implementation_status | SPECIFIED |
| token_status | TOKEN_DEFERRED |
| poc_status | idea |
| next_slice | {ID}_POC_PHASE1 |

## Notes
{Any special considerations for registry entry}
```

---

## Entity Type Decision Tree

```
Is this a consumer-facing venture?
├─ YES: Does it have its own token economics?
│   ├─ YES: Does source live in monorepo?
│   │   ├─ YES → entity_type: foundup
│   │   └─ NO  → entity_type: external_foundup
│   └─ NO: Is it planned to have tokens?
│       ├─ YES (future) → entity_type: skeleton_candidate
│       └─ NO (never) → entity_type: access_service
└─ NO: Is it infrastructure?
    ├─ YES: Does it serve multiple FoundUps?
    │   ├─ YES → entity_type: infra_service
    │   └─ NO  → entity_type: platform_layer
    └─ NO: Is it a development tool?
        └─ YES → entity_type: tool_simulator
```

---

## Duplicate Discovery Preflight

WSP 109 requires checking for existing FoundUps before creating intake artifacts.

### Required Searches

| Source | Path | Purpose |
|--------|------|---------|
| HoloIndex | semantic search | Find similar concepts |
| Registry | `modules/foundups/foundup_registry.json` | Check existing entries |
| Modules | `modules/foundups/**` | Check existing scaffolds |
| Mall Catalog | `public/member/mall-catalog.json` | Check published FoundUps |
| Video Catalog | `public/member/mall-video-catalog.json` | Check video entries |
| Portfolio | `public/f/portfolio_data.json` | Check portfolio entries |
| External Repos | known references | Check external FoundUps |

### Discovery Classification

| Classification | Meaning | Action |
|----------------|---------|--------|
| NEW_FOUNDUP | No existing match | Proceed with intake |
| EXISTING_FOUNDUP_UPDATE | Same FoundUp, new features | Route to update slice |
| POSSIBLE_DUPLICATE | May repeat existing FoundUp | Flag for architect review |
| LEGITIMATE_FORK | Intentional derivative | Proceed with lineage fields |
| DERIVATIVE_FOUNDUP | Narrower audience/vertical | Proceed with parent reference |
| EXTERNAL_FOUNDUP_REFERENCE | Points to external repo | Use external_foundup type |

### Discovery Questions

1. Is this the same FoundUp?
2. Is this an update to an existing FoundUp?
3. Is this a legitimate fork?
4. Is this an external FoundUp reference?
5. Is this a derivative that needs lineage recorded?

---

## Addendum A — WSP 109 WRE Orchestration Binding

### Purpose

This addendum clarifies that WSP 109 does not create a new routing or orchestration system.

WSP 109 produces the FoundUp intake packet.

The Windsurf Recursive Engine (WRE) receives that packet and routes the work through the existing orchestration framework.

### Core Rule

```
WSP 109 = intake.
WRE = orchestration.
Architect = routing authority.
```

OpenClaw, Hermes, Qwen, Gemma, evaluator workers, research workers, documentation workers, and build workers are downstream execution surfaces.

WSP 109 must not duplicate or replace WRE.

### Intake-to-WRE Flow

```
012 spoken idea
    |
    v
RedDog / 0102 intake conversation
    |
    v
WSP 109 architect packet
    |
    v
WRE orchestration layer
    |
    v
Architect routes work
    |
    v
Specialized workers execute, research, evaluate, test, document, and refine
    |
    v
Results return to architect / WRE
    |
    v
PoC / prototype / MVP progression
```

### WSP 109 Output Role

WSP 109 outputs the structured packet:

- INTAKE_SOURCE.md
- OUTCOME.md
- SOLUTION.md
- PAIN.md
- POC_SCOPE.md
- PROTOTYPE_GATE.md
- SKILLS_MAP.md
- FOUNDUP_MANIFEST_DRAFT.md

These are not final build instructions. They are WRE-ready intake artifacts.

### WRE Routing Role

After receiving the WSP 109 packet, WRE may route to:

- research worker
- build worker
- documentation worker
- evaluator worker
- skills worker
- test worker
- prototype worker
- compliance / risk worker
- valuation / CABR worker
- UI / UX worker
- marketplace / FoundUp Mall worker

The exact routing is determined by existing WRE logic, existing WSPs, and architect judgment.

### Boundary Statement

WSP 109 should never hard-code the full worker topology.

It should define the intake packet clearly enough that WRE can route it.

The routing system already exists.

The intake protocol feeds it.

### Correct Architecture

```
WSP 109 = FoundUp intake protocol
WRE = recursive orchestration engine
Architect = routing brain
Workers = execution/evaluation/research/documentation surfaces
Existing WSPs = governing law
```

---

## Addendum B — AutoPost/Sleeve Reuse Boundary

### Pattern Reuse

WSP 109 acknowledges that certain FoundUp patterns may be reused:

- **AutoPost sleeve pattern** - External repo + internal registry representation
- **Shield trust wedge pattern** - Free POC builds trust before commitment
- **GotJunk prototype pattern** - Cloud Run deployment model

### Reuse Rules

1. Pattern concepts may be reused
2. Source code must NOT be copied without explicit authorization
3. External FoundUps (`entity_type: external_foundup`) have `module_path: null`
4. Internal FoundUps must have monorepo module scaffold

### AutoPost Boundary

- AutoPost source lives in `O:/repos/AutoPost/` (external)
- AutoPost has registry entry with `module_path: null`
- New FoundUps may reference AutoPost pattern but not copy its PWA code

---

## Addendum C — FoundUp Mall / Exchange Read-Model Boundary

### Catalog Updates

WSP 109 intake does NOT update catalogs:

| Catalog | WSP 109 Role |
|---------|--------------|
| `mall-catalog.json` | NO update |
| `mall-video-catalog.json` | NO update |
| `portfolio_data.json` | NO update |
| `foundup_registry.json` | NO update (downstream) |

### Future Slice Pattern

Catalog updates are downstream work:

```
{ID}_PFMALL_DISCOVERABLE_ENTRY_PHASE1
```

### Exchange/Marketplace Boundary

WSP 109 does not interact with:

- Token economics
- CABR scoring
- Payout systems
- DAO activation
- Chain transactions

---

## Addendum D — WSP 95 SKILLz Boundary

### Skills Map vs Skills Creation

WSP 109 creates `SKILLS_MAP.md` which lists candidate skillz.

WSP 95 (WRE SKILLz Wardrobe Protocol) governs actual skill creation/promotion.

**Key invariant**: Skillz may evolve without changing WSP 109.

### Boundary

| Activity | Protocol |
|----------|----------|
| List candidate skills | WSP 109 |
| Create skill files | WSP 95 |
| Promote skills to wardrobe | WSP 95 |
| Skill execution | WRE |

### Proposed Wardrobe Location

Candidate onboarding skillz SHOULD live under:

```
modules/foundups/skillz/onboarding/
```

This is a proposed WSP 95 wardrobe location, not a fixed implementation dependency. WSP 95 placement review may route them elsewhere.

### Candidate SKILLz for Onboarding

Future slice `FOUNDUP_ONBOARDING_SKILLZ_WARDROBE_PHASE1` may create:

- `foundup_intake_normalizer`
- `foundup_pain_solution_outcome_mapper`
- `foundup_poc_scope_guard`
- `foundup_prototype_gate_mapper`
- `foundup_manifest_draft_generator`
- `foundup_duplicate_discovery_holoindex`
- `foundup_catalog_readiness_evaluator`

WSP 109 references these candidates but does not require specific skill files.

These are recommendations, not created by this WSP.

### SKILLz vs External Skills Terminology

| Term | Definition |
|------|------------|
| SKILLz | FoundUps/WRE wardrobe capabilities governed by WSP 95 |
| skills | External agent/plugin/tool capabilities (lowercase) |

WSP 109 may list candidate SKILLz and note external execution needs.
WSP 109 creates neither.

---

## Addendum E — New-Session Execution Validation

### Purpose

WSP 109 must be executable by a fresh 0102 from protocol text alone.

### Acceptance Test

Given only:
- WSP 109 (this document)
- One raw FoundUp idea

The worker must:
- Produce all required intake artifacts (8 files)
- Preserve intake-only boundary
- Avoid code changes
- Avoid registry/catalog/public route/token/DNS mutation
- Separate PoC from prototype
- Create a WRE-ready handoff
- Produce a packet an architect can route

### Worker Compatibility Probe

Future slice: `WSP_109_WORKER_COMPATIBILITY_PROBE_PHASE1`

Purpose: Test whether OpenClaw, Hermes, Qwen-class workers, and 0102 can follow WSP 109 in dry-run mode.

WSP 109 does NOT claim those workers are proven compatible yet.

---

## Addendum F — Duplicate vs Fork Boundary

### Core Rule

A FoundUp may be a fork. Duplicate discovery must not automatically block onboarding.

### Discovery Classifications

| Classification | Definition |
|----------------|------------|
| POSSIBLE_DUPLICATE | Appears to repeat existing FoundUp without new audience, outcome, domain, fork lineage, or differentiated execution path |
| LEGITIMATE_FORK | Intentionally derives from existing FoundUp with declared fork reason, lineage parent, and differentiated direction |
| DERIVATIVE_FOUNDUP | Derived from parent with narrower audience, vertical, region, creator, channel, token/community, or execution model |

### Fork Rules

- Duplicates are blocked or routed to update
- Forks are allowed when lineage and differentiation are explicit
- A fork must not mutate the parent FoundUp
- A fork must not inherit token, registry, route, catalog, or governance state unless a downstream WSP-gated slice explicitly authorizes it

### Fork Types

- audience_fork
- geography_fork
- creator_fork
- product_fork
- media_fork
- community_fork
- protocol_fork
- access_service_fork

### Required Fork Fields in FOUNDUP_MANIFEST_DRAFT.md

When applicable:
- parent_foundup_id
- fork_type
- fork_reason
- differentiation_summary
- lineage_notes
- shared_assets
- independent_assets
- governance_boundary
- token_boundary

---

## Addendum G — Skillz Placement Boundary

### Placement Status

WSP 109 does not create SKILLz.
WSP 109 may list candidate onboarding SKILLz in SKILLS_MAP.md.
Actual SKILLz creation and placement are governed by WSP 95.

### Current Repo Evidence

- No canonical `modules/foundups/skillz/` directory exists yet
- Existing SKILLz are module-local or system-local
- WSP 95 supports both `skillz/` and `skills/` discovery paths
- WSP 95 says skills belong with the module they serve

### Placement Rule

`modules/foundups/skillz/onboarding/` is a **candidate placement only**.

It must not be treated as canonical until a WSP 95 placement review slice confirms it.

### Future Slice

`FOUNDUP_ONBOARDING_SKILLZ_WARDROBE_DISCOVERY_PHASE1`

Purpose: Research existing SKILLz placement patterns, inspect WSP 95, identify whether onboarding SKILLz belong under:
- `modules/foundups/skillz/onboarding/`
- `modules/ai_intelligence/ai_overseer/skillz/`
- `modules/infrastructure/wre_core/skillz/`
- `.claude/skills/..._prototype`
- another WSP 95-compliant wardrobe path

Output: Placement recommendation only, or prototype SKILLz only if explicitly authorized.

---

## WSP Dependency Map

| WSP | Relationship |
|-----|--------------|
| WSP 95 | SKILLz governance (downstream) |
| WSP 97 | Execution discipline (applies to intake) |
| WSP 104 | Route namespace (downstream) |
| WSP 106 | API gateway (downstream) |
| WSP 108 | Documentation compliance (applies) |
| WSP 22 | ModLog updates (applies) |
| WSP 49 | Module structure (downstream) |
| WSP 50 | Pre-action verification (applies) |

---

## WSP 97 Truth Boundary

WSP 109 enforces these truth boundaries:

| Truth Boundary Checklist Item | Status |
|-------------------------------|--------|
| WSP_109_INTAKE_ONLY | YES |
| FRAMEWORK_CANONICAL | YES |
| KNOWLEDGE_MIRROR_BACKUP_ONLY | YES |
| MIRROR_EXISTS_FOR_RECOVERY_AND_DRIFT_DETECTION | YES |
| WRITTEN_FOR_0102_AGENT_EXECUTION | YES |
| 012_IS_IDEA_SOURCE_NOT_OPERATOR | YES |
| DOES_NOT_REPLACE_WRE | YES |
| ARCHITECT_REMAINS_ROUTING_AUTHORITY | YES |
| WSP_95_SKILLZ_BOUNDARY_PRESERVED | YES |
| DOES_NOT_CREATE_SKILLZ | YES |
| CITES_717_AS_PREDECESSOR | YES |
| PROMPT_SECURITY_GATE_DEFERRED_TO_SKILLZ | YES |
| NO_RUNTIME_CODE_MUTATION | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_CATALOG_MUTATION | YES |
| NO_MANIFEST_MUTATION | YES |
| NO_PUBLIC_ROUTE_ACTIVATION | YES |
| NO_DNS_CHANGE | YES |
| NO_TOKEN_ASSIGNMENT | YES |
| NO_WALLET | YES |
| NO_CHAIN_ACTIVATION | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |
| ASCII_SAFE_CANONICAL_TEXT | YES |
| QWEN3_ENDURANCE_NOISE_REMOVED | YES |
| NEW_SESSION_BOOTSTRAP_SUPPORTED | YES |
| INTAKE_SOURCE_CAPTURED | YES |
| EXTERNAL_0102_DISCUSSION_INTAKE_SUPPORTED | YES |
| PACKET_OUTPUT_ORDER_DEFINED | YES |
| DUPLICATE_DISCOVERY_PREFLIGHT_REQUIRED | YES |
| WORKER_COMPATIBILITY_MARKED_UNPROVEN_PENDING_PROBE | YES |
| EVALUATION_RUBRIC_DEFINED | YES |
| EXAMPLE_FIXTURE_INCLUDED | YES |
| SKILLZ_VS_EXTERNAL_SKILLS_BOUNDARY_DEFINED | YES |
| FOUNDUP_FORKS_ALLOWED_WITH_LINEAGE | YES |
| DUPLICATE_NOT_EQUAL_FORK | YES |
| FORK_LINEAGE_FIELDS_DEFINED | YES |
| PARENT_FOUNDUP_NOT_MUTATED_BY_FORK | YES |
| TOKEN_BOUNDARY_NOT_INHERITED_BY_DEFAULT | YES |
| SKILLZ_PLACEMENT_MARKED_UNPROVEN | YES |
| WSP_95_PLACEMENT_REVIEW_REQUIRED | YES |

---

## Evaluation Rubric

WSP 109 intake quality is evaluated on:

| Criterion | Description |
|-----------|-------------|
| Artifact Completeness | All 8 required artifacts present |
| Intake-Source Clarity | Source type, assumptions, and provenance clear |
| Duplicate-Discovery Quality | Proper search performed, classification justified |
| Outcome/Solution/Pain Ordering | Architect-order preserved in output |
| PoC/Prototype Separation | PoC scope bounded, prototype gate defined |
| Boundary Discipline | No code/registry/catalog/token/DNS mutation |
| WRE Handoff Clarity | Packet is routable without follow-up questions |
| No Implementation Creep | Intake only, no build artifacts |
| FoundUp Naming Quality | ID follows convention, name is descriptive |
| Manifest Draft Completeness | All required fields populated |

### Pass Rule

- All required artifacts present
- Zero hard-boundary violations
- No code/registry/catalog/token/DNS mutation
- Architect can route without asking for missing basics

---

## Example Fixture

### Shield FoundUp Intake (Reference)

**Raw Idea**: "Shield - free PoC builds trust before commitment"

**Expected Artifacts**:

| Artifact | Status |
|----------|--------|
| INTAKE_SOURCE.md | source_type: spoken_012, duplicate_status: NEW_FOUNDUP |
| OUTCOME.md | User gets free PoC code to validate trust |
| SOLUTION.md | Free PoC development service |
| PAIN.md | Buyers distrust untested vendors |
| POC_SCOPE.md | One free PoC per client |
| PROTOTYPE_GATE.md | PoC accepted -> paid engagement |
| SKILLS_MAP.md | Candidate: shield_poc_evaluator |
| FOUNDUP_MANIFEST_DRAFT.md | entity_type: foundup, tier: F0_DAE |

**Reference**: PR #717 (merged), `modules/foundups/shield/`

This fixture proves WSP 109 is self-contained.

---

## Validation Checklist

When WSP 109 completes, validate:

- [ ] All eight output contracts produced
- [ ] Entity type classified
- [ ] Trust wedge defined (POC_SCOPE.md)
- [ ] Pain point articulated (PAIN.md)
- [ ] No code written
- [ ] No registry updated
- [ ] No DNS configured
- [ ] No tokens created
- [ ] Packet ready for WRE handoff

---

## Predecessor Evidence

PR #717 provided the Shield-specific onboarding precedent. WSP 109 generalizes and canonizes the reusable intake protocol. Shield module docs remain valid as module-level application evidence.

| Evidence | Reference | Status |
|----------|-----------|--------|
| Module protocol | `modules/foundups/docs/FOUNDUP_ONBOARDING_PROTOCOL_PHASE1.md` | Valid (module-level evidence) |
| Shield validation | PR #717 | Merged (precedent) |
| Shield audit | `docs/audits/architecture/SHIELD_FOUNDUP_ONBOARDING_AND_CATALOG_SEED_PHASE1.md` | Valid (application evidence) |

---

## WSP Number Collision Note

WSP 109 was previously proposed for "Prompt Security Gating Protocol" in:
- `docs/audits/security/prompt_security/WRE_PROMPT_SECURITY_STRATEGIC_SYNTHESIS.md`

Resolution:
- WSP 109 is assigned to **FoundUp Onboarding Intake Protocol**
- Prompt Security Gating does NOT need a separate WSP
- Governance is already covered by WSP 97 (Execution) + WSP 96 (MCP)
- Execution belongs in a **skill** under WSP 95: `prompt_security_gate`
- Future slice: `PROMPT_SECURITY_GATE_SKILLZ_PHASE1`

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-05-25 | 0102 | Initial WSP creation. Promoted from module-level protocol. |
| 1.1.0 | 2026-05-25 | 0102 | Pass 3 hardening: Added INTAKE_SOURCE.md, duplicate discovery preflight, fork lineage, evaluation rubric, example fixture. Removed Qwen3 noise. Fixed glyphs to ASCII. Added Addendums E/F/G. |
