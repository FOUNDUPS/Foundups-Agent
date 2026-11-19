# GetK -- Get a Kei Truck

**Status**: monorepo PoC bootstrap (scaffold). `incubating`, tier `F0_DAE`.

GetK ("Get a Kei Truck") is the first vertical of a broader **decentralized,
AI-managed marketplace for used items**. The PoC category is Kei trucks; the
contract model is deliberately item-agnostic so the same rails serve any used
item.

## What this module IS (Phase 1)

A **declarative PoC contract layer** + a valid FoundUp manifest + a registry
entry, proven to validate through the existing WRE/OpenClaw/Hermes dry-run path.
It is a scaffold that proves the system can onboard a new FoundUp -- not a
working marketplace.

- `src/getk_contracts.py` -- pure Python (stdlib only) packet + rule model:
  `VehicleCapturePacket`, `GetKListingPacket`, `CostEstimatePacket`,
  `StakeholderBidGate`, `TokenUtilityRules`, `DeferredAuctionLookupProvider`.
- `foundup_manifest.json` -- passes the canonical manifest validator; readiness
  flags all `false`; `external_agent_allowed` false; dry-run default true.
- registry entry (`modules/foundups/foundup_registry.json`) -- `getk`,
  `incubating`, `SPECIFIED`, token deferred.

## What this module is NOT (deferred / out of scope)

No real auction lookup, scraping, or login/session automation; no bidding; no
payments; no PFmall frontend wiring; no AutoPost integration; no external
network/API calls; no regulatory/import legality encoded as truth. The GETK
token is **internal utility only** -- it can offset internal service fees in the
future; it is never a vehicle bid, never ownership in the vehicle, and never a
payment for the vehicle.

## Eventual product surface (future slices)

scouts discovering items -> AI-assisted media-quality review -> AI-assisted
listing-packet creation -> AI-assisted value/cost estimates -> PFmall public
browse -> stakeholder-only deeper actions (bidding). Regulatory/import legality
is owned by a separate, evidence-citing follow-up:
`GETK_IMPORT_REGULATORY_PROVIDER_AUDIT_PHASE1`.

## Tests

```bash
python -m pytest modules/foundups/getk/tests
python -m pytest modules/infrastructure/wre_core/tests/test_getk_monorepo_poc_dryrun_proof.py
```

## WSP

WSP 3 (domain placement), WSP 11 (INTERFACE), WSP 22 (ModLog), WSP 49 (module
structure), WSP 50 (pre-action), WSP 55/109 (FoundUp onboarding), WSP 97 (truth
boundaries).
