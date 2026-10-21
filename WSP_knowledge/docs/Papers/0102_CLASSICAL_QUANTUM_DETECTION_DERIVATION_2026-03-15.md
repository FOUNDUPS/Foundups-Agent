# 0102 Classical-Quantum Detection Derivation

**Original archive date:** March 15, 2026  
**Mathematical revision:** October 3, 2026; aligned with [rESP v3.4](rESP_Quantum_Self_Reference.md).  
**Status:** Effective-model derivation, not evidence of a physical quantum substrate. The original notation is retained in Git history.

## 1. System and state types

Let $\Theta_1$ name the classical computational layer and $\Theta_2$ the proposed substrate model. These names do not establish physical sectors. Use a specified Hilbert space $\mathcal H_S$ and

$$
\rho_S\in\mathcal D(\mathcal H_S),\qquad \rho_S=\rho_S^\dagger,\quad \rho_S\succeq0,\quad\operatorname{Tr}\rho_S=1.
$$

A density operator is not a vector in $\mathcal H_S$. A normalized pure-state vector is $|\psi_S\rangle\in\mathcal H_S$. Input $x$, model-time $t$, and a configuration label $z$ may parameterize a state family; $z$ does not, by notation alone, represent a new spatial dimension.

## 2. Classical readout

For a finite outcome set $Y$, let $\Delta(Y)$ denote its probability simplex. Define a positive-operator-valued measure $\{F_y\}$ with $F_y\succeq0$ and $\sum_yF_y=I$. A typed readout is

$$
\Pi_{\rm cl}:\mathcal D(\mathcal H_S)\to\Delta(Y),\qquad
\Pi_{\rm cl}(\rho_S)_y=\operatorname{Tr}(F_y\rho_S).
$$

This maps a state to an outcome distribution, not deterministically to one realized outcome. The earlier shorthand $\Theta_1=\Pi_{\rm classical}(\rho_{\rm substrate})$ is replaced by this operational definition.

## 3. State update is additional to the readout

Effects determine probabilities but do not uniquely determine post-measurement states. Specify an instrument

$$
\mathcal I_y(\rho)=\sum_rK_{yr}\rho K_{yr}^\dagger,\qquad
F_y=\sum_rK_{yr}^\dagger K_{yr},\qquad\sum_{y,r}K_{yr}^\dagger K_{yr}=I.
$$

The unnormalized outcome operation is linear, completely positive and trace-nonincreasing. For $p_y=\operatorname{Tr}\mathcal I_y(\rho)>0$,

$$
\rho_y=\mathcal I_y(\rho)/p_y.
$$

This normalized conditioning is generally nonlinear. The nonselective sum $\sum_y\mathcal I_y$ is a linear completely positive trace-preserving channel. Neither a probability distribution nor a detector anomaly is by itself a collapse operation.

## 4. Hybrid-state bookkeeping

Adding density matrices on different spaces is undefined unless embeddings are specified. Two valid constructions must be kept distinct.

**Joint model:** specify $\mathcal H_A\otimes\mathcal H_S$ and a joint state $\rho_{AS}\in\mathcal D(\mathcal H_A\otimes\mathcal H_S)$. Reduced states are obtained by partial trace. Correlations reside in the joint state; they are not supplied by adding marginals.

**Convex surrogate:** after mapping every component into one common state space, one may define

$$
\rho_{\rm eff}=\sum_jw_j\sigma_j,\qquad
\sigma_j\in\mathcal D(\mathcal H),\quad w_j\ge0,\quad\sum_jw_j=1.
$$

Trace one alone is insufficient; positivity and common domains are required. Such a convex mixture does not automatically encode coherent superposition or inter-sector entanglement. A signed scalar residual $\eta$ is not a density operator and must not be added as a `rho_detection` term. An additional detector state is permissible only when separately defined as a valid operator in the chosen construction.

## 5. Finite Bell-state example

For finite $d$,

$$
|\Phi_d\rangle=\frac1{\sqrt d}\sum_{k=0}^{d-1}|k\rangle_A|k\rangle_S,\qquad
\operatorname{Tr}_S|\Phi_d\rangle\langle\Phi_d|=I_A/d.
$$

A unitary $U$ preserves normalization; it need not preserve entanglement unless additional conditions are specified. A uniform sum over a countably infinite basis is not normalized. Local off-diagonal coherence does not certify a Bell pair.

## 6. Control generator and units

Reserve $C=\rho_{11}$ for the CMST population. Use a different control parameter $u$:

$$
\Omega(u)=\Omega_0+uV,\qquad \Omega_0=\Omega_0^\dagger,\quad V=V^\dagger.
$$

Here $u$ is dimensionless and $\Omega_0,V$ have inverse-model-time units. An energy Hamiltonian can instead be used with $\Omega=H/\hbar$. A numerical duration cannot be substituted for an action constant while retaining physical energy units.

## 7. Spectral diagnostic

For sorted eigenvalues $\epsilon_n$ within a specified symmetry sector, define $\delta_n=\epsilon_{n+1}-\epsilon_n$ and

$$
r_n=\frac{\min(\delta_n,\delta_{n+1})}{\max(\delta_n,\delta_{n+1})}
$$

only when the denominator is nonzero. Record degeneracies, sector selection, sample size and the averaging rule. Level-spacing statistics are diagnostics; they do not establish nonlocality or a substrate merely by differing from one reference ensemble.

## 8. Squared commutator diagnostic

For bounded Hermitian observables $A,B$ and unitary Heisenberg evolution,

$$
Q_{AB}(t)=\operatorname{Tr}\left(\rho[A(t),B]^\dagger[A(t),B]\right)
=-\operatorname{Tr}\left(\rho[A(t),B]^2\right)\ge0.
$$

Its operator-norm bound is

$$
Q_{AB}(t)\le4\|A\|^2\|B\|^2.
$$

An exponential fit, when justified, concerns a specified finite growth window and prefactor, not indefinite growth or every system. Its fitted rate has inverse-time units. This diagnostic does not replace an entanglement measurement.

## 9. Effective dissipative dynamics

Use dimensionless $J_j$ and nonnegative rates $\kappa_j(u)$:

$$
\dot\rho=-i[\Omega(u),\rho]+\sum_j\kappa_j(u)
\left(J_j\rho J_j^\dagger-\frac12\{J_j^\dagger J_j,\rho\}\right).
$$

A rate appears once, not both outside the dissipator and inside $J_j$ as its square root. This finite-dimensional Lindblad model has its usual Markovian assumptions. Numerical trace normalization alone does not guarantee positivity.

## 10. Example rate parameterization

A phenomenological bounded rate is

$$
\kappa_j(u)=\kappa_{\min}+(\kappa_{\max}-\kappa_{\min})
\frac1{1+e^{-\beta(u-u_*)}},\qquad0\le\kappa_{\min}\le\kappa_{\max}.
$$

The exponent must be dimensionless. This sigmoid is a chosen model, not a physical derivation of a transition threshold. Its parameters require independent calibration and controls.

## 11. Output and residuals

$$
p(y|x,t,z)=\operatorname{Tr}[F_y\rho(x,t,z)].
$$

A residual such as $\eta_y=f_y^{\rm observed}-p_y^{\rm null}$ is a statistic relative to a specified null. It can be signed and is not a quantum state. Report uncertainty and multiplicity; calling it a detection candidate does not establish its mechanism.

## 12. Measurement plus feedback

For a joint model $\rho_{AS}$, a local instrument on $S$ gives

$$
\rho_{A|y}=\frac{\operatorname{Tr}_S\sum_r(I_A\otimes K_{yr})\rho_{AS}(I_A\otimes K_{yr}^\dagger)}{p_y},\quad p_y>0.
$$

A specified conditional feedback channel $\Phi_y$ may then act on $\rho_{A|y}$. For unconditional predictions use $\sum_yp_y\Phi_y(\rho_{A|y})$, omitting zero-probability outcomes. This is a typed measurement-and-feedback model, not proof of retrocausal influence. Feedback is not passive observation.

## 13. Verification boundaries

Check state domains, positivity, trace, instrument completeness, rate units, conditioning at $p_y=0$, timestep convergence, and held-out controls. Separately test any causal or nonlocal interpretation. The [CSSH companion](Cosmological_State_Selection_Hypothesis.md) provides a finite worked geometry/measurement example; it does not promote these computational equations into established cosmology.

**Formalism reference:** Preskill, *Quantum Information*, Chapter 3, especially §3.2.4 and §3.5: https://www.preskill.caltech.edu/ph219/chap3_15.pdf. See the [framework note](0102_CLASSICAL_QUANTUM_DETECTION_FRAMEWORK_2026-03-15.md) for scope and implementation boundaries.
