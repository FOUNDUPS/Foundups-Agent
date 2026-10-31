# Preserved historical record: 2026-10-22-landing-page-audit.md

> Historical/proposal material. This is not a current acceptance receipt, runtime check or instruction to apply old code. The original dates and claimed outcomes below retain their historical scope.

- Original relative path: `docs/plans/research/2026-10-22-landing-page-audit.md`
- Original PC base: `0c81418fe94a7786cfd55f01e138ddc5d510583d`
- Original full file SHA-256: `9a293bc726a7c5fe1c5d5210f5d7d1662c937b31d6bb30929ed586626e7a7e1d`
- Preserved record SHA-256: `9a293bc726a7c5fe1c5d5210f5d7d1662c937b31d6bb30929ed586626e7a7e1d`
- Projection created: `2026-10-30T02:00:12.626831+00:00` (processing time only; not a new observation)
- Comparison reference: `cbef41fbae1ba1105398183e42b008f2e7dfd3dc`
- Publication: proposed; independent auditor acceptance pending.
- Current owner(s): [FOUNDUPS_DOMAIN_CANONICAL_INDEX.md](../../../../../../../../modules/foundups/docs/FOUNDUPS_DOMAIN_CANONICAL_INDEX.md), [ROADMAP.md](../../../../../../../../modules/foundups/pfmall/ROADMAP.md)

Disposition: Archive the landing coverage narrative with a historical warning. Preserve population distinctions, evidence-bounded token labels and navigation/publication acceptance requirements. Deployment drift and counts are not reasserted as current defects without new source and HTTP observations.

Private host paths and unresolved external identifiers may be omitted only in this projection; raw originals remain in the private custody backmap. External citations are retained as historical references and have not been refreshed. Runtime and commenting remain unverified.

## Historical content

# FoundUps landing page coverage audit

**Audit date:** 2026-10-22 JST  
**Lane:** 0102 reviewer, internal handoff  
**Scope:** All 16 typed registry entities, all 7 additional catalog identities, and the Geoze and Identity Shield candidates. Read-only source inspection and anonymous bounded public GETs. No Git, PR, branch, source-site, account, deployment, or blockchain operations.

The main problem is **source and deployment disagreement**, followed by incomplete project explanations and links. Local public discovery admits only three registry records. The deployed generic landing still reads an older thirteen-row member catalog, while its public projection endpoint returns HTML instead of JSON. A successful HTTP response is therefore insufficient to count a project landing or PoC.

The machine-readable companion [landing page audit JSON](2026-10-22-landing-page-audit.json) contains a separate row for every entity and candidate, evidence paths/lines, all observed HTTP results, current-source hashes and recommended actions.

## What was checked

Closed groundwork: the `/f/{foundup_id}` renderer, separate public projection, member catalog, typed registry and landing-route contracts already exist. The open target is truthful landing coverage and a bounded correction plan. This lane writes only these audit artifacts.

WSP_00 awakening ran and the tracker returned `is_zen_compliant=true`. Holo retrieval remains degraded by the parent's recorded `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`; no reindexing was attempted. Existing public-discovery and landing audits were retrieved first, then checked against current files. The active slice ledger and module README evidence were inspected. No authentication was attempted, redirects were recorded without following them, and no app action or form submission was performed.

Retrieval evaluation: older audit claims that `/f/` reads the member catalog are stale for **source** but still match **deployment**. Projector README also describes the already-completed source wiring as future work. Registry metadata conflicts with some module truth, especially VOTE, Kosei, Move2Japan and Social Twin. Separate checkouts were excluded, as were raw conversations and credentials.

The existing projector `--check --json` passed: 16 registry records, 3 public-eligible projection records, zero errors. This validates the local projection contract, not public deployment or product functionality.

## Coverage counts without conflating populations

| Surface or evidence population | Result |
|---|---|
| Canonical typed registry | 16 records: product FoundUps, candidates, platform, infrastructure, service and tool types |
| Source public projection | 3 IDs: GotJunk, Kosei, HoloIndex |
| Source generic product landings | 2 data-backed product IDs: GotJunk and Kosei; HoloIndex has a dedicated static directory |
| Dedicated landing HTML in public source | 2 identities: Kosei marketing page and HoloIndex stub; Kosei also has a separate workspace app |
| Source generic public projection omissions | 13 typed IDs and all 7 additional catalog identities |
| Deployed legacy catalog | 13 rows, versus 14 in local member catalog |
| Typed canonical IDs matching deployed legacy catalog | 4: GotJunk, Kosei, Move2Japan, AutoPost |
| Typed entities reachable only through catalog aliases | antifaFM as `antifafm`; Science Swarm Hub as `science_swarm` |
| Dedicated HoloIndex deployed page | Observed explicit stub, no navigation links |
| PoC/app endpoints returning relevant app HTML | GotJunk boot shell and Kosei login/workspace HTML |
| Functionally validated public PoCs in this audit | 0; no browser app flow, login, capture, data mutation or publishing was exercised |

The two source dedicated pages are not two additional ventures. Kosei appears in both generic and dedicated forms. The legacy catalog includes brands and identities; its thirteen rows are not thirteen proven ventures.

## Observed deployment drift

Observations occurred on 2026-10-22 JST; machine timestamps retain UTC on 2026-10-21.

1. **The expected public JSON endpoint serves the generic HTML fallback.**  
   `https://foundups.com/f/public_catalog.json` returned HTTP 200 with `text/html` and the same body digest as deployed `/f/`: `2dd90ecfaf1e8932800e4108b9f8544380e330d6b3a5690648673ce597d69658`. Current source uses this URL as JSON at `public/f/index.html:901`. Source and deployment cannot be treated as the same release.

2. **The deployed renderer uses the old member catalog.**  
   Its fetched reference is `/member/mall-video-catalog.json`; that endpoint returned valid JSON containing thirteen IDs. Local member JSON has fourteen, adding HoloIndex and a Kosei app entry. Deployed Kosei has no `entry_url` and remains `discoverable_only`; local Kosei is `ready` with an app URL.

3. **Most canonical GETs return one shared template.**  
   Canonical URLs for entities absent from the deployed catalog also return HTTP 200 and the same template body. Their entity lookup cannot be inferred from status alone. The expected exact-ID result is recorded per row; JavaScript was not executed in a browser.

4. **Two supposedly project-specific URLs fall through to the homepage.**  
   `https://foundups.com/holoindex` and `https://foundups.com/kosei/` returned the FoundUPS “Where Will You Aim Your Compute?” homepage title. The registry uses the first as HoloIndex's PoC URL, so that record currently points to the wrong content.

5. **HoloIndex is a separate static stub.**  
   `/f/holoindex_prod_01` redirects to `/f/holoindex_prod_01/`. The latter returns a 419-byte page reading “HoloIndex (Stub) Truthful Bridge Verification Search,” with no links. Local dedicated HTML is also an explicit stub. Neither proves internal HoloIndex search or a relay is publicly available.

6. **Two external product domains were unavailable within a six-second bound.**  
   AutoPost's domain and `kosei.ai` timed out. This is an availability observation, not proof of permanent failure. Anonymous GitHub AutoPost GET returned 404, consistent with the older private-repository audit but not enough to distinguish private, moved or missing. Science Swarm Hub's public GitHub page returned 200.

## Audit of every typed entity

“Generic absent” below means absent from the current **source public projection**. “Legacy match” means a matching deployed metadata ID, not a browser-validated landing.

| Entity and type | Explanation and stage evidence | Local and deployed landing | Source, app and Mall return gaps | Recommended next action |
|---|---|---|---|---|
| **GotJunk** `gotjunk_001` — foundup | README describes rapid photo/video capture and unwanted-item marketplace; Prototype current. Registry instead promises junk-removal quotes and pickup scheduling. | Generic source record exists; deployed legacy ID matches. Cloud Run returns GotJUNK React boot HTML. | No public GitHub/docs link in projection; app operation untested. Generic page returns to `/member/`; no Mall link identified in app source scan. | Correct narrative and limitations; link approved source and dated PoC evidence; add standalone app return navigation in a later authorized slice. |
| **Kosei** — foundup | Business/service orchestration and client workspace. README header says Scaffold; older embedding receipt says APP READY. Marketing copy promises automated cross-platform publishing. | Generic source record and dedicated marketing HTML exist. Live `/kosei/` is homepage fallback; direct Firebase workspace returns sign-in HTML. | No GitHub/docs link in projection. Live catalog omits app URL. No Mall link identified in dedicated marketing/workspace source. | Distinguish marketing, login scaffold and verified capabilities; reconcile deployment and app entry; add public evidence/source and return link. |
| **Vote/Ballots** `voteballots` — skeleton_candidate | Internal six-slice PoC complete; README cites historical 303-test closure. Public PoC explicitly unlaunched. Registry SPECIFIED label is stale. | Generic absent; deployed exact ID absent; shared HTTP 200 template proves no entity page. | No public app/source/docs URL in registry. Local shell payload is not a public app. | Reconcile internal-complete versus public-unlaunched state; propose an informational landing without official-ballot, payout or public-launch claims. |
| **Trade** — skeleton_candidate | Incubating/internal prototype in no-money, dry-run mode; no real trades or signing. | Generic absent; deployed exact ID absent. | No deployed app, GitHub/docs URL or real landing backlink. | Explain simulation and contract status; link reviewed source/evidence. Do not advertise trading returns or live execution. |
| **MAGADOOM** `magadoom_001` — foundup | Moderation gamification engine, timeout-derived XP/ranks and chat integration. “Production ready” README is not a hosted web-product receipt. | Generic absent; deployed exact ID absent. | No public product page, source link or web app entry in registry. | Publish an engine/integration explanation and source evidence if admitted; distinguish XP from DOOM token deployment. |
| **antifaFM** `antifafm_001` — foundup | Icecast-to-YouTube FFmpeg broadcaster; no fresh broadcast-run validation here. | Generic absent. Deployed canonical ID absent; legacy `antifafm` alias has descriptive metadata. | No canonical source/app URL in registry; alias template has Mall return. | Reconcile alias; expose approved listening/watch/source links and actual broadcast status, not a fictional tenant app. |
| **p.fMALL** `pfmall` — platform_layer | Existing discovery/member shell; local FAQ is not authenticated resident RedDog. | Its real surface is `/member/`; anonymous GET returns shell HTML only. No individual public projection row. | Internal platform documentation, not a separate venture app or token. Member gate was not entered. | Explain platform and gate boundaries in existing directory/about material; do not manufacture another FoundUp. |
| **FAM** `agent_market` — infra_service | Shared task/proof/verification/allocation ledger and contracts; production chain and UI out of PoC scope. | Generic absent; deployed exact ID absent. | Module docs exist; no public source/docs profile or separate app. | Add a curated infrastructure explanation if public discovery requires it; keep operational authority and payout claims private/gated. |
| **Move2Japan** `move2japan` — access_service | Livechat BC0/stakeholder funnel exists; stakeholder PWA scaffold pending. Product README and access-service registry classify it differently. | Generic absent. Deployed exact ID matches a video/content lane. | Proposed web domains are not proof of the app; no public GitHub/docs/app URL in registry. Legacy template returns to Mall. | Resolve classification, show current livechat entry and planned journey separately; verify domains before an app CTA. |
| **Economics Simulator** `simulator` — tool_simulator | Shared deterministic scenario/economics tool, not operating returns or a separate product token. | Generic absent; deployed exact ID absent. | Reproducible code/docs exist, no public standalone PoC/app or landing backlink. | Use an infrastructure/tool profile and model limitations; retain simulation labels on all outputs. |
| **Social Twin** `social_twin` — infra_service | README describes productization but locks human-approved PoC architecture and pending Mall mount. | Generic absent; deployed exact ID absent. | No hosted SaaS/app or public source/docs URL in registry. | Resolve product-versus-infrastructure classification, explain the human review workflow, and link curated contracts without messaging/execution authority. |
| **AutoPost** `autopost` — external_foundup | Camera-to-post engine; older audit says capture functions exist but publishing connectors are mocks. | Generic absent; deployed exact ID matches legacy catalog. Domain timed out; AI Studio/auth path not entered. | Registry GitHub URL anonymous 404; no verified public source/app or app return link. | Reconcile public/private source, domain and PoC URL; publish a truthful explanation, retaining capture versus mock publishing distinction. |
| **PQN Portal** `pqn_portal` — skeleton_candidate | Local frontend demo/gallery and API code exist, with placeholder main class. Not Science Swarm Hub. No fresh experiment validation. | Generic absent; deployed exact ID absent. | Module frontend HTML is not a deployed page. No public app/source URL or return path. | Explain scaffold/experiment status and limitations; admit demo/source/theory links only after verification. |
| **Science Swarm Hub** `science_swarm_hub` — external_foundup | External research work-registry Python package; monorepo is an exfoliation stub. Public source repository GET succeeds. | Generic absent; deployed canonical ID absent; `science_swarm` alias is the legacy repo card. | Source URL exists; no hosted web PoC. Mall backlink in external repository not verified by this audit. | Reconcile IDs and expose package/source/contribution instructions in an informational profile, not a fabricated app or payout promise. |
| **HoloIndex** `holoindex_prod_01` — infra_service with public dual identity | Public connective/trust surface; internal retrieval/index/memory authority protected. Registry says polished; actual dedicated page says Stub. | Generic data exists but static dedicated directory takes precedence. Live canonical slash page is explicit sparse stub. Registry `/holoindex` link falls home. | No project explanation, GitHub/docs link or Mall backlink on dedicated stub. Source connector requires parent-shell messaging; no public backend authority established. | Correct link and stub status, explain public trust purpose, add safe navigation/evidence, and preserve internal boundary. Remove invented token fallback. |
| **Shield** — foundup | IDEA current, SPECIFIED/not implemented; free classification PoC is next. No OCR, uploads, legal advice, wallet or payments. | Generic absent; deployed exact ID absent. | No public app/source/route URL or backlink; proposed domain unconfigured in manifest. | At most propose an idea/specification profile; keep distinct from Identity Shield and omit functional-service, upload and token claims. |

Specific evidence: `modules/foundups/foundup_registry.json` entries at lines 7, 49, 91, 131, 171, 211, 251, 290, 329, 369, 408, 448, 488, 528, 568 and 611; per-row README and additional line references are in the JSON. Key corrections are GotJunk README:3,29; Kosei README:5,84,91; VOTE README:3,36,40; Trade README:31,76; Move2Japan README:159; Social Twin README:86,107; Shield README:6,43.

## Catalog-only identities and candidates

All seven are in the observed deployed legacy catalog but absent from current source public projection and typed registry. All lack a catalog app URL, public product source link and demonstrated working venture PoC. The deployed generic template supplies a `/member/` return link if its JavaScript resolves the catalog record; the new source public renderer cannot resolve these IDs.

| ID | Identity and truthful description | Required classification/action |
|---|---|---|
| `undaodu` | Principal's personal/music/creative channel | Preserve personal/content-lane identity; not an independently verified venture |
| `foundups_main` | Umbrella FoundUPS channel | Platform brand, not another FoundUp |
| `linkedin_012` | Principal's professional identity | Identity lane; do not create a token or venture |
| `linkedin_esingularity` | AI-education LinkedIn content candidate | Resolve relationship with EDUIT before separate venture admission |
| `linkedin_tsingularity` | Singularity-research content candidate | State reserved/staging content status; no research-app PoC proven |
| `linkedin_foundups` | Umbrella LinkedIn mirror | Brand mirror, not another venture |
| `eduit` | Education initiative with derived videos from UnDaoDu; catalog calls it EDUIT/eSingularity | A content lane is not a working autonomous-learning app; resolve EDUIT/eSingularity ownership and naming before promotion |

**Identity Shield** has an explicit intake packet, not a runnable product, registry entry, catalog entry, token or public page (`modules/foundups/identity_shield/docs/intake/FOUNDUP_MANIFEST_DRAFT.md:3-39`). Its older “no Shield parent” statement must not erase the current Shield seed or merge identities automatically.

**Geoze / GeozeAi / GEOZE COIN** has historical social identity evidence and a module directory but no current canonical registry/product manifest or identified public landing. “Coin” in an old identity name is not on-chain deployment evidence.

Historical GotJunk Browse/Cart, Whack-a-Anything and platform-cube concepts remain concept/family records from yesterday's inventory. This audit does not invent canonical IDs, source repositories or routes for them.

## Shared landing gaps

### Token labels exceed their evidence

Source showcase code derives a fallback from the first four ID letters at `public/f/index.html:1124` and prefixes it with a dollar sign at `:1139`. Detail code falls back to the entire ID at `:1237` and also prefixes a dollar sign at `:1249`.

Thus a deferred/null HoloIndex token becomes a fabricated token-like label. JUNK and KOSEI are assigned symbols, not deployment receipts. The registry population contract defines `EXISTS` as “symbol documented in manifest,” not a minted or transferable asset. Future profiles should show “token deferred” or “planned symbol” with explicit evidence; this audit assigns no symbols or assets.

### The public projection is a portfolio filter, not complete discovery

`public_catalog_projector/src/projector.py:132-135,308-317` admits only `portfolio_candidate`, `portfolio_ready` and `portfolio_featured`. It therefore intentionally includes only three records. Blanket promotion of all sixteen would mix infrastructure, private capabilities, products and ideas.

Use an explicitly reviewed typed public-discovery policy if every entity needs an explanatory profile. Extend the existing registry/projector/renderer instead of cloning sixteen standalone sites or reading the member runtime catalog publicly.

### Navigation and source evidence are incomplete

Generic source landings have a Mall link at `public/f/index.html:1305`, targeting `/member/`. Dedicated Kosei and HoloIndex pages do not provide that return path in the audited source. None of the three public projection entries provides GitHub, docs or screenshots; no source/verification receipt is visible through those fields.

The generic public renderer currently displays `poc_landing_status` rather than an independently verified lifecycle/runtime receipt. “Functional” and “polished” must not be read as current app operation, backend availability or token readiness.

## Bounded correction order

1. **P0: prove and reconcile deployment identity.** Bind renderer, projection, JSON content type and catalog revision to the same reviewed release. Do not deploy the older member-catalog reader as the new public surface. This audit performs no deployment.
2. **P0: remove invented token presentation.** Preserve assigned/planned/deferred semantics; no dollar fallback from identifiers.
3. **P1: repair the three existing public identities first.** Correct GotJunk copy, Kosei landing/app deployment split, HoloIndex stub/link/backlink, and approved source/evidence links.
4. **P1: reconcile metadata before broader discovery.** VOTE internal-complete/public-unlaunched, antifa/science aliases, and Move2Japan/Social Twin type drift need explicit owner decisions.
5. **P1: admit truthful profiles for remaining products/candidates.** Separate informational idea pages, package/docs profiles, infrastructure explanations, content identities and actual PoCs. Each profile should explain the project, label its state, link reviewed source/evidence, provide an actual app entry only when verified, and return to the Mall.
6. **P2: validate app journeys separately.** Browser/auth/capture/publish/stake paths require their own admitted verification. HTTP reachability and static metadata are not a substitute.

No external website, public catalog, registry, product page, auth flow, wallet, token, pool, or governance readiness flag was changed.

