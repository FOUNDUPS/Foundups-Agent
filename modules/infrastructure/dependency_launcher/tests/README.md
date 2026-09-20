# Dependency Launcher Tests

The suite covers browser dependency recovery and the read-only runtime
compatibility advisory.

The separate WSL version advisory now requires both advisory and command opt-ins
before executing installed programs. The existing suite expanded from25 to43
cases: initial11 failed/32 passed, then43 passed after the source repair. Four
selected existing main/Gateway caller checks also passed. All used injected
boundaries; no real WSL, agent, provider or model was invoked.

The canonical [test inventory](TestModLog.md) lists all four existing test owners.
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
