# pfMALL discovery change log

## 2026-11-25 — Strict HPC discovery calls

Added optional `raise_on_error` for scheduled HPC proposal generation and sanitized provider exception logging. Existing callers retain their default proposal behavior; no source is auto-admitted by exploratory search. Existing discovery tests passed within the 135-test focused run. WSP 22/50/71/97.
