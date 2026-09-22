# Dependency Launcher Tests

The suite covers browser dependency recovery and the read-only runtime
compatibility advisory.

The separate WSL version advisory now requires both advisory and command opt-ins
before executing installed programs. The existing suite expanded from25 to43
cases: initial11 failed/32 passed, then43 passed after the source repair. Four
selected existing main/Gateway caller checks also passed. All used injected
boundaries; no real WSL, agent, provider or model was invoked.

The canonical [test inventory](TestModLog.md) lists all four existing test owners.

This WSL owner is content-bound by RedDog's existing backend manifest. Source
edits also require `python -B scripts/generate_reddog_backend_manifest.py --check`,
the existing generator tests (including staged-index closure), and RedDog's
backend compatibility/fast/package checks. If stale, regenerate the manifest and
update its existing extension and generator-test digest pins together; preserve
membership and gate assertions. PR1806 first CI caught this omitted integration
step after local adapter checks had passed. This maintenance does not release
or install an extension, launch WSL, or grant runtime authority.
The initial connected-check collection failed because the external dotenv stub
lacked `dotenv_values`; correcting that harness enabled the unchanged four
checks. This was not an application test failure or application-code repair.

For connected main imports, stub `env_managed_enabled`, `load_managed_env`, and
dotenv loading/value functions before collection, and use an external working
directory for logs. Select the two fail-soft runtime adapter tests and the two
Gateway transport-vector tests; avoid launching main or installed runtimes.
Use `python -B`, disabled bytecode/plugin autoload, isolated TMP/TEMP/database
paths, `--import-mode=importlib`, `-p pytest_asyncio.plugin` and
`-p no:cacheprovider`. Exact commands and receipts are bound in the system backlog.

Historical qualification on 2026-09-20: unchanged WSL source/tests passed25 in an isolated
temporary environment. Seven external injected witnesses also passed, covering
disabled, stopped, running, stop-before-exec, invalid distro, base mismatch and
the then-unsupported command-mode flag. These establish pre-repair command
reachability and modeled state transitions; they do not prove real WSL startup,
service health or no-start behavior. No WSL or provider was invoked.

The source/test lifecycle wording is now corrected per the
[module roadmap](../ROADMAP.md#wsl-advisory-lifecycle-boundary--2026-09-20).
The original source structural limits and adjacent Gateway/main contracts remain.

`test_wsl_agent_runtime.py` covers plain and numeric-suffixed OpenClaw releases,
optional build IDs, exact version preservation and rejection of unrecognized
suffix content. The probe remains advisory even when both components pass.
The 2026-09-13 focused run with the adjacent OpenClaw Gateway adapter passed
68 tests; a real WSL version-only probe changed from a false unavailable result
to PASS for installed OpenClaw `2026.7.1-2` and Hermes `0.20.4`.

Run:

```text
python -m pytest modules/infrastructure/dependency_launcher/tests -q
```

The compatibility tests must prove digest/TTL/component validation, off-repo
path confinement, nonblocking missing-evidence behavior, and absence of network
or command-execution imports.

Supplier tests additionally prove exact source sets, source-receipt
rehydration, expiry, official-release URL confinement, redirect/size rejection,
atomic prior-cache preservation, supply/output non-aliasing, and no install,
command, or model-load path. A recomputed-hash forgery must remain overall
`NOT_READY`; integrity-only source comparisons never claim authenticated
`CURRENT`.

## Signed expectation projection acceptance matrix

Contract: [existing interface owner](../INTERFACE.md#signed-expectation-projection-contract--qualification-2026-09-22).
This fixed matrix is an implementation gate. It is not a claim that a signed
slot projector exists. Reuse `ai_gateway/tests/test_model_runtime_binding_security.py`
and its serialized signed-evidence fixtures, current trusted-time/key inputs and
actual verification/one-shot APIs. Their deterministic signature verifier is a
test double, not a production cryptographic or signer-service qualification.
Never replace the evidence chain with a Boolean `verified=True` mock.

| ID | Synthetic condition | Required result | Current evidence / remaining work |
|---|---|---|---|
| C01 | Explicit exact slot mapping; same signed binding, role, model, provider, task and surface | Only the declared identity projects; overall v1 stays NOT_READY | Separate owner positive tests exist; cross-owner mapping/projector absent. |
| C02 | Change role, model, provider, task or runtime surface independently | Reject each substitution before projection; zero promoted output | Existing binding/topology checks are reusable; five slot-projection cases remain to implement. |
| C03 | Alter serialized selection, binding or signed evidence, including recomputed unkeyed hashes | Reject changed signed identity; no authority from self-hashes | Gateway tamper and supplier self-rehash tests exist; cross-owner cases pending. |
| C04 | Expired evidence or revoked/rotated key epoch before verification | Reject with no projection | Existing trusted-time/revocation controls; exact rotation case needs qualification. |
| C05 | Expiry/revocation/epoch change after capture, before projection | Revalidate at the qualified projection boundary or reject; no stale output | Gap: capability consumption alone does not recheck time/keys. |
| C06 | Reuse a consumed capability, or offer another dispatcher's capability | Reject replay; advisory never consumes borrowed dispatch authority | Existing one-shot rejection; advisory-private/discard lifecycle pending. |
| C07 | Missing/duplicate/partial promoted expectations or unsupported backend provenance | Reject exact-set supply; preserve previous valid cache | Existing supplier exact-set/cache tests; backend identity remains unsupported. |
| C08 | Tampered/expired supply or envelope; model evidence substituted for binary provenance | Reject or remain NOT_READY; zero update effects | Existing receipt/supplier tests; authenticated software provenance absent. |
| C09 | Success, mapping rejection or exception after private verification | Dispose every advisory-private capability; next dispatch verifies independently | New integration test required when an owner API is selected. |

The 2026-09-22 qualification reran the existing security, supplier and receipt
files together: **49 passed**, no skips, two disabled-plugin configuration
warnings. These are owner-level checks, not 49 end-to-end RSI experiments.
Do not count unimplemented rows above as passing. Exact source/test bindings,
independent review and publication state are in the canonical RSI backlog.
