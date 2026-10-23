# Dependency launcher test inventory

## 2026-09-22 — Signed expectation contract qualification

Reused the existing supplier and receipt suites with AI Gateway's runtime-binding
security suite:49 passed, zero skips, two disabled-plugin config warnings.
No new test file or changed oracle. The [fixed matrix](README.md#signed-expectation-projection-acceptance-matrix)
explicitly marks unimplemented cross-owner cases; passing existing owner tests
does not close them. Independent replay/source bindings live in the RSI backlog.

Canonical test memory under WSP22/50/84/97. Inventory inspected 2026-09-20;
reuse these four existing test files before adding another owner. This file
was missing and is added with the material WSL test expansion required by
WSP97 section1.2A. It is documentation, not a new test suite.

| Existing file | Coverage and reuse boundary |
|---|---|
| `test_attach_recovery_no_kill.py` | Mocked Chrome/Edge attach recovery, empty-page recovery, no-kill failures, successful attach and DevTools PUT/GET fallback. Does not validate a live browser. |
| `test_runtime_compatibility_receipt.py` | Cached integrity-only receipts, digest/TTL/schema/component checks, drift, missing evidence, off-repo path/size limits, nonblocking startup and no execution/network surface. |
| `test_runtime_compatibility_evidence_supplier.py` | Injected official release evidence, supply tamper/expiry/URL checks, redirect/size rejection, atomic publication, output alias rejection, watchlist integration and no update/model execution. |
| `test_wsl_agent_runtime.py` | WSL metadata versus explicit command selection, disabled receipt compatibility, registration/base failures, callback mutation, fixed vectors, version parsing/filtering, content-free errors, trusted executable resolution and structural limits. Uses injected runners; no real distro/service qualification. |

## 2026-09-20 — Explicit WSL command selection

The existing WSL test owner is extended, not replaced. Positive version tests
explicitly opt into command mode; separate cases enforce metadata-only behavior.
The original structural limits remain: source file240, function50, class200.
Exact red/green and independent verification results are recorded in the existing
[system backlog](../../../../docs/roadmaps/rsi_swarm_backlog.json), rather than
duplicating run receipts here. Earlier 25-test and seven injected-witness results
in the module documentation remain historical qualification evidence.

Adjacent callers are covered by the existing fail-soft adapter cases in
`tests/test_main_runtime_bootstrap.py` and transport-vector cases in
`modules/communication/moltbot_bridge/tests/test_reddog_openclaw_gateway_artifact_provider.py`.
Main import needs environment-loading stubs and disposable log storage; see
[execution guidance](README.md). Caller tests do not authorize runtime dispatch.
