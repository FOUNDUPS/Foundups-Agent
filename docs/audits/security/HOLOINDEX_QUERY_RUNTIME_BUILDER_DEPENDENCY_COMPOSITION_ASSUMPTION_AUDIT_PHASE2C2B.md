# HoloIndex Query Runtime Builder Dependency Composition Assumption Audit - Phase 2C2b

**Status:** Implemented and falsified as sequential inert composition only

**Decision:** Accept the smallest coordinator that reuses the two existing
materializers; reject cross-store locking, rollback, execution, and authority
inflation

**Scope receipt:**
`HOLOINDEX_QUERY_RUNTIME_BUILDER_DEPENDENCY_COMPOSITION_WSP15_RECEIPT_PHASE2C2B.json`

## Decision boundary

Phase 2C2a already produces a wheel-bound inert packaging source generation.
The dependency materializer already produces a separately content-addressed
inert dependency generation. Phase 2C2b answers only whether one call can prove
that the dependency was materialized from a source generation whose durable
identity is still the same immediately after the dependency transaction.

The accepted sequence is:

1. materialize or reprove source S1 and return from that call;
2. materialize or reprove the dependency from S1 `site-packages` and return;
3. materialize or reprove source S2;
4. require durable S1 identity equals S2 identity; and
5. require the source dependency-tree digest equals the dependency generation
   ID.

This is a sequential reproof. The stores are not locked together and are not
claimed to have been observed in one simultaneous filesystem snapshot.

## Verified assumptions

- The production entry point closes over the reviewed source and dependency
  materializers. Replacement callables exist only in a private test seam.
- Each source call independently requires the reviewed pin and current live
  source-verification authority. Persisted or historical lease booleans are not
  sufficient.
- Durable source comparison includes normalized roots, descriptor/generation/
  inventory/wheel/member/tree digests, and counts. It excludes only the
  publication-lease boolean because that truth belongs to the individual call.
- The dependency binding must retain publication byte verification, false
  write-denial and activation claims, valid identities/counts, and
  `generation_id == dependency_tree_digest`.
- All three reuse observations must be exact booleans before they can enter the
  public result contract.
- The final cross-binding requires
  `source.dependency_tree_digest == dependency.generation_id`.
- Public evidence contains no `Path` values. Stage failures expose stable codes
  rather than private paths; diagnostic causes remain chained internally.
- A later failure does not delete, quarantine, or roll back a valid source
  generation. Each existing materializer remains responsible for its own store.

## Failure modes and falsifiers

| Failure | Required outcome |
|---|---|
| Initial source call raises or returns the wrong result/reuse type | Fail with the initial-source stage code before dependency work |
| Dependency call raises or returns the wrong result/reuse type | Fail with the dependency stage code and retain the valid source |
| Final source call raises or returns the wrong result/reuse type | Fail with the final-source stage code and retain both valid generations |
| A source binding lacks live authority | Fail with the stable source-authority contract code |
| A dependency binding violates inert evidence | Fail with the stable dependency-binding contract code |
| Durable source identity changes between S1 and S2 | Fail closed as source changed |
| Tree digest does not match dependency generation | Fail after final source reproof as tree mismatch |
| A publication-lease field is not an exact boolean | Reject the source binding as invalid |
| Dependency claims write denial or activation | Reject the dependency binding as invalid |
| Internal exception contains a private path | Return only the stable path-free composition code |

The focused suite exercises the real dependency materializer from an
O:-confined source tree and the sealed public coordinator against the real
reviewed O: wheel for first publication and full reuse. That proves the
integration seam and local repeatability, not production-scale throughput or
simultaneous-store consistency.

## Rejected alternatives

- **One coordinator lock around both stores:** rejected because it creates a
  new lock-order/deadlock contract and still does not provide a filesystem-wide
  atomic snapshot.
- **Nested source and dependency locks:** rejected because neither existing
  materializer exports a safe retained-lease capability and lock inversion
  would enlarge the trusted computing base.
- **Delete or roll back source after dependency failure:** rejected because the
  source is a valid content-addressed generation owned by its own transaction.
- **Persist a composition descriptor now:** rejected because no consumer yet
  requires durable composition authority; adding storage would create another
  publication, migration, and reproof surface.
- **Treat matching digests as authenticated provenance or an executable
  builder:** rejected because structural equality supplies neither identity of
  an upstream producer nor process, loader, native, subprocess, or side-effect
  closure.

## Explicit nonclaims

Phase 2C2b does not prove cross-store atomicity, a simultaneous snapshot,
persistent write denial, post-return immutability, official provenance,
signature, installation, import, child execution, authenticated builder
runtime, pre-import/loader/native/subprocess/exact-runtime closure,
deterministic effects, activation eligibility, A-grade retrieval, or retrieval
RSI. It does not change RedDog conversation, owner, route, query, extension, or
VSIX behavior.

## Next gate

WSP_15 must allocate any producer/process work independently. Before a public
candidate can accept authenticated builder authority, that later transaction
must select and falsify a sealed O:/E: producer boundary and the relevant
pre-import, loader, native, subprocess, environment, and write-effect closure.
Composition evidence must remain inert until those independent gates pass.
