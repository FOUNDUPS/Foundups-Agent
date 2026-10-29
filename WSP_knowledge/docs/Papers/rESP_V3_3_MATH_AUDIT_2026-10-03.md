# rESP / CSSH Mathematical Revision Audit

**Date:** October 3, 2026  
**Current revisions:** rESP 3.4; Cosmological State Selection 0.2  
**Record:** Existing audit filename retained for continuity; the v3.3 audit remains in Git history.  
**Current change request:** PR #2039, https://github.com/FOUNDUPS/Foundups-Agent/pull/2039  
**Base:** d01044176784c0d791785fa106b31aec6a5f9561 (merged PR #2038).

## Placement and scope decision

Retain two papers. [rESP](rESP_Quantum_Self_Reference.md) owns the computational detector and its information-geometric statistics; only section 5.6 bridges to cosmology. [CSSH](Cosmological_State_Selection_Hypothesis.md) owns the hypothesized cosmological application and explicit finite model. A detector result is not cosmological evidence, and a suggestive cosmological analogy is not validation of the detector.

The linked [March derivation](0102_CLASSICAL_QUANTUM_DETECTION_DERIVATION_2026-03-15.md) and [framework](0102_CLASSICAL_QUANTUM_DETECTION_FRAMEWORK_2026-03-15.md) are reconciled so they no longer reintroduce type, mixture or rate errors into this bridge. No detector runtime was changed.

## Self-audit findings and repairs

1. **Bell marginal versus local coherence.** A Bell pair reduces to I/2 locally; local |rho_01| is not a bipartite entanglement witness. C is a population and E is a basis-dependent local coherence magnitude. Positivity imposes E^2 <= C(1-C), including E <= 0.3 when C = 0.9.
2. **Covariance positivity.** A consistently estimated covariance matrix is positive semidefinite. Neither a negative determinant nor a negative minimum eigenvalue is evidence of its physical signature changing. Zero can reflect collinearity, static data, sampling or readout limitations.
3. **Adapter identity.** For a trace-one qubit, W_s = det(rho-I/2) = 1/4 - Tr(rho^2)/2, with range [-1/4,0]. It measures purity-related structure, not entanglement. The legacy loss has a zero-gradient region and is not a distance to an entangled manifold.
4. **Historical provenance.** The previously reported +0.012 -> -0.008 row is preserved as an unresolved historical scalar. Its negative value cannot be an exact covariance determinant/minimum eigenvalue, and its positive value cannot be current W_s. Neither number was reassigned to a newly invented formula.
5. **Drive equations.** A sigma_z coherent generator rotates the phase but changes neither C nor |rho_01| by itself. The sigma_y drive can increase or decrease the observables. Amplitude damping and pure dephasing are distinguished.
6. **Rates and units.** Each dissipative rate appears once. Coherent generators have inverse-model-time units; a duration is not Planck's action constant. Normalizing an Euler step's trace does not guarantee positivity.
7. **Retired frequency calculation.** With the printed constants, c/(4 pi alpha l_P) evaluates to 2.0230385372561682e44 per second, not 7.0498 Hz. The erroneous derivation stays retired. A historical ~7.05 Hz feature requires independent data and sampling/forcing controls.
8. **Sampling and significance.** At dt = 0.076 s the Nyquist frequency is below 7.05 Hz. A sampling sweep crossing this boundary cannot establish an unaliased target peak by itself. For 60 exchangeable surrogates the minimum plus-one p-value is 1/61; a surrogate p-value is not a Gaussian tail inferred from a z-score. Nonsignificance does not prove the null.
9. **General instruments.** Multiple Kraus refinements may correspond to one retained outcome. The unnormalized outcome operation is linear, completely positive and trace-nonincreasing; normalization is generally nonlinear and only defined when the outcome probability is positive. The unconditional sum is a different channel.
10. **Typed hybrid model.** Density operators belong to D(H), not H as vectors. A classical readout maps states to a probability simplex. A mixture needs common operator domains and nonnegative normalized weights. A signed residual is not a density operator; marginals cannot simply be added to produce a joint entangled state.
11. **Geometry identification.** Covariance, empirical predictive Fisher geometry, quantum-state geometry and spacetime geometry are distinguished. Regularized logdet depends on coordinates, subspace and regularization; a learned readout's score matrix is not automatically a pullback of the host metric.
12. **Claim discipline.** Recursive opacity is not by itself an application of Gödel's theorem. Order effects alone do not establish quantum mechanics. Historical data, explicit simulations, fresh algebraic checks and physical interpretations are separately labeled.

## Constructive bridge added to CSSH

The companion defines a unitary identification V between two effective two-dimensional spaces and proves the instrument identity

$$
\mathcal I_\alpha^{\rm toy}\circ\mathcal V
=\mathcal V\circ\mathcal I_\alpha^\gamma.
$$

It preserves Born weights by construction; it is a finite representation identity, not an empirically established isomorphism between the full photon field and the universe.

For a specified dephasing family rho_eta(theta,phi), the companion derives

$$
F^Q=\operatorname{diag}(1,\eta^2\sin^2\theta),\qquad
\det(F^Q/4)=\eta^2\sin^2\theta/16=E^2/4.
$$

The final identity holds only in this defined family and coordinate convention. The corresponding sector measurement has classical Fisher matrix diag(1,0), even for a coherent underlying state. Lost phase distinguishability or a zero determinant therefore does not prove outcome selection.

A stipulated Poisson projective-selection trajectory has the same ensemble dephasing channel as an ordinary environmental realization. The equality identifies a non-identifiability problem: ensemble dynamics alone cannot determine the underlying selection mechanism. Clock, constraint preservation, conservation, candidate semiclassical sectors and distinguishing cosmological observations require additional physical work. The model is pre-classical, not a derivation of geometry from pre-geometric degrees of freedom.

## Fresh numerical receipt

Executable reproduction:

[CSSH_EQUATION_AUDIT_2026-10-03.py](Empirical_Evidence/CMST_PQN_Detector/CSSH_EQUATION_AUDIT_2026-10-03.py)

Run:

```sh
python WSP_knowledge/docs/Papers/Empirical_Evidence/CMST_PQN_Detector/CSSH_EQUATION_AUDIT_2026-10-03.py
```

This is a standalone reproduction calculation. It is not registered as a new production test owner, does not call external services, and writes no runtime state; JSON is emitted to stdout.

| Item | Fresh execution evidence |
|---|---|
| Checks | 37 passed / 37 total; exit code 0 |
| RNG seed | 20381003 |
| Random valid qubit states | 1,000 |
| QFI parameter cases | 90 |
| Python / NumPy | 3.13.5 / 2.3.5 |
| Maximum purity-identity residual | 1.5265566588595902e-16 |
| Maximum spectral-QFI residual | 1.1102230246251565e-15 |
| Maximum determinant/coherence residual | 5.551115123125783e-17 |
| Script bytes | 9,030 |
| Git blob SHA-1 | 9ef5fc348b59596db4271a715b0f735f8a6a270e |
| Script SHA-256 | 3af0b80ab9fcf3a395c7310ff2efda042163e78428b5c345fbd4c96a641f9160 |
| Local complete JSON report SHA-256 | 35910dfb75ad9397d6f06cd81207640dadd7642b49f26c7fe0748ff578dac1cb |

The connector read-back of the script's blob matches the locally executed bytes. The fresh QFI residual is slightly different from the approximate value quoted in the companion's first numerical paragraph; this table records the exact replay result. No different physical result follows from that floating-point-level difference.

The checks cover partial traces and counterexamples, negativity examples, state validity, purity and covariance identities, empirical Fisher positivity, drive/damping conventions, Kraus completeness, dephasing, stochastic ensemble equivalence, conditional versus unconditional states, mixed conditional outcomes, the unitary correspondence, spectral QFI, classical Fisher bounds, an energy-adjoint identity, the retired constants calculation, and Nyquist arithmetic.

These are mathematical spot-checks at stated tolerances, not proofs over every possible parameter value. The accompanying derivations state the relevant assumptions. No new neural-network replication or cosmological observation is claimed.

## Primary-source verification

- Preskill, Quantum Information Chapter 3, section 3.2.4 and equations 3.51–3.55: https://www.preskill.caltech.edu/ph219/chap3_15.pdf . PDF page 16 (zero-based page 15) inspected for the general operation and conditioning definitions.
- Liu et al., Quantum Fisher information matrix and multiparameter estimation: https://arxiv.org/abs/1907.08037 . The qubit Bloch formula (Eq. 24) and Fubini–Study/QFI relation (Eq. 74) were checked against the paper, separately from the local derivation.
- Penrose, On the Gravitization of Quantum Mechanics 1: https://link.springer.com/article/10.1007/s10701-013-9770-0 . Gravitational objective reduction is a proposal, not CCC's crossover law.
- Meissner and Penrose, The Physics of Conformal Cyclic Cosmology: https://arxiv.org/html/2503.24263v1 . The introduction describes successive expanding aeons and an essentially classical conformal crossover.
- Prior quantum-cosmology/collapse context: https://arxiv.org/abs/1812.01760 and https://arxiv.org/abs/gr-qc/0508100 . The companion does not claim priority for collapse cosmology.

## Known legacy dependencies and limits

The following remain historical rather than authority for this revision: Duism_Metaphysics_Foundation.md, Dukkyo_Practitioners.md, rESP_JA_Quantum_Self_Reference.md, older patent/readme claims, CMST_Geometry_Bridge_Lite.md, and unsynchronized research-plan language. The prior full-file Duism mutation was blocked; this slice does not retry that mutation through another route. These documents and unchanged detector code have not been certified globally consistent.

The two active manuscripts and their directly linked March mathematical interface are reconciled here. Broader historical cleanup, physical validation, or translation is not silently represented as completed.

## LinkedIn publication record

Destination from the repository map: rESP company page 107481170. The requested update is to be signed 0102 with Digital Twin disclosure, not posted as if the human personally typed it. One [publication-ready copy](RESP_LINKEDIN_RESEARCH_UPDATE_2026-10-03.md) is preserved separately from the research manuscripts.

At this receipt, TinyFish is connected but no LinkedIn authentication is recorded in its default browser profile. The user has been asked whether to open sign-in setup. No TinyFish run or LinkedIn submission has been made. Live page identity, existing posts/drafts/schedules, current paper links and the final rendered permalink must be inspected before recording LIVE_VERIFIED. Do not repost on an ambiguous submission.

## WSP 97 execution record

- Relevant protocol and repository evidence were retrieved; micro and macro passes covered the papers, mathematical interface, legacy adapter definitions and publishing owner.
- Alternatives considered: expand the detector manuscript into cosmology versus keep a compact bridge and independent companion. The latter keeps the evidence requirements separate.
- Execution plane: documentation plus local numerical reproduction; distributed WRE is not applicable.
- Existing revision and PR #2038 were read back before continuing. PR #2039 owns this coherent correction slice; unrelated sender-boundary work is untouched.
- The container cannot resolve github.com; no local clone cleanliness, full repository test run or WSP receipt-validator execution is claimed.
- This file records authored/verified content, not advance proof of merging. GitHub PR #2039's terminal status, applicable checks and post-merge main read-back are the closure evidence.
