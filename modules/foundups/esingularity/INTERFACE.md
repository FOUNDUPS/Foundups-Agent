# Project eSingularity interface

## Public routes

| Route | Purpose |
| --- | --- |
| `/` | 温泉を守る / campaign landing page |
| `/future` | 福井の未来 / community-benefit explanation |
| `/team` | Verified public team directory |
| `/team/[slug]` | Individual public profile |

## YUMORI presentation contract

- The landing page mounts the presentation at `#yumori-deck`, immediately after the existing hero.
- The existing campaign ticker contains exactly one `NEW` notification linking to that anchor; the ticker itself is not replaced or duplicated.
- `frontend/content/yumori-presentation.ts` is the canonical content boundary: Japanese is authored first, and English/Portuguese states derive from it.
- The component presents ten slides with previous/next controls, direct slide selectors, touch swiping, a play/pause control, and nine-second timed progression.
- Focus, pointer, wheel, disclosure, or navigation interaction pauses timed progression. Reduced-motion preference disables it.
- Each slide follows image/visual → proposition → explanation → evidence, with detailed material collapsed by default.

## FoundUps shell contract

| Field | Value |
| --- | --- |
| `foundup_id` | `esingularity_001` |
| Landing namespace | `/f/esingularity_001` |
| App namespace | `/f/esingularity_001/app` |
| Tenant data namespace | `idb_esingularity_001` |
| External entry URL | `https://esingularity.ai/` |

The Foundups shell owns discovery and routing. The eSingularity module owns campaign content, product UI, public routes, and its deployment.

## Shared external actions

- Canonical LINE invitation: `https://line.me/ti/p/baXEozL_Q6`
- Header and campaign LINE actions use the same shared URL.
- Event state is centralized in `frontend/lib/event.ts`.
- The existing `music.yumori.me` playlist route remains the soundtrack destination until approved local media exists.

## Hosting contract

The Sites project configuration remains at `frontend/.openai/hosting.json`. The frontend uses Vinext/Next App Router with Cloudflare-compatible output and the existing D1 binding declared by Sites.

## Safety boundary

- No secrets belong in the frontend or module manifests.
- No token or investment surface is enabled.
- Public financial claims remain governed by `frontend/audit/SOURCE_OF_TRUTH.md`.
- Unverified event details stay disabled rather than being inferred.
- COG DC capacity, heat recovery, demand, economics, and national reuse remain proposals pending validation.
- Akira Hasegawa is not represented as committed to the project.
- Public academic profiles are labeled as outreach candidates only; no membership or support is implied.
