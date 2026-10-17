# Move2Japan test memory (WSP 34 / WSP 84)

## 2026-10-17 JST — Public property search and shared Mall integration

**Source baseline:** `407292aa754a88143796163581b67ca6679eac29`, followed by the
`feat/move2japan-property-discovery-20261017` candidate changes.
**Owners:** Move2Japan property-search adapter/catalog and existing shared Mall
tile/detail components. No livechat implementation or existing BC0 test change.

### Added coverage

`property_search.cjs` executes 12 checks against the real JavaScript adapter and
five-record public catalog: listing identity within one tenant; budget boundary
and sorting; English/Japanese search; intersecting filters; source tours and land
area; nonmutating sorting; unknown data and original area labels; strict source
URL provenance; tenant/duplicate/restricted-state rejection; date/price rejection;
private/economic metadata projection; and public snapshot restrictions.

`test_property_search.py` invokes that harness with a 20-second subprocess
bound, checks exit status and requires `12 property-search checks passed`.
The Node checks and wrapper overlap; do not add their counts as independent cases.
Shared property tile/detail coverage is owned by
`public/member/tests/mall_property_listing_vm.mjs` and its existing Python
quickview wrapper. Existing BC0 and SQLite tests are retained.

### Observed validation

The root author reported these results from the shared candidate checkout:

| Check | Observed result | Scope |
| --- | --- | --- |
| Direct `property_search.cjs` | 12 checks passed | Public catalog/search adapter |
| Combined module and selected shared-Mall pytest command below | 412 passed, 1 failed in 0.92 seconds | Includes the new property wrapper and shared VM wrapper; not a green full run |
| Existing README contract selected for Move2Japan | 1 passed, 14 deselected | Required route/app/hooks/DAEmon/data/WSP documentation |

Combined command used the task environment's pytest-enabled Python:

```bash
/tmp/move2japan-tests/bin/python -B -m pytest modules/foundups/move2japan/tests public/member/tests/test_non_video_quickview_actions.py public/member/tests/test_non_video_action_surfaces.py public/member/tests/test_tile_keyboard_a11y.py public/member/tests/test_mall_tile_field.py public/member/tests/test_video_mall_field_runtime.py -q
```

The `/tmp` interpreter is a session-specific test environment, not a repository
runtime or deployment dependency. Future runs should use their qualified pytest
environment with Node available. After the two independent-review interaction
fixes, root repeated the same command: **412 passed, 1 unchanged failure in
1.13 seconds**. The shared owner replay passed 277 checks; an independent
reviewer replay passed 188 selected checks. These overlapping counts are not
additive. The final shared VM includes the real gesture engine and simulates
focus loss when a focused detail link is replaced.

### Known open failure

`modules/foundups/move2japan/tests/test_m2j_handler.py::TestIntentBucketDetection::test_cost`
expects `cost` for `is it expensive to live there`; actual result is `housing`.
The existing first-match keyword order matches housing's `live` before cost's
`expensive`. The root verified the handler and test are unchanged versus the
baseline; the skill configuration is also unchanged. This is retained as an
open BC0 defect, not reclassified as a property failure or hidden with an xfail.

### Canonical registry

The CI gate is
`modules/infrastructure/wre_core/scripts/generate_test_registry.py --check`.
Before adding the new tracked wrapper, the sole registry drift was this slice's
shared quickview wrapper gaining `process` capability for its Node harness.

Only `modules/foundups/move2japan/tests/test_property_search.py` was staged by the
documentation/registry worker. Canonical `--write` followed by `--check` succeeded:
`test_registry=current total=1720 quarantined=270`.

The retained registry delta is bounded to:

- One new Move2Japan property wrapper entry; collectable `unit`, `process`
  capability, existing `modules-foundups-move2japan-unit` shard.
- Total tracked Python test files: 1719 to 1720; quarantined count remains 270.
- Shared `test_non_video_quickview_actions.py` capability: `[]` to `["process"]`.

No unrelated entry, classification policy or registry generation rule changed.
Registry file SHA-256 after generation:
`385ce7a806fbeb36a8b03a703f0e9eb00f7a0d30edfb3597383d776b4f929e42`.
Registry counts are file counts, not pytest case counts or runtime success proof.

### Acceptance limits and next gates

These checks exercise local source data and code. They do not confirm current
property availability, media licenses, a live custom domain, publisher accounts,
paid subscriptions, token issuance or autonomous collection.

Prototype acceptance still needs real account-linked authorized submission,
permitted durable uploads, review/publication, update and withdrawal. MVP still
needs actual settled payment and delivered configured benefits, using verified
shared account/billing state with refund, expiry and revocation behavior. No
unreleased inventory may rely on client-side hiding in a public catalog.

See [test inventory](README.md), [roadmap](../ROADMAP.md) and
[source/reuse audit](../docs/08_HOUSING_DISCOVERY_REBASELINE.md).
