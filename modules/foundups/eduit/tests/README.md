# EDUIT verification plan

This is a specification-only module; no educational runtime tests exist yet.
The adjacent canonical schema/loader/README validators remain the owners for FoundUp
integration checks. This package does not replace or alter them.

Before implementing tests, read [TestModLog.md](TestModLog.md), inspect those existing
validators, and retrieve the closest game/PWA/session fixtures in the exact checkout.
Suggested repository checks after onboarding:

```bash
python -m pytest modules/foundups/tests/test_foundup_registry_schema.py -q
python -m pytest modules/foundups/tests/test_foundup_ai_hooks_daemon_contract_compliance.py -q
```

The loader tests and their dependencies must be discovered in the current checkout,
not assumed from an old command. Local package checks cover JSON syntax, the closed
learning-event schema, synthetic valid/invalid cases, documentation links, README
headings, namespace agreement and preservation of baseline registry entries.
They do not prove full-repository integration, HoloIndex freshness, WSP 00 execution,
learning benefit, child safety, fairness, deployment or talent detection.

POC test categories: seeded replay; scoring correctness; adaptation bounds; identical
logical results across input modalities; pause/skip; interrupted/offline continuation;
malformed/untrusted content; no undeclared data egress. Add later tests for consent,
tenant/role denial, export/deletion, sync conflicts, referrals and release authorization
only when the corresponding implementation exists.
