# DocDAE interface and persistence boundaries

These are source-reviewed prototype interfaces. No model, organizer, cleanup
chain or filesystem migration was run for this documentation change.

## Documentation organizer

[`DocDAE(root_docs_path=None)`](src/doc_dae.py) creates its module memory directory,
attempts local model initialization and loads JSON pattern memory. Constructing it
is not a read-only operation. `analyze_docs_folder()` recursively inventories the
selected docs root. `generate_movement_plan(analysis)` returns moves, archives,
keeps, unmatched items and a summary. These names do not prove model inference.

`execute_plan(plan, dry_run=True)` returns completed move/archive counts, errors
and the mode. False enables directory creation and `shutil.move`; the helper
name `_safe_move_file` does not implement a repository-bound authorization,
collision review or automatic Git commit. Source/destination plans need separate
review before execution.

`run_autonomous_organization(dry_run=True)` combines analysis, planning and
execution, then records training memory and attempts a doc-index update. **Dry
run does not disable all persistence.** The current training helper appends a
`pattern` after its move loop: zero moves can leave it undefined, and a recorded
success is not tied to a verified successful move. Do not interpret that memory
as acceptance evidence. `update_doc_index(..., dry_run=True)` itself previews
rather than writes; false writes the docs-root JSON index. The convenience
`run_doc_organization(dry_run=True)` constructs the same owner.

## Cleanup planning chain

[`AutonomousCleanupEngine(doc_root=None)`](src/autonomous_cleanup_engine.py)
constructs DocDAE and creates data/metrics directories. `run_phase_one(limit=None,
persist=True)` returns labels and PhaseSummary; the limit is applied **after**
the full DocDAE scan. `run_phase_two(labels, persist=True)` returns scored batches
and items for review. Async `run_phase_three(plan, persist=True, sample_limit=5,
preview_lines=6)` uses the Holo MCP client when batches exist and returns a
validated plan plus decision counts. It plans/reviews; these entrypoints do not
execute the proposed cleanup moves.

`persist=False` suppresses the primary labels/plan files, but metric recording
still appends JSONL. The [CLI runner](scripts/run_autonomous_cleanup_chain.py)
also records breadcrumbs even with `--dry-run`; its output flags describe primary
artifacts, not zero disk writes. Samples may retain document text and are not a
redaction boundary. Runtime authority, path safety, model fidelity and retained
learning remain independently unvalidated by this interface document.
