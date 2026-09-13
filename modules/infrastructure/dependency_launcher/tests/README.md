# Dependency Launcher Tests

The suite covers browser dependency recovery and the read-only runtime
compatibility advisory.

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
