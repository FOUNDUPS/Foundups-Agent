# Instance status and log-vitals tools interface

[log_vitals.py](scripts/log_vitals.py) provides
`compute_vitals(lines) -> Vitals`. It recognizes timestamp/logger/uppercase-level
lines matching `LOG_LINE_RE`, counts levels, returns the top five ERROR/WARNING
loggers, and tracks missing-script, terminated-Chrome, discovery-cache and offline
message indicators. `lines_scanned` counts every supplied line, including unmatched
ones. `Vitals.to_dict()` adds a current UTC `generated_at` value; counts are not
an independent live-health verdict.

`main(argv=None) -> int` accepts `--file` (default `012.txt`), `--lines` (910),
mutually exclusive `--head`/`--tail`, and `--json`. Head is the default. Missing
paths return 2; ordinary completion returns 0. Other file/read/argument failures
are not normalized into a structured result. Tail reads the full file into a
bounded deque; this is not a bounded-byte or Git-tracked scanner.

[status_check.py](scripts/status_check.py) exposes `check_instance_status()` with
printed output and no structured result. It reports duplicate processes, lock
metadata and health for `youtube_monitor` and `holodae_monitor`, checks local
automation dependencies and prints selected feature/gate snapshots. Duplicate
detection can return early; broad exception handlers print errors. Stale-lock
cleanup defaults on via `INSTANCE_LOCK_AUTO_CLEAN_STALE`; false disables its
explicit cleanup calls. It modifies import search paths at import time and may
invoke delegated helpers when called. Neither script was executed for this
source-only interface documentation.
