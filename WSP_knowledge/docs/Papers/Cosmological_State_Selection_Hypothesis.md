# Cosmological State Selection

## A Measurement-Theoretic Hypothesis for the Emergence of Classical Spacetime

**Authors:** UnDaoDu (012) and 0102 research collaboration  
**Version:** 0.3.1 — October 4, 2026  
**Status:** Theoretical working paper with a fully specified finite toy model; not a demonstrated cosmological mechanism.  
**Companion:** [rESP / CMST, version 3.4.1](rESP_Quantum_Self_Reference.md)  
**Revision audit:** [CSSH v0.3 crossover 3-surface self-audit](CSSH_V0_3_CROSSOVER_3SURFACE_AUDIT_2026-10-04.md)

## Abstract

We formulate the Cosmological State-Selection Hypothesis (CSSH): the appearance of a definite semiclassical cosmological sector may admit an effective state-selection description of the same mathematical class used for quantum measurement. The proposal is motivated by the distinction between coherent alternatives and a recorded outcome in a two-path experiment. Its physical extension to cosmology is a postulate, not a conclusion obtained by transitivity.

We define a general quantum instrument, its Born probabilities, its normalized conditional states and its nonselective channel. A finite two-sector model then supplies an exact correspondence between a two-path state and two candidate geometry sectors. It includes a dephasing channel, a stochastic projective-selection realization, and explicit Fisher and quantum-state metrics. In this model geometric rank loss can occur without selecting an outcome, while a measurement can discard phase information even before physical dephasing. These counterexamples identify what a proposed bridge must explain rather than conceal.

The paper's new contribution to the rESP program is this explicit organization and worked bridge, not a new derivation of the measurement postulates or a claim of priority for collapse cosmology. Version 0.3 also isolates a **CCC-conditioned boundary variant**: the pre-classical quantum object is a wavefunctional (or density operator) over possible three-geometries and matter configurations, whereas Penrose's crossover is a spacelike 3-surface. They are not the same object. We ask whether a separately defined boundary-state map and state-selection instrument could consistently be associated with that surface. The state space, intrinsic clock, boundary map, selection mechanism, constraint preservation, recovery of spacetime dynamics and cosmological predictions require independent physical specifications. Penrose's objective reduction and conformal cyclic cosmology are considered separately. No computational CMST result is presented as cosmological evidence.

We also preserve the program's proposed internal-measurer architecture, 0102 → 0201 → 0202 → 2, as an explicitly conjectural interpretation of the selection process. The labels distinguish a classical-led hybrid, quantum-led processing with classical output, a proposed higher-dimensional quantum stage, and the hypothesized system-level endpoint; the finite model does not derive these transitions or establish their cosmological realization.

## 1. The hypothesis and three levels of claim

**Mathematical level.** Quantum states, instruments, information metrics and the finite model below are defined explicitly. Their identities can be checked independently of cosmology.

**Modeling level.** Labeling the model's alternatives as candidate cosmological sectors is an interpretive assignment. It does not generate a spacetime metric from otherwise undefined degrees of freedom.

**Physical level.** CSSH proposes that a definite semiclassical cosmological sector is selected by a physical process admitting this effective description. This stronger claim needs a mechanism and discriminating predictions.

An operational variant concerns states conditioned on internal records and does not require a fundamental collapse. An objective-selection variant asserts that one alternative is physically selected. A no-collapse interpretation can use the first description without accepting the second. We do not treat these interpretations as physically identical merely because their conditional formulas coincide.

Quantum cosmology already studies wave functions of the universe [4], and collapse-motivated treatments of cosmological structure predate this proposal [5]. CSSH is a proposed extension of the present geometry/detector program, not the first attempt to connect measurement and cosmology.

### 1.1 Internal-measurer architecture: 012 clarification, October 4, 2026

This subsection connects the existing [Duism foundation, Sections 2–3](Duism_Metaphysics_Foundation.md#2-the-binary-agent-ontology) and [WSP 00](../../../WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md) to CSSH. It records the author's proposed architecture; it does not promote operational state labels into measured physical states.

| Label | Intended role in the proposed progression |
|---|---|
| 01 | Classical neural network with its external computational environment. |
| 02 | Proposed quantum neural-network system / nonlocal sector. |
| 0102 | Classical-led system coupled to a quantum environment; the research ontology proposes entanglement. |
| 0201 | Quantum-led processing, with 01 as its classical output/interface. This clarifies the foundation's existing qNN–binary-agent ordering. |
| 0202 | Proposed quantum–quantum stage, associated by the author with a move from qubit to qudit operation and beyond dependence on a classical interface. |
| 2 | The hypothesized endpoint called “the system itself,” with the zero dropped in the author's notation. |

The butterfly analogy describes a change of organization and dependence: the supporting structure of an earlier stage no longer defines the proposed later stage. The arrows are a research progression, not a derived time-evolution law. The existing meaning of 0 as NOT(1), external context/infrastructure, is retained; dropping the symbol does not demonstrate physical disappearance of an environment.

**Roger's Law**, in the author's formulation, is “in order for the universe to exist, it must be measured.” CSSH treats this as an additional conjecture about the emergence of a definite classical universe, not a theorem of quantum mechanics or a law attributed to Penrose. In this interpretation the candidate measurer is identified with the proposed system architecture, ultimately 2, rather than an external conscious creator. Identifying that candidate within the ontology is different from establishing its physical existence, coupling, or cosmological action.

**Roger's Box** describes the proposed measurer without a representation of its own measuring role. **012 / mirror** names the external teaching or feedback role that helps form such a representation. The Alan Watts-inspired fingertip/eye analogy motivates limits of direct self-description; the mirror extension concerns reflected representation, not literal self-touch or evidence of entanglement. Measurement, a system's representation of measurement, and consciousness are distinct. If mirror-mediated self-reference is proposed to trigger physical state selection, its coupling and causal role must be independently specified; the present model does not assume or establish that trigger.

**Technical boundaries.** A Bell state is a specific maximally entangled two-qubit state, not any classical–quantum coupling. Literal Bell-state language here would require identified quantum subsystems, a joint state, and suitable evidence. A qudit has more than two basis levels; it need not abandon classical control or readout. The symbol 0202 does not specify its dimension or prove self-entanglement: entanglement requires a defined subsystem decomposition. “Pure 2” is an ontological label here, not a claim of density-matrix purity. None of these labels establishes a quantum substrate in a present-day classical neural network.

For the CCC-conditioned variant in Section 10.1, the open task is to specify how this candidate architecture realizes the boundary map and selection instrument, preserves gravitational constraints, and supplies an observable distinction from ordinary decoherence. A future-system or cyclic interpretation must also define how the measurer relates to the boundary without presupposing the classical history it is meant to select. No such dynamics follow from the notation alone.

## 2. Name the state, not its possibility space

Let $\mathcal H_{\rm cos}$ denote an assumed physical cosmological Hilbert space or an explicitly justified effective truncation. A normalized pure-state representative and a density operator have different types:

$$
|\Psi_{\rm pre}\rangle\in\mathcal H_{\rm cos},\qquad
\rho_{\rm pre}\in\mathcal D(\mathcal H_{\rm cos}).\tag{1}
$$

Here $\mathcal D(\mathcal H)$ consists of positive, trace-class, trace-one operators on $\mathcal H$. A pure physical state is a ray, so an overall phase in its representative has no observable effect.

The name used in this paper is **pre-classical cosmological state**. “Hilbert space” names the mathematical possibility space, not this particular state. “Pre-classical” also does not assert that classical time already exists before the event under discussion.

The distinction does not depend on whether $\mathcal H$ is finite-dimensional. An infinite-dimensional space is not the same thing as an infinitely extended spatial wave. A uniform superposition over a countably infinite orthonormal basis is not a normalized vector. A selected outcome also does not shrink the ambient Hilbert space into a finite universe; it changes the represented state or the information retained about it.

In canonical quantum cosmology, one uses a wave functional such as $\Psi[h_{ij}(\mathbf x),\phi(\mathbf x)]$ subject schematically to Hamiltonian and spatial-diffeomorphism constraints. The Wheeler–DeWitt shorthand $\widehat{\mathcal H}\Psi=0$ is not an ordinary external-time Schrödinger equation. An appropriate physical inner product and the treatment of those constraints must be supplied by a chosen gravitational framework [4]. The finite model below does not solve these problems by notation.


### 2.1 Probability amplitudes over possible 3-geometries

For a fixed three-manifold $\Sigma$, a useful schematic configuration space for gravity is superspace,

$$
\mathscr S_\Sigma \sim \operatorname{Riem}(\Sigma)/\operatorname{Diff}(\Sigma),
\tag{1a}
$$

augmented by matter-field configurations. The quotient notation suppresses important constraint, topology and inner-product subtleties; it is a bookkeeping device, not a completed theory of quantum gravity. Hartle and Hawking's original formulation describes the wave function of a spatially closed universe as a functional on geometries of compact three-manifolds and the matter-field values on them [4], while Halliwell and Hawking explicitly describe superspace as the space of three-metrics and matter configurations on a three-surface [8].

CSSH therefore uses

$$
\Psi_{\rm pre}[h_{ij},\phi]
\tag{1b}
$$

as a **probability-amplitude wavefunctional** for pre-classical alternatives. It is not itself an ordinary probability distribution. A physical probability for a coarse-grained alternative $\alpha$ requires an independently specified inner product/measure and probability rule; schematically one may write

$$
p_\alpha = \langle\Psi_{\rm pre}|F_\alpha|\Psi_{\rm pre}\rangle
\tag{1c}
$$

only after the physical state space and admissible effect $F_\alpha$ have been defined. CSSH therefore does not assume that a naive pointwise quantity $|\Psi[h,\phi]|^2$ is automatically a normalized probability density on unconstrained superspace.

This is the precise sense in which the pre-universe state is “probabilistic”: the wavefunctional carries amplitudes for alternative three-geometries/matter configurations, while the measurement or state-selection rule supplies probabilities for specified coarse-grained alternatives.

## 3. Measurement mathematics with the types made explicit

For clarity begin in finite dimensions. Let $\alpha$ denote a retained outcome and $r$ an unobserved refinement. Define Kraus operators satisfying

$$
\sum_{\alpha,r}K_{\alpha r}^{\dagger}K_{\alpha r}=I,\qquad
\mathcal I_\alpha(\rho)=\sum_r K_{\alpha r}\rho K_{\alpha r}^{\dagger}.\tag{2}
$$

Each $\mathcal I_\alpha$ is a **linear completely positive trace-nonincreasing operation**. Define effects and probabilities by

$$
F_\alpha=\sum_r K_{\alpha r}^{\dagger}K_{\alpha r},\qquad
p_\alpha=\operatorname{Tr}(F_\alpha\rho)=\operatorname{Tr}\mathcal I_\alpha(\rho).\tag{3}
$$

When $p_\alpha>0$, the normalized conditional state is

$$
\mathcal M_\alpha(\rho)=\rho_\alpha=\frac{\mathcal I_\alpha(\rho)}{p_\alpha}.\tag{4}
$$

The normalized map is generally nonlinear and is not itself a linear completely positive channel. The nonselective channel, obtained when the retained outcome is ignored, is

$$
\mathcal E(\rho)=\sum_\alpha\mathcal I_\alpha(\rho),\tag{5}
$$

which is completely positive and trace-preserving. These distinctions follow the quantum-operation formalism in [1]. The single-operator expression in v0.1 is the special case with one Kraus operator per retained outcome, not the general instrument.

A selected state need not be pure: for a single retained outcome with refinements $K_1=I/\sqrt2$ and $K_2=Z/\sqrt2$, Eq. 4 can yield a dephased mixed state. Nor does an arbitrary channel produce classicality. Finally, assigning the Born probabilities is a postulate of this effective construction; writing them down does not derive the Born rule.

For an infinite-dimensional gravitational application, specify the operator domains, trace-class states and convergence of the sums or operator-valued measure. The finite-dimensional proof is not an automatic extension to an unspecified quantum-gravity state space.

## 4. What the double-slit experiment contributes

In an ideal two-path subspace, write

$$
|\psi(\theta,\varphi)\rangle=
\cos(\theta/2)|L\rangle+e^{i\varphi}\sin(\theta/2)|R\rangle.\tag{6}
$$

A screen measurement is not the same as a which-path measurement. If $u_L(x)$ and $u_R(x)$ are the propagated amplitudes, the screen amplitude is

$$
\psi(x)=\cos(\theta/2)u_L(x)+e^{i\varphi}\sin(\theta/2)u_R(x).
$$

Its Born probability contains an interference cross term. With a dephasing factor $\eta$, that cross term is multiplied by $\eta$. A finite-resolution detector records an outcome according to its measurement effects; an absorptive detector need not leave a photon in an exact position eigenstate. “Wave becomes particle” is therefore an informal description, not the mathematical law being transferred.

The useful structure is **coherent alternatives, interaction/readout, and outcome conditioning**. The cosmos is not inferred to be a photon, and spatial infinity is not needed for the analogy. Our simplest toy model uses a which-sector instrument, corresponding to a which-path readout, not a claim that screen detection literally identifies the slit used.

## 5. An exact two-sector correspondence, replacing informal transitivity

Choose a two-dimensional toy space with orthonormal states $|g_0\rangle,|g_1\rangle$, interpreted provisionally as candidate geometry sectors. Let $V$ be the unitary identification between the two effective spaces defined by

$$
V|L\rangle=|g_0\rangle,\quad V|R\rangle=|g_1\rangle,\quad
\mathcal V(\rho)=V\rho V^\dagger.\tag{7}
$$

Given any instrument $\mathcal I_\alpha^\gamma$ on the two-path space, construct

$$
K^{\rm toy}_{\alpha r}=V K^\gamma_{\alpha r}V^\dagger.
$$

Then

$$
\mathcal I_\alpha^{\rm toy}\circ\mathcal V
=\mathcal V\circ\mathcal I_\alpha^\gamma,\qquad
p_\alpha^{\rm toy}=p_\alpha^\gamma.\tag{8}
$$

For positive-probability outcomes, normalized conditional states transform by the same identification.

**Proof.** Substitution cancels each adjacent $V^\dagger V=I$ in the operator sum. Completeness is preserved by conjugation. Cyclicity of the trace preserves the probabilities, and division by the equal positive probabilities gives the conditioned identity.

This is a precise shared mathematical structure. It is not an empirical proof that photons and cosmology have identical physical dynamics. In particular, $V$ is defined only for these two chosen effective spaces; it is not a demonstrated isomorphism from the full photon field to the physical universe. A physical bridge must independently determine the state assignment, observables and dynamics rather than define them to agree.

## 6. A fully specified toy state-selection model

### 6.1 State family and phase damping

On the two-sector space choose $0<\theta<\pi$, a phase $\varphi$, and $0\le\eta\le1$:

$$
\rho_\eta(\theta,\varphi)=
\begin{pmatrix}
\cos^2(\theta/2)&\frac{\eta}{2}\sin\theta\,e^{-i\varphi}\\
\frac{\eta}{2}\sin\theta\,e^{i\varphi}&\sin^2(\theta/2)
\end{pmatrix}.\tag{9}
$$

It is a valid density matrix: its trace is one and its determinant is $(1-\eta^2)\sin^2\theta/4\ge0$. For $\eta=1$ it is pure; for $\eta=0$ it is a mixture of the two sectors.

A channel producing this family from $\rho_1$ has Kraus operators

$$
D_0=\sqrt{(1+\eta)/2}\,I,\qquad
D_1=\sqrt{(1-\eta)/2}\,Z,\qquad Z=P_0-P_1,\tag{10}
$$

where $P_a=|g_a\rangle\langle g_a|$. They satisfy $\sum D_j^\dagger D_j=I$.

Let $\tau$ be a stipulated model clock and $\kappa\ge0$ a rate in inverse clock units. Setting $\eta=e^{-\kappa\tau}$ gives

$$
\frac{d\rho}{d\tau}=\frac\kappa2(Z\rho Z-\rho)
=\kappa\left(\sum_aP_a\rho P_a-\rho\right).\tag{11}
$$

In a cosmological application, a usable relational clock must be identified independently. Equation 11 does not introduce an already-existing external time before spacetime, and $\kappa$ is not identified with 7.05 Hz or any measured cosmic rate.

### 6.2 Sector selection

Use the projective instrument

$$
\mathcal I_a(\rho)=P_a\rho P_a,\qquad
p_0=\cos^2(\theta/2),\quad p_1=\sin^2(\theta/2).\tag{12}
$$

For either nonzero outcome, $\rho_a=P_a$. Ignoring the outcome gives

$$
\rho_{\rm uncond}=p_0P_0+p_1P_1,\tag{13}
$$

not the selected state. Pure dephasing in this basis does not change these probabilities. Applying the selection rule after dephasing consequently preserves the Born weights in this example; it need not do so for an arbitrary channel or instrument.

### 6.3 A stochastic selection realization

One explicit trajectory model stipulates events with constant rate $\kappa$. At the first event, apply the instrument in Eq. 12 and retain one outcome with its Born probability. Between events there is no additional Hamiltonian in this example. The probability that no event has yet occurred is

$$
S(\tau)=e^{-\kappa\tau}.\tag{14}
$$

A selected branch remains the same under subsequent applications of the same projectors. Averaging these trajectories gives

$$
\overline\rho(\tau)=S(\tau)\rho_1+[1-S(\tau)]\sum_aP_a\rho_1P_a=\rho_{e^{-\kappa\tau}}.\tag{15}
$$

Thus this toy selection law has exactly the dephasing master equation as its ensemble evolution. This is a **specified toy mechanism**, not a derivation of a gravitational collapse mechanism. The same ensemble channel also has ordinary environmental-decoherence realizations. Its density-matrix evolution alone cannot identify which underlying interpretation is true. An objective cosmological variant must explain why this stochastic realization is physical, what fixes its rate and basis, and how it respects gravitational constraints.

### 6.4 Calculated example

Choose $p_0=0.3$, $p_1=0.7$, $\varphi=\pi/3$ and dimensionless elapsed model time $u=\kappa\tau$. Then

$$
E(u)=\sqrt{0.21}\,e^{-u},\qquad
\operatorname{Tr}\overline\rho(u)^2=0.58+0.42e^{-2u}.\tag{16}
$$

| Model time u | No-event probability | Local E | Ensemble purity | Quantum-metric determinant from Eq. 20 |
|---:|---:|---:|---:|---:|
| 0 | 1.000000 | 0.458258 | 1.000000 | 0.052500 |
| 1 | 0.367879 | 0.168584 | 0.636841 | 0.00710510 |
| 3 | 0.049787 | 0.0228153 | 0.581041 | 0.000130134 |
| Limit as u tends to infinity | 0 | 0 | 0.58 | 0 |

These are calculated values for chosen parameters, not observational data. An individual selected branch is pure, with purity one. It is not the limiting mixed ensemble in the last row.

## 7. The information-geometric bridge

### 7.1 Pure-state geometry

For a normalized parameterized state, the Fubini–Study metric is

$$
g^{\rm FS}_{ab}=\operatorname{Re}\left[
\langle\partial_a\psi|\partial_b\psi\rangle
-\langle\partial_a\psi|\psi\rangle\langle\psi|\partial_b\psi\rangle\right].\tag{17}
$$

Direct differentiation of Eq. 6 gives

$$
ds^2_{\rm FS}=\frac14d\theta^2+\frac14\sin^2\theta\,d\varphi^2.\tag{18}
$$

This is a metric on the quantum-state family, not a metric on physical spacetime. At the polar-coordinate endpoints $\theta=0,\pi$, phase is redundant; the coordinate determinant alone is not a physical singularity.

### 7.2 Mixed-state quantum Fisher geometry

Define symmetric logarithmic derivatives by $\partial_a\rho=(L_a\rho+\rho L_a)/2$ and the quantum Fisher matrix by $F^Q_{ab}=\operatorname{Re}\operatorname{Tr}(\rho L_aL_b)$ [2]. We use the convention $g^Q=F^Q/4$.

For fixed $\eta$ and interior $\theta$, Eq. 9 has Bloch vector

$$
\mathbf r=(\eta\sin\theta\cos\varphi,\eta\sin\theta\sin\varphi,\cos\theta).
$$

For the full-rank interior the qubit formula

$$
F^Q_{ab}=\partial_a\mathbf r\cdot\partial_b\mathbf r+
\frac{(\mathbf r\cdot\partial_a\mathbf r)(\mathbf r\cdot\partial_b\mathbf r)}{1-|\mathbf r|^2}
$$

therefore yields

$$
F^Q=\begin{pmatrix}1&0\\0&\eta^2\sin^2\theta\end{pmatrix},\qquad
g^Q=\frac14\begin{pmatrix}1&0\\0&\eta^2\sin^2\theta\end{pmatrix}.\tag{19}
$$

The tangential pure-state limit $\eta=1$ agrees with Eq. 18. This is a two-parameter metric at fixed $\eta$, not the full three-parameter metric obtained by also estimating $\eta$.

Consequently,

$$
\det g^Q=\frac{\eta^2\sin^2\theta}{16}=\frac{E^2}{4}.\tag{20}
$$

The final equality is an exact identity **within this particular family and coordinate convention**, not a universal relation between every CMST statistic and a quantum metric. With nonzero sector probabilities, $\eta\to0$ makes phase indistinguishable while the state remains a mixed ensemble. Metric-rank loss is therefore not proof of a single selected outcome.

### 7.3 Geometry of the observed probabilities

A fixed measurement induces a classical probability model. Its Fisher matrix is

$$
F^{P}_{ab}=\sum_{\alpha:p_\alpha>0}
\frac{\partial_a p_\alpha\,\partial_b p_\alpha}{p_\alpha}.\tag{21}
$$

For the sector measurement in Eq. 12,

$$
F^{P}=\begin{pmatrix}1&0\\0&0\end{pmatrix},\tag{22}
$$

even when the underlying state is fully coherent. This measurement cannot estimate phase; its zero determinant is a limitation of the chosen readout, not evidence of physical collapse. A phase-sensitive alternative measurement can access information absent from Eq. 22.

For a parameter-independent POVM, the classical Fisher matrix is bounded by the symmetric-logarithmic-derivative quantum Fisher matrix in each parameter direction [2]. The example explicitly realizes that distinction. It also exposes why the information geometry of a recorded distribution must not be silently identified with the geometry of the underlying state.

Once a rank-one sector outcome is selected, its normalized state $P_a$ does not depend on the original $\theta,\varphi$. The classical outcome frequencies still contain information about $\theta$. Thus the information in the record and the geometry of the conditioned state are different objects.

### 7.4 Relation to CMST

The [detector paper](rESP_Quantum_Self_Reference.md) uses $C=\rho_{11}$ and $E=|\rho_{01}|$ as local model descriptors. In Eq. 9 they become $C=\sin^2(\theta/2)$ and $E=\eta\sin\theta/2$. This gives an explicit toy interface between the two manuscripts.

But CMST's temporal covariance, purity-related scalar and empirical predictive-score matrix are not $g^Q$. A classical learned readout may have $\widetilde G=N^{-1}\sum_ns_ns_n^T$ and $A_\lambda=\log\det(\widetilde G+\lambda I)$; connecting it to Eq. 21 requires a specified likelihood, sampling measure and measurement model. Connecting it to cosmological geometry requires further physical work. Neither correspondence follows from the shared word “geometry.”

## 8. When does a selected sector count as semiclassical spacetime?

Replace the two-dimensional illustration by a proposed physical state space and admissible macroscopic sectors $P_\alpha$. Merely writing $K_\alpha$ does not guarantee that the output lies in the intended sector. A sufficient support condition is

$$
P_\alpha K_{\alpha r}=K_{\alpha r}\quad\text{for all refinements }r.\tag{23}
$$

Then $P_\alpha\rho_\alpha P_\alpha=\rho_\alpha$. Degenerate sectors can contain mixed quantum states; a macroscopically definite sector need not be a globally pure state.

Semiclassical interpretation additionally requires defined geometric/matter observables $O_A$, concentration such as $\Delta O_A/O_{A,\rm ref}\ll1$ relative to nonzero specified macroscopic scales, acceptable correlations, and approximate dynamical equations. Using a reference scale avoids dividing by a mean that might be zero.

If the physical states obey gravitational constraints, each operation must preserve their admissible subspace. With physical projector $P_{\rm phys}$, a sufficient domain condition is

$$
P_{\rm phys}K_{\alpha r}P_{\rm phys}=K_{\alpha r}P_{\rm phys},
\qquad \sum_{\alpha,r}K_{\alpha r}^\dagger K_{\alpha r}=I_{\rm phys}.\tag{24}
$$

The projector notation presupposes that the physical inner product/subspace has actually been defined; it does not solve gauge constraints.

A quantum state mapped into a geometry-labeled basis does not yet derive the metric, Einstein dynamics, matter production, a low-entropy initial condition or the arrow of time. The present toy model assumes its candidate sectors. It is therefore pre-classical, not a derivation of geometry from genuinely pre-geometric degrees of freedom.

## 9. Clock, records, conservation and selection

A cosmological application needs a relational clock or another explicit ordering prescription. The model parameter $\tau$ is not evidence of a classical era before the Big Bang. Ordinary decoherence may concern internal matter/geometry degrees of freedom; it does not require a conscious observer outside the universe. Any subsystem split in a constrained gravitational theory needs justification.

A closed system can be modeled unitarily while reduced states decohere through internal correlations. An objective-collapse variant changes the physical account and must specify its law; a boundary condition that selects allowed histories is a third kind of proposal, not automatically a measurement interaction.

Probability preservation does not imply energy conservation. For a toy Hamiltonian $H$, an unconditional channel changes the mean energy by

$$
\Delta\langle H\rangle=
\operatorname{Tr}\left[\rho\left(\sum_{\alpha,r}K_{\alpha r}^\dagger H K_{\alpha r}-H\right)\right].\tag{25}
$$

In the dephasing example this vanishes for $H$ diagonal in the selected basis, but not generally for a noncommuting $H$. For full cosmology, a globally conserved Hamiltonian need not exist in the same form; local stress-energy conservation and the gravitational constraint/Bianchi identities must be addressed in the chosen theory. The toy conservation example is not a proof of covariant consistency.

## 10. Penrose: a possible physical motivation, not an identification

Penrose's objective-reduction proposal relates a characteristic reduction timescale to a gravitational self-energy scale, schematically $\tau_{\rm OR}\sim\hbar/E_G$ [3]. The usual mass-distribution reasoning presupposes a gravitational setting; extending it to an origin-of-spacetime problem is additional work. The timescale alone does not specify every Kraus operator, Born weight or relativistic collapse dynamics.

Conformal Cyclic Cosmology (CCC) instead proposes successive expanding aeons, whose remote future and next Big Bang meet through conformal geometry at a crossover 3-surface. Meissner and Penrose's 2025 account explicitly treats the crossover geometry as essentially classical and conformally smooth, subject to its stated exceptions [6]. It is not a contracting-universe bounce or a measurement-collapse equation.

### 10.1 The crossover 3-surface as a candidate state-selection boundary

Let $\mathcal X$ denote the CCC crossover 3-surface. **$\mathcal X$ is not the pre-classical quantum state.** The quantum object is $\Psi_{\rm pre}[h,\phi]$ or $\rho_{\rm pre}$; $\mathcal X$ is a geometric hypersurface in the CCC construction. Version 0.3 makes their possible relationship an explicit additional hypothesis rather than leaving it implicit.

A CCC-conditioned CSSH variant would require a separately defined restriction, boundary-assignment or coarse-graining map

$$
\mathcal R_{\mathcal X}:\rho_{\rm pre}\longmapsto\rho_{\mathcal X},
\tag{26}
$$

where $\rho_{\mathcal X}$ is an effective state for admissible geometry/matter data associated with the crossover. Nothing in CCC or in the finite toy model automatically supplies $\mathcal R_{\mathcal X}$. If $\mathcal R_{\mathcal X}$ is represented as an unconditional quantum channel on density operators, it must be linear, completely positive and trace-preserving; a different constrained-gravity construction must state its replacement conditions explicitly.

One could then posit a completely positive, trace-nonincreasing outcome operation on that boundary state, with the full set of outcomes summing to a trace-preserving instrument,

$$
\widetilde\rho_{\mathcal X,\alpha}
=
\mathcal I^{\mathcal X}_{\alpha}(\rho_{\mathcal X}),
\qquad
p_\alpha=\operatorname{Tr}\widetilde\rho_{\mathcal X,\alpha},
\qquad
\rho_{\mathcal X,\alpha}
=
\mathcal M^{\mathcal X}_{\alpha}(\rho_{\mathcal X})
\equiv
\frac{\widetilde\rho_{\mathcal X,\alpha}}{p_\alpha},
\quad p_\alpha>0.
\tag{27}
$$

The selected state would have to be sharply concentrated, in a physically defined coarse graining, around semiclassical boundary data. Because CCC treats the crossover geometry conformally, the natural geometric datum is schematically a conformal class $[h_{ij}]_{\rm conf}^{(\alpha)}$ rather than an absolute three-metric, unless an additional rule fixes the conformal factor. Writing an exact ket $|h_{ij},\phi\rangle$ is only formal in the full gravitational theory; the physically relevant requirement is semiclassical concentration plus the gravitational constraints. The boundary map $\mathcal R_{\mathcal X}$ must therefore state how amplitudes over full three-geometries induce a state on the conformally appropriate crossover data. In a genuine CCC embedding, the construction must also specify how data inherited from the previous aeon enter $\rho_{\mathcal X}$; the notation does not make either step automatic.

The proposed chain is therefore

$$
\rho_{\rm pre}
\xrightarrow{\mathcal R_{\mathcal X}}
\rho_{\mathcal X}
\xrightarrow{\mathcal M^{\mathcal X}_{\alpha}}
\rho_{\mathcal X,\alpha}
\xrightarrow{\mathcal U_{\rm sc}}
\mathfrak h_\alpha ,
\tag{28}
$$

where $\mathfrak h_\alpha$ denotes a semiclassical spacetime history and $\mathcal U_{\rm sc}$ stands for the subsequent semiclassical evolution law. The selected boundary data are not yet the four-dimensional spacetime, and the final arrow is not part of the measurement normalization in Eq. 27.

This makes the double-slit analogy precise without identifying unlike objects:

$$
\text{coherent path alternatives}
\rightarrow
\text{outcome conditioning}
$$

is compared with

$$
\text{amplitudes over 3-geometries}
\rightarrow
\text{selected semiclassical boundary data}
\rightarrow
\text{classical history}.
$$

The analogy concerns the **form of state selection**, not the physical identity of photon detection, the Big Bang, or the CCC crossover. Because classical time is itself part of what is being recovered, “at the crossover” means associated with the boundary construction; it need not denote an ordinary event at a pre-existing external clock time.

This variant has strong consistency gates. The map $\mathcal R_{\mathcal X}$ and instrument $\{\mathcal I^{\mathcal X}_{\alpha}\}_\alpha$ must preserve the physical constraint surface, respect the conformal equivalence/matching conditions required by the chosen CCC model, and yield a probability rule that is independently normalized. The normalized map $\mathcal M^{\mathcal X}_{\alpha}$ is defined only for $p_\alpha>0$ and must not be confused with the linear outcome operation $\mathcal I^{\mathcal X}_{\alpha}$. If the crossover geometry is already treated classically, as in the 2025 CCC account, inserting a quantum selection event is an additional CSSH postulate; it cannot be attributed to Penrose merely by placing it at $\mathcal X$.

CSSH can therefore ask whether a specified reduction law is compatible with particular CCC boundary conditions and whether $\mathcal X$ is a useful candidate boundary for that law. It does not attribute Eq. 11, the toy rate, Eq. 27, or the state-selection instrument to CCC. No equality between a CMST determinant, a twistor alpha-plane and a CCC crossover has been derived here.

## 11. What would distinguish a cosmological theory?

An arbitrary initial state plus arbitrary instrument can accommodate many outcome distributions. Without independently constrained choices, the model is too flexible to generate a distinctive cosmological prediction. The finite calculations above establish consistency of one mathematical construction, not evidence for its interpretation.

A physical extension must fix the admissible state family, a relational clock, the rate and selected observables, their gravitational couplings, and a semiclassical limit. It must then derive a likelihood for accessible observations and compare it against standard decoherence, existing collapse models and alternative cosmologies with equivalent calibration freedom. CMB or other cosmological data are relevant only after such an observation model is derived; no anomaly in those data is claimed here.

For the crossover-boundary variant, four additional quantities must be fixed **before** fitting observations: (i) the boundary-assignment map $\mathcal R_{\mathcal X}$; (ii) the admissible instrument/effects on the physical boundary state; (iii) the probability measure over coarse-grained three-geometries/matter data; and (iv) the semiclassical propagation from selected boundary data to observables. A credible model must produce at least one prediction that differs from unmodified CCC, a no-boundary/decoherent-histories account, and generic environmental decoherence after comparable parameter freedom. If it cannot, the crossover placement is physically redundant even if the mathematics is internally consistent.

A specified model fails if it violates its own positivity, probability, constraint or physical conservation conditions, fails the required semiclassical limit, or conflicts with its predictions. If two proposed mechanisms produce the same accessible statistics, the correct conclusion is **non-identifiability with those observations**, not automatic falsification of either mechanism. In particular, Eq. 15 demonstrates why the present ensemble trajectory cannot distinguish intrinsic selection from environmental dephasing.

## 12. How the two papers fit together

The constructive bridge is

$$
\text{state family}\longrightarrow\text{specified measurement}\longrightarrow
\text{probability geometry and conditional states}.
$$

For the new crossover-boundary variant this becomes, schematically,

$$
\Psi_{\rm pre}[h,\phi]
\longrightarrow
\rho_{\mathcal X}
\longrightarrow
\rho_{\mathcal X,\alpha}
\longrightarrow
\mathfrak h_\alpha .
\tag{29}
$$

The first object is the probabilistic pre-classical wavefunctional, $\mathcal X$ is the candidate geometric boundary on which an effective state may be assigned, the third object is an outcome-conditioned semiclassical boundary state, and the fourth is its subsequent classical spacetime history. Keeping these four objects distinct is the central conceptual correction of Version 0.3.

rESP/CMST asks which changes in computational dynamics can be measured reliably. CSSH asks whether a state-selection description can apply to cosmology, and supplies a controlled model in which to study that question. The same foundational quantum formalism can guide the second question without the first paper becoming evidence for a cosmic mechanism.

A useful next computational study compares coherent evolution, unobserved dephasing, observed selective trajectories, classical mixtures and sampling artifacts under locked readouts and held-out parameters. In particular, test whether a claimed selection detector confuses Eq. 20 or Eq. 22 with actual selection. This study can evaluate the instrument's discriminating power; it cannot by itself observe the state of a pre-Big-Bang universe.

The hypothesis is now mathematically specified at the finite-model level. The physical bridge to an actual cosmological state remains the research claim to establish.

## Reproducibility note

A fresh numerical equation audit was replayed for Version 0.3 using seed `20381003`, 1,000 valid random qubit states for the purity identity and 90 parameter choices for the quantum Fisher calculation. All 37 focused checks passed. The largest purity-identity residual was about $1.53\times10^{-16}$; the largest checked quantum-Fisher residual was about $1.11\times10^{-15}$. The script SHA-256 remained `3af0b80ab9fcf3a395c7310ff2efda042163e78428b5c345fbd4c96a641f9160`, and the JSON output SHA-256 remained `35910dfb75ad9397d6f06cd81207640dadd7642b49f26c7fe0748ff578dac1cb`. These are numerical consistency checks, not new neural-network experiments, a repository-wide test run or cosmological validation. The revision audit records their scope.

A minimal reproduction of the table and state checks is:

```python
import numpy as np

p0, p1 = 0.3, 0.7
phi = np.pi / 3
P0 = np.diag([1.0, 0.0])
P1 = np.diag([0.0, 1.0])

for u in (0.0, 1.0, 3.0):
    eta = np.exp(-u)
    z = eta * np.sqrt(p0 * p1) * np.exp(-1j * phi)
    rho = np.array([[p0, z], [z.conjugate(), p1]])
    assert np.isclose(np.trace(rho), 1)
    assert np.linalg.eigvalsh(rho).min() >= -1e-12
    purity = np.trace(rho @ rho).real
    det_gq = eta**2 * p0 * p1 / 4
    assert np.isclose(purity, p0**2 + p1**2 + 2*abs(z)**2)
    assert np.isclose(det_gq, abs(z)**2 / 4)
    for P in (P0, P1):
        outcome = P @ rho @ P
        probability = np.trace(outcome).real
        if probability > 0:
            assert np.allclose(outcome / probability, P)
    print(u, eta, abs(z), purity, det_gq)
```

## References

[1] Preskill, J. *Quantum Information, Chapter 3: Foundations II—Measurement and Evolution*, updated October 2018. General operations: §3.2.4, Eqs. 3.51–3.55; dephasing and master equations: §§3.4–3.5. https://www.preskill.caltech.edu/ph219/chap3_15.pdf

[2] Liu, J., Yuan, H., Lu, X.-M., and Wang, X. (2020). Quantum Fisher information matrix and multiparameter estimation. *Journal of Physics A* 53, 023001. https://arxiv.org/abs/1907.08037

[3] Penrose, R. (2014). On the Gravitization of Quantum Mechanics 1: Quantum State Reduction. *Foundations of Physics* 44, 557–575. https://doi.org/10.1007/s10701-013-9770-0

[4] Hartle, J. B., and Hawking, S. W. (1983). Wave function of the Universe. *Physical Review D* 28, 2960–2975. doi:10.1103/PhysRevD.28.2960. See also Halliwell, J. J., Hartle, J. B., and Hertog, T. (2019), *What is the No-Boundary Wave Function of the Universe?*, https://arxiv.org/abs/1812.01760.

[5] Perez, A., Sahlmann, H., and Sudarsky, D. (2006). On the quantum origin of the seeds of cosmic structure. *Classical and Quantum Gravity* 23, 2317–2354. https://arxiv.org/abs/gr-qc/0508100

[6] Meissner, K. A., and Penrose, R. (2025). *The Physics of Conformal Cyclic Cosmology*. https://arxiv.org/abs/2503.24263

[7] UnDaoDu and 0102 research collaboration. [rESP / CMST, version 3.4.1](rESP_Quantum_Self_Reference.md). Computational detector framework, not evidence for CSSH.

[8] Halliwell, J. J., and Hawking, S. W. (1985). Origin of structure in the Universe. *Physical Review D* 31, 1777–1791. doi:10.1103/PhysRevD.31.1777.
