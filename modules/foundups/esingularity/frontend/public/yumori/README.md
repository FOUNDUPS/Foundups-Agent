# YUMORI Visual Asset Registry

Status: canonical manifest for public-facing YUMORI / Project eSingularity imagery.

YUMORI currently lives inside `modules/foundups/esingularity/frontend` as the public/campaign surface of Project eSingularity. This registry exists so prospectus and website work reuse validated assets instead of generating or publishing duplicates blindly.

## Rules

1. Never publish an asset marked `PRIVATE` or a `*-private.*` source file.
2. Generated/concept imagery must be labeled concept/mockup; never present it as an existing built condition.
3. Historical/site photographs and generated renders are different evidence classes and must not be mixed without captions.
4. Reuse existing public assets before generating new ones.
5. Any new YUMORI campaign visual should ultimately be stored under this `/public/yumori/` namespace or indexed here until binary relocation can be performed safely.
6. Image use must preserve provenance and intended context under WSP 97; uncertainty fails closed.

## Existing public campaign assets to reuse

| Current path | Status | Recommended prospectus use |
|---|---|---|
| `/concept-onsen.jpg` | PUBLIC / concept | Vision / onsen regeneration concept |
| `/campaign-phase-1.jpg` | PUBLIC / campaign | Early project phase / transformation narrative |
| `/campaign-phase-2.jpg` | PUBLIC / campaign | Later project phase / expansion narrative |
| `/how-it-works.jpg` | PUBLIC / campaign | System explanation |
| `/satellite-view.jpeg` | PUBLIC / site/context | Site/location context; caption accurately |
| `/akira-hasegawa.jpeg` | PUBLIC / person/source | Hasegawa / D-K context only |
| `/team/hasegawa.jpg` | PUBLIC / campaign | Hasegawa relationship/context if authorization remains valid |
| `/team/012-landowners.jpg` | PUBLIC / campaign | Community/landowner engagement |
| `/team/community-hillside.jpg` | PUBLIC / campaign | Regional/community context |
| `/team/global-network.jpg` | PUBLIC / campaign | National/global replication concept |
| `/yumori-economic-flow-ja.svg` | PUBLIC / evidence graphic | Demolition-versus-regeneration economics |
| `/yumori-inzai-fukui-comparison.webp` | PUBLIC / concept comparison | Hyperscaler comparison; must retain conceptual disclaimer |

## Private/source assets — DO NOT PUBLISH

Any path containing `-private` remains source/private material until explicit approval, including examples such as:

- `/team/012-landowners-private.png`
- `/team/community-hillside-private.png`
- `/team/hasegawa-private.png`
- `/team/global-network-private.png`

## Prospectus visual sequence

Recommended order for Document 06 / future `/yumori/prospectus` page:

1. **Hero transformation:** best existing old-to-new / nighttime onsen regeneration visual.
2. **Destination experience:** 24-hour onsen + rotenburo + food + wellness/rest layer.
3. **Every night is a festival:** Hasegawa D-K / light-art concept.
4. **Education + innovation:** children/students, robotics, 60 small AI-native startup teams.
5. **AI rice field:** one visual explaining `1 AI rice field ≈ 1 MW` as a public communication unit.
6. **Project structure:** City / landowners / public-benefit body / Project SPC / operating entities.
7. **Funding stack:** grants + private equity + project/equipment debt + customer demand + capital campaign.
8. **Hyperscaler contrast:** local phased compute versus large external hyperscale development.
9. **National replication:** one node in Fukui becoming a model for dormant assets across Japan.

## Missing visuals to create only if existing assets cannot serve

- `AI rice field` diagram: 1 MW planning unit, repeated 1 → 5 → 25 MW over validated phases.
- PPP/PFI structure diagram suitable for a non-technical audience.
- Funding waterfall showing verified grants, SPV finance, customers/offtake, and NCDS-aligned residual capital campaign.
- Interior concept for Korean-spa-inspired lower-level wellness/rest zone.

## Canonical document links

- Document 03: economics / policy / public-value case.
- Document 05: formal PPP/PFI legal, financing, VFM, risk and filing master.
- Document 06: YUMORI Project Prospectus / Case for Support.
- FIN.YUMORI: financial and regional-impact model.

This manifest is organizational metadata; it does not by itself change the public website or relocate binary assets.