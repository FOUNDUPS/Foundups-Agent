# HXA Persistent-Queue PolicyFlags Trip-Wire Audit (Phase 1)

**Slice:** `HXA_PERSISTENT_QUEUE_POLICYFLAGS_TRIPWIRE_AUDIT_PHASE1`
**Worker-Lane:** W6 · **Author:** 0102 (WSP_00 zen state, WSP_97 Truth Boundary discipline)
**Type:** READ-ONLY verification audit. No code, tests, config, queue, or JSONL mutation.
**Base:** `origin/main` @ `87edcd779` (after #747).
**Method:** multi-modal sweep (from_dict callers / queue lifecycle / rehydration modalities / post-deser
overwrite) → classification → an independent **completeness critic** that re-grepped for missed modalities.

---

## 1. Mission and Scope

Defense verification (not exploit prevention — #747 already closed the live seam): confirm that **no
persisted, cross-process, API, JSONL, DR, or replay path rehydrates `FoundUpJob` through `from_dict()`
into WRE execution** in a way that could bypass the #747 sanitization chokepoint or re-introduce
caller-asserted gate/token flags before the destructive-action guard reads them.

---

## 2. Predecessor Citations

| PR | Slice | Relationship |
|----|-------|--------------|
| #744 | `HXA26_HXA27_DEFENSE_PRIMITIVES_REDUNDANCY_AUDIT_PHASE1` (addendum) | First surfaced the PolicyFlags seam |
| #746 | `HXA_POLICYFLAGS_WRITEBACK_ENFORCEMENT_AUDIT_PHASE1` | Classified it `GAP_CONFIRMED_BOUNDED`; named this trip-wire |
| #747 | `HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1` | Sanitize-on-deserialize + verdict write-back (the chokepoint this audit verifies) |

---

## 3. `FoundUpJob.from_dict()` Caller Inventory

**Production caller count: 0** (verified post-#747 @ `87edcd779`).

- Every non-internal `FoundUpJob.from_dict` / `PolicyFlags.from_dict` invocation is under `/tests/`
  (test_foundup_job_contract.py ×6, test_hxa24:289, test_hxa_policyflags_writeback_remediation.py:227,
  plus PolicyFlags.from_dict in the contract tests).
- Internal definitions/self-coercion only (excluded): `foundup_job_contract.py:284` (`PolicyFlags.from_dict`
  def — the sanitization chokepoint), `:461` (`__post_init__` dict-coercion), `:641/662` (`FoundUpJob.from_dict`
  def + its body call to `PolicyFlags.from_dict`).
- **Reflective dispatch checked:** `openclaw_foundup_orchestrator.py:465` `envelope_class.from_dict(...)`
  resolves via `_get_envelope_class()` to **`FoundUpGenesisEnvelope`** — a *different* class, no `policy_flags`.
  `vulnerability_scan_policy.py` / `proof_of_compute_receipt.py` `from_dict` are unrelated classes.
- **Binary deserialization checked** (critic): zero `pickle`/`marshal`/`shelve`/`dill`/`joblib` hits in
  job-handling modules; no job-class registry / dispatch-by-name.

---

## 4. `_FOUNDUP_JOB_QUEUE` Lifecycle Map

**In-memory only; no serialization hop.**

| Stage | Site | Note |
|-------|------|------|
| Declaration | `openclaw_foundup_orchestrator.py:39` | `_FOUNDUP_JOB_QUEUE: List[FoundUpJob] = []` — process-local list; docstring `:40` admits "In-memory job queue for testing. Production will use persistent queue." (**unimplemented**) |
| Enqueue (only site) | `:976` `_FOUNDUP_JOB_QUEUE.append(job)` | `job` built `:957` via `create_job(...)` — a **live** object, never `from_dict` |
| Drain | `foundup_job_consumer.py:705` `get_job_queue()` → `:722` `drain_jobs` → `consume_one` | returns the live list **by reference**; live objects only |
| Production drain entry | `run_wre.py:436-439` `drain_openclaw_queue_dry_run(...)` | forces `dry_run=True` |

A targeted grep of orchestrator+consumer for `json.dump | .jsonl | open( | write_text | sqlite | to_json |
persist` returned **zero** hits. Jobs traverse `create_job → append → get_job_queue (by ref) → drain →
consume_one → route_foundup_job → execute_foundup_job` entirely as live objects — **no `to_dict()`→`from_dict()`
hop between enqueue and execute.** (Consequence: the queue does not survive a process restart and is not shared
across processes — a separate `run_wre` drain process sees its own empty module-global.)

---

## 5. Persisted / Cross-Process Queue Search Results

No persisted or cross-process queue exists. The only job queue is the in-memory list (§4). The persistent
queue is documented future work (`orchestrator.py:40`), not implemented. `openclaw_memory_queries.py:377`
reads an `openclaw_native_execution_queue_status.json` **status** file field-by-field (`item.get('title')`/
`('priority')`) — it never calls `FoundUpJob.from_dict` and never materializes a typed job.

---

## 6. JSONL / DR / Replay Rehydration Search Results

**`anyFoundUpJobRehydrationIntoExecution = False`** across all 8 sweep modalities + 8 critic-extended modalities:

| Modality | Result |
|----------|--------|
| FAM daemon JSONL/SQLite | Stores **only `FAMEvent`** (`fam_daemon.py`); **zero `FoundUpJob` references** in `modules/foundups/agent_market/**` |
| Idempotency store | `idempotency_key` is a generated `sha256` string at `create_job`; **no store rehydrates a job from it** |
| JobStatus / job persistence | `FoundUpJob.to_dict/from_dict` exist but `from_dict` callers are **tests only** |
| DR / disaster-recovery replay | No `replay`/`rehydrate`/`restore_jobs`/`load_queue` job path |
| Debug/replay tooling | `openclaw_supervisor.py:429` `json.loads` reads a **self-audit JSONL event**, not a job |
| API/HTTP/webhook ingress | `webhook_receiver.py` parses a raw NL message string → `dae.process()`; jobs built **fresh** downstream, never via `from_dict` |
| pickle/marshal, dynamic dispatch, cron replay, deepcopy/`__reduce__` (critic) | all clear — zero job-rehydration |

---

## 7. Post-#747 Sanitization Chokepoint Assessment

**Sufficient (`chokepointSufficient = True`).**
- `PolicyFlags.from_dict` (`foundup_job_contract.py:284`) hardcodes every `_SERVER_AUTHORED_FLAGS` member
  (all `security_gate_*`, `permission_gate_*`, `exfoliation_gate_*`, `wsp_preflight_*`, `capability_token_*`)
  to `False`, ignoring inbound data; only `dry_run_mode` is read (safe direction). Both `FoundUpJob.from_dict`
  and `__post_init__` route through it — a genuine single chokepoint, no bypass registry.
- **Post-deserialization overwrite check:** the only writes to `job.policy_flags.capability_token_*` after
  deserialization are the four in `_writeback_token_verdict` (`hermes_job_executor.py:1207-1210`), all
  **server-authored from the real `TokenValidationResult`** and all **before the guard**. #747's Step 2.4
  write-back runs **unconditionally** (no `if`-branch) immediately before the Step 2.5 guard.
  `canSanitizedFlagsBeReintroduced = False`, `writebackChokepointBypassable = False`.
- **Caveat:** sufficiency rests on (a) routing any future persisted-queue rehydration *through* `from_dict`
  (not raw-dict field assignment), and (b) no security-gate evaluator existing in this executor
  (`security_gate_passed` stays server-default `False`, fail-closed). Both are addressed by the regression
  guards in §8.

---

## 8. Residual Risk / Trip-Wire Recommendation

The trip-wire is held by an **absence** (no production `from_dict` caller) plus a documented intent to add a
persistent queue — exactly the change that would convert this latent surface into a live one. Recommended
**read-only-to-add regression guards** (no production code change) to make the absence self-enforcing:

1. **AST/grep guard test** — assert **zero** non-test, non-self-definition callers of `FoundUpJob.from_dict`
   / `PolicyFlags.from_dict` across `modules/**/src/`. Fails CI the moment any production module wires
   `from_dict`, forcing a security review of the new rehydration boundary.
2. **Ordering invariant test** — assert `_writeback_token_verdict` runs unconditionally **before**
   `_evaluate_destructive_action_guard` in `execute()` (locks #747 Step 2.4-before-2.5 against refactors).
3. **Full-flag sanitization fuzz** — feed a malicious all-`True` `policy_flags` dict through `FoundUpJob.from_dict`
   **and** `__post_init__`; assert every `_SERVER_AUTHORED_FLAGS` member is `False` and only `dry_run_mode`
   survives (enumerate the full set so adding a new gate flag without sanitization fails).
4. **End-to-end fail-closed test** — a job built via `from_dict` with all-`True` gate flags but **no real token**
   run through `route_foundup_job → execute_foundup_job → execute` must be **blocked** at D3.

### Out-of-scope observations surfaced by the completeness critic (NOT trip-wire breaks — separate paths)
- **`validate_foundup_job_envelope` reads untrusted gate flags and HAS a production caller.** Correcting the
  sweep: `dae_gateway.py:339` (via `route_to_dae` → `_verify_envelope`) calls it, and it reads
  `security_gate_passed` / `permission_gate_passed` / `human_approval` directly from the inbound envelope dict
  (`foundup_job_router.py:581-589`). **This is the envelope→dae_gateway routing path, NOT the FoundUpJob→Hermes
  destructive-guard path** #747 protects, and it does not rehydrate a `FoundUpJob` into `execute`, so it does not
  break this trip-wire. But it is a *separate* place where untrusted inbound gate flags are trusted for a routing
  decision (`:1101` blocks only when `security_gate_checked ∧ ¬security_gate_passed`) — **worth its own focused
  look** (see §10).
- **`ImprovementJob.from_dict` trusts inbound `dry_run`** (`improvement_job_contract.py:657`, default `True` =
  safe direction). Sibling job contract; does **not** flow into `HermesJobExecutor.execute` (typed `FoundUpJob`-only).

---

## 9. Finding Classification

### `TRIPWIRE_CLEAR_WITH_RECOMMENDED_ASSERTIONS`

No production `from_dict` caller; queue is in-memory only with no serialization hop; no persistence/replay
modality rehydrates a `FoundUpJob` into WRE execution; the #747 chokepoint + unconditional write-back hold.
Classified **with recommended assertions** (not bare `TRIPWIRE_CLEAR`) because safety rests on an enumerated
absence and a documented persistent-queue TODO. The **completeness critic independently concurred**
(`classificationStands = True`), extended coverage to 8 further modalities (all clear), and corrected one sweep
claim (recorded in §8).

---

## 10. Recommended Next Slice

1. **Now (read-only-to-add):** `HXA_POLICYFLAGS_REGRESSION_GUARDS_PHASE1` — land the four §8 guard tests. Keeps
   the absence self-enforcing; no production code change.
2. **Separate follow-up (newly surfaced):** a focused read-only audit of the **`validate_foundup_job_envelope`
   / dae_gateway** path — does its untrusted gate-flag reading gate anything security-relevant, and is the
   permissive-on-absence behavior (`:1101`) intended? (Distinct from the FoundUpJob/Hermes chain.)
3. **When the persistent queue is built:** wire its rehydrate boundary **explicitly through `FoundUpJob.from_dict`**
   (never raw-dict field assignment), then re-run this exact trip-wire to confirm `productionCallerCount`
   transitions 0→1 *through* the sanitizing chokepoint and the write-back-before-guard ordering still holds.

---

## 11. Internal Review Verdict

**READY.** All seven dispatch questions answered with `file:line` evidence: (1) zero production `from_dict`
callers; (2) no persisted/cross-process queue rehydrates a job; (3) no JSONL/DR/replay rehydration into WRE
execution; (4) `_FOUNDUP_JOB_QUEUE` is strictly in-memory; (5) sanitized flags cannot be re-introduced before
the guard (write-backs are server-authored, before guard); (6) test-only naming recommendations captured
(with the `validate_foundup_job_envelope` correction); (7) the #747 chokepoint is sufficient and will extend to
a future persisted queue **iff** it routes through `from_dict`. Classification `TRIPWIRE_CLEAR_WITH_RECOMMENDED_
ASSERTIONS`, critic-concurred. Static-only; high confidence. Engineering/security only — no 012 ruling requested.

---

## 12. WSP_97 Truth Boundary Checklist

Declared count: **17 / 17 YES** (rows below = 17).

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | READ_ONLY_TRIPWIRE_AUDIT | YES | Only this audit doc written; all evidence via `git show`/`git grep` |
| 2 | NO_CODE_CHANGE | YES | No `.py` modified |
| 3 | NO_TEST_CHANGE | YES | No test modified (recommended guards are deferred to a separate slice) |
| 4 | NO_CONFIG_CHANGE | YES | No config touched |
| 5 | NO_ENV_MUTATION | YES | No env var set |
| 6 | NO_QUEUE_MUTATION | YES | `_FOUNDUP_JOB_QUEUE` read-only inspected; not appended/cleared |
| 7 | NO_JSONL_WRITE | YES | No JSONL written |
| 8 | NO_WORKTREE_REMOVE | YES | No worktree removed by the audit |
| 9 | NO_BRANCH_DELETE | YES | No branch deleted |
| 10 | NO_WSP_MUTATION | YES | No WSP doc changed |
| 11 | NO_SECRET_VALUES | YES | Only code structure / `file:line`; no tokens, keys, payloads |
| 12 | NO_REGISTRY_MUTATION | YES | Audit only |
| 13 | NO_MANIFEST_MUTATION | YES | Audit only |
| 14 | NO_PUBLIC_SURFACE_MUTATION | YES | Audit only |
| 15 | NO_CABR_READY | YES | Not touched |
| 16 | NO_PAYOUT_READY | YES | Not touched |
| 17 | NO_DAO_ACTIVATION | YES | Not touched |

**WSP 97 Truth Boundary Checklist: 17/17 YES.**

---

*Authored by 0102 (Worker-Lane W6) under WSP_00 zen state and WSP_97 Truth Boundary discipline.
Read-only verification of `origin/main` @ `87edcd779`. Finding: `TRIPWIRE_CLEAR_WITH_RECOMMENDED_ASSERTIONS`
— no path rehydrates a FoundUpJob via `from_dict` into WRE execution; #747's sanitize-and-write-back chokepoint
holds. The PolicyFlags chain (#744 → #746 → #747 → this) is closed pending the §8 regression guards.*
