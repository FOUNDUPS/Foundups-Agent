# R25 — Consented 012 / RedDog feedback into governed tickets

Current validation scope (012 correction, 2026-09-13): this work first qualifies feedback behavior using synthetic participants, activity/consent records and a dedicated test FoundUp. The [latest system scope](../../ROADMAP.md#rsi-validation-scope-internal-workflows-and-dedicated-fixtures) also permits selected early-stage FoundUps/repositories as test workloads while protecting YUMORI/eSingularity and reserved lanes. Later cohort delivery must satisfy this packet's existing consent, activity, runtime and outreach authority; eligibility alone is not permission to message participants.

Date: 2026-09-11. Status: `SPECIFIED_NOT_IMPLEMENTED`. Parent: [system roadmap](../../ROADMAP.md). Registry: [planning backlog](rsi_swarm_backlog.json). Architecture decision: [hybrid tickets, teams and feedback](../architecture/REDDOG_HYBRID_TICKET_SWARM_FEEDBACK_MODEL.md). This packet is not a work order, a message-send instruction or a delegation of voting authority.

## Outcome

012 can describe a problem or suggestion to their own RedDog. The deep 0102 loop retrieves the applicable WSPs and current FoundUp evidence, checks duplicates, records a versioned proposal, and prepares a bounded ticket. Other eligible RedDogs may present that proposed change to their own 012s **only while those principals are actively engaged with the same FoundUp**, the change is relevant, and feedback/disclosure permission is current. Scoped summaries, dissent and corrections improve the proposal. Actual accepted work returns a truthful result to the originating conversation.

Feedback is optional input. It cannot authorize runtime mutation, create technical verification, mint rewards or count silence as approval. The default is one FoundUp and one principal; multi-principal consultation is a later slice. Cross-FoundUp consultation requires its own federation/scope admission.

## Active engagement is required at delivery

Select and deliver only when all conditions hold: authenticated principal/FoundUp scope, fresh evidence of meaningful participation in that FoundUp, relevance to that activity, current feedback/disclosure permission, and available attention budget. Recheck immediately before asking; earlier eligibility does not justify a prompt after activity expires or participation is paused.

For the first pilot, use an explicit active FoundUp interaction/context already supplied by the supported client. Later policies may admit recent use, contribution, review or advice within a declared freshness window. Define the activity source, qualifying events, expiry and pause semantics in the existing owner contract before implementation. Mere account existence, following, historical membership, token balance, an open idle tab or activity in a different FoundUp is insufficient. Do not manufacture qualifying activity with background agent messages.

Prefer matching pending relevant proposals when the principal next actively uses the FoundUp or discusses it with their RedDog. Do not wake inactive principals, send unrelated alerts or continuously poll every RedDog. If eligibility is absent or stale, skip/defer the prompt and record no response as unknown. Deduplicate by principal, proposal version and permitted consultation window.

Example at an appropriate interaction boundary: “This FoundUp is considering moving the next-action button onto this screen. Would that help your workflow, or get in the way?” Explain that it is a proposal, preserve the answer's meaning, and allow dismissal without repeated prompting. This is proposed product behavior, not a message sent by this packet.

## Connection to CABR / 3V

The proposed mapping is **active participant feedback → V1 Validation evidence → independent V2 Verification → V3 Valuation under CABR policy**. These are evidence responsibilities, not new runtime enum values or an automatically advancing pipeline.

| 3V role | R25 contribution | Required boundary |
|---|---|---|
| V1 — Validation | Active affected 012s assess whether the proposed change solves a real problem, improves their workflow, or introduces a constraint. Record relevance, dissent and sample coverage. | A useful feedback summary can support, revise or challenge a proposal. Popularity is not sufficient validation and nonresponse is not agreement. |
| V2 — Verification | Independent evaluators check the actual artifact, requirements, regression tests and observed outcome; verify feedback provenance/scope separately. | A verified origin does not make an opinion technically true. V1 agreement does not set `verification_complete` or count as an independent technical verifier. |
| V3 — Valuation | Admitted contribution/participation evidence and independently verified outcomes inform benefit assessment under the existing CABR/PoB contract. | No automatic score increment, reward eligibility or payout from a favorable answer. Valuation and settlement require their own evidence and owners. |

[WSP 29](../../WSP_framework/src/WSP_29_CABR_Engine.md) §2.3 names community feedback as social-impact evidence; §2.4 defines participation inputs. [WSP 26](../../WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md) §4.10 describes engagement signals including advice. Those specifications support this connection, but the response must retain its type and meet the owning contract before contributing to a score. Activity eligibility controls whom to ask; it does not assign voting weight or require a financial stake.

Current integration gap: [FAM CABR hooks](../../modules/foundups/agent_market/src/cabr_hooks.py) collect task metrics; the [simulator estimator](../../modules/foundups/simulator/ai/cabr_estimator.py) accepts aggregate participation counts and includes placeholder governance/cross-FoundUp terms. The [bridge scoring seam](../../modules/communication/moltbot_bridge/src/cabr_scoring_engine.py) is review-only and explicitly does not establish verification, CABR readiness or payout readiness. A consented, activity-bound feedback receipt is not an already-proven input to these paths. R25 must map it into the existing owners with typed evidence and tests; it must not relabel a survey answer as verified work or bypass R21's CABR truth reconciliation.

## Existing owners and dependencies

Reuse the [dual-loop sequence](../architecture/REDDOG_DUAL_LOOP_COGNITION_ARCHITECTURE.md), [Memex boundary ADR](../adr/ADR_REDDOG_FOUNDUPS_SECOND_BRAIN_BOUNDARY.md), existing authenticated conversation scope/session contracts, [learning-candidate projection](../../modules/communication/moltbot_bridge/src/foundup_memex_learning_candidate.py), WRE work-order intake, AgentDB and FAM task linkage. R22's existing product owner owns client/service delivery. Do not build a second personal memory system, federation server or independently mutable ticket queue.

Integrated ticket execution depends on R06, R09 and R16. R22's supported conversation adapter is required before claiming live end-to-end product delivery. R21 applies before claiming production CABR/3V feedback scoring; R24 applies to qualified team/reward claims; R11 applies to retained verified-outcome claims. R04 applies where the selected authority requires exact runtime closure. R25-A design and synthetic proof can proceed before these integrations; no new authority is inferred from that partial progress.

WSP 15 preliminary estimate: complexity 4, importance 4, deferability/urgency 3, impact 4; total 15/P1. This does not displace Wave 0 blockers. Proposed ownership: existing RedDog conversation owner plus FoundUp Memex/WRE integration owner, with independent privacy/verification review.

## Contract mapping required before implementation

Map these requirements to the existing contracts and enumerate only genuinely missing fields:

- Originating conversation/principal scope, destination FoundUp, source revision, proposal ID/version, observation timestamp, purpose and expiry.
- Distinct evidence types: reported preference, observed behavior, model inference, verified fact and formal authorization. A correction or supporting majority cannot silently change a type.
- Explicit disclosure permission and minimum permitted summary; same-FoundUp active-engagement evidence, its source/event/revision/time/expiry and delivery-time recheck; cohort eligibility, recipient cap, attention/frequency budget, response deadline and pause/opt-out/revocation behavior. Participation is optional and private source material stays with its owner.
- A typed V1 feedback receipt linked to the proposal version; any later V2 verification and V3 valuation references remain distinct. Preserve provenance, contradiction, sampling limits and supersession without duplicating a signal across receipt retries or counting the same contribution twice.
- Correlation/deduplication across repeated suggestions, multiple RedDogs representing one principal, retries and delivery acknowledgments. Authenticated identity is not proof that a sample represents all affected people.
- Supporting and contradicting evidence, version supersession, minority/affected-cohort constraints and unanswered questions. Model-generated speculation must not become a human response.
- Proposal-to-existing-ticket link, objective, fixed acceptance, budget and independent verifier. The proposal remains non-executable until normal work admission.
- Outcome receipts and disclosure-safe attribution back to the original conversation: proposed, declined, admitted, running, rejected, accepted, activated or rolled back only when supported. Late results must not overwrite newer context.

## Incremental slices and acceptance

### R25-A source qualification — 2026-09-20

At main `daae91db04088bc49ddde97ee972299165e1d35d`, the existing components pass
89 focused tests. A separate disposable replay passes 20 boundary checks and
creates **zero R25 feedback proposals**. R25 remains `SPECIFIED_NOT_IMPLEMENTED`:
the contract mapping is complete; a permissioned feedback-to-proposal path is
not implemented. The replay uses synthetic records and fixture databases only.
It is neither a live OpenClaw/Hermes run nor retained RSI improvement.

| Requirement | Existing owner and reusable behavior | Missing R25 connection |
|---|---|---|
| Principal, conversation and FoundUp | [Conversation scope](../../modules/communication/moltbot_bridge/src/reddog_conversation_scope_contract.py) binds authenticated identity, authorized FoundUp, revision and record digest. [Work context](../../modules/communication/moltbot_bridge/src/reddog_conversation_work_promotion.py) checks exact principal/FoundUp, current revision, expiry and grounded resident intent. | A principal-only scope cannot become FoundUp scope. Identify one explicit feedback item and its permitted destination; an authenticated conversation is not blanket feedback/disclosure consent. |
| Personal evidence | [Principal Memex contract](../../modules/ai_intelligence/digital_twin/src/principal_memex_contract.py) preserves source kind, receipt/revision, sensitivity and supersession. Its [projection](../../modules/ai_intelligence/digital_twin/src/principal_memex_projection.py) is structural and performs no FoundUp projection. | No destination FoundUp, feedback-purpose permission or work authority. Preserve source kind separately from R25 evidence type. |
| Purpose, expiry and revocation | [Signed disclosure](../../modules/communication/moltbot_bridge/src/reddog_principal_memex_disclosure.py) and [resident admission](../../modules/communication/moltbot_bridge/src/reddog_principal_memex_resident_admission.py) bind exact source decisions/revision, session, runtime, expiry, revocation and one-use consumption. | Purpose is exactly `resident_architect_context`; only public accepted `operator_statement` decisions from principal scope are admitted. This permission does not authorize FoundUp feedback. Do not broaden that purpose or reinterpret its receipt. |
| Evidence type | Conversation kinds are `operator_statement`, `repository_fact`, `model_inference`, `unresolved`. Principal Memex source kinds are `accepted_decision`, `governed_import`, `principal_statement`, `verified_observation`. | Neither enum is R25's five-type contract. A source label is not evidence of correctness. An operator statement may report a preference, observation or instruction; retain that distinction without inferring authorization. |
| Proposal and contradiction | [Learning-candidate builder](../../modules/communication/moltbot_bridge/src/foundup_memex_learning_candidate.py) and [contract](../../modules/communication/moltbot_bridge/src/foundup_memex_learning_candidate_contract.py) already supply content-bound proposal/candidate IDs, supporting/contradicting references and supersession. [Validation](../../modules/communication/moltbot_bridge/src/foundup_memex_learning_candidate_validation.py) checks FoundUp/snapshot/receipt/revision consistency. | Its source classes are `breadcrumbs`, `verified_outcome`, `governed_research`; none represents permissioned human feedback. It has no principal, consent, activity or R25 evidence-type binding. Never relabel feedback as a verified outcome or breadcrumb to obtain acceptance. |
| Deduplication and version | Exact repeated proposal payloads have identical IDs; source revision and content digest remain bound. | Changing creation time changes the proposal ID. That is not principal/proposal-version/consultation-window deduplication. Define the correlation key and revision/supersession rule before adding a persistent mapping. |
| Ticket preview and promotion | Existing conversation work promotion separates current authenticated context, pending preview and one-use promotion capability. | `commit_pending_conversation_work_proposal` performs a CAS persistence write. It is not a read-only projector and cannot run under R25-A's no-memory-write label. Normal work admission remains separate. |

**Smallest follow-on: qualify one explicit, same-FoundUp synthetic feedback input
at the existing learning-candidate contract/validation/builder boundary.** Exact
production field placement and compatibility remain unqualified. Reuse the
current source record/revision, proposal identity and scope owners; do not create
a second proposal queue, personal memory or generic authorization framework.
The follow-on contract qualification scores **3 + 4 + 3 + 3 = 13/P1** under WSP 15;
the broader 15/P1 parent estimate does not transfer automatically to this step.

The compatibility decision below fixes representation choices; its permission-owner prerequisite remains open before source implementation:

- Bind principal/conversation/record digest/revision and destination FoundUp to
  a specific permitted summary and source reference. Define feedback purpose,
  permission source, expiry and revocation under the existing authority owner;
  caller-supplied booleans or rehashed records cannot establish consent.
- Keep evidence type separate from source class and verification. Preserve
  reported preference, observed behavior and model inference; a verified fact
  needs its verification reference. Formal authorization is a distinct admitted
  authority reference, never feedback content that opens an execution valve.
- Specify proposal version/correlation, duplicate linkage, contradiction and
  supersession without inflating participants or contributions. Preserve the
  original source identity when a model summarizes it.
- For the local synthetic slice, declare current same-FoundUp interaction as a
  fixture input. Activity-event qualification, pause/expiry, attention budgets
  and delivery-time rechecks remain required before R25-B outreach. Do not call
  authenticated conversation expiry an implemented engagement policy.

Acceptance must include a permitted explicit-feedback positive case retaining
all bindings; exact retry linkage; visible dissent; and rejection of absent,
expired or revoked permission, source revision changes, wrong principal/FoundUp,
type laundering and feedback-as-authority. A changed summary, purpose, target or
proposal version must not inherit a stale permission. Existing component tests
are useful controls, not an end-to-end R25 acceptance result.

Evidence is bound in [the current backlog observation](rsi_swarm_backlog.json)
and its archived observations. Independent review checked 22 source/test/doc
blobs and the replay predicates/hashes; it did not rerun the replay or authorize
source implementation. Source/test ownership has no inspected peer overlap;
shared bridge `INTERFACE.md` overlaps PR1751/1645 and remains untouched here.

## R25-A approval-owner qualification — 2026-09-20

**Result: conditional record design qualified; source implementation blocked by
an exact host/consumer dependency.** This13/P1 planning action is complete.
It neither issues consent nor qualifies a source packet. Source/test hashes and
independent review are bound in the existing system backlog observation.

| Existing boundary | Current evidence | Required extension before implementation |
|---|---|---|
| Resident transport and admission | Closed v1 envelope exposes zero-authority TURN/STATUS/CANCEL. README explicitly leaves existing/new/first-turn aggregates host-unwired. | The separately owned host must define an authenticated explicit approve/withdraw action for one presented canonical summary. Generic text, a signed session or an approval boolean is insufficient. |
| Signed conversation record | v4 exact fields and typed continuity items; schema_version is immutable under ordinary CAS. HMAC/E0 protect integrity, not new-purpose permission. | Prefer an explicit feedback-capable version within existing record owners. Qualify creation identity or a specific version transition; never silently upgrade v4 or overload accepted_decisions. |
| Source identity | Current record retains latest content and digest receipts. Summary sanitization redacts/trims/truncates; learning text normalizes NFKC and trims. | Minimize/canonicalize before approval. Bind selected item IDs/kinds and an already observed source revision/digest; do not hash an approval into its own source identity. Specify current-source and historical-content availability rules. |
| Projection consumer | Learning v1 has three structural source classes and no R25 permission consumer. Work promotion targets FIX; Principal Memex stays resident_architect_context. | Verify exact approval and current source/session/revocation before copying summary into the existing learning boundary. Do not reuse other purposes or create a disconnected verifier. |
| Retry and recovery | Learning IDs include timestamps; E0 recovery and one-use work handles solve different identities. | Declare one logical proposal version/window/key and exact prior-result or rejection rule. Material approval time/expiry/version fields must remain bound; a timestamp-only repeat cannot count another participant. |

The conditional assertion binds authenticated principal/provider/conversation and
session, same-FoundUp destination, selected source item IDs/kinds and prior record
revision/digest, exact permitted summary bytes/digest, feedback purpose, logical
proposal version/window, issue/expiry and current revocation/supersession reference.
Source class remains separate from preference, observation, inference, verified
fact and formal authorization. Any material summary, scope, purpose or version
change requires a new approval binding. Dissent remains evidence, not a failure.

Compare three options: explicit-version record assertion is the preferred storage
seam; generic authenticated TURN is not an approval issuer; a standalone scoped
receipt has no current issuer/consumer and would duplicate authority machinery.
The external durable-adapter owner must supply the typed host handoff and current
revocation/retry linearization. Missing live012permission does not prevent local
design; the blocker is the absent engineering contract. Preserve that ownership.

Extend the existing compatibility matrix with: unchanged v4 record/sign/recovery
bytes and v1 learning IDs; unsupported version/migration rejection; normalized or
redacted text changed after approval; stale source content despite valid signature;
approval/revocation races; and exact retry after expiry/revocation. Use one synthetic
principal/FoundUp/item only after a source packet is qualified. Existing fixtures
for scope authentication/HMAC persistence, pending promotion, principal admission
and learning candidates are test owners, not proof of this missing positive path.
No tests or behavior probes ran during this qualification.

No work admission, technical verification, retention, reward, federation or outreach
authority follows. Resume R25 source qualification when the exact existing host
issuer, version transition and pre-projection current-state consumer are independently
bound; until then do not add fields, schemas, endpoints or a generic consent engine.

## R25-A compatibility decision — 2026-09-20

**Result: representation choices qualified; permission issuance/consumption remains
unqualified.** This is a planning result, not a new wire schema or an accepted
feedback proposal. No source, test, consent store or runtime changed. The 13/P1
qualification is complete; it does not assign that score to an implementation.

### Preserve the existing contract

Keep every v1 field set, enum, serialized byte and identity algorithm unchanged.
The current evidence validator requires string values and three exact source
classes; evidence and proposal IDs hash their full payload, including timestamps.
Adding optional or null feedback fields to v1 would change legacy identity.
Do not label human feedback as `breadcrumbs`, `verified_outcome` or
`governed_research` to get through the existing gate.

If the permission contract below is qualified, use an explicit feedback-capable
version in the existing contract, validation and builder owners. Keep the v1
path separate and make old readers reject the new version. This is a design
choice; no v2 name, class, registry entry or runtime capability is implemented.

| Binding | Proposed placement in existing owners | Compatibility requirement |
|---|---|---|
| Principal, conversation, source item and original source kind | Feedback-capable evidence alongside the existing source receipt/revision and FoundUp/snapshot fields | Preserve source record digest/revision and distinguish source class from evidence type; do not overload an existing ID. |
| Permitted summary | Evidence statement plus its existing content digest; retain the original source reference | Canonicalize and minimize before permission is obtained. Permission must bind exactly those bytes; later normalization, redaction or model rewriting requires a new binding. |
| Feedback purpose, permission reference, target and validity | Typed evidence binding, consumed through the existing authenticated conversation/record authority | Verify the exact principal, source, canonical summary, destination FoundUp, proposal version, purpose, expiry and current revocation state. A reference or digest alone is not permission. |
| Evidence type | Separate feedback evidence field | Keep reported preference, observed behavior and model inference distinct. Verified fact requires its verification reference; formal authorization requires its own admitted authority reference and cannot open an execution valve through feedback. |
| Logical proposal version and consultation-window correlation | Feedback-capable proposal, separate from its content-addressed ID and creation time | Same logical retry links to the same version/window without counting another participant; new material content/target/purpose/version needs a new permission binding. |
| Contradiction and supersession | Existing supporting/contradicting references; explicit version linkage in the proposal | Preserve dissent. `supersedes_memory_ids` remains memory-target metadata, not proof of proposal supersession or deduplication. |
| Candidate and reconstruction | Existing proposal ID and exact evidence-manifest closure | Bind every new semantic field into evidence/proposal identity, reconstruction and gate receipt. Copy only routing fields needed by a consumer; retain all non-authorizing/read-only flags. |

The learning-candidate normalizer is NFKC plus trim. Consent to arbitrary raw text followed
by silent canonicalization is insufficient. Keep a trace to the original source
and have any eventual permission cover the exact canonical disclosed summary.
A model summary remains a derived artifact, not a new principal statement.

Current builder/contract test budgets are 500 lines and 60 lines per function;
observed sizes are builder436/max58, contract175, validation489/max57. The
existing 851-line test owner includes inherited64/92-line helpers. Qualify any
growth against current tests/WSP62 before editing; add no exemption or duplicate
owner. The existing assembler emits no learning candidates, and no production
gate caller was found in the inspected module search. Shape support alone would
not connect the feedback lifecycle.

### Missing permission contract and reuse decision

Authenticated conversation scope supplies identity, destination/session binding
and expiry; its closed record contract does not contain an R25 feedback-permission
assertion. Personal Memex disclosure is explicitly `resident_architect_context`
from principal scope and must remain so. A signed record proves its authenticated
origin under its existing contract, not permission for a new purpose.

The older communication and infrastructure consent engines were also inspected.
Their automatic grants and unkeyed digest/UUID identifiers do not bind an
authenticated principal's approval of this exact summary, FoundUp and proposal
version. They are not an R25 authority adapter. No import connecting them to
the inspected bridge/digital-twin/FAM owners was found; this is a reuse decision,
not a claim of an exposed production vulnerability or an instruction to delete them.

The approval-owner qualification above selects a conditional record seam. Its unresolved prerequisite is the exact authenticated host handoff and current-state consumer for that approval assertion
and its issuer/consumer under the **existing authenticated conversation/record
owners**, including source-record signing/revision, permitted summary bytes,
purpose/target/version, expiry, revocation and retry semantics. Verify this before
the read projection copies permissioned content. Preserve existing read,
one-use promotion and CAS persistence boundaries. Do not add a second generic
consent engine, widen the architect disclosure purpose or introduce an unused
verifier to make the proposal appear accepted.

Missing live permission does not prevent safe contract development. The current
source-edit blocker is narrower: the assertion/issuance/consumption contract and
its exact compatible owner extension have not been selected and independently
qualified. Resolving that design does not itself require a new 012 approval.
A synthetic structural envelope may be designed separately, explicitly unverified
and non-authorizing; it cannot satisfy the consented-feedback acceptance gate.

### Required compatibility matrix for the eventual implementation

| Case | Required result |
|---|---|
| Unchanged legacy v1 inputs | Identical wire bytes, evidence/proposal/candidate IDs and gate receipts. |
| Explicit synthetic feedback with a qualified permission input | Preserve every source/type/scope/version binding; structural candidate only, with no work, persistence, verification or reward authority. **This positive path does not exist yet.** |
| Exact retry or timestamp-only repeat | Preserve the logical version/window linkage; never inflate participant or contribution counts. Keep legacy content IDs unchanged in meaning. |
| Dissent or a correction | Keep contrary evidence and explicit version linkage visible; no forced agreement or silent type conversion. |
| Missing, expired or revoked permission | Reject before projecting the permitted content; no candidate or side effect. |
| Wrong principal, conversation, FoundUp, source revision or digest | Reject even when a caller recomputes unsigned hashes. |
| Changed summary, purpose, destination or proposal version | Require a new exact permission binding; stale permission rejects. |
| Preference/inference relabeled as fact or authorization | Reject unsupported type/authority references; no execution-valve effect. |
| Principal-only disclosure or legacy automatic consent record | Reject as feedback permission; preserve the existing architect-only behavior. |
| Missing activity qualification, recipient policy or delivery-time recheck | No R25-B outreach. A synthetic activity assertion is fixture input, not implemented engagement policy. |

Source-bound independent reviews, searched owners, exact file/function budgets and
the post-qualification WSP15 decision are in the existing backlog observation.
No tests were rerun for this documentation-only qualification; unchanged earlier
component results remain scoped to their recorded source and do not prove R25.

| Slice | Deliverable | Required positive and negative evidence |
|---|---|---|
| R25-A: local proposal | One synthetic or explicitly supplied feedback item becomes a scoped, versioned proposal through existing read-only projections. | Source/disclosure/type retained; duplicate linked; contradiction visible; wrong FoundUp, absent permission, changed revision and feedback-as-authorization rejected. No external message or memory write implied. |
| R25-B: bounded consultation | One permissioned proposal is presented to a small opted-in cohort of 012s actively engaged with that same FoundUp, through their own RedDogs. | Active/relevant participant receives at most the admitted prompt; inactive, paused, idle-only, stale, wrong-FoundUp and revoked cases receive none; activity expires between selection and delivery and the prompt is withheld; recipient/attention caps hold; no private transcript leakage; nonresponse stays unknown; copied identities do not multiply participants. |
| R25-C: ticket and return path | A reconciled proposal enters the existing admitted ticket lifecycle; result returns to the originating scope. | One durable job mapping; revised criteria require re-admission; independent artifact audit; no claim of success from chat text; old, duplicate, forged or cross-scope result cannot overwrite current conversation state. Requires R06/R09/R16 and the applicable R22 adapter. |
| R25-D: scale and learning evidence | Bounded queues, durable delivery, consent revocation, activity expiry, typed 3V evidence mapping and measured usefulness at the declared workload. | Restart/duplicate delivery, partition, delayed response, cohort bias, prompt spam, forged participation and provider failure tests; one answer cannot inflate participation through retries; V1 support cannot set V2 completion, CABR-ready or payout-ready flags; predeclared attention/cost targets. Production CABR feedback scoring requires R21; R11/G4 are required for verified retention/RSI claims. |

Use one already authorized conversation integration at a time. A missing service caller is implementation work for its existing owner, not a reason to weaken the history guard or send raw transcripts to a provider. First use synthetic principals for cross-scope negative cases; actual outreach must be authorized by participating principals' applicable policy.

## Acceptance, rewards and stopping

The product should make collaborative intelligence visible without burdening 012: a compact explanation of the issue, material feedback, decision and result, with permitted provenance available. Preserve meaningful dissent instead of manufacturing agreement. Consultation ends at its deadline or attention limit; unresolved material constraints return a blocker or narrower proposal to the owner.

Do not pay for favorable feedback, agreeing with the proposer or generating more messages. Any contribution/review reward uses R24's pre-agreed policy, verified contribution and separate settlement owner. No CABR-derived authority, delegated vote threshold or reward amount is ratified here; the [deferred governance questions](../architecture/FOUNDUPS_MEMEX_DEFERRED_GOVERNANCE_NOTES.md) remain open.

Stop on scope mismatch, revoked consent, stale material proposal, missing authority, exhausted budget or conflicting active ownership. Keep approved prior versions and policy-compliant audit metadata; revoke/delete personal projections under their retention contract rather than retaining private content forever for an audit label. Rollback affects only the admitted slice.

Completion evidence must bind the source/runtime, principal and FoundUp scopes, permission, proposal versions, cohort/delivery record where applicable, exact ticket, artifact audit, costs and actual result receipt. Report PoC, multi-principal feedback MVP and RSI completion separately. This packet adds no current runtime capability.

Applicable WSPs: 15, 22, 26, 29, 48, 50, 60, 73, 77, 96, 97, 103, 104.
