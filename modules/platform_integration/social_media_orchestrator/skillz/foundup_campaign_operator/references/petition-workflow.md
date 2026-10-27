# Supervised petition workflow

Owner: FoundUp Campaign Operator / Social Media Orchestrator. Stage: prototype
instruction. No Action Network API adapter, `social campaign petition` command,
resident trigger or unattended cadence is implemented by this document.

## Retrieve and prepare

1. Follow WSP 00/97. Retrieve current campaign records, existing platform actions,
   relevant sources and current platform help. Evaluate retrieval noise,
   missing artifacts, staleness and duplicates before changing anything.
2. Establish the objective, accountable institution, requested remedies,
   organizer, platform, authorized publication scope and reply-to identity.
   Use the existing CampaignBrief vocabulary. Ask only for essential gaps.
3. Maintain one campaign record through an approved private owner, using a
   stable campaign ID. A repository index may link only approved non-sensitive
   metadata. Keep credentials, postal addresses, raw conversations, personal
   trauma allegations, supporter identities and exports out of public Git
   without explicit authorization for that destination. Do not create a new
   public campaign ledger to hold private operational data.
4. Record each material claim with a source URL, publication date, observation
   date, relevant timestamp and status: verified / attributed / opinion /
   unverified. Inspect original media when available. A third-party transcript
   can support drafting but does not establish that original media was reviewed.
5. Distinguish what a segment says or omits from speculation about intent.
   Attribute survivor accounts and distinguish a criminal charge from a
   conviction. Do not imply an organization endorses the campaign without proof.
   Verify current advertisers and the placement/platform/date before naming
   them as sponsors; a viewer's ad observation alone does not establish a
   continuing sponsorship. Do not copy full transcripts into the repository.
6. Write finished title, target, description, petition letter, thank-you copy,
   confirmation email and social drafts. Make pending fields conspicuous.
   Use general public messaging, not persuasion tailored to an individual's
   political views or sensitive history. Never require abuse disclosures to sign.

## Authentication and handoff

1. Prefer a sufficient available connector; otherwise use the permitted browser.
   Verify the live official signup/login page and reuse an existing owned tab.
2. For account creation, fill only authorized non-secret details. The principal
   enters a new password and completes account terms, required verification
   and any CAPTCHA under the active browser policy. Do not invent a location,
   create a password for the principal, or request secrets in chat.
3. For a new login, follow the current secure-auth capability. Do not enter,
   inspect or persist credentials through ordinary automation. For Google
   authentication, load the established Google phone-push skill first.
4. If the principal explicitly requests control, use the documented takeover
   method and preserve the tab according to the browser's lifecycle rules.
   A normal website link opens an independent session unless proven otherwise;
   explain this before treating an outside login as shared access.
5. After handback, verify a positive signed-in signal on the target site and
   the intended organizer/account. A stale signup form, disappearance of a
   popup, or a verbal "logged in" is not authenticated-browser evidence.
6. If handoff loses access or secure auth rejects the form, record the actual
   observed state and capability result. Reinspect/correct selectors only within
   that capability's allowed recovery. Stop repeating a failing path; do not
   infer site bot detection, failed credentials, or successful login from this.
   Continue independent preparation and report `authentication_blocked`.
   Do not ask for passwords/cookies/API keys as a workaround.

## Action Network draft and launch

Consult [Creating petitions](https://help.actionnetwork.org/hc/en-us/articles/203112629-Creating-petitions)
before operating; labels and account entitlements can change.

1. Search the authenticated organizer's actions for the existing campaign.
   Reuse its draft/manage URL and action ID; never guess or fabricate them.
2. From Start Organizing / Actions, choose Petition. Enter the prepared title,
   accountable target, description and delivery letter. Verify the creator and
   sponsoring group: these determine who receives supporter data.
3. Minimize fields. Review the live consent language, signer-name visibility,
   delivery/export contents and privacy notice. Do not promise anonymity or
   data deletion that the platform has not established. Keep optional campaign
   updates distinct and honor the platform's unsubscribe/suppression behavior.
4. Save Draft and verify persistence by reopening it. Record the actual draft
   URL/ID and `draft_saved` only after readback; prepared local text is
   `prepared_local`. Inspect mobile layout, sources, target, form and thank-you.
5. Where available/enabled, configure one confirmation response. Later campaign
   updates are separate email actions or automation, not the same autoresponder.
   Inspect plan/group requirements and sender identity; do not buy an upgrade
   or alter DNS to unlock them. Verify a test only with an authorized test address.
6. Reconcile publication authority against the exact destination, purpose and
   final copy. Apply any action-time requirement in the active tool policy;
   do not invent another approval when existing authority is sufficient.
7. Publish only when material claims, signer/data settings and required
   authority are resolved. Verify the public action and record its canonical
   URL, action ID, copy revision and observed status. Do not create a real
   signature as a test without authorization.

## Distribute and learn

1. Prepare broad public posts for the existing authorized accounts. Verify
   institutional handles and advertiser relationships. Keep a respectful,
   factual call to sign; do not impersonate survivors or mobilize abusive replies.
2. Use admitted provider owners and existing grants. AntifaFM's dedicated
   publisher is station-specific and is not a generic petition transport.
   If no suitable admitted route exists, retain social drafts and report that
   gap rather than repurposing a grant or claiming automatic distribution.
3. Use a stable job identity per account/revision and the existing publication
   ledger when supported. Reconcile uncertain writes before retrying; verify
   provider URLs and do not duplicate posts after a timeout.
4. Record signatures, visits/source attribution, actual responses, corrections
   and unsubscribe outcomes without exposing supporter data. A published post
   is not proof of reach or impact. Schedule monitoring only when requested.
5. Retain the failure and successful recovery as concise procedural learning.
   Never promote a prototype to unattended execution based on a successful
   draft or one browser run.

## Receipt

Report a stable campaign ID; current stage (`prepared_local`,
`authentication_blocked`, `draft_saved`, `published_verified`,
`distribution_pending`); actual draft/public URLs when known; unresolved claims;
consent/sender status; attempted effects and readback; and exact next blocker.
An `authentication_blocked` record can have completed local drafts. Report each
artifact separately instead of marking the entire campaign complete.
