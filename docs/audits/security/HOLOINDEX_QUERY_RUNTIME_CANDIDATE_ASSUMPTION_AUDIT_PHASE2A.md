# Assumption Audit: HoloIndex clean query-runtime candidate phase 2A

## Decision boundary

This transaction may define and falsify an **inert candidate manifest**. It may
not publish governed candidate evidence, materialize or activate a runtime,
change the owner or route, claim that a
live import trace is complete, resolve Windows loader behavior, or call
HoloIndex A-grade/RSI complete.

The governed owner query was `CURRENT`, no-gap, and no-reindex at base main
`3a2eb9a5a3a70c393b6e89305112aaedef1bfbbc`. Holo retrieval was useful but
noisy: exact file inspection was still required to distinguish already-lazy
package initializers from the aggregate AST walk's over-approximation.

## WSP_15 allocation

| Option | C/I/D/Impact | Score | Decision |
|---|---:|---:|---|
| Inert clean-candidate contract and positive distribution graph | 4/5/3/5 | 17 / P0 | GO |
| Logical allowlist over the broad venv | 3/5/5/5 | 18 / P0 | NO-GO: optional presence changes behavior |
| Windows loader, route, or activation now | 5/5/5/5 | 20 / P0 | BLOCKED on physical clean candidate |
| Signatures, write denial, A-grade, or RSI promotion | 5/5/4/5 | 19 / P0 | BLOCKED on loader and clean bootstrap |

## Verified assumptions and falsifiers

| ID | Assumption | Evidence / ruling |
|---|---|---|
| A1 | An O:-local venv executable implies an O:-local base runtime. | **False.** Exact `-I -S -B` probing reports an external machine base/stdlib. The candidate contract accepts only O:/E: volume classes and requires a standalone base. |
| A2 | Requires-Dist alone is executable closure. | **False.** Markers, extras, optional imports, entry points, namespaces, ctypes/CFFI, resources, and subprocesses require independent evidence/declarations. |
| A3 | The aggregate RedDog source manifest is an exact query import graph. | **False.** It intentionally walks guarded and function-local imports and produces roughly 1,250 local files from the owner root. It remains source-byte authority, not exact query reachability. |
| A4 | A successful query trace proves native closure. | **False.** One canary observed 138 loaded `.pyd` origins, but not DLL dependencies, delay loads, `ctypes`, CFFI, loader state, plugins, or subprocess images. Trace completeness is schema-forced false. |
| A5 | Unrelated wrong-architecture files can be ignored by name. | **False.** The broad environment's eight PE32, four ARM64, and duplicate `yara_x` RECORD path may disappear only from a physically separate positive candidate. |
| A6 | A distribution name uniquely identifies imported module ownership. | **False.** Namespace packages and multiple distributions require exact module-origin path plus RECORD ownership; ambiguity rejects. |
| A7 | Target markers can use normalized host values. | **False.** Marker inputs and decisions are content-bound exactly. Host `AMD64` versus package lowercase predicates is recorded disagreement, never silently normalized. |
| A8 | FastAPI/Uvicorn are required query transport. | **False.** The owner has a supported stdlib HTTP path. Selecting that smaller policy requires explicit equivalence tests in the physical-candidate slice. |
| A9 | Candidate schema validation proves runtime effects. | **False.** The contract earns only its own canonical candidate identity. Every runtime-effect and activation field remains false. |
| A10 | Pinning `packaging==26.0` authenticates parser semantics. | **False.** The ambient interpreter, stdlib, installed parser bytes, RECORD ownership, and loaded origins need a separate sealed evidence-builder proof. |

## Implemented Phase-2A boundary

- `reddog_holoindex_query_runtime_candidate_binding.py` contains the private
  diagnostic build/reproof seam. It derives component and O:/E: volume fields from one
  inert composition, binds the exact dependency inventory/tree, confines selected
  local reads beneath its `site-packages`, derives the declaration digest from
  canonical declarations, and proves clean exact-HEAD repository identity plus
  the exact declared Phase-2A module set and loaded origins before and after
  graph derivation. This is not complete transitive builder-source closure.
- Public build and reproof fail closed with
  `QUERY_RUNTIME_CANDIDATE_BUILDER_RUNTIME_UNBOUND`. No governed candidate may
  be emitted until Phase 2B authenticates the evidence-builder process image,
  parser payload/RECORD/origins, transitive local source, and cross-pass state.
- The WSP_62 split contract/descriptor modules bind the graph projection,
  nonempty module owners, exact target environment, candidate inventory, and
  descriptor pair while forcing all runtime-effect claims false.
- The metadata/graph modules parse each broad METADATA/RECORD once under
  aggregate limits and retain every local ownership claim. Only closure-selected
  local rows bind to inventory bytes. Prefix-local Scripts/share/include rows
  are canonical, explicit byte-unverified exclusions and cannot own modules or
  satisfy subprocess declarations.
- Selected distributions bind dist-info identity, required metadata, wheel
  dialect, Requires-Python, provided extras, marker decisions, local byte
  hashes, executable roles, and exact subprocess declaration use.
- Startup hooks, `.pth`, editable/direct installs, RECORD traversal/duplicates,
  missing hashes, ambiguous owners, disguised executables, and unused or
  undeclared subprocess images fail closed. The parser-only `packaging` pin is
  isolated from the exact four-package MCP runtime requirements.
- The modules perform no target-candidate import, filesystem materialization,
  image load, owner
  launch, subprocess launch, route change, maintenance, or package change.

## Independent-audit repair record

Three WSP_00/WSP_97 reviewers returned **NO-GO** on the first draft. Their
accepted-invalid probes demonstrated a disconnected graph/schema, contradictory
launch and marker environments, optional module-origin grounding, dist-info
aliasing, incorrect `extra !=` handling, unprovided extras, incomplete RECORD
metadata, suffix-only PE acceptance, unused subprocess declarations, unbounded
selected reads, noncanonical WSP receipts, and documentation overclaims. Each
finding gained a fail-closed invariant and regression test; none was waived or
downgraded. A second hostile pass found invalid execution receipts, ambient
C:/drive-relative inputs, missing before/after source proof, parsed-name
normalization errors, runtime-requirement drift, unbounded inputs, broad-tree
overbinding, source-authority ambiguity, and implicit external RECORD rows.
The third pass found a WSP_62 breach, linked-root and nested-input falsifier
gaps, stale receipts, and unbound ambient parser semantics. Code findings were
repaired or quarantined rather than waived; receipts are regenerated only from
the final staged bytes. Focused evidence is 73 passed / two expected skips; the
separate opt-in 45,450-member tier passed current bytes in 4.56 seconds. The
adjacent runtime matrix passed 274 / 11 expected skips; backend generation
passed 8 and retained its exact 1,366-file manifest; the registry remained
current at 1,625 tests / 268 quarantined.

## Nonclaims

The following remain false: complete installed topology outside selected RECORD
members, excluded-row bytes, source-import completeness, complete transitive
evidence-builder source, authenticated parser/stdlib execution, Python distribution
closure, dynamic-load closure, Windows native-loader closure, subprocess
closure, deterministic effects, pre-import bootstrap verification, signature,
empirical write denial, activation eligibility, exact runtime closure, A-grade,
retrieval-quality RSI, and RedDog route/VSIX propagation.

## Next P0

First bind a sealed Phase-2B evidence-builder runtime: exact composition and
actual process image, exact `packaging==26.0` RECORD-owned bytes and loaded
origins, transitive local source set, and before/after equality. Then physically
materialize a clean pinned O:/E:-resident query candidate, strictly
parse all startup configuration, prove that its complete file topology equals
the positive projection, bind the exact initial `sys.path` and launch dialect,
and run semantic/transport equivalence tests. The ABI layer may then be
regenerated over only the selected native rows. Windows loader resolution is a
separate later transaction.
