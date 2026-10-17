# Move2Japan FoundUp — ModLog (WSP 22)

## V0.2.0 — English house-discovery rebaseline (2026-10-17 JST)

**Authority:** 012's current website instruction; canonical spelling Move2Japan
and move2japan.info. **WSP:** 11, 22, 50, 60, 84, 97 and existing 104 namespace.

**Changes:** Rebased README, roadmap, interface, module metadata, premium model,
stage definitions and funnel architecture around real house search. The public
POC source lives in `public/move2japan/` and composes shared Mall tiles, detail
planes and gestures with five attributed Fukui observations. Source photos stay
at the original page; broker availability and media reuse remain unconfirmed.

**Stage decisions:** Prototype requires real account-linked, authorized and
reviewed property publication with durable upload. MVP requires actual settled
customer payment and delivered configured benefits, including expiry/refund
revocation. Shared Foundups account admission is not paid membership; no price,
release delay or token issuance was invented. Existing `move2japan` identity,
registry classification and `TOKEN_DEFERRED` are preserved.

**History retained:** BC0 conversation handling and SQLite memory are implemented
and remain unchanged. The wider BC1-BC7 relocation vision remains a later layer.
Historical docs 02/05 now flag planned surfaces and correct numeral-2 URL
spellings; old livechat runtime strings are a separately tracked follow-up.

**Evidence/validation:** See `docs/08_HOUSING_DISCOVERY_REBASELINE.md` and the
module test records for source and behavioral validation. Documentation was
checked for local link/metadata consistency. This entry does not claim custom
domain deployment, continuous listing refresh, publisher signup or paid users.

---

## V0.1.0 — Module Inception (2026-03-07)

**What**: Created Move2Japan FoundUp module scaffold under `modules/foundups/move2japan/`

**Why**: 012 defined comprehensive voice-mode architecture for an agent-driven relocation system. This module captures the complete architectural vision and establishes WSP-compliant structure for iterative build.

**Changes**:

- Created WSP 49-compliant module structure (README, INTERFACE, ROADMAP, ModLog, src/, tests/, memory/, docs/)
- Captured 012 voice conversation architecture across 7 docs:
  - `01_OVERVIEW.md` — FoundUp vision, core principles, mountain model
  - `02_SYSTEM_ARCHITECTURE.md` — 12 core modules, state model, data model, gating logic
  - `03_PREMIUM_MODEL.md` — Free/premium/concierge tiers, revenue streams
  - `04_POC_PROTOTYPE_MVP.md` — Occam's first-principle layering
  - `05_BASECAMP_ZERO_SPEC.md` — Complete BC0 conversation flow spec, dialogue tree, skill template
  - `06_BLINDSPOTS.md` — Urgency, trust, compliance, community, re-entry
  - `07_FUNNEL_ARCHITECTURE.md` — movetojapan.info vs movetojapan.foundups.com dual-surface

**WSP Compliance**: WSP 3, 11, 22, 34, 49, 60

**Integration Points**:

- Existing `persona_move2japan.json` livechat skill
- YouTube DAE infrastructure (existing banter engine + chat logs)
- FoundUps platform infrastructure (`modules/foundups/`)

**Impact**: Foundation laid. POC build target = BC0 live chat skill.

**Next**: Build BC0_IntentAndPassportSkill following WSP 95 (Skills Wardrobe) lifecycle.
