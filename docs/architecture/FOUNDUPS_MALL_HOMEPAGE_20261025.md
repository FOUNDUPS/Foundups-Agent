# Mall homepage and About routing — 2026-10-25

## Allocation before authoring

Approved worker slice on `agent/foundups-mall-home-20261025`, base
`c8eb983629454c6bef6e88d33826112ea19dc620`, in the managed Mall worktree only.
WSP 15: Complexity 3, Importance 4, Deferability 4, Impact 4 = **15/P1**.
Self `0102`, role `worker`, origin `internal_handoff`. Parent owns Git,
generated registries/manifests, security fingerprints, Hosting preview/browser
verification and publication. This document records allocation before product
or test changes; validation receipts will be added after execution.

## Outcome and reuse

Opening `/` displays **Play FoundUps Mall**, using the existing public directory
renderer and `/f/public_catalog.json`. `/f/` retains **FX — FoundUps Exchange**.
About reaches the existing explanatory/admission page, moved once from
`public/index.html` to `public/about/index.html`. No second catalog, router,
auth implementation, media service, wallet or trading capability is introduced.
Current inventory is 19 registry records and five public projection entities,
not an independently verified inventory of 115 FoundUps.

The shared renderer already treats a missing `/f/{id}` path as its index.
Its only catalog fetch is the scope-free public projection. Existing
`/f/{id}/app[/…]` paths hand off to `/member/` before fetching a catalog.
The exact Move2Japan public product selection remains distinct from admission.

## Retrieval and alternatives

WSP 00 awakening and tracker gate passed before execution. Refreshed WSP
15/97/102/104, NAVIGATION and the PFMall, member and touched simulator module
README, INTERFACE, ROADMAP, current ModLog and test documentation. These legacy
owners lack `memory/README.md` and module-local `requirements.txt`; no substitute
stub will be created. Historical member/simulator logs are read selectively for
the current route/PWA/integration contract, not treated as current runtime truth.

The mandated AGENTS command derives the canonical main checkout from Git's
common directory and invokes its helper. That query returned
`HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, `ok=false`, freshness `UNKNOWN`, index
gap true, authority HEAD `a519f0ad758618c5d82f0ebf8b48a3c4a0eae7f0` versus canonical
main workspace HEAD `0c81418fe94a7786cfd55f01e138ddc5d510583d` (overlay present).
An additional worktree-local helper query, prompted by newer WSP 00 guidance,
returned
`HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, `ok=false`, freshness `UNKNOWN`, index
gap true, authority HEAD `a519f0ad758618c5d82f0ebf8b48a3c4a0eae7f0` versus workspace
HEAD `c8eb983629454c6bef6e88d33826112ea19dc620`. Its local structured bundle is
additional lexical/direct-source fallback, not the mandated canonical query or
semantic-generation freshness. Both failed receipts remain distinct. No reindex occurred.
Retrieval evaluation: exact module contracts first, current owners/tests next,
historical material last; deduplicate paths and exclude training exports. The
lexical bundle omits route/browser tests, so exact source/test reads supply
those must-include artifacts. Stale documentation and optional missing artifacts
remain explicit. No Qwen/Gemma model execution is required or authorized for
this bounded static-route change; controlled local tests give direct evidence.

Competing design: retaining a physical root gateway and only adding rewrites
does not change the root page, because static content has precedence. Copying
the gateway would create two admission owners. A new router would duplicate
existing route logic. Select the single move plus existing shared renderer.

Firebase's [official Hosting configuration](https://firebase.google.com/docs/hosting/full-config)
(checked 2026-10-25) specifies static-file precedence over rewrites, first matching
rewrite selection, and rewrite content served without changing the browser URL.
Configuration matches paths, so query/hash compatibility belongs in the existing
shared script. An actual Hosting preview must still verify root-directory and
static-index resolution; a basic file server cannot establish that behavior.

## Bounded file ownership

- Move `public/index.html` to `public/about/index.html`; preserve the existing
  frontend attribute bytes without displaying them. Correct About metadata and
  the cube's sole relative script URL. Retain all legal/admission handlers.
- Update `public/f/index.html` for root/FX framing and Play, FX, About and member
  navigation. Add root manifest/worker registration only on the actual home and
  directory paths, before the existing index early return. Never register from
  protected app handoff or callback paths.
- Update `firebase.json`: exact `/` and `/index.html` rewrites to `/f/index.html`,
  existing `/f/**` rewrite next, catch-all to `/about/index.html`. Physical member
  and SSO callback pages retain their existing owners. Explicit no-cache headers
  cover root, FX and About request paths; the existing extension-based rule does
  not establish extensionless route freshness. Parent's pre-change production
  read observed root and `/f/` with `max-age=3600`, public JSON with `no-cache`.
- Update `public/sw.js`: new root cache generation, obsolete-cache cleanup only
  for the `foundups-root-` namespace, and no interception of admission URLs.
  Preserve member/tenant caches and current manifest installation identity.
  Root scope can control routes that never register it, so explicitly bypass
  About/member/callback and protected app handoff. Keep About's existing manifest
  and install affordances; migrate its old root-worker registration oracle to
  the genuine home/directory owner and remove registration from About.
- Extend only existing test owners: PFMall `test_gateway_roc_shell.py`,
  `test_gateway_terms_gate.py`, `test_video_mall_media_delivery.py`, and member
  `test_route_contract_bridge.py`. Migrate canonical gateway readers and the
  catch-all destination assertion; preserve all valid prior assertions.
- Correct the direct gateway pointer in `NAVIGATION.py`, the three default
  URL literals in simulator `visual_qa.py` to local HTTP Hosting About (root-
  absolute assets do not resolve from `file://`), the `sse_server.py` doc example,
  simulator INTERFACE examples, and the current `public/cube-animation-spec.md`
  owner pointer. Do not modify other simulator docs/logs or historical plans.
- After code freeze, update PFMall/member structured module and test memory.
  Give the parent simulator compatibility details for its separate additive log.

## Compatibility and security invariants

Only root `/` and `/index.html` may forward legacy `signin=required`,
`auth=failed`, `auth=error`, or `#how/#roc/#build/#terms` to fixed `/about/` plus
the original search and hash. Unknown markers remain ordinary discovery. Query
values never supply a redirect destination or authority; duplicate markers do
not widen the recognized set. No raw error message is inserted into HTML.

Keep Clerk redirect entry `/sso-callback/` and completion `/member/`, callback
error destinations and member guest bounce intact. About's existing curtain
continues to precede authentication. Keep public Move2Japan's exact identity/
destination pair, ordinary member admission, account return and app handoff.
Simulator options remain on About, and do not start an SSE request in discovery.
Declared symbols remain declarations, not chain assets or markets.

## Execution and acceptance

1. Run the four unchanged nearest test owners and preserve exact case IDs,
   source SHA-256 snapshots and outcome in external scratch.
2. Add desired controls in those owners before product, capture RED, then make
   the bounded move/routing/cache change. Tests execute actual route listeners
   and service-worker lifecycle/fetch handlers rather than only matching strings.
3. GREEN the same owners, then the adjacent member PWA/projector/public-product
   owners if their actual dependencies justify expansion. No broad suite.
4. Preserve original frontend attribute bytes through an opaque comparison;
   never print values. Freeze raw file hashes and report external receipts.
5. Parent independently verifies Hosting preview and browser behavior: root,
   `/index.html`, About, FX/search/readiness, detail/app paths, known admission
   query/hash flow, callback destinations, public product exception, missing media,
   responsive navigation and an old-root-cache upgrade that retains member caches.

Tests use the existing Python/Node runtimes, plugin/dotenv auto-loading disabled,
bytecode/cache writes disabled and scratch outside the checkout. Python socket/
DNS and Node network entry points are blocked in the runner. No provider/model,
credential, OAuth transaction, dependency install, Git or deploy effect belongs
to this slice. Source tests do not prove Firebase behavior, browser rendering,
actual login, deployment, live media or trading.

## Validation receipt

Worker source/test freeze is ready for parent review. External evidence root:
`C:/Users/user/AppData/Local/Temp/foundups-mall-home-695e26d23253404fac695e8fa797a5a3`.
The raw phase `results.json` files contain exact collected/executed IDs, args,
outcomes, warnings and before/after source hashes. `original-oracle-preservation.json`
records retained original assertions/case IDs after the intended path migration;
`freeze.json` records the final allocated file SHA-256 values and receipt map.
These host scratch artifacts require parent preservation for publication.

| Phase | Result | Evidence boundary |
|---|---|---|
| Unchanged baseline |365 passed,3 failed | Original368 case IDs; absent media directories |
| Initial invalid RED setup |257 passed,183 failed | Node preload path lost Windows backslashes; retained as setup history, not desired RED |
| Correct desired RED |400 passed,40 failed |37 new contract failures plus the same3 baseline failures; before product |
| Candidate and final affected |437 passed,3 failed each | All72 added cases pass; all368 original IDs/assertions retained; no new failures |
| Adjacent selection |164 passed,3 failed | Separate167 cases; unchanged member-worker regex failures |

The affected three failures are in `test_video_mall_media_delivery.py` under
`TestMediaDirectoryConvention`: `test_root_thumbs_dir_exists`,
`test_member_posters_dir_exists`, `test_member_thumbs_dir_exists`. No placeholder
directories, suppression or weakened oracle. The adjacent failures are unchanged
`test_member_pwa_hardening.py::TestServiceWorker` cases
`test_catalog_is_network_first`, `test_catalog_offline_fallback`, and
`test_poster_cache_is_separate`. Parent independently reproduced them on untouched
epoch worktree head `b6d2cf316` with identical member-worker/test blobs. Its correct
receipt is under
`C:/Users/user/AppData/Local/Temp/foundups-mall-parent-pwa-baseline-fc2f35db89b249a38459a51812fa579c`;
an earlier wrong-path exit4 before collection is separate setup history.

The same existing worker/product/account/state and projector behavioral owners
pass. Overlapping run counts and internal Node subchecks are not added. Corrected
runs record zero guarded network attempts; two inherited inactive asyncio config
warnings remain. The original baseline route helper stripped Node preload env,
so only its controlled VM fetch and Python parent guard apply to that baseline.
Projector CLI children perform pure local reads. No provider/network success
claim is inferred from the guards.

All opaque frontend attribute bytes compare unchanged. Gateway source readers
move to About; the old root-worker registration oracle now checks the public
directory. Auxiliary-only review corrected visual QA's three defaults to
`http://localhost:5000/about/` and its examples to HTTP/SSE enablement; local
Hosting must already run on port5000. This pointer correction received static
inspection, without importing Playwright or claiming file/HTTP preview execution.
No other simulator memory/source or generated security/registry artifacts changed.

Pending parent gates: independent final-source rerun, Hosting precedence/headers,
actual desktop/mobile browser route and cache-upgrade verification, reconciliation
with fresh main, generated registry/security review, publication and production
readback. No production completion is claimed by this source freeze.

## Parent publication allocation before binding

The parent independently reviewed the route, worker, Hosting and compatibility
changes and repeated all four affected owners:437 pass with the same3 inherited
media-directory failures, no collection errors, zero instrumented network calls
and stable source hashes. It also reproduced the3 adjacent stale PWA regex
failures against unchanged pre-slice sources; the first wrong-path invocation
failed before collection and remains recorded externally. Counts overlap.

Fresh main epoch PR2192 is MERGED_VERIFIED_MAIN at7d3d7f643 after22 successful
checks and exact combined-tree readback. Its public/Hosting bytes are unchanged
from the deployed92ae artifact. Reconcile that main before publication and retain
its simulator contract additions. This does not qualify a new installed runtime.

WSP15 C1/I4/D5/Impact4=14/P1 allocates one exact known frontend metadata review:
compare the old public gateway Git blob and staged About attribute opaquely,
verify the previous whole-file/rule/line approval, then bind only the unchanged
identifier's new path/file/line fingerprint in the existing ledger with one
review record. Do not print matched values or approve an unknown finding. No
scanner, rule, fingerprint, history/tree scope or regression changes. Fresh
hosted scans remain required.

Derived maintenance budget: regenerate the existing canonical test registry only
if its check proves derived drift, preserving membership and suite/quarantine classification;
append bounded root and simulator ModLog notes for the route/tool compatibility.
No extra simulator behavior or source-manifest member/cap change is allocated.
Hosting preview remains a reversible verification environment. Production follows
independent browser/headers/cache evidence, dedicated PR checks and main readback.

Registry check observed stale1770-file metadata after fresh-main reconciliation.
Canonical regeneration changes only two gateway/media descriptions and adds
the required process capability to the gateway owner, which now runs the real
Node worker harness. Membership, owner, suite, collectability and quarantine
remain unchanged (1770 files/273 quarantined). Retain this truthful derived
capability; do not alter the classifier or hide the new process dependency.

## Receipt digest review allocation before rebinding

At PR2196 head326654ae104d7f8acf15c91c5347addb9baa86b0, hosted security
job121045287812 passes20 gate regressions and reports three unreviewed generic
matches in the new portable receipt, lines494/519/548. Each is a public artifact
file SHA-256 value. WSP15 C1/I4/D5/Impact4=14/P1 allocates independent comparison
against the exact archived files and archive receipt, followed only by exact
whole-Git-blob/rule/line fingerprint bindings for those verified digests. Preserve
the receipt and scanner algorithms; no global hash/path exemption or unknown
finding approval. Re-run current-head hosted tree/history scans afterward.

The separate GitGuardian high-entropy finding identifies this receipt file but
exposes no line through its check API. Its details require dashboard access;
it remains unclassified and blocking. These three digest comparisons do not
establish the identity or resolution of that external finding.

## CI-discovered source-closure dependency allocation before repair

At headf03bc5c83e4e264178b944571a42029692180cd2, hosted test jobs fail the
unchanged canonical-generation and staged-index manifest parity controls.
The auxiliary simulator source URL edits affect source hashes even though
their intended behavior is limited to tooling/examples. The parent had not
qualified those bindings before publication; that omission is preserved here.

WSP15 C2/I5/D5/Impact4=16/P0 allocates canonical AST-only regeneration/check,
the two existing digest pins and existing closure test/log evidence. Retain
the1470-member set and all byte/member limits. Inspect exact source-row deltas
before retention; do not weaken parity or alter installed-runtime authority.
Stage only coherent bindings for the existing8 generator and3 Node controls.
The separate14/P1 exact metadata review applies only after the38 known old
manifest contexts/source identities have been independently verified against
the new whole-file binding. No blanket hash exemption or unknown approval.
Fresh current-head hosted tests, tree/history scans and GitGuardian resolution
remain required before merging or production delivery.

### Measured closure correction after canonical generation

Canonical regeneration at the same `f03bc5c83e4e264178b944571a42029692180cd2`
base disproves the preceding suspected auxiliary-source attribution: neither
`simulator/sse_server.py` nor `simulator/visual_qa.py` belongs to this manifest.
The only stale member hash is the already committed gateway test owner,
`modules/foundups/pfmall/tests/test_gateway_terms_gate.py`, whose canonical
About file-reader migration changed its source bytes. Its normalized SHA-256
changes from `1eb08d41862d43d459701413da1a8d63eca9164216891c8607cb024ad351df4c`
to `1a69a2a6b6dc515df52f475dfd24f8fa701d7994c7caea92f7f5f0c5fdd2b89d`.
The original omission and failed hosted controls remain repair history; the
16/P0 allocation covers this measured existing-owner binding, with no new
product or test behavior. All1470 paths and every other manifest field/hash
remain unchanged. Stage only the manifest and its existing JavaScript/Python
digest pins for the unchanged index-parity control.

Canonical compact-JSON digest becomes
`3db551ebd6dffc4afb0dc0ea7bd361dbca821448778c911715e7300fca43e1a7`.
The distinct whole-file LF digest becomes
`5c8ddf132bee44e95731b1affaf926c4c0183e4133d6e8f0a5c6e1272d400010`;
only that exact staged file hash belongs in any proposed scanner fingerprint.
Measured manifest sizes are332458 LF/335471 CRLF bytes, within328KiB;
normalized runtime source totals19656160 bytes, maximum member154924 bytes,
within32MiB total/2MiB per file. Keep1470 acceptance/1471 rejection unchanged.

Retrieval evaluation: the mandatory Git-common-dir-derived owner query still
returns `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, `ok=false`, freshnessUNKNOWN,
index gaptrue. Its exact result is retained externally; no reindex or current
generation claim. Direct generator, existing test/constants, module memory and
NAVIGATION evidence provide the degraded fallback. Structured-memory ordering
prioritized the actual owner and parity tests; historic epoch/authorization
entries were deduplicated as context, not Mall qualification. No missing source
owner is inferred from a search result. Manual deterministic inspection is used
because this repair requires exact Git/source-byte comparison; no model runs.

### Fresh Mall closure qualification and handoff

Canonical `--write` and `--check` exit0. After staging only the manifest and its
two existing pins, all8 unchanged cases in
`scripts/tests/test_generate_reddog_backend_manifest.py` pass in121.30s with2
inherited inactive asyncio configuration warnings. The existing Node contract,
preflight and blocked-request recovery entrypoints each exit0. Exact argv,
collected IDs, phase outcomes, JUnit and source snapshots are retained under
`C:/Users/user/AppData/Local/Temp/foundups-mall-source-closure-471faa1028fe40b08fcaf482d41fc4a5`.
These are fresh Mall qualifications. Earlier BTC/epoch results are not substituted.

Each phase's1613-file evidence map remains unchanged before/after execution;
this includes the1470 runtime members plus generator/pin/extension-JS evidence,
without increasing runtime membership. Python socket/DNS, Node network entrypoint
and dotenv-read instrumentation record zero attempts. Plugins, bytecode and
pytest cache are disabled, and temporary/database files stay outside checkout.
These are process-level guards, not OS isolation, provider or installed-runtime
qualification. Manifest caps,1470 acceptance and1471 rejection remain intact.
The existing Mall public assets, portable receipt/testcases, original CI failure
history and all1938 security ledger entries remain unchanged.

The external `proposed_metadata_rebindings.json` contains38 exact proposals
(36generic-api-key/2discord-api-token), keyed to the prior epoch evidence and the
actual staged whole-file LF hash. All five-line contexts and source blob
identities match; ledger1938, Mall3 receipt fingerprints and About fingerprint
are preserved. This document does not approve or apply them. Independent review,
fresh current-head hosted tests/tree/history scans, unresolved GitGuardian and
parent publication/readback remain required. Unknown findings are UNASSESSED.
No new registry/matrix qualification is claimed by this repair.

## Parent source-closure metadata binding after independent review

Parent independently rehashed every1470 staged runtime source blob, verified
unchanged membership and caps, both one-literal pins and the sole gateway-test
digest delta. It separately recomputed each of the38 prior reviewed bindings,
unique unchanged five-line contexts, exact source blob equality and proposed
new whole-manifest fingerprints. Stage snapshot remained stable.

The allocated14/P1 review now permits appending exactly these38 metadata
bindings to ledger1938, retaining every prior entry including About and three
artifact-digest findings. Fresh current-head hosted checks remain required;
GitGuardian's separate receipt finding remains unclassified and blocking.

## Current-main reconciliation allocation before merge — 2026-10-25

Reconcile Mall `f3817bb72d946eb44decf8ef1db58814797ad087` with verified main
`6fe7eba424c17f7813043dfb104cd845617cab38`, tree
`188c29aa4e38a5543a02d8f1971ef3549000d4f2`, under the same derived-closure
WSP15 C2/I5/D5/Impact4=16/P0 allocation. Preserve all124 public/Firebase tree
entries exactly at reviewed source `336c211cefac77b4d0c09a4c804bf085aa16b347`
and all four BTC product/test blobs exactly at main. Resolve additive docs/logs
and union every existing security-ledger entry and both Mall/BTC review proofs.
Regenerate the existing canonical manifest to combine the gateway test and BTC/
Mesa source hashes, retain1470 membership and all existing caps, and update only
the two existing digest pins. Qualify the unchanged8 generator cases and3 Node
entrypoints using prior guarded external-scratch execution, with fresh results.

Use `FOUNDUPS_SKIP_POST_COMMIT=1` for every merge/commit. Leave this merge
uncommitted until independent parent review of the new38 exact metadata
proposals; separate14/P1 review is required before any new ledger binding.
No historical receipt mutation, installed runtime promotion, public/source
behavior changes, push, Hosting deployment or GitGuardian/configuration bypass.
Exact pre-merge refs, blobs, query result and merge provenance remain external.

### Combined candidate qualification before metadata review

The merge uses the stated refs and remains uncommitted. Resolve five additive
Markdown log conflicts by retaining both sides; retain both reviewed evidence
JSONs and exact2030 existing security entries (1976 Mall/1988 main/1934 common).
No new fingerprint is added. All124 public/Firebase index entries match reviewed
336c211c; the four BTC source/test blobs match main. Historical portable receipts
remain byte-identical to their committed owners.

Canonical regeneration changes only two BTC/Mesa hash rows versus Mall and one
gateway-test row versus main. The1470-member set and all caps remain unchanged.
Manifest332458 LF/335471 CRLF bytes, normalized source total19657236 and maximum
154924 are within existing limits. Both existing digest pins advance together;
parent pin files were otherwise identical, and all original assertions remain.

Fresh canonical write/check pass; all8 existing generator cases pass in83.23s,
with2 inherited inactive asyncio warnings; all3 existing Node entrypoints exit0.
1613-file evidence snapshots are stable and instrumented network/dotenv attempts
are zero. These are source-closure checks, not a new simulator/browser/Hosting
qualification or OS sandbox proof. Exact provenance, commands, IDs, JUnit, hashes
and the external38 proposal are under
`C:/Users/user/AppData/Local/Temp/foundups-mall-main-reconciliation-fbc3fb6b643c48e29068bcd480518961`.

Mandatory owner query again returned authority-head mismatch/UNKNOWN/index gap;
current source/docs and frozen Git refs supplied the explicit degraded fallback.
No reindex or model execution. Two local packaging setup checks are preserved
externally: an overbroad Markdown marker detector matched historical long equals
separators before any write; a union hash assertion first compared Windows CRLF
with expected LF, then explicit LF bytes matched the independent union proof.
Neither was a test/product failure or grounds to weaken an oracle.

The38 combined whole-manifest fingerprints remain PROPOSED, with unchanged
contexts/source identities and UNASSESSED unknown findings. Parent independent
review must precede any new ledger binding and merge commit. New-head hosted CI/
security, unresolved GitGuardian and publication/main/readback remain required.

## Parent independent metadata acceptance — 2026-10-25

Independent review verifies all1470 indexed/working LF source digests, both
pins, fixed caps, exact2030 ordered ledger union and38 exact known manifest
metadata contexts/old approvals against main6fe and Mallf381. Exactly those38
new bindings are appended,2030->2068. Existing proof sections remain; new review
is additive. Public/Firebase bytes still equal tested preview336c. Historical
d9 candidate provenance is not claimed as an ancestor across squash integration.
No unknown finding, GitGuardian incident, scanner rule or path is exempted.
Fresh hosted checks and the pending GitGuardian inspection remain required.
Independent report rawSHA256:
7dfb2d5a90c028aa9f6c77e36fbc2ca1211f556881c776b747caf52881d038be.

## Reconcile numeric main and preserve Mall qualification

External preallocation 14/P1 precedes merging main5be89ae4 into Mall4723f6d5.
Retain all eight conflict resolutions: five additive ModLogs, the exact ordered
security-ledger union and two literal pins. Preserve both histories and current
main's numeric helper, numeric operations, resident authority forwarding and
1,471 acceptance / 1,472 rejection assertions. No cap is raised.

Canonical generation/check and the unchanged eight generator cases pass;
the same three Node entrypoints pass under the final frozen runner. Each phase
has 1,614 stable evidence inputs and zero network/dotenv/write denials. Retain
the setup-only pytest log failure, overstrict anonymous-pipe guard failure and
earlier Node runner-hash uncertainty; only their explicitly corrected fresh
phases establish this qualification. No frontend or browser rerun is claimed.

The 1,471 runtime entries match indexed and working source hashes. Relative to
main, only the existing gateway-terms test digest changes. The manifest remains
332,650 LF / 335,665 CRLF bytes under the unchanged 335,872-byte limit; source
limits remain 2 MiB each / 32 MiB total. The 124 public/Firebase Git entries and
three protected Mall evidence artifacts still equal the previously tested state
at this checkpoint. This does not cover the subsequent About ticker correction.

Parent and worker independently verify exactly 39 known source-hash contexts:
the prior 38 plus main's already approved private-helper context. All referenced
source bytes and unique lines equal main; all old fingerprints occur once in
both main and the preserved union. Retain 2,261 old entries and append only 39,
for 2,300. No flagged proof/receipt is rewritten, and no unknown finding,
GitGuardian incident, scanner scope or rule is approved.

External handoff SHA256:
f8529da84d71e9d9549b02d21446a90f040e6a10796d243cfbee1fb1f37ef684.
Parent independent review SHA256:
dc45b56b425441dcb2cbaaa537f4af6312e0775a1f812b0728ca99aa41176ca8.
Fresh hosted security/CI and the pending GitGuardian review remain required.

## About synthetic-counter correction — allocation before edit

2026-10-25; base f98f903aa16a7dbfd00ad2fbd7f7a0b8a398162a. Parent
allocates WSP15 C1/I4/D4/Impact4 = 13/P1 to the existing About page only.
Replace its synthetic-count heading with a static Browse FoundUPS link to `/`
and remove only the deterministic FoundUP Ticker IIFE before ROC Canvas.
Preserve every other byte of About, including admission/auth/opaque frontend
attributes, and retain the protected Mall receipt, testcase companion and proof.
This is local HTML copy/animation work; WRE is not applicable. Validate HTML
structure and inline JavaScript syntax, then verify all 1,471 runtime hashes
and existing manifest/pins unchanged. No eight-plus-three rerun, browser,
Hosting or production claim; old preview/test evidence remains historical.
External prior snapshots and preallocation: `foundups-mall-about-ticker-ej8lllyy`.
No commit, push, hosting, registry, framework or proof change is allocated.

### About counter correction — local static validation

Replaced one synthetic-count heading with the static `Browse FoundUPS` link
to `/`; removed only its 46-line deterministic ticker block before ROC Canvas.
Every other About byte and all seven script start tags/attributes are preserved.
HTML structure and JSON-LD parsing pass; all four inline JavaScript blocks pass
Node syntax-only checks. No inline script, login flow or browser was executed.
All 1,471 runtime inputs, manifest and two digest pins remain byte-identical;
the three protected Mall receipt/testcase/proof artifacts are unchanged. No
eight-plus-three, frontend suite, Hosting or production rerun is claimed.
External snapshots, raw/Git-LF hashes, effect counts and validation are retained
in `foundups-mall-about-ticker-ej8lllyy`. Parent review, commit and fresh preview remain pending.


## Exact About identifier rebinding after the copy correction

WSP15 allocation before ledger edit: C2/I4/D4/Impact4 = 14/P1, three existing
metadata files, one observed finding only. Hosted job 121077933339 reports one
unreviewed tree finding at About line 75 and zero unreviewed history findings.
Parent and independent reviewer compare its unchanged frontend publishable
identifier privately against both previously reviewed Git blobs and verify the
exact gate fingerprint. Preserve all 2,300 entries and append only that one.
No scanner, configuration, regression, public byte or protected evidence change.
GitGuardian incident 38958604 remains unlocated and unclassified.

Accepted one exact rebinding: ledger 2,300 -> 2,301. Independent report SHA256
f333a0aea43b381ade879cafe7e8da92c14a197ff205cdd9d52b792bd3bdcc38.
Parent report SHA256
580826fa3e367da83c6f42b0faf1332c5386433865f3dcfe2b9b3b6e3bd98d7d.
Fresh hosted security is required; this is no GitGuardian incident disposition.
