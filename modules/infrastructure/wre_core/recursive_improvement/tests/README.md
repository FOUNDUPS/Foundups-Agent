# tests/README.md - Test Documentation for Recursive Improvement

## Test Strategy
- **Current scope**: 8 async tests in `test_learning.py` covering error-to-proposal smoke flow, legacy unauthenticated fail-closed `blocked_unimplemented`, self-verified/rejected-gate `blocked_verification_rejected`, bounded end-to-end RSI apply + rollback with PatternMemory custody enforcement, unmeasured `None` preservation, valid receipt-backed `measurement_evidence` + `total_tokens_saved` accumulation + rollback subtraction, self-authored/regressive/boolean/negative measurement rejection (`blocked_measurement_rejected`), and `work_order_id` / state-digest mismatch rejection (both pre-applicator and post-applicator rollback), plus execution-truth regressions in `wre_core/tests/test_wre_telemetry_truth.py`.
- **Coverage boundary**: quantum-state restoration/coherence, concurrency, and persistence failure modes are not comprehensively covered here.
- **Authority boundary**: passing tests prove fail-closed verification and measurement enforcement on bounded reversible applicators, not unrestricted autonomous production code editing.

## How to Run
- Install dependencies: `pip install -r ../requirements.txt` (add pytest for testing)
- Run focused smoke test: `python -m pytest -q test_learning.py -p pytest_asyncio.plugin`
- Environment setup: Python 3.10+; isolate temporary and persistence paths under the caller's governed test root.

## Test Data
- Current test data: one synthetic `ValueError`.
- Dedicated quantum-state fixtures and metrics fixtures remain missing.

## Expected Behavior
- The smoke test asserts that error processing returns a linked `Improvement` proposal.
- Separate telemetry regressions prove application fails closed and shutdown returns truthful persistence status.
- State restoration, coherence thresholds, learning velocity, and broad metrics behavior still require dedicated tests.

## Integration Requirements
- Depends on wre_core for WSP protocols.
- Cross-module: Tests integration with infrastructure agents.

**WSP Note**: This is bounded contract evidence, not deterministic quantum progression or effect proof.
