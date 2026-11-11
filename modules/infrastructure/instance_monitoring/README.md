# Instance status and log-vitals tools

This owner contains a deterministic [log-vitals reader](scripts/log_vitals.py)
and an interactive-style [instance status report](scripts/status_check.py).
They reuse existing instance-lock, dependency-status and YouTube automation-gate
owners rather than managing a new daemon or database.

Log vitals counts matching log levels and a few message signals; it does not
establish service health from arbitrary logs. Tail mode retains a bounded number
of lines in memory but still reads the whole file. Missing-script samples retain
message text, so the output is not a secret-redaction boundary.

The status report may remove stale YouTube/HoloDAE lock files by default. Setting
`INSTANCE_LOCK_AUTO_CLEAN_STALE=false` disables that explicit cleanup branch,
but does not certify every delegated helper as side-effect-free. Do not call it
as an assumed read-only inventory during concurrent daemon work.

[INTERFACE.md](INTERFACE.md) describes arguments, return shapes and limitations.
This documentation-only change did not inspect private logs, query live instances,
remove locks or run these entrypoints. No module-local test suite is tracked.
