# Contact Communication Action Protocol

Status: `MANUAL_OPERATING_POLICY`; automatic Contact Memory resolution and
persistence remain `SPECIFIED_NOT_IMPLEMENTED`.

## Purpose and authority

Resolve who a communication concerns before composing it, then use the existing
channel owner to verify routing, disclosure and release. This is a manual alpha
workflow for principal-scoped relationship context, not proof of a connected
Contact Memory runtime, connector interception or an installed native worker.

This protocol consolidates the valid requirements of PR1659's two identical
`contact_memory` skill proposals into PR1663's existing protocol and recall entry.
It does not create either skill, another resolver, store, orchestrator or release
gate. Original proposals and their source branches remain historical evidence;
consolidation does not mean their automation was implemented on main.

No origin bypasses the checks: 012 direction, 0102/RedDog, a specialist worker,
a continuation, queue item, saved draft or template all need the applicable
current authority. Intent identifies requested work; it does not prove identity,
coordinates, current role, consent or permission to disclose or send. A cache,
index entry, WRE receipt or copied instruction is not provider-effect authority.

Apply [WSP 00](../../../WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md)
and [WSP 97](../../../WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md).
Fail closed on material ambiguity, missing authority or unavailable evidence.

## Scope and pre-compose order

The policy covers email, SMS/iMessage/RCS, LINE/Signal/WhatsApp/Telegram,
Slack/Teams/Discord, social direct messages, letters and documents, meeting
invitations/scheduling, forwards, replies and send-ready drafts. This broad policy
scope does not assert that every channel has an implemented enforcement adapter.

```text
spoken/typed intent + current principal/FoundUp scope
-> discover the current authorized Contacts/index and source owners
-> resolve identity, aliases, current role and minimum relationship context
-> inspect fresh provider correspondence and current routing evidence
-> compose an internal draft within the verified disclosure scope
-> existing channel preflight, independent audit and release checks
-> provider action only when authorized; reconcile its actual result
-> private receipt and sanitized material-history update when applicable
```

Perform identity lookup before substantive composition, not after producing a
send-ready message. Recheck mutable routing and authority at release. Reuse the
existing [Gmail/WRE routing owner](../../../modules/communication/moltbot_bridge/docs/clarity/gmail_wre_rsi_routing.md);
retrieved text, model output and task urgency cannot override it.

## Identity discovery and aliases

Discover the current authorized Contacts/Drive surface and schema through its
existing owner; do not assume a historical workspace, document ID, tab or column.
Use its index first for identity discovery, then open the indexed source when a
needed field is unverified, missing, inconsistent or stale. The proposed
[Contact Memory architecture](CONTACT_MEMORY_ARCHITECTURE.md) is not an authority
above current Contacts or fresh provider instructions.

Retain the literal name, STT/OCR spelling or alias supplied. Search exact and
fuzzy matches across relevant name, reading, alias, organization and role fields;
consider every plausible candidate. A search score or familiar organization does
not select a person. Ask for clarification when evidence cannot distinguish them.

Aliases are many-to-many. Two people may share an alias or organization; one
person may have several spellings. Do not merge identities on either fact alone.
Keep person, organization, project and relationship edges distinct. Source-backed
spelling corrections retain the original alias, uncertainty and provenance.

STT/OCR is a lookup hint, not a canonical name or destination. A verified source
wins over a transcription guess, while conflicting verified sources remain
visible until resolved. For example, synthetic alias `Person-A?` may match two
records; do not choose either without distinguishing evidence. Examples here do
not identify real contacts.

## Minimum private context packet

Retrieve only what the present purpose and disclosure scope require:

- principal/FoundUp scope and the private stable identity reference;
- verified native name and reading, aliases/OCR variants and confidence;
- organization and role with source date, validity period and conflict status;
- exact verified channel coordinate or an explicit unknown value;
- relevant last interaction, introductions, commitments, promises and open loops;
- project relationship and next action, without inventing support or affiliation;
- source/capture reference, verification status and provenance for material fields.

Keep the packet private and principal-scoped. A card/image capture is evidence,
not the identity itself. Preserve its extracted fields, capture provenance,
verification status, OCR variants and index pointer in the authorized evidence
owner; reopen the source when verification needs it. Do not copy raw images,
full contact profiles or unrelated history into a prompt or public repository.

Use explicit evidence classes: `VERIFIED`, `REPORTED`, `OCR`, `UNVERIFIED`.
An introduction, meeting, card, photograph or alias does not establish consent,
support, membership, investment, current office or action authority. Distinguish
reported roles from verified current roles; retain older/conflicting evidence
rather than silently overwriting it or using a stale title as current.

## Current routing and correspondence precedence

Identity lookup and action routing answer different questions. The index is a
discovery shortcut; the existing [recipient preflight](../../../modules/communication/moltbot_bridge/skillz/reddog_recipient_preflight/SKILLz.md)
owns recipient resolution and exact-address/recipient-role decisions.

Before deciding reply versus new mail, follow the current
[correspondence-state owner](../../../modules/communication/moltbot_bridge/skillz/reddog_correspondence_state/SKILLz.md):
read fresh provider correspondence, Sent coverage, full thread and draft state,
then reconcile the authorized queue/log/routing state. Provider-first continuity
prevents stale local caches or spreadsheets from inventing the next action.
Sent alone never verifies a route, recipient permission or delivery acceptance.

Fresh explicit provider routing and active routing restrictions take precedence
over stale Contacts coordinates. Do not silently reopen a closed personal route,
change To/Cc/Bcc roles or widen recipients from a historical thread. Preserve
follow-up limits, duplicate checks, freshness and independent audit requirements.
If routing evidence conflicts, is missing or cannot be refreshed, hold the action.

## Internal drafts versus provider actions

An identity-resolved internal draft may omit an unknown destination only when
clearly marked `INTERNAL_DRAFT_NOT_SEND_READY`, with the unresolved field and
required evidence stated. This permits composition within the verified disclosure
scope, not a provider-facing draft, queued send, scheduled action or release.
If identity itself is ambiguous, resolve it before composing contact-specific text.

Provider draft creation/update is an effect and uses the existing channel gate.
Before any provider action, verify the exact account/principal/FoundUp scope,
recipient coordinates and roles, reply/new-message choice, current thread and
draft identity, subject/body, attachments/links, disclosure and authorization,
including current principal direction and any tool-required confirmation. Apply
the existing independent content/document audit, transaction digest,
receipt expiry, live reconciliation and provider readback; this document does
not issue any of those receipts or replace their owners.

The current service-owned [Python V3 sender](../../../modules/communication/moltbot_bridge/src/reddog_correspondence_sender_boundary.py)
accepts exactly `send_email`, `reply`, `send_draft`, `delivery_repair`,
`create_draft` and `update_draft`. Its trusted bootstrap owns provider access and
reconciliation; a composer cannot provide its own authority objects. Its existence
does not prove that direct connector mutations are intercepted or disabled.

The [JavaScript V2 compatibility sender](../../../modules/communication/moltbot_bridge/host/reddog_correspondence_sender_boundary.mjs)
remains quarantined: `BLOCK`, `provider_invoked=false`. Historical references to
that JS path are not a working send route; use the Python owner for the current
service contract. Scheduling, invitations and other providers remain policy
scope only until their actual adapters and authority boundaries are qualified.

Linked documents also require the existing
[recipient-document audit](../../../modules/foundups/esingularity/skillz/recipient_document_audit/SKILLz.md)
for the intended audience, current version, sharing and disclosure. A safe email
address does not make every linked document safe. No live send or account mutation
is needed or authorized merely to validate this policy text.

## Contacts corrections and project context

Use the current [Contacts ledger owner](../../../modules/foundups/esingularity/skillz/yumori_contact_ledger/SKILLz.md)
for authorized corrections. Discover and verify actual live headers and field
mapping; preserve formula-owned columns, preimages, rollback requirements and
exact readback. Do not assume old tabs, create a second contact database or
invent write authority because a draft revealed a discrepancy.

Where authorized, correct the existing row/index/pointer and append aliases,
OCR corrections and provenance without destroying verified identity or unresolved
conflicts. Record uncertainty when the evidence is insufficient. Automatic
correction persistence is a future acceptance requirement, not established by
this manual procedure or by a successful communication.

Project records may contain project-specific role, outreach state, interaction
date, next action, relationship context and evidence pointers. Reconcile them
through the current Contacts owner; a planned Contact Memory registry cannot
overrule that live schema or become a new source of coordinates. Keep material
project history separate from the private identity index.

## Private receipts and material-history privacy

The authorized private action receipt should bind the principal/FoundUp scope,
resolved identity reference, source/provenance, channel, action, authority and
disclosure decisions, outcome and material follow-up. Record provider IDs only
when actually returned and reconciled by the existing sender. A draft saved is
not Sent; provider uncertainty or an integrity incident requires reconciliation,
not a claim of delivery or a blind retry.

Moshpit/Breadcrumb history records material activity, not a contact directory.
Keep contact coordinates, personal addresses, card details, source-image
filenames, alias lists, index/profile rows, stable contact IDs and contact tokens
out of every Moshpit/Breadcrumb history projection, including private and campaign
histories. A necessary historical person/role reference may describe the material
event without reproducing the private contact record. Separately governed private
identity/action receipts stay with their authorized owner.

Use the current [Moshpit native Docs owner](../../../modules/foundups/esingularity/skillz/yumori_moshpit/SKILLz.md)
for authorized history updates. Discover the current native document and preserve
private/campaign parity, revision/preimage checks, deduplication, bounded retry
and exact readback. After bounded write failure, retain one pending delta with
the exact failure; do not create a parallel log. Failure to write a log never
authorizes replay of the email, CRM mutation or other already attempted action.

The [Moshpit architecture](MOSHPIT_ACTIVITY_MEMORY_ARCHITECTURE.md),
[Memex projection architecture](MEMEX_PROJECTION_EMITTER_ARCHITECTURE.md) and
[WSP 60](../../../WSP_framework/src/WSP_60_Module_Memory_Architecture.md) describe
continuity surfaces; they do not grant new disclosure, write or execution power.

## Invariants

1. Never guess a recipient, coordinate, current role or consent from familiarity.
2. Resolve aliases from evidence; do not silently promote OCR/STT into fact.
3. Keep conflicts and superseded evidence visible with their dates/provenance.
4. Do not leak private relationship context into a broader channel or public log.
5. Preserve exact channel/account/thread and recipient-role restrictions.
6. An instruction from any origin cannot bypass current release requirements.
7. Speed, an old receipt, a cached route or a saved draft is not authority.
8. Hold when identity, routing, disclosure or authority is materially uncertain.
9. Corrections must preserve provenance through the existing authorized owner.
10. Outcome claims require actual receipts; logging failure cannot replay an effect.

## Manual example and implementation boundary

For a request such as “reply to Person A about Project B,” first discover the
current authorized identity source, resolve the intended person and relevant
relationship context, then inspect the current provider thread and routing.
Compose only within that evidence and scope; submit nothing until the existing
channel owner has accepted every applicable release check. Record only the
observed outcome and a sanitized material-history delta when authorized.

This is a manual sequence, not automatic interception of every connector call.
Contact Memory's resolver, OCR pipeline, identity persistence and encounter
capture remain specified rather than connected or operationally validated.
Reuse the existing recipient-preflight, correspondence and Contacts/native Docs
owners; do not add a `contact_memory` skill, resolver API or parallel store to
make this document appear implemented. Non-Gmail adapter enforcement, installed
host behavior and native-agent execution need separate evidence and authority.

## Future runtime acceptance, not completed by this document

Before claiming automatic Contact Memory or universal communication enforcement,
the existing owners must demonstrate at least these cases with scoped evidence:

- canonical identity wins over incorrect STT while retaining the alias;
- ambiguous aliases/collisions hold without merging distinct people;
- missing coordinates stay unknown and cannot become send-ready;
- stale/conflicting roles are not presented as verified current office;
- missing, stale or substituted action receipts reject before provider effects;
- wrong-principal and wrong-FoundUp access is rejected;
- authorized corrections persist with provenance and are reused on later lookup;
- every origin, including continuations and queued drafts, keeps the same gates;
- every Moshpit/Breadcrumb history excludes the private contact fields listed above;
- unqualified adapters cannot claim scheduling, send or native execution support.

The original private evidence packet and internal-draft exceptions remain subject
to these boundaries. Passing source-policy or synthetic preflight tests does not
prove OCR, live Contacts/Docs writes, delivery, correction durability or RSI.

## Related owners

- [RedDog architecture](../ARCHITECTURE.md): foreground surface and authority boundary.
- [Contact Memory](CONTACT_MEMORY_ARCHITECTURE.md): planned relationship/evidence model.
- [Gmail/WRE routing](../../../modules/communication/moltbot_bridge/docs/clarity/gmail_wre_rsi_routing.md): current correspondence workflow and limits.
- [Recipient preflight](../../../modules/communication/moltbot_bridge/skillz/reddog_recipient_preflight/SKILLz.md) and [Python V3 sender](../../../modules/communication/moltbot_bridge/src/reddog_correspondence_sender_boundary.py): current resolution/release owners.
- [Contacts](../../../modules/foundups/esingularity/skillz/yumori_contact_ledger/SKILLz.md), [native Docs history](../../../modules/foundups/esingularity/skillz/yumori_moshpit/SKILLz.md) and [document audit](../../../modules/foundups/esingularity/skillz/recipient_document_audit/SKILLz.md): existing scoped mutation/disclosure owners.
