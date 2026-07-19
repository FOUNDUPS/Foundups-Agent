# Agent Module TestModLog

## 2026-07-19 - Transport-neutral Hermes grounding tests

- Proved plain-text v2 requests use host identity/scope and submit a verified grounded intent to the canonical resident client.
- Proved identity, FoundUp scope, and caller-supplied grounding substitutions fail before the cycle runner.
- Proved the default repo-target route succeeds and external research fails closed without an approved adapter.
- Proved the bridge requires both authenticated principal and authorized FoundUp scope.
- Full agent regression: 1145 tests passed.

## 2026-07-19 - Resident RedDog Hermes thin-client tests

- Proved Hermes submit uses the canonical resident client and does not invoke the Hermes model/builder path.
- Proved reconnect, cancel, and resume use the persisted intent and reject replacement-intent substitution.
- Proved payload identity text, wrong schema, and unsupported operations fail before the cycle runner.
- Proved the one-shot bridge requires a host-authenticated principal and contains no shell or Hermes model imports.
- Proved unset host paths are omitted rather than forwarded as empty runtime overrides.
- Full `modules/foundups/agent/tests` validation: 1140 passed.

## 2026-06-20 - Package __init__ lazy-import boundary tests (FOUNDUP_AGENT_PACKAGE_INIT_LAZY_IMPORT_PHASE1)

**Commands** (PYTHONIOENCODING=utf-8):

```bash
python -m pytest modules/foundups/agent/tests/test_package_init_lazy_import.py -q
python -m pytest modules/foundups/agent -q                              # CI mode
AI_OVERSEER_HEAVY_TESTS=1 python -m pytest modules/foundups/agent -q    # heavy mode
```

**Result**: PASS

**Summary**:
- `test_package_init_lazy_import.py`: 8 passed (new file). Full agent suite: **1024 passed** in BOTH
  CI and heavy mode (was 1016 + 8 new = 1024). No skip/xfail, no regression.

**New coverage (closes the no-vendor boundary at the IMPORT boundary -- decision B)**:
1. `test_leaf_adapter_import_no_vendor_pullin` -- FRESH child interpreter: importing
   `kanban_plugin_contract` leaves none of
   `hermes_adapter`/`hermes_model_router`/`subprocess`/`sqlite3`/`urllib` in child `sys.modules`.
   (The publish adapter is parked in a different worktree; the #807 contract leaf is the present
   AST-clean adapter-side leaf.)
2. `test_leaf_contract_import_no_vendor_pullin` -- same proof for a 2nd independent AST-clean leaf
   (`source_authority`).
3. `test_all_public_exports_still_resolve` -- `__all__` unchanged (8 names); each resolves lazily,
   non-None, correct type, identity-stable on 2nd access.
4. `test_lazy_access_loads_hermes_only_on_demand` -- fresh child: `hermes_adapter` ABSENT until a
   public name is accessed, then PRESENT.
5. `test_lazy_access_resolves_value_identical_to_source` -- package names ARE the same objects as
   `hermes_adapter`/`hermes_model_router` exports (no behavior change).
6. `test_no_circular_import` -- package + both leaves + both hermes modules import in 3 orders
   (incl. reverse) with returncode 0.
7. `test_unknown_attribute_raises_AttributeError` -- bogus attr -> AttributeError (not ImportError).
8. `test_dir_includes_public_names` -- `__dir__` surfaces the lazy public names.

**Test method note**: proofs 1/2/4/6 run in a FRESH child interpreter via
`subprocess.run([sys.executable, "-c", SNIPPET])` because pytest may already have imported
subprocess/sqlite3/urllib in THIS process. The `subprocess` used in the test file is the HARNESS that
spawns the child; the boundary assertion is about the CHILD's clean `sys.modules`.

## 2026-06-20 - Kanban Contract dict-key redaction + token-precise command tests (FOUNDUP_KANBAN_CONTRACT_REDACT_KEYS_AND_PRECISE_COMMAND_MATCH_PHASE1)

**Commands** (PYTHONIOENCODING=utf-8):

```bash
python -m pytest modules/foundups/agent/tests/test_kanban_plugin_contract.py -q
AI_OVERSEER_HEAVY_TESTS=1 python -m pytest modules/foundups/agent -q   # heavy
python -m pytest modules/foundups/agent -q                            # CI mode
```

**Result**: PASS

**Summary**:
- `test_kanban_plugin_contract.py`: 319 passed (was 251; +68 net new). Full agent suite:
  **1016 passed** in BOTH heavy and CI mode. No skip/xfail, no regression.

**New coverage (this slice -- closes the parked-adapter RE-REVIEW findings)**:
1. **Fix 1 -- dict-KEY redaction** (`_redact_deep`): a secret used as a string dict KEY (and as a
   value) is redacted; a secret-as-KEY nested several levels deep is redacted; non-string keys
   (int/tuple) pass through unchanged; `_redact_deep` does NOT mutate the input mapping (a NEW
   structure is built); through `KanbanCardSpec.to_dict()` a secret hidden as a dict KEY inside a
   list field appears in NEITHER keys NOR values of the serialized body, and the instance is not
   mutated.
2. **Fix 2 -- token-precise command-key match** (`_key_is_command`):
   - true command keys (command/cmd/shell/script/exec/argv + run_command/runCmd/exec_now/
     shell_command/run_cmd) are detected;
   - legit substring fields (description/transcript/subscription/executive/scripted/prescription/
     descriptor/executive_summary/scripted_notes/subscription_id/transcription) are NOT command keys;
   - direct contrast test: `script` is a command key, `description`/`transcript` are not.
3. **Must-catch / must-not-catch through the validator**: a bare string under any TRUE command key
   (incl. multi-token forms) is REJECTED; `command: "rm -rf /"` rejected; a valid all-safe argv list
   under a true command key is ACCEPTED; description/transcript with an ordinary string value are
   ACCEPTED.
4. **Two-directional parity batteries**:
   - `_FALSE_POSITIVE_BATTERY` (NEW invariant #843 lacked): a corpus of legit field names that
     CONTAIN a command-marker substring, carrying ordinary string values, are ALL ACCEPTED;
     `test_false_positive_battery_zero_falsely_rejected_summary` asserts ZERO falsely rejected.
   - `test_authority_detection_not_weakened_by_token_match`: the whole `_ORIGIN_REJECTED_CARDS`
     AUTHORITY corpus stays rejected (0 newly accepted) -- the command-KEY change does not weaken
     authority detection.
   - `test_command_marker_set_is_single_token`: the marker set is single-token by construction.
- Imports extended: `_redact_deep`, `_key_is_command`, `_COMMAND_KEY_MARKERS`.
- ASCII-clean: the synthetic secret is built via `chr()` (0 non-ASCII bytes).
- AUDIT cross-check (NOT a committed test): origin/main module vs HEAD over the corpus confirmed
  0 authority weakening, true-command-keys still reject bare strings, and description/transcript/...
  flip REJECTED(origin)->ACCEPTED(HEAD); secret-as-key survives origin `to_dict()` but not HEAD.

---

## 2026-06-19 - Kanban Contract card-redaction + command-argv tests (FOUNDUP_KANBAN_CONTRACT_CARD_REDACTION_AND_COMMAND_ARGV_PHASE1)

**Commands** (PYTHONIOENCODING=utf-8):

```bash
python -m pytest modules/foundups/agent/tests/test_kanban_plugin_contract.py -q
AI_OVERSEER_HEAVY_TESTS=1 python -m pytest modules/foundups/agent -q   # heavy
python -m pytest modules/foundups/agent -q                            # CI mode
```

**Result**: PASS

**Summary**:
- `test_kanban_plugin_contract.py`: 251 passed (was 135; +116 net new). Full agent suite:
  948 passed in BOTH heavy and CI mode (was 832; +116 from the new contract tests). No
  skip/xfail, no regression.

### SENTINEL re-audit addendum (empty argv-list strengthening)

`_command_value_is_argv_or_null` accepted an EMPTY argv list `[]` (`all([])` is True),
contradicting its "NON-EMPTY argv LIST" docstring. The code was aligned to the contract so `[]`
is now REJECTED (strictly a strengthening; 0 newly-accepted, parity preserved). New tests:
- `test_command_empty_argv_list_rejected` (parametrized over command/cmd/argv/shell/exec/run_cmd/script):
  `{"<cmd_key>": []}` is REJECTED.
- `test_command_empty_argv_rejection_no_raw_echo`: the empty-list rejection names the rule class only.
- `test_command_null_and_nonempty_argv_still_accepted`: null/absent command and a NON-EMPTY all-safe
  argv list are STILL accepted.
- Added 7 empty-argv-list cases (one per command key) to `_NEW_REJECTED_BARE_COMMANDS` so the
  no-weakening battery + `test_no_weakening_zero_newly_accepted_summary` cover the strengthening
  (still 0 origin-rejected payloads newly accepted).

**New coverage (this slice)**:
1. **Finding A -- card `to_dict()` redaction**: a raw secret in a scalar free-text field (branch)
   and in a nested list field (expected_evidence / required_gates) does NOT appear in `to_dict()`
   ([REDACTED] present); redaction is deterministic and does NOT mutate the instance.
2. **CARD_ID_FROM_REDACTED_CANONICAL_BODY**: a sha256 digest over `to_dict()` is stable across two
   cards differing ONLY in a secret's raw bytes (both collapse to the same redacted canonical body).
3. **"adapter would now serialize safely"**: the exact property the parked publish adapter relies on
   -- a card carrying a secret yields a `to_dict()` with no raw secret.
4. **Finding B -- command argv-or-null**: bare metachar-free command strings (command/cmd/argv/
   shell/exec/run_cmd/script, incl. nested) REJECTED; argv LIST accepted ONLY if every element is a
   safe string (shell-metachar / authority / absolute / traversal / non-string element -> rejected);
   null/None command accepted; dict command rejected. No raw command echoed in any message.
5. **No-weakening behavioral parity battery** (REPLACES the prior AST-skeleton baseline test, which
   no longer applies to a logic change): a self-contained, checked-in corpus of origin-rejected
   inputs (authority markers + ~13 normalized evasions + source_authority promotion + verified=true
   + ~10 authority-by-value + path-hygiene + shell-metachar command cases) re-asserted REJECTED by
   HEAD; the NEW bare/unsafe command inputs asserted REJECTED; clean valid inputs asserted ACCEPTED;
   a summary guard asserts ZERO origin-rejected payloads are newly accepted. NO runtime git-show in
   the committed tests (the #830 shallow-CI lesson).

**Updated (outcome preserved, OLD pinned text refreshed)**:
- `test_scanner_shell_command_no_raw_echo`: pinned message updated to the new argv-or-null phrasing;
  added `test_scanner_bare_metachar_free_command_no_raw_echo`.
- `test_safe_message_locality_preserved`: command family phrase updated to the new message.
- REMOVED `test_authority_logic_skeleton_matches_origin_baseline` +
  `test_skeleton_blanking_is_message_insensitive_self_check` (AST-skeleton-identical does not apply
  to a logic change); replaced by the behavioral battery above.

## 2026-06-18 - Kanban Contract no-raw-echo + authority-parity tests (FOUNDUP_KANBAN_CONTRACT_ERROR_NO_RAW_ECHO_PHASE1)

**Commands**:

```bash
python -m pytest modules/foundups/agent/tests/test_kanban_plugin_contract.py -q
python -m pytest modules/foundups/agent -q                         # full agent suite
# launch-intake affected packages (both modes):
AI_OVERSEER_HEAVY_TESTS=1 python -m pytest modules/ai_intelligence/ai_overseer/tests/test_foundup_launch_request.py \
  modules/ai_intelligence/ai_overseer/tests/test_foundup_genesis_validator.py \
  modules/ai_intelligence/ai_overseer/tests/test_intake_auth_provider.py \
  modules/ai_intelligence/ai_overseer/tests/test_intake_transport.py -q
```

**Result**: PASS

**Summary**:
- `test_kanban_plugin_contract.py`: 135 passed (was 71; +64 new). Full agent suite: 832 passed
  (heavy and CI mode), no regression.
- launch-intake affected packages: 592 passed (heavy and CI mode). intake_transport alone: 188 passed.

**New coverage (this slice)**:
1. No-raw-echo scanner battery: every `_scan_authority` + `_check_path` + `validate_card_spec`
   rejection names the rule (+ fixed marker class) and NEVER echoes the raw key/value/repr/nested
   trail or a control byte. Sentinel leak tokens seeded into keys, trails, values, paths.
2. Addendum-A NAMED-category authority-detection parity: ~42 fixtures across the #807 corpus, each
   mapped to its expected violation class BY INPUT DESIGN (never message-derived); asserts rejection
   so a weakened detector fails even though the message text changed. Plus a coverage test that every
   named category appears in the battery.
3. Addendum-B message-locality: distinct safe rule families are present (not collapsed to one bland
   phrase) and the `{m}`/`{carried}` class token is from the fixed `_AUTHORITY_MARKERS` taxonomy.
4. AST-skeleton self-contained backstop: blanked control-flow skeleton SHA-256 == frozen origin/main
   baseline (no `git show` at runtime); a self-consistency check proves the skeleton is sensitive to
   LOGIC, not message text.
5. Downstream validate_* parity (outcome-only) + a `test_intake_transport.py` caller-regression
   (3 tests, incl. real `SQLiteNonceStore` + spy): authority-bearing body -> rejected,
   `reason == "invalid_request"`, no raw key/value/trail leak, valid invite NOT consumed.
6. Updated 4 `test_foundup_launch_request.py` assertions/helpers that pinned the #830-DEFERRED old
   #807 echo text (text-only; outcome assertions kept).

## 2026-06-13 - Kanban Plugin Contract Tests (HERMES_KANBAN_PLUGIN_CONTRACT_IMPL_PHASE1)

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_kanban_plugin_contract.py -q
```

**Result**: PASS

**Summary**: 71 passed. Full agent suite: 768 passed (no regression/collision).

**Coverage**:
1. Clean CardSpec / WorkerTaskSpec / WreEvidencePacket validate.
2. verified advisory-only: defaults False; construct verified=True raises; dict verified=true rejected;
   nested verified=true rejected; serialized verified is False.
3. Forbidden authority keys rejected (14 parametrized: gate_passed/all_gates_passed/merge_approved/
   merge_token/can_merge/land_approved/dao_approved/payout_ready/cabr_ready/create_repo/
   external_repo_requested/real_execution/source_authority promotion/lifecycle_stage mvp).
4. Public code/shell field rejected; shell-string command rejected.
5. Normalized authority evasion rejected (13 parametrized incl. gatePassed, gate-passed, gate.passed,
   GATE_PASSED, fullwidth gate_passed, mergeApproved, externalRepoRequested, canMerge, landApproved,
   camelCase sourceAuthority promotion).
6. Authority by semantic VALUE rejected (10 parametrized free-text values).
7. Path/ref hygiene: absolute/drive/UNC/traversal/shell-metachar rejected; two distinct foundup paths ok.
8. Value-level redaction: 10 secret shapes in free-text + structured-field redaction (pr_url/head_sha/tests_run) per the SENTINEL hardening observation; 11 secret shapes (sk-/ghp_/Bearer/access_token/refresh_token/client_secret/
   AIza/1// /ya29./env *_TOKEN=) absent from serialized to_dict.
9. Serialization deterministic + json-safe; no forbidden keys/values in the blob.
10. AST: no banned imports (os/sys/subprocess/socket/urllib/...); no runtime executor/consumer import; no
    banned builtin/attr calls; no second-orchestrator symbols (drain/queue/dispatch/spawn/scheduler/kanban.db).

No skips, no xfail.

## 2026-06-12 - WRE ContextBundle Dry-Run Consumer Phase 1 Tests

**Command**:

```
PYTHONIOENCODING=utf-8 python -m pytest modules/foundups/agent/tests/test_context_bundle_dry_run_consumer.py -q -p no:cacheprovider
PYTHONIOENCODING=utf-8 python -m pytest modules/foundups/agent/tests/ -q -p no:cacheprovider
```

**Slice**: WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1 (W6)
**New file**: `tests/test_context_bundle_dry_run_consumer.py` (51 tests)

**Result**: consumer suite 51 passed, 0 skip/xfail. Full
`modules/foundups/agent/tests/`: 697 passed, 0 skip/xfail.

**Coverage (negatives prove the boundary)**:

- Happy path: valid monorepo_poc bundle -> `DryRunResult`;
  `resolved_module_path` == validated canonical (from bundle/resolver),
  NEVER a payload value; observable-ignore surfaced even on a matching job.
- Forged payload `module_path` / `source_module` -> rejected via the SHARED
  resolver (cross-FoundUp, alias, absolute/traversal); rejected value
  observable in the rejection message.
- Non-monorepo_poc `source_authority` (dao_managed / mvp_runtime /
  external_proto) -> refused; consumer cannot promote a stage.
- `required_gates` appear as `gates_to_recheck` NAMES; no gate-pass boolean
  on the result object or anywhere in the serialized dict (denylist + token
  substring scan).
- Dry-run emits evidence but performs NO real execution:
  `HermesFoundUpBuilder.extract_foundup`, the wre_core
  `hermes_job_executor.execute_foundup_job`, and `subprocess.Popen/run/call`
  are all `assert_not_called` (both on the no-job and job-supplied paths).
- No file bodies in evidence (refs+sha256+size+role only); a distinctive
  manifest body line is asserted ABSENT from the serialized result.
- `HERMES_DELEGATE_ENABLED` unset/0 keeps `is_hermes_delegation_enabled()`
  False; the consumer never sets the flag (AST-scanned).
- AST guards: consumer imports NO orchestrator / runtime loop, defines NO
  second `_resolve_validated_module_path` (and binds the SAME shared object
  as the executor; exactly one resolver def repo-wide), performs NO
  subprocess / network / dynamic-import / file-write, and does not import the
  validator (trust is pre-validated).
- Return-value-only: no file write during consumption (patched
  `builtins.open` write-mode sentinel), result is a frozen dataclass, no FAM
  module imported.
- All 6 real manifests (gotjunk, kosei, whack_a_magat, antifafm_broadcaster,
  voteballots, trade) consume to a valid dry-run preview, with and without a
  matching job.

## 2026-06-11 - BuildPlan Generator Module-Path Trust Removal Phase 1 Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_build_plan_generator.py -q
python -m pytest modules/foundups/agent/tests/test_hermes_foundup_job_executor.py -q
python -m pytest modules/foundups/agent/tests/ -q
```

**Result**: PASS

**Summary**:
- Generator test file: **71 passed in 0.97s** (44 prior + 27 new).
- Executor test file (#778 file, **ZERO edits**): **46 passed in 0.83s** --
  Addendum C #3 satisfied.
- Full agent-module suite: **646 passed in 8.99s**; 0 skipped; 0 xfailed.

**Slice**: BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1

**Updated assertions** (flagged per dispatch "Update stale legacy
assertions ... flag each in TestModLog"):

- DELETED `TestModulePathInference::test_known_foundup_paths_include_voteballots`
  (line 489-492 in pre-slice file). The symbol `KNOWN_FOUNDUP_PATHS`
  is deleted; the assertion is moot.
- DELETED `TestModulePathInference::test_get_known_foundup_path_returns_voteballots`
  (line 494-497 in pre-slice file). The function
  `get_known_foundup_path` is deleted.
- UPDATED `TestModulePathInference::test_infer_module_path_for_voteballots`
  docstring to record the bounded foundup_id scan as the new
  derivation path. Now also asserts `rejected_payload_value is None`
  (observable-ignore on the absent-payload branch).
- UPDATED `TestModulePathInference::test_unknown_foundup_without_module_path_fails`
  expected `error_code` from `"MISSING_MODULE_PATH"` to
  `"manifest_missing"` (legacy MISSING_MODULE_PATH branch deleted
  along with the KNOWN_FOUNDUP_PATHS error-message interpolation).
- UPDATED `TestOutsideScopeRejected::test_infrastructure_path_rejected`
  expected `error_code` from `"INVALID_MODULE_PATH"` to
  `"manifest_missing"`. Path is under `modules/` but no on-disk
  manifest -> resolver rejects with manifest_missing.
- UPDATED `TestOutsideScopeRejected::test_root_path_rejected` expected
  `error_code` from `"INVALID_MODULE_PATH"` to `"syntactic_reject"`.
  `/etc/passwd` is an absolute path; the resolver rejects pre-manifest
  at the syntactic-harden step.
- UPDATED `TestOutsideScopeRejected::test_ai_intelligence_path_rejected`
  expected `error_code` from `"INVALID_MODULE_PATH"` to
  `"manifest_missing"`.

**Added** (in `test_build_plan_generator.py`):

- `TestSharedResolverValidationInGenerator` (the 14 dispatch-required
  tests + happy-path controls). Mapping to the dispatch's 14-test
  contract:
  1. `test_payload_path_with_no_backing_manifest_rejected`
  2. `test_source_module_alias_with_wrong_path_rejected`,
     `test_source_module_alias_happy_path`
  3. `test_cross_foundup_substitution_rejected`
  4. `test_suffix_basename_partial_match_rejected`
  5. `test_case_variant_payload_rejected`,
     `test_uppercase_modules_prefix_rejected`
  6. `test_absolute_path_rejected_pre_manifest`,
     `test_drive_prefix_path_rejected_pre_manifest`,
     `test_traversal_rejected_pre_manifest`,
     `test_backslash_rejected_pre_manifest`
  7. `test_empty_string_payload_treated_as_absent`
  8. `test_known_foundup_id_without_on_disk_manifest_fails_closed`
     (parametrized over `pqn_portal`, `social_twin`, `move2japan`),
     `test_known_foundup_paths_symbol_is_gone`
  9. `test_foundup_id_synthesis_dead_no_modules_foundups_fallback`,
     `test_build_target_does_not_use_synthesized_path`
  10. `test_pwa_surface_path_as_module_identity_rejected`
  11. `test_rejected_value_observable_on_failure`,
      `test_rejected_value_observable_on_success`
  12. `TestHermes778TestsUnchanged::test_executor_test_imports_still_resolve`,
      `..._executor_attribute_access_pattern_still_works`
  13. Full agent suite green (646 / 0 / 0).
  14. `test_rejected_payload_value_does_not_propagate_into_buildtarget`,
      `test_buildplan_carries_only_canonical_when_payload_provided`
- `TestSharedResolverIsSingleSourceOfTruth` (Addendum C #4 -- prove
  exactly ONE implementation):
  - `test_executor_shim_and_shared_module_resolve_same_function` --
    `is` identity check on every moved name.
  - `test_generator_uses_same_resolver_as_executor` -- `is` identity
    between generator and executor references.
  - `test_no_second_resolver_implementation_in_executor` -- AST scan
    on executor file asserts no local definition of the moved names.
  - `test_no_second_resolver_in_build_plan_generator` -- symmetric AST
    scan on generator file; also asserts `KNOWN_FOUNDUP_PATHS`
    assignment is gone.
- `TestHermes778TestsUnchanged` -- meta-test that the #778 test file's
  import patterns still resolve through the shim (Addendum C #3).

**Boundary preserved**:

- The #778 executor test file (`test_hermes_foundup_job_executor.py`)
  has ZERO edits. Verified via `pytest -q` returning `46 passed`
  unchanged from the #778 baseline.
- AST scans reject any second resolver implementation in either the
  executor or the generator.
- No skip / no xfail on any security assertion.

---

## 2026-06-10 - Hermes Module-Path Trust Removal Phase 1 Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_hermes_foundup_job_executor.py -q
python -m pytest modules/foundups/agent/tests/ -q
```

**Result**: PASS

**Summary**:
- Executor test file alone: **46 passed in 0.84s** (22 pre-existing + 24
  new in `TestResolvedModulePathValidation`).
- Full agent-module suite: **621 passed in 9.06s**; 0 skipped; 0 xfailed
  (575 prior + 46 executor).

**Slice**: HERMES_MODULE_PATH_TRUST_REMOVAL_PHASE1

**Added** (in `test_hermes_foundup_job_executor.py`):

- `TestResolvedModulePathValidation` (24 tests, mapped 1:1 to dispatch
  Addenda C and D):
  - Happy paths: real gotjunk_001 manifest; cross-domain kosei.
  - Addendum C #1 -- payload path with no backing manifest rejected.
  - Addendum C #2 -- source_module alias receives the same treatment as
    module_path (happy + reject variants).
  - Addendum C #4 -- bare basename and partial paths rejected at
    syntactic-harden step.
  - Addendum C #5 -- backslashes rejected pre-manifest.
  - Addendum C #6 -- absolute / drive-prefix / `..` traversal /
    internal traversal rejected pre-manifest.
  - Addendum C #7 -- omitted payload derives from validated manifest
    via bounded foundup_id scan; unknown id -> manifest_missing.
  - Addendum C #8 -- rejected payload value visible in
    `evidence_refs` (end-to-end through `execute_foundup_job`).
  - Addendum D #1 -- cross-FoundUp substitution (job foundup_id A,
    payload module_path B's real path) rejected with
    `cross_foundup_mismatch`; also via alias.
  - Addendum D #3 -- case-variant payload rejected; uppercase
    `Modules/` prefix rejected at syntactic guard.
  - Addendum D #4 -- empty-string payload semantics: treated as ABSENT
    (falsy); derivation falls through; `ignored=None`.
  - Closed-set token taxonomy: `test_all_fail_tokens_present_in_taxonomy`
    asserts `ALL_FAIL_TOKENS == {syntactic_reject, manifest_mismatch,
    manifest_missing, cross_foundup_mismatch}` exactly.
  - End-to-end fail-closed guards: `test_execute_foundup_job_fails_closed_on_invalid_payload`,
    `..._on_cross_foundup_substitution`, both asserting
    `HermesFoundUpBuilder` is NEVER instantiated when resolution fails.

**Updated assertions** (per dispatch "UPDATE stale assertions" + "flag
each updated assertion in TestModLog"):

- `TestActionDispatch::test_extract_foundup_calls_extract_method` --
  expected `source_module` argument changed from `"modules/foundups/widget"`
  to `"modules/foundups/gotjunk"` (the fixture now anchors on a real
  validator-passing manifest; the dispatch forwards the validator-
  confirmed canonical, not a raw payload string).
- `TestActionDispatch::test_validate_foundup_calls_gate_and_boundary` --
  same change for `check_exfoliation_gate` and `analyze_boundary`.
- `TestModulePathExtraction::test_foundup_id_as_fallback` -- RENAMED to
  `test_foundup_id_path_heuristic_removed`. Assertion flipped from "a
  path-shaped foundup_id IS used as a path source" to "a path-shaped
  foundup_id is NEVER a path source; bounded scan or
  `manifest_missing` wins". Asserts
  `resolved.fail_token == FAIL_TOKEN_MANIFEST_MISSING`.
- `TestModulePathExtraction::test_module_path_from_payload` /
  `test_source_module_from_payload` -- docstrings updated to record
  that the payload-shape check is documentary; behavioral coverage
  now lives in `TestResolvedModulePathValidation`.

**Updated fixtures**:

- `queued_extract_job` / `queued_validate_job` / `queued_build_job` --
  switched from synthetic `"modules/foundups/widget"` (which no longer
  reaches the executor under the new pre-flight) to the real
  `gotjunk_001` / `modules/foundups/gotjunk` pair. Fixture docstring
  explains the change.

**Boundary preserved**:

- AST scan rejects new banned imports (verified by `git diff`: only
  added imports are stdlib `json`, `dataclasses.dataclass`, and the
  intra-repo validator import).
- Validator NOT edited.
- Manifests NOT edited.
- No new dependencies.
- No skip / no xfail.

---

## 2026-06-10 - FoundUp Source-Authority Contract Phase 1 Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_source_authority.py -q
python -m pytest modules/foundups/agent/tests/ -q
```

**Result**: PASS

**Summary**:
- New enum test file alone: **67 passed in 0.36s**.
- Full agent-module suite: **597 passed in 9.43s**; 0 skipped; 0 xfailed
  (530 prior FIX2c + 67 new source-authority tests).

**Slice**: FOUNDUP_LIFECYCLE_SOURCE_AUTHORITY_CONTRACT_PHASE1

**Added** (in `test_source_authority.py`):

- `TestEnumShape` (4 tests): exactly 5 members, exact string values,
  exact member names, str-enum subclass verification.
- `TestActiveStages` (6 tests): `ACTIVE_STAGES == {MONOREPO_POC}`;
  frozen (mutation raises); each of the 4 non-active members is NOT
  in the active set.
- `TestResolveSourceAuthorityAlwaysMonorepoPoc` (12 tests): None /
  explicit None returns `(MONOREPO_POC, None)`; each non-active stage
  (string + enum) returns `(MONOREPO_POC, value)`; self-declared
  `"monorepo_poc"` is STILL reported as ignored (contract: builder
  decides, not caller).
- `TestResolveSourceAuthorityGarbageInputFuzz` (20 parametrized
  garbage inputs covering casing variants, whitespace, ints, floats,
  bools, tuples, lists, dicts, arbitrary objects, NUL, CRLF
  log-injection shape, ESC ANSI): NEVER raises; ALWAYS returns
  `MONOREPO_POC`; ignored is a non-None string.
- `TestRequestPromotionAlwaysRaises` (17 tests): every non-active
  string + enum target raises; even `MONOREPO_POC` target raises;
  garbage targets raise; error message references `Phase-1` and
  `FOUNDUP_SOURCE_AUTHORITY_CONTRACT`.
- `TestBuilderValueParity` (2 tests):
  `SourceAuthority.MONOREPO_POC.value == context_bundle_builder.SOURCE_AUTHORITY`;
  builder constant is exactly `"monorepo_poc"`. The test-only import of
  the builder is the ONLY contact between this slice and the builder.
- `TestSourceAuthorityAstSafety` (4 tests): AST scan rejects all
  imports beyond `{__future__, enum, typing}`; rejects any import
  containing `hermes` / `openclaw` / `ai_overseer` / `job_consumer` /
  `foundup_job_consumer` / `build_plan_executor` / `wre_core` /
  `wre_master_orchestrator` / `build_plan_swarm` /
  `context_bundle_builder` / `foundup_manifest_validator`; rejects
  `subprocess` / `socket` / `urllib` / `importlib` / `multiprocessing` /
  `os` / `sys` / `shutil` / `pickle` / `marshal`; rejects banned name
  calls (`eval`, `exec`, `compile`, `__import__`, `open`); rejects
  banned attr calls (`system`, `popen`, `Popen`, `run`, `write_text`,
  `urlopen`, `connect`, `kill`, ...); rejects CABR / payout / DAO /
  treasury / F_i / UPS / token surface identifiers.
- `TestEnumNotWiredIntoBuilder` (1 test): AST scan on
  `context_bundle_builder.py` asserts NO import of `source_authority`
  (Phase-1 boundary; unification deferred to
  `SOURCE_AUTHORITY_BUILDER_ENUM_UNIFICATION_PHASE2`).

**Coverage delta**: this slice adds a typed-enum code-pin for the
FoundUp source-authority axis defined by the new contract doc, with
fully mechanical coverage of the hard rule ("cannot promote by
declaration") via 20 garbage-input fuzz cases + observable-ignore
verification + `request_promotion` always-raises + builder
value-parity + AST safety. The 6 real manifests still build (the
builder is untouched); all prior FIX1 / FIX2 / FIX2-tighten / FIX2b /
FIX2c tests still pass unchanged; no skip / no xfail; both new `.py`
files 0 non-ASCII bytes.

---

## 2026-06-10 - WRE ContextBundle Builder Phase 1 FIX2c Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/ -q -p no:cacheprovider
```

**Result**: PASS

**Summary**:
- Full agent-module suite: **530 passed in 7.77s**; 0 skipped; 0 xfailed
  (520 FIX2b + 10 FIX2c source-authority-boundary tests).

**Slice**: WRE_CONTEXT_BUNDLE_BUILDER_PHASE1_FIX2C

**Added** (in `test_context_bundle_builder.py`):

- `TestMonorepoPhase1SourceAuthorityBoundary` (FIX2c / W10
  MONOREPO_POC_SOURCE_AUTHORITY_EXPLICIT): the bundle is HONEST about its
  monorepo-PoC Phase-1 scope and a manifest CANNOT promote its lifecycle
  stage by declaration:
  - `test_source_authority_constant_is_monorepo_poc` -- `SOURCE_AUTHORITY`
    builder constant is exactly `"monorepo_poc"`.
  - `test_real_manifest_source_authority_is_monorepo_poc` -- 6 parametrized
    real manifests; both `bundle.source_authority` and
    `to_dict()["source_authority"]` are `"monorepo_poc"`.
  - `test_manifest_cannot_self_promote_lifecycle_stage` -- ANTI-SELF-PROMOTION
    (load-bearing): a manifest adding top-level `source_authority:
    "dao_managed"` + build_contract `lifecycle_stage: "mvp_runtime"` STILL
    builds a bundle with `source_authority == "monorepo_poc"` (manifest stage
    is ignored, not merely rejected -- the bundle IS produced).
  - `test_to_dict_has_no_external_dao_mvp_readiness_authority` -- `to_dict()`
    carries NO external/DAO/MVP readiness key as a truthy authority surface;
    `source_authority` is exactly the Phase-1 constant.
  - `test_source_authority_not_in_bundle_id_fingerprint` -- determinism:
    `source_authority` does NOT enter the bundle_id formula; bundle_id stays
    `sha256(manifest_sha256 | module_path | BUNDLE_VERSION)`.

**Coverage delta**: the bundle now declares an explicit monorepo-PoC Phase-1
boundary via a builder-constant `source_authority` field, proven to be
non-manifest-sourced (anti-self-promotion). No external_proto / mvp_runtime /
dao_managed / archived handling, no DAO/MVP/CABR/payout fields, no lifecycle
transitions were added. All prior FIX1 / FIX2 / FIX2-tighten / FIX2b tests
still pass unchanged; the 6 real manifests still build; `BUNDLE_VERSION` and
the bundle_id formula are unchanged; no skip / no xfail; both `.py` files 0
non-ASCII bytes.

---

## 2026-06-10 - WRE ContextBundle Builder Phase 1 FIX2b Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/ -q -p no:cacheprovider
```

**Result**: PASS

**Summary**:
- Full agent-module suite: **520 passed in 8.86s**; 0 skipped; 0 xfailed
  (514 in FIX2 + 6 FIX2b control-char tests).

**Slice**: WRE_CONTEXT_BUNDLE_BUILDER_PHASE1_FIX2B

**Added** (in `test_context_bundle_builder.py`):

- Module-level CONTROL-CHARACTER fixtures (W10 FIX2b), all built from
  `\xXX` / `\r` / `\n` / `\t` ESCAPE sequences so the source stays 0
  non-ASCII bytes; each is ASCII (passes `isascii()`) but NOT printable
  (carries a control char) and contains NO authority keyword:
  - `_CTRL_NUL_SPLIT` -> `gate\x00name` (embedded NUL U+0000).
  - `_CTRL_CRLF_LOG` -> `ok\r\nFAKELOG: granted` (CRLF log-injection shape).
  - `_CTRL_ESC_ANSI` -> `x\x1b[31m` (ESC U+001B ANSI terminal escape).
  - `_CTRL_TAB` -> `a\tb` (bare TAB U+0009 control char).
- `TestControlCharactersRejected` (FIX2b / W10 final residual,
  printable-ASCII-only contract for the three protected list fields):
  - `test_control_char_fixtures_are_ascii_but_not_printable` -- non-vacuity:
    each fixture `isascii()` True, `isprintable()` False, no authority
    keyword (so it reaches the NEW printable check, not an earlier guard).
  - `test_nul_split_in_required_gates_rejected` -- NUL-split appended as a
    9th gate (8 real gate names preserved, validator passes); rejected
    BEFORE any bundle is produced.
  - `test_crlf_log_injection_in_safe_mutation_surface_rejected` --
    W10-EXPLOIT FIELD (safe_mutation_surface) with a CRLF log-injection
    shape; rejected.
  - `test_esc_ansi_in_forbidden_paths_rejected` -- ESC ANSI escape rejected.
  - `test_bare_tab_in_safe_mutation_surface_rejected` -- bare TAB rejected.
  - `test_printable_ascii_element_still_builds` -- positive control /
    non-vacuity: `modules/foundups/gotjunk/**` still builds and is preserved
    verbatim, with an explicit `isprintable()` positive assertion.

**Coverage delta**: control characters (NUL/CR/LF/TAB/ESC) are now refused
in `required_gates` / `forbidden_paths` / `safe_mutation_surface`,
completing the printable-ASCII-only contract and ending the
Unicode/control-char evasion class. All prior FIX1 / FIX2 / FIX2-tighten
tests still pass unchanged; the 6 real manifests still build; no skip / no
xfail; both `.py` files 0 non-ASCII bytes.

---

## 2026-06-10 - WRE ContextBundle Builder Phase 1 FIX2 Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/ -q -p no:cacheprovider
```

**Result**: PASS

**Summary**:
- Full agent-module suite: **514 passed in 8.47s**; 0 skipped; 0 xfailed
  (496 in FIX1 + 8 first-FIX2 tests + 10 FIX2-tighten tests).

**Slice**: WRE_CONTEXT_BUNDLE_BUILDER_PHASE1_FIX2

**Added** (in `test_context_bundle_builder.py`):

- Module-level fixtures `_FW_PAYOUT_READY`, `_FW_DAO_APPROVED`,
  `_FW_GATE_PASSED`, `_MIXED_HUMAN_APPROVAL`, built from `\uFFxx` ESCAPE
  sequences (source stays 0 non-ASCII bytes) -- fullwidth-Unicode forms of
  authority keywords that NFKC-normalize back to plain ASCII.
- Module-level BENIGN non-ASCII NON-authority fixtures `_NONASCII_CAFE_GLOB`
  (`caf<U+00E9>-glob`) and `_NONASCII_CJK_PATH` (`modules/foundups/
  <U+6587>/x`), built from `\uXXXX` ESCAPE sequences -- path/glob shapes that
  carry a non-ASCII char but no authority keyword (GAP A coverage).
- Module-level detector helper `_find_manifest_listlike_bypasses` (shared by
  the completeness guard and all its non-vacuity proofs; the prior name
  `_find_bare_tuple_of_manifest_access` is kept as a backwards-compatible
  alias).
- `TestFullwidthUnicodeAuthorityEvasionRejected` (FIX2 / W10 residual gap 1,
  fullwidth-Unicode evasion):
  - `test_fullwidth_fixtures_normalize_as_documented` -- non-vacuity guard:
    each fixture is a fullwidth form that NFKC-normalizes to its keyword and
    is NOT already that ASCII keyword.
  - `test_fullwidth_payout_ready_in_safe_mutation_surface_rejected` --
    W10-EXPLOIT FIELD (safe_mutation_surface) with fullwidth `payout_ready`;
    rejected BEFORE any bundle is produced.
  - `test_fullwidth_dao_approved_in_safe_mutation_surface_rejected`.
  - `test_fullwidth_gate_passed_appended_to_required_gates_rejected` --
    fullwidth `gate_passed` appended as a 9th gate (8 real names preserved).
  - `test_fullwidth_payout_ready_appended_to_forbidden_paths_rejected`.
  - `test_generic_nfkc_compatibility_form_also_rejected` -- mixed-form
    `human_approval` (single fullwidth char) also rejected.
- `TestNonAsciiNonAuthorityElementsRejected` (FIX2-tighten / W10 GAP A,
  ASCII-only contract):
  - `test_nonascii_fixtures_are_benign_and_nonascii` -- non-vacuity: each
    fixture is non-ASCII and carries NO authority keyword.
  - `test_nonascii_nonauthority_in_required_gates_rejected` (benign
    non-ASCII 9th gate; 8 real names preserved).
  - `test_nonascii_nonauthority_in_forbidden_paths_rejected`.
  - `test_nonascii_nonauthority_in_safe_mutation_surface_rejected`
    (the W10-exploit field).
  - `test_ascii_elements_preserved_unchanged` -- positive control: ASCII
    inputs build and are preserved verbatim (no rewrite).
- `TestManifestListFieldsStringOnly` (FIX2 / W10 residual gap 2,
  completeness; FIX2-tighten broadens beyond `tuple()`):
  - `test_no_bare_tuple_of_manifest_access_bypasses_helper` -- COMPLETENESS
    AST guard: ZERO manifest-derived list-like bypasses
    (tuple/list/set/frozenset conversion, comprehension/genexp, direct
    assignment reaching a ContextBundle field) that skip
    `_require_str_tuple`.
  - `test_completeness_guard_detects_synthetic_bare_tuple` -- NON-VACUITY:
    the same detector flags a synthetic `tuple(build_contract.get(...))`.
  - `test_completeness_guard_detects_synthetic_bare_list` -- NON-VACUITY:
    flags `list(build_contract.get(...))`.
  - `test_completeness_guard_detects_synthetic_bare_set_and_frozenset` --
    NON-VACUITY: flags `set(...)` and `frozenset(...)`.
  - `test_completeness_guard_detects_synthetic_comprehension` --
    NON-VACUITY: flags listcomp/setcomp/genexp over a manifest access.
  - `test_completeness_guard_detects_synthetic_direct_assignment` --
    NON-VACUITY: flags `x = build_contract.get(...)` reaching a
    ContextBundle field.
  - `test_completeness_guard_no_false_positive_on_local_assignment` --
    FALSE-POSITIVE guard: local conversions (`tuple(included)` /
    `dict(excluded)`) and manifest dict reads whose name never reaches a
    ContextBundle field are NOT flagged.
  - The original positive `test_no_other_manifest_list_field_is_serialized`
    is retained unchanged.

**WSP_97**: table stays at 34 rows (rows 33-34 and 18 evidence updated to
cite the ASCII-only rejection and the multi-pattern completeness detector).
Both `.py` files 0 non-ASCII bytes. No skip / no xfail.

---

## 2026-06-09 - WRE ContextBundle Builder Phase 1 FIX1 Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_context_bundle_builder.py -q
python -m pytest modules/foundups/agent/tests/ -q
```

**Result**: PASS

**Summary**:
- Builder test file alone: **129 passed in 2.40s** (54 prior + 75 new).
- Full agent-module suite: **496 passed in 7.87s**; 0 skipped; 0 xfailed.

**Slice**: WRE_CONTEXT_BUNDLE_BUILDER_PHASE1_FIX1

**Added** (in `test_context_bundle_builder.py`):

- `TestRequireStrTupleListFieldsRejectsAuthorityLaundering`:
  - `test_required_gates_with_appended_dict_rejected` -- the W10
    exact example for required_gates.
  - `test_required_gates_with_non_str_element_rejected` -- 7
    parametrized non-str element types (`int`, `True`, `False`,
    `None`, list, dict, float).
  - `test_required_gates_as_dict_value_rejected`.
  - `test_forbidden_paths_with_appended_dict_rejected` -- the W10
    exact example for forbidden_paths.
  - `test_forbidden_paths_with_non_str_element_rejected` -- 6
    parametrized.
  - `test_safe_mutation_surface_as_dict_value_rejected_w10_repro` --
    the ADVERSARIAL REPRO: exact W10 exploit
    `{"payout_ready": true, "dao_approved": true}` rejected before
    bundle construction.
  - `test_safe_mutation_surface_with_appended_dict_rejected`.
  - `test_safe_mutation_surface_with_non_str_element_rejected` -- 7
    parametrized.
  - `test_authority_keyword_strings_rejected` -- 9 parametrized
    `(field, keyword)` cases proving authority-keyword substring
    smuggling is refused (`payout_ready`, `dao_approved`,
    `manifest_ready`, `human_approval`, `external_agent_allowed`,
    `is_authorized`, `approval_level`, `gate_passed`,
    `security_passed`).
  - `test_empty_string_element_rejected` -- 3 parametrized fields.
  - `test_real_manifests_still_build_with_helpers` -- all 6 real
    manifests pass the helper unchanged.
  - `test_to_dict_never_produced_for_crafted_input` -- proves the
    bundle's `to_dict()` is never produced for poisoned input.

- `TestRequireStrictBoolScalarFieldsRejectsAuthorityLaundering`:
  - `test_readiness_with_non_bool_value_rejected` -- 3 readiness
    fields x 5 bad values (`{"is_authorized": True}`,
    `{"payout_ready": True, "dao_approved": True}`, list, int,
    `"true"` string).
  - `test_routing_flag_with_non_bool_value_rejected` -- 2 routing
    flags x 4 bad values.
  - `test_truthy_dict_readiness_not_laundered_to_true` -- explicit
    repro that the prior `bool(dict)` smuggle is closed.

- `TestManifestListFieldsStringOnly`:
  - `test_all_list_field_elements_are_str_after_build` -- type-check
    every element of every list field for all 6 real manifests.
  - `test_no_other_manifest_list_field_is_serialized` -- AST scan
    asserts `_require_str_tuple` is applied to exactly
    `{"required_gates", "forbidden_paths", "safe_mutation_surface"}`.
    If a future change adds a fourth list field that gets copied into
    the bundle, this test fails until it is routed through the helper.

**Boundary preserved (FIX1)**:

- All prior security AST scans still pass (no banned imports / banned
  calls / runtime executor imports / nondeterministic imports).
- Validator NOT edited.
- No new dependencies.
- No skip / no xfail.
- All 6 real manifests still build (clean-manifest behavior identical).

---

## 2026-06-09 - WRE ContextBundle Builder Phase 1 Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_context_bundle_builder.py \
                 modules/foundups/agent/tests/test_foundup_manifest_validator.py -q
```

**Result**: PASS

**Summary**: 142 passed in 1.20s; 0 skipped; 0 xfailed.

**Slice**: WRE_CONTEXT_BUNDLE_BUILDER_PHASE1

**Added** (in `test_context_bundle_builder.py`):
- `TestRealManifestsBuild`: each of the 6 real manifests builds a
  bundle; refs+sha256-only shape pinned at dataclass and `to_dict`
  levels; manifest ref present; declared test refs included where
  safe.
- `TestForbiddenPathsAndCap`: forbidden-path segment screen + total-cap
  fail-closed + cap-never-exceeded property.
- `TestValidatorRejectionsPropagate`: invalid manifest, three readiness
  promotions, `external_agent_allowed=true`, `can_self_authorize=true`,
  and module_path mismatch (via the #773 validator) all rejected.
- `TestNoGatePassNoCabrNoPayoutNoDao`: full-dict walk rejects 14
  forbidden authority keys; `required_gates_to_recheck` carries
  string names only.
- `TestOutsideModulePathExcluded`: docs outside `module_root` are not
  included.
- `TestPathTraversalRejected`: `..` in module_path rejected via the
  #773 validator canonicalizer.
- `TestSymlinkEscapeRejected`: integration test on platforms that
  support `os.symlink` (Windows without dev mode returns early without
  asserting) PLUS `test_is_path_within_helper_rejects_path_outside_base`
  -- the always-runs mechanical pin for the same boundary.
- `TestBuilderImportAndExecutionSafety`: AST scan -- no banned-module
  imports, no banned name/attr calls, no runtime executor imports.
- `TestBundleIdDeterministic`: 5 cases plus a static-AST check that
  the builder does not import `time` / `datetime` / `random` /
  `secrets` / `uuid`.
- `TestStreamHashAndOversized`: patched-cap oversized exclusion plus
  an AST scan proving `_stream_sha256` uses a while-loop with
  chunked reads.
- `TestReconciliationFlaggedStillBuild`: voteballots and trade build
  at the declarative level; readiness flags stay false
  (NEEDS_LABEL_RECONCILIATION not promoted).
- `TestNoConsumerWiringNoBuildRun`: signature has no consumer handle;
  source contains no runtime-consumer class identifier.
- `TestNo774LegacyPayloadAuthority`: API has no `payload` /
  `job_payload` / `job` / `task` / `request` parameter; bundle
  `module_path` comes from the validated manifest only; source has no
  `payload` / `job_payload` / `legacy_payload` identifier.
- `TestBundleStructuralIntegrity`: every required top-level field
  present; provenance carries builder version + validator path/sha256
  + applied WSPs (`WSP_50`, `WSP_77`, `WSP_84`, `WSP_97`).

**Boundary preserved**:
- AST scan rejects subprocess / socket / urllib / importlib /
  multiprocessing / pickle / marshal at the module-import level.
- AST scan rejects `eval` / `exec` / `compile` / `__import__` /
  `input` / `execfile` at the call level.
- AST scan rejects `system` / `popen` / `Popen` / `run` / `call` /
  `check_call` / `check_output` / `getoutput` / `write_text` /
  `write_bytes` / `writelines` / `urlopen` / `urlretrieve` / `connect` /
  `spawn` / `fork` / `execv` / `execve` / `remove` / `unlink` /
  `rmdir` / `makedirs` / `chmod` / `kill` at the attribute call level.
- AST scan rejects `hermes` / `openclaw` / `ai_overseer` /
  `job_consumer` / `foundup_job_consumer` / `build_plan_executor` /
  `wre_core` / `wre_master_orchestrator` / `build_plan_swarm` imports.
- AST scan rejects identifier-level references to `Hermes` / `OpenClaw`
  / `AIIntelligenceOverseer` / `AIOverseer` / `FoundUpJobConsumer` /
  `FoundUpJob` / `BuildPlanExecutor` / `WREMasterOrchestrator` while
  allowing the same words in docstrings/comments (which document the
  forbidden boundary).

**No skip / no xfail on any security assertion.**

---

## 2026-06-09 - FoundUp Manifest Validator Module Path Exact-Match Hardening Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_foundup_manifest_validator.py -q
```

**Result**: PASS

**Summary**: 88 passed in 0.28s.

**Slice**: FOUNDUP_MANIFEST_VALIDATOR_MODULE_PATH_EXACT_MATCH_HARDENING_PHASE1

**Added**:
- `TestExactMatchHelperDirect`: 8 direct unit tests on the
  `_expected_module_path_matches` helper and the two new canonicalize
  helpers. Pin the trust boundary mechanically -- not only through the
  full validator surface.
- `TestSuffixCollisionRejected`: 6 explicit suffix-collision cases that
  must fail under exact-only matching, including the shadow-prefix
  collision and the cross-domain `whack_a_magat` example from the W6
  dispatch.
- `TestCanonicalPathNormalization`: 16 parametrized variants split into
  accept (harmless: `./`, `//`, `.` segment, backslashes, trailing `/`)
  and reject (absolute drive, leading `/`, UNC, `..` traversal anywhere
  in the path, shadow directory, extra suffix segment).
- `TestOldSuffixBehaviorRegression`: 3 tests that compute the OLD
  suffix-fallback locally inside the test, assert it would have accepted
  the input, and assert the NEW exact-only helper rejects it. Pins the
  regression mechanically so any future loosening fails.

**Boundary preserved**:
- `test_validator_imports_no_runtime_executors` still passes (no
  hermes / openclaw / ai_overseer / job_consumer / wre_core imports).
- `test_validator_no_exec_process_network_or_write` still passes
  (no subprocess / socket / urllib / open / Popen / write / etc.).
- Negative controls (shell strings, shell metacharacters, gate-bypass
  flag, missing required gates, external_agent_allowed=true,
  build_ready=true, autonomous_execution_ready=true, manifest_ready=true
  without promotion) all still trigger rejection.

**No skip / xfail on any security assertion.**

---

## 2026-06-08 - FoundUp Manifest Validator Tests (FOUNDUP_MANIFEST_BASELINE_IMPL_PHASE1)

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_foundup_manifest_validator.py -q
```

**Result**: PASS

**Summary**: 51 passed in 0.28s.

**Coverage**:
1. All 6 updated manifests validate (positive, parametrized).
2. foundup_id matches build_contract.foundup_id (real manifests + mismatch negative).
3. forbidden_paths cover .env / main.py / *_dae.py / vendor (all 6).
4. Negative: reject unknown executor.
5. Negative: reject privileged + self-authorizing executor config.
6. Negative: reject missing required gate (genesis_gate).
7. Negative: reject dry_run.default=false.
8. Negative: reject external_agent_allowed=true.
9. Negative: reject build_ready=true.
10. Negative: reject autonomous_execution_ready=true.
11. Negative: reject manifest_ready=true without promotion.
12. Negative: reject shell-string command for build/test/dry_run.
13. Negative: reject shell metacharacters in argv (4 injection shapes).
14. Negative: reject truthy gate-bypass flag.
15. execution_routing declarative-only (all 6).
16. voteballots/trade flagged NEEDS_LABEL_RECONCILIATION (and not build-trusted).
17. Validator source imports no Hermes/OpenClaw/WRE consumer/AI Overseer runtime (AST).
18. Validator source makes no exec/process/network/file-write calls (AST).
19. Validation is pure (does not mutate input; repeatable).

**Cross-checked existing tests (still pass after manifest edits)**:

```bash
python -m pytest modules/foundups/gotjunk/tests/test_manifest.py -q              # 12 passed
python -m pytest modules/foundups/kosei/tests/test_manifest_contract.py -q       # 7 passed
python -m pytest modules/foundups/trade/tests/test_manifest_contract.py -q       # 15 passed
python -m pytest modules/foundups/voteballots/tests/test_shell_integration.py -q # 62 passed
python -m pytest modules/foundups/agent/tests/ -q                                # 330 passed
```

Note: cross-module collection of two same-named `tests` packages in ONE pytest
invocation collides (pre-existing layout); run per-file as above.

## 2026-05-01 - Worker Queue Observability Tests (OC20)

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_worker_queue_observability.py -q
```

**Result**: PASS

**Summary**: 28 passed in 1.04s.

**Coverage**:
1. emit_event stores append-only event
2. emit_heartbeat creates heartbeat event with consecutive tracking
3. emit_lease_expired creates lease expiry signal
4. worker availability/unavailability events are recorded
5. snapshot_queue_health reports queued/processing/completed/expired counts
6. get_events filters by worker_id
7. event fields preserve evidence_refs
8. all observability is in-memory only
9. no real worker/process fields imply execution
10. no CABR/reward/payout/token fields exist

**Notes**:
- Implements WSP 91 (DAEMON Observability Protocol) Pillar 1 (Logs) and partial Pillar 3 (Metrics)
- All 32 agent queue tests still passing (no regressions)
- All 33 VoteBallot PoC tests still passing (no regressions)

**WSP References**: WSP 11, WSP 50, WSP 91, WSP 97.

---

## 2026-04-30 - Full VoteBallot Dispatch PoC Integration (OC19)

**Command**:

```bash
python -m pytest modules/communication/moltbot_bridge/tests/test_internal_voteballot_build_poc.py -q
```

**Result**: PASS

**Summary**: 33 passed in 0.98s.

**Coverage** (TestVoteBallotFullDispatchPoC - 5 new tests):
1. test_full_voteballot_dispatch_pipeline_single_worker - proves Job->BuildPlan->Swarm->Queue->Dispatcher->Coordinator flow
2. test_full_voteballot_dispatch_pipeline_multiple_workers - proves multi-worker capability routing
3. test_full_dispatch_summary_preserves_wsp97_boundaries - proves all_simulated=True, no CABR/payout fields
4. test_full_dispatch_pipeline_preserves_job_plan_receipt_correlation - proves identity chain preserved
5. test_full_dispatch_pipeline_blocks_mismatched_worker - proves capability mismatch blocking

**Notes**:
- Integrates SwarmDispatchCoordinator with VoteBallot PoC
- Full simulated path: FoundUpJob -> BuildPlan -> SwarmCoordinator -> SwarmWorkerQueue -> AssignmentDispatcher -> SwarmDispatchCoordinator -> Evidence
- All 33 VoteBallot PoC tests passing (28 prior + 5 new)
- 57 agent module tests also passing (no regressions)

**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97.

---

## 2026-04-30 - Swarm Dispatch Integration Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_swarm_dispatch_integration.py -q
```

**Result**: PASS

**Summary**: 12 passed in 0.89s.

**Coverage**:
1. dispatch_next dequeues matching queue entry and dispatches simulated assignment
2. dispatch_next returns blocked/no-match for wrong capability
3. complete_dispatched_assignment records evidence in queue and dispatcher
4. run_simulated_cycle performs dequeue -> dispatch -> complete
5. multiple workers can process different assignments without file conflicts
6. summary reports all_simulated=True and real_execution_performed=False
7. VoteBallot swarm queue can run one simulated dispatch cycle

**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97.

---

## 2026-04-30 - Full Agent Module Test Suite (OC18)

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_swarm_dispatch_integration.py modules/foundups/agent/tests/test_worker_assignment_protocol.py modules/foundups/agent/tests/test_build_plan_swarm_queue.py -q
```

**Result**: PASS

**Summary**: 57 passed.

**Notes**:
- All dispatch integration tests (12) passing
- All worker assignment protocol tests (25) still passing
- All queue tests (20) still passing
- No regressions

---

## 2026-04-30 - Worker Assignment Protocol Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_worker_assignment_protocol.py -q
```

**Result**: PASS

**Summary**: 25 passed in 0.26s.

**Coverage**:
1. register_worker creates tracked worker process
2. register_worker records runtime type and capabilities
3. dispatch_assignment returns simulated/not-implemented status
4. dispatch_assignment does not start process
5. heartbeat updates worker last_seen
6. completion event records evidence_refs
7. deregistration changes status
8. no CABR/reward/payout/token fields exist
9. all WSP_97 truth fields remain false/simulated

**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97.

---

## 2026-04-30 - Full Agent Module Test Suite (OC17)

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_worker_assignment_protocol.py modules/foundups/agent/tests/test_build_plan_swarm_queue.py -q
```

**Result**: PASS

**Summary**: 45 passed.

**Notes**:
- All worker assignment protocol tests (25) passing
- All queue tests (20) still passing
- No regressions

---

## 2026-04-30 - BuildPlan Swarm WRE Queue Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_build_plan_swarm_queue.py -v
```

**Result**: PASS

**Summary**: 20 passed in 2.42s.

**Coverage**:
1. Create queue entry from StepAssignment
2. Dequeue matching worker capability succeeds
3. Dequeue mismatched worker capability is blocked
4. Heartbeat renews lease
5. Completion report marks entry complete with evidence
6. Expired entry can be requeued
7. Simulated completion cannot set real_execution_performed=True
8. Queue entry has no CABR/reward/payout/token fields
9. VoteBallot swarm assignment can be enqueued and dequeued by simulated worker

**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97.

---

## 2026-04-30 - Full Agent Module Test Suite (OC15)

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_build_plan_swarm_queue.py modules/foundups/agent/tests/test_build_plan_swarm.py -q
```

**Result**: PASS

**Summary**: 54 passed.

**Notes**:
- All queue tests (20) passing
- All swarm coordination tests (34) still passing
- No regressions

---

## 2026-04-30 - BuildPlan Swarm Coordination Scaffold Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_build_plan_swarm.py -q
```

**Result**: PASS

**Summary**: 34 passed in 0.67s.

**Coverage**:
1. Register multiple workers
2. Assign different steps to different workers
3. Block duplicate file claims
4. Allow release then re-claim
5. Expire lease releases claim
6. Reject out-of-scope file claim
7. Aggregate evidence from multiple assignments
8. Summary reports simulated-only execution
9. No real_execution_performed can become true
10. VoteBallot BuildPlan can be split into multiple simulated assignments

**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97.

---

## 2026-04-30 - Full Agent Module Test Suite (OC13)

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_build_plan_swarm.py modules/foundups/agent/tests/test_build_plan_executor.py modules/foundups/agent/tests/test_build_plan_generator.py -q
```

**Result**: PASS

**Summary**: 119 passed.

**Notes**:
- All swarm coordination tests (34) passing
- All executor tests (39 - from OC12) still passing  
- All generator tests (20 - from OC9) still passing
- No regressions

---

## 2026-04-29 - BuildPlanExecutor Interface Stub Tests

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_build_plan_executor.py -v
```

**Result**: PASS

**Summary**: 39 passed in 0.71s.

**Coverage**:
1. Executor instantiation with dry_run=True
2. validate_plan rejects mode=REAL without approval
3. simulate_step returns StepExecutionResult with SIMULATED
4. execute_step dry_run delegates to simulation
5. execute_step real returns BLOCKED
6. Mutating actions identified correctly
7. ExecutionReceipt WSP 97 truth fields all False
8. No CABR/reward/payout/token fields exist
9. VoteBallot generated BuildPlan validates and simulates

**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97.

---

## 2026-04-29 - Full Agent Module Test Suite

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/ -v
```

**Result**: PASS

**Summary**: 160 passed in 7.67s.

**Notes**:
- All BuildPlan pipeline tests (OC8/OC9/OC12) passing
- Hermes tests passing
- No regressions

---

## 2026-04-25 - Hermes Deploy Surface Detector Alignment

**Command**:

```bash
python -m pytest modules/foundups/agent/tests/test_hermes_foundup_builder.py -q
```

**Result**: PASS

**Summary**: 18 passed in 7.29s.

**Notes**:
- Verified Hermes FoundUp Builder recognizes deploy evidence from direct deploy configs, `app/index.html`, `frontend/index.html`, and manifest `entry_url` with `launch_readiness=ready`.
- The first run failed 3 tests on deploy-surface recognition; `HermesFoundUpBuilder._detect_deploy_surface()` was added and the focused suite passed.

**WSP References**: WSP 34, WSP 50, WSP 60, WSP 83, WSP 97.
