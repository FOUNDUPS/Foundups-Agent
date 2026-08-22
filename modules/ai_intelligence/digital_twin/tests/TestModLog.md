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
