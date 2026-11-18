# GotJunk migration to Play FoundUps Mall

Date: 2026-10-12 (JST). Status: approved architectural direction; migration NOT implemented.
Source reviewed: main `4095ad9ee6042f4e9b5668bf4f6bf50c493c5964`.

## Operator decision

GotJunk predates Play FoundUps. Rework it as a FoundUp using the shared
Play FoundUps / p.fMALL architecture, alongside Shop and GetK. The Mall is
the canonical internal discovery/search surface. Do not build a second Mall,
parallel global index, or separate platform identity for GotJunk. Retain its
capture, reuse/sale, proximity and item-management behavior as domain features.

This document is the bounded implementation handoff, not authorization to
silently replace production, migrate customer records, delete legacy storage,
enable cloud services, or start OpenClaw/main.py services.

## Verified baseline and gaps

| Concern | Current source evidence | Migration consequence |
| --- | --- | --- |
| Mall membership | `foundup_manifest.json`: `gotjunk_001`, `/f/gotjunk_001`, external Cloud Run entry, conditional readiness | Preserve stable identity and old links; embedding alone is not service convergence |
| Local captures | `frontend/services/storage.ts`: localforage database `got-junk-pwa`, store `captured_items` | Preserve offline captures; manifest namespace `idb_gotjunk_001` does not rename or isolate this existing database |
| Remote data/media | `frontend/services/firestoreSync.ts`: `gotjunk_items`, `gotjunk_blobs`, inline small blobs and Firebase Storage uploads; `firebaseConfig.ts` binds project `gen-lang-client-0061781628` | Inventory actual objects, owners, URLs and collections before selecting a shared provider; comments contain older names, so inspect executable paths |
| Mall read model | `../pfmall/api.py`, `shell_core.py`, `INTERFACE.md`: manifest/catalog/route reads | Reuse existing ownership; this is not a listing-write or media-upload service |
| Mall search | `public/member/INTERFACE.md` (repository root), `public/member/js/mall-tile-field.js`: catalog creator filtering; `shell-bridge-interceptor.js`: registered search seam/stub fallback | Item search needs a real permission-aware provider; do not present a stub or creator filter as complete marketplace search |
| Mall media | `../docs/PFMALL_MEDIA_DELIVERY_CONTRACT.md`, root `firebase.json`: static media paths and YouTube thumbnails/embeds | Firebase Hosting is distinct from Firebase Storage; static catalog delivery does not establish a shared user-upload backend |
| Platform security | `../docs/PFMALL_DATA_ISOLATION_MODEL.md`: several isolation/encryption/sentinel features explicitly specified, not implemented | Namespace labels, routes and browser messages are not authorization; verify actual server enforcement |
| GetK | Open PR #802 at `de63ab95aab0ca11247cf2620cb4bc559bbce16c`: manifest and declarative PoC contracts; README explicitly excludes working marketplace, Mall wiring and AutoPost | Reuse verified contracts after compatibility review; do not treat this unmerged scaffold as a deployed storage service |
| Shop | No Shop module located in this main-tree review | Locate the current owning branch/PR before implementation; operator intent does not prove deployed infrastructure |

The Mall and GotJunk documentation includes stale deployment statements and
aspirational capabilities. Code/configuration and exact deployment receipts
take precedence. Production data, bucket contents, IAM and current live write
exposure were not inventoried in this documentation task.

## Firebase decision

Security PR #2114 merged source corrections. Production run
https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/38089713689 failed before
rules/frontend rollout because `firebasestorage.googleapis.com` was disabled
and the deployment identity could not enable it. Those production protections
must not be marked applied.

Do not enable the legacy API merely to make that deployment green. First prove
which storage provider the shared architecture will own. If shared uploads use
Firebase Storage, the selected project still needs that API, least-privilege
IAM, bucket configuration and tested authorization rules. A different approved
provider could remove the legacy dependency, but a Mall route cannot do so.
Keep existing security fixes and fail-closed deployment gates. Migration is not
a reason to leave a verified exploitable legacy write path exposed: assess live
reachability and use a separately authorized temporary mitigation if required.

## Agent execution brief

You own a staged GotJunk convergence, not a standalone marketplace rewrite.
Follow repository AGENTS.md, WSP 50/84/97/98 and the current Mall contracts.
Re-resolve main, Shop and GetK exact heads; read their owners before edits.
Record source SHA, implemented/spec-only capabilities, deployment applicability,
and unresolved gates. Use separate worker/auditor roles where available.

1. Produce a source-backed dependency and data-ownership map. Locate Shop and
   GetK work, existing listing/media/search/auth owners, consumers and deploys.
   Decide the canonical listing model, storage provider/project, authenticated
   identity mapping, public/private fields, retention and migration rollback.
   If a shared service does not exist, document the gap and implement one small
   shared capability in its canonical owner rather than copying GotJunk APIs.
2. First code slice: wire one permission-filtered, read-only GotJunk listing
   projection into the existing Mall discovery/search contract. Preserve
   `gotjunk_001`, `foundup_id`, source item ID, provenance and deep links. GotJunk
   can submit category/proximity filters; the Mall owns internal discovery.
   Never index private captures, messages, exact private locations or tokenized
   media URLs into a public catalog. Server policy decides visibility.
3. Add shared media/listing adapters behind an explicit rollout switch. Verify
   identity at the backend; enforce owner/tenant ACLs, content/size limits,
   quotas, moderation and reservation concurrency. Keep GotJunk business logic
   separate from shared infrastructure and preserve offline capture behavior.
4. Design an idempotent, resumable migration with dry-run manifests, ownership
   mapping, counts, content digests and rollback. Browser-origin IndexedDB is
   not readable from another origin: preserve the old app's export/import or
   authenticated handoff. Do not just rename `got-junk-pwa` and strand captures.
   Preserve old item links and media access subject to current permissions.
5. Independently verify each slice before the next. Required cases: Mall
   discovery/deep links, cross-owner and cross-FoundUp denial, anonymous private
   search denial, unpublished/private media exclusion, malformed uploads,
   concurrent reservations/messages, offline retry/deduplication, interrupted
   migration replay and rollback, and compatibility with Shop/GetK consumers.
   Run the existing 9 Firebase emulator and 7 API security tests while those
   adapters remain in use; report failures/skips as incomplete coverage.
6. Release only after exact-head checks, an approved data cutover, and verified
   deployed rules/provider configuration. Remove legacy adapters, deployment
   dependencies and storage only after migration completeness, consumer
   inventory and rollback retention are proven. Never delete user data merely
   because the new catalog renders. Update README/INTERFACE/ROADMAP/ModLog.

Acceptance: one Mall discovery/search surface with permission-aware listing
results; reusable platform service ownership; preserved GotJunk identity and
data; audited migrations and production receipts. A new iframe or manifest
entry alone does not meet acceptance. No clean/security-complete claim from
partial tests or undeployed source.

## Review evidence

This change is documentation only. Existing runtime/security source is retained.
Lexical Holo retrieval returned UNKNOWN freshness with an index gap; direct
source reads resolved noisy results and stale documentation. No semantic
freshness claim is made. WSP00 used the documented torch-free formula fallback;
no detector measurement is claimed. No production settings or data changed.
