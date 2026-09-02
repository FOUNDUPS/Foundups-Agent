# eSingularity TestModLog

## 2026-09-03 — Japanese action-path regression coverage

- Replaced the obsolete repeated-vision assertions with checks for the see/listen/learn/share/join/act campaign journey.
- Added checks for all campaign vanity routes, native share and clipboard fallback behavior, and the complete ticker action set.
- Added official Fukui City contact checks and a regression guard preventing the expired August 31 notice from returning to the ticker.
- Replaced the D-K root-URL substring assertion with parsed scheme/host/path validation after CodeQL correctly identified the former test as an incomplete URL-sanitization pattern.

## 2026-09-01 — Economic scorecard and benchmark guardrails

- Added regression checks for the precise English annual and 30-year direct-spending displays with no “About” prefix.
- Added checks for the broader Fukui outcome scorecard and the explicit separation of construction and permanent employment.
- Added checks for the two official NCDS case-study links and the warning that their outcomes and ratios are not transferred to Fukui.

## 2026-09-01 — Innovation Hub language and typography coverage

- Added regression checks for the Gather → Learn → Create → Launch floor progression.
- Added English-copy checks for the AI learning, creation, and launch floor descriptions.
- Added typography checks that highlighted campaign headings keep one consistent font voice.
- Added outcome-card checks, removed-choice-diagram coverage, and multilingual alt-text handling.
- Added a regression contract for the native six-step campaign coalition sequence and removal of the old stakeholder image.
- Added economic-impact checks that keep the direct-spending layer distinct, expose the 30-year method progressively, and exclude supplier, wage, job, and tax figures until official input-output analysis is complete.

## 2026-09-01 — Awara and D-K visual-reference coverage

- Added contract checks for the official Awara Yukemuri Yokocho and D-K gallery destinations.
- Added regression checks that the artist portrait remains a compact 52-pixel identity element and no longer dominates the night-experience card.
- Added coverage for the operator-provided D-K YouTube link and the no-iframe/no-autoplay profile treatment.
- Added translation checks for the Japanese-first reference links.

## 2026-09-01 — English economic-story regression coverage

- Added assertions for the complete English AI Rice Field explanation and use cases.
- Updated visitor-spending arithmetic to the official 2025 Fukui day-trip benchmark and added 30-year constant-attendance calculations.
- Added campaign-headline assertions to prevent the previous weak English story copy from returning.

## 2026-08-31 — Community-vision regression coverage

- Added checks for equivalent campaign hero copy across Japanese, English, and Portuguese.
- Added checks that 0102 MUSIC remains opt-in and pauses through viewport observation.
- Added checks for conditional concept labels, the generated concept asset, revised floor labels, and removal of landing sections 08–10.

## 2026-08-30 — Migration contract baseline

- Added identity, namespace, registry, hosting, route, and token-deferral checks.
- Added the shared FoundUp build-contract validator as a regression gate.
