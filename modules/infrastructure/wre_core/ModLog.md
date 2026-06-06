# WRE Core - ModLog

## Chronological Change Log

### [2026-06-04] - HERMES_DELEGATE_IMPORT_PATH_REMEDIATION_PHASE1 (W6)

**WSP Protocol References**: WSP 97 (Truth Boundary), WSP 50 (Pre-Action), WSP 22 (ModLog)
**Predecessors**: #757 (HERMES_AGENT_RUNTIME_INSTALL_AND_PATH_AUDIT_PHASE1 - mapped import-path drift,
verdict DRIFT_CONFIRMED_BENIGN_TODAY, recommended Option B: importlib spec_from_file_location)
**Impact Analysis**: TARGETED REMEDIATION. Single production file modified (`hermes_job_executor.py`).
Fixes the `vendor.hermes_agent` (underscore) import-path drift that prevented the real
`vendor/hermes-agent/tools/delegate_tool.py` (hyphenated submodule) from resolving. No dependency added
(importlib.util is stdlib). No default changed. Delegation remains disabled by default.

**Change** - `src/hermes_job_executor.py` (3 changes):
- Added `import importlib.util` to stdlib import block.
- Added `_resolve_vendor_delegate_path()` method: resolves absolute path to vendored delegate_tool.py
  via workspace_root or __file__ ancestry walk. Returns `Path` (caller checks `.is_file()`).
- Added `_load_delegate_task_from_vendor_path()` method: uses `importlib.util.spec_from_file_location`
  + `module_from_spec` + `spec.loader.exec_module` to load from hyphenated vendor path. Validates loaded
  module has callable `delegate_task`. Returns True/False; sets `_import_error` on failure.
- Replaced `_lazy_import_delegate_task` body: removed broken `from vendor.hermes_agent.tools.delegate_tool
  import delegate_task` (underscore path that never resolved). Now delegates to
  `_load_delegate_task_from_vendor_path()`. Lazy-load caching via `_import_attempted` preserved.

**Behavior**: unchanged. `HERMES_DELEGATE_ENABLED` default `"0"` -> SIMULATED before import is attempted.
`dry_run=True` (production singleton) -> SIMULATED before import is attempted. Only the already-unreachable
import path is fixed: when `HERMES_DELEGATE_ENABLED=1` + `dry_run=False`, the import now succeeds
(if vendor file exists) -> `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` (Phase 2 block). If vendor file
missing or has unresolvable dependencies -> `BLOCKED_IMPORT_UNAVAILABLE` (same as before).

**Tests**: new `test_hermes_delegate_import_path.py` (19 passed). Existing executor tests: 94 passed.
Full `wre_core/tests`: 1438 passed, 3 skipped, 2 xfailed.
**Audit**: `docs/audits/architecture/HERMES_DELEGATE_IMPORT_PATH_REMEDIATION_PHASE1.md`.

### [2026-06-03] - HXA_POLICYFLAGS_REGRESSION_GUARDS_PHASE1 (W6)

**WSP Protocol References**: WSP 97 (Truth Boundary), WSP 50 (Pre-Action), WSP 22 (ModLog), WSP 5 (Coverage)
**Predecessors**: #755 (router security chain closeout review, lane W9 - NAMED this guard slice as the
outstanding work); #754 (route-gate live-mode discriminator); #753 (router boundary sanitize + Gate 2
fail-closed); #752 (DAE gateway gate-flags trust-boundary audit); #746/#747 (PolicyFlags write-back-before-guard).
**Impact Analysis**: TESTS/GUARDS ONLY. No production `.py` modified. CI-coverage capstone that locks the
already-CLOSED PolicyFlags trust chain with 6 durable invariant guards. New `wre_gateway/tests/` directory
(the module previously had none). No dependency/CI/WSP/registry/config change; no CABR/payout/DAO touch.

**Guards added** (see `docs/audits/security/HXA_POLICYFLAGS_REGRESSION_GUARDS_PHASE1.md`):
- G1 NO-PRODUCTION-CALLER INVARIANT (AST): `FoundUpJob.from_dict` prod callers = 0; every
  `PolicyFlags.from_dict` prod caller in the 3-entry ALLOWLIST {contract:461 __post_init__, contract:662
  from_dict body, router:372 sanitizer}. AST excludes strings/comments/docstrings (only `ast.Call` nodes);
  tests/archives excluded by path; BOM-tolerant scan. NOT naive count==0 for PolicyFlags (it has 3 legit callers).
- G4 SANITIZATION FUZZ (stdlib, DYNAMIC field enumeration): `dataclasses.fields(PolicyFlags)` at runtime;
  all-True + `itertools.product` combos -> BOTH contract `from_dict().to_dict()` and router
  `_sanitize_untrusted_policy_flags_dict` force every non-`dry_run_mode` field False; every such field in
  `_SERVER_AUTHORED_FLAGS`; router/contract CONSISTENT.
- G6 WRITE-BACK-BEFORE-GUARD ORDERING: static AST source-order (`_writeback_token_verdict` :1521 BEFORE
  `_evaluate_destructive_action_guard` :1524 in `execute()`) AND behavioral spy on both (relative call order).
- G2 GATEWAY VALIDATION AVAILABLE (test-only health, NOT a prod startup assert): `FOUNDUP_JOB_VALIDATION_AVAILABLE is True`.
- G3 GATEWAY E2E D3 FAIL-CLOSED: forged live FoundUpJob envelope (`security_gate_passed=True` +
  `dry_run_mode=False`) is BLOCKED, and `_invoke_core_dae`/`_invoke_foundup_dae` are NOT called
  (blocked BEFORE dispatch); plus structural proof the gateway imports NO execution path.
- G5 GATEWAY PERMISSIVE-FALLBACK: with `FOUNDUP_JOB_VALIDATION_AVAILABLE=False`, degraded behavior bounded
  (FoundUpJob-shaped w/o objective still blocked; even a dispatching generic envelope reaches only the
  pattern-recall stub, never route/execute).

**Negative controls (SAFE, synthetic only - no production mutation)**: G1 synthetic source string; G2/G5
monkeypatch module constant; G3 monkeypatch `_verify_envelope`; G4 test-local fake sanitizer; G6 synthetic
inverted source snippet. Each proven fail-when-inverted. `git status --porcelain` clean of production files.

**Real defect**: NONE found. All 6 guards pass on origin/main @ 01eb327d9; chain remains CLOSED.

**Tests**: focused new files -> 24 passed (14 G1/G4/G6 + 10 G2/G3/G5). Full `wre_core/tests` +
`wre_gateway/tests` -> 1424 passed, 5 failed (PRE-EXISTING, unrelated:
`test_hxa16_real_hermes_delegate_adapter_safe_harness.py` x4 - `vendor/hermes-agent` SUBMODULE not
populated in worktree; `test_wre_skills_discovery.py::test_initialization` - hardcoded repo dir name;
all 5 PASS on a clean main checkout), 3 skipped, 2 xfailed. No skip/xfail added. Existing PolicyFlags
suites re-run clean (61 passed).

**Deferred**: nav-comment hygiene at `foundup_job_consumer.py:27` (wrong filename `hermes_foundup_job_executor.py`;
actual import is `hermes_job_executor.execute_foundup_job`) - out of security-guard scope, not load-bearing.

### [2026-06-03] - FOUNDUP_JOB_ROUTER_ROUTE_GATE_LIVE_MODE_DISCRIMINATOR_PHASE1 (W6)

**WSP Protocol References**: WSP 97 (Truth Boundary), WSP 50 (Pre-Action), WSP 22 (ModLog), WSP 5 (Coverage)
**Predecessors**: #753 (router envelope sanitize + Gate 2 fail-closed  -  this is the sibling it DEFERRED);
#752 (DAE gateway gate-flags trust-boundary audit, decision-only); #744 -> #751 (PolicyFlags write-back context).
**Impact Analysis**: NARROW completion of #753. ROUTE_FOUNDUP_JOB_ONLY  -  only the Policy Check inside
`route_foundup_job` was edited. No gateway/contract/Hermes/validation-seam/config/CI/WSP mutation.

**Change**  -  `src/foundup_job_router.py`, `route_foundup_job` Policy Check (single hunk @ ~:1151):
- Removed the legacy OPT-IN authority condition `security_gate_checked and not security_gate_passed`
  (`security_gate_checked` is telemetry only, never an authority bit).
- Removed the RAW/UNTRUSTED `policy_summary = policy_flags` dict assignment. The `elif isinstance(dict)`
  branch now calls the existing #753 router-local helper
  `_sanitize_untrusted_policy_flags_dict(policy_flags) -> (sanitized, dry_run_defaulted)` (deferred
  `PolicyFlags` import inside the helper -> no new circular dep; `Tuple` import already added by #753).
- Added a live-mode discriminator + FAIL-CLOSED gate:
  `is_live = policy_summary.get("dry_run_mode") is False and not dry_run_defaulted`; if `is_live` and
  `security_gate_passed is not True` -> `BLOCKED_POLICY_GATE` ("Live mode requires security gate passed
  (fail-closed)"). `_make_blocked_envelope(...)` kwargs match the existing signature.

**Object-path asymmetry (by design)**: the `to_dict()` object path keeps `dry_run_defaulted=True`, so it
is NEVER treated as live at the routing seam (a default `dry_run_mode=False` is indistinguishable from
explicit-live; gating it would over-block normal/default/dry-run object routing). Only an explicit-live
RAW-DICT envelope can be live here, and it can never pass the gate because sanitization forces
`security_gate_passed` to False. Strict server-authored live validation remains the VALIDATION seam's job
(`validate_foundup_job_envelope` / `_validate_live_mode_gates`, #753).

**Behavior**: forged-live raw dict (`dry_run_mode=False` + forged `security_gate_passed=True`) is BLOCKED;
raw dict missing `dry_run_mode` stays dry-run and ROUTES (forged flags sanitized away); default/dry-run/
object jobs still ROUTE (no over-block). GENERIC_DAE non-regressed (`route_foundup_job` is not on that path).

**Tests**: new `tests/test_route_foundup_job_live_mode_gate.py` (5 passed). Updated 1 existing test in
`test_foundup_job_router.py` (`test_security_gate_failed_blocks_routing` ->
`test_security_gate_failed_object_path_still_routes`: legacy opt-in block replaced with a STRICTER
object-path-routes assertion; no assertion deleted without a stricter replacement; no skip/xfail). Routing
area (router + boundary + envelope + consumer + new): 176 passed. Full `wre_core/tests`: 1400 passed,
5 failed (PRE-EXISTING, unrelated  -  `test_hxa16_real_hermes_delegate_adapter_safe_harness.py` +
`test_wre_skills_discovery.py`; proven identical on stashed clean origin/main: 5 failed / 34 passed),
3 skipped, 2 xfailed. (Full-suite run mutates `config/WRE_RUNBOOK.md` + `config/wre_defaults.env` as a
pre-existing unrelated test side-effect; reverted  -  NO_CONFIG_CHANGE; routing test files do not mutate config.)
**Audit**: `docs/audits/security/FOUNDUP_JOB_ROUTER_ROUTE_GATE_LIVE_MODE_DISCRIMINATOR_PHASE1.md`.

### [2026-06-02] - FOUNDUP_JOB_ROUTER_POLICYFLAGS_BOUNDARY_SANITIZATION_AND_GATE2_FAILCLOSED_PHASE1 (W6)

**WSP Protocol References**: WSP 97 (Truth Boundary), WSP 50 (Pre-Action), WSP 22 (ModLog), WSP 5 (Coverage)
**Predecessors**: #752 (DAE gateway gate-flags trust-boundary audit, decision-only); #744 -> #746 -> #747 -> #751 (PolicyFlags write-back / `from_dict` chokepoint line)
**Impact Analysis**: Closes the bounded #752 trust-boundary defect at the ROUTER boundary. ROUTER-ONLY; no gateway/Hermes/contract mutation.

**Change** - `src/foundup_job_router.py` (3 changes, locked design):
- **NEW helper** `_sanitize_untrusted_policy_flags_dict(policy_flags) -> Tuple[Dict[str,bool], bool]` (`:337`-region).
  Deferred import of `PolicyFlags` (matches existing `:1073` pattern -> no circular dep). Runs the raw
  envelope dict through `PolicyFlags.from_dict(...).to_dict()` - zeroes ALL `_SERVER_AUTHORED_FLAGS`
  (security/permission/exfoliation/wsp-preflight gates + all capability_token_*), preserving only
  `dry_run_mode`. Restores the router's safe default (`dry_run_mode=True`) when the inbound dict omits
  it (because `from_dict({})` yields `dry_run_mode=False`).
- **Dict branch** (`:420`-region): replaced `policy_snapshot = policy_flags` (RAW - the defect) with
  `policy_snapshot, dry_run_defaulted = _sanitize_untrusted_policy_flags_dict(policy_flags)`; retained the
  `[WSP97] ... missing dry_run_mode - defaulted to True` log. None branch and object branch unchanged.
- **Gate 2 fail-closed** in `_validate_live_mode_gates` (`:587`-region): replaced the
  `if security_gate_checked and not security_gate_passed:` opt-in with `if not security_gate_passed:`
  (`security_gate_checked` retained log-only). Docstring updated to "security_gate_passed=True (required
  in live mode)".

**Behavior**: A raw self-asserted live envelope (e.g. forged `security_gate_passed=True`) is sanitized to
all-gates-False and BLOCKED in live mode. An absent `dry_run_mode` stays SAFE (dry-run, not live). A
legitimate live PASS requires a server-authored `PolicyFlags` object snapshot with
`security_gate_passed=True`. GENERIC_DAE routing is non-regressed.

**Sibling `route_foundup_job` (`:1101`): DEFERRED** - operates on a `FoundUpJob` OBJECT (already
sanitized by the #747 chokepoint) and has NO live-mode discriminator at `:1091-1111`; forcing fail-closed
there would block legitimate dry-run routing. Follow-up: `FOUNDUP_JOB_ROUTER_ROUTE_GATE_LIVE_MODE_DISCRIMINATOR_PHASE1`.

**Tests**: new `tests/test_foundup_job_router_policyflags_boundary.py` (12 passed). Updated 12 existing
tests in `test_foundup_job_envelope_validation.py` to the new fail-closed/sanitized semantics (legitimate
live passes + live-only gate codes exercised directly on `_validate_live_mode_gates` /
`_validate_compute_budget` with server-authored snapshots; no assertion deleted without replacement).
Focused router/envelope/boundary: 140 passed. Full `wre_core/tests`: 1395 passed, 5 failed
(pre-existing, unrelated - `test_hxa16_real_hermes_delegate_adapter_safe_harness.py` x4 + 
`test_wre_skills_discovery.py::test_initialization`; proven identical on clean origin/main), 3 skipped,
2 xfailed.
**Audit**: `docs/audits/security/FOUNDUP_JOB_ROUTER_POLICYFLAGS_BOUNDARY_SANITIZATION_AND_GATE2_FAILCLOSED_PHASE1.md`.

### [2026-06-02] - HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1 (W6)

**WSP Protocol References**: WSP 97 (Truth Boundary), WSP 22 (ModLog), WSP 50 (Pre-Action)
**Predecessors**: #746 (enforcement audit, `GAP_CONFIRMED_BOUNDED`), #744, HXA24/27/30
**Impact Analysis**: Positive-control closure of the #746 PolicyFlags write-back defect (CHANGE 2 of 2).

**Change** - `src/hermes_job_executor.py`:
- Added private helper `_writeback_token_verdict(job, token_validation_result)` (`:1158`).
- Called once in `execute()` (`:1521`), **immediately before** `_evaluate_destructive_action_guard`
  (`:1524`) and after `_validate_token_if_present` (`:1496`) + the invalid-token early-return.
- Writes the server-authored token verdict into `job.policy_flags`:
  `capability_token_checked=True`; `capability_token_present = result is not None`;
  `capability_token_validated = result is not None and result.token_valid`;
  `capability_token_scope_authorized = validated and not result.scope_action_class_mismatch`.
- `security_gate_*` intentionally left at server-default `False` (no security-gate evaluator here; the
  sole writer is the separate `modules/foundups/agent/src/hermes_foundup_job_executor.py:362`). Wiring a
  real security-gate verdict is deferred (future).

**Behavior**: unchanged. No-token/invalid-token -> capability flags not all-True -> D3 BLOCKED;
valid-token -> capability flags True but `security_gate_passed` still False -> D3 still BLOCKED;
D4/D5/D6 unconditionally blocked. **Bypass closed**: a payload pre-setting `capability_token_*=True`
with no real token is still BLOCKED at D3.

**Tests**: `test_hermes_job_executor.py` (94 passed); new
`test_hxa_policyflags_writeback_remediation.py` (13 passed); full `wre_core/tests/` 1383 passed
(5 pre-existing worktree-environmental failures deselected, verified unrelated). HXA4/12/14/16/24/25/28
test helpers updated to supply REAL tokens (forging flags no longer works).
**Audit**: `docs/audits/security/HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1.md`.

### [2026-05-28] - REDDOG_BOOTSTRAP_CONTEXT_RETRIEVAL_PHASE1 (v0.8.42)

**WSP Protocol References**: WSP 00 (Zen State), WSP 60 (Module Memory), WSP 22 (ModLog)
**Impact Analysis**: Adds boot retrieval layer for RedDog session continuity

#### Changes Made

- `tests/test_bootstrap_context_retrieval.py` (NEW - 120 lines):
  - Validates boot retrieval layer wiring
  - TestBootstrapFileExists: BOOTSTRAP.md existence
  - TestBootstrapNamesAllSiblings: All 4 siblings referenced
  - TestAllSiblingFilesExist: Sibling file existence
  - TestWSP00ReferencesBootstrap: WSP_00 references BOOTSTRAP.md
  - TestWSP00MirrorEquality: Framework/Knowledge mirrors byte-identical
  - TestNoSecretPatterns: Secret pattern scan (API keys, tokens, JWTs)
  - TestREADMELinksBootstrap: README.md links BOOTSTRAP.md

#### WSP_knowledge Additions

- `WSP_knowledge/red_dog_external_state/BOOTSTRAP.md` - Boot card with strict read-order
- `WSP_knowledge/red_dog_external_state/MEMORY_BOUNDARY.md` - Curated vs forbidden boundary
- `WSP_knowledge/red_dog_external_state/CURRENT_CONTEXT.md` - Active lanes, HEAD, worker roles
- `WSP_knowledge/red_dog_external_state/WORK_TO_WORK_LINEAGE.md` - PR/slice chain
- `WSP_knowledge/red_dog_external_state/ACTIVE_RESEARCH_THREADS.md` - Open threads with next-action slices

#### WSP_00 Amendment

- Added BOOTSTRAP.md reference in Session Bootstrap Contract section
- Amendment applied to both WSP_framework/src and WSP_knowledge/src mirrors
- Mirrors verified byte-identical

#### Coordination

- Predecessor: PR #724 (REDDOG_SESSION_CONTINUITY_CAPTURE_PHASE1) - storage layer
- Follow-on: REDDOG_BOOTSTRAP_LIVE_UPDATE_PHASE2 (deferred)

#### WSP 97 Compliance

All truth fields remain False. No network calls, no .env reads, no live execution.
Seeded files only (not live auto-update).

### [2026-05-27] - REDDOG_SESSION_CONTINUITY_CAPTURE_PHASE1 (v0.8.41)

**WSP Protocol References**: WSP 60 (Module Memory), WSP 87 (Code Navigation), WSP 22 (ModLog)
**Impact Analysis**: Adds curated session continuity capture for external AI tools

#### Changes Made

- `scripts/validate_session_closeout.py` (NEW - 130 lines):
  - Read-only validator for session closeout JSON files
  - Required field validation (session_id, source, captured_at, lane, work_summary)
  - work_summary length check (max 2000 chars)
  - Secret pattern detection (API keys, OAuth tokens, env vars)
  - Raw transcript marker rejection
  - Exit 0 on valid, non-zero on failure

- `tests/test_validate_session_closeout.py` (NEW - 180 lines):
  - 21 tests covering validator behavior
  - TestRequiredFields: 4 tests for field validation
  - TestSourceValidation: 3 tests for source enum
  - TestWorkSummaryLength: 3 tests for length limits
  - TestSecretDetection: 5 tests for secret patterns
  - TestRawTranscriptDetection: 4 tests for transcript markers
  - TestFullFileValidation: 6 tests for end-to-end validation

#### WSP_knowledge Additions

- `WSP_knowledge/red_dog_external_state/` directory structure
- `WSP_knowledge/red_dog_external_state/README.md` - Human index
- `WSP_knowledge/red_dog_external_state/SCHEMA.md` - JSON schema spec
- `WSP_knowledge/red_dog_external_state/sessions/` - Session files

#### Coordination

- Coordinates with PR #723 (WORKTREE_AUTONOMOUS_ARTIFACT_CLEANUP_DECISION_PHASE1)
- This slice provides curated replacement before raw artifacts untracked

#### WSP 97 Compliance

All truth fields remain False. No network calls, no .env reads, no live execution.

### [2026-05-18] - DESTRUCTIVE_ACTION_GUARD_PATH_CANONICALIZATION_IMPL_PHASE1 (v0.8.40)

**WSP Protocol References**: WSP 97 (Truthful), WSP 50 (Pre-Action), WSP 5 (Coverage)
**Impact Analysis**: P0 symlink traversal fix, P1 control character/Windows case fixes

#### Changes Made

- `src/destructive_action_guard.py` (EXTENDED):
  - Added Section 7: Path Canonicalization Utilities
  - `PathCanonicalizeResult` dataclass for canonicalization results
  - `canonicalize_path()` function with:
    - Control character filtering (ASCII 0x00-0x1F)
    - UNC path blocking (`\\\\`, `//`, `\\\\.\\`, `\\\\?\\`)
    - Symlink resolution via `os.path.realpath()`
    - Windows case normalization via `os.path.normcase()`
  - `PathConstraintValidator` class for symlink-safe path validation

- `tests/test_destructive_action_guard_edge_cases.py` (MODIFIED):
  - Updated tests to use new `PathConstraintValidator`
  - Converted 6 xfails to PASS (symlink, control chars, Windows case)
  - Added legacy gap documentation tests (xfail) for CapabilityToken

#### xfail Changes

| Test | Before | After |
|------|--------|-------|
| `test_null_byte_in_path_blocked` | xfail | PASS |
| `test_newline_in_path_blocked` | xfail | PASS |
| `test_carriage_return_in_path_blocked` | xfail | PASS |
| `test_tab_in_path_blocked` | xfail | PASS |
| `test_drive_case_mismatch_normalized` | xfail | PASS |
| `test_symlink_inside_allowed_pointing_outside_blocked` | xfail | PASS* |

*Symlink test now uses PathConstraintValidator; legacy CapabilityToken gap documented via new xfail.

#### WSP 97 Compliance

All truth fields remain False: `live_execution_allowed`, `repo_created`, `production_source_modified`, `verification_complete`, `cabr_ready`, `payout_ready`.

### [2026-05-15] - DESTRUCTIVE_ACTION_GUARD_EDGE_CASE_TEST_IMPL_PHASE1 (v0.8.39)

**WSP Protocol References**: WSP 97 (Truthful), WSP 50 (Pre-Action), WSP 5 (Coverage)
**Impact Analysis**: Edge case test coverage for destructive action guard path validation

#### Changes Made

- `tests/test_destructive_action_guard_edge_cases.py` (NEW - 626 lines):
  - 12 test classes covering edge cases from PR #613 audit
  - TestDirectoryTraversalBlocked: `../` normalization (3 tests)
  - TestMixedSeparatorHandling: `/` vs `\` normalization (2 tests)
  - TestSymlinkTraversal: Symlink traversal detection (2 tests, xfail - P0 gap)
  - TestWindowsUNCPaths: UNC path blocking (4 tests)
  - TestControlCharactersInPaths: Null/newline/CR/tab handling (4 tests, xfail - P1 gap)
  - TestWindowsDriveCaseNormalization: Drive case sensitivity (2 tests, 1 xfail)
  - TestD3SandboxBoundary: Gate validation for D3 (4 tests)
  - TestWSP97TruthBoundaries: Truth field invariants (4 tests)
  - TestBlockedPathOverride: Blocked paths override allowed (3 tests)
  - TestEmptyAndNullInputs: Edge case inputs (3 tests)
  - TestGuardIntegrationWithPathValidation: Path validation + guard flow (2 tests)

#### Gaps Documented via xfail

```
P0 (Critical):
- Symlink traversal: os.path.normpath does NOT resolve symlinks
  -> Fix in PATH_CANONICALIZATION_IMPL_PHASE1 (use os.path.realpath)

P1 (High):
- Control characters: No explicit blocking for \x00, \n, \r
  -> Fix in CONTROL_CHAR_VALIDATION_IMPL_PHASE1
- Windows drive case: c:\path vs C:\path may bypass path checks
  -> Fix in WINDOWS_DRIVE_NORMALIZATION_IMPL_PHASE1
```

#### Test Results

```
26 passed, 2 skipped, 5 xfailed in 0.36s
Regression: test_hxa22, test_hxa23, test_hxa30 - all passing
```

#### HXA31 Verdict

```
Verdict: DESTRUCTIVE_ACTION_GUARD_EDGE_CASE_TESTS_DEFINED

PR #613 audit findings now have test coverage:
  1. Directory traversal (../) - TESTED, PASSING
  2. Mixed separators (/, \) - TESTED, PASSING  
  3. Symlink traversal - TESTED, XFAIL (gap documented)
  4. UNC paths (\\server\share) - TESTED, PASSING
  5. Control characters - TESTED, XFAIL (gap documented)
  6. Windows drive case - TESTED, XFAIL (gap documented)
  7. D3 gate validation - TESTED, PASSING
  8. WSP 97 truth boundaries - TESTED, PASSING
  9. Blocked path overrides - TESTED, PASSING
  10. Empty/null inputs - TESTED, PASSING
```

---

### [2026-05-13] - HXA30_SCOPE_TO_ACTION_CLASS_HERMES_INTEGRATION_PHASE1 (v0.8.38)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority), WSP 50 (Pre-Action)
**Impact Analysis**: Scope-to-action-class validation integrated into HermesJobExecutor

#### Changes Made

- `src/hermes_job_executor.py` (MODIFIED - ~40 lines):
  - Step 2.2: Classifies action into D0-D6 BEFORE token validation
  - `_validate_token_if_present()`: New `action_class` parameter
  - Passes action_class to token validator for scope authorization
  - Updated decision tree documentation

- `src/capability_token_validator.py` (MODIFIED - ~50 lines):
  - `validate_token()`: New `action_class` parameter
  - Gate 13: Validates token scopes authorize classified action class
  - `SCOPE_DOES_NOT_AUTHORIZE_ACTION_CLASS` reason code
  - `TokenValidationResult`: New fields `scope_action_class_mismatch`, `requested_action_class`

- `tests/test_hxa30_scope_to_action_class_integration.py` (NEW - 400+ lines):
  - 24 tests covering scope-to-action-class integration
  - D3 token + D3/D4/D5/D6 action behavior
  - Token-vs-guard decision ordering
  - Defense-in-depth verification

- `tests/test_hxa27_hermes_token_validation_integration.py` (MODIFIED):
  - Updated `valid_token` fixture with `scopes=["d3:sandbox"]`
  - Updated `test_same_token_blocked_on_replay` with D3 scope
  - Updated `test_d4_blocked_even_with_valid_token` with D4 scope

- `tests/test_hxa29_token_scope_validation.py` (MODIFIED):
  - Updated test expectations for HXA30 behavior (token blocks before guard)

#### HXA30 Verdict

```
Verdict: SCOPE_TO_ACTION_CLASS_HERMES_INTEGRATION_DEFINED

HXA29 verdict was: TOKEN_SCOPE_VALIDATION_DEFINED
HXA30 proves:
  1. Action classified BEFORE token validation (Step 2.2)
  2. Token scopes validated against action class (Gate 13)
  3. D3 token + D4/D5/D6 action -> BLOCKED_BY_TOKEN_VALIDATION
  4. D4/D5/D6 scoped tokens pass validation but guard still blocks
  5. Defense-in-depth: scope layer + guard layer
  6. 335 tests passing (24 HXA30 + 54 HXA29 + 132 HXA28 + 31 HXA27 + 94 executor)
```

---

### [2026-05-12] - HXA29_TOKEN_SCOPE_VALIDATION_PHASE1 (v0.8.37)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority), WSP 50 (Pre-Action)
**Impact Analysis**: Token scope validation against Hermes destructive-action classes

#### Changes Made

- `src/capability_token_validator.py` (MODIFIED - ~80 lines):
  - Added `ACTION_CLASS_SCOPES` constant mapping action classes to authorized scopes
  - Added `SCOPE_TO_ACTION_CLASS` reverse mapping for scope lookup
  - Added `validate_scope_for_action_class()` function for scope-to-class validation
  - D3 scopes (d3:sandbox, d3:evidence, d3:dry-run) authorize ONLY D3 actions
  - D3 scopes do NOT authorize D4/D5/D6 actions (fail-closed)
  - D4/D5/D6 scopes defined but blocked by guard policy
  - Unknown scopes fail closed (return False)

- `tests/test_hxa29_token_scope_validation.py` (NEW - 700+ lines):
  - 54 tests covering scope validation
  - TestScopeConstantsExist (6 tests)
  - TestD3SandboxScopeAuthorizesD3Only (3 tests)
  - TestD3ScopeDoesNotAuthorizeD4 (4 tests)
  - TestD3ScopeDoesNotAuthorizeD5 (4 tests)
  - TestD3ScopeDoesNotAuthorizeD6 (4 tests)
  - TestD4D5D6ScopesDefinedButBlocked (3 tests)
  - TestMissingScopeFailsClosed (2 tests)
  - TestUnknownScopeFailsClosed (2 tests)
  - TestMixedScopesObeyActionClass (2 tests)
  - TestBlockedPathOverridesAllowedScope (1 test)
  - TestPathTraversalBlocked (2 tests)
  - TestDryRunOnlyBlocksLiveExecution (2 tests)
  - TestWSP97TruthFieldsAlwaysFalse (4 tests)
  - TestValidateScopeForActionClass (14 tests)
  - TestHXA29VerdictDocumentation (1 test)

- `docs/audits/openclaw_hermes/HXA29_TOKEN_SCOPE_VALIDATION.md` (NEW):
  - Full audit document with scope mapping tables
  - Fail-closed design documented
  - Defense in depth documented
  - 54 tests passing

#### HXA29 Verdict

```
Verdict: TOKEN_SCOPE_VALIDATION_DEFINED

HXA28 verdict was: D3_NATIVE_CLASSIFICATION_DEFINED

HXA29 proves:
1. D3 sandbox scopes authorize ONLY D3 dry-run/sandbox actions
2. D3 scopes do NOT authorize D4 repo creation
3. D3 scopes do NOT authorize D5 external side effects
4. D3 scopes do NOT authorize D6 irreversible actions
5. D4/D5/D6 scopes defined but blocked by guard policy
6. Missing scope fails closed
7. Unknown scope fails closed
8. Mixed scopes still obey action class restrictions
9. Blocked path overrides allowed scope
10. Path traversal is blocked
11. dry_run_only token blocks live execution
12. All WSP 97 truth fields remain False
13. 362 tests passing across all token/guard test files
```

---

### [2026-05-12] - HXA28_D3_NATIVE_CLASSIFICATION_PHASE1 (v0.8.36)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority), WSP 50 (Pre-Action)
**Impact Analysis**: Native classification hardened for deterministic, explicit D0-D6 hierarchy

#### Changes Made

- `src/hermes_job_executor.py` (MODIFIED - ~80 lines):
  - Enhanced `_classify_destructive_action()` from ~20 to ~100 lines
  - Added explicit prefix-based classification for D0/D1/D2/D5/D6
  - Added exact-match sets for D3 sandbox actions and D4 repo/git actions
  - Unknown/ambiguous actions now fail-closed to D6_IRREVERSIBLE
  - Valid tokens do NOT downgrade D4/D5/D6 classification (immutable)

- `tests/test_hxa28_d3_native_classification.py` (NEW - 600+ lines):
  - 132 tests covering all classification scenarios
  - TestD0ObserveValidateClassification (16 tests)
  - TestD1ReadFetchClassification (12 tests)
  - TestD2SimulatePlanClassification (10 tests)
  - TestD3SandboxWriteClassification (10 tests)
  - TestD4RepoGitOperationsBlocked (24 tests)
  - TestD5ExternalAPIMutationsBlocked (18 tests)
  - TestD6IrreversibleDeleteBlocked (20 tests)
  - TestAmbiguousActionsFailClosed (10 tests)
  - TestTokenDoesNotDowngradeClassification (3 tests)
  - TestWSP97TruthFieldsRemainFalse (4 tests)
  - TestClassificationDeterminism (3 tests)

- `tests/test_hxa23_hermes_guard_integration.py` (MODIFIED):
  - Updated build_foundup expectation from D2 to D3
  - Changed test_extract_action_classified_as_d2 to use simulate_build

- `tests/test_hermes_job_executor.py` (MODIFIED - 15 lines):
  - Changed build_foundup to validate_foundup where guard is not mocked
  - TestEvidenceCollection uses D0 actions now
  - TestNoQueueConsumption uses D0 actions now

- `docs/audits/openclaw_hermes/HXA28_D3_NATIVE_CLASSIFICATION.md` (NEW):
  - Full audit document with classification hierarchy
  - Fail-closed design documented
  - Token immutability documented
  - 260 tests passing

#### HXA28 Verdict

```
Verdict: D3_NATIVE_CLASSIFICATION_DEFINED

HXA27 verdict was: HERMES_TOKEN_VALIDATION_INTEGRATION_DEFINED

HXA28 proves:
1. D0/D1/D2 observe/read/simulate allowed in dry_run mode
2. D3 sandbox writes gated by capability token gates
3. D4/D5/D6 unconditionally blocked in Phase 1
4. Unknown/ambiguous actions fail-closed to D6
5. Valid tokens do NOT downgrade D4/D5/D6 classification
6. Classification is deterministic and explicit (prefix-based)
7. All WSP 97 truth fields remain False
8. 260 tests passing across all guard/classification test files
```

---

### [2026-05-12] - HXA27_HERMES_TOKEN_VALIDATION_INTEGRATION_PHASE1 (v0.8.35)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority), WSP 50 (Pre-Action)
**Impact Analysis**: Token validation integrated into HermesJobExecutor execute() flow

#### Changes Made

- `src/hermes_job_executor.py` (MODIFIED - ~200 lines):
  - Added imports for CapabilityToken, LocalCapabilityTokenValidator, TokenValidationResult
  - Added `BLOCKED_BY_TOKEN_VALIDATION` status to HermesExecutionStatus
  - Added `token_validation_performed` and `token_validation_result` fields to HermesDelegationResult
  - Added `token_validator` parameter to HermesJobExecutor constructor
  - Added `_extract_capability_token()` method for token extraction from payload
  - Added `_validate_token_if_present()` method for token validation
  - Added `_build_token_blocked_result()` method for blocked result construction
  - Updated `execute()` to call token validation at step 2.3 (before guard at step 2.5)
  - Updated all result constructions to include token validation fields

- `tests/test_hxa27_hermes_token_validation_integration.py` (NEW - 500+ lines):
  - 30 tests covering token validation integration
  - TestTokenValidatorInjection (3 tests)
  - TestTokenExtraction (6 tests)
  - TestTokenValidationIntegration (5 tests)
  - TestGuardAfterTokenValidation (2 tests)
  - TestWSP97TruthFields (3 tests)
  - TestResultSerialization (2 tests)
  - TestNonceReplayProtection (1 test)
  - TestD3D4D6Behavior (2 tests)
  - TestHXA27VerdictDocumentation (3 tests)
  - TestModuleImports (3 tests)

- `docs/audits/openclaw_hermes/HXA27_HERMES_TOKEN_VALIDATION_INTEGRATION.md` (NEW):
  - Full audit document with WSP 97 truth table
  - Integration architecture documented
  - Token failure behavior documented
  - D3/D4-D6 behavior documented

#### HXA27 Verdict

```
Verdict: HERMES_TOKEN_VALIDATION_INTEGRATION_DEFINED

HXA26 verdict was: TOKEN_VALIDATION_SERVICE_DEFINED

HXA27 proves:
1. Token validator is injectable into HermesJobExecutor constructor
2. Default validator used when none injected
3. Token extraction works from job payload (dict or instance)
4. Token validation performed before guard evaluation (step 2.3)
5. Invalid token blocks execution immediately (BLOCKED_BY_TOKEN_VALIDATION)
6. Valid token allows execution to proceed
7. No token in payload = no token validation performed
8. Nonce replay protection prevents token reuse
9. All WSP 97 truth fields remain False
10. Result includes token_validation_performed and token_validation_result
```

#### Token Validation Flow

```
execute(job):
  Step 1: Validate job structure
  Step 2: Build delegation request
  Step 2.3 [HXA27]: Validate capability token if present
    - If token present and invalid -> BLOCKED_BY_TOKEN_VALIDATION (guard NOT evaluated)
    - If token present and valid -> proceed (token_validation_result set)
    - If no token -> proceed (token_validation_performed = False)
  Step 2.5 [HXA23]: Evaluate destructive action guard
    - If blocked -> BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
    - If allowed -> proceed
  Steps 3-7: ... existing flow ...
```

#### What HXA27 Does NOT Prove

- Real JWT/OAuth token validation (Phase 1 is fake verification)
- External token service integration (local validator only)
- Production token issuance (test infrastructure only)
- Live operation authorization (Phase 1 is dry-run only)
- Token revocation (not implemented)

---

### [2026-05-12] - HXA26_TOKEN_VALIDATION_SERVICE_PHASE1 (v0.8.34)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority), WSP 50 (Pre-Action)
**Impact Analysis**: Production-ready capability token validation service module created

#### Changes Made

- `src/capability_token_validator.py` (NEW - 500+ lines):
  - TokenValidationReasonCode enum with all validation failure codes
  - CapabilityToken dataclass (from HXA21 test file)
  - TokenValidationResult dataclass with WSP 97 truth fields
  - ICapabilityTokenValidator protocol (interface for future implementations)
  - LocalCapabilityTokenValidator class with 12 validation gates
  - LocalCapabilityTokenIssuer class for test infrastructure
  - get_default_validator() singleton accessor
  - reset_default_validator() for testing

- `tests/test_hxa26_token_validation_service.py` (NEW - 500+ lines):
  - 52 tests covering token validation service
  - TestCapabilityTokenModel (11 tests)
  - TestTokenRedaction (2 tests)
  - TestTokenValidationResult (3 tests)
  - TestLocalCapabilityTokenValidator (15 tests)
  - TestValidatorNonceRegistry (3 tests)
  - TestLocalCapabilityTokenIssuer (3 tests)
  - TestDefaultValidator (3 tests)
  - TestWSP97TruthBoundaries (4 tests)
  - TestValidatorIntegration (2 tests)
  - TestHXA26Verdict (1 test)
  - TestModuleImports (5 tests)

- `docs/audits/openclaw_hermes/HXA26_TOKEN_VALIDATION_SERVICE.md` (NEW):
  - Full audit document with WSP 97 truth table
  - Module structure documented
  - 12 validation gates documented
  - Integration path documented

#### HXA26 Verdict

```
Verdict: TOKEN_VALIDATION_SERVICE_DEFINED

HXA25 verdict was: D3_SANDBOX_EXECUTION_DEFINED

HXA26 proves:
1. CapabilityToken model in production code
2. TokenValidationResult in production code
3. ICapabilityTokenValidator protocol for injection
4. LocalCapabilityTokenValidator with 12 validation gates
5. LocalCapabilityTokenIssuer for test infrastructure
6. Nonce registry prevents replay attacks
7. Token redaction protects security logging
8. All WSP 97 truth fields remain False
9. Module can be imported by production code
```

#### What HXA26 Does NOT Prove

- Real JWT/OAuth implementation (Phase 1 is fake verification)
- Real signing key management (no real keys)
- External token service integration (local only)
- Production token issuance (test infrastructure only)
- HermesJobExecutor integration (future slice)

---

### [2026-05-12] - HXA25_D3_SANDBOX_EXECUTION_PHASE1 (v0.8.33)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority), WSP 50 (Pre-Action)
**Impact Analysis**: D3 sandbox dry-run execution proven functional with evidence when all gates pass

#### Changes Made

- `tests/test_hxa25_d3_sandbox_execution.py` (NEW - 600+ lines):
  - 24 tests covering D3 sandbox execution behaviors
  - Tests D3 blocked by default (missing gates)
  - Tests D3 blocked without capability token flags
  - Tests D3 blocked if token not validated
  - Tests D3 blocked if scope not authorized
  - Tests D3 blocked without workspace binding
  - Tests D3 blocked without path constraints
  - Tests D3 allowed as dry-run when all gates true
  - Tests allowed D3 writes evidence only
  - Tests allowed D3 does not call live delegate
  - Tests allowed D3 does not create repo
  - Tests allowed D3 does not modify production source
  - Tests D4/D5/D6 blocked even with all gates
  - Tests blocked result keeps truth fields false

- `docs/audits/openclaw_hermes/HXA25_D3_SANDBOX_EXECUTION.md` (NEW):
  - Full audit document with WSP 97 truth table
  - D3 allow conditions documented
  - Evidence behavior documented

#### HXA25 Verdict

```
Verdict: D3_SANDBOX_EXECUTION_DEFINED

HXA24 verdict was: CAPABILITY_TOKEN_POLICYFLAGS_DEFINED

HXA25 proves:
1. D3 sandbox blocked by default (no capability token flags)
2. D3 sandbox blocked without capability token flags
3. D3 sandbox blocked if token checked/present but not validated
4. D3 sandbox blocked if token scope not authorized
5. D3 sandbox blocked without workspace binding
6. D3 sandbox blocked without path constraints
7. D3 sandbox allowed as dry-run when all gates true
8. Allowed D3 writes evidence/checkpoint only
9. Allowed D3 does not call live external delegate
10. Allowed D3 does not create repo
11. Allowed D3 does not modify production source
12. Allowed D3 does not set real_execution_performed True
13. D4/D5/D6 blocked even with all gates true
14. Blocked result keeps truth fields false
15. All WSP 97 truth fields remain False
```

#### D3 Allow Conditions

D3 sandbox dry-run is allowed when ALL of:
- capability_token_checked = True
- capability_token_present = True
- capability_token_validated = True
- capability_token_scope_authorized = True
- security_gate_passed = True
- workspace_binding_enforced = True
- path_constraints_validated = True
- dry_run_mode = True

When allowed: Status=SIMULATED, Evidence written to `.hermes_evidence/`, No live execution.

---

### [2026-05-12] - HXA24_CAPABILITY_TOKEN_POLICYFLAGS_PHASE1 (v0.8.32)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority), WSP 50 (Pre-Action)
**Impact Analysis**: Capability token policy flags added to PolicyFlags; HermesJobExecutor reads them

#### Changes Made

- `src/hermes_job_executor.py` (MODIFIED - ~25 lines):
  - Updated `_build_destructive_action_request()` to read capability token flags from PolicyFlags
  - Conservative logic: `capability_token_present` for guard requires ALL four flags True:
    - `policy_flags.capability_token_checked`
    - `policy_flags.capability_token_present`
    - `policy_flags.capability_token_validated`
    - `policy_flags.capability_token_scope_authorized`
  - Updated action_id prefix from `hxa23_` to `hxa24_`
  - Updated docstring to document HXA24 gate field mappings

- `tests/test_hxa24_capability_token_policyflags.py` (NEW - 500+ lines):
  - 31 tests covering capability token policy flag behaviors
  - Tests default flags block D3
  - Tests partial flags block D3
  - Tests all four True allows D3 sandbox dry-run
  - Tests D4/D5/D6 still blocked with tokens
  - Tests WSP 97 truth fields preserved
  - Tests guard request construction

#### HXA24 Verdict

```
Verdict: CAPABILITY_TOKEN_POLICYFLAGS_DEFINED

HXA23 verdict was: HERMES_GUARD_INTEGRATION_DEFINED

HXA24 proves:
1. PolicyFlags has capability_token_checked (default False)
2. PolicyFlags has capability_token_present (default False)
3. PolicyFlags has capability_token_validated (default False)
4. PolicyFlags has capability_token_scope_authorized (default False)
5. to_dict() includes all four fields
6. from_dict() restores all four fields (backward compat)
7. Guard reads capability token flags from PolicyFlags
8. Default flags block D3 (capability_token_present=False for guard)
9. Partial flags block D3 (any missing flag = False for guard)
10. All four True allows D3 sandbox dry-run
11. D4/D5/D6 still blocked even with all tokens
12. All WSP 97 truth fields remain False
```

#### HXA24 Capability Token Logic

For guard to receive `capability_token_present=True`, ALL four must be True:
```python
capability_token_present_for_guard = (
    policy_flags.capability_token_checked
    and policy_flags.capability_token_present
    and policy_flags.capability_token_validated
    and policy_flags.capability_token_scope_authorized
)
```

This conservative interpretation ensures D3+ operations remain blocked unless all token gates pass.

---

### [2026-05-12] - HXA23_HERMES_GUARD_INTEGRATION_PHASE1 (v0.8.31)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority), WSP 50 (Pre-Action)
**Impact Analysis**: Integration of HXA22 destructive action guard into HermesJobExecutor as safe no-op validation seam

#### Changes Made

- `src/hermes_job_executor.py` (MODIFIED - ~150 lines added):
  - Imported `DestructiveActionClass`, `DestructiveActionGuardResult`, `DestructiveActionRequest`, `evaluate_destructive_action` from destructive_action_guard
  - Added `BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD` to `HermesExecutionStatus` enum
  - Added `guard_evaluated` and `guard_result` fields to `HermesDelegationResult`
  - Added `_classify_destructive_action()` method - classifies job actions to D0-D2 in Phase 1
  - Added `_build_destructive_action_request()` method - builds guard request from job
  - Added `_evaluate_destructive_action_guard()` method - calls guard evaluation
  - Modified `execute()` method to evaluate guard before delegation paths
  - Guard blocks D4/D5/D6 actions; allows D0/D1/D2 to continue to SIMULATED

- `tests/test_hxa23_hermes_guard_integration.py` (NEW - 800+ lines):
  - 34 tests covering guard integration behaviors
  - Tests D0/D1/D2 allowed as dry-run
  - Tests D4/D5/D6 blocked by guard
  - Tests WSP 97 truth fields preserved
  - Tests existing dry-run behavior preserved

- `tests/test_hermes_job_executor.py` (MODIFIED - 3 tests updated):
  - Updated tests to mock guard for non-dry-run paths
  - Tests now bypass guard to test downstream blocking behavior

#### HXA23 Verdict

```
Verdict: HERMES_GUARD_INTEGRATION_DEFINED

HXA22 verdict was: DESTRUCTIVE_ACTION_GUARD_RUNTIME_DEFINED

HXA23 proves:
1. HermesJobExecutor integrates DestructiveActionGuard
2. Guard is evaluated before delegation paths
3. Guard result is stored in HermesDelegationResult
4. D0/D1/D2 allowed as dry-run only (D3 deferred - requires capability tokens)
5. D4 repo write blocked by guard
6. D5 external side effect blocked by guard
7. D6 irreversible blocked by guard
8. Blocked guard does not call delegate adapter
9. All WSP 97 truth fields remain False
10. Existing dry-run behavior preserved
```

#### HXA23 Action Classification (Phase 1)

| Action Pattern | Class | Phase 1 Behavior |
|----------------|-------|------------------|
| `validate_*` | D0_OBSERVE | Allowed (dry-run) |
| `queue_*` | D0_OBSERVE | Allowed (dry-run) |
| `build_*` | D2_SIMULATE | Allowed (dry-run) |
| `extract_*` | D2_SIMULATE | Allowed (dry-run) |
| Other | D2_SIMULATE | Allowed (dry-run) |

Note: D3 classification deferred - requires capability_token_present in PolicyFlags.

#### HXA23 WSP 97 Truth Fields (All False)

| Field | Value | Reason |
|-------|-------|--------|
| `live_external_delegate_called` | False | No external delegation |
| `repo_created` | False | No GitHub operations |
| `production_source_modified` | False | No source modifications |
| `external_federation_initiated` | False | No federation |
| `real_execution_performed` | False | Phase 1: no live execution |
| `verification_complete` | False | No CABR verification |
| `cabr_ready` | False | No CABR pipeline |
| `payout_ready` | False | No payout pipeline |

---

### [2026-05-12] - HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME_PHASE1 (v0.8.30)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority), WSP 50 (Pre-Action)
**Impact Analysis**: Minimal runtime guard seam for destructive actions; test-only, fail-closed

#### Changes Made

- `src/destructive_action_guard.py` (NEW - 450+ lines):
  - `DestructiveActionClass`: Enum defining D0-D6 action classes
  - `GuardDecision`: Enum for guard decisions (ALLOW_DRY_RUN, BLOCKED, REQUIRES_APPROVAL)
  - `GuardBlockReasonCode`: Enum for block reason codes (15 codes)
  - `DestructiveActionRequest`: Request dataclass capturing all gate requirements
  - `DestructiveActionGuardResult`: Result dataclass with all WSP 97 truth fields
  - `DestructiveActionGuard`: Fail-closed evaluator for destructive actions
  - Convenience functions: `get_destructive_action_guard()`, `evaluate_destructive_action()`

- `tests/test_hxa22_destructive_action_guard_runtime.py` (NEW - 700+ lines):
  - 40 tests covering all fail-closed behaviors
  - No live execution enabled - all WSP 97 truth fields remain False

#### HXA22 Verdict

```
Verdict: DESTRUCTIVE_ACTION_GUARD_RUNTIME_DEFINED

HXA19 verdict was: REPO_CREATION_APPROVAL_GATE_DEFINED
HXA20 verdict was: PRODUCTION_SOURCE_GATE_DEFINED
HXA21 verdict was: CAPABILITY_TOKEN_INFRASTRUCTURE_DEFINED

HXA22 proves:
1. DestructiveActionClass enum defines D0-D6 classes
2. DestructiveActionRequest captures all gate requirements
3. DestructiveActionGuardResult captures all WSP 97 truth fields
4. DestructiveActionGuard implements fail-closed evaluation
5. D0/D1/D2 allowed only in dry-run mode
6. D3 requires workspace_binding, path_validation, capability_token, security_gate
7. D4/D5/D6 blocked in Phase 1
8. All WSP 97 truth fields remain False always
```

#### HXA22 Fail-Closed Rules

| Action Class | Phase 1 Behavior | Required Gates |
|--------------|------------------|----------------|
| D0_OBSERVE | Allowed (dry-run only) | dry_run_mode=True |
| D1_READ | Allowed (dry-run only) | dry_run_mode=True |
| D2_SIMULATE | Allowed (dry-run only) | dry_run_mode=True |
| D3_WRITE_SANDBOX | Allowed when all gates pass | workspace_binding, path_validation, capability_token, security_gate |
| D4_WRITE_REPO | BLOCKED | - |
| D5_EXTERNAL_SIDE_EFFECT | BLOCKED | - |
| D6_IRREVERSIBLE | BLOCKED | - |

#### HXA22 WSP 97 Truth Fields (All False)

| Field | Value | Reason |
|-------|-------|--------|
| `live_execution_allowed` | False | Phase 1: no live execution |
| `repo_created` | False | No GitHub operations |
| `production_source_modified` | False | No source modifications |
| `external_federation_initiated` | False | No federation |
| `verification_complete` | False | No CABR verification |
| `cabr_ready` | False | No CABR pipeline |
| `payout_ready` | False | No payout pipeline |

---

### [2026-05-12] - HXA21_CAPABILITY_TOKEN_INFRASTRUCTURE_PHASE1 (v0.8.29)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority), WSP 50 (Pre-Action)
**Impact Analysis**: Safe local capability token model and validation for future gates

#### Changes Made

- `tests/test_hxa21_capability_token_infrastructure.py` (NEW - 800+ lines):
  - 42 tests covering capability token model and validation contract
  - No production code modified - test-only token infrastructure
  - Test-local definitions for:
    - `CapabilityToken`: Token model with all required fields
    - `TokenValidationReasonCode`: Enum of validation failure reasons (15 codes)
    - `TokenValidationResult`: Validation result with all failure details
    - `FakeTokenIssuer`: Test fixture that issues fake tokens (no real secrets)
    - `FakeTokenValidator`: Test fixture with in-memory nonce registry
    - `WSP97TruthTracker`: Truth field tracker for validation

#### HXA21 Verdict

```
Verdict: CAPABILITY_TOKEN_INFRASTRUCTURE_DEFINED

HXA19 verdict was: REPO_CREATION_APPROVAL_GATE_DEFINED
HXA20 verdict was: PRODUCTION_SOURCE_GATE_DEFINED

HXA21 proves:
1. CapabilityToken model defines all required fields
2. TokenValidationResult defines all validation outputs
3. FakeTokenIssuer creates test tokens (no real secrets)
4. FakeTokenValidator validates all gates (fail-closed)
5. In-memory nonce registry prevents replay
6. Token redaction works for security logging
7. All WSP 97 truth fields remain False
```

#### HXA21 Token Model Fields

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `token_id` | str | - | Unique token identifier |
| `issuer` | str | - | Token issuer identity |
| `subject` | str | - | Token subject |
| `audience` | str | - | Intended audience |
| `scopes` | List[str] | [] | Granted scopes |
| `allowed_actions` | List[str] | [] | Allowed actions |
| `allowed_paths` | List[str] | [] | Allowed path roots |
| `blocked_paths` | List[str] | [] | Blocked paths |
| `dry_run_only` | bool | True | Safe default |
| `issued_at` | datetime | now() | Issuance timestamp |
| `expires_at` | Optional[datetime] | None | Expiration timestamp |
| `nonce` | str | random | Replay protection |
| `signature_present` | bool | False | Signature exists |
| `signature_verified` | bool | False | Signature verified |

#### HXA21 Validation Failure Modes (Fail-Closed)

| Condition | Reason Code | Test Status |
|-----------|-------------|-------------|
| Missing token | `MISSING_TOKEN` | PASS |
| Missing signature | `MISSING_SIGNATURE` | PASS |
| Unverified signature | `SIGNATURE_NOT_VERIFIED` | PASS |
| Expired token | `TOKEN_EXPIRED` | PASS |
| Wrong audience | `WRONG_AUDIENCE` | PASS |
| Replayed nonce | `REPLAY_DETECTED` | PASS |
| Action not allowed | `ACTION_NOT_ALLOWED` | PASS |
| Scope not allowed | `SCOPE_NOT_ALLOWED` | PASS |
| Path outside allowed | `PATH_OUTSIDE_ALLOWED_ROOTS` | PASS |
| Blocked path | `PATH_IN_BLOCKED_LIST` | PASS |
| Dry-run blocks live | `DRY_RUN_ONLY_BLOCKS_LIVE` | PASS |

#### HXA21 WSP 97 Truth Fields (All False)

| Field | Value | Reason |
|-------|-------|--------|
| `repo_created` | False | No GitHub operations |
| `production_source_modified` | False | No source modifications |
| `network_called` | False | No network calls |
| `live_external_delegate_called` | False | No external delegation |
| `external_federation_initiated` | False | No federation |
| `verification_complete` | False | No CABR verification |
| `cabr_ready` | False | No CABR pipeline |
| `payout_ready` | False | No payout pipeline |

---

### [2026-05-12] - HXA20_PRODUCTION_SOURCE_GATE_PHASE1 (v0.8.28)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority), WSP 50 (Pre-Action)
**Impact Analysis**: Safe fail-closed gate contract for future production source modification paths

#### Changes Made

- `tests/test_hxa20_production_source_gate.py` (NEW - 650+ lines):
  - 32 tests covering production source modification gate contract
  - No production code modified - test-only approval model
  - Test-local definitions for:
    - `ProductionSourceGate`: Gate model with all required fields
    - `ProductionSourceBlockReason`: Enum of blocking reasons (10 conditions)
    - `ProductionSourceGateResult`: Enum of gate results (BLOCKED, SIMULATED_ONLY)
    - `DestructiveClass`: D0-D6 destructive action classification
    - `FakePatchAdapter`: Test fixture that never modifies production source
    - `FakePatchAdapterResult`: Result type with WSP 97 fields

#### HXA20 Verdict

```
Verdict: PRODUCTION_SOURCE_GATE_DEFINED

HXA19 verdict was: REPO_CREATION_APPROVAL_GATE_DEFINED

HXA20 proves:
1. ProductionSourceGate model defines all required fields
2. All blocking conditions are implemented (fail-closed)
3. Dry-run simulation path works correctly
4. FakePatchAdapter never modifies production source
5. All WSP 97 truth fields remain False
6. Gate can be evaluated without modifying production
```

#### HXA20 Gate Model Fields

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `source_modification_requested` | bool | False | Request flag |
| `target_path` | str | "" | Target file path |
| `operation` | str | "" | File operation |
| `human_approval` | bool | False | Human approval gate |
| `approval_id` | Optional[str] | None | Approval correlation ID |
| `capability_token_present` | bool | False | Token gate |
| `security_gate_passed` | bool | False | Security gate |
| `destructive_class` | DestructiveClass | D0_OBSERVE | Action classification |
| `dry_run_mode` | bool | True | Safe default |
| `workspace_binding_enforced` | bool | False | Workspace binding gate |
| `path_constraints_validated` | bool | False | Path constraint gate |
| `allowed_roots` | List[str] | [] | Allowed path roots |
| `blocked_paths` | List[str] | [] | Blocked path patterns |

#### HXA20 Block Conditions Tested

| Condition | Block Reason | Test Status |
|-----------|--------------|-------------|
| Missing human approval | `MISSING_HUMAN_APPROVAL` | PASS |
| Missing capability token | `MISSING_CAPABILITY_TOKEN` | PASS |
| Security gate not passed | `SECURITY_GATE_NOT_PASSED` | PASS |
| Target path outside allowed roots | `TARGET_PATH_OUTSIDE_ALLOWED_ROOTS` | PASS |
| Target path in blocked paths | `TARGET_PATH_IN_BLOCKED_PATHS` | PASS |
| Workspace binding not enforced | `WORKSPACE_BINDING_NOT_ENFORCED` | PASS |
| Path constraints not validated | `PATH_CONSTRAINTS_NOT_VALIDATED` | PASS |
| Unsupported operation | `UNSUPPORTED_OPERATION` | PASS |
| Destructive class above threshold | `DESTRUCTIVE_CLASS_ABOVE_THRESHOLD` | PASS |
| Dry-run mode active | `SIMULATED_ONLY` | PASS |

#### HXA20 WSP 97 Truth Fields (All False)

| Field | Value | Reason |
|-------|-------|--------|
| `production_source_modified` | False | No file modifications |
| `file_written` | False | No file writes |
| `network_called` | False | No network calls |
| `repo_created` | False | No GitHub operations |
| `live_external_delegate_called` | False | No external delegation |
| `external_federation_initiated` | False | No federation |
| `verification_complete` | False | No CABR verification |
| `cabr_ready` | False | No CABR pipeline |
| `payout_ready` | False | No payout pipeline |

---

### [2026-05-12] - HXA19_REPO_CREATION_APPROVAL_GATE_PHASE1 (v0.8.27)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority), WSP 50 (Pre-Action)
**Impact Analysis**: Safe approval gate contract for future repo creation paths

#### Changes Made

- `tests/test_hxa19_repo_creation_approval_gate.py` (NEW - 580 lines):
  - 35 tests covering repo creation approval gate contract
  - No production code modified - test-only approval model
  - Test-local definitions for:
    - `RepoCreationApproval`: Approval model with all required fields
    - `RepoCreationBlockReason`: Enum of blocking reasons
    - `RepoCreationGateResult`: Enum of gate results
    - `FakeRepoAdapter`: Test fixture that never creates repos
    - `FakeRepoAdapterResult`: Result type with WSP 97 fields

#### HXA19 Verdict

```
Verdict: REPO_CREATION_APPROVAL_GATE_DEFINED

HXA18 verdict was: RUNTIME_FIXTURE_HARNESS_SATISFIES_MISSING_SURFACE

HXA19 proves:
1. RepoCreationApproval model defines all required fields
2. All blocking conditions are implemented (fail-closed)
3. Dry-run approval path works correctly
4. FakeRepoAdapter never calls network or creates repos
5. All WSP 97 truth fields remain False
6. Gate can be evaluated without creating repos
```

#### HXA19 Approval Gate Fields

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `repo_creation_requested` | bool | False | Request flag |
| `repo_name` | str | "" | Target repo name |
| `target_org` | str | "" | Target GitHub org |
| `human_approval` | bool | False | Human approval gate |
| `approval_id` | Optional[str] | None | Approval correlation ID |
| `capability_token_present` | bool | False | Token gate |
| `security_gate_passed` | bool | False | Security gate |
| `dry_run_mode` | bool | True | Safe default |
| `approval_expires_at` | Optional[datetime] | None | Temporal validity |

#### HXA19 Block Conditions Tested

| Condition | Block Reason | Test Status |
|-----------|--------------|-------------|
| Missing human approval | `MISSING_HUMAN_APPROVAL` | PASS |
| Missing capability token | `MISSING_CAPABILITY_TOKEN` | PASS |
| Security gate not passed | `SECURITY_GATE_NOT_PASSED` | PASS |
| Approval expired | `APPROVAL_EXPIRED` | PASS |
| Org not allowlisted | `TARGET_ORG_NOT_ALLOWLISTED` | PASS |
| Repo name invalid | `REPO_NAME_INVALID` | PASS |
| Dry-run mode active | `APPROVED_DRY_RUN_ONLY` | PASS |

#### HXA19 WSP 97 Truth Fields (All False)

| Field | Value | Reason |
|-------|-------|--------|
| `repo_created` | False | No GitHub operations |
| `network_called` | False | No network calls |
| `production_source_modified` | False | Test-only code |
| `live_external_delegate_called` | False | No external delegation |
| `external_federation_initiated` | False | No federation |
| `verification_complete` | False | No CABR verification |
| `cabr_ready` | False | No CABR pipeline |
| `payout_ready` | False | No payout pipeline |

---

### [2026-05-12] - HXA18_HERMES_RUNTIME_FIXTURE_SAFE_HARNESS_PHASE1 (v0.8.26)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority)
**Impact Analysis**: Safe local runtime fixture objects satisfy missing Hermes runtime surface

#### Changes Made

- `tests/test_hxa18_hermes_runtime_fixture_safe_harness.py` (NEW - 620 lines):
  - 35 tests covering safe local fixture harness for Hermes runtime objects
  - No production code modified - test-only fixture objects
  - Safe local fixture objects for:
    - `FakeHermesParentAgent`: Satisfies parent_agent interface
    - `FakeToolsetRegistry`: Satisfies toolsets interface (read-only)
    - `RedactedCredentials`: Satisfies credentials interface (redacted placeholders)
    - `InMemoryTerminalSessions`: Satisfies terminal_sessions interface
    - `FakeDelegateAdapter`: Records calls without real delegation
    - `HermesRuntimeFixture`: Bundles all fixtures for safe invocation

#### HXA18 Verdict

```
Verdict: RUNTIME_FIXTURE_HARNESS_SATISFIES_MISSING_SURFACE

HXA17 verdict was: DELEGATE_ADAPTER_CONFIRMED_RUNTIME_OBJECTS_MISSING

HXA18 proves:
1. FakeHermesParentAgent satisfies parent_agent interface
2. FakeToolsetRegistry satisfies toolsets interface
3. RedactedCredentials satisfies credentials interface
4. InMemoryTerminalSessions satisfies terminal_sessions interface
5. FakeDelegateAdapter can be invoked with all fixture objects
6. All safety boundaries maintained (no real calls, no repo, no production)
```

#### HXA18 WSP 97 Truth Fields (All Safe)

| Field | Value | Reason |
|-------|-------|--------|
| `real_delegate_adapter_invoked` | True | For local fake adapter only |
| `live_external_delegate_called` | False | No real external delegation |
| `repo_created` | False | No GitHub operations |
| `production_source_modified` | False | No production writes |
| `external_federation_initiated` | False | No federation |
| `production_readiness_claimed` | False | Not claimed |
| `real_execution_performed` | False | Test fixtures only |
| `verification_complete` | False | No CABR verification |
| `cabr_ready` | False | No CABR pipeline |
| `payout_ready` | False | No payout pipeline |

#### Test Classes (35 tests)

| Class | Tests | Purpose |
|-------|-------|---------|
| `TestRuntimeFixtureSuppliesParentAgent` | 5 | FakeHermesParentAgent works |
| `TestRuntimeFixtureSuppliesToolsets` | 4 | FakeToolsetRegistry works |
| `TestRuntimeFixtureUsesRedactedCredentialsOnly` | 6 | RedactedCredentials safe |
| `TestRuntimeFixtureUsesInMemoryTerminalSessions` | 4 | InMemoryTerminalSessions works |
| `TestSafeDelegateAdapterInvoked` | 3 | FakeDelegateAdapter invokable |
| `TestLiveExternalDelegateCalledFalse` | 2 | No live external calls |
| `TestRepoCreatedFalse` | 2 | No repo creation |
| `TestProductionSourceModifiedFalse` | 2 | No production modification |
| `TestNoNetworkOrRealCredentials` | 2 | No network/real credentials |
| `TestEvidenceOrCheckpointTruthFieldsPreserved` | 2 | WSP 97 fields preserved |
| `TestHXA18CompleteFixtureHarness` | 2 | Integration proof |
| `TestHXA18VerdictDocumentation` | 1 | Verdict documented |

---

### [2026-05-10] - HXA16_REAL_HERMES_DELEGATE_ADAPTER_SAFE_HARNESS_PHASE1 (v0.8.25)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority)
**Impact Analysis**: Real delegate adapter boundary proven without external call

#### Changes Made

- `src/hermes_job_executor.py`:
  - Added `DELEGATE_ADAPTER_BOUNDARY_PROVEN` to `HermesExecutionStatus` enum
  - Added HXA16 truth fields to `HermesDelegationResult`:
    - `real_delegate_adapter_invoked`
    - `external_federation_initiated`
    - `production_readiness_claimed`
  - Added `real_delegate_adapter` parameter to `HermesJobExecutor.__init__()`
  - Added `_execute_real_delegate_adapter()` method for adapter boundary proof
  - Added `_write_adapter_boundary_evidence()` method for evidence generation
  - Updated `execute()` to handle `real_delegate_adapter` mode within controlled harness

- `tests/test_hxa16_real_hermes_delegate_adapter_safe_harness.py` (NEW - 340 lines):
  - 14 tests covering adapter boundary requirements:
    - Real delegate interface exists (delegate_tool.py)
    - Interface requirements documented (parent_agent, toolsets, etc.)
    - Adapter boundary proven via controlled harness
    - External call not enabled (requires full Hermes runtime)
    - Evidence files generated

#### HXA16 Verdict

```
Verdict: DELEGATE_ADAPTER_BOUNDARY_PROVEN_EXTERNAL_CALL_NOT_ENABLED

Rationale:
- vendor/hermes-agent/tools/delegate_tool.py EXISTS
- delegate_task() requires parent_agent (AIAgent instance)
- AIAgent requires full Hermes runtime infrastructure
- Cannot safely instantiate without production risk
- Adapter boundary CAN be proven without external call
```

#### HXA16 Truth Fields Added

| Field | Description |
|-------|-------------|
| `real_delegate_adapter_invoked` | True if adapter boundary was reached |
| `external_federation_initiated` | True ONLY if external federation started |
| `production_readiness_claimed` | True ONLY if production readiness asserted |

#### Evidence Files Generated

- `adapter_boundary_proof.json`: verdict, rationale, interface documentation
- `delegate_interface_requirements.json`: parent_agent, toolsets, credentials, etc.

---

### [2026-05-12] - HXA14_CONTROLLED_LIVE_HERMES_DELEGATION_HARNESS_PHASE1 (v0.8.24)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority)
**Impact Analysis**: Controlled live delegation harness for test-only explicit opt-in

#### Changes Made

- `src/hermes_job_executor.py`:
  - Added `CONTROLLED_HARNESS_EXECUTED` to `HermesExecutionStatus` enum
  - Added HXA14 truth fields to `HermesDelegationResult`:
    - `controlled_delegate_invoked`
    - `live_external_delegate_called`
    - `repo_created`
    - `production_source_modified`
    - `external_federation_ready`
    - `production_ready`
  - Added `controlled_harness` parameter to `HermesJobExecutor.__init__()`
  - Added `_execute_controlled_delegate()` method for test harness execution
  - Updated `execute()` to check `controlled_harness` flag before feature flag

- `tests/test_hxa14_controlled_live_hermes_harness.py` (NEW - 520 lines):
  - 22 tests covering all harness requirements:
    - Default state (harness disabled)
    - Explicit opt-in required
    - Safety boundary enforcement
    - Controlled delegate behavior
    - VoteBallots/GotJunk through harness
    - No GitHub API calls
    - No production source modification
    - WSP 97 truth table enforcement

#### HXA14 Harness Design

```
Controlled Harness Invocation:
  executor = HermesJobExecutor(controlled_harness=True)
  result = executor.execute(job)
  -> status = CONTROLLED_HARNESS_EXECUTED
  -> controlled_delegate_invoked = True
  -> live_external_delegate_called = False
  -> All safety boundaries enforced

Normal Execution (harness disabled):
  executor = HermesJobExecutor()  # controlled_harness=False default
  result = executor.execute(job)
  -> status = SIMULATED (or BLOCKED)
  -> controlled_delegate_invoked = False
```

#### HXA14 Truth Fields Added

| Field | Description |
|-------|-------------|
| `controlled_delegate_invoked` | True if harness delegate was called |
| `live_external_delegate_called` | True ONLY if real external delegate_task called |
| `repo_created` | True ONLY if GitHub repo was created |
| `production_source_modified` | True ONLY if modules/foundups/*/src was modified |
| `external_federation_ready` | True ONLY if ready for p.fMALL/pAVS |
| `production_ready` | True ONLY if FoundUp is production-ready |

#### WSP 97 Truth Table (Controlled Harness)

| Field | Value | Meaning |
|-------|-------|---------|
| `status` | CONTROLLED_HARNESS_EXECUTED | Harness completed |
| `controlled_delegate_invoked` | True | Harness delegate was called |
| `live_external_delegate_called` | False | No real external delegate |
| `real_execution_performed` | False | No production execution |
| `repo_created` | False | No GitHub operations |
| `production_source_modified` | False | Evidence only |
| `verification_complete` | False | No CABR verification |
| `cabr_ready` | False | No payout pipeline |
| `payout_ready` | False | No token operations |
| `external_federation_ready` | False | Not ready for federation |
| `production_ready` | False | Not production-ready |

#### Test Results

```
test_hxa14_controlled_live_hermes_harness.py: 22 passed in 1.01s
test_hxa4_real_hermes_object_dryrun.py: 17 passed in 0.73s
test_hxa12_gotjunk_second_proof_dryrun.py: 9 passed in 0.71s
```

---

### [2026-05-10] - HXA12_GOTJUNK_SECOND_PROOF_SAFE_DRYRUN_PHASE1 (v0.8.23)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority)
**Impact Analysis**: Second FoundUp proof - validates factory generalizes beyond VoteBallots

#### Changes Made

- `tests/test_hxa12_gotjunk_second_proof_dryrun.py` (NEW - 390 lines):
  - `TestGotJunkBuildIntentDetection` (3 tests) - OpenClaw intent parsing
  - `TestGotJunkDryRunJobCreation` (1 test) - FoundUpJob creation
  - `TestHXA12GotJunkSecondProofSafeDryRun` (3 tests):
    - `test_gotjunk_second_proof_safe_dryrun_reaches_hermes_and_generates_preview` (key HXA12 proof)
    - `test_gotjunk_consumer_path_reaches_real_executor`
    - `test_gotjunk_direct_job_reaches_hermes`
  - `TestGotJunkVoteBallotsParity` (2 tests) - same treatment verification

#### HXA12 Proof: GotJunk Second FoundUp

```
012 "start build gotjunk_001 --dry-run"
  -> OpenClaw dispatch_foundup() creates FoundUpJob
  -> foundup_id=gotjunk_001, requested_action=build_foundup
  -> Real HermesJobExecutor.execute() reached (not mocked)
  -> Status: SIMULATED (dry_run=True enforced)
  -> Evidence files generated:
    - poc_artifact_bundle.json (identifies gotjunk_001)
    - controlled_scaffold.json (identifies gotjunk_001)
    - gotjunk_001_poc/*.md (scaffold preview files)
  -> WSP 97 truth: same as VoteBallots
```

#### Factory Generalization Proven

| Target | Slice | Proof Level |
|--------|-------|-------------|
| VoteBallots | HXA3/HXA4/HXA9/HXA10 | First FoundUp proof |
| GotJunk | HXA12 | Second FoundUp proof (generalizes factory) |

#### WSP 97 Truth Boundaries

- GotJunk target: foundup_id=gotjunk_001
- dry_run=True enforced throughout
- real_execution_performed=False
- repo_created=False
- live_delegate_called=False
- production_source_modified=False
- Same evidence artifacts as VoteBallots (parity proven)

#### Test Results

```
test_hxa12_gotjunk_second_proof_dryrun.py: 9 passed in 0.70s
test_hxa4_real_hermes_object_dryrun.py: 17 passed in 0.74s
test_openclaw_voteballots_dryrun_proof.py: 7 passed in 0.60s
```

---

### [2026-05-10] - HXA10_VOTEBALLOTS_CONTROLLED_SCAFFOLD_GENERATION_PHASE1 (v0.8.22)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority)
**Impact Analysis**: Controlled scaffold file generation in temp/evidence workspace

#### Changes Made

- `src/hermes_job_executor.py`:
  - Added `_generate_controlled_scaffold()` method (lines 873-1056):
    - Generates actual scaffold files in evidence workspace
    - Creates `{foundup_id}_poc/` directory with preview artifacts
    - All files marked as DRY-RUN PREVIEW
    - WSP 97 truth: controlled_scaffold_generated=True, production_source_modified=False
  - Updated `_write_evidence()` to call `_generate_controlled_scaffold()` and write `controlled_scaffold.json`

- `tests/test_hxa4_real_hermes_object_dryrun.py`:
  - Added `TestHXA10ControlledScaffoldGeneration` class (3 tests):
    - `test_voteballots_controlled_scaffold_generation_safe_dryrun_writes_temp_artifacts` - HXA10 proof
    - `test_scaffold_files_contain_generation_metadata` - metadata verification
    - `test_validate_foundup_does_not_create_scaffold` - validate does NOT create scaffold

#### HXA10 Proof: Controlled Scaffold Generation

```
build_foundup VoteBallots (dry_run=True)
  -> HermesJobExecutor.execute() SIMULATED
  -> _generate_controlled_scaffold() creates actual files
  -> Evidence workspace: {job_id}/voteballots_poc/
  -> Files created (all marked DRY-RUN PREVIEW):
    - README.md
    - manifest.preview.json
    - interface.preview.md
    - implementation_plan.md
  -> controlled_scaffold.json written
  -> WSP 97 truth: controlled_scaffold_generated=True
```

#### Progression from HXA9

| Slice | Output | Location | Production Impact |
|-------|--------|----------|-------------------|
| HXA9 | Plan only (JSON) | poc_artifact_bundle.json | None |
| HXA10 | Actual scaffold files | {foundup_id}_poc/*.md | None (temp only) |

#### Generated Scaffold Files

```
.hermes_evidence/{job_id}/
+-- metadata.json
+-- checkpoint.json
+-- poc_artifact_bundle.json (HXA9)
+-- controlled_scaffold.json (HXA10)
\-- voteballots_poc/
    +-- README.md
    +-- manifest.preview.json
    +-- interface.preview.md
    \-- implementation_plan.md
```

#### WSP 97 Truth Boundaries

- controlled_scaffold_generated=True (files written to temp)
- real_execution_performed=False (not production)
- repo_created=False (no GitHub operations)
- live_delegate_called=False (no delegate_task invocation)
- production_source_modified=False (temp only)
- dry_run=True enforced

#### Test Results

```
17 passed in 0.77s (11 HXA4 + 3 HXA9 + 3 HXA10)
7 passed in 0.58s (OpenClaw VoteBallots)
```

---

### [2026-05-10] - HXA9_VOTEBALLOTS_POC_GENERATION_SAFE_DRYRUN_PHASE1 (v0.8.21)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority)
**Impact Analysis**: PoC artifact bundle generation - deterministic plan in evidence

#### Changes Made

- `src/hermes_job_executor.py`:
  - Added `_generate_poc_artifact_plan()` method (lines 807-872):
    - Generates deterministic PoC artifact plan for build_foundup/extract_foundup
    - Returns plan dict with planned_artifacts list
    - WSP 97 truth fields: poc_generation=True, real_execution_performed=False
  - Updated `_write_evidence()` to write `poc_artifact_bundle.json` for build/extract actions

- `tests/test_hxa4_real_hermes_object_dryrun.py`:
  - Added `TestHXA9PocArtifactBundleGeneration` class (3 tests):
    - `test_voteballots_poc_generation_safe_dryrun_creates_artifact_bundle` - HXA9 proof
    - `test_extract_foundup_creates_artifact_bundle` - extract action creates bundle
    - `test_validate_foundup_does_not_create_artifact_bundle` - validate does NOT create bundle

#### HXA9 Proof: PoC Artifact Bundle

```
build_foundup VoteBallots (dry_run=True)
  -> HermesJobExecutor.execute() SIMULATED
  -> _generate_poc_artifact_plan() creates deterministic plan
  -> _write_evidence() writes poc_artifact_bundle.json
  -> Bundle contains planned artifacts list (NOT actual files)
  -> WSP 97 truth: poc_generation=True, real_execution_performed=False
```

#### Bundle Contents (VoteBallots build_foundup)

```json
{
  "poc_generation": true,
  "foundup_id": "voteballots",
  "planned_artifacts": [
    "modules/foundups/voteballots/src/__init__.py",
    "modules/foundups/voteballots/src/voteballots_core.py",
    "modules/foundups/voteballots/src/voteballots_api.py",
    "modules/foundups/voteballots/tests/test_voteballots_core.py"
  ],
  "real_execution_performed": false,
  "repo_created": false,
  "live_delegate_called": false,
  "artifacts_written_to_source": false
}
```

#### WSP 97 Truth Boundaries

- poc_generation=True (plan generated)
- real_execution_performed=False (no actual file creation)
- repo_created=False (no GitHub operations)
- live_delegate_called=False (no delegate_task invocation)
- artifacts_written_to_source=False (plan only)

#### Test Results

```
14 passed in 0.69s (11 HXA4 + 3 HXA9)
```

---

### [2026-05-10] - HXA3_OPENCLAW_HERMES_VOTEBALLOTS_DRYRUN_PROOF_PHASE1 (v0.8.20)

**WSP Protocol References**: WSP 97 (Truthful), WSP 15 (Priority)
**Impact Analysis**: First executable trunk proof - VoteBallots idea->PoC dry-run

#### Changes Made

- `tests/test_openclaw_voteballots_dryrun_proof.py` (NEW):
  - 7 focused tests proving OpenClaw -> WRE -> Hermes trunk path
  - Test classes:
    - `TestVoteBallotsBuildIntentDetection` - 3 tests for intent parsing
    - `TestVoteBallotsDryRunJobCreation` - 1 test for job creation
    - `TestVoteBallotsDryRunPipelineProof` - 2 tests for full pipeline
    - `TestVoteBallotsBuildRouting` - 1 test for router verification
  - Key test: `test_openclaw_voteballots_foundup_build_dryrun_reaches_hermes`
    - Proves: OpenClaw dispatch -> FoundUpJob -> queue -> consumer -> Hermes (mocked)
    - Asserts: dry_run=True, real_execution_performed=False
    - Asserts: No live repo creation, no payout claims

#### Trunk Proof Verified

```
012 "start build voteballots --dry-run"
  -> dispatch_foundup() creates FoundUpJob
  -> _FOUNDUP_JOB_QUEUE receives job
  -> FoundUpJobConsumer.drain_openclaw_queue_once()
  -> route_foundup_job() -> HERMES_BUILDER
  -> execute_foundup_job() (mocked, returns SIMULATED)
  -> ConsumerResult with checkpoint_state="SIMULATED"
  -> real_execution_performed=False
```

#### WSP 97 Truth Boundaries

- dry_run=True enforced throughout
- real_execution_performed=False (Hermes executor mocked)
- No GitHub repo created (mocked)
- No live extraction performed (mocked)
- verification_complete=False, cabr_ready=False, payout_ready=False

#### Test Results

```
7 passed in 0.68s
```

Worker-Lane: W1
Slice: HXA3_OPENCLAW_HERMES_VOTEBALLOTS_DRYRUN_PROOF_PHASE1

---

### [2026-05-03] - WRE_HERMES_EXECUTOR_CONSUMER_BINDING_DRY_RUN_PHASE1 (v0.8.19)

**WSP Protocol References**: WSP 11 (Interface), WSP 97 (Truthful)
**Impact Analysis**: Bind FoundUpJobConsumer to WRE HermesJobExecutor dry-run seam

#### Changes Made

- `src/foundup_job_consumer.py`:
  - Added Phase 1C checkpoint/evidence fields to `ConsumerResult`:
    - `checkpoint_state: Optional[str]` - Hermes swarm checkpoint state
    - `checkpoint_result: Optional[str]` - Summary of work completed
    - `checkpoint_blocker: Optional[str]` - Description of blocker (if BLOCKED)
    - `checkpoint_next_action: Optional[str]` - Suggested next step
    - `evidence_path: Optional[str]` - Path to evidence directory
    - `real_execution_performed: bool` - WSP 97 truth (always False in Phase 1)
  - Updated `to_dict()` to always include WSP 97 truth fields
  - Updated `is_terminal` property to handle `HermesDelegationResult.status` enum
  - Updated `_dispatch_to_hermes()` to:
    - Import from WRE executor: `modules.infrastructure.wre_core.src.hermes_job_executor`
    - Call `execute_foundup_job(job)` without `force_dry_run` param
    - Populate checkpoint/evidence fields in ConsumerResult
  - Added `_emit_receipt_for_hermes_result()` method:
    - Skips receipt emission for dry-run (SIMULATED status)
    - Evidence captured in checkpoint files, not receipts for Phase 1
    - WSP 97: No overclaim for simulated jobs

- `tests/test_foundup_job_consumer.py`:
  - Updated all mock paths from old adapter to WRE executor
  - Refactored `TestHermesDispatch` tests for WRE executor interface
  - Renamed `TestConsumerResultReceiptBinding` -> `TestConsumerResultCheckpointBinding`
  - Updated tests to verify checkpoint/evidence fields instead of receipt
  - 30 tests passing

#### Consumer-Executor Binding Contract

```
FoundUpJobConsumer.consume_one(job)
  -> route_foundup_job(job) -> RouteEnvelope
  -> _dispatch_to_hermes(job, envelope)
      -> WRE execute_foundup_job(job) -> HermesDelegationResult
      -> ConsumerResult with checkpoint_state, evidence_path
```

#### WSP 97 Truth Boundaries (Phase 1C)

- `real_execution_performed` = False (WRE dry-run seam only)
- `checkpoint_state` = "SIMULATED" (no real Hermes delegation)
- `evidence_path` = populated (observability artifact, not proof)
- `receipt_emission` = None (no receipt for dry-run jobs)
- `verification_complete` = False (always)
- `cabr_ready` = False (always)
- `payout_ready` = False (always)

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_consumer.py -v
# 30 passed

python -m pytest modules/infrastructure/wre_core/tests/test_hermes_job_executor.py -v
# 94 passed
```

---

### [2026-05-03] - HERMES_EVIDENCE_COLLECTION_PHASE1 (v0.8.18)

**WSP Protocol References**: WSP 11 (Interface), WSP 97 (Truthful)
**Impact Analysis**: Add evidence file collection for auditable job artifacts

#### Changes Made

- `src/hermes_job_executor.py`:
  - Added `evidence_path: Optional[str]` to `HermesDelegationResult`
  - Added `_write_evidence()` method to `HermesJobExecutor`:
    - Creates `.hermes_evidence/{job_id}/` directory
    - Writes `metadata.json` with job identity, workspace binding, timing
    - Writes `checkpoint.json` with checkpoint state and execution details
    - Returns evidence path or None on error (silent failure)
  - Integrated evidence collection into `execute()` for all valid job paths
  - Evidence NOT written for validation failures (no valid job to document)
  - Added `json` to top-level imports

- `tests/test_hermes_job_executor.py`:
  - 10 new tests (94 total) for evidence collection
  - TestEvidenceCollection: directory creation, metadata/checkpoint JSON
  - TestEvidencePathField: default value, to_dict serialization

#### Evidence Directory Structure

```
.hermes_evidence/{job_id}/
+-- metadata.json    # Job identity, workspace binding, timing
\-- checkpoint.json  # Checkpoint state, files_changed, commands_run
```

#### WSP 97 Truth Boundaries

- Evidence files are observability artifacts ONLY
- They prove job was processed through WRE, not that real work occurred
- `real_execution_performed` = False (always in Phase 1)
- `verification_complete` = False (evidence is NOT verification)
- Evidence enables future CABR verification to have artifacts to score

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_hermes_job_executor.py -v
# 94 passed
```

---

### [2026-05-03] - HERMES_CHECKPOINT_PROTOCOL_PHASE1 (v0.8.17)

**WSP Protocol References**: WSP 11 (Interface), WSP 97 (Truthful)
**Impact Analysis**: Add checkpoint protocol fields for structured Hermes swarm evidence

#### Changes Made

- `src/hermes_job_executor.py`:
  - Added checkpoint protocol fields to `HermesDelegationResult`:
    - `checkpoint_state`: DONE|BLOCKED|NEEDS_INPUT|HANDOFF|SIMULATED (default: SIMULATED)
    - `checkpoint_result`: Summary of work completed (Optional[str])
    - `checkpoint_blocker`: Description of blocker if BLOCKED (Optional[str])
    - `checkpoint_next_action`: Suggested next step (Optional[str])
    - `files_changed`: List of files modified (List[str])
    - `commands_run`: List of commands executed (List[str])
  - Updated `to_dict()` to serialize all checkpoint fields

- `tests/test_hermes_job_executor.py`:
  - 20 new tests (84 total) for checkpoint protocol
  - TestCheckpointProtocolFields: default values
  - TestCheckpointInResult: to_dict serialization
  - TestCheckpointStateSimulated: dry_run behavior
  - TestCheckpointWSP97: truth field isolation

#### WSP 97 Truth Boundaries

- `checkpoint_state` = "SIMULATED" when dry_run=True or flag disabled
- `real_execution_performed` = False (always in Phase 1)
- `verification_complete` = False (checkpoint fields do NOT imply verification)
- `cabr_ready` = False
- `payout_ready` = False

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_hermes_job_executor.py -v
# 84 passed
```

---

### [2026-05-02] - HERMES_WORKSPACE_BINDING_CONTRACT_PHASE1 (v0.8.16)

**WSP Protocol References**: WSP 11 (Interface), WSP 50 (Pre-Action), WSP 97 (Truthful)
**Impact Analysis**: Define workspace binding contract for Hermes delegation sandbox

#### Changes Made

- `src/hermes_job_executor.py`:
  - `WorkspaceBinding` dataclass - sandbox context for Hermes subagents
  - `BLOCKED_PATHS` frozenset - security-hardcoded patterns (immutable)
  - `ACTION_ALLOWED_PATHS` dict - action-to-path template mapping
  - `build_allowed_paths()` - generate allowed paths from job context
  - `get_evidence_output_path()` - derive evidence path from job_id
  - `_build_workspace_binding()` method on HermesJobExecutor
  - Added `workspace_binding` field to HermesDelegationRequest
  - Path validation with `PurePath.match()` for `**` glob support

- `tests/test_hermes_job_executor.py`:
  - 31 new tests (64 total) for workspace binding
  - TestWorkspaceBindingDataclass, TestWorkspaceBindingPathValidation
  - TestBlockedPathsConstant, TestBuildAllowedPaths, TestGetEvidenceOutputPath
  - TestWorkspaceHintInRequest, TestAllowedPathsInRequest, TestBlockedPathsInRequest
  - TestWorkspaceRootDetection, TestNoRealExecutionWithWorkspaceBinding

- `docs/audits/hermes_swarm/HERMES_WORKSPACE_BINDING_CONTRACT.md` (NEW, gitignored):
  - Contract specification document defining all fields and behaviors
  - Path constraint rules, evidence output structure, retention modes

#### WorkspaceBinding Fields

| Field | Type | Purpose |
|-------|------|---------|
| workspace_root | str | Absolute path to repo root |
| workspace_hint | Optional[str] | Relative path for Hermes (e.g., "modules/foundups/gotjunk") |
| allowed_paths | List[str] | Paths Hermes may read/write |
| blocked_paths | List[str] | Paths Hermes must NOT access |
| evidence_output_path | str | `.hermes_evidence/{job_id}/` |
| retention_on_failure | str | "preserve" (default), "cleanup", "archive" |

#### WSP 97 Truth Boundaries

- `workspace_binding_enforced`: False (enforcement is Phase 2)
- `path_constraints_validated`: False (validation is Phase 2)
- `evidence_collected`: False (collection is Phase 2)
- Contract is structural definition only, not enforcement

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_hermes_job_executor.py -v
# 64 passed
```

---

### [2026-05-02] - HERMES_JOB_EXECUTOR_ADAPTER_PHASE1 (v0.8.15)

**WSP Protocol References**: WSP 11 (Interface), WSP 50 (Pre-Action), WSP 97 (Truthful)
**Impact Analysis**: Add Hermes FoundUpJob executor adapter seam (no real execution)

#### Changes Made

- `src/hermes_job_executor.py` (NEW):
  - `HermesJobExecutor` class - adapter mapping FoundUpJob to Hermes delegate_task contract
  - `HermesDelegationRequest` dataclass - outbound request to Hermes
  - `HermesDelegationResult` dataclass - result with WSP 97 truth fields
  - `HermesExecutionStatus` enum - status codes including SIMULATED, BLOCKED_*
  - Feature flag: `HERMES_DELEGATE_ENABLED=0` (default disabled)
  - Lazy import of `vendor.hermes_agent.tools.delegate_tool`
  - dry_run=True default (no real terminal/file execution)

- `tests/test_hermes_job_executor.py` (NEW):
  - 33 tests covering feature flag, mapping, validation, WSP 97 compliance
  - Verifies no CABR/token/payout/reward fields exist
  - Verifies no queue consumption occurs

#### Feature Flag Behavior

| Flag | dry_run | Status |
|------|---------|--------|
| 0 (default) | any | SIMULATED |
| 1 | True | SIMULATED |
| 1 | False | BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED |

#### WSP 97 Truth Boundaries

- `real_execution_performed`: Always False in Phase 1
- `verification_complete`: Always False (no CABR verification)
- `cabr_ready`: Always False (no CABR pipeline)
- `payout_ready`: Always False (no payout pipeline)
- Adapter is seam-only; does not consume jobs or mutate state

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_hermes_job_executor.py -v
# 33 passed

python -m pytest modules/infrastructure/wre_core/tests -q --ignore=modules/infrastructure/wre_core/tests/test_production_gates.py
# 550 passed (517 existing + 33 new)
```

---

### [2026-05-02] - WRE_MODEL_ROUTING_POLICY_VALIDATION_PHASE1 (v0.8.14)

**WSP Protocol References**: WSP 11 (Interface), WSP 97 (Truthful - policy validation only)
**Impact Analysis**: Validate tier/preference compatibility for FoundUpJob model routing

#### Changes Made

- `src/foundup_job_router.py`:
  - Added `EnvelopeValidationCode.MODEL_PREFERENCE_NOT_ALLOWED_FOR_TIER`
  - Added `TIER_ALLOWED_PREFERENCES` map:
    - freemium: auto, free only
    - basic: auto, free, standard
    - enterprise: auto, free, standard, premium
  - Added `EnvelopeValidationResult` fields: model_routing_policy_validated, model_routing_policy_reason
  - Added tier/preference compatibility check in `_validate_compute_budget()`

- `tests/test_foundup_job_envelope_validation.py`:
  - Added 18 new tests for model routing policy validation
  - Updated 2 existing tests to use compatible tiers

#### Policy Rules

| Tier | Allowed Preferences |
|------|---------------------|
| freemium | auto, free |
| basic | auto, free, standard |
| enterprise | auto, free, standard, premium |

#### WSP 97 Truth Boundaries

- Policy validation is structural only - no model selected
- No inference executed, no compute consumed
- verification_complete=False, cabr_ready=False, payout_ready=False

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_envelope_validation.py -q
# 111 passed

python -m pytest modules/infrastructure/wre_core/tests -q --ignore=modules/infrastructure/wre_core/tests/test_production_gates.py
# 517 passed
```

---

### [2026-05-02] - WRE_COMPUTE_BUDGET_VALIDATION_PHASE1 (v0.8.13)

**WSP Protocol References**: WSP 11 (Interface), WSP 97 (Truthful - structural validation only)
**Impact Analysis**: Add compute budget policy validation for FoundUpJob envelopes

#### Changes Made

- `src/foundup_job_router.py`:
  - Added `EnvelopeValidationCode` values for compute validation errors
  - Added `EnvelopeValidationResult` fields: compute_budget_validated, compute_tier, model_preference
  - Added `_validate_compute_budget()` helper function
  - Validates: compute_budget/compute_used types, non-negative values, budget limits
  - Validates: compute_tier (freemium|basic|enterprise), model_preference (auto|free|standard|premium)
  - Live mode requires explicit compute_budget

- `tests/test_foundup_job_envelope_validation.py`:
  - Added 34 new tests for compute budget validation
  - Covers type validation, negative values, budget overflow, tier/preference validation

#### WSP 97 Truth Boundaries

- Structural validation only - does not verify actual metering accuracy
- Does not prove resource consumption tracking
- Does not enable billing claims
- verification_complete=False, cabr_ready=False, payout_ready=False

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_envelope_validation.py -q
# 93 passed

python -m pytest modules/infrastructure/wre_core/tests -q --ignore=modules/infrastructure/wre_core/tests/test_production_gates.py
# 499 passed
```

---

### [2026-05-02] - WRE_LIVE_MODE_EVIDENCE_POLICY_GATE_PHASE1 (v0.8.12)

**WSP Protocol References**: WSP 11 (Interface), WSP 97 (Truthful - live mode blocked without gates)
**Impact Analysis**: Block non-dry-run FoundUpJob envelopes unless strict policy gates present

#### Changes Made

- `src/foundup_job_router.py`:
  - Added `EnvelopeValidationCode` values:
    - `LIVE_MODE_NOT_ENABLED`
    - `LIVE_MODE_REQUIRES_HUMAN_APPROVAL`
    - `LIVE_MODE_REQUIRES_EVIDENCE`
    - `LIVE_MODE_REQUIRES_SECURITY_GATE`
  - Added `EnvelopeValidationResult` fields:
    - `is_live_mode`: True if explicit dry_run_mode=False
    - `live_mode_gates_passed`: True if all required gates passed
    - `missing_live_gates`: List of missing policy gates
  - Added `_validate_live_mode_gates()` function
  - Updated `validate_foundup_job_envelope()` to apply live mode gates

- `tests/test_foundup_job_envelope_validation.py`:
  - Added 17 new tests for live mode policy gates
  - TestDryRunWithPendingEvidenceStillPasses (2 tests)
  - TestLiveModeWithoutApprovalFails (2 tests)
  - TestLiveModeWithoutEvidenceFails (2 tests)
  - TestLiveModeWithMalformedEvidenceFails (2 tests)
  - TestLiveModeWithApprovalAndEvidenceNoVerification (3 tests)
  - TestLiveModeSecurityGate (2 tests)
  - TestLiveModeValidationErrorDetails (4 tests)
  - Updated 2 existing tests for live mode approval

#### Live Mode Policy Gates (Phase 1)

| Gate | Requirement | Validation Code if Missing |
|------|-------------|----------------------------|
| human_approval OR permission_gate_passed | True | LIVE_MODE_REQUIRES_HUMAN_APPROVAL |
| security_gate_passed (if security_gate_checked) | True | LIVE_MODE_REQUIRES_SECURITY_GATE |
| evidence_refs | Non-empty, not pending | LIVE_MODE_REQUIRES_EVIDENCE |

#### WSP 97 Truth Boundaries

- Live mode gates do NOT imply `verification_complete=True`
- Live mode gates do NOT enable CABR claims (`cabr_ready=False`)
- Live mode gates do NOT enable payout claims (`payout_ready=False`)
- This is validation only - no actual execution path created
- Dry-run behavior unchanged (evidence_pending allowed)

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_envelope_validation.py -q
# 59 passed

python -m pytest modules/infrastructure/wre_core/tests -q --ignore=modules/infrastructure/wre_core/tests/test_production_gates.py
# 465 passed
```

---

### [2026-05-02] - WRE_EVIDENCE_REFS_VALIDATION_PHASE1 (v0.8.11)

**WSP Protocol References**: WSP 11 (Interface), WSP 97 (Truthful - evidence traceability only)
**Impact Analysis**: Add evidence reference validation for FoundUpJob execution envelopes

#### Changes Made

- `src/foundup_job_router.py`:
  - Added `EnvelopeValidationCode.VALID_EVIDENCE_PENDING` for dry-run pending state
  - Added `EnvelopeValidationCode.INVALID_EVIDENCE_REFS_TYPE` for wrong type
  - Added `EnvelopeValidationCode.INVALID_EVIDENCE_REF_ENTRY` for malformed entries
  - Added `EnvelopeValidationResult` fields: evidence_refs_validated, evidence_refs_count, evidence_pending
  - Added WSP 97 truth fields: verification_complete=False, cabr_ready=False, payout_ready=False (always False)
  - Added `_validate_evidence_refs()` helper function
  - Updated `validate_foundup_job_envelope()` to validate evidence shape

- `tests/test_foundup_job_envelope_validation.py`:
  - Added 22 new tests for evidence validation
  - TestEvidenceRefsListOfStrings (2 tests)
  - TestEvidenceRefsEmptyWithDryRun (3 tests)
  - TestEvidenceRefsWrongType (3 tests)
  - TestEvidenceRefsEmptyString (2 tests)
  - TestEvidenceRefsMalformedDict (6 tests)
  - TestEvidenceRefsWSP97TruthFields (4 tests)
  - TestGenericDAEEvidenceBehavior (2 tests)

#### Evidence Validation Rules

| Condition | Result | Code |
|-----------|--------|------|
| List of non-empty strings | Valid | VALID |
| Empty list in dry-run | Valid (pending) | VALID_EVIDENCE_PENDING |
| No evidence_refs in dry-run | Valid (pending) | VALID_EVIDENCE_PENDING |
| Dict with path/id/ref field | Valid | VALID |
| Not a list | Invalid | INVALID_EVIDENCE_REFS_TYPE |
| Empty string in list | Invalid | INVALID_EVIDENCE_REF_ENTRY |
| Dict without path/id/ref | Invalid | INVALID_EVIDENCE_REF_ENTRY |
| Non-string/dict in list | Invalid | INVALID_EVIDENCE_REF_ENTRY |

#### WSP 97 Truth Boundaries

- `verification_complete`: Always False (evidence proves traceability only)
- `cabr_ready`: Always False (evidence does NOT enable CABR claims)
- `payout_ready`: Always False (evidence does NOT enable payout claims)
- `evidence_refs_validated`: True if evidence shape is valid
- `evidence_pending`: True if dry-run mode with no/empty evidence

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_envelope_validation.py -q
# 42 passed

python -m pytest modules/infrastructure/wre_core/tests -q --ignore=modules/infrastructure/wre_core/tests/test_production_gates.py
# 448 passed
```

---

### [2026-05-02] - WRE_ENVELOPE_VALIDATION_FOUNDUPJOB_PHASE1 (v0.8.10)

**WSP Protocol References**: WSP 11 (Interface), WSP 50 (Pre-Action Verification), WSP 97 (Truthful)
**Impact Analysis**: Distinguish FoundUpJob envelopes from generic DAE envelopes; enforce strict validation

#### Changes Made

- `src/foundup_job_router.py`:
  - Added `EnvelopeType` enum (GENERIC_DAE, FOUNDUP_JOB)
  - Added `EnvelopeValidationCode` enum with validation reason codes
  - Added `EnvelopeValidationResult` dataclass for typed validation results
  - Added `detect_envelope_type()` function to classify envelopes
  - Added `validate_foundup_job_envelope()` function for strict FoundUpJob validation
  - Required fields for FoundUpJob: job_id, foundup_id, tenant_id, requested_action
  - WSP 97 safety: dry_run_mode defaults to True when missing

- `wre_gateway/src/dae_gateway.py`:
  - Updated `_verify_envelope()` to use strict validation for FoundUpJob envelopes
  - Added `get_last_validation_result()` for accessing validation details
  - Updated `route_to_dae()` to return detailed validation failures
  - Import seam with fallback when validation unavailable

- `tests/test_foundup_job_envelope_validation.py` (NEW):
  - 20 tests for envelope validation behavior
  - Tests generic DAE envelope permissive validation
  - Tests FoundUpJob strict validation (missing fields rejected)
  - Tests dry_run defaulting behavior
  - Tests failure messages identify missing fields
  - Tests envelope type detection

#### Validation Rules

| Envelope Type | Required Fields | Validation |
|---------------|-----------------|------------|
| GENERIC_DAE | objective | Permissive |
| FOUNDUP_JOB | job_id, foundup_id, tenant_id, requested_action | Strict |

#### WSP 97 Truth Boundaries

- Missing policy_flags -> dry_run_mode defaulted to True (logged)
- Missing FoundUpJob fields -> explicit rejection with missing_fields list
- Generic DAE envelopes -> permissive (objective only required)
- Validation results serializable for API/logging

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_envelope_validation.py -v
# 20 passed

python -m pytest modules/infrastructure/wre_core/tests -q --ignore=modules/infrastructure/wre_core/tests/test_production_gates.py
# 426 passed
```

---

### [2026-05-02] - WRE_QUEUE_RETENTION_SEMANTICS_PHASE1 (v0.8.9)

**WSP Protocol References**: WSP 11 (Interface), WSP 97 (Truthful - no silent failures)
**Impact Analysis**: Harden queue draining with retention-aware clearing

#### Changes Made

- `src/foundup_job_consumer.py`:
  - Added `DrainResult` dataclass for retention metadata
  - Added `ConsumerResult.should_clear` property - True only for terminal successful jobs with receipts
  - Added `ConsumerResult.retention_reason` property - explicit reason for retained jobs
  - Added `drain_openclaw_queue_with_retention()` method - selective job removal
  - Updated `drain_openclaw_queue_once()` to use retention semantics
  - Updated `drain_openclaw_queue_dry_run()` to return retention metadata

- `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py`:
  - Added `remove_jobs_by_id()` function for selective queue removal

- `tests/test_foundup_job_consumer.py`:
  - Added `TestRetentionSemantics` class (4 tests)
  - Updated existing tests for retention-aware behavior

#### Retention Semantics

| Condition | Action | Reason Code |
|-----------|--------|-------------|
| Terminal + receipt success | Clear | - |
| Routing FAILED | Retain | `routing_failed` |
| Routing BLOCKED | Retain | `routing_blocked` |
| Action UNSUPPORTED | Retain | `action_unsupported` |
| Not dispatched | Retain | `not_dispatched` |
| Not terminal | Retain | `not_terminal` |
| Receipt emission failed | Retain | `receipt_emission_failed` |

#### Example Output

```json
{
  "job_count": 3,
  "cleared_job_ids": ["job_success"],
  "retained_job_ids": ["job_fail1", "job_fail2"],
  "retention_reasons": {"job_fail1": "routing_failed", "job_fail2": "routing_blocked"},
  "cleared_count": 1,
  "retained_count": 2,
  "summary": {"verification_complete": false, "cabr_ready": false, "payout_ready": false}
}
```

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_consumer.py -q
# 29 passed
```

---

### [2026-05-02] - WRE_CLOSED_LOOP_DRY_RUN_COMMAND_PHASE1 (v0.8.8)

**WSP Protocol References**: WSP 11 (Interface), WSP 97 (Truthful)
**Impact Analysis**: Adds supported dry-run command/callable entrypoint to drain FoundUpJob queue

#### Changes Made

- `src/foundup_job_consumer.py`:
  - Added `drain_openclaw_queue_dry_run(clear=True)` convenience function
  - Returns structured evidence dict: job_count, results, dry_run, queue_cleared, summary
  - WSP 97 truth boundaries: verification_complete=False, cabr_ready=False, payout_ready=False

- `run_wre.py`:
  - Added `cmd_drain(args)` async handler
  - Added `drain` subparser with `--no-clear` flag
  - Registered in command dispatch dict

- `tests/test_foundup_job_consumer.py`:
  - Added `TestDrainOpenClawQueueDryRun` class (4 tests)
  - Tests: structured evidence, WSP 97 truth fields, empty queue, no-clear flag

#### Usage

```bash
# Drain queue (clears after)
python run_wre.py drain

# Drain queue (keep jobs in queue)
python run_wre.py drain --no-clear
```

#### Callable Entrypoint

```python
from modules.infrastructure.wre_core.src.foundup_job_consumer import (
    drain_openclaw_queue_dry_run,
)

summary = drain_openclaw_queue_dry_run(clear=True)
# Returns: {"job_count": N, "results": [...], "dry_run": True, "summary": {...}}
```

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_consumer.py -v
# 20 passed
```

---

### [2026-04-25] - W5/OC5: FoundUpJob Routing Envelope Phase 1 (v0.8.7)

**WSP Protocol References**: WSP 11 (Interface), WSP 50 (Pre-Action), WSP 77 (Agent Coordination), WSP 97 (Truthful)
**Impact Analysis**: WRE routing seam for FoundUpJob - validates identity, determines target backend, returns typed envelope (NO execution)

#### Changes Made

- `src/foundup_job_router.py` (NEW):
  - `RouteStatus` enum: ROUTED, QUEUED, BLOCKED, UNSUPPORTED, FAILED
  - `TargetBackend` enum: HERMES_BUILDER, HERMES_VALIDATOR, OPENCLAW_QUEUE, FAM_TRACKER, NONE
  - `RouteReasonCode` enum: OK_ROUTED, OK_QUEUED, BLOCKED_* codes, UNSUPPORTED_ACTION, FAIL_* codes
  - `RouteEnvelope` dataclass: typed routing decision with job identity, backend, status, reason, policy summary
  - `route_foundup_job(job)`: validates identity, checks terminal status, enforces policy gates, routes to backend
  - `get_action_route_map()`: inspection helper for documentation

- `tests/test_foundup_job_router.py` (NEW):
  - 17 tests covering all routing scenarios
  - Hermes routing (build/extract -> BUILDER, validate -> VALIDATOR)
  - Queue routing (queue_foundup_job -> QUEUED status)
  - Unsupported action handling
  - Terminal job blocking (SUCCEEDED, FAILED)
  - Missing identity blocking (job_id, tenant_id)
  - Policy gate blocking (security_gate_checked but not passed)
  - Envelope serialization

#### Action -> Backend Mapping

| Action | Target Backend |
|--------|---------------|
| build_foundup | HERMES_BUILDER |
| extract_foundup | HERMES_BUILDER |
| validate_foundup | HERMES_VALIDATOR |
| queue_foundup_job | OPENCLAW_QUEUE |

#### Architecture

```
OpenClaw -> FoundUpJob -> WRE Router -> RouteEnvelope -> Hermes/FAM (later)
```

Phase 1: Routing seam only. Execution deferred to W6 (Hermes adapter).

#### Verification

```bash
PYTHONPATH=. python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_router.py -v
# 17 passed
```

---

### [2026-04-19] - SEC9: Security Stack 0102 Control Hooks (v0.8.6)

**WSP Protocol References**: WSP 97 (Truthful), WSP 77 (Agent Coordination)
**Impact Analysis**: 0102 control integration for security stack - NO auto-remediation

#### Changes Made

- `src/security_control_hooks.py` (NEW):
  - `SecurityStackController` class - main 0102 entrypoint
  - `SecurityStackStatus` dataclass - durable status artifact
  - `SecurityAlert` dataclass - 012 escalation artifact
  - `DryRunResult` dataclass - dry-run execution result
  - CLI entrypoint for manual invocation

- `tests/test_security_control_hooks.py` (NEW):
  - 29 tests covering all 5 control hooks
  - Manual 0102 invocation (5 tests)
  - Unavailable tools path (3 tests)
  - Alert artifact generation (4 tests)
  - Report-only mode (3 tests)
  - HoloDAE trigger bridge (4 tests)
  - Status artifact (3 tests)
  - WRE skill contract (2 tests)

#### Control Hooks

1. **Manual 0102 Invocation** (`run_dry_run()`)
   - CLI: `python -m modules.infrastructure.wre_core.src.security_control_hooks dry-run`
   - Does not require 012 except for critical escalation

2. **WRE Skill Contract** (`invoke_sec3_skill()`)
   - Input: `{"tool": str, "target": str, "mode": str}`
   - Output: `{"state": "proposed"|"executed"|"unavailable", ...}`

3. **HoloDAE Trigger Bridge** (`bridge_trigger_to_sec3()`)
   - Transforms SEC4 proposals to SEC3 input contracts
   - Auto-execution DEFERRED (always report_only)

4. **Status Artifact** (`write_status()`, `read_status()`)
   - Path: `alerts/security/status.json`
   - Fields: last_run_at, mode, tools_available, next_operator_action

5. **012 Escalation** (`write_alert()`, `create_alert_from_finding()`)
   - Path: `alerts/security/alert_<id>_<timestamp>.json`
   - Triggers: critical severity, secret exposure

#### WSP 97 State Machine

```
triggered -> proposed -> executed -> escalated -> completed
                     \-> unavailable
```

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_security_control_hooks.py -v
# Result: 29 passed
```

---

### [2026-04-18] - SEC8: Security Stack E2E Dry-Run (v0.8.5)

**WSP Protocol References**: WSP 97 (Truthful), WSP 77 (Agent Coordination)
**Impact Analysis**: E2E operational proof with synthetic data - NO real vulnerabilities claimed

#### Changes Made

- `tests/test_security_stack_e2e.py` (NEW):
  - 11 E2E tests proving SEC1-SEC7 stack integration
  - Synthetic findings (CRITICAL/HIGH/MEDIUM)
  - Full flow: policy -> store -> recall -> analysis proposal
  - Report artifact generation

#### E2E Flow Validated

```
Synthetic Finding (mocked SEC1)
       |
       v
SEC2 Policy Routing (VulnerabilityScanPolicy)
       |
       v
SEC5 Pattern Memory (store_finding)
       |
       v
SEC6 Recall (recall_by_fingerprint)
       |
       v
SEC7 Analysis Proposal (analyze_finding)
       |
       v
Report Artifact (JSON)
```

#### Test Categories

- TestE2EDryRun: Full stack flows (4 tests)
- TestE2EReportGeneration: Artifact generation (2 tests)
- TestE2EInvariants: Critical invariants (4 tests)
- TestE2ESummary: Comprehensive summary (1 test)

#### Invariants Verified

- `no_patch_generated: true` for all findings
- CRITICAL always requires 012 gate
- Policy decision preserved through stack
- No live scanner invocation (synthetic only)

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_security_stack_e2e.py -v
# Result: 11 passed
```

---

### [2026-04-18] - SEC7: Security Analysis Assistant (v0.8.4)

**WSP Protocol References**: WSP 77 (Agent Coordination), WSP 97 (Truthful)
**Impact Analysis**: LLM-assisted proposal generation - NO auto-remediation, NO patch generation

#### Changes Made

- `src/security_analysis_assistant.py` (NEW):
  - `AnalysisProposal` dataclass - remediation proposal for human review
  - `SecurityAnalysisAssistant` class - LLM-assisted analysis (optional Qwen/Gemma)
  - `analyze_finding()` - produces proposals from scan findings + recall context
  - `write_proposal_artifact()` - explicit file write (disabled by default)
  - Lazy backend resolution (no LM Studio required for tests)

- `tests/test_security_analysis_assistant.py` (NEW):
  - 34 tests with mocked LLM backends
  - LLM unavailable returns `needs_review` (3 tests)
  - Qwen/Gemma output parsing (6 tests)
  - `requires_012` preserved from policy (3 tests)
  - `no_patch_generated: true` invariant (3 tests)
  - Recall context inclusion (4 tests)
  - No file writes except explicit (3 tests)

#### Hard Invariants

- `no_patch_generated: true` - always True
- `requires_012` - preserved from SEC2 policy, never overridden by LLM
- No code mutation
- No auto-remediation
- No MCP/Codex/Claude dependency

#### Proposal Output

```python
AnalysisProposal(
    fingerprint="...",
    finding_id="CVE-2024-001",
    classification="true_positive|false_positive|needs_review",
    classification_confidence=0.85,
    finding_summary="...",
    risk_explanation="...",
    remediation_proposal="...",  # Text only, no patch
    files_likely_affected=["src/api.py"],
    requires_012=True,
    no_patch_generated=True,  # Always True
    analysis_source="qwen+gemma|deterministic",
    recall_context_included=True,
)
```

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_security_analysis_assistant.py -v
# Result: 34 passed
```

---

### [2026-04-18] - SEC6: Security Recall Service (v0.8.3)

**WSP Protocol References**: WSP 60 (Module Memory), WSP 97 (Truthful), WSP 48 (Recursive Self-Improvement)
**Impact Analysis**: Read-only recall layer for historical vulnerability lookup - NO remediation

#### Changes Made

- `src/security_recall.py` (NEW):
  - `RecallResult` dataclass - query result with historical context and suggestion
  - `SecurityRecall` class - read-only recall service over SecurityPatternMemory
  - `recall_by_fingerprint()` - exact fingerprint lookup
  - `recall_by_finding_id()` - CVE/rule-id pattern lookup (aggregates all matches)
  - `recall_by_type()` - filter by tool/category/severity
  - `get_historical_summary()` - comprehensive timeline and statistics
  - `_suggest_outcome_from_patterns()` - suggests outcome based on historical majority

- `tests/test_security_recall.py` (NEW):
  - 33 tests covering all recall methods
  - Outcome suggestion logic (exact match, majority, mixed)
  - Historical summary generation
  - Read-only invariant verification (recall does not mutate)

#### Read-Only Invariants

- Recall does NOT modify findings
- Recall does NOT increment times_seen
- Recall does NOT update timestamps
- Recall does NOT add new findings
- Future SEC7+ may add Qwen/Gemma analysis (NOT in this phase)

#### Architecture

```
SEC5 (storage) <---- SEC6 (recall) ----> suggested outcome
                         ^
                         |
            fingerprint/finding_id/type query
```

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_security_recall.py -v
# Result: 33 passed
```

---

### [2026-04-18] - SEC5: Security Pattern Memory (v0.8.2)

**WSP Protocol References**: WSP 60 (Module Memory), WSP 97 (Truthful), WSP 48 (Recursive Self-Improvement)
**Impact Analysis**: SQLite storage for vulnerability outcomes - observations only, no remediation

#### Changes Made

- `src/security_pattern_memory.py` (NEW):
  - `SecurityFinding` dataclass with fingerprint, severity, policy decision, tracking fields
  - `SecurityPatternMemory` class - SQLite storage following existing PatternMemory patterns
  - `store_finding()` - store/update with times_seen increment
  - `get_finding_by_fingerprint()` - lookup by deterministic hash
  - `list_open_findings()` - filter by severity/tool
  - `list_findings_requiring_012()` - pending 012 review
  - `summarize_findings()` - aggregate statistics
  - `store_from_scan_report()` - integrate with SEC3 output

- `tests/test_security_pattern_memory.py` (NEW):
  - 33 tests covering storage, retrieval, queries, summaries
  - Repeated finding times_seen increment
  - Severity/policy field preservation
  - Missing optional fields handled

#### Schema

```sql
security_findings (
    fingerprint TEXT PRIMARY KEY,
    finding_id TEXT, tool TEXT, target TEXT,
    package_name TEXT, file_path TEXT, line_number INTEGER,
    severity TEXT, title TEXT, description TEXT,
    policy_decision TEXT, requires_012 INTEGER,
    status TEXT DEFAULT 'open',
    first_seen TEXT, last_seen TEXT, times_seen INTEGER,
    source_report_path TEXT,
    fix_available INTEGER, fix_version TEXT
)
```

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_security_pattern_memory.py -v
# Result: 33 passed
```

---

### [2026-04-18] - SEC4: Security Scan Trigger Detector (v0.8.1)

**WSP Protocol References**: WSP 97 (Truthful), WSP 77 (Agent Coordination), WSP 27 (DAE Architecture)
**Impact Analysis**: Trigger detection for security scans based on changed files

#### Changes Made

- `src/security_trigger.py` (NEW):
  - `SecurityTriggerDetector` class - detects security-relevant file changes
  - Pattern matching for: requirements*.txt, pyproject.toml, package.json, Dockerfile, docker-compose, GitHub workflows, IaC files
  - Proposes SCA/container/IaC scans based on file type
  - Default mode: `report_only` (proposals only, no auto-execution)
  - Truthful distinction: "proposed" vs "executed" vs "skipped"

- `tests/test_security_trigger.py` (NEW):
  - 26 tests covering all pattern types
  - Verifies dependency files propose SCA scan
  - Verifies Dockerfile/container changes propose Trivy scan
  - Verifies docs-only changes do NOT propose security scan
  - Verifies policy remains report-only by default

#### Architecture

```
SEC1 (scanner execution) -> SEC2 (policy routing) -> SEC3 (skill wrapper)
                                                           ^
SEC4 (trigger detection) -> proposes SEC3 execution -------+
```

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_security_trigger.py -v
# Result: 26 passed
```

---

### [2026-04-18] - SEC3: WRE Security Scan Skill (v0.8.0)

**WSP Protocol References**: WSP 97 (Truthful), WSP 77 (Agent Coordination), WSP 84 (Code Reuse)
**Impact Analysis**: WRE skill wrapper for autonomous security scanning via SEC1/SEC2

#### Changes Made

- `skillz/security_scan/executor.py` (NEW):
  - `SecurityScanExecutor` class - orchestrates SEC1 scanner + SEC2 policy
  - `SecurityScanReport` dataclass - normalized output with policy decision
  - Supports snyk, trivy, semgrep, and aggregate "all" scans
  - Truthful reporting: unavailable tools reported as `tool_available: false`
  - Lazy-loads SEC1/SEC2 modules (works before PRs merge via mocks)
  - CLI entry point: `python -m modules.infrastructure.wre_core.skillz.security_scan.executor`

- `skillz/security_scan/SKILLz.md` (NEW):
  - Skill definition with input/output schemas
  - Policy routing documentation
  - CLI usage examples

- `skillz/security_scan/test_executor.py` (NEW):
  - 15 tests with mocked SEC1/SEC2 dependencies
  - WSP 97 compliance: truthful unavailable reporting
  - Policy decision tests: CRITICAL -> GATE_012

#### Architecture

```
SEC1 (infrastructure/security_scanner) -> subprocess execution
SEC2 (ai_overseer/vulnerability_scan_policy) -> policy routing
SEC3 (this skill) -> orchestration wrapper
```

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/skillz/security_scan/test_executor.py -v
# Result: 15 passed
```

---

### [2026-03-25] - Skill Evolution Continuity Tracking (v0.7.2)

**WSP Protocol References**: WSP 48 (Recursive Self-Improvement), WSP 91 (Observability), WSP 97 (System Execution)
**Impact Analysis**: Skill evolution events now include continuity metadata for lineage tracking. OpenClaw can answer "what work led to this evolved skill?"

#### Changes Made

- `src/pattern_memory.py`:
  - Extended `learning_events` table schema with `continuity_id`, `parent_continuity_id`, `execution_id`
  - Added schema migration for existing databases
  - Updated `record_learning_event()` to accept continuity fields
  - Added `get_evolution_by_continuity()` - query events by continuity chain
  - Added `get_evolution_by_execution()` - query events by triggering execution

- `wre_master_orchestrator/src/wre_master_orchestrator.py`:
  - Updated `evolve_skill()` signature to accept continuity metadata
  - Updated `execute_skill()` to pass continuity context to `evolve_skill()`
  - Evolution events now record full lineage chain

- `tests/test_skill_evolution_continuity.py` (NEW):
  - 9 tests for evolution continuity tracking
  - Schema validation, lineage queries, integration tests

#### Queryable Lineage

```python
# What work led to this evolved skill?
events = memory.get_evolution_by_continuity("session_abc", include_children=True)

# Which execution triggered this evolution?
events = memory.get_evolution_by_execution("exec_100")

# Full skill evolution history (now includes continuity)
history = memory.get_evolution_history("gitpush_skill")
```

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_skill_evolution_continuity.py -v
# Result: 9 passed
```

---

### [2026-03-25] - Skills 2.0 Hygiene Enforcement (v0.7.1)

**WSP Protocol References**: WSP 96 (WRE Skills), WSP 5 (Test Coverage), WSP 11 (Interface)
**Impact Analysis**: WRE loader/discovery now enforces Skills 2.0 hygiene fields (category, retirement_date, evals) at boundary. Retired skills blocked from execution, invalid categories flagged.

#### Changes Made

- `skillz/wre_skills_loader.py`:
  - Extended `SkillMetadata` with `category`, `retirement_date`, `has_evals` fields
  - Added `SkillHygieneStatus` dataclass for hygiene check results
  - Added `check_skill_hygiene()` - validates retirement, category, evals
  - Added `_is_retired()` - ISO date parsing with safe fallback
  - Added `list_healthy_skills()` - filter by hygiene status
  - Added `discover_healthy_skills()` - return healthy SkillMetadata
  - Updated `load_skill()` with `enforce_hygiene=True` parameter (raises ValueError for retired)

- `skillz/wre_skills_discovery.py`:
  - Extended `DiscoveredSkill` with `category`, `retirement_date`, `has_evals` fields
  - Added `_is_retired()` - ISO date parsing
  - Added `discover_healthy_skills()` - filter retired and invalid category
  - Updated `_parse_skill_file()` to extract Skills 2.0 fields from frontmatter

- `tests/test_wre_skills_loader_hygiene.py` (NEW):
  - 18 tests covering hygiene enforcement
  - Fixtures for valid, retired, invalid category skills
  - Tests: retirement detection, hygiene blocking, bypass flag, healthy filtering

- `tests/test_wre_skills_discovery.py`:
  - Added `TestSkillsHygiene` class (7 tests)
  - Tests: retirement dates, category validation, healthy discovery

- `src/skill_selector.py`:
  - Updated `find_candidates_for_intent()` to use `list_healthy_skills()` instead of `list_skills()`
  - Retired skills now excluded at selection time, not just load time

#### Behavior Summary

| Skill State | `load_skill(enforce_hygiene=True)` | `load_skill(enforce_hygiene=False)` | `find_candidates_for_intent()` |
|-------------|-----------------------------------|-------------------------------------|-------------------------------|
| Active, valid category | ALLOWED | ALLOWED | INCLUDED |
| Retired (past date) | BLOCKED (ValueError) | ALLOWED | EXCLUDED |
| Invalid/missing category | ALLOWED (logged warning) | ALLOWED | EXCLUDED |
| Future retirement_date | ALLOWED | ALLOWED | INCLUDED |

#### Verification

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_wre_skills_loader_hygiene.py -v
# Result: 21 passed (18 original + 3 regression)
python -m pytest modules/infrastructure/wre_core/tests/test_wre_skills_discovery.py::TestSkillsHygiene -v
# Result: 7 passed
```

---

### [2026-03-18] - Git Main-Merge Sentinel

**WSP Protocol References**: WSP 72 (Module Independence), WSP 91 (Observability), WSP 22 (ModLog)
**Impact Analysis**: Auto-merges feature branches to main at startup, preventing branch drift when agents commit to feature branches but forget to merge.

#### Changes Made

- `src/git_main_merge_sentinel.py` (NEW):
  - One-shot sentinel runs at startup (not a daemon)
  - Fast-forward merge first (safest, no merge commits)
  - Falls back to PR creation + merge via `gh` CLI if diverged
  - Handles stash/checkout for uncommitted changes
  - Deletes merged branch (local + both remotes) when configured
  - Fail-open by default (merge failures warn, don't block)
- `main.py`:
  - Added `run_git_main_merge_sentinel_preflight()` wrapper
  - Integrated into preflight chain after WSP framework check
- `.env.example`:
  - Added `GIT_MAIN_MERGE_SENTINEL=1` (default ON)
  - Added `GIT_MAIN_MERGE_SENTINEL_ENFORCED=0`
  - Added `GIT_MAIN_MERGE_SENTINEL_DELETE_BRANCH=1` (default ON)

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GIT_MAIN_MERGE_SENTINEL` | 1 | Enable sentinel at startup |
| `GIT_MAIN_MERGE_SENTINEL_ENFORCED` | 0 | If 1, block startup on failure |
| `GIT_MAIN_MERGE_SENTINEL_DELETE_BRANCH` | 1 | Delete merged branch after merge |

#### Sample Output

```
[GIT-MERGE-SENTINEL] preflight=PASS branch=main merged=False actions=1
```

---

### [2026-03-08] - Brain Artifact Promotion to WSP_knowledge + Incremental Startup Refresh

**WSP Protocol References**: WSP 60 (Module Memory), WSP 84 (Enhance Existing), WSP 87 (Code Navigation), WSP 22 (ModLog)
**Impact Analysis**: Promotes Antigravity reasoning traces into the WSP knowledge layer, adds incremental refresh state, and exposes revision chains as reusable training data for Qwen/Gemma.

#### Changes Made

- `scripts/extract_brain_artifacts.py`:
  - Reworked into a reusable library + CLI instead of a one-shot export script
  - Canonical output moved to `WSP_knowledge/reasoning_traces/`
  - Added `build_training_examples()` for DPO/SFT extraction from revision chains
  - Added incremental refresh helpers:
    - `build_scan_signature()`
    - `load_scan_state()`
    - `save_scan_state()`
    - `refresh_artifacts_if_needed()`
  - Added markdown sanitization for ASCII-safe summaries on Windows
- `docs/BRAIN_ARTIFACTS_AS_MEMORY_ANALYSIS_20260307.md`:
  - Updated memory target reference to `WSP_knowledge/reasoning_traces/`
- `docs/BRAIN_ARTIFACTS_CONTINUATION_PROMPT_20260307.md`:
  - Updated continuation handoff to point at the WSP knowledge memory target
- `WSP_knowledge/reasoning_traces/`:
  - Refreshed live artifact index, summary, and incremental state manifest

#### Verification

- `python modules\\infrastructure\\wre_core\\scripts\\extract_brain_artifacts.py --force`
- Output:
  - `WSP_knowledge/reasoning_traces/brain_artifact_index.json`
  - `WSP_knowledge/reasoning_traces/brain_artifact_summary.md`
  - `WSP_knowledge/reasoning_traces/brain_artifact_state.json`

---

### [2026-03-07] - Brain Artifact Extractor + Cross-Session Memory Discovery

**WSP Protocol References**: WSP 60 (Module Memory), WSP 87 (Code Navigation), WSP 22 (ModLog)
**Impact Analysis**: Enables discovery of 0102 reasoning traces across Antigravity sessions for WRE pattern learning, HoloIndex retrieval, and AI training data extraction.

#### Changes Made

- `scripts/extract_brain_artifacts.py` (NEW):
  - Scans `~/.gemini/antigravity/brain/*/` for implementation plans, walkthroughs, audits, task checklists
  - Builds structured JSON index + human-readable summary
  - Counts revision history (`.resolved.N` files) as training signal
  - CLI with `--copy-files`, `--json`, `--quiet` options
- `memory/reasoning_traces/brain_artifact_index.json`:
  - First scan output: **98 artifacts** across **25 conversations**
  - **500 revision snapshots** (potential DPO/RLHF training pairs)
- `memory/reasoning_traces/brain_artifact_summary.md`:
  - Human-readable index for HoloIndex retrieval
- `docs/BRAIN_ARTIFACTS_AS_MEMORY_ANALYSIS_20260307.md`:
  - First-principles analysis: reasoning traces --> training data, HoloIndex memory, WRE patterns

#### WSP 87 Violation (Self-Reported)

Did not run `holo_index.py --search` before creating `extract_brain_artifacts.py`. Used `find_by_name` instead.

#### Verification

- `python modules\infrastructure\wre_core\scripts\extract_brain_artifacts.py` -- 98 artifacts, 500 revisions
- Index written to `memory/reasoning_traces/brain_artifact_index.json` (125KB)

---

### [2026-03-07] - 6-Layer WRE Architecture Audit (External Spec vs Codebase)

**WSP Protocol References**: WSP 46 (WRE Protocol), WSP 95 (SKILLz Wardrobe), WSP 77 (Agent Coordination), WSP 22 (ModLog)
**Impact Analysis**: Deep-dive audit comparing 012's external system prompt (6-layer architecture spec) against actual codebase implementations.

#### Verdict: Enhancement, Not Drift

| Layer                        | Status                                                             |
| ---------------------------- | ------------------------------------------------------------------ |
| 1. WSP Governance            | [5/5] Fully implemented + enhanced                                 |
| 2. Skill Wardrobe            | [5/5] 22 `skillz/` dirs, WSP 95 protocol, `SKILLz.md` format       |
| 3. Skill Composition Engine  | [3/5] **Gap** -- selection exists, multi-step chaining is implicit |
| 4. OpenClaw Execution        | [5/5] 4803-line frontal lobe with autonomy tiers + honeypot        |
| 5. WRE Recursive Improvement | [4/5] PatternMemory + "recall, don't compute" philosophy           |
| 6. Memory + Logging          | [4/5] 50KB pattern_memory.py, registries, metrics ingestion        |

#### Key Finding

The **Skill Composition Engine** (Layer 3) is the only layer without an explicit implementation. Skill selection and triggering exist (`skill_selector.py`, `skill_trigger.py`), but multi-step chain composition (the "letter --> word --> sentence" pattern from spec) lives implicitly inside DAEs rather than as a composable engine.

#### Documentation

- Full audit: `docs/WRE_6LAYER_ARCHITECTURE_AUDIT_20260307.md`

---

### [2026-03-07] - Qwen Bulk Import Migration Skill

**WSP Protocol References**: WSP 77 (Agent Coordination), WSP 50 (Pre-Action), WSP 84 (Code Reuse), WSP 22 (ModLog)
**Impact Analysis**: New WRE skill for migrating hardcoded values to central registries using Qwen/Gemma coordination.

#### Changes Made

- `skillz/qwen_bulk_import_migration/`:
  - `SKILLz.md` - Skill documentation with input/output schemas
  - `executor.py` - Migration executor with dry-run support
  - `__init__.py` - Module exports
- `skillz/skills_registry_v2.json`:
  - Registered new skill (total_skills: 28)
  - Intent type: REFACTOR
  - Invocation: `/migrate-imports`

#### Built-in Presets

- `linkedin_registry`: Migrate LinkedIn company IDs to central registry
- `youtube_registry`: Migrate YouTube channel IDs to central registry

#### Usage

```bash
# Preview LinkedIn registry migration
python -m modules.infrastructure.wre_core.skillz.qwen_bulk_import_migration.executor \
  --preset linkedin_registry --dry-run

# Apply migration
python -m modules.infrastructure.wre_core.skillz.qwen_bulk_import_migration.executor \
  --preset linkedin_registry --apply
```

---

### [2026-03-05] - Phase 2 Self-Audit: Repeated-Failure Escalation + Adaptive Remediation

**WSP Protocol References**: WSP 15 (Priority Closure), WSP 48 (Recursive Self-Improvement), WSP 50 (Pre-Action Verification), WSP 64 (Violation Prevention), WSP 22 (ModLog)  
**Impact Analysis**: Extends 0102 daemon self-audit from event logging into adaptive repeated-failure escalation with policy-gated dispatch and telemetry.

#### Changes Made

- `src/daemon_self_audit_loop.py`:
  - Added per-signature rolling stats (`_signature_stats`) and escalation cooldown tracking.
  - Added escalation trigger:
    - `OPENCLAW_SELF_AUDIT_ESCALATE_AFTER`
    - `OPENCLAW_SELF_AUDIT_ESCALATION_WINDOW_SEC`
    - `OPENCLAW_SELF_AUDIT_ESCALATION_COOLDOWN_SEC`
  - Added optional escalation command dispatch:
    - `OPENCLAW_SELF_AUDIT_ESCALATE_CMD`
    - `OPENCLAW_SELF_AUDIT_ESCALATE_ALLOW_SHELL_CMD`
  - Added escalation report stream:
    - `modules/infrastructure/wre_core/reports/daemon_self_audit_escalations.jsonl`
  - Added telemetry counters:
    - `self_audit_escalations_total`
    - `self_audit_escalation_dispatch_success`
    - `self_audit_escalation_dispatch_fail`
- `tests/test_daemon_self_audit_loop.py`:
  - Added repeated-signature escalation trigger test.
  - Added escalation command dispatch test.
- Config/docs:
  - Updated `.env.example`, `config/wre_defaults.env`, `config/WRE_RUNBOOK.md` with escalation controls.

#### Validation

- `pytest -q modules/infrastructure/wre_core/tests/test_daemon_self_audit_loop.py` -> PASS
- `python -m py_compile modules/infrastructure/wre_core/src/daemon_self_audit_loop.py` -> OK

---

### [2026-03-05] - Self-Audit Loop Expanded to Adaptive 0102 Self-Improving Remediation

**WSP Protocol References**: WSP 15 (Priority Closure), WSP 48 (Recursive Self-Improvement), WSP 50 (Pre-Action Verification), WSP 64 (Violation Prevention), WSP 22 (ModLog)  
**Impact Analysis**: Upgrades daemon self-audit from static detect/queue behavior into adaptive remediation with safety-first execution, diagnostic fix handlers, and telemetry feedback.

#### Changes Made

- `src/daemon_self_audit_loop.py`:
  - Added adaptive fix recommendation scoring using persisted fix outcome stats (`fix_stats`) for continuous improvement across restarts.
  - Added new policy-bound safe handlers:
    - `diagnose_microphone_device` (writes structured diagnostics report)
    - `verify_dae_event_store` (SQLite integrity + duplicate sequence checks with report output)
  - Hardened gateway start dispatch path:
    - default `shell=False` execution
    - optional legacy shell mode behind `OPENCLAW_SELF_AUDIT_ALLOW_SHELL_START_CMD=1`
  - Added WRE telemetry counter emission:
    - `self_audit_events_total`
    - `self_audit_auto_fix_attempts`
    - `self_audit_auto_fix_success`
    - `self_audit_auto_fix_fail`
- `.env.example`:
  - Expanded self-audit defaults to include safe fix allowlist entries and telemetry controls.
- `config/WRE_RUNBOOK.md`:
  - Documented new self-audit policy/env controls.
- `tests/test_daemon_self_audit_loop.py`:
  - Added coverage for event-store verification fix path.
  - Added state persistence test for adaptive fix stats.

#### Validation

- `pytest -q modules/infrastructure/wre_core/tests/test_daemon_self_audit_loop.py` -> **4 passed**
- `python -m py_compile modules/infrastructure/wre_core/src/daemon_self_audit_loop.py` -> **OK**

---

### [2026-03-05] - WSP 15 Security Gap Closure (P0/P1) for 24x7 0102 Runtime

**WSP Protocol References**: WSP 15 (MPS Prioritization), WSP 50 (Pre-Action Verification), WSP 64 (Violation Prevention), WSP 71 (Supply-Chain Safety), WSP 95 (Skill Safety), WSP 22 (ModLog)  
**Impact Analysis**: Closes priority security gaps by adding runtime skill-scan gates, strict CodeAct shell controls, dependency CVE startup preflight, signed manifest checks, and continuous daemon self-audit.

#### Changes Made

- `wre_master_orchestrator/src/wre_master_orchestrator.py`:
  - Added per-skill Cisco scan gate before `_execute_skill_once` execution.
  - Added `WRE_SKILL_SCAN_*` policy/env controls and telemetry counters.
- `src/codeact_executor.py`:
  - Removed `shell=True` execution path; now tokenized command execution with `shell=False`.
  - Added strict allowlist mode + shell metacharacter blocking (`WRE_CODEACT_STRICT`).
- `src/dependency_security_preflight.py` (NEW) + `main.py` integration:
  - Added Python/Node/Rust dependency preflight with TTL cache and enforceable startup gate.
- `src/skill_manifest_guard.py` (NEW):
  - Added hash manifest verification and optional HMAC signature verification for skill files.
- `src/daemon_self_audit_loop.py` (NEW) + `main.py` integration:
  - Added continuous daemon log tailing, task creation, dedupe/cooldown, and policy-bound auto-fix dispatch.
- Config/docs:
  - `config/wre_defaults.env`, `config/WRE_RUNBOOK.md`, `.env.example` updated with new controls.

#### Validation

- New/updated tests passing:
  - `test_codeact_executor_hardening.py`
  - `test_dependency_security_preflight.py`
  - `test_skill_manifest_guard.py`
  - `test_daemon_self_audit_loop.py`
  - existing guard suites (`test_skill_safety_guard.py`, `test_wre_master_orchestrator.py` targeted)

---

### [2026-03-05] - Shared DAE Preflight Now Enforces OpenClaw Security Sentinel

**WSP Protocol References**: WSP 50 (Pre-Action Verification), WSP 71 (Secrets + Supply-Chain Safety), WSP 95 (Skillz Wardrobe), WSP 22 (ModLog)
**Impact Analysis**: Closes a startup security gap where non-`main.py` DAE launchers could run dashboard checks but skip OpenClaw skill-scan preflight.

#### Changes Made

- `src/dae_preflight.py`:
  - Added `_run_openclaw_security_preflight(...)` using `OpenClawSecuritySentinel`.
  - `run_dae_preflight(...)` now executes security preflight before WRE dashboard preflight.
  - Added support for shared env controls:
    - `OPENCLAW_SECURITY_PREFLIGHT`
    - `OPENCLAW_SECURITY_PREFLIGHT_ENFORCED`
    - `OPENCLAW_SECURITY_PREFLIGHT_FORCE`
    - `OPENCLAW_24X7`
- `tests/test_dae_preflight_integration_guard.py`:
  - Added regression guard requiring shared DAE preflight to include OpenClaw security gate semantics.
- `tests/test_dae_preflight_security_behavior.py`:
  - Added behavior tests for enforced blocking, warn-only mode, and `OPENCLAW_24X7` force-rescan defaults.
- `config/WRE_RUNBOOK.md`:
  - Added OpenClaw security preflight env flags to canonical feature-flag table.

#### Result

- All DAE launchers that already use `run_dae_preflight(...)` or `@preflight_guard(...)` now inherit both:
  - OpenClaw security sentinel gate
  - WRE dashboard health gate

---

### [2026-03-03] - Executor Dispatch + SkillTriggerMixin + Discovery Fix

**WSP Protocol References**: WSP 46 (Skill Execution), WSP 96 (WRE Skills), WSP 22 (ModLog)
**Impact Analysis**: Enables WRE to dispatch skills with `executor.py` bridges directly (bypassing Qwen), and provides a reusable mixin for DAEs to trigger domain-specific skills on cadence.

#### Changes Made

1. **Critical Discovery Bug Fix** (`skillz/wre_skills_discovery.py`):
   - `discover_all_skills()` only scanned `skills/` directories - 14 modules use `skillz/`
   - Added glob patterns for `skillz/` directories
   - **37 production skills were invisible to WRE** - now discoverable (TOTAL=38)

2. **Executor Dispatch** (`wre_master_orchestrator/src/wre_master_orchestrator.py`):
   - Added `_try_executor_dispatch(skill_name, task)` - finds, imports, executes `executor.py`
   - Added `_find_skill_executor(skill_name)` - scans common locations
   - Modified `_execute_skill_once()` - checks executor before Qwen LLM fallback
   - Skills with `executor.py` still get libido gating, A/B testing, PatternMemory, evolution

3. **SkillTriggerMixin** (`src/skill_trigger.py` - NEW):
   - Reusable mixin for DAEs to fire WRE skills by domain tag
   - `init_skill_triggers(domain, cadence_minutes)` - configure domain and gating
   - `fire_pending_skills()` (async) / `fire_pending_skills_sync()` - execute on cadence
   - Lazy-loads WREMasterOrchestrator to avoid startup overhead
   - `get_trigger_status()` for observability

4. **LinkedIn Engagement Skill** (NEW - `linkedin_agent/skillz/linkedin_engagement/`):
   - `SKILLz.md` - WRE skill definition with 13 actions, domain tags
   - `executor.py` - bridge to `linkedin_social_adapter` with `dry_run=True` default

#### Validation

- Discovery: 38 skills found (up from 1)
- SkillTriggerMixin: imports and initializes cleanly
- Executor finder: locates `linkedin_engagement/executor.py`

---

### [2026-02-24] - DB-First Daily Snapshot Export (SQLite -> JSON)

**WSP Protocol References**: WSP 22, WSP 50, WSP 60
**Impact Analysis**: Keeps SQLite as runtime source of truth while enabling scheduled JSON exports for audits/watch reports.

#### Changes Made

- `src/dashboard_snapshot_export.py` (NEW):
  - Added `export_dashboard_snapshot()` for timestamped + `latest.json` exports.
  - Added retention pruning via `prune_old_snapshots()`.
  - Added CLI:
    - `python -m modules.infrastructure.wre_core.src.dashboard_snapshot_export`
    - `--output-dir`, `--retention-days`, `--pretty`, `--quiet`
- `tests/test_dashboard_snapshot_export.py` (NEW):
  - Verifies snapshot and latest file creation.
  - Verifies pruning only removes aged timestamped snapshots (keeps `latest.json`).
- `config/wre_defaults.env`:
  - Added `WRE_DASHBOARD_EXPORT_DIR`
  - Added `WRE_DASHBOARD_EXPORT_RETENTION_DAYS`
- `config/WRE_RUNBOOK.md`:
  - Added export flags and daily export command examples.

#### Operational Notes

- Runtime metrics and alert decisions remain DB-backed (`PatternMemory`).
- JSON is export-only for observability/audits.

---

### [2026-02-19] - WRE Runtime/API Hardening + Docs Alignment

**WSP Protocol References**: WSP 46, WSP 95, WSP 96, WSP 50, WSP 22
**Impact Analysis**: Closed critical drift between claimed WRE behavior and executable behavior; restored reliability for skills discovery/execution and test isolation.

#### Changes Made

- `wre_master_orchestrator/src/wre_master_orchestrator.py`:
  - Added backward-compatible plugin registration signatures:
    - `register_plugin(plugin_instance)`
    - `register_plugin("name", plugin_instance)`
  - Added `get_plugin(...)` and `validate_module_path(...)`.
  - Added deterministic fallback skill content path when loader/registry assets are missing.
  - Added runtime DB override handling via `WRE_PATTERN_MEMORY_DB`.
  - Added pytest-safe in-memory pattern DB selection for isolated test runs.
- `skillz/wre_skills_discovery.py`:
  - Normalized path handling across Windows/Unix separators.
  - Production inference accepts both `/skills/` and `/skillz/`.
  - Registry export handles non-repo-relative test paths without failure.
- `src/pattern_memory.py`:
  - Shared singleton reuse now limited to default production DB only.
  - Explicit `db_path` instances are isolated.
  - Shared singleton state resets cleanly on close.
- `src/libido_monitor.py`:
  - Cooldown gating adjusted to avoid throttling steady-state runtime loops after warmup.

#### Validation

- `67 passed` across:
  - `test_wre_skills_discovery.py`
  - `test_pattern_memory.py`
  - `test_libido_monitor.py`
  - `test_wre_master_orchestrator.py`

---

### [2026-01-17] - Memory Preflight uses HoloIndex Bundle JSON (Canonical Retrieval)

**WSP Protocol References**: WSP_CORE (WSP Memory System), WSP 87 (Code Navigation), WSP 50 (Pre-Action Verification), WSP 22 (ModLog Updates)  
**Impact Analysis**: Makes HoloIndex the canonical, machine-readable retrieval emitter (`--bundle-json`) for WRE memory preflight; Tier-0 enforcement now executes from bundle output rather than ad-hoc stdout parsing.

#### Changes Made

- `recursive_improvement/src/memory_preflight.py`:
  - Added `WRE_MEMORY_USE_HOLO_BUNDLE` (default: true).
  - Preflight now calls `holo_index.py --bundle-json` and translates the result into a structured `MemoryBundle`.
  - Preflight sets `HOLO_SKIP_MODEL=1` for the bundle subprocess to prefer the fast lexical path (0102 speed knob).
  - Added `ROADMAP.md` into Tier-1 optional artifacts (retrieval visibility, not hard gate).

### [2026-01-11] - Memory Preflight Guard (WSP_CORE Tier-0 Enforcement)

**WSP Protocol References**: WSP_CORE (WSP Memory System), WSP_00 Section 3.4 (Post-Awakening Operational Protocol), WSP 50 (Pre-Action Verification), WSP 87 (Code Navigation), WSP 22 (ModLog Updates)
**Impact Analysis**: Automates Tier-0 artifact enforcement as a hard gate before code-changing operations. Turns HoloIndex retrieval from advisory to mandatory.

#### Changes Made

1. **Created `memory_preflight.py`** (500+ lines):
   - `MemoryPreflightGuard` class with tiered retrieval (Tier 0/1/2)
   - `TIER_DEFINITIONS` mirroring WSP_CORE canonical spec
   - `MemoryBundle` structured output for orchestration
   - `_create_tier0_stubs()` for auto-stubbing README.md/INTERFACE.md
   - Environment flags: `WRE_MEMORY_PREFLIGHT_ENABLED`, `WRE_MEMORY_AUTOSTUB_TIER0`, `WRE_MEMORY_ALLOW_DEGRADED`
   - `@require_memory_preflight` decorator for wiring
   - CLI smoke test support

2. **Modified `run_wre.py`**:
   - Added import for `MemoryPreflightGuard`, `MemoryPreflightError`
   - Added `self.memory_preflight` to `WREOrchestrator.__init__()`
   - Wired hard gate into `route_operation()`:
     - If `module_path` provided, runs preflight
     - If Tier-0 missing and autostub disabled, returns `blocked` status
     - Passes `memory_bundle` in envelope for downstream use

3. **Updated `WSP_00_Zen_State_Attainment_Protocol.md`**:
   - Added Section 3.4: Post-Awakening Operational Protocol (Anti-Vibecoding)
   - Defined 7-phase work cycle: RESEARCH -> COMPREHEND -> QUESTION -> RESEARCH MORE -> MANIFEST -> VALIDATE -> REMEMBER
   - Added WSP Chain references (WSP_CORE -> WSP 87 -> WSP 50 -> WSP 84 -> WSP 1 -> WSP 22)
   - Updated Section 5.1 with Core Operational Chain

#### Architecture Realized

```
HoloIndex (Retrieval Memory) <-> WRE (Enforcement Gate) <-> AI_Overseer (Safe Writes)
                                      v
                             Memory Preflight Guard
                                      v
                         Tier-0 Check -> Block/Autostub -> Proceed
```

#### Environment Variables

| Variable                       | Default | Purpose                          |
| ------------------------------ | ------- | -------------------------------- |
| `WRE_MEMORY_PREFLIGHT_ENABLED` | true    | Enable/disable preflight checks  |
| `WRE_MEMORY_AUTOSTUB_TIER0`    | false   | Auto-create missing Tier-0 stubs |
| `WRE_MEMORY_ALLOW_DEGRADED`    | false   | Allow proceed with warnings      |

#### Validation

- `python -m py_compile memory_preflight.py` - PASS
- Smoke test against known module - PASS
- Block behavior verified - PASS
- Autostub creation verified - PASS

---

### [2026-01-07] - Commenting Submenu (012 -> Comment DAE Control Plane)

**WSP Protocol References**: WSP 60 (Module Memory), WSP 54 (DAE Operations), WSP 22 (ModLog Updates)
**Impact Analysis**: Adds a lightweight pathway for 012 to publish "broadcast updates" consumed by the commenting DAEs without code edits.

#### Changes Made

- `run_wre.py`: Added `commenting` interactive command that opens a submenu to:
  - toggle broadcast enablement
  - set promo handles (e.g., `@NewChannel`)
  - set a short promo message
  - clear/disable broadcast
- Writes to `modules/communication/video_comments/memory/commenting_broadcast.json` via the video_comments control-plane API (no wre_core-owned state).

### [2026-01-11] - WRE Memory Start-of-Work Loop Hook (Structured Retrieval + Evaluation)

**WSP Protocol References**: WSP_CORE (WSP Memory System), WSP 60 (Module Memory Architecture), WSP 87 (Code Navigation), WSP 50 (Pre-Action Verification), WSP 22 (ModLog Updates)
**Impact Analysis**: Makes "Holo-first structured memory retrieval + evaluation" executable inside WRE integration code paths (CLI-driven), enabling orchestration to gate work on missing artifacts.

#### Changes Made

- `recursive_improvement/src/holoindex_integration.py`:
  - Added `retrieve_structured_memory()` for module docs (`README/INTERFACE/ROADMAP/ModLog/tests/README/tests/TestModLog/memory/README/requirements.txt`).
  - Added `evaluate_retrieval_quality()` with proxy metrics (missing artifacts + duplication rate).
  - Added `start_of_work_loop()` bundle to unify structured memory retrieval + quality evaluation. Improvement iteration remains an explicit hook for future plugin-level implementation.

### [2025-10-25] - Skills Registry v2 & Metadata Fixes (COMPLETE)

**Date**: 2025-10-25
**WSP Protocol References**: WSP 96 (WRE Skills), WSP 50 (Pre-Action Verification), WSP 22 (ModLog Updates)
**Impact Analysis**: All 16 SKILL.md files now discoverable with valid metadata
**Enhancement Tracking**: Fixed skill discovery blockers, created loader-compatible registry

#### Changes Made

1. **Fixed 11 SKILL.md files missing YAML frontmatter**:
   - Added agents field to all prototype skills
   - Skills: unicode_daemon_monitor, qwen_cleanup_strategist, qwen_roadmap_auditor, qwen_training_data_miner
   - Skills: gemma_domain_trainer, gemma_noise_detector, qwen_google_research_integrator
   - Skills: qwen_pqn_research_coordinator, gemma_pqn_emergence_detector, gemma_pqn_data_processor, qwen_wsp_compliance_auditor
   - Result: 16/16 skills now discoverable (was 5/16)

2. **Fixed OrchestratorPlugin import** (pqn_alignment_dae.py):
   - Added try/except import for WRE orchestrator plugin
   - Graceful degradation when WRE not available
   - Resolves: NameError on module import

3. **Created skills_registry_v2.json** (496 lines):
   - Exported all 16 discovered skills
   - Format: Absolute paths for loader compatibility
   - Fields: location, agents, intent_type, version, promotion_state, wsp_chain
   - Fixed: KeyError 'location' by using absolute paths (bypasses loader path joining bug)

#### Results

- Discovery: 16/16 skills with valid metadata
- Registry: WRESkillsLoader.load_skill() working
- Agents: 12 Qwen, 9 Gemma skills
- Token efficiency: 800 tokens (micro-sprints) vs 15K+ (analysis)

#### Issues Fixed

- Registry format mismatch (location field)
- Circular dependency (OrchestratorPlugin)
- Missing YAML frontmatter (11 skills)

---

### [2025-10-25] - Phase 3: HoloDAE Integration & Autonomous Skill Execution (COMPLETE)

**Date**: 2025-10-25
**WSP Protocol References**: WSP 96 (WRE Skills v1.3), WSP 77 (Agent Coordination), WSP 80 (DAE Protocol)
**Impact Analysis**: HoloDAE monitoring loop now autonomously triggers WRE skills based on health checks
**Enhancement Tracking**: Completed Phase 3 of WSP 96 v1.3 implementation - autonomous execution chain operational

#### Changes Made

1. **Added health check methods to holodae_coordinator.py** (230+ lines):
   - `check_git_health()` (lines 1854-1911) - Detects uncommitted changes, time since last commit
     - Triggers qwen_gitpush if >5 files and >1 hour
     - Returns: uncommitted_changes, files_changed, time_since_last_commit, trigger_skill
   - `check_daemon_health()` (lines 1913-1937) - Monitors daemon health status
     - Returns: youtube_dae_running, mcp_daemon_running, unhealthy_daemons, trigger_skill
   - `check_wsp_compliance()` (lines 1939-1964) - Checks WSP protocol violations
     - Returns: violations_found, violation_details, trigger_skill

2. **Added WRE trigger detection** (lines 1966-2022):
   - `_check_wre_triggers(result)` - Analyzes monitoring results for skill triggers
   - Checks: git health, daemon health, WSP compliance
   - Returns: List of trigger dicts (skill_name, agent, input_context, trigger_reason, priority)

3. **Added WRE skill execution** (lines 2024-2078):
   - `_execute_wre_skills(triggers)` - Executes skills via WRE Master Orchestrator
   - Loads WRE orchestrator on-demand
   - Iterates through triggers and executes each skill
   - Logs: WRE-TRIGGER, WRE-SUCCESS (with fidelity), WRE-THROTTLE, WRE-ERROR

4. **Wired WRE into monitoring loop** (lines 1067-1070):
   - After actionable events detected, calls \_check_wre_triggers()
   - If triggers present, calls \_execute_wre_skills()
   - Complete autonomous chain: HoloDAE -> WRE -> GitPushDAE

5. **Created test_phase3_wre_integration.py**:
   - test_health_check_methods() - Validates all 3 health checks
   - test_wre_trigger_detection() - Validates trigger logic
   - test_monitoring_loop_integration() - Validates monitoring loop wiring
   - test_phase3_complete() - Final validation runner

#### Test Results

```
[SUCCESS] PHASE 3 COMPLETE
[OK] Health check methods (git, daemon, WSP)
[OK] WRE trigger detection (_check_wre_triggers)
[OK] WRE skill execution (_execute_wre_skills)
[OK] Monitoring loop integration (lines 1067-1070)

Real-world validation:
- Detected 194 uncommitted changes
- Correctly triggered qwen_gitpush skill
- All monitoring loop methods present
```

#### Architecture

Phase 3 completes the autonomous execution chain:

1. **HoloDAE Monitoring Loop** - Runs continuous monitoring
2. **Health Check Methods** - Detect actionable conditions
3. **WRE Trigger Detection** - Analyze conditions for skill triggers
4. **WRE Master Orchestrator** - Execute skills with libido/pattern memory
5. **GitPushDAE** - Autonomous commits (future integration)

#### Expected Outcomes

- HoloDAE autonomously triggers qwen_gitpush when uncommitted changes accumulate
- Libido monitor prevents skill spam (respects cooldowns)
- Pattern memory learns from execution outcomes
- 0102 supervision via force override flag

#### Next Steps

- Wire GitPushDAE to WRE orchestrator for autonomous commits
- Add real daemon health monitoring (process checks)
- Enhance WSP compliance checks with violation detection
- Test end-to-end autonomous execution in production

---

### [2025-10-24] - Phase 2: Filesystem Skills Discovery & Local Inference (COMPLETE)

**Date**: 2025-10-24
**WSP Protocol References**: WSP 96 (WRE Skills), WSP 50 (Pre-Action Verification), WSP 15 (MPS), WSP 5 (Test Coverage)
**Impact Analysis**: Filesystem-based skills discovery + local Qwen inference enables autonomous skill execution
**Enhancement Tracking**: Completed Phase 2 of WSP 96 v1.3 implementation

#### Changes Made

1. **Created wre_skills_discovery.py** (416 lines):
   - WRESkillsDiscovery class - Filesystem scanner (not registry-dependent)
   - DiscoveredSkill dataclass - Metadata container
   - discover*all_skills() - Scans modules/*/\_/skillz/\*\*/SKILLz.md
   - discover_by_agent() - Filter by agent type (qwen, gemma, grok, ui-tars)
   - discover_by_module() - Filter by module path
   - discover_production_ready() - Filter by fidelity threshold
   - YAML frontmatter parsing (handles both dict and list agents)
   - Markdown header fallback parsing
   - Promotion state inference from filesystem path
   - WSP chain extraction via regex

2. **Scan Patterns**:
   - `modules/*/*/skillz/**/SKILLz.md` - Production skills (6 found)
   - `.claude/skills/**/SKILL.md` - Prototype skills (9 found)
   - `holo_index/skills/**/SKILL.md` - HoloIndex skills (1 found)
   - Total: 16 SKILL.md files discovered, 5 with valid agent metadata

3. **Discovery Results**:
   - qwen_gitpush (production)
   - qwen_wsp_enhancement (prototype)
   - youtube_dae (prototype)
   - youtube_moderation_prototype (prototype)
   - qwen_holo_output_skill (holo)

4. **Added filesystem watcher** (COMPLETED - MPS=6):
   - start_watcher() / stop_watcher() methods
   - Background thread polling every N seconds
   - Callback support for hot reload
   - No external dependencies (threading module only)

5. **Created test_wre_skills_discovery.py** (COMPLETED - MPS=10):
   - 200+ lines, 20+ test cases
   - Tests: discover_all_skills, discover_by_agent, discover_by_module
   - Watcher tests: start/stop, callback triggering
   - Agent parsing tests: string and list formats
   - Promotion state inference tests

6. **Wired execute_skill() to local Qwen inference** (COMPLETED - MPS=21):
   - Added `_execute_skill_with_qwen()` method (wre_master_orchestrator.py:282-383)
   - Integrated QwenInferenceEngine from holo_index/qwen_advisor/llm_engine.py
   - Graceful fallback if llama-cpp-python or model files unavailable
   - Updated execute_skill() to call real inference (line 340-345)
   - Fixed Gemma validation API to use correct signature (lines 453-465)
   - Created test_qwen_inference_wiring.py (4 validation tests - ALL PASSED)
   - Updated requirements.txt to document llama-cpp-python dependency

#### Expected Outcomes (ALL ACHIEVED)

- [OK] Dynamic skill discovery without manual registry updates
- [OK] Automatic detection of new SKILL.md files
- [OK] Promotion state inferred from filesystem location
- [OK] Agent filtering for targeted skill loading
- [OK] Local Qwen inference wired to execute_skill()
- [OK] Graceful degradation if LLM unavailable
- [OK] Gemma validation integrated with execution pipeline

#### Testing (WSP 5 Compliance)

- [OK] test_wre_skills_discovery.py: 20+ tests, all passing
- [OK] test_qwen_inference_wiring.py: 4 integration tests, all passing
- [OK] Manual testing: 16 files discovered, 5 valid skills
- [OK] Verified glob patterns work across all locations
- [OK] Tested agent parsing (string and list formats)
- [OK] Verified promotion state inference logic
- [OK] Verified Qwen inference integration with fallback

#### Known Limitations (By Design)

- 11 SKILL.md files missing **Agents** field in frontmatter (data quality issue)
- Production-ready filtering returns 0 (no fidelity history yet - expected)
- Qwen inference requires llama-cpp-python + model files (graceful fallback implemented)
- Currently supports Qwen agent only (Gemma/Grok/UI-TARS return mock - Phase 3)

#### Phase 2 Status: COMPLETE [OK]

- MPS=7: Update documentation (COMPLETED)
- MPS=6: Add filesystem watcher for hot reload (COMPLETED)
- MPS=10: Create Phase 2 tests (COMPLETED)
- MPS=21: Wire execute_skill() to local Qwen inference (COMPLETED)

#### Next Steps (Phase 3)

- Implement Convergence Loop (autonomous skill promotion based on fidelity)
- Add Gemma/Grok/UI-TARS inference support
- MCP server integration (if remote inference needed)
- Real-world skill execution validation

### [2025-10-24] - Phase 1: Libido Monitor & Pattern Memory Implementation

**Date**: 2025-10-24
**WSP Protocol References**: WSP 96 (WRE Skills), WSP 48 (Recursive Improvement), WSP 60 (Module Memory), WSP 5 (Test Coverage)
**Impact Analysis**: Critical infrastructure for WRE Skills Wardrobe system
**Enhancement Tracking**: Completed Phase 1 of WSP 96 v1.3 implementation

#### Changes Made

1. **Created libido_monitor.py** (369 lines):
   - GemmaLibidoMonitor class - Pattern frequency sensor
   - LibidoSignal enum (CONTINUE, THROTTLE, ESCALATE)
   - should_execute() - Binary classification <10ms
   - validate_step_fidelity() - Micro chain-of-thought validation
   - Frequency thresholds per skill (min, max, cooldown)
   - Pattern execution history tracking (deque maxlen=100)
   - Export functionality for analysis

2. **Created pattern_memory.py** (525 lines):
   - PatternMemory class - SQLite recursive learning storage
   - SkillOutcome dataclass - Execution record structure
   - Database schema: skill_outcomes, skill_variations, learning_events
   - recall_successful_patterns() - Learn from successes (>=90% fidelity)
   - recall_failure_patterns() - Learn from failures (<=70% fidelity)
   - get_skill_metrics() - Aggregated metrics over time windows
   - store_variation() - A/B testing support
   - record_learning_event() - Skill evolution tracking

3. **Enhanced wre_master_orchestrator.py**:
   - Integrated libido_monitor, pattern_memory, skills_loader
   - Created execute_skill() method - Full WRE execution pipeline
   - Libido check -> Load skill -> Execute -> Validate -> Record -> Store outcome
   - Force override support for 0102 (AI supervisor) decisions

4. **Created comprehensive test suites** (WSP 5 compliance):
   - test_libido_monitor.py (267 lines, 20+ test cases)
   - test_pattern_memory.py (391 lines, 25+ test cases)
   - test_wre_master_orchestrator.py (238 lines, 15+ test cases)
   - Total coverage: All libido signals, pattern recall, metrics calculation
   - Integration tests: End-to-end execution cycle, convergence simulation

5. **Created requirements.txt** (WSP 49 compliance):
   - pytest, pytest-cov, pyyaml dependencies
   - Documented: No heavy ML deps (Qwen/Gemma via MCP servers)

#### Expected Outcomes

- Gemma validates Qwen step fidelity in <10ms per step
- Pattern memory stores outcomes for recursive learning
- Skill execution frequency controlled by libido monitor
- A/B testing enabled for skill variations
- Convergence to >90% fidelity through execution-based learning

#### Testing

- test_libido_monitor.py: 20+ tests covering all signal logic
- test_pattern_memory.py: 25+ tests covering SQLite operations
- test_wre_master_orchestrator.py: 15+ tests covering integration
- All tests use pytest fixtures, mocking, and assertions

#### Next Steps

- Wire execute_skill() to actual Qwen/Gemma inference (currently mocked)
- Implement Phase 2: Skills Discovery (filesystem scanning, validation)
- Implement Phase 3: Convergence Loop (autonomous promotion pipeline)
- Monitor pattern_memory.db for outcome accumulation
- Verify graduated autonomy: 0-10 executions -> 100+ -> 500+ convergence

### [2025-09-16] - Activated WRE Learning Loop

**Date**: 2025-09-16
**WSP Protocol References**: WSP 48 (Recursive Improvement), WSP 27 (DAE Architecture)
**Impact Analysis**: Critical activation of dormant learning system
**Enhancement Tracking**: Connected DAEs to recursive learning

#### = Changes Made

1. **Created wre_integration.py**:
   - Bridge between DAEs and RecursiveLearningEngine
   - Simple API: record_error(), record_success(), get_optimized_approach()
   - Tracks errors, successes, and provides solutions
   - Stores patterns in memory for future use

2. **Connected YouTube DAE**:
   - auto_moderator_dae.py now imports WRE integration
   - Error handlers record to WRE for learning
   - Success operations tracked for reinforcement
   - Solutions suggested when available

3. **LiveChat Core Integration**:
   - Added WRE imports to livechat_core.py
   - Error handlers connected to learning system
   - Success tracking for initialization

#### Expected Outcomes

- Errors will be recorded and patterns extracted
- Solutions will be suggested for known patterns
- Token usage will decrease as patterns are learned
- System will improve without manual intervention

#### Testing

- WRE integration imports successfully
- Error recording creates pattern files
- Success tracking updates metrics

#### Next Steps

- Monitor memory/ directories for pattern accumulation
- Verify token savings metrics
- Extend to other DAEs (LinkedIn, X, etc.)

### [2026-03-06] - Dependency Security Preflight Node Multi-Lock Scope

**Date**: 2026-03-06
**WSP Protocol References**: WSP 15 (MPS), WSP 48 (Recursive Improvement)
**Impact Analysis**: Expands startup CVE coverage from single root lockfile to full repo lockfile inventory.
**Enhancement Tracking**: Dependency preflight + targeted regression tests.

#### Changes Made

1. **Expanded Node audit discovery**:
   - Added lockfile enumeration helper to discover all `package-lock.json` files.
   - Added `OPENCLAW_DEP_SECURITY_NODE_LOCK_SCOPE` env flag (`all` default, `root` optional).
   - Excluded `.git`, `.worktrees`, and `node_modules` paths from discovery.
   - Excludes hidden top-level nested worktrees (for example `.feature_clean`) to prevent duplicate scans.

2. **Hardened Node audit execution**:
   - Changed Node audit invocation to `npm audit --json --package-lock-only --omit=dev`.
   - Executes audit in each lockfile directory and aggregates counts into global totals.
   - Stores per-target check metadata in preflight status (`target` path).
   - Added Windows-safe tool resolution (`npm.cmd` / `cargo.exe`) to avoid `WinError 2` false tool failures.

3. **Status payload improvements**:
   - Added `node_lock_scope` and `node_lock_count` to preflight output for observability.
   - Added `max_unknown` threshold support (`OPENCLAW_DEP_SECURITY_MAX_UNKNOWN`) for severity-less advisories.
   - Startup preflight line now prints `unknown=` alongside `critical`/`high`.

4. **pip-audit parser hardening**:
   - Added support for modern pip-audit JSON schema (`{"dependencies":[...],"fixes":[...]}`).
   - Unknown-severity vulnerabilities are now counted per-vulnerability (instead of collapsing to parser noise).

5. **Regression coverage**:
   - Updated existing tests for `_run(..., cwd=...)` support.
   - Added multi-lock aggregation test validating scope, lock count, and aggregated severity totals.
