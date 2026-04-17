# DD — Hermes FoundUp Builder Operational Proof, Phase 1

**Worker**: DD
**Slice**: HERMES_FOUNDUP_BUILDER_OPERATIONAL_PROOF_PHASE1
**Date**: 2026-04-17
**WSP References**: WSP 50 (Pre-Action), WSP 77 (Agent Coordination), WSP 91 (Observability), WSP 97 (System Execution Prompting), WSP 106 (FoundUp API Gateway)

---

## WSP 97 Truthfulness Statement

> **No real repository extraction was performed.** No `git filter-repo` was invoked, no GitHub repository was created, no external repo was mutated, no remote was pushed. All proof in this briefing was produced under `HERMES_BUILDER_DRY_RUN=1` with the security gate disabled (`HERMES_BUILDER_SECURITY_GATE=0`) for contract-only verification. The Hermes integration remains a scaffold/POC — this slice proves the dry-run contract surface, not live extraction.

---

## Scope

Phase 1 acceptance criteria from the worker brief:

1. Add focused tests for Hermes builder dry-run behaviour. ✅
2. Add a reproducible dry-run proof artifact for one known target. ✅ (this file)
3. Tighten deploy-surface detection only where evidence exists. ✅ (Kosei evidence: manifest `entry_url` + `launch_readiness: "ready"`)
4. Preserve WSP 97 truth: no claim that live extraction works. ✅
5. Do not invoke real `git filter-repo`, do not create repos, do not push. ✅

Out of scope (per brief): real extraction, GitHub repo creation, push, deploy, WSP 106 HTTP wiring, new model backends, broad Hermes feature expansion.

---

## Files Changed

| Path | Change | Why |
|------|--------|-----|
| `modules/foundups/agent/src/hermes_adapter.py` | Refactored deploy-surface check into `_detect_deploy_surface()` and added evidence-based recognition (manifest `entry_url + launch_readiness=ready`, `app/index.html`, `frontend/index.html`) | Kosei legitimately deploys via Firebase Hosting (manifest declares `entry_url: https://foundupscom.web.app/kosei/app/`, `launch_readiness: ready`) but had no `firebase.json/Dockerfile/cloudbuild.yaml/deployment/` in-module, so the prior detector falsely failed it. New detector accepts narrow, evidence-based signals. |
| `modules/foundups/agent/tests/__init__.py` | Created (empty) | Mark tests dir as package. |
| `modules/foundups/agent/tests/test_hermes_foundup_builder.py` | Created — 18 focused dry-run tests | Covers init/FAM-unavailable, qwen-unavailable, analyze_boundary, exfoliation gate (incl. all deploy-surface evidence paths), sign_manifest determinism, generate_adapters dry-run, extract_foundup dry-run pass + fail, and read-only assertions on real GotJunk + Kosei modules. |
| `modules/foundups/agent/tests/README.md` | Updated test status from planned → implemented for Hermes builder section | WSP 22 doc currency. |
| `modules/foundups/agent/INTERFACE.md` | Appended Hermes Builder Dry-Run Contract section | Public contract documentation per WSP 11. |
| `modules/foundups/agent/ModLog.md` | DD entry for this slice | WSP 22. |
| `docs/0102_session_briefings/DD_HERMES_FOUNDUP_BUILDER_OPERATIONAL_PROOF_PHASE1.md` | Created (this file) | Reproducible proof artifact. |

No unrelated dirty files were touched. The repo had pre-existing modifications outside this scope (e.g., `WSP_knowledge/reasoning_traces/...`, `tests/*` deletions, `public/kosei/*` additions); they were left alone.

---

## Tests Added & Result

**Command:**
```
python -m pytest modules/foundups/agent/tests -q
```

**Result:** `18 passed in 5.27s` (full output below).

| Test class | Test | Status |
|---|---|---|
| `TestInitialization` | `test_init_does_not_crash_when_fam_unavailable` | PASS |
| `TestInitialization` | `test_check_qwen_available_reports_unavailable_not_crashes` | PASS |
| `TestAnalyzeBoundary` | `test_returns_product_files_imports_blockers` | PASS |
| `TestAnalyzeBoundary` | `test_blockers_when_contracts_missing` | PASS |
| `TestAnalyzeBoundary` | `test_missing_module_produces_blocker` | PASS |
| `TestExfoliationGate` | `test_returns_structured_booleans_no_crash` | PASS |
| `TestExfoliationGate` | `test_full_fixture_passes_gate` | PASS |
| `TestExfoliationGate` | `test_manifest_entry_url_satisfies_deploy_surface` | PASS |
| `TestExfoliationGate` | `test_app_index_html_satisfies_deploy_surface` | PASS |
| `TestExfoliationGate` | `test_no_deploy_surface_blocks_check` | PASS |
| `TestSignManifest` | `test_signature_is_deterministic` | PASS |
| `TestSignManifest` | `test_signature_excludes_existing_signature_field` | PASS |
| `TestSignManifest` | `test_signature_changes_when_payload_changes` | PASS |
| `TestGenerateAdaptersDryRun` | `test_dry_run_returns_code_without_writing` | PASS |
| `TestExtractFoundUpDryRun` | `test_complete_fixture_dry_run_succeeds` | PASS |
| `TestExtractFoundUpDryRun` | `test_incomplete_fixture_returns_exfoliation_gate_failed` | PASS |
| `TestRealRepoReadOnly` | `test_gotjunk_boundary_analysis_returns_structure` | PASS |
| `TestRealRepoReadOnly` | `test_kosei_deploy_surface_now_recognized` | PASS |

Unit tests use `tmp_path` fixtures (no live repo state). Read-only assertions against the real GotJunk + Kosei modules are restricted to boundary inspection — no extraction is invoked.

---

## Dry-Run Proof — GotJunk

### Environment
- `HERMES_BUILDER_DRY_RUN=1`
- `HERMES_BUILDER_SECURITY_GATE=0` (disabled — proving the dry-run contract, not the security gate)
- `HERMES_BUILDER_ENABLED=1` (default)
- LM Studio at `localhost:1234`: **NOT available**
- FAM Daemon: **available** (attached at builder init)
- MCP Bridge v1.4: **available** (attached at builder init)
- Repo root: `o:/Foundups-Agent`
- Target module: `modules/foundups/gotjunk`
- Target org: `FOUNDUPS`

### Reproducible Command

```bash
HERMES_BUILDER_SECURITY_GATE=0 HERMES_BUILDER_DRY_RUN=1 python -c "
import json
from pathlib import Path
from modules.foundups.agent.src.hermes_adapter import HermesFoundUpBuilder

builder = HermesFoundUpBuilder(repo_root=Path('.'))
result = builder.extract_foundup('modules/foundups/gotjunk', target_org='FOUNDUPS')
print(json.dumps(result, indent=2, default=str))
"
```

### Captured Output

**`check_qwen_available()`**:
```json
{
  "available": false,
  "error": "LM Studio not running at localhost:1234"
}
```

**`analyze_boundary("modules/foundups/gotjunk")`**:
```json
{
  "module_path": "modules/foundups/gotjunk",
  "product_files_count": 4,
  "core_imports": ["modules.infrastructure.wre_core"],
  "adapters_needed": ["wre_adapter"],
  "blockers": [],
  "exfoliation_ready": true
}
```

**`check_exfoliation_gate("modules/foundups/gotjunk")`**:
```json
{
  "passed": true,
  "module_boundary_clear": true,
  "contracts_explicit": true,
  "runtime_testable": true,
  "deploy_surface_understood": true,
  "shared_deps_adapter_level": true,
  "claw_can_participate": true
}
```

**`extract_foundup("modules/foundups/gotjunk", target_org="FOUNDUPS")` [dry-run]**:
```json
{
  "success": true,
  "error": null,
  "dry_run": true,
  "target_repo": "FOUNDUPS/gotjunk",
  "boundary_analysis": {
    "product_files": 4,
    "core_dependencies": 1,
    "adapters_needed": ["wre_adapter"]
  },
  "exfoliation_gate": {
    "passed": true,
    "checks": {
      "module_boundary_clear": true,
      "contracts_explicit": true,
      "runtime_testable": true,
      "deploy_surface_understood": true,
      "shared_deps_adapter_level": true,
      "claw_can_participate": true
    }
  },
  "adapters_dry_run": true,
  "manifest_signed": true
}
```

### What This Proves

- The builder constructs without crashing when LM Studio is absent.
- FAM breadcrumb sink and MCP Bridge perception layer attach successfully on this host.
- `analyze_boundary()` correctly classifies product vs. core imports and identifies the WRE adapter requirement.
- `check_exfoliation_gate()` returns a fully-populated `ExfoliationGate` with all six structured booleans.
- `extract_foundup()` in dry-run mode produces a well-formed report including a signed manifest, **without** writing adapters to disk and **without** invoking `git filter-repo` or any subprocess.

### What This Does NOT Prove

- That `run_hermes_extraction()` (the live Hermes CLI invocation path) works end-to-end. That path requires LM Studio + Qwen + the vendored `hermes-agent` CLI and was deliberately not invoked.
- That a real GitHub repo can be created at `FOUNDUPS/gotjunk`.
- That `git filter-repo` would succeed on the actual git history.
- That deployment to Firebase Hosting / Cloud Run would succeed.

These remain unverified pending Phase 2.

---

## Kosei Gate — Before & After Deploy-Surface Tightening

### Evidence Gathered

`modules/foundups/kosei/foundup_manifest.json`:
```json
{
  "foundup_id": "kosei",
  "entry_url": "https://foundupscom.web.app/kosei/app/",
  "launch_readiness": "ready",
  ...
}
```

`modules/foundups/kosei/app/index.html` exists.
`public/kosei/app/index.html` exists at repo root (Firebase Hosting deploy artifact).

No `Dockerfile`, `cloudbuild.yaml`, `firebase.json`, or `deployment/` exist inside `modules/foundups/kosei/` — which is why the prior detector falsely failed deploy-surface understanding.

### Detector Change (Narrow)

`HermesFoundUpBuilder._detect_deploy_surface(full_path)` now returns `True` if **any** of the following hold:

1. **Container/CI** (legacy): `Dockerfile`, `cloudbuild.yaml`, `firebase.json`, or `deployment/` exists in-module.
2. **In-module web app**: `app/index.html` or `frontend/index.html` exists.
3. **Manifest-declared verified deployment**: `foundup_manifest.json` parses, has non-null `entry_url`, **and** `launch_readiness == "ready"`.

This is intentionally narrow:
- The manifest path requires **both** `entry_url` and `launch_readiness=ready` (incomplete manifests do not pass).
- The web-app paths require an actual `index.html`, not just a directory.
- Container/CI behaviour is unchanged.

### Result (post-fix)

`check_exfoliation_gate("modules/foundups/kosei")`:
```json
{
  "passed": true,
  "module_boundary_clear": true,
  "contracts_explicit": true,
  "runtime_testable": true,
  "deploy_surface_understood": true,
  "shared_deps_adapter_level": true,
  "claw_can_participate": true
}
```

Kosei's gate now passes because:
- Contracts present (README, INTERFACE, ROADMAP, ModLog).
- Tests present (`modules/foundups/kosei/tests/test_*.py`).
- Deploy surface recognised via manifest evidence (`entry_url` + `launch_readiness=ready`) **and** in-module `app/index.html`.
- No core imports to other monorepo modules → no adapters needed → shared-deps check trivially passes.

This does **not** mean Kosei should be extracted now — it means the gate no longer falsely blocks based on a missing `firebase.json` that lives at repo root rather than in-module. Real extraction readiness still requires Phase 2 verification (git history scope, secret scan, adapter wiring).

---

## Verification Commands

```bash
# AST sanity
python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8')) for p in pathlib.Path('modules/foundups/agent/src').glob('*.py')]; print('ast ok')"
# → ast ok

# Test suite
python -m pytest modules/foundups/agent/tests -q
# → 18 passed in 5.27s

# Dry-run proof (see GotJunk section above for full output)
HERMES_BUILDER_SECURITY_GATE=0 HERMES_BUILDER_DRY_RUN=1 python -c "..."
```

---

## HoloIndex

**Command:**
```
python holo_index.py --search "Hermes FoundUp Builder extract_foundup exfoliation gate dry run adapter generation" --limit 3
```

**Top hits (6 returned, code+wsp):**
1. `modules\foundups\simulator\adapters\fam_bridge.py` (code)
2. `public\js\firebase-runtime-config.js` (code)
3. `public\js\foundup-cube.js` (code)
4. `modules\foundups\docs\WSP_SKILL_BUILDER.md` (wsp)
5. `WSP_framework\src\WSP_106_FoundUp_API_Gateway_Protocol.md` (wsp)
6. `WSP_framework\src\WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md` (wsp)

Note: HoloIndex emitted a `sentence_transformers` missing-dependency warning, so the search ran in lexical-only mode. No semantic-rerank match for `hermes_adapter.py` itself — Hermes builder code is recent and may need a fresh index. The hits above are still useful pointers for related FAM/manifest/build context. The builder code was located via direct file read using paths supplied in the worker brief.

---

## Truth Summary

| Claim | Result | Notes |
|---|---|---|
| GotJunk dry-run extraction succeeds | **TRUE** | All 6 gate checks pass, manifest signed, adapters synthesized in-memory only. |
| Kosei gate now passes | **TRUE** | After narrow deploy-surface detector tightening based on real manifest evidence. |
| LM Studio available | **FALSE** | `LM Studio not running at localhost:1234` — reported honestly, not hidden. |
| FAM breadcrumbs available | **TRUE** | FAM Daemon attached at builder init. |
| MCP Bridge available | **TRUE** | MCP Bridge v1.4 perception layer attached at builder init. |
| Live extraction performed | **FALSE** | Strictly dry-run. WSP 97 honoured. |
| External repo mutated | **FALSE** | No git filter-repo, no GitHub API calls, no push. |
| Tests added & passing | **TRUE** | 18/18 pass in 5.27s. |
| Documentation updated | **TRUE** | INTERFACE.md, ModLog.md, tests/README.md, this briefing. |

---

## Reproducibility

To reproduce this proof on a fresh checkout:

```bash
# 1. Sanity check
python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8')) for p in pathlib.Path('modules/foundups/agent/src').glob('*.py')]; print('ast ok')"

# 2. Run the test suite
python -m pytest modules/foundups/agent/tests -q

# 3. Reproduce the GotJunk dry-run
HERMES_BUILDER_SECURITY_GATE=0 HERMES_BUILDER_DRY_RUN=1 python -c "
import json
from pathlib import Path
from modules.foundups.agent.src.hermes_adapter import HermesFoundUpBuilder
builder = HermesFoundUpBuilder(repo_root=Path('.'))
print(json.dumps(builder.extract_foundup('modules/foundups/gotjunk', target_org='FOUNDUPS'), indent=2, default=str))
"
```

Differences you may observe:
- `LM Studio not running at localhost:1234` will become `available: true` if LM Studio + `qwen-coder-7b` are loaded locally. Behaviour for everything else is unchanged.
- FAM Daemon attachment will be `False` if the FAM SQLite store is unavailable; the builder still constructs and dry-run still succeeds (validated by `test_init_does_not_crash_when_fam_unavailable`).

---

## Out-of-Scope (Phase 2 Candidates)

- Real extraction with `git filter-repo` against a temp clone (still no remote push).
- Live Hermes CLI invocation via `run_hermes_extraction()` (requires LM Studio + Qwen).
- Wiring `/api/v1/hermes/extract` per WSP 106 §8.
- Secret-scan integration before any real extraction.
- Validation that `0102_high` permission gate (per WSP 106 §8.1) is enforced.

---

*Worker DD reporting in. Phase 1 contract-level proof complete. No live extraction performed. No external mutation.*
