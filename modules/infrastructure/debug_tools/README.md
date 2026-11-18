# Import diagnostics

This legacy module contains two executable diagnostics, not a passive library. `src/import_tracer.py` inserts an ImportTimer into sys.meta_path and immediately imports the repository main module. `src/stderr_wrapper.py` similarly installs StderrWatchingFinder and imports main while observing changes to stderr. Merely importing either file runs that diagnostic.

ImportTimer measures intervals between import-hook callbacks; those intervals are heuristic observations, not isolated per-module execution times. StderrWatchingFinder reports when it first observes a stream replacement and the recent import chain; this does not prove which exact statement replaced the stream.

Both tools can trigger the side effects of main and its imports. Review those owners and use an isolated process/check-out before a deliberate diagnostic run. No automatic startup or unit-test collection is documented here. The module has no tracked dedicated tests or dependency manifest at this revision. Source inspection establishes these boundaries; no live diagnostic was executed for this documentation.
