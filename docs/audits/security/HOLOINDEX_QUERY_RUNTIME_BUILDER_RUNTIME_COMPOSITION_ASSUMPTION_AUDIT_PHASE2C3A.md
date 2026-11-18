# HoloIndex Query Runtime Builder Runtime Composition Assumption Audit - Phase 2C3a

**Status:** Implemented and falsified as an inert sequential join only
**Decision:** GO for Phase 2C3a; NO-GO for process, producer, loader, or activation claims
**Base:** `96c4bda6ff7af1abf1876355b211e8736c041ac2`
**WSP_15:** 20/P0, ULTRA
**Scope receipt:**
`HOLOINDEX_QUERY_RUNTIME_BUILDER_RUNTIME_COMPOSITION_WSP15_RECEIPT_PHASE2C3A.json`

## Retrieval and reuse audit

The governed owner query was CURRENT at the exact base, reported no index gap,
performed no reindex, and emitted receipt
`sha256:2e0f97ef6728c3e47cd54082a73f760f8fb3bf59f3bf8542453c8014eef7d83d`.
Ordering correctly led with Phase 2C2b and the candidate binding. Noise was low
but nonzero, and the first bundle omitted several Tier-1 runtime-composition
artifacts. Direct NAVIGATION and module-document reads supplied those missing
must-includes. No staleness was accepted. Apparent duplication was intentional:
source/dependency composition and base/dependency runtime composition own
different identities and stores.

The audit found that Phase 2C2b already emits the exact dependency binding and
the existing runtime-composition materializer already accepts that binding.
Creating a new base, dependency copier, descriptor format, or launcher would
duplicate proven code. A real reviewed-wheel compatibility probe confirmed the
two public APIs compose without relaxation.

## WSP_15 alternatives

| Work item | C/I/D/Im | Total | Decision |
|---|---:|---:|---|
| Inert Phase 2C2b to runtime-composition join | 5/5/5/5 | 20/P0 | GO |
| Combined sealed child plus loader/native/write closure | 5/5/5/5 | 20/P0 | NO-GO: unallocated big-bang |
| Provision pinned Git image | 4/5/4/4 | 17/P0 | Later independent gate |
| Documentation-only correction | 2/3/2/2 | 9/P3 | Insufficient |

## Earned authority

`compose_pinned_builder_runtime(...)` performs exactly two outer calls:

1. the sealed Phase 2C2b source/dependency/source coordinator;
2. the existing runtime-composition materializer using the returned dependency
   generation root.

The result requires exact dependency equality across normalized generation,
site-packages, and descriptor roots; descriptor, generation, inventory, and
tree digests; file/directory/byte counts; and the three inert authority flags.
The existing runtime verifier still owns its full `B1 -> D1 -> D2 -> B2`
component reproof. The outer coordinator creates no additional persistent
artifact, lock, rollback, deletion, process, import, owner, route, or Holo work.
Its public binding is path-free and does not carry Phase 2C2b's call-local
source-verification truth forward as current authority.

## Falsified assumptions and drift

| Assumption | Result |
|---|---|
| The Phase 2B process proof can consume a real materialized base unchanged. | **False.** Real base bindings use `<generation>/python-runtime/python.exe`; the process and candidate synthetic fixtures still assume `<generation>/python.exe`. |
| A runtime-composition receipt authenticates a producer. | **False.** It binds inert bytes/topology only. |
| Phase 2C2b source truth remains current after the longer runtime-composition call. | **False.** The outer public result records the ordering and forces current-at-return authority false. |
| Cross-store structural equality is atomicity or write denial. | **False.** Both remain explicit nonclaims. |

The base-prefix mismatch does not invalidate this join because Phase 2C3a uses
the real `RuntimeCompositionBinding.interpreter_path` and launches nothing. It
does block a truthful Phase 2C3b process adapter. The next sprint must repair
the existing process/candidate consumers and their synthetic fixtures to use
`BaseRuntimeBinding.base_prefix_root`, then independently falsify the one-shot
child. It must reuse the existing process-image and composition verifiers.

## Test-first evidence

The initial focused collection failed before production code with
`ModuleNotFoundError` for the absent builder-runtime-composition module. After
implementation, 36 focused falsifiers pass, including exact-class, boolean,
stage-stop, complete identity/nonclaim, and exception-graph probes plus the public reviewed O:
wheel with an exact synthetic base. The adjacent builder/base/composition
selection passes 318 tests with six expected capability/opt-in skips. Exact
generated closure and independent final review are recorded in the Phase 2C3a
WSP_97 execution receipt.

## Explicit nonclaims

Phase 2C3a does not prove current source authority after return, cross-store
atomicity, simultaneous snapshot, post-return immutability, persistent write
denial, upstream provenance, signature, install/import/execution, producer or
process authority, pre-import safety, ABI compatibility, Windows native-loader
or subprocess closure, deterministic effects, exact runtime closure,
activation, A-grade admission, or retrieval-quality RSI.
