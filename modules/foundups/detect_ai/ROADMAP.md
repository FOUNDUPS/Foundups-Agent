# AmIBot - Roadmap

Status: planning_reference; SPECIFIED_NOT_IMPLEMENTED; TOKEN_DEFERRED.
Display name: AmIBot. Tagline: Can you detect AI? Stable internal ID: `detect_ai`.
Technical decisions and primary sources: [chat/PWA/safety research](docs/CHAT_PWA_SAFETY_RESEARCH.md).

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

The 15/P1 package scope qualification corrects six dependency rows: conservative
G1 serialization, G2 waiting for all writers, and final success reporting after
publication. Static active root-overlap pairs fall from12 to0; all13orders and
scores remain. Controlled failures can be reported without downstream completion.
G0 still must qualify shared interfaces/hard prerequisites, exact file scopes,
typed intake/Skillz, model/runtime bindings, WRE admission and independent verifier.
Preserve registered `detect_ai`; do not replay new-identity scaffolding.
Reconcile `/f/amibot` through the canonical shell owner before publication.

System prioritization stays in the [root RSI roadmap](../../../ROADMAP.md) and
existing backlog. The historical14/P1 registry integration is closed; this
package-only repair is separate. No build, runtime bootstrap, model inference,
device acceptance or deployment is claimed. Re-observe and rescore after closure.
