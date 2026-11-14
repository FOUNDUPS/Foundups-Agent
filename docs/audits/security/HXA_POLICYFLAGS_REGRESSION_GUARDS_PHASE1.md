# HXA_POLICYFLAGS_REGRESSION_GUARDS_PHASE1

Worker-Lane: W6
Slice: HXA_POLICYFLAGS_REGRESSION_GUARDS_PHASE1
Base: origin/main @ 01eb327d9900d44d96318792a7605463f0519081
Scope: TESTS / GUARDS ONLY (+ ModLog, TestModLog, this audit, new wre_gateway/tests/)

---

## 1. Mission and Scope

This slice is the CI-coverage capstone named by the #755 router-security-chain
closeout review ("the only outstanding work is CI regression guards (slice
HXA_POLICYFLAGS_REGRESSION_GUARDS_PHASE1)"). The PolicyFlags trust chain is
already CLOSED in production; this slice does NOT re-implement or re-prove
per-slice behavior. It installs six durable INVARIANT guards that TRIP if a
future edit silently re-opens a closed hole.

GUARDS ONLY. No production code is modified. If a guard had exposed a real
current defect, the rule was: STOP, document, recommend a separate remediation
slice, do NOT fix here and do NOT weaken the guard. No such defect was found
(see Section 11).

In-scope files:
1. `modules/infrastructure/wre_core/tests/test_policyflags_regression_guards.py` (G1, G4, G6)
2. `modules/infrastructure/wre_core/wre_gateway/tests/__init__.py` (new package)
3. `modules/infrastructure/wre_core/wre_gateway/tests/test_dae_gateway_policyflags_guards.py` (G2, G3, G5)
4. `modules/infrastructure/wre_core/ModLog.md` + `modules/infrastructure/wre_core/tests/TestModLog.md`
5. `docs/audits/security/HXA_POLICYFLAGS_REGRESSION_GUARDS_PHASE1.md` (this doc)

The optional 1-line nav-comment fix at `foundup_job_consumer.py:27` is DEFERRED
(see Section 12) - it is a doc-hygiene staleness outside the security-guard scope.

---

## 2. Predecessor #755 and the Chain (#752 - #754)

| PR | Slice | Role |
|----|-------|------|
| #746 | HXA_POLICYFLAGS_WRITEBACK_REMEDIATION | Server-authored token verdict written into job.policy_flags BEFORE the destructive-action guard reads it (#747 ordering) |
| #752 | DAE_GATEWAY_ENVELOPE_GATEFLAGS_TRUST_BOUNDARY_AUDIT | Classified the envelope -> dae_gateway path GAP_CONFIRMED_BOUNDED |
| #753 | POLICYFLAGS_BOUNDARY_SANITIZATION_AND_GATE2_FAILCLOSED | Validation seam: raw dict branch sanitized; Gate 2 (security) fail-closed in live mode |
| #754 | ROUTE_GATE_LIVE_MODE_DISCRIMINATOR | Routing seam: raw-dict sanitize + is_live discriminator + fail-closed live gate |
| #755 | FOUNDUP_ROUTER_SECURITY_CHAIN_CLOSEOUT_REVIEW | Read-only closeout: CHAIN_CLOSED_WITH_RECOMMENDED_GUARDS (BOUNDED); NAMED this guard slice |

The #755 review (lane W9) inventoried "8 have / 5 missing" regression guards.
This slice installs the missing guard surface as durable CI invariants.

---

## 3. FOLLOW-WSP Evidence

### Step 1 - Occam's Razor
Simplest guard that traps each failure mode, with NO new dependency. `hypothesis`
is NOT installed; G4's "property-based fuzz" is implemented with stdlib
`dataclasses.fields` (dynamic enumeration) + `itertools.product` (representative
combinations). AST guards use the stdlib `ast` module. No runtime, no network, no
model, no live DAE.

### Step 2 - HoloIndex (queries run + top results)
`python holo_index.py --search ...` was available and run. Top results cited:

| Query | Top results (surfaced) |
|-------|------------------------|
| policyflags sanitization regression guard test | ai_overseer.py; wre_core/src/pattern_memory.py; WSP_5 / WSP_16 / WSP_47 |
| AST grep architectural rule no production caller | WSP_40 Architectural Coherence; WSP_9; WSP_MODULE_VIOLATIONS; pattern_memory.py |
| from_dict deserialization chokepoint test | moltbot_bridge/tests/test_openclaw_dae.py; pattern_memory.py; WSP_5 / WSP_16 / WSP_39 |
| wre_gateway route_to_dae envelope validation test | moltbot_bridge/tests/test_openclaw_dae.py; wre_skills_loader.py; WSP_95; WSP_4; WSP_106 |
| write-back before guard ordering assertion | digital_twin/style_guardrails.py; pattern_memory.py; WSP_50 / WSP_6 / WSP_14 |
| property based fuzz dataclass fields enumeration | synthetic_user_agent.py (SyntheticPersona dataclass); autonomous_refactoring.py; digital_twin/schemas.py |

HoloIndex did not surface an existing guard for these invariants (the #755 review
also classified them as missing), confirming this is net-new guard coverage, not
duplication. The three named exemplar suites
(`test_foundup_job_router_policyflags_boundary.py`,
`test_hxa_policyflags_writeback_remediation.py`,
`test_route_foundup_job_live_mode_gate.py`) were read and their patterns mirrored
(forged-flag fail-closed envelopes, `create_job` + `HERMES_DELEGATE_ENABLED=0`
bounded executor harness, live-mode gate semantics).

### Step 4 - NAVIGATION verification
`NAVIGATION.py` has no policyflags/dae_gateway-specific entries (grep: no matches),
so no navigation map needed updating. All anchor line numbers below were
re-derived directly against origin/main @ 01eb327d9 (prior audits not trusted).

---

## 4. Anchors Re-Verified on origin/main @ 01eb327d9

| Anchor | Location (re-verified) |
|--------|------------------------|
| `_SERVER_AUTHORED_FLAGS` frozenset | `foundup_job_contract.py:200-215` (12 members) |
| `PolicyFlags` dataclass | `foundup_job_contract.py:218` (13 fields total) |
| `PolicyFlags.from_dict` chokepoint | `foundup_job_contract.py:283-324` (only `dry_run_mode` preserved) |
| Caller: `__post_init__` | `foundup_job_contract.py:461` |
| Caller: `FoundUpJob.from_dict` body | `foundup_job_contract.py:662` |
| Caller: router sanitizer | `foundup_job_router.py:372` (def at `:337`) |
| Docstring hits (NOT calls) | `foundup_job_router.py:354`; `hermes_job_executor.py:1167`, `:1517`; `foundup_job_contract.py:194`, `:305` |
| `FOUNDUP_JOB_VALIDATION_AVAILABLE` | `dae_gateway.py:56/:58`, used `:334` |
| `route_to_dae` | `dae_gateway.py:149`; dispatch `_invoke_core_dae:214`, `_invoke_foundup_dae:275` |
| #747 ordering | `hermes_job_executor.py` execute(): `_writeback_token_verdict` `:1521` BEFORE `_evaluate_destructive_action_guard` `:1524` |

Runtime field enumeration confirmed 13 PolicyFlags fields; every non-`dry_run_mode`
field (12) is a member of `_SERVER_AUTHORED_FLAGS`, and the frozenset has exactly
those 12. This equivalence is the property G4 locks.

---

## 5. Per-Guard Reasoning Summary / WSP_97 Rationale

(Reasoning Summary; not private chain-of-thought.)

| Guard | #755 finding traced to | Invariant locked | Failure mode caught | file:line evidence | Negative control + method |
|-------|------------------------|------------------|---------------------|--------------------|---------------------------|
| G1 | "no-production-caller" architectural rule (residual surface 0) | FoundUpJob.from_dict prod callers = 0; PolicyFlags.from_dict prod callers exactly the 3-entry allowlist | A new untrusted-deserialization caller (object-path bypass) added to production | contract:461, contract:662, router:372 (allowlist); docstrings excluded by AST | `negative_control_method=synthetic_source_string`: AST scan of an inline source string with an extra `FoundUpJob.from_dict` call + comment + docstring detects ONLY the real CALL (line 4), comment/docstring/string-literal excluded |
| G2 | "8 have / 5 missing" - validator-available health | `FOUNDUP_JOB_VALIDATION_AVAILABLE is True` in a healthy env (test-only, NOT a prod startup assert) | The WSP 97 envelope validator import silently breaks -> gateway degrades to permissive | dae_gateway:49-58 | `negative_control_method=monkeypatch_module_constant`: patching the flag False makes the `is True` assertion raise (pytest.raises) |
| G3 | envelope -> dae_gateway "GAP_CONFIRMED_BOUNDED" (#752) | Forged live FoundUpJob envelope is BLOCKED before any DAE dispatch | A removed/broken sanitizer lets a forged `security_gate_passed=True` live envelope reach `_invoke_core_dae`/`_invoke_foundup_dae` | dae_gateway:167 (`_verify_envelope`), router `_validate_live_mode_gates` fail-closed | `negative_control_method=monkeypatch_function`: patching `_verify_envelope` -> True makes the SAME forged envelope dispatch (`_invoke_core_dae.called is True`), proving the block assertion is non-vacuous |
| G4 | sanitization correctness (#752/#753) | Every non-`dry_run_mode` field forced False by BOTH contract + router sanitizers; every such field in `_SERVER_AUTHORED_FLAGS`; router/contract CONSISTENT | A new gate field added without registering it server-authored, or a sanitizer that leaks a True flag | contract:283-324, router:337-378; fields enumerated at runtime | `negative_control_method=test_local_fake_dataclass_sanitizer`: a fake sanitizer preserving `security_gate_passed=True` fails the property (pytest.raises) |
| G5 | permissive-fallback bounding | With validation unavailable, degraded behavior is bounded: FoundUpJob-shaped (no objective) still blocked; even a dispatching generic envelope reaches only the pattern-recall stub, never route/execute | Degraded mode escalates to live/destructive execution | dae_gateway:334 (avail gate), :359-374 (permissive), :214/:275 (stubs) | `negative_control_method=monkeypatch_module_constant`: healthy-env contrast test shows STRICT block (different code path); proves the flag drives behavior |
| G6 | #747 write-back-before-guard ordering | `_writeback_token_verdict` precedes `_evaluate_destructive_action_guard` in execute() (static AST source-order AND behavioral spy) | Re-ordering so the guard reads pre-write-back (untrusted) policy_flags | hermes_job_executor.py execute(): :1521 before :1524 | `negative_control_method=synthetic_inverted_source_snippet`: an in-memory inverted source (guard before write-back) fails the same `wb<guard` check |

---

## 6. G1 Allowlist Rationale

`PolicyFlags.from_dict` is the single untrusted-deserialization chokepoint; it
LEGITIMATELY has multiple production callers, so a naive `count == 0` assertion
would be WRONG (it would falsely fail). G1 therefore uses an ALLOWLIST keyed by
`(production source file, enclosing function name)` resolved via AST:

| Allowlisted caller | file:line | Why legitimate |
|--------------------|-----------|----------------|
| `FoundUpJob.__post_init__` | contract:461 | Coerces a dict policy_flags on object construction (routes through the sanitizing chokepoint) |
| `FoundUpJob.from_dict` body | contract:662 | The deserialization entrypoint itself |
| `_sanitize_untrusted_policy_flags_dict` | router:372 | The router trust-boundary sanitizer (#752) |

Any PolicyFlags.from_dict call NOT in this allowlist TRIPS G1. The guard also
asserts all three chokepoints are STILL present (so a silent removal/rename is
caught), and pins the total production call count at 3. By contrast,
`FoundUpJob.from_dict` has ZERO production callers (only tests call it), so it
uses the strict count==0 form. AST excludes strings/comments/docstrings because
only `ast.Call` nodes are inspected; tests/archives are excluded by path
(`tests`, `test`, `archive`, `_archive`, `archived`, `__pycache__`).

---

## 7. Negative Control Methods Table (all SAFE - no committed mutation)

| Guard | negative_control_method | Mechanism | Observed fail-when-inverted |
|-------|-------------------------|-----------|------------------------------|
| G1 | synthetic_source_string | In-memory source string parsed with `ast` | Extra `FoundUpJob.from_dict` CALL detected at line 4; comment + docstring + string-literal NOT counted (0 hits in the strings-only synthetic) |
| G2 | monkeypatch_module_constant | `patch.object(gw, "FOUNDUP_JOB_VALIDATION_AVAILABLE", False)` | `assert ... is True` raises under the patch (pytest.raises) |
| G3 | monkeypatch_function | `patch.object(gateway, "_verify_envelope", return_value=True)` | Forged envelope dispatches: `_invoke_core_dae.called is True` |
| G4 | test_local_fake_dataclass_sanitizer | Fake sanitizer that preserves a True flag | Property assertion raises (pytest.raises) |
| G5 | monkeypatch_module_constant | Healthy-env (no patch) contrast vs degraded (patched) | Healthy path takes the STRICT block branch (distinct validation_code), degraded path differs |
| G6 | synthetic_inverted_source_snippet | In-memory inverted execute() source | `wb < guard` is False for the inverted snippet |

NO production file was edited or committed to prove any guard trips. `git status
--porcelain` showed no dirty production file at any point (verified after the
synthetic negative controls).

---

## 8. Guard Failure Mode Matrix

| Failure re-introduced | Guard that trips |
|-----------------------|------------------|
| New untrusted `FoundUpJob.from_dict` caller in production | G1 (count==0) |
| New non-allowlisted `PolicyFlags.from_dict` caller | G1 (allowlist + count==3) |
| A chokepoint silently removed/renamed | G1 (presence assertion) |
| Envelope validator import breaks | G2 |
| Sanitizer removed -> forged live envelope dispatches | G3 |
| Gateway gains an execution-path import | G3 (no-import structural) |
| New gate field not registered server-authored | G4 (membership) |
| Sanitizer leaks a True gate flag (either path) | G4 (force-False, both paths) |
| Router/contract sanitizers diverge on non-dry_run fields | G4 (consistency) |
| Degraded mode escalates to dispatch on a FoundUpJob envelope | G5 |
| Write-back re-ordered after the guard | G6 (static + behavioral) |

---

## 9. Production Caller Classification Table

| Symbol | file:line | ast.Call? | In docstring/comment/string? | Classification |
|--------|-----------|-----------|------------------------------|----------------|
| PolicyFlags.from_dict | contract:461 | YES | no | PRODUCTION CALLER (allowlisted: __post_init__) |
| PolicyFlags.from_dict | contract:662 | YES | no | PRODUCTION CALLER (allowlisted: from_dict body) |
| PolicyFlags.from_dict | router:372 | YES | no | PRODUCTION CALLER (allowlisted: sanitizer) |
| PolicyFlags.from_dict | router:354 | no | docstring | EXCLUDED |
| PolicyFlags.from_dict | hermes:1167 | no | docstring | EXCLUDED |
| PolicyFlags.from_dict | hermes:1517 | no | comment | EXCLUDED |
| PolicyFlags.from_dict | contract:194 | no | comment | EXCLUDED |
| PolicyFlags.from_dict | contract:305 | no | comment | EXCLUDED |
| FoundUpJob.from_dict | (production) | - | - | ZERO production callers (tests only) |

Production scan surface: `modules/**` + `holo_index/**`, excluding any path
component in {tests, test, archive, _archive, archived, __pycache__}. The scan
tolerates a UTF-8 BOM (`utf-8-sig`) and, for any file that still fails to parse,
re-raises ONLY if that file's raw text contains the `<owner>.from_dict` token
(so an unparseable file can never silently hide a caller).

---

## 10. Gateway No-Live-Execution Proof

All G2/G3/G5 tests prove blocked-before-dispatch via mocks/spies; none starts
WRE, a DAE, or Hermes, and none touches the network/model/process:

- `route_to_dae` is async and driven by `asyncio.run`.
- `_invoke_core_dae` and `_invoke_foundup_dae` (the ONLY doorways to DAE work)
  are replaced with `AsyncMock`; tests assert `.called is False` on the block
  path and assert the dispatch lands on a sentinel stub on the degraded-generic
  path.
- Structural proof (G3 `test_gateway_module_has_no_execution_path_imports`):
  `dae_gateway.py` contains NONE of `route_foundup_job`, `HermesJobExecutor`,
  `execute_foundup_job`, `hermes_job_executor` - the routing layer cannot reach
  the FoundUpJob execution path regardless of routing outcome. Therefore even a
  dispatching degraded-mode request cannot escalate to destructive execution.
- G6's behavioral test uses `HermesJobExecutor(dry_run=True, ...)` with
  `HERMES_DELEGATE_ENABLED=0` and `create_job(...)`; it asserts only relative
  call ORDER (write-back before guard) and tolerates the bounded downstream
  block. No live delegation, repo creation, or network call occurs. SQLite/file
  handles are released via `gc.collect()` before temp cleanup (Windows).

---

## 11. Real Defect Escalation Decision

No real current defect was exposed. All six guards PASS against origin/main @
01eb327d9, and all 61 existing PolicyFlags-related tests continue to pass. The
chain is closed as #755 concluded; these guards lock that closed state. No
remediation slice is recommended at this time. (Had a guard exposed a defect,
the rule was STOP + document + recommend a separate slice + do NOT weaken the
guard - not exercised.)

---

## 12. foundup_job_consumer.py:27 - Deferred

The NAVIGATION comment at `foundup_job_consumer.py:27` reads
`-> Uses: hermes_foundup_job_executor.py (execute_foundup_job)`, but the actual
production import at `:425-426` is `from ...wre_core.src.hermes_job_executor
import execute_foundup_job` (a file named `hermes_foundup_job_executor.py` exists
only under `modules/foundups/agent/src/`, which the consumer does NOT use). This
is a doc-hygiene staleness (wrong filename in a nav breadcrumb). It is NOT
load-bearing for any guard and is outside the security-guard scope, so it is
DEFERRED rather than touched in this tests-only slice.

---

## 13. Test Results

Focused (both new guard files):
`python -m pytest <two new files> -q` -> 24 passed (14 + 10).

Module suites:
`python -m pytest modules/infrastructure/wre_core/tests
modules/infrastructure/wre_core/wre_gateway/tests -q` ->
1424 passed, 5 failed, 3 skipped, 2 xfailed.

The 5 failures are PRE-EXISTING, environment/worktree artifacts unrelated to this
slice, proven against a clean main checkout (all 5 PASS there):

| Failing test | Root cause | Baseline (main checkout) |
|--------------|-----------|--------------------------|
| test_hxa16_real_hermes_delegate_adapter_safe_harness (x4) | `vendor/hermes-agent` is a git SUBMODULE not populated in the fresh worktree -> `vendor/hermes-agent/tools/delegate_tool.py` absent | PASS |
| test_wre_skills_discovery::test_initialization | Asserts `repo_root.name == "Foundups-Agent"`; worktree dir is `w6-hxa-policyflags` | PASS |

Not masked with skip/xfail (per scope). No production change required.
Existing PolicyFlags suites re-run clean: 61 passed
(`test_foundup_job_router_policyflags_boundary.py`,
`test_hxa_policyflags_writeback_remediation.py`,
`test_route_foundup_job_live_mode_gate.py`,
`test_hxa24_capability_token_policyflags.py`).

---

## 14. Boundary Proof

- GUARDS ONLY: no production `.py` modified (`git status --porcelain` shows only
  the in-scope test/doc files and the new `wre_gateway/tests/` dir; never
  `.claude/settings.local.json`).
- No dependency added (`hypothesis` NOT used; stdlib `ast` / `itertools` /
  `dataclasses` only).
- No skip/xfail added; no network/model/live-DAE/WRE start.
- Negative controls are 100% synthetic/in-memory (source strings, monkeypatch,
  test-local fakes); no production file was edited or committed to prove a trip.
- No WSP/registry/manifest/CI/config change. No CABR/payout/DAO touch.

---

## 15. Internal Review Verdict

VERDICT: PASS. Six durable regression guards installed for the PolicyFlags trust
chain (#746/#752/#753/#754), each with a proven, SAFE negative control
(fail-when-inverted observed). The wre_gateway module gains its first tests/
directory. No production code changed; no real defect exposed; the five module-
suite failures are pre-existing worktree/submodule artifacts proven green on main.
Chain remains CLOSED with CI coverage now in place.

---

## 16. WSP_97 Truth Boundary Checklist

Declared items: 20 - Rows: 20 - All YES.

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | GUARDS_ONLY_NO_PRODUCTION_CHANGE | YES | Sec 14; git status shows only test/doc files |
| 2 | HOLOINDEX_UTILIZED | YES | Sec 3 (6 queries + top results cited) |
| 3 | EACH_GUARD_NEGATIVE_CONTROL_PROVEN | YES | Sec 5, Sec 7; each fail-when-inverted observed |
| 4 | G1_ALLOWLIST_CORRECT | YES | Sec 6 (3 callers: contract:461/662, router:372); FoundUpJob.from_dict=0 |
| 5 | NO_HYPOTHESIS_DEP | YES | Sec 14; stdlib ast/itertools/dataclasses only |
| 6 | NO_SKIP_XFAIL_ADDED | YES | Sec 13; no skip/xfail introduced |
| 7 | GATEWAY_TESTS_CREATED | YES | new wre_gateway/tests/ (__init__ + G2/G3/G5 file) |
| 8 | WRITEBACK_ORDERING_LOCKED | YES | G6 static (:1521<:1524) + behavioral spy |
| 9 | REASONING_SUMMARY_NOT_PRIVATE_COT | YES | Sec 5 labeled Reasoning Summary; no private scratch reasoning |
| 10 | NEGATIVE_CONTROLS_SAFE_NO_COMMITTED_MUTATION | YES | Sec 7; synthetic only; clean git status |
| 11 | PRODUCTION_CALLER_SCAN_AST_BASED | YES | Sec 9; ast.Call walk, strings/comments excluded |
| 12 | GATEWAY_TESTS_NO_LIVE_EXECUTION | YES | Sec 10; AsyncMock spies + no-import proof |
| 13 | ROUTER_AND_CONTRACT_SANITIZER_CONSISTENCY_CHECKED | YES | G4 consistency test (router == contract for non-dry_run) |
| 14 | REAL_DEFECTS_ESCALATED_NOT_PATCHED | YES | Sec 11; none found; rule documented |
| 15 | CURRENT_MAIN_LINE_NUMBERS_REVERIFIED | YES | Sec 4; all anchors re-derived on 01eb327d9 |
| 16 | NO_DEPENDENCY_CHANGE | YES | Sec 14; no requirements/deps touched |
| 17 | NO_WSP_MUTATION | YES | No WSP file modified |
| 18 | NO_CABR_READY | YES | Not touched |
| 19 | NO_PAYOUT_READY | YES | Not touched |
| 20 | NO_DAO_ACTIVATION | YES | Not touched |

**WSP 97 Truth Boundary Checklist: 20/20 YES.**

---

*Authored by 0102 (Worker-Lane W6) under WSP_00 zen state and WSP_97 Truth
Boundary discipline. Tests/guards-only capstone of the PolicyFlags trust chain
named by #755. Base origin/main @ 01eb327d9. No production code authorized or
changed.*
