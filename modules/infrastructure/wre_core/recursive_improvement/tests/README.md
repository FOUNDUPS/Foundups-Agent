# tests/README.md - Test Documentation for Recursive Improvement

## Test Strategy
- **Current scope**: one async smoke test for the error-to-improvement proposal path, plus execution-truth regressions in `wre_core/tests/test_wre_telemetry_truth.py`.
- **Coverage boundary**: quantum-state restoration/coherence, metrics, concurrency, and persistence failure modes are not comprehensively covered here.
- **Authority boundary**: passing tests do not prove automatic improvement application, evaluation, promotion, activation, rollback, or production RSI.

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
