# Vote release accounting and launch checklist

## Standalone Oversight staff site

The Oversight publication now focuses on congressional accountability.
The phone disclosure opens upward with labeled touch targets and readable
type. Desktop retains the section sidebar. The landing presents the
hub-and-spoke workflow, a sourced January 6 precedent, separate state
authority and an attorney general transition snapshot that distinguishes
provisional results from the serving office.

The current source promotes the [legislative roadmap](https://maga.mtrout.com/legislative-roadmap)
to the main staff action. It gives each stage an owner, decision record and
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

## Built and verified

| Surface | What shipped | Evidence |
|---|---|---|
| Vote | A responsive static landing with the Oversight entry, product readiness labels, a PWA manifest and a scoped service worker. The canonical editable source is `web/`. | [Vote](https://vote.mtrout.com/), [source and release procedure](../web/README.md), [PR #2312](https://github.com/FOUNDUPS/Foundups-Agent/pull/2312) |
| Oversight Blueprint | The refreshed public guide has a clearer House-first entry, a responsive layout, and access to the document library, research material, templates and authored instruction bundles. The Vote workstream preserves all 155 public files and 13 root/web mirror pairs. The original Sites repository retains its history. | [Oversight](https://oversight.mtrout.com/), [source and release record](../oversight/README.md), [snapshot inventory](../oversight/source-snapshot.json) |
| Coalition | An independent public charter, creator/official/community contribution paths, a private draft preview and JSON download, and general congressional contact resources. The draft stays on the visitor's device. Participation and endorsement remain unconfirmed. | [Coalition](https://vote.mtrout.com/coalition), [source and identity audit](COALITION_TAB_AUDIT.md), [PR #2317](https://github.com/FOUNDUPS/Foundups-Agent/pull/2317) |
| Internal Vote PoC | Six merged parts cover the FEC adapter, candidate resolution, funding summaries, confidence scoring, quick answers and local shell payloads. Source provenance and aggregate-to-display confidence repairs are included. The current Python suite passed 398 tests. The earlier 303-test count is the six-slice closure baseline. | [Historical closure](../../../../docs/audits/architecture/VOTE_POC_CHAIN_OBSERVATION_SNAPSHOT_PHASE1.md), [current test history](../tests/TestModLog.md) |

## Publication and operational evidence

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
  reset. The clean route `/coalition` is verified online. The current worker's
  exact shell allowlist names `/coalition.html`; clean-route offline behavior
  still needs a fix and an installed-device check. [Test history](../tests/TestModLog.md)

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
| Public Vote, Oversight and Coalition pages | Live | Resolve Coalition clean-route offline coverage if offline use is a product requirement. Exercise install, update and cache migration on a real phone. |
| Candidate and funding evidence app | Internal PoC | Reconcile the registry's older `SPECIFIED` / `idea` labels with the runnable PoC in a tested slice. Manifest entry remains empty and discoverable-only. Repair exact election-cycle validation and review live-adapter admission, source freshness, coverage gaps and outage behavior. Prove one neutral race/candidate evidence journey under the existing tenant with traceable sources and explicit unknowns. Then verify routing, isolation and eligibility for catalog promotion. |
| Oversight reader and review workflow | Public guide | Validate one real reader journey and one source-backed correction through accountable human review. The pinned published roadmap and instruction bundles record the original design. Treat them as historical source alongside this release record. |
| Coalition membership and editorial work | Public draft only | Choose who receives and reviews applications, what is retained, and how consent can be withdrawn. Prove an authenticated, rate-limited private intake first. Verify provider account control separately from eligibility, membership consent and role grants. Official review, revocation, moderated publishing and durable revisions/votes are future layers. [Audit](COALITION_TAB_AUDIT.md) |
| Calling, credits and AI voice | Design | The live page offers a visitor-initiated switchboard link. A separate human-controlled calling product would need an authenticated queue, retry-safe call state and provider callbacks, consent and transcript retention decisions, and an auditable credits ledger before any live voice or payment pilot. If the OpenAI voice design is resumed, the choice between existing access and a separate Vote key is open. Location/affiliation-based campaign routing is outside the launch scope. |
| Claim verification and voting | Planned | Start claim verification with a frozen historical corpus and independent evidence review. Keep public scores and real-time overlays behind calibration and abstention gates. A non-binding ballot requires its own privacy, coercion, replay and receipt validation. Registration, resilience and SmartDAO extraction remain downstream. [Claim verification design](POLITICAL_CLAIM_VERIFICATION_AND_SCORING_ENGINE.md) |
| OpenClaw, WRE and RSI | Authored bundles and bounded trials | Governed runtime admission, isolated execution and an independently reviewed work result precede activation. Establish retained improvement through repeated measurements. The prior cycle-validator proposal failed the exact-integer requirement. [Runtime trial](../../../../docs/operations/RSI_SWARM_DISPATCH.md#native-openclaw-vote-qualification--2026-11-01) |

## Decision for the next build

If the priority is the Vote product, choose one public evidence journey as the
next milestone. It uses the six components already built and makes the jump from
an informational site to a working evidence product measurable. If the priority
is operating a coalition, first choose an accountable intake reviewer and agree
on data retention and the first moderation workflow. That is a separate
milestone. An Oversight reader and correction pilot can inform either path.
