# CMST External Math Integration Backlog

**Date**: 2026-03-15  
**Module**: `modules/ai_intelligence/pqn_alignment`  
**Status**: Backlog / intake stub  
**Source boundary**: external 012/0102 work not yet transcribed into this repo

## Purpose

Record where the externally developed math should land in PQN/CMST once it is transcribed into repo-visible form.

This file intentionally does **not** invent formulas. It only defines insertion points and acceptance criteria.

## Confirmed Integration Targets

These are already established by current technical extraction work and can absorb new derivations cleanly:

1. **Observable definition**
   - `A(theta) = log det(G_theta + epsilon I)`
   - primary detector scalar
   - target docs/code: CMST detector docs and `GeomMeter` / EFIM path

2. **Passive probe architecture**
   - adapter remains low-rank and non-perturbative
   - target docs/code: CMST detector header comments and protocol notes

3. **Control suite**
   - temporal shuffle
   - random probe
   - target scramble
   - target docs/code: detector CLI and paired-seed evaluation

4. **Subspace projection language**
   - adapter subspace pullback metric
   - target docs/code: implementation notes and paper-support materials

5. **Event thresholding**
   - z-score gating over running baseline
   - target docs/code: event emission and calibration docs

## External Math Intake Contract

When 012 provides the external derivation, convert it into the following repo artifacts:

1. a dated WSP knowledge note with the exact derivation
2. a technical extraction entry in:
   - `WSP_knowledge/docs/Papers/0102_TECHNICAL_EXTRACTIONS_2026-03-08.md`
3. implementation deltas for:
   - detector docs
   - CLI flags / config
   - code comments only where the derivation changes behavior
4. a validation plan:
   - synthetic control
   - matched null
   - seeded comparison

## Non-Negotiable Constraints

- no vibecoded formulas
- no ontology inflation
- no replacing detector-first terminology with mystical terms
- no code change until the derivation is written in repo-visible form

## Related Observations

The Microsoft STT `0102 -> 0-1-0-2` artifact is relevant as a symbolic-input evidence stream, but by itself it does not justify CMST math changes.

Cross reference:

- `modules/ai_intelligence/rESP_o1o2/docs/MS_STT_0102_HYPHEN_ARTIFACT_2026-03-15.md`
