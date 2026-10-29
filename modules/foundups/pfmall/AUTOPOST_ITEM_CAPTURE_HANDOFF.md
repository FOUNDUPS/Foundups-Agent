# AutoPost item capture into Play FoundUps Mall

**Updated:** 2026-10-23 (Japan date)  
**Status:** Canonical ownership/private-default decision; item grouping and private transfer are **SPECIFIED_NOT_IMPLEMENTED**.  
**Consumer:** 0102 continuing Shop, GetK, AutoPost or shared Mall work.  
**Owners:** external AutoPost for capture; existing p.fMALL services for admitted attachment and presentation; owning FoundUp for item/business state.  
**WSP references:** WSP 22, WSP 50, WSP 83, WSP 84, WSP 97.

## 1. Outcome and current decision

012's 2026-10-23 direction is to photograph clothing with AutoPost and assemble
those photos into item records usable within the existing Play FoundUps Mall.
Public-facing Shop distribution remains undecided. Capture therefore starts as
a **private local draft**. Taking a photo, selecting a category, signing a local
receipt or entering the Mall does not publish it or grant another person access.

Extend the existing camera, media repository, shared identity/listing/media
owners and Mall renderer. Do not create another camera, blob store, identity
database, marketplace backend or independent Shop website. Do not copy AutoPost
product code into `modules/foundups/autopost/`; its implementation remains in
[FOUNDUPS/autopost](https://github.com/FOUNDUPS/autopost).

One item may have many photographs. One capture batch may contain many items.
An item/lot is an opportunity instance beneath a FoundUp, not a new FoundUp for
each garment. See the [existing instance model](../docs/PFMALL_OPPORTUNITY_INSTANCE_MODEL.md).

## 2. Evidence and reuse map

Source baseline: Foundups-Agent `a048c24071e1a651b161025ba3342f14f3047280`;
AutoPost `3c0fc19d40e225ed7f826541a33c38293f9fe664`.

| Concern | Existing owner | Verified baseline / remaining gap |
|---|---|---|
| Photo capture and original bytes | AutoPost `useCaptureWorkflow.ts`, `captureMediaRepository.ts`, `indexedDbMediaStore.ts` | Implemented still capture and origin-local persistence, with explicit temporary fallback. No shared Mall transfer established. |
| Per-capture records and perception | AutoPost `PostRecord`, `CaptureEvent`, `CaptureDecision` | Existing capture provenance and local model invocation. Observations remain advisory; not authenticated ownership, garment appraisal or reviewed publication. |
| Multi-photo item grouping | AutoPost's existing capture/Preview composition | Type/specification in the existing capture module; selection controls, group persistence and runtime validation remain missing. |
| Private item attachment/read | Existing shared platform listing/media service ownership | Authenticated writer, media receipt and principal-scoped read adapter are missing. Extend this owner once, with domain adapters. |
| Browsing and detail | `public/member/js/mall-tile-field.js` and registered discovery adapters | Grouped rows, horizontal alternatives, vertical groups and restoration exist. Garment projection/private provider remain missing. |
| Public GotJunk reads | `listing_discovery.py`, `http_api.py`, optional Firestore provider | Public-only approval-joined projection. It is not a private ingest/search service. |

The [June capture audit](../../../docs/audits/architecture/AUTOPOST_REUSABLE_CAPTURE_ENGINE_AUDIT_PHASE1.md)
is historical for implementation status. Current AutoPost has still photos,
local persistence and real model calls; generic cloud delivery, private Shop
attachment and phone acceptance still require evidence. The registry's old
percentage/mock description must not be used as the current capture baseline.

GetK [PR #802](https://github.com/FOUNDUPS/Foundups-Agent/pull/802), head
`de63ab95aab0ca11247cf2620cb4bc559bbce16c`, was open/unmerged at this review.
Its capture/listing separation is useful, but `GetKListingPacket` defaults to
`public_browse`. **Do not reuse that default for private item drafts.** It does
not provide the missing upload, authenticated writer or commerce service.
No dedicated Shop module was located in the audited main tree. Earlier claimed
local Shop code/216 tests remain unverified; recover that checkpoint before
recreating its unique work if it becomes available.

## 3. Local draft contract in AutoPost

The companion type declaration belongs to existing
[`src/modules/capture/captureEvent.ts`](https://github.com/FOUNDUPS/autopost/blob/main/src/modules/capture/captureEvent.ts).
The [AutoPost layer map](https://github.com/FOUNDUPS/autopost/blob/main/docs/architecture/AUTOPOST_DAE_LAYER_MAP.md#private-item-draft-handoff)
owns its validation obligations. Type declarations do not implement grouping,
persistence, validation, upload, authentication or rendering.

| Type/field | Meaning |
|---|---|
| `AutoPostItemDraft.schemaVersion` | `autopost.item-draft.v1` |
| `batchId` / `itemId` | Stable local batch and item identifiers; a batch can hold multiple item drafts. Neither is trusted ownership. |
| `revision` | Starts at 1; grouping changes advance it. Runtime enforcement is pending. |
| `state` | Literal `private-local-draft`; a local declaration, not server access control. |
| `photos` | Ordered `ItemCapturePhotoRef` records; at least one original photo. |
| `captureId` | Existing `PostRecord.id` / `MediaAsset.captureId`, **not** the separate `CaptureEvent.id`. |
| `mediaAssetId` | Reference to existing original photo bytes in AutoPost's `MediaStore`. |
| `role` | `front`, `back`, `brand-label`, `size-label`, `care-label`, `measurement`, `defect`, `detail` or `other`. |
| `position` | Contiguous zero-based order within the item. |

Runtime validation must reject missing originals, wrong media types/variants,
mismatched capture IDs, duplicate references and reused original assets within
an item. Preserve capture timestamps/digests and advisory observations through
the existing source records. Selection and edits must not delete originals or
let a late model response silently regroup the operator's items. Independent
garment photos are not recording segments and must not be put into video
concatenation paths.

IDs in one origin's IndexedDB do not make bytes readable in another origin.
Exporting a draft JSON object is not a media transfer. The draft contains no
public URL, credentials, server principal, tenant authority or publication
approval. Clothing fields/price estimates remain reviewable suggestions until
the owning item workflow accepts them against evidence.

## 4. Missing authenticated shared adapter

These are logical obligations, **not newly callable endpoints**:

1. Authenticate the operator at the existing shared platform boundary and
   resolve permitted FoundUp/item scope server-side. Clerk/Firebase/local
   author identities are not interchangeable without a verified mapping.
2. Validate the original media and upload through one shared media owner.
   Record verified remote object identity, digest, size/type and ownership;
   keep failed/partial uploads distinct from acknowledged objects.
3. Attach those verified media references to a private item under the trusted
   principal/FoundUp. Bind client draft identifiers to this server scope;
   reject reuse with a different principal, item or incompatible revision.
4. Make retry idempotent for the same scoped draft/revision. Preserve conflicts,
   interrupted transfers and stale revisions instead of returning mock success.
5. Return an acknowledgment only after the private item and required media are
   durable. Mall reads an authorized projection, including only allowed photo
   derivatives and item fields. Revocation must also stop future media access.

Service/provider, project, identity mapping, upload limits, derivative policy,
retention and deployment remain implementation decisions with acceptance gates.
Extend the existing platform's service lineage; do not create a Shop-only
parallel database. The owning FoundUp retains domain state while shared
services supply identity, media attachment and permitted discovery.

**Do not route private capture through these existing public surfaces:**

- `GET /pfmall/listings/search`: unauthenticated, fixed to approved-public
  `gotjunk_001`; owner/cross-FoundUp requests remain denied and missing provider
  remains unavailable. Adding `owner_uid` or `private=true` cannot secure it.
- Static `mall-catalog.json`, `mall-video-catalog.json`, `public/media/` or
  `public/member/media/`. A member-named path or UI gate is not asset ACLs;
  the [static media contract](../docs/PFMALL_MEDIA_DELIVERY_CONTRACT.md) uses
  public caching. Unlisted YouTube is not a private clothing-photo transport.

Public publication, vendor invitations, pricing, ownership transfer and payment
are later decisions. None is a prerequisite for privately reviewing captures.

## 5. Mall presentation and truthful states

Preserve the shared field/detail plane and existing video/property experiences.
A future garment adapter supplies permitted item records, style groups and
filter state; horizontal tracks show real alternatives and vertical movement
changes groups. A unique secondhand garment is not an invented set of stocked
size/color variants.

RedDog text, preset buttons and future speech must update the same domain-owned
filters. Grouped discovery intentionally refuses the global `searchCatalog()`
command. The bounded request-prefix/alias repair in this slice only improves
loaded-metadata matching; semantic sizing/budget filters and microphone/STT
remain missing.

| Observation | Permitted description |
|---|---|
| Original saved locally | Local capture, with its actual durable/temporary state |
| Photos selected into a group | Private local draft, once grouping is implemented |
| Transfer queued/partial/failed | Attachment pending/partial/failed; originals retained |
| Trusted service acknowledgment received | Attached privately to Mall, within the acknowledged scope/revision |
| Public approval absent | Private; no public listing or public image URL |

## 6. Ordered implementation and acceptance

| Slice | Owner and outcome | Promotion evidence |
|---|---|---|
| C0 — current | Shared contract, AutoPost types, corrected status, linked roadmaps/ModLogs/navigation | Exact-source review, document attachment/hash checks and existing Mall regression tests. This is not transfer completion. |
| C1 — next | AutoPost group/review controls and local draft persistence using existing media repository | Two garments with several photos each remain correctly grouped after reload; duplicate/missing assets, temporary storage, late inference and AI-disabled capture are handled truthfully. |
| C2 | Authenticated shared media upload and private item writer | Wrong-principal/tenant denial; validated remote bytes; retry dedupe; stale/conflicting revision and partial failure; no public exposure; durable acknowledgment. |
| C3 | Private garment projection through the shared Mall | Authorized viewer sees only permitted items/photos; another account is denied; navigation/restore and existing video/property behavior remain intact. |
| C4 — undecided | Public Shop or invited-vendor publication | Explicit visibility decision, independent authorization/review, revocation and media-cache proof. |
| C5 — later | Sourcing, quotes, reservations, delivery and settlement | Separate accepted transaction/fulfillment evidence; no mock payment confirmation. |

## 7. Retrieval and continuation

Start here from [README](README.md), [INTERFACE](INTERFACE.md),
[ROADMAP](ROADMAP.md), [ModLog](ModLog.md), the
[canonical index](../docs/FOUNDUPS_DOMAIN_CANONICAL_INDEX.md) or the
`NAVIGATION.py` keys `Shop clothing capture`, `AutoPost multiple item photos`
and `private Mall listing`. The bounded [doc_index.json](doc_index.json)
records attachment and integrity. It does not activate a Holo generation.

This session used exact GitHub source and direct lexical reads because no
admitted Holo/WRE runtime was available. Semantic freshness remains UNKNOWN.
WSP 00 canonical bootstrap lacked `torch`; documented formula fallback opened
its software gate with detector witness absent. Do not promote those results
to model execution, semantic-index freshness or deployed-service evidence.
Use the governed maintenance owner for any later Holo generation refresh.

Before the next change, re-read both repository heads, affected module/test
logs and this acceptance table. Preserve unrelated open GetK, Lick and receipt
work. The owning PRs record checks, squash merge and exact main readback.
