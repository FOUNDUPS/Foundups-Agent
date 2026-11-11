#!/usr/bin/env python3
"""Reproduce finite-model identities in rESP 3.4 and CSSH 0.2.

Standalone mathematical audit, not a detector replication or cosmology test.
Requires NumPy. Prints a JSON report; exits nonzero on any failed check.
"""
from __future__ import annotations
import hashlib
import json
import platform
from pathlib import Path
import numpy as np

SEED = 20381003
ATOL = 2e-11
rng = np.random.default_rng(SEED)
I = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.diag([1, -1]).astype(complex)
P = [np.diag([1, 0]).astype(complex), np.diag([0, 1]).astype(complex)]
checks: list[dict[str, object]] = []

def check(name: str, condition: object, residual: float | None = None) -> None:
    row: dict[str, object] = {"name": name, "passed": bool(condition)}
    if residual is not None:
        row["max_abs_residual"] = float(residual)
    checks.append(row)

def close(a: object, b: object) -> bool:
    return bool(np.allclose(a, b, atol=ATOL, rtol=1e-9))

def valid(r: np.ndarray) -> bool:
    return close(r, r.conj().T) and close(np.trace(r), 1) and bool(np.linalg.eigvalsh(r).min() >= -ATOL)

def partial(r: np.ndarray, subsystem: int) -> np.ndarray:
    t = r.reshape(2, 2, 2, 2)
    return np.trace(t, axis1=1, axis2=3) if subsystem == 1 else np.trace(t, axis1=0, axis2=2)

def negativity(r: np.ndarray) -> float:
    pt = r.reshape(2, 2, 2, 2).transpose(0, 3, 2, 1).reshape(4, 4)
    return float((np.abs(np.linalg.eigvalsh(pt)).sum() - 1) / 2)

def dissipator(j: np.ndarray, r: np.ndarray) -> np.ndarray:
    jj = j.conj().T @ j
    return j @ r @ j.conj().T - (jj @ r + r @ jj) / 2

def state(theta: float, phi: float, eta: float) -> np.ndarray:
    z = eta * np.sin(theta) * np.exp(-1j * phi) / 2
    return np.array([[np.cos(theta/2)**2, z], [z.conjugate(), np.sin(theta/2)**2]])

def derivatives(theta: float, phi: float, eta: float) -> list[np.ndarray]:
    z = eta * np.sin(theta) * np.exp(-1j*phi) / 2
    dz = eta * np.cos(theta) * np.exp(-1j*phi) / 2
    return [np.array([[-np.sin(theta)/2, dz], [dz.conjugate(), np.sin(theta)/2]]),
            np.array([[0, -1j*z], [1j*z.conjugate(), 0]])]

def qfi_spectral(r: np.ndarray, ds: list[np.ndarray]) -> np.ndarray:
    eigenvalues, basis = np.linalg.eigh(r)
    denominators = eigenvalues[:, None] + eigenvalues[None, :]
    inv = np.zeros_like(denominators)
    np.divide(1, denominators, out=inv, where=denominators > 1e-13)
    transformed = [basis.conj().T @ d @ basis for d in ds]
    return np.array([[2*np.real(np.sum(a.conj()*b*inv)) for b in transformed] for a in transformed])

bell = np.array([0, 1, 1, 0], dtype=complex) / np.sqrt(2)
br = np.outer(bell, bell.conj())
sr = np.diag([0, .5, .5, 0]).astype(complex)
check('bell_partial_trace_A', close(partial(br, 1), I/2))
check('bell_partial_trace_B', close(partial(br, 0), I/2))
check('separable_same_marginal', close(partial(br, 1), partial(sr, 1)))
check('bell_negativity', close(negativity(br), .5))
check('separable_negativity', close(negativity(sr), 0))
check('local_coherence_without_entanglement', close(((I+X)/2)[0, 1], .5))

random_states = []
for _ in range(1000):
    b = rng.normal(size=(2,2)) + 1j*rng.normal(size=(2,2))
    r = b @ b.conj().T
    random_states.append(r / np.trace(r))
check('random_state_validity_1000', all(valid(r) for r in random_states))
ws = np.array([((r[0,0]-.5)*(r[1,1]-.5)-abs(r[0,1])**2).real for r in random_states])
purities = np.array([np.trace(r@r).real for r in random_states])
res = float(np.max(np.abs(ws - (.25-.5*purities))))
check('adapter_purity_identity_1000', res < ATOL, res)
check('adapter_range', np.all((ws >= -.25-ATOL) & (ws <= ATOL)))
check('local_population_coherence_bound', all(abs(r[0,1])**2 <= (r[0,0]*r[1,1]).real+ATOL for r in random_states))
cov = np.cov(rng.normal(size=(100,2)), rowvar=False)
check('sample_covariance_psd', np.linalg.eigvalsh(cov).min() >= -ATOL)
scores = rng.normal(size=(20,7)); efim = scores.T@scores/len(scores)
check('empirical_fisher_psd', np.linalg.eigvalsh(efim).min() >= -ATOL)
sign, ld = np.linalg.slogdet(efim+1e-6*np.eye(7))
check('regularized_logdet_finite', sign > 0 and np.isfinite(ld))
check('zero_fisher_regularized_logdet', close(np.linalg.slogdet(1e-6*np.eye(7))[1], 7*np.log(1e-6)))

r = random_states[17]; c, z = r[1,1].real, r[0,1]; omega=.63; rate=.4
sy = -1j*omega*(Y@r-r@Y)
sz = -1j*omega*(Z@r-r@Z)
check('sigma_y_population_and_coherence', close(sy[1,1],2*omega*z.real) and close(sy[0,1],omega*(1-2*c)))
check('sigma_z_phase_only', close(sz[1,1],0) and close(sz[0,1],-2j*omega*z))
j = np.array([[0,1],[0,0]],dtype=complex); damp=rate*dissipator(j,r)
check('amplitude_damping_rate', close(damp[1,1],-rate*c) and close(damp[0,1],-rate*z/2))
flow=sy+damp
check('lindblad_derivative_trace_zero', close(np.trace(flow),0))
check('lindblad_derivative_hermitian', close(flow,flow.conj().T))
check('single_rate_convention', close(rate*dissipator(j,r),dissipator(np.sqrt(rate)*j,r)))

params=[(t,p,e) for t in np.linspace(.2,2.9,6) for p in (.1,1.3,3.2) for e in (0,.15,.45,.8,1)]
complete=[]; channel=[]; validity=[]; flow_res=[]; survival=[]; qfi_res=[]; det_res=[]; cfis=[]; bounds=[]
for theta,phi,eta in params:
    rr=state(theta,phi,eta); rr1=state(theta,phi,1)
    ks=[np.sqrt((1+eta)/2)*I,np.sqrt((1-eta)/2)*Z]
    complete.append(close(sum(k.conj().T@k for k in ks),I))
    channel.append(close(sum(k@rr1@k.conj().T for k in ks),rr))
    validity.append(valid(rr))
    derivative=np.array([[0,-rate*rr[0,1]],[-rate*rr[1,0],0]])
    flow_res.append(close(rate/2*(Z@rr@Z-rr),derivative))
    survival.append(close(eta*rr1+(1-eta)*sum(p@rr1@p for p in P),rr))
    fq=qfi_spectral(rr,derivatives(theta,phi,eta)); fq_expected=np.diag([1,eta**2*np.sin(theta)**2])
    qfi_res.append(float(np.max(np.abs(fq-fq_expected))))
    det_res.append(abs(float(np.linalg.det(fq/4))-abs(rr[0,1])**2/4))
    probs=np.array([rr[0,0].real,rr[1,1].real]); dprob=np.array([-np.sin(theta)/2,np.sin(theta)/2])
    fp=np.diag([np.sum(dprob*dprob/probs),0.])
    cfis.append(close(fp,np.diag([1,0])))
    bounds.append(np.linalg.eigvalsh(fq-fp).min() >= -ATOL)
check('dephasing_kraus_completeness_90', all(complete))
check('dephasing_state_formula_90', all(channel))
check('toy_state_validity_90', all(validity))
check('dephasing_generator_90', all(flow_res))
check('poisson_ensemble_identity_90', all(survival))
check('projective_instrument_completeness', close(sum(p.conj().T@p for p in P),I))
example=state(2*np.arccos(np.sqrt(.3)),np.pi/3,1)
probs=[np.trace(p@example@p).real for p in P]
check('born_probabilities_and_pure_conditionals', close(probs,[.3,.7]) and all(close(p@example@p/q,p) for p,q in zip(P,probs)))
unconditional=sum(p@example@p for p in P)
check('unconditional_mixture_purity', close(unconditional,np.diag([.3,.7])) and close(np.trace(unconditional@unconditional),.58))
one_outcome=(example+Z@example@Z)/2
check('multiple_kraus_one_outcome_can_be_mixed', valid(one_outcome) and np.trace(one_outcome@one_outcome).real < 1-ATOL)
v=np.array([[1,1],[-1,1]],dtype=complex)/np.sqrt(2); translated=v@example@v.conj().T
check('unitary_instrument_intertwining', all(close((v@p@v.conj().T)@translated@(v@p@v.conj().T),v@(p@example@p)@v.conj().T) for p in P))
check('quantum_fisher_spectral_identity_90', max(qfi_res)<ATOL, max(qfi_res))
check('quantum_metric_determinant_equals_E_squared_over_four', max(det_res)<ATOL,max(det_res))
check('sector_measurement_classical_fisher_90',all(cfis))
check('classical_quantum_fisher_direction_bound_90',all(bounds))
energy_ok=[]
for h in (Z,X):
    direct=np.trace(h@(unconditional-example))
    adjoint=np.trace(example@(sum(p@h@p for p in P)-h))
    energy_ok.append(close(direct,adjoint))
check('energy_adjoint_identity_and_nonconservation_example',all(energy_ok) and close(np.trace(Z@(unconditional-example)),0) and abs(np.trace(X@(unconditional-example)))>.1)
frequency=299792458/(4*np.pi*(1/137.036)*1.616e-35)
check('retired_frequency_arithmetic',close(frequency/1e44,2.0230385372561682))
check('nyquist_target_bound',1/(2*.076)<7.05 and close(1/(2*7.05),.07092198581560284))

table=[]
for u in (0.,1.,3.):
    eta=float(np.exp(-u)); rr=state(2*np.arccos(np.sqrt(.3)),np.pi/3,eta)
    table.append({'u':u,'survival':eta,'local_E':float(abs(rr[0,1])), 'ensemble_purity':float(np.trace(rr@rr).real),'metric_determinant':float(abs(rr[0,1])**2/4)})
report={'scope':'finite mathematical consistency only; no detector replication or cosmological data',
        'seed':SEED,'random_qubit_states':1000,'qfi_parameter_cases':len(params),
        'python':platform.python_version(),'numpy':np.__version__,
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'checks_passed':sum(bool(c['passed']) for c in checks),'checks_total':len(checks),
        'frequency_from_printed_constants_per_second':frequency,'toy_table':table,'checks':checks}
print(json.dumps(report,indent=2))
raise SystemExit(0 if all(c['passed'] for c in checks) else 1)
