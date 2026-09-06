# Production recovery audit

Audit date: 2026-08-29 (Asia/Tokyo)

## Repository and deployment

- Framework: Vinext / Next App Router on Vite + Cloudflare Workers.
- Hosting: OpenAI Sites project `appgprj_6a917b21b1a4819181a61738ed5274a5`.
- Database: Cloudflare D1 binding `DB` for community-interest submissions.
- Existing routes: `/`, `/team`, `/team/:slug`, `/api/interest`.
- Missing required route: `/future` (live 404).
- PWA: no manifest and no service worker (both live 404).
- Direct LINE URL: live HTTP 200.
- Existing QR: visible only inside campaign poster; no dedicated QR asset/section.
- HoloIndex retrieval: unavailable due `HOLOINDEX_MAINTENANCE_ACTIVE`; no authority worktree mutation or reindex was performed. Audit used repository search fallback.

## P0 — broken or functionally missing

- [ ] Required Fukui Economic Future page does not exist.
- [ ] Production locale architecture does not exist. English and Portuguese are partial client-side DOM text substitutions, not equivalent pages/resources.
- [ ] Language controls are not flag-only and are below practical 44×44 mobile tap size.
- [ ] Mobile header does not expose the three required primary pages.
- [ ] No dedicated, preserved LINE QR image exists; QR cannot be reliably scanned as an independent CTA.
- [ ] No PWA manifest, app icons, service worker, installable metadata, or safe cache/update policy.

## P1 — misleading or wrong data

- [x] Remove the 1→2→4 MW revenue/jobs table. It extrapolates from a hard-coded, internally inconsistent financial workbook.
- [ ] Remove numeric job claims until methodology separates construction, permanent operating, indirect, and induced jobs.
- [ ] Reframe “約68億円” as an indexed construction-cost reference—not current value, appraisal, market value, or recoverable loss.
- [ ] Reframe ¥1.58B narrowly as a figure appearing in June 2026 council question material; do not imply final budget or awarded demolition price.
- [ ] Remove implied commitments by five named universities. Participation and allocations are not agreed.
- [ ] Remove unverified grant, tax, free-lease, lender, PUE, heat, and return claims.
- [ ] Remove or quarantine unconfirmed people from the launch Team page; the verified launch team is 012 + 0102.
- [ ] Replace scattered numeric strings with one shared structured data source used by all locales.
- [ ] Add explicit source/status labels distinguishing official facts, project models, benchmarks, and vision/targets.
- [ ] Add a privacy/purpose notice for collection of names and email addresses; retain no-publication-without-permission promise.

## P2 — message hierarchy and UX

- [ ] Landing page leads with process/fiscal language rather than “save the onsen” and the physical alternative.
- [ ] Required three-page information architecture is missing; the current single long page overloads a 30-second visitor.
- [ ] Mobile first viewport does not show the approved campaign image or current event state and does not present the three-part alternative clearly.
- [x] Removed the public mobile capacity table that required horizontal scrolling.
- [ ] “AIの田んぼ” starts too technically and needs the human food/rice/field explanation first.
- [ ] Physical plan is not unmistakable: first-floor onsen + upper/common Innovation Center + separate new campus on surrounding land.
- [ ] Demolition-vs-reuse comparison needs a simple vertical mobile diagram.
- [ ] Economic page lacks the complete Fukui development matrix and local money loop.
- [ ] Team page looks larger/more established than current confirmed organization.
- [ ] Event data is not separated into a globally switchable structured record.

## P3 — visual and performance polish

- [ ] Privacy-safe team PNGs are 1.5–3.1 MB each and need responsive delivery without changing the approved blur treatment.
- [ ] Images lack consistent “current facility / concept / proposed / illustrative” labels.
- [ ] Tablet hero leaves a large empty visual field before the poster.
- [ ] Long mobile headings wrap awkwardly; Japanese line breaks need section-by-section review.
- [ ] No localized Open Graph metadata, canonical locale URLs, or hreflang set.
- [ ] Focus states and keyboard/tap behavior require a cross-site pass.
- [ ] No restrained mobile sticky LINE action or safe-area handling.

## P4 — optional enhancements after correctness

- [x] Lightweight D-K treatment using a linked official-work example, compact artist identity, and a clearly labeled proposed Sukatto Land experience.
- [ ] Install-prompt guidance only where browser support makes it useful.
- [ ] Performance telemetry/Core Web Vitals monitoring after launch.

## Live visual baseline

- Captured at 390×844, 1024×900, and 1440×1000.
- Team mobile baseline captured at 390px width.
- In-app browser automation was attempted first but its runtime failed to initialize; isolated headless Chrome screenshots were used as the fallback.

No implementation item may be marked complete until it passes build, data check, mobile screenshot review, desktop review, and regression checks.

## Recursive implementation log

### PASS A — remove the worst public financial-model leak

- Defect: the landing page exposed a 1→2→4 MW revenue/GPU/energy/jobs table derived from an internally inconsistent workbook.
- Fix: removed the complete table and its landing-page model note; retained the workbook and audit findings only as internal evidence.
- Build: `npm run lint` and `npm run build` passed.
- Render: checked at 390×844 in `audit/screenshots/local-pass-a-mobile.png`.
- Data: rendered HTML contains neither `年間総収入モデル` nor the legacy `58.4億円` value.
- Regression: home route renders; primary CTA remains visible; no horizontal overflow appears in the checked first viewport.
- Status: `[FIXED] [VERIFIED] [SOURCE CHECKED] [MOBILE CHECKED]`.

### PASS B — replace procedural hero with the community choice

- Defect: the first phone screen led with council procedure, liability transfer, and contract timing before explaining what residents were being asked to save.
- Fix: changed the canonical Japanese hero to `この温泉を、壊す前に。`, stated the demolition path in one line, summarized the physical alternative in plain language, and made the primary hero action the canonical LINE link.
- Mobile correction: constrained the two hero actions to the available 390px grid width after the first visual check exposed a small overflow.
- Build: `npm run lint` and `npm run build` passed after the correction.
- Render: checked at 390×844 in `audit/screenshots/local-pass-b-hero-mobile-fixed.png`.
- Data: no new number or financial promise was introduced; the demolition wording remains procedural rather than claiming an awarded contract.
- Regression: campaign poster still follows the primary action, secondary plan link still reaches the story, and LINE remains a normal independent hyperlink.
- Status: `[FIXED] [VERIFIED] [SOURCE CHECKED] [MOBILE CHECKED]`.

### PASS C — keep public history; remove public valuation mechanics

- Defect: the first story section asked residents to interpret construction indexing, demolition estimates, and an unconfirmed public-contribution cap before seeing the proposed future.
- Fix: retained the short official facility history and removed the four-card valuation/funding comparison from the public landing page.
- Build: `npm run lint` and `npm run build` passed.
- Render: checked the story section at 390×844 in `audit/screenshots/local-pass-c-story-mobile-cdp.png`.
- Mobile measurement: `scrollWidth=390`, `clientWidth=390`; no horizontal overflow.
- Data: remaining dates, area, and utilization figures are official-source claims recorded in `SOURCE_OF_TRUTH.md`; no modeled valuation remains in this section.
- Status: `[FIXED] [VERIFIED] [SOURCE CHECKED] [MOBILE CHECKED]`.

### PASS D — remove public fiscal-bridge mechanics

- Defect: the landing page exposed a funding-cap formula, liability mechanics, and a four-step public-finance workflow suited to professional review rather than community participation.
- Fix: removed the complete fiscal-bridge section from the public route while preserving its evidence and proposal logic internally.
- Build: `npm run lint` and `npm run build` passed.
- Regression: the civic amendment section remains, followed directly by the plain-language project proposal.
- Mobile verification: proposal viewport checked at 390×844 in `audit/screenshots/local-pass-d-proposal-mobile-cdp.png`; `scrollWidth=390`, `clientWidth=390`.
- Status: `[FIXED] [VERIFIED] [SOURCE CHECKED] [MOBILE CHECKED]`.

### PASS E — add the 60-second future sequence

- Defect: the landing page moved from campaign poster into facility history without a glanceable explanation of what the retained site becomes.
- Fix: added a Japanese-first `いま → 選択 → 私たちの提案` sequence followed by five plain-language cards: onsen, learning, AI rice field, food/entrepreneurship, and festivals/culture.
- Build: `npm run lint` and `npm run build` passed.
- Render: checked at 390×844 in `audit/screenshots/local-pass-e-vision-mobile.png` and `audit/screenshots/local-pass-e-vision-cards-mobile.png`.
- Mobile measurement: `scrollWidth=390`, `clientWidth=390`; cards stack vertically and require no horizontal scrolling.
- Data: no numerical or contractual claim was added.
- Status: `[FIXED] [VERIFIED] [SOURCE CHECKED] [MOBILE CHECKED]`.

### PASS F — explain compute with the AI rice-field model

- Defect: the public explanation began with `計算資源`, training/inference language, a technical cycle, and an unagreed list of universities.
- Fix: replaced it with a first-principles sequence—inputs → AI rice field → computing power → AI work—plus three ordinary Fukui use cases and a clear statement that the facility enables applications rather than directly operating every machine.
- Removed: duplicate technical diagram, unsupported allocation implications, and named-university list from the landing page.
- Build: `npm run lint` and `npm run build` passed.
- Render: checked at 390×844 in `audit/screenshots/local-pass-f-ricefield-mobile.png`.
- Mobile measurement: `scrollWidth=390`, `clientWidth=390`.
- Data: no capacity, performance, customer, or hardware claim appears in the simplified explanation.
- Status: `[FIXED] [VERIFIED] [SOURCE CHECKED] [MOBILE CHECKED]`.

### PASS G — remove the global statistics and industry-precedent detour

- Defect: the landing journey left Fukui for U.S. electricity percentages, national vacant-home statistics, and four commercial precedent cards before returning to community participation.
- Fix: removed both global/industry sections from the public landing route; supporting research remains internal and can inform later professional material.
- Build: `npm run lint` and `npm run build` passed.
- Render: checked the following participation section at 390×844 in `audit/screenshots/local-pass-g-people-mobile.png`.
- Mobile measurement: `scrollWidth=390`, `clientWidth=390`.
- Regression: the simplified AI proposal now flows directly into the local-stakeholder section.
- Status: `[FIXED] [VERIFIED] [SOURCE CHECKED] [MOBILE CHECKED]`.

### PASS H — create the community-benefit Fukui Future tab

- Defect: `/future` returned 404 and economic messaging existed only as scattered technical/financial material on the landing page.
- Fix: created `/future` around one public question—`福井に、何が残る？`—with eight benefit cards, a local-value loop, and a collapsed `詳しく見る` roadmap.
- Progressive disclosure: capacity figures are not the opening experience; they appear only inside the optional roadmap and use the shared audited sequence and conditional wording.
- Build: `npm run lint` and `npm run build` passed; `/future` is present in the route manifest.
- Render: checked at 390×844 in `audit/screenshots/local-pass-h-future-hero-mobile.png` and `audit/screenshots/local-pass-h-future-benefits-mobile.png`.
- Mobile measurement: `scrollWidth=390`, `clientWidth=390` on both checks; cards stack vertically.
- Status: `[FIXED] [VERIFIED] [SOURCE CHECKED] [MOBILE CHECKED]`.

### PASS I — add an honest community-meetings concept

- Defect: there was no meeting/calendar touchpoint, but exact event details and an authenticated member backend are not currently verified or implemented.
- Fix: added a public meeting card with `日程・場所を確認中`, a direct LINE notification CTA, and a member-calendar disclosure explaining the intended LINE-member experience.
- Honesty control: the UI explicitly states that the website has no member authentication or protected calendar yet; it does not imitate protected access.
- Build: `npm run lint` and `npm run build` passed.
- Render: checked at 390×844 in `audit/screenshots/local-pass-i-calendar-mobile.png`.
- Mobile measurement: `scrollWidth=390`, `clientWidth=390`.
- Event data: no date, time, location, or public status was invented.
- Status: `[FIXED] [VERIFIED] [SOURCE CHECKED] [MOBILE CHECKED]`.

### PASS J — reduce Team to the verified launch pair

- Defect: the directory publicly implied endorsers, community representatives, and a global network before permissions and project roles were confirmed.
- Fix: the Team tab and landing preview now show only 012 and 0102; all other records remain in the internal structured data but are unpublished.
- Route control: static profile generation and public lookup now use `publicTeamProfiles`; `/team/hasegawa` returns HTTP 404.
- Privacy: 012's approved group imagery retains the privacy-safe blurred asset; 0102 uses the approved non-human visual identity.
- Build: `npm run lint` and `npm run build` passed.
- Render: checked at 390×844 in `audit/screenshots/local-pass-j-team-mobile.png`.
- Mobile measurement: `scrollWidth=390`, `clientWidth=390`.
- Status: `[FIXED] [VERIFIED] [SOURCE CHECKED] [MOBILE CHECKED]`.

### PASS K — mobile shell, flags, metadata, and PWA

- Fix: replaced platform-dependent emoji rendering with compact CSS-drawn Japan/U.S./Brazil flags, preserved accessible language names, and removed mobile brand overlap.
- PWA: added Japanese-first manifest, 192/512 PNG icons, HTTPS-only registration, and a service worker that caches only stable icons while all page/event content remains network-current.
- Endpoint verification: `/manifest.webmanifest` HTTP 200 with `application/manifest+json`; `/sw.js` HTTP 200 with JavaScript content type.
- Metadata: updated title/description/social copy around `温泉を守る` rather than construction procedure.
- Render: checked at 390×844 in `audit/screenshots/local-pass-l-final-hero-mobile.png`; `scrollWidth=390`, `clientWidth=390`.
- Status: `[FIXED] [VERIFIED] [MOBILE CHECKED]`.

### PASS L — make LINE the single conversion

- Defect: a multi-field database form created survey friction after the campaign asked visitors to join LINE.
- Fix: removed the form and client-side submission code; the landing conversion is now the canonical LINE link. Detailed source links are collapsed under intentional disclosure.
- Build: `npm run lint` and `npm run build` passed.
- Render: checked at 390×844 in `audit/screenshots/local-pass-l-line-cta-mobile.png`; `scrollWidth=390`, `clientWidth=390`.
- Status: `[FIXED] [VERIFIED] [MOBILE CHECKED]`.

### PASS M — verify language controls on the core campaign journey

- Japanese: first-visit/default canonical hero verified.
- English: flag interaction produced `This onsen—before we destroy it.` at 390×844 in `audit/screenshots/local-pass-m-english-hero-mobile.png`.
- Portuguese: flag interaction produced `Este onsen—antes de destruí-lo.` at 390×844 in `audit/screenshots/local-pass-m-portuguese-hero-mobile.png`.
- Both translated hero checks measured `scrollWidth=390`, `clientWidth=390`.
- Status: `[FIXED] [VERIFIED] [MOBILE CHECKED]` for the core hero journey; full route-based locale architecture remains a future hardening item.

### PASS N — convert repetition into Japanese campaign action

- Defect: the landing journey explained the same five-part future twice but did not give residents a compact path to see project photos, read the plan, share the campaign, join the citizens’ declaration, or contact Fukui City.
- Fix: preserved the existing section and card design while replacing the repeated summary with `見る・聴く・知る・共有する・参加する`; added a continuous campaign-action ticker in place of the expired event alert.
- Civic action: used Fukui City's official former-facility contact page, published telephone number and hours, and official inquiry form; the suggested message asks only that reuse proposals be fairly compared before a demolition contract.
- Link control: `pics.yumori.info`, `pc.yumori.info`, `music.yumori.me`, and `yumori.me` were opened successfully. The corrected music vanity route forwards over HTTPS to the approved Suno playlist and is used directly by the public controls.
- Build: `python -m pytest ../tests/test_contracts.py -q` (17 passed), `npm run lint`, and `npm run build` passed.
- Mobile: verified at 390×844 in Japanese; the hero, continuous ticker, stacked action cards, and City contact controls render without horizontal clipping. Added anchor scroll spacing for the fixed header.
- Language regression: verified the full new action and City-contact section in English and Portuguese against the Japanese source; no Japanese copy leaked into either translated action path.
- Production: Sites version 21 deployed successfully and the custom domain `https://esingularity.ai` was rechecked at 390×844 with a cache-busting query. The Japanese ticker and action controls were present; the English action path was rechecked with no Japanese leakage.
- Status: `[FIXED] [VERIFIED] [SOURCE CHECKED] [MOBILE CHECKED] [LIVE CHECKED]`.
