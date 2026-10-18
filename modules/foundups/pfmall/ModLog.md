## 2026-10-17 — Mobile creator studio research and machine outcome

## 2026-10-18 — Shared responsive rows and RedDog catalog search

Extend existing Mall renderer rather than duplicate tenant apps. Default category
tracks adapt card width to the viewport and preserve independent horizontal
positions; vertical browsing has no fixed row cap. Keep explicit legacy grid,
channel pinch/queue behavior and canonical entry. Repair drag-on-card exclusion,
reobserve rerenders and clear stale media indexes on scope/projection changes.
RedDog text and dispatcher share bounded metadata search; categories come from
catalog data. Service-worker shell version advanced for updated assets.

WSP 00: canonical bootstrap attempted; torch absent. Documented tracker fallback
opened gate; detector witness absent. WSP 50/87: exact-head lexical bundle read,
freshness UNKNOWN/index gap true; noisy retrieval supplemented by direct owner
reads. No semantic freshness or reindex claimed. WSP 84/97: shared-owner reuse;
voice, personalized mapping, payments and live ingestion remain future work.
Validation details are recorded in public/member/tests/TestModLog.md.


**WSP:** 00/10/15/22/50/57/83/84/97. **Agent:** 0102.
**Source baseline:** `407292aa754a88143796163581b67ca6679eac29`.
**Scope:** Documentation only; no native, API, catalog or deployment mutation.

- Added the [mobile studio contract](../docs/mobile_studio/PFMALL_MOBILE_STUDIO_CONTRACT.md),
  [YouTube API register](../docs/mobile_studio/PFMALL_CREATOR_LIVE_API_CONSTRAINTS.md)
  and [machine outcome](../docs/mobile_studio/mobile_studio_outcome.v1.json).
  They record current reuse, pain, proposed ownership, obstacles, staged delivery
  and AC01–AC09 without granting executable admission.
- Updated owner README/INTERFACE/ROADMAP, the FoundUps domain roadmap and the
  member roadmap's current-state pointer. Kept existing active runtime PRs and
  historical roadmap evidence separate from this main baseline.
- Added a bounded [doc_index.json](../docs/mobile_studio/doc_index.json) and
  [WSP 97 receipt](../docs/mobile_studio/wsp97_execution_receipt.json) for 0102
  retrieval and structural/repository validation. No Holo generation activation
  or current semantic-index claim is made.
- Verification scope: JSON and document attachment/hash checks, relative source
  references, WSP 97 receipt validation, diff review and PR checks. Actual account,
  provider, mobile/device, streaming and production checks were not performed;
  their required evidence remains explicit in the handoff and PR.

## 2026-10-12 — GotJunk privileged publication-evidence adapter (second gated slice)

**WSP:** 00/22/50/84/97/98. **Parent:** implementation PR #2117
(commit `58321915fa8c4ee5b02371d0e263a5f8711f5cf8`).
This is a **stacked review**, not a production cutover.

- Added server-injected read-only `FirestoreGotJunkPublicationProvider`,
  joining independently controlled `gotjunk_public_approvals` to legacy
  `gotjunk_items` by FoundUp, exact item ID, owner, reviewer, revision and
  listed status. Invalid records are omitted; provider failures propagate as
  unavailable without partial results. Privileged Firestore reads validate ID
  shape before issuing document requests.
- Extended focused fake-Firestore security tests (no network/credentials).
  Kept provider disabled until independently authorized reviewer, server IAM,
  source rule access and separate deployment checks exist.
- No Firebase API enablement, migration, identity account linking,
  publication writer, data changes or production exposure.

## 2026-10-12 — GotJunk public-only listing discovery (first gated slice)

**WSP:** 00, 22, 50, 84, 97, 98. **Base:** main
`4095ad9ee6042f4e9b5668bf4f6bf50c493c5964`.
**Handoff:** unmerged PR #2116 at
`3950d45cfdf0edbaf0c80f3c4b28d5dd0db0f550`.

- Added a tenant/owner/approval-joined, allowlisted GotJunk public listing
  projection in Mall's canonical read service and a read-only HTTP search route.
  Cross-tenant/owner parameter requests reject with 403; missing/failing
  trusted provider returns 503, not a false successful catalog.
- Added focused security/availability regression fixtures (no live data).
  Production publication approval writer, principal mapping, provider, UI,
  uploads and cutover **remain absent**.
- Recorded exact-source owners, Shop/GetK branch evidence, legacy Firebase
  read-rule risk, storage migration dry-run/idempotency/rollback gates in
  `GOTJUNK_LISTING_READ_SLICE.md`. Does not change legacy data/rules,
  security fixes, identity or Cloud Run deployment.
- CI/test and deployment evidence must be attached to implementation PR;
  no runtime or production success is asserted by this log.

# p.fMALL ModLog

## 2026-08-23 — Tier-0 contract and RedDog authority alignment

**WSP Protocol**: WSP 15, WSP 22, WSP 49, WSP 50, WSP 84, WSP 97
**Phase**: Documentation hardening / retrieval repair
**Agent**: 0102

### Changes

- Added the missing root `README.md` and `INTERFACE.md` required by the generic
  Holo Tier-0 retrieval contract.
- Reconciled PFMall's current shell, catalog, HTTP, member UI, RedDog,
  OpenClaw, and Hermes boundaries against source and canonical PFMall docs.
- Added a bounded roadmap and test documentation without claiming the legacy
  flat package is WSP 49 compliant.
- Added a real-repository regression proving the registered PFMall module has
  both required Tier-0 documents.
- Differentially reproduced the same 19 failing PFMall node IDs and 588 passes
  at the original pre-rebase `f06ca1f` baseline. The inherited catalog/UI/media
  drift remains a separately scoped repair; it was neither hidden nor expanded
  here. The exact post-#1538 Git parent is `69b7f073`.

### Impact

- Exact PFMall queries can fail closed on genuine future documentation loss
  without permanently failing because the module never supplied its contracts.
- The browser-local concierge and control dispatcher are no longer ambiguous:
  neither is resident RedDog, OpenClaw authority, nor Hermes execution.
- No runtime behavior, route, Holo enforcement rule, active replica, or model
  binding changed in this slice.
- The new Tier-0 regression passes independently; the candidate adds no
  PFMall-suite failure relative to the original pre-rebase baseline.

### WSP compliance

- WSP 15 canonical RedDog allocation receipt:
  `sha256:8d21ec361878bdad15f8c024c8a0af4f0c0a9c488989a22519f65400e8bd45cb`
  (`20/P0/ULTRA`, accepted).
- WSP 97 selected the smallest valid layer: satisfy the shared contract and
  retain strict fail-closed retrieval; no special case or downgrade was added.
- Remaining WSP 49/60/12 structure debt is explicit in `ROADMAP.md` and was not
  mixed into this documentation transaction.
