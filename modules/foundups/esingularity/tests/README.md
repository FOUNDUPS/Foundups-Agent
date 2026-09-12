# eSingularity tests

The test suite verifies the monorepo and public-presentation contracts:

- canonical FoundUp identity and WSP 104 namespace;
- manifest/registry agreement;
- Sites configuration and frontend build metadata;
- explicit token deferral rather than an invented token;
- existing public routes remain present in source;
- exactly one presentation notification is added to the existing ticker;
- the Japanese canonical source has ten slides with complete derived language states;
- floor allocation, COG DC ownership, economics labels, timed controls, assets, and outreach provenance remain truth-bound;
- the `/future` source remains valid UTF-8 and free of the superseded speculative capacity schedule.

Run from the repository root:

```powershell
python -m pytest modules/foundups/esingularity/tests -q
```

## Shared-host domain routing

`test_domain_routing.mjs` imports the actual `frontend/next.config.ts` with Node's built-in type stripping. It checks the before-files ordering, exact YUMORI.me/www host restriction, root-only internal destination, exclusion of eSingularity.ai/YUMORI.info/other hosts, and absence of broad path or query overrides. No npm dependency is needed for these configuration tests.

```powershell
node --experimental-strip-types --test modules/foundups/esingularity/tests/test_domain_routing.mjs
```

Use Node >=22.13.0, matching the frontend engine contract. The existing Validate eSingularity workflow runs this command after Node setup and retains the Python tests, catalog validation, lint and build.

These are configuration contracts, not proof of HTTP routing or publication. Before production acceptance, test fresh direct and client-side navigation against the actual Sites runtime: YUMORI.me `/` must show the movement while preserving the visible host; eSingularity.ai `/` must retain the project page; YUMORI.info must retain its redirect. Check query parameters, canonical metadata, JHR, signup, assets and browser cache behavior. See `../INTERFACE.md` for the domain and publication boundary.
