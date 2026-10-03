# Cosmological State Selection

## A Measurement-Theoretic Hypothesis for the Emergence of Classical Spacetime

**Authors:** UnDaoDu (012) + 0102 pArtifacts  
**Date:** October 2026  
**Version:** 0.1  
**Status:** Speculative companion theory; non-load-bearing to rESP/CMST  
**Companion:** The Bell State of AI, rESP v3.3

---

## Abstract

This paper formalizes a narrow hypothesis motivated by the analogy between quantum measurement and cosmological classicalization. In ordinary quantum theory, a state is represented in a state space and a measurement instrument maps that state to an outcome-conditioned state. We ask whether emergence of a definite semiclassical spacetime can be modeled by an operation of the same mathematical class.

The proposal does **not** identify the pre-classical universe with a Hilbert space. A Hilbert space is a space of possible states. The hypothesized pre-classical universe is represented by a state, wave functional, or density operator in an appropriate cosmological state space. We define a Cosmological State-Selection Hypothesis (CSSH) in which a pre-classical state ρ_pre is mapped to a selected semiclassical sector by a quantum-instrument-like map M_cos,α.

The central analogy is therefore not "the universe was a photon." It is:

measurement of a quantum system  
and  
selection of a classical cosmological branch

may be instances of the same **mathematical state-selection form**, even if their physical triggers differ.

Penrose's Objective Reduction (OR) and Conformal Cyclic Cosmology (CCC) are treated separately. OR is relevant to physical state reduction; CCC supplies a conformal aeon-to-aeon boundary structure but is not itself a collapse law. No rESP or CMST observation is offered as evidence for CSSH.

---

## 1. Scope and Scientific Boundary

CSSH is a hypothesis-development paper.

It does not claim:

1. that a classical Big Bang is known to be a wavefunction collapse;
2. that current quantum gravity provides a unique cosmological Hilbert space;
3. that decoherence by itself selects one actual outcome;
4. that Penrose's CCC requires state collapse at the crossover;
5. that CMST or rESP has measured cosmological physics.

It asks one mathematical question:

> Can the transition from a pre-classical cosmological state to a definite semiclassical spacetime be represented by the same class of state-update maps used for quantum measurement?

If the answer is yes, a second physical question remains:

> What, if anything, supplies the state-selection mechanism?

These questions must remain separate.

---

## 2. Why "Hilbert Space" Is Not the Pre-State

Let

$$
\mathcal H_{\mathrm{cos}}
$$

denote an abstract cosmological state space.

A state is an element of that space, or more generally a density operator on it:

$$
|\Psi_{\mathrm{pre}}\rangle\in\mathcal H_{\mathrm{cos}},
$$

or

$$
\rho_{\mathrm{pre}}\in\mathcal D(\mathcal H_{\mathrm{cos}}).
\quad \text{(1)}
$$

Therefore,

$$
\boxed{\text{pre-classical state} \neq \text{Hilbert space}}
$$

while

$$
\boxed{\text{pre-classical state} \in \text{state space}}
$$

is the correct relationship.

This is the same distinction as:

- physical space versus a point in physical space;
- a vector space versus a vector in that space;
- the set of possible quantum states versus one actual quantum state.

The word **pre** is used here to mean pre-classical or pre-semiclassical. It does not require an ordinary classical time coordinate to exist "before" the Big Bang.

---

## 3. Quantum-Cosmology Starting Point

Canonical quantum cosmology commonly represents the state of the universe by a wave functional over spatial geometries and matter fields,

$$
\Psi[h_{ij}(\mathbf x),\phi(\mathbf x)],
\quad \text{(2)}
$$

rather than an ordinary one-particle wavefunction Ψ(x,t).

Schematically, the Wheeler-DeWitt constraint is

$$
\hat{\mathcal H}\Psi = 0.
\quad \text{(3)}
$$

DeWitt's canonical work and the Hartle-Hawking wave function of the universe provide established examples of this general language. The physical inner product, time variable, and full quantum-gravity state space remain nontrivial issues; CSSH therefore keeps H_cos abstract rather than pretending these problems are solved.

The relevant conceptual move is simply that a **quantum state of cosmology** is already a legitimate mathematical object in quantum cosmology. CSSH adds a proposed state-selection layer.

---

## 4. Ordinary Quantum Measurement

For a quantum state ρ, a measurement instrument can be represented by outcome operators {M_α} satisfying

$$
\sum_\alpha M_\alpha^\dagger M_\alpha = I.
\quad \text{(4)}
$$

The probability of outcome α is

$$
p_\alpha
=
\operatorname{Tr}
\left(
M_\alpha^\dagger M_\alpha \rho
\right).
\quad \text{(5)}
$$

Conditioned on outcome α, the post-measurement state is

$$
\rho_\alpha
=
\frac{
M_\alpha \rho M_\alpha^\dagger
}{
p_\alpha
}.
\quad \text{(6)}
$$

If the outcome is ignored, the nonselective channel is

$$
\mathcal E(\rho)
=
\sum_\alpha
M_\alpha \rho M_\alpha^\dagger.
\quad \text{(7)}
$$

This distinction matters. Equation (6) is an **outcome-conditioned selection**. Equation (7) is the average channel.

---

## 5. The Double-Slit Analogy

For a photon or other quantum system, a pre-measurement state can be written schematically as

$$
|\psi\rangle
=
\sum_i c_i |i\rangle.
\quad \text{(8)}
$$

A position-sensitive measurement maps the state into an outcome-conditioned branch,

$$
|\psi\rangle
\xrightarrow{\mathcal M_i}
|i\rangle,
$$

with probability determined by the measurement rule.

CSSH does not claim that the early universe literally behaves like a photon in a laboratory. The proposed analogy is narrower:

$$
\boxed{
\text{superposed/quantum state}
\xrightarrow{\text{state selection}}
\text{definite classical outcome}
}
$$

may be a scale-independent mathematical pattern.

This is a **shared-form hypothesis**, not a proof by transitivity. Quantum measurement in a laboratory does not logically imply cosmological state reduction. The hypothesis must earn that extension by consistency and prediction.

---

## 6. Cosmological State-Selection Hypothesis

Let the pre-classical cosmological state be

$$
\rho_{\mathrm{pre}}
\in
\mathcal D(\mathcal H_{\mathrm{cos}}).
$$

Let α label candidate semiclassical sectors—coarse-grained geometries, matter configurations, or decohered histories. Introduce a cosmological instrument

$$
\{M_{\mathrm{cos},\alpha}\}_\alpha
$$

such that

$$
\sum_\alpha
M_{\mathrm{cos},\alpha}^\dagger
M_{\mathrm{cos},\alpha}
=
I.
\quad \text{(9)}
$$

Then

$$
p_\alpha
=
\operatorname{Tr}
\left(
M_{\mathrm{cos},\alpha}^\dagger
M_{\mathrm{cos},\alpha}
\rho_{\mathrm{pre}}
\right)
\quad \text{(10)}
$$

and

$$
\rho_{\mathrm{classical},\alpha}
=
\frac{
M_{\mathrm{cos},\alpha}
\rho_{\mathrm{pre}}
M_{\mathrm{cos},\alpha}^\dagger
}{
p_\alpha
}.
\quad \text{(11)}
$$

Define

$$
\boxed{
\mathcal M_{\mathrm{cos},\alpha}:
\rho_{\mathrm{pre}}
\mapsto
\rho_{\mathrm{classical},\alpha}
}
\quad \text{(12)}
$$

as the **cosmological state-selection map**.

CSSH is the conjecture that the emergence of a definite semiclassical spacetime can be represented by a map of this form.

This is the mathematical core of the hypothesis.

---

## 7. What Counts as "Classical"?

The right-hand side of Eq. (12) should not merely be another arbitrary quantum state. It must satisfy a classicalization criterion.

Let {P_α} be coarse-grained projectors onto candidate semiclassical sectors. Define inter-sector coherence

$$
D_{\alpha\beta}
=
\left\|
P_\alpha \rho P_\beta
\right\|_1,
\qquad \alpha\ne\beta.
\quad \text{(13)}
$$

A decohered semiclassical regime should satisfy approximately

$$
D_{\alpha\beta}\rightarrow0
\quad
(\alpha\ne\beta),
\quad \text{(14)}
$$

while the selected state is concentrated in one sector α.

A stronger model would additionally require that expectation values of relevant geometric operators are sharply peaked around a semiclassical geometry:

$$
\frac{
\Delta O
}{
|\langle O\rangle|
}
\ll 1
\quad \text{for selected macroscopic observables } O.
\quad \text{(15)}
$$

Thus "collapse into the universe" becomes mathematically more precise:

$$
\text{pre-classical quantum state}
\rightarrow
\text{decohered, sharply peaked semiclassical sector}.
$$

---

## 8. Decoherence Is Not Automatically Selection

Environmental decoherence can suppress interference between alternatives. In the coarse-grained notation above,

$$
D_{\alpha\beta}\rightarrow0.
$$

But decoherence alone does not, in every interpretation of quantum theory, explain why exactly one outcome is actual.

CSSH therefore distinguishes:

1. **Classicalization:** interference between macroscopic sectors becomes negligible.
2. **Selection:** one sector is treated as the realized outcome.

A no-collapse interpretation may accept the first and reject the second as a fundamental process. An objective-collapse model asserts a physical second step. CSSH remains compatible with either possibility until a mechanism is specified.

---

## 9. Penrose: OR and CCC Are Different Pieces

### 9.1 Objective Reduction

Penrose has argued that quantum state reduction may require a modification of standard quantum mechanics involving gravitation. In Diósi-Penrose-style reasoning, a characteristic reduction timescale is often written schematically as

$$
\tau
\sim
\frac{\hbar}{E_G},
\quad \text{(16)}
$$

where E_G characterizes the gravitational self-energy associated with competing mass distributions.

For CSSH, this is relevant because it offers a candidate **physical trigger** for M_cos,α.

CSSH does not assume Eq. (16) is correct for cosmology. It treats objective reduction as one candidate mechanism.

### 9.2 Conformal Cyclic Cosmology

CCC proposes a succession of aeons. The remote future of one aeon is conformally related to the Big Bang of the next across a crossover 3-surface.

Schematically,

$$
\mathscr I^+_{n}
\sim
\mathscr B^-_{n+1}
\quad \text{across } \mathcal X.
\quad \text{(17)}
$$

This is a conformal-geometric relationship. It is **not**, by itself, a quantum measurement operator.

Therefore:

$$
\boxed{\text{CCC crossover} \neq \text{wavefunction collapse law}}
$$

and

$$
\boxed{\text{OR} \neq \text{CCC}}.
$$

A future theory could ask whether the crossover geometry constrains, prepares, or coincides with a state-selection process, but that requires a derivation.

---

## 10. A Combined Penrose-Compatible Question

The strongest version of the present research question is not:

> Is CCC collapse?

It is:

> Could a cosmological state-selection law be compatible with Penrose-style objective reduction and with the conformal boundary conditions of CCC?

One schematic possibility is

$$
\rho_{\mathcal X^-}
\xrightarrow{
\mathcal R_{\mathrm{OR}}
}
\rho_{\mathcal X^+,\alpha},
\quad \text{(18)}
$$

where X denotes a cosmological classicalization/crossover boundary and R_OR is a hypothetical reduction law.

Equation (18) is **not Penrose's equation** and is not asserted as CCC. It is a research placeholder showing where an objective-selection mechanism would have to enter.

---

## 11. Relationship to rESP and CMST

CSSH was motivated by the same general question that motivates CMST: how does a distributed state become an observed state?

The mathematics must nevertheless remain separated.

In rESP v3.3:

$$
C(t)=\rho_{11}(t)
$$

is a population proxy,

$$
E(t)=|\rho_{01}(t)|
$$

is a local coherence/coupling proxy,

$$
\mathcal W_{\mathrm{cov}}
=
\lambda_{\min}(g_{\mathrm{cov}})
$$

is a covariance near-singularity witness,

$$
\mathcal W_s
$$

is a sign-bearing adapter regularizer, and

$$
A(\phi)
=
\log\det(\widetilde G+\lambda I)
$$

is a Fisher-subspace observable.

None is a collapse operator.

The cosmological state-selection operation is

$$
\mathcal M_{\mathrm{cos},\alpha}.
$$

CMST may serve as a **toy laboratory for comparing dynamical and state-selection mathematics**, but rESP data cannot be promoted into evidence for cosmological collapse without an independent physical bridge.

---

## 12. Naming

To prevent category errors, use:

| Object | Recommended name |
|---|---|
| H_cos | cosmological state space |
| ρ_pre or Ψ_pre | pre-classical cosmological state |
| {M_cos,α} | cosmological measurement/state-selection instrument |
| M_cos,α | outcome-conditioned state-selection map |
| ρ_classical,α | selected semiclassical branch/state |
| X | possible cosmological classicalization/crossover boundary |
| C, E | CMST local observables/proxies |
| W_cov, W_s, A(φ) | CMST geometry/statistical diagnostics |

Do **not** use "Hilbert space" as the name of the state itself.

---

## 13. What Would Make CSSH Physics Rather Than Analogy?

CSSH must clear at least five gates.

### Gate 1 — State-space definition

Specify the physical state space, constraints, and inner product rather than leaving H_cos abstract.

### Gate 2 — Selection dynamics

Derive M_cos,α or an alternative nonlinear reduction law from a physical mechanism rather than inserting it by hand.

### Gate 3 — Born consistency

Explain whether and why the resulting weights reproduce

$$
p_\alpha
=
\operatorname{Tr}(E_\alpha \rho)
$$

or predict a controlled deviation.

### Gate 4 — Semiclassical limit

Show that the selected state yields general relativity and quantum field theory in the appropriate limit.

### Gate 5 — Distinguishing prediction

Derive an observation that differs from standard decoherence, no-boundary/tunneling cosmology, objective-collapse alternatives, or CCC without selection.

Until Gate 5 exists, CSSH is a mathematically organized hypothesis, not a tested cosmological theory.

---

## 14. Candidate Falsifiers

The proposal should be rejected or substantially revised if:

1. no consistent state-selection map can be defined on the relevant constrained quantum-gravity state space;
2. the map violates probability conservation or positivity without a justified replacement theory;
3. it cannot recover known semiclassical physics;
4. it predicts uncontrolled energy-momentum violation;
5. its observable predictions reduce exactly to standard decoherence with no additional explanatory or predictive content;
6. an alleged CCC connection requires treating the conformal crossover as a measurement despite no such structure in the theory.

---

## 15. Minimal Hypothesis

The entire proposal can be compressed to:

$$
\boxed{
\rho_{\mathrm{pre}}
\in
\mathcal D(\mathcal H_{\mathrm{cos}})
}
$$

and

$$
\boxed{
\rho_{\mathrm{pre}}
\xrightarrow{
\mathcal M_{\mathrm{cos},\alpha}
}
\rho_{\mathrm{classical},\alpha}
}
$$

with M_cos,α belonging to the same mathematical family used to describe quantum state selection.

Everything beyond those two statements—the trigger, the relation to gravity, OR, CCC, retrocausality, or rESP—is additional hypothesis.

---

## References

1. DeWitt, B. S. (1967). Quantum Theory of Gravity. I. The Canonical Theory. *Physical Review*, 160, 1113–1148.
2. Hartle, J. B., & Hawking, S. W. (1983). Wave function of the Universe. *Physical Review D*, 28, 2960–2975.
3. Halliwell, J. J., Hartle, J. B., & Hertog, T. (2019). What is the no-boundary wave function of the Universe? *Physical Review D*, 99, 043526.
4. Nielsen, M. A., & Chuang, I. L. (2010). *Quantum Computation and Quantum Information* (10th Anniversary ed.). Cambridge University Press.
5. Zurek, W. H. (2003). Decoherence, einselection, and the quantum origins of the classical. *Reviews of Modern Physics*, 75, 715–775.
6. Penrose, R. (2014). On the Gravitization of Quantum Mechanics 1: Quantum State Reduction. *Foundations of Physics*, 44, 557–575.
7. Penrose, R. (2010). *Cycles of Time: An Extraordinary New View of the Universe*. The Bodley Head.
8. Meissner, K. A., & Penrose, R. (2025). *The Physics of Conformal Cyclic Cosmology*. arXiv:2503.24263.

---

**Boundary statement:** CSSH is a speculative mathematical hypothesis. Its purpose is to turn the double-slit/cosmology analogy into equations precise enough to criticize, extend, or falsify.
