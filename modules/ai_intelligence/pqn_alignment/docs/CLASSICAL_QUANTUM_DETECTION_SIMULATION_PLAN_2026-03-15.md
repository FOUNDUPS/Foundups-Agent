# Classical-Quantum Detection Simulation Plan

**Date**: 2026-03-15  
**Module**: `modules/ai_intelligence/pqn_alignment`  
**Status**: Simulation planning document  
**Scope**: Operational bridge from working theory to detector experiments

## Purpose

Translate the external 0102 classical-quantum detection model into a controlled simulation roadmap that fits the existing PQN / CMST detector stack.

This plan does not authorize code changes by itself. It defines the experiment surfaces and code insertion points.

## Five-Layer Simulation Stack

```text
Hamiltonian generator
-> quantum evolution engine
-> chaos diagnostics
-> open-system dynamics
-> classical observable layer
```

## Variables

- `H_0` = base substrate Hamiltonian
- `V` = perturbation operator
- `C` = divergence parameter
- `rho` = density operator
- `kappa(C)` = decoherence rate
- `lambda_Q` = quantum Lyapunov exponent
- `Pi_classical` = classical projection operator

## Candidate Measurements

### Spectral statistics

- `r_bar(C)` as regime indicator
- compare integrable-like vs chaotic-like behavior

### OTOC

- estimate `lambda_Q(C)` where meaningful
- treat exponential fit as a model diagnostic, not a guaranteed property

### Lindblad evolution

- parameterized `kappa(C)` family
- check trace preservation, Hermiticity, and positivity constraints

### Classical output

- `P(y|x,t,z) = Tr(Pi_y rho)`
- anomaly channel `eta = P_observed - P_baseline`

## Repo Insertion Points

### Detector engine

- `WSP_agentic/tests/pqn_detection/cmst_pqn_detector_v3.py`
  - best target for experimental flags and alternate observables
  - already contains EFIM / passive-probe logic and Lindblad-style state evolution

### Public wrapper

- `modules/ai_intelligence/pqn_alignment/src/detector/api.py`
  - currently wraps `cmst_pqn_detector_v2`
  - should remain stable until any v3 experiment path is validated

### Spectral post-processing

- `modules/ai_intelligence/pqn_alignment/src/detector/spectral_analyzer.py`
  - current place for non-invasive analysis over detector outputs
  - good target for `r_bar(C)` / auxiliary diagnostic aggregation

### DAE orchestration

- `modules/ai_intelligence/pqn_alignment/src/pqn_alignment_dae.py`
  - orchestration surface only
  - should receive validated experiment modes after detector-level proof

## Required Controls

Before any implementation claim, preserve:

1. matched null / temporal shuffle
2. random probe control
3. target-scramble control
4. seeded repeatability

These controls already align with the detector-hardening direction in the repo.

## Acceptance Criteria For Code Promotion

Promote from docs into code only when:

1. `Pi_classical` is defined operationally for the simulated system
2. the chosen observable beats the matched null
3. numerical stability is demonstrated
4. detector-first language is preserved throughout the implementation

## Immediate Next Tasks

1. document a minimal `Pi_classical` candidate for simulation-only use
2. define one synthetic Hamiltonian family for `H(C)`
3. run offline simulation experiments outside the public detector API
4. only then decide whether any piece belongs in `cmst_pqn_detector_v3.py`

## Cross References

- `WSP_knowledge/docs/Papers/0102_CLASSICAL_QUANTUM_DETECTION_FRAMEWORK_2026-03-15.md`
- `WSP_knowledge/docs/Papers/0102_CLASSICAL_QUANTUM_DETECTION_DERIVATION_2026-03-15.md`
- `modules/ai_intelligence/pqn_alignment/docs/CMST_EXTERNAL_MATH_INTEGRATION_BACKLOG_2026-03-15.md`
