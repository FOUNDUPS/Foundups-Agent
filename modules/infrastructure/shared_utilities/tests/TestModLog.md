# TestModLog

## 2026-08-28 - Windows Runtime Artifact Safety

- Added focused coverage for executable-suffix mode projection, clean file and
  directory stream admission, named file/directory stream rejection, and
  repeated clean-directory calls without handle growth.
- Kept the inherited runtime-artifact test at its exact no-growth baseline by
  extracting all new Windows cases into a WSP_62-bounded sibling.
- Added POSIX lock-root symlink, broad-permission, and private-root falsifiers
  for the pinned machine-wide runtime-lock namespace.
- Cross-module RedDog coverage now drives a valid deep payload past legacy
  Windows `MAX_PATH` through publish, full re-verification, and exact reuse.

## 2026-08-23 - Confined Streaming Digest Proof

- Added stable success, strict identity/bound, replacement/link, content
  mutation, and same-size restored-mtime coverage for the descriptor-confined
  streaming SHA-256 proof. All artifacts are disposable test files.

## 2026-08-22 - LM Studio Lifecycle Hardening

- Added deterministic native inventory, exact lease ownership, node-wide
  capacity, maximum-context, managed load/unload, restart recovery/quarantine,
  load-stage cancellation, authentication, loopback-alias, use-time
  instance/JIT, structural receipt binding, and real cross-process lock coverage.
- Focused cross-module command passed: 121 tests with one platform-specific skip
  across shared utilities, topology proposal/admission, authenticated proposer
  provenance, and runtime-artifact safety under the documented importlib-mode
  command and a unique outside-repository pytest base directory.
- Moved the real Windows spawned-process lock target into an import-stable test
  support module; this preserves the concurrency proof under the documented
  pytest `--import-mode=importlib` suite command.
- No live LM Studio server, model, network, model subprocess, or secret was
  used; the only real child process was the bounded cross-process lock proof.
- The inherited navigation sub-suite remains a separately named collection/
  registry-drift blocker and is not represented as part of this passing gate.

## 2026-08-21 - LM Studio Native Reasoning Control

- Added mocked coverage for native reasoning-off payloads, disabled storage and
  streaming, exact model ID, bounded reads, and allowlisted OpenAI-compatible
  structured/sampling controls.
- Revalidated the same payload/response boundary after WSP 62 decomposition.

## 2026-07-28 - Runtime Artifact Safety WSP 62 Gate

- Added exact no-growth coverage for the inherited runtime-artifact safety
  module and its oversized functions.
- The remediation record expires on 2026-09-30 and names the parity-preserving
  decomposition boundary.

## 2026-07-18 - Runtime Artifact Safety

- Added adversarial path, symlink, hardlink, device-name, root-ancestry,
  Unicode-obfuscated secret, and bounded-redaction coverage.

====================================================================
## 2026-05-30 - LM Studio Dependency Boundary Gate Coverage
- Command:
  - `python -m pytest modules/infrastructure/shared_utilities/tests/test_lm_studio_dependency_boundary.py modules/infrastructure/shared_utilities/tests/test_local_llm_backends.py -v`
- Status: PASS
- Result: `33 passed in 0.76s` (16 new + 17 existing regression-guard)
- Scope (new file `test_lm_studio_dependency_boundary.py`):
  - TestProbeAvailabilityState: named probe-only states (3 tests)
  - TestFallbackMessageClarity: clear fallback INFO + operator action (3 tests)
  - TestRequiredPathNamedError: `LMStudioUnavailableError` w/ operator action (3 tests)
  - TestHappyPathPreserved: LM Studio + llama.cpp fallback unchanged (2 tests)
  - TestResolverProbesOnly: no subprocess / no launch symbols (3 tests)
  - TestDaeLaunchBoundaryIntact: launch still lives in dependency_launcher (2 tests)
- Constraints proven: NO_AUTO_LAUNCH_LM_STUDIO, LOCAL_LLM_RESOLVER_PROBES_ONLY,
  NO_LIVE_LM_STUDIO_IN_TESTS, NO_NETWORK_CALL_IN_TESTS (all probes mocked)
- WSP References: WSP 77 (Agent Coordination), WSP 91 (Observability), WSP 97 (Truthful state distinction)
====================================================================

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
## 2026-07-25 - Stable Descriptor-Confined Runtime Text Reads

- Proved bounded reads use one descriptor and reject oversized input.
- Proved descriptor metadata changes and final-path escapes fail closed.
## 2026-07-28 - Windows Confined Lock Initialization Race

- Added mixed-case, not-yet-created runtime-root and extended-length prefix
  coverage for Windows containment validation.
- Repeated the spawned-process proposal nonce reservation regression 200
  times to prove one accepted reservation and no initialization-write or
  namespace-normalization race.
