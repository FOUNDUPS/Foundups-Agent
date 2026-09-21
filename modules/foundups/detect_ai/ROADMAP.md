# AmIBot - Roadmap

Status: planning_reference; SPECIFIED_NOT_IMPLEMENTED; TOKEN_DEFERRED.
Display name: AmIBot. Tagline: Can you detect AI? Stable internal ID: `detect_ai`.
Technical decisions and primary sources: [chat/PWA/safety research](docs/CHAT_PWA_SAFETY_RESEARCH.md).

## Public discovery alias contract — 2026-09-21

**Decision, specified only:** preserve canonical `detect_ai`, `/f/detect_ai`,
`/f/detect_ai/app` and `idb_detect_ai`. Under WSP104 sections3/7/9, an alias is
shell-owned pre-entry discovery input, never a second FoundUp or tenant route
family. Canonicalization must finish before tenant landing/context rendering.
This10/P2 contract does not change WSP104 or implement/activate `/f/amibot`.

The existing shell already searches display names and emits canonical ID links.
That is sufficient for ordinary AmIBot discovery after separate listing approval,
but does not fulfill012's literal `/f/amibot` request. Renaming `detect_ai`, adding
a second registry entry, deriving an alias from prose/display names, or mounting
an app under an alias would break the stable identity boundary.

| Existing owner | Finite follow-on contract |
|---|---|
| [Registry schema](../foundup_registry.schema.json) | Optional explicit `public_discovery_alias`: one lowercase slug matching `^[a-z0-9_]+$`, with no inferred alias. Absence preserves legacy behavior; empty/null/non-string/invalid values reject. No implicit normalization or alias chain. |
| [Projector](../public_catalog_projector/src/projector.py) | Validate reservations across ALL registry IDs and supplied aliases before filtering; reject canonical/self/other-alias collisions. Emit the optional alias only for portfolio-eligible entries whose public_surface_status is explicitly discoverable/listed/promoted. Missing/hidden status emits no alias. Validate exact derived values and omissions through existing validation paths. |
| [Public shell](../../../public/f/index.html) | Preserve the app/deep-app membership handoff BEFORE catalog fetch. Resolve an alias only for its exact landing root, optionally one trailing slash; reject other alias subpaths. Decode once, reject malformed/encoded separators, validate projection ambiguity, and use only a single eligible canonical target. |
| Shell canonicalization | On alias success, use same-origin `history.replaceState` to `/f/{canonical_id}` before assigning canonical foundupId and calling renderEntry/populateConciergeContext. Drop alias search/hash; never use them as identity/redirect targets. If canonicalization fails, render no tenant. No network redirect, alias app mount, tenant-specific rewrite, member-catalog read or alternative cache/storage namespace. |
| [Existing projector tests](../public_catalog_projector/tests/test_projector.py) and [route tests](../../../public/member/tests/test_route_contract_bridge.py) | Extend synthetic fixtures and execute actual parser/resolver code in an isolated browser/JS harness. Static substring assertions alone cannot prove alias identity or gate order. Keep no-transitional-redirect and canonical-URL requirements; do not weaken them to pass. |

**Visibility precision:** the existing projector filters portfolio_status only;
it does not independently filter public_surface_status. The additional explicit
visibility check applies to alias emission, not a silent rewrite of legacy
canonical projection policy. Current hidden/not_portfolio `detect_ai` remains
absent. Alias support alone cannot publish AmIBot or build its application.

**Required oracles:** legacy no-alias projection/output unchanged; a valid
synthetic alias resolves once to its canonical ID in URL, rendered label and
concierge context; canonical and alias collisions (including hidden IDs), empty,
null, duplicate, encoded-separator, malformed and unknown inputs fail closed;
hidden/missing-visibility/ineligible targets expose no alias; canonical/alias
app and deep-app paths reach the existing member gate before any fetch; failed
history replacement does not render; no member reads, remote fetches or real
registry writes in the fixture. Schema accepts/rejects the same alias grammar.

**Next source slice:** C4/I2/D2/Impact2 = **10/P2** for one reusable optional alias
capability in the five linked source/schema/test owners. Complexity reflects
cross-language identity and validation; importance/impact stay2 because current
display-name discovery exists and production data remains unchanged. Add no new
module, skill, identity, scheduler or fixture-only copy of the resolver. The raw
[registry loader](../src/foundup_registry_loader.py) already retains optional
fields as dictionaries; it needs no alias indexing or authorization change.

PR1792's schema overlap adds only brand_context_path; preserve that independent
hunk and refresh ownership before source work. PR802/1792/1822 registry changes
remain external; no production registry/catalog/manifest edits belong to this
slice. Runtime admission, independent application verification, public listing,
deployment and actual phone acceptance remain separate gates. The source task
is finite and needs no further generic planning pass unless fresh evidence changes.
If actual-inline JS tests add process capability, use the existing test-registry
generator/check and name only the affected derived record; do not leave metadata
stale. New functions stay<=50lines; local executable additions are bounded to100
lines each in the inherited oversized shell/projector, without unrelated rewrites.

PR1839's prototype qualification merged as `f0fa051a`; all ten PR checks and both
main workflows passed. This contract uses static reads/JSON/hash checks and an
independent source review, not tests or a live worker execution. One adjacent
read-only loader inspection corrected an assumption about typed field storage.
The lexical Holo bundle binds current main with UNKNOWN freshness/index gap;
older routing/projector phase1 prose is stale against current source. Missing
module test/memory readmes were recorded without creating placeholders.
Evidence, ranked comparison and the executable-scope candidate are attached to
[the existing RSI backlog](../../../docs/roadmaps/rsi_swarm_backlog.json).

## Layered delivery

| Layer | Deliverable | Required gate |
|---|---|---|
| Intake and research | Eight WSP 109 artifacts; platform comparison; PWA and safety design | Documents reviewed; unresolved checks remain explicit |
| Registry onboarding | Existing `detect_ai` candidate registered; declarative manifest and interface present | Schema, loader, namespace and truth checks; hidden/unbuilt/token-deferred; no runtime or catalog admission |
| Preflight | Source-bound retrieval, catalogs, dependencies, existing auth/transport/model owners | No duplicate or incompatible owner; pinned dependencies and license/security review |
| POC 1 - human chat | Invite login; one clean 18+ queue; random human-human pairs; mobile chat; report/block/leave | Real two-browser test; server authorization; moderation before delivery; adult cohort admission; available operator |
| POC 2 - detection game | Approved server-hosted small model; randomized human/AI assignment; locked verdict/confidence; coordinated reveal; provisional points | No truth leakage or silent AI replacement; idempotent scores; defined safety/disconnect outcomes |
| POC 3 - phone acceptance | Installable PWA shell; reconnect/resume; keyboard and safe-area layout; offline notice | Real iPhone and Android tests; stale messages rejected; no private cache; no mid-round forced update |
| Prototype | Versioned model comparisons; agent judges; authenticated rankings; calibration; consented exports | Existing POC pilot gate; independent security/privacy review; measured operating cost |
| MVP | Public clean-chat service; dependable matching; support and incident process; published method | Public age/access assessment, tested moderation capacity, costs and rollback; reward gate separate |
| Optional mature lane | Separate opt-in 18+ mature/NSFW policy and queue | Strong age assurance, jurisdiction/provider review, privacy and safety tests; disabled until all pass |
| Optional local AI | WebLLM or compatible Transformers.js checkpoint in foreground practice | Device probe, explicit download consent, memory/latency tests; separate unverified practice results |
| Optional distribution | Discord Activity or other wrapper | Same backend and scoring authority; no duplicate product or automatic permission inheritance |

The POC remains incomplete until human chat, model rounds and actual phone acceptance work together. A mock interface, documentation tests or a static preview does not satisfy it. The existing pilot target of 20 consenting adults and 100 valid rounds remains a usability target, not a superiority claim.

## Safety cannot be postponed beyond real participants

Clean chat is the only enabled initial policy: no profanity, sexual chat, harassment, threats, hate, scams or personal-data solicitation. All participants in the pilot are adults admitted through a documented process. An 18+ checkbox is not verified age, and a clean-content label does not make stranger chat suitable for children.

Require server-side filtering of human and AI messages before delivery; rate/length limits; plain-text rendering; no uploads or active links; reporting, blocking and leaving; non-rematching blocked participants; a moderation operator and queue kill switch. Hold delivery if moderation is unavailable. No filter is guaranteed to catch every harmful message.

The mature lane is a roadmap goal, not an unmoderated exception. Sexual-content permission is a separate unresolved policy/legal/provider gate, not automatically included in mature language. Under-18 participation would require a separate safeguarding design and is not enabled by this roadmap.

## Independent future gates

Token rewards remain deferred. Practice XP, benchmark skill and economic contributions are separate; no promised conversion or automatic payout. Reuse existing ledger/governance owners after authority, budget and verification checks.

Local AI stays out of ranked blinded trials: model downloads or execution on the judge's own phone can reveal assignment, and client code/results are user-controlled. A future volunteer device pool needs a separate provenance and integrity design, not a local-compute flag on ranked rounds.

Next bounded work remains `DETECT_AI_PREFLIGHT_AND_POC_CONTRACT_PHASE1` in issue
#1750. Registration merged in PR1751 (`f7307291`); all eleven PR checks and three
main workflows passed. PR1832 (`e3753a65`) closes existing public-route test drift:
48 local/independent cases and all ten PR checks passed; both main workflows passed.
Neither closure implements the public alias or admits runtime execution.

PR1833 (`1571ec55`) closes the15/P1 package scope correction; all ten PR checks
and both main workflows passed. Six dependency rows were corrected: conservative
G1 serialization, G2 waiting for all writers, and final success reporting after
publication. Static active root-overlap pairs fall from12 to0; all13orders and
scores remain. Controlled failures can be reported without downstream completion.
G0 still must qualify shared interfaces/hard prerequisites, exact file scopes,
typed intake/Skillz, model/runtime bindings, WRE admission and independent verifier.
Preserve registered `detect_ai`; do not replay new-identity scaffolding.
Reconcile `/f/amibot` through the canonical shell owner before publication.

System prioritization stays in the [root RSI roadmap](../../../ROADMAP.md) and
existing backlog. The historical14/P1 registry integration is closed; this
package-only repair is closed. Closed15/P1 existing-module route qualification
confirms WRE consumer -> WRE executor, a fresh dry-run default and blocked live
authoring; unqualified build/extract can block before simulation; the older extraction helper is not this route. Existing ContextBundle
preview attachment is implemented. See the package for exact owner/test limits,
validation-only model admission. PR1838 separately closes consumer/singleton
force-dry isolation with245 overlapping local/independent cases and passing CI. No build, runtime bootstrap, model inference, device acceptance or
deployment is claimed. Re-observe and rescore after closure.
