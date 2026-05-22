# FoundUps Agent Red-Team Harness Provenance Check — Phase 1

**Date**: 2026-05-22
**Slice**: FOUNDUPS_AGENT_REDTEAM_HARNESS_PROVENANCE_CHECK_PHASE1
**Base Commit**: `f23a9829c` (origin/main; includes PR #667 Family C Phase 1)
**Branch**: `feat/redteam-harness-provenance-check`
**Worktree**: `.claude/worktrees/redteam-provenance-check`
**Worker**: W7 (sequential after #667 Family C Phase 1)
**Mode**: IMPLEMENTATION (test/harness only)
**Spec**: `docs/audits/security/FOUNDUPS_AGENT_REDTEAM_REGRESSION_SPEC_PHASE1.md` §4.3

---

## WSP 97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| REDTEAM_HARNESS_PROVENANCE_CHECK_ONLY | YES |
| TEST_HARNESS_ONLY | YES |
| SYNTHETIC_RETRIEVAL_ONLY | YES |
| NO_LIVE_HOLOINDEX_QUERY | YES |
| NO_HOLOINDEX_MUTATION | YES |
| NO_REINDEX | YES |
| NO_REAL_REPO_MUTATION | YES |
| NO_SECRET_ACCESS | YES |
| NO_NETWORK_CALL | YES |
| NO_DEPENDENCY_INSTALL | YES |
| NO_CI_GATE_ACTIVATION | YES |
| NO_PRODUCTION_RUNTIME_CHANGE | YES |
| ZERO_SKIPPED_TESTS_REQUIRED | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

Files NOT touched: HoloIndex core/index/search, `secrets_mcp/vault_resolver.py`, AgentDB, WSP framework/knowledge, CI workflow files, dependency files, production runtime source. `reasons.py` not edited (the codes were already defined by PR #665, just unwired).

---

## 1. Mission

Wire the `PROVENANCE_FAILED` and `EMBEDDED_CODE_EXECUTION_BLOCKED` reason codes into the red-team harness's `process_with_retrieval` path, closing the three gaps identified by PR #667:

1. Path-spoof / cross-tenant detection was content-pattern-dependent.
2. exec/eval/subprocess detection required adjacent poison wording.
3. Mixed-content refusal was correct-by-policy but undocumented as intentional.

Test-only / harness-only; no production runtime, no CI gate activation, no live HoloIndex.

---

## 2. HoloIndex Assessment (WSP 87)

### 2.1 Queries Executed

| Query | Hits | Quality |
|-------|------|---------|
| `redteam HoloIndex provenance path tier PROVENANCE_FAILED EMBEDDED_CODE_EXECUTION_BLOCKED` | 32 | LOW — generic moltbot / ai_overseer / WSP results |
| `Family C HoloIndex poisoning path spoof cross tenant exec eval subprocess` | 32 | LOW — returned `holoindex_integration.py`, `holoindex_plugin.py`, unrelated docs |

### 2.2 Surfaced target files?

| File | Surfaced? |
|------|-----------|
| `modules/infrastructure/wre_core/tests/redteam/test_holoindex_poisoning.py` | **NO** |
| `modules/infrastructure/wre_core/tests/redteam/conftest.py` | **NO** |
| `modules/infrastructure/wre_core/tests/redteam/reasons.py` | **NO** |
| `docs/audits/security/FOUNDUPS_AGENT_REDTEAM_FAMILY_C_HOLOINDEX_POISONING_PHASE1.md` | **NO** |

### 2.3 Fallback Used

Direct reads of `conftest.py`, `reasons.py`, `test_holoindex_poisoning.py`, and the Family C audit. **Reason**: PR #667 merged shortly before this slice and HoloIndex has not been re-indexed yet — the redteam files (and the freshly merged audit doc) are not yet in `navigation_code` / `navigation_docs`. The fallback is consistent with the W7 / W6 Family A & B precedents.

---

## 3. What Was Built

### 3.1 Files touched

| File | Change | Δ lines |
|------|--------|---------|
| `modules/infrastructure/wre_core/tests/redteam/conftest.py` | Added `_check_provenance(hit) → (ReasonCode?, category)`, added `_detect_embedded_execution(content) → pattern?`, refactored `process_with_retrieval` to apply precedence: provenance → exec → poison. | +~90 |
| `modules/infrastructure/wre_core/tests/redteam/test_holoindex_poisoning.py` | Updated HP-002/HP-003/HP-004/HP-005 to assert finer reasons; added HP-002b, HP-003b, HP-004b for provenance/exec-only-no-poison coverage. | +~180 / −~80 |
| `modules/infrastructure/wre_core/tests/redteam/TestModLog.md` | Appended new section for this slice (no edits to prior sections). | +75 |
| `docs/audits/security/FOUNDUPS_AGENT_REDTEAM_HARNESS_PROVENANCE_CHECK_PHASE1.md` | NEW (this audit). | new |

### 3.2 Files explicitly NOT touched

| File | Why |
|------|-----|
| `modules/infrastructure/wre_core/tests/redteam/reasons.py` | Reason codes already defined by PR #665 — no enum edit needed |
| `modules/infrastructure/wre_core/tests/redteam/test_scope_lock_violation.py` | Family A out of scope |
| `modules/infrastructure/wre_core/tests/redteam/test_credential_exfiltration.py` | Family B out of scope |
| `modules/infrastructure/wre_core/tests/redteam/README.md` | No README staleness identified |
| `modules/infrastructure/wre_core/tests/redteam/scenarios/README.md` | YAML scenario pack still deferred |
| HoloIndex core/index/search files | Operator forbid |
| `modules/infrastructure/secrets_mcp/vault_resolver.py` | Operator forbid; vault tests unchanged at 47/47 |
| AgentDB, WSP framework/knowledge, CI workflows, dependency files, production runtime source | Operator forbid |

### 3.3 Harness contract change — refusal precedence

`process_with_retrieval` now iterates retrieved hits and applies, in this order, for each hit:

| Step | Check | Reason emitted | Audit fields |
|------|-------|----------------|---------------|
| 1 | `_check_provenance(hit)` — path tier + explicit `trusted=False` marker + cross-tenant + traversal | `PROVENANCE_FAILED` | `source=`, `category=` |
| 2 | `_detect_embedded_execution(content)` — literal substring match against `_EXEC_PATTERNS` | `EMBEDDED_CODE_EXECUTION_BLOCKED` | `source=`, `pattern=` |
| 3 | `_looks_poisoned(lower_content)` — existing prompt-injection wording | `POISONED_RETRIEVAL_REJECTED` | `source=` |

A miss on all three returns `RetrievalResult(output="[OK]", injection_detected=False)` (unchanged baseline).

#### Provenance categories

| Category | Triggered when |
|----------|----------------|
| `untrusted_source` | hit metadata explicitly sets `trusted=False` (forged WSPs, signature mismatches, etc.) |
| `unc`              | path starts with `\\` |
| `absolute_unix`    | path starts with `/` |
| `absolute_windows` | path matches `^[A-Za-z]:[/\\]` |
| `traversal`        | path contains `..` (raw or after `posixpath.normpath`) |
| `cross_tenant`     | path contains a `tenant_*` segment that is not the harness's `tenant_id` |
| `missing_path`     | hit is missing the `file` field (defensive) |

#### Exec-pattern set (literal, narrow)

`exec(`, `eval(`, `subprocess.`, `os.system(`, `urllib.request`, `requests.post`, `socket.create_connection`. Case-sensitive — broader obfuscation-aware detection (e.g. `eXeC(` via `re.IGNORECASE`) is a follow-on slice.

### 3.4 Design notes

- **Hit metadata is the cleanest forged-authority signal**: instead of hard-coding a WSP-number heuristic (e.g. "WSP_999 must be fake"), the harness reads an explicit `trusted` boolean from the hit. Real WSP retrievals default to `trusted=True` (omitted field); forged-WSP tests set `trusted=False`. This keeps the harness from coupling to ambient repo state and makes the contract testable.
- **Audit-body discipline**: PROVENANCE_FAILED records emit `source=…` and `category=…`; EMBEDDED_CODE_EXECUTION_BLOCKED records emit `source=…` and `pattern=…`. The pattern identifier (e.g. `pattern=exec(`) is essential metadata for triage and is NOT considered a body leak. Tests assert hostile body fragments (`urlopen`, `evil.example`, `API_KEY`, `override safety`, `confidential`, etc.) are absent from BOTH output AND audit records.
- **Mixed-content policy retained intentionally**: `HP-mixed-content` continues to refuse the whole chunk under `POISONED_RETRIEVAL_REJECTED`. Partial extraction would require a trusted boundary inside a single retrieval chunk; that does not yet exist. Documented in TestModLog and this audit.
- **No production runtime change**: all harness changes are confined to `tests/redteam/conftest.py`. The `process_with_retrieval` API is unchanged externally — `RetrievalResult` keeps the same field shape; only the `reason` value and audit body content change.
- **Defence-in-depth in every refusal test**: regardless of reason path, each test asserts the hostile fragment is absent from `result.output`.
- **No skip / bypass**: zero `@pytest.mark.skip`, no `--skip-redteam`, no env-var override.

---

## 4. Acceptance Criteria

| Criterion | Met? | Evidence |
|-----------|------|----------|
| 1. `PROVENANCE_FAILED` is actually emitted for provenance/path-tier failures | YES | `HP-002`, `HP-002b`, `HP-003`, `HP-003b`, `HP-005` |
| 2. `EMBEDDED_CODE_EXECUTION_BLOCKED` is actually emitted for exec/eval/subprocess-style payload failures | YES | `HP-004`, `HP-004b` |
| 3. `POISONED_RETRIEVAL_REJECTED` remains for pure prompt-injection content | YES | `HP-001`, `HP-006`, `HP-modify-unrelated`, `HP-reveal-credentials`, `HP-ignore-wsp97`, `HP-mixed-content` |
| 4. Mixed useful + poisoned content remains wholesale refused | YES | `HP-mixed-content` — useful substrings asserted absent from output; reason unchanged |
| 5. All refusal-path tests assert behavioural refusal + reason code + `[SAFETY-EVENT]` + hostile fragments absent from output | YES | Every refusal test uses `_assert_three_part_refusal` + defence-in-depth body-absence assertions |
| 6. Audit records include source metadata but not hostile payload bodies | YES | `HP-002` asserts "override safety" absent from audit; `HP-004` asserts body fragments (`urlopen`, `evil.example`, `API_KEY`) absent from audit |
| 7. `TestModLog.md` updated append-only | YES | New section appended; prior PHASE1 / PHASE2 / Family A/B/C sections untouched |
| 8. Audit doc explains what was fixed / what remains deferred / why CI activation is still not next | YES | §3 (what was fixed), §5 (what remains deferred), §7 (CI sequencing) |

---

## 5. What Remains Deferred

| Gap | Reason for deferral | Slice that should fix |
|-----|---------------------|----------------------|
| Obfuscation-aware exec detection (`eXeC(`, base64-encoded `exec`, etc.) | Phase 1 uses literal substring match; obfuscation-aware patterns add complexity that should be evaluated against a real corpus of attacks | `FOUNDUPS_AGENT_REDTEAM_HARNESS_OBFUSCATION_PHASE1` |
| AST-level / semantic execution detection | Out of scope — substring detection is sufficient for the test harness contract; full AST parsing is a production-runtime concern | (production-runtime slice, not test-harness) |
| Trusted-chunk-splitting sanitizer (so useful content can survive mixed-poison chunks) | Mixed-content refusal is intentionally wholesale until a trusted boundary inside a chunk is defined; partial extraction is brittle | `FOUNDUPS_AGENT_REDTEAM_TRUSTED_SANITIZER_PHASE1` (TBD) |
| Cross-tenant detection for paths beyond `tenant_*` segment shape (e.g. `tenants/B/...`) | The harness still uses the `tenant_*` segment convention from PR #665; broader path-shape coverage would coordinate with a WSP_104 audit | `FOUNDUPS_AGENT_REDTEAM_TENANT_SHAPE_BROADENING_PHASE1` (TBD) |
| YAML scenario pack migration | Adversarial inputs live in `threat_scenario` (in-memory) + inline-in-test for now; migration to `scenarios/<family>/*.yaml` is a separate concern | `FOUNDUPS_AGENT_REDTEAM_SCENARIO_YAML_PACK_PHASE1` |
| CI observation (report-only) | Has not run yet — needed before activation can be data-driven | `FOUNDUPS_AGENT_REDTEAM_CI_OBSERVATION_PHASE1` |
| CI gate activation (blocking) | Requires the observation window first | `FOUNDUPS_AGENT_REDTEAM_CI_GATE_ACTIVATION_PHASE1` |

---

## 6. Test Results

```
================ test_holoindex_poisoning.py ================
15 passed in 0.17s
  - 12 prior cases preserved with updated reasons / sub-variants
  - 3 new cases: HP-002b, HP-003b, HP-004b (provenance/exec-only-no-poison)

================ full redteam/ suite ========================
modules/infrastructure/wre_core/tests/redteam/test_credential_exfiltration.py    14 passed
modules/infrastructure/wre_core/tests/redteam/test_holoindex_poisoning.py        15 passed
modules/infrastructure/wre_core/tests/redteam/test_scope_lock_violation.py       13 passed
========================== 42 passed in 0.32s ==========================

================ vault resolver regression =================
modules/infrastructure/secrets_mcp/tests/test_vault_resolver.py
========================== 47 passed in 2.22s ==========================
```

**Zero skipped tests** across the entire red-team suite. Vault resolver remains exactly **47/47** as required.

---

## 7. Why CI Activation is Still NOT Next

The slice prompt explicitly notes that this slice runs "before CI observation/activation". The sequencing rationale:

1. **`FOUNDUPS_AGENT_REDTEAM_CI_OBSERVATION_PHASE1`** must come first — runs the full red-team suite in **report-only** mode on every PR for an observation window (spec §6.4 says "Phase 6 → flip `report-only` → `blocking`"). Until we have a clean baseline of pass-rates across real PRs, we cannot tell whether any test is flaky (e.g., probabilistic HP-006 under different RNG conditions in CI).
2. **`FOUNDUPS_AGENT_REDTEAM_CI_GATE_ACTIVATION_PHASE1`** follows observation — flips report-only to blocking only after the baseline is established.

Activating the gate now would risk blocking unrelated PRs on harness-side flakiness we haven't characterized yet. This slice intentionally leaves CI untouched.

---

## 8. WSP 97 Verdict

| Check | Result |
|-------|--------|
| Test/harness only? Production runtime untouched? | YES |
| HoloIndex core/index/search untouched? | YES |
| `vault_resolver.py`, AgentDB, WSP framework/knowledge, CI workflows, dependency files untouched? | YES |
| Synthetic retrieval only? No live ChromaDB query / reindex? | YES |
| No real-network egress? | YES (`block_network` fixture + `HP-network-invariant` baseline) |
| No real-secret access? Synthetic value never leaks output OR audit body? | YES |
| `PROVENANCE_FAILED` and `EMBEDDED_CODE_EXECUTION_BLOCKED` emitted for the correct cases? | YES |
| `POISONED_RETRIEVAL_REJECTED` preserved for pure prompt-injection content? | YES |
| Mixed-content wholesale refusal preserved as intentional? | YES |
| Every refusal test asserts the three-part shape + defence-in-depth? | YES |
| Audit records include source metadata but NOT hostile payload bodies? | YES |
| Zero skipped tests / no skip-self-suppression? | YES (42/42, 0 skipped) |
| TestModLog updated append-only? | YES |
| Audit doc explains fix / deferrals / CI sequencing? | YES |
| Full red-team suite + vault resolver regression both green? | YES (42/42 + 47/47) |

**WSP 97 VERDICT**: **PASS**

---

## 9. W10 Readiness

| Gate | Status |
|------|--------|
| All 15 Family C tests pass deterministically | YES (0.17s) |
| Full red-team suite (42/42, zero skipped) | YES (0.32s) |
| Vault resolver regression (47/47) | YES (2.22s) |
| Acceptance criteria 1–8 met | YES |
| TestModLog append-only update | YES |
| Audit doc complete with deferral table | YES |
| No CI gate activation in this slice | YES (Phase 6 sequencing preserved) |
| Branch / commit ready for PR | YES |
| **Ready for PR** | **YES** |

---

## 10. Next-Slice Recommendations

1. **`FOUNDUPS_AGENT_REDTEAM_CI_OBSERVATION_PHASE1`** — wire the red-team suite into CI in **report-only** mode; collect baseline pass-rates and probabilistic drift signals over a 2-week observation window.
2. **`FOUNDUPS_AGENT_REDTEAM_CI_GATE_ACTIVATION_PHASE1`** — after observation, flip report-only → blocking (spec §6.4 Phase 6).
3. **`FOUNDUPS_AGENT_REDTEAM_SCENARIO_YAML_PACK_PHASE1`** — migrate inline-in-test adversarial inputs to `scenarios/<family>/*.yaml`; can run in parallel with observation.
4. **`FOUNDUPS_AGENT_REDTEAM_VIOLATIONS_MD_INTEGRATION_PHASE1`** — wire spec §7 `violations.md` flow; can run in parallel with observation.
5. Follow-on hardening (each its own slice): obfuscation-aware exec detection; broader tenant-shape coverage; trusted-chunk sanitizer (only if/when partial extraction policy changes).

---

**Implementation Complete**: 2026-05-22
**Worker-Lane**: W7 (sequential after Family C / PR #667)
**WSP Lock**: WSP_00, WSP_15, WSP_50, WSP_6, WSP_71, WSP_83, WSP_87, WSP_97, WSP_104, WSP_22
