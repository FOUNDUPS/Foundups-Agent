# RedDog Builder Packaging Source Interface — Phase 2C2a

This focused interface extends the retained Phase 2C1 wheel capability without
growing the module's inherited oversized `INTERFACE.md`. It is authoritative
only for the API and nonclaims stated here.

## `materialize_pinned_builder_packaging_source(...) -> BuilderPackagingSourceMaterializationResult`

Windows-only Phase 2C2a persistence writes the exact raw wheel plus only its
strictly admitted members under `site-packages`. It publishes a wheel-and-tree-
bound generation by atomic no-replace rename and performs two consecutive
complete passes over both representations for every verification.

Bounded raw handles retain every admitted file and child directory across pass
two. Handle identity/path and complete live topology are rechecked immediately
before release. The public verifier independently requires the fixed reviewed
wheel bytes and never trusts persisted lease booleans; durable reproof returns
both publication and current-verification lease claims false.

The live public materializer returns
`source_lease_held_through_current_verification=true` on every successful call,
but returns `source_lease_held_through_publication=true` only when that call
actually publishes the generation. Reuse cannot inherit the historical claim,
and the private synthetic seam cannot confer live authority. Store paths are
restricted to O:/E: before mutation.

Equivalent calls serialize by proved store identity and reuse only a complete,
valid generation. Owned staging or newly published failures are preserved in
identity-bound no-delete quarantine. An unowned no-replace winner is verified
and never overwritten or quarantined. The returned binding carries internal
verified roots, while its exact-key `public_binding` is path-free and includes
the reviewed-pin/lease authority plus every operational nonclaim.

The result truthfully reports source extraction/materialization while official
provenance, signature, download/install, import, child execution, builder
authentication, pre-import/native/subprocess/exact-runtime closure,
determinism, write denial, activation, A-grade, and retrieval RSI remain false.
It does not invoke `materialize_dependency_runtime(...)`; the separately
allocated [Phase 2C2b composition interface](REDDOG_BUILDER_DEPENDENCY_COMPOSITION_INTERFACE_PHASE2C2B.md)
owns that sequential proof without changing this source-only authority.

The terminal retained proof denies tail changes to admitted files and detects
tail-added paths. It does not claim persistent destination write denial, an
atomic filesystem snapshot, or post-return immutability.
