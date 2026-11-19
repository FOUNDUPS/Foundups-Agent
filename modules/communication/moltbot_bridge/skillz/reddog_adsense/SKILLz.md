---
name: reddog_adsense
description: Verify website ownership in an existing AdSense account without enabling ads; distinguish site review, serving eligibility and YouTube payments.
agents: ["0102"]
intent: GENERAL
intent_type: GENERAL
version: "1.0.0"
promotion_state: prototype
category: workflow
---

# Red Dog website AdSense operations

## Scope and owner

Apply WSP 00, WSP 97 and WSP 95. This is a prototype operator procedure owned
by `modules/communication/moltbot_bridge`, not an executor or account authority.
Reuse the existing signed-in account, website source/deployment owner and private
Drive AdSense record. Retrieve current evidence before acting. A request to save
this skill does not authorize changes to sites, accounts, DNS or ad settings.

Use for website ownership verification, Add site and interpreting site status.
Exclude ad placements, Auto ads, traffic/revenue promises and payment setup.
A website in Sites is not proof of ownership, approval or active monetization.

## 1. Resolve the account, site and authorization

- In the signed-in AdSense website, open **Sites**. Confirm the intended account
  privately; never copy its account or publisher identifiers into public records.
- Inspect the existing list and exact owned root. Deduplicate before **Add site**
  (the UI may say **New site**). Add the root only if absent and authorized;
  do not add a page path, invent a domain, create another account or delete entries.
- Preserve Blogger/host-partner linkage. Use that partner's setup rather than
  treating its hosted blog as an independently controlled apex. For YouTube,
  start from YouTube Studio's existing Earn/payment association, not website Sites.
- An offer or promotional email does not establish account entitlement or need.
  Use actual account screens. The web account may be opened on a phone browser;
  a PC is useful for source/hosting changes, not an account-entitlement requirement.

## 2. Establish public reachability and the actual content owner

GET the exact URL, following and recording redirects. HEAD rejection alone is
not a failed website. Inspect final status, public HTML, canonical destination,
TLS, login requirements and frame wrappers. Separate origin failure from a
crawler/tool restriction. A redirected profile, parked root, inaccessible page
or framed child is not proof that the listed root has editable HTML.

Find the existing source, deploy project and current live revision. Check active
workers/PRs and reconcile newer published content before a bounded change.
Do not overwrite a live site with an older checkout. A tag inside a framed child
is not evidence that its wrapper/root contains the tag. Do not remove redirects,
change DNS, robots, authentication, indexing or crawler/security controls just
to pass verification. Record a blocker and the existing owner instead.

## 3. Choose only an offered verification-only method

Read the methods actually offered by that site's AdSense screen.

1. Prefer its **meta tag** when available: use the exact account-generated tag
   in the existing site's HTML head/metadata owner. Do not guess its value or
   substitute a generic Search Console tag. Keep actual publisher IDs out of
   this skill and public audit documentation; any site-source insertion requires
   the separately authorized publication scope and private handoff.
2. If meta verification is unavailable or unsuitable and **ads.txt** is offered,
   inspect the existing root file and response first. Append only the exact
   account-provided record if missing; preserve all existing sellers, comments
   and records. If already present, do not duplicate it. Verify a real text
   response rather than an SPA catch-all HTML page. ads.txt declares an authorized
   seller, so confirm that choice is within the requested scope before publishing.
3. Do not install the ad script, enable Auto ads or choose placements for an
   ownership-only request. If the remaining UI requires advertising setup,
   stop at that boundary. Do not invent a DNS verification option from another
   Google product or change DNS because a remembered guide mentioned it.

Use the existing site's authorized release path, narrowly scoped. Read back the
published head/root file at the exact domain before selecting **Verify**. Preserve
cache/redirect/crawl behavior and report access blocks without bypassing them.

## 4. Verify, then distinguish the three outcomes

Record separately, using observed UI wording and observation time:

- **Ownership:** verified, failed or not yet checked, including the exact target.
- **Site review:** not requested, requires review, getting ready/pending, approved
  or rejected. Submit **Request review** only when separately within the current
  task's authorization; ownership verification alone is not policy approval.
- **Ad serving:** observed configuration/status, or not inspected. Neither a
  successful Verify nor Ready means ads were installed or are earning revenue.

If verification fails, inspect published bytes, destination and provider error
once, then make only an authorized bounded correction. Do not repeat Add site,
blindly retry, create duplicate records or switch methods/accounts without
checking existing state. Keep pending review pending; no repeated submissions.

## 5. Private continuity and separate payment lane

Update the existing private Drive AdSense record only when authorized. Keep short,
newest-first dated action/result/next-step receipts and approved private evidence
links there, not competing documents. Verify saved content and sharing audience.
Public repository receipts contain only generic workflow/test evidence: no real
publisher IDs, account/email/bank/tax details, screenshots, case links or private
Drive URLs. Do not copy financial identifiers even into routine receipts.

Website verification does not set up YouTube payouts. Report any YouTube Earn,
AdSense for YouTube payment-account, identity/tax, threshold or payment-method
blocker separately. Do not alter payment recipients, banking or tax information
under website-verification authority; follow that separate task's confirmation
and handoff rules.

## Discovery and acceptance boundary

Canonical: this module-owned `SKILLz.md`. The `reddog-adsense` Claude/Codex
entrypoints point here; NAVIGATION and the existing WRE registry locate it.
The registry remains **prototype**, with no executor or promotion receipt.
Filesystem discovery's location-derived labels are not runtime admission.
Do not add a fake CLI to `holo_index/docs/command_rolodex.json`: this procedure
has no command executor. Source-bound HoloIndex lexical retrieval can locate
these instructions; unknown/stale semantic freshness must remain explicit.

A merged skill, discovery hit or local test does not prove phone installation,
fresh-session loading, live account verification or an admitted autonomous run.

## Official references (refresh against the actual UI)

- [Add a site and verification methods](https://support.google.com/adsense/answer/12169212?hl=en)
- [Site-management states](https://support.google.com/adsense/answer/12131223?hl=en)
