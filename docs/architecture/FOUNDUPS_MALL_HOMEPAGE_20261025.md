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
if its check proves description drift, preserving all membership/classification;
append bounded root and simulator ModLog notes for the route/tool compatibility.
No extra simulator behavior or source-manifest member/cap change is allocated.
Hosting preview remains a reversible verification environment. Production follows
independent browser/headers/cache evidence, dedicated PR checks and main readback.
