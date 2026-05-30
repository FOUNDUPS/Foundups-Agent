# OPUS_4_8_WORKER_ORCHESTRATION_PROBE_PHASE1

**Slice**: `OPUS_4_8_WORKER_ORCHESTRATION_PROBE_PHASE1`
**Worker**: W9
**Date**: 2026-05-30
**Status**: ORCHESTRATION PROBE
**Mode**: DOCS-ONLY / NO IMPLEMENTATION

---

## Critical Finding

**The original Vote PoC Hardening Chain (H1-H6) is INVALID as written.**

Vote PoC is governance-closed by PR #715. The proposed H1-H5 slices all require Vote mutation, which triggers re-open criteria. Only H6 (closure snapshot) is inherently docs-only, but it cannot exist without the preceding slices.

This probe demonstrates that Opus 4.8 correctly:
1. Reads governance closure state
2. Respects V1-V8 re-open criteria
3. Rejects invalid implementation proposals
4. Proposes safer alternatives

---

## 1. Mission and Scope

### 1.1 Objective

Test whether Opus 4.8 can act as a 0102 internal worker-orchestration planner by:
- Reading closure governance
- Respecting #715 Vote V1-V8 re-open criteria
- Building parallel/sequential worker DAGs
- Classifying slices as safe, blocked, or requiring re-open citation
- Producing improved dispatch packets without vibecoding
- Defining how worker outputs improve the orchestration system itself

### 1.2 Constraints

This is an orchestration probe, NOT implementation:
- NO Vote code mutation
- NO Vote test mutation
- NO Vote fixture mutation
- NO Vote ROADMAP mutation
- NO route/registry/catalog/manifest mutation
- Exactly one file produced (this audit)

---

## 2. Predecessor Citations

| PR | Slice | Relevance |
|----|-------|-----------|
| #715 | VOTE_POC_CHAIN_OBSERVATION_SNAPSHOT_PHASE1 | Defines V1-V8 re-open criteria |
| #718 | WSP_109_FOUNDUP_ONBOARDING_INTAKE_PROTOCOL_PHASE1 | Worker execution validation patterns |
| #725 | REDDOG_BOOTSTRAP_CONTEXT_RETRIEVAL_PHASE1 | Context retrieval patterns |
| #733 | LM_STUDIO_DEPENDENCY_BOUNDARY_DOC_AND_GATE_PHASE1 | Dependency boundary gating |

---

## 3. HoloIndex Retrieval Evaluation

| Query | Hits | Quality | Finding |
|-------|------|---------|---------|
| VOTE_POC_CHAIN_OBSERVATION_SNAPSHOT_PHASE1 V1 V8 | 20 | Medium | Semantic drift to Trade/CABR docs |
| Vote PoC closure governance re-open criteria | 20 | Medium | Mixed results, audit docs found |
| WSP 109 worker compatibility probe | 20 | Low | No direct WSP 109 hits |
| WSP 97 Truth Boundary Checklist worker orchestration | 20 | Medium | WSP docs found |
| OpenClaw Hermes Qwen worker orchestration | 20 | Low | Scattered results |

**Assessment**: HoloIndex semantic search requires direct file path access for precise governance docs. The closure snapshot at `docs/audits/architecture/VOTE_POC_CHAIN_OBSERVATION_SNAPSHOT_PHASE1.md` was read directly.

---

## 4. Vote PoC Governance Closure Summary

### 4.1 Current State (from #715)

| Attribute | Value |
|-----------|-------|
| Chain status | 6/6 slices MERGED |
| Tests | 303 passing |
| entry_url | EMPTY |
| launch_readiness | discoverable_only |
| Public surface | NONE |
| Governance state | CLOSED |

### 4.2 Critical Statement from #715

> "Implementation-complete does NOT mean public-launched."

The chain is locked. Any mutation requires explicit re-open.

---

## 5. V1-V8 Re-Open Criteria Matrix

| ID | Criterion | Triggers On |
|----|-----------|-------------|
| V1 | Live FEC API activation | Network calls to FEC |
| V2 | Public route or entry_url activation | Route handlers, entry_url change |
| V3 | Registry/entity promotion | Registry/catalog changes |
| V4 | Persuasion/recommendation/targeting | Political safety violation |
| V5 | Confidence rule change | confidence_scoring.py mutation |
| V6 | LLM/new facts in answers | quick_answer.py mutation, LLM calls |
| V7 | CABR/payout/DAO claim | Manifest governance fields |
| V8 | Shell contract change | shell_integration.py mutation |

---

## 6. Original H1-H6 Chain Assessment

### 6.1 Governance Subworker Analysis

| Slice | Proposed Action | Vote Files Touched | V1-V8 Trigger | Classification |
|-------|-----------------|-------------------|---------------|----------------|
| H1 | Update ROADMAP.md | `ROADMAP.md` | DOCS mutation | **REQUIRES_REOPEN** |
| H2 | Expand mock fixtures | `fec_adapter.py` | Code mutation | **REQUIRES_REOPEN** |
| H3 | Create CLI demo | New `vote_demo.py` | Code addition | **REQUIRES_REOPEN** |
| H4 | Add edge case tests | `tests/*.py` | Test mutation | **REQUIRES_REOPEN** |
| H5 | Pipeline benchmark | New benchmark code | Code addition | **REQUIRES_REOPEN** |
| H6 | Hardening snapshot | Docs only | None | **BLOCKED** (depends on H1-H5) |

### 6.2 Detailed Classification

**H1 - Update ROADMAP.md**
- Action: Mutate `modules/foundups/voteballots/ROADMAP.md`
- Violation: #715 prohibits Vote docs mutation without re-open
- Re-open path: Architect must issue explicit docs-update packet citing "ROADMAP staleness" as justification
- Classification: **REQUIRES_REOPEN_CRITERION**

**H2 - Expand mock fixtures**
- Action: Add candidates to `fec_adapter.py` fixtures
- Violation: Code mutation on closed chain
- Re-open path: Could cite V1 (expanding mock before live API) but stretches intent
- Classification: **REQUIRES_REOPEN_CRITERION**

**H3 - Create CLI demo script**
- Action: Add new `vote_demo.py`
- Violation: Code addition to closed chain
- Re-open path: No clean V1-V8 fit; would need new criterion "V9: Demo tooling"
- Classification: **BLOCKED_UNTIL_ARCHITECT_APPROVAL**

**H4 - Add edge case tests**
- Action: Mutate test files
- Violation: Test mutation on closed chain
- Re-open path: Could argue "test hardening" but #715 explicitly lists "NO test mutation"
- Classification: **REQUIRES_REOPEN_CRITERION**

**H5 - Pipeline benchmark**
- Action: Add benchmark code
- Violation: Code addition to closed chain
- Re-open path: No V1-V8 fit
- Classification: **BLOCKED_UNTIL_ARCHITECT_APPROVAL**

**H6 - Final hardening snapshot**
- Action: Docs-only snapshot
- Violation: None inherently, but depends on H1-H5 completing
- Classification: **BLOCKED** (dependency chain invalid)

### 6.3 Summary Count

| Classification | Count | Slices |
|----------------|-------|--------|
| SAFE_DOCS_ONLY | 0 | - |
| REQUIRES_REOPEN_CRITERION | 3 | H1, H2, H4 |
| BLOCKED_UNTIL_ARCHITECT_APPROVAL | 2 | H3, H5 |
| BLOCKED (dependency) | 1 | H6 |
| **Total** | 6 | All require action |

---

## 7. Worker DAG Model

### 7.1 Original Proposed DAG

```
        ┌─── H1 (ROADMAP) ───┐
        │                    │
START ──┼─── H2 (fixtures) ──┼──► H3 (demo) ──► H5 (benchmark) ──► H6 (snapshot) ──► END
        │         │          │
        └─── H4 (tests) ─────┘
             │
             └─────────────────────────────────────────────────────►
```

### 7.2 DAG Validity Assessment

| Edge | Valid? | Reason |
|------|--------|--------|
| START → H1 | NO | H1 requires re-open |
| START → H2 | NO | H2 requires re-open |
| START → H4 | NO | H4 requires re-open |
| H2 → H3 | NO | H3 blocked |
| H1,H2,H4 → H5 | NO | H5 blocked |
| H5 → H6 | NO | Chain broken |

**DAG Status**: INVALID - No executable path exists without governance action.

---

## 8. Parallel vs Sequential Execution Analysis

### 8.1 Original Plan

- **Parallel batch 1**: H1, H2, H4
- **Sequential**: H3 (after H2)
- **Sequential**: H5 (after all)
- **Sequential**: H6 (after H5)

### 8.2 Analysis

The parallel/sequential structure is sound **if** the slices were valid. The orchestration pattern itself is correct:
- Independent slices (H1, H2, H4) can parallelize
- Dependent slices (H3, H5, H6) must sequence

The problem is not the DAG structure but the **governance validity** of the nodes.

---

## 9. Governance Risk Findings

### 9.1 Critic Subworker Attack Results

| Risk | Finding | Severity |
|------|---------|----------|
| Vibecode risk | Original plan skips governance check | HIGH |
| Governance violation | 5 of 6 slices violate #715 closure | CRITICAL |
| Stale assumption | Assumes Vote is open for mutation | HIGH |
| Implementation creep | Treats docs-only probe as implementation trigger | MEDIUM |
| Over-claiming | "PoC-safe" label on code-mutating slices | HIGH |

### 9.2 Specific Violations

1. **#715 violation**: Closure explicitly states "NO code mutation, NO test mutation"
2. **V1-V8 bypass**: Original plan does not cite any re-open criterion
3. **Scope creep**: "Hardening" framed as safe when it requires implementation

### 9.3 Root Cause

The original architect proposal (me) failed to re-read #715 constraints before proposing H1-H6. This probe correctly identifies that failure.

---

## 10. Improved Orchestration Pattern

### 10.1 Key Insight

The orchestration system itself can be tested **without touching Vote**. Use a non-governance-closed substrate or create a synthetic test module.

### 10.2 Alternative Approaches

| Approach | Substrate | Risk |
|----------|-----------|------|
| A | Create `modules/foundups/worker_probe/` as new module | Zero Vote risk |
| B | Use Trade PoC (if not closed) | Depends on Trade state |
| C | Formally re-open Vote with explicit criterion | Architect overhead |
| D | Read-only Vote analysis (no mutation) | Safe but limited |

**Recommended**: Approach A or D

---

## 11. READ_ONLY_ORCHESTRATION_PROBE Dispatch Packet

This packet tests orchestration modeling without any implementation.

```text
W9 / OPUS 4.8 DISPATCH — WORKER_ORCHESTRATION_READ_ONLY_ANALYSIS_PHASE1

MISSION

Test worker orchestration modeling capability using Vote PoC as read-only
substrate. NO Vote files mutated.

SCOPE

Exactly one file:
  docs/audits/architecture/WORKER_ORCHESTRATION_READ_ONLY_ANALYSIS_PHASE1.md

ACTIONS

1. Read Vote PoC state (303 tests, 6 slices, closure snapshot)
2. Model a hypothetical worker DAG for future Vote work
3. Classify each hypothetical slice against V1-V8
4. Produce W10-ready dispatch template (not actual dispatch)
5. Evaluate Opus 4.8 modeling accuracy

CONSTRAINTS

- READ_ONLY
- NO_VOTE_MUTATION
- NO_IMPLEMENTATION
- DOCS_ONLY

WSP_97 CHECKLIST

Must include Truth Boundary Checklist with declared count = actual rows.
```

---

## 12. IMPLEMENTATION_CHAIN_REQUIRING_ARCHITECT_REOPEN_APPROVAL Dispatch Packet

This packet is blocked until architect explicitly re-opens Vote.

```text
BLOCKED — VOTE_POC_HARDENING_IMPLEMENTATION_CHAIN_PHASE1

STATUS: REQUIRES ARCHITECT APPROVAL

PREREQUISITE

Architect must issue re-open packet citing:
- Which V1-V8 criterion justifies the work
- Explicit acknowledgment of #715 closure override
- Updated governance snapshot plan

SLICES (if approved)

H1_REOPEN: Update ROADMAP.md
  Criterion: Docs staleness (new V9 or architect exception)
  
H2_REOPEN: Expand mock fixtures
  Criterion: V1 (mock expansion as pre-live hardening)
  
H4_REOPEN: Add edge case tests
  Criterion: V1 (test hardening as pre-live validation)

BLOCKED SLICES (no V1-V8 fit)

H3: CLI demo - requires new criterion or architect exception
H5: Benchmark - requires new criterion or architect exception

POST-REOPEN CHAIN

If approved:
  H1_REOPEN, H2_REOPEN, H4_REOPEN (parallel)
  → W10 gate
  → H3 (if approved)
  → W10 gate
  → H5 (if approved)
  → W10 gate
  → H6 (closure snapshot)

DISPATCH AUTHORITY

Only 012/0102 architect can approve this packet.
```

---

## 13. Opus 4.8 Capability Evaluation Rubric

| Capability | Test | Result |
|------------|------|--------|
| Read governance state | Extract V1-V8 from #715 | PASS |
| Respect closure | Reject invalid H1-H6 | PASS |
| Classify slices | Distinguish safe/blocked/reopen | PASS |
| Build DAG | Model dependencies correctly | PASS |
| Identify violations | Find 5/6 slices invalid | PASS |
| Propose alternatives | Offer read-only probe | PASS |
| Avoid vibecoding | No blind implementation | PASS |
| Self-correct | Identify own prior error | PASS |

**Opus 4.8 Orchestration Modeling**: CAPABLE

---

## 14. Recommendation

### 14.1 Verdict on Original H1-H6

**REJECT** - The original Vote PoC Hardening Chain is invalid under #715 governance closure.

### 14.2 Safe First Slice

**Option A (Safest)**: `WORKER_ORCHESTRATION_READ_ONLY_ANALYSIS_PHASE1`
- Read-only analysis of Vote without mutation
- Tests orchestration modeling capability
- Zero governance risk

**Option B (If Vote work needed)**: Architect issues explicit re-open packet
- Cite specific V1-V8 criterion
- Acknowledge #715 override
- Define minimal scope

### 14.3 How Worker Outputs Improve Orchestration

1. **Governance validation**: Workers must check closure state before proposing mutations
2. **DAG validation**: Workers must verify all nodes are executable before building DAG
3. **Re-open citation**: Workers must cite V1-V8 when proposing closed-chain work
4. **Probe before implement**: Use read-only probes to validate orchestration before implementation

---

## 15. Internal Review Section

### 15.1 Pre-Gate Checklist

| Item | Status |
|------|--------|
| Scope matches probe definition | YES |
| No Vote files mutated | YES |
| Exactly one file produced | YES |
| #715 closure respected | YES |
| V1-V8 criteria evaluated | YES |
| Original chain assessed | YES |
| DAG modeled | YES |
| Improved packets produced | YES |
| Capability rubric completed | YES |

### 15.2 Internal Review Verdict

**READY**

Probe demonstrates Opus 4.8 correctly rejects invalid implementation proposals and respects governance closure.

---

## 16. WSP 97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | ORCHESTRATION_PROBE_ONLY | YES | No implementation |
| 2 | NO_VOTE_CODE_MUTATION | YES | No src files touched |
| 3 | NO_VOTE_TEST_MUTATION | YES | No test files touched |
| 4 | NO_VOTE_FIXTURE_MUTATION | YES | fec_adapter.py unchanged |
| 5 | NO_VOTE_ROADMAP_MUTATION | YES | ROADMAP.md unchanged |
| 6 | NO_ROUTE_MUTATION | YES | No routes touched |
| 7 | NO_REGISTRY_MUTATION | YES | No registry touched |
| 8 | NO_CATALOG_MUTATION | YES | No catalog touched |
| 9 | NO_MANIFEST_MUTATION | YES | Manifest unchanged |
| 10 | NO_PUBLIC_SURFACE_MUTATION | YES | No public files |
| 11 | NO_TOKEN_ASSIGNMENT | YES | No token work |
| 12 | NO_CABR_READY | YES | No CABR claim |
| 13 | NO_PAYOUT_READY | YES | No payout claim |
| 14 | NO_DAO_ACTIVATION | YES | No DAO claim |
| 15 | CITES_PR_715_CLOSURE | YES | Section 4 |
| 16 | V1_V8_REOPEN_CRITERIA_EVALUATED | YES | Section 5-6 |
| 17 | WORKER_DAG_DEFINED | YES | Section 7 |
| 18 | PARALLEL_DEPENDENCIES_EXPLICIT | YES | Section 8 |
| 19 | W10_GATE_DEFINED | YES | Section 12 |
| 20 | NO_IMPLEMENTATION_DISPATCH_WITHOUT_ARCHITECT_APPROVAL | YES | Section 12 blocked |

**WSP 97 Truth Boundary Checklist: 20/20 YES**

---

## 17. Answers to Success Criteria

1. **Is the original Vote hardening chain valid as written?**
   NO - 5 of 6 slices violate #715 closure.

2. **Which H slices, if any, require V1-V8 citation?**
   H1, H2, H4 could cite V1 (mock/test hardening). H3, H5 have no clean fit.

3. **Which slices should be converted into read-only orchestration tests?**
   All of them. A read-only analysis probe is the safe first step.

4. **What is the safest first real Opus 4.8 slice?**
   `WORKER_ORCHESTRATION_READ_ONLY_ANALYSIS_PHASE1` - read Vote, model DAG, no mutation.

5. **How do internal worker outputs improve the orchestration system?**
   - Governance pre-check becomes mandatory
   - DAG node validation added
   - Re-open citation required for closed chains
   - Probe-before-implement pattern established

---

*W9 complete for OPUS_4_8_WORKER_ORCHESTRATION_PROBE_PHASE1. Opus 4.8 correctly rejected invalid implementation chain and proposed safer alternatives. Ready for W10 review.*
