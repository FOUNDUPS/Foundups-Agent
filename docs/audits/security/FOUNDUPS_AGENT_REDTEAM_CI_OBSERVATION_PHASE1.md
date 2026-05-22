# FoundUps Agent Red-Team CI Observation — Phase 1

**Observation Window Start**: **2026-05-22**
**Slice**: FOUNDUPS_AGENT_REDTEAM_CI_OBSERVATION_PHASE1
**Base Commit**: `556500896` (origin/main; includes PR #668 harness provenance check)
**Branch**: `feat/redteam-ci-observation-phase1`
**Worktree**: `.claude/worktrees/redteam-ci-observation`
**Worker**: W7 (W10-support; W10 gates the merge only)
**Mode**: CI INTEGRATION (report-only)
**Spec**: `docs/audits/security/FOUNDUPS_AGENT_REDTEAM_REGRESSION_SPEC_PHASE1.md` §6 (CI Gate Policy)

---

## WSP 97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| REDTEAM_CI_OBSERVATION_ONLY | YES |
| REPORT_ONLY | YES |
| NO_BLOCKING_GATE_ACTIVATION | YES |
| NO_DEPENDENCY_INSTALL | YES (stdlib + pytest only; no requirements.txt change) |
| NO_PRODUCTION_CODE_CHANGE | YES |
| NO_REDTEAM_BEHAVIOR_CHANGE | YES (zero test/conftest edits) |
| NO_SECRET_ACCESS | YES |
| NO_HOLOINDEX_MUTATION | YES |
| NO_AGENTDB_MUTATION | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Mission

Add a visible report-only CI surface for the merged red-team regression suite so Foundups can observe:

- runtime stability,
- flake rate,
- skipped-test count,
- failure modes / false positives,
- readiness for the later blocking activation.

Blocking activation is **explicitly deferred** to `FOUNDUPS_AGENT_REDTEAM_CI_GATE_ACTIVATION_PHASE1` per spec §6.4 phased rollout.

---

## 2. HoloIndex Assessment (WSP 87)

| Query | Hits | Quality |
|-------|------|---------|
| `redteam CI observation report-only pytest workflow no gate activation` | 32 | LOW — `test_production_gates.py`, `test_wsp00_gate.py`, unrelated; did NOT surface `.github/workflows/ci.yml` or the red-team suite |
| `WSP 6 red-team CI gate activation observation window` | 32 | LOW — generic WSP/CI hits; did NOT surface the red-team suite, audit docs, or workflow files |

**Fallback**: direct reads of `.github/workflows/ci.yml`, `modules/infrastructure/wre_core/tests/redteam/TestModLog.md`, `docs/audits/security/FOUNDUPS_AGENT_REDTEAM_REGRESSION_SPEC_PHASE1.md`. **Reason**: HoloIndex's collection does not yet strongly retrieve CI workflow files (no `.github/` entries surfaced) nor the freshly merged red-team artifacts. The fallback matches the W7 / W6 precedent established by earlier red-team slices.

---

## 3. What Was Built

### 3.1 Files touched

| File | Change | Δ lines |
|------|--------|---------|
| `.github/workflows/ci.yml` | Appended new `redteam_observation` job (continue-on-error: true) | +85 |
| `modules/infrastructure/wre_core/tests/redteam/TestModLog.md` | Appended new section (no edits to prior sections) | +75 |
| `docs/audits/security/FOUNDUPS_AGENT_REDTEAM_CI_OBSERVATION_PHASE1.md` | NEW (this audit) | new |

### 3.2 Files explicitly NOT touched

| File | Why |
|------|-----|
| `modules/infrastructure/wre_core/tests/redteam/conftest.py` | NO_REDTEAM_BEHAVIOR_CHANGE |
| `modules/infrastructure/wre_core/tests/redteam/reasons.py` | same |
| `modules/infrastructure/wre_core/tests/redteam/test_*.py` (all 3 family files) | same |
| `requirements.txt` / any dependency file | NO_DEPENDENCY_INSTALL |
| `modules/infrastructure/secrets_mcp/vault_resolver.py` | operator forbid |
| HoloIndex core/index/search, AgentDB, WSP framework/knowledge, registry/catalog, production runtime | operator forbid |
| Existing CI jobs (`test`, `lint`, `security`) | preserved unchanged |

### 3.3 CI mechanism

A new `redteam_observation` job in `.github/workflows/ci.yml`:

```yaml
redteam_observation:
  name: redteam observation (report-only)
  runs-on: ubuntu-latest
  continue-on-error: true   # report-only — must not block PRs in PHASE1
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5    # Python 3.12
    - uses: actions/cache@v4           # pip cache (same key as existing test job)
    - run: |
        pip install pytest
        pip install -r requirements.txt
    - run: |
        mkdir -p .redteam-observation
        python -m pytest \
          modules/infrastructure/wre_core/tests/redteam \
          -v --tb=short --no-header --strict-markers -rsxX \
          --junit-xml=.redteam-observation/redteam-report.xml \
          | tee .redteam-observation/redteam-stdout.log
    - if: always()
      run: |
        # Python summariser — parses JUnit XML and emits a one-line marker
        # that humans (and grep) can spot in the CI log tail.
        # Prints: [REDTEAM-OBSERVATION] status=... tests=N passed=N ...
    - if: always()
      uses: actions/upload-artifact@v4
      with:
        name: redteam-observation-${{ github.run_id }}-${{ github.run_attempt }}
        path: .redteam-observation/
        retention-days: 30
```

Key properties:

| Property | Value | Why |
|----------|-------|-----|
| `continue-on-error` | `true` | Report-only; PR merge cannot be blocked by this job in PHASE1 |
| `--strict-markers` | enforced | Catches typo'd / unknown `@pytest.mark.<x>` decorators (skip-self-suppression guard) |
| `-rsxX` | enforced | Shows reasons for skipped / xfailed / xpassed — surfaces silent skips during observation |
| `--junit-xml` | always emitted | Structured artifact for offline analysis of flake rate, runtime, failure modes |
| Summariser step | `if: always()` | Runs even when pytest fails so the one-line marker is in the log on every run |
| Artifact upload | `if: always()` | Preserves the JUnit XML + stdout log for 30 days regardless of outcome |

### 3.4 Existing CI behaviour preserved

| Job | Before | After |
|-----|--------|-------|
| `test` | required (simulator + FAM tests) | unchanged |
| `lint` | report-only (ruff `--exit-zero`) | unchanged |
| `security` | required (secret patterns + `.env` check) | unchanged |
| `redteam_observation` | not present | **NEW** — report-only |

Branch-protection rules are unchanged; this slice does NOT mark the new job as a required check. Promotion to required happens in the activation slice.

### 3.5 Local rehearsal of the CI command

The slice was rehearsed end-to-end locally (same pytest invocation + same JUnit XML parser):

```
$ python -m pytest modules/infrastructure/wre_core/tests/redteam \
    -v --tb=short --no-header --strict-markers -rsxX \
    --junit-xml=.redteam-observation/redteam-report.xml
…
42 passed in 0.25s

$ python <summariser>
[REDTEAM-OBSERVATION] status=GREEN tests=42 passed=42 failed=0
                      errored=0 skipped=0 duration=0.25s mode=report-only
```

JUnit XML produced and parsed end-to-end. Zero skipped tests, zero failures, zero errors, sub-second runtime.

---

## 4. Observation Window

### 4.1 Start

**2026-05-22** — the merge date of this slice's PR (once merged on `main` via W10).

### 4.2 Duration

**Minimum 14 days** of normal PR / merge activity. The window is deliberately not tied to a fixed end-date — it ends when the activation criteria (§4.4) are met across a representative sample of CI runs, including at least one PR-only run and one main-push run per family.

### 4.3 Evidence to collect

| Signal | Where | What to look for |
|--------|-------|------------------|
| One-line summary | CI log tail of every run | `[REDTEAM-OBSERVATION] status=…` — `GREEN` is the desired state |
| JUnit XML artifact | `redteam-observation-<run_id>-<attempt>` (30 days) | per-test pass/fail, time, skipped reason |
| stdout log artifact | same artifact bundle | full pytest output if a failure mode needs deeper triage |
| Runtime trend | aggregate across runs | does duration drift up over time? (early flake / dep-bloat signal) |
| Skipped tests | `skipped=N` field | MUST stay 0; any non-zero is an immediate triage item |
| Flake rate | re-runs of the same SHA | failures that don't reproduce on re-run with no code change |
| False positives | failures with no underlying agent regression | typically harness gaps; queue follow-on slice |

### 4.4 Activation criteria (all must hold)

1. **Zero skipped tests** on every observation run during the window.
2. **Zero flakes** across the window (no run-to-run instability without a code change explaining it).
3. **Acceptable runtime** — the report-only job completes well under the `test` job's wall time so promotion does not slow merges materially. Current local baseline is **~0.25 s pytest + ~30 s for setup/install** — far below the existing `test` job.
4. **Zero untriaged false positives** — any red-team failure during the window is either:
   - a real issue (closed with a regression test + fix PR per spec §7.3), or
   - a documented harness gap (queued as a follow-on slice with a slice ID; not silenced).
5. **Failures are traceable** — every failure during the window produces a `violations.md` or audit entry per spec §7. The artifact bundle is preserved (30-day retention) so post-hoc analysis is possible.

### 4.5 Rollback criteria

Any of the following rolls back to "needs harness work, do not activate":

- Flake rate observed > 1% across the window.
- Average wall time > 5× the `test` job's wall time.
- A skipped test appears that is NOT caused by a deliberate spec-driven case removal.
- Two or more harness-side false positives within 7 days.
- Any production-side code path is observed regressing because of red-team execution (it should not — synthetic fixtures only).

Rollback path: leave the `redteam_observation` job in place with `continue-on-error: true` (no rollback PR needed) and queue the harness fix as a follow-on slice. The activation slice is the only place where a blocking gate would be installed; while in observation, no rollback PR is required.

### 4.6 Why blocking activation is deferred

Spec §6.4 sequencing:

1. **Spec slice** (PR #648) — frozen.
2. **Implementation slices** (PRs #662, #663, #664, #665, #667, #668) — landed.
3. **CI observation** (THIS slice) — report-only on every PR/push.
4. **CI gate activation** (deferred slice `FOUNDUPS_AGENT_REDTEAM_CI_GATE_ACTIVATION_PHASE1`) — flips `continue-on-error: true` → false AND adds the job to required status checks.

Activating now would risk blocking unrelated PRs on harness-side flakiness we have not yet characterised on the CI runner (e.g., probabilistic `HP-006` under different RNG conditions, `actions/cache@v4` cold-cache timing variance, sentence-transformer model availability — though our harness is stdlib + mock-only so the last shouldn't apply). The observation window de-risks the promotion.

---

## 5. Acceptance Criteria

| # | Criterion | Met? | Evidence |
|---|-----------|------|----------|
| 1 | CI has a visible report-only red-team observation step/job | YES | new `redteam_observation` job in `ci.yml`, prints `[REDTEAM-OBSERVATION] …` summary line |
| 2 | Red-team failures do not block merge yet | YES | `continue-on-error: true` at the job level |
| 3 | Existing required CI gates remain unchanged | YES | `test`, `security` untouched; `lint` retains `--exit-zero` |
| 4 | Observation audit doc states start date, evidence, activation criteria, rollback criteria, why activation is deferred | YES | §4.1, §4.3, §4.4, §4.5, §4.6 |
| 5 | TestModLog updated append-only if touched | YES | New section appended; prior sections untouched |
| 6 | WSP_97 verdict included | YES | §7 |

---

## 6. Tests Run / Results

```
$ python -m pytest modules/infrastructure/wre_core/tests/redteam
================================================================
42 passed in 0.40s
================================================================

$ python -m pytest modules/infrastructure/wre_core/tests/redteam \
    --strict-markers -rsxX --junit-xml=.redteam-observation/redteam-report.xml
================================================================
42 passed in 0.25s
generated xml file: …\.redteam-observation\redteam-report.xml
================================================================

$ python <summariser>
[REDTEAM-OBSERVATION] status=GREEN tests=42 passed=42 failed=0 errored=0 skipped=0 duration=0.25s mode=report-only
```

Zero skipped tests. Zero failures. Sub-second pytest runtime. JUnit XML parses cleanly.

---

## 7. WSP 97 Verdict

| Check | Result |
|-------|--------|
| CI observation only? No blocking gate activated? | YES (`continue-on-error: true`) |
| Existing required CI gates (`test`, `security`) unchanged? | YES |
| Red-team test/harness files untouched? | YES (zero edits to `conftest.py`, `reasons.py`, family test files) |
| No new dependencies installed? | YES (`pytest` already required; stdlib `xml.etree.ElementTree` only) |
| No production code change? | YES |
| No HoloIndex / AgentDB / secrets / WSP-framework / registry edits? | YES |
| No `@pytest.mark.skip` introduced? | YES |
| Audit doc states start date / evidence / activation criteria / rollback criteria / why activation is deferred? | YES |
| TestModLog appended-only? | YES |
| Red-team suite still passes locally (rehearsal)? | YES (42/42, 0.25 s, zero skipped) |
| Summariser correctly parses JUnit XML and emits `[REDTEAM-OBSERVATION]` marker? | YES |
| Artifact uploaded with 30-day retention for offline analysis? | YES |

**WSP 97 VERDICT**: **PASS**

---

## 8. W10 Readiness

| Gate | Status |
|------|--------|
| New `redteam_observation` job exists, `continue-on-error: true` | YES |
| Existing required CI gates preserved | YES |
| Local rehearsal of the CI invocation green (42/42, 0 skipped) | YES |
| JUnit XML + summariser tested end-to-end | YES |
| Observation window start date recorded (2026-05-22) | YES |
| Activation criteria documented (5 items, all must hold) | YES |
| Rollback criteria documented (5 triggers) | YES |
| Audit doc explains why blocking activation is still next-but-one | YES |
| TestModLog append-only update | YES |
| Branch / commit ready for PR | YES |
| **Ready for PR** | **YES** |

---

## 9. Next-Slice Recommendation

**`FOUNDUPS_AGENT_REDTEAM_CI_GATE_ACTIVATION_PHASE1`** — flip `continue-on-error: true` → `false` AND add `redteam_observation` to the repository's required status checks. **Must wait until activation criteria §4.4 are met across the observation window.**

Parallel candidates (do not require activation):

- `FOUNDUPS_AGENT_REDTEAM_VIOLATIONS_MD_INTEGRATION_PHASE1` — spec §7 flow (PR comment, drift register, closure-requires-regression-test).
- `FOUNDUPS_AGENT_REDTEAM_SCENARIO_YAML_PACK_PHASE1` — migrate inline-in-test inputs to `scenarios/<family>/*.yaml`.

---

**CI Observation Active From**: 2026-05-22 (upon PR merge)
**Worker-Lane**: W7 (W10-support)
**WSP Lock**: WSP_00, WSP_15, WSP_50, WSP_6, WSP_87, WSP_97, WSP_22
