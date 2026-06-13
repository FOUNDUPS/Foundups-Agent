# GetK ROADMAP

GetK = "Get a Kei Truck". PoC = Kei trucks. Outcome = reusable AI-managed
marketplace for any used item. Each phase is a separate, gated slice; readiness
flags stay false until explicitly promoted by an evidence-backed slice.

## Phase 1 -- Monorepo PoC bootstrap (THIS slice)

- Registry entry + valid manifest + pure-Python PoC contract model.
- Proven through the EXISTING WRE/OpenClaw/Hermes dry-run `validate_foundup`
  path (no new wiring). Readiness false; source authority `monorepo_poc`.

## Deferred / future slices (named, not built)

- `GETK_IMPORT_REGULATORY_PROVIDER_AUDIT_PHASE1` -- browse current official/state
  import sources and cite them; replace the deferred regulatory marker. The
  Kei-truck state/import discussion is time-sensitive and is NOT encoded as
  product truth here.
- `GETK_CAPTURE_SCOUT_SKILL_PHASE1` -- scout/discovery capture (media + declared
  fields); item-agnostic.
- `GETK_MEDIA_QUALITY_REVIEW_SKILL_PHASE1` -- AI-assisted media-quality review.
- `GETK_LISTING_PACKET_SKILL_PHASE1` -- AI-assisted listing-packet creation.
- `GETK_VALUATION_ESTIMATE_SKILL_PHASE1` -- AI-assisted value/cost estimates
  (estimate-only, never authoritative).
- PFmall public-browse wiring and stakeholder-gated bidding -- separate slices,
  after the product SKILLz exist.

## Cross-cutting infrastructure follow-ups (system-level, surfaced by this slice)

- `WRE_FOUNDUP_ONBOARDING_BUILDER_SKILL_PHASE1` -- encode the manual
  registry+manifest+scaffold+dry-run onboarding procedure (performed by hand in
  this slice) as a reusable WRE BUILD skill. Today FoundUp onboarding has rails
  but no end-to-end build skill.
- `FOUNDUP_REGISTRY_HOLOINDEX_BRIDGE_PHASE1` -- index the FoundUp registry into
  HoloIndex so a newly-added FoundUp is "remembered" by registry lookup, not only
  via its README on reindex.

## Hard boundaries (all phases)

Token is utility only (never bid/ownership/payment). No real auction/scraping/
login. No payments. No regulatory claims as truth. No real execution until the
gated runtime path is explicitly enabled.
