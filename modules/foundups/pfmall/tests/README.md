# p.fMALL Tests

The suite verifies the Python shell/catalog surfaces, the Firebase/member Mall
contracts, and protected-decision boundaries. Tests are local and must not
mutate Holo replicas or trigger a Holo reindex.

## Test inventory

| File | Primary coverage |
|---|---|
| `test_shell_core.py` | Manifest validation/discovery, catalog, route, tile, shell boot |
| `test_api.py` | Dict adapter and default-shell behavior |
| `test_http_api.py` | FastAPI JSON routes |
| `test_clerk_proposal_intake.py` | Real RSA-signed Clerk-shaped session -> actual HTTP draft route, body/auth/wire bounds; no live provider identity |
| `test_shell_ui.py` | Static shell and route handoff |
| `test_member_catalog_export.py` | Canonical member projection/export |
| `test_catalog_foundup_truth_gate.py` | Catalog entity/status truth |
| `test_mall_video_catalog.py` | Video catalog shape and projections |
| `test_mall_video_player.py` | Player, gestures, queue, return, save/share/history |
| `test_video_mall_media_delivery.py` | Media paths, headers, embed and service-worker rules |
| `test_member_foundup_entry.py` | Member FoundUp entry flow |
| `test_member_pwa_hardening.py` | Manifest, service worker, restore, and wiring |
| `test_member_red_dog_concierge.py` | Shell-local FAQ concierge; no backend/AI claim |
| `test_gateway_roc_shell.py` | Gateway shell, public FX navigation and phased runtime contracts |
| `test_gateway_terms_gate.py` | Terms/disclaimer/admission UI |
| `test_verification_gap_guard.py` | Protected decisions and advisory local-AI boundary |

The repository-level PFMall Tier-0 regression lives in
`holo_index/tests/test_tier0_retrieval_hardening.py` because it verifies the
shared Holo contract rather than PFMall runtime behavior.

The actual `/f/` inline route/filter VM is owned by
`public/member/tests/test_route_contract_bridge.py`. Reuse it for public
directory search, readiness, escaped output, error and admission-handoff behavior;
its current inventory and focused commands are in `public/member/tests/README.md`.

## Commands

```powershell
python -m pytest modules/foundups/pfmall/tests -q
python -m pytest holo_index/tests/test_tier0_retrieval_hardening.py -q
python modules/infrastructure/wre_core/scripts/generate_test_registry.py --check
```

For focused work, execute the nearest test file first and expand to the full
module suite. A merged Holo documentation change additionally requires the
governed exact-main maintenance/activation flow and a digest-stable owner query;
pytest is not a substitute for that operational proof.

The new draft-intake owner uses the optional `../requirements.txt` HTTP profile,
pytest9.0.3 and httpx0.28.1 for local transport tests. Its final runtime profile
pins FastAPI0.162.0/Starlette1.10.0/PyJWT2.15.1/cryptography50.0.2 after public
registry advisories rejected the initial older profile. The isolated environment
and this contract CI pin pip26.2.2 separately, retaining its acquisition report;
the final installed-inventory inspection includes all26 distributions, including
the installer. Existing
nomination-contract CI retains the resolved dependency report and exact JUnit
cases. RSA keys and tokens are synthetic and never printed. Offline signatures
do not qualify a production Clerk instance, membership, current revocation,
repository control or a deployed service. Keep legacy HMAC owners unchanged.
The final profile's retained HTTPX test-client deprecation is reviewed and not
filtered; it is different from the original AnyIO alias warning.

The same real-RSA owner adds28 isolated-host cases using its original fixtures:
per-app policy and unchanged-handler identity, separate signing keys, minimal
routes/health, strict bounded policy files and generic startup failures. No new
test file or dependency profile. The786-case baseline and all36 original named
definitions are preserved; test-first RED and814-case GREEN are recorded below.
These local ASGI checks do not establish container/cloud serving, live provider
identity, current revocation, abuse protection or a deployed browser integration.

## Real server profile

The optional `../requirements-server.txt` profile adds minimal pinned Uvicorn.
Three cases in the same RSA owner start its real factory CLI on loopback port0,
bind startup output to the child process, exercise health/auth/draft/unrelated
routes and chunked oversize rejection, and reject missing/malformed policy before
listening. Children receive a stripped environment; Windows also uses built-in
CIM metadata and taskkill with a verified-child fallback. This explicit subprocess/
loopback profile is not zero-network, OS isolation or graceful-stop evidence.
Retain every failed fixture/cleanup run and independently challenge cleanup.

## Original pre-rebase baseline

At the original pre-rebase baseline
`f06ca1fcc4acc9e2645a3ed898bad844ac6df298`, the full module suite reported 588
passes and 19 failures. The candidate reproduced the same 19 node IDs. They are
inherited catalog enum/projection drift, member UI/concierge expectation drift,
one hard-coded `O:/Foundups-Agent` fixture, and missing tracked media
directories. They are not quarantined or claimed clean by this Tier-0 repair.
The exact post-#1538 Git parent is `69b7f073`; the focused Holo Tier-0 suite is
the acceptance surface for this slice.

## GotJunk public listing read slice (2026-10-12)

`test_listing_discovery.py` covers the server-side public projection,
approval/owner/FoundUp joins, private-data field exclusion, preserved Mall
deep-link path, unavailable-provider 503 and owner/tenant 403. Tests inject
fake server-owned approval evidence; **they do not represent a working
publication store or deployment**.

```bash
python -m pytest modules/foundups/pfmall/tests/test_listing_discovery.py -q
```

### Server-injected Firestore provider regression

The same `test_listing_discovery.py` adds mocked source/approval collection
scenarios: independently reviewed revision, cross-tenant and cross-owner
denials, draft/revoked/stale item rejection, wrong-project constructor denial,
failed provider => 503 at the HTTP boundary. No network or SDK credentials.
The production reviewer, Firestore rules and deployment are **not tested**.
