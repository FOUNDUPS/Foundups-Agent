# Preserved historical record: TestModLog.md

> Historical/proposal material. This is not a current acceptance receipt, runtime check or instruction to apply old code. The original dates and claimed outcomes below retain their historical scope.

- Original relative path: `modules/communication/moltbot_bridge/tests/TestModLog.md`
- Original PC base: `0c81418fe94a7786cfd55f01e138ddc5d510583d`
- Original full file SHA-256: `07fa5f149931ca1a77144fd7d11fb5120d5d74ee47928e47602f299fe984c639`
- Preserved record SHA-256: `827383553d517d17d66d1a98e54c168e73877e65cd564da187ae9137f6b8025c`
- Projection created: `2026-10-30T02:00:12.626831+00:00` (processing time only; not a new observation)
- Comparison reference: `cbef41fbae1ba1105398183e42b008f2e7dfd3dc`
- Publication: proposed; independent auditor acceptance pending.
- Current owner(s): [test_openclaw_ollama_contract.py](../../../../../../../../../modules/communication/moltbot_bridge/tests/test_openclaw_ollama_contract.py)

Disposition: Archive the old 106-test and live-probe log additions without adding them to the active test log as fresh results. Current main already contains the Ollama default/timeout cases and bounded fake-I/O contract tests; only the independent one-line identity assertion candidate remains.

Private host paths and unresolved external identifiers may be omitted only in this projection; raw originals remain in the private custody backmap. External citations are retained as historical references and have not been refreshed. Runtime and commenting remain unverified.

## Historical content

## 2026-09-05: Ollama relocation and cold-start timeout coverage

- Added focused coverage to the existing `test_openclaw_dae.py` runtime-flags
  suite for the Foundups Ollama default and configurable request timeout.
- Live pre-fix evidence: `/api/tags` returned four models after relocation;
  the exact OpenClaw-style `/api/chat` request timed out at 15 seconds, then
  succeeded with `qwen-overseer:latest` in 86.36 seconds when allowed 90.
- Focused command and result are recorded after execution below; this entry
  does not reuse historical aggregate pass counts. (WSP 06/22/34/50/97)
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k 'ollama_defaults_match_foundups_runtime or ollama_fallback_uses_configured_cold_start_timeout' -q`
- Result: **2 passed, 104 deselected** in 1.50 seconds; two pre-existing pytest
  configuration warnings were emitted.
- Live code-path result: `OpenClawDAE._execute_conversation()` used
  `qwen-overseer:latest`, `timeout=120.0`, reported `engine=ollama`, and returned
  `0102: CODEBASE_OLLAMA_OK`.
- The first full-file replay exposed two ambient-model cases: an identity
  assertion with case-sensitive wording and an unauthorized command that was
  logged as blocked but downgraded to conversation. The assertion now accepts
  the existing case-insensitive identity contract; the process loop now fails
  closed immediately on preflight rejection.
- Critical-path replay: **5 passed, 101 deselected** in 34.45 seconds.
- Final full-file replay: **106 passed, 2 warnings** in 43.20 seconds. The
  warnings are existing unknown pytest configuration options.
- Post-reconciliation full-file replay: **106 passed, 2 warnings** in 47.90
  seconds after synchronizing `.env.example` and `docs/CHANNEL_SETUP.md` with
  the installed Ollama model. No runtime regression was observed.
- Final live code-path probe used `qwen-overseer:latest`, the 120-second
  default, and `engine=ollama`, returning
  `0102: Final_PATH_RECONCILIATION_OK`.
