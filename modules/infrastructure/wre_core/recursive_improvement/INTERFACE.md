# Recursive Improvement Interface

## `RecursiveLearningEngine`

### `process_error(error, context=None) -> Improvement`

Extracts/persists an error pattern, generates a solution proposal, and returns
an improvement proposal. The result is not executed or independently verified.

### `extract_pattern(error, context=None) -> ErrorPattern`

Extracts and stores a heuristic error-pattern record. Similarity, type, root
cause, and structural confidence are learning metadata, not correctness proof.

### `remember_solution(pattern) -> Solution`

Returns or generates a solution proposal and stores it in proposal memory. Its
confidence/source fields do not prove execution, outcome quality, or promotion.

### `generate_improvement(pattern, solution) -> Improvement`

Creates and persists before/after proposal text linked to the supplied pattern
and solution. It does not apply, evaluate, activate, or roll back that text.

### `apply_improvement(improvement, *, verification_evidence=None, target_applicator=None, measurement_evidence=None) -> bool`

Verification-gated application contract:

- **Legacy zero-evidence call (`verification_evidence=None`, `target_applicator=None`, `measurement_evidence=None`)**:
  returns `False`, keeps `improvement.applied == False` and `applied_at == None`,
  sets `improvement.tokens_saved = None`, `improvement.metrics["token_reduction_measured"] = False`,
  and `improvement.metrics["application_status"] = "blocked_unimplemented"`.
- **Verification gate (`verification_evidence` + `target_applicator`)**:
  requires non-self-authored `AUTONOMOUS_SLICE_VERIFIER_ACCEPT`, linked
  `OUTCOME_RATCHET_RECORDED`, and `HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT`
  (`pattern_memory_admission_allowed is True`) plus a reversible `target_applicator(before_state, after_state) -> (applied_state, rollback_fn)`
  producing a non-identical state digest. Invalid verification or no-op state returns
  `False` with `application_status = "blocked_verification_rejected"`.
- **Optional Measured Benefit gate (`measurement_evidence`)**:
  - When `measurement_evidence is None`: `improvement.tokens_saved = None` and
    `improvement.metrics["token_reduction_measured"] = False`.
  - When `measurement_evidence` is supplied: validated fail-closed **before**
    calling `target_applicator` (non-empty `measurement_receipt_id`, non-empty
    `evaluator_id` distinct from `verification_result.receipt.worker_id`, exact
    `work_order_id` match, non-negative non-bool `int` `baseline_tokens` and
    `candidate_tokens` with `candidate_tokens <= baseline_tokens`, and optional
    `before_state_digest` / `after_state_digest` in `sha256:<64-hex>` or `<64-hex>`).
    Post-applicator `after_digest` is also verified against `after_state_digest`
    (invoking `rollback_fn()` on divergence). Any invalid, self-authored,
    regressive, or mismatched measurement sets `application_status = "blocked_measurement_rejected"`
    and returns `False` without retaining target mutation.
  - On valid measured apply: records `improvement.tokens_saved = baseline_tokens - candidate_tokens`,
    `improvement.metrics["token_reduction_measured"] = True`,
    `measurement_receipt_id`, `evaluator_id`, `baseline_tokens`, `candidate_tokens`
    (plus optional non-negative `baseline_latency_ms`, `candidate_latency_ms`,
    `latency_ms_saved`), and increments `self.metrics["total_tokens_saved"]`.

### `rollback_improvement(improvement) -> bool`

Executes the registered `rollback_fn()`, verifies the restored SHA-256 digest matches
`before_state`, marks `improvement.applied = False`, `rollback_available = False`,
and `improvement.metrics["application_status"] = "rolled_back"`. If
`improvement.metrics.get("token_reduction_measured") is True` and
`isinstance(improvement.tokens_saved, int)`, subtracts `improvement.tokens_saved`
from `self.metrics["total_tokens_saved"]` (clamped `>= 0`), records
`improvement.metrics["rolled_back_tokens_saved"]`, resets `improvement.tokens_saved = None`,
and sets `improvement.metrics["token_reduction_measured"] = False`.

### `get_metrics() -> dict`

Returns observed pattern/solution/proposal counters plus verified application and
measured aggregate counters:

```python
{
    "tokens_saved": None,
    "total_tokens_saved": 0,
    "token_reduction_measured": False,
}
```

Engine-level `tokens_saved` and `token_reduction_measured` remain compatibility
proposal sentinels (`None` / `False`), while receipt-backed measured savings
accumulate in `total_tokens_saved` and per-improvement `Improvement.tokens_saved`.

### `shutdown() -> bool`

Signals and joins the optional auto-save thread, then persists the final quantum
state. It returns `True` only when the thread stopped and persistence completed;
errors are redacted and return `False`. Background auto-save is disabled by
default and requires `WRE_RECURSIVE_AUTO_SAVE=1`; constructing the engine does
not otherwise start a persistence thread. Shutdown does not promote or activate
an artifact.

## `WREIntegration`

- `record_error(error, context=None)` forwards an error into proposal learning
  and may return a remembered solution proposal.
- `record_success(operation, context=None, tokens_used=0)` records the caller's
  success assertion in `successes.json`; it does not authenticate the effect,
  and the caller token value remains unverified.
- `get_optimized_approach(operation)` returns historical proposal text or
  `None`; expected savings remain unmeasured.
- `get_statistics()` returns observed/caller-reported counters and explicitly
  unmeasured token fields.

Module-level `get_learning_engine()`, `get_wre_integration()`, `record_error()`,
`record_success()`, and `get_optimized_approach()` expose process-global
compatibility instances. Their persistence is proposal/observation memory, not
effect, evaluator, promoter, Git, worker, provider, or Holo authority.

## Dataclasses

- `ErrorPattern`: extracted exception type, message, trace, context, frequency,
  and timestamps.
- `Solution`: proposed description/implementation, heuristic confidence/source,
  effectiveness defaulting to zero, and a legacy unverified `token_savings`
  field.
- `Improvement`: proposal linkage, target, before/after text, application flag,
  rollback availability, optional receipt-backed `tokens_saved` (`Optional[int]`),
  and metadata.

## Convenience functions

- `get_engine()` returns the process-global compatibility engine.
- `process_error(...)` forwards to that engine.
- `install_global_handler()` installs error-to-proposal capture.

These functions have proposal-memory authority only. They do not grant file,
Git, worker, model-provider, production, or Holo maintenance authority.
