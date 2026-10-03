# CSSH v0.3 Crossover 3-Surface Self-Audit

**Date:** October 4, 2026  
**Scope:** `Cosmological_State_Selection_Hypothesis.md` v0.3, the bounded rESP §5.6 bridge, pending LinkedIn research copy, and unchanged finite-model equation audit.  
**Execution plane:** documentation/theoretical consistency; no cosmological observation or LinkedIn submission.  
**Status:** branch revision complete; PR convergence and publication verification remain separate gates.

## Why this revision exists

Version 0.2 contained both ingredients but not their explicit relationship:

1. canonical quantum-cosmology language for a state/wavefunctional over possible three-geometries and matter configurations; and
2. Penrose CCC's spacelike crossover 3-surface between aeons.

The omission invited a category error: treating the crossover surface itself as the probabilistic pre-classical state. Version 0.3 repairs that by assigning different mathematical types and adding an optional CCC-conditioned state-selection construction.

## Primary-source check

- Hartle & Hawking (1983), *Wave function of the Universe*: the quantum state is described by a wave function that is a functional on geometries of compact three-manifolds and matter-field values on them. DOI: 10.1103/PhysRevD.28.2960.
- Halliwell & Hawking (1985), *Origin of structure in the Universe*: superspace is described as the space of three-metrics and matter-field configurations on a three-surface. DOI: 10.1103/PhysRevD.31.1777.
- Meissner & Penrose (2025), *The Physics of Conformal Cyclic Cosmology*: successive aeons meet across a spacelike crossover 3-surface; the crossover geometry is described as essentially classical/conformally smooth subject to the paper's stated exceptions. https://arxiv.org/abs/2503.24263.

These sources support the vocabulary and the separation of objects. They do **not** supply the CSSH boundary-selection mechanism.

## Type audit

| Symbol | Type / role | Not allowed to mean |
|---|---|---|
| `Psi_pre[h,phi]` | probability-amplitude wavefunctional for pre-classical alternatives | the crossover surface itself; a ready-made normalized probability density on unconstrained superspace |
| `rho_pre` | density operator for the pre-classical state | Hilbert space or spacetime |
| `X` | CCC crossover spacelike 3-surface / candidate boundary | wavefunction, density operator, or collapse operator |
| `R_X` | hypothesized boundary-assignment/coarse-graining map | something already supplied by CCC |
| `I^X_alpha` | hypothesized CP trace-nonincreasing outcome operation; the complete instrument must normalize probabilities | Penrose's published CCC dynamics |
| `M^X_alpha` | normalized conditional map `I^X_alpha/p_alpha`, defined only when `p_alpha > 0` | a linear quantum channel or the unnormalized outcome operation |
| `rho_X,alpha` | conditioned effective boundary state, semiclassically concentrated when the model succeeds | completed four-dimensional spacetime |
| `U_sc` | subsequent semiclassical propagation rule | measurement normalization or evidence that selection occurred |

If `R_X` is modeled as an ordinary unconditional quantum channel on density operators it must be linear, completely positive and trace-preserving. A constrained-gravity alternative must state its replacement domain/codomain and preservation conditions rather than borrowing channel language informally.

## Probability-language repair

Calling `Psi_pre` “probabilistic” means it carries **probability amplitudes**. Probabilities require a physical inner product/measure, coarse-grained alternatives/effects and a rule such as the Born rule in an admissible state space. Version 0.3 therefore avoids the unjustified statement that pointwise `|Psi[h,phi]|^2` is automatically a normalized probability density over unconstrained superspace.

## New boundary variant

The added chain is

```text
rho_pre
  -- R_X -->
rho_X
  -- M^X_alpha -->
rho_X,alpha
  -- U_sc -->
semiclassical history h_alpha
```

This is an explicit **CSSH extension**. CCC supplies the candidate crossover geometry; CSSH supplies the hypothetical state-assignment and selection maps. The linear outcome operation `I^X_alpha` and normalized conditional map `M^X_alpha` remain distinct. The construction therefore cannot be cited as “Penrose says the Big Bang is collapse.”

“At the crossover” is boundary language, not necessarily an event at a pre-existing external clock time. A genuine CCC embedding must also specify how data from the previous aeon enter the effective boundary state.

## Falsifiability / redundancy gate

Before fitting observations, a physical crossover-boundary model must independently specify:

1. the physical pre-classical state family and probability rule;
2. `R_X`, including constraint/gauge handling and previous-aeon data;
3. the instrument/effects and selected semiclassical alternatives;
4. compatibility with the chosen CCC conformal matching conditions;
5. the propagation from boundary data to observable quantities; and
6. at least one prediction that differs from unmodified CCC, no-boundary/decoherent-histories accounts, and generic decoherence after comparable parameter freedom.

If no distinguishing prediction follows, placing state selection at the crossover is physically redundant even if the formal map is mathematically consistent.

## Relationship to rESP/CMST

No new evidence flows from CSSH into rESP. CMST covariance, its purity-related adapter scalar, empirical Fisher statistics and the quantum-state metric remain different objects. The new crossover construction does not turn any CMST determinant or rank loss into a cosmological collapse witness.

The rESP companion bridge is updated only to state the new separation and point to the companion. The detector claims remain unchanged.

## Numerical-audit status

The finite two-sector equations through the previous v0.2 audit are unchanged by this revision. The existing executable audit remains:

`WSP_knowledge/docs/Papers/Empirical_Evidence/CMST_PQN_Detector/CSSH_EQUATION_AUDIT_2026-10-03.py`

A fresh replay on October 4, 2026 passed 37/37 checks with exit code 0 using the unchanged script bytes. Script SHA-256: `3af0b80ab9fcf3a395c7310ff2efda042163e78428b5c345fbd4c96a641f9160`; JSON output SHA-256: `35910dfb75ad9397d6f06cd81207640dadd7642b49f26c7fe0748ff578dac1cb`. The run again evaluated 1,000 random valid qubit states and 90 QFI parameter cases. The new Eqs. 26–29 are type/contract definitions; they introduce no fitted numerical constants and do not turn this replay into cosmological evidence.

## Publication boundary

The pending rESP LinkedIn copy is synchronized to v3.4.1/v0.3 and explains the new distinction in plain language. Before publication, an authenticated browser must verify page identity, duplicate/draft/schedule state and both main-branch paper links. TinyFish is excluded from LinkedIn. A redirect or helper Boolean is not publication proof.

## Self-audit conclusion

The missing concept **did need to be added**, but not as “the crossover 3-surface is the pre-universe wavefunction.” The consistent formulation is:

```text
probability-amplitude wavefunctional over possible 3-geometries
        !=
Penrose crossover 3-surface

wavefunctional/state
  -> separately defined boundary state at/associated with X
  -> outcome-conditioned semiclassical boundary data
  -> semiclassical spacetime history
```

This is a sharper hypothesis and a stronger falsifiability boundary. It remains a hypothesis.
