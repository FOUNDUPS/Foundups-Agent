# eSingularity tests

The test suite verifies the monorepo and public-presentation contracts:

- canonical FoundUp identity and WSP 104 namespace;
- manifest/registry agreement;
- Sites configuration and frontend build metadata;
- explicit token deferral rather than an invented token;
- existing public routes remain present in source;
- exactly one presentation notification is added to the existing ticker;
- the Japanese canonical source has ten slides with complete derived language states;
- the YUMORI movement page keeps Japanese as its source language and has complete English and Portuguese selector copy;
- floor allocation, COG DC ownership, economics labels, timed controls, assets, and outreach provenance remain truth-bound;
- the `/future` source remains valid UTF-8 and free of superseded speculative capacity schedules;
- the repository economic model preserves functional-FIN parity while demand-led sizing fails closed on missing demand, unpriced active services, and unverified grid capacity.

Run from the repository root:

```powershell
python -m pytest modules/foundups/esingularity/tests -q
```

## Shared-host domain routing

The regression boundary protects two independent concerns:

| Test surface | Contract protected |
| --- | --- |
| `test_domain_routing.mjs` | YUMORI.me/www root internally selects `/yumori`; eSingularity.ai is excluded and keeps the filesystem homepage |
| `test_yumori_national_landing.py` | The YUMORI page remains the join-first WHY/WHAT/HOW movement funnel with five committee actions, the 1,000-person target, and complete Japanese → English/Portuguese selector coverage |

Passing only one side is insufficient: correct routing to the wrong page is still a production failure, and correct page content without hostname routing is not deployed behavior.

`test_domain_routing.mjs` imports the actual `frontend/next.config.ts` with Node's built-in type stripping. It checks the before-files ordering, exact YUMORI.me/www host restriction, root-only internal destination, exclusion of eSingularity.ai/YUMORI.info/other hosts, and absence of broad path or query overrides. No npm dependency is needed for these configuration tests.

```powershell
node --experimental-strip-types --test modules/foundups/esingularity/tests/test_domain_routing.mjs
```

Use Node >=22.13.0, matching the frontend engine contract. The existing Validate eSingularity workflow runs this command after Node setup and retains the Python tests, catalog validation, lint and build.

These are configuration contracts, not proof of HTTP routing or publication. Before production acceptance, test fresh direct and client-side navigation against the actual Sites runtime: YUMORI.me `/` must show the movement while preserving the visible host; eSingularity.ai `/` must retain the project page; YUMORI.info must retain its redirect. Check query parameters, canonical metadata, JHR, signup, assets and browser cache behavior. See `../INTERFACE.md` for the domain and publication boundary.


## Economic model

Run the demand-led economic/model regression directly:

```powershell
python -m pytest modules/foundups/esingularity/tests/test_yumori_economic_model.py -q
```

The test protects the 24-offer service catalog, functional-FIN parity, demand-to-kW translation, the financial-floor distinction, and the utility-capacity gate. It must never turn an unverified site MW value into a build target.

## Portfolio regression coverage

`test_yumori_economic_model.py` also covers the bounded three-site portfolio engine.
Run the same focused file for legacy parity, demand-led sizing and portfolio tests:

```bash
python -m pytest -q modules/foundups/esingularity/tests/test_yumori_economic_model.py
```

Portfolio fixtures are synthetic unit tests, not site cost estimates. Defaults must
return INSUFFICIENT EVIDENCE, preserve Site 3/2/1 identities versus Priority 1/2/3,
exclude non-AWARDED grants, survive Sukatto removal, conserve investor/retained cash
and hold later-site deployment until its own evidence gates pass.

Costed planning tests additionally protect MODEL ONLY labels, independent site budgets, physical sales limits, idle energy, debt/investor separation, renewal costs and preservation of existing FIN/grant structures.

## Regional impact regression — 2026-09-29

The same `test_yumori_economic_model.py` now qualifies the separate
`src/yumori_regional_impact.py` calculation owner. See the
[model and native reconciliation receipt](../docs/YUMORI_REGIONAL_IMPACT.md).

Coverage includes source-derived historical uses versus an unverified lifetime
claim, retained FY2019 source-recheck status, recorded user fees, 41 native-sheet
numerical projection values, zero discount rates, zero attendance, demolition
escalation sensitivity, invalid/non-finite inputs, tourism category overlap and
unchanged commercial portfolio results before/after regional calculation.

No new test file or second financial workbook is introduced. Existing portfolio,
legacy-parity, demand and heat tests are preserved. Native FIN receipt: 41 outputs
matched the dated Python expected values; this does not certify commercial inputs.

## Website security regression

`node --experimental-strip-types --test modules/foundups/esingularity/frontend/tests/interest-security.test.mjs` runs dependency-free handler/stream rejection tests and the actual admission SQL against Node SQLite. It checks quotas, duplicate submissions, expiry/midnight rollover and publication asset boundaries. Node >=22.13 is required. Production traffic protection and deployed D1 state are separate verification boundaries.
