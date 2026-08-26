# Recursive Improvement

**Status:** proposal and pattern-memory prototype; automatic artifact
improvement is not implemented.

The recursive-improvement module extracts error patterns, generates solution
and improvement proposals, and persists those records. It is a source of
candidate evidence for WRE. It is not an authenticated code editor, evaluator,
promoter, rollback controller, or proof that a suggested change worked.

## Current behavior

- `process_error()` records an error pattern, generates a solution proposal,
  and creates an `Improvement` proposal.
- Generated confidence and legacy `token_savings` fields are heuristic proposal
  metadata, not independent evaluation or measured usage.
- `apply_improvement()` deliberately returns `False`, leaves `applied=False`,
  and records `application_status=blocked_unimplemented`.
- `get_metrics()` reports observed record counts. `tokens_saved` is `None` and
  `token_reduction_measured` is `False`.
- The optional global exception handler records learning candidates only; it
  does not modify code or WSP artifacts.

## Example

```python
from modules.infrastructure.wre_core.recursive_improvement.src.learning import (
    RecursiveLearningEngine,
)

engine = RecursiveLearningEngine(project_root=repo_root)
proposal = await engine.process_error(error, {"bounded_scope": "module"})
applied = await engine.apply_improvement(proposal)

assert applied is False
assert proposal.applied is False
assert proposal.metrics["application_status"] == "blocked_unimplemented"
```

Processing can persist pattern/proposal memory under the module memory root.
Tests and callers must isolate that state before exercising write paths.

## Public records

- `ErrorPattern`: extracted error/context record.
- `Solution`: proposed implementation with heuristic confidence.
- `Improvement`: before/after proposal and application status.

No record grants repository, Git, provider, network, production, or HoloIndex
authority.

## Missing RSI layers

- independently authenticated evaluator evidence;
- governed executor with exact artifact/effect receipts;
- signed promotion and activation decision;
- rollback proof and canary observation;
- receipt-backed token/compute measurements;
- production end-to-end RSI validation.

Until those exist, recursive improvement means durable proposal learning, not
self-modifying production code.
