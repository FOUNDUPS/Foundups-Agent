# foundups_mcp_bridge Roadmap

## 2026-08-30: Base-prefix consumer correction phase 2C3b

**Implemented and falsified as a topology correction only; still not a child,
producer, loader, or activation.** The process proof now treats
`BaseRuntimeBinding.base_prefix_root` as the CPython prefix for the executable,
DLLs, Lib, prefix roles, and `sys.path`. Candidate validation requires the
canonical `<generation>/python-runtime` payload directory and binds the
interpreter beneath it. Generation-root descriptor and inventory authority
remain unchanged.

The prior process and candidate suites were false-green because their synthetic
base generation and payload prefix were the same directory. Both fixtures now
model distinct generation/payload roots. A shared real-materialization suite
proves both topology validators accept the actual composition and candidate
validation rejects the obsolete `<generation>/python.exe` topology.

**Next independently allocated P0 transaction:** bind the Phase 2C3a result to
the smallest one-shot held-executable child and reprove its actual-process
authority. Pre-import, ABI/native/subprocess closure, deterministic effects,
signing, write denial, activation, A-grade, and retrieval RSI remain later
independent gates.

## 2026-08-30: Inert builder-runtime composition phase 2C3a

**Implemented and physically falsified as an inert join; not a producer,
process, or activation.** The coordinator calls Phase 2C2b, passes its exact
dependency generation to the existing runtime-composition materializer, and
requires equality across every dependency path identity, digest, count, byte,
and inert authority field. It creates no outer lock, rollback, deletion,
process, import, route, owner, or persistent coordinator artifact. Its public
binding is path-free and refuses to represent the earlier source observation
as current authority after the longer composition call.

The real reviewed O: wheel successfully composed with an exact synthetic base
and reused both dependency and descriptor generations. This integration
falsified an older synthetic topology assumption: materialized base runtimes
place the interpreter at `<generation>/python-runtime/python.exe`, while the
Phase 2B process/candidate consumers still required `<generation>/python.exe`.
Phase 2C3a uses the real composition binding and launches nothing, so its proof
remains valid.

**Phase 2C3b addendum:** the process and candidate consumers/tests now use the
real `base_prefix_root`. The smallest one-shot child adapter remains next.
Pre-import, ABI/native/subprocess closure, deterministic effects, signing,
write denial, activation, A-grade, and retrieval RSI remain later gates.

## 2026-08-29: Sequential builder/dependency composition phase 2C2b

**Implemented and falsified as a sequential composition proof; not an atomic,
installed, importable, executable, or authenticated builder runtime.** The
coordinator calls the sealed source materializer for S1, lets that call release
its source-store lease, calls the existing dependency materializer under only
its own store lease, then calls the source materializer again for S2. It
requires live fixed-pin source authority for both observations, exact durable
S1/S2 identity excluding call-local publication truth, an inert verified
dependency binding, and
`source.dependency_tree_digest == dependency.generation_id`.

The coordinator introduces no outer or cross-store lock, rollback, deletion,
or persistent composition artifact. A dependency failure leaves a valid source
generation intact. Its path-free binding explicitly marks the proof as
sequential and denies cross-store atomicity, simultaneous-snapshot authority,
persistent write denial, and post-return immutability. Provenance/signing,
installation/import/execution, authenticated builder and pre-import/loader/
native/subprocess/exact-runtime closure, deterministic effects, activation,
A-grade, and retrieval RSI remain later independently falsified gates.

**Next independently allocated P0 transaction:** bind the composition to an
authenticated producer boundary only after selecting and falsifying the
smallest sealed O:/E: child/process and pre-import loader closure. It must not
convert structural composition into provenance, execution, write-denial,
activation, or retrieval-quality authority.

## 2026-08-29: Wheel-bound inert packaging source phase 2C2a

**Implemented and physically falsified as persistent inert source; not an
installed, importable, executable, or authenticated builder.** One private
Phase 2C1 capability retains the original wheel directory/file handles while
the exact raw image and admitted members are written. Five WSP_62-bounded
modules separate the canonical contract, O(depth) Windows writer, Windows
store/root/topology leasing, full wheel-to-tree verifier, and
no-replace/quarantine materializer.

The generation identity binds the wheel pin and archive/distribution digests
as well as the extracted dependency-tree digest. Canonical verification
reparses the stored wheel, compares every extracted member byte-for-byte,
proves exact file and empty-directory topology, and rejects ADS, hardlinks,
reparse points, case aliases, mutation, corrupt
reuse, and unowned no-replace winners. The exact O: artifact passed first
publication plus 200 full reuses in 105.09 seconds with unchanged source SHA
and bounded handle/RSS deltas. This is repeatability/leak evidence, not
throughput or horizontal-scale proof. Public verification requires the fixed
reviewed bytes but treats persisted lease booleans as non-authoritative. The
live materializer exposes current-verification authority on publish/reuse and
publication-time authority only for its own new publication. Stores are
O:/E:-only and payload bounds/tokens fail before store creation. Every verification runs two
consecutive complete passes, with every admitted child file/directory retained
across pass two and a terminal handle plus complete-topology proof before
release. This closes inter-pass and admitted-file tail mutation, and rejects a
tail-added path before success; it is not persistent destination write denial,
an atomic snapshot, or post-return immutability.

**Completed by Phase 2C2b:** source S1/dependency/source S2 composition with
durable source identity and dependency-tree equality, without a cross-store
lock or rollback. Sealed child execution, Git trust, loader/native/subprocess
closure, deterministic controls, signing, empirical write denial, activation,
A-grade, and retrieval RSI remain later independent gates.

## 2026-08-29: Reviewed packaging wheel admission phase 2C1

**Implemented and physically falsified as inert source admission; not an
authenticated builder runtime, extractor, materializer, or activation.** The
Windows-only API binds the exact repository-reviewed `packaging==26.0` wheel
filename/size/SHA through retained parent/file identities and a single bounded
read. A strict raw parser rejects ZIP64, multidisk, flags, extras/comments,
gaps/overlaps, unsafe Windows identities, unapproved roots/payloads, expansion
bounds, metadata drift, and incomplete/noncanonical RECORD ownership.

The exact provisioned O: artifact passed a 200-admission repeatability gate
with bounded handle/RSS growth and unchanged source bytes. This is a local
resource/leak proof, not throughput, concurrency, horizontal scale, official
provenance, signature, download/install, extraction/publication, import,
execution, loader/native/subprocess/exact-runtime, write-denial, activation,
A-grade, or retrieval-RSI evidence.

**Completed by Phase 2C2a:** held-handle source generation, exact admitted-byte
extraction, no-replace publication, full reproof, and no-delete quarantine.
The Phase 2C1 receipt itself still grants none of that authority. Dependency
  composition is supplied only by the sequential Phase 2C2b gate above.

## 2026-08-29: Inert query-runtime builder authority phase 2B

**Implemented as cross-bound structural component scaffolding; not an
authenticated, executable, or activation-capable builder.** The slice separates
process, packaging, pinned-Git, repository-source, and receipt contracts into
WSP_62-bounded modules. It closes accepted-invalid RECORD case/alias/hash/size,
METADATA cardinality, dist-info identity, hidden Git index flags, Git topology,
held-executable TOCTOU, component substitution, and quadratic ownership lookup
failures. Public candidate build/reproof stay unbound.

The current host cannot complete a real public proof: Git is not provisioned on
O:/E:, and the ambient packaging installation is not a separate source-only
runtime. The opt-in 72,261 RECORD/inventory plus 1,500 Git/source-row soak is an
algorithmic resource proof only, not physical closure, interactive latency, or
horizontal throughput. Same-interpreter wrapper seals are not durable authority.

Documentation projection exposed separate debt: the canonical DocDAE full
cross-reference rebuild exceeded a 604-second ceiling without writing. The one
new audit entry was projected with DocDAE's exact per-document methods and
validated inside the sorted unique 538-document index. A later WSP_15 slice
should precompute the reference map once; this offline DocDAE scaling debt is
not a query-runtime blocker.

**Corrected next-step note:** Phase 2C2a supplies only the exact source-only
packaging generation. Phase 2C2b binds it sequentially to the already-existing
inert dependency materializer. A sealed O:/E: child, governed Git trust, pre-import
loader, native/DLL/subprocess closure, deterministic controls, signing, and
empirical write denial are not Phase 2C2 promises; each requires a later
independently falsified receipt before candidate build/reproof can accept an
authenticated producer. Activation, owner, route, VSIX, A-grade, and
retrieval-RSI remain later independent gates.

## 2026-08-29: Inert clean query-runtime candidate phase 2A

**Implemented as an inert contract, positive graph, and diagnostic reproof seam; not a governed evidence builder, materialized runtime, or activation.** Diagnostics
bind one composition, dependency inventory/tree, confined selected bytes, clean-HEAD repository, declared Phase-2A modules/origins, declarations, markers, roots, module
origins, and a lower-bound trace. Broad RECORD ownership precedes selection; selected
local rows are byte-bound and prefix-local external rows are explicit exclusions.
Requires-Python/extras, wheels, executables, and subprocess use fail closed. Installed topology and dynamic/import/native-loader completeness remain unproved; all loader,
determinism, signature, write-denial, activation, exact-closure, A-grade, and RSI
claims remain false.

The parser pin does not authenticate executing `packaging`, interpreter, or stdlib; public build/reproof reject with `QUERY_RUNTIME_CANDIDATE_BUILDER_RUNTIME_UNBOUND`.
Phase 2B must bind process image, parser RECORD bytes/origins, transitive local source,
and before/after equality before evidence can be published.

Hostile review proved the broad venv cannot be activated: optional Torch and Transformers packages alter behavior by presence, `-I -S` still reaches a base
runtime outside O:/E:, and one trace cannot enumerate DLL/delay/ctypes/CFFI or
process surfaces. Phase 2B now supplies only the inert structural builder
components described above; the sealed child remains next. Physical clean O:/E:
materialization and startup parsing follow. Then the inert ABI layer may be
regenerated over selected native rows; Windows loader resolution remains later. The candidate parser's pinned `packaging` dependency stays outside the exact
four-package MCP runtime launch requirements.

The prior ABI scan found eight PE32, four ARM64, and one duplicate native
RECORD path. They may disappear only through a physically separate positive
candidate, never filename ignores or a relaxed ABI contract.

## 2026-08-29: Inert exact runtime-composition generation

**Implemented; still not activation.** A strict path-free composition contract,
independent verifier, and descriptor-only materializer now bind one exact
Windows base generation to one exact dependency generation. The identity covers
both descriptor/inventory/tree digests and counts plus the exact `python.exe`
member, separate `site-packages` role, and fixed `-I -S -B` launch topology.
Both existing full-byte verifiers rerun as `B1 -> D1 -> D2 -> B2` on canonical
verification and reuse, with exact equality required across both passes;
neither payload is copied into the composition generation. This bounded
cross-pass mutation proof does not establish ABA resistance or write denial.

The schema forces ABI compatibility, external native-loader closure,
deterministic effects, pre-import bootstrap safety, signature, empirical write
denial, activation eligibility, and exact runtime closure false. Focused
coverage is 24 passed / 1 capability skip; the explicit adjacent runtime
non-scale selection is 159 passed / 6 capability skips. Production-pair
verification passed: dependency materialization took 2,856.73 seconds,
descriptor-only composition took 588.32 seconds, and a fresh repaired-verifier
reproof took 579.54 seconds. The full dependency pass is an offline release
long pole, not interactive-query work.

## 2026-08-29: Inert exact Windows Python base-runtime generation

**Implemented and production-shape verified; this is not an activation
claim.** A strict contract, materializer, and independent full-byte verifier
now preserve a runnable base-prefix topology for root Python/VCRuntime files,
`DLLs`, `Lib`, and `tcl`, while excluding development/documentation trees and
`Lib/site-packages`. File roles, file bytes/sizes, complete directory topology,
admission/exclusion policy, inventories, and descriptors are content-addressed.
The layer reuses the bounded dependency tree copy and adds a read-only source
lease mode that does not require DELETE authority from protected installed-Python
roots while retaining write/delete share denial.

The first real run falsified two synthetic assumptions before publication:
four `DLLs` catalog/icon files needed an explicit runtime-data role, and
`C:/Python312` correctly denied a source lease that unnecessarily requested
DELETE authority. Both were repaired without relaxing topology. The final
production shape passed materialization, staging proof, no-replace publication,
canonical reproof, and exact reuse in 239.94 seconds: 4,068 files, 372 child
directories, 81,515,843 bytes, generation `sha256:3efe4fba...`.

The descriptor keeps native-loader closure, deterministic effects, signature,
write denial, activation eligibility, and exact runtime closure false. No live
owner, route, replica, maintenance state, extension behavior, or RSI changed.

## 2026-08-29: Pre-owner exact-main acceptance

The merged `REPO_HEAD_MISMATCH` ingress passed the real broker-managed path at
exact main `0f992c9b55067055049674f49568e58315242c35`. The canonical task
completed through OpenClaw/WRE at generation `sha256:eeb23404...`; a fresh
owner query was CURRENT/no-gap/no-reindex on attempt one, and full production
verification retained 33 artifacts / 222,706,129 bytes unchanged. This closes
that exact-commit maintenance gate only. Exact runtime closure, A-grade,
retrieval RSI, resident scale, and future-commit authority remain open.

## 2026-08-28: Shared owner readiness policy

The owner-acquisition boundary now centrally exports the exact transient set,
two-attempt ceiling, and 300-second operation ceiling used by both the root
one-shot and RedDog's bounded post-completion verifier. The root script no
longer defines a parallel policy. Synthetic communication and infrastructure
shards pass; exact-main live replay remains a separate gate. This is bounded
availability hardening, not resident ownership, horizontal scale, exact runtime
closure, A-grade admission, or retrieval RSI.

## 2026-08-28: Inert exact dependency-payload generation

**Implemented with production-shape and exact real-byte evidence; this is not
an activation claim.** A dedicated materializer now binds every admitted
`site-packages` file plus the complete directory topology into a canonical
content-addressed generation. It provides bounded planning, early exact reuse,
`O(depth)` Windows handle retention, staging verification, atomic no-replace
publication, canonical post-publication proof, fail-closed preservation, and
machine-wide per-store builder serialization.
Windows file/directory alternate streams and execute-bit projection are covered
through shared primitives. A production-byte run also exposed a legacy
`MAX_PATH` directory-creation boundary; extended-length creation, enumeration,
metadata, hashing, verification, and reuse now have a direct regression. The
layer remains inert and reports no signing,
write-denial, or activation authority.

The opt-in synthetic production shape passed with 72,261 files and 11,639
child directories: first materialization 1,708.812 seconds, exact reuse
836.969 seconds, peak handle delta 6, and peak RSS delta 543,744,000 bytes.
The actual 1,853,891,335-byte installed dependency tree then passed as
generation `sha256:1f02b47c...`: first materialization 2,250.675 seconds,
full reuse verification 798.191 seconds, peak handle delta 31, peak RSS delta
537,284,608 bytes, one generation, and zero successful-root orphans. These are
bounded single-builder/reuse measurements, not interactive latency or
horizontal-throughput claims.

Arbitrarily long caller-supplied repository/canonical/runtime control roots are
not part of this layer's claim; a separate P2 transaction may either bind an
explicit absolute control-root limit or extend every creation, publication,
contract, quarantine, and recovery syscall boundary.

Next P0 layers are deliberately separate: durable hard-crash recovery and
retention, signer/write-denial admission, external native-loader and deterministic-execution binding,
pre-import bootstrap verification, and resident authenticated owner selection.
Only after those exist may the runtime exact-closure predicate become true.
Retrieval RSI then needs a distinct authenticated proposer/evaluator,
canary/promotion/rollback, and production-outcome learning transaction; current
maintenance self-repair and offline recommendation do not establish it.

## 2026-08-27: Runtime-environment binding implemented; resident owner remains P0

The owner now publishes a separate runtime-environment digest binding its
descriptor-pinned executable bytes, ABI/platform, exact verified RedDog source
closure, installed distribution build records, replica/model closure, and the
actual allowlisted runtime settings. The authenticated child computes the
digest; the parent no longer predicts another interpreter's state. Required
CPU/offline/read-only settings are checked against the actual child process.
Installed distribution payload bytes are not yet verified, so the exact-
closure flag is false and the A-grade gate rejects. The public benchmark
captures the authenticated digest and keeps one owner resident for its corpus.

Earlier post-restart one-shot diagnostics failed closed at both 60 and 180
seconds with `HOLOINDEX_QUERY_SERVICE_STARTUP_TIMEOUT`; source verification
itself took about 0.1 seconds, so semantic model/backend warm-up was the long
pole. A later base-bound governed query passed on attempt one inside the
300-second CLI wall. That supersedes the diagnostic timeout for base usability,
not exact-current-main readiness or scale; persistent authenticated RedDog
owner activation remains P0. Timeout expansion alone is not a scale solution.

## 2026-08-27: Historical exact-main cold-owner evidence

The existing broker-managed OpenClaw/AgentDB post-merge path completed at exact
main `66526ae5cdd0467ce264c1db4122ab82eadb7733`, generation
`sha256:f2013aeb...`, with retry count zero and a CURRENT revision-10 route.
Three fresh-process governed owner queries completed on attempt one in about 34
seconds each. A separately pre-warmed owner started in 25.5 seconds and served
the same governed path in 10.3 seconds. Full production verification retained
all 33 artifacts / 221,204,272 bytes and the same descriptor, replica, and path
identities. This remains valid single-owner evidence for that exact commit; the
later base-bound query supersedes the timeout only for base usability. Neither
establishes current-main acceptance, horizontal scale, A-grade quality, or
retrieval RSI.

WSP_15 keeps exact installed dependency-byte closure plus resident-owner
activation at P0. Evaluator/proposer trust and production promotion remain
subsequent authority transactions.

## 2026-08-27: Owner-loaded retrieval ranker attestation

The owner now emits a SHA-256 manifest digest for the ten retrieval/ranking
modules actually loaded in its process. Health and client contracts reject a
missing or malformed digest, and the Holo retrieval benchmark rejects any
digest different from its clean authority candidate. This closes the former
clean-authority/dirty-runtime attestation gap without forbidding ordinary
query use from a dirty workspace. Independent evaluator signing trust and
production ranker promotion remain separate blocked authority layers.
The closure includes backend routing plus final owner response ordering/path
projection plus the replica module that forces strict fp32 semantic-owner
configuration, and uses raw source bytes so checkout byte drift fails closed.
P1 remains: publish and verify one sealed owner executable/dependency/build
manifest and emit its digest instead of hashing a whole environment per query.
This must include ABI/platform and deterministic execution knobs before
retrieval-quality A-grade/RSI evidence can be called reproducible.

## 2026-08-27: Stable-route resolver environment correction

**Implemented and adjacent-GREEN; exact-main replay remains required.** The
0.4.118 exact-main run at `f058f87b` reached canonical generation
`sha256:cf1433b1...`, passed candidate admission, and committed revision 6.
Both stable proofs then failed because the callback expanded a caller mapping
that already contained `environment` and also supplied `environment` itself.
This deterministic Python duplicate-keyword failure was normalized to
`HOLOINDEX_QUERY_REPLICA_REQUIRED` and then
`ACTIVATION_QUERY_PROOF_INVALID`; the failed task and
`COMMITTED_UNVERIFIED` receipt remain immutable evidence.

The callback now projects canonical repository/store inputs explicitly and
replaces all caller route inputs with the committed route-file capability.
Candidate admission, two-attempt post-commit bound, terminal failure truth,
exact authority, semantic evidence, and immutable revalidation are unchanged.
RED reproduced the production-shaped failure. GREEN is 13 passed / 1 expected
skip at 90% controller coverage and 191 passed / 1 expected skip across the
current adjacent closure. WSP_15 is 16/P0. The pre-merge macro and release
gates are now complete: **1,136 passed / 8
expected skips in 549.69 seconds** and **4/4 release groups in 191.972
seconds**. Next gates are merge, exact-main automatic completion, immutable
verification, and the commit-bound VSIX audit.

## 2026-08-27: Post-commit stable-proof resilience

**Implemented and adjacent-GREEN; exact-main replay remains required.** The
0.4.117 OpenClaw run at exact `a48e9b61` refreshed canonical Holo, materialized
generation `sha256:7102c478...`, passed the candidate canary, and committed
route revision 5, but its first normal stable-route proof failed validation.
Later governed IDE and activation-shaped queries were CURRENT/no-gap/no-reindex
against the same immutable binding. The task and receipt remain failed/
`COMMITTED_UNVERIFIED`; they were not rewritten.

The activation controller now makes at most two post-commit stable proofs. It
catches only its typed query-validation failure, starts no retry before route
commit, and still requires full replica revalidation after a recovered proof.
Two failures remain fail-closed. WSP_15 is 17/P0. Current evidence is 13 passed
/ 1 expected skip, 90% controller coverage, 205 passed / 1 expected skip
across the adjacent closure, and 1,136 passed / 8 expected skips across the
complete bridge. The authenticated extension release passes 4/4 groups. The
next gate is merge, exact-main automatic OpenClaw completion, immutable
verification, and commit-bound VSIX packaging.

## 2026-08-27: Supported Holo owner acquisition reliability

**Implemented and focused-GREEN on base
`90e9eca19f810a03ffaacde0edfffbce2de9513b`; post-merge exact-main activation
and release packaging remain required.** Long-lived Windows callers now build
an allowlisted route-only environment from current-user authority/route values,
without copying credentials or mutating the process. The unchanged strict
resolver remains the authority gate. Independent one-shots use one of 64
PID-sharded loopback ports and one diversified retry after bounded transient
failure. Known pre-existing listeners are not adopted or killed; authenticated
health still guards the post-probe bind race, without claiming hostile
same-user isolation or globally unique PID pairs.

Final delta coverage is **119 passed**; the new owner acquisition boundary
reaches **100% statement coverage**. Two independent PowerShell processes completed
simultaneous plain governed queries at exact base, `CURRENT`, no gap, and no
reindex with distinct receipts in 38.04 seconds; both used attempt 1. Injected
contention and process-shard falsification tests cover attempt 2; live
contention is not claimed. The complete
bridge macro is **1,117 passed / 10 expected capability skips in 515.45
seconds**. Registry/backend projections and the extension release suite are
green. This proves
bounded multi-caller availability, not horizontal throughput: each caller can
still initialize its own model-backed owner. WSP_15 allocation is 19/P0. The
next scaling layer is one per-user resident broker with authenticated
current-user local IPC, broker-memory-only bearer state, bounded queueing, and
separate lifecycle/security acceptance.

WSP_62 follow-up debt: split the 1,151-line one-shot test by admission,
authority-race, owner-lifecycle, and CLI contracts, and extract the inherited
over-limit backend-manifest closure assertion function. Production files and
touched production functions remain within their enforced bounds; this debt is
test decomposition, not permission to expand either file further.

## 2026-08-27: Exact-main post-merge route activation ordering

**Implemented, focused-GREEN, and accepted through real OpenClaw at exact main
`cfd1e0051`.**
The authority transaction now holds its process lock across two authority
leases: exact-SHA checkout and canonical refresh under the first; replica
activation and stable-route owner proof outside it; final authority, clean
HEAD, and `origin/main` proof under the second. This avoids the observed
self-contention between the outer authority lease and the materializer's own
authority/maintenance lease order without creating an unlocked completion
window.

The bounded composer accepts an already-current route or allocates only an
absent `<generation-prefix>-rN` replica and
`activation_<head-prefix>_rN.json` receipt. Full digests remain authoritative;
the mnemonic prefixes select names only. Exact canonical HEAD, generation,
and receipt equality is mandatory after owner admission. Activation failure,
route malformation, second-lease contention, or supersession cannot complete
AgentDB.

Observed predecessor evidence remains intentionally separate: exact main
`a7302344424615dc9d061ef408c2de2508660b81` was manually refreshed and activated
to generation `sha256:d654414a...` with stable-route and unchanged-replica
proof. Two real OpenClaw attempts before this repair failed
`HOLOINDEX_QUERY_REPLICA_REQUIRED`. At successor exact main `cfd1e0051`, the
automatic transaction completed through the broker-managed OpenClaw supervisor
and AgentDB, activated generation `sha256:60d06274...`, returned a fresh
CURRENT/no-gap/no-reindex owner query, and preserved all immutable replica
digests. The gate is closed for that commit; later HEADs require new evidence.

## 2026-08-23: Exact query-replica activation controller

**Implemented locally and WSP_62-bounded; live activation remains an explicit
post-merge operation.** The inert-by-default controller composes the existing
maintenance-only proof, planner, compact materializer, route CAS, supported
one-shot owner query, replica revalidation, and no-replace private receipt
publisher. Its canary is fixed and must return real semantic evidence. Clean
exact repository state is reread, not synthesized, before and during owner
admission, after materialization before route transition, and again after the
candidate query immediately before commit.

Candidate query or replica drift rolls back to the exact predecessor.
Post-commit failures remain `COMMITTED_UNVERIFIED`; an interrupted receipt can
be finalized on the next identical invocation by resolving the committed
route, running one fresh stable-route canary, and revalidating every retained
artifact. Receipt, journal, lock, route, and quarantine collisions reject
before mutation. The controller installs no environment variable and deletes
nothing. Expanded adjacent evidence is 470 passed / 7 host-capability skips.

Historical operational gates were completed manually at exact main `a7302344`.
Automatic operation was then accepted at exact main `cfd1e0051` through the
post-merge composer, followed by independent receipt/route/replica and
unchanged-digest verification. The controller remains exact-commit-bound.

## 2026-08-23: Maintenance isolated-probe runtime provenance

**Historical pre-acceptance status; resolved by the exact-main `cfd1e0051`
transaction recorded above.** A governed exact-SHA refresh exposed that the outer handshake restored
the trusted dependency path only through `PYTHONPATH`, while the nested child
scrubber correctly removed that ambient override before the final isolated
snapshot probe. The result was deterministic
`HOLOINDEX_FINAL_COLLECTION_SNAPSHOT_PROBE_FAILED` /
`RUNTIME_DEPENDENCY_UNAVAILABLE` despite a durable store and a valid runtime.

The bounded repair conveys one separately validated site-packages path,
revalidates it before `MaintenanceSession` invalidation, creates a fresh
process-image proof, and forwards the typed pair unchanged to the existing
single-shot verifier. Governed invalid/ambiguous/link authority fails before
spawn and is never downgraded to a missing marker. It adds no retry, secret
field, receipt authority, route mutation, vector fallback, or relaxed
validation. At the time of this entry, exact-main authority refresh, compact
replica materialization, and route activation remained post-merge gates; the
current status is the accepted transaction recorded above.

## 2026-08-23: Stable route-file owner resolution

**Historical pre-activation status; live route acceptance is recorded at the
top of this roadmap.** The existing owner resolver now consumes the stable private
`REDDOG_HOLOINDEX_QUERY_ROUTE_FILE`, performs a nonmutating terminal read
through the route store, and requires exact authority, canonical, replica-root, and
four-field descriptor agreement. The legacy direct root remains a migration
path; both values together fail closed. RedDog forwards the pointer through
the closed owner and resident-architect profiles plus the bounded Start
Operations promotion/control boundary.

Normal consumers take the activation lock without write authority. An
unjournaled record is valid only while `EMPTY`; every `CURRENT` record requires
an exact terminal-journal digest. `PREPARED` fails pending and only an explicit
activation/controller load may perform rollback recovery. This closes
journal-loss promotion without giving query paths publication authority.

The activation controller is now the adjacent implemented layer. Its candidate
query receives the already verified route directly and therefore does not
re-enter the route lock; the post-commit query uses the stable route file.
Supported one-shot and post-merge callers now snapshot the current allowlisted
user route and replace an inherited legacy root in a private mapping. A
restart remains useful for unrelated long-lived consumers that do not yet use
that shared acquisition boundary, but it is no longer required for these two
governed paths.

## 2026-08-23: Private route CAS and crash-recovery layer

**Implemented and independently verified at `7da03c62`; no live route
activated.** The stable private route file now starts from an immutable-shape
`EMPTY` revision and admits only exact predecessor-digest plus incrementing-
revision `CURRENT` candidates. A machine-wide lock, PREPARED journal, atomic
same-directory replacement, exact reread, rollback-only crash recovery, and
normal-exit commit finalization prevent concurrent winner, ABA, and late-error
promotion. Unknown route/journal combinations fail terminally without deletion.
PREPARED recovery evaluates structurally valid route digests before selected-
root liveness, allowing exact predecessor restoration after candidate-root
loss. Direct proofs copy exact-key binding maps and normalize hostile values.
WSP_62 separates the 196-line policy class from a 133-line confined I/O class;
both route suites are registry-collectable.

The next separately reviewed layer must bind this transaction to the verified
planner/materializer, pre-route and selected-route owner queries, secret-free
activation receipt, and deterministic recovery entry point. Stable route-file
resolution and closed-profile propagation are now the adjacent implemented
layer; the one-time user-environment installation remains an operational gate.

## 2026-08-23: Exact activation-plan admission layer

**Implemented and independently verified; live activation remains gated.** A
read-only planner proves a clean exact HEAD, CURRENT canonical
freshness, the selected `all-MiniLM-L6-v2` snapshot, and the exact 22-file
generation-bound query-snapshot set. It descriptor-hashes every file twice,
uses a final third enumeration to catch second-pass identity swaps, and passes
the result through the production generation and manifest validators. It
holds no post-return lease; the materializer owns later source revalidation.
It neither materializes nor changes routing.

The next separately reviewed layers are the private stable route-file store,
serialized digest/revision CAS with crash recovery, activation controller,
secret-free receipt, and thin trusted-host CLI. Only after merge at exact main
may the controller materialize an absent immutable root, prove candidate and
selected-route queries, and reverify all digests. Existing and historical
replicas remain untouched by the planner.

## 2026-08-23: Narrow generation-bound query-replica closure

**Implemented locally; synthetic acceptance complete; live exact-main
activation pending.** The materializer now admits only one complete selected
model plus the exact generation-bound 22-file sealed snapshot set at
`vectors/query_snapshots/`. Complete legacy vector trees, SQLite/HNSW payloads,
extra or missing snapshot artifacts, and wrong-generation snapshot manifests
fail closed before copy. Static roots, receipt paths, artifact paths, scalar
types, aliases, ordering, and full descriptor-path bounds fail before the first
replica-root mutation; inner snapshot bindings must equal the outer manifest.
Descriptor verification requires one coherent model and either the exact
modern snapshot vector surface or a complete historical SQLite/HNSW closure.
Historical full descriptors remain audit-readable but cannot pass retained
modern runtime revalidation or new materialization.

WSP_62 review extracted generation/manifest policy from the materializer,
reduced that production module from 498 to 380 lines, kept the descriptor at
649 lines, and kept the expanded primary
test module below 800 lines by giving manifest-policy regressions their own
test file. Focused acceptance is 80 passed / 2 host-capability skips. The HTTP
owner fixture now carries the same complete
replica binding required by the production client, closing inherited baseline
drift; the complete bridge package is 981 passed / 7 expected skips / 14
inherited warnings in 328.28 seconds.

The replica manifest policy keeps RedDog one-shot startup import-light: the
snapshot-set wire name is owned by the existing lightweight contract, while
NumPy-backed store validation is deferred until materialization. A no-site-
packages subprocess regression guards that boundary.

Historical exact-main replicas containing the prior 8.33 GB legacy closure
produced 122--153 second cold owner queries. The exact-`66526ae5` acceptance
route selected a narrow 33-artifact / 221,204,272-byte
replica. Broker-managed refresh, immutable materialization, serialized route
CAS, three fresh-process queries, one pre-warmed query, and unchanged full
descriptor verification all passed. Historical replicas remain immutable;
retention and deletion stay out of scope.

## 2026-08-21: Streamable HTTP `/mcp` and governed Holo bundle

**Implemented locally; live ChatGPT/tunnel acceptance pending.** The canonical
loopback server now uses Streamable HTTP `/mcp`; official-client readiness
proves initialize, initialized, exact tools/list, and a store-free lexical
`holo_query_bundle` call. The remote allowlist is pruned to that one bounded
tool and carries conservative read-only annotations. Linked-worktree launch
selects a capability-proven main MCP environment using file-only common-dir
evidence. Legacy SSE is removed; deprecated SSE launcher names are aliases to
the same HTTP runtime/lock. Startup now has one canonical capability-proven
subprocess lifecycle with direct PID ownership; the former import-dependent
in-process branch and its shutdown race are removed.

Remaining operational work: configure and verify the external Secure MCP
Tunnel/OAuth control plane from ChatGPT, record a live connection/call receipt,
and decide whether currently local-only executable-backed tools can be safely
rerouted before any future remote admission. Static bearer auth is not a
substitute for ChatGPT OAuth.

### Remote admission audit

| Former remote name | Decision | Transitive reason |
|---|---|---|
| `holo_query_bundle` | ADMIT | Exact schema, governed one-shot adapter, secret-free 256 KiB projection, no-index proof. |
| `get_repo_tree` | LOCAL ONLY | Prefix-string confinement, recursive/symlink traversal, and multiplicative output were not remotely safe. |
| `read_file` | LOCAL ONLY | Prefix-string confinement did not exclude sibling roots, `.git`, disallowed suffixes, or special/link targets. |
| `get_wsp_docs` | LOCAL ONLY | Enumeration and output have no exact remote caps or shared confinement/redaction gate. |
| `get_module_docs` | LOCAL ONLY | Recursive module discovery and document reads are unbounded and accept unconstrained names. |
| `get_interface_doc` | LOCAL ONLY | Same unbounded recursive discovery/read boundary as module docs. |
| `get_test_docs` | LOCAL ONLY | Same discovery boundary and potentially two unbounded document bodies. |
| `get_modlog` | LOCAL ONLY | Reads full logs before slicing sections; caller limit and output bytes are not exact-bounded. |
| `get_violations` | LOCAL ONLY | JSON/log input and nested result shapes lack exact byte/container bounds. |
| `get_mission_history` | LOCAL ONLY | SQLite opened in default read-write mode and JSONL input is unbounded. |
| `get_pattern_memory` | LOCAL ONLY | JSON files/containers are unbounded and loaded mappings are mutated for projection. |
| `get_overseer_status` | LOCAL ONLY | SQLite opened in default read-write mode; JSON sources lack a remote projection gate. |
| `get_coordination_state` | LOCAL ONLY | SQLite opened in default read-write mode and may create sidecars. |
| `get_known_failure_patterns` | LOCAL ONLY | JSON/JSONL reads and nested records lack strict input/output byte bounds. |
| `get_module_dependencies` | LOCAL ONLY | Recursive AST scan/read and response size are unbounded; depth is not an enforced work cap. |
| `get_reverse_dependencies` | LOCAL ONLY | Repository-wide recursive AST scan and response size are unbounded. |

Pruning is the WSP_97/Occam correction: these functions remain available only
to trusted in-process callers. No SQLite, repository walker, or arbitrary file
reader crosses `/mcp`. Future admission requires its own bounded confinement,
redaction, resource, and side-effect proof.

## 2026-08-20: Main Integration and ChatGPT MCP Boundary

The immutable query-replica/acceptance stack is integrated with main's
FastMCP read-only allowlist, fail-closed auth, lifecycle, and bounded
maintenance diagnostics. The complete bridge suite now finishes naturally in
two independent unchanged-cap runs: **899 passed / 7 skipped** in 200.66 and
314.42 seconds; the final tree with its permanent cache receipt is **900 passed
/ 7 skipped** in 215.31 seconds. Following the integration-candidate WSP_62
split, the repaired tree is **901 passed / 7 skipped / 10 warnings** in 220.32
seconds. The earlier legacy-suite timeout is therefore closed through
test-only immutable-input snapshots; no runtime cache or larger timeout was
introduced. A live tunnel, ChatGPT custom app session, Holo model/store,
maintenance transaction, and post-commit exact-SHA acceptance remain explicit
operational work; local synthetic GREEN is not a live-service receipt.

## 2026-08-17: Verified Query Replica Owner Routing Phase 2

**R24 acceptance-closure correction implemented and synthetically validated;
independent verification and live integration pending.** R16-R19 made route,
binding, and health-container admission exact. R20 rejects hostile or coerced
host/token/port/timeout scalars before connection. One exact
container guard now admits only a built-in JSON dict before the generic binding
parser admits exact built-in four-tuples and
exact, trimmed, printable built-in strings. Only expected canonical fields may
be explicit empty wildcards; actual canonical and replica fields are nonempty.
R21 closes the remaining exchange-order gap: canonical expectation is parsed
first, replica expectation second, and only then transport is validated or an
HTTP object constructed. Malformed replica values and both wrappers return the
stable secret-free mismatch with zero connection and zero hostile calls; only
the retained parsed exact tuple reaches response validation.
R22 rejects duplicate JSON member names at every nesting level rather than
using last-wins semantics, rejects NaN and infinities, and fails closed on
Unicode, syntax, primitive, bounded-size, or recursion errors. Valid unique
JSON retains the same request/read/close and readiness contract.
R23 contains the stdlib `HTTPException` family at request, getresponse, and
bounded read. Targeted HTTP/OSError close failures preserve the prior ready or
unavailable decision; unexpected and resource exceptions are not suppressed.
R24 migrates the slow loopback acceptance fixture to the mandatory full route
and extracts shutdown/context lifecycle into a cohesive internal base. The
public supervisor remains below the 200-line class limit; context entry still
requires a full route.
One canonical verifier binds the active descriptor, immutable generation
manifest, canonical repository and freshness receipt, dual leases, and private
storage identity. A retained
`QueryReplicaOwnerRoute` separates canonical freshness authority from the
replica-only semantic backend. Capability proof runs before spawn and again
before authenticated health; health/reuse require all four public replica
fields and binding drift forces replacement rather than hot swap. Explicit
argv carries both roots and the child receives no ambient `HOLOINDEX_SSD_PATH`.

The live 10,556-file replica exposed that repeating its complete 8.29 GB proof
inside the 15-second request deadline was impossible. The resident path now
keeps complete admission at route resolution and again inside the isolated
owner, then revalidates the unchanged descriptor/authority plus only the model
and sealed snapshot artifacts reachable by the in-memory backend. Measured
runtime proofs were 1.297 and 1.359 seconds versus 42.422 seconds for complete
admission; no timeout was enlarged and SQLite/HNSW remain unreachable.

**Completed plumbing:** one-shot owner query `_owner_attempt`, maintenance
`_start_owner`, and promotion `_run_locked_promotion` now resolve and propagate
the explicit current replica capability without fallback or mutation.

**Still missing:** live authorized current-generation materialization and owner acceptance; ChatGPT-app MCP proof;
active/rollback retention; governed orphan deletion; and scale evidence for
Chroma lifecycle growth and registry/closure hashing. This author slice used
synthetic stores only and is not promotion evidence. R24 author validation is
317 passed / 1 host skip for lifecycle, 411 passed / 4 host-capability skips
for the exact closure, 96 passed / 3 skips for ten-file verifier adjacency,
and 3/3 for focused cold/context/WSP62 acceptance.
Governed generation is 1,360 runtime files at `fdf3643a2cb8...befc3592129e`; registry
totals remain 1,527 tests / 265 quarantined.

## 2026-08-17: Immutable Query Replica Materializer Phase 1

**R15 no-delete correction implemented; independent re-verification pending.** The first
Phase-1 candidate failed independent verification because point lease probes
and a receipt context ended before active publication. R13 fixed that race,
but independent R14 review then proved its inspect-then-delete rollback could
delete same-inode/same-size mutated content. R15 review found a second Windows
FileDisposition cleanup path reachable on failed model copy. Those deletion
APIs are now removed; handles close while partial bytes remain for staging
quarantine or direct-caller disposition. One
generation can be copied from an exact freshness/generation binding into a
private disjoint capability using the accepted descriptor/Windows-handle copy
primitives. The candidate retains noncreating authority-update then maintenance leases
and the receipt descriptor across both publications and final validation,
uses sealed production dependencies, requires direct-root model markers and
exact normalized manifests, and performs no content deletion. Failed temps,
staging, and active names move no-replace into an owned orphan root; move
failure preserves the source name. Synthetic tests cover those boundaries. Holo
retrieval remained quarantined and no live store was accessed.

**Phase-2 follow-up:** descriptor validation, owner activation, and
generation-change restart are implemented in the later section above.
Still missing: retain active + rollback generations;
define retention and deletion under a separately proven ownership policy;
and run a separately authorized live synthetic-to-operational acceptance. The
current owner still points at its configured storage root. This candidate is
not promotion evidence.

## 2026-08-17: R11 Launch-Capability Continuity Correction

**Correction dynamically validated; independent promotion review pending.**
Independent R10 review proved that point-in-time path/identity revalidation
closed its descriptor before `subprocess.run`, leaving a replacement interval.
R11 opens a fresh verified capability at the runtime-bound runner boundary and
retains it through runner return or exception. Windows denies write/delete
replacement while launching the exact case-proved path; Linux launches the
retained object through `/proc/self/fd/<fd>` plus `pass_fds`. The exact nine-file
closure collected 146 tests: 143 passed and three explicit symlink-capability
tests skipped. An actual child-launch smoke also passed. The 184-second broad
bridge timeout remains unresolved scale evidence and was not rerun. HoloIndex
remained quarantined; no live Holo, owner, maintenance, reindex, MCP, model,
canonical-store, commit, push, or promotion effect ran.

## 2026-08-17: R10 Windows Exact-Case Executable Correction

**Superseded after independent review found a pre-launch replacement gap.**
R9 file-identity/final-path admission still accepted a case-only parent or
leaf alias because all path comparisons used `normcase`. R10 used a live
descriptor only during point validation, then required its case-preserving final
path to match every non-anchor component. The exact nine-file acceptance closure
collected 141 tests: 138 passed and three filesystem-capability symlink tests
skipped. No live acceptance, owner, maintenance, reindex, MCP, model, or
canonical-store operation ran. `INTERFACE.md` is 999 lines after deduplicating
owner/bootstrap guidance. R9 is not promotion evidence by itself.

## 2026-08-17: R9 Process-Image Authority Closure

**Superseded by R10/R11; no R9 live acceptance run.** R8 independent review
proved mutable interpreter selection and inherited interactive mode remained
open. R9 binds the OS process image and descriptor identity through runtime
admission and point-in-time pre-spawn revalidation, while the shared sanitizer
drops `PYTHONINSPECT`. Semantic/generation/freshness/single-attempt contracts
remain unchanged. ChromaDB lifecycle-row scale debt remains open.

## 2026-08-17: R8 Trusted Snapshot Runtime Closure

**Implementation complete; no R8 live acceptance run.** The final isolated
snapshot now consumes the already-proven dependency runtime instead of ambient
user-site packages, validates ChromaDB 1.5.5 origin/version before store open,
and preserves typed generation-bound failures with no retry. The retained R7
FAIL remains evidence, not a retry target or live-PASS claim. ChromaDB
`acquire_write` lifecycle-row growth remains unresolved P0 scale debt; no
semantic, freshness, or generation contract was weakened.

## 2026-08-17: R6 Receipt Continuity Closure

**Implementation complete; no R6 live acceptance run.** The acceptance receipt
now proves a retained one-way private-owner session identity, while the
post-activation freshness receipt is confined, descriptor-held, strictly
parsed, and identity/digest-bound across the semantic snapshot probe. The
ChromaDB `acquire_write` lifecycle-row scale debt remains open without any
weakened semantic or generation proof.

## 2026-08-17: R5 Supported-Wrapper Activation Hardening

**Implementation complete; live activation not run in this code slice.** The
one-shot wrapper now rejects a freshness/root mismatch before owner startup or
retry. Candidate acceptance keeps exactly two direct queries, cleans the
private owner, then requires one candidate-self-selected supported-wrapper
query plus unchanged generation/root/receipt and collection snapshots.

The `b482fdaed4932a15b2b195c256761cfd1053f053` PASS is historical pre-R5
evidence only and cannot satisfy the new contract. Detached same-SHA authority
is not interchangeable with the receipt-bound candidate root. ChromaDB 1.5.5
adds an `acquire_write` lifecycle row on every `PersistentClient` open even in
logical read-only operation. Semantic correctness is re-proved, but the
unbounded metadata-row growth has no throughput/storage cap and remains P0
scale debt. A future bounded slice must measure, compact, or replace this
lifecycle behavior without weakening generation and collection proofs.

## 2026-08-17: Isolated Exact-SHA Candidate Acceptance

**Implementation and R3 hardening complete; one real attempt failed and no live
acceptance exists.** The immutable receipt for
`fb72cbd99bc9499545823fa1849fc4597b8d71ec` is FAIL with
`NEW_PRIVATE_OWNER_HANDOFF_MISSING`, zero queries, unchanged canonical receipt,
and SHA-256 `f9b5e18ce62e63af3bbbf0e0f3d36def5614216fafadca8872703f519be43a78`.
R3 proved that a primary `HOLOINDEX_MAINTENANCE_REFRESH_FAILED` result was masked
and that the source worktrees had no verified runtime dependencies. Stable
operational errors now precede missing-handoff validation; an explicit clean,
related, dependency-only runtime checkout supplies exactly one verified local
site-packages path. The default CLI remains import-inert until valid `--real`.
The failed store remains immutable evidence and cannot be retried or promoted.
Remaining operational work is a separately authorized post-commit `--real` run
using clean exact-SHA candidate/authority worktrees, the verified runtime root,
and entirely new store and receipt targets. No live PASS or capacity claim exists.

## 2026-08-16: K-Invariant Tier-0 Owner Diagnostics

**Complete:** removed hit-conditioned owner reordering. Flattening now reserves
only when canonical nullable `tier0_module_target`, query relation, and one
complete exact pair agree. Missing, unrelated, ambiguous, multi-module,
partial, mixed, duplicate, and forged claims preserve scoring. Three stable
producer failures retain distinct HTTP/retry semantics without exposing text.

**R3 correction:** the upstream HEAD catalog now rejects Unicode
control/format/surrogate records and canonically equivalent duplicate paths.
The exact six-file focused command includes the machine-spec contract and
passes 278 tests; the adjacent owner matrix passes 356 with one optional skip.
R4 removed duplicated operational detail from the public interface and linked
its existing README/runbook owners, reducing `INTERFACE.md` from 1,010 to 971
lines without changing endpoint, error, Tier-0, or security semantics.

**Deferred:** live exact-SHA owner validation, maintenance, and receipt
publication. The uncommitted candidate cannot truthfully validate against the
03c generation and does not restart/reindex the resident owner.

## 2026-08-16: Explicit-Module Tier-0 Owner Projection

**Complete:** global owner flattening now reserves at most two existing exact
root README/INTERFACE hits for explicit uniquely evidenced module queries,
after generation-bound Holo retrieval and path projection. Low-K,
ambiguous-query, and adversarial lookup behavior is pinned by focused tests.

**Deferred:** post-commit exact-SHA maintenance/publication and live governed
owner acceptance. The resident owner is not restarted by this change.

## Historical Phase-1: HoloIndex / RedDog Operational Truth Boundary POC

**Priority:** 20 / P0 under WSP_15
**Phase:** Exact-main implementation and live acceptance complete at `66526ae5`
**Owner:** 0102 architect for 012

The Phase-1 target is one query/health-only HoloIndex owner, one trusted-host
maintenance handshake, process-private bearer handoff, exact clean-HEAD and generation
binding, semantic-only health, and complete canonical proof for all seven
baseline collections.

Acceptance included the focused HoloIndex, owner lifecycle, HTTP, RedDog
boundary, startup-dispatch, and operational-consumer matrices plus static
contract checks. The exact-main post-merge task, fresh/warm governed owner
queries, and immutable replica revalidation are complete.

## Post-Merge Activation

1. Use a clean main checkout at the merge SHA.
2. Run the trusted full-maintenance handshake against the canonical store.
3. Require seven complete canonical source-scope proofs at the exact SHA.
4. Start the private owner and require an authenticated semantic canary bound
   to the receipt generation.
5. Run one activation-style RedDog query and retain only secret-free receipt
   identifiers and result metadata.
6. Stop the owned process and confirm no maintenance lease or invalidation is
   left behind.

## Next Operational Slices

- Publish and verify a sealed runtime-environment digest without hashing a
  complete environment on every query.
- Deploy independently administered evaluator trust and authenticated proposer
  provenance for the sealed corpus.
- Wire one non-test admission consumer to a separate promotion/canary/rollback/
  outcome-learning authority; query workers retain no write authority.
- Migrate or explicitly retire the legacy `src/holo_tools.py` direct-store
  HoloIndex consumer.
- Replace the cooperative-writer/exclusive-window POC assumption with an
  immutable exact-commit source snapshot, and add orphan-process reclamation
  for abrupt host death.
- Pass semantic recall/capacity gates for representative FoundUp creation,
  repair, and enhancement tasks before any A-grade claim.
- Prove governed build-to-test-to-draft-PR recursion in isolated worktrees
  before considering unattended merge authority.

## WSP_62 Remediation Register

The exact post-repair HEAD differential has zero errors and this non-zero
accepted bridge set only:

- WARNING: `README.md` has an inherited 1,044-line no-growth boundary; focused
  Phase 2C3b detail is extracted under `docs/clarity/`.
- WARNING: `INTERFACE.md` has an inherited 1,250-line no-growth boundary;
  focused Phase 2C2a detail is extracted under `docs/clarity/`.
- WARNING: append-only `ModLog.md` 1,613 lines.
- WARNING: `src/holo_tools.py` 1,094 lines. Its candidate-grown `holo_search`
  is now a 41-line orchestrator with cohesive helpers, so the function error is
  closed while the file-level warning remains visible.
- WARNING: `tests/test_mcp_bridge.py` 1,313 lines. Cache scaffolding is already
  extracted, but the file remains a warning below its applied 1,425-line
  candidate ceiling.
- WATCH: append-only `tests/TestModLog.md` 1,165 lines.
- WATCH: `tests/test_holo_query_service_edges.py` 787 lines.

No other bridge path is part of the accepted warning/watch set. The current
post-merge candidate is bounded at authority transaction 599/max-function 46,
authority marker 87/24, transaction types 59/no functions, and replica composer
277/50. The 599-line authority facade is `no_growth: true`; the RedDog/Holo
maintainers must extract Git/lease phase mechanics into a focused engine before
adding another authority phase. Owner bootstrap and candidate acceptance remain
decomposed below their applicable thresholds.

No global WSP_62 compliance claim is made until those historical items are
completed and the repository-wide FMAS size gate is green. The RedDog npm
release tier is extension-scoped and does not satisfy this gate.
