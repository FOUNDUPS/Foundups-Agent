# Petition campaign intake and execution plan

Stage: local prototype source; installed-host qualification remains separate.
Owner: existing Social Media Orchestrator / FoundUp Campaign Operator.

## Commands and conversational entry

```text
social campaign petition action=preview
social campaign petition action=plan petition_url=https://www.change.org/p/example
social campaign petition action=plan petition_url=https://chng.it/example platforms=x,linkedin,facebook,youtube
RedDog, let's launch a petition on this
```

The last request returns `awaiting_petition_url`. An explicit public link gives
`intake_ready`, with `petition_verified=false`. These are planning results, not
launch outcomes. `action=publish`, `dry_run=false`, unknown/duplicate command
parameters and ambiguous multiple links reject. Conversational petition entry
cannot dispatch the existing research or AntifaFM publishers.

The async leaf `src/petition_campaign.py::execute_petition_campaign` returns
`petition_campaign_plan.v1` without a model, environment/config read, browser,
provider call, storage write or scheduler. The existing outer CLI/runtime may
still perform its normal audit and permission work. Do not place secrets in
commands. URL tracking parameters are excluded from the returned plan and ID;
this does not redact the outer caller's original command log.

Supported public-link hosts: Change.org (`change.org`, `www.change.org`), its
short links (`chng.it`), and Action Network (`actionnetwork.org`, `www.actionnetwork.org`).
Only HTTPS public petition paths are accepted; credentials, explicit ports,
login paths, traversal and confusable domains reject. Short links need actual
approved resolution before use. This planner fetches no URL and makes no
network-security guarantee for a future reader.

## Required campaign flow

| Phase | Evidence required | Implemented here |
| --- | --- | --- |
| Intake | Principal's objective and public petition URL | Validated plan/identity; link remains unverified |
| Verify | Actual petition owner/title/content; claim/source map; current corrections | Pending approved readback |
| Bind | Existing social provider IDs, account ownership, applicable policy | Disabled account slots; no binding |
| Draft | Source-grounded posts, institutional handles, optional assets and exact copy revision | Work instructions; generation not invoked |
| Admit | Exact account/copy/revision, budget, authority and stable effect identity | Required; no grant inferred from this plan |
| Execute | Qualified existing transport and durable claim before publication | Not implemented for petitions |
| Verify outcome | Provider URL/readback; reconcile uncertain writes before retry | Required; no synthetic success |
| Learn/update | Verified responses, aggregate traffic/signatures and supporter preferences | Not wired; schedule only when requested |

`brief` retains the documented CampaignBrief vocabulary (`title`, `cta`,
`platform_matrix`) as a small petition-specific projection. It is not the full
historical CampaignBrief or CampaignWorkOrder schema and does not satisfy native
admission. `plan_revision` hashes the projection; it is not a signature or
provider idempotency key. A derived campaign ID identifies a canonical public
URL; the caller may supply an explicit stable ID for link migrations.

The in-memory plan contains no campaign persistence, publication ledger,
authenticated receipt, live account verification, actual drafts, analytics or
activation. All platform slots are disabled. X/LinkedIn have existing owners;
their presence is not a generic petition publication grant. Facebook/YouTube
slots name requested future work and do not assert qualified transports.

## Local browser setup — reuse, then qualify

For this campaign, the principal is creating the petition and will supply its
link. A public-link campaign intake needs no creator password or signup browser.

For later create/manage requests, reuse
`modules/infrastructure/foundups_selenium/src/foundups_driver.py::FoundUpsDriver`
and the current browser-action owner instead of starting a second browser daemon.
`connect_or_create(port, profile_dir, url)` exists; it is not a petition login
adapter. In the inspected ActionRouter, `PLAYWRIGHT` is an enum/counter label;
`_execute_with_driver` distinguishes Selenium from its vision path, with no
separate Playwright execution branch. Do not claim a working Playwright signup
integration from the enum alone.

Qualification acceptance for a bounded local-browser adapter:

1. Use the principal's authorized local browser and a dedicated persistent
   profile. Keep any debugging endpoint loopback-only; do not expose it publicly.
2. Verify target origin and non-secret form controls. Fill only authorized
   non-secret fields. Do not send private screenshots to a vision provider by
   default or introduce stealth/fingerprint changes to defeat a site safeguard.
3. Pause for human password creation, required account terms, CAPTCHA and MFA
   under the active tool policy. For Google, use the existing phone-push skill.
4. Resume in the same profile/tab and verify positive signed-in identity on the
   target site. Retest after a controlled restart. Never export cookies or put
   credentials, browser profiles or personal registration data in Git.
5. Save/reopen one authorized draft; verify title/body/creator and persistence
   separately from the later publish/readback step. Stop on session loss.
6. Retain a redacted receipt of each verified transition and failure, then
   forward only qualified operations through the existing execution owners.

This is an acceptance contract, not a browser implementation or deployment.
ChatGPT's observed handoff session ended; external login did not yield observed
agent access. No causal evidence links that failure to vulnerability mitigations.
A different automation library does not itself repair the hosted handoff.
