# Preserved historical record: ModLog.md

> Historical/proposal material. This is not a current acceptance receipt, runtime check or instruction to apply old code. The original dates and claimed outcomes below retain their historical scope.

- Original relative path: `modules/infrastructure/dependency_launcher/ModLog.md`
- Original PC base: `0c81418fe94a7786cfd55f01e138ddc5d510583d`
- Original full file SHA-256: `31951a02d208417f99e57528837fe65322da8725d1603cdb72efabccfef9b85d`
- Preserved record SHA-256: `6f5e3883b3e556aa64a4ff9a7c7edab50bed0f69a54fa33f5236bf9acc61b80e`
- Projection created: `2026-10-30T02:00:12.626831+00:00` (processing time only; not a new observation)
- Comparison reference: `cbef41fbae1ba1105398183e42b008f2e7dfd3dc`
- Publication: proposed; independent auditor acceptance pending.
- Current owner(s): [README.md](../../../../../../../../modules/infrastructure/dependency_launcher/README.md)

Disposition: Archive the old llmster startup/autoload history rather than apply it to current launcher behavior. Current main protects native inventory readiness, exact model identity, node ownership and cold-GUI fallback policy. Unique legacy /api/v1/models/load helper deltas remain separately preserved for lifecycle-owner qualification, not silently dropped or enabled.

Private host paths and unresolved external identifiers may be omitted only in this projection; raw originals remain in the private custody backmap. External citations are retained as historical references and have not been refreshed. Runtime and commenting remain unverified.

## Historical content


### 2026-10-29: Headless `llmster` Startup Fallback & Mutual Exclusion Guard

- Added `resolve_lms_cli_path()`, `is_llmster_process_running()`, `is_lm_studio_gui_running()`, and `launch_llmster()` in `src/dae_dependencies.py`.
- Updated `launch_lm_studio()` so YouTube DAE (`main.py`) startup uses headless `llmster` (`lms daemon up` + `lms server start --port 1234`) when `LM Studio.exe` is unavailable or when `LM_STUDIO_PREFER_LLMSTER=true` (default), while strictly preventing `LM Studio.exe` and `llmster` from launching concurrently.
- Added `/api/v1/models/load` to model auto-loader endpoint candidates and added unit coverage in `tests/test_llmster_startup_fallback.py`. (WSP 11/22/27/50/77/97)
