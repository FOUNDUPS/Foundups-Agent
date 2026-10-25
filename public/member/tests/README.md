# Member Mall tests

Read [TestModLog.md](TestModLog.md) before extending a fixture. It records the
existing suites, historical results and their limits; those results are not a
fresh test run.

## Public directory and gateway owners

- `test_route_contract_bridge.py` covers shared root Play and `/f/` FX discovery,
  landing aliases, public projection isolation and protected app handoff. Its
  existing Node VM executes the actual inline `/f/` owner with controlled DOM,
  history, fetch and optional worker registration. Reuse it for public search,
  fixed legacy query/hash compatibility and protected app behavior.
- `../../../modules/foundups/pfmall/tests/test_gateway_roc_shell.py` owns the
  public navigation, About framing, root-worker lifecycle and existing gateway
  contracts. Its worker VM executes the actual root service worker.
- `../../../modules/foundups/pfmall/tests/test_gateway_terms_gate.py` owns the
  existing About admission/callback path; public discovery does not grant admission.

Other member behavior belongs to the existing field, planes, concierge, product
state and media tests listed in this directory and in the TestModLog. Reuse the
nearest owner before adding a test file. The separate projector suite owns
registry-derived public fields and committed projection parity.

## Focused execution

Run from the repository root with the declared environment dependencies and
Node on PATH (the route fixture also recognizes the standard Windows Node path):

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -B -m pytest public/member/tests/test_route_contract_bridge.py modules/foundups/pfmall/tests/test_gateway_roc_shell.py --import-mode=importlib -o addopts= -p no:cacheprovider -q
```

Use a scratch `--basetemp` outside the checkout. These controlled local tests do
not prove deployed routing, real browser layout, authentication-provider
availability, token deployment, liquidity or trading.
