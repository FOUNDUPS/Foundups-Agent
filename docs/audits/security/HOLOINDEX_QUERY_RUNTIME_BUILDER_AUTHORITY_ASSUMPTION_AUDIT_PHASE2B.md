# Assumption Audit: HoloIndex Query-Runtime Builder Authority Phase 2B

**Date:** 2026-08-29
**Base commit:** `376628fbcd4f3b36bcb0cba8f06905f68ea035b5`
**Owner:** 0102 architect
**Decision:** PROCEED only with inert structural component scaffolding

## 1. Problem Statement

- **What:** Phase 2A cannot publish or reprove a clean query-runtime candidate
  because the code parsing and proving that candidate is not execution-bound.
- **Why:** A parser version pin and source manifest do not prove the interpreter,
  parser bytes, repository bytes, process topology, or Git observations used by
  the builder.
- **Who authorized:** 012 requested continued RedDog hardening under WSP_00,
  WSP_15, WSP_62, and WSP_97. WSP_15 allocation is 20/P0 (complexity 5,
  importance 5, deferability 5, impact 5).
- **Boundary:** This phase may emit only path-free inert structural evidence. It
  may not publish a candidate, launch a candidate/builder/owner child, change a
  route/owner, activate a runtime, alter Holo maintenance, or claim
  A-grade/retrieval RSI. Only the bounded pinned-Git proof process is in scope
  when its O:/E: image is provisioned.

## 2. Retrieved Evidence and Quality

The governed Holo owner query returned `ok=true`, `freshness=CURRENT`, exact
base HEAD, `index_gap_detected=false`, `no_reindex=true`, and no authority
worktree mutation. Results found adjacent runtime/candidate/scale primitives,
but ordering was noisy and the committed-HEAD authority correctly omitted the
uncommitted Phase-2B overlay. Direct reads of module README, INTERFACE,
ROADMAP, ModLog, tests README/TestModLog, candidate/runtime contracts, backend
manifest generator, bounded Git I/O, and the exact overlay closed that gap.

## 3. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | One held Windows executable handle with read-only sharing prevents write/delete replacement while Git observations run. | `reddog_holoindex_process_image.py`; held pre/post descriptor-hash tests | HIGH |
| A2 | Worktree porcelain is both unnecessary for bound-source proof and unsafe because repository config/attributes can make it launch external filters. | Hostile audit; `git status` removal falsifier; explicit bound HEAD-byte comparison | HIGH |
| A3 | Exact RECORD ownership must be literal-case, canonical, complete, and linear. | Packaging parser/ownership tests; 72,261-row index soak | HIGH |
| A4 | Observed `sys.modules`, loader, `__file__`, and `__cached__` fields are metadata, not executed-byte provenance. | Contract keeps `preimport_loader_verified=false` | HIGH |
| A5 | Same-interpreter wrapper seals prevent accidental raw-map composition but cannot authenticate a producer. | Private mint functions are importable; raw-map and scale tests | HIGH |
| A6 | Caller-supplied expected Git digest is a pin, not a governed trust anchor. | `prove_pinned_git_authority(...)` interface | HIGH |
| A7 | The current host cannot run the real public Git/source proof. | Active Git is outside O:/E:; targeted O:/E: image gate skips | HIGH |
| A8 | The installed packaging closure is not an eligible source-only builder dependency. | 42 RECORD rows include unhashed/physical bytecode rows | HIGH |

## 4. Failure Modes

| ID | Failure Mode | Likelihood | Impact | Mitigation / disposition |
|---|---|---:|---:|---|
| F1 | Process, packaging, and source receipts describe different roots/generations. | MEDIUM | HIGH | Cross-bind process source-root/dependency digests to source/packaging identities. |
| F2 | Git executable changes after hashing but before launch. | MEDIUM | CRITICAL | One retained capability encloses pre-hash, all Git calls, and post-hash; mutation rejects. |
| F3 | Dirty bound bytes are hidden by assume-unchanged/skip-worktree, or porcelain launches an external filter. | LOW | CRITICAL | Reject every nonordinary tracked index flag, compare every observed source byte with its exact HEAD blob, never invoke status/diff/checkout, and make no global-clean claim. |
| F4 | RECORD/dist-info/case/base64/size aliases admit different bytes. | MEDIUM | HIGH | Literal roots, strict CSV, exact metadata cardinality, canonical ASCII/base64url, exact inventory equality. |
| F5 | Large ownership sets become quadratic. | HIGH at bounds | HIGH | Collision-checked O(N) RECORD and committed-file indexes; upper-shape RSS/time/handle soak. |
| F6 | Git `.git` topology, Git observations, loaded origins, or source bytes change during proof. | MEDIUM | HIGH | Before/after topology/Git/origin equality plus two confined exact source bindings compared with HEAD and each other; overall write denial and ABA resistance remain false. |
| F7 | Native DLL, dynamic import, subprocess, or pre-import execution escapes the measured metadata. | MEDIUM | CRITICAL | Explicit nonclaim; all corresponding receipt fields forced false. Dedicated sealed child is next phase. |
| F8 | Same-interpreter code mints structurally valid wrappers. | HIGH | HIGH if misused | Document wrappers as misuse guards only; governed/signature/candidate authority remains false. |
| F9 | Heavy proof runs on interactive query path. | MEDIUM | HIGH | Offline release-gate contract only; no query, owner, route, or extension wiring in this phase. |
| F10 | Paths or secrets escape through failure text. | LOW | HIGH | Stable typed error codes; no absolute paths in public receipts; hostile exception mapping tests. |

## 5. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Activate the broad existing virtual environment | Contains optional/native/cache/unhashed closure and reaches an ineligible base; not source-only or exact. |
| Accept the host Git executable outside O:/E: | Violates the approved-volume boundary and still lacks governed native/DLL closure. |
| Treat `sys.modules` metadata as executed-byte proof | Bootstrap paradox: verifier/parser code runs before it authenticates itself. |
| Build the entire sealed runtime and activate it in one change | Violates layer-by-layer WSP execution and makes falsification/rollback too broad. |
| Keep list-scanning RECORD/committed rows | Quadratic at declared bounds and disproved by hostile scale analysis. |
| Retain `git status` for a global-clean claim | Repository-local filter configuration plus committed attributes can launch an unpinned child; bound-source authority does not need global cleanliness. |
| Make the capability seal cryptographic in-process | Same-interpreter adversarial code can reach keys/functions; durable producer authentication requires a separate process/trust boundary. |

## 6. Decision Record

**PROCEED** with the five inert component modules, linear indexes, bounded Git
stdin, strict adversarial suites, path-free cross-bound receipt, documentation,
and registry/manifest projections. This decision is conditional on final
focused/scale/manifest/registry/WSP_62/WSP_97 validation at stable bytes.

**HALT** candidate publication, build/reproof binding, activation, A-grade, and
retrieval-RSI promotion. The next transaction must provision a sealed O:/E:
builder child, source-only packaging runtime, governed Git digest trust anchor,
pre-import loader proof, native/DLL/subprocess closure, deterministic controls,
signing, and empirical write denial. No failed assumption is waived or
downgraded.
