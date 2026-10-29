# UTF-8 hygiene scanner

This owner contains the [legacy scanner](scripts/scanner.py) used by
the training-system command adapter. It flags characters whose code points exceed
127 in selected Python, Markdown, text, JSON and YAML files. That is an ASCII
compatibility heuristic, **not UTF-8 validation**: ordinary Japanese and other
valid Unicode text will be reported. A finding is not authorization to delete or
replace that text.

The scanner reads paths relative to the working directory and recursively scans
directories without Git inventory, byte limits or vendor exclusions. It prints
finding snippets. When findings exist and no memory is supplied, it attempts to
construct Holo PatternMemory and store them. Passing `memory=None` therefore does
not select a strictly read-only mode. Summaries also use that existing memory
owner; this module does not define a second store.

See [INTERFACE.md](INTERFACE.md) for arguments, result shapes and side effects.
This documentation is source-reviewed; no live scan, model/database operation or
behavioral acceptance run was performed. No module-local test suite is tracked.
