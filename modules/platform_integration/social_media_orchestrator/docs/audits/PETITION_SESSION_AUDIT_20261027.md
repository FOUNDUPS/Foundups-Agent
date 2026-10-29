# Petition session audit — 2026-10-27 JST

Baseline: main `50cd2ff612627ebdcd95df63eded72115c297977` (PR2236).
Scope: this session's petition setup and reusable social campaign orchestration.
Campaign-specific allegations, personal registration details and supporter data
are excluded from this public audit; the prepared campaign copy remains private.

## Verified work before this audit

| Surface | Evidence | Actual status |
| --- | --- | --- |
| Campaign research and copy | Prepared private draft with sources, demands, confirmation/update text and social drafts | Prepared; original-media/correction and advertiser verification remain open |
| Action Network setup | Registration fields entered; later agent browser still showed signup/login | No verified authenticated access or saved petition |
| Change.org pivot | Title/body and scope entered; login-to-save page observed | Last agent-side draft was unsaved; no verified public URL |
| Browser handoff | Principal's screenshot states the cloud-browser session ended | Observed failure; root cause unestablished |
| Secure login attempt | Capability returned `locator_invalid` after reinspection | No successful authentication result |
| Reusable campaign skill | Existing `foundup_campaign_operator/SKILLz.md` extended; petition playbook added | Instruction prototype |
| Skill discovery | `.claude/skills/launch-petition`, generated `.agents` mirror and OpenClaw workspace entry/hash manifest | Published source; no installed-host activation proof |
| Repository publication | PR2236 squash merged after all22 exact-head checks passed | Main50cd2ff; source publication only |
| Petition/social/email effects | No verified petition action ID, public URL or provider publication receipt | None established by this session |

The initial push containing the campaign narrative was rejected by automatic
approval review for that public destination. The narrative was excluded before
publication; only the generic workflow was published. A subsequent scan failure
was an exact reviewed-finding fingerprint changed by a bridge changelog edit.
The bridge changelog was restored; no scanner rule or baseline was relaxed.

## What was missing

The first change created instructions, not an autonomous campaign executor.
`social_campaign_adapter.py` supported only AntifaFM and the research campaign.
Its conversational controller had no petition shortcut. There was no petition
intake validator, active campaign state machine, campaign-specific browser
signup adapter, generic petition publication path or campaign analytics loop.

Existing social/browser functionality is reusable groundwork, not proof of this
campaign's account binding or end-to-end operation. Selenium profile/session
reuse exists. The inspected ActionRouter has no independent Playwright branch.
No new local browser, secret store or scheduler is justified by the evidence.

## Continuation implemented by this change

- An effect-free petition intake/planning leaf under the existing social owner.
- Strict `social campaign petition` commands plus bounded conversational launch
  phrases routed through the existing conversation/social controllers.
- Validated Change.org/short-link/Action Network public URLs, stable canonical
  campaign identity and a plan revision; no claimed URL verification.
- Explicit pending source checks, account binding, drafting, native admission,
  publication/readback and outcome review; all provider slots disabled.
- Command, no-effect and URL-boundary tests; preserve existing campaign routing.
- Regenerated backend dependency closure includes the new leaf and exact source
  hashes. The bounded source contract grows from1,471 to1,472 members and from
  328 to329KiB manifest bytes for LF/CRLF compatibility; signer authority,
  individual2MiB and total32MiB limits remain unchanged. Installation is unproved.
- Updated Change.org adoption/update instructions and a local-browser reuse
  qualification contract in [the runbook](../PETITION_CAMPAIGN.md).

This continuation is still plan-only. It does not create accounts, save platform
drafts, call models/providers, persist a campaign, sign a work order, publish
posts or activate a daemon. Source tests are not live-host evidence.

## Remaining work and acceptance

1. Adopt the principal's public petition URL; inspect its actual contents and
   organizer. Do not restart petition creation or require another login just
   to read the public destination.
2. Reconcile the source/claim map, institutional contacts/handles and current
   responses; derive the exact campaign brief and source-linked social copy.
3. Bind existing authorized provider identities and scope through current
   policy/credential owners. Distinguish login, posting access and authority.
4. Extend the existing private campaign/publication owners for durable state,
   copy revisions, stable jobs and uncertain-write reconciliation; do not create
   a competing scheduler or public ledger of supporter data.
5. Qualify a generic petition posting operation behind existing admission and
   transport owners. Demonstrate one exact authorized post plus readback before
   extending accounts, platforms or cadence.
6. Qualify the optional local-browser create/manage adapter against the runbook
   only when that workflow is needed. Human credential/MFA/CAPTCHA/terms steps
   remain subject to the active tool policy.
7. Connect aggregate analytics, corrections, supporter updates and retained
   procedural learning. Change.org notifications are platform updates, not an
   exported supporter mailing list or an Action Network autoresponder.

The principal now owns petition creation and will supply its link. Work that
does not depend on that link continues; publication cannot honestly be marked
complete without destination, account, source, authority and readback evidence.

## Retrieval and validation boundary

The original parent scratch checkout was no longer available, so its worktree's
Git pointer was broken. A fresh clone of current merged main recovered the
source; no peer files were reset. WSP00 V2 lacked torch; documented tracker
fallback/check passed with detector witness ABSENT. Source-bound lexical
retrieval reported UNKNOWN freshness/index gap and workspace-overlay authority;
current-owner reads, not semantic acceptance, ground this audit. Historical
CampaignBrief and unrelated phone hits were noise; the full historical contract
remains non-executing and is not falsely claimed implemented by the small plan.
Validation results are retained in the owner ModLog and test documentation.
The connected campaign/routing/projection/manifest selection passed121 tests
and76 subtests. Separately,8 generator/index cases and3 focused Node compatibility
commands passed after the exact member/byte bound update. Skill structure,
wardrobe hashes, source/test registry generation and instruction links verify.
Hosted CI/publication and installed-host qualification remain separate evidence.
The first continuation scan flagged a dummy basic-auth negative test and38
manifest metadata rows. The password fixture was removed; each manifest row was
matched to its exact staged source digest and prior reviewed binding. Only
whole-file/rule/line fingerprints were refreshed, with metadata-only evidence;
scanner rules were preserved. A fresh hosted result remains required.
