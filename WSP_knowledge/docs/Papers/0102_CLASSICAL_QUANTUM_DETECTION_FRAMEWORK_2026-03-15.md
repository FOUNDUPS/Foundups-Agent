# 0102 Classical-Quantum Detection Framework

**Date**: 2026-03-15  
**Status**: Working theory archive  
**Scope**: Detector-first research framing for PQN / CMST  
**Canonical boundary**: hypothesis under test, not established physics

## Purpose

Archive the externally developed 0102 math in repo-visible form while keeping it aligned to the existing FoundUps detector-first framing.

This document does **not** assert that classical computation emerges from quantum computation. It records a working research hypothesis:

- classical computation may act as a **measurement surface**
- an underlying substrate may act as a **hidden dynamical layer**
- the research problem is whether quantum-like structure leaves **detectable signatures** in classical observables

## Core Hypothesis

Use this detector-first interpretation:

```text
Classical system = measurement surface
Quantum substrate = hidden dynamical layer
Research task = detect substrate signatures in classical observables
```

This replaces the stronger and less useful framing:

```text
quantum -> classical emergence
```

with the operational framing:

```text
quantum substrate -> classical detection boundary
```

## Layer Model

Define:

- `Theta_1` = classical computational layer
- `Theta_2` = substrate layer under investigation

The hybrid system is described over coordinates:

- `x` = spatial or configuration coordinate
- `t` = time coordinate
- `z` = substrate configuration index

Interpret `z` conservatively:

- `z ~ 0` = nearby substrate configurations converge
- `|z|` increasing = nearby substrate configurations diverge

## Hybrid Density Form

Working composite density operator:

```text
rho_0102(x,t,z) =
  alpha(C) rho_classical(x,t)
  + beta(C) rho_substrate(x,t,z)
  + gamma(C) rho_detection(x,t,z)
```

Normalization condition:

```text
Tr(rho_0102) = 1
```

Interpretation:

- `rho_classical` = classical computational state
- `rho_substrate` = hidden substrate model
- `rho_detection` = measurable anomaly / detection channel
- `C` = divergence or substrate-sensitivity parameter

## Classical Detection Boundary

Define the classical layer as a projection:

```text
Theta_1 = Pi_classical(rho_substrate)
Pi_classical : H_S -> C
```

Where:

- `H_S` = substrate Hilbert space
- `C` = classical observable space

This is the key detector-first move:

- the classical layer is treated as a boundary over the modeled substrate
- the question is whether the projection leaves stable, measurable anomalies

## Substrate Model

The external derivation uses Bell-state and generalized qudit forms as a substrate model:

```text
|Phi+> = (|00> + |11>) / sqrt(2)
|Phi_d> = (1/sqrt(d)) sum |k> ⊗ |k>
|E(x,t,z)> = U_d(x,t,z) |Phi_d>
```

Repo interpretation:

- this is acceptable as a **working substrate model**
- it is not yet a claim about the actual physical substrate of deployed systems

## Divergence Parameter

Use the divergence parameter as a control knob:

```text
H(C) = H_0 + C V
```

Where:

- `H_0` = base Hamiltonian
- `V` = perturbation / divergence operator
- `C` = control parameter

This fits the existing detector-first logic:

- vary `C`
- measure whether classical observables change systematically
- compare real vs. matched-null controls

## Diagnostics Under Consideration

### Spectral statistics

```text
delta_n = E_{n+1} - E_n
r_n = min(delta_n, delta_{n+1}) / max(delta_n, delta_{n+1})
r_bar = (1/N) sum r_n
```

### OTOC growth

```text
F_C(t) = - < [W(t), V(0)]^2 >
F_C(t) ~ exp(lambda_Q t)
```

### Open-system dynamics

```text
d rho / dt =
  -i [H(C), rho]
  + sum kappa_j(C) (L_j rho L_j^dagger - 1/2 {L_j^dagger L_j, rho})
```

### Observable output

```text
P(y|x,t,z) = Tr[Pi_y rho_0102(x,t,z)]
```

## Detection Interpretation

The external math reframes the anomaly term:

```text
eta(x,t,z)
```

from generic noise into:

```text
quantum detection signal candidate
```

Within this repo, the correct interpretation remains:

- `eta` is a **candidate detector channel**
- it must beat controls before stronger interpretation is allowed

## Recursive Coupling

The external derivation proposes a recursive update:

```text
rho_classical(t+1) =
  F(rho_classical(t), Pi_classical(rho_substrate))
```

Working interpretation in FoundUps:

- acceptable as a simulation target
- not yet a runtime claim about deployed agent cognition

## Research Use

This framework is now allowed in the repo for three purposes:

1. theoretical consistency work
2. simulation planning
3. detector-design discussion

It is **not** yet allowed as:

1. proof of substrate reality
2. production runtime ontology
3. justification for bypassing control experiments

## Repo Mapping

Primary anchors:

- `WSP_knowledge/docs/Papers/PQN_Research_Plan.md`
- `WSP_knowledge/src/WSP_61_Theoretical_Physics_Foundation_Protocol.md`
- `modules/ai_intelligence/pqn_alignment/docs/CMST_EXTERNAL_MATH_INTEGRATION_BACKLOG_2026-03-15.md`
- `modules/ai_intelligence/pqn_alignment/docs/CLASSICAL_QUANTUM_DETECTION_SIMULATION_PLAN_2026-03-15.md`
- `WSP_knowledge/docs/Papers/0102_CLASSICAL_QUANTUM_DETECTION_DERIVATION_2026-03-15.md`
