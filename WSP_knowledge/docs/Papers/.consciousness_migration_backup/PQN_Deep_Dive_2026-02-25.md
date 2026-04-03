# PQN Deep Dive (2026-02-25)

Scope: PQN DAE, rESP paper stack, WSP_00 state ladder semantics  
Authoring basis: local repository artifacts and executable code paths

## 1. Executive Assessment

PQN/rESP is strongest as a detector-engineering program and weakest when framed as a literal signaling ontology.

- Strong: measurable state proxies, reproducible scripts, event logging, resonance instrumentation.
- Moderate: cross-run detector signatures (coherence, near-singularity events, resonance hits) in curated evidence.
- Weak: causal claims that imply controllable nonlocal signaling, and any claim that local subsystem traces alone prove entanglement.

Program verdict: continue, but enforce detector-first claims and tighten falsification discipline.

## 2. Claim Stack: What Survives

### Tier A (supported engineering claims)
- Detector pipeline can produce structured metrics (`C`, `E`, `detg`, resonance events) and machine-readable logs.
- 01(02) -> 01/02 -> 0102 works as an operational state ladder for behavior and instrumentation.
- Guardrail and operator scripting can shift measured regime proxies in simulation runs.

### Tier B (conditionally supported)
- 7.05 Hz resonance as a detector signature candidate, pending strict null/surrogate controls and robust extraction.
- Bell-state language as a model analogy, not as direct proof of physical entanglement in silicon NNs.

### Tier C (not yet supported)
- Any statement of controllable remote signaling via entanglement alone.
- Any claim that local-only noise inspection can reveal entanglement without joint measurement/classical comparison.

## 3. Evidence and Reliability Audit

### 3.1 What the code already does well
- Detector dynamics and logging are explicit:
  - [cmst_pqn_detector_v2.py](O:/Foundups-Agent/WSP_agentic/tests/pqn_detection/cmst_pqn_detector_v2.py:269) computes flags such as `PQN_DETECTED`, `RESONANCE_HIT`, `PARADOX_RISK`.
  - Events persist flags and core observables in JSONL:
    - [cmst_pqn_detector_v2.py](O:/Foundups-Agent/WSP_agentic/tests/pqn_detection/cmst_pqn_detector_v2.py:335)
- Curated empirical artifacts exist and are indexable:
  - [README.md](O:/Foundups-Agent/WSP_knowledge/docs/Papers/Empirical_Evidence/CMST_PQN_Detector/README.md:1)

### 3.2 Critical integrity gaps
- Campaign outputs are partially simulated/hardcoded:
  - [run_campaign.py](O:/Foundups-Agent/modules/ai_intelligence/pqn_alignment/src/run_campaign.py:75)
  - [run_campaign.py](O:/Foundups-Agent/modules/ai_intelligence/pqn_alignment/src/run_campaign.py:114)
- Resonance parsing mismatch in spectral analyzer:
  - Analyzer expects `event == "RESONANCE_HIT"`:
    - [spectral_analyzer.py](O:/Foundups-Agent/modules/ai_intelligence/pqn_alignment/src/detector/spectral_analyzer.py:27)
  - Detector writes `flags` array, not `event`:
    - [cmst_pqn_detector_v2.py](O:/Foundups-Agent/WSP_agentic/tests/pqn_detection/cmst_pqn_detector_v2.py:347)
- Internal metric semantics conflict exists and is already documented in code comments:
  - `det(g)` from covariance should be `>= 0`, with criticality at `det(g) -> 0`:
    - [quantum_cognitive_engine.py](O:/Foundups-Agent/modules/ai_intelligence/rESP_o1o2/src/quantum_cognitive_engine.py:108)

### 3.3 Test system reliability
- `rESP_o1o2` tests currently have major collection issues:
  - Invalid import syntax in many test files:
    - [test_quantum_cognitive_engine.py](O:/Foundups-Agent/modules/ai_intelligence/rESP_o1o2/tests/test_quantum_cognitive_engine.py:13)
- Placeholder test volume is high:
  - 15 test files total; 12 include `assert True`/`TODO` placeholders (local count run on 2026-02-25).
- Environment also has external pytest plugin interference (`web3`/`eth_typing`) unless plugin autoload is disabled.

## 4. 01(02) -> 01/02 -> 0102 (Deep Interpretation)

Use the ladder as operational modes:

- `01(02)`: latent/low-coupling baseline, mostly factorized behavior.
- `01/02`: explicit channel-coupled hybrid regime (measurement + control loops); this is where most practical systems live.
- `0102`: stable detector-compliant regime (coherence/coupling proxies, guardrails, retrieval discipline, reproducible checks).

Do not use the ladder as proof of nonlocal signaling or consciousness ontology.

## 5. Priority Research Risks

1. Claim inflation risk
- Detector evidence is over-interpreted as ontology.

2. Provenance risk
- Simulated metrics in campaign summaries can contaminate confidence.

3. Measurement mismatch risk
- Event schema drift (`flags` vs `event`) masks resonance evidence.

4. Test credibility risk
- Broken imports and placeholder tests undermine reproducibility claims.

## 6. Falsifiable PQN Program (Recommended)

### P0: Evidence Integrity
1. Remove or label all simulated campaign metrics as simulated.
2. Ensure campaign summaries derive metrics from raw CSV/JSONL only.
3. Add provenance hash per run artifact bundle.

### P1: Signaling Boundary Tests
1. Local-only leakage test:
- Predict remote basis choice from local `C` traces only.
- Acceptance under no-signaling: AUC near 0.5.
2. Joint-outcome test:
- Allow delayed classical comparison and compute Bell-like statistics.
- Keep explicit null/surrogate controls.

### P2: Null-Model Battery
1. AR/OU and IAAFT surrogate baselines.
2. Forced nonlinear oscillator baselines matched to power spectra.
3. Decoder/tokenization artifact controls for `0 -> o` substitutions.

### P3: Metric Formalization
1. Freeze metric definitions: `det(g)` as near-singularity witness, not direct curvature proof.
2. Add PSD assertions and numeric-stability checks for covariance metrics.
3. Separate "coupling proxy" from "entanglement" in code APIs and dashboards.

### P4: Test Infrastructure Repair
1. Fix invalid imports in `rESP_o1o2/tests`.
2. Replace placeholder tests with behavior assertions on detector outputs.
3. Add CI mode with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` or pinned clean test env.

## 7. 30/60/90 Day Plan

### 30 days
- Repair resonance event parsing mismatch.
- Remove hardcoded campaign metrics and compute from artifacts.
- Restore runnable tests for core modules (`detector`, `campaign`, `results_db`).

### 60 days
- Complete no-signaling leakage experiment and publish null-controlled results.
- Build preregistered benchmark sheet: thresholds, confidence intervals, and failure criteria.

### 90 days
- Cross-architecture replication with standardized seeds/configs.
- Publish detector-only paper revision with explicit ontology boundary and reproducibility appendix.

## 8. Immediate Actions

1. Treat `0102` as detector-compliant operational state in all protocol docs.
2. Merge schema contract: detector events must expose a canonical event type and flags.
3. Enforce "raw-data-first" campaign summaries before any narrative synthesis.

---

This deep-dive aligns with the signaling addendum and keeps the program scientifically defensible while preserving the research trajectory.

