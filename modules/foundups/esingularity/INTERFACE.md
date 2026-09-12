# Project eSingularity interface

## Domain identity contract — non-negotiable

This is one FoundUp and one deployed frontend with two deliberately different public homepages:

| Concern | eSingularity.ai | YUMORI.me / www.YUMORI.me |
| --- | --- | --- |
| Public purpose | Fukui project and vision | National YUMORI movement, case for support, and preparatory-committee conversion |
| Root-page source | `frontend/app/page.tsx` | `frontend/app/yumori/page.tsx` |
| Root selection | Normal filesystem `/` route | Internal hostname-specific `/` → `/yumori` rewrite |
| Browser hostname | Remains eSingularity.ai | Remains YUMORI.me; no cross-domain redirect |
| Safe edit boundary | May evolve without replacing the movement page | May evolve without replacing the project page |

Agents resolving merges or synchronizing a Sites checkout must preserve **both** page files and verify both hostnames. Similar subject matter, shared components, or one shared deployment never authorizes collapsing the pages. `yumori.info` is a separate external forwarding rule and is not an alternate YUMORI content source.

## Filesystem routes

| Route | Purpose |
| --- | --- |
| `/` | eSingularity project/vision landing on eSingularity.ai |
| `/yumori` | YUMORI movement, case for support, participation and evidence; also served internally at YUMORI.me `/` |
| `/future` | 福井の未来 / community-benefit explanation |
| `/team` | Verified public team directory |
| `/team/[slug]` | Individual public profile |

## YUMORI presentation contract

- eSingularity.ai is the canonical home of the project vision; YUMORI.me remains the movement/join surface.
- The landing page mounts the presentation at `#yumori-deck`, immediately after the existing hero.
- The existing campaign ticker contains exactly one `NEW` notification linking to that anchor; the ticker itself is not replaced or duplicated.
- `frontend/content/yumori-vision.ts` is the canonical content boundary for the current real-building 10-slide vision. Japanese is authored first; English and Portuguese are derived states.
- `frontend/content/yumori-presentation.ts` remains the legacy/detail presentation source used by existing campaign evidence and translation contracts; do not silently merge the two truth layers.
- The visual deck is built from the 2026-09-11 real Sukatto Land Kuzuryu photo set and generated adaptive-reuse concepts. The runtime serves one optimized vertical sprite at `frontend/public/vision/vision-sprite.jpg`; structured text/evidence stays in HTML/TypeScript for accessibility, search, translation and RedDog grounding.
- The component presents ten 16:9 slides with previous/next controls, direct slide selectors, touch swiping, play/pause, reduced-motion handling and keyboard Left/Right/Escape support.
- `?vision=1&slide=N#yumori-deck` is the canonical deep-link form for opening the deck full screen at a specific slide. Full-screen rendering uses `contain`/whole-slide semantics: no slide text may be cropped.
- Slide 01 is the real-building reuse vision. Slide 02 separates reported demolition cost from modeled five-year revenue/FCFE. Slides 03-10 cover D-K culture, onsen/wellness, AI rice field, COG DC heat reuse, 60 FoundUps/eSingularity Lab plus B1 gym/recovery, local problem-to-FoundUp, Fukui distributed-compute prototype, and the closing choice.
- Bathing visuals must remain private/screened and non-sexualized; public circulation and bath zones are not depicted as mixed.
- D-K visual language may be inspired by Akira Hasegawa's Digital Kakejiku work, but Hasegawa participation or headquarters status is never represented as committed without separate agreement.
- The full design/provenance record is `docs/YUMORI_VISION_DECK_20260911.md`.

## Japanese-first public copy contract

- Japanese (`html lang="ja"`) is the canonical public reading experience. English-only structural labels are not allowed to leak into the Japanese tab except proper names or technical identifiers such as `COG DC`, `D-K`, `AI`, `eSingularity`, and a defined `FoundUp` term.
- Public-facing `Innovation Hub` wording is replaced by `イノベーション・スペース` / `Innovation Space`. The space is for people and teams; a person is not a FoundUp.
- `FoundUp` names a problem-solving project. Japanese copy should introduce it as `FoundUpプロジェクト` or `課題解決プロジェクト` when the audience may not know the term. Do not use `FoundUps` as a label for people.
- Floor labels in Japanese are purpose-based: `下層階 · 温泉・地域スペース`, `3階 · 挑戦・育成スペース`, `最上階 · 実証・発展スペース`, and `別棟 · COG DC`.
- The Japanese surface uses Japanese section labels for building value, visitor economy, council decision, AI rice-field explanation, community participation, meetings, and calls to action instead of decorative English headings.
- `frontend/components/JapaneseSurfacePolisher.tsx` is the bounded compatibility layer for legacy hard-coded labels while route-by-route copy is migrated to a true structured locale source. It must preserve English and Portuguese equivalents when the language switcher changes `html.lang`.

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

### Domain roles — one deployment, separate front pages

| Public entry | Required behavior |
| --- | --- |
| `https://yumori.me/` | Serve the existing `app/yumori/page.tsx` movement/case-for-support page internally; keep YUMORI.me visible |
| `https://www.yumori.me/` | Same movement page when this alias is bound to the project |
| `https://esingularity.ai/` | Keep the existing `app/page.tsx` project/vision page |
| `https://yumori.info/` | Preserve the existing external redirect to eSingularity.ai |

`frontend/next.config.ts` owns the executable host mapping. A host-restricted `beforeFiles` rewrite maps only `/` on YUMORI.me/www to `/yumori`, before the existing project homepage is selected. It does not redirect visitors to another origin, copy either page, change a database, or rewrite all paths. JHR, API, asset and explicit `/yumori` paths remain unchanged. Other hosts, including preview hosts, keep their normal routes.

**Publication gate:** committed configuration is not proof that production is fixed. The existing Sites project must receive the patch and bind the intended YUMORI host(s), with HTTPS and original-host forwarding verified. Retrieve the DNS records required by Sites rather than guessing them; preserve nameservers, mail records and unrelated subdomains. Leave YUMORI.info forwarding intact. Compare live Sites source with GitHub before publishing so newer live content is not overwritten by an older checkout. Record the deployed version/source receipt and verify direct plus client-side navigation, canonical metadata, query strings, signup, JHR and cache behavior on both hosts before reporting restoration.

**Merge/deployment gate:** any branch that changes `frontend/app/page.tsx`, `frontend/app/yumori/page.tsx`, or `frontend/next.config.ts` must be checked against the domain matrix above. A valid change may update one experience while the other is being developed in another branch or session; reconciliation must keep both latest intended surfaces. Never solve a conflict by choosing one landing page for both hostnames.

## Safety boundary

- No secrets belong in the frontend or module manifests.
- No token or investment surface is enabled.
- Public financial claims remain governed by `frontend/audit/SOURCE_OF_TRUTH.md`.
- The slide-02 financial figures are explicitly modeled feasibility outputs, not forecasts or guarantees; they must not be combined with the municipal demolition estimate as though they were the same accounting measure.
- Unverified event details stay disabled rather than being inferred.
- COG DC capacity, heat recovery, demand, economics, 24-hour onsen operations, bath scale, 60-FoundUp occupancy, basement program and national reuse remain proposals pending validation.
- Akira Hasegawa is not represented as committed to the project.
- Public academic profiles are labeled as outreach candidates only; no membership or support is implied.
# First opening review contract (2026-09-12)

`frontend/content/esingularity-opening.ts` supplies the root hero and deck slide `vision` with Japanese-first `ja/en/pt` content, a single recovered visual and the existing direct YUMORI committee form URL. Portuguese opening content is Brazilian Portuguese. `?vision=1&slide=1#yumori-deck` opens the existing full-screen deck paused. Remaining slide records and YUMORI.me routing are unchanged. See `docs/OPENING_REVIEW_20260912.md` for source admission and pending review gates.
