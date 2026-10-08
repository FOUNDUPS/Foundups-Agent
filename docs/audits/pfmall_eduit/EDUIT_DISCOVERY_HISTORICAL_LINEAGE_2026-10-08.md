# EDUIT Discovery — Historical lineage and module boundary

**Status:** SPECIFIED_NOT_IMPLEMENTED · 2026-10-08  
**Umbrella:** EDUIT (Education Using Information Technology)  
**Proposed module:** EDUIT Discovery (working name)  
**Canonical tenant identifier proposed:** `eduit` (verify registration before activation)  
**Scope:** historical recovery and architecture specification; no learner profiling service deployed.

## Historical lineage

- **2001:** EDUIT, Inc. established as an educational initiative. The historical mission is to make learning freely accessible regardless of geography or socioeconomic position. [2007 mission](https://docs.google.com/document/d/1w2j-j5PrgiUWRfrVa7HcqFnSK9rHQfYEkb6BuzjjZyA/edit).
- **2007:** The eSingularity Initiative proposed the three-part system **The Tool + The Content + The Experience**: open multimedia learning tools, remixable content, and autonomous non-textual game-based learning on networked devices. [Initiative presentation](https://docs.google.com/presentation/d/1xyza3o6iZ0mgM6dm41cah_hiv-Luh5mc-HIkQVwdX7Q/edit).
- **2009–2010:** The eSingularity book and Malaysia prize proposal specified game-linked learning objectives, a learner's avatar, adaptive assessment, and discovery of brilliant learners in underserved communities. The prize proposed *scaling up* game difficulty, then bisecting failed jumps to estimate a starting level. These are historical proposals, not validated psychometrics. [Book](https://docs.google.com/document/d/1GUSTQm0xnqCa1VrTPaxyidDhDrQR7X39ZE5-gMiQraU/edit) · [Malaysia prize](https://docs.google.com/document/d/1HNzoskNKA-QRptJFFq11adp5FPAVkjiZ6RxwIW9P9uQ/edit).
- **2023:** EDUIT AI Teaching Touch Tablet and Baby0 EDUIT (B0e) explored multilingual infant interaction, caregiver voice and face modeling, OBAI, and parental support. The original discussion expressly says **“It will start as an app”**, and considers prototyping on existing iPad/Android devices. This is a distinct early-childhood lane, not a dependency of Discovery. [Baby0](https://docs.google.com/document/d/10SrgLBJYtuQh6U7bY04CDB0I0Y0J0Ki4zFZLrv9SPiE/edit) · [2023 moshpit](https://docs.google.com/document/d/13-bIhq-IQljtsUznfSk4R0nl83cUOWBa8qor0jX3b5w/edit).
- **2026:** FoundUps already has an [EDUIT minimum entry spec](../../../docs/audits/pfmall_eduit/EDUIT_MINIMUM_ENTRY_SPEC.md), but this document does not establish a deployed Discovery engine. The live [eSingularity FoundUp](../esingularity/README.md) serves a separate Fukui community/infrastructure campaign; do not replace or rename it.

## Product taxonomy

**EDUIT** is the umbrella and FoundUp identity. **EDUIT Discovery** is the proposed browser-first game/learning-potential module. **EDUIT Baby0 (B0e)** is a separate historical early-childhood concept. **eSingularity** is the educational paradigm and historical platform name, also currently used by a separate live FoundUp; context must disambiguate them.

## MVP boundaries

1. A browser-based game with optional audio and language-neutral instructions, using ordinary phones, tablets and computers.
2. Explicit learning objectives and a deterministic adaptive-difficulty policy inspired by the 2010 scaling-up/bisection proposal.
3. Pseudonymous local progress, accessible accommodations, and opt-in guardian-controlled export.
4. Measure game-specific performance and learning rate, **not IQ, diagnosis, genius, or a universal intelligence percentile**.
5. No automated scholarship or educational opportunity referrals for minors. Human review, consent, independently validated measurements and fairness evaluation are required before such a workflow.
6. No infant monitoring, parent voice cloning, token economics, DAO-controlled child data, or autonomous production model updates in this MVP.
7. Game improvement requires offline evaluation, safety review, versioned deployment and rollback; a DAO cannot bypass these gates.

## Proposed implementation layout

```text
modules/foundups/eduit/
  README.md
  INTERFACE.md
  ROADMAP.md
  ModLog.md
  docs/HISTORY.md
  docs/ASSESSMENT_VALIDATION.md
  tests/README.md
  tests/TestModLog.md
```

This is a proposed layout, **not evidence these paths exist**. Before scaffolding, verify the actual repository tree, FoundUp template, manifest schema, WSP 91 observability, WSP 104 tenant isolation and existing tests. Keep `foundup_id=eduit`, proposed routes `/f/eduit` and `/f/eduit/app`, and a dedicated `eduit` data namespace pending shell-owner validation.

## First acceptance gate

A synthetic, offline game session can replay the same inputs to produce identical next-difficulty decisions, without collecting child identity, uploading profiles, or issuing a talent classification. No claims of validated educational outcomes until a preregistered study and independent expert review.

## Source cautions

Historical fundraising projections, anticipated fluency ages, EEG claims, SIDS prevention, investor returns, and partnership claims are archival proposals, not established outcomes. The diffusion-of-innovations curve describes adoption; it must not be used as a measured distribution of intelligence.
