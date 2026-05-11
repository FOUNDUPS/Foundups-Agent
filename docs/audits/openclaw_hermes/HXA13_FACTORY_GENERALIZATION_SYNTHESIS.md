# HXA13 — FoundUp Factory Dry-Run Generalization Synthesis

**Slice**: `HXA13_FACTORY_GENERALIZATION_SYNTHESIS_PHASE1`
**Worker**: W5
**Date**: 2026-05-11
**Mode**: Audit-only — no code edits
**Branch**: `docs/hxa13-factory-generalization-synthesis`
**WSP Lock**: WSP 00 → WSP 97 → WSP 15 → WSP 50

---

## 1. Final Verdict

### **FACTORY_DRYRUN_GENERALIZATION_COMPLETE**

VoteBallots + GotJunk prove the internal FoundUp factory dry-run path generalizes across at least two FoundUp targets.

**This does not prove**:
- Live execution
- External federation
- Production repo creation
- CABR readiness
- DAO readiness

---

## 2. WSP 97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| VoteBallots dry-run proof complete | **VERIFIED** | HXA3/HXA4/HXA9/HXA10 tests pass |
| GotJunk dry-run proof complete | **VERIFIED** | HXA12 tests pass |
| Factory generalizes across 2 targets | **VERIFIED** | Same code path, same artifact types |
| Real Hermes executor object reached | **VERIFIED** | Both tests use non-mocked `HermesJobExecutor` |
| Scaffold artifacts in evidence workspace | **VERIFIED** | Both generate `controlled_scaffold.json` |
| Production source unchanged | **VERIFIED** | Both assert `production_source_modified=False` |
| Live delegation disabled | **VERIFIED** | Both assert `_delegate_task_fn=None` |
| `real_execution_performed=False` | **VERIFIED** | All tests assert this |
| `repo_created=False` | **VERIFIED** | All tests assert this |
| External federation ready | **FALSE** | Not claimed, not proven |
| CABR validation ready | **FALSE** | Not claimed, not proven |
| Production readiness | **FALSE** | Not claimed, not proven |

---

## 3. Verified Artifact Chain

| Slice | Artifact | Lines | Status |
|-------|----------|-------|--------|
| HXA3 | `test_openclaw_voteballots_dryrun_proof.py` | 299 | ✓ on main |
| HXA4 | `test_hxa4_real_hermes_object_dryrun.py` | 700+ | ✓ on main |
| HXA8 | `HXA8_OPENCLAW_HERMES_FACTORY_SYNTHESIS.md` | 250+ | ✓ on main |
| HXA11 | `HXA11_VOTEBALLOTS_FACTORY_PROOF_SYNTHESIS.md` | 300+ | ✓ on main |
| HXA12 | `test_hxa12_gotjunk_second_proof_dryrun.py` | 406 | ✓ on main |

**Git Evidence**:
```
ce964926f test(hermes): prove GotJunk second FoundUp safe dry-run path (#557)
d8ae4b71b docs(audit): synthesize VoteBallots FoundUp factory dry-run proof (#556)
552f9920f feat(hermes): generate VoteBallots scaffold artifacts in safe dry-run workspace (#555)
1a9eb1efa feat(hermes): generate VoteBallots PoC artifact bundle in safe dry-run (#554)
```

---

## 4. VoteBallots Proof Summary

**Target**: `voteballots` (idea-stage, no deployment)

| Proof Point | Slice | Evidence |
|-------------|-------|----------|
| Intent detection | HXA3 | `_is_explicit_build_intent("start build voteballots --dry-run")` |
| Job creation | HXA3 | `dispatch_foundup()` creates job with `dry_run_mode=True` |
| Queue drain | HXA3 | `drain_openclaw_queue_once()` |
| WRE routing | HXA3 | Routes to `HERMES_BUILDER` |
| Real executor reached | HXA4 | `HermesJobExecutor(dry_run=True).execute(job)` |
| PoC artifact plan | HXA9 | `poc_artifact_bundle.json` generated |
| Controlled scaffold | HXA10 | `controlled_scaffold.json` + `{foundup_id}_poc/` directory |
| WSP 97 truth fields | HXA4/HXA10 | All `False` except simulation markers |

**Lifecycle Stage**: `incubating` (no `entry_url`)

---

## 5. GotJunk Proof Summary

**Target**: `gotjunk_001` (deployed, operational)

| Proof Point | Slice | Evidence |
|-------------|-------|----------|
| Intent detection | HXA12 | `_is_explicit_build_intent("start build gotjunk_001 --dry-run")` |
| Job creation | HXA12 | `dispatch_foundup()` creates job with `foundup_id=gotjunk_001` |
| Real executor reached | HXA12 | `HermesJobExecutor(dry_run=True).execute(job)` |
| PoC artifact plan | HXA12 | `poc_artifact_bundle.json` with `foundup_id=gotjunk_001` |
| Controlled scaffold | HXA12 | `controlled_scaffold.json` + `gotjunk_001_poc/` directory |
| Parity with VoteBallots | HXA12 | `TestGotJunkVoteBallotsParity` tests |
| WSP 97 truth fields | HXA12 | All `False` except simulation markers |

**Lifecycle Stage**: `proto` (deployed `entry_url`)

**Key Distinction**: GotJunk has a deployed Cloud Run instance, proving the factory handles both idea-stage and operational FoundUps.

---

## 6. Factory Generalization Assessment

### 6.1 Generalization Proof

| Criterion | VoteBallots | GotJunk | Generalized? |
|-----------|-------------|---------|--------------|
| Same intent detection | ✓ | ✓ | YES |
| Same job creation | ✓ | ✓ | YES |
| Same executor object | ✓ | ✓ | YES |
| Same artifact types | ✓ | ✓ | YES |
| Same WSP 97 fields | ✓ | ✓ | YES |
| Scaffold references target | `voteballots` | `gotjunk_001` | YES |

### 6.2 Code Path Analysis

```
OpenClaw Intent ──► dispatch_foundup() ──► FoundUpJob
                                               │
                                               ▼
                                      FoundUpJobConsumer
                                               │
                                               ▼
                                      HermesJobExecutor.execute()
                                               │
                                               ▼
                              ┌────────────────┴────────────────┐
                              │                                 │
                              ▼                                 ▼
                    VoteBallots                           GotJunk
                    (voteballots)                      (gotjunk_001)
                              │                                 │
                              ▼                                 ▼
                    poc_artifact_bundle.json         poc_artifact_bundle.json
                    controlled_scaffold.json         controlled_scaffold.json
                    voteballots_poc/                 gotjunk_001_poc/
```

**Conclusion**: The factory code path is identical. Only the `foundup_id` differs.

### 6.3 Parity Tests

`TestGotJunkVoteBallotsParity` (HXA12, lines 329-405) explicitly verifies:
- Same evidence file types
- Same scaffold structure
- Same WSP 97 truth field values

---

## 7. What Is Still Not Proven

| Gap | Impact | Required For |
|-----|--------|--------------|
| Live `delegate_task` invocation | Cannot generate production source | HXA14 |
| Production source generation | FoundUp `src/` directories remain stubs | Live delegation harness |
| Third FoundUp proof (Trade) | N+1 generalization | Optional, low priority |
| External repo creation | No GitHub operations | DE4 extraction |
| CABR validation | External FoundUps get fake scores | MCPA10 |
| Human approval gate | Not exercised in dry-run | Production readiness |
| p.fMALL/pAVS external federation | External agents cannot onboard | MCPA10 + SDK publishing |

---

## 8. WSP 15 Priority Ranking

| Rank | Slice | Impact | Risk | Effort | SCORE |
|------|-------|--------|------|--------|-------|
| **P0** | `HXA14_CONTROLLED_LIVE_HERMES_DELEGATION_HARNESS_PHASE1` | HIGH — enables production | MEDIUM | HIGH | **85** |
| P1 | `MCPA10_CABR_BACKEND_RECONCILIATION_PHASE1` | MEDIUM — external readiness | LOW | MEDIUM | 70 |
| P2 | `PFMALL_PAVS_EXTERNAL_FEDERATION_PILOT_PHASE1` | LOW — requires live delegation | MEDIUM | HIGH | 50 |
| P2 | `LINK_SENTINEL_CONSUMER_HOOK_PHASE1` | LOW — security layer | LOW | LOW | 45 |
| P3 | `HXA15_TRADE_THIRD_PROOF_SAFE_DRYRUN_PHASE1` | LOW — N+1, diminishing returns | LOW | LOW | 35 |

**Ranking Rationale**:
- HXA14 is P0 because the factory dry-run path is now proven. The next bottleneck is controlled live delegation.
- MCPA10 is P1 because external FoundUps need real CABR scores before federation.
- Third proof (Trade) is P3 because 2 targets (VoteBallots + GotJunk) already prove generalization; a third adds marginal value.

---

## 9. Recommended Next Slice

### **P0: HXA14_CONTROLLED_LIVE_HERMES_DELEGATION_HARNESS_PHASE1**

**Mission**: Create a controlled test harness that enables `HERMES_DELEGATE_ENABLED=1` in isolation, proving the factory can invoke live delegation without production side effects.

**Scope**:
1. Create `test_hxa14_controlled_live_delegation_harness.py`
2. Test harness sets `HERMES_DELEGATE_ENABLED=1` via fixture
3. Mock or stub `delegate_task` to capture invocation without real execution
4. Prove `_delegate_task_fn` is imported and callable
5. Prove `HermesDelegationRequest` is passed correctly
6. Assert `real_execution_performed=True` (delegation was attempted)
7. Assert `repo_created=False` (no GitHub side effects)
8. Assert `production_source_modified=False`

**WSP 97 Boundaries**:
- Delegation is invoked but not executed to completion
- Test harness only, not production code change
- No external repo creation
- No CABR claims
- No payout operations

**Success Criteria**:
- `_lazy_import_delegate_task()` returns `True`
- `delegate_task` is called with `HermesDelegationRequest`
- Evidence shows controlled delegation attempt

---

## 10. External Federation Gate

### Current State

| Component | Status | Blocker |
|-----------|--------|---------|
| Internal factory dry-run | PROVEN | None |
| Internal factory generalization | PROVEN | None |
| Live delegation harness | NOT IMPLEMENTED | HXA14 |
| pAVS HTTP transport | REAL | None |
| pAVS 6/8 tools | REAL backends | None |
| pAVS `cabr_validate` | PLACEHOLDER | MCPA10 |
| pAVS SDKs | NOT PUBLISHED | MCPA11 |
| p.fMALL shell | Architecture locked | Stakeholder gate |

### Federation Unlock Sequence

```
HXA12 (GotJunk second proof) ✓
    │
    ▼
HXA13 (Generalization synthesis) ✓ ← YOU ARE HERE
    │
    ▼
HXA14 (Live delegation harness) ← NEXT
    │
    ▼
MCPA10 (CABR backend)
    │
    ▼
MCPA11 (SDK publishing)
    │
    ▼
External federation pilot
```

**Verdict**: External federation remains blocked until live delegation harness (HXA14) and CABR backend (MCPA10) are proven.

---

## 11. CABR / ROC / Proof-of-Benefit Implications

### CABR Readiness

| Component | Status | Notes |
|-----------|--------|-------|
| CABR engine (V3) | EXISTS | `WSP_29_CABR_Engine.md` |
| `cabr_validate` tool | PLACEHOLDER | Returns hardcoded `score=0.85` |
| CABR integration tests | NONE | Need MCPA10 |

**Impact**: Until CABR backend is real, external FoundUps cannot receive validated contribution scores.

### ROC Implications

| Metric | Dry-Run | Live Delegation |
|--------|---------|-----------------|
| Proof of Compute | Simulated | Real (harness) |
| Evidence files | Generated | Generated |
| CABR claim | NOT ALLOWED | NOT ALLOWED (Phase 1) |
| Payout claim | NOT ALLOWED | NOT ALLOWED |

### Proof-of-Benefit Path

```
Dry-Run (proven) → Live Harness (HXA14) → Controlled Production (HXA15+) → CABR Validation → ROC Milestone → Payout
```

Current position: **Dry-Run proven. Next: Live Harness.**

---

## 12. HoloIndex Search Evidence

**Query**: `HXA12 GotJunk VoteBallots factory generalization Hermes dry-run live delegation harness external federation CABR`

**Top Hits**:
| Type | Path | Relevance |
|------|------|-----------|
| WSP | `WSP_29_CABR_Engine.md` | CABR backend spec |
| WSP | `WSP_103_FoundUp_Federation_Protocol.md` | External federation rules |
| WSP | `WSP_106_FoundUp_API_Gateway_Protocol.md` | API gateway for external |
| DOCS | `WSP_UPDATE_RECOMMENDATIONS_MCP_FEDERATION.md` | Federation update notes |

**Note**: HoloIndex did not directly return HXA test files because they are in `tests/` directories which may have lower index priority. Direct glob/grep verification was used instead.

---

## 13. Open Questions

| Question | Owner | Priority |
|----------|-------|----------|
| Should HXA14 mock `delegate_task` or use a stub executor? | HXA14 worker | HIGH |
| Should Trade be third proof target or skip to live harness? | 012 | LOW |
| When should MCPA10 (CABR backend) be prioritized vs HXA14? | 012 | MEDIUM |
| Should external federation pilot wait for 3 proof targets or proceed after 2? | 012 | LOW |

**Recommendation**: Proceed to HXA14 (live delegation harness) since factory generalization is proven. Trade third proof can be deferred — 2 targets are sufficient for generalization.

---

## Sources

### Git Log (origin/main)

```
ce964926f test(hermes): prove GotJunk second FoundUp safe dry-run path (#557)
d8ae4b71b docs(audit): synthesize VoteBallots FoundUp factory dry-run proof (#556)
552f9920f feat(hermes): generate VoteBallots scaffold artifacts (#555)
1a9eb1efa feat(hermes): generate VoteBallots PoC artifact bundle (#554)
59a68d76e docs(audit): synthesize OpenClaw Hermes factory proof state (#553)
```

### Files Verified

| File | Status |
|------|--------|
| `test_openclaw_voteballots_dryrun_proof.py` | ✓ exists |
| `test_hxa4_real_hermes_object_dryrun.py` | ✓ exists |
| `test_hxa12_gotjunk_second_proof_dryrun.py` | ✓ exists |
| `HXA8_OPENCLAW_HERMES_FACTORY_SYNTHESIS.md` | ✓ exists |
| `HXA11_VOTEBALLOTS_FACTORY_PROOF_SYNTHESIS.md` | ✓ exists |

---

## WSP 97 Closing Statement

This synthesis confirms the FoundUp factory dry-run path is **generalized across VoteBallots and GotJunk**. Both targets follow identical code paths, generate identical artifact types, and respect identical WSP 97 truth boundaries.

**What is claimed**:
- Dry-run factory path proven for 2 distinct FoundUp targets
- Real Hermes executor object reached without mocking
- Scaffold artifacts generated in evidence workspace
- Production source remains unchanged

**What is NOT claimed**:
- Production readiness
- Live delegation
- External repo creation
- External agent onboarding readiness
- p.fMALL federation readiness
- CABR validation readiness
- DAO/DAE promotion readiness

---

*Audit performed by Worker W5 under WSP 97 truth boundaries.*

Worker W5 complete for HXA13_FACTORY_GENERALIZATION_SYNTHESIS_PHASE1.
