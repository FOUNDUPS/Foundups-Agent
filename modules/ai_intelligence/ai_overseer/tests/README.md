# AI Overseer Tests

This directory hosts unit and integration tests for the AI Overseer module.

Structure:
- `TestModLog.md` records test-suite changes (WSP 49 compliance).
- `conftest.py` skips heavy legacy suites unless explicitly requested.
- `test_analysis.py` lightweight mission analysis helpers.
- `test_planning.py` coordination planning helpers.
- `test_execution.py` execution routing helpers.
- `test_mcp.py` MCP enum smoke checks.
- `test_mixins_extended.py` extended coverage for mixin fallbacks.
- `test_monitor_flow.py` witness loop coverage (gated).
- `test_openclaw_security_sentinel.py` OpenClaw sentinel policy and cache behavior.
- `test_ai_overseer_openclaw_security.py` AI Overseer sentinel wiring and monitor lifecycle.
- `test_openclaw_security_alerts.py` OpenClaw security event emission, dispatch, and dedupe behavior.
- `test_m2m_holo_retrieval_benchmark.py` generation-bound, non-mutating Holo
  benchmark Skillz runtime coverage.

## Running Tests

Quick run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest modules/ai_intelligence/ai_overseer/tests -q
```

Targeted OpenClaw security tests:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest modules/ai_intelligence/ai_overseer/tests/test_openclaw_security_sentinel.py modules/ai_intelligence/ai_overseer/tests/test_ai_overseer_openclaw_security.py modules/ai_intelligence/ai_overseer/tests/test_openclaw_security_alerts.py -q
```

## Opt-in Flags

- `AI_OVERSEER_WITNESS_LOOP=1` enables witness loop scenarios.
- `AI_OVERSEER_HEAVY_TESTS=1` re-enables heavy regression files.

The Holo retrieval benchmark tests are explicitly allowlisted in the default
lane; broader legacy AI Overseer suites remain opt-in.

The benchmark regression proves canonical authority-root selection, governed
owner-query invocation, exact owner-error preservation, and non-mutation. The
2026-08-27 focused benchmark/navigation matrix passed 56 tests; the live corpus
correctly returned `quality_below_policy`, not success.

Keep these flags off for fast deterministic runs; enable intentionally for full-stack validation.
