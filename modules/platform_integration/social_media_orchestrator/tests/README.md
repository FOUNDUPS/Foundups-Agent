# Social Media Orchestrator Tests

## Qualified scheduler evidence slice — 2026-09-28

`test_autonomous_scheduler.py::TestExecutionEvidence` contains 13 isolated
current-behavior cases for the real scheduler leaf: five logging-only action
branches, one local reminder, five stream response shapes, an exception and a
no-due batch. A passing witness can reproduce a defect: it does **not** establish
that posting succeeded or that RSI improved.

This slice admits only the named hosted CI step after source/effect review.
Host-local application execution is not qualified. The exact hosted command is:

```bash
python -I -B modules/platform_integration/social_media_orchestrator/tests/test_autonomous_scheduler.py TestExecutionEvidence -v
```

The fixture loads actual producer enum/dataclass declarations under a private
module name, denies the posting constructor and loads the unchanged scheduler
leaf without real package initialization. It uses an awaited posting spy, a
fixed clock, in-memory actions and a save spy. It does not qualify providers,
browser execution, durable save/load, replay or the meaning of a real post result.
The CI step `Run social scheduler execution evidence` selects the same 13 cases.
Fresh execution and independent evidence receipts determine their result.

The eight methods in `TestAutonomousActionScheduler` are preserved historical
tests and are **not selected or claimed passing**. Their former import path,
real constructor and plain-unittest async method were not a qualified baseline.
Selecting that legacy class now hits the denied constructor rather than opening
real state. Direct execution defaults to the qualified class.

## Historical inventory and commands

The inventory below is historical: several flat filenames no longer exist, and
the directory mixes offline tests with live integration scripts. It is not a
current safe collection list. Use the exact qualified command above for this
slice; do not infer that `TEST_MODE=True` isolates the other scripts.

## Test Structure

### Unit Tests
- `test_orchestrator.py` - Core orchestrator functionality
- `test_oauth_coordinator.py` - OAuth management tests
- `test_content_orchestrator.py` - Content formatting tests
- `test_scheduling_engine.py` - Scheduling functionality tests
- `test_twitter_adapter.py` - Twitter platform adapter tests
- `test_linkedin_adapter.py` - LinkedIn platform adapter tests

### Integration Tests
- `test_integration.py` - Cross-component integration tests
- `test_hello_world.py` - Platform hello world tests

### Vision-Based Engagement Tests (WSP 77 Phase 3: Human Supervision)
- `test_autonomous_with_validation.py` - Post-action validation: AI executes → 012 validates → Pattern Memory learns
- `test_copilot_validation.py` - Pre-action validation: AI announces intent → 012 confirms → AI executes
- `test_live_engagement_existing_chrome.py` - YouTube engagement using existing Chrome on port 9222
- `test_ui_tars_studio.py` - UI-TARS Desktop integration for YouTube Studio engagement
- `test_ui_tars_no_nav.py` - UI-TARS Desktop engagement without navigation

### Performance Tests
- `test_performance.py` - Load and performance testing

## Running Tests

### Individual Test Files
```bash
# Run specific test file
python -m pytest tests/test_orchestrator.py -v

# Run with coverage
python -m pytest tests/test_orchestrator.py --cov=src --cov-report=html
```

### Historical whole-directory command (not qualified by this slice)
```bash
# Run all tests
python -m pytest tests/ -v

# Run with detailed output
python -m pytest tests/ -v --tb=short
```

### Historical Hello World command (execution effects not qualified here)
```bash
# Run hello world tests in dry-run mode (no actual posting)
python tests/test_hello_world.py
```

## Test Configuration

Tests use environment variables for configuration:

```bash
# Optional: Real credentials for integration testing
export TWITTER_BEARER_TOKEN="your_token"
export LINKEDIN_CLIENT_ID="your_client_id"
export LINKEDIN_CLIENT_SECRET="your_secret"
export LINKEDIN_ACCESS_TOKEN="your_token"

# Test mode (default: True for safety)
export TEST_MODE="True"
```

## WSP Compliance

All tests follow WSP 49 (Module Directory Structure) and WSP 22 (ModLog Documentation) standards.

### Test Categories

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test component interactions
3. **Hello World Tests**: Safe platform connectivity tests
4. **Performance Tests**: Load and stress testing

### Safety Measures

- All tests default to dry-run mode
- Real API calls only when explicitly enabled
- Comprehensive mocking for external dependencies
- Rate limiting awareness in all test scenarios
