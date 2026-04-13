# TestModLog

====================================================================
## 2026-04-13 - Local LLM Backend Adapter Layer Coverage
- Command:
  - `python -m pytest modules/infrastructure/shared_utilities/tests/test_local_llm_backends.py -v`
- Status: PASS
- Result: `17 passed in 0.44s`
- Scope:
  - TestIsLMStudioAvailable: API detection (3 tests)
  - TestResolverBackendSelection: LM Studio vs llama_cpp fallback (4 tests)
  - TestSingletonCacheReuse: Cache hit, force_reinit (3 tests)
  - TestCompatibilityMethods: generate_response, __call__ (4 tests)
  - TestLlamaCppFallbackPath: Direct llama_cpp backend (3 tests)
- Coverage:
  - `local_llm_backends.py`: LocalLLMBackend, LlamaCppBackend, LMStudioBackend
  - `local_llm_resolver.py`: resolve_qwen_backend, resolve_gemma_backend
  - `ai_engine_singletons.py`: Singleton cache behavior
- WSP References: WSP 77 (Agent Coordination), WSP 91 (Observability)
====================================================================

====================================================================
## TESTMODLOG - [+INIT]
- Summary: Documented shared_utilities test history with an initial TestModLog entry.
- Notes: Placeholder notes current absence of automated coverage while keeping WSP compliance.
- WSP References:
  - WSP 22
  - WSP 34
  - WSP 50
====================================================================

====================================================================
## 2026-03-07 - Managed env loader coverage
- Command:
  - `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/infrastructure/shared_utilities/tests/test_env_managed.py -q`
- Status: PASS
- Result: `1 passed, 2 warnings`
- Scope:
  - Validates duplicate resolution policy (last wins)
  - Validates orphan/non-parseable line preservation in generated managed env
- Additional verification:
  - `.\.venv\Scripts\python.exe -m py_compile main.py modules/infrastructure/shared_utilities/env_managed.py`
  - Status: PASS
====================================================================

====================================================================
## 2026-03-07 - Env exposure hardening (no disk copy)
- Command:
  - `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/infrastructure/shared_utilities/tests/test_env_managed.py -q`
- Status: PASS
- Result: `2 passed, 2 warnings`
- Scope:
  - Verifies in-memory managed env path.
  - Verifies stale `.env.managed` purge behavior.
- Additional verification:
  - `.\.venv\Scripts\python.exe -c "from pathlib import Path; from modules.infrastructure.shared_utilities.env_managed import load_managed_env; print(load_managed_env(Path('.').resolve(), override=False, regenerate=True)['mode'])"`
  - Result: `in_memory`
====================================================================

====================================================================
## 2026-03-07 - Env hygiene startup preflight verification
- Command:
  - `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest modules/infrastructure/shared_utilities/tests/test_env_managed.py -q`
- Status: PASS
- Result: `2 passed, 2 warnings`
- Additional verification:
  - `python -c "import os; from pathlib import Path; import main; os.environ['FOUNDUPS_ENV_PREFLIGHT']='1'; os.environ['FOUNDUPS_ENV_PREFLIGHT_ENFORCED']='1'; os.environ['FOUNDUPS_ENV_DUPLICATE_KEYS']='2'; os.environ['FOUNDUPS_ENV_ORPHAN_LINES']='1'; print(main.run_env_hygiene_preflight(Path('.')))"`.
  - Result: emits `[ENV-HYGIENE] preflight=WARN ...` and blocks startup (`False`) when enforcement is enabled.
  - `python -c "import os; from pathlib import Path; import main; [os.environ.pop(k,None) for k in ['FOUNDUPS_ENV_DUPLICATE_KEYS','FOUNDUPS_ENV_ORPHAN_LINES','FOUNDUPS_ENV_DUPLICATE_OVERWRITES','FOUNDUPS_ENV_MODE','FOUNDUPS_ENV_ACTIVE_FILE']]; print(main.run_env_hygiene_preflight(Path('.')))"`.
  - Result: fallback `legacy_scan` path works when managed stats are absent.
====================================================================
