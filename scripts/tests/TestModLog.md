# Script test inventory

## 2026-10-25 — FoundUps source-closure repair inventory

Reuse all eight cases in `test_generate_reddog_backend_manifest.py`; only its
canonical digest fixture changes after measured AST-only regeneration. Preserve
independent generation, fixed LF/CRLF byte caps, executable/dynamic sentinel
membership and staged-index source/hash consistency. The FoundUps delivery plan
records WSP15 allocation before repair. Fresh results will be recorded after
the coherent source/manifest/constants/test binding is staged.

Fresh run after staging: eight passed, two inherited inactive asyncio config
warnings, 80.23 seconds. No test body or oracle changed beyond the expected
canonical digest pin. Node compatibility contract/preflight/recovery entrypoints
also exit0. These are source-binding checks, not installed-runtime qualification.

Existing suites inventoried before extending the security workflow contract (WSP 22/97).

- `test_advisory_model_defensive_critic.py`: Focused defensive critic and abstention contracts.
- `test_advisory_model_kimi_k3_budget_truth.py`: Fail-closed completion-budget tests for RedDog's advisory bridge.
- `test_advisory_model_once_hardening.py`: Bridge hardening tests for advisory_model_once (Addendum B + C).
- `test_advisory_model_panel_input_contract.py`: Focused end-to-end contracts for RedDog Fusion panel input truth.
- `test_ci_security_gate.py`: Security gate regression tests; synthetic credential is assembled at runtime.
- `test_generate_reddog_backend_manifest.py`: Independent contract tests for the RedDog backend manifest generator.
- `test_reddog_fusion_progress_bridge.py`: openrouter response metadata and usage are retained without content, chat completion creates valid content free receipt, missing key returns bound progress receipt without network, redaction block emits no openrouter call receipt, successful single runtime binds progress events to call
- `test_reddog_holoindex_activate_query_replica.py`: CLI contracts for default-inert HoloIndex replica activation.
- `test_reddog_holoindex_blocked_request_recovery_once.py`: bridge dispatches strict operation, bridge rejects unknown operation
- `test_reddog_holoindex_owner_query_once.py`: Tests for the extension's one-shot generation-bound HoloIndex bridge.

## 2026-10-22 — Python trust bootstrap

Extend `test_ci_security_gate.py` to require a checksum-bound pip/certifi bootstrap before workflow dependency downloads, including the separately created Windows venv, and preserve Docker ordering. These configuration checks are distinct from a live TLS rejection test.

Module-local Docker hash bootstrap parity and Node security-release pins are covered in the same security suite.
