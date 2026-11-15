# Legacy code-quality analysis tools interface

[QwenOrphanAnalyzer](tools/orphan_analyzer.py) constructs a
`QwenInferenceEngine`. `analyze_orphan(orphan)` builds a prompt from required
orphan metadata and awaits `generate_async(max_tokens=300, temperature=0.3)`.
Prompt construction precedes its inference exception handler: malformed required
input can raise rather than return an ERROR result. Parsed model JSON gains
orphan metadata and a truncated raw response; model fields are not schema-validated.
Missing JSON falls back to ARCHIVE advice; parsing/inference errors use ERROR.

`analyze_batch(batch_file)` expects JSON `batch_id` and `orphans`, processes entries
sequentially and returns results. `save_results(results, output_file)` writes a
timestamp, counts by category and the results to the requested JSON path; it
does not create the output parent. The script entrypoint uses working-directory
paths `docs/qwen_batch_1_input.json` and `docs/qwen_batch_1_output.json`.
No classification moves, imports, archives or deletes the analyzed source.

[analyze_wsp90_risks()](tools/wsp90_analyzer.py) prints probe results and returns
`len(risks_found) == 0`. Only the later Windows redirection check contributes to
that list. Earlier failed print/log/subprocess checks are not accumulated into
the return value. The script maps the boolean to exit 0/1; its Windows message
does not independently verify stream-wrapper installation. Logging configuration,
temporary-file cleanup on exceptional paths and child execution are observable
side effects. This source review establishes no operational or safety verdict.
