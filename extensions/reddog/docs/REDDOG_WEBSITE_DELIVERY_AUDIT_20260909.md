# RedDog website delivery audit and work order

Date: 2026-09-09
Status: **AUDIT_COMPLETE / IMPLEMENTED_LOCALLY / LIVE_UNVERIFIED**
Owner: 0102 website delivery lane; origin: external principal 012.
Observed base: `c3666c02c1a819f8906e56f31fdc67d6ad46111d`.
Observed `origin/main`: `fb58e5279673ef9de30735ccfedc8001c3bb79d6`.
Owned branch: `feat/reddog-public-openrouter`.

These are local observation identifiers, not a claim about later remote state.
Implementation and verification rows below must be updated from actual evidence
by the delivery owner. This work order grants no resident execution authority.

## Requested outcome and scope

Connect the RedDog website surfaces on foundups.com and eSingularity.ai to
OpenRouter so visitors can understand the project and find the YUMORI.me
committee signup. Preserve the 0102/RedDog distinction: RedDog presents fast
conversation; 0102 supplies the reviewed knowledge and operating boundaries.
The principal describes a September 25 demolition-budget vote; public answers
must preserve source/date attribution and refresh this time-sensitive statement.

The existing public policy names foundups.com and eSingularity.ai. Speech
variants FoundX.com and eSingularity.org do not independently establish domain
ownership or authorize adding origins. Confirm actual redirects before exposure.

## WSP and retrieval audit

Read the master index and applicable WSP 00, 1, 10, 15, 31, 73, 81, 97, 98,
106 and 109, the RedDog documentation map, public admission contract and remote
work order, and Mosh Pit projection/gateway contracts. No WSP 110+ source was
found in the inspected framework/knowledge inventory; the index ends at 109.

The parent lane reports the WSP 00 V2 invocation failed because `torch` is
missing. Its canonical torch-free fallback opened the gate without a detector
witness. Holo owner retrieval returned `HOLOINDEX_AUTHORITY_ROOT_DIRTY`;
retain that failure, use scoped read-only `rg`/file inspection, and leave
governed Holo repair to its owning lane. Neither result proves detector-backed
awakening, current semantic retrieval, or recursive improvement.

Retrieval evaluation: broad RedDog matches include extensive generated receipts,
tests and historical audits. Start from `docs/REDDOG_DOCUMENTATION_MAP.md`, then
read current interfaces and exact functions. Historical read order is useful
continuity, not current deployment truth. The missing artifacts are live host,
provider-key readiness and public source bindings, rather than another WSP.

## Reuse decision and remaining gaps

| Boundary | Existing contract / observed gap |
| --- | --- |
| Public request | `reddog_public_policy.py`: fixed surfaces/origins, strict consent/input schemas and hard caps |
| Admission accounting | `reddog_public_session_gate.py`: AgentDB SQLite session/nonce/quota invariants; no transcript or private memory storage |
| HTTP transport | `reddog_public_http.py`: optional unmounted FastAPI router and injected `PublicSurfaceBinding` |
| Ingress | Existing Python adapter uses direct peer HMAC and ignores forwarded headers; proxy attribution requires deployment proof |
| Failure accounting | Ambiguous calls keep their reservation; process restart does not prove a provider call terminated |
| Model | Public-only OpenRouter responder and actual deployed credential binding remain unverified |
| Mosh Pit | `project_mosh_pit()` selects explicit disclosure views from an authorized snapshot; production public source remains absent |
| Stakeholder activity | Existing eSingularity `/api/mosh-pit` is separately gated and must not serve anonymous FAQ context |

Implement the first layer on the existing website host. A proposed Cloudflare
Worker adapter may use the existing Site D1 binding for **public admission
accounting only**, with shared atomic budgets across both website origins. D1
is not AgentDB and SQL compatibility is not proof that the Python gate's
transaction behavior carries over. Verify the migration and D1 atomicity,
concurrency, replay, expiry, timeout and restart invariants before enabling it.
Do not introduce a second activity store or replicate principal memory into D1.

The bounded public adapter is the chosen alternative to attaching the private
resident OpenClaw/WRE execution stack. It meets the website Q&A outcome with
`CHAT / FAST / NONE`. Future private continuity and live authorized recall retain
their existing independent gates.

Planning assessment under WSP 15: C=3, I=5, D=5, Impact=5, total 18/P0. This is
a planning score, not a signed allocation receipt. Sequence public context and
admission/provider binding before browser activation; resident execution is not
a dependency of this FAQ.

## Public project knowledge boundary

The parent lane reports that project documents 01 and 03 were verified readable
by anyone. Document 02 and the private Mosh Pit log are not public inputs. Carry
their reviewed public summary only; never fetch the private log or reuse its
server credential for the guest responder. Readability is disclosure evidence,
not verification of every factual or financial claim in a document.

The reviewed public packet must preserve source identifiers, revision/review
time, fact/proposal attribution, relevant project links and committee signup.
Do not publish unreviewed personal contact information or private correspondence.
Label approved activity summaries as snapshots until an actual public Mosh Pit
source, authorization and freshness check are connected. Plans, estimates and
012-reported events must not become confirmed outcomes through summarization.

## Delivery ledger and acceptance work

| Work | State at this audit / required evidence |
| --- | --- |
| Canonical public caps and SQLite gate | Source exists; prior isolated tests are not D1 or deployment evidence |
| Website Worker and public provider responder | Implemented; fixed server-only OpenRouter request, no tools |
| Reviewed public knowledge packet | Public 01/03/master snapshots + reviewed summaries; revision yumorime-public-2026-09-09.1 |
| D1 migration and quota parity | Generated migration and real SQLite transaction checks pass; production D1 pending |
| Foundups.com client | Shared client implemented; production deployment and canary pending |
| eSingularity.ai client | Shared client implemented; production deployment and canary pending |
| Deployed OpenRouter key / model route | Unresolved; no value is stored in this audit |
| Live public Mosh Pit | Unconnected; curated public summary only |
| Private resident memory / execution | Outside this public delivery slice |

Required acceptance follows WSP 97 Section 1.2.2. Reuse the public-surface test
inventory, add actual backend parity evidence, and verify one bounded successful
provider reply and denial/failure behavior through each deployed website.
Model output must render as text; browser input must not choose models, routes,
context sources or tools. Missing configuration must return unavailable rather
than inventing a reply or falling back to private infrastructure.

Separate source implementation, tests, merge, deployment and live verification
in later updates. A configured model is a public dialogue deployment binding,
not an independently promoted AI Gateway champion. Neither a reply nor a Lick
receipt proves identity, deep resident cognition, or work execution.

## Framework amendment and recovery record

The focused changes add WSP 97 public delivery evidence, clarify WSP 73 public
dialogue, scope WSP 106 protected gateway authentication, and add WSP 15
same-outcome complexity/dependency comparison. Existing scoring, caps,
priorities, core principles and effect admission remain unchanged. WSP 00 and
WSP 10 need no change for this slice.

Classification: WSP 81 Section 3.2 section additions/minor semantic clarifications
under the principal's requested WSP improvement sweep. Each numbered source is
mirrored exactly to its existing `WSP_knowledge/src/` counterpart. The delivery
owner must include base, mirror equality, validation and recovery in the
framework ModLog and focused PR record. No archive duplicate is needed.

Validation: inspect the focused diff, require `git diff --check`, and verify
byte equality of all four framework/knowledge pairs. Recovery uses the owned
branch/checkpoint and a reviewed revert under WSP 10; never reset another lane.
This audit itself is operational documentation and is not a numbered WSP mirror.

Related: [public admission](REDDOG_PUBLIC_SURFACE_ADMISSION.md),
[remote integration work order](prompts/WSP97_REDDOG_PUBLIC_SURFACE_REMOTE_PROMPT.md),
[Mosh Pit contract](MOSH_PIT_WAVE_MVP.md).

## Implementation verification checkpoint

Nine new frontend tests plus seven existing Mosh Pit tests pass. They use actual
SQLite transactions behind a D1-shaped adapter, not production D1. The dedicated
client script passes loss/replay/withdrawal checks. 41 existing Python checks and
TypeScript pass. Review caught and fixed a deleted-session admission race,
withdrawal-before-provider race, weak actor-claim typing and misleading health
wording. Health now reports configuration presence only.

OpenRouter and an independent subject secret remain absent from Site settings.
The model binding, ingress proof, production migration, live provider, Firebase
publishing and live Mosh Pit source remain unresolved. Provider abort limits
local transports; it is not proof remote generation stopped. Daily reservations
are not refunded, and crashed busy slots require explicit operator recovery.

See `modules/foundups/esingularity/docs/REDDOG_PUBLIC_RUNTIME.md` for the exact
public contract, source-refresh path, canaries and recovery instructions.

Production build: PASS (`build-site.mjs`, Vinext/Vite five environments). The
first attempt waited for uncached font downloads and was cancelled; the successful
build reused the unchanged site's existing font cache with local CSS paths
rewritten. No dependency source or font selection was modified for that recovery.

GitHub push of checkpoint `fbd66ae5c8281d574ec203ea10090cf658c4e035` to
`FOUNDUPS/Foundups-Agent:feat/reddog-public-openrouter` was rejected by automatic
approval review: repository/project material could disclose private organizational
data, and specific external publication authorization was not established. No
GitHub PR or merge occurred. Do not retry via another transport without resolving
that rejection. The local checkpoint remains available for review. Native Site
preparation contains only the requested frontend, independently of that GitHub
publication. Existing package versions were unchanged by the lockfile update
(83 added dependency entries, zero existing version changes).

## Saved release candidate

The existing native eSingularity Site now has **version 27**, saved but not
deployed. Source repository push succeeded to its existing Sites-owned source
remote; exact commit `8f2d5283687c8f4f053f2ee3a25db77b99498349`. Saved version ID:
`appgprj_6a917b21b1a4819181a61738ed5274a5~appgver_d6c1d03fdc088191b2d197b82a8f441d`.
The archive was built from a clean `git archive` of that commit, passed all five
Vinext build phases, and contains Worker output, public assets, hosting metadata
and the generated D1 migration. It excludes environment files and Git history.
No production deployment, provider spend, migration or runtime-secret mutation
was performed. The live site remains on its previous version.

Remaining operator inputs: the server-side OpenRouter key and selected model,
Firebase `foundupscom` publishing connection, and explicit resolution of the
automatic GitHub publication rejection. After configuration, verify deployed
D1/ingress and real replies before claiming operational status. The native Site
save does not publish the blocked GitHub branch or expose repository history.

## Resumption and security review

012 reported a Work UI “something seems to have gone wrong” screenshot and
asked to continue under WSP 71 without exposing credentials. The screenshot has
no error code/request ID. Available tools do not expose the affected Work/iOS
client or backend incident trace, so its root cause is **undetermined**. The
local source checkpoint and native Site version 27 both survived. Git status,
saved-version provenance and connector availability were rechecked, consistent
with [official recovery guidance](https://learn.chatgpt.com/docs/reference/troubleshooting).
The earlier font-network cancellation and GitHub auto-review denial are known
separate events; neither is established as the screenshot's cause.

WSP 00 gate recheck passed without a new detector witness. Holo owner retrieval
still returned `HOLOINDEX_AUTHORITY_ROOT_DIRTY`, freshness UNKNOWN and index gap
true. Scoped read-only retrieval remains the declared fallback. No owner repair
or reindex was attempted from this branch.

The connected GitHub account was verified as an administrator of the existing
**public** `FOUNDUPS/Foundups-Agent` repository, with push permission. This is new
evidence addressing the earlier unverified-destination rejection; any retry
must still pass automatic approval review, using the same intended destination.

Offline `detect-secrets` 1.5.0 scanning used `--no-verify`: no suspected credential
was sent to an external verifier. It scanned 88 unique changed blobs across the
unpublished history and text output in the exact version-27 deployment archive.
Thirty findings were reviewed: unchanged public examples/publishable config,
explicit synthetic fixtures, source checksums, generated module identifiers,
unchanged framework code, and the generated server-only `prerenderSecret`. That
generated build secret was absent from browser assets and was not displayed.
No new runtime credential was found in release source or browser assets. This
is a scoped heuristic scan, not a guarantee about all historical repository data.

An earlier raw Site diagnostic exposed a Sites sign-in bypass token in tool
output. No token value is reproduced here; it was not intentionally written to
source or the release bundle. Token-bearing result caches were cleared. Further
Site/environment diagnostics use explicit allowlisted fields only, never whole
connector results. The Sites token operation explicitly requires a request to
rotate/generate that token; rotation remains pending that request. Do not claim
it was rotated or reuse the exposed token for testing.

The resumed review also found and fixed two reproducible failures: a read after
admission committed could strand four provider slots before any call began; and
an aborted errored stream could reject a detached cancel promise. Exact-slot
cleanup and caught cancellation now have regression coverage. Existing lint
failures were corrected, and the project CI now runs the new boundaries.
18 frontend tests, 41 Python tests, transport checks, lint and types pass.
OpenRouter key/model, authenticated Firebase publishing, production D1/ingress
and live provider replies are still unverified; none is inferred from local tests.

### Resumed release candidate: version 28

The corrected frontend was pushed to the existing native Site source repository
and saved as **version 28**, still undeployed, from exact commit
`72aa995c566334d60341915f847c27ae09f5bc76`. Saved version ID:
`appgprj_6a917b21b1a4819181a61738ed5274a5~appgver_92524ac268b48191be4a61499ea90814`.
The clean build was extracted from that Git commit and matched every canonical
frontend file byte-for-byte. Build and archive validation passed. The resumed
source/archive scan had 25 reviewed findings; only the newly generated
server-only prerender secret differed from the prior scan. A synthetic positive
control was detected and then deleted. No verification requests or actual
provider calls were made. A local Miniflare D1 smoke probe did not return and
was cancelled (exit 130); it supplies no D1 conformance evidence.

The current evidence remains 18 frontend checks plus 41 Python checks, the
shared transport checks, lint, TypeScript and production build. Runtime key/model,
Firebase publishing access, token rotation, deployed D1/ingress and real replies
remain the activation gates.
