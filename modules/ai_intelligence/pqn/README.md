# PQN launch adapters

This folder adapts interactive and broker entrypoints to the existing
`modules/ai_intelligence/pqn_alignment` implementation. It does not provide a
second research engine. The maintained source is `scripts/launch.py`.

`run_pqn_dae()` opens a menu for architect/research work, local model selection
and experimental diagnostic protocols. Model selection inspects local model
directories and may start model work. This is an operational menu, not a test.

The non-interactive adapters are `run_pqn_architect_once()`,
`run_pqn_research_session(selected_agents=None, session_name="PQN_Research", save_results=True)`, and
`run_pqn_simulation_once(config=None)`. They delegate to the alignment owner's
architect, research orchestrator and theory/archive cycle respectively. The
architect may execute its selected directive and writes a timestamped report
under repository `strategic_reports/`; research saves under `research_results/`
when enabled. These adapters are not read-only, offline-safe diagnostics.

Use the alignment owner's documentation and dependency contracts before a
deliberate run. Experimental quantum/consciousness terminology describes the
software's research framing; this adapter establishes no physical quantum or
consciousness result. `tests/test_launch_runtime.py` contains bounded adapter
tests; their exact current results must be recorded separately. No live model,
research session or directive was executed for this documentation review.
