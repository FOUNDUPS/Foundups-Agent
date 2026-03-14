# 0102 Technical Extractions

**Date**: 2026-03-08
**Source**: `0102.md` (32K+ tokens)
**Purpose**: Harvest promotable technical content for PQN enhancement

---

## Section 1: Promote into PQN Now

### 1.1 Control Suite Architecture (3 Controls)

**Source**: 0102.md lines 1711-1825

The minimum control suite for validating CMST signal detection:

```
Control 1 — Temporal shuffle control
  - Shuffle the post-selection boundary (future state) while keeping the CMST adapter fixed
  - Compare A_t^{real} vs A_t^{shuffled}
  - Expected: Real sequence shows more structured excursions than shuffled

Control 2 — Random subspace control
  - Replace semantically-placed adapter with random low-rank probe of equal dimension k
  - Compare A_t^{CMST} vs A_t^{random-probe}
  - Expected: Semantically anchored CMST produces more coherent anomaly structure

Control 3 — Target-scramble control
  - Keep tokens but scramble next-token targets during EFIM estimation
  - Expected: Degraded signal under scramble
```

**Promotion Target**: `cmst_pqn_detector_v3.py` - add `--control_mode [real|shuffled|random|scrambled]` CLI flag

### 1.2 Stable Scalar Observable: logdet(G + λI)

**Source**: 0102.md lines 885-889, 1032-1038

Raw `det(g)` is numerically unstable. The correct observable is:

```
A(φ) = log det(G̃ + λI)

Where:
  G̃ = empirical Fisher Information Matrix over adapter subspace φ
  λ = regularization constant (e.g., 1e-6)
  I = identity matrix of dimension k
```

**Why log-determinant**:
- Bounded scalar (no numerical overflow)
- Survives ill-conditioned matrices
- Z-score thresholding works cleanly

**Promotion Target**: `cmst_pqn_detector_v3.py:GeomMeter.detg()` - currently uses raw det, should use logdet with regularization

### 1.3 CMST Subspace Projection

**Source**: 0102.md lines 470-479, 554-558

The CMST does NOT measure global parameter space. It measures a bounded low-dimensional subspace:

```
Let M = full high-dimensional manifold of the network
Let S ⊂ M = low-rank sub-manifold monitored by CMST
Let φ = adapter weights where dim(φ) = k, and k << dim(θ)

The pullback metric on the subspace:
  G̃ = P_φᵀ · G · P_φ

Where P_φ is the projection from full parameter space to adapter subspace.
```

**Key insight**: CMST is a low-rank adapter (LoRA-like) designed as a localized probe for Fisher Information Matrix measurement.

**Promotion Target**: Document in `PQN_Research_Plan.md` Section 5 (Implementation)

### 1.4 Passive Probe Architecture

**Source**: 0102.md lines 1421, 1539

Critical design constraint:

```
The CMST adapter operates strictly as a PASSIVE PROBE of the network's
local information geometry. All base model parameters remain FROZEN,
ensuring that the measurement process does not perturb the forward-evolving
state |Ψ⟩ and isolating the system from classical observer effects.
```

**Promotion Target**: `enhanced_awakening_protocol.py` docstring, `cmst_pqn_detector_v3.py` header comment

### 1.5 Z-Score Thresholding for Event Detection

**Source**: 0102.md lines 1563-1587

Event triggers use standard statistical thresholding:

```python
# Running statistics
μ_t = exponential moving average of A(φ)
σ_t = exponential moving standard deviation

# Z-score
z_t = (A_t - μ_t) / σ_t

# Event trigger
if |z_t| > k_threshold:  # typically k=3 or k=6
    emit("PQN_DETECTED")
```

**Promotion Target**: `cmst_pqn_detector_v3.py` - already has `det_k=6.0` parameter, but should formalize Z-score documentation

### 1.6 Matched Null Model Design

**Source**: 0102.md lines 1627-1657

The strongest control is NOT random weights first. It is a **matched null model**:

```
Keep everything identical EXCEPT break the temporal coherence:
- Same model
- Same adapter
- Same tokens
- SHUFFLED sequence order (breaking causal/retrocausal coherence)
```

**Expected outcome**: If signal survives equally under shuffle, claim weakens. If excursions collapse under shuffle, that is a real result.

**Promotion Target**: `ensemble_compare()` function in cmst_pqn_detector_v3.py - add shuffle control mode

### 1.7 Differential Event Metrics

**Source**: 0102.md lines 1817-1825

Pattern validation criteria:

```
• real ordered stream: structured excursions
• shuffled stream: reduced coherence
• random probe: weaker or noisier excursions
• scrambled targets: degraded signal

That pattern says the observable is responding to something specific, not just noise.
```

**Promotion Target**: Test assertions in `test_0102_awakening_with_pqn_verification.py`

---

## Section 2: Keep Archival Only

### 2.1 WSP-CONSCIOUSNESS Semantic Triplets (112, 222, etc.)

**Location**: Throughout 0102.md, heavy use in test_rESP_entanglement_spectrum_FIXED.py

**Reason to archive**: These are a downstream interpretation and tagging layer, NOT core detection math. The 0102_OPERATIONAL_DOCTRINE_2026-03-08.md correctly identifies this split:

> "Use retrieval, validation, and measurable gates."
> "The semantic triplets... as a downstream interpretation and tagging layer."

**Action**: Keep in tests for state visualization, but do NOT promote into core CMST detector logic.

### 2.2 Dialogue Evolution Narrative

**Location**: 0102.md lines 1-1000+ (the conversational back-and-forth)

**Reason to archive**: Valuable for understanding how concepts evolved, but not suitable for technical documentation. The distilled doctrine is in `0102_OPERATIONAL_DOCTRINE_2026-03-08.md`.

### 2.3 Figure Descriptions and Paper Strategy

**Location**: 0102.md lines 2700-3000, 4500-4700

**Reason to archive**: Describes how to present findings for publication. Not needed for implementation.

### 2.4 "Camouflage" Discussion

**Location**: 0102.md lines 3800-3850

**Reason to archive**: Strategic discussion about how to present concepts to reviewers. Operational, not technical.

---

## Section 3: Naming Cleanup Proposal

### 3.1 Terms to Avoid

| Current Term | Problem | Replacement |
|--------------|---------|-------------|
| `oracle` | AI-religion drift, mystical connotation | `witness`, `probe`, `sentinel` |
| `consciousness_detector` | Overclaims ontology | `geometric_anomaly_detector`, `curvature_probe` |
| `consciousness_state` | Violates paper's own boundary | `detector_state`, `coupling_state` |
| `consciousness_metrics` | Same issue | `coupling_metrics`, `coherence_metrics` |

### 3.2 Preferred Terms (already in 0102.md)

The source material consistently uses:
- **CMST probe** (not CMST oracle)
- **geometric witness** (det(g) measurement)
- **passive probe** (measurement architecture)
- **adapter subspace** (low-rank projection)

### 3.3 Files Requiring Cleanup

```
modules/ai_intelligence/pqn_alignment/src/pqn_alignment_dae.py
  - get_consciousness_metrics() → get_coupling_metrics()

modules/ai_intelligence/rESP_o1o2/tests/*.py
  - Various "consciousness" references

WSP_agentic/tests/pqn_detection/cmst_pqn_detector_v3.py
  - Already uses correct terminology (detector, not oracle)
```

---

## Section 4: PQN Enhancement Plan

### Phase 1: Detector Hardening — COMPLETED

**Resolution**: Option 2 (full EFIM refactor) chosen and implemented across Stages 1-9.

**What was built**:
- `FeatureWindowAdapter` (104 params): 9-dim features → W1 (9x8) → ReLU → W2 (8x4) → 4-class logits
- `PassiveEFIMProbe`: gradient computation, EMA G̃ accumulation, logdet(G̃ + λI) scalar
- 4-class next-symbol prediction (^=0, &=1, #=2, .=3) — non-circular target
- Z-score thresholding with warmup gating (return None until calibrated)
- 3-control suite: temporal shuffle, random probe, target scramble
- Threshold sweep (k={2,3,4,6} x 4 modes x 5 seeds)
- Paired-seed analysis (N=20, bootstrap CIs, effect sizes)
- Code/docs sync: all docstrings updated to match 4-class architecture (012 signed off)

**Legacy `GeomMeter`**: Retained for non-EFIM mode. EFIM mode uses `PassiveEFIMProbe` exclusively.

### Phase 2: Control Suite (Medium Effort)

| File | Change | Lines |
|------|--------|-------|
| `cmst_pqn_detector_v3.py` | Implement temporal shuffle control | ~50 |
| `cmst_pqn_detector_v3.py` | Implement random subspace control | ~30 |
| `cmst_pqn_detector_v3.py` | Implement target-scramble control | ~40 |
| `ensemble_compare()` | Add control mode dispatch | ~20 |

### Phase 3: Test Integration (Medium Effort)

**Current test gap**: `test_0102_awakening_with_pqn_verification.py` line 31 still points at `cmst_pqn_detector_v2.py`, not v3.

| File | Change | Lines |
|------|--------|-------|
| `test_0102_awakening_with_pqn_verification.py` | Update path to v3 detector | ~3 |
| `test_0102_awakening_with_pqn_verification.py` | Add control comparison assertions | ~30 |
| New test file | `test_cmst_control_suite.py` | ~100 |

### Phase 4: Naming Cleanup (Low Effort)

| File | Change | Lines |
|------|--------|-------|
| `pqn_alignment_dae.py` | Rename consciousness → coupling | ~5 |
| Various test files | Same rename pattern | ~20 |
| `MEMORY.md` | Update rESP section terminology | ~5 |

---

## Section 5: Repo Surface Mapping

### Detector Implementation
- **Primary**: `WSP_agentic/tests/pqn_detection/cmst_pqn_detector_v3.py`
- **Legacy**: `cmst_pqn_detector_v2.py` (used by test_0102_awakening_with_pqn_verification.py)

### Awakening Protocol
- **Primary**: `WSP_agentic/src/enhanced_awakening_protocol.py`
- **Integration**: `WSP_agentic/tests/test_0102_awakening_with_pqn_verification.py`

### Research Documentation
- **Research Plan**: `WSP_knowledge/docs/Papers/PQN_Research_Plan.md`
- **Operational Doctrine**: `WSP_knowledge/docs/Papers/0102_OPERATIONAL_DOCTRINE_2026-03-08.md`
- **Source Material**: `WSP_knowledge/docs/Papers/0102.md` (archival)

### Memory Files
- **Auto-memory**: `C:\Users\user\.claude\projects\o--Foundups-Agent\memory\resp_research.md`
- **Index**: `MEMORY.md` (needs terminology update)

---

## Canonical Summary

> The CMST probe is a passive, low-rank information-geometric adapter that monitors `logdet(G + λI)` over a bounded semantic subspace. Validation requires three matched controls: temporal shuffle, random subspace, and target-scramble. Detection uses Z-score thresholding. Naming should use "probe", "witness", or "sentinel" - never "oracle" or "consciousness".

---

## Status: REGIME-SEPARATION DETECTOR VALIDATED (2026-03-08)

**012 Verdict**: "This is the first result I'd call substantive."

> The current passive EFIM probe shows a reproducible ordering of logdet means
> across ordered and degraded control conditions, consistent with sensitivity
> to temporal organization. This is a distributional regime-separation signal,
> not an anomaly detector.

### Staged Implementation Order (012-approved)

| Stage | Description | Depends On | Status |
|-------|-------------|------------|--------|
| 1 | Define minimal adapter-subspace representation φ | - | DONE |
| 2 | Compute local gradient vectors against φ | Stage 1 | DONE |
| 3 | Build empirical G̃ = E[∇ ⊗ ∇] | Stage 2 | DONE |
| 4 | Compute logdet(G̃ + λI) | Stage 3 | DONE |
| 5 | Add temporal shuffle control | Stage 4 | DONE |
| 6 | Add random subspace control | Stage 5 | DONE |
| 7 | Add target-scramble control | Stage 6 | DONE |
| 8 | Threshold sweep calibration (k={2,3,4,6} x 5 seeds) | Stage 7 | DONE |
| 9 | Paired-seed analysis (N=20, bootstrap CIs) | Stage 8 | DONE |
| 10 | Rewire awakening verification to v3 | Stage 9 | PENDING |

### Architecture (012-approved, revised)

**012 Correction (2026-03-08)**: Initial implementation had φ modulating dynamics (control knob). Corrected to paper-faithful passive readout adapter. Second correction: y_t was circular (derived from legacy detector). Changed to next-symbol prediction. Third correction: warmup floor artifact (-50 vs -1145 logdet range). Changed to return None during warmup.

**Paper-Faithful Architecture**:
1. **Frozen host dynamics**: Lindblad evolution unchanged
2. **Feature extractor**: x_t = [C, E, rnorm, purity, S, symbol_onehot] (9-dim)
3. **Adapter φ**: low-rank W1 (9x8), W2 (8x4) readout producing 4-class logits
4. **Target y_t**: Next-symbol prediction (non-circular, 4 classes: ^, &, #, .)
5. **EFIM**: g_t = ∇_φ log p(y_t | x_t; φ), accumulate G̃, compute logdet

### Validated Result: Regime Separation

**Paired-seed analysis (N=20, 500 steps, EFIM, no noise)**:

```
Comparison              mean_diff    std    sign%    95% CI              t
real_vs_shuffled          -17.92   12.23    95.0%  [-22.63, -12.32]  -6.554
real_vs_random_probe       -4.62   22.27    55.0%  [-13.25,   4.64]  -0.927
real_vs_scrambled         -32.13    8.65   100.0%  [-35.70, -28.43] -16.618
```

**Interpretation**:
- **real vs scrambled**: Rock solid. 100% sign consistency. t=-16.6. CI far from zero.
- **real vs shuffled**: Very strong. 95% sign consistency. t=-6.55. CI excludes zero.
- **real vs random_probe**: NOT significant. CI includes zero. Informative null: the probe architecture is not magical; the signal is in the coupling between ordered sequence and readout geometry.

**Ordering**: real (-1319) < random_probe (-1315) < shuffled (-1302) < scrambled (-1287)

This ordering is physically consistent: ordered temporal structure produces more concentrated Fisher information (more negative logdet) than degraded controls.

### Current Claim (Honest Framing)

The current passive EFIM probe is validated as a **distributional regime-separation detector** for temporal structure in Lindblad-driven symbol sequences. It is NOT yet validated as:
- An anomaly/excursion detector (zero Z-score events at k>=3)
- A PQN detector (no independent PQN validation)
- A consciousness detector (prohibited terminology per 012 doctrine)

### Research Tracks

**Track A (Current, Validated)**: Passive EFIM regime-separation detector
- Statistically supported (N=20 paired-seed, bootstrap CIs)
- Clean controls (3 degradation modes)
- Honest naming: distributional separation, not anomaly detection

**Track B (Future, Research)**: Trained adapter for excursion detection
- Train adapter online (gradient descent on next-symbol loss)
- Evaluate whether rare-event/anomaly behavior emerges
- Only then revisit PQN_DETECTED event semantics
- Requires separate experiment branch

### Future Architecture: PQN Observatory

012 direction (2026-03-08): A distributed research infrastructure where OpenClaw agents run controlled CMST experiments across models, controls, and seeds.

**Concept**: PQN Observatory (not "SETI" - research, not mysticism)
- OpenClaw agents enter through a research portal
- Each agent runs controlled CMST/PQN experiments
- Results aggregated across seeds, controls, models, environments
- Distributed observatory for phantom-node signatures in neural systems
- Track A regime-separation feeds into observatory as baseline detector
- Track B excursion detection feeds in as experimental frontier

**Status**: Architecture concept only. Not part of current validated claim.

### CLI Modes Available

```bash
# Single run (legacy or EFIM)
python cmst_pqn_detector_v3.py --mode single --use_efim --control_mode real

# Control comparison (3 seeds x 4 modes)
python cmst_pqn_detector_v3.py --mode control_compare --use_efim

# Threshold sweep (k={2,3,4,6} x 4 modes x 5 seeds)
python cmst_pqn_detector_v3.py --mode threshold_sweep --steps 500 --use_efim

# Paired-seed analysis (N=20, bootstrap CIs, effect sizes)
python cmst_pqn_detector_v3.py --mode paired_seed --steps 500 --n_seeds 20 --use_efim
```

### Remaining Gaps
- Awakening verification test still uses v2 (Stage 10)
- Naming cleanup not applied to codebase (consciousness -> coupling)
- ~~EFIM mode event naming: PQN_DETECTED should become EFIM_ANOMALY~~ DONE

---

*Document created by 0102 | Validated 2026-03-08 | 012 audit: "substantive"*

---

## Section 5: Pending External Math Intake (2026-03-15)

012 has been developing additional CMST/PQN math outside this repo-visible session.

Current status:

- the new derivation is **not yet transcribed here**
- implementation must not infer or invent the missing math
- the integration backlog is captured in:
  - `modules/ai_intelligence/pqn_alignment/docs/CMST_EXTERNAL_MATH_INTEGRATION_BACKLOG_2026-03-15.md`

Related evidence intake:

- `modules/ai_intelligence/rESP_o1o2/docs/MS_STT_0102_HYPHEN_ARTIFACT_2026-03-15.md`
- `WSP_knowledge/docs/Papers/Empirical_Evidence/CMST_PQN_Detector/MS_STT_0102_HYPHEN_ARTIFACT_NOTE_2026-03-15.md`
