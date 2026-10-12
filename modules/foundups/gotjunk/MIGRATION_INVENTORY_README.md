# GotJunk -> Mall: offline metadata-only migration inventory

**Review stage:** dry-run / no cutover. **Source:** original GotJunk in
`modules/foundups/gotjunk`; Mall read projection under `pfmall`.
Handoff documentation is in **unmerged PR #2116**.

## Authority and limitations

This is a deterministic analysis of **operator-supplied metadata-only exports**,
not a crawler or a data migration. It makes **zero writes**, uses **no**
Firebase service/account, never starts GotJunk or Mall and never touches an
actual customer record. The report excludes source identifiers, owner UIDs,
exact locations, text descriptions, media URLs and private content. Input
identifiers are used in memory to build an idempotency-set digest; the only
reportable identity is `gotjunk_001`.

IndexedDB is bound to the browser origin: the future authenticated exporter
must run inside the **legacy GotJunk origin** or explicitly provide a safe
export/import bridge. A new Mall origin cannot read `got-junk-pwa` or
`captured_items`. These names remain unchanged. This script cannot inventory
existing devices or production Firestore/Storage without separately provided
authorized exports.

## Bounded input schema

JSON list, **at most 2,000 rows and 1 MiB** per invocation:

```json
[
  {
    "source_system": "gotjunk_firestore",
    "foundup_id": "gotjunk_001",
    "source_item_id": "example-item",
    "owner_uid": "example-owner",
    "content_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "status": "listed"
  }
]
```

The source system is one of `gotjunk_firestore`, `gotjunk_storage`,
`gotjunk_indexeddb`. **Never place blobs, media URLs, signed URLs, messages,
GPS coordinates, credentials, or exported PII in this input.** The source hash
must be produced by a separately verified trusted exporter; the planner
treats the hash as an *unverified assertion*. Owner UID reconciliation
(Clerk-to-Firebase) is **not implemented**.

Local, offline-only invocation:

```bash
python -m modules.foundups.gotjunk.src.migration_inventory --dry-run < redacted-metadata.json
```

The report contains unique candidate count, blocked count/reasons, duplicate
count, status counts, and a stable SHA-256 digest of opaque idempotency keys.
The planner blocks all versions of a source-system/item ID on owner, state or
digest conflicts. Exit 0 = no blocked metadata, 2 = invalid invocation/export,
3 = records blocked. **Exit 0 never means approved to migrate or deploy.**
No report contains the raw per-item mapping needed for rollback; a production
migrator must maintain that encrypted mapping separately under operator/IAM
control.

## Preconditions for any real migration

1. Inventory the actual live Firestore collections, Storage bucket, client
   IndexedDB origins, ownership, signed URLs and rules with separate authorized
   exports; reconcile all counts against source, including orphans and private
   captures. Avoid using this planner to silently skip missing records.
2. Choose a single shared listing/media authority, least-privilege IAM,
   server-only publication/review writer and permissions policy. Verify client
   and admin rules in emulators *and* their deployed production versions.
3. Establish signed, encrypted mapping from `gotjunk_001` source IDs/owners
   and content hashes to target IDs. Preserve original links and source IDs.
   Do not self-approve visibility from `listed` or seller-updatable flags.
4. Implement bounded, resumable, idempotent **copy** with per-item receipts,
   encrypted checkpoints and checksum validation; replay interrupted and
   offline cases without duplicate publication. Test owner conflicts and
   concurrent reservations/messages before any cutover.
5. Canary behind a disabled-by-default rollout switch; independently compare
   old/new counts, digest, owner ACLs, public/private exposure, deep links and
   media expiration. A provider error must return unavailable, not success.
6. **Rollback plan:** revert the read switch and routes, preserve source data
   and production rules, replay authorized deltas backwards where necessary,
   and reverify counts/hashes/ACLs. Never delete/move the legacy store until a
   separately approved retention and cutover plan completes.

## Test & operational truth

`python -m pytest modules/foundups/gotjunk/tests/test_migration_inventory.py -q`
uses only local synthetic metadata. CI registers the test in
`WSP_knowledge/WSP_Test_Registry.json`. No source/system deployment,
production data reconciliation, media safety audit or rollback drill has run.
