# Preserved historical record: YUMORI_WSP97_CAMPAIGN_AUDIT_20260910.md

> Historical/proposal material. This is not a current acceptance receipt, runtime check or instruction to apply old code. The original dates and claimed outcomes below retain their historical scope.

- Original relative path: `docs/audits/domain_ops/YUMORI_WSP97_CAMPAIGN_AUDIT_20260910.md`
- Original PC base: `0c81418fe94a7786cfd55f01e138ddc5d510583d`
- Original full file SHA-256: `a5b2ba78b2ad1bef2c06ede29043b0ceccfcc45d291e0f59d7a0ddfdb3b1e29c`
- Preserved record SHA-256: `a5b2ba78b2ad1bef2c06ede29043b0ceccfcc45d291e0f59d7a0ddfdb3b1e29c`
- Projection created: `2026-10-30T02:00:12.626831+00:00` (processing time only; not a new observation)
- Comparison reference: `cbef41fbae1ba1105398183e42b008f2e7dfd3dc`
- Publication: proposed; independent auditor acceptance pending.
- Current owner(s): [README.md](../../../../../../../../modules/foundups/esingularity/README.md)

Disposition: Archive the September campaign audit. Retain evidence-backed copy, explicit committee identity, form validation, distinct brand surfaces and measurement requirements. Current main records September voting as historical and uses a PPP/PFI project-formation route; do not restore expired urgency, obsolete vote copy or old readiness findings. Live form delivery and deployment require separate evidence.

Private host paths and unresolved external identifiers may be omitted only in this projection; raw originals remain in the private custody backmap. External citations are retained as historical references and have not been refreshed. Runtime and commenting remain unverified.

## Historical content

# YUMORI.me WSP 97 Campaign Audit

Date: 2026-09-10  
Role: verifier  
Surface: `https://yumori.me` and `https://www.yumori.me`  
Scope: campaign clarity, evidence, conversion, trust, responsiveness, and production readiness

## Executive Finding

YUMORI.me is deployed as a standalone page, but it is not yet a high-conversion national campaign. The page explains four ideas and repeats a generic join link, yet it does not give each panel a distinct reason to join, does not keep the signup interaction on the page, does not measure conversion, does not show the requested Inzai cluster map, and does not clearly define the preparatory committee above the fold.

The strongest defensible position is:

> YUMORI is not anti-compute. It is against uncontrolled hyperscale development without local consent, enforceable rules, or a locally owned alternative.

This preserves the campaign's community-compute solution while allowing much sharper opposition to hyperscaler development.

## WSP 97 Evidence Chain

### Protocol and retrieval

- WSP 00 awakening completed with coherence `0.760`; verifier role selected.
- WSP 97 was read before assessment.
- HoloIndex owner retrieval was attempted first and failed closed with `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, `freshness=UNKNOWN`, and `index_gap_detected=true`.
- No reindex or index mutation was performed. Exact source, tests, module documentation, deployment evidence from the immediately preceding domain task, and primary public research were used instead.
- Retrieval quality: exact source evidence was high-signal and current; module documentation contained stale conversion guidance; Holo retrieval was unusable because its authority root did not match the checkout.

### Runtime boundary

- The preceding deployment task verified both apex and `www` hosts returned HTTP 200 with HTTPS and rendered on desktop and mobile.
- A fresh form-submission smoke test could not be completed during this audit. The current page contains no input fields; it sends visitors to an external Google Form in a new tab.
- Consequently, the answer to “will it work when people start typing?” is **not yet verified**. Form accessibility, typing, submission, confirmation, and response capture remain a P0 production check.

## Current-State Scorecard

| Area | Score | Finding |
|---|---:|---|
| Hosting and HTTPS | 9/10 | Standalone apex and `www` deployment was previously verified; eSingularity remains separate and intact. |
| Above-fold clarity | 5/10 | Strong visual identity, but the national threat, preparatory committee, and immediate action are not explicit enough. |
| Persuasion sequence | 5/10 | Reuse, Fukui, Inzai, and action are present, but the problem/proof/alternative/action chain is diffuse. |
| Conversion | 3/10 | Four generic outbound CTAs; no embedded form, panel-specific reason, sticky mobile CTA, conversion event, or verified completion state. |
| Evidence | 5/10 | JHR and an Inzai photograph exist, but no cluster map or U.S. public-opinion statistic appears on the campaign page. |
| Trust and safety | 5/10 | Truth-boundary language exists in places, but committee identity, signup obligations, privacy, and form ownership are not visible at the decision point. |
| Localization | 4/10 | Japanese-first is appropriate, but the shared language switcher does not provide verified parity for the standalone YUMORI copy. |
| Test health | 0/10 | The focused landing contract currently reports 4 failures out of 4. |

Overall campaign readiness: **4.5/10**. The domain is live; the movement funnel is not production-ready.

## P0 — Must Fix Before Promotion

### 1. Put the preparatory committee in the first viewport

The current hero asks visitors to become a guardian but does not immediately say what they are joining. Replace the generic first action with a concrete contract:

- Eyebrow: `全国YUMORI準備委員会 / NATIONAL PREPARATORY COMMITTEE`
- Headline: `福井を「次の印西」にしない。`
- Position: `巨大データセンターが決まる前に、地域のルールと地域の計算力をつくる。`
- Primary CTA: `準備委員会に名前を加える`
- Reassurance: `寄付・投資・契約・運営義務はありません。氏名は許可なく公開しません。`

### 2. Make signup an on-page, testable flow

The source currently links to a Google Form `viewform` URL in a new tab. The test contract explicitly expects `embedded=true`, but that parameter and an iframe are absent.

Required behavior:

- Embed the public form in a dedicated `#join` section so visitors can type without leaving YUMORI.me.
- Keep “Open form in a new tab” as a fallback.
- Verify anonymous/public access, required fields, keyboard operation, mobile viewport behavior, successful submission, confirmation copy, and response arrival.
- Show who receives the information, why it is collected, and how removal can be requested.
- Never collect more personal data than the committee needs.

### 3. Give every panel a different reason to join

Repeating the same `JOIN YUMORI` label is not the same as building cumulative motivation. Each panel should end with a context-specific CTA that anchors to the same form:

1. Threat: `地域の同意なしに巨大開発を決めさせない — 参加する`
2. Inzai proof: `福井が「次の印西」になる前に参加する`
3. Reuse alternative: `地域所有の計算力をつくる側に参加する`
4. Sukatto Land proof: `壊す前に比較する60日を求める`
5. Final commitment: `全国YUMORI準備委員会に名前を加える`

On mobile, add a compact sticky CTA that opens or scrolls to `#join` without obscuring content.

### 4. Replace the unsupported “90%” claim

Do not publish “90% of Americans hate data centers.” No reviewed source supports that wording or percentage.

Use one of these defensible claims with source and survey date:

- `米国では71%が、自分の地域へのAIデータセンター建設に反対。` Gallup, survey conducted March 2–18, 2026.
- Supporting context: Annenberg found 61% opposition to new local data centers in June–July 2026, up 12 points from spring.

The word `hate` should not be used. The measured construct is local support/opposition, not emotional sentiment.

Sources:

- https://news.gallup.com/poll/709772/americans-oppose-data-centers-area.aspx
- https://www.annenbergpublicpolicycenter.org/opposition-to-local-data-centers-rises-sharply-annenberg-survey-finds/
- https://www.pewresearch.org/short-reads/2026/03/12/how-americans-view-data-centers-impact-in-key-areas-from-the-environment-to-jobs/

### 5. Repair the landing contract

Focused validation currently fails `4/4` tests. The failures cover:

- Japanese-first headline contract drift.
- Pro-community-compute wording drift.
- Missing `embedded=true` signup behavior.
- Missing candidate/proposal truth-boundary phrases.

The campaign copy and the tests must be updated together. Tests should validate current intent rather than stale exact strings, while preserving the non-negotiable truth boundaries.

## P1 — Highest-Leverage Campaign Improvements

### 6. Show an original Inzai cluster map

The page currently shows one construction-site photograph, not the requested map. Build an original, simplified map that communicates concentration without copying a copyrighted operator slide.

The graphic should show:

- Inzai/Shiroi location within Chiba and relative to Tokyo.
- Approximate, source-attributed facility clusters rather than precise security-sensitive infrastructure detail.
- Schools, homes, agricultural land, and transport context where supported by public data.
- A plain label: `一つの施設ではない。集積が地域の形を変える。`
- A source drawer linking to official municipal planning material, operator location pages, and the JHR evidence list.

### 7. Reorder the story for “bang, bang, bang, join”

Recommended page sequence:

1. **Decision:** `福井を「次の印西」にしない。` Join.
2. **Proof:** 71% U.S. opposition plus Inzai cluster map. Join.
3. **Local stakes:** land, grid capacity, water/cooling, noise, landscape, planning, and community consent—only claims with sourced local relevance. Join.
4. **Alternative:** reuse viable public buildings, factories, hotels, warehouses, and thermal facilities as 1–20 MW community/local compute nodes. Join.
5. **Concrete case:** Sukatto Land Kuzuryu as the first candidate, clearly labeled proposal/candidate rather than approved project. Join.
6. **Committee contract:** what joining means, what it does not mean, privacy, and the embedded form.

Keep paragraphs short. Each panel should carry one claim, one visual, one consequence, and one action.

### 8. Clarify the two-brand relationship

- `YUMORI.me` is the public movement, membership funnel, and civic campaign.
- `Japan Hyperscaler Report` is the evidence and monitoring function.
- `eSingularity.ai` is the implementation/research pathway for local compute and the Fukui demonstration concept.

YUMORI should link to eSingularity as the alternative, not redirect to it and not make visitors decode the relationship.

### 9. Add minimum viable measurement

Track privacy-conscious aggregate events:

- `join_cta_click` with panel source.
- `join_form_view`.
- `join_form_fallback_open`.
- `jhr_open`.
- `esingularity_open`.
- `join_confirmation_view` where technically possible.

Use panel identifiers rather than personal data. Add campaign parameters only where they do not leak form answers or identity.

### 10. Make trust visible at every decision point

Add a short reusable disclosure next to join actions:

- Current status: preparatory committee.
- Joining is not a donation, investment, contract, or operating obligation.
- Names are not published without permission.
- The Sukatto Land reuse and COG DC are proposals/candidates subject to technical, legal, financial, and public decision processes.

## P2 — Growth and Quality

- Add verified Japanese/English copy parity and correct document language metadata; keep Japanese as default.
- Add a share action and QR code only after the join funnel works and is measured.
- Show a member count only if it comes from a verifiable source and has a clear update timestamp.
- Add campaign-specific social metadata and an image based on the original map, not a third-party photograph without explicit reuse rights.
- Expand JHR with dated source notes and a visible distinction among proposed, approved, under-construction, and operating projects.
- Add accessibility checks for 200% text zoom, focus visibility, reduced motion, iframe title, and sticky-CTA obstruction.

## First-Principles Message Architecture

### Problem

Large hyperscale projects can lock in land, grid, infrastructure, and planning decisions before communities have organized rules or alternatives.

### Proof

Local opposition in the United States is now measurable and broad. Inzai demonstrates what concentrated development looks like in Japan. The campaign must show both with dates and sources.

### Alternative

Japan still needs compute. YUMORI proposes evaluating existing infrastructure for smaller, modular, community-oriented compute that serves schools, universities, hospitals, agriculture, government, makers, and local firms before exporting capacity elsewhere.

### Action

Join the national preparatory committee before irreversible development decisions are made.

## Recommended Micro-Sprints

### Slice 1 — Conversion contract

- Rewrite the hero and panel-specific CTAs.
- Add the committee reassurance language.
- Embed and verify the Google Form with fallback.
- Add join-funnel event measurement.
- Repair focused tests.

Exit gate: a first-time mobile visitor understands the threat, the alternative, and the meaning of joining; can type and submit without leaving the site; and generates a measurable success signal.

### Slice 2 — Evidence panel

- Add the sourced 71% Gallup statistic.
- Create the original Inzai cluster map.
- Connect each claim to a dated source drawer and JHR.

Exit gate: every numeric or local-impact claim has a visible source and no copyrighted map is copied.

### Slice 3 — National campaign polish

- Verify Japanese/English parity.
- Add campaign social metadata and share tools.
- Run desktop/mobile visual, keyboard, HTTPS, and form-submission checks.
- Update README, INTERFACE, ROADMAP, ModLog, source-of-truth, and audit records.

Exit gate: both hosts, both languages, and the full join path pass production checks without changing the existing eSingularity deployment behavior.

## Go/No-Go Decision

**No-go for broad promotion today.** Hosting is operational, but the join flow has not been submission-tested, the page contract is red, conversion is unmeasured, and the central proof visual/statistic is missing.

**Go after Slice 1.** The fastest responsible path is not a full redesign. First make the preparatory-committee promise explicit, keep signup on YUMORI.me, verify an actual submission, instrument the funnel, and restore the tests. Then add the evidence/map layer.
