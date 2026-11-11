# WSP tools interface

This module contains three distinct legacy entrypoints. None was executed for
this source-only contract review; historical file counts are not current audits.

## Flagged wrapper repair

[`scripts/fix_wsp90_utf8_bulk.py`](scripts/fix_wsp90_utf8_bulk.py) exposes
`fix_file(filepath, dry_run=True, include_entrypoints=False) -> (modified, message)`.
It parses the original source to find executable `io.TextIOWrapper` assignments,
skips recognized entrypoints by default and skips content already mentioning
`FOUNDUPS_UTF8_WRAPPED`. Regex substitutions produce the candidate text. In dry
mode, `modified=True` means a proposed change; otherwise the file is rewritten
as UTF-8. The replacement is not reparsed or behaviorally tested by this helper.

The CLI requires `--dry-run` or `--apply`, optionally `--include-entrypoints` and
`--verbose`. If both mode flags are supplied, **`--apply` wins**. It recursively
walks the repository's `modules` directory, excluding only named backup/cache
patterns in its source; it is not a Git-tracked bounded audit. Per-file failures
are printed and counted without a final nonzero failure status.

## Older bulk remover and campaign

[`src/wsp90_bulk_fix.py`](src/wsp90_bulk_fix.py) exposes `is_entry_point(path)` and
`remove_utf8_enforcement(path) -> (success, removed_lines)`. The latter directly
rewrites matching marked blocks, without a dry-run argument or AST validation.
Its `main()` scans the hard-coded `O:/Foundups-Agent/modules` path and applies
changes. Do not confuse this executable with the flagged preview script above.

[`src/wsp90_orchestrator.py`](src/wsp90_orchestrator.py) exposes async
`orchestrate_wsp90_campaign()`. It constructs WSPOrchestrator, submits a historical
bulk-change task, then invokes `tools/wsp90_enforcer.py` from the working directory.
It prints results/errors without a structured acceptance receipt. This interface
does not authorize a campaign or prove model execution, compatibility or safety.
