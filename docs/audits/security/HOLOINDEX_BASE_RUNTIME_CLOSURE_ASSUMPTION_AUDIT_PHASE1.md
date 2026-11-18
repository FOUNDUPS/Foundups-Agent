# Assumption Audit: HoloIndex inert base-runtime closure phase 1

## 1. Problem boundary

The query owner still executes a Python interpreter and standard library whose
bytes are ambient to the sealed source/dependency bootstrap.  Activating the
already exact dependency generation first would create partial runtime
authority while the interpreter, standard library, Python DLLs, native
extensions, loader closure, and deterministic process effects remain unbound.

This transaction may create and verify only an inert, content-addressed Python
base-runtime generation.  It may not activate that generation or change the
owner, route, supervisor, live replica, VSIX, signing, or access-control state.

## 2. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | Exact runtime closure requires interpreter and standard-library bytes, not executable metadata alone. | `reddog_holoindex_runtime_environment_binding.py` currently proves only the executable file and explicitly leaves installed bytes incomplete. | High |
| A2 | The base runtime can be projected without ambient `Lib/site-packages`; dependencies remain a separate sealed generation. | The sealed launcher already isolates Python with `-I -S -B` and admits a distinct site-packages root. | High |
| A3 | Content addressing is reusable and scalable when full hashing occurs at publication/reproof rather than per query. | The existing replica and dependency generation contracts use this pattern successfully at production shape. | High |
| A4 | Existing snapshot, confined-reader, Windows handle, no-replace publication, store-proof, orphan, and lock primitives are the correct security substrate. | Those primitives passed the prior dependency-runtime production-scale and adversarial suites. | High |
| A5 | Copying the base-runtime payload does not prove external Windows loader DLLs or deterministic process effects. | Those artifacts/effects lie outside the admitted base prefix or require empirical launch evidence. | High |

## 3. Failure modes

| ID | Failure mode | Likelihood | Impact | Mitigation |
|---|---|---:|---:|---|
| F1 | Excluded development/dependency trees silently re-enter the payload. | Medium | High | Canonically bind exact admitted and excluded roots in the descriptor and reject topology aliases. |
| F2 | Native extensions are copied but their external loader dependencies are treated as closed. | High | Critical | Inventory native-extension roles and hard-code external loader closure false. |
| F3 | Publication races or path substitution produce a generation different from the verified source. | Low | Critical | Reuse proved stores, handle-bounded copy, staging verification, atomic no-replace publication, canonical reproof, and owned quarantine. |
| F4 | A content-addressed generation is mistaken for an activation authority. | Medium | Critical | Hard-code signing, write-denial, activation eligibility, and exact-runtime closure false; document the non-claims at every interface. |
| F5 | Full host runtime hashing occurs on every owner query. | Low | High | Keep this layer offline and inert; later activation binds a verified generation identity once. |
| F6 | Current host Python on `C:` becomes an implicit production route. | Medium | High | Treat it only as publication input; a later protected transaction must activate a verified generation on the governed E:/O: runtime plane. |

## 4. Alternatives considered

1. Activate the dependency generation first: rejected because it would grant
   partial authority while interpreter/stdlib/native-loader bytes remain
   ambient.
2. Trust `METADATA`, `WHEEL`, `RECORD`, version strings, or executable paths:
   rejected because these do not prove installed runtime bytes or topology.
3. Hash the ambient interpreter tree per query: rejected as non-scalable and
   unable to provide immutable activation identity.
4. Build signing, ACL write denial, owner activation, and route-v2 in the same
   transaction: rejected by WSP_62/Occam layering and because the inert payload
   must first be independently falsifiable.

## 5. Decision

**PROCEED** with the narrow inert base-runtime contract, materializer, full-byte
descriptor verification, focused tests, production-shape opt-in proof, and
truthful documentation.  Preserve these non-claims: no activation, no signing,
no write-denial proof, no owner/supervisor/route change, no A-grade claim, and
no retrieval-RSI claim.  `runtime_environment_exact_closure_verified` remains
false.

## 6. Production falsification addendum

The opt-in real-source proof falsified two pre-publication assumptions:

1. `DLLs` contains four non-code runtime resources (`.ico` and `.cat`) in
   addition to `.dll`/`.pyd` files. They are now admitted under the explicit
   `python_runtime_data` role; no catch-all role was introduced.
2. The protected installed-Python directory denies DELETE authority. The
   existing directory lease requested that authority even for a read-only
   source. Its source mode now requests only read-attributes while
   retaining read-only sharing, so competing write/delete opens remain denied.

The repaired real proof completed without publication to any live runtime:
4,068 files, 372 child directories, 81,515,843 bytes, generation
`sha256:3efe4fba...`, exact reuse, 239.94 seconds. The decision remains
**PROCEED** with the same non-claims.
