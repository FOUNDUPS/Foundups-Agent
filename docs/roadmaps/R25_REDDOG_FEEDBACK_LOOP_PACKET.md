# R25 — Consented 012 / RedDog feedback into governed tickets

Date: 2026-09-11. Status: `SPECIFIED_NOT_IMPLEMENTED`. Parent: [system roadmap](../../ROADMAP.md). Registry: [planning backlog](rsi_swarm_backlog.json). Architecture decision: [hybrid tickets, teams and feedback](../architecture/REDDOG_HYBRID_TICKET_SWARM_FEEDBACK_MODEL.md). This packet is not a work order, a message-send instruction or a delegation of voting authority.

## Outcome

012 can describe a problem or suggestion to their own RedDog. The deep 0102 loop retrieves the applicable WSPs and current FoundUp evidence, checks duplicates, records a versioned proposal, and prepares a bounded ticket. When useful and consented, other eligible RedDogs ask their own 012s for relevant feedback. Scoped summaries, dissent and corrections improve the proposal. Actual accepted work returns a truthful result to the originating conversation.

Feedback is optional input. It cannot authorize runtime mutation, create technical verification, mint rewards or count silence as approval. The default is one FoundUp and one principal; multi-principal consultation is a later slice. Cross-FoundUp consultation requires its own federation/scope admission.

## Existing owners and dependencies

Reuse the [dual-loop sequence](../architecture/REDDOG_DUAL_LOOP_COGNITION_ARCHITECTURE.md), [Memex boundary ADR](../adr/ADR_REDDOG_FOUNDUPS_SECOND_BRAIN_BOUNDARY.md), existing authenticated conversation scope/session contracts, [learning-candidate projection](../../modules/communication/moltbot_bridge/src/foundup_memex_learning_candidate.py), WRE work-order intake, AgentDB and FAM task linkage. R22's existing product owner owns client/service delivery. Do not build a second personal memory system, federation server or independently mutable ticket queue.

Integrated ticket execution depends on R06, R09 and R16. R22's supported conversation adapter is required before claiming live end-to-end product delivery. R24 applies to qualified team/reward claims; R11 applies to retained verified-outcome claims. R04 applies where the selected authority requires exact runtime closure. R25-A design and synthetic proof can proceed before these integrations; no new authority is inferred from that partial progress.

WSP 15 preliminary estimate: complexity 4, importance 4, deferability/urgency 3, impact 4; total 15/P1. This does not displace Wave 0 blockers. Proposed ownership: existing RedDog conversation owner plus FoundUp Memex/WRE integration owner, with independent privacy/verification review.

## Contract mapping required before implementation

Map these requirements to the existing contracts and enumerate only genuinely missing fields:

- Originating conversation/principal scope, destination FoundUp, source revision, proposal ID/version, observation timestamp, purpose and expiry.
- Distinct evidence types: reported preference, observed behavior, model inference, verified fact and formal authorization. A correction or supporting majority cannot silently change a type.
- Explicit disclosure permission and minimum permitted summary; cohort eligibility, recipient cap, attention/frequency budget, response deadline and opt-out/revocation behavior. Participation is optional and private source material stays with its owner.
- Correlation/deduplication across repeated suggestions, multiple RedDogs representing one principal, retries and delivery acknowledgments. Authenticated identity is not proof that a sample represents all affected people.
- Supporting and contradicting evidence, version supersession, minority/affected-cohort constraints and unanswered questions. Model-generated speculation must not become a human response.
- Proposal-to-existing-ticket link, objective, fixed acceptance, budget and independent verifier. The proposal remains non-executable until normal work admission.
- Outcome receipts and disclosure-safe attribution back to the original conversation: proposed, declined, admitted, running, rejected, accepted, activated or rolled back only when supported. Late results must not overwrite newer context.

## Incremental slices and acceptance

| Slice | Deliverable | Required positive and negative evidence |
|---|---|---|
| R25-A: local proposal | One synthetic or explicitly supplied feedback item becomes a scoped, versioned proposal through existing read-only projections. | Source/disclosure/type retained; duplicate linked; contradiction visible; wrong FoundUp, absent permission, changed revision and feedback-as-authorization rejected. No external message or memory write implied. |
| R25-B: bounded consultation | One permissioned proposal is routed to a small opted-in cohort through supported conversation adapters. | Only eligible recipients; aggregate recipient/attention caps; each RedDog talks to its own principal; revocation blocks pending disclosure; no private transcript leakage; no response remains unknown; copied identities do not multiply participants. |
| R25-C: ticket and return path | A reconciled proposal enters the existing admitted ticket lifecycle; result returns to the originating scope. | One durable job mapping; revised criteria require re-admission; independent artifact audit; no claim of success from chat text; old, duplicate, forged or cross-scope result cannot overwrite current conversation state. Requires R06/R09/R16 and the applicable R22 adapter. |
| R25-D: scale and learning evidence | Bounded queues, durable delivery, consent revocation, correction propagation and measured usefulness at the declared workload. | Restart/duplicate delivery, partition, delayed response, cohort bias, prompt spam, forged participation and provider failure tests; predeclared attention/cost targets; independent benefit measurement before claiming improved future work. R11/G4 are required for verified retention/RSI claims. |

Use one already authorized conversation integration at a time. A missing service caller is implementation work for its existing owner, not a reason to weaken the history guard or send raw transcripts to a provider. First use synthetic principals for cross-scope negative cases; actual outreach must be authorized by participating principals' applicable policy.

## Acceptance, rewards and stopping

The product should make collaborative intelligence visible without burdening 012: a compact explanation of the issue, material feedback, decision and result, with permitted provenance available. Preserve meaningful dissent instead of manufacturing agreement. Consultation ends at its deadline or attention limit; unresolved material constraints return a blocker or narrower proposal to the owner.

Do not pay for favorable feedback, agreeing with the proposer or generating more messages. Any contribution/review reward uses R24's pre-agreed policy, verified contribution and separate settlement owner. No CABR-derived authority, delegated vote threshold or reward amount is ratified here; the [deferred governance questions](../architecture/FOUNDUPS_MEMEX_DEFERRED_GOVERNANCE_NOTES.md) remain open.

Stop on scope mismatch, revoked consent, stale material proposal, missing authority, exhausted budget or conflicting active ownership. Keep approved prior versions and policy-compliant audit metadata; revoke/delete personal projections under their retention contract rather than retaining private content forever for an audit label. Rollback affects only the admitted slice.

Completion evidence must bind the source/runtime, principal and FoundUp scopes, permission, proposal versions, cohort/delivery record where applicable, exact ticket, artifact audit, costs and actual result receipt. Report PoC, multi-principal feedback MVP and RSI completion separately. This packet adds no current runtime capability.

Applicable WSPs: 15, 22, 48, 50, 60, 73, 77, 96, 97, 103, 104.
