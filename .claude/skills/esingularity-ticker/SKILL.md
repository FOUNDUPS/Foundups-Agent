---
name: esingularity-ticker
description: Update the eSingularity campaign ticker and the monk's public field status, including location, attendance window, invitations and YUMORI links. Use for requests to update the ticker; excludes broadcast and exchange-price tickers.
---

# eSingularity ticker

Canonical repository: `FOUNDUPS/Foundups-Agent`.
Module: `modules/foundups/esingularity`.

## Locate and update

Read repository instructions and the module README, INTERFACE and recent ModLog in bounded chunks. Search for an existing update before editing.

- Edit `frontend/content/current-field-status.ts`: this is the single source for `currentFieldStatus`.
- `frontend/components/CampaignTicker.tsx` renders it as the existing LIVE action, twice for the scrolling loop. Preserve its other actions and links. Verify `frontend/app/page.tsx` actually mounts `<CampaignTicker />`; an unused component cannot display an update.
- Keep updatedAt, updatedLabelJa, locationJa, tickerJa, detailJa, detailEn and href consistent. Use an explicit calendar date and Japan time (`+09:00`), including the stated end time in visible copy. Never infer a recurring appearance from one visit. The present implementation does not automatically expire the LIVE entry; do not claim otherwise.
- Japanese is primary. Refer to the monk in third person. Normalize obvious speech-recognition errors such as “Morty” or “youMorty” to YUMORI when campaign context establishes that meaning.
- Use the location and giveaways confirmed by 012. Do not identify an unknown building across the street, invent stock counts or carry old City Hall/flyer details into a new event.
- Follow the requested destination: YUMORI.info is the project-information redirect to eSingularity.ai; YUMORI.me is the separate movement/join page. Verify an unfamiliar domain such as eSingularity.org before assigning it a new role.

## Verify and publish

Update the module ModLog with the dated change and evidence. Run the existing field-status contract in `tests/test_jhr_public_contract.py`; its structural assertions should permit normal date/location updates. For presentation changes, run the existing ticker and hostname-routing checks too.

Use a narrow branch and PR; squash when authorized and repository checks allow it. Source merge does not publish the website.

Publish through the existing Sites project in `frontend/.openai/hosting.json`, following the available Sites hosting skill. Compare the latest Sites source with the monorepo before applying the small content patch so concurrent homepage work is preserved. Keep eSingularity.ai and YUMORI.me as separate homepages and preserve YUMORI.info forwarding. Verify the fresh live ticker contains the correct date, place, time, offer and destination. Record actual publication evidence; if blocked, distinguish merged source from live status.
