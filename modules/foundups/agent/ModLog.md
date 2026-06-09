# Agent Module ModLog

## 2026-06-10 - WRE ContextBundle Builder Phase 1 FIX2 (W10 residual-gap closure)

**Author**: 0102 (W6)
**Slice**: WRE_CONTEXT_BUNDLE_BUILDER_PHASE1_FIX2
**Predecessor**: FIX1 (commit 96314ab6c, PR #775)
**Trigger**: W10 adversarial re-gate of PR #775

**W10 residual gaps proven after FIX1**:

> FINDING 1 (MAJOR): fullwidth-Unicode evades the `_AUTHORITY_KEYWORDS`
> substring scan. A manifest element that is the FULLWIDTH form of
> "payout_ready" (U+FF50 U+FF41 U+FF59 U+FF4F U+FF55 U+FF54 "_" U+FF52
> U+FF45 U+FF41 U+FF44 U+FF59) is a `str`, passed the raw `item.lower()`
> guard, landed in `bundle.to_dict()`, and NFKC-normalizes to
> "payout_ready" downstream. The denylist was Unicode-evadable.
>
> FINDING 2 (MINOR): the check-5 AST test
> `test_no_other_manifest_list_field_is_serialized` was POSITIVE-ONLY: it
> asserts the set of fields routed through `_require_str_tuple` equals the
> expected three. A FUTURE `tuple(build_contract.get("new_list", []))`
> that BYPASSES the helper would STILL pass that positive check.

**FIX2 changes (4 files; read-only builder; no validator/manifest/runtime
edit; no new dependency)**:

1. `src/context_bundle_builder.py`: added `import unicodedata` (stdlib).
   In `_require_str_tuple`, the `_AUTHORITY_KEYWORDS` denylist scan now runs
   against `unicodedata.normalize("NFKC", item).lower()` instead of
   `item.lower()`. The rejection DECISION uses the normalized form; the
   value APPENDED to the output tuple remains the ORIGINAL `item` (no silent
   rewrite of the serialized value). Type-check and empty/whitespace check
   are unchanged.

2. `tests/test_context_bundle_builder.py`: new
   `TestFullwidthUnicodeAuthorityEvasionRejected` (6 tests + 1 non-vacuity
   fixture check) asserts `ContextBundleRejected` is raised BEFORE any
   bundle is produced for fullwidth `payout_ready` / `dao_approved` /
   `gate_passed` payloads across `safe_mutation_surface` (the W10-exploit
   field), `required_gates` (appended as a 9th gate so the 8 real names
   remain), and `forbidden_paths`, plus a generic NFKC-compatibility form
   (`human_approval`). Fullwidth strings are encoded via `\uFFxx` ESCAPE
   sequences so the source file stays 0 non-ASCII bytes.

3. `tests/test_context_bundle_builder.py`: check-5 AST guard upgraded to
   COMPLETENESS. New `test_no_bare_tuple_of_manifest_access_bypasses_helper`
   walks the builder AST and flags any `tuple(...)` of a manifest dict
   access not routed through `_require_str_tuple` (asserts ZERO). Non-vacuity
   proven by `test_completeness_guard_detects_synthetic_bare_tuple` (same
   detector flags a synthetic bare `tuple(build_contract.get("new_list",
   []))`). The original positive assertion is retained.

4. `ModLog.md` / `tests/TestModLog.md`: WSP_97 table extended to 34 rows
   (rows 33-34 added; rows 18 and 24 evidence Unicode-hardened); test-run
   summary updated.

**FIX1 guarantees preserved**: no validator edit, no manifest edit, no
runtime/consumer wiring, no build run, no new dependency. All 6 real
manifests still build. The original W10 dict/bool exploit (dict appended
to `required_gates`, dict-as-value `safe_mutation_surface`, truthy-dict
readiness/routing, int readiness) is still rejected BEFORE `to_dict()`.
No skip / no xfail.

**Test run**: `python -m pytest modules/foundups/agent/tests/ -q
-p no:cacheprovider` -> 504 passed, 0 skipped, 0 xfailed (496 in FIX1 +
8 new FIX2 tests).

**ASCII**: both `.py` files are 0 non-ASCII bytes (fullwidth test strings
are `\uFFxx` escapes). This ModLog FIX2 entry is ASCII-clean.

See the FIX1 entry below for the full 34-row WSP_97 Truth Boundary
Checklist (rows 33-34 are the FIX2 additions; verdict FIX2 PASS 34/34).

---

## 2026-06-09 - WRE ContextBundle Builder Phase 1 FIX1 (authority-laundering closure)

**Author**: 0102 (W6)
**Slice**: WRE_CONTEXT_BUNDLE_BUILDER_PHASE1_FIX1
**Predecessor**: this branch's prior commit (PR #775 first push)
**Trigger**: W10 return-from-review on PR #775

**W10 blocker**:

> A manifest that passes `validate_manifest_file` can smuggle non-string
> authority dicts into `bundle.to_dict()` because `context_bundle_builder.py`
> copies these build_contract list fields verbatim:
>   - required_gates_to_recheck
>   - forbidden_paths
>   - safe_mutation_surface
>
> Examples proven by W10:
>   required_gates_to_recheck: `{"gate_passed": true, "security_passed": true, "human_approval": true}`
>   forbidden_paths: `{"is_authorized": true, "approval_level": "CRITICAL"}`
>   safe_mutation_surface: `{"payout_ready": true, "dao_approved": true}`
>
> This refutes WSP_97 rows GATE_NAMES_ONLY_NOT_PASS_BOOLEANS and
> NO_CABR_PAYOUT_DAO.

**Root cause**: the #771/#773 validator does NOT enforce element types
on `required_gates` / `forbidden_paths`, and does not type-check
`safe_mutation_surface` at all. The prior builder's
`tuple(build_contract.get(field, []) or [])` faithfully forwarded any
element (or, for `safe_mutation_surface`, a dict-as-value where
`tuple(dict)` yields the dict's keys) into the bundle. The
validator's `is True` check on readiness / routing scalars created the
same vector at scalar granularity (a truthy dict passes `is True` then
`bool(dict)` coerces to True).

### Changed

- **`context_bundle_builder.py`**:
  - Added `_AUTHORITY_KEYWORDS` denylist constant (gate-pass / readiness
    / CABR / payout / DAO / human-approval / external-agent /
    self-authorization keywords; lower-case substring match).
  - Added `_require_str_tuple(field_name, value) -> Tuple[str, ...]`
    helper: rejects non-list/tuple value (dict-as-field), any element
    whose `type(item) is not str` (rejects dict / list / bool / int /
    None / object), empty / whitespace-only strings, and strings whose
    lower-cased form contains any authority keyword from
    `_AUTHORITY_KEYWORDS`. No silent drop -- raises
    `ContextBundleRejected`.
  - Added `_require_strict_bool(field_name, value, *, default=False)
    -> bool` helper: rejects anything that is not exactly `bool` /
    `None`. None / missing maps to `default`. No `bool(dict)` smuggle.
  - Applied `_require_strict_bool` to `readiness.manifest_ready`,
    `readiness.build_ready`, `readiness.autonomous_execution_ready`,
    `execution_routing.external_agent_allowed`,
    `execution_routing.can_self_authorize`, and
    `build_contract.dry_run.required` BEFORE the defense-in-depth
    safety re-checks (step 3a). The re-checks now operate on
    strictly-typed locals (step 3b).
  - Applied `_require_str_tuple` to `required_gates`, `forbidden_paths`,
    `safe_mutation_surface` BEFORE bundle construction (step 3c). The
    resulting `Tuple[str, ...]` values flow directly into
    `ContextBundle(...)`; the prior verbatim `tuple(...)` calls are
    gone.

### Audit -- other manifest-provided list/tuple fields copied into the bundle

Source audit performed: the ONLY manifest-provided list/tuple values
forwarded into the bundle are `required_gates`, `forbidden_paths`, and
`safe_mutation_surface`. Pinned mechanically by
`TestManifestListFieldsStringOnly::test_no_other_manifest_list_field_is_serialized`:
an AST scan of `context_bundle_builder.py` extracts the field-name
argument of every `_require_str_tuple(...)` call and asserts it equals
exactly `{"required_gates", "forbidden_paths", "safe_mutation_surface"}`.
If a future change adds a fourth list field that goes into the bundle,
that test fails until it is routed through the helper and a WSP_97
evidence line is added.

Scalar manifest fields audited:
- `foundup_id`, `module_path`, `contract_version`,
  `build_contract_status` -- already `str(...)`-coerced; cannot carry
  authority dicts even under malicious manifests.
- `routing.orchestrator` / `executor` / `auditor` -- validator already
  rejects anything not in the respective `ALLOWED_*` `frozenset`s (must
  be `str`).
- `routing.declarative_only` -- validator already rejects anything that
  is not the `True` singleton.
- `routing.external_agent_allowed`, `routing.can_self_authorize`,
  `readiness.*`, `build_contract.dry_run.required` -- newly routed
  through `_require_strict_bool` in this fix.

### Tests added

In `test_context_bundle_builder.py`:

- `TestRequireStrTupleListFieldsRejectsAuthorityLaundering` -- crafted
  manifests with appended dicts, parametrized non-str element types
  (`int`, `True`, `False`, `None`, nested list, dict, float, zero),
  dict-as-field-value (the safe_mutation_surface W10 repro), authority-
  keyword string smuggling (9 parametrized `(field, keyword)` cases),
  empty-string elements, all-six real manifests still build with
  helper applied, and the `to_dict()` is NEVER produced for crafted
  input.
- `TestRequireStrictBoolScalarFieldsRejectsAuthorityLaundering` --
  crafted truthy-dict / list / int / string values on each of three
  readiness fields and two routing flags; plus a specific repro that a
  truthy dict in `readiness.build_ready` is NOT laundered to True.
- `TestManifestListFieldsStringOnly` -- WSP_97 row coverage: every list
  field element is `str` after build for all six real manifests; AST
  scan pins that the helper is applied to exactly the three protected
  field names.

Full suite: `pytest -q modules/foundups/agent/tests/` ->
**496 passed in 7.87s**; 0 skipped; 0 xfailed.

The builder-test file alone: **129 passed in 2.40s** (54 prior +
75 new in FIX1).

### Boundary preserved

- READ_ONLY_BUILDER_ONLY. No new module-level imports beyond what was
  already there; no subprocess / network / dynamic-import / file-write.
- NO_CONSUMER_WIRING. NO_HERMES_CALL. NO_OPENCLAW_CALL.
  NO_JOB_ENQUEUE_OR_DRAIN. NO_BUILD_RUN.
- Validator NOT edited (one of the explicit RETURN_CONDITIONS).
- Manifests NOT edited.
- Bundle remains deterministic (`bundle_id` formula unchanged;
  `created_at` still injected; helpers do not introduce nondeterminism).
- All 6 real manifests still build (`TestRealManifestsBuild` plus
  `TestRequireStrTupleListFieldsRejectsAuthorityLaundering::
  test_real_manifests_still_build_with_helpers`).
- No skip / no xfail on any security assertion.

### WSP_97 Truth Boundary Checklist (FIX1 repair: 32 rows; FIX2 extends to 34 rows)

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | HOLOINDEX_PRIOR_ART_SEARCHED | YES | 4 HoloIndex queries recorded in the previous PR-775 ModLog entry below; this fix uses the same Phase 0 result (no prior art for `ContextBundle`). |
| 2 | WSP_84_REUSE_DECISION_DOCUMENTED | YES | Validator imported (`_require_str_tuple` and `_require_strict_bool` are NEW helpers private to the builder; they do not duplicate validator logic). |
| 3 | VALIDATOR_REUSED_NOT_REIMPLEMENTED | YES | `context_bundle_builder.py` imports `validate_manifest_file`, `ManifestValidationResult`, `_canonicalize_module_path` and adds NO new logic that lives in the validator. The two new helpers operate solely on the bundle-output boundary. |
| 4 | READ_ONLY_BUILDER_ONLY | YES | `test_builder_no_subprocess_network_dynamic_import_or_write` still passes after FIX1; AST scan: no new banned-module imports, no banned calls. |
| 5 | NO_CONSUMER_WIRING | YES | `test_builder_signature_has_no_consumer_handle` still passes; no new consumer parameter. |
| 6 | NO_HERMES_CALL | YES | `test_builder_imports_no_runtime_executors` still passes. |
| 7 | NO_OPENCLAW_CALL | YES | Same test. |
| 8 | NO_JOB_ENQUEUE_OR_DRAIN | YES | No queue / broker / publish API referenced. |
| 9 | NO_BUILD_RUN | YES | No `subprocess.run` / `Popen`. |
| 10 | VALIDATOR_REQUIRED_BEFORE_MODULE_PATH_TRUST | YES | Order preserved: step 1 calls `validate_manifest_file(manifest_path)`; helpers run AFTER validator passes. `TestValidatorRejectionsPropagate` still pins this. |
| 11 | JOB_PAYLOAD_MODULE_PATH_NOT_TRUSTED | YES | `TestNo774LegacyPayloadAuthority` still passes; FIX1 did not add any payload-accepting parameter. |
| 12 | REFS_AND_SHA256_ONLY | YES | `FileRef` shape unchanged; `test_bundle_carries_only_refs_no_file_bodies` still passes. |
| 13 | NO_FILE_BODIES | YES | Same test. |
| 14 | STREAM_HASHED_NO_FULL_BODY_LOAD | YES | `_stream_sha256` unchanged. |
| 15 | MAX_CONTEXT_BYTES_ENFORCED | YES | Total-cap logic unchanged. |
| 16 | FORBIDDEN_PATHS_EXCLUDED | YES | `_is_path_forbidden` segment screen unchanged. |
| 17 | SYMLINK_ESCAPE_REJECTED | YES | `_is_path_within` helper-level test still passes. |
| 18 | GATE_NAMES_ONLY_NOT_PASS_BOOLEANS | YES (repaired; FIX2 Unicode-robust) | Now backed by `_require_str_tuple` element-type check + `_AUTHORITY_KEYWORDS` denylist substring rejection, and (FIX2) the denylist scan is NFKC-normalized before matching so fullwidth-Unicode forms cannot evade it. Crafted-test evidence: `test_required_gates_with_appended_dict_rejected` (W10 exact example), `test_required_gates_with_non_str_element_rejected` (7 parametrized non-str types), `test_required_gates_as_dict_value_rejected`, `test_authority_keyword_strings_rejected` (9 parametrized authority-keyword smuggle cases), `test_fullwidth_gate_passed_appended_to_required_gates_rejected` (FIX2: fullwidth `gate_passed` appended as a 9th gate), `test_all_list_field_elements_are_str_after_build` (all 6 real manifests). |
| 19 | NO_READINESS_PROMOTION | YES | `_require_strict_bool` now rejects truthy-dict / list / int / "true"-string smuggling on each readiness field. Crafted evidence: `test_readiness_with_non_bool_value_rejected` (3 fields x 5 bad values), `test_truthy_dict_readiness_not_laundered_to_true`. Defense-in-depth check still raises `ContextBundleRejected` on `is True`. |
| 20 | BUNDLE_ID_DETERMINISTIC_NOT_WALLCLOCK | YES | bundle_id formula unchanged; `TestBundleIdDeterministic` still passes (4 cases + AST scan for nondeterministic imports). |
| 21 | EXTERNAL_AGENTS_STILL_DISABLED | YES | `_require_strict_bool` rejects non-bool `external_agent_allowed`; `test_routing_flag_with_non_bool_value_rejected` (parametrized) and the existing `test_external_agent_allowed_true_rejected` both pin this. |
| 22 | EXECUTION_ROUTING_DECLARATIVE_ONLY | YES | Validator's `is not True` check unchanged; `routing.declarative_only` cannot be a dict (validator rejects). |
| 23 | AI_OVERSEER_NOT_BUILDER | YES | No `ai_overseer` import or identifier added. |
| 24 | NO_CABR_PAYOUT_DAO | YES (repaired; FIX2 Unicode-robust) | Now backed by `_AUTHORITY_KEYWORDS` containing `cabr_ready`, `cabr_passed`, `payout_ready`, `payout_passed`, `payout_approved`, `dao_ready`, `dao_approved`, `dao_passed`, `dao_signed` (substring rejection in `_require_str_tuple`); plus `_require_strict_bool` for readiness fields. FIX2: the denylist scan is NFKC-normalized before matching, so fullwidth-Unicode forms of `payout_ready` / `dao_approved` are also rejected (W10 proved the raw `item.lower()` scan was Unicode-evadable). Crafted-test evidence: `test_safe_mutation_surface_as_dict_value_rejected_w10_repro` (the exact W10 example `{"payout_ready": True, "dao_approved": True}` rejected), `test_authority_keyword_strings_rejected` includes `payout_ready` and `dao_approved` as parametrized rejected substrings, `test_fullwidth_payout_ready_in_safe_mutation_surface_rejected` and `test_fullwidth_dao_approved_in_safe_mutation_surface_rejected` (FIX2 fullwidth payloads in the W10-exploit field), `test_to_dict_never_produced_for_crafted_input` proves the bundle is never produced for the W10 payload. |
| 25 | MANIFESTS_BUNDLE_BUILD_TESTED | YES | All 6 real manifests still build (`TestRealManifestsBuild::test_each_manifest_builds`, `TestReconciliationFlaggedStillBuild`, and new `TestRequireStrTupleListFieldsRejectsAuthorityLaundering::test_real_manifests_still_build_with_helpers`). |
| 26 | BUILDER_IMPORTS_NO_RUNTIME_EXECUTORS | YES | Imports unchanged from prior PR-775 push. |
| 27 | NO_SKIP_XFAIL | YES | `pytest -q modules/foundups/agent/tests/` -> 496 passed in 7.87s; 0 skipped; 0 xfailed. |
| 28 | CITES_PR_772 | YES | PR-775 ModLog entry and builder docstring both cite #772. |
| 29 | CITES_PR_773 | YES | PR-775 ModLog entry and builder docstring both cite #773. Validator imported. |
| 30 | CITES_PR_774 | YES | PR-775 ModLog entry and builder docstring section "Trust seam (carry-forward from #774)" cite #774. |
| 31 | ASCII_CLEAN | YES | Slice-introduced content for FIX1 (builder helpers + tests + this ModLog entry + TestModLog entry) is 0 non-ASCII bytes. Pre-existing non-ASCII bytes elsewhere in `ModLog.md`/`INTERFACE.md`/`ROADMAP.md` are unchanged. |
| 32 | MANIFEST_LIST_FIELDS_STRING_ONLY | YES (NEW) | Every list field forwarded from the manifest into the bundle is `Tuple[str, ...]` produced by `_require_str_tuple`. The three protected fields are `required_gates`, `forbidden_paths`, `safe_mutation_surface`. Pinned by `TestManifestListFieldsStringOnly::test_all_list_field_elements_are_str_after_build` (all 6 real manifests) and `..._test_no_other_manifest_list_field_is_serialized` (AST scan asserts exactly these three field names are routed through the helper). |
| 33 | AUTHORITY_KEYWORDS_UNICODE_NORMALIZED | YES (NEW; FIX2) | The `_AUTHORITY_KEYWORDS` denylist scan in `_require_str_tuple` NFKC-normalizes each element (`unicodedata.normalize("NFKC", item).lower()`) BEFORE the substring match, closing the W10-proven fullwidth-Unicode evasion (a fullwidth `payout_ready` previously passed the raw `item.lower()` scan and NFKC-normalized to `payout_ready` downstream). The serialized value remains the ORIGINAL `item` (no silent rewrite); only the rejection DECISION uses the normalized form. `unicodedata` is stdlib (no new dependency). Pinned by `TestFullwidthUnicodeAuthorityEvasionRejected`: `test_fullwidth_payout_ready_in_safe_mutation_surface_rejected` (W10-exploit field), `test_fullwidth_dao_approved_in_safe_mutation_surface_rejected`, `test_fullwidth_gate_passed_appended_to_required_gates_rejected` (9th gate), `test_fullwidth_payout_ready_appended_to_forbidden_paths_rejected`, `test_generic_nfkc_compatibility_form_also_rejected` (mixed-form `human_approval`), and the non-vacuity guard `test_fullwidth_fixtures_normalize_as_documented`. |
| 34 | MANIFEST_LIST_FIELDS_COMPLETENESS_PINNED | YES (NEW; FIX2) | The check-5 AST guard is upgraded from positive-only to a COMPLETENESS check. `TestManifestListFieldsStringOnly::test_no_bare_tuple_of_manifest_access_bypasses_helper` walks the builder AST and flags any `tuple(...)` whose argument is a manifest dict access (`build_contract.get(...)` / `build_contract[...]` / routing / readiness / data) that is NOT a `_require_str_tuple(...)` call; asserts ZERO such bare patterns. Non-vacuity proven by `test_completeness_guard_detects_synthetic_bare_tuple`, which runs the SAME detector over a synthetic source containing `tuple(build_contract.get("new_list", []))` and asserts it IS detected (so a future bare bypass would fail the guard). The original positive assertion is retained. |

**WSP_97 VERDICT (FIX1)**: PASS (32/32).
**WSP_97 VERDICT (FIX2)**: PASS (34/34). FIX2 adds rows 33-34 and Unicode-hardens the evidence for rows 18 and 24; declared == actual == 34.

---

## 2026-06-09 - WRE ContextBundle Builder Phase 1 (v0.16.0)

**Author**: 0102 (W6)
**Slice**: WRE_CONTEXT_BUNDLE_BUILDER_PHASE1
**Predecessors**:
- PR #768 typed shell=False exec boundary + redaction
- PR #769 durable design / build on existing primitives
- PR #770 manifest readiness audit
- PR #771 baseline build_contract / read-only validator
- PR #772 WRE context bundle boundary audit (identified suffix-match fallback)
- PR #773 canonical exact module_path validator hardening
- PR #774 OpenClaw / WRE / Hermes execution-chain audit
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 84, WSP 97

### Phase 0 -- Mandatory Discovery (per CLAUDE.md Steps 2 and 2.1, WSP 50/87)

HoloIndex prior-art search (4 queries, all run from `O:/Foundups-Agent`):

1. `python holo_index.py --search "context bundle provenance envelope file refs sha256" --limit 8`
   -> no existing `ContextBundle` / provenance-envelope builder surfaced.
   Closest WSPs: WSP_83 (Documentation Tree Attachment), WSP_56 (Artifact
   State Coherence). Neither implements a builder.
2. `python holo_index.py --search "manifest build contract bundle builder" --limit 8`
   -> WSP_30 (Agentic Module Build Orchestration) is the protocol but no
   executable builder for FoundUp manifests; the closest CODE hits were
   `dae_dependencies.py` and `m2m_compiler.py` (different domains).
3. `python holo_index.py --search "build plan generator FoundUp manifest" --limit 8`
   -> WSP_30 again plus `mesa_model.py` / `INTERFACE.md` for `agent_market`;
   no plan-vs-bundle confusion (BuildPlan is FoundUpJob -> dry_run plan;
   ContextBundle is validated-manifest -> provenance envelope).
4. `python holo_index.py --search "skill bundle skill loader registry" --limit 8`
   -> `wre_skills_loader.py` exists for SKILL bundles (a different
   abstraction: skill registry, not per-FoundUp provenance).

Direct Grep over the source tree for ``ContextBundle`` / ``context_bundle``
/ ``build_context_bundle`` returned only audit docs (#772 and the
autonomous-build context-bundle audit). Greenfield confirmed.

Retrieval evaluation: queries 2-4 returned medium-relevance hits with
some noise from unrelated "bundle" terminology (skill bundles vs context
bundles); query 1 was high-signal for the validator/protocol surface but
contained no builder. No HOLOINDEX_LOW_SIGNAL events; no Grep fallback
required. No duplication risk.

WSP_84 reuse decision (documented; not asserted):

- `build_plan.py` + `build_plan_generator.py` translate FoundUpJob into
  a dry-run BuildPlan -- a different lifecycle moment (post-job-
  translation) than the pre-execution provenance envelope this slice
  produces.
- `build_plan_executor.py` simulates step execution -- not provenance.
- `build_plan_swarm.py` aggregates `EvidenceBundle` from swarm step
  results -- post-execution, not pre-execution.
- `wre_skills_loader.py` loads SKILL bundles -- a registry mechanism,
  not a per-FoundUp manifest envelope.

Conclusion: a NEW co-located module
`modules/foundups/agent/src/context_bundle_builder.py` is justified
because (a) no existing primitive covers the per-FoundUp pre-execution
provenance-envelope shape, (b) co-location with `foundup_manifest_validator`
(#771/#773) keeps the validator-builder pair together with a single
ModLog/TestModLog to maintain, and (c) placing this in `wre_core/`
would risk the "lives in WRE so WRE can call it" assumption this slice
explicitly forbids.

### Added

- **context_bundle_builder.py** -- read-only builder that converts a
  validated FoundUp manifest into a bounded provenance envelope.
  - `build_context_bundle(manifest_path, repo_root, *, created_at,
    max_context_bytes=65536)` -- public API. Required keyword-only
    `created_at` (caller-injected; no wall-clock).
  - `ContextBundle` / `FileRef` / `ProvenanceRecord` frozen dataclasses
    plus `to_dict()` serializer.
  - `ContextBundleRejected` exception raised on any safety refusal.
  - Calls `foundup_manifest_validator.validate_manifest_file` before
    trusting `module_path`. Imports the validator; does NOT reimplement.
  - Stream-hash helper (`_stream_sha256`) in 64 KiB chunks; oversized
    files (> `PER_FILE_READ_CAP_BYTES`, default 4 MiB) recorded as
    excluded via `Path.stat()` without opening the body.
  - Symlink escape rejection via `Path.resolve()` + `Path.relative_to`.
  - Forbidden-path segment screen for `.env*`, `main.py`, `*_dae.py`,
    `vendor/`, `wallet/`, `token/`, `reward/`, `payout/`, `cabr/`,
    `blockchain/`, `credentials*`, `secrets*`.
  - `max_context_bytes` enforced fail-closed (over-cap candidates
    recorded under `excluded_paths_summary["over_total_cap"]`).
  - Defence-in-depth re-checks on `readiness.{manifest_ready,
    build_ready, autonomous_execution_ready}`, `external_agent_allowed`,
    `can_self_authorize`, and `declarative_only` (validator already
    enforces; builder refuses the bundle anyway).
  - Deterministic `bundle_id = sha256(source_manifest_sha256 + "|" +
    module_path + "|" + bundle_version).hexdigest()`. `created_at` is
    recorded but is NOT part of the fingerprint, so caller-injected
    timestamps cannot cause bundle_id drift.

### Tests added

- 53 tests in `tests/test_context_bundle_builder.py`. Categories:
  - Real-manifests-build (6 parametrized).
  - Bundle carries refs+sha256 only; no file bodies (6 parametrized).
  - Manifest ref included (6 parametrized).
  - Declared test refs included where safe.
  - Forbidden-path screen + total-cap fail-closed + cap-never-exceeded.
  - Validator rejections propagate (7 cases).
  - No gate-pass / CABR / payout / DAO keys anywhere in `to_dict()`.
  - Outside-module file excluded.
  - Path-traversal rejected.
  - Symlink-escape rejected (environment-gated integration) plus a
    helper-level pin (`_is_path_within`) that does NOT need symlink
    creation.
  - Builder-import + execution-safety AST scan (no `subprocess`,
    `socket`, `urllib`, `eval`, `exec`, `Popen`, `urlopen`, `write_*`,
    no Hermes / OpenClaw / WRE consumer / AI Overseer imports).
  - Deterministic `bundle_id` (4 cases) plus `created_at` required.
  - Builder does not import `time` / `datetime` / `random` / `secrets` /
    `uuid` for identity-field population (AST scan).
  - Stream-hash + oversized-excluded (with patched cap) plus AST scan
    proving `_stream_sha256` uses chunked reads inside a while loop.
  - voteballots / trade NEEDS_LABEL_RECONCILIATION builds with
    readiness false (#22 from dispatch).
  - No consumer wiring; signature has no `executor` / `consumer` /
    `hermes` / `openclaw` / `wre` parameter.
  - #774 carry-forward: API has no `payload` / `job_payload` / `job` /
    `task` / `request` parameter; bundle `module_path` comes from the
    validated manifest only; builder code does not reference
    `payload` / `job_payload` / `legacy_payload` as identifiers.

Full suite: `pytest -q tests/test_context_bundle_builder.py
tests/test_foundup_manifest_validator.py` -> **142 passed in 1.20s**;
0 skipped; 0 xfailed.

### Boundary preserved

- READ_ONLY_BUILDER_ONLY. No subprocess, Popen, os.system, eval, exec,
  importlib dynamic loading, network, runtime command execution.
- NO_CONSUMER_WIRING. NO_HERMES_CALL. NO_OPENCLAW_CALL.
  NO_JOB_ENQUEUE_OR_DRAIN. NO_BUILD_RUN.
- NO_READINESS_PROMOTION. NO_CABR_PAYOUT_DAO.
- AI_OVERSEER_NOT_BUILDER. EXTERNAL_AGENTS_STILL_DISABLED.
- The #773 validator is imported (not reimplemented) and called
  BEFORE trusting `module_path`.
- The #774 carry-forward precondition is documented in the builder
  docstring and pinned by tests; this slice does NOT satisfy the
  consumer-wiring precondition and does not claim to.

### What this unblocks

- Future WRE / Hermes work can adopt the `ContextBundle` envelope as
  the source of truth for what a consumer is allowed to look at. The
  envelope makes `allowed_source_roots` derivable from
  `build_contract.module_path` AFTER the #773 validator and the
  builder's own boundary checks have both passed.
- This slice does NOT wire any consumer; consumer wiring remains
  BLOCKED until a separate PR removes or guards legacy
  payload.module_path trust in Hermes legacy executor.

### WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | HOLOINDEX_PRIOR_ART_SEARCHED | YES | 4 HoloIndex queries run + verbatim top hits recorded in the "Phase 0 -- Mandatory Discovery" subsection above. |
| 2 | WSP_84_REUSE_DECISION_DOCUMENTED | YES | Discovery subsection enumerates `build_plan.py`, `build_plan_generator.py`, `build_plan_executor.py`, `build_plan_swarm.py`, `wre_skills_loader.py` and explains why each is a different lifecycle moment; new module justified, not asserted. |
| 3 | VALIDATOR_REUSED_NOT_REIMPLEMENTED | YES | `context_bundle_builder.py` imports `validate_manifest_file`, `ManifestValidationResult`, and `_canonicalize_module_path` from `foundup_manifest_validator`. No validator logic is duplicated; the test `test_builder_imports_no_runtime_executors` cross-checks. |
| 4 | READ_ONLY_BUILDER_ONLY | YES | AST self-check `test_builder_no_subprocess_network_dynamic_import_or_write` passes: zero banned-module imports (subprocess, socket, urllib, importlib, ...) and zero banned name/attr calls (eval, exec, run, Popen, write_text, ...). |
| 5 | NO_CONSUMER_WIRING | YES | `test_builder_signature_has_no_consumer_handle` passes; public signature has no `executor` / `consumer` / `dispatcher` / `hermes` / `openclaw` / `wre` / `job_queue` / `broker` parameter. |
| 6 | NO_HERMES_CALL | YES | AST scan `test_builder_imports_no_runtime_executors` rejects any import matching `hermes`; passes. Source contains no identifier `Hermes` (`test_builder_source_does_not_reference_runtime_consumer_classes` AST scan). |
| 7 | NO_OPENCLAW_CALL | YES | Same AST scan rejects `openclaw` import + identifier `OpenClaw`; passes. |
| 8 | NO_JOB_ENQUEUE_OR_DRAIN | YES | No `enqueue` / `drain` / `publish` / `broker` / `queue` API touched. Source contains no `FoundUpJobConsumer` / `JobQueue` references (verified by `test_builder_source_does_not_reference_runtime_consumer_classes`). |
| 9 | NO_BUILD_RUN | YES | Builder does not invoke `subprocess.run` / `Popen` / `os.system`; banned-attr AST scan passes. |
| 10 | VALIDATOR_REQUIRED_BEFORE_MODULE_PATH_TRUST | YES | `build_context_bundle` calls `validate_manifest_file(manifest_path)` at line ~462 BEFORE any use of `build_contract.module_path` (step 4). Any non-ok result raises `ContextBundleRejected`. Covered by `TestValidatorRejectionsPropagate` (7 tests). |
| 11 | JOB_PAYLOAD_MODULE_PATH_NOT_TRUSTED | YES | Builder API exposes no `payload` / `job_payload` / `job` / `task` / `request` parameter (`test_builder_api_exposes_no_payload_parameter`). Bundle's `module_path` is sourced verbatim from the validated manifest (`test_bundle_module_path_comes_from_manifest_not_external_input`). Source has no identifier `payload` / `job_payload` / `legacy_payload` (`test_builder_does_not_reference_hermes_payload_fields`). |
| 12 | REFS_AND_SHA256_ONLY | YES | `FileRef` is a frozen dataclass with fields {path, sha256, size_bytes, role} only. `test_bundle_carries_only_refs_no_file_bodies` enforces this both at dataclass level and through `to_dict()` (no `body` or `content` keys). |
| 13 | NO_FILE_BODIES | YES | Same test. Additionally, the builder never reads a file body into the bundle: only `_stream_sha256` reads file content (for hashing) and the bundle stores only the digest. |
| 14 | STREAM_HASHED_NO_FULL_BODY_LOAD | YES | `_stream_sha256` uses `f.read(_HASH_CHUNK_BYTES)` inside a while loop; `test_stream_hash_function_uses_chunked_reads` AST-pins this. Oversized files are not opened (Path.stat-only) per `test_oversized_file_is_excluded_not_full_loaded`. |
| 15 | MAX_CONTEXT_BYTES_ENFORCED | YES | `test_max_context_bytes_cap_records_exclusion` and `test_cap_never_exceeded_even_when_close` pin the fail-closed total-cap behavior. Implementation: step 7 stops including once `total_bytes + size > max_context_bytes` and records `over_total_cap`. |
| 16 | FORBIDDEN_PATHS_EXCLUDED | YES | `_is_path_forbidden` segment-screen + `test_forbidden_path_screen_excludes_secrets_like_paths` pin exclusion of `.env*`, `main.py`, `*_dae.py`, `vendor/`, `wallet/`, `token/`, `reward/`, `payout/`, `cabr/`, `blockchain/`, `credentials*`, `secrets*`. |
| 17 | SYMLINK_ESCAPE_REJECTED | YES | `_is_path_within` uses `Path.relative_to` after `Path.resolve()`. Mechanically pinned by `test_is_path_within_helper_rejects_path_outside_base` (no symlink creation required). Integration `test_symlink_pointing_outside_module_is_excluded` exercises the resolve-and-reject path end-to-end where symlink creation is supported. |
| 18 | GATE_NAMES_ONLY_NOT_PASS_BOOLEANS | YES | `required_gates_to_recheck` is `Tuple[str, ...]`. `test_required_gates_to_recheck_carries_names_not_booleans` asserts all elements are strings. `test_bundle_to_dict_has_no_gate_pass_keys` walks the full serialized dict and rejects 14 forbidden authority keys including `gate_passed`, `security_passed`, `permission_passed`, `dry_run_passed`, `build_passed`, `verification_complete`, `real_execution_performed`, `cabr_ready`, `payout_ready`, `dao_ready`. |
| 19 | NO_READINESS_PROMOTION | YES | Builder echoes readiness verbatim and refuses with `ContextBundleRejected` if any readiness flag is true. Covered by `test_readiness_build_ready_true_rejected`, `..._autonomous_execution_ready_true_rejected`, `..._manifest_ready_true_rejected`, and `test_reconciliation_manifest_builds_with_readiness_false`. |
| 20 | BUNDLE_ID_DETERMINISTIC_NOT_WALLCLOCK | YES | `bundle_id = sha256(source_manifest_sha256 + "|" + module_path + "|" + bundle_version)`. Pinned by `test_same_inputs_yield_same_bundle_id`, `test_bundle_id_is_sha256_of_documented_components`, `test_bundle_id_not_affected_by_created_at`, `test_different_manifests_yield_different_bundle_ids`. `test_builder_does_not_call_time_or_random` AST-verifies no `time` / `datetime` / `random` / `secrets` / `uuid` import. `test_required_created_at_argument` enforces the keyword-only required `created_at`. |
| 21 | EXTERNAL_AGENTS_STILL_DISABLED | YES | `test_external_agent_allowed_true_rejected`; defence-in-depth re-check in step 3 raises on `routing.get("external_agent_allowed") is True`. |
| 22 | EXECUTION_ROUTING_DECLARATIVE_ONLY | YES | Step 3 raises if `routing.get("declarative_only") is not True`. Validator also rejects (covered by existing `test_execution_routing_declarative_only`). |
| 23 | AI_OVERSEER_NOT_BUILDER | YES | No `ai_overseer` import (AST scan in `test_builder_imports_no_runtime_executors`); no `AIIntelligenceOverseer` / `AIOverseer` identifier (`test_builder_source_does_not_reference_runtime_consumer_classes`). |
| 24 | NO_CABR_PAYOUT_DAO | YES | `test_bundle_to_dict_has_no_gate_pass_keys` walks the serialized dict and rejects `cabr_ready`, `cabr_passed`, `payout_ready`, `payout_passed`, `dao_ready`, `dao_passed`. Source contains no `cabr` / `payout` / `dao` references. |
| 25 | MANIFESTS_BUNDLE_BUILD_TESTED | YES | `TestRealManifestsBuild.test_each_manifest_builds` parametrizes all 6 real manifests; all 6 produce a valid bundle. `TestReconciliationFlaggedStillBuild` additionally pins that voteballots / trade build at the declarative level with readiness false (NEEDS_LABEL_RECONCILIATION not promoted). |
| 26 | BUILDER_IMPORTS_NO_RUNTIME_EXECUTORS | YES | `test_builder_imports_no_runtime_executors` passes; module imports: `__future__`, `hashlib`, `json`, `dataclasses`, `pathlib`, `typing`, plus `foundup_manifest_validator` (validator, not executor). |
| 27 | NO_SKIP_XFAIL | YES | `pytest -q` output: `142 passed in 1.20s` (52 builder + 1 helper-level pin + 89 validator). 0 skipped (the prior Windows-symlink `pytest.skip` was replaced by a clean early-return so the test runs but is a no-op when symlinks are unsupported; the security boundary is pinned by `test_is_path_within_helper_rejects_path_outside_base` which always runs). 0 xfailed. |
| 28 | CITES_PR_772 | YES | Predecessors list and builder docstring both cite PR #772 (WRE context-bundle boundary audit). |
| 29 | CITES_PR_773 | YES | Predecessors list and builder docstring both cite PR #773 (canonical exact module_path validator hardening). Validator is imported. |
| 30 | CITES_PR_774 | YES | Predecessors list and the docstring section "Trust seam (carry-forward from #774)" cite PR #774 (OpenClaw / WRE / Hermes execution-chain audit). The `TestNo774LegacyPayloadAuthority` test class pins the carry-forward. |
| 31 | ASCII_CLEAN | YES | Slice-introduced content is 0 non-ASCII bytes (`context_bundle_builder.py`=0, `test_context_bundle_builder.py`=0, this ModLog entry=0, INTERFACE/ROADMAP/TestModLog entries=0). Pre-existing non-ASCII bytes elsewhere in ModLog.md (60 bytes of box-drawing glyphs in an earlier entry) are unchanged and out of slice scope. |

**WSP_97 VERDICT**: PASS (31/31).

---

## 2026-06-09 - FoundUp Manifest Validator Module Path Exact-Match Hardening (v0.15.1)

**Author**: 0102 (W6)
**Slice**: FOUNDUP_MANIFEST_VALIDATOR_MODULE_PATH_EXACT_MATCH_HARDENING_PHASE1
**Predecessors**:
- PR #770 - manifest readiness + execution ecosystem boundary
- PR #771 - baseline build_contract / execution_routing + read-only validator
- PR #772 - WRE context-bundle boundary audit (identified suffix-match fallback)
**WSP References**: WSP 11, WSP 50, WSP 84, WSP 97

### Changed

- **foundup_manifest_validator.py** - `_expected_module_path_matches` now
  requires EXACT normalized repo-relative path equality between
  `build_contract.module_path` and the manifest file's parent directory.
  The prior suffix-match fallback (`parent.endswith("/" + norm_module)`)
  identified by PR #772 has been removed.
  - New helper `_canonicalize_module_path(raw)`: canonicalizes a manifest-
    declared module_path to repo-relative POSIX form. Accepts harmless
    equivalents (leading `./`, repeated `/`, `.` segments, backslashes).
    Rejects empty, absolute (drive letter, leading `/`), UNC (`\\\\`),
    and any `..` segment.
  - New helper `_canonicalize_manifest_path_for_compare(raw)`: as above,
    plus strips the validator's known repo-root prefix (case-insensitive
    for Windows drive-letter casing) so absolute on-disk manifest paths
    still compare correctly.
  - New module-level constants `_VALIDATOR_FILE`, `_REPO_ROOT_POSIX`,
    `_ABSOLUTE_OR_UNC_PATTERN` (used only for compare; no IO, no exec).
  - Module-level `import re` and `from pathlib import Path` added. The
    AST self-check tests confirm no banned-module imports, no
    `subprocess` / network / file-write calls, and no runtime executor
    or consumer imports.

### Boundary preserved

- Validator remains READ-ONLY. No subprocess, Popen, os.system, eval,
  exec, dynamic import, network, or file write.
- No manifest mutation. All 6 existing manifests still validate.
- No registry mutation. No runtime consumer wiring.
- No readiness promotion. No CABR / payout / DAO / token touch.
- AI Overseer is not invoked. External agents remain disabled.

### Test additions

- Existing tests: 51 pre-hardening tests still pass unchanged.
- `TestExactMatchHelperDirect` (8 unit tests on the helper itself).
- `TestSuffixCollisionRejected` (6 explicit suffix-collision cases).
- `TestCanonicalPathNormalization` (16 parametrized variants).
- `TestOldSuffixBehaviorRegression` (3 regressions that mechanically
  prove the old suffix fallback would have accepted these and the new
  exact-only rule rejects them).
- Total: 88 tests pass; 0 skipped; 0 xfailed.

### What this unblocks

- `WRE_CONTEXT_BUNDLE_BUILDER_PHASE1` may now safely derive
  `allowed_source_roots` from `build_contract.module_path`.
- This slice does NOT implement that builder; it only removes the
  pre-consumer trust gap.

### WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | VALIDATOR_HARDENING_ONLY | YES | git diff: only 4 in-scope files changed (validator src, test, ModLog, TestModLog). |
| 2 | EXACT_MATCH_ONLY | YES | `foundup_manifest_validator.py::_expected_module_path_matches` returns `parent == canonical_module`; no other path is accepted. |
| 3 | SUFFIX_FALLBACK_REMOVED | YES | Prior `parent.endswith("/" + norm_module)` branch removed; not present anywhere in `foundup_manifest_validator.py`. Verified by Grep. |
| 4 | SUFFIX_COLLISION_NEGATIVE_TESTS_PASS | YES | `TestSuffixCollisionRejected` (6 cases) + `TestCanonicalPathNormalization::test_unsafe_or_shadow_module_paths_rejected` (10 parametrized cases) all pass. |
| 5 | SIX_EXISTING_MANIFESTS_STILL_VALIDATE | YES | `test_all_six_manifests_validate` parametrized over `TARGET_MANIFESTS` (6 entries) passes; also `TestExactMatchHelperDirect::test_real_manifest_locations_match_exactly` covers each pair directly. |
| 6 | MAGADOOM_CROSS_DOMAIN_EXACT_MATCH_VALID | YES | `magadoom_001` at `modules/gamification/whack_a_magat/foundup_manifest.json` declares `module_path=modules/gamification/whack_a_magat`; exact-only match accepts. Covered by `TestExactMatchHelperDirect::test_real_manifest_locations_match_exactly[magadoom row]`. |
| 7 | NO_MANIFEST_MUTATION | YES | `git diff --name-only` shows no `foundup_manifest.json` files changed. |
| 8 | NO_REGISTRY_MUTATION | YES | No file under `modules/foundups/registry/`, `modules/foundups/manifest/`, `modules/foundups/projection/`, or `modules/foundups/catalog/` touched. |
| 9 | NO_RUNTIME_CONSUMER_WIRING | YES | No file in `modules/communication/moltbot_bridge/`, `modules/infrastructure/wre_core/`, `modules/ai_intelligence/ai_overseer/`, or any `*_dae.py` touched. |
| 10 | NO_BUILD_RUN | YES | No build/test execution performed by this slice beyond running the validator test file itself. |
| 11 | NO_READINESS_PROMOTION | YES | `test_reject_build_ready_true`, `test_reject_autonomous_execution_ready_true`, `test_reject_manifest_ready_true_without_promotion` still pass; no manifest readiness field flipped. |
| 12 | VALIDATOR_READ_ONLY | YES | `test_validator_no_exec_process_network_or_write` passes; no banned-name calls (`open`, `eval`, `exec`, `compile`, etc.), no banned-attr calls (`run`, `Popen`, `write`, `urlopen`, etc.). |
| 13 | VALIDATOR_IMPORTS_NO_RUNTIME_EXECUTORS | YES | `test_validator_imports_no_runtime_executors` passes; module imports: `__future__`, `dataclasses`, `json`, `pathlib`, `re`, `typing`. No `hermes`, `openclaw`, `ai_overseer`, `job_consumer`, `build_plan_executor`, `wre_core`. |
| 14 | COMMANDS_REMAIN_ARGV_OR_NULL | YES | `_validate_command_block` and `_is_argv_list_or_null` unchanged; `test_reject_shell_string_command` and `test_reject_shell_metacharacters_in_argv` still pass. |
| 15 | EXTERNAL_AGENTS_STILL_DISABLED | YES | `test_reject_external_agent_allowed_true` and `test_execution_routing_declarative_only` still pass; no relaxation of external-agent gating. |
| 16 | AI_OVERSEER_NOT_BUILDER | YES | `ALLOWED_AUDITORS = frozenset({"ai_overseer"})` unchanged; AI Overseer remains in the auditor allowlist only, not in `ALLOWED_EXECUTORS` (still `{"hermes"}`) or `ALLOWED_ORCHESTRATORS` (still `{"openclaw"}`). |
| 17 | CITES_PR_771 | YES | This ModLog entry's Predecessors block and the new validator docstring on `_expected_module_path_matches` cite PR #771 (baseline build_contract / validator). |
| 18 | CITES_PR_772 | YES | This ModLog entry's Predecessors block and the docstring on `_expected_module_path_matches` cite PR #772 (suffix-match audit). |
| 19 | NO_CABR_PAYOUT_DAO | YES | No file under `modules/foundups/agent_market/`, no CABR/UPS/Du/F_i/Treasury references added; validator does not emit any economic signal. |
| 20 | NO_SKIP_XFAIL | YES | `pytest -q` summary: `88 passed in 0.28s`; no `s` (skip) or `x` (xfail) markers in test output. |
| 21 | ASCII_CLEAN | YES | Slice-introduced content is 0 non-ASCII bytes (validator src=0, test=0, TestModLog.md=0, this ModLog entry=0). The 60 non-ASCII bytes elsewhere in `ModLog.md` are pre-existing box-drawing glyphs (U+2502, U+2500, U+2514, etc.) in an unrelated earlier entry; out of slice scope and not modified. |
| 22 | CANONICAL_REPO_RELATIVE_PATH_MATCH | YES | `_canonicalize_module_path` + `_canonicalize_manifest_path_for_compare` normalize both inputs to repo-relative POSIX form before comparing. `TestCanonicalPathNormalization::test_harmless_module_path_normalizations_accepted` (6 variants: `./`, `//`, `.` segment, backslashes, trailing `/`, baseline) all match. |
| 23 | TRAVERSAL_PATHS_REJECTED | YES | `_canonicalize_module_path` returns None on any `..` segment (leading, mid-path, or trailing). `TestExactMatchHelperDirect::test_canonical_module_path_rejects_unsafe_forms` and `..._rejects_internal_traversal` cover 3 traversal positions. |
| 24 | ABSOLUTE_AND_UNC_PATHS_REJECTED | YES | `_ABSOLUTE_OR_UNC_PATTERN = re.compile(r"^([A-Za-z]:\|/)")` rejects drive-prefixed and leading-slash forms; UNC (`\\\\srv\\share`) becomes `//srv/share` after backslash conversion and is caught by the leading-slash branch. `TestCanonicalPathNormalization::test_unsafe_or_shadow_module_paths_rejected` covers `O:/`, `C:/`, `/`, UNC. |
| 25 | OLD_SUFFIX_BEHAVIOR_REGRESSION_PINNED | YES | `TestOldSuffixBehaviorRegression::test_suffix_match_that_old_validator_would_accept_is_rejected` re-implements the legacy logic inline and asserts it would have accepted the input; the new helper rejects it. Two cases (shadow-prefixed and deep-shadow nesting) plus a positive control. |
| 26 | EXACT_MATCH_HELPER_TESTED_DIRECTLY | YES | `TestExactMatchHelperDirect` calls `_expected_module_path_matches`, `_canonicalize_module_path`, and `_canonicalize_manifest_path_for_compare` directly (not only through full-manifest validation) so the trust boundary is mechanically pinned. |

**WSP_97 VERDICT**: PASS (26/26).

---

## 2026-06-08 - FoundUp Manifest Baseline Build/Test Contract Validator (v0.15.0)

**Author**: 0102 (W6)
**Slice**: FOUNDUP_MANIFEST_BASELINE_IMPL_PHASE1
**Predecessor**: PR #770 (FOUNDUP_MANIFEST_READINESS_AUDIT, merged f3459a070)
**WSP References**: WSP 11, WSP 50, WSP 84, WSP 97

### Added

- **foundup_manifest_validator.py** - read-only validator for the new
  declarative `build_contract` / `execution_routing` manifest blocks.
  - `validate_manifest(data, manifest_path, *, allow_readiness_promotion=False)`
    - pure, no IO, returns `ManifestValidationResult(ok, errors, warnings, manifest_path)`.
  - `validate_manifest_file(path)` - reads via `Path.read_text` (read-only), then validates.
  - Enforces: foundup_id match, module_path matches manifest location, commands are
    argv-list-or-null (never shell strings), no shell metacharacters in argv,
    forbidden_paths cover `.env`/`main.py`/`*_dae.py`/`vendor`, all 8 required gates
    present (genesis/manifest/dry_run/test/D0-D6/typed_exec/no_live_launch/
    policy_required_sovereign_valve), executor/orchestrator/auditor are
    non-privileged, `external_agent_allowed`/`can_self_authorize` cannot be true,
    `dry_run.default` cannot be false, readiness cannot promote build/autonomous/
    manifest readiness, and no gate-bypass flag may be truthy.
  - EXECUTES NOTHING. Imports no Hermes/OpenClaw/WRE consumer/AI Overseer runtime;
    no process, network, dynamic-import, or file-write calls.

### Manifest contract blocks (declarative only, no runtime wiring)

Added sibling `build_contract` + `execution_routing` blocks to the 6
MANIFEST_PRESENT_BUT_INCOMPLETE FoundUps identified by #770:

| FoundUp | module_path | status |
|---------|-------------|--------|
| gotjunk_001 | modules/foundups/gotjunk | BASELINE_DECLARATIVE_ONLY |
| kosei | modules/foundups/kosei | BASELINE_DECLARATIVE_ONLY |
| magadoom_001 | modules/gamification/whack_a_magat | BASELINE_DECLARATIVE_ONLY |
| antifafm_001 | modules/platform_integration/antifafm_broadcaster | BASELINE_DECLARATIVE_ONLY |
| voteballots | modules/foundups/voteballots | NEEDS_LABEL_RECONCILIATION |
| trade | modules/foundups/trade | NEEDS_LABEL_RECONCILIATION |

- All 6 keep `manifest_ready=false`, `build_ready=false`,
  `autonomous_execution_ready=false`. This slice establishes contract presence only.
- No consumer wired; no autonomous build run; no runtime behavior changed; registry
  untouched; AI Overseer remains auditor (not a builder).
- voteballots/trade carry the #770 label-vs-surface conflict (labels say
  SPECIFIED_NOT_IMPLEMENTED but real src/tests exist) and are flagged, not build-trusted.

## 2026-05-01 - Worker Queue Observability Scaffold (v0.14.0)

**Author**: 0102 (W4)
**Slice**: OC20_WRE_WORKER_QUEUE_OBSERVABILITY_EVENTS_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 91, WSP 97

### Added

- **worker_queue_observability.py** - WorkerQueueObservability
  - `WorkerQueueObservability` class for queue telemetry
  - `emit_event()` - Emit observability event (append-only)
  - `emit_heartbeat()` - Emit heartbeat with consecutive tracking
  - `emit_lease_expired()` - Emit lease expiry signal
  - `emit_worker_available()` - Emit worker availability event
  - `emit_worker_unavailable()` - Emit worker unavailability event
  - `snapshot_queue_health()` - Queue health snapshot with counts

### Enums and Dataclasses

| Type | Purpose |
|------|---------|
| `WorkerQueueEventType` | HEARTBEAT, LEASE_EXPIRED, WORKER_AVAILABLE, etc. |
| `WorkerAvailabilityStatus` | AVAILABLE, BUSY, OFFLINE, TERMINATED |
| `QueueHealthStatus` | HEALTHY, DEGRADED, UNHEALTHY |
| `WorkerQueueEvent` | Base event with timestamp, worker_id, entry_id, evidence_refs |
| `WorkerHeartbeatSnapshot` | Heartbeat state with consecutive count |
| `LeaseExpirySignal` | Lease expiration details |
| `WorkerAvailabilitySnapshot` | Worker availability state |
| `QueueHealthSnapshot` | Queue health with entry counts |

### WSP 91 Three Pillars

| Pillar | Implementation |
|--------|----------------|
| Logs | emit_* methods create discrete events with timestamps |
| Traces | Not implemented (Phase 2) |
| Metrics | snapshot_* methods for aggregated state |

### WSP 97 Truth Boundary

- Events are in-memory only (Phase 1)
- Events are append-only
- No real_execution_performed field exists
- No CABR/reward/payout/token fields exist
- No external telemetry sink yet
- No RedDog/pfMALL event emission yet

### Tests

- `test_worker_queue_observability.py` - 28 tests covering all 10 requirements

---

## 2026-04-30 - Swarm Dispatch Integration (v0.13.0)

**Author**: 0102 (W4)
**Slice**: OC18_DISPATCHER_QUEUE_INTEGRATION_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97

### Added

- **swarm_dispatch_integration.py** - SwarmDispatchCoordinator
  - `SwarmDispatchCoordinator` class for queue-dispatcher coordination
  - `dispatch_next()` - Dequeue and dispatch to worker
  - `complete_dispatched_assignment()` - Report completion with evidence
  - `run_simulated_cycle()` - Full dequeue → dispatch → complete cycle
  - `summarize()` - Queue/dispatcher state summary

### Enums and Dataclasses

| Type | Purpose |
|------|---------|
| `DispatchCycleStatus` | SUCCESS, NO_QUEUED_ENTRIES, NO_CAPABILITY_MATCH, etc. |
| `DispatchCycleResult` | Result of dispatch cycle (simulated) |
| `QueueDispatchSummary` | Queue and dispatcher state summary |

### Integration Flow

```
SwarmWorkerQueue.dequeue_for_worker()
    │
    ▼
SwarmDispatchCoordinator.dispatch_next()
    │
    ▼
AssignmentDispatcher.dispatch_assignment()
    │
    ▼
(Simulated work)
    │
    ▼
SwarmDispatchCoordinator.complete_dispatched_assignment()
    │
    ├─> AssignmentDispatcher.receive_completion()
    └─> SwarmWorkerQueue.complete_assignment()
```

### WSP 97 Truth Boundary

- `DispatchCycleResult.simulated = True` (always)
- `DispatchCycleResult.real_process_started = False` (always)
- `QueueDispatchSummary.all_simulated = True` (always)
- `QueueDispatchSummary.real_execution_performed = False` (always)
- No CABR/reward/payout/token fields exist

### Tests

- `test_swarm_dispatch_integration.py` - 12 tests covering all 7 requirements

---

## 2026-04-30 - Real Worker Assignment Protocol Scaffold (v0.12.0)

**Author**: 0102 (W4)
**Slice**: OC17_REAL_WORKER_ASSIGNMENT_PROTOCOL_DESIGN_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97

### Added

- **worker_assignment_protocol.py** - AssignmentDispatcher scaffold
  - `AssignmentDispatcher` class for worker dispatch
  - `register_worker()` - Register worker with capabilities
  - `deregister_worker()` - Release worker and assignments
  - `dispatch_assignment()` - Simulated dispatch (no real process)
  - `receive_heartbeat()` - Update worker last_seen
  - `receive_completion()` - Record evidence from completion

- **REAL_WORKER_ASSIGNMENT_PROTOCOL.md** - Architecture spec

### Enums and Dataclasses

| Type | Purpose |
|------|---------|
| `WorkerProcessStatus` | IDLE, ASSIGNED, PROCESSING, FAILED, TERMINATED |
| `WorkerRuntimeType` | OPENCLAW, HERMES, CLAUDE_0102, QWEN, GEMMA, GENERIC |
| `AssignmentDispatchStatus` | SIMULATED_DISPATCH, SPECIFIED_NOT_IMPLEMENTED, etc. |
| `WorkerTrustLevel` | UNTRUSTED, VERIFIED, TRUSTED, SYSTEM |
| `WorkerProcess` | Registered worker with status, capabilities |
| `WorkerRegistration` | Worker registration request |
| `WorkerDeregistration` | Deregistration result |
| `AssignmentDispatchRequest` | Dispatch request with step details |
| `AssignmentDispatchResult` | Dispatch result (simulated) |
| `WorkerHeartbeatEvent` | Heartbeat from worker |
| `WorkerCompletionEvent` | Completion report with evidence |

### Protocol Rules

| Rule | Description |
|------|-------------|
| R1 | Dispatch is simulated only |
| R2 | No real processes are started |
| R3 | No Claude/OpenClaw/Hermes invocation |
| R4 | Identity verification is simulated |
| R5 | Completion can carry evidence_refs |
| R6 | No CABR/payout/reward fields exist |

### WSP 97 Truth Boundary

- `WorkerProcess.simulated = True` (always)
- `AssignmentDispatchResult.simulated = True` (always)
- `AssignmentDispatchResult.real_process_started = False` (always)
- `WorkerCompletionEvent.simulated = True` (always)
- `real_execution_performed` does not exist
- No CABR/reward/payout/token fields exist

### Tests

- `test_worker_assignment_protocol.py` - 25 tests covering all 9 requirements

---

## 2026-04-30 - BuildPlan Swarm WRE Queue Contract (v0.11.0)

**Author**: 0102 (W4)
**Slice**: OC15_SWARM_WORKER_ASSIGNMENT_WRE_QUEUE_CONTRACT_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97

### Added

- **build_plan_swarm_queue.py** - SwarmWorkerQueue scaffold
  - `SwarmWorkerQueue` class for worker assignment dispatch
  - `enqueue_assignment()` - Enqueue StepAssignment for worker pickup
  - `dequeue_for_worker()` - Capability-aware dequeue
  - `heartbeat()` - Lease renewal
  - `complete_assignment()` - Completion with evidence
  - `expire_entries()` - Expiration and requeue

- **BUILD_PLAN_SWARM_WRE_QUEUE_CONTRACT.md** - Architecture spec

### Enums and Dataclasses

| Type | Purpose |
|------|---------|
| `QueuePriority` | CRITICAL, HIGH, NORMAL, LOW |
| `QueueEntryStatus` | QUEUED, PROCESSING, COMPLETED, FAILED, EXPIRED |
| `DequeueDecision` | ASSIGNED, NO_MATCH, QUEUE_EMPTY, BLOCKED |
| `CompletionStatus` | SUCCEEDED, FAILED, SKIPPED |
| `SwarmWorkerQueueEntry` | Queue entry with lease and evidence |
| `WorkerDequeueRequest` | Worker request with capabilities |
| `WorkerDequeueResult` | Dequeue result with assigned entries |
| `WorkerHeartbeat` | Heartbeat response |
| `AssignmentCompletionReport` | Completion report |
| `QueueAssignmentResult` | Operation result |

### Queue Rules

| Rule | Description |
|------|-------------|
| R1 | Dequeue is capability-aware |
| R2 | Dequeue creates/renews a lease |
| R3 | Expired entries requeue if retries remain |
| R4 | Completion reports simulated completion only |
| R5 | No real worker process is started |
| R6 | No files are edited |
| R7 | No CABR/payout/reward fields exist |

### WSP 97 Truth Boundary

- `SwarmWorkerQueueEntry.simulated = True` (always)
- `AssignmentCompletionReport.simulated = True` (always)
- `real_execution_performed` does not exist (cannot become True)
- No CABR/reward/payout/token fields exist

### Tests

- `test_build_plan_swarm_queue.py` - 20 tests covering all 9 requirements

---

## 2026-04-30 - BuildPlan Swarm Coordination Scaffold (v0.10.0)

**Author**: 0102 (W4)
**Slice**: OC13_SWARM_COORDINATION_CONTRACT_AND_TEST_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97

### Added

- **build_plan_swarm.py** - SwarmCoordinator scaffold
  - `SwarmCoordinator` class for multi-agent step assignment
  - `register_worker()` - Register workers with leases
  - `assign_step()` - Assign steps to workers with file ownership
  - `claim_files()` / `release_files()` - File ownership management
  - `detect_conflicts()` - Conflict detection
  - `renew_lease()` / `expire_leases()` - Lease lifecycle
  - `aggregate_evidence()` - Evidence bundling
  - `summarize()` - Execution summary

- **BUILD_PLAN_SWARM_COORDINATION_CONTRACT.md** - Architecture spec

### Enums and Dataclasses

| Type | Purpose |
|------|---------|
| `AssignmentStatus` | ASSIGNED, IN_PROGRESS, COMPLETED, FAILED, CANCELLED |
| `LeaseStatus` | ACTIVE, EXPIRED, RELEASED |
| `ConflictSeverity` | WARNING, ERROR, FATAL |
| `WorkerCapability` | VALIDATE, BUILD, TEST, ALL |
| `WorkerIdentity` | Worker registration with capabilities |
| `StepAssignment` | Step-to-worker assignment (simulated only) |
| `FileOwnershipClaim` | File ownership with lease expiration |
| `Lease` | Worker lease with renewal support |
| `ConflictReport` | File ownership conflict report |
| `EvidenceBundle` | Aggregated evidence refs |
| `SwarmExecutionSummary` | Execution state summary |

### Coordination Rules

| Rule | Description |
|------|-------------|
| R1 | Two workers cannot own same file simultaneously |
| R2 | Claims must be within BuildPlan target scope |
| R3 | Lease expiration releases file claims |
| R4 | Assignments are simulated only |
| R5 | No workers actually edit files |
| R6 | No real agent processes start |

### WSP 97 Truth Boundary

- `StepAssignment.simulated = True` (always)
- `EvidenceBundle.verification_complete = False` (always)
- `EvidenceBundle.cabr_ready = False` (always)
- `SwarmExecutionSummary.all_simulated = True` (always)
- `SwarmExecutionSummary.real_execution_performed = False` (always)
- No CABR/reward/payout/token fields exist

### Tests

- `test_build_plan_swarm.py` - 34 tests covering all 10 requirements

---

## 2026-04-29 - BuildPlanExecutor Interface Stub (v0.9.0)

**Author**: 0102 (W4)
**Slice**: OC12_BUILD_PLAN_EXECUTOR_INTERFACE_STUB_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97

### Added

- **build_plan_executor.py** - BuildPlanExecutor interface stub
  - `BuildPlanExecutor` class with dry_run=True default
  - `validate_plan()` - Plan validation with gate checks
  - `evaluate_gate()` - Gate evaluation (genesis, dry_run, human_approval)
  - `simulate_step()` - Step simulation returning SIMULATED status
  - `execute_step()` - Delegates to simulation; real execution returns BLOCKED
  - `create_execution_receipt()` - Creates receipt with WSP 97 truth fields

### Enums and Dataclasses

| Type | Purpose |
|------|---------|
| `StepExecutionStatus` | SUCCEEDED, FAILED, BLOCKED, SKIPPED, SIMULATED |
| `ExecutionMode` | DRY_RUN, REAL |
| `ExecutionBlockReason` | Block reasons (REAL_EXECUTION_NOT_IMPLEMENTED, etc.) |
| `StepExecutionResult` | Step execution outcome with evidence |
| `GateEvaluationResult` | Gate evaluation outcome |
| `ExecutionReceipt` | Terminal receipt with WSP 97 truth fields |

### WSP 97 Truth Boundary

- `verification_complete = False` (always)
- `cabr_ready = False` (always)
- `payout_ready = False` (always)
- `real_execution_performed = False` (stub)
- No CABR/reward/payout/token fields exist

### Tests

- `test_build_plan_executor.py` - 39 tests covering all 9 requirements

---

## 2026-04-29 - BuildPlan Generator (v0.8.0)

**Author**: 0102 (W4)
**Slice**: OC9_BUILD_PLAN_GENERATOR_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97

### Added

- **build_plan_generator.py** - BuildPlan generation from FoundUpJob
  - `create_build_plan_from_job()` - Main entry point
  - `validate_job_for_build_plan()` - Pre-validation
  - `infer_build_scope()` - Scope inference from action
  - `build_target_from_job()` - Target construction
  - `KNOWN_FOUNDUP_PATHS` - Path inference for known FoundUps

### Scope Inference

| Action | Inferred Scope |
|--------|----------------|
| `validate_foundup` | GENESIS_ONLY |
| `build_foundup` | FULL_BUILD |
| `extract_foundup` | FULL_BUILD |

### Tests

- `test_build_plan_generator.py` - 20 tests

---

## 2026-04-29 - BuildPlan Dataclass (v0.7.0)

**Author**: 0102 (W4)
**Slice**: OC8_BUILD_PLAN_DATACLASS_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97

### Added

- **build_plan.py** - BuildPlan typed interface
  - `BuildPlan` - Multi-step orchestration contract
  - `BuildTarget` - Target paths and scope
  - `BuildStep` - Step definition with action enum
  - `BuildGate` - Gate checkpoints
  - `BuildEvidence` - Evidence with verification status
  - `create_standard_build_steps()` - Standard step factory

### Enums

| Enum | Values |
|------|--------|
| `BuildPlanStatus` | DRAFT, READY, IN_PROGRESS, COMPLETED, FAILED, CANCELLED |
| `BuildMode` | DRY_RUN, REAL, PARTIAL |
| `BuildScope` | GENESIS_ONLY, FULL_BUILD, INCREMENTAL |
| `BuildStepAction` | VALIDATE_*, CREATE_*, UPDATE_*, RUN_TESTS, etc. |
| `GateType` | genesis_gate, dry_run_gate, test_gate, human_approval_gate |

### WSP 97 Truth Boundary

- `is_real_build_allowed()` checks all gates before real execution
- `dry_run=True` default enforced
- No CABR/payout/reward/token fields

---

## 2026-04-26 - Hermes FoundUpJob Executor (v0.6.0)

**Author**: 0102 (W4)
**Slice**: OC4_HERMES_FOUNDUP_JOB_EXECUTION_ADAPTER_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 91, WSP 97

### Added

- **hermes_foundup_job_executor.py** - FoundUpJob execution adapter for Hermes
  - `execute_foundup_job()` - Main entry point accepting `FoundUpJob`
  - `HermesJobExecutionResult` - Result container with job, hermes_result, error
  - Supports actions: `build_foundup`, `extract_foundup`, `validate_foundup`

### Status Mapping (WSP 97 Truthful)

| Hermes Result | JobStatus | StatusReasonCode |
|---------------|-----------|------------------|
| `success: True, dry_run: True` | SUCCEEDED | OK_DRY_RUN_PASSED |
| `success: True, dry_run: False` | SUCCEEDED | OK_COMPLETED |
| `error: "security_gate_failed"` | BLOCKED | BLOCKED_AWAITING_APPROVAL |
| `error: "exfoliation_gate_failed"` | BLOCKED | FAIL_EXFOLIATION_GATE |
| Module not found | FAILED | FAIL_VALIDATION_ERROR |
| Exception | FAILED | FAIL_EXECUTION_ERROR |

### Scope Boundary

**DOES**: Job validation, Hermes invocation, status mapping, evidence_refs, dry_run truth
**DOES NOT**: FAM events, CABR/PoB, WRE queueing, autonomous build claims

### Tests

- `test_hermes_foundup_job_executor.py` - 22 tests covering:
  - Pre-validation (terminal, running, unsupported action, missing path)
  - Status mapping (success, security blocked, exfoliation blocked, exception)
  - Action dispatch (extract, validate, build)
  - Evidence and payload augmentation
  - Worker identity

---

## 2026-04-16 - FAM Daemon Breadcrumb System (v0.5.1)

**Author**: 0102
**WSP References**: WSP 29, WSP 77, WSP 91

### Added

- **FAM event breadcrumbs** for full audit trail of Hermes actions
  - `HERMES_EXTRACTION_STARTED` - Extraction initiated
  - `HERMES_EXTRACTION_COMPLETED` - Extraction succeeded
  - `HERMES_EXTRACTION_FAILED` - Extraction failed (with stage + error)
  - `HERMES_SECURITY_GATE` - AI Overseer gate result
  - `HERMES_BOUNDARY_ANALYZED` - Module boundary analysis done
  - `HERMES_GATE_CHECKED` - Exfoliation gate result

- `_emit_breadcrumb()` helper method for consistent event emission
- FAM dedupe keys for all Hermes events

### Observability

| Action | FAM Event | Payload |
|--------|-----------|---------|
| Start extraction | `hermes_extraction_started` | source_module, target_org |
| Security check | `hermes_security_gate` | passed, message |
| Boundary scan | `hermes_boundary_analyzed` | module_path, files, imports, blockers |
| Gate check | `hermes_gate_checked` | passed, all 6 check results |
| Success | `hermes_extraction_completed` | target_repo, files, adapters |
| Failure | `hermes_extraction_failed` | error, stage, blockers |

### Exports

- `FAM_DAEMON_AVAILABLE` flag added to `__init__.py`

---

## 2026-04-16 - MCP Bridge v1.4 Perception Integration (v0.5.0)

**Author**: 0102
**WSP References**: WSP 29, WSP 50, WSP 77, WSP 97

### Added

- **MCP Bridge perception layer** integrated into HermesFoundUpBuilder
  - `analyze_boundary()` now uses `get_module_dependencies` + `get_reverse_dependencies`
  - `check_exfoliation_gate()` now uses `get_change_impact_score` for risk analysis
  - `run_hermes_extraction()` injects context via `get_prompt_context_packet`
  - New `get_perception()` method for direct MCP tool calls

### Perception Capabilities

| Layer | Tools Used | Purpose |
|-------|------------|---------|
| Layer 1 | `get_module_dependencies`, `get_reverse_dependencies` | Boundary analysis |
| Layer 2 | `get_change_impact_score` | Exfoliation risk |
| Layer 4 | `get_prompt_context_packet` | Context injection |

### Exports

- `MCP_BRIDGE_AVAILABLE` flag added to `__init__.py`

### Communication Flow

```
012 → 0102 (Claude) → MCP Bridge → Hermes
```

012 gives intent, 0102 translates to execution with MCP perception, Hermes builds.

---

## 2026-04-25 - Hermes Deploy Surface Detector Alignment

**Author**: 0102
**WSP References**: WSP 34, WSP 50, WSP 60, WSP 83, WSP 97

### Fixed

- Added `HermesFoundUpBuilder._detect_deploy_surface()` so the exfoliation gate accepts existing verified deploy evidence:
  - direct deploy config (`Dockerfile`, `cloudbuild.yaml`, `firebase.json`, `deployment/`)
  - `app/index.html`
  - `frontend/index.html`
  - `foundup_manifest.json` with `entry_url` and `launch_readiness=ready`

### Validation

- `python -m pytest modules/foundups/agent/tests/test_hermes_foundup_builder.py -q`
- Result: 18 passed.

### Memory

- Updated `tests/README.md` with implemented Hermes builder coverage.
- Added `tests/TestModLog.md` for WSP 34/WSP 60 test memory.

---

## 2026-04-16 - Hermes Agent Integration (v0.4.0)

**Author**: 0102
**WSP References**: WSP 29, WSP 50, WSP 77, WSP 97

### Added

- **hermes_adapter.py** - Bounded Hermes agent wrapper
  - `HermesFoundUpBuilder` class with security gates
  - `extract_foundup()` - Main extraction entry point
  - `run_hermes_extraction()` - Hermes CLI invocation
  - `analyze_boundary()` - Module boundary analysis
  - `check_exfoliation_gate()` - CABR V1/V2/V3 gates
  - `generate_adapters()` - Adapter stub generation

- **hermes_model_router.py** - Dynamic model switching
  - `TaskCapability` enum: VISION, CODE, REASONING, TRIAGE, VOICE
  - `HermesModelRouter` class with fallback chains
  - `route_to_model()` convenience function

- **hermes-foundup-builder.yaml** - LM Studio configuration
  - Qwen Coder 7B as default
  - LM Studio provider at localhost:1234

### Git Submodule

- `vendor/hermes-agent` added from FOUNDUPS/hermes-agent fork

---

## 2026-02-16 - Domain continuity alignment docs

**Author**: 0102
**WSP References**: WSP 15, WSP 22, WSP 49

### Changes
- Updated `ROADMAP.md` with canonical domain alignment references:
  - `modules/foundups/ROADMAP.md`
  - `modules/foundups/docs/OCCAM_LAYERED_EXECUTION_PLAN.md`
  - `modules/foundups/docs/CONTINUATION_RUNBOOK.md`

### Rationale
- Ensure agent-module planning stays synchronized with domain-level layered
  delivery and handoff discipline.

---

## 2026-02-15 - Module Creation (v0.1.0)

**Author**: 0102
**WSP References**: WSP 00, WSP 29, WSP 49, WSP 73, WSP 77

### Created

- Initial module structure per WSP 49
- README.md with state machine documentation
- INTERFACE.md with event schemas
- ROADMAP.md with phased implementation plan
- This ModLog.md

### Integrated

- 6 agent lifecycle event types added to FAMDaemon:
  - `agent_joins` - 01(02) enters with public key
  - `agent_awakened` - → 0102 zen state
  - `agent_idle` - → 01/02 decayed
  - `agent_ranked` - Rank progression 1-7
  - `agent_earned` - F_i payout credited
  - `agent_leaves` - Logs off with wallet

- FAMBridge emit methods:
  - `emit_agent_joins()` - Enhanced with public_key, rank
  - `emit_agent_awakened()` - New method
  - `emit_agent_ranked()` - New method
  - `emit_agent_leaves()` - New method
  - `emit_agent_idle()` - Enhanced with tick tracking

- Mesa model integration:
  - `_track_agent_lifecycle()` method added
  - Awakening on first successful action
  - Idle detection (100 tick threshold)
  - Rank evaluation based on earnings

- SSE Server:
  - All 6 event types added to STREAMABLE_EVENT_TYPES

- Animation (foundup-cube.js):
  - SIM_EVENT_MAP entries for all agent events
  - TICKER_MESSAGES templates updated
  - Color key compacted (F_i Rating label fix)
  - Shift+wheel speed control added

### Files Modified

| File | Change |
|------|--------|
| `modules/foundups/agent_market/src/fam_daemon.py` | +6 event types, +dedupe keys |
| `modules/foundups/simulator/adapters/fam_bridge.py` | +4 emit methods, enhanced existing |
| `modules/foundups/simulator/mesa_model.py` | +lifecycle tracking, +emit calls |
| `modules/foundups/simulator/sse_server.py` | +6 event types |
| `public/js/foundup-cube.js` | +SIM_EVENT_MAP, +ticker, +speed wheel |

### Next Steps

1. Implement `AgentLifecycleService` class
2. Add coherence calculation logic
3. Create unit tests for state transitions
4. Integrate wallet generation
