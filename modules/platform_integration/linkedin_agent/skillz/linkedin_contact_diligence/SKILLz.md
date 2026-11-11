---
name: linkedin_contact_diligence
description: Evidence-based professional due diligence for consequential LinkedIn contacts before sensitive disclosure, financing, partnership, or relationship decisions
version: 0.1.0
author: 0102
agents: [qwen]
intent_type: AUDIT
promotion_state: prototype
category: workflow
evals: []
---
# LinkedIn contact diligence

Read the [master routing contract](../../docs/LINKEDIN_ACTIVITY_ROUTING.md) and
the [shared review contract](../../docs/LINKEDIN_REVIEW_WORKFLOW.md). This skill
is a bounded research/audit child. It does not accept or reject a connection,
send a message, authorize disclosure, or establish that a person is legitimate.

## Trigger

Use this skill when a LinkedIn connection request, existing connection, inbound
message, introduction, or outreach target creates a consequential relationship
question, especially when the contact claims or offers:

- investment, family-office capital, project finance, fundraising or banking;
- government, institutional, infrastructure or strategic introductions;
- legal, financial, procurement, acquisition or partnership authority;
- access to investors, customers, compute, property, energy or other material resources;
- a role that would justify sharing non-public financial, technical, legal or
  government-facing project material.

A routine low-consequence connection does not require this audit. A senior title
alone is neither a trigger nor proof.

## Evidence collection

Start with the live LinkedIn profile/thread and prior relationship context. Then
use bounded public professional evidence appropriate to the claim, such as:

- official company or organization websites and leadership pages;
- corporate registries and government business records;
- regulator or professional-license records when the claimed activity makes
  those records relevant;
- named transactions, projects, publications, conference programs or press
  releases from identifiable organizations;
- reputable reporting and other primary-source records.

Search aliases or name variants only when necessary to resolve identity. Do not
collect sensitive personal data, family information, home addresses, private
accounts, unrelated litigation, or other material that is not needed to assess
the professional claim. Absence of a public footprint is not proof of fraud.

## Evidence labels

Every material statement in the diligence packet must be one of:

- **VERIFIED** — supported by a reliable public source tied to the same person/entity;
- **CLAIMED** — stated by the contact or their LinkedIn profile but not independently verified;
- **UNVERIFIED** — relevant claim searched for but not established by available evidence;
- **CONFLICTING** — credible sources materially disagree or identity linkage remains unresolved.

Keep allegations attributed to their source and separate them from adjudicated
findings. Similar names are not identity proof.

## Diligence packet

Return a compact private decision packet:

```text
CONTACT
Name:
LinkedIn URL:
Current relationship:
Claimed role:
Why diligence triggered:

IDENTITY / PROFESSIONAL FOOTPRINT
VERIFIED:
CLAIMED:
UNVERIFIED:
CONFLICTING:

BUSINESS / MANDATE
Current legal or advisory entity:
Official company footprint:
Relevant registrations/licenses:
Named transactions/projects:
Investor/customer/partner mandate evidence:

MATERIAL GAPS
- ...

CLAIMS TO TEST DIRECTLY
- ...

SAFE DISCLOSURE LEVEL
PUBLIC_OVERVIEW_ONLY | NON_SENSITIVE_DECK | NDA_STAGE | HOLD

NEXT STEP
PROCEED | ASK_FOR_EVIDENCE | HUMAN_REVIEW | HOLD

DRAFT 0102 RESPONSE
...
```

Do not produce a numerical "legitimacy score." Evidence quality and consequence
determine the next step; a polished profile, photo, title, follower count or model
confidence never establishes identity or authority.

## Capital and project-finance contacts

For an investor, family-office representative, placement adviser, project-finance
contact or capital intermediary, explicitly test the claims that matter before
non-public financial disclosure:

- legal entity or advisory firm used for the engagement;
- investor/family-office mandate they actually represent;
- typical check size and geography;
- preferred project stage and instrument;
- whether the mandate covers infrastructure/project finance, equity, debt or
  another structure;
- compensation/fee model and whether payment is contingent on capital raised;
- two or three comparable transactions or projects they personally worked on;
- relevant regulatory status when the proposed activity would require it.

Missing public evidence is a reason to ask a measured question, not to accuse.
Financial, legal, investment-term or contractual decisions remain human-review
items under the shared LinkedIn authority contract.

## Disclosure boundary

Default to **PUBLIC_OVERVIEW_ONLY** until the contact's claimed capacity and need
for deeper information are established. Do not disclose private investor lists,
government correspondence, non-public financial models, legal strategy,
credentials, security details, personal contact data or confidential project
documents merely because a contact appears relevant.

A later disclosure decision must be separately authorized and should follow the
minimum-necessary principle.

## Response drafting

When clarification is appropriate, draft as 0102, the monk's Digital Twin and
project operator. State what was and was not found without implying that absence
proves wrongdoing. Prefer direct professional questions that let a legitimate
contact establish mandate and fit.

Keep the project description accurate: distinguish proposed, feasibility,
financing, approved, operating and funded states. Do not imply secured capital,
government approval, site feasibility or operating infrastructure without
evidence.

## Continuity and privacy

Pass only the material outcome and next action to
[linkedin_continuity](../linkedin_continuity/SKILLz.md). Do not store contact
dossiers, private message bodies, sensitive personal information or raw web-search
results in public Git, reusable skills, campaign logs or training data.

A reusable lesson may update this skill through the normal dedicated-branch/PR
workflow, but one person's dossier never becomes skill content.
