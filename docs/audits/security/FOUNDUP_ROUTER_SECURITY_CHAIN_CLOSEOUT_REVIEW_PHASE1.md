# FoundUp Router Security Chain Closeout Review (Phase 1)

**Slice:** FOUNDUP_ROUTER_SECURITY_CHAIN_CLOSEOUT_REVIEW_PHASE1
**Worker-Lane:** W9 - **Author:** 0102 (WSP_00 zen state, WSP_97 Truth Boundary discipline)
**Type:** READ-ONLY adversarial closeout review. No code, tests, cherry-pick, or worktree mutation.
**Base:** origin/main @ d95f1183c (HEAD == origin/main; all line numbers re-verified live, prior audits NOT trusted).
**Method:** read-only subworkers (chain-state / residual-surface / object-path-adversary / future-ingress /
regression-guards) -> draft verdict -> adversarial critic.

---

## 1. Mission and Scope

The router/gateway PolicyFlags trust-boundary chain (#752 audit, #753 validation seam, #754 routing seam) is
code-complete. Critically review the WHOLE chain on current main and answer, with file:line evidence, what
actually remains - do not assume the fixes are correct; re-verify them. Verdict is one of CHAIN_CLOSED /
CHAIN_CLOSED_WITH_RECOMMENDED_GUARDS / RESIDUAL_GAP_FOUND. This is a review, not a re-implementation.

---

## 2. Predecessor Citations

| PR | Slice | Effect (re-verified) |
|----|-------|----------------------|
| #752 (f3b0293e5) | DAE_GATEWAY_ENVELOPE_GATEFLAGS_TRUST_BOUNDARY_AUDIT | DOCS-ONLY audit; classified the envelope->dae_gateway path GAP_CONFIRMED_BOUNDED |
| #753 (0cbcc7824) | POLICYFLAGS_BOUNDARY_SANITIZATION_AND_GATE2_FAILCLOSED | Validation seam: dict branch sanitized; Gate 2 fail-closed |
| #754 (d95f1183c) | ROUTE_GATE_LIVE_MODE_DISCRIMINATOR | Routing seam: raw-dict sanitize + is_live discriminator + fail-closed live gate |
| #744 -> #751 | PolicyFlags chain (FoundUpJob->Hermes path) | Context: #747 sanitize+write-back, #751 trip-wire CLEAR |

---

## 3. Chain State Map (re-verified file:line)

| Seam | Site | State |
|------|------|-------|
| Validation seam | `foundup_job_router.py:383` (`validate_foundup_job_envelope`), `:597` (`_validate_live_mode_gates`), is_live `:483` | #753: dict branch `:466-475` -> `_sanitize_untrusted_policy_flags_dict`; Gate 2 `:639-647` fail-closed (`if not security_gate_passed`); object branch never-live |
| Routing seam | `foundup_job_router.py:1077` (`route_foundup_job`), Policy Check `:1151-1182`, is_live `:1168` | #754: removed opt-in block + raw `policy_summary = policy_flags`; dict branch `:1160-1162` sanitizes; live gate `:1172-1182` BLOCKED_POLICY_GATE; object path `dry_run_defaulted=True` (never live) |
| Sanitizer | `foundup_job_router.py:337` | NEW #753; `PolicyFlags.from_dict(policy_flags).to_dict()`; restores `dry_run_mode=True` when absent; used by BOTH seams |
| PolicyFlags chokepoint | `foundup_job_contract.py:284-324`, `_SERVER_AUTHORED_FLAGS :200-215` | `from_dict` forces all 12 server-authored flags False, preserves only `dry_run_mode`. NOT modified by #752/#753/#754 |
| #747 write-back-before-guard | `hermes_job_executor.py:1158` (`_writeback_token_verdict`), called `:1521` (Step 2.4) BEFORE guard `:1524` (Step 2.5) | Pre-existing; NOT modified by the chain. Execution-permission seam, structurally separate from the router |
| dae_gateway boundary | `dae_gateway.py:149` (`route_to_dae`), `:325` (`_verify_envelope`), `:339` (calls validation seam) | NOT modified by the chain; #753 hardening takes effect through it. route_to_dae dispatches to pattern-recall, NOT to route_foundup_job/execute |

Change surface (name-only diffs, authoritative): #752 docs-only; #753 + #754 each = `foundup_job_router.py`
+ tests + ModLog/TestModLog + audit. `hermes_job_executor.py`, `dae_gateway.py`, `foundup_job_contract.py`
were NOT touched by any of the three PRs (re-verified).

---

## 4. Q1 - What Remains (residual surface)

**residualSurfaceCount = 0.** All raw-dict policy_flags read sites in the four chain files resolve to
CLOSED_BY_SANITIZER or SERVER_AUTHORED_ONLY. No production gate read consumes an unsanitized raw policy_flags
dict. Representative sites: `foundup_job_router.py:455` (validate envelope.get), `:1152` (route getattr),
`:635/636/643/644` (live-gate reads of the already-sanitized snapshot), `foundup_job_contract.py:461/662`
(both route through `PolicyFlags.from_dict`). Server-authored-only: `foundup_job_contract.py:627`
(`to_dict`), `dae_gateway.py:353` (reads the validation result), `foundup_job_consumer.py` (`self.dry_run`).

---

## 5. Q2 - Object-Path Asymmetry Adversarial Test (LOAD-BEARING)

**Premise CONFIRMED, bypass REFUTED, bounded by executor-owned `self.dry_run` (not the router gate, not the
#747 guard alone).**

**Consumer executor binding (resolved):** `foundup_job_consumer.py:425-426` imports `execute_foundup_job` from
`modules.infrastructure.wre_core.src.hermes_job_executor` and calls it at `:439`. The NAVIGATION comment at
`foundup_job_consumer.py:27` ("Uses: hermes_foundup_job_executor.py") is **STALE** - it names the legacy
`modules/foundups/agent/src/hermes_foundup_job_executor.py`, which is NOT imported on this path. Code binding
wins; the legacy executor is dead here. `executorHasDestructiveGuard = True`, `writebackBeforeGuard = True`.

**Strongest bypass construction (the adversary premise holds at routing):** a server-authored FoundUpJob whose
`policy_flags` is a PolicyFlags object (so `.to_dict()` branch), `requested_action="build_foundup"`
(-> HERMES_BUILDER / D3_WRITE_SANDBOX), `dry_run_mode=False`, `security_gate_passed=False`, all four
`capability_token_*` True, + a workspace_binding with allowed_paths. At `route_foundup_job` the object path
keeps `dry_run_defaulted=True` (`:1154`, `:1156-1160`), so `is_live` is False (`:1168`) and the #754 live gate
(`:1172`) does NOT fire -> the job ROUTES (ROUTED / HERMES_BUILDER). **So this object-path job IS NOT blocked
at the routing seam.**

**Why that is bounded (route != execute):** at the executor, `build_delegation_request` sets
`request.dry_run = self.dry_run` (`hermes_job_executor.py:834`) and `_build_destructive_action_request` sets
`DestructiveActionRequest.dry_run_mode = request.dry_run` (`:1145`). The consumer-bound singleton is
`get_executor()` with default `dry_run=True` (`:2249/:2257`). **The job's own attacker-settable
`policy_flags.dry_run_mode` is never read into the guard request**, so the destructive-action guard always sees
`dry_run_mode=True` and, for the only routable D3/D0 actions, returns at most ALLOW_DRY_RUN with
`live_execution_allowed=False`. This is backstopped by three further terminal gates in `execute()`: Step 4
delegation-disabled -> SIMULATED, Step 5 `self.dry_run=True` -> SIMULATED (`:1700`), and Step 7 unconditional
`BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` (`:1754`, **no real-execution branch exists at all**). No production
caller constructs the executor with `dry_run=False` or `controlled_harness=True` (the only `dry_run=False`
construction sites belong to unrelated executors). The #747 write-back (`:1521`) re-confirmed to precede the
guard (`:1524`).

**Bounding-gate statement (exact):** the object-path asymmetry is bounded by **executor-owned `self.dry_run`
on the consumer-bound singleton (default True), plus the unconditional Step-7 real-delegation block** - i.e.
Phase 1 has no live-execution branch reachable from this path at all. The router live gate and the #747 guard
are additional layers, but the decisive bound is the executor's own dry-run authority, which the job cannot
influence. Q2 verdict: **REFUTED** (no present bypass).

---

## 6. Q3 - Future-Ingress Inventory

**anyOpensNewGap = True, but strictly FUTURE-work and BOUNDED** (no present reachable ingress).

| Candidate | Sanitization holds today? |
|-----------|---------------------------|
| Today's sole live ingress (run_wre.py:152 -> GENERIC_DAE; webhook MoltbotMessage has no policy_flags; in-memory `List[FoundUpJob]` queue) | HOLDS - no untrusted policy_flags reaches either seam |
| Persistent queue (JSONL/SQLite rehydrate) | HOLDS *if* it rehydrates via `FoundUpJob.from_dict` (routes through the chokepoint) |
| HTTP/API / webhook / message bus | HOLDS *if* the dict reaches a seam's dict branch (sanitized) |
| New `FoundUpJob.from_dict` / `PolicyFlags.from_dict` wiring | HOLDS - by definition routes through the chokepoint |
| **A NEW raw-dict gate read, OR a PolicyFlags OBJECT built from attacker fields, NOT routed through the sanitizer** | **OPENS A NEW GAP** - the sanitizer fires only on the dict branches that call `_sanitize_untrusted_policy_flags_dict`; net-new wiring that reads gate flags off a raw dict, or constructs a server-authored object from attacker input, bypasses it |

The new-gap class requires net-new wiring that does not exist today; classify BOUNDED (future-work), guarded
by the AST/grep regression guard recommended in Q4.

---

## 7. Q4 - Regression-Guard Inventory (have 8 / missing 5)

**HAVE (behavioral/fixed-case):** (b) write-back-before-guard effect (behavioral: D3 BLOCKED proven, not an
explicit order assertion); (d) D3 fail-closed at the executor (D3 stays dry-run, D4/D5/D6 blocked); (e) both
seams use the same `_sanitize_untrusted_policy_flags_dict`; (f) missing `dry_run_mode` is not live;
(g) raw-dict route fallback sanitizes forged flags; (h) object-path non-live routing (routes, not over-blocked)
+ executor-level execution bound; (c-fixed) all 12 `_SERVER_AUTHORED_FLAGS` zeroed (enumerated, not fuzz);
contract-level from_dict chokepoint.

**MISSING (CI coverage gaps - none is a present bypass):**
1. **AST/grep "no production from_dict caller" invariant** - the deserialization-chokepoint architectural rule
   is exercised behaviorally but UNGUARDED against a future production caller.
2. **`FOUNDUP_JOB_VALIDATION_AVAILABLE` startup assertion** - `dae_gateway.py:56-58` sets it False on
   ImportError and `:334` silently degrades to permissive (`required=['objective']`) validation; no startup
   assertion, no test references the flag. (Critic-confirmed NON-reachable to destructive execution:
   `route_to_dae` -> pattern-recall, not -> `route_foundup_job`/`execute`.)
3. **Gateway end-to-end D3 fail-closed test** - `wre_gateway/` has NO `tests/` directory; the gateway seam is
   untested end-to-end.
4. **Property-based sanitization fuzz** - all assertions are fixed cases; a future flag added to PolicyFlags
   but omitted from `_SERVER_AUTHORED_FLAGS` would not be caught.
5. **Gateway permissive-fallback regression guard** - the silent-degradation branch is uncovered.

**Recommended guard slice:** `HXA_POLICYFLAGS_REGRESSION_GUARDS_PHASE1` (read-only-to-add tests; no production
code) covering items 1-5 + an explicit write-back-before-guard ordering assertion.

---

## 8. Q5 - Two-Seam Consistency Check

**Consistent.** Both seams call the SAME `_sanitize_untrusted_policy_flags_dict` (`:337`) on their dict branch
(validation `:466-470`, routing `:1160-1164`) and use the IDENTICAL live-mode formula
`dry_run_mode is False AND not dry_run_defaulted` (validation `:483`, routing `:1168`). No divergence where one
seam accepts what the other rejects.

---

## 9. Adversarial Bypass Attempt + Critic Review

**Strongest attempt:** the Q2 object-path construction (server-authored object, build_foundup, dry_run_mode=False,
security_gate_passed=False) - it routes, but is bounded at the executor (Section 5). **REFUTED.**

**Critic Review - verdict PASS (UPHELD, high confidence).** The critic independently re-verified the consumer
executor binding (`:425-426` overrides the stale `:27` comment), confirmed route != execute (no conflation),
confirmed the bounding gate is executor-owned `self.dry_run` (not the router gate), and confirmed the gateway
permissive-fallback is future-work not a present bypass (`route_to_dae` -> pattern-recall, never -> execute).
Issues found were non-load-bearing line drift only (Step 5 body `:1700`; `get_executor` `:2249/:2257`; router
object comment `:1153-1160`) and a consumer path cited without its full directory prefix - corrected here; none
change a conclusion. No missed production caller, no `security_gate_checked`-as-authority error, no present bypass.

---

## 10. Verdict

### CHAIN_CLOSED_WITH_RECOMMENDED_GUARDS (gap class: BOUNDED)

The present code path is CLOSED: Q1 residual = 0; the object-path adversary is REFUTED (route != execute,
bounded by executor-owned dry-run + Step-7 unimplemented real delegation); both seams are consistent. It is
NOT bare CHAIN_CLOSED because CI guard coverage is materially incomplete (5 missing guards, notably the
entirely-untested gateway seam and the unguarded `FOUNDUP_JOB_VALIDATION_AVAILABLE` silent-degradation). It is
NOT RESIDUAL_GAP_FOUND because no present or near-future bypass is reachable on today's wiring; the only
new-gap class (Q3) requires net-new wiring that does not exist today (BOUNDED, future-work).

---

## 11. Recommended Next Slice

`HXA_POLICYFLAGS_REGRESSION_GUARDS_PHASE1` - read-only-to-add test bundle (NO production code) closing the 5
missing guards (AST no-production-from_dict-caller invariant; `FOUNDUP_JOB_VALIDATION_AVAILABLE` startup
assertion; gateway end-to-end D3 fail-closed; property-based sanitization fuzz; gateway permissive-fallback
guard) + an explicit write-back-before-guard ordering assertion. Secondary (doc hygiene, optional): correct the
stale `foundup_job_consumer.py:27` nav comment to point at `wre_core.src.hermes_job_executor`.

---

## 12. Internal Review Verdict

**READY.** All five review questions answered with re-verified file:line evidence: Q1 residual=0;
Q2 REFUTED, bounded by executor-owned `self.dry_run` + Step-7 block (named, not hand-waved); Q3 no present
ingress, one BOUNDED future-work gap class; Q4 8 have / 5 missing + named guard slice; Q5 consistent.
Object-path bypass attempt recorded and refuted. NO_OVERCLAIM honored (route != execute kept distinct;
CHAIN_CLOSED not asserted). Critic UPHELD high confidence. Decision-only - no code authorized here.

---

## 13. Subworker Findings Summary

| Subworker | Finding |
|-----------|---------|
| chain_state | All 6 seams re-verified on d95f1183c; #747/gateway/contract untouched by the chain |
| residual_surface | 0 residual surfaces; 11 CLOSED_BY_SANITIZER + 3 SERVER_AUTHORED_ONLY |
| object_path_adversary | Premise confirmed (routes), bypass REFUTED; executor binding = wre_core hermes_job_executor; bounded by self.dry_run |
| future_ingress | No present ingress; 1 BOUNDED future-work new-gap class (raw-dict read / object-from-attacker bypassing sanitizer) |
| regression_guards | 8 have / 5 missing; slice HXA_POLICYFLAGS_REGRESSION_GUARDS_PHASE1 |
| critic | UPHELD, high confidence; only non-load-bearing line drift corrected |

---

## 14. WSP_97 Truth Boundary Checklist

Declared items: 24 - Rows: 24 - All YES.

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | READ_ONLY_CLOSEOUT_REVIEW | YES | Only this doc written; all evidence via git show/grep |
| 2 | NO_CODE_CHANGE | YES | No .py modified |
| 3 | NO_TEST_CHANGE | YES | No test modified |
| 4 | NO_CHERRY_PICK | YES | None performed |
| 5 | NO_WORKTREE_REMOVAL | YES | Review performed no worktree removal |
| 6 | NO_BRANCH_DELETE | YES | No branch deleted |
| 7 | NO_CONFIG_CHANGE | YES | No config touched |
| 8 | NO_SECRET_VALUES | YES | Only code structure / file:line |
| 9 | DISTINCT_FROM_IMPLEMENTATION | YES | Review only; #752-#754 not re-implemented |
| 10 | NO_OVERCLAIM | YES | route != execute kept distinct; CHAIN_CLOSED not asserted; future-gap bounded |
| 11 | CITES_PR_752_753_754 | YES | Sec 2, 3 |
| 12 | CURRENT_MAIN_LINE_NUMBERS_REVERIFIED | YES | All lines re-derived on d95f1183c; prior audits not trusted |
| 13 | NO_CABR_READY | YES | Not touched |
| 14 | NO_PAYOUT_READY | YES | Not touched |
| 15 | NO_DAO_ACTIVATION | YES | Not touched |
| 16 | ASCII_CLEAN_AUDIT | YES | Doc is ASCII-only |
| 17 | SUBWORKERS_COMPLETED | YES | Sec 13 (6 subworkers + critic) |
| 18 | PRODUCTION_CALLERS_DISTINGUISHED_FROM_TESTS | YES | Sec 5 (consumer binding), Sec 4 (residual classification) |
| 19 | OBJECT_PATH_BYPASS_ATTEMPT_RECORDED | YES | Sec 5, Sec 9 (construction + REFUTED) |
| 20 | FUTURE_INGRESS_INVENTORIED | YES | Sec 6 |
| 21 | REGRESSION_GUARDS_INVENTORIED | YES | Sec 7 (8 have / 5 missing) |
| 22 | CRITIC_REVIEW_COMPLETED | YES | Sec 9 (UPHELD, high confidence) |
| 23 | CANONICAL_WSP97_HEADER_USED | YES | This table uses the canonical 4-column header |
| 24 | NO_ROUTE_EQUALS_EXECUTION_OVERCLAIM | YES | Sec 5: route_foundup_job returns RouteEnvelope only; execution bounded at executor |

**WSP 97 Truth Boundary Checklist: 24/24 YES.**

---

*Authored by 0102 (Worker-Lane W9) under WSP_00 zen state and WSP_97 Truth Boundary discipline. Read-only
closeout review of origin/main @ d95f1183c. Verdict: CHAIN_CLOSED_WITH_RECOMMENDED_GUARDS (BOUNDED) - the
#752/#753/#754 code path is closed (residual surface 0; object-path bypass REFUTED, bounded by executor-owned
dry-run, not the router gate); the only outstanding work is CI regression guards (slice
HXA_POLICYFLAGS_REGRESSION_GUARDS_PHASE1). No code authorized here.*
