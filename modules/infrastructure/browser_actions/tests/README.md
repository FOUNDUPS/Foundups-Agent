# Browser Actions - Test Documentation

**WSP Reference:** WSP 34 (Test Documentation)

## Test Strategy

Browser action testing uses:
1. Mock drivers for unit tests
2. Profile fixtures for session testing
3. Integration tests with real browsers (E2E)

## Test Files

| File | Existing scope |
|---|---|
| `test_linkedin_connection_policy.py` |29 qualified inert cases: policy/preview/note and manager-result behavior; four legacy constructor cases excluded. |
| `test_linkedin_actions_unit.py` |Other action behaviors with fake router; not run in this qualification. |
| `test_autonomous_gemini_heart.py` |Existing-Chrome Gemini heart integration harness; not run. |
| `test_final_autonomous_gemini.py` |Standalone Chrome/Gemini integration harness; not run. |
| `test_gemini_studio_heart.py` |Gemini Studio heart targeting harness; not run. |
| `test_gemini_js_click.py` |Gemini/JavaScript click integration harness; not run. |

## Manager-result qualification — 2026-09-24

Six new fixed cases extend the same owner; all23 prior cases remain unchanged.
Local and independent runs each pass29, with four legacy constructor cases
deselected and two known plugin warnings. Passing characterizes the existing
admission gap; it does not assert repaired behavior. Status, returned/stored
object identity, fixed-clock same-ID failure, history, exact UI calls and success credit
are checked. See [TestModLog](TestModLog.md) and the
[contract](../../../platform_integration/linkedin_agent/docs/LINKEDIN_REVIEW_WORKFLOW.md#rsi-manager-result-qualification--2026-09-24).

The source/hash-bound runner,29 IDs and XML live at
`O:/Foundups-Agent-audits/20260924-rsi-manager-admission`. It uses the qualified
Python interpreter with `-I -B`, no conftests/plugin autoload, inert eager-import
boundaries, constructor bypass and fake simulator sleep. Whole-folder collection
includes browser integration harnesses and is not this bounded proof.

## Requested-note repair validation — 2026-09-23

Frozen 23 cases select `test_connection_ack_`, `test_connection_preview_`,
`test_connection_current_` and `test_connection_live_`. Baseline: 4 failures, 19 passes;
candidate and independent runs pass 23; four legacy constructor tests excluded.
Seventeen prior compatibility controls and all shared fixtures remain unchanged.
The prospective cases enforce Add/type before one Send and zero sends on their
failure, including None for an unattempted Send. None/empty message controls
preserve fallback. The isolated runner and XML are bound in the RSI backlog;
no live browser or external delivery proof is claimed. Two known warnings remain.
See [contract](../../../platform_integration/linkedin_agent/docs/LINKEDIN_REVIEW_WORKFLOW.md#rsi-requested-note-repair--2026-09-23).

## Connection preview validation — 2026-09-22

PR1869's ten cases qualified the pre-repair mutation. The prospective dry-run
oracles now replace those obsolete mutation expectations in the same owner.
The frozen17-case matrix covers allow/deny supplied/extracted metadata,
repeated previews with empty/pending/connected/quota state, fake-live click and
policy-denial controls, and missing/unavailable early errors. Baseline12fail/5pass
becomes17pass locally and independently; four original constructor tests stay
unchanged/excluded and two disabled-plugin configuration warnings remain.
The reviewed inert runner in the canonical backlog isolates eager imports,
bypasses construction and forbids preview manager/send simulation calls.
Whole-folder collection is not this bounded qualification. See the
[contract](../../../platform_integration/linkedin_agent/docs/LINKEDIN_REVIEW_WORKFLOW.md#rsi-connection-policy-preview--2026-09-22).

## Running Tests

Use the reviewed, source-bound selection above for this qualification. Rebind
the runner/source hashes in an isolated owned worktree before a later run;
historical counts are not fresh execution. The integration harnesses require
separate runtime and action authorization.

## Test Data

- `fixtures/profiles/` - Mock browser profiles
- `fixtures/responses/` - Expected action responses

## Expected Behavior

- Router correctly classifies actions
- Platform actions execute successfully
- Fallback to Selenium works when UI-TARS unavailable



