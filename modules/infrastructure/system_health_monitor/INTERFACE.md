# System health tools interface

## Root validator

`WSP85Validator(project_root=".")` resolves a path; construction does not create
directories. `scan_root_directory()` returns a dictionary with `prohibited_files`,
`prohibited_dirs` and `unknown_files`, each a list of path strings. It enumerates
immediate children and uses filesystem type checks; symbolic-link type checks may
follow their targets, but the validator does not recursively enumerate them.
Absent or inaccessible roots are errors, not clean results. Ordering follows the
filesystem and is not a stable API guarantee.

Root temporary names and handoff prompt names are checked before the generic
hidden-file exemption. Recognized foundational Git/configuration/instruction
files are allowed. A directory whose name begins with an ASCII drive letter and
the Windows private-use colon substitution is reported for ownership review.
That report grants no authority to delete or relocate its contents.

`get_correct_placement(filename)` returns advisory text. `validate_and_report()`
prints findings and returns whether all three categories are empty.
`suggest_fixes(violations)` returns strings for a subset of findings; it does not
execute them, shell-quote arbitrary names or establish move safety. The CLI's
`main()` checks the current working directory and returns 0 or 1. There is no
automatic cleanup, provider call, credential read or persistence in this owner.

## Separate analyzer and scaffold

`SystemHealthAnalyzer(memory_dir="memory/system_health")` creates that directory.
`analyze_message(message, timestamp=None)` updates bounded message history and
issue/error state, returning newly detected issues; an explicit zero timestamp
falls back to current time. `track_operation(operation, duration_ms)` records
timings. `analyze_pattern(pattern_type, pattern_data)` returns heuristic advice
or None. `get_health_report()` returns a dictionary of score, counts, timings,
critical issue data and recommendations; samples are not a redaction boundary.
`integrate_with_self_improvement(engine)` calls `engine.observe_system_issue`
for stored high/critical issues and returns the report; delegated effects depend
on that engine. These APIs are source-reviewed, not exercised by the root tests.

`SystemHealthMonitor(config=None).process()` and
`utility_system_health_monitor()` return placeholder strings. Their presence
does not implement the old generated interface template's proposed service.
See [source](src/system_health_monitor.py) and [tests](tests/README.md).
