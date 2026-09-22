# Browser Actions - Test Documentation

**WSP Reference:** WSP 34 (Test Documentation)

## Test Strategy

Browser action testing uses:
1. Mock drivers for unit tests
2. Profile fixtures for session testing
3. Integration tests with real browsers (E2E)

## Test Files

| File | Purpose |
|------|---------|
| `test_action_router.py` | Router logic tests |
| `test_youtube_actions.py` | YouTube action tests |
| `test_linkedin_actions.py` | LinkedIn action tests |
| `test_linkedin_connection_policy.py` | Seven acknowledgment plus17 preserved inert compatibility cases; four legacy constructor tests separate |
| `test_x_actions.py` | X action tests |
| `test_autonomous_gemini_heart.py` | Gemini Vision element detection with existing Chrome |
| `test_final_autonomous_gemini.py` | Gemini Vision standalone infrastructure test |
| `test_gemini_studio_heart.py` | Gemini Vision YouTube Studio heart button test |
| `test_gemini_js_click.py` | Gemini Vision JavaScript click injection test |

## Invitation acknowledgment qualification — 2026-09-23

The frozen24-case run selects `test_connection_ack_`, `test_connection_preview_`,
`test_connection_current_` and `test_connection_live_`; four constructor tests stay
excluded. Both runs pass24 with two disabled-plugin config warnings. Scripted
first/final Send results reuse the inert fixture and preserve all prior ASTs.
Exact payload/driver ordering, results, pending/history and counter controls
characterize current behavior; passing does not certify correct delivery.
Use the hash-bound isolated runner/XML in the canonical RSI backlog. See the
[observations and prospective repair](../../../platform_integration/linkedin_agent/docs/LINKEDIN_REVIEW_WORKFLOW.md#rsi-invitation-acknowledgment-qualification--2026-09-23).

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

```bash
# Unit tests (mock drivers)
pytest modules/infrastructure/browser_actions/tests/ -v

# Integration tests (requires browser)
pytest modules/infrastructure/browser_actions/tests/ -v -m integration
```

## Test Data

- `fixtures/profiles/` - Mock browser profiles
- `fixtures/responses/` - Expected action responses

## Expected Behavior

- Router correctly classifies actions
- Platform actions execute successfully
- Fallback to Selenium works when UI-TARS unavailable



