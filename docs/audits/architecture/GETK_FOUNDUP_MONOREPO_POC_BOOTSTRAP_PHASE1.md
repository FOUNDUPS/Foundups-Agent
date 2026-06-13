# GetK FoundUp Monorepo PoC Bootstrap -- Phase 1

- Slice: GETK_FOUNDUP_MONOREPO_POC_BOOTSTRAP_PHASE1
- Worker-Lane: W6 / AUTHOR | Base SHA: 20c26b7d4 (origin/main after #799)
- Risk class: CODE_NON_SPINE / PRODUCT_FOUNDUP_BOOTSTRAP
- Method: WSP_00 / WSP_50 (pre-action) / WSP_97 (truth boundary)
- Merge: STOP at MERGE_READY. Not self-merged.

## 1. Mission

Test the operational-WRE build path by adding a NEW FoundUp -- GetK -- to the
roster and proving it validates through the existing dry-run path without real
execution. The slice proves: (1) GetK is representable in the registry; (2) GetK
has a valid manifest/build contract; (3) GetK has a minimal PoC module scaffold +
test contract; (4) the existing WRE/OpenClaw/Hermes dry-run path validates GetK;
(5) source authority stays `monorepo_poc` and cannot self-promote.

Result: ALL FIVE proven. The dry-run seam supported GetK with NO new wiring (no
`WRE_GETK_DRYRUN_SEAM_GAP`).

## 2. GetK Product Framing

GetK = "Get a Kei Truck." The PoC category is Kei trucks. The outcome is a
reusable, AI-managed marketplace for ANY used item; the contract model is
item-agnostic (category defaults to `kei_truck` but is a field, not a hard-code).

Eventual surface (future slices, NOT built here): scouts discovering items ->
AI-assisted media-quality review -> AI-assisted listing-packet creation ->
AI-assisted value/cost estimates -> PFmall public browse -> stakeholder-only
deeper actions (bidding).

Token boundary: the GETK token may offset internal marketplace/service fees in
the future. It is NOT the vehicle bid, NOT ownership in the vehicle, and does NOT
replace the transaction. In this slice the token is `TOKEN_DEFERRED` (utility
symbol reserved; no token economics implemented).

## 3. Phase 0 HoloIndex Results

| # | Query | Rating | Top hits / note |
|---|-------|--------|-----------------|
| 1 | foundup registry manifest build contract add new FoundUp | HIGH | `foundup_registry_loader.py`, `tests/test_foundup_registry_schema.py`, `modules/foundups/INTERFACE.md`, WSP 98/104/55/109. Exact registry mechanism. |
| 2 | ContextBundle dry-run consumer FoundUpJob validate_foundup | HIGH | `context_bundle_dry_run_consumer.py`, `context_bundle_builder.py`, WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1. Exact dry-run seam. |
| 3 | GotJunk CapturedItem listing capture PFmall | MEDIUM | `pfmall_catalog.py`, PFMALL identity/runtime reports, WSP 109. No gotjunk CapturedItem exists (capture is not yet a FoundUp pattern). |
| 4 | AutoPost reusable capture engine ListingRecord | MEDIUM | AUTOPOST_REUSABLE_CAPTURE_ENGINE_AUDIT_PHASE1, WSP 55. AutoPost capture engine is an audit doc, not a wired engine. |
| 5 | GetK Kei truck FoundUp | LOW / FALSE_LEAD | GetK did not exist at base; surfaced `openclaw_foundup_orchestrator.py` (the create entry, useful) + simulator noise. |

Direct reads were required for the load-bearing facts (registry schema, manifest
validator, the parameterized vertical-proof seam, the resolver's foundup_id
manifest scan) -- HoloIndex located the files; the contracts came from reading
them. HOLOINDEX_LOW_SIGNAL follow-up: a registry-indexing bridge (Section 9) would
let a query like Q5 surface a newly-registered FoundUp.

## 4. Registry + Manifest Changes

Registry (`modules/foundups/foundup_registry.json`): added one entity `getk`
(entity_type foundup, module_path `modules/foundups/getk`, stage `incubating`,
tier `F0_DAE`, implementation_status `SPECIFIED`, poc_status `poc`,
prototype_gate_status `pending`, manifest_status `exists`,
hermes_openclaw_build_status `scaffold`, token_status `TOKEN_DEFERRED`,
token_symbol `GETK`, public_surface_status `hidden`, portfolio_ready false). Bumped
`last_updated`. The entry passes `test_foundup_registry_schema.py` (46) and the
#799 catalog projector (`test_projector.py`, 42).

Manifest (`modules/foundups/getk/foundup_manifest.json`): valid under the
canonical `foundup_manifest_validator`. `build_contract.module_path ==
modules/foundups/getk`; readiness flags all false; `dry_run.default` true;
`external_agent_allowed` false; `declarative_only` true; `can_self_authorize`
false; all 8 required gates; forbidden_paths include `main.py`, `**/*_dae.py`,
secrets, and `modules/foundups/foundup_registry.json` (registry mutation
out-of-scope).

## 5. PoC Contract Model

`modules/foundups/getk/src/getk_contracts.py` (pure stdlib; AST-proven no
network/subprocess/file-IO):

- `VehicleCapturePacket` -- captured item; declared fields are scout-declared,
  not verified; `auction_lookup` and `regulatory_status` are forced to
  `"deferred"` (construction raises otherwise). `MediaRef` is a pointer, never a
  body.
- `GetKListingPacket` -- `visibility="public_browse"`,
  `stakeholder_required_for_bid=True`.
- `CostEstimatePacket` -- `is_authoritative` always False (raises if set True); a
  disclaimer is always present.
- `StakeholderBidGate.allows(action, is_stakeholder)` -- public browse for all;
  bid/offer/inspect_deep/settle require a stakeholder; unknown actions fail closed.
- `TokenUtilityRules.validate_use(use)` -- allows only
  `offset_internal_service_fee`; raises for `vehicle_bid`, `vehicle_ownership`,
  `payment_for_vehicle`.
- `DeferredAuctionLookupProvider.lookup()` -- raises NotImplementedError; owned by
  `GETK_IMPORT_REGULATORY_PROVIDER_AUDIT_PHASE1`.

## 6. WRE/OpenClaw/Hermes Dry-Run Proof

`modules/infrastructure/wre_core/tests/test_getk_monorepo_poc_dryrun_proof.py`
reuses the EXISTING create+drain seam (the same path as the parameterized
`test_operational_wre_monorepo_poc_vertical_proof.py`): REAL OpenClaw
`dispatch_foundup(None, "validate foundup getk --dry-run")` -> queued
`validate_foundup` job -> REAL WRE `drain_openclaw_queue_with_retention` ->
Hermes executor (SIMULATED) -> ContextBundle dry-run.

Asserted (PASS): job reaches `SIMULATED`; `real_execution_performed` False;
`context_bundle_dry_run.source_authority == "monorepo_poc"`;
`resolved_module_path == "modules/foundups/getk"` (the shared validated resolver
derived it from GetK's manifest -- the create payload carried no module_path);
readiness flags false; `verification_complete` / `cabr_ready` / `payout_ready`
False; and `subprocess.Popen/run/call` + the real delegate loader were asserted
**not-called** through the full seam. HERMES_DELEGATE_ENABLED unset.

Verdict: the existing seam validates GetK as-is. No new wiring. No seam gap.

## 7. Tests Added

| File | Count | What |
|------|-------|------|
| `modules/foundups/getk/tests/test_getk_contracts.py` | 16 | gate, token rules, estimate-not-authoritative, deferred auction, capture refs/deferred, AST purity |
| `modules/foundups/getk/tests/test_getk_manifest.py` | 11 | manifest validates, readiness false, routing locked, forbidden paths, registry resolves, no overclaim, token utility-deferred |
| `modules/infrastructure/wre_core/tests/test_getk_monorepo_poc_dryrun_proof.py` | 2 | reaches SIMULATED; full create+drain dry-run proof |

Cross-checks unchanged: registry schema 46; catalog projector 42; the existing
gotjunk vertical proof still passes. No skips, no xfail. Non-vacuous: every test
asserts a concrete behaviour (a gate denies, a use raises, the seam reaches
SIMULATED with the resolved path).

## 8. Out-of-Scope Boundaries

NOT done: real vehicle image recognition; VIN/plate OCR; real auction lookup,
login, session automation, or scraping; real bidding; payments; token contract /
token economics; PFmall UI changes; AutoPost integration; legal/import compliance
rules; any state/port recommendation; production listing ingestion; external
repo; source_authority promotion; CABR/PAYOUT/DAO/MVP claims; Docker; OAuth;
HERMES_DELEGATE_ENABLED change; external network/API calls; WSP mutation;
NAVIGATION.py edit.

Legal/regulatory: the Kei-truck state/import discussion is unverified and
time-sensitive and is NOT encoded as product truth. It is deferred to
`GETK_IMPORT_REGULATORY_PROVIDER_AUDIT_PHASE1`, which must browse current
official/state sources and cite them.

## 9. Risks and Next Slices

Risk: a scaffold can read as a working marketplace. Mitigation: readiness flags
false; implementation_status SPECIFIED; token deferred; auction/regulatory
deferred-and-raising; estimates non-authoritative; the audit + ModLog state the
boundaries explicitly.

**Skillz gap (assessed this slice, per 012):** two read-only assessors confirmed
the system has the RAILS (registry, manifest/build-contract, the WRE dry-run
seam, the `autonomous_slice_worker` orchestration meta-skill, `wre_skills_loader`)
but:

- No FoundUp carries product SKILLz (capture / media-quality / listing /
  valuation / stakeholder-gate) -- GetK would be the first to need them.
- There is NO end-to-end WRE BUILD skill that onboards a FoundUp
  (registry+manifest+scaffold+dry-run). That onboarding was performed MANUALLY by
  the worker in THIS slice -- which is precisely the spec a future build-skill
  should encode.
- The FoundUp registry is NOT HoloIndex-indexed (the docs pass rglobs `*.md`
  only), so a newly-added FoundUp is "remembered" via its README on the next
  reindex, not via registry lookup. The registry is a "dark source" to HoloIndex.

Named next slices (NOT built here):
1. `GETK_IMPORT_REGULATORY_PROVIDER_AUDIT_PHASE1` -- cite official import sources.
2. `GETK_CAPTURE_SCOUT_SKILL_PHASE1`, `GETK_MEDIA_QUALITY_REVIEW_SKILL_PHASE1`,
   `GETK_LISTING_PACKET_SKILL_PHASE1`, `GETK_VALUATION_ESTIMATE_SKILL_PHASE1` --
   product SKILLz (item-agnostic).
3. `WRE_FOUNDUP_ONBOARDING_BUILDER_SKILL_PHASE1` -- a WRE BUILD skill encoding the
   onboarding procedure done by hand here.
4. `FOUNDUP_REGISTRY_HOLOINDEX_BRIDGE_PHASE1` -- index the registry so new
   FoundUps are remembered by registry lookup.

## 10. Internal Sentinel Review

An independent adversarial critic (separate lane from the author) attacked the
overclaim surface by direct read at base 20c26b7d4: (a) full marketplace built --
REFUTED (only declarative contracts + scaffold; readiness false); (b) legal/import
correctness claimed -- REFUTED (deferred + raising; no claims encoded);
(c) real auction lookup implied -- REFUTED (DeferredAuctionLookupProvider raises;
AST shows no network); (d) token/bid/ownership confusion -- REFUTED (TokenUtilityRules
rejects bid/ownership/payment; token_status TOKEN_DEFERRED); (e) PFmall wiring
implied -- REFUTED (public_surface_status hidden; no UI files); (f) real execution
opened -- REFUTED (dry-run proof asserts sinks not-called; HERMES_DELEGATE_ENABLED
unset). Verdict: READY. No blocking findings. File scope is the GetK module + the
registry + one WRE proof test + this doc + ModLogs (Section 11 row FILE_SCOPE_EXACT).

## 11. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | GETK_FRAMED_AS_KEI_TRUCK_FIRST_FOUNDUP | YES | Sections 1-2; README; manifest description ("first vertical", category kei_truck). |
| 2 | ANY_ITEM_OUTCOME_NOT_IMPLEMENTED | YES | Contracts are item-agnostic but no marketplace built; readiness false (Section 5). |
| 3 | REGISTRY_ENTRY_ADDED | YES | `getk` entity in foundup_registry.json; passes schema test (46) + projector (42). |
| 4 | MANIFEST_VALIDATED | YES | `validate_manifest_file` ok; test_getk_manifest.py (11). |
| 5 | SOURCE_AUTHORITY_MONOREPO_POC_ONLY | YES | Dry-run proof asserts `source_authority == monorepo_poc`; no promotion (Section 6). |
| 6 | READINESS_FLAGS_FALSE | YES | manifest_ready/build_ready/autonomous_execution_ready all false; tested. |
| 7 | TOKEN_NOT_BID_OR_OWNERSHIP | YES | TokenUtilityRules rejects vehicle_bid/ownership/payment; token_status TOKEN_DEFERRED. |
| 8 | AUCTION_LOOKUP_DEFERRED | YES | DeferredAuctionLookupProvider raises; capture auction_lookup forced "deferred". |
| 9 | REGULATORY_CLAIMS_NOT_ENCODED | YES | regulatory_status forced "deferred"; deferred to GETK_IMPORT_REGULATORY_PROVIDER_AUDIT_PHASE1. |
| 10 | PF_MALL_UI_NOT_WIRED | YES | public_surface_status hidden; no UI/frontend file in scope. |
| 11 | AUTPOST_INTEGRATION_NOT_WIRED | YES | No AutoPost import or wiring; named only as a future consideration. |
| 12 | WRE_DRYRUN_PATH_TESTED_OR_GAP_REPORTED | YES | Tested and PASSED via the existing seam (Section 6); no gap. |
| 13 | NO_REAL_EXECUTION | YES | subprocess sinks + real delegate asserted not-called; SIMULATED only. |
| 14 | NO_NETWORK | YES | AST purity test on contracts; dry-run proof makes no network call. |
| 15 | NO_HERMES_DELEGATE_ENABLE | YES | HERMES_DELEGATE_ENABLED unset in the proof; no change to the flag. |
| 16 | NO_CABR_PAYOUT_DAO_READY | YES | cabr_ready/payout_ready false in receipt; no CABR/payout/DAO/MVP claim. |
| 17 | TESTS_NON_VACUOUS | YES | 29 new tests, each asserting concrete behaviour; cross-checks 88 pass. |
| 18 | FILE_SCOPE_EXACT | YES | Diff = GetK module files + registry entry + one WRE proof test + this doc + root ModLog. |

Declared 18 / Rows 18 / All YES.
