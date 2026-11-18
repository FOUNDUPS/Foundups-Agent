# YUMORI / Project eSingularity — 10-slide vision deck

Date: 2026-09-11
Status: public concept / evidence-bound vision
Owner: Project eSingularity (`esingularity_001`)

## Decision

The canonical project vision lives on **eSingularity.ai**. **YUMORI.me** remains the movement/join surface. The deck is not duplicated as a second independently maintained presentation on YUMORI.me; YUMORI may link into the canonical eSingularity full-screen deck and receive the closing JOIN conversion.

## Presentation model

The public presentation follows a Guy Kawasaki-inspired ten-slide constraint: one dominant idea/visual per slide, very large type, minimal prose on the slide, with structured explanation/evidence preserved below the image for accessibility, search, translation, RedDog grounding and fact review.

The public UI supports:

- full-screen 16:9 presentation;
- touch swipe and previous/next controls;
- keyboard Left/Right/Escape;
- direct slide selectors;
- optional 9-second progression;
- reduced-motion opt-out;
- deep links using `?vision=1&slide=N#yumori-deck`;
- Japanese-first structured content with English and Portuguese derived states.

The image is the human presentation layer. `frontend/content/yumori-vision.ts` remains the semantic/evidence layer.

## Real-building visual rule

The September 11 deck was regenerated from 012's photographs of the actual former Sukatto Land Kuzuryu building. Concept art must preserve recognizable site massing wherever practical: the long hotel wing, pale exterior, green pyramidal-roof tower, curved-roof annex, entrance canopy, service-yard context and mountain setting.

This is **adaptive reuse**, not a fantasy greenfield replacement. Selective additions and facade upgrades are allowed only as clearly conceptual interventions.

Bathing zones are depicted as private/screened spaces. Public event circulation is not mixed with exposed bathers. No sexualized presentation is permitted.

## Current ten-slide spine

1. **VISION — 壊す前に、未来を比べる。** Real-building adaptive reuse: 24-hour onsen × COG DC × eSingularity Lab × D-K.
2. **OPTION VALUE — なぜ15.8億円を使って、選択肢を壊すのか。** Reported demolition estimate vs. modeled reuse outputs, with accounting categories kept separate.
3. **CULTURE AFTER DARK — 毎夜、違う景色。** D-K / Digital Kakejiku-inspired cultural activation of the retained building.
4. **THE ONSEN DESTINATION — 24時間温泉。大きな露天風呂。滞在したくなる場所。** Screened/private bathing, sauna, lounge, food, small performance, B1 gym/rest/recovery.
5. **WHAT IS COMPUTE? — コンピュートは、新しい「田んぼ」だ。** 1 AI Rice Field ≈ 1 MW as a communication/planning metaphor, not agricultural conversion.
6. **COG DC — 熱を捨てない。地域へ戻す。** Separate compute plant; heat-reuse candidates: onsen, building hot water/heating, snowmelt, agriculture.
7. **eSINGULARITY LAB — 60 FoundUps。1チーム最大3人。あとはAI。** Two upper floors for small AI-native FoundUp teams; B1 gym/rest/recovery.
8. **LOCAL PROBLEM TO FOUNDUP — 福井の課題から、福井の会社をつくる。** Agriculture, weeding, drones, sensing, field validation.
9. **FUKUI AS A PROTOTYPE — 福井から、日本の分散型コンピュートへ。** Community-scale distributed compute as a complement to hyperscale concentration.
10. **THE CHOICE — 建物は、まだ立っている。選択肢も、まだ残っている。** Compare futures before demolition; JOIN conversion to YUMORI.me.

## Financial truth boundary

Slide 02 uses the current internal model outputs:

- reported future demolition estimate: about **¥1.58B / 15.8億円**;
- verified FY2018 users: **129,649**;
- modeled five-year revenue: about **¥5.37B / 53.7億円**;
- modeled cumulative five-year FCFE: about **¥1.94B / 19.4億円**.

These figures are not interchangeable. Municipal demolition cost is not shareholder cash flow. FCFE is cumulative model output, not annual public return. All financial slide outputs are labeled modeled and are **not forecasts or guarantees**.

The earlier summary IRR value also requires reconciliation against the underlying cash-flow table before any public IRR claim is used; this deck intentionally omits IRR.

## D-K truth boundary

Akira Hasegawa's official D-K / Digital Kakejiku work is the artistic reference for the culture-after-dark concept. D-K has been installed internationally, but no slide may imply Hasegawa has formally committed to YUMORI or that the site is already designated headquarters without a separate documented agreement.

## Domain funnel

- **eSingularity.ai:** vision, evidence, project explanation, JHR context and RedDog.
- **YUMORI.me:** civic movement, guardian/join conversion and participation.
- The deck may link to YUMORI.me on the closing/join action; YUMORI.me may preview/link back to the canonical eSingularity deck.

## Runtime asset strategy

To keep the initial PR bounded, the ten approved 16:9 slide images are packed into one optimized vertical JPEG sprite at `frontend/public/vision/vision-sprite.jpg`. The presentation selects one tenth of the sprite using responsive CSS background positioning. This preserves full-slide rendering, reduces request count and keeps slide text uncropped.

If future image revisions require independent caching or social sharing per slide, split the sprite into ten versioned assets without changing the semantic source or slide IDs.

## WSP / recovery

- WSP 00: discover through the eSingularity module and this document.
- WSP 22: record public presentation changes in `ModLog.md`.
- WSP 97: execute public-surface changes through the governed repo/PR path and preserve current truth boundaries.
- Do not create a second deck owner in YUMORI or a second financial source of truth.
