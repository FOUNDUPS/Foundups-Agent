# Training menu and command adapters

`scripts/launch.py` provides `run_training_system()`, the interactive training
menu. `scripts/training_commands.py` provides
`execute_training_command(command, targets, json_output) -> None`; it prints a
result rather than returning the result mapping. Both use existing HoloIndex
pattern-memory and training owners rather than implementing a model trainer.

Supported command names are `utf8_scan`, `utf8_summary`, `utf8_fix` and `batch`.
Targets are comma-separated scopes. Scan and summary delegate to the canonical
`modules/ai_intelligence/utf8_hygiene/scripts/scanner.py`. Command execution
attempts to initialize PatternMemory even for scan/summary. `utf8_fix` invokes
the remediation coordinator with auto-approval; `batch` invokes the idle DAE's
pattern-training operation. They are not read-only audit commands.

The menu can read the configured training corpus, store/recall patterns and run
model-routing work. Its Gemma policy and Qwen summary drills are explicitly
unimplemented menu options. Option 9 clears stored patterns and resets their
checkpoint after its typed confirmation. Do not use that operation to verify
documentation or ordinary source changes.

Dependencies and storage behavior belong to HoloIndex, UTF-8 hygiene and the
idle automation owners. `tests/test_utf8_import_boundary.py` checks callable
imports, helper signatures and simple missing-target behavior; it does not prove
exclusion of every transitive import or establish operational model training. No
corpus, pattern database, model, remediation or destructive menu action was
executed for this documentation review.
