# GotJunk -> Mall: first public listing read slice

**Date:** 2026-10-12 JST. **Source authority:** `FOUNDUPS/Foundups-Agent` main
`4095ad9ee6042f4e9b5668bf4f6bf50c493c5964`. Handoff:
[PR #2116](https://github.com/FOUNDUPS/Foundups-Agent/pull/2116), unmerged
at `3950d45cfdf0edbaf0c80f3c4b28d5dd0db0f550`.
This file records a narrow source-level change, **not a live shared marketplace**.

## Verified service/data ownership (working vs target)

| Concern | Verified source | Current state | Owner/decision |
| --- | --- | --- | --- |
| Identity and route | `modules/foundups/gotjunk/foundup_manifest.json`; `modules/foundups/pfmall/shell_core.py` | `gotjunk_001`, route `/f/gotjunk_001` working as Mall manifest/route; **not an identity-provider login** | Mall owns FoundUp identity/route; preserve IDs and old links |
| Member identity | `public/member/INTERFACE.md` | Clerk invite/session for member Mall | Separate from GotJunk Firebase UID; no verified account-linking service |
| GotJunk writer identity | `modules/foundups/gotjunk/backend/security.py`; `frontend/services/firebaseAuth.ts` | Firebase bearer UID on legacy API writes; not interchangeable with Clerk identity | Shared backend identity mapping **missing** |
| GotJunk offline captures | `frontend/services/storage.ts` | localforage `got-junk-pwa` database / `captured_items` store | GotJunk owns local capture; do not rename to manifest `idb_gotjunk_001` without export/import |
| GotJunk remote items/media | `frontend/services/firestoreSync.ts`, `frontend/services/firebaseConfig.ts` | `gotjunk_items`, `gotjunk_blobs`, base64 and Firebase Storage URLs; legacy project `gen-lang-client-0061781628` | Legacy adapter only; shared publication, upload and media provider **not selected** |
| GotJunk authorization | `modules/foundups/gotjunk/firestore.rules` | Item and blob **reads are currently public in source rules**; server-side writes use UID checks | Raw legacy reads are **not safe** to index as approved public listings. Production rule deployment not proven |
| Mall discovery | `modules/foundups/pfmall/shell_core.py`, `api.py`, `http_api.py` | Working **FoundUp tile/catalog/route** reads; unauthenticated HTTP. New read-only listing projection in this PR | Mall owns discovery/search read model and bounded projections |
| Member search | `public/member/INTERFACE.md`, `public/member/js/mall-tile-field.js` | Creator filtering, **not a vetted item search service** | New item search is not connected to member UI |
| Browser search stub | `public/member/js/shell-bridge-interceptor.js` | Stub results possible when backend unregistered | Not an item-search authority; never claim stub success |
| GetK | PR [#802](https://github.com/FOUNDUPS/Foundups-Agent/pull/802), head `de63ab95aab0ca11247cf2620cb4bc559bbce16c`, `modules/foundups/getk/src/getk_contracts.py` | Unmerged declarative marketplace packets; no working Mall/backend/media service | Future consumer, **not** a current provider |
| Shop/GetK resale consumer | GitHub code/PR/branch searches on 2026-10-12 | No Shop implementation branch, module or named PR located in this repo search | External/unpublished Shop work **unverified**; do not assume contracts |
| Media delivery | `modules/foundups/docs/PFMALL_MEDIA_DELIVERY_CONTRACT.md`, root `firebase.json` | Static Hosting and video presentation, **not user-upload storage** | Provider and credential/ACL decisions still open |

### Implemented boundary

- `listing_discovery.py` is the **canonical Mall item-read projection**, restricted in this slice to `gotjunk_001`. It reads **separate server-owned publication approval evidence** joined to immutable source item/owner/FoundUp identity and requires a listed source item. The approval cannot be a flag from a browser or a writable raw capture record.
- `GET /pfmall/listings/search` takes only `q`, `category`, `limit`, and the fixed `foundup_id`. An owner-specific or other FoundUp request is denied (403). Only fixed public fields `foundup_id`, `source_item_id`, `source_collection`, `title`, `category`, `deep_link` are emitted. No coordinates, raw descriptions, messages, owner UIDs, blobs, media URLs or embedded credentials.
- A trusted `app.state.listing_evidence_provider` must be configured **by the server** to supply independent item + publication-approval evidence. There is deliberately **no production provider** in this slice. Missing, broken or malformed providers return **503**, not a successful empty response. Passing raw Firestore documents, claimed browser permissions or user-controlled approval fields is prohibited.
- Links preserve `/f/gotjunk_001/listings/{item_id}` as a Mall route path. **The existing shell only hands off this route**; resolving it to a legacy item-detail page is a separate interoperability gate. Old direct legacy URLs are not modified.
- There is no item upload, migration, search indexing, publication approval writer, account linking, cross-tenant private search, member JS wiring or deployment in this slice.

## Security and acceptance gates for provider wiring

Before any production listing can be exposed:

1. Select server-owned listing record + independent approval store; define reviewer/publisher authority and revocation, owner transfer and delete behavior. Re-check ACL, tenant, item, reviewer evidence **on each read**, not on browser filters or cached approval alone.
2. Resolve Clerk-to-Firebase principal mapping and invite scope (if needed for private features), using verified backend identity; `owner_id: 012` in a manifest is **not** a Firebase UID.
3. Narrow legacy Firestore/Storage access with tested rules and verified deployed configuration; classify all historical public reads/exposure. PR #2114 merged source hardening, but [production deployment failed](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/38089713689) before rules/frontend rollout because legacy Storage API was disabled and deploy identity could not enable it. **Do not enable that API solely to unblock migration.**
4. Validate default-deny, per-owner/per-FoundUp scoping, approval lifecycle, public copy moderation, privacy and signed URL expiry. Security tests here prove the projection logic with fake evidence; they **do not** prove the missing production provider or Firebase rule deployment.
5. Confirm Shop/GetK contracts and source head when their actual implementations become available. Route a tenant-neutral `ListingEvidenceProvider` for approved additional FoundUps only in a separate reviewed slice.

## Subsequent storage and data migration (NOT executed)

**Inventory & dry-run:** Enumerate counts and item IDs for `gotjunk_items`, `gotjunk_blobs`, actual Storage objects/URL lifetimes, messages/reservations, Firestore rules, bucket/project/IAM, and per-device IndexedDB exports. Separate private captures, listed inventory, historical deletes and orphans. Build a redacted signed dry-run manifest with source owner UID, `foundup_id`, item ID, bytes, content digests, ACL, publication state, target mapping, collisions and blocked cases. Zero writes.

**Provider decision:** Compare canonical Mall/shared item metadata ownership, storage project/provider, quotas, costs, upload content validation, media moderation, lifecycle and lawful retention. Prefer reusing a verified shared service; if absent implement once in the actual platform owner. No duplicate marketplace backend or unauthorized Firebase configuration changes.

**Idempotent copy:** Use a migration key `(source_system, foundup_id, source_item_id, digest)`. Stage encrypted media/records without public exposure; copy only after owner and tenant identity reconciliation; checksum source-vs-target, validate permissions and dry-run link redirects. Persist per-item checkpoint and retry/replay/duplicate semantics; never use silent destructive moves. Support interrupted streams and offline client replay with deduplication. Keep origin-bound `got-junk-pwa` export/import or authenticated handoff; another origin cannot read its IndexedDB.

**Canary/read parity:** Behind an explicit disabled-by-default switch, compare counts, hashes, public-vs-private visibility, old/new links, query/proximity and reservation semantics, cross-owner denials, and concurrent updates. Run 9 Firebase emulator and 7 backend authorization tests plus service/integration tests at exact SHA. Require independent review and deployment/rule verification.

**Rollback:** Retain old objects and rules for an approved window. Stop new projections, revert the routing/read switch, replay write deltas if authorized, preserve item and redirect mappings, and audit counts/hashes/ACLs after rollback. Delete old storage or revoke credentials only after separate signed cutover/retention approval.

## Validation scope / WSP

WSP 00/50/84/97/98: source-ref verification, micro API/filter pass, macro identity/route/storage pass, fail-closed alternative chosen over guessed Firebase/Shop provider. WSP 22: module docs and ModLog update. Verification must report exact tests/CI, not conflate code-only review with live deployment.
