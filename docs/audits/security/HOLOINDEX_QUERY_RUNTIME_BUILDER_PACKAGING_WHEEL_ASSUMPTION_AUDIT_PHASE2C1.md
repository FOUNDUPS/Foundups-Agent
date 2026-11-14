# HoloIndex Query Runtime Builder Packaging Wheel Assumption Audit - Phase 2C1

Date: 2026-08-29 JST
Authority base: `f11a49b8b35a971c467f33fc06827fbcb03cf2a3`
WSP allocation: 20/20, P0, ULTRA
Scope: inert admission only; no extraction, publication, import, execution, or activation

## Decision

Proceed with one bounded layer: admit exactly the Git-reviewed
`packaging-26.0-py3-none-any.whl` through a held Windows directory and file
identity, then parse and cross-check its ZIP, distribution metadata, and RECORD
bytes without reopening the source path. Persistent source generation and
dependency-runtime materialization remain a separate Phase 2C2 transaction.

The reviewed pin is:

- filename: `packaging-26.0-py3-none-any.whl`
- size: 74,366 bytes
- SHA-256: `b36f1fef9334a5588b4166f8bcd26a14e521f2b55e6b9de3aaa80d3ff7a37529`
- expected wheel tag: `py3-none-any`

The pin was compared with the PyPI JSON file record and the corresponding
`files.pythonhosted.org` payload during research. That comparison is not a
signature, transparency-log proof, or authenticated durable upstream
provenance. Production claims only a repository-reviewed exact pin match.

## WSP 50 / governed retrieval evidence

The generation-bound owner query completed at the authority base with
`ok=true`, `freshness=CURRENT`, `index_gap_detected=false`, and
`no_holoindex_reindex_performed=true`. Generation
`sha256:19d1119ae2d22f3c2ac3b5622703f0286459957976fc36f282b298574e99220d`
ranked the existing Windows acceptance leases, packaging ownership proof, and
model-copy admission code among the first three relevant implementations.

Retrieval quality was sufficient but imperfect: ordering correctly surfaced
the held-handle and packaging contracts; one model-copy result was analogous
rather than wheel-specific; no existing strict raw wheel parser or reviewed-pin
admission wrapper was found. The exact module documentation, interface,
roadmap, tests documentation, ModLogs, dependency-runtime contract, current
packaging authority, and Windows lease primitives were inspected before edits.
No Holo maintenance or reindex was performed by the query.

## Security assumptions that must be falsified

1. A path hash alone is not identity. The source parent and file must remain
   leased from before the first byte read through parsing and final reproof.
2. `zipfile.ZipFile(path)` would reopen a mutable pathname and is forbidden in
   production admission. Parsing must consume the single bounded byte image
   read from a descriptor duplicated from the retained source lease.
3. ZIP central-directory claims are untrusted. EOCD, central and local headers,
   offsets, sizes, names, methods, flags, CRCs, and raw-deflate consumption must
   agree exactly; gaps, overlaps, prefixes, trailers, ZIP64, multidisk,
   encryption, descriptors, extras, and comments must reject.
4. Archive paths are Windows extraction identities. Absolute/device/UNC/drive,
   backslash, colon/ADS, dot segments, control bytes, trailing dot/space,
   reserved names, case aliases, and file-prefix collisions must reject even
   though this phase never extracts.
5. Expansion is attacker-controlled. Raw size, members, path bytes, per-member
   bytes, aggregate expanded bytes, and compression ratio require hard limits.
6. Distribution identity is not implied by the filename. One exact METADATA,
   WHEEL, and RECORD must bind `packaging==26.0`, purelib, `py3-none-any`, the
   exact member set, canonical unpadded SHA-256 hashes and canonical sizes.
7. A valid admitted wheel remains inert evidence. It grants no official
   provenance, signature, extraction, publication, loader/import authority,
   child execution, deterministic-effects, write-denial, activation, A-grade,
   or retrieval-RSI claim.

## WSP 62 boundary

The layer is split into a shared distribution contract, a strict bounded raw
wheel parser, and a Windows held-descriptor reviewed-pin wrapper. Each source
module must remain below the 500-line extraction signal, functions should stay
at or below 50 lines unless a documented cohesive parser boundary requires a
smaller helper extraction, and the existing packaging authority must reuse the
shared distribution semantics rather than grow a second implementation.

## Independent falsification disposition

The first green implementation was not accepted. Independent WSP_00/WSP_97
review returned NO-GO and reproduced two correctness defects:

1. Windows-illegal `<`, `>`, `"`, `|`, `?`, and `*` characters were accepted in
   archive components. The parser now rejects all six, and each spelling is a
   durable parameterized test.
2. The synthetic byte seam returned the public admission dataclass with
   `reviewed_pin_match=true` and `source_lease_held_during_admission=true`, even
   though it proved neither. Byte parsing now returns a separate private proof
   that has no such fields. Only the public fixed-pin path constructs an
   admission, after final retained-handle reproof.

The review also required explicit false fields for builder-runtime
authentication, pre-import loader authority, native-loader, subprocess and
exact-runtime closure, and network/download/installation activity. Those
fields are now present and exhaustively asserted false in the public-path test.
No finding was waived or downgraded.

The dedicated software-security verifier was blocked twice by the hosting
model's generic cybersecurity gate, including after the task was narrowed to
local defensive file-format correctness. That failure is not represented as a
completed review. The architecture and test/scale verifiers independently ran
the hostile local probes, and every reproduced case was converted to a durable
test before the final re-audit request.

## Validation evidence

- Authentic RED evidence: before implementation, collection failed with
  `ModuleNotFoundError` for
  `reddog_holoindex_query_runtime_builder_packaging_wheel`. This is preserved
  in the operator execution transcript, not independently recoverable from Git
  history; no stronger durable test-first claim is made.
- Corrected unit suite: 63 passed in 0.37 seconds. The final additions bind
  control-byte path rejection and a valid raw-archive payload ceiling.
- Exact physical reviewed wheel: 200 equal admissions in 2.78 seconds; 24
  members, 276,911 expanded bytes, bounded handle/RSS deltas, unchanged source
  SHA-256.
- Inherited upper-shape builder tier: 72,261 RECORD/inventory rows and 1,500
  Git/source rows passed in 25.70 seconds after shared-contract extraction.
- The generated registry contains 1,633 tests / 268 quarantined; the unit and
  integration wheel suites are both collectable and unquarantined.
- The generated backend closure contains 1,381 files at
  `f3cdaacf716a115e4c1d411dddab3f6e1c13a83eb27b313c3ef388f9acd99054`.

These are bounded local correctness and repeatability statements. They do not
establish upstream authentication, production workload throughput,
concurrency/horizontal scale, extraction/materialization, runtime execution,
activation, A-grade, or retrieval-quality RSI.

## Exit gate

Phase 2C1 may merge only after the synthetic hostile suite, the opt-in physical
reviewed-wheel gate, adjacent builder tests, registry/manifest checks, exact
documentation bindings, and independent WSP_00/WSP_97 architecture, security,
and test concerns are covered by completed architecture and test/scale reviews.
Any valid hostile counterexample is a NO-GO and must
be repaired without weakening the claim.
