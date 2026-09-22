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
| `test_linkedin_connection_policy.py` | Ten inert current-behavior qualification cases; four legacy constructor tests separate |
| `test_x_actions.py` | X action tests |
| `test_autonomous_gemini_heart.py` | Gemini Vision element detection with existing Chrome |
| `test_final_autonomous_gemini.py` | Gemini Vision standalone infrastructure test |
| `test_gemini_studio_heart.py` | Gemini Vision YouTube Studio heart button test |
| `test_gemini_js_click.py` | Gemini Vision JavaScript click injection test |

## Connection qualification scope — 2026-09-22

The ten new cases qualify current request-history/pending/simulation behavior;
they deliberately describe the pre-repair state, not safe preview acceptance.
Use the frozen inert runner referenced by the canonical RSI backlog receipt.
It isolates eager parent imports, bypasses the real constructor and selects
only these cases; ordinary whole-folder collection is not that qualification.
Four original constructor-using cases are unchanged and excluded. Both primary
and independent runs pass the same ten case IDs. See the
[current and prospective contract](../../../platform_integration/linkedin_agent/docs/LINKEDIN_REVIEW_WORKFLOW.md#rsi-connection-policy-qualification--2026-09-22).

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



