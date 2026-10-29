# System health tools

This module contains separate root-name validation and message-health analysis
tools. The generated `SystemHealthMonitor` class remains a placeholder; it does
not certify the real tools or provide an operational monitoring service.

[`WSP85Validator`](src/wsp_85_validator.py) inspects immediate children of a chosen
repository root, classifies prohibited files/directories and unknown visible
files, and suggests placement. It does not inspect file contents, recursively
scan children, delete files, move work or execute its suggested commands.
The command-line entrypoint checks the current directory and exits 1 for findings,
0 for none. Filesystem errors may raise; an empty finding list is not proof that
all repository content is secure or WSP compliant.

[`SystemHealthAnalyzer`](src/system_health_analyzer.py) keeps message/issue and
timing data in memory, creates the selected memory directory during construction,
and can send issue observations to an explicitly supplied engine. Its score is a
heuristic over supplied messages, not an independent service-health measurement.
Samples are not redacted automatically. It is separate from root validation.

Use the [interface](INTERFACE.md) for effect boundaries and the
[test guide](tests/README.md) for bounded offline checks. Legacy integration
drivers can reach YouTube and social publishing flows; they are not substitutes
for the root-validator unit tests. This slice qualifies only root classification
against disposable fixtures. Analyzer and live integration behavior remain
IMPLEMENTED_NOT_VALIDATED by this work.
