# Assumption Audit: HoloIndex inert runtime composition phase 1

## Boundary

The exact Windows Python base generation and exact dependency-payload
generation existed independently, but nothing prevented a consumer from
mixing an arbitrary verified base with an arbitrary verified dependency tree.
This transaction may create only a durable, path-free, content-addressed
composition descriptor that independently reproves both payloads and the exact
`python.exe`/`site-packages` launch topology. It may not launch Python, change
an owner or route, copy payload bytes again, sign, alter ACLs, or claim A-grade
or retrieval RSI.

## Governed retrieval evaluation

The canonical owner query was `CURRENT` at exact main
`9c27cd03953bb4573c0a1091f01af649434c872a`, with no index gap and no reindex.
The first broad query was noisy: only two of ten leading results directly
constrained this slice, while exact base/dependency, sealed-runtime, signer,
route, and runtime-environment sources were displaced by historical and
adjacent records. A tightened bundle with twelve must-include paths restored
the mandatory module documents and dependency/runtime sources, but the 96 KiB
aggregate direct-read budget exhausted before all large sources were returned.
This is ranking/budget debt, not a freshness failure. Exact direct reads after
the governed freshness proof completed the audit; no maintenance was run.

## WSP_15 allocation and dialectic

| Candidate | C/I/D/Im | MPS | Decision |
|---|---:|---:|---|
| Inert exact base/dependency composition | 3/5/5/5 | 18 / P0 | **GO now** |
| Durable hard-crash recovery/retention | 3/4/3/3 | 13 / P1 | Before activation, separate slice |
| Native-loader/deterministic execution | 5/5/4/5 | 19 / P0 | Blocked on composition |
| Signer plus empirical write denial | 5/5/4/5 | 19 / P0 | Blocked on composition/loader and external principal lifecycle |
| Route-v2/resident authenticated owner | 5/5/4/5 | 19 / P0 | Must remain last |

The preferred option was challenged as possible artifact naming. A digest
concatenation or document-only “stage zero” was rejected. The accepted layer
is useful only if it reuses both existing full-byte verifiers, binds every
component descriptor/inventory/tree digest and count, binds the exact
interpreter member and isolated launch flags, publishes a canonical no-replace
generation, and fully reproves the selected component roots on reuse.

## Assumptions and falsifiers

| ID | Assumption | Required falsifier |
|---|---|---|
| A1 | A stable typed pair prevents base/dependency mix-and-match. | Substitute either generation, descriptor, inventory, tree digest, count, or role and require rejection. |
| A2 | Composition requires no third payload copy. | Prove the generation contains only the descriptor and empty publication-orphan directory while both component digests remain unchanged. |
| A3 | `python.exe` is the exact launch member, not merely any `python*.exe`. | Require the exact inventory row, role, size, and content digest and rehash that member. |
| A4 | A descriptor generation is not execution authority. | Force ABI, native-loader, determinism, pre-import, signature, write-denial, activation, and exact-closure flags false in schema validation. |
| A5 | Publication cannot convert changed component evidence into a valid composition. | Mutate a component after descriptor creation and require post-publication reproof plus quarantine. |
| A6 | Durable composition remains offline evidence, not an interactive query operation. | No spawn, owner, route, ACL, replica, queue, maintenance, or Holo mutation occurs. |
| A7 | Sequential verification cannot retain a stale first-component proof. | Inject one-shot mutations after the first base proof and after the first dependency proof; require reverse-order `B1 -> D1 -> D2 -> B2` full reproof and exact binding equality to fail closed. |

## Decision

**PROCEED** with three WSP_62-bounded sibling modules: contract, independent
descriptor verifier, and descriptor-only materializer. Reuse the existing
confined JSON, isolated-store, operation-lock, no-replace publication, owned
quarantine, base-runtime, and dependency-runtime primitives. Publish no paths
or secrets. Preserve every activation-grade claim as false.

This transaction does not close Python ABI compatibility or external DLL
loader closure. It also cannot eliminate post-proof mutation until a distinct
principal supplies durable empirical write denial. Those are explicit P0
successors, not inferred properties of content addressing. The bounded reverse
reproof detects one-shot cross-pass mutation; it is not an ABA, immutability,
or durable write-denial proof.

## Production falsification

The exact O:-local production shape materialized 72,261 dependency files / 11,639
directories / 1,853,891,335 bytes in 2,856.73 seconds, then published the
descriptor-only composition in 588.32 seconds. A fresh process running the
repaired verifier accepted `sha256:44e21db7...` in 579.54 seconds with the
descriptor unchanged, exact base `sha256:3efe4fba...`, exact dependency
`sha256:1f02b47c...`, and all activation-grade flags still false. This is
release evidence only; the double full-tree dependency pass is prohibited from
the interactive query path.
