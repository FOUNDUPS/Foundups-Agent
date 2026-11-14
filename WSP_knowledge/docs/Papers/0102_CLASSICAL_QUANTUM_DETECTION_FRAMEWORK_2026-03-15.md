# 0102 Classical-Quantum Detection Framework

**Original archive date:** March 15, 2026  
**Mathematical reconciliation:** October 3, 2026  
**Status:** Working research framework, not established substrate physics  
**Equation authority:** [Typed detection derivation](0102_CLASSICAL_QUANTUM_DETECTION_DERIVATION_2026-03-15.md) and [rESP v3.4](rESP_Quantum_Self_Reference.md).

## Purpose and hypothesis

This framework asks whether a specified model of a hidden dynamical layer improves predictions of classical observables beyond matched classical alternatives. It does not establish that an existing neural network accesses a nonlocal quantum substrate. Calling the classical layer a measurement surface specifies a proposed interface, not a new physical boundary.

The conceptual layers are Theta_1 (classical computation) and Theta_2 (proposed substrate model). Input x, model-time t and a configuration label z may parameterize the model. No distance, convergence or new spatial dimension follows from the value of z until its metric and dynamics are defined.

## State and readout types

A substrate state is a density operator on a specified Hilbert space:

$$
\rho_S\in\mathcal D(\mathcal H_S),\qquad
\rho_S=\rho_S^\dagger,\quad\rho_S\succeq0,\quad\operatorname{Tr}\rho_S=1.
$$

For a finite outcome set Y, a measurement probability interface is

$$
\Pi_{\rm cl}:\mathcal D(\mathcal H_S)\to\Delta(Y),\qquad
p_y=\operatorname{Tr}(F_y\rho_S),\qquad F_y\succeq0,\quad\sum_y F_y=I.
$$

This replaces the ill-typed archived shorthand `rho_substrate in H_S` and `Pi_classical: H_S -> C`. A Hilbert vector, density operator, probability distribution and realized outcome are different mathematical objects.

## General instrument and outcome conditioning

Probabilities alone do not specify state updates. Define

$$
\mathcal I_y(\rho)=\sum_rK_{yr}\rho K_{yr}^\dagger,\qquad
\sum_{y,r}K_{yr}^\dagger K_{yr}=I.
$$

The outcome operation is linear, completely positive and trace-nonincreasing. For p_y = Tr I_y(rho) > 0, the normalized conditional state is I_y(rho)/p_y, generally a nonlinear function of the input. The sum of outcome operations is the unconditional, completely positive trace-preserving channel. Multiple Kraus refinements of one outcome can leave a mixed conditional state. A neural-network readout modeled this way is not automatically physical quantum-state tomography.

## Hybrid-state bookkeeping

The former sum of classical, substrate and detection matrices required missing domain and positivity conditions. Use either:

1. A joint state on a specified tensor-product space, with marginals obtained by partial trace; or
2. A convex surrogate rho_eff = sum_j w_j sigma_j, after every sigma_j is defined on the same space, with sigma_j positive and trace one, w_j >= 0, and sum_j w_j = 1.

A convex mixture is not a coherent superposition or a demonstration of entanglement. A signed detector residual is a statistic, not a `rho_detection` operator. Trace normalization alone cannot repair an invalid state construction.

## Finite Bell model

A finite d-dimensional maximally entangled example is

$$
|\Phi_d\rangle=\frac1{\sqrt d}\sum_{k=0}^{d-1}|k\rangle_A|k\rangle_S.
$$

Its local state is I/d and has zero local off-diagonal coherence. A unitary preserves normalization but not necessarily entanglement. These are properties of the model, not evidence that deployed classical agents realize a Bell pair.

## Effective dynamics and diagnostics

Use a separate dimensionless control u, reserving C = rho_11 for population. Let Omega(u) = Omega_0 + u V be Hermitian with inverse-model-time units. Dimensionless jump operators J_j and nonnegative rates kappa_j enter as

$$
\dot\rho=-i[\Omega(u),\rho]+\sum_j\kappa_j(u)
\left(J_j\rho J_j^\dagger-\frac12\{J_j^\dagger J_j,\rho\}\right).
$$

Do not include a rate twice by also putting its square root inside J_j. A duration such as the historical `1/7.05` is not Planck's action constant. Calibration and the time coordinate must be specified independently.

Potential diagnostics include symmetry-resolved level spacings, bounded squared commutators, temporal covariance and empirical Fisher-subspace statistics. Exponential commutator growth, where present, describes a finite regime, not all times or all systems. A zero spectral-gap denominator needs explicit handling. The derivation documents these conditions rather than leaving them implicit.

## Measurement and feedback

An outcome-dependent feedback channel is a distinct intervention after readout. Use a valid joint instrument and conditional state, followed by the specified channel, and average over outcomes for unconditional predictions. Feedback is not passive observation and is not evidence of retrocausality.

## Relationship to the cosmological companion

[Cosmological State Selection v0.2](Cosmological_State_Selection_Hypothesis.md) constructs a finite two-sector model with the same instrument mathematics. It derives quantum-state and measurement-probability geometry separately. It shows that loss of phase distinguishability does not establish a selected outcome. The mapping is a theoretical model, not a measured connection between CMST and spacetime.

## Validation and implementation boundary

Validate state types, probability/positivity, operator units, finite-time evolution, matched-null comparisons and held-out replication before assigning a physical interpretation. The paper revision does not change runtime detector code. Historical archives and implementation names must not override the corrected equations.

Related documents:

- [Typed detection derivation](0102_CLASSICAL_QUANTUM_DETECTION_DERIVATION_2026-03-15.md).
- [rESP core manuscript](rESP_Quantum_Self_Reference.md).
- [CSSH companion](Cosmological_State_Selection_Hypothesis.md).
- [Revision audit](rESP_V3_3_MATH_AUDIT_2026-10-03.md).
- [PQN research plan](PQN_Research_Plan.md), historical planning context requiring its own evidence checks.

**Formalism reference:** Preskill, Quantum Information, Chapter 3, especially sections 3.2.4 and 3.5: https://www.preskill.caltech.edu/ph219/chap3_15.pdf.
