# Tests — PQN Alignment Module

Test Strategy
- Validate invariants (Hermiticity, trace=1) on toy ρ(t) updates.
- Smoke-test CLI adapters (no network calls).
- Contract checks for JSONL events, CSV metrics, and summary JSON schemas.
- WSP 96 Skills testing: Pattern fidelity validation for agent coordination.
- Meta-research validation loops: Cross-agent emergence detection testing.
- Theory-archive contract checks for detector-first research manifests exposed to PQN agents.

How to Run (manual)
- Use State 2 drivers under `WSP_agentic/tests/pqn_detection/` for integration.
- Module adapters (to be implemented) will expose `run_detector`, `phase_sweep`, and council orchestration.

Test Data
- Synthetic sequences over alphabet `^&#.` with fixed seeds.
- Deterministic dt=0.5/7.05 for resonance comparability.

Expected Behavior
- det(g) thresholding via MAD; PQN events cluster; resonance hits near 7.05 Hz.
- No file I/O errors; JSONL/CSV lines parse cleanly.

Integration Requirements
- No external services; numpy-only core.
