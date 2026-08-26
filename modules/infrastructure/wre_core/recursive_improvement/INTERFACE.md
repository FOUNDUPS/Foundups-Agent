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

### `apply_improvement(improvement) -> bool`

Compatibility boundary. Current behavior is fail closed:

- returns `False`;
- keeps `improvement.applied == False`;
- keeps `applied_at == None`;
- sets `improvement.metrics["application_status"]` to
  `blocked_unimplemented`;
- does not update solution effectiveness or token savings.

### `get_metrics() -> dict`

Returns observed pattern/solution/proposal counters. Token fields remain:

```python
{"tokens_saved": None, "token_reduction_measured": False}
```

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
  and metadata.

## Convenience functions

- `get_engine()` returns the process-global compatibility engine.
- `process_error(...)` forwards to that engine.
- `install_global_handler()` installs error-to-proposal capture.

These functions have proposal-memory authority only. They do not grant file,
Git, worker, model-provider, production, or Holo maintenance authority.
