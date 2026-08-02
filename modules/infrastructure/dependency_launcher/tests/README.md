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
