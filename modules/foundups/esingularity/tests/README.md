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
