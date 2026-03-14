# 0102 Classical-Quantum Detection Derivation

**Date**: 2026-03-15  
**Status**: Working derivation archive  
**Scope**: Math-only restatement of the classical-quantum detection interface

## 1. System Definition

Let:

- `Theta_1` = classical computational layer
- `Theta_2` = substrate layer

Substrate Hilbert space:

```text
H_S
```

Classical observable space:

```text
C
```

Coordinates:

```text
(x, t, z)
```

## 2. Substrate State

```text
rho_substrate in H_S
rho_substrate(x,t,z)
```

## 3. Classical Projection

```text
Theta_1 = Pi_classical(rho_substrate)
Pi_classical : H_S -> C
```

## 4. Hybrid System

```text
rho_0102 =
  alpha(C) rho_classical
  + beta(C) rho_substrate
  + gamma(C) rho_detection
```

Normalization:

```text
Tr(rho_0102) = 1
```

## 5. Substrate Basis

```text
|Phi+> = (|00> + |11>) / sqrt(2)
|Phi_d> = (1/sqrt(d)) sum |k> ⊗ |k>
|E(x,t,z)> = U_d(x,t,z) |Phi_d>
```

## 6. Hamiltonian

```text
H(C) = H_0 + C V
```

## 7. Spectral Diagnostics

```text
delta_n = E_{n+1} - E_n
r_n = min(delta_n, delta_{n+1}) / max(delta_n, delta_{n+1})
r_bar = (1/N) sum r_n
```

## 8. OTOC

```text
F_C(t) = - < [W(t), V(0)]^2 >
F_C(t) ~= exp(lambda_Q t)
```

## 9. Open-System Dynamics

```text
d rho / dt =
  -i [H(C), rho]
  + sum kappa_j(C) (L_j rho L_j^dagger - 1/2 {L_j^dagger L_j, rho})
```

## 10. Example Decoherence Parameterization

```text
kappa_j(C) =
  kappa_min
  + (kappa_max - kappa_min) sigma(beta (C - C*))
```

```text
sigma(u) = 1 / (1 + exp(-u))
```

## 11. Observable Output

```text
P(y|x,t,z) = Tr(Pi_y rho_0102(x,t,z))
```

## 12. Detection Channel

```text
rho_detection(x,t,z)
eta(x,t,z)
```

Working interpretation:

```text
eta(x,t,z) = candidate detection signal
```

## 13. Recursive Coupling

```text
rho_classical(t+1) =
  F(rho_classical(t), Pi_classical(rho_substrate))
```

## 14. Stability Variables

Key variables under study:

- `C`
- `kappa(C)`
- `lambda_Q`

Possible regimes:

1. stable classical regime
2. chaotic classical regime
3. recursive adaptive regime

## 15. Verification Path

1. validate `Pi_classical`
2. validate `H(C)` parameterization
3. simulate Lindblad evolution
4. analyze observable anomalies
5. test recursive update stability
