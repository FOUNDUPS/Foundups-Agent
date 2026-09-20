---
name: esingularity-ticker
description: Update the eSingularity campaign ticker and the monk's public field status, including location, attendance window, invitations and YUMORI links. Use for requests to update the ticker; excludes broadcast and exchange-price tickers.
---

# eSingularity ticker

Canonical repository: `FOUNDUPS/Foundups-Agent`.
Module: `modules/foundups/esingularity`.

For wider website edits or redesigns, apply `modules/foundups/esingularity/skills/website-update/SKILL.md`; it requires preserving both ticker consumers.

For every ticker copy update, read that workflow's **Shared branding and language — both sites** section. Keep YUMORI.me and JHR brand labels intact, put context alongside them, and preserve Japanese-first and complete English copy across both consumers. Do not maintain separate branding rules in this ticker skill.

## Locate and update

Read repository instructions and the module README, INTERFACE and recent ModLog in bounded chunks. Search for an existing update before editing.

- Treat a verbal ticker request as the editing interface. Convert the confirmed facts into one bounded JSON payload; do not ask 012 to author JSON or repeat the same message three times.
- For a routine live update, edit only `modules/foundups/esingularity/frontend/content/current-field-status.json` on the dedicated `live/yumori-field-status` branch. The deployed ticker polls that exact raw file every 60 seconds, so this path does not need a source PR, frontend build, or Sites deployment.
- Write `label.ja/en/pt` and `message.ja/en/pt` together. Japanese is primary; English and Portuguese must be complete, meaning-preserving authored translations. Do not rely on browser machine translation or the legacy DOM translation map.
- Keep `schemaVersion: 1`, `visible`, `updatedAt`, `expiresAt`, and `href` valid. Use explicit Japan-time offsets (`+09:00`). `expiresAt` must be after `updatedAt` and no more than 14 days later. Use `visible: false` to withdraw the live item immediately. Expired, hidden, malformed, overlong, future-dated, or off-domain payloads automatically fall back to the durable campaign action.
- `frontend/components/CampaignTicker.tsx` renders the live item plus its existing action list twice for the scrolling loop. Preserve both `frontend/app/page.tsx` (`<CampaignTicker />`) and `frontend/app/yumori/page.tsx` (`<CampaignTicker movement />`) consumers. The movement option keeps the ticker in normal flow and resolves project-section links to eSingularity.ai.
- `frontend/content/current-field-status.json` on `main` is the compiled safety fallback and schema example. Change that copy only through the normal source PR and deployment workflow; routine verbal updates target the dedicated live branch.
- When the report is a material campaign activity, also follow `modules/foundups/esingularity/skillz/yumori_moshpit/SKILLz.md`. Its linked Google Doc is the canonical campaign ledger; the ticker is a public current-status projection, not a second activity history.
- Japanese is primary. Refer to the monk in third person. Normalize obvious speech-recognition errors such as “Morty” or “youMorty” to YUMORI when campaign context establishes that meaning.
- Use the location and giveaways confirmed by 012. Do not identify an unknown building across the street, invent stock counts or carry old City Hall/flyer details into a new event.
- Follow the requested destination: YUMORI.info is the project-information redirect to eSingularity.ai; YUMORI.me is the separate movement/join page. Verify an unfamiliar domain such as eSingularity.org before assigning it a new role.

## Verify and publish

For ticker code/schema changes, update the module ModLog and run the existing field-status contract in `tests/test_jhr_public_contract.py`; for presentation changes, run the ticker and hostname-routing checks too. For a routine live-branch JSON update, validate the JSON shape, all three languages, timestamps, allowed destination, and the resulting raw file; do not create a source-history entry for every field update.

Use a narrow branch and PR; squash when authorized and repository checks allow it. Source merge does not publish the website.

Publish ticker code/schema changes through the existing Sites project in `frontend/.openai/hosting.json`, following the available Sites hosting skill. Compare the latest Sites source with the monorepo before applying the patch so concurrent homepage work is preserved. Keep eSingularity.ai and YUMORI.me as separate homepages and preserve YUMORI.info forwarding. After the one-time runtime deployment, routine live-branch JSON updates require no Sites publication; verify the raw payload and, when available, both rendered domains in all three languages.
