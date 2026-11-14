# UTF-8 hygiene scanner interface

The source owner is [scripts/scanner.py](scripts/scanner.py).

- `run_utf8_hygiene_scan(memory=None, targets=None, interactive=True)` returns a
  list of dictionaries with `path`, one-based `line`, `snippet` and `offending`.
  Interactive input can replace `targets`; empty input restores hard-coded
  defaults. Empty/nonprovided targets select those defaults even noninteractively.
  Files are decoded as UTF-8; read errors and missing paths are printed rather
  than represented as structured failure results. An empty list is consequently
  not proof that every requested file was inspected successfully.
- Findings may be printed and stored through `memory.store_pattern`. With no
  supplied memory, the function attempts to initialize Holo PatternMemory after
  finding non-ASCII characters. It does not rewrite inspected files.
- `summarize_utf8_findings(memory=None, target_filters=None, limit=50)` reads
  collection records with `source=utf8_hygiene_scan`. Success returns `status`,
  `total_findings`, `files`, `unique_characters` and ranked `top` samples; memory
  initialization/query failures return `status=error` and `message`.
- The script accepts `scan` or `summary`; `scan` remains interactive. It does not
  parse a bounded target list from trailing command-line arguments.

Neither API proves invalid encoding, authorizes replacement of valid Unicode,
nor provides secret redaction or a repository-bound scan. Runtime compatibility
and storage behavior remain unvalidated by this documentation-only change.
