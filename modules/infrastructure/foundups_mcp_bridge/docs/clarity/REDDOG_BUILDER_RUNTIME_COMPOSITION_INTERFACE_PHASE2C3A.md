# RedDog Builder Runtime Composition Interface - Phase 2C3a

This focused interface extends Phase 2C2b without growing the module's inherited
oversized `INTERFACE.md`. It is authoritative only for this inert join.

## `compose_pinned_builder_runtime(...) -> BuilderRuntimeCompositionResult`

The production entry point accepts the reviewed wheel and its store, source and
dependency stores, one already-materialized base store/generation, a composition
store, the canonical store, repository roots, and the four existing limit
contracts. Production dependencies are sealed to:

- `compose_pinned_builder_dependency_runtime(...)`; and
- `materialize_runtime_composition(...)`.

The first call returns the Phase 2C2b source/dependency binding. The second call
receives that exact dependency generation. The outer contract compares every
durable dependency identity field, including normalized internal roots, all
four digests, counts, bytes, and inert booleans. Runtime composition continues
to own full base/dependency reproof and descriptor publication.

The result preserves all four exact reuse observations: initial source,
dependency, final source, and runtime composition. Its path-free projection
binds reviewed source, dependency, base, interpreter, and runtime-composition
identities. It records sequential reuse of existing verifiers and forces all
unearned authority false. In particular, the source's earlier live-verification
observation is not represented as current authority when the outer call returns.

Stage exceptions map to stable path-free error codes. No outer lock, rollback,
delete, process, import, owner, route, or extra persistent coordinator artifact
is introduced. The only new durable object is the existing descriptor-only
runtime-composition generation.

The real base layout is `<base-generation>/python-runtime/python.exe`. Existing
Phase 2B process/candidate consumers still assume the interpreter is directly
under the generation root. Phase 2C3a launches nothing and is valid with the
real binding; Phase 2C3b must correct those consumers before child execution.

Authenticated producer/process authority, pre-import, ABI/native/subprocess
closure, deterministic effects, signing, write denial, activation, A-grade,
and retrieval RSI remain false and independently allocated.
