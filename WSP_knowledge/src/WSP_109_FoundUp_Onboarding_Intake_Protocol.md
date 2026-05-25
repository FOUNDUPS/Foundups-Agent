# WSP 109: FoundUp Onboarding Intake Protocol

**Version**: 1.0.0  
**Status**: Draft  
**Created**: 2026-05-25  
**Author**: W9  
**Supersedes**: `modules/foundups/docs/FOUNDUP_ONBOARDING_PROTOCOL_PHASE1.md` (module-level)  
**Predecessor**: PR #717 (Shield onboarding validation)  

---

## Purpose

WSP 109 defines how a raw 012 idea becomes an architect-ready FoundUp intake packet.

It does NOT build the FoundUp.  
It does NOT replace WRE.  
It does NOT hard-code worker topology.  
It prepares the handoff.

When 012 says "add this FoundUp, follow WSP 109", it provides the scope to add it to the codebase monorepo following WSPs.

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
    ↓
RedDog / 0102 intake conversation
    ↓
WSP 109 architect packet
    ↓
WRE orchestration layer
    ↓
Architect routes work
    ↓
Specialized workers execute
    ↓
Results return to architect / WRE
    ↓
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

WSP 109 produces seven structured artifacts:

| Artifact | Purpose | Required |
|----------|---------|----------|
| `OUTCOME.md` | What success looks like for the user | YES |
| `SOLUTION.md` | How the FoundUp solves the problem | YES |
| `PAIN.md` | What pain point drives adoption | YES |
| `POC_SCOPE.md` | Minimum viable proof-of-concept boundary | YES |
| `PROTOTYPE_GATE.md` | Criteria to advance from POC to prototype | YES |
| `SKILLS_MAP.md` | Candidate skillz for future wardrobe | YES |
| `FOUNDUP_MANIFEST_DRAFT.md` | Draft manifest for registry seed | YES |

These are NOT final build instructions. They are WRE-ready intake artifacts.

---

## Contract Definitions

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

## POC → Prototype Criteria
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
    ↓
RedDog / 0102 intake conversation
    ↓
WSP 109 architect packet
    ↓
WRE orchestration layer
    ↓
Architect routes work
    ↓
Specialized workers execute, research, evaluate, test, document, and refine
    ↓
Results return to architect / WRE
    ↓
PoC / prototype / MVP progression
```

### WSP 109 Output Role

WSP 109 outputs the structured packet:

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

### Qwen3 Endurance Note

The Qwen3 35-hour run validates the FoundUps development framework's ability to sustain long-running recursive agent work.

This is a milestone signal for WRE viability.

It does not mean WSP 109 should absorb orchestration logic.

It means WSP 109 should hand off cleanly into WRE because the recursive engine has demonstrated operational endurance.

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

### Boundary

| Activity | Protocol |
|----------|----------|
| List candidate skills | WSP 109 |
| Create skill files | WSP 95 |
| Promote skills to wardrobe | WSP 95 |
| Skill execution | WRE |

### Candidate SKILLz for Onboarding

Future slice `FOUNDUP_ONBOARDING_SKILLZ_WARDROBE_PHASE1` may create:

- `foundup_intake_normalizer`
- `foundup_pain_solution_outcome_mapper`
- `foundup_poc_scope_guard`
- `foundup_prototype_gate_mapper`
- `foundup_manifest_draft_generator`
- `foundup_duplicate_discovery_holoindex`
- `foundup_catalog_readiness_evaluator`

These are recommendations, not created by this WSP.

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

| Boundary | Status |
|----------|--------|
| Does not write code | ENFORCED |
| Does not update registry | ENFORCED |
| Does not configure DNS | ENFORCED |
| Does not create tokens | ENFORCED |
| Does not create public routes | ENFORCED |
| Hands off to architect/WRE | ENFORCED |
| Does not replace WRE | ENFORCED |
| Does not hard-code worker topology | ENFORCED |
| Does not create SKILLz | ENFORCED |

---

## Validation Checklist

When WSP 109 completes, validate:

- [ ] All seven output contracts produced
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

This WSP was promoted from module-level protocol after validation:

| Evidence | Reference |
|----------|-----------|
| Module protocol | `modules/foundups/docs/FOUNDUP_ONBOARDING_PROTOCOL_PHASE1.md` |
| Shield validation | PR #717 |
| Shield audit | `docs/audits/architecture/SHIELD_FOUNDUP_ONBOARDING_AND_CATALOG_SEED_PHASE1.md` |

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
| 1.0.0 | 2026-05-25 | W9 | Initial WSP creation. Promoted from module-level protocol. |
