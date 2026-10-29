# LM_STUDIO_DEPENDENCY_BOUNDARY_DOC_AND_GATE_PHASE1

> **Superseded in part on 2026-08-22:** the non-launch boundary remains valid,
> but OpenAI-compatible `/v1/models` presence is not residency proof when LM
> Studio JIT loading is enabled. Exact current behavior is governed by
> `REDDOG_LM_STUDIO_MODEL_LIFECYCLE_HARDENING_PHASE1.md` and native
> `/api/v1/models` `loaded_instances` evidence.

**Slice**: `fix/lm-studio-dependency-boundary-doc-and-gate-phase1`
**Operating protocols**: WSP_00 (Zen State), WSP_97 (Truthful state distinction)
**Internal Review Verdict**: READY for the original dependency-boundary slice;
the lifecycle audit named above is now authoritative for residency and managed
execution behavior.

---

## 1. Mission + Scope

Make LM Studio a clearly bounded **optional/local** dependency. The HoloIndex
cold-model timeout work (#730) removed SentenceTransformer false negatives, but
the broader local-model stack (Qwen / Gemma / UI-TARS via LM Studio) could still
degrade silently or warn ambiguously when LM Studio is absent.

This slice **documents and gates** LM Studio usage. It:

- Makes LM Studio absence **explicit and operator-actionable** instead of a
  silent `None` return.
- Guarantees the resolver layer is **probe-only** (never launches LM Studio).
- Keeps the **launch** behavior confined to the explicit dependency launcher.

**In scope (locked after discovery)**:
- `modules/infrastructure/shared_utilities/local_llm_resolver.py` (additive gate)
- `modules/infrastructure/shared_utilities/tests/test_lm_studio_dependency_boundary.py` (NEW)
- `modules/infrastructure/shared_utilities/ModLog.md` / `tests/TestModLog.md`
- this audit doc

**Out of scope (proven by discovery)**:
- `main.py` — does **not** probe or launch LM Studio at menu boot (grep: no
  matches for `lm_studio`/`ensure_dependencies`/`launch_lm_studio`). Not touched.
- `dependency_launcher/dae_dependencies.py` — already the correct explicit launch
  site; no behavior change.
- HoloIndex timeout defaults (#730), OBS startup boundaries (#720/#721) — untouched.

---

## 2. Predecessor Citations

- **#720** OBS secret logging guard
- **#721** main-menu startup boundary
- **#728** HoloIndex knowledge full-body chunking
- **#730** HoloIndex cold model timeout boundary
- **#732** local-first MoltBot config pin (base for this slice)

---

## 3. HoloIndex Retrieval Evaluation

Queries run (mandatory discovery):
1. `LM Studio local model resolver fallback`
2. `localhost 1234 local_llm_resolver qwen gemma`
3. `AutoModeratorDAE LM Studio dependency launcher`

| Dimension | Evaluation |
|-----------|------------|
| Noise | Low. Top code hits were the exact target files (`local_llm_resolver.py`, `local_llm_backends.py`, `local_model_selection.py`, `dae_dependencies.py`). |
| Ordering | Correct. Query 1/2 surfaced shared_utilities resolver first; query 3 surfaced `dae_dependencies.py` first. |
| Missing artifacts | None critical. `ai_engine_singletons.py` (caller) was not top-ranked but found via grep on `local_llm_resolver` imports. |
| Staleness risk | Low. Knowledge hits (Papers/*) were tangential and ignored; code hits matched current tree. |
| Duplication | None. Single resolver + single backend module; launch lives only in `dae_dependencies.py`. |

Grep confirmed the launch site is unique: `launch_lm_studio` /
`subprocess.Popen([lm_studio_path])` exists only in `dae_dependencies.py`.

---

## 4. LM Studio Dependency Matrix

| Subsystem | Current behavior | Requires LM Studio? | Fallback behavior | Operator action |
|-----------|------------------|---------------------|-------------------|-----------------|
| Qwen reasoning (`resolve_qwen_backend` / `get_qwen_engine`) | Probe LM Studio; if reachable + model loaded → `LMStudioBackend`; else llama.cpp GGUF | **OPTIONAL** | `LlamaCppBackend` via `model_path` (GGUF) | None if reachable; else provide GGUF `model_path` or start LM Studio via launcher |
| Gemma pattern matching (`resolve_gemma_backend` / `get_gemma_engine`) | Same as Qwen (CPU-only GGUF fallback) | **OPTIONAL** | `LlamaCppBackend` via `resolve_triage_model_path` | Same as Qwen |
| UI-TARS vision (`auto_moderator_dae` Phase -2 → `ensure_dependencies(require_lm_studio=True)`) | Explicit launch via `dae_dependencies.launch_lm_studio`; absent → DOM-only mode | **OPTIONAL (no GGUF fallback)** — degrades to DOM-only, not a hard failure | Vision-less DOM-only engagement | Start LM Studio via dependency launcher / load UI-TARS model |
| `is_lm_studio_available()` probe (`local_llm_backends`) | Bounded native HTTP GET to the normalized loopback endpoint `/api/v1/models`; requires exact native inventory evidence | N/A (pure probe) | N/A | N/A |
| Dependency launcher (`dae_dependencies.launch_lm_studio`) | `subprocess.Popen` LM Studio, waits ≤120s, then `load_all_models()` | This **is** the launch path (explicit, operator/DAE-initiated) | N/A | This is the sanctioned launch entry point |
| `main.py` menu boot | No LM Studio probe or launch | **NO** | N/A | N/A |

**Conclusion**: No subsystem *hard-requires* LM Studio. Qwen/Gemma fall back to
llama.cpp; UI-TARS degrades to DOM-only. LM Studio is uniformly OPTIONAL.

---

## 5. Pre-State Failure / Warning Map

| Path | Pre-state issue |
|------|-----------------|
| `resolve_qwen_backend` / `resolve_gemma_backend` (LM Studio absent + `model_path` provided) | Silently jumped to llama.cpp with **no message stating why** LM Studio was skipped — looked like LM Studio was simply not chosen. |
| `resolve_*_backend` (LM Studio absent + `model_path=None`) | `logger.warning("No Qwen backend: LM Studio unavailable and no model_path for fallback")` — accurate but **not operator-actionable** (no remedy stated). |
| `ai_engine_singletons.get_*_engine` | Returns `None` with `"no backend available"` — **silent degradation**; caller cannot distinguish "LM Studio absent" from "GGUF missing" or get a remedy. |
| Required-LM-Studio callers (e.g. UI-TARS) | No **named** unavailable state to branch on — would have to inspect logs or a bare `None`. |

---

## 6. Post-State Gate Map

All additions are in `local_llm_resolver.py` and are **probe-only / additive**
(no existing signature or return type changed):

| New symbol | Purpose | Launches LM Studio? |
|------------|---------|---------------------|
| `LocalLLMAvailability` (Enum) | Named states: `LM_STUDIO_SERVER_REACHABLE` / `FALLBACK_LLAMA_CPP` / `UNAVAILABLE`; reachability is not model residency | No |
| `probe_backend_availability(model_path=None)` | Probe-only classifier (HTTP probe + GGUF filesystem check) | No |
| `operator_action_for(status)` | Operator-actionable guidance string per state | No |
| `LMStudioUnavailableError` | Named error for paths that strictly require LM Studio | No |
| `require_lm_studio_backend(model_id, base_url=None)` | Required-path resolver; raises the named error w/ remedy instead of `None` | No |

Resolver messaging upgraded:
- LM Studio absent + fallback → **INFO** clearly states "using local GGUF
  fallback via llama.cpp … resolver does not auto-launch it."
- LM Studio absent + no fallback → **WARNING** with operator remedy (start via
  launcher or provide `model_path`).

The original happy/fallback selection remains, but its LM Studio evidence is
now deliberately stronger: the probe uses native inventory, propagates the
configured base URL and token, and distinguishes server reachability from
exact model residency. Managed RedDog calls additionally use the separately
documented lifecycle authority.

---

## 7. Explicit Non-Launch Boundary

- `local_llm_resolver.py` and `local_llm_backends.py` **never** import
  `subprocess`, `dependency_launcher`, or `launch_lm_studio`. Verified by test
  (`test_resolver_does_not_import_launch_symbols`) and by patching
  `subprocess.Popen` and asserting it is never called
  (`test_resolve_never_calls_subprocess`, `test_require_never_calls_subprocess`).
- The **only** LM Studio launch site remains
  `dependency_launcher.dae_dependencies.launch_lm_studio`, invoked exclusively
  from the explicit DAE startup path
  (`auto_moderator_dae` Phase -2, gated by `YT_DEPS_AUTO_LAUNCH`) /
  `ensure_dependencies(require_lm_studio=...)`.

---

## 8. Test Matrix

File: `modules/infrastructure/shared_utilities/tests/test_lm_studio_dependency_boundary.py`

| # | Requirement | Test(s) |
|---|-------------|---------|
| 1 | LM Studio absent + fallback → clear fallback state/message | `test_fallback_state_when_lm_studio_absent_but_gguf_exists`, `test_fallback_operator_action_states_llama_cpp_and_non_launch`, `test_resolver_logs_clear_fallback_when_lm_studio_absent` |
| 2 | LM Studio absent + required path → named error + operator action | `test_require_raises_named_error_when_lm_studio_absent`, `test_require_raises_when_reachable_but_model_not_loaded`, `test_unavailable_operator_action_is_actionable` |
| 3 | LM Studio available → happy path preserved | `test_lm_studio_ready_when_probe_succeeds`, `test_require_returns_backend_when_available`, `test_resolve_qwen_uses_lm_studio_when_available`, `test_resolve_gemma_falls_back_to_llama_cpp_when_lm_studio_absent` |
| 4 | Resolver does not call dependency launcher / subprocess | `test_resolve_never_calls_subprocess`, `test_require_never_calls_subprocess`, `test_resolver_does_not_import_launch_symbols` |
| 5 | No live LM Studio, no network, no `.env` reads | All tests patch `is_lm_studio_available` (the sole network site); no `.env` access anywhere in the suite |
| 6 | Existing DAE dependency behavior still routes through explicit launcher | `test_launch_lives_in_dependency_launcher`, `test_ensure_dependencies_still_gates_lm_studio` |

**Run**:
`python -m pytest modules/infrastructure/shared_utilities/tests/test_lm_studio_dependency_boundary.py modules/infrastructure/shared_utilities/tests/test_local_llm_backends.py -v`
**Current result (2026-08-22)**: `46 passed in 1.67s`.

---

## 9. Internal Review Verdict

**READY for its original scope.** The named states, probe-only classifier,
required-path error, non-launch boundary, and `main.py` boundary remain valid.
Native inventory/authentication and managed model behavior are now governed by
`REDDOG_LM_STUDIO_MODEL_LIFECYCLE_HARDENING_PHASE1.md`.

---

## 10. WSP_97 Truth Boundary Checklist

The 20 rows below record the original dependency-boundary slice. They are not
a substitute for the current lifecycle-hardening checklist and release gate.

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | LM_STUDIO_DEPENDENCY_BOUNDARY_ONLY | PASS | Only resolver gate + tests + docs changed; matrix scoped to LM Studio dependency. |
| 2 | NO_AUTO_LAUNCH_LM_STUDIO | PASS | No `subprocess`/launch in resolver; `subprocess.Popen` patched and asserted never called. |
| 3 | LOCAL_LLM_RESOLVER_PROBES_ONLY | PASS | `probe_backend_availability` does HTTP probe + filesystem check only; resolver imports no launch symbols (`test_resolver_does_not_import_launch_symbols`). |
| 4 | NO_MODEL_BEHAVIOR_CHANGE | SUPERSEDED | True for the original slice. The later lifecycle-hardening slice intentionally strengthened native inventory, authentication, capacity, lease, and managed unload behavior; see its authoritative audit. |
| 5 | NO_HOLOINDEX_TIMEOUT_CHANGE | PASS | No edit to `holo_index/core/*`; timeout defaults from #730 untouched. |
| 6 | NO_OBS_BOUNDARY_CHANGE | PASS | `dae_dependencies.launch_obs` / OBS paths from #720/#721 untouched. |
| 7 | NO_MAIN_MENU_STARTUP_REGRESSION | PASS | `main.py` not touched; grep confirms it never probes/launches LM Studio. |
| 8 | NO_LIVE_LM_STUDIO_IN_TESTS | PASS | All tests patch `is_lm_studio_available`; no live API used. |
| 9 | NO_NETWORK_CALL_IN_TESTS | PASS | Sole network site (`is_lm_studio_available`) mocked in every test. |
| 10 | NO_DOTENV_READ_IN_TESTS | PASS | No `.env` access in suite; no `load_dotenv`/env-file reads. |
| 11 | NO_REAL_SECRET_VALUES | PASS | No secrets referenced; only `localhost:1234` and model ids. |
| 12 | NO_DEPENDENCY_CHANGE | PASS | No `requirements.txt`/lockfile change; uses stdlib `enum`. |
| 13 | NO_CI_CHANGE | PASS | No workflow/CI files touched. |
| 14 | NO_WSP_MUTATION | PASS | No `WSP_framework`/`WSP_knowledge` protocol files edited. |
| 15 | NO_REGISTRY_MUTATION | PASS | No registry/SKILLz/manifest files edited. |
| 16 | NO_MANIFEST_MUTATION | PASS | No manifest files edited. |
| 17 | NO_PUBLIC_SURFACE_MUTATION | PASS | No existing signature/return type changed; only **additive, non-breaking** new symbols introduced (required by dispatch). |
| 18 | NO_CABR_READY | PASS | No CABR/valuation logic touched. |
| 19 | NO_PAYOUT_READY | PASS | No payout logic touched. |
| 20 | NO_DAO_ACTIVATION | PASS | No DAO activation logic touched. |
