# R25 — Consented 012 / RedDog feedback into governed tickets

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
