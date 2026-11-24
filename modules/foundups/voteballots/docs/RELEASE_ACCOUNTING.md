# Vote release accounting and launch checklist

## 2026-11-25 Dispatch portrait release

This slice adds the two approved animated caricatures to The Vote Dispatch at
`vote.foundups.com`, with separate hashtag captions and reduced-motion stills.
The existing homepage remains the entrypoint; the shared HPC/Mall card system and
computed fundraising scores are outside this release.

The refreshed public Sites project is
`appgprj_6aee6646e6ac81918ac2624d5d1db413`, observed at version 12 with source mirror
`8c40f15770ba78b622a23ebfe3d2d04533a22f99`. That mirror retains the campaign-song
player and its exact frame policy. It differs from GitHub's homepage/navigation,
so publication applies only the new portrait section, CSS/controller additions,
v13 worker and four approved WebPs. Do not replace the whole deployed homepage
or copy repository-only navigation/Press changes. Other deployed assets, including
the guide and Contact, must remain byte-identical to the refreshed mirror. Of the
33 existing public files, only four change and 29 are preserved; four are added.

Both animations retain 50 frames, 80 ms per frame and 480 × 561 dimensions;
the captions are `#SchumerOut`, `#ChuckSchumerOut` and `#JeffriesOut`.
The existing public-worker fixture covers all 36 cached resources and retirement
through v12; the new controller case covers pause and visibility state.
Detailed browser observations belong in `tests/TestModLog.md`. The focused portrait
PR is the shared release receipt for exact source/main checks, resulting mirror
commit, Sites version/deployment and live readback. This source record alone does
not assert that publication occurred.

## 2026-11-22 Source-selected skin handoff

HPC's Voice link now carries `https://vote.mtrout.com/contact#hpc`, selecting
the existing Vote skin automatically without referrer access. Vote itself stays
at Sites version 11. The public tag conveys presentation context, not identity.

Firebase Hosting project `gen-lang-client-0061781628`, site `foundupscom`:

- Pinned original live version `e8d8961e7c139c79`; authenticated custom-domain
  binding confirmed HPC belongs to this site.
- Version `cfc547e3558f4433` / release `1795302953440000` changed only the root
  `/member/mall-public-video-catalog.json` Voice link.
- Live click verification revealed the deployed HPC v25 snapshot. Version
  `2a4d064fac8b3170` / release `1795303104510000` additionally changed only
  `/member/hpc-v25/mall-public-video-catalog.json` Voice link.
- Each release cloned the current live version, compared configuration and all
  178 file hashes, changed one admitted catalog field, rechecked the live head
  before publication and read back the resulting release. Other 177 files were
  unchanged in each release; newer player assets and hosting rules were retained.
- Actual live HPC Voice click reached Vote's HPC skin at 390px without manual
  selection. 136 targeted Node tests passed; source projection equals canonical
  generator output. The broader player browser fixture was not rerun.
- PR #2444's first CI run found a stale destination assertion in pfMALL's
  generator contract. It was corrected to the requested fragment, retaining
  exact destination and idempotency checks; all 33 catalog tests then passed
  locally. Initial CI result: 1 failed, 1856 passed, followed by a dependent
  missing-artifact error because later steps had been skipped.
- Deployment-helper repairs: accept Firebase's short version resource names;
  use the installed CLI's compatible AbortController for its upload client.
  Failed attempts did not publish. The extra unmodified, unpublished candidate
  `fb07d096478b2ce8` was verified against its source then deleted. No credentials
  were exported and no permission/security settings were changed.

The existing [Vote skin skill](../skillz/vote_skin/SKILL.md) records the same
outbound-link convention for other registered skins. Missing/unknown tags remain
Vote Classic. This does not implement or claim another FoundUp's skin.

## 2026-11-22 HPC contact skin

- Source: [PR #2441](https://github.com/FOUNDUPS/Foundups-Agent/pull/2441),
  implementation commit `7d42d4b5265900bee4c12430c52bfc313dc384c2`.
  GitHub integration/check status is recorded on that PR, separately from Sites.
- Existing public Vote Sites project `appgprj_6aee6646e6ac81918ac2624d5d1db413`:
  **version 11 deployed successfully** at 2026-11-21 22:47 UTC / November 22 JST.
  Site source `ba616749273598614166e054b9dfe76f75e4d8ed`, deployment
  `appgdep_6b021f68dc88819193b8c481f9330c61`.
- [Live HPC contact page](https://vote.foundups.com/contact#hpc): actual Chrome
  readback confirmed the HPC preset, 1280px supplied poster, generated script,
  preserved Hasan-for-Speaker brand link, and working regeneration. Live 390px
  screenshot confirmed the readable script controls. Audience remains public.
- Source/fixture result: **135 passed, 0 failed**; browser checks and limitations
  are in `tests/TestModLog.md`. No independent model review or physical-phone
  qualification is claimed. Provider execution is unnecessary for fixed templates.
- Publication reconciled Sites base `459f25ba56100da4510e47f23acc1e33586fb0a3`:
  Contact files, required HPC navigation assets, poster and v11 worker only.
  Other deployed pages were preserved. The deployment archive's 11 scoped assets
  matched their recorded SHA-256 hashes; no Git, credentials or provenance file
  entered the public archive. The supported helper places hosting metadata under
  `dist/.openai/hosting.json`; an initial root-only archive assertion was corrected.
- The supplied director/2,000+ coalition/callback draft is opt-in and caller
  asserted. It is not verified membership or endorsement. The separate supplied
  seat-count screenshot is not published as current election evidence.
- No automated calls, messages, model spend, new subscriptions or RSI promotion.
  The direct skin link is available; this release does not redeploy the separate
  HPC/Mall app or change its existing outbound link.

## 2026-11-09 documentation audit

The [Oversight landing contract](../oversight/README.md#phase-one-landing-contract)
is the architectural handoff. This audit records observed publication and
remaining gates. The four-entry landing is specified. The deployed root still
opens with Pain, Solution and Outcome, with the interactive maps beneath it.
The current hero offers the maps and senator directory as its two primary
actions. The model rules and staffing plan are available deeper in the staff
library. In a live 390 × 844 CSS-pixel view, the two 48-pixel action buttons
started at vertical positions 918 and 978. The 52-pixel section menu was
visible, with no horizontal overflow. At 1366 × 900, the sidebar was visible
and both actions started at 736. The planned entry sequence moves the
destinations into the first phone screen while preserving the staff brief.

| Surface | Observed result | Status |
|---|---|---|
| `oversight.mtrout.com`, `maga.mtrout.com`, `oversight.vote.foundups.com` and `oversight-hub-pwa.undaodu.chatgpt.site` | All four returned HTTP 200 with strict TLS, zero redirects and identical landing HTML after removing the identified Cloudflare insertion. Sites lists all three custom names active with SSL active. | One live Oversight v10 Site. [Release PR #2323](https://github.com/FOUNDUPS/Foundups-Agent/pull/2323) |
| `oversight.voice.foundups.com` and `oversight.voice.mtrout.com` | Google and Cloudflare public resolvers returned NXDOMAIN. Neither name appears in the Oversight Sites custom-domain list. | Proposed alias and alternate spelling, respectively. |
| `vote.mtrout.com`, `vote.foundups.com` and `vote.undaodu.chatgpt.site` | Strict HTTPS returned the Vote informational landing. The two custom hosts returned matching landing HTML after removing the identified Cloudflare insertion. The original host also returned `/coalition`, `/evidence` and `/contact`. | One live Vote v3 Site. [Release PR #2319](https://github.com/FOUNDUPS/Foundups-Agent/pull/2319) |
| `voice.houseoutis.com` | Both public resolvers returned NXDOMAIN. | Intended Voice outbound destination. Live link blocked on destination verification. |
| Play FoundUps | `foundups.com/member/` returned the Mall shell. `foundups.com/f/voteballots` and its `/app` path returned the same generic entry shell as `/f/`. Source checks found the registry record, an empty manifest `entry_url` and discoverable-only readiness. Vote was absent from the live public catalog, portfolio and member catalog projections. | Tenant activation requires an admitted entry and verified runtime. |

Both active Sites deployments returned `succeeded` and matched the clean PC
deployment mirror commits:

| Site | Project | Version and deployment | Mirror commit |
|---|---|---|---|
| Oversight | `appgprj_6aed5317a2e4819193b1fdfe340a1cea` | v10 · `appgdep_6aef1d36c44c81919941e5be20508e9a` | `4ea7134c22fe147ecc6a4c8ed7f36c95b72d1a1c` |
| Vote | `appgprj_6aee6646e6ac81918ac2624d5d1db413` | v3 · `appgdep_6aeed7c291648191a1d377c554bb04ba` | `0038b0f3d08b687a7c237e09fe2d5d5447e6b317` |

**Pass 1 — architecture and evidence.** Audited GitHub main `020a89c16`,
which adds unrelated work after the Oversight release source `92aa9951c`.
The Vote, Oversight and Mall paths inspected were identical between those
commits. Read the existing module, shell, routing, navigation, state, external
route and interior contracts. WSP 00 strict passed. The semantic HoloIndex
query returned an authority HEAD mismatch and unknown freshness. A lexical
query bound to `020a89c16` returned workspace context with unknown freshness.
Exact paths and direct source reads supplied the documentation evidence.
The earlier local Vote concatenation branch had no unique diff against the
audited main. The related Oversight release PRs were already merged.

**Pass 2 — landing and route readiness.** Strict HTTPS returned the model
House rules, House readiness package, staffing plan, hub charter, committee
operating plan, maps, roadmap, senator directory and source indexes. Sites
redirects the legacy template `.html` paths to their clean paths on the same
host. The snapshot verifier returned 155 files, 13 mirror pairs and inventory
SHA-256 `d75a8544dc1352c9e5dca2510835ea092a6824cc6adc2bfc95cff0c638e59e86`.
The prior v10 PR holds the implementation, test and mobile/offline evidence
for the deployed map. A four-entry candidate has yet to be implemented.

**Pass 3 — documentation challenge.** A House reader reaches the proposed
rule text first. A Senate reader retains distinct rules and approval paths.
A first-time public reader gets a clear Voice destination and its current
availability gate. A mobile reader's planned entry order and navigation
requirements are explicit. `git diff --check`, the ordered entry and hostname
checks, and 19 local Markdown references on changed lines passed. The future candidate
still requires independent browser and accessibility review. This slice
changes documentation only.

## Standalone Oversight staff site

The [interactive maps](https://maga.mtrout.com/explore) put decision screens
behind the landing diagram. The authority branch covers five featured
committees and selected subcommittees with individually sourced rules. The
investigation branch provides three fictional walkthroughs with a supported
payment trace, contrary evidence and an explicit point where the trail ends.
Separate coordination, witness and January 6 branches link the legal gates
and historical sources. The maps share the five-stage roadmap and publish a
[machine-readable graph](https://maga.mtrout.com/map-data.json).

The landing leads with Pain, Solution and Outcome. It dates and sources DOJ
leadership and prior representation, marks the impartiality concern as the
project's assessment, and separates the state-law referral from federal criminal
contempt. Recheck the dated leadership context whenever DOJ leadership changes.

The Oversight publication now focuses on congressional accountability.
The phone disclosure opens upward with labeled touch targets and readable
type. Desktop retains the section sidebar. The landing presents the
hub-and-spoke workflow, a sourced January 6 precedent, separate state
authority and an attorney general transition snapshot that distinguishes
provisional results from the serving office.

The [legislative roadmap](https://maga.mtrout.com/legislative-roadmap)
provides the process underneath the maps. It gives each stage an owner, decision record and
supporting template. Congressional oversight and legislative outputs can proceed
without DOJ. A separate referral needs an independently established state-law
basis, a verified receiving office and authorized disclosure. The
[senator directory](https://maga.mtrout.com/contact) provides manual state selection,
an optional device-local state suggestion, direct office dial links and private
voicemail preparation. The PWA caches the roadmap and manual directory. Precise
location and notes are never sent to the site. See the merged pull request for
the exact production version and independent browser verification.

The public build uses an explicit staff-material allowlist. It excludes
exploratory research, product branding and internal control files. The
155-file source archive and 13 mirror pairs remain the historical record.
The Vote evidence and contact releases continue on their existing Site.

## Accountability integration

The new source extends the two existing public Sites under one
`voteballots` FoundUp. The dates and deployment IDs in the previous release
section below are the v2 Vote and v5 Oversight baseline.

| Surface | Delivered in source | Acceptance boundary |
|---|---|---|
| [Oversight](https://maga.mtrout.com/) | Staff overview, legislative roadmap, senator lookup, professional documents, `/accountability.json` and `/llms.txt` | Preserved archive remains 155 files and 13 exact mirror pairs. Publication uses an explicit public allowlist. Congress, agencies and state authorities retain their independent powers and obligations. |
| [Vote evidence](https://vote.mtrout.com/evidence) | Five selected Schedule B records in four raw FEC filings, matched to their exact transaction identifiers and official candidate/committee IDs. Separate chamber roles, procedures and roll calls. | Direct contributions and forwarded individual earmarks are shown separately. UDP coverage and cycle totals remain unknown. No live lookup, estimate, ownership allegation or causal inference enters the public page. |
| [Contact Congress](https://vote.mtrout.com/contact) | Dated official directory snapshot of 539 House and Senate offices. Visitor selects a state/chamber and up to 1, 3 or 5 offices. Each dialer action and next step is manual. | Committee and leadership discovery links out to official directories. This Vote page uses manual selection. Notes and selection stay in memory. |

### Three review cycles

1. **Architecture and evidence.** The previous Oversight root had no raw
   overview or agent index. The first candidate's House, Senate and library
   links required JavaScript. Direct documents now work without it. The
   separate verifier rechecked the archive against its original checkout.
   In the existing resolver, invalid cycle input either reached the adapter
   or raised. The guard now accepts omission or an exact integer in range.
   The independent entry-point probe moved from 7/15 to 15/15.
2. **Public experience and integration.** Independent readers matched all
   five filing records and the 539 phone entries to primary sources. Vote's
   initial worker could cache a redirected response during installation. The
   repair checks exact URLs, status and media type before writing. The
   verifier exercised legacy and clean offline routes and a manually
   controlled contact queue. Browser preview checked navigation without dialing.
3. **System release audit.** The previous Oversight worker matched paths
   outside its `/web/` scope and could return another cache's response. The
   replacement uses exact scoped URLs and one cache per registration path.
   A browser replay exposed offline legacy navigation with a fragment. The
   worker now strips the fragment from its cache lookup while the original
   House and Senate routes remain in the browser address.
   The current chamber planning label and the HTTPS LinkedIn link clarify
   the original header and apex redirect. The release requires exact
   GitHub and Sites source plus public readback. Initial hosted CI caught
   two new tests missing from the generated registry. The canonical
   generator added both as collectable Vote unit tests. These review cycles
   do not establish retained autonomous improvement under WSP 48.

### Remaining gates toward 2028

The live FEC factory remains disabled and the alternate TypeScript fetch is
a stub. Before expanding public lookup, qualify the live input, missing and
stale records, amendments, refunds, duplicates and source receipts. Full
candidate totals, state/race resolution and a Mall tenant launch remain
separate work. Oversight still needs professional review and a reader
correction pilot. Validate actual installed-device update and offline behavior
in addition to worker and browser tests.

## Previous public release

**As of 7 November 2026.** Vote has a live public front door, a live Oversight
Blueprint workstream, and a live Coalition information page. The candidate and
funding application remains an internal proof of concept. Oversight and Coalition
belong to the same `voteballots` FoundUp.

### Historical features and evidence

| Surface | What shipped | Evidence |
|---|---|---|
| Vote | A responsive static landing with the Oversight entry, product readiness labels, a PWA manifest and a scoped service worker. The canonical editable source is `web/`. | [Vote](https://vote.mtrout.com/), [source and release procedure](../web/README.md), [PR #2312](https://github.com/FOUNDUPS/Foundups-Agent/pull/2312) |
| Oversight Blueprint | The refreshed public guide has a clearer House-first entry, a responsive layout, and access to the document library, research material, templates and authored instruction bundles. The Vote workstream preserves all 155 public files and 13 root/web mirror pairs. The original Sites repository retains its history. | [Oversight](https://oversight.mtrout.com/), [source and release record](../oversight/README.md), [snapshot inventory](../oversight/source-snapshot.json) |
| Coalition | An independent public charter, creator/official/community contribution paths, a private draft preview and JSON download, and general congressional contact resources. The draft stays on the visitor's device. Participation and endorsement remain unconfirmed. | [Coalition](https://vote.mtrout.com/coalition), [source and identity audit](COALITION_TAB_AUDIT.md), [PR #2317](https://github.com/FOUNDUPS/Foundups-Agent/pull/2317) |
| Internal Vote PoC | Six merged parts cover the FEC adapter, candidate resolution, funding summaries, confidence scoring, quick answers and local shell payloads. Source provenance and aggregate-to-display confidence repairs are included. The prior release recorded 398 Python tests and the earlier six-slice closure recorded 303. | [Historical closure](../../../../docs/audits/architecture/VOTE_POC_CHAIN_OBSERVATION_SNAPSHOT_PHASE1.md), [test history](../tests/TestModLog.md) |

### Historical publication and operational evidence

- **GitHub and PC.** The related Vote PRs #2275, #2282, #2289 and #2298 were
  already merged before the preservation work. PR #2312 merged the Oversight
  import and Vote front door at `ea99f53dd`. PR #2313 recorded the preferred
  addresses at `746ff5b76`. PR #2317 merged Coalition at
  `e242d126cc825f15633691333016ae476b3f813e`. At that release, GitHub main,
  PC HEAD and the local tracking ref matched. All four resulting main
  workflows passed. [Main CI](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/42343397849),
  [GitHub release commit](https://github.com/FOUNDUPS/Foundups-Agent/commit/e242d126cc825f15633691333016ae476b3f813e),
  [address PR](https://github.com/FOUNDUPS/Foundups-Agent/pull/2313)
- **Sites.** Vote version 2 deployed from mirror commit
  `aa94fb0c7c4e395c1d830322f08988ee6f8ca6f4`, deployment
  `appgdep_6aeeb92319f0819191bf2af7dcea6188`. Oversight version 5 deployed from
  `c66d22afc5795874f4020661dcadfdd69d3ad129`, deployment
  `appgdep_6aee654bd6308191a3f0bca480e9aad3`. Independent release checks matched
  all 11 Vote assets on three Vote hosts. [Vote release owner](../web/README.md),
  [Oversight release owner](../oversight/README.md)
- **DNS.** Public Google and Cloudflare resolvers returned the expected Sites
  CNAME for `vote.mtrout.com`, `oversight.mtrout.com` and `maga.mtrout.com`.
  The DNS change records also recorded ownership and hostname verification for
  the custom domains. A prior PC result traced to cached negative DNS on its
  configured VPN resolver. Coalition publication used the existing domains.
- **HTTPS and browser.** Fresh strict TLS checks returned HTTP 200 and the
  expected page on all seven addresses below. Earlier automated checks received
  Cloudflare 1010. Ordinary Windows Chrome rendered Vote and
  Oversight at desktop and 400 CSS pixels, and opened the House package.
  The Coalition release passed 114 independent draft cases. Live in-app browser
  QA at 475 CSS pixels confirmed the draft preview, download button state and
  reset. The clean route `/coalition` is verified online. The version 2 worker
  used a legacy-only cache key. Version 3 added clean-route
  offline coverage. Installed-device acceptance remains a separate gate.
  [Test history](../tests/TestModLog.md)

| Project | Preferred address | Retained addresses |
|---|---|---|
| Vote | [vote.mtrout.com](https://vote.mtrout.com/) | [vote.foundups.com](https://vote.foundups.com/), [original Sites address](https://vote.undaodu.chatgpt.site/) |
| Oversight | [oversight.mtrout.com](https://oversight.mtrout.com/) | [maga.mtrout.com](https://maga.mtrout.com/), [oversight.vote.foundups.com](https://oversight.vote.foundups.com/), [original Sites address](https://oversight-hub-pwa.undaodu.chatgpt.site/) |

## Launch Pad

The table tracks release readiness by capability. The [module roadmap](../ROADMAP.md)
owns sequencing. The registry and manifest own catalog readiness and entry
configuration. The published sites use separate origins, so each has its own
browser storage and worker scope. The shared Vote tenant route is
`/f/voteballots/app` and its data namespace is `idb_voteballots`.

| Capability | State | What remains before launch or expansion |
|---|---|---|
| Public Vote, Oversight and Coalition pages | Live | Exercise install, update and cache migration on a real phone. |
| MAGA/Oversight four-entry landing | Documented | Reuse the existing Site and routes. Verify Voice availability and complete authorized implementation and independent review before publication. [Landing contract](../oversight/README.md#phase-one-landing-contract) |
| Candidate and funding evidence app | Internal PoC | Reconcile the registry's older `SPECIFIED` / `idea` labels with the runnable PoC in a tested slice. Manifest entry remains empty and discoverable-only. Review live-adapter admission, source freshness, coverage gaps and outage behavior. Prove one neutral race/candidate evidence journey under the existing tenant with traceable sources and explicit unknowns. Then verify routing, isolation and eligibility for catalog promotion. |
| Oversight reader and review workflow | Public guide | Validate one real reader journey and one source-backed correction through accountable human review. The pinned published roadmap and instruction bundles record the original design. Treat them as historical source alongside this release record. |
| Coalition membership and editorial work | Public draft only | Choose who receives and reviews applications, what is retained, and how consent can be withdrawn. Prove an authenticated, rate-limited private intake first. Verify provider account control separately from eligibility, membership consent and role grants. Official review, revocation, moderated publishing and durable revisions/votes are future layers. [Audit](COALITION_TAB_AUDIT.md) |
| Calling, credits and AI voice | Design | The live page offers a visitor-initiated switchboard link. A separate human-controlled calling product would need an authenticated queue, retry-safe call state and provider callbacks, consent and transcript retention decisions, and an auditable credits ledger before any live voice or payment pilot. If the OpenAI voice design is resumed, the choice between existing access and a separate Vote key is open. Location/affiliation-based campaign routing is outside the launch scope. |
| Claim verification and voting | Planned | Start claim verification with a frozen historical corpus and independent evidence review. Keep public scores and real-time overlays behind calibration and abstention gates. A non-binding ballot requires its own privacy, coercion, replay and receipt validation. Registration, resilience and SmartDAO extraction remain downstream. [Claim verification design](POLITICAL_CLAIM_VERIFICATION_AND_SCORING_ENGINE.md) |
| OpenClaw, WRE and RSI | Authored bundles and bounded trials | Governed runtime admission, isolated execution and an independently reviewed work result precede activation. Establish retained improvement through repeated measurements. The prior cycle-validator proposal failed the exact-integer requirement. [Runtime trial](../../../../docs/operations/RSI_SWARM_DISPATCH.md#native-openclaw-vote-qualification--2026-11-01) |

## Decision for the next build

The next MAGA/Oversight slice follows the
[four-entry landing contract](../oversight/README.md#four-entry-landing) after
the documentation handoff. The Vote product's first public evidence journey
and Coalition intake remain separate milestones with their own acceptance
gates.
