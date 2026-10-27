# Soro / Social Media DAE audit — 2026-10-27 JST

Source baseline: `84f069bdac3fef9c84b5e7cc78b08b4d0b4b9a9e`.
Authority: 012 requested competitor research, repository audit and implementation.
Scope: public Soro behavior and Foundups-Agent source. No Soro account, private
implementation, provider account, local Windows runtime or live posting tested.

## Finding

The identified product is **Soro at trysoro.com**, an SEO/content autopilot.
Its strength is packaging an end-to-end marketing workflow. Foundups-Agent has
many execution components, but a general evidence/brand/content/delivery/outcome
loop is not demonstrated. More agents or a second scheduler will not close that
gap. Soro parity also does not establish the broader conversational social DAE.

### Public evidence

| Source read on audit date | What it supports | Limit |
|---|---|---|
| https://trysoro.com/ | Website onboarding, keywords, brand style, daily articles, CMS integrations and languages | Vendor claims; ranking/traffic examples not independently measured |
| https://trysoro.com/pricing | Calendar, review/autopublish, research, linking, image creation, configurable brand | No evidence that a 100/100 score guarantees ranking; do not reproduce that claim |
| https://apps.shopify.com/soro | Actual app listing, developer DIGIMERI OU, content/research interfaces and claimed publishing workflow | Listing existence does not verify all features or business outcomes |
| https://wordpress.org/plugins/soro-seo/ | Documented WordPress integration using site-side configuration | Not inspected or installed in our runtime |

The Shopify listing includes individual reports of manual editing and repetitive
content. These are customer observations, not controlled tests or universal
product findings. Public primary pages reviewed do not establish autonomous
replying, negotiation or a safely self-improving agent. Facebook/Instagram
auto-sharing appears in third-party reviews; it remains unqualified in this audit.

## Repository comparison

Paths below are relative to the repository root.

| Capability | Existing owner/evidence | Missing or weak connection |
|---|---|---|
| Brand identity | `modules/foundups/brand_context.schema.json`; registered-target grounding/verifier | Branding is explicitly not execution authority; production brand payloads and content voice learning need qualification |
| Audience and topic research | Public retrieval tools; existing social/LinkedIn research skills | No demonstrated campaign-scoped demand/SERP/Search Console intake that continuously selects content |
| Content preparation | `src/content/content_orchestrator.py` formats existing copy | Previously no reusable campaign brief, source-bound topic package or cross-platform editorial calendar here |
| Marketing workspace | `modules/foundups/kosei/ROADMAP.md`, `INTERFACE.md` | Roadmap says scaffold; dashboard claims are not a working marketing control surface |
| Distribution | `simple_posting_orchestrator.py`, `multi_account_manager.py`, unified interfaces and platform agents | Stream/commit workflows are not a general brand marketing lifecycle; preserve legitimate separate triggers |
| Verified X publishing | `unified_x_interface.py`, `core/publication_store.py`, AntifaFM pilot | Exact provider identity, durable claim and readback exist for the bounded pilot; no generic CMS workflow follows |
| Legacy adapters | `platform_adapters/twitter_adapter.py`, `linkedin_adapter.py` | Authentication/post methods simulate success; generated IDs must not count as delivery evidence |
| History | `src/social_media_orchestrator.py:get_content_history` | Returns sample posts; unsuitable as production reporting |
| Calendar/runtime | Existing scheduling owners; `scripts/launch.py` fires WRE social skills on cadence | A running cadence alone does not prove connected campaign work, real delivery or learning |
| Publication safety | OpenClaw permission/containment + WRE admission | Independent inert reproduction confirms denied SOCIAL and failed preflight can reach LinkedIn through conversation fallback; separate fail-closed repair required |
| Feedback | Video-comments feedback owner; WRE PatternMemory; publication receipts | Operational outcomes differ from impressions/clicks/conversions; no demonstrated joined cross-platform marketing feedback/promotion loop |
| Images/video | Existing project imagery, media generation and video evidence workflows | Need campaign/claim/asset provenance and reuse; never invent a real project facility |
| CMS/SEO | Existing websites and content surfaces | No generic qualified WordPress/Shopify/Webflow publishing + readback path found in this social module; metadata, canonical links and internal links need a concrete site target |

`src/` paths in this table belong to this module unless otherwise qualified.
Source evidence is narrower than production state. Documentation may describe
intent that is not wired; simulated IDs, dry runs and planned dates are not live
receipts. The Windows resident processes, sessions and installed source were not
available in this audit environment.

Independent source-bound routing reproduction reached an inert LinkedIn handler
once after each of two failures: denied SOCIAL permission, and failed WSP preflight.
The process loop rewrites the category to CONVERSATION before the conversation
social controls execute. This is a source-level security defect; the reproduction
performed no provider mutation. Its repair is a separate specialized change.

## Reconstructed workflow and chosen implementation

The public Soro behavior suggests this sequence (inference, not knowledge of its
private architecture): site/brand intake → demand/topic research → calendar →
draft/review → CMS publication → promotion → performance review.

Preserve our ownership chain: OpenClaw intent/admission → WRE execution owners →
existing content and qualified platform adapters → provider readback → existing
durable memory/outcome owners. Brand text and retrieved pages are data; neither
can authorize an action, supply credentials or change routing.

### Implemented slice: reusable editorial packages

- Extend `content_orchestrator.prepare_campaign`; use the existing SOCIAL campaign
  adapter through `social campaign content action=prepare brief='<JSON>'`.
- Compile an explicit FoundUp-scoped brand projection, audience, objective, CTA,
  source excerpts and editorial topics into bounded dated X/LinkedIn drafts.
- Rank supplied editorial priorities deterministically; deduplicate equivalent
  evidence sets. No invented keyword volume, optimal-time or ranking score.
- Keep source excerpts and URLs intact. Withhold overlength drafts instead of
  cutting a qualifier/link. Length checks are raw Unicode prechecks; actual
  provider weighting remains pending, including Japanese/emoji X copy.
- Bind the whole output by a deterministic package revision; keep the value
  explicitly non-authoritative. Return measurement join keys for later owners.
- Reject cross-FoundUp evidence, unsupported fields, live flags, duplicate JSON
  keys, malformed/control/surrogate strings, oversized payloads and naive dates.
- Reuse the canonical brand schema's identity/locale semantics as a **projection**;
  full registry verification stays with its current owner. No second registry.
- Source evidence remains caller-supplied/unverified. Brand rules are carried for
  review, not claimed to be learned or mechanically enforced. Dates are proposed
  absolute intervals, not timezone-local recurring appointments or booked slots.
- No model, network, credential, host configuration, database, scheduler, browser
  or publisher use in package compilation. No new daemon or memory system.

### Selection / WSP 15 allocation

Selected package layer: C3 + I4 + D3 + Impact4 = **14/P1**. Need: bridge existing
brand/source concepts to reusable content. Affordability: standard-library-only,
bounded inputs, existing router/content owner. Deferability: useful before any
generic autonomous publisher; live publication remains blocked on authority and
transport qualification. First focused/module tests, then connected campaign
regressions, generated runtime/test registry checks, independent review and CI.

Alternative: create a second marketing agent/scheduler/database. Rejected because
those owners already exist. Alternative: expose legacy simulated publishers.
Rejected because fabricated success IDs cannot establish effects. Alternative:
start with a CMS writer. Deferred until a concrete site and scoped credential,
admission and readback contracts are available. This local source change is not
runtime-distributed WRE work; future admitted cadence execution must use WRE.

## Remaining build sequence and acceptance

| Order | Existing owner to extend | Work and acceptance |
|---|---|---|
| 1 | OpenClaw permission/process/controller | Qualify and repair denied mutations reaching a conversation social adapter. Unauthorized action must terminate with zero provider/model/executor calls; preserve permitted conversation controls. |
| 2 | Existing registry + grounding + AI Gateway | Resolve real FoundUp brand context and approved public sources; add revisioned voice examples and factual claims. Test source injection as data, revoked/stale source rejection and brand isolation. No brand text grants execution. |
| 3 | Existing retrieval + content owner | Collect measured demand/keyword inputs with provenance, time and source. Generate original articles and short variants through the configured model owner. Evaluate facts, voice, rights, locale and source citations; do not turn editorial priority into fabricated search volume. |
| 4 | Existing scheduler + AgentDB/WRE queue | Persist admitted exact package/account/revision jobs in existing records. Collision-aware preview, budgets, quiet times, durable acknowledgement and restart/replay safety must precede resident apply. |
| 5 | Existing unified adapters + publication receipt owner | Generalize only qualified transports; require exact account identity and provider readback. Retire or clearly fence simulated legacy entrypoints without breaking stream/commit consumers. Unknown create outcome reconciles instead of resending. |
| 6 | Concrete FoundUp website/CMS owner | Add one chosen CMS transport and metadata/link/media package; least-scoped existing credential resolution, idempotency, saved-content readback and rollback. Add other CMSs only after first live proof. |
| 7 | Existing outcome/memory owners | Join provider account/post/package revision to timestamped impressions, clicks and conversions. Missing means unknown, not zero. Independent evaluation and bounded promotion/rollback before changing strategy or cadence. |
| 8 | Existing Kosei/PlayFoundUps surfaces | Show sources, drafts, approval state, upcoming slots, delivery receipts and measured outcomes in one mobile workflow. Reuse architecture; no separate marketing portal/database. |

None of the remaining rows is declared complete by the package compiler. No
whole-system completion percentage or unattended-production readiness is claimed.

## Verification / evidence boundary

WSP_00 V2 script attempted; failed because torch was absent. The documented
torch-free tracker fallback opened the gate (`mathematical_formulas`); no detector
witness is claimed. HoloIndex source-bound lexical bundle succeeded with
`freshness=UNKNOWN`, `index_gap_detected=true`, `workspace_overlay`; current source
reads/rg supplied exact ownership evidence. No semantic reindex/authority change.
Initial lexical results were campaign-heavy and omitted the existing content test
scaffold; direct module/test inventory repaired that retrieval omission.

The old `tests/test_content/content_orchestrator.py` had an invalid Windows-style
import and two empty assertions. Replace it with substantive offline package tests;
preserve all unrelated tests. TestModLog and tests README own exact run results.
Independent verifier found identity/locale mismatches and a decoded surrogate
serialization defect; both were repaired. Raw/provider length distinctions and
URL syntax limits were also made explicit. Static URL checks do not resolve DNS,
read a page, verify rights or authenticate its claims.
