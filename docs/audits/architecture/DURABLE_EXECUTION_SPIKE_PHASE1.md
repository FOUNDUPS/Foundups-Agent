# DURABLE_EXECUTION_SPIKE_PHASE1

**Slice:** DURABLE_EXECUTION_SPIKE_PHASE1
**Worker-Lane:** W9
**Author:** 0102 (WSP_00 zen state, FOLLOW-WSP, WSP_97 Truth Boundary + CoT/CoR)
**Type:** READ-ONLY DESIGN SPIKE. One design memo. No code, no dependency, no orchestrator.

---

## 1. Mission and Scope (design-only)

Evaluate whether to pilot a durable checkpoint/resume pattern for the autonomous FoundUp build
cycle - targeting the `OpenClawSupervisor.run_cycle()` in-memory-state gap (crash mid-cycle =
lost state, no resume) - and whether to do it with the #766-named DBOS dependency OR by building
on existing repo primitives (the load-bearing Occam comparison). This is a design recommendation,
not an implementation: NO dependency installed, NO code/test, NO second orchestrator, NO vendoring.
NO_OVERCLAIM: this memo is a design evaluation, not a working durable loop.

---

## 2. Predecessor #766 + Secured-Base Context

#766 CODE_PUPPY_FOUNDUPS_ARCHITECTURE_AUDIT (merged `b69ec0659`) ruled
`CREATE_DURABLE_EXECUTION_SPIKE`: pilot durable checkpoint/resume WITHOUT vendoring Code Puppy and
WITHOUT a second orchestrator, naming DBOS (pydantic-ai `DBOSAgent` + `SetWorkflowID`) as the
candidate. This spike builds on the secured base (cited, not re-audited): #762 headless
no-live-launch default, #761 Hermes import path, #768 AI Overseer typed shell=False exec boundary,
#763 FoundUp coverage map, #747 genesis-gate write-back-before-guard, #752 anti-duplication ruling
(OpenClaw already owns the loop - fold in, do not add a 2nd layer).

---

## 3. FOLLOW-WSP Evidence (HoloIndex + existing-primitive inventory)

**HoloIndex first (discovery, not proof).** Seven mandated queries; every hit USED was confirmed
by a direct file read (Addendum A).

| Query | Top hits | Signal | Used for |
|-------|----------|--------|----------|
| OpenClawSupervisor run_cycle checkpoint resume durable execution | agent_market/ARCHITECTURE.md, openclaw_dae.py, fam_adapter.py | FALSE_LEAD (missed the supervisor) | direct read of `openclaw_supervisor.py:161` instead |
| FAM daemon dual write SQLite JSONL deterministic id | `dae_daemon/event_store.py`, voice_command_ingestion | MEDIUM | located event_store; direct read of `fam_daemon.py` + `event_store.py` |
| WSP 56 artifact state coherence checkpoint resume | wsp_compliance_checker.py, action_pattern_learner.py | LOW (missed WSP_56) | direct read of `WSP_56_...md` |
| PatternMemory SQLite outcome store replay | `pattern_memory.py` | HIGH | direct read of `pattern_memory.py` |
| FoundUpJob idempotency status resume | agent_market/INTERFACE.md, ai_overseer.py | MEDIUM (missed contract) | direct read of `foundup_job_contract.py` |
| pydantic ai DBOSAgent SetWorkflowID durable execution | vision_executor.py, in_memory.py | FALSE_LEAD | confirms DBOS not in repo; dependency files read directly |
| DBOS transact python SQLite workflow resume | vision_executor.py, models.py | FALSE_LEAD | same |

**`HOLOINDEX_LOW_SIGNAL`** for the architecture specifics: it surfaced `pattern_memory.py` and
`event_store.py` but missed `openclaw_supervisor.py`, `foundup_job_contract.py`, `WSP_56`, and
`fam_daemon.py`; the two DBOS queries drifted to unrelated files (consistent with DBOS being
absent). **Fallback:** `rg` + direct file reads (recorded per-section below); every architecture
claim in this memo is anchored to a direct read with file:line.

---

## 4. Gap Map (Q1 - direct read of `openclaw_supervisor.py`)

`run_cycle` (def `openclaw_supervisor.py:161`) is a single in-process pass. State is held in
**local in-memory variables** `observation / plan / action_result / verify` (:178-181):

| Step | Code | State durability |
|------|------|------------------|
| BOOT/PREFLIGHT | :168-172 (`self._bootstrapped` flag) | in-memory flag, lost on crash |
| OBSERVE | `observation = self._observe()` :184 | in-memory dict |
| TRIAGE | `triage = self._triage(observation)` :187 | in-memory |
| PLAN | `plan = self._plan(triage, observation)` :239 | in-memory |
| **EXECUTE** | `action_result = self._execute(plan)` :242 | **in-memory; the crash-loss surface** |
| VERIFY | `verify = self._verify(plan, action_result)` :245 | in-memory |
| REMEMBER | `self._remember(...)` :249 / :274 | persists OUTCOME **after** the fact |

`_execute` (def :706) dispatches four real actions - `start_openclaw` -> `broker.start_dae` (:724-726);
`execute_autonomous_task` -> `db.assign_autonomous_task` + in-process `execute_task(...)` (:745-761);
`execute_maintenance_task` -> `execute_task(...)` (:795-814); `execute_self_audit_fix` ->
`_apply_policy_fix` (:850-855). `_remember` (def :1039) runs **after** `_execute`/`_verify`
(ordering at :242/:245/:249/:274) and only stores a post-hoc `SkillOutcome` to PatternMemory
(:1090) when `action_result.get("ok")`.

**Precise crash-loss surface:** a crash between PLAN (:239) and REMEMBER (:274) loses the in-flight
`plan` + partial `action_result`; on restart `run_cycle` begins a FRESH cycle (re-OBSERVE,
re-PLAN) - there is **no read-back-and-continue-from-step** logic anywhere. `self.last_cycle`
(:277-283), `self._bootstrapped`, `self.metrics`, `self.fix_attempts`, `self._restart_attempts`
are all in-memory, lost on crash.

**Where resume actually matters:** the long-running, multi-step actions inside `_execute`
(`execute_task` for a real FoundUp build). TODAY these are short (maintenance/self-audit) and the
FoundUp->Hermes build path is dry-run/separate (#762), so loss is small; **resume becomes critical
when real long-running FoundUp builds are wired through `run_cycle`** (future). The gap is real but
the resume-critical surface is not yet live.

---

## 5. Existing-Primitives Assessment (Q2 - classified by direct read)

| Primitive | File:line | Class | Why (direct evidence) |
|-----------|-----------|-------|------------------------|
| FAM DAEmon dual-write (+ `event_store.py`) | `fam_daemon.py:405` (`write`), `:447-452` (jsonl+sqlite), `:119-122` (det. id), `:325` (`dedupe_key UNIQUE`) | **EVENT_LOG_ONLY** | Writes happen AFTER the action (`DAEMON_STOPPED`/`task_state_changed`/`payout_triggered` are past-tense facts). "Replay-safe" = idempotent re-emission via `dedupe_key`, NOT resume. No in-flight step table, no checkpoint/restore API, no read-back-and-continue. CAVEAT: jsonl write (:422) + sqlite commit (:425) is **non-atomic** (no fsync/cross-store txn) - a crash between diverges them; `verify_parity()` (:570) exists to DETECT this. |
| PatternMemory | `pattern_memory.py:342-365` (`store_outcome` INSERT+commit), fields `success`/`pattern_fidelity`/`failed_at_step` (:47-52) | **EVENT_LOG_ONLY** | Stores terminal post-execution OUTCOMES for learning. `failed_at_step` is an epitaph on a finished run, not a resume bookmark. All recall methods (:496/:529/:586) read for learning/ranking, never continuation. No `step_state`/`resume_from`/`pending_steps`. |
| FoundUpJob contract | `foundup_job_contract.py:85-104` (`JobStatus`), `:566-575` (`resume()`), `:372-376`+`:702-715` (`idempotency_key`) | **STATE_STORE_ONLY** | Has the SHAPE of resume (status state machine + `resume()` + `idempotency_key`) but `resume()` only flips status to RUNNING (no step pointer, no skip-completed, no destructive-step guard); `idempotency_key` is assigned/serialized only - **no read-back/dedup/reject consumer** in the contract. No step-index field. |
| WSP 56 Artifact State Coherence | `WSP_56_...md:3,11,32-33` | **NOT_APPLICABLE** | Defines artifact IDENTITY coherence across Knowledge/Scaffolding/Agentic state **layers/directories** (read-and-compare; raise `CoherenceViolation`). "State" = Three-State Architecture, not in-flight workflow state. No persisted step state, no resume. (Correction: #766 framed WSP 56 as the closest protocol; direct read shows it is not applicable to the durability axis.) |

**Answer to Q2:** NONE of the existing primitives is `CHECKPOINT_CAPABLE` or `RESUME_CAPABLE`
today. BUT the durable **substrate** exists: FAM crash-recoverable dual-write + deterministic IDs +
semantic dedupe keys, and a FoundUpJob status state machine + `idempotency_key` (shape present,
consumer missing). A checkpoint/resume layer CAN be built on these **without a new dependency**
(see Section 9-10), provided (a) the FAM non-atomic dual-write is made write-ahead/atomic for the
checkpoint record, and (b) the `idempotency_key` gets its read-back consumer.

---

## 6. DBOS Evaluation + Dependency Cost (Q3)

**What DBOS adds** (UNVERIFIED_EXTERNAL_DETAIL - per official pydantic-ai/DBOS docs, not local
code; no DBOS source exists in this repo to read): the pydantic-ai `DBOSAgent` wrapper +
`SetWorkflowID` provide AUTOMATIC, decorator-driven step-level durability - each workflow step is
transactionally checkpointed to a backing store (SQLite default, Postgres optional) so an
interrupted workflow RESUMES from the last completed step on restart, with exactly-once step
semantics. This is genuinely more than the existing primitives give (which is durable logging +
idempotent writes, not automatic step replay).

**Dependency cost (verified LOCALLY):**
- `pydantic-ai`: **NOT_PRESENT_LOCALLY** (0 matches across `requirements.txt`,
  `holo_index/requirements.txt`, `WSP_agentic/requirements.txt`, `foundups-mcp-p1/requirements.txt`;
  no `pyproject.toml` exists).
- `dbos` / `dbos-transact-py`: **NOT_PRESENT_LOCALLY** (0 matches).
- Even base `pydantic` is **not pinned** in any requirements file.

So DBOS is a **net-new dependency tree** (pydantic-ai -> pydantic -> dbos-transact + its runtime),
not an incremental add. Operational cost: SQLite default is in-process (acceptable), but
production durability typically wants Postgres (a new service/footprint). Against the repo's WSP 84
(code-reuse) and no-accidental-deps culture (the prior web3.py/lockfile pain), adding a heavyweight
agent-framework dependency to get step durability is a significant, deliberate cost - especially
while the resume-critical surface (Section 4) is not yet live.

---

## 7. Resume Contract + Safety (Q4 - the security-continuity check)

A durable/replayable build cycle is a NEW way to re-run steps, so the resume design MUST preserve
the secured boundaries. Direct-read locations:

- **#747 genesis gate**: `validate_genesis_envelope` at `openclaw_foundup_orchestrator.py:404`.
- **#768 typed exec boundary**: `execute_fix` at `modules/ai_intelligence/ai_overseer/src/autofix_executor.py:221` (rejects before exec; shell=False).
- **#762 no-live-launch default**: `os.environ.setdefault("OPENCLAW_SUPERVISOR_ALLOW_RESTART","0")` at `main.py:1362` (read by supervisor `__init__` at `openclaw_supervisor.py:109`).

**Today's safety is structural statelessness:** because nothing records that a gate was passed,
every restart re-enters all three gated. The resume design must NOT regress this. Contract:

1. **Checkpoint definition:** a durable, idempotent record `{cycle_id, job_id, step_id, status,
   idempotency_key}` of "step completed" - written **before** marking a step done, via an
   ATOMIC store (fix FAM's non-atomic dual-write, or use the SQLite store-of-record with fsync).
   NO secrets in the checkpoint (mirror #768 `redact_sensitive`): no tokens, OAuth codes/URLs,
   credentials, or raw env - only IDs/status/timestamps.
2. **Gated re-entry, not pre-clearance (CRITICAL):** a resumed step re-enters #747/#768/#762 gates.
   The checkpoint says "skip the already-done WORK," it does NOT mean "the gate was pre-passed."
   Any NEW action a resumed cycle takes must re-pass `validate_genesis_envelope` / `execute_fix`
   allowlist / the no-live-launch default. Resume re-enters gated.
3. **Replay-safe vs replay-forbidden:**
   - Replay-SAFE (idempotent): OBSERVE/TRIAGE/PLAN/VERIFY (pure/recomputable), dry-run steps,
     and any step guarded by the FoundUpJob `idempotency_key` consumer (duplicate -> rejected).
   - Replay-FORBIDDEN (destructive / D3+): real Hermes build, repo writes, credential rotation.
     These must NOT auto-re-run on resume; the `idempotency_key` consumer marks them terminal and
     a resumed cycle re-enters the gate rather than re-firing the destructive action.
4. **No-secret checkpoints:** enforced by reusing the #768 redaction helper on any captured text
   stored in a checkpoint/evidence record.

---

## 8. No-Second-Layer Fit (Q5)

Per #752, durable execution folds INTO the existing loop, not a parallel orchestrator:
- **Cycle-level checkpoint/resume** is owned by `OpenClawSupervisor.run_cycle` (`:161`) - it
  already drives the state machine and calls `_remember` (`:1039`); the checkpoint write is a thin
  wrapper around the existing transitions (a "step-started" write before `_execute`, completing the
  "step-completed" record `_remember` already conceptually does post-hoc).
- **Job-level resume** is owned by the existing `FoundUpJob` lifecycle + consumer: wire the
  `idempotency_key` read-back consumer (currently absent) so a re-queued job re-enters at the
  correct status without re-running completed/destructive steps.
- **Durable store** reuses FAM dual-write / the SQLite store-of-record - no new store, no new
  orchestrator class. This is an extension of owned components, not a 2nd layer.

---

## 9. Verdict + Rationale (Q6)

**VERDICT: BUILD_ON_EXISTING_PRIMITIVES** (DBOS DEFERRED; HYBRID only as fallback).

Rationale:
- The repo already owns the durable **substrate** (FAM dual-write + deterministic IDs + dedupe;
  FoundUpJob status + `idempotency_key` shape). The missing piece is a thin checkpoint-event + an
  `idempotency_key` consumer + a gated resume reader - all buildable on existing components,
  folded into the owning loop (Section 8), no new dependency.
- DBOS is a **net-new heavyweight dependency tree** (pydantic-ai + pydantic + dbos-transact; none
  present locally, Section 6) against WSP 84 / no-accidental-deps culture. Its automatic step
  durability is real value, but not worth that dependency cost while the resume-critical surface
  (long-running real builds through `run_cycle`) is not yet live (Section 4).
- Honest caveat: BUILD_ON_EXISTING is MORE implementation code than DBOS's decorators, and FAM's
  non-atomic dual-write must be hardened for the checkpoint to be crash-safe. If Phase-2 proves the
  hand-built transactional resume semantics intractable, re-open DBOS as a **HYBRID** (DBOS for the
  durable workflow engine only) under its own dependency gate - this verdict does not foreclose it.
- Not DEFER-entirely: the substrate + the future need justify piloting the thin layer now (Phase-2),
  but behind a gate.

---

## 10. Recommended Phase-2 Shape + Dependency-Gate Note

**Phase-2 slice: `DURABLE_EXECUTION_IMPL_PHASE2`** (gated, separate). Smallest pilot:
1. A `step_checkpoint` record (cycle_id, job_id, step_id, status, idempotency_key, ts) on an
   ATOMIC SQLite store-of-record (harden FAM dual-write OR single-store + fsync); **no secrets**.
2. A checkpoint write before `_execute` and on step completion, inside `run_cycle` (owned loop).
3. The FoundUpJob `idempotency_key` read-back consumer (dedup/reject duplicate; resume-from-status).
4. A resume reader that, on restart, reads the last completed step and re-enters `run_cycle`
   **gated** (re-passes #747/#768/#762), skipping already-completed non-destructive work and
   refusing to auto-re-run destructive/D3+ steps.
5. A characterization test: kill mid-`_execute`, restart, assert the destructive step is NOT
   re-run and the gates are re-entered.

**Dependency-gate note:** Phase-2 as scoped adds NO dependency (stdlib sqlite3 + existing FAM). If
a future evaluation chooses the DBOS/HYBRID path, that dependency addition is its OWN gated
decision (a separate slice + W10 gate), never folded into an implementation slice silently.

---

## 11. Internal Review Verdict

**READY.** Design-only: no code, no dependency installed, no orchestrator, no vendoring. The gap
map, all four existing-primitive classifications, the DBOS dependency check, and the secured-
boundary locations are each anchored to a DIRECT read with file:line (HoloIndex used as discovery
only; LOW_SIGNAL + rg fallback recorded). The resume contract preserves #747/#768/#762 via gated
re-entry and forbids no-secret-checkpoint regression. Verdict (BUILD_ON_EXISTING) is justified
against the Occam alternative with the dependency cost verified locally and is not a foregone DBOS
conclusion. NO_OVERCLAIM: this is a design memo, not a working durable loop.

---

## 12. WSP_97 Truth Boundary Checklist

Declared items: 19 - Rows: 19 - All YES.

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | DESIGN_ONLY_NO_CODE | YES | One memo; no `.py`/test changed |
| 2 | NO_DEPENDENCY_INSTALLED | YES | No install; dependency evaluated on paper (Sec 6) |
| 3 | NO_NEW_ORCHESTRATOR | YES | Sec 8 folds into `run_cycle`/FoundUpJob; no new orchestrator |
| 4 | NO_VENDORING | YES | Code Puppy not vendored; no vendor/ change |
| 5 | EXISTING_PRIMITIVES_EVALUATED | YES | Sec 5 table (FAM/PatternMemory/FoundUpJob/WSP56) |
| 6 | RESUME_SAFETY_RESPECTS_GATES | YES | Sec 7: gated re-entry of #747 (orch:404) / #768 (autofix:221) / #762 (main:1362) |
| 7 | NO_SECRET_IN_CHECKPOINT | YES | Sec 7.1/7.4: reuse #768 redaction; IDs/status only |
| 8 | CITES_PR_766 | YES | Sec 2 (mandate `b69ec0659`) |
| 9 | CURRENT_MAIN_LINE_NUMBERS_REVERIFIED | YES | Re-verified on `4dd29761c`: supervisor:161/242/706/1039/1090, fam:405, orch:404, main:1362 |
| 10 | NO_CABR_READY | YES | No CABR scoring/activation |
| 11 | NO_PAYOUT_READY | YES | No payout |
| 12 | NO_DAO_ACTIVATION | YES | No DAO activation |
| 13 | HOLOINDEX_USED_AS_DISCOVERY_NOT_PROOF | YES | Sec 3 table; every hit confirmed by direct read |
| 14 | HOLOINDEX_LOW_SIGNAL_FALLBACK_RECORDED_IF_APPLICABLE | YES | Sec 3: HOLOINDEX_LOW_SIGNAL + rg/direct-read fallback |
| 15 | EVERY_ARCHITECTURE_CLAIM_HAS_DIRECT_EVIDENCE | YES | All Sec 4-8 claims carry file:line |
| 16 | NO_RUNTIME_TOPOLOGY_INFERRED_FROM_SEARCH_RESULTS | YES | Gap map (Sec 4) from direct read of `openclaw_supervisor.py`, not search |
| 17 | EXISTING_PRIMITIVES_CLASSIFIED_BY_DIRECT_READ | YES | Sec 5 enum classes each cite source lines |
| 18 | DEPENDENCY_PRESENCE_VERIFIED_LOCALLY | YES | Sec 6: 0 matches in all requirements files; NOT_PRESENT_LOCALLY |
| 19 | NO_OVERCLAIM_SPIKE_IS_DESIGN_MEMO | YES | Sec 1/11 explicit; no working durable loop claimed |

**WSP 97 Truth Boundary Checklist: 19/19 YES.**

---

*Authored by 0102 (Worker-Lane W9). Read-only design spike. Existing primitives (FAM/PatternMemory
= EVENT_LOG_ONLY, FoundUpJob = STATE_STORE_ONLY, WSP56 = NOT_APPLICABLE) are the durable substrate
but none is resume-capable today; a thin checkpoint/resume layer can be built on them with no new
dependency. Verdict: BUILD_ON_EXISTING_PRIMITIVES; DBOS deferred (net-new heavy dep). Resume design
preserves the #747/#768/#762 gates via gated re-entry and no-secret checkpoints.*
