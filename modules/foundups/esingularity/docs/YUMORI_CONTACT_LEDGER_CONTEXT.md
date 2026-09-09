# YUMORI.me Contact Ledger Context

**Status:** Operational context contract; live state remains external.

## Why this exists

YUMORI.me outreach is active across city government, council, universities,
researchers, media, businesses, civic groups, legal reviewers, local community
organizations, tourism/hospitality operators, and other stakeholders. The
campaign needs one place to answer questions such as:

- Who have we contacted?
- What was the first email?
- Did we send a follow-up?
- Did they reply?
- Was the reply human, automated, negative, positive, or a delivery failure?
- What is the next action?
- Which Gmail thread contains the evidence?

The live system is deliberately split so the spreadsheet is an index rather
than a duplicate mailbox.

## External source names

Agents with connected Google access should resolve these exact titles:

- `YUMORI.me Contacts` — Google Sheet; operational contact ledger.
- `YUMORI.me Moshpit` — Google Doc; dated campaign activity/milestone record.
- `YUMORI.me Contacts Pics` — Google Doc; original contact/business-card imagery.
- Gmail account containing YUMORI.me outbound and inbound correspondence.

Do not hard-code Drive file IDs or private contact dumps into the public repo.
Resolve by exact title through the connected account and verify the selected
file before reading or writing.

## Current sheet contract

### `Contacts` tab

The first fourteen columns are contact/context fields:

```text
Contact ID
Name (JP)
Name (Romaji)
Organization
Role / Context
Email
Phone
Address / Area
YUMORI.me Role
Last Interaction
Next Action
Source
Verification
Notes
```

The communications roll-up extends the row with:

```text
Primary Gmail Thread
Email Events
First Outbound
Last Outbound
Last Inbound
Email Status
Last Subject
Last Gmail URL
Delivery
Last Reply Summary
Email Follow-up
Last Email Sync
```

`Contact ID` uses the stable `YMC-####` form. Never reuse an ID for a different
contact.

### `Email Log` tab

The event ledger uses:

```text
Message ID
Thread ID
Contact ID
Direction
Date (JST)
From
To
CC
Subject
Event Type
Snippet / Note
Status
Gmail URL
Sync Date
```

The canonical uniqueness constraint is Gmail `Message ID`, not subject text.
Gmail `thread_id` is the canonical conversation-lineage key for grouping the
first outbound, follow-ups, inbound replies, and closure in one conversation.

A single Gmail message can involve many contacts through To/CC. The event row
must preserve those addresses. Contact roll-ups may associate the same Gmail
message/thread with more than one contact, but the Email Log must not create
fake duplicate message IDs merely to represent CC membership.

## Canonical concatenation model

```text
Gmail message_id  -> unique communication event
Gmail thread_id   -> conversation sequence
normalized email  -> contact-route join
YMC Contact ID    -> stable spreadsheet entity
Moshpit date      -> material campaign milestone
```

No extra email signature/index token is necessary. Gmail already provides the
stable lineage keys.

## Status vocabulary

Use concise operational states rather than free-text ambiguity:

- `NO EMAIL`
- `SENT`
- `AWAITING`
- `HUMAN REPLY`
- `AUTO ONLY`
- `BOUNCED`
- `CLOSED`
- `NEEDS VERIFICATION`

When an old route bounces and a corrected address is successfully resent, the
contact-level active status should reflect the active route (`SENT`/`AWAITING`)
while the old bounce remains preserved in delivery history/notes.

## Truth labels

Apply WSP 97-style distinctions to contact notes and campaign claims:

- **OBSERVED** — directly present in Gmail/Drive/current official source.
- **INFERRED** — reasonable interpretation, explicitly labeled.
- **STRATEGY / PROPOSED** — intended next action or project concept.
- **NEEDS_VERIFICATION** — source unavailable, contradictory, or incomplete.

Examples:

- An email being in Sent is OBSERVED outbound activity.
- No bounce does not prove delivery/readership.
- An automatic reply is not a human response.
- A polite meeting or discussion does not equal support or commitment.
- A modeled project cost or floor use remains a proposal until independently
  verified/approved.

## Campaign context pointer

The contact ledger is part of the registered `esingularity_001` FoundUp. For
current project context, retrieve the module README/INTERFACE/ROADMAP/ModLog,
public claim audit, and connected `YUMORI.me Moshpit` before drafting outreach.

The stable public framing is the question:

> Can compute help save an onsen, revitalize a region, and create a repeatable
> regional model for Japan?

The current civic action is an evidence-based request to preserve a short review
window and convene stakeholders before irreversible demolition advances. This
is not proof that the proposed reuse, compute capacity, economics, floor plan,
funding, or cultural program has already been approved.

## Retrieval phrases for HoloIndex / RedDog

This context should be discoverable from phrases including:

```text
YUMORI.me contacts
YUMORI contact ledger
YUMORI email log
YUMORI Gmail replies
YUMORI stakeholder outreach
YUMORI campaign communications
Save the Onsen contacts
Sukatto Land Kuzuryu outreach
YMC contact ID
RedDog YUMORI rolodex
```

The corresponding Skillz is:

`modules/foundups/esingularity/skillz/yumori_contact_ledger/SKILLz.md`
