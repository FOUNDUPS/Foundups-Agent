# RedDog Builder Packaging Source Assumption Audit - Phase 2C2a

**Date:** 2026-08-29
**Base commit:** `329788414ca35ba593dfef91db3f80ff875928b6`
**Scope:** persistent inert source generation from the exact Phase 2C1 wheel
**Verdict:** GO for Phase 2C2a only; NO-GO for combined dependency composition

## Decision boundary

Phase 2C2a may preserve the exact reviewed wheel byte image and its exact
strictly admitted members in a content-addressed inert source generation. It
may prove source extraction, materialization, no-replace publication, reuse,
and complete wheel-to-tree byte equality.

It may not install or import that tree, launch a child, authenticate an
upstream publisher, compose a dependency runtime, alter the Holo owner or
route, or promote exact runtime closure, activation, A-grade, or retrieval RSI.
Those properties do not follow from source persistence.

## WSP_00 / WSP_15 / WSP_97 grounding

- WSP_00 detector-backed awakening passed at coherence `0.759` before code.
- The governed Holo query was `CURRENT` at the exact base commit, with no gap,
  no reindex, first-attempt retrieval, and generation
  `sha256:d108075504550c62ff83460f5ec5dab1aeba81793341a9a777b53e7f9f1d8389`.
- Retrieval ordering correctly surfaced the Phase 2C1 audit, wheel admission,
  strict archive/distribution code, and generic dependency materializer. It did
  not directly return the exact publication/quarantine test surfaces, so module
  docs and repository-local exact search were used as must-include reranking.
- No existing packaging-source materializer was found. The generic dependency
  materializer was found and explicitly reserved for Phase 2C2b reuse.
- The canonical WSP_15 receipt is 20/20, P0, ULTRA:
  `sha256:96381ff550ecfa496df2f464625208943f7737164eac41a807d054f292f91f15`.

## Rejected combined transaction

Independent architecture and test/scale reviews both rejected an atomic
"source plus dependency runtime" Phase 2C2 transaction.

The reasons are structural:

1. Phase 2C1 intentionally discarded public raw payload authority after
   admission. Reopening the wheel pathname would recreate the TOCTOU defect.
2. The existing dependency materializer already owns generic tree planning,
   copy, no-replace publication, quarantine, and reuse. Reimplementing it would
   duplicate a proven LEGO block.
3. Two stores have separate locks and publication transitions. The current
   contracts cannot truthfully claim cross-store atomicity or rollback.
4. A dependency failure must not delete a valid wheel-bound source generation.

The work is therefore split:

- **2C2a:** exact wheel-bound inert source generation.
- **2C2b:** source S1 -> dependency materialization -> source S2 -> equality and
  tree-digest binding, with no nested locks or cross-store atomicity claim.

## Retained-source capability

The Phase 2C1 module now has one private retained capability. It contains the
exact descriptor-read wheel bytes, immutable parsed members, and private byte
proof while retaining the original parent and file handles. The capability is
not exported in `__all__` and never appears in the public admission or source
binding.

Source materialization performs:

1. strict byte proof from the held original source;
2. exact in-memory member write to isolated staging;
3. canonical inventory/descriptor publication;
4. two consecutive full unpublished wheel-to-tree passes, with every admitted
   child retained across pass two and terminal handle/topology reproof;
5. original source-handle reproof;
6. atomic no-replace generation publication;
7. two consecutive full published wheel-to-tree passes under the same retained
   terminal proof boundary;
8. final original source-handle reproof; and
9. an unconditional scope-exit original-source reproof.

No pathname reopen is used to recover source bytes.

## Persisted proof and generation identity

Each generation contains exactly:

- `wheel/packaging-26.0-py3-none-any.whl` with the reviewed bytes;
- `site-packages/` with exactly the admitted member bytes and directory tree;
- one canonical source inventory;
- one canonical source descriptor; and
- one empty private-JSON publication-orphan directory.

The generation ID is domain-separated and binds:

- fixed wheel filename, size, and SHA-256;
- central-directory and member-set digests;
- METADATA, WHEEL, RECORD, and owned-files digests;
- exact dependency-tree digest;
- member and directory counts; and
- expanded byte count.

Consequently, two wheel encodings with an identical extracted tree do not
share a source generation identity.

The verifier reparses the persisted wheel and compares every extracted member
byte-for-byte. It also independently plans the extracted tree through the
existing dependency-runtime planner and requires its tree digest/counts to
equal the source descriptor. Public verification independently requires the
fixed reviewed wheel bytes and treats persisted lease booleans as
non-authoritative. Durable reproof returns both lease claims false. Only the
live public materializer returns current-verification authority, and it returns
publication authority only for a generation that call actually publishes;
reuse cannot inherit the claim. Pass two holds bounded raw handles for every admitted child file and
directory. Exit reproves those handles and complete live topology, denying
admitted-file tail mutation and rejecting a tail-added path before success.
The released result does not prove persistent destination write denial, an
atomic snapshot, or post-return immutability.

## Windows write and publication model

- All destination files use create-new retained file leases.
- Directory leases scale with current path depth, not total member count.
- Exact path spelling, directory identity, regular single-link files, and
  unnamed data streams are rechecked.
- Valid extended-length paths use the existing Windows path primitives.
- Staging is process-owned and identity-bound.
- Generation publication is atomic and no-replace.
- The source store is restricted to O:/E:, and valid-payload bounds plus the
  staging token are validated before store creation.
- A valid unowned winner is verified and reused; a corrupt unowned winner fails
  and is never overwritten or quarantined.
- Owned failed staging or a newly published owned generation is moved to
  no-delete quarantine. Quarantine failure is explicit and retains the primary
  failure as its exception cause.

## Durable falsification evidence

Authentic pre-implementation collection failed with `ModuleNotFoundError` for
the absent source-contract module. That ordering is present in the execution
transcript; Git cannot independently prove it.

Focused tests cover:

- wheel-vs-tree generation identity;
- exact raw wheel and extracted member bytes;
- truthful extraction/materialization and exhaustive operational nonclaims;
- private byte-seam absence of live pin/lease authority;
- unsigned descriptor pin/lease laundering rejection on durable proof and reuse;
- exact reuse without writer/publisher calls;
- descriptor/inventory/wheel/member mutation and duplicate keys;
- extra files and empty directories;
- wheel/member ADS, hardlinks, reparse classification, and case aliases;
- pre- and post-publication corruption;
- valid and corrupt no-replace winners;
- same-store two-thread convergence;
- source mutation denial during contracts and after publication;
- C: store, valid-payload limit, and token rejection before store mutation;
- store/repository overlap rejection;
- quarantine failure cause preservation; and
- source-write denial during target proofs and unconditional scope-exit reproof;
- inter-pass descriptor/inventory/wheel/member mutation; and
- tail descriptor/inventory/wheel/member mutation under retained handles;
- tail extra-file injection rejected by terminal complete-topology proof; and
- 105 sibling members with peak handles bounded by depth.

The exact O: reviewed wheel passed one publication and 200 full reuses in
105.09 seconds. Durable binding fields and descriptor bytes were identical;
the first result alone truthfully carried publication-time lease authority,
while every call carried current-verification authority. Exactly one source
generation remained, no dependency runtime appeared, process handle and RSS
deltas stayed within fixed gates, and the original wheel SHA was unchanged.
This is local repeatability/resource evidence, not throughput or horizontal
scale evidence.

## Explicit nonclaims

Phase 2C2a does not prove or perform:

- official/authenticated upstream provenance;
- signature or transparency-log verification;
- network access, download, or installation;
- import or child execution authority;
- builder runtime authentication;
- pre-import loader, native/DLL, or subprocess closure;
- exact runtime closure or deterministic effects;
- empirical write denial;
- destination atomic-snapshot or post-return immutability assurance;
- candidate/owner/route/query/VSIX activation;
- HoloIndex A-grade; or
- retrieval-quality RSI.

## Remaining Phase 2C2b contract

The next transaction may only coordinate existing verified blocks:

`source S1 -> release source lock -> materialize_dependency_runtime -> source S2 -> require S1 == S2 -> require source tree digest == dependency generation ID`.

It must preserve successful source state if dependency materialization fails,
must not nest source/dependency store locks, and must not claim cross-store
atomicity. Every execution, loader, signing, write-denial, activation, A-grade,
and RSI property remains outside Phase 2C2b.
