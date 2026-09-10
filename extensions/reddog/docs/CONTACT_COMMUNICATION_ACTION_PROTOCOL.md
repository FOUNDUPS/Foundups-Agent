# RedDog Contact Communication Action Protocol

Status: `NORMATIVE_EXECUTION_CONTRACT`

This document defines the pre-action contract for RedDog / 0102 when drafting,
replying to, sending, forwarding, scheduling, or otherwise initiating external
communication to a human or organization.

It exists because live 012/0102 alpha use repeatedly shows that approximate
speech, STT artifacts, aliases, nicknames, OCR, and remembered roles can resolve
to the wrong person unless identity is checked against canonical relationship
evidence before action.

## Authority Boundary

No instruction source bypasses this protocol.

That includes:

- 012;
- 0102;
- RedDog;
- a specialist agent;
- a continuation prompt;
- a queued task;
- a retrieved draft;
- a prior message template.

An instruction supplies intent. It does not prove recipient identity, contact
coordinates, current role, relationship context, or authority to communicate.

Before any external communication action, execute WSP_97 and this protocol.
Where identity or authority remains materially ambiguous, fail closed rather
than guess.

## Scope

This protocol applies to:

- email;
- SMS / iMessage / RCS;
- LINE / Signal / WhatsApp / Telegram / other chat;
- Slack / Teams / Discord or equivalent direct outreach;
- social direct messages;
- letters and addressed documents;
- meeting invitations when the invite targets a known human or organization;
- contact-sensitive drafts intended for immediate sending by the principal.

It applies both to actual sends and to final send-ready drafts where a wrong
name, role, address, or thread would create relationship damage.

## WSP_97 Pre-Action Gate

Every communication action must enter through:

```text
intent from 012 / 0102 / task
        |
        v
WSP_00 current-state intake when repo/work discovery is required
        |
        v
WSP_97 execution gate
        |
        +--> canonical contact/relationship owner lookup
        +--> evidence + freshness check
        +--> ambiguity / STT / alias resolution
        +--> recipient + channel resolution
        +--> relationship/thread context retrieval
        +--> disclosure / authority check
        |
        v
DRAFT / REPLY / SEND
        |
        v
receipt + Breadcrumb / Contact Memory update where material
```

The action must not move from intent directly to draft/send when the target is a
known or purportedly known contact whose identity can be resolved from existing
principal-scoped evidence.

## Recipient Resolution Contract

Before producing a send-ready communication, resolve the recipient against the
canonical Contact Memory / contact registry and source evidence.

Minimum checks:

1. **Canonical person identity**
   - native-script name where available;
   - romanization / reading where available;
   - known aliases, OCR variants, nicknames, and STT variants;
   - identity confidence.
2. **Current organization / role**
   - use time-bounded role evidence where available;
   - do not silently preserve an obsolete title.
3. **Communication coordinate**
   - exact email / phone / account / thread supplied by canonical evidence;
   - never manufacture an address from a name, employer, or domain.
4. **Relationship context**
   - last relevant interaction;
   - promises / open loops;
   - project / FoundUp relationship;
   - introductions that affect tone or trust.
5. **Source provenance**
   - business card, contact registry row, prior verified thread, message capture,
     Lick evidence, or equivalent principal-scoped source.
6. **Freshness / conflict check**
   - if two records conflict, resolve or surface the ambiguity;
   - latest evidence does not automatically overwrite older evidence without
     preserving provenance.

## Name / STT Rule

Speech recognition is evidence, not authority.

When 012 dictates an approximate name, RedDog / 0102 must treat it as a lookup
hint, not as canonical spelling.

Example failure pattern:

```text
spoken / STT: "Akamura"
canonical registry evidence: 中村 光宏 / Nakamura Mitsuhiro
```

The outgoing communication must use the canonical identity returned by the
contact registry / relationship evidence, not the approximate STT token.

If no canonical match reaches sufficient confidence, do not guess. Ask only
when the ambiguity materially prevents safe completion and cannot be resolved
from available evidence.

## Drafting vs Sending

### Draft-only

A draft may be prepared before a communication coordinate is known only when:

- the recipient identity itself is resolved; and
- the draft is clearly not represented as ready to send through a specific
  unresolved channel.

A send-ready draft must still use the canonical name/role and relevant thread
context.

### Sending / forwarding / replying

Before mutation of an external communication system, additionally verify:

- exact destination coordinate or existing thread;
- correct account / provider context;
- reply vs new-thread intent;
- attachments and links;
- disclosure class / confidentiality;
- whether the principal actually authorized the external action;
- whether any action-specific confirmation is required by the connected tool.

## Relationship Protection Invariants

1. **Never guess a known contact's name when registry evidence is available.**
2. **Never invent an email address, phone number, handle, organization, or role.**
3. **Never rely on STT spelling when canonical relationship evidence conflicts.**
4. **Never upgrade an inferred identity into a verified identity silently.**
5. **Never send on the basis of a stale role if fresher evidence is available.**
6. **Never expose private contact evidence merely to prove identity to an
   external recipient.**
7. **Never let 0102 authority bypass WSP_97.** 0102 orchestrates; WSP governance
   still gates execution.
8. **Never let RedDog speed bypass verification.** Fast surface behavior means
   fast retrieval, not lower truth standards.
9. **Fail closed on material recipient ambiguity.**
10. **Preserve correction evidence.** When 012 or a contact corrects a name,
    alias, role, or relationship, append the correction to Contact Memory and
    prefer it in future resolution while retaining provenance.

## Canonical Retrieval Order

For a known/project contact, query in this order where available:

```text
1. Contact Memory canonical entity / contact registry
2. verified prior communication thread
3. business card / source capture / Lick evidence
4. project-specific Contacts ledger
5. Breadcrumbs / Brain/Memex relationship context
6. semantic retrieval / fuzzy recall as discovery aid only
```

Semantic retrieval may locate the candidate, but deterministic identity evidence
must decide the final recipient whenever possible.

## Project-Specific Registry Rule

A FoundUp may maintain a project-facing contact ledger or projection (for
example YUMORI Contacts), but this must project from or reconcile with canonical
Contact Memory rather than becoming an independent contradictory identity
source.

Project ledgers may hold operational fields such as:

- project role;
- outreach status;
- last contact date;
- next action;
- project-specific notes;
- evidence references.

They must not silently override canonical identity fields without evidence.

## WSP_97 Evidence Receipt

For consequential communication, execution evidence should be sufficient to
reconstruct:

- requested action;
- resolved recipient entity;
- evidence used to resolve identity;
- destination channel/thread;
- authority/confirmation state;
- disclosure decision;
- action outcome;
- external message/thread ID where returned;
- Breadcrumb / open-loop update if material.

Do not place raw private contact data in public repository receipts. Use opaque
IDs, hashes, synthetic fixtures, or disclosure-safe references.

## RedDog / 0102 Operating Rule

When the principal says phrases such as:

- "email him";
- "send Nakamura this";
- "write the BB100 guy";
- "message the councilman";
- "reply to that reporter";
- "follow the email protocol";

RedDog / 0102 must interpret the request as:

```text
resolve person -> retrieve relationship/thread -> run WSP_97 -> draft/action
```

not:

```text
approximate spoken name -> compose -> send
```

This rule is part of the RedDog proxy contract, not optional user-memory
personalization.

## Implementation Status

The current repository contains Contact Memory architecture and governed
external-action boundaries, but the complete automated recipient-resolution
runtime is not yet proven deployed. Until runtime enforcement exists, agents
must follow this protocol manually and must not claim automated enforcement.

Future implementation should expose a fail-closed `resolve_communication_target`
or equivalent owner interface that returns a bounded recipient-resolution
receipt before any external communication adapter can execute.

## Acceptance Tests for Runtime Enforcement

A production communication gate is not complete until tests prove:

- canonical name beats conflicting STT spelling;
- ambiguous same/similar names fail closed;
- no contact coordinate can be invented;
- stale and current role conflicts are surfaced/resolved;
- a send adapter rejects a missing recipient-resolution receipt;
- a send adapter rejects a recipient receipt scoped to another principal;
- a send adapter rejects a recipient receipt scoped to another FoundUp when
  project scope matters;
- corrections persist and win future resolution without destroying old source
  evidence;
- 0102-originated and RedDog-originated actions pass through the same gate;
- public logs/receipts do not leak raw contact data.

## Canonical Dependencies

- `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md`
- `extensions/reddog/ARCHITECTURE.md`
- `extensions/reddog/docs/CONTACT_MEMORY_ARCHITECTURE.md`
- `extensions/reddog/docs/MEMEX_PROJECTION_EMITTER_ARCHITECTURE.md`
- WSP 60 Breadcrumbs / FoundUp Brain/Memex current-state surfaces

This protocol refines the communication domain under WSP_97. It does not replace
WSP_97 or create an alternate execution authority.
