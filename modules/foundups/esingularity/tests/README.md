# eSingularity tests

The frontend Mosh Pit gate has focused synthetic tests. From `frontend`, run
`node --test tests/mosh-pit.test.mjs`; run `npx tsc --noEmit` for type checking.
These cover membership-before-fetch, scope/expiry, response bounds, explicit
stakeholder disclosure and escaped expandable rendering. They do not assert
that the canonical host or live sign-in has been connected.

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
