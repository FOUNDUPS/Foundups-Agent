# Public catalog projector test inventory

## 2026-10-18 — Recovered registered housing POC and canonical shell handoff

Reused `test_projector.py` and `public/member/tests/test_route_contract_bridge.py`.
Two projector cases read the actual Move2Japan registry/manifest and check the
public POC, canonical namespace, deferred token and absence of execution/publisher
authority. Eleven route cases execute the actual inline owner with controlled
DOM/fetch/history: same-tab landing/portfolio links, exact ID/destination pairing,
query non-authority, protected app/deep-app handoff, missing-token display and
retained real-token display. The existing VM gained opt-in anchor capture; its
original route checks remain active. The portfolio case exposed the existing
early-return filter initialization defect, now repaired.

Fresh command in the recovered checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 /tmp/move2japan-tests/bin/python -B -m pytest modules/foundups/public_catalog_projector/tests/test_projector.py public/member/tests/test_route_contract_bridge.py modules/foundups/tests/test_foundup_registry_schema.py --import-mode=importlib -q -p no:cacheprovider
```

Result: **284 passed in 5.83 seconds, no skips**. An initial new assertion expected
an explicit null token in the public projection; the existing generator correctly
omits null optional fields. The test was corrected to assert omission, without
changing the generator. The successful replay above is the current focused gate.
The existing `--generate --json` command reported five eligible of eighteen
registry records and zero violations. Generated output is not hand-authored.

Cross-contract command:

```bash
PYTHONDONTWRITEBYTECODE=1 /tmp/move2japan-tests/bin/python -B -m pytest modules/foundups/tests/test_namespace_guardrail.py modules/foundups/pfmall/tests/test_catalog_foundup_truth_gate.py modules/foundups/pfmall/tests/test_member_catalog_export.py --import-mode=importlib -q -p no:cacheprovider
```

Result: **56 passed, 7 failed in 0.48 seconds**. All failures cite existing
EDuit/Shield/HoloIndex values, not the Move2Japan manifest:

| Existing test owner | Failing case | Observed input |
| --- | --- | --- |
| `modules/foundups/tests/test_namespace_guardrail.py` | `TestCanonicalRouteShape.test_manifest_data_namespace_matches_pattern` | EDuit namespace is `eduit` |
| Same owner | `TestCanonicalRouteShape.test_manifest_data_namespace_contains_foundup_id` | EDuit namespace is not `idb_eduit` |
| Same owner | `TestManifestStructure.test_manifest_has_required_fields` | Shield lacks routing prefix and data namespace |
| `modules/foundups/pfmall/tests/test_catalog_foundup_truth_gate.py` | `TestCategoryEnum.test_all_categories_are_valid` | HoloIndex category is `infrastructure` |
| Same owner | `TestCategoryEnum.test_catalog_does_not_use_unknown_categories` | `infrastructure` absent from the current category enum |
| Same owner | `TestTierEnum.test_all_tiers_are_valid` | HoloIndex tier is `INFRA` |
| Same owner | `TestBoundTenants.test_bound_entry_launch_readiness_not_discoverable_only` | HoloIndex is bound and `discoverable_only` |

Byte comparison against recovered PR baseline
`db1442ae5d5c8856a9a15ef8cdd96362c824c03e` confirmed those two test owners,
the member exporter test, EDuit/Shield manifests, `pfmall/shell_core.py` and
`public/member/mall-video-catalog.json` are unchanged. The canonical Move2Japan
README contract also passed: one selected, fourteen deselected in 0.03 seconds.
The wider check is not green; no failures were skipped or masked. Node/mock-DOM
tests and registry generation establish local behavior, not deployment, browser
layout, account-provider availability, paid benefits or token issuance.

## 2026-09-21 — Optional discovery aliases

Existing owner: `test_projector.py`. The suite covers allowlist/member-field
rejection, registry-derived values, portfolio filtering, committed artifact
parity, source independence and CLI exit behavior. The same fixture now covers
optional alias grammar, all visibility states, hidden/ineligible reservations,
self/canonical/alias collisions, duplicate targets, optional field omission or
injection, and the registry schema (including trailing-newline rejection).

Local result: 97 passed, no skips. Two pytest configuration warnings arise from
intentionally disabled plugin autoload. Node/mock-browser route controls live
in the existing `public/member/tests/test_route_contract_bridge.py` owner and
are recorded in that directory's TestModLog. No production data generated.

WSP 15/22/50/97: inventory added at the canonical missing TestModLog location;
the existing test file was extended, with no duplicate suite or new framework.
