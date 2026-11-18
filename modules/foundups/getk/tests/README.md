# GetK Tests

```bash
python -m pytest modules/foundups/getk/tests
python -m pytest modules/infrastructure/wre_core/tests/test_getk_monorepo_poc_dryrun_proof.py
```

## Coverage

- `test_getk_contracts.py` -- stakeholder gate (public browse open, bid gated),
  token utility rules (rejects vehicle_bid / vehicle_ownership / payment_for_vehicle;
  allows fee offset only), cost estimate is never authoritative, auction lookup is
  deferred/raises, capture uses media refs (not bodies) with auction+regulatory
  deferred, and an AST scan proving the contracts module is pure (no network /
  subprocess / file IO / external imports).
- `test_getk_manifest.py` -- manifest validates via the canonical validator;
  readiness flags all false; execution_routing locked (external_agent_allowed
  false, declarative_only true, can_self_authorize false); forbidden_paths cover
  main.py / *_dae.py / secrets / the registry; the registry entry resolves and
  does not overclaim maturity; token is utility-deferred (not EXISTS).
- WRE dry-run proof lives under `modules/infrastructure/wre_core/tests/` and
  reuses the existing OpenClaw create + WRE drain seam to prove GetK reaches the
  SIMULATED dry-run branch with `source_authority == monorepo_poc` and no real
  execution.

No skips, no xfail.
