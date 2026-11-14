# Hermes Agent Runtime Install + Import-Path Drift Audit (Phase 1)

**Slice:** HERMES_AGENT_RUNTIME_INSTALL_AND_PATH_AUDIT_PHASE1
**Worker-Lane:** W6 - **Author:** 0102 (WSP_00 zen state, WSP_97 Truth Boundary discipline)
**Type:** READ-ONLY mapping audit. No code, tests, import edits, or worktree mutation. ONE doc.
**Base:** origin/main @ 4b222fd03 (all line numbers re-verified live).
**Method:** direct read-only probes (importlib.find_spec, Path, code reads, read-only WSL inspection) +
an independent adversarial critic. This is a deterministic path-resolution mapping; it does NOT fix the
drift - it classifies it and recommends a remediation shape.

---

## 1. Mission and Scope

Map the real Hermes install/runtime against the repo's imports BEFORE any code change. Confirm the
import-path drift (`vendor.hermes_agent` underscore vs `vendor/hermes-agent` hyphen), determine present
reachability/safety, disentangle the WSL-installed Hermes runtime from the repo-vendored delegate tool,
and recommend (not implement) a remediation. One verdict from the scheme in Section 9.

---

## 2. Predecessors

| PR / Item | Relationship |
|-----------|--------------|
| #745 HERMES_NOUS_AGENT_DELEGATE_BINDING_AUDIT | Found WRE->delegate_task RUNTIME_DEPENDENCY_MISSING + IMPORT_PATH_DRIFT; this slice pins it to exact lines |
| #748 RedDog capture | Nous Hermes 0.15.1 in WSL Ubuntu at /home/undaodu/.hermes (Docker terminal backend) |
| #755 closeout review | Flagged the stale nav comment `foundup_job_consumer.py:27` |

---

## 3. FOLLOW-WSP Evidence (methodology)

- **HoloIndex (step 2):** queried `hermes delegate_task binding import path drift vendor hermes-agent`
  (returned matches; the #745 predecessor is the governing prior audit). For a deterministic
  path-resolution question, discovery was carried out primarily via direct read-only probes (below),
  which are the appropriate evidence for import resolution.
- **Probes run (read-only):** `importlib.util.find_spec` on both module names; `Path(...).exists()` +
  text inspection of `delegate_tool.py`; `git ls-files` / `.gitmodules` / `git submodule status` for the
  vendor submodule; `git grep` reachability of `HERMES_DELEGATE_ENABLED` / `_lazy_import_delegate_task`;
  read-only WSL inspection (`hermes --version`, filename-only `find ~/.hermes`).
- **Adversarial critic:** an independent agent re-verified every fact and attempted to construct a
  reachable crash path (Section 9). NAVIGATION.py consulted for module locations.

---

## 4. Import-vs-Filesystem Map (Q1)

**Reasoning Summary:** the lazy import targets an UNDERSCORE module that does not exist; the real artifact
is a HYPHEN submodule directory that is not addressable by a dotted import statement.

| Item | Evidence | Classification |
|------|----------|----------------|
| Lazy import | `hermes_job_executor.py:623` `from vendor.hermes_agent.tools.delegate_tool import delegate_task` | IMPORT_PATH (underscore) |
| Path refs | `:31` (docstring), `:719`, `:739`, `:1733`, `:2069` use `vendor/hermes-agent` | FILESYSTEM_PATH / DOCSTRING (hyphen) |
| find_spec("vendor.hermes_agent...") | `ModuleNotFoundError: No module named 'vendor.hermes_agent'` | import BROKEN |
| find_spec("vendor.hermes-agent...") | resolves to a SourceFileLoader at the real file (namespace-package walk) - but a hyphen is NOT a writable Python identifier, so `import` cannot use it | not addressable by statement |
| On-disk file | `vendor/hermes-agent/tools/delegate_tool.py` exists (~46-47KB, executable), defines `delegate_task` | present |
| vendor status | git SUBMODULE (`.gitmodules` url `FOUNDUPS/hermes-agent.git`), gitlink pinned `d1d425e9` (~v2026.4.13), populated on this checkout | submodule |
| `vendor/__init__.py` | ABSENT (vendor resolves only as a namespace package) | not a package |
| `vendor/hermes_agent` underscore dir / symlink | ABSENT (no bridge) | none |

**Q1 conclusion:** the `:623` import cannot resolve today. The underscore module does not exist; the real
code lives in a hyphen submodule dir that no dotted `import` statement can name.

---

## 5. Lazy-Import Reachability + Path-vs-Import Disagreement (Q2)

**Reasoning Summary:** the broken import is wrapped in try/except, reached only behind a feature gate, and
its result is never executed - so it degrades gracefully rather than crashing.

- `_lazy_import_delegate_task` (`:610-641`): `try: <:623 import>` ... `except ImportError: return False`
  (`:628-634`), broad `except Exception: return False` (`:635-641`). The broken import is CAUGHT.
- Single call site `:1728` `if not self._lazy_import_delegate_task():`. On failure (broken import) it
  returns **`BLOCKED_IMPORT_UNAVAILABLE`** (`:1730/:1746`). [Correction vs the first-pass draft: it does
  NOT reach `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` `:1754` - that status is reached ONLY when the
  import SUCCEEDS, which the executor tests prove by mocking `_delegate_task_fn` to a MagicMock.]
- `self._delegate_task_fn` is assigned (`:625`) on success but is **never invoked anywhere** - even a
  working import would not execute delegate_task in Phase 1.
- **Path-vs-import disagreement:** `:739`/`:2069` `Path("vendor/hermes-agent/...")` (hyphen, exists, used
  only as `str()`/`.exists()` for evidence JSON, never imported) vs `:623` import (underscore, fails).
  The module header `:31` even says "Imports: vendor/hermes-agent/..." (hyphen) while `:623` uses
  underscore - an internal contradiction.

---

## 6. WSL Runtime vs Repo Vendor Map (Q3)

**Reasoning Summary:** there are TWO distinct Hermes artifacts; the repo import targets the vendored one
(broken), and the WSL install is irrelevant to that import.

| Artifact | Location | Identity | Wired to `:623`? |
|----------|----------|----------|------------------|
| Repo-vendored delegate tool | `vendor/hermes-agent/tools/delegate_tool.py` (submodule pinned `d1d425e9`, ~v2026.4.13) | FOUNDUPS/hermes-agent submodule | YES (the intended source per `:623`/`:739`) - but the import path is broken |
| WSL-installed Hermes runtime | `/home/undaodu/.local/bin/hermes`; project `/home/undaodu/.hermes/hermes-agent` | Hermes Agent **v0.15.1** (2026.5.29), Py 3.11.15 (cli.py/run_agent.py/mcp_serve.py + config.yaml/SOUL.md/.env present) | NO - the repo imports from `vendor`, never from `~/.hermes` |

**Q3 conclusion:** intended `delegate_task` source = the **repo-vendored** tool. The WSL Hermes is a
SEPARATE install (same upstream project, different version `v0.15.1` vs submodule `~v2026.4.13`, different
location), not referenced by the repo import. The conflation is at the shared name "hermes-agent" only.
(WSL inspection was performed read-only - `hermes --version` + filename-only listing; no secret/.env
contents read.)

---

## 7. Legacy-vs-Live Executor Binding (Q4)

**Reasoning Summary:** the live consumer binds the new executor; the legacy executor is dead on this path
and only survives in a stale comment.

- Live binding: `foundup_job_consumer.py:425-429` `from modules.infrastructure.wre_core.src.hermes_job_executor
  import execute_foundup_job, ...`; called `:439`.
- Stale comment: `foundup_job_consumer.py:27` "Uses: hermes_foundup_job_executor.py" names the legacy
  `modules/foundups/agent/src/hermes_foundup_job_executor.py`.
- Legacy executor: ZERO production (non-test) imports anywhere; dead on the live path. (It does not import
  `vendor.hermes_agent` either.)

---

## 8. Present Blast Radius / Safety (Q5)

**Reasoning Summary:** the drift is benign today and, importantly, SILENT - no test exercises the real
import.

- **Doubly gated in production:** `is_hermes_delegation_enabled()` defaults `"0"` (`:93`) -> SIMULATED at
  `:1680` before `:1728`; and the production singleton `get_executor()` runs `dry_run=True` (`:2250`) ->
  SIMULATED at `:1700` before `:1728`. The broken `:623` is unreachable on every production path.
- **Worst reachable case** (a hypothetical `HermesJobExecutor(dry_run=False)` + `HERMES_DELEGATE_ENABLED=1`;
  no such production caller exists - only test files) returns `BLOCKED_IMPORT_UNAVAILABLE` gracefully. No
  exception, no live execution.
- **Silent gap:** the executor tests MOCK `_lazy_import_delegate_task`/`_delegate_task_fn`, so they pass
  whether or not `:623` resolves. No test fails on the real broken import -> the drift is undetected by CI.

---

## 9. Verdict

### DRIFT_CONFIRMED_BENIGN_TODAY

The underscore-vs-hyphen import drift is real and currently un-resolvable, but fully contained: caught by
try/except (`:628`), reached only behind a default-off feature flag (and a dry-run singleton), result
never executed, and worst-case degrades to `BLOCKED_IMPORT_UNAVAILABLE`. It is NOT reachable (no
propagation/crash) - so not DRIFT_CONFIRMED_REACHABLE; the import genuinely does NOT resolve as a statement
- so not NO_DRIFT; WSL facts were inspectable read-only - so not INCONCLUSIVE_WSL_DEPENDENCY. The drift
becomes ACTIVE the day someone enables real delegation expecting `:623` to bind - it silently never will.

**Adversarial critic: UPHELD (high confidence ~0.95).** The critic re-verified every fact, corrected the
failure status code (`BLOCKED_IMPORT_UNAVAILABLE`, not `BLOCKED_REAL_DELEGATION`), confirmed the single
guarded call site, confirmed `_delegate_task_fn` is never invoked, confirmed no top-level/module-load
import of `vendor.hermes_agent`, and confirmed the CI/empty-submodule edge still does not crash. No
reachable propagation exists.

---

## 10. Remediation Shape (no code here) - options compared

| Option | Assessment |
|--------|------------|
| **A. Rename/mirror vendored dir to importable `vendor/hermes_agent`** | UNSOUND as stated: it is a SUBMODULE - renaming the gitlink requires `.gitmodules` surgery + moving the submodule; and a hyphen dir is never importable by dotted path regardless, so the dir name is not the real blocker. A duplicate importable mirror duplicates a submodule (drift-prone). |
| **B. importlib `spec_from_file_location` from the hyphen dir** | SOUNDEST for the eventual fix: load `vendor/hermes-agent/tools/delegate_tool.py` by path (the path the code already proves exists at `:739/:2069/:2099`); no rename/`.gitmodules` surgery; resolves the underscore-vs-hyphen impossibility directly. Caveat: that file relies on sibling imports, so the loader may need the submodule root on `sys.path`. |
| **C. Bind to the WSL/installed Hermes runtime** | UNSOUND for the repo path: couples repo execution to a per-machine out-of-tree install (`~/.hermes`, v0.15.1 != pinned submodule), non-reproducible in CI. |
| **D. Doc/comment repair only** | Defensible TODAY (delegation intentionally off + contained): fix the `:31` docstring drift and the stale `:27` nav comment. But it leaves a latent silent break that will mislead whoever flips the flag in Phase 2 - acceptable ONLY paired with a regression test that exercises the REAL `:623` import (current tests mock it). |

**Recommendation:** **D now** (doc-hygiene: correct `:31` + `:27`) + **B at Phase-2** when real delegation is
implemented, accompanied by a regression test that drives the REAL import (closing the silent-CI gap from
Section 8). Named follow-up slice: **HERMES_DELEGATE_IMPORT_PATH_REMEDIATION_PHASE1** (code; gated on the
decision to enable real delegation).

---

## 11. Internal Review Verdict

**READY.** All five questions answered with re-verified file:line evidence: Q1 import broken (underscore
module absent; hyphen submodule not statement-addressable); Q2 reached only behind the gate and caught ->
`BLOCKED_IMPORT_UNAVAILABLE`, Path-vs-import disagree; Q3 WSL runtime (v0.15.1) distinct from the repo
submodule (~v2026.4.13), repo targets the vendored tool; Q4 live binds new executor, legacy dead, `:27`
stale; Q5 doubly-gated, benign, but silent (tests mock the import). Verdict DRIFT_CONFIRMED_BENIGN_TODAY,
critic-UPHELD. NO_OVERCLAIM: no remediation asserted as proven; WSL facts inspected read-only, not assumed.
Decision-only - no code authorized here.

---

## 12. WSP_97 Truth Boundary Checklist

Declared items: 23 - Rows: 23 - All YES.

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | READ_ONLY_MAPPING_AUDIT | YES | Only this doc written; all probes read-only |
| 2 | NO_CODE_CHANGE | YES | No .py modified |
| 3 | NO_IMPORT_EDIT | YES | `:623` and all imports untouched |
| 4 | HOLOINDEX_UTILIZED | YES | Sec 3 (query run; #745 predecessor governing) |
| 5 | CURRENT_MAIN_LINE_NUMBERS_REVERIFIED | YES | All lines re-derived on 4b222fd03 |
| 6 | WSL_VS_REPO_DISTINGUISHED | YES | Sec 6 (two distinct artifacts mapped) |
| 7 | NO_OVERCLAIM | YES | No remediation claimed proven; benign-not-fixed |
| 8 | CITES_PR_745 | YES | Sec 2 (+ #748, #755) |
| 9 | NO_DEPENDENCY_CHANGE | YES | No requirements/packaging touched |
| 10 | NO_WSP_MUTATION | YES | No WSP doc changed |
| 11 | NO_CABR_READY | YES | Not touched |
| 12 | NO_PAYOUT_READY | YES | Not touched |
| 13 | NO_DAO_ACTIVATION | YES | Not touched |
| 14 | ASCII_CLEAN_AUDIT | YES | Doc is ASCII-only |
| 15 | NO_SECRET_FILE_CONTENT_PRINTED | YES | WSL listing was filenames only; no .env/config contents read |
| 16 | WSL_READ_ONLY_IF_USED | YES | `hermes --version` + filename `find` only; no setup/auth/launch/write |
| 17 | IMPORT_RESOLUTION_PROBED | YES | Sec 4 (find_spec both names) |
| 18 | VENDOR_PACKAGE_STATUS_RECORDED | YES | Sec 4 (submodule, no __init__.py, pinned d1d425e9) |
| 19 | WSL_RUNTIME_DISTINGUISHED_FROM_REPO_VENDOR | YES | Sec 6 |
| 20 | REACHABILITY_TRACED_TO_HERMES_DELEGATE_ENABLED | YES | Sec 5, Sec 8 (:93 default, :1680/:1700/:1728) |
| 21 | LEGACY_EXECUTOR_BINDING_VERIFIED | YES | Sec 7 (live :425-429; legacy 0 prod imports) |
| 22 | REMEDIATION_OPTIONS_COMPARED | YES | Sec 10 (A/B/C/D) |
| 23 | CRITIC_REVIEW_COMPLETED | YES | Sec 9 (UPHELD, high confidence) |

**WSP 97 Truth Boundary Checklist: 23/23 YES.**

---

*Authored by 0102 (Worker-Lane W6) under WSP_00 zen state and WSP_97 Truth Boundary discipline. Read-only
mapping audit of origin/main @ 4b222fd03. Verdict: DRIFT_CONFIRMED_BENIGN_TODAY - the `vendor.hermes_agent`
(underscore) import at hermes_job_executor.py:623 cannot resolve (real code is the `vendor/hermes-agent`
hyphen submodule), but it is caught, gated, never executed, and degrades to BLOCKED_IMPORT_UNAVAILABLE; the
WSL Hermes v0.15.1 install is a separate artifact not wired to that import. Remediation deferred: doc repair
now + importlib-from-path fix (HERMES_DELEGATE_IMPORT_PATH_REMEDIATION_PHASE1) when real delegation lands.*
