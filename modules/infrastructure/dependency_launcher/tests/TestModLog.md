# Dependency launcher test inventory

## 2026-10-29 — Native startup offline qualification

Actual owned-source validation passed94 cases, zero failures/skips:49 startup,
21 existing model-selection/dependency-boundary, and24 lifecycle controls.
The external runner imports actual worktree source with no draft overlays,
uses a fixed minimal credential-free child environment, clears/replaces it
before source imports, denies real process/HTTP/socket-create-connection effects
with constant messages, checks mock counts without serializing kwargs, and isolates lifecycle
journals and OS mutexes from the shared live-model namespace. Existing node-lock
identity/journal protocol is checked directly with the actual borrowed transaction.
This is local unit evidence, not independent acceptance, live daemon readiness,
model inference, or full main.py execution. The earlier49 isolated draft cases
overlap with this selection and are not added to it.

Coverage: warm exact General readiness without CLI/discovery; server versus
resident distinction; installed/missing/wrong/ambiguous models; malformed/auth
HTTP; occupied port; missing/denied/incomplete/conflicting/racing processes;
checked nonzero/timeouts; explicit bind; cold GUI refusal without spawn, while
existing GUI via CLI remains usable; bounded API
failure; busy competing callers; actual facade/ensure_dependencies forwarding;
actual isolated YouTube Phase-2 AST execution; unchanged General default; and
three prior-protocol/actual transaction lock+digest equivalence controls.
The caller AST slice avoids importing/starting the full DAE and establishes only
that selected phase's argument flow. Model loading/unloading/inference is denied.

The unchanged21 model-selection/dependency-boundary cases also passed on clean
01b87f0e before implementation. Those earlier results overlap with the94-case
actual-source selection. Independent review remains a separate gate.


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
