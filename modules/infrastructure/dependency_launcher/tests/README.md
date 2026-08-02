# Dependency Launcher Tests

The suite covers browser dependency recovery and the read-only runtime
compatibility advisory.

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
