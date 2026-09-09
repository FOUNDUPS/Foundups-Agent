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
- the `/future` source remains valid UTF-8 and free of the superseded speculative capacity schedule;
- the YUMORI.me contact-ledger Skillz remains registered as a WSP 95 prototype and preserves Gmail `message_id` / `thread_id` lineage;
- the contact-ledger context continues to point to the connected `YUMORI.me Contacts`, `YUMORI.me Moshpit`, and `YUMORI.me Contacts Pics` sources without embedding a private contact dump in Git.

Run from the repository root:

```powershell
python -m pytest modules/foundups/esingularity/tests -q
```
