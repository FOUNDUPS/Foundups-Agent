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
