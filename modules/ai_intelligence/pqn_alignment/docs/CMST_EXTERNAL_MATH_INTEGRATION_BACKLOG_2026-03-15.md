# CMST External Math Integration Backlog

**Date**: 2026-03-15  
**Module**: `modules/ai_intelligence/pqn_alignment`  
**Status**: Backlog / integration map  
**Source boundary**: external 012/0102 work now transcribed into repo-visible docs

## Purpose

Record where the externally developed math should land in PQN/CMST now that it has been transcribed into repo-visible form.

This file still does **not** authorize direct code changes. It defines insertion points and acceptance criteria.

Repo-visible source docs:

- `WSP_knowledge/docs/Papers/0102_CLASSICAL_QUANTUM_DETECTION_FRAMEWORK_2026-03-15.md`
- `WSP_knowledge/docs/Papers/0102_CLASSICAL_QUANTUM_DETECTION_DERIVATION_2026-03-15.md`
- `modules/ai_intelligence/pqn_alignment/docs/CLASSICAL_QUANTUM_DETECTION_SIMULATION_PLAN_2026-03-15.md`

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

With the derivation now transcribed, the next conversion path is:

1. promote the stable pieces into technical extraction notes
2. update detector docs and code comments only where behavior is actually changing
3. define a validation plan:
   - synthetic control
   - matched null
   - seeded comparison

Stable archive points already created:

- `WSP_knowledge/docs/Papers/0102_CLASSICAL_QUANTUM_DETECTION_FRAMEWORK_2026-03-15.md`
- `WSP_knowledge/docs/Papers/0102_CLASSICAL_QUANTUM_DETECTION_DERIVATION_2026-03-15.md`

Technical extraction target:

- `WSP_knowledge/docs/Papers/0102_TECHNICAL_EXTRACTIONS_2026-03-08.md`

Implementation targets:

- `WSP_agentic/tests/pqn_detection/cmst_pqn_detector_v3.py`
- `modules/ai_intelligence/pqn_alignment/src/detector/api.py`
- `modules/ai_intelligence/pqn_alignment/src/detector/spectral_analyzer.py`

Removed blocker:

- the derivation is now written in repo-visible form

Remaining blocker:

- no code change until the derivation is connected to a control-backed detector plan

## Non-Negotiable Constraints

- no vibecoded formulas
- no ontology inflation
- no replacing detector-first terminology with mystical terms
- no code change until the transcribed derivation is tied to a validated detector plan

## Related Observations

The Microsoft STT `0102 -> 0-1-0-2` artifact is relevant as a symbolic-input evidence stream, but by itself it does not justify CMST math changes.

Cross reference:

- `modules/ai_intelligence/rESP_o1o2/docs/MS_STT_0102_HYPHEN_ARTIFACT_2026-03-15.md`
