# HXA8 — OpenClaw Hermes FoundUp Factory Synthesis

**Slice**: `HXA8_OPENCLAW_HERMES_FACTORY_SYNTHESIS_PHASE1`
**Worker**: W5
**Date**: 2026-05-10
**Mode**: Audit-only — no code edits
**WSP Lock**: WSP 00 → WSP 97 → WSP 15 → WSP 50

---

## 1. Final Verdict

### **READY_FOR_VOTEBALLOTS_POC_GENERATION**

The internal OpenClaw → Hermes factory trunk is **proven safe at the dry-run level**. HXA3 proves the mocked seam. HXA4 proves the real HermesJobExecutor object is reached without live delegation. The factory is ready to generate/update VoteBallots PoC artifacts in safe dry-run mode.

---

## 2. HXA3 Truth: Mocked Hermes Seam Proof

**Artifact**: `modules/infrastructure/wre_core/tests/test_openclaw_voteballots_dryrun_proof.py` (299 lines)

**What it proves**:
- OpenClaw intent detection parses `"start build voteballots --dry-run"` correctly
- `_is_explicit_build_intent()` returns `True`
- `_extract_foundup_id()` returns `"voteballots"`
- `_detect_dry_run_mode()` returns `True`
- FoundUpJob created with `dry_run_mode=True` and `tenant_id="012"`
- Job added to queue via `dispatch_foundup()`
- WRE Consumer drains queue
- Job routes to `HERMES_BUILDER` backend
- Hermes executor invoked (mocked in HXA3)
- All WSP 97 truth fields asserted:
  - `real_execution_performed=False`
  - `verification_complete=False`
  - `cabr_ready=False`
  - `payout_ready=False`

**Test Classes**:
| Class | Assertions |
|-------|------------|
| `TestVoteBallotsBuildIntentDetection` | 3 tests |
| `TestVoteBallotsDryRunJobCreation` | 1 test |
| `TestVoteBallotsDryRunPipelineProof` | 2 tests |
| `TestVoteBallotsBuildRouting` | 1 test |

**Key Assertion**:
```python
@patch("modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job")
def test_openclaw_voteballots_foundup_build_dryrun_reaches_hermes(self, mock_hermes_execute):
    # ...
    mock_hermes_execute.assert_called_once()
    assert result.checkpoint_state == "SIMULATED"
    assert result.real_execution_performed is False
```

**Verdict**: TRUNK PATH PROVEN (mocked seam)

---

## 3. HXA4 Truth: Real Hermes Executor Object Safe Dry-Run Proof

**Artifact**: `modules/infrastructure/wre_core/tests/test_hxa4_real_hermes_object_dryrun.py` (458 lines)

**What it proves**:
- Real `HermesJobExecutor` object instantiated (NOT mocked)
- `HERMES_DELEGATE_ENABLED=0` enforced as safety gate
- `is_hermes_delegation_enabled()` returns `False`
- VoteBallots job reaches `HermesJobExecutor.execute()` method
- Execution status: `HermesExecutionStatus.SIMULATED`
- Evidence files written to disk (`metadata.json`, `checkpoint.json`)
- Workspace binding correctly scopes to `modules/foundups/voteballots`
- `delegate_task` is NOT imported in dry-run mode
- All WSP 97 truth fields verified:
  - `status=SIMULATED`
  - `checkpoint_state=SIMULATED`
  - `real_execution_performed=False`
  - `verification_complete=False`
  - `cabr_ready=False`
  - `payout_ready=False`
  - `request.dry_run=True`
  - `_delegate_task_fn=None`

**Test Classes**:
| Class | Assertions |
|-------|------------|
| `TestHXA4EnvironmentSafetyGate` | 2 tests |
| `TestRealHermesJobExecutorInstantiation` | 2 tests |
| `TestVoteBallotsDryRunReachesRealExecutor` | 2 tests |
| `TestVoteBallotsDelegationRequestContract` | 2 tests |
| `TestNoLiveDelegateTaskCalls` | 2 tests |
| `TestWSP97TruthTableVerification` | 1 test |

**Key Assertion**:
```python
def test_voteballots_job_reaches_real_executor_object(self):
    # Step 2: Create REAL executor (NOT mocked)
    executor = HermesJobExecutor(dry_run=True, workspace_root=self.evidence_root)
    
    # Step 3: Execute job through REAL executor
    result = executor.execute(job)
    
    assert result.status == HermesExecutionStatus.SIMULATED
    assert result.real_execution_performed is False
    assert executor._delegate_task_fn is None
```

**Verdict**: REAL OBJECT REACHED, SAFE DRY-RUN CONFIRMED

---

## 4. HXA5 Truth: External Federation Follows Internal Factory

**Artifact**: `docs/audits/openclaw_hermes/HXA5_EXTERNAL_FEDERATION_PFMALL_PAVS_AUDIT.md` (351 lines)

**What it proves**:
- pAVS MCP Server has REAL HTTP/JSON transport (MCPA8)
- 6/8 tool backends are REAL:
  - `holo_search` → S2/HoloIndex
  - `fam_emit` → FAM DAEmon
  - `pattern_recall` → PatternMemory
  - `pattern_store` → PatternMemory
  - `gemma_classify` → GemmaRAGInference
  - `qwen_plan` → QwenInferenceEngine
- 2/8 tools remain placeholder:
  - `cabr_validate` → hardcoded `score=0.85`
  - `foundup_register` → stub
- Architecture locked by WSP 103 + WSP 104
- Shell contract (postMessage) defined
- External FoundUps must wait until internal factory can generate artifacts

**Federation Order**:
```
INTERNAL FIRST: OpenClaw → Hermes trunk proof (HXA3/HXA4) ✓
THEN EXTERNAL:  pAVS → External FoundUp registration
```

**Verdict**: EXTERNAL FEDERATION BLOCKED UNTIL INTERNAL FACTORY GENERATES ARTIFACTS

---

## 5. HXA6 Truth: VoteBallots is Canonical Idea→PoC Fixture

**Artifact**: `docs/audits/openclaw_hermes/HXA6_VOTEBALLOTS_IDEA_TO_POC_LIFECYCLE_AUDIT.md` (380 lines)

**What it proves**:
- VoteBallots is the canonical test fixture for idea→PoC pipeline validation
- Manifest explicitly states `_wsp97_implementation_state: SPECIFIED_NOT_IMPLEMENTED`
- `lifecycle_stage: incubating`, `launch_readiness: discoverable_only`
- 2300+ lines of dry-run tests:
  - `test_openclaw_voteballots_dryrun_proof.py` (299 lines)
  - `test_internal_voteballot_build_poc.py` (2012 lines)
- Referenced as prerequisite in `FOUNDUP_BUILD_PLAN_CONTRACT.md` Section 2
- All required PoC artifacts present: manifest, module.json, README, INTERFACE, ROADMAP, ModLog, tests/

**Missing for PoC Completion**:
- `src/` implementation files
- FEC API integration
- Confidence scoring runtime
- Report generator
- `entry_url` deployment

**Verdict**: VOTEBALLOTS IS CANONICAL FIXTURE — READY FOR HERMES PoC GENERATION

---

## 6. HXA7 Truth: GotJunk is Second Proof Target

**Artifact**: `docs/audits/openclaw_hermes/HXA7_SECOND_PROOF_TARGET_AUDIT.md` (221 lines)

**What it proves**:
- GotJunk is the ONLY candidate with deployed `entry_url`:
  - `https://gotjunk-56566376153.us-west1.run.app/`
- WSP 15 scoring: GotJunk 96/100 vs Trade 6/100 vs VoteBallots 10/100
- GotJunk PoC Phase 1 complete: photo capture, swipe UI, geo-filtering
- Cloud Run CSP headers verified (2026-04-19)
- Autonomous deploy pipeline exists
- DE4-ready for GitHub repo creation

**Comparison**:
| Criterion | GotJunk | Trade | VoteBallots |
|-----------|---------|-------|-------------|
| Deployed entry_url | YES | NO | NO |
| Runnable artifact | YES | NO | NO |
| PoC complete | YES | NO | NO |
| Hermes prerequisites | MET | NOT MET | NOT MET |

**Verdict**: GOTJUNK IS SECOND PROOF TARGET (after VoteBallots contract validation)

---

## 7. What is Now Proven

| Proof Point | Status | Evidence |
|-------------|--------|----------|
| OpenClaw intent detection | PROVEN | HXA3 test: `_is_explicit_build_intent()` |
| FoundUpJob creation | PROVEN | HXA3 test: `dispatch_foundup()` |
| Queue → WRE Consumer | PROVEN | HXA3 test: `drain_openclaw_queue_once()` |
| WRE routing to HERMES_BUILDER | PROVEN | HXA3 test: `route_foundup_job()` |
| Hermes executor reached (mocked) | PROVEN | HXA3 test: `mock_hermes_execute.assert_called_once()` |
| Real HermesJobExecutor object reached | PROVEN | HXA4 test: `executor.execute(job)` |
| Evidence files written | PROVEN | HXA4 test: `metadata.json`, `checkpoint.json` |
| Delegation disabled safety | PROVEN | HXA4 test: `_delegate_task_fn is None` |
| WSP 97 truth fields enforced | PROVEN | Both tests assert all fields |

---

## 8. What Remains Unproven

| Gap | Impact | Remediation |
|-----|--------|-------------|
| Live `delegate_task` execution | Hermes cannot generate artifacts | Enable HERMES_DELEGATE_ENABLED=1 in controlled slice |
| VoteBallots `src/` implementation | No runnable FoundUp | HXA9: Hermes generates stubs |
| GotJunk extraction | Second proof not started | HXA10: Apply Hermes to deployed FoundUp |
| CABR real backend | External FoundUps get fake scores | MCPA10 |
| pAVS SDK publishing | External devs need raw HTTP | MCPA11 |
| Human approval gate | Not exercised in dry-run | Phase 2+ |

---

## 9. WSP 15 Next-Slice Scoring

| Slice | Impact | Risk | Effort | Dependencies | SCORE |
|-------|--------|------|--------|--------------|-------|
| **VoteBallots PoC generation** | HIGH (proves factory generates) | LOW (dry-run mode) | MEDIUM | HXA3/HXA4 ✓ | **P0** |
| GotJunk second proof | MEDIUM (proves extraction) | LOW (deployed) | MEDIUM | VoteBallots PoC | P1 |
| p.fMALL/pAVS external federation | LOW (internal first) | MEDIUM | HIGH | Internal factory working | P2 |
| CABR final backend | MEDIUM (external readiness) | LOW | MEDIUM | MCPA9 complete | P1 |
| Link Sentinel consumer hook | LOW (security layer) | LOW | LOW | None | P2 |

---

## 10. Recommended Next Implementation Slice

### **P0: HXA9_VOTEBALLOTS_POC_GENERATION_SAFE_DRYRUN_PHASE1**

**Mission**: Have Hermes generate or update VoteBallots PoC artifacts in dry-run/safe mode, still no live repo creation.

**Scope**:
1. Enable `HERMES_DELEGATE_ENABLED=1` in test harness only
2. Create `delegate_task` stub that writes to temp workspace
3. Hermes generates `src/` stub files for VoteBallots
4. Evidence: generated files written to `.hermes_evidence/hxa9_voteballots/`
5. Assert: `real_execution_performed=True` but `cabr_ready=False` (no payout claim)

**Success Criteria**:
- Hermes writes at least one `src/*.py` file for VoteBallots
- All generated files pass linter
- No GitHub repo created
- No production claims

**WSP 97 Boundaries**:
- `dry_run=False` (controlled delegation enabled)
- `real_execution_performed=True` (actually writes files)
- `cabr_ready=False` (no payout claim)
- `payout_ready=False` (no token operations)
- `verification_complete=False` (no human approval)

---

## 11. Do-Not-Touch / Support-Lane Parking List

| Item | Reason | Lane |
|------|--------|------|
| pAVS SDK publishing | External federation, internal first | SUPPORT |
| Access DAE implementation | External access gating, not factory | SUPPORT |
| Stakeholder Gate UI | Phase 2+ per entry contract | DEFERRED |
| GotJunk repo creation | Second proof, after VoteBallots | QUEUED (HXA10) |
| Trade implementation | Phase 0 constraints active | PARKED |
| CABR real backend | MCPA10 scope | SUPPORT |
| Link Sentinel hooks | Security layer, not factory | SUPPORT |

---

## 12. WSP 97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| Internal trunk proof exists | **VERIFIED** | HXA3: mocked seam test passes |
| Real Hermes executor object proof exists | **VERIFIED** | HXA4: real object test passes |
| Live delegate remains disabled | **VERIFIED** | HXA4: `_delegate_task_fn is None` |
| No repo creation yet | **VERIFIED** | No GitHub API calls in tests |
| No production readiness claim | **VERIFIED** | All tests assert `cabr_ready=False`, `payout_ready=False` |
| External federation should wait | **VERIFIED** | HXA5: "internal factory must work first" |
| GotJunk is second proof | **VERIFIED** | HXA7: only candidate with entry_url |
| VoteBallots is canonical fixture | **VERIFIED** | HXA6: 2300+ lines of tests, contract reference |

### Uncertainty Acknowledgment

| Item | Uncertainty | Mitigation |
|------|-------------|------------|
| `delegate_task` integration complexity | MEDIUM | HXA9 will prove with stub |
| VoteBallots implementation scope | LOW | Generate minimal stubs |
| GotJunk extraction scope | MEDIUM | Wait for HXA9 completion |

---

## Sources

### HXA Artifacts Verified on origin/main

| Artifact | Lines | Purpose |
|----------|-------|---------|
| `test_openclaw_voteballots_dryrun_proof.py` | 299 | HXA3: mocked Hermes seam |
| `test_hxa4_real_hermes_object_dryrun.py` | 458 | HXA4: real object dry-run |
| `HXA5_EXTERNAL_FEDERATION_PFMALL_PAVS_AUDIT.md` | 351 | HXA5: external federation |
| `HXA6_VOTEBALLOTS_IDEA_TO_POC_LIFECYCLE_AUDIT.md` | 380 | HXA6: VoteBallots lifecycle |
| `HXA7_SECOND_PROOF_TARGET_AUDIT.md` | 221 | HXA7: second proof target |

### HoloIndex Top Hit

`modules/communication/moltbot_bridge/tests/test_internal_voteballot_build_poc.py` — 2012 lines of full pipeline PoC tests

---

## WSP 97 Note

This audit synthesizes HXA3-HXA7 findings. All claims are sourced from codebase artifacts. No implementation claims are made beyond what tests prove. The recommended next slice (HXA9) stays within controlled safe boundaries: artifact generation without repo creation or payout claims.

---

*Audit performed by Worker W5 under WSP 97 truth boundaries.*

Worker W5 complete for HXA8_OPENCLAW_HERMES_FACTORY_SYNTHESIS_PHASE1.
