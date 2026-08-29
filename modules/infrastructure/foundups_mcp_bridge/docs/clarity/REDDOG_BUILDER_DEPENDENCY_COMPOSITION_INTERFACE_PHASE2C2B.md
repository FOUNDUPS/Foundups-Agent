# RedDog Builder Dependency Composition Interface - Phase 2C2b

This focused interface extends the inert Phase 2C2a source generation without
growing the module's inherited oversized `INTERFACE.md`. It is authoritative
only for the sequential composition API and nonclaims stated here.

## `compose_pinned_builder_dependency_runtime(...) -> BuilderDependencyCompositionResult`

The Windows production entry point accepts the reviewed wheel path; wheel,
source, dependency, and canonical store roots; repository roots; and the two
existing materializer limit contracts. It uses only the module-sealed source
and dependency materializers. Dependency injection is private and test-only.

The call order is exact:

1. Materialize or reprove packaging source S1 under the source materializer's
   own lease, then return and release that call.
2. Materialize or reprove the dependency runtime from S1 `site-packages` under
   only the dependency materializer's own lease, then return and release it.
3. Materialize or reprove packaging source S2 under the source materializer's
   own lease, then require durable S1 and S2 identity.
4. Require `S2.dependency_tree_digest == dependency.generation_id`.

Durable source equality covers normalized internal roots, descriptor and
generation identities, inventory, wheel/member/tree digests, and counts. It
deliberately excludes the call-local publication-lease boolean. Both source
observations must independently carry current live fixed-pin verification.
The dependency must remain a verified inert generation whose generation ID is
its dependency-tree digest.

The result contains the final source binding, dependency binding, and three
exact-boolean reuse observations. Its exact-key public binding is path-free, flattens the
underlying public evidence, records the two generation IDs and matched tree
digest, and marks source-after-dependency reproof plus sequential-only proof.
Materializer exceptions and wrong result/reuse types map to stable stage error
codes that expose no private paths. Binding-invariant failures retain their
stable contract codes; original exceptions remain only as chained causes.

There is no coordinator lock, nested cross-store lease, rollback, deletion, or
persisted composition artifact. A valid source generation is retained if the
dependency or final reproof fails. The result does not prove that both stores
were observed simultaneously or remained immutable after return.

Accordingly, cross-store atomicity, simultaneous snapshot, persistent write
denial, post-return immutability, official provenance, signature, installation,
import, child execution, authenticated builder runtime, pre-import/loader/
native/subprocess/exact-runtime closure, deterministic effects, activation,
A-grade, and retrieval RSI are explicitly false.
