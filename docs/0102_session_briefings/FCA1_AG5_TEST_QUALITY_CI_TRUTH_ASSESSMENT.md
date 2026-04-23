# FCA1-AG5 - Test Quality / CI Truth Assessment

```text
Window: AG5
Slice: FCA1-AG5
Lane: Test Quality / CI Truth
Branch: main
Mode: read-only audit
Status: complete
Code files edited: none; report file created
```

## Verdict: CI_TRUTH_RISKY

CI workflow targets only 2 test directories, covering roughly 8% of module test files by file-count.

## Methodology

- **Total test files**: Counted by pattern `test_*.py` and `*_test.py` under `modules/`
- **CI-targeted paths**: Extracted from `.github/workflows/ci.yml`
- **Coverage metric**: File-count coverage (not test-case-count coverage)
- **Local verification**: AG5-local pytest run on Windows

### Commands Used

```bash
# Total test file count
find ./modules -type f \( -name "test_*.py" -o -name "*_test.py" \) | wc -l
# Result: 730

# CI workflow inspection
cat .github/workflows/ci.yml | grep -A2 "pytest"
# Targets: modules/foundups/simulator/tests/, modules/foundups/agent_market/tests/

# CI-targeted file count
find modules/foundups/simulator/tests modules/foundups/agent_market/tests -name "test_*.py" | wc -l
# Result: 58
```

## Metrics

| Metric | Count | Source |
|--------|-------|--------|
| Total test files (modules/) | 730 | find pattern count |
| CI-targeted test files | 58 | CI workflow paths |
| Not in CI (file count) | 672 | 730 - 58 |
| CI file coverage | 7.9% | 58/730 |

### AG5-Local Scan Results

The following metrics are from AG5-local scans and should be independently verified:

| Metric | Count | Command |
|--------|-------|---------|
| CI test pass (Windows) | 450/450 | `pytest modules/foundups/simulator/tests/ modules/foundups/agent_market/tests/ --ignore=...test_sse_server.py` |
| Tests with sleep() | 528 | `grep -r "time.sleep\|asyncio.sleep" modules/ --include="test_*.py" \| wc -l` |
| Heavy mocking | 130 | `grep -l "@patch\|@mock\|MagicMock" modules/*/tests/test_*.py \| wc -l` |
| Windows-specific patterns | 101 | `grep -r "os.name.*nt\|sys.platform.*win" modules/ --include="test_*.py" \| wc -l` |
| "Operational" claims | 181 | `grep -r "production\|operational\|live" modules/*/tests/test_*.py -l \| wc -l` |
| Flaky/skip/xfail markers | 15 | `grep -r "@pytest.mark.flaky\|skip\|xfail" modules/ --include="test_*.py" \| wc -l` |

## Assessment Questions

### 1. What is operational?

CI tests only these directories:
- `modules/foundups/simulator/tests/` (excludes test_sse_server.py)
- `modules/foundups/agent_market/tests/`

AG5-local measurement: 450 tests passed on Windows in 155.66s.

### 2. What is only documented?

**672 test files exist but are never run in CI.** These tests provide no CI gate. They may:
- Pass locally but fail in CI environment
- Have been broken by recent changes
- Depend on local-only fixtures (browser profiles, credentials)

Distribution of untested modules (AG5-local count):
- communication: ~213 test files (NOT in CI)
- platform_integration: ~162 test files (NOT in CI)
- infrastructure: ~110 test files (NOT in CI)
- ai_intelligence: ~108 test files (NOT in CI)

### 3. What has WRE/0102 hooks?

No WRE hooks observed in test execution. Tests are standalone pytest runs.

### 4. What lacks hooks?

All 672 non-CI tests lack any automated execution trigger. They require manual `pytest` invocation.

### 5. What has tests proving production paths?

Only the CI-scoped tests (simulator + agent_market) prove production paths via automated gates:
- FAM daemon lifecycle
- Simulator event handling
- Schema validation
- Persistence layer

### 6. What has stale or duplicated docs?

**Stale test directories** (src updated, tests not - AG5-local scan):
- modules/ai_intelligence/digital_twin/tests
- modules/ai_intelligence/multi_agent_system/tests
- modules/infrastructure/browser_actions/tests
- modules/infrastructure/cli/tests
- modules/infrastructure/foundups_vision/tests

**Duplicate test file names** (AG5-local scan):
- test_orchestrator.py (4 copies)
- test_bot_status.py (4 copies)
- test_schemas.py (3 copies)
- test_launch_runtime.py (3 copies)
- test_integration.py (3 copies)

### 7. What has extraction risk?

Tests with local dependencies that won't extract cleanly (AG5-local scan):
- 101 files with Windows-specific patterns
- 528 files using sleep() (timing-dependent)
- Tests depending on browser profiles, OAuth tokens, local databases

### 8. What has false claims / WSP 97 risk?

AG5-local scan found 181 test files containing "operational/production/live" language, but most are NOT in CI. This creates WSP 97 risk: tests may claim operational status without CI proof.

Examples observed:
- "Mock service operational" - tests mock, not production
- "Platform integrations operational" - no CI verification
- "System fully operational" - unverified claim

### 9. What is the next smallest hardening slice?

**TEST1 - CI_WRE_CORE_TEST_GATE_PHASE1**

Add WRE control-plane tests to CI. WRE is the recursive execution engine; it must be gated.

## Windows/Linux Parity

| Check | Status |
|-------|--------|
| CI runs on ubuntu-latest | YES |
| AG5-local tests run on Windows | YES (450 pass) |
| Windows-specific patterns | 101 files (AG5-local scan) |
| Path separator issues | Likely (not audited) |

**Risk**: Tests may pass on Windows but fail on Linux CI, or vice versa.

## Flaky Test Risk (AG5-local scan)

| Indicator | Count | Risk |
|-----------|-------|------|
| sleep() usage | 528 | HIGH - timing sensitive |
| @pytest.mark.flaky | 5 | Known flaky |
| @pytest.mark.skip | 8 | Disabled |
| @pytest.mark.xfail | 2 | Expected failures |

## Recommended Hardening Sequence

### TEST1 - CI_WRE_CORE_TEST_GATE_PHASE1 (P0)
Add a focused, non-live wre_core test subset to CI. WRE is control plane and must be gated.

### TEST2 - CI_AI_OVERSEER_TEST_GATE_PHASE1 (P1)
Add ai_overseer tests after wre_core gate is stable. Security-critical module.

### TEST3 - CI_YOUTUBE_CHANNEL_PULL_TEST_GATE_PHASE1 (P1)
Add active YouTube ingest tests that are no-network/mocked.

### TEST4 - TEST_CLAIM_LANGUAGE_WSP97_AUDIT_PHASE1 (P2)
Audit "operational/live/production" language in tests and qualify claims per WSP 97.

### TEST5 - TEST_SLEEP_FLAKINESS_REDUCTION_PHASE1 (P2)
Replace sleep-heavy tests with event waits, starting with highest-value modules.

---

**Generated**: 2026-04-19 (corrected 2026-04-20)
**Window**: AG5
**Slice**: FCA1-AG5
**Mode**: read-only audit
**Architect review**: ACCEPT_WITH_CORRECTIONS applied
