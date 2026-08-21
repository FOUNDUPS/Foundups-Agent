# AI Gateway Tests

This directory contains offline unit and contract tests for provider routing,
catalog evidence, AutoResearch admission, runtime binding, and request safety.
Provider transports are injected or mocked; the suite must not require live
credentials or make provider calls.

## Nemotron routing coverage

`test_model_topology_proposal_lm_studio.py` verifies the local reasoning-off
caller, compact two-panel choice contract, content-free call evidence, and
evaluation-only boundary. `test_model_topology_proposal_admission.py` covers
catalog/requirements binding, provider and role substitution, production
rejection, tamper detection, and handoff to the existing held-out benchmark
harness with deterministic incumbent inclusion. Catalog coverage proves missing
or disjoint modalities remain unknown. `test_model_runtime_binding_security.py`
covers one-shot verified topology resolution, replay, trusted-time expiry, and
unavailable-provider rejection.

`test_model_autoresearch_configured_gateway_runner.py` and the configured
bootstrap safety matrix prove whole-campaign reservation occurs before first
egress, failures release only unattempted reservations, exact local/provider
routes are preserved, and preflight failure performs zero calls.
The safety suite also enforces the extracted configured-runtime boundary,
canonical prompt-guard ownership, and reduced WSP-62 bootstrap ceilings.
`test_model_topology_proposer_authenticated_provenance.py` and
`test_model_autoresearch_authenticated_promotion_authority.py` cover exact
call/admission/campaign/policy binding, trust, revocation, TTL, durable replay,
retry, and publication ordering. The production-handoff matrix proves only a
single model can enter the existing independently signed production-evidence
and runtime-binding suppliers; aggregate panel candidates fail closed.
That matrix also proves forged direct authority construction, expiry,
revocation, invalid/overlong signed TTL, non-APPLIED publication state,
malformed policy/trust, and preexisting output claims have zero
provider calls and zero output artifacts, while an exact retry succeeds after
a transient post-reservation runtime-supply failure. Adversarial transaction
coverage also proves claim-race convergence, real subprocess death recovery,
immediate durable provider-bundle zero-callback retry, and conflicting-path
plus exact APPLIED replay are
zero-callback, APPLIED directory-flush ambiguity and AUTHORIZED terminal state
recover exact artifacts without provider replay, and an APPLIED partial
two-file publication completes from its verified remaining stage. Foreign
cleanup replacements and occupied finals survive, while same-content inode
replacement, hard links, and symlinks never become valid finals. Callback-time
authority expiry has zero publication/artifact effect, pre-APPLIED expiry never
exposes valid final artifacts, and unlink denial attempts explicit quarantine
while surfacing cleanup failure; failed quarantine preserves the artifact with
an explicit failure. File-fsync failure before the terminal leaves no
terminal/APPLIED/final artifact; final-directory fsync failure after APPLIED
resumes durably with zero provider callback.
The crash-security matrix also kills real subprocesses after selection and
runtime supply but before sealing. Retry uses the durable bundle with zero
provider callbacks while preserving unproved isolated `.supply` orphans. It
proves an unreadable provider receipt fails before callback and two concurrent
bindings for one authority nonce make only one callback. POSIX-only subprocess
cases cover death after final hard-link creation and immutable target-link
creation; those cases are skipped, not simulated, on Windows.
Callback-advancing authority and evidence verifiers prove the final pure time
check blocks terminal/APPLIED or recovery publication without provider replay.
WSP-62 guards keep every extracted authority, atomic-create, claim, retained
identity, POSIX recovery, output cleanup, output, transaction, evidence, execution, recovery, runner, and
terminal-receipt module at or below 200 lines
with no function above 50 lines.

## Kimi K3 request-truth coverage

`test_kimi_k3_request_truth.py` verifies the exact OpenRouter model route
`moonshotai/kimi-k3`:

- explicit completion budgets 256, 4,096, 8,192, and 131,072;
- provider-environment budgets 256 and 8,192;
- explicit-over-environment precedence before the 4,096 floor;
- forced maximum reasoning and temperature omission;
- pre-HTTP rejection at 131,073; and
- unchanged non-K3 and non-OpenRouter behavior.

The 131,072 maximum is grounded in
`fixtures/openrouter_endpoints_k3_success.json`. Fixture evidence is a bounded
test contract, not proof of current provider availability.

## Commands

Focused request-truth test:

```text
python -m pytest -q modules/ai_intelligence/ai_gateway/tests/test_kimi_k3_request_truth.py
```

Full module suite:

```text
python -m pytest -q modules/ai_intelligence/ai_gateway/tests
```

Record material test changes in `TestModLog.md` and behavioral changes in the
module `ModLog.md`. See WSP 00, WSP 15, WSP 22, WSP 49, WSP 50, WSP 62, and
WSP 97.
