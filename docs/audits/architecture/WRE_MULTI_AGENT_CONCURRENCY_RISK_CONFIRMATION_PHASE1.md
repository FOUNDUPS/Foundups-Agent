# WRE Multi-Agent Concurrency Risk Confirmation -- Phase 1 (Decision-Only)

- Slice: WRE_MULTI_AGENT_CONCURRENCY_RISK_CONFIRMATION_PHASE1
- Base SHA: dc685f93400151b840e90326134d20b6a10fffc4
- Method: WSP_00 (Zen State) / WSP_50 (pre-action verification) / WSP_97 (Truth Boundary) / COTCAR
- Status: DECISION-ONLY confirmation. NO src change, NO fix, NO committed test.
- Worker-Lane: A (W9)
- Parent: docs/audits/architecture/WRE_MULTI_AGENT_EVOLUTION_AUDIT_PHASE1.md (documented these two
  races as "DOCUMENTED, NOT FIXED" and named this slice as the first execution follow-up).

---

## 1. Purpose and Scope

The merged Phase 1 evolution audit listed two active concurrency hazards in the WRE multi-agent
spine and explicitly deferred any fix. This slice CONFIRMS, against current main (base dc685f934),
whether each hazard is REAL (root cause present at verified file:line), whether it is
REACHABLE-NOW (a live bug today) or LATENT (real root cause but unreachable until in-process
multi-lane drain exists), and specs the minimal fix for each.

This slice does NOT implement any fix. It changes exactly two files: this audit document and one
dated ModLog entry. The fixes themselves are separate, named execution slices (Section 5).

All cites below were re-derived at base dc685f934 via `git show dc685f934:<path>` and grep; line
numbers were not trusted from the parent audit blindly -- they were re-verified and are quoted.

---

## 2. Race 1 -- policy_flags in-place mutation

File: modules/infrastructure/wre_core/src/hermes_job_executor.py

### (a) REAL? -- root cause confirmed at current main

`HermesJobExecutor._writeback_token_verdict` mutates the shared `job.policy_flags` object in place,
and the destructive-action guard then reads those same mutated fields.

Verified cites (re-derived at dc685f934):

- Writeback mutates in place -- hermes_job_executor.py:1302-1305:

      job.policy_flags.capability_token_checked = True
      job.policy_flags.capability_token_present = token_present
      job.policy_flags.capability_token_validated = token_valid
      job.policy_flags.capability_token_scope_authorized = scope_authorized

  Docstring states the contract explicitly -- hermes_job_executor.py:1287:

      job: Source FoundUpJob (policy_flags mutated in place).

- Writeback is called inside `execute()` BEFORE the guard -- hermes_job_executor.py:1616:

      self._writeback_token_verdict(job, token_validation_result)

- Guard is evaluated immediately after -- hermes_job_executor.py:1619:

      guard_result = self._evaluate_destructive_action_guard(job, request)

  which calls `_build_destructive_action_request` (hermes_job_executor.py:1325), which READS the
  just-mutated flags -- hermes_job_executor.py:1227-1232:

      if policy_flags is not None:
          capability_token_present_for_guard = (
              policy_flags.capability_token_checked
              and policy_flags.capability_token_present
              and policy_flags.capability_token_validated
              and policy_flags.capability_token_scope_authorized
          )

Cite reconciliation vs parent audit: parent cited writeback :1302-1305 (CONFIRMED), docstring :1287
(CONFIRMED), call :1616 (CONFIRMED), guard :1619 (CONFIRMED), guard read :1227-1232 (CONFIRMED). No
line corrections required for Race 1.

Root-cause type: shared mutable state. `FoundUpJob.policy_flags` is a single `PolicyFlags`
dataclass instance (foundup_job_contract.py:404, `field(default_factory=PolicyFlags)`). Writeback
assigns onto its attributes rather than returning a request-scoped verdict the consumer applies.

### (b) Deterministic characterization -- throwaway probe (run, NOT committed)

A throwaway probe under o:/tmp/race1_policyflags_probe.py (NOT in the repo, NOT committed)
constructed a `FoundUpJob` with a fresh `PolicyFlags` (all capability_token_* False), called
`HermesJobExecutor._writeback_token_verdict(job, result)` single-threaded with a valid
`TokenValidationResult(token_valid=True, scope_action_class_mismatch=False)`, and asserted on the
SAME job object.

Probe result (actual output):

- PART A (same-object writeback):
  - policy_flags before: (False, False, False, False)
  - policy_flags after : (True, True, True, True)
  - same policy_flags object id (no copy): True
  - MUTATION CONFIRMED: True
- PART B (one shared job object, two lanes):
  - after lane A (valid token) validated/scope: (True, True)
  - after lane B (no token)    validated/scope: (False, False)
  - CROSS-CONTAMINATION CONFIRMED (B flipped A's guard input): True
- RESULT: PRECONDITION_CONFIRMED

Interpretation: the call mutates the SAME object (no defensive copy, no request-scoped return), and
a second writeback against a shared job reference overwrites the first writeback's verdict -- i.e.
the guard input is shared state, not request-scoped. This deterministically proves the
shared-state-mutation PRECONDITION of the data race single-threaded. The data race itself (two
threads interleaving on one job) still requires real concurrency, which is assessed in (c).

### (c) REACHABLE-NOW vs LATENT -- verdict: LATENT

Verdict: LATENT (real root cause; not reachable as a data race on current main).

Evidence:

- The only non-test path that reaches the writeback is the drain path:
  `drain_openclaw_queue_dry_run` -> `drain_openclaw_queue_with_retention` -> `drain_jobs` ->
  `consume_one` -> dispatch (foundup_job_consumer.py:458 `execute_foundup_job(job)`) ->
  `HermesJobExecutor.execute` -> `_writeback_token_verdict`.
- The drain is invoked exactly once, synchronously, single-process. The single non-test caller is
  run_wre.py `cmd_drain` (run_wre.py:433-439), which calls `drain_openclaw_queue_dry_run(...)` ONCE;
  the consumer method is documented "This is a synchronous operation. No daemon loop."
  (foundup_job_consumer.py:852) and "Drain ... once in dry-run mode." (foundup_job_consumer.py:974).
- No concurrent driver exists. A repo sweep for `create_task` / `asyncio.gather` /
  `run_in_executor` / `ThreadPoolExecutor` / `ProcessPoolExecutor` / `multiprocessing` /
  `threading.Thread` across modules/infrastructure/wre_core matched 5 files (wre_monitor.py,
  src/skill_trigger.py, src/daemon_self_audit_loop.py, skillz/wre_skills_discovery.py,
  recursive_improvement/src/learning.py); NONE reference drain / FoundUpJobConsumer /
  HermesJobExecutor / _FOUNDUP_JOB_QUEUE / remove_jobs_by_id / consume_one (grep = ZERO hits).
- Within a single drain, jobs come from one queue and are distinct objects, so the same `job` is
  not shared across two writeback calls today. The cross-contamination in probe PART B was forced by
  aliasing one job to two "lanes" -- a state that no current code path produces.

This CONFIRMS the parent audit's framing for Race 1: thread-safety is incidental to
worktree-per-agent being separate processes; the race is unreachable until an in-process multi-lane
drain shares a `job` object. It is a latent root cause, not a live bug.

### (d) Trigger condition

Two (or more) in-process lanes hold a reference to the SAME `FoundUpJob` instance and call
`execute()` (hence `_writeback_token_verdict`) concurrently or interleaved, such that one lane's
writeback flips the `capability_token_*` flags the other lane's destructive guard reads between its
own writeback (1616) and its guard read (1619/1227-1232). Requires shared-job in-process
multi-lane drain (does not exist at dc685f934).

### (e) Minimal fix spec (NOT implemented)

Return the token verdict as request-scoped metadata that the consumer/guard applies, instead of
mutating `job.policy_flags` in place:

- Change `_writeback_token_verdict` to RETURN a small immutable verdict (the four
  capability_token_* booleans) rather than writing onto `job.policy_flags`.
- Have `_build_destructive_action_request` accept that request-scoped verdict (or a per-execute
  local copy of policy_flags) instead of reading `job.policy_flags` directly, so guard input is
  local to the execute() call and never shared across lanes.
- Net effect: `job` becomes read-only with respect to capability_token_* during execute(); no
  shared-state write, so no cross-lane contamination is possible by construction.

Scope note (not part of the fix's required surface, but relevant): the sibling executor
modules/foundups/agent/src/hermes_foundup_job_executor.py ALSO mutates `job.policy_flags.*` in place
(e.g. :237, :358, :363-364, :398-399). The in-place-mutation anti-pattern is systemic, not isolated
to one method; the execution slice should decide whether to converge both executors on the
request-scoped pattern. This confirmation only certifies the WRE-core `_writeback_token_verdict`
cite named by the parent audit.

### (f) Recommendation -- fix-before-multi-lane

Fix BEFORE any in-process multi-lane drain is introduced. It is latent today, so it is not an
emergency; but the parent audit's near-term roadmap correctly orders this fix BEFORE
parallelize-drain (audit Section 7 Near-Term: "Remove in-place job mutation ... (fixes the
policy_flags race)" precedes "Parallelize drain per-lane"). Closing the shared-write precondition
before concurrency exists prevents the latent race from becoming live the moment a second lane is
added. Do not parallelize the drain until this is fixed.

---

## 3. Race 2 -- queue split-authority TOCTOU

Files: modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py (queue + exports),
modules/infrastructure/wre_core/src/foundup_job_consumer.py (consumer).

### (a) REAL? -- root cause confirmed at current main

OpenClaw owns the shared global queue AND exports a remove primitive; the WRE consumer reads,
drains, then removes against that shared global in three non-atomic calls, holding no lock.

Verified cites (re-derived at dc685f934):

- Shared global queue -- openclaw_foundup_orchestrator.py:39:

      _FOUNDUP_JOB_QUEUE: List[FoundUpJob] = []

- `get_job_queue()` returns the LIVE module global (not a copy) --
  openclaw_foundup_orchestrator.py:230-232:

      def get_job_queue() -> List[FoundUpJob]:
          """Return the in-memory job queue (for testing)."""
          return _FOUNDUP_JOB_QUEUE

- `remove_jobs_by_id` exported by the orchestrator AND it REBINDS the global to a new list --
  openclaw_foundup_orchestrator.py:240, with the rebind at :252-255:

      global _FOUNDUP_JOB_QUEUE
      original_count = len(_FOUNDUP_JOB_QUEUE)
      job_id_set = set(job_ids)
      _FOUNDUP_JOB_QUEUE = [j for j in _FOUNDUP_JOB_QUEUE if j.job_id not in job_id_set]

- Consumer performs read -> drain -> remove as three non-atomic calls, no lock --
  foundup_job_consumer.py (method `drain_openclaw_queue_with_retention`, foundup_job_consumer.py:858):
  - :897  `queue = get_job_queue()`            (read; captures live reference)
  - :914  `results = self.drain_jobs(queue)`    (process)
  - :930  `removed = remove_jobs_by_id(cleared_job_ids)` (remove)

  No `threading` / `asyncio` / lock primitive appears anywhere in foundup_job_consumer.py or
  openclaw_foundup_orchestrator.py guarding this sequence (grep = ZERO).

Cite reconciliation vs parent audit: parent cited remove export :240 (CONFIRMED), consumer
:897/:914/:930 (ALL CONFIRMED exactly), global :39 (CONFIRMED). No line corrections required for
Race 2.

Split-authority + rebind detail (beyond what the parent audit stated): because `remove_jobs_by_id`
REBINDS `_FOUNDUP_JOB_QUEUE` to a fresh list (:255) rather than mutating in place, a reference held
via `get_job_queue()` at :897 becomes STALE after any concurrent remove -- so a second drainer's
appended jobs (orchestrator append at :976 targets the rebound name) and the first drainer's removal
operate on divergent list objects. This is a second, sharper hazard dimension layered on the
classic TOCTOU.

### (b) Deterministic characterization

`get_job_queue()` is a bare `return _FOUNDUP_JOB_QUEUE` (no copy), so it hands out a live reference
to the module global -- confirmed by direct read of :230-232. The read (:897) -> drain (:914) ->
remove (:930) sequence holds no lock -- confirmed by the absence of any lock/`with`-guard around
the sequence and the method docstring describing it as a plain synchronous operation
(foundup_job_consumer.py:852). No isolation probe is required; the non-atomicity is structural and
visible in the quoted code.

### (c) REACHABLE-NOW vs LATENT -- verdict: LATENT

Verdict: LATENT (real root cause; not reachable as a TOCTOU on current main).

Evidence: identical concurrency-presence finding as Race 1 -- there is exactly one synchronous,
single-process, single-drain caller (run_wre.py:433-439 `cmd_drain` -> `drain_openclaw_queue_dry_run`
ONCE), and no concurrent driver of the drain path exists anywhere in the repo (the 5
concurrency-primitive files in wre_core do not touch the queue/drain/consumer/executor symbols;
grep = ZERO). A TOCTOU needs two interleaving drains against the shared queue; with a single drain
there is no second actor to interleave. Real root cause, currently unreachable.

This CONFIRMS the parent audit's framing: queue safety is accidental (single-drain, dry-run,
process isolation), not guaranteed.

### (d) Trigger condition

Two or more drains (in-process, e.g. per-lane consumers) run `get_job_queue() -> drain_jobs ->
remove_jobs_by_id` against the one shared `_FOUNDUP_JOB_QUEUE` without a shared lock, OR OpenClaw
appends to the queue while a drain is mid-sequence. Interleaving causes: (i) classic TOCTOU
(a job classified for removal by one drainer is removed by the other, or removed twice / lost), and
(ii) stale-reference divergence because `remove_jobs_by_id` rebinds the global to a new list. Requires
in-process concurrent drain or concurrent append-during-drain (neither exists at dc685f934).

### (e) Minimal fix spec (NOT implemented)

A single QueueManager owns append + remove under one lock, with an atomic classify-remove, and
OpenClaw becomes PUSH-only:

- Promote `_FOUNDUP_JOB_QUEUE` into an explicit QueueManager object that owns the list and a lock;
  all append/read/remove go through it under the lock (mutate in place; never rebind the name).
- Provide an atomic classify-and-remove operation so the read -> drain-decision -> remove sequence
  is performed while holding the lock (or as a single compare-and-remove keyed on job_id), closing
  the TOCTOU window.
- Consolidate mutation authority: OpenClaw PUSH only (append at orchestrator); the WRE consumer owns
  POP/remove. Remove `remove_jobs_by_id` / `clear_job_queue` as orchestrator-side exports so there
  is one removal authority, not two.

### (f) Recommendation -- fix-before-multi-lane

Fix BEFORE parallelizing the drain (before any 2nd in-process lane). The parent audit's Immediate
Foundation roadmap places "promote `_FOUNDUP_JOB_QUEUE` into an explicit QueueManager ... with
atomic classify-remove (closes the TOCTOU)" and "OpenClaw PUSH only" BEFORE concurrency exists. This
confirmation agrees: build the single-authority locked queue before a second drainer is introduced;
do not rely on the current single-drain accident.

---

## 4. Current Concurrency Presence (evidence for the REACHABLE-NOW vs LATENT verdict)

What runs the drain/execute path today:

- Single non-test entrypoint: run_wre.py `cmd_drain` (run_wre.py:433-439) calls
  `drain_openclaw_queue_dry_run(clear=...)` exactly ONCE. The CLI dispatch is a single
  `asyncio.run(commands["drain"](args))` (run_wre.py:557) of a single coroutine -- there is no
  `gather`, `create_task`, thread pool, or process pool over the drain.
- The drain method is explicitly synchronous and single-shot: foundup_job_consumer.py:852 ("This is
  a synchronous operation. No daemon loop.") and the module wrapper docstring
  (foundup_job_consumer.py:974, "Drain ... once in dry-run mode."), dry_run=True always
  (foundup_job_consumer.py:1002).
- Concurrency-primitive sweep (create_task / asyncio.gather / run_in_executor / ThreadPoolExecutor /
  ProcessPoolExecutor / multiprocessing / threading.Thread) over modules/infrastructure/wre_core
  returned 5 files, NONE of which reference drain / FoundUpJobConsumer / HermesJobExecutor /
  _FOUNDUP_JOB_QUEUE / remove_jobs_by_id / consume_one (grep = ZERO). The moltbot_bridge src files
  that mention `.execute(` (openclaw_execution_routes.py:197, openclaw_skill_evolution.py SQL
  cursor) are unrelated to HermesJobExecutor.execute and are not concurrent.

Conclusion: nothing runs the drain/execute path concurrently on current main. Both races are LATENT
(real root cause, unreachable until an in-process multi-lane drain or concurrent append-during-drain
exists). The "accidental" thread-safety claimed by the parent audit is confirmed: safety is
incidental to single-drain, dry-run, worktree-per-agent process isolation -- not a guarantee.

---

## 5. Recommendation Summary and Proposed Execution Slices

Both races are REAL and CONFIRMED at dc685f934; both are LATENT today. Recommendation for each:
fix-before-multi-lane (not an emergency, but a hard precondition for parallelizing the drain).

Ordering (consistent with the parent audit's roadmap):

1. WRE_POLICY_FLAGS_RACE_FIX_PHASE1 -- implement Race 1 minimal fix (return token verdict as
   request-scoped metadata; stop mutating `job.policy_flags` in place). FIRST.
2. WRE_QUEUE_OWNERSHIP_CONSOLIDATION_PHASE1 -- implement Race 2 minimal fix (single locked
   QueueManager owning append+remove with atomic classify-remove; OpenClaw PUSH-only; drop
   orchestrator-side remove/clear exports). SECOND.

Both MUST land before any slice that introduces a second in-process drain lane
(parallelize-drain-per-lane). Until then, the drain remains single-shot, synchronous, dry-run, and
the races stay unreachable. No fix is performed in THIS slice.

---

## 6. WSP_97 Truth Boundary Checklist

Declared rows: 9.

| # | Truth Boundary Checklist Item | Status | Evidence |
| 1 | DECISION_ONLY_NO_SRC_NO_FIX | YES | Two files changed (this doc + one ModLog entry); zero .py edited; no committed test; `git diff --name-only` against base lists exactly the two in-scope files. |
| 2 | RACE1_ROOTCAUSE_CONFIRMED_AT_DC685F934 | YES | hermes_job_executor.py in-place mutation :1302-1305 (docstring :1287), called :1616, guard read :1227-1232 via :1619 -- all re-derived at dc685f934 and quoted in Section 2(a). |
| 3 | RACE2_ROOTCAUSE_CONFIRMED_AT_DC685F934 | YES | openclaw_foundup_orchestrator.py global :39, get_job_queue live-return :230-232, remove_jobs_by_id export+rebind :240/:252-255; consumer non-atomic :897/:914/:930 -- re-derived at dc685f934 and quoted in Section 3(a). |
| 4 | REACHABILITY_VERDICT_EVIDENCE_BASED | YES | Both LATENT: single synchronous single-drain caller run_wre.py:433-439/:557; consumer synchronous (foundup_job_consumer.py:852/:974); concurrency-primitive sweep over wre_core = 5 files, ZERO touch the drain/queue/executor symbols (Section 4). |
| 5 | CHARACTERIZATION_PROBE_RUN_NOT_COMMITTED | YES | o:/tmp/race1_policyflags_probe.py (outside repo, NOT staged) run; output PART A MUTATION CONFIRMED True / same-object True, PART B CROSS-CONTAMINATION True, RESULT PRECONDITION_CONFIRMED (Section 2(b)). |
| 6 | MINIMAL_FIX_SPECCED_NOT_IMPLEMENTED | YES | Race 1 fix (request-scoped verdict) Section 2(e); Race 2 fix (single locked QueueManager + PUSH-only) Section 3(e); both spec-only, no code changed. |
| 7 | NO_NAVIGATION_OR_HOLOINDEX_ARTIFACTS | YES | NAVIGATION.py, holo_index/docs/AGENT_CLI_CATALOG.md, holo_index/docs/command_rolodex.json, .claude/** untouched; diff is exactly the two in-scope files. |
| 8 | ASCII_CLEAN | YES | Byte-check of this doc reports NON_ASCII 0. |
| 9 | FILE_SCOPE_EXACTLY_TWO | YES | NEW docs/audits/architecture/WRE_MULTI_AGENT_CONCURRENCY_RISK_CONFIRMATION_PHASE1.md + EDIT ModLog.md (root); no other path staged. |
