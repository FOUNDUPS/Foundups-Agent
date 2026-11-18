# Recursive Improvement

**Status:** bounded verification-gated application, digest-verified rollback, and
fail-closed measured-benefit accounting; unauthenticated automatic code editing
remains blocked.

The recursive-improvement module extracts error patterns, generates solution
and improvement proposals, persists those records, and gates bounded improvement
application on independent verification, outcome ratcheting, held-out regression
gates, and optional non-self-authored measurement receipts.

## Current behavior

- `process_error()` records an error pattern, generates a solution proposal,
  and creates an `Improvement` proposal.
- Generated confidence and legacy `Solution.token_savings` fields are heuristic
  proposal metadata, not independent evaluation or measured usage.
- Zero-evidence `apply_improvement(proposal)` fails closed (`False`), leaves
  `applied=False`, and records `application_status="blocked_unimplemented"`.
- Verification-gated `apply_improvement(proposal, verification_evidence=..., target_applicator=..., measurement_evidence=...)`
  validates independent verifier (`AUTONOMOUS_SLICE_VERIFIER_ACCEPT`), outcome
  ratchet (`OUTCOME_RATCHET_RECORDED`), and held-out regression gate
  (`HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT`) receipts before
  executing a reversible `target_applicator`.
- Optional `measurement_evidence` validates fail-closed **before** target
  mutation (requiring non-self-authored `evaluator_id != worker_id`, matching
  `work_order_id`, non-regressive `candidate_tokens <= baseline_tokens`, and
  optional `before_state_digest` / `after_state_digest` verification) or rejects
  with `application_status="blocked_measurement_rejected"`.
- `rollback_improvement(proposal)` restores `before_state`, verifies SHA-256
  restoration, and subtracts any measured `tokens_saved` from
  `engine.metrics["total_tokens_saved"]` (clamped `>= 0`).
- `get_metrics()` preserves compatibility `tokens_saved=None` and
  `token_reduction_measured=False` for unmeasured runs while tracking verified
  receipt-backed deltas in `total_tokens_saved`.
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
