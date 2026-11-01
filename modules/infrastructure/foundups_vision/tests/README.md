# FoundUps Vision - Test Documentation

**WSP Reference:** WSP 34 (Test Documentation)

## Test Strategy

Vision-based testing requires:
1. Mock UI-TARS responses for unit tests
2. Screenshot fixtures for visual verification
3. Integration tests with actual UI-TARS (E2E)

## Test Files

| File | Purpose |
|------|---------|
| `test_ui_tars_bridge.py` | UITarsBridge unit tests |
| `test_account_switcher.py` | Account-switch training/export tests |
| `test_account_switch.py` | Studio account switching smoke test (manual/integration) |

`pytest modules/infrastructure/foundups_vision/tests/test_ui_tars_bridge.py -q -k TestUITarsCoordinates`
isolates offline pure decoder/grid and mocked snapshot-only verify contracts.
Other historical bridge/executor cases may contact local services; do not call
them isolated unit tests or proof of model grounding. See TestModLog for inventory.

## Running Tests

```bash
# Unit tests (mock UI-TARS)
pytest modules/infrastructure/foundups_vision/tests/ -v

# Integration tests (requires UI-TARS running)
pytest modules/infrastructure/foundups_vision/tests/ -v -m integration
```

## Test Data

- `fixtures/screenshots/` - Sample screenshots for vision testing
- `fixtures/actions/` - Sample action sequences

## Expected Behavior

- UITarsBridge connects to UI-TARS Desktop
- VisionExecutor handles multi-step workflows
- Actions are verified via screenshot comparison



