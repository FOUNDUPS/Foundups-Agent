# Move2Japan tests

Updated 2026-10-17 JST. Reuse these tests before adding coverage. Current product
acceptance is public English house discovery; publisher and paid-service gates
remain future work. See [the roadmap](../ROADMAP.md) and [TestModLog](TestModLog.md).

## Existing test owners

| File | Coverage |
| --- | --- |
| `property_search.cjs` | Executes the actual public search adapter and catalog through 12 Node checks |
| `test_property_search.py` | Pytest wrapper; requires successful Node exit and the exact 12-check completion marker |
| `test_m2j_handler.py` | Existing BC0 triggers, urgency/passport parsing, intent classification, emotional redirects, routing, state, re-engagement and persistence |
| `test_m2j_stakeholder_db.py` | Existing SQLite create/get/update/resume/stats and duplicate handling with temporary databases |
| `public/member/tests/mall_property_listing_vm.mjs` | Shared Mall property-tile/detail behavior, including multiple houses in one tenant |
| `public/member/tests/test_non_video_quickview_actions.py` | Existing shared quickview tests plus its Node property harness invocation |
| `modules/foundups/tests/test_foundup_ai_hooks_daemon_contract_compliance.py` | Existing module README route/hook/namespace contract |

Repository-relative paths are shown for shared owners. The property wrapper is
one pytest test that runs 12 JavaScript checks; these are not 13 independent tests.

## Public property-search checks

The Node suite loads `public/move2japan/property-search.js` and
`properties.json` from the current checkout. It does not use a browser, contact
sources, authenticate an account or execute a crawler.

1. Five distinct listing IDs retain the single Move2Japan tenant.
2. Price sorting and an inclusive budget boundary operate on stated prices.
3. English town names, original Japanese addresses and area filters are searchable.
4. Compound search terms and area filters intersect.
5. Large-plot and virtual-tour filters use the actual source fields.
6. Alternate sorting leaves the original catalog order unchanged.
7. Missing condition/construction remain unknown and `建築面積` retains its label.
8. Unsafe, credential-bearing, unrelated or mismatched source URLs reject.
9. Foreign tenants, duplicate listing IDs and restricted availability states reject.
10. Invalid dates and nonnumeric/negative prices reject instead of being fabricated.
11. The render projection drops injected private, economic and unlicensed-media metadata.
12. The shipped public snapshot contains no paid/private fields and no broker-confirmed availability claims.

These checks establish local data/projection behavior. Source availability,
media rights and live-domain deployment require separate evidence.

## Running focused tests

From the repository root, with Node and a pytest-enabled Python installed:

```bash
node modules/foundups/move2japan/tests/property_search.cjs
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest modules/foundups/move2japan/tests/test_property_search.py -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest modules/foundups/move2japan/tests/test_m2j_stakeholder_db.py -q -p no:cacheprovider
```

The existing BC0 handler suite imports livechat dependencies through
`message_processor.py`; use the established test environment rather than
activating a livechat runtime to satisfy imports.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest modules/foundups/move2japan/tests/test_m2j_handler.py -q -p no:cacheprovider
```

## Known unchanged BC0 failure

`TestIntentBucketDetection.test_cost` expects `cost` for
`is it expensive to live there`, but the existing handler returns `housing`.
The first-match keyword loop reaches the housing keyword `live` before the cost
keyword `expensive`. The handler, skill data and existing test are unchanged by
the property-search slice.

The combined Move2Japan/shared-Mall author run on 2026-10-17 reported
**412 passed, 1 failed**; this was the sole failure. It remains an open BC0 issue
and is not skipped, masked or repaired in this slice. It does not exercise the
property-search adapter. The full combined suite must not be described as green.
Exact commands and scope are retained in [TestModLog](TestModLog.md).

## Next-stage acceptance

| Stage | Required evidence |
| --- | --- |
| POC | Real source-backed house search, correct detail selection, source dates/unknowns and shared Mall behavior; separate browser/deployment review |
| Prototype | A verified account and authorized owner/broker submit permitted media to durable storage; review, publish, edit and withdraw work |
| MVP | Actual settled customer payment and delivered configured benefit; verified shared billing identity, server filtering, refund/expiry/revocation behavior |

A static form, fake membership flag, simulated token balance or successful local
test does not establish a publisher workflow or paying-customer MVP.

## Canonical registry gate

`.github/workflows/ci.yml` runs the existing generator in check mode. It discovers
Git-tracked `test_*.py` files, so a new Python wrapper must be tracked/staged before
regeneration. JavaScript harnesses are exercised through their Python owners.

```bash
python modules/infrastructure/wre_core/scripts/generate_test_registry.py --write
python modules/infrastructure/wre_core/scripts/generate_test_registry.py --check
```

Inspect the resulting `WSP_knowledge/WSP_Test_Registry.json` diff. The property
wrapper is a collectable unit entry with `process` capability because it invokes
Node. Keep the canonical generator; do not hand-edit registry rows or change
classification rules to force admission.
