# Digital Twin Tests - TestModLog

**WSP Compliance**: WSP 34 (Test Documentation), WSP 22 (ModLog Updates)

## Purpose
- Record test executions, commands, environments, and outcomes.
- Provide reproducible evidence for verification steps.

## Format (minimum)
- date/time
- command(s)
- pass/fail
- short failure signature (if any)
- evidence location (log file, screenshot)

## Entries
- 2026-08-22
  - Command: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p pytest_cov modules/ai_intelligence/digital_twin/tests/test_resident_conversation_transport_contract.py --cov=modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract --cov-report=term-missing --cov-fail-under=100`
  - Result: PASS (36/36); 100% statement and branch coverage for the new contract.
  - Coverage: exact shape, authority-field injection, native JSON types,
    operation/revision semantics, digest bindings, expiry/future clock bounds,
    use-time freshness, Unicode/control characters, content-free projection,
    forged object rejection, and WSP-62 limits.
  - Environment note: two pre-existing pytest configuration warnings reported
    missing async plugin options; no test was skipped, deselected, or failed.
  - Module closure: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q modules/ai_intelligence/digital_twin/tests` PASS (117/117).
  - Dependency closure: `cd extensions/reddog && npm run test:conversation`
    PASS (15 JavaScript vectors; 32 Python contracts).
  - Registry: `python modules/infrastructure/wre_core/scripts/generate_test_registry.py --check`
    PASS (`current`, 1,567 tracked tests; new test is collectable and not quarantined).
- 2026-08-22
  - Command: `cd extensions/reddog && npm run test:conversation`
  - Result: PASS (15 shared JS vectors; 32 Python contract tests).
  - Coverage: default chat, read-only research/status, proposal-only work and
    authorization, cancel authority requirement, ambiguous `do it`, risk-only
    reasoning escalation, strict rehydration, and effect-ceiling rejection.
- 2026-08-06
  - Command: `pytest -q modules/ai_intelligence/digital_twin/tests/test_principal_memex_projection.py`
  - Result: PASS (32/32)
  - Coverage: round-trip rehydration, digest tamper, cross-principal and
    duplicate rejection, exact JSON type policy, secret material,
    pre-traversal mapping bounds, factory-bound typed results,
    multi-generation supersession, and no-authority fields.
- 2026-02-04
  - Command: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest modules/ai_intelligence/digital_twin/tests`
  - Result: PASS (17/17)
  - Modules: test_comment_drafter (3), test_decision_policy (6), test_trajectory_logger (4), test_voice_memory (4)
  - Notes: `include_videos=False` in unit tests to avoid ChromaDB Rust segfault.
