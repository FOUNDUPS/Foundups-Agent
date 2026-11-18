# Recursive Improvement Roadmap

**Current state:** proposal/pattern persistence with verification-gated
application, digest-verified rollback, and fail-closed `measurement_evidence`
token/latency accounting.

## Completed foundation

- error-pattern, solution-proposal, and improvement-proposal records;
- JSON persistence and compatibility global handler;
- proposal metrics that explicitly mark unmeasured token reduction as `None` / `False`;
- fail-closed `apply_improvement()` truth boundary (`blocked_unimplemented` without receipts, `blocked_verification_rejected` on failed verification, `blocked_measurement_rejected` on invalid/self-authored/regressive measurement);
- digest-verified `rollback_improvement()` with measured `total_tokens_saved` subtraction;
- receipt-backed `measurement_evidence` integration binding non-self-authored `evaluator_id`, `work_order_id`, and state SHA-256 digests.

## Required next layers

1. Define a typed candidate artifact and exact base/source identity.
2. Add an isolated executor that returns durable effect receipts.
3. Add an independent authenticated evaluator with adversarial tests.
4. Bind evaluator evidence to a signed promotion nomination.
5. Implement governed activation, canary observation, and rollback receipts.
6. Add concurrency/idempotency/recovery contracts for many FoundUp workers.
7. Add authenticated provider/runtime compute usage before evaluating any
   efficiency hypothesis.

## Production acceptance

- no proposal can label itself applied, effective, or promoted;
- author, executor, evaluator, and promoter identities are independently bound;
- every state transition is exact-artifact and exact-base reproducible;
- rollback is tested before activation;
- token/compute claims are receipt-backed and baseline-defined;
- an end-to-end RedDog/WRE RSI canary passes under failure injection.

Automatic file editing is not the next safe shortcut. The next layer is an
authenticated, isolated executor contract.
